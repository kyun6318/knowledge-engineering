# v4 C4 Component Layer 설계 리뷰

> **리뷰 대상**: `v4/` 디렉터리 전체 (8개 문서)
> **리뷰 기준**: `v3/` 설계 문서 (10개 문서) 대비 정합성, 과잉 설계 여부, 개선점
> **리뷰 일자**: 2026-02-28

---

## 1. 설계 오류 (Design Errors)

### 1.1 [RT] Cancel 타임아웃 시 `FAILED` 전이 경로 미표현

**대상 파일**: `C4_Component_Layer_RT.md`

**문제**: v3 `Execution_Sequence_Cancel.md` (L41-46)에서는 VXP cancel 호출 후 **타임아웃(30s 이내 미응답)** 시 `state=FAILED`로 전이하고 `ml.dead-letter`를 발행하는 분기가 존재합니다. v4 RT 다이어그램에서는 `CANCEL_HDLR` → `VXP_CLIENT` → `External_VXP` 까지만 표현되어 있고, cancel 자체가 실패하는 경우의 `FAILED` 전이 및 `ml.dead-letter` 발행이 누락되어 있습니다.

| 구분 | v3 Cancel Sequence | v4 RT |
|------|-------------------|-------|
| cancel 성공 | CANCELLED + `ml.run.cancelled` 발행 | ✅ 표현됨 |
| cancel 타임아웃/실패 | FAILED + `ml.dead-letter` 발행 | ❌ 누락 |

> [!WARNING]
> **권고**: Cancel Handler의 Component Details에 "cancel 자체 실패 시 `state=FAILED` 전이 + `ml.dead-letter` 발행" 분기를 추가하고, 다이어그램에도 `VXP_CLIENT` → `DLQ_ROUTER` 경로 또는 FAILED 노드를 표현해야 합니다.

---

### 1.2 [RT] CANCELLING 상태에서 `ml.step.failed` 수신 Race Condition 미기술

**대상 파일**: `C4_Component_Layer_RT.md`

**문제**: v3 `Run-level_State_Machine.md` (L59-64)에서는 CANCELLING 상태에서 `ml.step.failed`를 수신하는 Race Condition 처리가 명시되어 있습니다:
- `step_failed.timestamp ≥ cancel_requested_at` → cancel에 의한 실패로 간주 → CANCELLED
- `step_failed.timestamp < cancel_requested_at` → cancel 이전 실패지만 cancel 의도 우선 → CANCELLED (retry 없음)

v4 RT에서는 CANCELLING 상태에서의 `ml.step.failed` 수신 처리가 다이어그램/Component Details 모두에 누락되어 있습니다.

> [!WARNING]
> **권고**: Component Details의 Cancel Handler 설명에 "CANCELLING 상태에서 `ml.step.failed` 수신 시 timestamp 무관하게 retry 없이 CANCELLED로 흡수" 정책을 추가해야 합니다.

---

### 1.3 [EP] Staging Orchestrator의 `state=DATA_SYNCING` 업데이트 경로 누락

**대상 파일**: `C4_Component_Layer_EP.md`

**문제**: v3 `Execution_Sequence_default.md` (L59)에서 EP는 STS를 트리거한 후 **`state=DATA_SYNCING`으로 Firestore 상태를 업데이트**합니다. 또한 Sync 완료 시(L72) `state=STEP_RUNNING + gcs_dataset_uri 저장`을 수행합니다. v4 EP 다이어그램에서 Staging Orchestrator는 STS를 트리거하고 Sync 완료 시 첫 Step을 발행하지만, **중간 상태 업데이트(`DATA_SYNCING`, `STEP_RUNNING + gcs_dataset_uri`)를 Firestore에 기록하는 경로**가 다이어그램에 표현되지 않았습니다.

> [!NOTE]
> **권고**: Staging Orchestrator → `FS_CLIENT` 경로에 `"update state=DATA_SYNCING"` 및 Sync 완료 시 `"update state=STEP_RUNNING + gcs_dataset_uri"` 를 추가하면 v3와의 정합성이 완전해집니다. 또는 Component Details에 해당 Firestore 상태 갱신을 명시적으로 기술해야 합니다.

