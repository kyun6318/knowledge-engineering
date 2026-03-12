# Phase 3: 기업 정보 + 매칭 관계 (7주, Week 16-22)

> **목적**: JD 데이터와 기업 정보를 Graph에 추가하고, 후보자-공고 매칭 관계를 구축.
>
> **v2 대비 변경**:
> - N3: MAPPED_TO 관계 규모 추정 + 소규모 테스트 (Phase 3-0)
> - N7: 매칭 가중치 튜닝 프로세스 1일 추가 (Phase 3-4 완료 시)
> - N9: 잔여 배치 처리 현황 주간 리포트
> - v12 §2: CompanyContext 프롬프트 전면 반영 (S5, C3)
> - v12 M2: v19 canonical 관계명 (HAS_VACANCY, REQUIRES_ROLE, REQUIRES_SKILL, NEEDS_SIGNAL)
> - v12 S3: compute_skill_overlap 제거 확인 (매칭은 본 문서에서 별도 설계)
> - v12 C3: operating_model 진정성 체크 단순화 (키워드 수 + 구체적 맥락 규칙)
> - v12 §6: MappingFeatures 매핑 테이블 반영 (F1~F5 가중치)
>
> **데이터 확장**: Candidate-Only Graph → **+ Vacancy, CompanyContext, Organization(ER), MappingFeatures**
> **에이전트 역량 변화**: 후보자 검색만 → **매칭 스코어 기반 랭킹 + 기업 필터**
>
> **인력**: DE 1명 + MLE 1명 풀타임

---

## 3-0. 매칭 알고리즘 설계 문서 + ★ MAPPED_TO 규모 추정 (2일) — Week 16

### 설계 문서 내용 (v2 유지 + ★ v3 추가)

```
매칭 알고리즘 설계 (Phase 3 Day 1-2):

1. 피처 정의 (★ v12 §6 MappingFeatures 반영)
   ├─ F1 stage_match (25%): Organization.stage 비교 (v19 A4 매트릭스)
   ├─ F2 vacancy_fit (30%): scope_type + situational_signals 매칭
   ├─ F3 domain_fit (20%): Skill Jaccard + Industry 코드 매칭
   ├─ F4 culture_fit (10%): ★ v1 INACTIVE (Candidate 측 미추출, Company만)
   ├─ F5 role_fit (15%): seniority 매칭 + role_evolution
   └─ ★ v12 S3: compute_skill_overlap 삭제 확인

2. 스코어 계산 (v2 유지)
   ├─ 가중 합산: Σ(weight_i × score_i)
   ├─ 임계값: ≥ 0.4 → MAPPED_TO 관계 생성
   └─ 스코어 정규화: [0, 1]

3. ★ MAPPED_TO 규모 추정 (N3 신규)
   ├─ 소규모 테스트: JD 100건 × Person 1,000건 실행
   ├─ 임계값 0.4에서의 평균 매칭 수 측정
   ├─ 전체 규모 외삽: 10K JD × 평균 매칭 수
   ├─ 시나리오:
   │   - 보수적 (평균 50명/JD): 10K × 50 = 500K 관계
   │   - 기본 (평균 200명/JD): 10K × 200 = 2M 관계
   │   - 낙관적 (평균 500명/JD): 10K × 500 = 5M 관계
   ├─ Neo4j 영향 분석:
   │   - 500K 관계: Professional 8GB 충분
   │   - 2M 관계: Professional 16GB 권장
   │   - 5M 관계: Professional 32GB 필요, 임계값 0.5로 상향 검토
   └─ ★ 임계값 조정: 규모가 과도하면 0.4 → 0.5로 상향

4. 역방향 매칭 (v2 유지)
   └─ 2단계: 벡터 근사(100건) → 정밀 스코어링(Top-K)

5. ★ 가중치 튜닝 프로세스 (N7 신규)
   ├─ Phase 3-4 완료 후 1일 추가
   ├─ 50건 수동 검증 결과 분석
   ├─ 가중치 재조정 (grid search 또는 수동)
   ├─ 재조정 전/후 Top-10 적합도 비교
   └─ 결과 문서화
```

