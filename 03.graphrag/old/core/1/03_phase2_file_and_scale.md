# Phase 2: 파일 이력서 통합 + 전체 처리 (6주, Week 7-12)

> **목적**: Phase 1의 DB 텍스트 기반 Graph에 파일 이력서(PDF/DOCX/HWP)를 통합하고,
> 전체 450K 이력서를 처리하여 에이전트의 검색 범위를 전체 후보자 풀로 확대.
>
> **데이터 확장**: DB 텍스트 1,000건 → **전체 450K** (DB + 파일 소스 통합)
> **에이전트 역량 변화**: 1,000건 검색 → **450K 전체 후보자 검색**
>
> **인력**: DE 1명 + MLE 1명 풀타임

---

## 2-0. 코드 리팩토링 + 파일 파싱 PoC (1주) — Week 7

### Phase 1 PoC → 프로덕션 코드 전환

| Task ID | 과제 | 담당 | 산출물 | 일정 |
|---------|------|------|--------|------|
| 2-0-1 | Phase 1 PoC 코드 리팩토링 (src/ 모듈 구조) | DE | `src/` 디렉토리 구조 | Mon-Tue |
| 2-0-2 | Phase 0/1 의사결정 코드 반영 (재설계 결과) | MLE | 업데이트된 모듈 | Tue-Wed |
| 2-0-3 | HWP 파싱 PoC (3가지 방법 테스트) | DE | PoC 코드 + 선택 결과 (CER ≤ 0.15) | Wed-Thu |
| 2-0-4 | PDF/DOCX 파싱 방법 확정 | DE | 최종 선택 (Document AI vs pymupdf/python-docx) | Thu |
| 2-0-5 | 프로덕션 파싱 모듈 초안 | DE | `src/parsers/` 초안 | Thu-Fri |
| 2-0-6 | 테스트 세트 구성 (각 포맷 100건) | MLE | `tests/fixtures/` 100×3 파일 | Fri |

### 프로젝트 구조 (Phase 2-3 전체 적용)

```
src/
├── parsers/              # PDF, DOCX, HWP 파서
│   ├── pdf_parser.py     # PDF 파싱 (Document AI 또는 pymupdf)
│   ├── docx_parser.py    # DOCX 파싱 (python-docx)
│   ├── hwp_parser.py     # HWP 파싱 (LibreOffice/pyhwp/Gemini 멀티모달)
│   └── __init__.py
├── splitters/            # 섹션 분할, 경력 블록 분리
│   ├── section_splitter.py    # Rule-based 섹션 분할
│   ├── career_block_splitter.py  # 경력 블록 분리
│   └── __init__.py
├── pii/                  # PII 마스킹 (offset mapping 보존)
│   ├── masker.py         # PII 마스킹 (offset 기록)
│   └── __init__.py
├── dedup/                # SimHash 중복 제거
│   ├── simhash.py        # SimHash 계산
│   ├── dedup_manager.py  # 대규모 중복 제거
│   └── __init__.py
├── extractors/           # Rule 추출, LLM 추출
│   ├── rule_extractor.py      # 정규식 기반 추출
│   ├── llm_extractor.py       # LLM 기반 추출
│   └── __init__.py
├── models/               # Pydantic 모델 (Candidate)
│   ├── candidate.py      # Candidate 스키마
│   ├── parsed_document.py  # ParsedDocument 스키마
│   └── __init__.py
├── shared/               # 공유 유틸
│   ├── llm_parser.py         # LLM API 호출 (재시도/토큰 계산)
│   ├── checkpoint.py         # 진행 상태 체크포인트
│   ├── neo4j_pool.py         # Neo4j 커넥션 풀
│   ├── gcs_manager.py        # GCS 파일 연동
│   └── __init__.py
├── crawlers/             # Phase 1 크롤러 (유지)
│   ├── linkedin_crawler.py
│   ├── github_crawler.py
│   └── __init__.py
├── batch/                # Batch API (유지)
│   ├── batch_submitter.py    # Batch 요청 생성 및 제출
│   ├── batch_poller.py       # 결과 수집
│   └── __init__.py
├── graph/                # Neo4j 적재 (유지)
│   ├── graph_loader.py       # 그래프 적재 엔진
│   ├── embedding_manager.py  # 임베딩 관리
│   └── __init__.py
├── parse_resumes.py      # 파싱 Cloud Run Job 진입점
├── dedup_resumes.py      # 중복 제거 Cloud Run Job 진입점
├── process_batch.py      # Batch API 처리
├── load_graph.py         # 그래프 적재
└── requirements.txt      # 의존성 (pdf2image, pymupdf, python-docx, pyhwp, google-cloud-documentai 등)
```

---

## 2-1. 파일 파싱 + 전처리 확장 (2주) — Week 8-9

### 태스크 구성

| Task ID | 과제 | 담당 | 산출물 | 일정 |
|---------|------|------|--------|------|
| 2-1-1 | PDF/DOCX 파서 모듈 (DE) | DE | `src/parsers/pdf_parser.py`, `src/parsers/docx_parser.py` | Week 8 Mon-Wed |
| 2-1-2 | HWP 파서 모듈 (Phase 2-0 PoC 결과 반영) | DE | `src/parsers/hwp_parser.py` | Week 8 Wed-Fri |
| 2-1-3 | 섹션 분할기 (Rule-based) | MLE | `src/splitters/section_splitter.py` | Week 8 Mon-Thu |
| 2-1-4 | 경력 블록 분리기 | MLE | `src/splitters/career_block_splitter.py` | Week 8 Thu-Fri |
| 2-1-5 | PII 마스킹 확장 (offset mapping 보존) | MLE | `src/pii/masker.py` (offset 기록 추가) | Week 9 Mon-Tue |
| 2-1-6 | SimHash 중복 제거 확장 | DE | `src/dedup/dedup_manager.py` (대규모 처리) | Week 9 Tue-Wed |
| 2-1-7 | JD 파서 + 섹션 분할 (Phase 3 사전 준비) | DE | `src/parsers/jd_parser.py`, `src/splitters/jd_splitter.py` | Week 9 Wed-Thu |
| 2-1-8 | 기술 사전 (2,000개) + 회사 사전 확장 | DE, MLE | `reference/tech_dict.json`, `reference/company_dict.json` | Week 9 Thu-Fri |
| 2-1-9 | Docker 이미지 빌드 + Job 등록 | DE | Dockerfile, 등록된 Cloud Run Jobs | Week 9 Fri |

