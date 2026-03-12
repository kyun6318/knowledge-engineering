# v7 온톨로지 스키마 리뷰

> 리뷰 대상: 7개 문서
> - `ontology/schema/v7/01_company_context.md` (568줄)
> - `ontology/schema/v7/02_candidate_context.md` (631줄)
> - `ontology/schema/v7/02_v4_amendments.md` (561줄)
> - `ontology/schema/v7/03_mapping_features.md` (790줄)
> - `ontology/schema/v7/04_graph_schema.md` (392줄)
> - `ontology/schema/v7/05_evaluation_strategy.md` (1244줄)
> - `ontology/schema/v7/06_crawling_strategy.md` (1486줄)
>
> 리뷰 기준: v6 리뷰, v5 리뷰, v4 문서 4건, v3 평가서
>
> 리뷰일: 2026-03-08

---

## 1. 전체 평가

v7은 v6 리뷰의 **잔여 권장사항 8건 + 추가 개선 1건**을 반영한 통합판이다. 01~04 문서는 v4 원본에 amendments를 인라인 통합하여 단일 참조점을 제공하고, 05(evaluation_strategy)는 독립 문서로 확장, 06(crawling_strategy)는 v6에서 누적된 개선을 모두 포함한다.

| 평가 영역 | v6 점수 | v7 점수 | 변화 | 코멘트 |
|---|---|---|---|---|
| CompanyContext 완성도 | 4.5 | **4.5** | 0 | T4 ceiling 예외 통합, 의도적 제외 명문화 |
| CandidateContext 완성도 | 4.5 | **4.5** | 0 | A1 통합 완료, domain_depth evidence 누락 (아래 참조) |
| MappingFeatures 완성도 | 4.5 | **4.5** | 0 | STAGE_SIMILARITY 전체 매트릭스 + 캘리브레이션 통합 |
| Graph Schema 완성도 | 4.5 | **4.5** | 0 | Industry 노드, Company 간 관계 제외 명문화 |
| Evaluation Strategy | -- | **3.5** | 신규 | 피처명 불일치, 가상 데이터 혼동 우려 (아래 상세) |
| Crawling Strategy | 4.5 | **4.5** | 0 | S-4/S-5 해결, 집계 트리거 추가, 프롬프트 로드맵 |
| 문서 간 정합성 | 4.5 | **4.0** | -0.5 | 05 문서의 피처명 불일치, 임베딩 모델 불일치 발생 |
| **종합** | **4.5** | **4.3** | -0.2 | 01~04/06은 우수, 05 문서의 품질 이슈가 종합 점수를 하향 |

---

## 2. v6 리뷰 피드백 반영 상태

### 2.1 파일럿 중 검증 -- 5건

| # | v6 리뷰 항목 | v7 반영 상태 | 반영 위치 | 품질 |
|---|---|---|---|---|
| 1 | [C6-3] facet 병합 threshold 0.20 캘리브레이션 | **반영 완료** | 06, 4.4절 | 우수 -- 4단계 절차 + 의사결정 기준표 명시 |
| 2 | [S-4] 짧은 기사 관련성 필터 | **반영 완료** | 06, 3.3절 | 양호 -- 본문 길이 적응형 기준(200/500자 경계)으로 교체 |
| 3 | [S-5] 중복 제거 임계값 | **반영 완료** | 06, 3.3절 | 우수 -- 2단계 클러스터링(제목 유사도 + 핵심 엔티티) |
| 4 | [C6-1, C6-2] P4~P6, N2/N3/N5 프롬프트 추가 | **반영 완료** | 02_amendments A8 | 양호 -- 4단계 로드맵 + 안정화 판정 기준 |
| 5 | HTML 해시 vs 텍스트 해시 비교 | **반영 완료** | 06, 2.3절 | 우수 -- A/B 검증 계획 + text_hash 컬럼 추가 |

### 2.2 v1 운영 전 -- 3건

| # | v6 리뷰 항목 | v7 반영 상태 | 반영 위치 | 품질 |
|---|---|---|---|---|
| 6 | [A7-1] Vector baseline 구체화 | **반영 완료** | 02_amendments A7, 05 문서 전체 | 양호 -- 임베딩 모델/입력/통제변수 명시 |
| 7 | [V-6] T4 Tier ceiling 예외 반영 | **반영 완료** | 01, 1절 + 02_amendments A6 | 우수 -- 예외 조건 + 적용 함수 코드 포함 |
| 8 | 집계 Job 트리거 방식 정의 | **반영 완료** | 06, 5.3절 | 우수 -- Eventarc(Primary) + Cloud Scheduler(Backup) 이중 구조 |

