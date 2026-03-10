# Phase 2: 파일 이력서 통합 + 전체 처리 (8주, Week 7-14)

> **목적**: Phase 1의 DB 텍스트 기반 Graph에 파일 이력서(PDF/DOCX/HWP)를 통합하고,
> 전체 600K 이력서를 처리하여 에이전트의 검색 범위를 전체 후보자 풀로 확대.
>
> **v2 대비 변경**:
> - N5: LLM provider 추상화 레이어 (Phase 2-0)
> - N8: Neo4j 인스턴스 사이징 — 1,000건 적재 후 메모리 외삽 (Phase 2-2)
> - N9: 잔여 배치 처리 — Phase 3 주간 리포트 준비
> - v12 S1: Hybrid 섹션 분리 (패턴 기반 → LLM 폴백)
> - v12 M1: 적응형 호출 전략 전체 적용 (500K DB + 100K 파일)
> - v12 S2: PII 매핑 GCS CMEK (파일 이력서 확장)
> - v12 S4: 전화번호 8종 정규식 (파일 이력서 PII 탐지)
> - v12 §4.1: 파일 이력서 confidence 패널티 적용
> - 데이터 볼륨: 450K → **600K** (DB 500K + 파일 100K, v12 기준)
>
> **데이터 확장**: DB 텍스트 1,000건 → **전체 600K 중 80%+** (DB + 파일 소스 통합)
> **에이전트 역량 변화**: 1,000건 검색 → **480K+ 전체 후보자 검색**
>
> **인력**: DE 1명 + MLE 1명 풀타임

---

## 2-0. 코드 리팩토링 + ★ Provider 추상화 + 파일 파싱 PoC (1주) — Week 7

### 프로젝트 구조 (v3)

```
src/
├── parsers/              # PDF, DOCX, HWP 파서
├── splitters/            # ★ v12 S1: Hybrid 섹션 분리 (패턴 + LLM 폴백)
│   ├── pattern_splitter.py
│   └── llm_splitter.py
├── pii/                  # ★ v12 S2/S4: PII 마스킹 + GCS CMEK
│   ├── masker.py
│   └── mapping_store.py  # GCS CMEK 저장
├── dedup/                # SimHash 중복 제거
├── extractors/           # Rule 추출, LLM 추출
│   ├── candidate_extractor.py  # ★ v12 M1: 적응형 호출
│   └── llm_provider.py         # ★ N5: Provider 추상화
├── models/               # Pydantic 모델 (v12 §1.3, §2.3)
├── shared/               # 공유 유틸
├── crawlers/             # Phase 1 크롤러 (법무 허용 시)
├── batch/                # Batch API
├── graph/                # Neo4j 적재 (★ v19 관계명)
├── api/                  # GraphRAG REST API (★ N2 PII 필터)
├── quality/              # 품질 메트릭
└── requirements.txt
```

### ★ N5: LLM Provider 추상화 레이어

```python
# src/extractors/llm_provider.py — v3 N5 신규

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

    async def extract(self, prompt, schema_class):
        # Anthropic API 호출 → JSON → Pydantic 검증
        ...

    async def submit_batch(self, prompts):
        # Anthropic Batch API 제출
        ...

class GeminiProvider(LLMProvider):
    """Anthropic 한도 도달 시에만 구현"""
    pass  # Phase 2-0에서 인터페이스만, 구현은 필요 시

def get_provider(name: str = "anthropic") -> LLMProvider:
    return {"anthropic": AnthropicProvider, "gemini": GeminiProvider}[name]()
```

> **BigQuery 확장**: batch_tracking.api_provider 컬럼 활용

---

## 2-1. 파일 파싱 + 전처리 확장 (2주) — Week 8-9

### ★ v12 S1: Hybrid 섹션 분리 전략

