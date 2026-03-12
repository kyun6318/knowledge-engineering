# Topic 명세서 (EventBridge Event Specification)

> C4 Container Layer 및 Sequence Diagram에서 참조하는 모든 EventBridge Event Type의 명세입니다.

---

## DynamoDB 테이블 스키마

> EP, RT, RunAPI가 공유하는 DynamoDB 테이블 구조입니다. 이후 모든 State Machine / Sequence에서 참조하는 필드명의 단일 출처(Single Source of Truth)입니다.

### `ml-run` 테이블
```yaml
ml-run:
  run_id: string              # Partition Key (PK)
  project: string             # 프로젝트 식별자 (GSI: project-index)
  run_key: string             # dataset_version + config_hash + image_tag + pipeline_name 조합
  state: string               # INTAKE | CONFIG_RESOLVING | LOCK_ACQUIRING | PLANNING |
                              # DATA_SYNCING | STEP_RUNNING | RETRYING | CANCELLING |
                              # COMPLETED | FAILED | CANCELLED | REJECTED | IGNORED |
                              # AWAITING_MANUAL | TERMINATED
  current_step: string        # preprocess | train | infer | postprocess | null
  attempt: int                # 현재 step의 재시도 횟수
                              # step 전환(preprocess→train→infer→postprocess) 시
                              # RT가 ml.{next_step}.requested 발행 시점에 0으로 리셋
  execution_plan_id: string   # ml-execution-plan 테이블 참조
  pipeline_execution_arn: string  # 현재 실행 중인 SageMaker Pipeline Execution ARN
                              # Pipeline Trigger가 StartPipelineExecution() 후 저장
                              # CANCELLING 상태에서 StopPipelineExecution 호출에 사용
                              # postprocess step (EXP 직접 호출)에는 null
  cancel_requested_at: string # CANCELLING 상태 진입 시 RT가 기록 (ISO 8601)
                              # Race Condition 해소용 기준 타임스탬프
                              # (step_failed.timestamp와 비교)
  s3_dataset_uri: string      # DATA_SYNCING 완료 후 EP가 저장
                              # (s3://ml-staging-{account}/{project}/{run_id}/ 경로)
                              # preprocess step에서 참조
  sync_attempt: int           # DATA_SYNCING 재시도 횟수 (0부터 시작)
                              # EP가 ml.data.sync.failed 수신 시 증가
                              # 기본 max_sync_attempts = 2
  created_at: string          # ISO 8601 timestamp
  updated_at: string          # ISO 8601 timestamp
```

### `ml-execution-plan` 테이블
```yaml
ml-execution-plan:
  execution_plan_id: string   # Partition Key (PK)
  run_id: string              # 상위 run 참조 (GSI: run-id-index)
  steps: list<string>         # ["preprocess", "train", "infer", "postprocess"]
  current_step_index: int     # 현재 실행 중인 step 인덱스
  infer_type: string          # batch | custom
  sync_target: string         # artifacts | results | both | none
  max_attempts: int           # step 최대 재시도 횟수
  max_sync_attempts: int      # DATA_SYNCING 최대 재시도 횟수 (기본값: 2)
  retry_policy: string        # DEFAULT | SKIP_RETRY (step 실패 시 기본 정책)
  dataset_version: string     # 사용 중인 데이터셋 버전
  config_hash: string         # 설정 해시 (run_key 구성 요소)
  image_tag: string           # 컨테이너 이미지 태그
                              # Pipeline Trigger가 StartPipelineExecution() 시 참조
                              # run_key 구성 요소: dataset_version + config_hash + image_tag + pipeline_name
```

### `ml-lock` 테이블
```yaml
ml-lock:
  idempotency_key: string     # Partition Key (PK) = project#run_key
  run_id: string              # 이 락을 점유한 run 참조
  created_at: string          # ISO 8601 timestamp
```

### `ml-duplicate-events` 테이블
```yaml
ml-duplicate-events:
  event_id: string            # Partition Key (PK)
  status: string              # IGNORED (고정값)
  duplicate_run_key: string   # 중복 감지된 run_key
  timestamp: string           # 중복 수신 시각 (ISO 8601)
  original_run_id: string     # 이미 실행 중인 원본 run 참조
```

