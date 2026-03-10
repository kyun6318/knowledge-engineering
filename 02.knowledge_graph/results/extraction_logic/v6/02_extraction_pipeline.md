# v10 온톨로지 기반 추출 파이프라인 설계

> v10 CompanyContext / CandidateContext / Graph Schema에 정합하는 추출 파이프라인.
> v1의 "범용 NER/RE" 접근을 폐기하고, 도메인 특화 Context 생성 파이프라인으로 재설계한다.
>
> 작성일: 2026-03-08 (v2 기반)
> 개정일: 2026-03-08 (v6 — v10 온톨로지 정합: Industry 노드, Embedding 확정, REQUIRES_ROLE/MAPPED_TO 엣지, source tier, ScopeType 변환)

---

## 0. 설계 원칙

| 원칙 | 설명 |
|---|---|
| **v10 스키마 정합** | 추출 결과가 v10 JSON 스키마(CompanyContext, CandidateContext)에 직접 매핑 |
| **Rule-first, LLM-for-reasoning** | 정형/팩트 필드는 Rule/Lookup, 추론/해석 필드는 LLM |
| **Graceful Degradation** | null 허용 필드 명시, 비활성 피처 자동 처리 |
| **Evidence 필수** | 모든 추출에 source_id + span + confidence 첨부 |
| **비용 현실주의** | LLM 의존도를 인정하되 최적화 전략 적용 |
| **Fail-safe** | 에러 유형별 retry/skip/fallback 정책으로 대량 처리 안정성 확보 |
| **Idempotency** | 동일 입력의 재처리가 Graph 데이터를 오염시키지 않음 (v5 추가) |
| **Source Tier Confidence** | `field_confidence = min(extraction_confidence, source_ceiling)` 규칙 적용 **(v6 변경 M-4)** |

---

## 1. 파이프라인 전체 구조

```
[데이터 소스]
├─ JD (자사 보유 / 크롤링)
├─ NICE 기업 정보 DB
├─ 이력서 (자사 보유)
├─ NICE 업종코드 마스터 (v6 추가 H-1)
└─ (향후) 크롤링 / 투자DB

    ▼

[Pipeline A: CompanyContext 생성]
    JD + NICE → CompanyContext JSON
    ├─ company_profile (NICE Lookup)
    ├─ stage_estimate (Rule + LLM)
    ├─ vacancy + role_expectations (LLM 통합 추출)
    ├─ operating_model (키워드 + LLM)
    ├─ domain_positioning (Optional, v6 추가 L-3)
    │   ├─ market_segment: Optional[str]
    │   ├─ competitive_landscape: Optional[str]
    │   └─ product_description: Optional[str]
    └─ structural_tensions (크롤링 데이터 확보 시 활성화, v6 추가 H-4)

    ▼

[Pipeline B: CandidateContext 생성]
    이력서 + NICE → CandidateContext JSON
    ├─ 중복 감지 + canonical 선택 (v5 추가)
    ├─ experiences[] 추출 (Rule + LLM)
    │   ├─ 기본 정보 (Rule)
    │   ├─ scope_type, outcomes (LLM)
    │   ├─ situational_signals (LLM + taxonomy)
    │   └─ past_company_context (NICE Lookup)
    ├─ role_evolution (LLM)
    └─ domain_depth (LLM)

    ▼

[Pipeline C: Graph 적재]
    CompanyContext + CandidateContext → Neo4j
    ├─ Industry 마스터 노드 사전 적재 (v6 추가 H-1)
    ├─ Deterministic ID 생성 (v5 추가)
    ├─ 노드 생성 — 전체 MERGE 기반 (v5 변경)
    ├─ 관계 생성 (HAS_CHAPTER, OCCURRED_AT, IN_INDUSTRY, REQUIRES_ROLE, ...)
    └─ Vector Index 업데이트

    ▼

[Pipeline D: MappingFeatures 계산]
    CompanyContext × CandidateContext → MappingFeatures JSON
    ├─ stage_match (Rule)
    ├─ vacancy_fit (Rule + lookup)
    ├─ domain_fit (Embedding)
    ├─ culture_fit (Rule, 대부분 INACTIVE)
    ├─ role_fit (Rule + LLM + ScopeType 변환, v6 변경 M-2)
    └─ MAPPED_TO 그래프 반영 (v6 추가 H-6)

    ▼

[Pipeline E: 서빙]
    MappingFeatures → BigQuery 테이블
    └─ MAPPED_TO 그래프 반영 (v6 추가 H-6)
```

### 1.1 structural_tensions Pydantic 스키마 **(v6 신설 H-4)**

> structural_tensions는 크롤링 데이터(뉴스, 채용 포탈 리뷰, 투자DB 등)가 확보되었을 때 활성화된다.
> JD 단독으로는 추출하지 않으며, 크롤링 소스가 연결되면 아래 8-type taxonomy 기반으로 추출한다.

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class StructuralTensionType(str, Enum):
    """(v6 신설) 8-type structural tension taxonomy"""
    TECH_DEBT_VS_FEATURES = "tech_debt_vs_features"
    SPEED_VS_RELIABILITY = "speed_vs_reliability"
    FOUNDER_VS_PROFESSIONAL_MGMT = "founder_vs_professional_mgmt"
    EFFICIENCY_VS_GROWTH = "efficiency_vs_growth"
    SCALING_LEADERSHIP = "scaling_leadership"
    INTEGRATION_TENSION = "integration_tension"
    BUILD_VS_BUY = "build_vs_buy"
    PORTFOLIO_RESTRUCTURING = "portfolio_restructuring"

class StructuralTension(BaseModel):
    """(v6 신설) 개별 structural tension 인스턴스"""
    tension_type: StructuralTensionType
    description: str = Field(..., description="구조적 긴장의 구체적 서술")
    evidence_span: str = Field(..., description="크롤링 소스 원문 인용")
    source_id: str = Field(..., description="크롤링 소스 식별자")
    confidence: float = Field(..., ge=0.0, le=1.0)

class DomainPositioning(BaseModel):
    """(v6 신설 L-3) domain_positioning 3개 하위 필드"""
    market_segment: Optional[str] = None
    competitive_landscape: Optional[str] = None
    product_description: Optional[str] = None

class CompanyContextExtended(BaseModel):
    """(v6 변경) Pipeline A 출력 스키마에 추가된 필드들"""
    # ... 기존 필드 생략 ...
    domain_positioning: Optional[DomainPositioning] = None  # (v6 신설 L-3)
    structural_tensions: Optional[List[StructuralTension]] = None  # (v6 신설 H-4)
```

**크롤링 데이터 활성화 경로** **(v6 신설 H-4)**:

```
[크롤링 데이터 확보 시 활성화 경로]

1. 크롤링 소스 연결 (뉴스/리뷰/투자DB)
   │
   ├─ source_type 태깅: "news" / "review" / "investment_db"
   │
   ▼
2. LLM 추출 (structural_tensions 전용 프롬프트)
   │
   ├─ 8-type taxonomy에서 해당 tension만 추출
   ├─ evidence_span 필수 (원문 인용)
   ├─ source_ceiling: news=0.50, review=0.40, investment_db=0.65
   │
   ▼
3. CompanyContext.structural_tensions[] 에 추가
   │
   ├─ JD만 있는 경우: structural_tensions = null (추출 안함)
   └─ 크롤링 있는 경우: 해당 tension 리스트 생성
```

---

## 2. Pipeline A: CompanyContext 생성

### 입력
- JD 텍스트 (job_id 단위)
- NICE 기업 정보 (company_id 기준)
- (선택) 크롤링 데이터 (뉴스, 리뷰, 투자DB)

### 2.1 company_profile — NICE Lookup (Rule, LLM 불필요)

```python
def extract_company_profile(nice_data):
    """NICE DB에서 직접 조회. LLM 불필요."""
    return {
        "company_name": nice_data.company_name,
        "industry_code": nice_data.industry_code,
        "industry_label": INDUSTRY_CODE_MAP[nice_data.industry_code],
        "founded_year": nice_data.founded_year,
        "employee_count": nice_data.employee_count,
        "revenue_range": categorize_revenue(nice_data.revenue),
        "is_regulated_industry": nice_data.industry_code[:2] in REGULATED_CODES,
        "evidence": [Evidence(source_type="nice", ...)]
    }
```

- **비용**: 0 (DB 조회만)
- **confidence**: 0.70 (NICE ceiling)

#### Evidence 기반 field_confidence 규칙 **(v6 변경 M-4)**

> 모든 추출 필드에 `field_confidence = min(extraction_confidence, source_ceiling)` 규칙을 적용한다.
> 단, T4 카테고리(funding, performance)는 소스 특성상 예외 ceiling을 적용한다.

```python
# (v6 변경 M-4) Source Tier별 ceiling 정의
SOURCE_CEILING = {
    "nice":           0.70,   # T1 — 정형 DB
    "jd":             0.55,   # T2 — 1차 텍스트
    "resume":         0.55,   # T2 — 1차 텍스트
    "news":           0.50,   # T3 — 크롤링
    "review":         0.40,   # T3 — 크롤링 (주관적)
    "investment_db":  0.65,   # T3 — 크롤링 (정형)
}

