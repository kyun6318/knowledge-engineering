# v25 온톨로지 스키마 리뷰

> 리뷰 일시: 2026-03-14
> 리뷰 대상: `01.ontology/v25/` 전체 (6개 파일)
> 리뷰 기준: v3 데이터 분석(00.datamodel/summary/v3.md, v3-db-schema.md)과의 정합성, 실현 가능성/타당성, 과도한 설계, 부족한 설계
> 범위: 온톨로지 설계에 집중 (3-Layer 경계 준수 검증 포함)
> 모델: Claude Opus 4.6

---

## 1. 총평

v25는 v18 리뷰 이후 7차 증분 개선을 거친 버전으로, v3 데이터 분석(SIE 모델, LinkedIn 외부 데이터, code-hub 정밀 EDA)을 반영한 성숙한 설계이다. 핵심 강점은 (1) 실측 데이터 기반의 fill rate/품질 수치가 전반에 걸쳐 정확히 인용되고, (2) 구현 상세가 02.knowledge_graph/03.graphrag로 적절히 분리되어 3-Layer 경계를 대체로 준수하며, (3) Graceful Degradation과 confidence 모델이 일관성을 유지하는 점이다.

그러나 18→25 사이의 누적 변경으로 인해 **일부 문서 간 용어/참조 불일치**가 발생하고, **v3 데이터 분석에서 발견된 이슈 중 온톨로지에 미반영된 항목**이 존재한다. 또한 **"파일럿에서 검증" 항목이 v18 대비 더 누적**되어, Phase 0 파일럿의 범위가 과부하 상태이다.

**종합 평가: A- (양호~우수)**

| 평가 항목 | 점수 (5점 만점) | v18 대비 | 한줄 요약 |
|---|---|---|---|
| v3 데이터 정합성 | 4.0 | 신규 | 핵심 수치 정확, 일부 미반영 항목 존재 |
| 3-Layer 경계 준수 | 4.5 | +0.5 | 온톨로지/KG/서빙 분리 양호, 잔여 침범 소수 |
| 실현 가능성 | 3.5 | = | v1 범위 현실적이나 파일럿 과부하 |
| 타당성 | 4.5 | = | confidence 모델, taxonomy 설계 합리적 |
| 과도한 설계 | 3.5 | = | v2/v3 로드맵이 여전히 과다 |
| 부족한 설계 | 3.0 | -0.5 | v3 신규 데이터 반영 불완전 |

---

## 2. v3 데이터 분석과의 정합성 검증

### 2.1 정확히 반영된 항목 (우수)

| v3 데이터 항목 | v25 반영 위치 | 평가 |
|---|---|---|
| career.daysWorked 100% 제로 | 00_data_source_mapping §3.2 D3, compute_duration_months() | 정확 |
| CareerDescription FK 부재 (career_id 없음) | 00_data_source_mapping §3.2 D4, 02_candidate_context §2.7 | 정확, SIE 보완 경로도 명시 |
| education.schoolType vs finalEducationLevel 35.6% 불일치 | 00_data_source_mapping §3.5, 02_candidate_context §2.6 | schoolType 진실 소스로 일관 적용 |
| 서비스 풀 5,545,741건 (PUBLIC+COMPLETED) | 00_data_source_mapping §3.1 get_service_resume_pool() | 수치 정확 |
| SIE 모델(GLiNER2/NuExtract 1.5) 도입 | 00_data_source_mapping §3.2 D5, 02_candidate_context §2.7.1 | v3 §3과 정합 |
| code-hub INDUSTRY 3단계 계층(11→63→936) | 00_data_source_mapping §1.1, 04_graph_schema §1.9 | 정확 |
| BRN 입력률 62% | 00_data_source_mapping §3.4 | 정확 |
| LinkedIn 2.0M 프로필, AI 표준화 경력 | 00_data_source_mapping §3.7, 02_candidate_context §0 T3 | 정확 |
| 사용 불가 필드 목록 | 00_data_source_mapping §9 | v3 §12와 완전 일치 |

### 2.2 미반영 또는 불일치 항목 (개선 필요)

