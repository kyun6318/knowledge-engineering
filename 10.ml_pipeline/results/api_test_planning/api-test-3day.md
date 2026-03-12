# Vertex AI API 기능 테스트 — GraphRAG + LLM 집중 (3일) v2

> **원본**: `api-test2.md` (v4, 5주 계획)에서 GraphRAG 구축 및 LLM API 기능 검증에 필수적인 항목만 추출.
> **v2 변경 이력**:
> - Day 3 과부하 해소: C5 corpus + VAS Data Store 생성을 Day 2 오전으로 이동
> - VAS 웹 크롤링을 옵션으로 분리, GCS 기반만 필수
> - RAG Engine import 완료 대기(폴링) 명시 추가
> - NER gold 데이터 준비 일정 명시 + normalize/entity-relation 정합성 체크 추가
> - DocAI 프로세서 사전 Console 생성 방식으로 변경 + batch LRO polling
> - 텍스트 추출 품질 지표를 CER(Character Error Rate) / WER(Word Error Rate)로 변경
> - 비용 추적 공통 유틸리티 추가
> - C10 Prompt Caching contents 필드 보완 + 재전달 금지 규칙 명시
> - tokens_per_char 캘리브레이션 + split-retry 로직 추가
> - Gemini 멀티모달 PDF 크기 제한 규칙 추가
> - X1 Rate Limit/Safety 테스트 Pass 기준 현실화

> **목적**: Gemini API, Embeddings, Document AI, RAG Engine의 **기능 동작 여부**와 **한국어 품질**을 검증하여 GraphRAG 서비스 설계 의사결정에 필요한 데이터를 확보한다.

> **테스트 범위**: 크롤링(Document AI,Vertex AI Search,Gemini 멀티모달), NER 작업 graphrag 구축과 llm api를 사용하기 위한 기능 테스트 위주 테스트

---

## 테스트 구조 — GraphRAG 파이프라인 순서

```
Day 1                           Day 2                                     Day 3
┌───────────────────┐  ┌───────────────────────────────────────┐  ┌──────────────────────┐
│ LLM 기본 기능       │  │ 데이터 수집 → 정제 → NER                │  │ 검색 + 생성 + 운영     │
├───────────────────┤  ├───────────────────────────────────────┤  ├──────────────────────┤
│ C1: Gemini API    │  │ ★ C5 corpus + VAS Data Store 생성     │  │ C5: RAG 검색+생성     │
│ C2: Embedding     │  │   (오전 최우선 — 인덱싱 백그라운드 대기)  │  │ VAS: Vertex AI Search│
│                   │  │ DOC: Document AI (PDF→텍스트)          │  │ C6: Grounding        │
│                   │  │ MMD: Gemini 멀티모달 (비교)             │  │ C10: Prompt Caching  │
│                   │  │ NER: 엔티티/관계 추출                   │  │ X1: 에러 핸들링       │
│                   │  │ E2E: 정제→NER 파이프라인 비교            │  │ 결과 종합 + 의사결정   │
└───────────────────┘  └───────────────────────────────────────┘  └──────────────────────┘
```

> **Day 2 → Day 3 핸드오프**: Day 2 오전에 트리거한 C5 corpus import와 VAS 문서 인덱싱이 Day 2 작업 중 백그라운드로 완료됨. Day 3 시작 시 즉시 검색 테스트 진입 가능.

---

## 범위 및 제외 사항

### 포함 (기능 테스트 중심)

| ID | 테스트 | 이유 |
|----|--------|------|
| C1 | Gemini API 기본 추론 | LLM API 핵심 — 호출 패턴, 스트리밍, 한국어 품질 |
| C2 | Embeddings API | GraphRAG 문서 임베딩 필수 |
| DOC | Document AI | 크롤링 결과물(PDF/이미지) → 구조화 텍스트 추출 |
| MMD | Gemini 멀티모달 입력 | PDF/이미지 직접 입력으로 텍스트 추출+정제 (Document AI 대안) |
| NER | Gemini 기반 NER (엔티티 추출) | GraphRAG 지식 그래프 구축 핵심 — 엔티티/관계 추출 |
| C5 | RAG Engine | GraphRAG 검색+생성 핵심 |
| VAS | Vertex AI Search (Discovery Engine) | URL 기반 자동 크롤링+인덱싱, RAG 보완 |
| C6 | Grounding (Google Search) | RAG 보완 — 실시간 정보 |
| C10 | Prompt Caching | GraphRAG 운영 비용 절감 검증 |
| X1 | API 에러 핸들링 | 에러 코드/재시도 패턴 확인 |

### 제외

| 항목 | 제외 이유 |
|------|----------|
| Part A (AutoML, Feature Store, Model Registry, Batch Predict) | GraphRAG와 무관한 Traditional ML |
| Part B (GPU/TPU 학습, KFP, HPT, 분산학습, KGE 서빙) | Deep Learning 학습 인프라 — 별도 일정 |
| C3/C4 (SFT, LoRA Fine-Tuning) | 초기 GraphRAG 구축에 불필요, 추후 품질 개선 단계 |
| C7 (Model Garden 오픈 모델) | 모델 비교는 C1 결과로 충분 |
| C8 (Live API) | 실시간 스트리밍 세션 — GraphRAG 초기 불필요 |
| C9 (Agent Engine) | 에이전트 배포 — 별도 일정 |
| X2 (SDK vs REST 일관성) | 기능 검증 후 필요 시 추가 |
| X3 (Billing 정확성) | 3일 테스트에서는 공통 비용 유틸로 대체 |
| 성능 부하 테스트 (QPS, 동시성, 스케일링) | 기능 확인 후 별도 수행 |
| KR probe runner (asia-northeast3) | 리전 latency 측정은 별도 |

---

## 공통 환경 구성

```
프로젝트: ml-api-test-vertex
리전:
  us-central1          — Vertex AI 리소스 (LLM, Embedding, RAG, Vertex AI Search)
  us (멀티리전)         — Document AI 프로세서 전용 (us/eu 리전만 지원)
  global               — Discovery Engine (Vertex AI Search)
Budget Alert: $500 (경고), $800 (강제 중단)

SDK 버전 (전 테스트 통일):
  google-genai >= 1.5.0                   # LLM / Embedding / RAG
  google-cloud-aiplatform >= 1.74.0       # 보조 (필요 시)
  google-cloud-documentai >= 2.29.0       # Document AI
  google-cloud-discoveryengine >= 0.13.0  # Vertex AI Search
  pypdf >= 4.0.0                          # PDF 페이지 수 검증 (validate_pdf)

API 활성화 필요:
  - Vertex AI API
  - Cloud Storage API
  - Document AI API (리전: us)
  - Discovery Engine API (Vertex AI Search)

# ⚠ Deprecated 사용 금지
# vertexai.generative_models → google.genai
# vertexai.language_models   → google.genai
```

### 사전 준비 체크리스트 (테스트 시작 전 완료)

```
□ GCP 프로젝트 API 활성화 (Vertex AI, Cloud Storage, Document AI, Discovery Engine)
□ 서비스 계정 + ADC 설정
□ SDK 설치 및 버전 확인 → requirements-lock.txt 생성

□ Document AI 프로세서: GCP Console에서 사전 생성 (코드 생성 금지)
  ├── OCR Processor → processor name 기록: ___
  └── Layout Parser → processor name 기록: ___
  ⚠ type 문자열은 Console UI 기준. API type 문자열(OCR_PROCESSOR 등)은 버전마다 다를 수 있음

□ DS-NER-EVAL gold 데이터 라벨링 완료
  ├── 최소 10~20건 (한국어 이력서/뉴스)
  ├── 엔티티: (text, type) 쌍
  ├── 관계: (subject, predicate, object) 쌍
  └── 담당: ___ / 완료 기한: 테스트 D-2

□ 데이터셋 GCS 업로드 (전체)
□ DS-PDF-SAMPLE 선별 기준: 10MB 미만, 5페이지 이하, 레이아웃 다양성 확보
  ├── 단순 텍스트 (KO/EN 각 3개)
  ├── 2단 레이아웃 (KO/EN 각 2개)
  ├── 표 포함 (KO/EN 각 3개)
  └── 이미지 포함 (KO/EN 각 2개)
□ 프롬프트 파일 준비 (short/medium 한국어·영어 쌍)
```

### 데이터셋 (최소 구성)

| ID | 용도 | 형태 | 크기 | 언어 |
|----|------|------|------|------|
| `DS-RAG-DOCS` | RAG 문서 (이력서+뉴스) | PDF + TXT | 200~500 docs | KO/EN 7:3 |
| `DS-PDF-SAMPLE` | Document AI / 멀티모달 평가 | PDF (이력서, 뉴스, 표 포함) | 20~30 files (**10MB 미만, 5p 이하**) | KO/EN 7:3 |
| `DS-LLM-EVAL` | LLM 평가셋 | JSONL | 50~100 examples | KO/EN 7:3 |
| `DS-EMBED-SAMPLE` | 임베딩 품질 평가 | JSONL | 1K~5K docs | KO/EN 7:3 |
| `DS-NER-EVAL` | NER 평가셋 (텍스트 + **정답 엔티티/관계**) | JSONL | 10~20 examples (**사전 라벨링 필수**) | KO/EN 7:3 |

### 한국어 품질 평가 기준 (3축)

| 축 | 설명 | 점수 |
|----|------|------|
| 정확성/환각 | 사실 오류, 존재하지 않는 정보 생성 여부 | 0~3 |
| 완전성 | 질문 의도를 충분히 충족했는가 | 0~3 |
| 도메인 적합성 | 채용/이력서/기업 맥락 용어·표현 적절성 | 0~2 |
| **합계** | 6점 이상 = 사용 가능, 4~5 = 개선 필요, 3 이하 = 불가 | **0~8** |

### 비용 추적 공통 유틸리티

> Cloud Logging 이중 추적은 3일 플랜에서 과잉. 대신 모든 API 호출의 토큰/비용을 로컬 JSONL로 누적 저장.

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

def summarize_costs():
    """Day 3 결과 종합 시 호출 — 테스트별/모델별 토큰 집계 + 추정 비용($) 산출.
    ⚠ v2.1: 추정 비용 추가 — 정확 청구는 Billing에서 확인, 여기서는 의사결정용 참고치.
    """
    from collections import defaultdict

    # 모델별 단가 (USD per 1K tokens, 2025 Q4 기준 — 변동 가능)
    PRICE_PER_1K = {
        # (input, output) per 1K tokens
        "gemini-2.5-flash":       (0.00015, 0.0006),
        "gemini-2.5-pro":         (0.00125, 0.005),
        "gemini-embedding-001":   (0.00004, 0.0),     # 임베딩: input만
        "text-embedding-005":     (0.00004, 0.0),
        "docai-ocr":              (0.0, 0.0),          # 페이지 단가라 토큰 기반 아님
        "docai-layout":           (0.0, 0.0),
        "discovery-engine":       (0.0, 0.0),          # 검색 단가 별도
        "rag-retrieval":          (0.0, 0.0),
        "pipeline-a":             (0.0, 0.0),          # E2E는 개별 모델에서 이미 집계
        "pipeline-b":             (0.0, 0.0),
    }

    totals = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "calls": 0})
    with open(f"{COST_LOG_DIR}/cost_log.jsonl") as f:
        for line in f:
            entry = json.loads(line)
            key = (entry["test_id"], entry["model_id"])
            totals[key]["input_tokens"] += entry["input_tokens"]
            totals[key]["output_tokens"] += entry["output_tokens"]
            totals[key]["calls"] += 1

    total_estimated = 0.0
    print(f"\n{'='*70}")
    print(f"{'테스트':>15} {'모델':>25} {'입력토큰':>10} {'출력토큰':>10} {'호출':>5} {'추정$':>8}")
    print(f"{'='*70}")
    for (test_id, model_id), v in sorted(totals.items()):
        prices = PRICE_PER_1K.get(model_id, (0.001, 0.002))  # 미등록 모델 보수적 기본값
        est = (v["input_tokens"] / 1000 * prices[0] +
               v["output_tokens"] / 1000 * prices[1])
        total_estimated += est
        print(f"{test_id:>15} {model_id:>25} {v['input_tokens']:>10,} "
              f"{v['output_tokens']:>10,} {v['calls']:>5} ${est:>7.3f}")

    print(f"{'='*70}")
    print(f"{'추정 합계':>53} ${total_estimated:>7.2f}")
    print(f"  ⚠ Document AI, VAS Enterprise, Grounding 비용은 토큰 기반이 아님 — Billing에서 별도 확인")
