> **Related Documents**: [C4_Component_Layer_FailureHandling.md](./C4_Component_Layer_FailureHandling.md) (실패 처리 3-Tier 상세), [C4_Component_Layer_EP.md](./C4_Component_Layer_EP.md) (Execution Planner — 첫 Step 발행), [C4_Component_Layer_Triggers.md](./C4_Component_Layer_Triggers.md) (Pipeline Trigger — Step 실행)

```mermaid
graph TD
  subgraph Input_Handlers["Event Handlers"]
    COMPLETION_HDLR["Step Completion Handler"]
    FAIL_HDLR["Step Failure Handler"]
    CANCEL_HDLR["Run Cancel Handler"]
  end

  subgraph Core_Logic["Run State Core (Single Firestore Transaction)"]
    STATE_TXN["Idempotency Check &\nState Transition Transaction"]
  end

  subgraph Outbound["Outbound Actioners"]
    RETRY_ASSESS["Retry Assessor & Backoff Calc"]
    DLQ_ROUTER["DLQ Router (App-Level)"]
    CT_CLIENT["Cloud Tasks Client"]
    VXP_CLIENT["VXP Cancel API Client"]
    PS_CLIENT["Pub/Sub Publisher Client"]
  end

  FS_CLIENT["Firestore Client"]

  %% 입력 흐름 (Pub/Sub Trigger)
  EventBus_Comp([Pub/Sub: ml.step.completed]) --> COMPLETION_HDLR
  EventBus_Fail([Pub/Sub: ml.step.failed]) --> FAIL_HDLR
  EventBus_Cancel([Pub/Sub: ml.run.cancel.requested]) --> CANCEL_HDLR

  %% 단일 트랜잭션: 멱등성 확인 + 상태 업데이트
  COMPLETION_HDLR --> STATE_TXN
  FAIL_HDLR --> STATE_TXN
  
  STATE_TXN -->|"1. begin txn: read run & plan\n2. check idempotency_key"| FS_CLIENT
  
  STATE_TXN -.->|"Already Processed"| ACK([ACK & Exit])
  
  %% ── Step Completed ──
  STATE_TXN -->|"3. update state + outputs\n(Commit Transaction)"| FS_CLIENT
  STATE_TXN -->|"if next_step exists:\ntrigger next_step"| PS_CLIENT
  PS_CLIENT -->|"publish ml.{next}.requested"| EventBus_Out[(Pub/Sub Event Bus)]

  %% ── Run 최종 완료 (next_step = null) ──
  STATE_TXN -.->|"if next_step = null\n(all steps done)"| RUN_COMPLETE([update state=COMPLETED])
  RUN_COMPLETE --> PS_CLIENT
  PS_CLIENT -->|"publish ml.run.completed"| EventBus_Out

  %% ── Step Failed (Failure Handling SM) ──
  STATE_TXN -.->|"New (Failed)"| RETRY_ASSESS
  RETRY_ASSESS -.->|"Exceeds Max or SKIP_RETRY"| DLQ_ROUTER
  RETRY_ASSESS -.->|"Eligible"| CT_CLIENT

  DLQ_ROUTER -->|"publish ml.dead-letter"| PS_CLIENT

  CT_CLIENT -->|"create Delayed Task"| CloudTasks[(Cloud Tasks)]
  CloudTasks -.->|"scheduleTime 후 발행\n(상태가 CANCELLED면 무시됨)"| EventBus_Out

  %% ── Cancel Flow ──
  CANCEL_HDLR -->|"check state"| FS_CLIENT

  %% STEP_RUNNING 분기
  CANCEL_HDLR -.->|"if STEP_RUNNING\n& pipeline_job_id != null"| VXP_CLIENT
  VXP_CLIENT -->|"PipelineJob.cancel"| External_VXP[(Vertex AI Pipelines)]

  %% RETRYING 분기: Cloud Tasks 취소 시도
  CANCEL_HDLR -.->|"if RETRYING\n→ cancel scheduled task"| CT_CLIENT
  CT_CLIENT -.->|"delete task (best-effort)"| CloudTasks

  CANCEL_HDLR -->|"update state=CANCELLING\n+ cancel_requested_at 기록"| FS_CLIENT

  %% CANCELLED 후 ml.run.cancelled 발행
  CANCEL_HDLR -.->|"cancel 확인 후\nstate=CANCELLED"| PS_CLIENT
  PS_CLIENT -->|"publish ml.run.cancelled"| EventBus_Out

  %% cancel 타임아웃/실패 시 FAILED + DLQ
  VXP_CLIENT -.->|"cancel timeout\nor failure"| CANCEL_FAIL([update state=FAILED])
  CANCEL_FAIL --> DLQ_ROUTER

  %% CANCELLING 중 ml.step.failed 수신 → STATE_TXN 내부에서 흡수
  STATE_TXN -.->|"if state=CANCELLING\n→ retry 없이 CANCELLED 흡수"| PS_CLIENT

  %% 이미 완료/실패/취소 상태
  CANCEL_HDLR -.->|"if state ∉ {STEP_RUNNING, RETRYING}\n→ audit log & ACK"| ACK_CANCEL([Audit & ACK])


  %% 스타일 적용
  classDef comp fill:#bfb,stroke:#333,stroke-width:2px;
  class COMPLETION_HDLR,FAIL_HDLR,CANCEL_HDLR,STATE_TXN,RETRY_ASSESS,DLQ_ROUTER,CT_CLIENT,VXP_CLIENT,PS_CLIENT,FS_CLIENT comp;
```

