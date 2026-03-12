# v12 온톨로지 스키마 리뷰

> 리뷰 대상: 4개 문서
> - `ontology/schema/v12/00_data_source_mapping.md` (~880줄)
> - `ontology/schema/v12/02_v4_amendments.md` (~220줄)
> - `ontology/schema/v12/05_evaluation_strategy.md` (v11에서 변경 없음)
> - `ontology/schema/v12/06_crawling_strategy.md` (v11에서 변경 없음)
>
> 리뷰 기준: v11 스키마, 데이터 분석 v2.1, v10 리뷰 기준 연속
>
> 리뷰일: 2026-03-10

---

## 1. 전체 평가

v12는 v11.1까지 **추정치에 의존**하던 데이터 소스 매핑을 **실측 데이터(v2.1 분석 결과)**로 전면 교체한 버전이다. 설계 결정의 근거가 추측에서 실증으로 전환된 점에서 의미가 크다. 특히 fill rate 실측치, 정규화 선행 과제 식별, 4단계 구현 로드맵은 파일럿 착수의 실질적 기반을 제공한다.

| 평가 영역 | v11 점수 | v12 점수 | 변화 | 코멘트 |
|---|---|---|---|---|
| CompanyContext 완성도 | 4.5 | **4.5** | 0 | 01 문서 변경 없음 |
| CandidateContext 완성도 | 4.5 | **4.7** | +0.2 | Person 보강 속성, CareerDescription 제약 반영, duration_months 계산 로직 |
| MappingFeatures 완성도 | 4.5 | **4.6** | +0.1 | F1~F5 예상 ACTIVE 비율 실측 기반 보정 |
| Graph Schema 완성도 | 4.7 | **4.7** | 0 | 04 문서 변경 없음 (Person 속성 추가는 차기) |
| Data Source Mapping | 4.5 | **4.8** | +0.3 | 실측 fill rate, 정규화 과제, 구현 로드맵 추가 |
| Evaluation Strategy | 4.9 | **4.9** | 0 | 변경 없음 |
| Crawling Strategy | 4.5 | **4.5** | 0 | 변경 없음 |
| 문서 간 정합성 | 4.5 | **4.6** | +0.1 | 00 문서가 02~04의 갭을 보완, 단 인라인 반영은 미완 |
| **종합** | **4.6** | **4.7** | +0.1 | 실측 데이터 기반 설계의 신뢰도 향상. 구현 착수 가능 |

---

## 2. 우수한 부분 (5건)

### S-1. 실측 fill rate 전면 교체 — §6.1

v11의 추정치("positionTitleCode 30~40%")가 실측치("29.45%")로 교체되었다. 모든 필드에 대해 출처와 규모(레코드 수)가 명시되어 설계 결정의 추적성이 확보되었다.

### S-2. CareerDescription FK 부재 제약 — §3.2 D4

`career_id` FK 없음이라는 치명적 제약을 명시하고, LLM 기반 career 귀속 전략을 정의한 점이 우수하다. 이 제약이 없었다면 구현 시 Outcome 추출에서 혼란이 발생했을 것이다.

### S-3. 서비스 풀 필터링 — §3.1 D6

전체 8M → PUBLIC+COMPLETED 5.5M → HIGH+PREMIUM 3.2M의 단계적 필터링이 명확하다. 파일럿과 운영의 데이터 범위를 사전 정의한 점이 좋다.

### S-4. 정규화 선행 과제 5건 — §7

구현 전 필수 데이터 정제 과제를 난이도/영향 범위와 함께 정리했다. 특히 days_worked 100% 제로 → 직접 계산이라는 단순하지만 치명적인 과제를 최우선(Phase 1-1)으로 배치한 점이 적절하다.

### S-5. 4단계 구현 로드맵 — §8

Phase 1~4의 의존성 체인이 명확하다. Phase 1 정제 → Phase 2 핵심 노드 → Phase 3 LLM 추출 → Phase 4 기업측+매핑의 순서가 논리적이다.

---

## 3. 개선 필요 사항 — 긴급 (2건)

### C-1. 04_graph_schema Person 노드 미갱신

00_data_source_mapping §3.5에서 Person 보강 속성(gender, age, career_type, freshness_weight, education_level)을 정의했으나, 04_graph_schema(v10)의 Person 노드 스키마에는 반영되지 않았다. 두 문서 간 불일치가 존재한다.

**권장**: v13에서 04_graph_schema의 Person 노드에 해당 속성을 추가하거나, v12 내에서 즉시 반영.

### C-2. industry_code_match 함수의 코드 타입 혼용

§4.1 `compute_industry_code_match()`에서 `company_industry_codes`는 INDUSTRY 타입인데, `candidate_career_codes`는 JOB_CLASSIFICATION_SUBCATEGORY 타입으로 비교한다. 산업 코드와 직무 분류 코드는 **다른 코드 체계**이므로, 직접 비교(code == r_code)가 성립하지 않을 수 있다.

**권장**: company 측은 INDUSTRY 코드, candidate 측은 workcondition.industryCodes (INDUSTRY_SUBCATEGORY)를 사용하거나, 두 코드 체계 간 매핑 로직을 명시.

---

## 4. 개선 필요 사항 — 비긴급 (6건)

### N-1. 01~04 통합판 문서 v12 미갱신

