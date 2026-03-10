# v4 계획 종합 리뷰 — 실현 가능성, 과설계, 부족 설계 분석

> v4 계획 5개 문서를 독립적으로 심층 재검토한다.
> 00_v4_plan_review.md(v3 리뷰 반영 점검)와는 별도로, v4 계획 자체의 실현 가능성과 설계 품질을 분석한다.
>
> 리뷰일: 2026-03-08

---

## 1. 실현 가능성 분석

### 1.1 [High] 이력서 섹션 분할 및 경력 블록 분리의 난이도 과소평가

02 §3.1에서 이력서 파싱 후 "Rule 기반 섹션 분할 + 경력 블록 분리"를 제시하고, §3.2에서 정규식 패턴 예시를 보여준다. 그러나:

1. **한국어 이력서 포맷의 극단적 다양성**: 자유형식 서술, 표 기반, 반정형, PDF 양식(form field) 등 포맷이 통일되어 있지 않음
2. **경력 블록 경계 인식**: "회사명 + 기간" 패턴으로 블록을 분리한다고 하지만, 프로젝트 단위로 기술한 이력서, 회사 구분 없이 연속 서술한 이력서 등이 존재
3. **Rule 추출 성공률 추정 근거 부재**: 02 §3.2 하단에서 "company, role_title: 60-70% 커버"라 했으나 이 수치의 근거가 없음. 실제 한국어 이력서에서 이 패턴들의 커버리지를 실측한 데이터가 없다

**영향**: 경력 블록 분리가 실패하면 LLM에 올바른 입력을 줄 수 없고, 전체 CandidateContext 품질이 연쇄 하락한다. 05 §2.3(파싱+LLM 상관 리스크)에서 이를 인지하고 있으나, **Phase 0 PoC의 50건 테스트가 이 리스크를 충분히 검증하는지 불명확**하다.

**권장**: Phase 0 PoC 50건에서 "파싱 → 섹션 분할 → 경력 블록 분리" 단계의 성공률을 별도로 측정하고, Rule 커버리지가 50% 미만이면 LLM 기반 섹션 분할로 전환하는 fallback 전략을 명시할 것. 단, LLM 기반 섹션 분할 전환 시 이력서당 추가 ~1,000 토큰이 발생하므로 비용 영향($250~500 증가)도 함께 평가해야 한다.

### 1.2 [High] Graph 적재 Idempotency 미보장

02 §4.1에서 Vacancy 노드를 `CREATE`로, Organization을 `MERGE`로 처리한다:

```cypher
-- Organization: MERGE (멱등)
MERGE (o:Organization {org_id: $org_id})

-- Vacancy: CREATE (비멱등)
CREATE (v:Vacancy {vacancy_id: $job_id, scope_type: $scope_type, ...})
```

**문제**: 동일 JD를 재처리하면 Vacancy 노드가 중복 생성된다. 운영 전략(04)에서 "프롬프트 변경 → 해당 필드만 재추출 → Graph에서 해당 노드/엣지 DELETE + 재생성"을 제시하지만, DELETE 없이 파이프라인을 재실행하면 데이터가 오염된다.

**영향**: Phase 2 전체 데이터 처리(500K)에서 부분 실패 → 재시도 시 Vacancy/Outcome/SituationalSignal 등 CREATE로 생성되는 노드가 모두 중복될 위험.

**권장**:
- Vacancy, Outcome 등도 deterministic ID 기반 `MERGE`로 변경
- 또는 적재 전 기존 데이터 삭제를 파이프라인에 포함 (upsert 패턴)

### 1.3 [Medium] Phase 0 법무 의사결정의 일정 리스크

04 Phase 0-3에서 "PII 마스킹 전략 결정 (법무 확인 결과 반영)"을 1주차에 배치했다. 그러나:

- 법무 검토는 외부 의존성이 높아 3~4주 내 완료 보장이 없음
- PII 전략은 전체 아키텍처를 결정하는 Critical 의사결정 (API vs On-premise)
- 법무 결론이 지연되면 Phase 1 전체가 블로킹됨

**현재 계획의 완화 장치**: Phase 0-4 의사결정에서 "법무 불가 판정 시 Azure OpenAI Private Endpoint 또는 On-premise 전환"을 옵션으로 제시. 그러나 법무 결론이 **나오지 않는** 경우의 대응이 없다.

