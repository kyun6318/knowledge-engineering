# v15 Schema Review

> 리뷰 일시: 2026-03-10
> 리뷰 대상: `01.ontology/results/schema/v15/` 전체 8개 문서
> 리뷰 기준: README.md 방향성 일치, 실현 가능성/타당성, 과도한 설계 vs 부족한 설계
> 리뷰 관점: **온톨로지 설계** (지식 그래프 구축 설계는 02.knowledge_graph에서 별도 진행)
> 이전 리뷰: `reviews/v14/review.md` (v13 이월 22건 + v14 신규 7건 = 29건 이슈)

---

## 1. 종합 평가

### 1.1 README 방향성과의 일치도: **높음 (9/10)**

README에서 정의한 6개 설계 원칙과 핵심 개념이 v15에서도 충실하게 유지되어 있다.

| README 원칙 | v15 반영 상태 | 평가 |
|---|---|---|
| **독립성**: Company/Candidate 독립 생성 | 01, 02 문서에서 일관 유지 | O |
| **Evidence-first**: 모든 claim에 근거 필수 | Evidence 통합 모델 전문서 적용 | O |
| **부분 완성 허용**: null 명시, 안전 동작 | Graceful Degradation 체계 완비 | O |
| **데이터 소스 계층화**: Tier별 confidence ceiling | T1~T7 체계 + 카테고리별 예외 | O |
| **Taxonomy 고정**: LLM 자유 생성 방지 | SituationalSignal 14개, TensionType 8개 | O |
| **의도적 제외 명문화**: 제외 이유 + 로드맵 | CompanyTalentSignal 등 명시 | O |

**미해소 1건 이월**:
- **[R-6 CARRIED]** README의 문서 구조 설명이 `schema/v10/` 기준. v15와 불일치. **v13 이후 4버전 경과하였으나 미수정** — 이 시점에서 수정하는 것이 맞다.

### 1.2 전체 성숙도 평가 (v14→v15 진전 요약)

v15는 **소폭 변경 버전**이다. v14에서 7건의 신규 이슈가 식별되었으나, v15에서는 그 중 **5건을 해소**하고 1건을 신규 추가하였다.

주요 변경:
1. **[N14-1 RESOLVED]** 00_data_source_mapping §10.1: output token 30% 가정에 대한 주의사항 및 실측 보정 계획 추가
2. **[N14-2 RESOLVED]** 04_graph_schema §7.3: MAPPED_TO 엣지 TTL/아카이빙 정책 추가
3. **[N14-3 RESOLVED]** 04_graph_schema §9.3: sync_to_neo4j 에러 핸들링/재시도 정책 정의
4. **[N14-4 RESOLVED]** 04_graph_schema §9.1: 동기화 방향성 정확화
5. **[N14-5 RESOLVED]** 04_graph_schema §8.2: Organization.name 풀텍스트 인덱스 추가
6. **[X-2 RESOLVED]** 02_candidate_context §2.6: Person `name` 필드 소스 명시

### 1.3 v14 이슈 해소 현황 요약

| 상태 | 건수 | 비율 |
|---|---|---|
| RESOLVED (v15에서 해소) | 6 | 20.7% |
| CARRIED (미해소 이월) | 23 | 79.3% |
| **합계** | **29** | 100% |

v15의 변경이 소폭이었으므로 이월 비율이 높다. 이월된 이슈 중 **온톨로지 설계에 영향을 미치는 핵심 이슈**를 아래에서 재분류한다.

---

## 2. 온톨로지 설계 관점 심층 리뷰

### 2.1 노드/엣지 체계의 타당성

#### 강점

**9종 노드 체계가 매칭 유스케이스에 적합하게 설계됨.** Person → Chapter → (Role, Skill, Outcome, SituationalSignal, Organization) 그래프와 Organization → Vacancy → (Role, Skill, SituationalSignal) 그래프가 `SituationalSignal`과 `Role`, `Skill` 노드를 공유 접점으로 삼아 자연스러운 매칭 탐색을 지원한다.

특히 SituationalSignal을 **공유 노드**로 설계한 것은 탁월하다. "같은 상황을 경험한 후보"를 그래프 탐색으로 직접 찾을 수 있어, 이것이 단순 Vector 검색 대비 GraphRAG의 핵심 차별점이 된다.

