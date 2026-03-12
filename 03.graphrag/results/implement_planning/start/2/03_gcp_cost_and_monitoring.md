# GCP 비용 추정 + 모니터링 구성

> v7 파이프라인의 GCP 인프라 비용, LLM/Embedding 비용, 모니터링 구성.
>
> 작성일: 2026-03-08

---

## 1. 비용 추정

### 1.1 Phase 0: PoC (3~4주)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| Cloud Run Jobs | PoC 50건 파싱 + 추출 | ~$5 |
| GCS | 150GB 원본 업로드 + 1GB 파싱 결과 | ~$5 |
| BigQuery | 10MB 이하 | ~$0 (Free tier) |
| Neo4j AuraDB Free | 200K 노드 | $0 |
| Secret Manager | 6개 시크릿 | ~$0 |
| Anthropic API (PoC) | 50건 × 3모델 비교 (일반 API) | ~$20 |
| Vertex AI Embedding (PoC) | 20쌍 검증 | ~$10 |
| **Phase 0 합계** | | **~$40** |

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

### 1.3 Phase 2: 전체 처리 (4~5주)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| **Anthropic Batch API (CandidateContext)** | 500K 이력서 × $0.00115/건 | **$575** |
| **Anthropic Batch API (CompanyContext)** | 10K JD × $0.0004/건 | **$4** |
| **Vertex AI Embedding** | 302M 토큰 × $0.0065/1M | **$2** |
| Cloud Run Jobs (전체) | ~500시간 (전 Job 합산) | **$150** |
| GCS | 150GB 원본 + 50GB 결과 | **$8/월** |
| BigQuery | 10GB 서빙 테이블 + 쿼리 | **$10/월** |
| Neo4j AuraDB Professional | 800K~8M 노드 전환 | **$100~200/월** |
| Cloud Workflows | 실행 횟수 | ~$1 |
| Cloud Monitoring / Logging | 기본 | ~$10/월 |
| Silver Label (PoC, Sonnet) | 2,000건 × $0.01 | **$20** |
| 프롬프트 최적화 LLM (Sonnet) | ~500건 | **~$600** |
| **Phase 2 LLM 합계** | | **~$1,201** |
| **Phase 2 인프라/월** | | **~$130/월** |

### 1.4 시나리오별 총비용 (GCP 인프라 포함)

| 시나리오 | LLM 비용 | GCP 인프라 (Phase 0~2) | Gold Label 인건비 | 총비용 | 원화 |
|---|---|---|---|---|---|
| **A: Haiku Batch (권장)** | $1,211 | ~$700 | $5,840 | **~$7,751** | **~1,062만** |
| **A': Haiku→Sonnet Fallback (v7)** | $3,522 | ~$700 | $5,840 | **~$10,062** | **~1,378만** |
| B: Sonnet Batch | $3,340 | ~$700 | $5,840 | $9,880 | ~1,353만 |
| C: On-premise (GPU) | $9,254 | ~$2,500 (GPU 포함) | $5,840 | $17,594 | ~2,410만 |
| D: Gemini Flash | $942 | ~$700 | $5,840 | $7,482 | ~1,025만 |

> **v7 GCP 계획 vs v5 원본 비용 비교**: GCP 인프라 비용이 v5 추정보다 약 $1,460 절감.
> - 오케스트레이션: Prefect/외부 $600/년 → Cloud Workflows ~$12/년
> - BigQuery: 외부 추정 $360/년 → GCP 네이티브 $120/년
> - Cloud Run Jobs: 실행 시간 과금 → 상시 인프라 대비 저렴

### 1.5 운영 단계 (월간)

| 서비스 | 사용량 | 월 비용 |
|---|---|---|
| Neo4j AuraDB Professional | 800만 노드 유지 | $100~200 |
| GCS | 200GB | $5 |
| BigQuery | 10GB + 쿼리 | $10 |
| Cloud Run Jobs (증분) | 일 1,000건 × 30일 | $10 |
| Anthropic API (증분) | 일 1,000건 × $0.00115 | $35 |
| Vertex AI Embedding (증분) | 일 1,000건 | ~$0.01 |
| Cloud Scheduler + Workflows | 일 2회 | ~$1 |
| Monitoring / Logging | 기본 | $10 |
| **운영 월 합계** | | **~$170~270/월** |

### 1.6 Phase 3: 크롤링 파이프라인 (추가)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| Cloud Run (홈페이지 크롤러) | Playwright, ~67배치 | ~$15 |
| Cloud Run (뉴스 수집기) | API + 본문 크롤링 | ~$5 |
| Cloud Run (LLM 추출) | Gemini Flash | ~$10 |
| Gemini API (추출) | 1,000기업 × ~15건 | ~$5 |
| 네이버 뉴스 API | 무료 | $0 |
| **Phase 3 합계** | | **~$35** |

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
  COUNTIF(status = 'SKIPPED') AS skip_count,
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
  ROUND(COUNTIF(status = 'COMPLETED') / COUNT(*) * 100, 1) AS completion_pct,
  -- 예상 완료 시간
  CASE
    WHEN COUNTIF(status = 'COMPLETED') > 0 THEN
      TIMESTAMP_ADD(
        MIN(CASE WHEN status = 'COMPLETED' THEN start_time END),
        INTERVAL CAST(
          TIMESTAMP_DIFF(MAX(end_time), MIN(start_time), SECOND)
          / COUNTIF(status = 'COMPLETED') * COUNT(*)
          AS INT64
        ) SECOND
      )
    ELSE NULL
  END AS estimated_completion
