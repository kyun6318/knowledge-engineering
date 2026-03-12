# Phase 0: 사전 준비 + 환경 구성 + PoC (Week 0~1)

> **목적**: 사전 준비를 병렬 진행하고, Week 1에서 GCP 환경 + LLM PoC + 크롤링 실현 가능성을 검증.
>
> **v1 대비 변경**:
> - Gemini Flash Batch 대안 사전 검증 추가 (Week 0)
> - 서비스 계정 3개 분리 (최소 권한 원칙)
> - 크롤링 Go/No-Go: 법무 미결이어도 DB-only로 Phase 1 진행 가능
>
> **인력**: DE 1명 + MLE 1명 풀타임
> **산출물**: GCP 환경 완성 + PoC 결과 + Go/No-Go 판정

---

## Week 0: 사전 준비 (27주 카운트에 미포함, 지금 즉시)

> 아래 항목은 모두 **병렬 실행** 가능. Phase 0 시작 전에 완료하거나 병행.

### Blocking #1: Anthropic Batch API Quota 확인

```
□ Anthropic 콘솔(console.anthropic.com)에서 즉시 확인:
  ├─ 현재 Tier → 결과: Tier ___
  ├─ Claude Haiku 4.5 Batch API 지원 여부 → 결과: ___
  ├─ 동시 활성 batch 수 한도 → 결과: ___
  ├─ 일일 요청 한도(RPD) → 결과: ___
  └─ Batch 결과 보관 기간 (현재 29일) → 결과: ___

□ 필요 시 Tier 업그레이드 요청 (1~2주 소요 감안)

확인 결과별 대응:
  - 동시 ≥ 10: 계획대로 진행
  - 동시 5~9: Phase 2 8주 범위 내 처리 가능
  - 동시 ≤ 4: ★ Gemini Flash 병행 또는 chunk 크기 확대
```

### Blocking #1-B: Gemini Flash Batch 대안 검증 (★ v2 신규)

```
□ Gemini Flash 1.5/2.0 Batch API 호출 테스트 (10건)
  ├─ 동일 이력서 10건으로 Anthropic vs Gemini 품질 비교
  ├─ 비용 비교 (건당 단가)
  ├─ 응답 시간 비교
  └─ JSON 출력 안정성 비교

→ Anthropic 동시 ≤ 4일 경우, Gemini Flash 병행 전략 확정
→ 병행 시: 간단한 프롬프트(work_style)는 Gemini, 복잡한 프롬프트(experience_extract)는 Anthropic
```

### Blocking #2: 법무 PII 검토

```
□ 법무팀에 PII 처리 방침 검토 요청
  - 이력서 PII를 외부 LLM API에 마스킹 전송 가능 여부
  - Anthropic Data Processing Agreement 검토

→ 결론 대기 중에도 마스킹 적용 상태로 진행
→ 법무 허용 판정 시 마스킹 제거 옵션 적용
```

### Blocking #3: 크롤링 법적 검토

```
□ 법무팀에 크롤링 법적 검토 요청
  - 채용 사이트 크롤링의 저작권법/정보통신망법 적합성
  - 이용약관 위반 가능성
  - 크롤링 데이터의 LLM 입력 활용 시 법적 이슈

★ v2 변경: 법무 결론 전에도 DB-only MVP로 Phase 1 진행 가능
  - 크롤링 허용 시: Phase 1에서 크롤링 파이프라인 포함
  - 크롤링 불허 시: DB 데이터만으로 MVP, 크롤링은 대체 전략 수립
  - 대체 데이터 소스 사전 식별: 파트너사 API, 데이터 구매 등
```

### 기존 데이터 확보

```
□ 기존 이력서 DB 데이터 샘플 100건 확보
  ├─ 필드 구조 확인 (어떤 컬럼이 있는지)
  ├─ 텍스트 필드 내용 확인 (구조화 수준)
  └─ BigQuery 또는 다른 DB에서 export
```

### 사전 준비 체크리스트

