# Phase 3: 기업 정보 + 매칭 관계 (★ 6주, Week 17-22)

> **목적**: JD 데이터와 기업 정보를 Graph에 추가하고, 후보자-공고 매칭 관계를 구축.
>
> **v4 대비 변경**:
> - ★ v5 A1: JD 파서 0.5주의 **job-hub API 스펙 확정 여부 확인** 인지 사항 추가
>
> **v3 대비 변경 (v4에서 반영 완료)**:
> - R5: Phase 3 기간 7주 → 6주 (Phase 2에 1주 이동, 총 27주 유지)
> - O3: 가중치 튜닝 Grid search → 수동 비교 우선, 자동화 참고
> - 3-1 JD 파서 1주 → 0.5주 (단순 구조), 3-3 ER 2주 → 1.5주
>
> **6주 축소 근거**:
> - 3-1 JD 파서는 job-hub API에서 구조화된 JSON을 받으므로 파싱이 단순
> - 3-3 Organization ER의 계열사 사전 구축은 초기 버전에서 축소 가능
> - O3: 가중치 튜닝 자동화 코드 작성 시간 절감 (수동 비교로 대체)
>
> **데이터 확장**: Candidate-Only Graph → **+ Vacancy, CompanyContext, Organization(ER), MappingFeatures**
> **에이전트 역량 변화**: 후보자 검색만 → **매칭 스코어 기반 랭킹 + 기업 필터**
>
> **인력**: DE 1명 + MLE 1명 풀타임

---

## 3-0. 매칭 알고리즘 설계 문서 + MAPPED_TO 규모 추정 (2일) — Week 17

### 설계 문서 내용

```
매칭 알고리즘 설계 (Phase 3 Day 1-2):

1. 피처 정의 (v12 §6 MappingFeatures 반영)
   ├─ F1 stage_match (25%): Organization.stage 비교 (v19 A4 매트릭스)
   ├─ F2 vacancy_fit (30%): scope_type + situational_signals 매칭
   ├─ F3 domain_fit (20%): Skill Jaccard + Industry 코드 매칭
   ├─ F4 culture_fit (10%): v1 INACTIVE (Candidate 측 미추출, Company만)
   ├─ F5 role_fit (15%): seniority 매칭 + role_evolution
   └─ v12 S3: compute_skill_overlap 삭제 확인

2. 스코어 계산
   ├─ 가중 합산: Σ(weight_i × score_i)
   ├─ 임계값: ≥ 0.4 → MAPPED_TO 관계 생성
   └─ 스코어 정규화: [0, 1]

3. MAPPED_TO 규모 추정 (N3)
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
   └─ 임계값 조정: 규모가 과도하면 0.4 → 0.5로 상향

4. 역방향 매칭
   └─ 2단계: 벡터 근사(100건) → 정밀 스코어링(Top-K)

5. ★ v4 O3: 가중치 튜닝 프로세스 (수동 비교 우선)
   ├─ Phase 3-4 완료 후 1일 추가
   ├─ 50건 수동 검증 결과 분석
   ├─ ★ 수동 비교 우선: Top-10 결과를 3~4개 가중치 조합으로 전문가 비교
   ├─ 재조정 전/후 Top-10 적합도 비교
   ├─ (참고용) Grid search 코드는 유지하되 Gold Label 200건 이상 확보 시 활용
   └─ 결과 문서화
```

---

## 3-1. JD 파서 + Vacancy 노드 (★ 0.5주) — Week 17 후반

> ★ v4: 1주 → 0.5주. job-hub API에서 구조화된 JSON을 받으므로 파싱이 단순.
>
> ★ v5 A1: **Phase 3 시작 전 job-hub API 스펙 확정 여부 반드시 확인**.
> API가 구조화된 JSON이면 0.5주 실현 가능. 스펙 미확정 또는 비구조화(HTML 등)이면
> **즉시 0.5주→1주로 확장하고, 3-3 Organization ER에서 0.5주 흡수** (버퍼 1주 보존).
> Phase 3의 핵심 리스크이므로 Week 16(버퍼) Go/No-Go 시 확인 항목에 포함.

### v19 관계명 적용

```cypher
-- Vacancy + 관계 적재 (v19)
UNWIND $batch AS v
MERGE (vacancy:Vacancy {vacancy_id: v.vacancy_id})
SET vacancy += v.properties
WITH vacancy, v
MATCH (o:Organization {org_id: v.org_id})
MERGE (o)-[:HAS_VACANCY]->(vacancy)

// REQUIRES_ROLE (v19)
UNWIND $role_rels AS r
MATCH (v:Vacancy {vacancy_id: r.vacancy_id})
MERGE (role:Role {title: r.role_title})
MERGE (v)-[:REQUIRES_ROLE]->(role)

// REQUIRES_SKILL (v19)
UNWIND $skill_rels AS r
MATCH (v:Vacancy {vacancy_id: r.vacancy_id})
MERGE (s:Skill {name: r.skill_name})
MERGE (v)-[:REQUIRES_SKILL]->(s)

// NEEDS_SIGNAL (v19)
UNWIND $signal_rels AS r
MATCH (v:Vacancy {vacancy_id: r.vacancy_id})
MERGE (sig:SituationalSignal {label: r.signal_label})
MERGE (v)-[:NEEDS_SIGNAL]->(sig)
```

