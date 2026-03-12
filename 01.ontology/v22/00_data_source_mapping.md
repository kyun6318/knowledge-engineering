# 데이터베이스 ↔ 온톨로지 매핑

> 작성일: 2026-03-13
> 
> 
> job-hub, resume-hub, code-hub 데이터베이스를 CompanyContext, CandidateContext, MappingFeatures, Graph Schema 매핑 정의
> 

---

## 0. 설계 원칙

| 원칙 | 설명 |
| --- | --- |
| **Structured-first** | DB에 구조화된 코드/필드가 존재하면 LLM 추출 전에 먼저 활용한다. 표준화 가능한 컬럼은 방법론에 대해 별도 논의를 진행한다. 비구조화 혹은 표준화 공수가 높은 컬럼에 대해서 LLM을 사용한다 |
| **코드 정규화** | code-hub의 공통코드를 기준으로 산업/직무/스킬을 정규화한다. 외부 코드는 `foreign_code_mapping`을 통해 내부 코드로 변환 후 사용한다. 코드 허브에 통일성이 부족한 코드에 대해서는 별도 표준화를 진행한다. |
| **임베딩 기반 비교** | DB 컬럼의 값이 표준화되어 있지 않음을 전제한다. 스킬/전공/직무 등 표현이 다양한 항목은 코드 정규화를 강제하지 않고 **임베딩 유사도**로 비교한다. 정규화는 유한 집합에만 적용한다 (1.5절 참조) |
| **ID 연결** | 온톨로지의 company_id, candidate_id는 각각 job-hub의 `job.user_ref_key`, resume-hub의 `SiteUserMapping.id`에 대응된다(확인 필요, 키가 난잡한데 어느 것을 키로 잡을 것인지) |
| **증분 보강** | DB 구조화 데이터를 기본 골격으로, LLM 추출 결과 및 크롤링 추가 데이터를 보강 레이어로 적용한다 |
| **실측 데이터 기반 설계** | fill rate, 품질 수치를 v2.1 데이터 분석 실측치로 처리하고 설계 결정은 실측 데이터에 근거한다 |

---

## 1. code-hub 매핑

code-hub는 공고/이력서에서 공통으로 사용하는 **마스터 코드**를 관리한다. 온톨로지 전반에 걸쳐 정규화 기준이 된다.

### 1.1 산업 코드 -> Industry 노드 / company_profile.industry_code

| code-hub | 코드 계층 | 온톨로지 매핑 대상 | 용도 |
| --- | --- | --- | --- |
| `INDUSTRY_CATEGORY` | 1depth (대분류) | `Industry.category` | 산업 대분류, `is_regulated` 판정 |
| `INDUSTRY_SUBCATEGORY` | 2depth (중분류, **63개 코드**) | `Industry.industry_id` | 산업 중분류 |
| `INDUSTRY` | 3depth (소분류) | `company_profile.industry_code`, `Organization.industry_code` | 기업 산업 코드 |

**매핑 규칙**:

```python
def resolve_industry_code(job_overview):
    """
    job-hub overview.industry_codes에서 code-hub 산업 코드를 추출하여
    온톨로지 industry_code로 매핑한다.

    job-hub의 industry_codes는 code-hub의 INDUSTRY 타입 코드 배열이다.
    복수 산업 코드가 있을 경우 첫 번째를 primary로 사용한다.
    """
    industry_codes = job_overview.industry_codes  # VARCHAR[]
    if not industry_codes:
        return None

    primary_code = industry_codes[0]

    # code-hub에서 코드 상세 조회
    code_detail = lookup_common_code(type="INDUSTRY", code=primary_code)

    return {
        "industry_code": primary_code,
        "industry_label": code_detail.detail_name,
        "industry_category": code_detail.group_code,
        "industry_category_label": code_detail.group_name,
    }
```

**NICE industry_code와의 관계**:
- code-hub의 INDUSTRY 코드를 **primary 산업 코드**로 사용하고, NICE 코드는 **보조 소스**로 교차 검증
- code-hub ↔ NICE 간 매핑이 필요한 경우 `foreign_code_mapping` 에서 처리

**후보 Industry 연결**:

| 필드 | 빈배열 비율 | 활용 가능성 |
| --- | --- | --- |
| `workcondition.industryCodes` (INDUSTRY_SUBCATEGORY) | **66.0%** | 5순위 - 34%만 활용 가능 |
| `workcondition.industryKeywordCodes` (INDUSTRY) | 81.7% | 6순위 - 18.3%만 활용 가능 |
| `workcondition.jobIndustryCodes` | **100%** | **사용 불가** |
| `workcondition.careerJobIndustryCodes` | **100%** | **사용 불가** |
| `overview.industry_codes` (job-hub) | 분석 필요 | **Vacancy->Industry 주요 소스** |

### 1.2 직무 코드 → Role 노드

| code-hub Enum | 코드 계층 | 온톨로지 매핑 대상 | 용도 |
| --- | --- | --- | --- |
| `JOB_CLASSIFICATION_CATEGORY` | 1depth | `Role.category` | 직무 대분류 (engineering/product/design 등) |
| `JOB_CLASSIFICATION_SUBCATEGORY` | 2depth (**242개 코드**) | Role 매칭 중간 레벨 | 직무 중분류 |
| `JOB_CLASSIFICATION` | 3depth | `Role.role_id` | 직무 소분류 (정규화된 역할) |

**직무 코드 실측 품질**:
- career.jobClassificationCodes: ~100% fill rate (경력 보유자)
- workcondition.jobClassificationCodes: 17.4% 빈배열 (82.6% 활용 가능)
- **희망 직무 vs 실제 경력 직무 간 64.9% 불일치** -> 직무전환 의도로 해석, 경력 직무를 기준으로 사용

### 1.3~1.8 정규화/임베딩 구현

> §1.3 스킬 정규화, §1.5 3-Tier 비교 전략, §1.7 기타 코드 매핑, §1.8 Certificate Type 변환
> → 02.knowledge_graph/results/extraction_logic/v15/06_normalization.md로 이동

---

## 2. job-hub → CompanyContext 매핑

### 2.1 ID 매핑

| 온톨로지 필드 | job-hub 소스 | 비고 |
| --- | --- | --- |
| `company_id` | `job.user_ref_key` 또는 `job.workspace_id` | 기업 식별자. 동일 기업의 복수 공고를 묶는 키 |
| `job_id` | `job.id` (VARCHAR 126) | 공고 식별자 |
| `company_name` | `work_condition.company_name` | 근무 기업명 |

### 2.2 company_profile 매핑

| 온톨로지 필드 | job-hub 소스 | 추출 방법 | 비고 |
| --- | --- | --- | --- |
| `industry_code` | `overview.industry_codes[0]` | Lookup (code-hub) | code-hub INDUSTRY Code + NICE |
| `industry_label` | code-hub 코드명 조회 | Lookup | code-hub `detail_name` |
| `is_regulated_industry` | `overview.industry_codes[0]` -> code-hub 대분류 | Rule | K=금융, Q=보건, D=전기, H=운수 -> true |

### 2.3 vacancy 매핑

| 온톨로지 필드 | job-hub 소스 | 추출 방법 | 비고 |
| --- | --- | --- | --- |
| `role_title` | `overview.work_fields[]` + `overview.job_classification_codes[]` | Rule + Lookup | work_fields는 자유 텍스트, job_classification_codes는 정규화 코드 |
| `seniority` | `overview.designation_codes[]` | Rule (매핑 테이블) | code-hub DESIGNATION -> seniority 변환 |
| `hiring_context` | `overview.descriptions` (JSONB) | LLM | BUILD_NEW/SCALE_EXISTING/RESET/REPLACE |
| `scope_description` | `overview.descriptions` (JSONB) | LLM | 비구조화 텍스트에서 추출 |
| `team_context` | `overview.descriptions` (JSONB) | LLM | 비구조화 텍스트에서 추출 |
| `tech_stack` | `skill` 테이블 (type=HARD) | Lookup (code-hub) |  |

**designation_codes -> seniority 매핑 테이블**:

- 거짓 직명이 많아 단순 맵핑에 대한 고려 필요
- **[v21]** designation 기반 seniority는 confidence 상한 0.65를 이미 적용 중. Phase 0 PoC 20건에서 직명-실제 역할 불일치율을 측정하여, 불일치율 30%+ 시 confidence 상한을 0.55로 하향 조정.

