# Phase 2: 파일 이력서 통합 + 전체 처리 (★ 9주, Week 7-15)

> **목적**: Phase 1의 DB 텍스트 기반 Graph에 파일 이력서(PDF/DOCX/HWP)를 통합하고,
> 전체 600K 이력서를 처리하여 에이전트의 검색 범위를 전체 후보자 풀로 확대.
>
> **v4 대비 변경**:
> - ★ v5 A3: AuraDB Free→Professional 마이그레이션 절차 명시 (Cypher 복사 방식)
>
> **v3 대비 변경 (v4에서 반영 완료)**:
> - R4: Hybrid 섹션 분리 LLM 폴백도 Batch API로 묶어 처리
> - R5: Phase 2 기간 8주 → 9주
> - R6: 처리 우선순위 전략 — DB 500K 먼저 → 파일 100K 후순위
> - 비관 시나리오 대응 계획 보강
>
> **데이터 확장**: DB 텍스트 1,000건 → **전체 600K 중 80%+** (DB + 파일 소스 통합)
> **에이전트 역량 변화**: 1,000건 검색 → **480K+ 전체 후보자 검색**
>
> **인력**: DE 1명 + MLE 1명 풀타임

---

## 2-0. 코드 리팩토링 + Provider 추상화 + 파일 파싱 PoC (1주) — Week 7

### 프로젝트 구조 (v3 유지)

```
src/
├── parsers/              # PDF, DOCX, HWP 파서
├── splitters/            # v12 S1: Hybrid 섹션 분리 (패턴 + LLM 폴백)
│   ├── pattern_splitter.py
│   └── llm_splitter.py
├── pii/                  # v12 S2/S4: PII 마스킹 + GCS CMEK
│   ├── masker.py         # ★ v4 R1: re.sub 콜백 방식
│   └── mapping_store.py  # GCS CMEK 저장
├── dedup/                # SimHash 중복 제거
├── extractors/           # Rule 추출, LLM 추출
│   ├── candidate_extractor.py  # v12 M1: 적응형 호출
│   └── llm_provider.py         # N5: Provider 추상화
├── models/               # Pydantic 모델 (v12 §1.3, §2.3)
├── shared/               # 공유 유틸
├── crawlers/             # Phase 1 크롤러 (법무 허용 시)
├── batch/                # Batch API
├── graph/                # Neo4j 적재 (v19 관계명)
├── api/                  # GraphRAG REST API (N2 PII 필터)
├── quality/              # 품질 메트릭
└── requirements.txt
```

### N5: LLM Provider 추상화 레이어

```python
# src/extractors/llm_provider.py — N5

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

> **구현 범위**: 인터페이스 + Anthropic 구현만. 추가 확장(라우팅, 품질 기반 동적 분배) 자제.

---

## 2-1. 파일 파싱 + 전처리 확장 (2주) — Week 8-9

### v12 S1: Hybrid 섹션 분리 전략

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

### ★ v4 R4: LLM 폴백을 Batch API로 묶어 처리

```python
# src/splitters/llm_splitter.py — v4 R4: Batch API 지원

async def split_by_llm_single(text: str, provider: LLMProvider) -> dict:
    """단일 건 LLM 섹션 분리 (개별 호출, 긴급용)"""
    prompt = f"""[System] You are a resume parser. Split the resume text into career blocks.
[User] 아래 이력서 텍스트에서 각 경력(Career)을 구분하여 JSON 배열로 반환하세요.
각 Career에는 company, period, role, details를 포함하세요.
경력을 구분할 수 없으면 전체를 단일 Career로 반환하세요.

{text}"""
    return await provider.extract(prompt, list)


async def split_by_llm_batch(failed_texts: list[dict], provider: LLMProvider) -> list[dict]:
    """★ v4 R4: LLM 폴백 건을 Batch API로 묶어 처리

    v3에서는 개별 호출만 설계 → 30K건 × 2초/건 = ~15시간
    v4에서는 Batch API 활용 → 30K건 chunk 1,000 = 30 batch → 수 시간
    """
    prompts = []
    for item in failed_texts:
        prompts.append({
            "person_id": item["person_id"],
            "prompt": f"""[System] You are a resume parser. Split the resume text into career blocks.
[User] 아래 이력서 텍스트에서 각 경력(Career)을 구분하여 JSON 배열로 반환하세요.
각 Career에는 company, period, role, details를 포함하세요.
경력을 구분할 수 없으면 전체를 단일 Career로 반환하세요.

{item['text']}"""
        })

    # Batch API로 제출
    batch_id = await provider.submit_batch([p["prompt"] for p in prompts])
    results = await provider.poll_batch(batch_id)

    return results
