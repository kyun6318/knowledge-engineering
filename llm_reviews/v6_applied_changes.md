# v6 리뷰 반영 Changelog

> **리뷰 원본**: `llm_reviews/v6.md`
> **반영일**: 2026-03-14
> **대상 버전 변경**: `01.ontology/v24→v25`, `02.knowledge_graph/v17→v18`, `03.graphrag/separate/v7→v8`

---

## 요약

v6.md 리뷰에서 식별된 CRITICAL/HIGH/MEDIUM/LOW 항목 중 **20건**을 3개 디렉토리에 걸쳐 반영하였다.

| 심각도 | 반영 | 보류 | 사유 |
|--------|------|------|------|
| CRITICAL | 4 | 0 | — |
| HIGH | 8 | 0 | — |
| MEDIUM | 8 | 0 | — |
| LOW | 4 | 0 | — |

---

## CRITICAL

### C1. Vacancy `seniority_confidence` 필드 추가
- **파일**: `01.ontology/v25/01_company_context.md`
- **내용**: vacancy 필드 정의 테이블에 `seniority_confidence: number` 행 추가. "JD에 직급이 명시되면 0.85, 추론 시 0.50~0.70" 설명 포함
- **리뷰 근거**: F5 role_fit 코드가 `vacancy.seniority_confidence`를 참조하나 정본에 필드 미정의

### C2. 05_evaluation_strategy.md 리다이렉트 버전 갱신
- **파일**: `01.ontology/v25/05_evaluation_strategy.md`
- **내용**: `separate/v3/` → `separate/v8/`로 수정
- **리뷰 근거**: graphrag 현재 버전은 v8이나 v3 참조 잔존

### C3. Data Contract Vacancy JSON 중복 필드 제거
- **파일**: `03.graphrag/separate/v8/interface/00_data_contract.md`
- **내용**: `"vacancy_seniority": "SENIOR"` 행 삭제, `"seniority"` 단일 필드로 통일. [v8] 주석으로 정본 필드명 명시
- **리뷰 근거**: seniority와 vacancy_seniority 두 필드가 동시 존재하여 정본 불명확

### C4. sf/04_sf_phase3_jd_company.md v5 반영 누락 수정
- **파일**: `03.graphrag/separate/v8/sf/04_sf_phase3_jd_company.md`
- **내용**: `"hiring_context_scope": "LEAD"` → `"seniority": "LEAD"`로 변경
- **리뷰 근거**: Data Contract 갱신 시 sf/ 디렉토리 JSON 예시 미갱신

---

## HIGH

### H1. candidate_id → person_id 통일
- **파일**: `01.ontology/v25/02_candidate_context.md`
- **내용**: JSON 예시의 `"candidate_id": "cand_99999"` → `"person_id": "P_99999"`로 변경. Graph Schema의 person_id와 일치
- **리뷰 근거**: candidate_id(cand_접두사)와 experience_id(P_접두사) 간 불일치

### H2. F5 "SENIOR_IC" 주석 수정
- **파일**: `01.ontology/v25/03_mapping_features.md`
- **내용**: `IC/SENIOR_IC/LEAD/HEAD/FOUNDER` → `IC/LEAD/HEAD/FOUNDER/UNKNOWN`으로 수정
- **리뷰 근거**: SENIOR_IC는 ScopeType enum에 존재하지 않는 값

### H3. SituationalSignal evidence 복수형 통일
- **파일**: `01.ontology/v25/02_candidate_context.md`
- **내용**: `evidence: Evidence;` → `evidence: Evidence[];`로 변경. JSON 예시도 배열 형태로 수정
- **리뷰 근거**: Outcome의 evidence는 복수(Evidence[])이나 SituationalSignal만 단수