#### 이슈

- **[S-1 NEW] Chapter-Outcome 1:N 관계의 Outcome 품질 리스크**: CareerDescription FK 부재(16.9% 보유, career_id FK 없음)로 인해 LLM이 텍스트 컨텍스트로 career에 outcome을 귀속해야 한다. 이 귀속 정확도가 낮으면 Outcome 노드 자체의 품질이 저하되고, Outcome 노드를 활용한 탐색이 의미를 잃는다. **온톨로지 설계는 적절하나, 데이터 품질 전제가 취약하다.** 권장: Phase 3 착수 전 LLM 귀속 정확도를 20건 샘플로 실측하고, 정확도 70% 미만이면 Outcome을 Chapter 속성으로 내리는 방안을 검토.

- **[S-2 NEW] Industry 노드의 code-hub 의존도**: Industry 노드가 code-hub INDUSTRY_SUBCATEGORY 63개에 전적으로 의존한다. code-hub의 산업 분류 체계가 변경되면 Industry 노드 전체가 영향받는다. 또한 63개 중분류가 IT/SW 분야를 얼마나 세분화하는지 불명확 — 채용 플랫폼 특성상 IT 직군 비중이 높을 텐데, "소프트웨어 개발"이 단일 코드라면 산업 매칭(F3)의 변별력이 떨어질 수 있다. 권장: code-hub INDUSTRY_SUBCATEGORY의 IT 관련 코드 분포를 확인하고, 필요시 3depth(INDUSTRY) 기반으로 Industry 노드 세분화를 검토.

### 2.2 Taxonomy 설계의 적정성

#### SituationalSignal 14개 — 적정 수준이나 OTHER 비율 예측 부재

14개 taxonomy는 성장 단계(4), 조직 변화(3), 기술 변화(3), 비즈니스(3) + OTHER로 구성되어 있다. 카테고리 배분은 균형적이나, **실제 이력서에서 OTHER로 분류될 비율에 대한 추정이 없다.** OTHER가 30%를 초과하면 taxonomy의 실효성에 의문이 생기며, 추가 라벨 도입을 검토해야 한다.

권장: Phase 3 파일럿에서 SituationalSignal 추출 시 OTHER 비율을 모니터링하고, 20% 초과 시 해당 사례를 분석하여 v2 taxonomy 확장에 반영.

#### Vacancy scope_type 4개 — BUILD_NEW / SCALE_EXISTING / RESET / REPLACE

- **[S-3 NEW] REPLACE 타입의 매칭 전략 부재**: REPLACE(충원)에 대해 vacancy_fit 계산 시 strong/moderate/weak 매핑이 모두 빈 배열이고, 중립 스코어 0.5를 반환한다. 전체 공고의 상당 부분이 REPLACE(단순 충원)일 가능성이 높은데, 이 경우 vacancy_fit이 무의미해진다. REPLACE 공고에서는 vacancy_fit 대신 role_fit의 가중치를 높이는 등 보완이 필요하다. 권장: REPLACE 비율을 Phase 4-1 job-hub 분석에서 확인하고, 30% 이상이면 REPLACE 전용 매칭 전략을 수립.

#### Outcome type 5개 — METRIC / SCALE / DELIVERY / ORGANIZATIONAL / OTHER

적절한 수준. 이력서에서 추출 가능한 성과 유형을 잘 포괄한다.

#### TensionType 8개 — v1에서 대부분 null

**[O-3 CARRIED]** structural_tensions의 8개 taxonomy는 설계 완성도가 높으나, v1에서 70%+ null 예상이다. 배타성 가이드, related_tensions 등 상세 정의는 v1.1 크롤링 활성화 후 필요한 것이지, 현 시점에서 온톨로지 문서의 볼륨만 증가시킨다. 다만 "의도적 제외 명문화" 원칙에 따라 정의해 둔 것이므로 삭제가 아닌 별도 부록으로의 분리를 권장.

### 2.3 MappingFeatures 5개 피처의 온톨로지 설계 관점

#### F1 stage_match — 타당

