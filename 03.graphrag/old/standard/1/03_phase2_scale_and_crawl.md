# Phase 2: 확장 + 크롤링 + 품질 (12~16주)

> **목적**: 전체 데이터(500K 이력서) 처리 + 크롤링으로 CompanyContext 보강 + 품질 평가 + 운영 자동화.
>
> **standard.1 변경**:
> - [standard.1-3] 2-0: Neo4j Professional 전환을 **필수** 선행 작업으로 격상
> - [standard.1-7] 2-1: 전체 데이터 처리 타임라인 2~3주 → **3~4주**로 조정
> - [standard.1-9] Pre-Phase 2에 크롤링 법적 검토 추가
> - [standard.23] 크롤링과 전체 처리를 **직렬화** (인력 부족 리스크 해소)
> - [standard.24] Cloud Workflows 도입 (Phase 1의 Makefile에서 전환)
> - [standard.25] ML Knowledge Distillation을 Phase 3으로 분리
>
> **인력**: DE 1명 + MLE 1명 풀타임, 도메인 전문가 1명 파트타임
>
> **인력 추가 옵션** [standard.23]: 크롤링 담당 인력 1명 추가 투입 시
> → 2-1(전체 처리)과 2-3(크롤링) 병행 가능 → 12~14주로 단축

---

## Pre-Phase 2: 사전 준비 (Phase 1 완료 ~ Phase 2 시작 사이)

### [standard.1-9] 크롤링 법적 검토

```bash
□ 법무팀에 크롤링 법적 검토 요청
  - 검토 항목:
    ├─ 기업 홈페이지 크롤링의 저작권법 적합성
    ├─ 네이버 뉴스 API 이용약관 준수 사항
    ├─ 정보통신망법 관련 리스크 (대량 접근, 서버 부하)
    ├─ 크롤링 데이터의 LLM 입력 활용 시 저작권 이슈
    └─ 원본 비보관 정책의 법적 리스크 경감 효과
  - 판정 기한: Phase 2 Week 4 이전 (2-3 크롤링 시작 전)
□ 정책 명시:
  - "추출 목적 한정, 원본 비보관" 정책 문서화
  - robots.txt 준수 + 요청 간격 2초 이상
  - 크롤링 대상 기업 수 제한 (초기 1,000개)
```

**법적 검토 지연/불허 시**: 크롤링을 NICE/DART 공공 데이터로 한정, 홈페이지/뉴스 크롤링 보류

### [standard.1-3] Neo4j Professional 전환 사전 준비

```bash
□ Professional 인스턴스 사양 결정
  - 예상 노드 수: ~2.77M (Phase 0-3-8 계산 기반)
  - 최소 사양: 4GB RAM / 16GB Storage
  - 리전: asia-northeast1 (도쿄)
□ 예산 승인: $65~200/월 (Phase 2 기간 ~4개월 = $260~800)
□ Phase 1 Neo4j 백업 완료 확인 (APOC export → GCS)
```

---

## 2-0. Neo4j Professional 전환 (1일) — Week 17, Phase 2 시작 전 [standard.1-3]

> **필수** 선행 작업. "필요 시"가 아닌 **확정 일정**.
> Phase 1의 ~9K 노드에서 Phase 2의 ~2.77M 노드로 확장 시 Free 200K 한도 즉시 초과.

| # | 작업 | 도구 | 소요 시간 |
|---|---|---|---|
| 2-0-1 | AuraDB Professional 인스턴스 생성 | Neo4j Console | 5분 |
| 2-0-2 | Phase 1 백업 데이터 Import | cypher-shell | 30분 |
| 2-0-3 | Vector Index 재생성 | cypher-shell | 5분 |
| 2-0-4 | Constraint 재생성 | cypher-shell | 5분 |
| 2-0-5 | Secret Manager 연결 정보 업데이트 | gcloud CLI | 5분 |
| 2-0-6 | 연결 테스트 (Cloud Run Job → Neo4j) | Cloud Run | 10분 |
| 2-0-7 | Free 인스턴스 삭제 | Neo4j Console | 1분 |