| # | v3 데이터 항목 | v25 현황 | 심각도 | 권고 |
|---|---|---|---|---|
| D-1 | **JOB_CLASSIFICATION_SUBCATEGORY 242개 과도 세분화** (v3 §4.4): 유사 코드 동시선택율 20%+, 디자이너 15개/엔지니어 15개 과다 | 04_graph_schema §1.4 Role 노드에 주석으로만 언급 ("권장: ~30개 2단 계층"), 03_mapping_features F5에는 미반영 | **중간** | Role 노드의 category를 ~30개 JobCategory 기반으로 확정하고, F5 role_fit에서 계층 매칭 로직 추가 필요 |
| D-2 | **스킬 정규화 101,925개 중 2.4%만 표준화** (v3 §4.5) | 00_data_source_mapping에서 정규화를 02.knowledge_graph로 이관했지만, F3 domain_fit의 스킬 매칭이 이 2.4% 한계를 어떻게 극복하는지 명시 없음 | **중간** | F3 compute_domain_fit()에 스킬 기반 보조 매칭 추가 시, 97.6% 비표준 스킬 처리 전략(임베딩 폴백 등) 명시 |
| D-3 | **구코드→신코드 학교 매핑** (v3 §9.3): ~110만건 미매핑, 457개 구코드 | 00_data_source_mapping §3.6 Education 행에 "schoolType을 진실 소스"로만 언급, 구코드 이슈 미언급 | **낮음** | Person.education_level에는 schoolType을 사용하므로 직접 영향은 없으나, 학교명 기반 매칭이 필요할 경우 해당 이슈를 02.knowledge_graph에서 처리해야 함을 참조로 명시 |
| D-4 | **LinkedIn experience 구조 특이사항** (v3 §2.2): company=title(7.1%)인 경우 position 배열에 세부 직책 | 00_data_source_mapping §3.7에 미반영 | **낮음** | Phase 5 LinkedIn 교차 매핑 시 이 구조 차이를 처리해야 함을 주석 추가 |
| D-5 | **v3에서 Vacancy 노드에 seniority_confidence 추가** (v3 §11.2) | 01_company_context §2.1 vacancy에 seniority_confidence 필드가 v25에서 추가됨 (**정합**). 단, 04_graph_schema §1.8 Vacancy 노드 정의에는 seniority_confidence 속성 **누락** | **중간** | 04_graph_schema Vacancy 노드에 `seniority_confidence: FLOAT` 추가 |
| D-6 | **희망 직무 vs 실제 경력 직무 64.9% 불일치** (v3 §4.4) | 00_data_source_mapping §1.2에 "경력 직무를 기준으로 사용"으로 반영 (**정합**). 단, 이 64.9% 불일치를 **직무전환 의도 시그널**로 활용하는 가능성은 언급되지 않음 | **낮음** | v2 로드맵에서 직무전환 의도 감지 피처로 활용 가능성 언급 고려 |
| D-7 | **code-hub 지역 코드 name 6,858건 전부 빈값** (v3 §2.3) | 00_data_source_mapping §9에 미포함 (v3 §12.3에는 있음) | **낮음** | 사용 불가 필드에 code-hub 지역 코드 name 빈값 이슈 추가, 또는 별도 name 매핑 필요성 언급 |

### 2.3 수치 정확성 검증

v25 문서 전반의 fill rate/건수 수치를 v3 실측치와 교차 검증한 결과:

| 항목 | v25 인용 | v3 실측 | 일치 |
|---|---|---|---|
| 이력서 총 건수 | 8,018,110 | 8,018,110 | O |
| 고유 사용자 | 7,780,115 | 7,780,115 | O |
| career 건수 | 18,709,830 | 18,709,830 | O |
| skill 커버리지 | 38.3% | 38.3% | O |
| careerDescription 커버리지 | 16.9% | 16.9% | O |
| selfIntroduction 커버리지 | 64.1% | 64.1% | O |
| BRN 입력률 | 62% | 62% | O |
| 고유 회사명 | 4,479,983 | 4,479,983 | O |
| LinkedIn 프로필 수 | 2,019,293 | 2,019,293 | O |
| code-hub 총 코드 수 | 미명시 | 58,413 | - |
| workcondition.industryCodes 빈배열 | 66.0% | 66.0% | O |
| positionGradeCode fill rate | 39.16% | 39.16% | O |
| positionTitleCode fill rate | 29.45% | 29.45% | O |

**결론**: 수치 정확성은 **100% 일치**. v3 데이터를 충실히 반영하고 있다.

---

## 3. 3-Layer 경계 준수 분석

### 3.1 잘 분리된 부분

| 규칙 | v25 현황 | 평가 |
|---|---|---|
| 추출/정규화 로직 → 02.knowledge_graph | §1.3~1.8, §5, §6, §7이 모두 02.knowledge_graph로 이관 | 우수 |
| 비용/인프라/Neo4j → 03.graphrag | §8 로드맵, §10 LLM 비용, §4-9 Neo4j 구현이 모두 03.graphrag로 이관 | 우수 |
| 재생성 조건 → 03.graphrag | 01/02 문서의 재생성 조건이 regeneration_policy.md로 이관 | 우수 |
| 평가 전략 → 03.graphrag | 05_evaluation_strategy.md가 09_evaluation.md로 완전 이관 | 우수 |

### 3.2 경계 침범 잔여 항목

| # | 위치 | 침범 내용 | 심각도 | 권고 |
|---|---|---|---|---|
| L-1 | 00_data_source_mapping §3.2 compute_duration_months() | Python 구현 코드가 온톨로지 문서에 존재. 이는 "매핑 규칙"이므로 경계선상이지만, 동일 함수가 02.knowledge_graph에도 존재할 수 있어 이중 관리 위험 | **낮음** | pseudo-code 수준으로 유지하되, 구현 정본은 02.knowledge_graph임을 주석으로 명시 |
| L-2 | 00_data_source_mapping §2.5 extract_structured_facet_signals() | job-hub 필드에서 operating_model facet 시그널을 추출하는 **구현 코드**가 온톨로지 문서에 위치 | **낮음** | 매핑 규칙의 일부로 허용 가능하나, 02.knowledge_graph 05_extraction_operations.md와 중복 여부 확인 필요 |
| L-3 | 01_company_context §1 get_category_ceiling() | confidence ceiling 계산 코드. 이는 온톨로지 "정책"이므로 01.ontology에 있는 것이 적절 | 해당없음 | 현재 위치 적절 |

**전체 평가**: 3-Layer 경계 준수는 **v18 대비 개선**. 이관 작업이 대부분 완료되었으며, 잔여 침범은 경계선상의 매핑 규칙 코드로 심각도가 낮다.

---

## 4. 타당성 분석

### 4.1 타당성이 높은 설계 결정

**[V-1] SIE 모델 통합 (v3 신규)**

