# 내부 데이터베이스 ↔ 온톨로지 매핑 가이드 v19

> 작성일: 2026-03-10 | 현재 유효 버전: **v19** | 기준: v11.1 + 데이터 분석 v2.1 통합
>
> job-hub, resume-hub, code-hub 데이터베이스의 테이블/컬럼이 CompanyContext, CandidateContext, MappingFeatures, Graph Schema의 어떤 필드에 매핑되는지 정의한다.
>
> **v19 변경** (2026-03-11): 내용 변경 없음 (버전 헤더 동기화)
>
> <details><summary>v18 변경 이력</summary>
>
> **v18 변경** (2026-03-10): v17 리뷰 피드백 반영
> - [R-10/U-2] §3.1 다중 이력서 처리 규칙 추가 (main_flag 없는 3.77% 대응)
> - [R-5] §5 추출 파이프라인: 중복 기술 제거, 정본 문서 참조 관계 명확화
> - [R-5] §6.5 피처별 ACTIVE 전망 — 정본을 `03_mapping_features.md §7.3`으로 지정, 본 문서에서 제거
> - §11 섹션 번호 오류 수정 (10.1/10.2 → 11.1/11.2)
>
> <details><summary>v16~v17 변경 이력</summary>
>
> **v17 변경** (2026-03-10): v16 리뷰 피드백 반영
> - [R-1] §2.3 vacancy 매핑에서 scope_type → hiring_context 명칭 변경 반영
>
> </details>
>
> <details><summary>v12~v16 변경 이력</summary>
>
> **v16 변경** (2026-03-10): v15 리뷰 피드백 반영
> - [S-7] §4.3 스킬 매칭에서 SOFT_SKILL 제외 규칙 명시 (type=HARD만 매칭 대상)
> - [S-5] §3.1 서비스 풀에서 v1 매칭 대상 = EXPERIENCED 제한 명시
>
> <details><summary>v12~v15 변경 이력</summary>
>
> **v15 변경** (2026-03-10): v14 리뷰 피드백 반영
> - [N14-1] §10.1 LLM 비용 output token 비율 30% 가정에 대한 주의사항 및 실측 보정 계획 추가
>
> **v14 변경** (2026-03-10): v13 리뷰 피드백 반영
> - [R-1] §4.1 industry code 매칭 로직 정본을 03_mapping_features F3로 확정, 본 문서는 데이터 소스 참조만 유지
> - [R-2] §1.5 임베딩 batch 구현 코드를 pseudo-code 수준으로 축소 (O-1)
> - [R-3] §11 LLM 비용 총 추정 섹션 신규 추가 (전체 파이프라인 LLM 호출 비용 산정)
> - [R-4] §3.5 gender/age는 매칭 점수 사용 금지 + 별도 분석 테이블 관리 권고 추가 (O-2)
>
> <details><summary>v12~v13 변경 이력</summary>
>
> **v13 변경** (2026-03-10): v12 리뷰 피드백 반영
> - [C-2] compute_industry_code_match() 코드 타입 혼용 수정
> - 01~04 통합판 v12 변경사항 인라인 반영 완료 표시
>
> **v12 변경** (2026-03-10): 데이터 분석 v2.1 결과 통합
> - [D1~D10] 실측 fill rate 전면 교체, Person 보강, days_worked 계산, CareerDescription FK 제약, certificate type 매핑, Resume 품질 등급, 스킬 데이터, Education 불일치, 정규화 과제, 구현 로드맵
>
> </details>
>
> </details>
>
> </details>
>
> </details>

---

## 0. 설계 원칙

| 원칙 | 설명 |
|---|---|
| **구조화 우선 (Structured-first)** | DB에 구조화된 코드/필드가 존재하면 LLM 추출 전에 먼저 활용한다. LLM은 비구조화 텍스트(descriptions, workDetails)에만 사용한다 |
| **코드 정규화 통일** | code-hub의 공통코드를 기준으로 산업/직무/스킬을 정규화한다. 외부 코드는 `foreign_code_mapping`을 통해 내부 코드로 변환 후 사용한다 |
| **임베딩 기반 비교 (Embedding-first Comparison)** [v11.1] | DB 컬럼의 값이 표준화되어 있지 않음을 전제한다. 스킬/전공/직무 등 표현이 다양한 항목은 코드 정규화를 강제하지 않고 **임베딩 유사도**로 비교한다. 정규화는 대학교/회사명 등 유한 집합에만 적용한다 (1.5절 참조) |
| **ID 연결** | 온톨로지의 company_id, candidate_id는 각각 job-hub의 `job.user_ref_key`, resume-hub의 `SiteUserMapping.id`에 대응된다 |
| **증분 보강** | DB 구조화 데이터를 기본 골격으로, LLM 추출 결과를 보강 레이어로 적용한다 |
| **실측 데이터 기반 설계** [v12] | v11까지 추정치로 기재된 fill rate, 품질 수치를 v2.1 데이터 분석 실측치로 교체한다. 설계 결정은 실측 데이터에 근거한다 |

---

## 1. code-hub 매핑

code-hub는 공고/이력서에서 공통으로 사용하는 **마스터 코드**를 관리한다. 온톨로지 전반에 걸쳐 정규화 기준이 된다.

### 1.1 산업 코드 → Industry 노드 / company_profile.industry_code

| code-hub Enum | 코드 계층 | 온톨로지 매핑 대상 | 용도 |
|---|---|---|---|
| `INDUSTRY_CATEGORY` | 1depth (대분류) | `Industry.category` | 산업 대분류, `is_regulated` 판정 |
| `INDUSTRY_SUBCATEGORY` | 2depth (중분류, **63개 코드**) | `Industry.industry_id` | 산업 중분류 |
| `INDUSTRY` | 3depth (소분류) | `company_profile.industry_code`, `Organization.industry_code` | 기업의 산업 코드 |

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

**v10 NICE industry_code와의 관계**:
- v10에서는 NICE 업종 코드(예: "J63112")를 사용했다
- v11에서는 code-hub의 INDUSTRY 코드를 **primary 산업 코드**로 사용하고, NICE 코드는 **보조 소스**로 교차 검증에 활용한다
- code-hub ↔ NICE 간 매핑이 필요한 경우 `foreign_code_mapping`의 확장으로 처리한다

**[v12] 후보측 Industry 연결 현황**:

| 필드 | 빈배열 비율 | 활용 가능성 |
|---|---|---|
| `workcondition.industryCodes` (INDUSTRY_SUBCATEGORY) | **66.0%** | 5순위 — 34%만 활용 가능 |
| `workcondition.industryKeywordCodes` (INDUSTRY) | 81.7% | 6순위 — 18.3%만 활용 가능 |
| `workcondition.jobIndustryCodes` | **100%** | **사용 불가** |
| `workcondition.careerJobIndustryCodes` | **100%** | **사용 불가** |
| `overview.industry_codes` (job-hub) | 분석 필요 | **Vacancy→Industry 주요 소스** |

