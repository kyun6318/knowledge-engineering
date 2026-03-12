# Phase 1: MVP 파이프라인 (6.5~7주)

> **목적**: 전처리 → Context 생성 → Graph 적재 → MappingFeatures까지 E2E 파이프라인 완성.
> Phase 0 의사결정 결과를 반영하여 구현.
>
> **light.1 압축 전략** (standard.1 10~12주 → light.1 6.5~7주):
> - [light.1-P1-1] 전처리(DE) + CompanyContext(MLE) 2주 병행 (standard.1: 직렬 4주)
> - [light.1-P1-2] CandidateContext 3주 (standard.1: 4주, Batch API 대기 시간에 Graph 선행)
> - [light.1-P1-3] Graph + Embedding + Mapping 1주로 압축 (standard.1: 4주, 1,000건이므로 충분)
> - [light.1-P1-4] 테스트 + 검증 + 백업 0.5~1주 (Organization ER 알고리즘, regression test, Go/No-Go)
> - **Batch API 대기 시간 활용**: Week 7 (1-B-12) Batch API 폴링 중 Graph 적재 모듈 선행 구현 (1-C-1~2 진행)
>
> **standard.1 품질 개선 통합**:
> - [standard.1-2] HWP 파서 모듈 포함
> - [standard.1-5] Checkpoint/재시작 전략 (파싱, Batch API, Graph 적재)
> - [standard.1-6] 테스트 인프라 + Regression Test 추가
> - [standard.24] Makefile 오케스트레이션 (MVP 규모에 적합)
> - [standard.20] Neo4j 백업 및 Go/No-Go 게이트
>
> **인력**: DE 1명 + MLE 1명 풀타임
> **산출물**: E2E 파이프라인 (JD 100건 + 이력서 1,000건 + Graph + MappingFeatures + MAPPED_TO)

---

## 1-A. 전처리 + CompanyContext 병행 (2주) — Week 3~5

### DE 담당: 전처리 모듈 (2주)

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-A-1 | **PDF/DOCX/HWP 파서 모듈** (Phase 0-C-7 결정 반영) [standard.1-2] | Cloud Run Job 코드 | `src/parsers/hwp.py` |
| 1-A-2 | 섹션 분할기 (Rule-based) | 동일 | `src/splitters/` |
| 1-A-3 | 경력 블록 분리기 | 동일 | |
| 1-A-4 | PII 마스킹 모듈 (offset mapping 보존) | 동일 | `src/pii/` |
| 1-A-5 | 이력서 중복 제거 모듈 (SimHash) | 동일 | `src/dedup/` |
| 1-A-6 | JD 파서 + 섹션 분할 | 동일 | |
| 1-A-7 | 기술 사전 (2,000개) + 회사 사전 구축 | GCS | `reference/` |
| 1-A-8 | Docker 이미지 빌드 + Job 등록 | Cloud Build | |

### MLE 담당: CompanyContext 파이프라인 (2주, 전처리와 병행)

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-A-9 | CompanyContext Pydantic 모델 정의 | 코드 | `src/models/company.py` |
| 1-A-10 | NICE Lookup 모듈 | Cloud Functions | `src/nice/` |
| 1-A-11 | stage_estimate Rule 엔진 | 코드 | |
| 1-A-12 | LLM 추출 프롬프트 (vacancy + role 통합) | GCS | `vacancy_role_v1.txt` |
| 1-A-13 | operating_model 키워드 엔진 + LLM 보정 | 코드 | |
| 1-A-14 | Evidence 생성 모듈 + source_ceiling 적용 | 코드 | |
| 1-A-15 | 통합 테스트 (JD 100건) | Cloud Run Job | E2E 결과 |

### 병행 가능 근거

- 전처리(이력서 파싱)와 CompanyContext(JD 처리)는 **입력 데이터가 다르다** (이력서 vs JD)
- 모듈 간 인터페이스는 JSON 스키마만 사전 합의하면 됨
- DE는 인프라+파싱, MLE는 모델+프롬프트로 역할이 명확히 분리됨

### Cloud Run Jobs 등록 (1-A 완료 시)

```bash
IMAGE=asia-northeast3-docker.pkg.dev/graphrag-kg/kg-pipeline/kg-pipeline:latest
SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com

# 파싱 Job
gcloud run jobs create kg-parse-resumes \
  --image=$IMAGE \
  --command="python,src/parse_resumes.py" \
  --tasks=50 --max-retries=1 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3

# 중복 제거 Job
gcloud run jobs create kg-dedup-resumes \
  --image=$IMAGE \
  --command="python,src/dedup_resumes.py" \
  --tasks=1 \
  --cpu=4 --memory=8Gi \
  --task-timeout=7200 \
  --service-account=$SA \
  --region=asia-northeast3

# CompanyContext Job
gcloud run jobs create kg-company-ctx \
  --image=$IMAGE \
  --command="python,src/company_context.py" \
  --tasks=5 --max-retries=1 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3
```

