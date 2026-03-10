# v10 온톨로지 기반 추출 파이프라인 설계 — DB 기반 재설계

> v10 CompanyContext / CandidateContext / Graph Schema에 정합하는 추출 파이프라인.
> v7의 파일 파싱 기반 접근을 **resume-hub/job-hub/code-hub DB 기반**으로 재설계한다.
>
> 작성일: 2026-03-08 (v2 기반)
> 개정일: 2026-03-08 (v6 — v10 온톨로지 정합: Industry 노드, Embedding 확정, REQUIRES_ROLE/MAPPED_TO 엣지, source tier, ScopeType 변환)
> 개정일: 2026-03-08 (v7 — LLM 출력 파싱 실패 전략 §8.3 신설)
> 개정일: 2026-03-09 (v8 — DB 기반 파이프라인 재설계: resume-hub/job-hub/code-hub 직접 조회, 전처리/파싱 제거, 토큰 44%/40% 절감)

---

## 0. 설계 원칙

| 원칙 | 설명 |
|---|---|
| **v10 스키마 정합** | 추출 결과가 v10 JSON 스키마(CompanyContext, CandidateContext)에 직접 매핑 |
| **DB-first, LLM-for-reasoning** | 정형/팩트 필드는 DB 직접 조회, 추론/해석 필드만 LLM **(v8 변경: Rule-first → DB-first)** |
| **Graceful Degradation** | null 허용 필드 명시, 비활성 피처 자동 처리 |
| **Evidence 필수** | 모든 추출에 source_id + span + confidence 첨부 |
| **비용 현실주의** | LLM 입력에 DB 정형 필드를 사전 제공하여 토큰 절감 |
| **Fail-safe** | 에러 유형별 retry/skip/fallback 정책으로 대량 처리 안정성 확보 |
| **Idempotency** | 동일 입력의 재처리가 Graph 데이터를 오염시키지 않음 |
| **Source Tier Confidence** | `field_confidence = min(extraction_confidence, source_ceiling)` 규칙 적용 |
| **2-Tier Entity Normalization** | Tier 1: 대학교/회사명/상위 스킬은 case-insensitive 정규화, Tier 2: 스킬/전공/직무는 embedding 유사도(threshold 기반 연속 점수) **(v8.1 신설)** |

---

## 1. 파이프라인 전체 구조

```
[데이터 소스 — v8 변경]
├─ resume-hub DB (Career, Skill, Education, CareerDescription, SelfIntroduction)
├─ job-hub DB (job, overview, requirement, work_condition, skill)
├─ code-hub DB (HARD_SKILL, SOFT_SKILL, JOB_CLASSIFICATION, INDUSTRY)
├─ NICE 기업 정보 DB
└─ (향후) 크롤링 / 투자DB

    ▼

[Pipeline A: CompanyContext 생성 — v8 변경]
    job-hub + code-hub + NICE → CompanyContext JSON
    ├─ tech_stack (DB 조회 → 2-Tier 정규화: Tier 1 case-insensitive + Tier 2 embedding) — LLM 불필요
    ├─ industry (DB 직접: overview.industry_codes → code-hub INDUSTRY) — LLM 불필요
    ├─ career_types, education, designation (DB 직접: requirement, overview) — LLM 불필요
    ├─ company_profile (NICE Lookup)
    ├─ stage_estimate (Rule + LLM)
    ├─ vacancy + role_expectations (LLM — 정형 필드 사전 제공, 토큰 44% 절감)
    ├─ operating_model (키워드 + LLM)
    ├─ domain_positioning (Optional)
    └─ structural_tensions (크롤링 데이터 확보 시 활성화)

    ▼

[Pipeline B: CandidateContext 생성 — v8 변경]
    resume-hub + code-hub + NICE → CandidateContext JSON
    ├─ 중복 감지 (SiteUserMapping 기반) — v8 변경: SimHash → SiteUserMapping
    ├─ experiences[] 추출
    │   ├─ 기본 정보 (DB 직접: Career 엔티티) — 파싱/Rule 추출 제거
    │   ├─ tech_stack (DB 조회 → 2-Tier 정규화) — LLM 불필요
    │   ├─ scope_type, outcomes (LLM — positionGradeCode 힌트 제공)
    │   ├─ situational_signals (LLM + taxonomy)
    │   └─ past_company_context (BRN 기반 NICE 직접 매칭 — 매칭률 80-90%)
    ├─ role_evolution (LLM)
    ├─ domain_depth (LLM)
    └─ work_style_signals (LLM)

    ▼

[Pipeline C: Graph 적재] — v7과 동일
    CompanyContext + CandidateContext → Neo4j

    ▼

[Pipeline D: MappingFeatures 계산] — v7과 동일
    CompanyContext × CandidateContext → MappingFeatures JSON

    ▼

[Pipeline E: 서빙] — v7과 동일
    MappingFeatures → BigQuery 테이블
```

### 1.1 v7 대비 변경 요약

| 영역 | v7 | v8 | 효과 |
|---|---|---|---|
| 이력서 전처리 | PDF/DOCX/HWP 파싱 → 텍스트 → 섹션 분할 → 블록 분리 | **제거** (Career 엔티티가 이미 분리) | 2주 → 0주 |
| JD 전처리 | JD 텍스트 파싱 → 섹션 분할 | **제거** (job-hub 테이블 직접 조회) | - |
| 기본 필드 추출 | Rule (정규식) | **DB 직접 조회** | Rule 모듈 불필요 |
| 기술 정규화 | 기술 사전 2,000개 + fuzzy | **2-Tier 정규화**: Tier 1(case-insensitive) + Tier 2(embedding 유사도) | code-hub 코드 참조 + 비표준 값 정규화 **(v8.1 변경)** |
| NICE 매칭 | 회사명 fuzzy match (60%) | **BRN 직접 매칭 (80-90%)** | 매칭률 대폭 향상 |
| 이력서 중복 | SimHash + candidate_id | **SiteUserMapping + candidate_id** | 간소화 |
| CompanyContext LLM | ~3,900 tok/건 | **~2,200 tok/건** | 44% 절감 |
| CandidateContext LLM | ~3,000 tok/건 | **~1,800 tok/건** | 40% 절감 |

