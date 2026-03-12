# v3 설계 수정 내역

**작성일**: 2026-02-28
**기준**: Design_Review.md (E1~E5, O1~O2, I1~I5)

---

## 수정 내역 표

| ID | 수정 대상 파일 | 수정 이유 | 수정 전 | 수정 후 |
|---|---|---|---|---|
| **E2** | `Run-level_State_Machine.md` | CANCELLING 상태에서 `ml.step.failed` 수신 시 timestamp < cancel_requested_at 조건에서 FAILED + retry 발생. 운영자 cancel 의도가 무시됨. CANCELLING은 terminal-directed 상태이므로 모든 step 실패를 CANCELLED로 흡수해야 함. | `CANCELLING --> FAILED : ml.step.failed 수신\n★ step_failed.timestamp < cancel_requested_at\n→ cancel 이전에 발생한 실패\n(retry 정책 정상 적용)` | `CANCELLING --> CANCELLED : ml.step.failed 수신\n★ step_failed.timestamp < cancel_requested_at\n→ cancel 이전 실패지만 cancel 의도 우선\n(retry 없이 CANCELLED 처리)` |
| **E2** | `Run-level_State_Machine.md` | Race Condition 주석에 CANCELLING의 terminal-directed 특성 명시. | (주석 없음) | `%% ★ CANCELLING은 terminal-directed 상태: 모든 ml.step.failed를 CANCELLED로 흡수` 주석 추가 |
| **E3** | `Step-level_State_Machine_(preprocess).md` | TIMED_OUT 후 Vertex AI Pipeline Job이 취소되지 않아 고아 Job 발생. 재시도 시 이전 attempt job과 충돌 및 GCS 데이터 오염 위험. | `state "TIMED_OUT\ntimeout 저장 (Firestore)\n★ Preprocess Trigger...publish ml.step.failed\n{...,error_code=TIMEOUT,\nretry_policy=SKIP_RETRY,...}"` | `state "TIMED_OUT\ntimeout 저장 (Firestore)\n+ Vertex AI PipelineJob.cancel(pipeline_job_id)\n  (고아 Job 방지 — run.pipeline_job_id 참조)\n★ Preprocess Trigger...publish ml.step.failed\n{...,error_code=TIMEOUT,...}"` |
| **E3** | `Step-level_State_Machine_(train).md` | 동일 (고아 Job 방지). | `state "TIMED_OUT\n...retry_policy=SKIP_RETRY..."` (train) | `state "TIMED_OUT\n...+ Vertex AI PipelineJob.cancel(pipeline_job_id)..."` (train, retry_policy 제거 포함) |
| **E3** | `Step-level_State_Machine_(infer).md` | 동일 (고아 Job 방지). | `state "TIMED_OUT\n...retry_policy=SKIP_RETRY..."` (infer) | `state "TIMED_OUT\n...+ Vertex AI PipelineJob.cancel(pipeline_job_id)..."` (infer, retry_policy 제거 포함) |
| **E1** | `Step-level_State_Machine_(preprocess).md` | Topic_Spec(SSOT) 선언: `ml.step.failed`에 `retry_policy` 포함 불가. RT는 `error_code=TIMEOUT` 수신 시 자체적으로 SKIP_RETRY 적용. 메시지 필드 포함 시 RT 구현 혼란 야기. | `error_code=TIMEOUT,\nretry_policy=SKIP_RETRY,\nidempotency_key=...` | `error_code=TIMEOUT,\nidempotency_key=...` (`retry_policy=SKIP_RETRY` 제거) |
| **E1** | `Step-level_State_Machine_(preprocess).md` | TIMED_OUT 주석에서 override 필드 설명 삭제, SSOT 참조로 교체. | `%% retry_policy=SKIP_RETRY는 TIMED_OUT 전용 override 필드.` | `%% RT는 error_code=TIMEOUT 수신 시 SKIP_RETRY를 자체 적용\n%% (Topic_Spec SSOT: ml.step.failed에 retry_policy 필드 포함 안 함).` |
| **E1** | `Step-level_State_Machine_(train).md` | 동일 (retry_policy SSOT 불일치). | `retry_policy=SKIP_RETRY` 포함 (train) + override 주석 | `retry_policy=SKIP_RETRY` 제거 + SSOT 주석으로 교체 |
| **E1** | `Step-level_State_Machine_(infer).md` | 동일 (retry_policy SSOT 불일치). | `retry_policy=SKIP_RETRY` 포함 (infer) + override 주석 | `retry_policy=SKIP_RETRY` 제거 + SSOT 주석으로 교체 |
| **E1** | `Step-level_State_Machine_(postprocess).md` | 동일 (retry_policy SSOT 불일치). postprocess는 VXP 미사용이므로 E3 미적용. | `error_code=TIMEOUT,\nretry_policy=SKIP_RETRY,\nidempotency_key=...` (postprocess) | `error_code=TIMEOUT,\nidempotency_key=...` + SSOT 주석으로 교체 |
| **E4** | `Execution_Sequence_default.md` | Run-level SM에 `DATA_SYNCED` 상태가 없음. 정의된 상태: `DATA_SYNCING → STEP_RUNNING`. 다이어그램 간 상태명 불일치. | `EP->>FS: 상태 업데이트 (DATA_SYNCED + gcs_dataset_uri)` | `EP->>FS: 상태 업데이트 (STEP_RUNNING + gcs_dataset_uri 저장)` |
| **E5** | `Topic_Specification.md` | run_key 구성: `dataset_version + config_hash + image_tag + pipeline_name`. `execution_plan` 스키마에 `image_tag` 누락. Pipeline Trigger가 `PipelineJob.submit()` 시 image_tag 조회처 불명확. | `execution_plan` 스키마에 `image_tag` 필드 없음 | `image_tag: string  # 컨테이너 이미지 태그\n# Pipeline Trigger가 PipelineJob.submit() 시 참조\n# run_key 구성 요소` 추가 |
| **O1** | `Run-level_State_Machine.md` | `force=true` 플래그는 RunAPI 스키마 미정의, lock 해제 로직 미정의, sequence diagram 없음. 불완전한 미래 기능이 SM 본문에 포함되어 현재 기능으로 오인 가능. | `IGNORED` 상태에 `- 예외: 기존 run이 FAILED 상태 + 운영자\n  명시적 재실행 플래그(force=true) 제공 시\n  → lock 해제 후 신규 run 허용` 포함 | `force=true` 관련 서술 제거. `%% Future Work (O1): FAILED 상태 run 강제 재실행 (force=true)` 주석으로 이동. |
| **O2** | `Execution_Sequence_DataSync_Failure.md` | EP가 AWS STS AssumeRoleWithWebIdentity를 직접 호출하는 것은 아키텍처 위반. WIF 재인증은 STS(Storage Transfer Service)가 새 job 실행 시 내부적으로 자동 처리. | `EP->>STS: WIF 토큰 갱신 요청\n(AssumeRoleWithWebIdentity 재시도)` 별도 step으로 존재 | 해당 step 제거. `EP->>STS: transfer job 재실행` 이후 `Note over STS: STS가 내부적으로 WIF 재인증\n(AssumeRoleWithWebIdentity 자동 처리)` 로 대체 |
| **O2** | `Execution_Sequence_DataSync_Failure.md` | 재시도 설명 노트 수정 (토큰 갱신 → STS 자동 재인증). | `Note over EP: 토큰 갱신 후 STS 재시도 (최대 2회)` | `Note over EP: STS 재시도 (최대 2회)\nSTS가 새 job 실행 시 WIF를 통해 AWS 자격증명 자동 재취득` |
| **I1** | `Step-level_State_Machine_(postprocess).md` | CF timeout(60분) 초과 시 EXP Cloud Run Job이 여전히 실행 중인 상태에서 FAILED 처리됨. 다음 시도 시 이전 Job과 동시 실행 → S3 중복 업로드 위험. 단기/장기 대응 방향 명시. | TIMED_OUT 주석에 timeout 결합 문제 언급 없음 | `%% [개선 권고 I1] Timeout 결합 문제:\n%% 단기: EXP 자체 timeout을 CF timeout보다 짧게 설정.\n%% 장기: 비동기 패턴(CF→EXP 트리거→Pub/Sub 콜백) 도입 검토.` 추가 |
| **I2** | `Topic_Specification.md` | `run.attempt` 필드의 리셋 시점(step 전환 시 0으로 리셋)이 어느 파일에도 명시되지 않음. 구현 시 누락될 위험. | `attempt: int  # 현재 step의 재시도 횟수` | `attempt: int  # 현재 step의 재시도 횟수\n# step 전환 시 RT가 ml.{next_step}.requested 발행 시점에 0으로 리셋` 추가 |
| **I3** | `Failure_Handling_State_Machine.md` | `AWAITING_MANUAL → RETRY_ELIGIBLE` 진입 시 `attempt >= max_attempts` 상태 그대로면 `retry_check`에서 즉시 `DLQ_ROUTING`으로 빠져 무한루프 발생. attempt 리셋 명시 필요. | `AWAITING_MANUAL --> RETRY_ELIGIBLE : 수동 재처리 트리거` | attempt 리셋 주석 추가 + `수동 재처리 트리거\n(run.attempt 리셋 후 진입)` 레이블 수정 |
| **I4** | `C4_Container_Layer.md` | `Topic_Specification.md`에 `audit_events` 컬렉션 정의 완료되었으나 C4 Firestore 레이블에 누락. | `FS["Firestore<br>(run / execution_plan / lock / duplicate_events)"]` | `FS["Firestore<br>(run / execution_plan / lock / duplicate_events / audit_events)"]` |
| **I5** | `Execution_Sequence_default.md` | default sequence의 DATA_SYNC 실패가 즉시 FAILED 단순 처리로 표시. 실제로는 에러 코드별 재시도 로직 존재. 단순화 의도가 불명확하여 혼동 야기. | `else STS 전송 실패\n  STS-->>EA: STS 작업 실패 이벤트 발생` | `else STS 전송 실패\n  Note over EP, SL: 에러 코드별 재시도 로직 포함 (단순화된 뷰)<br>상세 분기: Execution_Sequence_DataSync_Failure.md 참조\n  STS-->>EA: ...` |

