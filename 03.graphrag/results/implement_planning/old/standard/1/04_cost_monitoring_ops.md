# 비용 추정 + 모니터링 + 운영

> 전체 라이프사이클 비용 통합 추정 (Phase 0 API 검증 포함)
> + 모니터링 구성 + 보안 설계 + 리전 선택
>
> **standard.1 변경**:
> - [standard.21] 한국어 토큰 기준 Batch API 비용 재계산 (한글 1자 ≈ 2~3 tokens)
> - [standard.26] Embedding egress 비용 (서울→US) 추가
> - [standard.20] 백업 비용 반영
> - [standard.1-3] Neo4j Professional 비용 Phase 2 필수로 반영

---

## 1. 비용 추정

### 1.1 Phase 0: API 검증 + PoC (4~5주)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| **Vertex AI API 검증 (2일)** [standard.2] | Gemini Flash/Pro, Embedding, DocAI | **~$55** |
| Cloud Run Jobs | PoC 50건 파싱 + 추출 | ~$5 |
| GCS | 150GB 원본 업로드 + 1GB 파싱 결과 + 테스트 데이터셋 | ~$5 |
| BigQuery | 10MB 이하 | ~$0 (Free tier) |
| Neo4j AuraDB Free | 200K 노드 | $0 |
| Secret Manager | 8개 시크릿 | ~$0 |
| Anthropic API (PoC) | 50건 × 3모델 비교 (일반 API) | ~$20 |
| Vertex AI Embedding (PoC) | 20쌍 검증 | ~$10 |
| **Phase 0 합계** | | **~$95** |

> v2 대비 -$25: VAS/RAG Engine 검증 비용 제거 (~$15) + 검증 단축 [standard.2]

### 1.2 Phase 1: MVP 파이프라인 (10~12주)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| Cloud Run Jobs (파싱) | 2 vCPU × 4GB × ~6시간 | ~$10 |
| Cloud Run Jobs (Context) | CompanyContext 100건 + CandidateContext 1,000건 | ~$5 |
| Cloud Run Jobs (Graph) | 8 tasks × 2시간 | ~$5 |
| Cloud Run Jobs (기타) | Embedding, Mapping 등 | ~$10 |
| Anthropic API (개발) | 프롬프트 튜닝 + 통합 테스트 ~5,000건 | ~$50 |
| Vertex AI Embedding | 1,000건 테스트 | ~$1 |
| Neo4j AuraDB Free | 200K 노드 내 | $0 |
| BigQuery | 소량 | ~$5 |
| **Phase 1 합계** | | **~$86** |

### 1.3 Phase 2: 전체 처리 + 크롤링 (12~16주) — [standard.21] 한국어 토큰 보정

> **핵심 변경**: 한국어 이력서는 한글 1자 ≈ 2~3 tokens으로 토큰 효율이 낮음.
> 평균 input 1,500 tokens(영어 가정) → **3,000~4,000 tokens**(한국어 보정) 적용.

#### Anthropic Batch API 비용 재계산 [standard.21]

| 항목 | v2 가정 (영어 기준) | standard.1 가정 (한국어 보정) | 비고 |
|---|---|---|---|
| 이력서 평균 input tokens | 1,500 | 3,500 | 한글 ×2.3배 |
| 이력서 평균 output tokens | 500 | 800 | JSON 출력 (혼합) |
| Haiku Batch input 단가 | $0.40/1M | $0.40/1M | 50% 할인 적용 |
| Haiku Batch output 단가 | $2.00/1M | $2.00/1M | 50% 할인 적용 |
| **이력서 1건당 비용** | **$0.00160** | **$0.00300** | ×1.88배 |
| **500K 이력서 총비용** | **$800** | **$1,500** | |

