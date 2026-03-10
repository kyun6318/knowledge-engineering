# Phase 1: MVP 파이프라인 (10~12주)

> **목적**: 전처리 → Context 생성 → Graph 적재 → MappingFeatures까지 E2E 파이프라인 완성.
> Phase 0 의사결정 결과를 반영하여 구현.
>
> **standard.1 변경**:
> - [standard.1-5] 파이프라인 레벨 checkpoint/재시작 전략 내장
> - [standard.1-6] 1-6에 테스트 인프라 + regression test 추가
> - [standard.24] Cloud Workflows 대신 Makefile로 오케스트레이션 (MVP 규모에 적합)
> - [standard.20] Phase 1 완료 시 Neo4j 백업 절차 추가
>
> **인력**: DE 1명 + MLE 1명 풀타임
> **산출물**: E2E 파이프라인 (JD 100건 + 이력서 1,000건 + Graph + MappingFeatures + MAPPED_TO)

---

## 1-1. 전처리 모듈 (2주) — Week 5-7

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-1-1 | PDF/DOCX 파서 모듈 | Cloud Run Job 코드 | `src/parsers/` |
| 1-1-2 | **HWP 파서 모듈** (Phase 0-4-7 결정 반영) [standard.1-2] | 동일 | `src/parsers/hwp.py` |
| 1-1-3 | 섹션 분할기 (Rule-based) | 동일 | `src/splitters/` |
| 1-1-4 | 경력 블록 분리기 | 동일 | |
| 1-1-5 | PII 마스킹 모듈 (offset mapping 보존) | 동일 | `src/pii/` |
| 1-1-6 | 이력서 중복 제거 모듈 (SimHash) | 동일 | `src/dedup/` |
| 1-1-7 | JD 파서 + 섹션 분할 | 동일 | |
| 1-1-8 | 기술 사전 (2,000개) + 회사 사전 구축 | GCS | `reference/` |
| 1-1-9 | Docker 이미지 빌드 + Job 등록 | Cloud Build + Cloud Run | |

### Cloud Run Jobs 등록 — [standard.24] 단일 이미지 + --command 인자

```bash
IMAGE=asia-northeast3-docker.pkg.dev/graphrag-kg/kg-pipeline/kg-pipeline:latest
SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com

# Phase 1: 단일 이미지, --command로 모듈 선택 (11개 Job 분리 불필요)
# 파싱 Job
gcloud run jobs create kg-parse-resumes \
  --image=$IMAGE \
  --command="python,src/parse_resumes.py" \
  --tasks=50 --max-retries=2 \
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
```

### 파싱 Job 핵심 로직 — [standard.1-5] checkpoint 내장

```python
# kg-parse-resumes/main.py
import os, json
from google.cloud import storage, bigquery

TASK_INDEX = int(os.environ.get("CLOUD_RUN_TASK_INDEX", 0))
TASK_COUNT = int(os.environ.get("CLOUD_RUN_TASK_COUNT", 1))

def get_already_processed(bq_client, pipeline: str) -> set:
    """[standard.1-5] 이미 성공한 item을 checkpoint로 조회"""
    query = f"""
        SELECT item_id FROM graphrag_kg.processing_log
        WHERE pipeline = '{pipeline}' AND status = 'SUCCESS'
    """
    return {row.item_id for row in bq_client.query(query)}

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

## 1-2. CompanyContext 파이프라인 (1~2주) — Week 7-9

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-2-1 | CompanyContext Pydantic 모델 정의 | 코드 | `src/models/company.py` |
| 1-2-2 | NICE Lookup 모듈 | Cloud Functions | `src/nice/` |
| 1-2-3 | stage_estimate Rule 엔진 | 코드 | |
| 1-2-4 | LLM 추출 프롬프트 (vacancy + role 통합) | GCS prompts/ | `vacancy_role_v1.txt` |
| 1-2-5 | operating_model 키워드 엔진 + LLM 보정 | 코드 | |
| 1-2-6 | Evidence 생성 모듈 + source_ceiling 적용 | 코드 | |
| 1-2-7 | 통합 테스트 (JD 100건) | Cloud Run Job | E2E 결과 |
| 1-2-8 | CompanyContext → GCS 저장 파이프라인 | Cloud Run Job | |

```bash
gcloud run jobs create kg-company-ctx \
  --image=$IMAGE \
  --command="python,src/company_context.py" \
  --tasks=5 --max-retries=1 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3