GLiNER2/NuExtract 1.5 SIE 모델을 온톨로지에 "보조 추출 소스"로 포지셔닝한 것은 적절하다:
- CareerDescription FK 부재(16.9% 커버리지)의 한계를 workDetails(~56%)까지 확장하는 현실적 경로 제시
- Span 기반 추출(Hallucination 없음)의 장점이 Evidence-first 원칙과 정합
- 온톨로지 매핑(§3.4)이 명확: experience.achievements → Outcome, project.tech_stack → Skill
- 다만, SIE 추출 결과의 confidence 수준은 아직 미정의 → 02.knowledge_graph에서 정의 필요

**[V-2] LinkedIn 외부 데이터의 Phase 5 지연 배치**

LinkedIn 데이터를 Phase 5(외부 데이터 통합)에 배치한 것은 현실적이다:
- 동일 인물 매칭(이름+회사명+기간)의 정확도가 미검증
- 한/영 혼재(삼성전자 vs Samsung Electronics)가 심각하여 회사명 정규화가 선행 필요
- confidence 상한 0.65(T3)로 보수적 설정

**[V-3] vacancy.seniority_confidence 추가 (v25 신규)**

JD에서 직급이 명시되면 0.85, 추론 시 0.50~0.70이라는 구간 설정이 합리적이다. designation_codes 기반 seniority의 불확실성(거짓 직명)을 confidence로 반영한 점이 좋다.

**[V-4] freshness_weight의 step vs smooth 모드 제공**

두 모드를 파라미터로 전환 가능하게 설계하고, Phase 0에서 비교 검증하겠다는 프로토콜이 합리적이다. v3 실측 반감기 31.5개월을 smooth 모드의 half_life_days(958일)에 정확히 반영한 점도 좋다.

### 4.2 타당성이 의심되는 설계 결정

**[Q-1] REPLACE 공고의 vacancy_fit INACTIVE 처리**

REPLACE 공고에서 vacancy_fit을 완전 INACTIVE로 처리하고 가중치를 재분배하는 현재 설계는 합리적이지만, **REPLACE 비율이 실제로 얼마인지 전혀 모르는 상태**에서 이 설계를 확정한 것은 리스크가 있다.

- v3 데이터에 job-hub hiring_context 분포 실측이 없음
- REPLACE가 전체 JD의 50%+인 경우(충원 목적이 가장 흔할 수 있음), vacancy_fit(가중치 0.30)이 절반 이상의 매핑에서 비활성화됨
- 03_mapping_features §4.1에 "Phase 0에서 JD 100건 이상 실측" 계획이 있으나, 이는 **온톨로지 설계를 뒤집을 수 있는 결정**이므로 더 이른 시점에 확인해야 함

> **권고**: job-hub에서 hiring_context 키워드("충원", "결원" 등) 빈도를 사전 분석하여, REPLACE 비율의 대략적 추정을 v1 설계 확정 전에 수행

**[Q-2] F3 domain_fit의 cosine_similarity 단독 사용**

F3에서 primary 방법으로 임베딩 cosine_similarity를 사용하고, industry_code 매칭을 "보조(bonus)"로만 사용하는 것은 **본말이 전도**된 설계일 수 있다:

- code-hub INDUSTRY 코드가 구조화되어 있고 3단계 계층 비교가 가능한 상황에서, 임베딩이 primary인 이유가 불명확
- v3에서 code-hub INDUSTRY_SUBCATEGORY 63개, INDUSTRY 936개로 충분히 세분화된 코드 체계가 존재
- 임베딩 비교의 confidence 상한이 0.60으로 제한되어 있어, F3 전체의 confidence가 낮게 고정됨

> **권고**: code-hub industry_code 매칭을 primary로 승격하고, 코드 매칭 실패 시에만 임베딩 폴백을 적용하는 것을 검토. 이 경우 F3 confidence를 0.60→0.80까지 올릴 수 있음

**[Q-3] scope_type 단순 매핑 테이블의 누적 오차**

00_data_source_mapping §3.2의 POSITION_TO_SCOPE 매핑과 01_company_context §2.3의 DESIGNATION_TO_SENIORITY 매핑이 각각 독립적으로 정의되어 있으나, 이 두 매핑이 **동일한 code-hub POSITION_GRADE/TITLE 코드를 참조**하면서도 출력 체계가 다르다(scope_type vs seniority). 변환 체인이 길어질수록 오차가 누적된다:

```
positionGradeCode → scope_type (confidence 0.65)
    → seniority (02_candidate_context §2.1 변환)
        → F5 role_fit 비교 (03_mapping_features)
```

> **권고**: v25 문서에 "scope_type → seniority 변환 체인의 최종 confidence는 개별 confidence의 곱이 아닌, 체인 전체에 대한 단일 confidence를 부여"하는 규칙을 명시. 현재는 각 단계의 confidence가 독립적으로 보이지만 실제로는 연쇄 추정이므로.

---

## 5. 과도한 설계 분석

### 5.1 과도한 부분

