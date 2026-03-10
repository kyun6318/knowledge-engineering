# v3 온톨로지 설계 평가

> v3 문서 2건(Context Overview, GraphDB 엔티티 구조 Ideation)에 대한 타당성 및 구현 가능성 종합 평가
>
> 평가일: 2026-03-08

---

## 1. 총평

v3 설계는 **개념적으로 매우 탄탄한 프레임워크**를 제시한다. "맥락은 궤적이지 상태가 아니다"라는 핵심 정의, Chapter 기반 구조화, Evidence-first 원칙 등은 인재 추천 시스템의 근본적 한계(키워드 매칭)를 정확히 짚고 있다. 다만 **설계의 야심과 현실 데이터 가용성 사이의 격차**가 가장 큰 리스크이며, 두 문서 간 정합성 부족도 해결이 필요하다.

| 평가 항목 | 점수 (5점 만점) | 요약 |
|---|---|---|
| 개념적 타당성 | 4.5 | Chapter-Trajectory 모델은 독창적이고 문제를 정확히 해결 |
| 스키마 설계 완성도 | 4.0 | CompanyContext/CandidateContext 스키마 잘 정의, 일부 모호한 부분 존재 |
| 두 문서 간 정합성 | 2.5 | Context Overview와 GraphDB 엔티티 구조 사이에 상당한 괴리 |
| 데이터 가용성 대비 현실성 | 2.0 | 기업 데이터 수집 미비가 전체 파이프라인의 최대 병목 |
| 구현 가능성 (v1 MVP) | 3.0 | 축소된 v1 범위는 합리적이나, 전제 조건 충족이 불확실 |
| 운영/확장 고려 | 3.5 | 버저닝/품질 원칙은 우수, 실제 파이프라인 운영 설계는 미비 |

---

## 2. 강점 분석

### 2.1 Chapter-Trajectory 모델의 독창성

"기업의 미래 벡터 <-> 후보의 과거 경험 벡터" 매칭이라는 핵심 원리는 기존 스킬 매칭 / JD-이력서 유사도 방식과 본질적으로 다른 가치를 제공한다. 이는 실제 채용 의사결정자의 사고방식("이 단계를 겪어본 사람이 필요해")과 일치한다.

### 2.2 Evidence-first 원칙의 엄격성

모든 claim에 `source_id + span + source_type + confidence + extracted_at`를 강제하는 것은:
- LLM hallucination 방지
- 추천 근거의 투명성 확보
- downstream 시스템의 신뢰도 기반 가중치 조절 가능

이 세 가지를 동시에 해결하는 좋은 설계다.

### 2.3 부분 완성(Partial Completion) 정상화

Context를 "완성 or 미완성"이 아닌 "신뢰도가 표기된 부분 완성"으로 정의한 것은 현실적이다. `missing_fields`를 명시하고 confidence에 따라 feature weight를 자동 하향하는 설계는 데이터가 빈약한 초기에 시스템이 graceful하게 동작할 수 있게 한다.

### 2.4 CompanyContext와 CandidateContext의 독립성

후보 분포에 의한 기업 맥락 오염을 명확히 경계하고 `CompanyTalentSignal`로 분리한 것은 올바른 판단이다. Anti-pattern 방어 명문화는 향후 설계 드리프트를 방지한다.

### 2.5 문화 Proxy Facets의 관측 가능성

"수평적 문화" 같은 선언이 아닌, 키워드/행동 프록시 기반으로 문화를 수치화하려는 시도는 방향이 옳다.

---

## 3. 핵심 리스크 및 약점 분석

### 3.1 [Critical] 기업 데이터 가용성 — 최대 병목

**현재 상황**: NICE 기업 정보만 보유, 나머지는 수집 단계부터 필요.

**CompanyContext 생성에 필요한 데이터 vs 현실**:

| 데이터 소스 | 필요 정보 | 현재 상태 | 확보 난이도 |
|---|---|---|---|
| JD | vacancy chapter, role expectations | 크롤링 가능 | 중 (구조화 필요) |
| 회사 보유 기업 정보 | structural tensions, operating model | 미보유 | 상 (영업/파트너십 필요) |
| 회사 사이트/기사 크롤링 | stage, domain positioning | 미수집 | 중 (크롤러 구축 필요) |
| NICE 기업 정보 | 업력, 규모, 매출 | 보유 | 하 |
| 채용 히스토리 | vacancy pattern, 이직률 | 자사 데이터 활용 가능 | 중 |