### 1.2 structural_tensions Pydantic 스키마 — v6/v7과 동일

```python
class StructuralTensionType(str, Enum):
    TECH_DEBT_VS_FEATURES = "tech_debt_vs_features"
    SPEED_VS_RELIABILITY = "speed_vs_reliability"
    FOUNDER_VS_PROFESSIONAL_MGMT = "founder_vs_professional_mgmt"
    EFFICIENCY_VS_GROWTH = "efficiency_vs_growth"
    SCALING_LEADERSHIP = "scaling_leadership"
    INTEGRATION_TENSION = "integration_tension"
    BUILD_VS_BUY = "build_vs_buy"
    PORTFOLIO_RESTRUCTURING = "portfolio_restructuring"

class DomainPositioning(BaseModel):
    market_segment: Optional[str] = None
    competitive_landscape: Optional[str] = None
    product_description: Optional[str] = None
```

---

## 2. Pipeline A: CompanyContext 생성

### 입력 **(v8 변경)**
- job-hub DB: job, overview, requirement, work_condition, skill 테이블
- code-hub DB: HARD_SKILL, INDUSTRY 코드
- NICE 기업 정보 (BRN 기반 조회)
- (선택) 크롤링 데이터

### 2.1 DB 직접 조회 필드 (LLM 불필요) **(v8 신설)**

```python
def extract_company_fields_from_db(job_id: str) -> dict:
    """v8 신설: job-hub + code-hub에서 정형 필드 직접 조회. LLM 불필요."""
    overview = job_hub.get_overview(job_id)
    requirement = job_hub.get_requirement(job_id)
    skills = job_hub.get_skills(job_id)

    # tech_stack: job-hub.skill → 2-Tier 정규화 (v8.1 변경)
    tech_stack = []
    for skill in skills:
        normalized = normalize_skill(skill)  # 2-Tier 정규화 적용
        tech_stack.append(normalized)

    # industry: overview.industry_codes → code-hub INDUSTRY 매핑
    industry_codes = overview.industry_codes or []
    industries = [code_hub.get_industry(code) for code in industry_codes]

    # career_types, education, designation: requirement, overview에서 직접
    career_types = requirement.careers if requirement else None  # JSONB
    education_req = requirement.education if requirement else None
    designation = overview.designation if overview else None

    return {
        "tech_stack": tech_stack,
        "industry_codes": industry_codes,
        "industry_labels": [i.label for i in industries if i],
        "career_types": career_types,
        "education_requirement": education_req,
        "designation": designation,
    }
```

- **비용**: DB 조회 0 + Tier 2 embedding 정규화 비용 (§4.3.1 참조)
- **커버리지**: tech_stack 90%+(Tier 1 정규화 후, Tier 2 embedding으로 추가 매핑), industry 95%+

### 2.2 company_profile — NICE Lookup (Rule, LLM 불필요)

