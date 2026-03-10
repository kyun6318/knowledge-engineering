# 10. 필드 선별력(Selectivity) 및 MCP 필터 활용도 분석

> 분석일: 2026-03-03 | 데이터베이스: `import_resume_hub_tmp`
> 분석 대상: 에이전트 MCP 필터 후보 20개 필드 (Enum 14개 + Array 6개)

---

## 1. Filter Score 산출 방식

```
Filter Score = Coverage × Cardinality_Score × Evenness
```

### 각 구성 요소 정의

| 구성 요소 | 공식 | 설명 |
|-----------|------|------|
| **Coverage** | `1 - (null 또는 empty 비율)` | 해당 필드에 유효한 값이 있는 레코드 비율. 1.0 = 모든 레코드에 값 존재 |
| **Cardinality_Score** (Enum) | `exp(-0.5 × ((log10(distinct) - 1.0) / 1.5)²)` | 고유값 수의 적절성. Gaussian 커널 기반으로 **최적 고유값 수 = 10개** (log10(10)=1.0)에서 1.0, 이탈 시 감쇄. σ=1.5로 완만한 감쇄 |
| **Cardinality_Score** (Array) | `exp(-0.5 × ((log10(distinct) - 2.477) / 1.5)²)` | Array 필드는 **최적 고유값 수 = 300개** (log10(300)≈2.477). 더 높은 카디널리티를 허용 |
| **Evenness** | `1 - (가장 빈번한 값의 점유 비율)` | 값 분포의 균등성. Top1 값이 전체의 X%를 차지하면 Evenness = 1-X/100. 1.0에 가까울수록 균등 분포 |

> **설계 근거**: Filter Score는 MCP 에이전트가 필터 조건으로 사용할 필드의 "검색 변별력"을 종합 평가한다.
> - **Coverage가 낮으면** → 필터 적용 시 대량 레코드 누락 (recall 저하)
> - **Cardinality가 너무 낮으면** (예: 2값) → 필터 적용 효과 미미, 너무 높으면 (예: 100만 고유값) → 사실상 자유 텍스트와 동일하여 필터로 부적합
> - **Evenness가 낮으면** → 특정 값에 편중되어 필터의 실질적 분류 효과 없음 (예: 98%가 단일값)
>
> **Cardinality_Score의 Gaussian 커널**: log-scale에서 정규분포 형태로 최적 카디널리티에서 1.0, 이탈 시 부드럽게 감쇄. Enum(최적 10개)과 Array(최적 300개) 필드의 특성 차이를 반영.

### 검증 예시

`county_codes` (Array, 순위 1위):
- Coverage = 0.871
- distinct = 63 → log10(63) = 1.799 → Cardinality_Score = exp(-0.5 × ((1.799 - 2.477) / 1.5)²) = exp(-0.5 × 0.204) ≈ **0.903**
- Top1 집중도 = 0.3% → Evenness = 1 - 0.003 = **0.997**
- Filter Score = 0.871 × 0.903 × 0.997 ≈ **0.784** (보고값 0.7832과 근사 — 반올림 차이)

### 등급 기준

| Filter Score | 등급 | 필터 활용 권고 |
|-------------|------|-------------|
| ≥ 0.5 | 우수 | 주요 필터 조건으로 적극 활용 |
| 0.2 ~ 0.5 | 양호 | 보조 필터 조건으로 활용 가능 |
| 0.1 ~ 0.2 | 주의 | 단독 필터로는 부적합, 조합 필터로만 활용 |
| < 0.1 | 비추천 | 필터 조건으로 부적합 (Coverage, Cardinality, 또는 Evenness 중 하나 이상 극단적으로 낮음) |

---

## 2. 필드 선별력 종합 랭킹

