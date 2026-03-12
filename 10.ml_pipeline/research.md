# ML Pipeline을 AWS에 통합하지 않고 GCP 별도 환경으로 구축하는 것에 대한 분석

> 본 문서는 `ml-platform/designs/` 설계 문서 18개를 정밀 분석하여, 기존 AWS 인프라와 별도로 GCP에 ML Pipeline 환경을 구축하는 아키텍처 결정의 장점, 단점, 트레이드오프를 상세히 기술합니다.

---

## 1. 현재 아키텍처 요약

### 1.1 전체 구조
```
AWS Data Account          GCP ML Environment           AWS Service Domain
┌──────────────┐    ┌──────────────────────────┐    ┌──────────────────┐
│ S3 (dataset)  │───→│ RunAPI (Cloud Run)        │    │ S3 (artifacts)   │
│ EventBridge   │    │ Pub/Sub (Event Bus)       │    │ S3 (results)     │
│ Data Platform │    │ EP / RT (Cloud Functions)  │    │ Serving API      │
│               │    │ Cloud Tasks (지연 발행)    │───→│ Result Ingest    │
│               │    │ Vertex AI Pipelines       │    │ Service DB       │
│               │    │ Firestore (상태 관리)      │    │ Observability    │
│               │    │ Storage Transfer Service   │    └──────────────────┘
│               │    │ Cross-Cloud Exporter (EXP) │
│               │    └──────────────────────────┘
└──────────────┘
```

### 1.2 핵심 데이터 흐름
1. **Inbound** (AWS → GCP): S3 dataset → EventBridge → RunAPI → STS(S3→GCS) → Vertex AI Pipelines
2. **Compute**: GCS staging → Preprocess → Train → Infer (모두 Vertex AI)
3. **Outbound** (GCP → AWS): GCS artifacts/results → EXP(WIF + AssumeRole) → S3 → ResultIngest → Service DB

### 1.3 사용되는 GCP 서비스
| 범주 | 서비스 |
|------|--------|
| **Compute** | Cloud Run, Cloud Functions (×6+), Vertex AI Pipelines, Vertex AI Training/BatchPred |
| **Orchestration** | Pub/Sub (10+ topics), Cloud Tasks, Eventarc, Cloud Scheduler |
| **Storage** | GCS (staging/artifacts/results), Firestore (5 collections) |
| **ML** | Vertex AI Model Registry, Artifact Registry (container images) |
| **Security** | Cloud Run IAM, Secret Manager, Workload Identity Federation |
| **Monitoring** | Cloud Monitoring, Cloud Logging, Log-based Alerting |

---

## 2. GCP 별도 환경 구축의 장점

### 2.1 Vertex AI Pipelines — ML 전용 매니지드 오케스트레이션

**핵심 가치**: Kubeflow SDK 기반 파이프라인 정의 → 자동 DAG 실행 → GPU/TPU 네이티브 지원

- **설계 문서 근거** (`C4_Component_Layer_VXP.md`):
  - Preprocess, Train, Infer 파이프라인이 Kubeflow 컴포넌트로 선언적 정의됨
  - Train Pipeline의 `Threshold Gating Node`가 파이프라인 내부 조건부 분기를 자연스럽게 표현
  - `Custom Training Job (GPU/TPU)` — Vertex AI에서 GPU/TPU 인스턴스를 on-demand로 할당
  - Batch Prediction Job — 대규모 추론을 Vertex AI 네이티브 기능으로 병렬 실행

- **AWS 대비 우위**:
  - AWS SageMaker Pipelines도 유사 기능을 제공하지만, Kubeflow 호환성과 커스텀 컨테이너 유연성에서 Vertex AI가 더 성숙함
  - TPU 접근성: Google의 TPU는 GCP에서만 사용 가능. LLM Fine-tuning이나 대규모 Embedding 학습에서 TPU v4/v5 활용 시 비용 대비 성능이 SageMaker의 GPU 인스턴스 대비 우수할 수 있음
  - Vertex AI Model Registry와 네이티브 통합 — 모델 버전 관리, 메트릭 추적이 파이프라인과 긴밀히 결합

### 2.2 이벤트 기반 아키텍처의 자연스러운 구현

