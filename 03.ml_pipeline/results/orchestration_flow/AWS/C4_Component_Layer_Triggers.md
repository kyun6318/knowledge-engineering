> **Related Documents**: [C4_Component_Layer_SMP.md](./C4_Component_Layer_SMP.md) (SageMaker Pipeline 내부 구조), [C4_Component_Layer_RT.md](./C4_Component_Layer_RT.md) (Run Tracker — Step 완료/실패 수신), [C4_Component_Layer_EXP.md](./C4_Component_Layer_EXP.md) (Cross-Account Exporter — Postprocess 전용)

```mermaid
graph TD
  subgraph Generic_Trigger_Template["Generic Trigger Template (Stateless Lambda)"]
    MSG_DEC["Message Decoder"]
    STRAT_FAC["Pipeline Strategy Factory"]
    PRM_ASM["Parameter Assembler"]
    SMP_SUB["SageMaker Pipeline Submitter"]
  end

  subgraph SMP_Notifier["SMP Status Forwarder (Lambda)"]
    SMP_LSTN["SageMaker State Change Listener"]
    EB_CLIENT["EventBridge PutEvents Client"]
  end

  subgraph Postprocess_Path["Postprocess Trigger (Lambda)"]
    PP_DEC["PP Message Decoder"]
    EXP_CALLER["EXP ECS Task Invoker"]
    PP_EB["PP EventBridge PutEvents Client"]
  end

  %% 입력 (EventBridge: ml.{step}.requested → SQS FIFO → Lambda)
  EventBus_In([EventBridge: ml.{step}.requested]) --> MSG_DEC
  MSG_DEC -->|"1. Extract run_id, step, attempt\n& execution_plan payload"| STRAT_FAC

  %% 전략 패턴 로드 (DynamoDB 제거, Stateless 환경변수 주입)
  ENV[(Environment Variables)] -.->|"inject pipeline ARN & instance type"| STRAT_FAC
  STRAT_FAC -->|"2. construct StepStrategy (Pre/Train/Infer)"| PRM_ASM

  %% 파라미터 조립
  PRM_ASM -->|"3. inject dataset_uri, model_version, etc"| SMP_SUB

  %% 파이프라인 제출 후 즉시 종료
  SMP_SUB -->|"4. StartPipelineExecution()"| External_SMP[(SageMaker Pipelines)]

  %% ── 독립된 비동기 완료 알림 수신 (Postprocess 제외) ──
  External_SMP -.->|"비동기 완료/실패 알림\n(preprocess, train, infer만)"| SMP_LSTN
  SMP_LSTN -->|"extract state"| EB_CLIENT
  EB_CLIENT -->|"publish ml.step.completed/failed"| EventBus_Out[(EventBridge Event Bus)]

  %% ── Postprocess 전용 경로 (SMP Forwarder 미사용) ──
  EventBus_PP([EventBridge: ml.postprocess.requested]) --> PP_DEC
  PP_DEC -->|"if sync_target ≠ none:\nextract sync_target, URIs"| EXP_CALLER
  PP_DEC -.->|"if sync_target = none:\nskip EXP"| PP_EB
  EXP_CALLER -->|"동기 ECS Task 호출\n(ECS RunTask — sync wait)"| External_EXP[(Cross-Account Exporter)]
  External_EXP -.->|"Task 완료/실패 응답"| EXP_CALLER
  EXP_CALLER --> PP_EB
  PP_EB -->|"publish ml.step.completed/failed\n(EXP 응답 기반 or 즉시 발행)"| EventBus_Out

  %% 스타일 적용
  classDef comp fill:#fcf,stroke:#333,stroke-width:2px;
  class MSG_DEC,STRAT_FAC,PRM_ASM,SMP_SUB,SMP_LSTN,EB_CLIENT,PP_DEC,EXP_CALLER,PP_EB comp;
```

### Component Details
1. **Message Decoder**: `ml.{step}.requested` 이벤트 페이로드를 읽어 `run_id`, `step`, 인덱스, `dataset_version` 및 런타임에 필요한 **`execution_plan` 전체**를 Pydantic 스키마로 디코딩합니다.
2. **Pipeline Strategy Factory**: 해당 Step(preprocess, train, infer)에 맞는 실행 템플릿(SageMaker Pipeline ARN, Instance Type, Network 설정 등)을 결정합니다. DB(DynamoDB) 조회를 배제하고 정적 **환경 변수(ENV)**와 Payload만을 결합하여 다형성 인터페이스(`StepStrategy`) 인스턴스를 생성하는 완벽한 무상태(Stateless) 아키텍처입니다.
3. **Parameter Assembler**: `execution_plan`에 들어있는 값(예: infer의 `infer_type=batch`, train의 `image_tag`)과 이전 Step의 아웃풋 URI(예: `s3_dataset_uri`)를 파이프라인 런타임 Parameter로 변환합니다.
4. **SageMaker Pipeline Submitter**: 조립된 최종 명세로 `StartPipelineExecution()`을 호출합니다. 비동기로 작업을 트리거한 후 Ephemeral 컨테이너(Trigger Lambda)는 즉시 가볍게 종료됩니다.
5. **SMP Status Forwarder (분리된 리시버)**: SageMaker Pipeline에서 발생하는 비동기 상태 변경 이벤트(EventBridge 네이티브)를 독립적인 Lambda(`SMP_LSTN`)가 수신합니다. 상태를 포매팅한 후, `EventBridge PutEvents Client`가 Event Bus에 `ml.step.completed` 혹은 `ml.step.failed`로 규격화하여 발행합니다. **※ Postprocess Step은 SageMaker를 사용하지 않으므로 이 Forwarder를 경유하지 않습니다.**
6. **Postprocess Trigger (SMP 미사용 별도 경로)**: Postprocess Step은 SageMaker Pipeline이 아닌 [Cross-Account Exporter(EXP)](./C4_Component_Layer_EXP.md)를 **동기 ECS Task 호출**합니다. ECS RunTask의 완료/실패 상태를 수신한 후, Postprocess Trigger가 직접 `ml.step.completed` 또는 `ml.step.failed`를 발행합니다. **`sync_target=none`인 경우 EXP 호출을 건너뛰고 즉시 `ml.step.completed`를 발행**하는 단축 경로가 존재합니다.