```python
DESIGNATION_TO_SENIORITY = {
    "사원": "JUNIOR",
    "대리": "MID",
    "과장": "MID",
    "차장": "SENIOR",
    "부장": "SENIOR",
    "팀장": "LEAD",
    "실장": "LEAD",
    "이사": "HEAD",
    "상무": "HEAD",
}

def infer_seniority_from_designation(designation_codes):
    if not designation_codes:
        return None
    for code in designation_codes:
        code_detail = lookup_common_code(type="POSITION_GRADE", code=code)
        if code_detail and code_detail.detail_name in DESIGNATION_TO_SENIORITY:
            return DESIGNATION_TO_SENIORITY[code_detail.detail_name]
    return None
```

### 2.4 role_expectations 매핑

| 온톨로지 필드 | job-hub 소스 | 추출 방법 | 비고 |
| --- | --- | --- | --- |
| `responsibilities` | `overview.descriptions` (JSONB) | LLM | 상세 요강에서 추출 |
| `requirements` | `requirement` 테이블 전체 | Rule + LLM | 구조화 필드(career_types, education_code) + 비구조화(descriptions) |
| `preferred` | `requirement.preference_codes[]` | Lookup (code-hub PREFERRED) | 구조화된 우대조건 코드 직접 사용 |
| `tech_stack` | `skill` 테이블 (type=HARD, job_id 기준) | Lookup | code-hub HARD_SKILL 코드 직접 사용 |

### 2.5 operating_model facets 매핑 보강

| 온톨로지 facet | job-hub 보조 소스 | 추출 방법 | 비고 |
| --- | --- | --- | --- |
| `speed` | `overview.always_hire`, `overview.close_on_hire` | Rule | 상시채용/채용시마감 시그널 |
| `autonomy` | `work_condition.work_schedule_option_types[]` | Rule | FLEXIBLE_WORK, WORK_HOURS_NEGOTIABLE |
| `autonomy` | `overview.recruitment_option_types[]` | Rule | REMOTE_WORK_AVAILABLE |
| `process` | `overview.descriptions` (JSONB) | LLM |  |

```python
def extract_structured_facet_signals(job):
    """
    job-hub의 구조화된 필드에서 operating_model facet 시그널을 추출한다.

    전체 ACTIVE 비율은 여전히 낮지만 (<10%),
    LLM 없이도 즉시 추출 가능하여 기업측 facet 기초 데이터로 활용 가능할듯.
    """
    signals = {"speed": [], "autonomy": [], "process": []}

    if job.overview.always_hire:
        signals["speed"].append("상시채용 (빠른 채용 프로세스 시사)")
    if getattr(job.overview, 'close_on_hire', False):
        signals["speed"].append("채용시마감 (긴급 충원 시사)")

    wc = job.work_condition
    if wc and wc.work_schedule_option_types:
        schedule_opts = set(wc.work_schedule_option_types)
        if "FLEXIBLE_WORK" in schedule_opts:
            signals["autonomy"].append("유연근무 가능")
        if "WORK_HOURS_NEGOTIABLE" in schedule_opts:
            signals["autonomy"].append("근무시간 협의 가능")

    if job.overview.recruitment_option_types:
        opts = set(job.overview.recruitment_option_types)
        if "REMOTE_WORK_AVAILABLE" in opts:
            signals["autonomy"].append("재택근무 가능")

    return signals
```

---

## 3. resume-hub -> CandidateContext 매핑

### 3.1 ID 매핑

| 온톨로지 필드 | resume-hub 소스 | 비고 |
| --- | --- | --- |
| `candidate_id` | `SiteUserMapping.id` | **7,780,115** 고유 사용자 |
| `resume_id` | `Resume.id` (main_flag=1 필터) | **main_flag=1 필터 필수**, 96.23% 보유 (7,715,508) |

### 다중 이력서 처리 규칙 [R-10/U-2]

한 사용자(`SiteUserMapping.id`)가 복수의 Resume을 보유하는 경우의 처리 규칙:

