# v3/C4_Component_Layer_FailureHandling 변경 내역 표

**작업일**: 2026-02-28
**관련 리뷰 파일**: `review/C4_Component_Layer_FailureHandling_Review.md`

| ID | 수정 대상 파일 | 수정 이유 | 수정 전 | 수정 후 |
|---|---|---|---|---|
| **E1** | `C4_Component_Layer_FailureHandling.md` | 수동 복구(Manual Invoker) 시 이미 해결된 실패 건을 불필요하게 [실패 백오프 연산 큐(Retry Assessor)]에 집어넣는 라우팅 이벤트 오남용, 즉시 재실행 안되는 논리적 한계 극복 | `MANUAL_INVOKER -->|"push to process flow"\| RETRY_ASSESS` 로 진입하여 평가기를 다시 통과해야 함 | `MANUAL_INVOKER`에서 `fs.attempt=0 / state=STEP_RUNNING` 후 대상 토픽 `ml.{step}.requested` 으로 즉시 직행(`Bypass Publish`) 하도록 명세 아키텍처 우회 |
| **O1** | `C4_Component_Layer_FailureHandling.md` | 앱 레벨에서 모니터링 포맷팅, Alerting 템플릿, 알람 Push 클라이언트를 각각 직접 짜는 클라우드 안티 패턴 (거대한 컴포넌트 바퀴 재발명) 제거 | 알람 발송용의 거대한 `OBS_PUSH`, `ALERT_RENDER`, `MON_CLIENT` 3개 커스텀 컴포넌트 계층 존재 | 애플리케이션은 순수 JSON 로그 기반 컴포넌트(`LOG_CLIENT`)만 유지하고, 나머지는 모두 GCP 네이티브 `Log-based Alerting` 인프라로 완전 통폐합하여 위임 처리 |
| **I1** | `C4_Component_Layer_FailureHandling.md` | 단일 책임 원칙 (SRP) 고도화. DLQ Router는 "이벤트를 DLQ로 쏘는 일"만 책임지도록 화살표 다이어트 개선 | `DLQ_ROUTER` 혼자서 `state=FAILED` 업데이트, DLQ 펍섭 송신, `OBS_PUSH` 연동 등 세 가지 역할을 동시 관장 | 코어의 STATE_MGR에게 트랜잭션을 위임(RT 도면 참조)하고 순수하게 `ml.dead-letter` 포워딩 임무만 표기토록 개선 |