# (v6 변경 M-4) T4 카테고리 예외 ceiling
T4_CATEGORY_CEILING = {
    "funding":     0.65,   # 투자 관련 필드
    "performance": 0.60,   # 실적 관련 필드
}

def compute_field_confidence(
    extraction_confidence: float,
    source_type: str,
    field_category: str = None
) -> float:
    """(v6 변경 M-4) field_confidence = min(extraction_confidence, source_ceiling)
    T4 카테고리는 예외 ceiling 적용."""
    ceiling = SOURCE_CEILING.get(source_type, 0.50)

    # T4 카테고리 예외
    if field_category in T4_CATEGORY_CEILING:
        ceiling = T4_CATEGORY_CEILING[field_category]

    return min(extraction_confidence, ceiling)
```

### 2.2 stage_estimate — Rule + LLM Fallback

```python
def extract_stage(nice_data, jd_text):
    """v10 01_company_context.md의 pseudo-code 그대로 구현"""
    # Step 1: Rule-based (NICE 데이터)
    if nice_data.founded_year and nice_data.employee_count:
        age = 2026 - nice_data.founded_year
        emp = nice_data.employee_count
        if age <= 3 and emp < 30:
            return "EARLY", 0.70
        elif 30 <= emp <= 300:
            return "GROWTH", 0.65
        elif emp > 300 or nice_data.revenue > 10_000_000_000:
            return "SCALE", 0.65
        elif age >= 15 and nice_data.revenue > 50_000_000_000:
            return "MATURE", 0.70

    # Step 2: LLM fallback (JD에서 stage 힌트)
    stage = llm_extract_stage(jd_text)  # Haiku/Flash급으로 충분
    if stage:
        return stage, 0.50
    return "UNKNOWN", 0.0
```

- **비용**: Rule로 해결되면 0, LLM fallback 시 JD 1건당 ~500 토큰
- **LLM fallback 예상 비율**: 20-30% (NICE 데이터가 불완전한 경우)

### 2.3 vacancy + role_expectations — LLM 통합 추출 (필수)

> **v3 변경**: v2에서 별도 프롬프트였던 vacancy와 role_expectations를 **단일 프롬프트로 통합**.
> 토큰 절감 효과: JD 1건당 ~1,000 토큰 절감 (JD 본문 중복 입력 제거).

```python
VACANCY_AND_ROLE_PROMPT = """
아래 채용 공고(JD)를 분석하여 JSON으로 응답하세요.

[1. Vacancy 추출]
- scope_type: BUILD_NEW / SCALE_EXISTING / RESET / REPLACE / UNKNOWN
  - BUILD_NEW: "신규 구축", "0→1", "greenfield" 등
  - SCALE_EXISTING: "확장", "스케일", "고도화" 등
  - RESET: "리팩토링", "재설계", "전환" 등
  - REPLACE: "충원", "결원", "대체" 등
- seniority: JUNIOR / MID / SENIOR / LEAD / HEAD / UNKNOWN
- role_title: 직무명 (원문 그대로)
- team_context: 팀 구성/규모 (추출 가능시만, 없으면 null)

[2. Role Expectations 추출]
- responsibilities: 주요 업무 (리스트)
- requirements: 필수 자격 (리스트)
- preferred: 우대 사항 (리스트)
- tech_stack: 기술 스택 (정규화된 이름, 리스트)

[규칙]
- 반드시 근거 문장(span)을 원문에서 인용하세요.
- 인용할 수 없으면 UNKNOWN으로 분류하세요.
- confidence: 0.0~1.0 (확신도)

[JD]
{jd_text}

[출력 JSON]
{
  "vacancy": { "scope_type": ..., "seniority": ..., "role_title": ..., "team_context": ..., "evidence": [...] },
  "role_expectations": { "responsibilities": [...], "requirements": [...], "preferred": [...], "tech_stack": [...] }
}
"""
```

- **비용**: JD 1건당 ~2,500-3,500 토큰 (입력 + 출력)
- **모델**: Claude Haiku 4.5 / Gemini Flash 2.0 (비용 효율)
- **Rule 불가 이유**: scope_type 판별은 문맥 해석이 필수
- **tech_stack 후처리**: LLM 추출 후 기술 사전으로 정규화

### 2.4 operating_model — 키워드 + LLM 보정

#### FACET_KEYWORDS 정의 **(v6 변경 M-1)**

> v1 범위에서는 3개 facet(speed, autonomy, process)만 활성화한다.
> 나머지 5개 facet(innovation, customer_focus, data_driven, collaboration, sustainability)은 v2 로드맵으로 이관한다.

```python
# (v6 변경 M-1) v1 스코프: 3개 facet 명시 정의
FACET_KEYWORDS = {
    "speed": [
        "빠른", "신속", "애자일", "agile", "스프린트", "sprint",
        "빠르게", "린", "lean", "속도", "speed", "rapid",
        "MVP", "iteration", "이터레이션", "quick",
    ],
    "autonomy": [
        "자율", "자기주도", "자유", "재량", "독립적",
        "autonomous", "self-driven", "ownership", "오너십",
        "책임감", "주도적", "empowerment", "위임",
    ],
    "process": [
        "프로세스", "체계", "절차", "표준", "규정",
        "process", "compliance", "컴플라이언스", "거버넌스",
        "governance", "SOP", "매뉴얼", "manual", "감사", "audit",
    ],
}

# (v6 변경 M-1) v2 로드맵: 추가 5개 facet
# V2_FACET_KEYWORDS = {
#     "innovation": [...],
#     "customer_focus": [...],
#     "data_driven": [...],
#     "collaboration": [...],
#     "sustainability": [...],
# }
```

```python
def extract_operating_model(jd_text, crawling_data=None):
    """v10의 키워드 카운트 + LLM 보정"""
    facets = {}
    for facet_name, keywords in FACET_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw.lower() in jd_text.lower())
        keyword_score = min(count / 5.0, 1.0)

        if count >= 2:
            # 키워드가 충분하면 LLM 보정으로 광고성 필터링
            llm_adj = llm_assess_authenticity(jd_text, facet_name, count)
            score = keyword_score * llm_adj
            confidence = min(0.60, 0.30 + count * 0.06)
        else:
            score = keyword_score
            confidence = max(0.20, count * 0.10)

        facets[facet_name] = {"score": score, "confidence": confidence, "source": "jd"}

    # (v6 변경 M-5) 크롤링 데이터 사용 가능 시 facet merge
    if crawling_data:
        facets = merge_facets_with_crawling(facets, crawling_data)

    return facets
```

#### 크롤링 데이터 facet merge 로직 **(v6 신설 M-5)**

> JD만 사용한 facet 점수와 크롤링 데이터에서 추출한 facet 점수를 병합한다.
> 크롤링 점수가 JD 점수와 큰 차이(threshold 0.20)를 보이면 크롤링 점수를 우선 반영한다.

```python
FACET_MERGE_THRESHOLD = 0.20  # (v6 신설 M-5)

def merge_facets_with_crawling(jd_facets: dict, crawling_data) -> dict:
    """(v6 신설 M-5) JD-only vs JD+crawling facet merge.

    Rules:
    1. 크롤링 데이터가 없는 facet → JD 점수 유지 (source="jd")
    2. 크롤링 데이터가 있고 |jd_score - crawl_score| < threshold → 가중평균
    3. 크롤링 데이터가 있고 |jd_score - crawl_score| >= threshold → 크롤링 우선
    """
    crawl_facets = extract_facets_from_crawling(crawling_data)
    merged = {}

    for facet_name, jd_facet in jd_facets.items():
        if facet_name not in crawl_facets:
            merged[facet_name] = jd_facet
            continue

        crawl_score = crawl_facets[facet_name]["score"]
        jd_score = jd_facet["score"]
        diff = abs(jd_score - crawl_score)

        if diff < FACET_MERGE_THRESHOLD:
            # 유사 → 가중평균 (JD 0.4, crawling 0.6)
            merged_score = jd_score * 0.4 + crawl_score * 0.6
            merged_conf = max(jd_facet["confidence"], crawl_facets[facet_name]["confidence"])
            merged[facet_name] = {
                "score": merged_score,
                "confidence": merged_conf,
                "source": "jd+crawling",
            }
        else:
            # 큰 차이 → 크롤링 우선 (실제 운영 모습 반영)
            merged[facet_name] = {
                "score": crawl_score,
                "confidence": crawl_facets[facet_name]["confidence"],
                "source": "crawling_override",
                "jd_score_original": jd_score,
            }

    return merged
