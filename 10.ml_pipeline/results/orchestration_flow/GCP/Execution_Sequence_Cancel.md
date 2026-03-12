```mermaid
sequenceDiagram
  autonumber

  participant DE     as Operator / DE-MLE
  participant RunAPI as Run Request API<br>(Cloud Run)
  participant PS     as Cloud Pub/Sub<br>(Event Bus)
  participant RT     as Run Tracker<br>(Cloud Function)
  participant FS     as Firestore
  participant CT     as Cloud Tasks
  participant VXP    as Vertex AI Pipelines
  participant MON    as Cloud Monitoring
  participant SL     as Slack

  Note over DE, SL: Run 취소 시나리오 (STEP_RUNNING 또는 RETRYING 상태에서)

  %% ── Cancel 요청 ──
  rect rgb(255, 240, 240)
    Note over DE, RunAPI: 운영자가 잘못된 config 등을 발견하여 취소 요청
    DE->>RunAPI: POST /runs/{run_id}/cancel
    RunAPI->>RunAPI: AuthN/AuthZ + run_id 유효성 확인
    RunAPI->>PS: publish ml.run.cancel.requested<br>{run_id, requested_by, reason}
  end

  %% ── Run Tracker Cancel 처리 ──
  rect rgb(255, 245, 230)
    PS->>RT: subscribe ml.run.cancel.requested
    RT->>FS: run state 조회
    FS-->>RT: state + current_step + pipeline_job_id

    alt state = STEP_RUNNING
      RT->>FS: 상태 업데이트 (CANCELLING)<br>+ cancel_requested_at 기록 (Race Condition 기준)
      RT->>VXP: Pipeline Job cancel API 호출<br>(run.pipeline_job_id)

      alt cancel 성공 (Pipeline CANCELLED 감지)
        VXP-->>RT: job status = CANCELLED
        RT->>FS: 상태 업데이트 (CANCELLED)<br>+ cancel summary 저장<br>{cancelled_step, cancelled_by, reason}
        RT->>PS: publish ml.run.cancelled<br>{run_id, cancelled_step,<br>cancelled_by, reason}
        RT->>MON: cancel summary 푸시
        MON->>SL: Slack 알림<br>(CANCELLED + run_id + step<br>+ cancelled_by)
      else cancel 타임아웃 (30s 이내 미응답)
        Note over VXP: Pipeline cancel 미응답
        RT->>FS: 상태 업데이트 (FAILED)<br>+ error_code = CANCEL_TIMEOUT
        RT->>PS: publish ml.dead-letter<br>{original_topic=ml.run.cancel.requested,<br>original_message (전체 보존),<br>attempt=1,<br>first_receive_time (Pub/Sub message.publishTime)}
        RT->>MON: cancel 실패 알림
        MON->>SL: Slack 알림<br>(CANCEL_FAILED + run_id)
      end

    else state = RETRYING
      Note over RT: RETRYING 중 cancel 요청<br>Cloud Tasks scheduled task 취소 시도 후 CANCELLING 전이
      RT->>CT: Cloud Tasks scheduled task 취소 요청<br>(run_id에 해당하는 지연 task)
      Note over CT: 취소 성공 여부와 무관하게 CANCELLING 전이<br>(이미 실행된 경우 VXP cancel API로 처리)
      RT->>FS: 상태 업데이트 (CANCELLING)<br>+ cancel_requested_at 기록

      alt pipeline_job_id 존재 (Pipeline 이미 시작된 경우)
        RT->>VXP: Pipeline Job cancel API 호출<br>(run.pipeline_job_id)
        VXP-->>RT: job status = CANCELLED
        RT->>FS: 상태 업데이트 (CANCELLED)<br>+ cancel summary 저장
        RT->>PS: publish ml.run.cancelled<br>{run_id, cancelled_step,<br>cancelled_by, reason}
        RT->>MON: cancel summary 푸시
        MON->>SL: Slack 알림<br>(CANCELLED + run_id + step)
      else pipeline_job_id 없음 (Cloud Tasks 취소 성공, Pipeline 미시작)
        RT->>FS: 상태 업데이트 (CANCELLED)<br>(Pipeline job 없으므로 cancel API 불필요)
        RT->>PS: publish ml.run.cancelled<br>{run_id, cancelled_step=null,<br>cancelled_by, reason}
        RT->>MON: cancel summary 푸시
        MON->>SL: Slack 알림<br>(CANCELLED + run_id + retry_cancelled)
      end

    else state ≠ STEP_RUNNING, RETRYING (이미 완료/실패/취소)
      RT->>FS: cancel 무시 기록<br>(audit_events collection)<br>{event_type=CANCEL_IGNORED, run_id,<br>reason="run already " + state,<br>requested_by, timestamp}
      Note over RT: 이미 COMPLETED/FAILED/CANCELLED인 run은<br>cancel 불가 → 무시 후 ACK
    end
  end
```
