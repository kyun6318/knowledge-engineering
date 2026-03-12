# Knowledge Graph 구축 GCP 실행 계획 — v7 파이프라인 기반

> **원본**: `02.create-kg/plans/v7/` (5개 문서)의 v10 온톨로지 기반 파이프라인을
> GCP 환경에서 실행하기 위한 인프라 + 실행 계획.
>
> **참조 문서**:
> - `02.create-kg/plans/v7/02_extraction_pipeline.md` — 파이프라인 설계
> - `02.create-kg/plans/v7/03_model_candidates_and_costs.md` — 모델/비용
> - `02.create-kg/plans/v7/04_execution_plan.md` — 실행 계획 (논리)
> - `03.ml-platform/plans/create-kg-gcp-plan.md` — 기존 GCP 계획 (참조)
> - `03.ml-platform/plans/crawling-gcp-plan.md` — 크롤링 GCP 계획 (참조)
> - `03.ml-platform/plans/api-test-3day-v3.md` — GCP 기능 검증 결과
>
> 작성일: 2026-03-08

---

## 1. GCP 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   GCP Project: graphrag-kg                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [데이터 레이어]                                                         │
│  ├─ GCS: gs://graphrag-kg-data/                                        │
│  │   ├─ raw/resumes/            (이력서 원본 150GB)                      │
│  │   ├─ raw/jds/                (JD 원본)                               │
│  │   ├─ reference/              (NICE, 기술사전, 회사사전, 역할사전)       │
│  │   ├─ parsed/                 (파싱 결과 JSON)                        │
│  │   ├─ dedup/                  (중복 제거 결과)                         │
│  │   ├─ contexts/company/       (CompanyContext JSON)                    │
│  │   ├─ contexts/candidate/     (CandidateContext JSON)                 │
│  │   ├─ batch-api/              (Anthropic Batch API 요청/응답)          │
│  │   ├─ mapping-features/       (MappingFeatures JSON)                  │
│  │   ├─ prompts/                (프롬프트 버전 관리)                     │
│  │   ├─ dead-letter/            (처리 실패 건)                           │
│  │   ├─ quality/                (Golden Set, Gold Labels)               │
│  │   └─ backups/                (Context JSON 버전 백업)                 │
│  │                                                                       │
│  ├─ BigQuery: graphrag_kg                                               │
│  │   ├─ processing_log          (처리 이력/모니터링)                     │
│  │   ├─ chunk_status            (chunk 상태 추적)                       │
│  │   ├─ mapping_features        (서빙 테이블)                            │
│  │   ├─ quality_metrics         (품질 평가 결과)                         │
│  │   └─ crawl.*                 (크롤링 관련 — 별도 데이터셋)             │
│  │                                                                       │
│  └─ Neo4j AuraDB (외부 관리형)                                          │
│      ├─ Person, Chapter, Organization, Vacancy, Industry, ...           │
│      ├─ Vector Index (chapter_embedding, vacancy_embedding)              │
│      └─ MAPPED_TO, REQUIRES_ROLE, BELONGS_TO, IN_INDUSTRY 관계          │
│                                                                         │
│  [컴퓨팅 레이어]                                                         │
│  ├─ Cloud Run Jobs            (배치 파이프라인 실행)                     │
│  ├─ Cloud Functions           (이벤트 트리거, 경량 처리)                 │
│  └─ Compute Engine (GPU)      (시나리오 C: On-premise SLM 전용)        │
│                                                                         │
│  [오케스트레이션]                                                        │
│  ├─ Cloud Workflows           (파이프라인 DAG 관리 — 옵션 A)            │
│  └─ Prefect (Cloud Run 호스팅) (파이프라인 DAG 관리 — 옵션 B)           │
│                                                                         │
│  [LLM API (외부)]                                                       │
│  ├─ Anthropic Batch API       (Claude Haiku 4.5 — Primary)              │
│  ├─ Anthropic API             (Claude Sonnet 4.6 — Fallback/PoC)        │
│  └─ Vertex AI                 (text-multilingual-embedding-002)         │
│                                                                         │
│  [크롤링 레이어 — Phase 3]                                               │
│  ├─ Cloud Run Jobs            (Playwright 홈페이지 크롤러)               │
│  ├─ Cloud Run Jobs            (네이버 뉴스 수집기)                       │
│  └─ Vertex AI Gemini API      (크롤링 데이터 LLM 추출)                  │
│                                                                         │
│  [모니터링]                                                              │
│  ├─ Cloud Monitoring          (인프라 메트릭)                            │
│  ├─ Cloud Logging             (애플리케이션 로그)                        │
│  └─ BigQuery + Looker Studio  (커스텀 대시보드)                          │
│                                                                         │
│  [보안]                                                                  │
│  ├─ Secret Manager            (Anthropic, Neo4j, 네이버 API 키)         │
│  ├─ IAM                       (서비스 계정 최소 권한)                    │
│  └─ VPC Service Controls      (PII 유출 방지, 선택적)                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. v7 파이프라인 → GCP 서비스 매핑

