# v3 초기 설계 관점의 v6 반영도 평가

> v3 문서 2건(Context Overview, GraphDB 엔티티 구조 Ideation)에서 제시한 핵심 설계 관점이
> v4 -> v5 -> v6 진화 과정을 거치며 **보존, 강화, 변형, 또는 누락**되었는지를 추적 평가한다.
>
> 평가일: 2026-03-08
> 기준 문서:
> - v3: `Context Overview`, `GraphDB 엔티티 구조 Ideation`
> - v4: `01~04` (CompanyContext, CandidateContext, MappingFeatures, Graph Schema)
> - v5: `01_crawling_strategy`, `02_v4_amendments`
> - v6: `01_crawling_strategy`, `02_v4_amendments`
> - v6 리뷰: `review/v6/review.md`

---

## 1. 총평

v3의 핵심 설계 철학은 v6에서 **대부분 보존되거나 강화**되었다. 특히 Chapter-Trajectory 모델, Evidence-first 원칙, CompanyContext/CandidateContext 독립성이라는 3대 축은 v4에서 구현 가능하게 재정의된 이후 v6까지 일관되게 유지된다. 다만 v3의 일부 야심적 구상(8 facets, GraphRAG community report, Closed-loop Enrichment)은 v1 현실성을 고려해 의도적으로 축소/후속 버전으로 이동되었으며, 이 결정은 v3 평가서에서 권장한 방향과 일치한다.

| 평가 축 | 반영도 (5점) | 요약 |
|---|---|---|
| 핵심 철학 보존 | **5.0** | 궤적 기반 매칭, Evidence-first, 독립성 원칙 완전 보존 |
| 스키마 설계 계승 | **4.5** | Chapter/Experience 통합, Evidence 정규화, 구현 가능 수준으로 강화 |
| GraphDB 구조 통합 | **4.0** | Company 측 모델링 추가, SituationalSignal 노드 신설, v3 괴리 해소 |
| 데이터 품질 원칙 | **4.5** | confidence ceiling, source tier, 부분 완성 모두 유지 + 캘리브레이션 추가 |
| 현실적 축소의 합리성 | **4.5** | 축소/이동 결정이 명확한 근거와 함께 문서화 |
| v3 미비점 보완 | **4.5** | v3 평가서의 6개 권장사항 중 5개 해결, 1개(LLM 추출 PoC) 파일럿으로 위임 |
| **종합** | **4.5** | v3 설계의 정신과 구조를 충실히 계승하면서 구현 가능성을 확보 |

---

## 2. 핵심 설계 관점별 추적

### 2.1 Chapter-Trajectory 모델

**v3 원문**: "맥락(Context)은 '현재 상태(state)'가 아니라 '어디서 와서 어디로 가는가'를 나타내는 궤적(trajectory) + 상황(situation)의 복합이다."

| 구성요소 | v3 정의 | v6 반영 | 반영도 |
|---|---|---|---|
| Chapter 개념 | 변곡점/긴장/의도된 방향 포함 | v4 Experience로 통합, situational_signals로 구조화 | 보존 + 강화 |
| CompanyChapter 6요소 | Growth Trajectory, Structural Tensions, Domain, Vacancy, Operating Model, Role Expectations | v4에서 모두 필드화, v6에서 tensions taxonomy(A6) + facet 병합(D-3) 확정 | 보존 + 강화 |
| CandidateChapter 6요소 | Experienced Trajectory, Role Evolution, Domain Depth, Failure & Recovery, Work Style, PastCompanyContext | v4에서 모두 필드화, 14개 SignalLabel taxonomy로 일관성 확보 | 보존 + 강화 |
| "미래 벡터 <-> 과거 벡터" 매칭 | 기업의 미래 챕터 vs 후보의 과거 경험 | v4 MappingFeatures의 stage_match, vacancy_fit으로 직접 구현 | **핵심 보존** |
| NEXT_CHAPTER 관계 | 커리어 궤적 보존 | v4 Graph Schema에서 `gap_months` edge 속성 추가하여 강화 | 보존 + 강화 |

