# v10 Extraction Logic 리뷰 요약

> 리뷰일: 2026-03-11 | 리뷰어: Claude Opus 4.6
> 대상: 02.knowledge_graph/results/extraction_logic/v10/ (6개 문서)
> 참조: 04.graphrag/results/implement_planning/core/2/ (GraphRAG Core v2)

---

## 1. 총평

v10은 온톨로지 v19, GCP 인프라, GraphRAG Core v2 세 축을 하나의 "추출 로직" 문서로 통합하려는 시도다. 각 축의 내용을 충실히 반영했으나, **문서의 정체성이 모호해졌다**는 것이 핵심 문제다.

- **타당성**: 기술 선택과 아키텍처 판단은 대체로 합리적 (8/10)
- **실현 가능성**: 27주 로드맵은 현실적이나, 전제 조건 미충족 리스크가 큼 (6/10)
- **과도한 설계**: GraphRAG Core v2와 중복이 심하고, 추출 로직 범위를 넘는 내용 다수 (과도 5건)
- **부족한 설계**: LLM 프롬프트 설계, 데이터 검증, 에러 복구 등 핵심 구현 세부사항 부재 (부족 7건)

---

## 2. 핵심 판정

### 문서 역할 혼란 (가장 큰 문제)

v10은 "Extraction Pipeline" 문서인데, 실제로는 다음을 모두 포함:
- 추출 파이프라인 설계 (본래 역할)
- GCP 인프라 아키텍처 (→ 03.ml_pipeline 영역)
- 매칭 알고리즘 설계 (→ 04.graphrag 영역)
- 서빙 API 설계 (→ 04.graphrag 영역)
- 27주 실행 계획 (→ 04.graphrag 영역)
- 운영/모니터링 체계 (→ 04.graphrag 영역)

**GraphRAG Core v2 (04.graphrag/results/implement_planning/core/2/)와 80% 이상 내용이 중복된다.**

### 권고

v10은 **추출 로직에 집중**하고, 실행 계획/인프라/서빙/운영은 04.graphrag에서 관리해야 한다.
현재 상태에서는 두 문서 간 불일치가 발생할 때 어느 것이 canonical인지 불명확하다.

---

## 3. 리뷰 문서 목록

| 파일 | 내용 |
|------|------|
| 00_review_summary.md | 본 요약 |
| 01_review_validity.md | 타당성 리뷰 (기술 선택, 아키텍처 판단) |
| 02_review_feasibility.md | 실현 가능성 리뷰 (일정, 비용, 인력, 전제 조건) |
| 03_review_over_engineering.md | 과도한 설계 (범위 초과, 불필요한 복잡성) |
| 04_review_under_engineering.md | 부족한 설계 (누락된 핵심 사항) |
| 05_review_action_items.md | 조치 사항 및 권고 |

---

## 4. 점수 요약

| 평가 항목 | 점수 | 비고 |
|----------|------|------|
| 기술적 타당성 | 8/10 | 모델/인프라 선택 합리적 |
| 온톨로지 v19 정합성 | 9/10 | 충실한 반영 |
| 실현 가능성 (일정) | 6/10 | 전제 조건 미충족 리스크 |
| 실현 가능성 (비용) | 7/10 | Gold Label이 전체의 77% |
| 문서 정체성/범위 | 4/10 | GraphRAG Core v2와 심각한 중복 |
| 구현 디테일 | 5/10 | 프롬프트, 에러 복구 등 부재 |
| GraphRAG v2 정합성 | 8/10 | 소소한 불일치 존재 |