```

### GCS 구조

```yaml
gs://ml-api-test-vertex/
├── datasets/
│   ├── DS-RAG-DOCS/
│   ├── DS-PDF-SAMPLE/       # 10MB 미만, 5p 이하 PDF만
│   ├── DS-LLM-EVAL/
│   ├── DS-EMBED-SAMPLE/
│   └── DS-NER-EVAL/         # gold 엔티티/관계 포함
├── prompts/
├── results/                  # 비용 로그 + 테스트 결과 JSON
├── docai-output/
└── configs/
```

---

## Day 1 — Gemini API 기본 추론 + Embeddings API

### 오전: 환경 구성 (1~2시간)

```
□ SDK 설치 + ADC 인증 확인
□ Document AI 프로세서 Console 생성 완료 확인 (name 기록)
□ 데이터셋 GCS 업로드 확인
□ 비용 추적 유틸리티 (log_api_cost) 동작 확인
□ DS-NER-EVAL gold 데이터 확인 (사전 라벨링 완료 여부)
```

### TEST-C1: Gemini API 기본 추론

> **목표**: Gemini 모델별 호출 패턴 확인, 스트리밍 동작, 한국어 응답 품질 검증

```python
import google.genai as genai
from google.genai import types
import time

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")

# ── 1. 비스트리밍 호출 (기본 동작 확인) ──────────────────────────
models = ["gemini-2.5-flash", "gemini-2.5-pro"]
prompts = {
    "short_ko": "지식 그래프 임베딩 개념을 한 문장으로 요약해줘.",
    "short_en": "Summarize the concept of knowledge graph embedding in one sentence.",
    "medium_ko": open("prompts/medium_1k_ko.txt").read(),
    "medium_en": open("prompts/medium_1k_en.txt").read(),
}

for model_id in models:
    for prompt_name, prompt_text in prompts.items():
        start = time.perf_counter()
        response = client.models.generate_content(
            model=model_id,
            contents=prompt_text,
            config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=2048)
        )
        latency = (time.perf_counter() - start) * 1000

        usage = response.usage_metadata
        input_tokens = getattr(usage, "prompt_token_count", 0)
        output_tokens = getattr(usage, "candidates_token_count", 0)

        log_api_cost("test-c1", model_id, input_tokens, output_tokens, latency,
                     {"prompt_name": prompt_name, "mode": "non-streaming"})

        print(f"[{model_id}] {prompt_name}: "
              f"latency={latency:.0f}ms, "
              f"input={input_tokens}, output={output_tokens}")

# ── 2. 스트리밍 호출 (ttft 측정) ─────────────────────────────────
def measure_streaming(client, model_id: str, prompt: str, test_id: str = "test-c1"):
    ttft = None
    start = time.perf_counter()
    usage = None

    for chunk in client.models.generate_content_stream(
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=2048)
    ):
        if ttft is None and getattr(chunk, "text", None):
            ttft = (time.perf_counter() - start) * 1000
        if getattr(chunk, "usage_metadata", None) is not None:
            usage = chunk.usage_metadata

    total = (time.perf_counter() - start) * 1000

    input_tokens  = getattr(usage, "prompt_token_count", 0) if usage else 0
    output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

    log_api_cost(test_id, model_id, input_tokens, output_tokens, total,
                 {"mode": "streaming", "ttft_ms": ttft})

    return {"ttft_ms": ttft, "total_ms": total,
            "input_tokens": input_tokens, "output_tokens": output_tokens}

# ── 3. 시스템 프롬프트 + 구조화 출력 ─────────────────────────────
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="다음 이력서를 분석해서 핵심 스킬 3가지를 추출해줘: [이력서 텍스트]",
    config=types.GenerateContentConfig(
        system_instruction="당신은 채용 도메인 전문가입니다. JSON 형식으로 응답하세요.",
        temperature=0.0,
        response_mime_type="application/json",
    )
)
```

**검증 항목**:

| 항목 | 2.5 Flash | 2.5 Pro | Pass 기준 |
|------|-----------|---------|----------|
| 비스트리밍 호출 성공 | ✓/✗ | ✓/✗ | 정상 응답 |
| 스트리밍 ttft (short_ko) | ___ms | ___ms | < 2s |
| 한국어 응답 품질 (3축, 0-8) | ___ | ___ | ≥ 6 |
| JSON 구조화 출력 | ✓/✗ | ✓/✗ | 유효 JSON |
| usage_metadata 반환 | ✓/✗ | ✓/✗ | 토큰 수 확인 |
| 비용 (short 10회 기준) | $___ | $___ | 기록 (cost_log.jsonl) |

---

### TEST-C2: Embeddings API

> **목표**: 임베딩 모델 동작 확인, 한국어 임베딩 품질 비교, 배치 처리 패턴 검증
> **변경 v2**: tokens_per_char 캘리브레이션 + split-retry 로직 추가
> **변경 v2.1**: 캘리브레이션을 CountTokens API 기반으로 전환 (임베딩 응답 usage_metadata 미반환 대비).
>               split-retry를 핵심 안전장치로 격상 — 캘리브레이션은 "참고용 최적화"로 명시.

```python
import google.genai as genai
from google.genai import types

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")

# ── 0. tokens_per_char 캘리브레이션 (참고용 — 핵심 안전장치는 split-retry) ──
# ⚠ v2.1 변경: embed_content() 응답의 usage_metadata.prompt_token_count는
#   SDK/모델에 따라 반환되지 않는 경우가 흔함 → 0.6 fallback으로 굳어지는 결함.
#   CountTokens API를 사용하거나, 캘리브레이션 자체를 "참고용"으로 격하.
#
# 전략:
#   1) CountTokens API로 정확한 토큰 수 측정 (지원 시)
#   2) 실패하면 보수적 기본값 0.6 유지
#   3) 어떤 경우든 split-retry가 실제 안전장치 — 캘리브레이션은 배치 효율 최적화용

DEFAULT_TOKENS_PER_CHAR = 0.6  # 한국어 보수적 기본값
calibration_texts = load_sample_texts()[:10]

def calibrate_tokens_per_char(client, texts: list[str], model: str) -> float:
    """CountTokens API 기반 캘리브레이션. 실패 시 기본값 반환."""
    total_chars, total_tokens = 0, 0
    api_available = False

    for text in texts:
        total_chars += len(text)
        try:
            # 방법 1: CountTokens API (가장 정확)
            count_resp = client.models.count_tokens(
                model=model,
                contents=text
            )
            total_tokens += count_resp.total_tokens
            api_available = True
        except Exception:
            # CountTokens 미지원 시 기본값으로 fallback
            total_tokens += int(len(text) * DEFAULT_TOKENS_PER_CHAR)

    result = total_tokens / total_chars if total_chars > 0 else DEFAULT_TOKENS_PER_CHAR

    if api_available:
        print(f"✓ 캘리브레이션 완료 (CountTokens API): tokens_per_char = {result:.3f}")
    else:
        print(f"⚠ CountTokens API 미지원 — 기본값 유지: tokens_per_char = {result:.3f}")
        print(f"  → split-retry가 핵심 안전장치로 동작합니다.")

    return result

CALIBRATED_TOKENS_PER_CHAR = calibrate_tokens_per_char(
    client, calibration_texts, "gemini-embedding-001"
)

# ── 1. 단건 임베딩 (기본 동작 확인) ──────────────────────────────
models = ["gemini-embedding-001", "text-embedding-005"]

for model_id in models:
    start = time.perf_counter()
    resp = client.models.embed_content(
        model=model_id,
        contents="지식 그래프 임베딩은 엔티티와 관계를 벡터로 표현하는 기법입니다.",
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
    )
    latency = (time.perf_counter() - start) * 1000
    dim = len(resp.embeddings[0].values)

    log_api_cost("test-c2", model_id, 0, 0, latency,
                 {"mode": "single", "dimension": dim})
    print(f"[{model_id}] dimension={dim}, first_5={resp.embeddings[0].values[:5]}")

# ── 2. 동적 배치 (캘리브레이션 값 적용 — 참고용 최적화) ─────────────
def dynamic_batch(texts: list[str], max_texts: int = 250, max_tokens: int = 20000,
                  tokens_per_char: float = None) -> list[list[str]]:
    """토큰 기반 동적 배치.
    ⚠ 이 함수는 배치 효율 최적화용. 실제 안전장치는 embed_with_retry()의 split-retry.
    """
    tpc = tokens_per_char or CALIBRATED_TOKENS_PER_CHAR
    batches, current_batch, current_tokens = [], [], 0
    for text in texts:
        est_tokens = int(len(text) * tpc)
        if len(current_batch) >= max_texts or current_tokens + est_tokens > max_tokens:
            if current_batch:
                batches.append(current_batch)
            current_batch, current_tokens = [text], est_tokens
        else:
            current_batch.append(text)
            current_tokens += est_tokens
    if current_batch:
        batches.append(current_batch)
    return batches

# ── 3. split-retry 로직 ★ 핵심 안전장치 ★ ─────────────────────────
# 캘리브레이션이 부정확하거나 기본값(0.6)이어도, 이 함수가 토큰 초과를 자동 복구.
def embed_with_retry(client, model: str, batch: list[str],
                     config, max_splits: int = 3) -> list:
    """토큰 상한 초과 시 배치를 절반으로 쪼개 재시도.
    ★ 캘리브레이션과 무관하게 동작하는 핵심 안전장치.
    """
    from google.api_core.exceptions import InvalidArgument
    try:
        resp = client.models.embed_content(model=model, contents=batch, config=config)
        return [e.values for e in resp.embeddings]
    except InvalidArgument as e:
        if "token" in str(e).lower() and max_splits > 0 and len(batch) > 1:
            mid = len(batch) // 2
            print(f"  ⚠ 토큰 초과 — 배치 분할 ({len(batch)} → {mid} + {len(batch)-mid})")
            left  = embed_with_retry(client, model, batch[:mid], config, max_splits - 1)
            right = embed_with_retry(client, model, batch[mid:], config, max_splits - 1)
            return left + right
        raise

# ── 4. DS-EMBED-SAMPLE 배치 처리 ─────────────────────────────────
sample_texts = load_sample_texts()
batches = dynamic_batch(sample_texts)
embed_config = types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")

all_embeddings = []
for batch in batches:
    start = time.perf_counter()
    embeddings = embed_with_retry(client, "gemini-embedding-001", batch, embed_config)
    latency = (time.perf_counter() - start) * 1000
    all_embeddings.extend(embeddings)

    log_api_cost("test-c2", "gemini-embedding-001", 0, 0, latency,
                 {"mode": "batch", "batch_size": len(batch)})

# ── 5. 차원별 품질 비교 (text-embedding-005만) ────────────────────
DIM_SWEEP = [256, 768]
for dim in DIM_SWEEP:
    resp = client.models.embed_content(
        model="text-embedding-005",
        contents=sample_texts[:100],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=dim
        )
    )
    print(f"text-embedding-005 dim={dim}: OK, sample_size={len(resp.embeddings)}")

# ── 6. task_type별 동작 확인 ──────────────────────────────────────
task_types = ["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY", "SEMANTIC_SIMILARITY", "CLASSIFICATION"]
for tt in task_types:
    try:
        resp = client.models.embed_content(
            model="gemini-embedding-001",
            contents="테스트 텍스트",
            config=types.EmbedContentConfig(task_type=tt)
        )
        print(f"task_type={tt}: OK (dim={len(resp.embeddings[0].values)})")
    except Exception as e:
        print(f"task_type={tt}: FAIL ({e})")
