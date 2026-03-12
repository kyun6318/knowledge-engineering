# Phase 0: 기반 구축 + API 검증 + PoC (4~5주)

> **목적**: GCP API 기능 검증 + LLM 추출 품질 PoC + 인프라 셋업을 통합 수행.
> 검증 결과가 즉시 의사결정에 반영되도록 한다.
>
> **standard.1 변경**:
> - [standard.2] VAS/RAG Engine 검증 제거 → Day 2~3 단축 (총 2일)
> - [standard.1-2] 0-4에 HWP 파싱 품질 PoC 10건 추가
> - [standard.1-8] Pre-Phase 0에 법무 PII 검토 추가
> - [standard.22] Embedding 비교: text-embedding-005 vs gemini-embedding-001로 통일
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

### [standard.1-8] 법무팀 PII 처리 방침 검토 요청 — Blocking

```bash
□ 법무팀에 PII 처리 방침 검토 요청 (Phase 0 시작 2주 전)
  - 검토 항목:
    ├─ 이력서 PII(이름, 연락처)를 외부 LLM API에 마스킹 전송 가능 여부
    ├─ 마스킹 없이 전송 가능한 조건 (개인정보 처리 동의 존재 시)
    ├─ Anthropic Data Processing Agreement 검토
    └─ 마스킹 적용 시 법적 리스크 해소 여부
  - 예상 소요: 1~3주
□ 법무 결론 도출 기한: Phase 0-4 시작 전 (Week 3)
```

**법무 지연 시 contingency**:
- 마스킹 적용 상태로 Phase 0~1 우선 진행
- 법무 허용 판정 시 마스킹 제거 옵션 적용
- 법무 불허 판정 시 시나리오 C(On-premise GPU) 전환 검토 (+4~8주 추가)

### GCP 프로젝트 사전 준비

```bash
gcloud projects create graphrag-kg --name="GraphRAG Knowledge Graph"
gcloud config set project graphrag-kg

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  bigquery.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  cloudfunctions.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  documentai.googleapis.com \
  storage.googleapis.com
# Note: Cloud Workflows API는 Phase 2에서 활성화 [standard.24]
# Note: Discovery Engine API 제거 [standard.2]

# 서비스 계정
gcloud iam service-accounts create kg-pipeline \
  --display-name="KG Pipeline Service Account"

SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com

for ROLE in storage.objectAdmin bigquery.dataEditor \
  secretmanager.secretAccessor run.invoker \
  monitoring.metricWriter logging.logWriter aiplatform.user; do
  gcloud projects add-iam-policy-binding graphrag-kg \
    --member="serviceAccount:$SA" \
    --role="roles/$ROLE"
done

# Artifact Registry
gcloud artifacts repositories create kg-pipeline \
  --repository-format=docker \
  --location=asia-northeast3

# GCS 버킷 + Object Versioning [standard.20]
gcloud storage buckets create gs://graphrag-kg-data \
  --location=asia-northeast3 \
  --uniform-bucket-level-access
gcloud storage buckets update gs://graphrag-kg-data --versioning

# BigQuery 데이터셋
bq mk --dataset --location=asia-northeast3 graphrag_kg
```

### Anthropic Batch API Quota 사전 확인 — [standard.1-4]

```bash
□ Anthropic 계정 Tier 확인 (Tier 1/2/3/4)
□ 동시 활성 batch 수 한도 확인
□ 일일 요청 한도(RPD) 확인
□ Batch 결과 보관 기간 확인 (현재 29일)
□ Claude Haiku 4.5가 Batch API에서 지원되는 모델인지 확인 [R-3]
□ 필요 시 Tier 업그레이드 또는 한도 증가 요청
  - 예상 필요: 동시 10+ batch, 일 50K+ 요청
  - Tier 업그레이드 소요 시간(1~2주) 감안, Phase 0 시작 최소 3주 전 확인 시작 [R-3]
□ 확인 결과를 Phase 0 의사결정 문서에 기록
```

**[R-3] 동시 batch ≤ 5인 경우 contingency**:
- 처리 기간 6~8주로 연장 (45 라운드 × 12시간 = ~22일 + 버퍼)
- 또는 Gemini Flash 병행 처리로 부하 분산
- Tier 업그레이드 거부 시 → 일일 처리 한도 내에서 순차 제출, 타임라인 Phase 2-1을 5~6주로 조정

### 사전 준비 체크리스트

