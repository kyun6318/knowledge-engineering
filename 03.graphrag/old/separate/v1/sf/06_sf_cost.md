# S&F 팀 비용 (Single Source of Truth)

> v5 `06_cost_and_monitoring.md` 기반. S&F 담당 항목만 추출.

---

## Phase별 비용

### Phase 0 (1주)

| 항목 | 비용 |
|------|------|
| Anthropic API (PoC 20건 + Sonnet 비교 + 적응형 검증) | ~$7 |
| 기타 (Gemini 테스트, Embedding, Batch 실측, GCS/BQ 초기) | ~$3 |
| **Phase 0 합계** | **~$10** |

### Phase 1 (5주, W2-6 중 S&F는 W2-5)

| 항목 | 비용 |
|------|------|
| Anthropic API (Batch 1,000건 + 프롬프트 튜닝 ~200건) | ~$24 |
| Cloud Run (크롤링 Job + 전처리) | ~$8 |
| 기타 (Embedding, GCS/BQ) | ~$2 |
| **Phase 1 합계** | **~$34** |

### Phase 2 (9주, W7-15)

| 항목 | 비용 |
|------|------|
| Anthropic Batch API (600K, 적응형 호출) | $1,488 |
| Anthropic API (재처리/에러 ~6K건 + Parser ~300건) | ~$32 |
| 파일 섹션 분리 LLM 폴백 (30K건, Batch API, R4) | ~$60 |
| Dead-letter 재처리 (~18K건) | ~$54 |
| Vertex AI Embedding (2.6M건) | ~$52 |
| Embedding Egress (서울→US) | ~$4 |
| Cloud Run Jobs (9주) | ~$84 |
| GCS + BigQuery (9주) | ~$30 |
| 기타 | ~$20 |
| **Phase 2 합계 (S&F 분)** | **~$1,824** |

> Neo4j Professional 비용($225~540)은 GraphRAG 팀 비용

### Phase 3 (6주, W17-22 중 S&F는 W17-18 + 잔여)

| 항목 | 비용 |
|------|------|
| Anthropic Batch API (CompanyContext 10K JD) | $4 |
| Anthropic Batch API (Vacancy 추출 10K) | $30 |
| Anthropic API (프롬프트 튜닝 + 검증 + ER LLM) | ~$20 |
| Vertex AI Embedding (vacancy + company) | ~$0.2 |
| Cloud Run + GCS + BQ (S&F 분) | ~$10 |
| **Phase 3 합계 (S&F 분)** | **~$64** |

### Phase 4 (4주, W24-27 중 S&F는 W24-25)

| 항목 | 비용 |
|------|------|
| Gemini API (크롤링 LLM 추출, 1,000기업) | ~$11 |
| Vertex AI Embedding (5,000건) | ~$0.1 |
| Cloud Run + GCS + BQ (S&F 분) | ~$12 |
| **Phase 4 합계 (S&F 분)** | **~$23** |

---

## S&F 비용 총괄

| Phase | LLM | Embedding | 인프라 | **합계** |
|-------|-----|-----------|-------|--------|
| Phase 0 | $7 | $0.1 | $3 | **~$10** |
| Phase 1 | $24 | $1 | $9 | **~$34** |
| Phase 2 | $1,634 | $56 | $134 | **~$1,824** |
| Phase 3 | $54 | $0.2 | $10 | **~$64** |
| Phase 4 | $11 | $0.1 | $12 | **~$23** |
| **합계** | **$1,730** | **~$57** | **~$168** | **~$1,955** |