```
□ Anthropic Batch API quota 확인 완료
□ ★ Gemini Flash Batch 대안 테스트 완료
□ 법무 PII 검토 요청 완료
□ 크롤링 법적 검토 요청 완료
□ 크롤링 대상 사이트 3곳 사전 조사 완료 (법무 허용 전제)
□ ★ 크롤링 불허 시 대체 데이터 소스 목록 작성
□ 기존 DB 샘플 100건 확보
□ GCP 프로젝트 생성 (또는 기존 프로젝트 사용 확인)
```

---

## Week 1: Phase 0 — 환경 + PoC (1주)

### DE 담당 (Day 1~5)

#### Day 1-2: GCP 환경 구성

```bash
# 프로젝트 설정
gcloud config set project graphrag-kg

# API 활성화
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  bigquery.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com

# ★ v2: 서비스 계정 3개 분리 (최소 권한 원칙)

# 1. 크롤링 전용
gcloud iam service-accounts create kg-crawling \
  --display-name="KG Crawling Service Account"
SA_CRAWL=kg-crawling@graphrag-kg.iam.gserviceaccount.com
for ROLE in storage.objectCreator bigquery.dataEditor \
  secretmanager.secretAccessor run.invoker; do
  gcloud projects add-iam-policy-binding graphrag-kg \
    --member="serviceAccount:$SA_CRAWL" --role="roles/$ROLE"
done

# 2. 처리/추출 전용
gcloud iam service-accounts create kg-processing \
  --display-name="KG Processing Service Account"
SA_PROC=kg-processing@graphrag-kg.iam.gserviceaccount.com
for ROLE in storage.objectViewer storage.objectCreator \
  bigquery.dataEditor aiplatform.user \
  secretmanager.secretAccessor run.invoker; do
  gcloud projects add-iam-policy-binding graphrag-kg \
    --member="serviceAccount:$SA_PROC" --role="roles/$ROLE"
done

# 3. Graph 적재 전용
gcloud iam service-accounts create kg-loading \
  --display-name="KG Loading Service Account"
SA_LOAD=kg-loading@graphrag-kg.iam.gserviceaccount.com
for ROLE in storage.objectViewer bigquery.dataViewer \
  secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding graphrag-kg \
    --member="serviceAccount:$SA_LOAD" --role="roles/$ROLE"
done

# Artifact Registry
gcloud artifacts repositories create kg-pipeline \
  --repository-format=docker \
  --location=asia-northeast3

# GCS
gcloud storage buckets create gs://graphrag-kg-data \
  --location=asia-northeast3 \
  --uniform-bucket-level-access
gcloud storage buckets update gs://graphrag-kg-data --versioning

# BigQuery
bq mk --dataset --location=asia-northeast3 graphrag_kg
```

#### Day 2: BigQuery 테이블 생성

> v1과 동일 (resume_raw, resume_processed, processing_log, batch_tracking, parse_failure_log).
> ★ v2 추가: quality_metrics 테이블

```sql
-- ★ v2 신규: 자동 품질 메트릭 테이블
CREATE TABLE graphrag_kg.quality_metrics (
  id STRING NOT NULL,
  pipeline STRING NOT NULL,
  metric_name STRING NOT NULL,
  metric_value FLOAT64,
  sample_size INT64,
  confidence_interval STRING,
  measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

#### Day 2-3: Neo4j + 인프라

```
□ Neo4j AuraDB Free 인스턴스 생성
  - 리전: asia-northeast1 (도쿄)
  - 연결 URI + password → Secret Manager 등록

□ APOC Extended 지원 여부 즉시 확인
  - AuraDB Free에서 APOC 사용 가능 여부 → 결과: ___
  - 마이그레이션 방법 분기에 영향:
    방법 A (APOC 가능 시): CALL apoc.export.json.all(...)
    방법 B (APOC 불가 시): Cypher UNWIND + CSV export → GCS
    방법 C (APOC 불가 시): AuraDB Console 스냅샷 (Professional 기본 제공)