```
□ GCP 프로젝트 API 활성화 완료
□ 서비스 계정 + ADC 설정
□ SDK 설치 및 버전 확인 → requirements-lock.txt 생성
□ GCS Object Versioning 활성화 확인 [standard.20]

□ Document AI 프로세서: GCP Console에서 사전 생성 (코드 생성 금지)
  ├── OCR Processor → processor name 기록: ___
  └── Layout Parser → processor name 기록: ___

□ DS-NER-EVAL gold 데이터 라벨링 완료
  ├── 최소 10~20건 (한국어 이력서/뉴스)
  ├── 엔티티: (text, type) 쌍
  ├── 관계: (subject, predicate, object) 쌍
  └── 담당: ___ / 완료 기한: Phase 0 시작 D-2

□ 데이터셋 GCS 업로드
  ├── DS-PDF-SAMPLE (20~30 files, 10MB 미만, 5p 이하)
  ├── DS-LLM-EVAL (50~100 examples)
  ├── DS-EMBED-SAMPLE (1K~5K docs)
  └── DS-NER-EVAL (10~20 examples, 사전 라벨링)

□ 프롬프트 파일 준비 (short/medium 한국어·영어 쌍)

□ 법무팀 PII 검토 요청 완료 [standard.1-8]
□ Anthropic Batch API quota 확인 완료 [standard.1-4]
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

## 0-2. Vertex AI API 기능 검증 (2일) — Week 1 Day 4 ~ Week 2 Day 1

> **standard.1 변경**: 3일 → 2일. VAS Data Store / RAG Corpus 생성 및 검색 테스트 제거 [standard.2].
> 이유: VAS(Vertex AI Search)와 RAG Engine은 Phase 1~2 파이프라인에서 미사용.
> Neo4j Vector Index가 최종 retrieval 레이어이므로 검증 불필요.

### Day 1: Gemini API 기본 추론 + Embeddings API

#### TEST-C1: Gemini API 기본 추론

- 비스트리밍/스트리밍 호출, 시스템 프롬프트, 구조화 JSON 출력
- 모델: gemini-2.5-flash, gemini-2.5-pro
- 한국어 품질 3축 평가 (정확성/환각, 완전성, 도메인 적합성, 총 0~8점)

**Pass 기준**: 정상 응답, ttft < 2s, 한국어 품질 ≥ 6점, 유효 JSON

#### TEST-C2: Embeddings API

- **gemini-embedding-001 vs text-embedding-005** 비교 [standard.22 통일]
- **[P0패치]** 캘리브레이션 CountTokens 모델을 **생성 모델(gemini-2.5-flash)**로 변경
- split-retry 핵심 안전장치 동작 확인
- task_type 4종 (RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, SEMANTIC_SIMILARITY, CLASSIFICATION)
- 한국어 코사인 유사도 정상 확인

```python
# [P0패치] 캘리브레이션 모델을 생성 모델로 변경
CALIBRATED_TOKENS_PER_CHAR = calibrate_tokens_per_char(
    client, calibration_texts, "gemini-2.5-flash"  # NOT "gemini-embedding-001"
)
```

**Pass 기준**: 벡터 반환, 배치 처리 성공, split-retry 동작, 유사 문서 > 0.7

### Day 2: 데이터 수집·정제 → NER + 생성 파이프라인

#### TEST-DOC: Document AI — PDF 텍스트 추출

- OCR Processor + Layout Parser (Console 사전 생성, name만 사용)
- CER/WER 기반 품질 평가 (CER ≤ 0.10 = GOOD)
- 배치 처리 LRO polling
- **[P0패치]** batch_process에서 `operation.result()`로 성공/실패 확정

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

#### TEST-C10: Prompt Caching

- **[P0패치]** 절감율은 $ 뿐 아니라 **input_tokens 감소율**도 함께 출력

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
| 0-3-8 | **예상 노드 수 계산** (1,000건 → 450K 외삽) [standard.1-3] | 산출물 | 노드 수 추정 문서 |

### [standard.1-3] 예상 노드 수 계산

```python
# 0-3 프로파일링 결과로 노드 수 추정
# 이력서 1,000건 파싱 결과 기반

avg_chapters_per_person = 5.2     # 프로파일링에서 측정
avg_orgs_per_person = 2.1
avg_skills_per_person = 8.3