```python
def extract_company_profile(job_data, nice_data):
    """NICE DB에서 직접 조회. v8: BRN 기반 매칭."""
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

- **confidence**: 0.70 (NICE ceiling)

#### Evidence 기반 field_confidence 규칙 — v6/v7과 동일

```python
SOURCE_CEILING = {
    "nice":           0.70,
    "db_structured":  0.80,   # v8 신규: DB 정형 필드 ceiling (NICE보다 높음)
    "jd":             0.55,
    "resume":         0.55,
    "news":           0.50,
    "review":         0.40,
    "investment_db":  0.65,
}
```

> **(v8 변경)**: `db_structured` source type 추가 — resume-hub/job-hub/code-hub에서 직접 조회한 정형 필드에 적용. NICE(0.70)보다 높은 0.80 ceiling 부여 (데이터 입력 시점에 이미 검증됨).

### 2.3 stage_estimate — Rule + LLM Fallback — v7과 동일

### 2.4 vacancy + role_expectations — LLM 통합 추출 **(v8 변경: 입력 축소)**

> v8에서는 정형 필드(tech_stack, industry, career_types 등)를 LLM에 사전 제공하여
> LLM이 scope_type, seniority, operating_model 추론에만 집중하도록 한다.

```python
VACANCY_AND_ROLE_PROMPT_V8 = """
아래 채용 공고 정보를 분석하여 JSON으로 응답하세요.

[이미 추출된 정형 정보 — DB에서 조회됨]
기술 스택: {tech_stack}
업종: {industry_labels}
경력 요건: {career_types}
학력 요건: {education_requirement}
직급: {designation}

[채용 공고 상세 설명 — LLM 분석 필요]
{descriptions}

[1. Vacancy 추출]
- scope_type: BUILD_NEW / SCALE_EXISTING / RESET / REPLACE / UNKNOWN
- seniority: JUNIOR / MID / SENIOR / LEAD / HEAD / UNKNOWN
- role_title: 직무명 (원문 그대로)
- team_context: 팀 구성/규모 (추출 가능시만, 없으면 null)

[2. Role Expectations 추출]
- responsibilities: 주요 업무 (리스트)
- requirements: 필수 자격 — 위 정형 정보를 참고하되, 설명에서 추가 발견 시 보완
- preferred: 우대 사항 (리스트)

[규칙]
- 근거 문장(span)을 설명에서 인용하세요.
- 인용할 수 없으면 UNKNOWN으로 분류하세요.
- confidence: 0.0~1.0

[출력 JSON]
{
  "vacancy": { "scope_type": ..., "seniority": ..., "role_title": ..., "team_context": ..., "evidence": [...] },
  "role_expectations": { "responsibilities": [...], "requirements": [...], "preferred": [...] }
}
"""
```

- **v8 토큰 절감**: ~3,900 → ~2,200 tok/건 (44% 절감)
  - 절감 근거: JD 전문이 아닌 descriptions JSONB만 전달, tech_stack/industry 등은 이미 추출된 정형 데이터로 제공
- **모델**: Claude Haiku 4.5 / Gemini Flash 2.0

### 2.5 operating_model — 키워드 + LLM 보정 — v7과 동일

> v8 변경: 입력 텍스트가 JD 전문이 아닌 `overview.descriptions` JSONB로 변경됨.

### 2.6 structural_tensions 추출 — v6/v7과 동일

### CompanyContext 생성 비용 요약 (1건당) **(v8 변경)**

| 필드 | 방법 | 토큰 (입출력) | 비용 (Haiku 일반) | 비용 (Haiku Batch 50%) |
|---|---|---|---|---|
| tech_stack, industry, career_types | **DB 직접 조회** **(v8)** | 0 | $0 | $0 |
| company_profile | NICE Lookup | 0 | $0 | $0 |
| stage_estimate | Rule (80%) / LLM (20%) | 평균 ~100 | ~$0.00002 | ~$0.00001 |
| vacancy + role_expectations | LLM (정형 필드 사전 제공) | **~1,800** **(v8: 3,000→1,800)** | ~$0.00036 | ~$0.00018 |
| operating_model | 키워드 + LLM 보정 | **~300** **(v8: 800→300)** | ~$0.00006 | ~$0.00003 |
| structural_tensions | LLM (크롤링 시만) | ~2,000 (선택적) | ~$0.0004 | ~$0.0002 |
| **합계 (JD only)** | | **~2,200** **(v8: 3,900→2,200)** | **~$0.00044** | **~$0.00022** |
| **합계 (JD + 크롤링)** | | **~4,200** **(v8: 5,900→4,200)** | **~$0.00084** | **~$0.00042** |

---

## 3. Pipeline B: CandidateContext 생성

### 입력 **(v8 변경)**
- resume-hub DB: Career, Skill, Education, CareerDescription, SelfIntroduction
- code-hub DB: HARD_SKILL, JOB_CLASSIFICATION
- NICE 기업 정보 (BRN 기반 조회)

### 3.1 전처리: DB 조회 기반 **(v8 변경: 파싱 전체 제거)**

> v7의 PDF/HWP 파싱 → 텍스트 → 섹션 분할 → 경력 블록 분리가 **전체 제거**됨.
> resume-hub의 Career 엔티티가 이미 회사 단위로 분리되어 있으므로 직접 조회만 필요.

```
[v8: DB 조회 기반]
resume-hub DB
    │
    ├─ Career 엔티티 조회 (이미 회사 단위 분리)
    ├─ Skill 엔티티 조회 → code-hub HARD_SKILL 매핑
    ├─ CareerDescription 조회 → LLM 입력
    ├─ SelfIntroduction 조회 → LLM 보조 입력
    └─ SiteUserMapping 조회 → 중복 감지

[v7 대비 제거된 단계]
    ├─ ~~PDF/DOCX/HWP → 텍스트 변환~~ 제거
    ├─ ~~섹션 분할 (경력, 학력, 기술)~~ 제거
    ├─ ~~경력 블록 분리 (회사별 단위)~~ 제거
    └─ ~~Rule 기반 기본 정보 추출 (정규식)~~ 제거
```

### 3.2 Experience 추출 — DB 매핑 + LLM 계층 **(v8 변경)**

#### Step 1: DB 직접 매핑 (비용 0, LLM 불필요) **(v8 변경: Rule → DB)**

```python
def map_career_to_basic(career, skills) -> dict:
    """v8: Career 엔티티에서 정형 필드 직접 매핑. Rule 추출 불필요."""
    # tech_stack: Skill → 2-Tier 정규화 (v8.1 변경)
    tech_stack = []
    for skill in skills:
        if skill.career_id == career.id:
            normalized = normalize_skill(skill)  # 2-Tier 정규화 적용
            tech_stack.append(normalized)

    # company: Tier 1 정규화 (case-insensitive)
    company = normalize_company_name(career.companyName)  # Tier 1

    # role_title: Tier 2 정규화 (embedding 유사도)
    role_title = normalize_role(career.positionTitleCode, career.positionTitle)  # Tier 2

    return {
        "company": company,
        "role_title": role_title,
        "period_start": career.startDate,
        "period_end": career.endDate,
        "tech_stack": tech_stack,
        "position_grade": career.positionGradeCode,  # scope_type 힌트
        "brn": career.businessRegistrationNumber,     # NICE 매칭 키
    }
```

- **v7과의 차이**: Rule 추출 (정규식 패턴 매칭)이 완전히 제거됨
- **v8.1 변경**: DB 값이 비표준화된 상태이므로 2-Tier 정규화 레이어 추가
- **커버리지**: company 100% (Tier 1 정규화), period 100%, tech_stack 90%+ (Tier 1+2 정규화)

#### Step 2: LLM 추출 (Experience별, 핵심) **(v8 변경: 입력 축소)**

```python
def build_llm_input(career, career_descs, self_intros) -> str:
    """v8: LLM 입력을 DB 텍스트 필드에서 구성."""
    parts = []
    # workDetails가 주요 LLM 입력
    if career.workDetails:
        parts.append(career.workDetails)
    # CareerDescription이 보조 입력
    for desc in career_descs:
        if desc.career_id == career.id and desc.description:
            parts.append(desc.description)
    # SelfIntroduction은 전체 커리어 맥락 제공
    for intro in self_intros:
        if intro.description:
            parts.append(f"[자기소개] {intro.description}")
    return "\n\n".join(parts)