### 파싱 Job 핵심 로직 — [standard.1-5] Checkpoint 내장

```python
# kg-parse-resumes/main.py
import os, json
from google.cloud import storage, bigquery
from datetime import datetime

TASK_INDEX = int(os.environ.get("CLOUD_RUN_TASK_INDEX", 0))
TASK_COUNT = int(os.environ.get("CLOUD_RUN_TASK_COUNT", 1))

def get_already_processed(bq_client, pipeline: str) -> set:
    """[standard.1-5] 이미 성공한 item을 checkpoint로 조회"""
    query = f"""
        SELECT item_id FROM graphrag_kg.processing_log
        WHERE pipeline = '{pipeline}' AND status = 'SUCCESS'
    """
    try:
        rows = bq_client.query(query).result()
        return {row.item_id for row in rows}
    except Exception:
        return set()  # 첫 실행 시 테이블 없음

def log_processing(bq_client, pipeline: str, item_id: str, status: str, error: str = None):
    """[standard.1-5] BigQuery processing_log에 기록"""
    rows = [{
        "pipeline": pipeline,
        "item_id": item_id,
        "status": status,
        "error": error,
        "timestamp": datetime.utcnow().isoformat(),
    }]
    bq_client.insert_rows_json("graphrag_kg.processing_log", rows)

def main():
    gcs = storage.Client()
    bq = bigquery.Client()
    bucket = gcs.bucket("graphrag-kg-data")

    all_resumes = list_resumes(bucket, "raw/resumes/")
    my_resumes = partition(all_resumes, TASK_INDEX, TASK_COUNT)

    # [standard.1-5] checkpoint: 이미 처리된 건 skip
    processed = get_already_processed(bq, "parse")

    for resume_blob in my_resumes:
        candidate_id = extract_candidate_id(resume_blob.name)
        if candidate_id in processed:
            continue  # skip already processed

        try:
            raw_bytes = resume_blob.download_as_bytes()
            parsed = parse_resume(raw_bytes, resume_blob.name)

            sections = split_sections(parsed.text)
            blocks = split_career_blocks(sections)
            masked_text, offset_map = mask_pii(parsed.text)

            result = {
                "candidate_id": candidate_id,
                "source_path": resume_blob.name,
                "text": parsed.text,
                "masked_text": masked_text,
                "offset_map": offset_map,
                "sections": sections,
                "career_blocks": blocks,
                "metadata": parsed.metadata,
                "parsed_at": datetime.utcnow().isoformat(),
            }
            save_json(bucket, f"parsed/resumes/{candidate_id}.json", result)

            # [standard.1-5] checkpoint 기록
            log_processing(bq, "parse", candidate_id, "SUCCESS")

        except Exception as e:
            save_dead_letter(bucket, "parse", resume_blob.name, str(e))
            log_processing(bq, "parse", candidate_id, "FAILED", str(e))

    print(f"[Task {TASK_INDEX}] Completed: {len(my_resumes)} resumes")
```

---

## 1-B. CandidateContext 파이프라인 (3주) — Week 5~8

> v2의 4주를 3주로 압축. Batch API 제출 후 대기 시간(~24시간)에 Graph 적재 모듈 선행 구현.

### Week 5~6: 모듈 구현 (DE + MLE 공동)

| # | 작업 | 담당 | 산출물 |
|---|---|---|---|
| 1-B-1 | CandidateContext Pydantic 모델 정의 | MLE | `src/models/candidate.py` |
| 1-B-2 | Rule 추출 모듈 (날짜/회사/기술) | MLE | `src/extractors/rule.py` |
| 1-B-3 | LLM 추출 프롬프트 (Experience별) | MLE | `experience_extract_v1.txt` |
| 1-B-4 | LLM 추출 프롬프트 (전체 커리어) | MLE | `career_level_v1.txt` |
| 1-B-5 | WorkStyleSignals LLM 프롬프트 | MLE | |
| 1-B-6 | PastCompanyContext NICE 역산 모듈 | MLE | |
| 1-B-7 | **LLM 파싱 실패 3-tier 구현** | MLE | `src/shared/llm_parser.py` |
| 1-B-8 | Batch API 요청 생성 모듈 (1,000건/chunk) | DE | |
| 1-B-9 | Batch API 제출/폴링 모듈 + checkpoint | DE | |
| 1-B-10 | Chunk 상태 추적 인프라 | DE | BigQuery `batch_tracking` |

### Week 7: Batch API 테스트 + (대기 중) Graph 선행

