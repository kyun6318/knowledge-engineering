# v5 계획 ↔ v10 온톨로지 교차 검증 리뷰

> v5 실행 계획(02.create-kg/plans/v5/, 5개 문서)은 v4 온톨로지 기준으로 작성되었으나,
> 온톨로지 스키마가 v10(01.ontology/schema/v10/, 7개 문서)으로 진화함.
> v5~v10 사이에 추가된 Industry 노드, 크롤링 전략, 엣지 타입, Embedding 모델 확정 등이
> v5 계획에 반영되지 않아 교차 검증을 수행한다.
>
> 리뷰일: 2026-03-08

---

## 종합 평가 요약

| 항목 | 상태 | 설명 |
|---|---|---|
| **v4 온톨로지 정합** | 우수 | v5 계획은 v4 원본 스키마에 정확히 정합 |
| **v10 온톨로지 정합** | **불일치 다수** | v5→v10 사이 17건의 불일치 식별 (HIGH 6, MEDIUM 5, LOW 6) |
| **v6 계획 필요 여부** | **필요** | HIGH 6건은 파이프라인 구조/스키마에 직접 영향 |

---

## 1. HIGH — v6 필수 반영 (6건)

### H-1. Industry 노드 + IN_INDUSTRY 엣지 누락

| 항목 | 내용 |
|---|---|
| **v5 상태** | 8개 노드(Person, Organization, Chapter, Role, Skill, Outcome, SituationalSignal, Vacancy)만 참조 |
| **v10 상태** | 9개 노드 — `Industry` 노드 추가 (04_graph_schema §1.9), `IN_INDUSTRY` 엣지 추가 (§2.2) |
| **v10 참조** | `01.ontology/schema/v10/04_graph_schema.md` §1.9, §2.2, Q5 |
| **v5 참조** | `02_extraction_pipeline.md` §4.1 (CompanyContext → Graph) |
| **영향** | Pipeline C의 Graph 적재 코드에 Industry 노드 MERGE + Organization→Industry 관계 생성 누락 |
| **영향 범위** | 02 §4.1, 04 Phase 1-4 |

**권장 조치**:
1. v10의 Industry 노드 스키마를 Pipeline C에 반영 — NICE 업종 코드 기반 마스터 데이터 사전 생성
2. Organization 노드 생성 시 `IN_INDUSTRY` 관계 자동 생성
3. Phase 1-4 체크리스트에 Industry 노드 적재 + Q5 쿼리 테스트 추가

```python
# 추가 필요한 코드 (02 §4.1에 삽입)
# Industry 마스터 노드 (사전 생성)
tx.run("""
    MERGE (ind:Industry {industry_id: $industry_id})
    SET ind.label = $label, ind.category = $category,
        ind.category_label = $category_label,
        ind.is_regulated = $is_regulated
""", ...)

# Organization → Industry 관계
tx.run("""
    MATCH (o:Organization {org_id: $org_id})
    MATCH (ind:Industry {industry_id: $industry_code})
    MERGE (o)-[:IN_INDUSTRY]->(ind)
""")
```

---

### H-2. Embedding 모델 불일치

| 항목 | 내용 |
|---|---|
| **v5 상태** | 후보 3개: `text-embedding-3-small` (OpenAI) / Cohere embed-multilingual-v3.0 / BGE-M3 — Phase 0에서 비교 후 결정 |
| **v10 상태** | `text-multilingual-embedding-002` (Vertex AI)로 **확정** (v8 변경) |
| **v10 참조** | `04_graph_schema.md` §5 ("v1 채택: text-multilingual-embedding-002"), `05_evaluation_strategy.md` §2.1 |
| **v5 참조** | `02_extraction_pipeline.md` §4.5, `04_execution_plan.md` Phase 0-2 Embedding 모델 비교 |
| **영향** | Phase 0 PoC의 Embedding 모델 비교 대상이 v10 확정 모델을 포함하지 않음 |
| **영향 범위** | 02 §4.5, 03 §2 (비용 추정), 04 Phase 0-2 |

**권장 조치**:
1. Embedding 모델 후보를 v10 확정 모델(`text-multilingual-embedding-002`)로 교체
2. Phase 0 PoC의 비교 대상을 `text-multilingual-embedding-002` (확정) vs 대안 1~2개로 변경
3. 비용 추정을 Vertex AI Embedding API 가격 기준으로 갱신
4. 04 Phase 0-2의 의사결정 표에서 "Embedding 모델 선택" → "Embedding 모델 확정 검증"으로 변경

---

### H-3. 크롤링 파이프라인 부재