| 서비스 | 사용량 | 비용 |
|---|---|---|
| **Anthropic Batch API (CandidateContext)** [standard.21] | 500K × $0.00300/건 | **$1,500** |
| **Anthropic Batch API (CompanyContext)** | 10K JD × $0.0004/건 | **$4** |
| **Vertex AI Embedding** | 302M 토큰 × $0.0001/1K | **$30** |
| **Embedding Egress (서울→US)** [standard.26] | ~30GB × $0.12/GB | **$3.6** |
| Cloud Run Jobs (전체 KG) | ~350시간 합산 [R-8 절감 반영] | **$88** |
| Cloud Run Jobs (크롤링) | 홈페이지 + 뉴스 + LLM 추출 | **$30** |
| Gemini API (크롤링 추출) | 1,000기업 × ~15건 | **$5** |
| GCS | 150GB 원본 + 50GB 결과 + Versioning [standard.20] | **$10/월** |
| BigQuery | 10GB 서빙 + 크롤링 + batch_tracking [standard.1-5] | **$10/월** |
| **Neo4j AuraDB Professional** [standard.1-3] | ~2.77M 노드, 필수 | **$100~200/월** |
| Cloud Workflows [standard.24] | 실행 횟수 | ~$1 |
| Cloud Monitoring / Logging | 기본 | ~$10/월 |
| Silver Label (PoC, Sonnet) | 2,000건 × $0.01 | **$20** |
| 프롬프트 최적화 LLM (Sonnet) | ~500건 | **~$600** |
| 네이버 뉴스 API | 무료 | $0 |
| **Phase 2 LLM 합계** | | **~$2,131** |
| **Phase 2 인프라/월** | | **~$115~215/월** |

> [R-12] LLM 비용 = Anthropic Batch + Embedding + Egress + Gemini 크롤링 + Silver Label + 프롬프트 최적화.
> 인프라 비용 = Cloud Run + GCS + BigQuery + Neo4j + Monitoring. 분류 기준을 명확히 하여 중복 계상 방지.

#### Cloud Run Jobs 비용 상세 [standard.21]

| Job | vCPU × 시간 | vCPU 비용 | Memory 비용 | 합계 |
|---|---|---|---|---|
| kg-parse-resumes | 2 × 50 tasks × 4h = 400 vCPU·h | $28.8 | $14.4 | $43.2 |
| kg-dedup-resumes | 4 × 1 task × 2h = 8 vCPU·h | $0.6 | $0.6 | $1.2 |
| kg-batch-prepare | 2 × 10 tasks × 1h = 20 vCPU·h | $1.4 | $0.7 | $2.1 |
| kg-batch-submit | 1 × 1 task × 0.5h = 0.5 vCPU·h [R-8] | $0.04 | $0.01 | **$0.05** |
| kg-batch-poll | 1 × 1 task × 0.1h × 48회 = 4.8 vCPU·h [R-8] | $0.35 | $0.07 | **$0.42** |
| kg-batch-collect | 2 × 20 tasks × 2h = 80 vCPU·h | $5.8 | $2.9 | $8.7 |
| kg-company-ctx | 2 × 5 tasks × 2h = 20 vCPU·h | $1.4 | $0.7 | $2.1 |
| kg-graph-load | 2 × 8 tasks × 12h = 192 vCPU·h | $13.8 | $6.9 | $20.7 |
| kg-embedding | 2 × 10 tasks × 6h = 120 vCPU·h | $8.6 | $4.3 | $12.9 |
| kg-mapping | 4 × 20 tasks × 3h = 240 vCPU·h | $17.3 | $13.8 | $31.1 |
| **합계** | **~1,085 vCPU·h** | | | **~$122** |

> [R-8] batch-submit/poll 분리로 $62 → $0.5 절감. 전체 Cloud Run 비용 $184 → ~$122.

> 단가: vCPU $0.072/h, Memory $0.008/GiB·h (asia-northeast3)

#### [standard.26] Embedding Egress 비용 계산

