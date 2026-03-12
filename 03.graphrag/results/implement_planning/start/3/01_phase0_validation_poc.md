# Phase 0: 기반 구축 + API 검증 + PoC (4~5주)

> **목적**: GCP API 기능 검증 + LLM 추출 품질 PoC + 인프라 셋업을 통합 수행.
> api-test-3day의 검증 항목을 Phase 0에 내장하여, 검증 결과가 즉시 의사결정에 반영되도록 한다.
>
> **v2 통합 변경**: api-test-3day-v3-review.md P0급 패치 5건 반영.
>
> **인력**: DE 1명 + MLE 1명 풀타임, 도메인 전문가 1명 파트타임

---

## 사전 준비 (Pre-Phase 0) — Blocking Dependencies

> Phase 0 시작 **2주 전**까지 완료 필요.

### NICE DB 접근 확보

```bash
□ NICE DB 접근 계약 상태 확인
  - 기존 계약 → API 접근 키 + 필드 + 호출 제한 확인
  - 신규 계약 → 협의 시작 (예상 2~4주)
□ NICE DB 테스트 환경 API 호출 가능 확인
□ NICE 업종코드 마스터 데이터 확보 (KSIC 대/중/소분류)
```

**판정**: 2주 전까지 미확보 시 → NICE 의존 태스크를 Phase 0 후반으로 연기, DART + 사업자등록 조회로 대체.

### GCP 프로젝트 사전 준비

```bash
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
  aiplatform.googleapis.com \
  documentai.googleapis.com \
  discoveryengine.googleapis.com \
  storage.googleapis.com

# 서비스 계정
gcloud iam service-accounts create kg-pipeline \
  --display-name="KG Pipeline Service Account"

SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com

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

### 사전 준비 체크리스트

```
□ GCP 프로젝트 API 활성화 완료
□ 서비스 계정 + ADC 설정
□ SDK 설치 및 버전 확인 → requirements-lock.txt 생성

□ Document AI 프로세서: GCP Console에서 사전 생성 (코드 생성 금지)
  ├── OCR Processor → processor name 기록: ___
  └── Layout Parser → processor name 기록: ___
  ⚠ type 문자열은 Console UI 기준. API type 문자열은 버전마다 다를 수 있음

□ DS-NER-EVAL gold 데이터 라벨링 완료
  ├── 최소 10~20건 (한국어 이력서/뉴스)
  ├── 엔티티: (text, type) 쌍
  ├── 관계: (subject, predicate, object) 쌍
  └── 담당: ___ / 완료 기한: Phase 0 시작 D-2

□ 데이터셋 GCS 업로드
  ├── DS-RAG-DOCS (200~500 docs, KO/EN 7:3)
  ├── DS-PDF-SAMPLE (20~30 files, 10MB 미만, 5p 이하)
  ├── DS-LLM-EVAL (50~100 examples)
  ├── DS-EMBED-SAMPLE (1K~5K docs)
  └── DS-NER-EVAL (10~20 examples, 사전 라벨링)

□ 프롬프트 파일 준비 (short/medium 한국어·영어 쌍)
```

---

## 0-1. GCP 환경 구성 (3일) — Week 1 Day 1-3

| # | 작업 | 산출물 |
|---|---|---|
| 0-1-1 | SDK 설치 + ADC 인증 확인 | requirements-lock.txt |
| 0-1-2 | Document AI 프로세서 Console 생성 확인 (name 기록) | 프로세서 목록 |
| 0-1-3 | 데이터셋 GCS 업로드 확인 | GCS 파일 목록 |
| 0-1-4 | 비용 추적 유틸리티 동작 확인 | cost_log.jsonl |
| 0-1-5 | DS-NER-EVAL gold 데이터 확인 | gold.jsonl |
| 0-1-6 | Secret Manager 시크릿 등록 | Anthropic, Neo4j API 키 |

### 비용 추적 공통 유틸리티

```python
import json, time, os

COST_LOG_DIR = "results"
os.makedirs(COST_LOG_DIR, exist_ok=True)