```python
# src/splitters/pattern_splitter.py — v12 §4.1.1

SECTION_PATTERNS = {
    "career": r'(?:경력\s*(?:사항|내역)?|EXPERIENCE|WORK\s*EXPERIENCE|Career)',
    "education": r'(?:학력\s*(?:사항)?|EDUCATION)',
    "skill": r'(?:보유\s*기술|기술\s*스택|SKILLS?|Technical)',
    "introduction": r'(?:자기\s*소개서?|ABOUT\s*ME|SUMMARY|PROFILE)',
    "project": r'(?:프로젝트|PROJECT)',
    "certificate": r'(?:자격증|자격\s*사항|CERTIFICATION)',
}

CAREER_SEPARATOR_PATTERNS = [
    r'(?P<company>.+?)\s*[\|·/]\s*(?P<period>\d{4}[\.\-/]\d{1,2}\s*[~\-–]\s*(?:\d{4}[\.\-/]\d{1,2}|현재|재직중))',
    r'(?P<period>\d{4}[\.\-/]\d{1,2}\s*[~\-–]\s*(?:\d{4}[\.\-/]\d{1,2}|현재|재직중))\s*[\|·/]\s*(?P<company>.+)',
    r'(?P<company>.+?)\s+(?P<position>.+?)\s+(?P<period>\d{4}\.\d{2}\s*[~\-]\s*\d{4}\.\d{2})',
]

def split_by_pattern(text: str) -> dict | None:
    """패턴 기반 섹션 분리 (비용 $0, <1s)"""
    sections = {}
    # ... 패턴 매칭 로직
    if not sections.get("career"):
        return None  # 실패 → LLM 폴백
    return sections
```

```python
# src/splitters/llm_splitter.py — v12 §4.1.1 LLM 폴백

async def split_by_llm(text: str, provider: LLMProvider) -> dict:
    """LLM 기반 섹션 분리 (비용 ~$0.002/건, 30% 대상)"""
    prompt = f"""[System] You are a resume parser. Split the resume text into career blocks.
[User] 아래 이력서 텍스트에서 각 경력(Career)을 구분하여 JSON 배열로 반환하세요.
각 Career에는 company, period, role, details를 포함하세요.
경력을 구분할 수 없으면 전체를 단일 Career로 반환하세요.

{text}"""
    return await provider.extract(prompt, list)
```

```python
# src/splitters/hybrid_splitter.py — v12 §4.1.1 Hybrid 전략

async def hybrid_split(text: str, provider: LLMProvider) -> tuple[dict, str]:
    """Hybrid 접근: 패턴 → LLM 폴백"""
    # Step 1: 패턴 기반 (70% 성공 예상)
    result = split_by_pattern(text)
    if result:
        return result, "pattern"

    # Step 2: LLM 폴백 (30% 대상)
    result = await split_by_llm(text, provider)
    if result:
        return result, "llm"

    # Step 3: 최종 실패 → 전체를 단일 Career로 취급
    return {"career": [{"company": "unknown", "details": text}]}, "fallback"
```

### ★ v12 §4.1.2: 파일 소스 confidence 패널티

```python
# 파일 추출 시 normalization_confidence 상한 적용
SOURCE_CONFIDENCE_CEILING = {
    "db": 0.85,           # DB 소스
    "file_pattern": 0.75, # 파일 소스 (패턴 분리 성공)
    "file_llm": 0.70,     # 파일 소스 (LLM 분리)
    "file_fallback": 0.30, # 분리 실패, 단일 Career
}
```

### 주 단위 마일스톤

```
Week 8: 파서 구현 + ★ Hybrid 섹션 분할
  DE:  PDF/DOCX 파서 모듈 + HWP 파서 모듈
  MLE: ★ Hybrid 섹션 분리 (패턴 + LLM 폴백, v12 S1) + 경력 블록 분리기
  목표: 각 포맷 100건 테스트 통과, 패턴 성공률 70%+ 검증

Week 9: 전처리 확장 + 인프라
  DE:  SimHash 대규모 중복 제거 + Docker + Job 등록
  MLE: PII 마스킹 offset mapping (★ GCS CMEK) + 기술/회사 사전 확장
  목표: 전체 파이프라인 E2E 1,000건 테스트 통과
```

### Cloud Run Jobs 등록

> v2와 동일 (kg-parse-resumes tasks=50, kg-graph-load tasks≤5).

---

## 2-2. Neo4j Professional 전환 + ★ 사이징 검증 (1일+) — Week 10 시작

### ★ N8: 1,000건 적재 후 인스턴스 사이징 외삽