---

### 1.4 [Triggers] Postprocess Trigger의 `sync_target=none` 분기 미표현

**대상 파일**: `C4_Component_Layer_Triggers.md`

**문제**: v3 `Step-level_State_Machine_(postprocess).md` (L10)에서 `sync_target=none`인 경우 EXP 호출 없이 즉시 `ml.step.completed`를 발행합니다. v4 Triggers 다이어그램의 Postprocess 경로에서는 `PP_DEC → EXP_CALLER → EXP`를 항상 거치는 것으로 표현되어 있어, `sync_target=none` 단축 경로가 보이지 않습니다.

> [!NOTE]
> **권고**: `PP_DEC`에서 `sync_target=none` 확인 후 EXP 호출을 건너뛰고 직접 `PP_PS`로 이동하는 분기를 다이어그램에 추가하거나, Component Details에 해당 로직을 명시해야 합니다.

---

## 2. 과잉 설계 (Over-Engineering) 검토

### 2.1 [RunAPI] Cloud Run IAM + Subject Extractor + RBAC 3단 인증/인가 — **적정**

Cloud Run IAM(인프라 Auth) → Subject Extractor(식별자 추출) → RBAC(인가)는 CNCF 보안 모범 사례에 부합하는 계층 분리입니다. v3에서도 RunAPI가 AuthN/AuthZ를 수행했으므로 자연스러운 구체화입니다.

**판정**: ✅ 적정 설계

### 2.2 [FailureHandling] 3-Tier 방어선의 독립 문서 분리 — **적정**

Retry Tier → DLQ Tier → Alert & Manual Tier가 RT 다이어그램과 상호보완적으로 참조되며, v3의 `Failure_Handling_State_Machine.md`의 복잡한 상태 전이를 시각적으로 단순화한 효과가 있습니다.

**판정**: ✅ 적정 설계

### 2.3 [Triggers] Postprocess Trigger 별도 서브그래프 분리 — **적정**

v3에서도 Postprocess는 VXP를 사용하지 않는 독립 경로였으므로, 이를 별도 서브그래프로 분리한 것은 시각적 명확성을 높입니다.

**판정**: ✅ 적정 설계

### 2.4 [EXP] Checksum Validator를 별도 컴포넌트로 분리 — **적정**

AWS SDK Native Checksum을 활용하므로 실제 구현 코드량은 적지만, C4 Component Layer에서는 "검증 책임"을 명확히 시각화하는 것이 목적이므로 적정합니다.

**판정**: ✅ 적정 설계

---

## 3. 개선 권고 (Improvements)

### 3.1 [RT] `cancel_requested_at` 타임스탬프 기록 시점 Component Details 보완

**대상 파일**: `C4_Component_Layer_RT.md`

v3 `Run-level_State_Machine.md` (L55)에서 `cancel_requested_at`는 CANCELLING 진입 시 기록되며, 이후 `ml.step.failed` Race Condition 해소에 사용됩니다. v4 RT 다이어그램에서 `update state=CANCELLING`이 표현되어 있으나, `cancel_requested_at` 기록이 Component Details에 언급되지 않았습니다.

> [!TIP]
> **권고**: Cancel Handler 설명에 "`cancel_requested_at` 타임스탬프를 CANCELLING 전이 시 기록 (Race Condition 해소용)"을 추가하면 v3 `Topic_Specification.md`의 `run.cancel_requested_at` 필드와 정합성이 확보됩니다.

---

### 3.2 [EP] Configuration Initializer의 Secret Manager 조회 누락

**대상 파일**: `C4_Component_Layer_EP.md`

v3 `Execution_Sequence_default.md` (L46-47)에서 EP는 Firestore config 외에 **Secret Manager에서 민감 정보(credentials / API keys)를 조회**합니다. v4 EP 다이어그램에는 Secret Manager 컴포넌트가 없으며, `CFG_INIT`은 Firestore만 사용합니다.

