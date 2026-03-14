> 작성일: 2026-03-12
> 01.ontology/results/schema/v24/00_data_source_mapping.md §6에서 이동.
> 데이터 품질/coverage 메트릭을 추출 영역으로 분리.

---

## 1. resume-hub 필드 가용성 (실측)

| 온톨로지 필드 | resume-hub 소스 필드 | **실측 fill rate** | 비고 |
| --- | --- | --- | --- |
| company | Career.companyName | **99.96%** (18.7M건) | 4,479,983 고유값, 정규화 필수 |
| period | Career.period.period | **~100%** | daysWorked 100% 제로 -> 직접 계산 |
| positionTitleCode | Career.positionTitleCode | **29.45%** | 직책 코드 |
| positionGradeCode | Career.positionGradeCode | **39.16%** | 직급 코드 |
| jobClassificationCodes | Career.jobClassificationCodes | **~100%** (경력 보유자) | 242개 코드, codehub 100% 매핑 |
| workDetails | Career.workDetails | **~56%** (중앙값 96자) | 정보량 제한 |
| CareerDescription | CareerDescription.description | **16.9%** (1,351,836) | 중앙값 527자, **career_id FK 없음** |
| SelfIntroduction | SelfIntroduction.description | **64.1%** (7,962,522) | 중앙값 1,320자 |
| Skill (HARD) | Skill 테이블 | **38.3%** (3,074,732) | 6.77개/이력서, **97.6% 비표준** |
| departmentName | Career.departmentName | **58.9%** | scope_type/role 추론 보조 |

## 2. job-hub 필드 가용성

| 온톨로지 필드 | job-hub 소스 필드 | 예상 fill rate | 비고 |
| --- | --- | --- | --- |
| industry_code | overview.industry_codes | 90%+ | 대부분 공고에 산업 코드 존재 |
| job_classification | overview.job_classification_codes | 85%+ | 직무 분류 코드 |
| tech_stack (구조화) | skill 테이블 | 60~70% | 일부 공고는 스킬 미입력 |
| designation_codes | overview.designation_codes | 40~50% | 직급 정보 선택 입력 |
| descriptions (JD 본문) | overview.descriptions (JSONB) | 95%+ | **Vacancy.evidence_chunk 소스** |
| employment_types | overview.employment_types | 90%+ | 고용 형태 |
| work_schedule_options | work_condition.work_schedule_option_types | 50~60% | 선택 입력 |

> **주의**: job-hub 데이터 상세 분석(레코드 수, 품질, 커버리지)은 **별도 분석 필요** - Phase 4-1

## 3. Graceful Degradation 전략

| 구조화 데이터 | 누락 시 fallback | confidence 영향 |
| --- | --- | --- |
| industry_codes | NICE industry_code 사용 | confidence 유지 |
| designation_codes | JD 텍스트에서 LLM 추출 | confidence -0.10 |
| skill 테이블 | JD/이력서 텍스트에서 LLM 추출 | confidence -0.05 |
| positionTitleCode | positionGradeCode -> workDetails LLM | confidence -0.15~-0.25 |
| jobClassificationCodes | 임베딩 유사도 fallback | confidence -0.10 |
| CareerDescription | SelfIntroduction fallback | confidence -0.10 |

## 4. 비정형 값 비교 품질 모니터링

| 지표 | 산식 | 목표치 | 비고 |
| --- | --- | --- | --- |
| **스킬 코드 매칭률** | 경량 정규화 성공 건 / 전체 스킬 건 | 참고용 (실측 ~2.4%) | 낮아도 임베딩이 보완 |
| **임베딩 매칭 커버리지** | 임베딩 매칭 성공 건 / 코드 미매칭 건 | >= 70% | 임베딩 모델의 스킬명 이해도 |
| **임베딩 매칭 정확도** | human eval 샘플 10건 정확률 | >= 85% | 월간 샘플링 검증 |
| **전공/직무 임베딩 유사도 분포** | 매칭 쌍의 similarity 분포 | 중앙값 >= 0.80 | threshold 조정 근거 |

## 5. 피처별 v1 활성화 전망

> 데이터 소스 관점의 병목 분석으로 참조용

| 피처 | 주요 데이터 병목 (본 문서 범위) |
| --- | --- |
| F1 stage_match | 회사명->Organization 정규화 (4.48M 고유값), NICE 매핑 |
| F2 vacancy_fit | careerDescription **16.9%** 보유율이 SituationalSignal 추출 병목 |
| F3 domain_fit | industryCodes 66% 빈배열이나 NICE/codehub/PastCompanyContext 보완 가능 |
| F4 culture_fit | work_style_signals 추출 가능 데이터 부재 |
| F5 role_fit | positionGrade/Title 저입력 (29-39%) |

## [v15] 6. 미확인 기업(Unknown Organization) 영향 분석

BRN 부재(40%) × NICE fuzzy 매칭 실패(40%) = **전체 Organization의 ~16%가 "미확인 기업"** 노드로 생성된다 (org_id = hash(companyName_normalized)).

미확인 기업의 속성: stage_label = "UNKNOWN", industry_code = null, employee_count = null

### 피처 활성화 영향

| 피처 | 미확인 기업 Chapter | 영향 |
|---|---|---|
| F1 stage_match | INACTIVE (past_company_context.stage = UNKNOWN) | 해당 Chapter의 stage 경험이 매칭에 반영되지 않음 |
| F3 domain_fit | industry code 보너스 불가 (code_match_bonus = 0) | embedding similarity만으로 평가, 보너스 최대 0.25 손실 |
| F2 vacancy_fit | 영향 없음 (SituationalSignal은 텍스트 기반) | — |
| F5 role_fit | 영향 없음 (scope_type은 텍스트 기반) | — |

### 전체 매칭 품질 영향 추정

- 미확인 기업 Chapter 비율: ~16%
- 후보당 평균 3개 Chapter 중 1개가 미확인 기업일 확률: ~40%
- 영향: 해당 후보의 F1에서 "최적 매칭 Chapter"가 미확인 기업일 경우, 차선 Chapter로 대체되어 stage_match 점수 하락
- **Phase 0 실측 과제**: PoC 20건에서 미확인 기업 비율을 실측하고, F1/F3 활성화율에 미치는 영향을 정량화한다.
