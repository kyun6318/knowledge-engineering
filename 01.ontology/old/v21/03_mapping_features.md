# MappingFeatures

> 작성일: 2026-03-13
> 

---

## 0. 설계 원칙

각 피처는 **필수 입력(required inputs)**이 정의되어 있고, 해당 입력이 null/Unknown이면 피처 자체를 null로 반환한다. null 피처는 안전하게 무시할 수 있다.

```python
# 피처 계산 공통 패턴
def compute_feature(company_ctx, candidate_ctx, feature_func):
    required = feature_func.required_inputs
    for field_path in required:
        if get_field(company_ctx, candidate_ctx, field_path) is None:
            return FeatureResult(
                score=None,
                confidence=0.0,
                status="INACTIVE",
                reason=f"Required field missing:{field_path}"
            )
    return feature_func(company_ctx, candidate_ctx)
```

### 0.1 매칭 범위 제한

**MappingFeatures 계산 대상은 `career_type = "EXPERIENCED"` 후보로 제한**

서비스 풀의 30.9%를 차지하는 NEW_COMER(신입)는 Career 데이터가 없거나 인턴/아르바이트 수준으로, F1(stage_match), F2(vacancy_fit), F5(role_fit)이 대부분 INACTIVE가 되며 의미 있는 매칭이 불가능하다.

| 피처 | EXPERIENCED | NEW_COMER |
| --- | --- | --- |
| F1 stage_match | ACTIVE 가능 (50-60%) | **INACTIVE** (past_company_context 없음) |
| F2 vacancy_fit | ACTIVE 가능 (50-65%) | **INACTIVE** (situational_signals 추출 불가) |
| F3 domain_fit | ACTIVE 가능 (70%+) | 부분 ACTIVE (Education 기반만 가능) |
| F4 culture_fit | <10% ACTIVE | **INACTIVE** |
| F5 role_fit | ACTIVE 가능 (50-60%) | **INACTIVE** (role_evolution 없음) |

**v2 신입 매칭 로드맵**:

| 버전 | 대상 | 매칭 전략 |
| --- | --- | --- |
| v1 | EXPERIENCED만 | MappingFeatures F1~F5 (본 문서) |
| v2 | + NEW_COMER | Education-based matching (전공-산업 연관), Certificate matching (자격증-직무 연관), 희망 직무 기반 Role matching |

---

## 1. 피처 목록 (v1: 5개)

| # | 피처 | 계산 방법 | 필수 입력 |
| --- | --- | --- | --- |
| F1 | `stage_match` | Rule + LLM | company.stage_estimate, candidate.past_company_context |
| F2 | `vacancy_fit` | LLM scoring | company.vacancy, candidate.situational_signals |
| F3 | `domain_fit` | Embedding 유사도 | company.industry_label, candidate.domain_depth |
| F4 | `culture_fit` | Facet 비교 | company.operating_model.facets, candidate.work_style_signals |
| F5 | `role_fit` | Rule + LLM | company.vacancy.seniority, candidate.role_evolution |

---

## 2. 피처별 상세 계산 로직

### F1: stage_match - 성장 단계 경험 매칭

**질문**: “기업이 현재 겪고 있는 성장 단계를, 후보가 과거에 경험한 적이 있는가?”

### 필수 입력

- `company.stage_estimate.stage_label` (≠ UNKNOWN)
- `candidate.experiences[].past_company_context.estimated_stage_at_tenure` (1개 이상 non-null)

### 계산