```

---

## 1-3. CandidateContext 파이프라인 (4주) — Week 9-13

> v7 변경: 3주 → 4주. LLM 파싱 실패 3-tier 구현 + chunk 관리에 추가 시간.

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-3-1 | CandidateContext Pydantic 모델 정의 | 코드 | `src/models/candidate.py` |
| 1-3-2 | Rule 추출 모듈 (날짜/회사/기술) | 코드 | `src/extractors/rule.py` |
| 1-3-3 | LLM 추출 프롬프트 (Experience별) | GCS prompts/ | `experience_extract_v1.txt` |
| 1-3-4 | LLM 추출 프롬프트 (전체 커리어) | GCS prompts/ | `career_level_v1.txt` |
| 1-3-5 | WorkStyleSignals LLM 프롬프트 | 코드 | |
| 1-3-6 | PastCompanyContext NICE 역산 모듈 | Cloud Functions | |
| 1-3-7 | **LLM 파싱 실패 3-tier 구현** | 코드 | `src/shared/llm_parser.py` |
| 1-3-8 | Batch API 요청 생성 모듈 (1,000건/chunk) | Cloud Run Job | |
| 1-3-9 | **Batch API 제출/폴링 모듈 + batch_tracking** [standard.1-5] | Cloud Run Job | |
| 1-3-10 | **Chunk 상태 추적 인프라** | BigQuery | `chunk_status` 테이블 |
| 1-3-11 | 통합 테스트 (이력서 200건) | Cloud Run Job | E2E 결과 |
| 1-3-12 | Batch API 연동 테스트 (1,000건) | Anthropic Batch API | |

### LLM 파싱 실패 3-tier 전략

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

### Batch API 제출 Job — [standard.1-5] batch_tracking 내장

```python
# kg-batch-submit/main.py
import anthropic, json, time
from google.cloud import storage, secretmanager, bigquery

def main():
    api_key = get_anthropic_key()
    anthropic_client = anthropic.Anthropic(api_key=api_key)
    gcs = storage.Client()
    bq = bigquery.Client()
    bucket = gcs.bucket("graphrag-kg-data")

    request_blobs = list(bucket.list_blobs(prefix="batch-api/requests/"))
    MAX_CONCURRENT = 5  # [standard.1-4] Anthropic quota에 맞게 조정
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

def poll_and_collect(client, batches, bucket, bq):
    """[standard.1-5] 폴링 + 수집 + tracking 업데이트"""
    still_active = []
    for b in batches:
        status = client.messages.batches.retrieve(b["batch_id"])
        if status.processing_status == "ended":
            # 결과 수집
            collect_results(client, b["batch_id"], b["chunk_id"], bucket)
            # tracking 업데이트
            update_batch_tracking(bq, b["batch_id"], "COMPLETED", result_collected=True)
        else:
            still_active.append(b)
    return still_active

def track_batch(bq, batch_id, chunk_id, status, gcs_path):
    """[standard.1-5] BigQuery batch_tracking에 기록"""
    rows = [{
        "batch_id": batch_id,
        "chunk_id": chunk_id,
        "status": status,
        "submitted_at": datetime.utcnow().isoformat(),
        "gcs_request_path": gcs_path,
    }]
    bq.insert_rows_json("graphrag_kg.batch_tracking", rows)
```

---

## 1-4. Graph 적재 파이프라인 (2주) — Week 13-15

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-4-1 | CompanyContext → Neo4j 로더 (MERGE) | Cloud Run Job | |
| 1-4-2 | CandidateContext → Neo4j 로더 (MERGE) | Cloud Run Job | |
| 1-4-3 | Deterministic ID 생성 모듈 | 코드 | |
| 1-4-4 | Organization Entity Resolution 모듈 [R-4] | 코드 | |
| 1-4-5 | Industry 마스터 노드 적재 + 검증 | Cloud Run Job | |
| 1-4-6 | Vacancy→REQUIRES_ROLE→Role 관계 | 코드 | |
| 1-4-7 | Vector Index 적재 (Vertex AI Embedding) | Cloud Run Job | |
| 1-4-8 | Idempotency 테스트 (동일 데이터 2회 적재) | Neo4j | 노드/엣지 수 불변 확인 |
| 1-4-9 | 적재 벤치마크 (1,000건 → 500K 추정) + **도쿄↔서울 RTT 영향 측정** [R-9] | 측정 | |
| 1-4-10 | **Graph 적재 checkpoint 구현** [standard.1-5] | 코드 + BigQuery | batch 단위 재시작 |

### [R-4] Organization Entity Resolution 설계

```
ER 알고리즘 단계:
  1단계: 사전 매칭 — company_alias.json 기반 (삼성전자(주) → 삼성전자)
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
Phase 2에서 2.77M 노드 적재 시 RTT overhead 최소화 필요:
  - 1-4-9 벤치마크에서 배치 크기 100/500/1,000건 비교 측정
  - UNWIND 구문으로 단일 트랜잭션 내 다수 건 처리
  - 벤치마크 결과에 따라 BATCH_SIZE 조정 (기본 100 → 최대 1,000)
```

### [standard.1-5] Graph 적재 Checkpoint

```python
# src/graph_load.py — batch 단위 checkpoint

