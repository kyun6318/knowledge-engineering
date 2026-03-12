# GCP 실행 계획 — Phase별 상세

> v7 실행 계획(`04_execution_plan.md`)을 GCP 환경에서 수행하기 위한 Phase별 구체적 작업 항목.
>
> **인력 배치**: DE 1명 + MLE 1명 풀타임, 도메인 전문가 1명 파트타임
> **총 타임라인**: 18~22주 (Phase 0~2, ML Distillation 제외 시 17~19주)
>
> 작성일: 2026-03-08

---

## 사전 준비 (Pre-Phase 0) — Blocking Dependencies

> Phase 0 시작 **2주 전**까지 완료 필요.

### NICE DB 접근 확보

```bash
# 확인 사항 체크리스트
□ NICE DB 접근 계약 상태 확인
  - 기존 계약 → API 접근 키 + 필드 + 호출 제한 확인
  - 신규 계약 → 협의 시작 (예상 2~4주)
□ NICE DB 테스트 환경 API 호출 가능 확인
□ NICE 업종코드 마스터 데이터 확보 (KSIC 대/중/소분류)
```

**판정**: 2주 전까지 미확보 시 → NICE 의존 태스크를 Phase 0 후반으로 연기, DART + 사업자등록 조회로 대체.

### GCP 프로젝트 사전 준비

```bash
# 프로젝트 생성 + API 활성화
gcloud projects create graphrag-kg --name="GraphRAG Knowledge Graph"
gcloud config set project graphrag-kg

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
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com

# 서비스 계정 생성
gcloud iam service-accounts create kg-pipeline \
  --display-name="KG Pipeline Service Account"

SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com

# IAM 역할 바인딩
for ROLE in storage.objectAdmin bigquery.dataEditor \
  secretmanager.secretAccessor run.invoker \
  workflows.invoker monitoring.metricWriter \
  logging.logWriter aiplatform.user; do
  gcloud projects add-iam-policy-binding graphrag-kg \
    --member="serviceAccount:$SA" \
    --role="roles/$ROLE"
done

# Artifact Registry
gcloud artifacts repositories create kg-pipeline \
  --repository-format=docker \
  --location=asia-northeast3

# GCS 버킷
gcloud storage buckets create gs://graphrag-kg-data \
  --location=asia-northeast3 \
  --uniform-bucket-level-access

# BigQuery 데이터셋
bq mk --dataset --location=asia-northeast3 graphrag_kg
```

---

## Phase 0: 기반 구축 + PoC (3~4주)

### 0-1. 데이터 탐색 및 프로파일링 (1주)

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 0-1-1 | 이력서 원본 GCS 업로드 시작 | GCS | `gs://graphrag-kg-data/raw/resumes/` |
| 0-1-2 | 파일 형식 분포 조사 (PDF/DOCX/HWP) | Cloud Shell / 로컬 | 가정 A11 검증 |
| 0-1-3 | 무작위 500건 샘플링 → 평균 크기, 경력 수 | Cloud Shell | 가정 A2, A4 검증 |
| 0-1-4 | OCR 필요 비율 확인 | Cloud Shell | 가정 A12 검증 |
| 0-1-5 | SimHash 중복률 추정 테스트 | Cloud Shell | 가정 A17 검증 |
| 0-1-6 | JD 보유량 확인 + GCS 업로드 | GCS | 가정 A1 검증 |
| 0-1-7 | NICE DB 접근 확인 + 매칭률 테스트 (100건) | Cloud Functions | 가정 A5 검증 |

```bash
# 이력서 업로드 (백그라운드)
gcloud storage cp -r /path/to/resumes/ gs://graphrag-kg-data/raw/resumes/ &

# 파일 형식 분포 확인
gcloud storage ls gs://graphrag-kg-data/raw/resumes/**/*.pdf | wc -l
gcloud storage ls gs://graphrag-kg-data/raw/resumes/**/*.docx | wc -l
gcloud storage ls gs://graphrag-kg-data/raw/resumes/**/*.hwp | wc -l
```

### 0-2. LLM 추출 품질 PoC (1~2주)

| # | 작업 | 도구/서비스 | 산출물 |
|---|---|---|---|
| 0-2-1 | 파싱→섹션분할→경력블록 단계별 성공률 (50건) | 로컬 Python | 파싱 품질 리포트 |
| 0-2-2 | CandidateContext 추출 모델 비교 (50건) | Anthropic API (직접 호출) | 모델 비교 리포트 |
| 0-2-3 | CompanyContext 추출 테스트 (JD 30건) | Anthropic API | 추출 품질 메트릭 |
| 0-2-4 | PII 마스킹 영향 테스트 (10건) | 로컬 Python + API | PII 영향 리포트 |
| 0-2-5 | Embedding 모델 확정 검증 (20쌍) | Vertex AI API | Embedding 검증 리포트 |
| 0-2-6 | LLM 호출 전략 비교 (10건) | Anthropic API | 호출 전략 결정 |