### Week 8 일정 상세 (Mon-Fri)

```
Monday (4일):
  09:00-10:30 - 2-1-3 시작 (섹션 분할기 구조 설계)
  10:30-12:00 - 2-1-1 시작 (PDF/DOCX 파서 구현 시작)
  13:00-17:00 - 2-1-1 진행 (파서 테스트 케이스)

Tuesday (2일):
  09:00-12:00 - 2-1-1 완료 (PDF/DOCX 파서)
  13:00-17:00 - 2-1-3 진행 (섹션 분할 룰 정의)

Wednesday (1일):
  09:00-12:00 - 2-1-3 진행 (섹션 분할 테스트)
  13:00-17:00 - 2-1-2 시작 (HWP 파서, Phase 2-0 결과 반영)

Thursday (1일):
  09:00-12:00 - 2-1-2 진행 (HWP 파서 테스트)
  13:00-15:00 - 2-1-3 완료 (섹션 분할기)
  15:00-17:00 - 2-1-4 시작 (경력 블록 분리)

Friday (1일):
  09:00-12:00 - 2-1-4 진행 (경력 블록 테스트)
  13:00-17:00 - 2-1-2 완료 (HWP 파서)
```

### Week 9 일정 상세 (Mon-Fri)

```
Monday (2일):
  09:00-12:00 - 2-1-4 완료 (경력 블록 분리기)
  13:00-17:00 - 2-1-5 시작 (PII 마스킹 확장)

Tuesday (2일):
  09:00-12:00 - 2-1-5 진행 (offset mapping 구현)
  13:00-17:00 - 2-1-6 시작 (SimHash 중복 제거)

Wednesday (1일):
  09:00-12:00 - 2-1-5 완료 (PII 마스킹)
  13:00-17:00 - 2-1-6 진행 (대규모 중복 제거 최적화)

Thursday (1일):
  09:00-12:00 - 2-1-6 완료 (중복 제거)
  13:00-17:00 - 2-1-7 시작 (JD 파서)

Friday (1일):
  09:00-12:00 - 2-1-7 진행 (JD 파서, 섹션 분할)
  13:00-15:00 - 2-1-8 시작 (기술/회사 사전)
  15:00-17:00 - 2-1-9 준비 (Dockerfile)
```

### Cloud Run Jobs 등록 명령어

```bash
# 환경 변수 설정
PROJECT_ID="graphrag-kg"
REGION="asia-northeast3"
IMAGE="asia-northeast3-docker.pkg.dev/$PROJECT_ID/kg-pipeline/kg-pipeline:latest"
SA="kg-pipeline@$PROJECT_ID.iam.gserviceaccount.com"
BUCKET="graphrag-kg-data"

# 파싱 Job (50개 병렬 task)
gcloud run jobs create kg-parse-resumes \
  --image=$IMAGE \
  --command="python,src/parse_resumes.py" \
  --tasks=50 \
  --max-retries=2 \
  --cpu=2 \
  --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=$REGION \
  --set-env-vars="GCS_BUCKET=$BUCKET,BATCH_SIZE=100"

# 중복 제거 Job (단일 task, 시간 소요)
gcloud run jobs create kg-dedup-resumes \
  --image=$IMAGE \
  --command="python,src/dedup_resumes.py" \
  --tasks=1 \
  --max-retries=1 \
  --cpu=4 \
  --memory=8Gi \
  --task-timeout=7200 \
  --service-account=$SA \
  --region=$REGION \
  --set-env-vars="GCS_BUCKET=$BUCKET"

# 추출 Job (20개 병렬 task)
gcloud run jobs create kg-extract-candidates \
  --image=$IMAGE \
  --command="python,src/extract_candidates.py" \
  --tasks=20 \
  --max-retries=2 \
  --cpu=2 \
  --memory=4Gi \
  --task-timeout=1800 \
  --service-account=$SA \
  --region=$REGION \
  --set-env-vars="GCS_BUCKET=$BUCKET"
```

### Job 실행 (Phase 2-3 처리 시작)

```bash
# 파싱 Job 실행
gcloud run jobs execute kg-parse-resumes \
  --region=$REGION \
  --wait

# 중복 제거 Job 실행
gcloud run jobs execute kg-dedup-resumes \
  --region=$REGION \
  --wait

# 추출 Job 실행
gcloud run jobs execute kg-extract-candidates \
  --region=$REGION \
  --wait
```

---

## 2-2. Neo4j Professional 전환 (1일) — Week 10 시작

### 1단계: Professional 인스턴스 생성

```bash
# Neo4j Aura에서 Professional 인스턴스 생성 (수동 UI)
# 사양: 4GB RAM, 16GB Storage, asia-northeast1
# 생성 후 자격 증명 메모

NEO4J_URI="neo4j+s://..."  # Aura에서 제공
NEO4J_USER="neo4j"
NEO4J_PASSWORD="..."       # Aura에서 제공

# Secret Manager에 저장
echo -n "$NEO4J_PASSWORD" | gcloud secrets create neo4j-password \
  --replication-policy="automatic"

gcloud secrets create neo4j-uri --data-file=- <<< "$NEO4J_URI"
```

### 2단계: Phase 1 데이터 마이그레이션 (방법 3가지)

#### 방법 A: APOC (빠름, 권장)

