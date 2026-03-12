# 비용 추정 + 모니터링 + 운영

> 전체 라이프사이클 비용 통합 추정 + 모니터링 구성 + 보안 설계
>
> **v1 대비 변경**:
> - 총비용: $8,023~8,774 → **$8,235~8,895** (Phase 2 기간 연장 반영)
> - 인력비: Phase별 개별 계상 제거 → **별도 관리** (Gold Label만 포함)
> - 모니터링: Phase 0-1 과도한 Runbook 제거 → **Phase 4에서 전체 구축**
> - 서비스 계정: 단일 → **3개 분리**

---

## 1. 비용 추정

### 1.1 Phase 0: 환경 + PoC (1주)

| 서비스 | 비용 |
|---|---|
| Anthropic API (PoC 20건 + Sonnet 비교) | ~$5 |
| Gemini Flash 대안 테스트 (10건) | ~$1 |
| Vertex AI Embedding (20쌍) | ~$0.001 |
| Batch API 실측 (3~5건) | ~$1 |
| GCS + BigQuery (초기 설정) | ~$1 |
| **Phase 0 합계** | **~$8** |

### 1.2 Phase 1: Core Candidate MVP (5주)

| 서비스 | 비용 |
|---|---|
| Cloud Run Jobs (크롤링, 법무 허용 시) | ~$3.6 |
| Cloud Run Jobs (전처리) | ~$2 |
| Cloud Run Service (GraphRAG API) | ~$5 |
| Anthropic Batch API (1,000건) | ~$3 |
| Anthropic API (프롬프트 튜닝 ~200건) | ~$20 |
| Vertex AI Embedding (1,000건) | ~$0.5 |
| Neo4j AuraDB Free | $0 |
| GCS + BigQuery | ~$1 |
| **Phase 1 합계** | **~$36** |

### 1.3 Phase 2: 파일 이력서 + 전체 처리 (8주)

#### LLM 비용

| 서비스 | 비용 |
|---|---|
| Anthropic Batch API (450K CandidateContext) | $1,350 |
| Anthropic API (재처리/에러 ~5,000건) | ~$25 |
| Anthropic API (Parser 프롬프트 ~300건) | ~$2 |
| Vertex AI Embedding (2.34M건) | ~$47 |
| Embedding Egress (서울→US, ~30GB) | ~$3.6 |
| Dead-letter 재처리 (~15,000건) | ~$45 |
| **Phase 2 LLM 합계** | **~$1,473** |

#### 인프라 비용 (8주 = ~2개월)

| 서비스 | 월 비용 | 8주 비용 |
|---|---|---|
| Cloud Run Jobs | ~$30/월 | ~$70 |
| GCS | $5/월 | ~$12 |
| BigQuery | $5/월 | ~$12 |
| Neo4j AuraDB Professional | $65~200/월 | ~$200~480 |
| Cloud Monitoring + Logging | ~$6/월 | ~$16 |
| **Phase 2 인프라 합계** | | **~$310~570** |

#### Phase 2 소계

| 항목 | 비용 |
|---|---|
| LLM | ~$1,473 |
| 인프라 | ~$310~570 |
| **Phase 2 합계** | **~$1,783~2,043** |

### 1.4 Phase 3: 기업 정보 + 매칭 (7주)

#### LLM 비용

| 서비스 | 비용 |
|---|---|
| Anthropic Batch API (CompanyContext 10K JD) | $4 |
| Anthropic Batch API (Vacancy 추출 10K) | $30 |
| Anthropic API (프롬프트 튜닝 + 검증) | ~$15 |
| Anthropic API (Organization ER LLM 2차) | ~$5 |
| Vertex AI Embedding (vacancy + company) | ~$0.2 |
| **Phase 3 LLM 합계** | **~$54** |

#### 인프라 비용 (7주 = ~1.75개월)

| 서비스 | 월 비용 | 7주 비용 |
|---|---|---|
| Neo4j Professional | $150~300/월 | ~$260~525 |
| Cloud Run + GCS + BigQuery | ~$15/월 | ~$26 |
| **Phase 3 인프라 합계** | | **~$286~551** |

#### Phase 3 소계

| 항목 | 비용 |
|---|---|
| LLM | ~$54 |
| 인프라 | ~$286~551 |
| **Phase 3 합계** | **~$340~605** |

### 1.5 Phase 4: 외부 보강 + 운영 (4주)

#### LLM 비용

| 서비스 | 비용 |
|---|---|
| Gemini API (크롤링 LLM 추출, 1,000기업) | ~$11 |
| Anthropic API (Gold Label 검증, 2,000건 Sonnet) | ~$20 |
| Vertex AI Embedding (5,000건) | ~$0.1 |
| **Phase 4 LLM 합계** | **~$31** |

#### 인프라 비용 (4주 = ~1개월)