```python
def compute_stage_match(company_ctx, candidate_ctx):
    target_stage = company_ctx.stage_estimate.stage_label
    if target_stage == "UNKNOWN":
        return inactive("company stage unknown")

    # 후보의 과거 경험에서 동일/유사 stage 탐색
    stage_experiences = []
    for exp in candidate_ctx.experiences:
        pcc = exp.past_company_context
        if pcc and pcc.estimated_stage_at_tenure:
            stage_experiences.append({
                "stage": pcc.estimated_stage_at_tenure,
                "duration_months": exp.period.duration_months,
                "scope_type": exp.scope_type,
                "experience_id": exp.experience_id
            })

    if not stage_experiences:
        return inactive("no past_company_context with stage")

    # [v7] STAGE_SIMILARITY 전체 4x4 매트릭스 (A4 적용)
    # 행: 기업 stage, 열: 후보 경험 stage
    STAGE_SIMILARITY = {
        ("EARLY", "EARLY"): 1.00,
        ("EARLY", "GROWTH"): 0.30,
        ("EARLY", "SCALE"): 0.15,
        ("EARLY", "MATURE"): 0.10,

        ("GROWTH", "EARLY"): 0.50,
        ("GROWTH", "GROWTH"): 1.00,
        ("GROWTH", "SCALE"): 0.40,
        ("GROWTH", "MATURE"): 0.20,

        ("SCALE", "EARLY"): 0.15,
        ("SCALE", "GROWTH"): 0.50,
        ("SCALE", "SCALE"): 1.00,
        ("SCALE", "MATURE"): 0.45,

        ("MATURE", "EARLY"): 0.10,
        ("MATURE", "GROWTH"): 0.20,
        ("MATURE", "SCALE"): 0.45,
        ("MATURE", "MATURE"): 1.00,
    }

    # --- STAGE_SIMILARITY 비대칭성 설계 근거 [v21] ---
    # (GROWTH, EARLY): 0.50 > (EARLY, GROWTH): 0.30 인 이유:
    # "큰 조직 → 작은 조직" 적응이 "작은 조직 → 큰 조직" 적응보다 용이하다는 가정.
    # GROWTH 기업에서 EARLY 경험자(0.50)가 높은 이유: 초기 스타트업의 빠른 실행력/다역할 경험이
    # 성장기 기업에서도 유용. 반면 EARLY 기업에서 GROWTH 경험자(0.30)가 낮은 이유: 성장기 기업의
    # 전문화된 역할 분담/프로세스 경험이 초기 스타트업의 불확실성/자원 제약 환경에 직접 적용이 어려움.
    #
    # 유사한 논리가 SCALE↔GROWTH, MATURE↔SCALE 쌍에도 적용됨.
    # Phase 0 파일럿에서 이 비대칭 가정의 타당성을 검증한다:
    # - 50건 매핑에서 비대칭 매트릭스 vs 대칭 매트릭스(평균값) 비교
    # - 채용 전문가 5명의 stage_match 적합도 평가와의 상관 분석

    best_match = None
    best_score = 0.0
    for se in stage_experiences:
        sim = STAGE_SIMILARITY.get(
            (target_stage, se["stage"]), 0.2
        )
        # 재직 기간 가중: 12개월+ 경험이면 보너스
        duration_bonus = min(se["duration_months"] / 24.0, 1.0) * 0.15
        # 리더십 가중: Lead/Head로 해당 단계 경험 시 보너스
        scope_bonus = 0.10 if se["scope_type"] in ("LEAD", "HEAD") else 0.0

        total = min(sim + duration_bonus + scope_bonus, 1.0)
        if total > best_score:
            best_score = total
            best_match = se

    # confidence: 양쪽 소스 confidence의 최소값
    confidence = min(
        company_ctx.stage_estimate.stage_confidence,
        best_match_pcc_confidence
    )

    return FeatureResult(
        score=best_score,
        confidence=confidence,
        status="ACTIVE",
        matched_experience_id=best_match["experience_id"],
        evidence=build_evidence(company_ctx.stage_estimate, best_match)
    )
```

### F1 캘리브레이션 계획

| 단계 | 시기 | 방법 | 산출물 |
| --- | --- | --- | --- |
| 초기값 | v1 파일럿 | 전문가 판단 | 현재 4x4 매트릭스 |
| 1차 캘리브레이션 | v1 파일럿 후 | Human evaluation 50건 stage_match 분포 분석 | 보정 매트릭스 |
| 2차 캘리브레이션 | v1 운영 3개월 후 | stage_match score vs 채용 성공률 상관 분석 | 최종 매트릭스 |

---

### F2: vacancy_fit - 포지션 유형 적합도

**질문**: “기업이 찾는 포지션 유형(신규 구축 / 확장 / 리셋)과 후보의 경험이 맞는가?”

