# v13 Schema Review

> 리뷰 일시: 2026-03-10
> 리뷰 대상: `01.ontology/results/schema/v13/` 전체 8개 문서
> 리뷰 기준: README.md 방향성 일치, 실현 가능성/타당성, 과도한 설계 vs 부족한 설계

---

## 1. 종합 평가

### 1.1 README 방향성과의 일치도: **높음 (9/10)**

README에서 정의한 6개 핵심 개념(CompanyContext, CandidateContext, MappingFeatures, Graph Schema, 평가 전략, 크롤링 전략)이 v13에서 모두 충실하게 구현되어 있다. 특히:

- **독립성 원칙** 준수: CompanyContext/CandidateContext가 서로 독립적으로 생성되는 구조 유지
- **Evidence-first** 원칙: 모든 문서에 걸쳐 Evidence 구조가 일관되게 적용
- **부분 완성 허용**: Graceful Degradation이 체계적으로 설계됨
- **Taxonomy 고정**: SituationalSignal 14개, TensionType 8개 등 고정 분류 체계 유지
- **데이터 소스 계층화**: Tier 체계와 confidence ceiling이 잘 정의됨

**미흡 1건**: README에서 "v10/" 기준으로 문서 구조를 설명하고 있으나, 실제 최신은 v13이다. README 업데이트 필요.

### 1.2 전체 성숙도 평가

v13은 v4 원본에서 출발하여 10회 이상의 반복 리뷰를 거치며 상당히 정교해진 상태이다. 특히 v12에서 **실측 데이터(8M 이력서, 120M 레코드)**를 반영하여 설계를 검증한 것은 매우 큰 진전이다. 다만 반복 리뷰 과정에서 문서 간 참조 관계가 복잡해져 가독성이 저하된 부분이 있다.

---

## 2. 문서별 상세 리뷰

### 2.1 `00_data_source_mapping.md` — 데이터 소스 매핑

#### 강점
- **실측 데이터 기반 설계**: v12에서 추정치를 실측치로 전면 교체한 것은 설계 신뢰도를 크게 높임
- **3-Tier 비교 전략**: 정규화 적합/경량 정규화+임베딩/임베딩 전용으로 분리한 것은 현실적이고 타당
- **정규화 선행 과제 식별**: days_worked, 회사명, 스킬, 전공명 등 구현 전 필수 과제를 명확히 정리
- **4단계 구현 로드맵**: Phase 1(데이터 정제) → Phase 4(매핑)까지 의존성 기반 순서 정의

#### 과도한 설계
- **[O-1] 임베딩 비교 batch 구현 코드 (1.5절)**: O(n*m) brute-force cosine similarity 구현이 포함되어 있으나, 실제 서비스에서는 ANN 인덱스를 사용할 것이므로 pseudo-code로 충분. 구현 디테일은 이 문서의 범위를 넘어감
- **[O-2] Person 보강 속성 중 gender/age**: 매칭 점수에 사용 금지라고 명시했지만, 편향 모니터링만을 위해 그래프 노드에 저장하는 것은 개인정보 관점에서 리스크. 별도 분석 테이블에서 관리하는 것이 더 적절

#### 부족한 설계
- **[U-1] job-hub 데이터 상세 분석 부재**: resume-hub는 실측 분석이 완료되었으나, job-hub는 "Phase 4-1에서 수행 예정"으로 미완. company 측 데이터 품질 없이 CompanyContext 설계가 확정된 상태는 리스크
- **[U-2] 스킬 정규화의 구체적 임베딩 threshold 검증 부재**: 임베딩 유사도 threshold 0.80/0.85를 설정했으나, 실제 스킬 쌍에 대한 검증 데이터가 없음. "Python" vs "파이썬" 같은 기본 케이스의 similarity 분포 분석이 필요
- **[U-3] CareerDescription FK 부재 대응의 LLM 정확도 추정 부재**: career_id 없이 LLM이 텍스트 컨텍스트로 outcome을 career에 귀속하는 전략을 제시했으나, 이 귀속의 예상 정확도에 대한 추정이 없음

#### 타당성 이슈
- **[V-1] `compute_industry_code_match()` (v13 C-2 수정)**: candidate 측을 INDUSTRY_SUBCATEGORY로 변경한 것은 올바르나, candidate industryCodes가 **66% 빈배열**인 상황에서 이 함수의 실효성이 제한적. PastCompanyContext 역참조 보조 소스에 과도하게 의존하게 됨

