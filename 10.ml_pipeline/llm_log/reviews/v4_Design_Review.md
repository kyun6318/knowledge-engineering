# v4 C4 Component Layer 설계 리뷰

> **리뷰 대상**: `v4/` 디렉터리 전체 (8개 문서)
> **리뷰 기준**: `v3/` 설계 문서 (10개 문서) 대비 정합성, 과잉 설계 여부, 개선점
> **리뷰 일자**: 2026-02-28

---

## 1. 설계 오류 (Design Errors)

### 1.1 [EP] Staging Orchestrator의 Sync 완료 후 처리 주체 불일치

**대상 파일**: `C4_Component_Layer_EP.md` (Line 58)

**문제**: EP 문서에서 `Staging Orchestrator`가 `ml.data.synced`를 수신하면 "**Run Tracker로 릴레이**되도록 처리"한다고 기술되어 있습니다. 그러나 v3 설계(`Execution_Sequence_default.md` Line 69-75)에서는 `ml.data.synced`를 **EP(Execution Planner)** 인스턴스가 수신하여 `execution_plan`을 재조회하고, 직접 `ml.preprocess.requested`를 발행합니다.

| 구분 | v3 | v4 EP |
|------|-----|-------|
| `ml.data.synced` 수신자 | EP (새 인스턴스) | Staging Orchestrator → RT 릴레이 |
| 첫 Step 발행 주체 | EP | 불명확 (RT?) |

**근거**: v3 Topic Spec에도 `ml.data.synced`의 Subscriber는 `Execution Planner`로 명시되어 있습니다. RT로 릴레이하면 v3의 **EP가 첫 Step을 발행**하는 원칙과 충돌하며, RT에 불필요한 Sync 후속 처리 책임이 추가됩니다.

> [!CAUTION]
> **권고**: Staging Orchestrator는 `ml.data.synced` 수신 시 RT가 아닌 EP 내부에서 `ml.preprocess.requested`를 직접 발행하도록 수정해야 합니다. v3와 v4 Mermaid 다이어그램의 흐름도 일치시켜야 합니다.

---

### 1.2 [RT] Idempotency Guard → State Transition Transaction 순서 역전

**대상 파일**: `C4_Component_Layer_RT.md` (Line 30-35)

**문제**: 다이어그램에서 `COMPLETION_HDLR` / `FAIL_HDLR` → `IDEMP_GUARD` → `STATE_MGR` 순서로 흐름이 그려져 있습니다. 그런데 Component Details (Line 66)에서는 "**단일 Firestore 트랜잭션**으로 병합"이라고 기술하면서도, 다이어그램 상에서는 `IDEMP_GUARD`가 `STATE_MGR`에 "1. start transaction"을 보내는 것으로 표현되어 있습니다.

**근거**: v3 `Failure_Handling_State_Machine.md`에서의 멱등성 검사는 Firestore **트랜잭션 내부**에서 수행됩니다. 다이어그램에서 `IDEMP_GUARD`와 `STATE_MGR`가 별개 노드로 분리되면, "Guard가 먼저 실행 → 그 후 트랜잭션 시작"이라는 **TOCTOU(Time-Of-Check-to-Time-Of-Use)** 오해를 유발할 수 있습니다.

> [!WARNING]
> **권고**: `IDEMP_GUARD`와 `STATE_MGR`를 하나의 트랜잭션 컴포넌트로 병합하거나, 다이어그램 주석으로 "동일 트랜잭션 내부 단계"임을 명시해야 합니다. 현재 Component Details 텍스트와 다이어그램의 의미가 불일치합니다.

---

### 1.3 [RT] Cancel Handler의 Firestore 조회 위치 불일치

**대상 파일**: `C4_Component_Layer_RT.md` (Line 54-57)

**문제**: `CANCEL_HDLR`가 `FS_CLIENT`에 직접 `check state`를 수행한 후 `VXP_CLIENT`를 호출하는 것으로 되어 있습니다. 그러나 v3 Cancel Sequence(`Execution_Sequence_Cancel.md`)에서 Cancel Handler의 주요 분기는:
- `state = STEP_RUNNING` → CANCELLING + VXP cancel
- `state = RETRYING` → Cloud Tasks 취소 시도 + CANCELLING
- `state ≠ STEP_RUNNING, RETRYING` → audit 기록 후 무시