**평가: 5.0/5.0** -- v3의 가장 핵심적인 설계 철학이 완벽하게 보존되고, 구현 가능한 형태로 구체화되었다.

---

### 2.2 Evidence-first 원칙

**v3 원문**: "모든 맥락 주장(claim)은 반드시 evidence와 연결된다. 최소 단위: source_id + span + source_type + confidence + extracted_at"

| 항목 | v3 | v6 | 반영도 |
|---|---|---|---|
| Evidence 구조 | 5개 필드 (source_id, span, source_type, confidence, extracted_at) | v4에서 `extraction_method` 추가하여 6개 필드로 확장 | 보존 + 강화 |
| source_type enum | 미확정 | v4에서 12개 enum 확정, v6에서 source_id 네이밍 컨벤션(C-5) 추가 | **미비점 해결** |
| confidence 캘리브레이션 | 미정의 (v3 평가서에서 지적) | v4에서 6단계 캘리브레이션 기준 + source ceiling 도입, v6에서 카테고리별 ceiling 차등(S-3) 추가 | **미비점 해결** |
| 두 문서 간 Evidence 불일치 | Context Overview(정규화 배열) vs GraphDB(evidence_chunk 속성) | v4에서 통합 Evidence 모델 확정 + Graph에서는 evidence_chunk(Vector Index용) 별도 유지 | **괴리 해소** |
| 광고성 필터링 | 원칙만 제시 | v6에서 NOISE_PATTERNS + OPERATIONAL_CONTEXT 검증 + LLM 프롬프트 내장 | 보존 + 대폭 강화 |

**평가: 5.0/5.0** -- v3에서 가장 잘 설계된 원칙이 v6에서 더욱 구체화되었고, v3 평가서에서 지적한 미비점(confidence 캘리브레이션, source_type enum)도 해결되었다.

---

### 2.3 CompanyContext / CandidateContext 독립성

**v3 원문**: "CompanyContext는 후보와 무관하게, 회사/포지션 소스만으로 생성한다. CandidateContext는 회사와 무관하게, 후보 소스만으로 생성한다."

| 항목 | v3 | v6 | 반영도 |
|---|---|---|---|
| 독립 생성 원칙 | 명문화 | v4에서 유지, v6까지 변경 없음 | 완전 보존 |
| CompanyTalentSignal 분리 | v1.1+ 옵션으로 분리 | v6 A3에서 의도적 제외 명문화 + v2 로드맵 배치 | 보존 + 명확화 |
| Anti-pattern 방어 | 역방향 제외 이유 명문화 | v6 A3에서 3가지 제외 이유 재확인 (데이터 전제조건, 독립성, 편향) | 완전 보존 |

**평가: 5.0/5.0** -- 독립성 원칙이 v6까지 일관되게 유지되며, CompanyTalentSignal의 의도적 제외 사유도 명확하게 문서화되었다.

---

### 2.4 데이터 품질 원칙 (8개항)

v3 Context Overview의 8개 데이터 품질 원칙(8.1~8.5) 추적:

| # | v3 원칙 | v6 반영 | 상세 |
|---|---|---|---|
| 8.1 | 소스 신뢰도 계층 + source_type 강제 | **보존 + 강화** | v4 Tier 시스템(T1~T7, confidence ceiling), v6에서 뉴스 카테고리별 ceiling 차등(S-3) |
| 8.2 | 소스별 처리 원칙 (광고성 필터, NICE 범위 제한, PastCompanyContext 역산) | **보존 + 강화** | v6 광고성 필터(NOISE_PATTERNS + OPERATIONAL_CONTEXT), v4 NICE 팩트 전용 사용, PastCompanyContext nice_current 방식 |
| 8.3 | 부분 완성 정상화 (missing_fields, confidence 기반 weight 하향) | **보존 + 강화** | v4 completeness 메타데이터(fill_rate), v4 MappingFeatures graceful degradation(INACTIVE 상태) |
| 8.4 | coverage/freshness/source_diversity 관리 | **부분 보존** | freshness는 v6 뉴스 신뢰도 보정(기사 나이 감쇠)에 반영. coverage/source_diversity는 completeness.sources_used로 간접 관리되나 필드 단위 관리는 v2로 이동 |
| 8.5 | Closed-loop Enrichment (타겟 질문 루프) | **v2로 이동** | v4/v6에서 enrichment_qa source_type만 정의, 실제 루프는 v2 로드맵 |

