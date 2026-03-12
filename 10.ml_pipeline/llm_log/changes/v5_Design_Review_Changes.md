# v5 Design Review — 변경 작업 내역

> 리뷰 문서: `v5_Design_Review.md`
> 작업 일자: 2026-02-28

---

| # | 유형 | 대상 파일 | 리뷰 항목 | Before | After | 상태 |
|---|------|----------|----------|--------|-------|------|
| R.1 | 🟡 오류 | `v3/Topic_Specification.md` | `run.state` 열거형에 `AWAITING_MANUAL`, `TERMINATED` 누락 | 13개 상태만 열거 | `AWAITING_MANUAL \| TERMINATED` 추가 (15개) | ✅ 완료 |
| R.2 | 🟡 오류 | `v3/Execution_Sequence_default.md` | 존재하지 않는 `Execution_Sequence_DataSync_Failure.md` 참조 | `상세 분기: Execution_Sequence_DataSync_Failure.md 참조` | `상세 분기: Run-level_State_Machine.md DATA_SYNCING 상태 전이 참조` | ✅ 완료 |
| R.3 | 🟡 불일치 | `v3/Run-level_State_Machine.md` | 수동 재시도 시 `FAILED → RETRYING` 전이 (v4와 불일치) | `FAILED → RETRYING` (RETRY_ELIGIBLE 경유, Cloud Tasks 지연) | `FAILED → STEP_RUNNING` (RT 우회, 즉시 실행) | ✅ 완료 |
| R.3 | 🟡 불일치 | `v3/Failure_Handling_State_Machine.md` | `AWAITING_MANUAL → RETRY_ELIGIBLE` 경로 설명 미흡 | `수동 재처리 트리거 (run.attempt 리셋 후 진입)` | `run.attempt=0 리셋, state=STEP_RUNNING 갱신 후 RT 우회하여 직접 발행` | ✅ 완료 |

---

## 요약

| 리뷰 항목 | 건수 | 수정 파일 수 | 상태 |
|----------|------|------------|------|
| run.state 열거형 누락 | 1건 | 1개 | ✅ 완료 |
| 미존재 문서 참조 | 1건 | 1개 | ✅ 완료 |
| v3↔v4 상태 전이 불일치 | 1건 | 2개 | ✅ 완료 |
| **합계** | **3건** | **4개 파일** | **✅ 전체 완료** |