| # | 위치 | 내용 | 권고 |
|---|---|---|---|
| O-1 | 01_company_context §2.2 domain_positioning | v1에서 market_segment만 JD에서 추출 가능하고, competitive_landscape/product_description은 v1 제외로 명시. **3개 필드 중 2개가 null인 섹션을 유지하는 이유가 약함** | v1에서는 market_segment를 company_profile 또는 vacancy에 통합하고, domain_positioning 섹션은 v2에서 도입 |
| O-2 | 01_company_context §2.2 structural_tensions | v1에서 Unknown 70%+ 예상, JD만으로 거의 추출 불가. 8개 tension_type taxonomy와 배타성 규칙이 v1에서 실질적으로 사용되지 않음 | v1에서는 structural_tensions를 완전 제외하고, T3/T4 크롤링 활성화 시 도입. taxonomy 정의는 유지하되 "v2 예정"으로 표기 |
| O-3 | 03_mapping_features §2 F4 culture_fit | ACTIVE <10% 예상이면서 27개 조합 매트릭스(v2에서 완성)까지 설계. v1에서 culture_fit 전체를 INACTIVE로 확정하면서도 상세 계산 로직을 유지하는 것은 문서 부피만 증가 | F4 계산 로직을 축소하고 "v2 활성화 시 상세 설계"로 이관 |
| O-4 | 02_candidate_context §2.4 PastCompanyContext temporal_decay | years_since_tenure 기반 4단계 decay(0.90/0.75/0.55/0.40)가 v1에서 실측 없이 정의됨. NICE 현재 시점 데이터로 과거 stage를 추정하는 것 자체가 불확실한데, decay까지 정밀하게 설계한 것은 과도 | v1에서는 단일 decay 0.70 적용, Phase 0 실측 후 단계별 decay 도입 |

### 5.2 파일럿 과부하

v25에서 **"Phase 0/v1 파일럿에서 검증"**으로 미루어진 항목을 전수 조사한 결과:

| # | 항목 | 위치 |
|---|---|---|
| 1 | step vs smooth freshness_weight 비교 | 00_data_source_mapping §3.5 |
| 2 | main_flag=1 복수 존재 빈도 측정 | 00_data_source_mapping §3.1 |
| 3 | designation 기반 seniority 불일치율 30%+ 시 confidence 하향 | 00_data_source_mapping §2.3 |
| 4 | SIE 모델 PoC | v3 §13 Phase 3 |
| 5 | STAGE_SIMILARITY 비대칭 vs 대칭 비교 | 03_mapping_features F1 |
| 6 | overall_match_score 이중 감쇠 vs 단순 평균 비교 | 03_mapping_features §4 |
| 7 | OTHER 비율 30% 초과 시 taxonomy 확장 | 02_candidate_context §2.3 T-1 |
| 8 | F2 SelfIntroduction 경유 0.5x 감쇠 적정성 | 03_mapping_features F2 |
| 9 | REPLACE 공고 비율 실측 (JD 100건) | 03_mapping_features §4.1 |
| 10 | 동일 회사 Career 3건+ 사용자 빈도 | 02_candidate_context §2.1 |
| 11 | F5 ROLE_PATTERN_FIT 캘리브레이션 | 03_mapping_features F5 |
| 12 | F2 vacancy_fit confidence 분포 실측 | 03_mapping_features F2 |
| 13 | Human eval 50건 overall 점수 vs 전문가 평가 | 03_mapping_features §4 |

**13개 항목**이 Phase 0/파일럿에 집중되어 있다. 50건 파일럿으로 이 모든 항목을 유의미하게 검증하기는 **통계적으로 불가능**하다.

> **권고**: 파일럿 항목을 **P0(설계 확정 전 필수)**, **P1(v1 런칭 전 필수)**, **P2(v1 운영 중 수집)**으로 3단계 분류하고, P0는 20건이면 충분한 항목(e.g., REPLACE 비율, main_flag 복수 빈도)으로 제한

---

## 6. 부족한 설계 분석

### 6.1 부족한 부분

| # | 항목 | 현황 | 심각도 | 권고 |
|---|---|---|---|---|
| U-1 | **Skill-Chapter 직접 연결 불가** | v3 §7.3: "경력-스킬 직접 연결 불가 (resume 단위)". 04_graph_schema에서 `(:Chapter)-[:USED_SKILL]->(:Skill)` 엣지가 정의되어 있으나, **실제 데이터에서는 resume.skill이 경력별이 아닌 이력서 단위**로 입력됨. 이 근본적 한계가 04_graph_schema에 명시되지 않음 | **높음** | 04_graph_schema USED_SKILL 엣지에 "v1에서는 전체 resume의 skill을 모든 Chapter에 연결하거나, 최신 Chapter에만 연결하는 전략 중 선택 필요" 명시. 또는 SIE 모델의 project.tech_stack 추출로 Chapter-Skill 직접 연결 가능성 언급 |
| U-2 | **Graph Schema에서 NEEDS_SIGNAL 엣지 생성 방법 미정의** | 04_graph_schema §2.2: `(:Vacancy)-[:NEEDS_SIGNAL]->(:SituationalSignal)` 엣지가 정의되었으나, **JD에서 어떻게 SituationalSignal을 추출하여 이 엣지를 생성하는지** 추출 규칙이 01.ontology 어디에도 없음 | **중간** | vacancy.hiring_context → SituationalSignal 매핑 규칙(예: BUILD_NEW → NEW_SYSTEM_BUILD, EARLY_STAGE) 정의 필요. 현재 F2의 VACANCY_SIGNAL_ALIGNMENT가 역방향으로 이 매핑을 암시하지만, 엣지 생성 규칙으로는 불충분 |
| U-3 | **Organization 노드의 company_id 결정 미확정** | 00_data_source_mapping §0 "ID 연결"에 "확인 필요, 키가 난잡한데 어느 것을 키로 잡을 것인지" 주석이 **v25에서도 여전히 미해결**. job.user_ref_key vs job.workspace_id 중 어느 것이 company_id인지 확정되지 않음 | **높음** | 이는 v1 구현 전 **반드시 확정**해야 하는 결정. job-hub 데이터에서 두 키의 분포/유니크 수를 확인하여 확정 |
| U-4 | **Person 노드에 name 필드의 PII 처리 규칙 미정의** | 04_graph_schema §1.1 Person에 `name: STRING`이 있고, v3에서 `profile.name → REDACTED`로 PII 마스킹됨. 그러나 **Neo4j에 저장할 때 마스킹된 name을 그대로 저장하는지, 원본 name을 저장하는지** 규칙 미정의 | **중간** | PII 처리 정책을 02.knowledge_graph 04_pii_and_validation.md에서 정의하되, 온톨로지에서는 "name은 PII 처리 정책에 따라 마스킹/해싱 적용"을 명시 |
| U-5 | **LinkedIn 데이터의 동일 인물 매칭 키 전략** | 00_data_source_mapping §3.7: "이름+회사명+기간 조합으로 추정"이라고만 언급. 매칭 confidence, false positive 처리, 매칭 실패 시 fallback이 미정의 | **낮음** | Phase 5 예정이므로 현재 심각도는 낮으나, Phase 5 진입 전 사전 분석 필요성 명시 |