```bash
# Community → Professional 직접 연결 불가능하므로
# 먼저 GCS로 export 후 Professional으로 import

# 1) Community 인스턴스에서 export (APOC)
# cypher-shell에서 실행:
CALL apoc.export.json.all("gs://graphrag-kg-backup/neo4j-export.json", {});

# 2) Professional 인스턴스에서 import
CALL apoc.load.json("gs://graphrag-kg-backup/neo4j-export.json") YIELD value
UNWIND value as record
CREATE (n) SET n = record;
```

#### 방법 B: CSV Export/Import (안정적)

```bash
# Community에서 CSV로 export
cypher-shell -u neo4j -p $OLD_PASSWORD -a $OLD_URI << 'EOF'
// Node export
CALL apoc.export.csv.all("gs://graphrag-kg-backup/nodes.csv", {});
// Relationship export
CALL apoc.export.csv.all("gs://graphrag-kg-backup/rels.csv", {});
EOF

# Professional에서 import (Cypher 스크립트)
# import_csv.cypher 파일 생성 후 실행
```

#### 방법 C: 재적재 (가장 안정적, ~10분)

```bash
# Phase 1 처리한 모든 CandidateContext를 BigQuery에서 조회
# 다시 Graph Load (src/load_graph.py) 실행
# 소요 시간: ~10분 (450K Node, 2M Relationship)

# BigQuery에서 CandidateContext 조회 후 재적재
python src/load_graph.py \
  --neo4j-uri=$NEO4J_URI \
  --neo4j-user=$NEO4J_USER \
  --gcs-bucket=graphrag-kg-data \
  --mode=full-reload
```

### 3단계: Secret Manager 연결 정보 업데이트

```bash
# 기존 Secret 업데이트
gcloud secrets versions add neo4j-uri --data-file=- <<< "$NEW_NEO4J_URI"
gcloud secrets versions add neo4j-password --data-file=- <<< "$NEW_NEO4J_PASSWORD"

# Cloud Run 서비스에서 마운트 확인
gcloud run services update kg-batch-api \
  --update-env-vars="NEO4J_URI=$NEW_NEO4J_URI" \
  --region=$REGION
```

### 4단계: 연결 테스트 + Constraint/Vector Index 재생성

```python
# src/shared/neo4j_pool.py - 연결 테스트
from neo4j import GraphDatabase
import time

def create_driver_with_retry(uri, auth, max_retries=3):
    """Neo4j 연결 재시도 로직"""
    for attempt in range(max_retries):
        try:
            driver = GraphDatabase.driver(
                uri, auth=auth,
                max_connection_pool_size=2,
                connection_acquisition_timeout=30,
            )
            driver.verify_connectivity()
            print(f"✓ Neo4j 연결 성공: {uri}")
            return driver
        except Exception as e:
            wait = min(2 ** attempt, 30)
            print(f"✗ 연결 실패 (시도 {attempt+1}/{max_retries}): {e}")
            print(f"  {wait}초 후 재시도...")
            time.sleep(wait)
    raise RuntimeError("Neo4j 연결 실패 (최대 재시도 초과)")

def setup_constraints_and_indexes(driver):
    """Constraint와 Vector Index 생성"""
    with driver.session() as session:
        # 기존 Constraint (Phase 1에서 생성됨)
        session.run("""
            CREATE CONSTRAINT person_id IF NOT EXISTS
            FOR (n:Person) REQUIRE n.person_id IS UNIQUE
        """)

        session.run("""
            CREATE CONSTRAINT skill_name IF NOT EXISTS
            FOR (n:Skill) REQUIRE n.name IS UNIQUE
        """)

        session.run("""
            CREATE CONSTRAINT role_name IF NOT EXISTS
            FOR (n:Role) REQUIRE n.name IS UNIQUE
        """)

        # Vector Index (Professional 전환 시 재생성)
        session.run("""
            CREATE VECTOR INDEX person_embeddings IF NOT EXISTS
            FOR (n:Person)
            ON n.embedding
            OPTIONS {indexConfig: {
              `vector.dimensions`: 1536,
              `vector.similarity_metric`: 'cosine'
            }}
        """)

        print("✓ Constraint/Index 재생성 완료")

# 연결 테스트
if __name__ == "__main__":
    uri = "neo4j+s://..."  # Secret Manager에서 읽기
    auth = ("neo4j", "...")

    driver = create_driver_with_retry(uri, auth)
    setup_constraints_and_indexes(driver)
    driver.close()
    print("✓ Neo4j Professional 전환 완료")
```

### 5단계: Connection Pool 한도 확인

```python
# Professional 인스턴스 스펙:
# - 최대 동시 연결: 5~10개 (Aura 플랜에 따라 다름)
# - 권장 max_connection_pool_size: 2
# - Cloud Run Job tasks 결정: ≤ (max_connections / 2)

# 예시:
# Professional (max 10 connections) → tasks = 5
# 만약 tasks=8로 설정하면 일부 task가 연결 대기

# 실제 Cloud Run Job task 수 결정
NEO4J_MAX_CONNECTIONS=10
RECOMMENDED_TASKS=$((NEO4J_MAX_CONNECTIONS / 2))
echo "권장 tasks 수: $RECOMMENDED_TASKS"
```

---

## 2-3. 전체 450K Batch 처리 (3주) — Week 10-12

### 처리 흐름도

```
GCS 이력서 원본 (150GB)
      │
      ├─ parsed/ (JSON)      ← 2-1-1,2 파싱 결과
      │
      ▼
BigQuery resume_text 테이블 통합
      │
      ├─ DB 기존 데이터 (1,000건)
      ├─ PDF 파싱 결과 (200K건)
      ├─ DOCX 파싱 결과 (150K건)
      └─ HWP 파싱 결과 (100K건)
      │
      ▼
Batch API 제출 (450 chunks × 1,000건)
      │
      ├─ 동시 10 batch 진행
      ├─ 라운드당 약 6~24시간
      └─ 완료 건부터 즉시 처리
      │
      ▼
CandidateContext 생성 (BigQuery contexts/candidate/)
      │
      ▼
Neo4j Graph 적재 + Embedding (병렬)
      │
      ▼
최종 450K Person Node + 2.25M Relationship
```