| # | 작업 | 담당 | 비고 |
|---|---|---|---|
| 1-B-11 | 통합 테스트 (이력서 200건) | MLE | 로컬 Python |
| 1-B-12 | Batch API 연동 테스트 (1,000건 제출) | DE | 24시간 SLA 대기 |
| 1-B-13 | **(대기 중)** Graph 적재 모듈 구현 | DE | 1-C-1~2 선행 |
| 1-B-14 | **(대기 중)** Deterministic ID 생성 | MLE | 1-C 선행 |
| 1-B-15 | Batch API 응답 수집 + Context 생성 | DE | 대기 완료 후 |

### light.1 압축 핵심: Batch API 대기 시간 활용

```
Week 7 타임라인:
Day 1 AM: Batch API 1,000건 제출
Day 1 PM~Day 2 AM: [대기 — 24h SLA]
  ├─ DE: Graph 적재 모듈 구현 (1-C-1~2 선행)
  ├─ DE: Checkpoint 구현 (1-C-10 선행)
  └─ MLE: Deterministic ID + Org Resolution 구현 (1-C-2 선행)
Day 2 PM: Batch API 응답 수집 + CandidateContext 생성
Day 3: CandidateContext 품질 검증 (200건 → 기준 미달 시 프롬프트 수정)
```

### LLM 파싱 실패 3-tier 전략 (v2와 동일, 필수)

```python
# src/shared/llm_parser.py
import json
from json_repair import repair_json
from pydantic import ValidationError

def parse_llm_response(raw_text: str, schema_class, item_id: str) -> tuple:
    """
    v7 3-tier retry:
    1. json-repair 시도
    2. temperature 조정 재시도 (호출측에서 처리)
    3. skip + dead-letter + 부분 추출 허용

    Returns: (parsed_result, parse_tier, partial)
    """
    # Tier 1: json-repair
    try:
        repaired = repair_json(raw_text)
        parsed = json.loads(repaired)
        result = schema_class(**parsed)
        return result, "tier1", False
    except (json.JSONDecodeError, ValidationError):
        pass

    # Tier 3: 부분 추출 허용
    try:
        repaired = repair_json(raw_text)
        parsed = json.loads(repaired)
        partial = schema_class.model_construct(**{
            k: v for k, v in parsed.items()
            if k in schema_class.model_fields
        })
        return partial, "tier3", True
    except Exception:
        save_dead_letter("llm_parse", item_id, raw_text[:500])
        return None, "tier3", False
```

### Batch API 제출 Job — [standard.1-5] batch_tracking & checkpoint 내장

```python
# kg-batch-submit/main.py
import anthropic, json, time
from google.cloud import storage, secretmanager, bigquery
from datetime import datetime

def is_chunk_submitted(bq_client, chunk_id: str) -> bool:
    """[standard.1-5] 이미 제출된 chunk 확인"""
    query = f"""
        SELECT COUNT(*) as cnt FROM graphrag_kg.batch_tracking
        WHERE chunk_id = '{chunk_id}' AND status IN ('SUBMITTED', 'COMPLETED')
    """
    result = bq_client.query(query).result()
    return list(result)[0].cnt > 0

def track_batch(bq_client, batch_id: str, chunk_id: str, status: str, gcs_path: str):
    """[standard.1-5] BigQuery batch_tracking에 기록"""
    rows = [{
        "batch_id": batch_id,
        "chunk_id": chunk_id,
        "status": status,
        "submitted_at": datetime.utcnow().isoformat(),
        "gcs_request_path": gcs_path,
    }]
    bq_client.insert_rows_json("graphrag_kg.batch_tracking", rows)

def poll_and_collect(client, batches, bucket, bq_client):
    """[standard.1-5] 폴링 + 수집 + tracking 업데이트"""
    still_active = []
    for b in batches:
        status = client.messages.batches.retrieve(b["batch_id"])
        if status.processing_status == "ended":
            # 결과 수집
            collect_results(client, b["batch_id"], b["chunk_id"], bucket)
            # tracking 업데이트
            update_batch_tracking(bq_client, b["batch_id"], "COMPLETED")
        else:
            still_active.append(b)
    return still_active

def main():
    api_key = get_anthropic_key()
    anthropic_client = anthropic.Anthropic(api_key=api_key)
    gcs = storage.Client()
    bq = bigquery.Client()
    bucket = gcs.bucket("graphrag-kg-data")

    request_blobs = list(bucket.list_blobs(prefix="batch-api/requests/"))
    MAX_CONCURRENT = 5
    active_batches = []

    for blob in request_blobs:
        chunk_id = extract_chunk_id(blob.name)

        # [standard.1-5] 이미 제출된 chunk skip
        if is_chunk_submitted(bq, chunk_id):
            continue

        while len(active_batches) >= MAX_CONCURRENT:
            active_batches = poll_and_collect(anthropic_client, active_batches, bucket, bq)
            time.sleep(60)

        requests = load_jsonl(blob)
        batch = anthropic_client.messages.batches.create(requests=requests)

        # [standard.1-5] 제출 즉시 batch_tracking에 기록
        track_batch(bq, batch.id, chunk_id, "SUBMITTED", blob.name)

        active_batches.append({
            "batch_id": batch.id,
            "chunk_id": chunk_id,
        })

    while active_batches:
        active_batches = poll_and_collect(anthropic_client, active_batches, bucket, bq)
        if active_batches:
            time.sleep(300)

    print("All batches processed")
```