**영향도**: CompanyContext의 핵심인 `Growth Trajectory`, `Structural Tensions`, `Operating Model`은 JD와 NICE만으로는 생성이 거의 불가능하다. JD에서 추출할 수 있는 것은 `vacancy_scope_type`과 `role_expectations` 정도이며, 기업의 변곡점이나 긴장은 내부 정보 없이 추론하기 어렵다.

**권장 사항**:
1. v1에서 CompanyContext의 범위를 **JD + NICE + 크롤링으로 추출 가능한 것**으로 재한정
2. `structural_tensions`는 v1에서 "Unknown" 비율이 70%+ 될 수 있음을 인정하고, 이것이 MappingFeatures에 미치는 영향을 시뮬레이션
3. 크롤링 파이프라인(회사 홈페이지, 뉴스 기사, 투자 정보)을 Phase 0에서 우선 구축
4. 투자 정보 DB (크런치베이스, 더브이씨 등) 연동을 고려 — stage/trajectory 추정에 유용

### 3.2 [Critical] 두 문서 간 정합성 부족

**Context Overview**와 **GraphDB 엔티티 구조**는 같은 시스템을 설계하면서 상당한 괴리가 있다.

| 항목 | Context Overview | GraphDB 엔티티 구조 |
|---|---|---|
| 범위 | Company + Candidate + Mapping | **인재(Candidate) 중심만** |
| Chapter 정의 | Situation + Trajectory + Tension + Intention | Situation + Period (단순화) |
| Outcome 위치 | Chapter 내부 또는 별도 피처 | 별도 Outcome 노드 |
| Evidence 구조 | `source_id + span + source_type + confidence + extracted_at` | `evidence_chunk` 속성 (비정규화) |
| Organization | PastCompanyContext (stage/scale/domain/operating_mode) | Organization 노드 (기업 성장 단계 속성) |
| 관계 풍부도 | 7개 피처 차원의 매핑 | 5개 기본 관계만 정의 |

**핵심 불일치**:
1. GraphDB 엔티티 구조에 **CompanyContext 노드가 없다** — 기업 측 그래프 모델링이 전혀 안 되어 있음
2. Evidence 저장 방식이 다름 — Context Overview는 정규화된 evidence 배열, GraphDB는 노드 내 chunk 속성
3. MappingFeatures의 그래프 표현이 없음 — Company와 Candidate 간 매핑이 그래프에서 어떻게 표현되는지 미정의

**권장 사항**: GraphDB 엔티티 구조를 Context Overview에 맞춰 대폭 보강하거나, 통합 문서를 새로 작성해야 한다.

### 3.3 [High] LLM 추출 품질의 불확실성

Context 생성의 핵심은 비정형 텍스트(JD, 이력서, 기사)에서 구조화된 Chapter 정보를 추출하는 것인데, 이는 전적으로 LLM에 의존한다.

**우려 사항**:

| 추출 대상 | 난이도 | 이유 |
|---|---|---|
| Skill/Tool | 낮음 | 명시적, 표준화 가능 |
| Role, Period | 낮음 | 이력서에 명시적 |
| Stage (Series A→B 등) | 중간 | JD에 직접 언급되는 경우 제한적 |
| Structural Tensions | 높음 | 암묵적, 해석 필요, 소스 자체가 부족 |
| Vacancy Chapter Type (0→1/1→10/reset) | 중간~높음 | JD 문맥에서 추론해야 함 |
| Situational Signals | 중간 | 이력서 표현 방식에 따라 편차 큼 |
| Failure & Recovery | 높음 | 후보가 자발적으로 기술하지 않는 정보 |
| Culture Proxy Facets | 중간~높음 | 키워드 기반이지만 광고성 필터링 어려움 |

**권장 사항**:
1. 추출 품질 벤치마크를 Phase 0에서 수행 — 샘플 JD 50건 + 이력서 100건으로 Human evaluation
2. 추출 프롬프트를 분야별/레벨별로 세분화 (시니어 개발자 JD vs 주니어 마케터 JD)
3. `confidence` 점수의 캘리브레이션 기준을 명시 (현재 문서에 없음)

### 3.4 [High] MappingFeatures 계산 방식 미정의

7개 피처(`stage_transition_match`, `tension_alignment` 등)의 **실제 계산 방법**이 정의되어 있지 않다.

- LLM이 직접 점수를 매기는 것인가? → 재현성/일관성 문제
- Embedding 유사도인가? → 어떤 레벨에서 임베딩하는지 미정
- Rule-based 조합인가? → 규칙 정의 필요
- Graph path 기반인가? → 어떤 path를 어떻게 스코어링하는지 미정