BATCH_SIZE = 100  # 트랜잭션 단위 (1-4-9 벤치마크 결과에 따라 조정) [R-9]

def load_contexts_to_neo4j(contexts: list, bq_client, neo4j_driver):
    """[standard.1-5] batch 단위 checkpoint로 중단 후 재시작 지원"""
    last_batch = get_last_successful_batch(bq_client, "graph_load")

    for batch_idx in range(0, len(contexts), BATCH_SIZE):
        if batch_idx <= last_batch:
            continue  # [standard.1-5] 이미 처리된 batch skip

        batch = contexts[batch_idx:batch_idx + BATCH_SIZE]

        with neo4j_driver.session() as session:
            session.execute_write(lambda tx: merge_batch(tx, batch))

        # checkpoint 기록
        record_batch_checkpoint(bq_client, "graph_load", batch_idx)

    print(f"Graph 적재 완료: {len(contexts)} contexts")
```

```bash
# Graph 적재 Job
gcloud run jobs create kg-graph-load \
  --image=$IMAGE \
  --command="python,src/graph_load.py" \
  --tasks=8 --max-retries=2 \
  --cpu=2 --memory=4Gi \
  --task-timeout=43200 \
  --service-account=$SA \
  --region=asia-northeast3

# Embedding Job
gcloud run jobs create kg-embedding \
  --image=$IMAGE \
  --command="python,src/generate_embeddings.py" \
  --tasks=10 \
  --cpu=2 --memory=4Gi \
  --task-timeout=21600 \
  --service-account=$SA \
  --region=asia-northeast3
```

---

## 1-5. MappingFeatures + MAPPED_TO (2주) — Week 15-17

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-5-1 | Candidate Shortlisting (Rule + Vector Search) | Cloud Run Job | |
| 1-5-2 | MappingFeatures 계산 모듈 | 코드 | |
| 1-5-3 | ScopeType→Seniority 변환 함수 | 코드 | |
| 1-5-4 | MAPPED_TO 관계 Graph 적재 | Cloud Run Job | |
| 1-5-5 | BigQuery mapping_features 테이블 적재 | BigQuery | |
| 1-5-6 | 매핑 50건 수동 검증 | 수동 | |
| 1-5-7 | **E2E 통합 테스트 (JD 100건 + 이력서 1,000건)** | 전체 파이프라인 | |

```bash
gcloud run jobs create kg-mapping \
  --image=$IMAGE \
  --command="python,src/compute_mapping.py" \
  --tasks=20 \
  --cpu=4 --memory=8Gi \
  --task-timeout=10800 \
  --service-account=$SA \
  --region=asia-northeast3
```

---

## 1-6. 테스트 인프라 + Regression Test (1주, 1-5와 병행) — Week 16-17 [standard.1-6]

> **standard.1 신규**: Phase 1에 체계적 테스트 전략 추가.
> Phase 0 PoC 50건을 regression test set으로 활용.

| # | 작업 | 도구 | 산출물 |
|---|---|---|---|
| 1-6-1 | pytest 기반 단위 테스트 프레임워크 | pytest + fixtures | `tests/` |
| 1-6-2 | 파서 모듈 단위 테스트 (PDF/DOCX/HWP) | pytest | `tests/test_parsers.py` |
| 1-6-3 | LLM 파싱 3-tier 단위 테스트 | pytest | `tests/test_llm_parser.py` |
| 1-6-4 | Pydantic 모델 검증 테스트 | pytest | `tests/test_models.py` |
| 1-6-5 | **Golden 50건 regression test** | pytest + deepdiff | `tests/test_regression.py` |
| 1-6-6 | 통합 테스트 (파싱→Context→Graph E2E) | pytest | `tests/test_integration.py` |
| 1-6-7 | CI 스크립트 (로컬 실행) | Makefile | |

### Regression Test 설계

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
```

### Makefile 기반 실행 — [standard.24]

```makefile
# Makefile — Phase 1 오케스트레이션 (Cloud Workflows 대신)
.PHONY: test parse dedup company-ctx candidate-ctx graph-load embedding mapping full-pipeline

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
full-pipeline: parse dedup company-ctx candidate-ctx-prepare candidate-ctx-submit candidate-ctx-collect graph-load embedding mapping
	@echo "Full pipeline completed"

# 진행 상태 확인
status:
	@echo "=== Chunk Status ==="
	bq query --nouse_legacy_sql 'SELECT status, COUNT(*) FROM graphrag_kg.chunk_status GROUP BY status'
	@echo "=== Batch Tracking ==="
	bq query --nouse_legacy_sql 'SELECT status, COUNT(*) FROM graphrag_kg.batch_tracking GROUP BY status'
```

---

## Cloud Run Jobs 전체 요약 — [standard.24] Phase 1 최소 구성