| 케이스 | 비율 | 처리 규칙 |
| --- | --- | --- |
| main_flag=1 이력서 1개 | 96.23% | 해당 이력서 사용 (정상 케이스) |
| main_flag=1 이력서 없음 | 3.77% (~294K 사용자) | `resume.userUpdatedAt` 기준 **최신 이력서**를 사용. 단, 최신 이력서도 `COMPLETED` + `PUBLIC`이어야 함. 조건 미충족 시 해당 사용자 **매칭 대상에서 제외** |
| main_flag=1 이력서 복수 | 데이터 무결성 확인 필요 | **가장 최근 `userUpdatedAt`** 이력서를 사용. 이 케이스가 1% 이상 발견되면 데이터팀에 무결성 이슈로 에스컬레이션 |

> **구현 시 검증 필요**: main_flag=1이 복수 존재하는 사용자가 실제로 있는지 확인하고, 빈도 측정
> 

**[D6] 서비스 가용 이력서 풀 필터링**:

```python
def get_service_resume_pool():
    """
    서비스 가용 이력서 풀 정의.

    전체 8,018,110 -> 활성 7,975,889 (99.5%)
    -> PUBLIC + COMPLETED: 5,545,741 (69.2%)
      -> EXPERIENCED: 3,726,057 (67.2%)
      -> NEW_COMER: 1,819,684 (32.8%)
      -> HIGH + PREMIUM 품질: 3,183,554 (57.4%)
    """
    return {
        "filters": [
            "deletedAt IS NULL",
            "visibilityType = 'PUBLIC'",
            "completeStatus = 'COMPLETED'",
            "main_flag = true",
        ],
        "quality_filter": "quality_score >= 6",  # HIGH + PREMIUM 등급
        "total_pool": 5_545_741,
        "quality_pool": 3_183_554,
    }

# v1 매칭 대상 제한
def get_v1_matching_pool():
    """
    v1에서 MappingFeatures 계산 대상은 EXPERIENCED만.
    NEW_COMER(30.9%)는 CandidateContext 기본 속성만 생성하고 매칭 대상에서 제외.

    전체 5,545,741 -> EXPERIENCED: 3,726,057 (67.2%)
    -> HIGH+PREMIUM 품질: ~2,139,000 (추정 57.4%)

    v2에서 NEW_COMER 전용 매칭 피처(Education, Certificate, 희망 직무) 도입 예정.
    상세: 02_candidate_context.md §0.1, 03_mapping_features.md §0.1
    """
    base_pool = get_service_resume_pool()
    return {
        **base_pool,
        "v1_matching_filter": "careerType = 'EXPERIENCED'",
        "v1_matching_pool": 3_726_057,
        "excluded_new_comer": 1_819_684,
    }
```

**Resume 품질 등급 분포**:

| 등급 | 점수 범위 | 비율 |
| --- | --- | --- |
| LOW | 0-3 | 8.6% |
| MEDIUM | 3-6 | 29.9% |
| HIGH | 6-9 | 48.3% |
| PREMIUM | 9-11 | 13.3% |

### 3.2 Experience 매핑

| 온톨로지 필드 | resume-hub 소스 | 추출 방법 | v12 실측 fill rate |
| --- | --- | --- | --- |
| `company` | `Career.companyName` | Lookup | 99.96% (**4,479,983 고유값**) |
| `role_title` | `Career.jobClassificationCodes[]` + `Career.positionTitleCode` | Lookup (code-hub) | jobClassCodes ~100%, positionTitle **29.45%** |
| `period.start` | `Career.period.period` (DATERANGE 시작) | Rule | ~100% |
| `period.end` | `Career.period.period` (DATERANGE 끝) | Rule | ~100% (EMPLOYED 10.5% = “present”) |
| `period.duration_months` | **계산** (started_on ~ ended_on) | Rule | **daysWorked 100% 제로 -> 직접 계산** [v12 D3] |
| `tech_stack` | `Skill` 테이블 (type=HARD, resume_id 기준) | Lookup (code-hub) | 38.3% (3,074,732 이력서) |
| `scope_type` | `Career.positionTitleCode` -> `positionGradeCode` -> LLM | Rule + LLM | positionTitle **29.45%**, positionGrade **39.16%** |
| `scope_summary` | `Career.workDetails` 또는 `CareerDescription.description` | LLM | workDetails ~56%, careerDesc **16.9%** |
| `outcomes` | `CareerDescription.description` + `SelfIntroduction` | LLM | careerDesc **16.9%** (1차), selfIntro **64.1%** (2차) |
| `situational_signals` | 텍스트 소스 복합 | LLM + Rule | 합집합 ~65-70% |