| 순위 | 필드 | 타입 | 테이블 | Coverage | Distinct | Top1 집중도 | Filter Score | 등급 |
|------|------|------|--------|--------:|--------:|----------:|------------:|------|
| 1 | `county_codes` | Array | workcondition | 0.871 | 63 | 0.3% | **0.7832** | 우수 |
| 2 | `job_classification_codes` | Array | workcondition | 0.826 | 914 | 4.1% | **0.7520** | 우수 |
| 3 | `school_type` | Enum | education | 1.000 | 5 | 39.9% | **0.5893** | 우수 |
| 4 | `final_education_level` | Enum | resume | 1.000 | 5 | 43.4% | **0.5546** | 우수 |
| 5 | `gender` | Enum | profile | 1.000 | 3 | 52.5% | **0.4468** | 양호 |
| 6 | `job_keyword_codes` | Array | workcondition | 0.484 | 619 | 31.2% | **0.3261** | 양호 |
| 7 | `industry_codes` | Array | workcondition | 0.340 | 242 | 5.6% | **0.3204** | 양호 |
| 8 | `career_type` | Enum | resume | 1.000 | 2 | 69.1% | **0.2772** | 양호 |
| 9 | `visibility_type` | Enum | resume | 1.000 | 3 | 71.0% | **0.2731** | 양호 |
| 10 | `position_grade_code` | Enum | career | 0.392 | 22 | 44.0% | **0.2136** | 양호 |
| 11 | `area_code` | Enum | profile | 0.718 | 258 | 57.8% | **0.1945** | 주의 |
| 12 | `industry_keyword_codes` | Array | workcondition | 0.183 | 1204 | 3.8% | **0.1625** | 주의 |
| 13 | `employment_types` | Array | workcondition | 0.801 | 7 | 64.6% | **0.1570** | 주의 |
| 14 | `academic_status` | Enum | education | 1.000 | 7 | 86.2% | **0.1375** | 주의 |
| 15 | `final_education_status` | Enum | resume | 1.000 | 7 | 86.7% | **0.1319** | 주의 |
| 16 | `position_title_code` | Enum | career | 0.294 | 17 | 64.1% | **0.1044** | 주의 |
| 17 | `employment_status` | Enum | career | 1.000 | 2 | 89.5% | **0.0940** | 비추천 |
| 18 | `job_search_status` | Enum | profile | 1.000 | 2 | 96.3% | **0.0333** | 비추천 |
| 19 | `complete_status` | Enum | resume | 1.000 | 4 | 98.3% | **0.0166** | 비추천 |
| 20 | `work_arrangement_type` | Enum | workcondition | 0.975 | 2 | 100.0% | **0.0000** | 비추천 |

**Array 필드 평균 Filter Score = 0.391, Enum 필드 평균 = 0.171 (2.3배 차이)**

---

## 3. Enum 필드 상세

### resume.resume (n=8,018,110)

#### final_education_level (최종 학력) — Score: 0.5546

| 값 | 건수 | 비율 |
|----|-----:|-----:|
| BACHELOR | 3,481,044 | 43.4% |
| HIGH_SCHOOL | 1,980,738 | 24.7% |
| ASSOCIATE | 1,801,169 | 22.5% |
| GRADUATE | 401,364 | 5.0% |
| NONE | 353,795 | 4.4% |

#### career_type (경력 구분) — Score: 0.2772

| 값 | 건수 | 비율 |
|----|-----:|-----:|
| EXPERIENCED | 5,540,880 | 69.1% |
| NEW_COMER | 2,477,230 | 30.9% |

#### visibility_type (공개 상태) — Score: 0.2731

| 값 | 건수 | 비율 |
|----|-----:|-----:|
| PUBLIC | 5,691,631 | 71.0% |
| PRIVATE | 2,097,262 | 26.2% |
| HEADHUNTER_ONLY | 229,217 | 2.9% |

에이전트 필터 시 PUBLIC만 접근 가능하므로 실질 대상은 전체의 71%.

#### complete_status (완성도) — Score: 0.0166 [비추천]

98.3%가 COMPLETED. 필터 의미 없음.

#### final_education_status (학적 상태) — Score: 0.1319 [주의]

86.7%가 GRADUATED. `final_education_level`과 조합 시 보완적 가치 있으나 단독 사용 비추천.

---

### user_profile.profile (n=7,780,115)

#### gender (성별) — Score: 0.4468