> [!NOTE]
> **권고**: Secret Manager 조회가 v4에서도 필요한 경우, `CFG_INIT` → `SM_CLIENT["Secret Manager Client"]` 경로를 추가해야 합니다. 만약 v4에서 의도적으로 ENV 기반으로 대체한 것이라면, Component Details에 그 결정 근거를 명시해야 합니다.

---

### 3.3 [EP] Lock 실패 시 `duplicate_events` audit 기록 누락

**대상 파일**: `C4_Component_Layer_EP.md`

v3 `Run-level_State_Machine.md` (L22) 및 `Execution_Sequence_Idempotency.md` (L21)에서 Lock 실패(중복 요청) 시 `duplicate_events` 컬렉션에 감사 기록을 저장합니다. v4 EP에서 Lock 실패는 단순히 `Log & HTTP 409 / ACK`로 처리되며, Firestore 감사 기록이 표현되지 않았습니다.

> [!TIP]
> **권고**: Lock 실패 시 `FS_CLIENT`에 `duplicate_events` 감사 기록을 남기는 경로를 추가하면 v3의 운영 가시성(Audit Trail)이 유지됩니다.

---

### 3.4 [FailureHandling] Cloud Tasks 생성 실패 시 DLQ 즉시 라우팅 분기 미표현

**대상 파일**: `C4_Component_Layer_FailureHandling.md`

v3 `Failure_Handling_State_Machine.md` (L46)에서 Cloud Tasks **생성 자체가 실패**(인프라 오류)하면 즉시 `DLQ_ROUTING`으로 전이하고 `state=FAILED`가 됩니다. v4 FailureHandling 다이어그램에서는 `CT_CLIENT → CloudTasks` 성공만 표현되어 있고, CT 생성 실패 → DLQ 직행 경로가 없습니다.

> [!NOTE]
> **권고**: `CT_CLIENT` -.-> `DLQ_ROUTER` (라벨: `"if task creation fails"`)를 추가하면 v3의 2단계 안전망이 완전히 표현됩니다.

---

### 3.5 [FailureHandling] `TERMINATED` 상태 미표현

**대상 파일**: `C4_Component_Layer_FailureHandling.md`

v3 `Failure_Handling_State_Machine.md` (L63-66)에서 수동 작업 대기(`AWAITING_MANUAL`) 후 운영자가 재시도 대신 **최종 종료**를 선택하는 `TERMINATED` 상태가 있습니다. v4 FailureHandling에서는 `MANUAL_INVOKER`만 존재하고, 운영자가 종료를 선택하는 경로가 없습니다.

> [!TIP]
> **권고**: `Operator` → `TERMINATED` 경로를 추가하거나, Component Details에 "운영자가 재시도 대신 최종 종료를 선택할 수 있음 (Firestore 기록 보존)"을 명시하면 완전한 설계가 됩니다.

---

## 4. 리뷰 항목 자체 검증 (Validation)

| # | 리뷰 항목 | 검증 근거 (v3 원본) | 타당성 |
|---|----------|-------------------|--------|
| 1.1 | Cancel 타임아웃 → FAILED | `Execution_Sequence_Cancel.md` L41-46: cancel 타임아웃 시 `FAILED + ml.dead-letter` 발행 | ✅ **타당** |
| 1.2 | CANCELLING 중 ml.step.failed Race | `Run-level_State_Machine.md` L59-64: CANCELLING은 terminal-directed, 모든 실패를 CANCELLED로 흡수 | ✅ **타당** |
| 1.3 | EP state=DATA_SYNCING 기록 | `Execution_Sequence_default.md` L59, L72: DATA_SYNCING → STEP_RUNNING 상태 전이 명시 | ✅ **타당** |
| 1.4 | Postprocess sync_target=none | `Step-level_State_Machine_(postprocess).md` L10: sync_target=none → 즉시 SUCCEEDED | ✅ **타당** |
| 2.1-2.4 | 과잉 설계 검토 | 모두 v3 설계의 자연스러운 구체화 | ✅ **타당** |
| 3.1 | cancel_requested_at 기록 | `Run-level_State_Machine.md` L55, `Topic_Specification.md` L29-31: CANCELLING 진입 시 기록 | ✅ **타당** |
| 3.2 | EP Secret Manager 조회 | `Execution_Sequence_default.md` L46-47: EP→SM 민감 정보 조회 | ✅ **타당** |
| 3.3 | duplicate_events 감사 기록 | `Run-level_State_Machine.md` L22, `Execution_Sequence_Idempotency.md` L21 | ✅ **타당** |
| 3.4 | CT 생성 실패 → DLQ | `Failure_Handling_State_Machine.md` L46: Cloud Tasks 생성 실패 → 즉시 DLQ | ✅ **타당** |
| 3.5 | TERMINATED 상태 | `Failure_Handling_State_Machine.md` L63-66: AWAITING_MANUAL → TERMINATED | ✅ **타당** |

