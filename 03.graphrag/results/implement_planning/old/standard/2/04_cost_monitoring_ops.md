# 비용 추정 + 모니터링 + 운영

> 전체 라이프사이클 비용 통합 추정 + 모니터링 구성 + 보안 설계 + 리전 선택
>
> **standard.2 변경**:
> - [standard.1.1-11] Looker Studio Phase 3으로 이동 → BigQuery Saved Queries로 대체
> - [standard.1.1-16] 문서 간 비용 수치 통일 (04_cost vs 05_models)

---

## 1. 비용 추정

### 1.1 Phase 0: API 검증 + PoC (4~5주)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| **Vertex AI API 검증 (2일)** | Gemini Flash/Pro, Embedding, DocAI | **~$55** |
| Cloud Run Jobs | PoC 50건 파싱 + 추출 | ~$5 |
| GCS | 150GB 원본 업로드 + 1GB 파싱 결과 + 테스트 데이터셋 | ~$5 |
| BigQuery | 10MB 이하 | ~$0 (Free tier) |
| Neo4j AuraDB Free | 200K 노드 | $0 |
| Secret Manager | 8개 시크릿 | ~$0 |
| Anthropic API (PoC) | 50건 × 3모델 비교 (일반 API) | ~$20 |
| Vertex AI Embedding (PoC) | 20쌍 검증 | ~$10 |
| **Phase 0 합계** | | **~$95** |

### 1.2 Phase 1: MVP 파이프라인 (11~13주)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| Cloud Run Jobs (파싱) | 2 vCPU × 4GB × ~6시간 | ~$10 |
| Cloud Run Jobs (Context) | CompanyContext 100건 + CandidateContext 1,000건 | ~$5 |
| Cloud Run Jobs (Graph) | 3~5 tasks × 2시간 [standard.1.1-12] | ~$5 |
| Cloud Run Jobs (기타) | Embedding, Mapping 등 | ~$10 |
| Anthropic API (개발) | 프롬프트 튜닝 + 통합 테스트 ~5,000건 | ~$50 |
| Vertex AI Embedding | 1,000건 테스트 | ~$1 |
| Neo4j AuraDB Free | 200K 노드 내 | $0 |
| BigQuery | 소량 | ~$5 |
| **Phase 1 합계** | | **~$86** |

### 1.3 Phase 2: 전체 처리 + 크롤링 (11~14주)

> 한국어 토큰 보정 적용: 한글 1자 ≈ 2~3 tokens.

#### LLM 비용

| 서비스 | 사용량 | 비용 |
|---|---|---|
| **Anthropic Batch API (CandidateContext)** | 500K × $0.00300/건 | **$1,500** |
| **Anthropic Batch API (CompanyContext)** | 10K JD × $0.0004/건 | **$4** |
| **Vertex AI Embedding** | 302M 토큰 × $0.0001/1K | **$30** |
| **Embedding Egress (서울→US)** | ~30GB × $0.12/GB (보수적) | **$3.6** |
| Gemini API (크롤링 추출) | 1,000기업 × ~15건 | **$5** |
| Silver Label (Sonnet) | 2,000건 × $0.01 | **$20** |
| 프롬프트 최적화 LLM (Sonnet) | ~500건 | **~$600** |
| **Phase 2 LLM 합계** | | **~$2,163** |

#### 인프라 비용 (Phase 2 기간 ~4개월)

| 서비스 | 월 비용 | 4개월 합계 |
|---|---|---|
| Cloud Run Jobs (전체 KG + 크롤링) | ~$30/월 | ~$120 |
| GCS | $10/월 | $40 |
| BigQuery | $10/월 | $40 |
| **Neo4j AuraDB Professional** | $100~200/월 | $400~800 |
| Cloud Workflows | ~$0.25/월 | ~$1 |
| Cloud Monitoring / Logging | $10/월 | $40 |
| **Phase 2 인프라 합계** | **$160~260/월** | **~$641~1,041** |