### 1.2 직무 코드 → Role 노드

| code-hub Enum | 코드 계층 | 온톨로지 매핑 대상 | 용도 |
|---|---|---|---|
| `JOB_CLASSIFICATION_CATEGORY` | 1depth | `Role.category` | 직무 대분류 (engineering/product/design 등) |
| `JOB_CLASSIFICATION_SUBCATEGORY` | 2depth (**242개 코드**) | Role 매칭 중간 레벨 | 직무 중분류 |
| `JOB_CLASSIFICATION` | 3depth | `Role.role_id` | 직무 소분류 (정규화된 역할) |

**[v12] 직무 코드 실측 품질**:
- career.jobClassificationCodes: ~100% fill rate (경력 보유자)
- workcondition.jobClassificationCodes: 17.4% 빈배열 (82.6% 활용 가능)
- **희망 직무 vs 실제 경력 직무 간 64.9% 불일치** → 직무전환 의도 반영으로 해석, 경력 직무를 진실 소스로 사용

### 1.3 스킬 코드 → Skill 노드

| code-hub Enum | 온톨로지 매핑 대상 | 용도 |
|---|---|---|
| `HARD_SKILL` (~2,398개 표준) | `Skill` (category: code-hub 속성 참조) | 기술 스킬 (Python, React 등) |
| `SOFT_SKILL` | `Skill` (category: "soft") | 소프트 스킬 |

**[v12] 스킬 데이터 실측 현황** (Critical):

| 항목 | 값 |
|---|---|
| 총 고유 스킬 코드 | **101,925개** |
| codehub 매핑 완료 | **2,398개 (2.4%)** |
| 비표준 코드 | **99,527개 (97.6%)** |
| 이력서 커버리지 | 38.3% (3,074,732 이력서) |
| 이력서당 평균 스킬 수 | 6.77개 |
| **20개 캡 의심** | 172K 이력서가 정확히 20개 → 입력 상한 존재 추정 |
| SOFT_SKILL 편중 | TOP 10의 60% 차지 — 성실성(25.2%), 긍정적(17.3%) |

**스킬 정규화** [v11.1 개정 유지: 경량 정규화 + 임베딩 fallback]:

```python
def normalize_skill(raw_skill_name, site_type="JOBKOREA"):
    """
    이력서/공고의 원본 스킬명을 code-hub 기준으로 경량 정규화한다.

    v11.1 전략 (v12 유지):
    - 정확 매칭(CI) + synonyms 매칭만 수행 (2단계)
    - 미매칭 시 원본 유지 → 비교는 임베딩 유사도로 수행 (4.3절)

    [v12] codehub synonyms 소스: ForeignCodeAttribute HARD_SKILL (JOBKOREA)의
    displayName + synonyms 속성
    """
    cleaned = raw_skill_name.strip()
    if not cleaned:
        return {"skill_id": None, "name": "", "normalized": False}

    # 1. code-hub 정확 매칭 (case-insensitive)
    match = lookup_foreign_code_attribute(
        site_type=site_type, type="HARD_SKILL", name=cleaned
    )
    if not match:
        match = lookup_foreign_code_attribute(
            site_type=site_type, type="HARD_SKILL", name=cleaned.lower()
        )
    if match:
        return {"skill_id": match.code, "name": match.name, "normalized": True}

    # 2. synonyms 매칭 (JSONB attributes 내 synonyms 필드)
    synonym_match = search_skill_synonyms(cleaned, site_type)
    if synonym_match:
        return {"skill_id": synonym_match.code, "name": synonym_match.name, "normalized": True}

    # 3. 미매칭 → 원본 유지 (비교는 임베딩으로)
    return {
        "skill_id": None,
        "name": raw_skill_name,
        "normalized": False
    }
```

**[v12] 스킬 Co-occurrence 클러스터** (정규화 참고):
- Illustrator-Photoshop: Lift 6.79
- Excel-PPT-Word: Lift 4.2x
- → 동일 클러스터 내 스킬은 그룹 노드로 묶는 것을 v2에서 검토

**[v12] 스킬 트렌드 (2022-2025)**:
- AI/GenAI 폭발: Gemini(7.1x), ChatGPT(5.0x), RAG(4.4x), AI Agent(4.9x)
- 레거시 감소: Servlet(0.65x), Eclipse(0.65x)
- 2022년 이후 이력서당 스킬 수 164% 급증

### 1.5 비정형 값 비교 전략 [v11.1, v12 보강]

DB 컬럼의 값이 표준화되어 있지 않음을 전제로, **대상의 특성에 따라 비교 전략을 분리**한다.

#### 3-Tier 비교 전략

| Tier | 대상 | 비교 방법 | 근거 |
|---|---|---|---|
| **Tier 1: 정규화 적합** | 대학교명, 회사명, 산업 코드 | code-hub Lookup (CI 매칭) | 유한 집합, 명확한 정체성, 오매칭 위험 낮음 |
| **Tier 2: 경량 정규화 + 임베딩** | 상위 스킬 (Java, Python 등) | code-hub CI 매칭 시도 → 미매칭 시 임베딩 | 상위 50~100개는 CI 매칭 가능, 롱테일은 임베딩 |
| **Tier 3: 임베딩 전용** | 전공(47,163 고유값), 직무명(자유 텍스트), 롱테일 스킬 | 임베딩 cosine similarity | 표현 다양성 높음, 정규화 시 거짓 동일성 위험 |

#### [v12] 비교 방법별 Confidence 보정 테이블

| 비교 방법 | Confidence | 적용 대상 |
|---|---|---|
| code-hub 코드 매칭 (CI) | 0.95 | Tier 1 (대학교, 회사명), Tier 2 상위 스킬 |
| code-hub synonyms 매칭 | 0.85 | Tier 2 상위 스킬 |
| 임베딩 유사도 (≥ 0.90) | 0.80 | Tier 2 미매칭 스킬, Tier 3 전공/직무 |
| 임베딩 유사도 (0.80~0.90) | 0.70 | Tier 2/3 경계 영역 |
| 임베딩 유사도 (0.75~0.80) | 0.60 | Tier 3 전공 (넓은 의미적 유사성) |
| 미매칭 (threshold 미달) | 0.0 | 매칭에서 제외 |

#### 임베딩 비교 구현

