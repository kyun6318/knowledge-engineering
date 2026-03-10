# 누락 필드 분석 보고서

> 생성일: 2026-03-03
> 데이터: ClickHouse `import_resume_hub_tmp` (jobko.io DEV)
> 기준: 총 이력서 8,018,110건 (resume.resume 기준), 총 사용자 7,780,115명 (profile 기준), career 18,709,830건, education 11,201,148건
> 코드 레이블: codehub 딕셔너리 매핑 완료. hiring_advantages 항목 코드는 AI 추정.

---

## 1. `user_profile.profile.hiring_advantages` — 취업우대사항

취업우대사항은 96.73%가 빈배열이며, 기재 시 군 관련 항목이 가장 많다.

| 지표 | 값 |
|---|---|
| 총 프로필 수 | 7,780,115 |
| 빈배열 비율 | **96.73%** |
| 이력서당 평균 개수 | 0.037개 |
| 최대 개수 | 5개 |

**항목별 빈도 Top 6** (항목 코드는 AI 추정)

| 순위 | 항목 코드 | 건수 | 추정 의미 |
|---|---|---|---|
| 1 | MILITARY_EXEMPTED | 114,497 | 병역 면제 |
| 2 | MILITARY_NOT_COMPLETED | 46,251 | 미필 |
| 3 | EMPLOYMENT_SUBSIDY | 44,101 | 취업지원금 대상 |
| 4 | NATIONAL_MERIT | 38,306 | 국가유공자 |
| 5 | DISABILITY | 24,052 | 장애인 |
| 6 | EMPLOYMENT_PROTECTION | 19,971 | 고용보호 대상 |

기재 건수(254,181명, 3.27%)보다 TOP 6 합계(287,178)가 많으므로 멀티셀렉트 구조임. 법적 의무 항목이므로 실제 대상자의 자발적 미기재 가능성이 높다. 코드 체계가 6종만 확인되어 전체 코드 목록은 codehub에서 별도 확인 필요.

---

## 2. `resume.resume.complete_status` — 이력서 완성도 상태

이력서의 98.28%가 COMPLETED 상태이며 미완성은 1.70%에 불과하다.

| complete_status | 건수 | 비율 |
|---|---|---|
| COMPLETED | 7,879,887 | **98.28%** |
| BASIC_INFO_COMPLETED | 136,370 | 1.70% |
| NONE | 1,471 | 0.02% |
| SKILL_SET_COMPLETED | 382 | 0.00% |

n = 8,018,110

NONE 1,471건은 시스템 오류 또는 마이그레이션 잔재로 추정. 완성도 필터 기준으로 COMPLETED 단일값 사용 가능.

---

## 3. `resume.resume.final_education_status` — 최종 학력 재적 상태

최종 학력 재적 상태의 86.74%가 졸업(GRADUATED)이다.

| final_education_status | 건수 | 비율 |
|---|---|---|
| GRADUATED | 6,955,114 | **86.74%** |
| NONE | 361,334 | 4.51% |
| EXPECTED_GRADUATION | 355,032 | 4.43% |
| ENROLLED | 143,622 | 1.79% |
| DROPPED_OUT | 99,322 | 1.24% |
| LEAVE_OF_ABSENCE | 64,745 | 0.81% |
| COMPLETED | 38,941 | 0.49% |

n = 8,018,110

비교: `education.academic_status`(학력 테이블 전체 레코드)도 GRADUATED 86.17%로 유사하나, 복수 학력 보유자가 중복 집계되어 DROPPED_OUT/ENROLLED 비율이 더 높게 나타난다.

---

## 4. `resume.career.position_grade_code` — 직급 코드

직급 코드 60.84%가 미입력이며, 기재 건 중 사원(18.89%)이 가장 많다.

| position_grade_code | 건수 | 비율 | 직급명 |
|---|---|---|---|
| *(빈값)* | 11,382,228 | **60.84%** | 미입력 |
| 6010000001 | 3,534,575 | 18.89% | 사원 |
| 6010000005 | 1,034,083 | 5.53% | 대리 |
| 6010000007 | 812,543 | 4.34% | 과장 |
| 6010000003 | 688,042 | 3.68% | 주임/계장 |
| 6010000009 | 348,265 | 1.86% | 차장 |
| 6010000011 | 344,742 | 1.84% | 부장 |
| 6010000013 | 224,552 | 1.20% | 임원 |
| 6010000002 | 124,415 | 0.66% | 연구원 |
| 6010000006 | 60,035 | 0.32% | 선임연구원 |
| 6010000008 | 53,563 | 0.29% | 책임연구원 |
| 기타 코드 | ~102,208 | ~0.55% | — |