### 필수 입력

- `company.vacancy.hiring_context` (≠ UNKNOWN)
- `candidate.experiences[].situational_signals` (1개 이상)

### 계산

```python
# vacancy hiring_context <-> situational_signal 매핑 테이블
VACANCY_SIGNAL_ALIGNMENT = {
    "BUILD_NEW": {
        "strong": ["NEW_SYSTEM_BUILD", "EARLY_STAGE", "PMF_SEARCH"],
        "moderate": ["TEAM_BUILDING", "TECH_STACK_TRANSITION"],
        "weak": ["SCALE_UP"]
    },
    "SCALE_EXISTING": {
        "strong": ["SCALE_UP", "TEAM_SCALING"],
        "moderate": ["LEGACY_MODERNIZATION", "ENTERPRISE_TRANSITION"],
        "weak": ["NEW_SYSTEM_BUILD"]
    },
    "RESET": {
        "strong": ["LEGACY_MODERNIZATION", "TURNAROUND", "TECH_STACK_TRANSITION"],
        "moderate": ["REORG"],
        "weak": ["SCALE_UP"]
    },
    "REPLACE": {
        # REPLACE는 상황 특화 매칭 불필요, 역할 매칭으로 커버
        "strong": [],
        "moderate": [],
        "weak": []
    }
}

def compute_vacancy_fit(company_ctx, candidate_ctx):
    vacancy_type = company_ctx.vacancy.hiring_context
    if vacancy_type == "UNKNOWN":
        return inactive("vacancy hiring_context unknown")

    alignment = VACANCY_SIGNAL_ALIGNMENT.get(vacancy_type)
    if not alignment or vacancy_type == "REPLACE":
        # [v16] REPLACE 공고는 vacancy_fit이 무의미하므로 INACTIVE 처리하고,
        # §4의 가중치 재분배에서 role_fit이 이 가중치를 흡수한다.
        return FeatureResult(score=None, confidence=0.0,
                             status="INACTIVE",
                             reason="REPLACE type: vacancy_fit 비활성, role_fit으로 가중치 재분배")

    # 후보의 모든 situational_signals 수집
    all_signals = []
    for exp in candidate_ctx.experiences:
        for sig in (exp.situational_signals or []):
            all_signals.append({
                "label": sig.signal_label,
                "confidence": sig.confidence,
                "experience_id": exp.experience_id,
                "duration_months": exp.period.duration_months
            })

    if not all_signals:
        return inactive("no situational_signals found")

    # 매칭 스코어 계산
    strong_matches = [s for s in all_signals if s["label"] in alignment["strong"]]
    moderate_matches = [s for s in all_signals if s["label"] in alignment["moderate"]]
    weak_matches = [s for s in all_signals if s["label"] in alignment["weak"]]

    if strong_matches:
        best = max(strong_matches, key=lambda s: s["confidence"])
        base_score = 0.85
    elif moderate_matches:
        best = max(moderate_matches, key=lambda s: s["confidence"])
        base_score = 0.60
    elif weak_matches:
        best = max(weak_matches, key=lambda s: s["confidence"])
        base_score = 0.35
    else:
        return FeatureResult(score=0.15, confidence=0.40,
                             status="ACTIVE", reason="no matching signals")

    # 복수 매칭 보너스
    match_count = len(strong_matches) + len(moderate_matches)
    multi_bonus = min(match_count * 0.05, 0.10)

    score = min(base_score + multi_bonus, 1.0)
    confidence = min(
        company_ctx.vacancy.evidence[0].confidence if company_ctx.vacancy.evidence else 0.5,
        best["confidence"]
    )

    return FeatureResult(
        score=score,
        confidence=confidence,
        status="ACTIVE",
        matched_signals=[s["label"] for s in strong_matches + moderate_matches],
        evidence=build_evidence(company_ctx.vacancy, best)
    )
```

### F2 보충: Outcome 활용 방침

**v1에서 Outcome은 MappingFeatures 매칭 피처로 사용하지 않는다.**

