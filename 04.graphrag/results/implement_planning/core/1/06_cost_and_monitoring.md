# 비용 추정 + 모니터링 + 운영

> 전체 라이프사이클 비용 통합 추정 + 모니터링 구성 + 보안 설계 + 리전 선택
>
> **core 확장 총비용**: ~$7,805~8,205 (원화 ~1,069~1,124만)
> **standard 대비**: $8,825~9,225 → ~$1,000 절감 (Phase 0 축소, 인프라 기간 효율화)

---

## 1. 비용 추정

### 1.1 Phase 0: 환경 + PoC (1주)

| 서비스 | 사용량 | 단가 | 비용 |
|---|---|---|---|
| Anthropic API (PoC 20건) | Haiku 20건 + Sonnet 비교 | - | ~$5 |
| Vertex AI Embedding | 20쌍 | $0.02/1K | ~$0.001 |
| Batch API 실측 | 3~5건 | - | ~$1 |
| GCS + BigQuery | 초기 설정 | - | ~$1 |
| **Phase 0 합계** | | | **~$8** |

**근거**:
- PoC 범위: 이력서 3개 × 5회, embedding 패턴 검증
- Batch API 비용은 PoC이므로 일반 API 대비 비용 (1회용)

### 1.2 Phase 1: Core Candidate MVP (5주)

| 서비스 | 사용량 | 단가 | 비용 |
|---|---|---|---|
| Cloud Run Jobs (크롤링) | Playwright ~20시간 | $0.00005/초 | ~$3.6 |
| Cloud Run Jobs (전처리) | 1,000건 | - | ~$2 |
| Anthropic Batch API (1,000건) | 1,000건 CandidateContext | $0.003/건 | ~$3 |
| Anthropic API (프롬프트 튜닝) | ~200건 일반 API | $0.005/건 | ~$20 |
| Vertex AI Embedding | 1,000건 × 5 버전 | $0.02/1K | ~$0.5 |
| Neo4j AuraDB Free | Free tier | - | $0 |
| GCS + BigQuery | 1GB | - | ~$1 |
| Cloud Scheduler (일일 1회) | 5 jobs × 7일 | $0.1/job/month | ~$0.04 |
| **Phase 1 합계** | | | **~$30.14** |

**근거**:
- Playwright 크롤링: 평일 20시간 (4주) + 점차 감소
- 전처리: 1,000건 텍스트 청소, 청킹
- Batch API: PoC 대비 본격 사용 (Haiku 권장)
- 프롬프트 튜닝: 다양한 프롬프트 실험 200회

### 1.3 Phase 2: 파일 이력서 + 전체 450K 처리 (6주)

#### 2.3.1 LLM 비용

| 서비스 | 사용량 | 단가 | 비용 |
|---|---|---|---|
| Anthropic Batch API (450K CandidateContext) | 450,000건 | $0.003/건 | $1,350 |
| Anthropic API (재처리/에러) | ~5,000건 | $0.005/건 | ~$25 |
| Anthropic API (Parser 프롬프트) | ~300건 | $0.005/건 | ~$2 |
| Vertex AI Embedding (450K + delta) | 2,340,000건 | $0.02/1K | ~$47 |
| Embedding Egress (서울→US) | ~30GB × $0.12/GB | - | ~$3.6 |
| Dead-letter 재처리 (자동) | ~15,000건 | $0.003/건 | ~$45 |
| **Phase 2 LLM 합계** | | | **~$1,472.6** |

#### 2.3.2 인프라 비용 (~2개월, 6주)

| 서비스 | 월 비용 | 비고 | 6주 비용 |
|---|---|---|---|
| Cloud Run Jobs | ~$30/월 | 일일 2회 job | ~$52.5 |
| GCS | $5/월 | 1TB 이하 | ~$8.75 |
| BigQuery | $5/월 | on-demand 최소 | ~$8.75 |
| Neo4j AuraDB Professional | $65~200/월 | 노드 수 증가 | ~$150~350 |
| Cloud Monitoring | $5/월 | 기본 모니터링 | ~$8.75 |
| Cloud Logging | ~$1/월 | 기본 로깅 | ~$1.75 |
| **Phase 2 인프라 합계** | | | **~$230.25~430.25** |

#### 2.3.3 Phase 2 소계

| 항목 | 비용 |
|---|---|
| LLM 비용 | ~$1,472.6 |
| 인프라 비용 | ~$230.25~430.25 |
| **Phase 2 합계** | **~$1,702.85~1,902.85** |

**근거**:
- Batch API 주 처리: 450K 후보자 데이터
- PDF/DOCX 파서: LibreOffice + LLM (구조화)
- Neo4j: 1,000~5,000 노드 범위 (중간 규모)
- Embedding: 문장 + chunk 단위 (~5배)

### 1.4 Phase 3: 기업 정보 + 매칭 (6주)

#### 1.4.1 LLM 비용

| 서비스 | 사용량 | 단가 | 비용 |
|---|---|---|---|
| Anthropic Batch API (CompanyContext 10K JD) | 10,000건 | $0.0004/건 | $4 |
| Anthropic Batch API (Vacancy 추출) | 10,000건 | $0.003/건 | $30 |
| Anthropic API (프롬프트 튜닝 + 검증) | ~300건 | $0.005/건 | ~$15 |
| Anthropic API (매칭 로직 검증) | ~300건 | $0.005/건 | ~$15 |
| Vertex AI Embedding (vacancy + company) | 10,000건 | $0.02/1K | ~$0.2 |
| **Phase 3 LLM 합계** | | | **~$64.2** |

#### 1.4.2 인프라 비용 (~1.5개월)

| 서비스 | 월 비용 | 6주 비용 |
|---|---|---|
| Neo4j Professional | $150~300/월 | ~$225~450 |
| Cloud Run + GCS + BigQuery | ~$15/월 | ~$22.5 |
| Cloud Scheduler (매칭 주 1회) | - | ~$0.025 |
| **Phase 3 인프라 합계** | | **~$247.5~472.5** |

#### 1.4.3 Phase 3 소계

| 항목 | 비용 |
|---|---|
| LLM 비용 | ~$64.2 |
| 인프라 비용 | ~$247.5~472.5 |
| **Phase 3 합계** | **~$311.7~536.7** |

**근거**:
- CompanyContext: 약 10K JD (6주 수집)
- Vacancy 추출: 동일 10K건 (구조화 단순)
- 매칭: 복잡도 높지 않음 (별도 LLM 사용 없음)

### 1.5 Phase 4: 외부 보강 + 품질 + 운영 (6주)

#### 1.5.1 LLM 비용

| 서비스 | 사용량 | 단가 | 비용 |
|---|---|---|---|
| Gemini API (크롤링 LLM 추출) | 1,000기업 × ~15건 | $0.00075/건 | ~$11.25 |
| Anthropic API (Gold Label 검증) | 2,000건 × Sonnet | $0.01/건 | ~$20 |
| Anthropic API (추가 프롬프트) | ~500건 | $0.005/건 | ~$2.5 |
| Vertex AI Embedding (뉴스 + 보강) | 5,000건 | $0.02/1K | ~$0.1 |
| **Phase 4 LLM 합계** | | | **~$33.85** |

#### 1.5.2 인프라 비용 (~1.5개월)

| 서비스 | 월 비용 | 6주 비용 |
|---|---|---|
| Neo4j Professional | $150~300/월 | ~$225~450 |
| Cloud Run (크롤링 증가) | ~$20/월 | ~$30 |
| GCS + BigQuery | ~$5/월 | ~$7.5 |
| Cloud Scheduler (크롤링 일일) | - | ~$0.3 |
| Cloud Workflows (보강 파이프라인) | ~$1/월 | ~$1.5 |
| **Phase 4 인프라 합계** | | **~$264.3~489.3** |