| 항목 | 내용 |
|---|---|
| **v5 상태** | Phase 3에 "크롤링/투자DB 연동" 한 줄 언급, 상세 계획 없음 |
| **v10 상태** | `06_crawling_strategy.md` — 전체 크롤링 전략 확정 (T3 홈페이지 6개 페이지 유형, T4 뉴스 5개 카테고리, 프롬프트 완비, 실행 계획 4 Phase) |
| **v10 참조** | `01.ontology/schema/v10/06_crawling_strategy.md` 전체 |
| **v5 참조** | `04_execution_plan.md` Phase 3-1 (3줄) |
| **영향** | v10에서 크롤링이 v1.1로 구체화되었으나, v5 계획에는 이 전략이 Phase 3에 포함되어 있어 Phase/일정 설계가 v10과 정합하지 않음 |
| **영향 범위** | 04 Phase 3 전체, 02 Pipeline A (CompanyContext 보강) |

**권장 조치**:
1. v10 `06_crawling_strategy.md`의 4 Phase 실행 계획을 v5 Phase 3에 인라인 반영 또는 참조 추가
2. Pipeline A에 크롤링 데이터 병합 경로 추가 (stage_estimate, domain_positioning, structural_tensions 보강)
3. 04_graph_schema v10의 Organization 크롤링 보강 속성(product_description, market_segment 등)을 Pipeline C에 반영
4. Phase 2~3 경계에 "크롤링 파이프라인 구축" 태스크 명시

---

### H-4. structural_tensions 8-type taxonomy 미참조

| 항목 | 내용 |
|---|---|
| **v5 상태** | Pipeline A에서 `structural_tensions=None` 고정, "v1에서 null, 외부 데이터 필요"로만 기술 |
| **v10 상태** | 8-type taxonomy 확정 + T4(뉴스) 소스에서 30~50% 활성화 가능 + 크롤링 N4 프롬프트 완비 |
| **v10 참조** | `01_company_context.md` §2.2 structural_tensions, `02_v4_amendments.md` A6, `06_crawling_strategy.md` N4 |
| **v5 참조** | `02_extraction_pipeline.md` §1 (Pipeline A), `04_execution_plan.md` Phase 1-2 |
| **영향** | v10에서 structural_tensions의 taxonomy와 추출 방법이 구체화되었으나, v5 계획에서는 여전히 null로 처리 |
| **영향 범위** | 02 Pipeline A, MappingFeatures의 tension_alignment 피처 활성화 시기 |

**권장 조치**:
1. v5 Pipeline A CompanyContextPipeline에 structural_tensions 추출 분기 추가 (크롤링 데이터 유입 시)
2. 8-type taxonomy(`tech_debt_vs_features`, `speed_vs_reliability` 등)를 Pydantic 스키마에 반영
3. Phase 3에서 크롤링 활성화 시 tension_alignment 피처 활성화 로드맵 명시
4. 배타성 가이드(v10 A6)와 related_tensions 구조를 pipeline 설계에 반영

---

### H-5. REQUIRES_ROLE 엣지 미반영

| 항목 | 내용 |
|---|---|
| **v5 상태** | Vacancy→Skill (`REQUIRES_SKILL`), Vacancy→SituationalSignal (`NEEDS_SIGNAL`)만 구현 |
| **v10 상태** | `Vacancy→REQUIRES_ROLE→Role` 엣지 추가 (seniority 속성 포함) |
| **v10 참조** | `04_graph_schema.md` §2.2 기업 측 관계 테이블 |
| **v5 참조** | `02_extraction_pipeline.md` §4.1 `load_company_to_graph()` |
| **영향** | Graph에서 "포지션이 요구하는 역할"을 탐색할 수 없음. role_fit 계산 시 Graph 경유 불가 |
| **영향 범위** | 02 §4.1, MappingFeatures F5(role_fit) |

**권장 조치**:
```python
# 02 §4.1 load_company_to_graph()에 추가
# Vacancy -[:REQUIRES_ROLE]-> Role
if company_ctx.vacancy.role_title:
    tx.run("""
        MERGE (r:Role {name: $role_name})
        MATCH (v:Vacancy {vacancy_id: $vacancy_id})
        MERGE (v)-[:REQUIRES_ROLE {seniority: $seniority}]->(r)
    """, role_name=normalize_role(company_ctx.vacancy.role_title),
        vacancy_id=..., seniority=company_ctx.vacancy.seniority)
```

---

### H-6. MAPPED_TO 엣지 Graph 미반영