**권장 사항**: 각 피처의 계산 방식을 최소한 pseudo-code 수준으로 정의해야 한다. v1에서는 LLM scoring + rule-based 하이브리드가 현실적일 수 있다.

### 3.5 [Medium] PastCompanyContext 역산의 한계

이력서에서 재직 회사명 + 기간으로 해당 시점의 기업 맥락을 역산하는 것은 좋은 아이디어이나:

- **시점 특정의 어려움**: NICE 데이터는 "현재" 기업 정보이지 "2020년 당시" 정보가 아님
- **비상장/초기 기업**: 정보 자체가 없는 경우가 많음
- **크롤링 시점 데이터**: Wayback Machine 등 과거 데이터 확보가 현실적으로 어려움

**권장 사항**: v1에서는 PastCompanyContext를 "현재 시점 기업 정보" 기반으로만 생성하고, 시점 보정은 v2로 미루는 것이 현실적이다.

### 3.6 [Medium] GraphRAG 스택의 ROI 불확실

v1 MVP 범위에서 GraphRAG의 community report, graph traversal 등 풀스택이 정말 필요한지 검증이 필요하다.

**대안 비교**:

| 접근법 | 장점 | 단점 |
|---|---|---|
| Full GraphRAG (현 설계) | 관계 추론, community 발견, path 근거 | 구축 비용 높음, 튜닝 어려움 |
| LLM + Vector DB | 빠른 구축, 유연한 추출 | 관계 추론 약함, evidence 추적 약함 |
| Structured Extraction + Rule Engine | 재현성 높음, 해석 용이 | 표현력 제한, 새 패턴 대응 어려움 |
| Hybrid (Vector + 경량 Graph) | 균형 잡힌 접근 | 두 시스템 관리 부담 |

**권장 사항**: Phase 1에서 "GraphRAG가 단순 Vector 검색 대비 실제로 더 나은 MappingFeatures를 생산하는가"를 ablation으로 검증해야 한다. 이를 위해 baseline(LLM + Vector DB)을 먼저 빠르게 구축하는 것도 전략이다.

---

## 4. 구현 가능성 평가

### 4.1 v1 MVP 범위의 적정성

v1에서 제안한 최소 범위는 합리적이다:
- CompanyContext: stage 1개 + vacancy_scope_type + facet 3개
- CandidateContext: experience 1개 + signals 2~3개
- MappingFeatures: 4개 피처

다만 **전제 조건이 충족되지 않으면 이 축소된 범위조차 위험**하다:

| 전제 조건 | 충족 여부 | 비고 |
|---|---|---|
| JD 크롤링 파이프라인 | 미구축 | 구축 필요 |
| 기업 정보 크롤링 | 미구축 | 구축 필요 |
| NICE 데이터 접근 | 가능 | 활용 범위 제한적 |
| 자사 이력서 접근 | 가능 (추정) | 구조화 수준 확인 필요 |
| LinkedIn 이력서 접근 | 미확인 | 크롤링 정책/법적 이슈 확인 필요 |
| GraphRAG 프레임워크 선정 | 미정 | Microsoft GraphRAG / LlamaIndex 등 |
| Graph DB 선정 | 미정 | Neo4j / Neptune / NebulaGraph 등 |
| LLM 추출 프롬프트 개발 | 미착수 | 핵심 개발 항목 |

### 4.2 예상 병목 우선순위

1. **기업 데이터 수집** — 크롤링 + 투자정보 DB 연동 없이는 CompanyContext 자체가 빈약
2. **LLM 추출 품질** — Chapter/Signal 추출의 정확도가 전체 시스템 품질을 좌우
3. **GraphDB 스키마 확정** — 두 문서의 괴리를 해소한 통합 스키마 필요
4. **MappingFeatures 계산 로직** — 피처 계산 방식이 정의되어야 평가 가능
5. **DS/MLE 소비 인터페이스** — 실제 소비자의 요구사항 확인 필요

---

## 5. 문서별 세부 피드백

### 5.1 Context Overview

**잘된 점**:
- 시스템 경계 선언이 명확 ("GraphRAG는 피처 + 근거 공급까지")
- 데이터 품질 원칙 8개항이 구체적이고 실용적
- v1 vs v2 분리 기준이 명확

