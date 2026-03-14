> 작성일: 2026-03-13
> 01.ontology/results/schema/v25/00_data_source_mapping.md §1.3, §1.5, §1.7, §1.8, §4, §7에서 이동.
> 정규화/코드 매칭 관련 구현 로직을 추출 영역으로 분리.

---

## 1. 비정형 값 비교 전략

DB 컬럼의 값이 표준화되어 있지 않음을 전제로, **대상의 특성에 따라 비교 전략 분리**

### 3-Tier 비교 전략 (팀 논의 내용 포함)

| Tier | 대상 | 비교 방법 | 근거 |
| --- | --- | --- | --- |
| **Tier 1: 정규화 적합** | 대학교명, 회사명, 산업 코드 | code-hub Lookup (CI 매칭) | 유한 집합, 명확한 정체성, 오매칭 위험 낮음 |
| **Tier 2: 경량 정규화 + 임베딩** | 상위 스킬 (Java, Python 등) | code-hub CI 매칭 시도 -> 미매칭 시 임베딩 | 상위 50~100개는 CI 매칭 가능, 롱테일은 임베딩 |
| **Tier 3: 임베딩 전용** | 전공(47,163 고유값), 직무명(자유 텍스트), 롱테일 스킬 | 임베딩 cosine similarity | 표현 다양성 높음, 정규화 시 거짓 동일성 위험 |

### 비교 방법 별 Confidence 보정 테이블

| 비교 방법 | Confidence | 적용 대상 |
| --- | --- | --- |
| code-hub 코드 매칭 (CI) | 0.95 | Tier 1 (대학교, 회사명), Tier 2 상위 스킬 |
| code-hub synonyms 매칭 | 0.85 | Tier 2 상위 스킬 |
| 임베딩 유사도 (> 0.90) | 0.80 | Tier 2 미매칭 스킬, Tier 3 전공/직무 |
| 임베딩 유사도 (0.80~0.90) | 0.70 | Tier 2/3 경계 영역 |
| 임베딩 유사도 (0.75~0.80) | 0.60 | Tier 3 전공 (넓은 의미적 유사성) |
| 미매칭 (threshold 미달) | 0.0 | 매칭에서 제외 |

### 임베딩 비교 구현 (현재는 코사인 유사도 기반)

```python
def compute_embedding_similarity(text_a, text_b):
    """
    두 텍스트 간 임베딩 cosine similarity를 계산한다.
    임베딩 모델: text-embedding-005 (768d, Vertex AI) - 02_model_and_infrastructure.md §2.1과 동일
    """
    emb_a = embed_text(text_a)  # 768d vector
    emb_b = embed_text(text_b)
    return cosine_similarity(emb_a, emb_b)

def compute_embedding_similarity_batch(texts_a, texts_b, threshold=0.80):
    """
    두 텍스트 집합 간 임베딩 유사도를 계산하고 threshold 이상인 쌍을 반환한다.

    ANN 인덱스(Vertex AI Vector Search 등) 사용
    로직 설명용 pseudo-code이며, 실서비스에서는 ANN 기반 검색

    Returns: [{"a": str, "b": str, "similarity": float}, ...]
    """
    # 1. batch_embed(texts_a), batch_embed(texts_b) 수행
    # 2. 각 text_a에 대해 threshold 이상인 best match를 texts_b에서 탐색
    # 3. ANN 인덱스 사용 시: texts_b를 인덱싱 -> texts_a로 top-1 쿼리
    pass
```

---

## 2. 스킬 정규화

### 스킬 코드 → Skill 노드

| code-hub Enum | 온톨로지 매핑 대상 | 용도 |
| --- | --- | --- |
| `HARD_SKILL` (~2,398개) | `Skill` (category: code-hub 속성) | 기술 스킬 (Python, React 등) |
| `SOFT_SKILL` | `Skill` (category: "soft") | 소프트 스킬 |

**스킬 데이터 실측 현황**:

| 항목 | 값 |
| --- | --- |
| 총 고유 스킬 코드 | **101,925개** |
| codehub 매핑 완료 | **2,398개 (2.4%)** |
| 비표준 코드 | **99,527개 (97.6%)** |
| 이력서 커버리지 | 38.3% (3,074,732 이력서) |
| 이력서 당 평균 스킬 수 | 6.77개 |
| **20개 캡** | 172K 이력서가 정확히 20개 -> 입력 상한(?) |
| SOFT_SKILL 편중 | TOP 10의 60% 차지 - 성실성(25.2%), 긍정적(17.3%) |
- 당연한 이야기지만 스킬 관련 작업하면서 추가된 기능과 관련 (은희님 의견?)