```python
def compute_embedding_similarity(text_a, text_b):
    """
    두 텍스트 간 임베딩 cosine similarity를 계산한다.
    임베딩 모델: text-multilingual-embedding-002 (04_graph_schema와 동일)
    """
    emb_a = embed_text(text_a)  # 1536d vector
    emb_b = embed_text(text_b)
    return cosine_similarity(emb_a, emb_b)


def compute_embedding_similarity_batch(texts_a, texts_b, threshold=0.80):
    """
    두 텍스트 집합 간 임베딩 유사도를 계산하고 threshold 이상인 쌍을 반환한다.

    [v14] 구현 시 ANN 인덱스(Vertex AI Vector Search 등) 사용 권장.
    아래는 로직 설명용 pseudo-code이며, 실서비스에서는 O(n*m) brute-force 대신
    ANN 기반 검색으로 대체한다.

    Returns: [{"a": str, "b": str, "similarity": float}, ...]
    """
    # 1. batch_embed(texts_a), batch_embed(texts_b) 수행
    # 2. 각 text_a에 대해 threshold 이상인 best match를 texts_b에서 탐색
    # 3. ANN 인덱스 사용 시: texts_b를 인덱싱 → texts_a로 top-1 쿼리
    pass
```

### 1.7 기타 코드 매핑

| code-hub Enum | 온톨로지 활용 | 비고 |
|---|---|---|
| `POSITION_GRADE` (15코드) | `vacancy.seniority` 추정 보조 | 직급 코드 → seniority 매핑 테이블, **fill rate 39.16%** |
| `POSITION_TITLE` (16코드) | `Experience.scope_type` 추정 보조 | 직책 코드 → scope_type 매핑, **fill rate 29.45%** |
| `BENEFIT` | `operating_model.facets` 보조 신호 | 복리후생 → 운영 방식 힌트 |
| `EDUCATION_LEVEL` | `requirement.education_code` | 학력 요건 매핑 |
| `AREA_CODE` (5단계 계층) | `work_condition.location` | 근무지 정보 |
| `LICENSE` | CandidateContext 확장 (v2) | **주의: resume-hub `CERTIFICATE` ≠ codehub `LICENSE`** [v12 D5] |
| `LANGUAGE_EXAM` | CandidateContext 확장 (v2) | **주의: resume-hub `LANGUAGE_TEST` ≠ codehub `LANGUAGE_EXAM`** [v12 D5] |
| `DESIGNATION` | Vacancy.seniority 추론 | job-hub `overview.designation_codes` 소스 |

### 1.8 Certificate Type 매핑 변환 [v12 D5 신규]

resume-hub와 code-hub 간 자격증 타입명이 불일치한다. 변환 없이 codehub 조회 시 매핑 실패.

```python
# 필수 변환 테이블
CERT_TYPE_MAPPING = {
    "CERTIFICATE": "LICENSE",        # resume-hub → codehub
    "LANGUAGE_TEST": "LANGUAGE_EXAM", # resume-hub → codehub
}

def resolve_certificate_code(cert_type_resume, cert_code):
    """
    resume-hub의 certificate type을 codehub의 dict key로 변환 후 조회한다.
    """
    codehub_type = CERT_TYPE_MAPPING.get(cert_type_resume)
    if not codehub_type:
        return None
    return lookup_common_code(type=codehub_type, code=cert_code)
```

**규모**: 13,573,606건, 이력서 커버리지 54%, 이력서당 평균 3.14개

---

## 2. job-hub → CompanyContext 매핑

### 2.1 ID 매핑

| 온톨로지 필드 | job-hub 소스 | 비고 |
|---|---|---|
| `company_id` | `job.user_ref_key` 또는 `job.workspace_id` | 기업 식별자. 동일 기업의 복수 공고를 묶는 키 |
| `job_id` | `job.id` (VARCHAR 126) | 공고 식별자 |
| `company_name` | `work_condition.company_name` | 근무 기업명 |

### 2.2 company_profile 매핑

| 온톨로지 필드 | job-hub 소스 | 추출 방법 | v10 대비 변경 |
|---|---|---|---|
| `industry_code` | `overview.industry_codes[0]` | Lookup (code-hub) | **v11**: code-hub INDUSTRY 코드 직접 사용 (v10: NICE만) |
| `industry_label` | code-hub에서 코드명 조회 | Lookup | code-hub `detail_name` |
| `is_regulated_industry` | `overview.industry_codes[0]` → code-hub 대분류 | Rule | K=금융, Q=보건, D=전기, H=운수 → true |

### 2.3 vacancy 매핑

| 온톨로지 필드 | job-hub 소스 | 추출 방법 | 비고 |
|---|---|---|---|
| `role_title` | `overview.work_fields[]` + `overview.job_classification_codes[]` | Rule + Lookup | work_fields는 자유 텍스트, job_classification_codes는 정규화 코드 |
| `seniority` | `overview.designation_codes[]` | Rule (매핑 테이블) | code-hub DESIGNATION → seniority 변환 |
| `hiring_context` | `overview.descriptions` (JSONB) | LLM | BUILD_NEW/SCALE_EXISTING/RESET/REPLACE |
| `scope_description` | `overview.descriptions` (JSONB) | LLM | 비구조화 텍스트에서 추출 |
| `team_context` | `overview.descriptions` (JSONB) | LLM | 비구조화 텍스트에서 추출 |
| `tech_stack` | `skill` 테이블 (type=HARD) | Lookup (code-hub) | **v11 신규**: 구조화된 스킬 데이터 직접 사용 |

**designation_codes → seniority 매핑 테이블**:

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
|---|---|---|---|
| `responsibilities` | `overview.descriptions` (JSONB) | LLM | 상세 요강에서 추출 |
| `requirements` | `requirement` 테이블 전체 | Rule + LLM | 구조화 필드(career_types, education_code) + 비구조화(descriptions) |
| `preferred` | `requirement.preference_codes[]` | Lookup (code-hub PREFERRED) | 구조화된 우대조건 코드 직접 사용 |
| `tech_stack` | `skill` 테이블 (type=HARD, job_id 기준) | Lookup | code-hub HARD_SKILL 코드 직접 사용 |

### 2.5 operating_model facets 매핑 보강

| 온톨로지 facet | job-hub 보조 소스 | 추출 방법 | 비고 |
|---|---|---|---|
| `speed` | `overview.always_hire`, `overview.close_on_hire` | Rule | 상시채용/채용시마감 시그널 |
| `autonomy` | `work_condition.work_schedule_option_types[]` | Rule | FLEXIBLE_WORK, WORK_HOURS_NEGOTIABLE |
| `autonomy` | `overview.recruitment_option_types[]` | Rule | REMOTE_WORK_AVAILABLE |
| `process` | `overview.descriptions` (JSONB) | LLM | 기존 유지 |