### 2.1 파이프라인별 GCP 서비스

| v7 파이프라인 | GCP 서비스 | 선택 근거 |
|---|---|---|
| **이력서 파싱 (전처리)** | Cloud Run Jobs | CPU 집약, Task 단위 병렬 (최대 10,000 tasks) |
| **이력서 중복 제거** | Cloud Run Jobs | 메모리 집약 (SimHash 전체 비교) |
| **Pipeline A: CompanyContext** | Cloud Run Jobs + Anthropic Batch API | 10K JD 규모, Batch API 50% 할인 |
| **Pipeline B: CandidateContext** | Cloud Run Jobs + Anthropic Batch API | 500K 이력서, 핵심 비용 포인트 |
| **Pipeline C: Graph 적재** | Cloud Run Jobs | Neo4j AuraDB 연결, 트랜잭션 배치 |
| **Pipeline D: MappingFeatures** | Cloud Run Jobs + Vertex AI Embedding | Rule + Embedding cosine 계산 |
| **Pipeline E: 서빙** | BigQuery | JSON → BigQuery 로드 + MAPPED_TO Graph 반영 |
| **증분 처리 (운영)** | Cloud Functions + Cloud Scheduler | 일일 트리거, 경량 변경 감지 |
| **Dead-Letter 재처리** | Cloud Scheduler + Cloud Run Jobs | 일 1회 자동 재시도 |
| **NICE DB 조회** | Cloud Functions | 경량 lookup, 캐싱 |
| **크롤링 (Phase 3)** | Cloud Run Jobs + Gemini API | crawling-gcp-plan.md 참조 |

### 2.2 Pipeline DAG 의존성 (v7)

```
Pipeline A (CompanyContext)  ──┐
                               ├──→ C (Graph 적재) ──→ D (MappingFeatures) ──→ E (서빙)
Pipeline B (CandidateContext) ─┘
```

| 관계 | 설명 | GCP 구현 |
|---|---|---|
| **A ∥ B** | 병렬 실행 (입력 독립) | Cloud Workflows parallel branch 또는 Prefect concurrent task |
| **A+B → C** | 양쪽 완료 후 Graph 적재 | Workflows join step / Prefect wait_for |
| **C → D** | Vector Index 필요 | 순차 step |
| **D → E** | BigQuery + MAPPED_TO | 순차 step |

---

## 3. GCP 환경 구성

```
프로젝트: graphrag-kg (신규 생성 또는 기존 ml-api-test-vertex 재활용)
리전: asia-northeast3 (서울) — 데이터 주권, 레이턴시

Vertex AI 리전: us-central1 — Embedding API (text-multilingual-embedding-002)
Neo4j AuraDB: asia-northeast1 (도쿄) — 서울 미지원, 가장 가까운 리전

API 활성화 필요:
  - Cloud Run API
  - Cloud Workflows API
  - Cloud Scheduler API
  - Secret Manager API
  - Artifact Registry API
  - Cloud Build API
  - BigQuery API
  - Cloud Monitoring API
  - Cloud Logging API
  - Cloud Functions API
  - Vertex AI API (Embedding 전용)

SDK:
  anthropic >= 0.39.0              # Claude Haiku/Sonnet (Batch API)
  google-cloud-aiplatform >= 1.74.0 # text-multilingual-embedding-002
  google-cloud-bigquery >= 3.20.0
  google-cloud-storage >= 2.14.0
  google-cloud-secret-manager >= 2.18.0
  neo4j >= 5.15.0                  # Neo4j Python Driver
  pymupdf >= 1.23.0                # PDF 파싱
  python-docx >= 1.1.0             # DOCX 파싱
  pydantic >= 2.5.0                # Context JSON 스키마
  simhash >= 2.1.2                 # 이력서 중복 감지

Budget Alert: $300 (경고), $600 (강제 중단)
  — 크롤링 파이프라인과 별도 알림 설정

Anthropic Batch API:
  Claude Haiku 4.5 Batch: Input $0.40/1M, Output $2.00/1M
  → 파일럿은 일반 API, Phase 2 전체 처리는 Batch API 적용

Vertex AI Embedding:
  text-multilingual-embedding-002: $0.0065/1M 토큰
  → QPM 제한 확인 후 throttle 설정
```