EXPERIENCE_PROMPT_V8 = """
아래 경력 정보에서 다음을 추출하세요.

[이미 추출된 정형 정보 — DB에서 조회됨]
회사: {company}
직무: {role_title}
기간: {period_start} ~ {period_end}
기술 스택: {tech_stack}
직급 코드: {position_grade}

[경력 상세 텍스트 — LLM 분석 필요]
{text_input}

[필수 추출 항목]
1. scope_type: IC / LEAD / HEAD / FOUNDER / UNKNOWN
   - 직급 코드 "{position_grade}"를 참고하세요
2. scope_summary: 역할 범위 한 문장 요약
3. outcomes: 정량/정성 성과 목록
4. situational_signals: [Taxonomy: EARLY_STAGE, SCALE_UP, ...]

[규칙]
- 근거 없이 추론하지 마세요. 인용할 수 없으면 해당 항목을 생성하지 마세요.
- confidence: 0.0~1.0

[출력 JSON]
"""
```

- **v8 토큰 절감**: ~3,000 → ~1,800 tok/건 (40% 절감)
  - 절감 근거: 이력서 전문이 아닌 workDetails + CareerDescription만 전달
  - 기본 필드(회사/기간/기술)는 이미 추출된 정형 데이터로 제공하여 LLM 중복 추출 방지
- **v8 정확도 향상**: positionGradeCode를 scope_type 힌트로 제공 → 분류 정확도 향상 예상

#### Step 3: NICE Lookup — PastCompanyContext **(v8 변경: BRN 기반 직접 매칭)**

```python
def build_past_company_context(career) -> Optional[PastCompanyContext]:
    """v8: BRN 기반 직접 매칭 (v7의 회사명 fuzzy match → BRN 직접)"""
    # BRN 있는 경우: 직접 매칭 (매칭률 ~100%)
    if career.businessRegistrationNumber:
        nice = lookup_nice_by_brn(career.businessRegistrationNumber)
        if nice:
            years_gap = 2026 - career.endDate.year if career.endDate else 0
            confidence = max(0.20, 0.70 - years_gap * 0.08)  # BRN 매칭은 ceiling 0.70
            return PastCompanyContext(
                company_name=career.companyName,
                industry_code=nice.industry_code,
                employee_count=nice.employee_count,
                founded_year=nice.founded_year,
                stage_estimation_method="nice_brn_direct",  # v8: 방법 명시
                confidence=confidence,
            )

    # BRN 없는 경우: 회사명 fuzzy match fallback (v7 방식)
    nice = lookup_nice_fuzzy(career.companyName, threshold=0.85)
    if nice:
        years_gap = 2026 - career.endDate.year if career.endDate else 0
        confidence = max(0.20, 0.60 - years_gap * 0.08)  # fuzzy match는 ceiling 0.60
        return PastCompanyContext(
            company_name=career.companyName,
            industry_code=nice.industry_code,
            employee_count=nice.employee_count,
            founded_year=nice.founded_year,
            stage_estimation_method="nice_fuzzy_match",
            confidence=confidence,
        )

    return None  # NICE에 없는 회사
```

- **v8 매칭률**: BRN 있는 60% × ~100% + BRN 없는 40% × ~60% = **~84%** (v7: ~60%)

### 3.3 전체 커리어 수준 추출 — v7과 동일

### 3.4 이력서 중복 처리 전략 **(v8 변경: SiteUserMapping 기반)**

```python
def deduplicate_resumes(candidate_ids: list) -> list:
    """v8: SiteUserMapping 기반 중복 감지. SimHash 불필요."""

    # Case 1: 동일 candidate_id — 최신 Career만 처리 (v7과 동일)
    # DB에서 이미 candidate_id 기준으로 그룹핑 가능

    # Case 2: 다른 candidate_id, 동일인 — SiteUserMapping 기반 (v8 변경)
    #   SiteUserMapping 테이블에서 동일 siteUserId가 여러 사이트에 매핑된 경우 감지
    site_mappings = resume_hub.get_site_user_mappings(candidate_ids)
    grouped = group_by(site_mappings, key=lambda m: m.siteUserId)

    canonical_ids = []
    for site_user_id, mappings in grouped.items():
        if len(mappings) > 1:
            # 여러 사이트에서 동일인 → 가장 최신/완전한 이력서 선택
            selected = max(mappings, key=lambda m: m.updated_at)
            canonical_ids.append(selected.candidate_id)
            logger.info(f"Duplicate siteUserId={site_user_id}: {len(mappings)} entries")
        else:
            canonical_ids.append(mappings[0].candidate_id)

    return canonical_ids
