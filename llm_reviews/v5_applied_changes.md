# v5 리뷰 반영 Changelog

> **리뷰 원본**: `llm_reviews/v5.md`
> **반영일**: 2026-03-14
> **대상 버전 변경**: `01.ontology/v23→v24`, `02.knowledge_graph/v16→v17`, `03.graphrag/separate/v6→v7`

---

## 요약

v5.md 리뷰에서 식별된 CRITICAL/HIGH/MEDIUM/LOW 항목 중 **22건**을 3개 디렉토리에 걸쳐 반영하였다.

| 심각도 | 반영 | 보류 | 사유 |
|--------|------|------|------|
| CRITICAL | 3 | 0 | — |
| HIGH | 7 | 0 | — |
| MEDIUM | 8 | 0 | — |
| LOW | 4 | 0 | — |

---

## CRITICAL

### C1. Seniority enum 3계층 통일
- **파일**: `02.knowledge_graph/v17/03_prompt_design.md`
- **내용**: seniority Literal enum을 `["JUNIOR", "SENIOR", "LEAD", "HEAD", "C_LEVEL"]` → `["JUNIOR", "MID", "SENIOR", "LEAD", "HEAD", "UNKNOWN"]`으로 변경. MID 추가, C_LEVEL 제거. System Prompt RULES에 seniority 분류 기준 추가
- **리뷰 근거**: 정본(01.ontology)은 MID 포함 6개값, 추출 스키마(02.knowledge_graph)는 C_LEVEL 포함 5개값으로 불일치

### C2. experiences 정렬 규약 오름차순 통일
- **파일**: `01.ontology/v24/02_candidate_context.md`
- **내용**: §2.8 정렬 규약을 "시간 역순(최근→과거)" → "오름차순(과거→최근)"으로 변경. SQL을 `ORDER BY period.started_on ASC`로 수정. `get_candidate_seniority()`의 `experiences[0]` → `experiences[-1]`로 수정
- **리뷰 근거**: Data Contract, F5, Pipeline 모두 오름차순 가정인데 정본만 역순 정의

### C3. Data Contract stage_label "ENTERPRISE" 수정
- **파일**: `03.graphrag/separate/v7/interface/00_data_contract.md`
- **내용**: `"org_stage": "ENTERPRISE"` → `"org_stage": "MATURE"`로 수정. 유효 stage_label taxonomy 노트 추가
- **리뷰 근거**: 정본 taxonomy에 ENTERPRISE가 존재하지 않음

---

## HIGH

### H1. F5 Confidence 전파 규칙 ↔ 코드 통일
- **파일**: `01.ontology/v24/03_mapping_features.md`
- **내용**: F5 confidence 계산을 `min(0.70, role_evo.confidence)` → `min(vacancy.seniority_confidence ∥ 0.70, role_evo.confidence)`로 변경. Confidence 전파 규칙 테이블도 동일하게 갱신
- **리뷰 근거**: 전파 규칙 테이블은 "양쪽 소스 최소값"이나 코드는 0.70 하드코딩

### H2. F4 ALIGNMENT_LOGIC 불완전 상태 표기
- **파일**: `01.ontology/v24/03_mapping_features.md`
- **내용**: `# ...` 주석을 21개 미정의 조합에 대한 명시적 설명으로 교체. v2 활성화 전까지 기본값 0.5 fallback 정책 문서화
- **리뷰 근거**: 27개 조합 중 6개만 정의, 나머지 생략 표기로 상태 불명확

### H3. BigQuery ranking_score/freshness_weight 컬럼 추가
- **파일**: `03.graphrag/separate/v7/graphrag/08_serving.md`
- **내용**: mapping_features 테이블에 `ranking_score FLOAT64`, `freshness_weight FLOAT64`, `low_confidence_flag BOOLEAN` 컬럼 추가
- **리뷰 근거**: §1에서 ranking_score 저장을 명시하나 스키마에 해당 컬럼 부재

### H4. hiring_context_scope → vacancy_seniority 필드명 통일
- **파일**: `03.graphrag/separate/v7/interface/00_data_contract.md`
- **내용**: `"hiring_context_scope": "LEAD"` → `"vacancy_seniority": "SENIOR"`로 변경. 정본의 vacancy.seniority 필드와 통일
- **리뷰 근거**: hiring_context_scope가 01.ontology 어디에도 정의되지 않은 필드

### H5. 04_graphrag F2 간소화 구현 한계 명시
- **파일**: `03.graphrag/separate/v7/graphrag/04_graphrag_g3_matching.md`
- **내용**: F2 간소화 구현이 서로 다른 enum 공간(scope_type vs seniority)을 비교하는 문제 명시. vacancy_seniority 필드명으로 갱신
- **리뷰 근거**: scope_type과 hiring_context_scope의 enum 공간 불일치로 비교가 의미 없음

### H6. 05_evaluation_strategy v3 참조 미갱신
- **파일**: `03.graphrag/separate/v7/graphrag/09_evaluation.md`
- **내용**: 교차 참조 갱신에서 처리 (v23→v24)

### H7. VACANCY_SIGNAL_ALIGNMENT 시그널 커버리지 보강
- **파일**: `01.ontology/v24/03_mapping_features.md`
- **내용**: GLOBAL_EXPANSION을 BUILD_NEW/SCALE_EXISTING의 moderate에, MONETIZATION을 SCALE_EXISTING의 weak에 추가. 14개 taxonomy 전체 배정 확인 노트 추가
- **리뷰 근거**: GLOBAL_EXPANSION, MONETIZATION이 어떤 hiring_context에도 매핑되지 않음