---

## 4. GCS 버킷 구조

```yaml
gs://graphrag-kg-data/
├── raw/
│   ├── resumes/                    # 이력서 원본 (150GB)
│   │   ├── pdf/
│   │   ├── docx/
│   │   └── hwp/
│   └── jds/                        # JD 원본
│       └── *.json                   # {job_id, company_id, jd_text}
│
├── reference/
│   ├── nice/                        # NICE 기업 정보 스냅샷
│   │   └── nice_companies.parquet
│   ├── nice_industry_codes.json     # KSIC 업종 코드 마스터
│   ├── tech_dictionary.json         # 기술 사전 (2,000+ 기술명)
│   ├── company_alias.json           # 회사명 정규화 사전
│   └── role_alias.json              # 직무명 정규화 사전
│
├── parsed/
│   ├── resumes/                     # 파싱 결과
│   │   └── {candidate_id}.json      # {text, sections, career_blocks, metadata}
│   └── jds/
│       └── {job_id}.json
│
├── dedup/
│   ├── canonical_list.json          # 중복 제거 후 canonical 이력서 목록
│   └── review_queue.json            # SimHash 유사 이력서 검토 큐
│
├── contexts/
│   ├── company/
│   │   └── {job_id}/
│   │       ├── v1.json              # CompanyContext (버전 관리)
│   │       └── latest.json
│   └── candidate/
│       └── {candidate_id}/
│           ├── v1.json              # CandidateContext
│           └── latest.json
│
├── batch-api/
│   ├── requests/                    # Anthropic Batch API 요청 파일
│   │   └── batch_{chunk_id}.jsonl
│   └── responses/                   # Batch API 응답 파일
│       └── batch_{chunk_id}_result.jsonl
│
├── mapping-features/
│   └── {job_id}/
│       └── top500.json              # 상위 500명 MappingFeatures
│
├── prompts/
│   ├── experience_extract_v1.txt
│   ├── career_level_v1.txt
│   ├── vacancy_role_v1.txt
│   ├── structural_tension_v1.txt
│   └── CHANGELOG.md
│
├── dead-letter/
│   └── {pipeline}/{item_id}.json    # 처리 실패 건
│
├── quality/
│   ├── golden_set/                  # Phase 0 PoC 50건 (고정)
│   └── gold_labels/                 # Phase 2 전문가 검수 400건
│
└── backups/
    └── {date}/                      # 일일 Context JSON 백업
```

---

## 5. BigQuery 테이블 스키마