### Cloud Run Jobs 등록 (CandidateContext)

```bash
gcloud run jobs create kg-batch-prepare \
  --image=$IMAGE \
  --command="python,src/batch_prepare.py" \
  --tasks=10 --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3

gcloud run jobs create kg-batch-submit \
  --image=$IMAGE \
  --command="python,src/batch_submit.py" \
  --tasks=1 --cpu=1 --memory=2Gi \
  --task-timeout=86400 \
  --service-account=$SA \
  --region=asia-northeast3

gcloud run jobs create kg-batch-collect \
  --image=$IMAGE \
  --command="python,src/batch_collect.py" \
  --tasks=20 --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3
```

---

## 1-C. Graph + Embedding + Mapping (1주) — Week 8~9

> standard.1에서 4주(Graph 2주 + Mapping 2주)를 1주로 압축.
> 근거: MVP 1,000건이므로 Graph 적재 ~30분, Embedding ~1시간, Mapping ~1시간.
> Graph 적재 모듈은 1-B 대기 시간에 이미 구현 완료.
> **참고**: 1-C는 실행 시간 기반 1주. 테스트/검증/백업은 1-D에서 별도 0.5~1주 할당.

| # | 작업 | 담당 | 시간 |
|---|---|---|---|
| 1-C-1 | CompanyContext → Neo4j 로더 (MERGE) | DE | 0.5일 (1-B-13에서 선행) |
| 1-C-2 | CandidateContext → Neo4j 로더 (MERGE) | DE | 0.5일 (1-B-13에서 선행) |
| 1-C-3 | **Organization Entity Resolution** [standard.1-3] | MLE | 1일 |
| 1-C-4 | Industry 마스터 노드 적재 | DE | 0.5일 |
| 1-C-5 | Vacancy→REQUIRES_ROLE→Role 관계 | MLE | 0.5일 |
| 1-C-6 | Vector Index 적재 (Vertex AI Embedding) | DE | 0.5일 |
| 1-C-7 | MappingFeatures 계산 모듈 | MLE | 1일 |
| 1-C-8 | MAPPED_TO 관계 적재 | DE | 0.5일 |
| 1-C-9 | BigQuery mapping_features 적재 | DE | 0.5일 |
| 1-C-10 | **Graph 적재 checkpoint 구현** [standard.1-5] | DE | 포함됨 |
| 1-C-11 | Idempotency 테스트 (동일 데이터 2회) | 공동 | 0.5일 |
| 1-C-12 | **E2E 통합 테스트 + 50건 수동 검증** | 공동 | 1일 |

### [standard.1-3] Organization Entity Resolution 설계

```
ER 알고리즘 단계:
  1단계: 사전 매칭 — company_alias.json 기반
         (삼성전자(주) → 삼성전자, Samsung Electronics → 삼성전자)
  2단계: 문자열 유사도 — Jaro-Winkler (threshold ≥ 0.85) 또는 편집거리
  3단계: (NICE 접근 가능 시) 사업자등록번호 기반 최종 확인

구현 주의:
  - Phase 0-3 프로파일링에서 회사명 변형 패턴 분석 (1,000건 샘플 기반)
  - "삼성전자" vs "삼성전자(주)" vs "Samsung Electronics" vs "삼성전자 DS부문" 패턴 식별
  - ER 실패 시 동일 회사가 여러 Organization 노드로 생성 → Graph 품질 직결

정확도 목표:
  - Precision ≥ 95% (잘못된 병합 방지)
  - Recall ≥ 80% (미병합 허용, 수동 검수로 보완)
```

### [R-9] Graph 적재 네트워크 레이턴시 대응

```
도쿄(Neo4j)↔서울(Cloud Run) 간 RTT ~30-50ms
Batch 크기 비교 (1-C-10 벤치마크):
  - 배치 크기 100건: 병렬성 낮음, RTT 오버헤드 약
  - 배치 크기 500건: 균형 잡힘 (기본값)
  - 배치 크기 1,000건: RTT 오버헤드 최소, 메모리 증가

Phase 1 MVP에서는 기본 500건 배치로 실행.
UNWIND 구문으로 단일 트랜잭션 내 다수 건 처리.
벤치마크 결과에 따라 Phase 2 BATCH_SIZE 조정 (최대 1,000).
```