> Phase 1에서는 단일 이미지(`kg-pipeline`) + `--command` 인자로 모듈 선택.
> 개별 Job 분리는 Phase 2 성능 최적화 시점에 수행.

| Job 이름 | 용도 | CPU/Memory | 병렬 Tasks | Timeout | 예상 실행 시간 |
|---|---|---|---|---|---|
| `kg-parse-resumes` | 이력서 파싱 | 2 vCPU / 4GB | 50 | 3600s | 4~6시간 |
| `kg-dedup-resumes` | 중복 제거 | 4 vCPU / 8GB | 1 | 7200s | 1~2시간 |
| `kg-batch-prepare` | Batch API 요청 생성 | 2 vCPU / 4GB | 10 | 3600s | 1시간 |
| `kg-batch-submit` | Batch API 제출 (제출만, 즉시 종료) [R-8] | 1 vCPU / 2GB | 1 | 3600s | ~30분 |
| `kg-batch-poll` | Batch API 폴링 (Cloud Scheduler 30분 주기) [R-8] | 1 vCPU / 2GB | 1 | 600s | ~5분/회 |
| `kg-batch-collect` | 응답 수집+Context 생성 | 2 vCPU / 4GB | 20 | 3600s | 2~3시간 |
| `kg-company-ctx` | CompanyContext 생성 | 2 vCPU / 4GB | 5 | 3600s | 1~2시간 |
| `kg-graph-load` | Context → Neo4j 적재 | 2 vCPU / 4GB | 8 | 43200s | 8~12시간 |
| `kg-embedding` | Embedding + Vector Index | 2 vCPU / 4GB | 10 | 21600s | 4~6시간 |
| `kg-mapping` | MappingFeatures + BigQuery | 4 vCPU / 8GB | 20 | 10800s | 2~3시간 |
| `kg-industry-load` | Industry 마스터 적재 | 1 vCPU / 2GB | 1 | 600s | 5분 |
| `kg-dead-letter` | Dead-Letter 재처리 | 1 vCPU / 2GB | 1 | 3600s | 30분 |

---

## Phase 1 완료 산출물

```
□ E2E 파이프라인 동작 (JD 100건 + 이력서 1,000건)
□ Neo4j Graph (Person, Chapter, Organization, Vacancy, Industry, Skill, Role 노드)
□ Vector Index (chapter_embedding, vacancy_embedding)
□ mapping_features BigQuery 테이블
□ MAPPED_TO 관계 Graph 반영
□ 50건 수동 검증 결과
□ Makefile 기반 파이프라인 실행 스크립트 [standard.24]
□ pytest 테스트 스위트 (단위 + 통합 + regression) [standard.1-6]
□ Golden 50건 regression test 통과 [standard.1-6]
□ Docker 이미지 (단일 kg-pipeline) + 11개 Cloud Run Jobs 등록
□ Neo4j 데이터 백업 (APOC export 또는 대안 방법 → GCS) [standard.20, R-2]
  └─ gs://graphrag-kg-data/backups/neo4j/{date}/
□ 인력 추가 여부 의사결정 (Phase 2 크롤링 병행 가능 여부) [R-7]
```

### [R-7] Phase 1 → Phase 2 Go/No-Go 기준

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| E2E 파이프라인 | JD 100건 + 이력서 1,000건 정상 처리 | Phase 1 연장 (최대 2주) |
| Regression test | Golden 50건 전 항목 통과 | 실패 항목 프롬프트 수정 후 재실행 |
| 수동 검증 | 50건 중 치명적 결함 0건 | 결함 원인 분석 + 수정 후 재검증 |
| Neo4j 백업 | 백업 완료 + 노드/엣지 수 기록 | 백업 완료 전 Phase 2 진입 불가 |
| 적재 벤치마크 | 500K 추정 시간 산출 완료 [R-9] | 벤치마크 미완료 시 Phase 2 Graph 적재 리스크 |

**미달 판정 시**: Phase 1을 최대 2주 연장하여 보완. Phase 2에서 보완하는 것은 허용하지 않음 (기반 품질 문제가 확장 시 증폭되므로).

### [standard.20] Phase 1 완료 시 Neo4j 백업

```bash
# Phase 1 완료 후, Phase 2 Professional 전환 전 백업
# Neo4j Browser 또는 cypher-shell에서 실행

# 1. 노드 + 관계 export
CALL apoc.export.json.all("phase1_backup.json", {useTypes: true})

# 2. GCS 업로드
gsutil cp phase1_backup.json gs://graphrag-kg-data/backups/neo4j/$(date +%Y%m%d)/

# 3. 노드/엣지 수 기록 (검증용)
MATCH (n) RETURN labels(n) AS label, count(n) AS cnt
# 예상: Person ~1K, Chapter ~5K, Organization ~500, ...
```
