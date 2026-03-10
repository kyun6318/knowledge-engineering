# 비용 추정 + 모니터링 + 운영

> 전체 라이프사이클 비용 통합 추정 (Phase 0 API 검증 포함)
> + 모니터링 구성 + 보안 설계 + 리전 선택

---

## 1. 비용 추정

### 1.1 Phase 0: API 검증 + PoC (4~5주)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| **Vertex AI API 검증 (3일)** | Gemini Flash/Pro, Embedding, DocAI, RAG, VAS | **~$80** |
| Cloud Run Jobs | PoC 50건 파싱 + 추출 | ~$5 |
| GCS | 150GB 원본 업로드 + 1GB 파싱 결과 + 테스트 데이터셋 | ~$5 |
| BigQuery | 10MB 이하 | ~$0 (Free tier) |
| Neo4j AuraDB Free | 200K 노드 | $0 |
| Secret Manager | 8개 시크릿 | ~$0 |
| Anthropic API (PoC) | 50건 × 3모델 비교 (일반 API) | ~$20 |
| Vertex AI Embedding (PoC) | 20쌍 검증 | ~$10 |
| **Phase 0 합계** | | **~$120** |

> API 검증 비용 상세: Gemini Pro ~$30, Gemini Flash ~$10, DocAI ~$5, RAG/VAS ~$15, Embedding ~$10, Prompt Caching ~$10

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

### 1.3 Phase 2: 전체 처리 + 크롤링 (10~12주)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| **Anthropic Batch API (CandidateContext)** | 500K 이력서 × $0.00115/건 | **$575** |
| **Anthropic Batch API (CompanyContext)** | 10K JD × $0.0004/건 | **$4** |
| **Vertex AI Embedding** | 302M 토큰 × $0.0065/1M | **$2** |
| Cloud Run Jobs (전체 KG) | ~500시간 (전 Job 합산) | **$150** |
| Cloud Run Jobs (크롤링) | 홈페이지 + 뉴스 + LLM 추출 | **$30** |
| Gemini API (크롤링 추출) | 1,000기업 × ~15건 | **$5** |
| GCS | 150GB 원본 + 50GB 결과 + 크롤링 데이터 | **$8/월** |
| BigQuery | 10GB 서빙 + 크롤링 테이블 + 쿼리 | **$10/월** |
| Neo4j AuraDB Professional | 800K~8M 노드 전환 | **$100~200/월** |
| Cloud Workflows | 실행 횟수 | ~$1 |
| Cloud Monitoring / Logging | 기본 | ~$10/월 |
| Silver Label (PoC, Sonnet) | 2,000건 × $0.01 | **$20** |
| 프롬프트 최적화 LLM (Sonnet) | ~500건 | **~$600** |
| 네이버 뉴스 API | 무료 | $0 |
| **Phase 2 LLM 합계** | | **~$1,236** |
| **Phase 2 인프라/월** | | **~$130/월** |

### 1.4 시나리오별 총비용 (전 Phase 통합)

| 시나리오 | Phase 0 | Phase 1 | Phase 2 LLM | Phase 2 인프라 | Gold Label 인건비 | **총비용** | **원화** |
|---|---|---|---|---|---|---|---|
| **A: Haiku Batch (권장)** | $120 | $86 | $1,236 | ~$520 | $5,840 | **~$7,802** | **~1,069만** |
| A': Haiku→Sonnet Fallback | $120 | $86 | $3,547 | ~$520 | $5,840 | **~$10,113** | **~1,385만** |
| B: Sonnet Batch | $120 | $86 | $3,365 | ~$520 | $5,840 | **~$9,931** | **~1,360만** |
| C: On-premise (GPU) | $120 | $86 | $9,279 | ~$2,320 | $5,840 | **~$17,645** | **~2,417만** |
| D: Gemini Flash | $120 | $86 | $967 | ~$520 | $5,840 | **~$7,533** | **~1,032만** |

> **v2 vs v1 비용 차이**: +$80 (Phase 0 API 검증 내장) + $35 (크롤링 Phase 2 통합). 별도 프로젝트 운영 비용 절감.

### 1.5 운영 단계 (월간)