```
Embedding 대상 텍스트:
  - Chapter evidence_chunk: 450K × 5.2 chapters × 평균 200자 × 3 bytes/char = ~1.4GB
  - Vacancy description: 10K × 평균 500자 × 3 bytes/char = ~15MB
  - 합계: ~1.5GB (텍스트 데이터)

GCP Egress (asia-northeast3 → us-central1):
  - 같은 대륙 내: $0.01/GB (실제로는 대부분 무료 또는 최소)
  - 다른 대륙 간: $0.12/GB
  - 서울→US는 대륙 간: 1.5GB × $0.12 = ~$0.18

+ Embedding API 응답 (768d float32 × 항목 수):
  - (450K × 5.2 + 10K) × 768 × 4 bytes = ~7.2GB
  - US→서울: $0.12/GB × 7.2 = ~$0.86

= 총 Egress: ~$1.04 (v2 예상 "수십 GB" 보다 실제로는 적음)

→ 보수적 추정: $3.6 (안전 마진 ×3)
```

### 1.4 시나리오별 총비용 (전 Phase 통합) — [standard.21] 한국어 보정

| 시나리오 | Phase 0 | Phase 1 | Phase 2 LLM | Phase 2 인프라 (4개월) | Gold Label 인건비 | **총비용** | **원화** |
|---|---|---|---|---|---|---|---|
| **A: Haiku Batch (권장)** | $95 | $86 | $2,131 | ~$660 | $5,840 | **~$8,812** | **~1,207만** |
| A': Haiku→Sonnet Fallback | $95 | $86 | $5,504 | ~$720 | $5,840 | **~$12,245** | **~1,678만** |
| B: Sonnet Batch | $95 | $86 | $5,322 | ~$720 | $5,840 | **~$12,063** | **~1,653만** |
| C: On-premise (GPU) | $95 | $86 | $9,279 | ~$2,520 | $5,840 | **~$17,820** | **~2,441만** |
| D: Gemini Flash | $95 | $86 | $1,567 | ~$720 | $5,840 | **~$8,308** | **~1,138만** |

> **standard.1 vs v2 비용 차이**: 시나리오 A 기준 +$1,132 (+15%). 주 원인: 한국어 토큰 보정으로 Batch API 비용 $575→$1,500 증가.
> Gold Label 인건비($5,840)가 여전히 총비용의 65%를 차지하여 LLM 비용 차이의 절대적 영향은 제한적.

### 1.5 운영 단계 (월간)

| 서비스 | 사용량 | 월 비용 |
|---|---|---|
| **Neo4j AuraDB Professional** [standard.1-3] | 2.77M+ 노드 유지 | **$100~200** |
| GCS | 200GB + Versioning [standard.20] | $6 |
| BigQuery | 10GB + 쿼리 | $10 |
| Cloud Run Jobs (증분 KG) | 일 1,000건 × 30일 | $10 |
| Cloud Run Jobs (크롤링 30일 주기) | 3 Jobs/월 | $3 |
| Cloud Run Jobs (Neo4j 백업) [standard.20] | 주 1회 | $1 |
| Anthropic API (증분) | 일 1,000건 × $0.003 [standard.21] | $90 |
| Gemini API (크롤링 LLM 추출) | 1,000기업/월 | $5 |
| Vertex AI Embedding (증분) | 일 1,000건 | ~$0.01 |
| Cloud Scheduler + Workflows | 일 2회 + 주 1회 백업 + 월 1회 크롤링 | ~$1 |
| Monitoring / Logging | 기본 | $10 |
| 네이버 뉴스 API | 무료 | $0 |
| **운영 월 합계** | | **~$236~336/월** |

> v2 대비 +$56/월: 한국어 토큰 보정 Anthropic API $35→$90, Neo4j 백업 $1

---

## 2. 모니터링 구성

### 2.1 BigQuery 처리 로그 대시보드