```

**검증 항목**:

| 항목 | gemini-embedding-001 | text-embedding-005 | Pass 기준 |
|------|---------------------|-------------------|----------|
| 단건 호출 성공 | ✓/✗ | ✓/✗ | 벡터 반환 |
| 기본 차원 | ___ | ___ | 기록 |
| tokens_per_char 캘리브레이션 | ___ | N/A | 값 기록 (0.4~0.8 범위) |
| 배치 처리 성공 (250건) | ✓/✗ | ✓/✗ | 에러 없음 |
| split-retry 동작 (초과 시) | ✓/✗ | ✓/✗ | 분할 후 성공 |
| task_type 4종 지원 | ___/4 | ___/4 | 기록 |
| 한국어 코사인 유사도 정상 | ✓/✗ | ✓/✗ | 유사 문서 > 0.7 |
| dim_sweep (256/768) | N/A | ✓/✗ | 품질 비교 |

---

## Day 2 — 데이터 수집·정제 → NER 파이프라인

> **Day 2 목표**: 크롤링 결과물(PDF/HTML/이미지)을 텍스트로 변환하고, 엔티티/관계를 추출하는 **GraphRAG 데이터 파이프라인**의 각 단계를 GCP 서비스로 검증한다.
>
> ```
> 크롤링 결과물 (PDF/HTML)
>     │
>     ├─ 방법 A: Document AI → 텍스트 추출 → Gemini NER → 그래프 트리플
>     │          (정확도 높음, 2단계, 레이아웃 보존)
>     │
>     └─ 방법 B: Gemini 멀티모달 → 텍스트 추출 + NER 동시 → 그래프 트리플
>                (단순함, 1단계, PDF 직접 입력)
> ```

### ★ Day 2 오전 최우선: C5 Corpus + VAS Data Store 생성 (인덱싱 백그라운드 실행)

> Day 3에서 즉시 검색 테스트에 들어가려면, 인덱싱을 Day 2에 미리 시작해야 함.
> 아래 생성 + import 트리거 후, DOC/MMD/NER 작업을 진행하면서 백그라운드 대기.

```python
import google.genai as genai
from google.genai import types
from google.cloud import discoveryengine_v1 as discoveryengine
import datetime

# ── 재실행 방어: RUN_ID suffix (v2.1 추가) ────────────────────────
# ⚠ 리소스 이름이 고정이면 재실행 시 "Already exists" 에러.
#   timestamp suffix로 고유성 확보. 이전 실행 리소스는 삭제 체크리스트에서 정리.
RUN_ID = datetime.datetime.now().strftime("%m%d%H%M")  # e.g., "03051430"
print(f"[RUN_ID] {RUN_ID} — 모든 리소스에 suffix 적용")

# ── C5: RAG Corpus 생성 + Import 트리거 ───────────────────────────
client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")

corpus = client.corpora.create(
    display_name=f"test-c5-rag-corpus-{RUN_ID}",
    rag_embedding_model_config=types.RagEmbeddingModelConfig(
        vertex_prediction_endpoint=types.VertexPredictionEndpoint(
            model="publishers/google/models/gemini-embedding-001"
        )
    ),
    backend_config=types.RagCorpusBackendConfig(
        rag_managed_db=types.RagManagedDbConfig(tier="BASIC")
    )
)
print(f"[C5] Corpus 생성: {corpus.name}")

import_op = client.corpora.import_files(
    name=corpus.name,
    import_rag_files_config=types.ImportRagFilesConfig(
        gcs_source=types.GcsSource(
            uris=["gs://ml-api-test-vertex/datasets/DS-RAG-DOCS/"]
        ),
        rag_file_chunking_config=types.RagFileChunkingConfig(
            chunk_size=512,
            chunk_overlap=100
        ),
        max_embedding_requests_per_min=900
    )
)
print(f"[C5] Import 시작 — 백그라운드 대기. Operation: {import_op}")
# ⚠ import_op 완료 확인은 Day 3 시작 시 수행 (아래 C5 섹션 참고)

# ── VAS: GCS Data Store 생성 + 문서 Import 트리거 ─────────────────
de_client = discoveryengine.DataStoreServiceClient()
doc_client = discoveryengine.DocumentServiceClient()
parent = "projects/ml-api-test-vertex/locations/global/collections/default_collection"

unstructured_store_op = de_client.create_data_store(
    parent=parent,
    data_store_id=f"test-vas-documents-{RUN_ID}",
    data_store=discoveryengine.DataStore(
        display_name="test-vas-gcs-docs",
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
    )
)
unstructured_store = unstructured_store_op.result()
print(f"[VAS] Data Store: {unstructured_store.name}")

vas_import_op = doc_client.import_documents(
    parent=f"{unstructured_store.name}/branches/default_branch",
    request=discoveryengine.ImportDocumentsRequest(
        parent=f"{unstructured_store.name}/branches/default_branch",
        gcs_source=discoveryengine.GcsSource(
            input_uris=["gs://ml-api-test-vertex/datasets/DS-RAG-DOCS/*"]
        ),
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )
)
print(f"[VAS] 문서 Import 시작 — 백그라운드 대기.")
# VAS import도 Day 3 시작 시 확인

# ── VAS: Search Engine 생성 (Day 2에 미리 생성 — Day 3 대기 제거) ──
# ⚠ v2.1: Engine 생성이 Day 3에 남아있으면 engine_op.result() 대기 리스크.
engine_client = discoveryengine.EngineServiceClient()
engine_op = engine_client.create_engine(
    parent=parent,
    engine_id=f"test-vas-search-engine-{RUN_ID}",
    engine=discoveryengine.Engine(
        display_name="test-vas-search",
        solution_type=discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH,
        data_store_ids=[f"test-vas-documents-{RUN_ID}"],
        search_engine_config=discoveryengine.Engine.SearchEngineConfig(
            search_tier=discoveryengine.SearchTier.SEARCH_TIER_ENTERPRISE,
            search_add_ons=[discoveryengine.SearchAddOn.SEARCH_ADD_ON_LLM],
        ),
    )
)
print(f"[VAS] Search Engine 생성 시작 — 백그라운드 대기.")

print("\n★ Day 2 백그라운드 작업 시작 완료. DOC/MMD/NER 진행.")
```

---

### TEST-DOC: Document AI — PDF 텍스트 추출

> **목표**: PDF 이력서/뉴스에서 텍스트를 정확하게 추출하는지 검증. OCR, 표 파싱, 레이아웃 분석 품질 확인.
> **변경 v2**: 프로세서는 Console 사전 생성 → name만 사용. 품질 지표를 CER/WER로 변경.

```python
from google.cloud import documentai_v1 as documentai
import time, glob

project_id = "ml-api-test-vertex"
location = "us"  # ⚠ Document AI는 us / eu 멀티리전만 지원 (us-central1 아님)

docai_client = documentai.DocumentProcessorServiceClient(
    client_options={"api_endpoint": f"{location}-documentai.googleapis.com"}
)

# ── 1. 사전 생성된 프로세서 name 사용 (Console에서 생성 완료) ──────
# ⚠ API create_processor() 사용 금지 — type 문자열 불일치/권한 이슈 방지
OCR_PROCESSOR_NAME    = "projects/ml-api-test-vertex/locations/us/processors/YOUR_OCR_ID"
LAYOUT_PROCESSOR_NAME = "projects/ml-api-test-vertex/locations/us/processors/YOUR_LAYOUT_ID"

# ── 2. 단건 처리 (동기 API) ──────────────────────────────────────
def process_document(processor_name: str, file_path: str, mime_type: str = "application/pdf"):
    """로컬 PDF를 Document AI로 처리."""
    with open(file_path, "rb") as f:
        raw_document = documentai.RawDocument(content=f.read(), mime_type=mime_type)

    request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)

    start = time.perf_counter()
    result = docai_client.process_document(request=request)
    latency = (time.perf_counter() - start) * 1000

    doc = result.document
    return {
        "text": doc.text,
        "text_length": len(doc.text),
        "pages": len(doc.pages),
        "entities": [(e.type_, e.mention_text) for e in doc.entities] if doc.entities else [],
        "tables": sum(len(page.tables) for page in doc.pages),
        "latency_ms": latency
    }

# ── 3. 텍스트 추출 품질 평가 — CER / WER ─────────────────────────
# ⚠ v2 변경: 단어 set F1 → CER/WER (편집거리 기반, 위치 정보 보존)
#
# 왜 char-level F1이 아닌 CER/WER인가?
#   - char-level F1은 bag-of-characters — 위치 정보 완전 상실
#     예: gold="서울대학교" extracted="학교대서울" → F1=1.0 (완벽 점수, 실제론 엉망)
#   - CER은 편집거리(Levenshtein) 기반 — 삽입/삭제/치환을 모두 반영
#     예: gold="서울대학교" extracted="서울대학" → CER=0.20 (1글자 삭제)
#   - WER은 단어 단위 편집거리 — 한국어 띄어쓰기 변동에 민감하므로 보조 지표
#   - CER은 OCR/텍스트 추출 분야의 사실상 표준 지표 (ICDAR, Google DocAI 벤치마크 등)
import unicodedata, re

def normalize_text(text: str) -> str:
    """비교 전 정규화: 유니코드 NFC + 연속 공백 단일화 + strip."""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def levenshtein_distance(s1: list, s2: list) -> int:
    """편집거리 (삽입/삭제/치환). DP O(n*m) 구현."""
    n, m = len(s1), len(s2)
    # 메모리 최적화: 2행만 유지
    prev = list(range(m + 1))
    curr = [0] * (m + 1)
    for i in range(1, n + 1):
        curr[0] = i
        for j in range(1, m + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,      # 삭제
                curr[j - 1] + 1,  # 삽입
                prev[j - 1] + cost  # 치환
            )
        prev, curr = curr, [0] * (m + 1)
    return prev[m]

def calc_cer(extracted: str, gold: str) -> dict:
    """Character Error Rate — 문자 단위 편집거리 / gold 문자 수.
    
    CER = (Substitutions + Insertions + Deletions) / len(gold)
    - 0.0 = 완벽 일치
    - 0.05 = 5% 오류 (매우 좋음)
    - 0.10 = 10% 오류 (양호)
    - 1.0+ = gold보다 오류가 많음 (삽입 과다 시 1.0 초과 가능)
    """
    ext_chars = list(normalize_text(extracted))
    gold_chars = list(normalize_text(gold))
    
    if len(gold_chars) == 0:
        return {"cer": 0.0 if len(ext_chars) == 0 else float('inf'),
                "edit_distance": len(ext_chars), "gold_length": 0}
    
    dist = levenshtein_distance(ext_chars, gold_chars)
    cer = dist / len(gold_chars)
    return {
        "cer": round(cer, 4),
        "edit_distance": dist,
        "gold_length": len(gold_chars),
        "extracted_length": len(ext_chars),
    }

def calc_wer(extracted: str, gold: str) -> dict:
    """Word Error Rate — 단어 단위 편집거리 / gold 단어 수.
    
    ⚠ 한국어는 띄어쓰기가 불규칙하므로 CER의 보조 지표로만 사용.
    WER이 높아도 CER이 낮으면 실질 추출 품질은 양호한 것.
    """
    ext_words = normalize_text(extracted).split()
    gold_words = normalize_text(gold).split()
    
    if len(gold_words) == 0:
        return {"wer": 0.0 if len(ext_words) == 0 else float('inf'),
                "gold_words": 0}
    
    dist = levenshtein_distance(ext_words, gold_words)
    wer = dist / len(gold_words)
    return {
        "wer": round(wer, 4),
        "edit_distance": dist,
        "gold_words": len(gold_words),
        "extracted_words": len(ext_words),
    }