**[D3] duration_months 계산**:

```python
def compute_duration_months(career):
    """
    career.period.daysWorked가 100% 제로이므로, period DATERANGE에서 직접 계산한다.

    대상: 18,709,830건 career 레코드
    """
    started = career.period.period.started_on
    ended = career.period.period.ended_on

    if ended is None or career.period.employmentStatus == "EMPLOYED":
        ended = date.today()

    delta = relativedelta(ended, started)
    return delta.years * 12 + delta.months
```

**[D4] CareerDescription FK 부재 제약**:

> **핵심 제약**: CareerDescription 테이블에 `career_id` FK가 없다. resume_id로만 연결되므로, 복수 경력이 있는 이력서에서 어떤 경력에 대한 기술인지 career 단위 매핑이 불가능하다. Outcome/SituationalSignal 추출 시 LLM으로 컨텍스트 판단 필요
> 

```python
def extract_outcomes_from_career_description(resume_id, careers):
    """
    [D4] CareerDescription은 resume 단위 귀속 (career_id FK 없음).

    전략:
    1. CareerDescription.description 전문을 가져온다 (중앙값 527자)
    2. 해당 resume의 Career[] 목록을 함께 LLM에 전달한다
    3. LLM이 텍스트 컨텍스트로 각 career에 outcome을 귀속한다
    4. 귀속 불가 시 resume 전체에 귀속 (confidence 하향)
    """
    career_desc = get_career_description(resume_id)  # 16.9% 보유
    if not career_desc:
        # fallback: selfIntroduction (64.1% 보유, 중앙값 1,320자)
        self_intros = get_self_introductions(resume_id)
        if not self_intros:
            return []  # ~35% 이력서는 Outcome 생성 불가
        return llm_extract_outcomes_from_self_intro(self_intros, careers)

    return llm_extract_outcomes_with_career_attribution(
        career_desc.description, careers
    )
```

**scope_type 구조화 추정**:

- 역시 이런 단순 맵핑을 계속 써도 될지 고민 필요

```python
POSITION_TO_SCOPE = {
    # positionTitleCode (직책) - Confidence 0.75
    "사원": "IC", "대리": "IC", "과장": "IC", "차장": "IC",
    "팀장": "LEAD", "파트장": "LEAD", "실장": "LEAD",
    "이사": "HEAD", "상무": "HEAD", "부사장": "HEAD",
    "대표": "FOUNDER", "CEO": "FOUNDER", "CTO": "HEAD",
}

def estimate_scope_type(career):
    """
    추정 우선순위:
    1순위: positionTitleCode (직책, 29.45% fill rate) -> confidence 0.75
    2순위: positionGradeCode (직급, 39.16% fill rate) -> confidence 0.65
    3순위: workDetails LLM 추출 (~56% fill rate) -> confidence 0.50
    """
    # 1순위: 직책 코드
    if career.positionTitleCode:
        title_detail = lookup_common_code(
            type="POSITION_TITLE", code=career.positionTitleCode
        )
        if title_detail and title_detail.detail_name in POSITION_TO_SCOPE:
            return POSITION_TO_SCOPE[title_detail.detail_name], 0.75

    # 2순위: 직급 코드
    if career.positionGradeCode:
        grade_detail = lookup_common_code(
            type="POSITION_GRADE", code=career.positionGradeCode
        )
        if grade_detail and grade_detail.detail_name in POSITION_TO_SCOPE:
            return POSITION_TO_SCOPE[grade_detail.detail_name], 0.65

    # 3순위: LLM fallback
    if career.workDetails:
        return llm_extract_scope_type(career.workDetails), 0.50

    return "UNKNOWN", 0.0
```

### 3.3 전체 커리어 수준 필드 매핑

| 온톨로지 필드 | resume-hub 소스 | 추출 방법 | v12 실측 |
| --- | --- | --- | --- |
| `role_evolution` | `Career[]` (전체 경력 시퀀스) | Rule + LLM | 경력 보유자 68.9% |
| `domain_depth` | `Career[].jobClassificationCodes[]` + `WorkCondition.workJobField` | Rule | 82.6% (jobClassCodes 기반) |
| `work_style_signals` | `SelfIntroduction.description` + `Career.workDetails` | LLM | selfIntro 64.1%, **v1 대부분 null** |