---

## 5. 종합 평가

| 분류 | 건수 | 심각도 |
|------|------|--------|
| 설계 오류 | 4건 | 🟡 1.1-1.2 (Medium), 🟢 1.3-1.4 (Low) |
| 과잉 설계 | 0건 | — |
| 개선 권고 | 5건 | 🟢 3.1-3.5 (Low) |

### 총평

현재 v4 설계는 이전 리뷰 피드백(EP Sync 주체 수정, RT 트랜잭션 병합, RETRYING 분기 추가, Postprocess 경로 분리 등)이 충실히 반영되어 **v3 대비 구조적 정합성이 크게 향상**되었습니다. 과잉 설계 없이 각 컴포넌트의 책임이 적절히 분리되어 있으며, Related Documents 참조로 문서 간 추적성도 확보되었습니다.

잔여 이슈는 주로 v3에서 상세하게 다룬 **에지 케이스와 예외 경로**(cancel 타임아웃, CANCELLING 중 Race Condition, sync_target=none 단축 경로)가 v4 Component Layer에서 생략된 경우가 대부분입니다. 이들은 심각도가 Medium~Low이며, Component Details에 한두 문장 추가하는 수준으로 해소 가능합니다.

---
---

# v4 C4 Component Layer 설계 리뷰 (3차 — 2차 리뷰 반영 후)

> **리뷰 대상**: `v4/` 디렉터리 전체 (8개 문서, 2차 리뷰 피드백 반영 버전)
> **리뷰 기준**: `v3/` 설계 문서 (10개 문서) 대비 정합성, 과잉 설계 여부, 개선점
> **리뷰 일자**: 2026-02-28

---

## 1. 2차 리뷰 항목 적용 확인

| # | 리뷰 항목 | 적용 상태 | 적용 위치 |
|---|----------|----------|----------|
| 1.1 | Cancel 타임아웃 → FAILED + DLQ | ✅ 적용됨 | RT 다이어그램 L75-77, Component Details #5 |
| 1.2 | CANCELLING 중 ml.step.failed Race Condition | ✅ 적용됨 | RT 다이어그램 L79-80, Component Details #5 |
| 1.3 | EP DATA_SYNCING/STEP_RUNNING 상태 업데이트 | ✅ 적용됨 | EP 다이어그램 L46/L50, Component Details #5 |
| 1.4 | Postprocess sync_target=none 단축 경로 | ✅ 적용됨 | Triggers 다이어그램 L45, Component Details #6 |
| 3.1 | cancel_requested_at 기록 시점 | ✅ 적용됨 | RT 다이어그램 L69, Component Details #5 |
| 3.2 | EP Secret Manager 이관 설명 | ✅ 적용됨 | EP Component Details #1 |
| 3.3 | duplicate_events 감사 기록 | ✅ 적용됨 | EP 다이어그램 L33, Component Details #2 |
| 3.4 | CT 생성 실패 → DLQ 즉시 라우팅 | ✅ 적용됨 | FailureHandling 다이어그램 L26, Component Details #2 |
| 3.5 | TERMINATED 상태 | ✅ 적용됨 | FailureHandling 다이어그램 L43, Component Details #5 |

> **결론**: 2차 리뷰의 설계 오류 4건 + 개선 권고 5건이 **모두 정확히 반영**되었습니다.

---

## 2. 설계 오류 (Design Errors) — 3차