```python
# 사이징 검증 절차 (N8)

def estimate_neo4j_sizing():
    """1,000건 적재 후 메모리 사용량 외삽"""
    # Step 1: 1,000건 적재
    load_candidates_batch(driver, sample_1000)

    # Step 2: 메모리 사용량 측정
    result = session.run("""
        CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Store sizes')
        YIELD attributes
        RETURN attributes
    """)
    store_size = result  # 바이트 단위

    # Step 3: 600K 외삽
    estimated_total = store_size * 600  # 1K → 600K
    vector_index_size = 1_800_000 * 768 * 4  # 1.8M chapters × 768d × 4byte ≈ 5.5GB

    total_estimated = estimated_total + vector_index_size

    # Step 4: 인스턴스 결정
    if total_estimated < 8 * 1024**3:
        return "8GB ($65/월)"
    elif total_estimated < 16 * 1024**3:
        return "16GB (~$130/월)"
    elif total_estimated < 32 * 1024**3:
        return "32GB (~$260/월)"
    else:
        return "★ $200 초과 대응: Vector Index 분리 or 768d→384d 차원 축소"
```

> **$200/월 초과 시 대응 방안** (N8):
> - Vector Index를 별도 서비스로 분리 (Vertex AI Vector Search)
> - 768d → 384d 차원 축소 (PCA, 품질 검증 필요)
> - 노드 속성 최소화 (불필요 속성 제거)

---

## 2-3. 전체 600K Batch 처리 (5주) — Week 10-14

> v2 기반 + ★ v12 적응형 호출 + 600K 볼륨.

### 처리 시간 계산 (v3: 600K)

```
총 이력서 수: 600,000건 (DB 500K + 파일 100K)
Batch API chunk 크기: 1,000건/chunk
필요한 chunk 수: 600개 (v2: 450개)

★ 적응형 호출 반영:
  - 1-pass (80%): 480K × 1건/이력서 = 480K 호출
  - N+1 pass (20%): 120K × 평균 5.5건/이력서 = 660K 호출
  - 총 호출 수: ~1,140K (v2: 450K 단순 호출)
  - Batch chunk 수: ~1,140개

동시 실행: 10 batch
라운드 수: 114 라운드

시나리오별 소요:
  낙관 (6h/라운드): 28.5일 → 100% 완료, 여유 6.5일
  기본 (12h/라운드): 57일 → 61%, Phase 3 백그라운드 필요    ← ★ 600K는 타이트
  비관 (24h/라운드): 114일 → 31%, 심각한 미달

★ 대응 전략 (600K 볼륨):
  - Batch chunk 크기 1,000 → 2,000으로 확대 (라운드 수 절반)
  - 1-pass 건은 chunk 크기 2,000, N+1 pass 건은 1,000 유지
  - 조정 후: 라운드 수 ~800개, 80 라운드
  - 기본 시나리오: 40일 → 87% 완료 ✓

Graph 적재: UNWIND 배치 (v2 유지)
```

### ★ N9: 잔여 배치 처리 준비

```sql
-- Phase 3 주간 리포트용 쿼리 (N9)
SELECT
  DATE(processed_at) AS week_start,
  COUNT(*) AS processed,
  COUNTIF(status = 'SUCCESS') AS success,
  COUNTIF(status = 'FAILED') AS failed,
  SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) AS remaining
FROM graphrag_kg.batch_tracking
GROUP BY week_start
ORDER BY week_start DESC;

-- Batch API 할당 계획 (Phase 3 진입 후)
-- Phase 3 작업: 최소 2 batch 예약
-- 잔여 처리: 나머지 batch 할당
```

---

## 2-4. 자동 품질 메트릭 + 벤치마크 (v2 유지 + v12 메트릭)

### 자동 품질 체크 (★ v12 §3 메트릭 반영)

```python
def run_quality_checks_v3():
    """v3 품질 검사 — v12 품질 메트릭 포함"""
    checks = {
        "schema_compliance": check_schema_compliance(),     # 목표: ≥95%
        "required_field_rate": check_required_fields(),     # 목표: ≥90%
        "skill_code_match_rate": check_skill_matching(),    # ★ v12: ≥70%
        "embedding_coverage": check_embedding_coverage(),   # ★ v12: ≥85%
        "pii_leak_rate": check_pii_leaks(),                # ★ v12: ≤0.01%
        "dead_letter_rate": check_dead_letter(),            # ★ v12: <5%
        "distribution_anomaly": check_distribution(),
        "adaptive_call_ratio": check_adaptive_ratio(),      # ★ v12 M1: 1-pass/N+1 비율
    }
    return checks
```