| 항목 | 내용 |
|---|---|
| **v5 상태** | MappingFeatures 결과를 BigQuery에만 적재, Graph에는 미반영 |
| **v10 상태** | `Vacancy→MAPPED_TO→Person` 관계 정의 (overall_score, generated_at 속성) |
| **v10 참조** | `04_graph_schema.md` §2.3 매핑 관계 |
| **v5 참조** | `02_extraction_pipeline.md` §5 Pipeline D/E |
| **영향** | Graph 기반 매핑 결과 탐색(예: "이 포지션에 매핑된 후보 Top-10") 불가 |
| **영향 범위** | 02 Pipeline D/E, 04 Phase 1-5 |

**권장 조치**:
1. Pipeline D/E에 MAPPED_TO 관계 생성 단계 추가
2. BigQuery 적재와 병행하여 Graph에도 매핑 결과 반영
3. Phase 1-5 체크리스트에 MAPPED_TO 관계 적재 + 검증 추가

```python
# Pipeline D/E에 추가
tx.run("""
    MATCH (v:Vacancy {vacancy_id: $vacancy_id})
    MATCH (p:Person {person_id: $person_id})
    MERGE (v)-[m:MAPPED_TO]->(p)
    SET m.overall_score = $score, m.generated_at = datetime()
""", ...)
```

---

## 2. MEDIUM — v6 반영 권장 (5건)

### M-1. operating_model facets 개수 불일치

| 항목 | 내용 |
|---|---|
| **v5 상태** | 02 §2.4에서 `FACET_KEYWORDS`를 순회하며 facets를 추출 — 개수 미명시 (v4 원본에서 "8개 facets" 참조) |
| **v10 상태** | "v1은 3개 facets" 명시 (`speed`, `autonomy`, `process`) |
| **v10 참조** | `01_company_context.md` §2.1 operating_model |
| **v5 참조** | `02_extraction_pipeline.md` §2.4 |
| **영향** | v5 코드의 `FACET_KEYWORDS` 딕셔너리가 3개(v1)인지 8개(v2)인지 모호 |

**권장 조치**: v5 §2.4에 `FACET_KEYWORDS = {"speed": [...], "autonomy": [...], "process": [...]}`로 v1 범위를 명시하고, 나머지 5개 facets는 v2 로드맵으로 기록.

---

### M-2. ScopeType→Seniority 변환 규칙 미참조

| 항목 | 내용 |
|---|---|
| **v5 상태** | MappingFeatures role_fit 계산 시 scope_type과 seniority를 직접 비교하는 로직 미정의 |
| **v10 상태** | A1 변환 규칙 확정 — IC→경력연수 기반 세분화, FOUNDER→HEAD 승격 규칙 포함 |
| **v10 참조** | `02_candidate_context.md` §2.1 ScopeType→Seniority 변환 규칙 |
| **v5 참조** | `02_extraction_pipeline.md` §5 Pipeline D (role_fit) |
| **영향** | role_fit 계산 시 scope_type↔seniority 간 변환이 누락되면 매칭 정확도 저하 |

**권장 조치**: v10의 `ic_to_seniority()`, `get_candidate_seniority()` 함수를 Pipeline D의 role_fit 계산에 통합.

---

### M-3. WorkStyleSignals 필드 누락

| 항목 | 내용 |
|---|---|
| **v5 상태** | `work_style_signals=None` (v1에서 대부분 null), `autonomy_preference`와 `process_tolerance`만 언급 |
| **v10 상태** | `experiment_orientation: Level | null`과 `collaboration_style: string | null` 필드 추가 |
| **v10 참조** | `02_candidate_context.md` §2.5 WorkStyleSignals |
| **v5 참조** | `02_extraction_pipeline.md` §3.3 CAREER_LEVEL_PROMPT |
| **영향** | LLM 추출 프롬프트에 experiment_orientation, collaboration_style 추출이 누락 |

**권장 조치**: v5 §3.3의 CAREER_LEVEL_PROMPT에 `experiment_orientation`과 `collaboration_style` 추출 항목 추가. v1에서 대부분 null이더라도 프롬프트에는 포함해야 추출 기회를 놓치지 않음.

---

### M-4. Evidence source tier 체계 미참조

| 항목 | 내용 |
|---|---|
| **v5 상태** | Evidence에 source_type, confidence를 개별 설정하지만 Tier 체계 미참조 |
| **v10 상태** | T1~T7 7단계 소스 Tier 정의 + confidence ceiling 규칙 확정 |
| **v10 참조** | `01_company_context.md` §1 데이터 소스 Tier 정의, `02_candidate_context.md` §0 |
| **v5 참조** | `02_extraction_pipeline.md` §2.1, §8.2 |
| **영향** | confidence 값이 source ceiling을 초과할 수 있음 (예: NICE 소스인데 confidence 0.90 설정) |

