# 내부 데이터베이스 ↔ 온톨로지 매핑 가이드 v11

> 작성일: 2026-03-09 | 기준: v11 신규
>
> job-hub, resume-hub, code-hub 데이터베이스의 테이블/컬럼이 CompanyContext, CandidateContext, MappingFeatures, Graph Schema의 어떤 필드에 매핑되는지 정의한다.
>
> 이 문서는 v10까지 추상적으로 정의되었던 "JD 데이터", "이력서 데이터"의 실체를 구체화한다.
>
> **v11.1 변경** (2026-03-09): 비정형 값 비교 전략 (임베딩 기반)
> - [A9] 설계 원칙에 "임베딩 기반 비교 (Embedding-first Comparison)" 추가
> - [A9] 1.3절 `normalize_skill()` 경량 정규화로 축소 (CI 매칭 + synonyms만, fuzzy/한영사전 제거)
> - [A9] 1.5절 비정형 값 비교 전략 신규 (대상별 3-tier 전략: 정규화 적합 / 경량 정규화+임베딩 / 임베딩 전용)
> - [A9] 4.3절 `compute_skill_overlap()` 임베딩 유사도 기반으로 전환
> - [A9] 5.1/5.2절 추출 파이프라인에 임베딩 비교 단계 삽입
> - [A9] 6.4절 임베딩 비교 품질 모니터링 추가

---

## 0. 설계 원칙

| 원칙 | 설명 |
|---|---|
| **구조화 우선 (Structured-first)** | DB에 구조화된 코드/필드가 존재하면 LLM 추출 전에 먼저 활용한다. LLM은 비구조화 텍스트(descriptions, workDetails)에만 사용한다 |
| **코드 정규화 통일** | code-hub의 공통코드를 기준으로 산업/직무/스킬을 정규화한다. 외부 코드는 `foreign_code_mapping`을 통해 내부 코드로 변환 후 사용한다 |
| **임베딩 기반 비교 (Embedding-first Comparison)** [v11.1] | DB 컬럼의 값이 표준화되어 있지 않음을 전제한다. 스킬/전공/직무 등 표현이 다양한 항목은 코드 정규화를 강제하지 않고 **임베딩 유사도**로 비교한다. 정규화는 대학교/회사명 등 유한 집합에만 적용한다 (1.5절 참조) |
| **ID 연결** | 온톨로지의 company_id, candidate_id는 각각 job-hub의 `job.user_ref_key`, resume-hub의 `SiteUserMapping.id`에 대응된다 |
| **증분 보강** | DB 구조화 데이터를 기본 골격으로, LLM 추출 결과를 보강 레이어로 적용한다 |

---

## 1. code-hub 매핑

code-hub는 공고/이력서에서 공통으로 사용하는 **마스터 코드**를 관리한다. 온톨로지 전반에 걸쳐 정규화 기준이 된다.

### 1.1 산업 코드 → Industry 노드 / company_profile.industry_code

| code-hub Enum | 코드 계층 | 온톨로지 매핑 대상 | 용도 |
|---|---|---|---|
| `INDUSTRY_CATEGORY` | 1depth (대분류) | `Industry.category` | 산업 대분류, `is_regulated` 판정 |
| `INDUSTRY_SUBCATEGORY` | 2depth (중분류) | `Industry.industry_id` | 산업 중분류 |
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

### 1.2 직무 코드 → Role 노드

| code-hub Enum | 코드 계층 | 온톨로지 매핑 대상 | 용도 |
|---|---|---|---|
| `JOB_CLASSIFICATION_CATEGORY` | 1depth | `Role.category` | 직무 대분류 (engineering/product/design 등) |
| `JOB_CLASSIFICATION_SUBCATEGORY` | 2depth | Role 매칭 중간 레벨 | 직무 중분류 |
| `JOB_CLASSIFICATION` | 3depth | `Role.role_id` | 직무 소분류 (정규화된 역할) |

**정규화 전략 변경 (v10 → v11 → v11.1)**:
- v10: 동의어 사전 기반 수동 매핑 (`{"팀 리더": "Team Lead"}`)
- v11: code-hub `JOB_CLASSIFICATION` 코드를 정규화 기준으로 사용. `foreign_code_attribute`의 `display_name`과 `name`을 동의어로 활용
- v11.1: 자유 텍스트 직무명(work_fields 등)은 **코드 정규화를 강제하지 않고 임베딩 유사도로 비교**한다 (1.5절 Tier 3 참조). code-hub 코드가 있는 경우(job_classification_codes)만 코드 기반 매칭 사용

### 1.3 스킬 코드 → Skill 노드

| code-hub Enum | 온톨로지 매핑 대상 | 용도 |
|---|---|---|
| `HARD_SKILL` | `Skill` (category: code-hub 속성 참조) | 기술 스킬 (Python, React 등) |
| `SOFT_SKILL` | `Skill` (category: "soft") | 소프트 스킬 |

**스킬 정규화** [v11.1 개정: 경량 정규화 + 임베딩 fallback]:

