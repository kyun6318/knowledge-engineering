# DB 스키마 상세 참조 (v3 부속 문서)

> v3.md의 부속 참조 문서. 소스 DB(resume-hub, job-hub, code-hub)의 필드 단위 상세 스키마.
> 온톨로지 매핑 시 필드 타입/Fill Rate 확인용.
>
> 작성일: 2026-03-14

---

## 1. resume-hub 테이블 구조

> 잡코리아 & 알바몬 Legacy 이력서의 공통 속성 재정의 데이터

### 1.1 SiteUserMapping (사용자 매핑)

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | PK | 사용자 매핑 ID → **Person.person_id** |
| `memberOriginType` | Enum | 회원 출처 |
| `siteUserRef` | String | 사이트 회원 참조키 |
| `globalUserRef` | String | 통합 회원키 (**100% 빈값**) |

### 1.2 Profile (사용자 프로필) — SiteUserMapping 1:N

| 필드 | 타입 | 설명 | Fill Rate |
|------|------|------|-----------|
| `id` | PK | 프로필 ID | 100% |
| `originSite` | Enum | UNKNOWN / ALBAMON / JOBKOREA | 100% |
| `siteUserMappingId` | FK | SiteUserMapping 참조 | 100% |
| `name` | String(암호화) | 이름 | PII 마스킹 |
| `gender` | Enum | MALE(52.5%) / FEMALE(47.4%) / OTHER(0.1%) | 100% |
| `birthday` | Date | 생년월일 (**100% sentinel '1900-01-01'**) | 사용 불가 |
| `age` | Integer | 나이 (평균 36.2세) | 93.3% (6.7% 이상치 age>100) |
| `address` | String | 주소 | 83.2% |
| `area_code` | Code | 거주지 코드 (AreaCodeType#COUNTY) | 71.7% |
| `hiringAdvantages` | Array | 취업 우대사항 | **3.3%** (96.7% 빈배열) |
| `jobSearchStatus` | Enum | 구직 상태 (96.3% NONE, 3.7% ACTIVE) | 100% |
| `deletedAt` | Instant | 삭제일시 (소프트 삭제) | 100% 입력됨 |

### 1.3 Resume (이력서) — SiteUserMapping 1:N, 중심 엔티티

| 필드 | 타입 | 설명 | Fill Rate / 분포 |
|------|------|------|-----------------|
| `id` | PK | 이력서 ID | 100% (8,018,110) |
| `originSite` | Enum | 출처 사이트 | 100% |
| `siteResumeRef` | String | 사이트 이력서 참조키 | 100% |
| `siteUserMappingId` | FK | SiteUserMapping 참조 | 100% |
| `title` | String | 이력서 제목 (평균 40.8자) | 98.3% |
| `visibilityType` | Enum | PUBLIC(71%) / PRIVATE(26.2%) / HEADHUNTER_ONLY(2.9%) | 100% |
| `careerType` | Enum | EXPERIENCED(69.1%) / NEW_COMER(30.9%) | 100% |
| `finalEducationLevel` | Enum(SchoolType) | BACHELOR(43.4%) / HIGH_SCHOOL(24.7%) / ASSOCIATE(22.5%) / GRADUATE(5%) | 100% |
| `finalEducationStatus` | Enum(AcademicStatus) | 최종 학력 상태 | 100% |
| `mainFlag` | Boolean | 메인 이력서 여부 (**96.2% true**) | 100% |
| `completeStatus` | Enum | 98.3% COMPLETED | 100% |
| `createdAt` | Instant | 생성일시 | 100% |
| `updatedAt` | Instant | 수정일시 | 100% |
| `userUpdatedAt` | Instant | 회원정보 수정일시 (중앙값 2.8년 전, 31.6% 5년+ 미갱신) | 100% |
| `deletedAt` | Instant | 삭제일시 | 소프트 삭제 |

### 1.4 Career (경력) — Resume 1:N

**규모**: 18,709,830건, 이력서 커버리지 68.9% (5,523,101 이력서), 이력서당 평균 3.4개

| 필드 | 타입 | 설명 | Fill Rate |
|------|------|------|-----------|
| `id` | PK | 경력 ID | 100% |
| `companyName` | String | 회사명 (**4,479,983 고유값**) | 99.96% |
| `companyNameVisible` | Boolean | 회사명 공개 여부 | 100% |
| `businessRegistrationNumber` | String | 사업자등록번호 | 62% |
| `departmentName` | String | 소속 부서 | 58.9% |
| `workDetails` | String | 담당 업무 (중앙값 96자) | ~56% |
| `period.type` | Enum | RANGE / JOIN_DATE_PLUS_WORK_DAYS | 100% |
| `period.period` | DateRange | 근무 기간 (started_on ~ ended_on) | ~100% |
| `period.daysWorked` | Integer | 총 근무일수 (**100% 제로**) | 계산 필요 |
| `period.employmentStatus` | Enum | RESIGNED(89.5%) / EMPLOYED(10.5%) | 100% |
| `jobClassificationCodes` | Array(Code) | 직무 코드 (JOB_CLASSIFICATION_SUBCATEGORY) | ~100% |
| `jobKeywordCodes` | Array(Code) | 직무 키워드 코드 | 100% |
| `positionGradeCode` | Code | 직급 코드 (POSITION_GRADE, 15코드) | **39.16%** |
| `positionTitleCode` | Code | 직책 코드 (POSITION_TITLE, 16코드) | **29.45%** |
| `salary` | SalaryVo | 급여 (REDACTED) | 마스킹됨 |

### 1.5 CareerDescription (경력 설명) — Resume 1:1

| 필드 | 타입 | 설명 | Fill Rate |
|------|------|------|-----------|
| `description` | String | 경력 상세 (중앙값 527자, 빈값 0%) | **16.9%** (1,351,836 이력서) |

**핵심 제약**: `career_id` FK 없음 — career 항목별 매핑 불가, resume 단위 귀속

### 1.6 Education (학력) — Resume 1:N

**규모**: 11,201,436건, 이력서 커버리지 95.6%, 이력서당 평균 1.46개

| 필드 | 타입 | 설명 | Fill Rate |
|------|------|------|-----------|
| `schoolType` | Enum | HIGH_SCHOOL(39.9%) / BACHELOR(36.2%) / ASSOCIATE(20%) / GRADUATE(4%) | 100% |
| `degreeProgramType` | Enum | NONE(96.15%) / MASTER(3.45%) / DOCTORATE(0.33%) | 100% |
| `academicStatus` | Enum | GRADUATED(86.2%) / EXPECTED(5.3%) / DROPPED(3.8%) | 100% |
| `educationPath` | Enum | REGULAR / GED / TRANSFER | 100% |
| `schoolName` | String | 학교 이름 (4,466 고유값) | 100% |
| `schoolCode` | Code | 학교 코드 (UNIVERSITY_CAMPUS) | **51.7%** (48.3% 레거시) |
| `startedOn` | Date | 입학일 | 60% |
| `endedOn` | Date | 졸업일 | ~95% |
| `researchTopic` | String | 논문 주제 | **3.4%** (대학원만) |
| `gpa` | Decimal | 학점 (평균 3.624, 4.5만점 87.77%) | **33.6%** |
| `gpaScale` | Decimal | 만점 기준 | 33.6% |

**품질 이슈**:
- `finalEducationLevel`(resume 헤더) vs `education.schoolType` 간 **35.6% 불일치** — education.schoolType을 진실 소스로 사용
- schoolCode 48.3% 레거시 코드 (`~Unknown:Cxxxxxxx`) — codehub UNIVERSITY_CAMPUS 매핑 갭

### 1.7 Major (전공) — Education 1:N

**규모**: 7,147,005건

| 필드 | 타입 | 설명 | Fill Rate |
|------|------|------|-----------|
| `type` | Enum | PRIMARY(93.1%) / DOUBLE(3.8%) / MINOR(2.5%) / SECOND | 100% |
| `name` | String | 전공명 (47,163 고유값) | 93.9% |
| `code` | Code | 전공 코드 (PREFERENCE_MAJOR, 157,033 고유 코드) | 98.4% |

### 1.8 Skill (스킬) — Resume 1:N

**규모**: 20,810,452건, 이력서 커버리지 38.3% (3,074,732), 이력서당 평균 6.77개

| 필드 | 타입 | 설명 | Fill Rate |
|------|------|------|-----------|
| `type` | Enum | HARD(50.2%) / SOFT(47.5%) / NONE(2.3%) | 100% |
| `name` | String | 스킬명 (100,905 고유값) | 100% |
| `code` | Code | 스킬 코드 (HARD_SKILL/SOFT_SKILL) | 100% (단, **2.4%만 표준**) |

### 1.9 Certificate (자격증) — Resume 1:N

**규모**: 13,573,606건, 이력서 커버리지 54%, 이력서당 평균 3.14개

| 필드 | 타입 | 설명 | Fill Rate |
|------|------|------|-----------|
| `type` | Enum(CertificateType) | CERTIFICATE(88.7%) / LANGUAGE_TEST(11.3%) | 100% |
| `name` | String | 자격증명 | 100% |
| `code` | Code | 자격증 코드 (LICENSE / LANGUAGE_EXAM) | 100% (codehub 매핑) |
| `issuer` | String | 발행처 | ~90% |
| `score` | String | 획득 점수 | 3.6% (LANGUAGE_TEST 한정 49.5%) |
| `scoreCriteriaCode` | Code | 등급 코드 (LANGUAGE_EXAM_CRITERIA) | 3.6% |
| `scoreType` | Enum | NONE(96.4%) / SCORE(1.8%) / GRADE(1.8%) / PASS | 100% |
| `issuedAt` | Date | 취득일 | 94.1% |

**매핑 이슈**: resume-hub `CERTIFICATE` → codehub `LICENSE`, resume-hub `LANGUAGE_TEST` → codehub `LANGUAGE_EXAM` (변환 필수)

### 1.10 Language (어학) — Resume 1:N

**규모**: 653,876건, 이력서 커버리지 6.3% (509K), 이력서당 평균 1.28개

| 필드 | 타입 | 설명 | Fill Rate |
|------|------|------|-----------|
| `name` | String | 언어명 | 100% |
| `code` | Code | 언어 코드 (LANGUAGE, 33코드) | 100% |
| `levelGroup` | Enum | A/초급(45.3%) / B/중급(35.2%) / C/고급(19.5%) | 100% |
| `trainingExperience` | Enum | **100% NONE** (미사용 필드) | 사용 불가 |

### 1.11 Experience (경험/활동) — Resume 1:N

**규모**: 6,638,635건, 이력서 커버리지 27.9% (2,240K), 이력서당 평균 2.96개

| 필드 | 타입 | 설명 | Fill Rate |
|------|------|------|-----------|
| `type` | Enum | TRAINING(27%) / OVERSEAS(19.3%) / PART_TIME(13.3%) / INTERNSHIP(9.1%) / CAMPUS(7.7%) / SOCIAL(7.3%) / VOLUNTEERING(6.9%) / CLUB(5.4%) | 100% |
| `title` | String | 경험 제목 | **27%** |
| `affiliationName` | String | 관련 기관/국가명 | ~70% |
| `affiliationCode` | Code | 기관/국가 코드 (AreaCodeType#NATION) | ~50% |
| `description` | String | 상세 내용 (평균 201.9자) | 91.5% |
| `startedOn` | Date(가변) | 시작일 | ~80% |
| `endedOn` | Date(가변) | 종료일 (중앙값 기간 4개월) | ~70% |

### 1.12 SelfIntroduction (자기소개서) — Resume 1:N

**규모**: 이력서 커버리지 64.1% (7,962,522), 이력서당 평균 1.55개

| 필드 | 타입 | 설명 | Fill Rate |
|------|------|------|-----------|
| `title` | String | 질문 제목 | ~95% |
| `description` | String | 답변 내용 (중앙값 1,320자) | 97.4% (빈값 2.6%) |

### 1.13 Award (수상) — Resume 1:N

**규모**: 이력서 커버리지 8.8%, 이력서당 평균 2.1개

| 필드 | 타입 | 설명 | Fill Rate |
|------|------|------|-----------|
| `title` | String | 수상 제목 | ~95% |
| `organization` | String | 수여 기관 | ~85% |
| `description` | String | 상세 내용 | **0%** (100% 빈값) |
| `awardedAt` | Date | 수상일 | ~90% |

### 1.14 WorkCondition (희망 근무조건) — Resume 1:1

**규모**: 8,018,110건, Resume과 완전 1:1

| 필드 | 타입 | 설명 | 빈배열 비율 |
|------|------|------|-----------|
| `employmentTypes` | Array(Enum) | 고용형태: PERMANENT(64%) / CONTRACT(18.4%) / INTERN(6.4%) / FREELANCER(6.1%) | 19.8% |
| `workJobField.industryCodes` | Array(Code) | 산업 코드 (INDUSTRY_SUBCATEGORY, 63코드) | **66.0%** |
| `workJobField.industryKeywordCodes` | Array(Code) | 산업 키워드 (INDUSTRY) | 81.7% |
| `workJobField.jobClassificationCodes` | Array(Code) | 직무 코드 (JOB_CLASSIFICATION_SUBCATEGORY, 242+코드) | 17.4% |
| `workJobField.jobKeywordCodes` | Array(Code) | 직무 키워드 (JOB_CLASSIFICATION) | 51.6% |
| `workJobField.jobIndustryCodes` | Array(Code) | 업직종 코드 | **100%** (사용 불가) |
| `workJobField.careerJobIndustryCodes` | Array(Code) | 경력 업직종 코드 | **100%** (사용 불가) |
| `workLocation.countyCodes` | Array(Code) | 구/군 코드 (COUNTY, 63코드) | 13% |
| `workLocation.workArrangementType` | Enum | 근무형태: **97.5% ANY** (구분 불가) | - |
| `workSchedule` | JSON | 근무 스케줄 | **100%** (사용 불가) |
| `salary.type` | Enum | **97.5% ANNUAL** | - |
| `salary.salary` | Number | 희망 연봉 | REDACTED |

---

## 2. job-hub 테이블 구조

> 잡코리아 & 알바몬 Legacy 공고의 공통 속성 재정의 데이터

### 2.1 Job (공고) — 중심 엔티티

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | PK(VARCHAR 126) | 공고 식별자 → **Vacancy.vacancy_id** |
| `title` | String | 공고 제목 |
| `status_type` | Enum(StatusType) | READY / PAUSE / POSTING / CLOSE |
| `posting_type` | Enum(PostingType) | GENERAL / HEAD_HUNTING / AGENT / ONEPICK |
| `posting_company_name` | String | 게시 회사명 |
| `posting_start_at` | Timestamp | 게재 시작일 |
| `posting_end_at` | Timestamp | 게재 종료일 |
| `first_posted_at` | Timestamp | 최초 게시일 |
| `user_ref_key` | String | 원본 사용자 참조키 → **company_id 후보** |
| `workspace_id` | String | 비즈센터 Workspace ID → **company_id 후보** |

### 2.2 Overview (개요) — Job 1:1

| 필드 | 타입 | 설명 |
|------|------|------|
| `descriptions` | JSONB | 상세 요강 (JD 원문 — **evidence_chunk 소스**) |
| `job_classification_codes` | Array(Code) | 직무 코드 (→ **REQUIRES_ROLE 엣지 소스**) |
| `industry_codes` | Array(Code) | 산업 코드 (→ **IN_INDUSTRY 엣지 소스**) |
| `employment_types` | Array(Enum) | 고용형태 |
| `work_fields` | Array | 모집 분야/포지션 |
| `vacancy` | Integer | 모집 인원 |
| `designation_codes` | Array(Code) | 직급/직책 코드 (→ **seniority 추론 소스**) |
| `always_hire` | Boolean | 상시 채용 여부 (→ **operating_model.speed 시그널**) |
| `application_start_at` | Timestamp | 지원 시작일 |
| `application_end_at` | Timestamp | 지원 종료일 |

### 2.3 Requirement (자격 요건) — Job 1:1

| 필드 | 타입 | 설명 |
|------|------|------|
| `education_code` | Code | 최종 학력 코드 |
| `career_types` | Array(Enum) | NEWBIE / EXPERIENCED / ANY |
| `careers` | JSONB | 상세 경력 정보 (경력 연차 범위 등) |
| `license_codes` | Array(Code) | 자격증 코드 |
| `preference_codes` | Array(Code) | 우대 조건 코드 |
| `preference_major_codes` | Array(Code) | 우대 전공 코드 |
| `language_codes` | Array(Code) | 언어 코드 |
| `language_exam_codes` | Array(Code) | 어학 시험 코드 |
| `languages` | JSONB | 언어 상세 (수준 등) |
| `visa_codes` | Array(Code) | 비자 코드 |
| `gender` | Enum | 성별 (NONE/MALE/FEMALE/ANY) |
| `age_range` | INT4RANGE | 연령 제한 |

### 2.4 WorkCondition (근무 조건) — Job 1:1

| 필드 | 타입 | 설명 |
|------|------|------|
| `company_name` | String | 근무 기업명 |
| `location_area_codes` | Array(Code) | 근무지 지역 코드 |
| `location_attributes` | JSONB | 위치 상세 (좌표 등) |
| `work_week_type` | Enum | 근무 요일 (MON_TO_FRI 등) |
| `work_hours_description` | String | 근무 시간 직접 입력 |
| `work_term_type` | Enum | 근무 기간 (단기/장기 등) |
| `work_schedule_option_types` | Array(Enum) | FLEXIBLE_WORK / NEGOTIABLE 등 (→ **autonomy 시그널**) |
| `pay_type` | Enum | 급여 타입 (연봉/월급/시급 등) |
| `pay_range` | INT4RANGE | 급여 범위 |
| `benefit_codes` | Array(Code) | 복리후생 코드 |

### 2.5 Skill (스킬) — Job 1:N

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | PK(TSID) | 스킬 ID |
| `job_id` | FK | 공고 참조 |
| `type` | Enum | SOFT / HARD |
| `code` | Code | 스킬 코드 (→ **REQUIRES_SKILL 엣지 소스**) |

### 2.6 기타 테이블

| 테이블 | 관계 | 용도 | 온톨로지 활용 |
|--------|------|------|-------------|
| Reception | Job 1:1 | 접수 방법 | 낮음 |
| HrManager | Job 1:1 | 채용 담당자 | 낮음 (PII) |
| AdditionalInfo | Job 1:1 | 키워드, 사전 인터뷰 | 보조 (keywords) |
| ServiceSiteMapping | Job 1:N | 사이트 매핑 (ALBAMON/JOBKOREA) | 참조용 |
| WorknetJob | 독립 | 워크넷 공고 (BRN 포함) | Organization 보강 |

---

## 3. code-hub 테이블 구조

> 잡코리아 & 알바몬 공통코드 체계

### 3.1 CommonCode (공통 코드) — 3단계 계층

| 필드 | 타입 | 설명 |
|------|------|------|
| `code` | PK(VARCHAR 126) | group_code + sub_code + detail_code 조합 |
| `parent_code` | String | 상위 코드 |
| `type` | Enum(CommonCodeType) | 코드 유형 (37개) |
| `group_code` | VARCHAR(3) | 1DEPTH 그룹코드 |
| `sub_code` | VARCHAR(3) | 2DEPTH 서브코드 |
| `detail_code` | VARCHAR(4) | 3DEPTH 상세코드 |
| `group_name` | String | 그룹명 |
| `sub_name` | String | 서브명 |
| `detail_name` | String | 상세명 |

### 3.2 CommonCodeType 주요 값 (온톨로지 연관)

| CommonCodeType | 코드 수 | resume-hub 연결 필드 | 온톨로지 노드 |
|---------------|---------|---------------------|-------------|
| `INDUSTRY_SUBCATEGORY` | 63개 | workcondition.industryCodes | Industry |
| `JOB_CLASSIFICATION_SUBCATEGORY` | 242개 | career/workcondition.jobClassificationCodes | Role |
| `HARD_SKILL` | ~2,398개 (표준) | skill.code | Skill |
| `SOFT_SKILL` | ~표준 일부 | skill.code | Skill |
| `POSITION_GRADE` | 15개 | career.positionGradeCode | Chapter.scope_type 추론 |
| `POSITION_TITLE` | 16개 | career.positionTitleCode | Chapter.scope_type 추론 |
| `LICENSE` | 다수 | certificate.code (type=CERTIFICATE) | (보조 데이터) |
| `LANGUAGE_EXAM` | 다수 | certificate.code (type=LANGUAGE_TEST) | (보조 데이터) |
| `UNIVERSITY_CAMPUS` | 다수 | education.schoolCode | (보조 데이터) |
| `PREFERENCE_MAJOR` | 다수 | major.code | (보조 데이터) |
| `LANGUAGE` | 33개 | language.code | (보조 데이터) |
| `DESIGNATION` | 다수 | overview.designation_codes | Vacancy.seniority 추론 |

### 3.3 AreaCode (지역 코드) — 5단계 계층

| 레벨 | 타입 | 설명 |
|------|------|------|
| 1 | CONTINENT | 대륙 (continent_code, 2자리) |
| 2 | NATION | 국가 (nation_code, ISO 3166-1 2자리) |
| 3 | CITY | 시/도 (city_code, 2자리) |
| 4 | COUNTY | 시/군/구 (county_code, 2자리) |
| 5 | TOWN | 읍/면/동 (town_code, 3자리) |

### 3.4 ForeignCodeMapping (외부 코드 매핑)

| 필드 | 설명 |
|------|------|
| `site_type` | ALL / JOBKOREA / ALBAMON / KLIK / GAMEJOB |
| `mapping_code` | 원본 사이트 코드 |
| `type` | CodeHubType (매핑 대상 유형) |
| `code` | 내부 공통코드 (FK → common_code 또는 area_code) |

**역할**: resume-hub/job-hub의 원본 코드 → 표준 코드 변환 레이어

### 3.5 ForeignCodeAttribute (외부 코드 속성)

주요 확장 속성:
- `HARD_SKILL` (JOBKOREA): `displayName`, `synonyms` ← **스킬 정규화 시 동의어 소스**
- `LICENSE` (JOBKOREA): `issuer` ← 발급처 정보
- `UNIVERSITY_CAMPUS` (JOBKOREA): `countryCode`, `institutionType`, `operationStatus`
- `LANGUAGE_EXAM` (JOBKOREA): `criteriaType`, `maxScore`, `minScore`

---

## 4. 외부 이력서 (LinkedIn/BrightData) 테이블 구조

### 4.1 brightdata_dump_raw_stage0b — 프로필 플래트닝

| 분류 | 필드 | 채움률 | 유니크 |
|------|------|--------|--------|
| 기본 | `name` | ~100% | 1,189,850 |
| 기본 | `city` | 100% (실질 ~35%) | 525 |
| 기본 | `country_code` | 100% (전부 KR) | 1 |
| 기본 | `about` | 17.2% | - |
| 현재 직무 | `position` | 96.4% (실질 74.8%) | 1,043,068 |
| 경력 | `experience` | 68.7% (Array of Tuple) | - |
| 학력 | `education` | 41.0% (Array of Tuple) | - |
| 소셜 | `connections` | 69.9% (-1 제외) | - |
| 소셜 | `followers` | 71.0% (-1 제외) | - |

### 4.2 linkedin_experience_standardized — AI 표준화 경력

| 필드 | 설명 |
|------|------|
| `user_id` | 외부 이력서 프로필 ID |
| `exp_index` | 해당 사용자의 N번째 경력 |
| `original_company` → `standardized_company` | 회사명 원본 → 표준화 |
| `original_title` → `standardized_title` | 직책 원본 → 표준화 |
| `job_function`, `job_sub_function` | 직무 분류 |
| `role_type` | 역할 유형 |
| `seniority` | 직급 |
| `skills` | 스킬 |
| `start_date`, `end_date` | 기간 |
| `confidence` | High / Medium / Low |
| `reasoning` | 표준화 근거 |