```python
def extract_structured_facet_signals(job):
    """
    job-hub의 구조화된 필드에서 operating_model facet 시그널을 추출한다.

    [v12] F4 전체 ACTIVE 비율은 여전히 낮지만 (<10%),
    이 구조화 시그널은 LLM 없이도 즉시 추출 가능하여 기업측 facet 기초 데이터로 활용.
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

## 3. resume-hub → CandidateContext 매핑

### 3.1 ID 매핑

| 온톨로지 필드 | resume-hub 소스 | 비고 |
|---|---|---|
| `candidate_id` | `SiteUserMapping.id` | **7,780,115** 고유 사용자 |
| `resume_id` | `Resume.id` (main_flag=1 필터) | **main_flag=1 필터 필수**, 96.23% 보유 (7,715,508) |

#### [v18] 다중 이력서 처리 규칙 [R-10/U-2]

한 사용자(`SiteUserMapping.id`)가 복수의 Resume을 보유하는 경우의 처리 규칙:

| 케이스 | 비율 | 처리 규칙 |
|---|---|---|
| main_flag=1 이력서 1개 | 96.23% | 해당 이력서 사용 (정상 케이스) |
| main_flag=1 이력서 없음 | 3.77% (~294K 사용자) | `resume.userUpdatedAt` 기준 **최신 이력서**를 사용. 단, 최신 이력서도 `COMPLETED` + `PUBLIC`이어야 함. 조건 미충족 시 해당 사용자 **매칭 대상에서 제외** |
| main_flag=1 이력서 복수 | 데이터 무결성 확인 필요 | **가장 최근 `userUpdatedAt`** 이력서를 사용. 이 케이스가 1% 이상 발견되면 데이터팀에 무결성 이슈로 에스컬레이션 |

> **구현 시 검증 필요**: main_flag=1이 복수 존재하는 사용자가 실제로 있는지 확인하고, 있다면 빈도를 측정한다.

**[v12 D6] 서비스 가용 이력서 풀 필터링**:

```python
def get_service_resume_pool():
    """
    서비스 가용 이력서 풀 정의.

    전체 8,018,110 → 활성 7,975,889 (99.5%)
    → PUBLIC + COMPLETED: 5,545,741 (69.2%)
      → EXPERIENCED: 3,726,057 (67.2%)
      → NEW_COMER: 1,819,684 (32.8%)
      → HIGH + PREMIUM 품질: 3,183,554 (57.4%)
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

# [v16] v1 매칭 대상 제한
def get_v1_matching_pool():
    """
    v1에서 MappingFeatures 계산 대상은 EXPERIENCED만.
    NEW_COMER(30.9%)는 CandidateContext 기본 속성만 생성하고 매칭 대상에서 제외.

    전체 5,545,741 → EXPERIENCED: 3,726,057 (67.2%)
    → HIGH+PREMIUM 품질: ~2,139,000 (추정 57.4%)

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

**[v12] Resume 품질 등급 분포**:

| 등급 | 점수 범위 | 비율 |
|---|---|---|
| LOW | 0-3 | 8.6% |
| MEDIUM | 3-6 | 29.9% |
| HIGH | 6-9 | 48.3% |
| PREMIUM | 9-11 | 13.3% |

### 3.2 Experience 매핑

| 온톨로지 필드 | resume-hub 소스 | 추출 방법 | v12 실측 fill rate |
|---|---|---|---|
| `company` | `Career.companyName` | Lookup | 99.96% (**4,479,983 고유값**) |
| `role_title` | `Career.jobClassificationCodes[]` + `Career.positionTitleCode` | Lookup (code-hub) | jobClassCodes ~100%, positionTitle **29.45%** |
| `period.start` | `Career.period.period` (DATERANGE 시작) | Rule | ~100% |
| `period.end` | `Career.period.period` (DATERANGE 끝) | Rule | ~100% (EMPLOYED 10.5% = "present") |
| `period.duration_months` | **계산** (started_on ~ ended_on) | Rule | **daysWorked 100% 제로 → 직접 계산** [v12 D3] |
| `tech_stack` | `Skill` 테이블 (type=HARD, resume_id 기준) | Lookup (code-hub) | 38.3% (3,074,732 이력서) |
| `scope_type` | `Career.positionTitleCode` → `positionGradeCode` → LLM | Rule + LLM | positionTitle **29.45%**, positionGrade **39.16%** |
| `scope_summary` | `Career.workDetails` 또는 `CareerDescription.description` | LLM | workDetails ~56%, careerDesc **16.9%** |
| `outcomes` | `CareerDescription.description` + `SelfIntroduction` | LLM | careerDesc **16.9%** (1차), selfIntro **64.1%** (2차) |
| `situational_signals` | 텍스트 소스 복합 | LLM + Rule | 합집합 ~65-70% |

**[v12 D3] duration_months 계산** (Critical, 난이도 낮음):

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

**[v12 D4] CareerDescription FK 부재 제약**:

> **핵심 제약**: CareerDescription 테이블에 `career_id` FK가 없다. resume_id로만 연결되므로, 복수 경력이 있는 이력서에서 어떤 경력에 대한 기술인지 career 단위 매핑이 불가능하다. Outcome/SituationalSignal 추출 시 LLM이 텍스트 컨텍스트로 판단해야 한다.

```python
def extract_outcomes_from_career_description(resume_id, careers):
    """
    [v12 D4] CareerDescription은 resume 단위 귀속 (career_id FK 없음).

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

**scope_type 구조화 추정** [v12 보강]:

```python
POSITION_TO_SCOPE = {
    # positionTitleCode (직책) — Confidence 0.75
    "사원": "IC", "대리": "IC", "과장": "IC", "차장": "IC",
    "팀장": "LEAD", "파트장": "LEAD", "실장": "LEAD",
    "이사": "HEAD", "상무": "HEAD", "부사장": "HEAD",
    "대표": "FOUNDER", "CEO": "FOUNDER", "CTO": "HEAD",
}

def estimate_scope_type(career):
    """
    [v12] 추정 우선순위:
    1순위: positionTitleCode (직책, 29.45% fill rate) → confidence 0.75
    2순위: positionGradeCode (직급, 39.16% fill rate) → confidence 0.65
    3순위: workDetails LLM 추출 (~56% fill rate) → confidence 0.50
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
|---|---|---|---|
| `role_evolution` | `Career[]` (전체 경력 시퀀스) | Rule + LLM | 경력 보유자 68.9% |
| `domain_depth` | `Career[].jobClassificationCodes[]` + `WorkCondition.workJobField` | Rule | 82.6% (jobClassCodes 기반) |
| `work_style_signals` | `SelfIntroduction.description` + `Career.workDetails` | LLM | selfIntro 64.1%, **v1 대부분 null** |

**domain_depth 구조화 추출**:

```python
def extract_domain_depth_structured(resume):
    """
    [v12] 구조화 직무 코드 기반 primary_domain 추정.
    LLM 추출 이전에 수행하여 기초 분석을 확보한다.

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
|---|---|---|
| `company_name` | `Career.companyName` | 99.96% fill rate |
| `industry_code` | 1순위: job-hub 역참조, 2순위: NICE | job-hub 역참조 confidence 0.75 |
| `brn` | `Career.businessRegistrationNumber` | **62% fill rate** — 정규화 1차 키 |