def log_api_cost(test_id: str, model_id: str, input_tokens: int,
                 output_tokens: int, latency_ms: float, extra: dict = None):
    """모든 API 호출에서 공통 호출. results/cost_log.jsonl에 누적 저장."""
    entry = {
        "test_id": test_id,
        "model_id": model_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": round(latency_ms, 1),
        "timestamp": time.time(),
    }
    if extra:
        entry.update(extra)
    with open(f"{COST_LOG_DIR}/cost_log.jsonl", "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

---

## 0-2. Vertex AI API 기능 검증 (3일) — Week 1 Day 4 ~ Week 2 Day 1

> **원본**: api-test-3day.md의 핵심 테스트를 Phase 0에 통합.
> **목적**: Gemini API, Embeddings, Document AI, RAG Engine의 기능 동작 여부와 한국어 품질을 검증하여 의사결정 데이터 확보.

### Day 1: Gemini API 기본 추론 + Embeddings API

#### TEST-C1: Gemini API 기본 추론

- 비스트리밍/스트리밍 호출, 시스템 프롬프트, 구조화 JSON 출력
- 모델: gemini-2.5-flash, gemini-2.5-pro
- 한국어 품질 3축 평가 (정확성/환각, 완전성, 도메인 적합성, 총 0~8점)

**Pass 기준**: 정상 응답, ttft < 2s, 한국어 품질 ≥ 6점, 유효 JSON

#### TEST-C2: Embeddings API

- gemini-embedding-001, text-embedding-005 비교
- **[V2-P0패치]** 캘리브레이션 CountTokens 모델을 **생성 모델(gemini-2.5-flash)**로 변경
  (embedding 모델에서 CountTokens 미동작 가능성 대응)
- split-retry 핵심 안전장치 동작 확인
- task_type 4종 (RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, SEMANTIC_SIMILARITY, CLASSIFICATION)
- 한국어 코사인 유사도 정상 확인

```python
# [V2-P0패치] 캘리브레이션 모델을 생성 모델로 변경
CALIBRATED_TOKENS_PER_CHAR = calibrate_tokens_per_char(
    client, calibration_texts, "gemini-2.5-flash"  # NOT "gemini-embedding-001"
)
```

**Pass 기준**: 벡터 반환, 배치 처리 성공, split-retry 동작, 유사 문서 > 0.7

### Day 2: 데이터 수집·정제 → NER 파이프라인

#### ★ 최우선: C5 Corpus + VAS Data Store 생성 (인덱싱 백그라운드)

- RAG Corpus 생성 + Import 트리거 (Day 3 검색 테스트 대비)
- VAS GCS Data Store 생성 + 문서 Import + Search Engine 생성
- **[V2-P0패치]** pending_ops 저장은 op name 없이도 동작 (resource name 중심)

```python
# [V2-P0패치] op name 저장은 "있으면 좋고 없으면 생략"
import_op_name = getattr(getattr(import_op, "operation", None), "name", None) \
                 or getattr(import_op, "name", None)
# op name이 없어도 corpus.name만 있으면 Day 3에서 list_files로 완료 판정 가능
```

#### TEST-DOC: Document AI — PDF 텍스트 추출

- OCR Processor + Layout Parser (Console 사전 생성, name만 사용)
- CER/WER 기반 품질 평가 (CER ≤ 0.10 = GOOD)
- 배치 처리 LRO polling
- **[V2-P0패치]** batch_process에서 `operation.result()`로 성공/실패 확정

```python
# [V2-P0패치] batch LRO 성공/실패 확정
operation = docai_client.batch_process_documents(request=request)
while not operation.done():
    time.sleep(30)

# ★ 반드시 result()로 성공 확인 — done()만으로는 실패도 True
try:
    result = operation.result()
    print(f"배치 처리 성공: {result}")
except Exception as e:
    print(f"배치 처리 실패: {e}")
    raise  # 테스트 실패로 처리
```

#### TEST-MMD: Gemini 멀티모달 — PDF 직접 텍스트 추출

- PDF 크기/페이지 사전 검증 (10MB 미만, 5p 이하)
- 텍스트 추출 + 구조화 출력 동시 테스트
- CER/WER로 Document AI와 직접 비교

#### TEST-NER: Gemini 기반 NER

- Zero-shot / Few-shot 엔티티+관계 추출
- normalize 적용 + Entity-Relation 정합성 체크 (consistency_rate ≥ 90%)
- DS-NER-EVAL 10~20건 정량 평가 (Entity F1 ≥ 0.70, Relation F1 ≥ 0.60)

#### TEST-E2E: 정제→NER 파이프라인 비교

- 방법 A: Document AI → Gemini NER (2단계)
- 방법 B: Gemini 멀티모달 → NER 동시 (1단계)
- 품질·비용·속도 매트릭스 비교 → **Phase 1 파이프라인 방법 확정**

### Day 3: 검색 + 생성 + 운영

#### TEST-C5: RAG 검색+생성

- **[V2-P0패치]** VAS 문서 확인은 전체 list → **첫 1개만 확인**으로 변경

```python
# [V2-P0패치] 1개만 확인하고 멈추기 (전체 list 방지)
docs_iter = doc_client.list_documents(parent=f"{store_name}/branches/default_branch")
first_doc = next(iter(docs_iter), None)
if first_doc:
    print(f"[VAS] 문서 인덱싱 확인: {first_doc.name}")
else:
    print("[VAS] ⚠ 문서 없음 — 인덱싱 미완료")
```

- RAG retrieval + 생성 품질 (hit rate, 한국어 응답 품질)

#### TEST-C6: Grounding (Google Search)

- Google Search 기반 실시간 정보 보강

#### TEST-C10: Prompt Caching

- **[V2-P0패치]** 절감율은 $ 뿐 아니라 **input_tokens 감소율**도 함께 출력

```python
# [V2-P0패치] 토큰 감소율 추가 출력
token_reduction = 1 - (cached_input_tokens / original_input_tokens)
cost_reduction = 1 - (cached_cost / original_cost)
print(f"토큰 감소율: {token_reduction:.1%}")
print(f"비용 절감율(추정): {cost_reduction:.1%}")
```

#### TEST-X1: API 에러 핸들링

- Rate limit, Safety filter, Invalid input 에러 처리 패턴

#### API 검증 결과 종합 + 의사결정

- summarize_costs() 호출 → 테스트별/모델별 비용 집계
- 검증 결과 매트릭스 → Phase 0 의사결정에 직접 반영

---

## 0-3. 데이터 탐색 + 프로파일링 (1주) — Week 2-3

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 0-3-1 | 이력서 원본 GCS 업로드 시작 | GCS | `gs://graphrag-kg-data/raw/resumes/` |
| 0-3-2 | 파일 형식 분포 조사 (PDF/DOCX/HWP) | Cloud Shell | 가정 A11 검증 |
| 0-3-3 | 무작위 500건 샘플링 → 평균 크기, 경력 수 | Cloud Shell | 가정 A2, A4 검증 |
| 0-3-4 | OCR 필요 비율 확인 | Cloud Shell | 가정 A12 검증 |
| 0-3-5 | SimHash 중복률 추정 테스트 | Cloud Shell | 가정 A17 검증 |
| 0-3-6 | JD 보유량 확인 + GCS 업로드 | GCS | 가정 A1 검증 |
| 0-3-7 | NICE DB 접근 확인 + 매칭률 테스트 (100건) | Cloud Functions | 가정 A5 검증 |

---

## 0-4. LLM 추출 품질 PoC (1~2주) — Week 3-4

| # | 작업 | 도구/서비스 | 산출물 |
|---|---|---|---|
| 0-4-1 | 파싱→섹션분할→경력블록 성공률 (50건) | 로컬 Python | 파싱 품질 리포트 |
| 0-4-2 | CandidateContext 추출 모델 비교 (50건) | Anthropic API | 모델 비교 리포트 |
| 0-4-3 | CompanyContext 추출 테스트 (JD 30건) | Anthropic API | 추출 품질 메트릭 |
| 0-4-4 | PII 마스킹 영향 테스트 (10건) | 로컬 Python + API | PII 영향 리포트 |
| 0-4-5 | **Embedding 모델 확정 검증 (20쌍)** | Vertex AI API | **text-multilingual-embedding-002 vs gemini-embedding-001** |
| 0-4-6 | LLM 호출 전략 비교 (10건) | Anthropic API | 호출 전략 결정 |

### Embedding 모델 비교 (V2 통합)

```python
# text-multilingual-embedding-002 (Vertex AI 네이티브)
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

model_v = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")

# gemini-embedding-001 (Phase 0-2에서 이미 검증)
import google.genai as genai
client = genai.Client(vertexai=True, project="graphrag-kg", location="us-central1")

# 20쌍: 같은 도메인 10쌍 + 다른 도메인 10쌍
# Mann-Whitney U test로 분리도 검증
# → Phase 0-6 의사결정에서 최종 확정
```

### LLM 파싱 실패율 사전 측정 (v7 3-tier)

```python
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
```

---

## 0-5. 인프라 셋업 (1주, 0-3과 병행) — Week 3-4

| # | 작업 | GCP 서비스 |
|---|---|---|
| 0-5-1 | Secret Manager 시크릿 등록 | Secret Manager |
| 0-5-2 | Neo4j AuraDB Free 인스턴스 생성 | Neo4j Console |
| 0-5-3 | v10 Graph 스키마 적용 | Neo4j |
| 0-5-4 | Vector Index 설정 (768차원) | Neo4j |
| 0-5-5 | BigQuery 테이블 생성 (6개) | BigQuery |
| 0-5-6 | Artifact Registry 레포 생성 | Artifact Registry |
| 0-5-7 | Industry 마스터 노드 준비 (KSIC 코드) | GCS + 스크립트 |
| 0-5-8 | Docker 베이스 이미지 빌드 | Cloud Build |

```cypher
// Neo4j — v10 Graph 스키마
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.candidate_id IS UNIQUE;
CREATE CONSTRAINT org_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.org_id IS UNIQUE;
CREATE CONSTRAINT vacancy_id IF NOT EXISTS FOR (v:Vacancy) REQUIRE v.vacancy_id IS UNIQUE;
CREATE CONSTRAINT chapter_id IF NOT EXISTS FOR (c:Chapter) REQUIRE c.chapter_id IS UNIQUE;
CREATE CONSTRAINT industry_id IF NOT EXISTS FOR (i:Industry) REQUIRE i.industry_id IS UNIQUE;
CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.canonical_name IS UNIQUE;
CREATE CONSTRAINT role_name IF NOT EXISTS FOR (r:Role) REQUIRE r.canonical_name IS UNIQUE;

// Vector Index (768차원)
CREATE VECTOR INDEX chapter_embedding IF NOT EXISTS
FOR (c:Chapter) ON (c.evidence_chunk_embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX vacancy_embedding IF NOT EXISTS
FOR (v:Vacancy) ON (v.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};
```

```sql
-- BigQuery 테이블 (graphrag_kg 데이터셋)
-- processing_log, chunk_status, mapping_features,
-- quality_metrics, parse_failure_log
-- + crawl 데이터셋: company_targets, homepage_pages,
--   news_articles, extracted_fields, company_crawl_summary
```

---

## 0-6. Phase 0 완료 의사결정 — Week 4-5

| 의사결정 | 판단 기준 | 입력 데이터 |
|---|---|---|
| **Embedding 모델** | 한국어 분별력 (Mann-Whitney U) | Phase 0-2 C2 + 0-4-5 비교 |
| **텍스트 추출 방법** | CER/WER + 비용/속도 매트릭스 | Phase 0-2 DOC vs MMD vs E2E |
| **LLM 모델 선택** | 품질·비용 비교 (Haiku vs Sonnet vs Gemini) | Phase 0-4-2 PoC |
| **PII 전략** | 법무 결론 + 마스킹 영향 | Phase 0-4-4 |
| **오케스트레이션 도구** | DE 역량 + 통합 요구 | 팀 역량 평가 |
| **LLM 호출 전략** | 단건 vs 묶음 품질/비용 | Phase 0-4-6 |
| **섹션 분할 전략** | 파싱 성공률 | Phase 0-4-1 |
| **Graph DB 플랜** | 예상 노드 수 | Phase 0-3 데이터 프로파일 |

### Phase 0 산출물 체크리스트

```
□ API 검증 결과 종합 리포트 (cost_log.jsonl + 검증 매트릭스)
□ LLM 추출 품질 PoC 리포트 (50건 결과)
□ 데이터 프로파일 리포트 (파일 형식, 중복률, OCR 비율)
□ Embedding 모델 비교 리포트
□ 의사결정 문서 (위 8개 항목 확정)
□ Neo4j 스키마 + Vector Index 설정 완료
□ BigQuery 테이블 생성 완료
□ Docker 베이스 이미지 빌드 완료
□ 이력서 원본 GCS 업로드 진행 중 (또는 완료)
```
