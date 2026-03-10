# Phase 0: 기반 구축 + API 검증 + PoC (2.5주)

> **목적**: GCP API 검증 + LLM 추출 품질 PoC + 인프라 셋업을 **완전 병렬**로 2.5주 내에 완료.
> standard.1의 4~5주를 2.5주로 압축하되, 의사결정 품질은 보존한다.
>
> **light.1 압축 전략**:
> - standard.1의 0-1~0-6을 4개 병렬 트랙(0-A/0-B/0-C/0-D)으로 재구성
> - API 검증 항목 중 Phase 1에 불필요한 것 제거 (RAG Engine, VAS, Grounding)
> - standard.1의 핵심 의사결정 6개 통합 (Embedding 모델, 텍스트 추출, LLM 모델, PII 전략, HWP 파싱, Graph DB 플랜)
>
> **인력**: DE 1명 + MLE 1명 풀타임, 도메인 전문가 1명 파트타임

---

## 사전 준비 (Pre-Phase 0) — Blocking Dependencies

> Phase 0 시작 **2주 전**까지 완료 필요.

### Blocking #1: [standard.1-8] 법무팀 PII 처리 방침 검토 요청

```bash
□ 법무팀에 PII 처리 방침 검토 요청 (Phase 0 시작 2주 전)
  - 검토 항목:
    ├─ 이력서 PII(이름, 연락처)를 외부 LLM API에 마스킹 전송 가능 여부
    ├─ 마스킹 없이 전송 가능한 조건 (개인정보 처리 동의 존재 시)
    ├─ Anthropic Data Processing Agreement 검토
    └─ 마스킹 적용 시 법적 리스크 해소 여부
  - 예상 소요: 1~3주
□ 법무 결론 도출 기한: Phase 0-C 시작 전 (Week 2)
```

**법무 지연 시 contingency**:
- 마스킹 적용 상태로 Phase 0~1 우선 진행
- 법무 허용 판정 시 마스킹 제거 옵션 적용
- 법무 불허 판정 시 시나리오 C(On-premise GPU) 전환 검토 (+4~8주 추가)

### Blocking #2: [standard.1-4] Anthropic Batch API Quota 사전 확인

```bash
□ Anthropic 계정 Tier 확인 (Tier 1/2/3/4)
□ 동시 활성 batch 수 한도 확인
□ 일일 요청 한도(RPD) 확인
□ Batch 결과 보관 기간 확인 (현재 29일)
□ Claude Haiku 4.5가 Batch API에서 지원되는 모델인지 확인
□ 필요 시 Tier 업그레이드 또는 한도 증가 요청
  - 예상 필요: 동시 10+ batch, 일 50K+ 요청
  - Tier 업그레이드 소요 시간(1~2주) 감안, Phase 0 시작 최소 3주 전 확인 시작
□ 확인 결과를 Phase 0 의사결정 문서에 기록
```

**동시 batch ≤ 5인 경우 contingency**:
- 처리 기간 6~8주로 연장 (45 라운드 × 12시간 = ~22일 + 버퍼)
- 또는 Gemini Flash 병행 처리로 부하 분산
- Tier 업그레이드 거부 시 → 일일 처리 한도 내에서 순차 제출, 타임라인 Phase 2-1을 5~6주로 조정

### GCP 프로젝트 사전 준비

```bash
gcloud projects create graphrag-kg --name="GraphRAG Knowledge Graph"
gcloud config set project graphrag-kg

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  workflows.googleapis.com \
  secretmanager.googleapis.com \
  bigquery.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  cloudfunctions.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  documentai.googleapis.com \
  storage.googleapis.com

SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com
gcloud iam service-accounts create kg-pipeline \
  --display-name="KG Pipeline Service Account"

for ROLE in storage.objectAdmin bigquery.dataEditor \
  secretmanager.secretAccessor run.invoker \
  workflows.invoker monitoring.metricWriter \
  logging.logWriter aiplatform.user; do
  gcloud projects add-iam-policy-binding graphrag-kg \
    --member="serviceAccount:$SA" \
    --role="roles/$ROLE"
done

gcloud artifacts repositories create kg-pipeline \
  --repository-format=docker \
  --location=asia-northeast3

# GCS 버킷 + Object Versioning [standard.20]
gcloud storage buckets create gs://graphrag-kg-data \
  --location=asia-northeast3 \
  --uniform-bucket-level-access
gcloud storage buckets update gs://graphrag-kg-data --versioning

bq mk --dataset --location=asia-northeast3 graphrag_kg
```

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