n = 18,709,830 (career 전체 레코드). codehub type: POSITION_GRADE. 전체 15코드 매핑 완료 (08-codehub-mapping.md 참조).

---

## 5. `resume.career.position_title_code` — 직책 코드

직책 코드 70.55%가 미입력이며, 기재 건 중 팀원(17.24%)이 가장 많다. 직급보다 미입력 비율이 9.71%p 높다.

| position_title_code | 건수 | 비율 | 직책명 |
|---|---|---|---|
| *(빈값)* | 13,199,481 | **70.55%** | 미입력 |
| 6020000001 | 3,225,962 | 17.24% | 팀원 |
| 6020000002 | 1,010,913 | 5.40% | 팀장 |
| 6020000003 | 503,994 | 2.69% | 매니저 |
| 6020000005 | 252,949 | 1.35% | 실장 |
| 6020000004 | 174,327 | 0.93% | 파트장 |
| 6020000006 | 83,984 | 0.45% | 지점장 |
| 6020000010 | 75,429 | 0.40% | 본부장 |
| 기타 코드 | ~182,791 | ~0.98% | — |

n = 18,709,830. codehub type: POSITION_TITLE. 전체 16코드 매핑 완료 (08-codehub-mapping.md 참조).

---

## 6. `resume.career.employment_status` — 재직 상태

경력 레코드의 89.52%가 퇴직(RESIGNED) 상태이며 빈값은 없다.

| employment_status | 건수 | 비율 |
|---|---|---|
| RESIGNED | 16,748,690 | **89.52%** |
| EMPLOYED | 1,961,140 | 10.48% |

n = 18,709,830

현직자(EMPLOYED) 10.48%는 경력 레코드 기준이다. 1인이 여러 경력을 가질 수 있으므로 이용자 단위 현직자 비율은 이보다 높다.

---

## 7. `resume.education.degree_program_type` — 학위 유형

학위 유형의 96.15%가 NONE이며, 대학원생 식별에만 유용한 필드다.

| degree_program_type | 건수 | 비율 |
|---|---|---|
| NONE | 10,770,377 | **96.15%** |
| MASTER | 386,589 | 3.45% |
| DOCTORATE | 36,562 | 0.33% |
| INTEGRATED | 7,908 | 0.07% |

n = 11,201,436

school_type=GRADUATE임에도 NONE인 17,334건은 대학원 재학/수료자가 학위 유형을 미입력한 케이스로 추정. MASTER의 ASSOCIATE 1건은 데이터 오류.

---

## 8. `resume.workcondition.work_arrangement_type` — 근무 형태

근무 형태의 97.46%가 ANY(무관)로, 변별력이 없는 필드다.

| work_arrangement_type | 건수 | 비율 |
|---|---|---|
| ANY | 7,814,346 | **97.46%** |
| *(빈값)* | 203,764 | 2.54% |

n = 8,018,110

재택근무·하이브리드 등의 세분화 코드가 존재하지 않아 구직자 희망 근무형태를 필터 기준으로 활용하기 어렵다. 향후 코드 확장이 필요하다.

---

## 9. `resume.certificate.score_type` — 점수 유형

자격증 점수 유형의 96.39%가 NONE이다. 어학시험 점수를 보유한 자격증에서만 의미있는 분포가 나타난다.

| score_type | 건수 | 비율 |
|---|---|---|
| NONE | 13,084,181 | **96.39%** |
| SCORE | 243,684 | 1.80% |
| GRADE | 237,624 | 1.75% |
| PASS | 8,117 | 0.06% |

n = 13,573,606 (certificate 전체)

SCORE(수치 점수)와 GRADE(등급)가 거의 동수. 어학시험(TOEIC 등) 점수 보유 여부 필터에 한정적으로 사용 가능.

---

## 10. `resume.career.salary_type` — 급여 유형

급여 유형 38.23%가 미입력이며, 기재 건 전체가 ANNUAL(연봉)이다.

| salary_type | 건수 | 비율 |
|---|---|---|
| ANNUAL | 11,557,866 | **61.77%** |
| *(빈값)* | 7,151,964 | 38.23% |

n = 18,709,830

