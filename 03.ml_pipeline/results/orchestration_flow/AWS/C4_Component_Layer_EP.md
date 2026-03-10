> **Related Documents**: [C4_Component_Layer_RT.md](./C4_Component_Layer_RT.md) (Run Tracker — Step 완료/실패 수신), [C4_Component_Layer_Triggers.md](./C4_Component_Layer_Triggers.md) (Pipeline Trigger — Step 실행), [C4_Component_Layer_SMP.md](./C4_Component_Layer_SMP.md) (SageMaker Pipelines)

```mermaid
graph TD
  subgraph Data_Sync["Data Sync Orchestration"]
    STG_ORCH["Staging Orchestrator"]
    S3_COPY_CLIENT["S3 Cross-Account Copy Client"]
    SYNC_RESOLVER["Sync Strategy Resolver"]
  end

  subgraph Core_Planning["Execution Planning Core"]
    CFG_INIT["Configuration Initializer"]
    LOCK_MGR["Optimistic Lock Manager"]
    PLAN_BLD["Execution Plan Builder"]
  end

  subgraph Persistence["State & Plan Persistence"]
    DDB_CLIENT["DynamoDB Client"]
  end

  %% 입력 흐름 (EventBridge Rule → SQS FIFO → Lambda)
  EventBus([EventBridge: ml.run.requested]) --> CFG_INIT
  EventBus_Sync([EventBridge: ml.data.synced]) --> STG_ORCH
  EventBus_SyncFail([EventBridge: ml.data.sync.failed]) --> STG_ORCH

  %% 설정 및 멱등성 처리
  CFG_INIT -->|"read config & generate run_key"| DDB_CLIENT
  CFG_INIT -->|"idempotency_key"| LOCK_MGR
  LOCK_MGR -->|"PutItem ConditionExpression\n(project#run_key)"| DDB_CLIENT

  %% 잠금 실패 시 (조기 리턴 + 감사 기록)
  LOCK_MGR -.->|"ConditionalCheckFailed\n(Already Exists)"| ACK([Log & HTTP 409 / ACK])
  LOCK_MGR -.->|"write ml-duplicate-events\naudit record"| DDB_CLIENT

  %% 잠금 성공 시 -> 플랜 수립 및 동기화 판단
  LOCK_MGR -.->|"Success"| PLAN_BLD
  PLAN_BLD -->|"write ml-execution-plan & ml-run"| DDB_CLIENT
  PLAN_BLD --> SYNC_RESOLVER

  %% Data Sync 판단
  SYNC_RESOLVER -->|"Need Sync"| STG_ORCH
  SYNC_RESOLVER -->|"Skip Sync"| EB_CLIENT["EventBridge PutEvents Client"]

  %% S3 Cross-Account Copy + 상태 업데이트
  STG_ORCH -->|"invoke cross-account\nS3 copy Lambda"| S3_COPY_CLIENT
  STG_ORCH -->|"update state=DATA_SYNCING"| DDB_CLIENT
  S3_COPY_CLIENT -->|"Lambda (IAM AssumeRole)"| External_S3[(Data Account S3 → ML Account S3)]

  %% Sync 완료 시 EP가 직접 첫 Step 발행
  STG_ORCH -->|"sync 완료:\nupdate state=STEP_RUNNING\n+ save s3_dataset_uri"| DDB_CLIENT
  STG_ORCH -->|"first step 발행"| EB_CLIENT

  %% Sync 실패 시 재시도/FAILED 분기
  STG_ORCH -.->|"sync_attempt < max\n& retryable error"| S3_COPY_CLIENT
  STG_ORCH -.->|"sync_attempt ≥ max\nOR MANIFEST_INVALID"| FAIL_OUT([update state=FAILED\n& Log Error])

  %% Sync 스킵 시 & Sync 완료 시 모두 EP가 발행
  EB_CLIENT -->|"publish ml.preprocess.requested"| EventBus_Out[(EventBridge Event Bus)]

  %% 스타일 적용
  classDef comp fill:#bbf,stroke:#333,stroke-width:2px;
  class STG_ORCH,S3_COPY_CLIENT,SYNC_RESOLVER,CFG_INIT,LOCK_MGR,PLAN_BLD,DDB_CLIENT,EB_CLIENT comp;
```

### Component Details
1. **Configuration Initializer**: DynamoDB `ml-config` 테이블을 조회하여 설정값을 병합하고, `dataset_version`, `config_hash`, `image_tag`, `pipeline_name`을 조합하여 고유한 `run_key`를 계산하는 통합 파이프라인(순차 프로세스)입니다. 민감 정보 조회는 EXP 컴포넌트로 이관하였으며, EP에서는 ENV 기반 비암호화 구성값만 사용합니다.
2. **Optimistic Lock Manager**: DynamoDB `PutItem`의 `ConditionExpression: attribute_not_exists(PK)`를 사용하여 `idempotency_key` (project#run_key)를 기반으로 중복 실행을 원천 차단합니다. 잠금 실패(`ConditionalCheckFailedException`, 중복 요청) 시 `ml-duplicate-events` 테이블에 감사 기록(`status=IGNORED, duplicate_run_key, timestamp, original_run_id`)을 저장한 후 조기 종료합니다.
3. **Execution Plan Builder**: 사용할 Step 시퀀스, 재시도 횟수, Sync Target 등의 최종 `ml-execution-plan` 항목과 `ml-run` 항목을 생성하여 DynamoDB에 `TransactWriteItems`로 원자적 저장합니다.
4. **Sync Strategy Resolver**: 수립된 계획과 S3 상태를 비교하여 Data Sync(S3 Cross-Account Copy)가 필요한지 판단합니다. 동기화가 불필요하면 즉시 `EventBridge PutEvents Client`를 호출해 첫 Step 이벤트(`ml.preprocess.requested`)를 발행합니다.
5. **Staging Orchestrator**: S3 Cross-Account Copy Lambda를 호출하여 전송 작업을 시작하며, 동시에 DynamoDB에 `state=DATA_SYNCING`을 기록합니다. EventBridge 규칙으로 라우팅되는 `ml.data.synced` 이벤트를 수신하면, **EP 내부에서 `execution_plan`을 재조회**하고, `state=STEP_RUNNING + s3_dataset_uri`를 DynamoDB에 업데이트한 후, 직접 `EventBridge PutEvents Client`를 통해 `ml.preprocess.requested`를 발행합니다 (Topic Spec의 `ml.data.synced` Subscriber = EP 원칙 유지). `ml.data.sync.failed` 수신 시에는 `error_code`와 `sync_attempt`를 평가하여, 재시도 가능하면(`error_code ≠ MANIFEST_INVALID && sync_attempt < max_sync_attempts`) Copy Lambda를 재트리거하고, 그렇지 않으면 `state=FAILED`로 전이하여 종료합니다.
6. **S3 Cross-Account Copy Client**: ML Account의 Lambda가 IAM Cross-Account Role을 AssumeRole하여 Data Account S3에서 ML Account S3 staging 영역으로 객체를 복사합니다. Copy 완료 또는 실패 시 EventBridge에 `ml.data.synced` 또는 `ml.data.sync.failed` 이벤트를 발행합니다.