**결과**: v6 리뷰의 8건 중 **8건 모두 반영 완료 (100%)**.

### 2.3 v7 추가 개선 -- 1건

| # | 항목 | 반영 위치 | 품질 |
|---|---|---|---|
| 9 | [C6-4] 서브도메인 탐색 스킵 조건 | 06, 2.3절 | 양호 -- P1~P3 확보 시 스킵 함수 + 정책 반영 |

---

## 3. 과도한 부분 (5건)

### [E-1] 05_evaluation_strategy.md 피처명 불일치 (심각도: 높음)

**문제**: 05 문서의 Step 1(graphrag_mapping 함수, :209행)과 Step 7(feature_contribution_analysis, :606행)에서 사용하는 MappingFeatures 이름이 03_mapping_features.md의 실제 피처명과 **완전히 다르다**.

| 05 문서의 피처명 | 03 문서의 실제 피처명 |
|---|---|
| `skill_gap_analysis` | (존재하지 않음) |
| `domain_relevance_score` | `domain_fit` (F3) |
| `growth_stage_fit` | `stage_match` (F1) |
| `seniority_transition_score` | `role_fit` (F5) |
| `industry_transition_readiness` | (존재하지 않음) |

5개 피처명 중 **5개 모두 불일치**한다. `skill_gap_analysis`와 `industry_transition_readiness`는 03 문서에 존재하지 않는 피처이다.

**영향**: 05 문서를 참조하여 구현하면 존재하지 않는 피처를 호출하게 된다. 03 문서와의 정합성이 완전히 깨진 상태.

**권장**: 05 문서의 모든 피처명을 03 문서 기준으로 교체:
- `skill_gap_analysis` -> 해당 없음 (제거 또는 `vacancy_fit`으로 매핑)
- `domain_relevance_score` -> `domain_fit`
- `growth_stage_fit` -> `stage_match`
- `seniority_transition_score` -> `role_fit`
- `industry_transition_readiness` -> 해당 없음 (제거 또는 `domain_fit`에 통합)

### [E-2] 05_evaluation_strategy.md 과도한 구현 코드 (심각도: 중간)

**문제**: 05 문서는 1,244줄에 달하는 실험 계획서인데, pseudo-code가 전체 분량의 약 60%를 차지한다. 특히:

- Step 2: Vector Baseline 구현 (:48~100행) -- 단순 cosine similarity 함수에 65줄
- Step 3: Vector + LLM Reranking (:268~363행) -- 프롬프트 구성 + 파싱에 100줄
- Step 4: 블라인드 처리 (:366~440행) -- 셔플 + ID 부여에 75줄
- Step 5: 전문가 평가 (:444~511행) -- 입력 수집 함수에 67줄
- Step 6: 통계 검정 (:515~594행) -- scipy.stats 호출에 80줄

이 코드들은 **설계 문서가 아닌 구현 코드** 수준이다. 실험 계획서에는 "무엇을 하는가"가 중요하지, "어떻게 구현하는가"는 과도하다.

**영향**: 문서 분량이 불필요하게 팽창하여 핵심 설계 의도를 파악하기 어렵다. 향후 유지보수 시 pseudo-code와 실제 구현 코드의 동기화 부담이 생긴다.

**권장**: pseudo-code를 핵심 로직 요약(함수 시그니처 + 주석 수준)으로 축소하고, 상세 구현은 별도 노트북/스크립트로 분리. 05 문서는 실험 설계 + 의사결정 트리에 집중.

### [E-3] 05_evaluation_strategy.md 가상 실험 데이터 (심각도: 높음)

**문제**: 05 문서 10절(:1095~1218행)에 **미수행 실험의 구체적 결과 수치**가 마치 실제 결과인 것처럼 제시되어 있다.

```
"method_A_graphrag": { "mean": 3.82, "std": 0.94, "median": 4.0 }
"method_B_vector": { "mean": 3.34, "std": 1.12 }
"paired_t_test_a_vs_b": { "t_statistic": 2.84, "p_value": 0.0062 }
"cohens_d": 0.48
```

또한 피처 기여도 분석에서 `domain_relevance_score`의 `correlation_with_overall: 0.68` 등 구체적 상관계수까지 제시한다. 이 수치들은 **2026-04월 이후 수행 예정인 실험의 가상 데이터**이다.

