# v3/C4_Component_Layer_RT 변경 내역 표

**작업일**: 2026-02-28
**관련 리뷰 파일**: `review/C4_Component_Layer_RT_Review.md`

| ID | 수정 대상 파일 | 수정 이유 | 수정 전 | 수정 후 |
|---|---|---|---|---|
| **E1** | `C4_Component_Layer_RT.md` | Postprocess 단계는 VXP를 쓰지 않으므로 Cancel 발생 시 NullPointerException으로 인한 크래시 방지용 방어 전이 논리 추가 | `CANCEL_HDLR -.->\|"if STEP_RUNNING"\| VXP_CLIENT` | `CANCEL_HDLR -.->\|"if STEP_RUNNING & pipeline_job_id != null"\| VXP_CLIENT` |
| **O1** | `C4_Component_Layer_RT.md` | Cloud Tasks에 예약된 지연 재시도를 직접 삭제하기 위한 `task_name` 저장 비용 등 과잉 상태 관리 로직 제거 ("상태 기반 이벤트 무력화" 우회로 도입) | `CANCEL_HDLR -.->\|"if RETRYING"\| CT_CLIENT -.->\|"cancel scheduled task"\| CloudTasks` | Task 명시적 취소 로직 삭제. Task 실행 시 상태머신이 `CANCELLED` 검토로 자연 무시하도록 주석(\n상태가 CANCELLED면 무시됨) 추가 |
| **I1** | `C4_Component_Layer_RT.md` | Idempotency 처리, Execution Plan 읽기, State 업데이트로 쪼개져 3번 발생하는 Firestore 연산의 지연과 Race Condition 방지를 위해 단일 트랜잭션으로 응집 | 개별 `IDEMP_GUARD`, `PLAN_NAV`, `STATE_MGR` 흐름 및 DB I/O 화살표 3개 | `State Transition Transaction` 컴포넌트로 병합하여 단일 ACID 통제 및 I/O 최적화 달성 |