```

```python
# src/splitters/hybrid_splitter.py — v4: Batch 통합 Hybrid 전략

async def hybrid_split_batch(texts: list[dict], provider: LLMProvider) -> list[tuple[dict, str]]:
    """Hybrid 접근: 패턴 일괄 시도 → 실패분만 LLM Batch 폴백"""
    results = []
    failed_for_llm = []

    # Step 1: 패턴 기반 (70% 성공 예상)
    for item in texts:
        result = split_by_pattern(item["text"])
        if result:
            results.append((item["person_id"], result, "pattern"))
        else:
            failed_for_llm.append(item)

    # Step 2: ★ v4 R4: 실패분을 Batch API로 묶어 LLM 폴백
    if failed_for_llm:
        llm_results = await split_by_llm_batch(failed_for_llm, provider)
        for item, llm_result in zip(failed_for_llm, llm_results):
            if llm_result:
                results.append((item["person_id"], llm_result, "llm"))
            else:
                # Step 3: 최종 실패 → 전체를 단일 Career로 취급
                results.append((item["person_id"],
                    {"career": [{"company": "unknown", "details": item["text"]}]},
                    "fallback"))

    return results
```

> **★ v4 R4 효과**:
> - v3: 30K건 개별 호출 → ~15시간 (2초/건)
> - v4: 30K건 Batch API → ~수 시간 (chunk 1,000 × 30 batch)
> - Phase 2 타이트한 일정(R5)에서 추가 병목 방지

### v12 §4.1.2: 파일 소스 confidence 패널티

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
Week 8: 파서 구현 + Hybrid 섹션 분할
  DE:  PDF/DOCX 파서 모듈 + HWP 파서 모듈
  MLE: Hybrid 섹션 분리 (패턴 + ★ LLM 폴백 Batch화, R4) + 경력 블록 분리기
  목표: 각 포맷 100건 테스트 통과, 패턴 성공률 70%+ 검증
  ★ v4: 패턴 성공률 50% 미만이면 패턴 개선에 1일 투자 (R4 연계)

Week 9: 전처리 확장 + 인프라
  DE:  SimHash 대규모 중복 제거 + Docker + Job 등록
  MLE: PII 마스킹 offset mapping (GCS CMEK) + 기술/회사 사전 확장
  목표: 전체 파이프라인 E2E 1,000건 테스트 통과
```

---

## 2-2. Neo4j Professional 전환 + 사이징 검증 (1일+) — Week 10 시작

### ★ v5 A3: AuraDB Free → Professional 마이그레이션 절차

```
AuraDB Free → Professional 마이그레이션 (★ v5 A3):

AuraDB Free는 "업그레이드"가 아닌 별도 인스턴스 생성이 필요.
AuraDB Free에서는 neo4j-admin dump가 불가(관리자 접근 제한).

마이그레이션 절차 (~30분, 1,000건 규모):
  1. Professional 인스턴스 생성 (사이징 결과 기반)
  2. Cypher 쿼리로 기존 Free 인스턴스에서 노드/관계 읽기
  3. 새 인스턴스에 UNWIND 배치 적재 (기존 load_candidates_batch 재활용)
  4. Vector Index 재생성 + Embedding 재적재
  5. 연결 정보 업데이트 (URI, 인증)
  6. API + Scheduler 연결 대상 변경
  7. Free 인스턴스 삭제

1,000건 수준이므로 APOC.export 없이 Cypher 복사로 충분.
```

### N8: 1,000건 적재 후 인스턴스 사이징 외삽

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

---

## 2-3. 전체 600K Batch 처리 (★ 6주) — Week 10-15

> v3 기반 + ★ v4 R5(+1주)/R6(우선순위).

### ★ R6: 처리 우선순위 전략