**핵심 가치**: Pub/Sub + Eventarc + Cloud Tasks 조합으로 복잡한 비동기 워크플로를 선언적으로 구성

- **설계 문서 근거** (`Topic_Specification.md`, `C4_Container_Layer.md`):
  - 10+ Pub/Sub topics로 `ml.{domain}.{action}` 네이밍 컨벤션의 일관된 이벤트 버스 구현
  - `ordering key = run_id`로 동일 run 내 이벤트 순서 보장
  - Cloud Tasks의 `scheduleTime` 기반 지연 발행으로 exponential backoff 재시도를 sleep 없이 구현
  - Eventarc가 STS 완료/실패 이벤트를 자동으로 Pub/Sub 토픽으로 라우팅

- **AWS 대비 우위**:
  - AWS에서 동일 구조를 구현하려면 SNS + SQS + EventBridge + Step Functions을 조합해야 하며, 각 서비스 간 설정 복잡도가 높음
  - Pub/Sub의 ordering key는 SQS FIFO Queue의 MessageGroupId보다 설정이 간결하고 throughput 제한이 적음
  - Cloud Tasks의 HTTP target 기반 지연 실행은 SQS delay queue + Lambda 트리거보다 직관적
  - Pub/Sub native DLQ (max_delivery_attempts=5)와 Application-level DLQ (`ml.dead-letter`) 이중 안전망이 GCP 네이티브로 깔끔하게 분리됨

### 2.3 Firestore 기반 상태 관리의 단순성

**핵심 가치**: 서버리스 NoSQL DB로 run 상태 머신을 트랜잭션 보장하에 구현

- **설계 문서 근거** (`C4_Component_Layer_RT.md`, `Failure_Handling_State_Machine.md`):
  - `Idempotency Check & State Transition Transaction` — 단일 Firestore 트랜잭션으로 TOCTOU 방지
  - `create-if-absent` 조건부 쓰기로 낙관적 잠금(Optimistic Lock) 구현
  - 5개 컬렉션 (`run`, `execution_plan`, `lock`, `duplicate_events`, `audit_events`)으로 전체 상태 모델링

- **AWS 대비 우위**:
  - DynamoDB도 유사하게 가능하지만, Firestore의 트랜잭션은 여러 문서를 아토믹하게 읽기/쓰기 가능 (DynamoDB TransactWriteItems의 25개 항목 제한 대비 유연)
  - Firestore의 실시간 리스너(onSnapshot)를 활용한 운영 대시보드 구축이 용이
  - 서버리스 자동 스케일링으로 별도 용량 관리 불필요

### 2.4 Cloud Functions 기반 마이크로 컨트롤러 패턴

**핵심 가치**: 각 컴포넌트가 독립적인 서버리스 함수로 분리되어 관심사 분리와 독립 배포 가능

- **설계 문서 근거** (`C4_Container_Layer.md`, `C4_Component_Layer_Triggers.md`):
  - Pipeline Triggers가 4개 독립 Cloud Functions (`Preprocess/Train/Infer/Postprocess Trigger`)
  - EP, RT가 각각 독립 Cloud Function으로 이벤트별 독립 확장
  - Trigger의 Stateless 설계 — 환경 변수(ENV)와 Payload만으로 실행, Firestore 조회 불필요

- **AWS 대비 우위**:
  - Lambda와 유사하지만, Cloud Functions의 Pub/Sub 직접 트리거는 Lambda + SQS/SNS 구성보다 설정이 간결
  - Vertex AI 상태 변경 이벤트를 Pub/Sub notification으로 직접 수신하는 패턴이 GCP 생태계에서 네이티브 지원

### 2.5 Cross-Cloud 인증 — Workload Identity Federation

**핵심 가치**: 장기 자격증명(Long-lived credentials) 없이 GCP↔AWS 간 안전한 인증

- **설계 문서 근거** (`C4_Component_Layer_EXP.md`):
  - `WIF Token Exchanger` → Google OIDC Token 발행 → `AssumeRoleWithWebIdentity` → 임시 S3 자격증명
  - Secret Manager에는 `AWS_ROLE_ARN + externalId`만 저장 (AWS Access Key 저장 불필요)
  - STS 세션 토큰 재사용으로 `sync_target=both` 시 재인증 불필요

