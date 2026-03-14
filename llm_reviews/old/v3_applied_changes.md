# v3 리뷰 반영 Changelog

> **리뷰 원본**: `llm_reviews/v3.md`
> **반영일**: 2026-03-13
> **대상 버전 변경**: `01.ontology/v21→v22`, `02.knowledge_graph/v14→v15`, `03.graphrag/separate/v4→v5`

---

## 요약

v3.md 리뷰에서 식별된 CRITICAL/HIGH/MEDIUM/LOW 항목 중 **22건**을 3개 디렉토리에 걸쳐 15개 파일에 반영하였다.

| 심각도 | 반영 | 보류 | 사유 |
|--------|------|------|------|
| CRITICAL | 3 | 0 | — |
| HIGH | 7 | 0 | — |
| MEDIUM | 8 | 0 | — |
| LOW | 4 | 1 | L2(코드 주석 한/영 혼용)는 주관적이며 변경 범위 과대 |

---

## CRITICAL

### C1. 규모 추정 듀얼 시나리오 병기
- **파일**: `02.knowledge_graph/v15/01_extraction_pipeline.md`
- **내용**: §5.5 규모 추정표에 600K(v1 초기) vs 3.2M(전체 풀) 듀얼 시나리오 테이블 추가. 각 시나리오별 노드/엣지 수, Neo4j 티어 권장사항 병기
- **리뷰 근거**: 01(600K 기준)과 03(3.2M 기준)이 서로 다른 가정을 사용하며 명시적 연결 부재

### C2. 06_graphrag_cost.md 비용 테이블 서식 수정
- **파일**: `03.graphrag/separate/v5/graphrag/06_graphrag_cost.md`
- **내용**: 전체 비용 테이블에서 12건 이상의 누락된 틸데(~) 복원. `$68123` → `$68~123`, `$248473` → `$248~473` 등
- **리뷰 근거**: 마크다운 렌더링 시 범위 값이 깨져 단일 숫자로 표시

### C3. SituationalSignal 공유 노드 재분류
- **파일**: `02.knowledge_graph/v15/05_extraction_operations.md`
- **내용**: SituationalSignal을 비공유→공유 노드로 재분류. 04_graph_schema.md의 정의(14개 고정 taxonomy)와 일치. Cypher 스크립트에서 Step 2에 SituationalSignal 관계 제거 추가, 분류 테이블 수정
- **리뷰 근거**: 04_graph_schema에서는 공유 노드로 설계되어 있으나 05_extraction_operations에서 비공유로 분류

---

## HIGH

### H1. 매칭 알고리즘 구현 참조 노트
- **파일**: `03.graphrag/separate/v5/graphrag/04_graphrag_g3_matching.md`
- **내용**: `compute_match_score()` 코드 블록 상단에 "v1 MVP 간소화 구현"임을 명시하는 참조 노트 추가. 01.ontology 정본과의 차이점(F2, F3) 및 Phase 3 교체 계획 문서화
- **리뷰 근거**: 01과 03에 동일 알고리즘의 다른 버전이 존재하며 정본 관계 불명확

### H2. MAPPED_TO 엣지 방향 수정
- **파일**: `02.knowledge_graph/v15/01_extraction_pipeline.md`
- **내용**: `Person → Vacancy` → `Vacancy → Person`으로 수정. 04_graph_schema.md의 정의와 일치
- **리뷰 근거**: 01의 엣지 방향이 그래프 스키마 정의와 반대

### H3. 09_evaluation.md 임베딩 모델 수정
- **파일**: `03.graphrag/separate/v5/graphrag/09_evaluation.md`
- **내용**: docstring 내 `text-multilingual-embedding-002` → `text-embedding-005`로 수정. 768d 차원 명시
- **리뷰 근거**: 프로덕션 파이프라인(text-embedding-005)과 평가 파이프라인의 모델 불일치

### H4. freshness_weight smooth 모드 서빙 전파
- **파일**: `03.graphrag/separate/v5/graphrag/08_serving.md`
- **내용**: freshness_weight 적용 규칙에 "v1은 step 모드, smooth 모드 전환 시 전체 재계산 필요" 노트 추가
- **리뷰 근거**: 00_data_source_mapping에 듀얼 모드가 정의되었으나 서빙 레이어에 미전파

### H5. low_confidence_flag 정책 추가
- **파일**: `01.ontology/v22/03_mapping_features.md`
- **내용**: 활성 피처 ≤2개일 때 `low_confidence_flag = true` 설정 정책 추가. 가중치 재분배 시 과적합 리스크 경고
- **리뷰 근거**: culture_fit INACTIVE 시 4피처 재분배는 검증되었으나, 추가 피처 비활성화 시 가중치 집중 문제 미분석

### H6. F2 vacancy_fit confidence 분포 테이블
- **파일**: `01.ontology/v22/03_mapping_features.md`
- **내용**: CareerDescription 귀속 감쇠(0.6x/0.5x)가 F2 confidence에 미치는 영향 분포 테이블 추가
- **리뷰 근거**: 02에서 정의된 감쇠율이 피처 confidence에 어떻게 전파되는지 미문서화

### H7. LLM 비용 듀얼 시나리오
- **파일**: `03.graphrag/separate/v5/interface/implementation_roadmap.md`
- **내용**: Gemini Flash 기준 비용(~$484) 외에 Claude Haiku 시나리오(~$1,700~2,000, 4-5x 차이) 추가. Phase 0 모델 선정에 따른 비용 변동 노트
- **리뷰 근거**: 02에서는 Claude Haiku를, interface에서는 Gemini Flash를 가정하여 비용 추정 불일치

