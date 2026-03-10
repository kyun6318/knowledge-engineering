# Phase 3: 기업 정보 + 매칭 관계 (7주, Week 16-22)

> **목적**: JD 데이터와 기업 정보를 Graph에 추가하고, 후보자-공고 매칭 관계를 구축.
>
> **v1 대비 변경**:
> - 기간 6주→7주 (M3: Organization ER +1주)
> - 매칭 알고리즘 설계 문서 추가 (S5: Phase 3 초반 2일)
> - Organization ER: 1주→2주, 검수 500개→1,000개+, Rule+LLM 2단계
> - 계열사/사명변경 사전 Phase 2에서 사전 구축 (→ Phase 3-3에서 활용)
>
> **데이터 확장**: Candidate-Only Graph → **+ Vacancy, CompanyContext, Organization(ER), MappingFeatures**
> **에이전트 역량 변화**: 후보자 검색만 → **매칭 스코어 기반 랭킹 + 기업 필터**
>
> **인력**: DE 1명 + MLE 1명 풀타임

---

## 3-0. 매칭 알고리즘 설계 문서 (★ v2 신규, 2일) — Week 16 초반

> v1에서 부재했던 매칭 로직의 구체적 설계를 Phase 3 시작 전에 수립.

### 설계 문서 내용

```
매칭 알고리즘 설계 (Phase 3 Day 1-2):

1. 피처 정의
   ├─ 스킬 매칭: Jaccard 유사도 (집합 기반) + Cosine on embeddings (시맨틱)
   ├─ 경력 연수 매칭: 범위 기반 (±2년), 가중치 0.15
   ├─ 시니어리티 매칭: 동일 1.0, 인접 0.7, 2단계 차이 0.3
   ├─ 업종 매칭: KSIC 대분류 동일 1.0, 소분류 동일 0.5
   └─ 직무 매칭: Role 유사도 (embedding cosine)

2. 스코어 계산
   ├─ 가중 합산 (초기): w_skill*skill + w_exp*exp + w_sen*sen + w_ind*ind + w_role*role
   ├─ 가중치 초기값: skill=0.35, exp=0.15, sen=0.15, ind=0.15, role=0.20
   ├─ 임계값: overall_match_score ≥ 0.4 → MAPPED_TO 관계 생성
   └─ 스코어 정규화: Min-Max → [0, 1]

3. 역방향 매칭 (Candidate → Vacancy)
   ├─ Pre-computation: Person별 feature vector 캐싱
   ├─ 조회 시: Vector Search (vacancy_embedding → 근사 Top-K) + 정밀 스코어링
   └─ 전수 계산 대신 2단계: 벡터 근사(100건) → 정밀 스코어링(Top-K)

4. 검증 방법
   ├─ 매칭 쌍 50건 수동 검증 (적합/부적합/애매)
   ├─ Top-10 적합도: 70%+ 목표
   └─ Cohen's Kappa ≥ 0.6 (검수자 간 일치도, Phase 5에서)
```

---

## 3-1. JD 파서 + Vacancy 노드 (1주) — Week 16 후반 ~ Week 17 전반

> v1과 동일. Phase 2-1-7에서 초안 완료된 JD 파서를 프로덕션화.

---

## 3-2. CompanyContext 파이프라인 (2주) — Week 17-18

> v1과 동일. NICE DB + Rule + LLM 기반 CompanyContext 생성.

---

## 3-3. Organization ER + 한국어 특화 (★ 2주) — Week 19-20

> v1(1주)→v2(2주): 한국어 회사명 ER의 난이도를 반영하여 기간 확대.

### Week 19: Rule-based 1차 매칭 + 사전 구축

| # | 작업 | 담당 | 기간 |
|---|------|------|------|
| ER-1 | 회사명 정규화 (대소문자, (주), Inc 등) | DE | 1일 |
| ER-2 | 계열사/사명변경 사전 구축 (Phase 2에서 사전 조사) | DE | 1일 |
| ER-3 | Rule-based 1차 매칭 (정규화 + 사전 + Levenshtein) | DE | 2일 |
| ER-4 | 1차 매칭 결과 검수 (500개) | 공동 | 1일 |

### Week 20: LLM 2차 매칭 + 전수 검수

| # | 작업 | 담당 | 기간 |
|---|------|------|------|
| ER-5 | LLM 2차 매칭 (1차에서 미매칭/애매한 케이스) | MLE | 2일 |
| ER-6 | 전수 검수 확대 (1,000개+, 2%+) | 공동 | 2일 |
| ER-7 | ER 결과 Graph 반영 (Organization 노드 병합) | DE | 1일|

### 한국어 ER 난제 대응 (★ v2 보강)

```
Rule-based 1차 매칭 (정확도 우선):
  1. 정규화: (주), Inc, Co., Ltd 제거 + 공백/특수문자 정리
  2. 정확 매칭: 정규화 후 동일 문자열
  3. 사전 매칭: 계열사 사전, 사명변경 사전 활용
     - 삼성전자 = Samsung Electronics = SAMSUNG
     - (주)토스 = 비바리퍼블리카
     - 네이버 ≠ NHN (사명변경 이력, 시점 기반)
  4. 유사 매칭: Levenshtein ≤ 2 AND 길이 비율 ≥ 0.8

LLM 2차 매칭 (재현율 보완):
  - 1차에서 미매칭 건 중 "카카오" CONTAINS 패턴으로 후보 추출
  - LLM에 "이 두 회사는 같은 회사인가?" 판정 요청
  - 계열사 구분: "카카오" vs "카카오뱅크" → LLM이 "별개 법인" 판정
  - 비용: ~$5 (애매한 케이스 ~1,000건 × $0.005)

검수 규모 (v2: 500→1,000+):
  - 정확 매칭 결과: 200개 샘플 검수
  - 사전 매칭 결과: 300개 전수 검수
  - LLM 매칭 결과: 500개+ 전수 검수
  - 총 1,000개+ (50K Organization 중 2%+)
```