```python
def enrich_past_company_from_jobhub(company_name):
    """
    [v12] 후보의 이전 회사명 → job-hub 역참조 → NICE fallback.
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

### 3.5 Person 노드 보강 속성 [v12 D2 신규]

v11까지 누락되었던 Person 속성을 데이터 분석 결과에 기반하여 추가한다.

| 속성 | 소스 | fill rate | 용도 | 비고 |
|---|---|---|---|---|
| `gender` | `profile.gender` | 100% (M 52.5% / F 47.4% / OTHER 0.1%) | 매칭 편향 모니터링 | **매칭 점수에 사용 금지**, 별도 분석 테이블 관리 권장 [v14] |
| `age` | `profile.age` | 93.3% (평균 36.2세) | 세그먼트 분석 보조 | **6.7% 이상치(age>100)** → 1~100 필터, 별도 분석 테이블 관리 권장 [v14] |
| `career_type` | `resume.careerType` | 100% | 경력/신입 세그먼트 | EXPERIENCED 69.1% / NEW_COMER 30.9% |
| `freshness_weight` | `resume.userUpdatedAt` 기반 계산 | 100% | 데이터 신선도 가중치 | 31.6% 5년+ 미갱신 → 감쇠 적용 |
| `education_level` | `education.schoolType` (MAX) | 95.6% | 학력 필터링 | **finalEducationLevel 35.6% 불일치 → education.schoolType을 진실 소스로** [v12 D8] |

```python
def compute_freshness_weight(user_updated_at):
    """
    [v12 D2] 이력서 신선도 가중치.

    90일 이내: 1.0
    1년 이내: 0.9
    3년 이내: 0.7
    5년 이내: 0.5
    5년+: 0.3

    실측: 90일 이내 활성 13.9%, 반감기 31.5개월, 5년+ 미갱신 31.6%
    """
    days_since = (date.today() - user_updated_at.date()).days
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

### 3.6 보조 데이터 매핑 [v12 신규]

온톨로지 노드에 직접 매핑되지 않지만, 매칭/추론에 보조적으로 활용되는 데이터.

| 데이터 | 규모 | 활용 | 비고 |
|---|---|---|---|
| Education | 11.2M건, 95.6% 커버리지 | Person.education_level, 학력 필터링 | schoolType을 진실 소스로 |
| Major | 7.1M건, 47,163 고유값 | F3 domain_fit 보조 (전공-산업 연관 추론) | **정규화 불가 → Tier 3 임베딩** |
| Certificate | 13.6M건, 54% 커버리지 | 자격증 매칭 (JD 요구 vs 보유) | **type 매핑 변환 필수** (1.8절) |
| Language | 654K건, 6.3% 커버리지 | 어학 능력 매칭 | 영어 62.1%, 일본어 14.8% |
| Experience(활동) | 6.6M건, 27.9% | INTERNSHIP → 초기 경력, OVERSEAS → 국제 시그널 | |
| Award | 이력서 8.8% 커버리지 | 메타데이터만 활용 | **description 100% 빈값** |

---

## 4. 구조화 코드 기반 매칭 강화 (MappingFeatures 보강)

### 4.1 F3 domain_fit: 산업 코드 직접 매칭

> **[v14] 정본 안내**: industry code 매칭의 계산 로직 정본은 `03_mapping_features.md F3 compute_domain_fit()`이다. 본 절은 데이터 소스 관점의 매핑 정보만 기술한다.

**데이터 소스 매핑**:

| 측 | 데이터 소스 | 코드 타입 | fill rate |
|---|---|---|---|
| Company | `overview.industry_codes` (job-hub) | INDUSTRY (3depth) | 90%+ (예상) |
| Candidate (1순위) | `workcondition.industryCodes` | INDUSTRY_SUBCATEGORY (2depth) | **34%** (66% 빈배열) |
| Candidate (2순위) | `PastCompanyContext.industry_code` | INDUSTRY (3depth) | job-hub 역참조 (§3.4) |

**비교 전략 요약** (상세 계산은 `03_mapping_features.md F3` 참조):
- 동일 코드 체계(INDUSTRY) 내에서 계층적 비교 (3depth → 2depth → 1depth)
- candidate 측이 INDUSTRY_SUBCATEGORY(2depth)인 경우, company INDUSTRY(3depth)를 상위로 올려 비교
- candidate industryCodes 66% 빈배열이므로 PastCompanyContext 역참조(§3.4)를 보조 소스로 활용

### 4.2 F5 role_fit: 직무 코드 매칭

```python
def compute_job_classification_match(vacancy_job_codes, candidate_career_codes):
    """
    3depth 일치: 0.15 보너스
    2depth 일치: 0.08 보너스
    """
    best_bonus = 0.0
    for v_code in vacancy_job_codes:
        v_detail = lookup_common_code(type="JOB_CLASSIFICATION", code=v_code)
        if not v_detail:
            continue
        for c_code in candidate_career_codes:
            c_detail = lookup_common_code(type="JOB_CLASSIFICATION", code=c_code)
            if not c_detail:
                continue
            if v_code == c_code:
                best_bonus = max(best_bonus, 0.15)
            elif (v_detail.group_code == c_detail.group_code and
                  v_detail.sub_code == c_detail.sub_code):
                best_bonus = max(best_bonus, 0.08)
    return best_bonus
```

### 4.3 스킬 매칭 (코드 매칭 + 임베딩 하이브리드)

```python
def compute_skill_overlap(vacancy_skills_raw, candidate_skills_raw, site_type="JOBKOREA"):
    """
    [v12] 실측 데이터 반영:
    - 스킬 codehub 매칭률 2.4% → 대부분 임베딩 비교로 귀결
    - 코드 매칭 가중치 1.0 + 임베딩 매칭 가중치 0.8

    주의: 이력서 스킬 커버리지 38.3%
    [v16] SOFT_SKILL 매칭 제외: type=HARD 스킬만 매칭 대상.
    SOFT_SKILL TOP 10의 60%가 "성실성(25.2%), 긍정적(17.3%)"으로 편중되어
    매칭 노이즈를 유발하므로, vacancy/candidate 양쪽 모두 type=HARD만 사용한다.
    SOFT_SKILL은 후보 프로필 표시용으로만 Skill 노드에 저장한다.
    """
    # [v16] SOFT_SKILL 제외: type=HARD 스킬만 매칭 대상
    v_normalized = [normalize_skill(s, site_type) for s in vacancy_skills_raw]  # vacancy는 skill 테이블에서 type=HARD 필터 적용 후 전달
    c_normalized = [normalize_skill(s, site_type) for s in candidate_skills_raw]  # candidate도 type=HARD 필터 적용 후 전달

    v_coded = {s["skill_id"] for s in v_normalized if s["normalized"]}
    c_coded = {s["skill_id"] for s in c_normalized if s["normalized"]}

    v_uncoded = [s["name"] for s in v_normalized if not s["normalized"]]
    c_uncoded = [s["name"] for s in c_normalized if not s["normalized"]]

    if not v_coded and not v_uncoded:
        return None

    code_intersection = v_coded & c_coded
    code_coverage = len(code_intersection) / len(v_coded) if v_coded else 0.0

    embedding_matches = compute_embedding_similarity_batch(
        v_uncoded, c_uncoded, threshold=0.85
    ) if v_uncoded and c_uncoded else []
    embedding_coverage = len(embedding_matches) / len(v_uncoded) if v_uncoded else 0.0

    total_vacancy = len(v_coded) + len(v_uncoded)
    weighted_matches = len(code_intersection) * 1.0 + len(embedding_matches) * 0.8
    overall_coverage = weighted_matches / total_vacancy if total_vacancy else 0.0

    return {
        "overall_coverage": min(1.0, overall_coverage),
        "code_match": {"matched": list(code_intersection), "coverage": code_coverage},
        "embedding_match": {"matched": embedding_matches, "coverage": embedding_coverage},
        "unmatched_vacancy_skills": list(
            (v_coded - c_coded) | set(s for s in v_uncoded if s not in [m["a"] for m in embedding_matches])
        ),
    }
```