```

- **v7 대비 변경**: SimHash 유사도 비교 제거 → SiteUserMapping 테이블 활용
- **이점**: 정확한 동일인 매핑 (사이트간 연동 데이터 활용)

### CandidateContext 생성 비용 요약 (이력서 1건당) **(v8 변경)**

| 추출 단계 | 방법 | 토큰 (입출력) | 비용 (Haiku 일반) | 비용 (Haiku Batch 50%) |
|---|---|---|---|---|
| 기본 필드 (회사/직무/기간/기술) | **DB 직접 조회** **(v8)** | 0 | $0 | $0 |
| ~~전처리 (파싱, 섹션분할)~~ | ~~Rule~~ | ~~0~~ | — | **제거** |
| Experience별 추출 (x3 평균) | LLM | **~5,400** **(v8: 9,000→5,400)** | ~$0.00108 | ~$0.00054 |
| PastCompanyContext (x3) | BRN NICE 직접 매칭 **(v8)** | 0 | $0 | $0 |
| 전체 커리어 (role_evolution 등) | LLM | ~2,500 | ~$0.0005 | ~$0.00025 |
| **합계** | | **~7,900** **(v8: 11,500→7,900)** | **~$0.00158** | **~$0.00079** |

> **v7 대비 변경**: 11,500 → 7,900 토큰 (31% 절감). Experience별 추출에서 토큰 40% 절감이 핵심.

---

## 4. Pipeline C: Graph 적재 — v7과 기본 동일

### 4.1 CompanyContext → Graph — v7과 동일

### 4.2 CandidateContext → Graph — v7과 동일

### 4.3 Entity Resolution + 2-Tier 정규화 **(v8.1 변경: 비표준 데이터 정규화 추가)**

> **v8.1 핵심 변경**: DB 데이터가 정형 컬럼에 존재하지만 값 자체가 표준화되지 않은 상태이다.
> 예: "자바", "JAVA", "java", "Java" 등이 혼재. 이를 해결하기 위해 2-Tier 정규화 전략을 도입한다.

#### 4.3.0 2-Tier Entity Normalization Strategy **(v8.1 신설)**

| Tier | 대상 | 방법 | 비용 | 정확도 |
|---|---|---|---|---|
| **Tier 1: 정규화** | 대학교, 회사명, 상위 스킬 카테고리 | case-insensitive 매칭 + 공백/특수문자 정규화 + alias 사전 | **0** (룰 기반) | 높음 (95%+) |
| **Tier 2: Embedding 유사도** | 스킬, 전공, 직무 | embedding vector cosine similarity + threshold 기반 연속 점수 | **embedding API 호출** | 중~높음 (threshold 의존) |

##### Tier 1: 정규화 (Case-Insensitive Matching)

```python
def normalize_tier1(value: str, entity_type: str) -> str:
    """Tier 1: 단순 정규화 — 대학교, 회사명, 상위 스킬 카테고리"""
    # Step 1: 기본 정규화 (소문자, 공백/특수문자 제거)
    normalized = value.strip().lower()
    normalized = re.sub(r'[()（）\s·•\-_]', '', normalized)

    # Step 2: alias 사전 조회 (entity_type별)
    alias_dict = TIER1_ALIAS[entity_type]  # e.g., {"서울대": "서울대학교", "(주)네이버": "네이버"}
    if normalized in alias_dict:
        return alias_dict[normalized]

    return normalized


# 적용 대상별 예시
TIER1_ALIAS = {
    "university": {
        "서울대": "서울대학교", "서울대학": "서울대학교",
        "kaist": "한국과학기술원", "카이스트": "한국과학기술원",
    },
    "company": {
        "네이버": "naver", "naver": "naver", "(주)네이버": "naver",
        "카카오": "kakao", "kakao": "kakao", "(주)카카오": "kakao",
    },
    "skill_category": {  # 상위 스킬 카테고리만 (e.g., "프론트엔드", "백엔드")
        "frontend": "프론트엔드", "front-end": "프론트엔드",
        "backend": "백엔드", "back-end": "백엔드",
    },
}
```

- **Tier 1 적용 조건**: 값의 변형이 대소문자/공백/특수문자 수준이고, alias 사전으로 충분히 커버 가능한 엔티티
- **alias 사전 규모**: 대학교 ~200개, 회사명 ~500개 (BRN null fallback), 상위 스킬 카테고리 ~50개
- **비용**: 0 (룰 기반, DB/API 호출 없음)

##### Tier 2: Embedding 유사도 (Threshold-Based Continuous Score)

```python
from typing import Optional, Tuple

# 사전 계산된 canonical embedding 캐시
CANONICAL_EMBEDDINGS: dict[str, dict[str, list[float]]] = {
    "skill": {},      # {"Python": [0.1, ...], "Java": [0.2, ...], ...}
    "major": {},      # {"컴퓨터공학": [...], "경영학": [...], ...}
    "role": {},       # {"백엔드 개발자": [...], "프로덕트 매니저": [...], ...}
}

SIMILARITY_THRESHOLDS = {
    "skill": 0.85,    # 스킬: 높은 threshold (동의어가 명확)
    "major": 0.80,    # 전공: 중간 threshold (유사 전공 포함)
    "role":  0.80,    # 직무: 중간 threshold (직무명 변형 다양)
}

def normalize_tier2(
    value: str,
    entity_type: str,  # "skill" | "major" | "role"
    embedding_fn=None,  # Vertex AI text-multilingual-embedding-002
) -> Tuple[str, float]:
    """
    Tier 2: Embedding 유사도 기반 정규화.
    Returns: (canonical_name, similarity_score)
    """
    # Step 1: Tier 1 정규화 먼저 적용 (기본 전처리)
    preprocessed = value.strip().lower()

    # Step 2: canonical 목록에서 exact match 시도
    canonicals = CANONICAL_EMBEDDINGS[entity_type]
    for canonical_name in canonicals:
        if preprocessed == canonical_name.lower():
            return (canonical_name, 1.0)

    # Step 3: Embedding 유사도 계산
    query_embedding = embedding_fn(preprocessed)  # 1 API call
    best_match, best_score = None, 0.0
    for canonical_name, canonical_emb in canonicals.items():
        score = cosine_similarity(query_embedding, canonical_emb)
        if score > best_score:
            best_match, best_score = canonical_name, score

    # Step 4: Threshold 판정
    threshold = SIMILARITY_THRESHOLDS[entity_type]
    if best_score >= threshold:
        return (best_match, best_score)
    else:
        # threshold 미달: 원본 유지 + 낮은 confidence
        return (value, best_score)


