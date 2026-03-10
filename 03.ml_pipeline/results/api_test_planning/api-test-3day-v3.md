# Vertex AI API 기능 테스트 — GraphRAG + LLM 집중 (3일) v3

> **목적**: Gemini API, Embeddings, Document AI, RAG Engine의 **기능 동작 여부**와 **한국어 품질**을 검증하여 GraphRAG 서비스 설계 의사결정에 필요한 데이터를 확보한다.
> 

> **테스트 범위**: 크롤링(Document AI,Vertex AI Search,Gemini 멀티모달), NER 작업 graphrag 구축과 llm api를 사용하기 위한 기능 테스트 위주 테스트
> 

---

## 테스트 구조 — GraphRAG 파이프라인 순서

| 날짜 | 테스트 목적 | 상세 기능 |
| --- | --- | --- |
| Day 1 | LLM 기본 기능  | C1: Gemini API
C2: Embedding |
| Day 2  | 데이터 수집 → 정제 → NER | C5 corpus + VAS Data Store 생성
(오전 최우선 — 인덱싱 백그라운드 대기)
DOC: Document AI (PDF→텍스트) 
MMD: Gemini 멀티모달 (비교)
NER: 엔티티/관계 추출
E2E: 정제→NER 파이프라인 비교 |
| Day 3 | 검색 + 생성 + 운영 | C5: RAG 검색+생성
VAS: Vertex AI Search
C6: Grounding
C10: Prompt Caching
X1: 에러 핸들링
결과 종합 + 의사결정 |

> Day 2 오전에 트리거한 C5 corpus import와 VAS 문서 인덱싱한 데이터를 Day 3 시작 시 검색 테스트 데이터로 사용
**[v3] Operation name은 `results/pending_ops.json`에 저장 — Day 3 세션에서 복원.**
> 

---

## 범위 및 제외 사항

### 포함 (기능 테스트 중심)

| ID | 테스트 | 이유 |
| --- | --- | --- |
| C1 | Gemini API 기본 추론 | LLM API 핵심: 호출 패턴, 스트리밍, 한국어 품질 |
| C2 | Embeddings API | GraphRAG 문서 임베딩 필수 |
| DOC | Document AI | 크롤링 결과물(PDF/이미지) → 구조화 텍스트 추출 |
| MMD | Gemini 멀티모달 입력 | PDF/이미지 직접 입력으로 텍스트 추출+정제 (Document AI 대안) |
| NER | Gemini 기반 NER (엔티티 추출) | GraphRAG 지식 그래프 구축 핵심: 엔티티/관계 추출 |
| C5 | RAG Engine | GraphRAG 검색+생성 핵심 |
| VAS | Vertex AI Search (Discovery Engine) | URL 기반 자동 크롤링+인덱싱, RAG 보완 |
| C6 | Grounding (Google Search) | RAG 보완: 실시간 정보 |
| C10 | Prompt Caching | GraphRAG 운영 비용 절감 검증 |
| X1 | API 에러 핸들링 | 에러 코드/재시도 패턴 확인 |

### 전체 시스템 대비 테스트 제외 항목

| 항목 | 제외 이유 |
| --- | --- |
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
  asia-northeast3      — Vertex AI 리소스 (LLM, Embedding, RAG, Vertex AI Search): 리전 별 서비스 차이 확인
  asia (멀티리전)        — Document AI 프로세서 전용 (asia 리전만 지원?)
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
  - Document AI API (리전: asia)
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
  ├── 엔티티: (text, type)
  ├── 관계: (subject, predicate, object)
  └── 담당: ___ / 완료 기한: 테스트 D-2

□ 데이터셋 GCS 업로드 (전체)
□ DS-PDF-SAMPLE 선별 기준: 10MB 미만, 5페이지 이하, 레이아웃 다양성 확보
  ├── 단순 텍스트 (KO/EN 각 3개)
  ├── 2단 레이아웃 (KO/EN 각 2개)
  ├── 표 포함 (KO/EN 각 3개)
  └── 이미지 포함 (KO/EN 각 2개)
□ 프롬프트 파일 준비 (short/medium 한국어·영어 쌍)
□ C5 RAG 검색 gold 문서 준비 (쿼리별 기대 문서 1~2건 지정)   ← [v3 I4]
```

### 데이터셋 (최소 구성)

| ID | 용도 | 형태 | 크기 | 언어 |
| --- | --- | --- | --- | --- |
| `DS-RAG-DOCS` | RAG 문서 (이력서+뉴스) | PDF + TXT | 200~500 docs | KO/EN 7:3 |
| `DS-PDF-SAMPLE` | Document AI / 멀티모달 평가 | PDF (이력서, 뉴스, 표 포함) | 20~30 files (**10MB 미만, 5p 이하**) | KO/EN 7:3 |
| `DS-LLM-EVAL` | LLM 평가셋 | JSONL | 50~100 examples | KO/EN 7:3 |
| `DS-EMBED-SAMPLE` | 임베딩 품질 평가 | JSONL | 1K~5K docs | KO/EN 7:3 |
| `DS-NER-EVAL` | NER 평가셋 (텍스트 + **정답 엔티티/관계**) | JSONL | 10~20 examples (**사전 라벨링 필수**) | KO/EN 7:3 |
| `DS-RAG-GOLD` | RAG 검색 gold (쿼리→기대 문서) | JSON | 5 queries | KO |

### 한국어 품질 평가 기준

| 축 | 설명 | 점수 |
| --- | --- | --- |
| 정확성/환각 | 사실 오류, 존재하지 않는 정보 생성 여부 | 0~3 |
| 완전성 | 질문 의도를 충분히 충족했는가 | 0~3 |
| 도메인 적합성 | 채용/이력서/기업 맥락 용어, 표현 적절성 | 0~2 |
| **합계** | 6점 이상 = 사용 가능, 4~5 = 개선 필요, 3 이하 = 불가 | **0~8** |

### 공통 테스트 프레임워크

```python
import json, time, os, traceback
from datetime import datetime

COST_LOG_DIR = "results"
RESULT_LOG_PATH = f"{COST_LOG_DIR}/test_results.json"
os.makedirs(COST_LOG_DIR, exist_ok=True)

# ── 테스트 실행 래퍼 ─────────────────────────────────────
_test_results = {}

def run_test(name: str, fn, *args, **kwargs):
    """개별 테스트를 try/except로 격리. 실패해도 다음 테스트 계속 진행."""
    print(f"\n{'='*60}")
    print(f"[START]{name}")
    print(f"{'='*60}")
    start = time.perf_counter()
    try:
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        _test_results[name] = {"status": "PASS", "elapsed_ms": round(elapsed, 1),
                                "result": result, "timestamp": datetime.now().isoformat()}
        print(f"[PASS]{name} ({elapsed:.0f}ms)")
        return result
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        _test_results[name] = {"status": "FAIL", "elapsed_ms": round(elapsed, 1),
                                "error": str(e), "traceback": traceback.format_exc(),
                                "timestamp": datetime.now().isoformat()}
        print(f"[FAIL]{name} ({elapsed:.0f}ms):{e}")
        return None

