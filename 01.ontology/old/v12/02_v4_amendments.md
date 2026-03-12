# v4 스키마 보완 사항 (Amendments)

> v4 평가에서 식별된 5개 보완 권장사항 + crawling 전략에서 발견된 1개 정합성 이슈를 해결.
> 이 문서의 내용은 v4 문서(01~04)에 대한 **패치**로, v5 이후 스키마에 반영한다.
>
> **v12 반영** (2026-03-10): 데이터 분석 v2.1 결과 통합
> - [A10] 실측 데이터 기반 설계 결정 (fill rate, 품질, 제약 조건)
> - [A10] Person 노드 보강 속성 (gender, age, careerType, freshness_weight)
> - [A10] 정규화 선행 과제 5건 및 4단계 구현 로드맵
> - [A10] CareerDescription FK 부재 제약 반영
> - [A10] Certificate type 매핑 변환 (CERTIFICATE→LICENSE)
> - [A10] Resume 품질 등급 기반 서비스 풀 필터링
>
> **v11 반영** (2026-03-09): 내부 DB 매핑(00_data_source_mapping.md) 신규 추가에 따른 참조 관계 기록
>
> **v11.1 반영** (2026-03-09): 비정형 값 비교 전략 (임베딩 기반)
> - [A9] 비정형 값 비교 3-Tier 전략 (정규화 적합 / 경량 정규화+임베딩 / 임베딩 전용)
> - [A9] normalize_skill() 경량화 (CI + synonyms만, fuzzy/한영사전 제거)
> - [A9] 스킬/전공/직무명은 임베딩 유사도 기반 비교로 전환
> - [A9] 임베딩 비교 품질 모니터링 (6.4절)
>
> 작성일: 2026-03-08
>
> **v6 반영** (2026-03-08): v5 리뷰 피드백 반영
> - [A1-1] FOUNDER의 경력 연수 기반 HEAD 승격 규칙 추가
> - [A2-1] is_regulated 판정 기준 목록 추가
> - [A4-1] STAGE_SIMILARITY 매트릭스 캘리브레이션 계획 추가
> - [A6-1] tension_type 간 배타성 정리 및 related_tensions 구조 추가
> - [V-6] CompanyContext JSON 스키마 업데이트 지침 명시
>
> **v7 반영** (2026-03-08): v6 리뷰 잔여 권장사항 3건 반영
> - [V-6] T4 Tier ceiling 예외 규칙 명문화 (A6 뒤 신규 하위섹션)
> - [A7-1] Vector baseline 구체화 (임베딩 모델/입력/통제변수 명시)
> - [C6-1, C6-2] A8 추출 프롬프트 확장 로드맵 신규 추가
>
> **v8 반영** (2026-03-08): [E-4/E-5] A1~A6 통합판 이관 완료 표시
>
> **v9 반영** (2026-03-08): [E-2] A7도 A1~A6과 동일하게 통합판 이관 완료 표시

---

## A1. ScopeType <-> Seniority 매핑 테이블

> **[v8] 통합판 이관 완료** — 이 amendment의 내용은 02_candidate_context(v7), 03_mapping_features(v7) 통합판에 인라인 반영되었습니다.
> 정본은 해당 통합판 문서를 참조하세요.
> 변경 이력: scope_type(IC/LEAD/HEAD/FOUNDER) → seniority 변환 규칙 및 FOUNDER HEAD 승격 규칙 정의

---

## A2. Industry 노드 정의

> **[v8] 통합판 이관 완료** — 이 amendment의 내용은 04_graph_schema(v7) 통합판에 인라인 반영되었습니다.
> 정본은 해당 통합판 문서를 참조하세요.
> 변경 이력: Industry 노드 스키마 정의, is_regulated 판정 기준, IN_INDUSTRY 관계 쿼리 예시

---

## A3. CompanyTalentSignal 처리 방침

> **[v8] 통합판 이관 완료**

---

## A4. STAGE_SIMILARITY 전체 매트릭스

> **[v8] 통합판 이관 완료**

---