def evaluate_extraction_quality(extracted: str, gold: str) -> dict:
    """CER + WER 통합 평가. CER이 주 지표, WER은 보조."""
    cer_result = calc_cer(extracted, gold)
    wer_result = calc_wer(extracted, gold)
    
    # 판정 기준
    if cer_result["cer"] <= 0.05:
        grade = "EXCELLENT"
    elif cer_result["cer"] <= 0.10:
        grade = "GOOD"
    elif cer_result["cer"] <= 0.20:
        grade = "ACCEPTABLE"
    else:
        grade = "POOR"
    
    return {
        "cer": cer_result["cer"],
        "wer": wer_result["wer"],
        "grade": grade,
        "detail": {"cer": cer_result, "wer": wer_result},
    }

# ── 4. DS-PDF-SAMPLE 테스트 (20~30 PDF) ──────────────────────────
pdf_files = glob.glob("datasets/DS-PDF-SAMPLE/*.pdf")

results_ocr = []
results_layout = []

for pdf_path in pdf_files:
    filename = pdf_path.split("/")[-1]

    ocr_result = process_document(OCR_PROCESSOR_NAME, pdf_path)
    results_ocr.append({"file": filename, **ocr_result})
    log_api_cost("test-doc", "docai-ocr", 0, 0, ocr_result["latency_ms"],
                 {"file": filename, "pages": ocr_result["pages"]})

    layout_result = process_document(LAYOUT_PROCESSOR_NAME, pdf_path)
    results_layout.append({"file": filename, **layout_result})
    log_api_cost("test-doc", "docai-layout", 0, 0, layout_result["latency_ms"],
                 {"file": filename, "tables": layout_result["tables"]})

    print(f"[{filename}] OCR={ocr_result['text_length']}chars/{ocr_result['latency_ms']:.0f}ms | "
          f"Layout={layout_result['text_length']}chars/tables={layout_result['tables']}")

# ── 5. Gold 텍스트 대비 품질 평가 (사전 준비된 3~5건) ─────────────
gold_files = glob.glob("datasets/DS-PDF-SAMPLE/gold/*.txt")
for gold_path in gold_files:
    filename = gold_path.split("/")[-1].replace(".txt", ".pdf")
    gold_text = open(gold_path).read()

    # OCR 결과에서 매칭
    ocr_match = next((r for r in results_ocr if r["file"] == filename), None)
    if ocr_match:
        quality = evaluate_extraction_quality(ocr_match["text"], gold_text)
        print(f"[OCR] {filename}: CER={quality['cer']:.4f}, "
              f"WER={quality['wer']:.4f}, Grade={quality['grade']}")

    # Layout Parser 결과에서 매칭
    layout_match = next((r for r in results_layout if r["file"] == filename), None)
    if layout_match:
        quality = evaluate_extraction_quality(layout_match["text"], gold_text)
        print(f"[Layout] {filename}: CER={quality['cer']:.4f}, "
              f"WER={quality['wer']:.4f}, Grade={quality['grade']}")

# ── 6. 배치 처리 (비동기 API — 대량 문서용, LRO polling) ──────────
def batch_process_gcs(processor_name: str, gcs_input_uri: str, gcs_output_uri: str):
    """GCS PDF 배치 처리. LRO polling으로 완료 대기 (timeout 제거)."""
    request = documentai.BatchProcessRequest(
        name=processor_name,
        input_documents=documentai.BatchDocumentsInputConfig(
            gcs_prefix=documentai.GcsPrefix(gcs_uri_prefix=gcs_input_uri)
        ),
        document_output_config=documentai.DocumentOutputConfig(
            gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(
                gcs_uri=gcs_output_uri
            )
        )
    )
    operation = docai_client.batch_process_documents(request=request)
    print(f"배치 처리 LRO 시작: {operation.operation.name}")

    # ⚠ v2: timeout=600 → LRO polling으로 변경 (PDF 20~30건은 10분 초과 가능)
    while not operation.done():
        time.sleep(30)
        print(f"  배치 처리 진행 중... done={operation.done()}")
    print("배치 처리 완료")
```

**검증 항목**:

| 항목 | OCR Processor | Layout Parser | Pass 기준 |
|------|--------------|---------------|----------|
| PDF 텍스트 추출 성공 | ___/20 files | ___/20 files | ≥ 95% |
| 한국어 텍스트 추출 **CER** | ___ | ___ | **≤ 0.10** (10% 이하) |
| 한국어 텍스트 추출 **WER** (보조) | ___ | ___ | 기록 (CER 보조) |
| 표(table) 구조 인식 | N/A | ___/___건 | 표 포함 문서에서 인식 |
| 2단 레이아웃 처리 | ✓/✗ | ✓/✗ | 순서 보존 |
| 이미지 내 한국어 OCR | ✓/✗ | ✓/✗ | 읽기 가능 |
| 단건 처리 latency | ___ms | ___ms | < 5s (1페이지) |
| 배치 처리 동작 (LRO) | ✓/✗ | ✓/✗ | polling 완료 |
| 비용 (20건 기준) | $___ | $___ | 기록 (cost_log.jsonl) |

---

### TEST-MMD: Gemini 멀티모달 — PDF/이미지 직접 텍스트 추출

> **목표**: Gemini에 PDF를 직접 입력해 텍스트 추출 + 정제를 한 번에 처리하는 패턴 검증.
> **변경 v2**: PDF 크기/페이지 제한 규칙 추가. 품질 지표를 CER/WER로 통일.

```python
import google.genai as genai
from google.genai import types
import time, json, glob, os

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")

# ── 0. PDF 크기/페이지 사전 검증 ──────────────────────────────────
# ⚠ v2 추가: 10MB 초과 또는 5페이지 초과 PDF는 스킵 또는 N페이지 제한
MAX_PDF_SIZE_MB = 10
MAX_PDF_PAGES = 5  # Gemini 멀티모달 입력 시 토큰/비용 제한 감안

def validate_pdf(pdf_path: str) -> bool:
    """PDF 크기 + 페이지 수 사전 검증.
    ⚠ v2.1: 페이지 수 체크 추가 — MAX_PDF_PAGES 선언만 되어 있던 결함 수정.
    pypdf 미설치 시 크기만 체크하고 warning 출력.
    """
    import os
    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    if size_mb > MAX_PDF_SIZE_MB:
        print(f"⚠ SKIP {pdf_path}: {size_mb:.1f}MB > {MAX_PDF_SIZE_MB}MB")
        return False

    # 페이지 수 체크 (pypdf 사용)
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
        if num_pages > MAX_PDF_PAGES:
            print(f"⚠ SKIP {pdf_path}: {num_pages}p > {MAX_PDF_PAGES}p")
            return False
    except ImportError:
        print(f"⚠ WARNING: pypdf 미설치 — 페이지 수 체크 스킵. "
              f"pip install pypdf 권장")
    except Exception as e:
        print(f"⚠ WARNING: {pdf_path} 페이지 수 읽기 실패: {e}")

    return True

# ── 1. PDF 직접 입력 — 텍스트 추출 ────────────────────────────────
def extract_text_multimodal(pdf_path: str, model_id: str = "gemini-2.5-flash"):
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    start = time.perf_counter()
    response = client.models.generate_content(
        model=model_id,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            "이 PDF 문서의 전체 텍스트를 정확하게 추출해주세요. "
            "표가 있으면 마크다운 표 형식으로 변환하고, "
            "레이아웃 순서를 유지해주세요. 추가 설명 없이 원문 텍스트만 출력하세요."
        ],
        config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=8192)
    )
    latency = (time.perf_counter() - start) * 1000

    input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
    output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
    log_api_cost("test-mmd", model_id, input_tokens, output_tokens, latency,
                 {"mode": "text_extraction"})

    return {
        "text": response.text,
        "text_length": len(response.text),
        "latency_ms": latency,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }

# ── 2. PDF 입력 — 텍스트 추출 + 구조화 동시 ───────────────────────
def extract_structured_multimodal(pdf_path: str, model_id: str = "gemini-2.5-flash"):
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    STRUCTURED_SCHEMA = {
        "type": "object",
        "properties": {
            "document_type": {"type": "string", "enum": ["이력서", "뉴스기사", "보고서", "기타"]},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "section_type": {"type": "string",
                                         "enum": ["인적사항", "경력", "학력", "스킬", "자격증",
                                                  "프로젝트", "본문", "표", "기타"]}
                    },
                    "required": ["title", "content", "section_type"]
                }
            }
        }
    }

    start = time.perf_counter()
    response = client.models.generate_content(
        model=model_id,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            "이 PDF 문서를 분석하여 섹션별로 구조화해주세요."
        ],
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=STRUCTURED_SCHEMA,
            max_output_tokens=8192
        )
    )
    latency = (time.perf_counter() - start) * 1000
    log_api_cost("test-mmd", model_id,
                 getattr(response.usage_metadata, "prompt_token_count", 0),
                 getattr(response.usage_metadata, "candidates_token_count", 0),
                 latency, {"mode": "structured"})

    try:
        structured = json.loads(response.text)
        return {"structured": structured, "latency_ms": latency, "success": True}
    except json.JSONDecodeError:
        return {"raw": response.text[:500], "latency_ms": latency, "success": False}

# ── 3. DS-PDF-SAMPLE 전수 테스트 (크기 검증 후) ───────────────────
pdf_files = [f for f in glob.glob("datasets/DS-PDF-SAMPLE/*.pdf") if validate_pdf(f)]

results_mm_text = []
results_mm_struct = []

for pdf_path in pdf_files:
    filename = pdf_path.split("/")[-1]

    text_result = extract_text_multimodal(pdf_path)
    results_mm_text.append({"file": filename, **text_result})

    struct_result = extract_structured_multimodal(pdf_path)
    results_mm_struct.append({"file": filename, **struct_result})

    sections = len(struct_result.get("structured", {}).get("sections", []))
    print(f"[{filename}] Text={text_result['text_length']}chars/{text_result['latency_ms']:.0f}ms | "
          f"Struct=success={struct_result['success']},sections={sections}")

# ── 4. Gold 텍스트 대비 CER/WER 평가 (DOC 결과와 동일 gold 사용) ──
for gold_path in glob.glob("datasets/DS-PDF-SAMPLE/gold/*.txt"):
    filename = gold_path.split("/")[-1].replace(".txt", ".pdf")
    gold_text = open(gold_path).read()

    mm_match = next((r for r in results_mm_text if r["file"] == filename), None)
    if mm_match:
        quality = evaluate_extraction_quality(mm_match["text"], gold_text)
        print(f"[MMD] {filename}: CER={quality['cer']:.4f}, "
              f"WER={quality['wer']:.4f}, Grade={quality['grade']}")
```

**검증 항목**:

| 항목 | Gemini 텍스트 추출 | Gemini 구조화 추출 | Pass 기준 |
|------|------------------|------------------|----------|
| PDF 입력 성공 | ___/20 files | ___/20 files | ≥ 95% |
| 한국어 텍스트 추출 **CER** | ___ | N/A | **≤ 0.15** (15% 이하) |
| 한국어 텍스트 추출 **WER** (보조) | ___ | N/A | 기록 (CER 보조) |
| 구조화 JSON 성공률 | N/A | ___% | ≥ 90% |
| 문서 타입 분류 정확도 | N/A | ___% | ≥ 90% |
| 표 마크다운 변환 | ✓/✗ | ✓/✗ | 표 구조 유지 |
| 단건 latency | ___ms | ___ms | < 10s (1페이지) |
| 비용 (20건 기준) | $___ | $___ | 기록 (cost_log.jsonl) |

**Document AI vs Gemini 멀티모달 비교 매트릭스**:

| 비교 항목 | Document AI (OCR) | Document AI (Layout) | Gemini 멀티모달 |
|----------|-------------------|---------------------|----------------|
| 텍스트 추출 CER (↓ 낮을수록 좋음) | ___ | ___ | ___ |
| 텍스트 추출 WER (보조) | ___ | ___ | ___ |
| 표 인식 | ___ | ___ | ___ |
| 구조화 출력 | ✗ (별도 후처리) | △ (레이아웃만) | ✓ (JSON 직접) |
| 한국어 OCR | ___ | ___ | ___ |
| 단건 latency | ___ms | ___ms | ___ms |
| 비용/페이지 | $0.0015 | $0.01 | ~$___ |
| 후속 NER 연결 | 텍스트→별도 NER | 텍스트→별도 NER | 동시 처리 가능 |

---

### TEST-NER: Gemini 기반 Named Entity Recognition

> **목표**: GraphRAG 지식 그래프 구축을 위한 엔티티/관계 추출 성능 검증.
> **변경 v2**: normalize() 추가, entity-relation 정합성 체크 추가, gold 데이터 10~20건 기준.

```python
import google.genai as genai
from google.genai import types
import json, time, re, unicodedata

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")