STAGE_SIMILARITY 4x4 매트릭스의 비대칭 설계(GROWTH→EARLY 0.50 > EARLY→GROWTH 0.30)는 직관적으로 합리적이다. 성장기 기업 경험자가 초기 기업에 적응하는 것이 그 반대보다 쉽다는 가정은 채용 도메인에서 통용된다.

다만 **duration_bonus와 scope_bonus가 base similarity에 additive로 합산되는 방식**이 적절한지는 검증 필요. 12개월 미만 EARLY 경험(sim=1.0 + duration=0.075 + scope=0.0)과 36개월 GROWTH 경험(sim=0.30 + duration=0.15 + scope=0.10 = 0.55)의 우열이 직관과 일치하는지 확인 필요.

#### F2 vacancy_fit — 타당하나 위 [S-3] 참조

#### F3 domain_fit — 타당

Embedding 유사도 + Industry code 직접 매칭 + 반복 경험 가중의 3중 구조가 견고하다. code_match_bonus를 `industry_code[:3]` 대분류 비교로 처리하는 것은 code-hub 코드 체계의 계층성을 잘 활용한다.

#### F4 culture_fit — **v1에서 실질적으로 비활성**

**[O-6 CARRIED]** v1에서 <10% ACTIVE 예상. 온톨로지에 WorkStyleSignals 구조가 정의되어 있으나, 데이터가 거의 없어 dead weight이다. 가중치 0.10이 배정되어 있지만, INACTIVE 시 다른 피처에 재분배되므로 실질적 영향은 없다. 온톨로지 설계로서는 v2를 위한 placeholder로 적절하지만, v1 구현 시 이 피처의 구현 우선순위를 최하로 두어야 한다.

#### F5 role_fit — 타당

ScopeType → Seniority 변환 규칙이 명확하게 정의되어 있다. IC의 경력 연수 기반 세분화(3년/6년 경계)는 한국 채용 시장의 관행과 부합한다.

#### overall_match_score의 이중 감쇠 — 주의 필요

**[S-4 NEW]** confidence를 가중치로 사용하는 "의도적 이중 감쇠"는 설계 의도가 문서화되어 있으나, **v1에서 대부분의 피처 confidence가 0.40~0.65 범위**에 있어 overall_match_score가 과도하게 낮아질 수 있다. 예: 4개 피처가 모두 score=0.80, confidence=0.50이면 overall=0.80이 되어 감쇠가 없으나, confidence가 불균일하면(0.30~0.70) 고confidence 피처가 과도하게 지배한다. 파일럿 50건에서 overall_match_score의 분포를 확인하고, 0.3~0.7 범위에 80%+ 집중되는지 검증 필요.

---

## 3. 과도한 설계 (Over-engineering)

### 3.1 MAPPED_TO 엣지 TTL/아카이빙 정책 (04_graph_schema §7.3)

v15에서 신규 추가된 MAPPED_TO TTL 정책(90일 미조회 + Vacancy 마감 → 아카이빙)은 **v1 파일럿 단계에서 premature**하다. 아직 매핑 결과 자체가 없는 상태에서 아카이빙 정책을 정의하는 것은 시기상조. 운영 데이터가 축적된 후(6개월+) 실제 MAPPED_TO 엣지 증가 속도를 관측하고 정책을 수립해도 늦지 않다.

**심각도**: 낮음 (구현하지 않으면 되므로)
**권장**: v1에서는 구현하지 않고, 운영 6개월 후 재검토. 문서에는 "v1.1 이후 검토" 표시 추가.

### 3.2 Crawling Strategy의 상세도 (06_crawling_strategy.md)

06 문서가 1,500줄에 달하며, 현재 "미구축" 상태의 기능에 대해 지나치게 상세하다. URL 발견 4단계, 서브도메인 스킵 조건, 텍스트 해시 A/B 검증 계획, 뉴스 중복 제거 2단계 클러스터링, facet 병합 threshold 4단계 캘리브레이션 등은 **구현 시점에 설계해도 충분**한 수준이다.

온톨로지 설계 관점에서 06 문서에 필요한 것은 "어떤 필드를 어떤 소스에서 보강하는가"의 매핑 정보이지, 크롤링 엔진의 구현 세부사항이 아니다.