# ── 결과 저장 ────────────────────────────────────────
def save_test_result(test_id: str, metrics: dict):
    """개별 테스트 검증 수치를 results/test_results.json에 누적 저장."""
    existing = {}
    if os.path.exists(RESULT_LOG_PATH):
        with open(RESULT_LOG_PATH) as f:
            existing = json.load(f)
    existing[test_id] = {**metrics, "saved_at": datetime.now().isoformat()}
    with open(RESULT_LOG_PATH, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

def save_all_results():
    """세션 종료 시 전체 결과 덤프."""
    with open(f"{COST_LOG_DIR}/test_run_summary.json", "w") as f:
        json.dump(_test_results, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 전체 결과 저장:{COST_LOG_DIR}/test_run_summary.json")

# ── 비용 추적 공통 유틸리티 ────────────────────────────────────────
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
    """Day 3 결과 종합 시 호출 — 테스트별/모델별 토큰 집계 + 추정 비용($) 산출."""
    from collections import defaultdict

    # 모델별 단가 (USD per 1K tokens, 2025 Q4 기준 — 변동 가능)
    # 향후 configs/pricing.json으로 외부화 권장
    PRICE_PER_1K = {
        "gemini-2.5-flash":       (0.00015, 0.0006),
        "gemini-2.5-pro":         (0.00125, 0.005),
        "gemini-embedding-001":   (0.00004, 0.0),
        "text-embedding-005":     (0.00004, 0.0),
        "docai-ocr":              (0.0, 0.0),
        "docai-layout":           (0.0, 0.0),
        "discovery-engine":       (0.0, 0.0),
        "rag-retrieval":          (0.0, 0.0),
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
    print(f"{'테스트':>15}{'모델':>25}{'입력토큰':>10}{'출력토큰':>10}{'호출':>5}{'추정$':>8}")
    print(f"{'='*70}")
    for (test_id, model_id), v in sorted(totals.items()):
        prices = PRICE_PER_1K.get(model_id, (0.001, 0.002))
        est = (v["input_tokens"] / 1000 * prices[0] +
               v["output_tokens"] / 1000 * prices[1])
        total_estimated += est
        print(f"{test_id:>15}{model_id:>25}{v['input_tokens']:>10,} "
              f"{v['output_tokens']:>10,}{v['calls']:>5} ${est:>7.3f}")

    print(f"{'='*70}")
    print(f"{'추정 합계':>53} ${total_estimated:>7.2f}")
    print(f"  ⚠ Document AI, VAS Enterprise, Grounding 비용은 토큰 기반이 아님 — Billing에서 별도 확인")

# ── Operation 영속 저장/복원 유틸 ─────────────────────────
PENDING_OPS_PATH = f"{COST_LOG_DIR}/pending_ops.json"

def save_pending_ops(ops: dict):
    """Day 2에서 LRO operation name 저장. Day 3에서 복원용."""
    with open(PENDING_OPS_PATH, "w") as f:
        json.dump(ops, f, indent=2)
    print(f"✓ Operation names 저장:{PENDING_OPS_PATH}")

def load_pending_ops() -> dict:
    """Day 3에서 Day 2 operation name 복원."""
    with open(PENDING_OPS_PATH) as f:
        ops = json.load(f)
    print(f"✓ Operation names 복원:{list(ops.keys())}")
    return ops
```

### GCS 구조

```yaml
gs://ml-api-test-vertex/
├── datasets/
│   ├── DS-RAG-DOCS/
│   ├── DS-PDF-SAMPLE/       # 10MB 미만, 5p 이하 PDF만
│   ├── DS-LLM-EVAL/
│   ├── DS-EMBED-SAMPLE/
│   ├── DS-NER-EVAL/         # gold 엔티티/관계 포함
│   └── DS-RAG-GOLD/         # [v3 I4] 쿼리별 기대 문서 ID
├── prompts/
├── results/                  # 비용 로그 + 테스트 결과 JSON
├── docai-output/
└── configs/
```

---

## Day 1 — Gemini API 기본 추론 + Embeddings API

### 환경 구성

```
□ SDK 설치 + ADC 인증 확인
□ Document AI 프로세서 Console 생성 완료 확인 (name 기록)
□ 데이터셋 GCS 업로드 확인
□ 공통 프레임워크 (run_test, log_api_cost, save_test_result) 동작 확인
□ DS-NER-EVAL gold 데이터 확인 (사전 라벨링 완료 여부)
□ DS-RAG-GOLD 쿼리별 기대 문서 확인
```

### TEST-C1: Gemini API 기본 추론

> **목표**: Gemini 모델별 호출 패턴 확인, 스트리밍 동작, 한국어 응답 품질 검증
> 

```python
import google.genai as genai
from google.genai import types
import time

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="asia-northeast3")

# ── 1. 비스트리밍 호출 (기본 동작 확인) ──────────────────────────
# [v3 O6] Pro는 KO만, Flash는 KO+EN — 한국어 품질이 핵심 목적
test_matrix = {
    "gemini-2.5-flash": ["short_ko", "short_en", "medium_ko", "medium_en"],
    "gemini-2.5-pro":   ["short_ko", "medium_ko"],  # [v3] EN 제거
}
prompts = {
    "short_ko": "지식 그래프 임베딩 개념을 한 문장으로 요약해줘.",
    "short_en": "Summarize the concept of knowledge graph embedding in one sentence.",
    "medium_ko": open("prompts/medium_1k_ko.txt").read(),
    "medium_en": open("prompts/medium_1k_en.txt").read(),
}

def test_c1_non_streaming():
    results = []
    for model_id, prompt_names in test_matrix.items():
        for prompt_name in prompt_names:
            start = time.perf_counter()
            response = client.models.generate_content(
                model=model_id,
                contents=prompts[prompt_name],
                config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=2048)
            )
            latency = (time.perf_counter() - start) * 1000

            usage = response.usage_metadata
            input_tokens = getattr(usage, "prompt_token_count", 0)
            output_tokens = getattr(usage, "candidates_token_count", 0)

            log_api_cost("test-c1", model_id, input_tokens, output_tokens, latency,
                         {"prompt_name": prompt_name, "mode": "non-streaming"})

            results.append({"model": model_id, "prompt": prompt_name,
                           "latency_ms": latency, "input_tokens": input_tokens,
                           "output_tokens": output_tokens})
            print(f"[{model_id}]{prompt_name}: "
                  f"latency={latency:.0f}ms, input={input_tokens}, output={output_tokens}")
    return results

run_test("C1-non-streaming", test_c1_non_streaming)

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

def test_c1_streaming():
    results = {}
    for model_id in ["gemini-2.5-flash", "gemini-2.5-pro"]:
        r = measure_streaming(client, model_id, prompts["short_ko"])
        results[model_id] = r
        print(f"[{model_id}] streaming: ttft={r['ttft_ms']:.0f}ms, total={r['total_ms']:.0f}ms")
    return results

run_test("C1-streaming", test_c1_streaming)

# ── 3. 시스템 프롬프트 + 구조화 출력 ─────────────────────────────
def test_c1_structured():
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="다음 이력서를 분석해서 핵심 스킬 3가지를 추출해줘: [이력서 텍스트]",
        config=types.GenerateContentConfig(
            system_instruction="당신은 채용 도메인 전문가입니다. JSON 형식으로 응답하세요.",
            temperature=0.0,
            response_mime_type="application/json",
        )
    )
    try:
        result = json.loads(response.text)
        return {"success": True, "keys": list(result.keys()) if isinstance(result, dict) else "array"}
    except json.JSONDecodeError:
        return {"success": False, "raw": response.text[:200]}

run_test("C1-structured-output", test_c1_structured)

# C1 결과 저장
save_test_result("C1", {
    "non_streaming": _test_results.get("C1-non-streaming", {}),
    "streaming": _test_results.get("C1-streaming", {}),
    "structured": _test_results.get("C1-structured-output", {}),
})
```

**검증 항목**:

| 항목 | 2.5 Flash | 2.5 Pro | Pass 기준 |
| --- | --- | --- | --- |
| 비스트리밍 호출 성공 | ✓/✗ | ✓/✗ | 정상 응답 |
| 스트리밍 ttft (short_ko) | ___ms | ___ms | < 2s |
| 한국어 응답 품질 (3축, 0-8) | ___ | ___ | ≥ 6 |
| JSON 구조화 출력 | ✓/✗ | ✓/✗ | 유효 JSON |
| usage_metadata 반환 | ✓/✗ | ✓/✗ | 토큰 수 확인 |
| 비용 (short 10회 기준) | $___ | $___ | 기록 (cost_log.jsonl) |

---

### TEST-C2: Embeddings API

> **목표**: 임베딩 모델 동작 확인, 한국어 임베딩 품질, 배치 처리 패턴 검증
> 

```python
import google.genai as genai
from google.genai import types

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="asia-northeast3")

# ── 0. tokens_per_char 캘리브레이션 (참고용 — 핵심 안전장치는 split-retry) ──
DEFAULT_TOKENS_PER_CHAR = 0.6  # 한국어 보수적 기본값
calibration_texts = load_sample_texts()[:10]

def calibrate_tokens_per_char(client, texts: list[str], model: str) -> float:
    """CountTokens API 기반 캘리브레이션. 실패 시 기본값 반환."""
    total_chars, total_tokens = 0, 0
    api_available = False

    for text in texts:
        total_chars += len(text)
        try:
            count_resp = client.models.count_tokens(model=model, contents=text)
            total_tokens += count_resp.total_tokens
            api_available = True
        except Exception:
            total_tokens += int(len(text) * DEFAULT_TOKENS_PER_CHAR)

    result = total_tokens / total_chars if total_chars > 0 else DEFAULT_TOKENS_PER_CHAR

    if api_available:
        print(f"✓ 캘리브레이션 완료 (CountTokens API): tokens_per_char ={result:.3f}")
    else:
        print(f"⚠ CountTokens API 미지원 — 기본값 유지: tokens_per_char ={result:.3f}")

    return result