### 처리 시간 계산

```
총 이력서 수: 450,000건
Batch API chunk 크기: 1,000건/chunk
필요한 chunk 수: 450,000 / 1,000 = 450 chunk

동시 실행: 10 batch (API 한도 고려)
라운드 수: 450 / 10 = 45 라운드

라운드당 소요 시간 (3가지 시나리오):

시나리오 1 (낙관): 라운드당 6시간
  - 45 라운드 × 6h = 270 시간
  - = 11.25일 (연속 실행)

시나리오 2 (기본): 라운드당 12시간 (API 대기 시간)
  - 45 라운드 × 12h = 540 시간
  - = 22.5일 (연속 실행)

시나리오 3 (비관): 라운드당 24시간 (토큰/할당량 한도)
  - 45 라운드 × 24h = 1,080 시간
  - = 45일 (연속 실행)

Week 10-12 (21일) 내 완료 가능한 처리량:

낙관 (6h): 21 / 11.25 = 1.87배 → 450K × 1.87 = 840K (100% 초과)
기본 (12h): 21 / 22.5 = 0.93배 → 450K × 0.93 = 418K (93%)
비관 (24h): 21 / 45 = 0.47배 → 450K × 0.47 = 211K (47%)

실패 재시도: +2일
결과 수집: +2일
Graph 적재: +3일 (동시 진행 가능)
버퍼: +3일

총 실제 필요: ~11일 (낙관) ~ 45일 (비관)
Week 10-12 범위: 21일 (상황에 따라 부분 완료 가능)
```

### 3-시나리오 타임라인

| 시나리오 | 라운드당 | 총 소요 | Week 12 완료량 | 에이전트 상태 |
|----------|---------|--------|-------------|------------|
| **낙관** (6h/라운드) | 11.25일 | 450K 전량 | **100% (450K)** | 전체 KG 활용 가능 |
| **기본** (12h/라운드) | 22.5일 | 418K | **~250K (55%)** | 부분 활용, 수주 추가 |
| **비관** (24h/라운드) | 45일 | 211K | **~100K (22%)** | 기본 검색만, 장기화 |

### 처리 모니터링 (Python 스크립트)

```python
# src/batch/batch_monitor.py - 실시간 모니터링
import time
from google.cloud import bigquery, storage
from datetime import datetime, timedelta

def monitor_batch_progress(bucket_name="graphrag-kg-data"):
    """Batch 처리 진행 상황 실시간 모니터링"""

    bq = bigquery.Client()
    gcs = storage.Client()

    while True:
        # BigQuery 테이블 상태 조회
        query = """
        SELECT
          COUNT(*) as total_chunks,
          SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
          SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
          SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending,
          MAX(completed_at) as last_completion
        FROM graphrag_kg.chunk_status
        """

        result = bq.query(query).result().to_dataframe()

        total = result.iloc[0]['total_chunks']
        completed = result.iloc[0]['completed']
        failed = result.iloc[0]['failed']
        pending = result.iloc[0]['pending']
        last_completion = result.iloc[0]['last_completion']

        completion_rate = (completed / total * 100) if total > 0 else 0

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        print(f"  총 Chunk: {int(total)}")
        print(f"  완료: {int(completed)} ({completion_rate:.1f}%)")
        print(f"  실패: {int(failed)}")
        print(f"  대기: {int(pending)}")
        print(f"  마지막 완료: {last_completion}")
        print()

        # 매 30분마다 확인
        time.sleep(1800)

def estimate_completion_time(completed, total, time_elapsed_hours):
    """완료 시간 추정"""
    if completed == 0:
        return None

    avg_time_per_chunk = time_elapsed_hours / completed
    remaining_chunks = total - completed
    estimated_remaining_hours = avg_time_per_chunk * remaining_chunks

    estimated_completion = datetime.now() + timedelta(hours=estimated_remaining_hours)

    return {
        'estimated_completion': estimated_completion,
        'remaining_hours': estimated_remaining_hours,
        'avg_time_per_chunk_hours': avg_time_per_chunk
    }

if __name__ == "__main__":
    monitor_batch_progress()
```

### BigQuery Chunk Status 추적 테이블

```sql
-- 생성: Week 10 초반 (2-3 처리 시작 전)

CREATE TABLE IF NOT EXISTS graphrag_kg.chunk_status (
  chunk_id STRING NOT NULL,           -- "chunk_0000", "chunk_0001", ...
  source_type STRING NOT NULL,        -- 'DB' | 'PDF' | 'DOCX' | 'HWP'
  pipeline STRING NOT NULL,           -- 'extraction' | 'embedding'
  status STRING NOT NULL,             -- 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  total_items INT64,                  -- 1000 (보통)
  completed_items INT64,              -- 0~1000
  failed_items INT64,                 -- 0~1000
  batch_request_id STRING,            -- Batch API 요청 ID
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  error_message STRING,
  retry_count INT64,
  PRIMARY KEY (chunk_id)
) PARTITION BY DATE(created_at)
CLUSTER BY source_type, status;

-- 인덱스
CREATE INDEX idx_chunk_status ON graphrag_kg.chunk_status(status, source_type);
CREATE INDEX idx_chunk_started ON graphrag_kg.chunk_status(started_at DESC);
```

### GCS 데이터 구조 확장 (Phase 2)