MONTHLY·HOURLY 등 다른 유형 코드가 스키마에 존재하나 실제 데이터에 없다. 입력 UI가 연봉만 지원하거나 마이그레이션 시 변환된 것으로 추정된다. 비정규직·단기 계약직의 급여 데이터 다양성이 반영되지 않는 구조적 한계가 있다.

---

## 11. 신선도 컬럼 — `updated_at` vs `user_updated_at` vs `indexed_at`

| 컬럼 | 중앙값 경과일 | 추정 날짜 | 최솟값 |
|---|---|---|---|
| `updated_at` | 1,097일 | 2023-03-02 | 2001-11-01 |
| `user_updated_at` | 1,029일 | 2023-05-09 | 2001-11-01 |
| `indexed_at` | 43일 | 2026-01-20 | 2026-01-14 |

n = 8,018,110

`indexed_at`은 2026년 1~2월 배치 인덱싱 결과로 전체가 최근값을 가져 신선도 기준으로 부적합하다. `user_updated_at`을 신선도 기준으로 채택한다 (07b 보고서에서 상세 검증).

---

## 12. `user_profile.profile.area_code` — 거주 지역

지역 코드 28.25%가 미입력이며, 서울·경기 수도권 집중도가 높다.

| 지표 | 값 |
|---|---|
| 빈값 건수 | 2,198,058 |
| 빈값 비율 | **28.25%** |
| 총 프로필 수 | 7,780,115 |

**area_code 상위 10개** (codehub type: COUNTY, properties JSON에서 cityName+countyName 추출)

| 순위 | area_code | 건수 | 비율 | 지역명 |
|---|---|---|---|---|
| 1 | *(빈값)* | 2,198,058 | 28.25% | 미입력 |
| 2 | ASKR1006000 | 124,879 | 1.61% | 서울특별시 관악구 |
| 3 | ASKR1005000 | 106,778 | 1.37% | 서울특별시 강서구 |
| 4 | ASKR1019000 | 100,094 | 1.29% | 서울특별시 송파구 |
| 5 | ASKR0343000 | 97,257 | 1.25% | 경기도 화성시 |
| 6 | ASKR1308000 | 90,147 | 1.16% | 인천광역시 서구 |
| 7 | ASKR1307000 | 87,512 | 1.12% | 인천광역시 부평구 |
| 8 | ASKR0312000 | 86,544 | 1.11% | 경기도 남양주시 |
| 9 | ASKR1002000 | 78,101 | 1.00% | 서울특별시 강남구 |
| 10 | ASKR1023000 | 77,368 | 0.99% | 서울특별시 은평구 |

codehub COUNTY의 `name` 컬럼이 비어 있어 `properties` JSON에서 지역명을 추출해야 한다. 빈값 28.25%는 지역 기반 필터 정확도에 영향을 준다.

```sql
-- area_code 지역명 추출 (codehub.codes 직접 조회)
SELECT
  code,
  JSONExtractString(toString(properties), 'cityName') AS city,
  JSONExtractString(toString(properties), 'countyName') AS county
FROM codehub.codes
WHERE type = 'COUNTY'
  AND code IN ('ASKR1006000', 'ASKR1005000', 'ASKR1019000');
```

---

## 결측 메커니즘 분류 (MCAR / MAR / MNAR)

