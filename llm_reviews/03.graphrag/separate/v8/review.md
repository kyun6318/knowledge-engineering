# v8 리뷰 — 03.graphrag/separate/v8

> **리뷰 대상**: `03.graphrag/separate/v8/` (graphrag 11개, interface 6개, sf 8개 = 총 25개 문서)
> **리뷰일**: 2026-03-14
> **교차 참조**: `00.datamodel/summary/v3.md`, `00.datamodel/summary/v3-db-schema.md`, `01.ontology/v25/`, `02.knowledge_graph/v18/`
> **이전 리뷰**: `llm_reviews/03.graphrag/separate/v2/review.md`

---

## 요약

| 심각도 | 건수 | 핵심 패턴 |
|--------|------|-----------|
| **CRITICAL** | 4건 | MAPPED_TO 방향 불일치, Vacancy JSON 중복 키, 스키마 버전 참조 오류, 파일명 불일치 |
| **HIGH** | 7건 | Chapter 규모 산출 근거 불명확, 유니크 제약 누락, 비용 비율 오류, Cypher Q번호 충돌, SIE 통합 미구체화 |
| **MEDIUM** | 6건 | LLM 비용 기준 혼용, 태스크 수 불일치, freshness 참조 경로, 적재 범위 혼용, Phase 5 태스크 미집계 |
| **LOW** | 3건 | 의사결정 건수 표기 오류, 코드 async/sync 혼용, 구코드 매핑 누락 |

---

## CRITICAL

### C1: MAPPED_TO 엣지 방향 불일치

**위치**: `graphrag/01_graphrag_g0_setup.md` line 37 vs `graphrag/07_neo4j_schema.md` §9.3 line 340-344

**현상**:
- `01_graphrag_g0_setup.md`: `Person ──[MAPPED_TO]──-> Vacancy` (Person → Vacancy)
- `07_neo4j_schema.md`: `MERGE (v)-[m:MAPPED_TO]->(p)` (Vacancy → Person)
- `04_graphrag_g3_matching.md` line 123: `Vacancy -> MAPPED_TO -> Person Top-K` (Vacancy → Person)

**문제**: 동일 엣지의 방향이 문서 간 반대. Neo4j에서 방향은 쿼리 성능과 의미에 직접 영향.

**영향**: GraphRAG 팀이 G-0에서 스키마를 설정할 때 잘못된 방향으로 구현할 위험.

**권장**: `01_graphrag_g0_setup.md`의 Phase G-3 스키마를 `Vacancy ──[MAPPED_TO]──-> Person`으로 통일. 07_neo4j_schema.md와 04_graphrag_g3_matching.md가 정본.

---

### C2: Vacancy Data Contract JSON 중복 키

**위치**: `sf/04_sf_phase3_jd_company.md` line 26-27

**현상**:
```json
"seniority": "SENIOR",
"needed_signals": ["TEAM_SCALING", "NEW_SYSTEM_BUILD"],
"seniority": "LEAD"
```

**문제**: `seniority` 키가 2번 등장. JSON 파서에 따라 첫 번째 또는 마지막 값이 사용되어 비결정적 동작 발생.

**영향**: S&F 팀이 이 예시를 참조하여 Vacancy JSON을 생성하면 실제 적재 시 seniority 값이 의도와 다를 수 있음.

**권장**: 중복 `seniority` 제거. `interface/00_data_contract.md`의 Vacancy 스키마(seniority 1개)가 정본.

---

### C3: 스키마 버전 참조 잔존 (v19)

**위치**: 다수 파일

| 파일 | 위치 | 참조 |
|------|------|------|
| `graphrag/01_graphrag_g0_setup.md` | line 12, 46 | "v19 스키마", "v25/02_candidate_context.md" (혼재) |
| `graphrag/02_graphrag_g1_mvp.md` | line 61, 63 | "v19" |
| `graphrag/04_graphrag_g3_matching.md` | line 37, 39 | "(v19)", "(v19)" |
| `graphrag/README.md` | line 23 | "v19 스키마" |
| `interface/02_tasks.md` | line 39-42 | "v19" |

**문제**: 현재 온톨로지 정본은 `v25`이나 다수 위치에서 `v19`를 참조. v19→v25 사이에 필드 변경/추가가 있었을 수 있음.

**영향**: 구현 시 이전 버전의 스키마를 기준으로 개발할 위험.

**권장**: 모든 "v19" 참조를 "v25"로 갱신. 단, 스키마 필드 차이가 있다면 해당 변경을 반영해야 함.

