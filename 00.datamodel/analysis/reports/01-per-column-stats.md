# 14개 테이블 컬럼별 완전 통계 분석

**생성일시:** 2026-02-27
**분석 대상 DB:** `import_resume_hub_tmp` (ClickHouse 26.1.3.52)
**분석 범위:** 14개 테이블, 전체 컬럼

> [OBJECTIVE] 14개 이력서 허브 테이블의 모든 컬럼에 대해 데이터 타입별 완전한 통계 요약 생성

---

## 목차

1. [external_mapping.site_user_mapping](#1-external_mappingsite_user_mapping)
2. [user_profile.profile](#2-user_profileprofile)
3. [resume.resume](#3-resumeresume)
4. [resume.career](#4-resumecareer)
5. [resume.career_description](#5-resumecareer_description)
6. [resume.self_introduction](#6-resumeself_introduction)
7. [resume.award](#7-resumeaward)
8. [resume.certificate](#8-resumecertificate)
9. [resume.experience](#9-resumeexperience)
10. [resume.education](#10-resumeeducation)
11. [resume.major](#11-resumemajor)
12. [resume.language](#12-resumelanguage)
13. [resume.skill](#13-resumeskill)
14. [resume.workcondition](#14-resumeworkcondition)

---

## 1. external_mapping.site_user_mapping

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 7,780,115 |
| 출처 사이트 유형 | JOBKOREA / JOBKOREACORP 2종 |
| 데이터 적재 기간 | 2026-01-14 ~ 2026-02-25 |

### 컬럼별 통계

| 컬럼명 | 타입 | count | distinct | NULL/빈값 | 비고 |
|--------|------|-------|----------|-----------|------|
| `id` | String | 7,780,115 | 7,780,115 | 0 (0%) | PK, 완전 unique |
| `member_origin_type` | LowCardinality(String) | 7,780,115 | 2 | 0 (0%) | 아래 분포 참조 |
| `site_user_ref` | String | 7,780,115 | 7,780,115 | 0 (0%) | 완전 unique |
| `global_user_ref` | String | 7,780,115 | 1 | 7,780,115 (100%) | **전체 빈값** - 통합회원키 미연결 |
| `created_at` | DateTime64(6) | 7,780,115 | - | 0 | min: 2026-01-14, max: 2026-02-25 |

### member_origin_type 분포

| 값 | count | 비율 |
|----|-------|------|
| JOBKOREA | 4,303,603 | 55.3% |
| JOBKOREACORP | 3,476,512 | 44.7% |

### 데이터 품질 이슈

> **[FINDING] global_user_ref 100% 빈값:** 7,780,115건 전체에서 통합회원키(global_user_ref)가 비어있음. 외부 시스템과의 매핑 연결이 아직 미완성 상태.
> [STAT:n] n = 7,780,115 (전수)

---

## 2. user_profile.profile

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 7,780,115 |
| 출처 사이트 | 1종 (origin_site distinct=1) |
| 데이터 적재 기간 | 2026-01-14 ~ 2026-02-25 |

### 숫자형 컬럼: age

| 통계 | 값 |
|------|----|
| count | 7,780,115 |
| avg | 43.05세 (전체) / **36.18세** (age 1-100) |
| min | 0세 |
| max | 203세 |
| p25 | 30세 |
| p50 (median) | 35세 |
| p75 | 44세 |
| stddev | 27.14 (전체) / **8.57** (age 1-100) |
| 0값 (나이 미상) | 11,005 (0.14%) |
| age>100 이상치 | 523,752 (6.7%) |

> **[FINDING] age 이상값 존재:** max=203세, 0세 11,005건은 데이터 품질 문제.
> **[CORRECTION] age 1-100 유효 범위 기준 평균은 36.18세**이며, 연령 기반 분석은 유효 범위 값을 사용해야 함.
> [STAT:n] n = 7,780,115 (전체), n = 7,245,358 (age 1-100)

### 날짜 컬럼: birthday

| 통계 | 값 |
|------|-----|
| 센티넬값(1900-01-01) | **7,780,115 (100%)** |
| 실제 생년월일 데이터 | 0건 |
| ALIAS 설정 | `ALIAS '1900-01-01'` (REDACTED) |

> **[FINDING] birthday 100% 센티넬값:** birthday 컬럼은 ALIAS로 `'1900-01-01'`로 고정되어 있음. 개인정보 보호를 위해 실제 생년월일은 저장하지 않고, `age` 컬럼으로 대체.
> [STAT:n] n = 7,780,115

### 문자열/Enum 컬럼

| 컬럼명 | distinct | 빈값 | 기타 |
|--------|----------|------|------|
| `id` | 7,780,115 | 0 | PK |
| `origin_site` | 1 | 0 | 단일 출처 |
| `site_user_mapping_id` | 7,780,115 | 0 | 완전 unique |
| `gender` | 3 | 0 | 아래 분포 |
| `job_search_status` | 2 | 0 | 아래 분포 |
| `address` | - | 1,306,935 (16.8%) | avg 길이 24.6자 |
| `area_code` | 258 | 2,198,058 (28.3%) | 지역코드 미기재 많음 |

### deleted_at

| 통계 | 값 |
|------|-----|
| deleted_at IS NULL | 0 (0%) |
| deleted_at IS NOT NULL | 7,780,115 (100%) |

> **[FINDING] deleted_at 100% NOT NULL:** 모든 행의 deleted_at이 채워져 있음. 실제 삭제 처리 여부와 컬럼 의미 재확인 필요 (soft delete 플래그 vs. 일괄 설정값 가능성).

### gender 분포

| 값 | count | 비율 |
|----|-------|------|
| MALE | 4,086,056 | 52.5% |
| FEMALE | 3,686,369 | 47.4% |
| UNKNOWN | 7,690 | 0.1% |

### job_search_status 분포

| 값 | count | 비율 |
|----|-------|------|
| NONE (구직 비희망) | 7,491,127 | 96.3% |
| ACTIVE (구직 희망) | 288,988 | 3.7% |

### hiring_advantages (Array)

| 통계 | 값 |
|------|-----|
| 빈 배열 (미기재) | 7,525,497 (96.7%) |
| 평균 배열 길이 | 0.037 |
| 최대 배열 길이 | 5 |

**Top 값 분포:**

| 값 | count |
|----|-------|
| MILITARY_EXEMPTED (병역특례) | 114,497 |
| MILITARY_NOT_COMPLETED (미필) | 46,251 |
| EMPLOYMENT_SUBSIDY (고용지원금) | 44,101 |
| NATIONAL_MERIT (보훈) | 38,306 |
| DISABILITY (장애) | 24,052 |
| EMPLOYMENT_PROTECTION (고용보호) | 19,971 |

---

## 3. resume.resume

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 8,018,110 |
| distinct resume_id | 8,018,110 (PK) |
| 출처 사이트 | 1종 |
| 데이터 생성 기간 | 1999-06-16 ~ 2026-02-25 |

### 숫자형 컬럼: main_flag

| 값 | count | 비율 |
|----|-------|------|
| 1 (대표이력서) | 7,715,508 | 96.2% |
| 0 (비대표) | 302,602 | 3.8% |

### 문자열 컬럼

| 컬럼명 | distinct | 빈값 | avg 길이 | max 길이 |
|--------|----------|------|----------|----------|
| `id` | 8,018,110 | 0 | - | - |
| `origin_site` | 1 | 0 | - | - |
| `site_resume_ref` | 8,018,110 | 0 | - | - |
| `site_user_mapping_id` | - | 0 | - | - |
| `title` | - | 135,258 (1.7%) | 40.8자 | 356자 |

### Enum/LowCardinality 컬럼

**visibility_type 분포:**

| 값 | count | 비율 |
|----|-------|------|
| PUBLIC | 5,691,631 | 71.0% |
| PRIVATE | 2,097,262 | 26.2% |
| HEADHUNTER_ONLY | 229,217 | 2.9% |

**career_type 분포:**

| 값 | count | 비율 |
|----|-------|------|
| EXPERIENCED (경력) | 5,540,880 | 69.1% |
| NEW_COMER (신입) | 2,477,230 | 30.9% |

**final_education_level 분포:**

| 값 | count | 비율 |
|----|-------|------|
| BACHELOR (4년제) | 3,481,044 | 43.4% |
| HIGH_SCHOOL (고졸) | 1,980,738 | 24.7% |
| ASSOCIATE (전문대) | 1,801,169 | 22.5% |
| GRADUATE (대학원) | 401,364 | 5.0% |
| NONE | 353,795 | 4.4% |

**final_education_status:** 7개 distinct 값 (상세 분포 미수집)

**complete_status 분포:**

| 값 | count | 비율 |
|----|-------|------|
| COMPLETED | 7,879,887 | 98.3% |
| BASIC_INFO_COMPLETED | 136,370 | 1.7% |
| NONE | 1,471 | 0.02% |
| SKILL_SET_COMPLETED | 382 | 0.005% |

### 날짜 컬럼

| 컬럼 | min | max |
|------|-----|-----|
| `created_at` | 1999-06-16 | 2026-02-25 |
| `updated_at` | 2001-11-01 | 2026-02-25 |
| `indexed_at` | 2026-01-14 | 2026-02-25 |
| `deleted_at` (NOT NULL) | 8,018,110 (100%) | - |

**연도별 이력서 생성 분포 (created_at):**

| 연도 | count |
|------|-------|
| 1999 | 9 |
| 2000 | 2,331 |
| 2001~2010 | 약 58만 |
| 2011~2015 | 약 77만 |
| 2016 | 291,100 |
| 2017 | 400,866 |
| 2018 | 633,676 |
| 2019 | 717,270 |
| 2020 | 694,487 |
| 2021 | 711,875 |
| 2022 | 711,235 |
| 2023 | 825,923 |
| 2024 | 689,500 |
| 2025 | 706,524 |
| 2026 (Jan~Feb) | 293,176 |

> **[FINDING] 이력서 생성량 2018년 이후 급증:** 2018년부터 연간 60만+ 이력서 생성, 2023년 최고점(82.6만). 서비스 성장 지표.
> [STAT:n] n = 8,018,110

---

## 4. resume.career

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 18,709,830 |
| distinct resume_id | 5,523,101 (이력서당 평균 3.4개 경력) |
| 데이터 기간 | 2026-01-14 ~ 2026-02-25 |

### 숫자형 컬럼

| 컬럼 | avg | min | max | median | p95 | stddev | 0값 비율 | 음수 비율 |
|------|-----|-----|-----|--------|-----|--------|----------|----------|
| `days_worked` | 0 | 0 | 0 | 0 | 0 | 0 | 100% | 0% |
| `sort_order` | 3.33 | 0 | 255 | - | - | - | - | - |
| `company_name_visible` | - | - | - | - | - | - | 15,291,930 (81.7% = 공개) | - |

> **[FINDING] days_worked 전체 0:** 18,709,830건 모두 days_worked = 0. 해당 컬럼이 아직 계산/채워지지 않은 상태.
> [STAT:n] n = 18,709,830

### 문자열 컬럼

| 컬럼명 | 빈값 | 빈값비율 | avg 길이 |
|--------|------|----------|----------|
| `company_name` | 7,508 | 0.04% | 19.9자 |
| `business_registration_number` | 7,110,218 | 38.0% | - |
| `department_name` | 7,697,894 | 41.2% | - |
| `work_details` | 8,236,528 | 44.0% | 146.0자 (비빈값 기준) |
| `period` | - | - | - |

### Enum/LowCardinality 컬럼

**period_type:** distinct = 1 (단일값)

**employment_status 분포:**

| 값 | count | 비율 |
|----|-------|------|
| RESIGNED (퇴직) | 16,748,690 | 89.5% |
| EMPLOYED (재직) | 1,961,140 | 10.5% |

**salary_type 분포:**

| 값 | count | 비율 |
|----|-------|------|
| ANNUAL (연봉) | 11,557,866 | 61.8% |
| (빈값) | 7,151,964 | 38.2% |

**position_grade_code Top 20:**

| 코드 | count | 비율 |
|------|-------|------|
| (빈값) | 11,382,228 | 60.8% |
| 6010000001 | 3,534,575 | 18.9% |
| 6010000005 | 1,034,083 | 5.5% |
| 6010000007 | 812,543 | 4.3% |
| 6010000003 | 688,042 | 3.7% |
| 6010000009 | 348,265 | 1.9% |
| 6010000011 | 344,742 | 1.8% |
| 6010000013 | 224,552 | 1.2% |
| 기타 9개 | ~320,000 | 1.7% |

**position_title_code:** 17개 distinct 값
**currency_code:** 2개 distinct 값
**job_classification_codes (Array):** Top 30 코드 수집 완료 (codehub JOB_CLASSIFICATION_SUBCATEGORY 매핑 완료)
**job_keyword_codes (Array):** Array 타입

---

## 5. resume.career_description

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 1,351,836 |
| distinct resume_id | 1,351,836 (이력서당 1개 = 1:1 관계) |
| 데이터 기간 | 2026-01-14 ~ 2026-02-25 |

### 컬럼별 통계

| 컬럼명 | 타입 | 통계 |
|--------|------|------|
| `id` | String | distinct = 1,351,836 (PK) |
| `resume_id` | String | distinct = 1,351,836 (1:1) |
| `description` | String | 빈값: 0 (0%) |

### description 길이 통계

| 통계 | 값 |
|------|----|
| avg 길이 | 1,467.6자 |
| min 길이 | 1자 |
| max 길이 | 150,000자 |
| median (p50) | 524.5자 |
| p95 | 5,613자 |

> **[FINDING] 경력기술서 avg 1,468자:** 중앙값 525자, 상위 5%는 5,600자 이상. 최대 15만자(약 75페이지 분량)의 이상값 존재.
> [STAT:n] n = 1,351,836

---

## 6. resume.self_introduction

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 7,962,522 |
| distinct resume_id | 5,137,844 (이력서당 평균 1.55개) |
| 데이터 기간 | 2026-01-14 ~ 2026-02-25 |

### 컬럼별 통계

| 컬럼명 | 빈값 | 빈값비율 | avg 길이 | max 길이 |
|--------|------|----------|----------|----------|
| `id` | 0 | 0% | - | - |
| `resume_id` | 0 | 0% | - | - |
| `title` | 1,055,000 | 13.2% | 25.5자 | 651자 |
| `description` | 209,440 | 2.6% | 1,697.9자 | 121,574자 |

### sort_order 통계

| 통계 | 값 |
|------|----|
| avg | 1.58 |
| min | 0 |
| max | 92 |

### description 길이 분포

| 통계 | 값 |
|------|----|
| avg 길이 | 1,697.9자 |
| median | 1,286자 |
| p95 | 4,958자 |
| max | 121,574자 |

> **[FINDING] 자기소개서 avg 1,698자:** 경력기술서보다 길이 편차가 작음. 최대 12만자 이상값 존재.
> [STAT:n] n = 7,962,522

---

## 7. resume.award

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 1,516,747 |
| distinct resume_id | 707,646 (이력서당 평균 2.1개) |
| 데이터 기간 | 2026-01-14 ~ 2026-02-25 |

### 컬럼별 통계

| 컬럼명 | 빈값 | 빈값비율 | avg 길이 | max 길이 |
|--------|------|----------|----------|----------|
| `id` | 0 | 0% | - | - |
| `resume_id` | 0 | 0% | - | - |
| `title` | 28 | 0.002% | 32.8자 | 140자 |
| `description` | **1,516,747** | **100%** | 0자 | 0자 |
| `organization` | 13,238 | 0.87% | 23.2자 | - |
| `awarded_at` | 19,935 | 1.3% | - | - |

### sort_order 통계

| 통계 | 값 |
|------|----|
| avg | 2.42 |
| min | 1 |
| max | 110 |

> **[FINDING] description 100% 빈값:** award.description 컬럼은 전체 1,516,747건 모두 빈값. 해당 컬럼은 사실상 미사용.
> [STAT:n] n = 1,516,747

---

## 8. resume.certificate

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 13,573,606 |
| distinct resume_id | 4,325,794 (이력서당 평균 3.1개) |
| 데이터 기간 | 2026-01-14 ~ 2026-02-25 |

### Enum 컬럼

**type 분포:**

| 값 | count | 비율 |
|----|-------|------|
| CERTIFICATE (자격증) | 12,037,087 | 88.7% |
| LANGUAGE_TEST (어학시험) | 1,536,519 | 11.3% |

**score_type 분포:**

| 값 | count | 비율 |
|----|-------|------|
| NONE | 13,084,181 | 96.4% |
| SCORE (점수) | 243,684 | 1.8% |
| GRADE (등급) | 237,624 | 1.8% |
| PASS (합격) | 8,117 | 0.06% |

### 문자열 컬럼

| 컬럼명 | distinct | 빈값 | 빈값비율 | avg 길이 |
|--------|----------|------|----------|----------|
| `name` | - | 44,716 | 0.33% | 20.5자 |
| `parent_code` | 34 | 12,037,087 | 88.7% | - |
| `code` | 3,818 | 1,756,830 | 12.9% | - |
| `issuer` | - | 1,758,106 | 12.9% | - |
| `score` | - | 12,813,124 | 94.4% | - |
| `score_criteria_code` | 702 | - | - | - |
| `issued_at` | - | 795,339 | 5.9% | - |

### sort_order 통계

| avg | min | max |
|-----|-----|-----|
| 2.58 | 0 | 255 |

> **[FINDING] parent_code 88.7% 빈값:** CERTIFICATE 타입은 parent_code 없음(자격증은 언어코드 불필요). LANGUAGE_TEST에서만 parent_code 활용.
> [STAT:n] n = 13,573,606

---

## 9. resume.experience

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 6,638,635 |
| distinct resume_id | 2,240,622 (이력서당 평균 2.96개) |
| 데이터 기간 | 2026-01-14 ~ 2026-02-25 |

### type 분포 (11종)

| 값 | count | 비율 |
|----|-------|------|
| TRAINING (교육) | 1,793,528 | 27.0% |
| OVERSEAS (해외) | 1,281,533 | 19.3% |
| PART_TIME (아르바이트) | 882,531 | 13.3% |
| INTERNSHIP (인턴십) | 606,200 | 9.1% |
| CAMPUS (교내활동) | 508,035 | 7.7% |
| SOCIAL (사회활동) | 485,503 | 7.3% |
| VOLUNTEERING (봉사활동) | 455,310 | 6.9% |
| CLUB (동아리) | 360,988 | 5.4% |
| WORKED_OVERSEAS (해외근무) | 154,791 | 2.3% |
| ETC (기타) | 110,201 | 1.7% |
| NONE | 15 | 0.0002% |

### 문자열 컬럼

| 컬럼명 | 빈값 | 빈값비율 | avg 길이 | max 길이 |
|--------|------|----------|----------|----------|
| `title` | 4,845,194 | **73.0%** | 9.0자 | 150자 |
| `description` | 562,533 | 8.5% | 184.8자 | 38,001자 |
| `affiliation_code` | 5,054,629 | 76.1% | - | - |
| `affiliation_name` | 126,746 | 1.9% | - | - |
| `started_on` | 160,572 | 2.4% | - | - |
| `ended_on` | 162,528 | 2.4% | - | - |

**affiliation_code:** 492개 distinct 값

### sort_order 통계

| avg | min | max |
|-----|-----|-----|
| 2.17 | 0 | 257 |

> **[FINDING] title 73% 빈값:** experience.title은 대부분 미기재. 실제 활용 컬럼은 description.
> [STAT:n] n = 6,638,635

---

## 10. resume.education

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 11,201,436 |
| distinct resume_id | 7,665,296 (이력서당 평균 1.46개) |
| 데이터 기간 | 2026-01-14 ~ 2026-02-25 |

### Enum 컬럼

**school_type 분포:**

| 값 | count | 비율 |
|----|-------|------|
| HIGH_SCHOOL | 4,466,884 | 39.9% |
| BACHELOR (4년제) | 4,049,872 | 36.2% |
| ASSOCIATE (전문대) | 2,236,138 | 20.0% |
| GRADUATE (대학원) | 448,392 | 4.0% |
| NONE | 150 | 0.001% |

**academic_status 분포:**

| 값 | count | 비율 |
|----|-------|------|
| GRADUATED (졸업) | 9,652,734 | 86.2% |
| EXPECTED_GRADUATION (졸업예정) | 595,436 | 5.3% |
| DROPPED_OUT (중퇴) | 424,355 | 3.8% |
| ENROLLED (재학) | 229,135 | 2.0% |
| LEAVE_OF_ABSENCE (휴학) | 157,904 | 1.4% |
| COMPLETED (수료) | 127,473 | 1.1% |
| NONE | 14,399 | 0.1% |

**degree_program_type:** 4개 distinct 값
**education_path:** 3개 distinct 값 (NORMAL/VERIFICATION/TRANSFER)

### 문자열 컬럼

| 컬럼명 | 빈값 | 빈값비율 | avg 길이 | distinct |
|--------|------|----------|----------|---------|
| `school_code` | 1,638,699 | 14.6% | - | 10,003 |
| `school_name` | 1,190,197 | 10.6% | 21.5자 | - |
| `started_on` | 4,480,672 | **40.0%** | - | - |
| `ended_on` | 26,429 | 0.24% | - | - |
| `research_topic` | 10,819,554 | **96.6%** | - | - |
| `gpa` | 7,437,741 | **66.4%** | - | - |
| `gpa_scale` | 7,185,140 | **64.1%** | - | - |

### sort_order 통계

| avg | min | max |
|-----|-----|-----|
| 0.69 | 0 | 16 |

> **[FINDING] started_on 40% 빈값:** 학력 시작일 미기재율이 높음. 고등학교 학력의 경우 입학일 기재 생략 패턴.
> **[FINDING] gpa/gpa_scale 66% 빈값:** 학점 미기재가 대다수. 실질적 활용 데이터는 약 1/3.
> [STAT:n] n = 11,201,436

---

## 11. resume.major

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 7,147,005 |
| distinct education_id | 6,656,347 |
| distinct resume_id | 5,813,623 |
| 전공 코드 수 | 157,033개 distinct |
| 전공명 수 | 47,163개 distinct |

### type 분포 (5종)

| 값 | count | 비율 |
|----|-------|------|
| PRIMARY (주전공) | 6,656,026 | 93.1% |
| DOUBLE (복수전공) | 272,913 | 3.8% |
| MINOR (부전공) | 176,292 | 2.5% |
| SECOND (제2전공) | 41,544 | 0.6% |
| NONE | 230 | 0.003% |

### 문자열 컬럼

| 컬럼명 | 빈값 | 빈값비율 | distinct | avg 길이 | max 길이 |
|--------|------|----------|---------|----------|----------|
| `code` | 113,703 | 1.6% | 157,033 | - | - |
| `name` | 437,188 | 6.1% | 47,163 | 16.9자 | 131자 |

> **[FINDING] 전공코드 157,033개 distinct:** 표준화된 코드(표준코드 대비 커스텀 값 혼재 가능성). 전공명 distinct 47,163개는 사용자 자유 입력.
> [STAT:n] n = 7,147,005

---

## 12. resume.language

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 653,876 |
| distinct resume_id | 509,027 (이력서당 평균 1.28개) |
| 언어 코드 | 33개 distinct |
| 데이터 기간 | 2026-01-14 ~ 2026-02-25 |

### Enum 컬럼

**level_group (CEFR 등급) 분포:**

| 값 | count | 비율 |
|----|-------|------|
| A (기초) | 296,116 | 45.3% |
| B (중급) | 230,102 | 35.2% |
| C (고급) | 127,658 | 19.5% |

**training_experience:** 1개 distinct 값 (사실상 단일값 = 미활용)

### 언어명 Top 20

| 언어 | count | 비율 |
|------|-------|------|
| 영어 | 406,204 | 62.1% |
| 일본어 | 96,827 | 14.8% |
| 중국어(북경어) | 77,852 | 11.9% |
| 한국어 | 14,509 | 2.2% |
| 스페인어 | 10,808 | 1.7% |
| 프랑스어 | 8,788 | 1.3% |
| 독일어 | 6,256 | 1.0% |
| 러시아어 | 6,088 | 0.9% |
| 베트남어 | 5,941 | 0.9% |
| 기타 11개 언어 | ~10,000 | 1.5% |

### 문자열 컬럼

| 컬럼명 | 빈값 | training_experience_description |
|--------|------|--------------------------------|
| `training_experience_description` | 653,876 (100%) | **전체 빈값** |

### sort_order 통계

| avg | min | max |
|-----|-----|-----|
| 2.09 | 1 | 19 |

> **[FINDING] 영어가 62.1% 압도적 1위:** 영어-일본어-중국어 3개 언어가 전체의 88.8% 차지.
> **[FINDING] training_experience_description 100% 빈값:** 어학연수 설명 컬럼 미활용.
> [STAT:n] n = 653,876

---

## 13. resume.skill

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 20,810,452 |
| distinct resume_id | 3,074,732 (이력서당 평균 6.8개) |
| distinct 스킬코드 | 101,925개 |
| distinct 스킬명 | 100,905개 |
| 데이터 기간 | 2026-01-14 ~ 2026-02-25 |

### type 분포 (3종)

| 값 | count | 비율 |
|----|-------|------|
| HARD | 10,449,376 | 50.2% |
| SOFT | 9,891,605 | 47.5% |
| NONE | 469,471 | 2.3% |

### 문자열 컬럼

| 컬럼명 | 빈값 | 빈값비율 | distinct | avg 길이 | max 길이 |
|--------|------|----------|---------|----------|----------|
| `code` | 0 | 0% | 101,925 | - | - |
| `name` | 12,360 | 0.06% | 100,905 | 10.1자 | 144자 |

> **[FINDING] 스킬 테이블 최대 행수(2천만):** 전체 14개 테이블 중 가장 많은 행. 이력서당 평균 6.8개 스킬 기재.
> **[FINDING] HARD/SOFT 거의 균등 분포:** HARD 50.2% vs SOFT 47.5%로 균형.
> [STAT:n] n = 20,810,452

---

## 14. resume.workcondition

**테이블 요약**

| 항목 | 값 |
|------|-----|
| 총 행수 | 8,018,110 |
| distinct resume_id | 8,018,110 (이력서와 1:1 관계) |
| 데이터 기간 | 2026-01-14 ~ 2026-02-25 |

### Array 컬럼 통계

| 컬럼명 | 빈배열 | 빈배열비율 | avg 길이 | max 길이 |
|--------|--------|----------|----------|----------|
| `employment_types` | 1,591,514 | 19.9% | 1.18 | 7 |
| `industry_codes` | 5,292,761 | 66.0% | 0.53 | 10 |
| `industry_keyword_codes` | 6,549,231 | 81.7% | - | - |
| `job_classification_codes` | 1,393,034 | 17.4% | 1.83 | 15 |
| `job_keyword_codes` | 4,134,991 | 51.6% | - | - |
| `job_industry_codes` | **8,018,110** | **100%** | - | - |
| `career_job_industry_codes` | **8,018,110** | **100%** | - | - |
| `county_codes` | 1,038,597 | 13.0% | 1.73 | - |

### Enum/String 컬럼

| 컬럼명 | distinct | 빈값 | 빈값비율 |
|--------|----------|------|----------|
| `work_arrangement_type` | 2 | 203,764 | 2.5% |
| `work_schedule` | - | 8,018,110 | **100%** |
| `salary_type` | - | 203,764 | 2.5% |
| `currency_code` | 2 | - | - |

**work_arrangement_type 분포:**

| 값 | count | 비율 |
|----|-------|------|
| ANY | 7,814,346 | 97.5% |
| (빈값) | 203,764 | 2.5% |

### employment_types Top 값 (ARRAY JOIN)

| 값 | count |
|----|-------|
| PERMANENT (정규직) | 6,101,863 |
| CONTRACT (계약직) | 1,751,338 |
| INTERN (인턴) | 605,396 |
| FREELANCER (프리랜서) | 581,705 |
| HEADHUNTING (헤드헌팅) | 201,672 |
| DISPATCH (파견) | 190,616 |
| MILITARY (병역특례) | 37,932 |

### job_classification_codes Top 30 (workcondition, ARRAY JOIN)

상위 코드 (4010000xxx 형식, codehub JOB_CLASSIFICATION_SUBCATEGORY 매핑 완료):

| 코드 | count |
|------|-------|
| 4010000131 | 605,090 |
| 4010000284 | 548,125 |
| 4010000129 | 467,786 |
| 4010000145 | 377,380 |
| 4010000286 | 355,361 |
| 4010000000 | 326,899 |
| 4010000285 | 237,137 |
| 기타 23개 | 약 310만 |

### industry_codes Top 30 (workcondition, ARRAY JOIN)

| 코드 | count |
|------|-------|
| 3010000021 | 236,792 |
| 3010000008 | 183,182 |
| 3010000001 | 165,287 |
| 3010000002 | 160,879 |
| 3010000023 | 157,229 |
| 3010000030 | 146,136 |
| 기타 24개 | 약 200만 |

> **[FINDING] job_industry_codes & career_job_industry_codes 100% 빈값:** 두 컬럼 전체 8,018,110건 모두 빈배열. 해당 컬럼들이 아직 미사용/미계산 상태.
> [STAT:n] n = 8,018,110
> **[FINDING] work_schedule 100% 빈값:** 근무 스케줄 컬럼 전체 미기재. 미사용 컬럼.
> [STAT:n] n = 8,018,110

---

## 전체 테이블 요약

[DATA] 14개 테이블, 총 약 1억 2천만 행

| 테이블 | 행수 | 비고 |
|--------|------|------|
| external_mapping.site_user_mapping | 7,780,115 | 사용자 매핑 |
| user_profile.profile | 7,780,115 | 사용자 프로필 |
| resume.resume | 8,018,110 | 이력서 (최대) |
| resume.career | 18,709,830 | 경력 (최다) |
| resume.career_description | 1,351,836 | 경력기술서 |
| resume.self_introduction | 7,962,522 | 자기소개서 |
| resume.award | 1,516,747 | 수상 |
| resume.certificate | 13,573,606 | 자격증/어학 |
| resume.experience | 6,638,635 | 경험 |
| resume.education | 11,201,436 | 학력 |
| resume.major | 7,147,005 | 전공 |
| resume.language | 653,876 | 언어 |
| resume.skill | **20,810,452** | 스킬 (최대행수) |
| resume.workcondition | 8,018,110 | 근무조건 |
| **합계** | **~120,161,845** | |

---

## 주요 데이터 품질 이슈 정리

[LIMITATION] 아래 이슈들은 AI/ML 모델 학습 및 검색 품질에 영향을 줄 수 있음.

| 우선순위 | 테이블.컬럼 | 이슈 | 규모 |
|---------|------------|------|------|
| Critical | external_mapping.site_user_mapping.global_user_ref | 100% 빈값 - 통합회원키 미연결 | 7.78M건 |
| Critical | resume.workcondition.job_industry_codes | 100% 빈배열 | 8.02M건 |
| Critical | resume.workcondition.career_job_industry_codes | 100% 빈배열 | 8.02M건 |
| Critical | resume.workcondition.work_schedule | 100% 빈값 | 8.02M건 |
| Critical | resume.career.days_worked | 100% 0값 - 미계산 | 18.71M건 |
| Critical | resume.award.description | 100% 빈값 - 미사용 컬럼 | 1.52M건 |
| Critical | resume.language.training_experience_description | 100% 빈값 | 653K건 |
| High | user_profile.profile.birthday | 100% 센티넬(1900-01-01) - ALIAS | 7.78M건 |
| High | user_profile.profile.deleted_at | 100% NOT NULL - 의미 불명확 | 7.78M건 |
| High | resume.resume.deleted_at | 100% NOT NULL | 8.02M건 |
| High | resume.career.salary_type | 38.2% 빈값 | 7.15M건 |
| High | resume.education.started_on | 40.0% 빈값 | 4.48M건 |
| Medium | user_profile.profile.age | max=203, 0값 11,005건 | 11K건 |
| Medium | resume.experience.title | 73.0% 빈값 | 4.85M건 |
| Medium | resume.education.gpa | 66.4% 빈값 | 7.44M건 |
| Medium | user_profile.profile.area_code | 28.3% 빈값 | 2.20M건 |

[LIMITATION] 분석 제약사항:
1. **코드 테이블 매핑 완료 (v2 보정):** job_classification_codes, industry_codes, position_grade_code 등 주요 코드는 codehub 딕셔너리로 매핑 완료. school_code만 51.7% 매핑률 (구 시스템 코드 미등록). 상세: reports/08-codehub-mapping.md, 08b-job-industry-mapping.md
2. **salary 컬럼 제외:** ALIAS `'<REDACTED>'`로 설정된 급여 관련 컬럼은 개인정보 보호로 통계 수집 불가
3. **name 컬럼 제외:** ALIAS `'<REDACTED>'`로 설정된 성명 컬럼은 개인정보 보호로 통계 수집 불가
4. **단일 출처:** origin_site distinct = 1로, 모든 데이터가 단일 출처에서 적재됨 (편향 가능성)
5. **적재 기간:** 2026-01-14 ~ 2026-02-25 (약 6주간의 스냅샷 데이터)

---

*Report generated: 2026-02-27*
*Analysis method: Direct ClickHouse query via HTTP API*
*Privacy: 개인식별정보(이름, 연락처, 급여) 출력 제외*