---

### 2.2 `01_company_context.md` — 기업 맥락

#### 강점
- **stage_estimate 추정 로직**이 Rule-based primary + LLM fallback으로 명확하게 설계됨
- **operating_model facets**의 광고성 필터링 규칙이 현실적
- **structural_tensions 8개 taxonomy**가 잘 정의되고 배타성 가이드까지 제공
- **의도적 제외(CompanyTalentSignal)** 명문화가 설계 원칙에 부합

#### 과도한 설계
- **[O-3] structural_tensions 8개 taxonomy**: v1에서 이 필드가 **null 70%+ 예상**이라고 명시하면서도 8개 taxonomy와 배타성 가이드, related_tensions 구조까지 정의한 것은 과도. v1에서는 3-4개 핵심 유형만 정의하고 v1.1에서 확장하는 것이 효율적
- **[O-4] T4 Tier ceiling 예외 규칙**: funding과 performance에 대한 카테고리별 ceiling 예외가 0.05~0.10 차이밖에 안 되는 미세 조정. v1에서는 일괄 0.55 적용으로 충분하고, 파일럿 후 분화해도 늦지 않음

#### 부족한 설계
- **[U-4] company_profile의 NICE 의존도가 너무 높음**: founded_year, employee_count, revenue_range 모두 NICE 단일 소스 의존. NICE 데이터의 갱신 주기/정확도에 대한 언급이 없음. NICE 데이터가 outdated된 경우의 처리 전략 필요
- **[U-5] vacancy scope_type 추출의 LLM 의존도**: BUILD_NEW/SCALE_EXISTING/RESET/REPLACE 분류가 JD 텍스트의 LLM 추출에 전적으로 의존. 이 분류의 예상 정확도/일관성에 대한 추정이 없음

---

### 2.3 `02_candidate_context.md` — 후보 맥락

#### 강점
- **Experience 구조 설계**가 실측 데이터와 잘 정합됨 (fill rate 주석 포함)
- **ScopeType → Seniority 변환 규칙**이 명확하고 경력 연수 기반 세분화가 현실적
- **SituationalSignal 14개 taxonomy**가 JD의 vacancy scope_type과 매핑되어 매칭의 핵심 연결고리 역할
- **v13에서 CareerDescription FK 부재 제약을 명시적으로 반영**한 것은 실무적으로 중요한 설계 결정

#### 과도한 설계
- **[O-5] PastCompanyContext의 estimated_stage_at_tenure**: 현재 시점 NICE 데이터로 과거 재직 시점의 stage를 추정하는 것은 정확도가 매우 낮음 (문서 자체도 인정). confidence가 years_gap에 따라 급격히 하락하는 구조인데, 대부분의 경력이 2-5년 전이라면 실효성이 의문
- **[O-6] WorkStyleSignals 구조**: autonomy_preference, process_tolerance, experiment_orientation 3개 차원이 정의되어 있으나 v1에서 "대부분 null"이 예상됨. 구조 정의는 하되, MappingFeatures F4(culture_fit)에서 이를 사용하는 로직까지 구현하는 것은 과도

#### 부족한 설계
- **[U-6] 이력서 텍스트 품질 편차 대응 부재**: workDetails 중앙값 96자, CareerDescription 중앙값 527자로 텍스트 길이 편차가 큼. 짧은 텍스트(50자 미만)에서의 LLM 추출 품질 저하에 대한 대응 전략이 없음
- **[U-7] 경력 순서(시간순) 보장 로직 부재**: Career[] 배열의 정렬 순서가 보장되는지, 시간 역순인지에 대한 명시가 없음. role_evolution 추출 시 시간순이 중요한데 이 전제가 검증되지 않음

---

### 2.4 `03_mapping_features.md` — 매칭 피처

#### 강점
- **5개 피처의 계산 로직이 pseudo-code로 명확히 정의됨**
- **Graceful Degradation** 패턴이 일관되게 적용 (필수 입력 null이면 INACTIVE)
- **overall_match_score의 confidence 이중 감쇠 설계 의도**가 v8에서 명시적으로 문서화됨
- **DS/MLE 소비 인터페이스(BigQuery 테이블 + SQL 예시)**가 실용적