FROM graphrag_kg.chunk_status
GROUP BY pipeline;

-- LLM 파싱 실패 모니터링 (v7)
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
| 파싱 실패율 > 5% (v7) | Slack (WARNING) | 1시간 내 |
| 파싱 실패율 > 10% (v7) | Slack + Email (CRITICAL) | 즉시 |
| Chunk 처리 72시간 초과 PROCESSING | Email | 일일 체크 |

```bash
# 알림 정책 생성 예시
gcloud alpha monitoring policies create \
  --display-name="KG Pipeline Job Failure" \
  --condition-display-name="Cloud Run Job Failed" \
  --condition-filter='resource.type="cloud_run_job" AND metric.type="run.googleapis.com/job/completed_task_attempt_count" AND metric.labels.result="failed"' \
  --condition-threshold-value=1 \
  --condition-threshold-comparison=COMPARISON_GT \
  --notification-channels=$SLACK_CHANNEL_ID
```

### 2.3 Looker Studio 대시보드 구성

| 패널 | 데이터 소스 | 시각화 |
|---|---|---|
| 파이프라인 진행률 | `chunk_status` | 스택 바 차트 (PENDING/PROCESSING/COMPLETED/FAILED) |
| 에러율 추이 | `processing_log` | 시계열 (파이프라인별 에러율) |
| LLM 비용 추적 | `processing_log` | 누적 비용 시계열 |
| 파싱 실패 분포 (v7) | `parse_failure_log` | 파이 차트 (tier별 비율) |
| 피처 활성화 현황 | `mapping_features` | 히트맵 (피처별 ACTIVE/INACTIVE) |
| Neo4j 적재 현황 | `processing_log` (graph_load) | 카운터 (노드/엣지 수) |

---

## 3. 인프라 셋업 절차 요약

### 3.1 빠른 시작 (30분)

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

# 6. Neo4j AuraDB Free → Console에서 생성
# → URI/인증정보를 Secret Manager에 저장

# 7. 첫 번째 Cloud Run Job 배포 + 실행
IMAGE=asia-northeast3-docker.pkg.dev/graphrag-kg/kg-pipeline/kg-pipeline:latest
gcloud run jobs create kg-parse-poc \
  --image=$IMAGE --tasks=1 --cpu=2 --memory=4Gi \
  --region=asia-northeast3
gcloud run jobs execute kg-parse-poc --region=asia-northeast3
```

### 3.2 Docker 이미지 빌드

```dockerfile
# Dockerfile
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

# 엔트리포인트는 Job별로 --command 옵션으로 지정
CMD ["python", "src/main.py"]
```

```
# requirements.txt
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
readability-lxml>=0.8.1
beautifulsoup4>=4.12.0
```

---

## 4. v7 계획 대비 GCP 특이사항

| v7 설계 | GCP 구현 | 비고 |
|---|---|---|
| Cloud Workflows / Prefect 권장 | **Cloud Workflows 기본 + Prefect 옵션** | Phase 0-4 의사결정 |
| Anthropic Batch API (50% 할인) | **Cloud Run Job이 Batch API 제출/폴링** | task-timeout=24h 설정 |
| Vertex AI Embedding | **직접 API 호출** (us-central1) | text-multilingual-embedding-002 |
| Neo4j AuraDB | **asia-northeast1** (도쿄) | 서울 미지원, ~10ms 레이턴시 |
| Chunk 상태 추적 | **BigQuery** `chunk_status` 테이블 | Looker Studio 연동 |
| LLM 파싱 실패 3-tier (v7) | **BigQuery** `parse_failure_log` + 알림 | 5% WARNING, 10% CRITICAL |
| Dead-Letter 큐 | **GCS 파일 기반** + Cloud Scheduler | Pub/Sub 대신 단순 구조 |
| 프롬프트 버전 관리 | **GCS + Git** | GCS에 배포, Git에 원본 |
| PII 마스킹 | **Cloud Run 내 처리** → 마스킹 후 API 전송 | 법무 미확정 시 기본값 |
| 크롤링 파이프라인 (Phase 3) | **crawling-gcp-plan.md와 동일 아키텍처** | 별도 Cloud Run Jobs |
| 모니터링 (Grafana 제안) | **Looker Studio + Cloud Monitoring** | GCP 네이티브 |

---

## 5. 의사결정 포인트 요약 (GCP 영향)

| 시점 | 의사결정 | GCP 영향 |
|---|---|---|
| Pre-Phase 0 | NICE DB 접근 | Cloud Functions 구현 범위 |
| Phase 0 완료 | 오케스트레이션 도구 | Cloud Workflows YAML vs Prefect Cloud Run |
| Phase 0 완료 | LLM 모델 선택 | Batch API 모델 설정 (Haiku/Sonnet) |
| Phase 0 완료 | PII 전략 | API (Cloud Run) vs On-premise (Compute Engine GPU) |
| Phase 0 완료 | Embedding 확정 | Vertex AI 모델/리전 설정 |
| Phase 1 중간 | Neo4j 플랜 | Free → Professional 전환 |
| Phase 2 시작 | Cloud Run 스케일 | Task 수, 동시 배치 수 조정 |
| Phase 2 완료 | 운영 모드 | Cloud Scheduler 증분 주기 |
| Phase 3 시작 | 크롤링 인프라 | crawling-gcp-plan.md 별도 배포 |