v4에서는 **RETRYING 상태에서의 Cloud Tasks 취소 분기**가 다이어그램에 표현되지 않았습니다.

> [!WARNING]
> **권고**: `CANCEL_HDLR`에서 RETRYING 분기 시 `CT_CLIENT`(Cloud Tasks Client)로의 취소 요청 경로를 다이어그램에 추가하거나, Component Details에 해당 분기를 명시해야 합니다.

---

### 1.4 [Triggers] VXP Status Forwarder의 Postprocess 제외 미명시

**대상 파일**: `C4_Component_Layer_Triggers.md`

**문제**: `VXP Status Forwarder`가 Vertex AI 상태 변경 알림을 수신/발행하는 것으로 표현되어 있으나, Postprocess Step은 VXP를 사용하지 않고 EXP를 동기 HTTP 호출합니다. Postprocess Trigger가 `ml.step.completed/failed`를 직접 발행하는 경로가 이 다이어그램에는 없습니다.

**근거**: v3 `Execution_Sequence_default.md` Line 180-211에서 Postprocess Trigger는 VXP 없이 EXP를 동기 호출하고 직접 `ml.step.completed`를 발행합니다.

> [!IMPORTANT]
> **권고**: Triggers 다이어그램에 Postprocess Trigger의 별도 경로(EXP 동기 호출 → 직접 발행)를 추가하거나, 주석으로 "Postprocess는 VXP Forwarder를 사용하지 않음 — EXP 다이어그램 참조"를 명시해야 합니다.

---

## 2. 과잉 설계 (Over-Engineering) 검토

### 2.1 [FailureHandling] 독립 문서 분리의 적정성 — **과잉 아님**

`C4_Component_Layer_FailureHandling.md`는 RT의 서브프로세스를 별도로 분리한 문서입니다. 3-Tier 방어선 구조(Immediate Retry → DLQ → Alert & Manual)가 명확히 시각화되어 있고, RT 다이어그램에서도 동일 컴포넌트(`RETRY_ASSESS`, `DLQ_ROUTER`)가 참조되므로 **중복이 아닌 상호보완적 관계**입니다.

**판정**: ✅ 적정 설계

### 2.2 [RunAPI] Project-level RBAC Manager — **과잉 가능성 낮음**

Firestore 기반 RBAC 정책 조회는 v3에서도 AuthN/AuthZ를 요구했으므로 자연스러운 구체화입니다. 다만, 초기 운영 단계에서 Project 수가 적다면 **환경 변수 기반 허용 목록**으로 시작하고 추후 승격하는 것도 고려 가능합니다.

**판정**: ✅ 적정 (단, 초기에는 간소화 옵션 고려 가능)

### 2.3 [EP] Sync Strategy Resolver의 분리 — **적정**

v3에서도 EP 내부에서 Sync 필요 여부를 판단하는 분기가 있었으므로, 이를 `Sync Strategy Resolver`로 명명하고 분리한 것은 합리적입니다.

**판정**: ✅ 적정 설계

### 2.4 [Triggers] Pipeline Strategy Factory의 Stateless 환경 변수 주입 — **적정**

v3에서 Trigger가 Firestore를 조회하던 부분을 ENV 기반 Stateless로 전환한 것은 **Cold Start 최적화** 및 **의존성 감소** 관점에서 올바른 진화입니다.

**판정**: ✅ 적정 설계

---

## 3. 개선 권고 (Improvements)

### 3.1 [RT] `ml.step.completed` 수신 시 Run 최종 완료 발행 경로 누락

**대상 파일**: `C4_Component_Layer_RT.md`

**문제**: v3 `Execution_Sequence_default.md` (Line 214-225)에서 RT가 모든 Step 완료 후 수행하는 최종 처리:
1. `execution_plan` 소진 확인 (next_step = null)
2. `state = COMPLETED` 업데이트
3. `ml.run.completed` 발행
4. Monitoring/Slack 알림