def normalize_skill(skill) -> dict:
    """스킬 정규화: code-hub 코드 참조 후 Tier 2 embedding fallback"""
    # Step 1: code-hub 코드가 있으면 직접 참조
    if skill.code:
        hard_skill = code_hub.get_hard_skill(skill.code)
        if hard_skill:
            return {"name": hard_skill.name, "canonical": True, "score": 1.0}

    # Step 2: Tier 2 embedding 유사도 매칭
    canonical, score = normalize_tier2(skill.name, "skill")
    return {"name": canonical, "canonical": score >= SIMILARITY_THRESHOLDS["skill"], "score": score}


def normalize_role(position_title_code: str, position_title: str) -> dict:
    """직무 정규화: code-hub 코드 참조 후 Tier 2 embedding fallback"""
    # Step 1: code-hub JOB_CLASSIFICATION 코드가 있으면 직접 참조
    if position_title_code:
        job_class = code_hub.get_job_classification(position_title_code)
        if job_class:
            return {"name": job_class.name, "canonical": True, "score": 1.0}

    # Step 2: Tier 2 embedding 유사도 매칭
    if position_title:
        canonical, score = normalize_tier2(position_title, "role")
        return {"name": canonical, "canonical": score >= SIMILARITY_THRESHOLDS["role"], "score": score}

    return {"name": position_title or "UNKNOWN", "canonical": False, "score": 0.0}
```

##### Canonical Embedding 사전 구축 (1회성)

```python
def build_canonical_embeddings():
    """
    Phase 1-1에서 1회 실행: canonical 엔티티의 embedding 사전 생성.
    이후 정규화 시 query embedding만 계산하면 됨.
    """
    # 스킬: code-hub HARD_SKILL 전체 + 수동 추가
    hard_skills = code_hub.get_all_hard_skills()  # ~2,000개
    skill_texts = [s.name for s in hard_skills]
    skill_embeddings = embedding_fn(skill_texts)  # 배치 임베딩
    CANONICAL_EMBEDDINGS["skill"] = dict(zip(skill_texts, skill_embeddings))

    # 전공: 대학교 전공 마스터 데이터 (~500개)
    majors = load_major_master()
    major_texts = [m.name for m in majors]
    major_embeddings = embedding_fn(major_texts)
    CANONICAL_EMBEDDINGS["major"] = dict(zip(major_texts, major_embeddings))

    # 직무: code-hub JOB_CLASSIFICATION 전체 (~300개)
    job_classes = code_hub.get_all_job_classifications()
    role_texts = [j.name for j in job_classes]
    role_embeddings = embedding_fn(role_texts)
    CANONICAL_EMBEDDINGS["role"] = dict(zip(role_texts, role_embeddings))
```

- **Canonical 목록 규모**: 스킬 ~2,000개, 전공 ~500개, 직무 ~300개
- **1회 embedding 비용**: ~2,800개 × 평균 10 토큰 × $0.0065/1M = **~$0.0002** (무시할 수준)
- **런타임 embedding 비용**: §6 비용 산출 참조

##### Tier 2 Embedding 비용 추정

| 대상 | 건수 | 건당 평균 항목 수 | 총 embedding 호출 | 토큰 (평균 10 tok) | 비용 ($0.0065/1M) |
|---|---|---|---|---|---|
| 이력서 스킬 | 500K 이력서 × 3 경력 | 5 스킬/경력 | ~7,500K (캐시 후 ~750K) | ~7.5M | **~$0.05** |
| 이력서 전공 | 500K 이력서 | 1 전공 | ~500K (캐시 후 ~50K) | ~0.5M | **~$0.003** |
| 이력서 직무 | 500K × 3 경력 | 1 직무/경력 | ~1,500K (캐시 후 ~150K) | ~1.5M | **~$0.01** |
| JD 스킬 | 10K JD | 8 스킬/JD | ~80K (캐시 후 ~8K) | ~0.08M | **~$0.001** |
| **합계** | | | **~958K (캐시 적용)** | **~9.6M** | **~$0.06** |

> **캐시 전략**: 동일 텍스트의 embedding은 캐시하여 재계산 방지. "자바"가 100K번 등장해도 embedding은 1번만 계산.
> **비용 영향**: Tier 2 embedding 정규화 비용은 **~$0.06**으로 전체 비용 대비 무시할 수준.

#### 4.3.1 Organization Entity Resolution **(v8 유지, Tier 1 정규화 적용)**

```python
def resolve_org_id(career) -> Optional[str]:
    """v8: BRN 기반 org_id 매핑이 주 경로. 회사명은 Tier 1 정규화."""
    # Step 1: BRN 기반 직접 매핑 (v8 주 경로)
    if career.businessRegistrationNumber:
        nice = lookup_nice_by_brn(career.businessRegistrationNumber)
        if nice:
            return nice.org_id

    # Step 2: 회사명 Tier 1 정규화 후 사전 조회
    normalized = normalize_tier1(career.companyName, "company")
    canonical = COMPANY_ALIAS_DICT.get(normalized)
    if canonical:
        return canonical.org_id

    # Step 3: 회사명 NICE fuzzy match (v7 방식 fallback)
    nice = lookup_nice_fuzzy(career.companyName, threshold=0.85)
    if nice:
        return nice.org_id

    return None
