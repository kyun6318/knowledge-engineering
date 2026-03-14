# v4 리뷰 반영 Changelog

> **리뷰 원본**: `llm_reviews/v4.md`
> **반영일**: 2026-03-14
> **대상 버전 변경**: `01.ontology/v22→v23`, `02.knowledge_graph/v15→v16`, `03.graphrag/separate/v5→v6`

---

## 요약

v4.md 리뷰에서 식별된 CRITICAL/HIGH/MEDIUM/LOW 항목 중 **21건**을 3개 디렉토리에 걸쳐 12개 파일에 반영하였다.

| 심각도 | 반영 | 보류 | 사유 |
|--------|------|------|------|
| CRITICAL | 3 | 0 | — |
| HIGH | 6 | 0 | — |
| MEDIUM | 8 | 0 | — |
| LOW | 4 | 0 | — |

---

## CRITICAL

### C1. F1 `best_match_pcc_confidence` 미정의 변수 수정
- **파일**: `01.ontology/v23/03_mapping_features.md`
- **내용**: `stage_experiences.append()` 딕셔너리에 `"pcc_confidence": pcc.confidence` 추가 (L91). `confidence = min(...)` 직전에 `best_match_pcc_confidence = best_match["pcc_confidence"]` 선언 추가 (L151)
- **리뷰 근거**: v7부터 v22까지 15개 버전에 걸쳐 미정의 변수가 잔존, 런타임 NameError 발생

### C2. SituationalSignal 열거값 불일치 수정 (2건)
- **파일**: `03.graphrag/separate/v6/interface/00_data_contract.md`, `03.graphrag/separate/v6/sf/04_sf_phase3_jd_company.md`
- **내용**: `SCALING_TEAM` → `TEAM_SCALING`, `GREENFIELD` → `NEW_SYSTEM_BUILD`로 전체 수정. Data Contract에 14개 유효 열거값 목록 추가
- **리뷰 근거**: 정본(01.ontology) taxonomy에 `SCALING_TEAM`, `GREENFIELD`가 존재하지 않음

### C3. operating_model 타입 불일치 수정
- **파일**: `03.graphrag/separate/v6/interface/00_data_contract.md`, `02.knowledge_graph/v16/03_prompt_design.md`
- **내용**: Data Contract의 operating_model을 string enum(`"FAST"`)에서 float(`0.8`)로 수정. Pydantic 스키마에 정본 타입(float) 확인 주석 추가. 이산형 변환 규칙(HIGH≥0.7, MID 0.3~0.7, LOW<0.3) 문서화
- **리뷰 근거**: v15 Pydantic은 float(0.0~1.0), v5 Data Contract은 string enum으로 타입 불일치

---

## HIGH

### H1. Industry 코드 계층 필드명 정의
- **파일**: `01.ontology/v23/03_mapping_features.md`, `01.ontology/v23/00_data_source_mapping.md`
- **내용**: F3 domain_fit 섹션에 code-hub INDUSTRY 3계층 매핑 테이블(1depth group_code, 2depth sub_code, 3depth code) 추가. `resolve_industry_code()`에 `lookup_common_code` 반환 필드 정의 주석 추가
- **리뷰 근거**: F3 코드에서 `sub_code` 참조하나 해당 필드가 어디에서도 정의되지 않음

### H2. chapter_id 생성 규격 추가
- **파일**: `02.knowledge_graph/v16/01_extraction_pipeline.md`
- **내용**: §3.2 직전에 `[v16] chapter_id 생성 규칙` 섹션 추가. `{person_id}_ch{idx}` 형식, period_start 오름차순 정렬 후 0-based 인덱스 규칙 명시
- **리뷰 근거**: GraphRAG Data Contract이 chapter_id 형식을 기대하나 추출 파이프라인에 생성 로직 부재

### H3. Vacancy seniority 추출 필드 추가
- **파일**: `02.knowledge_graph/v16/03_prompt_design.md`
- **내용**: CompanyContextExtraction Pydantic 스키마에 `seniority: Optional[Literal["JUNIOR", "SENIOR", "LEAD", "HEAD", "C_LEVEL"]]` 및 `seniority_confidence` 필드 추가
- **리뷰 근거**: Data Contract이 seniority를 요구하나 추출 스키마에 해당 필드 미존재