```
gs://graphrag-kg-data/
│
├── raw/
│   ├── resumes/                   ← Phase 2 신규: 이력서 원본 (150GB)
│   │   ├── pdf/                   (70GB, ~200K 파일)
│   │   ├── docx/                  (50GB, ~150K 파일)
│   │   └── hwp/                   (30GB, ~100K 파일)
│   │
│   └── jds/                       ← Phase 3 사전 업로드: JD 원본
│       ├── pdf/
│       └── docx/
│
├── reference/
│   ├── NICE_DB_snapshot.json      (최신 버전 유지)
│   ├── tech_dict.json             (2,000개, Phase 2-1-8)
│   ├── company_dict.json          (10K개, 확장)
│   ├── role_dict.json             (1K개)
│   └── ...
│
├── parsed/                         ← Phase 2 신규: 파싱 결과
│   ├── pdf/parsed.jsonl           (200K 레코드)
│   ├── docx/parsed.jsonl          (150K 레코드)
│   └── hwp/parsed.jsonl           (100K 레코드)
│
├── dedup/                          ← Phase 2 신규: 중복 제거 결과
│   ├── candidates_dedup.jsonl     (450K 중복 제거 결과)
│   └── dedup_mapping.json         (매핑 정보)
│
├── contexts/
│   ├── candidate/                 (CandidateContext JSON)
│   │   └── contexts_YYYYMMDD.jsonl  (누적 생성)
│   │
│   └── jd/                        ← Phase 3 사전 생성
│       └── contexts_YYYYMMDD.jsonl
│
├── batch-api/
│   ├── requests/                  (요청 JSON)
│   │   └── chunk_XXXX_request.json
│   │
│   ├── responses/                 (응답 JSON)
│   │   └── chunk_XXXX_response.json
│   │
│   └── results/                   (최종 결과)
│       └── extraction_results_YYYYMMDD.jsonl
│
├── prompts/
│   ├── v1_extraction_prompt.txt
│   ├── v2_extraction_prompt.txt
│   └── ...
│
├── dead-letter/                   (처리 실패 건)
│   ├── parsing/
│   ├── extraction/
│   └── loading/
│
├── backups/
│   └── neo4j_export_YYYYMMDD.json
│
└── logs/
    ├── parsing_YYYYMMDD.log
    ├── batch_YYYYMMDD.log
    └── loading_YYYYMMDD.log
```

### 업무 시간 외 자동화 SLA

```
=== 업무 시간 (09:00~18:00) ===

CRITICAL (API 한도 도달, DB 연결 실패):
  - 대응 시간: 즉시 (30분 내)
  - 담당: DE 또는 MLE
  - 조치: Slack 즉시 공지 + 수동 재시작

WARNING (일부 chunk 실패, 재시도 필요):
  - 대응 시간: 2시간 내 확인
  - 담당: 당번자 확인
  - 조치: Dead-letter 분석 후 수동 실행 또는 자동 재시도

INFO (정상 진행):
  - 로그 기록만 (자동)
  - 매 라운드 완료 시 Slack 알림

=== 업무 시간 외 (18:00~09:00) ===

자동화 우선:
  1. kg-batch-poll (Cloud Scheduler, 30분 주기)
     └─ 완료된 batch 결과 수집
     └─ failed batch 자동 재시도 (max 2회)
     └─ dead-letter 누적

  2. kg-dead-letter-retry (Cloud Scheduler, 일 1회 자정)
     └─ Dead-letter 재분석
     └─ 복구 가능한 건 자동 재시도
     └─ 복구 불가 건 로그 및 Slack 알림

Manual intervention (다음 업무일 아침 대응):
  - Batch 결과 만료 24h 이내 → 수동 실행
  - API 할당량 한도 도달 → 일정 조정
  - DB 연결 지속 실패 → Neo4j 재시작

SLA 위반 방지:
  - 진행 중인 chunk 상태 캐싱 (Firestore)
  - 완료된 결과 즉시 저장 (GCS + BigQuery)
  - 자동화 실패 시 로그 수집 후 다음 업무일 검토
```

### Batch 처리 자동화 스크립트

```python
# src/batch/batch_auto_retry.py - Cloud Scheduler 실행 대상

import logging
from google.cloud import bigquery, storage, tasks_v2
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_failed_chunks(project_id="graphrag-kg"):
    """Failed chunk 자동 재시도"""

    bq = bigquery.Client(project=project_id)

    # Failed chunk 조회 (max 5개, 타임아웃 제외)
    query = """
    SELECT chunk_id, source_type, error_message, retry_count
    FROM graphrag_kg.chunk_status
    WHERE status = 'FAILED'
      AND retry_count < 2
      AND error_message NOT LIKE '%TIMED_OUT%'
    LIMIT 5
    ORDER BY completed_at ASC
    """

    failed_chunks = bq.query(query).result()

    retry_count = 0
    for row in failed_chunks:
        chunk_id = row['chunk_id']
        error = row['error_message']

        logger.info(f"Retrying {chunk_id}: {error}")

        # Batch API 재제출 (상세 구현 생략)
        # submit_batch_chunk(chunk_id)

        # Status 업데이트
        bq.query(f"""
            UPDATE graphrag_kg.chunk_status
            SET status = 'PENDING',
                retry_count = retry_count + 1,
                started_at = CURRENT_TIMESTAMP()
            WHERE chunk_id = '{chunk_id}'
        """)

        retry_count += 1

    logger.info(f"✓ {retry_count}개 chunk 재시도 완료")
    return retry_count

def collect_completed_results(project_id="graphrag-kg"):
    """완료된 batch 결과 수집"""

    bq = bigquery.Client(project=project_id)

    # COMPLETED 상태 chunk 조회
    query = """
    SELECT chunk_id, batch_request_id
    FROM graphrag_kg.chunk_status
    WHERE status = 'COMPLETED'
      AND completed_at IS NULL  -- 결과 미수집
    """

    completed_chunks = bq.query(query).result()

    collected_count = 0
    for row in completed_chunks:
        chunk_id = row['chunk_id']
        batch_id = row['batch_request_id']

        # Batch API 결과 수집 (상세 구현 생략)
        # response = get_batch_result(batch_id)

        # 결과 저장 (GCS)
        # save_to_gcs(f"batch-api/results/{chunk_id}.json", response)

        # Status 업데이트
        bq.query(f"""
            UPDATE graphrag_kg.chunk_status
            SET completed_at = CURRENT_TIMESTAMP(),
                completed_items = completed_items + 1000
            WHERE chunk_id = '{chunk_id}'
        """)

        collected_count += 1

    logger.info(f"✓ {collected_count}개 chunk 결과 수집 완료")
    return collected_count

if __name__ == "__main__":
    logger.info("=== Batch 자동 처리 시작 ===")

    retry_count = retry_failed_chunks()
    collected = collect_completed_results()

    logger.info(f"재시도: {retry_count}, 수집: {collected}")
```