```sql
-- 데이터셋 생성
CREATE SCHEMA graphrag_kg OPTIONS(location='asia-northeast3');

-- 처리 로그 (전체 파이프라인 공통)
CREATE TABLE graphrag_kg.processing_log (
  run_id STRING NOT NULL,
  pipeline STRING NOT NULL,          -- 'parse' | 'company_ctx' | 'candidate_ctx' | 'graph_load' | 'mapping'
  item_id STRING NOT NULL,           -- candidate_id 또는 job_id
  status STRING NOT NULL,            -- 'SUCCESS' | 'FAILED' | 'SKIPPED' | 'PARTIAL'
  error_type STRING,                 -- 'json_parse' | 'schema_mismatch' | 'api_error' | 'timeout'
  error_message STRING,
  input_tokens INT64,
  output_tokens INT64,
  llm_model STRING,
  prompt_version STRING,
  retry_count INT64 DEFAULT 0,
  latency_ms FLOAT64,
  processed_at TIMESTAMP NOT NULL,
  run_date DATE NOT NULL,
);

-- Chunk 상태 추적 (v7 신설)
CREATE TABLE graphrag_kg.chunk_status (
  chunk_id STRING NOT NULL,          -- "chunk_001" ~ "chunk_450"
  pipeline STRING NOT NULL,          -- 'candidate_ctx' | 'company_ctx'
  status STRING NOT NULL,            -- 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  total_count INT64,
  success_count INT64 DEFAULT 0,
  fail_count INT64 DEFAULT 0,
  partial_count INT64 DEFAULT 0,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  error_summary STRING,
  retry_attempt INT64 DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP,
);

-- MappingFeatures 서빙 테이블
CREATE TABLE graphrag_kg.mapping_features (
  job_id STRING NOT NULL,
  candidate_id STRING NOT NULL,
  overall_match_score FLOAT64,
  stage_match FLOAT64,
  stage_match_status STRING,         -- 'ACTIVE' | 'INACTIVE'
  vacancy_fit FLOAT64,
  vacancy_fit_status STRING,
  domain_fit FLOAT64,
  domain_fit_status STRING,
  culture_fit FLOAT64,
  culture_fit_status STRING,
  role_fit FLOAT64,
  role_fit_status STRING,
  active_feature_count INT64,
  mapped_to_graph BOOLEAN DEFAULT FALSE,
  computed_at TIMESTAMP,
  prompt_version STRING,
);

-- 품질 평가 결과
CREATE TABLE graphrag_kg.quality_metrics (
  eval_id STRING NOT NULL,
  eval_date DATE NOT NULL,
  eval_type STRING,                  -- 'poc' | 'gold' | 'regression'
  pipeline STRING,
  field_name STRING,                 -- 'scope_type' | 'outcomes' | 'vacancy_fit' 등
  metric_name STRING,                -- 'accuracy' | 'f1' | 'cohens_d' | 'correlation_r'
  metric_value FLOAT64,
  sample_size INT64,
  model_version STRING,
  prompt_version STRING,
  notes STRING,
);

-- LLM 파싱 실패 모니터링 (v7 신설)
CREATE TABLE graphrag_kg.parse_failure_log (
  item_id STRING NOT NULL,
  pipeline STRING NOT NULL,
  failure_tier STRING NOT NULL,      -- 'tier1_json_repair' | 'tier2_retry' | 'tier3_skip'
  original_error STRING,
  repair_attempted BOOLEAN,
  repair_success BOOLEAN,
  partial_fields_extracted INT64,    -- 부분 추출 시 추출된 필드 수
  total_fields INT64,                -- 전체 필드 수
  raw_response_preview STRING,       -- 실패한 LLM 응답 앞 500자
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
);
```

---

## 6. Cloud Run Jobs 설계

### 6.1 Job 정의

| Job 이름 | 용도 | CPU/Memory | 병렬 Tasks | Timeout | 예상 실행 시간 |
|---|---|---|---|---|---|
| `kg-parse-resumes` | 이력서 파싱 (PDF/DOCX/HWP → JSON) | 2 vCPU / 4GB | 50 | 3600s | 4~6시간 |
| `kg-dedup-resumes` | 이력서 중복 제거 (SimHash) | 4 vCPU / 8GB | 1 | 7200s | 1~2시간 |
| `kg-batch-prepare` | Batch API 요청 파일 생성 (1,000건/chunk) | 2 vCPU / 4GB | 10 | 3600s | 1시간 |
| `kg-batch-submit` | Anthropic Batch API 제출 + 폴링 | 1 vCPU / 2GB | 1 | 86400s (24h) | 대기 |
| `kg-batch-collect` | Batch 응답 수집 + Context JSON 생성 | 2 vCPU / 4GB | 20 | 3600s | 2~3시간 |
| `kg-company-ctx` | CompanyContext 생성 (NICE + LLM) | 2 vCPU / 4GB | 5 | 3600s | 1~2시간 |
| `kg-graph-load` | Context → Neo4j 적재 (MERGE) | 2 vCPU / 4GB | 8 | 43200s (12h) | 8~12시간 |
| `kg-embedding` | Embedding 생성 + Neo4j Vector Index | 2 vCPU / 4GB | 10 | 21600s (6h) | 4~6시간 |
| `kg-mapping` | MappingFeatures 계산 + BigQuery 적재 | 4 vCPU / 8GB | 20 | 10800s (3h) | 2~3시간 |
| `kg-dead-letter` | Dead-Letter 재처리 | 1 vCPU / 2GB | 1 | 3600s | 30분 |
| `kg-industry-load` | Industry 마스터 노드 적재 (KSIC) | 1 vCPU / 2GB | 1 | 600s | 5분 |