#### 1.5.3 Gold Label 인건비

| 항목 | 수량 | 단가 | 비용 |
|---|---|---|---|
| 검수 전문가 (유경험) | 2명 | - | - |
| 검수량 | 200건 (후보자-매칭 쌍) | - | - |
| 시간당 비용 | 2명 × $200/h × 200건 ÷ 0.5건/h | - | ~$160,000 |
| **근거**: 검수 난이도 중간 (2~3분/건) | | | **재산정: $5,840** |

> **수정**: Phase 4에서 200건 검수, 유경험 검수자 1명 × 약 40시간 (8시간/일 × 5일) = ~$5,840 (또는 국내 전문가 200만원)

#### 1.5.4 Phase 4 소계

| 항목 | 비용 |
|---|---|
| LLM 비용 | ~$33.85 |
| 인프라 비용 | ~$264.3~489.3 |
| Gold Label 인건비 | ~$5,840 |
| **Phase 4 합계** | **~$6,138.15~6,363.15** |

**근거**:
- 외부 보강: 홈페이지, 뉴스 크롤링 (제한적)
- Gold Label: 200건 검수 (검증용, 품질 확보)
- 운영 자동화: 주간 크롤링 + 월간 업데이트

### 1.6 시나리오별 총비용

#### 1.6.1 전체 기간 비용 (Phase 0~4, 25주)

| 항목 | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | **합계** |
|---|---|---|---|---|---|---|
| LLM 비용 | $8 | ~$23.14 | ~$1,472.6 | ~$64.2 | ~$33.85 | ~$1,601.79 |
| 인프라 비용 | $0 | ~$0.1 | ~$230.25~430.25 | ~$247.5~472.5 | ~$264.3~489.3 | ~$742.15~1,392.15 |
| 인건비 (Gold Label) | $0 | $0 | $0 | $0 | ~$5,840 | ~$5,840 |
| **각 Phase 합계** | **~$8** | **~$23.24** | **~$1,702.85~1,902.85** | **~$311.7~536.7** | **~$6,138.15~6,363.15** | **~$8,183.94~8,833.94** |

#### 1.6.2 추정 범위

| 시나리오 | Phase 0-1 | Phase 2 | Phase 3 | Phase 4 | Gold Label | **총비용** | **원화** |
|---|---|---|---|---|---|---|---|
| **A: Haiku Batch (권장)** | ~$31.24 | ~$1,702.85~1,902.85 | ~$311.7~536.7 | ~$6,138.15~6,363.15 | ~$5,840 | **~$8,023.94~8,773.94** | **~1,099만~1,202만** |
| **B: Sonnet Batch (고품질)** | ~$31.24 | ~$2,202.85~2,402.85 | ~$314.2~539.2 | ~$6,188.15~6,413.15 | ~$5,840 | **~$8,576.39~9,326.39** | **~1,175만~1,278만** |

**주요 변수**:
- Neo4j 노드 수: 1,000~5,000 (월 $65~300 범위)
- Embedding egress: 서울→US 트래픽 (30GB 가정)
- Gold Label: 200건 × $292/h 또는 국내 전문가 200만원 선택

### 1.7 운영 단계 월간 비용 (Phase 4 이후)

| 서비스 | 설명 | 월 비용 |
|---|---|---|
| Neo4j AuraDB Professional | 유지보수 | $100~200 |
| GCS + BigQuery | 인크리멘탈 저장 + 분석 | ~$16 |
| Cloud Run Jobs | 일일 크롤링 + 주간 벤치 | ~$14 |
| Cloud Scheduler | 스케줄 작업 | ~$2 |
| Cloud Monitoring + Logging | 모니터링 | ~$10 |
| Anthropic API (증분 1,000건/일) | 신입 후보자 처리 | ~$90 |
| Gemini API (크롤링 LLM) | 홈페이지 추출 | ~$5 |
| Vertex AI Embedding | 벡터 임베딩 | ~$0.01 |
| Cloud Workflows | 파이프라인 오케스트레이션 | ~$1 |
| Secret Manager + Service Account | 보안 관리 | ~$2 |
| **운영 월 합계** | | **~$240~340/월** |

**계절성**: 채용 성수기(3~5월, 9~10월) → 15~20% 증가

---

## 2. 모니터링 구성

### 2.1 Phase 0~1: 최소 모니터링

#### 2.1.1 3가지 Critical Alerts

```
ALARM 1: Cloud Run Job 연속 3회 실패
  - Metric: cloud_run_job.failed_count
  - Condition: count > 3 in 1 hour
  - Action: Slack #ml-alerts (urgent)
  - Runbook: 01-cloud-run-job-failure.md

ALARM 2: Neo4j 연결 실패
  - Metric: connectivity_check.success = false
  - Condition: 2회 연속 (10분 간격)
  - Action: Slack + PagerDuty
  - Runbook: 02-neo4j-connection-failure.md

ALARM 3: Batch API 결과 만료 72시간 이내
  - Metric: batch_api.result_ttl_hours < 72
  - Condition: any processing job
  - Action: Slack + Email to team
  - Runbook: 03-batch-api-expiration.md
```

#### 2.1.2 BigQuery 모니터링 쿼리 (5종)

**Q1: 전체 파이프라인 진행률**

```sql
-- Purpose: Phase 1~2 진행 상황 실시간 모니터링
SELECT
  DATE(created_at) as date,
  COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed,
  COUNT(CASE WHEN status = 'PROCESSING' THEN 1 END) as processing,
  COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed,
  COUNT(*) as total,
  ROUND(100 * COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) / COUNT(*), 2) as completion_rate
FROM `project.dataset.candidate_context`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY date
ORDER BY date DESC;
```

**Q2: Batch API 상태**

```sql
-- Purpose: Batch job 별 처리 현황 및 에러율
SELECT
  batch_job_id,
  batch_type,
  COUNT(*) as total_items,
  COUNT(CASE WHEN parse_status = 'SUCCESS' THEN 1 END) as success,
  COUNT(CASE WHEN parse_status = 'FAILED' THEN 1 END) as failed,
  COUNT(CASE WHEN parse_status = 'TIMEOUT' THEN 1 END) as timeout,
  ROUND(100 * COUNT(CASE WHEN parse_status = 'SUCCESS' THEN 1 END) / COUNT(*), 2) as success_rate,
  MIN(created_at) as start_time,
  MAX(completed_at) as end_time,
  TIMESTAMP_DIFF(MAX(completed_at), MIN(created_at), MINUTE) as duration_minutes
FROM `project.dataset.batch_api_logs`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 14 DAY)
GROUP BY batch_job_id, batch_type
ORDER BY created_at DESC;
```

**Q3: 일일 크롤링 현황**

```sql
-- Purpose: Playwright 크롤링 성공률 및 트렌드
SELECT
  DATE(crawl_start) as crawl_date,
  crawl_source,
  COUNT(*) as total_urls,
  COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as success,
  COUNT(CASE WHEN status = 'TIMEOUT' THEN 1 END) as timeout,
  COUNT(CASE WHEN status = 'ERROR' THEN 1 END) as error,
  COUNT(CASE WHEN status = 'BLOCKED' THEN 1 END) as blocked,
  ROUND(100 * COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) / COUNT(*), 2) as success_rate,
  ROUND(AVG(CASE WHEN status = 'SUCCESS' THEN response_time_ms END), 0) as avg_response_ms
FROM `project.dataset.crawl_logs`
WHERE crawl_start >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY crawl_date, crawl_source
ORDER BY crawl_date DESC;
```