total_resumes = 450_000
estimated_nodes = {
    "Person": total_resumes,
    "Chapter": int(total_resumes * avg_chapters_per_person),
    "Organization": 50_000,          # 중복 MERGE 후 추정
    "Vacancy": 10_000,
    "Skill": 5_000,                  # canonical_name 기준 유니크
    "Role": 1_000,
    "Industry": 500,
}
total = sum(estimated_nodes.values())
print(f"총 예상 노드 수: {total:,}")  # ~2.77M
# → AuraDB Free 200K 한도 → Phase 2 전 Professional 전환 필수 확인
```

---

## 0-4. LLM 추출 품질 PoC (1~2주) — Week 3-4

| # | 작업 | 도구/서비스 | 산출물 |
|---|---|---|---|
| 0-4-1 | 파싱→섹션분할→경력블록 성공률 (50건) | 로컬 Python | 파싱 품질 리포트 |
| 0-4-2 | CandidateContext 추출 모델 비교 (50건) | Anthropic API | 모델 비교 리포트 |
| 0-4-3 | CompanyContext 추출 테스트 (JD 30건) | Anthropic API | 추출 품질 메트릭 |
| 0-4-4 | PII 마스킹 영향 테스트 (10건) | 로컬 Python + API | PII 영향 리포트 |
| 0-4-5 | **Embedding 모델 확정 검증 (20쌍)** | Vertex AI API | **text-embedding-005 vs gemini-embedding-001** [standard.22] |
| 0-4-6 | LLM 호출 전략 비교 (10건) | Anthropic API | 호출 전략 결정 |
| 0-4-7 | **HWP 파싱 품질 PoC (10건)** [standard.1-2] | 로컬 Python | HWP 파싱 방법 결정 |

### [standard.1-2] HWP 파싱 품질 PoC

> HWP는 한국 이력서에서 상당 비율을 차지할 수 있으나, 파싱 품질이 방법에 따라 크게 차이남.
> 3가지 방법을 10건 샘플로 비교하여 Phase 1 파싱 모듈에 사용할 방법 확정.

```python
# HWP 파싱 3가지 방법 비교 (10건 샘플)

# 방법 A: LibreOffice CLI 변환
import subprocess
def parse_hwp_libreoffice(hwp_path: str) -> str:
    """HWP → PDF → PyMuPDF 텍스트 추출"""
    subprocess.run([
        "libreoffice", "--headless", "--convert-to", "pdf", hwp_path,
        "--outdir", "/tmp"
    ], check=True, timeout=60)
    pdf_path = hwp_path.replace(".hwp", ".pdf")
    return extract_text_from_pdf(f"/tmp/{os.path.basename(pdf_path)}")

# 방법 B: pyhwp 직접 텍스트 추출
from hwp5.hwp5txt import Hwp5Txt
def parse_hwp_pyhwp(hwp_path: str) -> str:
    """HWP → 텍스트 직접 추출 (표 구조 손실 가능)"""
    return Hwp5Txt(hwp_path).text()

# 방법 C: Gemini 멀티모달 (HWP→PDF→이미지→Gemini)
def parse_hwp_gemini(hwp_path: str) -> str:
    """HWP → PDF → 페이지 이미지 → Gemini 멀티모달 텍스트 추출"""
    pdf_path = convert_hwp_to_pdf(hwp_path)
    images = pdf_to_images(pdf_path)
    return gemini_extract_text(images)

# 평가 기준:
# 1. 텍스트 추출 완전성 (CER 기준, gold 수동 입력 대비)
# 2. 표 구조 보존률 (표 포함 이력서 5건 중)
# 3. 한글 폰트 렌더링 정확도
# 4. 처리 시간 + 비용
# 5. Docker 이미지 크기 영향

hwp_poc_results = []
for hwp_file in hwp_samples_10:
    gold_text = manual_transcription[hwp_file]
    for method_name, method_fn in [
        ("libreoffice", parse_hwp_libreoffice),
        ("pyhwp", parse_hwp_pyhwp),
        ("gemini", parse_hwp_gemini),
    ]:
        extracted = method_fn(hwp_file)
        cer = compute_cer(gold_text, extracted)
        table_preserved = check_table_structure(gold_text, extracted)
        hwp_poc_results.append({
            "file": hwp_file,
            "method": method_name,
            "cer": cer,
            "table_preserved": table_preserved,
            "processing_time_ms": ...,
        })

# Pass 기준: CER ≤ 0.15, 표 구조 보존 ≥ 60%