```

### 2.5 structural_tensions 추출 **(v6 신설 H-4)**

> 크롤링 데이터가 확보된 경우에만 활성화되는 선택적 추출 단계.
> JD만 있는 경우 `structural_tensions = null`로 설정하여 skip한다.

```python
STRUCTURAL_TENSION_PROMPT = """
아래 기업 관련 텍스트(뉴스/리뷰/투자 정보)를 분석하여,
해당 기업이 겪고 있는 구조적 긴장(structural tension)을 추출하세요.

[8-type Taxonomy]
1. tech_debt_vs_features: 기술 부채 해소 vs 신규 기능 개발 우선순위 갈등
2. speed_vs_reliability: 빠른 출시 vs 안정성/품질 확보 사이의 긴장
3. founder_vs_professional_mgmt: 창업자 주도 경영 vs 전문 경영인 체제 전환
4. efficiency_vs_growth: 비용 효율화 vs 성장 투자 사이의 갈등
5. scaling_leadership: 조직 확대에 따른 리더십/관리 체계 확장 과제
6. integration_tension: M&A/합병 후 조직/시스템/문화 통합 긴장
7. build_vs_buy: 자체 개발 vs 외부 솔루션 도입 의사결정 갈등
8. portfolio_restructuring: 사업 포트폴리오 재편/선택과 집중 과제

[규칙]
- 텍스트에서 명시적 근거가 있는 tension만 추출하세요.
- 각 tension에 evidence_span(원문 인용)을 반드시 포함하세요.
- 추론만으로는 추출하지 마세요.
- confidence: 0.0~1.0

[기업 관련 텍스트]
{crawling_text}

[기업 기본 정보]
회사명: {company_name}
업종: {industry_label}
스테이지: {stage_label}

[출력 JSON]
{
  "structural_tensions": [
    {
      "tension_type": "...",
      "description": "...",
      "evidence_span": "...",
      "source_id": "...",
      "confidence": 0.0
    }
  ]
}
"""

def extract_structural_tensions(company_ctx, crawling_data):
    """(v6 신설 H-4) 크롤링 데이터 기반 structural_tensions 추출"""
    if not crawling_data:
        return None  # 크롤링 미확보 → skip

    crawling_text = prepare_crawling_text(crawling_data, max_tokens=4000)
    result = llm_extract(
        STRUCTURAL_TENSION_PROMPT,
        crawling_text=crawling_text,
        company_name=company_ctx.company_profile.company_name,
        industry_label=company_ctx.company_profile.industry_label,
        stage_label=company_ctx.stage_estimate.stage,
    )

    # field_confidence 적용 (v6 M-4)
    for tension in result.structural_tensions or []:
        source_type = crawling_data.source_type  # "news" / "review" / "investment_db"
        tension.confidence = compute_field_confidence(
            tension.confidence, source_type
        )

    return result.structural_tensions
```

### CompanyContext 생성 비용 요약 (1건당)

| 필드 | 방법 | 토큰 (입출력) | 비용 (Haiku 일반) | 비용 (Haiku Batch 50%) |
|---|---|---|---|---|
| company_profile | NICE Lookup | 0 | $0 | $0 |
| stage_estimate | Rule (80%) / LLM (20%) | 평균 ~100 | ~$0.00002 | ~$0.00001 |
| vacancy + role_expectations | LLM (통합 프롬프트) | ~3,000 | ~$0.0006 | ~$0.0003 |
| operating_model | 키워드 + LLM 보정 | ~800 | ~$0.00016 | ~$0.00008 |
| structural_tensions **(v6 추가)** | LLM (크롤링 있을 때만) | ~2,000 (선택적) | ~$0.0004 | ~$0.0002 |
| **합계 (JD only)** | | **~3,900** | **~$0.0008** | **~$0.0004** |
| **합계 (JD + 크롤링)** | | **~5,900** | **~$0.0012** | **~$0.0006** |

> **참고**: 대량 처리 시 Batch API(50% 할인) 적용을 권장. 03 문서의 시나리오별 비용은 Batch 가격 기준.

---

## 3. Pipeline B: CandidateContext 생성

### 입력
- 이력서 텍스트 (candidate_id 단위)
- NICE 기업 정보 (회사명 기반 조회)

### 3.1 전처리: 이력서 파싱

v1의 PDF/HWP 파싱은 그대로 유효하지만, 출력 형식을 v10에 맞춘다.

```
[이력서 원본]
    │
    ├─ PDF → PyMuPDF / pdfplumber
    ├─ DOCX → python-docx
    ├─ HWP → python-hwp / LibreOffice headless
    │
    ▼
[텍스트 + 레이아웃]
    │
    ├─[Rule] 섹션 분할 (경력, 학력, 기술, 프로젝트)
    ├─[Rule] 경력 블록 분리 (회사별 단위)
    └─[Rule] 기본 정보 추출 (이름, 연락처)
```

### 3.2 Experience 추출 — Rule + LLM 계층

#### Step 1: Rule 추출 (비용 0)

```python
def rule_extract_experience(block_text):
    """경력 블록에서 정형 필드 추출"""
    return {
        "company": extract_company_name(block_text),  # 패턴 매칭
        "role_title": extract_role_title(block_text),  # 패턴 매칭
        "period": extract_period(block_text),           # 날짜 regex
        "tech_stack": match_tech_dictionary(block_text), # 기술 사전
    }
```

**주요 정규식 패턴 예시**:

```python
# 회사명 추출 패턴 (한국어 이력서)
COMPANY_PATTERNS = [
    # "㈜카카오", "(주)네이버", "주식회사 라인"
    r'[㈜\(주\)]\s*([가-힣A-Za-z0-9]+)',
    r'주식회사\s+([가-힣A-Za-z0-9]+)',
    # "카카오 | 백엔드 개발자", "네이버 / 시니어 엔지니어"
    r'^([가-힣A-Za-z0-9\s]+?)\s*[|/·]\s*(.+?)$',
    # "카카오 (2020.03 ~ 2023.06)"
    r'^([가-힣A-Za-z0-9\s]+?)\s*[\(（]\s*\d{4}',
]

# 기간 추출 패턴
PERIOD_PATTERNS = [
    # "2020.03 ~ 2023.06", "2020-03 - 2023-06"
    r'(\d{4})[.\-/](\d{1,2})\s*[~\-–]\s*(\d{4})[.\-/](\d{1,2})',
    # "2020.03 ~ 현재", "2020-03 - 재직중"
    r'(\d{4})[.\-/](\d{1,2})\s*[~\-–]\s*(현재|재직중|Present)',
    # "2020년 3월 ~ 2023년 6월"
    r'(\d{4})년\s*(\d{1,2})월\s*[~\-–]\s*(\d{4})년\s*(\d{1,2})월',
]

# 직무명 추출 패턴
ROLE_PATTERNS = [
    # "백엔드 개발자", "시니어 엔지니어", "프론트엔드 리드"
    r'(시니어|주니어|리드|수석|책임|선임)?\s*([\w]+\s*(개발자|엔지니어|디자이너|매니저|PM|PO|리드))',
    # "CTO", "VP of Engineering"
    r'\b(CTO|CEO|VP|Director|Manager|Lead|Senior|Staff)\b',
]
```

- company, role_title: 경력 블록 첫 줄의 패턴으로 60-70% 커버
- period: 날짜 regex로 80-90% 커버
- tech_stack: 기술 사전 fuzzy matching으로 70-80% 커버

#### Step 2: LLM 추출 (Experience별, 핵심)

```python
EXPERIENCE_PROMPT = """
아래 경력 텍스트에서 다음을 추출하세요.

[필수 추출 항목]
1. scope_type: IC / LEAD / HEAD / FOUNDER / UNKNOWN
   - IC: 개인 기여자, 팀원
   - LEAD: 팀 리드, 테크 리드 (3~20명 관리)
   - HEAD: 부서장, CTO (20명+ 관리)
   - FOUNDER: 창업자
2. scope_summary: 역할 범위 한 문장 요약
3. outcomes: 정량/정성 성과 목록
   - 각 outcome에: description, outcome_type(METRIC/SCALE/DELIVERY/ORGANIZATIONAL),
     quantitative(bool), metric_value(수치 있으면)
4. situational_signals: 아래 taxonomy에서 해당하는 것만 선택
   [Taxonomy: EARLY_STAGE, SCALE_UP, TURNAROUND, GLOBAL_EXPANSION,
    TEAM_BUILDING, TEAM_SCALING, REORG, LEGACY_MODERNIZATION,
    NEW_SYSTEM_BUILD, TECH_STACK_TRANSITION, PMF_SEARCH,
    MONETIZATION, ENTERPRISE_TRANSITION, OTHER]
   - 각 signal에: label, description, evidence_span(원문 인용), confidence

[규칙]
- 근거 없이 추론하지 마세요. 인용할 수 없으면 해당 항목을 생성하지 마세요.
- confidence: 0.0~1.0

[경력 텍스트]
{experience_block}

[기본 정보 (Rule에서 추출)]
{basic_info_block}

[출력 JSON]
"""

# Rule 추출 결과에 따른 프롬프트 분기
def build_basic_info_block(basic):
    """Rule 추출 성공/실패에 따라 프롬프트 컨텍스트를 조정"""
    parts = []
    if basic.company:
        parts.append(f"회사: {basic.company}")
    if basic.role_title:
        parts.append(f"직무: {basic.role_title}")
    if basic.period:
        parts.append(f"기간: {basic.period}")

    if not parts:
        # Rule 추출 전체 실패 → LLM에 기본 필드도 함께 추출 요청
        return (
            "※ 기본 정보를 자동 추출하지 못했습니다.\n"
            "위 경력 텍스트에서 회사명, 직무명, 근무 기간도 함께 추출하세요."
        )
    elif len(parts) < 3:
        # 부분 실패 → 누락 필드만 추가 추출 요청
        missing = []
        if not basic.company: missing.append("회사명")
        if not basic.role_title: missing.append("직무명")
        if not basic.period: missing.append("근무 기간")
        return "\n".join(parts) + f"\n※ 다음 항목은 자동 추출 실패. 텍스트에서 추출하세요: {', '.join(missing)}"
    else:
        return "\n".join(parts)