**영향**: 문서 독자가 실제 실험 결과로 오해할 수 있다. 특히 "p=0.0062, significant: true" 같은 구체적 통계치는 이미 GraphRAG의 우위가 입증된 것으로 착각하게 만든다. 더불어 E-1의 피처명 불일치가 가상 데이터에도 그대로 반영되어 있어, 잘못된 피처명이 "검증된 결과"처럼 고착될 위험이 있다.

**권장**: 10절의 데이터를 다음 중 하나로 처리:
1. **삭제**: 가장 깔끔한 방법. 실험 수행 후 실제 데이터로 대체
2. **명시적 표기**: 유지한다면 `[가상 예시 데이터 -- 실제 실험 결과가 아님]` 레이블을 눈에 띄게 추가

### [E-4] 문서 간 내용 3중 중복 (심각도: 중간)

**문제**: 동일한 내용이 여러 문서에 반복 기술되어 있다.

**tension taxonomy 3중 기술**:
1. `01_company_context.md` 2.2절 (:249~301행) -- 8개 taxonomy + 배타성 가이드 + TypeScript
2. `02_v4_amendments.md` A6절 (:289~431행) -- 동일 taxonomy + 배타성 가이드 + TypeScript + JSON 예시
3. `06_crawling_strategy.md` 3.2절 N4 (:570~631행) -- taxonomy enum이 프롬프트에 내장

**ScopeType -> Seniority 변환 2중 기술**:
1. `02_candidate_context.md` 2.1절 (:97~150행) -- 변환 규칙 + 코드
2. `02_v4_amendments.md` A1절 (:22~95행) -- 동일 변환 규칙 + 코드

**T4 Tier ceiling 예외 2중 기술**:
1. `01_company_context.md` 1절 (:46~74행) -- 예외 규칙 + 코드
2. `02_v4_amendments.md` A6절 (:373~417행) -- 동일 예외 규칙 + 코드

**영향**: 한 곳을 수정할 때 나머지도 동기화해야 하는 유지보수 부담. 불일치 발생 시 어느 문서가 정본인지 혼란.

**권장**: "통합판"인 01~04 문서를 정본(source of truth)으로 확정하고, amendments 문서에는 "01~04 문서 참조"로 간소화. 단, 06의 N4 프롬프트 내 taxonomy는 프롬프트 자체가 독립적으로 작동해야 하므로 중복 유지가 합리적.

### [E-5] 통합판 + amendments 이중 유지 (심각도: 낮음)

**문제**: 01~04 문서 헤더에 "v7 -- 통합판"이라고 명시되어 있고, amendments의 A1~A6까지를 인라인 통합했다. 그런데 `02_v4_amendments.md`도 여전히 A1~A6 원본 + A7~A8 신규를 모두 포함하고 있다.

**영향**: "통합판"이라면 amendments가 별도로 존재할 필요가 줄어든다. 특히 A1~A6는 통합판에 이미 반영되어 amendments에 남아 있으면 E-4의 중복을 심화시킨다.

**권장**: 두 가지 방안 중 택일:
1. amendments를 **A7~A8만 유지** (A1~A6 삭제, "통합판으로 이관됨" 명시)
2. amendments를 **변경 이력 문서로 전환** (패치 내용이 아닌 "무엇이 왜 바뀌었는지"만 기록)

---

## 4. 부족한 부분 (7건)

### [M-1] 임베딩 모델 불일치 (심각도: 중간)

**문제**: 두 문서에서 서로 다른 임베딩 모델을 참조한다.

| 문서 | 위치 | 임베딩 모델 |
|---|---|---|
| 04_graph_schema.md | 5절 Vector Index 전략 (:379행) | `text-embedding-3-small` (OpenAI) |
| 05_evaluation_strategy.md | 2.1절 (:39행) | `text-multilingual-embedding-002` (Vertex AI) |

04 문서의 5절에서는 "v1 후보: OpenAI text-embedding-3-small, Cohere embed-multilingual-v3.0"이라 하고, 05 문서에서는 "GCP 네이티브"를 이유로 Vertex AI 모델을 명시했다. 두 문서가 서로 다른 임베딩 모델을 참조하므로, 실제 구현 시 어떤 모델을 사용할지 모호하다.

**권장**: 임베딩 모델 선택을 한 곳(04 또는 별도 기술 선택 문서)에서 확정하고, 나머지 문서에서 참조. GCP 인프라를 사용하는 맥락에서는 `text-multilingual-embedding-002`가 합리적이나, 04 문서의 후보 목록도 업데이트 필요.