| 서비스 | 월 비용 | 4주 비용 |
|---|---|---|
| Neo4j Professional | $150~300/월 | ~$150~300 |
| Cloud Run (크롤링 증가) | ~$20/월 | ~$20 |
| GCS + BigQuery | ~$5/월 | ~$5 |
| Cloud Workflows + Scheduler | ~$2/월 | ~$2 |
| **Phase 4 인프라 합계** | | **~$177~327** |

#### Gold Label 인건비

| 항목 | 비용 |
|---|---|
| 검수 전문가 1명 × 40시간 | ~$5,840 |
| (국내 전문가 대안) | (~200만원) |

#### Phase 4 소계

| 항목 | 비용 |
|---|---|
| LLM | ~$31 |
| 인프라 | ~$177~327 |
| Gold Label | ~$5,840 |
| **Phase 4 합계** | **~$6,048~6,198** |

### 1.6 전체 비용 총괄

| Phase | LLM | 인프라 | Gold Label | **합계** |
|---|---|---|---|---|
| Phase 0 (1주) | $7 | $1 | — | **$8** |
| Phase 1 (5주) | $24 | $12 | — | **$36** |
| Phase 2 (8주) | $1,473 | $310~570 | — | **$1,783~2,043** |
| Phase 3 (7주) | $54 | $286~551 | — | **$340~605** |
| Phase 4 (4주) | $31 | $177~327 | $5,840 | **$6,048~6,198** |
| **총합계** | **$1,589** | **$786~1,461** | **$5,840** | **$8,215~8,890** |
| **원화** | | | | **~1,125~1,218만** |

> v1 총비용 $8,023~8,774 대비: +$192~116 (Phase 2 기간 연장 반영)
> standard 총비용 $8,825~9,225 대비: $610~335 절감

### 1.7 운영 단계 월간 비용 (Phase 4 이후)

| 서비스 | 월 비용 |
|---|---|
| Neo4j AuraDB Professional | $100~200 |
| GCS + BigQuery | ~$16 |
| Cloud Run Jobs (일일 크롤링 + 증분) | ~$14 |
| Cloud Scheduler | ~$2 |
| Cloud Monitoring + Logging | ~$10 |
| Cloud Workflows | ~$1 |
| **운영 월간 합계** | **~$143~243** |

---

## 2. 모니터링 — Phase별 점진적 구축

> ★ v2: Phase 0-2는 최소 모니터링, Phase 4에서 전체 구축.

### Phase 0-2: 최소 모니터링 (BigQuery 쿼리 + Slack 수동)

```sql
-- 모니터링 쿼리 Q1: 처리 현황
SELECT pipeline, status, COUNT(*) as cnt
FROM graphrag_kg.processing_log
GROUP BY pipeline, status;

-- 모니터링 쿼리 Q2: 실패율
SELECT
  pipeline,
  COUNTIF(status = 'FAILED') / COUNT(*) as fail_rate
FROM graphrag_kg.processing_log
WHERE processed_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
GROUP BY pipeline;

-- 모니터링 쿼리 Q3: 비용 추적
SELECT
  DATE(processed_at) as dt,
  SUM(input_tokens + output_tokens) as total_tokens,
  SUM(input_tokens + output_tokens) * 0.000001 as estimated_cost
FROM graphrag_kg.processing_log
GROUP BY dt
ORDER BY dt DESC
LIMIT 7;
```

### Phase 2 추가: Alarm 3종

```
1. Cloud Run Job 실패 → Slack 알림
2. Neo4j 연결 실패 → Slack 알림
3. Batch API 만료 임박 (24h 이내 미수집) → Slack 알림
```

### Phase 4: 전체 모니터링 + Runbook

```
→ 05_phase4_enrichment_and_ops.md 참조
  - Runbook 5종
  - Alarm 10종 (Critical 3 + Warning 3 + Info 4)
  - Slack Webhook + (선택) PagerDuty
```

---

## 3. 보안 — 서비스 계정 분리 (★ v2)

### 서비스 계정 3개

| 계정 | 용도 | 권한 |
|------|------|------|
| `kg-crawling` | 크롤링 Job | storage.objectCreator, bigquery.dataEditor |
| `kg-processing` | 전처리 + LLM 추출 | storage.objectViewer/Creator, bigquery.dataEditor, aiplatform.user |
| `kg-loading` | Graph 적재 + API | storage.objectViewer, bigquery.dataViewer, **Neo4j 접근** |

### VPC 네트워크 (Phase 4에서 구성)

```
Neo4j AuraDB Professional:
  - Allowlist: Cloud Run Service IP만 허용
  - kg-loading 서비스 계정에서만 접근
  - 다른 서비스 계정은 Neo4j 접근 불가
```

---

## 4. 리전 선택 (v1과 동일)

| 서비스 | 리전 | 근거 |
|---|---|---|
| GCP 프로젝트 | asia-northeast3 (서울) | 데이터 주권, 레이턴시 |
| Vertex AI | us-central1 | Gemini/Embedding API 가용성 |
| Neo4j AuraDB | asia-northeast1 (도쿄) | 서울 미지원, 최소 레이턴시 |