v12의 변경 사항은 00_data_source_mapping에 집중되어 있고, 01_company_context, 02_candidate_context, 03_mapping_features, 04_graph_schema는 v10 통합판 그대로이다. 정본(source of truth)이 분산되어 있으므로, 독자가 최신 설계를 파악하려면 00 + v10 통합판을 교차 참조해야 한다.

**권장**: v13에서 01~04 통합판에 v12 변경 사항을 인라인 반영하여 정본을 단일화.

### N-2. freshness_weight 계산의 경계값 검증

§3.5의 freshness_weight 계산에서 90일/1년/3년/5년 경계값은 실측 분포(90일 활성 13.9%, 반감기 31.5개월)에 기반하지만, 가중치 값(1.0/0.9/0.7/0.5/0.3)은 경험적 설정이다. 파일럿에서 실제 매칭 품질과의 상관관계를 검증해야 한다.

**권장**: Phase 3 LLM 추출 완료 후, freshness_weight와 매칭 정확도의 상관 분석 수행.

### N-3. 스킬 20개 캡의 영향 미분석

§1.3에서 172K 이력서가 정확히 20개 스킬을 가진다는 점을 "입력 상한 존재 추정"으로만 기재했다. 20개 캡이 실제로 존재한다면, 스킬 데이터의 completeness에 체계적 편향이 존재한다.

**권장**: 20개 캡 존재 시, 해당 이력서의 스킬 매칭 confidence에 -0.05 보정 적용을 검토.

### N-4. SOFT_SKILL 필터링 전략 미정의

SOFT_SKILL TOP 10의 60%가 "성실성", "긍정적" 같은 범용 특성이라는 실측이 있으나, 매칭에서 이를 어떻게 처리할지 전략이 없다.

**권장**: SOFT_SKILL은 매칭 스코어 계산에서 제외하거나, 가중치를 대폭 하향(0.1x)하는 규칙 추가.

### N-5. job-hub 상세 분석 미완

§6.2에서 job-hub 필드 가용성이 여전히 "예상 fill rate"로 표기되어 있다. resume-hub 수준의 실측 분석이 필요하다.

**권장**: Phase 4-1에서 job-hub 분석을 반드시 수행하고, Vacancy 노드의 실측 fill rate를 v13에 반영.

### N-6. Education 불일치 35.6%의 처리 전략

§3.5에서 `education.schoolType`을 진실 소스로 지정했으나, 불일치 35.6%에 대한 구체적 처리 로직(예: 로깅만? 자동 보정?)이 없다.

**권장**: 불일치 시 education.schoolType을 채택하되, 불일치 플래그를 Person 노드 속성으로 보존.

---

## 5. 과도한 부분 (1건)

### E-1. 00_data_source_mapping의 비대화

00_data_source_mapping.md가 ~880줄로, 원래 "매핑 가이드" 목적을 넘어 정규화 과제(§7), 구현 로드맵(§8), 사용 불가 필드(§9)까지 포함하고 있다. 문서의 책임 범위가 과도하게 넓어졌다.

**권장**: §7(정규화 과제)과 §8(구현 로드맵)은 별도 문서(`07_implementation_plan.md`)로 분리하는 것을 v13에서 검토.

---

## 6. 미해결 이슈 (v11 이월)

| # | 이슈 | 원래 버전 | 상태 |
|---|---|---|---|
| L-1 | amendments 파일 폐기/축소 | v9 | **미반영** — A8만 실질 내용, A1~A7/A9 이관 완료. A10 추가로 오히려 악화 |
| L-2 | 05 가상 데이터 수치 마스킹 | v9 | **미반영** — 비긴급 |
| L-3 | 01 인라인 Python 코드 표/서술 대체 | v9 | **미반영** — 비긴급 |
| L-4 | F4 ALIGNMENT_LOGIC 전체 매트릭스 | v9 | **미반영** — v2 범위 |
| L-5 | E2E 오류 전파 맵 설계 | v9 | **미반영** — v1.1 범위 |
| L-6 | 버전 넘버링 체계 정리 | v9 | **미반영** — 문서 내부(v8 통합판), 폴더(v12), amendments 간 번호 불일치 |

---

## 7. v12 총평 및 다음 단계 권장

### 총평

v12는 "설계의 실증화"라는 명확한 목표를 달성했다. 추정치에서 실측치로의 전환은 파일럿 착수의 필수 전제였으며, 정규화 선행 과제와 구현 로드맵은 즉시 실행 가능한 수준으로 구체화되었다. 단, 변경 범위가 00_data_source_mapping에 집중되어 01~04 통합판과의 정합성 유지가 과제로 남았다.

### v13 권장 사항 우선순위

| 우선순위 | 항목 | 근거 |
|---|---|---|
| **파일럿 전 필수** | C-1: 04_graph_schema Person 노드 갱신 | 구현 시 스키마 불일치 발생 |
| **파일럿 전 필수** | C-2: industry_code_match 코드 타입 혼용 수정 | 잘못된 매칭 로직 |
| 파일럿 중 검토 | N-2: freshness_weight 경계값 검증 | 파일럿 데이터로 검증 가능 |
| 파일럿 중 검토 | N-4: SOFT_SKILL 필터링 전략 | 매칭 품질에 직접 영향 |
| 비긴급 | N-1: 01~04 통합판 v12 반영 | 문서 정합성 (기능 영향 없음) |
| 비긴급 | N-5: job-hub 상세 분석 | Phase 4 범위 |
| 비긴급 | E-1: 00 문서 분리 (구현 로드맵) | 문서 구조 개선 |