```bash
# Secret Manager 업데이트
echo -n "neo4j+s://XXXXX.databases.neo4j.io" | \
  gcloud secrets versions add neo4j-uri --data-file=-

echo -n "new_password_here" | \
  gcloud secrets versions add neo4j-password --data-file=-

# 연결 테스트
gcloud run jobs execute kg-industry-load --region=asia-northeast3 --wait
```

---

## 2-1. 전체 데이터 처리 (3~4주) — Week 17-21 [standard.1-7]

> **standard.1 변경**: 2~3주 → 3~4주. 현실적 처리 시간 반영 (R-7).

| # | 작업 | GCP 서비스 | 비고 |
|---|---|---|---|
| 2-1-1 | 이력서 500K 중복 제거 실행 | Cloud Run Job | canonical ~450K |
| 2-1-2 | 450 chunks × Batch API 처리 | Anthropic Batch API | 동시 5~10 batch [standard.1-4] |
| 2-1-3 | JD 10K × Batch API 처리 | Anthropic Batch API | |
| 2-1-4 | Graph 전체 적재 | Cloud Run Job (8 tasks) | |
| 2-1-5 | Embedding 전체 적재 | Cloud Run Job (10 tasks) | |
| 2-1-6 | MappingFeatures 전체 계산 | Cloud Run Job (20 tasks) | |
| 2-1-7 | Dead-letter 재처리 | Cloud Run Job | |

### Chunk 처리 흐름 — [standard.1-4, standard.1-7] 현실적 추정

```
이력서 ~450K (중복 제거 후)
    │
    ├─ 1,000건/chunk × ~450 chunks
    │
    ├─ 동시 처리: 5~10 chunks (Anthropic quota 사전 확인 기반) [standard.1-4]
    │
    ├─ BigQuery chunk_status + batch_tracking으로 진행률 추적 [standard.1-5]
    │   └─ Looker Studio 대시보드 연동
    │
    ├─ 실패 chunk: 자동 재시도 (최대 2회)
    │   └─ 2회 실패 → 건별 분해 → 개별 재시도
    │
    ├─ Batch 결과 보관 기간 (29일) 내 수집 보장 [standard.1-4]
    │   └─ 일일 batch_tracking 미수집 건 알림
    │
    └─ 현실적 추정: [standard.1-7]
        ├─ 450 chunks / 10 동시 = 45 라운드 × 6시간(평균) = ~11일
        ├─ + 실패 재시도: ~2일
        ├─ + 결과 수집 + Context 생성: ~2일
        ├─ + Graph 적재 + Embedding: ~3일
        ├─ + 버퍼: ~3일
        └─ = 총 ~21일 ≈ 3~4주
```

### Cloud Workflows 도입 — [standard.24]

> Phase 2부터 Cloud Workflows로 전환. Phase 1의 Makefile보다 안정적 오케스트레이션 필요.

```bash
# Cloud Workflows API 활성화 (Phase 2 시점)
gcloud services enable workflows.googleapis.com

# Workflows IAM
gcloud projects add-iam-policy-binding graphrag-kg \
  --member="serviceAccount:$SA" \
  --role="roles/workflows.invoker"
```

