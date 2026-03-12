# Phase 2: 확장 + 크롤링 + 품질 (10~12주)

> **목적**: 전체 데이터(500K 이력서) 처리 + 크롤링으로 CompanyContext 보강 + 품질 평가 + 운영 자동화.
>
> **v2 변경**: v0/v1에서 Phase 3으로 분리되었던 크롤링 파이프라인을 Phase 2에 통합.
> 전체 데이터 처리와 크롤링을 병행하여 CompanyContext 보강을 조기에 반영.
>
> **인력**: DE 1명 + MLE 1명 풀타임, 도메인 전문가 1명 파트타임

---

## 2-1. 전체 데이터 처리 (2~3주) — Week 17-20

| # | 작업 | GCP 서비스 | 비고 |
|---|---|---|---|
| 2-1-1 | 이력서 500K 중복 제거 실행 | Cloud Run Job | canonical ~450K |
| 2-1-2 | 450 chunks × Batch API 처리 | Anthropic Batch API | 동시 5~10 batch |
| 2-1-3 | JD 10K × Batch API 처리 | Anthropic Batch API | |
| 2-1-4 | Graph 전체 적재 | Cloud Run Job (8 tasks) | |
| 2-1-5 | Embedding 전체 적재 | Cloud Run Job (10 tasks) | |
| 2-1-6 | MappingFeatures 전체 계산 | Cloud Run Job (20 tasks) | |
| 2-1-7 | Dead-letter 재처리 | Cloud Run Job | |
| 2-1-8 | Neo4j Professional 전환 (필요 시) | Neo4j Console | |

### Chunk 처리 흐름

```
이력서 ~450K (중복 제거 후)
    │
    ├─ 1,000건/chunk × ~450 chunks
    │
    ├─ 동시 처리: 5~10 chunks (Batch API quota)
    │
    ├─ BigQuery chunk_status로 진행률 추적
    │   └─ Looker Studio 대시보드 연동
    │
    ├─ 실패 chunk: 자동 재시도 (최대 2회)
    │   └─ 2회 실패 → 건별 분해 → 개별 재시도
    │
    └─ 예상: ~45 batch × 6시간 = ~11일 (여유 포함 2~3주)
```

---

## 2-2. 크롤링 파이프라인 구축 (4주) — Week 18-22 (2-1과 병행)

> **원본**: v0 `crawling-gcp-plan.md` 전체 흡수.
> Phase 0에서 검증된 Gemini API를 크롤링 LLM 추출에 활용.

### 크롤링 아키텍처

```
Cloud Scheduler (30일 주기)
    │
    ▼
Cloud Workflows (오케스트레이션)
    │
    ├─[Step 1] BigQuery에서 크롤링 대상 기업 목록 조회
    │
    ├─[Step 2] Cloud Run Job: 홈페이지 크롤링
    │   ├─ Playwright (headless Chrome)
    │   ├─ URL 발견 + 페이지 분류 (about/product/careers)
    │   ├─ robots.txt 준수 (urllib.robotparser)
    │   ├─ 텍스트 정제 (Readability)
    │   └─ 결과 → GCS + BigQuery
    │
    ├─[Step 3] Cloud Run Job: 뉴스 수집
    │   ├─ 네이버 뉴스 검색 API 호출
    │   ├─ 5개 카테고리: funding, product, org_change, performance, mna
    │   ├─ funding/org_change/mna → 기사 본문 크롤링 (link 추가 크롤링)
    │   ├─ 중복 제거 + 관련성 필터
    │   ├─ 기업당 최대 30건 cap
    │   └─ 결과 → GCS + BigQuery
    │
    ├─[Step 4] Cloud Run Job: LLM 추출
    │   ├─ Gemini API (Phase 0에서 확정된 모델)
    │   ├─ 페이지/기사 유형별 프롬프트 (4종)
    │   │   ├─ homepage_extract: product_description, market_segment, scale/culture_signals
    │   │   ├─ news_funding: funding_round, amount, investors, growth_narrative
    │   │   ├─ news_org: change_type, tension_type, tension_description
    │   │   └─ news_product: product_name, traction_data, growth_narrative
    │   ├─ QPM throttle (5초 간격, 무료 15 QPM 내 안전 마진)
    │   └─ 결과 → BigQuery (extracted_fields)
    │
    └─[Step 5] BigQuery: CompanyContext 통합 뷰 갱신
```