| 결정 | 근거 |
| --- | --- |
| Outcome을 F1~F5에서 사용하지 않음 | (1) Outcome은 자유 텍스트 기반 추출로 정규화가 되어 있지 않아, 두 Outcome 간 비교 방법이 미정의. “MAU 10x”와 “사용자 10배 증가”가 동일 성과인지 판단 불가. (2) F2 vacancy_fit은 SituationalSignal(고정 taxonomy)로 매칭하며, 이것이 구조화된 비교를 가능하게 함. (3) Outcome의 정량 비교는 outcome_type, metric_value의 정규화가 선행되어야 함 |
| Outcome 노드는 유지 | 후보 프로필 표시, 그래프 탐색(Q3 유사 경험 후보), v2 매칭 피처 확장에 활용 |

**v2 Outcome 활용 계획**:

| 단계 | 활용 방안 | 전제 조건 |
| --- | --- | --- |
| v2.0 | outcome_type 기반 카테고리 매칭 (METRIC/SCALE/DELIVERY 등) | outcome_type 추출 정확도 >= 80% |
| v2.1 | metric_value 정규화 (숫자 추출 + 단위 통일) 후 정량 비교 | metric_value 정규화 파이프라인 구축 |
| v2.2 | Outcome description 임베딩 유사도 기반 비교 | 임베딩 매칭 정확도 검증 |

---

### F3: domain_fit - 도메인 적합도

> F3 domain_fit의 industry code 매칭 로직은 본 문서가 정본이다. 00_data_source_mapping §4.1은 데이터 소스 관점의 참조 정보만 기술한다.
> 

**질문**: “기업의 산업/도메인과 후보의 도메인 경험이 맞는가?”

### 필수 입력

- `company.company_profile.industry_label` 또는 `company.domain_positioning.market_segment`
- `candidate.domain_depth`

### 계산

```python
def compute_domain_fit(company_ctx, candidate_ctx):
    company_domain = (
        company_ctx.domain_positioning.market_segment
        or company_ctx.company_profile.industry_label
    )
    if not company_domain:
        return inactive("company domain unknown")

    candidate_domain = candidate_ctx.domain_depth
    if not candidate_domain:
        return inactive("candidate domain_depth missing")

    # 방법 1: Embedding 유사도 (Primary)
    company_emb = embed(company_domain)
    candidate_emb = embed(candidate_domain.primary_domain
                          + " " + candidate_domain.description)
    cosine_sim = cosine_similarity(company_emb, candidate_emb)

    # 방법 2: Industry code 직접 매칭 (보조)
    # [R-7/U-7] industry_code[:3] 슬라이싱 제거 -> code-hub lookup 기반 계층 비교로 변경.
    # code-hub INDUSTRY 코드는 prefix 기반 계층 구조가 보장되지 않으므로,
    # group_code(INDUSTRY_SUBCATEGORY) / category(INDUSTRY_CATEGORY)를 명시적으로 조회하여 비교한다.
    code_match_bonus = 0.0
    company_code = company_ctx.company_profile.industry_code
    company_detail = lookup_common_code(type="INDUSTRY", code=company_code) if company_code else None

    for exp in candidate_ctx.experiences:
        pcc = exp.past_company_context
        if pcc and pcc.industry_code:
            candidate_detail = lookup_common_code(type="INDUSTRY", code=pcc.industry_code)
            if not candidate_detail or not company_detail:
                continue

            if pcc.industry_code == company_code:
                code_match_bonus = 0.25  # 소분류(3depth) 일치
                break
            elif candidate_detail.sub_code == company_detail.sub_code:
                code_match_bonus = max(code_match_bonus, 0.15)  # 중분류(2depth) 일치
            elif candidate_detail.group_code == company_detail.group_code:
                code_match_bonus = max(code_match_bonus, 0.08)  # 대분류(1depth) 일치

    # 반복 경험 가중
    repeat_bonus = min(candidate_domain.domain_experience_count * 0.05, 0.15)

    score = min(cosine_sim + code_match_bonus + repeat_bonus, 1.0)

    # confidence: embedding 유사도는 해석이 어려우므로 보수적
    confidence = min(0.60, 0.40 + code_match_bonus)

    return FeatureResult(
        score=score,
        confidence=confidence,
        status="ACTIVE",
        evidence=build_evidence_domain(company_domain, candidate_domain)
    )
```

