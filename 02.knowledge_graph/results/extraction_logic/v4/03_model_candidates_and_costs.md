# 모델 후보 및 예상 비용 상세

> 각 파이프라인 단계별 사용 모델 후보, 가격, 장단점을 정리하고
> 시나리오별 총비용을 산출한다.
>
> 작성일: 2026-03-08 (v2 기반)
> 개정일: 2026-03-08 (v4 — 프롬프트 최적화 비용 현실화, embedding 모델 평가 비용 추가)

---

## 1. LLM 모델 후보

### 1.1 Context 추출용 (CompanyContext + CandidateContext)

> **가격 기준일**: 2026-03. LLM 가격은 하락 추세이므로 PoC 시점에 반드시 재확인 필요. 특히 Gemini Flash는 가격 변동이 빈번함.

| 모델 | Input $/1M tok | Output $/1M tok | 한국어 품질 | 추출 정확도 (예상) | 비고 |
|---|---|---|---|---|---|
| **Claude Haiku 4.5** | $0.80 | $4.00 | 우수 | 중상 | **v1 MVP 추천** — 비용 대비 성능 최적 |
| **Gemini 2.0 Flash** | $0.10 | $0.40 | 양호 | 중 | 최저 비용, 품질 검증 필요 |
| Claude Sonnet 4.6 | $3.00 | $15.00 | 최우수 | 상 | 품질 우선 시 / 복잡한 추출 |
| GPT-4o-mini | $0.15 | $0.60 | 양호 | 중 | Gemini Flash와 비슷한 포지션 |
| GPT-4o | $2.50 | $10.00 | 우수 | 상 | 비용 높음 |
| Gemini 2.0 Pro | $1.25 | $10.00 | 우수 | 중상 | Flash 대비 가격 대폭 상승 |

#### 모델 선택 전략

```
v1 MVP (비용 효율):
  Primary: Claude Haiku 4.5 (대부분의 추출)
  Fallback: Claude Sonnet 4.6 (Haiku confidence 낮은 케이스)

대안 A (최저 비용):
  Primary: Gemini 2.0 Flash
  Fallback: Claude Haiku 4.5

대안 B (품질 우선):
  Primary: Claude Sonnet 4.6
  Batch API 활용 시 50% 할인
```

### 1.2 Batch API 활용

| 제공사 | Batch API | 할인율 | 처리 시간 | 비고 |
|---|---|---|---|---|
| Anthropic | Message Batches API | 50% | 24시간 이내 | Claude 모델 전체 지원 |
| OpenAI | Batch API | 50% | 24시간 이내 | GPT-4o, 4o-mini 지원 |
| Google | 없음 (Vertex Batch 별도) | — | — | Vertex AI 파이프라인 필요 |

**권장**: Context 생성은 실시간이 아닌 **배치 처리**이므로 Batch API 적극 활용.
Haiku Batch 시 Input $0.40/1M, Output $2.00/1M.

---

## 2. Embedding 모델 후보

### 2.1 Vector Index용 (Chapter/Vacancy 임베딩)

| 모델 | 가격 ($/1M tok) | 차원 | 한국어 성능 | 비고 |
|---|---|---|---|---|
| **OpenAI text-embedding-3-small** | $0.02 | 1536 | 양호 | **v1 MVP 추천** — 가격/성능 균형 |
| OpenAI text-embedding-3-large | $0.13 | 3072 | 우수 | 더 높은 품질, 6.5배 비용 |
| Cohere embed-multilingual-v3.0 | $0.10 | 1024 | 우수 (한국어 특화) | 한국어 최적화, 비용 높음 |
| Gemini text-embedding-004 | $0.006 | 768 | 양호 | 최저가, 차원 낮음 |
| BGE-M3 (자체 호스팅) | GPU 비용만 | 1024 | 우수 | 인프라 관리 필요 |

#### 비용 비교 (150만 Chapter + 1만 Vacancy, 평균 200 토큰)

| 모델 | 총 토큰 | 비용 |
|---|---|---|
| text-embedding-3-small | ~302M | **$6** |
| text-embedding-3-large | ~302M | $39 |
| Cohere multilingual v3 | ~302M | $30 |
| Gemini embedding-004 | ~302M | **$2** |
| BGE-M3 (자체 호스팅) | — | GPU $10~30/월 |