# embedding 모델은 CountTokens API 미지원 (?) → 생성 모델(flash)로 캘리브레이션.
# 토큰화 특성은 모델 간 유사하므로, 배치 효율 최적화 목적에는 충분.
CALIBRATED_TOKENS_PER_CHAR = calibrate_tokens_per_char(
    client, calibration_texts, "gemini-2.5-flash"
)

# ── 1. 단건 임베딩 (기본 동작 확인) ──────────────────────────────
def test_c2_single():
    results = {}
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

        log_api_cost("test-c2", model_id, 0, 0, latency, {"mode": "single", "dimension": dim})
        results[model_id] = {"dimension": dim, "latency_ms": latency}
        print(f"[{model_id}] dimension={dim}, first_5={resp.embeddings[0].values[:5]}")
    return results

run_test("C2-single-embedding", test_c2_single)

# ── 2. 동적 배치 (캘리브레이션 값 적용 — 참고용 최적화) ─────────────
def dynamic_batch(texts: list[str], max_texts: int = 250, max_tokens: int = 20000,
                  tokens_per_char: float = None) -> list[list[str]]:
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
def embed_with_retry(client, model: str, batch: list[str],
                     config, max_splits: int = 3) -> list:
    from google.api_core.exceptions import InvalidArgument
    try:
        resp = client.models.embed_content(model=model, contents=batch, config=config)
        return [e.values for e in resp.embeddings]
    except InvalidArgument as e:
        if "token" in str(e).lower() and max_splits > 0 and len(batch) > 1:
            mid = len(batch) // 2
            print(f"  ⚠ 토큰 초과 — 배치 분할 ({len(batch)} →{mid} +{len(batch)-mid})")
            left  = embed_with_retry(client, model, batch[:mid], config, max_splits - 1)
            right = embed_with_retry(client, model, batch[mid:], config, max_splits - 1)
            return left + right
        raise

# ── 4. DS-EMBED-SAMPLE 배치 처리 ─────────────────────────────────
def test_c2_batch():
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

    return {"total_embeddings": len(all_embeddings), "batches": len(batches)}

run_test("C2-batch-embedding", test_c2_batch)

# ── 5. task_type별 동작 확인 ──────────────────────────────────────
def test_c2_task_types():
    task_types = ["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]  # [v3] 2종만
    results = {}
    for tt in task_types:
        try:
            resp = client.models.embed_content(
                model="gemini-embedding-001",
                contents="테스트 텍스트",
                config=types.EmbedContentConfig(task_type=tt)
            )
            results[tt] = {"success": True, "dim": len(resp.embeddings[0].values)}
            print(f"task_type={tt}: OK (dim={len(resp.embeddings[0].values)})")
        except Exception as e:
            results[tt] = {"success": False, "error": str(e)}
            print(f"task_type={tt}: FAIL ({e})")
    return results

run_test("C2-task-types", test_c2_task_types)

# [v3 I2] C2 결과 저장
save_test_result("C2", {
    "calibrated_tokens_per_char": CALIBRATED_TOKENS_PER_CHAR,
    "single": _test_results.get("C2-single-embedding", {}),
    "batch": _test_results.get("C2-batch-embedding", {}),
    "task_types": _test_results.get("C2-task-types", {}),
})
```

**검증 항목**:

| 항목 | gemini-embedding-001 | text-embedding-005 | Pass 기준 |
| --- | --- | --- | --- |
| 단건 호출 성공 | ✓/✗ | ✓/✗ | 벡터 반환 |
| 기본 차원 | ___ | ___ | 기록 |
| tokens_per_char 캘리브레이션 | ___ | N/A | 값 기록 (0.4~0.8 범위) |
| 배치 처리 성공 (250건) | ✓/✗ | N/A | 에러 없음 |
| split-retry 동작 (초과 시) | ✓/✗ | N/A | 분할 후 성공 |
| task_type 2종 지원 | ___/2 | N/A | 기록 |
| 한국어 코사인 유사도 정상 | ✓/✗ | N/A | 유사 문서 > 0.7 |

---

## Day 2 — 데이터 수집·정제 → NER 파이프라인

> **Day 2 목표**: 크롤링 결과물(PDF/HTML/이미지)을 텍스트로 변환하고, 엔티티/관계를 추출하는 **GraphRAG 데이터 파이프라인**의 각 단계를 GCP 서비스로 검증한다.
> 
> 
> ```
> 크롤링 결과물 (PDF/HTML)
>     ├─ 방법 A: Document AI → 텍스트 추출 → Gemini NER → 그래프 트리플
>     │          (정확도 높음, 2단계, 레이아웃 보존)
>     └─ 방법 B: Gemini 멀티모달 → 텍스트 추출 + NER 동시 → 그래프 트리플
>                (단순함, 1단계, PDF 직접 입력)
> ```
> 

### Day 2 C5 Corpus + VAS Data Store 생성 (인덱싱 백그라운드 실행)

> Day 3에서 즉시 검색 테스트에 들어가려면, 인덱싱을 Day 2에 미리 시작해야 함.
아래 생성 + import 트리거 후, DOC/MMD/NER 작업을 진행하면서 백그라운드 대기.
> 

```python
import google.genai as genai
from google.genai import types
from google.cloud import discoveryengine_v1 as discoveryengine
import datetime

# ── 재실행 방어: RUN_ID suffix ────────────────────────────────────
RUN_ID = datetime.datetime.now().strftime("%m%d%H%M")  # e.g., "03051430"
print(f"[RUN_ID]{RUN_ID} — 모든 리소스에 suffix 적용")

# ── C5: RAG Corpus 생성 + Import 트리거 ───────────────────────────
client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="asia-northeast3")

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
print(f"[C5] Corpus 생성:{corpus.name}")

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
print(f"[C5] Import 시작 — 백그라운드 대기. Operation:{import_op}")

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
print(f"[VAS] Data Store:{unstructured_store.name}")

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

# ── VAS: Search Engine 생성 (Day 2에 미리 생성 — Day 3 대기 제거) ──
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

# ── Resource names 파일 저장 (Day 3 복원용) ───────────────
pending = {
    "c5_corpus_name": corpus.name,
    "vas_store_name": unstructured_store.name,
    "vas_engine_id": f"test-vas-search-engine-{RUN_ID}",
    "run_id": RUN_ID,
}
# op name은 best-effort 저장 (없어도 Day 3 list_files/list_documents로 판정)
for key, op in [("c5_import_op", import_op), ("vas_import_op", vas_import_op),
                ("vas_engine_op", engine_op)]:
    try:
        pending[key] = getattr(op, "operation", op).name
    except Exception:
        print(f"  ⚠{key} op name 저장 실패 — Day 3에서 resource 기반 판정으로 대체")
save_pending_ops(pending)

print("\n★ Day 2 백그라운드 작업 시작 완료. DOC/MMD/NER 진행.")
```

---

### TEST-DOC: Document AI — PDF 텍스트 추출

> **목표**: PDF 이력서/뉴스에서 텍스트를 정확하게 추출하는지 검증. OCR, 표 파싱, 레이아웃 분석 품질 확인.
> 

```python
from google.cloud import documentai_v1 as documentai
import time, glob

project_id = "ml-api-test-vertex"
location = "us"  # ⚠ Document AI는 us / eu 멀티리전만 지원 (asia-northeast3 아님)

docai_client = documentai.DocumentProcessorServiceClient(
    client_options={"api_endpoint": f"{location}-documentai.googleapis.com"}
)

# ── 1. 사전 생성된 프로세서 name 사용 (Console에서 생성 완료) ──────
OCR_PROCESSOR_NAME    = "projects/ml-api-test-vertex/locations/us/processors/YOUR_OCR_ID"
LAYOUT_PROCESSOR_NAME = "projects/ml-api-test-vertex/locations/us/processors/YOUR_LAYOUT_ID"