**심각도**: 중간 (문서 유지보수 부담 증가, 변경 시 동기화 비용)
**권장**: 06 문서를 온톨로지 관련(소스→필드 매핑, confidence 보정 규칙) / 구현 관련(크롤링 엔진, 파이프라인)으로 분리하고, 구현 부분은 02.knowledge_graph로 이관을 검토.

### 3.3 structural_tensions 상세 정의 (01_company_context.md §2.2)

**[O-3 CARRIED]** 8개 taxonomy + 배타성 가이드 + related_tensions + T4 ceiling 예외 규칙. v1에서 70%+ null이므로 현 시점에서 과도. 위에서 언급한 바와 같이 별도 부록 분리 권장.

### 3.4 evaluation_strategy의 가상 데이터 (05_evaluation_strategy.md §10)

§10의 가상 실험 데이터가 100줄 이상을 차지한다. 실험 설계 문서에 가상 데이터가 필요하긴 하나, 결과 스키마만 보여주면 충분하다. 가상 수치까지 상세히 기술할 필요는 없다.

**심각도**: 낮음
**권장**: 가상 수치를 제거하고 결과 스키마(필드 정의)만 유지.

---

## 4. 부족한 설계 (Under-engineering)

### 4.1 신입(NEW_COMER) 30.9%에 대한 매칭 전략 부재

**[S-5 NEW — Critical]** CandidateContext의 전체 설계가 **경력자(EXPERIENCED)** 중심이다. Experience/Chapter 기반 분해, SituationalSignal, RoleEvolution 등이 모두 경력 기반이다. 그러나 서비스 풀의 **30.9%가 NEW_COMER(신입)**이며, 이들은:

- Career 데이터가 없거나 인턴/아르바이트 수준
- SituationalSignal 추출 불가
- RoleEvolution 추출 불가 (경력 1건 미만)
- PastCompanyContext 없음

현재 이들에 대해 MappingFeatures F1(stage_match), F2(vacancy_fit), F5(role_fit)이 대부분 INACTIVE가 되고, F3(domain_fit)만 Education 기반으로 부분 활성화될 수 있다. 사실상 **신입 후보에 대한 매칭이 거의 작동하지 않는다.**

온톨로지 설계에서 신입 후보를 어떻게 표현할 것인지 — Education, Certificate, 희망 직무, 자기소개서 기반의 대체 시그널 체계가 필요하다.

**권장**:
1. v1에서는 `career_type = "NEW_COMER"` 필터로 경력자만 매칭 대상으로 제한하고 이를 명시적으로 문서화
2. v2에서 신입 전용 피처(Education-based matching, Certificate matching, 희망 직무 매칭) 도입을 로드맵에 추가

### 4.2 다중 공고 처리 전략 부재

**[S-6 NEW]** 동일 기업이 여러 Vacancy를 동시에 보유하는 경우의 처리가 미정의. Organization → HAS_VACANCY → Vacancy 관계에서 10개 이상의 Vacancy가 달린 기업의 경우:

- CompanyContext의 operating_model, structural_tensions는 기업 수준인데 Vacancy마다 다를 수 있는가?
- vacancy scope_type이 공고마다 다를 때 (하나는 BUILD_NEW, 다른 하나는 REPLACE) Organization의 stage_label은 공유되는데 vacancy 수준 속성은 어떻게 구분되는가?

현재 설계는 이를 자연스럽게 처리한다 (CompanyContext는 기업 단위, Vacancy는 공고 단위로 분리). 다만 이 원칙을 명시적으로 문서화하고, "CompanyContext는 job_id별로 생성되지만, company_profile/stage_estimate/operating_model은 동일 기업 공고 간 공유된다"는 점을 명확히 해야 한다.

**심각도**: 중간
**권장**: 01_company_context에 "동일 기업 다중 공고 처리 원칙" 절을 추가.

### 4.3 시간 변화에 따른 Context 갱신 전략

**[U-8 CARRIED]** CompanyContext와 CandidateContext가 한 번 생성된 후 어떤 조건에서 재생성되는지 정의되어 있지 않다. 이력서가 갱신되면? 공고가 수정되면? NICE 데이터가 업데이트되면? 04_graph_schema §9.2에서 동기화 주기(일간/주간)는 정의되었으나, **Context 재생성 트리거**는 미정의.