```yaml
# workflows/kg-full-pipeline.yaml
main:
  params: [args]
  steps:
    - init:
        assign:
          - project_id: ${sys.get_env("GOOGLE_CLOUD_PROJECT_ID")}
          - region: "asia-northeast3"
          - run_id: ${text.replace_all(time.format(sys.now()), ":", "")}

    # Phase 1: 전처리
    - parse_resumes:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-parse-resumes"}
          location: ${region}
          body:
            overrides:
              taskCount: 50
              containerOverrides:
                - env:
                    - name: RUN_ID
                      value: ${run_id}

    - dedup_resumes:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-dedup-resumes"}
          location: ${region}

    # Phase 2: Context 생성 (A ∥ B 병렬)
    - create_contexts:
        parallel:
          branches:
            - company_context:
                steps:
                  - run_company:
                      call: googleapis.run.v1.namespaces.jobs.run
                      args:
                        name: ${"namespaces/" + project_id + "/jobs/kg-company-ctx"}
                        location: ${region}

            - candidate_context:
                steps:
                  - prepare_batches:
                      call: googleapis.run.v1.namespaces.jobs.run
                      args:
                        name: ${"namespaces/" + project_id + "/jobs/kg-batch-prepare"}
                        location: ${region}
                  - submit_batches:
                      call: googleapis.run.v1.namespaces.jobs.run
                      args:
                        name: ${"namespaces/" + project_id + "/jobs/kg-batch-submit"}
                        location: ${region}
                  - collect_results:
                      call: googleapis.run.v1.namespaces.jobs.run
                      args:
                        name: ${"namespaces/" + project_id + "/jobs/kg-batch-collect"}
                        location: ${region}

    # Phase 3: Graph 적재
    - load_graph:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-graph-load"}
          location: ${region}
          body:
            overrides:
              taskCount: 8

    # Phase 4: Embedding + MappingFeatures
    - generate_embeddings:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-embedding"}
          location: ${region}

    - compute_mapping:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-mapping"}
          location: ${region}

    - notify:
        call: http.post
        args:
          url: ${args.slack_webhook_url}
          body:
            text: ${"KG Pipeline 완료: run_id=" + run_id}
```

---

## 2-2. 품질 평가 (1주, 2-1과 병행) — Week 19-20