```

- **비용**: Experience 1건당 ~2,000-3,500 토큰 (Rule 전체 실패 시 +500 토큰)
- **평균 이력서**: 경력 2-4개 → **이력서 1건당 ~6,000-12,000 토큰**
- **모델**: Claude Haiku 4.5 / Gemini Flash 2.0

#### Step 3: NICE Lookup — PastCompanyContext (비용 0)

```python
def build_past_company_context(company_name, tenure_start, tenure_end):
    """v10 02_candidate_context.md의 로직 그대로"""
    nice = lookup_nice(company_name)
    if not nice:
        return None  # NICE에 없는 회사

    years_gap = 2026 - tenure_end.year
    confidence = max(0.20, 0.60 - years_gap * 0.08)

    return PastCompanyContext(
        company_name=company_name,
        industry_code=nice.industry_code,
        employee_count=nice.employee_count,
        founded_year=nice.founded_year,
        stage_estimation_method="nice_current",
        confidence=confidence,
        ...
    )
```

### 3.3 전체 커리어 수준 추출 — LLM (1회)

```python
CAREER_LEVEL_PROMPT = """
아래 후보의 전체 경력 요약을 분석하여 추출하세요.

[추출 항목]
1. role_evolution:
   - pattern: IC_TO_LEAD / IC_DEPTH / LEAD_TO_HEAD / FOUNDER / GENERALIST / DOWNSHIFT / LATERAL / UNKNOWN
   - description: 커리어 패턴 서술
   - total_experience_years: 총 경력 연수
2. domain_depth:
   - primary_domain: 주요 도메인
   - domain_experience_count: 해당 도메인 회사 수
   - description: 도메인 경험 서술
3. work_style_signals (있을 때만):
   - autonomy_preference: HIGH / MID / LOW / null
   - process_tolerance: HIGH / MID / LOW / null
   - experiment_orientation: HIGH / MID / LOW / null  (v6 추가 M-3)
   - collaboration_style: INDEPENDENT / PAIR / TEAM / null  (v6 추가 M-3)

[전체 경력]
{all_experiences_summary}

[출력 JSON]
"""
```

> **(v6 변경 M-3)**: `work_style_signals`에 `experiment_orientation`과 `collaboration_style` 추출 항목을 추가.
> - `experiment_orientation`: 실험/PoC 지향성 (HIGH: A/B 테스트, 실험 문화 언급 / MID: 일부 시도 / LOW: 안정 우선)
> - `collaboration_style`: 협업 방식 선호 (INDEPENDENT: 독립 작업 / PAIR: 페어 프로그래밍 / TEAM: 팀 단위 협업)

- **비용**: 이력서 1건당 ~2,000-3,000 토큰 (전체 경력 요약 1회)

### 3.4 이력서 중복 처리 전략

> **v5 신설**: v4 리뷰에서 지적된 중복 처리 전략 부재를 보강.

```python
def deduplicate_resumes(resume_list):
    """동일인의 다중 이력서를 감지하고 canonical 버전을 선택"""

    # Case 1: 동일 candidate_id — 최신 파일만 처리
    by_candidate = group_by(resume_list, key=lambda r: r.candidate_id)
    canonical = []
    for cid, versions in by_candidate.items():
        if len(versions) > 1:
            selected = max(versions, key=lambda r: r.updated_at)
            canonical.append(selected)
            logger.info(f"Duplicate candidate_id={cid}: {len(versions)} versions, selected latest")
        else:
            canonical.append(versions[0])

    # Case 2: 다른 candidate_id, 동일인 추정 — SimHash 유사도
    # Phase 0에서 중복률 실측 후 임계값 확정
    # 유사도 > 0.9 시 수동 검토 큐로 이동 (Phase 2 운영에서 처리)

    return canonical
```

- **처리 시점**: Pipeline B 진입 전, 전처리 단계에서 실행
- **Phase 0 확인 항목**: 동일 candidate_id 다중 버전 비율, SimHash 기반 유사 이력서 비율

### CandidateContext 생성 비용 요약 (이력서 1건당)

| 추출 단계 | 방법 | 토큰 (입출력) | 비용 (Haiku 일반) | 비용 (Haiku Batch 50%) |
|---|---|---|---|---|
| 전처리 (파싱, 섹션분할) | Rule | 0 | $0 | $0 |
| 기본 필드 (회사/직무/기간/기술) | Rule | 0 | $0 | $0 |
| Experience별 추출 (x3 평균) | LLM | ~9,000 | ~$0.0018 | ~$0.0009 |
| PastCompanyContext (x3) | NICE Lookup | 0 | $0 | $0 |
| 전체 커리어 (role_evolution 등) | LLM | ~2,500 | ~$0.0005 | ~$0.00025 |
| **합계** | | **~11,500** | **~$0.0023** | **~$0.00115** |

> **참고**: 대량 처리 시 Batch API(50% 할인) 적용을 권장. 03 문서의 시나리오별 비용은 Batch 가격 기준.

---

## 4. Pipeline C: Graph 적재

### 4.1 CompanyContext → Graph

```python
def load_company_to_graph(company_ctx, tx):
    """CompanyContext JSON → Neo4j 노드/엣지"""
    # Organization 노드
    tx.run("""
        MERGE (o:Organization {org_id: $org_id})
        SET o.name = $name, o.industry_code = $industry_code,
            o.stage_label = $stage_label, ...
    """, company_ctx.company_profile)

    # Organization -[:IN_INDUSTRY]-> Industry (v6 추가 H-1)
    tx.run("""
        MATCH (o:Organization {org_id: $org_id})
        MATCH (ind:Industry {industry_code: $industry_code})
        MERGE (o)-[:IN_INDUSTRY]->(ind)
    """, org_id=company_ctx.company_profile.org_id,
        industry_code=company_ctx.company_profile.industry_code)

    # Vacancy 노드 — v5 변경: CREATE → MERGE (idempotency 보장)
    tx.run("""
        MERGE (v:Vacancy {vacancy_id: $vacancy_id})
        SET v.scope_type = $scope_type, v.seniority = $seniority,
            v.role_title = $role_title, v.team_context = $team_context,
            v.extracted_at = datetime(), v.prompt_version = $prompt_version
    """, vacancy_id=generate_vacancy_id(company_ctx.job_id),
        **company_ctx.vacancy)

    # Organization -[:HAS_VACANCY]-> Vacancy
    tx.run("""
        MATCH (o:Organization {org_id: $org_id})
        MATCH (v:Vacancy {vacancy_id: $vacancy_id})
        MERGE (o)-[:HAS_VACANCY]->(v)
    """)

    # Vacancy -[:REQUIRES_ROLE]-> Role (v6 추가 H-5)
    if company_ctx.vacancy.role_title:
        tx.run("""
            MERGE (r:Role {name: $role_name})
            MATCH (v:Vacancy {vacancy_id: $vacancy_id})
            MERGE (v)-[:REQUIRES_ROLE {seniority: $seniority}]->(r)
        """, role_name=normalize_role(company_ctx.vacancy.role_title),
            vacancy_id=generate_vacancy_id(company_ctx.job_id),
            seniority=company_ctx.vacancy.seniority)

    # Vacancy -[:REQUIRES_SKILL]-> Skill (tech_stack에서)
    for skill in company_ctx.role_expectations.tech_stack:
        tx.run("""
            MERGE (s:Skill {name: $name})
            MATCH (v:Vacancy {vacancy_id: $vacancy_id})
            MERGE (v)-[:REQUIRES_SKILL]->(s)
        """, name=normalize_skill(skill))

    # Vacancy -[:NEEDS_SIGNAL]-> SituationalSignal (추론)
    signals = infer_vacancy_signals(company_ctx.vacancy)
    for signal_label in signals:
        tx.run("""
            MERGE (sig:SituationalSignal {label: $label})
            MATCH (v:Vacancy {vacancy_id: $vacancy_id})
            MERGE (v)-[:NEEDS_SIGNAL {inferred: true}]->(sig)
        """, label=signal_label)