---

## 3-4. MappingFeatures + MAPPED_TO (2주) — Week 20-22

> 3-3(Week 19-20)과 1주 병렬 진행 가능.

### 매칭 구현 (★ v2: 설계 문서 기반)

```python
# src/matching/scorer.py — 3-0 설계 문서 기반 구현

from dataclasses import dataclass
import numpy as np

@dataclass
class MatchWeights:
    skill: float = 0.35
    experience: float = 0.15
    seniority: float = 0.15
    industry: float = 0.15
    role: float = 0.20

def compute_match_score(candidate: dict, vacancy: dict, weights: MatchWeights) -> float:
    """후보자-공고 매칭 스코어 계산 (가중 합산)"""

    # 스킬 매칭: Jaccard + Cosine 혼합
    skill_jaccard = jaccard_similarity(
        set(candidate["skills"]), set(vacancy["required_skills"])
    )
    skill_cosine = cosine_similarity(
        candidate["skill_embedding"], vacancy["skill_embedding"]
    )
    skill_score = 0.5 * skill_jaccard + 0.5 * skill_cosine

    # 경력 연수 매칭: 범위 기반
    exp_diff = abs(candidate["total_years"] - vacancy.get("preferred_years", 5))
    exp_score = max(0, 1 - exp_diff / 10)  # 10년 차이면 0

    # 시니어리티 매칭
    sen_map = {"JUNIOR": 0, "MID": 1, "SENIOR": 2, "LEAD": 3, "EXECUTIVE": 4}
    sen_diff = abs(sen_map.get(candidate["seniority"], 1) - sen_map.get(vacancy.get("seniority"), 1))
    sen_score = [1.0, 0.7, 0.3, 0.1, 0.0][min(sen_diff, 4)]

    # 업종 매칭: KSIC 코드
    ind_score = 1.0 if candidate.get("industry") == vacancy.get("industry") else 0.3

    # 직무 매칭: Role embedding cosine
    role_score = cosine_similarity(
        candidate.get("role_embedding", []), vacancy.get("role_embedding", [])
    )

    # 가중 합산
    overall = (
        weights.skill * skill_score +
        weights.experience * exp_score +
        weights.seniority * sen_score +
        weights.industry * ind_score +
        weights.role * role_score
    )

    return round(min(max(overall, 0), 1), 4)  # 정규화 [0, 1]

# MAPPED_TO 관계 생성 임계값
MATCH_THRESHOLD = 0.4
```

### MAPPED_TO 관계 배치 생성

```python
def create_mapped_to_relations(driver, matches: list[dict]):
    """매칭 결과 → MAPPED_TO 관계 배치 적재"""
    with driver.session() as session:
        session.run("""
            UNWIND $matches AS m
            MATCH (p:Person {candidate_id: m.candidate_id})
            MATCH (v:Vacancy {vacancy_id: m.vacancy_id})
            MERGE (p)-[r:MAPPED_TO]->(v)
            SET r.overall_match_score = m.score,
                r.feature_vector = m.features,
                r.loaded_batch_id = $batch_id,
                r.loaded_at = datetime()
        """, matches=matches, batch_id=f"match_{datetime.now().strftime('%Y%m%d')}")
```

---

## 3-5. 통합 테스트 + Regression Test (Week 21-22, 병행)

> v1과 동일. ★ v2 추가: 매칭 품질 검증 (Top-10 적합도 70%+)

---

## Phase 3 완료 산출물

```
□ ★ 매칭 알고리즘 설계 문서 (v2 신규)

□ JD 파서 + Vacancy 노드 (v1과 동일)

□ CompanyContext 파이프라인 (v1과 동일)

□ Organization ER (★ v2 확장)
  ├─ Rule-based 1차 + LLM 2차 (2단계)
  ├─ 계열사/사명변경 사전 구축
  ├─ 전수 검수 1,000개+ (2%+)
  └─ 기간: 2주 (v1: 1주)

□ MappingFeatures + MAPPED_TO (★ v2: 설계 기반)
  ├─ 5종 피처 (skill, exp, seniority, industry, role)
  ├─ 가중 합산 스코어
  ├─ 임계값 0.4 이상 관계 생성
  └─ 역방향 매칭 (Candidate → Vacancy)

□ GraphRAG API 확장 (Phase 3)
  ├─ /match/jd-to-candidates
  ├─ /match/candidate-to-jds
  └─ /companies/{org_id}

□ 통합 테스트 + Regression Test
  ├─ 매칭 50건 수동 검증
  └─ Top-10 적합도 70%+
```

---

## 버퍼 1주 — Week 23 (★ v2 신규)

> v1에는 없던 Phase 3-4 사이 버퍼. 번아웃 방지 + Phase 3 마무리 + Phase 4 준비.

```
Week 23 활동:
  ├─ Phase 3 Go/No-Go 판정
  ├─ 잔여 배치 처리 마무리 (Phase 2 잔여 20% 백그라운드 완료 확인)
  ├─ 코드 정리 + 문서화
  ├─ 크롤링 법무 결론 최종 확인
  └─ Phase 4 크롤링 범위 확정
```