□ 데이터셋 GCS 업로드 준비
  ├── DS-PDF-SAMPLE (20~30 files, 10MB 미만, 5p 이하)
  ├── DS-LLM-EVAL (50~100 examples)
  ├── DS-EMBED-SAMPLE (1K~5K docs)
  └── DS-NER-EVAL (10~20 examples, 사전 라벨링)

□ NICE DB 접근 계약 상태 확인 (미확보 시 DART 대체)
□ 법무팀 PII 검토 요청 완료 [standard.1-8]
□ Anthropic Batch API quota 확인 완료 [standard.1-4]
```

---

## 병렬 트랙 구성 (Week 1 ~ Week 2.5)

```
Week 1                              Week 2                    Week 2.5
──────────────────────────────────────────────────────────────────────
[DE]  ── 0-A: 환경 + 데이터 업로드 ──── 0-B: 프로파일링 ────┐
                                                               ├─ 의사결정
[MLE] ── 0-A: API 검증 (3일) ─── 0-C: LLM PoC ──────────────┘

[병행] ── 0-D: 인프라 셋업 (DE/MLE 여유 시간 활용) ───────────
```

---

## 0-A. GCP 환경 + API 검증 (3일) — Week 1 Day 1-3

### DE 담당: 환경 구성 + 데이터 업로드

| # | 작업 | 산출물 |
|---|---|---|
| 0-A-1 | SDK 설치 + ADC 인증 확인 | requirements-lock.txt |
| 0-A-2 | 테스트 데이터셋 GCS 업로드 | GCS 파일 확인 |
| 0-A-3 | 이력서 원본 GCS 업로드 시작 (백그라운드) | gsutil rsync 실행 |
| 0-A-4 | Secret Manager 시크릿 등록 | Anthropic, Neo4j 키 |
| 0-A-5 | 비용 추적 유틸리티 세팅 | cost_log.jsonl |

### MLE 담당: Vertex AI API 검증 (3일)

> v2 대비 검증 항목 간소화: KG 파이프라인에 직접 필요한 것만 검증.

#### Day 1: Gemini API + Embeddings [standard.2]

| 테스트 | 내용 | Pass 기준 |
|--------|------|----------|
| TEST-C1 | Gemini API 기본 추론 (Flash/Pro, 한국어, JSON 출력) | ttft < 2s, 한국어 ≥ 6점 |
| TEST-C2 | **Embeddings 비교: text-embedding-005 vs gemini-embedding-001** [standard.22] | 벡터 반환, 유사 > 0.7 |

```python
# [P0패치] 캘리브레이션 모델을 생성 모델로 변경
CALIBRATED_TOKENS_PER_CHAR = calibrate_tokens_per_char(
    client, calibration_texts, "gemini-2.5-flash"  # NOT "text-multilingual-embedding-002"
)
```

#### Day 2: Document AI + Gemini 멀티모달

| 테스트 | 내용 | Pass 기준 |
|--------|------|----------|
| TEST-DOC | Document AI OCR + Layout Parser (20건) | CER ≤ 0.10 |
| TEST-MMD | Gemini 멀티모달 PDF 추출 (20건) | CER ≤ 0.10 |
| TEST-E2E | 방법 A(DocAI→NER) vs 방법 B(Gemini 멀티모달→NER) | 품질/비용/속도 매트릭스 |

```python
# [V2-P0패치 유지] batch LRO 성공/실패 확정
operation = docai_client.batch_process_documents(request=request)
while not operation.done():
    time.sleep(30)
try:
    result = operation.result()
except Exception as e:
    raise