### [standard.1-5] Graph 적재 Checkpoint 구현

```python
# src/graph_load.py — batch 단위 checkpoint
from google.cloud import bigquery
from neo4j import GraphDatabase

BATCH_SIZE = 500  # 트랜잭션 단위 (1-C-10 벤치마크 기반) [R-9]

def get_last_successful_batch(bq_client, pipeline: str) -> int:
    """[standard.1-5] 마지막으로 성공한 batch 인덱스 조회"""
    query = f"""
        SELECT MAX(batch_idx) as last_idx FROM graphrag_kg.batch_checkpoint
        WHERE pipeline = '{pipeline}' AND status = 'SUCCESS'
    """
    result = bq_client.query(query).result()
    last_idx = list(result)[0].last_idx
    return last_idx if last_idx is not None else -1

def record_batch_checkpoint(bq_client, pipeline: str, batch_idx: int, status: str):
    """[standard.1-5] batch 처리 완료 기록"""
    rows = [{
        "pipeline": pipeline,
        "batch_idx": batch_idx,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
    }]
    bq_client.insert_rows_json("graphrag_kg.batch_checkpoint", rows)

def load_contexts_to_neo4j(contexts: list, bq_client, neo4j_driver):
    """[standard.1-5] batch 단위 checkpoint로 중단 후 재시작 지원"""
    last_batch = get_last_successful_batch(bq_client, "graph_load")
    print(f"[CHECKPOINT] Last successful batch: {last_batch}")

    for batch_idx in range(0, len(contexts), BATCH_SIZE):
        if batch_idx <= last_batch:
            print(f"[SKIP] Batch {batch_idx} already processed")
            continue  # [standard.1-5] 이미 처리된 batch skip

        batch = contexts[batch_idx:batch_idx + BATCH_SIZE]

        try:
            with neo4j_driver.session() as session:
                session.execute_write(lambda tx: merge_batch(tx, batch))

            # checkpoint 기록
            record_batch_checkpoint(bq_client, "graph_load", batch_idx, "SUCCESS")
            print(f"[SUCCESS] Batch {batch_idx} ({len(batch)} items) loaded")

        except Exception as e:
            record_batch_checkpoint(bq_client, "graph_load", batch_idx, "FAILED")
            print(f"[ERROR] Batch {batch_idx} failed: {str(e)}")
            raise

    print(f"Graph 적재 완료: {len(contexts)} contexts")

def merge_batch(tx, batch: list):
    """Neo4j MERGE로 idempotent하게 batch 적재"""
    cypher = """
    UNWIND $batch AS item
    MERGE (p:Person {id: item.person_id})
    SET p += item.person_props
    MERGE (c:Chapter {id: item.chapter_id})
    SET c += item.chapter_props
    MERGE (p)-[:HAS_CHAPTER]->(c)
    """
    tx.run(cypher, batch=batch)
```

### Cloud Run Jobs 등록

```bash
# Graph 적재 Job (1,000건 → tasks=2로 충분)
gcloud run jobs create kg-graph-load \
  --image=$IMAGE \
  --command="python,src/graph_load.py" \
  --tasks=2 --max-retries=2 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3

# Embedding Job (1,000건 → tasks=2로 충분)
gcloud run jobs create kg-embedding \
  --image=$IMAGE \
  --command="python,src/generate_embeddings.py" \
  --tasks=2 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3

# Mapping Job (1,000건 → tasks=5로 충분)
gcloud run jobs create kg-mapping \
  --image=$IMAGE \
  --command="python,src/compute_mapping.py" \
  --tasks=5 \
  --cpu=4 --memory=8Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3
```

---

## 1-D. 테스트 + 검증 + 백업 (0.5~1주) — Week 9~10 [standard.1-6, standard.20]

> **standard.1 신규**: Phase 1에 체계적 테스트 전략 추가.
> Phase 0 PoC 50건을 regression test set으로 활용.
>
> **light.1 타임라인 근거**: 이 단계는 데이터 규모(1,000건)와 무관한 **알고리즘 개발 시간**이 지배적.
> Organization ER 알고리즘 설계, pytest 프레임워크 구축, regression test 작성, Go/No-Go 검증은
> 실행 시간이 아닌 개발 시간이 필요하므로 별도 0.5~1주를 할당한다.