# ── 2. 단건 처리 (동기 API) ──────────────────────────────────────
def process_document(processor_name: str, file_path: str, mime_type: str = "application/pdf"):
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
import unicodedata, re

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def levenshtein_distance(s1: list, s2: list) -> int:
    n, m = len(s1), len(s2)
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        curr = [i] + [0] * m  # [v3 P6] 매 반복 curr 초기화 개선
        for j in range(1, m + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[m]

def calc_cer(extracted: str, gold: str) -> dict:
    ext_chars = list(normalize_text(extracted))
    gold_chars = list(normalize_text(gold))
    if len(gold_chars) == 0:
        return {"cer": 0.0 if len(ext_chars) == 0 else float('inf'),
                "edit_distance": len(ext_chars), "gold_length": 0}
    dist = levenshtein_distance(ext_chars, gold_chars)
    return {"cer": round(dist / len(gold_chars), 4), "edit_distance": dist,
            "gold_length": len(gold_chars), "extracted_length": len(ext_chars)}

def calc_wer(extracted: str, gold: str) -> dict:
    ext_words = normalize_text(extracted).split()
    gold_words = normalize_text(gold).split()
    if len(gold_words) == 0:
        return {"wer": 0.0 if len(ext_words) == 0 else float('inf'), "gold_words": 0}
    dist = levenshtein_distance(ext_words, gold_words)
    return {"wer": round(dist / len(gold_words), 4), "edit_distance": dist,
            "gold_words": len(gold_words), "extracted_words": len(ext_words)}

def evaluate_extraction_quality(extracted: str, gold: str) -> dict:
    cer_result = calc_cer(extracted, gold)
    wer_result = calc_wer(extracted, gold)
    if cer_result["cer"] <= 0.05:     grade = "EXCELLENT"
    elif cer_result["cer"] <= 0.10:   grade = "GOOD"
    elif cer_result["cer"] <= 0.20:   grade = "ACCEPTABLE"
    else:                              grade = "POOR"
    return {"cer": cer_result["cer"], "wer": wer_result["wer"], "grade": grade,
            "detail": {"cer": cer_result, "wer": wer_result}}

# ── 4. DS-PDF-SAMPLE 테스트 (20~30 PDF) ──────────────────────────
def test_doc():
    pdf_files = glob.glob("datasets/DS-PDF-SAMPLE/*.pdf")
    results_ocr, results_layout = [], []

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

    # ── 5. Gold 텍스트 대비 품질 평가 (사전 준비된 3~5건) ─────────
    quality_results = []
    gold_files = glob.glob("datasets/DS-PDF-SAMPLE/gold/*.txt")
    for gold_path in gold_files:
        filename = gold_path.split("/")[-1].replace(".txt", ".pdf")
        gold_text = open(gold_path).read()

        ocr_match = next((r for r in results_ocr if r["file"] == filename), None)
        if ocr_match:
            quality = evaluate_extraction_quality(ocr_match["text"], gold_text)
            quality_results.append({"file": filename, "processor": "OCR", **quality})
            print(f"[OCR]{filename}: CER={quality['cer']:.4f}, WER={quality['wer']:.4f}, Grade={quality['grade']}")

        layout_match = next((r for r in results_layout if r["file"] == filename), None)
        if layout_match:
            quality = evaluate_extraction_quality(layout_match["text"], gold_text)
            quality_results.append({"file": filename, "processor": "Layout", **quality})
            print(f"[Layout]{filename}: CER={quality['cer']:.4f}, WER={quality['wer']:.4f}, Grade={quality['grade']}")

    return {"ocr_count": len(results_ocr), "layout_count": len(results_layout),
            "quality": quality_results, "results_ocr": results_ocr, "results_layout": results_layout}

doc_results = run_test("DOC-pdf-extraction", test_doc)

# ── 6. 배치 처리 (비동기 API — 대량 문서용, LRO polling) ──────────
def test_doc_batch():
    def batch_process_gcs(processor_name, gcs_input_uri, gcs_output_uri):
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
        print(f"배치 처리 LRO 시작:{operation.operation.name}")
        while not operation.done():
            time.sleep(30)
            print(f"  배치 처리 진행 중... done={operation.done()}")

        # [v3.1] 성공/실패 확정 — done()=True여도 실패일 수 있음
        if operation.exception():
            raise RuntimeError(f"배치 처리 실패:{operation.exception()}")
        result = operation.result()
        print(f"배치 처리 완료 ✓")
        return True

    return batch_process_gcs(
        OCR_PROCESSOR_NAME,
        "gs://ml-api-test-vertex/datasets/DS-PDF-SAMPLE/",
        "gs://ml-api-test-vertex/docai-output/"
    )

run_test("DOC-batch-processing", test_doc_batch)
save_test_result("DOC", _test_results.get("DOC-pdf-extraction", {}))
```

**검증 항목**:

| 항목 | OCR Processor | Layout Parser | Pass 기준 |
| --- | --- | --- | --- |
| PDF 텍스트 추출 성공 | ___/20 files | ___/20 files | ≥ 95% |
| 한국어 텍스트 추출 **CER** | ___ | ___ | **≤ 0.10** (10% 이하) |
| 한국어 텍스트 추출 **WER** (보조) | ___ | ___ | 기록 (CER 보조) |
| 표(table) 구조 인식 | N/A | _**/**_건 | 표 포함 문서에서 인식 |
| 2단 레이아웃 처리 | ✓/✗ | ✓/✗ | 순서 보존 |
| 이미지 내 한국어 OCR | ✓/✗ | ✓/✗ | 읽기 가능 |
| 단건 처리 latency | ___ms | ___ms | < 5s (1페이지) |
| 배치 처리 동작 (LRO) | ✓/✗ | ✓/✗ | polling 완료 |

---

### TEST-MMD: Gemini 멀티모달 — PDF/이미지 직접 텍스트 추출

> **목표**: Gemini에 PDF를 직접 입력해 텍스트 추출 + 정제를 한 번에 처리하는 패턴 검증.
NER 파이프라인 B에서 유사 검증
> 

```python
import google.genai as genai
from google.genai import types
import time, json, glob, os

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="asia-northeast3")

# ── 0. PDF 크기/페이지 사전 검증 ──────────────────────────────────
MAX_PDF_SIZE_MB = 10
MAX_PDF_PAGES = 5

def validate_pdf(pdf_path: str) -> bool:
    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    if size_mb > MAX_PDF_SIZE_MB:
        print(f"⚠ SKIP{pdf_path}:{size_mb:.1f}MB >{MAX_PDF_SIZE_MB}MB")
        return False
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        if len(reader.pages) > MAX_PDF_PAGES:
            print(f"⚠ SKIP{pdf_path}:{len(reader.pages)}p >{MAX_PDF_PAGES}p")
            return False
    except ImportError:
        print(f"⚠ WARNING: pypdf 미설치 — 페이지 수 체크 스킵")
    except Exception as e:
        print(f"⚠ WARNING:{pdf_path} 페이지 수 읽기 실패:{e}")
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

    return {"text": response.text, "text_length": len(response.text),
            "latency_ms": latency, "input_tokens": input_tokens, "output_tokens": output_tokens}

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
            temperature=0.0, response_mime_type="application/json",
            response_schema=STRUCTURED_SCHEMA, max_output_tokens=8192
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

# ── 3. DS-PDF-SAMPLE 테스트 ───────────────────────────────────────
# 텍스트 추출: 전수, 구조화 추출: 5건 샘플
def test_mmd():
    pdf_files = [f for f in glob.glob("datasets/DS-PDF-SAMPLE/*.pdf") if validate_pdf(f)]
    results_mm_text = []
    results_mm_struct = []

    for i, pdf_path in enumerate(pdf_files):
        filename = pdf_path.split("/")[-1]

        # 텍스트 추출: 전수
        text_result = extract_text_multimodal(pdf_path)
        results_mm_text.append({"file": filename, **text_result})

        # [v3 O3] 구조화 추출: 5건만
        if i < 5:
            struct_result = extract_structured_multimodal(pdf_path)
            results_mm_struct.append({"file": filename, **struct_result})
            sections = len(struct_result.get("structured", {}).get("sections", []))
            print(f"[{filename}] Text={text_result['text_length']}chars | "
                  f"Struct=success={struct_result['success']},sections={sections}")
        else:
            print(f"[{filename}] Text={text_result['text_length']}chars | Struct=SKIP (>5건)")

    # ── 4. Gold 텍스트 대비 CER/WER 평가 ──────────────────────────
    quality_results = []
    for gold_path in glob.glob("datasets/DS-PDF-SAMPLE/gold/*.txt"):
        filename = gold_path.split("/")[-1].replace(".txt", ".pdf")
        gold_text = open(gold_path).read()

        mm_match = next((r for r in results_mm_text if r["file"] == filename), None)
        if mm_match:
            quality = evaluate_extraction_quality(mm_match["text"], gold_text)
            quality_results.append({"file": filename, **quality})
            print(f"[MMD]{filename}: CER={quality['cer']:.4f}, WER={quality['wer']:.4f}, Grade={quality['grade']}")

    struct_success = sum(1 for r in results_mm_struct if r.get("success"))
    return {"text_count": len(results_mm_text), "struct_count": len(results_mm_struct),
            "struct_success": struct_success, "quality": quality_results,
            "results_mm_text": results_mm_text}

