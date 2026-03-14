## A. 테이블 리스트

> 
> 
> 
> **분석 대상**: `import_resume_hub_tmp` 데이터베이스 (resume 스키마)
> 

### 1. 메인 테이블 (Main Entities)

가장 핵심이 되는 사용자 및 이력서의 기본 정보

| **테이블명** | **행 수 (Rows)** | **설명** |
| --- | --- | --- |
| `resume.resume` | 8,018,110 | **이력서 메인 (PK: id)**. 제목, 경력구분, 최종학력, 공개여부 등 |
| `user_profile.profile` | 7,780,115 | 유저 프로필 (성별, 나이, 주소, 구직상태). `site_user_mapping_id`로 연결 |

---

### 2. 보조 테이블 (Sub Entities)

이력서(`resume_id`)에 귀속되는 상세 정보 (1:N 관계)

| **테이블명** | **행 수 (Rows)** | **컬럼 수** | **상세 설명** |
| --- | --- | --- | --- |
| `resume.skill` | **20,810,452** | 6 | **스킬**  • HARD/SOFT 구분, 코드+이름 |
| `resume.career` | 18,709,830 | 20 | **경력**  • 회사명, 부서, 업무내용, 근무기간, 직무코드 |
| `resume.certificate` | 13,573,606 | 13 | **자격증**  • 유형, 이름, 발급기관, 점수 |
| `resume.education` | 11,201,436 | 15 | **학력**  • 학교유형, 학교명, 학적상태, GPA |
| `resume.workcondition` | 8,018,110 | 15 | **희망근무조건**  • 고용형태, 업종, 직무, 지역, 연봉 (Array) |
| `resume.self_introduction` | 7,962,522 | 6 | **자기소개서**  • 제목 + 본문 |
| `resume.major` | 7,147,005 | 6 | **전공**  • `education_id`로 학력 테이블과 연결 |
| `resume.experience` | 6,638,635 | 11 | **경험**  • 인턴, 동아리, 봉사 등 |
| `resume.career_description` | 1,351,836 | 4 | **경력기술서**  • 자유 텍스트 (단순 구조) |
| `resume.language` | 653,876 | 9 | **어학**  • 언어, 수준, 연수경험 |

---

## B. 표준화 가능성 및 Hard Filter 사용 가능성 평가

> **목적**: 기업의 exact matching 기반 Hard Filter 검색을 위한 표준화 가능성 평가
> 

---

### 2.1 종합 평가표

> • **표준화 가능성**: 동일 의미 → 동일 코드로 통일할 수 있는 정도
    ◦ 상: 이미 코드 기반 1:1 매핑 or 간단한 정규화로 해결
    ◦ 중: 규칙 기반 정규화 + 일부 수작업 매핑 필요
    ◦ 하: 비정형 텍스트, 자동 표준화 어려움
• **Hard Filter 사용 가능성**: 기업이 텍스트 검색 시 exact matching으로 원하는 후보를 빠짐없이 가져올 수 있는 정도
    ◦ 상: 코드 매핑 완료, 텍스트→코드 변환 후 exact match 가능
    ◦ 중: 코드 매핑은 되지만 유사 코드 누수/미매핑 존재, 보완 필요
    ◦ 하: 코드화 불가 or 표기 불일치가 심해 exact match로 커버 불가
> 

### **2.1 종합 평가표**

- 표기: ⭕=상 / 🔺=중 /  ❌=하

