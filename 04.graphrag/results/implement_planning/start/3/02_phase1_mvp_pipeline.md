# Phase 1: MVP 파이프라인 (10~12주)

> **목적**: 전처리 → Context 생성 → Graph 적재 → MappingFeatures까지 E2E 파이프라인 완성.
> Phase 0 의사결정 결과를 반영하여 구현.
>
> **인력**: DE 1명 + MLE 1명 풀타임
> **산출물**: E2E 파이프라인 (JD 100건 + 이력서 1,000건 + Graph + MappingFeatures + MAPPED_TO)

---

## 1-1. 전처리 모듈 (2주) — Week 5-7

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-1-1 | PDF/DOCX/HWP 파서 모듈 | Cloud Run Job 코드 | `src/parsers/` |
| 1-1-2 | 섹션 분할기 (Rule-based) | 동일 | `src/splitters/` |
| 1-1-3 | 경력 블록 분리기 | 동일 | |
| 1-1-4 | PII 마스킹 모듈 (offset mapping 보존) | 동일 | `src/pii/` |
| 1-1-5 | 이력서 중복 제거 모듈 (SimHash) | 동일 | `src/dedup/` |
| 1-1-6 | JD 파서 + 섹션 분할 | 동일 | |
| 1-1-7 | 기술 사전 (2,000개) + 회사 사전 구축 | GCS | `reference/` |
| 1-1-8 | Docker 이미지 빌드 + Job 등록 | Cloud Build + Cloud Run | |

### Cloud Run Jobs 등록

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
```

### 파싱 Job 핵심 로직

```python
# kg-parse-resumes/main.py
import os, json
from google.cloud import storage

TASK_INDEX = int(os.environ.get("CLOUD_RUN_TASK_INDEX", 0))
TASK_COUNT = int(os.environ.get("CLOUD_RUN_TASK_COUNT", 1))

def main():
    client = storage.Client()
    bucket = client.bucket("graphrag-kg-data")

    all_resumes = list_resumes(bucket, "raw/resumes/")
    my_resumes = partition(all_resumes, TASK_INDEX, TASK_COUNT)

    for resume_blob in my_resumes:
        try:
            raw_bytes = resume_blob.download_as_bytes()
            parsed = parse_resume(raw_bytes, resume_blob.name)

            sections = split_sections(parsed.text)
            blocks = split_career_blocks(sections)
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
| 1-3-9 | Batch API 제출/폴링 모듈 | Cloud Run Job | |
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

### Batch API 제출 Job

```python
# kg-batch-submit/main.py
import anthropic, json, time
from google.cloud import storage, secretmanager

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

    while active_batches:
        active_batches = poll_and_collect(anthropic_client, active_batches, bucket)
        if active_batches:
            time.sleep(300)
```

---

## 1-4. Graph 적재 파이프라인 (2주) — Week 13-15

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-4-1 | CompanyContext → Neo4j 로더 (MERGE) | Cloud Run Job | |
| 1-4-2 | CandidateContext → Neo4j 로더 (MERGE) | Cloud Run Job | |
| 1-4-3 | Deterministic ID 생성 모듈 | 코드 | |
| 1-4-4 | Organization Entity Resolution 모듈 | 코드 | |
| 1-4-5 | Industry 마스터 노드 적재 + 검증 | Cloud Run Job | |
| 1-4-6 | Vacancy→REQUIRES_ROLE→Role 관계 | 코드 | |
| 1-4-7 | Vector Index 적재 (Vertex AI Embedding) | Cloud Run Job | |
| 1-4-8 | Idempotency 테스트 (동일 데이터 2회 적재) | Neo4j | 노드/엣지 수 불변 확인 |
| 1-4-9 | 적재 벤치마크 (1,000건 → 500K 추정) | 측정 | |

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

## Cloud Run Jobs 전체 요약

| Job 이름 | 용도 | CPU/Memory | 병렬 Tasks | Timeout | 예상 실행 시간 |
|---|---|---|---|---|---|
| `kg-parse-resumes` | 이력서 파싱 | 2 vCPU / 4GB | 50 | 3600s | 4~6시간 |
| `kg-dedup-resumes` | 중복 제거 | 4 vCPU / 8GB | 1 | 7200s | 1~2시간 |
| `kg-batch-prepare` | Batch API 요청 생성 | 2 vCPU / 4GB | 10 | 3600s | 1시간 |
| `kg-batch-submit` | Batch API 제출+폴링 | 1 vCPU / 2GB | 1 | 86400s | 대기 (24h SLA) |
| `kg-batch-collect` | 응답 수집+Context 생성 | 2 vCPU / 4GB | 20 | 3600s | 2~3시간 |
| `kg-company-ctx` | CompanyContext 생성 | 2 vCPU / 4GB | 5 | 3600s | 1~2시간 |
| `kg-graph-load` | Context → Neo4j 적재 | 2 vCPU / 4GB | 8 | 43200s | 8~12시간 |
| `kg-embedding` | Embedding + Vector Index | 2 vCPU / 4GB | 10 | 21600s | 4~6시간 |
| `kg-mapping` | MappingFeatures + BigQuery | 4 vCPU / 8GB | 20 | 10800s | 2~3시간 |
| `kg-industry-load` | Industry 마스터 적재 | 1 vCPU / 2GB | 1 | 600s | 5분 |
| `kg-dead-letter` | Dead-Letter 재처리 | 1 vCPU / 2GB | 1 | 3600s | 30분 |

---

## 오케스트레이션 (Cloud Workflows — 권장)

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

    - notify:
        call: http.post
        args:
          url: ${args.slack_webhook_url}
          body:
            text: ${"KG Pipeline 완료: run_id=" + run_id}
```

---

## Phase 1 완료 산출물

```
□ E2E 파이프라인 동작 (JD 100건 + 이력서 1,000건)
□ Neo4j Graph (Person, Chapter, Organization, Vacancy, Industry, Skill, Role 노드)
□ Vector Index (chapter_embedding, vacancy_embedding)
□ mapping_features BigQuery 테이블
□ MAPPED_TO 관계 Graph 반영
□ 50건 수동 검증 결과
□ Cloud Workflows 파이프라인 배포
□ Docker 이미지 + 11개 Cloud Run Jobs 등록
```