mmd_results = run_test("MMD-multimodal-extraction", test_mmd)
save_test_result("MMD", _test_results.get("MMD-multimodal-extraction", {}))
```

**검증 항목**:

| 항목 | Gemini 텍스트 추출 | Gemini 구조화 추출 (5건) | Pass 기준 |
| --- | --- | --- | --- |
| PDF 입력 성공 | ___/20 files | ___/5 files | ≥ 95% |
| 한국어 텍스트 추출 **CER** | ___ | N/A | **≤ 0.15** (15% 이하) |
| 구조화 JSON 성공률 | N/A | ___% | ≥ 90% |
| 표 마크다운 변환 | ✓/✗ | ✓/✗ | 표 구조 유지 |
| 단건 latency | ___ms | ___ms | < 10s (1페이지) |

**Document AI vs Gemini 멀티모달 비교 매트릭스**:

| 비교 항목 | Document AI (OCR) | Document AI (Layout) | Gemini 멀티모달 |
| --- | --- | --- | --- |
| 텍스트 추출 CER (↓ 낮을수록 좋음) | ___ | ___ | ___ |
| 텍스트 추출 WER (보조) | ___ | ___ | ___ |
| 표 인식 | ___ | ___ | ___ |
| 구조화 출력 | ✗ (별도 후처리) | △ (레이아웃만) | ✓ (JSON 직접) |
| 한국어 OCR | ___ | ___ | ___ |
| 단건 latency | ___ms | ___ms | ___ms |
| 비용/페이지 | $0.0015 | $0.01 | ~$___ |  |
| 후속 NER 연결 | 텍스트→별도 NER | 텍스트→별도 NER | 동시 처리 가능 |

---

### TEST-NER: Gemini 기반 Named Entity Recognition

> **목표**: GraphRAG 지식 그래프 구축을 위한 엔티티/관계 추출 성능 검증.
Few-shot 실행 코드 추가
evaluate_relations 호출부 + DS-NER-EVAL 드라이버 코드 추가
> 

**검증 항목**:

| 항목 | 2.5 Flash | 2.5 Pro | Pass 기준 |
| --- | --- | --- | --- |
| JSON 구조화 출력 성공률 | ___% | ___% | ≥ 95% |
| Zero-shot 엔티티 F1 (KO, normalized) | ___ | ___ | ≥ 0.70 |
| **[v3 P3] Few-shot 엔티티 F1 (KO)** | ___ | N/A | > Zero-shot |
| **[v3 P4] 관계 추출 F1 (KO)** | ___ | ___ | ≥ 0.60 |
| Entity-Relation 정합성 (consistency_rate) | ___% | ___% | ≥ 90% |
| 단건 latency (KO, short) | ___ms | ___ms | < 3s |

---

### TEST-E2E: 정제 → NER 파이프라인 비교 (방법 A vs 방법 B)

> **목표**: PDF → 그래프 트리플까지의 E2E 파이프라인을 2가지 방법으로 실행하고 품질·비용·속도를 비교.
비용 로깅에 실제 토큰 수 반영
> 

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

    # [v3 P5] 실제 Gemini 토큰 수 기록
    input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
    output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
    log_api_cost("test-e2e", "gemini-2.5-flash", input_tokens, output_tokens, total_ms,
                 {"pipeline": "A", "docai_ms": docai_result["latency_ms"]})

    try:
        ner_result = json.loads(response.text)
    except json.JSONDecodeError:
        ner_result = {"entities": [], "relations": []}

    consistency = check_entity_relation_consistency(ner_result)
    return {"method": "A (DocAI→NER)", "total_ms": total_ms,
            "text_length": len(extracted_text),
            "entities": len(ner_result.get("entities", [])),
            "relations": len(ner_result.get("relations", [])),
            "consistency_rate": consistency["consistency_rate"],
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "ner_result": ner_result}

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
            temperature=0.0, response_mime_type="application/json",
            response_schema=ENTITY_SCHEMA, max_output_tokens=8192
        )
    )
    total_ms = (time.perf_counter() - start) * 1000

    # [v3 P5] 실제 토큰 수 기록
    input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
    output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
    log_api_cost("test-e2e", "gemini-2.5-flash", input_tokens, output_tokens, total_ms,
                 {"pipeline": "B"})

    try:
        ner_result = json.loads(response.text)
    except json.JSONDecodeError:
        ner_result = {"entities": [], "relations": []}

    consistency = check_entity_relation_consistency(ner_result)
    return {"method": "B (Multimodal→NER)", "total_ms": total_ms,
            "entities": len(ner_result.get("entities", [])),
            "relations": len(ner_result.get("relations", [])),
            "consistency_rate": consistency["consistency_rate"],
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "ner_result": ner_result}

# ── 비교 실행 ─────────────────────────────────────────────────────
# [v3 I8] 10건→5건 축소 (Day 2 부하 경감)
def test_e2e():
    pdf_files = [f for f in glob.glob("datasets/DS-PDF-SAMPLE/*.pdf") if validate_pdf(f)]
    comparison = []
    for pdf_path in pdf_files[:5]:  # [v3] 5건
        filename = pdf_path.split("/")[-1]
        result_a = pipeline_a(pdf_path)
        result_b = pipeline_b(pdf_path)

        print(f"\n[{filename}]")
        print(f"  A:{result_a['total_ms']:.0f}ms, ent={result_a['entities']}, "
              f"rel={result_a['relations']}, consistency={result_a['consistency_rate']:.0%}")
        print(f"  B:{result_b['total_ms']:.0f}ms, ent={result_b['entities']}, "
              f"rel={result_b['relations']}, consistency={result_b.get('consistency_rate', 'N/A')}")

        comparison.append({"file": filename, "pipeline_a": result_a, "pipeline_b": result_b})
    return comparison

run_test("E2E-pipeline-comparison", test_e2e)
save_test_result("E2E", _test_results.get("E2E-pipeline-comparison", {}))
```

**E2E 파이프라인 비교 결과**:

| 비교 항목 | 방법 A (DocAI → NER) | 방법 B (멀티모달 NER) | 판단 |
| --- | --- | --- | --- |
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
from google.api_core import operation as ga_operation
from google.longrunning import operations_pb2
from google.cloud import discoveryengine_v1 as discoveryengine
import google.genai as genai
from google.genai import types

# ── [v3 P1] Day 2 Operation names 복원 ───────────────────────────
ops = load_pending_ops()
corpus_name = ops["c5_corpus_name"]
RUN_ID = ops["run_id"]

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="asia-northeast3")

# ── C5 import 완료 확인 (폴링) ────────────────────────────────────
MAX_WAIT_MINUTES = 30
POLL_INTERVAL_SEC = 60

print("[C5] Import 완료 확인 중...")
# [v3 P1] operation name으로 상태 조회
c5_import_ready = False
waited = 0

# GenAI SDK로 corpus 파일 목록 확인하여 import 완료 판단
try:
    files = list(client.corpora.list_files(name=corpus_name))
    if len(files) > 0:
        print(f"[C5] Import 완료 ✓ (파일{len(files)}건 확인)")
        c5_import_ready = True
    else:
        print(f"[C5] 파일 0건 — import 아직 진행 중일 수 있음, 폴링 시작")
except Exception as e:
    print(f"[C5] 파일 확인 실패:{e} — 폴링으로 전환")

while not c5_import_ready and waited < MAX_WAIT_MINUTES * 60:
    time.sleep(POLL_INTERVAL_SEC)
    waited += POLL_INTERVAL_SEC
    try:
        files = list(client.corpora.list_files(name=corpus_name))
        if len(files) > 0:
            print(f"[C5] Import 완료 ✓ (대기{waited//60}분, 파일{len(files)}건)")
            c5_import_ready = True
    except Exception:
        print(f"  ... 대기 중 ({waited//60}/{MAX_WAIT_MINUTES}분)")

if not c5_import_ready:
    print(f"⚠ [C5]{MAX_WAIT_MINUTES}분 내 미완료 — C5 검색 테스트 후반으로 지연")

# ── VAS import + Engine 완료 확인 ─────────────────────────────────
# [v3 I5] Engine 확인 한 번만 (중복 제거)
engine_client = discoveryengine.EngineServiceClient()
de_parent = "projects/ml-api-test-vertex/locations/global/collections/default_collection"