3차 리뷰에서 v3 대비 **유의미한 설계 오류는 발견되지 않았습니다**. 이전 1차·2차 리뷰를 통해 주요 정합성 이슈가 모두 해소되었습니다.

---

## 3. 과잉 설계 (Over-Engineering) 검토 — 3차

### 3.1 [FailureHandling] FailureHandling 다이어그램의 `TERMINATED` 노드 — **적정**

신규 추가된 TERMINATED 경로는 v3 `Failure_Handling_State_Machine.md`의 `AWAITING_MANUAL → TERMINATED` 전이를 그대로 반영한 것으로, 과잉이 아닌 필수 경로입니다.

**판정**: ✅ 적정 설계

---

## 4. 개선 권고 (Improvements) — 3차

### 4.1 [Index] `C4_Component_Layer.md`의 문서 형식 보완

**대상 파일**: `C4_Component_Layer.md`

**문제**: 인덱스 문서가 파일 목록 plain-text로만 구성되어 있어 다른 v4 문서들의 Related Documents 링크 형식과 일관성이 없습니다. 마크다운 링크, 문서 제목(heading), 또는 표 형식으로 구조화하면 가독성과 탐색성이 개선됩니다.

> [!TIP]
> **권고**: 인덱스 문서를 마크다운 표 또는 링크 목록 형식으로 변경하고, 각 문서에 대한 간략한 책임 설명을 포함시키면 일관성이 향상됩니다.

---

### 4.2 [FailureHandling] `Structured Error Logger`의 로깅 타이밍 명확화

**대상 파일**: `C4_Component_Layer_FailureHandling.md`

**문제**: 다이어그램에서 `RETRY_ASSESS` → `LOG_CLIENT` 경로가 **Retry Eligible 경로와 DLQ 경로 모두**에서 독립적으로 트리거되는 것처럼 보입니다. v3 `Failure_Handling_State_Machine.md`에서 구조화 로그는 **DLQ 확정 시점(`DLQ_ROUTING → ALERTING`)에만** 발생하며, Retry Eligible에서는 별도 로그가 없습니다. 현재 다이어그램에서는 Retry 시에도 로깅하는 것처럼 해석될 수 있습니다.

> [!TIP]
> **권고**: `LOG_CLIENT`로의 경로를 `DLQ_ROUTER`에서만 트리거되도록 조정하거나, `RETRY_ASSESS` → `LOG_CLIENT` 라벨에 "DLQ 전환 시에만" 조건을 추가하면 v3의 의도와 일치합니다.

---

## 5. 리뷰 항목 자체 검증 (Validation) — 3차

| # | 리뷰 항목 | 검증 근거 (v3 원본) | 타당성 |
|---|----------|-------------------|--------|
| 4.1 | 인덱스 문서 형식 | 다른 7개 v4 문서의 Related Documents 형식(마크다운 링크) 대비 plain-text 불일치 | ✅ **타당** (일관성) |
| 4.2 | Logger 트리거 시점 | `Failure_Handling_State_Machine.md` L51-54: `DLQ_ROUTING → ALERTING` 순서의 로깅, Retry 경로에서는 ALERTING 미진입 | ✅ **타당** |

---

## 6. 종합 평가 — 3차

| 분류 | 건수 | 심각도 |
|------|------|--------|
| 설계 오류 | 0건 | — |
| 과잉 설계 | 0건 | — |
| 개선 권고 | 2건 | 🟢 4.1-4.2 (Low) |

### 총평

2차 리뷰 피드백 9건이 모두 정확히 반영되어 **v3 대비 구조적 정합성이 완전히 확보**되었습니다. 주요 흐름(Run 완료·취소·실패·재시도·Data Sync)이 모두 v3와 1:1로 대응되며, 과잉 설계 없이 C4 Component Layer로 적절하게 분리되어 있습니다.

잔여 개선점은 인덱스 문서 형식(`C4_Component_Layer.md`)과 Structured Error Logger의 트리거 시점 명확화로, 모두 **Low 심각도의 가독성/일관성 개선** 수준입니다. v4 설계는 이 시점에서 **구현 착수 가능한 수준의 설계 완성도**에 도달했다고 판단됩니다.