### 2.2 domain_fit 계산용

domain_fit은 company domain text와 candidate domain text의 cosine similarity로 계산.
짧은 텍스트이므로 **어떤 모델이든 비용 무시할 수준**.

---

## 3. Graph DB 후보

### 3.1 선택지 비교

| DB | 가격 | Vector Index | 한국어 | 장점 | 단점 |
|---|---|---|---|---|---|
| **Neo4j AuraDB** | Free tier: 200K 노드 / Professional: $65/월~ | 5.11+ 내장 | 무관 | **v1 MVP 추천** — Cypher 생태계, Vector 내장 | 대규모 시 비용 증가 |
| Neo4j AuraDB Free | $0 | O | 무관 | 무료, PoC에 최적 | 200K 노드 제한 |
| Amazon Neptune | $0.348/시간~ | Neptune Analytics | 무관 | AWS 생태계 통합 | Gremlin/SPARQL, Cypher 미지원 |
| NebulaGraph Cloud | $0.15/시간~ | 미지원 | 무관 | 오픈소스, 대규모 | Vector 별도 필요 |
| Memgraph Cloud | $150/월~ | 없음 | 무관 | in-memory 빠름 | Vector 별도, 비용 높음 |

#### v1 MVP 권장: Neo4j AuraDB

- **Free tier** (200K 노드): PoC + 품질 검증에 충분
  - 200K 노드 ≈ 이력서 ~10,000건 + JD ~2,000건 분량
- **Professional** ($65/월): 풀 스케일 시 전환
- Vector Index 내장: 별도 Pinecone/Weaviate 불필요
- Cypher: v4 graph_schema.md의 예시 쿼리 직접 사용 가능

### 3.2 Graph DB 비용 시나리오

| 시나리오 | 노드 수 (예상) | 엣지 수 (예상) | 권장 플랜 | 월 비용 |
|---|---|---|---|---|
| PoC (이력서 5K + JD 1K) | ~80K | ~250K | AuraDB Free | **$0** |
| MVP (이력서 50K + JD 5K) | ~800K | ~2.5M | AuraDB Professional | **$65~130/월** |
| Full (이력서 500K + JD 10K) | ~8M | ~25M | AuraDB Professional+ | **$200~500/월** |

---

## 4. ML 모델 후보 (Phase 2 Knowledge Distillation용)

### 4.1 NER / 분류기 베이스 모델 — Phase 2 선택적

> Phase 2 ML Knowledge Distillation에서 scope_type/seniority 분류 시 사용. Phase 2 품질 평가 결과에 따라 투자 여부 결정.

| 모델 | 파라미터 | 한국어 | 추론 속도 (T4) | 학습 비용 | 비고 |
|---|---|---|---|---|---|
| **KLUE-BERT-base** (권장) | 110M | 우수 | ~200 문서/초 | ~$10 (1 epoch) | 검증된 한국어 사전학습, 비용/성능 균형 |
| DeBERTa-v3-base-kor (대안) | 184M | 우수 | ~120 문서/초 | ~$15 | KLUE-BERT보다 높은 성능, 추론 느림 |

### 4.2 SLM (On-premise LLM) 후보 — PII 불가 시만 해당

> PII 이슈로 외부 API 사용이 불가한 경우에만 검토. 시나리오 C 참조.

| 모델 | 파라미터 | 한국어 | VRAM | 추론 비용 (A100) | 비고 |
|---|---|---|---|---|---|
| **EXAONE-3.5-7.8B** (권장) | 7.8B | 최우수 | 16GB (Q4) | ~$1.50/시간 | 한국어 최강, LG AI Research |
| Qwen2.5-7B-Instruct (대안) | 7B | 우수 | 14GB (Q4) | ~$1.50/시간 | 다국어 우수, EXAONE 대비 한국어 약간 열세 |

> **On-premise vs API 비용**: API(Haiku Batch) ~$619 vs On-premise(EXAONE, A100×4) ~$8,700 → **API가 14배 저렴**.
> PII 불가 판정 시에만 On-premise를 검토하며, Azure/AWS Private Endpoint도 대안으로 고려(§5 참조).

---

## 5. 시나리오별 총비용 산출