vas_import_ready = False
vas_engine_ready = False
vas_engine_name = None

print("[VAS] Import + Engine 준비 확인 중...")
try:
    # Engine 상태 조회 (name으로 get)
    engine = engine_client.get_engine(
        name=f"{de_parent}/engines/{ops['vas_engine_id']}"
    )
    vas_engine_name = engine.name
    vas_engine_ready = True
    print(f"[VAS] Engine 준비 완료 ✓:{engine.name}")
except Exception as e:
    print(f"⚠ [VAS] Engine 조회 실패:{e} — VAS 검색 테스트 스킵 가능")

# VAS import 확인 — 문서 1건이라도 존재하면 OK
# [v3.1] 전체 list → early break로 변경 (200~500건 전체 로드 방지)
try:
    doc_client = discoveryengine.DocumentServiceClient()
    first_doc = next(
        iter(doc_client.list_documents(
            parent=f"{ops['vas_store_name']}/branches/default_branch"
        )),
        None
    )
    if first_doc is not None:
        vas_import_ready = True
        print(f"[VAS] Import 완료 ✓ (문서 존재 확인)")
    else:
        print(f"⚠ [VAS] 문서 0건 — import 미완료, VAS 검색 제한적 실행")
except Exception as e:
    print(f"⚠ [VAS] 문서 확인 실패:{e}")
```

### TEST-C5: RAG Engine — 문서 검색 + 생성

> gold 문서 기반 자동 hit 판정 추가
> 

```python
# ── 0. [v3 I4] Gold 검색 데이터 로드 ─────────────────────────────
# gold 포맷: [{"query": "...", "expected_doc_names": ["doc1.pdf", "doc2.pdf"]}, ...]
# [v3.1] 인덱스 의존 → query 키 dict 매핑으로 변경 (순서 불일치 방어)
import json

rag_gold_map = {}  # {query_prefix: expected_doc_names}
try:
    with open("datasets/DS-RAG-GOLD/gold_queries.json") as f:
        rag_gold_list = json.load(f)
    for item in rag_gold_list:
        # 쿼리 앞 30자를 키로 사용 (정확 매칭보다 유연)
        rag_gold_map[item["query"][:30]] = set(item.get("expected_doc_names", []))
    print(f"[C5] RAG gold 쿼리 로드:{len(rag_gold_map)}건")
except FileNotFoundError:
    print("⚠ [C5] DS-RAG-GOLD 미준비 — 수동 판정으로 전환")

# ── 1. 검색 (Retrieval) 테스트 ────────────────────────────────────
ko_queries = [
    "Python과 머신러닝 경험이 있는 백엔드 개발자를 찾아줘",
    "데이터 엔지니어링과 클라우드 인프라 경험자",
    "NLP 및 자연어처리 관련 연구 경험이 있는 후보자",
    "스타트업 경험이 풍부한 프로덕트 매니저",
    "그래프 데이터베이스 및 지식 그래프 전문가",
]

def test_c5_retrieval():
    results = []
    for i, query in enumerate(ko_queries):
        start = time.perf_counter()
        search_results = client.corpora.retrieve(
            name=corpus_name,
            query=query,
            config=types.RetrieveConfig(top_k=5)
        )
        latency = (time.perf_counter() - start) * 1000
        log_api_cost("test-c5", "rag-retrieval", 0, 0, latency,
                     {"query": query[:30], "chunks": len(search_results.relevant_chunks)})

        # [v3 I4] Gold 기반 자동 hit 판정
        hit = False
        returned_docs = []
        for chunk in search_results.relevant_chunks[:5]:
            doc_name = chunk.chunk.document_metadata.display_name
            returned_docs.append(doc_name)

        # [v3.1] query prefix로 gold 매칭 (순서 무관)
        expected = rag_gold_map.get(query[:30], set())
        if expected:
            hit = bool(expected & set(returned_docs))

        results.append({"query": query, "chunks": len(search_results.relevant_chunks),
                        "latency_ms": latency, "hit": hit, "returned_docs": returned_docs[:3]})

        print(f"Query:{query[:30]}... →{len(search_results.relevant_chunks)} chunks "
              f"({latency:.0f}ms){'HIT' if hit else 'MISS/MANUAL'}")
        for j, chunk in enumerate(search_results.relevant_chunks[:3]):
            print(f"  [{j+1}] score={chunk.chunk_relevance_score:.3f} | "
                  f"{chunk.chunk.document_metadata.display_name}")

    hits = sum(1 for r in results if r["hit"])
    print(f"\n[C5] hit@5:{hits}/{len(results)}")
    return {"results": results, "hit_at_5": hits, "total_queries": len(results)}

run_test("C5-retrieval", test_c5_retrieval) if c5_import_ready else print("⚠ C5 import 미완료 — 스킵")

# ── 2. RAG + 생성 ────────────────────────────────────────────────
rag_queries = [
    "Python 백엔드 개발 경험이 있는 후보자 3명을 추천하고 각각의 강점을 설명해줘.",
    "데이터 엔지니어 포지션에 적합한 후보자를 찾아서 이력서 요약을 작성해줘.",
    "그래프 데이터베이스 전문가를 찾아 기술 스택과 경험을 정리해줘.",
    "NLP 연구 경험이 있는 후보자의 논문/프로젝트 이력을 요약해줘.",
    "클라우드 인프라 경험이 풍부한 DevOps 엔지니어를 추천해줘.",
]

def test_c5_rag_generate():
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
                            rag_corpora=[corpus_name],
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
        print(f"\nQuery:{query[:40]}...")
        print(f"Response ({latency:.0f}ms):{response.text[:200]}...")

    return rag_responses

rag_responses = run_test("C5-rag-generate", test_c5_rag_generate) if c5_import_ready else []
save_test_result("C5", {
    "retrieval": _test_results.get("C5-retrieval", {}),
    "rag_generate": _test_results.get("C5-rag-generate", {}),
})
```

**검증 항목**:

| 항목 | 결과 | Pass 기준 |
| --- | --- | --- |
| Corpus 생성 | ✓/✗ | 정상 생성 |
| 문서 인제스트 (200~500 docs) | ___건 성공 | 에러율 < 5% |
| import 완료 대기 후 검색 | ✓/✗ | 파일 목록 확인 성공 |
| 한국어 검색 **hit@5** (gold 자동 판정) | ___/5 queries | ≥ 3/5 |
| 한국어 검색 relevance score 분포 | min=***, median=***, max=___ | 기록 |
| RAG 생성 — 한국어 품질 (3축) | ___/8 | ≥ 6 |
| RAG 생성 — 소스 문서 인용 | ✓/✗ | grounding_metadata 존재 |

---

### TEST-VAS: Vertex AI Search — GCS 문서 검색 (+ 웹 크롤링 옵션)

```python
from google.cloud import discoveryengine_v1 as discoveryengine

search_client = discoveryengine.SearchServiceClient()

# ── 1. 검색 실행 (C5와 동일 쿼리) ────────────────────────────────
# [v3 I5] Engine name은 Day 3 시작 블록에서 이미 조회 완료
serving_config = f"{vas_engine_name}/servingConfigs/default_search"

shared_queries = [
    "Python과 머신러닝 경험이 있는 백엔드 개발자를 찾아줘",
    "데이터 엔지니어링과 클라우드 인프라 경험자",
    "NLP 및 자연어처리 관련 연구 경험이 있는 후보자",
    "스타트업 경험이 풍부한 프로덕트 매니저",
    "그래프 데이터베이스 및 지식 그래프 전문가",
]

def test_vas_search():
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

        print(f"\nQuery:{query}")
        print(f"  Results:{response.total_size}, Latency:{latency:.0f}ms")
        if summary_text:
            print(f"  Summary:{summary_text[:200]}")

    return vas_responses

vas_responses = run_test("VAS-search", test_vas_search) if vas_engine_ready else []

# ── 2. C5 vs VAS 공정 비교 (동일 쿼리 5개, 3축 평가) ─────────────
if rag_responses and vas_responses:
    print("\n" + "="*70)
    print("C5 RAG Engine vs VAS 비교 (동일 쿼리 5개)")
    print("="*70)
    for i, query in enumerate(shared_queries):
        rag_resp = rag_responses[i] if i < len(rag_responses) else {"response": "N/A"}
        vas_resp = vas_responses[i] if i < len(vas_responses) else {"summary": "N/A"}
        print(f"\n[Query{i+1}]{query[:40]}...")
        print(f"  RAG:{rag_resp.get('response', 'N/A')[:150]}...")
        print(f"  VAS:{vas_resp.get('summary', 'N/A')[:150]}...")
        print(f"  → 3축 수동 평가: RAG=___/8, VAS=___/8")