| # | 작업 | 도구 |
|---|---|---|
| 2-2-1 | Gold Test Set 구축 (전문가 2인 × 200건) | 수동 + BigQuery |
| 2-2-2 | Inter-annotator agreement (Cohen's κ) | Python |
| 2-2-3 | Power analysis (Cohen's d) | Python (scipy) |
| 2-2-4 | 평가 지표 측정 + BigQuery 적재 | BigQuery quality_metrics |

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

## 2-3. 크롤링 파이프라인 구축 (4주) — Week 21-25 [standard.23]

> **standard.1 변경**: 2-1 전체 처리 완료 **후** 직렬 수행 (v2에서는 병행).
> 이유: DE 1명 + MLE 1명으로 크롤링(Playwright, 뉴스 API, LLM 추출)과 전체 데이터 처리
> 운영/모니터링을 동시 수행하면 인력 부족 리스크 높음 (R-13).
>
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
    │   ├─ 요청 간격 2초 이상 [standard.1-9]
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

### 2-3-1. 크롤러 인프라 구축 (1주)

| # | 작업 | GCP 서비스 |
|---|---|---|
| 2-3-1-1 | Playwright 크롤러 Docker 이미지 | Cloud Run Job |
| 2-3-1-2 | 뉴스 수집기 Docker 이미지 | Cloud Run Job |
| 2-3-1-3 | LLM 추출기 Docker 이미지 | Cloud Run Job |
| 2-3-1-4 | 크롤링 BigQuery 테이블 생성 | BigQuery |
| 2-3-1-5 | 네이버 뉴스 API 키 발급 + Secret Manager | Secret Manager |
| 2-3-1-6 | 크롤링 대상 기업 목록 작성 (domain_url 확보) | BigQuery |

#### BigQuery 크롤링 테이블

```sql
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

CREATE TABLE graphrag_kg.crawl_homepage_pages (
  company_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  page_url STRING,
  page_type STRING,
  text_length INT64,
  crawl_status STRING,
  gcs_raw_path STRING,
  gcs_text_path STRING,
  created_at TIMESTAMP
);

CREATE TABLE graphrag_kg.crawl_news_articles (
  company_id STRING NOT NULL,
  article_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  title STRING,
  source_media STRING,
  publish_date DATE,
  article_url STRING,
  category STRING,
  body_length INT64,
  is_press_release BOOLEAN,
  gcs_path STRING,
  created_at TIMESTAMP
);

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

### 2-3-2. 홈페이지 크롤러 + 파일럿 (1주)

- Playwright 기반 headless Chrome 크롤링
- 페이지 분류: about / product / careers 패턴 매칭
- robots.txt 준수 (urllib.robotparser) + 요청 간격 2초 [standard.1-9]
- 텍스트 정제: readability-lxml + BeautifulSoup
- **파일럿: 기업 10개 → 결과 검수**
- 기업 15개/배치, 10페이지/기업

### 2-3-3. 뉴스 수집기 + 파일럿 (1주, 2-3-2와 병행)

- 네이버 뉴스 검색 API (5개 카테고리 쿼리)
- funding/org_change/mna 카테고리 → 기사 본문 크롤링
- 중복 제거 (link 기준) + 관련성 필터 (회사명 포함 여부)
- 기업당 최대 30건 cap
- **파일럿: 기업 10개 → 수집량/관련성 확인**

### 2-3-4. LLM 추출기 + 프롬프트 튜닝 (1주)

- 4종 프롬프트: homepage / news_funding / news_org / news_product
- Gemini API rate limit 대응 (5초 간격, 429 → 30초 대기 재시도)
- **파일럿: 기업 10개 → 추출 품질 Human eval → 프롬프트 튜닝**

---

## 2-4. 크롤링 데이터 → CompanyContext 보강 (1주) — Week 25-26

| # | 작업 | 비고 |
|---|---|---|
| 2-4-1 | 크롤링 추출 결과 → CompanyContext 병합 로직 | |
| 2-4-2 | operating_model facet merge (v6 M-5) | 기존 값과 크롤링 값 통합 |
| 2-4-3 | structural_tensions 추출 활성화 | 뉴스 org_change에서 |
| 2-4-4 | Organization 노드 속성 업데이트 | product_description, market_segment |
| 2-4-5 | 크롤링 전/후 품질 비교 (50건) | fill_rate 검증 |

### 목표 보강 지표

| 보강 대상 필드 | 크롤링 전 | 크롤링 후 목표 |
|---|---|---|
| `domain_positioning.product_description` | null | 60%+ 활성화 |
| `structural_tensions` | null (70%+) | 30~50% 활성화 |
| `operating_model.facets` confidence | 0.30~0.45 | 0.40~0.60 |
| `stage_estimate` confidence | 0.50~0.65 | 0.65~0.80 |
| CompanyContext 전체 fill_rate | 0.71 | 0.85+ |

---

## 2-5. DS/MLE 서빙 인터페이스 (1주) — Week 26-27

| # | 작업 | GCP 서비스 |
|---|---|---|
| 2-5-1 | BigQuery mapping_features 스키마 확정 | BigQuery |
| 2-5-2 | SQL 예시 쿼리 작성 + 문서화 | |
| 2-5-3 | Context on/off ablation 테스트 환경 | BigQuery |

---

## 2-6. 증분 처리 + 운영 인프라 (1~2주) — Week 27-29

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

# [standard.20] Neo4j 주간 백업
gcloud scheduler jobs create http neo4j-weekly-backup \
  --schedule="0 3 * * 0" \
  --uri="https://asia-northeast3-run.googleapis.com/v2/projects/graphrag-kg/locations/asia-northeast3/jobs/kg-neo4j-backup:run" \
  --http-method=POST \
  --oauth-service-account-email=$SA \
  --time-zone="Asia/Seoul"
```

### [standard.20] Neo4j 백업 Job

```bash
gcloud run jobs create kg-neo4j-backup \
  --image=$IMAGE \
  --command="python,src/neo4j_backup.py" \
  --tasks=1 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3
```

```python
# src/neo4j_backup.py
"""[standard.20] Neo4j AuraDB Professional 주간 백업"""
from neo4j import GraphDatabase
from google.cloud import storage
from datetime import datetime

def backup_neo4j():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    gcs = storage.Client()
    bucket = gcs.bucket("graphrag-kg-data")
    date_str = datetime.utcnow().strftime("%Y%m%d")

    with driver.session() as session:
        # APOC export
        result = session.run("CALL apoc.export.json.all(null, {stream: true})")
        json_data = result.single()["data"]

        # GCS 업로드
        blob = bucket.blob(f"backups/neo4j/{date_str}/full_export.json")
        blob.upload_from_string(json_data)

        # 노드/엣지 수 기록 (검증용)
        stats = session.run("""
            MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt
            UNION ALL
            MATCH ()-[r]->() RETURN type(r) AS label, count(r) AS cnt
        """)
        stats_blob = bucket.blob(f"backups/neo4j/{date_str}/stats.json")
        stats_blob.upload_from_string(json.dumps([dict(r) for r in stats]))

    print(f"Neo4j backup completed: {date_str}")
```

### [R-1] 증분 처리 변경 감지 메커니즘

```
변경 감지 기준 (kg-detect-changes Job):
  1. 신규 이력서: processing_log의 마지막 처리 시점 이후 GCS raw/resumes/에 새로 업로드된 파일
     - GCS Object metadata의 timeCreated > last_incremental_run_timestamp
  2. 신규 JD: 동일 방식으로 raw/jds/ 탐지
  3. JD 변경: JD JSON의 content_hash 비교 (이전 처리 시점 대비)

JD 변경 시 영향 범위:
  - JD 변경 → 해당 JD의 CompanyContext 재생성
  - CompanyContext 변경 → 해당 JD의 MAPPED_TO 관계만 재계산 (전체 재처리 불필요)
  - Vacancy 노드 속성 업데이트 (MERGE로 idempotent)

사전(tech_dictionary, company_alias, role_alias) 업데이트 시:
  - 사전 파일의 GCS Object generation 번호 변경 감지
  - 변경 시: 전체 재처리 트리거 (Cloud Workflows 수동 실행)
  - 빈도: 분기 1회 이하 예상 → 자동화 불필요, 수동 트리거로 충분
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

---

## Phase 2 산출물

```
□ Neo4j Professional 전환 완료 [standard.1-3]
□ 전체 데이터 처리 완료 (450K 이력서 + 10K JD)
□ 크롤링 파이프라인 동작 (홈페이지 + 뉴스 + LLM 추출)
□ 크롤링 법적 검토 완료 + 정책 문서 [standard.1-9]
□ CompanyContext 보강 완료 (fill_rate 0.85+ 목표)
□ 품질 평가 리포트 (Gold Test Set 400건)
□ BigQuery 서빙 인터페이스 확정
□ Cloud Workflows 파이프라인 배포 [standard.24]
□ 증분 처리 자동화 (Cloud Scheduler → Workflows)
□ 크롤링 30일 주기 자동화
□ Dead-letter 일일 재처리 자동화
□ Neo4j 주간 백업 자동화 [standard.20]
□ Looker Studio 대시보드 구축
```

---

## Phase 3: 운영 최적화 (별도, 필요 시) — [standard.25]

> **standard.1 변경**: Phase 2-6에 있던 ML Knowledge Distillation을 별도 Phase로 분리.
> 이유: 전체 파이프라인 품질 검증도 안 된 시점에 ML distillation은 시기상조 (R-15).
> Phase 2 완료 후 운영 데이터 기반으로 진행하는 것이 합리적.

| # | 작업 | 비고 |
|---|---|---|
| 3-1 | scope_type 분류기 학습 (KLUE-BERT) | F1 > 75% 목표 |
| 3-2 | seniority 분류기 학습 | F1 > 80% 목표 |
| 3-3 | Confidence 기반 라우팅 (ML > 0.85 → ML, else → LLM) | LLM 비용 절감 |
| 3-4 | 파이프라인 성능 튜닝 (Cloud Run Job 사양 최적화) | |
| 3-5 | Prompt 최적화 (운영 데이터 기반 A/B 테스트) | |

### 진입 조건

- Phase 2 품질 평가 완료 (Gold Test Set 기준 최소 기준 충족)
- 운영 데이터 최소 3개월 축적
- LLM 비용이 월 $50 이상으로 비용 절감 ROI 확인