**Q4: LLM 파싱 실패 분포**

```sql
-- Purpose: 파싱 에러 원인 분석 (Phase 2 파일 파서)
SELECT
  error_type,
  error_message,
  COUNT(*) as count,
  COUNT(DISTINCT candidate_id) as affected_candidates,
  MIN(first_error_at) as first_occurrence,
  MAX(last_error_at) as last_occurrence,
  ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM `project.dataset.parse_errors`), 2) as percentage
FROM `project.dataset.parse_errors`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY error_type, error_message
ORDER BY count DESC;
```

**Q5: 만료 위험 Batch (72시간 이내)**

```sql
-- Purpose: Batch API 결과 TTL 모니터링 (1일 1회 실행)
SELECT
  batch_job_id,
  batch_type,
  created_at,
  result_expires_at,
  TIMESTAMP_DIFF(result_expires_at, CURRENT_TIMESTAMP(), HOUR) as hours_until_expiry,
  COUNT(*) as pending_items,
  CONCAT('gs://', bucket, '/', object_name) as result_path
FROM `project.dataset.batch_api_logs`
WHERE
  result_expires_at > CURRENT_TIMESTAMP()
  AND TIMESTAMP_DIFF(result_expires_at, CURRENT_TIMESTAMP(), HOUR) < 72
  AND status NOT IN ('COMPLETED', 'FAILED', 'ARCHIVED')
ORDER BY result_expires_at ASC;
```

#### 2.1.3 대시보드 구성

```
GCP Cloud Monitoring Dashboard (JSON):
{
  "displayName": "GraphRAG Core Phase 0-1 Monitor",
  "dashboardFilters": [],
  "gridLayout": {
    "widgets": [
      {
        "title": "Pipeline Completion Rate",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "metric.type=\"custom.googleapis.com/pipeline/completion_rate\""
              }
            }
          }]
        }
      },
      {
        "title": "Cloud Run Job Failures (Last 7d)",
        "scorecard": {
          "timeSeriesQuery": {
            "timeSeriesFilter": {
              "filter": "metric.type=\"run.googleapis.com/job_executions\" AND resource.type=\"cloud_run_job\"",
              "aggregation": {
                "alignmentPeriod": "60s",
                "perSeriesAligner": "ALIGN_RATE"
              }
            }
          }
        }
      },
      {
        "title": "Neo4j Connection Status",
        "scorecard": {
          "gaugePresentation": {
            "lowerBound": 0,
            "upperBound": 1
          }
        }
      },
      {
        "title": "Batch API Success Rate",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "metric.type=\"custom.googleapis.com/batch_api/success_rate\""
              }
            }
          }]
        }
      },
      {
        "title": "Cost Tracker (Daily)",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"billing_account\""
              }
            }
          }]
        }
      }
    ]
  }
}
```

### 2.2 Phase 2~3: 확장 모니터링

#### 2.2.1 추가 Alarms (총 10개)

```
ALARM 4: Dead-letter 건수 > 1,000
  - Metric: pubsub.subscription.dead_letter.message_count
  - Condition: > 1,000 in 24 hours
  - Action: Slack + PagerDuty (high priority)
  - Investigation: Q4 실패 분포 쿼리 실행

ALARM 5: LLM API 누적 비용 > $500/일
  - Metric: billing.googleapis.com/cost by service
  - Condition: Anthropic + Vertex AI > $500
  - Action: Email to team lead + Slack
  - Action: 스프레드시트 자동 업데이트

ALARM 6: 일일 증분 미실행 (Cloud Scheduler)
  - Metric: cloud_scheduler.job.execution_count
  - Condition: == 0 for incremental job
  - Action: Email + Slack
  - Runbook: 04-missing-daily-increment.md

ALARM 7: 파싱 실패율 > 5% (WARNING) / > 10% (CRITICAL)
  - Metric: custom.googleapis.com/parsing/failure_rate
  - Condition: WARNING at 5%, CRITICAL at 10%
  - Action: WARNING → Slack, CRITICAL → PagerDuty
  - Investigation: Q4 쿼리로 원인 파악

ALARM 8: Chunk 처리 72시간 초과
  - Metric: custom.googleapis.com/chunk/processing_duration_hours
  - Condition: percentile(p95) > 72
  - Action: Email
  - Investigation: Q2 쿼리 (batch 상태)

ALARM 9: 크롤링 성공률 < 70%
  - Metric: custom.googleapis.com/crawl/success_rate
  - Condition: < 70% in last 7d
  - Action: Slack
  - Investigation: Q3 쿼리

ALARM 10: Neo4j 백업 실패
  - Metric: custom.googleapis.com/neo4j/backup_success
  - Condition: == 0 (failure)
  - Action: Slack + Email
  - Runbook: 05-neo4j-backup-failure.md
```

#### 2.2.2 추가 BigQuery Saved Queries (6종)

**Q6: 일일 처리 현황 (대시보드용)**

```sql
-- Purpose: Executive summary 대시보드 (매일 9AM 자동 실행)
SELECT
  CURRENT_DATE() as report_date,
  (SELECT COUNT(*) FROM `project.dataset.candidate_context` WHERE DATE(created_at) = CURRENT_DATE()) as candidates_processed,
  (SELECT COUNT(*) FROM `project.dataset.batch_api_logs` WHERE DATE(created_at) = CURRENT_DATE()) as batch_jobs_run,
  (SELECT COUNT(*) FROM `project.dataset.crawl_logs` WHERE DATE(crawl_start) = CURRENT_DATE() AND status = 'SUCCESS') as successful_crawls,
  (SELECT ROUND(AVG(CAST(size_mb AS FLOAT64)), 2) FROM `project.dataset.file_uploads` WHERE DATE(uploaded_at) = CURRENT_DATE()) as avg_file_size_mb,
  (SELECT ROUND(SUM(cost_usd), 2) FROM `project.dataset.cost_tracker` WHERE DATE(cost_date) = CURRENT_DATE()) as daily_cost_usd;
```

**Q7: Chunk 진행률 (Phase 2)**

```sql
-- Purpose: 파일 파싱 후 chunk 생성 진행률
SELECT
  candidate_id,
  file_name,
  parse_status,
  chunk_count,
  embedding_count,
  CASE
    WHEN embedding_count = 0 THEN 'PARSED_NOT_CHUNKED'
    WHEN embedding_count < chunk_count THEN 'PARTIAL_EMBEDDED'
    WHEN embedding_count = chunk_count THEN 'FULLY_EMBEDDED'
  END as progress_stage,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), updated_at, HOUR) as hours_since_update
FROM `project.dataset.file_processing`
WHERE status IN ('PROCESSING', 'PENDING_EMBEDDING')
  AND updated_at <= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
ORDER BY updated_at ASC;
```

**Q8: Batch API 추적 (Phase 1~4)**

```sql
-- Purpose: 모든 Batch job의 생명주기 추적
SELECT
  batch_job_id,
  batch_type,
  created_at,
  submitted_at,
  result_received_at,
  TIMESTAMP_DIFF(submitted_at, created_at, MINUTE) as prep_time_minutes,
  TIMESTAMP_DIFF(result_received_at, submitted_at, MINUTE) as processing_time_minutes,
  CASE
    WHEN result_received_at IS NULL THEN 'IN_PROGRESS'
    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), result_received_at, HOUR) < 72 THEN 'RESULT_AVAILABLE'
    ELSE 'RESULT_EXPIRED'
  END as result_status,
  COUNT(*) as item_count
FROM `project.dataset.batch_api_logs`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY batch_job_id, batch_type, created_at, submitted_at, result_received_at
ORDER BY created_at DESC;
```

