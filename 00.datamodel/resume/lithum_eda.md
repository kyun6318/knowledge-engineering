# 데이터 파이프라인 및 테이블 명세

## A. 데이터 파이프라인 및 테이블 설명

### 전체 흐름

BrightData (외부 이력서 크롤링)

→ stage0a (원본 JSON 덤프)

→ stage0b (JSON → 컬럼 플래트닝)

→ linkedin_experience_standardized (경력 추출 + AI 표준화)

---

### brightdata_dump_raw_stage0a

> **역할**: BrightData에서 크롤링한 외부 이력서 프로필 원본 적재
> 
- **단위**: 1행 = 1 외부 이력서 프로필
- **특징**: 프로필 전체 정보가 `data` JSON 컬럼 하나에 중첩되어 있음 (이름, 학력, 경력, 자격증 등)
- **주요 컬럼**: `_src_file` (수집 파일), `_src_line` (행 번호), `vanity_name` (프로필 ID), `data` (JSON)

---

### ⭐ brightdata_dump_raw_stage0b

> **역할**: stage0a의 JSON을 개별 컬럼으로 플래트닝(펼침)한 분석용 테이블
> 
- **단위**: 1행 = 1 외부 이력서 프로필
- **특징**: 경력(`experience`), 학력(`education`) 등은 Array(Tuple) 타입으로, 한 사람의 여러 경력이 배열 안에 중첩
- **주요 컬럼 분류**:
    - **기본 프로필**: `name`, `first_name`, `last_name`, `location`, `country_code`, `city`, `avatar`, `about`
    - **현재 직무**: `position`, `current_company` (Tuple)
    - **경력**: `experience` (Array of Tuple — company, title, duration, description 등)
    - **학력**: `education` (Array of Tuple — title, degree, field 등)
    - **기타**: `certifications`, `languages`, `honors_and_awards`, `patents`, `publications`, `volunteer_experience`
    - **소셜**: `connections`, `followers`, `recommendations`, `recommendations_count`

---

### deleteme_brightdata_dump_raw_stage0_old

> **역할**: stage0b의 이전 버전 (폐기 예정)
> 

---

### ⭐ linkedin_experience_standardized

> **역할**: stage0b의 `experience` 배열을 1건=1행으로 정규화하고, AI(LLM)로 표준화한 핵심 테이블
> 
- **단위**: 1행 = 1명의 1개 경력
- **특징**: 원본값과 표준화값이 쌍으로 존재 (original → standardized). AI 표준화 신뢰도(`confidence`)와 근거(`reasoning`)도 포함.
- **주요 컬럼 분류**:
    - **식별**: `user_id` (외부 이력서 프로필), `exp_index` (해당 사용자의 N번째 경력)
    - **회사**: `original_company` → `standardized_company`
    - **직책**: `original_title` → `standardized_title`, `job_function`, `job_sub_function`
    - **위치**: `original_location` → `country`, `city`
    - **분류**: `role_type` (역할 유형), `seniority` (직급)
    - **부가**: `skills`, `start_date`, `end_date`
    - **AI 메타**: `confidence` (High/Medium/Low), `reasoning` (표준화 근거)

---

## B. 주요 테이블 인사이트 및 유의미 컬럼 선정

> 타겟 테이블: brightdata_dump_raw_stage0b
> 

## 1.1 지역 (City)

| **항목** | **값** |
| --- | --- |
| **출처 테이블** | `brightdata_dump_raw_stage0b` (2.0M rows) |
| **출처 컬럼** | `city` (채움률 100%), `location` (채움률 28.6%) |
| **유니크 수 (정규화 전)** | 525개 |
| **유니크 수 (정규화 후)** | 483개 |
| **country_code** | 1개 (전부 `KR`) |

### 1.1.1 주요 인사이트

- `location`은 `city`의 축약값이며 채움률 28.6%로 낮음, 완전 일치 0건 → **location 폐기, city 사용 권장**
- city 값의 64.8%가 "South Korea"(국가명만)로 실질 지역 정보 없음
    - 상세: `Seoul, South Korea` 16.7%, `Gangnam-gu, Seoul, South Korea` 11.9%, `Metropolitan Area` 6.6%
