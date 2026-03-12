# C4 Component Layer - Run Request API 리뷰

**작성일**: 2026-02-28
**대상**: `v3/C4_Component_Layer_RunAPI.md`
**관점**: 설계 오류(Errors), 과잉 설계(Over-engineering), 개선점(Improvements)

---

## ❌ 설계 오류 (Design Errors) & 타당성 검증

### [E1] Amazon EventBridge 인증 메커니즘 설정 오류 (가상의 토큰 검증기)
- **설명**: 다이어그램 내 `AWS OIDC Token Verifier` 컴포넌트가 명시되어 있고, EB_AWS가 "AWS OIDC token"을 보낸다고 기술되어 있습니다. 이는 **AWS EventBridge API Destination**의 동작을 오해한 설계 오류입니다. EventBridge는 외부 HTTPS 엔드포인트 호출 시 AWS 자체 서명 OIDC 토큰을 동적으로 발행하여 주입하지 않습니다.
- **올바른 아키텍처**: EventBridge가 GCP Cloud Run을 인증된 상태로 호출하려면 API Destination의 **OAuth (Client Credentials)** 기능을 사용하여 사전에 GCP Token Endpoint(`oauth2.googleapis.com`)에서 교환한 **GCP OIDC 토큰**을 Bearer로 전송해야 합니다. 결과적으로 API가 수신하는 것은 AWS 토큰이 아니라 "GCP Service Account OIDC 토큰"입니다.
- **타당성 검증(Validation)**: AWS EventBridge 공식 문서의 API Destination Auth 유형(Basic, API Key, OAuth) 대조를 통해 증명 완료. 기술적으로 존재하지 않는 토큰을 검증하려 하므로 명백한 설계 오류이자 구현 불가능한 스펙입니다.

---

## ⚙️ 과잉 설계 (Over-engineering) & 타당성 검증

### [O1] Cloud Run IAM 인프라 보안을 배제한 애플리케이션 레벨 인증(AuthN) 구현
- **설명**: FastAPI 코드 베이스 내부(`Authentication Layer`)에 3가지 분기된 Token Verifier(AWS_OIDC, GCP_SA, OAUTH) 컴포넌트를 명시적으로 개발하도록 설계되었습니다. 이는 배포 환경이 **GCP Cloud Run**이라는 맥락을 놓친 전형적인 과잉 설계입니다.
- **올바른 아키텍처**: EventBridge(OAuth 연동), Cloud Scheduler, DE 운영자(gcloud/UI) 이 3가지 Caller는 모두 최종적으로 **Google 서명 JWT (OIDC/OAuth)**를 API로 전송할 수 있습니다. Cloud Run 서비스 설정을 `--no-allow-unauthenticated`로 배포하면 프록시(GCP Front End)에서 토큰 서명 유효성 및 인가를 대신 검증합니다. 애플리케이션 코드는 `X-Email` 이나 JWT 페이로드에서 식별자만 추출하여 바로 Authorization(RBAC) 레이어로 넘기면 됩니다.
- **타당성 검증(Validation)**: 프레임워크 레벨에서 암호학적 서명 검증 코드를 직접 구현(3-tier)하고 유지 보수하는 것은 높은 보안 리스크와 개발 부채를 야기합니다. 인프라 매니지드 서비스를 완벽하게 활용할 수 있는 상황에서 코드 레벨로 끌어내린 설계는 인프라-코드 간의 명확한 안티 패턴입니다.

---

## 💡 개선점 (Improvements) & 타당성 검증

### [I1] 컴포넌트 의존성(Dependency) 역전 표기 (FastAPI)
- **설명**: 다이어그램의 흐름 화살표가 `AuthN -> ROUTER -> SCHEMA` 순서의 절차적 실행 흐름으로 그려져 있습니다. C4 Component Diagram은 기능적 절차보다 **컴포넌트 간의 의존성**을 그려야 합니다.
- **올바른 아키텍처**: FastAPI 환경에서 인증/인가 및 검증은 라우터의 의존성 주입(`FastAPI Depends`) 패턴으로 동작합니다. 따라서 제어의 주체인 `Request Router`가 `Authenticator`와 `RBAC Manager`, `Schema Validator`를 의존하여(가리키는) 형태로 화살표(`ROUTER --> AuthN`)가 구성되어야 합니다.
- **타당성 검증(Validation)**: 엔터프라이즈 아키텍처를 FastAPI로 분리할 때, 인증을 외부 미들웨어로 보지 않는 한 Router 모듈이 Security 모듈에 의존하는 것이 C4 Component Diagram의 올바른 뷰 포인트입니다.

---

## 요약 (권고안)
해당 Component Layer의 `Authentication Layer` 컨테이너 자체를 삭제 또는 **Cloud Run IAM (Managed)** 엔티티로 승격/분리하고, FastAPI 애플리케이션의 핵심 로직은 `Subject Extractor`와 `RBAC Manager`로 간소화하는 방향으로 구조를 재수립할 것을 강력히 권고합니다.
