# v3/C4_Component_Layer_VXP 변경 내역 표

**작업일**: 2026-02-28
**관련 리뷰 파일**: `review/C4_Component_Layer_VXP_Review.md`

| ID | 수정 대상 파일 | 수정 이유 | 수정 전 | 수정 후 |
|---|---|---|---|---|
| **E1** | `C4_Component_Layer_VXP.md` | 파이프라인의 개별 노드가 아닌 PipelineJob 런타임 수명 주기 통째로 알림 서비스와 연동되는 올바른 인프라 컴포넌트 멘탈 모델로 수정 | `PP_WRITE` 등 각각의 노드 컴포넌트 내부에서 `--> VXP_Notifier` 화살표가 뿜어져 나옴 | 개별 화살표 4개를 모두 지우고 각 Subgraph (전체 파이프라인 컨테이너 껍데기) 자체에서 `==> VXP_Notifier` 로 상태 이벤트를 라우팅 하도록 거시 구조로 표현 |
| **O1** | `C4_Component_Layer_VXP.md` | 모델 성능이 기준에 미달했다고 FAILED 에러를 던져 파이프라인의 장애 처리기(Retry 등)를 오동작 시키는 **치명적 MLOps Anti-Pattern** 수정 | 성능 미달 시 FAILED 상태로 반환, 상위의 Run Tracker가 시스템 에러로 파악하여 **무한 재시도 및 DLQ 이관** | 임계치 미달 시 Model Registry 단계만 스킵하고 파이프라인 자체는 정상(`SUCCEEDED`) 완료되도록 분기 종료 표기 및 설명 추가 |
| **I1** | `C4_Component_Layer_VXP.md` | Batch Prediction Job 생성 파라미터로 Model Registry ID를 직접 넘기면 자동으로 해석되어 구동되는 점을 활용, 쓸모없는 Model 물리 경로 반환 컴포넌트 노드 삭제 | 추론 파이프라인 내부에 `Model Artifact Fetcher` 컴포넌트 존재 | 불필요 컴포넌트 노드(`IN_MODEL`) 삭제 및 Batch Job이 파라미터를 자체 해석한다는 코드 최적화 명시 |