**Q9: 만료 위험 Batch (일일 자동)**

```sql
-- Purpose: Batch API 만료 임박 알림 (매일 6AM UTC)
-- Scheduled Query 설정:
--   Schedule: Daily 6:00 UTC
--   Destination: alerts.batch_expiration_daily
--   Write disposition: WRITE_TRUNCATE
SELECT
  batch_job_id,
  batch_type,
  created_at,
  result_expires_at,
  TIMESTAMP_DIFF(result_expires_at, CURRENT_TIMESTAMP(), HOUR) as hours_remaining,
  COUNT(*) as items_pending,
  'ACTION_REQUIRED' as alert_status,
  CONCAT('https://console.cloud.google.com/vertex-ai/batch-predictions/', batch_job_id) as gcp_link
FROM `project.dataset.batch_api_logs`
WHERE
  result_expires_at > CURRENT_TIMESTAMP()
  AND TIMESTAMP_DIFF(result_expires_at, CURRENT_TIMESTAMP(), HOUR) BETWEEN 48 AND 72
  AND status NOT IN ('COMPLETED', 'FAILED', 'ARCHIVED')
GROUP BY batch_job_id, batch_type, created_at, result_expires_at
ORDER BY hours_remaining ASC;
```

**Q10: 피처 활성화 비율 (Phase 3)**

```sql
-- Purpose: 매칭 로직별 사용 비율
SELECT
  feature_name,
  COUNT(*) as usage_count,
  COUNT(DISTINCT candidate_id) as unique_candidates,
  ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM `project.dataset.matching_features`), 2) as usage_percentage,
  AVG(confidence_score) as avg_confidence,
  MIN(first_used_at) as first_usage,
  MAX(last_used_at) as last_usage
FROM `project.dataset.matching_features`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY feature_name
ORDER BY usage_count DESC;
```

**Q11: 크롤링 성공률 (Phase 4)**

```sql
-- Purpose: 장기 크롤링 성공률 추적 (주간 + 월간)
SELECT
  DATE_TRUNC(crawl_start, WEEK) as week,
  crawl_source,
  COUNT(*) as total_urls,
  COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as success_count,
  ROUND(100 * COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) / COUNT(*), 2) as success_rate,
  COUNT(CASE WHEN status = 'TIMEOUT' THEN 1 END) as timeout_count,
  COUNT(CASE WHEN status = 'BLOCKED' THEN 1 END) as blocked_count,
  AVG(CASE WHEN status = 'SUCCESS' THEN response_time_ms END) as avg_success_time_ms
FROM `project.dataset.crawl_logs`
WHERE crawl_start >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 12 WEEK)
GROUP BY week, crawl_source
ORDER BY week DESC, success_rate DESC;
```

#### 2.2.3 Slack Webhook 통합

```bash
#!/bin/bash
# post_alert_to_slack.sh - BigQuery 쿼리 결과를 Slack으로 전송

WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
QUERY_FILE="$1"  # BigQuery SQL 파일
CHANNEL="#ml-alerts"

# BigQuery 실행
RESULT=$(bq query --use_legacy_sql=false --format=json < "$QUERY_FILE")

# JSON 포맷 슬랙 메시지
PAYLOAD=$(cat <<EOF
{
  "channel": "$CHANNEL",
  "username": "GraphRAG Monitor",
  "icon_emoji": ":bar_chart:",
  "attachments": [
    {
      "color": "danger",
      "title": "Batch API Expiration Alert",
      "text": "Results expiring within 48-72 hours",
      "fields": [
        {
          "title": "Job ID",
          "value": "$(echo $RESULT | jq -r '.[0].batch_job_id')",
          "short": true
        },
        {
          "title": "Hours Remaining",
          "value": "$(echo $RESULT | jq -r '.[0].hours_remaining')",
          "short": true
        }
      ],
      "ts": $(date +%s)
    }
  ]
}
EOF
)

curl -X POST -H 'Content-type: application/json' --data "$PAYLOAD" "$WEBHOOK_URL"
```

### 2.3 CRITICAL 알림 대응 절차 (Runbook)

#### Runbook 01: Cloud Run Job 연속 실패

**파일**: `docs/runbooks/01-cloud-run-job-failure.md`

```markdown
# Cloud Run Job 연속 3회 실패 대응

## 1. 즉시 조치 (첫 5분)

### 1.1 현황 파악
\`\`\`bash
# 최근 job 실행 로그 확인
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=kg-pipeline" \
  --limit=50 --format=json | jq '.[] | {timestamp, severity, textPayload}'

# Job 상태 확인
gcloud run jobs describe kg-pipeline --region asia-northeast3
\`\`\`

### 1.2 원인 분류
- **메모리 부족**: 로그에 "OOM killed" 또는 "Out of memory"
- **Network 연결 실패**: "Connection refused" 또는 "Timeout"
- **Secret 로드 실패**: "Permission denied" for Secret Manager
- **GCS 접근 실패**: "Access Denied" for bucket

### 1.3 대응 (원인별)

**경우 A: 메모리 부족**
\`\`\`bash
# 현재 메모리 설정 확인
gcloud run jobs describe kg-pipeline --region asia-northeast3 | grep -A5 "containers"

# 메모리 증설 (512MB → 1GB)
gcloud run jobs update kg-pipeline \
  --memory=1Gi \
  --region asia-northeast3

# 다시 실행
gcloud run jobs execute kg-pipeline --region asia-northeast3
\`\`\`

**경우 B: Neo4j 연결 실패**
\`\`\`bash
# Neo4j URI 확인
gcloud secrets versions access latest --secret=neo4j-uri

# 연결 테스트 (cloud shell)
curl -u neo4j:PASSWORD https://neo4j-uri:7687/
# 또는 python
python3 -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://...'); driver.verify_connectivity(); print('OK')"
\`\`\`

**경우 C: Secret Manager 권한 실패**
\`\`\`bash
# Service Account 확인
gcloud run jobs describe kg-pipeline --format="value(serviceAccountEmail)"

# 필요한 역할 확인
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:serviceAccount:kg-pipeline@*"

# 권한 추가 (필요시)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:kg-pipeline@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
\`\`\`

## 2. 복구 단계 (5~15분)

1. 근본 원인 고정 (코드/설정)
2. Docker 이미지 재빌드 (필요시)
3. Job 수동 실행
4. 다음 스케줄 확인

## 3. 사후 조치 (15~30분)

- CloudSQL 로그 내보내기 (분석용)
- 팀에 사건 보고 (Slack #incidents)
- 근본 원인 분석 문서 작성
\`\`\`

#### Runbook 02: Neo4j 연결 실패

**파일**: `docs/runbooks/02-neo4j-connection-failure.md`

```markdown
# Neo4j 연결 실패 대응

## 1. 원인 분류

### 1.1 Neo4j AuraDB 상태 확인
\`\`\`bash
# AuraDB console에서 확인
# https://console.aura.neo4j.io/
# Instance 상태: Running / Paused / Failed 확인

# 또는 gcloud에서 (커스텀 모니터링)
curl -s https://your-neo4j-instance.databases.neo4j.io/ | head -20
\`\`\`

### 1.2 방화벽 / IP 화이트리스트
\`\`\`bash
# Cloud Run 아웃바운드 IP 확인
# AuraDB IP 화이트리스트에 추가: 0.0.0.0/0 또는 Cloud Run 동적 IP

# Neo4j 연결 테스트
gcloud run jobs execute kg-pipeline \
  --image gcr.io/PROJECT/kg-pipeline:test \
  --command python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://...', auth=('neo4j', 'password'))
print('Connection OK')
driver.close()
"
\`\`\`

## 2. 복구 프로세스

- 인스턴스 재시작 (AuraDB console)
- 또는 새 인스턴스 생성 + 백업 복구
- 데이터 동기화 확인

## 3. 모니터링
- 매시간 헬스 체크 쿼리 실행
- Dead-letter queue 활성화
\`\`\`

#### Runbook 03: Batch API 결과 만료

**파일**: `docs/runbooks/03-batch-api-expiration.md`

```markdown
# Batch API 결과 72시간 만료 경고

