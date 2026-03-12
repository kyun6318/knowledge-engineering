# 비용 추정 + 최소 모니터링

> light.1 Staged Fast Fail의 비용 추정 + 최소한의 모니터링 구성
> standard.1 기반 한국어 토큰 보정 적용
> [standard.21] 한글 1자 ≈ 2~3 tokens으로 ×1.88배 비용 조정

---

## 1. 비용 추정

### 1.1 Phase 0: API 검증 + PoC (2.5주)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| **Vertex AI API 검증 (2일)** [standard.2] | Gemini Flash/Pro, Embedding, DocAI | **~$50** |
| Cloud Run Jobs | PoC 50건 파싱 | ~$3 |
| GCS | 150GB 원본 업로드 + 테스트 데이터 | ~$5 |
| BigQuery | 10MB 이하 | ~$0 (Free tier) |
| Neo4j AuraDB Free | 200K 노드 | $0 |
| Secret Manager | 4개 시크릿 | ~$0 |
| Anthropic API (PoC) | 50건 × 3모델 비교 | ~$20 |
| Vertex AI Embedding (PoC) | 20쌍 검증 | ~$5 |
| **Phase 0 합계** | | **~$83** |

> standard.1($95) 대비 -$12: 일정 단축 (4~5주 → 2.5주)

### 1.2 Phase 1: MVP 파이프라인 (5~6주)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| Cloud Run Jobs (파싱) | 1,000건, 2 vCPU × 4GB × ~30분 | ~$2 |
| Cloud Run Jobs (Context) | CompanyCtx 100건 + CandidateCtx 1,000건 | ~$3 |
| Cloud Run Jobs (Graph+Embedding+Mapping) | 1,000건 규모 | ~$3 |
| Anthropic API (개발+테스트) | 프롬프트 튜닝 ~3,000건 | ~$30 |
| Anthropic Batch API (MVP) | 1,000건 × $0.00300/건 [standard.21] | ~$3 |
| Vertex AI Embedding | 1,000건 | ~$0.50 |
| Neo4j AuraDB Free | 200K 노드 내 | $0 |
| BigQuery | 소량 | ~$0.50 |
| **Phase 1 합계** | | **~$42** |

> standard.1($86) 대비 -$44: 기간 단축(10~12주 → 5~6주) + 규모 축소

### 1.3 Phase 2: 전체 처리 + 품질 평가 (4~5주) — [standard.21] 한국어 토큰 보정

> **핵심 변경**: 한국어 이력서는 한글 1자 ≈ 2~3 tokens으로 토큰 효율이 낮음.
> v2 가정(영어): 평균 input 1,500 tokens → standard.1 가정(한국어 보정): 3,500 tokens 적용
> 결과: 이력서 1건당 비용 $0.00160 → **$0.00300** (×1.88배)

#### [standard.21] Anthropic Batch API 비용 비교

| 항목 | v2 가정 (영어 기준) | standard.1 가정 (한국어 보정) | 비고 |
|---|---|---|---|
| 이력서 평균 input tokens | 1,500 | 3,500 | 한글 ×2.3배 |
| 이력서 평균 output tokens | 500 | 800 | JSON 출력 (혼합) |
| Haiku Batch input 단가 | $0.40/1M | $0.40/1M | 50% 할인 적용 |
| Haiku Batch output 단가 | $2.00/1M | $2.00/1M | 50% 할인 적용 |
| **이력서 1건당 비용** | **$0.00160** | **$0.00300** | ×1.88배 |
| **500K 이력서 총비용** | **$800** | **$1,500** | light.1는 450K 사용 |

#### Phase 2 LLM 비용 상세

| 서비스 | 사용량 | 비용 |
|---|---|---|
| **Anthropic Batch API (CandidateContext)** | 450K × $0.00300/건 [standard.21] | **$1,350** |
| **Anthropic Batch API (CompanyContext)** | 10K JD × $0.0004/건 | **$4** |
| **Vertex AI Embedding** | 302M 토큰 × $0.0001/1K | **$30** |
| **Embedding Egress (서울→US)** [standard.26] | ~30GB × $0.12/GB | **$3.6** |
| Silver Label (Sonnet) | 1,000건 × $0.01 | **$10** |
| 프롬프트 최적화 LLM | ~250건 | **$300** |
| **Phase 2 LLM 합계** | | **~$1,698** |