| 값 | 건수 | 비율 |
|----|-----:|-----:|
| MALE | 4,086,056 | 52.5% |
| FEMALE | 3,686,369 | 47.4% |
| UNKNOWN | 7,690 | 0.1% |

분포가 52:47로 가장 균등한 Enum 필드. 법적 이슈(고용상 성차별 금지) 적용 시 활용 제한 검토 필요.

#### job_search_status (구직 활성 상태) — Score: 0.0333 [비추천]

96.3%가 NONE. ACTIVE 필터 시 288,988건으로 급감.

#### area_code (거주 지역) — Score: 0.1945 [주의]

28.3% 결측. 서울 편중(57.8%). `county_codes`(희망 근무지, score=0.783)가 우수한 대안.

---

### resume.career (n=18,709,830)

#### position_grade_code (직급) — Score: 0.2136 [주의]

60.8% 결측. 비결측 데이터에서는 22개 직급으로 적절한 카디널리티. "결측 = 직급 무관"으로 처리 가능.

#### position_title_code (직책) — Score: 0.1044 [주의]

70.5% 결측. 실질 선별력 매우 낮음.

#### employment_status (재직 상태) — Score: 0.0940 [비추천]

89.5%가 RESIGNED. 현재 재직자(EMPLOYED) 필터로는 사용 가능하나 선별력 약함.

---

### resume.education (n=11,201,436)

#### school_type (학교 유형) — Score: 0.5893

| 값 | 건수 | 비율 |
|----|-----:|-----:|
| HIGH_SCHOOL | 4,466,884 | 39.9% |
| BACHELOR | 4,049,872 | 36.2% |
| ASSOCIATE | 2,236,138 | 20.0% |
| GRADUATE | 448,392 | 4.0% |

결측 없음, 5개 카테고리, 균등 분포. Enum 필드 중 최고 선별력.

#### academic_status (학적) — Score: 0.1375 [주의]

86.2%가 GRADUATED. 재학/휴학 등 특수 상태 필터로 제한적 활용.

---

### resume.workcondition (n=8,018,110)

#### work_arrangement_type (근무 형태) — Score: 0.0000 [사용 금지]

사실상 모든 값이 ANY. 절대 사용 금지.

---

## 4. Array 필드 상세

| 필드 | Empty% | Avg길이 | Max | Distinct코드 | Top1코드% | Filter Score |
|------|-------:|------:|----:|------------:|----------:|------------:|
| `county_codes` | 13.0% | 1.99 | 77 | 63 | 0.3% | **0.7832** |
| `job_classification_codes` | 17.4% | 2.21 | 15 | 914 | 4.1% | **0.7520** |
| `industry_codes` | 66.0% | 1.56 | 10 | 242 | 5.6% | **0.3204** |
| `job_keyword_codes` | 51.6% | 2.68 | 44 | 619 | 31.2% | **0.3261** |
| `employment_types` | 19.8% | 1.47 | 7 | 7 | 64.6% | **0.1570** |
| `industry_keyword_codes` | 81.7% | 3.02 | 27 | 1,204 | 3.8% | **0.1625** |

- `county_codes`: 희망 근무지. 63개 지역 코드, Top1 집중도 0.3%로 매우 균등. 거주지(`area_code`, score=0.195)보다 4배 이상 선별력 우수.
- `job_classification_codes`: 914개 직무 코드, Empty 17.4%, Top1 4.1%. `job_keyword_codes`(Empty 51.6%)보다 커버리지에서 명확히 우위.
- `industry_keyword_codes`: 1,204개 코드로 가장 세분화되나 81.7% 공백으로 실제 커버리지 18.3%에 불과.

---

## 5. MCP 필터 설계 권고

### 1순위 필터 (Score ≥ 0.5)

| 필드 | Score | 권고 사항 |
|------|------:|----------|
| `county_codes` | 0.783 | 희망 근무지. 복수 선택 지원. 지역 코드 매핑 테이블 필수 |
| `job_classification_codes` | 0.752 | 희망 직무. 복수 선택 + 상위 카테고리 계층 검색 지원 권장 |
| `school_type` | 0.589 | 학교 유형. `final_education_level`과 조합 사용 |
| `final_education_level` | 0.555 | 최종 학력. "학사 이상" 범위 필터 지원 권장 |