**평가: 4.0/5.0** -- 핵심 원칙(8.1~8.3)은 강화되었으나, 8.4의 필드 단위 coverage/diversity 관리와 8.5의 Closed-loop Enrichment는 v2로 이동. v1 범위를 고려하면 합리적 결정이나, v3의 야심 대비 축소된 부분이다.

---

### 2.5 GraphRAG 표현 원칙 (Situation-Role-Outcome Triple)

**v3 원문**: "단순 스킬 그래프가 아니라 Situation-Role-Outcome (+Evidence) 트리플 중심으로 구성한다."

| 트리플 요소 | v3 정의 | v6 Graph 표현 | 반영도 |
|---|---|---|---|
| Situation (Chapter) | 변곡점/긴장/공백 상황 | `:Chapter` 노드 + `:SituationalSignal` 노드(v4 신규) | 보존 + 강화 |
| Role | 해당 상황에서의 스코프/행동 | `:Role` 노드 + `scope_type` 속성 + `PERFORMED_ROLE` 관계 | 보존 |
| Outcome | 결과 -- 성공/실패/지표/학습 | `:Outcome` 노드 (outcome_type 분류, metric_value 포함) | 보존 + 강화 |
| Evidence | 뒷받침 문장/문서/출처 | evidence_chunk 속성(Vector Index용) + 정규화된 Evidence 배열 | 보존 + 정합 해소 |
| Community Report | GraphRAG indexing community report | **미정의** | 미반영 (아래 참조) |

**Community Report 미반영에 대한 분석**:

v3에서는 "GraphRAG Indexing은 엔티티를 추출/정리하고, community report를 생성해 Context Profile을 산출"한다고 기술했으나, v4~v6에서 community report 생성 방식은 구체화되지 않았다. 이는 v3 평가서(3.6절)에서 "GraphRAG 스택의 ROI 불확실"을 지적하며 baseline 비교를 권장한 것과 관련된다. v6 A7에서 GraphRAG vs Vector 비교 실험 계획을 수립했으므로, community report의 필요성은 이 실험 결과에 따라 결정될 것이다.

**평가: 4.0/5.0** -- S-R-O 트리플은 그래프에 충실히 반영되었으나, GraphRAG 특유의 community report/graph traversal 기반 매칭은 아직 구체화되지 않았다. v6 A7 실험이 이를 결정할 예정이므로 합리적이다.

---

### 2.6 GraphDB 엔티티 구조 (v3 Ideation)

**v3에서 정의한 6개 노드와 5개 관계의 v6 반영 추적**:

| v3 노드 | v6 상태 | 변화 |
|---|---|---|
| `:Person` | **보존** | 속성에 role_evolution_pattern, primary_domain 추가 |
| `:Chapter` | **보존** | scope_type, evidence_chunk_embedding 추가, Experience와 통합 |
| `:Skill` | **보존** | category, aliases 추가, 정규화 전략 정의 |
| `:Role` | **보존** | name_ko, category 추가, 정규화 사전 전략 |
| `:Organization` | **대폭 강화** | v3에서 최소였던 것이 v4에서 stage_label 등 포함, v6에서 product_description, crawl_quality 등 크롤링 보강 속성 추가 |
| `:Outcome` | **보존 + 확정** | v3의 이중 설계(노드 vs 속성) → v4에서 별도 노드로 확정, outcome_type 분류 추가 |

| v3 관계 | v6 상태 | 변화 |
|---|---|---|
| `HAS_EXPERIENCED` | `HAS_CHAPTER`로 명칭 변경 | seq_order edge 속성 추가 |
| `NEXT_CHAPTER` | **보존** | gap_months edge 속성 추가 |
| `PERFORMED_ROLE` | **보존** | confidence edge 속성 추가 |
| `USED_SKILL` | **보존** | 유지 |
| `OCCURRED_AT` | **보존** | tenure_start, tenure_end, stage_at_tenure 추가 |