```sql
-- 일일 처리 현황 (파이프라인별)
SELECT
  run_date,
  pipeline,
  COUNTIF(status = 'SUCCESS') AS success_count,
  COUNTIF(status = 'FAILED') AS fail_count,
  COUNTIF(status = 'PARTIAL') AS partial_count,
  ROUND(COUNTIF(status = 'FAILED') / COUNT(*) * 100, 2) AS error_rate_pct,
  SUM(input_tokens) AS total_input_tokens,
  SUM(output_tokens) AS total_output_tokens,
  ROUND(SUM(input_tokens) * 0.00000040 + SUM(output_tokens) * 0.0000020, 2) AS estimated_cost_usd
FROM graphrag_kg.processing_log
WHERE run_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY run_date, pipeline
ORDER BY run_date DESC, pipeline;

-- Chunk 진행률 (Phase 2 전체 처리 시)
SELECT
  pipeline,
  COUNT(*) AS total_chunks,
  COUNTIF(status = 'COMPLETED') AS completed,
  COUNTIF(status = 'PROCESSING') AS in_progress,
  COUNTIF(status = 'FAILED') AS failed,
  COUNTIF(status = 'PENDING') AS pending,
  ROUND(COUNTIF(status = 'COMPLETED') / COUNT(*) * 100, 1) AS completion_pct
FROM graphrag_kg.chunk_status
GROUP BY pipeline;

-- [standard.1-5] Batch API 추적 현황
SELECT
  status,
  COUNT(*) AS batch_count,
  COUNTIF(result_collected) AS collected,
  COUNTIF(NOT result_collected AND status = 'COMPLETED') AS uncollected,
  COUNTIF(retry_count > 0) AS retried,
  MIN(submitted_at) AS earliest_submitted,
  MAX(completed_at) AS latest_completed
FROM graphrag_kg.batch_tracking
GROUP BY status;

-- [standard.1-5] 만료 위험 batch (29일 보관 기간)
SELECT
  batch_id, chunk_id, submitted_at,
  TIMESTAMP_DIFF(TIMESTAMP_ADD(submitted_at, INTERVAL 29 DAY), CURRENT_TIMESTAMP(), HOUR) AS hours_until_expiry
FROM graphrag_kg.batch_tracking
WHERE status = 'COMPLETED' AND NOT result_collected
  AND TIMESTAMP_DIFF(TIMESTAMP_ADD(submitted_at, INTERVAL 29 DAY), CURRENT_TIMESTAMP(), HOUR) < 72
ORDER BY hours_until_expiry;

-- LLM 파싱 실패 모니터링 (v7 3-tier)
SELECT
  DATE(created_at) AS date,
  pipeline,
  failure_tier,
  COUNT(*) AS count,
  ROUND(AVG(partial_fields_extracted / NULLIF(total_fields, 0)) * 100, 1) AS avg_extraction_pct,
  COUNTIF(repair_success) AS repair_success_count
FROM graphrag_kg.parse_failure_log
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY date, pipeline, failure_tier
ORDER BY date DESC, pipeline, failure_tier;

-- 크롤링 품질 대시보드
SELECT
  DATE(created_at) AS crawl_date,
  COUNT(DISTINCT company_id) AS companies_crawled,
  COUNTIF(crawl_status = 'SUCCESS') AS pages_success,
  COUNTIF(crawl_status != 'SUCCESS') AS pages_failed,
  ROUND(COUNTIF(crawl_status = 'SUCCESS') / COUNT(*) * 100, 1) AS success_rate_pct
FROM graphrag_kg.crawl_homepage_pages
GROUP BY 1
ORDER BY 1 DESC;

-- 피처 활성화 비율
SELECT
  COUNT(*) AS total_mappings,
  COUNTIF(stage_match_status = 'ACTIVE') AS stage_active,
  COUNTIF(vacancy_fit_status = 'ACTIVE') AS vacancy_active,
  COUNTIF(domain_fit_status = 'ACTIVE') AS domain_active,
  COUNTIF(culture_fit_status = 'ACTIVE') AS culture_active,
  COUNTIF(role_fit_status = 'ACTIVE') AS role_active,
  ROUND(COUNTIF(active_feature_count >= 1) / COUNT(*) * 100, 1) AS at_least_1_active_pct,
  ROUND(AVG(overall_match_score), 3) AS avg_overall_score
FROM graphrag_kg.mapping_features;
```

### 2.2 Cloud Monitoring 알림 정책