**스킬 정규화** [개정 유지: 경량 정규화 + 임베딩 fallback]:

```python
def normalize_skill(raw_skill_name, site_type="JOBKOREA"):
    """
    이력서/공고의 원본 스킬명을 code-hub 기준으로 경량 정규화한다.

    - 정확 매칭(CI) + synonyms 매칭만 수행 (2단계)
    - 미매칭 시 원본 유지 -> 비교는 임베딩 유사도로 수행 (4.3절)

    codehub synonyms 소스: ForeignCodeAttribute HARD_SKILL (JOBKOREA)의
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

    # 3. 미매칭 -> 원본 유지 (비교는 임베딩으로)
    return {
        "skill_id": None,
        "name": raw_skill_name,
        "normalized": False
    }
```

**스킬 Co-occurrence 클러스터** (정규화 참고):

- Illustrator-Photoshop: Lift 6.79
- Excel-PPT-Word: Lift 4.2x

→ 동일 클러스터 내 스킬은 그룹 노드로 묶는 것을 추후 검토

**스킬 트렌드 (2022-2025)**:

- AI/GenAI: Gemini(7.1x), ChatGPT(5.0x), RAG(4.4x), AI Agent(4.9x)
- 레거시 감소: Servlet(0.65x), Eclipse(0.65x)
- 2022년 이후 이력서당 스킬 수 164% 급증 (스킬 관련 작업 이후 추가)

---

## 3. 기타 코드 매핑

| code-hub Enum | 온톨로지 활용 | 비고 |
| --- | --- | --- |
| `POSITION_GRADE` (15코드) | `vacancy.seniority` 추정 보조 | 직급 코드 -> seniority 매핑 테이블, **fill rate 39.16%** |
| `POSITION_TITLE` (16코드) | `Experience.scope_type` 추정 보조 | 직책 코드 -> scope_type 매핑, **fill rate 29.45%** |
| `BENEFIT` | `operating_model.facets` 보조 신호 | 복리후생 -> 운영 방식 힌트 |
| `EDUCATION_LEVEL` | `requirement.education_code` | 학력 요건 매핑 |
| `AREA_CODE` (5단계 계층) | `work_condition.location` | 근무지 정보 |
| `LICENSE` | CandidateContext 확장 (v2) | **주의: resume-hub `CERTIFICATE` != codehub `LICENSE`** [v12 D5→v18 유지] |
| `LANGUAGE_EXAM` | CandidateContext 확장 (v2) | **주의: resume-hub `LANGUAGE_TEST` != codehub `LANGUAGE_EXAM`** [v12 D5→v18 유지] |
| `DESIGNATION` | Vacancy.seniority 추론 | job-hub `overview.designation_codes` 소스 |

---

## 4. Certificate Type 매핑 변환

resume-hub와 code-hub 간 자격증 타입명 불일치, 변환 없이 codehub 조회 시 매핑 실패.

```python
# 필수 변환 테이블
CERT_TYPE_MAPPING = {
    "CERTIFICATE": "LICENSE",        # resume-hub -> codehub
    "LANGUAGE_TEST": "LANGUAGE_EXAM", # resume-hub -> codehub
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

**규모**: 13,573,606건, 이력서 커버리지 54%, 이력서 당 평균 3.14개

---

## 5. 구조화 코드 기반 매칭 강화 (MappingFeatures 보강)

### 5.1 F3 domain_fit: 산업 코드 직접 매칭

> 데이터 소스 관점의 매핑 정보만 기술

**데이터 소스 매핑**:

| 측 | 데이터 소스 | 코드 타입 | fill rate |
| --- | --- | --- | --- |
| Company | `overview.industry_codes` (job-hub) | INDUSTRY (3depth) | 90%+ (예상) |
| Candidate (1순위) | `workcondition.industryCodes` | INDUSTRY_SUBCATEGORY (2depth) | **34%** (66% 빈배열) |
| Candidate (2순위) | `PastCompanyContext.industry_code` | INDUSTRY (3depth) | job-hub 역참조 (§3.4) |

**비교 전략 요약**:
- 동일 코드 체계(INDUSTRY) 내에서 계층적 비교 (3depth -> 2depth -> 1depth)
- candidate 측이 INDUSTRY_SUBCATEGORY(2depth)인 경우, company INDUSTRY(3depth)를 상위로 올려 비교
- candidate industryCodes 66% 빈배열이므로 PastCompanyContext 역참조(§3.4)를 보조 소스로 활용

### 5.2 F5 role_fit: 직무 코드 매칭

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

### 5.3 스킬 매칭 (코드 매칭 + 임베딩 하이브리드)

```python
def compute_skill_overlap(vacancy_skills_raw, candidate_skills_raw, site_type="JOBKOREA"):
    """
    실측 데이터 반영:
    - 스킬 codehub 매칭률 2.4% -> 대부분 임베딩 비교로 귀결
    - 코드 매칭 가중치 1.0 + 임베딩 매칭 가중치 0.8

    주의: 이력서 스킬 커버리지 38.3%
    SOFT_SKILL 매칭 제외: type=HARD 스킬만 매칭 대상.
    SOFT_SKILL TOP 10의 60%가 "성실성(25.2%), 긍정적(17.3%)"으로 편중되어
    매칭 노이즈를 유발하므로, vacancy/candidate 양쪽 모두 type=HARD만 사용한다.
    SOFT_SKILL은 후보 프로필 표시용으로만 Skill 노드에 저장한다.
    """
    # SOFT_SKILL 제외: type=HARD 스킬만 매칭 대상
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