#### 과도한 설계
- **[O-7] F4 culture_fit의 전체 계산 로직**: ACTIVE 비율 <10% 예상인 피처에 대해 FACET_TO_WORKSTYLE 매핑, ALIGNMENT_LOGIC 딕셔너리, 전체 계산 함수까지 구현한 것은 과도. v1에서는 "INACTIVE" 상태 처리만 정의하고, 계산 로직은 v2에서 데이터 확보 후 설계하는 것이 효율적
- **[O-8] ROLE_PATTERN_FIT 매트릭스**: (required_seniority, role_pattern) 조합별 fit_score를 하드코딩했으나, 이 값들의 근거가 없고 캘리브레이션 계획도 stage_match(F1)에만 존재. F5에도 동일한 캘리브레이션 계획이 필요

#### 부족한 설계
- **[U-8] 피처 간 상관관계 분석 부재**: stage_match와 vacancy_fit가 서로 상관이 높을 가능성이 있음 (같은 stage 경험 = 유사한 situational signal). 피처 간 다중공선성이 overall_score에 미치는 영향 분석이 없음
- **[U-9] FEATURE_WEIGHTS의 근거 부재**: stage_match 0.25, vacancy_fit 0.30 등 가중치의 설정 근거가 없음. "전문가 판단" 기반인지, 어떤 원칙으로 배분했는지 명시 필요
- **[U-10] 처리 시간 제약 미고려**: "1건 매핑 < 30초" 목표가 있으나, F3 domain_fit의 임베딩 계산 + F2의 LLM scoring 등을 합산한 예상 소요 시간 분석이 없음

---

### 2.5 `04_graph_schema.md` — Neo4j 그래프 스키마

#### 강점
- **9종 노드 + 관계 정의**가 명확하고, 후보/기업/매칭 3개 서브그래프로 구분이 깔끔
- **SituationalSignal을 공유 노드로 설계**한 것은 "같은 상황 경험 후보 탐색" 쿼리를 가능하게 하는 핵심 설계
- **Vector + Graph 하이브리드 쿼리(Q3)**가 실용적
- **v13에서 Industry 노드를 code-hub 기반으로 정합**한 것은 00_data_source_mapping과의 일관성 확보

#### 과도한 설계
- **[O-9] Organization 노드의 크롤링 보강 속성(v10)**: product_description, market_segment, latest_funding_round 등이 v1에서는 모두 null인데 스키마에 미리 정의. nullable로 선언하는 것은 좋으나, 문서에서 이 속성들의 설명에 할애하는 분량이 과도
- **[O-10] v2 로드맵의 Company 간 관계 4종**: COMPETES_WITH, INVESTED_BY, ACQUIRED, PARTNERED_WITH가 v1 범위 밖으로 명시되어 있으면서도 상세 설명이 포함됨. 로드맵 테이블 한 줄이면 충분

#### 부족한 설계
- **[U-11] 노드/엣지 규모 추정 부재**: 서비스 풀 ~3.2M 이력서 기준으로 Person 노드 ~3.2M, Chapter 노드 ~18M (경력 보유자 기준), Skill 노드 ~100K 등의 규모 추정과 이에 따른 Neo4j 성능/비용 계획이 없음
- **[U-12] 인덱스 전략 부재**: person_id, org_id 등에 대한 Neo4j 인덱스 정의가 없음. Q1~Q5 쿼리의 예상 성능을 보장하려면 인덱스 전략이 필수
- **[U-13] 데이터 동기화 전략 부재**: BigQuery(서빙)와 Neo4j(그래프 탐색) 간 데이터 동기화 주기/방법이 정의되지 않음

---

### 2.6 `05_evaluation_strategy.md` — 평가 전략