□ max concurrent connections 확인
  - AuraDB Free: 일반적으로 3~5 concurrent connections
  - 확인 방법: Neo4j Browser에서 CALL dbms.showConnections()
  - 또는 Neo4j AuraDB 문서에서 플랜별 한도 확인
  - 결과에 따라 Graph 적재 tasks 수 조정:
    max ≤ 5:  tasks=3, kg-embedding tasks=4
    max ≤ 10: tasks=5, kg-embedding tasks=5
    Professional 전환 후: 플랜에 따라 tasks 상향

□ Graph 스키마 적용 (v1과 동일)

□ Vector Index 설정:
  CREATE VECTOR INDEX chapter_embedding FOR (c:Chapter)
  ON (c.embedding)
  OPTIONS {indexConfig: {
    `vector.dimensions`: 768,              ← ★ 768d 통일
    `vector.similarity_function`: 'cosine' ← ★ similarity_function (v1 오류 수정)
  }};
```

### Neo4j Connection Pool 관리 코드

```python
# src/shared/neo4j_pool.py
import time
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

def create_driver_with_retry(uri, auth, max_retries=3):
    """Connection pool 부족 시 exponential backoff 재시도"""
    for attempt in range(max_retries):
        try:
            driver = GraphDatabase.driver(
                uri, auth=auth,
                max_connection_pool_size=2,  # task당 최소한의 pool
                connection_acquisition_timeout=30,
            )
            driver.verify_connectivity()
            return driver
        except ServiceUnavailable:
            wait = min(2 ** attempt, 30)
            print(f"Neo4j connection failed, retry in {wait}s (attempt {attempt+1}/{max_retries})")
            time.sleep(wait)
    raise ServiceUnavailable("Neo4j connection failed after max retries")
```

#### Day 3-5: 크롤링 대상 사이트 구조 분석 (법무 허용 시에만)

> v1과 동일. 법무 미결 시 DE는 BigQuery 스키마/인프라 보강에 시간 활용.

---

### MLE 담당 (Day 1~5)

> v1과 동일 (DB 프로파일링, LLM 추출 PoC 20건, Embedding 모델 선택, Batch API 실측).
> Embedding: text-embedding-005 (768d) 확정.

---

### 공동: Go/No-Go 판정 (Day 5)

| 기준 | 통과 조건 | 미달 시 대응 |
|------|-----------|-------------|
| LLM 추출 품질 | 20건 scope_type 정확도 > 60% | 프롬프트 재설계 + 3일 추가 |
| DB 데이터 품질 | 텍스트 필드 비어있는 비율 < 20% | structured_fields 활용으로 전환 |
| Batch API quota | 계획 실행 최소 조건 확인 | 동시 3 batch + Gemini Flash 대비 |
| 크롤링 가능성 | ★ **법무 미결이어도 DB-only Go** | 크롤링은 법무 결론 후 추가 |
| Embedding 분별력 | similar > 0.7, dissimilar < 0.4 | text-embedding-005(768d) 기본값 |

---

## Phase 0 산출물

```
□ GCP 환경 구성 완료 (API, ★ 서비스 계정 3개, GCS, BigQuery, Secret Manager)
□ Neo4j AuraDB Free + 스키마 + Vector Index (768d)
□ Neo4j APOC Extended 지원 여부 확인 결과
□ Neo4j max concurrent connections 확인 결과 + tasks 수 결정
□ BigQuery 테이블 5개 + ★ quality_metrics
□ DB 데이터 프로파일 리포트 (100건)
□ LLM 추출 PoC 결과 (20건) + 품질 측정
□ Embedding 모델 확정 (text-embedding-005, 768d)
□ Batch API 응답 시간 실측 (3~5건)
□ ★ Gemini Flash Batch 대안 테스트 결과
□ 크롤링 대상 사이트 구조 분석 (법무 허용 시)
□ Go/No-Go 판정 문서

--- Phase 2 사전 조사 (v1과 동일, 우선순위 낮음) ---
□ 이력서 원본 파일 형식 분포 사전 조사
□ HWP 파싱 3방법 사전 조사
□ Document AI 프로세서 사전 생성

--- Phase 3 사전 준비 (v1과 동일) ---
□ NICE DB 접근 계약 상태 확인
```