```

#### Day 3: NER + 에러 핸들링

| 테스트 | 내용 | Pass 기준 |
|--------|------|----------|
| TEST-NER | Gemini 기반 NER (Zero/Few-shot, 10건) | Entity F1 ≥ 0.70 |
| TEST-X1 | API 에러 핸들링 (rate limit, safety filter) | 재시도 패턴 동작 |

### v2 대비 제거된 검증 항목

| 항목 | 제거 사유 |
|------|----------|
| TEST-C5 (RAG Corpus + 검색) | KG 파이프라인에서 RAG Engine 미사용 |
| TEST-C6 (Grounding) | KG 파이프라인에서 미사용 |
| TEST-C10 (Prompt Caching) | Batch API 사용, Prompt Caching 비적용 |
| VAS Data Store 생성 | KG 파이프라인에서 미사용 |
| Discovery Engine 테스트 | KG 파이프라인에서 미사용 |

---

## 0-B. 데이터 탐색 + 프로파일링 (1주) — Week 1-2

> DE 담당. 0-A 완료 후 즉시 시작. 0-A-3 업로드와 병행.

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 0-B-1 | 파일 형식 분포 (PDF/DOCX/HWP) | Cloud Shell | 가정 A11 검증 |
| 0-B-2 | 무작위 500건 샘플 → 평균 크기, 경력 수 | Cloud Shell | 가정 A2, A4 검증 |
| 0-B-3 | OCR 필요 비율 확인 | Cloud Shell | 가정 A12 검증 |
| 0-B-4 | SimHash 중복률 추정 (1,000건 샘플) | Cloud Shell | 가정 A17 검증 |
| 0-B-5 | JD 보유량 확인 + GCS 업로드 | GCS | 가정 A1 검증 |
| 0-B-6 | NICE DB 접근 확인 + 매칭률 (100건) | Cloud Functions | 가정 A5 검증 |
| 0-B-8 | **예상 노드 수 계산** (1,000건 → 450K 외삽) [standard.1-3] | Python | 노드 수 추정 문서 |

### [standard.1-3] 예상 노드 수 계산

```python
# 0-B 프로파일링 결과로 노드 수 추정
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

## 0-C. LLM 추출 품질 PoC (1.5주) — Week 1.5~2.5

> MLE 담당. 0-A API 검증 완료 후 시작.

| # | 작업 | 도구/서비스 | 산출물 |
|---|---|---|---|
| 0-C-1 | 파싱→섹션분할→경력블록 성공률 (50건) | 로컬 Python | 파싱 품질 리포트 |
| 0-C-2 | CandidateContext 추출 모델 비교 (50건) | Anthropic API | 모델 비교 리포트 |
| 0-C-3 | CompanyContext 추출 테스트 (JD 30건) | Anthropic API | 추출 품질 메트릭 |
| 0-C-4 | PII 마스킹 영향 테스트 (10건) | 로컬 Python | PII 영향 리포트 |
| 0-C-5 | **Embedding 모델 확정 검증** (20쌍) | Vertex AI | **text-embedding-005 vs gemini-embedding-001** [standard.22] |
| 0-C-7 | **HWP 파싱 PoC** (10건, 3방법 비교) [standard.1-2] | 로컬 Python | HWP 파싱 방법 결정 |

### LLM 파싱 실패율 사전 측정

```python
parse_stats = {"tier1": 0, "tier2": 0, "tier3_partial": 0, "tier3_fail": 0}

for resume in poc_50:
    result, tier, partial = parse_llm_response(raw, CandidateExperience, resume.id)
    parse_stats[f"tier{tier[4:]}" if not partial else "tier3_partial"] += 1

# 목표: tier1 > 85%, tier3_fail < 3%
# 미달 시: 프롬프트 재설계 (+1주 버퍼)
```

### [standard.22] Embedding 모델 비교: text-embedding-005 vs gemini-embedding-001

```python
from vertexai.language_models import TextEmbeddingModel
import google.genai as genai

# text-embedding-005 (Vertex AI 네이티브)
model_v = TextEmbeddingModel.from_pretrained("text-embedding-005")

# gemini-embedding-001 (Phase 0-A에서 이미 검증)
client = genai.Client(vertexai=True, project="graphrag-kg", location="us-central1")

# 20쌍: 같은 도메인 10쌍 + 다른 도메인 10쌍
# Mann-Whitney U test로 분리도 검증
# → Phase 0 의사결정에서 최종 확정
```

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

---

## 0-D. 인프라 셋업 (1주, 0-A/0-B와 병행) — Week 1-2

> DE/MLE가 0-A/0-B 여유 시간에 분담. 0-B와 완전 병행.