---

### C4: interface/README.md 파일명 불일치

**위치**: `interface/README.md` line 70, `graphrag/README.md` line 42

**현상**:
- README에서 `02_risks.md`로 문서를 참조
- 실제 파일명은 `02_tasks.md`
- `graphrag/README.md`에서도 `../interface/02_risks.md` 참조

**문제**: 존재하지 않는 파일을 참조. 리스크 관리 문서가 실제로 누락되었거나 파일명이 변경됨.

**영향**: 팀 분리 5대 리스크(R1~R5) 정보를 찾을 수 없음. 리스크 완화 방안 문서화 공백.

**권장**: (1) `02_tasks.md`가 리스크 내용을 포함하는지 확인, (2) 리스크 내용이 별도 파일이라면 `02_risks.md` 생성, (3) README 참조 경로 수정.

---

## HIGH

### H1: Chapter 노드 규모 산출 근거 불일치

**위치**: `graphrag/07_neo4j_schema.md` §7.1 vs `00.datamodel/summary/v3.md` §2.1

**현상**:
- v8: Chapter ~18M, "이력서당 평균 ~5.6건" (3.2M × 5.6 = 17.9M)
- v3.md: career 18,709,830건, 이력서당 평균 **3.4개**, 이력서 커버리지 **68.9%**

**문제**: v3.md 기준 서비스 가용 풀(3.2M)에서 경력 보유자는 3.2M × 68.9% ≈ 2.2M명, 2.2M × 3.4 ≈ 7.5M으로 산출됨. 18M과 큰 차이.

**가능한 설명**: 서비스 풀 3.2M이 이미 경력 보유자 위주(EXPERIENCED + HIGH/PREMIUM)로 필터링된 집합이라면, 이 집합의 경력 보유율이 ~100%이고 이력서당 평균이 5.6일 수 있음. 그러나 이 가정이 명시되지 않음.

**권장**: 07_neo4j_schema.md §7.1에 "EXPERIENCED + HIGH/PREMIUM 필터 후 경력 보유율 ~100%, 이력서당 평균 5.6건"의 산출 근거를 명시.

---

### H2: Chapter, Outcome 유니크 제약 누락

**위치**: `graphrag/07_neo4j_schema.md` §8.1

**현상**: Unique Constraints에 Chapter(~18M)와 Outcome(~5M) 노드가 없음. 정의된 제약:
- Person, Organization, Vacancy, Role, Skill, Industry, SituationalSignal

**문제**: Chapter는 MERGE 적재 시 `chapter_id` 기반 중복 방지가 필요. 유니크 제약 없이 MERGE하면 인덱스 미사용으로 O(N) 스캔 발생 → 적재 성능 심각 저하.

**영향**: 18M Chapter MERGE 시 적재 시간이 수 시간→수 일로 증가 가능.

**권장**: 다음 제약 추가:
```
CREATE CONSTRAINT chapter_id_unique FOR (c:Chapter) REQUIRE c.chapter_id IS UNIQUE;
CREATE CONSTRAINT outcome_id_unique FOR (o:Outcome) REQUIRE o.outcome_id IS UNIQUE;
```

---

### H3: Gold Label 비용 비율 오류

**위치**: `graphrag/05_graphrag_g4_ops.md` line 75

**현상**: "Gold Label 인건비 혹은 LLM 비용($2,920~5,840)은 전체 프로젝트 비용의 **53~64%**를 차지한다"

**검증**:
- 하한: $2,920 / ($3,427 + $1,955) = $2,920 / $5,382 = **54.2%** → ~54% ✓
- 상한: $5,840 / ($6,777 + $1,955) = $5,840 / $8,732 = **66.9%** → ~67% ✗ (64%가 아님)

**권장**: "53~**67%**"로 수정.

---

### H4: Cypher Q1~Q5 번호 충돌

**위치**: `graphrag/02_graphrag_g1_mvp.md` vs `graphrag/07_neo4j_schema.md`

**현상**:

| Q번호 | 02_graphrag_g1_mvp.md | 07_neo4j_schema.md |
|-------|----------------------|-------------------|
| Q1 | 스킬 기반 검색 | vacancy_fit (NEEDS_SIGNAL) |
| Q2 | 시맨틱 검색 (Vector) | stage_match (Organization) |
| Q3 | 회사 기반 검색 | 하이브리드 (Vector+Graph) |
| Q4 | 시니어리티 분포 | NEEDS_SIGNAL 자동 추론 |
| Q5 | 복합 조건 (PERFORMED_ROLE) | 같은 산업 후보 탐색 |