- 쉼표 split → 시/도 추출 정규화 시 상위 20개 city로 **93.6% 커버** 가능 (단, 65%는 국가명만이라 실질 커버리지 제한)
- `country_code`는 전부 `KR` → 상수값으로 필터 의미 없음

### 1.1.2 주요 이슈

**City 칼럼 패턴별 샘플 - 정규화 전 원본값**

- 설명: city 칼럼에 4가지 패턴으로 값이 들어가 있음
    - Case 1) 국가명만: South Korea
    - Case 2) 시, 국가: Seoul, South Korea
    - Case 3) 구/동, 시, 국가:  Yongin, Gyeonggi, South Korea
    - Case 4) Metropolitan: Seoul Incheon Metropolitan Area
- 정규화를 통해 Case 2,3,4에서 도시명을 추출할 수 있지만 국가명만 있는 경우가 64.8%로 city 기반 hard filter 커버리지가 낮음
    
    
    | **정규화 후 city** | **건수** |
    | --- | --- |
    | (국가명만) | 1,307,982 |
    | Seoul | 288,723 |
    | Seoul Incheon | 121,812 |
    | Gyeonggi | 50,831 |
    | Busan | 14,936 |
    | Yongin | 10,890 |
    | Daejeon | 10,351 |
    | Seongnam | 9,999 |
    | Incheon | 8,558 |

> **유의미 컬럼**: `city`(정규화 필요)
> 
> 
> **사용 불가 컬럼**: `location`(폐기), `country_code`(상수)
> 

---

## 1.2 경력 / 회사 (Experience — stage0b)

| **항목** | **값** |
| --- | --- |
| **출처 테이블** | `brightdata_dump_raw_stage0b.experience` (Array of Tuple) |
| **빈배열 비율** | 631,760건 (31.3%) |
| **유효 프로필** | 1,387,533건 (68.7%) |
| **총 경력 레코드 (ARRAY JOIN)** | 2,695,840건 |
| **company 유니크** | 933,923개 |
| **title 유니크** | 530,824개 |
- experience array<tuple> 구조
    1. company
    2. url
    3. company_id
    4. company_logo_url
    5. title
    6. subtitle
    7. subtitleURL
    8. description
    9. description_html
    10. starte_date
    11. end_date
    12. duration
    13. duration_short
    14. location
    15. position (array<tuple> 구조)
        - 직책명 (title)
        - 회사명 (subtitle)
        - 설명 (description)
        - 시작/종료일 (start_date/end_date)
        - 재직기간 (duration)
        - 근무지 (location)
    

### 1.2.1 주요 인사이트

- company에 **한/영 혼재** 심각: `삼성전자`(9,658건) vs `Samsung Electronics`(24,910건)
    - `LG Electronics`(18,125건), `프리랜서`(10,964건), `KT`(6,570건) 등
- title도 한/영 혼재 + **직급/직무 혼재**: `대리`(55K) / `과장`(54K) / `Manager`(50K) / `CEO`(32K)
    - 직급(대리/과장/차장/부장)과 직무(개발자/디자이너)가 같은 필드에 혼재
    - company명과 title이 같은 경우, 회사내에서 포지션이 바뀐 경우임 → experience.position에 해당 내용이 포함되어있음
- description 채움률 31.5%로 텍스트 기반 분석 제한적

### 1.2.2 주요 이슈