- **보안적 이점**:
  - AWS Access Key/Secret Key가 GCP 환경에 존재하지 않음 → 자격증명 유출 위험 원천 차단
  - 토큰 수명이 제한적(기본 1시간) → 유출되더라도 피해 범위 한정
  - AWS IAM Role의 Trust Policy에서 GCP SA의 OIDC issuer를 명시적으로 허용 → 최소 권한 원칙 적용

### 2.6 Storage Transfer Service — 관리형 크로스 클라우드 데이터 이동

**핵심 가치**: S3→GCS 데이터 전송을 매니지드 서비스로 처리

- **설계 문서 근거** (`C4_Component_Layer_EP.md`, `Execution_Sequence_default.md`):
  - EP가 STS를 트리거하고 즉시 반환 → 비동기 완료 대기 (Eventarc 경유)
  - manifest 검증 + 전송 상태 추적 내장
  - 에러 코드별 재시도: `ACCESS_DENIED(max 2)`, `TRANSFER_TIMEOUT(max 2)`, `MANIFEST_INVALID(no retry)`, `GCS_WRITE_ERROR(max 2)`

- **AWS 대비 우위**:
  - AWS DataSync나 직접 S3→S3 복사보다 GCS STS가 GCP 생태계와 자연스럽게 통합
  - Eventarc를 통한 이벤트 기반 완료 알림이 네이티브 지원

### 2.7 비용 최적화 가능성

- **GPU/TPU 가격**: GCP의 Spot/Preemptible VM은 특히 학습 워크로드에서 AWS Spot Instance 대비 경쟁력 있는 가격
- **서버리스 컴포넌트**: Cloud Functions + Pub/Sub + Firestore는 사용량 기반 과금으로, 파이프라인이 실행되지 않을 때 비용 제로
- **GCS 비용**: S3 대비 egress fee가 낮은 경우가 있으며, 특히 Vertex AI와 같은 리전 내 서비스와 데이터 이동 시 무료

---

## 3. GCP 별도 환경 구축의 단점

### 3.1 크로스 클라우드 데이터 전송 오버헤드

**핵심 문제**: 모든 파이프라인 실행마다 AWS↔GCP 간 데이터 왕복 필수

- **Inbound** (S3 → GCS via STS): 학습 데이터셋 전체를 매번 또는 변경분 동기화
  - 네트워크 지연 + 전송 시간이 파이프라인 전체 latency에 추가
  - 대용량 데이터셋(수십~수백 GB)의 경우 STS 전송만 30분~수시간 소요 가능
  - STS 전송 실패 시 최대 2회 재시도 → 최악의 경우 전체 파이프라인 지연 ×3

- **Outbound** (GCS → S3 via EXP): 모델 아티팩트 + 추론 결과를 다시 AWS로 전송
  - EXP의 멀티파트 업로드 + Checksum 검증에 추가 시간 소요
  - `sync_target=both` 시 artifacts → results 순차 동기화 (병렬화 불가)
  - EXP HTTP 타임아웃 문제 (설계 문서 `I1` 개선 권고): CF timeout(60분) 초과 시 EXP Job은 계속 실행 → 고아 Job 발생 가능

- **네트워크 비용**:
  - GCS egress 비용: GCP → 외부(AWS) 전송 시 GB당 $0.08~$0.12
  - 매 파이프라인 실행 시 수~수십 GB의 양방향 전송 → 월간 상당한 네트워크 비용 발생
  - S3 → GCS 방향은 AWS egress fee + GCP ingress (무료) 구조

### 3.2 운영 복잡도 증가 — 듀얼 클라우드 관리

**핵심 문제**: 두 클라우드 환경의 동시 관리 필요

- **인프라 관리 이중화**:
  - AWS: IAM, EventBridge, S3, Lambda/ECS (ResultIngest), CloudWatch
  - GCP: Cloud Run IAM, Pub/Sub, Cloud Functions, Firestore, Vertex AI, STS, Secret Manager, Cloud Monitoring
  - IaC(Terraform/Pulumi) 설정이 두 프로바이더에 분산 → 코드 복잡도 증가