### H4. OutcomeType "OTHER" Graph Schema 추가
- **파일**: `01.ontology/v25/04_graph_schema.md`
- **내용**: outcome_type 주석에 `/ "OTHER"` 추가 (5개값 완성)
- **리뷰 근거**: 정본(02_candidate_context.md)은 OTHER 포함 5개값, Graph Schema는 4개만 나열

### H5. org_stage → stage_label 필드명 통일
- **파일**: `03.graphrag/separate/v8/interface/00_data_contract.md`
- **내용**: `"org_stage": "MATURE"` → `"stage_label": "MATURE"`로 변경. 관련 [v7] 주석도 stage_label로 갱신
- **리뷰 근거**: 정본과 Neo4j 스키마는 stage_label, Data Contract만 org_stage 사용

### H6. compute_ranking_score() 함수 추가
- **파일**: `03.graphrag/separate/v8/graphrag/04_graphrag_g3_matching.md`
- **내용**: `compute_match_score()` 뒤에 `compute_ranking_score()` 함수 추가. `ranking_score = overall × freshness_weight` 산출 및 `low_confidence_flag` 판정 로직 포함
- **리뷰 근거**: 08_serving.md에 ranking_score 컬럼이 있으나 산출 코드 부재

### H7. F4 culture_fit v1 MVP 주석 추가
- **파일**: `03.graphrag/separate/v8/graphrag/04_graphrag_g3_matching.md`
- **내용**: `culture_score = 0.5` 위에 "[v8] v1 MVP: INACTIVE 기본값 0.5 포함, 정본의 가중치 재분배 정책과 차이, Phase 2에서 적용 예정" 주석 추가
- **리뷰 근거**: 정본은 INACTIVE → 가중치 재분배이나 간소화 구현은 0.5 고정

### H8. scope_type vs seniority 비교 로직 명확화
- **파일**: `03.graphrag/separate/v8/graphrag/04_graphrag_g3_matching.md`
- **내용**: `vacancy.get("vacancy_seniority")` → `vacancy.get("seniority")`로 변경 (C3 연계). enum 공간 불일치 설명 주석 추가
- **리뷰 근거**: scope_type(IC/LEAD/HEAD/FOUNDER)과 seniority(JUNIOR~HEAD)는 다른 enum 공간

---

## MEDIUM

### M1. ScopeType "UNKNOWN" Graph Schema 추가
- **파일**: `01.ontology/v25/04_graph_schema.md`
- **내용**: scope_type 주석에 `/ "UNKNOWN"` 추가 (5개값 완성)
- **리뷰 근거**: 정본은 UNKNOWN 포함 5개값, Graph Schema 주석은 4개만 나열

### M2. Outcome type → outcome_type 필드명 수정
- **파일**: `03.graphrag/separate/v8/interface/00_data_contract.md`
- **내용**: CandidateContext JSON 예시의 `"type": "SCALE"` → `"outcome_type": "SCALE"`
- **리뷰 근거**: 정본 Outcome 인터페이스는 `outcome_type` 필드명 사용

### M3. Chapter 노드 seniority 속성 제거
- **파일**: `02.knowledge_graph/v18/01_extraction_pipeline.md`
- **내용**: Chapter 노드 속성에서 `seniority` 제거, "scope_type (→ seniority 변환은 매칭 시점)" 주석으로 교체
- **리뷰 근거**: Graph Schema에서 Chapter는 scope_type만 보유, seniority는 Vacancy 속성

### M4. SituationalSignal taxonomy 참조 위치 수정
- **파일**: `02.knowledge_graph/v18/05_extraction_operations.md`
- **내용**: `04_graph_schema.md §1.7` → `01.ontology/v25/02_candidate_context.md §2.3 (taxonomy 정의) + 04_graph_schema.md §1.7 (노드 구조)` 이중 참조로 변경
- **리뷰 근거**: 14개 taxonomy 라벨은 02_candidate_context.md에 정의, 04_graph_schema.md는 노드 구조만