```

### 4.2 CandidateContext → Graph

```python
def load_candidate_to_graph(candidate_ctx, tx):
    """CandidateContext JSON → Neo4j 노드/엣지"""
    # Person 노드
    tx.run("""
        MERGE (p:Person {person_id: $candidate_id})
        SET p.role_evolution_pattern = $pattern, ...
    """)

    for i, exp in enumerate(candidate_ctx.experiences):
        # Chapter 노드 — v5 변경: deterministic ID + MERGE
        chapter_id = generate_chapter_id(candidate_ctx.candidate_id, exp)
        tx.run("""
            MERGE (ch:Chapter {chapter_id: $chapter_id})
            SET ch.scope_type = $scope_type, ch.scope_summary = $scope_summary,
                ch.extracted_at = datetime(), ch.prompt_version = $prompt_version
        """, chapter_id=chapter_id, **exp)

        # Person -[:HAS_CHAPTER]-> Chapter
        tx.run("""
            MATCH (p:Person {person_id: $candidate_id})
            MATCH (ch:Chapter {chapter_id: $chapter_id})
            MERGE (p)-[:HAS_CHAPTER {order: $order}]->(ch)
        """, candidate_id=candidate_ctx.candidate_id, chapter_id=chapter_id, order=i)

        # Chapter -[:OCCURRED_AT]-> Organization
        if exp.company:
            org_id = resolve_org_id(exp.company)
            if org_id:
                tx.run("""
                    MERGE (o:Organization {org_id: $org_id})
                    SET o.name = COALESCE(o.name, $company_name)
                    WITH o
                    MATCH (ch:Chapter {chapter_id: $chapter_id})
                    MERGE (ch)-[:OCCURRED_AT {start: $start, end: $end}]->(o)
                """, org_id=org_id, company_name=exp.company,
                    chapter_id=chapter_id, start=exp.period_start, end=exp.period_end)
            else:
                # NICE/사전에 없는 회사 → name 기반 MERGE (fallback)
                tx.run("""
                    MERGE (o:Organization {name: $company_name})
                    WITH o
                    MATCH (ch:Chapter {chapter_id: $chapter_id})
                    MERGE (ch)-[:OCCURRED_AT {start: $start, end: $end}]->(o)
                """, company_name=exp.company, chapter_id=chapter_id,
                    start=exp.period_start, end=exp.period_end)

        # Chapter -[:PERFORMED_ROLE]-> Role
        if exp.role_title:
            tx.run("""
                MERGE (r:Role {name: $role_name})
                MATCH (ch:Chapter {chapter_id: $chapter_id})
                MERGE (ch)-[:PERFORMED_ROLE]->(r)
            """, role_name=normalize_role(exp.role_title), chapter_id=chapter_id)

        # Chapter -[:USED_SKILL]-> Skill
        for skill in exp.tech_stack or []:
            tx.run("""
                MERGE (s:Skill {name: $name})
                MATCH (ch:Chapter {chapter_id: $chapter_id})
                MERGE (ch)-[:USED_SKILL]->(s)
            """, name=normalize_skill(skill), chapter_id=chapter_id)

        # Chapter -[:PRODUCED_OUTCOME]-> Outcome — v5 변경: deterministic ID + MERGE
        for j, outcome in enumerate(exp.outcomes or []):
            outcome_id = generate_outcome_id(chapter_id, j)
            tx.run("""
                MERGE (out:Outcome {outcome_id: $outcome_id})
                SET out.description = $desc, out.outcome_type = $type,
                    out.quantitative = $quant, out.metric_value = $metric
                WITH out
                MATCH (ch:Chapter {chapter_id: $chapter_id})
                MERGE (ch)-[:PRODUCED_OUTCOME]->(out)
            """, outcome_id=outcome_id, desc=outcome.description,
                type=outcome.outcome_type, quant=outcome.quantitative,
                metric=outcome.metric_value, chapter_id=chapter_id)

        # Chapter -[:HAS_SIGNAL]-> SituationalSignal (공유 노드)
        for signal in exp.situational_signals or []:
            tx.run("""
                MERGE (sig:SituationalSignal {label: $label})
                MATCH (ch:Chapter {chapter_id: $chapter_id})
                MERGE (ch)-[:HAS_SIGNAL {confidence: $conf}]->(sig)
            """, label=signal.label, chapter_id=chapter_id, conf=signal.confidence)

    # Chapter -[:NEXT_CHAPTER]-> Chapter (시간순)
    sorted_exps = sorted(candidate_ctx.experiences, key=lambda e: e.period_start)
    for i in range(len(sorted_exps) - 1):
        id1 = generate_chapter_id(candidate_ctx.candidate_id, sorted_exps[i])
        id2 = generate_chapter_id(candidate_ctx.candidate_id, sorted_exps[i+1])
        tx.run("""
            MATCH (c1:Chapter {chapter_id: $id1})
            MATCH (c2:Chapter {chapter_id: $id2})
            MERGE (c1)-[:NEXT_CHAPTER]->(c2)
        """, id1=id1, id2=id2)
```

### 4.3 Organization Entity Resolution

> **v4 신설**: v3 리뷰에서 지적된 Organization MERGE 전략 불일치를 해결.

```python
def resolve_org_id(company_name: str) -> Optional[str]:
    """회사명 → org_id 매핑. NICE DB + 회사명 정규화 사전 활용."""
    # Step 1: 정규화 사전 조회 (alias → canonical name → org_id)
    canonical = COMPANY_ALIAS_DICT.get(normalize_company_name(company_name))
    if canonical:
        return canonical.org_id

    # Step 2: NICE DB 직접 조회 (fuzzy match)
    nice = lookup_nice_fuzzy(company_name, threshold=0.85)
    if nice:
        return nice.org_id

    # Step 3: 매칭 실패 → None (fallback: name 기반 MERGE)
    return None
```

**정규화 사전 구축**:
- KOSPI/KOSDAQ 상장사 + NICE 등록 기업에서 자동 생성 (~1,000개)
- "카카오" / "주식회사 카카오" / "(주)카카오" / "카카오엔터프라이즈" 등 alias 수동 추가
- Phase 1-4에서 구축, 이후 증분 갱신

### 4.4 Graph 적재 전략: 초기 vs 증분

> **v4 신설**: v3 리뷰에서 지적된 대량 적재 전략 부재를 보강.

#### 초기 적재 (Phase 2-1, 500K 전체)

AuraDB 관리형 환경에서 대량 적재 시:

```
[초기 적재 전략]
1. Industry 마스터 노드 사전 적재 (v6 추가 H-1, §4.7 참조)
   └─ NICE 업종코드 기반 ~1,500개 Industry 노드 MERGE

2. Context JSON → CSV 변환 (노드별, 엣지별 파일 분리)
   ├─ nodes_person.csv, nodes_chapter.csv, nodes_organization.csv, ...
   ├─ nodes_industry.csv (v6 추가)
   └─ edges_has_chapter.csv, edges_occurred_at.csv, edges_in_industry.csv, ...

3. Neo4j LOAD CSV + APOC batch 활용
   ├─ USING PERIODIC COMMIT 500
   ├─ CALL apoc.periodic.iterate(...)로 대량 MERGE
   └─ 인덱스는 적재 후 빌드 (적재 중 인덱스 비활성화)

4. Vector Index 적재 (embedding 별도 배치)
   ├─ Chapter embedding: 150만 건
   ├─ Vacancy embedding: 1만 건
   └─ HNSW 인덱스 빌드: ~2~4시간 (150만 벡터)

예상 적재 시간: CSV 변환 4~6시간 + LOAD CSV 8~12시간 + Vector 2~4시간 = ~1~2일
```

#### 증분 적재 (운영 단계)

- 일일 신규/갱신 건만 Cypher MERGE로 처리
- 예상 일일 처리량: 100~1,000건 → ~수 분 이내
- 트랜잭션 배치: 100건/TX

### 4.5 Vector Index

> **v6 변경 H-2, L-1**: Embedding 모델을 `text-multilingual-embedding-002` (Vertex AI)로 확정.
> 필드명을 `embedding_text`/`embedding` → `evidence_chunk`/`evidence_chunk_embedding`으로 변경.

```python
# Chapter embedding — scope_summary + outcomes 요약 텍스트
def build_chapter_evidence_chunk(chapter):
    """(v6 변경 L-1) Vector search에 사용할 Chapter 요약 텍스트 생성.
    필드명: embedding_text → evidence_chunk"""
    parts = []
    if chapter.scope_summary:
        parts.append(chapter.scope_summary)
    for outcome in chapter.outcomes or []:
        parts.append(outcome.description)
    for signal in chapter.situational_signals or []:
        parts.append(f"{signal.label}: {signal.description}")

    # v5 추가: 빈 텍스트 방지
    text = " ".join(parts)
    if not text.strip():
        return None  # embedding 적재 skip
    return text

# (v6 변경 H-2) Embedding 모델 확정: text-multilingual-embedding-002 (Vertex AI)
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

embed_model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")

def get_embedding(text: str) -> list[float]:
    """(v6 변경 H-2) Vertex AI text-multilingual-embedding-002로 embedding 생성"""
    embeddings = embed_model.get_embeddings([text])
    return embeddings[0].values  # 768-dim vector

for chapter in chapters:
    evidence_chunk = build_chapter_evidence_chunk(chapter)  # (v6 변경 L-1)
    if evidence_chunk is None:
        continue  # 빈 텍스트인 경우 embedding 생성 skip
    evidence_chunk_embedding = get_embedding(evidence_chunk)  # (v6 변경 H-2, L-1)
    tx.run("""
        MATCH (ch:Chapter {chapter_id: $id})
        SET ch.evidence_chunk = $text,
            ch.evidence_chunk_embedding = $emb
    """, id=chapter.chapter_id, text=evidence_chunk, emb=evidence_chunk_embedding)

# Vacancy embedding — vacancy scope_type + responsibilities 요약
def build_vacancy_evidence_chunk(vacancy, role_exp):
    """(v6 변경 L-1) Vacancy embedding 텍스트 생성.
    필드명: embedding_text → evidence_chunk"""
    parts = [f"scope: {vacancy.scope_type}"]
    parts.extend(role_exp.responsibilities or [])
    return " ".join(parts)