#### [standard.26] Embedding Egress 비용 계산

```
Embedding 대상 텍스트:
  - Chapter evidence_chunk: 450K × 5.2 chapters × 평균 200자 × 3 bytes/char = ~1.4GB
  - Vacancy description: 10K × 평균 500자 × 3 bytes/char = ~15MB
  - 합계: ~1.5GB (텍스트 데이터)

GCP Egress (asia-northeast3 → us-central1):
  - 다른 대륙 간: $0.12/GB
  - 서울→US: 1.5GB × $0.12 = ~$0.18

+ Embedding API 응답 (768d float32 × 항목 수):
  - (450K × 5.2 + 10K) × 768 × 4 bytes = ~7.2GB
  - US→서울: $0.12/GB × 7.2 = ~$0.86

= 총 Egress: ~$1.04 (보수적 추정: $3.6)
```

#### Phase 2 인프라 비용 (1개월)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| Cloud Run Jobs (전체) | ~300시간 | ~$90 |
| GCS | 150GB + Versioning [standard.20] | ~$5 |
| BigQuery | + batch_tracking [standard.1-5] | ~$5 |
| Neo4j AuraDB Professional [standard.1-3] | 1개월 | $100~200 |
| **Phase 2 인프라 합계** | | **~$200** |

### 1.4 시나리오별 총비용 (light.1)

| 시나리오 | Phase 0 | Phase 1 | Phase 2 LLM | Phase 2 인프라 | Gold Label 인건비 | **총비용** | **원화** |
|---|---|---|---|---|---|---|---|
| **A: Haiku Batch (권장)** | $83 | $42 | $1,698 | ~$200 | $2,920 | **~$4,943** | **~677만** |
| A': Haiku→Sonnet Fallback | $83 | $42 | +LLM | ~$200 | $2,920 | **~$5,700** | **~780만** |
| B: Sonnet Batch | $83 | $42 | +LLM | ~$200 | $2,920 | **~$5,500** | **~753만** |
| D: Gemini Flash | $83 | $42 | 낮음 | ~$200 | $2,920 | **~$4,300** | **~589만** |

**standard.1 대비 비용 절감:**
- Gold Label: $5,840 → $2,920 (-50%)
- 크롤링 비용: $35 → $0 (제거)
- 운영 인프라: $660 → $200 (1개월만)
- Batch API: $1,500 → $1,350 (450K 중복제거, 한국어 보정 유지)
- 프롬프트 최적화: $600 → $300 (-50%)

### 1.5 Budget Alert 설정

```bash
# Phase 0: $100 경고, $150 강제 중단
# Phase 1: $50 경고, $80 강제 중단
# Phase 2: $2,000 경고, $3,000 강제 중단

gcloud billing budgets create \
  --billing-account=$BILLING_ACCOUNT \
  --display-name="GraphRAG light.1 Phase 2" \
  --budget-amount=3000 \
  --threshold-rules=percent=0.67,basis=current-spend \
  --threshold-rules=percent=1.0,basis=current-spend \
  --notifications-rule-pubsub-topic=projects/graphrag-kg/topics/budget-alert \
  --notifications-rule-monitoring-notification-channels=$CHANNEL_ID
```

---

## 2. 최소 모니터링 (light.1)

> v2의 Looker Studio + 10+ 알림 → BigQuery 직접 쿼리 + 3개 핵심 알림으로 축소

### 2.1 Cloud Monitoring 알림 (3개만)

| 조건 | 채널 | 임계값 |
|------|------|-------|
| Cloud Run Job 실패 | Slack | 즉시 |
| Dead-letter 건수 > 1,000 | Slack | 1시간 내 |
| Neo4j 연결 실패 | Slack | 즉시 |