- [experience.company](http://exerience.company) ≠ experience.title인 경우 (92.9%)
    - company 명과 title이 달라 주로 title이 직무/직급/주요 업무 등의 내용이 들어감
    - 그런데 company명과 title이 다른데 position에 값이 있는 경우는 없음
    
    ![스크린샷 2026-03-11 오후 2.18.51.png](attachment:730d9d6c-5603-4c04-961d-0a344090bb47:35de13f8-fbde-48ef-8627-5cfcb65f6f19.png)
    
- [experience.company](http://exerience.company) = experience.title이고, position 필드가 채워진 경우 (7.1%)
    - company명과 title을 동일하게 입력하고, position에 직무/직급/주요 업무를 디테일하게 적는 경우가 있음 (아예 position을 넣지 않은 경우도..)
    - 해석: 같은 회사에서 포지션이 바뀌거나 직급(승진)이 변화했을때 추가가능한 것으로 추정
    
    ![스크린샷 2026-03-11 오후 2.30.41.png](attachment:6fe57126-c56c-4064-85f4-b44b611eab8e:72c7f5a5-4953-41e7-943e-cefebf7e9787.png)
    
    ![스크린샷 2026-03-11 오후 2.52.07.png](attachment:a6041e4e-2dcd-43a6-b347-d12ff77cd060:스크린샷_2026-03-11_오후_2.52.07.png)
    
- [experience.company](http://exerience.company) = experience.title이고, position 필드가 비어있는 경우
    
    거의 채워지지 않은 프로필일 확률이 높음
    
    ![스크린샷 2026-03-11 오후 3.36.12.png](attachment:428b40a6-038d-40c6-9eea-3843ced4e134:스크린샷_2026-03-11_오후_3.36.12.png)
    

### 1.2.3 내부 필드 채움률

| **필드** | **인덱스** | **채움률%** |
| --- | --- | --- |
| title | 5 | 100.0% |
| company | 1 | 99.9% |
| company_logo_url | 4 | 82.5% |
| url | 2 | 47.1% |
| company_id | 3 | 43.7% |
| description | 8 | 31.5% |

> **유의미 컬럼**: `company`(정규화 필요), `title`(분류 모델 필요), `start_date`, `end_date`, `description`(보조)
> 

---

## 1.3 학력 / 학교 (Education — stage0b)

| **항목** | **값** |
| --- | --- |
| **출처 테이블** | `brightdata_dump_raw_stage0b.education` (Array of Tuple) |
| **빈배열 비율** | 1,191,652건 (59.0%) |
| **유효 프로필** | 827,641건 (41.0%) |
| **총 학력 레코드 (ARRAY JOIN)** | 1,256,049건 |
| **school 유니크** | 다수 (한/영 혼재) |

### 1.3.1 주요 인사이트

- **한/영 혼재**: `서울대학교 (Seoul National University)`(31K) vs `Seoul National University`(21K) vs `서울대학교`(별도)
    - `고려대학교`(32K), `한양대학교`(28K), `Yonsei University 연세대학교`(23K) vs `Yonsei University`(17K)
    - `Bachelor of Science - BS` (13K), `Bachelor's degree`(100K),  `학사`(231K)
- 빈배열 59.0%로 학력 정보 자체의 커버리지가 낮음
- 표준화 가능성
    - **school**: 괄호·슬래시 제거만으로 유니크 축소 가능. 한/영 대표명 매핑 테이블 구축 시 Hard Filter 가능
    - **degree**: 유니크 적음, 규칙 기반 매핑으로 5~7개 카테고리 표준화 가능 → Hard Filter 유력 후보
    - **field_of_study(전공명)**: 유니크 다수, 키워드 기반 상위 그룹 매핑 필요 → 난이도 높음
    - **start_year/end_year**: 연도 필터(Range Filter) 가능, 비연도 값 정리 필요

### 1.3.2 내부 필드 채움률

| **필드** | **채움건수** | **채움률%** | **유니크수** |
| --- | --- | --- | --- |
| **edu.1 (school/학교명)** | 1,235,076 | 98.3% | 107,378 |
| **edu.2 (url)** | 945,363 | 75.3% | - |
| **edu.3 (start_year)** | 1,097,139 | 87.3% | - |
| **edu.4 (end_year)** | 1,069,702 | 85.2% | - |
| **edu.5 (degree)** | 983,609 | 78.3% | 86,952 |
| **edu.6 (field_of_study)** | 839,726 | 66.9% | 153,097 |

> **유의미 컬럼**: `school`(정규화 필요), `degree`(정규화 필요, URL 정리 선행)
> 
> 
> **주의 컬럼**: `field` 계열 (인덱스 매핑 재확인 필요)
> 

---

## 1.4 현재 직무 (Position — stage0b)

| **항목** | **값** |
| --- | --- |
| **출처 테이블** | `brightdata_dump_raw_stage0b` (2.0M rows) |
| **출처 컬럼** | `position` |
| **채움률** | 96.4% (빈값 3.6%) |
| **placeholder 비율** | 21.6% (`--`, `.`, `-` 등) |
| **실질 유효** | 74.8% |
| **유니크 수** | 1,043,068개 |

### 1.4.1 주요 인사이트

- 외부이력서 첫 프로필 사진 아래 소개되는 공간에 들어가는 **자유 텍스트** (ex. 커리어케어/ Executive Director)
- 채움률 96.4%이나 placeholder 21.6% 제거 시 **실질 유효 74.8%**
- 유니크 104만개로 자유 텍스트 → 코드화 불가
- 직급, 직무, 회사명이 혼재된 비정형 텍스트

> **유의미 컬럼**: 없음 (Hard Filter 부적합 — Vector Search 권장)
> 

---

## 1.5 수치형 지표 (Connections / Followers)

| **항목** | **값** |
| --- | --- |
| **출처 테이블** | `brightdata_dump_raw_stage0b` (2.0M rows) |
| **connections 유효율** | 69.9% (-1이 아닌 경우) |
| **followers 유효율** | 71.0% (-1이 아닌 경우) |
| **상관관계** | connections ≈ followers (극단 편향, 1-10 구간 집중) |

### 1.5.1 주요 인사이트

- 대부분 1-10 구간에 집중, **connections >= 50 기준 "활성 사용자" 18.3% 선별 가능**
- `recommendations_count`는 99.1%가 -1 → 분석 제외
- connections, followers가 -1인 60만개의 프로필이 유의미한 데이터를 갖고있는가?
    - 주요 항목에 대해서 채워져있는지를 확인함 (총 5개: city, position, experience, education, about)
    - 완성도 높음 (3개+): 443,676명 (73.1%) → 유지 가치 있음
    - 완성도 낮음 (0~1개): 117,775명 (19.4%) → 제거 후보
    
    ![스크린샷 2026-03-11 오후 4.03.03.png](attachment:5dba26ed-5ca3-480e-b55e-608327b5dd8e:스크린샷_2026-03-11_오후_4.03.03.png)
    

### 구간별 분포

| **구간** | **connections** | **conn_%** | **followers** | **fol_%** |
| --- | --- | --- | --- | --- |
| = -1 | 606,859 | 30.1% | 585,969 | 29.0% |
| 1-10 | 787,074 | 39.0% | 801,387 | 39.7% |
| 11-50 | 258,821 | 12.8% | 260,193 | 12.9% |
| 51-100 | 108,660 | 5.4% | 109,876 | 5.4% |
| 101-500 | 257,879 | 12.8% | 191,882 | 9.5% |
| 500+ | 0 | 0.0% | 69,986 | 3.5% |

> **유의미 컬럼**: `connections`, `followers` (Range Filter 적용 가능)
> 
> 
> **사용 불가 컬럼**: `recommendations_count`(99.1% 무효)
> 

---

## 1.6 저채움 Array 컬럼 (Languages, Certifications 등)

| **컬럼** | **유효건수** | **채움률%** |
| --- | --- | --- |
| languages | 181,733 | 9.0% |
| certifications | 127,859 | 6.3% |
| honors_and_awards | 46,469 | 2.3% |
| publications | 40,293 | 2.0% |
| projects | 37,687 | 1.9% |
| volunteer_experience | 36,413 | 1.8% |
| organizations | 19,243 | 1.0% |
| patents | 11,939 | 0.6% |

### 1.6.1 주요 인사이트

- **전부 채움률 10% 미만** → Hard Filter / Vector Search 모두 부적합
- 외부 이력서 프로필 특성상 선택 입력 항목은 대부분 미기입

> **유의미 컬럼**: 없음 (전체 사용 불가)
> 

---

## 1.7 기타 프로필 컬럼

| **항목** | **값** |
| --- | --- |
| **about 채움률** | 17.2% (82.8% 빈값) |
| **name 유니크** | 1,189,850개 |
| **educations_details 채움률** | 40.9% (59.1% 빈값) |

### 1.7.1 주요 인사이트

- `about`은 채움률 17.2%의 장문 텍스트 → 분석 대상 부적합
- `educations_details`는 education Array와 중복되며 요약 문자열

> **유의미 컬럼**: 없음 (Hard Filter 부적합)
> 

---