---

### F4: culture_fit - 문화/운영 방식 정렬

**질문**: “기업의 운영 방식과 후보의 일하는 방식 선호가 맞는가?”

### 필수 입력

- `company.operating_model.facets` (1개 이상 non-null)
- `candidate.work_style_signals` (non-null)

### 계산

```python
FACET_TO_WORKSTYLE = {
    "speed": "autonomy_preference",      # 빠른 실행 -> 높은 자율성 선호
    "autonomy": "autonomy_preference",
    "process": "process_tolerance",
}

ALIGNMENT_LOGIC = {
    # (company_facet_high, candidate_preference) -> alignment_score
    ("speed_high", "autonomy_HIGH"): 0.9,
    ("speed_high", "autonomy_MID"): 0.6,
    ("speed_high", "autonomy_LOW"): 0.3,
    ("process_high", "process_tolerance_HIGH"): 0.9,
    ("process_high", "process_tolerance_MID"): 0.6,
    ("process_high", "process_tolerance_LOW"): 0.3,
    # ...
}

def compute_culture_fit(company_ctx, candidate_ctx):
    facets = company_ctx.operating_model.facets
    work_style = candidate_ctx.work_style_signals
    if not work_style:
        return inactive("candidate work_style_signals is null")

    active_facets = {k: v for k, v in facets.items()
                     if v and v.score is not None}
    if not active_facets:
        return inactive("no active company facets")

    # 각 facet별 정렬 스코어 계산
    alignment_scores = []
    for facet_name, facet_data in active_facets.items():
        ws_field = FACET_TO_WORKSTYLE.get(facet_name)
        if not ws_field:
            continue
        ws_value = getattr(work_style, ws_field, None)
        if ws_value is None:
            continue

        # facet score를 high/mid/low로 변환
        facet_level = "high" if facet_data.score > 0.6 else (
            "low" if facet_data.score < 0.3 else "mid"
        )
        key = (f"{facet_name}_{facet_level}", f"{ws_field}_{ws_value}")
        alignment = ALIGNMENT_LOGIC.get(key, 0.5)  # 기본값 중립

        alignment_scores.append({
            "facet": facet_name,
            "score": alignment,
            "confidence": min(facet_data.confidence, work_style.confidence)
        })

    if not alignment_scores:
        return inactive("no overlapping facets and work_style")

    # 평균 정렬 스코어
    avg_score = sum(a["score"] for a in alignment_scores) / len(alignment_scores)
    avg_confidence = sum(a["confidence"] for a in alignment_scores) / len(alignment_scores)

    return FeatureResult(
        score=avg_score,
        confidence=avg_confidence,
        status="ACTIVE",
        facet_details=alignment_scores,
        evidence=build_evidence_culture(facets, work_style)
    )
```

candidate.work_style_signals가 null인 경우가 70%+ 예상되므로, culture_fit은 **대부분의 매핑에서 INACTIVE** 상태가 될 것이다. v2에서 Closed-loop 질문으로 보강한다.

---

### F5: role_fit - 역할 적합도

**질문**: “기업이 요구하는 시니어리티/역할과 후보의 경력 수준이 맞는가?”

### 필수 입력

- `company.vacancy.seniority` (!= UNKNOWN)
- `candidate.role_evolution` (non-null)

### 계산