**문제**: 두 문서의 Q번호가 완전히 다른 쿼리를 가리킴. 다른 문서에서 "Q3 쿼리"를 참조할 때 혼란 발생.

**권장**: (1) g1_mvp의 쿼리는 MVP 단계 쿼리로 `Q-MVP-1~5`로 재번호, (2) 07_neo4j_schema의 쿼리는 본 스키마 쿼리로 `Q1~Q5` 유지, 또는 (3) 하나의 통합 쿼리 목록으로 정리.

---

### H5: SIE 모델 (GLiNER2/NuExtract) 통합 단계 미구체화

**위치**: `sf/01_sf_phase0_poc.md` line 120-123, `sf/02_sf_phase1_preprocessing.md` line 101

**현상**:
- Phase 0에서 "GLiNER2/NuExtract 1.5 모델의 경력기술서 구조 추출 성능 검증" 언급
- Phase 1에서 "GLiNER2 모델을 workDetails/careerDescription에 적용" 언급
- 그러나 **구체적 태스크, 코드 골격, 산출물이 없음**

**문제**: v3.md §3에서 SIE 모델은 핵심 구성 요소(Outcome 추출, careerDescription 16.9% 한계 보완)로 정의되었으나, v8 실행계획에서는 코멘트 수준의 언급만 있음.

**영향**: SIE 모델의 구현 책임(S&F vs 별도 ML팀), 필요 GPU 리소스(NuExtract 1.5 = ~15GB VRAM), 파이프라인 통합 방법이 불명확.

**권장**: (1) `02_tasks.md`에 SIE 관련 태스크 추가 (Phase 0: PoC, Phase 1: 파이프라인 통합), (2) GPU 리소스 요구사항을 비용 문서에 반영, (3) SIE 출력 → LLM 프롬프트 연계 데이터 흐름 명시.

---

### H6: F4 culture_fit INACTIVE 시 가중치 재분배 미적용

**위치**: `graphrag/04_graphrag_g3_matching.md` line 90-91

**현상**:
- v8 코드: `culture_score = 0.5` (F4 INACTIVE, 기본값 포함)
- v8 주석: "정본(01.ontology)의 INACTIVE→가중치 재분배 정책과 다름"
- 01.ontology/v25/03_mapping_features.md: INACTIVE 피처는 가중치 0으로 설정 후 나머지 피처에 비례 재분배

**문제**: F4가 <10% ACTIVE인 상황에서 기본값 0.5를 주면, 실질적으로 **모든 후보의 overall_match_score가 0.05(= 0.10 × 0.5) 만큼 동일하게 상향**됨. 변별력은 없지만 다른 피처의 상대적 기여도를 왜곡.

**영향**: 가중치 합 1.0을 유지하면서 F4에 0.5를 주면, F4가 항상 동일한 점수를 기여하여 나머지 4개 피처의 변별력이 상대적으로 약화됨. 정본의 재분배 방식(F4=0, 나머지 90%→100%로 비례 확대)이 더 정확.

**권장**: v1 MVP라도 INACTIVE 피처의 가중치 재분배를 구현하거나, 최소한 `culture_score = None, weight = 0`으로 처리. 기본값 0.5 포함은 피하는 것이 좋음.

---

### H7: 적재 범위 600K vs 3.2M 혼용

**위치**: `graphrag/07_neo4j_schema.md` §7, `graphrag/03_graphrag_g2_scale.md`, `sf/03_sf_phase2_file_and_batch.md`

**현상**:
- 07_neo4j_schema: "서비스 풀 ~3.2M 이력서 기준으로 Neo4j에 적재될 노드/엣지 규모 추정"
- 같은 문서 바로 아래: "v1 초기 적재는 600K 규모로 시작"
- G-2 사이징: "600K 외삽"
- sf Phase 2: "600K Batch 처리"
- 비용 계산: Neo4j Professional 사이징은 600K 기준

**문제**: 규모 추정(§7)은 3.2M 기반(27M 노드, 133M+ 관계)이나 실제 실행계획과 비용은 600K 기반. 이 차이가 명확히 분리되지 않아 Neo4j 티어 판단에 혼란 발생.