### [M-2] overall_match_score의 confidence 이중 감쇠 (심각도: 중간)

**문제**: `03_mapping_features.md` 4절(:601~633행)의 `compute_overall_score` 함수에서 confidence가 이중으로 작용한다.

1단계: 개별 피처 계산 시 source ceiling이 confidence에 반영됨 (예: `stage_match.confidence = 0.55`)
2단계: overall_match_score 계산 시 confidence를 **다시 가중치로 사용**

```python
weighted_sum = sum(
    active[k].score * normalized_weights[k] * active[k].confidence
    for k in active
)
weight_sum = sum(
    normalized_weights[k] * active[k].confidence
    for k in active
)
return weighted_sum / weight_sum
```

이 수식에서 confidence가 낮은 피처의 score가 과도하게 할인된다. 예를 들어 `stage_match`(score=0.78, confidence=0.55)와 `vacancy_fit`(score=0.85, confidence=0.65)가 있을 때, stage_match의 기여는 confidence 0.55로 두 번째 감쇠를 받는다. 그러나 이미 score 자체가 confidence를 고려하여 산출된 것이므로 이중 감쇠가 발생한다.

**수식 분석**: `weighted_sum / weight_sum` 구조는 실제로 confidence-weighted average이므로, 수학적으로는 단순 가중 평균과 동치이다. 그러나 score가 이미 confidence를 반영하여 보수적으로 산출된 경우(예: source ceiling 적용), overall에서 다시 confidence 가중을 하면 **low-confidence 피처가 과소 반영**된다.

**권장**: 설계 의도를 명확히 해야 한다:
- **의도적 이중 감쇠**: "low-confidence 피처는 overall에서도 덜 기여해야 한다"면 현재 수식이 맞으나, 그 의도를 문서에 명시
- **비의도적**: 단순 가중 평균 `sum(score * weight) / sum(weight)`로 변경하고, confidence는 별도 `overall_confidence` 지표로 보고

### [M-3] domain_depth에 Evidence 구조 누락 (심각도: 낮음)

**문제**: `02_candidate_context.md` 3절 JSON 스키마(:527~533행)에서 `domain_depth` 필드에 `evidence`가 없다.

```json
"domain_depth": {
    "primary_domain": "B2B SaaS",
    "domain_experience_count": 3,
    "description": "B2B SaaS 3개 회사에서 반복 경험, 결제/인프라 도메인 특화",
    "confidence": 0.65
}
```

반면 동일 문서의 다른 모든 구조체(`role_evolution`, `work_style_signals`, `outcomes` 등)는 `evidence` 필드를 가진다. 01 문서의 설계 원칙 "Evidence-first: 모든 claim에 근거 필수"와 불일치.

**권장**: `domain_depth`에 `evidence: Evidence[]` 필드를 추가. domain_depth는 전체 커리어를 종합한 판단이므로 여러 experience의 evidence를 참조할 수 있다.

### [M-4] NEEDS_SIGNAL 자동 추론 검증 계획 부재 (심각도: 낮음)

**문제**: `04_graph_schema.md` Q4(:327~351행)에서 Vacancy의 `NEEDS_SIGNAL` 관계를 LLM으로 자동 추론한다.

```python
jd_signals = llm_extract_signals_from_jd(vacancy.evidence_chunk)
signals = list(set(signals + jd_signals))
```

`SCOPE_TO_SIGNALS` 딕셔너리에 의한 rule-based 매핑은 검증 가능하지만, `llm_extract_signals_from_jd`의 결과는 LLM 의존적이다. 이 자동 추론의 정확도를 검증하는 계획이 어디에도 없다.

**영향**: NEEDS_SIGNAL이 부정확하면 Q1 쿼리(vacancy_fit 기반 후보 탐색)의 결과 품질이 저하된다.

**권장**: 파일럿에서 LLM 추론 NEEDS_SIGNAL과 rule-based NEEDS_SIGNAL을 비교하여 precision/recall 측정. 03 문서의 F2(vacancy_fit)에서 이미 `VACANCY_SIGNAL_ALIGNMENT` 테이블을 정의하고 있으므로, NEEDS_SIGNAL은 rule-based만으로도 충분할 수 있다.

### [M-5] tech_stack 정규화 사전 관리 방법 부재 (심각도: 낮음)