## 6. 정규화 선행 과제

구현 전 반드시 완료해야 하는 데이터 정제 과제. 난이도 순서가 아닌 **영향 범위** 순서로 정렬.

### 6.1 days_worked 계산 (Critical, 난이도 낮음)

| 항목 | 값 |
| --- | --- |
| 대상 | career 18,709,830건 |
| 현재 상태 | **100% 제로값** |
| 계산 소스 | career.period.period (started_on ~ ended_on) |
| 영향 범위 | Chapter.duration_months, F1 stage_match, F5 role_fit |

### 6.2 Certificate type 매핑 (Critical, 난이도 낮음)

| resume-hub 값 | codehub dict 키 |
| --- | --- |
| `CERTIFICATE` | `LICENSE` |
| `LANGUAGE_TEST` | `LANGUAGE_EXAM` |

### 6.3 회사명 정규화 (난이도 높음)

| 항목 | 값 |
| --- | --- |
| 고유 회사명 수 | **4,479,983개** |
| BRN 입력률 | 62% |
| 다중 표기 사례 | "쿠팡" 관련 3종 = 합산 42,085건 |
| 접근 | BRN 1차 클러스터링(62%) -> 회사명 유사도 2차 보완(38%) |
| 영향 범위 | Organization 노드, Chapter->Org 엣지, F1 stage_match |

### 6.4 스킬 정규화 (난이도 높음)

| 항목 | 값 |
| --- | --- |
| 총 고유 스킬 코드 | 101,925개 |
| codehub 매핑 완료 | 2,398개 (**2.4%**) |
| 접근 | v11.1: 경량 정규화 (CI + 동의어만) -> 실패 시 임베딩 폴백 |
| 영향 범위 | Skill 노드, Chapter->Skill 엣지, F3 domain_fit |

### 6.5 전공명 정규화 (난이도 높음)

| 항목 | 값 |
| --- | --- |
| 고유 전공명 | **47,163개** |
| 다중 표기 | "경영학" vs "경영학과" vs "경영학부" (4종 = 326K건) |
| 접근 | **Tier 3 (임베딩 전용)** - 정규화 금지, 오매칭 방지 |

### [v3 신규] 구코드→신코드 학교 매핑

| 항목 | 값 |
|------|-----|
| 대상 | 구코드(U0/C0) 457개, ~110만건 |
| 현재 상태 | `Unknown:` 접두사로 미매핑 |
| 접근 | Unknown 접두사에서 원본 코드 추출 → 학교명 기반 매칭 → 신코드(1310xxxx) 매핑 |
| 영향 범위 | Person.education_level 정확도, 학력 필터링 |

**미매핑 코드 분포**:

| 패턴 | 행 수 | 유니크 코드 수 |
|------|--------|-------------|
| Unknown:U0xxx (구 대학) | 616,988 | 282 |
| Unknown:C0xxx (구 전문대) | 477,690 | 175 |
| Unknown:기타 | 4,702 | 1,526 |

### [v3 신규] 직무 코드 계층화

| 항목 | 값 |
|------|-----|
| 대상 | JOB_CLASSIFICATION_SUBCATEGORY 242개 코드 |
| 이슈 | 과도 세분화, 유사 코드 동시선택율 20%+ (실내디자이너↔공간디자이너 30.7%) |
| 접근 | JobCategory(~30개) → JobClassification(242개) 2단 계층 정의 |
| 영향 범위 | Role 노드 category, F5 role_fit |

### [v3 신규] 캠퍼스 코드 정리

| 항목 | 값 |
|------|-----|
| 대상 | UNIVERSITY_CAMPUS 9,665개 중 공백 변형 |
| 사례 | 경상국립대학교 8개 코드 중 3개 불필요 공백 → 5개로 축소 |
| 영향 범위 | 학교 정확 매칭 |