**권장**: §7에 두 시나리오를 명시적으로 분리:
- **v1 초기 적재 (600K)**: ~4.5M 노드, ~22M 관계 → Professional 8GB 충분
- **전체 서비스 풀 (3.2M)**: ~27M 노드, ~133M 관계 → Professional/Enterprise 검증 필요

---

## MEDIUM

### M1: LLM 비용 추정 기준 혼용

**위치**: `interface/implementation_roadmap.md` §2 vs `sf/06_sf_cost.md`

**현상**:
- implementation_roadmap: LLM 비용 ~$484 (Gemini 2.0 Flash 기준)
- sf_cost: LLM 비용 $1,730 (Anthropic Batch API = Claude Haiku 4.5 기준)
- 차이: **3.6배**

**문제**: 같은 파이프라인의 LLM 비용이 모델 선택에 따라 극적으로 달라지는데, 두 문서가 다른 모델을 기본값으로 사용. `sf/06_sf_cost.md`의 [v5] 주석에서 이를 언급하지만, `implementation_roadmap.md`는 Gemini 기준으로만 작성.

**권장**: implementation_roadmap.md에 모델별 시나리오 테이블 추가:

| 모델 | 1회 처리 비용 | Phase 0 확정 시점 |
|------|-------------|-----------------|
| Gemini 2.0 Flash | ~$484 | Phase 0 기본값 |
| Claude Haiku 4.5 (Batch) | ~$1,730 | Phase 0 비교 후 결정 |

---

### M2: 태스크 수 불일치

**위치**: `interface/README.md` vs `interface/02_tasks.md`

**현상**:
- README: "태스크 분류 집계 (73개)"
- 02_tasks.md: Phase 0~4에서 73개 + Phase 5에서 3개 = **76개**

**문제**: Phase 5(LinkedIn 통합)가 02_tasks.md에는 있으나 README 집계에 미반영.

**권장**: README 집계 테이블에 Phase 5 행 추가 (S&F 3건).

---

### M3: Cypher 쿼리 벤치마크 대상 불명확

**위치**: `graphrag/03_graphrag_g2_scale.md` line 75-78

**현상**: "Cypher 5종 × 480K+ 데이터: p95 < 2초 확인"

**문제**: "Cypher 5종"이 g1_mvp의 Q1~Q5인지, 07_neo4j_schema의 Q1~Q5인지 불명확 (H4 참조). G-2 시점에서는 Candidate-Only 스키마이므로 07_neo4j_schema의 Q1(vacancy_fit), Q2(stage_match)는 아직 사용 불가.

**권장**: G-2 벤치마크 대상 쿼리를 명시적으로 나열 (g1_mvp Q1~Q5 기준).

---

### M4: freshness_weight 참조 경로 불일치

**위치**: `graphrag/08_serving.md` §1, `graphrag/04_graphrag_g3_matching.md` line 107

**현상**:
- 08_serving.md: `00_data_source_mapping §3.5` 참조
- 04_graphrag_g3_matching.md: `01.ontology/v25/00_data_source_mapping.md §3.5` 참조

**문제**: 08_serving.md의 참조가 상대 경로 없이 파일명만 기재. 혼동 가능.

**권장**: `01.ontology/v25/00_data_source_mapping.md §3.5`로 전체 경로 통일.

---

### M5: Phase 5 의존성 표기 오류

**위치**: `interface/02_tasks.md` Phase 5 섹션

**현상**: Phase 5 의존성이 `T1-4`, `T2-1`, `T2-4`로 표기되어 있으나 나머지 Phase의 태스크 ID 체계(`0-1`, `1-A`, `2-0-1` 등)와 다름.

**문제**: `T1-4`가 `implementation_roadmap.md` Phase 1 순서 4(스킬 정규화)인지, `02_tasks.md` Phase 1의 특정 태스크인지 불명확.

**권장**: Phase 5 태스크의 의존성을 `02_tasks.md`의 태스크 ID 체계로 통일 (예: `T5-1 의존: 1-D-3 + 3-3-1`).

---

### M6: Data Contract에 Outcome/SituationalSignal 상세 스키마 부재

**위치**: `interface/00_data_contract.md` §2.A

**현상**: CandidateContext JSON에 `outcomes`와 `situational_signals`가 Chapter 하위 배열로 포함되어 있으나:
- `outcomes[].outcome_type`의 유효값 열거 없음 (SCALE, EFFICIENCY, LAUNCH 등)
- `outcomes[].confidence` 범위 미명시
- `situational_signals[].confidence` 범위 미명시 (v25에서는 0.0~1.0)