---

## 5. 추출 파이프라인 (v12)

### 5.1 CompanyContext 추출 파이프라인

```
[job-hub DB]
    │
    ├─[1] 구조화 데이터 조회 (Rule-based)
    │   ├─ job.id, work_condition.company_name → company_id, company_name
    │   ├─ overview.industry_codes → industry_code (code-hub Lookup)
    │   ├─ overview.designation_codes → seniority (매핑 테이블, 2.3절)
    │   ├─ overview.job_classification_codes → role_title (code-hub Lookup)
    │   ├─ skill 테이블 (type=HARD) → tech_stack (code-hub 정규화)
    │   ├─ requirement → 자격요건 구조화 필드
    │   ├─ work_condition → 근무조건 구조화 필드
    │   └─ overview.always_hire, recruitment_option_types → facet 보조 시그널 (2.5절)
    │
    ├─[1.5] 비정형 값 비교 준비 (v11.1)
    │   ├─ skill 테이블 원본 값 → normalize_skill() → 경량 정규화 (CI + synonyms)
    │   ├─ 정규화 성공 (예상 ~2.4%) → code-hub skill_id 기반 비교
    │   ├─ 정규화 실패 (예상 ~97.6%) → 원본 유지, 임베딩 벡터 생성
    │   └─ work_fields (자유 텍스트 직무명) → 임베딩으로 비교
    │
    ├─[2] NICE 데이터 조회 (보조)
    │   ├─ company_name → NICE 매칭
    │   └─ 직원수, 매출, 설립연도 등
    │
    ├─[3] LLM 추출 (비구조화 텍스트만)
    │   ├─ overview.descriptions (JSONB) → hiring_context, scope_description, team_context
    │   ├─ overview.descriptions (JSONB) → responsibilities
    │   └─ overview.descriptions (JSONB) → operating_model facets
    │
    └─[4] 교차 검증
        ├─ code-hub industry_code vs NICE industry_code
        └─ 구조화 tech_stack vs LLM 추출 tech_stack
```

### 5.2 CandidateContext 추출 파이프라인

```
[resume-hub DB]
    │
    ├─[0] 서비스 풀 필터링 [v12 D6]
    │   ├─ PUBLIC + COMPLETED + main_flag=1 → 5,545,741
    │   ├─ 품질 등급 HIGH+PREMIUM → 3,183,554 (57.4%)
    │   └─ deletedAt IS NULL 필터
    │
    ├─[1] 구조화 데이터 조회 (Rule-based)
    │   ├─ SiteUserMapping.id → candidate_id
    │   ├─ Resume.id (main_flag=1) → resume_id
    │   ├─ Profile → gender, age(1~100 필터), career_type
    │   ├─ Resume.userUpdatedAt → freshness_weight (3.5절)
    │   ├─ Career[] → company, period (DATERANGE → duration_months 계산) [v12 D3]
    │   ├─ Career.positionTitleCode/positionGradeCode → scope_type 1차 추정
    │   ├─ Career.jobClassificationCodes → role_title (code-hub Lookup)
    │   ├─ Skill[] (type=HARD) → tech_stack (code-hub 정규화, 38.3% 커버리지)
    │   ├─ Career[].jobClassificationCodes 반복 분석 → domain_depth 기초 (3.3절)
    │   ├─ Education[] → education_level (schoolType 진실 소스) [v12 D8]
    │   └─ Certificate[] → type 변환 후 codehub 조회 [v12 D5]
    │
    ├─[1.5] 비정형 값 비교 준비 (v11.1)
    │   ├─ Skill 테이블 원본 값 → normalize_skill() → 경량 정규화
    │   ├─ 정규화 성공 → code-hub skill_id 기반 비교
    │   ├─ 정규화 실패 → 원본 유지, 임베딩 벡터 생성
    │   └─ Major.name (47,163 고유값) → Tier 3 임베딩 전용
    │
    ├─[2] LLM 추출 (비구조화 텍스트, Experience별)
    │   ├─ Career.workDetails (~56%) → scope_summary, outcomes, situational_signals
    │   ├─ Career.workDetails → scope_type 보정 (구조화 결과 교차 검증)
    │   └─ Career.workDetails → failure_recovery (있을 때만)
    │
    ├─[3] LLM 추출 (전체 커리어)
    │   ├─ CareerDescription.description (16.9%) → outcomes 1차 추출 [v12 D4 제약]
    │   ├─ SelfIntroduction[] (64.1%) → outcomes 2차 추출, work_style_signals
    │   └─ Career[] 전체 → domain_depth (구조화 결과와 LLM 결과 병합)
    │
    ├─[4] PastCompanyContext 보강
    │   ├─ Career.companyName → job-hub 역참조 (3.4절, confidence 0.75)
    │   ├─ Career.businessRegistrationNumber (62%) → BRN 기반 클러스터링
    │   └─ NICE Lookup fallback
    │
    └─[5] 교차 검증
        ├─ 구조화 scope_type vs LLM scope_type
        ├─ 구조화 tech_stack vs LLM tech_stack
        └─ education.schoolType vs resume.finalEducationLevel (35.6% 불일치 로깅)
```

---

## 6. 데이터 품질 및 coverage — 실측치 [v12 전면 교체]

### 6.1 resume-hub 필드 가용성 (실측)