```
★ v4 R6: DB 500K 먼저 → 파일 100K 후순위

Phase   주차      대상          목표
────────────────────────────────────────────────
1차    W10-12    DB 500K       DB 데이터 우선 처리
                               ★ 적응형 호출 비율 실측 (v12 M1 80/20 가정 검증)
                               ★ DB 데이터 처리 성공률/처리 속도 확정
────────────────────────────────────────────────
2차    W12-15    파일 100K     PDF/DOCX/HWP 순차 투입
                               ★ Hybrid 섹션 분리 패턴 성공률 최종 확인
                               ★ DB 완료 후 파이프라인 안정 상태에서 진행
────────────────────────────────────────────────

우선순위 전략 근거:
  - DB 500K는 텍스트 품질이 높고 패턴 분리 불필요 → 처리 속도 예측 가능
  - 파일 100K는 Hybrid 분리, 포맷 다양성 등 불확실성이 높음
  - DB 먼저 처리하면 적응형 호출 실측 비율로 비용/시간 재산정 가능
  - W12 시점에서 DB 500K 완료율로 파일 100K 처리 가능 범위 판단
```

### 처리 시간 계산 (v4: 600K, 9주)

```
총 이력서 수: 600,000건 (DB 500K + 파일 100K)
Batch API chunk 크기: 2,000건 (1-pass) / 1,000건 (N+1 pass)

★ 적응형 호출 반영:
  - 1-pass (80%): 480K × 1건/이력서 = 480K 호출 → 240 chunk (2K)
  - N+1 pass (20%): 120K × 평균 5.5건/이력서 = 660K 호출 → 660 chunk (1K)
  - 총 chunk: ~900개
  - 동시 실행: 10 batch → 90 라운드

시나리오별 소요 (★ v4: 9주 = 45일 기준):
  낙관 (6h/라운드):  22.5일 → 100% 완료, 여유 22.5일       ★ 충분
  기본 (12h/라운드): 45일   → 100% 완료, 여유 0일          ★ v4: 87%→100% (R5)
  비관 (24h/라운드): 90일   → 50%, Phase 3 백그라운드 필요   ★ v3(44%)보다 개선

★ v4 개선 (v3 대비):
  - 기본 시나리오: v3 87%(여유 0일) → v4 100%(여유 0일, 기간 내 완료)
  - 비관 시나리오: v3 44% → v4 50% (+6%)
  - R6 우선순위: DB 500K를 먼저 처리하므로 비관 시에도 DB는 80%+ 달성 가능
```

### ★ 비관 시나리오 대응 계획 (v4 보강)

```
비관 시나리오 (50% 완료, 잔여 300K):

  Phase 3 백그라운드 처리가 아닌 ★ 명시적 배치 할당 계획:

  Week 17-18 (Phase 3 초반):
    ├─ Phase 3 전용 Batch: 2 batch (JD/CompanyContext 추출)
    ├─ 잔여 처리 전용 Batch: 8 batch (잔여 300K 소화)
    └─ 예상 소화량: 8 batch × 14일 = ~140K 건

  Week 19-22 (Phase 3 중반~후반):
    ├─ Phase 3 전용 Batch: 3 batch (MAPPED_TO 계산 등)
    ├─ 잔여 처리 전용 Batch: 7 batch
    └─ 예상 소화량: 7 batch × 28일 = ~160K 건

  총 추가 소화: ~300K 건 → 비관 시나리오에서도 Week 22까지 90%+ 완료

  ★ 핵심: "Phase 3 백그라운드"가 아닌 Batch API 할당을 Phase 3 초반에 명시적 배치
```

### N9: 잔여 배치 처리 준비

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
```

---

## 2-4. 자동 품질 메트릭 + 벤치마크 (v3 유지 + v12 메트릭)

### 자동 품질 체크

```python
def run_quality_checks():
    """품질 검사 — v12 품질 메트릭 포함"""
    checks = {
        "schema_compliance": check_schema_compliance(),     # 목표: ≥95%
        "required_field_rate": check_required_fields(),     # 목표: ≥90%
        "skill_code_match_rate": check_skill_matching(),    # v12: ≥70%
        "embedding_coverage": check_embedding_coverage(),   # v12: ≥85%
        "pii_leak_rate": check_pii_leaks(),                # v12: ≤0.01%
        "dead_letter_rate": check_dead_letter(),            # v12: <5%
        "distribution_anomaly": check_distribution(),
        "adaptive_call_ratio": check_adaptive_ratio(),      # v12 M1: 1-pass/N+1 비율
    }
    return checks