> **[AI 추정]** 아래 결측 메커니즘 분류는 데이터 패턴 관찰에 기반한 추정이며, 엄밀한 통계적 검정(Little's MCAR test 등)은 수행되지 않았다. 실제 결측 메커니즘 확정을 위해서는 (1) 결측 여부와 다른 변수 간 상관분석, (2) 플랫폼 입력 UI 이력 확인이 필요하다.

| 필드 | 결측률 | 분류 | 근거 |
|------|--------|------|------|
| `hiring_advantages` | 96.73% 빈배열 | **MAR** | 법적 우대사항(병역, 장애 등)은 해당자만 기재. 결측은 "해당 없음"과 "미기재"가 구분 불가하나, 항목 특성상 비해당자의 비기재가 지배적 — 결측이 관측 가능한 사용자 속성(나이, 성별 등)에 의존 |
| `position_grade_code` | 60.84% | **MAR** | 미입력률이 경력 유형(career_type)과 상관 — 신입(NEW_COMER) 및 비정규직에서 미입력 비율이 높을 것으로 추정. 기재 시 15개 코드에 완전 매핑되므로 관측값 자체의 편향은 적음 |
| `position_title_code` | 70.55% | **MAR** | position_grade_code와 유사 패턴. 직급보다 직책 미입력이 9.71%p 더 높은 것은 직책 개념이 명확하지 않은 소규모 사업장 종사자에서 미입력 경향이 높기 때문으로 추정 |
| `salary_type` | 38.23% | **MNAR** | 급여 정보 미입력은 급여 수준 자체와 관련될 가능성 — 저임금 근로자 또는 비정규직이 급여 정보를 의도적으로 생략하는 경향. 기재 건 100%가 ANNUAL인 점도 UI 제약에 의한 구조적 결측 가능성 시사 |
| `area_code` | 28.25% | **MAR/MCAR 혼합** | 가입 경로(모바일/웹)에 따라 결측률이 달라질 수 있음(MAR). 일부는 단순 건너뛰기(MCAR). 가입 경로 데이터와의 교차 분석으로 구분 가능 |
| `degree_program_type` | 96.15% NONE | **구조적 NA** | 대학원 이외 학력에서는 학위 유형이 개념적으로 존재하지 않음. "결측"이 아닌 "해당 없음"으로, 전통적 MCAR/MAR/MNAR 분류 대상이 아님. 대학원 학력(school_type=GRADUATE) 내에서의 NONE 17,334건만이 진정한 결측 |
| `work_arrangement_type` | 2.54% 빈값 | **구조적 결측** | 97.46%가 ANY(무관)로 사실상 무의미한 단일값 필드. 빈값 2.54%는 마이그레이션 잔재로 추정. 재택/하이브리드 등 코드 확장 전까지 결측 분석 의미 없음 |
| `score_type` | 96.39% NONE | **구조적 NA** | 어학시험 자격증에만 해당하는 필드. 일반 자격증(운전면허, 기사 등)에서의 NONE은 결측이 아닌 해당 없음 |

**결측 처리 권고:**
- **MAR 필드** (hiring_advantages, position_grade/title_code): 결측이 무작위가 아니므로 단순 삭제(listwise deletion) 시 편향 발생. 다중대체법(Multiple Imputation) 또는 결측 자체를 별도 카테고리로 처리 권장
- **MNAR 필드** (salary_type): 결측 자체가 정보를 담고 있으므로 "미공개" 카테고리로 처리. 결측 비율이 높은 집단의 특성 별도 분석 필요
- **구조적 NA** (degree_program_type, work_arrangement_type, score_type): 해당 없음으로 처리. 분석 대상 모집단 정의 시 사전 필터링 적용

---

## 종합 요약 — 필드별 활용 가능성 평가

| 필드 | 빈값/NONE 비율 | 활용 가능성 | 비고 |
|---|---|---|---|
| hiring_advantages | 96.73% 빈배열 | 낮음 | 법적 우대 항목 편중, 자발적 미기재 다수 |
| complete_status | 1.70% 미완성 | 높음 | COMPLETED 기준 필터링 가능 |
| final_education_status | 4.51% NONE | 높음 | resume 레벨 최종 학력 상태 |
| position_grade_code | 60.84% 빈값 | 중간 | 기재 시 정확, codehub 15코드 완전 매핑 |
| position_title_code | 70.55% 빈값 | 낮음 | 직급보다 미입력 9.71%p 더 많음 |
| employment_status | 0% 빈값 | 높음 | 현직/퇴직 이분법, 명확 |
| degree_program_type | 96.15% NONE | 낮음 | 대학원생 식별에만 유용 |
| work_arrangement_type | 2.54% 빈값 | 낮음 | 사실상 ANY 단일값, 세분화 필요 |
| score_type | 96.39% NONE | 낮음 | 어학시험 점수 보유 여부에만 활용 |
| salary_type | 38.23% 빈값 | 낮음 | 기재 시 100% ANNUAL |
| user_updated_at | — | 높음 | 신선도 기준 컬럼으로 채택 |
| area_code | 28.25% 빈값 | 중간 | codehub COUNTY 매핑 완료, properties JSON 추출 필요 |

---

**후속 작업**
- hiring_advantages 코드 전체 목록을 codehub에서 조회하여 AI 추정값 검증
- work_arrangement_type 코드 확장 여부 Product 팀 확인 (재택/하이브리드 지원 계획)
- area_code 빈값 28.25% 원인 분석 — 가입 단계 미수집 또는 선택 생략 여부 확인
- salary_type MONTHLY/HOURLY 코드 실제 입력 경로가 있는지 BE 코드 확인

*Report: 2026-03-03 | Scientist Agent (claude-sonnet-4-6)*