| 조건 | 채널 | 임계값 |
|---|---|---|
| Cloud Run Job 실패 | Slack + Email | 즉시 |
| Dead-letter 건수 > 1,000 | Slack | 1시간 내 |
| LLM API 누적 비용 > $500 | Email | 일일 체크 |
| Neo4j 연결 실패 | Slack | 즉시 |
| 일일 증분 처리 미실행 | Email | 오전 6시 |
| 파싱 실패율 > 5% | Slack (WARNING) | 1시간 내 |
| 파싱 실패율 > 10% | Slack + Email (CRITICAL) | 즉시 |
| Chunk 처리 72시간 초과 | Email | 일일 체크 |
| **Batch 결과 만료 72시간 이내** [standard.1-5] | **Slack + Email (CRITICAL)** | **일일 체크** |
| 크롤링 성공률 < 70% | Slack | 즉시 |
| 뉴스 수집량 < 2건/기업 | Email | 일일 체크 |
| 크롤링 LLM 추출 성공률 < 85% | Slack | 즉시 |
| Gemini API 크롤링 비용 > $20/월 | Email | 일일 체크 |
| **Neo4j 백업 실패** [standard.20] | **Slack + Email** | **즉시** |

### [R-6] CRITICAL 알림 대응 절차 (Runbook)

| 알림 | 대응 절차 |
|------|-----------|
| **파싱 실패율 > 10%** | 1) processing_log에서 실패 패턴 확인 (특정 파일 형식?) → 2) dead-letter 샘플 3건 수동 확인 → 3) 파서 버그 시 핫픽스 + 재배포 → 4) LLM 출력 변경 시 프롬프트 수정 |
| **Batch 결과 만료 72시간 이내** | 1) `kg-batch-poll` 즉시 수동 실행 → 2) 수집 실패 시 Anthropic API 상태 확인 → 3) 수집 불가 시 해당 chunk 재제출 |
| **Neo4j 연결 실패** | 1) AuraDB Console에서 인스턴스 상태 확인 → 2) Secret Manager URI/password 유효성 확인 → 3) AuraDB 장애 시 Anthropic 처리는 계속, Graph 적재만 보류 |
| **Cloud Run Job 실패 (3회 연속)** | 1) Cloud Logging에서 OOM/Timeout 여부 확인 → 2) OOM: Job 메모리 상향 재배포 → 3) Timeout: 처리 건수 축소 후 재실행 |

### 2.3 Looker Studio 대시보드 구성

| 패널 | 데이터 소스 | 시각화 |
|---|---|---|
| KG 파이프라인 진행률 | `chunk_status` | 스택 바 차트 |
| KG 에러율 추이 | `processing_log` | 시계열 |
| LLM 비용 추적 | `processing_log` | 누적 비용 시계열 |
| 파싱 실패 분포 | `parse_failure_log` | 파이 차트 (tier별) |
| **Batch API 상태** [standard.1-5] | `batch_tracking` | 상태별 카운터 + 만료 경고 |
| 피처 활성화 현황 | `mapping_features` | 히트맵 |
| 크롤링 성공률 | `crawl_homepage_pages` | 게이지 차트 |
| 뉴스 수집 현황 | `crawl_news_articles` | 기업별 바 차트 |
| CompanyContext fill_rate | `crawl_company_summary` | 게이지 차트 |
| Neo4j 적재 현황 | `processing_log` | 카운터 (노드/엣지 수) |
| **Neo4j 백업 이력** [standard.20] | `backups/neo4j/` (GCS) | 리스트 |

---

## 3. 보안 설계

### 3.1 PII 처리 플로우 — [standard.1-8] 법무 검토 연동

