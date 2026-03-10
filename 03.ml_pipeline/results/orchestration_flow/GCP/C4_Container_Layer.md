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
    EB_AWS["Amazon EventBridge"]
  end

  subgraph GCPEnv["GCP ML Environment"]
    CloudSched["Cloud Scheduler"]
    RunAPI["Run Request API<br>(Cloud Run)"]

    subgraph EventBus["Event Bus (Pub/Sub)"]
      TOPICS["Topics<br>(→ Topic 명세서 참조)"]
    end

    EP["Execution Planner<br>(Cloud Function)"]
    RT["Run Tracker<br>(Cloud Function)"]
    CT["Cloud Tasks<br>(지연 발행)"]
    EA["Eventarc<br>(STS 완료 이벤트 라우팅)"]

    subgraph PipelineTriggers["Pipeline Triggers (독립 Cloud Functions × 4)"]
      TRG_PP["Preprocess Trigger<br>(Cloud Function)"]
      TRG_TR["Train Trigger<br>(Cloud Function)"]
      TRG_IN["Infer Trigger<br>(Cloud Function)"]
      TRG_PO["Postprocess Trigger<br>(Cloud Function)<br>★ EXP를 동기 HTTP 호출 후<br>ml.step.completed 발행"]
    end

    subgraph Pipelines["Vertex AI Pipelines"]
      P["전처리 / 학습 / 추론<br>(Kubeflow Orchestration)"]
    end

    FS["Firestore<br>(run / execution_plan / lock / duplicate_events / audit_events)"]
    SM["Secret Manager<br>(WIF Role ARN + externalId)"]
    GCS["Google Cloud Storage<br>(staging / artifacts / results)"]
    AR["Artifact Registry"]
    MR["Vertex AI Model Registry"]
    XFER["Storage Transfer Service<br>(S3 → GCS)"]
    EXPORTER["Cross-Cloud Exporter<br>(Cloud Run Job)<br>★ Postprocess Trigger가 동기 HTTP 호출"]
    MON["Cloud Monitoring"]
  end

  subgraph ServiceDom["AWS Service Domain"]
    S3Art["S3 — Model Artifacts"]
    S3Res["S3 — Inference Results"]
    API["Serving API"]
    SDB["Service DB"]
    ResultIngest["Result Ingest Job<br>(Lambda / ECS Task)"]
    Obs["Observability<br>(CloudWatch / Grafana)"]
  end

  %% AWS Data Account
  ETL -->|write| S3Train
  S3Train -->|S3 Event| EB_AWS
  Stream -.->|publish (planned)| EB_AWS

  %% 진입점 → Event Bus (모두 RunAPI 경유)
  EB_AWS -->|"HTTPS POST<br>(API Destination + Connection<br>OIDC token)"| RunAPI
  DE -->|trigger| RunAPI
  Biz -.->|trigger (planned)| RunAPI
  CloudSched -->|HTTP POST| RunAPI
  RunAPI -->|publish| EventBus

  %% Cancel 흐름 (RunAPI 경유, Operator 전용 — Biz 권한 없음)
  DE -->|cancel API| RunAPI
  RunAPI -->|"publish<br>ml.run.cancel.requested"| EventBus

  %% Event Bus ↔ Controllers
  EventBus -->|trigger| EP
  EP -->|publish| EventBus
  EventBus -->|subscribe| RT
  RT -->|publish| EventBus

  %% Cloud Tasks (지연 발행)
  RT -->|지연 task 생성| CT
  CT -->|scheduleTime 후 publish| EventBus

  %% Event Bus → Pipeline Triggers (step별 독립 트리거)
  EventBus -->|"ml.preprocess.requested<br>Pub/Sub trigger"| TRG_PP
  EventBus -->|"ml.train.requested<br>Pub/Sub trigger"| TRG_TR
  EventBus -->|"ml.infer.requested<br>Pub/Sub trigger"| TRG_IN
  EventBus -->|"ml.postprocess.requested<br>Pub/Sub trigger"| TRG_PO

  %% Pipeline Triggers → Vertex AI Pipelines (preprocess/train/infer)
  TRG_PP -->|PipelineJob.submit| P
  TRG_TR -->|PipelineJob.submit| P
  TRG_IN -->|PipelineJob.submit| P

  %% Postprocess Trigger → EXP (동기 HTTP 호출)
  TRG_PO -->|"동기 HTTP 호출<br>(Cloud Run Job invoke)"| EXPORTER
  EXPORTER -.->|"완료 응답"| TRG_PO
  TRG_PO -->|"publish ml.step.completed<br>(EXP 응답 수신 후)"| EventBus

  %% Pipelines → Event Bus (Vertex AI 상태 변경 → Pipeline Trigger 수신)
  P -->|"Vertex AI 상태 변경 이벤트<br>(Pub/Sub notification)"| EventBus
  EventBus -->|"완료 이벤트 수신<br>(Pipeline Trigger가 구독)"| TRG_PP
  EventBus -->|"완료 이벤트 수신<br>(Pipeline Trigger가 구독)"| TRG_TR
  EventBus -->|"완료 이벤트 수신<br>(Pipeline Trigger가 구독)"| TRG_IN
  TRG_PP -->|"publish ml.step.completed/failed"| EventBus
  TRG_TR -->|"publish ml.step.completed/failed"| EventBus
  TRG_IN -->|"publish ml.step.completed/failed"| EventBus

  %% Controllers → Firestore (EP, RT, RunAPI 모두 접근)
  EP -->|R/W| FS
  RT -->|R/W| FS
  RunAPI -->|R/W| FS

  %% Pipelines → GCP Services
  P -->|R/W| GCS
  P -->|register / ref| MR
  P -.->|pull image| AR

  %% Data Sync (비동기: Eventarc 경유)
  EP -->|trigger transfer| XFER
  XFER -->|read| S3Train
  XFER -->|write staging| GCS
  XFER -->|완료/실패 이벤트| EA
  EA -->|Eventarc → Pub/Sub| EventBus

  %% Cross-Cloud Export (EXP 내부)
  EXPORTER -->|read config| SM
  EXPORTER -->|read| GCS
  EXPORTER -->|upload| S3Art & S3Res

  %% Observability
  RT -->|run summary| Obs & MON

  %% AWS Service Domain
  API -->|read| S3Art
  API <-->|R/W| SDB
  S3Res -->|S3 Event| ResultIngest
  ResultIngest -->|ingest| SDB

  %% ── Topic 명세서 (별도 문서로 관리 권장) ──
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
