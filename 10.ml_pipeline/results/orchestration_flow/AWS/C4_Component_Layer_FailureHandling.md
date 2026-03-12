> **Related Documents**: [C4_Component_Layer_RT.md](./C4_Component_Layer_RT.md) (Run Tracker — Failure Handler가 이 서브프로세스를 호출)

```mermaid
graph TD
  subgraph Retry_Logic["Immediate Retry Tier"]
    RETRY_ASSESS["Retry Assessor"]
    EB_SCHED_CLIENT["EventBridge Scheduler Client"]
  end

  subgraph Dead_Letter_Logic["DLQ Routing Tier"]
    DLQ_ROUTER["App-Level DLQ Router"]
    LOG_CLIENT["Structured Error Logger"]
  end

  subgraph Alert_Manual_Logic["Alert & Manual Action Tier"]
    CW_ALARM["CloudWatch Alarm (AWS Native)"]
    MANUAL_INVOKER["Manual Retry Invoker"]
  end

  %% 입력 흐름 (Run Tracker 내부 컴포넌트 호출)
  FAIL_HDLR([Step Failure Handler]) -->|"eval retry"| RETRY_ASSESS

  %% 1. Immediate Retry Tier
  RETRY_ASSESS -.->|"if Eligible"| EB_SCHED_CLIENT
  EB_SCHED_CLIENT -->|"create one-time schedule\n(지연 재시도)"| EventSched[(EventBridge Scheduler)]
  EB_SCHED_CLIENT -.->|"if schedule creation fails\n(인프라 오류)"| DLQ_ROUTER

  %% 2. DLQ Routing Tier
  RETRY_ASSESS -.->|"if Exceeds Max / SKIP_RETRY"| DLQ_ROUTER
  DLQ_ROUTER -->|"publish ml.dead-letter"| EventBus[(EventBridge Event Bus)]

  %% 단순 로깅으로 전환
  RETRY_ASSESS -.->|"log failure details"| LOG_CLIENT
  LOG_CLIENT -->|"stdout JSON"| CWLogs[(CloudWatch Logs)]

  %% 3. Alert Tier (AWS Managed)
  CWLogs -.->|"Metric Filter on severity=ERROR"| CW_ALARM
  CW_ALARM -->|"Notify via SNS"| Slack[(Slack Alert)]

  %% 4. Manual Retry Flow (수동 액션)
  Operator([DE-MLE Operator]) -.->|"read alert"| Slack
  Operator -->|"invoke manual retry"| MANUAL_INVOKER
  Operator -.->|"terminate run\n(재시도 포기)"| TERMINATED([update state=TERMINATED\nDynamoDB 이력 보존])
  MANUAL_INVOKER -->|"reset attempt=0\nupdate state=STEP_RUNNING"| DDB_CLIENT[(DynamoDB)]
  MANUAL_INVOKER -->|"Push to Execution Queue"| EB_REQ([EventBridge: ml.{step}.requested])

  %% 스타일 적용
  classDef comp fill:#fcc,stroke:#333,stroke-width:2px;
  class RETRY_ASSESS,EB_SCHED_CLIENT,DLQ_ROUTER,LOG_CLIENT,CW_ALARM,MANUAL_INVOKER comp;
```

### Component Details
*※ 참고: 이 다이어그램은 Run Tracker의 Failure Handling 서브프로세스 및 관련 컴포넌트를 논리적으로 분리하여 설명합니다.*

1. **Retry Assessor**: `ml.step.failed` 이벤트 수신 후 `max_attempts` 및 `retry_policy`를 평가하는 **1단계 방어선**입니다. Exponential Backoff 수식을 통해 지연 시간을 계산합니다.
2. **EventBridge Scheduler Client**: Assessor가 재시도를 결정했을 때, 안전한 지연(Delay)을 주기 위해 EventBridge Scheduler에 일회성 스케줄(`ScheduleExpression: at(datetime)`)을 생성합니다. 설정된 시간이 지나면 EventBridge Scheduler가 다시 Event Bus로 이벤트를 발행합니다. **EventBridge Schedule 생성 자체가 실패(인프라 오류)하면 즉시 DLQ Router로 전달**하여 `state=FAILED` 전이 및 `ml.dead-letter` 발행을 트리거합니다.
3. **App-Level DLQ Router**: 재시도 횟수를 모두 소진했거나 `SKIP_RETRY` 정책인 경우 동작하는 **2단계 방어선**입니다. 이벤트 원본과 시각을 유지한 채 순수하게 `ml.dead-letter` 이벤트로 원본 메시지를 라우팅(포워딩)하는 단일 책임(SRP)만을 수행합니다.
4. **Structured Error Logger & CloudWatch Alarm**: 실패가 확정되면 애플리케이션 컴포넌트는 오직 JSON 포맷 구조화 에러 로그(`stdout`)만 발생시킵니다. 이후 AWS Native 인프라 기능(CloudWatch Logs Metric Filter → CloudWatch Alarm → SNS)이 이 로그를 감지하여 자동으로 Slack 등으로 에러를 통보합니다. 불필요한 알림 발송용 자체 컴포넌트 로직이 제거된 클라우드 네이티브 설계입니다.
5. **Manual Retry Invoker**: **3단계 방어선**. 알림을 확인한 운영자가 DLQ 상태의 Run을 다시 복구하려 할 때(API 등), `run.attempt=0`, `state=STEP_RUNNING`으로 DynamoDB를 업데이트하고, **RT의 일반 Retry 경로를 우회(Bypass)**하여 파이프라인 트리거 대상인 `ml.{step}.requested` 이벤트를 EventBridge에 직접 발행합니다. 우회하는 이유는 DLQ 상태(FAILED)의 Run은 RT State Machine의 정상 Retry 진입 조건(`state=STEP_RUNNING`)을 만족하지 않기 때문이며, attempt를 0으로 리셋함으로써 재시도 횟수 초과에 의한 즉시 DLQ 재라우팅 무한루프를 방지합니다. 운영자가 재시도 대신 **최종 종료를 선택**할 경우, `state=TERMINATED`로 DynamoDB를 업데이트하여 이력을 보존하고 Run을 종료합니다.