| # | 작업 | 도구 | 산출물 |
|---|---|---|---|
| 1-D-1 | pytest 기반 단위 테스트 프레임워크 | pytest + fixtures | `tests/` |
| 1-D-2 | 파서 모듈 단위 테스트 (PDF/DOCX/HWP) | pytest | `tests/test_parsers.py` |
| 1-D-3 | LLM 파싱 3-tier 단위 테스트 | pytest | `tests/test_llm_parser.py` |
| 1-D-4 | Pydantic 모델 검증 테스트 | pytest | `tests/test_models.py` |
| 1-D-5 | **Golden 50건 regression test** | pytest + deepdiff | `tests/test_regression.py` |
| 1-D-6 | 통합 테스트 (파싱→Context→Graph E2E) | pytest | `tests/test_integration.py` |

### Regression Test 설계 — [standard.1-6]

```python
# tests/test_regression.py
"""
Phase 0 PoC 50건을 golden set으로 사용하여
프롬프트 변경 시 기존 품질 유지를 확인하는 regression test.
"""
import pytest
import json
from deepdiff import DeepDiff
from pathlib import Path

GOLDEN_DIR = Path("quality/golden_set/")
TOLERANCE = {
    "scope_type": 0.95,       # 95% 이상 일치 유지
    "outcome_f1": 0.90,       # F1 10% 이내 하락 허용
    "field_coverage": 0.85,   # 필드 커버리지 85% 이상 유지
}

@pytest.fixture
def golden_results():
    """Phase 0 PoC 50건의 검증 완료 결과"""
    results = []
    for f in sorted(GOLDEN_DIR.glob("*.json")):
        results.append(json.loads(f.read_text()))
    return results

def test_scope_type_regression(golden_results):
    """scope_type 분류 결과가 golden 대비 95% 이상 일치"""
    matches = 0
    for golden in golden_results:
        new_result = run_extraction(golden["input"])
        if new_result.scope_type == golden["expected"]["scope_type"]:
            matches += 1
    accuracy = matches / len(golden_results)
    assert accuracy >= TOLERANCE["scope_type"], \
        f"scope_type regression: {accuracy:.2%} < {TOLERANCE['scope_type']:.2%}"

def test_field_coverage_regression(golden_results):
    """추출 필드 커버리지가 golden 대비 85% 이상 유지"""
    for golden in golden_results:
        new_result = run_extraction(golden["input"])
        expected_fields = set(golden["expected"].keys())
        actual_fields = {k for k, v in new_result.dict().items() if v is not None}
        coverage = len(actual_fields & expected_fields) / len(expected_fields)
        assert coverage >= TOLERANCE["field_coverage"], \
            f"Field coverage regression for {golden['id']}: {coverage:.2%}"

def test_outcome_f1_regression(golden_results):
    """F1 점수가 golden 대비 90% 이상 유지"""
    for golden in golden_results:
        new_result = run_extraction(golden["input"])
        new_f1 = compute_f1(new_result, golden["expected"])
        golden_f1 = golden["expected"].get("f1", 1.0)
        ratio = new_f1 / golden_f1 if golden_f1 > 0 else 1.0
        assert ratio >= TOLERANCE["outcome_f1"], \
            f"F1 regression for {golden['id']}: {new_f1:.2%} (ratio {ratio:.2%})"
```

---

## 오케스트레이션 (Makefile) — [standard.24]

> Phase 1은 Makefile 기반 오케스트레이션으로 간단하게 관리.
> Phase 2에서 Cloud Workflows 전환으로 고도화 예정. [standard.24]