```python
SENIORITY_ORDER = {
    "JUNIOR": 1, "MID": 2, "SENIOR": 3, "LEAD": 4, "HEAD": 5
}

ROLE_PATTERN_FIT = {
    # (required_seniority, role_pattern) -> fit_score
    ("SENIOR", "IC_TO_LEAD"): 0.90,     # Lead 경험이 있는 사람이 Senior급으로 오는 것
    ("SENIOR", "IC_DEPTH"): 0.85,       # IC 전문가가 Senior급
    ("LEAD", "IC_TO_LEAD"): 0.95,       # 정확히 맞는 궤적
    ("LEAD", "LEAD_TO_HEAD"): 0.80,     # 오버 스펙이지만 적합
    ("HEAD", "LEAD_TO_HEAD"): 0.95,
    ("HEAD", "IC_TO_LEAD"): 0.50,       # 궤적은 맞지만 Head까지는 아직
    # ...
}

# ROLE_PATTERN_FIT 캘리브레이션 계획:
# 현재 매트릭스는 전문가 판단 기반 초기값이다.
# - 1차 캘리브레이션: v1 파일럿 50건에서 role_fit score vs 전문가 평가 상관 분석
# - 2차 캘리브레이션: v1 운영 3개월 후 실제 채용 데이터 기반 보정
# - F1 stage_match와 동일한 캘리브레이션 프로토콜 적용

def compute_role_fit(company_ctx, candidate_ctx):
    required = company_ctx.vacancy.seniority
    if required == "UNKNOWN":
        return inactive("vacancy seniority unknown")

    role_evo = candidate_ctx.role_evolution
    if not role_evo:
        return inactive("role_evolution missing")

    # 패턴 기반 적합도
    pattern_score = ROLE_PATTERN_FIT.get(
        (required, role_evo.pattern), 0.50  # 기본값 중립
    )

    # 경력 연수 보정
    required_years = {"JUNIOR": 2, "MID": 4, "SENIOR": 7, "LEAD": 8, "HEAD": 12}
    min_years = required_years.get(required, 5)
    years_ratio = candidate_ctx.role_evolution.total_experience_years / min_years

    if years_ratio >= 1.0:
        years_bonus = min((years_ratio - 1.0) * 0.05, 0.10)
    else:
        years_penalty = (1.0 - years_ratio) * 0.20
        years_bonus = -years_penalty

    score = max(0.0, min(pattern_score + years_bonus, 1.0))

    # [v7] 최근 경험의 scope_type -> seniority 변환 적용 (A1)
    # 02_candidate_context.md의 scope_type -> seniority 매핑 참조
    latest_exp = candidate_ctx.experiences[0] if candidate_ctx.experiences else None
    if latest_exp and latest_exp.scope_type != "UNKNOWN":
        # scope_type을 seniority로 변환: IC/SENIOR_IC/LEAD/HEAD/FOUNDER 매핑
        candidate_seniority = get_candidate_seniority(candidate_ctx)
        latest_level = SENIORITY_ORDER.get(candidate_seniority, 0)
        required_level = SENIORITY_ORDER.get(required, 0)
        if latest_level >= required_level:
            score = min(score + 0.05, 1.0)  # 현재 수준이 요구 수준 이상

    confidence = min(
        0.70,  # role matching은 비교적 판단 가능
        role_evo.confidence
    )

    return FeatureResult(
        score=score,
        confidence=confidence,
        status="ACTIVE",
        evidence=build_evidence_role(company_ctx.vacancy, role_evo)
    )
```

---

## 3. MappingFeatures JSON 스키마