---

## 3-1. JD 파서 + Vacancy 노드 (1주) — Week 16 후반 ~ Week 17 전반

> v2와 동일.

### ★ v19 관계명 적용

```cypher
-- Vacancy + 관계 적재 (★ v19)
UNWIND $batch AS v
MERGE (vacancy:Vacancy {vacancy_id: v.vacancy_id})
SET vacancy += v.properties
WITH vacancy, v
MATCH (o:Organization {org_id: v.org_id})
MERGE (o)-[:HAS_VACANCY]->(vacancy)    // ★ v19

// REQUIRES_ROLE (★ v19)
UNWIND $role_rels AS r
MATCH (v:Vacancy {vacancy_id: r.vacancy_id})
MERGE (role:Role {title: r.role_title})
MERGE (v)-[:REQUIRES_ROLE]->(role)

// REQUIRES_SKILL (★ v19)
UNWIND $skill_rels AS r
MATCH (v:Vacancy {vacancy_id: r.vacancy_id})
MERGE (s:Skill {name: r.skill_name})
MERGE (v)-[:REQUIRES_SKILL]->(s)

// NEEDS_SIGNAL (★ v19)
UNWIND $signal_rels AS r
MATCH (v:Vacancy {vacancy_id: r.vacancy_id})
MERGE (sig:SituationalSignal {label: r.signal_label})
MERGE (v)-[:NEEDS_SIGNAL]->(sig)
```

---

## 3-2. CompanyContext 파이프라인 (2주) — Week 17-18

> ★ v12 §1~§2 전면 반영.

### CompanyContext 추출 (★ v12 프롬프트)

```python
# src/extractors/company_extractor.py — v3: v12 §1 전면 반영

async def extract_company_context(jd: dict, nice_info: dict, provider: LLMProvider) -> dict:
    """CompanyContext 생성: DB 직접 + NICE Rule + LLM 추출"""

    # Step 1: DB 직접 매핑 (LLM 비용 $0) — v12 §2.1
    direct_fields = {
        "company_name": jd.get("company_name"),
        "industry": lookup_industry(jd.get("skill_codes")),  # Tier 1 CI Lookup
        "tech_stack": normalize_skills(jd.get("skills")),     # Tier 2 정규화+임베딩
        "career_types": parse_career_types(jd.get("requirement")),
        "education_level": jd.get("education_level"),
        "designation": jd.get("designation"),
        "location": jd.get("work_condition", {}).get("location"),
        "salary_range": jd.get("work_condition", {}).get("salary"),
    }

    # Step 2: NICE Lookup (Rule 기반) — v12 §2.2
    stage_estimate = estimate_stage(
        employee_count=nice_info.get("employee_count"),
        revenue=nice_info.get("revenue"),
        founded_year=nice_info.get("founded_year"),
        industry_code=nice_info.get("industry_code"),
    )

    # Step 3: LLM 추출 (hiring_context, role_expectations, operating_model)
    # ★ v12 S5: structural_tensions 제외
    # ★ v12 C3: operating_model 단순 confidence 규칙
    llm_result = await provider.extract(
        build_company_prompt(jd, direct_fields, nice_info),
        CompanyContextExtraction
    )

    return {**direct_fields, "stage": stage_estimate, **llm_result}
```

### ★ v12 C3: operating_model 진정성 체크 단순화

```python
def validate_operating_model(facets: dict, evidence: list[str]) -> dict:
    """operating_model 각 facet 검증 — 구체적 맥락 유무만 판단"""
    validated = {}
    for facet in ["speed", "autonomy", "process"]:
        value = facets.get(facet)
        if value is None:
            validated[facet] = None
            continue

        # v12 C3: 구체적 맥락 부재 시 null
        # 예: "애자일 팀"만 단독 → speed = null
        # 예: "2주 스프린트로 빠르게 배포" → speed = 0.8
        has_specific_context = any(
            keyword in str(evidence)
            for keyword in ["주 스프린트", "리뷰 빈도", "CI/CD", "OKR", "주도적"]
        )

        if not has_specific_context:
            validated[facet] = None
        else:
            # confidence = min(0.60, 0.30 + count × 0.06)
            validated[facet] = value

    return validated
```