**권장**: "Phase 0 시작과 동시에 법무 검토 요청, 법무 결론 미확정 시 마스킹 기반 API 사용으로 진행하되 법무 결론 확정 시 전환" 형태의 **기본값 전략**을 명시할 것.

### 1.4 [Medium] evidence_span 검증의 Strict Match 한계

02 §8.2의 `validate_evidence_spans()` 함수가 `span not in original_text`로 검증한다. 그러나:

- LLM은 원문을 **약간 변형**하여 인용하는 경우가 흔함 (공백 정규화, 줄바꿈 제거, 부분 인용)
- PII 마스킹 후 텍스트에서 span을 검증하면, 마스킹 전 원문과의 offset 차이로 인해 false negative 증가
- strict `in` 검사의 예상 false negative 비율: 10~20% (실제 올바른 span이지만 검증 실패)

**영향**: 올바른 추출인데도 confidence가 50% 감쇄되는 케이스가 과다하게 발생할 수 있음.

**권장**: 공백/줄바꿈 정규화 후 비교하는 `normalized_contains()` 함수 사용. 또는 LLM에 span 대신 line_number 기반 참조를 요구하는 프롬프트 전략 검토.

### 1.5 [Low] Embedding 텍스트가 빈 문자열이 되는 Edge Case

02 §4.5의 `build_chapter_embedding_text()` 함수에서 scope_summary, outcomes, situational_signals를 결합한다. 그러나 LLM 추출이 실패하여 세 필드가 모두 null이면 빈 문자열이 반환된다.

- 빈 문자열의 embedding은 의미 없는 벡터가 됨
- Vector Index에 적재되면 ANN search에서 noise로 작용

**권장**: 빈 embedding 텍스트인 경우 embedding 적재를 skip하고, Candidate Shortlisting에서 해당 Chapter를 Rule pre-filter에서만 처리.

---

## 2. 과설계 (Over-engineering) 분석

### 2.1 [Low] culture_fit 피처 — 구현 우선순위 하향 가능

02 §5.1에서 culture_fit을 "Rule (facet 비교) — 대부분 INACTIVE"로 정의하고, 05 §2.11에서 ACTIVE 비율을 10-30%로 예상한다.

- work_style_signals는 "v1에서 대부분 null" (03 §3.3)
- operating_model도 JD 키워드 기반 low confidence (0.20~0.60)
- 두 저신뢰 데이터의 비교 결과는 **실질적 가치가 거의 없음**

**판정**: 다만 culture_fit의 구현 자체는 `if not data: return INACTIVE` 수준으로 **극히 단순**하며, v4 온톨로지 스키마 정합성을 유지하는 가치가 있다. "과설계"라기보다는 **구현 우선순위를 낮출 수 있는 항목**이다. Phase 1-5에서 다른 피처 구현 후 시간이 남으면 포함.

### 2.2 [Medium] operating_model LLM 보정 유지

v3 리뷰에서 "v1에서는 키워드만으로 충분, LLM 보정은 Phase 3"을 권장했으나 v4에서 미반영. 02 §2.4의 `llm_assess_authenticity` 함수가 여전히 존재한다.

- JD 키워드의 "광고성 필터링"은 LLM으로도 신뢰성이 낮음
- culture_fit이 대부분 INACTIVE이면 operating_model의 정밀도를 높일 실익이 없음
- JD당 추가 ~500 토큰 × 10K JD = 500만 토큰 (Haiku Batch 기준 ~$1.50, 비용은 미미하지만 복잡도 증가)

**판정**: 비용 영향은 미미하므로 **현재 수준 유지 가능**. 다만 구현 우선순위는 낮추는 것이 적절.

### 2.3 [참고] Outcome 노드의 독립 분리 — 향후 검토 사항

02 §4.2에서 Outcome을 별도 노드로 CREATE하고 `Chapter -[:PRODUCED_OUTCOME]-> Outcome` 엣지를 생성한다. 현재 MappingFeatures에서 Outcome은 직접 사용되지 않으며, Graph traversal에서 Outcome 노드를 독립 쿼리하는 유스케이스가 정의되어 있지 않다.

