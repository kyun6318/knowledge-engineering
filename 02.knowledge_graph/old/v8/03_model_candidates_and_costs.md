# 모델 후보 및 예상 비용 상세

> 각 파이프라인 단계별 사용 모델 후보, 가격, 장단점을 정리하고
> 시나리오별 총비용을 산출한다.
>
> 작성일: 2026-03-08 (v2 기반)
> 개정일: 2026-03-08 (v6 — Embedding 모델 v10 확정 반영, 비용 재산정)
> 개정일: 2026-03-08 (v7 — 시나리오 A' Sonnet Batch fallback 추가)
> 개정일: 2026-03-09 (v8 — DB 기반 파이프라인 전환에 따른 토큰 절감 반영, 비용 재산정)

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

## 2. Embedding 모델 — v10 확정 반영

> **v6 변경 (H-2)**: v5에서 3개 후보를 비교하는 방식에서, v10에서 확정된 `text-multilingual-embedding-002` (Vertex AI)를 기본 모델로 채택하는 방식으로 변경.

### 2.1 Vector Index용 (Chapter/Vacancy 임베딩) — 확정

| 모델 | 가격 ($/1M tok) | 차원 | 한국어 성능 | 비고 |
|---|---|---|---|---|
| **text-multilingual-embedding-002** (Vertex AI) | $0.0065 | 768 | 우수 (다국어 특화) | **v10 확정 모델** — GCP 네이티브, 05_evaluation_strategy와 동일 |
| Cohere embed-multilingual-v3.0 | $0.10 | 1024 | 우수 (한국어 특화) | 대안 1 — 한국어 최적화, 비용 높음 |
| BGE-M3 (자체 호스팅) | GPU 비용만 | 1024 | 우수 | 대안 2 — 인프라 관리 필요 |

**v5 대비 변경 사항**:
- `text-embedding-3-small` (OpenAI)과 `Gemini text-embedding-004`를 후보에서 제외
- Phase 0 PoC의 "Embedding 모델 비교"를 "Embedding 모델 확정 검증"으로 변경 — `text-multilingual-embedding-002`의 한국어 분별력이 v10 기준을 충족하는지 검증
- 검증 실패 시에만 대안(Cohere/BGE-M3)으로 전환

#### 비용 비교 (150만 Chapter + 1만 Vacancy, 평균 200 토큰)

| 모델 | 총 토큰 | 비용 |
|---|---|---|
| **text-multilingual-embedding-002** | ~302M | **$2** |
| Cohere multilingual v3 | ~302M | $30 |
| BGE-M3 (자체 호스팅) | — | GPU $10~30/월 |

### 2.2 Tier 2 Entity Normalization용 **(v8.1 신설)**

> 스킬, 전공, 직무의 비표준 값을 canonical 엔티티에 매핑하기 위한 embedding 유사도 계산.
> Chapter/Vacancy embedding과 **동일 모델** (`text-multilingual-embedding-002`)을 사용한다.

| 용도 | 대상 건수 | 1회성/런타임 | 토큰 | 비용 |
|---|---|---|---|---|
| **Canonical embedding 사전 구축** | ~2,800개 (스킬 2,000 + 전공 500 + 직무 300) | 1회성 | ~28K | **~$0.0002** |
| **런타임 정규화 (이력서)** | ~958K 유니크 (캐시 적용) | 런타임 | ~9.6M | **~$0.06** |
| **런타임 정규화 (JD)** | ~8K 유니크 (캐시 적용) | 런타임 | ~0.08M | **~$0.001** |
| **합계** | | | ~9.7M | **~$0.06** |

> **비용 영향**: Tier 2 embedding 정규화 비용은 전체 Embedding 비용($2)의 3%에 불과. 전체 비용에 미치는 영향 무시할 수준.
> **캐시 전략**: 동일 텍스트의 embedding 결과를 메모리/디스크 캐시. "자바"가 100K번 등장해도 embedding은 1번만 계산.

### 2.3 domain_fit 계산용

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
- Cypher: v10 graph_schema.md의 예시 쿼리(Q1~Q5) 직접 사용 가능

### 3.2 Graph DB 비용 시나리오

| 시나리오 | 노드 수 (예상) | 엣지 수 (예상) | 권장 플랜 | 월 비용 |
|---|---|---|---|---|
| PoC (이력서 5K + JD 1K) | ~80K | ~250K | AuraDB Free | **$0** |
| MVP (이력서 50K + JD 5K) | ~800K | ~2.5M | AuraDB Professional | **$65~130/월** |
| Full (이력서 500K + JD 10K) | ~8M | ~25M | AuraDB Professional+ | **$200~500/월** |

> **v6 참고**: v10에서 추가된 Industry 노드(~100개), IN_INDUSTRY/REQUIRES_ROLE/MAPPED_TO 엣지는 전체 노드/엣지 수에 미미한 영향 (1% 미만 증가)

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

### v8 토큰 절감 반영 **(v8 신설)**

> DB 기반 파이프라인 전환으로 LLM 호출 건수와 건당 토큰 수가 감소한다.

| 파이프라인 | v7 건당 토큰 | v8 건당 토큰 | 절감률 | 절감 근거 |
|---|---|---|---|---|
| CompanyContext LLM | ~3,900 tok | **~2,200 tok** | **44%** | tech_stack, industry, career_types 등 DB 직접 조회, LLM 입력에 정형 필드 사전 제공 |
| CandidateContext LLM (경력당) | ~3,000 tok | **~1,800 tok** | **40%** | 회사명/기간/직급/기술 DB 직접 조회, workDetails+CareerDescription만 LLM 입력 |

### 5.1 시나리오 A: API 기반 (PII 해결 전제) — 권장

| 비용 항목 | 모델/서비스 | 수량 | 단가 | 비용 |
|---|---|---|---|---|
| **CompanyContext LLM** | Haiku Batch | 10K JD | $0.00022/건 **(v8 변경)** | **$2.2** |
| **CandidateContext LLM** | Haiku Batch | 500K 이력서 | $0.00069/건 **(v8 변경)** | **$345** |
| **Embedding** | text-multilingual-embedding-002 | 302M 토큰 | $0.0065/1M | **$2** |
| **Embedding 모델 검증 (PoC)** | 확정 모델 검증 | 20쌍 | — | **$10** |
| **Graph DB** | Neo4j AuraDB Professional | 12개월 | $100/월 | **$1,200** |
| **BigQuery** | 서빙 테이블 | 12개월 | $30/월 (추정) | **$360** |
| **Silver Label (PoC)** | Sonnet | 2,000건 | $0.01/건 | **$20** |
| **Gold Label 인건비** | 전문가 검수 | 400건 | 건당 20,000원 | **~$5,840** |
| **오케스트레이션 인프라** | Cloud Workflows / Prefect | 12개월 | ~$50/월 | **$600** |
| **프롬프트 최적화 LLM** | Sonnet (테스트용) | 3개 프롬프트 × 10~15회 반복 ≈ 500건 | — | **~$520** |
| | | | | |
| **LLM 소계** | | | | **~$899** |
| **인프라 소계** | | | | **$2,160/년** |
| **인건비 소계** | | | | **$5,840** |
| **총비용** | | | | **~$8,899 (~1,219만 원)** |

> **v8 비용 변경**: LLM 소계 $1,211 → $899 ($312 절감, 25.8% 절감). CompanyContext 토큰 44% 절감, CandidateContext 토큰 40% 절감 반영.

### 5.1.1 시나리오 A': Haiku 품질 미달 시 Sonnet Batch Fallback

> **v7 신설**: Phase 0 PoC에서 Haiku 추출 품질이 기준 미달일 경우, CompanyContext와 CandidateContext만 Sonnet Batch로 전환.

| 비용 항목 | 모델/서비스 | 수량 | 단가 | 비용 |
|---|---|---|---|---|
| **CompanyContext LLM** | Sonnet Batch | 10K JD | $0.00083/건 **(v8 변경)** | **$8.3** |
| **CandidateContext LLM** | Sonnet Batch | 500K 이력서 | $0.00345/건 **(v8 변경)** | **$1,725** |
| **Embedding** | text-multilingual-embedding-002 | 302M 토큰 | $0.0065/1M | **$2** |
| **Embedding 모델 검증 (PoC)** | 확정 모델 검증 | 20쌍 | — | **$10** |
| **Graph DB** | Neo4j AuraDB Professional | 12개월 | $100/월 | **$1,200** |
| **BigQuery** | 서빙 테이블 | 12개월 | $30/월 (추정) | **$360** |
| **Silver Label (PoC)** | Sonnet | 2,000건 | $0.01/건 | **$20** |
| **Gold Label 인건비** | 전문가 검수 | 400건 | 건당 20,000원 | **~$5,840** |
| **오케스트레이션 인프라** | Cloud Workflows / Prefect | 12개월 | ~$50/월 | **$600** |
| **프롬프트 최적화 LLM** | Sonnet (테스트용) | 500건 | — | **~$520** |
| | | | | |
| **LLM 소계** | | | | **~$2,285** |
| **인프라 소계** | | | | **$2,160/년** |
| **인건비 소계** | | | | **$5,840** |
| **총비용** | | | | **~$10,244 (~1,403만 원)** |

> **전환 기준**: Phase 0 PoC에서 Haiku 추출 품질이 아래 기준 미달이면 시나리오 A'를 기본 시나리오로 전환한다.
> - scope_type 분류 정확도 < 60%
> - outcomes 추출 F1 < 50%

### 5.2 시나리오 B: 품질 우선 (Sonnet 사용)

| 비용 항목 | 모델/서비스 | 비용 |
|---|---|---|
| CompanyContext LLM | Sonnet Batch | **$8.3** |
| CandidateContext LLM | Sonnet Batch | **$1,725** |
| 나머지 | 시나리오 A 동일 | **$8,552** |
| **총비용** | | **$10,244 (~1,403만 원)** |

### 5.3 시나리오 C: On-premise (PII 제약)

| 비용 항목 | 모델/서비스 | 비용 |
|---|---|---|
| CandidateContext LLM | EXAONE-3.5-7.8B × A100 | **$5,220** **(v8 변경: 토큰 절감 반영)** |
| CompanyContext LLM | Haiku API (JD는 PII 아님) | **$2.2** |
| GPU 인프라 (학습용) | A100 × 24시간 | **$100** |
| 나머지 | 시나리오 A 동일 | **$8,552** |
| **총비용** | | **$13,874 (~1,901만 원)** |

### 5.4 시나리오 D: 최저 비용 (Gemini Flash)

| 비용 항목 | 모델/서비스 | 비용 |
|---|---|---|
| CompanyContext LLM | Gemini Flash | **$0.8** |
| CandidateContext LLM | Gemini Flash | **$174** |
| 나머지 | 시나리오 A 동일 | **$8,552** |
| **총비용** | | **$8,727 (~1,196만 원)** |

---

## 6. 비용 비교 요약

| 시나리오 | LLM 비용 | 인프라/년 | 인건비 | 총비용 | 원화 |
|---|---|---|---|---|---|
| **A: Haiku API (권장)** | $899 | $2,160 | $5,840 | **~$8,899** | **~1,219만** |
| **A': Haiku→Sonnet Fallback** | $2,285 | $2,160 | $5,840 | **~$10,244** | **~1,403만** |
| B: Sonnet API | $2,285 | $2,160 | $5,840 | $10,244 | ~1,403만 |
| C: On-premise | $5,773 | $2,160 | $5,840 | $13,874 | ~1,901만 |
| D: Gemini Flash | $725 | $2,160 | $5,840 | $8,727 | ~1,196만 |

### v7→v8 비용 변경 요약 **(v8 신설)**

| 시나리오 | v7 | v8 | 절감 | 절감률 |
|---|---|---|---|---|
| A: Haiku API | ~$9,211 | **~$8,899** | $312 | 3.4% |
| A': Sonnet Fallback | ~$11,522 | **~$10,244** | $1,278 | 11.1% |

> **비용 절감이 상대적으로 작은 이유**: LLM 비용은 전체의 10~13%에 불과하고 인건비($5,840)와 인프라($2,160)가 대부분을 차지. **v8의 실질적 이점은 비용 절감보다 일정 단축(5~6주)과 리스크 제거(파싱 품질 Critical 리스크 제거)에 있다.**

### v1 대비 비용 변화

| 항목 | v1 계획 추정 | v8 계획 추정 | 차이 원인 |
|---|---|---|---|
| LLM 비용 | 500만~3,000만 원 | 49만~314만 원 (API) | v8은 DB 정형 데이터 활용, 토큰 대폭 절감 |
| ML 학습 비용 | 100만~300만 원 | 14만 원 (Phase 2) | v10에서 ML Distillation 범위 축소 |
| 인건비 (레이블링) | 500만~1,000만 원 | ~800만 원 | Gold set 검수 난이도 증가 (v10 스키마 복잡도) |
| 인프라 | 별도 추정 없음 | ~296만 원/년 | Neo4j + BigQuery + 오케스트레이션 |
| **총비용** | **1,250만~4,800만 원** | **1,196만~1,901만 원** | DB 기반 전처리 제거 + 토큰 절감 |

---

## 7. 가상 정보(Assumptions) 목록

아래는 비용 산출에 사용된 가정으로, **실제 데이터로 검증이 필요하다**.

| # | 가정 항목 | 가정값 | 실측 방법 | 영향도 |
|---|---|---|---|---|
| A1 | JD 보유량 | 10,000건 | job-hub DB 카운트 쿼리 **(v8 변경)** | 중 (CompanyContext 비용에 비례) |
| A2 | 이력서 보유량 | 500,000건 | resume-hub DB 카운트 쿼리 **(v8 변경)** | **높음** (CandidateContext 비용에 직접 비례) |
| ~~A3~~ | ~~이력서 평균 크기~~ | ~~300KB~~ | — | **제거** (v8: 파일 크기 무관) |
| A4 | 이력서당 평균 경력 수 | 3건 | resume-hub Career 엔티티 평균 카운트 **(v8 변경)** | 중 (LLM 호출 횟수) |
| A5 | NICE 매칭률 | **80-90%** **(v8 변경)** | BRN 기반 매칭 테스트 | 중 (PastCompanyContext 커버리지) |
| A6 | LLM 추출 1회당 평균 토큰 | **CompanyContext: 2,200, CandidateContext: 1,800** **(v8 변경)** | 파일럿 10건 측정 | 높음 (비용 직결) |
| ~~A7~~ | ~~Rule 추출 성공률~~ | ~~70%~~ | — | **제거** (v8: DB 직접 조회) |
| A8 | Haiku의 한국어 추출 품질 | Sonnet의 85% 수준 | 50건 비교 평가 | **높음** (모델 선택 결정) |
| A9 | 매핑 대상 쌍 수 | 500만 (JD × 상위 500) | 비즈니스 요구사항 확인 | 낮음 (MappingFeatures 비용 미미) |
| A10 | PII 외부 전송 가능 여부 | 가능 (마스킹 전제) | 법무 확인 필수 | **Critical** (시나리오 A↔C 결정) |
| ~~A11~~ | ~~PDF/HWP 비율~~ | ~~PDF 70%, DOCX 20%, HWP 10%~~ | — | **제거** (v8: 파일 형식 무관) |
| ~~A12~~ | ~~OCR 필요 비율~~ | ~~5% 미만~~ | — | **제거** (v8: OCR 불필요) |
| ~~A13~~ | ~~기술 사전 초기 크기~~ | ~~2,000개 기술명~~ | — | **변경** → Tier 2 canonical embedding 사전 ~2,800개 (code-hub 기반) **(v8.1 변경)** |
| A14 | Neo4j AuraDB Professional 용량 | 800K 노드 시 $100/월 | 실제 적재 후 확인 | 중 |
| A15 | Haiku Batch API 응답 시간 | 24시간 이내 | 소규모 테스트 | 낮음 |
| A16 | text-multilingual-embedding-002 한국어 분별력 | v10 확정 모델, "우수" 예상 | 20쌍 cosine similarity 테스트 | 높음 (domain_fit 피처 직결) |
| **A19** | Career.businessRegistrationNumber null 비율 | **40%** **(v8 신규)** | resume-hub 쿼리 | 높음 (NICE 매칭률 핵심 드라이버) |
| **A20** | Career.workDetails null 비율 | **20%** **(v8 신규)** | resume-hub 쿼리 | 높음 (LLM 입력 품질) |
| **A21** | overview.descriptions 평균 길이 | **1,000자** **(v8 신규)** | job-hub 쿼리 | 중 (CompanyContext 토큰) |
| **A22** | Skill.code null 비율 + 비표준 값 비율 | **code null 10%, 비표준 값 30-50%** **(v8.1 변경)** | resume-hub 쿼리 + 샘플 수동 확인 | 높음 (Tier 2 embedding 정규화 부하에 영향) |
| **A25** | Tier 2 embedding similarity threshold | **스킬 0.85, 전공 0.80, 직무 0.80** **(v8.1 신규)** | Phase 0 PoC 50건 검증 | 높음 (정규화 정확도 직결) |
| **A26** | Tier 2 canonical embedding 사전 커버리지 | **스킬 ~2,000, 전공 ~500, 직무 ~300** **(v8.1 신규)** | code-hub + 도메인 전문가 검토 | 중 (커버리지 부족 시 정규화 실패율 증가) |
| **A23** | resume-hub 전체 이력서 적재 완료 | **완료** **(v8 신규)** | DB 레코드 수 확인 | **Critical** (전제 조건) |
| **A24** | DB 접근 방식 | **리드 레플리카 직접** **(v8 신규)** | 인프라팀 확인 | 높음 (대량 조회 성능) |