```python
# Embedding 확정 검증 코드 (Vertex AI)
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")

# 20쌍 테스트
similar_pairs = [...]  # 10쌍: 같은 도메인
dissimilar_pairs = [...]  # 10쌍: 다른 도메인

for pair in similar_pairs + dissimilar_pairs:
    emb1 = model.get_embeddings([pair[0]])[0].values
    emb2 = model.get_embeddings([pair[1]])[0].values
    similarity = cosine_similarity(emb1, emb2)
    # Mann-Whitney U test로 분리도 검증
```

#### LLM 파싱 실패율 사전 측정 (v7)

```python
# Phase 0 PoC에서 50건 테스트 시 tier별 비율 측정
parse_stats = {"tier1": 0, "tier2": 0, "tier3_partial": 0, "tier3_fail": 0}

for resume in poc_50:
    result, tier, partial = parse_llm_response(raw, CandidateExperience, resume.id)
    if tier == "tier1":
        parse_stats["tier1"] += 1
    elif tier == "tier2":
        parse_stats["tier2"] += 1
    elif partial:
        parse_stats["tier3_partial"] += 1
    else:
        parse_stats["tier3_fail"] += 1

# 목표: tier1 > 85%, tier3_fail < 3%
print(f"Tier 1 (json-repair 성공): {parse_stats['tier1']/50*100:.1f}%")
print(f"Tier 3 실패 (dead-letter): {parse_stats['tier3_fail']/50*100:.1f}%")
```

### 0-3. 인프라 셋업 (1주, 0-1과 병행)

| # | 작업 | GCP 서비스 | 비고 |
|---|---|---|---|
| 0-3-1 | Secret Manager 시크릿 등록 | Secret Manager | Anthropic, Neo4j |
| 0-3-2 | Neo4j AuraDB Free 인스턴스 생성 | Neo4j Console | 200K 노드 |
| 0-3-3 | v10 Graph 스키마 적용 | Neo4j | 노드/엣지/인덱스 |
| 0-3-4 | Vector Index 설정 | Neo4j | chapter/vacancy embedding (768차원) |
| 0-3-5 | BigQuery 테이블 생성 | BigQuery | 위 스키마 6개 테이블 |
| 0-3-6 | Artifact Registry 레포 생성 | Artifact Registry | `kg-pipeline` |
| 0-3-7 | Organization 크롤링 보강 속성 사전 선언 | Neo4j | nullable 필드 |
| 0-3-8 | Industry 마스터 노드 준비 | GCS + 스크립트 | KSIC 코드 → JSON |
| 0-3-9 | Docker 베이스 이미지 빌드 | Cloud Build | 공통 의존성 |

```bash
# Secret Manager 등록
echo -n "$ANTHROPIC_API_KEY" | gcloud secrets create anthropic-api-key \
  --data-file=- --replication-policy=automatic
echo -n "neo4j+s://xxx.databases.neo4j.io" | gcloud secrets create neo4j-uri \
  --data-file=- --replication-policy=automatic
echo -n "neo4j" | gcloud secrets create neo4j-user \
  --data-file=- --replication-policy=automatic
echo -n "$NEO4J_PASSWORD" | gcloud secrets create neo4j-password \
  --data-file=- --replication-policy=automatic

# BigQuery 테이블 생성 (스키마 파일 기반)
bq mk --table graphrag_kg.processing_log schema/processing_log.json
bq mk --table graphrag_kg.chunk_status schema/chunk_status.json
bq mk --table graphrag_kg.mapping_features schema/mapping_features.json
bq mk --table graphrag_kg.quality_metrics schema/quality_metrics.json
bq mk --table graphrag_kg.parse_failure_log schema/parse_failure_log.json
```

