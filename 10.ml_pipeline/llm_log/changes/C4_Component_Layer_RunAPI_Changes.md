# v3/C4_Component_Layer_RunAPI 변경 내역 표

**작업일**: 2026-02-28
**관련 리뷰 파일**: `review/C4_Component_Layer_RunAPI_Review.md`

| ID | 수정 대상 파일 | 수정 이유 | 수정 전 | 수정 후 |
|---|---|---|---|---|
| **E1** | `C4_Component_Layer_RunAPI.md` | AWS EventBridge API Destination 동작 오해 (AWS OIDC 토큰이 아니라 GCP OIDC 발급 후 전송) | `EB_AWS -->\|"HTTPS POST (OIDC token)"\| AWS_OIDC` | `EB_AWS -->\|"HTTPS POST (GCP OIDC token via OAuth Client Creds)"\| IAM_AUTH` |
| **O1** | `C4_Component_Layer_RunAPI.md` | Cloud Run IAM을 무시하고 애플리케이션 프레임워크 내부에 Token 검증 로직 3종을 생성하는 과잉 구조 제거 | `subgraph AuthN`, `AWS_OIDC`, `GCP_SA`, `OAUTH` 컴포넌트들 자체 구현 명시 | 관리형 `IAM_AUTH`(`Cloud Run IAM (--no-allow-unauthenticated)`) 엔티티 하나로 모두 통합 및 `Subject Extractor` 추가 |
| **I1** | `C4_Component_Layer_RunAPI.md` | FastAPI 라우터의 의존성(Dependency Injection) 방향 부합화 | `AuthN -> ROUTER -> SCHEMA / RBAC` (순차적 실행 흐름) | `ROUTER --> EXTRACTOR / RBAC / SCHEMA` (의존성 역전 구조) |