```bash
# Cloud Run Job 실패 알림
gcloud monitoring policies create \
  --display-name="KG Job Failure" \
  --condition-display-name="Cloud Run Job Failed" \
  --condition-filter='resource.type="cloud_run_job" AND metric.type="run.googleapis.com/job/completed_task_attempt_count" AND metric.labels.result="failed"' \
  --condition-threshold-value=0 \
  --condition-comparison=COMPARISON_GT \
  --notification-channels=$SLACK_CHANNEL
```

### 2.2 BigQuery 모니터링 쿼리 (수동 실행)

```sql
-- 일일 처리 현황
SELECT
  run_date,
  pipeline,
  COUNTIF(status = 'SUCCESS') AS success,
  COUNTIF(status = 'FAILED') AS failed,
  ROUND(COUNTIF(status = 'FAILED') / COUNT(*) * 100, 2) AS error_rate,
  ROUND(SUM(input_tokens) * 0.00000040 + SUM(output_tokens) * 0.0000020, 2) AS cost_usd
FROM graphrag_kg.processing_log
WHERE run_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY run_date, pipeline
ORDER BY run_date DESC;

-- Chunk 진행률 (Phase 2)
SELECT
  pipeline,
  COUNT(*) AS total,
  COUNTIF(status = 'COMPLETED') AS done,
  COUNTIF(status = 'FAILED') AS failed,
  ROUND(COUNTIF(status = 'COMPLETED') / COUNT(*) * 100, 1) AS pct
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

-- LLM 파싱 실패 분포
SELECT
  pipeline,
  failure_tier,
  COUNT(*) AS count
FROM graphrag_kg.parse_failure_log
GROUP BY pipeline, failure_tier
ORDER BY pipeline, failure_tier;
```

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
    │   └─ 불허: 시나리오 C (On-premise GPU) 전환 → 재평가 필요
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
| `kg-pipeline` | `aiplatform.user` | Vertex AI Embedding |

### 3.3 Secret Manager 등록 대상 (light.1 축소)

| 시크릿 이름 | 용도 |
|---|---|
| `anthropic-api-key` | Claude Haiku/Sonnet API |
| `neo4j-uri` | Neo4j AuraDB 연결 |
| `neo4j-user` | Neo4j 인증 |
| `neo4j-password` | Neo4j 인증 |

> v2 대비 제거: `naver-api-client-id`, `naver-api-client-secret` (크롤링 제거)

---

## 4. 리전 선택

| 서비스 | 리전 | 근거 |
|---|---|---|
| GCS | `asia-northeast3` (서울) | 데이터 주권, 레이턴시 |
| BigQuery | `asia-northeast3` | GCS와 같은 리전 |
| Cloud Run Jobs | `asia-northeast3` | GCS 접근 레이턴시 |
| Cloud Workflows | `asia-northeast3` | Cloud Run과 같은 리전 |
| Vertex AI (Embedding) | `us-central1` | 모델 제공 리전 |
| Document AI | `us` | Phase 0 검증용 |
| Neo4j AuraDB | `asia-northeast1` (도쿄) | 서울 미지원 |
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

#### requirements.txt (light.1 — 크롤링 의존성 제거)

```
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
```

> v2 대비 제거: `playwright`, `readability-lxml`, `beautifulsoup4`, `google-genai`, `Dockerfile.crawler`, `requirements-crawl.txt`

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

## 7. light.1 전체 비용 요약

```
Phase 0 (2.5주):      ~$83
Phase 1 (5~6주):      ~$42
Phase 2 LLM (1개월):  ~$1,698
Phase 2 인프라 (1개월): ~$200
Gold Label 인건비:     ~$2,920
────────────────────────────
총비용 (시나리오 A):   ~$4,943 (~677만원)

standard.1 대비 절감:
  - 기간 단축: Phase 0 4~5주 → 2.5주, Phase 1 10~12주 → 5~6주
  - Gold Label 축소: 400건 → 200건 (-50%)
  - 크롤링 제거: $35 → $0
  - 인프라: 1개월만 (4개월 → 1개월, Phase 2 미운영)
```