```

---

## 버퍼 1주 — Week 16

### Phase 2 → Phase 3 Go/No-Go 판정

```
평가 기준:

1. 완료도 평가
   ├─ 처리량: 목표 80%+ (480K+)
   ├─ ★ v4 R6: DB 500K 중 90%+ 필수, 파일은 별도 추적
   ├─ 파싱 성공률: 목표 95%+
   ├─ CER (HWP): ≤ 0.15
   └─ Hybrid 섹션 분리 성공률: 패턴 70%+ (v12 S1)

2. 자동 품질 평가
   ├─ schema 준수율: 95%+
   ├─ 필수 필드 완성도: 90%+
   ├─ skill_code_match_rate: 70%+ (v12)
   ├─ pii_leak_rate: ≤0.01% (v12)
   ├─ 통계적 샘플링 384건 결과
   └─ 분포 이상 없음

3. 쿼리 성능 벤치마크
   ├─ Cypher 5종 × 480K+ 데이터
   ├─ p95 < 2초
   └─ 미달 시: 복합 인덱스 추가

4. Neo4j 사이징 확정 (N8)
   ├─ 인스턴스 크기 확정 + 안정 동작 확인
   └─ $200/월 초과 시 대응 방안 실행 여부

5. 잔여 배치 자동화 (N9)
   ├─ 잔여 처리 자동화 확인
   ├─ ★ v4: Phase 3 Batch API 할당 계획 수립 완료
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
  ★ v4 R4: LLM 폴백 Batch API 처리
  ★ 파일 소스 confidence 패널티 적용 (v12 §4.1.2)

□ 전처리 확장 모듈
  ★ PII 매핑 GCS CMEK 확장 (파일 이력서) (v12 S2)
  ★ 전화번호 8종 정규식 (파일 이력서) (v12 S4)
  ★ v4 R1: PII 마스킹 re.sub 콜백 방식

□ LLM Provider 추상화 레이어 (N5)
  ├─ AnthropicProvider 구현
  ├─ GeminiProvider 인터페이스 (필요 시 구현)
  └─ batch_tracking.api_provider 컬럼

□ 인프라 전환
  ├─ Neo4j Professional (Vector Index 768d)
  ├─ 인스턴스 사이징 검증 완료 (N8)
  ├─ Graph 적재 Job tasks ≤ 5
  └─ UNWIND 배치 적재 + 버전 태그

□ 전체 데이터 처리 (600K 이력서, ★ 9주)
  ├─ 목표: 80%+ (480K+)
  ├─ ★ v4 R6: DB 500K 우선 처리, 파일 100K 후순위
  ├─ 적응형 호출: 1-pass 80% / N+1 pass 20% (v12 M1)
  ├─ 잔여: ★ v4: 비관 시나리오 시 Phase 3 명시적 Batch 할당
  └─ Graph 적재: UNWIND 배치

□ 자동 품질 메트릭
  ├─ v12 메트릭 포함 (skill_match, embedding_coverage, pii_leak)
  ├─ 통계적 샘플링 384건
  └─ BigQuery quality_metrics

□ 쿼리 성능 벤치마크
□ Regression 테스트 (Golden 50건)
□ Go/No-Go 판정
```

---

## 예상 비용 (Phase 2, ★ 9주)

> 상세 비용은 `06_cost_and_monitoring.md` §1.3 참조 (R2: Single Source of Truth).

| 항목 | v4 비용 | v3 대비 |
|------|--------|---------|
| Anthropic Batch API (600K, 적응형 호출) | ~$1,488 | 동일 |
| Anthropic API (재처리/에러) | ~$30 | 동일 |
| ★ 파일 섹션 분리 LLM 폴백 (30K건, **Batch API**) | ~$60 | ★ v4 R4: 개별→Batch |
| Vertex AI Embedding | ~$52 | 동일 |
| Neo4j Professional (**9주**) | $225~540 | +$25~60 (★ R5: +1주) |
| Cloud Run Jobs | ~$84 | +$9 (★ +1주) |
| GCS + BigQuery | ~$30 | +$3 (★ +1주) |
| 기타 | ~$20 | +$2 |
| **Phase 2 합계** | **$1,989~2,304** | +$39~74 |