- **모니터링 분산**:
  - 설계에서 `Cloud Monitoring → Slack` 알림과 `AWS Observability (CloudWatch/Grafana)` 가 공존
  - 장애 발생 시 GCP 콘솔과 AWS 콘솔을 동시에 확인해야 함
  - 크로스 클라우드 구간(STS 전송, EXP 업로드)의 장애는 양쪽 모두 확인 필요

- **팀 역량 요구**:
  - GCP와 AWS 양쪽에 깊은 이해가 필요한 엔지니어 확보/양성
  - Vertex AI Pipelines, Kubeflow, Pub/Sub, Firestore 등 GCP 전용 서비스 학습 곡선
  - 온콜 엔지니어가 두 클라우드 환경을 모두 다룰 수 있어야 함

### 3.3 크로스 클라우드 인증의 복잡성과 실패 지점

- **WIF 인증 체인 길이**:
  ```
  GCP SA → Google OIDC Token → AWS STS AssumeRoleWithWebIdentity → Temporary S3 Credentials
  ```
  - 3단계 인증 체인의 각 단계가 실패 가능 지점
  - AWS IAM Trust Policy와 GCP WIF 설정 간 일관성 유지 필요
  - Token 만료(1시간)로 장시간 실행되는 EXP Job에서 토큰 갱신 필요

- **EventBridge → RunAPI 인증**:
  - API Destination + Connection에서 GCP OIDC 토큰 발급 → AWS에서 GCP 인증 토큰 관리
  - AWS 측에서 GCP Service Account 키 또는 OAuth Client Credentials 설정 필요

### 3.4 장애 격리의 양면성

- **GCP 장애 시**: ML 파이프라인 전체 중단 → AWS 서빙은 기존 모델로 계속 서비스 가능 (장점)
- **하지만**: GCP 장애 시 새 모델/추론 결과가 AWS로 전달되지 않음 → 서비스가 stale 데이터로 운영
- **크로스 클라우드 장애**: STS/EXP 구간 장애 시 GCP 내부는 정상이지만 결과가 AWS에 도달하지 못함 → 가장 디버깅이 어려운 케이스

### 3.5 데이터 거버넌스 및 규정 준수

- **데이터 이중 보관**: 동일 데이터가 S3와 GCS에 모두 존재 → 데이터 관리 범위 확대
- **규정 준수**: GDPR, 개인정보보호법 등에서 데이터 위치(data residency) 관리가 두 클라우드에 걸쳐 필요
- **데이터 삭제 정책**: S3와 GCS 양쪽에서의 일관된 retention/deletion 정책 필요
- **감사 추적**: `audit_events`, `duplicate_events` 는 Firestore에만 존재 → AWS 쪽 감사 시스템과 통합 필요

### 3.6 Vendor Lock-in 심화

- **Vertex AI 종속**: Kubeflow Pipeline 정의, Model Registry, Batch Prediction 등이 Vertex AI에 깊이 의존
- **Pub/Sub 종속**: 10+ topics의 이벤트 아키텍처가 Pub/Sub 고유 기능(ordering key, DLQ, Eventarc 통합)에 의존
- **Firestore 종속**: 상태 머신 전체가 Firestore 트랜잭션 시맨틱스에 의존
- **향후 클라우드 전환 비용**: GCP에서 다른 클라우드로 이동하려면 사실상 전체 시스템 재설계 필요

---

## 4. 트레이드오프 상세 분석

### 4.1 ML 서비스 품질 vs 운영 복잡도

| 측면 | GCP 별도 환경 (현재 설계) | AWS 단일 환경 가상 대안 |
|------|-------------------------|----------------------|
| **ML 파이프라인 품질** | Vertex AI의 성숙한 ML 기능 활용 (TPU, Model Registry, Kubeflow 네이티브) | SageMaker Pipelines — 기능적으로 유사하나 Kubeflow 호환성 약함 |
| **운영 복잡도** | 높음 — 듀얼 클라우드 운영, 크로스 클라우드 인증/전송 관리 | 낮음 — 단일 클라우드 내 모든 서비스 통합 |
| **장애 격리** | 강함 — ML 장애가 서빙에 영향 미치지 않음 | 약함 — 동일 클라우드 내 cascading failure 가능성 |
| **네트워크 비용** | 높음 — 매 실행마다 크로스 클라우드 전송 비용 | 낮음 — 리전 내 전송 무료 |
| **보안** | 강함 — WIF 기반 무자격증명, 환경 분리 | 보통 — IAM Role 기반, 동일 계정 내 접근 관리 |