```cypher
// Neo4j — v10 Graph 스키마 적용
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.candidate_id IS UNIQUE;
CREATE CONSTRAINT org_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.org_id IS UNIQUE;
CREATE CONSTRAINT vacancy_id IF NOT EXISTS FOR (v:Vacancy) REQUIRE v.vacancy_id IS UNIQUE;
CREATE CONSTRAINT chapter_id IF NOT EXISTS FOR (c:Chapter) REQUIRE c.chapter_id IS UNIQUE;
CREATE CONSTRAINT industry_id IF NOT EXISTS FOR (i:Industry) REQUIRE i.industry_id IS UNIQUE;
CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.canonical_name IS UNIQUE;
CREATE CONSTRAINT role_name IF NOT EXISTS FOR (r:Role) REQUIRE r.canonical_name IS UNIQUE;

// Vector Index (768차원 — text-multilingual-embedding-002)
CREATE VECTOR INDEX chapter_embedding IF NOT EXISTS
FOR (c:Chapter) ON (c.evidence_chunk_embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX vacancy_embedding IF NOT EXISTS
FOR (v:Vacancy) ON (v.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};
```

### 0-4. Phase 0 완료 의사결정

| 의사결정 | 판단 기준 | GCP 영향 |
|---|---|---|
| LLM 모델 선택 | PoC 품질 비교 | Batch API 모델 설정 |
| PII 전략 | 법무 + 마스킹 영향 | API vs Compute Engine GPU |
| Embedding 확정 검증 | 한국어 분별력 | Vertex AI 모델 설정 |
| 오케스트레이션 도구 | DE 역량 + 통합 요구 | Cloud Workflows vs Prefect (Cloud Run) |
| 섹션 분할 전략 | 파싱 성공률 | LLM fallback 시 비용 증가 |
| LLM 호출 전략 | 품질/비용 비교 | Batch API 요청 구조 |
| Graph DB 플랜 | 예상 노드 수 | Free → Professional 전환 시점 |

---

## Phase 1: MVP 파이프라인 (10~12주)

### 1-1. 전처리 모듈 (2주) — Week 4-6

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

```bash
# Docker 이미지 빌드
IMAGE=asia-northeast3-docker.pkg.dev/graphrag-kg/kg-pipeline/kg-pipeline:latest
docker build -t $IMAGE .
docker push $IMAGE

# 파싱 Job 등록
gcloud run jobs create kg-parse-resumes \
  --image=$IMAGE \
  --command="python,src/parse_resumes.py" \
  --tasks=50 --max-retries=1 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3
```

### 1-2. CompanyContext 파이프라인 (1~2주) — Week 6-8

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
# CompanyContext Job 등록
gcloud run jobs create kg-company-ctx \
  --image=$IMAGE \
  --command="python,src/company_context.py" \
  --tasks=5 --max-retries=1 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3
```

### 1-3. CandidateContext 파이프라인 (4주) — Week 8-12

> v7 변경: 3주 → 4주. LLM 파싱 실패 3-tier 구현 + chunk 관리 인프라에 추가 시간.

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-3-1 | CandidateContext Pydantic 모델 정의 | 코드 | `src/models/candidate.py` |
| 1-3-2 | Rule 추출 모듈 (날짜/회사/기술) | 코드 | `src/extractors/rule.py` |
| 1-3-3 | LLM 추출 프롬프트 (Experience별) | GCS prompts/ | `experience_extract_v1.txt` |
| 1-3-4 | LLM 추출 프롬프트 (전체 커리어) | GCS prompts/ | `career_level_v1.txt` |
| 1-3-5 | WorkStyleSignals LLM 프롬프트 (v6) | 코드 | |
| 1-3-6 | PastCompanyContext NICE 역산 모듈 | Cloud Functions | |
| 1-3-7 | **LLM 파싱 실패 3-tier 구현 (v7)** | 코드 | `src/shared/llm_parser.py` |
| 1-3-8 | Batch API 요청 생성 모듈 (1,000건/chunk) | Cloud Run Job | |
| 1-3-9 | Batch API 제출/폴링 모듈 | Cloud Run Job | |
| 1-3-10 | **Chunk 상태 추적 인프라 (v7)** | BigQuery | `chunk_status` 테이블 |
| 1-3-11 | 통합 테스트 (이력서 200건) | Cloud Run Job | E2E 결과 |
| 1-3-12 | Batch API 연동 테스트 (1,000건) | Anthropic Batch API | |

```python
# Chunk 상태 추적 (BigQuery)
from google.cloud import bigquery