**domain_depth 구조화 추출**:

```python
def extract_domain_depth_structured(resume):
    """
    구조화 직무 코드 기반 primary_domain 추정
    LLM 추출 이전 수행으로 기초 분석 확보

    Confidence: min(0.80, 0.50 + 반복횟수 × 0.10)
    """
    job_codes = []
    for career in resume.careers:
        if career.jobClassificationCodes:
            job_codes.extend(career.jobClassificationCodes)

    # 희망 근무 조건의 산업 코드 (보조, 66% 빈배열이므로 있을 때만)
    if resume.workCondition and resume.workCondition.workJobField:
        wjf = resume.workCondition.workJobField
        if wjf.industryCodes:
            job_codes.extend(wjf.industryCodes)

    if not job_codes:
        return None

    from collections import Counter
    code_counts = Counter(job_codes)
    primary_code, count = code_counts.most_common(1)[0]

    code_detail = lookup_common_code(
        type="JOB_CLASSIFICATION_SUBCATEGORY", code=primary_code
    )

    return {
        "primary_domain": code_detail.sub_name if code_detail else primary_code,
        "domain_experience_count": count,
        "confidence": min(0.80, 0.50 + count * 0.10),
    }
```

### 3.4 PastCompanyContext 보강

| 온톨로지 필드 | resume-hub 소스 | 비고 |
| --- | --- | --- |
| `company_name` | `Career.companyName` | 99.96% fill rate |
| `industry_code` | 1순위: job-hub 역참조, 2순위: NICE | job-hub 역참조 confidence 0.75 |
| `brn` | `Career.businessRegistrationNumber` | **62% fill rate** - 정규화 1차 키 |

```python
def enrich_past_company_from_jobhub(company_name):
    """
    후보의 이전 회사명 -> job-hub 역참조 -> NICE fallback.
    Confidence: 0.75 (동일 회사 공고 기반)
    """
    jobs = query_jobs_by_company_name(company_name)
    if not jobs:
        return None  # NICE fallback

    latest_job = max(jobs, key=lambda j: j.created_at)
    industry_codes = latest_job.overview.industry_codes

    return {
        "industry_code": industry_codes[0] if industry_codes else None,
        "source": "job_hub_reverse_lookup",
        "confidence": 0.75,
    }
```

### 3.5 Person 노드 보강 속성

Person 속성을 데이터 분석 결과에 기반하여 추가

| 속성 | 소스 | fill rate | 용도 | 비고 |
| --- | --- | --- | --- | --- |
| `gender` | `profile.gender` | 100% (M 52.5% / F 47.4% / OTHER 0.1%) | 매칭 편향 모니터링 | **매칭 점수에 사용 금지**, 별도 분석 테이블 관리 권장 |
| `age` | `profile.age` | 93.3% (평균 36.2세) | 세그먼트 분석 보조 | **6.7% 이상치(age>100)** -> 1~100 필터, 별도 분석 테이블 관리 권장 |
| `career_type` | `resume.careerType` | 100% | 경력/신입 세그먼트 | EXPERIENCED 69.1% / NEW_COMER 30.9% |
| `freshness_weight` | `resume.userUpdatedAt` 기반 계산 | 100% | 데이터 신선도 가중치 | 31.6% 5년+ 미갱신 -> 감쇠 적용 |
| `education_level` | `education.schoolType` (MAX) | 95.6% | 학력 필터링 | **finalEducationLevel 35.6% 불일치 -> education.schoolType을 진실 소스로** |
- 노출은 최근 데이터만 사용해도 5년 정도는 데이터 소스에 넣어서 학습 등에 사용할 수 있을 듯