**v4/v6 신규 노드 및 관계**:

| 신규 항목 | 용도 | v3에서의 부재 해소 |
|---|---|---|
| `:SituationalSignal` 노드 | 같은 상황 경험 후보 탐색 | v3에서 Chapter 내부에 암묵적이던 상황 라벨을 공유 노드로 분리 |
| `:Vacancy` 노드 | 기업 측 매칭 앵커 | **v3 평가서(3.2절) "CompanyContext 노드가 없다" 해결** |
| `:Industry` 노드 | 산업 분류 공유 | v6 A2에서 스키마 정의, is_regulated 판정 기준 추가 |
| `NEEDS_SIGNAL` 관계 | Vacancy -> SituationalSignal | 기업이 필요로 하는 상황 경험을 그래프에서 탐색 가능 |
| `MAPPED_TO` 관계 | 매핑 결과 | MappingFeatures의 그래프 표현 |
| `IN_INDUSTRY` 관계 | 산업 분류 | 동종 산업 기업 탐색 |

**평가: 4.5/5.0** -- v3의 모든 노드/관계가 보존되었고, v3 평가서에서 지적한 "Company 측 모델링 부재"가 Vacancy, Organization 확장, Industry, NEEDS_SIGNAL로 해결되었다. Skill/Role 정규화 전략도 추가되었다.

---

### 2.7 MappingFeatures

**v3에서 정의한 7개 피처의 v6 추적**:

| v3 피처 | v6 상태 | 근거 |
|---|---|---|
| `stage_transition_match` | `stage_match`로 유지 + 계산 로직 확정 | STAGE_SIMILARITY 전체 매트릭스(A4) + 캘리브레이션 계획(A4-1) |
| `tension_alignment` | **v2로 이동** | structural_tensions가 v1에서 대부분 null이므로 합리적 |
| `vacancy_fit` | **보존** + 계산 로직 확정 | VACANCY_SIGNAL_ALIGNMENT 매핑 테이블로 구체화 |
| `domain_positioning_fit` | `domain_fit`으로 유지 | Embedding + industry code 하이브리드 계산 |
| `role_evolution_fit` | `role_fit`으로 유지 | ROLE_PATTERN_FIT + ScopeType-Seniority 매핑(A1) |
| `resilience_fit` | **v2로 이동** | failure_recovery가 v1에서 대부분 null이므로 합리적 |
| `culture_fit` | **보존** (대부분 INACTIVE 예상) | work_style_signals null 비율 70%+ 인정 |

**7 -> 5 피처 축소의 합리성**:

v3 평가서(3.4절)에서 "MappingFeatures 계산 방식 미정의"를 지적했고, v4에서 5개 피처의 계산 로직을 pseudo-code 수준으로 정의했다. 2개 피처(tension_alignment, resilience_fit)의 제거는 v1 데이터 가용성(structural_tensions, failure_recovery가 대부분 null)에 근거한 합리적 결정이며, v2 로드맵에 배치되어 있다.

**평가: 4.5/5.0** -- v3의 피처 개념이 모두 보존되었고, v3에서 완전히 미정의였던 계산 로직이 구현 가능한 수준으로 구체화되었다. 축소는 현실적이고 문서화된 결정이다.

---

### 2.8 문화 Proxy Facets (v3: 8개)

**v3에서 정의한 8개 facets의 v6 추적**:

| v3 Facet | v1 상태 | v2 계획 | 비고 |
|---|---|---|---|
| 9.1 Execution Speed | **v1 포함** | 유지 | v6에서 keyword + OPERATIONAL_CONTEXT 검증 강화 |
| 9.2 Autonomy & Ownership | **v1 포함** | 유지 | |
| 9.3 Process Discipline | **v1 포함** | 유지 | |
| 9.4 Quality & Reliability Bias | v2로 이동 | 8 facets 확장 시 | |
| 9.5 Experimentation & Learning | v2로 이동 | 8 facets 확장 시 | |
| 9.6 Collaboration Structure | v2로 이동 | 8 facets 확장 시 | |
| 9.7 Risk Tolerance & Innovation | v2로 이동 | 8 facets 확장 시 | |
| 9.8 Transparency & Feedback | v2로 이동 | 8 facets 확장 시 | |