vacancy_chunk = build_vacancy_evidence_chunk(vacancy, role_expectations)  # (v6 변경 L-1)
vacancy_emb = get_embedding(vacancy_chunk)  # (v6 변경 H-2)
tx.run("""
    MATCH (v:Vacancy {vacancy_id: $id})
    SET v.evidence_chunk = $text,
        v.evidence_chunk_embedding = $emb
""", id=vacancy.vacancy_id, text=vacancy_chunk, emb=vacancy_emb)
```

> **(v6 변경 H-2)**: Embedding 모델을 Phase 0 PoC 비교 없이 `text-multilingual-embedding-002` (Vertex AI)로 확정.
> - 768차원 벡터, 한국어/영어 다국어 지원
> - Vertex AI 네이티브 통합으로 인프라 단순화
> - 비용: $0.025/1M 토큰 (Vertex AI 가격)
>
> **(v6 변경 L-1)**: 필드명 변경 — 그래프 스키마와 일관성 확보
> - `embedding_text` → `evidence_chunk`: 실제 저장되는 텍스트의 성격을 더 정확히 반영
> - `embedding` → `evidence_chunk_embedding`: evidence_chunk에 대한 벡터임을 명시

### 4.6 Deterministic ID 생성 전략

> **v5 신설**: v4 리뷰에서 지적된 ID 생성 규칙 부재를 보강.
> 증분 처리와 재처리 시 Graph 데이터 일관성을 보장하기 위해, 모든 노드 ID는 deterministic하게 생성한다.

```python
import hashlib

def _hash_id(*parts) -> str:
    """입력 값들을 결합하여 deterministic hash ID 생성"""
    raw = "|".join(str(p) for p in parts if p is not None)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def generate_vacancy_id(job_id: str) -> str:
    """Vacancy ID = job_id 그대로 사용 (이미 unique)"""
    return f"vac_{job_id}"

def generate_chapter_id(candidate_id: str, exp) -> str:
    """Chapter ID = hash(candidate_id + company_normalized + period_start)"""
    company_norm = normalize_company_name(exp.company) if exp.company else "unknown"
    period = exp.period_start or "unknown"
    return f"ch_{_hash_id(candidate_id, company_norm, period)}"

def generate_outcome_id(chapter_id: str, outcome_index: int) -> str:
    """Outcome ID = hash(chapter_id + outcome_index)
    outcome_index는 LLM 추출 순서 기반. 동일 chapter의 동일 순서 outcome은 동일 ID."""
    return f"out_{_hash_id(chapter_id, outcome_index)}"
```

**ID 생성 원칙**:
- **Person**: `candidate_id` 그대로 사용 (시스템 부여 ID)
- **Organization**: `org_id` (NICE 기반) 또는 `name` (fallback)
- **Industry**: `industry_code` (NICE 업종코드) **(v6 추가 H-1)**
- **Chapter**: `hash(candidate_id + company + period_start)` — 동일 경력은 동일 ID
- **Vacancy**: `job_id` 그대로 사용 (시스템 부여 ID)
- **Outcome**: `hash(chapter_id + index)` — 동일 chapter 내 동일 순서 outcome은 동일 ID
- **Skill, Role, SituationalSignal**: `name` 또는 `label` 기반 MERGE (이미 deterministic)

**Idempotency 보장**: 모든 노드가 deterministic ID + MERGE 패턴을 사용하므로, 동일 입력을 재처리해도 노드가 중복 생성되지 않고 속성만 업데이트된다.

### 4.7 Industry 마스터 데이터 사전 적재 **(v6 신설 H-1)**

> NICE 업종코드 기반으로 Industry 마스터 노드를 사전 생성한다.
> Organization 노드 적재 시 IN_INDUSTRY 관계를 통해 연결한다.

```python
def preload_industry_master(tx):
    """(v6 신설 H-1) NICE 업종코드 기반 Industry 마스터 노드 사전 적재.
    Pipeline C 실행 전에 1회 실행. 이후 증분 갱신."""

    # NICE 업종코드 마스터 테이블 (대분류 ~20, 중분류 ~80, 소분류 ~1,500)
    industry_codes = load_nice_industry_codes()  # NICE DB에서 전체 업종코드 조회

    for code in industry_codes:
        tx.run("""
            MERGE (ind:Industry {industry_code: $code})
            SET ind.label = $label,
                ind.category_large = $cat_large,
                ind.category_medium = $cat_medium,
                ind.category_small = $cat_small,
                ind.updated_at = datetime()
        """, code=code.industry_code,
            label=code.label,
            cat_large=code.category_large,
            cat_medium=code.category_medium,
            cat_small=code.category_small)

    # Industry 계층 관계 (선택적 — 대분류-중분류-소분류)
    for code in industry_codes:
        if code.parent_code:
            tx.run("""
                MATCH (child:Industry {industry_code: $child_code})
                MATCH (parent:Industry {industry_code: $parent_code})
                MERGE (child)-[:BELONGS_TO]->(parent)
            """, child_code=code.industry_code,
                parent_code=code.parent_code)
```

**Industry 노드 활용**:
- `Organization -[:IN_INDUSTRY]-> Industry`: §4.1에서 CompanyContext 적재 시 자동 연결
- `Chapter -[:OCCURRED_AT]-> Organization -[:IN_INDUSTRY]-> Industry`: 후보의 산업 경험 탐색 가능
- Pipeline D `domain_fit` 계산 시 Industry 노드를 활용한 산업 유사도 계산 가능

**적재 시점**:
- 초기 적재: Pipeline C 실행 전 1회 (§4.4 초기 적재 Step 1)
- 갱신: NICE 업종코드 변경 시 증분 MERGE (연 1회 수준)

**예상 규모**: ~1,500 Industry 노드 + ~1,500 BELONGS_TO 관계

---

## 5. Pipeline D: MappingFeatures 계산

MappingFeatures는 v10 `03_mapping_features.md`의 로직을 그대로 구현한다.
이 단계에서는 **LLM을 사용하지 않는다** (Rule + Embedding만).

### 5.0 Candidate Shortlisting — 매핑 대상 후보 선정

> **v4 신설**: v3에서 "상위 500명"의 선정 기준이 미정의였던 점을 보강.

전수 매핑(500K x 10K = 50억 쌍)은 비현실적이므로, JD별 **상위 후보 500명**을 사전 선정한다.

#### 선정 방법 (2단계 필터)

```python
def shortlist_candidates(vacancy, all_candidates, top_k=500):
    """JD별 상위 후보 선정. Rule pre-filter → Embedding ANN 순서."""
    # Stage 1: Rule pre-filter (비용 0)
    # — industry, tech_stack 교집합, 경력연수 범위로 대상 축소
    filtered = [c for c in all_candidates if passes_rule_filter(vacancy, c)]
    # 예상 축소율: 500K → 5K~50K (industry + 경력연수 필터)

    # Stage 2: Embedding ANN (Vector Search)
    # — Vacancy evidence_chunk_embedding과 Chapter evidence_chunk_embedding의
    #   cosine similarity top-K (v6 변경 L-1: 필드명 변경)
    # — embedding이 없는 Chapter는 Stage 1 결과에서만 평가 (v5 추가)
    vacancy_emb = get_vacancy_embedding(vacancy.vacancy_id)
    results = vector_index.search(vacancy_emb, candidates=filtered, top_k=top_k)
    return results
```

#### 인프라

- **Rule pre-filter**: BigQuery SQL 또는 in-memory 필터링 (추가 인프라 불필요)
- **Embedding ANN**: Neo4j Vector Index (`db.index.vector.queryNodes`) 활용 — 별도 ANN 서비스 불필요
- **비용**: 사실상 $0 (Neo4j Vector Index가 이미 Pipeline C에서 구축됨)

#### 범위 결정

> Candidate Shortlisting은 KG 구축(create-kg)의 최종 단계이자, 서빙 시스템의 시작점이다.
> v1 MVP에서는 **배치 방식**으로 사전 계산하여 BigQuery에 적재하고,
> 실시간 Shortlisting은 Phase 3(서빙 API)에서 구현한다.

### 5.1 계산 비용

| 피처 | 방법 | 비용 |
|---|---|---|
| stage_match | Rule (lookup table) | 0 |
| vacancy_fit | Rule (signal alignment table, 아래 참조) | 0 |
| domain_fit | Embedding cosine similarity | ~0.00001/건 |
| culture_fit | Rule (facet 비교) — 대부분 INACTIVE | 0 |
| role_fit | Rule + ScopeType 변환 (v6 변경 M-2) | 0 |
| **합계** | | **~$0.00001/매핑** |

#### vacancy_fit Signal Alignment Table 구축 방법

vacancy_fit은 Vacancy의 `scope_type`이 요구하는 상황과 후보의 `situational_signals` 보유 여부를 매칭한다.
이 매핑 테이블은 **수동 설계(도메인 전문가)**이며, v10 온톨로지의 비즈니스 로직에 기반한다.

```python
# 수동 설계된 정적 매핑 테이블 (v10 03_mapping_features.md 기반)
VACANCY_SIGNAL_ALIGNMENT = {
    "BUILD_NEW":       ["NEW_SYSTEM_BUILD", "EARLY_STAGE", "PMF_SEARCH", "TEAM_BUILDING"],
    "SCALE_EXISTING":  ["SCALE_UP", "TEAM_SCALING", "MONETIZATION"],
    "RESET":           ["TURNAROUND", "LEGACY_MODERNIZATION", "TECH_STACK_TRANSITION", "REORG"],
    "REPLACE":         [],  # 충원은 특별한 signal alignment 없음
}

