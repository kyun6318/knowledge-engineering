# GraphRAG standard.2 — 모델 및 방법론 정리

> standard.2 계획 전체에서 사용하는 LLM, ML 모델, Embedding, 청킹/파싱 방법론을 한 곳에 정리.
>
> **standard.2 변경**:
> - [standard.1.1-5] Cohen's d / Power analysis를 Phase 3으로 이동
> - [standard.1.1-16] Phase별 비용 수치를 04_cost와 통일

---

## 1. Phase 0 — PoC · 검증 · 의사결정

> standard.1과 동일. 상세 내용은 `standard.1/05_models_and_methods.md` 1절 참조.

### 1.6 Phase 0 비용

| 모델/서비스 | 비용 |
|---|---|
| Anthropic 일반 (Sonnet) | $20 |
| Gemini API (검증) | $55 |
| Vertex AI Embedding | $10 |
| Cloud Run + GCS 등 | $10 |
| **Phase 0 합계** | **$95** |

> [standard.1.1-16] standard.1의 05_models에서 $85, 04_cost에서 $95 → $10 차이 해소.
> Embedding $10은 LLM 비용이 아닌 Phase 0 전체 비용에 포함. Cloud Run/GCS $10도 포함.

---

## 2. Phase 1 — MVP 파이프라인 (1,000건)

> standard.1과 동일. 상세 내용은 `standard.1/05_models_and_methods.md` 2절 참조.

### 2.6 Phase 1 비용

| 모델/서비스 | 비용 |
|---|---|
| Anthropic Batch (Haiku) | ~$50 |
| Vertex AI Embedding | $1 |
| Cloud Run + 인프라 | ~$35 |
| **Phase 1 합계** | **$86** |

> [standard.1.1-16] 04_cost의 $86과 통일. 인프라 비용 $35 포함.

---

## 3. Phase 2 — 전체 확장 (450K건)

> standard.1과 동일한 모델/방법론. 알고리즘 변경 사항만 기술.

### 3.3 알고리즘 — [standard.1.1-5] 변경

| 알고리즘 | 용도 | 세부 Phase |
|----------|------|-----------|
| SimHash | 이력서 중복 제거 (500K → ~450K) | Phase 2-1-1 |
| Cohen's κ | Inter-annotator agreement (품질 평가) | Phase 2-2 |
| ~~Cohen's d~~ | ~~효과 크기 측정~~ | ~~Phase 2-2~~ → **Phase 3-5로 이동** [standard.1.1-5] |

### 3.4 Phase 2 비용

| 모델/서비스 | 비용 |
|---|---|
| Anthropic Batch (Haiku) CandidateContext | $1,500 |
| Anthropic Batch (Haiku) CompanyContext | $4 |
| Anthropic 일반 (Sonnet) Silver Label + 프롬프트 | $620 |
| Gemini API (크롤링) | $5 |
| Vertex AI Embedding | $30 |
| Embedding Egress | $3.6 |
| **Phase 2 LLM 합계** | **$2,163** |

> [standard.1.1-16] standard.1의 04_cost에서 $2,131, 05_models에서 $2,159 → **$2,163**으로 통일.
> 차이 원인: Cloud Run 비용이 LLM에 혼입되어 있었음 → 인프라로 분리.

---

## 4. Phase 3 — 운영 최적화

> standard.1과 동일 + Phase 2에서 이동된 항목.

### 4.1 ML 모델: Knowledge Distillation

> standard.1과 동일. KLUE-BERT scope_type/seniority 분류기.

### 4.5 Phase 2에서 이동된 항목 [standard.1.1-5]

| 항목 | 원래 위치 | 용도 |
|------|-----------|------|
| Cohen's d (효과 크기) | Phase 2-2 | ML Distillation 모델 vs LLM 비교 |
| Power analysis | Phase 2-2 | A/B 테스트 표본 크기 결정 |
| Looker Studio 대시보드 | Phase 2 산출물 | 운영 인력 5명+ 시 도입 |

---

## 5. 공통 — LLM 응답 파싱 전략

> standard.1과 동일. 3-Tier 파싱 실패 처리 (json-repair → 재시도 → 부분 추출/skip).

---

## 6. 비용 총괄 요약 — [standard.1.1-16] 통일

### Phase별 비용

| 모델/서비스 | Phase 0 | Phase 1 | Phase 2 | 합계 |
|---|---|---|---|---|
| Anthropic Batch (Haiku) | — | ~$50 | $1,504 | **$1,554** |
| Anthropic 일반 (Sonnet) | $20 | — | $620 | **$640** |
| Gemini API (검증 + 크롤링) | $55 | — | $5 | **$60** |
| Vertex AI Embedding | $10 | $1 | $34 | **$45** |
| **LLM/Embedding 합계** | **$85** | **$51** | **$2,163** | **$2,299** |

### 총비용 요약

| 항목 | 비용 |
|---|---|
| LLM/Embedding (전 Phase) | $2,299 |
| 인프라 (Phase 2 4개월) | $641~1,041 |
| Phase 0 인프라 | $10 |
| Phase 1 인프라 | $35 |
| Gold Label 인건비 | $5,840 |
| **총비용 (시나리오 A)** | **$8,825~9,225** |
