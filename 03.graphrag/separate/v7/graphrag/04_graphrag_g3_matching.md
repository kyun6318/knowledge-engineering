> **트리거**: S&F 산출물 D (JD + CompanyContext JSONL) PubSub 수신
> 

---

## W17: 매칭 설계 + MAPPED_TO 규모 추정 (N3)

```
매칭 알고리즘 설계 (2일):
  F1 stage_match (25%): Organization.stage 비교 (v19 A4)
  F2 vacancy_fit (30%): scope_type + situational_signals
  F3 domain_fit (20%): Skill Jaccard + Industry 코드
  F4 culture_fit (10%): v1 INACTIVE (기본값 0.5)
  F5 role_fit (15%): seniority + role_evolution

규모 추정 (N3):
  [v4] Phase 1(1K 적재 후) 시점에서 소규모 매칭 시뮬레이션 선행:
    JD 10건 × Person 1K -> 임계값 0.4에서 평균 매칭 수 실측
    실측 결과를 기반으로 전체 규모 외삽 후 Neo4j 티어 적합성 재검증
  Phase 3 본 시뮬레이션:
    JD 100건 × Person 1,000건 -> 임계값 0.4에서 평균 매칭 수 측정
  전체 외삽: 10K JD × 평균 매칭 수
  보수적: 500K 관계 (8GB 충분)
  기본: 2M 관계 (16GB 권장)
  낙관적: 5M 관계 (32GB 또는 임계값 0.5 상향)
```

## W17 후반: Vacancy 적재

```
-- PubSub로 S&F JD JSON 수신 -> Vacancy 적재 (v19)
UNWIND $batch AS v
MERGE (vacancy:Vacancy {vacancy_id: v.vacancy_id})
SET vacancy += v.properties
WITH vacancy, v
MATCH (o:Organization {org_id: v.org_id})
MERGE (o)-[:HAS_VACANCY]->(vacancy)

-- REQUIRES_ROLE, REQUIRES_SKILL, NEEDS_SIGNAL (v19)
```

## W18: Organization ER + 한국어 특화 (1.5주)

> 계열사 사전: 삼성/현대/SK/LG/롯데 초기 버전
S&F NICE 데이터 + BigQuery 조인
> 

## W19-20: 5-피처 스코어링 + MAPPED_TO

> **[v5] 구현 참조**: 아래 `compute_match_score()`는 `01.ontology/v24/03_mapping_features.md`의 F1~F5 정의를 **v1 MVP 간소화 구현**한 것이다. 정본은 01.ontology의 정의이며, 차이점은 다음과 같다:
> - F2 vacancy_fit: 정본은 VACANCY_SIGNAL_ALIGNMENT 매핑 테이블(strong/moderate/weak) 기반이나, 여기서는 scope_match + signal Jaccard 가중 평균으로 간소화
> - F3 domain_fit: 정본은 embedding similarity + industry code 계층 비교 + repeat bonus이나, 여기서는 Skill Jaccard + Industry 코드 단순 비교로 간소화
> - Phase 3 구현 시 정본 로직으로 교체하거나, 간소화 버전과의 품질 차이를 파일럿에서 비교 후 결정
> - **[v7] F2 추가 주의사항**: 간소화 구현의 scope_match는 candidate.scope_type(IC/LEAD/HEAD/FOUNDER)과 vacancy.vacancy_seniority(JUNIOR~HEAD)를 비교하는데, 이는 서로 다른 enum 공간이다. 정본 F2는 hiring_context(BUILD_NEW 등)와 situational_signals를 VACANCY_SIGNAL_ALIGNMENT 테이블 기반으로 매칭한다. v1 MVP에서는 Jaccard signal_overlap이 F2의 실질적 변별력을 제공한다.

```python
# src/matching/scorer.py - v12 §6
@dataclass
class MatchWeights:
    stage_match: float = 0.25
    vacancy_fit: float = 0.30
    domain_fit: float = 0.20
    culture_fit: float = 0.10
    role_fit: float = 0.15

def compute_match_score(candidate: dict, vacancy: dict, weights: MatchWeights) -> float:
    # F1: stage_match (v19 A4 STAGE_SIMILARITY)
    stage_score = stage_similarity_matrix[
        candidate.get("org_stage", "UNKNOWN")
    ].get(vacancy.get("org_stage", "UNKNOWN"), 0.5)

    # F2: vacancy_fit (scope_type + signals)
    scope_match = 1.0 if candidate.get("scope_type") == vacancy.get("vacancy_seniority") else 0.5
    signal_overlap = jaccard_similarity(
        set(candidate.get("signals", [])), set(vacancy.get("needed_signals", [])))
    vacancy_score = 0.6 * scope_match + 0.4 * signal_overlap

    # F3: domain_fit (Skill + Industry)
    skill_score = jaccard_similarity(
        set(candidate.get("skills", [])), set(vacancy.get("required_skills", [])))
    industry_match = 1.0 if candidate.get("industry") == vacancy.get("industry") else 0.3
    domain_score = 0.7 * skill_score + 0.3 * industry_match

    # F4: culture_fit (INACTIVE, 기본 0.5)
    culture_score = 0.5

    # F5: role_fit (seniority + role_evolution)
    sen_diff = abs(SENIORITY_ORDER.get(candidate.get("seniority"), 2)
                   - SENIORITY_ORDER.get(vacancy.get("seniority"), 2))
    role_score = [1.0, 0.7, 0.3, 0.1, 0.0][min(sen_diff, 4)]

    overall = (weights.stage_match * stage_score + weights.vacancy_fit * vacancy_score +
               weights.domain_fit * domain_score + weights.culture_fit * culture_score +
               weights.role_fit * role_score)
    return round(min(max(overall, 0), 1), 4)
```

### API 확장

```
/match/jd-to-candidates   -> Vacancy -> MAPPED_TO -> Person Top-K
/match/candidate-to-jds   -> Person -> MAPPED_TO -> Vacancy Top-K
/companies/{org_id}        -> Organization 상세
```

## W20: 가중치 튜닝

```python
# src/matching/weight_tuner.py
candidate_weights = [
    MatchWeights(0.25, 0.30, 0.20, 0.10, 0.15),  # 현재
    MatchWeights(0.20, 0.35, 0.20, 0.10, 0.15),  # vacancy_fit 강조
    MatchWeights(0.25, 0.25, 0.25, 0.10, 0.15),  # domain_fit 강조
    MatchWeights(0.30, 0.30, 0.15, 0.10, 0.15),  # stage_match 강조
]
# Top-10 결과 출력 -> 전문가 비교 -> 최적 선택
```

## W21-22: 통합 테스트 + Go/No-Go

[] 매칭 50건 수동 검증, Top-10 적합도 70%+

[] MAPPED_TO 규모 확인 (N3)

[] 가중치 튜닝 후 적합도 개선 확인