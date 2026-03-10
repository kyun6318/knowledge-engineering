> **Related Documents**: [C4_Component_Layer_VXP.md](./C4_Component_Layer_VXP.md) (Kubeflow Pipeline 내부 구조), [C4_Component_Layer_RT.md](./C4_Component_Layer_RT.md) (Run Tracker — Step 완료/실패 수신), [C4_Component_Layer_EXP.md](./C4_Component_Layer_EXP.md) (Cross-Cloud Exporter — Postprocess 전용)

```mermaid
graph TD
  subgraph Generic_Trigger_Template["Generic Trigger Template (Stateless Cloud Function)"]
    MSG_DEC["Message Decoder"]
    STRAT_FAC["Pipeline Strategy Factory"]
    PRM_ASM["Parameter Assembler"]
    VXP_SUB["Vertex AI Submitter"]
  end

  subgraph VXP_Notifier["VXP Status Forwarder (Cloud Function)"]
    VXP_LSTN["Vertex AI State Change Listener"]
    PS_CLIENT["Pub/Sub Publisher Client"]
  end

  subgraph Postprocess_Path["Postprocess Trigger (Cloud Function)"]
    PP_DEC["PP Message Decoder"]
    EXP_CALLER["EXP Sync HTTP Caller"]
    PP_PS["PP Pub/Sub Publisher Client"]
  end

  %% 입력 (Pub/Sub: ml.{step}.requested)
  EventBus_In([Pub/Sub: ml.{step}.requested]) --> MSG_DEC
  MSG_DEC -->|"1. Extract run_id, step, attempt\n& execution_plan payload"| STRAT_FAC
  
  %% 전략 패턴 로드 (Firestore 제거, Stateless 환경변수 주입)
  ENV[(Environment Variables)] -.->|"inject template URI & machine spec"| STRAT_FAC
  STRAT_FAC -->|"2. construct StepStrategy (Pre/Train/Infer)"| PRM_ASM
  
  %% 파라미터 조립
  PRM_ASM -->|"3. inject dataset_uri, model_version, etc"| VXP_SUB
  
  %% 파이프라인/작업 제출 후 즉시 종료
  VXP_SUB -->|"4. PipelineJob.submit()"| External_VXP[(Vertex AI Pipelines)]

  %% ── 독립된 비동기 완료 알림 수신 (Postprocess 제외) ──
  External_VXP -.->|"비동기 완료/실패 알림\n(preprocess, train, infer만)"| VXP_LSTN
  VXP_LSTN -->|"extract state"| PS_CLIENT
  PS_CLIENT -->|"publish ml.step.completed/failed"| EventBus_Out[(Pub/Sub Event Bus)]

  %% ── Postprocess 전용 경로 (VXP Forwarder 미사용) ──
  EventBus_PP([Pub/Sub: ml.postprocess.requested]) --> PP_DEC
  PP_DEC -->|"if sync_target ≠ none:\nextract sync_target, URIs"| EXP_CALLER
  PP_DEC -.->|"if sync_target = none:\nskip EXP"| PP_PS
  EXP_CALLER -->|"동기 HTTP 호출\n(Cloud Run Job invoke)"| External_EXP[(Cross-Cloud Exporter)]
  External_EXP -.->|"HTTP 200/500 응답"| EXP_CALLER
  EXP_CALLER --> PP_PS
  PP_PS -->|"publish ml.step.completed/failed\n(EXP 응답 기반 or 즉시 발행)"| EventBus_Out

  %% 스타일 적용
  classDef comp fill:#fcf,stroke:#333,stroke-width:2px;
  class MSG_DEC,STRAT_FAC,PRM_ASM,VXP_SUB,VXP_LSTN,PS_CLIENT,PP_DEC,EXP_CALLER,PP_PS comp;
```

### Component Details
1. **Message Decoder**: `ml.{step}.requested` 이벤트 페이로드를 읽어 `run_id`, `step`, 인덱스, `dataset_version` 및 런타임에 필요한 **`execution_plan` 전체**를 Pydantic 스키마로 디코딩합니다.
2. **Pipeline Strategy Factory**: 해당 Step(preprocess, train, infer)에 맞는 실행 템플릿(Kubeflow Container URI, Machine Type, Network 설정 등)을 결정합니다. DB(Firestore) 조회를 배제하고 정적 **환경 변수(ENV)**와 Payload만을 결합하여 다형성 인터페이스(`StepStrategy`) 인스턴스를 생성하는 완벽한 무상태(Stateless) 아키텍처입니다.
3. **Parameter Assembler**: `execution_plan`에 들어있는 값(예: infer의 `infer_type=batch`, train의 `image_tag`)과 이전 Step의 아웃풋 URI(예: `gcs_dataset_uri`)를 파이프라인 런타임 Argument로 변환합니다.
4. **Vertex AI Submitter**: 조립된 최종 명세로 `PipelineJob.submit()`을 호출합니다. 비동기로 작업을 트리거한 후 Ephemeral 컨테이너(Trigger Cloud Function)는 즉시 가볍게 종료됩니다.
5. **VXP Status Forwarder (분리된 리시버)**: Vertex AI 인프라에서 발생하는 수 시간 뒤의 비동기 상태 변경 알림(완료/오류)을 독립적인 컴포넌트(`VXP_LSTN`)가 수신합니다. 상태를 포매팅한 후, `Pub/Sub Publisher Client`가 Event Bus에 `ml.step.completed` 혹은 `ml.step.failed`로 규격화하여 발행합니다. **※ Postprocess Step은 VXP를 사용하지 않으므로 이 Forwarder를 경유하지 않습니다.**
6. **Postprocess Trigger (VXP 미사용 별도 경로)**: Postprocess Step은 Vertex AI Pipeline이 아닌 [Cross-Cloud Exporter(EXP)](./C4_Component_Layer_EXP.md)를 **동기 HTTP 호출**합니다. EXP의 HTTP 응답(200/500)을 수신한 후, Postprocess Trigger가 직접 `ml.step.completed` 또는 `ml.step.failed`를 발행합니다. **`sync_target=none`인 경우 EXP 호출을 건너뛰고 즉시 `ml.step.completed`를 발행**하는 단축 경로가 존재합니다.