**문제**: S&F가 JSON을 생성할 때 유효값 참조 없이 자유 생성할 위험.

**권장**: Data Contract에 outcome_type enum과 confidence 범위(0.0~1.0)를 명시. `01.ontology/v25/02_candidate_context.md` 참조 링크 추가.

---

## LOW

### L1: 의사결정 포인트 건수 표기 오류

**위치**: `interface/01_go_nogo_decisions.md` §2 제목

**현상**: "의사결정 포인트 (11건)"이라고 하지만 실제 테이블에 **17건** 나열 (원래 11건 + [v4] 추가 3건 + [v5] 추가 1건 + W0 PII 1건 + W27 1건).

**권장**: "(17건)"으로 수정.

---

### L2: Python 코드 async/sync 혼용

**위치**: sf 전반 (`sf/02_sf_phase1_preprocessing.md`, `sf/03_sf_phase2_file_and_batch.md`)

**현상**:
- `extract_candidate_context()` → `async def`
- `mask_pii()` → 일반 `def`
- `run_quality_checks()` → 일반 `def`

**문제**: 실행 컨텍스트(asyncio vs sync) 혼용 시 실제 구현에서 이벤트 루프 관련 이슈 발생 가능. 코드 골격 수준이므로 심각도 낮음.

**권장**: 구현 시 통일. Batch 처리 파이프라인은 sync, API 서빙은 async가 적합.

---

### L3: implementation_roadmap.md Phase 1에 구코드→신코드 학교 매핑 누락

**위치**: `interface/implementation_roadmap.md` §1.Phase 1

**현상**: v3.md §9.3에서 "Critical, 난이도 중간"으로 분류된 "구코드→신코드 학교 매핑 (~110만건)" 과제가 implementation_roadmap.md Phase 1에 누락.

**영향**: Person.education_level 정확도에 영향. 단, v1 매칭에서 학력은 보조 데이터이므로 심각도 LOW.

**권장**: implementation_roadmap.md Phase 1에 추가 (순서 2.5, 난이도 중간, 영향: Person.education_level).

---

## 긍정적 평가

### P1: v8 주석 시스템의 성숙도

v8에서 `[v8]` 태그로 표시된 주석들이 정본(01.ontology)과의 차이점, v1 MVP 한계, 향후 개선 방향을 명확히 문서화. 특히:
- F2 scope_type vs seniority enum 불일치 인지 및 문서화
- F4 INACTIVE 기본값 vs 정본 재분배 정책 차이 명시
- Data Contract의 flat 필드 vs Graph Schema의 관계 변환 설명

### P2: SituationalSignal 14개 taxonomy 정합성

`01_graphrag_g0_setup.md`의 SituationalSignal 초기화 Cypher가 `01.ontology/v25/02_candidate_context.md`의 14개 라벨과 **정확히 일치**:
- EARLY_STAGE, SCALE_UP, TURNAROUND, GLOBAL_EXPANSION
- TEAM_BUILDING, TEAM_SCALING, REORG
- LEGACY_MODERNIZATION, NEW_SYSTEM_BUILD, TECH_STACK_TRANSITION
- PMF_SEARCH, MONETIZATION, ENTERPRISE_TRANSITION, OTHER

(참고: `v3.md` §4.7의 taxonomy는 구 버전으로, M_AND_A/PIVOT/INTERNATIONAL_EXPANSION 대신 MONETIZATION/GLOBAL_EXPANSION/OTHER 사용)

### P3: Data Contract의 완성도

`interface/00_data_contract.md`의 PubSub 토픽 스키마, JSON 3종, 보안 설계(CMEK + 서비스계정 분리)가 잘 정의되어 있으며, 팀 간 결합도를 최소화하는 설계 원칙이 잘 구현됨.

### P4: 평가 전략의 체계성

