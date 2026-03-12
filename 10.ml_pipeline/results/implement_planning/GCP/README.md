# ML Platform 실현 계획 (Plans)

[설계 문서](../../03.ml_pipeline/results/orchestration_flow/GCP)에 정의된 GCP ML 파이프라인 아키텍처를 **실제로 구현하기 전에 검증해야 할 항목**들을 다루는 문서입니다. "GCP로 ML 플랫폼을 분리하는 것이 타당한가?"라는 근본 질문부터, "Vertex AI API가 설계에서 기대한 대로 동작하는가?"까지 단계적으로 검증합니다.

---

## 문서 구성

### 1. GCP vs AWS 타당성 분석 (왜 GCP인가?)

설계의 전제 — AWS 데이터/서비스 환경에서 ML 파이프라인만 GCP로 분리하는 구조 — 가 합리적인지 다각도로 분석합니다.

| 문서 | 설명 |
|------|------|
| **compare-claude.md** | Claude의 타당성 분석. GCP 분리가 유리한 조건(배치 중심 학습, TPU, Vertex AI 고유 기능)과 불리한 조건(데이터 이동 비용, 실시간 서빙, 멀티클라우드 운영)을 정리. 결정 체크리스트 포함. |
| **compare-gpt.md** | GPT의 타당성 분석. 크로스 클라우드의 실질적 비용(egress, 네트워크 레이턴시, IAM 이중화, 운영 복잡도)을 중심으로 GCP 분리 vs AWS 통합의 판단 기준 제시. |

### 2. GCP vs AWS 비교 테스트 계획 (실측 검증)

타당성 분석에서 제기된 주장들을 **동일 조건의 GCP/AWS 병렬 환경에서 실측**하는 테스트 계획입니다.

| 문서 | 설명 |
|------|------|
| **compare.md** | 8개 Phase의 비교 테스트 실행 계획. 데이터 전송 → ML 컴퓨팅 → E2E Latency → 비용 → 안정성 → 보안 → 운영성 → 확장성 순으로 GCP와 AWS를 정량 비교. Terraform IaC 기반 환경 구성, 4종 데이터셋 프로파일(1GB~200GB), 의사결정 매트릭스 포함. |

### 3. Vertex AI API 테스트 계획 (GCP 깊이 검증)

GCP 채택을 결정한 후, 설계 문서의 각 컴포넌트가 실제 Vertex AI API에서 기대대로 동작하는지 검증합니다.

| 문서 | 설명 | 비고 |
|------|------|------|
| **api-test.md** | Vertex AI API 테스트 v1. Traditional ML / Deep Learning / LLM 3개 파트로 나누어 Vertex AI의 성능, 비용, 운영성을 실측. | 초기 버전 |
| **api-test2.md** | Vertex AI API 테스트 v4. v1 대비 SDK 일관성, TPU 제약, 한국어 품질 지표, Billing 추적, Gemini 2.0 retire 대응 등 대폭 보강. | **최신 버전** |

---

## 문서 읽는 순서 (권장)

```
1. compare-claude.md / compare-gpt.md
   └─ "GCP ML 분리가 타당한가?" 에 대한 분석 (먼저 읽기)

2. compare.md
   └─ 타당성 분석의 주장들을 실측으로 검증하는 테스트 계획

3. api-test2.md (최신)
   └─ GCP 채택 후 Vertex AI API의 구체적 기능/성능 검증 계획
```

---

## 설계 문서와의 관계

```
designs/                          plans/designs/
(아키텍처 설계)                     (실현 계획)

C4_Container_Layer.md  ─────────→  compare.md
  (전체 구조)                        (GCP vs AWS 비교 테스트)

C4_Component_Layer_VXP.md ──────→  api-test2.md
  (Vertex AI 파이프라인 설계)          (Vertex AI API 실측 검증)

Topic_Specification.md  ─────────→  compare.md Phase 5
  (이벤트/상태 스키마)                  (안정성/장애 처리 비교)
```

---

## 테스트 대상 Vertex AI API 범위 (api-test2.md)

| Part | 영역 | 주요 테스트 항목 |
|------|------|-----------------|
| **A** | Traditional ML | AutoML, Feature Store, Model Registry, Batch/Online Prediction |
| **B** | Deep Learning | Custom Training, Kubeflow Pipelines, HPT(Vizier), GPU/TPU 분산 학습 |
| **C** | LLM / GenAI | Gemini API, Embeddings, Fine-Tuning, RAG Engine, Agent Engine, Prompt Caching |

---

## 비교 테스트 Phase 요약 (compare.md)

| Phase | 영역 | GCP | AWS |
|-------|------|-----|-----|
| 1 | 데이터 전송 | STS (S3→GCS) + EXP (GCS→S3) | 동일 리전 S3 직접 접근 |
| 2 | ML 컴퓨팅 | Vertex AI Training (GPU/TPU) | SageMaker Training (GPU) |
| 3 | E2E Latency | Pub/Sub + Cloud Tasks | SNS + SQS + EventBridge |
| 4 | 비용 | GCP Billing Export | AWS Cost Explorer |
| 5 | 안정성 | Firestore + Cloud Tasks retry | DynamoDB + Step Functions |
| 6 | 보안 | WIF + AssumeRoleWithWebIdentity | IAM Role (Cross-Account) |
| 7 | 운영성 | Cloud Monitoring + Logging | CloudWatch + X-Ray |
| 8 | 확장성 | Vertex AI auto-scaling | SageMaker auto-scaling |