```python
def compute_freshness_weight(user_updated_at, use_smooth=False):
    """
    이력서 신선도 가중치.

    [v21] 두 가지 모드 제공:
    - Step function (v20 기본): 경계에서 불연속 (예: 364일 0.9 → 366일 0.7)
    - Smooth function (v21 신규): 지수 감쇠로 경계 불연속 제거

    v1 파일럿에서 step vs smooth의 랭킹 차이를 비교 검토:
    - 50건 매핑에서 step/smooth 각각의 ranking_score Top-10 비교
    - 순위 변동이 10% 미만이면 step 유지 (단순성), 10% 이상이면 smooth 전환

    실측: 90일 이내 활성 13.9%, 반감기 31.5개월, 5년+ 미갱신 31.6%
    """
    days_since = (date.today() - user_updated_at.date()).days

    if use_smooth:
        # 지수 감쇠: half_life = 31.5개월 ≈ 958일 (실측 반감기 기반)
        import math
        half_life_days = 958
        weight = math.exp(-math.log(2) * days_since / half_life_days)  # ln(2) 정확값 사용
        return max(round(weight, 2), 0.10)  # 최소값 0.10
    else:
        # Step function (v20 유지)
        if days_since <= 90:
            return 1.0
        elif days_since <= 365:
            return 0.9
        elif days_since <= 1095:
            return 0.7
        elif days_since <= 1825:
            return 0.5
        else:
            return 0.3
```

### 3.6 보조 데이터 매핑

온톨로지 노드에 직접 매핑되지 않지만, 매칭/추론에 보조적으로 활용되는 데이터.

| 데이터 | 규모 | 활용 | 비고 |
| --- | --- | --- | --- |
| Education | 11.2M건, 95.6% 커버리지 | Person.education_level, 학력 필터링 | schoolType을 진실 소스로 |
| Major | 7.1M건, 47,163 고유값 | F3 domain_fit 보조 (전공-산업 연관 추론) | **정규화 불가 -> Tier 3 임베딩** |
| Certificate | 13.6M건, 54% 커버리지 | 자격증 매칭 (JD 요구 vs 보유) | **type 매핑 변환 필수** (1.8절) |
| Language | 654K건, 6.3% 커버리지 | 어학 능력 매칭 | 영어 62.1%, 일본어 14.8% |
| Experience(활동) | 6.6M건, 27.9% | INTERNSHIP -> 초기 경력, OVERSEAS -> 국제 시그널 |  |
| Award | 이력서 8.8% 커버리지 | 메타데이터만 활용 | **description 100% 빈값** |

---

## 4. 구조화 코드 기반 매칭 강화

> §4 코드 매칭 구현 (domain_fit 산업코드 매칭, role_fit 직무코드 매칭, 스킬 하이브리드 매칭)
> → 02.knowledge_graph/results/extraction_logic/v15/06_normalization.md로 이동

---

## 5. 추출 파이프라인

> §5 추출 파이프라인 → 02.knowledge_graph/results/extraction_logic/v15/01_extraction_pipeline.md 참조

---

## 6. 데이터 품질 및 coverage

> §6 데이터 품질/coverage 실측치 → 02.knowledge_graph/results/extraction_logic/v15/07_data_quality.md로 이동

---

## 7. 정규화 선행 과제

> §7 정규화 선행 과제 → 02.knowledge_graph/results/extraction_logic/v15/06_normalization.md로 이동

---

## 8. 구현 로드맵

> §8 구현 로드맵 → 03.graphrag/results/implement_planning/separate/v5/shared/implementation_roadmap.md로 이동

---

## 9. 사용 불가 / 제거 대상 필드

| 필드 | 사유 |
| --- | --- |
| `profile.birthday` | 100% sentinel ‘1900-01-01’ |
| `profile.globalUserRef` | 100% 빈값 |
| `profile.hiringAdvantages` | 96.7% 빈배열 |
| `career.period.daysWorked` | 100% 제로 (계산으로 대체) |
| `career.salary` | REDACTED |
| `language.trainingExperience` | 100% NONE |
| `award.description` | 100% 빈값 |
| `workcondition.workSchedule` | 100% 빈값 |
| `workcondition.workArrangementType` | 97.5% ANY (구분 불가) |
| `workcondition.jobIndustryCodes` | 100% 빈배열 |
| `workcondition.careerJobIndustryCodes` | 100% 빈배열 |
| `resume.completeStatus` | 98.3% COMPLETED (변별력 없음) |

---

## 10. LLM 비용 총 추정

> §10 LLM 비용 → 03.graphrag/results/implement_planning/separate/v5/shared/implementation_roadmap.md로 이동