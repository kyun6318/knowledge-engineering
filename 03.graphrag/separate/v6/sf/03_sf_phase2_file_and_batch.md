> **산출물 C**: CandidateContext 480K+ JSONL -> GCS -> PubSub (순차, 10K/chunk)
> 

---

## 2-0. 코드 리팩토링 + Provider 추상화 (1주, W7)

### LLM Provider 추상화 레이어

```python
# src/extractors/llm_provider.py
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def extract(self, prompt: str, schema_class: type) -> dict: ...
    @abstractmethod
    async def submit_batch(self, prompts: list[str]) -> str: ...
    @abstractmethod
    async def poll_batch(self, batch_id: str) -> list[dict]: ...

class AnthropicProvider(LLMProvider):
    def __init__(self, model="claude-haiku-4-5"):
        self.model = model
    # ... 구현

class GeminiProvider(LLMProvider):
    """Anthropic 한도 도달 시에만 구현"""
    pass

def get_provider(name: str = "anthropic") -> LLMProvider:
    return {"anthropic": AnthropicProvider, "gemini": GeminiProvider}[name]()
```

---

## 2-1. 파일 파싱 + Hybrid 섹션 분리 (2주, W8-9)

### Hybrid 섹션 분리 전략

`knowledge_graph/01_extraction_pipeline.md` S1

```python
# src/splitters/pattern_splitter.py - §4.1.1
SECTION_PATTERNS = {
    "career": r'(?:경력\s*(?:사항|내역)?|EXPERIENCE|WORK\s*EXPERIENCE|Career)',
    "education": r'(?:학력\s*(?:사항)?|EDUCATION)',
    "skill": r'(?:보유\s*기술|기술\s*스택|SKILLS?|Technical)',
    # ...
}

def split_by_pattern(text: str) -> dict | None:
    sections = {}
    # 패턴 매칭 로직
    if not sections.get("career"):
        return None  # 실패 -> LLM 폴백
    return sections
```

### LLM 폴백 Batch API 처리

`knowledge_graph/01_extraction_pipeline.md` R4

```python
# src/splitters/hybrid_splitter.py
async def hybrid_split_batch(texts: list[dict], provider: LLMProvider) -> list[tuple]:
    results = []
    failed_for_llm = []
    # Step 1: 패턴 기반 (70% 성공)
    for item in texts:
        result = split_by_pattern(item["text"])
        if result:
            results.append((item["person_id"], result, "pattern"))
        else:
            failed_for_llm.append(item)
    # Step 2: 실패분 Batch API LLM 폴백
    if failed_for_llm:
        llm_results = await split_by_llm_batch(failed_for_llm, provider)
        # ...
    return results
```

### 파일 소스 confidence 패널티 (v12 §4.1.2)

```python
SOURCE_CONFIDENCE_CEILING = {
    "db": 0.85, "file_pattern": 0.75, "file_llm": 0.70, "file_fallback": 0.30
}
```

---

## 2-3. 전체 600K Batch 처리 (6주, W10-15)

### R6: 처리 우선순위

```
1차 (W10-12): DB 500K -> 적응형 호출 비율 실측 (v12 M1 80/20 검증)
2차 (W12-15): 파일 100K -> PDF/DOCX/HWP Hybrid 분리 + 투입
```

### 처리 시간 계산 (9주 = 45일)

```
적응형 호출: 1-pass 80% (480K) + N+1 20% (120K, 5.5건/인) -> 총 ~900 chunk
낙관 (6h/라운드): 22.5일 -> 100% 완료
기본 (12h/라운드): 45일 -> 100% 완료
비관 (24h/라운드): 50%, Phase 3 명시적 Batch 할당으로 W22까지 90%+
```

### W10 중간 체크포인트

W10 체크 (DB 500K 1차 Batch 시작 시점):

[] 라운드 시간 실측

[] 18h 초과 시 -> 즉시 비관 대응 발동:
- Phase 3에 명시적 Batch 할당 (2+8 -> 3+7)
- Gemini Flash Batch 병행 검토 (N5 Provider 추상화 활용)
- 주간 싱크에서 GraphRAG 팀에 산출물 지연 가능성 사전 공지

[] 18h 이하 -> 기본 시나리오 유지, W12에 R6 완료율 재확인

---

## 2-4. 자동 품질 메트릭

```python
def run_quality_checks():
    checks = {
        "schema_compliance": check_schema_compliance(),     # >95%
        "required_field_rate": check_required_fields(),     # >90%
        "pii_leak_rate": check_pii_leaks(),                # <0.01%
        "adaptive_call_ratio": check_adaptive_ratio(),
        "dead_letter_rate": check_dead_letter(),            # <5%
    }
    return checks
```

---

## 산출물 C

W9~15 순차:

[] CandidateContext JSONL (10K건/chunk) -> GCS gs://kg-artifacts/candidate/batch_{id}.jsonl

[] PubSub kg-artifact-ready 자동 발행 -> GraphRAG Cloud Run Job 순차 적재

[] 주간 Slack 리포트 (처리 현황)

[JD 파싱 + CompanyContext (Week 17~18)](https://www.notion.so/JD-CompanyContext-Week-17-18-3217d8322b04804dbca7f29d86749202?pvs=21)