**권장**: "Context 재생성 조건" 정의 필요 — 이력서 갱신 시 CandidateContext 재생성, 공고 수정 시 해당 Vacancy 재생성 등.

### 4.4 SOFT_SKILL 편중 대응 부재

**[S-7 NEW]** 00_data_source_mapping §1.3에서 SOFT_SKILL TOP 10의 60%가 "성실성(25.2%), 긍정적(17.3%)"으로 편중되어 있다고 기술했으나, 이에 대한 대응이 없다. 스킬 매칭에서 SOFT_SKILL을 그대로 포함하면 "성실성" 하나로 대다수 후보가 매칭되는 노이즈가 발생한다.

**권장**: 스킬 매칭 시 `type=HARD` 스킬만 사용하고, SOFT_SKILL은 매칭에서 제외하는 규칙을 명시. (현재 코드에서 `type=HARD` 필터가 있는 곳도 있으나, 일관되지 않음)

---

## 5. 실현 가능성 평가

### 5.1 데이터 가용성 기반 피처 활성화 전망

| 피처 | 예상 ACTIVE | 핵심 병목 | 실현 가능성 | 비고 |
|---|---|---|---|---|
| F1 stage_match | 50-60% | 회사명 정규화 4.48M 고유값 | **중간** | BRN 62% 활용 가능하나 38%는 회사명 유사도 의존 |
| F2 vacancy_fit | 50-65% | careerDescription 16.9% | **중간** | selfIntroduction 64.1% fallback이 핵심 |
| F3 domain_fit | 70%+ | industryCodes 66% 빈배열 | **높음** | code-hub/NICE 보완 경로 존재 |
| F4 culture_fit | <10% | work_style_signals 부재 | **매우 낮음** | v1에서 사실상 비활성 |
| F5 role_fit | 50-60% | positionGrade/Title 29-39% | **중간** | LLM fallback 경로 존재 |

**종합 판단**: v1에서 "4개 피처 중 3개 이상 ACTIVE" 비율은 **40-50%** 수준으로 예상. 이는 전체 매핑의 절반 정도만 의미 있는 Context 기반 매칭이 가능함을 의미. 나머지 절반은 1-2개 피처만 활성화되어 매칭 품질이 제한적일 수 있다.

### 5.2 핵심 선행 과제의 실현 가능성

| 과제 | 난이도 | 실현 가능성 | 리스크 |
|---|---|---|---|
| days_worked 계산 | 낮음 | **높음** | 없음 — DATERANGE에서 직접 계산 |
| certificate type 매핑 | 낮음 | **높음** | 단순 매핑 테이블 |
| 회사명 정규화 | 중간 | **중간** | 4.48M 고유값, BRN 62%만 1차 키 |
| 스킬 정규화 | 높음 | **중간-낮음** | 97.6% 비표준, 임베딩 fallback 품질 미검증 |
| 전공명 정규화 | 중간 | **높음** | Tier 3 임베딩 전용 — 정규화 안 하므로 구현 부담 낮음 |

**스킬 정규화가 가장 큰 리스크**. 97.6%가 비표준이고 임베딩 fallback에 의존하는데, 스킬명 임베딩의 실제 품질이 검증되지 않았다. "React"와 "리액트"의 임베딩 유사도가 threshold를 넘는지, "Spring Boot"와 "스프링부트"가 매칭되는지 등 기본적인 검증이 필요하다.

### 5.3 LLM 비용/처리 시간 실현 가능성

v14에서 추가되고 v15에서 보정된 비용 추정($484~$700, ~80시간):

- **비용**: $700 이내라면 관리 가능. 다만 output token 비율이 실측되지 않았으므로 v15의 주의사항(N14-1 해소)에 따라 Phase 3 전 실측 필수.
- **처리 시간**: 80시간(3.3일)은 50 병렬 기준. 실제로 Gemini 2.0 Flash에서 50 병렬 호출이 rate limit에 걸리지 않는지 확인 필요. Vertex AI의 기본 QPS 제한(60 QPM for flash)을 고려하면 실제 소요 시간이 2-3배 늘어날 수 있다.