`graphrag/09_evaluation.md`의 GraphRAG vs Vector Baseline 비교 실험 설계가 매우 체계적:
- 검정력 분석(Power Analysis)과 적응적 표본 크기 결정 프로토콜
- Cohen's d + p-value 공동 판단 기준
- 4-Case 의사결정 트리 + 구체적 수치 시나리오
- 평가자 간 일치도(Krippendorff's alpha) 미달 시 대응 방안

### P5: 비용 추정의 투명성

GraphRAG/S&F 비용을 Phase별로 상세 분류하고, VG4(통합 버전) 대비 차이의 원인을 설명. Enterprise 시나리오 비용도 별도 산정.

---

## 다음 단계 권장

| 우선순위 | 작업 | 영향 범위 |
|---------|------|-----------|
| 1 (즉시) | C1: MAPPED_TO 방향 통일 | g0_setup |
| 2 (즉시) | C2: Vacancy JSON 중복 키 제거 | sf Phase 3 |
| 3 (즉시) | C4: README 파일명 수정 + 리스크 문서 확인 | interface |
| 4 (1주 내) | C3: v19→v25 참조 갱신 | 다수 파일 |
| 5 (1주 내) | H2: Chapter/Outcome 유니크 제약 추가 | 07_neo4j_schema |
| 6 (1주 내) | H4: Cypher Q번호 재정리 | g1_mvp, 07_neo4j_schema |
| 7 (Phase 0 전) | H5: SIE 통합 태스크 구체화 | sf, 02_tasks |
| 8 (Phase 0 전) | H6: F4 INACTIVE 가중치 재분배 설계 결정 | 04_graphrag_g3_matching |

---

## 부록: CRITICAL/HIGH 이슈 기원 추적

> `03.graphrag/old/` 역순 탐색 결과. 각 이슈가 최초 도입된 버전과 원인을 기록.

### C1: MAPPED_TO 방향 불일치 — 기원: `core/1`

| 버전 | 상태 | 비고 |
|------|------|------|
| **core/1** | **최초 도입** | `04_phase3_company_and_matching.md` line 405: 다이어그램 `Person→Vacancy` (잘못됨), 같은 파일 Q6~Q10 쿼리는 `Vacancy→Person` (맞음) |
| core/2~5 | 전파 | 다이어그램 복사, Cypher 코드 없음 |
| separate/v1~v2 | 전파 | `01_graphrag_g0_setup.md` 다이어그램 복사 |
| separate/v3 | 분기 발생 | `07_neo4j_schema.md` 신규 작성 시 `MERGE (v)-[m:MAPPED_TO]->(p)` (맞음). 다이어그램은 미수정 |
| separate/v4~v5 → **v8** | 고착 | 다이어그램(잘못됨)과 Cypher(맞음)가 별개 파일에서 공존 |

**근본 원인**: core/1에서 개념 다이어그램과 구현 쿼리가 동시에 작성될 때, 다이어그램은 "Person이 Vacancy에 매핑된다"는 자연어 관점으로, 쿼리는 "Vacancy가 Person을 찾는다"는 검색 관점으로 작성. v3에서 07_neo4j_schema.md를 별도 파일로 분리하면서 올바른 방향으로 구현했으나, g0_setup 다이어그램은 갱신되지 않음.

---

### C2: Vacancy JSON 중복 `seniority` 키 — 기원: `v8` (v7→v8 전환 오류)

| 버전 | 상태 | 비고 |
|------|------|------|
| v1~v6 | 정상 | `"seniority"` 1개 + `"hiring_context_scope"` 별도 필드 |
| **v7** | 필드명 변경 | `hiring_context_scope` → `vacancy_seniority`로 변경 (2개 필드 공존, 정상) |
| **v8** | **버그 도입** | `vacancy_seniority` 제거 결정 → `sf/04_sf_phase3_jd_company.md` 예시에서 `"hiring_context_scope": "LEAD"` → `"seniority": "LEAD"`로 잘못 변환하여 중복 키 발생 |

**근본 원인**: v8에서 `vacancy_seniority`를 `seniority`로 통합할 때, `interface/00_data_contract.md`(정본)은 올바르게 수정했으나, `sf/04_sf_phase3_jd_company.md`(예시)는 기존 필드명을 `seniority`로 바꾸기만 하여 중복 키 발생. **정본-예시 간 동기화 누락**.

---

### C3: v19 스키마 참조 잔존 — 기원: `separate/v1` (2026-03-11)

| 버전 | 상태 | 비고 |
|------|------|------|
| **separate/v1** | **최초 작성** | 2026-03-11, 당시 온톨로지 정본은 v19 → v19 참조는 **작성 시점에 정확** |
| separate/v2~v5 | 미갱신 | 온톨로지가 v20→v21→v22로 진화했으나 graphrag 문서의 v19 참조 미갱신 |
| **v8** | 부분 갱신 | `[v8]` 주석에서는 `v25` 참조를 추가했으나, 본문의 v19 참조는 미수정 |

**근본 원인**: 2026-03-11~14 사이 온톨로지가 v19→v25로 빠르게 진화(4일간 6버전). graphrag 문서는 별도 리뷰 사이클로 갱신되어 동기화 지연. v8에서 `[v8]` 주석으로 v25 참조를 추가한 것은 올바른 방향이나, 본문의 v19 참조를 일괄 치환하지 않음.

**참고**: v19와 v25의 노드/엣지 이름(HAS_CHAPTER, PERFORMED_ROLE 등)은 동일하므로 실질적 구현 영향은 낮음. 단, 세부 필드 정의(속성 타입, 신규 추가 필드)에서 차이가 있을 수 있음.

---

### C4: README의 `02_risks.md` 참조 — 기원: `separate/v3` (파일명 변경 시 미갱신)

| 버전 | 상태 | 비고 |
|------|------|------|
| separate/v1~v2 | 정상 | 실제 파일 `02_risks.md` 존재, README 참조 일치 |
| **separate/v3** | **버그 도입** | 파일이 `02_risks.md` → `02_tasks.md`로 **리네임/교체**됨. README와 graphrag/README의 참조는 미갱신 |
| separate/v4~v5 → **v8** | 고착 | README 참조 계속 `02_risks.md`로 유지 |

**근본 원인**: v3에서 문서 구조를 개편하면서 리스크 문서를 태스크 문서로 교체했으나, README 인덱스를 갱신하지 않음.

---

### H1: Chapter 규모 산출 근거 불일치 — 기원: `separate/v3` (07_neo4j_schema 최초 작성)

| 버전 | 상태 | 비고 |
|------|------|------|
| core/1~5 | 해당 없음 | 별도 규모 추정 문서 없음 |
| v1~v2 | 해당 없음 | 07_neo4j_schema 미존재 |
| **v3** | **최초 작성** | §7 노드/엣지 규모 추정 작성. Chapter ~18M, "이력서당 ~5.6건" 기재 |
| v4 | [v4] 주석 추가 | "3.2M은 전체 서비스 가용 풀, 600K는 v1 초기 적재" 구분 추가. 그러나 5.6건 산출 근거는 미보충 |
| v5 → **v8** | 미변경 | 산출 근거 여전히 불명확 |

**근본 원인**: v3에서 규모 추정 시 career 전체 18.7M건을 Person 3.2M으로 나눈 것으로 추정(18.7M / 3.2M ≈ 5.8). 그러나 이는 모든 이력서(8M)의 career를 서비스 풀(3.2M)로 나눈 것이라 산출이 정확하지 않음.

---

### H2: Chapter/Outcome 유니크 제약 누락 — 기원: `separate/v3` (07_neo4j_schema 최초 작성)

| 버전 | 상태 | 비고 |
|------|------|------|
| v1~v2 | 해당 없음 | 07_neo4j_schema 미존재 |
| **v3** | **누락 시작** | §8.1에 Person, Organization, Vacancy, Role, Skill, Industry, SituationalSignal만 정의 |
| v4~v5 → **v8** | 미보완 | 이후 버전에서도 Chapter/Outcome 유니크 제약 추가 없음 |

**근본 원인**: v3에서 Neo4j 스키마를 설계할 때, **공유 노드**(Role 242개, Industry 63개, Signal 14개)와 **엔티티 노드**(Person, Organization, Vacancy)에만 유니크 제약을 적용. **종속 노드**(Chapter, Outcome)는 MERGE 패턴에서 Person→Chapter 관계로 접근하므로 유니크 제약이 불필요하다고 판단한 것으로 보임. 그러나 UNWIND 배치 적재 시에는 `MERGE (c:Chapter {chapter_id: ...})`로 직접 접근하므로 유니크 제약이 필요.

---

### H3: Gold Label 비용 비율 "53~64%" — 기원: `separate/v2`

| 버전 | 상태 | 비고 |
|------|------|------|
| v1 | 해당 없음 | Gold Label 비용 비율 미기재 |
| **v2** | **최초 작성** | `05_graphrag_g4_ops.md` line 75: "53~64%" 기재 |
| v3~v5 → **v8** | 미수정 | 이후 비용 구조 변경에도 비율 미갱신 |

**근본 원인**: v2 시점 비용 구조에서는 64%가 정확했을 가능성. 이후 S&F 비용이 변경되면서 분모가 달라졌으나 비율을 재계산하지 않음.

---

### H4: Cypher Q1~Q5 번호 충돌 — 기원: `separate/v1` + `separate/v3`

| 버전 | 상태 | 비고 |
|------|------|------|
| **v1** | MVP 쿼리 작성 | `02_graphrag_g1_mvp.md`에 Q1~Q5 (스킬, 시맨틱, 회사, 시니어리티, 복합) |
| v2 | 유지 | 동일 |
| **v3** | **충돌 도입** | `07_neo4j_schema.md` 신규 작성 시 별도 Q1~Q5 (vacancy_fit, stage_match, 하이브리드, 추론, 산업) |
| v4~v5 → **v8** | 고착 | 두 체계가 별개 파일에서 공존, 번호 재정리 없음 |

**근본 원인**: v3에서 07_neo4j_schema.md를 01.ontology에서 분리 이동할 때, 온톨로지의 쿼리 번호(Q1~Q5)를 그대로 가져옴. 기존 g1_mvp의 Q1~Q5와 충돌 여부를 확인하지 않음.

---

### H5: SIE 모델 통합 미구체화 — 기원: `v8` (v3.md 신규 요소)

| 버전 | 상태 | 비고 |
|------|------|------|
| v1~v5 | 해당 없음 | SIE 모델 미언급 (v3.md의 SIE 분석은 별도 진행) |
| **v6~v8** | 코멘트만 추가 | `[v3 신규]` 주석으로 SIE 언급, 구체적 태스크/코드 미구현 |

**근본 원인**: `00.datamodel/summary/v3.md`(2026-03-14)에서 SIE 모델(GLiNER2/NuExtract)을 핵심 구성 요소로 신규 정의. graphrag v6~v8에서 이를 반영하려 했으나 코멘트 수준에서 멈춤. SIE는 데이터모델 분석에서 정의된 것이지, graphrag 실행계획의 태스크로 아직 분해되지 않은 상태.

---

### H6: F4 culture_fit 기본값 0.5 — 기원: `separate/v1` (최초 설계)

| 버전 | 상태 | 비고 |
|------|------|------|
| **v1** | **최초 작성** | `04_graphrag_g3_matching.md`: `culture_score = 0.5`, 가중치 10% |
| v2~v5 | 미변경 | 동일 코드 |
| **v8** | 주석만 추가 | `[v8]` 주석으로 정본과의 차이 인지 문서화, 코드는 미변경 |

**근본 원인**: v1 설계 시 "v1 MVP에서 F4는 데이터 부재로 INACTIVE, 기본값 0.5로 처리"라는 의도적 결정. 그러나 정본(01.ontology)의 INACTIVE 처리 방식(가중치 재분배)과 달라진 것을 v8에서 인지했으나 코드를 수정하지 않음.

---

### H7: 600K vs 3.2M 혼용 — 기원: `separate/v3` + `v4` 보강

| 버전 | 상태 | 비고 |
|------|------|------|
| v1~v2 | 해당 없음 | 07_neo4j_schema 미존재 |
| **v3** | 3.2M 단일 기준 | §7 규모 추정에 3.2M만 사용, 600K 미언급 |
| **v4** | 이중 기준 도입 | `[v4]` 주석으로 "3.2M=전체 풀, 600K=v1 초기"를 구분 추가 |
| v5 → **v8** | 고착 | 구분은 주석으로만 존재, §7 본문 규모 추정은 여전히 3.2M 기반 |

**근본 원인**: v4에서 02.knowledge_graph와의 규모 정합성을 맞추기 위해 이중 기준을 도입했으나, 주석 수준의 설명만 추가. §7 본문에 600K 기준 노드/엣지 수를 별도 행으로 추가하지 않아 실질적 혼란 해소 미흡.

---

### 종합: 이슈 기원 분포

| 기원 시점 | 이슈 수 | 이슈 목록 |
|-----------|---------|-----------|
| **core/1** (최초 설계) | 1 | C1 |
| **separate/v1** (팀 분리 최초) | 3 | C3, H4(일부), H6 |
| **separate/v2** | 1 | H3 |
| **separate/v3** (07_neo4j_schema 도입) | 4 | C4, H1, H2, H4(완성) |
| **separate/v4** | 1 | H7(이중 기준 도입) |
| **v8** (최신) | 2 | C2, H5 |

**패턴**: 이슈의 **54%**(6/11)가 v1~v3에서 기원하여 이후 버전으로 전파됨. 특히 v3에서 07_neo4j_schema.md를 온톨로지에서 분리할 때 4건의 이슈가 동시 발생. **문서 분리/이동 시 일관성 검증** 프로세스 부재가 근본 원인.