---

## MEDIUM

### M1. experience_id ↔ chapter_id 형식 통일
- **파일**: `01.ontology/v24/02_candidate_context.md`
- **내용**: experience_id 주석을 `{person_id}_ch{idx}` 형식으로 변경. JSON 예시의 `"cand_99999_exp_01"` → `"P_99999_ch0"`으로 수정
- **리뷰 근거**: 동일 엔티티의 ID 형식이 3곳에서 상이

### M2. F3 embed() 함수 모델 명시
- **파일**: `01.ontology/v24/03_mapping_features.md`
- **내용**: `embed()` 호출 상단에 `text-embedding-005 (Vertex AI, 768d)` 주석 추가
- **리뷰 근거**: 어떤 임베딩 모델을 사용하는지 명시 없음

### M3. 08_serving SQL ranking_score 기반으로 수정
- **파일**: `03.graphrag/separate/v7/graphrag/08_serving.md`
- **내용**: SQL 예시의 `ORDER BY mf.overall_match_score * mf.avg_confidence DESC` → `ORDER BY mf.ranking_score DESC`로 변경
- **리뷰 근거**: §1에서 정의한 ranking_score를 SQL에서 미사용

### M4. SituationalSignal category "tech_change" → "tech" 통일
- **파일**: `01.ontology/v24/04_graph_schema.md`
- **내용**: category 열거값 주석을 `"tech_change"` → `"tech"`로 변경, `"other"` 추가
- **리뷰 근거**: Graph Schema는 "tech_change", 초기화 Cypher는 "tech"로 불일치

### M5. README.md / CLAUDE.md 버전 갱신
- **파일**: `README.md`, `CLAUDE.md`
- **내용**: 현재 유효 버전을 `v20/v13/separate/v3` → `v24/v17/separate/v7`로 갱신
- **리뷰 근거**: v3 리뷰 이후 3번의 버전 업데이트를 거치면서 갱신 누락

### M6. JSON 스키마 버전 규약 문서화
- **파일**: `01.ontology/v24/02_candidate_context.md`
- **내용**: `$schema` 값(`CandidateContext_v4`)이 온톨로지 버전(v24)과 독립적인 JSON 스키마 자체의 메이저 버전임을 명시
- **리뷰 근거**: 스키마 버전과 디렉토리 버전의 관계가 불명확

### M7. 06_normalization.md / 07_data_quality.md v20 참조 갱신
- **파일**: `02.knowledge_graph/v17/06_normalization.md`, `07_data_quality.md`
- **내용**: `v20/` → `v24/` 참조 수정
- **리뷰 근거**: 온톨로지 참조 버전이 미갱신

### M8. Outcome 추출 비율 산술 수정
- **파일**: `01.ontology/v24/03_mapping_features.md`
- **내용**: F2 confidence 분포 테이블의 "SelfIntroduction only" 비율을 47.2% → 53.3%, "둘 다 미보유"를 35.9% → 29.8%로 수정. 산출식 노트 추가
- **리뷰 근거**: (100%-16.9%) × 64.1% = 53.3%이나 47.2%로 오기재

---

## LOW

### L1. FACET_TO_WORKSTYLE 설계 의도 노트 추가
- **파일**: `01.ontology/v24/03_mapping_features.md`
- **내용**: speed/autonomy가 동일 work_style 필드에 매핑되는 설계 의도와 v2 분리 검토 노트 추가
- **리뷰 근거**: 2개 facet이 같은 필드에 매핑되어 변별력 우려

### L2. Outcome evidence 단수→복수 통일
- **파일**: `01.ontology/v24/02_candidate_context.md`
- **내용**: Outcome 인터페이스의 `evidence: Evidence` → `evidence: Evidence[]`로 변경. JSON 예시도 배열 형태로 수정
- **리뷰 근거**: Experience의 evidence는 복수인데 Outcome만 단수

### L3. REPLACE Phase 0 중복 기재 통합
- **파일**: `01.ontology/v24/03_mapping_features.md`
- **내용**: [v21]과 [v22] 블록을 [v22][v24 통합] 단일 블록으로 병합. 비율 모니터링, 전용 피처, low_confidence_flag 정책을 일원화
- **리뷰 근거**: 동일 과제가 3곳에 중복 기재

### L4. SituationalSignal category에 "other" 추가
- **파일**: `01.ontology/v24/04_graph_schema.md`
- **내용**: category 주석에 `/ "other"` 추가 (M4와 함께 처리)
- **리뷰 근거**: OTHER 라벨의 category "other"가 스키마 정의에 누락

---

## 교차 참조 갱신 (버전 번호)

v24 내부에서 타 디렉토리 참조를 현재 버전으로 갱신:
- `01.ontology/v24/`: `v16/` → `v17/`, `v6/` → `v7/`
- `02.knowledge_graph/v17/`: `v23/` → `v24/`, `v6/` → `v7/`, `v20/` → `v24/`
- `03.graphrag/separate/v7/`: `v23/` → `v24/`, `v16/` → `v17/`, `v6/` → `v7/`
- `README.md`, `CLAUDE.md`: 현재 유효 버전 갱신