```

- **v8 변경**: 회사명 정규화 사전 규모 대폭 축소 (~1,000개 → BRN null fallback용 ~500개)
- **v8.1 변경**: Tier 1 정규화(case-insensitive + alias) 적용하여 매칭률 향상
- **BRN 기반 매칭이 주 경로**: 60%의 Career가 BRN → org_id 직접 매핑

### 4.4 Skill/Role/Major 정규화 — Graph 적재 시 적용 **(v8.1 신설)**

```python
def normalize_and_merge_skill(tx, skill_data: dict):
    """Graph 적재 시 정규화된 Skill 노드로 MERGE"""
    if skill_data["canonical"]:
        # Tier 1/2 정규화 성공: canonical 이름으로 MERGE
        tx.run("""
            MERGE (s:Skill {name: $canonical_name})
            SET s.category = COALESCE(s.category, $category),
                s.aliases = CASE WHEN $raw_name IN s.aliases THEN s.aliases
                                 ELSE COALESCE(s.aliases, []) + [$raw_name] END,
                s.updated_at = datetime()
        """, canonical_name=skill_data["name"],
            raw_name=skill_data["raw_name"],
            category=skill_data.get("category"))
    else:
        # 정규화 실패 (threshold 미달): 원본 이름으로 MERGE + low_confidence 표시
        tx.run("""
            MERGE (s:Skill {name: $raw_name})
            SET s.normalization_score = $score,
                s.needs_review = true,
                s.updated_at = datetime()
        """, raw_name=skill_data["raw_name"], score=skill_data["score"])
```

- **Graph 효과**: "자바", "JAVA", "java" → 단일 `Skill {name: "Java"}` 노드로 MERGE
- **aliases 관리**: 원본 값을 aliases 배열에 보존하여 역추적 가능
- **needs_review 플래그**: threshold 미달 노드는 수동 검토 대상으로 태그

### 4.5 Graph 적재 전략 — v7과 동일

### 4.6 Vector Index — v7과 동일

### 4.7 Deterministic ID 생성 전략 — v7과 동일

### 4.8 Industry 마스터 데이터 사전 적재 **(v8 변경: code-hub 활용)**

```python
def preload_industry_master(tx):
    """v8: code-hub INDUSTRY 코드 + NICE 업종코드 병합 적재."""
    # code-hub INDUSTRY 계층 조회
    code_hub_industries = code_hub.get_all_industries()

    for ind in code_hub_industries:
        tx.run("""
            MERGE (ind:Industry {industry_code: $code})
            SET ind.label = $label,
                ind.level = $level,
                ind.parent_code = $parent_code,
                ind.source = 'code_hub',
                ind.updated_at = datetime()
        """, code=ind.code, label=ind.label,
            level=ind.level, parent_code=ind.parent_code)

    # NICE 업종코드도 병행 적재 (code-hub에 없는 코드)
    nice_industries = load_nice_industry_codes()
    for code in nice_industries:
        tx.run("""
            MERGE (ind:Industry {industry_code: $code})
            SET ind.label = COALESCE(ind.label, $label),
                ind.category_large = $cat_large,
                ind.source = COALESCE(ind.source, 'nice'),
                ind.updated_at = datetime()
        """, code=code.industry_code, label=code.label,
            cat_large=code.category_large)