| **엔티티** | **필터 항목** | **출처 테이블** | **유니크 수** | **표준화 가능성** | **Hard Filter 가능성** | **비고** |
| --- | --- | --- | --- | --- | --- | --- |
| 나이 | 나이(범주화 가능) | user_profile.profile | 3 | ⭕ | ⭕ | MALE/FEMALE 등 3값, 100% 채움. 완전 표준화된 enum |
| 성별 | 남/여 | user_profile.profile | - | ⭕ | 🔺 | 숫자형 범위 필터 가능. 0값(미입력) 및 이상치(203세 등) 존재하여 필터 적용 시 누락·오탐 주의 |
| **스킬** | 스킬명/코드 | resume.skill | 101,925 | 🔺 | 🔺 | code:name 1:1이나 한/영 혼재·약어로 텍스트 검색 시 누수. 의미적 동의어 매핑 테이블 필요 |
| **자격증** | 자격증명/코드 | resume.certificate | 3,817 | ⭕ | 🔺 | code 기반 매칭 가능. issuer 정규화만 추가하면 완성도 높음 |
| **자격증 점수** | 어학시험 점수 | resume.certificate | - | ⭕ | 🔺 | 미기입 비율 고려 필요 |
| **회사** | 회사명 | [resume.career](http://resume.career) | 1,107,924 | 🔺 | ❌ | 사업자번호 기반 통합은 가능하나, 텍스트 검색 시 (주)/㈜/주식회사 혼재로 exact match 불가. 대표명 정규화 필수 |
| **고용형태** | 재직/퇴직 | [resume.career](http://resume.career) | 2 | ⭕ | ⭕ | EMPLOYED/RESIGNED 2값, 완전 표준화 |
| **직무분류** | 희망직무 | resume.workcondition | 242 | 🔺 | 🔺 | dict_code 100% 매핑이나 유사 코드 과다 세분화 (동시선택율 20%+). 상위 그룹(~30개) 계층 도입 시 가능 |
| **업종** | 희망업종 | resume.workcondition | 63 | ⭕ | 🔺 | dict_code 100% 매핑, 의료 3코드 통합 외 양호 |
| **지역** | 희망근무지역 | resume.workcondition | 619 | ⭕ | 🔺 | dict_code 97.1% 매핑, 코드 기반 exact match 가능 |
| **고용형태** | 희망고용형태 | resume.workcondition | 7 | ⭕ | 🔺 | enum 7개 값, 완전 표준화 |
| **학교** | 학교명/코드 | [resume.education](http://resume.education) | 10,002 | ❌ | ❌ | 14.6% code 부재(257K 유니크 name), 동명이교(고교), 신구코드 중복, 대학원 과다분리. 텍스트 검색 시 "서울대"→동서울대·남서울대 혼입 |
| **학력수준** | 고졸/초대졸/대졸/석사 | [resume.education](http://resume.education) | 5 | ⭕ | ⭕ | school_type 5개 값, 완전 표준화 |
| **학적상태** | 졸업/재학/중퇴 등 | [resume.education](http://resume.education) | 7 | ⭕ | ⭕ | academic_status 7개 값, 100% 채움 |
| **GPA** | 학점 | [resume.education](http://resume.education) | - | ⭕ | 🔺 | gpa/gpa_scale 정규화 가능 (4.5/4.3 통합). 채움률 33.6%로 필터 적용 시 누락 주의 |
| **전공** | 전공명/코드 | resume.major | 157,032 | 🔺 | ❌ | code:name 1:1이나 "경영"=881개 코드 분산. 접미사(~과/~학과/~학부) 정규화 + 키워드 상위그룹 매핑 필요 |
| **어학** | 어학능력 | resume.language | 33 | ⭕ | ⭕ | code 1:1 매핑, level_group 3단계. 완전 표준화 |
| **수상** | 수상 내역 | resume.award | 863,579 | ❌ | ❌ | 완전 비정형 텍스트, 코드화 불가 |

---

## C. Hard Filter 적용을 위한 권장 조치

### 3.1 즉시 적용 가능 (표준화 상 + Hard Filter 상)

| **필터 항목** | **조치** | **예상 효과** |
| --- | --- | --- |
| 성별 | gender enum exact match | 3개 값(MALE/FEMALE/NONE 등) 정확 매칭 |
| 자격증 | code 기반 exact match | 3,817개 코드로 정확 매칭 |
| 학력수준 | school_type enum | 5개 값 exact match |
| 학적상태 | academic_status enum | 7개 값 exact match |
| 어학 | code + level_group | 33개 어학 × 3단계 |

### 3.2 정규화 작업 후 적용 가능 (표준화 중 → 상 전환 가능)

| **필터 항목** | **필요 작업** | **예상 공수** |
| --- | --- | --- |
| 업종 | industry_code → dict_code name | 소 |
| 지역 | county_code → dict_code name | 소 |
| 고용형태 | employment_types enum | 소 |
| 스킬 | 한/영 동의어 매핑 테이블 구축 (Excel↔엑셀 등), 유사명 클러스터링 | 중 |
| 직무분류 | 상위 그룹(~30개) 카테고리 정의, 242개 코드 → 그룹 매핑 | 중 |
| 학교 | 미매핑 11.5% 수동 매핑, 같은 학교 다른 코드 20건 통합 | 대 |
| 회사명 | (주)/㈜/주식회사 정규화 규칙 + 사업자번호 기반 대표명 테이블 | 대 |
| GPA | gpa/gpa_scale 정규화 수식 적용 | 소 |

## D. 엔티티별 주요 인사이트 및 유의미 컬럼 선정

### 1.1 스킬 (Skill)

| **항목** | **값** |
| --- | --- |
| 출처 테이블 | `resume.skill` (20.8M rows) |
| 유니크 코드 수 | 101,925개 |
| code:name 매핑 | 1:1 (동의어 0건) |
| 같은 name → 다른 code | 30건 (중복 코드) |
| 유의미 컬럼 | `code`, `name`, `type`(HARD/SOFT — 엣지 속성) |

**주요 인사이트**:

- code:name은 1:1 매핑이지만, **텍스트 기반 검색 시 동일 스킬이 다른 코드로 분산**되는 문제 존재
    - 예: `MS-엑셀` ↔ `Excel` ↔ `MS-Excel` — 한/영 혼재, 약어 차이
- SOFT 스킬은 `끈기/인내심`, `팀워크/협동심` 등 의미적 동의어가 다른 코드로 분리 (2그룹)
- 빈도 ≥100 기준 유효 스킬: **1,694개** (전체 대비 1.7%이지만 전체 데이터의 대부분 커버)

---

### 1.2 자격증 (Certificate)

| **항목** | **값** |
| --- | --- |
| 출처 테이블 | `resume.certificate` (13.6M rows) |
| 유니크 코드 수 | 3,817개 |
| 같은 code → 다른 name | 1건 |
| 같은 name → 다른 code | 30건 |
| 유의미 컬럼 | `code`, `name`, `type`, `score`(LANGUAGE_TEST 한정), `issuer`(정규화 필요) |

**주요 인사이트**:

- 자격증 코드 자체는 비교적 깨끗하나, **issuer(발급기관) 표기 불일치**가 존재
    - 예: `한국산업인력공단` vs `한국산업인력관리공단`
- **조건부 유의미 컬럼**: `score`는 전체 빈값률이 높으나 `type='LANGUAGE_TEST'`일 때 49.5% 채움 → 어학시험 점수로 유의미
- `type='CERTIFICATE'`의 score는 0.0% → 제외

---

### 1.3 경력 / 회사 (Career / Company)

| **항목** | **값** |
| --- | --- |
| 출처 테이블 | `resume.career` (18.7M rows) |
| 유니크 사업자번호 | 1,107,924개 |
| 동일 사업자번호 다른 회사명 | 다수 (삼성전자 520개 표기, LG전자 560개 등) |
| 법인 표기 패턴 | (주) 158만, 주식회사 114만, ㈜ 49만 |
| 비표준 패턴 | 프리랜서/군/아르바이트/인턴/자영업 |
| 변별력 없는 컬럼 | days_worked(전부 0), salary(전부 REDACTED), period_type(전부 RANGE) |
| 유의미 컬럼 | `business_registration_number`, `company_name`(정규화 필요), `employment_status`, `period`, `position_grade_code`(39.2% 채움) |

**주요 인사이트**:

- company_name은 **극심한 표기 불일치**: 같은 사업자번호에 수백 개의 다른 이름
    - `(주)삼성전자`, `삼성전자㈜`, `삼성전자주식회사`, `삼성전자(반도체)` 등
- `business_registration_number` 기반 대표명 선정 전략 필요 (최빈 이름 = argMax)
- 빈도 ≥10 기준 Company 노드: **159,454개**

---

### 1.4 학력 / 학교 (Education / School)

| **항목** | **값** |
| --- | --- |
| 출처 테이블 | `resume.education` (11.2M rows) |
| 유니크 school_code | 10,002개 |
| dict_code 매핑률 | 88.5% (미매핑 11.5%) |
| 미매핑 패턴 | `Unknown:C0072001` 등 — 폐교/캠퍼스 통합 추정 |
| 같은 name → 다른 code | 20건 (한국방송통신대학교, 인하공업전문대학 등) |
| GPA 정규화 | gpa/gpa_scale로 4.5/4.3 만점 통합 가능 (avg normalized: 0.797 / 0.792) |
| 유의미 컬럼 | `school_code`, `school_type`, `academic_status`, `gpa`(정규화 필요), `research_topic`(대학원 한정) |

**주요 인사이트**:

- **코드 체계 혼재:** 신코드(1310xxxx) 494만건, 고등학교(2500xxxx) 352만건, Unknown 110만건, 구코드(U0/C0) 63건
    - 같은 학교가 신/구 코드 두 개 보유 (예: 서울대 `1310000930` + 구코드 `U0226015`)
- **code 없는 14.6% (164만건)**: 유니크 name 257,311개 — 폐교, 개명, 비인가, 해외학교, 고등학교 등
    - 예: `검정고시`, `서울호서전문학교`, `아세아항공전문학교` 등 코드 부재
- **"서울대" 텍스트 검색 시 문제**: `동서울대학교`(36K), `남서울대학교`(24K), `서울대학교`(16K) + 대학원 8개 코드 혼재 — exact match로 "서울대학교 출신"을 정확히 찾을 수 없음
- **동명이교 (고등학교)**: `대성고등학교` 3개 코드 (서로 다른 학교), `대원고등학교` 3개 코드 → 지역 코드 + 학교명으로 검색 가능
- **대학원 과도 분리**: 서울대학교만 본교(관악/연건) + 대학원(경영/국제/환경/공학/행정/보건/융합) 10+개 코드
- school_code 미매핑 11.5%는 대부분 `Unknown:` 접두사 → 원본 시스템에서 이미 미매핑
- **name vs code 비대칭:** code 10,002개 vs name 260,525개 — name으로는 매칭 불가
    - 왜 이렇게 비대칭이 심한가?
        
        **실제 수치**
        
        - 전체 [resume.education](http://resume.education) rows: 11,201,436건
            - school_code 있는 rows: 9,562,737건 (85.4%)
                - dict_code에 매핑됨: 8,463,262행 / 7,956 유니크 코드 (88.5%)
                - dict_code에 없음: 1,099,475행 / 2,046 유니크 코드 (11.5%: `Unknown:` 패턴)
            - school_code 없는 rows: 1,638,699건 (14.6%)
        
        핵심 원인: code 없는 164만건이 유니크 name의 대부분을 차지 (실제 유저가 free text로 입력하는 경우 school_code가 “” 빈 값으로 들어감)
        
        ![스크린샷 2026-03-10 오후 3.05.21.png](attachment:fad88a21-f4ca-4721-8889-1688e60fc379:스크린샷_2026-03-10_오후_3.05.21.png)
        
- `academic_status` 100% 채움, 7개 상태값 (GRADUATED 86.2%)

---

### 1.5 전공 (Major)

| **항목** | **값** |
| --- | --- |
| 출처 테이블 | `resume.major` (7.1M rows) |
| 유니크 코드 수 | 16,026개 (code:name 1:1) |
| 같은 code → 다른 name | 0건 |
| 같은 name → 다른 code | 0건 |
| dict_code 미매핑 | 약 6.2% (`Unknown:` 패턴) |
| education_id 정합성 | 100% |
| 유의미 컬럼 | `code`, `name`, `type`(PRIMARY/DOUBLE/MINOR) |

**주요 인사이트**:

- code:name은 1:1이지만, **동일 학문이 접미사 차이로 수백 개 코드에 분산**:
    - `경영과`(1100100537) ≠ `경영학과`(1100100601) ≠ `경영학부`(1100100624) ≠ `경영학`(1100100600) — 모두 다른 코드
    - "경영" 전공자를 찾으려면 **881개 코드** 필요
    - "디자인" → 813개, "컴퓨터" → 302개, "화학" → 484개 코드
- **Levenshtein 기반 유사명 매핑의 한계**: `신학과`↔`철학과`가 거리 1로 묶이지만 완전히 다른 학문
- 접미사(~과/~학과/~학부/~전공/~계열)를 제거한 **키워드 기반 상위 그룹** 매핑이 필요하나, 동음이의어 문제 존재
- type 분포: PRIMARY 93.1%, DOUBLE 3.8%, MINOR 2.5%
- **표준화 과제**: 접미사 정규화 + 키워드 기반 상위 전공 그룹 매핑 테이블 구축 필요

---

### 1.6 희망근무조건 (Work Condition)

| **항목** | **값** |
| --- | --- |
| 출처 테이블 | `resume.workcondition` (8.0M rows) |
| employment_types | 7개 enum (PERMANENT 64%, CONTRACT 18%, INTERN 6% 등) |
| industry_codes | 63개, dict_code 100% 매핑 |
| job_classification_codes | 242개, dict_code 100% 매핑 |
| county_codes | 619개, dict_code 97.1% 매핑 |
| 사용불가 컬럼 | work_schedule(빈), job_industry_codes(빈), career_job_industry_codes(빈) |
| 유의미 컬럼 | `employment_types`, `industry_codes`, `job_classification_codes`, `county_codes` |

**주요 인사이트**:

- dict_code 100% 매핑이지만 **"표준화 완료"는 아님**:
    - **job_classification_codes**: 유사 코드 동시선택율이 높음
        - 실내디자이너 ↔ 공간디자이너: 30.7%, 그래픽 ↔ 시각디자이너: 26.6%
        - 사무담당자 ↔ 사무보조: 21.8%, 요리사 ↔ 조리사: 18.5%
    - **industry_codes**: 의료 3개 코드 동시선택율 12~15% → 상위 그룹 통합 권장
- 디자이너 15개, 엔지니어 15개, 영업 9개, 개발자 9개, AI 12개로 **과도 세분화**
- **권장**: JobCategory(~30개) → JobClassification(242개) 2단 계층

---

### 1.7 경험 (Experience)

| **항목** | **값** |
| --- | --- |
| 출처 테이블 | `resume.experience` (6.6M rows) |
| type 분포 | TRAINING 27%, OVERSEAS 19%, PART_TIME 13%, INTERNSHIP 9% 등 11개 |
| affiliation_code 채움률 | 24% |
| affiliation_name 채움률 | 98% |
| 유의미 컬럼 | `type`, `title`, `affiliation_code`(있는 경우), `affiliation_name`(정규화 필요) |

**주요 인사이트**:

- `affiliation_code`는 24%만 채워져 있어 코드 기반 매칭 제한적
- `affiliation_name`은 98% 채움이나 비정형 텍스트 → 정규화 필요
- type별로 데이터 풍부도가 다름 → 의미 있는 type만 노드화

---

### 1.8 어학 (Language)

| **항목** | **값** |
| --- | --- |
| 출처 테이블 | `resume.language` (654K rows) |
| 유니크 code | 33개 |
| 유니크 name | 985개 |
| 동의어 | 0건 (code:name 1:1) |
| level_group 채움률 | 100% (A/B/C 3단계) |

**주요 인사이트**:

- 33개 어학 코드로 깨끗하게 정리됨, 표준화 이슈 없음
- level_group(A/B/C)으로 수준 구분 가능

**유의미 컬럼**: `code`, `name`, `level_group`

---

### 1.9 수상 (Award)

| **항목** | **값** |
| --- | --- |
| 출처 테이블 | `resume.award` (1.5M rows) |
| 유니크 title | 863,579개 |
| 유니크 organization | 325,079개 |

**주요 인사이트**:

- 완전 비정형 텍스트 → 코드화/표준화 불가
- Resume 속성으로만 활용, 독립 엔티티 부적합

**유의미 컬럼**: 없음 (Hard Filter 대상 아님)

---

## 추가) codehub.dict_code 테이블 EDA

- 총 행 수: 58,413
- 유니크 code 수: 58,413
- 유니크 name 수: 40,157
- 유니크 parent_code 수: 8,829

### type별 코드 구성

| **type** | **code** | **name** | **description** | **parent_code** | **group_code** | **group_name** | **properties** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | PREFERENCE_MAJOR | 1100600109 | 바이오융합기술연계전공 |  |  | 110 | 우대전공 |
| 1 | INDUSTRY | 3020000586 | 전자출판 |  | 3010000047 | 302 | 산업 |
| 2 | UNIVERSITY | 1300007448 | University of Rhode Island |  |  | 130 | 대학 |
| 3 | HARD_SKILL | 1710001513 | DevExpress |  |  | 171 | 하드 스킬 |
| 4 | LICENSE | 2010002554 | 2종전기차량 운전면허 |  | 2000000003 | 201 | 자격증 |
- 같은 이름의 다른 code 상위 20개 예시
    
    ![스크린샷 2026-03-10 오후 7.49.29.png](attachment:6cdcf881-0757-4fe8-a6ec-67fb9586b0bf:스크린샷_2026-03-10_오후_7.49.29.png)