### 2-2-1. 크롤러 인프라 구축 (1주)

| # | 작업 | GCP 서비스 |
|---|---|---|
| 2-2-1-1 | Playwright 크롤러 Docker 이미지 | Cloud Run Job |
| 2-2-1-2 | 뉴스 수집기 Docker 이미지 | Cloud Run Job |
| 2-2-1-3 | LLM 추출기 Docker 이미지 | Cloud Run Job |
| 2-2-1-4 | 크롤링 BigQuery 테이블 생성 | BigQuery |
| 2-2-1-5 | 네이버 뉴스 API 키 발급 + Secret Manager | Secret Manager |
| 2-2-1-6 | 크롤링 대상 기업 목록 작성 (domain_url 확보) | BigQuery |

#### BigQuery 크롤링 테이블

```sql
-- 크롤링 대상 기업 마스터
CREATE TABLE graphrag_kg.crawl_company_targets (
  company_id STRING NOT NULL,
  company_name STRING NOT NULL,
  aliases ARRAY<STRING>,
  domain_url STRING,
  nice_industry_code STRING,
  is_active BOOLEAN DEFAULT TRUE,
  last_homepage_crawl TIMESTAMP,
  last_news_crawl TIMESTAMP,
  created_at TIMESTAMP
);

-- 홈페이지 크롤링 결과
CREATE TABLE graphrag_kg.crawl_homepage_pages (
  company_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  page_url STRING,
  page_type STRING,               -- about / product / careers / blog / culture / other
  text_length INT64,
  crawl_status STRING,            -- SUCCESS / BLOCKED / TIMEOUT / NO_CONTENT
  gcs_raw_path STRING,
  gcs_text_path STRING,
  created_at TIMESTAMP
);

-- 뉴스 수집 결과
CREATE TABLE graphrag_kg.crawl_news_articles (
  company_id STRING NOT NULL,
  article_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  title STRING,
  source_media STRING,
  publish_date DATE,
  article_url STRING,
  category STRING,                -- funding / product / org_change / performance / mna
  body_length INT64,
  is_press_release BOOLEAN,
  gcs_path STRING,
  created_at TIMESTAMP
);

-- LLM 추출 결과
CREATE TABLE graphrag_kg.crawl_extracted_fields (
  company_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  source_type STRING,
  source_id STRING,
  product_description STRING,
  market_segment STRING,
  funding_round STRING,
  funding_amount STRING,
  investors ARRAY<STRING>,
  growth_narrative STRING,
  tension_type STRING,
  tension_description STRING,
  culture_signals JSON,
  scale_signals JSON,
  extraction_model STRING,
  evidence_spans JSON,
  confidence FLOAT64,
  adjusted_confidence FLOAT64,
  created_at TIMESTAMP
);

-- 기업별 크롤링 집계
CREATE TABLE graphrag_kg.crawl_company_summary (
  company_id STRING NOT NULL,
  homepage_pages_count INT64,
  news_articles_count INT64,
  extracted_fields_count INT64,
  product_description_filled BOOLEAN,
  structural_tensions_filled BOOLEAN,
  fill_rate FLOAT64,
  last_updated TIMESTAMP
);
```

#### Cloud Run Job 설정 (크롤링)

| Job 이름 | CPU | Memory | Timeout | 비고 |
|---|---|---|---|---|
| `crawl-homepage` | 2 vCPU | 2Gi | 3600s | Playwright + Chrome |
| `crawl-news` | 1 vCPU | 512Mi | 3600s | API + 본문 크롤링 |
| `crawl-extract` | 1 vCPU | 1Gi | 3600s | Gemini API |