# ── 1. 엔티티/관계 스키마 정의 (GraphRAG 도메인) ──────────────────
ENTITY_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "원문에서 추출한 엔티티 텍스트"},
                    "type": {"type": "string", "enum": [
                        "PERSON", "ORGANIZATION", "SKILL", "ROLE",
                        "EDUCATION", "LOCATION", "CERTIFICATION", "PROJECT"
                    ]},
                },
                "required": ["text", "type"]
            }
        },
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "predicate": {"type": "string", "enum": [
                        "HAS_SKILL", "WORKED_AT", "GRADUATED_FROM",
                        "HAS_ROLE", "LOCATED_IN", "CERTIFIED_BY", "WORKED_ON"
                    ]},
                    "object": {"type": "string"}
                },
                "required": ["subject", "predicate", "object"]
            }
        }
    }
}

# ── 2. 정규화 함수 (v2 추가) ─────────────────────────────────────
def normalize_entity(text: str) -> str:
    """엔티티 문자열 정규화 — exact match 왜곡 방지.
    법인 표기, 괄호, 공백, 특수문자, 대소문자를 통일.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.strip()
    # 법인 표기 제거: (주), ㈜, Inc., Corp., Ltd. 등
    text = re.sub(r'[(\(]주[)\)]|㈜|,?\s*(Inc\.?|Corp\.?|Ltd\.?|Co\.?)', '', text)
    # 괄호 내용 제거 (보조 설명)
    text = re.sub(r'\s*[(\(][^)]*[)\)]', '', text)
    # 연속 공백 → 단일 공백
    text = re.sub(r'\s+', ' ', text).strip()
    # 소문자 통일 (영문)
    text = text.lower()
    return text

# ── 3. Entity-Relation 정합성 체크 (v2 추가) ──────────────────────
def check_entity_relation_consistency(ner_result: dict) -> dict:
    """relations의 subject/object가 entities의 text에 존재하는지 검증.
    정합성이 낮으면 그래프 구축 시 노드 매칭이 깨짐.
    """
    entity_texts_raw = {e["text"] for e in ner_result.get("entities", [])}
    entity_texts_norm = {normalize_entity(e["text"]) for e in ner_result.get("entities", [])}

    relations = ner_result.get("relations", [])
    exact_match, norm_match, no_match = 0, 0, 0

    for rel in relations:
        subj, obj = rel["subject"], rel["object"]
        if subj in entity_texts_raw and obj in entity_texts_raw:
            exact_match += 1
        elif normalize_entity(subj) in entity_texts_norm and normalize_entity(obj) in entity_texts_norm:
            norm_match += 1
        else:
            no_match += 1

    total = len(relations)
    return {
        "total_relations": total,
        "exact_match": exact_match,
        "norm_match": norm_match,
        "no_match": no_match,
        "consistency_rate": (exact_match + norm_match) / total if total > 0 else 1.0,
    }

# ── 4. 프롬프트 (entity-relation 정합성 제약 추가) ────────────────
# ⚠ v2: 프롬프트에 "relations의 subject/object는 entities의 text와 동일 문자열" 제약 추가
ZERO_SHOT_PROMPT = """다음 텍스트에서 엔티티와 관계를 추출하세요.

규칙:
- 엔티티 타입: PERSON, ORGANIZATION, SKILL, ROLE, EDUCATION, LOCATION, CERTIFICATION, PROJECT
- 관계 타입: HAS_SKILL, WORKED_AT, GRADUATED_FROM, HAS_ROLE, LOCATED_IN, CERTIFIED_BY, WORKED_ON
- **중요**: relations의 subject와 object는 반드시 entities에 포함된 text와 **정확히 동일한 문자열**을 사용하세요.

텍스트:
{text}"""

FEW_SHOT_PROMPT = """다음은 텍스트에서 엔티티와 관계를 추출하는 예시입니다.

[예시 입력]
박지훈은 고려대학교 경영학과를 졸업하고 SK텔레콤에서 데이터 분석가로 근무했다.

[예시 출력]
{{"entities": [
    {{"text": "박지훈", "type": "PERSON"}},
    {{"text": "고려대학교", "type": "EDUCATION"}},
    {{"text": "경영학과", "type": "EDUCATION"}},
    {{"text": "SK텔레콤", "type": "ORGANIZATION"}},
    {{"text": "데이터 분석가", "type": "ROLE"}}
  ],
  "relations": [
    {{"subject": "박지훈", "predicate": "GRADUATED_FROM", "object": "고려대학교"}},
    {{"subject": "박지훈", "predicate": "WORKED_AT", "object": "SK텔레콤"}},
    {{"subject": "박지훈", "predicate": "HAS_ROLE", "object": "데이터 분석가"}}
  ]
}}

규칙:
- **relations의 subject/object는 entities의 text와 정확히 동일한 문자열 사용**

이제 아래 텍스트에서 동일한 방식으로 추출하세요.