**판정**: v4 온톨로지가 Outcome을 별도 노드로 정의하고 있으므로 **스키마 정합성을 위해 현재 설계 유지가 적절**하며, 과설계가 아니다. Phase 3에서 Outcome 기반 Graph 쿼리(예: "정량 성과를 달성한 후보 탐색")가 추가될 수 있으므로 현재 구조를 유지하는 것이 합리적이다.

---

## 3. 부족 설계 (Under-engineering) 분석

### 3.1 [High] 이력서 중복 처리 전략 부재

04 Phase 0-1에서 "중복률 추정 (SimHash 테스트)"를 체크리스트에 포함했으나, **중복 감지 후의 처리 전략**이 정의되어 있지 않다.

> **참고**: Person 노드는 이미 `candidate_id` 기반 MERGE로 처리되므로(02 §4.2) Person 중복은 발생하지 않는다. 문제는 **동일인이 여러 이력서 파일로 등록된 경우**의 처리이다.

- 500K 이력서 중 동일인의 다중 버전 존재 가능 (갱신, 재제출, 다른 candidate_id로 등록)
- 어떤 버전을 canonical로 선택할지 (최신? 가장 상세?)
- 동일인이 다른 candidate_id로 등록된 경우 Person 노드 중복 발생
- MappingFeatures에서 동일인이 여러 번 매핑되어 결과 왜곡

**영향**: 동일인 다중 등록률이 5~10%라면, MappingFeatures 서빙 결과에서 중복 추천이 발생한다.

**권장**: 02 또는 04에 "이력서 중복 처리 전략" 섹션 추가:
1. **동일 candidate_id**: 최신 파일만 처리, 이전 버전은 아카이브 (파일 timestamp 또는 DB updated_at 기준)
2. **다른 candidate_id, 동일인 추정**: SimHash 유사도 > 0.9 시 수동 검토 큐로 이동 (Phase 2 운영에서 처리)
3. Phase 0에서 중복률 실측 후 처리 전략의 범위를 결정

### 3.2 [High] Chapter/Outcome ID 생성 전략 미정의

02 §4.2에서 `chapter_id`, `exp_id`를 사용하지만, 이 ID의 생성 방법이 정의되지 않았다.

- **UUID 방식**: 매번 새 ID 생성 → 증분 처리 시 동일 경력이 다른 chapter_id를 받아 Graph에 중복 노드 생성
- **Deterministic 방식** (예: `hash(candidate_id + company + period)`): 동일 경력은 동일 ID → 증분 처리에서 MERGE 가능

**영향**: 04 운영 전략의 증분 처리("변경된 경력 블록만 재추출")가 동작하려면 deterministic ID가 **필수**. 현재 설계에서는 이 전제가 명시되지 않아 증분 처리 구현 시 혼란 발생.

**권장**: chapter_id 생성 규칙을 명시: `chapter_id = hash(candidate_id + company_name_normalized + period_start)`. Outcome, SituationalSignal HAS_SIGNAL 엣지도 동일 원칙 적용.

### 3.3 [Medium] JD 갱신 시 MappingFeatures Cascade 미정의

04 운영 전략에서 이력서의 증분 처리는 상세하지만, **JD 갱신/삭제 시의 cascade 처리**가 정의되지 않았다.

- JD가 수정되면 기존 Vacancy 노드와 연결된 MappingFeatures가 모두 무효화됨
- JD가 마감/삭제되면 해당 Vacancy + 연결된 NEEDS_SIGNAL + MappingFeatures를 어떻게 처리?
- BigQuery 서빙 테이블에서 무효화된 MappingFeatures가 남아 있으면 서빙 품질 저하

**권장**: JD 갱신 시의 처리 플로우 추가:
1. JD 수정 → Vacancy 노드 업데이트 → 해당 Vacancy의 MappingFeatures 재계산 (Shortlisting부터)
2. JD 마감 → Vacancy soft-delete + MappingFeatures에서 제외

### 3.4 [Medium] BigQuery 서빙 테이블 스키마 미정의

02 §1에서 "Pipeline E: MappingFeatures → BigQuery 테이블"을 제시하고, 04 §2-4에서 "BigQuery 테이블 스키마 확정"을 Phase 2 작업으로 배정했다.

그러나 **DS/MLE 소비자가 어떤 쿼리 패턴으로 데이터를 사용하는지**가 정의되지 않았다:

- JD 기준 top-K 후보 조회?
- 후보 기준 적합 JD 조회?
- 피처별 필터링 + 정렬?
- 대시보드용 집계 쿼리?

**영향**: 쿼리 패턴에 따라 테이블 파티셔닝, 인덱싱 전략이 달라지며, Phase 2-4에서 뒤늦게 발견되면 재설계 필요.

**권장**: 02 또는 04에 "서빙 테이블 요구사항" 초안을 1페이지 수준으로 추가. Phase 2-4에서 확정하되, 기본 쿼리 패턴은 미리 정의.

### 3.5 [Medium] Confidence 값의 MappingFeatures Aggregation 전략 미정의

02에서 모든 추출 결과에 confidence를 부여하고, 05 §2.5에서 confidence 캘리브레이션을 다루지만, **MappingFeatures 계산 시 개별 confidence를 어떻게 aggregation하는지** 정의되지 않았다.

예: vacancy_fit 계산 시 후보의 situational_signals 중 confidence 0.3인 signal과 0.9인 signal을 동일하게 취급하는가?

```python
# 현재 설계 (02 §5.1)
matched = [s for s in candidate_signals if s.label in required]
score = len(matched) / len(required)
# → confidence 무시, 존재 여부만 카운트
```

**영향**: low confidence signal이 매칭에 동일 가중치로 반영되면, MappingFeatures 정확도가 하락할 수 있음.

**권장**: 간단한 가중 평균 도입: `score = sum(s.confidence for s in matched) / len(required)`. Phase 2 품질 평가에서 가중 vs 비가중 비교 후 결정.

### 3.6 [Low] 한국어/영문 혼합 이력서 처리 전략

02의 모든 프롬프트가 한국어로 작성되어 있으나, 실무에서는 영문 이력서 또는 한영 혼합 이력서가 상당 비율 존재할 수 있다. 04 Phase 0-1에서 "한국어/영문 혼합 비율" 조사를 포함하지만, 비율에 따른 **프롬프트 분기 전략**이 없다.

**판정**: LLM(Haiku)은 한영 혼합 입력을 잘 처리하므로 **현재 수준으로 충분**. 영문 전용 이력서 비율이 20% 이상이면 프롬프트 분기를 검토하는 정도로 Phase 0에서 확인.

---

## 4. 비용 모델 검증

### 4.1 비용 추정의 합리성

03 시나리오 A 총비용 $9,255는 v3 대비 $250 증가(프롬프트 최적화 비용 현실화 + embedding 평가 비용). 주요 비용 항목별 검증:

| 항목 | 추정 | 판정 | 비고 |
|---|---|---|---|
| CandidateContext LLM ($575) | 500K × $0.00115 | **합리적** | 토큰 추정이 정확하면 |
| Gold Label 인건비 ($5,840) | 400건 × 20,000원 | **합리적** | 건당 30~40분은 v4 스키마 복잡도에 적합 |
| Neo4j AuraDB ($1,200/년) | $100/월 × 12 | **보수적** | 800만 노드 시 Professional+ 필요 가능 ($200~500/월) |
| 프롬프트 최적화 ($600) | 500건 Sonnet | **적절** (v3 $200에서 현실화) | — |

### 4.2 누락된 비용 항목

| 항목 | 추정 영향 | 비고 |
|---|---|---|
| 이력서 중복 제거 인프라 | $0~100 | SimHash 계산은 저렴 |
| JD 갱신 시 MappingFeatures 재계산 | 월 $10~50 | 운영 단계 |
| span offset 보존 + 역매핑 개발 | 개발 인건비 0.5~1일 | 일정 영향 |
| LLM 재시도/디버깅 추가 비용 | LLM 비용의 10~20% | $60~120 |

**총 누락 비용**: ~$200~400. 전체 비용($9,255) 대비 2~4%로 **무시 가능 수준**.

### 4.3 비용 리스크 시나리오

| 시나리오 | 비용 영향 | 확률 |
|---|---|---|
| A8 불성립 (Haiku 품질 부족 → Sonnet) | +$2,300 (시나리오 B) | 20~30% |
| A2 불성립 (이력서 100만건) | +$575 (LLM 2배) | 10% |
| A11 불성립 (HWP 40%) | 일정 1~2주 연장 | 15% |
| Neo4j Professional 부족 | +$100~400/월 | 30% |