```
[이력서 원본 (PII 포함)]
    │
    ├─ GCS에 저장 (암호화: Google-managed key)
    │   └─ IAM: kg-pipeline SA만 접근 가능
    │
    ├─ Cloud Run Job 내에서 PII 마스킹
    │   ├─ 이름 → [NAME]
    │   ├─ 연락처 → [PHONE]
    │   ├─ 주소 → [ADDR]
    │   └─ offset mapping 보존 (span 역매핑용)
    │
    ├─ [standard.1-8] 법무 판정에 따라:
    │   ├─ 허용: 마스킹 선택적 (성능 최적화 시 마스킹 제거 가능)
    │   ├─ 조건부 허용: 마스킹 필수, Anthropic DPA 체결 필요
    │   └─ 불허: 시나리오 C (On-premise GPU) 전환 → Phase 0-6 의사결정
    │
    ├─ 마스킹된 텍스트만 Anthropic API로 전송
    │   └─ API 키: Secret Manager에서 런타임 조회
    │
    └─ 추출 결과의 evidence_span → offset mapping으로 원본 위치 역매핑
```

### 3.2 IAM 최소 권한

| 서비스 계정 | 역할 | 접근 대상 |
|---|---|---|
| `kg-pipeline` | `storage.objectAdmin` | `gs://graphrag-kg-data/` |
| `kg-pipeline` | `bigquery.dataEditor` | `graphrag_kg` 데이터셋 |
| `kg-pipeline` | `secretmanager.secretAccessor` | API 키 시크릿 |
| `kg-pipeline` | `run.invoker` | Cloud Run Jobs |
| `kg-pipeline` | `workflows.invoker` | Cloud Workflows (Phase 2+) [standard.24] |
| `kg-pipeline` | `monitoring.metricWriter` | 커스텀 메트릭 |
| `kg-pipeline` | `logging.logWriter` | Cloud Logging |
| `kg-pipeline` | `aiplatform.user` | Vertex AI Embedding/Gemini API |

### 3.3 Secret Manager 등록 대상

| 시크릿 이름 | 용도 |
|---|---|
| `anthropic-api-key` | Claude Haiku/Sonnet API |
| `neo4j-uri` | Neo4j AuraDB 연결 |
| `neo4j-user` | Neo4j 인증 |
| `neo4j-password` | Neo4j 인증 |
| `naver-api-client-id` | 네이버 뉴스 API |
| `naver-api-client-secret` | 네이버 뉴스 API |

### 3.4 [standard.1-9] 크롤링 데이터 보안 정책

```
크롤링 데이터 취급 정책:
  - 원본 HTML은 분석 후 30일 뒤 자동 삭제 (GCS lifecycle policy)
  - 추출 결과(BigQuery)만 영구 보관
  - 크롤링 데이터를 LLM 학습에 사용하지 않음 (추출 목적 한정)
  - 개인정보 포함 가능성 있는 careers 페이지: PII 마스킹 적용
```

---

## 4. 리전 선택

| 서비스 | 리전 | 근거 |
|---|---|---|
| GCS | `asia-northeast3` (서울) | 데이터 주권, 레이턴시 |
| BigQuery | `asia-northeast3` | GCS와 같은 리전 |
| Cloud Run Jobs | `asia-northeast3` | GCS 접근 레이턴시 |
| Cloud Workflows | `asia-northeast3` | Cloud Run과 같은 리전 (Phase 2+) [standard.24] |
| Cloud Scheduler | `asia-northeast3` | 동일 |
| Vertex AI (Gemini/Embedding) | `us-central1` | 모델 제공 리전 |
| Document AI | `us` (멀티리전) | Phase 0 검증용, us/eu만 지원 |
| Neo4j AuraDB | `asia-northeast1` (도쿄) | 서울 미지원, 가장 가까움 (~10ms) |
| Anthropic API | US (외부) | 선택 불가 |

---

## 5. Docker 이미지

```dockerfile
# Dockerfile (KG 파이프라인 통합 이미지)
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 (HWP 변환용 LibreOffice) — [standard.1-2] HWP 지원
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY prompts/ ./prompts/
COPY tests/ ./tests/    # [standard.1-6] 테스트 포함

CMD ["python", "src/main.py"]
```

```dockerfile
# Dockerfile.crawler (크롤링 전용 이미지)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy
WORKDIR /app
COPY requirements-crawl.txt .
RUN pip install --no-cache-dir -r requirements-crawl.txt
COPY src/ ./src/
CMD ["python", "src/homepage_crawler.py"]
```