### 5.1 시나리오 A: API 기반 (PII 해결 전제) — 권장

| 비용 항목 | 모델/서비스 | 수량 | 단가 | 비용 |
|---|---|---|---|---|
| **CompanyContext LLM** | Haiku Batch | 10K JD | $0.0004/건 | **$4** |
| **CandidateContext LLM** | Haiku Batch | 500K 이력서 | $0.00115/건 | **$575** |
| **Embedding** | text-embedding-3-small | 302M 토큰 | $0.02/1M | **$6** |
| **Embedding 모델 평가 (PoC)** | 3개 모델 비교 | 20쌍 × 3모델 | — | **$50** |
| **Graph DB** | Neo4j AuraDB Professional | 12개월 | $100/월 | **$1,200** |
| **BigQuery** | 서빙 테이블 | 12개월 | $30/월 (추정) | **$360** |
| **Silver Label (PoC)** | Sonnet | 2,000건 | $0.01/건 | **$20** |
| **Gold Label 인건비** | 전문가 검수 | 400건 | 건당 20,000원 | **~$5,840** |
| **오케스트레이션 인프라** | Cloud Workflows / Prefect | 12개월 | ~$50/월 | **$600** |
| **프롬프트 최적화 LLM** | Sonnet (테스트용) | 3개 프롬프트 × 10~15회 반복 ≈ 500건 | — | **~$600** |
| | | | | |
| **LLM 소계** | | | | **~$1,255** |
| **인프라 소계** | | | | **$2,160/년** |
| **인건비 소계** | | | | **$5,840** |
| **총비용** | | | | **~$9,255 (~1,268만 원)** |

> **Gold Label 인건비 산정 근거**: v4 스키마 기준으로 이력서 1건 전체를 검수하면 scope_type, outcomes, situational_signals 등 다수 필드를 판정해야 하므로 건당 30~40분 소요. 건당 20,000원(시급 40,000원 기준)으로 산정.
>
> **프롬프트 최적화 비용 근거**: Phase 0~1에서 프롬프트 반복 테스트 시 Sonnet급 모델 사용 불가피. 3개 프롬프트 × 10~15회 반복 ≈ 500건.
>
> **엔지니어 인건비 미포함**: 위 비용은 직접 비용(API, 인프라, 데이터 레이블링)만 포함. 개발 인력(DE 1명 + MLE 1명, 16~19주) 인건비는 조직에 따라 다르므로 별도 산정 필요. 참고: 시니어 엔지니어 2명 × 16~19주 ≈ $40,000~$75,000.

### 5.2 시나리오 B: 품질 우선 (Sonnet 사용)

| 비용 항목 | 모델/서비스 | 비용 |
|---|---|---|
| CompanyContext LLM | Sonnet Batch | **$15** |
| CandidateContext LLM | Sonnet Batch | **$2,875** |
| 나머지 | 시나리오 A 동일 | **$8,676** |
| **총비용** | | **$11,566 (~1,585만 원)** |

### 5.3 시나리오 C: On-premise (PII 제약)

| 비용 항목 | 모델/서비스 | 비용 |
|---|---|---|
| CandidateContext LLM | EXAONE-3.5-7.8B × A100 | **$8,700** |
| CompanyContext LLM | Haiku API (JD는 PII 아님) | **$4** |
| GPU 인프라 (학습용) | A100 × 24시간 | **$100** |
| 나머지 | 시나리오 A 동일 | **$8,676** |
| **총비용** | | **$17,480 (~2,395만 원)** |

### 5.4 시나리오 D: 최저 비용 (Gemini Flash)

| 비용 항목 | 모델/서비스 | 비용 |
|---|---|---|
| CompanyContext LLM | Gemini Flash | **$1.5** |
| CandidateContext LLM | Gemini Flash | **$290** |
| 나머지 | 시나리오 A 동일 | **$8,676** |
| **총비용** | | **$8,968 (~1,229만 원)** |

---

## 6. 비용 비교 요약