### 2-2-2. 홈페이지 크롤러 + 파일럿 (1주)

- Playwright 기반 headless Chrome 크롤링
- 페이지 분류: about / product / careers 패턴 매칭
- robots.txt 준수 (urllib.robotparser)
- 텍스트 정제: readability-lxml + BeautifulSoup
- **파일럿: 기업 10개 → 결과 검수**
- 기업 15개/배치, 10페이지/기업, 요청 간격 2초

### 2-2-3. 뉴스 수집기 + 파일럿 (1주, 2-2-2와 병행)

- 네이버 뉴스 검색 API (5개 카테고리 쿼리)
- funding/org_change/mna 카테고리 → 기사 본문 크롤링 (link 추가 크롤링)
  - 네이버 뉴스 API는 title + description만 반환, 본문 미제공
- product/performance → description으로 충분
- 중복 제거 (link 기준) + 관련성 필터 (회사명 포함 여부)
- 기업당 최대 30건 cap
- **파일럿: 기업 10개 → 수집량/관련성 확인**

### 2-2-4. LLM 추출기 + 프롬프트 튜닝 (1주)

- 4종 프롬프트: homepage / news_funding / news_org / news_product
- Gemini API rate limit 대응 (5초 간격, 429 → 30초 대기 재시도)
- **파일럿: 기업 10개 → 추출 품질 Human eval → 프롬프트 튜닝**

---

## 2-3. 크롤링 데이터 → CompanyContext 보강 (1주) — Week 22-23

| # | 작업 | 비고 |
|---|---|---|
| 2-3-1 | 크롤링 추출 결과 → CompanyContext 병합 로직 | |
| 2-3-2 | operating_model facet merge (v6 M-5) | 기존 값과 크롤링 값 통합 |
| 2-3-3 | structural_tensions 추출 활성화 | 뉴스 org_change에서 |
| 2-3-4 | Organization 노드 속성 업데이트 | product_description, market_segment |
| 2-3-5 | 크롤링 전/후 품질 비교 (50건) | fill_rate 검증 |

### 목표 보강 지표

| 보강 대상 필드 | 크롤링 전 | 크롤링 후 목표 |
|---|---|---|
| `domain_positioning.product_description` | null | 60%+ 활성화 |
| `structural_tensions` | null (70%+) | 30~50% 활성화 |
| `operating_model.facets` confidence | 0.30~0.45 | 0.40~0.60 |
| `stage_estimate` confidence | 0.50~0.65 | 0.65~0.80 |
| CompanyContext 전체 fill_rate | 0.71 | 0.85+ |

---

## 2-4. 품질 평가 (1주, 2-1과 병행) — Week 19-20