---

## 3-3. Organization ER + 한국어 특화 (2주) — Week 19-20

> v2와 동일.

---

## 3-4. MappingFeatures + MAPPED_TO + ★ 가중치 튜닝 (2주+1일) — Week 20-22

### 매칭 구현 (★ v12 §6 MappingFeatures 반영)

```python
# src/matching/scorer.py — v3: v12 §6 반영

@dataclass
class MatchWeights:
    """v12 §6 MappingFeatures 가중치"""
    stage_match: float = 0.25    # F1
    vacancy_fit: float = 0.30    # F2
    domain_fit: float = 0.20     # F3
    culture_fit: float = 0.10    # F4 (v1 INACTIVE, Company 측만)
    role_fit: float = 0.15       # F5

def compute_match_score_v3(candidate: dict, vacancy: dict, weights: MatchWeights) -> float:
    """v12 §6 기반 5-피처 매칭 스코어"""

    # F1: stage_match (★ v19 A4: 4×4 STAGE_SIMILARITY 매트릭스)
    stage_score = stage_similarity_matrix[
        candidate.get("org_stage", "UNKNOWN")
    ].get(vacancy.get("org_stage", "UNKNOWN"), 0.5)

    # F2: vacancy_fit (scope_type + situational_signals)
    scope_match = 1.0 if candidate.get("scope_type") == vacancy.get("hiring_context_scope") else 0.5
    signal_overlap = jaccard_similarity(
        set(candidate.get("signals", [])),
        set(vacancy.get("needed_signals", []))
    )
    vacancy_score = 0.6 * scope_match + 0.4 * signal_overlap

    # F3: domain_fit (Skill + Industry)
    skill_score = jaccard_similarity(
        set(candidate.get("skills", [])),
        set(vacancy.get("required_skills", []))
    )
    industry_match = 1.0 if candidate.get("industry") == vacancy.get("industry") else 0.3
    domain_score = 0.7 * skill_score + 0.3 * industry_match

    # F4: culture_fit (★ v1 INACTIVE — Candidate 측 미추출)
    # Company의 operating_model만 있으므로 단순 0.5 기본값
    culture_score = 0.5

    # F5: role_fit (seniority + role_evolution)
    sen_diff = abs(SENIORITY_ORDER.get(candidate.get("seniority"), 2)
                   - SENIORITY_ORDER.get(vacancy.get("seniority"), 2))
    role_score = [1.0, 0.7, 0.3, 0.1, 0.0][min(sen_diff, 4)]

    # 가중 합산
    overall = (
        weights.stage_match * stage_score +
        weights.vacancy_fit * vacancy_score +
        weights.domain_fit * domain_score +
        weights.culture_fit * culture_score +
        weights.role_fit * role_score
    )

    return round(min(max(overall, 0), 1), 4)
```

### ★ N7: 매칭 가중치 튜닝 프로세스 (Phase 3-4 완료 후 1일)