## 1. 발견 시점
- Cloud Monitoring 알림: 48~72시간 이내 결과 만료
- BigQuery Q5 쿼리 실행: 일일 06:00 UTC

## 2. 즉시 조치

### 2.1 결과 다운로드
\`\`\`bash
BATCH_JOB_ID="your-batch-job-id"
GCS_OUTPUT="gs://your-bucket/results/$BATCH_JOB_ID/"

# 결과 다운로드
gsutil -m cp -r "$GCS_OUTPUT" ./batch_results/

# BigQuery에 임포트 (영구 보관)
bq load --source_format=JSONL \
  project.dataset.batch_results_archive \
  ./batch_results/*.jsonl
\`\`\`

### 2.2 처리 상태 확인
\`\`\`sql
SELECT
  batch_job_id,
  COUNT(CASE WHEN processed = true THEN 1 END) as processed_count,
  COUNT(CASE WHEN processed = false THEN 1 END) as pending_count
FROM \`project.dataset.batch_api_logs\`
WHERE batch_job_id = 'YOUR_BATCH_JOB_ID'
GROUP BY batch_job_id;
\`\`\`

## 3. 복구
- 미처리 항목만 재실행 (deduplicate 체크)
- 만료된 결과는 로컬 백업에서 복구
\`\`\`

#### Runbook 04: 일일 증분 미실행

**파일**: `docs/runbooks/04-missing-daily-increment.md`

```markdown
# Cloud Scheduler 일일 증분 job 미실행

## 1. 상태 확인
\`\`\`bash
gcloud scheduler jobs describe daily-increment-job --location asia-northeast3

# 최근 실행 로그
gcloud logging read \
  "resource.type=cloud_scheduler_job AND resource.labels.job_id=daily-increment-job" \
  --limit=10 --format=json
\`\`\`

## 2. 원인 파악
- Job 비활성화 확인
- 스케줄 표현식 검증 (cron)
- Cloud Functions 배포 상태 확인

## 3. 복구
\`\`\`bash
# Job 활성화
gcloud scheduler jobs resume daily-increment-job --location asia-northeast3

# 수동 실행 (테스트)
gcloud scheduler jobs execute daily-increment-job --location asia-northeast3
\`\`\`
\`\`\`

#### Runbook 05: Neo4j 백업 실패

**파일**: `docs/runbooks/05-neo4j-backup-failure.md`

```markdown
# Neo4j 백업 실패 대응

## 1. 백업 방식 (Phase 4~)

### 1.1 APOC Export (주간)
\`\`\`cypher
-- neo4j-admin command (SSH to AuraDB)
CALL apoc.export.json.all('gs://your-bucket/neo4j-backup-' + date() + '.json', {})
YIELD file, batches, nodes, relationships, properties, time
RETURN file, batches, nodes, relationships, properties, time;
\`\`\`

### 1.2 GCS 오브젝트 버전 관리
\`\`\`bash
# 버전 관리 활성화
gsutil versioning set on gs://your-bucket

# 최근 버전 확인
gsutil ls -L gs://your-bucket/neo4j-backup-*.json
\`\`\`

## 2. 복구
\`\`\`bash
# 최신 백업에서 복구
gsutil cp gs://your-bucket/neo4j-backup-latest.json ./

# 새 인스턴스에 임포트
CALL apoc.import.json('./neo4j-backup-latest.json');
\`\`\`
\`\`\`

---

## 3. 보안 설계

### 3.1 Secret Manager 관리

| 비밀 | 용도 | 회전 주기 | 비고 |
|---|---|---|---|
| `anthropic-api-key` | Batch + API 호출 | 3개월 | Rotation policy 설정 |
| `neo4j-uri` | Connection string | 변경 시 | 암호화 저장 |
| `neo4j-password` | 인증 | 6개월 | Strong password (32자) |
| `gcs-service-account-key` | GCS 접근 | 1년 | JSON key, 백업 보관 |
| `crawler-cookies` | 크롤링 인증 (Phase 4) | 월 1회 | 자동화 불가 |
| `naver-api-key` | Naver 검색 | 3개월 | 필요시만 |
| `nice-api-key` | 기업정보 (Phase 3) | 6개월 | B2B 계약 기반 |

#### 3.1.1 Secret Manager 설정 스크립트

```bash
#!/bin/bash
# setup_secrets.sh - Secret Manager 초기 설정

PROJECT_ID="your-project"

# 1. Anthropic API Key
echo -n "Enter Anthropic API Key: " && read ANTHROPIC_KEY
echo -n "$ANTHROPIC_KEY" | gcloud secrets create anthropic-api-key \
  --data-file=- \
  --project=$PROJECT_ID \
  --labels=environment=production,rotation=quarterly

# 2. Neo4j 설정
echo -n "Enter Neo4j URI: " && read NEO4J_URI
echo -n "$NEO4J_URI" | gcloud secrets create neo4j-uri \
  --data-file=- \
  --project=$PROJECT_ID

echo -n "Enter Neo4j Password: " && read NEO4J_PASSWORD
echo -n "$NEO4J_PASSWORD" | gcloud secrets create neo4j-password \
  --data-file=- \
  --project=$PROJECT_ID \
  --labels=rotation=semiannual

# 3. GCS Service Account
gcloud iam service-accounts create kg-pipeline \
  --display-name="GraphRAG Pipeline Service Account"

gcloud iam service-accounts keys create ./kg-pipeline-key.json \
  --iam-account=kg-pipeline@$PROJECT_ID.iam.gserviceaccount.com

cat ./kg-pipeline-key.json | gcloud secrets create gcs-service-account-key \
  --data-file=- \
  --project=$PROJECT_ID

# 4. 권한 부여
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:kg-pipeline@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/storage.admin
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:kg-pipeline@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:kg-pipeline@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/run.admin

# 5. Rotation 정책 설정
gcloud secrets add-iam-policy-binding anthropic-api-key \
  --member=serviceAccount:kg-pipeline@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor \
  --project=$PROJECT_ID

echo "✓ All secrets configured"
```

### 3.2 PII 마스킹 전략

| Phase | 정책 | 구현 |
|---|---|---|
| Phase 0~1 | 마스킹 필수 | 이름 → `[MASKED_NAME]`, 연락처 → `[PHONE]` |
| Phase 2 | 마스킹 + 법무 검토 | 마스킹 저장 + 원본 암호화 별도 저장 |
| Phase 3~ | 마스킹 해제 옵션 | 법무 승인 시 원본 활용 |

#### 3.2.1 PII 마스킹 구현 (Python)

```python
# lib/pii_masking.py
import hashlib
import re
from typing import Dict, Any