### H4. stage_label ↔ stage_estimate 명칭 연결
- **파일**: `02.knowledge_graph/v16/01_extraction_pipeline.md`
- **내용**: `rule_engine.estimate_stage()` 코드 블록 하단에 Neo4j 적재 시 필드 매핑 노트 추가: `Organization.stage_label = stage_estimate.stage_label`
- **리뷰 근거**: 추출(stage_estimate 객체)과 쿼리(stage_label 단순 문자열) 간 변환 규칙 미명시

### H5. Vector Index 속성명 통일
- **파일**: `02.knowledge_graph/v16/01_extraction_pipeline.md`
- **내용**: Vector Index 생성 코드의 `ON (c.embedding)` → `ON (c.evidence_chunk_embedding)`, `ON (v.embedding)` → `ON (v.evidence_chunk_embedding)`으로 수정. 03.graphrag v6의 명칭과 통일
- **리뷰 근거**: v15는 `embedding`, v5는 `evidence_chunk_embedding`으로 속성명 불일치

### H6. F2 "no matching signals" ACTIVE 설계 근거 문서화
- **파일**: `01.ontology/v23/03_mapping_features.md`
- **내용**: `else: return FeatureResult(score=0.15, ...)` 상단에 설계 근거 주석 8줄 추가. signals 부재(INACTIVE)와 매칭 불일치(ACTIVE 0.15)의 차이, 0.15 baseline 선정 논리 명시
- **리뷰 근거**: F1/F5는 데이터 부재 시 INACTIVE이나 F2만 ACTIVE 반환하여 논리 불일치

---

## MEDIUM

### M1. NEXT_CHAPTER 엣지 방향 명시
- **파일**: `01.ontology/v23/04_graph_schema.md`
- **내용**: NEXT_CHAPTER 엣지 정의 하단에 `[v23] 방향 규약` 블록쿼트 추가: "이전 Chapter → 이후 Chapter 방향, `(C_2019)-[:NEXT_CHAPTER]->(C_2021)`"
- **리뷰 근거**: 스키마 정의에 방향성 명시 없어 구현 시 혼란

### M2. Confidence 전파 규칙 추가
- **파일**: `01.ontology/v23/03_mapping_features.md`
- **내용**: F5 섹션 후, §3 앞에 `[v23] Confidence 전파 규칙` 서브섹션 추가. F1~F5 각 피처의 confidence 산출 규칙 테이블 및 "보수적 전파(최소값)" 원칙 명시
- **리뷰 근거**: 엣지 confidence와 피처 confidence의 관계가 미정의

### M3. Outcome 적재 의사결정 매트릭스 추가
- **파일**: `01.ontology/v23/03_mapping_features.md`
- **내용**: F2 Outcome 활용 방침 섹션에 CareerDesc/SelfIntro 보유 여부별 Outcome 추출·적재 의사결정 테이블 추가. 전체 추출 가능 비율 ~70.2% 산출
- **리뷰 근거**: Outcome 충전율 산식 미정의, Neo4j 적재 기준 불명확

### M4. freshness_weight v1 기본 모드 명시
- **파일**: `01.ontology/v23/00_data_source_mapping.md`
- **내용**: `compute_freshness_weight` 함수 내에 `[v23] v1 기본값: use_smooth = False (step 모드)` 명시. smooth 전환 조건(Top-10 순위 변동 10% 이상) 기록
- **리뷰 근거**: step vs smooth 듀얼 모드 설계이나 v1에서 어느 모드를 사용하는지 명시적 선언 부재

### M5. experiences 배열 정렬 규약 통일
- **파일**: `01.ontology/v23/03_mapping_features.md`, `03.graphrag/separate/v6/interface/00_data_contract.md`
- **내용**: F5 코드의 `experiences[0]` → `experiences[-1]`로 수정 (period_start 오름차순 정렬이므로 마지막이 최신). Data Contract에 `chapters[0]=oldest, chapters[-1]=latest` 명시 추가
- **리뷰 근거**: Data Contract은 오름차순, F5는 `[0]=latest` 가정으로 불일치