### Component Details
1. **Idempotency Check & State Transition Transaction**: 모든 인입 메시지(`ml.step.completed/failed`)의 `idempotency_key` 확인과 `execution_plan`에 따른 `next_step` 탐색 및 `state` 업데이트를 **단일 Firestore 트랜잭션** 내에서 수행합니다. 멱등성 확인(read → check processed_events)과 상태 전이(write)가 동일 트랜잭션에 포함되어 TOCTOU(Time-Of-Check-to-Time-Of-Use) 경합이 발생하지 않습니다.
2. **Run 완료 처리**: `next_step = null`(모든 step 소진)이면 `state=COMPLETED`로 업데이트하고, `Pub/Sub Publisher Client`를 통해 `ml.run.completed` 이벤트를 발행합니다. (v3 `Execution_Sequence_default.md` L214-225 대응)
3. **Retry Assessor**: 실패 시 트랜잭션 내에서 읽어온 `max_attempts` 속성과 `retry_policy`를 기반으로 재시도 적격성을 판단하고 Exponential Backoff 지연 시간을 계산합니다. (상세 흐름: [FailureHandling 문서](./C4_Component_Layer_FailureHandling.md) 참조)
4. **Cloud Tasks Client**: 산출된 지연 시간(`scheduleTime`)을 바탕으로 Cloud Tasks에 재시도 이벤트 발행을 예약합니다. Cancel이 발생하더라도 명시적으로 Task를 지우지 않고, 나중에 Task가 실행될 때 상태 머신이 `CANCELLED`를 확인하고 자연스럽게 무시하는 '상태 기반 무력화' 패턴을 사용합니다.
5. **Run Cancel Handler**: CANCELLING 전이 시 `cancel_requested_at` 타임스탬프를 기록하며(Race Condition 해소용), 4가지 분기를 수행합니다:
   - **`state = STEP_RUNNING`**: `pipeline_job_id`가 존재하면 VXP Cancel API Client로 Vertex AI Pipeline Job을 중지시킨 후 `CANCELLING → CANCELLED` 전이. **cancel 타임아웃(30s 이내 미응답) 또는 cancel 자체 실패 시** `state=FAILED`로 전이하고 `ml.dead-letter`를 발행합니다.
   - **`state = RETRYING`**: Cloud Tasks의 예약된 재시도 task를 삭제 시도(best-effort)한 후 `CANCELLING` 전이. `pipeline_job_id`가 이미 존재하면 추가로 VXP cancel도 수행.
   - **`state = CANCELLING` (Race Condition)**: CANCELLING 상태에서 `ml.step.failed`를 수신하면, `step_failed.timestamp`와 무관하게 **retry 없이 CANCELLED로 흡수**합니다 (운영자 cancel 의도 우선 정책).
   - **`state ∉ {STEP_RUNNING, RETRYING}`**: 이미 완료/실패/취소된 Run이므로 `audit_events`에 기록 후 ACK.
   - CANCELLED 확인 후 `Pub/Sub Publisher Client`를 통해 `ml.run.cancelled`를 발행합니다.
6. **VXP Cancel API Client**: `run.pipeline_job_id`가 존재하는 경우(Postprocess 제외)에만 조건부로 Vertex AI Pipeline Job을 직접 중지시킵니다.
7. **DLQ Router (App-Level)**: 재시도 임계치가 초과된 실패 건 또는 cancel 타임아웃 건을 어플리케이션 레벨의 DLQ 토픽(`ml.dead-letter`)으로 원본 메시지와 함께 라우팅합니다.
