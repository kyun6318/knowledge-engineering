# v4 Design Review — 변경 작업 내역

> 리뷰 문서: `v4_Design_Review.md`, `Design_Review_v4.md`
> 작업 일자: 2026-02-28

---

## 1차 리뷰 (v3 기반) — `v4_Design_Review.md` §1-3

| # | 유형 | 대상 파일 | 리뷰 항목 | Before | After | 상태 |
|---|------|----------|----------|--------|-------|------|
| 1.1 | 🔴 오류 | `EP.md` | Staging Orchestrator Sync 완료 후 처리 주체 | RT로 릴레이 | EP가 직접 `ml.preprocess.requested` 발행 | ✅ 완료 |
| 1.2 | 🟡 오류 | `RT.md` | Idempotency Guard / State Manager 분리 | `IDEMP_GUARD` → `STATE_MGR` 별개 노드 | 단일 `STATE_TXN` 노드로 병합 (TOCTOU 제거) | ✅ 완료 |
| 1.3 | 🟡 오류 | `RT.md` | Cancel Handler RETRYING 분기 누락 | STEP_RUNNING 분기만 | RETRYING → CT 취소 시도 분기 추가 | ✅ 완료 |
| 1.4 | 🟡 오류 | `Triggers.md` | Postprocess의 VXP 미사용 경로 미명시 | VXP Forwarder만 표현 | Postprocess Trigger 서브그래프 (EXP 동기 호출) 추가 | ✅ 완료 |
| 3.1 | 🟡 개선 | `RT.md` | Run 완료 (`ml.run.completed`) 발행 경로 | 누락 | `next_step=null` → `COMPLETED` → `ml.run.completed` 발행 추가 | ✅ 완료 |
| 3.2 | 🟡 개선 | `RT.md` | Cancel 완료 (`ml.run.cancelled`) 발행 경로 | 누락 | `CANCELLED` 후 `ml.run.cancelled` 발행 추가 | ✅ 완료 |
| 3.3 | 🟢 개선 | `EP.md` | Data Sync 실패 시 재시도 분기 | `ml.data.sync.failed → STG_ORCH`만 | `sync_attempt` 기반 재시도 / FAILED 분기 추가 | ✅ 완료 |
| 3.4 | 🟢 개선 | `VXP.md` | Data Locator 데이터 소스 표기 | `"Read S3 Data via STS"` | `"Read from GCS Staging"` | ✅ 완료 |
| 3.5 | 🟢 개선 | `EXP.md` | Checksum 재시도 종료 조건 | 미정의 (무한 루프 가능) | `최대 1회 재전송 → HTTP 500` 명시 | ✅ 완료 |
| 3.6 | 🟢 개선 | `FailureHandling.md` | Manual Retry Invoker 우회 설명 | 의도 불명확 | DLQ 상태에서 RT 우회 사유 + attempt 리셋 근거 보충 | ✅ 완료 |
| 3.7 | 🟢 개선 | 전체 7개 파일 | Related Documents 섹션 | 없음 | 모든 문서에 Related Documents 링크 추가 | ✅ 완료 |

---

## 2차 리뷰 (v3 기반) — `Design_Review_v4.md` §1-3

| # | 유형 | 대상 파일 | 리뷰 항목 | Before | After | 상태 |
|---|------|----------|----------|--------|-------|------|
| 1.1 | 🟡 오류 | `RT.md` | Cancel 타임아웃 → FAILED 전이 경로 | cancel 성공만 표현 | `VXP_CLIENT → CANCEL_FAIL → DLQ_ROUTER` 경로 추가 | ✅ 완료 |
| 1.2 | 🟡 오류 | `RT.md` | CANCELLING 중 `ml.step.failed` Race Condition | 누락 | CANCELLING 상태에서 retry 없이 CANCELLED 흡수 정책 추가 | ✅ 완료 |
| 1.3 | 🟢 오류 | `EP.md` | `DATA_SYNCING` / `STEP_RUNNING` 상태 업데이트 | 다이어그램 미표현 | `STG_ORCH → FS_CLIENT` 경로에 상태 업데이트 추가 | ✅ 완료 |
| 1.4 | 🟢 오류 | `Triggers.md` | Postprocess `sync_target=none` 단축 경로 | 항상 EXP 호출 | `PP_DEC → PP_PS` 직행 분기 추가 | ✅ 완료 |
| 3.1 | 🟢 개선 | `RT.md` | `cancel_requested_at` 기록 시점 | Component Details 미언급 | CANCELLING 전이 시 기록 명시 | ✅ 완료 |
| 3.2 | 🟢 개선 | `EP.md` | Secret Manager 조회 누락 설명 | 미설명 | EXP로 이관 결정 근거 Component Details에 명시 | ✅ 완료 |
| 3.3 | 🟢 개선 | `EP.md` | Lock 실패 시 `duplicate_events` 감사 기록 | `Log & ACK`만 | `FS_CLIENT`에 `duplicate_events` 기록 경로 추가 | ✅ 완료 |
| 3.4 | 🟢 개선 | `FailureHandling.md` | CT 생성 실패 → DLQ 즉시 라우팅 | 미표현 | `CT_CLIENT → DLQ_ROUTER` 실패 경로 추가 | ✅ 완료 |
| 3.5 | 🟢 개선 | `FailureHandling.md` | `TERMINATED` 상태 | 미표현 | `Operator → TERMINATED` 경로 + Component Details 추가 | ✅ 완료 |

---

## v4 독립 리뷰 — `v4_Design_Review.md` §D

| # | 유형 | 대상 파일 | 리뷰 항목 | Before | After | 상태 |
|---|------|----------|----------|--------|-------|------|
| D.1 | 🟡 오류 | `EXP.md` | AWS 임시 자격증명 흐름 대상 | `AWS_STS → GCS_READER` | `AWS_STS → AWS_TM` | ✅ 완료 |
| D.2 | 🟡 오류 | `RT.md` | CANCELLING 흡수 엣지 라우팅 | `EventBus_Fail → CANCEL_HDLR` | `STATE_TXN → PS_CLIENT` (트랜잭션 내부 분기) | ✅ 완료 |

---

## 요약

| 리뷰 라운드 | 설계 오류 | 개선 권고 | 합계 | 적용 상태 |
|------------|----------|----------|------|----------|
| 1차 (v3 기반) | 4건 | 7건 | 11건 | ✅ 전체 완료 |
| 2차 (v3 기반) | 4건 | 5건 | 9건 | ✅ 전체 완료 |
| v4 독립 리뷰 | 2건 | 0건 | 2건 | ✅ 전체 완료 |
| **합계** | **10건** | **12건** | **22건** | **✅ 전체 완료** |
