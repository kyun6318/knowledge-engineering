## codehub.dict_code 테이블 EDA 보고서

> **분석 대상**: `codehub.dict_code` — 모든 resume 테이블의 코드를 매핑하는 범용 사전 테이블
**목적**: dict_code 테이블 자체의 데이터 품질 검증, 학교 코드 표기 변형 분석, type별 계층 구조 파악
> 

---

## 1. 테이블 개요

| 항목 | 값 |
| --- | --- |
| 총 행 수 | **58,413** |
| 유니크 code | 58,413 (code = PK, 중복 없음) |
| 유니크 name | 40,157 (18,256개 name이 빈값 또는 중복) |
| 유니크 parent_code | 8,829 |
| 컬럼 | `type`, `code`, `name`, `description`, `parent_code`, `group_code`, `group_name`, `properties` |
| type 종류 | **37개** |

### 1.1 type별 코드 수 상위 10

| type | 코드 수 | parent 보유율 | group_name |
| --- | --- | --- | --- |
| PREFERENCE_MAJOR | 17,231 | 0% | 우대전공 |
| UNIVERSITY_CAMPUS | 9,665 | 100% | 대학 캠퍼스 |
| UNIVERSITY | 8,088 | 0% | 대학 |
| TOWN | 6,216 | 100% | (name 빈값) |
| LICENSE | 4,183 | 85% | 자격증 |
| JOB_CLASSIFICATION | 2,977 | 100% | 직무 |
| HIGH_SCHOOL | 2,516 | 0% | 고등학교 |
| HARD_SKILL | 2,315 | 0% | 하드 스킬 |
| SUBWAY_STATION | 1,082 | 100% | 지하철 호선 |
| INDUSTRY | 936 | 100% | 산업 |

### 1.2 code 접두사별 분포

| 접두사 | 건수 | 예시 |
| --- | --- | --- |
| 13 | 17,753 | 대학/직무/지역 등 |
| 11 | 17,231 | 우대전공 |
| AS | 6,634 | 지역 코드 (TOWN/COUNTY 등, name 빈값) |
| 20 | 4,203 | 자격증 |
| 40 | 3,374 | 직무 분류 |
| 25 | 2,516 | 고등학교 |
| 17 | 2,464 | 하드 스킬 / 언어 |
| 12 | 1,117 | 지하철 |
| 30 | 1,010 | 산업 / 직무 세부 |

---

## 2. 전체 데이터 품질

### 2.1 code:name 매핑 관계

| 관계 | 건수 | 평가 |
| --- | --- | --- |
| 같은 code → 다른 name (1:N) | **0건** | 완벽한 1:1 |
| 같은 name → 다른 code (N:1) | **다수** | 동명이코드 존재 |

**주요 인사이트**:

- code→name은 **완전 1:1** — code가 PK 역할
- name→code 동명이코드 상위:
    - 어학점수 등급(IL, NH, AL 등): 최대 **21개 코드**가 같은 name → 어학시험별 동일 등급명
    - 자격증(노인심리상담사 1급, 병원코디네이터 1급): **10~12개 코드** 중복 → 발급기관별 분리
    - 고등학교(대성고등학교, 대원고등학교): **3개 코드** — 실제 동명이교 (지역이 다른 학교)

### 2.2 빈값 현황

| 컬럼 | 빈값 수 | 비율 |
| --- | --- | --- |
| code | 0 | 0% |
| name | 6,858 | 11.7% |
| parent_code | 31,594 | 54.1% |
- **name 빈값 6,858건**: 주로 지역 코드 — TOWN(6,216), COUNTY(273), CITY(153), NATION(210), CONTINENT(6)
    - 지역 계층은 code 자체가 식별자 역할 (예: `ASKR1024000`), name은 별도 관리로 추정

### 2.3 parent_code 계층 정합성

| 항목 | 값 |
| --- | --- |
| parent 없음 (루트) | 31,594건 (54.1%) |
| parent가 dict_code에 존재 | 26,819건 (45.9%) |
| parent가 dict_code에 미존재 (orphan) | **0건** (0.0%) |
- orphan 0건 → **계층 참조 무결성 완벽**

---

## 3. type별 계층 구조 분석

### 3.1 계층 구조 유형 분류

**핵심 발견: parent→child 관계는 100% 다른 type 간에만 존재** (동일 type 내 계층 = 0건)