### M5. low_confidence_flag 교차 참조 추가
- **파일**: `03.graphrag/separate/v8/graphrag/08_serving.md`
- **내용**: low_confidence_flag 주석에 `(01.ontology/v25/03_mapping_features.md §4 판정 규칙)` 교차 링크 추가
- **리뷰 근거**: 주석만으로 판정 기준 불명확

### M6. Data Contract flat 필드 설계 의도 주석
- **파일**: `03.graphrag/separate/v8/interface/00_data_contract.md`
- **내용**: Vacancy JSON 뒤에 [v8] 주석 추가: "required_role 등은 정본에서 관계로 표현되나 Data Contract에서는 적재 편의를 위해 flat 필드로 제공, 적재 시 노드+관계로 분해"
- **리뷰 근거**: 정본 미정의 필드(required_role, needed_signals)의 존재 사유 불명확

### M7. graphrag 참조 버전 명시
- **파일**: `02.knowledge_graph/v18/02_model_and_infrastructure.md`
- **내용**: "04.graphrag를 참조" → `03.graphrag/separate/v8/graphrag/` 구체 경로로 변경
- **리뷰 근거**: 참조 대상 버전 미명시

### M8. Graceful Degradation confidence penalty 테이블 추가
- **파일**: `02.knowledge_graph/v18/07_data_quality.md`
- **내용**: [v18] Confidence Penalty 규약 테이블 추가 (1차→2차 소스: -0.10, DB→LLM: -0.05, 정규화→임베딩: -0.05~-0.15, 부재→기본값: -0.20)
- **리뷰 근거**: fallback 전략은 있으나 confidence 감쇠 수치 미기재

---

## LOW

### L1. ROLE_PATTERN_FIT 기본값 주석 추가
- **파일**: `01.ontology/v25/03_mapping_features.md`
- **내용**: `# ...` → `# [v25] 미정의 조합은 기본값 0.50 반환 (.get() fallback)`으로 교체
- **리뷰 근거**: 미완성 표기(`# ...`)를 명시적 기본값 설명으로 전환

### L2. "v3 표현" 컬럼 설명 추가
- **파일**: `01.ontology/v25/01_company_context.md`
- **내용**: hiring_context 테이블 뒤에 `[v25] "v3 표현"은 초기 설계 단계(온톨로지 v3)에서 사용한 약식 표기로, 역사적 맥락으로만 참조한다` 주석 추가
- **리뷰 근거**: "v3"가 무엇을 지칭하는지 설명 없음

### L3. 구 버전 태그 정리 (선택적)
- **파일**: `02.knowledge_graph/v18/` 다수 파일
- **내용**: `[v14]` → `[v14→v18 유지]`, `[v12 D5]` → `[v12 D5→v18 유지]` 등 유효성 표시 추가 (총 6건)
- **리뷰 근거**: 구 버전 태그의 현재 유효성 불명확

### L4. F1 피처 참조 교차 링크 전환
- **파일**: `02.knowledge_graph/v18/07_data_quality.md`
- **내용**: `F1 stage_match` → `F1 stage_match (→ 01.ontology/v25/03_mapping_features.md F1 참조)` 형태로 변경
- **리뷰 근거**: 02 레이어에서 피처 직접 정의 → 교차 참조로 전환 (3-Layer 분리 원칙)

---

## 교차 참조 갱신 (버전 번호)

v25/v18/v8 내부에서 타 디렉토리 참조를 현재 버전으로 갱신:
- `01.ontology/v25/`: `v17/` → `v18/` (10건), `v7/` → `v8/` (8건)
- `02.knowledge_graph/v18/`: `v24/` → `v25/` (다수), `v7/` → `v8/` (4건)
- `03.graphrag/separate/v8/`: `v24/` → `v25/` (다수), `v17/` → `v18/` (다수)
- `README.md`, `CLAUDE.md`: 현재 유효 버전 v25/v18/separate/v8로 갱신