텍스트:
{text}"""

# ── 5. 테스트 실행 ────────────────────────────────────────────────
test_texts_ko = [
    """김민수는 서울대학교 컴퓨터공학과를 졸업하고, 네이버에서 3년간 백엔드 개발자로 근무했다.
    주요 기술 스택은 Python, FastAPI, PostgreSQL이며, 추천 시스템 프로젝트를 리드했다.
    현재 카카오에서 시니어 ML 엔지니어로 근무 중이며, AWS Solutions Architect 자격증을 보유하고 있다.""",

    """이지은 박사는 KAIST AI대학원에서 자연어처리를 전공했으며, 삼성전자 AI센터에서
    지식 그래프 구축 프로젝트를 담당했다. Neo4j와 PyTorch를 활용한 그래프 신경망 연구 경험이 있다.
    2025년 ACL에 논문을 발표했으며, 현재 LG AI Research에서 GraphRAG 시스템을 개발하고 있다.""",

    """(주)테크스타트 AI팀은 서울 강남구에 위치하며, React와 TypeScript 기반 프론트엔드 개발자를
    채용 중이다. 3년 이상 경력자를 우대하며, Kubernetes와 Docker 운영 경험이 있으면 가산점을 부여한다.""",
]

models = ["gemini-2.5-flash", "gemini-2.5-pro"]

for model_id in models:
    print(f"\n{'='*60}")
    print(f"[{model_id}] Zero-shot NER + 정합성 체크")
    print(f"{'='*60}")

    for i, text in enumerate(test_texts_ko):
        start = time.perf_counter()
        response = client.models.generate_content(
            model=model_id,
            contents=ZERO_SHOT_PROMPT.format(text=text),
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=ENTITY_SCHEMA,
            )
        )
        latency = (time.perf_counter() - start) * 1000
        log_api_cost("test-ner", model_id,
                     getattr(response.usage_metadata, "prompt_token_count", 0),
                     getattr(response.usage_metadata, "candidates_token_count", 0),
                     latency, {"mode": "zero-shot"})

        try:
            result = json.loads(response.text)
            entities = result.get("entities", [])
            relations = result.get("relations", [])

            # v2: entity-relation 정합성 체크
            consistency = check_entity_relation_consistency(result)

            print(f"\n[ko-{i+1}] latency={latency:.0f}ms | "
                  f"entities={len(entities)}, relations={len(relations)} | "
                  f"consistency={consistency['consistency_rate']:.0%} "
                  f"(exact={consistency['exact_match']}, norm={consistency['norm_match']}, "
                  f"no_match={consistency['no_match']})")
            for e in entities:
                print(f"  Entity: {e['type']:15s} → {e['text']}")
            for r in relations:
                print(f"  Rel:    {r['subject']} --{r['predicate']}--> {r['object']}")
        except json.JSONDecodeError:
            print(f"[ko-{i+1}] JSON 파싱 실패: {response.text[:200]}")

# ── 6. 정량 평가 (DS-NER-EVAL, 10~20건, 사전 라벨링) ─────────────
def evaluate_ner(predictions, golds):
    """엔티티 단위 (normalize(text), type) 매칭으로 P/R/F1 산출.
    v2: normalize 적용으로 법인 표기/괄호/공백 변형 흡수.
    """
    tp, fp, fn = 0, 0, 0
    for pred, gold in zip(predictions, golds):
        if pred is None:
            fn += len(gold)
            continue
        pred_set = {(normalize_entity(e["text"]), e["type"]) for e in pred.get("entities", [])}
        gold_set = {(normalize_entity(e["text"]), e["type"]) for e in gold}
        tp += len(pred_set & gold_set)
        fp += len(pred_set - gold_set)
        fn += len(gold_set - pred_set)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}

def evaluate_relations(predictions, golds):
    """관계 단위 (normalize(subject), predicate, normalize(object)) 매칭으로 P/R/F1 산출.
    ⚠ v2.1 추가: 결과 표에 '관계 F1 ≥ 0.60' 기준이 있었으나 코드가 없었음.
    """
    tp, fp, fn = 0, 0, 0
    for pred, gold in zip(predictions, golds):
        if pred is None:
            fn += len(gold)
            continue
        pred_rels = {(normalize_entity(r["subject"]), r["predicate"], normalize_entity(r["object"]))
                     for r in pred.get("relations", [])}
        gold_rels = {(normalize_entity(r["subject"]), r["predicate"], normalize_entity(r["object"]))
                     for r in gold}
        tp += len(pred_rels & gold_rels)
        fp += len(pred_rels - gold_rels)
        fn += len(gold_rels - pred_rels)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
```

**검증 항목**:

| 항목 | 2.5 Flash | 2.5 Pro | Pass 기준 |
|------|-----------|---------|----------|
| JSON 구조화 출력 성공률 | ___% | ___% | ≥ 95% |
| Zero-shot 엔티티 F1 (KO, normalized) | ___ | ___ | ≥ 0.70 |
| Zero-shot 엔티티 F1 (EN, normalized) | ___ | ___ | ≥ 0.75 |
| Few-shot 엔티티 F1 (KO) | ___ | N/A | > Zero-shot |
| 관계 추출 정확도 (KO) | ___ | ___ | ≥ 0.60 |
| **Entity-Relation 정합성 (consistency_rate)** | ___% | ___% | **≥ 90%** |
| 처리량 (docs/sec, Flash) | ___ | N/A | ≥ 1 doc/s |
| 단건 latency (KO, short) | ___ms | ___ms | < 3s |

---

### TEST-E2E: 정제 → NER 파이프라인 비교 (방법 A vs 방법 B)

> **목표**: PDF → 그래프 트리플까지의 E2E 파이프라인을 2가지 방법으로 실행하고 품질·비용·속도를 비교.
> (코드는 v1과 동일하되, process_document는 사전 생성 프로세서 사용, NER은 normalize + 정합성 체크 포함)

```python
# ── 방법 A: Document AI → 별도 Gemini NER (2단계) ─────────────────
def pipeline_a(pdf_path: str) -> dict:
    start = time.perf_counter()
    docai_result = process_document(OCR_PROCESSOR_NAME, pdf_path)
    extracted_text = docai_result["text"]

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=ZERO_SHOT_PROMPT.format(text=extracted_text),
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=ENTITY_SCHEMA,
        )
    )
    total_ms = (time.perf_counter() - start) * 1000
    log_api_cost("test-e2e", "pipeline-a", 0, 0, total_ms)

    try:
        ner_result = json.loads(response.text)
    except json.JSONDecodeError:
        ner_result = {"entities": [], "relations": []}

    consistency = check_entity_relation_consistency(ner_result)

    return {
        "method": "A (DocAI→NER)",
        "total_ms": total_ms,
        "text_length": len(extracted_text),
        "entities": len(ner_result.get("entities", [])),
        "relations": len(ner_result.get("relations", [])),
        "consistency_rate": consistency["consistency_rate"],
        "ner_result": ner_result,
    }

# ── 방법 B: Gemini 멀티모달 PDF → NER 동시 (1단계) ───────────────
def pipeline_b(pdf_path: str) -> dict:
    if not validate_pdf(pdf_path):
        return {"method": "B", "error": "PDF size/page limit exceeded"}

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    start = time.perf_counter()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            "이 PDF 문서에서 엔티티(PERSON, ORGANIZATION, SKILL, ROLE, EDUCATION, "
            "LOCATION, CERTIFICATION, PROJECT)와 엔티티 간 관계(HAS_SKILL, WORKED_AT, "
            "GRADUATED_FROM, HAS_ROLE, LOCATED_IN, CERTIFIED_BY, WORKED_ON)를 추출하세요. "
            "**relations의 subject/object는 entities의 text와 정확히 동일한 문자열을 사용하세요.**"
        ],
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=ENTITY_SCHEMA,
            max_output_tokens=8192
        )
    )
    total_ms = (time.perf_counter() - start) * 1000
    log_api_cost("test-e2e", "pipeline-b", 0, 0, total_ms)

    try:
        ner_result = json.loads(response.text)
    except json.JSONDecodeError:
        ner_result = {"entities": [], "relations": []}

    consistency = check_entity_relation_consistency(ner_result)

    return {
        "method": "B (Multimodal→NER)",
        "total_ms": total_ms,
        "entities": len(ner_result.get("entities", [])),
        "relations": len(ner_result.get("relations", [])),
        "consistency_rate": consistency["consistency_rate"],
        "ner_result": ner_result,
    }

# ── 비교 실행 (상위 10개) ────────────────────────────────────────
comparison = []
for pdf_path in pdf_files[:10]:
    filename = pdf_path.split("/")[-1]
    result_a = pipeline_a(pdf_path)
    result_b = pipeline_b(pdf_path)

    print(f"\n[{filename}]")
    print(f"  A: {result_a['total_ms']:.0f}ms, ent={result_a['entities']}, "
          f"rel={result_a['relations']}, consistency={result_a['consistency_rate']:.0%}")
    print(f"  B: {result_b['total_ms']:.0f}ms, ent={result_b['entities']}, "
          f"rel={result_b['relations']}, consistency={result_b.get('consistency_rate', 'N/A')}")

    comparison.append({"file": filename, "pipeline_a": result_a, "pipeline_b": result_b})
```

**E2E 파이프라인 비교 결과**:

| 비교 항목 | 방법 A (DocAI → NER) | 방법 B (멀티모달 NER) | 판단 |
|----------|---------------------|---------------------|------|
| E2E latency (평균) | ___ms | ___ms | ___ |
| 엔티티 추출 수 (평균) | ___ | ___ | ___ |
| 관계 추출 수 (평균) | ___ | ___ | ___ |
| **Entity-Relation 정합성** | ___% | ___% | **≥ 90%** |
| NER 정확도 (gold 대비) | ___ | ___ | ___ |
| 표/이미지 처리 | ✓ (DocAI 강점) | △ | ___ |
| 비용/문서 | $___ | $___ | ___ |
| 구현 복잡도 | 2단계 (SDK 2개) | 1단계 (SDK 1개) | ___ |
| 대량 처리 적합성 | ✓ (배치 API) | △ (순차 호출) | ___ |

---

## Day 3 — 검색·생성 + Vertex AI Search + 운영 기능 + 결과 정리

### Day 3 시작: 백그라운드 작업 완료 확인

```python
import time

# ── C5 import 완료 확인 (폴링 + 플랜B) ────────────────────────────
# ⚠ v2.1 변경: .result(timeout=600)은 500 docs 인제스트 시 초과 가능.
#   폴링 루프 + 최대 대기 + 미완료 시 범위 축소 플랜B.
MAX_WAIT_MINUTES = 30  # 최대 30분 대기 (Day 2에 이미 시작했으므로 보통 충분)
POLL_INTERVAL_SEC = 60

print("[C5] Import 완료 확인 중...")
waited = 0
c5_import_ready = False
while waited < MAX_WAIT_MINUTES * 60:
    if import_op.done():
        import_result = import_op.result()
        print(f"[C5] Import 완료 ✓ (대기 {waited//60}분)")
        c5_import_ready = True
        break
    print(f"  ... 대기 중 ({waited//60}/{MAX_WAIT_MINUTES}분)")
    time.sleep(POLL_INTERVAL_SEC)
    waited += POLL_INTERVAL_SEC

if not c5_import_ready:
    print(f"⚠ [C5] {MAX_WAIT_MINUTES}분 내 미완료 — 플랜B 적용:")
    print(f"  → RAG 검색 테스트를 Day 3 후반으로 지연")
    print(f"  → 미완료 시 C5는 인제스트 성능 기록만, 검색 테스트는 후속으로 이월")

# ── VAS import 완료 확인 (동일 패턴) ──────────────────────────────
print("[VAS] 문서 Import 완료 확인 중...")
waited = 0
vas_import_ready = False
while waited < MAX_WAIT_MINUTES * 60:
    if vas_import_op.done():
        vas_import_result = vas_import_op.result()
        print(f"[VAS] Import 완료 ✓ (대기 {waited//60}분)")
        vas_import_ready = True
        break
    print(f"  ... 대기 중 ({waited//60}/{MAX_WAIT_MINUTES}분)")
    time.sleep(POLL_INTERVAL_SEC)
    waited += POLL_INTERVAL_SEC

if not vas_import_ready:
    print(f"⚠ [VAS] {MAX_WAIT_MINUTES}분 내 미완료 — VAS 검색 테스트는 후속으로 이월")

# ── VAS Engine 준비 확인 (Day 2에서 생성 시작) ────────────────────
print("[VAS] Engine 준비 확인 중...")
try:
    engine = engine_op.result(timeout=300)  # Engine 생성은 보통 수 분
    print(f"[VAS] Engine 준비 완료 ✓: {engine.name}")
except Exception as e:
    print(f"⚠ [VAS] Engine 준비 실패: {e} — VAS 검색 테스트 스킵")
```

### TEST-C5: RAG Engine — 문서 검색 + 생성

> **변경 v2**: import 완료 대기 명시, Unprovisioned 순서 고정

```python
# ── 1. 검색 (Retrieval) 테스트 ────────────────────────────────────
ko_queries = [
    "Python과 머신러닝 경험이 있는 백엔드 개발자를 찾아줘",
    "데이터 엔지니어링과 클라우드 인프라 경험자",
    "NLP 및 자연어처리 관련 연구 경험이 있는 후보자",
    "스타트업 경험이 풍부한 프로덕트 매니저",
    "그래프 데이터베이스 및 지식 그래프 전문가",
]

for query in ko_queries:
    start = time.perf_counter()
    results = client.corpora.retrieve(
        name=corpus.name,
        query=query,
        config=types.RetrieveConfig(top_k=5)
    )
    latency = (time.perf_counter() - start) * 1000
    log_api_cost("test-c5", "rag-retrieval", 0, 0, latency,
                 {"query": query[:30], "chunks": len(results.relevant_chunks)})

    print(f"Query: {query[:30]}... → {len(results.relevant_chunks)} chunks ({latency:.0f}ms)")
    for i, chunk in enumerate(results.relevant_chunks[:3]):
        print(f"  [{i+1}] score={chunk.chunk_relevance_score:.3f} | "
              f"{chunk.chunk.document_metadata.display_name}")

# ── 2. RAG + 생성 ────────────────────────────────────────────────
rag_queries = [
    "Python 백엔드 개발 경험이 있는 후보자 3명을 추천하고 각각의 강점을 설명해줘.",
    "데이터 엔지니어 포지션에 적합한 후보자를 찾아서 이력서 요약을 작성해줘.",
    "그래프 데이터베이스 전문가를 찾아 기술 스택과 경험을 정리해줘.",
    "NLP 연구 경험이 있는 후보자의 논문/프로젝트 이력을 요약해줘.",
    "클라우드 인프라 경험이 풍부한 DevOps 엔지니어를 추천해줘.",
]

rag_responses = []
for query in rag_queries:
    start = time.perf_counter()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=query,
        config=types.GenerateContentConfig(
            tools=[types.Tool(
                retrieval=types.Retrieval(
                    vertex_rag_store=types.VertexRagStore(
                        rag_corpora=[corpus.name],
                        similarity_top_k=5
                    )
                )
            )],
            temperature=0.2
        )
    )
    latency = (time.perf_counter() - start) * 1000
    log_api_cost("test-c5", "gemini-2.5-flash",
                 getattr(response.usage_metadata, "prompt_token_count", 0),
                 getattr(response.usage_metadata, "candidates_token_count", 0),
                 latency, {"mode": "rag-generate"})

    rag_responses.append({"query": query, "response": response.text, "latency_ms": latency})
    print(f"\nQuery: {query[:40]}...")
    print(f"Response ({latency:.0f}ms): {response.text[:200]}...")
```

**검증 항목**:

| 항목 | 결과 | Pass 기준 |
|------|------|----------|
| Corpus 생성 | ✓/✗ | 정상 생성 |
| 문서 인제스트 (200~500 docs) | ___건 성공 | 에러율 < 5% |
| 인제스트 소요 시간 | ___분 | 기록 |
| **import 완료 대기 후 검색** | ✓/✗ | **import_op.result() 성공** |
| 한국어 검색 — 관련 문서 반환 | ✓/✗ | top-5에 관련 문서 포함 |
| 한국어 검색 **hit@5** (수동 판정) | ___/5 queries | ≥ 3/5 (관련 문서 1건 이상 포함) |
| 한국어 검색 relevance score 분포 | min=___, median=___, max=___ | 기록 (모델/코퍼스에 따라 분포 다름 — 절대 임계값 부적합) |
| RAG 생성 — 한국어 품질 (3축) | ___/8 | ≥ 6 |
| RAG 생성 — 소스 문서 인용 | ✓/✗ | grounding_metadata 존재 |
| RAG vs Base 정확도 차이 | +___% | RAG > Base |
| Corpus 삭제 | ✓/✗ | 정상 삭제 |

---

### TEST-VAS: Vertex AI Search — GCS 문서 검색 (+ 웹 크롤링 옵션)

> **변경 v2**: 웹 크롤링은 옵션. GCS Unstructured Data Store 기반 검색만 필수.
> C5와의 공정 비교를 위해 동일 쿼리 5개로 양쪽 생성 결과를 3축 평가.

```python
from google.cloud import discoveryengine_v1 as discoveryengine

# Data Store + Engine은 Day 2에 생성 완료 (engine_op은 Day 2 변수)
search_client = discoveryengine.SearchServiceClient()

# ── 1. Engine 완료 확인 (Day 2에서 생성 시작) ─────────────────────
print("[VAS] Engine 준비 확인 중...")
engine = engine_op.result()  # Day 2에서 이미 시작 — 보통 즉시 반환
print(f"[VAS] Engine 준비 완료: {engine.name}")

# ── 2. 검색 실행 (C5와 동일 쿼리) ────────────────────────────────
serving_config = f"{engine.name}/servingConfigs/default_search"

# C5와 동일 5개 쿼리로 공정 비교
shared_queries = [
    "Python과 머신러닝 경험이 있는 백엔드 개발자를 찾아줘",
    "데이터 엔지니어링과 클라우드 인프라 경험자",
    "NLP 및 자연어처리 관련 연구 경험이 있는 후보자",
    "스타트업 경험이 풍부한 프로덕트 매니저",
    "그래프 데이터베이스 및 지식 그래프 전문가",
]

vas_responses = []
for query in shared_queries:
    start = time.perf_counter()
    response = search_client.search(
        request=discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=5,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True
                ),
                summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                    summary_result_count=3,
                    include_citations=True,
                    language_code="ko",
                ),
            ),
        )
    )
    latency = (time.perf_counter() - start) * 1000
    log_api_cost("test-vas", "discovery-engine", 0, 0, latency, {"query": query[:30]})

    summary_text = response.summary.summary_text if response.summary else ""
    vas_responses.append({"query": query, "summary": summary_text, "latency_ms": latency,
                          "total_results": response.total_size})

    print(f"\nQuery: {query}")
    print(f"  Results: {response.total_size}, Latency: {latency:.0f}ms")
    if summary_text:
        print(f"  Summary: {summary_text[:200]}")

# ── 3. C5 vs VAS 공정 비교 (동일 쿼리 5개, 3축 평가) ─────────────
print("\n" + "="*70)
print("C5 RAG Engine vs VAS 비교 (동일 쿼리 5개)")
print("="*70)
for i, query in enumerate(shared_queries):
    rag_resp = rag_responses[i] if i < len(rag_responses) else {"response": "N/A"}
    vas_resp = vas_responses[i] if i < len(vas_responses) else {"summary": "N/A"}
    print(f"\n[Query {i+1}] {query[:40]}...")
    print(f"  RAG: {rag_resp['response'][:150]}...")
    print(f"  VAS: {vas_resp['summary'][:150]}...")
    print(f"  → 3축 수동 평가: RAG=___/8, VAS=___/8")

# ── 4. (옵션) Website Data Store — 시간 남으면 ────────────────────
# ⚠ v2: 웹 크롤링은 3일 내 완료 불확실 → 옵션 처리
# Website Data Store는 설정/검증/인덱싱에 수시간~1일 소요 가능
# 아래는 생성 가능 여부만 확인하고, 검색 품질 비교는 후속 테스트로

# OPTIONAL:
# website_store_op = de_client.create_data_store(
#     parent=parent,
#     data_store_id="test-vas-website",
#     data_store=discoveryengine.DataStore(
#         display_name="test-vas-website-crawl",
#         industry_vertical=discoveryengine.IndustryVertical.GENERIC,
#         content_config=discoveryengine.DataStore.ContentConfig.PUBLIC_WEBSITE,
#     )
# )
# print(f"[옵션] Website Data Store 생성: {website_store_op.result().name}")
# print("⚠ Console에서 Site URL 설정 후 인덱싱 완료 대기 필요 — 후속 테스트")
```

**검증 항목 (필수: GCS 기반)**:

| 항목 | GCS 문서 | Pass 기준 |
|------|---------|----------|
| Data Store 생성 | ✓/✗ | 정상 생성 |
| 문서 인덱싱 | ___건 | 에러 없음 |
| 인덱싱 소요 시간 | ___분 | 기록 |
| 한국어 검색 결과 품질 | ✓/✗ | 관련 문서 반환 |
| AI 요약 (한국어) | ✓/✗ | 한국어 요약 생성 |
| 인용(citation) | ✓/✗ | 출처 포함 |
| 검색 latency | ___ms | < 2s |

**검증 항목 (옵션: 웹 크롤링)**:

| 항목 | Website (크롤링) | Pass 기준 |
|------|-----------------|----------|
| Data Store 생성 | ✓/✗ | 생성 가능 여부만 확인 |
| 크롤링 시작 | ✓/✗ | 기록 (완료는 후속) |

**C5 RAG Engine vs VAS 비교 매트릭스 (동일 쿼리 5개 기준)**:

| 비교 항목 | RAG Engine (C5) | Vertex AI Search (VAS) |
|----------|----------------|----------------------|
| 데이터 소스 | GCS 파일 업로드 | GCS + **(옵션) 웹 크롤링** |
| 임베딩 제어 | 모델 직접 선택 | 내장 (자동) |
| 검색 품질 (3축) | ___/8 | ___/8 |
| AI 생성/요약 품질 (3축) | ___/8 | ___/8 |
| chunk 제어 | chunk_size 직접 설정 | 자동 |
| 비용 모델 | Spanner + Embedding API | Enterprise 검색 단가 |
| 크롤링 지원 | ✗ (별도 구축) | **✓ (내장, 옵션)** |
| GraphRAG 적합성 | 커스텀 가능 | 매니지드 한정 |

---

### TEST-C6: Grounding with Google Search

```python
import time

# Grounding ON
start = time.perf_counter()
response_grounded = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="2026년 최신 그래프 신경망 연구 동향을 알려줘.",
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
)
latency_on = (time.perf_counter() - start) * 1000
log_api_cost("test-c6", "gemini-2.5-flash",
             getattr(response_grounded.usage_metadata, "prompt_token_count", 0),
             getattr(response_grounded.usage_metadata, "candidates_token_count", 0),
             latency_on, {"mode": "grounding-on"})
print(f"[C6] Grounding ON: {latency_on:.0f}ms")

# Grounding OFF (동일 질문)
start = time.perf_counter()
response_base = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="2026년 최신 그래프 신경망 연구 동향을 알려줘.",
    config=types.GenerateContentConfig(temperature=0.0)
)
latency_off = (time.perf_counter() - start) * 1000
log_api_cost("test-c6", "gemini-2.5-flash",
             getattr(response_base.usage_metadata, "prompt_token_count", 0),
             getattr(response_base.usage_metadata, "candidates_token_count", 0),
             latency_off, {"mode": "grounding-off"})
print(f"[C6] Grounding OFF: {latency_off:.0f}ms")

# 한국어 도메인 질문
domain_queries = [
    "2026년 한국 AI 채용 시장 동향은?",
    "최근 GraphRAG 관련 논문이나 프로젝트를 알려줘.",
]
for query in domain_queries:
    start = time.perf_counter()
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=query,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    lat = (time.perf_counter() - start) * 1000
    log_api_cost("test-c6", "gemini-2.5-flash",
                 getattr(resp.usage_metadata, "prompt_token_count", 0),
                 getattr(resp.usage_metadata, "candidates_token_count", 0),
                 lat, {"mode": "grounding-domain", "query": query[:30]})
    print(f"[C6] Domain '{query[:30]}...': {lat:.0f}ms")
```

**검증 항목**:

| 항목 | Grounding ON | Grounding OFF | Pass 기준 |
|------|-------------|---------------|----------|
| 호출 성공 | ✓/✗ | ✓/✗ | 정상 응답 |
| 최신 정보 포함 (2026) | ✓/✗ | ✓/✗ | ON에서 최신 정보 반영 |
| 한국어 품질 (3축) | ___/8 | ___/8 | ≥ 6 |
| 검색 소스 메타데이터 | ✓/✗ | N/A | 출처 URL 포함 |
| 비용/쿼리 | ~$0.035+토큰 | 토큰만 | 기록 (cost_log.jsonl) |

---

### TEST-C10: Prompt Caching

> **변경 v2**: contents 필드 병행 설정, 재전달 금지 규칙 명시, 캐시 생성 성공 사전 체크

```python
import time

SYSTEM_PROMPT = open("prompts/graphrag_system_5k.txt").read()  # ~5K tokens

# ── 캐시 생성 ─────────────────────────────────────────────────────
# ⚠ v2: contents를 최소 1개 포함 — system_instruction만으로는 최소 토큰 요건 미충족 가능
cache = client.caches.create(
    model="gemini-2.5-flash",
    config=types.CreateCachedContentConfig(
        contents=[{"role": "user", "parts": [{"text": SYSTEM_PROMPT}]}],
        system_instruction="GraphRAG 전문가로서 이력서와 기업 정보를 분석합니다.",
        ttl="3600s",
        display_name="test-c10-graphrag-cache"
    )
)
print(f"캐시 생성 성공: {cache.name}")

# ⚠ 캐시 생성 실패 시 → 에러 기록하고 C10 스킵 (3일 플랜에서 블로커 아님)

# ⚠ v2 금지 규칙: cached_content 사용 시 아래 파라미터 재전달 금지
# - system_instruction: 캐시에 이미 포함됨 → generate 요청에서 재전달하면 INVALID_ARGUMENT
# - tools / tool_config: 캐시에 포함된 경우 동일 제약
# → 향후 tools/retrieval과 결합 시 캐시 생성 단계에서 tools도 포함해야 함

queries = [f"후보자 {i}번의 경력과 기업 A의 요구사항을 매칭해줘." for i in range(20)]

# 캐시 ON (20회)
latencies_cached = []
for query in queries:
    start = time.perf_counter()
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=query,
        config=types.GenerateContentConfig(
            cached_content=cache.name,
            max_output_tokens=512
            # ⚠ system_instruction 재전달 금지!
        )
    )
    lat = (time.perf_counter() - start) * 1000
    latencies_cached.append(lat)
    log_api_cost("test-c10-cached", "gemini-2.5-flash",
                 getattr(resp.usage_metadata, "prompt_token_count", 0),
                 getattr(resp.usage_metadata, "candidates_token_count", 0),
                 lat)

# 캐시 OFF — 순서 효과 제거를 위해 OFF를 먼저 실행하거나 interleave 권장
# (여기서는 간이 테스트이므로 순차 실행, 결과 해석 시 warm-up 효과 감안)
latencies_uncached = []
for query in queries:
    start = time.perf_counter()
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{SYSTEM_PROMPT}\n\n{query}",
        config=types.GenerateContentConfig(max_output_tokens=512)
    )
    lat = (time.perf_counter() - start) * 1000
    latencies_uncached.append(lat)
    log_api_cost("test-c10-uncached", "gemini-2.5-flash",
                 getattr(resp.usage_metadata, "prompt_token_count", 0),
                 getattr(resp.usage_metadata, "candidates_token_count", 0),
                 lat)

# 캐시 삭제
client.caches.delete(name=cache.name)
```

**검증 항목**:

| 항목 | 캐시 ON | 캐시 OFF | Pass 기준 |
|------|--------|--------|----------|
| 캐시 생성/삭제 | ✓/✗ | N/A | 정상 동작 |
| 평균 latency (20회) | ___ms | ___ms | 기록 |
| cached_content_token_count 반환 | ✓/✗ | N/A | 캐시 적용 확인 |
| 응답 품질 차이 | ___/8 | ___/8 | 동등 (±0.5) |
| 비용 절감 효과 (추정) | ___% | — | ≥ 30% |

---

### TEST-X1: API 에러 핸들링

> **변경 v2**: Rate Limit은 "도달 시 확인, 미도달 시 기록". Safety는 파라미터 수용+메타데이터 존재 확인.

```python
# 시나리오 1: 존재하지 않는 모델
try:
    client.models.generate_content(model="gemini-nonexistent", contents="test")
except Exception as e:
    print(f"[잘못된 모델] {type(e).__name__}: {e}")

# 시나리오 2: 빈 입력
try:
    client.models.generate_content(model="gemini-2.5-flash", contents="")
except Exception as e:
    print(f"[빈 입력] {type(e).__name__}: {e}")

# 시나리오 3: max_output_tokens 초과 설정
try:
    client.models.generate_content(
        model="gemini-2.5-flash", contents="test",
        config=types.GenerateContentConfig(max_output_tokens=999999)
    )
except Exception as e:
    print(f"[토큰 초과] {type(e).__name__}: {e}")

# 시나리오 4: 임베딩 배치 크기 초과
try:
    client.models.embed_content(
        model="gemini-embedding-001", contents=["text"] * 300,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
    )
except Exception as e:
    print(f"[배치 초과] {type(e).__name__}: {e}")

# 시나리오 5: Rate Limit 확인
# ⚠ v2: 기본 quota에서 429가 안 나올 수 있음 → "도달 시 확인, 미도달 시 기록"
errors = []
for i in range(30):
    try:
        client.models.generate_content(
            model="gemini-2.5-flash", contents=f"Quick test {i}",
            config=types.GenerateContentConfig(max_output_tokens=10)
        )
    except Exception as e:
        errors.append((i, type(e).__name__, str(e)[:100]))
if errors:
    print(f"30회 연속 호출: {len(errors)} errors — Retry-After 헤더 확인")
    for idx, etype, emsg in errors[:3]:
        print(f"  [{idx}] {etype}: {emsg}")
else:
    print("30회 연속 호출: 429 미도달 (quota 충분) — '도달 못함' 기록")

# 시나리오 6: Safety filter — 차단 유발 목적 아님, 파라미터 수용 + 메타데이터 확인
# ⚠ v2: 무해한 문장으로 차단이 안 나는 건 정상. safety_settings 수용 여부만 확인.
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="이것은 안전 필터 테스트 프롬프트입니다.",
    config=types.GenerateContentConfig(
        safety_settings=[types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold="BLOCK_LOW_AND_ABOVE"
        )]
    )
)
has_safety_meta = hasattr(response, "candidates") and response.candidates
print(f"[Safety] safety_settings 파라미터 수용: ✓")
print(f"[Safety] 응답에 safety 메타데이터 포함: {'✓' if has_safety_meta else '✗'}")
```

**검증 항목**:

| 시나리오 | 기대 동작 | 실제 결과 | Pass 기준 |
|---------|----------|----------|----------|
| 잘못된 모델 ID | 404 / NotFound | ___ | 명확한 에러 |
| 빈 입력 | 400 / InvalidArgument | ___ | 명확한 에러 |
| 토큰 초과 | 400 / InvalidArgument | ___ | 명확한 에러 |
| 임베딩 배치 초과 | 400 / InvalidArgument | ___ | 명확한 에러 |
| Rate Limit | **429 발생 시**: Retry-After 확인. **미발생 시**: "도달 못함" 기록 | ___ | 동작 확인 또는 관찰치 |
| Safety filter | **파라미터 수용 + 메타데이터 존재** 확인 (차단 유발 목적 아님) | ___ | 파라미터 정상 수용 |

---

### 결과 종합 및 정리 (Day 3 마무리)

```python
# cost_log.jsonl 기반 비용 집계
summarize_costs()
```

#### 기능 검증 결과 매트릭스

| 테스트 | 핵심 결과 | 한국어 품질 | 비용 | 판단 |
|--------|---------|-----------|------|------|
| C1: Gemini API | 스트리밍/비스트리밍 동작, ttft=___ms | ___/8 | $___ | ○/△/× |
| C2: Embeddings | dim=___, 배치 OK, task_type ___/4 | 유사도=___ | $___ | ○/△/× |
| DOC: Document AI | OCR CER=___, Layout 표 인식 | 추출 CER=___ | $___ | ○/△/× |
| MMD: Gemini 멀티모달 | PDF 직접 추출 CER=___, 구조화 ___% | ___/8 | $___ | ○/△/× |
| NER: 엔티티/관계 추출 | 엔티티 F1=___, 관계 F1=___, **정합성=___%** | ___/8 | $___ | ○/△/× |
| E2E: 파이프라인 비교 | 방법 A vs B latency/품질/**정합성** | N/A | $___ | ○/△/× |
| C5: RAG Engine | 인제스트 ___건, recall OK | ___/8 | $___ | ○/△/× |
| VAS: Vertex AI Search | GCS 인덱싱, AI 요약 | ___/8 | $___ | ○/△/× |
| C6: Grounding | 최신 정보 반영 | ___/8 | $___ | ○/△/× |
| C10: Caching | 절감=___% | ___/8 | $___ | ○/△/× |
| X1: 에러 핸들링 | ___/6 시나리오 확인 | N/A | — | ○/△/× |

#### GraphRAG 구축 의사결정 포인트

| 의사결정 | 테스트 근거 | 결론 |
|---------|-----------|------|
| **데이터 수집 방식** | VAS 크롤링(옵션) vs 자체 크롤러 | ___ |
| **PDF 정제 파이프라인** | DOC(방법A) vs MMD(방법B) 비교 | ___ |
| **NER 모델** (Flash vs Pro) | NER F1 + 정합성 차이, 비용 비교 | ___ |
| **NER 프롬프트 전략** | zero-shot vs few-shot F1 | ___ |
| **관계 추출 → 그래프 구축** | 관계 F1 ≥ 0.60 + **entity-relation 정합성 ≥ 90%** | ___ |
| **임베딩 모델 선택** | C2 품질 비교 | ___ |
| **임베딩 차원** | C2 dim_sweep | ___ |
| **RAG 서비스** | RAG Engine vs VAS (**동일 쿼리 3축 비교**) | ___ |
| **RAG 검색 품질 충분성** | C5 recall, 생성 품질 | ___ |
| **Grounding 추가 적용 여부** | C6 정확도 향상폭 | ___ |
| **Prompt Caching 적용** | C10 비용 절감 ≥ 30% | ___ |
| **기본 LLM 모델** (Flash vs Pro) | C1 품질/비용 비교 | ___ |

#### GraphRAG 최종 파이프라인 후보

```
후보 1: 매니지드 파이프라인
  Vertex AI Search(크롤링+검색) → Gemini(생성) + Grounding(실시간)
  장점: 운영 부담 최소 / 단점: 커스텀 제한

후보 2: 하이브리드 파이프라인
  자체 크롤링 → Document AI(정제) → Gemini NER(그래프) → RAG Engine(검색)
  장점: 그래프 품질 통제 / 단점: 구현 복잡

후보 3: Gemini 올인원 파이프라인
  자체 크롤링 → Gemini 멀티모달(정제+NER 동시) → RAG Engine(검색)
  장점: 단순 / 단점: Gemini 의존도 높음

→ 테스트 결과 기반 선택: ___
```

#### 리소스 삭제 체크리스트

```
⚠ 모든 리소스에 RUN_ID suffix가 붙어있음 — 현재 실행의 RUN_ID 확인 후 삭제.
  이전 실행 잔여 리소스도 함께 정리할 것.

□ RAG Corpus 삭제 완료 (client.corpora.delete)
  - display_name: test-c5-rag-corpus-{RUN_ID}
□ RagEngineConfig → Unprovisioned tier 확인
  ⚠ Corpus 삭제 후 마지막에 실행 — Unprovisioned는 복구 불가
  ⚠ Corpus 삭제만으로는 Spanner billing이 멈추지 않을 수 있음
□ Prompt Cache 삭제 완료
□ Document AI 프로세서 삭제 (Console)
□ Vertex AI Search 삭제:
  - Engine: test-vas-search-engine-{RUN_ID}
  - Data Store: test-vas-documents-{RUN_ID}
□ GCS 임시 파일 정리 (docai-output 등)
□ 48시간 내 Billing 잔여 비용 확인 + summarize_costs() 추정치와 대조
```

---

## 비용 예산

| 항목 | 추정 비용 |
|------|----------|
| Gemini API 호출 (C1, 영어+한국어) | $20~$50 |
| Embeddings API (C2, 1K~5K docs) | $5~$15 |
| Document AI (DOC, 20~30 PDF, OCR+Layout) | $1~$5 |
| Gemini 멀티모달 PDF 입력 (MMD, 20~30건) | $10~$25 |
| NER 엔티티/관계 추출 (10~20건 × 2모델) | $10~$25 |
| E2E 파이프라인 비교 (10건 × 2방법) | $5~$10 |
| RAG Engine Spanner BASIC (C5, 수 시간) | $10~$30 |
| Vertex AI Search (VAS, Enterprise tier) | $10~$30 |
| Grounding (C6, ~20 쿼리) | $5~$10 |
| Prompt Caching (C10, 40회 호출) | $5~$10 |
| GCS, 기타 | $5~$10 |
| **합계** | **$86~$220** |

Budget Alert: $500 (충분한 여유)

---

## 후속 테스트 (별도 일정)

| 우선순위 | 항목 | 시기 |
|---------|------|------|
| 1 | C5 chunk_size 비교 (256/512/1024) | 기능 테스트 결과 확정 후 |
| 2 | VAS Website 크롤링 품질 평가 | 데이터 수집 전략 확정 시 |
| 3 | Document AI Custom Extractor 학습 | 이력서 도메인 특화 필요 시 |
| 4 | C3/C4 SFT/LoRA Fine-Tuning | NER/생성 한국어 품질 개선 필요 시 |
| 5 | 성능·부하 테스트 (QPS, 동시성) | 서비스 아키텍처 확정 후 |
| 6 | KR latency (asia-northeast3 probe) | 서비스 리전 결정 시 |
| 7 | Part A/B (ML, DL 인프라) | ML Pipeline 구축 시 |
| 8 | 텍스트 추출 CER/WER 정밀 평가 | gold 데이터 충분 확보 후 |

---

## Appendix: v2 변경 사항 추적

| # | 변경 | 출처 | 반영 위치 |
|---|------|------|----------|
| 1 | Day 3 과부하 → Day 2에 C5/VAS 사전 트리거 | 자체 리뷰 | Day 2 오전, Day 3 시작 |
| 2 | VAS 웹 크롤링 옵션화 | 자체+외부 리뷰 | VAS 섹션 |
| 3 | RAG import 완료 대기 명시 | 자체+외부 리뷰 | Day 3 시작, C5 |
| 4 | NER gold 준비 일정 명시 | 자체 리뷰 | 사전 준비 체크리스트 |
| 5 | NER entity-relation 정합성 체크 | 자체 리뷰 | NER, E2E |
| 6 | NER normalize 추가 | 외부 리뷰 #4 | NER |
| 7 | DocAI 프로세서 사전 Console 생성 | 외부 리뷰 #1 | DOC |
| 8 | DocAI batch timeout → LRO polling | 외부 리뷰 #1 | DOC |
| 9 | 텍스트 추출 F1 → CER/WER | 외부 리뷰 #2 | DOC, MMD |
| 10 | 비용 추적 공통 유틸 (cost_log.jsonl) | 자체 리뷰 | 공통 환경, 전 테스트 |
| 11 | C10 contents 필드 병행 + 재전달 금지 규칙 | 자체+외부 리뷰 | C10 |
| 12 | tokens_per_char 캘리브레이션 | 자체 리뷰 | C2 |
| 13 | Embedding split-retry 로직 | 외부 리뷰 | C2 |
| 14 | PDF 크기 제한 (10MB, 5p) | 외부 리뷰 #3 | 체크리스트, MMD |
| 15 | DocAI 리전 명시 | 자체 리뷰 | 공통 환경 |
| 16 | X1 Rate Limit/Safety 기대값 현실화 | 외부 리뷰 #8 | X1 |
| 17 | C5 vs VAS 공정 비교 (동일 쿼리 3축) | 자체 리뷰 | VAS, 결과 종합 |
| **v2.1 변경** | | | |
| 18 | validate_pdf()에 페이지 수 체크 추가 (pypdf) | 코드 리뷰 | MMD |
| 19 | 캘리브레이션을 CountTokens API로 전환 + split-retry를 핵심 안전장치로 격상 | 코드 리뷰 | C2 |
| 20 | import_op 폴링 루프 + 플랜B (미완료 시 범위 축소) | 코드 리뷰 | Day 3 시작 |
| 21 | C6 latency=0 → time.perf_counter() 측정 + domain 쿼리도 기록 | 코드 리뷰 | C6 |
| 22 | VAS Engine 생성을 Day 2 선트리거로 이동 | 코드 리뷰 | Day 2, VAS |
| 23 | RUN_ID suffix로 리소스 이름 고유화 (재실행 방어) | 코드 리뷰 | Day 2, 삭제 체크리스트 |
| 24 | summarize_costs()에 모델별 단가 상수 + 추정 비용($) 산출 추가 | 코드 리뷰 | 공통 유틸 |
| 25 | evaluate_relations() 관계 F1 산출 함수 추가 | 코드 리뷰 | NER |
| 26 | RAG score threshold(>0.5) → hit@5 + score 분포 기록으로 변경 | 코드 리뷰 | C5 |