def update_chunk_status(chunk_id, pipeline, status, counts=None):
    bq = bigquery.Client()
    row = {
        "chunk_id": chunk_id,
        "pipeline": pipeline,
        "status": status,
        "success_count": counts.get("success", 0) if counts else 0,
        "fail_count": counts.get("fail", 0) if counts else 0,
        "partial_count": counts.get("partial", 0) if counts else 0,
        "updated_at": datetime.utcnow().isoformat(),
    }
    # MERGE (upsert)
    bq.query(f"""
        MERGE graphrag_kg.chunk_status T
        USING (SELECT '{chunk_id}' as chunk_id) S
        ON T.chunk_id = S.chunk_id AND T.pipeline = '{pipeline}'
        WHEN MATCHED THEN UPDATE SET
          status = '{status}',
          success_count = {row['success_count']},
          fail_count = {row['fail_count']},
          partial_count = {row['partial_count']},
          updated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN INSERT
          (chunk_id, pipeline, status, total_count, created_at)
          VALUES ('{chunk_id}', '{pipeline}', '{status}', 1000, CURRENT_TIMESTAMP())
    """)
```

### 1-4. Graph 적재 파이프라인 (2주) — Week 12-14

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-4-1 | CompanyContext → Neo4j 로더 (MERGE) | Cloud Run Job | |
| 1-4-2 | CandidateContext → Neo4j 로더 (MERGE) | Cloud Run Job | |
| 1-4-3 | Deterministic ID 생성 모듈 | 코드 | |
| 1-4-4 | Organization Entity Resolution 모듈 | 코드 | |
| 1-4-5 | **Industry 마스터 노드 적재 + 검증 (v6)** | Cloud Run Job | |
| 1-4-6 | **Vacancy→REQUIRES_ROLE→Role 관계 (v6)** | 코드 | |
| 1-4-7 | Vector Index 적재 (Vertex AI Embedding) | Cloud Run Job | |
| 1-4-8 | Idempotency 테스트 (동일 데이터 2회 적재) | Neo4j | 노드/엣지 수 불변 확인 |
| 1-4-9 | 적재 벤치마크 (1,000건 → 500K 추정) | 측정 | |

```bash
# Industry 마스터 적재 Job
gcloud run jobs create kg-industry-load \
  --image=$IMAGE \
  --command="python,src/load_industry.py" \
  --tasks=1 --cpu=1 --memory=2Gi \
  --task-timeout=600 \
  --service-account=$SA \
  --region=asia-northeast3

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

### 1-5. MappingFeatures + MAPPED_TO (2주) — Week 14-16

> v7 변경: 1주 → 2주. MAPPED_TO 적재 + 통합 E2E 테스트에 추가 시간.

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-5-1 | Candidate Shortlisting (Rule + Vector Search) | Cloud Run Job | |
| 1-5-2 | MappingFeatures 계산 모듈 | 코드 | |
| 1-5-3 | **ScopeType→Seniority 변환 함수 (v6)** | 코드 | |
| 1-5-4 | **MAPPED_TO 관계 Graph 적재 (v6)** | Cloud Run Job | |
| 1-5-5 | BigQuery mapping_features 테이블 적재 | BigQuery | |
| 1-5-6 | 매핑 50건 수동 검증 | 수동 | |
| 1-5-7 | E2E 통합 테스트 (JD 100건 + 이력서 1,000건) | 전체 파이프라인 | |

```bash
# MappingFeatures Job
gcloud run jobs create kg-mapping \
  --image=$IMAGE \
  --command="python,src/compute_mapping.py" \
  --tasks=20 \
  --cpu=4 --memory=8Gi \
  --task-timeout=10800 \
  --service-account=$SA \
  --region=asia-northeast3
```

**Phase 1 산출물**: E2E 파이프라인 (JD 100건 + 이력서 1,000건 + Graph + MappingFeatures + MAPPED_TO)

---

## Phase 2: 확장 + 최적화 (4~5주)

### 2-1. 전체 데이터 처리 (2~3주) — Week 16-19

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