v3에서 8개 facets를 정의했으나 v1 MVP(11.1절)에서 이미 "facet 3개만(speed/autonomy/process)"으로 축소한 것을 v4가 그대로 따랐다. 즉, **v3 자체의 v1 범위 정의에 충실**한 것이다.

v6에서의 추가 강화:
- `is_actionable_signal` 로직에 OPERATIONAL_CONTEXT 검증 추가 (S-1)
- P3 프롬프트에 광고성 필터 규칙 직접 내장 (C-1)
- facet score 병합 규칙 확정 (D-3) -- JD + 크롤링 통합 시 합의/충돌 처리

**평가: 4.0/5.0** -- v3 자체의 v1 범위(3 facets)에 충실하며, 추출 품질 향상(광고성 필터, 운영 컨텍스트 검증)이 추가되었다. 8 facets 확장은 v2 로드맵에 명시되어 있다.

---

### 2.9 버전/재현성 (Versioning)

**v3 원문**: "모든 산출물에 context_version, dataset_version, code_sha, generated_at를 필수 포함"

| 필드 | v6 반영 | 위치 |
|---|---|---|
| `context_version` | **보존** | `_meta.context_version` |
| `dataset_version` | **보존** | `_meta.dataset_version` |
| `code_sha` | **보존** | `_meta.code_sha` |
| `generated_at` | **보존** | `_meta.generated_at` |
| `sources_used` | **v4 추가** | `_meta.sources_used` -- 어떤 소스가 사용되었는지 추적 |
| `completeness` | **v4 추가** | `_meta.completeness` -- fill_rate, missing_fields |

**평가: 5.0/5.0** -- v3의 4개 필수 메타데이터가 모두 보존되고, 2개 추가 메타데이터로 강화되었다.

---

### 2.10 v3의 확장 모듈 (v2 이후)

v3 10절에서 제시한 5개 확장 모듈의 v6 반영 추적:

| v3 확장 모듈 | v6 대응 | 상태 |
|---|---|---|
| StageTransitionContext | stage_label taxonomy + STAGE_SIMILARITY 매트릭스 | v1에서 기본 구현, v2에서 taxonomy 확장 예정 |
| CultureContext | operating_model 3 facets + 광고성 필터 | v1에서 3 facets, v2에서 8 facets 확장 예정 |
| RoleScopeContext | scope_type + ScopeType-Seniority 매핑(A1) | v1에서 기본 구현 |
| ImpactContext | Outcome 노드 (outcome_type + metric_value) | v1에서 구현 |
| RiskConstraintContext | is_regulated_industry + structural_tensions taxonomy(A6) | v1에서 부분 구현, v2에서 확장 |

**평가: 4.0/5.0** -- 모든 확장 모듈이 v1 기본 구현 또는 v2 로드맵에 배치되어 있다. v3의 구상이 폐기되지 않고 계획적으로 단계 배분되었다.

---

## 3. v3 평가서 권장사항 반영 추적

v3 평가서(v4/v3_evaluation.md)에서 제시한 10개 액션 아이템의 해결 상태:

### 즉시 (Phase 0 진입 전)

| # | 권장 액션 | v6 해결 상태 | 근거 |
|---|---|---|---|
| 1 | 두 문서의 통합 스키마 작성 | **해결** | v4 `04_graph_schema.md`에서 Company+Candidate 양쪽 포함 통합 스키마 작성 |
| 2 | 기업 데이터 수집 전략 확정 | **해결** | v5/v6 `01_crawling_strategy.md`에서 T3/T4 크롤링 전략 상세 정의 |
| 3 | GraphDB 기술 스택 선정 | **해결** | v4 `04_graph_schema.md` 6절에서 Neo4j AuraDB 권장 |
| 4 | LLM 추출 PoC (JD 50건 + 이력서 100건) | **파일럿으로 위임** | v4/v6 실행 계획에서 파일럿(기업 20개)로 포함 |