### 6.2 핵심 Job 상세

#### 6.2.1 이력서 파싱 Job

```python
# kg-parse-resumes/main.py
import os, json
from google.cloud import storage

TASK_INDEX = int(os.environ.get("CLOUD_RUN_TASK_INDEX", 0))
TASK_COUNT = int(os.environ.get("CLOUD_RUN_TASK_COUNT", 1))

def main():
    """Cloud Run Jobs Task — 이력서 파싱"""
    client = storage.Client()
    bucket = client.bucket("graphrag-kg-data")

    # Task별 처리 범위 결정
    all_resumes = list_resumes(bucket, "raw/resumes/")
    my_resumes = partition(all_resumes, TASK_INDEX, TASK_COUNT)

    for resume_blob in my_resumes:
        try:
            raw_bytes = resume_blob.download_as_bytes()
            parsed = parse_resume(raw_bytes, resume_blob.name)

            # 섹션 분할 + 경력 블록 분리
            sections = split_sections(parsed.text)
            blocks = split_career_blocks(sections)

            # PII 마스킹
            masked_text, offset_map = mask_pii(parsed.text)

            result = {
                "candidate_id": extract_candidate_id(resume_blob.name),
                "source_path": resume_blob.name,
                "text": parsed.text,
                "masked_text": masked_text,
                "offset_map": offset_map,
                "sections": sections,
                "career_blocks": blocks,
                "metadata": parsed.metadata,
                "parsed_at": datetime.utcnow().isoformat(),
            }
            save_json(bucket, f"parsed/resumes/{result['candidate_id']}.json", result)

        except Exception as e:
            save_dead_letter(bucket, "parse", resume_blob.name, str(e))

    print(f"[Task {TASK_INDEX}] Completed: {len(my_resumes)} resumes")

if __name__ == "__main__":
    main()
```

#### 6.2.2 Batch API 제출 Job (Anthropic)

```python
# kg-batch-submit/main.py
import anthropic, json, time
from google.cloud import storage, secretmanager

def get_anthropic_key():
    client = secretmanager.SecretManagerServiceClient()
    name = "projects/graphrag-kg/secrets/anthropic-api-key/versions/latest"
    return client.access_secret_version(name=name).payload.data.decode("UTF-8")

def main():
    api_key = get_anthropic_key()
    anthropic_client = anthropic.Anthropic(api_key=api_key)
    gcs = storage.Client()
    bucket = gcs.bucket("graphrag-kg-data")

    request_blobs = list(bucket.list_blobs(prefix="batch-api/requests/"))
    MAX_CONCURRENT = 5
    active_batches = []

    for blob in request_blobs:
        while len(active_batches) >= MAX_CONCURRENT:
            active_batches = poll_and_collect(anthropic_client, active_batches, bucket)
            time.sleep(60)

        requests = load_jsonl(blob)
        batch = anthropic_client.messages.batches.create(requests=requests)
        active_batches.append({
            "batch_id": batch.id,
            "chunk_id": extract_chunk_id(blob.name),
        })
        log_to_bigquery("batch_submit", blob.name, batch.id)

    # 남은 배치 완료 대기
    while active_batches:
        active_batches = poll_and_collect(anthropic_client, active_batches, bucket)
        if active_batches:
            time.sleep(300)  # 5분 간격 폴링
```

#### 6.2.3 LLM 출력 파싱 실패 처리 (v7 3-tier)