#### 강점
- **실험 설계가 매우 체계적**: A/B/(B') 3가지 방법 비교, 통제 변수 명시, 블라인드 처리
- **사전 검정력 분석(Power Analysis)**이 추가되어 통계적 타당성 확보
- **의사결정 트리**가 4가지 Case로 사전 정의되어 결과에 따른 방향이 명확
- **적응적 표본 크기 결정 프로토콜**이 현실적

#### 과도한 설계
- **[O-11] 10절 가상 실험 데이터**: 실험 전 예상 구조를 보여주기 위한 가상 데이터가 ~100줄에 걸쳐 포함됨. 경고 배너가 있지만, 이후 실제 데이터로 교체되지 않으면 혼란 유발. 스키마 정의만으로 충분
- **[O-12] Step별 함수 시그니처**: v8에서 과도한 pseudo-code를 축소했다고 하지만, 여전히 7개 Step의 함수 시그니처+핵심 로직 주석이 포함됨. 실험 설계 문서에서는 워크플로우 다이어그램과 핵심 파라미터만으로 충분

#### 부족한 설계
- **[U-14] 후보 풀 ~500명의 선정 기준 부재**: "동일 후보 풀 (~500명)"이라고만 되어 있고, 어떤 기준으로 500명을 선정하는지 정의가 없음. 무작위? 기존 매칭 이력? 이에 따라 실험 결과가 크게 달라질 수 있음
- **[U-15] 평가자 보상/동기 부여 계획 부재**: 250건 × 2분 = ~8시간의 평가 작업에 대한 보상 체계가 없음
- **[U-16] (B') Vector + LLM Reranking에서 LLM이 보는 정보 범위**: LLM에게 이력서 전문을 제공하는지, 요약만 제공하는지에 따라 결과가 달라짐. 정보 범위가 명확하지 않음

---

### 2.7 `06_crawling_strategy.md` — 크롤링 전략

#### 강점
- **페이지 유형별 추출 프롬프트가 상세하게 정의됨** (P1~P3, N1, N4)
- **광고성 필터링 규칙**이 구체적이고 NOISE_PATTERNS/SIGNAL_PATTERNS 분리가 실용적
- **해시 기반 변경 감지 + HTML vs 텍스트 해시 A/B 검증 계획**이 비용 최적화에 기여
- **비용 추정**이 현실적 (~$107/월 for 1,000 기업)

#### 과도한 설계
- **[O-13] 2단계 중복 제거(S-5)**: 제목 유사도 + 핵심 엔티티 overlap 클러스터링은 정교하지만, v1 파일럿 단계에서 기업당 30건 뉴스에 대해 이 수준의 중복 제거가 필요한지 의문. 단순 제목 유사도(threshold 0.85)만으로 충분할 수 있고, 엔티티 추출 자체의 정확도가 보장되지 않으면 2단계가 오히려 노이즈
- **[O-14] 서브도메인 탐색 + 스킵 조건**: 필수 P1~P3 확보 여부에 따른 서브도메인 탐색 스킵 로직이 상세하지만, 대부분의 한국 기업은 서브도메인을 사용하지 않음. 파일럿 20개 기업에서 서브도메인 활용률을 먼저 확인하고 설계해도 충분
- **[O-15] facet 병합 threshold 캘리브레이션 4단계**: 0.20이라는 threshold 하나를 확정하기 위해 4단계 절차(데이터 수집→분포 분석→Human eval→확정)를 정의한 것은 과도. 파일럿에서 score_diff 분포만 확인하고 직관적으로 설정해도 됨

#### 부족한 설계
- **[U-17] 네이버 뉴스 API의 본문 미제공에 대한 구체적 대안 부재**: "link 추가 크롤링"이라고만 되어 있는데, 각 언론사별 본문 추출의 기술적 난이도/성공률 예측이 없음. 특히 유료 기사, 동적 로딩 기사 등의 처리 전략 부재
- **[U-18] 크롤링 법적 리스크 대응이 피상적**: "robots.txt 준수, 개인정보 미수집"만으로는 불충분. 뉴스 저작권법, 데이터베이스 권리 등 구체적 법적 검토 결과가 필요

---

### 2.8 `02_v4_amendments.md` — 보완 이력

#### 강점
- A1~A7이 통합판으로 이관 완료 표시되어 추적 가능
- A8(추출 프롬프트 확장 로드맵)의 4단계 일정과 안정화 판정 기준이 명확
- A10(실측 데이터 기반 설계 결정)의 D1~D10 요약이 체계적

#### 이슈
- **[V-2] 이 문서의 존재 의의 감소**: A1~A7, A9, A10이 모두 각 통합판 문서에 인라인 반영 완료됨. 현재 남아있는 유효 내용은 A8(추출 프롬프트 확장 로드맵)뿐. A8도 06_crawling_strategy.md에 통합하거나, 이 문서를 "변경 이력 요약"으로 축소하는 것이 적절

---

## 3. 횡단 이슈 (Cross-cutting Concerns)

### 3.1 문서 간 일관성

| 이슈 | 상세 | 심각도 |
|---|---|---|
| **[X-1] industry_code 이중 정의** | 01_company_context.md의 JSON 스키마에서 industry_code가 "J63112" (NICE 코드)로 예시되어 있으나, 00_data_source_mapping은 code-hub INDUSTRY 코드가 primary라고 정의. 예시와 본문의 불일치 | 중간 |
| **[X-2] Person 노드 속성 누락** | 04_graph_schema의 Person 노드에 `name` 속성이 있으나, 02_candidate_context의 CandidateContext JSON 스키마에는 name 필드가 없음 | 낮음 |
| **[X-3] confidence 상한 불일치** | 01_company_context에서 자사 이력서 T1의 상한이 0.80이나, 02_candidate_context에서는 0.85 | 중간 — 동일한 "T1"이 문서마다 다른 의미 (기업 T1=JD, 후보 T1=이력서)이므로 혼동 유발 |
| **[X-4] F3 domain_fit 계산 로직 중복** | 00_data_source_mapping §4.1과 03_mapping_features F3에 모두 industry code 매칭 로직이 존재하나 세부 구현이 다름 | 높음 — 정본이 어느 쪽인지 불명확 |

### 3.2 LLM 비용 추정 부재

- 전체 파이프라인에서 LLM 호출 지점이 최소 8곳 (vacancy scope_type, scope_summary, outcomes, situational_signals, operating_model facets, role_evolution, work_style_signals, 크롤링 추출)
- 서비스 풀 3.2M 이력서, 공고 수 미정 규모에서의 LLM 비용 총 추정이 없음
- 크롤링 전략에서만 비용 추정($107/월)이 있고, CandidateContext/CompanyContext 추출 비용은 미산정

### 3.3 버전 관리 복잡도

- 각 문서에 v3~v13까지의 변경 이력이 누적되어 "현재 유효한 정의"를 파악하기 어려움
- 특히 01_company_context.md의 헤더에 "v4 원본에 A3, A6 통합"이라는 설명이 있으나, 실제로는 v13까지의 변경이 모두 반영된 상태
- **권장**: 각 문서의 변경 이력을 별도 CHANGELOG로 분리하거나, 최소한 "현재 유효 버전: v13" 명시

---

## 4. 실현 가능성 평가

### 4.1 Phase 1 (데이터 정제) — **실현 가능**

| 과제 | 난이도 | 실현 가능성 | 비고 |
|---|---|---|---|
| days_worked 계산 | 낮음 | 높음 | 단순 daterange 연산, 즉시 구현 가능 |
| certificate type 매핑 | 낮음 | 높음 | 변환 테이블 2줄, 즉시 구현 가능 |
| 회사명 정규화 | 중간 | 중간 | 4.48M 고유값, BRN 62%로 1차 클러스터링은 가능하나 38% 잔여분 처리가 관건 |
| 스킬 정규화 | 높음 | 중간-낮음 | 97.6% 비표준 → 임베딩 fallback에 전적으로 의존. 임베딩 품질 미검증 |
| 전공명 정규화 | 중간 | 높음 | Tier 3 임베딩 전용으로 결정, 정규화하지 않으므로 구현 부담 낮음 |

### 4.2 Phase 2 (노드/엣지 구축) — **실현 가능, 규모 주의**

- Person ~3.2M + Chapter ~18M + Skill ~100K + Role ~242 + Industry 63 노드 생성
- **핵심 리스크**: Neo4j AuraDB의 가격/성능이 이 규모를 감당할 수 있는지 사전 검증 필요. Free tier 한계는 200K 노드/400K 관계

### 4.3 Phase 3 (LLM 추출) — **실현 가능하나 비용/시간 리스크**

- Outcome/SituationalSignal 추출 대상: CareerDescription 16.9% + SelfIntroduction 64.1% = 합집합 ~65-70% 이력서
- 대상 이력서 수: ~2.2M (3.2M × 70%)
- LLM 호출당 평균 1K tokens 입력 가정 시, 2.2M × 1K = 2.2B tokens
- Gemini 2.0 Flash 기준 ~$220 (input $0.10/1M tokens) — **관리 가능한 수준**
- 단, 처리 시간은 동기 처리 시 ~2,200시간, 병렬 50 동시 처리 시 ~44시간

### 4.4 Phase 4 (기업측 + 매핑) — **실현 가능, job-hub 분석 선행 필수**

- job-hub 상세 분석이 미완이므로, CompanyContext 추출의 실제 fill rate/품질이 불확실
- **권장**: Phase 4-1(job-hub 분석)을 Phase 1과 병렬로 진행하여 일정 리스크 완화

---

## 5. 핵심 권장 사항 (우선순위순)

### 5.1 즉시 조치 (Critical)

| # | 권장 사항 | 근거 |
|---|---|---|
| R-1 | **job-hub 데이터 상세 분석 조기 착수** | CompanyContext 설계의 실측 기반 검증이 누락된 상태. company 측 fill rate 없이 F1~F5 ACTIVE 비율 추정이 불완전 |
| R-2 | **F3 domain_fit industry code 매칭 로직 정본 확정** | 00_data_source_mapping §4.1과 03_mapping_features F3에 중복/불일치 존재 |
| R-3 | **Neo4j 규모 PoC** | 3.2M Person + 18M Chapter 규모에서 Q1~Q5 쿼리 성능 검증. AuraDB tier 선정 근거 확보 |

### 5.2 단기 개선 (High)

| # | 권장 사항 | 근거 |
|---|---|---|
| R-4 | **스킬 임베딩 threshold 검증** | 한국어/영어 혼합 스킬명에 대한 text-multilingual-embedding-002의 cosine similarity 분포 분석 (50쌍 샘플) |
| R-5 | **FEATURE_WEIGHTS 설정 근거 문서화** | 현재 가중치가 전문가 판단인지 임의인지 불명확. 최소한 "초기값이며 파일럿 후 캘리브레이션"이라는 명시 필요 |
| R-6 | **README.md 업데이트** | 문서 구조가 "schema/v10/" 기준으로 되어 있어 최신 v13과 불일치 |
| R-7 | **문서 변경 이력 분리** | 각 문서의 v3~v13 변경 이력을 CHANGELOG로 분리하여 본문 가독성 향상 |

### 5.3 중기 개선 (Medium)

| # | 권장 사항 | 근거 |
|---|---|---|
| R-8 | **LLM 추출 전체 비용/시간 추정** | 크롤링 외 CandidateContext/CompanyContext 추출의 LLM 비용이 미산정 |
| R-9 | **F4 culture_fit 계산 로직을 v2로 이동** | ACTIVE <10%인 피처의 상세 계산 로직은 데이터 확보 후 설계하는 것이 효율적 |
| R-10 | **BigQuery-Neo4j 데이터 동기화 전략 정의** | 서빙(BQ)과 탐색(Neo4j) 간 데이터 일관성 보장 방안 필요 |

---

## 6. 결론

v13 스키마는 **채용 도메인의 기업-인재 매칭을 위한 Knowledge Graph 설계로서 높은 완성도**를 보인다. 13회의 반복 리뷰를 거치며 실측 데이터 기반 검증, Evidence-first 원칙, Graceful Degradation 등 핵심 설계 원칙이 잘 관철되었다.

주요 리스크는:
1. **job-hub 측 데이터 분석 미완** — company 측 설계가 검증되지 않은 상태
2. **스케일 검증 부재** — 3.2M Person + 18M Chapter 규모의 Neo4j 성능/비용
3. **LLM 추출 비용/시간 총 추정 부재** — 파이프라인 전체의 운영 비용 불확실

과도한 설계가 부족한 설계보다 다소 많은 경향이 있으며, 이는 v1에서 아직 데이터가 없거나 INACTIVE 예정인 기능에 대해 미리 상세 설계를 진행한 결과이다. "v1에서 필요한 것만 정의하고, 나머지는 v2 로드맵에 한 줄로 남기는" 원칙을 강화하면 문서 분량과 유지보수 부담을 줄일 수 있다.

---

## 부록: 이슈 요약 테이블

| ID | 유형 | 문서 | 설명 | 심각도 |
|---|---|---|---|---|
| O-1 | 과도 | 00 | 임베딩 비교 batch O(n*m) 구현 코드 | 낮음 |
| O-2 | 과도 | 00 | gender/age를 그래프 노드에 저장 | 중간 |
| O-3 | 과도 | 01 | structural_tensions 8개 taxonomy (v1 null 70%+) | 중간 |
| O-4 | 과도 | 01 | T4 ceiling 예외 규칙 (0.05 차이) | 낮음 |
| O-5 | 과도 | 02 | PastCompanyContext estimated_stage_at_tenure | 중간 |
| O-6 | 과도 | 02 | WorkStyleSignals 전체 구조 (v1 대부분 null) | 낮음 |
| O-7 | 과도 | 03 | F4 culture_fit 전체 계산 로직 | 중간 |
| O-8 | 과도 | 03 | ROLE_PATTERN_FIT 매트릭스 근거 부재 | 중간 |
| O-9 | 과도 | 04 | Organization 크롤링 보강 속성 설명 분량 | 낮음 |
| O-10 | 과도 | 04 | v2 Company 간 관계 상세 설명 | 낮음 |
| O-11 | 과도 | 05 | 가상 실험 데이터 ~100줄 | 낮음 |
| O-12 | 과도 | 05 | Step별 함수 시그니처 | 낮음 |
| O-13 | 과도 | 06 | 2단계 중복 제거 (엔티티 기반) | 중간 |
| O-14 | 과도 | 06 | 서브도메인 탐색 스킵 조건 | 낮음 |
| O-15 | 과도 | 06 | facet 병합 threshold 캘리브레이션 4단계 | 낮음 |
| U-1 | 부족 | 00 | job-hub 데이터 상세 분석 부재 | **높음** |
| U-2 | 부족 | 00 | 스킬 임베딩 threshold 검증 부재 | 중간 |
| U-3 | 부족 | 00 | CareerDescription LLM 귀속 정확도 추정 부재 | 중간 |
| U-4 | 부족 | 01 | NICE 데이터 갱신 주기/정확도 미언급 | 중간 |
| U-5 | 부족 | 01 | vacancy scope_type LLM 추출 정확도 추정 부재 | 중간 |
| U-6 | 부족 | 02 | 짧은 텍스트 LLM 추출 품질 대응 부재 | 중간 |
| U-7 | 부족 | 02 | 경력 시간순 정렬 보장 미명시 | 낮음 |
| U-8 | 부족 | 03 | 피처 간 상관관계 분석 부재 | 중간 |
| U-9 | 부족 | 03 | FEATURE_WEIGHTS 설정 근거 부재 | 중간 |
| U-10 | 부족 | 03 | 매핑 1건 처리 시간 분석 부재 | 중간 |
| U-11 | 부족 | 04 | 노드/엣지 규모 추정 부재 | **높음** |
| U-12 | 부족 | 04 | Neo4j 인덱스 전략 부재 | 중간 |
| U-13 | 부족 | 04 | BigQuery-Neo4j 데이터 동기화 전략 부재 | 중간 |
| U-14 | 부족 | 05 | 후보 풀 500명 선정 기준 부재 | 중간 |
| U-15 | 부족 | 05 | 평가자 보상 계획 부재 | 낮음 |
| U-16 | 부족 | 05 | B' LLM 정보 범위 불명확 | 중간 |
| U-17 | 부족 | 06 | 언론사 본문 추출 성공률 예측 부재 | 중간 |
| U-18 | 부족 | 06 | 크롤링 법적 리스크 대응 피상적 | 중간 |
| X-1 | 불일치 | 01/00 | industry_code 예시 vs 본문 불일치 | 중간 |
| X-2 | 불일치 | 04/02 | Person name 속성 존재/부재 | 낮음 |
| X-3 | 불일치 | 01/02 | T1 confidence 상한 0.80 vs 0.85 | 중간 |
| X-4 | 불일치 | 00/03 | F3 industry code 매칭 로직 중복 | **높음** |
| V-1 | 타당성 | 00 | industry_code_match 실효성 (66% 빈배열) | 중간 |
| V-2 | 타당성 | 02_v4 | amendments 문서 존재 의의 감소 | 낮음 |