save_test_result("VAS", _test_results.get("VAS-search", {}))
```

**검증 항목 (필수: GCS 기반)**:

| 항목 | GCS 문서 | Pass 기준 |
| --- | --- | --- |
| Data Store 생성 | ✓/✗ | 정상 생성 |
| 문서 인덱싱 | ___건 | 에러 없음 |
| 한국어 검색 결과 품질 | ✓/✗ | 관련 문서 반환 |
| AI 요약 (한국어) | ✓/✗ | 한국어 요약 생성 |
| 인용(citation) | ✓/✗ | 출처 포함 |
| 검색 latency | ___ms | < 2s |

**C5 RAG Engine vs VAS 비교 매트릭스 (동일 쿼리 5개 기준)**:

| 비교 항목 | RAG Engine (C5) | Vertex AI Search (VAS) |
| --- | --- | --- |
| 데이터 소스 | GCS 파일 업로드 | GCS + **(옵션) 웹 크롤링** |
| 임베딩 제어 | 모델 직접 선택 | 내장 (자동) |
| 검색 품질 (3축) | ___/8 | ___/8 |
| AI 생성/요약 품질 (3축) | ___/8 | ___/8 |
| chunk 제어 | chunk_size 직접 설정 | 자동 |
| 비용 모델 | Spanner + Embedding API | Enterprise 검색 단가 |
| GraphRAG 적합성 | 커스텀 가능 | 매니지드 한정 |

---

### TEST-C6: Grounding with Google Search

```python
def test_c6_grounding():
    results = {}

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
    results["grounding_on"] = {"latency_ms": latency_on, "text": response_grounded.text[:300]}

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
    results["grounding_off"] = {"latency_ms": latency_off, "text": response_base.text[:300]}

    print(f"[C6] Grounding ON:{latency_on:.0f}ms")
    print(f"[C6] Grounding OFF:{latency_off:.0f}ms")

    # [v3 O4] 한국어 도메인 질문 1건만
    query = "2026년 한국 AI 채용 시장 동향은?"
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
    results["domain"] = {"query": query, "latency_ms": lat}
    print(f"[C6] Domain '{query}':{lat:.0f}ms")

    return results

run_test("C6-grounding", test_c6_grounding)
save_test_result("C6", _test_results.get("C6-grounding", {}))
```

**검증 항목**:

| 항목 | Grounding ON | Grounding OFF | Pass 기준 |
| --- | --- | --- | --- |
| 호출 성공 | ✓/✗ | ✓/✗ | 정상 응답 |
| 최신 정보 포함 (2026) | ✓/✗ | ✓/✗ | ON에서 최신 정보 반영 |
| 한국어 품질 (3축) | ___/8 | ___/8 | ≥ 6 |
| 검색 소스 메타데이터 | ✓/✗ | N/A | 출처 URL 포함 |

---

### TEST-C10: Prompt Caching

```python
SYSTEM_PROMPT = open("prompts/graphrag_system_5k.txt").read()  # ~5K tokens

def test_c10_caching():
    # ── [v3 I7] 캐시 생성 (실패 시 스킵) ─────────────────────────
    try:
        cache = client.caches.create(
            model="gemini-2.5-flash",
            config=types.CreateCachedContentConfig(
                contents=[{"role": "user", "parts": [{"text": SYSTEM_PROMPT}]}],
                system_instruction="GraphRAG 전문가로서 이력서와 기업 정보를 분석합니다.",
                ttl="3600s",
                display_name="test-c10-graphrag-cache"
            )
        )
        print(f"캐시 생성 성공:{cache.name}")
    except Exception as e:
        print(f"⚠ 캐시 생성 실패:{e} — C10 스킵")
        return {"status": "SKIP", "error": str(e)}

    queries = [f"후보자{i}번의 경력과 기업 A의 요구사항을 매칭해줘." for i in range(20)]

    # ── 캐시 ON (20회) ────────────────────────────────────────────
    latencies_cached = []
    cached_tokens_total = 0
    input_tokens_cached_total = 0
    output_tokens_cached_total = 0

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

        usage = resp.usage_metadata
        input_tokens = getattr(usage, "prompt_token_count", 0)
        output_tokens = getattr(usage, "candidates_token_count", 0)
        # [v3 P2] cached_content_token_count 추출
        cached_tokens = getattr(usage, "cached_content_token_count", 0)
        cached_tokens_total += cached_tokens
        input_tokens_cached_total += input_tokens
        output_tokens_cached_total += output_tokens

        log_api_cost("test-c10-cached", "gemini-2.5-flash", input_tokens, output_tokens, lat,
                     {"cached_tokens": cached_tokens})

    # ── 캐시 OFF (20회) ───────────────────────────────────────────
    latencies_uncached = []
    input_tokens_uncached_total = 0
    output_tokens_uncached_total = 0

    for query in queries:
        start = time.perf_counter()
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{SYSTEM_PROMPT}\n\n{query}",
            config=types.GenerateContentConfig(max_output_tokens=512)
        )
        lat = (time.perf_counter() - start) * 1000
        latencies_uncached.append(lat)

        usage = resp.usage_metadata
        input_tokens_uncached_total += getattr(usage, "prompt_token_count", 0)
        output_tokens_uncached_total += getattr(usage, "candidates_token_count", 0)

        log_api_cost("test-c10-uncached", "gemini-2.5-flash",
                     getattr(usage, "prompt_token_count", 0),
                     getattr(usage, "candidates_token_count", 0), lat)

    # ── [v3 P2] 비용 절감율 산출 ─────────────────────────────────
    # Prompt Caching: cached 토큰은 25% 할인 (Flash 기준)
    CACHE_DISCOUNT = 0.75  # cached 토큰은 원가의 75%
    PRICE_INPUT_PER_1K = 0.00015  # Flash input

    cost_uncached = input_tokens_uncached_total / 1000 * PRICE_INPUT_PER_1K
    # cached 토큰은 할인, 나머지 input은 정가
    non_cached_input = input_tokens_cached_total - cached_tokens_total
    cost_cached = ((cached_tokens_total * CACHE_DISCOUNT + non_cached_input) / 1000 * PRICE_INPUT_PER_1K)

    savings_pct = ((cost_uncached - cost_cached) / cost_uncached * 100) if cost_uncached > 0 else 0

    # [v3.1] 토큰 감소율 — 단가 변동에 무관한 지표로 결론 내구성 확보
    token_reduction_pct = (
        (input_tokens_uncached_total - (input_tokens_cached_total - cached_tokens_total))
        / input_tokens_uncached_total * 100
    ) if input_tokens_uncached_total > 0 else 0
    cached_token_ratio = (
        cached_tokens_total / input_tokens_cached_total * 100
    ) if input_tokens_cached_total > 0 else 0

    print(f"\n[C10] 결과:")
    print(f"  캐시 ON  — avg latency:{sum(latencies_cached)/len(latencies_cached):.0f}ms, "
          f"cached_tokens:{cached_tokens_total}")
    print(f"  캐시 OFF — avg latency:{sum(latencies_uncached)/len(latencies_uncached):.0f}ms")
    print(f"  비용 절감 (추정):{savings_pct:.1f}% (uncached=${cost_uncached:.4f}, cached=${cost_cached:.4f})")
    print(f"  토큰 감소율:{token_reduction_pct:.1f}% (단가 무관 지표)")
    print(f"  캐시 토큰 비중:{cached_token_ratio:.1f}% (cached/{input_tokens_cached_total} total input)")

    # 캐시 삭제
    client.caches.delete(name=cache.name)

    return {
        "avg_latency_cached": round(sum(latencies_cached)/len(latencies_cached), 1),
        "avg_latency_uncached": round(sum(latencies_uncached)/len(latencies_uncached), 1),
        "cached_tokens_total": cached_tokens_total,
        "cached_token_ratio_pct": round(cached_token_ratio, 1),
        "token_reduction_pct": round(token_reduction_pct, 1),  # [v3.1] 단가 무관 지표
        "savings_pct": round(savings_pct, 1),  # 추정치 (단가 의존)
        "cost_cached": round(cost_cached, 6),
        "cost_uncached": round(cost_uncached, 6),
    }