---

## 6. 문서별 세부 이슈

### 6.1 00_data_source_mapping.md

| ID | 유형 | 설명 | 심각도 | 상태 |
|---|---|---|---|---|
| N14-1 | 부족 | output token 30% 가정 미검증 | 중간 | **v15 RESOLVED** (주의사항 + 실측 계획 추가) |
| U-1 | 부족 | job-hub 상세 분석 미완 (Phase 4-1 대기) | 중간 | CARRIED |
| V-1 | 타당성 | industryCodes 66% 빈배열로 F3 실효성 제한 | 중간 | CARRIED |
| S-7 | 부족 | SOFT_SKILL 편중(60%) 대응 부재 | 중간 | **NEW** |

### 6.2 01_company_context.md

| ID | 유형 | 설명 | 심각도 | 상태 |
|---|---|---|---|---|
| O-3 | 과도 | structural_tensions 8개 taxonomy 상세 정의 (v1 null 70%+) | 낮음 | CARRIED |
| O-4 | 과도 | T4 ceiling 예외 규칙 미세 조정 | 낮음 | CARRIED |
| U-4 | 부족 | NICE 데이터 갱신 주기/정확도 미언급 | 중간 | CARRIED |
| U-5 | 부족 | vacancy scope_type LLM 추출 정확도 추정 부재 | 중간 | CARRIED |
| S-6 | 부족 | 동일 기업 다중 공고 처리 원칙 미명시 | 중간 | **NEW** |

### 6.3 02_candidate_context.md

| ID | 유형 | 설명 | 심각도 | 상태 |
|---|---|---|---|---|
| X-2 | 부족 | Person `name` 소스 미정의 | 낮음 | **v15 RESOLVED** |
| O-5 | 과도 | PastCompanyContext 현재 시점 NICE로 과거 추정 | 낮음 | CARRIED |
| O-6 | 과도 | WorkStyleSignals 전체 구조 (v1 대부분 null) | 낮음 | CARRIED |
| U-2 | 부족 | 스킬 임베딩 threshold 검증 부재 | 중간 | CARRIED |
| U-3 | 부족 | CareerDescription LLM 귀속 정확도 추정 부재 | 높음 | CARRIED |
| S-1 | 타당성 | Chapter-Outcome 귀속 품질 리스크 | 높음 | **NEW** |
| S-5 | 부족 | NEW_COMER 30.9% 매칭 전략 부재 | **Critical** | **NEW** |

### 6.4 03_mapping_features.md

| ID | 유형 | 설명 | 심각도 | 상태 |
|---|---|---|---|---|
| S-3 | 부족 | REPLACE scope_type의 vacancy_fit 매칭 전략 부재 | 중간 | **NEW** |
| S-4 | 주의 | overall_match_score 이중 감쇠로 점수 분포 왜곡 가능성 | 중간 | **NEW** |

### 6.5 04_graph_schema.md

| ID | 유형 | 설명 | 심각도 | 상태 |
|---|---|---|---|---|
| N14-2 | 과도 | MAPPED_TO TTL 정책 (v1에서 premature) | 낮음 | **v15 RESOLVED** (추가됨, 단 시기 부적절) |
| N14-3 | 부족 | sync_to_neo4j 에러 핸들링 | 중간 | **v15 RESOLVED** |
| N14-4 | 부족 | 동기화 방향성 모호 | 낮음 | **v15 RESOLVED** |
| N14-5 | 부족 | Organization.name 풀텍스트 인덱스 | 중간 | **v15 RESOLVED** |
| S-2 | 타당성 | Industry 노드 code-hub 63개 의존, IT 세분화 부족 가능성 | 중간 | **NEW** |

### 6.6 05_evaluation_strategy.md

| ID | 유형 | 설명 | 심각도 | 상태 |
|---|---|---|---|---|
| O-7 | 과도 | 가상 실험 데이터 과다 (§10) | 낮음 | CARRIED |

### 6.7 06_crawling_strategy.md

| ID | 유형 | 설명 | 심각도 | 상태 |
|---|---|---|---|---|
| O-8 | 과도 | 미구축 기능의 구현 세부사항 과다 (1,500줄) | 중간 | CARRIED |