---

## MEDIUM

### M1. smooth 함수 ln(2) 근사값 수정
- **파일**: `01.ontology/v22/00_data_source_mapping.md`
- **내용**: `0.693` 하드코딩 → `math.log(2)` 정확값으로 교체. 코멘트에 ln(2) 명시
- **리뷰 근거**: 하드코딩된 근사값은 유지보수 시 의미 파악 어려움

### M2. REPLACE 공고 Phase 0 검증 구체화
- **파일**: `01.ontology/v22/03_mapping_features.md`
- **내용**: REPLACE 공고에 대한 Phase 0 검증을 "분포 모니터링"에서 "전임자 컨텍스트 가용 여부 확인 + 미가용 시 폴백 전략"으로 구체화
- **리뷰 근거**: REPLACE 매칭 전략이 "미완"으로만 표시되어 있어 Phase 0 액션이 불분명

### M3. Gold Set W22 확장 포인트
- **파일**: `03.graphrag/separate/v5/interface/01_go_nogo_decisions.md`
- **내용**: Gold Set 50건→100건 확장 시점(W22)과 확장 기준 추가
- **리뷰 근거**: 09_evaluation(100건)과 01_go_nogo(50건) 간 Gold Set 규모 불일치

### M4. PastCompanyContext confidence 계산 규칙
- **파일**: `01.ontology/v22/02_candidate_context.md`
- **내용**: `source_ceiling(0.70) × temporal_decay(0.63) = 0.44` 계산 과정을 명시적으로 문서화
- **리뷰 근거**: 0.44라는 수치가 어떻게 도출되었는지 설명 부재

### M5. FOUNDER 매핑 수정
- **파일**: `02.knowledge_graph/v15/03_prompt_design.md`
- **내용**: A1 scope_type 매핑에서 `FOUNDER → C_LEVEL`을 `FOUNDER → LEAD/HEAD`로 수정. 02_candidate_context.md의 정의와 일치
- **리뷰 근거**: 01의 scope_type 정의에서 C_LEVEL과 FOUNDER는 별개 카테고리

### M6. Top-5→Top-10 추출 수정
- **파일**: `03.graphrag/separate/v5/graphrag/09_evaluation.md`
- **내용**: 데이터 흐름도에서 "Top-5"를 "Top-10 → Top-5 추출"로 수정. 실제 평가 파이프라인 단계 반영
- **리뷰 근거**: 흐름도가 중간 단계(Top-10 후보군)를 생략하여 파이프라인 이해 혼란

### M7. Unknown Organization 영향 분석
- **파일**: `02.knowledge_graph/v15/07_data_quality.md`
- **내용**: 새 §6 "Unknown Organization 영향 분석" 추가. ~16% 미확인 기업이 F1 stage_match, F3 domain_fit에 미치는 영향과 완화 전략(기본값 할당, confidence 감쇠) 문서화
- **리뷰 근거**: BRN 부재 40% × fuzzy match 실패 40% = ~16% 미확인 기업의 그래프 품질 영향 미분석

### M8. Phase 0→1 Go/No-Go 테이블 분리
- **파일**: `03.graphrag/separate/v5/interface/01_go_nogo_decisions.md`
- **내용**: Phase 0→1 판정 테이블을 "W0 선행 결정"과 "W1 D5 판정" 두 시점으로 분리
- **리뷰 근거**: 선행 결정(PII, Neo4j 티어)과 Phase 내 판정이 하나의 테이블에 혼재

---

## LOW

### L1. 문서 참조 경로 갱신 (5개 파일)
- **파일**: `01.ontology/v22/` 전체 (00~04)
- **내용**: `v13` → `v15`, `v3` → `v5` 등 stale 버전 참조를 현재 버전으로 갱신
- **리뷰 근거**: 문서 간 참조가 이전 버전을 가리키고 있어 추적 혼란

### L3. extraction_method 열거값 수정
- **파일**: `01.ontology/v22/01_company_context.md`
- **내용**: `extraction_method` 예시에서 `"llm_gpt4o"` → `"llm"` (프로바이더 비종속)으로 수정
- **리뷰 근거**: 특정 모델명이 열거값에 하드코딩되면 모델 전환 시 스키마 변경 필요

### L4. 전화번호 정규식 word boundary 추가
- **파일**: `02.knowledge_graph/v15/04_pii_and_validation.md`
- **내용**: 전화번호 정규식에 `\b` word boundary 추가. "1024×768" 등 해상도 문자열의 오탐 방지
- **리뷰 근거**: 기존 정규식이 일부 정상 문자열을 전화번호로 오탐

### L5. 비용 테이블 VG4 대비 차이 수정
- **파일**: `03.graphrag/separate/v5/graphrag/06_graphrag_cost.md`
- **내용**: C2와 동일 — 비용 범위값의 틸데(~) 누락 수정으로 VG4 대비 계산이 정상 렌더링
- **리뷰 근거**: 서식 오류로 인해 차이 계산 테이블도 동일하게 깨짐

---

## 보류

### L2. 코드 주석 한/영 혼용 일관성
- **사유**: 변경 대상 파일이 광범위하고, 한/영 혼용이 실제 이해에 큰 장애를 주지 않음. 주관적 스타일 판단이므로 보류