**문제**: `04_graph_schema.md` 1.4절(:76행)에서 Role 노드의 정규화 전략을 "동의어 사전 기반"이라 하고, 1.5절(:86행)에서 Skill 노드의 aliases를 정의했다. 그러나:

- 동의어 사전의 초기 범위 (몇 개의 기술/역할?)
- 사전 갱신 방법 (수동? 자동 감지?)
- 사전 관리 주체

가 정의되지 않았다. `02_candidate_context.md` 6절 로드맵(:621행)에서 "v1.1: 정규화 사전 확장"이라고만 언급.

**권장**: v1 파일럿 시 최소 사전 규모(예: 기술 200개, 역할 50개)와 갱신 프로세스를 정의. 파일럿에서 미매칭 비율을 측정하여 v1.1 확장 범위를 결정.

### [M-6] operating_model 8 facets 확장 로드맵 미정의 (심각도: 낮음)

**문제**: `01_company_context.md` 6절(:524행)에서 v2에서 operating_model을 "8 facets 확장"한다고 명시했으나, 추가될 5개 facet이 무엇인지 어디에도 정의되지 않았다. 현재 3개(speed, autonomy, process)만 정의.

**영향**: v2 설계 시 facet 정의부터 시작해야 하므로, 현재 시점의 로드맵으로서의 가치가 낮다.

**권장**: 후보 facet 목록이라도 명시 (예: collaboration, innovation, data-drivenness, transparency, customer-focus). 확정이 아닌 후보라도 v2 스코프 논의의 출발점이 된다.

### [M-7] PastCompanyContext 시점 보정 방법론 미정의 (심각도: 낮음)

**문제**: `02_candidate_context.md` 6절(:626행)에서 v2에서 past_company_context에 "시점 보정"을 도입한다고 했다. 그러나 보정 방법론이 어디에도 제시되지 않았다. 현재는 "NICE 현재 시점 데이터만 사용"(2.4절, :247행)하며, `stage_estimation_method: "nice_current"`로 한계를 인정하고 있다.

**영향**: v1에서는 문제없으나, v2 로드맵의 구체성이 부족. 시점 보정은 "현재 직원 150명인 회사가 후보 재직 당시에는 20명이었을 수 있다"는 근본적 문제이므로, 접근 방식의 방향성이라도 있어야 한다.

**권장**: v2 보정 후보 접근법을 1~2줄로 명시:
- 접근법 A: NICE 연도별 스냅샷(있는 경우) 활용
- 접근법 B: 설립년도 + 현재 규모로 성장 곡선 역추정
- 접근법 C: 투자 DB의 투자 시점 데이터로 당시 규모 추정

---

## 5. 문서 간 정합성 검증

### 5.1 v7 통합판 내부 정합성 (01~04)

| # | 항목 | 상태 | 설명 |
|---|---|---|---|
| I-1 | 01 tension taxonomy <-> 06 N4 프롬프트 | **정합** | 동일 8개 enum, 동일 배타성 가이드 |
| I-2 | 01 T4 ceiling 예외 <-> 06 CATEGORY_CEILING | **정합** | funding 0.65, performance 0.60 일치 |
| I-3 | 02 ScopeType 변환 <-> 03 F5 role_fit | **정합** | `get_candidate_seniority` 함수 참조 일치 |
| I-4 | 04 Industry 노드 <-> 01 is_regulated_industry | **정합** | 동일 4개 대분류 코드(K, Q, D, H) |
| I-5 | 03 STAGE_SIMILARITY <-> 02_amendments A4 | **정합** | 동일 4x4 매트릭스 |
| I-6 | 01 Evidence 통합 모델 <-> 02 Evidence 사용 | **정합** | 동일 interface, source_type enum 공유 |

### 5.2 01~04 <-> 05 정합성

| # | 항목 | 상태 | 설명 |
|---|---|---|---|
| I-7 | 03 피처명 <-> 05 피처명 | **불일치** | [E-1] 5개 피처명 모두 다름 |
| I-8 | 04 임베딩 모델 <-> 05 임베딩 모델 | **불일치** | [M-1] OpenAI vs Vertex AI |
| I-9 | 03 overall_match_score <-> 05 평가 지표 | **정합** | 동일 score 구조 참조 |

### 5.3 01~04 <-> 06 정합성