v11.1에서는 코드 정규화를 **최소한으로만** 수행한다. code-hub에 정확히 매칭되는 상위 스킬(Java, Python, React 등)만 코드로 정규화하고, 매칭 실패 시 임베딩 유사도로 비교한다 (4.3절 참조). fuzzy 매칭, 한영 사전 등의 복잡한 정규화는 **ROI가 낮아 적용하지 않는다**.

> **정규화하지 않는 이유**: 스킬 표현은 무한히 다양하고(사내 도구, 신기술, 도메인 특화 기술), 매칭에서 차별화를 만드는 것은 롱테일 스킬이다. 롱테일까지 코드 정규화를 시도하면 유지보수 비용만 높고 커버리지는 낮다.

```python
def normalize_skill(raw_skill_name, site_type="JOBKOREA"):
    """
    이력서/공고의 원본 스킬명을 code-hub 기준으로 경량 정규화한다.

    v11.1 전략:
    - 정확 매칭(CI) + synonyms 매칭만 수행 (2단계)
    - 미매칭 시 원본 유지 → 비교는 임베딩 유사도로 수행 (4.3절)
    - fuzzy 매칭, 한영 사전 등 복잡한 정규화는 적용하지 않음
    """
    cleaned = raw_skill_name.strip()
    if not cleaned:
        return {"skill_id": None, "name": "", "normalized": False}

    # 1. code-hub 정확 매칭 (case-insensitive)
    match = lookup_foreign_code_attribute(
        site_type=site_type, type="HARD_SKILL", name=cleaned
    )
    if not match:
        # 소문자로 재시도
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

### 1.5 비정형 값 비교 전략 [v11.1 신규]

DB 컬럼의 값이 표준화되어 있지 않음을 전제로, **대상의 특성에 따라 비교 전략을 분리**한다. 모든 항목을 코드 정규화하려는 접근은 ROI가 낮으므로, 정규화가 효과적인 대상에만 적용하고 나머지는 임베딩 유사도로 비교한다.

#### 3-Tier 비교 전략

| Tier | 대상 | 비교 방법 | 근거 |
|---|---|---|---|
| **Tier 1: 정규화 적합** | 대학교명, 회사명, 산업 코드 | code-hub Lookup (CI 매칭) | 유한 집합, 명확한 정체성, 오매칭 위험 낮음 |
| **Tier 2: 경량 정규화 + 임베딩** | 상위 스킬 (Java, Python 등) | code-hub CI 매칭 시도 → 미매칭 시 임베딩 | 상위 50~100개는 CI 매칭 가능, 롱테일은 임베딩 |
| **Tier 3: 임베딩 전용** | 전공, 직무명(자유 텍스트), 롱테일 스킬 | 임베딩 cosine similarity | 표현 다양성 높음, 정규화 시 거짓 동일성 위험 |

#### Tier별 근거

**Tier 1 (정규화 적합)** — 대학교, 회사명:
- "서울대학교", "서울대", "SNU" → 동일 기관임이 명확. 유한 집합이라 사전 구축 가능
- 오매칭 위험이 거의 없음 (동명이인 기관이 드물다)

**Tier 2 (경량 정규화 + 임베딩)** — 스킬:
- "Java/JAVA/java" → 상위 스킬은 CI 매칭으로 충분
- "사내 MLOps 도구", "커스텀 프레임워크" → code-hub에 없으므로 임베딩으로 비교
- 1.3절 `normalize_skill()`은 CI + synonyms 2단계만 수행하고, 미매칭은 임베딩에 위임

**Tier 3 (임베딩 전용)** — 전공, 직무명:
- "컴퓨터공학" vs "컴퓨터과학" → **다른 전공**인데 정규화하면 동일 처리되는 위험
- "정보통신공학", "전자공학", "전기전자공학" → 유사하지만 실제로 다름
- 정규화 = "같은 것인가?" (이진 판단, 오류 시 치명적)
- 임베딩 = "얼마나 비슷한가?" (연속 점수, 오류에 관대)

#### 임베딩 비교 구현

```python
def compute_embedding_similarity(text_a, text_b):
    """
    두 텍스트 간 임베딩 cosine similarity를 계산한다.
    임베딩 모델: text-multilingual-embedding-002 (04_graph_schema와 동일)

    용도: Tier 2 미매칭 스킬, Tier 3 전공/직무명 비교
    """
    emb_a = embed_text(text_a)  # 1536d vector
    emb_b = embed_text(text_b)
    return cosine_similarity(emb_a, emb_b)


def compute_embedding_similarity_batch(texts_a, texts_b, threshold=0.80):
    """
    두 텍스트 집합 간 임베딩 유사도를 계산하고 threshold 이상인 쌍을 반환한다.

    Args:
        texts_a: 비교 대상 A (예: 공고의 스킬 목록)
        texts_b: 비교 대상 B (예: 후보의 스킬 목록)
        threshold: 유사도 하한 (0~1)

    Returns:
        매칭된 쌍 리스트: [{"a": str, "b": str, "similarity": float}, ...]
    """
    if not texts_a or not texts_b:
        return []

    embeddings_a = batch_embed(texts_a)
    embeddings_b = batch_embed(texts_b)

    matches = []
    for i, emb_a in enumerate(embeddings_a):
        best_sim = 0.0
        best_j = -1
        for j, emb_b in enumerate(embeddings_b):
            sim = cosine_similarity(emb_a, emb_b)
            if sim > best_sim:
                best_sim = sim
                best_j = j
        if best_sim >= threshold:
            matches.append({
                "a": texts_a[i],
                "b": texts_b[best_j],
                "similarity": best_sim,
            })

    return matches