### M6. NEEDS_SIGNAL 생성 방법 Layer 2에 추가
- **파일**: `02.knowledge_graph/v16/01_extraction_pipeline.md`
- **내용**: Pipeline A 섹션에 `[v16] 2.5 NEEDS_SIGNAL 관계 생성` 추가. Rule 기반(HIRING_CONTEXT_TO_SIGNALS) + LLM 기반 2-Track 병행 전략, Phase 0 검증 기준(Precision≥0.70, Recall≥0.60) 명시
- **리뷰 근거**: v5에서 NEEDS_SIGNAL 추론이 정의되었으나 Layer 2에 해당 사양 부재

### M7. 비용 비교 파이프라인별 분리 설명 추가
- **파일**: `02.knowledge_graph/v16/01_extraction_pipeline.md`
- **내용**: CandidateContext 비용 테이블 하단에 `[v16] 비용 변동 상세` 노트 추가. 토큰 절감은 Pipeline A, 비용 증가는 Pipeline B에서 발생하여 방향이 반대인 점 명시
- **리뷰 근거**: 토큰 절감과 비용 증가가 동시에 기술되어 내부 모순으로 오해 가능

### M8. v14→v16, v20→v23 참조 갱신
- **파일**: `03.graphrag/separate/v6/graphrag/07_neo4j_schema.md`, `08_serving.md`, `09_evaluation.md`, `04_graphrag_g3_matching.md`
- **내용**: `v14/` → `v16/`, `v20/` → `v23/`, `v22/` → `v23/` 참조 일괄 갱신 (총 6건)
- **리뷰 근거**: v3 리뷰의 L1이 01.ontology에만 적용되고 03.graphrag 내 참조가 미갱신

---

## LOW

### L1. STAGE_SIMILARITY 매트릭스 초기값 표기
- **파일**: `01.ontology/v23/03_mapping_features.md`
- **내용**: 매트릭스 주석을 `[v7] [v1-PILOT]`로 변경, "전문가 판단 기반 초기값, Phase 0 파일럿 후 확정" 노트 추가
- **리뷰 근거**: 확정값과 초기값 구분이 어려움

### L2. gender/age 필드 분리 검토 노트
- **파일**: `01.ontology/v23/04_graph_schema.md`
- **내용**: Person 노드의 gender, age 필드에 `[v23: analytics 분리 검토]` 태그 추가. v2에서 별도 analytics 테이블 분리 검토 노트 추가
- **리뷰 근거**: 매칭 금지 필드가 메인 그래프에 저장되어 의도치 않은 사용 리스크

### L3. hiring_context UNKNOWN 사용 가이드
- **파일**: `02.knowledge_graph/v16/03_prompt_design.md`
- **내용**: CompanyContext System Prompt RULES에 "hiring context 판별 불가 시 UNKNOWN + confidence < 0.3" 가이드 추가
- **리뷰 근거**: UNKNOWN 열거값 존재하나 사용 조건 미정의

### L4. SituationalSignal 14개 사전 생성 스크립트
- **파일**: `03.graphrag/separate/v6/graphrag/01_graphrag_g0_setup.md`
- **내용**: `[v6] SituationalSignal 초기화` 섹션 추가. 14개 공유 노드를 MERGE로 사전 생성하는 Cypher 스크립트 포함. 카테고리(growth/org_change/tech/business/other) 자동 설정
- **리뷰 근거**: 공유 노드 설계이나 초기화 스크립트 부재

---

## 교차 참조 갱신 (버전 번호)

v23 내부에서 타 디렉토리 참조를 현재 버전으로 갱신:
- `01.ontology/v23/`: `v15/` → `v16/`, `v5/` → `v6/` (약 13건)
- `02.knowledge_graph/v16/`: `v5/` → `v6/` (약 2건)
- `03.graphrag/separate/v6/`: `v14/` → `v16/`, `v20/` → `v23/`, `v22/` → `v23/` (약 6건)