```python
# shared/llm_parser.py — v7 3-tier retry 전략

import json
from json_repair import repair_json  # json-repair 라이브러리
from pydantic import ValidationError

def parse_llm_response(raw_text: str, schema_class, item_id: str) -> tuple:
    """
    v7 3-tier retry:
    1. json-repair 시도
    2. temperature 조정 재시도
    3. skip + dead-letter + 부분 추출 허용

    Returns: (parsed_result, parse_tier, partial)
    """
    # Tier 1: json-repair
    try:
        repaired = repair_json(raw_text)
        parsed = json.loads(repaired)
        result = schema_class(**parsed)
        log_parse_result(item_id, "tier1_json_repair", success=True)
        return result, "tier1", False
    except (json.JSONDecodeError, ValidationError):
        pass

    # Tier 2: temperature 조정 재시도 (호출측에서 처리)
    # → 이 함수는 단일 응답 파싱만 담당, 재시도는 호출측

    # Tier 3: 부분 추출 허용
    try:
        repaired = repair_json(raw_text)
        parsed = json.loads(repaired)
        # 필수 필드만 추출 시도
        partial = schema_class.model_construct(**{
            k: v for k, v in parsed.items()
            if k in schema_class.model_fields
        })
        log_parse_result(item_id, "tier3_skip", success=True, partial=True,
                        extracted=len([v for v in parsed.values() if v is not None]),
                        total=len(schema_class.model_fields))
        return partial, "tier3", True
    except Exception:
        log_parse_result(item_id, "tier3_skip", success=False)
        save_dead_letter("llm_parse", item_id, raw_text[:500])
        return None, "tier3", False
```

#### 6.2.4 Graph 적재 Job

```python
# kg-graph-load/main.py
import os
from neo4j import GraphDatabase
from google.cloud import storage, secretmanager

TASK_INDEX = int(os.environ.get("CLOUD_RUN_TASK_INDEX", 0))
TASK_COUNT = int(os.environ.get("CLOUD_RUN_TASK_COUNT", 1))
BATCH_SIZE = 100

def main():
    uri, user, password = get_neo4j_credentials()
    driver = GraphDatabase.driver(uri, auth=(user, password))
    gcs = storage.Client()
    bucket = gcs.bucket("graphrag-kg-data")

    all_contexts = list_context_files(bucket)
    my_contexts = partition(all_contexts, TASK_INDEX, TASK_COUNT)

    with driver.session() as session:
        batch = []
        for ctx_blob in my_contexts:
            ctx = load_json(ctx_blob)

            if "company" in ctx_blob.name:
                batch.append(("company", ctx))
            else:
                batch.append(("candidate", ctx))

            if len(batch) >= BATCH_SIZE:
                execute_batch(session, batch)
                batch = []
        if batch:
            execute_batch(session, batch)

    driver.close()

def execute_batch(session, batch):
    """Deterministic ID + MERGE 패턴 — Idempotent 적재"""
    def _tx(tx):
        for ctx_type, ctx in batch:
            if ctx_type == "company":
                load_company(ctx, tx)  # Organization, Vacancy, Industry 관계 포함
            else:
                load_candidate(ctx, tx)  # Person, Chapter, Outcome, Signal 포함

    try:
        session.execute_write(_tx)
    except Exception as e:
        # 배치 실패 → 건별 재시도
        for ctx_type, ctx in batch:
            try:
                session.execute_write(
                    lambda tx: load_company(ctx, tx)
                    if ctx_type == "company"
                    else load_candidate(ctx, tx)
                )
            except Exception as e2:
                save_dead_letter_item(ctx_type, ctx, str(e2))
```

---

## 7. 오케스트레이션 전략 (v7)

### 7.1 Cloud Workflows (옵션 A — 권장)

GCP 네이티브, 서버리스, 추가 인프라 불필요.

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
        result: parse_result

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
          body:
            overrides:
              taskCount: 10

    - compute_mapping:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-mapping"}
          location: ${region}
          body:
            overrides:
              taskCount: 20

    # 완료 알림
    - notify:
        call: http.post
        args:
          url: ${args.slack_webhook_url}
          body:
            text: ${"KG Pipeline 완료: run_id=" + run_id}
```

### 7.2 Prefect (옵션 B)

Python 네이티브, 유연한 조건 분기. Cloud Run에서 self-hosted.

```python
# flows/kg_pipeline.py
from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

@task
def parse_resumes(run_id: str):
    trigger_cloud_run_job("kg-parse-resumes", run_id=run_id, tasks=50)

@task
def dedup_resumes(run_id: str):
    trigger_cloud_run_job("kg-dedup-resumes", run_id=run_id)