### 6.8 02_v4_amendments.md

변경 이력 관리가 잘 되어 있다. A8(추출 프롬프트 확장 로드맵)만 미이관 상태로 유지되며, 이는 06_crawling_strategy Phase 2~4에서 참조되므로 적절하다.

---

## 7. 이월 이슈 + 신규 이슈 종합

### 7.1 Critical (즉시 대응 필요)

| ID | 설명 | 권장 조치 |
|---|---|---|
| **S-5** | NEW_COMER 30.9% 매칭 전략 부재 | v1 범위를 EXPERIENCED로 제한하고 명시적으로 문서화. v2 로드맵에 신입 매칭 추가 |

### 7.2 High (v1 파일럿 전 해소 권장)

| ID | 설명 | 권장 조치 |
|---|---|---|
| S-1 | Outcome LLM 귀속 정확도 미검증 | Phase 3 전 20건 샘플 실측 |
| U-3 | CareerDescription LLM 귀속 정확도 추정 부재 | 위 S-1과 동일 — 통합하여 검증 |
| U-2 | 스킬 임베딩 threshold 검증 부재 | 한국어/영어 혼합 스킬명 10쌍 실측 |

### 7.3 Medium (v1 운영 중 해소 권장)

| ID | 설명 |
|---|---|
| S-3 | REPLACE 공고 매칭 전략 수립 |
| S-4 | overall_match_score 이중 감쇠 분포 검증 |
| S-6 | 동일 기업 다중 공고 처리 원칙 명시 |
| S-7 | SOFT_SKILL 매칭 제외 규칙 명시 |
| S-2 | Industry 노드 IT 세분화 적정성 확인 |
| U-1 | job-hub 상세 분석 |
| U-4 | NICE 갱신 주기 명시 |
| U-5 | vacancy scope_type 추출 정확도 추정 |
| V-1 | industryCodes 빈배열 대응 |
| R-6 | README 문서 구조 v15 기준으로 갱신 |

### 7.4 Low (v1.1+ 대응 가능)

| ID | 설명 |
|---|---|
| O-3 | structural_tensions 상세 정의 별도 분리 |
| O-4 | T4 ceiling 예외 규칙 단순화 |
| O-5 | PastCompanyContext 과거 추정 정확도 |
| O-6 | WorkStyleSignals 구조 경량화 |
| O-7 | 가상 실험 데이터 축소 |
| O-8 | 06 crawling 구현 세부 분리 |

---

## 8. 총평

### v15 온톨로지 스키마의 성숙도: **높음 (8/10)**

v15는 v11부터 이어진 데이터 분석 기반 설계 보정의 결실로, **온톨로지 설계 자체는 상당히 완성도가 높다.** 특히:

1. **노드/엣지 체계**: 9종 노드, 13종 관계가 채용 도메인의 매칭 유스케이스를 잘 표현한다
2. **Evidence-first + Confidence 체계**: 소스 계층화, ceiling 적용, 교차 검증 규칙이 견고하다
3. **Graceful Degradation**: 데이터 불완전성을 전제로 한 안전한 설계가 일관적이다
4. **실측 데이터 기반 보정**: v12 이후 fill rate 실측치 반영으로 이론-현실 간 갭이 크게 줄었다

**개선이 필요한 영역**:

1. **신입 후보 대응**: 30.9%의 서비스 풀이 사실상 매칭 불가 — 범위 명시 또는 대안 설계 필요
2. **데이터 품질 전제의 검증**: 스킬 임베딩, LLM 귀속 정확도 등 핵심 가정이 미검증 상태
3. **문서 볼륨 관리**: 총 4,000줄+ 규모로 관련자의 전체 파악이 어려움. 특히 06 크롤링의 구현 세부사항 분리 필요
4. **REPLACE 공고 매칭**: 전체 공고의 상당 부분을 차지할 수 있는 유형에 대한 전략 부재

이 리뷰에서 식별된 **신규 7건(S-1~S-7)** 중 S-5(신입 매칭)가 가장 중요하며, 이는 온톨로지 설계의 적용 범위를 명확히 하는 문제이므로 v16에서 반드시 대응해야 한다.