### Cloud Scheduler 설정

```bash
# Batch 결과 수집 (30분 주기)
gcloud scheduler jobs create pubsub kg-batch-poll \
  --schedule="*/30 * * * *" \
  --topic=kg-batch-poll-trigger \
  --message-body='{"action":"poll_results"}' \
  --time-zone=Asia/Seoul

# Dead-letter 재시도 (일일 자정)
gcloud scheduler jobs create pubsub kg-deadletter-retry \
  --schedule="0 0 * * *" \
  --topic=kg-deadletter-retry-trigger \
  --message-body='{"action":"retry_deadletter"}' \
  --time-zone=Asia/Seoul

# Pub/Sub → Cloud Function 연결 (상세 구현 생략)
```

---

## Phase 2 완료 산출물

```
□ 파일 파싱 모듈 (PDF, DOCX, HWP)
  ├─ src/parsers/pdf_parser.py      ✓ 2-1-1
  ├─ src/parsers/docx_parser.py     ✓ 2-1-1
  ├─ src/parsers/hwp_parser.py      ✓ 2-1-2
  └─ 테스트 케이스 (각 100건)        ✓ 2-0-6

□ 전처리 확장 모듈
  ├─ src/splitters/section_splitter.py          ✓ 2-1-3
  ├─ src/splitters/career_block_splitter.py     ✓ 2-1-4
  ├─ src/pii/masker.py (offset mapping)         ✓ 2-1-5
  ├─ src/dedup/dedup_manager.py                 ✓ 2-1-6
  └─ src/parsers/jd_parser.py (Phase 3 준비)    ✓ 2-1-7

□ 참조 데이터 확장
  ├─ reference/tech_dict.json (2,000개)         ✓ 2-1-8
  ├─ reference/company_dict.json (10K 확장)     ✓ 2-1-8
  └─ reference/role_dict.json                   ✓ 2-1-8

□ 인프라 전환
  ├─ Neo4j Professional 인스턴스 생성            ✓ 2-2
  ├─ Phase 1 데이터 마이그레이션 완료           ✓ 2-2
  ├─ Constraint/Index 재생성                    ✓ 2-2
  ├─ Connection Pool 최적화                     ✓ 2-2
  └─ Docker 이미지 + Job 등록                   ✓ 2-1-9

□ 전체 데이터 처리 (450K 이력서)
  ├─ 파싱 완료: 450K (또는 진행 중)
  ├─ 중복 제거: 450K (또는 진행 중)
  ├─ CandidateContext 생성:
  │   ├─ 낙관: 450K (100%)
  │   ├─ 기본: ~250K (55%)
  │   └─ 비관: ~100K (22%)
  ├─ Graph 적재 (병렬):
  │   ├─ Person: ~100K~450K
  │   ├─ Chapter: ~500K~2.25M
  │   ├─ Skill: ~2K~5K
  │   ├─ Role: ~500~1K
  │   └─ Relationship: 적재 상황에 따라 증가
  └─ Vector Index 업데이트

□ Phase 1 크롤링 파이프라인
  ├─ 계속 가동 (링크드인 + GitHub)
  └─ 일일 신규 데이터 추가 (1K 건/일)

□ 자동화 + 모니터링
  ├─ BigQuery chunk_status 테이블
  ├─ Cloud Scheduler (Batch 폴링, Dead-letter 재시도)
  ├─ src/batch/batch_monitor.py (실시간 모니터링)
  └─ src/batch/batch_auto_retry.py (자동 재시도)

□ 에이전트 역량 확대
  ├─ 검색 범위: 1,000건 → 100K~450K
  ├─ 데이터 소스: DB 텍스트만 → DB + PDF + DOCX + HWP
  └─ Embedding 커버리지: 1K 증가분 → 450K

□ Regression 테스트
  ├─ Golden 데이터 50건 준비
  │   ├─ DB 텍스트 20건 (Phase 1)
  │   ├─ PDF 10건
  │   ├─ DOCX 10건
  │   └─ HWP 10건
  ├─ 수동 검증 완료
  └─ 프롬프트 미세조정 (필요 시)

□ Go/No-Go 판정
  ├─ Phase 2 완료도 평가
  │   ├─ 낙관: 100% → Phase 3 GO
  │   ├─ 기본: 50~99% → GO (부분)
  │   └─ 비관: <50% → 기간 연장 또는 Phase 3 연기
  │
  ├─ 데이터 품질 평가
  │   ├─ CER (Character Error Rate)
  │   ├─ Entity 추출 정확도
  │   └─ Graph 일관성
  │
  └─ 리소스 평가
      ├─ API 비용 (Batch API, Vertex AI)
      ├─ 인프라 비용 (Neo4j Professional, GCS, BQ)
      └─ 인력 소진도

□ Phase 3 사전 준비
  ├─ JD 파서 코드 초안 (2-1-7)          ✓ 2-1-7
  ├─ raw/jds/ 데이터 사전 업로드 준비
  ├─ NICE DB 접근 권한 확보 진행 중
  │   ├─ 법무 검토 (PII 마스킹 최종 확정)
  │   ├─ 보안 검토 (접근 제어)
  │   └─ IT 연동 (DB 커넥션 설정)
  ├─ JD 데이터 구조 설계 완료
  ├─ Neo4j Professional Connection pool 한도 확인
  │   └─ tasks 수 최종 결정 (tasks ≤ max_connections/2)
  └─ 인력 추가 여부 최종 결정 (DE 1명, MLE 1명 또는 추가)
```