### 2순위 필터 (Score 0.2~0.5)

| 필드 | Score | 권고 사항 |
|------|------:|----------|
| `gender` | 0.447 | 법적 이슈 검토 후 활용. 성별 무관 옵션 기본값 권장 |
| `job_keyword_codes` | 0.326 | `job_classification_codes` 보완용 |
| `industry_codes` | 0.320 | 희망 산업. Empty 66%는 "산업 무관"으로 해석 가능 |
| `career_type` | 0.277 | 경력/신입 구분. 단순하지만 실용적 |
| `visibility_type` | 0.273 | PUBLIC 전제 필터. 기본값으로 설정 권장 |
| `position_grade_code` | 0.214 | 60.8% 결측 → "결측 = 직급 무관"으로 처리 |

### 3순위 필터 (Score 0.1~0.2, 보조 활용)

| 필드 | Score | 권고 사항 |
|------|------:|----------|
| `area_code` | 0.195 | `county_codes` 없을 때 폴백 용도로만 사용 |
| `industry_keyword_codes` | 0.163 | 81.7% 공백. 선택적 심화 필터로만 사용 |
| `employment_types` | 0.157 | 정규직 외 고용형태 검색에만 유효 |
| `academic_status` | 0.138 | 재학/휴학 등 특수 학적 검색 전용 |
| `final_education_status` | 0.132 | 재학/졸업 예정 필터로 제한적 사용 |
| `position_title_code` | 0.104 | 70.5% 결측. 보조 힌트 수준 |

### 비추천 필터 (Score < 0.1, 사용 금지)

| 필드 | Score | 이유 |
|------|------:|------|
| `employment_status` | 0.094 | 89.5% RESIGNED |
| `job_search_status` | 0.033 | 96.3% NONE |
| `complete_status` | 0.017 | 98.3% COMPLETED |
| `work_arrangement_type` | 0.000 | **100% ANY. 절대 사용 금지** |

### 추천 MCP 필터 조합 시나리오

**시나리오 A: 경력직 개발자 검색**
```
career_type = EXPERIENCED
job_classification_codes IN [개발 관련 코드들]
final_education_level IN [BACHELOR, GRADUATE]
county_codes IN [서울, 경기 코드]
visibility_type = PUBLIC
```
[AI 추정] 상위 4개 필드 조합으로 전체 이력서의 5~15% 내외 타겟팅 가능

**시나리오 B: 특정 산업 신입 공개 이력서**
```
career_type = NEW_COMER
industry_codes IN [타겟 산업 코드들]
school_type IN [BACHELOR, GRADUATE]
visibility_type = PUBLIC
```

**시나리오 C: 재직 중 이직 희망자 (헤드헌팅)**
```
visibility_type IN [PUBLIC, HEADHUNTER_ONLY]
employment_status = EMPLOYED  -- 주의: 10.5%만 해당
job_search_status = ACTIVE    -- 주의: 3.7%만 해당, 중복 적용 시 과도 축소
```

---

## 6. 한계 및 후속 작업

1. **career 테이블 1:N**: `position_grade_code`, `position_title_code`는 이력서당 여러 경력 레코드 존재 — 이력서 기준 통계로 재집계 필요
2. **area_code 결측 원인**: 28.3% 결측이 "비공개 설정"인지 "미입력"인지 구분하여 Coverage 재평가
3. **job_keyword_codes / industry_keyword_codes 코드 체계 확인**: `job_classification_codes`와의 중복 여부 검토
4. **이력서 최신성 미고려**: 신선도 필터 조합 시 실질 활용도 재평가 필요 (12번 리포트 참조)
5. **코드 매핑 테이블 검증**: `area_code`, `position_grade_code` 숫자 코드의 실제 레이블 매핑 확인

---

*데이터: ClickHouse `import_resume_hub_tmp` (n=8,018,110 workcondition 기준) | 분석: Scientist Agent (claude-sonnet-4-6) | [AI 추정] 표기 항목은 AI 해석*