---

## 3-2. CompanyContext 파이프라인 (2주) — Week 18-19

> v12 §1~§2 전면 반영.

### CompanyContext 추출 (v12 프롬프트)

```python
# src/extractors/company_extractor.py — v12 §1 전면 반영

async def extract_company_context(jd: dict, nice_info: dict, provider: LLMProvider) -> dict:
    """CompanyContext 생성: DB 직접 + NICE Rule + LLM 추출"""

    # Step 1: DB 직접 매핑 (LLM 비용 $0) — v12 §2.1
    direct_fields = {
        "company_name": jd.get("company_name"),
        "industry": lookup_industry(jd.get("skill_codes")),
        "tech_stack": normalize_skills(jd.get("skills")),
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
    # v12 S5: structural_tensions 제외
    # v12 C3: operating_model 단순 confidence 규칙
    llm_result = await provider.extract(
        build_company_prompt(jd, direct_fields, nice_info),
        CompanyContextExtraction
    )

    return {**direct_fields, "stage": stage_estimate, **llm_result}
```

### v12 C3: operating_model 진정성 체크 단순화

```python
def validate_operating_model(facets: dict, evidence: list[str]) -> dict:
    """operating_model 각 facet 검증 — evidence 텍스트 길이 기반 단순 규칙

    ★ v4: v3의 키워드 하드코딩에서 evidence 길이 기반 규칙으로 단순화.
    v12 C3의 원래 의도대로 "evidence 텍스트가 충분하면 유효"로 판단.
    culture_fit 가중치 10%이므로 전체 스코어 영향 < 1%.
    """
    validated = {}
    MIN_EVIDENCE_LENGTH = 20  # 최소 20자 이상의 구체적 근거

    for facet in ["speed", "autonomy", "process"]:
        value = facets.get(facet)
        if value is None:
            validated[facet] = None
            continue

        # 해당 facet에 대한 evidence 텍스트 길이로 유효성 판단
        facet_evidence = " ".join(str(e) for e in evidence if facet.lower() in str(e).lower())
        if len(facet_evidence) < MIN_EVIDENCE_LENGTH:
            # 구체적 맥락 부재 시 null
            validated[facet] = None
        else:
            validated[facet] = value

    return validated
```

---

## 3-3. Organization ER + 한국어 특화 (★ 1.5주) — Week 19 후반 ~ Week 20

> ★ v4: 2주 → 1.5주. 계열사 사전은 주요 그룹(삼성/현대/SK/LG/롯데) 초기 버전으로 축소.

---

## 3-4. MappingFeatures + MAPPED_TO + ★ 가중치 수동 튜닝 (2주) — Week 20 후반 ~ Week 22

### 매칭 구현 (v12 §6 MappingFeatures 반영)

```python
# src/matching/scorer.py — v12 §6 반영

@dataclass
class MatchWeights:
    """v12 §6 MappingFeatures 가중치"""
    stage_match: float = 0.25    # F1
    vacancy_fit: float = 0.30    # F2
    domain_fit: float = 0.20     # F3
    culture_fit: float = 0.10    # F4 (v1 INACTIVE, Company 측만)
    role_fit: float = 0.15       # F5

def compute_match_score(candidate: dict, vacancy: dict, weights: MatchWeights) -> float:
    """v12 §6 기반 5-피처 매칭 스코어"""

    # F1: stage_match (v19 A4: 4×4 STAGE_SIMILARITY 매트릭스)
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

    # F4: culture_fit (v1 INACTIVE — Candidate 측 미추출, 기본값 0.5)
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

### ★ v4 O3: 매칭 가중치 튜닝 — 수동 비교 우선

```python
# src/matching/weight_tuner.py — v4 O3: 수동 비교 우선, Grid search 참고용