def compute_vacancy_fit(vacancy_scope_type, candidate_signals):
    """Vacancy scope_type에 해당하는 signal을 후보가 보유하는지 룩업"""
    required = VACANCY_SIGNAL_ALIGNMENT.get(vacancy_scope_type, [])
    if not required:
        return {"score": 0.5, "status": "INACTIVE", "reason": "no_alignment_defined"}
    matched = [s for s in candidate_signals if s.label in required]
    score = len(matched) / len(required)
    return {"score": score, "status": "ACTIVE", "matched_signals": matched}
```

> **참고**: 이 테이블은 Phase 2 품질 평가에서 실제 매칭 효과를 검증한 후 조정한다.
> 현재는 v10 온톨로지 설계자의 도메인 지식에 기반한 초기 버전이다.

### 5.2 role_fit — ScopeType 변환 통합 **(v6 변경 M-2)**

> v10 `02_candidate_context.md`의 `ic_to_seniority()`와 `get_candidate_seniority()` 변환 함수를 통합하여,
> Vacancy의 seniority와 Candidate의 scope_type 간 비교를 가능하게 한다.

```python
# (v6 변경 M-2) IC scope_type → seniority 변환 매핑
# v10 02_candidate_context.md에서 가져옴
def ic_to_seniority(scope_type: str, total_years: int) -> str:
    """(v6 변경 M-2) Candidate의 scope_type(IC/LEAD/HEAD/FOUNDER)을
    Vacancy의 seniority(JUNIOR/MID/SENIOR/LEAD/HEAD)로 변환.

    IC인 경우 경력 연수로 세분화, LEAD/HEAD/FOUNDER는 직접 매핑."""
    if scope_type == "IC":
        if total_years <= 3:
            return "JUNIOR"
        elif total_years <= 7:
            return "MID"
        else:
            return "SENIOR"
    elif scope_type == "LEAD":
        return "LEAD"
    elif scope_type == "HEAD":
        return "HEAD"
    elif scope_type == "FOUNDER":
        return "HEAD"  # FOUNDER → HEAD급으로 간주
    return "UNKNOWN"

def get_candidate_seniority(candidate_ctx) -> str:
    """(v6 변경 M-2) Candidate의 최근 경력에서 seniority를 추정.
    가장 최근 experience의 scope_type + 총 경력 연수 기반."""
    if not candidate_ctx.experiences:
        return "UNKNOWN"

    latest_exp = max(candidate_ctx.experiences, key=lambda e: e.period_start or "")
    total_years = candidate_ctx.role_evolution.total_experience_years or 0
    return ic_to_seniority(latest_exp.scope_type, total_years)

# (v6 변경 M-2) Seniority 레벨 순서 (비교용)
SENIORITY_ORDER = {
    "JUNIOR": 1, "MID": 2, "SENIOR": 3, "LEAD": 4, "HEAD": 5, "UNKNOWN": 0
}

def compute_role_fit(vacancy, candidate_ctx):
    """(v6 변경 M-2) Vacancy seniority와 Candidate seniority 비교.
    ScopeType 변환 함수를 활용하여 동일 척도에서 비교."""
    vacancy_seniority = vacancy.seniority  # JUNIOR / MID / SENIOR / LEAD / HEAD
    candidate_seniority = get_candidate_seniority(candidate_ctx)

    v_level = SENIORITY_ORDER.get(vacancy_seniority, 0)
    c_level = SENIORITY_ORDER.get(candidate_seniority, 0)

    if v_level == 0 or c_level == 0:
        return {"score": 0.5, "status": "INACTIVE", "reason": "unknown_seniority"}

    diff = abs(v_level - c_level)
    if diff == 0:
        score = 1.0
    elif diff == 1:
        score = 0.7
    elif diff == 2:
        score = 0.3
    else:
        score = 0.1

    return {
        "score": score,
        "status": "ACTIVE",
        "vacancy_seniority": vacancy_seniority,
        "candidate_seniority": candidate_seniority,
        "level_diff": diff,
    }
```

### 5.3 MAPPED_TO 그래프 반영 **(v6 신설 H-6)**

> Pipeline D/E에서 계산된 MappingFeatures 결과를 그래프에 MAPPED_TO 엣지로 반영한다.
> 이를 통해 그래프 탐색 시 Vacancy→Person 매핑을 직접 조회할 수 있다.

```python
def reflect_mapping_to_graph(vacancy_id, candidate_id, mapping_features, tx):
    """(v6 신설 H-6) MappingFeatures 결과를 Graph에 MAPPED_TO 엣지로 반영.
    Pipeline D 계산 완료 후 호출."""
    overall_score = compute_overall_score(mapping_features)

    tx.run("""
        MATCH (v:Vacancy {vacancy_id: $vacancy_id})
        MATCH (p:Person {person_id: $person_id})
        MERGE (v)-[m:MAPPED_TO]->(p)
        SET m.overall_score = $score,
            m.stage_match = $stage_match,
            m.vacancy_fit = $vacancy_fit,
            m.domain_fit = $domain_fit,
            m.culture_fit = $culture_fit,
            m.role_fit = $role_fit,
            m.generated_at = datetime()
    """, vacancy_id=vacancy_id,
        person_id=candidate_id,
        score=overall_score,
        stage_match=mapping_features.stage_match.score,
        vacancy_fit=mapping_features.vacancy_fit.score,
        domain_fit=mapping_features.domain_fit.score,
        culture_fit=mapping_features.culture_fit.score,
        role_fit=mapping_features.role_fit.score)

def compute_overall_score(mapping_features) -> float:
    """(v6 신설 H-6) 가중 평균 기반 overall_score 계산"""
    weights = {
        "stage_match": 0.15,
        "vacancy_fit": 0.25,
        "domain_fit": 0.25,
        "culture_fit": 0.10,
        "role_fit": 0.25,
    }
    total = 0.0
    for feature_name, weight in weights.items():
        feature = getattr(mapping_features, feature_name)
        if feature.status == "ACTIVE":
            total += feature.score * weight
        else:
            # INACTIVE 피처는 가중치를 다른 피처에 재분배
            pass
    return total

# Pipeline D/E 실행 시 호출
def run_pipeline_d_e(vacancy, shortlisted_candidates, tx):
    """(v6 변경 H-6) Pipeline D/E에 MAPPED_TO 그래프 반영 단계 추가"""
    for candidate_ctx in shortlisted_candidates:
        # 기존 MappingFeatures 계산
        mapping_features = compute_mapping_features(vacancy, candidate_ctx)

        # BigQuery 적재 (기존)
        save_to_bigquery(vacancy, candidate_ctx, mapping_features)

        # (v6 신설 H-6) Graph 반영
        reflect_mapping_to_graph(
            vacancy_id=generate_vacancy_id(vacancy.job_id),
            candidate_id=candidate_ctx.candidate_id,
            mapping_features=mapping_features,
            tx=tx
        )