이 과정이 v4 RT 다이어그램에서는 **`PS_CLIENT → publish ml.{next}.requested`만 표현**되어 있고, `next_step = null` 시의 Run 완료 흐름이 보이지 않습니다.

> [!IMPORTANT]
> **권고**: `STATE_MGR`에서 `next_step = null`일 때 `PS_CLIENT`를 통해 `ml.run.completed`를 발행하는 분기를 다이어그램과 Component Details에 추가해야 합니다.

---

### 3.2 [RT] `ml.run.cancelled` 발행 경로 누락

Cancel Handler가 CANCELLING → CANCELLED 전이 후 `ml.run.cancelled` 이벤트를 발행하는 경로가 v4 RT 다이어그램에 없습니다. v3 Cancel Sequence(Line 38, 59)에서는 `ml.run.cancelled`를 Pub/Sub로 발행합니다.

> [!NOTE]
> **권고**: `CANCEL_HDLR`가 CANCELLED 상태로 전이한 후 `PS_CLIENT`를 통해 `ml.run.cancelled`를 발행하는 경로를 추가해야 합니다.

---

### 3.3 [EP] `ml.data.sync.failed` 수신 시 재시도 분기 미표현

**대상 파일**: `C4_Component_Layer_EP.md`

v3 `Run-level_State_Machine.md` (Line 31)에서는 `ml.data.sync.failed` 수신 시:
- `error_code ≠ MANIFEST_INVALID && sync_attempt < max_sync_attempts` → STS 재트리거
- 그 외 → FAILED

v4 EP 다이어그램(Line 22)에서는 `ml.data.sync.failed → STG_ORCH`로만 표현되어 있고, 재시도/실패 분기가 없습니다.

> [!NOTE]
> **권고**: `STG_ORCH` 내부에서 `sync_attempt` 기반 재시도/FAILED 분기를 표현하거나, Component Details에 해당 로직을 기술해야 합니다.

---

### 3.4 [VXP] Preprocess Pipeline의 Data Locator 데이터 소스 표기 오류

**대상 파일**: `C4_Component_Layer_VXP.md` (Line 38)

`PP_READ -.- |"Read S3 Data via STS"| GCS`로 표기되어 있는데, Preprocess 시점에서는 STS를 통한 동기화가 이미 완료된 상태입니다. 따라서 실제로는 **GCS** staging 영역에서 데이터를 읽는 것이지 S3에서 직접 읽는 것이 아닙니다.

> [!NOTE]
> **권고**: 라벨을 `"Read Staged Data"` 또는 `"Read from GCS Staging"` 으로 수정하여 혼동을 방지해야 합니다.

---

### 3.5 [EXP] Checksum 재시도의 루프 종료 조건 미정의

**대상 파일**: `C4_Component_Layer_EXP.md` (Line 29)

`CSUM_VAL → |"if ChecksumAlgorithm mismatch"| GCS_READER`로 재발송(retry)을 표현하고 있으나, 최대 재시도 횟수나 종료 조건이 정의되어 있지 않습니다. 무한 루프 가능성이 있습니다.

> [!NOTE]
> **권고**: `max_checksum_retry` 또는 고정 1회 재시도(최초 업로드 + 1회 재시도) 등의 종료 조건을 Component Details에 명시해야 합니다.

---

### 3.6 [FailureHandling] Manual Retry Invoker의 attempt 리셋 상세화

**대상 파일**: `C4_Component_Layer_FailureHandling.md` (Line 40-41, 55)

`MANUAL_INVOKER`가 `reset attempt=0, update state=STEP_RUNNING`으로 Firestore를 업데이트하고 `ml.{step}.requested`를 발행하는 것은 v3의 설계 의도(`attempt 리셋 후 RETRY_ELIGIBLE 진입`)와 부합합니다. 다만, v3에서 원래 경로는 `AWAITING_MANUAL → RETRY_ELIGIBLE`이었고, v4에서는 RT를 우회(Bypass)하여 직접 Pub/Sub으로 발행합니다. 이 **우회 패턴의 의도**를 Component Details에 보다 명확히 기술할 필요가 있습니다.

