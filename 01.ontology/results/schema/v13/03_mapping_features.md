# MappingFeatures v13 — 통합판

> v4 원본에 A4(STAGE_SIMILARITY 전체 매트릭스 + 캘리브레이션), A1(F5 scope_type 변환)을 통합.
>
> 작성일: 2026-03-10 | 기준: v4 MappingFeatures + v4 amendments (A1, A4) + v12 데이터 분석 v2.1
>
> **v8 변경** (2026-03-08): [M-2] compute_overall_score의 confidence 이중 감쇠 설계 의도 주석 추가
>
> **v13 변경** (2026-03-10): v12 데이터 분석 v2.1 결과 인라인 반영
> - F1~F5 예상 ACTIVE 비율을 실측 데이터 기반으로 보정 (7.1절 뒤에 추가)
> - F3 domain_fit에서 industry_code_match 참조를 v13 C-2 수정 반영

---

## 0. 설계 원칙

### 핵심 변경 (v3 → v4)

| v3 | v4 |
|---|---|
| 7개 피처 정의 (계산 방법 미정의) | 5개 피처로 축소 + 계산 로직 명시 |
| 모든 피처가 필수 | 소스 필드 가용성에 따라 자동 비활성화 |
| EvidenceBundle이 별도 구조 | 각 피처 내부에 evidence 포함 |
| 점수 산출 기준 불명확 | Hybrid 계산 (Rule + LLM + Embedding) 명시 |

### Graceful Degradation

각 피처는 **필수 입력(required inputs)**이 정의되어 있고, 해당 입력이 null/Unknown이면 피처 자체를 null로 반환한다. DS/MLE는 null 피처를 안전하게 무시할 수 있다.

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
                reason=f"Required field missing: {field_path}"
            )
    return feature_func(company_ctx, candidate_ctx)
```

---

## 1. 피처 목록 (v1: 5개)

| # | 피처 | v3 대응 | 계산 방법 | 필수 입력 |
|---|---|---|---|---|
| F1 | `stage_match` | stage_transition_match | Rule + LLM | company.stage_estimate, candidate.past_company_context |
| F2 | `vacancy_fit` | vacancy_fit | LLM scoring | company.vacancy, candidate.situational_signals |
| F3 | `domain_fit` | domain_positioning_fit | Embedding 유사도 | company.industry_label, candidate.domain_depth |
| F4 | `culture_fit` | culture_fit | Facet 비교 | company.operating_model.facets, candidate.work_style_signals |
| F5 | `role_fit` | role_evolution_fit | Rule + LLM | company.vacancy.seniority, candidate.role_evolution |

**v3에서 제거/축소한 피처**:
- `tension_alignment` → v1에서 structural_tensions가 대부분 null이므로 v2로 이동
- `resilience_fit` → v1에서 failure_recovery가 대부분 null이므로 v2로 이동

---

## 2. 피처별 상세 계산 로직

### F1: stage_match — 성장 단계 경험 매칭

**질문**: "기업이 현재 겪고 있는 성장 단계를, 후보가 과거에 경험한 적이 있는가?"

#### 필수 입력
- `company.stage_estimate.stage_label` (≠ UNKNOWN)
- `candidate.experiences[].past_company_context.estimated_stage_at_tenure` (1개 이상 non-null)

#### 계산

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

    # 설계 근거:
    # - 대각선(동일 stage) = 1.0
    # - 인접 비대칭: GROWTH->EARLY(0.50) > EARLY->GROWTH(0.30)
    # - MATURE-SCALE 양방향 0.45
    # - 원거리 0.10~0.20

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

#### [v7] F1 캘리브레이션 계획

| 단계 | 시기 | 방법 | 산출물 |
|---|---|---|---|
| 초기값 | v1 파일럿 | 전문가 판단 | 현재 4x4 매트릭스 |
| 1차 캘리브레이션 | v1 파일럿 후 | Human evaluation 50건 stage_match 분포 분석 | 보정 매트릭스 |
| 2차 캘리브레이션 | v1 운영 3개월 후 | stage_match score vs 채용 성공률 상관 분석 | 최종 매트릭스 |

---

### F2: vacancy_fit — 포지션 유형 적합도

**질문**: "기업이 찾는 포지션 유형(신규 구축 / 확장 / 리셋)과 후보의 경험이 맞는가?"

#### 필수 입력
- `company.vacancy.scope_type` (≠ UNKNOWN)
- `candidate.experiences[].situational_signals` (1개 이상)

#### 계산

```python
# vacancy scope_type ↔ situational_signal 매핑 테이블
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
    vacancy_type = company_ctx.vacancy.scope_type
    if vacancy_type == "UNKNOWN":
        return inactive("vacancy scope_type unknown")

    alignment = VACANCY_SIGNAL_ALIGNMENT.get(vacancy_type)
    if not alignment or vacancy_type == "REPLACE":
        return FeatureResult(score=0.5, confidence=0.30,
                             status="ACTIVE", reason="REPLACE type, neutral score")

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