```
[Chunk 처리 흐름]
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

### 2-2. 품질 평가 (1주, 2-1과 병행) — Week 17-18

| # | 작업 | 도구 | 비고 |
|---|---|---|---|
| 2-2-1 | Gold Test Set 구축 (전문가 2인 × 200건) | 수동 + BigQuery | |
| 2-2-2 | Inter-annotator agreement (Cohen's κ) | Python | |
| 2-2-3 | Power analysis (Cohen's d) | Python (scipy) | v6 신설 |
| 2-2-4 | 평가 지표 측정 + BigQuery 적재 | BigQuery | quality_metrics 테이블 |

#### 평가 기준

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

### 2-3. DS/MLE 서빙 인터페이스 (1주) — Week 18-19

| # | 작업 | GCP 서비스 | 비고 |
|---|---|---|---|
| 2-3-1 | BigQuery mapping_features 스키마 확정 | BigQuery | |
| 2-3-2 | SQL 예시 쿼리 작성 + 문서화 | | |
| 2-3-3 | Context on/off ablation 테스트 환경 | BigQuery | |

### 2-4. ML Knowledge Distillation (1~2주, 선택적) — Week 19-22

| # | 작업 | GCP 서비스 | 비고 |
|---|---|---|---|
| 2-4-1 | scope_type 분류기 학습 (KLUE-BERT) | Vertex AI Training / 로컬 | F1 > 75% 목표 |
| 2-4-2 | seniority 분류기 학습 | 동일 | F1 > 80% 목표 |
| 2-4-3 | Confidence 기반 라우팅 구현 | 코드 | ML > 0.85 → ML, else → LLM |

### 2-5. 증분 처리 + 운영 인프라 — Week 19-22 (병행)

```bash
# Cloud Scheduler (일일 증분 처리)
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
```

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

**Phase 2 산출물**: 전체 데이터 처리 완료 + 품질 리포트 + 서빙 인터페이스 + 증분 처리 자동화

---

## Phase 3: 크롤링 파이프라인 (7주) — Week 22-29

> `crawling-gcp-plan.md` 참조. Phase 3의 GCP 구현은 해당 문서와 동일한 아키텍처를 사용.

### 3-1. 크롤러 인프라 구축 (2주) — Week 22-24

| # | 작업 | GCP 서비스 | 참조 |
|---|---|---|---|
| 3-1-1 | Playwright 크롤러 Docker 이미지 | Cloud Run Job | crawling-gcp-plan §4.1 |
| 3-1-2 | 뉴스 수집기 Docker 이미지 | Cloud Run Job | crawling-gcp-plan §4.2 |
| 3-1-3 | LLM 추출기 (Gemini Flash) | Cloud Run Job | crawling-gcp-plan §4.3 |
| 3-1-4 | 크롤링 BigQuery 테이블 생성 | BigQuery | `crawl.*` 데이터셋 |
| 3-1-5 | 네이버 뉴스 API 키 발급 + Secret Manager | Secret Manager | |

### 3-2. T3 홈페이지 크롤링 (2주) — Week 24-26

- crawling-gcp-plan의 Phase 1과 동일
- Organization 노드 속성 업데이트 (product_description, market_segment)

### 3-3. T4 뉴스 크롤링 (2주) — Week 26-28

- crawling-gcp-plan의 Phase 2와 동일
- **structural_tensions 추출 활성화 (v6)**
- CompanyContext.structural_tensions 필드 업데이트

### 3-4. 데이터 병합 + 품질 검증 (1주) — Week 28-29

- 크롤링 결과 → CompanyContext 보강 병합
- operating_model facet merge 로직 (v6 M-5)
- 크롤링 전/후 품질 비교 (50건)

---

## 타임라인 요약

```
Pre-Phase 0: NICE DB 접근 확보 + GCP 프로젝트 준비 — Phase 0 시작 2주 전

Week 1-2:   Phase 0-1 (데이터 탐색 + GCS 업로드)
Week 2-3:   Phase 0-2 (LLM PoC + 파싱 PoC + Embedding 검증)
Week 3-4:   Phase 0-3 (인프라 셋업) + Phase 0-4 (의사결정)

Week 4-6:   Phase 1-1 (전처리 모듈 + 중복 제거)
Week 6-8:   Phase 1-2 (CompanyContext 파이프라인)
Week 8-12:  Phase 1-3 (CandidateContext 파이프라인 — 4주)
Week 12-14: Phase 1-4 (Graph 적재 + Entity Resolution + Industry + REQUIRES_ROLE)
Week 14-16: Phase 1-5 (MappingFeatures + MAPPED_TO + 통합 테스트)

Week 16-19: Phase 2-1 (전체 데이터 처리 — 450 chunks)
Week 17-18: Phase 2-2 (품질 평가 + power analysis) — 병행
Week 18-19: Phase 2-3 (DS/MLE 서빙)
Week 19-22: Phase 2-4 (ML Distillation — 선택적) + 증분 처리 자동화

Week 22-24: Phase 3-1 (크롤러 인프라)
Week 24-26: Phase 3-2 (T3 홈페이지 크롤링)
Week 26-28: Phase 3-3 (T4 뉴스 크롤링 + structural_tensions)
Week 28-29: Phase 3-4 (데이터 병합 + 품질 검증)
Week 29+:   GraphRAG 활용 확장, 운영 고도화

총 MVP 완성: ~18~22주 (Phase 0~2)
첫 동작 데모: ~16주 (Phase 0~1 완료)
크롤링 완료: ~29주
```
