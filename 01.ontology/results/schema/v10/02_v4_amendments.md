# v4 스키마 보완 사항 (Amendments)

> v4 평가에서 식별된 5개 보완 권장사항 + crawling 전략에서 발견된 1개 정합성 이슈를 해결.
> 이 문서의 내용은 v4 문서(01~04)에 대한 **패치**로, v5 이후 스키마에 반영한다.
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

> **[v8] 통합판 이관 완료** — 이 amendment의 내용은 01~04 통합판(v7)에 인라인 반영되었습니다.
> 정본은 해당 통합판 문서를 참조하세요.
> 변경 이력: CompanyTalentSignal 의도적 제외 명문화 및 v2 로드맵 배치

---

## A4. STAGE_SIMILARITY 전체 매트릭스

> **[v8] 통합판 이관 완료** — 이 amendment의 내용은 03_mapping_features(v7) 통합판에 인라인 반영되었습니다.
> 정본은 해당 통합판 문서를 참조하세요.
> 변경 이력: STAGE_SIMILARITY 전체 4x4 매트릭스 확정, 비대칭 설계 근거, 캘리브레이션 계획

---

## A5. Company 간 관계 미포함 이유

> **[v8] 통합판 이관 완료** — 이 amendment의 내용은 04_graph_schema(v7) 통합판에 인라인 반영되었습니다.
> 정본은 해당 통합판 문서를 참조하세요.
> 변경 이력: Company 간 관계 의도적 제외 명문화, v2 로드맵(COMPETES_WITH, INVESTED_BY 등)

---

## A6. structural_tensions Taxonomy 확정

> **[v8] 통합판 이관 완료** — 이 amendment의 내용은 01_company_context(v7), 06_crawling_strategy(v7) 통합판에 인라인 반영되었습니다.
> 정본은 해당 통합판 문서를 참조하세요.
> 변경 이력: tension_type 8개 taxonomy 확정, 배타성 가이드, related_tensions 구조, T4 Tier ceiling 예외 규칙

---

## A7. GraphRAG vs Vector Baseline 비교 실험 계획 [v6 추가]

> **[v9] 통합판 이관 완료** — 이 amendment의 내용은 05_evaluation_strategy(v8) 통합판에 독립 문서로 확장 반영되었습니다.
> 정본은 해당 통합판 문서를 참조하세요.
> 변경 이력: 실험 설계, Vector Baseline 구성(임베딩 모델/입력/통제변수), 선택적 B' 실험, 의사결정 트리, 평가 지표 상세

---

## A8. 추출 프롬프트 확장 로드맵 [v7 추가: C6-1, C6-2 반영]

### 문제

v6 기준으로 필수 페이지/기사 유형(P1~P3, N1, N4)에 대해서는 상세 추출 프롬프트가 완비되었으나, 선택 유형(P4~P6, N2, N3, N5)은 추출 구조만 정의되어 있다. 파일럿에서 필수 유형의 프롬프트가 안정화된 후 선택 유형의 프롬프트를 단계적으로 추가해야 한다.

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
| 2단계 | Phase 3 (통합) | N3 (M&A) | N2/N5 프롬프트 검증 완료, A6 taxonomy 연동 필요 |
| 3단계 | Phase 4 초기 (배치) | P4 (기술 블로그) | 홈페이지 크롤러 안정 운영 확인 |
| 4단계 | Phase 4 중기 | P5 (팀/문화), P6 (고객 사례) | P4 프롬프트 검증 완료 |

**우선순위 근거**:
- N2/N5: 필수/선택 카테고리이지만 수집 빈도가 높고, 구조화된 추출이 CompanyContext 보강에 직접 기여
- N3: A6 tension taxonomy와 연동 필요 (`build_vs_buy`, `integration_tension`), N4 프롬프트 패턴 재활용 가능
- P4: `operating_model.facets` 보강에 기여, 블로그 존재 자체가 `process` facet 지지
- P5/P6: 기여도가 가장 낮고, P3와 중복 추출 가능성 있음

### 안정화 판정 기준

각 단계 전환 시 이전 단계 프롬프트의 안정화를 다음 4개 지표로 판정한다:

| 지표 | 기준 | 측정 방법 |
|---|---|---|
| 추출 성공률 | >= 80% | 프롬프트 실행 건수 중 유효 JSON 반환 비율 |
| 팩트 정확도 | >= 85% | Human eval 샘플링 10건에서 추출 사실의 정확도 |
| 광고성 오추출률 | <= 10% | 광고성 표현이 결과에 포함된 비율 |
| JSON 파싱 성공률 | >= 95% | LLM 응답의 JSON 파싱 성공 비율 |

> 4개 지표 중 3개 이상을 충족하면 안정화로 판정하고 다음 단계를 진행한다.

---

## 변경 요약

| # | 항목 | 영향 문서 | 변경 유형 |
|---|---|---|---|
| A1 | ScopeType <-> Seniority 매핑 | `02_candidate_context`, `03_mapping_features` | 추가 (변환 규칙), [v6] FOUNDER HEAD 승격 |
| A2 | Industry 노드 정의 | `04_graph_schema` | 추가 (노드 스키마), [v6] is_regulated 판정 기준 |
| A3 | CompanyTalentSignal 제외 명문화 | 전체 | 명문화 (v2 로드맵) |
| A4 | STAGE_SIMILARITY 전체 매트릭스 | `03_mapping_features` | 수정 (부분 -> 전체), [v6] 캘리브레이션 계획 |
| A5 | Company 간 관계 제외 명문화 | `04_graph_schema` | 명문화 (v2 로드맵) |
| A6 | structural_tensions Taxonomy | `01_company_context`, `01_crawling_strategy` | 추가 (8개 enum), [v6] 배타성 가이드 + related_tensions, [v7] Tier ceiling 예외 |
| A7 | GraphRAG vs Vector 비교 실험 | 전체 | [v6] 신규, [v7] Vector baseline 구체화, [v9] 05_evaluation_strategy 이관 완료 |
| A8 | 추출 프롬프트 확장 로드맵 | `01_crawling_strategy` | [v7] 신규 (4단계 일정 + 안정화 판정 기준) |