```

**MAPPED_TO 엣지 활용 시나리오**:
- `MATCH (v:Vacancy)-[m:MAPPED_TO]->(p:Person) WHERE m.overall_score > 0.7 RETURN p ORDER BY m.overall_score DESC`
- Vacancy → Person 매핑 결과를 그래프에서 직접 탐색 가능
- BigQuery와 이중 저장이지만, 그래프 기반 탐색/추천에 필수

---

## 6. 처리 볼륨과 총비용 추정

### 가정 (가상 — 실제 데이터 확인 필요)

| 항목 | 가정값 | 근거 |
|---|---|---|
| JD 보유량 | 10,000건 | 자사 보유 + 크롤링 |
| 이력서 보유량 | 500,000건 | 150GB / 이력서 평균 300KB |
| 이력서당 평균 경력 수 | 3건 | 경력직 기준 |
| 매핑 대상 쌍 | 5,000,000건 | JD x 상위 후보 500명 |

### 비용 산출

| 파이프라인 | 건수 | 건당 비용 | 총비용 |
|---|---|---|---|
| CompanyContext 생성 | 10,000 | $0.0008 | **$8** |
| CandidateContext 생성 | 500,000 | $0.0023 | **$1,150** |
| Graph 적재 | 510,000 | ~0 (compute) | 인프라 비용 |
| Embedding (Vector Index) **(v6 변경 H-2)** | 1,500,000 chapters | $0.000025 | **$37.5** |
| MappingFeatures 계산 | 5,000,000 | $0.00001 | **$50** |
| **LLM 총비용** | | | **~$1,245.5** |

> **(v6 변경 H-2)**: Embedding 비용이 `text-multilingual-embedding-002` ($0.025/1M 토큰) 기준으로 재산출됨.

**원화 환산**: ~170만 원 (Haiku 기준, 2026-03 환율 1,370원/$)

### Sonnet 사용 시 비용 비교

| 모델 | CandidateContext 비용 | 총 LLM 비용 | 원화 |
|---|---|---|---|
| Claude Haiku 4.5 | $1,150 | ~$1,245.5 | ~170만 원 |
| Gemini 2.0 Flash | $875 | ~$970 | ~133만 원 |
| Claude Sonnet 4.6 | $5,750 | ~$5,845 | ~800만 원 |
| GPT-4o-mini | $1,725 | ~$1,820 | ~250만 원 |
| GPT-4o | $28,750 | ~$28,845 | ~3,950만 원 |

> **권장**: v1 MVP에서는 Haiku/Flash급으로 시작하고, 추출 품질 평가 후 필요 시 Sonnet급으로 업그레이드

---

## 7. v1 하이브리드 비율 재정의

### 이력서(CandidateContext) 추출 기준

| 추출 대상 | Rule | LLM | 비고 |
|---|---|---|---|
| company, role_title, period | **70%** | 30% fallback | 블록 패턴 커버리지 |
| tech_stack | **75%** | 25% (LLM에서 추가 발견) | 기술 사전 기반 |
| scope_type | 0% | **100%** | 문맥 해석 필수 |
| outcomes | 0% | **100%** | 성과 추출은 LLM만 가능 |
| situational_signals | 0% | **100%** | taxonomy 분류 = LLM |
| past_company_context | **100%** | 0% | NICE Lookup |
| role_evolution | 0% | **100%** | 전체 커리어 추론 |
| domain_depth | 0% | **100%** | 도메인 판별 = LLM |
| work_style_signals **(v6 확장 M-3)** | 0% | **100%** | experiment_orientation, collaboration_style 추가 |

**전체 가중 비율**: Rule ~25%, LLM ~75% (필드 중요도 가중)

### JD(CompanyContext) 추출 기준

| 추출 대상 | Rule | LLM | 비고 |
|---|---|---|---|
| company_profile | **100%** | 0% | NICE Lookup |
| stage_estimate | **75%** | 25% | Rule 우선, LLM fallback |
| vacancy + role_expectations | 0% | **100%** | 문맥 해석 필수 (통합 프롬프트) |
| operating_model | **40%** (키워드) | 60% (보정) | 하이브리드 |
| domain_positioning **(v6 추가 L-3)** | 0% | **100%** | JD 문맥에서 추출 |
| structural_tensions **(v6 추가 H-4)** | 0% | **100%** | 크롤링 데이터 필요 (선택적) |

---

## 8. 에러 핸들링 및 배치 처리 전략

> **v3 신설**: v2 리뷰에서 지적된 에러 핸들링 부재, 배치 아키텍처 미상세를 보강.

### 8.1 에러 유형별 처리 정책

| 에러 유형 | 원인 | 정책 | 최대 재시도 | 비고 |
|---|---|---|---|---|
| **LLM API 호출 실패** | 네트워크, 서버 에러 (5xx) | **재시도** (exponential backoff) | 3회 | 1초 → 2초 → 4초 |
| **LLM API Rate Limit** | 429 Too Many Requests | **대기 후 재시도** (Retry-After 헤더) | 5회 | Batch API 사용 시 거의 없음 |
| **LLM 응답 파싱 실패** | JSON 형식 오류 | **재시도** (temperature 0.1 상향) | 2회 | 2회 실패 시 skip + 로그 |
| **LLM 응답 스키마 불일치** | 필수 필드 누락 | **부분 수용** (있는 필드만 사용) | 0 | null로 graceful degradation |
| **NICE DB 타임아웃** | DB 부하, 네트워크 | **재시도** | 3회 | 실패 시 past_company_context = null |
| **NICE DB 매칭 실패** | 회사명 미등록 | **skip** (graceful degradation) | 0 | 정상 케이스로 처리 |
| **이력서 파싱 실패** | 손상된 파일, 미지원 형식 | **skip + 로그** | 0 | dead-letter 큐로 이동 |
| **Graph 적재 실패** | Neo4j 연결 문제, 제약 조건 위반 | **재시도** (트랜잭션 롤백 후) | 3회 | 실패 시 skip + 로그 |
| **Embedding API 실패** | Vertex AI 서비스 에러 **(v6 추가 H-2)** | **재시도** (exponential backoff) | 3회 | 실패 시 embedding = null |

### 8.2 evidence_span 후처리 검증

> **v4 신설**: LLM이 원문에 없는 span을 생성(hallucination)하는 케이스를 방지.
> **v5 변경**: strict match → normalized match로 개선. LLM이 공백/줄바꿈을 정규화하여 인용하는 케이스의 false negative를 방지.

```python
import re

def normalize_text(text: str) -> str:
    """공백, 줄바꿈, 탭을 단일 공백으로 정규화"""
    return re.sub(r'\s+', ' ', text).strip()

def validate_evidence_spans(extraction_result, original_text, source_type="jd"):
    """LLM 추출 결과의 evidence_span이 원문에 실제로 존재하는지 검증.
    (v6 변경 M-4) field_confidence = min(extraction_confidence, source_ceiling) 적용."""
    normalized_original = normalize_text(original_text)

    for field_name, field_value in extraction_result.items():
        if hasattr(field_value, 'evidence_span') and field_value.evidence_span:
            span = field_value.evidence_span
            normalized_span = normalize_text(span)

            if normalized_span in normalized_original:
                field_value.evidence_span_verified = True
            else:
                # span이 정규화 후에도 원문에 없음 → confidence 하향
                field_value.confidence *= 0.5
                field_value.evidence_span_verified = False
                logger.warning(f"evidence_span not found in original: {span[:50]}...")

        # (v6 변경 M-4) source_ceiling 적용
        if hasattr(field_value, 'confidence'):
            field_category = getattr(field_value, 'field_category', None)
            field_value.confidence = compute_field_confidence(
                field_value.confidence, source_type, field_category
            )
```

- **비용**: 0 (문자열 정규화 + 포함 검사만)
- **예상 hallucination 비율**: 5~15% (Phase 0 PoC에서 실측)
- **정책**: span 미검증 건은 추출 결과를 유지하되 confidence를 50% 감쇄
- **v5 개선**: 공백/줄바꿈 정규화로 false negative 10~20% 감소 예상
- **(v6 변경 M-4)**: `compute_field_confidence()` 적용으로 source tier 기반 ceiling 강제

### 8.3 Dead-Letter 큐 및 재처리

```python
class DeadLetterHandler:
    """처리 실패 건을 별도 관리하여 이후 수동/자동 재처리"""
    def handle_failure(self, item_id, pipeline, error_type, error_msg):
        self.dead_letter_store.save({
            "item_id": item_id,
            "pipeline": pipeline,      # "company_context" / "candidate_context"
            "error_type": error_type,   # "parse_fail" / "llm_fail" / "graph_fail"
            "error_message": error_msg,
            "failed_at": datetime.utcnow(),
            "retry_count": 0,
            "status": "PENDING"         # PENDING → RETRYING → RESOLVED / SKIPPED
        })
```

- **에러율 가정**: 전체 처리 중 2-5% 실패 예상
- **재처리 주기**: 일 1회 dead-letter 큐 자동 재시도 → 2회 실패 시 수동 검토 전환

### 8.4 배치 처리 / 병렬 설계 (500K 이력서)

```
[Batch Processing Architecture]

이력서 500K
    │
    ├─ 중복 제거 (§3.4) → canonical 이력서만 처리
    │
    ├─ Chunk 분할 (1,000건/chunk x 500 chunks)
    │
    ├─ Batch API 요청 (chunk 단위)
    │   ├─ Anthropic Batch API: 최대 10,000건/batch, 24시간 SLA
    │   ├─ 동시 배치 수: 5~10개 (API quota에 따라 조정)
    │   └─ 예상 처리 시간: 2~3일 (500K / 50K/일)
    │
    ├─ 결과 수집 + 파싱
    │   ├─ 성공: CandidateContext JSON → Graph 적재 큐
    │   └─ 실패: Dead-Letter 큐
    │
    └─ Graph 적재 (비동기, 병렬 worker 4~8개)
        ├─ Neo4j Transaction 배치: 100건/트랜잭션
        ├─ Industry 마스터 노드 사전 확인 (v6 추가 H-1)
        └─ 예상 적재 시간: 1~2일
```

**처리 오케스트레이션**: Cloud Workflows (GCP) 또는 Prefect (셀프 호스팅) 권장
- 단계 간 의존성 관리 (파싱 → LLM 추출 → Graph 적재)
- 재시도/실패 알림/진행률 모니터링 내장

---

## 9. ML Knowledge Distillation 적용 범위 (요약)

> **상세 실행 계획은 `04_execution_plan.md` Phase 2-3 참조**

v1의 "LLM Teacher → ML Student" 전략은 v10에서도 유효하지만 **적용 범위가 제한적**이다.

- **ML 대체 가능**: scope_type 분류, seniority 분류 (KLUE-BERT 기반, Phase 2 선택적)
- **ML 대체 불가**: outcomes 추출, situational_signals, vacancy scope_type, role_evolution, operating_model 보정
- **비용 절감 효과**: 이력서 1건당 LLM 토큰 22% 감소, 500K 기준 약 $250 절감 (Batch 기준)

**결론**: ML Distillation은 v10에서 **20-30% 수준**의 비용 절감만 가능. LLM 비용 최적화(모델 선택, Batch API)가 더 큰 영향을 미친다.