@task
def create_company_context(run_id: str):
    trigger_cloud_run_job("kg-company-ctx", run_id=run_id)

@task
def create_candidate_context(run_id: str):
    trigger_cloud_run_job("kg-batch-prepare", run_id=run_id)
    trigger_cloud_run_job("kg-batch-submit", run_id=run_id)
    trigger_cloud_run_job("kg-batch-collect", run_id=run_id)

@flow(task_runner=ConcurrentTaskRunner())
def kg_full_pipeline(run_id: str):
    # 전처리 (순차)
    parse_resumes(run_id)
    dedup_resumes(run_id)

    # Context 생성 (병렬)
    company_future = create_company_context.submit(run_id)
    candidate_future = create_candidate_context.submit(run_id)
    company_future.result()
    candidate_future.result()

    # Graph → Embedding → Mapping (순차)
    load_graph(run_id)
    generate_embeddings(run_id)
    compute_mapping(run_id)
```

### 7.3 오케스트레이션 도구 선정 기준

| 기준 | Cloud Workflows | Prefect (self-hosted) |
|---|---|---|
| 비용 | $0.01/1,000 steps (~무료) | Cloud Run 호스팅 ~$30/월 |
| DAG 지원 | 순차/병렬 step | 네이티브 task dependency |
| 모니터링 | Cloud Logging | 내장 UI (flow runs) |
| retry | 기본 retry 정책 | per-task retry, backoff |
| 복잡도 | YAML 기반 (단순) | Python 코드 (유연) |
| **권장** | **GCP 네이티브 우선 시** | **DE가 Python 중심 시** |

> Phase 0-4 의사결정에서 최종 선정.

---

## 8. 보안 설계

### 8.1 PII 처리 플로우

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

> **v5 기본값 전략**: 법무 결론 미확정 시 마스킹 기반 API 사용으로 Phase 1 진행.
> 전환 영향: API endpoint만 변경 (~1일).

### 8.2 IAM 최소 권한

| 서비스 계정 | 역할 | 접근 대상 |
|---|---|---|
| `kg-pipeline` | `storage.objectAdmin` | `gs://graphrag-kg-data/` |
| `kg-pipeline` | `bigquery.dataEditor` | `graphrag_kg` 데이터셋 |
| `kg-pipeline` | `secretmanager.secretAccessor` | API 키 시크릿 |
| `kg-pipeline` | `run.invoker` | Cloud Run Jobs |
| `kg-pipeline` | `workflows.invoker` | Cloud Workflows |
| `kg-pipeline` | `monitoring.metricWriter` | 커스텀 메트릭 |
| `kg-pipeline` | `logging.logWriter` | Cloud Logging |
| `kg-pipeline` | `aiplatform.user` | Vertex AI Embedding API |

### 8.3 Secret Manager 등록 대상

| 시크릿 이름 | 용도 |
|---|---|
| `anthropic-api-key` | Claude Haiku/Sonnet API |
| `neo4j-uri` | Neo4j AuraDB 연결 |
| `neo4j-user` | Neo4j 인증 |
| `neo4j-password` | Neo4j 인증 |
| `naver-api-client-id` | 네이버 뉴스 API (Phase 3) |
| `naver-api-client-secret` | 네이버 뉴스 API (Phase 3) |

---

## 9. 리전 선택

| 서비스 | 리전 | 근거 |
|---|---|---|
| GCS | `asia-northeast3` (서울) | 데이터 주권, 레이턴시 |
| BigQuery | `asia-northeast3` | GCS와 같은 리전 |
| Cloud Run Jobs | `asia-northeast3` | GCS 접근 레이턴시 |
| Cloud Workflows | `asia-northeast3` | Cloud Run과 같은 리전 |
| Cloud Scheduler | `asia-northeast3` | 동일 |
| Vertex AI Embedding | `us-central1` | text-multilingual-embedding-002 제공 리전 |
| Neo4j AuraDB | `asia-northeast1` (도쿄) | 서울 미지원, 가장 가까움 (~10ms) |
| Anthropic API | US (외부) | 선택 불가 |

> **Neo4j 리전**: AuraDB는 `asia-northeast3` 미지원. 배치 처리 특성상 도쿄 리전 레이턴시 영향 미미.