### 4.2 이벤트 기반 설계의 정교함 vs 디버깅 난이도

**설계의 정교함** (장점):
- Pub/Sub ordering key로 run 단위 순서 보장
- Application-level DLQ (`ml.dead-letter`) + Pub/Sub native DLQ 이중 안전망
- Cloud Tasks 기반 exponential backoff — sleep 없는 비동기 재시도
- Idempotency key (`{run_id}_{step}_{attempt}`)로 중복 처리 완전 방지
- 상태 기반 무력화 — CANCELLED 상태면 Cloud Tasks 실행을 자연스럽게 무시

**디버깅 난이도** (단점):
- 메시지 흐름이 10+ topics를 거치며 여러 Cloud Functions를 경유
- 특정 run의 문제 추적 시 Pub/Sub 메시지 로그 + Firestore 상태 + Cloud Functions 로그를 크로스 참조해야 함
- Race Condition 디버깅 (예: CANCELLING 중 ml.step.failed 수신)은 분산 시스템 전문 지식 필요
- 크로스 클라우드 구간(STS, EXP)은 양쪽 로그를 모두 확인해야 근본 원인 파악 가능

### 4.3 비용 구조 비교

| 비용 항목 | GCP 별도 환경 | 예상 영향 |
|----------|-------------|----------|
| **Vertex AI Compute** | GPU/TPU 사용량 기반 | 핵심 비용. Spot/Preemptible 활용 시 절감 가능 |
| **Cross-Cloud Egress** | GCS→AWS + AWS→GCS 양방향 | 데이터 크기에 비례. 월 수백~수천 달러 가능 |
| **서버리스 컴포넌트** | Cloud Functions + Pub/Sub + Firestore | 사용량 비례 과금. 유휴 시 비용 ~0 |
| **STS** | S3→GCS 전송 | 전송량 기반. 대용량 시 유의미 |
| **운영 인력** | 듀얼 클라우드 전문가 | 인건비 프리미엄. 시장에서 희소한 인력 |
| **대비: AWS 단일 환경** | SageMaker + S3 + Step Functions | 리전 내 전송 무료. 단일 스킬셋 운영 |

**핵심 트레이드오프**: Vertex AI의 GPU/TPU 가격 경쟁력으로 컴퓨팅 비용을 절감하더라도, 크로스 클라우드 네트워크 비용과 운영 인력 비용이 이를 상쇄할 수 있음. 순 비용 이점은 **학습 워크로드의 규모와 빈도**에 크게 의존.

### 4.4 보안 경계 분리 vs 공격 표면 확대

**보안 경계 분리** (장점):
- ML 환경이 서비스 도메인과 완전히 분리 → blast radius 최소화
- GCP 환경 침해가 AWS 서빙 환경에 직접 영향을 주지 않음
- WIF 기반 임시 자격증명 → 장기 자격증명 유출 위험 제거

**공격 표면 확대** (단점):
- 크로스 클라우드 인증 엔드포인트가 추가 공격 대상
- EventBridge → RunAPI HTTPS 연결의 OIDC 토큰 관리
- EXP의 `AssumeRoleWithWebIdentity` 호출 → AWS STS 엔드포인트 노출
- 두 클라우드의 IAM 정책을 동시에 정확하게 관리해야 하는 부담

### 4.5 Postprocess Step의 동기 호출 병목

**설계 문서 근거** (`Step-level_State_Machine_(postprocess).md`, 개선 권고 `I1`):
- Postprocess Trigger가 EXP를 **동기 HTTP 호출** → CF timeout(60분) 내에 완료 필요
- 대용량 파일 동기화 시 타임아웃 위험 → 고아 Job 발생 가능
- 이 문제는 GCP↔AWS 크로스 클라우드 구조에서만 발생하는 고유 문제

**만약 AWS 단일 환경이었다면**: S3→S3 복사 또는 동일 리전 내 데이터 이동이므로 이 병목 자체가 존재하지 않음

### 4.6 관심사 분리의 깔끔함 vs 통합 테스트의 어려움

