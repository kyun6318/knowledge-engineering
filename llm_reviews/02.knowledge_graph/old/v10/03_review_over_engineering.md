# v10 과도한 설계 리뷰

> 범위 초과, 불필요한 복잡성, 시기상조 설계 식별

---

## 과도 #1: GraphRAG Core v2와의 심각한 중복 (Critical)

### 현황

v10 "Extraction Pipeline" 문서가 다루는 범위:

| v10 문서 | 섹션 | GraphRAG Core v2 대응 |
|---------|------|---------------------|
| 01_extraction_pipeline.md §7 | Agent Serving API | 00_overview.md §13 (거의 동일) |
| 01_extraction_pipeline.md §6 | MappingFeatures 계산 | 04_phase3.md (동일) |
| 01_extraction_pipeline.md §10 | GraphRAG vs Vector 실험 | 04_phase3.md §3-5 (동일) |
| 02_model_and_infrastructure.md §4 | GCP 인프라 아키텍처 | 00_overview.md §5-6 (동일) |
| 03_execution_plan.md | 전체 27주 로드맵 | 00_overview.md §2 + Phase별 문서 (거의 동일) |
| 04_assumptions_and_risks.md | GCP/GraphRAG 리스크 | 각 Phase 문서 내 리스크 (분산) |
| 05_operations_and_monitoring.md | 운영/모니터링 체계 | 06_cost_and_monitoring.md (동일) |

**80% 이상 내용이 중복**. 두 문서를 독립적으로 유지보수하면 불일치가 누적된다.

### 이미 발생한 불일치

- 관계명: v10 PERFORMED_ROLE vs GraphRAG v2 HAD_ROLE
- 비용 총액: v10 $7,567-10,507 vs GraphRAG v2 $8,235-8,895
- Embedding 비용: v10 내부 $37.5 vs $25.5 불일치

### 권고

**v10은 "추출 로직"으로 범위를 한정해야 함:**
- Pipeline A (CompanyContext 생성): 소스 매핑, LLM 프롬프트, 필드별 추출 로직
- Pipeline B/B' (CandidateContext 생성): DB 매핑, 파일 파싱, LLM 추출
- Pipeline C (Graph 적재): 스키마 매핑, UNWIND 패턴, 3-Tier 비교
- 오류 처리: 3-Tier 재시도, dead-letter

**제거 또는 참조로 대체:**
- Pipeline D (MappingFeatures) → "04.graphrag Phase 3 참조"
- Pipeline E (Serving API) → "04.graphrag Phase 1 참조"
- GCP 인프라 상세 → "03.ml_pipeline 참조" 또는 "04.graphrag 참조"
- 27주 실행 계획 → "04.graphrag 참조"
- 운영/모니터링 → "04.graphrag 06_cost_and_monitoring.md 참조"

---

## 과도 #2: Pipeline E (Agent Serving API) — 추출 문서 범위 초과

### 현황

01_extraction_pipeline.md §7에 8개 REST API 엔드포인트 정의.
이는 "추출 파이프라인"이 아니라 "서빙 레이어"로, GraphRAG Core v2에서 이미 동일한 명세를 제공.

### 권고

v10에서 제거. "서빙 API는 04.graphrag/results/implement_planning/core/2/00_overview.md §13 참조" 한 줄로 대체.

---

## 과도 #3: 03_execution_plan.md 전체 — 범위 초과

### 현황

27주 실행 계획(11개 섹션, 623줄)이 GraphRAG Core v2의 Phase별 문서(6개 문서)와 거의 동일한 내용을 담고 있다.

### 차이점 (v10만의 고유 내용)

- v9 → v10 타임라인 비교 (§10): 유용하나 00_changelog.md에 포함 가능
- 테스트 전략 (§11): GraphRAG v2에는 명시적 테스트 전략이 없어 유용

### 권고

- §10 (타임라인 비교)은 00_changelog.md로 이동
- §11 (테스트 전략)은 별도 문서 또는 04.graphrag에 추가
- 나머지는 "04.graphrag 참조"로 대체

---

## 과도 #4: 05_operations_and_monitoring.md — 추출 문서 범위 초과

### 현황

운영/모니터링 문서(230줄)는 KG 추출 파이프라인 자체가 아니라 **전체 시스템 운영**에 관한 것.
증분 처리, 크롤링 운영, 백업, 프롬프트 버전 관리, 보안, 핸드오프 등은 GraphRAG Core v2의 06_cost_and_monitoring.md + Phase 4 문서와 중복.

### v10만의 고유 내용

- 프롬프트 버전 관리 절차 (§5): 유용. 추출 로직에 고유한 운영 사항
- Secret 로테이션 (§7.3): 인프라 영역이나 필요 정보

### 권고

프롬프트 버전 관리(§5)만 v10에 유지. 나머지는 04.graphrag 참조.

---

## 과도 #5: compute_skill_overlap() 내 FAISS 언급 — 시기상조

### 현황

```python
# v10 R-1: 현재 brute-force O(n×m). canonical ~2,800개 수준에서는 문제없으나,
# 유니크 스킬 수만 개 시 FAISS IndexFlatIP로 전환 (구현 10줄, Phase 2 성능 이슈 시)
```

canonical 2,800개 × vacancy_skills ~20개 = ~56K 비교. brute-force로 <1ms. FAISS 전환은 불필요한 미래 최적화.

### 권고

주석 제거 또는 "성능 이슈 발생 시 FAISS 검토" 한 줄로 축소. 현재 규모에서는 관련 없음.

---

## 과도 설계 종합

| # | 항목 | 심각도 | 조치 |
|---|------|--------|------|
| 1 | GraphRAG Core v2 중복 | Critical | 범위 한정, 참조로 대체 |
| 2 | Serving API | Medium | 제거, GraphRAG 참조 |
| 3 | 27주 실행 계획 | Medium | 고유 부분만 유지, 나머지 참조 |
| 4 | 운영/모니터링 | Medium | 프롬프트 관리만 유지 |
| 5 | FAISS 언급 | Low | 주석 축소 |