---

## 7. 문서 간 일관성 분석

### 7.1 용어/참조 불일치

| # | 불일치 내용 | 위치 1 | 위치 2 | 권고 |
|---|---|---|---|---|
| C-1 | **v12 실측**이라는 레이블이 여전히 사용됨 | 00_data_source_mapping §3.2 테이블 헤더 "v12 실측 fill rate" | v3 데이터 분석이 최신임 | "v12 실측" → "v3 실측" 또는 "실측"으로 통일 |
| C-2 | **CompanyContext JSON 스키마 버전** | 01_company_context §3: `$schema: "CompanyContext_v4"` | 02_candidate_context §3: `$schema: "CandidateContext_v4"` | 스키마 버전은 일관(v4). 다만 ontology 디렉토리 버전(v25)과의 관계가 v24 주석에만 설명됨. 혼란 방지를 위해 README 또는 00 문서에 버전 규약 요약 추가 |
| C-3 | **POSITION_GRADE vs DESIGNATION 코드** | 00_data_source_mapping §2.3: `lookup_common_code(type="POSITION_GRADE")` | v3-db-schema §3.2: code-hub에 `DESIGNATION`과 `POSITION_GRADE`가 별도 존재 | job-hub overview.designation_codes가 참조하는 code-hub 타입이 DESIGNATION인지 POSITION_GRADE인지 확정 필요 |
| C-4 | **SituationalSignal taxonomy 개수** | 02_candidate_context §2.3: 14개(카테고리 포함 목록에 13개 + OTHER = 14개) | v3 §4.7: "14개 taxonomy" 나열 시 MONETIZATION이 v3에는 없으나 v25에는 있고, M_AND_A/PIVOT이 v3에는 있으나 v25에는 없음 | **taxonomy 불일치 해소 필요**. v25 기준으로 v3 참조를 업데이트하거나, v25 taxonomy가 최신임을 명시 |

### 7.2 참조 링크 정합성

| # | 문서 | 참조 경로 | 유효성 |
|---|---|---|---|
| R-1 | 00_data_source_mapping §1.3 | `02.knowledge_graph/results/extraction_logic/v18/06_normalization.md` | 확인 필요 (실제 경로가 `02.knowledge_graph/v18/`인지) |
| R-2 | 01_company_context §2.1 | `02.knowledge_graph/results/extraction_logic/v18/03_prompt_design.md` | 동일 |
| R-3 | 00_data_source_mapping §8 | `03.graphrag/results/implement_planning/separate/v8/shared/implementation_roadmap.md` | 확인 필요 |

> **권고**: 참조 경로의 `results/extraction_logic/` 부분이 실제 디렉토리 구조와 일치하는지 일괄 확인 필요. 경로 불일치는 문서 탐색 시 큰 혼란을 유발함.

---

## 8. 문서별 상세 리뷰

### 8.1 00_data_source_mapping.md

**강점**:
- v3 데이터 분석의 실측치를 충실히 반영하여 fill rate, 품질 수치가 정확
- LinkedIn 외부 데이터 매핑(§3.7)이 Phase 5 범위로 적절히 배치
- 사용 불가 필드 목록(§9)이 v3 §12와 거의 완전 일치
- SIE 모델 보조 추출(§3.2 D5)이 온톨로지 매핑과 연결

**개선 필요**:
- §0 ID 연결: `company_id` 키 미확정 주석이 v25까지 잔존 (U-3)
- §3.2: "v12 실측 fill rate" 레이블 잔존 (C-1)
- §3.3 domain_depth: `workJobField.industryCodes`(66% 빈배열)를 job_codes에 extend하는 로직에서, INDUSTRY_SUBCATEGORY와 JOB_CLASSIFICATION_SUBCATEGORY를 혼합하여 Counter에 넣는 잠재적 문제. 두 코드 체계가 다른데 같은 Counter에서 most_common을 구하면 의미가 없음

> **[Bug] domain_depth 계산의 코드 체계 혼합**:
> ```python
> # 현재 코드 (§3.3):
> job_codes.extend(career.jobClassificationCodes)  # JOB_CLASSIFICATION 코드
> job_codes.extend(wjf.industryCodes)               # INDUSTRY_SUBCATEGORY 코드
> # → 두 코드 체계를 같은 Counter에서 집계하면 의미 없는 결과
> ```
> **권고**: jobClassificationCodes와 industryCodes를 별도로 집계하거나, primary_domain 결정 시 jobClassificationCodes만 사용

### 8.2 01_company_context.md