```

#### Tier 3 적용 예시: 전공 비교

```python
def compare_majors(vacancy_preferred_majors, candidate_majors):
    """
    전공은 정규화하지 않고 임베딩 유사도로 비교한다.

    "컴퓨터공학" vs "컴퓨터과학" → similarity 0.92 (높지만 1.0이 아님)
    "컴퓨터공학" vs "경영학" → similarity 0.35 (낮음)
    "전자공학" vs "전기전자공학" → similarity 0.95 (매우 높음)

    이진 동일성 판단 대신 연속 점수를 반환하여,
    다운스트림에서 threshold를 조정할 수 있게 한다.
    """
    if not vacancy_preferred_majors or not candidate_majors:
        return {"score": None, "matches": []}

    matches = compute_embedding_similarity_batch(
        vacancy_preferred_majors,
        candidate_majors,
        threshold=0.75  # 전공은 의미적 유사성이 넓으므로 낮은 threshold
    )

    # 최고 유사도를 점수로 사용
    best_score = max([m["similarity"] for m in matches], default=0.0)

    return {
        "score": best_score,
        "matches": matches,
    }
```

### 1.7 기타 코드 매핑

| code-hub Enum | 온톨로지 활용 | 비고 |
|---|---|---|
| `POSITION_GRADE` | `vacancy.seniority` 추정 보조 | 직급 코드 → seniority 매핑 테이블 필요 |
| `POSITION_TITLE` | `Experience.scope_type` 추정 보조 | 직책 코드 → scope_type 매핑 |
| `BENEFIT` | `operating_model.facets` 보조 신호 | 복리후생 → 운영 방식 힌트 |
| `EDUCATION_LEVEL` | `requirement.education_code` | 학력 요건 매핑 |
| `AREA_CODE` | `work_condition.location` | 근무지 정보 |
| `LICENSE` | CandidateContext 확장 (v2) | 자격증 매칭 |

---

## 2. job-hub → CompanyContext 매핑

job-hub의 공고 데이터가 CompanyContext의 각 필드에 어떻게 매핑되는지 정의한다.

### 2.1 ID 매핑

| 온톨로지 필드 | job-hub 소스 | 비고 |
|---|---|---|
| `company_id` | `job.user_ref_key` 또는 `job.workspace_id` | 기업 식별자. 동일 기업의 복수 공고를 묶는 키 |
| `job_id` | `job.id` | 공고 식별자 |
| `company_name` | `work_condition.company_name` | 근무 기업명 |

### 2.2 company_profile 매핑

| 온톨로지 필드 | job-hub 소스 | 추출 방법 | v10 대비 변경 |
|---|---|---|---|
| `industry_code` | `overview.industry_codes[0]` | Lookup (code-hub) | **v11**: code-hub INDUSTRY 코드 직접 사용 (v10: NICE만) |
| `industry_label` | code-hub에서 코드명 조회 | Lookup | code-hub `detail_name` |
| `is_regulated_industry` | `overview.industry_codes[0]` → code-hub 대분류 | Rule | v10 로직 유지, 코드 소스만 변경 |

### 2.3 vacancy 매핑

| 온톨로지 필드 | job-hub 소스 | 추출 방법 | 비고 |
|---|---|---|---|
| `role_title` | `overview.work_fields[]` + `overview.job_classification_codes[]` | Rule + Lookup | work_fields는 자유 텍스트, job_classification_codes는 정규화 코드 |
| `seniority` | `overview.designation_codes[]` | Rule (매핑 테이블) | code-hub POSITION_GRADE → seniority 변환 |
| `scope_type` | `overview.descriptions` (JSONB) | LLM | 비구조화 텍스트에서 추출 |
| `scope_description` | `overview.descriptions` (JSONB) | LLM | 비구조화 텍스트에서 추출 |
| `team_context` | `overview.descriptions` (JSONB) | LLM | 비구조화 텍스트에서 추출 |
| `tech_stack` | `skill` 테이블 (type=HARD) | Lookup (code-hub) | **v11 신규**: 구조화된 스킬 데이터 직접 사용 |

**designation_codes → seniority 매핑 테이블** [v11 신규]:

```python
# code-hub POSITION_GRADE 코드 → seniority 매핑
# 실제 코드값은 code-hub 데이터 확인 후 확정 필요
DESIGNATION_TO_SENIORITY = {
    # code-hub POSITION_GRADE 코드: seniority enum
    # 예시 (실제 코드값 확인 필요)
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
    """
    공고의 직급/직책 코드에서 seniority를 추론한다.

    Args:
        designation_codes: job-hub overview.designation_codes (VARCHAR[])
    Returns:
        seniority enum 또는 None
    """
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
| `preferred` | `requirement.preference_codes[]` | Lookup (code-hub PREFERRED) | **v11 신규**: 구조화된 우대조건 코드 직접 사용 |
| `tech_stack` | `skill` 테이블 (type=HARD, job_id 기준) | Lookup | **v11 신규**: code-hub HARD_SKILL 코드 직접 사용 |

**tech_stack 추출 우선순위** [v11 신규]:
```python
def extract_tech_stack(job_id, jd_text):
    """
    기술 스택 추출: 구조화 데이터 우선, LLM 보강.

    1순위: job-hub skill 테이블 (type=HARD) → code-hub 정규화
    2순위: JD 텍스트에서 LLM 추출 → code-hub 매칭 시도
    """
    # 1순위: 구조화된 스킬 데이터
    structured_skills = query_job_skills(job_id, type="HARD")
    normalized = [normalize_skill(s.code) for s in structured_skills]

    # 2순위: JD 텍스트에서 추가 스킬 추출 (1순위에 없는 것만)
    existing_names = {s["name"].lower() for s in normalized}
    llm_skills = llm_extract_tech_stack(jd_text)
    for skill_name in llm_skills:
        if skill_name.lower() not in existing_names:
            norm = normalize_skill(skill_name)
            normalized.append(norm)

    return normalized
```

### 2.5 operating_model facets 매핑 보강

| 온톨로지 facet | job-hub 보조 소스 | 추출 방법 | 비고 |
|---|---|---|---|
| `speed` | `overview.recruitment_option_types[]` | Rule | 예: 즉시 채용 → 빠른 조직 시그널 |
| `autonomy` | `work_condition.work_schedule_option_types[]` | Rule | FLEXIBLE_WORK → 자율 시그널 |
| `process` | `overview.descriptions` (JSONB) | LLM | 기존 유지 |

**구조화 시그널 보강** [v11 신규]:
```python
def extract_structured_facet_signals(job):
    """
    job-hub의 구조화된 필드에서 operating_model facet 시그널을 추출한다.
    JD 텍스트 LLM 추출 이전에 먼저 적용되는 기초 시그널이다.
    """
    signals = {"speed": [], "autonomy": [], "process": []}

    # speed 시그널
    if job.overview.always_hire:
        signals["speed"].append("상시채용 (빠른 채용 프로세스 시사)")
    if job.overview.close_on_hire:
        signals["speed"].append("채용시마감 (긴급 충원 시사)")

    # autonomy 시그널
    wc = job.work_condition
    if wc and wc.work_schedule_option_types:
        schedule_opts = set(wc.work_schedule_option_types)
        if "FLEXIBLE_WORK" in schedule_opts:
            signals["autonomy"].append("유연근무 가능")
        if "WORK_HOURS_NEGOTIABLE" in schedule_opts:
            signals["autonomy"].append("근무시간 협의 가능")

    # recruitment options에서 추가 시그널
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
| `candidate_id` | `SiteUserMapping.id` | 사용자 매핑 ID (잡코리아/알바몬 통합) |
| `resume_id` | `Resume.id` | 이력서 식별자 |

### 3.2 Experience 매핑

| 온톨로지 필드 | resume-hub 소스 | 추출 방법 | v10 대비 변경 |
|---|---|---|---|
| `company` | `Career.companyName` | Lookup | 직접 매핑 |
| `role_title` | `Career.jobClassificationCodes[]` + `Career.positionTitleCode` | Lookup (code-hub) | **v11**: code-hub 코드 기반 정규화 |
| `period.start` | `Career.period.period` (DATERANGE 시작) | Rule | PostgreSQL DATERANGE → YYYY-MM 변환 |
| `period.end` | `Career.period.period` (DATERANGE 끝) 또는 `employmentStatus=EMPLOYED` | Rule | EMPLOYED이면 "present" |
| `period.duration_months` | `Career.period.daysWorked` | 계산 | `daysWorked / 30` |
| `tech_stack` | `Skill` 테이블 (type=HARD, resume_id 기준) | Lookup (code-hub) | **v11**: 구조화된 스킬 직접 사용 |
| `scope_type` | `Career.positionGradeCode` + `Career.positionTitleCode` | Rule + LLM | **v11**: 구조화 코드로 1차 추정, LLM 보정 |
| `scope_summary` | `Career.workDetails` | LLM | 근무 상세 내용에서 추출 |
| `outcomes` | `Career.workDetails` | LLM | 근무 상세 내용에서 추출 |
| `situational_signals` | `Career.workDetails` + 구조화 메타 | LLM + Rule | 아래 상세 참조 |

**scope_type 구조화 추정** [v11 신규]:
```python
# code-hub POSITION_TITLE / POSITION_GRADE → scope_type 매핑
POSITION_TO_SCOPE = {
    # POSITION_TITLE (직책) 기반
    "사원": "IC",
    "대리": "IC",
    "과장": "IC",     # 한국 기업에서 과장은 보통 IC
    "차장": "IC",     # 상황에 따라 LEAD일 수 있으나 기본 IC
    "팀장": "LEAD",
    "파트장": "LEAD",
    "실장": "LEAD",
    "이사": "HEAD",
    "상무": "HEAD",
    "부사장": "HEAD",
    "대표": "FOUNDER",
    "CEO": "FOUNDER",
    "CTO": "HEAD",
}

def estimate_scope_type(career):
    """
    resume-hub Career 레코드에서 scope_type을 추정한다.

    1순위: positionTitleCode → code-hub 조회 → 매핑
    2순위: positionGradeCode → code-hub 조회 → 매핑
    3순위: workDetails에서 LLM 추출
    """
    # 1순위: 직책 코드
    if career.positionTitleCode:
        title_detail = lookup_common_code(
            type="POSITION_TITLE", code=career.positionTitleCode
        )
        if title_detail and title_detail.detail_name in POSITION_TO_SCOPE:
            return POSITION_TO_SCOPE[title_detail.detail_name], 0.75  # 구조화 confidence

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

| 온톨로지 필드 | resume-hub 소스 | 추출 방법 | 비고 |
|---|---|---|---|
| `role_evolution` | `Career[]` (전체 경력 시퀀스) | Rule + LLM | scope_type 시퀀스로 패턴 판단 |
| `domain_depth` | `Career[].jobClassificationCodes[]` + `WorkCondition.workJobField` | Rule | **v11**: 직무 코드 반복 패턴 분석 |
| `work_style_signals` | `SelfIntroduction.description` + `Career.workDetails` | LLM | 자기소개서가 주 소스 |

**domain_depth 구조화 추출** [v11 신규]:
```python
def extract_domain_depth_structured(resume):
    """
    resume-hub의 구조화된 직무/산업 코드로 domain_depth를 추출한다.

    LLM 추출 이전에 구조화 데이터로 기초 분석을 수행한다.
    """
    # 1. 전체 경력의 산업 코드 수집
    industry_codes = []
    for career in resume.careers:
        if career.jobClassificationCodes:
            industry_codes.extend(career.jobClassificationCodes)

    # 2. 희망 근무 조건의 산업/직무 코드
    if resume.workCondition and resume.workCondition.workJobField:
        wjf = resume.workCondition.workJobField
        if wjf.industryCodes:
            industry_codes.extend(wjf.industryCodes)

    # 3. 가장 빈번한 코드 = primary domain
    if not industry_codes:
        return None

    from collections import Counter
    code_counts = Counter(industry_codes)
    primary_code, count = code_counts.most_common(1)[0]

    # code-hub에서 라벨 조회
    code_detail = lookup_common_code(
        type="JOB_CLASSIFICATION_SUBCATEGORY", code=primary_code
    )

    return {
        "primary_domain": code_detail.sub_name if code_detail else primary_code,
        "domain_experience_count": count,
        "confidence": min(0.80, 0.50 + count * 0.10),  # 구조화 데이터이므로 높은 confidence
    }
```

### 3.4 PastCompanyContext 보강

| 온톨로지 필드 | resume-hub 소스 | 비고 |
|---|---|---|
| `company_name` | `Career.companyName` | 직접 매핑 |
| `industry_code` | `Career.companyName` → job-hub 역조회 | **v11**: 동일 회사의 공고에서 industry_code 역참조 |

**동일 회사 공고 역참조** [v11 신규]:
```python
def enrich_past_company_from_jobhub(company_name):
    """
    후보의 이전 회사명으로 job-hub에서 해당 회사의 공고를 찾아
    산업 코드, 규모 등 구조화 정보를 역참조한다.

    NICE 조회 이전에 먼저 시도하여 code-hub 기준 정규화된 코드를 얻는다.
    """
    # job-hub에서 동일 회사명의 공고 검색
    jobs = query_jobs_by_company_name(company_name)
    if not jobs:
        return None  # NICE fallback

    # 가장 최근 공고에서 산업 코드 추출
    latest_job = max(jobs, key=lambda j: j.created_at)
    industry_codes = latest_job.overview.industry_codes

    return {
        "industry_code": industry_codes[0] if industry_codes else None,
        "source": "job_hub_reverse_lookup",
        "confidence": 0.75,  # 동일 회사 공고이므로 비교적 높은 신뢰도
    }
```

---

## 4. 구조화 코드 기반 매칭 강화 (MappingFeatures 보강)

### 4.1 F3 domain_fit: 산업 코드 직접 매칭

v10에서는 임베딩 유사도 + industry_code 보조 매칭이었으나, v11에서는 code-hub 기반 **계층적 코드 매칭**을 추가한다.

```python
def compute_industry_code_match(company_industry_codes, candidate_career_codes):
    """
    code-hub 산업 코드의 계층 구조를 활용한 매칭.

    3depth 일치: 0.25 보너스 (소분류 일치)
    2depth 일치: 0.15 보너스 (중분류 일치)
    1depth 일치: 0.05 보너스 (대분류 일치)

    code-hub의 group_code(1d), sub_code(2d), detail_code(3d) 계층을 사용한다.
    """
    best_bonus = 0.0

    for c_code in company_industry_codes:
        company_detail = lookup_common_code(type="INDUSTRY", code=c_code)
        if not company_detail:
            continue

        for r_code in candidate_career_codes:
            career_detail = lookup_common_code(
                type="JOB_CLASSIFICATION_SUBCATEGORY", code=r_code
            )
            if not career_detail:
                continue

            # 소분류 일치 (가장 정확)
            if c_code == r_code:
                best_bonus = max(best_bonus, 0.25)
            # 중분류 일치
            elif (company_detail.group_code == career_detail.group_code and
                  company_detail.sub_code == career_detail.sub_code):
                best_bonus = max(best_bonus, 0.15)
            # 대분류 일치
            elif company_detail.group_code == career_detail.group_code:
                best_bonus = max(best_bonus, 0.05)

    return best_bonus
```

### 4.2 F5 role_fit: 직무 코드 매칭

v10에서는 seniority 패턴만으로 role_fit을 계산했으나, v11에서는 **직무 코드 일치도**를 추가한다.

```python
def compute_job_classification_match(vacancy_job_codes, candidate_career_codes):
    """
    공고의 직무 코드(JOB_CLASSIFICATION)와 후보 경력의 직무 코드를 비교한다.

    3depth 일치: 0.15 보너스
    2depth 일치: 0.08 보너스
    """
    best_bonus = 0.0

    for v_code in vacancy_job_codes:
        v_detail = lookup_common_code(type="JOB_CLASSIFICATION", code=v_code)
        if not v_detail:
            continue

        for c_code in candidate_career_codes:
            c_detail = lookup_common_code(
                type="JOB_CLASSIFICATION", code=c_code
            )
            if not c_detail:
                continue

            if v_code == c_code:
                best_bonus = max(best_bonus, 0.15)
            elif (v_detail.group_code == c_detail.group_code and
                  v_detail.sub_code == c_detail.sub_code):
                best_bonus = max(best_bonus, 0.08)

    return best_bonus
```

### 4.3 스킬 매칭 (F6 신규 후보 — v2 검토)

v11에서는 code-hub의 HARD_SKILL 코드를 활용한 **구조화 스킬 매칭**의 설계를 준비한다. v1에서는 tech_stack 비교가 role_expectations의 일부로만 동작했으나, v2에서 독립 피처로 검토한다.

**[v11.1]** 비정형 스킬 값을 전제로, **코드 매칭 + 임베딩 유사도 하이브리드** 방식을 적용한다. 경량 정규화(1.3절)로 매칭된 스킬은 코드 기반으로 비교하고, 미매칭 스킬은 임베딩 유사도(1.5절)로 비교한다.

```python
def compute_skill_overlap(vacancy_skills_raw, candidate_skills_raw, site_type="JOBKOREA"):
    """
    [v2 검토용] 공고 요구 스킬과 후보 보유 스킬의 하이브리드 매칭.

    v11.1 전략:
    1. 경량 정규화(CI + synonyms)로 코드 매칭 시도
    2. 코드 매칭 성공한 스킬 → skill_id 기준 집합 비교
    3. 코드 매칭 실패한 스킬 → 임베딩 유사도로 비교 (1.5절 Tier 2)

    두 결과를 가중 합산하여 최종 score를 산출한다.
    """
    # 경량 정규화 시도
    v_normalized = [normalize_skill(s, site_type) for s in vacancy_skills_raw]
    c_normalized = [normalize_skill(s, site_type) for s in candidate_skills_raw]

    # 코드 매칭 성공 스킬
    v_coded = {s["skill_id"] for s in v_normalized if s["normalized"]}
    c_coded = {s["skill_id"] for s in c_normalized if s["normalized"]}

    # 코드 미매칭 스킬 (원본 텍스트)
    v_uncoded = [s["name"] for s in v_normalized if not s["normalized"]]
    c_uncoded = [s["name"] for s in c_normalized if not s["normalized"]]

    if not v_coded and not v_uncoded:
        return None  # 공고에 스킬 정보 없음

    # (1) 코드 매칭 결과
    code_intersection = v_coded & c_coded
    code_coverage = len(code_intersection) / len(v_coded) if v_coded else 0.0

    # (2) 임베딩 매칭 결과 (미매칭 스킬만)
    embedding_matches = compute_embedding_similarity_batch(
        v_uncoded, c_uncoded, threshold=0.85
    ) if v_uncoded and c_uncoded else []

    embedding_coverage = len(embedding_matches) / len(v_uncoded) if v_uncoded else 0.0

    # (3) 가중 합산: 코드 매칭(가중치 1.0) + 임베딩 매칭(가중치 0.8)
    total_vacancy = len(v_coded) + len(v_uncoded)
    weighted_matches = len(code_intersection) * 1.0 + len(embedding_matches) * 0.8
    overall_coverage = weighted_matches / total_vacancy if total_vacancy else 0.0

    return {
        "overall_coverage": min(1.0, overall_coverage),
        "code_match": {
            "matched": list(code_intersection),
            "coverage": code_coverage,
        },
        "embedding_match": {
            "matched": embedding_matches,
            "coverage": embedding_coverage,
        },
        "unmatched_vacancy_skills": list(
            (v_coded - c_coded) | set(s for s in v_uncoded if s not in [m["a"] for m in embedding_matches])
        ),
    }
```

---

## 5. 추출 파이프라인 변경 (v10 → v11)

### 5.1 CompanyContext 추출 파이프라인

```
[job-hub DB]
    │
    ├─[1] 구조화 데이터 조회 (Rule-based)
    │   ├─ job.id, work_condition.company_name → company_id, company_name
    │   ├─ overview.industry_codes → industry_code (code-hub Lookup)
    │   ├─ overview.designation_codes → seniority (매핑 테이블)
    │   ├─ overview.job_classification_codes → role_title (code-hub Lookup)
    │   ├─ skill 테이블 (type=HARD) → tech_stack (code-hub 정규화)
    │   ├─ requirement → 자격요건 구조화 필드
    │   ├─ work_condition → 근무조건 구조화 필드
    │   └─ overview.recruitment_option_types → facet 보조 시그널
    │
    ├─[1.5] 비정형 값 비교 준비 (v11.1) ────────────────────────
    │   ├─ skill 테이블 원본 값 → normalize_skill() → 경량 정규화 (CI + synonyms)
    │   ├─ 정규화 성공 → code-hub skill_id 기반 비교
    │   ├─ 정규화 실패 → 원본 유지, 임베딩 벡터 생성 (4.3절에서 비교)
    │   └─ work_fields (자유 텍스트 직무명) → 정규화 시도하지 않음, 임베딩으로 비교
    │
    ├─[2] NICE 데이터 조회 (보조)
    │   ├─ company_name → NICE 매칭
    │   └─ 직원수, 매출, 설립연도 등
    │
    ├─[3] LLM 추출 (비구조화 텍스트만)
    │   ├─ overview.descriptions (JSONB) → scope_type, scope_description, team_context
    │   ├─ overview.descriptions (JSONB) → responsibilities (구조화 미제공 항목)
    │   └─ overview.descriptions (JSONB) → operating_model facets (키워드 + LLM)
    │
    └─[4] 교차 검증
        ├─ code-hub industry_code vs NICE industry_code
        └─ 구조화 tech_stack vs LLM 추출 tech_stack
```

### 5.2 CandidateContext 추출 파이프라인

```
[resume-hub DB]
    │
    ├─[1] 구조화 데이터 조회 (Rule-based)
    │   ├─ SiteUserMapping.id → candidate_id
    │   ├─ Resume.id → resume_id
    │   ├─ Career[] → company, period (DATERANGE 변환)
    │   ├─ Career.positionTitleCode/positionGradeCode → scope_type 1차 추정
    │   ├─ Career.jobClassificationCodes → role_title (code-hub Lookup)
    │   ├─ Skill[] (type=HARD) → tech_stack (code-hub 정규화)
    │   ├─ Career[].jobClassificationCodes 반복 분석 → domain_depth 기초
    │   └─ Education[] → 학력 정보
    │
    ├─[1.5] 비정형 값 비교 준비 (v11.1) ────────────────────────
    │   ├─ Skill 테이블 원본 값 → normalize_skill() → 경량 정규화 (CI + synonyms)
    │   ├─ 정규화 성공 → code-hub skill_id 기반 비교
    │   ├─ 정규화 실패 → 원본 유지, 임베딩 벡터 생성 (4.3절에서 비교)
    │   └─ 전공/직무명 자유 텍스트 → 정규화 시도하지 않음, 임베딩으로 비교
    │
    ├─[2] LLM 추출 (비구조화 텍스트만, Experience별)
    │   ├─ Career.workDetails → scope_summary, outcomes, situational_signals
    │   ├─ Career.workDetails → scope_type 보정 (구조화 결과 교차 검증)
    │   └─ Career.workDetails → failure_recovery (있을 때만)
    │
    ├─[3] LLM 추출 (전체 커리어)
    │   ├─ CareerDescription.description → role_evolution 보강
    │   ├─ SelfIntroduction[] → work_style_signals
    │   └─ Career[] 전체 → domain_depth (구조화 결과와 LLM 결과 병합)
    │
    ├─[4] NICE Lookup (회사명 기반)
    │   └─ job-hub 역참조 → NICE Lookup (순차)
    │
    └─[5] 교차 검증
        ├─ 구조화 scope_type vs LLM scope_type
        └─ 구조화 tech_stack vs LLM tech_stack
```

---

## 6. 데이터 품질 및 coverage 예측

### 6.1 job-hub 필드 가용성

| 온톨로지 필드 | job-hub 소스 필드 | 예상 fill rate | 비고 |
|---|---|---|---|
| industry_code | overview.industry_codes | 90%+ | 대부분 공고에 산업 코드 존재 |
| job_classification | overview.job_classification_codes | 85%+ | 직무 분류 코드 |
| tech_stack (구조화) | skill 테이블 | 60~70% | 일부 공고는 스킬 미입력 |
| designation_codes | overview.designation_codes | 40~50% | 직급 정보 선택 입력 |
| descriptions (JD 본문) | overview.descriptions (JSONB) | 95%+ | 거의 모든 공고에 존재 |
| employment_types | overview.employment_types | 90%+ | 고용 형태 |
| work_schedule_options | work_condition.work_schedule_option_types | 50~60% | 선택 입력 |

### 6.2 resume-hub 필드 가용성

| 온톨로지 필드 | resume-hub 소스 필드 | 예상 fill rate | 비고 |
|---|---|---|---|
| company | Career.companyName | 95%+ | 거의 모든 경력에 존재 |
| period | Career.period | 90%+ | 대부분 입력 |
| positionTitleCode | Career.positionTitleCode | 30~40% | 선택 입력, 낮은 fill rate |
| positionGradeCode | Career.positionGradeCode | 35~45% | 선택 입력 |
| jobClassificationCodes | Career.jobClassificationCodes | 50~60% | 직무 코드 |
| workDetails | Career.workDetails | 60~70% | 경력직은 높음, 신입은 낮음 |
| Skill (HARD) | Skill 테이블 | 55~65% | 선택 입력 |
| SelfIntroduction | SelfIntroduction 테이블 | 40~50% | 선택 입력 |

### 6.3 Graceful Degradation 전략

구조화 데이터의 fill rate가 100%가 아니므로, 누락 시 fallback 전략을 정의한다:

| 구조화 데이터 | 누락 시 fallback | confidence 영향 |
|---|---|---|
| industry_codes | NICE industry_code 사용 | confidence 유지 (v10 동일 수준) |
| designation_codes | JD 텍스트에서 LLM 추출 | confidence -0.10 (v10 동일) |
| skill 테이블 | JD/이력서 텍스트에서 LLM 추출 | confidence -0.05 |
| positionTitleCode | workDetails에서 LLM 추출 | confidence -0.15 |
| jobClassificationCodes | 임베딩 유사도 fallback (v10 동일) | confidence -0.10 |

### 6.4 비정형 값 비교 품질 모니터링 [v11.1 신규]

스킬/전공/직무명의 비정형 값 비교(1.5절) 품질을 추적한다.

#### 모니터링 지표

| 지표 | 산식 | 목표치 | 비고 |
|---|---|---|---|
| **스킬 코드 매칭률** | 경량 정규화 성공 건 / 전체 스킬 건 | 참고용 (목표치 없음) | 상위 스킬 커버리지 확인용. 낮아도 임베딩이 보완 |
| **임베딩 매칭 커버리지** | 임베딩 매칭 성공 건 / 코드 미매칭 건 | >= 70% | 임베딩 모델의 스킬명 이해도 지표 |
| **임베딩 매칭 정확도** | human eval 샘플 10건 정확률 | >= 85% | 월간 샘플링 검증 |
| **전공/직무 임베딩 유사도 분포** | 매칭 쌍의 similarity 분포 | 중앙값 >= 0.80 | threshold 조정 근거 |

#### 비교 방법별 신뢰도

| 비교 방법 | confidence | 적용 대상 |
|---|---|---|
| code-hub 코드 매칭 (CI) | 0.95 | Tier 1 (대학교, 회사명), Tier 2 상위 스킬 |
| code-hub synonyms 매칭 | 0.85 | Tier 2 상위 스킬 |
| 임베딩 유사도 (>= 0.90) | 0.80 | Tier 2 미매칭 스킬, Tier 3 전공/직무 |
| 임베딩 유사도 (0.80~0.90) | 0.70 | Tier 2/3 경계 영역 |
| 임베딩 유사도 (0.75~0.80) | 0.60 | Tier 3 전공 (넓은 의미적 유사성) |
| 미매칭 (threshold 미달) | 0.0 | 매칭에서 제외 |

---

## 7. v10 → v11 마이그레이션 영향

### 7.1 변경 없는 항목

- Evidence 통합 모델 (source_type enum 유지)
- confidence 캘리브레이션 기준
- structural_tensions taxonomy (8개)
- STAGE_SIMILARITY 매트릭스
- 크롤링 전략 (06_crawling_strategy.md) — 크롤링은 외부 소스이므로 내부 DB 매핑과 무관

### 7.2 변경 항목 요약

| 문서 | 변경 내용 |
|---|---|
| 01_company_context | industry_code 소스 변경 (NICE → code-hub primary), tech_stack 구조화 추출 추가, seniority 구조화 추정 추가 |
| 02_candidate_context | scope_type 구조화 추정 추가, tech_stack/role_title code-hub 정규화, domain_depth 구조화 추출 추가, PastCompanyContext job-hub 역참조 |
| 03_mapping_features | F3 domain_fit에 계층적 코드 매칭 추가, F5 role_fit에 직무 코드 매칭 추가, F6 skill_match 준비 |
| 04_graph_schema | Industry 노드를 code-hub INDUSTRY 코드 기준으로 재정의, Skill 노드를 code-hub HARD_SKILL 기준 정규화, Role 노드를 code-hub JOB_CLASSIFICATION 기준 정규화 |
| 05_evaluation_strategy | 변경 없음 |
| 06_crawling_strategy | 변경 없음 |
| 00_data_source_mapping | **[v11.1] 비정형 값 비교 3-Tier 전략(1.5절) 신규, normalize_skill 경량화, compute_skill_overlap 임베딩 하이브리드 전환, 비교 품질 모니터링(6.4절) 추가** |
