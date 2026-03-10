# codehub 코드 매핑 딕셔너리

> 생성일: 2026-03-03
> 출처: ClickHouse `codehub.codes` 테이블 (data-analytics-ch.dev.jobko.io)

이력서 데이터에서 사용되는 코드값의 레이블 매핑 딕셔너리. 직급·직책·지역 코드를 codehub에서 조회한 전체 목록이다.

---

## A. position_grade_code (직급) — type: `POSITION_GRADE`

| 코드 | 직급명 |
|---|---|
| 6010000001 | 사원 |
| 6010000002 | 연구원 |
| 6010000003 | 주임/계장 |
| 6010000004 | 주임연구원 |
| 6010000005 | 대리 |
| 6010000006 | 선임연구원 |
| 6010000007 | 과장 |
| 6010000008 | 책임연구원 |
| 6010000009 | 차장 |
| 6010000010 | 수석연구원 |
| 6010000011 | 부장 |
| 6010000012 | 연구소장 |
| 6010000013 | 임원 |
| 6010000014 | 기사 |
| 6010000015 | 주무 |

codehub에는 6010000016(기원)~6010000020(기성)까지 추가 코드가 존재하나 이력서 데이터에는 미등장한다.

```sql
SELECT code, name FROM codehub.codes WHERE type = 'POSITION_GRADE' ORDER BY code;
```

---

## B. position_title_code (직책) — type: `POSITION_TITLE`

| 코드 | 직책명 |
|---|---|
| 6020000001 | 팀원 |
| 6020000002 | 팀장 |
| 6020000003 | 매니저 |
| 6020000004 | 파트장 |
| 6020000005 | 실장 |
| 6020000006 | 지점장 |
| 6020000007 | 지사장 |
| 6020000008 | 원장 |
| 6020000009 | 국장 |
| 6020000010 | 본부장 |
| 6020000011 | 센터장 |
| 6020000012 | 공장장 |
| 6020000013 | 그룹장 |
| 6020000014 | 조장 |
| 6020000015 | 반장 |
| 6020000016 | 직장 |

```sql
SELECT code, name FROM codehub.codes WHERE type = 'POSITION_TITLE' ORDER BY code;
```

---

## C. area_code (지역) — type: `COUNTY`

`name` 컬럼이 현재 비어 있어 `properties` JSON의 `cityName` + `countyName` 필드에서 추출해야 한다.

| 코드 | 시/도 | 구/시 | 전체 지역명 |
|---|---|---|---|
| ASKR0303000 | 경기도 | 고양시 덕양구 | 경기도 고양시 덕양구 |
| ASKR0312000 | 경기도 | 남양주시 | 경기도 남양주시 |
| ASKR0322000 | 경기도 | 시흥시 | 경기도 시흥시 |
| ASKR0337000 | 경기도 | 의정부시 | 경기도 의정부시 |
| ASKR0340000 | 경기도 | 평택시 | 경기도 평택시 |
| ASKR0343000 | 경기도 | 화성시 | 경기도 화성시 |
| ASKR1002000 | 서울특별시 | 강남구 | 서울특별시 강남구 |
| ASKR1003000 | 서울특별시 | 강동구 | 서울특별시 강동구 |
| ASKR1005000 | 서울특별시 | 강서구 | 서울특별시 강서구 |
| ASKR1006000 | 서울특별시 | 관악구 | 서울특별시 관악구 |
| ASKR1007000 | 서울특별시 | 광진구 | 서울특별시 광진구 |
| ASKR1008000 | 서울특별시 | 구로구 | 서울특별시 구로구 |
| ASKR1010000 | 서울특별시 | 노원구 | 서울특별시 노원구 |
| ASKR1013000 | 서울특별시 | 동작구 | 서울특별시 동작구 |
| ASKR1014000 | 서울특별시 | 마포구 | 서울특별시 마포구 |
| ASKR1018000 | 서울특별시 | 성북구 | 서울특별시 성북구 |
| ASKR1019000 | 서울특별시 | 송파구 | 서울특별시 송파구 |
| ASKR1020000 | 서울특별시 | 양천구 | 서울특별시 양천구 |
| ASKR1021000 | 서울특별시 | 영등포구 | 서울특별시 영등포구 |
| ASKR1023000 | 서울특별시 | 은평구 | 서울특별시 은평구 |
| ASKR1028000 | 서울특별시 | 중랑구 | 서울특별시 중랑구 |
| ASKR1304000 | 인천광역시 | 남동구 | 인천광역시 남동구 |
| ASKR1307000 | 인천광역시 | 부평구 | 인천광역시 부평구 |
| ASKR1308000 | 인천광역시 | 서구 | 인천광역시 서구 |

```sql
-- COUNTY 지역명 추출 (name 컬럼 비어있음, properties JSON 사용)
SELECT
  code,
  JSONExtractString(toString(properties), 'cityName')   AS city,
  JSONExtractString(toString(properties), 'countyName') AS county
FROM codehub.codes
WHERE type = 'COUNTY'
  AND code IN (...);
```

---

## 주의사항

**딕셔너리 조회 (`codehub.dict_code`) 사용 시**

- POSITION_GRADE / POSITION_TITLE: `name` 컬럼 직접 값 있음 — 딕셔너리 정상 작동
- COUNTY: `name` 컬럼이 비어 있어 `dictGetString('codehub.dict_code', 'name', ('COUNTY', code))` 조회 시 빈 문자열 반환됨
- 지역명은 반드시 `codehub.codes.properties` JSON에서 추출할 것

**코드 타입 실제 매핑 (08b 보고서 관련)**

| 이력서 코드 형식 | 실제 codehub 타입 | 문서 표기와 차이 |
|---|---|---|
| 401xxxxxxx (직무 코드) | `JOB_CLASSIFICATION_SUBCATEGORY` | `JOB_CLASSIFICATION`이 아님 |
| 301xxxxxxx (산업 코드) | `INDUSTRY_SUBCATEGORY` | `INDUSTRY`가 아님 |

딕셔너리 쿼리 시 위 실제 타입명을 사용해야 한다.

*Report: 2026-03-03 | Scientist Agent (claude-sonnet-4-6)*