**권장 조치**:
1. Evidence 생성 시 `field_confidence = min(extraction_confidence, source_ceiling)` 규칙 적용
2. T4 카테고리별 ceiling 예외 규칙(funding 0.65, performance 0.60) 반영
3. 복수 소스 부스트 규칙(`boosted = min(max(c1, c2) + 0.10, 0.95)`) 구현

---

### M-5. Facet merge 로직 부재

| 항목 | 내용 |
|---|---|
| **v5 상태** | operating_model facets를 JD 키워드 + LLM 보정으로만 계산, 외부 데이터 병합 로직 없음 |
| **v10 상태** | 크롤링 데이터(홈페이지 P3 채용 페이지, P4 기술 블로그) 병합 규칙 확정 |
| **v10 참조** | `06_crawling_strategy.md` P3 operating_model facets 보강 규칙, §5.4 facet score 병합 |
| **v5 참조** | `02_extraction_pipeline.md` §2.4 |
| **영향** | 크롤링 활성화 시 JD 기반 facet score와 크롤링 기반 score를 어떻게 병합할지 미정의 |

**권장 조치**: v10의 facet merge 규칙(threshold 0.20, 캘리브레이션 4단계)을 Pipeline A에 확장 포인트로 설계. 크롤링 비활성 시 JD 단독, 활성 시 병합 로직 분기.

---

## 3. LOW — 선택 반영 (6건)

### L-1. Chapter 필드명 불일치 (evidence_chunk)

| 항목 | 내용 |
|---|---|
| **v5 상태** | Chapter 노드에 `embedding_text` 필드명 사용 (02 §4.5) |
| **v10 상태** | `evidence_chunk` + `evidence_chunk_embedding` 필드명 사용 (04_graph_schema §1.3) |
| **영향** | 필드명 불일치 시 Vector Index 설정과 쿼리 불일치 |

**권장 조치**: v10의 `evidence_chunk` / `evidence_chunk_embedding` 필드명으로 통일.

---

### L-2. Organization 크롤링 보강 속성

| 항목 | 내용 |
|---|---|
| **v5 상태** | Organization 노드에 기본 속성만 정의 |
| **v10 상태** | v10에서 `product_description`, `market_segment`, `latest_funding_round`, `latest_funding_date`, `crawl_quality`, `last_crawled_at` nullable 속성 추가 |
| **영향** | v1에서 모두 null이므로 즉시 영향 없음. 단, Neo4j 스키마 선언 시 포함해 두면 v1.1 마이그레이션 불필요 |

**권장 조치**: Phase 0-3 인프라 셋업 시 v10의 Organization 확장 속성을 nullable로 선언.

---

### L-3. domain_positioning 상세 미반영

| 항목 | 내용 |
|---|---|
| **v5 상태** | `domain_positioning`을 `extract_domain(jd_text, nice)`로 간략히 처리 |
| **v10 상태** | `market_segment`, `competitive_landscape`, `product_description` 3개 하위 필드 정의 |
| **영향** | v1에서 JD 단독 추출 시 market_segment만 활성, 나머지는 null. 크롤링 활성화 시 보강 |

**권장 조치**: Pydantic 스키마에 3개 하위 필드를 Optional로 정의.

---

### L-4. CompanyTalentSignal 제외 명시 부재

| 항목 | 내용 |
|---|---|
| **v5 상태** | CompanyTalentSignal 언급 없음 |
| **v10 상태** | A3에서 의도적 제외 명문화 + v2 로드맵 배치 |
| **영향** | 계획 실행에 영향 없음. 문서 완전성 차원 |

**권장 조치**: 05_assumptions_and_risks.md에 "CompanyTalentSignal은 v1에서 의도적으로 제외 (v10 A3 참조)" 한 줄 추가.

---

### L-5. Company-to-Company 관계 로드맵 미참조

| 항목 | 내용 |
|---|---|
| **v5 상태** | Phase 3에서 간접적으로만 언급 |
| **v10 상태** | A5에서 4개 관계(`COMPETES_WITH`, `INVESTED_BY`, `ACQUIRED`, `PARTNERED_WITH`)의 도입 시기와 데이터 소스 명시 |
| **영향** | Phase 3 고도화 계획의 구체성 차원 |

**권장 조치**: 04 Phase 3에 v10 A5의 로드맵 표를 참조 추가.

---

### L-6. 평가 전략 power analysis 미참조