| 시나리오 | LLM 비용 | 인프라/년 | 인건비 | 총비용 | 원화 |
|---|---|---|---|---|---|
| **A: Haiku API (권장)** | $1,255 | $2,160 | $5,840 | **~$9,255** | **~1,268만** |
| B: Sonnet API | $3,340 | $2,160 | $5,840 | $11,566 | ~1,585만 |
| C: On-premise | $9,254 | $2,160 | $5,840 | $17,480 | ~2,395만 |
| D: Gemini Flash | $942 | $2,160 | $5,840 | $8,968 | ~1,229만 |

### v1 대비 비용 변화

| 항목 | v1 계획 추정 | v4 계획 추정 | 차이 원인 |
|---|---|---|---|
| LLM 비용 | 500만~3,000만 원 | 67만~396만 원 (API) | v4는 이력서+JD 단위 처리, v1은 150GB 전체 NER/RE |
| ML 학습 비용 | 100만~300만 원 | 14만 원 (Phase 2) | v4에서 ML Distillation 범위 축소 |
| 인건비 (레이블링) | 500만~1,000만 원 | ~800만 원 | Gold set 검수 난이도 증가 (v4 스키마 복잡도) |
| 인프라 | 별도 추정 없음 | ~296만 원/년 | Neo4j + BigQuery + 오케스트레이션 |
| **총비용** | **1,250만~4,800만 원** | **1,229만~2,395만 원** | 처리 단위/방법의 근본적 차이 |

> **주의**: v1과 v4의 비용 차이는 "v4가 더 효율적"이라는 의미가 아니라,
> **추출 대상과 방법이 근본적으로 다르기 때문**이다.
> v1은 범용 NER/RE로 150GB 전체를 처리하는 비용이고,
> v4는 v4 온톨로지에 맞춘 Context 생성 비용이다.

---

## 7. 가상 정보(Assumptions) 목록

아래는 비용 산출에 사용된 가정으로, **실제 데이터로 검증이 필요하다**.

| # | 가정 항목 | 가정값 | 실측 방법 | 영향도 |
|---|---|---|---|---|
| A1 | JD 보유량 | 10,000건 | 자사 DB 확인 | 중 (CompanyContext 비용에 비례) |
| A2 | 이력서 보유량 | 500,000건 | 150GB ÷ 평균 크기 측정 | **높음** (CandidateContext 비용에 직접 비례) |
| A3 | 이력서 평균 크기 | 300KB | 무작위 500건 샘플링 | 높음 |
| A4 | 이력서당 평균 경력 수 | 3건 | 샘플 분석 | 중 (LLM 호출 횟수) |
| A5 | NICE 데이터에 있는 회사 비율 | 60% | NICE DB 매칭 테스트 | 중 (PastCompanyContext 커버리지) |
| A6 | LLM 추출 1회당 평균 토큰 | Experience: 3,000, Career: 2,500 | 파일럿 10건 측정 | 높음 (비용 직결) |
| A7 | Rule 기반 날짜/회사명 추출 성공률 | 70% | 파일럿 500건 실측 | 중 |
| A8 | Haiku의 한국어 추출 품질 | Sonnet의 85% 수준 | 50건 비교 평가 | **높음** (모델 선택 결정) |
| A9 | 매핑 대상 쌍 수 | 500만 (JD × 상위 500) | 비즈니스 요구사항 확인 | 낮음 (MappingFeatures 비용 미미) |
| A10 | PII 외부 전송 가능 여부 | 가능 (마스킹 전제) | 법무 확인 필수 | **Critical** (시나리오 A↔C 결정) |
| A11 | PDF 비율 / HWP 비율 | PDF 70%, DOCX 20%, HWP 10% | 파일 형식 분포 조사 | 높음 (파싱 난이도) |
| A12 | OCR 필요 비율 | 5% 미만 | 파일 분석 | 중 (5% 이상이면 파싱 비용 증가) |
| A13 | 기술 사전 초기 크기 | 2,000개 기술명 | 기존 사전 확인 + 추가 | 낮음 |
| A14 | Neo4j AuraDB Professional 용량 | 800K 노드 시 $100/월 | 실제 적재 후 확인 | 중 |
| A15 | Haiku Batch API 응답 시간 | 24시간 이내 | 소규모 테스트 | 낮음 |
| A16 | Embedding 모델 한국어 분별력 | 양호 (text-embedding-3-small) | 20쌍 cosine similarity 테스트 | 높음 (domain_fit 피처 직결) |