| # | 작업 | GCP 서비스 | 담당 |
|---|---|---|---|
| 0-D-1 | Neo4j AuraDB Free 인스턴스 생성 | Neo4j Console | MLE |
| 0-D-2 | v10 Graph 스키마 적용 (Constraint + Index) | Neo4j | MLE |
| 0-D-2a | **APOC Extended 지원 여부 즉시 확인** (`apoc.export.json.all` 동작 테스트) [standard.1-3/R-2] | Neo4j Console | MLE |
| 0-D-3 | Vector Index 설정 (768차원 기본, 의사결정 후 변경 가능) | Neo4j | MLE |
| 0-D-4 | BigQuery 테이블 생성 (7개 — batch_tracking 추가) [standard.1-5] | BigQuery | DE |
| 0-D-5 | Artifact Registry 레포 생성 | Artifact Registry | DE |
| 0-D-6 | Docker 베이스 이미지 빌드 | Cloud Build | DE |
| 0-D-7 | Industry 마스터 노드 준비 (KSIC 코드) | GCS + 스크립트 | DE |

```cypher
// Neo4j — v10 Graph 스키마
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.candidate_id IS UNIQUE;
CREATE CONSTRAINT org_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.org_id IS UNIQUE;
CREATE CONSTRAINT vacancy_id IF NOT EXISTS FOR (v:Vacancy) REQUIRE v.vacancy_id IS UNIQUE;
CREATE CONSTRAINT chapter_id IF NOT EXISTS FOR (c:Chapter) REQUIRE c.chapter_id IS UNIQUE;
CREATE CONSTRAINT industry_id IF NOT EXISTS FOR (i:Industry) REQUIRE i.industry_id IS UNIQUE;
CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.canonical_name IS UNIQUE;
CREATE CONSTRAINT role_name IF NOT EXISTS FOR (r:Role) REQUIRE r.canonical_name IS UNIQUE;

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

## Phase 0 의사결정 — Week 2.5

### Go/No-Go 게이트

| 기준 | 최소 통과 | 미달 시 대응 |
|------|----------|------------|
| LLM 추출 (50건) tier1 비율 | > 80% | 프롬프트 재설계 (+1주) |
| Embedding 한국어 분별력 | 유사 > 비유사 (p < 0.05) | 모델 변경 |
| 파싱 성공률 | > 90% | 파서 보강 (+0.5주) |
| 비용 추정 대비 실제 | ±30% 이내 | 예산 재조정 |

**모든 기준 미달**: 접근법 재검토 (1주 추가 조사 → 재판정)

### 의사결정 항목 (6개 — standard.1 통합)

| 의사결정 | 판단 기준 | 입력 데이터 |
|---|---|---|
| **1. Embedding 모델** | 한국어 분별력 (Mann-Whitney U) | 0-A TEST-C2 + 0-C-5 비교 [standard.22] |
| **2. 텍스트 추출 방법** | CER/WER + 비용/속도 매트릭스 | 0-A TEST-DOC vs TEST-MMD vs TEST-E2E |
| **3. LLM 모델 선택** | 품질·비용 (Haiku vs Sonnet vs Gemini) | 0-C-2 PoC |
| **4. PII 전략** | 법무 결론 + 마스킹 영향 | 0-C-4 + Pre-Phase 0 법무 [standard.1-8] |
| **5. HWP 파싱 방법** | CER + 표 보존 + 비용 | 0-C-7 [standard.1-2] |
| **6. Graph DB 플랜 + Batch API** | 예상 노드 수 + quota 처리 계획 | 0-B-8 [standard.1-3] + Pre-Phase 0 [standard.1-4] |

---

## Phase 0 산출물 체크리스트

```
□ API 검증 결과 종합 리포트 (cost_log.jsonl + 검증 매트릭스)
□ LLM 추출 품질 PoC 리포트 (50건 결과)
□ HWP 파싱 품질 PoC 리포트 (10건, 3방법 비교) [standard.1-2]
□ 데이터 프로파일 리포트 (파일 형식, 중복률, OCR 비율)
□ 예상 노드 수 계산 + Neo4j 전환 계획 확정 [standard.1-3]
□ Embedding 모델 비교 리포트 (text-embedding-005 vs gemini-embedding-001) [standard.22]
□ Anthropic Batch API quota 확인 결과 + 처리 계획 [standard.1-4]
□ 법무 PII 검토 결과 (또는 지연 시 contingency 적용) [standard.1-8]
□ 의사결정 문서 (6개 항목 확정)
□ Neo4j 스키마 + Vector Index 설정 완료
□ BigQuery 테이블 생성 완료 (batch_tracking 포함) [standard.1-5]
□ Docker 베이스 이미지 빌드 완료
□ 이력서 원본 GCS 업로드 진행 중 (또는 완료)
□ Go/No-Go 판정: GO / NO-GO
```