### 쿼리 성능 벤치마크

> v2와 동일 (Cypher 5종 × 480K+ 데이터, p95 < 2초).

---

## 버퍼 1주 — Week 15

### Phase 2 → Phase 3 Go/No-Go 판정 (v3)

```
평가 기준:

1. 완료도 평가
   ├─ 처리량: 목표 80%+ (480K+)
   ├─ 파싱 성공률: 목표 95%+
   ├─ CER (HWP): ≤ 0.15
   └─ ★ Hybrid 섹션 분리 성공률: 패턴 70%+ (v12 S1)

2. 자동 품질 평가
   ├─ schema 준수율: 95%+
   ├─ 필수 필드 완성도: 90%+
   ├─ ★ skill_code_match_rate: 70%+ (v12)
   ├─ ★ pii_leak_rate: ≤0.01% (v12)
   ├─ 통계적 샘플링 384건 결과
   └─ 분포 이상 없음

3. 쿼리 성능 벤치마크
   ├─ Cypher 5종 × 480K+ 데이터
   ├─ p95 < 2초
   └─ 미달 시: 복합 인덱스 추가

4. ★ Neo4j 사이징 확정 (N8)
   ├─ 인스턴스 크기 확정 + 안정 동작 확인
   └─ $200/월 초과 시 대응 방안 실행 여부

5. ★ 잔여 배치 자동화 (N9)
   ├─ 잔여 처리 자동화 확인
   └─ Phase 3 리소스 충돌 없음 확인

6. Neo4j 백업
   ├─ 스냅샷 백업 완료
   └─ 노드/엣지 수 기록
```

---

## Phase 2 완료 산출물

```
□ 파일 파싱 모듈
  ★ Hybrid 섹션 분리 (패턴 70%+ / LLM 폴백 30%) (v12 S1)
  ★ 파일 소스 confidence 패널티 적용 (v12 §4.1.2)

□ 전처리 확장 모듈
  ★ PII 매핑 GCS CMEK 확장 (파일 이력서) (v12 S2)
  ★ 전화번호 8종 정규식 (파일 이력서) (v12 S4)

□ ★ LLM Provider 추상화 레이어 (N5)
  ├─ AnthropicProvider 구현
  ├─ GeminiProvider 인터페이스 (필요 시 구현)
  └─ batch_tracking.api_provider 컬럼

□ 인프라 전환
  ├─ Neo4j Professional (Vector Index 768d)
  ├─ ★ 인스턴스 사이징 검증 완료 (N8)
  ├─ Graph 적재 Job tasks ≤ 5
  └─ UNWIND 배치 적재 + 버전 태그

□ 전체 데이터 처리 (600K 이력서)
  ├─ 목표: 80%+ (480K+)
  ├─ ★ 적응형 호출: 1-pass 80% / N+1 pass 20% (v12 M1)
  ├─ 잔여: Phase 3 백그라운드 + ★ 주간 리포트 준비 (N9)
  └─ Graph 적재: UNWIND 배치

□ 자동 품질 메트릭
  ├─ ★ v12 메트릭 포함 (skill_match, embedding_coverage, pii_leak)
  ├─ 통계적 샘플링 384건
  └─ BigQuery quality_metrics

□ 쿼리 성능 벤치마크
□ Regression 테스트 (Golden 50건)
□ Go/No-Go 판정
```

---

## 예상 비용 (Phase 2, 8주)

| 항목 | v3 비용 | v2 대비 |
|------|--------|---------|
| Anthropic Batch API (600K, ★ 적응형 호출) | ~$1,488 | +$138 (v12 M1 + 100K 추가) |
| Anthropic API (재처리/에러) | ~$30 | +$5 |
| ★ 파일 섹션 분리 LLM 폴백 (30K건) | ~$60 | 신규 (v12 S1) |
| Vertex AI Embedding | ~$52 | +$2 |
| Neo4j Professional (8주) | $200~480 | 동일 |
| Cloud Run Jobs | ~$75 | +$5 |
| GCS + BigQuery | ~$27 | +$2 |
| 기타 | ~$18 | +$2 |
| **Phase 2 합계** | **$1,950~2,230** | +$167~187 |