**관심사 분리** (장점):
- 데이터 생산(AWS) / ML 훈련·추론(GCP) / 서빙(AWS)이 명확히 분리
- 각 환경의 독립적 업그레이드/스케일링 가능
- ML 팀과 서비스 팀의 책임 경계가 클라우드 경계와 일치

**통합 테스트** (단점):
- End-to-End 테스트가 두 클라우드를 모두 포함해야 함
- 테스트 환경에서 STS, EXP, WIF 인증 등을 모두 모킹하거나 실제 구성해야 함
- CI/CD 파이프라인이 두 클라우드의 자격증명을 모두 보유해야 함
- 로컬 개발 환경에서 전체 파이프라인 시뮬레이션이 사실상 불가능

---

## 5. 의사결정 프레임워크

### 5.1 GCP 별도 환경이 유리한 경우

1. **TPU가 필수적인 대규모 학습 워크로드가 존재**: LLM Fine-tuning, 대규모 Graph Embedding
2. **ML 팀이 GCP/Vertex AI에 대한 깊은 전문성 보유**: 학습 곡선 부담이 낮음
3. **학습 빈도가 높고 컴퓨팅 비용이 전체 비용의 대부분**: GPU/TPU 가격 차이가 크로스 클라우드 비용을 상쇄
4. **보안 규정이 ML 환경과 서빙 환경의 물리적 분리를 요구**: 금융, 의료 등
5. **기존 AWS 환경의 변경이 어려운 조직적 제약**: 별도 환경이 독립적 의사결정 가능

### 5.2 AWS 단일 환경이 유리한 경우

1. **학습 워크로드 규모가 작고 GPU만으로 충분**: SageMaker로 충분히 커버 가능
2. **데이터 전송량이 크고 빈번함**: 크로스 클라우드 비용이 컴퓨팅 절감분을 초과
3. **소규모 팀으로 운영**: 듀얼 클라우드 전문성 확보가 어려움
4. **빠른 개발 속도가 우선**: 단일 클라우드 내 통합이 개발/테스트 속도에서 유리
5. **E2E latency가 중요**: 크로스 클라우드 데이터 전송 시간이 SLA를 위협

### 5.3 하이브리드 접근 고려

1. **학습은 GCP, 추론은 AWS**: 가장 비용이 큰 학습만 GCP에서 실행하고, 추론은 서빙과 가까운 AWS에서 실행
2. **초기에는 AWS 단일, 규모 성장 시 GCP 분리**: 점진적 마이그레이션으로 리스크 분산
3. **멀티 클라우드 추상화 레이어 도입**: Kubeflow를 EKS에서도 실행 가능하게 하여 이식성 확보

---

## 6. 종합 평가

### 현재 설계의 강점
이 설계는 ML 파이프라인 오케스트레이션의 **정교함과 견고성**에서 높은 수준을 달성합니다. 특히:
- 멱등성 보장 (idempotency_key), 낙관적 잠금, 이중 DLQ, 상태 기반 무력화 등 **분산 시스템 패턴의 모범적 적용**
- Vertex AI의 ML 네이티브 기능 최대 활용
- WIF 기반 제로 트러스트 크로스 클라우드 인증

### 현재 설계의 리스크
- 크로스 클라우드 데이터 전송이 **성능 병목이자 비용 동인**으로 작용
- 운영 복잡도가 높아 **전문 인력 의존도가 높음**
- 디버깅과 통합 테스트의 **난이도가 단일 클라우드 대비 현저히 높음**
- Postprocess의 동기 호출 병목(I1)은 **데이터 규모 증가 시 시스템 안정성을 위협**

### 최종 판단
GCP 별도 환경 구축은 **"ML 워크로드 품질과 보안을 위해 운영 복잡도와 네트워크 비용을 지불하는"** 트레이드오프입니다. 이 결정이 합리적인지는 궁극적으로 **학습 워크로드의 규모, TPU 필요성, 팀의 GCP 역량, 조직의 보안 요구사항**에 의해 결정됩니다. 현재 설계의 아키텍처 품질은 매우 높으므로, GCP를 선택하는 전략적 이유가 명확하다면 구현 리스크는 관리 가능한 수준입니다.