```python
# src/matching/weight_tuner.py — N7 신규

def tune_weights(validation_results: list[dict], current_weights: MatchWeights) -> MatchWeights:
    """50건 검증 결과 기반 가중치 재조정"""

    # Step 1: 현재 가중치로 50건 스코어 계산
    current_scores = [compute_match_score_v3(r["candidate"], r["vacancy"], current_weights)
                     for r in validation_results]

    # Step 2: 수동 검증 결과 (적합/부적합/애매)와 상관관계 분석
    human_labels = [r["human_label"] for r in validation_results]  # 1.0/0.0/0.5
    correlation = pearsonr(current_scores, human_labels)

    # Step 3: Grid search (간단한 범위)
    best_weights = current_weights
    best_corr = correlation[0]

    for stage in [0.20, 0.25, 0.30]:
        for vacancy in [0.25, 0.30, 0.35]:
            for domain in [0.15, 0.20, 0.25]:
                role = 1.0 - stage - vacancy - domain - 0.10  # culture 고정 0.10
                if role < 0.05 or role > 0.30:
                    continue
                w = MatchWeights(stage, vacancy, domain, 0.10, role)
                scores = [compute_match_score_v3(r["candidate"], r["vacancy"], w)
                         for r in validation_results]
                corr = pearsonr(scores, human_labels)[0]
                if corr > best_corr:
                    best_corr = corr
                    best_weights = w

    print(f"Before: r={correlation[0]:.3f}, After: r={best_corr:.3f}")
    print(f"Tuned weights: {best_weights}")

    return best_weights
```

### ★ N9: 잔여 배치 처리 주간 리포트

```
Phase 3 주간 리포트 (매주 월요일):
  1. 잔여 배치 처리 현황
     - 총 대상: 600K
     - Phase 2 완료: xxx건 (xx%)
     - Phase 3 백그라운드 처리: xxx건 추가
     - 잔여: xxx건
  2. Phase 3 Batch API 할당
     - Phase 3 전용: 2 batch (최소)
     - 잔여 처리: 나머지
  3. 리소스 충돌 여부
     - Neo4j 커넥션 풀 사용률
     - Batch API 동시 활성 수
```

---

## 3-5. 통합 테스트 + Regression Test (Week 21-22, 병행)

> v2와 동일 + ★ v12 품질 메트릭 적용.

### 매칭 품질 검증 (★ v3 보강)

```
매칭 품질 기준:
  - 50건 수동 검증: 치명적 결함 0건
  - Top-10 적합도: 70%+
  - ★ 가중치 튜닝 후 상관관계: r > 0.4 (N7)
  - ★ MAPPED_TO 관계 수: 추정 범위 내 (N3)
```

---

## Phase 3 완료 산출물

```
□ ★ 매칭 알고리즘 설계 문서 (v2 유지 + N3 규모 추정)
  ├─ v12 §6 MappingFeatures 5-피처 반영
  ├─ ★ MAPPED_TO 규모 추정 결과 (N3)
  └─ ★ Neo4j 사이징 영향 분석

□ JD 파서 + Vacancy 노드
  └─ ★ v19 관계명: HAS_VACANCY, REQUIRES_ROLE, REQUIRES_SKILL, NEEDS_SIGNAL

□ CompanyContext 파이프라인
  ├─ ★ v12 §1 프롬프트 (S5 INACTIVE 제외)
  ├─ ★ v12 C3 operating_model 단순화
  └─ DB 직접 + NICE Rule + LLM 3단계

□ Organization ER (v2 유지)

□ MappingFeatures + MAPPED_TO
  ├─ ★ v12 §6 기반 5-피처 (F1~F5)
  ├─ ★ 가중치 튜닝 1일 완료 (N7)
  └─ 임계값 0.4 (N3 결과에 따라 조정)

□ GraphRAG API 확장
  ├─ /match/jd-to-candidates
  ├─ /match/candidate-to-jds
  └─ /companies/{org_id}

□ ★ 잔여 배치 처리 완료 확인 (N9)

□ 통합 테스트 + Regression Test
  ├─ 매칭 50건 수동 검증
  ├─ Top-10 적합도 70%+
  └─ ★ 가중치 튜닝 후 상관관계 r > 0.4
```

---

## 버퍼 1주 — Week 23

> v2와 동일 + ★ N9 최종 확인.

```
Week 23 활동:
  ├─ Phase 3 Go/No-Go 판정
  ├─ ★ 잔여 배치 처리 100% 완료 확인 (N9)
  ├─ ★ MAPPED_TO 관계 규모 최종 확인 (N3)
  ├─ 코드 정리 + 문서화
  ├─ 크롤링 법무 결론 최종 확인
  └─ Phase 4 크롤링 범위 확정
```