### Phase 0 중

| # | 권장 액션 | v6 해결 상태 | 근거 |
|---|---|---|---|
| 5 | confidence 캘리브레이션 기준 정의 | **해결** | v4 `01_company_context.md` 5절 6단계 기준 + v6 카테고리별 ceiling |
| 6 | MappingFeatures 계산 로직 pseudo-code | **해결** | v4 `03_mapping_features.md` 전체가 이 목적 |
| 7 | DS/MLE 소비자 인터뷰 -> 인터페이스 확정 | **부분 해결** | v4에서 BigQuery 테이블 스키마 + SQL 예시 제공, 실제 인터뷰는 미확인 |
| 8 | baseline 시스템 구축 (LLM + Vector DB) | **실험 계획 수립** | v6 A7에서 GraphRAG vs Vector 비교 실험 계획 |

### Phase 1 이후

| # | 권장 액션 | v6 해결 상태 | 근거 |
|---|---|---|---|
| 9 | GraphRAG vs baseline ablation | **실험 계획 수립** | v6 A7 (파일럿 50건 후 paired t-test) |
| 10 | Company 측 그래프 모델링 완성 | **해결** | v4 `04_graph_schema.md`에서 Organization, Vacancy, Industry 노드 + 6개 관계 정의 |

**해결율: 8/10 완전 해결, 2/10 계획 수립(파일럿 의존)**

---

## 4. v3 -> v6 진화에서의 의도적 축소/변형 목록

v3 대비 의도적으로 축소 또는 변형된 항목과 그 합리성:

| 항목 | v3 | v6 | 축소 근거 | 합리성 |
|---|---|---|---|---|
| 문화 facets | 8개 | 3개 (speed, autonomy, process) | v3 자체의 v1 MVP 범위(11.1절) | 합리적 -- v3의 자체 계획과 일치 |
| MappingFeatures | 7개 피처 | 5개 피처 | tension_alignment, resilience_fit의 입력 데이터 null 비율 | 합리적 -- v2 로드맵 배치 |
| CompanyTalentSignal | v1.1+ 옵션 | v2로 이동 | 표본 크기 부족, 독립성 원칙 강화 | 합리적 -- A3에서 명문화 |
| Closed-loop Enrichment | v3 8.5절 정의 | v2로 이동 | v1 파이프라인 안정화 우선 | 합리적 |
| PastCompanyContext 시점 보정 | 재직 당시 시점 역산 | 현재 시점 NICE 데이터만 사용 | Wayback Machine 등 과거 데이터 확보 비현실적 | 합리적 -- v3 평가서(3.5절) 권장과 일치 |
| GraphRAG community report | 문서에 명시 | 미구체화 | GraphRAG ROI 검증 필요 | 합리적 -- A7 실험으로 결정 예정 |
| Company 간 관계 | v3 평가서에서 지적 | v2로 이동 | 데이터 소스 부재, MappingFeatures 직접 기여 없음 | 합리적 -- A5에서 명문화 |
| operating_model 스케일 | v3: 1~5 정수 | v4: 0.0~1.0 실수 | 연속값이 ML 파이프라인에 적합 | 개선 |

모든 축소/변형이 명확한 근거와 함께 문서화되어 있으며, v2 로드맵에 복원 계획이 배치되어 있다.

---

## 5. v6에서 v3를 넘어선 강화 사항

v3에는 없었으나 v4~v6에서 추가된 가치:

| 항목 | 내용 | v3에서의 부재 |
|---|---|---|
| 데이터 소스 Tier 시스템 | T1~T7 소스별 confidence ceiling | v3은 소스 신뢰도 "높음/중간/낮음"만 구분 |
| 추출 방법 명시 | 각 필드별 LLM / Rule / Lookup 명시 | v3은 추출 방법 미정의 |
| Graceful Degradation | 피처별 ACTIVE/INACTIVE 상태 + 자동 비활성화 | v3은 부분 완성 원칙만 있고 피처 수준 대응 없음 |
| SituationalSignal 14개 taxonomy | 고정 taxonomy로 LLM 추출 일관성 확보 | v3은 자유 텍스트 signal |
| structural_tensions 8개 taxonomy | v6 A6에서 확정 + 배타성 가이드 | v3은 3개 예시만 |
| BigQuery 서빙 인터페이스 | 테이블 스키마 + SQL 예시 | v3은 "테이블 조인 vs API" 미확정 |
| 크롤링 전략 | 홈페이지 6개 유형 + 뉴스 5개 유형 + 추출 프롬프트 + 비용 추정 | v3은 데이터 수집 전략 전무 |
| 해시 기반 변경 감지 | 재크롤링 시 불필요한 LLM 호출 방지 | v3에 운영 전략 없음 |
| GraphRAG vs Vector 비교 실험 | A7에서 실험 설계 구체화 | v3에서 "GraphRAG가 정말 필요한가" 미검증 |

---

## 6. 잔여 격차 (v3 대비 v6에서 아직 미해결)

| 항목 | v3 원문 참조 | 현재 상태 | 해결 계획 |
|---|---|---|---|
| GraphRAG community report | 4절: "community report를 생성해 Context Profile을 산출" | 미구체화 | v6 A7 실험 결과에 따라 결정 |
| 필드 단위 coverage/source_diversity | 8.4절: "claim/field 단위로 coverage, freshness, source_diversity를 함께 관리" | completeness.fill_rate으로 간접 관리만 | v2 |
| Closed-loop Enrichment | 8.5절: "missing_fields 기반으로 타겟 질문을 생성" | source_type enum만 정의(enrichment_qa) | v2 |
| LinkedIn 접근 정책 | 후보 소스 T3 | 미확인 상태 유지 | 정책 확인 필요 |
| 검색 쿼리 패턴(Cypher) 확장 | v3 평가서 5.2절: "검색 쿼리 패턴 미정의" | v4에서 4개 쿼리 예시 제공, 운영 수준 쿼리 셋은 미확정 | v1 구현 시 |

---

## 7. 결론

### v3 설계 철학의 v6 계승도: 4.5 / 5.0

v3가 제시한 **"맥락은 궤적이다"**, **"Evidence-first"**, **"독립 생성"** 이라는 3대 설계 철학은 v6까지 **완벽하게 보존**되었다. v3의 개념적 프레임워크(Chapter, S-R-O Triple, 8 facets, 7 features)는 v4에서 구현 가능한 형태로 구체화되었고, v5/v6에서 크롤링 전략과 보완 사항을 통해 **실행 가능한 수준**으로 완성되었다.

### v3 -> v6의 핵심 진화 요약

```
v3 (개념 설계)
  "무엇을 만들어야 하는가"에 대한 훌륭한 답
  ↓
v3 평가서 (현실성 검증)
  "어떻게 만들 것인가"의 격차 식별 (6개 리스크, 10개 액션)
  ↓
v4 (구현 재정의)
  스키마 구체화 + 추출 로직 pseudo-code + 통합 Graph 스키마
  ↓
v5 (크롤링 전략 + 보완)
  데이터 수집 전략 + 6개 Amendment로 v4 미비점 해소
  ↓
v6 (실행 가능 완성)
  v5 리뷰 13건 100% 반영 + GraphRAG 실험 계획
  = "파일럿 실행 승인 가능" 수준
```

v3의 야심적 구상 중 현실적으로 축소된 부분(8->3 facets, 7->5 features, CompanyTalentSignal 제외 등)은 모두 **v3 자체의 v1 MVP 범위**이거나 **v3 평가서의 권장사항**에 부합하는 결정이며, v2 로드맵에 복원 계획이 배치되어 있다.

**v3의 가장 큰 약점이었던 "데이터를 어디서 가져올 것인가"**는 v5/v6의 크롤링 전략을 통해 해결되었다. v3 -> v6의 진화는 "개념적 설계 -> 구현 가능한 시스템"으로의 성공적 전환이라 평가할 수 있다.
