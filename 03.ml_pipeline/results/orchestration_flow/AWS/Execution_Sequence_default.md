```mermaid
sequenceDiagram
  autonumber

  participant S3      as Data Account S3<br>(dataset / manifest)
  participant EB_DATA as Amazon EventBridge<br>(Data Account)
  participant RunAPI  as Run Request API<br>(API Gateway + Lambda)
  participant EB      as EventBridge<br>(ML Account Event Bus)
  participant EP      as Execution Planner<br>(Lambda)
  participant RT      as Run Tracker<br>(Lambda)
  participant DDB     as DynamoDB<br>(ml-run / ml-execution-plan / ml-lock)
  participant SM      as Secrets Manager<br>(Cross-Account Role ARN)
  participant COPY    as S3 Cross-Account Copy Lambda<br>(Data Account S3 → ML Account S3)
  participant S3ML    as S3 ML Account<br>(staging / artifacts / results)
  participant TRG     as Pipeline Trigger<br>(Lambda — step별 독립 인스턴스)
  participant SMP     as SageMaker Pipelines<br>(Pipeline Orchestration)
  participant ECR     as Amazon ECR<br>(container images)
  participant SM_JOB  as SageMaker Jobs<br>(Training / BatchTransform / Processing)
  participant MR      as SageMaker Model Registry
  participant EXP     as Cross-Account Exporter<br>(ECS Fargate Task)
  participant S3A     as Service Account S3<br>(model artifacts)
  participant S3R     as Service Account S3<br>(inference results)
  participant CW      as Amazon CloudWatch
  participant SL      as Slack

  %% ── Trigger ──
  rect rgb(230, 240, 255)
    Note over S3, RunAPI: 진입점 — 데이터 도착 or 수동 트리거
    alt 데이터 도착 트리거
      S3->>EB_DATA: S3 Event Notification<br>(_READY marker 감지)
      EB_DATA->>RunAPI: API Destination HTTPS POST<br>(Connection: SigV4 IAM Auth)
    else 수동 / 운영 트리거
      Note over RunAPI: Operator / EventBridge Scheduler 직접 호출
    end
    RunAPI->>RunAPI: AuthN/AuthZ + Request Validation
    RunAPI->>EB: publish ml.run.requested<br>{project, run_key_hint, params, trigger_source}
  end

  %% ── Config / run_key / Lock ──
  rect rgb(240, 255, 240)
    Note over EP, DDB: Execution Planner — 설정 조회 · run_key 계산 · 락 획득
    EB->>EP: EventBridge Rule → SQS FIFO → Lambda
    EP->>DDB: 설정 조회 (ml-config 테이블)
    DDB-->>EP: config + config_hash
    EP->>SM: 민감 정보 조회 (필요 시)
    SM-->>EP: credentials / API keys
    EP->>EP: run_key 계산<br>(dataset_version + config_hash<br>+ image_tag + pipeline_name)
    EP->>DDB: PutItem ConditionExpression<br>(idempotency_key = project#run_key)
    DDB-->>EP: lock acquired
    EP->>DDB: save ml-execution-plan + state=PLANNING<br>{steps=["preprocess","train","infer","postprocess"],<br>infer_type, sync_target, dataset_version,<br>max_attempts, retry_policy, config_hash}
  end

  %% ── Data Sync (비동기) / Data Sync 스킵 분기 ──
  rect rgb(255, 252, 230)
    Note over EP, S3ML: Cross-Account Data Ingest (Data Account S3 → ML Account S3) — 비동기 패턴 또는 스킵
    alt Data Account S3 신규 데이터 존재 (DATA_SYNCING 필요)
      EP->>COPY: invoke S3 cross-account copy Lambda<br>(dataset_version 지정)
      EP->>DDB: 상태 업데이트 (DATA_SYNCING)
      Note over EP: EP 즉시 반환 — Copy Lambda 완료 대기 없음

      COPY->>S3: manifest 검증 + 데이터 읽기<br>(IAM AssumeRole → Data Account)
      COPY->>S3ML: staging 영역에 저장<br>(prefix: staging/{project}/{run_id}/)

      alt Copy Lambda 전송 성공
        COPY->>EB: ml.data.synced 발행<br>{run_id, s3_dataset_uri, transfer_status}

        EB->>EP: EventBridge Rule → SQS FIFO → Lambda
        EP->>DDB: execution_plan 재조회<br>(run_id 기반, 새 EP 인스턴스)
        DDB-->>EP: execution_plan + state=DATA_SYNCING 확인
        EP->>DDB: 상태 업데이트 (STEP_RUNNING + s3_dataset_uri 저장)

        Note over EP, EB: ★ EP(Execution Planner)가 첫 번째 step 발행<br>(DATA_SYNCING 완료 후)
        EP->>EB: publish ml.preprocess.requested<br>{run_id, step=preprocess,<br>dataset_version, execution_plan, attempt=0}
      else Copy Lambda 전송 실패
        Note over EP, SL: 에러 코드별 재시도 로직 포함 (단순화된 뷰)<br>상세 분기: Run-level_State_Machine.md DATA_SYNCING 상태 전이 참조
        COPY->>EB: ml.data.sync.failed 발행<br>{run_id, error_code, error_msg, copy_job_id}
        EB->>EP: EventBridge Rule → SQS FIFO → Lambda
        EP->>DDB: 상태 업데이트 (FAILED + 에러 저장)
        EP->>CW: Data Sync 실패 알림 푸시
        CW->>SL: Slack 알림<br>(DATA_SYNC_FAILED + run_id)
      end
    else ML Account S3 데이터 최신 (DATA_SYNCING 불필요)
      Note over EP, EB: ★ EP(Execution Planner)가 첫 번째 step 발행<br>(DATA_SYNCING 스킵 — 동일하게 EP가 발행)
      EP->>DDB: 상태 업데이트 (STEP_RUNNING)
      EP->>EB: publish ml.preprocess.requested<br>{run_id, step=preprocess,<br>dataset_version, execution_plan, attempt=0}
    end
  end

  %% ── Preprocess Step ──
  rect rgb(245, 235, 255)
    Note over TRG, SMP: Step 1 — 전처리<br>(Preprocess Trigger Lambda)
    EB->>TRG: EventBridge Rule → SQS FIFO → Lambda
    TRG->>SMP: StartPipelineExecution()<br>{run_id, step=preprocess, s3_dataset_uri}
    SMP->>S3ML: staged 데이터 읽기
    SMP->>SMP: Feature Engineering + Data Validation
    SMP->>S3ML: processed data 저장
    SMP-->>EB: SageMaker Pipeline 완료 이벤트<br>(EventBridge 네이티브)
    Note over TRG, EB: ★ Pipeline Trigger (Lambda)가<br>SageMaker 완료 EventBridge 이벤트 수신 후 발행<br>(SMP 내 custom component가 직접 발행하지 않음)
    EB->>TRG: SageMaker 완료 EventBridge 이벤트 구독
    TRG->>EB: publish ml.step.completed<br>{run_id, step=preprocess, status=SUCCESS,<br>processed_uri, duration_s,<br>idempotency_key={run_id}_preprocess_0}
  end

  %% ── Run Tracker: preprocess 완료 → next_step 판단 → train 발행 ──
  rect rgb(255, 245, 230)
    Note over RT, EB: ★ Run Tracker — execution_plan 조회 후 next_step 결정
    EB->>RT: EventBridge Rule → SQS FIFO → Lambda<br>{step=preprocess}
    RT->>DDB: idempotency_key 중복 확인<br>(이미 처리된 경우 SQS DeleteMessage)
    RT->>DDB: step 상태 업데이트 (PREPROCESS_SUCCEEDED + processed_uri)
    RT->>DDB: execution_plan 조회 → next_step 확인
    DDB-->>RT: next_step = "train"
    RT->>EB: publish ml.train.requested<br>{run_id, step=train,<br>dataset_version, execution_plan, attempt=0}
  end

  %% ── Train Step ──
  rect rgb(245, 235, 255)
    Note over TRG, MR: Step 2 — 학습<br>(Train Trigger Lambda)
    EB->>TRG: EventBridge Rule → SQS FIFO → Lambda
    TRG->>SMP: StartPipelineExecution()<br>{run_id, step=train}
    SMP->>ECR: 이미지 확인 (image_tag)
    SMP->>SM_JOB: SageMaker Training Job 생성 / 모니터링
    SM_JOB->>ECR: 이미지 Pull
    SM_JOB->>S3ML: 학습 데이터 읽기 (processed_uri)
    SM_JOB->>S3ML: 모델 아티팩트 저장
    SM_JOB-->>SMP: job status=Completed
    SMP->>MR: 모델 등록 (Model Package + metrics)
    MR-->>SMP: model_package_arn + model_version
    SMP-->>EB: SageMaker Pipeline 완료 이벤트<br>(EventBridge 네이티브)
    EB->>TRG: SageMaker 완료 EventBridge 이벤트 구독
    TRG->>EB: publish ml.step.completed<br>{run_id, step=train, status=SUCCESS,<br>artifact_uri, model_version, metrics, duration_s,<br>idempotency_key={run_id}_train_0}
  end

  %% ── Run Tracker: train 완료 → next_step 판단 → infer 발행 ──
  rect rgb(255, 245, 230)
    EB->>RT: EventBridge Rule → SQS FIFO → Lambda<br>{step=train}
    RT->>DDB: idempotency_key 중복 확인
    RT->>DDB: 상태 업데이트 (TRAINING_SUCCEEDED + artifact_uri + model_version)
    RT->>DDB: execution_plan 조회 → next_step 확인
    DDB-->>RT: next_step = "infer"
    RT->>EB: publish ml.infer.requested<br>{run_id, step=infer,<br>model_version, execution_plan, attempt=0}
  end

  %% ── Infer Step ──
  rect rgb(245, 235, 255)
    Note over TRG, SM_JOB: Step 3 — 추론 (infer_type으로 Batch / Custom 분기)<br>(Infer Trigger Lambda)
    EB->>TRG: EventBridge Rule → SQS FIFO → Lambda
    TRG->>SMP: StartPipelineExecution()<br>{run_id, step=infer, infer_type}
    SMP->>MR: 모델 참조 (model_package_arn + model_version)
    MR-->>SMP: model artifact path

    alt infer_type = batch
      SMP->>SM_JOB: Batch Transform Job 생성 / 모니터링
      SM_JOB->>S3ML: 추론 결과 저장
      SM_JOB-->>SMP: job status=Completed (result_uri)
    else infer_type = custom
      SMP->>SM_JOB: Processing Job 생성 / 모니터링
      SM_JOB->>S3ML: 결과 / 출력 저장
      SM_JOB-->>SMP: job status=Completed (outputs)
    end

    SMP-->>EB: SageMaker Pipeline 완료 이벤트<br>(EventBridge 네이티브)
    EB->>TRG: SageMaker 완료 EventBridge 이벤트 구독
    TRG->>EB: publish ml.step.completed<br>{run_id, step=infer, status=SUCCESS,<br>result_uri, duration_s,<br>idempotency_key={run_id}_infer_0}
  end

  %% ── Run Tracker: infer 완료 → next_step 판단 → postprocess 발행 ──
  rect rgb(255, 245, 230)
    EB->>RT: EventBridge Rule → SQS FIFO → Lambda<br>{step=infer}
    RT->>DDB: idempotency_key 중복 확인
    RT->>DDB: 상태 업데이트 (INFERENCE_SUCCEEDED + result_uri)
    RT->>DDB: execution_plan 조회 → next_step 확인
    DDB-->>RT: next_step = "postprocess"
    RT->>EB: publish ml.postprocess.requested<br>{run_id, step=postprocess,<br>execution_plan, attempt=0}
  end

  %% ── Postprocess Step (Cross-Account Sync) ──
  rect rgb(245, 235, 255)
    Note over TRG, S3R: Step 4 — 후처리 + Cross-Account 동기화<br>(Postprocess Trigger Lambda)<br>★ SMP 없음 — TRG가 EXP를 직접 동기 ECS Task 호출
    EB->>TRG: EventBridge Rule → SQS FIFO → Lambda
    Note over TRG, EXP: Postprocess Trigger Lambda → EXP 동기 ECS Task 호출<br>(ECS RunTask — sync wait — 완료 응답 대기)
    TRG->>EXP: 동기 ECS Task 호출<br>(sync_target, artifact_uri, result_uri)
    EXP->>SM: Cross-Account Role ARN 조회
    SM-->>EXP: credentials

    alt sync_target = artifacts
      EXP->>S3ML: 모델 아티팩트 읽기
      EXP->>EXP: IAM → AssumeRole (cross-account)
      EXP->>S3A: 멀티파트 업로드<br>(prefix: {model_version}/{run_id}/)
      EXP->>EXP: S3 object 존재 확인 + Checksum 검증
    else sync_target = results
      EXP->>S3ML: 추론 결과 읽기
      EXP->>EXP: IAM → AssumeRole (cross-account)
      EXP->>S3R: 멀티파트 업로드<br>(prefix: {model_version}/{run_id}/)
      EXP->>EXP: S3 object 존재 확인 + Checksum 검증
    else sync_target = both
      Note over EXP: 학습+추론 파이프라인: artifacts → results 순차 동기화
      EXP->>S3ML: 모델 아티팩트 읽기
      EXP->>EXP: IAM → AssumeRole (cross-account)
      EXP->>S3A: 멀티파트 업로드 (artifacts)
      EXP->>EXP: S3 object 존재 확인 + Checksum 검증
      EXP->>S3ML: 추론 결과 읽기
      Note over EXP: STS 세션 토큰 재사용<br>(유효시간 내 재인증 불필요)
      EXP->>S3R: 멀티파트 업로드 (results)
      EXP->>EXP: S3 object 존재 확인 + Checksum 검증
    end

    EXP-->>TRG: 동기화 완료 Task 응답<br>(ALL_SYNCED / ARTIFACT_SYNCED / RESULT_SYNCED)
    Note over TRG, EB: ★ Postprocess Trigger (Lambda)가<br>EXP 동기 Task 응답 수신 후 발행<br>(SMP 없이 TRG가 직접 발행)
    TRG->>EB: publish ml.step.completed<br>{run_id, step=postprocess, status=SUCCESS,<br>idempotency_key={run_id}_postprocess_0}
  end

  %% ── Run Tracker: all steps done ──
  rect rgb(255, 245, 230)
    Note over RT, SL: ★ Run Tracker — execution_plan 소진 확인 → run 완료 처리
    EB->>RT: EventBridge Rule → SQS FIFO → Lambda<br>{step=postprocess}
    RT->>DDB: idempotency_key 중복 확인
    RT->>DDB: execution_plan 조회 → next_step 확인
    DDB-->>RT: next_step = null (all steps done)
    RT->>DDB: 최종 상태 업데이트 (COMPLETED) + run summary 저장
    RT->>EB: publish ml.run.completed<br>{run_id, steps_summary, artifact_uris, final_status=COMPLETED}
    RT->>CW: run summary 푸시<br>(run_id, steps, result, model_version)
    CW->>SL: Slack 알림 (완료 + run_key + 링크)
  end
```