def tune_weights_manual(validation_results: list[dict], current_weights: MatchWeights) -> MatchWeights:
    """50건 검증 결과 기반 가중치 재조정 — 수동 비교 방식

    ★ v4 O3 변경:
    v3의 Grid search 27개 조합 자동 탐색 → 수동 3~4개 조합 비교로 변경.
    50건 규모에서 Pearson r 차이 0.01~0.02는 통계적으로 무의미하므로,
    전문가가 Top-10 결과를 직접 비교하는 것이 더 신뢰도 높음.
    Grid search 코드는 Gold Label 200건 이상 확보 시(Phase 5) 활용.
    """

    # Step 1: 현재 가중치로 50건 스코어 계산
    human_labels = [r["human_label"] for r in validation_results]  # 1.0/0.0/0.5

    # Step 2: 전문가가 선정한 3~4개 후보 가중치 조합 비교
    candidate_weights = [
        current_weights,                                          # 현재
        MatchWeights(0.20, 0.35, 0.20, 0.10, 0.15),            # vacancy_fit 강조
        MatchWeights(0.25, 0.25, 0.25, 0.10, 0.15),            # domain_fit 강조
        MatchWeights(0.30, 0.30, 0.15, 0.10, 0.15),            # stage_match 강조
    ]

    # Step 3: 각 조합별 Top-10 결과 출력 → 전문가 비교
    for i, w in enumerate(candidate_weights):
        scores = [compute_match_score(r["candidate"], r["vacancy"], w)
                 for r in validation_results]
        # Top-10 적합도 비교: 전문가가 직접 판단
        top10_indices = sorted(range(len(scores)), key=lambda x: scores[x], reverse=True)[:10]
        top10_labels = [human_labels[j] for j in top10_indices]
        top10_precision = sum(1 for l in top10_labels if l >= 0.5) / 10
        print(f"Weights {i}: Top-10 precision={top10_precision:.1%}, weights={w}")

    # Step 4: 전문가가 최적 조합 선택 (코드가 아닌 사람이 결정)
    selected_index = int(input("Select best weights (0-3): "))
    return candidate_weights[selected_index]


# ── 참고용: Grid search (Gold Label 200건 이상 확보 시 활용) ──
# def tune_weights_grid(validation_results, current_weights):
#     """200건+ Gold Label 확보 후 Phase 5에서 검토"""
#     # ... v3의 Grid search 코드 (27개 조합)
#     pass
```

### N9: 잔여 배치 처리 주간 리포트

```
Phase 3 주간 리포트 (매주 월요일):
  1. 잔여 배치 처리 현황
     - 총 대상: 600K
     - Phase 2 완료: xxx건 (xx%)
     - Phase 3 백그라운드 처리: xxx건 추가
     - 잔여: xxx건
  2. Phase 3 Batch API 할당
     - Phase 3 전용: 2~3 batch (최소)
     - 잔여 처리: 나머지
  3. 리소스 충돌 여부
     - Neo4j 커넥션 풀 사용률
     - Batch API 동시 활성 수
```

---

## 3-5. 통합 테스트 + Regression Test (Week 21-22, 병행)

> v3와 동일 + v12 품질 메트릭 적용.

### 매칭 품질 검증

```
매칭 품질 기준:
  - 50건 수동 검증: 치명적 결함 0건
  - Top-10 적합도: 70%+
  - ★ v4 O3: 가중치 수동 튜닝 후 Top-10 적합도 개선 확인
  - MAPPED_TO 관계 수: 추정 범위 내 (N3)
```

---

## Phase 3 완료 산출물

```
□ 매칭 알고리즘 설계 문서
  ├─ v12 §6 MappingFeatures 5-피처 반영
  ├─ MAPPED_TO 규모 추정 결과 (N3)
  └─ Neo4j 사이징 영향 분석

□ JD 파서 + Vacancy 노드 (★ v4: 0.5주)
  └─ v19 관계명: HAS_VACANCY, REQUIRES_ROLE, REQUIRES_SKILL, NEEDS_SIGNAL

□ CompanyContext 파이프라인
  ├─ v12 §1 프롬프트 (S5 INACTIVE 제외)
  ├─ ★ v4: operating_model evidence 길이 기반 검증 (v12 C3 원래 의도)
  └─ DB 직접 + NICE Rule + LLM 3단계

□ Organization ER (★ v4: 1.5주, 주요 그룹 초기 버전)

□ MappingFeatures + MAPPED_TO
  ├─ v12 §6 기반 5-피처 (F1~F5)
  ├─ ★ v4 O3: 가중치 수동 튜닝 완료 (Grid search는 Phase 5 참고용)
  └─ 임계값 0.4 (N3 결과에 따라 조정)

□ GraphRAG API 확장
  ├─ /match/jd-to-candidates
  ├─ /match/candidate-to-jds
  └─ /companies/{org_id}

□ 잔여 배치 처리 완료 확인 (N9)

□ 통합 테스트 + Regression Test
  ├─ 매칭 50건 수동 검증
  ├─ Top-10 적합도 70%+
  └─ ★ v4: 가중치 수동 튜닝 후 적합도 개선 확인
```

---

## 버퍼 1주 — Week 23

```
Week 23 활동:
  ├─ Phase 3 Go/No-Go 판정
  ├─ 잔여 배치 처리 100% 완료 확인 (N9)
  ├─ MAPPED_TO 관계 규모 최종 확인 (N3)
  ├─ 코드 정리 + 문서화
  ├─ 크롤링 법무 결론 최종 확인
  └─ Phase 4 크롤링 범위 확정
```