---

## 버퍼 1주 — Week 13

```
버퍼 주간 활동 (상황에 따라 유동적):

=== Phase 2 → Phase 3 Go/No-Go 판정 (Mon-Tue) ===

평가 기준:

1. 완료도 평가
   ├─ 450K 처리량: 낙관(100%) vs 기본(50-99%) vs 비관(<50%)
   ├─ 파싱 성공률: 목표 95% 이상
   ├─ CER (Character Error Rate): HWP ≤ 0.15
   └─ 데이터 품질: Golden 50건 검증 통과

2. 인프라 평가
   ├─ Neo4j Professional 안정성 (uptime 99% 이상)
   ├─ API 비용 실제 vs 예상 (편차 ±20% 내)
   └─ 자동화 안정성 (Batch 폴링 성공률 95% 이상)

3. 인력 평가
   ├─ DE, MLE 소진도 (기간 내 완료 가능성)
   ├─ 기술 부채 누적 (코드 정리 필요 여부)
   └─ Phase 3 인력 추가 필요 여부

판정 결과:
  - GO: Phase 3 일정대로 진행 (Week 14 시작)
  - GO (부분): Phase 2 연장 + Phase 3 병렬 (또는 순차)
  - NO-GO: Phase 2 연장 (1~2주) → Phase 3 미루기

=== Phase 2 미완료 태스크 마무리 (Tue-Wed) ===

만약 일부 chunk가 미처리된 경우:
  ├─ 자동화 확대 (kg-batch-poll 빈도 증가)
  ├─ 우선순위 재조정 (중요 chunk 먼저 처리)
  └─ Week 14 이후 백그라운드 진행

=== 기술 부채 해소 (Wed-Thu) ===

Code cleanup:
  ├─ Linting (pylint, black)
  ├─ Type hints 완성
  ├─ 테스트 커버리지 90% 이상 (필요 시)
  └─ Docstring 정비

문서화:
  ├─ API 문서 (swagger)
  ├─ 운영 메뉴얼 (Batch 처리 가이드)
  ├─ 트러블슈팅 가이드 (Dead-letter 분석 방법)
  └─ 비용 리포트 (실제 소요 비용 정리)

=== NICE DB 접근 최종 확인 (Thu-Fri) ===

Phase 3 사전 준비:
  ├─ NICE DB 커넥션 테스트 (권한 확인)
  │   ├─ 조회 권한: Person, Career, Education
  │   ├─ PII 마스킹 정책 최종 확정
  │   └─ 데이터 가용성 확인 (450K 건 이상)
  │
  ├─ JD 데이터 수집 시작 (선택: WANTED, SARAMIN, 내부)
  │   └─ raw/jds/ 구조 준비 완료
  │
  ├─ Phase 3 크롤러 구현 계획 (Week 14 시작 대비)
  │   ├─ NICE 크롤러 초안 (2-1-7의 JD 파서 활용)
  │   ├─ JD 파싱 파이프라인 설계
  │   └─ JD ↔ Candidate 매칭 알고리즘
  │
  └─ 법무 최종 PII 확정
      └─ 생년월일 마스킹 범위 (년월만 vs 년만)

=== 인력 추가 여부 최종 결정 (Fri) ===

현황 분석:
  ├─ Phase 2 완료도 (%)
  ├─ Phase 3 예상 작업량
  ├─ 현 인력(DE 1, MLE 1)으로 수행 가능 여부
  └─ 추가 인력 필요 시 type (DE, MLE, DevOps)

의사결정:
  ├─ 추가 인력 없음: Phase 3 단계적 진행 (JD 크롤링 먼저, 매칭은 나중)
  ├─ DE 1명 추가: 데이터 파이프라인 병렬화 (크롤링 + 파싱 + 적재)
  ├─ MLE 1명 추가: 매칭 알고리즘 병렬 개발 (크롤링 중 개발)
  └─ 둘 다 추가: Phase 3 전속 진행 (Week 14-19, 6주)

결정 후 공지:
  └─ 경영진 + 엔지니어링 팀 공유 (Week 14 일정 확정)

=== 잔여 Batch 처리 모니터링 (지속) ===

백그라운드 작업 (자동화):
  ├─ kg-batch-poll: 30분 주기 (계속)
  ├─ kg-deadletter-retry: 일 1회 자정 (계속)
  ├─ BigQuery chunk_status 모니터링 (주 1회 요약 리포트)
  └─ Neo4j 커넥션 풀 상태 모니터링 (필요 시)

주간 리포트:
  ├─ 완료된 chunk 수
  ├─ 실패 chunk 분석 (원인별 분류)
  ├─ 예상 최종 완료 시점
  └─ Phase 3 영향도 (데이터 커버리지)
```

---

## 실행 체크리스트

