# v3 역방향 리뷰 (v4 설계 기준)

> **리뷰 기준**: v4 설계에서 개선·명확화된 항목이 v3 원본에 반영되어야 할 사항
> **리뷰 대상**: Execution_Sequence 4개, State_Machine 4개, Topic_Specification
> **리뷰 일자**: 2026-02-28

---

### R.1 [Topic_Specification] `run.state` 열거형에 `TERMINATED`, `AWAITING_MANUAL` 누락

**대상 파일**: `Topic_Specification.md` (L17-19)

**문제**: `run.state` 필드의 유효 값 목록이 다음과 같이 정의되어 있습니다:
```
INTAKE | CONFIG_RESOLVING | LOCK_ACQUIRING | PLANNING |
DATA_SYNCING | STEP_RUNNING | RETRYING | CANCELLING |
COMPLETED | FAILED | CANCELLED | REJECTED | IGNORED
```

그러나 같은 v3 내 `Failure_Handling_State_Machine.md` (L57, L63-66)에서는 `AWAITING_MANUAL`과 `TERMINATED`가 명시적으로 사용됩니다:
- `DLQ_ROUTING → ALERTING → AWAITING_MANUAL`
- `AWAITING_MANUAL → TERMINATED`

Topic Specification이 Firestore 스키마의 **Single Source of Truth**를 자처하므로, 여기에 누락된 상태는 구현 시 유효성 검증에서 오류를 일으킬 수 있습니다.

> [!WARNING]
> **권고**: `run.state` 열거형에 `AWAITING_MANUAL | TERMINATED`를 추가하여 Failure_Handling_State_Machine과 정합성을 맞춰야 합니다.

---

### R.2 [Execution_Sequence_default] 존재하지 않는 문서 참조

**대상 파일**: `Execution_Sequence_default.md` (L77)

**문제**: STS 전송 실패 분기에서 `"상세 분기: Execution_Sequence_DataSync_Failure.md 참조"`라고 기술하고 있으나, v3 디렉터리에 해당 파일이 **존재하지 않습니다**. 현재 v3 디렉터리의 파일 목록:

| 파일 | 존재 여부 |
|------|----------|
| `Execution_Sequence_default.md` | ✅ |
| `Execution_Sequence_Cancel.md` | ✅ |
| `Execution_Sequence_Failure_Retry.md` | ✅ |
| `Execution_Sequence_Idempotency.md` | ✅ |
| `Execution_Sequence_DataSync_Failure.md` | ❌ **미존재** |

Data Sync 실패 시의 `sync_attempt` 기반 재시도 로직은 `Run-level_State_Machine.md` (L31-32)에 정의되어 있으나, 전용 Sequence Diagram은 작성되지 않은 상태입니다.

> [!NOTE]
> **권고**: `Execution_Sequence_DataSync_Failure.md`를 작성하거나, 참조를 `Run-level_State_Machine.md`의 `DATA_SYNCING` 상태 전이 설명으로 변경해야 합니다.

---

### 검증

| # | 리뷰 항목 | 근거 | 타당성 |
|---|----------|------|--------|
| R.1 | `run.state` 열거형 누락 | `Failure_Handling_State_Machine.md` L57(`AWAITING_MANUAL`), L63-66(`TERMINATED`) 에서 사용하는 상태가 Topic_Specification L17-19의 SSOT 열거형에 미포함 | ✅ **타당** |
| R.2 | 존재하지 않는 문서 참조 | `find` 결과 v3 디렉터리에 `Execution_Sequence_DataSync_Failure.md` 미존재 확인 | ✅ **타당** |

---

### R.3 [v3↔v4] 수동 재시도(Manual Retry) 시 상태 전이 값 불일치

**대상 파일**: v3 `Failure_Handling_State_Machine.md` (L40, L62) ↔ v4 `C4_Component_Layer_FailureHandling.md` (#5)

**문제**: 운영자 수동 재시도 시 Firestore에 기록되는 `run.state` 값이 v3과 v4에서 다릅니다.

| 구분 | 경로 | state 값 | 지연 |
|------|------|----------|------|
| v3 | `AWAITING_MANUAL → RETRY_ELIGIBLE` → Cloud Tasks 지연 task | `RETRYING` | Cloud Tasks backoff |
| v4 | `Manual Retry Invoker` → `ml.{step}.requested` 직접 발행 | `STEP_RUNNING` | 없음 (즉시 실행) |

v4의 bypass 설계는 의도적이며(DLQ 상태에서 RT 정상 Retry 진입 불가), Component Details에 근거가 설명되어 있습니다. 그러나 `Topic_Specification.md`가 Firestore SSOT이므로, 구현 시 어떤 문서를 따르느냐에 따라 Firestore에 기록되는 state가 달라집니다.

> [!NOTE]
> **권고**: v3 `Run-level_State_Machine.md` L74의 `FAILED → RETRYING` 전이를 `FAILED → STEP_RUNNING`으로 수정하고, v3 `Failure_Handling_State_Machine.md` L62의 `AWAITING_MANUAL → RETRY_ELIGIBLE` 경로 설명에 "state=STEP_RUNNING으로 갱신 후 RT 우회하여 직접 발행" 주석을 추가하면 v4 Component Layer와 정합성이 확보됩니다.

---

### 검증 (R.3 추가)

| # | 리뷰 항목 | 근거 | 타당성 |
|---|----------|------|--------|
| R.3 | 수동 재시도 state 값 | v3 `Failure_Handling_SM` L40: `state = RETRYING` / v4 `FailureHandling` #5: `state=STEP_RUNNING`. Topic_Specification SSOT 기준으로 구현 시 충돌 가능 | ✅ **타당** |