# [R-5] pyhwp 리스크 확인 항목:
#   - HWPX(한글 2014 이후 표준) 파일 처리 가능 여부 테스트
#   - 인코딩 깨짐/비정상 출력 발생률 측정
#   - pyhwp 실패 시 → LibreOffice가 유일한 현실적 대안
#   - 10건 샘플에서 HWP5 vs HWPX 비율 확인 → HWPX 비율 높으면 pyhwp 제외
```

### Embedding 모델 비교 (standard.1 통합) — [standard.22]

```python
# text-embedding-005 (Vertex AI 네이티브) — v2의 "text-multilingual-embedding-002"에서 변경
from vertexai.language_models import TextEmbeddingModel
model_v = TextEmbeddingModel.from_pretrained("text-embedding-005")

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
| 0-5-2a | **APOC Extended 지원 여부 즉시 확인** (`apoc.export.json.all` 동작 테스트) [R-2] | Neo4j Console |
| 0-5-3 | v10 Graph 스키마 적용 | Neo4j |
| 0-5-4 | Vector Index 설정 (768차원) | Neo4j |
| 0-5-5 | BigQuery 테이블 생성 (7개 — batch_tracking 추가) [standard.1-5] | BigQuery |
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
-- processing_log, chunk_status, batch_tracking [standard.1-5],
-- mapping_features, quality_metrics, parse_failure_log
-- + crawl 데이터셋: company_targets, homepage_pages,
--   news_articles, extracted_fields, company_crawl_summary

-- [standard.1-5] Batch API 추적 테이블
CREATE TABLE graphrag_kg.batch_tracking (
  batch_id STRING NOT NULL,
  chunk_id STRING NOT NULL,
  status STRING,            -- SUBMITTED / PROCESSING / COMPLETED / FAILED / EXPIRED
  submitted_at TIMESTAMP,
  completed_at TIMESTAMP,
  result_collected BOOLEAN DEFAULT FALSE,
  retry_count INT64 DEFAULT 0,
  gcs_request_path STRING,
  gcs_response_path STRING
);
```

---

## 0-6. Phase 0 완료 의사결정 — Week 4-5

| 의사결정 | 판단 기준 | 입력 데이터 |
|---|---|---|
| **Embedding 모델** | 한국어 분별력 (Mann-Whitney U) | Phase 0-2 C2 + 0-4-5 비교 |
| **텍스트 추출 방법** | CER/WER + 비용/속도 매트릭스 | Phase 0-2 DOC vs MMD vs E2E |
| **LLM 모델 선택** | 품질·비용 비교 (Haiku vs Sonnet vs Gemini) | Phase 0-4-2 PoC |
| **PII 전략** | 법무 결론 + 마스킹 영향 | Phase 0-4-4 + Pre-Phase 0 법무 [standard.1-8] |
| **HWP 파싱 방법** | CER + 표 보존 + 비용 | Phase 0-4-7 [standard.1-2] |
| **LLM 호출 전략** | 단건 vs 묶음 품질/비용 | Phase 0-4-6 |
| **섹션 분할 전략** | 파싱 성공률 | Phase 0-4-1 |
| **Graph DB 플랜** | 예상 노드 수 계산 | Phase 0-3-8 [standard.1-3] |
| **Batch API 처리 계획** | quota 확인 결과 | Pre-Phase 0 확인 [standard.1-4] |

### Phase 0 산출물 체크리스트

```
□ API 검증 결과 종합 리포트 (cost_log.jsonl + 검증 매트릭스)
□ LLM 추출 품질 PoC 리포트 (50건 결과)
□ HWP 파싱 품질 PoC 리포트 (10건, 3방법 비교) [standard.1-2]
□ 데이터 프로파일 리포트 (파일 형식, 중복률, OCR 비율)
□ 예상 노드 수 계산 + Neo4j 전환 계획 확정 [standard.1-3]
□ Embedding 모델 비교 리포트 (text-embedding-005 vs gemini-embedding-001) [standard.22]
□ Anthropic Batch API quota 확인 결과 + 처리 계획 [standard.1-4]
□ 법무 PII 검토 결과 (또는 지연 시 contingency 적용) [standard.1-8]
□ 의사결정 문서 (위 9개 항목 확정)
□ Neo4j 스키마 + Vector Index 설정 완료
□ BigQuery 테이블 생성 완료 (batch_tracking 포함)
□ Docker 베이스 이미지 빌드 완료
□ 이력서 원본 GCS 업로드 진행 중 (또는 완료)
```