### FLAT (계층 없음) — 17개 type

단순 코드:name 매핑만 사용. parent_code가 전부 빈값.

| type | 코드 수 | 비고 |
| --- | --- | --- |
| PREFERENCE_MAJOR | 17,231 | 우대전공 (최대 규모) |
| UNIVERSITY | 8,088 | 대학 (캠퍼스의 parent) |
| HIGH_SCHOOL | 2,516 | 고등학교 |
| HARD_SKILL | 2,315 | 하드 스킬 |
| SOFT_SKILL | 133 | 소프트 스킬 |
| LANGUAGE | 48 | 언어 |
| JOB_CLASSIFICATION_CATEGORY | 35 | 직무 카테고리 |
| LICENSE_CATEGORY | 20 | 자격증 카테고리 |
| BENEFIT | 190 | 복리후생 |
| SUBWAY_LINE | 35 | 지하철 호선 |
| MBTI | 16 | MBTI |
| 기타 6개 | 소규모 | POSITION_GRADE, VISA_GROUP 등 |

### HIERARCHICAL (다른 type을 parent로 참조) — 16개 type

| child type | parent type | 건수 | 깊이 |
| --- | --- | --- | --- |
| NATION | CONTINENT | 210 | 1단계 |
| CITY | NATION | 153 | 2단계 |
| COUNTY | CITY | 273 | 3단계 |
| TOWN | COUNTY | 6,216 | 3단계 |
| BRAND | JOB_INDUSTRY | 536 | 2단계 |
| JOB_INDUSTRY | JOB_INDUSTRY_CATEGORY | 200 | 1단계 |
| INDUSTRY | INDUSTRY_SUBCATEGORY | 936 | 2단계 |
| JOB_CLASSIFICATION | JOB_CLASSIFICATION_SUBCATEGORY | 2,977 | 2단계 |
| UNIVERSITY_CAMPUS | UNIVERSITY | 9,665 | 1단계 |
| SUBWAY_STATION | SUBWAY_LINE | 1,082 | 1단계 |
| LANGUAGE_EXAM_CRITERIA | LANGUAGE_EXAM | 452 | 2단계 |
| LICENSE | LICENSE_CATEGORY | 3,557 | 1단계 |

### 3.2 주요 계층 체인

```
지역:  CONTINENT(6) → NATION(210) → CITY(153) → COUNTY(273) → TOWN(6,216)
       깊이 4단계, name 전부 빈값 (code-only)

직무:  JOB_CLASSIFICATION_CATEGORY(35) → SUBCATEGORY(362) → JOB_CLASSIFICATION(2,977)
       예: AI·개발·데이터 → 응용프로그래머 → 세부 직무 52개

산업:  INDUSTRY_CATEGORY(11) → SUBCATEGORY(63) → INDUSTRY(936)
       예: 의료(진료과별) → 세부 산업 51개

학교:  UNIVERSITY(8,088) → UNIVERSITY_CAMPUS(9,665)
       예: 한국폴리텍 → 40개 캠퍼스, 고려대학교 → 31개 캠퍼스

자격증: LICENSE_CATEGORY(20) → LICENSE(4,183)
        예: 카테고리 20개 → 자격증 3,557개 (미배정 626개)

지하철: SUBWAY_LINE(35) → SUBWAY_STATION(1,082)
        예: 1호선 → 102개 역
```

**주요 인사이트**:

- **UNIVERSITY vs UNIVERSITY_CAMPUS 분리**: 대학(8,088)은 FLAT이지만 캠퍼스(9,665)가 이를 parent로 참조. 캠퍼스가 대학보다 많음 → 캠퍼스 단위 관리
- **지역 계층은 name 빈값**: TOWN/COUNTY/CITY/NATION/CONTINENT 총 6,858건이 전부 name='' → code 자체가 식별자
- **LICENSE 혼합형**: 4,183건 중 3,557건만 parent 보유, 626건은 루트 → 카테고리 미배정 자격증 626개

---

## 4. 도메인별 분석

### 4.1 학교 — 대학 (UNIVERSITY_CAMPUS)