> [standard.1.1-16] 비용 항목 분류 명확화:
> - **LLM 비용** = Anthropic Batch + Embedding + Egress + Gemini + Silver Label + 프롬프트 최적화
> - **인프라 비용** = Cloud Run + GCS + BigQuery + Neo4j + Monitoring + Workflows
> - 두 카테고리를 분리하여 중복 계상 방지

### 1.4 시나리오별 총비용 (전 Phase 통합)

| 시나리오 | Phase 0 | Phase 1 | Phase 2 LLM | Phase 2 인프라 | Gold Label 인건비 | **총비용** | **원화** |
|---|---|---|---|---|---|---|---|
| **A: Haiku Batch (권장)** | $95 | $86 | $2,163 | ~$641~1,041 | $5,840 | **~$8,825~9,225** | **~1,209~1,264만** |
| D: Gemini Flash | $95 | $86 | $1,567 | ~$641~1,041 | $5,840 | **~$8,229~8,629** | **~1,127~1,182만** |
| B: Sonnet Batch | $95 | $86 | $5,322 | ~$641~1,041 | $5,840 | **~$11,984~12,384** | **~1,642~1,697만** |

> [standard.1.1-16] standard.1에서 $28~30 불일치 해소. LLM/인프라 경계 명확화로 비용 추정 신뢰성 향상.

### 1.5 운영 단계 (월간)

| 서비스 | 사용량 | 월 비용 |
|---|---|---|
| **Neo4j AuraDB Professional** | 2.77M+ 노드 유지 | **$100~200** |
| GCS | 200GB + Versioning | $6 |
| BigQuery | 10GB + 쿼리 | $10 |
| Cloud Run Jobs (증분 KG) | 일 1,000건 × 30일 | $10 |
| Cloud Run Jobs (크롤링 30일 주기) | 3 Jobs/월 | $3 |
| Cloud Run Jobs (Neo4j 백업) | 주 1회 | $1 |
| Anthropic API (증분) | 일 1,000건 × $0.003 | $90 |
| Gemini API (크롤링 LLM 추출) | 1,000기업/월 | $5 |
| Vertex AI Embedding (증분) | 일 1,000건 | ~$0.01 |
| Cloud Scheduler + Workflows | 일 2회 + 주 1회 백업 + 월 1회 크롤링 | ~$1 |
| Monitoring / Logging | 기본 | $10 |
| 네이버 뉴스 API | 무료 | $0 |
| **운영 월 합계** | | **~$236~336/월** |

---

## 2. 모니터링 구성

### 2.1 BigQuery Saved Queries — [standard.1.1-11] Looker Studio 대체

> **standard.2 변경**: Looker Studio 대시보드를 Phase 3으로 이동.
> Phase 2에서는 BigQuery Saved Queries + Cloud Monitoring 알림으로 충분.
> 2명 운영 체제에서 Looker Studio 11개 패널은 과잉 투자 (구축 2~3일 vs SQL 30분/일).

