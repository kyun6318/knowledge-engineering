# Knowledge Graph 구축 GCP 실행 계획

> **원본**: `create-kg/plans/v5/` (5개 문서)의 파이프라인 설계를 GCP 환경에서 구현하기 위한 인프라 + 실행 계획.
> **참고**: `ml-platform/plans/api-test-3day-v3.md`의 GCP 서비스 검증 결과를 반영.
>
> 작성일: 2026-03-08

---

## 1. GCP 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GCP Project: create-kg                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [데이터 레이어]                                                     │
│  ├─ GCS: gs://create-kg-data/                                      │
│  │   ├─ raw/resumes/          (이력서 원본 150GB)                    │
│  │   ├─ raw/jds/              (JD 원본)                             │
│  │   ├─ parsed/resumes/       (파싱 결과 JSON)                      │
│  │   ├─ parsed/jds/           (JD 파싱 결과)                        │
│  │   ├─ contexts/company/     (CompanyContext JSON)                  │
│  │   ├─ contexts/candidate/   (CandidateContext JSON)               │
│  │   ├─ mapping-features/     (MappingFeatures JSON)                │
│  │   ├─ prompts/              (프롬프트 버전 관리)                   │
│  │   ├─ dead-letter/          (처리 실패 건)                         │
│  │   └─ backups/              (Context JSON 버전 백업)               │
│  │                                                                   │
│  ├─ BigQuery: create_kg                                             │
│  │   ├─ mapping_features      (서빙 테이블)                          │
│  │   ├─ processing_log        (처리 이력/모니터링)                   │
│  │   └─ quality_metrics       (품질 평가 결과)                       │
│  │                                                                   │
│  └─ Neo4j AuraDB (외부 관리형)                                      │
│      ├─ Person, Chapter, Organization, Vacancy, ...                 │
│      └─ Vector Index (chapter_embedding, vacancy_embedding)          │
│                                                                     │
│  [컴퓨팅 레이어]                                                     │
│  ├─ Cloud Run Jobs        (배치 파이프라인 실행)                     │
│  ├─ Cloud Functions       (이벤트 트리거, 경량 처리)                 │
│  └─ Compute Engine (GPU)  (On-premise SLM 시나리오 C 전용)          │
│                                                                     │
│  [오케스트레이션]                                                    │
│  ├─ Cloud Workflows       (파이프라인 단계 간 의존성 관리)           │
│  └─ Cloud Scheduler       (증분 처리 일일 배치 트리거)               │
│                                                                     │
│  [LLM API (외부)]                                                   │
│  ├─ Anthropic Batch API   (Claude Haiku 4.5 — Primary)              │
│  ├─ Anthropic API         (Claude Sonnet 4.6 — Fallback/PoC)        │
│  └─ OpenAI API            (text-embedding-3-small)                  │
│                                                                     │
│  [모니터링]                                                          │
│  ├─ Cloud Monitoring      (인프라 메트릭)                            │
│  ├─ Cloud Logging         (애플리케이션 로그)                        │
│  └─ Grafana (Cloud Run)   (커스텀 대시보드 — BigQuery 연동)          │
│                                                                     │
│  [보안]                                                              │
│  ├─ Secret Manager        (API 키: Anthropic, OpenAI, Neo4j)        │
│  ├─ IAM                   (서비스 계정 최소 권한)                    │
│  └─ VPC Service Controls  (PII 데이터 유출 방지, 선택적)            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. GCP 서비스 매핑

### 2.1 파이프라인별 GCP 서비스

| v5 파이프라인 | GCP 서비스 | 선택 근거 |
|---|---|---|
| **이력서 파싱 (전처리)** | Cloud Run Jobs | CPU 집약, 병렬 처리 필요, Job 단위 실행 |
| **이력서 중복 제거** | Cloud Run Jobs | 전처리 단계에서 일괄 실행 |
| **CompanyContext 생성** | Cloud Run Jobs + Anthropic Batch API | LLM 호출은 Batch API, 결과 조합은 Cloud Run |
| **CandidateContext 생성** | Cloud Run Jobs + Anthropic Batch API | 동일 |
| **Graph 적재** | Cloud Run Jobs | Neo4j AuraDB 연결, 트랜잭션 배치 처리 |
| **Vector Index 적재** | Cloud Run Jobs + OpenAI API | Embedding 생성 → Neo4j SET |
| **MappingFeatures 계산** | Cloud Run Jobs | Rule + Embedding cosine, LLM 불필요 |
| **BigQuery 적재** | Cloud Run Jobs + BigQuery API | JSON → BigQuery 로드 |
| **증분 처리 (운영)** | Cloud Functions + Cloud Scheduler | 일일 트리거, 경량 처리 |
| **Dead-Letter 재처리** | Cloud Scheduler + Cloud Run Jobs | 일 1회 자동 재시도 |
| **NICE DB 조회** | Cloud Functions | 경량 lookup, 캐싱 가능 |