### `ml-audit-events` 테이블
```yaml
ml-audit-events:
  event_id: string            # Partition Key (PK)
  event_type: string          # CANCEL_IGNORED | 향후 확장 가능
  run_id: string              # 대상 run 참조 (GSI: run-id-index)
  reason: string              # 무시된 이유 (예: "run already COMPLETED")
  requested_by: string        # 요청자 (cancel 요청자 등)
  timestamp: string           # 이벤트 수신 시각 (ISO 8601)
```

### `ml-processed-events` 테이블
```yaml
ml-processed-events:
  idempotency_key: string     # Partition Key (PK) = {run_id}_{step}_{attempt}
  run_id: string              # 처리된 run 참조
  processed_at: string        # 처리 시각 (ISO 8601)
  ttl: int                    # DynamoDB TTL (epoch seconds, 30일 후 자동 삭제)
```

> `ml-duplicate-events`는 동일 run_key 중복 실행 시도 기록 전용.
> `ml-audit-events`는 cancel 무시 등 운영 이벤트 감사(audit) 기록 전용.
> `ml-processed-events`는 RT의 멱등성 확인(idempotency_key 중복 처리 방지) 전용.

---

## Core Run Lifecycle

| Event Type (detail-type) | Publisher | Subscriber | Retry 정책 | Schema (주요 필드) |
|-------|-----------|------------|-----------|-------------------|
| `ml.run.requested` | RunAPI | Execution Planner | SQS retention (14일 기본) | `{project, run_key_hint, params, trigger_source}` |
| `ml.run.completed` | Run Tracker | Observability, 외부 시스템 | — (소비 전용) | `{run_id, steps_summary, artifact_uris, final_status}` |
| `ml.run.cancelled` | Run Tracker | Observability | — (소비 전용) | `{run_id, cancelled_step, cancelled_by, reason}` |
| `ml.run.cancel.requested` | RunAPI | Run Tracker | SQS retention | `{run_id, requested_by, reason}` |

## Step Execution

| Event Type (detail-type) | Publisher | Subscriber | Retry 정책 | Schema (주요 필드) |
|-------|-----------|------------|-----------|-------------------|
| `ml.preprocess.requested` | EP (초기) / RT via EventBridge Scheduler (재시도) | Preprocess Trigger | App-level retry via EventBridge Scheduler | `{run_id, step, dataset_version, execution_plan, attempt}` |
| `ml.train.requested` | RT / RT via EventBridge Scheduler (재시도) | Train Trigger | App-level retry via EventBridge Scheduler | `{run_id, step, dataset_version, execution_plan, attempt}` |
| `ml.infer.requested` | RT / RT via EventBridge Scheduler (재시도) | Infer Trigger | App-level retry via EventBridge Scheduler | `{run_id, step, model_version, execution_plan, attempt}` |
| `ml.postprocess.requested` | RT / RT via EventBridge Scheduler (재시도) | Postprocess Trigger | App-level retry via EventBridge Scheduler | `{run_id, step, execution_plan, attempt}` |
| `ml.step.completed` | Pipeline Trigger (Lambda) | Run Tracker | SQS retention | `{run_id, step, status, duration_s, idempotency_key, ...step별 outputs}` |
| `ml.step.failed` | Pipeline Trigger (Lambda) | Run Tracker (SQS FIFO: T_FAIL_Q) | App-level retry | `{run_id, step, attempt, error_code, error_msg, idempotency_key}` |