```json
{
  "$schema": "MappingFeatures_v4",
  "company_id": "comp_12345",
  "job_id": "job_67890",
  "candidate_id": "cand_99999",

  "_meta": {
    "mapping_version": "4.0",
    "context_version": "4.0",
    "company_context_id": "cc_xxx",
    "candidate_context_id": "cdc_yyy",
    "code_sha": "abc1234",
    "generated_at": "2026-03-08T12:00:00Z"
  },

  "summary": {
    "active_features": 4,
    "total_features": 5,
    "inactive_features": ["culture_fit"],
    "avg_confidence": 0.58,
    "overall_match_score": 0.72
  },

  "features": {
    "stage_match": {
      "score": 0.78,
      "confidence": 0.55,
      "status": "ACTIVE",
      "matched_experience_id": "cand_99999_exp_01",
      "detail": "기업 GROWTH 단계, 후보 A사에서 GROWTH 단계 27개월 경험 (Lead)",
      "company_evidence": {
        "source_id": "nice_comp_12345",
        "source_type": "nice",
        "span": "설립 2019, 직원 85명 -> GROWTH 추정",
        "confidence": 0.65
      },
      "candidate_evidence": {
        "source_id": "resume_001",
        "source_type": "self_resume",
        "span": "시리즈 A->B 전환기 경험",
        "confidence": 0.70
      }
    },

    "vacancy_fit": {
      "score": 0.85,
      "confidence": 0.65,
      "status": "ACTIVE",
      "matched_signals": ["SCALE_UP", "TEAM_SCALING"],
      "detail": "SCALE_EXISTING 포지션, 후보 SCALE_UP + TEAM_SCALING strong match",
      "company_evidence": {
        "source_id": "jd_67890",
        "source_type": "jd_internal",
        "span": "트래픽 10배 증가 대응을 위한 시니어 엔지니어",
        "confidence": 0.75
      },
      "candidate_evidence": {
        "source_id": "resume_001",
        "source_type": "self_resume",
        "span": "MAU 10x 달성, 팀 4->18명 확장",
        "confidence": 0.80
      }
    },

    "domain_fit": {
      "score": 0.72,
      "confidence": 0.55,
      "status": "ACTIVE",
      "detail": "기업 소프트웨어 개발(B2B SaaS), 후보 B2B SaaS 3개사 반복 경험",
      "company_evidence": {
        "source_id": "nice_comp_12345",
        "source_type": "nice",
        "span": "업종: SW_DEV 소프트웨어 개발업",
        "confidence": 0.70
      },
      "candidate_evidence": {
        "source_id": "resume_001",
        "source_type": "self_resume",
        "span": "B2B SaaS 기반 서비스 3개사 경험",
        "confidence": 0.65
      }
    },

    "culture_fit": {
      "score": null,
      "confidence": 0.0,
      "status": "INACTIVE",
      "reason": "candidate work_style_signals is null",
      "company_evidence": null,
      "candidate_evidence": null
    },

    "role_fit": {
      "score": 0.88,
      "confidence": 0.65,
      "status": "ACTIVE",
      "detail": "SENIOR 요구, 후보 IC_TO_LEAD 패턴 / 7년 경력 / 최근 LEAD",
      "company_evidence": {
        "source_id": "jd_67890",
        "source_type": "jd_internal",
        "span": "시니어 백엔드 엔지니어",
        "confidence": 0.75
      },
      "candidate_evidence": {
        "source_id": "resume_001",
        "source_type": "self_resume",
        "span": "Engineering Lead (2021~2023)",
        "confidence": 0.70
      }
    }
  }
}
```

---

## 4. overall_match_score 계산

활성화된 피처의 가중 평균. 비활성 피처는 제외.

```python
FEATURE_WEIGHTS = {
    "stage_match": 0.25,
    "vacancy_fit": 0.30,
    "domain_fit": 0.20,
    "culture_fit": 0.10,
    "role_fit": 0.15
}

# 가중치 설정 근거:
# - vacancy_fit (0.30): 포지션 유형 적합도가 매칭에 가장 직접적인 영향. 채용 전문가 판단 기반 최우선 피처
# - stage_match (0.25): 성장 단계 경험은 조직 적응의 핵심 예측 변수
# - domain_fit (0.20): 산업/도메인 이해도는 성과와 상관관계 높으나, 이직 시 학습 가능
# - role_fit (0.15): 역할 수준 매칭은 필터링에 가까움 (over-spec은 허용)
# - culture_fit (0.10): v1에서 대부분 INACTIVE이므로 최소 가중치 배정
#
# 이 가중치는 전문가 판단 기반 초기값이다. v1 파일럿 후 아래 캘리브레이션을 수행한다:
# - 1차: Human eval 50건의 overall 점수 vs 전문가 적합도 평가 상관 분석 -> 가중치 보정
# - 2차: v1 운영 3개월 후 채용 성공률 데이터 기반 최종 보정

def compute_overall_score(features, use_double_dampening=False):
    """
    [R-9/O-7] v1 기본: 단순 가중 평균.
    v1 대부분의 피처 confidence가 0.40~0.65 범위이므로, 이중 감쇠 적용 시
    점수 분포가 과도하게 압축되어 변별력이 저하될 위험이 있다.

    v1 파일럿에서 다음 비교를 수행한 후 이중 감쇠 도입 여부를 결정한다:
    - 단순 가중 평균 vs 이중 감쇠의 점수 분포 비교
    - 전문가 평가와의 상관관계(Pearson r) 비교
    - 이중 감쇠가 r을 유의미하게(+0.05 이상) 개선하면 도입
    """
    active = {k: v for k, v in features.items() if v.status == "ACTIVE"}
    if not active:
        return None

    # 비활성 피처의 weight를 활성 피처에 재분배
    total_active_weight = sum(FEATURE_WEIGHTS[k] for k in active)
    normalized_weights = {
        k: FEATURE_WEIGHTS[k] / total_active_weight for k in active
    }

    if use_double_dampening:
        # [원본] confidence 가중 스코어 (의도적 이중 감쇠)
        # "확신도 높은 피처가 최종 스코어를 주도"하는 효과.
        # v1 파일럿 결과 단순 가중 평균 대비 개선이 확인되면 활성화.
        weighted_sum = sum(
            active[k].score * normalized_weights[k] * active[k].confidence
            for k in active
        )
        weight_sum = sum(
            normalized_weights[k] * active[k].confidence
            for k in active
        )
        return weighted_sum / weight_sum if weight_sum > 0 else None
    else:
        # 단순 가중 평균 - score만 사용, confidence는 메타 정보로 보고
        return sum(
            active[k].score * normalized_weights[k]
            for k in active
        )
```