### 2.2 Cloud Run Jobs 선택 근거

v5 파이프라인은 **장시간 배치 처리**가 핵심이므로 Cloud Run Jobs가 적합하다:

| 비교 항목 | Cloud Run Jobs | Cloud Functions | Dataflow | GKE |
|---|---|---|---|---|
| 최대 실행 시간 | 24시간 | 9분 (2세대) | 무제한 | 무제한 |
| 병렬 처리 | Task 단위 병렬 (최대 10,000) | 인스턴스 자동 확장 | Worker 자동 확장 | Pod 단위 |
| 비용 | 실행 시간만 과금 | 호출+실행 시간 | 처리량 과금 | 상시 과금 |
| 셋업 복잡도 | 낮음 (Docker 이미지만) | 최저 | 높음 (Apache Beam) | 높음 |
| GPU 지원 | 지원 (L4/A100) | 미지원 | 미지원 | 지원 |
| **적합도** | **최적** | 트리거/경량만 | 과도 | 과도 |

---

## 3. GCS 버킷 구조

```yaml
gs://create-kg-data/
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
│   ├── tech_dictionary.json         # 기술 사전 (2,000+ 기술명)
│   ├── company_alias.json           # 회사명 정규화 사전
│   └── role_alias.json              # 직무명 정규화 사전
│
├── parsed/
│   ├── resumes/                     # 파싱 결과
│   │   └── {candidate_id}.json      # {text, sections, blocks, metadata}
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
│   │       └── latest.json          # 최신 버전 symlink
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

## 4. Cloud Run Jobs 설계

### 4.1 Job 정의

```yaml
# cloudbuild.yaml — 파이프라인 이미지 빌드
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/${PROJECT_ID}/kg-pipeline:${SHORT_SHA}', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/${PROJECT_ID}/kg-pipeline:${SHORT_SHA}']
```

| Job 이름 | 용도 | CPU/Memory | 병렬 Task 수 | 예상 실행 시간 |
|---|---|---|---|---|
| `kg-parse-resumes` | 이력서 파싱 (PDF/DOCX/HWP → JSON) | 2 vCPU / 4GB | 50 (10,000건/task) | 4~6시간 |
| `kg-dedup-resumes` | 이력서 중복 제거 | 4 vCPU / 8GB | 1 | 1~2시간 |
| `kg-batch-prepare` | Batch API 요청 파일 생성 (1,000건/chunk) | 2 vCPU / 4GB | 10 | 1시간 |
| `kg-batch-submit` | Anthropic Batch API 제출 + 폴링 | 1 vCPU / 2GB | 1 (순차) | 대기 (24시간 SLA) |
| `kg-batch-collect` | Batch API 응답 수집 + Context JSON 생성 | 2 vCPU / 4GB | 20 | 2~3시간 |
| `kg-graph-load` | Context → Neo4j 적재 | 2 vCPU / 4GB | 8 (병렬 worker) | 8~12시간 |
| `kg-embedding` | Embedding 생성 + Neo4j Vector Index 적재 | 2 vCPU / 4GB | 10 | 4~6시간 |
| `kg-mapping` | MappingFeatures 계산 + BigQuery 적재 | 4 vCPU / 8GB | 20 | 2~3시간 |
| `kg-dead-letter` | Dead-Letter 재처리 | 1 vCPU / 2GB | 1 | 30분 |

### 4.2 파싱 Job 상세

```python
# kg-parse-resumes/main.py
import os
import json
from google.cloud import storage

TASK_INDEX = int(os.environ.get("CLOUD_RUN_TASK_INDEX", 0))
TASK_COUNT = int(os.environ.get("CLOUD_RUN_TASK_COUNT", 1))