**강점**:
- 데이터 소스 Tier 정의(T1~T5)와 confidence ceiling이 일관적이고 합리적
- 다중 공고 처리 원칙(§2.3)이 명확 — company_profile/stage_estimate 공유, vacancy/role_expectations 독립
- hiring_context taxonomy(BUILD_NEW/SCALE_EXISTING/RESET/REPLACE)가 JD 탐지 패턴과 함께 정의
- Evidence 통합 모델의 TypeScript 정의가 정밀

**개선 필요**:
- structural_tensions(§2.2 T3+T4): v1에서 실질적으로 사용되지 않는 8개 taxonomy에 과도한 문서 분량(O-2)
- operating_model v1 ROI 검토 주석([v21]): v1에서 LLM 기반 facet 추출 생략 권장이 명확하여 좋으나, 이 결정이 F4 culture_fit INACTIVE와 연쇄된다는 점을 명시적으로 연결하면 더 좋음
- stage_label taxonomy: EARLY(설립 3년 이내 AND 직원 30명 미만)의 AND 조건이 모든 초기 스타트업을 포착하지 못할 수 있음(설립 5년인데 직원 15명인 경우). OR 조건 또는 추가 규칙 검토

### 8.3 02_candidate_context.md

**강점**:
- NEW_COMER 제외 결정과 v2 로드맵이 명확
- Experience-Chapter 매핑 원칙([S-3])이 상세하고 에지 케이스 처리(동일 회사 연속 근무) 정의
- ScopeType → Seniority 변환 규칙이 완전 — IC의 세분화(연수 기반)까지 정의
- CareerDescription FK 부재 제약과 SIE 보완 경로가 잘 연결
- RoleEvolution의 오름차순 정렬 전제([v24])가 명시

**개선 필요**:
- §2.6 Person 보강 속성: `name` 필드의 소스가 `profile.name`으로 명시되었으나, PII 처리 후 형태 미정의 (U-4)
- §2.5 WorkStyleSignals: v1에서 20~30% 미만 추출 가능 → F4 INACTIVE → 이 섹션의 상세 인터페이스 정의가 v1에서 필요한지 의문 (O-3과 연결)
- §2.8 RoleEvolution: DOWNSHIFT 패턴의 처리가 미정의. 상위→하위 이동이 "부정적"인지 "선택적 전환"인지에 따라 role_fit 점수가 달라질 수 있음

### 8.4 03_mapping_features.md

**강점**:
- F1~F5 전체의 필수 입력/INACTIVE 조건이 일관되게 정의
- VACANCY_SIGNAL_ALIGNMENT 매핑 테이블이 14개 taxonomy 전체를 커버하는지 검증 주석([v24])이 좋음
- confidence 전파 규칙(§2 하단 테이블)이 5개 피처 전체에 대해 통일적으로 정의
- REPLACE 공고 처리와 가중치 재분배 메커니즘이 상세

**개선 필요**:
- F1 STAGE_SIMILARITY: 4x4 매트릭스의 16개 값이 아직 전문가 판단 기반. 이 자체는 문제가 아니나, **이 값들이 파일럿 20~50건으로 캘리브레이션 가능한지** 통계적 검증이 필요 (16개 파라미터를 50건으로 피팅하는 것은 과적합 위험)
- F3 domain_fit: 임베딩 primary + 코드 보조 구조의 타당성 의문 (Q-2)
- F5 role_fit: ROLE_PATTERN_FIT 테이블이 7개 조합만 정의, 나머지 ~23개 조합은 기본값 0.50. 실제로 자주 발생하는 조합(JUNIOR-IC_DEPTH, MID-GENERALIST 등)의 명시적 정의가 부족
- §4 FEATURE_WEIGHTS: 가중치 합계 0.25+0.30+0.20+0.10+0.15 = 1.00 (정합 확인됨)

### 8.5 04_graph_schema.md

**강점**:
- 9개 노드 정의가 CompanyContext/CandidateContext와 정합
- Mermaid 다이어그램이 전체 구조를 시각적으로 표현
- USED_SKILL recency 결정에서 "별도 속성 추가 안 함, Chapter.period로 추론" 결정이 합리적
- v1 범위 밖 관계(§2.4)의 v2 로드맵이 명확

**개선 필요**:
- Vacancy 노드에 `seniority_confidence: FLOAT` 누락 (D-5)
- Chapter-USED_SKILL 엣지의 근본적 한계 미명시 (U-1)
- NEEDS_SIGNAL 엣지 생성 규칙 미정의 (U-2)
- Organization.org_id가 company_id와 동일하다고 되어 있으나, company_id 자체가 미확정 (U-3)

### 8.6 05_evaluation_strategy.md

03.graphrag로 완전 이관 완료. 4줄의 이관 안내문만 남아 있어 적절하다.

---

## 9. 핵심 액션 아이템 요약

### 9.1 Critical (v1 구현 전 필수)

| # | 항목 | 관련 이슈 |
|---|---|---|
| **A-1** | company_id 키 확정 (user_ref_key vs workspace_id) | U-3 |
| **A-2** | Chapter-USED_SKILL 엣지의 실제 데이터 매핑 전략 확정 | U-1 |
| **A-3** | REPLACE 공고 비율 사전 추정 (job-hub 키워드 분석) | Q-1 |
| **A-4** | domain_depth 계산의 코드 체계 혼합 버그 수정 | §8.1 Bug |

### 9.2 High (v1 품질 영향)