## A5. Company 간 관계 미포함 이유

> **[v8] 통합판 이관 완료**

---

## A6. structural_tensions Taxonomy 확정

> **[v8] 통합판 이관 완료**

---

## A7. GraphRAG vs Vector Baseline 비교 실험 계획

> **[v9] 통합판 이관 완료** — 05_evaluation_strategy에 독립 문서로 확장 반영.

---

## A8. 추출 프롬프트 확장 로드맵 [v7 추가]

### 문제

v6 기준으로 필수 페이지/기사 유형(P1~P3, N1, N4)에 대해서는 상세 추출 프롬프트가 완비되었으나, 선택 유형(P4~P6, N2, N3, N5)은 추출 구조만 정의되어 있다.

### 현황: 프롬프트 완비/미비 정리

| 유형 | 우선순위 | 프롬프트 상태 | 비고 |
|---|---|---|---|
| P1 (회사 소개) | 필수 | 완비 | v6 |
| P2 (제품/서비스) | 필수 | 완비 | v6 |
| P3 (채용) | 필수 | 완비 | v6, 광고성 필터 내장 |
| P4 (기술 블로그) | 선택 | **미비** | 추출 구조만 정의 |
| P5 (팀/문화) | 선택 | **미비** | 추출 구조만 정의 |
| P6 (고객 사례) | 선택 | **미비** | 추출 구조만 정의 |
| N1 (투자) | 필수 | 완비 | v6 |
| N2 (제품 런칭) | 필수 | **미비** | 추출 구조만 정의 |
| N3 (M&A) | 선택 | **미비** | 추출 구조만 정의 |
| N4 (조직 변화) | 선택 | 완비 | v6, A6 taxonomy 연동 |
| N5 (실적) | 선택 | **미비** | 추출 구조만 정의 |

### 해결: 4단계 추가 일정

| 단계 | 시기 | 대상 | 전제 조건 |
|---|---|---|---|
| 1단계 | Phase 2 (파일럿) | N2 (제품 런칭), N5 (실적) | P1~P3/N1/N4 프롬프트 안정화 확인 |
| 2단계 | Phase 3 (통합) | N3 (M&A) | N2/N5 프롬프트 검증 완료 |
| 3단계 | Phase 4 초기 (배치) | P4 (기술 블로그) | 홈페이지 크롤러 안정 운영 확인 |
| 4단계 | Phase 4 중기 | P5 (팀/문화), P6 (고객 사례) | P4 프롬프트 검증 완료 |

### 안정화 판정 기준

| 지표 | 기준 | 측정 방법 |
|---|---|---|
| 추출 성공률 | >= 80% | 프롬프트 실행 건수 중 유효 JSON 반환 비율 |
| 팩트 정확도 | >= 85% | Human eval 샘플링 10건에서 추출 사실의 정확도 |
| 광고성 오추출률 | <= 10% | 광고성 표현이 결과에 포함된 비율 |
| JSON 파싱 성공률 | >= 95% | LLM 응답의 JSON 파싱 성공 비율 |

> 4개 지표 중 3개 이상을 충족하면 안정화로 판정하고 다음 단계를 진행한다.

---

## A9. 비정형 값 비교 전략 — 임베딩 기반 [v11.1 추가]

> **[v11.1] 00_data_source_mapping.md에 인라인 반영 완료.**
> 정본은 00_data_source_mapping.md 0절, 1.3절, 1.5절, 4.3절, 6.4절을 참조하세요.

---

## A10. 실측 데이터 기반 설계 결정 [v12 추가]

### 문제

v11까지의 설계는 데이터 fill rate, 품질, 제약 조건을 **추정치**에 기반하여 결정했다. 데이터 분석 v2.1(14개 테이블, ~120M 레코드, 8M 이력서, 7.78M 사용자)이 완료됨에 따라, 실측 수치로 설계를 검증하고 보정해야 한다.

### 주요 발견 및 영향