def main():
    """Cloud Run Jobs Task — 이력서 파싱"""
    client = storage.Client()
    bucket = client.bucket("create-kg-data")

    # Task별 처리 범위 결정
    all_resumes = list_resumes(bucket, "raw/resumes/")
    my_resumes = partition(all_resumes, TASK_INDEX, TASK_COUNT)

    for resume_blob in my_resumes:
        try:
            # 1. 파일 형식 판별 + 파싱
            raw_bytes = resume_blob.download_as_bytes()
            parsed = parse_resume(raw_bytes, resume_blob.name)

            # 2. 섹션 분할 + 경력 블록 분리
            sections = split_sections(parsed.text)
            blocks = split_career_blocks(sections)

            # 3. 결과 저장
            result = {
                "candidate_id": extract_candidate_id(resume_blob.name),
                "source_path": resume_blob.name,
                "text": parsed.text,
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

### 4.3 Batch API 제출 Job 상세

```python
# kg-batch-submit/main.py
import anthropic
import json
import time
from google.cloud import storage, secretmanager

def get_api_key():
    """Secret Manager에서 Anthropic API 키 조회"""
    client = secretmanager.SecretManagerServiceClient()
    name = "projects/create-kg/secrets/anthropic-api-key/versions/latest"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")

def main():
    api_key = get_api_key()
    anthropic_client = anthropic.Anthropic(api_key=api_key)
    gcs_client = storage.Client()
    bucket = gcs_client.bucket("create-kg-data")

    # 1. 준비된 Batch 요청 파일 목록
    request_blobs = list(bucket.list_blobs(prefix="batch-api/requests/"))

    # 2. 동시 배치 제한 (5~10개)
    MAX_CONCURRENT = 5
    active_batches = []

    for blob in request_blobs:
        # 동시 배치 수 제한 대기
        while len(active_batches) >= MAX_CONCURRENT:
            active_batches = poll_and_collect(anthropic_client, active_batches, bucket)
            time.sleep(60)

        # 3. Batch API 제출
        requests = load_jsonl(blob)
        batch = anthropic_client.messages.batches.create(requests=requests)
        active_batches.append({
            "batch_id": batch.id,
            "chunk_id": extract_chunk_id(blob.name),
            "submitted_at": datetime.utcnow().isoformat(),
        })
        print(f"[Batch] Submitted: {batch.id} ({len(requests)} requests)")

        # 제출 로그 저장
        save_processing_log(bucket, "batch_submit", blob.name, batch.id)

    # 4. 남은 배치 완료 대기
    while active_batches:
        active_batches = poll_and_collect(anthropic_client, active_batches, bucket)
        if active_batches:
            time.sleep(300)  # 5분 간격 폴링

def poll_and_collect(client, batches, bucket):
    """완료된 배치 수집, 미완료 배치 반환"""
    remaining = []
    for b in batches:
        status = client.messages.batches.retrieve(b["batch_id"])
        if status.processing_status == "ended":
            # 결과 수집 → GCS 저장
            results = list(client.messages.batches.results(b["batch_id"]))
            save_jsonl(bucket,
                      f"batch-api/responses/batch_{b['chunk_id']}_result.jsonl",
                      results)
            print(f"[Batch] Completed: {b['batch_id']} ({len(results)} results)")
        else:
            remaining.append(b)
    return remaining
```

### 4.4 Graph 적재 Job 상세

```python
# kg-graph-load/main.py
import os
from neo4j import GraphDatabase
from google.cloud import storage, secretmanager

TASK_INDEX = int(os.environ.get("CLOUD_RUN_TASK_INDEX", 0))
TASK_COUNT = int(os.environ.get("CLOUD_RUN_TASK_COUNT", 1))
BATCH_SIZE = 100  # 트랜잭션당 처리 건수

def get_neo4j_credentials():
    client = secretmanager.SecretManagerServiceClient()
    uri = access_secret(client, "neo4j-uri")
    user = access_secret(client, "neo4j-user")
    password = access_secret(client, "neo4j-password")
    return uri, user, password

def main():
    uri, user, password = get_neo4j_credentials()
    driver = GraphDatabase.driver(uri, auth=(user, password))

    gcs = storage.Client()
    bucket = gcs.bucket("create-kg-data")

    # Task별 처리 범위 — Company + Candidate Context
    all_contexts = list_context_files(bucket)
    my_contexts = partition(all_contexts, TASK_INDEX, TASK_COUNT)

    with driver.session() as session:
        batch = []
        for ctx_blob in my_contexts:
            ctx = load_json(ctx_blob)

            if ctx_blob.name.startswith("contexts/company/"):
                batch.append(("company", ctx))
            else:
                batch.append(("candidate", ctx))

            # 배치 단위 트랜잭션
            if len(batch) >= BATCH_SIZE:
                execute_batch(session, batch)
                batch = []

        if batch:
            execute_batch(session, batch)

    driver.close()

def execute_batch(session, batch):
    """트랜잭션 내에서 배치 적재 — Deterministic ID + MERGE"""
    def _tx(tx):
        for ctx_type, ctx in batch:
            if ctx_type == "company":
                load_company_to_graph(ctx, tx)
            else:
                load_candidate_to_graph(ctx, tx)

    try:
        session.execute_write(_tx)
    except Exception as e:
        # 배치 실패 시 건별 재시도
        for ctx_type, ctx in batch:
            try:
                session.execute_write(
                    lambda tx: load_company_to_graph(ctx, tx)
                    if ctx_type == "company"
                    else load_candidate_to_graph(ctx, tx)
                )
            except Exception as e2:
                save_dead_letter_item(ctx_type, ctx, str(e2))
```

---

## 5. Cloud Workflows 오케스트레이션

### 5.1 전체 파이프라인 워크플로우

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
          body:
            overrides:
              containerOverrides:
                - env:
                    - name: RUN_ID
                      value: ${run_id}
        result: dedup_result

    # Phase 2: Batch API 요청 준비 + 제출
    - prepare_batches:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-batch-prepare"}
          location: ${region}
        result: prepare_result

    - submit_batches:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-batch-submit"}
          location: ${region}
        result: submit_result
        # 이 단계는 Batch API 응답 대기 (최대 24시간)

    # Phase 3: 결과 수집 + Graph 적재 (병렬)
    - collect_and_load:
        parallel:
          branches:
            - collect_results:
                steps:
                  - run_collect:
                      call: googleapis.run.v1.namespaces.jobs.run
                      args:
                        name: ${"namespaces/" + project_id + "/jobs/kg-batch-collect"}
                        location: ${region}

            - load_company_graph:
                steps:
                  - wait_for_company_contexts:
                      call: sys.sleep
                      args:
                        seconds: 300  # collect 시작 후 5분 대기
                  - run_company_load:
                      call: googleapis.run.v1.namespaces.jobs.run
                      args:
                        name: ${"namespaces/" + project_id + "/jobs/kg-graph-load"}
                        location: ${region}
                        body:
                          overrides:
                            taskCount: 8
                            containerOverrides:
                              - env:
                                  - name: CONTEXT_TYPE
                                    value: "company"

    - load_candidate_graph:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-graph-load"}
          location: ${region}
          body:
            overrides:
              taskCount: 8
              containerOverrides:
                - env:
                    - name: CONTEXT_TYPE
                      value: "candidate"

    # Phase 4: Embedding + MappingFeatures (순차)
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

    # Phase 5: 완료 알림
    - notify_completion:
        call: http.post
        args:
          url: ${args.slack_webhook_url}
          body:
            text: ${"KG Pipeline 완료: run_id=" + run_id}
```

### 5.2 증분 처리 워크플로우

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
              # 소량이므로 실시간 API 호출 (Batch API 불필요)
              call: googleapis.run.v1.namespaces.jobs.run
              args:
                name: ${"namespaces/" + project_id + "/jobs/kg-realtime-extract"}
                location: "asia-northeast3"

    - no_changes:
        return: "No changes detected"
```

---

## 6. 인프라 셋업 절차

### 6.1 Phase 0 (Week 1-2): GCP 환경 구성

```bash
# 0. 프로젝트 생성 + API 활성화
gcloud projects create create-kg --name="Knowledge Graph Pipeline"
gcloud config set project create-kg

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  workflows.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  bigquery.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  cloudfunctions.googleapis.com \
  artifactregistry.googleapis.com

# 1. GCS 버킷 생성
gcloud storage buckets create gs://create-kg-data \
  --location=asia-northeast3 \
  --uniform-bucket-level-access

# 2. BigQuery 데이터셋 생성
bq mk --dataset --location=asia-northeast3 create_kg

# 3. Secret Manager — API 키 등록
echo -n "sk-ant-..." | gcloud secrets create anthropic-api-key \
  --data-file=- --replication-policy=automatic
echo -n "sk-..." | gcloud secrets create openai-api-key \
  --data-file=- --replication-policy=automatic
echo -n "neo4j+s://..." | gcloud secrets create neo4j-uri \
  --data-file=- --replication-policy=automatic
echo -n "neo4j" | gcloud secrets create neo4j-user \
  --data-file=- --replication-policy=automatic
echo -n "..." | gcloud secrets create neo4j-password \
  --data-file=- --replication-policy=automatic

# 4. 서비스 계정 생성 + 권한
gcloud iam service-accounts create kg-pipeline \
  --display-name="KG Pipeline Service Account"

SA=kg-pipeline@create-kg.iam.gserviceaccount.com

# GCS 읽기/쓰기
gcloud projects add-iam-policy-binding create-kg \
  --member="serviceAccount:$SA" \
  --role="roles/storage.objectAdmin"

# BigQuery 편집
gcloud projects add-iam-policy-binding create-kg \
  --member="serviceAccount:$SA" \
  --role="roles/bigquery.dataEditor"

# Secret Manager 접근
gcloud projects add-iam-policy-binding create-kg \
  --member="serviceAccount:$SA" \
  --role="roles/secretmanager.secretAccessor"

# Cloud Run Jobs 실행
gcloud projects add-iam-policy-binding create-kg \
  --member="serviceAccount:$SA" \
  --role="roles/run.invoker"

# Workflows 실행
gcloud projects add-iam-policy-binding create-kg \
  --member="serviceAccount:$SA" \
  --role="roles/workflows.invoker"

# 5. Artifact Registry (Docker 이미지)
gcloud artifacts repositories create kg-pipeline \
  --repository-format=docker \
  --location=asia-northeast3

# 6. Neo4j AuraDB Free 인스턴스 생성 (Console에서)
# → URI, 인증정보를 Secret Manager에 저장

# 7. Cloud Scheduler (증분 처리)
gcloud scheduler jobs create http kg-incremental-daily \
  --schedule="0 2 * * *" \
  --uri="https://workflowexecutions.googleapis.com/v1/projects/create-kg/locations/asia-northeast3/workflows/kg-incremental/executions" \
  --http-method=POST \
  --oauth-service-account-email=$SA \
  --time-zone="Asia/Seoul"
```

### 6.2 Cloud Run Jobs 배포

```bash
# Docker 이미지 빌드 + 푸시
docker build -t asia-northeast3-docker.pkg.dev/create-kg/kg-pipeline/kg-pipeline:latest .
docker push asia-northeast3-docker.pkg.dev/create-kg/kg-pipeline/kg-pipeline:latest

IMAGE=asia-northeast3-docker.pkg.dev/create-kg/kg-pipeline/kg-pipeline:latest

# 파싱 Job
gcloud run jobs create kg-parse-resumes \
  --image=$IMAGE \
  --command="python,kg_parse_resumes/main.py" \
  --tasks=50 \
  --max-retries=1 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3

# 중복 제거 Job
gcloud run jobs create kg-dedup-resumes \
  --image=$IMAGE \
  --command="python,kg_dedup/main.py" \
  --tasks=1 \
  --cpu=4 --memory=8Gi \
  --task-timeout=7200 \
  --service-account=$SA \
  --region=asia-northeast3

# Batch API 제출 Job
gcloud run jobs create kg-batch-submit \
  --image=$IMAGE \
  --command="python,kg_batch_submit/main.py" \
  --tasks=1 \
  --cpu=1 --memory=2Gi \
  --task-timeout=86400 \
  --service-account=$SA \
  --region=asia-northeast3

# Graph 적재 Job
gcloud run jobs create kg-graph-load \
  --image=$IMAGE \
  --command="python,kg_graph_load/main.py" \
  --tasks=8 \
  --max-retries=2 \
  --cpu=2 --memory=4Gi \
  --task-timeout=43200 \
  --service-account=$SA \
  --region=asia-northeast3

# Embedding Job
gcloud run jobs create kg-embedding \
  --image=$IMAGE \
  --command="python,kg_embedding/main.py" \
  --tasks=10 \
  --cpu=2 --memory=4Gi \
  --task-timeout=21600 \
  --service-account=$SA \
  --region=asia-northeast3

# MappingFeatures Job
gcloud run jobs create kg-mapping \
  --image=$IMAGE \
  --command="python,kg_mapping/main.py" \
  --tasks=20 \
  --cpu=4 --memory=8Gi \
  --task-timeout=10800 \
  --service-account=$SA \
  --region=asia-northeast3
```

---

## 7. 비용 추정 (GCP 인프라)

### 7.1 Phase 0 (PoC, 3~4주)

| 서비스 | 사용량 | 월 비용 |
|---|---|---|
| Cloud Run Jobs | PoC 50건 파싱 + 추출 | ~$5 |
| GCS | 150GB 원본 + 1GB 파싱 결과 | ~$5 |
| BigQuery | 10MB 이하 | ~$0 (Free tier) |
| Neo4j AuraDB Free | 200K 노드 | $0 |
| Secret Manager | 5개 시크릿 | ~$0 |
| Anthropic API (PoC) | 50건 × 3모델 비교 | ~$50 |
| OpenAI Embedding (PoC) | 20쌍 × 3모델 | ~$50 |
| **Phase 0 합계** | | **~$110** |

### 7.2 Phase 1-2 (MVP + 전체 처리, 12~15주)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| **Anthropic Batch API** | 500K 이력서 + 10K JD | **$579** (Haiku Batch) |
| **OpenAI Embedding API** | 150만 Chapter + 1만 Vacancy | **$6** |
| Cloud Run Jobs | 총 ~500시간 (전 Job 합산) | **$150** |
| GCS | 150GB 원본 + 50GB 파싱/Context | **$10/월** |
| BigQuery | 10GB 서빙 테이블 | **$5/월** |
| Neo4j AuraDB Professional | 800만 노드 | **$100~200/월** |
| Cloud Workflows | 실행 횟수 | ~$1 |
| Cloud Monitoring / Logging | 기본 | ~$10/월 |
| Secret Manager | 5개 시크릿 | ~$1/월 |
| **Phase 1-2 인프라 합계** | | **~$250/월 × 4개월 = $1,000** |
| **Phase 1-2 LLM 합계** | | **~$585** |
| **Phase 1-2 총합** | | **~$1,585** |

### 7.3 운영 단계 (월간)

| 서비스 | 사용량 | 월 비용 |
|---|---|---|
| Neo4j AuraDB Professional | 800만 노드 유지 | $100~200 |
| GCS | 200GB | $5 |
| BigQuery | 10GB + 쿼리 | $10 |
| Cloud Run Jobs (증분) | 일 1,000건 × 30일 | $10 |
| Anthropic API (증분) | 일 1,000건 | $35 |
| Cloud Scheduler + Workflows | 일 1회 | ~$1 |
| Monitoring / Logging | 기본 | $10 |
| **운영 월 합계** | | **~$170~270/월** |

### 7.4 v5 비용과 GCP 비용 대비

| 항목 | v5 추정 (시나리오 A) | GCP 실행 추정 | 비고 |
|---|---|---|---|
| LLM 비용 | $1,255 | $585 (Batch) + $50 (PoC) | Batch API 50% 할인 반영 |
| Embedding | $6 | $6 | 동일 |
| Graph DB | $1,200/년 | $1,200~2,400/년 | AuraDB Professional |
| GCP 인프라 | — | ~$1,000 (4개월) | Cloud Run, GCS, BQ 등 |
| 오케스트레이션 | $600/년 | ~$12/년 | Cloud Workflows (저렴) |
| BigQuery | $360/년 | $120/년 | GCP 네이티브 할인 |
| Gold Label 인건비 | $5,840 | $5,840 | 동일 (인프라 무관) |
| **총비용** | **~$9,255** | **~$8,800** | GCP가 약간 저렴 |

---

## 8. 모니터링 구성

### 8.1 Cloud Monitoring 대시보드

```yaml
# monitoring/dashboard.json (요약)
widgets:
  - title: "파이프라인 진행률"
    metrics:
      - custom.googleapis.com/kg/parsed_count
      - custom.googleapis.com/kg/extracted_count
      - custom.googleapis.com/kg/loaded_count

  - title: "에러율"
    metrics:
      - custom.googleapis.com/kg/error_rate
      - custom.googleapis.com/kg/dead_letter_count

  - title: "LLM API 비용"
    metrics:
      - custom.googleapis.com/kg/llm_input_tokens
      - custom.googleapis.com/kg/llm_output_tokens
      - custom.googleapis.com/kg/llm_cost_usd

  - title: "Neo4j 적재"
    metrics:
      - custom.googleapis.com/kg/nodes_created
      - custom.googleapis.com/kg/edges_created
      - custom.googleapis.com/kg/merge_conflicts
```

### 8.2 알림 정책

| 조건 | 채널 | 임계값 |
|---|---|---|
| Dead-letter 건수 > 1,000 | Slack + Email | 1시간 내 |
| Cloud Run Job 실패 | Slack | 즉시 |
| LLM API 누적 비용 > $500 | Email | 일일 체크 |
| Neo4j 연결 실패 | Slack | 즉시 |
| 일일 증분 처리 미실행 | Email | 오전 6시 |

### 8.3 BigQuery 처리 로그

```sql
-- processing_log 테이블 스키마
CREATE TABLE create_kg.processing_log (
  run_id STRING NOT NULL,
  pipeline STRING NOT NULL,         -- 'parse' | 'extract' | 'graph_load' | 'mapping'
  item_id STRING NOT NULL,          -- candidate_id 또는 job_id
  status STRING NOT NULL,           -- 'SUCCESS' | 'FAILED' | 'SKIPPED'
  error_type STRING,
  error_message STRING,
  input_tokens INT64,
  output_tokens INT64,
  llm_model STRING,
  prompt_version STRING,
  latency_ms FLOAT64,
  processed_at TIMESTAMP NOT NULL,
  run_date DATE NOT NULL,
);

-- 일일 처리 현황 쿼리
SELECT
  run_date,
  pipeline,
  COUNTIF(status = 'SUCCESS') AS success_count,
  COUNTIF(status = 'FAILED') AS fail_count,
  COUNTIF(status = 'SKIPPED') AS skip_count,
  ROUND(COUNTIF(status = 'FAILED') / COUNT(*) * 100, 2) AS error_rate_pct,
  SUM(input_tokens) AS total_input_tokens,
  SUM(output_tokens) AS total_output_tokens,
FROM create_kg.processing_log
WHERE run_date = CURRENT_DATE()
GROUP BY run_date, pipeline
ORDER BY pipeline;
```

---

## 9. 보안 설계

### 9.1 PII 처리 플로우

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

### 9.2 IAM 최소 권한

| 서비스 계정 | 역할 | 접근 대상 |
|---|---|---|
| `kg-pipeline` | `storage.objectAdmin` | `gs://create-kg-data/` |
| `kg-pipeline` | `bigquery.dataEditor` | `create_kg` 데이터셋 |
| `kg-pipeline` | `secretmanager.secretAccessor` | API 키 시크릿 |
| `kg-pipeline` | `run.invoker` | Cloud Run Jobs |
| `kg-pipeline` | `workflows.invoker` | Cloud Workflows |
| `kg-pipeline` | `monitoring.metricWriter` | 커스텀 메트릭 |
| `kg-pipeline` | `logging.logWriter` | Cloud Logging |

### 9.3 네트워크 보안 (선택적)

```bash
# VPC Service Controls — PII 데이터 유출 방지
# Phase 1에서 필요 시 적용 (법무 요구사항에 따라)
gcloud access-context-manager perimeters create kg-perimeter \
  --title="KG Pipeline Perimeter" \
  --resources="projects/create-kg" \
  --restricted-services="storage.googleapis.com,bigquery.googleapis.com" \
  --access-levels="accessPolicies/.../accessLevels/kg-allowed"
```

---

## 10. Phase별 GCP 작업 체크리스트

### Phase 0: 기반 구축 + PoC (3~4주)

```
Week 1:
□ GCP 프로젝트 생성 + API 활성화
□ GCS 버킷 생성 + 이력서 원본 업로드 시작
□ Secret Manager 시크릿 등록 (Anthropic, OpenAI, Neo4j)
□ Neo4j AuraDB Free 인스턴스 생성 + Graph 스키마 적용
□ 서비스 계정 생성 + IAM 설정
□ Artifact Registry 리포지토리 생성
□ Python 프로젝트 구조 생성 (Poetry/uv)
□ 이력서 파싱 라이브러리 설치 + 단건 테스트

Week 2:
□ Docker 이미지 빌드 + Cloud Run Job 등록 (파싱 Job 우선)
□ 이력서 50건 파싱 PoC (파싱 → 섹션 분할 → 블록 분리 3단계 성공률)
□ LLM 추출 PoC: Haiku/Flash/Sonnet 비교 (50건)
□ PII 마스킹 영향 테스트 (10건)
□ Embedding 모델 비교 (20쌍)
□ LLM 호출 전략 비교 (경력별 vs 전체 1회, 10건)

Week 3:
□ PoC 결과 정리 + 의사결정
□ BigQuery 데이터셋 + processing_log 테이블 생성
□ Cloud Monitoring 대시보드 생성
□ Cloud Workflows 워크플로우 배포
```

### Phase 1: MVP 파이프라인 (8~10주)

```
Week 4-5 (전처리):
□ 이력서 파서 모듈 완성 (PDF/DOCX/HWP)
□ PII 마스킹 모듈
□ 이력서 중복 제거 모듈
□ 기술 사전 + 회사 사전 구축
□ Cloud Run Job 업데이트 + 1,000건 배치 테스트

Week 6-7 (CompanyContext):
□ CompanyContext Pydantic 모델
□ NICE Lookup 모듈
□ LLM 추출 프롬프트 확정
□ JD 100건 E2E 테스트

Week 8-10 (CandidateContext):
□ CandidateContext Pydantic 모델
□ Rule 추출 + LLM 추출 모듈
□ Batch API 연동 (1,000건 단위 제출/수집)
□ 이력서 200건 통합 테스트

Week 11-12 (Graph + Entity Resolution):
□ Deterministic ID 생성 모듈
□ Graph 적재 Job (MERGE 패턴)
□ Organization Entity Resolution
□ Idempotency 테스트 (동일 데이터 2회 적재)
□ Vector Index 적재 Job

Week 13 (MappingFeatures):
□ Candidate Shortlisting (Rule + Vector Search)
□ MappingFeatures 계산 모듈
□ BigQuery 적재
```

### Phase 2: 확장 + 최적화 (4~5주)

```
Week 14-16 (전체 데이터 처리):
□ 이력서 500K 중복 제거 실행
□ Batch API 전체 처리 (500 chunks × 1,000건)
□ Graph 전체 적재 (Neo4j AuraDB Professional 전환)
□ Dead-letter 재처리
□ Cloud Scheduler 설정 (증분 처리)

Week 15-16 (품질 평가, 병행):
□ Gold Test Set 구축 (전문가 2인 × 200건)
□ 품질 메트릭 측정 + BigQuery 적재
□ 프롬프트 최적화 (Golden Set 회귀 테스트)

Week 17 (서빙):
□ BigQuery 서빙 테이블 확정
□ 증분 처리 워크플로우 운영 확인
□ 모니터링 + 알림 운영 확인
```

---

## 11. 리전 선택

| 서비스 | 리전 | 근거 |
|---|---|---|
| GCS | `asia-northeast3` (서울) | 데이터 주권, 레이턴시 |
| BigQuery | `asia-northeast3` | GCS와 같은 리전 |
| Cloud Run Jobs | `asia-northeast3` | GCS 접근 레이턴시 |
| Cloud Workflows | `asia-northeast3` | Cloud Run과 같은 리전 |
| Cloud Scheduler | `asia-northeast3` | 동일 |
| Neo4j AuraDB | GCP `asia-northeast1` (도쿄) | 서울 미지원, 도쿄가 가장 가까움 |
| Anthropic API | US (외부) | 선택 불가 (외부 API) |
| OpenAI API | US (외부) | 선택 불가 (외부 API) |

> **Neo4j 리전 주의**: AuraDB는 `asia-northeast3`을 지원하지 않으므로 `asia-northeast1` (도쿄) 사용. Cloud Run → Neo4j 간 리전 간 레이턴시(~10ms)가 발생하지만, 배치 처리 특성상 영향 미미.

---

## 12. 시나리오 C (On-premise) GCP 구성

> PII 법무 검토에서 외부 API 전송 불가 판정 시에만 해당.

```bash
# GPU VM 생성 (EXAONE-3.5-7.8B 추론용)
gcloud compute instances create kg-llm-inference \
  --zone=asia-northeast3-a \
  --machine-type=a2-highgpu-1g \
  --accelerator=type=nvidia-tesla-a100,count=1 \
  --boot-disk-size=200GB \
  --image-family=pytorch-latest-gpu \
  --image-project=deeplearning-platform-release \
  --maintenance-policy=TERMINATE

# 비용: A100 1개 = ~$3.67/시간
# 500K 이력서 × 3경력/이력서 = 1.5M 추론
# 추론 속도: ~50건/분 → 500시간 → ~$1,835
# + GPU 인프라 오버헤드 → 총 ~$2,500~3,000
```

---

## 13. 의사결정 포인트 요약

| 시점 | 의사결정 | GCP 영향 |
|---|---|---|
| Phase 0 완료 | PII 전략 | API(Cloud Run) vs On-premise(Compute Engine GPU) |
| Phase 0 완료 | 파싱 성공률 | < 50%이면 Document AI 추가 검토 가능 |
| Phase 0 완료 | LLM 모델 | Batch API 제출 Job의 모델 설정 |
| Phase 1 중간 | Neo4j 플랜 | Free → Professional 전환 시점 |
| Phase 2 시작 | Cloud Run 스케일 | Task 수, 동시 배치 수 조정 |
| Phase 2 완료 | 운영 모드 | Cloud Scheduler 증분 처리 주기 |

---

## 14. v5 계획 대비 GCP 특이사항

| v5 설계 | GCP 구현 | 비고 |
|---|---|---|
| Cloud Workflows / Prefect 권장 | **Cloud Workflows 채택** | GCP 네이티브, 추가 인프라 불필요, 비용 최저 |
| Grafana + BigQuery | **Cloud Monitoring + BigQuery** | Grafana는 선택적 (Cloud Monitoring으로 충분) |
| 이력서 파싱 (PyMuPDF 등) | **Cloud Run Jobs** | Document AI는 PoC에서 비교 후 결정 |
| NICE DB 조회 | **Cloud Functions 또는 Cloud Run 내장** | 조회 빈도에 따라 결정 |
| evidence_span normalized match | **동일 (Python 코드)** | 인프라 무관 |
| Deterministic ID + MERGE | **동일 (Neo4j Cypher)** | 인프라 무관 |
| Batch API 50% 할인 | **Cloud Run Job이 Batch API 제출/폴링** | Job의 task-timeout=24h 설정 |
| Dead-Letter 큐 | **GCS + Cloud Scheduler + Cloud Run Job** | Pub/Sub 대신 GCS 파일 기반 (단순) |
| 프롬프트 버전 관리 | **GCS + Git** | GCS에 배포, Git에 원본 |

---

## 15. 빠른 시작 가이드

### 최소 환경으로 PoC 시작 (30분)

```bash
# 1. 프로젝트 + API
gcloud config set project create-kg
gcloud services enable run.googleapis.com secretmanager.googleapis.com storage.googleapis.com

# 2. GCS + 샘플 데이터
gcloud storage buckets create gs://create-kg-data --location=asia-northeast3
gcloud storage cp sample_resumes/ gs://create-kg-data/raw/resumes/ --recursive

# 3. API 키
echo -n "$ANTHROPIC_API_KEY" | gcloud secrets create anthropic-api-key --data-file=-

# 4. 로컬 테스트 (Cloud Run 배포 전)
export GOOGLE_CLOUD_PROJECT=create-kg
python kg_parse_resumes/main.py --local --sample=10

# 5. Neo4j AuraDB Free → Console에서 생성
# → URI/인증정보를 Secret Manager에 저장

# 6. 첫 번째 Cloud Run Job 배포 + 실행
gcloud run jobs create kg-parse-poc \
  --image=... --tasks=1 --cpu=2 --memory=4Gi \
  --region=asia-northeast3
gcloud run jobs execute kg-parse-poc --region=asia-northeast3
```