**가장 큰 리스크**: Haiku 품질 부족 시 Sonnet 전환. 이는 Phase 0 PoC에서 검증되므로 **관리 가능**.

---

## 5. 설계 일관성 이슈

### 5.1 [Medium] domain_fit embedding과 Vector Index embedding의 관계 불명확

02 §4.5에서 Chapter/Vacancy의 Vector Index용 embedding을 정의하고, 03 §2.2에서 "domain_fit은 company domain text와 candidate domain text의 cosine similarity"라고 별도 정의한다.

- Vector Index의 embedding: `scope_summary + outcomes + signals` (02 §4.5)
- domain_fit의 embedding: `company domain text vs candidate domain text` (03 §2.2)

이 두 embedding이 **동일한 벡터를 사용하는지, 별도 텍스트로 생성하는지** 불명확하다.

**권장**: domain_fit에서 사용하는 embedding 텍스트를 02에 명시적으로 정의. Vector Index embedding과 별도라면 추가 embedding 비용을 03에 반영.

### 5.2 [Low] 05 문서 제목과 내용 불일치

05 문서 제목은 "가상 정보, 리스크, 완화 전략"이지만, §3(v1에서 유효한 부분)과 §4(v1→v4 핵심 변경 요약)는 리스크와 무관한 내용이다. 이 내용은 01(Gap 분석)에 더 적합하다.

**판정**: 문서 구조의 미적 이슈이며 실질적 문제 아님.

---

## 6. 종합 판정

### 전체 완성도: 우수

v4 계획은 v3의 핵심 지적 사항을 체계적으로 반영하여 **즉시 실행 가능한 수준**에 도달했다. 특히 Entity Resolution, Candidate Shortlisting, evidence_span 검증, Phase 0 PoC 확장은 실현 가능성을 크게 높였다.

### 개선 권장 사항 (우선순위순)

| 우선순위 | 항목 | 조치 | v5 반영 필요 |
|---|---|---|---|
| **High** | Graph 적재 Idempotency | Vacancy/Outcome 등 CREATE → deterministic MERGE 전환 | **O** |
| **High** | 이력서 중복 처리 전략 | 중복 감지 + canonical 선택 + Graph 중복 방지 정의 | **O** |
| **High** | Chapter/Outcome ID 생성 전략 | deterministic ID 규칙 명시 | **O** |
| **High** | 이력서 섹션 분할 커버리지 | Phase 0 PoC에 파싱 단계별 성공률 측정 추가 | **O** |
| **Medium** | Phase 0 법무 의사결정 기본값 전략 | 법무 미확정 시 기본 행동 명시 | **O** |
| **Medium** | evidence_span 검증 정규화 | normalized_contains() 도입 | **O** |
| **Medium** | JD 갱신 cascade 처리 | Vacancy 업데이트 → MappingFeatures 재계산 플로우 | 선택 |
| **Medium** | Confidence aggregation 전략 | vacancy_fit에 confidence 가중 도입 | 선택 |
| **Medium** | domain_fit embedding 정의 | Vector Index vs domain_fit embedding 관계 명시 | 선택 |
| **Medium** | BigQuery 서빙 쿼리 패턴 | 기본 쿼리 패턴 초안 추가 | 선택 |
| **Low** | culture_fit 구현 우선순위 하향 | 스키마 정합성 유지하되 마지막에 구현 | 불필요 |
| **Low** | Embedding 빈 텍스트 처리 | null 필드 시 embedding skip 로직 | 선택 |
| **Low** | 한국어/영문 혼합 처리 | Phase 0에서 비율 확인 후 판단 | 불필요 |

### v5 반영 판단

**"v5 반영 필요 = O"인 6개 항목** 중 4개는 Graph 적재/데이터 무결성 관련이다. 이들은 개별적으로는 Medium~High이지만, **Graph 데이터 무결성이라는 하나의 주제로 수렴**하며, v4의 Graph 적재 설계(02 §4)에 집중적으로 반영할 수 있다.

나머지 2개(Phase 0 법무 기본값, evidence_span 정규화)는 각각 04와 02의 소규모 보강이다.

이 6개 항목은 계획의 **실행 안정성**을 의미 있게 높이므로, v5 작성을 권장한다.