**보완 필요**:
- `confidence` 값의 산출 기준이 없음 (0.85가 무엇을 의미하는지?)
- `source_type` 열거형(enum)이 확정되지 않음
- MappingFeatures의 각 피처별 계산 pseudo-code 필요
- `operating_model.facets`의 점수 스케일(1~5? 0~1?)과 산출 방법 미정의
- Closed-loop Enrichment (8.5)가 v1인지 v2인지 불명확

### 5.2 GraphDB 엔티티 구조 Ideation

**잘된 점**:
- NEXT_CHAPTER 관계로 커리어 궤적을 보존하는 설계
- evidence_chunk + Vector Index 하이브리드 검색 전략
- Mermaid 예시가 직관적

**보완 필요**:
- **Company/Organization 측 모델링이 거의 없음** — CompanyContext, CompanyChapter가 그래프에 어떻게 표현되는지 정의 필요
- **Outcome 노드 vs evidence_chunk 속성의 이중 설계** — 어느 쪽이 정답인지 확정 필요
- **PRODUCED_OUTCOME 관계가 Context Overview의 evidence 구조와 불일치** — 통합 필요
- **edge 속성(properties) 미정의** — 관계에 confidence, period 등이 필요
- **Skill/Role 표준화 전략 부재** — "Python" vs "파이썬", "팀 리더" vs "Team Lead" 등 정규화 방안 필요
- **Company 간 관계 부재** — 경쟁사, 동종업계, 투자 관계 등이 그래프에 없음
- **검색 쿼리 패턴 미정의** — 어떤 Cypher/Gremlin 패턴으로 MappingFeatures를 생성하는지

---

## 6. 권장 액션 아이템

### 즉시 (Phase 0 진입 전)

| # | 액션 | 이유 |
|---|---|---|
| 1 | **두 문서의 통합 스키마 작성** | 현재 괴리가 구현 시 혼란 유발 |
| 2 | **기업 데이터 수집 전략 확정** | 최대 병목, 선행 없이 진행 불가 |
| 3 | **GraphDB 기술 스택 선정** | 스키마 설계가 DB 특성에 의존 |
| 4 | **LLM 추출 PoC (JD 50건 + 이력서 100건)** | 추출 품질이 전체 시스템 실현 가능성 결정 |

### Phase 0 중

| # | 액션 | 이유 |
|---|---|---|
| 5 | **confidence 캘리브레이션 기준 정의** | 0.85 같은 숫자의 의미가 불명확 |
| 6 | **MappingFeatures 계산 로직 pseudo-code 작성** | 피처 정의만으로는 구현/평가 불가 |
| 7 | **DS/MLE 소비자 인터뷰 → 인터페이스 확정** | 실제 소비 패턴 모르면 서빙 설계 불가 |
| 8 | **baseline 시스템 구축 (LLM + Vector DB)** | GraphRAG ROI 검증의 비교 대상 |

### Phase 1 이후

| # | 액션 | 이유 |
|---|---|---|
| 9 | **GraphRAG vs baseline ablation** | Full GraphRAG 투자 정당화 |
| 10 | **Company 측 그래프 모델링 완성** | 인재 중심만으로는 매칭 불가 |

---

## 7. 결론

v3 설계는 **"무엇을 만들어야 하는가"에 대한 답은 훌륭하게 제시**하고 있다. Chapter-Trajectory 기반 맥락 매칭이라는 핵심 아이디어는 차별화된 가치를 제공할 수 있다.

그러나 **"어떻게 만들 것인가"와 "데이터를 어디서 가져올 것인가"** 사이의 간극이 크다. 특히:

1. **기업 데이터 수집이 선행되지 않으면 CompanyContext 자체가 빈 껍데기**가 된다. NICE만으로는 stage/scale 팩트 정도만 채울 수 있고, 핵심인 trajectory/tension/operating_model은 불가능하다.
2. **두 설계 문서의 통합 없이 구현에 들어가면** GraphDB와 Context Layer가 따로 노는 시스템이 된다.
3. **LLM 추출 품질 검증 없이 파이프라인을 구축하면** 나중에 전면 재설계 리스크가 있다.

**권장 진행 순서**: 데이터 수집 전략 확정 → LLM 추출 PoC → 통합 스키마 확정 → Phase 0 → Phase 1 → Phase 2

v1을 "완벽한 시스템"이 아닌 **"가설 검증 도구"**로 포지셔닝하고, "Chapter 기반 매칭이 키워드 매칭보다 실제로 나은가?"라는 질문에 답할 수 있는 최소 파이프라인을 만드는 데 집중하는 것이 바람직하다.
