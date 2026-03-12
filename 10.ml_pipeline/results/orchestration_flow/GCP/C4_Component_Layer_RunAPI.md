> **Related Documents**: [C4_Component_Layer_EP.md](./C4_Component_Layer_EP.md) (Execution Planner — 요청 수신 후속 처리), [C4_Component_Layer_RT.md](./C4_Component_Layer_RT.md) (Run Tracker — Cancel 요청 처리)

```mermaid
graph TD
  subgraph AuthN["Cloud Run IAM (Managed)"]
    IAM_AUTH["Token Signature & Expiry Verifier\n(--no-allow-unauthenticated)"]
  end

  subgraph API_Core["API Core Mechanisms"]
    ROUTER["Request Router (FastAPI)"]
    EXTRACTOR["Subject Extractor"]
    RBAC["Project-level RBAC Manager"]
    FS_Pol["Firestore Policy Store"]
    SCHEMA["Schema Validator (Pydantic)"]
    PS_CLIENT["Pub/Sub Publisher Client"]
  end

  %% 외부 트리거 (Caller)
  EB_AWS([Amazon EventBridge])
  CloudSched([Cloud Scheduler])
  DE([DE-MLE Operator])

  %% 인증 흐름
  EB_AWS -->|"HTTPS POST\n(GCP OIDC token via OAuth Client Creds)"| IAM_AUTH
  CloudSched -->|"HTTPS POST (GCP OIDC/SA)"| IAM_AUTH
  DE -->|"HTTPS POST (Google OAuth)"| IAM_AUTH

  IAM_AUTH -->|"Authenticated Request"| ROUTER

  %% 핵심 로직 흐름 (의존성 역전)
  ROUTER -->|"1. extract subject"| EXTRACTOR
  ROUTER -->|"2. check permission"| RBAC
  RBAC -->|"read policy"| FS_Pol
  ROUTER -->|"3. validate schema"| SCHEMA
  
  ROUTER -->|"4. construct message"| PS_CLIENT

  %% 외부 시스템 연결
  PS_CLIENT -->|"publish ml.run.requested"| EventBus[(Pub/Sub Event Bus)]
  PS_CLIENT -->|"publish ml.run.cancel.requested"| EventBus

  %% 스타일 적용
  classDef comp fill:#f9f,stroke:#333,stroke-width:2px;
  class IAM_AUTH,EXTRACTOR,RBAC,ROUTER,SCHEMA,PS_CLIENT comp;
```

### Component Details
1. **Cloud Run IAM (Managed)**: Cloud Run의 `--no-allow-unauthenticated` 인프라 설정을 통해 진입하는 모든 요청(AWS EventBridge, Cloud Scheduler, DE)의 JWT 서명과 만료 여부를 검증합니다. EventBridge 호출 시 API Destination의 OAuth 설정으로 부여받은 GCP OIDC 토큰을 파싱합니다.
2. **Subject Extractor**: 검증을 통과한 요청 헤더(`X-Email` 또는 Auth JWT Payload)에서 호출자의 식별자(Subject)를 추출하는 모듈입니다.
3. **Request Router**: FastAPI 컨트롤러로, 하위 모듈들에 대한 의존성 주입(Dependency Injection)을 기반으로 실행 흐름을 통제합니다.
4. **Project-level RBAC Manager**: 추출된 식별자가 대상 `project`에 대해 실행(Run) 또는 취소(Cancel) 권한이 있는지 Firestore 정책상에서 확인합니다.
5. **Schema Validator**: `ml.run.requested`의 필수 파라미터(project, run_key_hint 등) 정합성을 Pydantic 모델을 통해 검증합니다.
6. **Pub/Sub Publisher Client**: 인가 및 검증이 모두 완료된 요청을 `ml.run.requested` 또는 `ml.run.cancel.requested` 이벤트로 규격화하여 비동기 발행합니다.
