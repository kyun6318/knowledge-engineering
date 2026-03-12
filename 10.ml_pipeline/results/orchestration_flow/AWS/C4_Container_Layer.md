```mermaid
graph TD
  subgraph People["People"]
    DE["Operator / DE-MLE"]
    Biz["Service Owner / PM"]
  end

  subgraph DataAcc["AWS Data Account"]
    ETL["Data Platform<br>(ETL / Feature Engineering)"]
    S3Train["S3 — Training Dataset"]
    Stream["Streaming Data<br>(Kinesis / Kafka)"]
    EB_DATA["Amazon EventBridge<br>(Data Account)"]
  end

  subgraph MLAcc["AWS ML Account"]
    EventSched["EventBridge Scheduler"]
    RunAPI["Run Request API<br>(API Gateway + Lambda)"]

    subgraph EventBus["Event Bus (EventBridge + SQS FIFO)"]
      EVENTS["Events<br>(→ Topic 명세서 참조)"]
    end

    EP["Execution Planner<br>(Lambda)"]
    RT["Run Tracker<br>(Lambda)"]
    EB_SCHED["EventBridge Scheduler<br>(지연 발행)"]
    COPY_LAMBDA["S3 Cross-Account Copy Lambda<br>(Data Account S3 → ML Account S3)"]

    subgraph PipelineTriggers["Pipeline Triggers (독립 Lambda × 4)"]
      TRG_PP["Preprocess Trigger<br>(Lambda)"]
      TRG_TR["Train Trigger<br>(Lambda)"]
      TRG_IN["Infer Trigger<br>(Lambda)"]
      TRG_PO["Postprocess Trigger<br>(Lambda)<br>★ EXP를 동기 ECS Task 호출 후<br>ml.step.completed 발행"]
    end

    subgraph Pipelines["SageMaker Pipelines"]
      P["전처리 / 학습 / 추론<br>(SageMaker Orchestration)"]
    end

    DDB["DynamoDB<br>(ml-run / ml-execution-plan / ml-lock /<br>ml-duplicate-events / ml-audit-events /<br>ml-processed-events)"]
    SM["Secrets Manager<br>(Cross-Account Role ARN)"]
    S3ML["S3 ML Account<br>(staging / artifacts / results)"]
    ECR["Amazon ECR"]
    MR["SageMaker Model Registry"]
    EXPORTER["Cross-Account Exporter<br>(ECS Fargate Task)<br>★ Postprocess Trigger가 동기 호출"]
    CW["Amazon CloudWatch"]
  end

  subgraph ServiceDom["AWS Service Account"]
    S3Art["S3 — Model Artifacts"]
    S3Res["S3 — Inference Results"]
    API["Serving API"]
    SDB["Service DB"]
    ResultIngest["Result Ingest Job<br>(Lambda / ECS Task)"]
    Obs["Observability<br>(CloudWatch / Grafana)"]
  end

  %% AWS Data Account
  ETL -->|write| S3Train
  S3Train -->|S3 Event| EB_DATA
  Stream -.->|publish (planned)| EB_DATA

  %% 진입점 → Event Bus (모두 RunAPI 경유)
  EB_DATA -->|"HTTPS POST<br>(API Destination + Connection<br>SigV4 IAM Auth)"| RunAPI
  DE -->|trigger| RunAPI
  Biz -.->|trigger (planned)| RunAPI
  EventSched -->|HTTP POST| RunAPI
  RunAPI -->|publish| EventBus

  %% Cancel 흐름 (RunAPI 경유, Operator 전용 — Biz 권한 없음)
  DE -->|cancel API| RunAPI
  RunAPI -->|"publish<br>ml.run.cancel.requested"| EventBus

  %% Event Bus ↔ Controllers
  EventBus -->|trigger| EP
  EP -->|publish| EventBus
  EventBus -->|subscribe| RT
  RT -->|publish| EventBus

  %% EventBridge Scheduler (지연 발행)
  RT -->|지연 schedule 생성| EB_SCHED
  EB_SCHED -->|"scheduled time 후 publish"| EventBus

  %% Event Bus → Pipeline Triggers (step별 독립 트리거)
  EventBus -->|"ml.preprocess.requested<br>EventBridge Rule → SQS FIFO"| TRG_PP
  EventBus -->|"ml.train.requested<br>EventBridge Rule → SQS FIFO"| TRG_TR
  EventBus -->|"ml.infer.requested<br>EventBridge Rule → SQS FIFO"| TRG_IN
  EventBus -->|"ml.postprocess.requested<br>EventBridge Rule → SQS FIFO"| TRG_PO

  %% Pipeline Triggers → SageMaker Pipelines (preprocess/train/infer)
  TRG_PP -->|StartPipelineExecution| P
  TRG_TR -->|StartPipelineExecution| P
  TRG_IN -->|StartPipelineExecution| P

  %% Postprocess Trigger → EXP (동기 ECS Task 호출)
  TRG_PO -->|"동기 ECS Task 호출<br>(ECS RunTask — sync wait)"| EXPORTER
  EXPORTER -.->|"완료 응답"| TRG_PO
  TRG_PO -->|"publish ml.step.completed<br>(EXP 응답 수신 후)"| EventBus

  %% Pipelines → Event Bus (SageMaker 상태 변경 → Pipeline Trigger 수신)
  P -->|"SageMaker 상태 변경 이벤트<br>(EventBridge 네이티브)"| EventBus
  EventBus -->|"완료 이벤트 수신<br>(Pipeline Trigger가 구독)"| TRG_PP
  EventBus -->|"완료 이벤트 수신<br>(Pipeline Trigger가 구독)"| TRG_TR
  EventBus -->|"완료 이벤트 수신<br>(Pipeline Trigger가 구독)"| TRG_IN
  TRG_PP -->|"publish ml.step.completed/failed"| EventBus
  TRG_TR -->|"publish ml.step.completed/failed"| EventBus
  TRG_IN -->|"publish ml.step.completed/failed"| EventBus

  %% Controllers → DynamoDB (EP, RT, RunAPI 모두 접근)
  EP -->|R/W| DDB
  RT -->|R/W| DDB
  RunAPI -->|R/W| DDB

  %% Pipelines → AWS Services
  P -->|R/W| S3ML
  P -->|register / ref| MR
  P -.->|pull image| ECR

  %% Data Sync (비동기: S3 Cross-Account Copy)
  EP -->|invoke copy Lambda| COPY_LAMBDA
  COPY_LAMBDA -->|"IAM AssumeRole → read"| S3Train
  COPY_LAMBDA -->|write staging| S3ML
  COPY_LAMBDA -->|"완료/실패 이벤트 발행"| EventBus

  %% Cross-Account Export (EXP 내부)
  EXPORTER -->|read config| SM
  EXPORTER -->|read| S3ML
  EXPORTER -->|"IAM AssumeRole → upload"| S3Art & S3Res

  %% Observability
  RT -->|run summary| Obs & CW

  %% AWS Service Account
  API -->|read| S3Art
  API <-->|R/W| SDB
  S3Res -->|S3 Event| ResultIngest
  ResultIngest -->|ingest| SDB

  %% ── Topic 명세서 (별도 문서로 관리) ──
  %% ml.run.requested
  %% ml.{step}.requested  (preprocess / train / infer / postprocess)
  %% ml.step.completed
  %% ml.step.failed
  %% ml.dead-letter
  %% ml.run.completed
  %% ml.run.cancelled
  %% ml.run.cancel.requested
  %% ml.data.synced
  %% ml.data.sync.failed
```