> [!TIP]
> **권고**: Manual Retry가 RT의 State Machine을 우회하는 이유(예: DLQ 상태에서 일반 Retry 경로 진입 불가)를 보충 설명으로 추가하면 설계 의도가 명확해집니다.

---

### 3.7 [전체] 문서 간 Cross-Reference 부재

v4 문서들은 각 레이어를 독립적으로 기술하고 있으나, 문서 간 참조가 불충분합니다:
- RT 문서에서 FailureHandling 문서로의 참조 없음
- Triggers 문서에서 VXP 문서로의 참조 없음
- EP 문서에서 RT로의 `ml.data.synced` 후속 처리 릴레이 언급이 있으나, RT 문서에는 해당 수신 처리가 없음

> [!TIP]
> **권고**: 각 문서 상단에 `Related Documents` 섹션을 추가하여 연관 문서를 명시하면 전체 설계의 추적성(Traceability)이 향상됩니다.

---

## 4. 리뷰 항목 자체 검증 (Validation)

각 리뷰 항목의 타당성을 v3 원본 문서와의 교차 검증으로 확인합니다.

| # | 리뷰 항목 | 검증 근거 (v3 원본) | 타당성 |
|---|----------|-------------------|--------|
| 1.1 | EP Sync 완료 후 처리 주체 | `Execution_Sequence_default.md` L69-75: EP가 `ml.data.synced` 수신 후 직접 `ml.preprocess.requested` 발행 / `Topic_Specification.md`: `ml.data.synced` Subscriber = EP | ✅ **타당** |
| 1.2 | RT Idempotency Guard 순서 | `Failure_Handling_State_Machine.md` L13-24: idempotency 확인과 상태 업데이트가 동일 트랜잭션 흐름 | ✅ **타당** |
| 1.3 | Cancel Handler RETRYING 분기 | `Execution_Sequence_Cancel.md` L49-67: RETRYING 상태에서 CT 취소 후 CANCELLING 전이 명시 | ✅ **타당** |
| 1.4 | Triggers Postprocess 경로 | `Execution_Sequence_default.md` L180-211: Postprocess는 VXP 없이 TRG→EXP 동기 호출 | ✅ **타당** |
| 2.1-2.4 | 과잉 설계 검토 | v3 대비 자연스러운 구체화이며, 새로운 불필요한 추상화 계층 추가 없음 | ✅ **타당** |
| 3.1 | Run 완료 발행 누락 | `Execution_Sequence_default.md` L214-225: next_step=null 시 COMPLETED + ml.run.completed 발행 | ✅ **타당** |
| 3.2 | ml.run.cancelled 누락 | `Execution_Sequence_Cancel.md` L38, 59: CANCELLED 후 ml.run.cancelled 발행 | ✅ **타당** |
| 3.3 | Data Sync 재시도 분기 | `Run-level_State_Machine.md` L31: sync_attempt 기반 재시도/FAILED 분기 | ✅ **타당** |
| 3.4 | VXP Data Locator 표기 | `Execution_Sequence_default.md` L97: VXP가 GCS staged 데이터를 읽음 (S3 직접 아님) | ✅ **타당** |
| 3.5 | Checksum 재시도 종료 조건 | v3 `Step-level_State_Machine_(postprocess).md`: 검증 실패 시 SYNC_FAILED 전이 (무한 재시도 아님) | ✅ **타당** |
| 3.6 | Manual Retry 우회 설명 | `Failure_Handling_State_Machine.md` L58-62: attempt 리셋 후 진입 경로 정의 | ✅ **타당** |
| 3.7 | Cross-Reference 부재 | v3는 단일 Sequence 문서에서 전체 흐름 추적 가능했으나, v4 분리 후 개별 추적이 어려움 | ✅ **타당** |

---

## 5. 종합 평가

| 분류 | 건수 | 심각도 |
|------|------|--------|
| 설계 오류 | 4건 | 🔴 1.1 (High), 🟡 1.2-1.4 (Medium) |
| 과잉 설계 | 0건 | — |
| 개선 권고 | 7건 | 🟡 3.1-3.2 (Medium), 🟢 3.3-3.7 (Low) |