| # | 항목 | 관련 이슈 |
|---|---|---|
| **A-5** | Vacancy 노드에 seniority_confidence 속성 추가 | D-5 |
| **A-6** | NEEDS_SIGNAL 엣지 생성 규칙 정의 | U-2 |
| **A-7** | F3 domain_fit: 코드 매칭 primary 승격 검토 | Q-2 |
| **A-8** | 파일럿 항목 13개 → P0/P1/P2 3단계 우선순위 분류 | §5.2 |

### 9.3 Medium (문서 품질)

| # | 항목 | 관련 이슈 |
|---|---|---|
| **A-9** | "v12 실측" → "v3 실측" 레이블 통일 | C-1 |
| **A-10** | SituationalSignal taxonomy v25 vs v3 불일치 해소 | C-4 |
| **A-11** | 참조 경로(`results/extraction_logic/` 등) 실제 디렉토리와 일치 확인 | R-1~R-3 |
| **A-12** | POSITION_GRADE vs DESIGNATION code-hub 타입 확정 | C-3 |
| **A-13** | Person.name PII 처리 정책 명시 | U-4 |

### 9.4 Low (v2 대비)

| # | 항목 | 관련 이슈 |
|---|---|---|
| **A-14** | Role 노드 ~30개 JobCategory 계층 확정 | D-1 |
| **A-15** | 비표준 스킬 97.6% 처리 전략 명시 | D-2 |
| **A-16** | LinkedIn experience 구조 특이사항 반영 | D-4 |
| **A-17** | 직무전환 의도 시그널 활용 가능성 검토 | D-6 |

---

## 10. Critical 이슈 기원 추적 (Archaeology)

old/ 디렉토리를 역순 검색하여 Critical 4건의 최초 발생 버전과 경위를 추적한 결과:

### A-1. company_id 키 미확정 — v12에서 도입, v14에서 의문 제기, **13개 버전간 미해결**

| 시점 | 버전 | 내용 |
|---|---|---|
| **최초 도입** | **v12** (2026-03-10) | 00_data_source_mapping §2.1에 `company_id → job.user_ref_key 또는 job.workspace_id` 매핑 정의. 이 시점에서는 의문 없이 양자를 병렬 나열 |
| 의문 제기 | **v14** | 설계 원칙에 "확인 필요, 키가 난잡한데 어느 것을 키로 잡을 것인지" 주석 추가 |
| 방치 | v14→v25 (12개 버전) | 주석이 그대로 복사되며 **한 번도 해결 시도 없음** |

**분석**: job-hub의 `user_ref_key`와 `workspace_id`가 동일 기업을 서로 다르게 식별할 수 있어, 이 결정이 Organization 노드의 중복/분리에 직접 영향을 미친다. 13개 버전 동안 미해결된 것은 **job-hub 데이터 접근/분석이 지연**되었기 때문으로 추정된다.

**권고**: v26에서 job-hub 데이터로 두 키의 유니크 수, 교차 관계(1:1인지 1:N인지)를 실측하여 확정. 이것 없이는 Organization 노드 생성 자체가 불가능.

---

### A-2. Chapter-USED_SKILL 엣지 데이터 불일치 — v4에서 도입, **22개 버전간 미인지**

| 시점 | 버전 | 내용 |
|---|---|---|
| **최초 도입** | **v4** (2026-03-08) | 04_graph_schema에 `(:Chapter)-[:USED_SKILL]->(:Skill)` 엣지 정의. Chapter(경력) 단위로 스킬이 연결되는 설계 |
| 데이터 매핑 | **v11** (2026-03-09) | 00_data_source_mapping에서 tech_stack 소스를 `Skill 테이블 (type=HARD, **resume_id 기준**)` 으로 명시 |
| FK 부재 인지 | **v12** (2026-03-10) | CareerDescription의 career_id FK 부재는 인지([D4])했으나, **Skill 테이블의 동일한 한계(resume 단위, career 단위 아님)는 명시하지 않음** |
| 방치 | v4→v25 (22개 버전) | Graph Schema의 USED_SKILL 엣지와 실제 데이터(resume 단위)의 불일치가 **한 번도 명시적으로 언급되지 않음** |

**분석**: CareerDescription FK 부재(D4)와 **동일한 구조적 문제**이지만, CareerDescription은 v12에서 명시적으로 인지된 반면 Skill은 간과되었다. 이유는 Skill 데이터가 resume.skill 테이블에서 오고, resume_id로만 JOIN 가능하다는 사실이 Graph Schema 설계 시점(v4)에 고려되지 않았기 때문이다.

**영향 범위**:
- Chapter-Skill 연결이 불정확하면 F3 domain_fit의 스킬 기반 보조 매칭도 영향
- SIE 모델(GLiNER2)의 project.tech_stack 추출이 이 한계를 부분적으로 해소할 수 있음 (Chapter별 tech_stack 직접 추출)

**권고**: v26 04_graph_schema USED_SKILL 엣지에 다음 중 하나를 명시:
1. "v1에서는 resume 전체 skill을 최신 Chapter에만 연결" (보수적)
2. "v1에서는 resume 전체 skill을 모든 Chapter에 연결, SIE 보완 시 Chapter별로 정밀화" (확장적)

---

### A-3. REPLACE 공고 비율 미실측 — v16에서 도입, v21에서 위험 인지, **실측 없이 9개 버전 경과**