| 온톨로지 필드 | resume-hub 소스 필드 | **실측 fill rate** | 비고 |
|---|---|---|---|
| company | Career.companyName | **99.96%** (18.7M건) | 4,479,983 고유값, 정규화 필수 |
| period | Career.period.period | **~100%** | daysWorked 100% 제로 → 직접 계산 |
| positionTitleCode | Career.positionTitleCode | **29.45%** | 직책 코드 |
| positionGradeCode | Career.positionGradeCode | **39.16%** | 직급 코드 |
| jobClassificationCodes | Career.jobClassificationCodes | **~100%** (경력 보유자) | 242개 코드, codehub 100% 매핑 |
| workDetails | Career.workDetails | **~56%** (중앙값 96자) | 정보량 제한 |
| CareerDescription | CareerDescription.description | **16.9%** (1,351,836) | 중앙값 527자, **career_id FK 없음** |
| SelfIntroduction | SelfIntroduction.description | **64.1%** (7,962,522) | 중앙값 1,320자 |
| Skill (HARD) | Skill 테이블 | **38.3%** (3,074,732) | 6.77개/이력서, **97.6% 비표준** |
| departmentName | Career.departmentName | **58.9%** | scope_type/role 추론 보조 |

### 6.2 job-hub 필드 가용성

| 온톨로지 필드 | job-hub 소스 필드 | 예상 fill rate | 비고 |
|---|---|---|---|
| industry_code | overview.industry_codes | 90%+ | 대부분 공고에 산업 코드 존재 |
| job_classification | overview.job_classification_codes | 85%+ | 직무 분류 코드 |
| tech_stack (구조화) | skill 테이블 | 60~70% | 일부 공고는 스킬 미입력 |
| designation_codes | overview.designation_codes | 40~50% | 직급 정보 선택 입력 |
| descriptions (JD 본문) | overview.descriptions (JSONB) | 95%+ | **Vacancy.evidence_chunk 소스** |
| employment_types | overview.employment_types | 90%+ | 고용 형태 |
| work_schedule_options | work_condition.work_schedule_option_types | 50~60% | 선택 입력 |

> **주의**: job-hub 데이터 상세 분석(레코드 수, 품질, 커버리지)은 **별도 분석 필요** — Phase 4-1

### 6.3 Graceful Degradation 전략

| 구조화 데이터 | 누락 시 fallback | confidence 영향 |
|---|---|---|
| industry_codes | NICE industry_code 사용 | confidence 유지 |
| designation_codes | JD 텍스트에서 LLM 추출 | confidence -0.10 |
| skill 테이블 | JD/이력서 텍스트에서 LLM 추출 | confidence -0.05 |
| positionTitleCode | positionGradeCode → workDetails LLM | confidence -0.15~-0.25 |
| jobClassificationCodes | 임베딩 유사도 fallback | confidence -0.10 |
| CareerDescription | SelfIntroduction fallback | confidence -0.10 |

### 6.4 비정형 값 비교 품질 모니터링

| 지표 | 산식 | 목표치 | 비고 |
|---|---|---|---|
| **스킬 코드 매칭률** | 경량 정규화 성공 건 / 전체 스킬 건 | 참고용 (실측 ~2.4%) | 낮아도 임베딩이 보완 |
| **임베딩 매칭 커버리지** | 임베딩 매칭 성공 건 / 코드 미매칭 건 | >= 70% | 임베딩 모델의 스킬명 이해도 |
| **임베딩 매칭 정확도** | human eval 샘플 10건 정확률 | >= 85% | 월간 샘플링 검증 |
| **전공/직무 임베딩 유사도 분포** | 매칭 쌍의 similarity 분포 | 중앙값 >= 0.80 | threshold 조정 근거 |

### 6.5 피처별 v1 활성화 전망

> **[v18 R-5] 정본 안내**: 피처별 ACTIVE 전망의 정본은 `03_mapping_features.md §7.3`이다. 데이터 소스 관점의 병목 분석은 아래 표를 참조하되, 피처 설계 관점의 상세는 정본 문서를 참조한다.

| 피처 | 주요 데이터 병목 (본 문서 범위) |
|---|---|
| F1 stage_match | 회사명→Organization 정규화 (4.48M 고유값), NICE 매핑 |
| F2 vacancy_fit | careerDescription **16.9%** 보유율이 SituationalSignal 추출 병목 |
| F3 domain_fit | industryCodes 66% 빈배열이나 NICE/codehub/PastCompanyContext 보완 가능 |
| F4 culture_fit | work_style_signals 추출 가능 데이터 부재 |
| F5 role_fit | positionGrade/Title 저입력 (29-39%) |

---

## 7. 정규화 선행 과제 [v12 D9 신규]

구현 전 반드시 완료해야 하는 데이터 정제 과제. 난이도 순서가 아닌 **영향 범위** 순서로 정렬.

### 7.1 days_worked 계산 (Critical, 난이도 낮음)

| 항목 | 값 |
|---|---|
| 대상 | career 18,709,830건 |
| 현재 상태 | **100% 제로값** |
| 계산 소스 | career.period.period (started_on ~ ended_on) |
| 영향 범위 | Chapter.duration_months, F1 stage_match, F5 role_fit |

### 7.2 Certificate type 매핑 (Critical, 난이도 낮음)

| resume-hub 값 | codehub dict 키 |
|---|---|
| `CERTIFICATE` | `LICENSE` |
| `LANGUAGE_TEST` | `LANGUAGE_EXAM` |

### 7.3 회사명 정규화 (Critical, 난이도 중간)

| 항목 | 값 |
|---|---|
| 고유 회사명 수 | **4,479,983개** |
| BRN 입력률 | 62% |
| 다중 표기 사례 | "쿠팡" 관련 3종 = 합산 42,085건 |
| 접근 | BRN 1차 클러스터링(62%) → 회사명 유사도 2차 보완(38%) |
| 영향 범위 | Organization 노드, Chapter→Org 엣지, F1 stage_match |

### 7.4 스킬 정규화 (Critical, 난이도 높음)

| 항목 | 값 |
|---|---|
| 총 고유 스킬 코드 | 101,925개 |
| codehub 매핑 완료 | 2,398개 (**2.4%**) |
| 접근 | v11.1: 경량 정규화 (CI + 동의어만) → 실패 시 임베딩 폴백 |
| 영향 범위 | Skill 노드, Chapter→Skill 엣지, F3 domain_fit |

### 7.5 전공명 정규화 (Medium, 난이도 중간)

| 항목 | 값 |
|---|---|
| 고유 전공명 | **47,163개** |
| 다중 표기 | "경영학" vs "경영학과" vs "경영학부" (4종 = 326K건) |
| 접근 | **Tier 3 (임베딩 전용)** — 정규화 금지, 오매칭 방지 |

---

## 8. 구현 로드맵 [v12 D10 신규]

### Phase 1: 기반 데이터 정제 (구현 전 선행)