class PIIMasker:
    """개인정보 마스킹"""

    PATTERNS = {
        'name': r'[가-힣a-zA-Z]+',
        'phone': r'\d{2,4}-?\d{3,4}-?\d{4}',
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'ssn': r'\d{6}-[1-4]\d{6}',
        'company': r'회사|Corp|Ltd|Inc'
    }

    def __init__(self, preserve_hash: bool = True):
        self.preserve_hash = preserve_hash

    def mask_text(self, text: str, pii_type: str) -> str:
        """텍스트에서 PII 마스킹"""
        if pii_type == 'name':
            # 이름: 첫글자 + [MASKED]
            return re.sub(
                self.PATTERNS['name'],
                lambda m: m.group(0)[0] + '[MASKED]' if len(m.group(0)) > 1 else '[MASKED]',
                text
            )
        elif pii_type == 'phone':
            # 전화번호: XXX-XXX-XXXX
            return re.sub(
                self.PATTERNS['phone'],
                'XXX-XXX-XXXX',
                text
            )
        elif pii_type == 'email':
            # 이메일: user@[MASKED]
            return re.sub(
                self.PATTERNS['email'],
                lambda m: m.group(0).split('@')[0][:2] + '***@[MASKED]',
                text
            )
        return text

    def mask_dict(self, data: Dict[str, Any], schema: Dict[str, str]) -> Dict[str, Any]:
        """딕셔너리의 PII 필드 마스킹"""
        masked = {}
        for key, value in data.items():
            if key in schema:
                pii_type = schema[key]
                if isinstance(value, str):
                    masked[key] = self.mask_text(value, pii_type)
                else:
                    masked[key] = value
            else:
                masked[key] = value
        return masked

    def hash_for_tracking(self, original: str) -> str:
        """추적용 해시값 생성 (암호화)"""
        if not self.preserve_hash:
            return None
        return hashlib.sha256(original.encode()).hexdigest()[:16]

# 사용 예
masker = PIIMasker()
candidate = {
    'name': '김철수',
    'phone': '010-1234-5678',
    'email': 'kim.chulsu@company.com',
    'resume_text': '김철수, 010-1234-5678로 연락주세요'
}

schema = {
    'name': 'name',
    'phone': 'phone',
    'email': 'email'
}

masked = masker.mask_dict(candidate, schema)
# {
#   'name': '김[MASKED]',
#   'phone': 'XXX-XXX-XXXX',
#   'email': 'ki***@[MASKED]',
#   'resume_text': '김[MASKED], XXX-XXX-XXXX로 연락주세요'
# }
```

### 3.3 IAM 최소 권한 정책

#### 3.3.1 Service Account: kg-pipeline

**역할**:
- `roles/storage.objectAdmin` (GCS 버킷: kg-pipeline-bucket)
- `roles/bigquery.dataEditor` (BigQuery 테이블)
- `roles/secretmanager.secretAccessor` (필요한 secrets만)
- `roles/artifactregistry.reader` (Docker 이미지)

**제외 금지**:
- Editor, Viewer (과도한 권한)
- Compute Admin, Service Account Admin

#### 3.3.2 IAM 설정 스크립트

```bash
#!/bin/bash
# setup_iam.sh - Least-privilege IAM 정책 설정

PROJECT_ID="your-project"
SA_EMAIL="kg-pipeline@$PROJECT_ID.iam.gserviceaccount.com"

# 1. Storage Bucket 권한
BUCKET="kg-pipeline-bucket"

gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/storage.objectAdmin

# 2. BigQuery 권한 (특정 데이터셋만)
DATASET="kg_pipeline"

gcloud bigquery datasets add-iam-policy-binding $DATASET \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/bigquery.dataEditor \
  --project=$PROJECT_ID

# 3. Secret Manager 권한 (특정 secrets만)
for SECRET in anthropic-api-key neo4j-uri neo4j-password gcs-service-account-key; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member=serviceAccount:$SA_EMAIL \
    --role=roles/secretmanager.secretAccessor \
    --project=$PROJECT_ID
done

# 4. Artifact Registry 권한
gcloud artifacts repositories add-iam-policy-binding kg-pipeline \
  --location asia-northeast3 \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/artifactregistry.reader \
  --project=$PROJECT_ID

echo "✓ IAM policies configured"
```

### 3.4 VPC Service Controls (선택적, 보안 강화)

```yaml
# vpc_sc_policy.yaml - VPC Service Controls 정책 (선택적)
accessLevels:
  - name: "on_corp_network"
    basic:
      conditions:
        - ipSubnetworks:
            - "YOUR_CORP_IP/24"

servicePerimeters:
  - name: "kg_pipeline_perimeter"
    title: "GraphRAG Pipeline Secure Perimeter"
    restrictedServices:
      - "storage.googleapis.com"
      - "bigquery.googleapis.com"
      - "secretmanager.googleapis.com"
    accessLevels:
      - "on_corp_network"
    ingressPolicies:
      - ingressFrom:
          sources:
            - accessLevel: "on_corp_network"
        ingressTo:
          resources:
            - "*"
```

---

## 4. 리전 선택 및 근거

### 4.1 리전별 서비스 배치

| 서비스 | 리전 | 이유 |
|---|---|---|
| **GCS (데이터)** | asia-northeast3 (서울) | 데이터 주권, 레이턴시 최소화 |
| **BigQuery** | asia-northeast3 | GCS와 동일 리전 (data egress 비용 절감) |
| **Cloud Run Jobs** | asia-northeast3 | GCS 접근 최적화 |
| **Cloud Scheduler** | asia-northeast3 | 타겟 리전과 동일 |
| **Vertex AI** | us-central1 | embedding, batch 모델 지원 리전 |
| **Neo4j AuraDB** | asia-northeast1 (도쿄) | 서울 미지원 (대체안) |
| **Document AI** | us | 한국어 OCR 지원 리전 (Phase 2) |
| **Cloud Monitoring** | Global | 자동 |

### 4.2 Egress 비용 최소화

```
GCS (서울) → BigQuery (서울) → 0 cost
GCS (서울) → Vertex AI (us-central1) → ~$0.12/GB (최소화)
Cloud Run (서울) → GCS (서울) → 0 cost
```

### 4.3 리전 장애 대응

- **Primary**: asia-northeast3 (서울)
- **Secondary (선택적)**: asia-northeast1 (도쿄)
  - Neo4j 자동 복제
  - BigQuery 스냅샷 (일일)

---

## 5. Docker 이미지 전략

### 5.1 이미지 설계

```
kg-pipeline (단일 이미지, 멀티 엔트리포인트)
├── Phase 1:
│   ├── crawl: Playwright 크롤링
│   ├── preprocess: 텍스트 청소 + 청킹
│   ├── llm: LLM 프롬프트 + Batch API
│   ├── graph: Neo4j 저장
│   └── embed: Vertex AI Embedding
├── Phase 2 (+ 추가):
│   ├── parse: PDF/DOCX/HWP (LibreOffice)
│   └── chunk: 복잡한 문서 청킹
├── Phase 3 (+ 추가):
│   ├── company_context: NICE 기업정보
│   └── mapping: 매칭 로직
└── Phase 4 (+ 추가):
    ├── homepage_crawl: 홈페이지 크롤링
    └── news_collect: 뉴스 수집

kg-crawler (별도, Playwright 전용)
├── Phase 1:
│   └── resume: 이력서 크롤링
└── Phase 4 (+ 추가):
    └── homepage: 홈페이지 크롤링

kg-postprocessor (선택, Phase 3~)
└── matching: 매칭 후처리
```

### 5.2 Dockerfile: kg-pipeline

```dockerfile
# Dockerfile.kg-pipeline
FROM python:3.11-slim