| 서비스 | 사용량 | 월 비용 |
|---|---|---|
| Neo4j AuraDB Professional | 800만 노드 유지 | $100~200 |
| GCS | 200GB | $5 |
| BigQuery | 10GB + 쿼리 | $10 |
| Cloud Run Jobs (증분 KG) | 일 1,000건 × 30일 | $10 |
| Cloud Run Jobs (크롤링 30일 주기) | 3 Jobs/월 | $3 |
| Anthropic API (증분) | 일 1,000건 × $0.00115 | $35 |
| Gemini API (크롤링 LLM 추출) | 1,000기업/월 | $5 |
| Vertex AI Embedding (증분) | 일 1,000건 | ~$0.01 |
| Cloud Scheduler + Workflows | 일 2회 + 월 1회 크롤링 | ~$1 |
| Monitoring / Logging | 기본 | $10 |
| 네이버 뉴스 API | 무료 | $0 |
| **운영 월 합계** | | **~$180~280/월** |

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
| 크롤링 성공률 < 70% | Slack | 즉시 |
| 뉴스 수집량 < 2건/기업 | Email | 일일 체크 |
| 크롤링 LLM 추출 성공률 < 85% | Slack | 즉시 |
| Gemini API 크롤링 비용 > $20/월 | Email | 일일 체크 |

### 2.3 Looker Studio 대시보드 구성

| 패널 | 데이터 소스 | 시각화 |
|---|---|---|
| KG 파이프라인 진행률 | `chunk_status` | 스택 바 차트 |
| KG 에러율 추이 | `processing_log` | 시계열 |
| LLM 비용 추적 | `processing_log` | 누적 비용 시계열 |
| 파싱 실패 분포 | `parse_failure_log` | 파이 차트 (tier별) |
| 피처 활성화 현황 | `mapping_features` | 히트맵 |
| 크롤링 성공률 | `crawl_homepage_pages` | 게이지 차트 |
| 뉴스 수집 현황 | `crawl_news_articles` | 기업별 바 차트 |
| CompanyContext fill_rate | `crawl_company_summary` | 게이지 차트 |
| Neo4j 적재 현황 | `processing_log` | 카운터 (노드/엣지 수) |

---

## 3. 보안 설계

### 3.1 PII 처리 플로우

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
| `kg-pipeline` | `workflows.invoker` | Cloud Workflows |
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

---

## 4. 리전 선택

| 서비스 | 리전 | 근거 |
|---|---|---|
| GCS | `asia-northeast3` (서울) | 데이터 주권, 레이턴시 |
| BigQuery | `asia-northeast3` | GCS와 같은 리전 |
| Cloud Run Jobs | `asia-northeast3` | GCS 접근 레이턴시 |
| Cloud Workflows | `asia-northeast3` | Cloud Run과 같은 리전 |
| Cloud Scheduler | `asia-northeast3` | 동일 |
| Vertex AI (Gemini/Embedding) | `us-central1` | 모델 제공 리전 |
| Document AI | `us` (멀티리전) | Phase 0 검증용, us/eu만 지원 |
| Discovery Engine (VAS) | `global` | Phase 0 검증용 |
| Neo4j AuraDB | `asia-northeast1` (도쿄) | 서울 미지원, 가장 가까움 (~10ms) |
| Anthropic API | US (외부) | 선택 불가 |

---

## 5. Docker 이미지

```dockerfile
# Dockerfile (KG 파이프라인 통합 이미지)
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 (HWP 변환용 LibreOffice)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY prompts/ ./prompts/

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

## 6. 빠른 시작 (30분)

```bash
# 1. 프로젝트 + API 활성화
gcloud config set project graphrag-kg
gcloud services enable run.googleapis.com secretmanager.googleapis.com \
  storage.googleapis.com bigquery.googleapis.com aiplatform.googleapis.com

# 2. GCS + 샘플 데이터
gcloud storage buckets create gs://graphrag-kg-data --location=asia-northeast3
gcloud storage cp sample_resumes/ gs://graphrag-kg-data/raw/resumes/ --recursive

# 3. API 키
echo -n "$ANTHROPIC_API_KEY" | gcloud secrets create anthropic-api-key --data-file=-

# 4. BigQuery
bq mk --dataset --location=asia-northeast3 graphrag_kg

# 5. 로컬 테스트 (Cloud Run 배포 전)
export GOOGLE_CLOUD_PROJECT=graphrag-kg
python src/parse_resumes.py --local --sample=10

# 6. Neo4j AuraDB Free → Console에서 생성 → Secret Manager 저장

# 7. 첫 번째 Cloud Run Job 배포 + 실행
IMAGE=asia-northeast3-docker.pkg.dev/graphrag-kg/kg-pipeline/kg-pipeline:latest
gcloud run jobs create kg-parse-poc \
  --image=$IMAGE --tasks=1 --cpu=2 --memory=4Gi \
  --region=asia-northeast3
gcloud run jobs execute kg-parse-poc --region=asia-northeast3
```