| # | 작업 | 도구 |
|---|---|---|
| 2-4-1 | Gold Test Set 구축 (전문가 2인 × 200건) | 수동 + BigQuery |
| 2-4-2 | Inter-annotator agreement (Cohen's κ) | Python |
| 2-4-3 | Power analysis (Cohen's d) | Python (scipy) |
| 2-4-4 | 평가 지표 측정 + BigQuery 적재 | BigQuery quality_metrics |

### 평가 기준

| 지표 | 최소 기준 | 목표 |
|---|---|---|
| scope_type 분류 정확도 | > 70% | > 80% |
| outcome 추출 F1 | > 55% | > 70% |
| situational_signal 분류 F1 | > 50% | > 65% |
| vacancy scope_type 정확도 | > 65% | > 80% |
| stage_estimate 정확도 | > 75% | > 85% |
| 피처 1개+ ACTIVE 비율 | > 80% | > 90% |
| Human eval 상관관계 (r) | > 0.4 | > 0.6 |
| Cohen's d 효과 크기 | ≥ 0.5 | ≥ 0.8 |

---

## 2-5. DS/MLE 서빙 인터페이스 (1주) — Week 20-21

| # | 작업 | GCP 서비스 |
|---|---|---|
| 2-5-1 | BigQuery mapping_features 스키마 확정 | BigQuery |
| 2-5-2 | SQL 예시 쿼리 작성 + 문서화 | |
| 2-5-3 | Context on/off ablation 테스트 환경 | BigQuery |

---

## 2-6. 증분 처리 + 운영 인프라 (1~2주) — Week 21-23

### Cloud Scheduler 설정

```bash
SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com

# 일일 증분 처리
gcloud scheduler jobs create http kg-incremental-daily \
  --schedule="0 2 * * *" \
  --uri="https://workflowexecutions.googleapis.com/v1/projects/graphrag-kg/locations/asia-northeast3/workflows/kg-incremental/executions" \
  --http-method=POST \
  --oauth-service-account-email=$SA \
  --time-zone="Asia/Seoul"

# Dead-letter 재처리 (일일)
gcloud scheduler jobs create http kg-dead-letter-daily \
  --schedule="0 4 * * *" \
  --uri="https://asia-northeast3-run.googleapis.com/v2/projects/graphrag-kg/locations/asia-northeast3/jobs/kg-dead-letter:run" \
  --http-method=POST \
  --oauth-service-account-email=$SA \
  --time-zone="Asia/Seoul"

# 크롤링 (30일 주기)
gcloud scheduler jobs create http crawl-monthly \
  --schedule="0 0 1 * *" \
  --uri="https://workflowexecutions.googleapis.com/v1/projects/graphrag-kg/locations/asia-northeast3/workflows/crawl-pipeline/executions" \
  --http-method=POST \
  --oauth-service-account-email=$SA \
  --time-zone="Asia/Seoul"
```

### 증분 처리 워크플로우

```yaml
# workflows/kg-incremental.yaml
main:
  steps:
    - detect_changes:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-detect-changes"}
          location: "asia-northeast3"
        result: changes

    - check_has_changes:
        switch:
          - condition: ${changes.body.new_count == 0 and changes.body.updated_count == 0}
            next: no_changes
        next: process_changes

    - process_changes:
        steps:
          - parse_new:
              call: googleapis.run.v1.namespaces.jobs.run
              args:
                name: ${"namespaces/" + project_id + "/jobs/kg-parse-resumes"}
                location: "asia-northeast3"
                body:
                  overrides:
                    taskCount: 1
                    containerOverrides:
                      - env:
                          - name: MODE
                            value: "incremental"

          - extract_and_load:
              call: googleapis.run.v1.namespaces.jobs.run
              args:
                name: ${"namespaces/" + project_id + "/jobs/kg-realtime-extract"}
                location: "asia-northeast3"

    - no_changes:
        return: "No changes detected"
```

### ML Knowledge Distillation (선택적)

| # | 작업 | 비고 |
|---|---|---|
| 2-6-1 | scope_type 분류기 학습 (KLUE-BERT) | F1 > 75% 목표 |
| 2-6-2 | seniority 분류기 학습 | F1 > 80% 목표 |
| 2-6-3 | Confidence 기반 라우팅 (ML > 0.85 → ML, else → LLM) | |

---

## Phase 2 산출물

```
□ 전체 데이터 처리 완료 (450K 이력서 + 10K JD)
□ 크롤링 파이프라인 동작 (홈페이지 + 뉴스 + LLM 추출)
□ CompanyContext 보강 완료 (fill_rate 0.85+ 목표)
□ 품질 평가 리포트 (Gold Test Set 400건)
□ BigQuery 서빙 인터페이스 확정
□ 증분 처리 자동화 (Cloud Scheduler → Workflows)
□ 크롤링 30일 주기 자동화
□ Dead-letter 일일 재처리 자동화
□ Looker Studio 대시보드 구축
```