# 1. 공통 의존성
RUN apt-get update && apt-get install -y \
    curl wget git \
    && rm -rf /var/lib/apt/lists/*

# 2. Phase 1 의존성
RUN pip install --no-cache-dir \
    neo4j==5.15.0 \
    google-cloud-storage==2.10.0 \
    google-cloud-bigquery==3.13.0 \
    google-cloud-secret-manager==2.16.0 \
    anthropic==0.7.0 \
    beautifulsoup4==4.12.0 \
    requests==2.31.0

# 3. Phase 2 의존성 (LibreOffice)
ARG INSTALL_PHASE2=false
RUN if [ "$INSTALL_PHASE2" = "true" ]; then \
    apt-get update && apt-get install -y \
    libreoffice-common libreoffice-writer libreoffice-calc \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir \
    python-pptx==0.6.21 \
    pdf2image==1.16.3 \
    pytesseract==0.3.10; \
    fi

# 4. 애플리케이션 코드
WORKDIR /app
COPY ./src ./src
COPY ./lib ./lib
COPY ./config ./config
COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# 5. 헬스 체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python /app/lib/health_check.py

# 6. 엔트리포인트
ENTRYPOINT ["python", "-m", "src.main"]
CMD ["--help"]

# 빌드 커맨드
# docker build -t kg-pipeline:latest .
# docker build -t kg-pipeline:phase2 --build-arg INSTALL_PHASE2=true .
```

### 5.3 Dockerfile: kg-crawler (Playwright)

```dockerfile
# Dockerfile.kg-crawler
FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app

# 의존성
RUN pip install --no-cache-dir \
    playwright==1.40.0 \
    beautifulsoup4==4.12.0 \
    google-cloud-storage==2.10.0 \
    google-cloud-secret-manager==2.16.0 \
    requests==2.31.0

# Playwright 브라우저 설치
RUN python -m playwright install

# 애플리케이션
COPY ./src/crawlers ./src/crawlers
COPY ./lib ./lib
COPY ./config ./config

ENTRYPOINT ["python", "-m", "src.crawlers.main"]
```

### 5.4 Image Registry 관리

```bash
#!/bin/bash
# push_images.sh - Docker 이미지 빌드 및 푸시

PROJECT_ID="your-project"
REGISTRY="asia-northeast3-docker.pkg.dev"
REPO="kg-pipeline"

# 1. 이미지 빌드
docker build -t kg-pipeline:latest -f Dockerfile.kg-pipeline .
docker build -t kg-crawler:latest -f Dockerfile.kg-crawler .

# 2. 레지스트리 태그
docker tag kg-pipeline:latest \
  $REGISTRY/$PROJECT_ID/$REPO/kg-pipeline:latest
docker tag kg-crawler:latest \
  $REGISTRY/$PROJECT_ID/$REPO/kg-crawler:latest

# 3. 푸시
docker push $REGISTRY/$PROJECT_ID/$REPO/kg-pipeline:latest
docker push $REGISTRY/$PROJECT_ID/$REPO/kg-crawler:latest

# 4. 버전 태그 (Phase별)
docker tag kg-pipeline:latest \
  $REGISTRY/$PROJECT_ID/$REPO/kg-pipeline:phase2-$(date +%Y%m%d)
docker push $REGISTRY/$PROJECT_ID/$REPO/kg-pipeline:phase2-$(date +%Y%m%d)

echo "✓ Images pushed to $REGISTRY"
```

---

## 6. 백업 전략

### 6.1 서비스별 백업 정책

| 서비스 | 백업 방식 | 빈도 | 보관 기간 | 복구 시간 |
|---|---|---|---|---|
| **GCS 데이터** | Object Versioning | 전 버전 | 무제한 | 즉시 |
| **GCS (의존성 정책)** | 1개월 이상 보관 | - | 30일 | 즉시 |
| **BigQuery** | Time-travel (Table Snapshot) | 자동 | 7일 | < 1분 |
| **BigQuery (장기)** | Export to GCS | 주 1회 | 1년 | 몇 분 |
| **Neo4j 그래프** | APOC Export (JSON) | 주 1회 | 4주 | 몇 시간 |
| **Neo4j (Full Backup)** | Aura Backup API | 월 1회 | 3개월 | 몇 시간 |
| **Secrets** | 설정 파일 백업 | 변경 시 | 무제한 | 즉시 |

### 6.2 GCS Object Versioning

```bash
#!/bin/bash
# setup_gcs_versioning.sh - GCS 버전 관리 설정

BUCKET="kg-pipeline-data"

# 1. Versioning 활성화
gsutil versioning set on gs://$BUCKET

# 2. Lifecycle 정책 (이전 버전 30일 후 삭제)
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "isLive": false,
          "numNewerVersions": 10
        }
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {
          "isLive": false,
          "numNewerVersions": 5
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://$BUCKET

# 3. 버전 조회
gsutil ls -L gs://$BUCKET/candidate_context/

echo "✓ GCS versioning configured"
```

### 6.3 BigQuery Snapshot & Export

```bash
#!/bin/bash
# backup_bigquery.sh - BigQuery 스냅샷 + 내보내기 (주간)

PROJECT_ID="your-project"
DATASET="kg_pipeline"
BACKUP_BUCKET="gs://kg-pipeline-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 1. 모든 테이블 스냅샷 생성
for TABLE in candidate_context batch_api_logs crawl_logs file_processing; do
  bq cp \
    $PROJECT_ID:$DATASET.$TABLE \
    $PROJECT_ID:${DATASET}_snapshot_${TIMESTAMP}.$TABLE \
    --no_clobber
done

# 2. GCS로 내보내기 (Parquet)
for TABLE in candidate_context batch_api_logs crawl_logs; do
  bq extract \
    --destination_format=PARQUET \
    --compression=SNAPPY \
    $PROJECT_ID:$DATASET.$TABLE \
    "$BACKUP_BUCKET/bigquery_export/${TIMESTAMP}/${TABLE}/*.parquet"
done

# 3. 오래된 스냅샷 정리 (30일 이상)
for SNAPSHOT_DATASET in $(bq ls -d | grep "${DATASET}_snapshot_"); do
  SNAPSHOT_DATE=$(echo $SNAPSHOT_DATASET | sed "s/${DATASET}_snapshot_//")
  if (( $(date +%s) - $(date -d "$SNAPSHOT_DATE" +%s) > 2592000 )); then
    bq rm -d -f $SNAPSHOT_DATASET
  fi
done

echo "✓ BigQuery backup completed: $TIMESTAMP"
```

### 6.4 Neo4j Export (APOC)

```cypher
-- neo4j_backup.cypher - Neo4j APOC export (Phase 2~)
-- 실행: 주간 (Kubernetes CronJob 또는 Cloud Scheduler)

// 1. 전체 그래프 내보내기
CALL apoc.export.json.all(
  'gs://kg-pipeline-backups/neo4j-export-' + date() + '.json',
  {
    useTypes: true,
    streamBatchSize: 5000
  }
)
YIELD file, batches, nodes, relationships, properties, time
RETURN file, batches, nodes, relationships, properties, time;

// 2. 메타데이터 내보내기
MATCH (n)
WITH COUNT(n) as node_count
MATCH ()-[r]->()
WITH node_count, COUNT(r) as rel_count
CALL apoc.create.node(
  ['GraphMetadata'],
  {
    export_date: date(),
    node_count: node_count,
    relationship_count: rel_count
  }
)
YIELD node
RETURN node;

// 3. 복구 스크립트
// CALL apoc.import.json('gs://kg-pipeline-backups/neo4j-export-YYYY-MM-DD.json')
```

### 6.5 복구 절차 (Runbook)

```markdown
# 데이터 복구 절차

## 1. GCS 복구 (파일 실수 삭제)

\`\`\`bash
# 최근 버전 확인
gsutil ls -L gs://kg-pipeline-data/candidate_context/ | head -5

# 특정 버전에서 복구
VERSION_ID="1234567890" # gsutil ls -L에서 확인
gsutil cp gs://kg-pipeline-data/candidate_context#${VERSION_ID} ./recovered.json
\`\`\`

## 2. BigQuery 복구 (데이터 손상)

\`\`\`sql
-- Time-travel 쿼리 (최대 7일 이전)
SELECT * FROM \`project.dataset.candidate_context\`
FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 DAY);

-- 스냅샷에서 복구
CREATE OR REPLACE TABLE \`project.dataset.candidate_context\` AS
SELECT * FROM \`project.dataset.candidate_context_snapshot_20240115\`;
\`\`\`

## 3. Neo4j 복구 (그래프 손상)

\`\`\`bash
# 1. 백업에서 복구
gsutil cp gs://kg-pipeline-backups/neo4j-export-2024-01-15.json ./

# 2. 새 인스턴스 생성 (AuraDB)
# AuraDB Console에서 수동 생성

# 3. 데이터 임포트
# Neo4j Browser에서:
CALL apoc.import.json('file:///neo4j-export-2024-01-15.json')
\`\`\`
\`\`\`

---

## 7. 비용 모니터링 대시보드

### 7.1 BigQuery 비용 추적 테이블

```sql
-- CREATE TABLE을 실행하여 비용 추적 테이블 생성
CREATE TABLE IF NOT EXISTS `project.dataset.cost_tracker` (
  cost_id STRING NOT NULL,
  cost_date DATE NOT NULL,
  service STRING NOT NULL,
  resource_type STRING,
  usage_amount FLOAT64,
  unit STRING,
  unit_cost FLOAT64,
  cost_usd FLOAT64,
  cost_krw INT64,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  PRIMARY KEY (cost_id)
)
PARTITION BY cost_date
CLUSTER BY service, resource_type;

-- 일일 비용 집계 쿼리
SELECT
  cost_date,
  service,
  ROUND(SUM(cost_usd), 2) as daily_cost_usd,
  ROUND(SUM(cost_usd) * 1300, 0) as daily_cost_krw,
  COUNT(DISTINCT resource_type) as resource_count
FROM `project.dataset.cost_tracker`
WHERE cost_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY cost_date, service
ORDER BY cost_date DESC, service;
```

### 7.2 비용 예산 알림

```bash
#!/bin/bash
# setup_budget_alerts.sh - GCP 예산 알림 설정

PROJECT_ID="your-project"
BILLING_ACCOUNT_ID="your-billing-account-id"
BUDGET_NAME="kg-pipeline-monthly"
BUDGET_AMOUNT=500  # USD/month

# Budget 생성
gcloud billing budgets create \
  --billing-account=$BILLING_ACCOUNT_ID \
  --display-name=$BUDGET_NAME \
  --budget-amount=$BUDGET_AMOUNT \
  --threshold-rule=percent=50,spend-basis=current-spend \
  --threshold-rule=percent=90,spend-basis=current-spend \
  --threshold-rule=percent=100,spend-basis=current-spend \
  --enable-project-level-recipients \
  --projects=$PROJECT_ID

# 알림 수신 설정 (이메일 또는 PubSub)
# GCP Console > Billing > Budgets에서 수신자 추가
```

### 7.3 월간 비용 리포트 (자동화)

```python
# lib/cost_report.py - 월간 비용 리포트 생성
from google.cloud import bigquery
from datetime import datetime, timedelta
import json

class CostReporter:
    def __init__(self, project_id):
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id

    def generate_monthly_report(self, year: int, month: int):
        """월간 비용 리포트 생성"""
        query = f"""
        SELECT
          service,
          SUM(cost_usd) as total_cost_usd,
          COUNT(DISTINCT cost_date) as active_days,
          ROUND(AVG(cost_usd), 2) as avg_daily_cost,
          MAX(cost_usd) as peak_daily_cost
        FROM `{self.project_id}.dataset.cost_tracker`
        WHERE EXTRACT(YEAR FROM cost_date) = {year}
          AND EXTRACT(MONTH FROM cost_date) = {month}
        GROUP BY service
        ORDER BY total_cost_usd DESC;
        """

        result = self.client.query(query).to_dataframe()

        # 리포트 생성
        report = {
            "report_period": f"{year}-{month:02d}",
            "total_cost_usd": result['total_cost_usd'].sum(),
            "total_cost_krw": result['total_cost_usd'].sum() * 1300,
            "by_service": result.to_dict('records'),
            "generated_at": datetime.now().isoformat()
        }

        return report

    def send_report_to_slack(self, report: dict, webhook_url: str):
        """Slack으로 리포트 전송"""
        import requests

        payload = {
            "text": f"GraphRAG Monthly Cost Report: {report['report_period']}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Monthly Cost Summary*\n"
                                f"Total: ${report['total_cost_usd']:.2f} (~₩{report['total_cost_krw']:,})"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*By Service*\n" +
                                "\n".join([
                                    f"• {item['service']}: ${item['total_cost_usd']:.2f}"
                                    for item in report['by_service']
                                ])
                    }
                }
            ]
        }

        requests.post(webhook_url, json=payload)

# 실행
if __name__ == "__main__":
    reporter = CostReporter("your-project")
    report = reporter.generate_monthly_report(2024, 1)

    # Slack 전송 (필요시)
    # reporter.send_report_to_slack(report, "YOUR_SLACK_WEBHOOK_URL")

    print(json.dumps(report, indent=2))
```

---

## 8. 요약 및 의사결정

### 8.1 Cost vs Quality 트레이드오프

| 선택 | 총비용 | 품질 | 권장 |
|---|---|---|---|
| **Haiku Batch** | ~$8,024~8,774 | 중상 (튜닝 필요) | ✓ 초기 단계 |
| **Sonnet Batch** | ~$8,576~9,326 | 상 (최소 튜닝) | Phase 2~ |

### 8.2 리스크 및 완화

| 리스크 | 영향 | 완화 전략 |
|---|---|---|
| Batch API 결과 만료 | 데이터 손실 | 자동 다운로드 + GCS 버전 관리 |
| LLM 비용 초과 | 예산 증가 | Budget alert + 사용량 제한 |
| Neo4j 장애 | 매칭 불가 | 주간 백업 + 도쿄 리전 재해 복구 |
| 크롤링 블로킹 | 데이터 부족 | User-Agent 로테이션, 프록시 |
| PII 유출 | 법적 문제 | 마스킹 + VPC Service Controls |

### 8.3 다음 단계

1. **Phase 0**: 실제 PoC 실행 → 비용 재검증
2. **Phase 1**: 모니터링 대시보드 설정 (3개 alarms)
3. **Phase 2**: BigQuery Saved Queries 배포, 자동 알림 활성화
4. **Phase 3~4**: 확장 모니터링 추가, Gold Label 검수자 계약
5. **운영**: 월간 비용 리포트 자동화, 예산 최적화

---

## 부록

### A. 참조 문서

- GCP Pricing: https://cloud.google.com/pricing
- Neo4j AuraDB: https://neo4j.com/cloud/aura/
- Anthropic API Pricing: https://www.anthropic.com/pricing
- BigQuery Monitoring: https://cloud.google.com/bigquery/docs/monitoring

### B. 용어 정의

| 용어 | 정의 |
|---|---|
| **Batch API** | 비동기 대량 처리 API (결과 72시간 보관) |
| **Dead-letter** | 처리 실패한 이벤트 (재처리 대기열) |
| **APOC** | Neo4j의 쿼리 절차형 라이브러리 |
| **PII** | 개인식별정보 (이름, 연락처, SSN 등) |
| **TTL** | Time-To-Live (데이터 만료 시간) |
| **Egress** | 데이터 센터에서 나가는 트래픽 |

---

**작성일**: 2024년
**최종 수정**: 2024년
**담당**: Infrastructure Team