| 순서 | 과제 | 난이도 | 영향 범위 |
|---|---|---|---|
| 1 | days_worked (duration_months) 계산 | 낮음 | Chapter, F1, F5 |
| 2 | certificate type 매핑 변환 | 낮음 | 코드 매핑 정합성 |
| 3 | 회사명 정규화 파이프라인 | 중간 | Organization, Chapter→Org 엣지, F1 |
| 4 | 스킬 정규화 (경량 + 임베딩 폴백) | 높음 | Skill, Chapter→Skill 엣지, F3 |
| 5 | 전공명 정규화 (Tier 3 임베딩) | 중간 | F3 domain_fit 보조 |

### Phase 2: 핵심 노드/엣지 구축

| 순서 | 과제 | 의존성 |
|---|---|---|
| 1 | Person + Chapter 노드 생성 | Phase 1-1 |
| 2 | Organization 노드 + OCCURRED_AT 엣지 | Phase 1-3 |
| 3 | Industry 노드 + IN_INDUSTRY 엣지 | codehub 63개 코드 (즉시 가능) |
| 4 | Role 노드 + PERFORMED_ROLE 엣지 | codehub JOB_CLASSIFICATION 242개 코드 |
| 5 | Skill 노드 + USED_SKILL 엣지 | Phase 1-4 |

### Phase 3: LLM 추출 노드/엣지

| 순서 | 과제 | 의존성 |
|---|---|---|
| 1 | Outcome 추출 (careerDescription + selfIntroduction) | Phase 2-1 |
| 2 | SituationalSignal 추출 | Phase 2-1 |
| 3 | Person 속성 보강 (role_evolution_pattern, primary_domain) | Phase 3-1, 3-2 |

### Phase 4: 기업측 + 매핑

| 순서 | 과제 | 의존성 |
|---|---|---|
| 1 | job-hub 상세 분석 | 독립 (병렬 가능) |
| 2 | Vacancy 노드 (구조화 + LLM 추출) | Phase 4-1 |
| 3 | MAPPED_TO 엣지 (매핑 피처 F1~F5 계산) | Phase 2, 3 완료 |

---

## 9. 사용 불가 / 제거 대상 필드 [v12 D1 통합]

| 필드 | 사유 |
|---|---|
| `profile.birthday` | 100% sentinel '1900-01-01' |
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

## 10. LLM 비용 총 추정 [v14 신규]

전체 파이프라인에서 LLM 호출이 필요한 지점과 예상 비용을 산정한다.

### 10.1 LLM 호출 지점 및 비용 추정

| # | 호출 지점 | 대상 규모 | 평균 입력 토큰 | 모델 | 예상 비용 |
|---|---|---|---|---|---|
| L1 | CandidateContext: Outcome/Signal 추출 (careerDesc+selfIntro) | ~2.2M 이력서 (서비스 풀 70%) | ~1K tokens | Gemini 2.0 Flash | **~$220** |
| L2 | CandidateContext: scope_type LLM fallback (workDetails) | ~1.0M 이력서 (구조화 미매칭 분) | ~200 tokens | Gemini 2.0 Flash | **~$20** |
| L3 | CandidateContext: role_evolution 추출 | ~2.2M 이력서 | ~500 tokens | Gemini 2.0 Flash | **~$110** |
| L4 | CandidateContext: work_style_signals 추출 | ~2.2M 이력서 | ~500 tokens | Gemini 2.0 Flash | **~$110** |
| L5 | CompanyContext: vacancy hiring_context/description | 공고 수 미정 (추정 ~100K) | ~1K tokens | Gemini 2.0 Flash | **~$10** |
| L6 | CompanyContext: operating_model facets | ~100K 공고 | ~1K tokens | Gemini 2.0 Flash | **~$10** |
| L7 | CompanyContext: stage_estimate LLM fallback | ~30K 공고 (Rule 미매칭 분) | ~500 tokens | Gemini 2.0 Flash | **~$1.5** |
| L8 | 크롤링: 홈페이지+뉴스 추출 | ~1,000 기업 × ~10페이지 | ~2K tokens | Gemini 2.0 Flash | **~$2** (월간 $107 포함) |
| | **합계 (1회 전체 처리)** | | | | **~$484** |

> 비용 기준: Gemini 2.0 Flash input $0.10/1M tokens, output $0.40/1M tokens (2026-03 기준)
> 출력 토큰은 입력의 ~30%로 추정하여 합산
>
> **[v15] 주의 (N14-1)**: output token 30% 가정은 보수적 하한이다. Outcome/Signal 추출(L1)처럼 구조화된 JSON을 출력하는 경우 output이 입력의 50~80%에 달할 수 있어, 실제 비용이 ~$700까지 상승할 가능성이 있다. **Phase 3 착수 전 L1에 대해 샘플 10건으로 실측 후 비율을 보정해야 한다.** 전체 비용이 $1,000 이내라면 관리 가능 범위로 판단한다.

### 10.2 처리 시간 추정

| 단계 | 대상 규모 | 동시 처리 수 | 예상 소요 시간 |
|---|---|---|---|
| L1 Outcome/Signal 추출 | 2.2M건 | 50 병렬 | ~44시간 |
| L2~L4 기타 CandidateContext | 2.2M건 | 50 병렬 | ~30시간 |
| L5~L7 CompanyContext | ~100K건 | 50 병렬 | ~1시간 |
| L8 크롤링 | 1,000기업 | 10 병렬 | ~5시간 |
| **전체** | | | **~80시간 (3.3일)** |

> **결론**: 1회 전체 파이프라인 LLM 비용은 **~$500 이내**로 관리 가능한 수준이다. 증분 처리(신규/변경분만) 시 월간 비용은 이보다 크게 감소한다.

---

## 11. v11 → v12 마이그레이션 영향

### 11.1 변경 없는 항목

- Evidence 통합 모델 (source_type enum 유지)
- confidence 캘리브레이션 기준
- structural_tensions taxonomy (8개)
- STAGE_SIMILARITY 매트릭스
- 크롤링 전략 (06_crawling_strategy.md)
- 비정형 값 비교 3-Tier 전략 (v11.1 유지)
- 평가 전략 (05_evaluation_strategy.md)

### 11.2 변경 항목 요약

| 문서 | v12 변경 내용 |
|---|---|
| 00_data_source_mapping | 실측 fill rate 전면 교체, Person 보강 속성 추가, days_worked 계산 로직, CareerDescription FK 제약, certificate type 매핑, Resume 품질 등급, 정규화 선행 과제, 구현 로드맵 |
| 01_company_context | 변경 없음 (v12는 데이터 소스 매핑 집중) |
| 02_candidate_context | Person 보강 속성(gender, age, freshness_weight) 적용 시 업데이트 필요 |
| 03_mapping_features | F1~F5 예상 ACTIVE 비율 실측 기반 보정 |
| 04_graph_schema | Person 노드 속성 추가 필요 (gender, career_type, freshness_weight, education_level) |
| 05_evaluation_strategy | 변경 없음 |
| 06_crawling_strategy | 변경 없음 |