| 항목 | 값 |
| --- | --- |
| type | UNIVERSITY_CAMPUS |
| 접두사 | 1310 (신코드) |
| 코드 수 | 9,665 |
| 유니크 name | 9,665 (code:name 완전 1:1) |
| 동명이코드 | 0건 |
| name 중복률 | **0.0%** |
| parent type | UNIVERSITY (8,088개) |

**주요 인사이트**:

- code:name 품질 **최우수** — 중복·누락 없음
- 정규화 후 동일 학교명에 다른 코드: **243건** (571개 코드 관련)
    - **캠퍼스 분리** 81건: 의도된 분리 (경상국립대 가좌/칠암/통영, 한국폴리텍 계열 등)
    - **동명이교 등 기타** 162건: 실제 다른 학교 또는 공백 변형
- 경상국립대학교 **8개 코드** 중 3개는 불필요한 공백 차이 (정리 대상)
- Levenshtein ≤2 유사쌍 **100건+**: 대부분 해외 대학 동명이교 (Acadia↔Arcadia, DePaul↔DePauw) — 자동 병합 대상 아님
- 주요 대학 코드 분산: 건국대/경희대/한양대 각 10+개 (서울/분교/대학원별 캠퍼스)
- **구코드(U0/C0)가 dict_code에 전혀 없음** → resume.education의 Unknown 코드 발생 원인

### 4.2 학교 — 고교 (HIGH_SCHOOL)

| 항목 | 값 |
| --- | --- |
| type | HIGH_SCHOOL |
| 접두사 | 2500 |
| 코드 수 | 2,516 |
| 유니크 name | 2,415 |
| 동명이코드 | **89건** |
| name 중복률 | **3.7%** |

**주요 인사이트**:

- 동명이교 89건: 대성고(3), 대원고(3), 금성고(3), 덕산고(3), 세종고(3) 등 — 전부 지역이 다른 실제 다른 학교
- Levenshtein ≤2 유사쌍 **50건**: 간동고↔강동고, 갈산고↔금산고 등 — 실제 다른 학교
- 동명이교 해소를 위해 지역 정보 추가 필요 (예: `대성고등학교(서울)`, `대성고등학교(대전)`)

### 4.3 전공 (PREFERENCE_MAJOR)

| 항목 | 값 |
| --- | --- |
| type | PREFERENCE_MAJOR |
| 접두사 | 1100 |
| 코드 수 | 17,231 (최대 규모) |
| 유니크 name | 17,231 |
| 동명이코드 | 0건 |
| name 중복률 | **0.0%** |

**주요 인사이트**:

- code:name 완전 1:1 — 품질 우수
- 전체 37개 type 중 가장 많은 코드 수
- FLAT 구조 (parent 없음)

### 4.4 직무 (JOB_CLASSIFICATION)

| 항목 | 값 |
| --- | --- |
| type | JOB_CLASSIFICATION |
| 접두사 | 1300 |
| 코드 수 | 8,088 |
| 유니크 name | 7,954 |
| 동명이코드 | **112건** |
| name 중복률 | **1.4%** |
| 계층 | CATEGORY(35) → SUBCATEGORY(362) → JOB_CLASSIFICATION(2,977) |

**주요 인사이트**:

- 동명이코드 112건 존재 — UNIVERSITY type과 겹치는 코드가 원인 (접두사 1300 공유)
- 3단계 계층 구조: 최상위 카테고리 35개 → 응용프로그래머(52개 세부), 판매·서빙(32개) 등

### 4.5 자격증 (LICENSE)

| 항목 | 값 |
| --- | --- |
| type | LICENSE |
| 접두사 | 1400/2000 |
| 코드 수 | 4,183 |
| parent 보유율 | 85% (3,557건) |
| 카테고리 미배정 | **626건** |

**주요 인사이트**:

- LICENSE_CATEGORY(20) → LICENSE(3,557) 계층이지만, 626건은 루트 노드 → 카테고리 미배정 자격증

### 4.6 지역 (TOWN/COUNTY/CITY/NATION/CONTINENT)

| 항목 | 값 |
| --- | --- |
| 계층 깊이 | 4단계 |
| 총 코드 수 | 6,858 |
| name 빈값 | **6,858건 (100%)** |
| code 체계 | `ASKR`+숫자 형식 |

**주요 인사이트**:

- 전체 name 빈값의 100%가 지역 계층에 집중
- code 자체가 식별자 역할 → 별도 name 매핑 테이블이 존재할 가능성
- 접두사 `AS`로 시작하는 6,634건이 해당