### 총평

v4 설계는 v3의 단일 Sequence 기반 설계를 C4 Component Layer로 **적절하게 분리·구체화**하였으며, 과잉 설계 없이 각 컴포넌트의 책임을 명확히 정의하고 있습니다. 특히 EXP의 AWS SDK Transfer Manager 도입, Triggers의 Stateless 환경 변수 패턴, RunAPI의 인증/인가 분리는 v3 리뷰 피드백을 충실히 반영한 결과입니다.

다만, v3에서 단일 문서로 추적 가능했던 몇 가지 흐름(Run 완료, Cancel 완료, Data Sync 재시도)이 레이어 분리 과정에서 **누락 또는 불일치**가 발생했습니다. 1.1번 이슈(EP Sync 완료 후 처리 주체)가 가장 심각한 정합성 오류이므로 우선 수정이 필요합니다.

---
---

# v4 독립 리뷰 (v4 문서만 기준)

> **리뷰 기준**: v4 문서 자체의 내적 일관성, 다이어그램 정확성
> **리뷰 일자**: 2026-02-28

---

### D.1 [EXP] AWS 임시 자격증명 흐름 대상 오류

**대상 파일**: `C4_Component_Layer_EXP.md` (L23)

**문제**: `AWS_STS -.->|"Temporary S3 Credentials"| GCS_READER`로 되어 있어 AWS 임시 자격증명이 `GCS_READER`로 주입됩니다. 그러나 `GCS_READER`는 **GCS에서 읽는 컴포넌트**이므로 GCP IAM 권한만 필요하고, AWS 자격증명은 **S3에 쓰는** `AWS_TM`(Transfer Manager)에 필요합니다.

| 현재 | 올바른 흐름 |
|------|------------|
| `AWS_STS → GCS_READER` | `AWS_STS → AWS_TM` |

> [!WARNING]
> **권고**: `AWS_STS -.->|"Temporary S3 Credentials"| AWS_TM`으로 수정해야 합니다.

---

### D.2 [RT] CANCELLING 상태 `ml.step.failed` 흡수 엣지 라우팅 오류

**대상 파일**: `C4_Component_Layer_RT.md` (L80)

**문제**: `EventBus_Fail -.->|"if state=CANCELLING"| CANCEL_HDLR`로 되어 있어, `ml.step.failed` 이벤트가 **Event Bus에서 직접 Cancel Handler로** 라우팅되는 것처럼 보입니다. 그러나 Event Bus는 상태 기반 라우팅을 수행하지 않으며, `ml.step.failed`는 항상 `FAIL_HDLR → STATE_TXN`을 거쳐 **트랜잭션 내부에서 상태를 확인**한 후 CANCELLING 흡수가 결정됩니다.

| 현재 | 올바른 흐름 |
|------|------------|
| `EventBus_Fail → CANCEL_HDLR` | `FAIL_HDLR → STATE_TXN → (if CANCELLING) → CANCELLED 흡수` |

> [!NOTE]
> **권고**: L80의 `EventBus_Fail → CANCEL_HDLR` 엣지를 삭제하고, `STATE_TXN`에서 `"if state=CANCELLING → absorb as CANCELLED"` 분기를 추가하면 실제 이벤트 처리 흐름과 일치합니다.

---

### 검증

| # | 리뷰 항목 | 근거 | 타당성 |
|---|----------|------|--------|
| D.1 | EXP 자격증명 대상 | `GCS_READER`는 "GCS Chunk Reader"로 GCS 읽기 전용. AWS 자격증명(`S3 PutObject`)은 S3에 쓰는 `AWS_TM`에 필요 | ✅ **타당** |
| D.2 | RT 이벤트 라우팅 | RT 구조에서 `EventBus_Fail` → `FAIL_HDLR` → `STATE_TXN` 경로가 이미 존재(L27, L32). Pub/Sub는 topic 기반 라우팅만 수행하며 상태 기반 분기 불가 | ✅ **타당** |