```makefile
# Makefile — Phase 1 오케스트레이션
.PHONY: test parse dedup company-ctx candidate-ctx-prepare candidate-ctx-submit \
        candidate-ctx-collect graph-load embedding mapping full-pipeline status backup

# 테스트 [standard.1-6]
test:
	pytest tests/ -v --tb=short

test-regression:
	pytest tests/test_regression.py -v

# 파이프라인 단계별 실행
parse:
	gcloud run jobs execute kg-parse-resumes --region=asia-northeast3 --wait

dedup:
	gcloud run jobs execute kg-dedup-resumes --region=asia-northeast3 --wait

company-ctx:
	gcloud run jobs execute kg-company-ctx --region=asia-northeast3 --wait

candidate-ctx-prepare:
	gcloud run jobs execute kg-batch-prepare --region=asia-northeast3 --wait

candidate-ctx-submit:
	gcloud run jobs execute kg-batch-submit --region=asia-northeast3 --wait

candidate-ctx-collect:
	gcloud run jobs execute kg-batch-collect --region=asia-northeast3 --wait

graph-load:
	gcloud run jobs execute kg-graph-load --region=asia-northeast3 --wait

embedding:
	gcloud run jobs execute kg-embedding --region=asia-northeast3 --wait

mapping:
	gcloud run jobs execute kg-mapping --region=asia-northeast3 --wait

# E2E 전체 파이프라인
full-pipeline: parse dedup company-ctx candidate-ctx-prepare candidate-ctx-submit \
               candidate-ctx-collect graph-load embedding mapping
	@echo "Full pipeline completed"

# 진행 상태 확인
status:
	@echo "=== Parsing Status ==="
	bq query --nouse_legacy_sql 'SELECT status, COUNT(*) as cnt FROM graphrag_kg.processing_log WHERE pipeline="parse" GROUP BY status'
	@echo ""
	@echo "=== Batch Tracking Status ==="
	bq query --nouse_legacy_sql 'SELECT status, COUNT(*) as cnt FROM graphrag_kg.batch_tracking GROUP BY status'
	@echo ""
	@echo "=== Graph Load Checkpoint ==="
	bq query --nouse_legacy_sql 'SELECT batch_idx, status FROM graphrag_kg.batch_checkpoint WHERE pipeline="graph_load" ORDER BY batch_idx DESC LIMIT 5'

# Neo4j 백업 [standard.20]
backup:
	@echo "Backing up Neo4j data..."
	cypher-shell -u neo4j -p $${NEO4J_PASSWORD} \
	  "CALL apoc.export.json.all('/tmp/phase1_backup.json', {useTypes: true})"
	gsutil cp /tmp/phase1_backup.json gs://graphrag-kg-data/backups/neo4j/$$(date +%Y%m%d)/
	@echo "Neo4j backup completed: gs://graphrag-kg-data/backups/neo4j/$$(date +%Y%m%d)/"
	cypher-shell -u neo4j -p $${NEO4J_PASSWORD} \
	  "MATCH (n) RETURN labels(n) AS label, count(n) AS cnt"
```

---

## Cloud Run Jobs 전체 요약 (Phase 1 MVP 규모)

| Job 이름 | 용도 | CPU/Memory | Tasks | Timeout | 예상 시간 |
|---|---|---|---|---|---|
| `kg-parse-resumes` | 이력서 파싱 | 2/4GB | 50 | 3600s | 30분 (1K건) |
| `kg-dedup-resumes` | 중복 제거 | 4/8GB | 1 | 7200s | 10분 (1K건) |
| `kg-batch-prepare` | Batch 요청 생성 | 2/4GB | 10 | 3600s | 5분 |
| `kg-batch-submit` | Batch 제출+폴링 | 1/2GB | 1 | 86400s | 대기 (24h SLA) |
| `kg-batch-collect` | 응답 수집 | 2/4GB | 20 | 3600s | 10분 |
| `kg-company-ctx` | CompanyContext | 2/4GB | 5 | 3600s | 15분 |
| `kg-graph-load` | Graph 적재 | 2/4GB | 2 | 3600s | 30분 |
| `kg-embedding` | Embedding | 2/4GB | 2 | 3600s | 30분 |
| `kg-mapping` | MappingFeatures | 4/8GB | 5 | 3600s | 20분 |
| `kg-industry-load` | Industry 마스터 | 1/2GB | 1 | 600s | 5분 |

---

## Phase 1 완료 산출물 (Week 9~10)

```
□ E2E 파이프라인 동작 (JD 100건 + 이력서 1,000건)
□ Neo4j Graph (Person, Chapter, Organization, Vacancy, Industry, Skill, Role)
□ Vector Index (chapter_embedding, vacancy_embedding)
□ mapping_features BigQuery 테이블
□ MAPPED_TO 관계 Graph 반영
□ 50건 수동 검증 결과

# standard.1 추가 산출물
□ Makefile 기반 파이프라인 실행 스크립트 [standard.24]
□ pytest 테스트 스위트 (단위 + 통합 + regression) [standard.1-6]
□ Golden 50건 regression test 통과 [standard.1-6]
□ Docker 이미지 + 10개 Cloud Run Jobs 등록
□ LLM 파싱 실패율 리포트 (tier1/tier3 비율)
□ 적재 벤치마크 (1,000건 → 450K 추정 노드/엣지) [R-9]
□ Neo4j 데이터 백업 (APOC export → GCS) [standard.20]
  └─ gs://graphrag-kg-data/backups/neo4j/{YYYYMMDD}/phase1_backup.json
  └─ 노드/엣지 수 기록 (검증용)
```

### Phase 2 진행 Go/No-Go 게이트 [standard.20]

| 기준 | 최소 통과 | 미달 시 대응 |
|------|----------|------------|
| **E2E 파이프라인 동작** | JD 100 + 이력서 1,000건 성공 | Phase 1 연장 (최대 2주) |
| **파싱 실패율** (tier3_fail) | < 5% | 프롬프트 수정 (+0.5주) |
| **Regression test** | Golden 50건 전 항목 통과 | 실패 항목 프롬프트 수정 후 재실행 |
| **수동 검증** (50건) | 합격률 > 70% | 추출 로직 수정 (+1주) |
| **Idempotency 테스트** | 2회 적재 후 노드/엣지 수 불변 | MERGE 로직 수정 |
| **적재 벤치마크** | 450K 추정 < 1시간 | 병렬 Task 수 조정 [R-9] |
| **Neo4j 백업** | 백업 완료 + 노드/엣지 수 기록 | 백업 완료 전 Phase 2 진입 불가 |