| # | 항목 | 상태 | 설명 |
|---|---|---|---|
| I-10 | 01 source_type enum <-> 06 evidence source_id | **정합** | crawl_site, crawl_news 일치 |
| I-11 | 01 structural_tensions <-> 06 N4 추출 프롬프트 | **정합** | taxonomy + related_tensions 구조 일치 |
| I-12 | 04 Organization 확장 속성 <-> 06 Graph 반영 | **정합** | product_description, market_segment 등 일치 |

---

## 6. 권장 사항 요약

### 즉시 조치 (v7.1 패치)

| # | 항목 | 심각도 | 근거 |
|---|---|---|---|
| 1 | [E-1] 05 문서 피처명을 03 문서 기준으로 교정 | 높음 | 구현 시 존재하지 않는 피처 호출 위험 |
| 2 | [E-3] 05 문서 10절 가상 데이터에 명시적 레이블 추가 | 높음 | 미수행 실험 결과로 오해 위험 |
| 3 | [M-1] 임베딩 모델 04 vs 05 불일치 해소 | 중간 | 구현 시 모호함 |

### 파일럿 중 검토

| # | 항목 | 심각도 | 근거 |
|---|---|---|---|
| 4 | [M-2] overall_match_score confidence 이중 감쇠 의도 명확화 | 중간 | 파일럿 결과로 영향도 확인 가능 |
| 5 | [M-3] domain_depth evidence 추가 | 낮음 | Evidence-first 원칙 일관성 |
| 6 | [M-4] NEEDS_SIGNAL 자동 추론 정확도 측정 | 낮음 | 파일럿 데이터 필요 |
| 7 | [M-5] tech_stack 정규화 사전 초기 범위 정의 | 낮음 | 파일럿 미매칭 비율로 판단 |

### 문서 구조 개선 (비긴급)

| # | 항목 | 심각도 | 근거 |
|---|---|---|---|
| 8 | [E-2] 05 문서 pseudo-code 축소 | 중간 | 문서 가독성 개선 |
| 9 | [E-4] tension taxonomy 등 3중 중복 해소 | 중간 | 유지보수 부담 경감 |
| 10 | [E-5] amendments A1~A6 정리 (통합판 이관 완료 표시) | 낮음 | 문서 구조 명확화 |
| 11 | [M-6] operating_model 확장 facet 후보 목록 | 낮음 | v2 로드맵 구체화 |
| 12 | [M-7] PastCompanyContext 시점 보정 접근법 후보 | 낮음 | v2 로드맵 구체화 |

---

## 7. 종합 점수

| 영역 | 점수 | 코멘트 |
|---|---|---|
| 01 CompanyContext | 4.5/5 | T4 ceiling 예외 통합, 의도적 제외 명문화 우수 |
| 02 CandidateContext | 4.5/5 | A1 통합 완료, domain_depth evidence만 보완 필요 |
| 02 Amendments | 4.0/5 | A7/A8 신규 양호, A1~A6 중복 정리 필요 |
| 03 MappingFeatures | 4.5/5 | STAGE_SIMILARITY 완성, confidence 이중 감쇠 명확화 필요 |
| 04 Graph Schema | 4.5/5 | Industry 노드 완성, 임베딩 모델 통일 필요 |
| 05 Evaluation Strategy | 3.5/5 | 피처명 불일치, 가상 데이터 혼동이 큰 감점 요인 |
| 06 Crawling Strategy | 4.5/5 | v6 잔여 모두 해결, 실행 계획 완성도 높음 |
| **종합** | **4.3/5** | 01~04/06은 파일럿 투입 가능, 05는 즉시 패치 필요 |

---

## 8. 결론

v7 문서 세트는 **01~04(스키마 정의)와 06(크롤링 전략)은 높은 완성도**를 보여주며, v6 리뷰 피드백 8건을 100% 반영했다. 특히 facet 병합 캘리브레이션 4단계, 2단계 중복 제거 클러스터링, 집계 Job 이중 트리거 구조는 실행 가능성을 크게 높였다.

**핵심 리스크**는 05_evaluation_strategy.md에 집중되어 있다:
1. MappingFeatures 피처명이 03 문서와 완전히 불일치하여, 이 문서를 참조한 구현이 실패할 위험이 있다
2. 가상 실험 데이터가 실제 결과로 오해될 수 있다
3. 1,244줄 중 과도한 pseudo-code가 핵심 설계를 가린다

**판정**: 05 문서의 [E-1], [E-3] 즉시 패치 후 **파일럿 실행 승인 가능**. 01~04/06은 현재 상태로 투입 가능.