| 시점 | 버전 | 내용 |
|---|---|---|
| **최초 도입** | **v16** (2026-03-10) | 03_mapping_features F2에 REPLACE hiring_context 추가. vacancy_fit을 INACTIVE로 처리하고 role_fit으로 가중치 재분배하는 로직 도입. 태그: `[v16] REPLACE 공고 매칭 전략 보완` |
| 위험 인지 | **v21** (2026-03-13) | "REPLACE가 전체 JD의 30% 이상이면 매칭 품질에 상당한 영향" 경고 추가 |
| 격상 | **v22** (2026-03-13) | "Phase 0 **최우선 과제**로 격상", "50%+일 경우 Go/No-Go 의사결정 항목" 추가 |
| 현재 | v25 | Phase 0 실측 계획은 있으나 **아직 미실행** |

**분석**: REPLACE는 한국 채용 시장에서 "충원/결원/대체" 목적의 공고로, 직관적으로 전체 공고의 상당 비율(30~60%)을 차지할 가능성이 높다. v22에서 Go/No-Go 항목으로 격상한 것은 적절한 판단이나, **v16 도입 시점에 사전 분석 없이 설계한 것이 근본 원인**이다.

**권고**: Phase 0 착수 전에 job-hub에서 `overview.descriptions` 텍스트의 "충원/결원/대체" 키워드 빈도를 SQL로 간단히 실측하여 대략적 비율 추정. 이것은 LLM 없이도 가능한 작업.

---

### A-4. domain_depth 코드 체계 혼합 버그 — v11에서 도입, **15개 버전간 미발견**

| 시점 | 버전 | 내용 |
|---|---|---|
| **최초 도입** | **v11** (2026-03-09) | 00_data_source_mapping에 `extract_domain_depth_structured()` 함수 신규 추가. 태그: `[v11 신규]` |
| 데이터 분석 | **v12** (2026-03-10) | v12 데이터 분석에서 `career.jobClassificationCodes`(JOB_CLASSIFICATION_SUBCATEGORY)와 `workcondition.industryCodes`(INDUSTRY_SUBCATEGORY)를 **별도 코드 체계**로 명확히 문서화. 그러나 **함수 코드는 수정하지 않음** |
| 방치 | v11→v25 (15개 버전) | 함수 코드가 그대로 복사됨. 변수명 `industry_codes`에 JOB_CLASSIFICATION 코드를 넣는 혼란도 유지 |

**버그 상세**:
```python
# v11에서 도입된 코드 (v25까지 동일):
job_codes = []
job_codes.extend(career.jobClassificationCodes)     # ← JOB_CLASSIFICATION_SUBCATEGORY (242개)
job_codes.extend(wjf.industryCodes)                  # ← INDUSTRY_SUBCATEGORY (63개) — 다른 코드 체계!

code_counts = Counter(job_codes)                     # ← 두 체계 혼합 집계
primary_code, count = code_counts.most_common(1)[0]
lookup_common_code(type="JOB_CLASSIFICATION_SUBCATEGORY", code=primary_code)
# ↑ INDUSTRY_SUBCATEGORY 코드가 most_common이면 lookup 실패 또는 오매칭
```

**의도성 판단: 비의도적(실수)**
- 변수명 혼란: v11 원본에서 `industry_codes`라는 변수에 jobClassificationCodes를 넣음
- v12 데이터 분석가가 두 코드 체계를 별도로 문서화했지만, 함수 코드를 교차 검증하지 않음
- lookup 타입이 `JOB_CLASSIFICATION_SUBCATEGORY`로 하드코딩되어 있어 INDUSTRY 코드 유입 시 실패

**영향 범위**:
- `workcondition.industryCodes`가 66% 빈배열이므로, 실제 영향을 받는 이력서는 **34% × 해당 코드가 most_common인 경우**로 제한적
- 그러나 영향을 받는 케이스에서는 primary_domain이 완전히 잘못 결정됨

**권고**: 즉시 수정 — `industryCodes`를 Counter에서 제거하거나, 별도 `industry_counter`로 분리하여 domain_depth와 industry_depth를 독립 계산

---

### Critical 이슈 기원 요약

| # | 이슈 | 최초 도입 | 미해결 기간 | 근본 원인 |
|---|---|---|---|---|
| A-1 | company_id 키 미확정 | **v12** | 13개 버전 | job-hub 데이터 접근/분석 지연 |
| A-2 | USED_SKILL 데이터 불일치 | **v4** | 22개 버전 | Graph Schema 설계 시 데이터 구조 미확인 |
| A-3 | REPLACE 비율 미실측 | **v16** | 9개 버전 | 사전 데이터 분석 없이 설계 |
| A-4 | domain_depth 코드 혼합 | **v11** | 15개 버전 | 코드 리뷰 부재, 변수명 혼란 |

**공통 패턴**: 4건 모두 **"설계 시점에 실제 데이터를 확인하지 않고 가정에 기반하여 정의"**한 것이 근본 원인이다. v12에서 데이터 분석을 도입한 것이 큰 진전이었으나, 기존 설계(v4~v11)의 가정을 소급 검증하지는 않았다.

---

## 11. v18 리뷰 대비 변경 추적

v18 리뷰에서 지적된 주요 항목의 v25 반영 현황:

| v18 리뷰 항목 | v25 반영 | 상태 |
|---|---|---|
| README 버전 참조 업데이트 | 미확인 (README.md 미읽음) | 확인 필요 |
| Vector + Graph 하이브리드 검색 위치 명확화 | 03.graphrag로 이관됨 | 해결 |
| 3-Layer 경계 정리 | 추출/비용/인프라 이관 완료 | 해결 |
| 파일럿 의존 항목 축소 | **오히려 증가** (13개) | 미해결 |
| 과도한 설계 축소 | 부분 개선 (이관), 부분 유지 (O-1~O-4) | 부분 해결 |