**미달 판정 시**: Phase 1을 최대 2주 연장하여 보완. Phase 2에서 보완하는 것은 허용하지 않음 (기반 품질 문제가 확장 시 증폭되므로).

### [standard.20] Phase 1 완료 후 Neo4j 백업

```bash
# Phase 1 완료 후, Phase 2 Professional 전환 전 백업 실행
# 환경 변수 설정 필수: export NEO4J_PASSWORD=xxxx

# 1. cypher-shell로 모든 데이터 export
cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL apoc.export.json.all('/tmp/phase1_backup.json', {useTypes: true})"

# 2. GCS 업로드
BACKUP_DATE=$(date +%Y%m%d)
gsutil cp /tmp/phase1_backup.json gs://graphrag-kg-data/backups/neo4j/$BACKUP_DATE/

# 3. 노드/엣지 수 기록 (검증용)
echo "=== Node Count ===" > /tmp/backup_report.txt
cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (n) RETURN labels(n) AS label, count(n) AS cnt ORDER BY cnt DESC" \
  >> /tmp/backup_report.txt

echo "" >> /tmp/backup_report.txt
echo "=== Relationship Count ===" >> /tmp/backup_report.txt
cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS cnt ORDER BY cnt DESC" \
  >> /tmp/backup_report.txt

gsutil cp /tmp/backup_report.txt gs://graphrag-kg-data/backups/neo4j/$BACKUP_DATE/

echo "Neo4j backup completed: gs://graphrag-kg-data/backups/neo4j/$BACKUP_DATE/"
```

---

## 전체 일정 요약

```
Week 3~5: Phase 1-A (전처리 + CompanyContext)
  ├─ DE: 파싱, 중복제거, 기술/회사 사전 (2주)
  └─ MLE: CompanyContext 모듈 (2주)

Week 5~8: Phase 1-B (CandidateContext)
  ├─ Week 5~6: 모듈 구현 (DE+MLE)
  ├─ Week 7: Batch API 제출 + (대기) Graph 선행 구현
  └─ Week 8: Batch API 응답 수집 + Context 생성

Week 8~9: Phase 1-C (Graph + Embedding + Mapping)
  ├─ (대기 중 구현 완료) Graph 적재
  ├─ Embedding 생성
  └─ MappingFeatures + 관계 적재

Week 9~10: Phase 1-D (테스트 + 검증 + 백업) ← standard.1 개발 시간 반영
  ├─ Organization ER 알고리즘 설계+구현 (개발 시간)
  ├─ pytest 프레임워크 + regression test (개발 시간)
  ├─ E2E 통합 테스트 + 50건 수동 검증
  ├─ Neo4j 백업 (APOC export → GCS)
  └─ Go/No-Go 게이트 판정

→ **총 6.5~7주 (Week 3~9.5~10)**
```

---

## 핵심 특징 정리

### light.1 압축 (Week 10~12→6.5~7)

| 단계 | standard.1 시간 | light.1 시간 | 압축 기법 |
|------|--------|--------|---------|
| 전처리+Company | 4주 직렬 | 2주 병행 | DE/MLE 역할 분리 |
| CandidateContext | 4주 | 3주 | Batch API 대기 활용 |
| Graph+Embedding+Mapping | 4주 | 1주 | MVP 규모 + 선행 구현 |
| 테스트+검증+백업 | (포함) | 0.5~1주 | Org ER, regression test, Go/No-Go (개발 시간) |
| **합계** | **10~12주** | **6.5~7주** | **-42% 압축** |

### standard.1 품질 개선 통합

| 개선 항목 | 포함 | 세부 내용 |
|---------|------|---------|
| [standard.1-2] HWP 파서 | O | 1-A-1에 포함, `src/parsers/hwp.py` |
| [standard.1-5] Checkpoint | O | 파싱, Batch API, Graph 적재 3곳 |
| [standard.1-6] 테스트 | O | 1-D 신규 섹션, regression test |
| [standard.24] Makefile | O | Cloud Workflows 대체, Phase 2 전환 |
| [standard.20] 백업 | O | Go/No-Go 게이트 추가 |

### [R-9] 네트워크 레이턴시 대응

- 도쿄↔서울 RTT ~30-50ms 고려
- Batch 크기 비교 (100/500/1,000건)
- UNWIND 단일 트랜잭션 처리
- 벤치마크 기반 Phase 2 최적화
