# v10 조치 사항 및 권고

> 리뷰 결과를 기반으로 한 구체적 조치 사항

---

## 1. 즉시 조치 (v10 확정 전)

### A1. 문서 범위 재정의 (Critical)

**문제**: v10이 추출 로직 + 인프라 + 매칭 + 서빙 + 운영을 모두 포함하여 GraphRAG Core v2와 80% 중복.

**조치**:
- v10 범위를 **Pipeline A/B/B'/C + 오류 처리 + 프롬프트 설계**로 한정
- Pipeline D(MappingFeatures), E(Serving API)는 "04.graphrag 참조"로 대체
- 03_execution_plan.md는 v10 고유 내용(테스트 전략, v9→v10 비교)만 유지
- 05_operations_and_monitoring.md는 프롬프트 버전 관리(§5)만 유지

**대안**: 범위 재정의가 어려우면, v10을 "04.graphrag의 상세 구현 참조 문서"로 명시적 위상 부여하고, GraphRAG Core v2를 canonical로 선언.

### A2. 관계명 통일 (Critical)

**문제**: v10은 PERFORMED_ROLE/OCCURRED_AT, GraphRAG Core v2는 HAD_ROLE/AT_COMPANY.

**조치**: v19 온톨로지를 canonical로 하여 양쪽 통일. 04.graphrag 문서 업데이트.

### A3. Embedding 비용 불일치 수정 (Medium)

**문제**: 01_extraction_pipeline.md §9.2 Embedding $37.5 vs 02_model_and_infrastructure.md §2.2 $25.5.

**조치**: text-embedding-005 기준 $25.5로 통일. §9.2 수정.

---

## 2. v10 보강 (Phase 0 시작 전)

### B1. LLM 프롬프트 설계 문서 추가 (Critical)

**산출물**: `06_prompt_design.md` (신규)

포함 내용:
- CompanyContext 추출 프롬프트 (system prompt + user prompt + JSON schema)
- CandidateContext 추출 프롬프트 (동일)
- scope_type 분류 가이드라인 + few-shot 예시
- outcome 추출 가이드라인 + few-shot 예시
- situational_signal 14개 라벨 분류 기준
- temperature, max_tokens 등 LLM 파라미터

### B2. Pydantic 스키마 정의 (High)

**산출물**: 프롬프트 설계 문서 내 또는 별도 `07_schema_definitions.md`

포함 내용:
- CandidateContext JSON 스키마 (Pydantic v2)
- CompanyContext JSON 스키마
- Chapter, Outcome, SituationalSignal 세부 구조
- LLM 출력 → Pydantic 검증 → 3-Tier 재시도 흐름

### B3. PII 마스킹 전략 상세화 (High)

**산출물**: `08_pii_strategy.md` 또는 01_extraction_pipeline.md에 섹션 추가

포함 내용:
- 대상 PII 필드 목록 (이름, 전화번호, 주소, 이메일, 주민번호 등)
- 마스킹 방식 (비가역 해시 vs 가역 토큰)
- LLM 전송 범위 vs Graph 적재 범위
- 파일 이력서 PII 탐지 방법

---

## 3. Phase 0에서 검증 필요

### C1. Neo4j AuraDB Professional 노드 한도

v10에서 "800K+"라고 했지만 8M 노드 + 25M 엣지를 수용하는지 정확히 확인.
**불가 시**: AuraDB Enterprise 또는 자체 호스팅 Neo4j Community Edition (비용 재계산).

### C2. Anthropic Batch API 동시 활성 배치 수

10 동시 배치 미만이면 Phase 2 일정 초과. Gemini Flash 병행 비율 결정.

### C3. text-embedding-005 한국어 분별력

실패 시 Cohere embed-multilingual-v3.0 (1024d) 전환 → Neo4j Vector Index 차원 변경.
**Phase 0에서 Neo4j Vector Index 생성은 임베딩 모델 확정 후로 순서 조정 권고.**

### C4. resume-hub Career.BRN 존재 여부

Organization ER의 핵심 전제. BRN 필드가 resume-hub에 없으면 NICE 역매칭 전략 필요.

### C5. Phase 0 일정 1주 → 2주 조정 검토

50건 Gold Set 수동 작성 + LLM PoC 반복 설계를 1주에 완료하기 어려움.
GraphRAG Core v2도 동일하게 1주이므로, **양쪽 모두 2주로 조정 권고**.

---

## 4. 04.graphrag 구현 계획에 반영 필요

### D1. v10 고유 내용 중 GraphRAG Core v2에 없는 것

| v10 고유 내용 | GraphRAG Core v2 현황 | 반영 권고 |
|-------------|---------------------|----------|
| 테스트 전략 (03 §11) | 테스트 언급만, 전략 없음 | Phase별 테스트 기준 추가 |
| 프롬프트 버전 관리 (05 §5) | 미언급 | Phase 1부터 적용 |
| v9→v10 비교표 | 해당 없음 | 변경 이력으로 유지 |
| 비용 시나리오 4종 (01 §9.4) | 단일 시나리오 | 복수 시나리오 추가 검토 |

### D2. 매칭 함수 상세 설계 (Phase 3 시작 전)

vacancy_fit, domain_fit, culture_fit, role_fit 4개 함수의 구체적 계산 로직.
이것은 04.graphrag Phase 3 매칭 알고리즘 설계(Week 16, 2일)에서 다뤄야 하지만, v10에서도 "추출 시 어떤 필드가 매칭에 사용되는지" 매핑 테이블 필요.

---

## 5. 우선순위 요약

| 우선순위 | 조치 | 담당 | 시기 |
|---------|------|------|------|
| P0 | A1. 문서 범위 재정의 | 공동 | 즉시 |
| P0 | A2. 관계명 통일 | 공동 | 즉시 |
| P1 | B1. 프롬프트 설계 | MLE | Phase 0 전 |
| P1 | B2. Pydantic 스키마 | MLE | Phase 0 전 |
| P1 | B3. PII 마스킹 전략 | 공동 | Phase 0 전 |
| P1 | A3. Embedding 비용 수정 | 누구나 | 즉시 |
| P2 | C1-C5 검증 | Phase 0 | Phase 0 |
| P2 | D1. 테스트 전략 반영 | 공동 | Phase 1 전 |
| P3 | D2. 매칭 함수 설계 | MLE | Phase 3 전 |

---

## 6. 결론

v10은 v9에서 큰 폭의 개선을 이루었다. 온톨로지 v19 반영, GCP 인프라 통합, GraphRAG Core v2 정합 모두 올바른 방향이다.

그러나 **문서의 정체성 혼란**(추출 로직 vs 전체 구현 계획)이 가장 큰 문제이며, 이를 해소하지 않으면 04.graphrag와의 이중 관리 부담 + 불일치 누적이 불가피하다.

**핵심 권고**: v10은 "추출 로직"에 집중하고, 프롬프트 설계/Pydantic 스키마/PII 전략 등 **구현에 직접 필요한 세부사항**을 보강하라. 실행 계획/인프라/서빙/운영은 04.graphrag에 위임하라.