---

## 5. dict_code ↔ resume.education 교차 분석

| 항목 | 값 |
| --- | --- |
| dict_code 학교 코드 수 | **12,181** |
| resume.education school_code 유니크 수 | **10,002** |
| dict_code에만 있는 코드 (미사용) | **4,225** |
| education에만 있는 코드 (미매핑) | **2,046** |

### 5.1 미매핑 코드 (Unknown) 패턴

| 패턴 | 행 수 | 유니크 코드 수 | 설명 |
| --- | --- | --- | --- |
| Unknown:U0xxx (구대학) | 616,988 | 282 | dict_code에 구코드 자체가 없음 |
| Unknown:C0xxx (구전문대) | 477,690 | 175 | dict_code에 구코드 자체가 없음 |
| Unknown:기타 | 4,702 | 1,526 | 기타 패턴 |
| 기타 | 95 | 63 | — |

**주요 인사이트**:

- **구코드(U0/C0) 체계가 dict_code에서 완전 제거**되었으나, resume.education에는 구코드 참조가 남아 있음 → `Unknown:` 접두사로 표시
- 구코드 미매핑으로 인한 영향: **약 110만건** (전체 education의 상당 비율)
- Unknown:U0xxx 상위: Unknown:U0226(한국방송통신대 추정) 16,908건, Unknown:U0009 12,349건
- Unknown:C0xxx 상위: Unknown:C0072001 40,702건, Unknown:C0147001 38,698건

### 5.2 신코드↔구코드 매핑

| 항목 | 값 |
| --- | --- |
| dict_code 내 1310코드↔U0/C0 동일 name 쌍 | **0건** |
| 이유 | 구코드가 dict_code에 아예 존재하지 않음 |
- resume.education에서 같은 학교가 신코드와 구코드로 분산 사용 중
    - 예: 한국방송통신대학교 — 신코드 79,701건 + Unknown:U0226 16,908건

---

## 6. 권장 조치

### P0 (즉시)

1. **구코드 매핑 테이블 구축**: `Unknown:U0xxx` → `1310xxxx`, `Unknown:C0xxx` → `1310xxxx` 매핑
    - resume.education의 미매핑 **약 110만건** (457개 구코드) 복원 가능
    - Unknown 접두사에서 원본 코드 추출 후 학교명 기반 매칭

### P1 (단기)

1. **캠퍼스 코드 공백 변형 정리**: 경상국립대학교 8개 → 정상 5개로 축소 (불필요 공백 차이 3건 제거)
2. **지역 코드 name 보완**: TOWN/COUNTY/CITY 등 6,858건의 빈 name에 실제 지역명 매핑

### P2 (중기)

1. **동명이코드 해소 전략 수립**:
    - 고교 동명이교(89건): 지역 정보 추가하여 구분 (예: `대성고등학교(서울)`, `대성고등학교(대전)`)
    - 자격증 동명이코드(노인심리상담사 1급 12개 등): 발급기관 기반 통합
2. **UNIVERSITY ↔ UNIVERSITY_CAMPUS 관계 활용**: GraphDB 설계 시 대학→캠퍼스 계층 엣지로 모델링
3. **LICENSE 카테고리 미배정 626건 정리**: 적절한 LICENSE_CATEGORY 할당

### P3 (장기)

1. **type 기반 통합 코드 뷰 구축**: 37개 type과 계층 체인을 활용한 통합 코드 카탈로그
2. **코드 거버넌스 체계**: 신규 코드 등록 시 정규화 검증 (공백, 괄호, 접미사 통일) 자동화

---

## 핵심 수치 요약

| 지표 | 값 |
| --- | --- |
| 총 코드 수 | 58,413 |
| type 수 | 37개 |
| code:name 1:1 위반 | **0건** |
| name 빈값 | 6,858건 (11.7%) — 전부 지역 코드 |
| 학교(대학) name 중복률 | 0.0% |
| 학교(고교) 동명이교 | 89건 (3.7%) |
| 구코드 미매핑으로 인한 Unknown | **~110만건** |
| 정규화 기반 캠퍼스 중복 | 243건 (571개 코드) |
| 자동 병합 불가 Levenshtein 쌍 | 150건+ (대부분 동명이교) |