```

---

## 5. Pipeline D: MappingFeatures 계산 — v7과 동일

### 5.0 Candidate Shortlisting — v7과 동일
### 5.1 계산 비용 — v7과 동일
### 5.2 role_fit — ScopeType 변환 — v6/v7과 동일
### 5.3 MAPPED_TO 그래프 반영 — v6/v7과 동일

---

## 6. 처리 볼륨과 총비용 추정

### 가정 **(v8 변경)**

| 항목 | v7 가정값 | v8 가정값 | 변경 |
|---|---|---|---|
| JD 보유량 | 10,000건 | 10,000건 | 동일 |
| 이력서 보유량 | 500,000건 (150GB / 300KB) | **500,000건** (resume-hub DB 카운트) | **산출 방식 변경** |
| 이력서당 평균 경력 수 | 3건 | 3건 | 동일 |
| 매핑 대상 쌍 | 5,000,000건 | 5,000,000건 | 동일 |
| CompanyContext LLM 토큰 | ~3,900 tok | **~2,200 tok** | **44% 절감** |
| CandidateContext LLM 토큰 | ~3,000 tok/경력 | **~1,800 tok/경력** | **40% 절감** |

### 비용 산출 **(v8 변경)**

| 파이프라인 | 건수 | 건당 비용 | v8 총비용 | v7 총비용 | 절감 |
|---|---|---|---|---|---|
| CompanyContext 생성 | 10,000 | **$0.00044** | **$4.4** | $8 | 45% |
| CandidateContext 생성 | 500,000 | **$0.00158** | **$790** | $1,150 | 31% |
| Graph 적재 | 510,000 | ~0 | 인프라 비용 | — | — |
| Embedding (Chapter/Vacancy) | 1,500,000 chapters | $0.000025 | **$37.5** | $37.5 | 0% |
| Embedding (Tier 2 정규화) **(v8.1)** | ~958K 유니크 (캐시 적용) | $0.0065/1M tok | **~$0.06** | — | 신규 |
| MappingFeatures 계산 | 5,000,000 | $0.00001 | **$50** | $50 | 0% |
| **LLM 총비용** | | | **~$882** | ~$1,245.5 | **29%** |

### Batch API 적용 시 (50% 할인)

| 파이프라인 | v8 Batch 비용 | v7 Batch 비용 | 절감 |
|---|---|---|---|
| CompanyContext | **$2.2** | $4 | 45% |
| CandidateContext | **$395** | $575 | 31% |
| **Batch LLM 총비용** | **~$485** | ~$667 | **27%** |

---

## 7. v1 하이브리드 비율 재정의 **(v8 변경)**

### 이력서(CandidateContext) 추출 기준

| 추출 대상 | DB 조회 | LLM | 비고 |
|---|---|---|---|
| company, role_title, period | **100%** **(v8: DB)** | 0% | DB 직접 조회 |
| tech_stack | **90%** **(v8: code-hub + Tier 2 embedding)** | 10% | Tier 1 정규화 + Tier 2 embedding 유사도 **(v8.1)** |
| scope_type | 0% (힌트 제공) | **100%** | positionGradeCode 힌트 |
| outcomes | 0% | **100%** | 성과 추출은 LLM만 가능 |
| situational_signals | 0% | **100%** | taxonomy 분류 = LLM |
| past_company_context | **100%** **(v8: BRN 직접)** | 0% | BRN NICE 직접 매칭 |
| role_evolution | 0% | **100%** | 전체 커리어 추론 |
| domain_depth | 0% | **100%** | 도메인 판별 = LLM |
| work_style_signals | 0% | **100%** | LLM 추론 |

**전체 가중 비율**: DB 조회 ~35% + Tier 1/2 정규화 ~10%, LLM ~55% (v7: Rule 25%, LLM 75%) **(v8.1 변경)**

### JD(CompanyContext) 추출 기준

| 추출 대상 | DB 조회 | LLM | 비고 |
|---|---|---|---|
| tech_stack | **100%** **(v8: code-hub + Tier 2)** | 0% | DB 조회 + 2-Tier 정규화 **(v8.1)** |
| industry | **100%** **(v8: code-hub)** | 0% | DB 직접 조회 + Tier 1 정규화 |
| career_types, education | **100%** **(v8: DB)** | 0% | requirement 테이블 |
| company_profile | **100%** | 0% | NICE Lookup |
| stage_estimate | **75%** | 25% | Rule 우선 |
| vacancy + role_expectations | 0% (정형 사전 제공) | **100%** | 정형 필드로 토큰 절감 |
| operating_model | **40%** (키워드) | 60% | 하이브리드 |
| domain_positioning | 0% | **100%** | 선택적 |
| structural_tensions | 0% | **100%** | 크롤링 필요 |

---

## 8. 에러 핸들링 및 배치 처리 전략

### 8.1 에러 유형별 처리 정책 **(v8 변경: DB 관련 에러 추가)**

| 에러 유형 | 원인 | 정책 | 최대 재시도 | 비고 |
|---|---|---|---|---|
| **DB 조회 실패** **(v8 신설)** | DB 연결 문제, 타임아웃 | **재시도** (exponential backoff) | 3회 | 리드 레플리카 장애 시 |
| **DB 데이터 누락** **(v8 신설)** | Career/Skill 엔티티 부재 | **skip** (graceful degradation) | 0 | 해당 필드 null |
| **JSONB 파싱 실패** **(v8 신설)** | overview.descriptions 구조 불일치 | **fallback**: 전체 텍스트를 LLM에 전달 | 0 | 토큰 증가 감수 |
| **LLM API 호출 실패** | 네트워크, 서버 에러 | **재시도** | 3회 | 동일 |
| **LLM API Rate Limit** | 429 Too Many Requests | **대기 후 재시도** | 5회 | 동일 |
| **LLM 응답 파싱 실패** | JSON 형식 오류 | **재시도** (temperature 조정) | 2회 | 동일 |
| **LLM 응답 스키마 불일치** | 필수 필드 누락 | **부분 수용** | 0 | 동일 |
| **NICE DB 타임아웃** | DB 부하 | **재시도** | 3회 | 동일 |
| **NICE DB 매칭 실패** | BRN/회사명 미등록 | **skip** | 0 | 정상 케이스 |
| ~~**이력서 파싱 실패**~~ | — | — | — | **v8 제거**: DB 조회이므로 파싱 실패 없음 |
| **Graph 적재 실패** | Neo4j 연결/제약 조건 | **재시도** | 3회 | 동일 |
| **Embedding API 실패** | Vertex AI 에러 | **재시도** | 3회 | 동일 |

### 8.2 evidence_span 후처리 검증 — v7과 동일

### 8.3 LLM 출력 파싱 실패 전략 — v7과 동일

> v7의 3-tier retry 전략을 그대로 유지. LLM 호출 건수는 동일하나, 프롬프트가 간결해져 파싱 실패율이 다소 감소할 수 있음.

### 8.4 Dead-Letter 큐 및 재처리 — v7과 동일

### 8.5 배치 처리 / 병렬 설계 **(v8 변경: DB 기반)**

```
[Batch Processing Architecture — v8]

resume-hub 500K 레코드
    │
    ├─ 중복 제거 (SiteUserMapping) → canonical ~450K
    │
    ├─ DB cursor 기반 Chunk 분할 (1,000건/chunk x 450 chunks)
    │   (v7의 파일 기반 분할 → DB cursor 기반으로 변경)
    │
    ├─ Chunk별 처리
    │   ├─ DB 조회 (Career, Skill, CareerDescription) — 벌크 조회
    │   ├─ 정형 필드 매핑 (비용 0)
    │   ├─ LLM Batch API 요청 (경력별)
    │   └─ 결과 수집 + 파싱
    │
    └─ Graph 적재 (비동기, 병렬 worker 4~8개)
```

- **v8 이점**: 파일 I/O가 없으므로 전처리 단계가 DB 조회로 대체됨 → 처리 속도 향상
- **예상 처리 시간**: DB 조회 + LLM Batch 포함 ~1.5~2.5일 (v7: ~2~3일)

---

## 9. ML Knowledge Distillation 적용 범위 — v7과 동일

- **ML 대체 가능**: scope_type 분류, seniority 분류
- **ML 대체 불가**: outcomes 추출, situational_signals, vacancy scope_type, role_evolution
- **비용 절감 효과**: 이력서 1건당 LLM 토큰 22% 감소, 500K 기준 약 $150 절감 (v8 Batch 기준)