> **`ml.preprocess.requested` 발행자**:
> - **초기 실행**: DATA_SYNCING 완료 후 및 DATA_SYNCING 스킵 시 모두 EP(Execution Planner)가 발행
> - **재시도**: RT(Run Tracker)가 EventBridge Scheduler에 일회성 스케줄을 생성하고, 스케줄 실행 시점에 발행
> - RT가 직접 발행하지 않는 이유: 재시도는 EventBridge Scheduler의 ScheduleExpression 기반 지연 발행 메커니즘을 통해 처리되므로, 실제 메시지 발행 주체는 EventBridge Scheduler임
>
> **`ml.step.completed` / `ml.step.failed` 발행자**: SageMaker Pipeline 내 custom component가 직접 발행하는 것이 아닙니다. **Pipeline Trigger (Lambda)**가 SageMaker 완료/실패 이벤트를 수신(EventBridge 네이티브 상태 변경 이벤트 구독) 후 발행합니다. Postprocess Trigger의 경우 EXP(Cross-Account Exporter)를 동기 ECS Task 호출하고 완료 응답을 받은 뒤 발행합니다.
>
> **`idempotency_key` 형식**: `{run_id}_{step}_{attempt}` — RT가 중복 메시지 수신 시 이미 처리된 key이면 SQS DeleteMessage만 반환하고 로직을 건너뜁니다.
>
> **`retry_policy`**: `ml.step.failed` 메시지에는 포함되지 않습니다. RT가 DynamoDB의 `ml-execution-plan.retry_policy`를 조회하여 재시도 여부를 판단합니다. 단, `error_code=TIMEOUT` 수신 시 기본 정책은 `SKIP_RETRY`이며, `execution_plan.timeout_retry_policy`가 명시된 경우 해당 정책을 따릅니다.

## Data Sync

| Event Type (detail-type) | Publisher | Subscriber | Retry 정책 | Schema (주요 필드) |
|-------|-----------|------------|-----------|-------------------|
| `ml.data.synced` | S3 Cross-Account Copy Lambda (완료) | Execution Planner | SQS retention | `{run_id, s3_dataset_uri, transfer_status}` |
| `ml.data.sync.failed` | S3 Cross-Account Copy Lambda (실패) | Execution Planner | SQS retention | `{run_id, error_code, error_msg, copy_job_id}` |

## Error Handling

| Event Type (detail-type) | Publisher | Subscriber | Retry 정책 | Schema (주요 필드) |
|-------|-----------|------------|-----------|-------------------|
| `ml.dead-letter` | Run Tracker (App-level) | Operator (수동) | 무기한 보존 | `{original_event_type, original_message, attempt, first_receive_time}` |

> **`first_receive_time`**: SQS 메시지의 `ApproximateFirstReceiveTimestamp` 속성에서 추출합니다 (RT가 직접 측정하는 wall-clock이 아님). 이는 메시지가 처음 SQS에서 수신된 시각을 의미합니다.

---

## Step별 Output Schema (`ml.step.completed`)

| step | 추가 출력 필드 |
|------|---------------|
| preprocess | `processed_uri` |
| train | `artifact_uri, model_version, metrics` |
| infer | `result_uri` |
| postprocess | — (EXP가 Service Account S3에 업로드 완료 → S3 Event가 ResultIngest Job 자동 트리거. EventBridge 이벤트 없음.) |

---

## 공통 규칙

1. **Naming Convention**: `ml.{domain}.{action}` (예: `ml.run.requested`, `ml.step.completed`) — EventBridge `detail-type` 필드로 사용, `source`는 `ml-platform` 고정
2. **Message Ordering**: SQS FIFO Queue의 `MessageGroupId = run_id` (동일 run의 이벤트 순서 보장)
3. **Acknowledgement**: 모든 subscriber(Lambda)는 처리 완료 후 SQS DeleteMessage. 처리 실패 시 SQS Visibility Timeout 만료 → 재처리 → SQS DLQ (maxReceiveCount=5, 인프라 안전망)
4. **Application-level Retry**: `ml.step.failed` 전용. Run Tracker가 `attempt`와 DynamoDB `ml-execution-plan.retry_policy`를 확인하여 EventBridge Scheduler로 지연 재발행
5. **Idempotency**: `ml.step.completed` / `ml.step.failed` 수신 시 RT는 `idempotency_key`로 중복 처리 여부를 DynamoDB `ml-processed-events` 테이블에서 확인. 이미 처리된 경우 SQS DeleteMessage만 반환
6. **Retention**: SQS 기본 14일. `ml.dead-letter`는 30일 이상 보존 권장 (EventBridge Archive 활용)
7. **Dead Letter**: SQS native DLQ (maxReceiveCount 초과, 처리 실패 전용) ≠ Application-level DLQ (`ml.dead-letter` 이벤트, 비즈니스 로직 기반)