```sql
-- [Saved Query 1] 일일 처리 현황 (파이프라인별)
SELECT
  run_date, pipeline,
  COUNTIF(status = 'SUCCESS') AS success_count,
  COUNTIF(status = 'FAILED') AS fail_count,
  ROUND(COUNTIF(status = 'FAILED') / COUNT(*) * 100, 2) AS error_rate_pct,
  ROUND(SUM(input_tokens) * 0.00000040 + SUM(output_tokens) * 0.0000020, 2) AS estimated_cost_usd
FROM graphrag_kg.processing_log
WHERE run_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY run_date, pipeline
ORDER BY run_date DESC, pipeline;

-- [Saved Query 2] Chunk 진행률
SELECT
  pipeline,
  COUNT(*) AS total_chunks,
  COUNTIF(status = 'COMPLETED') AS completed,
  COUNTIF(status = 'FAILED') AS failed,
  ROUND(COUNTIF(status = 'COMPLETED') / COUNT(*) * 100, 1) AS completion_pct
FROM graphrag_kg.chunk_status
GROUP BY pipeline;

-- [Saved Query 3] Batch API 추적 현황
SELECT
  status, COUNT(*) AS batch_count,
  COUNTIF(result_collected) AS collected,
  COUNTIF(NOT result_collected AND status = 'COMPLETED') AS uncollected
FROM graphrag_kg.batch_tracking
GROUP BY status;

-- [Saved Query 4] 만료 위험 batch
SELECT
  batch_id, chunk_id, submitted_at,
  TIMESTAMP_DIFF(TIMESTAMP_ADD(submitted_at, INTERVAL 29 DAY), CURRENT_TIMESTAMP(), HOUR) AS hours_until_expiry
FROM graphrag_kg.batch_tracking
WHERE status = 'COMPLETED' AND NOT result_collected
  AND TIMESTAMP_DIFF(TIMESTAMP_ADD(submitted_at, INTERVAL 29 DAY), CURRENT_TIMESTAMP(), HOUR) < 72;

-- [Saved Query 5] 피처 활성화 비율
SELECT
  COUNT(*) AS total_mappings,
  ROUND(COUNTIF(active_feature_count >= 1) / COUNT(*) * 100, 1) AS at_least_1_active_pct,
  ROUND(AVG(overall_match_score), 3) AS avg_overall_score
FROM graphrag_kg.mapping_features;

-- [Saved Query 6] 크롤링 성공률
SELECT
  crawl_date,
  COUNT(DISTINCT company_id) AS companies_crawled,
  COUNTIF(crawl_status = 'SUCCESS') AS pages_success,
  ROUND(COUNTIF(crawl_status = 'SUCCESS') / COUNT(*) * 100, 1) AS success_rate_pct
FROM graphrag_kg.crawl_raw_data
GROUP BY crawl_date
ORDER BY crawl_date DESC;
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
| **Batch 결과 만료 72시간 이내** | **Slack + Email (CRITICAL)** | **일일 체크** |
| 크롤링 성공률 < 70% | Slack | 즉시 |
| **Neo4j 백업 실패** | **Slack + Email** | **즉시** |

### CRITICAL 알림 대응 절차 (Runbook)

| 알림 | 대응 절차 |
|------|-----------|
| **파싱 실패율 > 10%** | 1) processing_log에서 실패 패턴 확인 → 2) dead-letter 샘플 3건 수동 확인 → 3) 파서 버그 시 핫픽스 + 재배포 → 4) LLM 출력 변경 시 프롬프트 수정 |
| **Batch 결과 만료 72시간 이내** | 1) `kg-batch-poll` 즉시 수동 실행 → 2) 수집 실패 시 Anthropic API 상태 확인 → 3) 수집 불가 시 해당 chunk 재제출 |
| **Neo4j 연결 실패** | 1) AuraDB Console에서 인스턴스 상태 확인 → 2) Secret Manager URI/password 유효성 확인 → 3) AuraDB 장애 시 Graph 적재만 보류 |
| **Cloud Run Job 실패 (3회 연속)** | 1) Cloud Logging에서 OOM/Timeout 여부 확인 → 2) OOM: 메모리 상향 재배포 → 3) Timeout: 처리 건수 축소 후 재실행 |

---

## 3. 보안 설계

> standard.1과 동일. 상세 내용은 `standard.1/04_cost_monitoring_ops.md` 3절 참조.
> PII 처리 플로우, IAM 최소 권한, Secret Manager, 크롤링 데이터 보안 정책.

---

## 4. 리전 선택

> standard.1과 동일. 상세 내용은 `standard.1/04_cost_monitoring_ops.md` 4절 참조.

---

## 5. Docker 이미지

> standard.1과 동일. 상세 내용은 `standard.1/04_cost_monitoring_ops.md` 5절 참조.

---

## 6. 백업 전략

> standard.1과 동일. 상세 내용은 `standard.1/04_cost_monitoring_ops.md` 6절 참조.
> GCS Object Versioning + Neo4j APOC export + BigQuery time-travel.