| 항목 | 내용 |
|---|---|
| **v5 상태** | Phase 2-2 품질 평가에 50건 수동 검증만 기술 |
| **v10 상태** | v10에서 사전 검정력 분석(power analysis) + 적응적 표본 크기 결정 프로토콜 추가 |
| **v10 참조** | `05_evaluation_strategy.md` §1.1 |
| **영향** | 50건 평가의 통계적 신뢰성 판단 기준이 v5에 부재 |

**권장 조치**: Phase 2-2에 v10의 power analysis 프로토콜 참조 추가.

---

## 4. 불일치 현황 요약

### 심각도별 분포

| 심각도 | 건수 | 핵심 특성 |
|---|---|---|
| **HIGH** | 6 | 파이프라인 코드/스키마 변경 필수 |
| **MEDIUM** | 5 | 품질/정합성 개선, 코드 수정 필요 |
| **LOW** | 6 | 문서 보완, 스키마 사전 선언 수준 |

### v5 문서별 영향 분포

| v5 문서 | HIGH | MEDIUM | LOW | 합계 |
|---|---|---|---|---|
| `02_extraction_pipeline.md` | 5 (H-1~H-6) | 5 (M-1~M-5) | 3 (L-1~L-3) | 13 |
| `04_execution_plan.md` | 3 (H-1,H-3,H-6) | 0 | 2 (L-5,L-6) | 5 |
| `05_assumptions_and_risks.md` | 0 | 0 | 1 (L-4) | 1 |
| `03_model_candidates_and_costs.md` | 1 (H-2) | 0 | 0 | 1 |
| `01_v1_gap_analysis.md` | 0 | 0 | 0 | 0 |

### v10 문서별 참조 분포

| v10 문서 | 참조 횟수 | 주요 불일치 |
|---|---|---|
| `04_graph_schema.md` | 8 | H-1, H-2, H-5, H-6, L-1, L-2 |
| `01_company_context.md` | 4 | H-4, M-1, M-4 |
| `02_candidate_context.md` | 3 | M-2, M-3, M-4 |
| `06_crawling_strategy.md` | 3 | H-3, H-4, M-5 |
| `05_evaluation_strategy.md` | 2 | H-2, L-6 |
| `02_v4_amendments.md` | 2 | H-4, L-4 |
| `03_mapping_features.md` | 1 | M-2 |

---

## 5. v6 계획 작성 시 우선순위 권장

### Phase 1: 즉시 반영 (v6 작성 시)

| 순서 | 항목 | 이유 |
|---|---|---|
| 1 | H-2 Embedding 모델 확정 | Phase 0 PoC 설계에 직접 영향, 비용 추정 기반 변경 |
| 2 | H-1 Industry 노드 | Graph 스키마 변경, Phase 1-4 적재 코드 수정 |
| 3 | H-5 REQUIRES_ROLE 엣지 | Graph 스키마 변경, 적재 코드 수정 |
| 4 | H-6 MAPPED_TO 엣지 | Pipeline D/E 변경, Phase 1-5 수정 |
| 5 | M-1~M-5 전체 | 코드/프롬프트 수정, 문서 보완 |

### Phase 2: 크롤링 활성화 시 반영

| 순서 | 항목 | 이유 |
|---|---|---|
| 1 | H-3 크롤링 파이프라인 | v10의 06_crawling_strategy와 정합 |
| 2 | H-4 structural_tensions | 크롤링 데이터 유입 시 활성화 |
| 3 | M-5 Facet merge | 크롤링 데이터 병합 로직 |

---

## 6. 최종 판정

> v5 계획은 **v4 원본 온톨로지에 정확히 정합**하나,
> v5→v10 사이의 스키마 진화(Industry 노드, Embedding 모델 확정, 크롤링 전략, 엣지 타입 추가 등)가
> **6건의 HIGH 불일치**를 발생시킨다.
>
> 이 불일치들은 파이프라인 코드와 Graph 스키마에 직접 영향을 미치므로,
> **v6 계획에서 필수 반영**해야 한다.
>
> 특히 H-2(Embedding 모델)는 Phase 0 PoC 설계를 변경하므로 **가장 먼저 반영**해야 하고,
> H-1/H-5/H-6은 Graph 적재 코드 수정이 필요하므로 **Phase 1-4 이전에 반영**해야 한다.
> H-3/H-4는 크롤링 활성화 시점(Phase 3 또는 v1.1)에 반영하면 충분하다.

### v6 계획 필요 여부: **필요**

v5→v10 온톨로지 간극을 해소하는 v6 계획이 필요하며, 위 17건의 불일치 사항을 체계적으로 반영해야 한다.