| # | 발견 | 영향 | 반영 위치 |
|---|---|---|---|
| D1 | fill rate 추정치 vs 실측치 괴리 (positionTitle 추정 30~40% → 실측 29.45%) | 실측치 전면 교체 | 00_data_source_mapping §6 |
| D2 | Person 보강 가능 속성 발견 (gender 100%, age 93.3%, freshness 100%) | Person 노드 속성 추가 | 00_data_source_mapping §3.5, 04_graph_schema |
| D3 | career.daysWorked 100% 제로 — period 기반 계산 필수 | duration_months 계산 로직 명시 | 00_data_source_mapping §3.2, §7.1 |
| D4 | CareerDescription에 career_id FK 없음 | Outcome/Signal 추출 제약 반영 | 00_data_source_mapping §3.2 |
| D5 | Certificate type 매핑 불일치 (CERTIFICATE≠LICENSE) | 변환 로직 추가 | 00_data_source_mapping §1.8 |
| D6 | Resume 품질 등급 분포 (HIGH+PREMIUM 61.6%) | 서비스 풀 필터링 추가 | 00_data_source_mapping §3.1 |
| D7 | 스킬 20개 캡, 97.6% 비표준, co-occurrence 클러스터 | 스킬 실측 현황 반영 | 00_data_source_mapping §1.3 |
| D8 | Education finalEducationLevel vs schoolType 35.6% 불일치 | schoolType을 진실 소스로 지정 | 00_data_source_mapping §3.5, §5.2 |
| D9 | 정규화 선행 과제 5건 식별 | 구현 전 필수 과제 목록 | 00_data_source_mapping §7 |
| D10 | 4단계 구현 로드맵 (Phase 1~4) | 구현 우선순위 정의 | 00_data_source_mapping §8 |

### 변경 내용

**00_data_source_mapping.md**: D1~D10 전체 반영 (0절 원칙 추가, 1.3/1.8절 실측, 3.1~3.6절 보강, 5절 파이프라인, 6절 전면 교체, 7~9절 신규)

### 영향 범위

| 영향 대상 | 변경 내용 |
|---|---|
| `00_data_source_mapping.md` | 0, 1.3, 1.5, 1.7, 1.8(신규), 2.3, 3.1~3.6, 5.1, 5.2, 6.1~6.5, 7~9절(신규) |
| `04_graph_schema` (v10) | Person 노드 속성 추가 필요 (v12에서는 00에 정의, 04 업데이트는 v13) |
| `02_candidate_context` (v10) | Person 보강 속성 적용 시 업데이트 필요 |
| `03_mapping_features` (v10) | F1~F5 예상 ACTIVE 비율 실측 기반 보정 |

---

## 변경 요약

| # | 항목 | 영향 문서 | 변경 유형 |
|---|---|---|---|
| A1 | ScopeType <-> Seniority 매핑 | `02_candidate_context`, `03_mapping_features` | [v8] 통합판 이관 완료 |
| A2 | Industry 노드 정의 | `04_graph_schema` | [v8] 통합판 이관 완료 |
| A3 | CompanyTalentSignal 제외 명문화 | 전체 | [v8] 통합판 이관 완료 |
| A4 | STAGE_SIMILARITY 전체 매트릭스 | `03_mapping_features` | [v8] 통합판 이관 완료 |
| A5 | Company 간 관계 제외 명문화 | `04_graph_schema` | [v8] 통합판 이관 완료 |
| A6 | structural_tensions Taxonomy | `01_company_context`, `06_crawling_strategy` | [v8] 통합판 이관 완료 |
| A7 | GraphRAG vs Vector 비교 실험 | `05_evaluation_strategy` | [v9] 통합판 이관 완료 |
| A8 | 추출 프롬프트 확장 로드맵 | `06_crawling_strategy` | [v7] 신규 (미이관, 독립 유지) |
| A9 | 비정형 값 비교 전략 (임베딩 기반) | `00_data_source_mapping` | [v11.1] 인라인 반영 완료 |
| A10 | 실측 데이터 기반 설계 결정 | `00_data_source_mapping`, `02~04` | [v12] 신규 (00에 인라인 반영, 02~04는 차기 반영) |