```
# requirements.txt (KG 파이프라인)
anthropic>=0.39.0
google-cloud-aiplatform>=1.74.0
google-cloud-bigquery>=3.20.0
google-cloud-storage>=2.14.0
google-cloud-secret-manager>=2.18.0
neo4j>=5.15.0
pymupdf>=1.23.0
python-docx>=1.1.0
pydantic>=2.5.0
simhash>=2.1.2
json-repair>=0.28.0
pyhwp>=0.1b12          # [standard.1-2] HWP 파싱

# 테스트 [standard.1-6]
pytest>=8.0.0
pytest-cov>=4.1.0
deepdiff>=6.7.0

# requirements-crawl.txt (크롤링)
google-genai>=1.5.0
google-cloud-bigquery>=3.20.0
google-cloud-storage>=2.14.0
google-cloud-secret-manager>=2.18.0
readability-lxml>=0.8.1
beautifulsoup4>=4.12.0
requests>=2.31.0
```

---

## 6. 백업 전략 — [standard.20]

### 6.1 GCS Object Versioning

```bash
# contexts/ 및 mapping-features/의 데이터 보호
# (LLM 재생성 비용이 높으므로 버전 관리 필수)
gcloud storage buckets update gs://graphrag-kg-data --versioning

# 30일 이전 비현재 버전 자동 삭제 (비용 제어)
cat > lifecycle.json << 'EOF'
{
  "rule": [{
    "action": {"type": "Delete"},
    "condition": {
      "numNewerVersions": 3,
      "isLive": false
    }
  }]
}
EOF
gcloud storage buckets update gs://graphrag-kg-data --lifecycle-file=lifecycle.json
```

### 6.2 Neo4j 백업

| 단계 | 방법 | 주기 |
|---|---|---|
| Phase 0~1 (Free) | 수동 APOC export → GCS | Phase 1 완료 시 1회 |
| Phase 2+ (Professional) | Cloud Run Job + Cloud Scheduler | 주 1회 자동 |
| Professional 자동 백업 | AuraDB 자체 기능 (Professional 기본 제공) | 일 1회 |

### 6.3 BigQuery 백업

```
- BigQuery 테이블 삭제 방지: time-travel (7일) 기본 활성화
- 중요 테이블(mapping_features, processing_log): 스냅샷 데코레이터로 복구 가능
- 월 1회 BigQuery export → GCS (장기 보관용)
```

---

## 7. 빠른 시작 (30분)

```bash
# 1. 프로젝트 + API 활성화
gcloud config set project graphrag-kg
gcloud services enable run.googleapis.com secretmanager.googleapis.com \
  storage.googleapis.com bigquery.googleapis.com aiplatform.googleapis.com

# 2. GCS + Object Versioning [standard.20] + 샘플 데이터
gcloud storage buckets create gs://graphrag-kg-data --location=asia-northeast3
gcloud storage buckets update gs://graphrag-kg-data --versioning
gcloud storage cp sample_resumes/ gs://graphrag-kg-data/raw/resumes/ --recursive

# 3. API 키
echo -n "$ANTHROPIC_API_KEY" | gcloud secrets create anthropic-api-key --data-file=-

# 4. BigQuery
bq mk --dataset --location=asia-northeast3 graphrag_kg

# 5. 로컬 테스트 (Cloud Run 배포 전)
export GOOGLE_CLOUD_PROJECT=graphrag-kg
python src/parse_resumes.py --local --sample=10

# 6. 테스트 실행 [standard.1-6]
pytest tests/ -v

# 7. Neo4j AuraDB Free → Console에서 생성 → Secret Manager 저장

# 8. 첫 번째 Cloud Run Job 배포 + 실행
IMAGE=asia-northeast3-docker.pkg.dev/graphrag-kg/kg-pipeline/kg-pipeline:latest
gcloud run jobs create kg-parse-poc \
  --image=$IMAGE --tasks=1 --cpu=2 --memory=4Gi \
  --region=asia-northeast3
gcloud run jobs execute kg-parse-poc --region=asia-northeast3
```
