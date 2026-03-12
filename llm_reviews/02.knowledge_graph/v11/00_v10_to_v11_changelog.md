# v10 → v11 변경 이력

> 작성일: 2026-03-11 | 리뷰 기반: v10 리뷰 (01_review_validity ~ 05_review_action_items)

---

## 1. 변경 동기

v10 리뷰에서 **문서 정체성 혼란**이 가장 큰 문제로 지적됨.
v10은 "Extraction Pipeline" 문서이면서 인프라/매칭/서빙/운영을 모두 포함하여
GraphRAG Core v2와 80% 이상 내용이 중복되고, 이미 불일치가 발생.

동시에, 추출 로직의 **핵심인 LLM 프롬프트 설계, Pydantic 스키마, PII 마스킹 전략이 전무**하여
문서의 존재 의의가 반감된 상태.

---

## 2. 핵심 변경 사항

### 2.1 문서 범위 재정의 (Critical → 해소)

v10은 5개 파이프라인(A/B/B'/C/D/E)을 모두 포함했으나,
v11은 **추출 로직(Pipeline A/B/B'/C)에 집중**.

| 범위 | v10 | v11 | 비고 |
|------|-----|-----|------|
| Pipeline A (CompanyContext) | 포함 | **포함** | 추출 로직 본연 |
| Pipeline B (CandidateContext DB) | 포함 | **포함** | 추출 로직 본연 |
| Pipeline B' (CandidateContext 파일) | 포함 | **포함** | 추출 로직 본연 |
| Pipeline C (Graph 적재) | 포함 | **포함** | 추출 로직 본연 |
| Pipeline D (MappingFeatures) | 포함 | **→ 참조** | 04.graphrag Phase 3 참조 |
| Pipeline E (Serving API) | 포함 | **→ 참조** | 04.graphrag Phase 1 참조 |
| GCP 인프라 상세 | 포함 | **→ 간소화** | 추출 관련 리소스만 유지 |
| 27주 실행 계획 | 포함 | **→ 참조** | 04.graphrag 참조, 테스트 전략만 유지 |
| 운영/모니터링 | 포함 | **→ 간소화** | 프롬프트 버전 관리 + 증분 처리만 유지 |

### 2.2 핵심 누락 보강

| 항목 | v10 | v11 | 문서 |
|------|-----|-----|------|
| LLM 프롬프트 설계 | **전무** | **추가** | 03_prompt_design.md |
| Pydantic 스키마 | **전무** | **추가** | 03_prompt_design.md 내 포함 |
| PII 마스킹 전략 | 1줄 언급 | **상세 설계** | 04_pii_and_validation.md |
| 파이프라인 내 검증 | 배치 후 체크만 | **단계별 체크포인트** | 04_pii_and_validation.md |
| 증분 처리 상세 | 유형만 정의 | **변경 감지/공유 노드 보호** | 05_extraction_operations.md |

### 2.3 내부 불일치 수정

| 항목 | v10 | v11 | 비고 |
|------|-----|-----|------|
| Embedding 비용 | 01문서 $37.5 / 02문서 $25.5 | **$25.5 통일** | text-embedding-005 기준 |
| 관계명 | PERFORMED_ROLE, OCCURRED_AT | **유지 (v19 canonical)** | GraphRAG Core v2 측 업데이트 권고 |
| FAISS 주석 | 불필요한 미래 최적화 | **제거** | 2,800 canonical에서 brute-force 충분 |

### 2.4 매칭 필드 매핑 테이블 추가

v10에서 매칭 함수(vacancy_fit, domain_fit 등) 미정의 지적에 대해,
v11은 함수 설계는 04.graphrag Phase 3에 위임하되,
**"추출 시 어떤 필드가 매칭에 사용되는지" 매핑 테이블**을 01_extraction_pipeline.md에 추가.

---

## 3. 문서 구조 변경

| v10 문서 | v11 문서 | 변경 |
|---------|---------|------|
| 00_v9_to_v10_changelog.md | 00_v10_to_v11_changelog.md (본 문서) | 변경 이력 갱신 |
| 01_extraction_pipeline.md | 01_extraction_pipeline.md | Pipeline D/E 제거, 매칭 필드 매핑 추가, 비용 수정 |
| 02_model_and_infrastructure.md | 02_model_and_infrastructure.md | 인프라 간소화 (추출 관련만), 비용 수정 |
| 03_execution_plan.md (623줄) | **→ 04.graphrag 참조** | 테스트 전략만 05에 이동 |
| 04_assumptions_and_risks.md | 03_assumptions_and_risks.md | 추출 로직 고유 리스크만 유지 |
| 05_operations_and_monitoring.md (231줄) | **→ 간소화** | 프롬프트 관리 + 증분 처리만 05에 이동 |
| (없음) | **03_prompt_design.md** | 신규: LLM 프롬프트 + Pydantic 스키마 |
| (없음) | **04_pii_and_validation.md** | 신규: PII 마스킹 + 검증 체크포인트 |
| (없음) | **05_extraction_operations.md** | 신규: 증분 처리 + 프롬프트 관리 + 테스트 전략 |

---

## 4. 삭제/이동된 내용 추적

| v10 내용 | v11 위치 | 이유 |
|---------|---------|------|
| §6 Pipeline D (MappingFeatures) | 04.graphrag Phase 3 참조 | 매칭은 추출 로직 범위 외 |
| §7 Pipeline E (Serving API) | 04.graphrag Phase 1 참조 | 서빙은 추출 로직 범위 외 |
| §10 모니터링 메트릭 (GraphRAG vs Vector) | 04.graphrag Phase 3 참조 | 실험은 추출 로직 범위 외 |
| 03_execution_plan.md 전체 | 04.graphrag 참조 | 실행 계획 중복 해소 |
| 05_operations_and_monitoring.md 대부분 | 04.graphrag 참조 | 운영 중복 해소 |
| 02 §4 GCP 인프라 상세 | 간소화 | 추출 관련 리소스만 유지 |
| 02 §5 ML Knowledge Distillation | 04.graphrag 참조 | Phase 2 선택적, 추출 범위 외 |