### 4.1 overall_match_score 분포 모니터링

v1에서 대부분의 피처 confidence가 0.40~0.65 범위에 있어, 이중 감쇠로 overall_match_score가 과도하게 낮아지거나 고confidence 피처가 과도하게 지배할 수 있다.

**파일럿 50건 모니터링 기준**:

| 지표 | 정상 범위 | 이상 징후 | 대응 |
| --- | --- | --- | --- |
| overall_match_score 분포 | 0.3~0.7에 60~80% 집중 | 0.3 미만 40%+ 또는 0.7 초과 30%+ | 이중 감쇠 -> 단순 가중 평균 전환 검토 |
| 단일 피처 지배율 | 어떤 피처도 overall에 50% 이상 기여하지 않음 | 특정 피처가 overall의 60%+ 기여 | 해당 피처의 confidence 보정 또는 가중치 하향 |
| REPLACE 공고 overall 분포 | role_fit 주도 (vacancy_fit INACTIVE) | role_fit도 INACTIVE -> overall 산출 불가 비율 10%+ | REPLACE 전용 fallback 피처 검토 |

> **REPLACE 공고 처리**: REPLACE 공고에서 vacancy_fit이 INACTIVE가 되면, 해당 가중치(0.30)가 나머지 활성 피처에 재분배된다. 특히 role_fit(기존 0.15)이 재분배 후 실질 가중치가 크게 상승하므로, REPLACE 공고에서는 역할 적합도가 매칭의 핵심 기준이 된다. 이는 “충원” 목적의 공고에서 역할/시니어리티 매칭이 가장 중요하다는 도메인 직관과 일치한다.
>

> **[v21] REPLACE 공고 비율 모니터링**: Phase 0에서 JD의 hiring_context 분포를 실측하여 REPLACE 비율을 확인한다. REPLACE가 전체 JD의 30% 이상이면 vacancy_fit 가중치(0.30)의 대부분이 role_fit으로 흡수되어 전체 매칭 품질에 상당한 영향을 미칠 수 있다. 이 경우 REPLACE 전용 피처(경력 연수 정확 매칭, 기술 스택 중첩도 등) 도입을 Phase 2에서 검토한다.

### 4.2 freshness_weight 적용 규칙

> §4.2 freshness_weight/ranking_score 서빙 구현 → 03.graphrag/results/implement_planning/separate/v3/graphrag/08_serving.md로 이동

---

## 5. DS/MLE 소비 인터페이스

> §5 BigQuery 서빙 스키마/SQL → 03.graphrag/results/implement_planning/separate/v3/graphrag/08_serving.md로 이동

---

## 6. 평가 전략

> §6 평가 전략 → 03.graphrag/results/implement_planning/separate/v3/graphrag/09_evaluation.md로 이동