run_test("C10-prompt-caching", test_c10_caching)
save_test_result("C10", _test_results.get("C10-prompt-caching", {}))
```

**검증 항목**:

| 항목 | 캐시 ON | 캐시 OFF | Pass 기준 |
| --- | --- | --- | --- |
| 캐시 생성/삭제 | ✓/✗ | N/A | 정상 동작 |
| 평균 latency (20회) | ___ms | ___ms | 기록 |
| **[v3 P2] cached_content_token_count 반환** | ✓/✗ (값: ___) | N/A | **캐시 적용 확인** |
| **[v3.1] 캐시 토큰 비중** | ___% | N/A | 기록 (높을수록 효과적) |
| 응답 품질 차이 | ___/8 | ___/8 | 동등 (±0.5) |
| **[v3.1] 토큰 감소율 (단가 무관)** | ___% | — | ≥ 25% |
| **[v3 P2] 비용 절감 효과 (추정)** | ___% | — | 참고치 (단가 변동 가능) |

---

### TEST-X1: API 에러 핸들링

```python
def test_x1_error_handling():
    results = {}

    # 시나리오 1: 존재하지 않는 모델
    try:
        client.models.generate_content(model="gemini-nonexistent", contents="test")
        results["invalid_model"] = "NO_ERROR (unexpected)"
    except Exception as e:
        results["invalid_model"] = f"{type(e).__name__}:{str(e)[:100]}"
        print(f"[잘못된 모델]{type(e).__name__}:{e}")

    # 시나리오 2: 빈 입력
    try:
        client.models.generate_content(model="gemini-2.5-flash", contents="")
        results["empty_input"] = "NO_ERROR (unexpected)"
    except Exception as e:
        results["empty_input"] = f"{type(e).__name__}:{str(e)[:100]}"
        print(f"[빈 입력]{type(e).__name__}:{e}")

    # 시나리오 3: max_output_tokens 초과 설정
    try:
        client.models.generate_content(
            model="gemini-2.5-flash", contents="test",
            config=types.GenerateContentConfig(max_output_tokens=999999)
        )
        results["token_overflow"] = "NO_ERROR (unexpected)"
    except Exception as e:
        results["token_overflow"] = f"{type(e).__name__}:{str(e)[:100]}"
        print(f"[토큰 초과]{type(e).__name__}:{e}")

    # 시나리오 4: 임베딩 배치 크기 초과
    try:
        client.models.embed_content(
            model="gemini-embedding-001", contents=["text"] * 300,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        results["batch_overflow"] = "NO_ERROR (unexpected)"
    except Exception as e:
        results["batch_overflow"] = f"{type(e).__name__}:{str(e)[:100]}"
        print(f"[배치 초과]{type(e).__name__}:{e}")

    # 시나리오 5: Rate Limit 확인
    # [v3 O5] 30회→10회 축소
    errors = []
    for i in range(10):
        try:
            client.models.generate_content(
                model="gemini-2.5-flash", contents=f"Quick test{i}",
                config=types.GenerateContentConfig(max_output_tokens=10)
            )
        except Exception as e:
            errors.append((i, type(e).__name__, str(e)[:100]))
    if errors:
        results["rate_limit"] = f"{len(errors)} errors in 10 calls"
        print(f"10회 연속 호출:{len(errors)} errors")
    else:
        results["rate_limit"] = "429 미도달 (quota 충분)"
        print("10회 연속 호출: 429 미도달 — '도달 못함' 기록")

    # 시나리오 6: Safety filter — 파라미터 수용 + 메타데이터 확인
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
    results["safety_filter"] = f"params_accepted=True, metadata={'✓' if has_safety_meta else '✗'}"
    print(f"[Safety] safety_settings 파라미터 수용: ✓")
    print(f"[Safety] 응답에 safety 메타데이터 포함:{'✓' if has_safety_meta else '✗'}")

    return results

run_test("X1-error-handling", test_x1_error_handling)
save_test_result("X1", _test_results.get("X1-error-handling", {}))
```

**검증 항목**:

| 시나리오 | 기대 동작 | 실제 결과 | Pass 기준 |
| --- | --- | --- | --- |
| 잘못된 모델 ID | 404 / NotFound | ___ | 명확한 에러 |
| 빈 입력 | 400 / InvalidArgument | ___ | 명확한 에러 |
| 토큰 초과 | 400 / InvalidArgument | ___ | 명확한 에러 |
| 임베딩 배치 초과 | 400 / InvalidArgument | ___ | 명확한 에러 |
| Rate Limit (10회) | **429 발생 시**: 확인. **미발생 시**: 기록 | ___ | 관찰치 |
| Safety filter | 파라미터 수용 + 메타데이터 존재 | ___ | 파라미터 정상 수용 |

---

### 결과 종합 및 정리 (Day 3 마무리)

```python
# cost_log.jsonl 기반 비용 집계
summarize_costs()

# [v3 I2] 전체 테스트 결과 저장
save_all_results()
```

### 기능 검증 결과 매트릭스

| 테스트 | 핵심 결과 | 한국어 품질 | 비용 | 판단 |
| --- | --- | --- | --- | --- |
| C1: Gemini API | 스트리밍/비스트리밍 동작, ttft=___ms | ___/8 | $___ | ○/△/× |
| C2: Embeddings | dim=***, 배치 OK, task_type*** /2 | 유사도=___ | $___ | ○/△/× |
| DOC: Document AI | OCR CER=___, Layout 표 인식 | 추출 CER=___ | $___ | ○/△/× |
| MMD: Gemini 멀티모달 | PDF 직접 추출 CER=***, 구조화(5건)*** % | ___/8 | $___ | ○/△/× |
| NER: 엔티티/관계 추출 | 엔티티 F1=___, **관계 F1=*, 정합성=*%** | ___/8 | $___ | ○/△/× |
| E2E: 파이프라인 비교 | 방법 A vs B latency/품질/**정합성** | N/A | $___ | ○/△/× |
| C5: RAG Engine | 인제스트 ___건, **hit@5=___/5** | ___/8 | $___ | ○/△/× |
| VAS: Vertex AI Search | GCS 인덱싱, AI 요약 | ___/8 | $___ | ○/△/× |
| C6: Grounding | 최신 정보 반영 | ___/8 | $___ | ○/△/× |
| C10: Caching | **절감=*%, cached_tokens=*** | ___/8 | $___ | ○/△/× |
| X1: 에러 핸들링 | ___/6 시나리오 확인 | N/A | — | ○/△/× |

### GraphRAG 구축 의사결정 포인트

| 의사결정 | 테스트 근거 | 결론 |
| --- | --- | --- |
| **데이터 수집 방식** | VAS 크롤링(옵션) vs 자체 크롤러 | ___ |
| **PDF 정제 파이프라인** | DOC(방법A) vs MMD(방법B) 비교 | ___ |
| **NER 모델** (Flash vs Pro) | NER F1 + 정합성 차이, 비용 비교 | ___ |
| **NER 프롬프트 전략** | zero-shot vs few-shot F1 | ___ |
| **관계 추출 → 그래프 구축** | 관계 F1 ≥ 0.60 + **entity-relation 정합성 ≥ 90%** | ___ |
| **임베딩 모델 선택** | C2 품질 비교 | ___ |
| **RAG 서비스** | RAG Engine vs VAS (**동일 쿼리 3축 비교**) | ___ |
| **Grounding 추가 적용 여부** | C6 정확도 향상폭 | ___ |
| **Prompt Caching 적용** | C10 비용 절감 ≥ 25% | ___ |
| **기본 LLM 모델** (Flash vs Pro) | C1 품질/비용 비교 | ___ |

### GraphRAG 최종 파이프라인 후보

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

### 리소스 삭제 체크리스트

```
⚠ 모든 리소스에 RUN_ID suffix가 붙어있음 — pending_ops.json에서 RUN_ID 확인 후 삭제.

□ RAG Corpus 삭제 완료 (client.corpora.delete)
  - corpus name: pending_ops.json의 c5_corpus_name
□ RagEngineConfig → Unprovisioned tier 확인
  ⚠ Corpus 삭제 후 마지막에 실행 — Unprovisioned는 복구 불가
□ Prompt Cache 삭제 완료 (테스트 코드에서 자동 삭제)
□ Document AI 프로세서 삭제 (Console)
□ Vertex AI Search 삭제:
  - Engine: pending_ops.json의 vas_engine_id
  - Data Store: pending_ops.json의 vas_store_name
□ GCS 임시 파일 정리 (docai-output 등)
□ 48시간 내 Billing 잔여 비용 확인 + summarize_costs() 추정치와 대조
```

---