---

### F3: domain_fit — 도메인 적합도

**질문**: "기업의 산업/도메인과 후보의 도메인 경험이 맞는가?"

#### 필수 입력
- `company.company_profile.industry_label` 또는 `company.domain_positioning.market_segment`
- `candidate.domain_depth`

#### 계산

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
    code_match_bonus = 0.0
    for exp in candidate_ctx.experiences:
        pcc = exp.past_company_context
        if pcc and pcc.industry_code:
            if pcc.industry_code[:3] == company_ctx.company_profile.industry_code[:3]:
                code_match_bonus = 0.15  # 대분류 일치
            if pcc.industry_code == company_ctx.company_profile.industry_code:
                code_match_bonus = 0.25  # 소분류 일치
                break

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

### F4: culture_fit — 문화/운영 방식 정렬

**질문**: "기업의 운영 방식과 후보의 일하는 방식 선호가 맞는가?"

#### 필수 입력
- `company.operating_model.facets` (1개 이상 non-null)
- `candidate.work_style_signals` (non-null)

#### 계산

```python
FACET_TO_WORKSTYLE = {
    "speed": "autonomy_preference",      # 빠른 실행 → 높은 자율성 선호
    "autonomy": "autonomy_preference",
    "process": "process_tolerance",
}

ALIGNMENT_LOGIC = {
    # (company_facet_high, candidate_preference) → alignment_score
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

**v1 현실**: candidate.work_style_signals가 null인 경우가 70%+ 예상되므로, culture_fit은 **대부분의 매핑에서 INACTIVE** 상태가 될 것이다. 이는 정상이며, v2에서 Closed-loop 질문으로 보강한다.

---

### F5: role_fit — 역할 적합도

**질문**: "기업이 요구하는 시니어리티/역할과 후보의 경력 수준이 맞는가?"

#### 필수 입력
- `company.vacancy.seniority` (≠ UNKNOWN)
- `candidate.role_evolution` (non-null)

#### 계산

```python
SENIORITY_ORDER = {
    "JUNIOR": 1, "MID": 2, "SENIOR": 3, "LEAD": 4, "HEAD": 5
}