```
Week 7 (2-0)
  □ Phase 1 PoC 코드 리팩토링 (2-0-1)
  □ 의사결정 코드 반영 (2-0-2)
  □ HWP 파싱 PoC (2-0-3) — CER 측정
  □ PDF/DOCX 방법 확정 (2-0-4)
  □ 프로덕션 파싱 초안 (2-0-5)
  □ 테스트 세트 구성 (2-0-6)

Week 8-9 (2-1)
  □ PDF/DOCX 파서 모듈 (2-1-1) — Week 8
  □ HWP 파서 모듈 (2-1-2) — Week 8
  □ 섹션 분할기 (2-1-3) — Week 8
  □ 경력 블록 분리기 (2-1-4) — Week 8-9
  □ PII 마스킹 확장 (2-1-5) — Week 9
  □ SimHash 중복 제거 (2-1-6) — Week 9
  □ JD 파서 (2-1-7) — Week 9
  □ 기술/회사 사전 (2-1-8) — Week 9
  □ Docker + Job 등록 (2-1-9) — Week 9

Week 10 (2-2)
  □ Neo4j Professional 인스턴스 생성
  □ Phase 1 데이터 마이그레이션
  □ Secret Manager 업데이트
  □ Constraint/Index 재생성
  □ Connection pool 최적화

Week 10-12 (2-3)
  □ Batch API 450 chunks 제출 시작
  □ BigQuery chunk_status 추적 시작
  □ Cloud Scheduler 자동화 활성화
  □ 실시간 모니터링 (batch_monitor.py)
  □ Dead-letter 관리
  □ Graph 적재 (병렬 진행)
  □ Golden 50건 Regression 테스트

Week 13 (버퍼)
  □ Phase 2 → Phase 3 Go/No-Go 판정
  □ 미완료 태스크 마무리
  □ 기술 부채 해소 (코드 정리, 문서화)
  □ NICE DB 접근 최종 확인
  □ 인력 추가 여부 최종 결정
  □ Phase 3 사전 준비 완료
```

---

## 리스크 관리

### High Risk

| 리스크 | 영향도 | 대응 |
|--------|--------|------|
| Batch API 할당량 한도 (매월 10M 호출) | 높음 | 사전 할당량 증청 (한달 전) + 동시 batch 수 제한 (10→5) |
| HWP 파싱 CER > 0.15 | 높음 | Gemini 멀티모달 또는 LibreOffice 더블 검증 + 비용 추가 |
| Neo4j Professional 연결 풀 한도 (max 10) | 중간 | Cloud Run Job tasks 조정 (tasks ≤ 5) |
| 450K 전체 처리 불완료 (Week 12 내) | 중간 | 자동화 확대 (Week 13+) + Phase 3 부분 병렬 진행 |

### Medium Risk

| 리스크 | 영향도 | 대응 |
|--------|--------|------|
| PDF/DOCX 파싱 정확도 < 90% | 중간 | Document AI 검증 (정확도 98% vs pymupdf 90%) |
| DB + 파일 중복 (같은 사람 2개 이상 파일) | 중간 | SimHash + 메뉴얼 매칭 규칙 정의 |
| GCS 스토리지 비용 (150GB) | 낮음 | Archive 정책 (3개월 후 coldline) |

### Low Risk

| 리스크 | 영향도 | 대응 |
|--------|--------|------|
| 파싱 Job 재시도 (GCS 네트워크 오류) | 낮음 | max-retries=2 + dead-letter 처리 |
| BigQuery 비용 (450K 쿼리) | 낮음 | Clustering (source_type, status) + 파티셔닝 |

---

## 예상 비용

### Phase 2 비용 추정 (6주, Week 7-12)

| 항목 | 수량 | 단가 | 소계 | 비고 |
|------|------|------|------|------|
| **Batch API** | 450 chunks | $0.06/1K | $27 | 1K 텍스트 당 비용 |
| **Vertex AI (LLM)** | 450K tokens × 5회 | $0.0005/1K | $1,125 | 추출 + 정제 |
| **Neo4j Professional** (4GB) | 42일 | $20/일 | $840 | 월 $600 + 7일 추가 |
| **GCS 스토리지** (150GB) | 150GB | $0.020/GB/월 | $90 | 6주 치 |
| **BigQuery** (스캔) | 450K rows × 10 쿼리 | $6.25/TB | $28 | 저가 스토리지 |
| **Cloud Run Jobs** (파싱, 중복제거) | 100 task-hours | $0.00002/GB-s | $10 | 저비용 |
| **Cloud Scheduler** | 50 실행 | 무료 | — | 월 3회 무료 |
| **기타** (로깅, 모니터링) | — | — | $50 | 예비 |
| **합계** | — | — | **$2,170** | 약 230만원 |

### Phase 2 인력비 추정

```
인력: DE 1명 + MLE 1명 (6주 풀타임)
- DE: 240시간 × 75,000원 = 18,000,000원
- MLE: 240시간 × 80,000원 = 19,200,000원
- 합계: 37,200,000원 (약 37M)

전체 비용 (인프라 + 인력): 약 39.4M 원
```

---

## 다음 단계 (Week 13 이후)

### Phase 3: JD 통합 + 후보자-직무 매칭 (6주, Week 14-19)

```
Week 14: NICE DB 통합 + JD 크롤링
Week 15-17: 매칭 알고리즘 + 점수 모델
Week 18-19: Scale-out + 최종 검증

예상 산출물:
- JD Extractor (NICE DB + 외부 소스)
- Candidate-JD 매칭 Score (코사인 유사도 + LLM)
- 최종 KG: 450K Candidate + JD + Matching
- 에이전트 역량: "senior backend engineer 찾기" → 50명 추천
```

---

## 참고: Phase 0/1 의사결정 결과 (Code에 반영됨)

```
Phase 0 (검증 PoC)에서 확정한 사항:
  ✓ Document AI vs pymupdf: Document AI 선택 (PDF 정확도 98%)
  ✓ HWP 파싱: pyhwp + Gemini 멀티모달 (CER 0.12)
  ✓ PII 마스킹: 생년월일, 연락처 (offset 기록 보존)
  ✓ 중복 제거: SimHash 기반 (코드 통합)
  ✓ Neo4j 버전: Community → Professional (Week 10)
  ✓ Batch API: 동시 10 chunks (할당량 고려)

Phase 1에서 검증한 사항:
  ✓ 1,000건 처리 가능 (6시간)
  ✓ LLM 프롬프트 (Entity 추출: F1=0.92)
  ✓ Graph 구조 (Person-Chapter-Skill 3단계)
  ✓ Vector Embedding (Ada 1536차원)
  ✓ 에이전트 검색 성능 (AUC=0.88)

Phase 2에서 적용:
  └─ Phase 0/1 결과를 코드에 직접 반영 (2-0, 2-1)
```