---

## 파일별 수정 요약

| 파일 | 적용 항목 | 수정 건수 |
|---|---|---|
| `Run-level_State_Machine.md` | E2, O1 | 3건 |
| `Step-level_State_Machine_(preprocess).md` | E3, E1 | 2건 |
| `Step-level_State_Machine_(train).md` | E3, E1 | 2건 |
| `Step-level_State_Machine_(infer).md` | E3, E1 | 2건 |
| `Step-level_State_Machine_(postprocess).md` | E1, I1 | 3건 |
| `Execution_Sequence_default.md` | E4, I5 | 2건 |
| `Topic_Specification.md` | E5, I2 | 2건 |
| `Execution_Sequence_DataSync_Failure.md` | O2 | 2건 |
| `Failure_Handling_State_Machine.md` | I3 | 2건 |
| `C4_Container_Layer.md` | I4 | 1건 |
| **합계** | | **21건** |

---

## 2차 수정 내역 표 (2026-02-28)

| ID | 수정 대상 파일 | 수정 이유 | 수정 전 | 수정 후 |
|---|---|---|---|---|
| **E1** | `Step-level_State_Machine_(postprocess).md` | Sequence Diagram과 SM 간 VERIFY 단계 불일치 해소 | `VERIFY` 단일 상태 | `VERIFY_ARTIFACTS`와 `VERIFY_RESULTS`로 분리하여 양쪽 target 모두 검증 |
| **E2** | `Run-level_State_Machine.md` | CANCELLING + 실패 교차 시나리오 전이선 누락 지적 | (기존 1차 수정에서 이미 반영됨) | (기존 반영분 유지 `CANCELLING --> CANCELLED : ml.step.failed...`) |
| **E3** | `Step-level_State_Machine_*.md` | TIMED_OUT 시 VXP 파이프라인 실제 취소 로직 누락 지적 | (기존 1차 수정에서 이미 반영됨) | (기존 반영분 유지 `+ Vertex AI PipelineJob.cancel...`) |
| **O1** | `Run-level_State_Machine.md` | step_transition 4중 분기가 STEP_RUNNING 목적지와 publish 형태로 완벽히 중복됨 | `next_step = train`, `infer`, `postprocess` 각각 분기 | `next_step ∈ {train, infer, postprocess}` 1개로 통합 |
| **O2** | `Step-level_State_Machine_*.md` | preprocess, train, infer 3개 SM 파일 구조 완벽 중복 | 파일 3개 각각 관리 | `Step-level_State_Machine_(generic).md` 1개로 병합 후 기존 3개 파일 삭제 |
| **O3** | `Execution_Sequence_DataSync_Failure.md` | default sequence의 실패 블록과 역할이 중첩되어 과잉 설계 | 파일 존재 | 해당 파일 삭제 처리 (default sequence로 통합) |
| **I1** | `C4_Container_Layer.md` | Stream, Biz 노드가 어떤 sequence에도 등장하지 않는 placeholder 성격이므로 혼선 유발 | 실선(직접 화살표) 처리 | 점선(`-.->`) 표기 및 `(planned)` 라벨 추가 |
| **I2** | `Failure_Handling_State_Machine.md` | 수동 재처리(`AWAITING_MANUAL`) 발생 시 attempt 초기화 로직 표기 누락 지적 | (기존 1차 수정에서 이미 반영됨) | (기존 반영분 유지 `run.attempt 리셋 후 진입`) |

---

## 2차 파일별 수정 요약

| 파일 | 적용 항목 | 수정 건수 | 비고 |
|---|---|---|---|
| `Step-level_State_Machine_(postprocess).md` | E1 | 1건 | VERIFY 분리 |
| `Run-level_State_Machine.md` | O1 | 1건 | step_transition 병합 |
| `Step-level_State_Machine_(generic).md` | O2 | 1건 | 신규 생성 |
| 기존 `Step-level_State_Machine` 3종 | O2 | 3건 | 병합에 따른 삭제 |
| `Execution_Sequence_DataSync_Failure.md` | O3 | 1건 | 삭제 |
| `C4_Container_Layer.md` | I1 | 1건 | 점선 표기 |
| **합계** | | **8건** | (E2, E3, I2는 기 반영) |