ROLE_PATTERN_FIT = {
    # (required_seniority, role_pattern) → fit_score
    ("SENIOR", "IC_TO_LEAD"): 0.90,     # Lead 경험이 있는 사람이 Senior급으로 오는 것
    ("SENIOR", "IC_DEPTH"): 0.85,       # IC 전문가가 Senior급
    ("LEAD", "IC_TO_LEAD"): 0.95,       # 정확히 맞는 궤적
    ("LEAD", "LEAD_TO_HEAD"): 0.80,     # 오버 스펙이지만 적합
    ("HEAD", "LEAD_TO_HEAD"): 0.95,
    ("HEAD", "IC_TO_LEAD"): 0.50,       # 궤적은 맞지만 Head까지는 아직
    # ...
}

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

    # [v7] 최근 경험의 scope_type → seniority 변환 적용 (A1)
    # 02_candidate_context.md의 scope_type → seniority 매핑 참조
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
        "span": "설립 2019, 직원 85명 → GROWTH 추정",
        "confidence": 0.65
      },
      "candidate_evidence": {
        "source_id": "resume_001",
        "source_type": "self_resume",
        "span": "시리즈 A→B 전환기 경험",
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
        "span": "MAU 10x 달성, 팀 4→18명 확장",
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
        "span": "업종: J63112 소프트웨어 개발",
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

def compute_overall_score(features):
    # [v8] 설계 의도: confidence를 가중치로 사용하는 것은 의도적 이중 감쇠이다.
    # 개별 피처 score는 source ceiling 적용으로 이미 보수적이나,
    # overall에서 low-confidence 피처의 기여를 추가로 제한하여
    # "확신도 높은 피처가 최종 스코어를 주도"하는 효과를 의도한다.
    # 파일럿 후 이중 감쇠가 과도하면 단순 가중 평균으로 전환을 검토한다.
    active = {k: v for k, v in features.items() if v.status == "ACTIVE"}
    if not active:
        return None

    # 비활성 피처의 weight를 활성 피처에 재분배
    total_active_weight = sum(FEATURE_WEIGHTS[k] for k in active)
    normalized_weights = {
        k: FEATURE_WEIGHTS[k] / total_active_weight for k in active
    }

    # confidence 가중 스코어 (의도적 이중 감쇠 — 위 설계 의도 참조)
    weighted_sum = sum(
        active[k].score * normalized_weights[k] * active[k].confidence
        for k in active
    )
    weight_sum = sum(
        normalized_weights[k] * active[k].confidence
        for k in active
    )

    return weighted_sum / weight_sum if weight_sum > 0 else None
```

---

## 5. DS/MLE 소비 인터페이스

### 5.1 서빙 형태

| 옵션 | 장점 | 단점 | v1 권장 |
|---|---|---|---|
| BigQuery 테이블 | 기존 파이프라인 통합 쉬움, SQL 조인 | 실시간 불가 | **v1 채택** |
| REST API | 실시간 조회 가능 | 구축 비용 | v2 |
| Parquet 파일 (GCS) | 가장 단순 | 접근성 낮음 | PoC용 |

### 5.2 BigQuery 테이블 스키마 (v1)

```sql
-- mapping_features 테이블
CREATE TABLE context.mapping_features (
  mapping_id STRING NOT NULL,
  company_id STRING NOT NULL,
  job_id STRING NOT NULL,
  candidate_id STRING NOT NULL,

  -- 피처 스코어 (null = INACTIVE)
  stage_match_score FLOAT64,
  stage_match_confidence FLOAT64,
  vacancy_fit_score FLOAT64,
  vacancy_fit_confidence FLOAT64,
  domain_fit_score FLOAT64,
  domain_fit_confidence FLOAT64,
  culture_fit_score FLOAT64,
  culture_fit_confidence FLOAT64,
  role_fit_score FLOAT64,
  role_fit_confidence FLOAT64,

  -- 요약
  active_feature_count INT64,
  overall_match_score FLOAT64,
  avg_confidence FLOAT64,

  -- 메타
  context_version STRING,
  generated_at TIMESTAMP,

  -- JSON 상세 (디버깅/분석용)
  features_detail JSON
);

-- company_context 테이블
CREATE TABLE context.company_context (
  company_id STRING NOT NULL,
  job_id STRING NOT NULL,
  stage_label STRING,
  stage_confidence FLOAT64,
  vacancy_scope_type STRING,
  vacancy_seniority STRING,
  industry_code STRING,
  industry_label STRING,
  employee_count INT64,
  speed_score FLOAT64,
  autonomy_score FLOAT64,
  process_score FLOAT64,
  fill_rate FLOAT64,
  context_version STRING,
  generated_at TIMESTAMP,
  full_context JSON
);

-- candidate_context 테이블
CREATE TABLE context.candidate_context (
  candidate_id STRING NOT NULL,
  resume_id STRING NOT NULL,
  role_evolution_pattern STRING,
  total_experience_years FLOAT64,
  primary_domain STRING,
  domain_experience_count INT64,
  experience_count INT64,
  signal_labels ARRAY<STRING>,  -- 모든 경험의 situational_signal 합집합
  fill_rate FLOAT64,
  context_version STRING,
  generated_at TIMESTAMP,
  full_context JSON
);
```

### 5.3 DS/MLE 사용 예시

```sql
-- 기본 매핑 조회: job_id별 후보 랭킹
SELECT
  mf.candidate_id,
  mf.overall_match_score,
  mf.avg_confidence,
  mf.stage_match_score,
  mf.vacancy_fit_score,
  mf.domain_fit_score,
  mf.role_fit_score,
  mf.active_feature_count
FROM context.mapping_features mf
WHERE mf.job_id = 'job_67890'
  AND mf.overall_match_score IS NOT NULL
ORDER BY mf.overall_match_score * mf.avg_confidence DESC
LIMIT 50;

-- Context on/off ablation: 기존 스킬 매칭 + Context 피처 결합
SELECT
  s.candidate_id,
  s.skill_match_score,
  mf.overall_match_score AS context_score,
  -- 결합 스코어
  s.skill_match_score * 0.5 + COALESCE(mf.overall_match_score, 0) * 0.5 AS combined_score
FROM search.skill_matching s
LEFT JOIN context.mapping_features mf
  ON s.candidate_id = mf.candidate_id
  AND s.job_id = mf.job_id
WHERE s.job_id = 'job_67890'
ORDER BY combined_score DESC;
```

---

## 6. v1 / v1.1 / v2 로드맵

| 피처 | v1 | v1.1 | v2 |
|---|---|---|---|
| stage_match | O (Rule + NICE) | 투자 DB 보강 | stage taxonomy 확장 |
| vacancy_fit | O (14 signal labels) | O | taxonomy 확장 |
| domain_fit | O (Embedding + code) | 크롤링 보강 | 경쟁사 맥락 추가 |
| culture_fit | 대부분 INACTIVE | 일부 활성화 | Closed-loop 보강 |
| role_fit | O (Rule + LLM) | O | 세분화 |
| tension_alignment | — | — | v2 추가 (structural_tensions 활성화 후) |
| resilience_fit | — | — | v2 추가 (failure_recovery 보강 후) |

---

## 7. 평가 전략

### 7.1 오프라인 평가 (v1)

| 평가 방법 | 대상 | 측정 지표 |
|---|---|---|
| Human evaluation (5명) | 매핑 50건 | 피처 스코어 vs 전문가 판단 상관관계 |
| stage_match 캘리브레이션 | 매핑 50건 | Human eval의 stage_match 분포 분석 -> A4 매트릭스 1차 보정 (F1 참조) |
| Ablation (Context on/off) | 전체 매핑 | 기존 스킬 매칭 대비 랭킹 품질 변화 |
| Coverage 분석 | 전체 매핑 | 피처별 ACTIVE 비율 |
| Confidence 캘리브레이션 | 전체 매핑 | confidence vs 실제 정확도 상관관계 |

### 7.2 성공 기준 (v1 MVP)

| 지표 | 최소 기준 | 목표 |
|---|---|---|
| 매핑 생성 성공률 | 90%+ | 95%+ |
| 피처 1개 이상 ACTIVE 비율 | 80%+ | 90%+ |
| Human eval 상관관계 (stage_match) | r > 0.4 | r > 0.6 |
| Human eval 상관관계 (vacancy_fit) | r > 0.4 | r > 0.6 |
| 처리 시간 (1건 매핑) | < 30초 | < 10초 |

### 7.3 피처별 v1 활성화 전망 — 실측 기반 [v13, 00_data_source_mapping §6.5 인라인]

데이터 분석 v2.1 실측 결과에 기반한 각 피처의 ACTIVE 비율 전망.

| 피처 | 예상 ACTIVE 비율 | 주요 병목 | 보완 전략 |
|---|---|---|---|
| F1 stage_match | 중간 (~50-60%) | 회사명→Organization 정규화 (4.48M 고유값), NICE 매핑 | BRN 62% 활용 1차 클러스터링 |
| F2 vacancy_fit | 중간 (~50-65%) | careerDescription **16.9%** 보유율이 병목 | selfIntroduction 64.1% fallback |
| F3 domain_fit | 높음 (~70%+) | industryCodes 66% 빈배열이나 NICE/codehub 보완 가능 | PastCompanyContext job-hub 역참조 |
| F4 culture_fit | **매우 낮음 (<10%)** | work_style_signals 데이터 부재 | v2 Closed-loop 질문으로 보강 |
| F5 role_fit | 중간 (~50-60%) | positionGrade/Title 저입력 (29-39%) | workDetails LLM fallback |

> **[v13]** F4 culture_fit의 ACTIVE 비율이 <10%로 매우 낮으나, 이는 v1에서 예상된 정상 상태이다 (02_candidate_context §2.5 "v1 현실" 참조). v2에서 Closed-loop 질문으로 보강 시 50%+ ACTIVE 달성이 목표이다.
