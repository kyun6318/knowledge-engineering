# v18 온톨로지 스키마 리뷰

> 리뷰 일시: 2026-03-11
> 리뷰 대상: `results/schema/v18/` 전체 (8개 파일)
> 리뷰 기준: README.md와의 방향성 일치, 실현 가능성/타당성, 과도한 설계, 부족한 설계
> 범위: 온톨로지 설계에 집중 (지식 그래프 구축은 02.knowledge_graph에서 진행)
> 모델: Claude Opus 4.6

---

## 1. 총평

v18은 v17 리뷰 피드백 11건을 반영한 증분 개선 버전이다. 핵심 변경은 (1) 다중 이력서 처리 규칙 명시, (2) SituationalSignal 경계 가이드/OTHER 모니터링, (3) Outcome v1 ROI 명시적 결정, (4) STAGE_SIMILARITY 비대칭 근거 추가, (5) overall_match_score 이중 감쇠 → 단순 가중 평균 전환, (6) 문서 간 중복 기술 정리 등이다.

v17 대비 개선된 점은 명확하다. 특히 문서 간 정본(canonical source) 관계를 명확히 하고, 구현 상세를 온톨로지 문서에서 02.knowledge_graph로 넘기는 범위 축소가 진행된 점이 좋다. 그러나 18차 반복을 거치면서 **온톨로지 설계 문서와 데이터 엔지니어링 설계 문서의 경계가 여전히 흐릿한 구간**이 남아 있고, **일부 설계 결정이 파일럿 검증 없이 누적되어 "파일럿에서 검증" 항목이 과도하게 쌓인** 상태이다.

**종합 평가: A- (양호~우수)**

| 평가 항목 | 점수 (5점 만점) | v17 대비 | 한줄 요약 |
|---|---|---|---|
| README 방향성 일치 | 4.5 | = | 핵심 비전과 거의 완벽히 정렬 |
| 실현 가능성 | 3.5 | = | v1 범위는 현실적이나 파일럿 의존 항목 누적 |
| 타당성 | 4.5 | +0.5 | STAGE_SIMILARITY 근거, overall_score 단순화가 합리적 |
| 과도한 설계 | 3.5 | +0.5 | 범위 축소 진행 중이나 완료되지 않음 |
| 부족한 설계 | 3.5 | = | 경계 사례 처리 일부 보완, 근본 부족은 유지 |

---

## 2. README 방향성 일치 분석

### 2.1 잘 정렬된 부분

| README 핵심 개념 | v18 구현 | 평가 |
|---|---|---|
| CompanyContext-CandidateContext 독립 생성 | 양측 독립 파이프라인 설계, 다중 공고 시 기업 수준 데이터 캐싱(§2.3) | 우수 |
| Evidence-first 원칙 | 모든 claim에 Evidence 인터페이스 일관 적용, source ceiling 체계 | 우수 |
| 5개 MappingFeatures + Graceful Degradation | F1~F5 계산 로직 명시, null 피처 자동 비활성화, 가중치 재분배 | 우수 |
| Taxonomy 고정 원칙 | SituationalSignal 14개, stage_label 5개, hiring_context 5개 등 고정 enum | 우수 |
| 부분 완성 허용 + 데이터 소스 Tier | T1~T7 confidence ceiling, 교차 검증, Graceful Degradation | 우수 |
| Graph Schema 9종 노드 | Person, Organization, Chapter, Vacancy, Role, Skill, Outcome, SituationalSignal, Industry — 모두 정의 | 우수 |

### 2.2 정렬이 약한 부분

| README 설명 | v18 현실 | 격차 | 심각도 |
|---|---|---|---|
| README "schema/v16" 참조 | 실제 스키마는 v18 | README 버전 참조 업데이트 필요 | 낮음 |
| README "Vector + Graph 하이브리드" | Q3 쿼리로 정의되었으나 MappingFeatures F1~F5와의 통합 워크플로우 미정의 | v17부터 지적된 사항, 하이브리드 검색이 매칭 파이프라인 어디에 위치하는지 명확화 필요 | 중간 |
| README Outcome이 핵심 구성요소 | v18에서 Outcome은 v1 매칭 피처에 미사용 결정 (§2.2 ROI 명시) | Outcome의 실질적 역할이 "프로필 표시 + v2 준비"로 축소. README의 핵심 개념 다이어그램과 괴리 | 낮음 (의도적 결정, 합리적) |

### 2.3 v18에서 개선된 정렬

- **[R-10/U-2] 다중 이력서 처리 규칙**: README의 "CandidateContext 소스 = 이력서"라는 전제에서, 한 사용자가 복수 이력서를 가진 경우의 처리가 이제 명확해졌다. 96.23%는 main_flag=1, 3.77%는 최신 이력서 fallback.
- **[T-1, T-2] SituationalSignal 경계 가이드**: README의 "Taxonomy 고정" 원칙을 강화. OTHER 비율 모니터링 기준(30%/50% 임계값)으로 taxonomy의 적정성을 운영 중 검증할 수 있게 됨.

---

## 3. 타당성 분석

### 3.1 타당성이 높은 설계 결정

**[V-1] overall_match_score 단순 가중 평균 전환 (v18 R-9/O-7)**

v1 대부분의 피처 confidence가 0.40~0.65 범위라는 현실을 인정하고, 이중 감쇠(score × weight × confidence) 대신 단순 가중 평균을 기본으로 채택한 것은 **탁월한 판단**이다.

- 이중 감쇠는 "확신도가 높은 피처가 주도"하는 효과를 의도했으나, v1에서는 모든 피처의 confidence가 비슷하게 낮아 변별력이 생기지 않고 점수만 전체적으로 압축됨
- 파일럿 후 비교 실험을 통해 도입 여부를 결정하겠다는 프로토콜이 합리적
- `use_double_dampening` 파라미터로 코드 변경 없이 전환 가능한 설계도 좋음

**[V-2] STAGE_SIMILARITY 비대칭 근거 명시 (v18 R-6)**

"상위 단계 경험자가 하위 단계에 적응하기 더 쉽다"는 비대칭 원칙을 코드 주석으로 명시한 것은 설계 의도를 명확히 한다.

- GROWTH→EARLY(0.50) vs EARLY→GROWTH(0.30): 성장기 경험자는 초기 불확실성을 이해하지만, 반대 방향은 프로세스/스케일링 경험 부족
- SCALE→GROWTH(0.50) vs GROWTH→SCALE(0.40): 큰 조직→작은 조직은 속도/민첩성 적응이 가능하나, 반대는 거버넌스 적응이 어려움
- 이 수치들은 여전히 전문가 판단 기반 초기값이지만, 근거가 문서화된 것만으로도 캘리브레이션 시 출발점이 됨

**[V-3] industry_code 비교의 코드 기반 계층 조회 (v18 R-7/U-7)**

v17까지의 `industry_code[:3]` 문자열 슬라이싱을 code-hub `lookup_common_code` 기반 group_code/sub_code 조회로 변경한 것은 **정확한 수정**이다. code-hub INDUSTRY 코드가 prefix 기반 계층 구조를 보장하지 않으므로, 문자열 슬라이싱은 잘못된 계층 비교를 초래할 수 있었다.

**[V-4] Outcome v1 ROI 명시적 결정 (v18 R-2)**

Outcome 추출을 v1에서 수행하되 매칭에는 사용하지 않겠다는 결정이, 비용 분석과 함께 명시적으로 문서화된 점이 좋다.

- 핵심 논거: SituationalSignal 추출과 동일 LLM 호출에서 수행되므로 Outcome만 제거해도 호출 자체는 줄지 않음. 추가 비용은 output token ~$30~50
- v2에서 전량 재추출보다 v1에서 축적이 효율적이라는 판단도 합리적
- Neo4j 적재는 선택적으로 하여 그래프 복잡도를 관리할 수 있는 유연성 확보

### 3.2 타당성에 의문이 있는 부분

**[V-5] SituationalSignal 라벨 경계 가이드의 실효성**

v18에서 추가된 5개 모호한 조합(SCALE_UP vs TEAM_SCALING 등)의 경계 가이드는 의도는 좋으나, **LLM 프롬프트에 이 가이드를 어떻게 반영할지**가 미정의이다.

- 가이드는 인간 평가자용으로는 명확하지만, LLM에게 "조직 전체의 성장이면 SCALE_UP, 특정 팀이면 TEAM_SCALING"을 일관되게 판단시키려면 프롬프트 엔지니어링이 필요
- **권고**: 파일럿에서 경계 사례 10건을 수집하여, 가이드를 프롬프트에 포함했을 때 vs 미포함 시 일관성 차이를 측정

**[V-6] REPLACE 공고의 vacancy_fit INACTIVE 처리**

REPLACE 공고에서 vacancy_fit을 INACTIVE로 처리하고 가중치를 role_fit에 재분배하는 것은 직관적으로 타당하나, **REPLACE 공고의 비율**이 전체 공고 중 얼마인지 데이터가 없다.

- 만약 REPLACE가 전체 공고의 40%+ 이상이라면, 상당수 매칭에서 vacancy_fit이 비활성화되어 F2 피처의 실질적 가치가 크게 감소
- **권고**: Phase 4-1(job-hub 상세 분석)에서 hiring_context 분포를 반드시 확인하고, REPLACE 비율이 30% 이상이면 REPLACE 전용 보조 피처 검토

---

## 4. 실현 가능성 분석

### 4.1 현실적으로 잘 설계된 부분

**[R-1] 다중 이력서 처리 규칙의 현실성**

main_flag=1이 없는 3.77%(~294K 사용자)에 대해 최신 이력서 fallback을 정의하고, 복수 main_flag=1 케이스에 대해 에스컬레이션 기준(1% 이상이면 데이터팀 보고)을 둔 것은 실무적으로 적절하다.

**[R-2] 문서 간 정본 관계 명확화**

v18에서 진행된 정본 지정이 좋다:
- 피처별 ACTIVE 전망 → `03_mapping_features.md §7.3`이 정본
- 추출 파이프라인 → `00_data_source_mapping §5.2`가 정본
- industry code 매칭 로직 → `03_mapping_features F3`가 정본

이를 통해 동일 정보가 여러 문서에 산재하던 문제가 완화되었다.

**[R-3] BigQuery-Neo4j 동기화의 범위 축소 (v18 R-5)**

DLQ, exponential backoff 등 구현 상세를 02.knowledge_graph로 넘기고 온톨로지 문서에는 동기화 방향/주기만 유지하는 것이 적절하다. 이전 버전에서 온톨로지 설계 문서에 에러 핸들링 상세가 포함된 것은 범위 침범이었다.

### 4.2 실현 가능성 우려

**[R-4] "파일럿에서 검증" 항목의 누적 — 중요 우려**

v14~v18을 거치면서 "v1 파일럿에서 검증/측정/결정" 항목이 과도하게 누적되었다. 파일럿 50건에서 검증해야 할 항목을 정리하면:

| # | 검증 항목 | 문서 출처 |
|---|---|---|
| 1 | F1 stage_match 실제 ACTIVE 비율 | 03 §7.3 |
| 2 | F2 vacancy_fit SituationalSignal 추출 정확도 | 03 §7.3 |
| 3 | F4 culture_fit의 <10% ACTIVE 확인 | 03 §7.3 |
| 4 | STAGE_SIMILARITY 매트릭스 캘리브레이션 | 03 F1 |
| 5 | ROLE_PATTERN_FIT 매트릭스 캘리브레이션 | 03 F5 |
| 6 | FEATURE_WEIGHTS 가중치 캘리브레이션 | 03 §4 |
| 7 | 이중 감쇠 vs 단순 가중 평균 비교 | 03 §4 |
| 8 | overall_match_score 분포 모니터링 | 03 §4.1 |
| 9 | NEEDS_SIGNAL 자동 추론 Precision/Recall | 04 §Q4 |
| 10 | SituationalSignal OTHER 비율 측정 | 02 §2.3 |
| 11 | LLM output token 비율 실측 (L1) | 00 §10.1 |
| 12 | workDetails 길이별 추출 정확도 | 02 §2.7 |
| 13 | GraphRAG vs Vector 비교 실험 | 05 전체 |

**13개 검증 항목을 50건 파일럿에서 모두 수행하는 것은 비현실적이다.** 50건으로는 통계적 유의성을 확보하기 어려운 항목이 다수이며, 파일럿의 범위가 과도하게 팽창할 위험이 있다.

**권고**:
- **필수 검증 (파일럿 50건에서 반드시)**: #1, #2, #8, #10, #11 — 시스템 동작 여부 확인
- **우선 검증 (파일럿 확장 또는 v1 초기 운영)**: #4, #5, #6, #9 — 매칭 품질에 직접 영향
- **후순위 (v1 운영 3개월 후)**: #3, #7, #12, #13 — 충분한 데이터 축적 후 수행

**[R-5] PastCompanyContext의 NICE 시점 한계**

v18에서도 해결되지 않은 근본 한계: PastCompanyContext는 **현재 시점** NICE 데이터로 과거 시점 기업 상태를 역산한다. confidence를 시간 차이에 따라 감쇠(0.60 - years_gap × 0.08)시키지만, 이는 **회사가 성장/축소/피봇한 경우 근본적으로 부정확**하다.

예: 2020년에 재직한 EARLY 스타트업이 현재 SCALE 기업이 된 경우, NICE 현재 데이터로 estimated_stage_at_tenure를 추정하면 SCALE이 반환될 수 있다.

- v1에서 이 한계를 인정하고 confidence를 하향하는 것은 적절하지만, F1 stage_match의 핵심 입력이 이렇게 부정확할 수 있다는 점은 전체 매칭 품질에 영향
- **이 문제는 온톨로지 설계로 해결할 수 없으며**, 투자 DB(T5)나 뉴스 크롤링(T4)으로 역사적 stage 데이터를 확보해야 해결됨
- 권고: v1에서는 현 설계 유지, v1.1에서 투자 DB 연동을 최우선으로 추진

---

## 5. 과도한 설계 분석

### 5.1 개선된 부분 (v17 대비)

- **[O-1] BigQuery-Neo4j 동기화 구현 상세 축소**: DLQ, exponential backoff 등을 "02.knowledge_graph에서 정의"로 이관. 온톨로지 문서의 범위가 적절해졌다.
- **[O-2] 피처별 ACTIVE 전망 정본 분리**: `00_data_source_mapping §6.5`가 데이터 소스 병목만 기술하고, 피처 설계 관점 정본을 `03_mapping_features §7.3`으로 확정. 중복 기술 감소.

### 5.2 여전히 과도한 부분

**[O-3] `00_data_source_mapping`의 과도한 구현 코드**

`00_data_source_mapping.md`는 1,125줄에 달하며, 온톨로지 매핑 가이드라는 목적 대비 **Python 구현 코드가 과도**하다. normalize_skill(), compute_skill_overlap(), compute_embedding_similarity_batch() 등은 온톨로지 설계가 아닌 데이터 엔지니어링 구현에 해당한다.

- 온톨로지 문서에 필요한 것: "스킬은 code-hub CI 매칭 → synonyms → 임베딩 fallback 순으로 정규화한다"
- 온톨로지 문서에 불필요한 것: 해당 로직의 30줄 Python 구현

**권고**: 의사 코드(pseudo-code) 수준을 유지하되, 실행 가능한 Python 코드는 02.knowledge_graph의 구현 문서로 이관. v14에서 일부 축소했으나 여전히 과도.

**[O-4] `06_crawling_strategy.md`의 분량**

500줄+ 이상의 크롤링 전략은 본래 온톨로지 설계의 범위를 벗어난다. v18 헤더에서 "데이터 수집 파이프라인 설계 문서로, 온톨로지 스키마와 분리된 구현 참조 문서"라고 명시한 것은 좋지만, 여전히 01.ontology/results/schema/ 디렉토리 안에 위치한다.

**권고**: 온톨로지 설계에서는 "T3/T4 소스 활성화 시 어떤 필드가 보강되고 confidence가 어떻게 변하는가"만 필요. 크롤링 실행 계획(Playwright, Cloud Run, GCS 등)은 별도 디렉토리로 분리하는 것이 자연스럽다.

**[O-5] `05_evaluation_strategy.md`의 위치**

GraphRAG vs Vector 비교 실험 계획은 온톨로지 설계가 아닌 **시스템 평가/검증** 문서이다. v18 헤더에서 "실험 설계 문서로, 온톨로지 설계와 분리된 구현/검증 참조 문서"라고 명시한 것은 인지하고 있다는 증거이지만, 물리적 이동이 필요하다.

### 5.3 과도한 설계의 근본 원인

18차 반복의 부작용으로, **온톨로지 설계 문서가 다음 3가지를 동시에 담고 있다**:
1. **온톨로지 스키마**: 노드/관계/속성 정의, taxonomy, Evidence 모델 (핵심)
2. **데이터 엔지니어링 설계**: 매핑 규칙, 정규화 로직, 추출 파이프라인 (00번 문서 주도)
3. **운영/평가 계획**: 크롤링 전략, 비교 실험, 비용 추정 (05, 06번 문서)

이 3가지를 분리하면 각 문서의 역할이 명확해지고, 온톨로지 설계 리뷰도 핵심에 집중할 수 있다.

---

## 6. 부족한 설계 분석

### 6.1 v18에서 보완된 부분

- **[D-1] SituationalSignal 라벨 간 경계 가이드**: v17에서 지적된 모호한 조합에 대한 판정 기준이 5개 추가됨. 복수 선택 규칙도 명시. 다만 LLM 프롬프트 반영 방안은 미정.
- **[D-2] OTHER 비율 모니터링**: 30%/50% 임계값으로 taxonomy 적정성을 운영 중 검증할 수 있게 됨. taxonomy 동결 원칙과 진화 가능성 사이의 균형점.
- **[D-3] 다중 이력서 처리 규칙**: main_flag 없는 3.77% 케이스에 대한 명시적 처리.

### 6.2 여전히 부족한 부분

**[D-4] hiring_context 추출의 LLM 의존성과 품질 보장 — 중요**

vacancy.hiring_context(BUILD_NEW/SCALE_EXISTING/RESET/REPLACE/UNKNOWN)은 F2 vacancy_fit의 핵심 입력이자, Q4 NEEDS_SIGNAL 자동 추론의 시작점이다. 그러나:

- 추출 방법이 "overview.descriptions(JSONB)에서 LLM 추출"로만 정의
- JD 텍스트에서 BUILD_NEW vs SCALE_EXISTING을 정확히 구분하는 것은 쉽지 않음
  - "시스템을 고도화할 시니어 엔지니어" → SCALE_EXISTING? RESET?
  - "새로운 팀에서 함께할 분" → BUILD_NEW? REPLACE?
- hiring_context 추출 정확도가 F2 전체의 정확도를 결정하는데, 이에 대한 검증 계획이 없음

**권고**:
1. hiring_context 탐지 패턴(§2.1의 키워드 테이블)을 Rule-based 1차 분류로 사용하고, LLM은 Rule이 UNKNOWN일 때만 fallback
2. 파일럿 50건에서 hiring_context 추출 정확도를 채용 전문가 평가로 측정 (검증 항목에 추가)

**[D-5] scope_type 추출의 저품질 입력 문제**

후보 Experience의 scope_type(IC/LEAD/HEAD/FOUNDER)은 F5 role_fit과 F1 stage_match에 모두 영향을 미치는 중요 필드이다. 그러나:

- positionTitleCode: 29.45% fill rate (1순위)
- positionGradeCode: 39.16% fill rate (2순위)
- workDetails LLM 추출: ~56% fill rate, 중앙값 96자 (3순위)
- **최악의 경우 30~40%의 Experience에서 scope_type이 UNKNOWN으로 남을 수 있음**

scope_type이 UNKNOWN이면:
- F5 role_fit에서 scope_type → seniority 변환이 불가 → "UNKNOWN"으로 fallback → 경력 연수 기반만으로 판단
- F1 stage_match에서 scope_bonus(Lead/Head 보너스 +0.10)를 받지 못함

**권고**: scope_type UNKNOWN 비율을 v1 파일럿에서 측정하고, 30%를 초과하면 departmentName(58.9% fill rate)을 보조 입력으로 활용하는 규칙 추가 검토
- 예: departmentName에 "팀장", "센터장" 등이 포함되면 LEAD로 추정

**[D-6] 시간 감쇠(Freshness) 적용 범위의 불명확**

freshness_weight(0.3~1.0)이 Person 노드 속성으로 정의되어 있으나, **이 가중치가 MappingFeatures 계산에 어디서 어떻게 적용되는지** 명시되지 않았다.

- overall_match_score에 곱해지는가?
- 검색 결과 순위에 반영되는가?
- 단순 필터링 용도인가?

**권고**: freshness_weight의 적용 지점을 명시. 예: "overall_match_score 계산 후, freshness_weight를 곱하여 최종 랭킹 점수를 산출" 또는 "freshness_weight < 0.5인 후보는 결과에서 후순위 표시"

**[D-7] 동일 기업 경력이 여러 Chapter인 경우의 처리**

한 후보가 동일 기업에서 직급/직무가 변경된 경우(예: A사 주니어 → A사 시니어), 이것이 1개 Chapter인지 2개 Chapter인지의 분할 기준이 없다.

- resume-hub의 Career 레코드가 동일 회사에서 2건이면 2개 Chapter?
- 동일 회사 연속 근무이면 1개로 병합?
- 이는 Chapter → Organization 관계(OCCURRED_AT), SituationalSignal 추출, duration_months 계산에 영향

**권고**: "resume-hub Career 레코드 1건 = 1 Chapter" 원칙을 명시하되, 동일 회사 연속 근무 시 NEXT_CHAPTER의 gap_months를 0으로 설정하고, role_evolution 추출 시 "같은 회사 내 성장"으로 처리하는 규칙 추가

**[D-8] 폐업/인수된 회사의 PastCompanyContext 처리**

NICE에서 조회 불가한 기업(폐업, 인수합병, 미등록 스타트업)에 대한 PastCompanyContext 처리가 "confidence=0.0, stage_estimation_method='unknown'"으로만 정의되어 있다.

- NICE 미등록 비율을 알 수 없지만, 4.48M 고유 회사명 중 소규모/프리랜서/해외 기업은 NICE에 없을 가능성 높음
- BRN(62% fill rate)이 있어도 NICE 매핑이 안 되면 industry_code, employee_count, stage 모두 null

**권고**: NICE 미매칭 비율을 Phase 1에서 측정. 30% 이상이면 job-hub 역참조(§3.4)의 coverage도 함께 확인하여 보완 전략 수립

---

## 7. 문서별 상세 피드백

### 7.1 `00_data_source_mapping.md`

**강점**: 실측 데이터 기반 설계의 핵심 문서. fill rate, 품질 등급, 사용 불가 필드 등이 체계적으로 정리됨.

**개선 필요**:
- [00-1] §10 LLM 비용 추정에서 Gemini 2.0 Flash 가격 기준일(2026-03)이 명시되어 있으나, 모델 버전 업데이트에 따른 가격 변동 가능성 언급 필요
- [00-2] §8 구현 로드맵의 Phase 1~4가 02.knowledge_graph의 실행 계획과 정합되는지 교차 확인 필요. 02.knowledge_graph README는 아직 v10 기반(스키마 v18 이전)으로 기술되어 있음

### 7.2 `01_company_context.md`

**강점**: v18에서 내용 변경 없음(버전 헤더 동기화만). 이미 안정화된 문서.

**개선 필요**:
- [01-1] §3 JSON 예시의 `$schema: "CompanyContext_v4"`: 문서 버전은 v18인데 스키마 버전은 v4. 이는 의도적(v4 원본 기반)이지만, context_version도 "4.0"으로 되어 있어 혼란 가능. "v4 스키마를 v18에서도 유지한다"는 명시적 설명이 있으면 좋겠음

### 7.3 `02_candidate_context.md`

**강점**: v18에서 SituationalSignal 경계 가이드(T-2), OTHER 모니터링(T-1), Outcome ROI 결정(R-2)이 추가되어 운영 가능성 향상.

**개선 필요**:
- [02-1] §2.3 SituationalSignal 추출 프롬프트에 v18에서 추가된 경계 가이드가 반영되어야 하지만, 프롬프트 예시에는 아직 미반영. "모호한 조합 판정 기준"을 프롬프트에 인라인하거나 few-shot 예시로 추가 필요
- [02-2] §2.1 Experience 인터페이스에 `responsibilities: string[]`이 Low difficulty 필드로 정의되어 있으나, JSON 예시(§3)에는 누락. 인터페이스 vs 예시 불일치

### 7.4 `03_mapping_features.md`

**강점**: v18에서 overall_match_score 단순화, STAGE_SIMILARITY 근거 추가 등 핵심 계산 로직이 개선됨.

**개선 필요**:
- [03-1] §2 F3 domain_fit의 `embed()` 함수에서 company_domain을 "market_segment or industry_label"로 선택하는데, 두 값의 성격이 매우 다름. market_segment는 "B2B SaaS"처럼 비즈니스 모델 지향적이고, industry_label은 "소프트웨어 개발업"처럼 산업 분류 지향적. 이 두 값을 동일 임베딩 공간에서 candidate domain_depth와 비교하면 일관성이 떨어질 수 있음
  - **권고**: company_domain 선택 시 market_segment를 우선하되, 임베딩 비교의 한계를 인정하고 code_match_bonus에 더 높은 가중치를 부여하는 것을 검토
- [03-2] §4 FEATURE_WEIGHTS에서 role_fit(0.15)이 domain_fit(0.20)보다 낮은 것이 적절한지 재검토 필요. 채용 실무에서 역할 적합도(시니어리티/스킬 매칭)가 도메인 적합도보다 중요한 경우가 많음
  - 다만 이는 캘리브레이션 계획이 있으므로 v1에서는 현행 유지 가능

### 7.5 `04_graph_schema.md`

**강점**: 노드/엣지 규모 추정(§7), 인덱스 전략(§8), 동기화 전략(§9)이 체계적.

**개선 필요**:
- [04-1] §7.1 노드 규모에서 Organization ~500K 추정이 "4.48M 고유값 → 정규화 후 추정"으로만 기술. 이 10배 축소가 어떤 근거인지 불명확. BRN 기반 클러스터링으로 62%를 처리한다 해도, 나머지 38%의 회사명 유사도 기반 병합에서 500K까지 줄어드는 것은 낙관적일 수 있음
  - **권고**: Organization 노드 수를 500K~2M 범위로 추정하고, Neo4j 용량 산정도 이에 맞춰 상한 기준으로 조정

### 7.6 `05_evaluation_strategy.md`

**강점**: 비교 실험 설계가 체계적. Power analysis, 적응적 표본 크기 결정, 4가지 Case 의사결정 트리가 명확.

**개선 필요**:
- [05-1] §1.1 후보 풀 선정에서 "데이터 완성도: Skill 보유 50%+"를 조건으로 두면 전체 풀(38.3%)보다 높은 완성도의 표본이 선택되어 **실험 결과가 실제 운영보다 낙관적으로 나올 위험**이 있음
  - **권고**: 전체 풀 대표성을 위해 Skill 보유율 조건을 제거하거나, 최소한 Skill 보유/미보유 하위 그룹 비교를 실험에 포함

### 7.7 `06_crawling_strategy.md`

별도 상세 리뷰 불요. v18에서 내용 변경 없음. 크롤링 전략 자체는 잘 설계되어 있으나, 온톨로지 설계 문서로서의 위치가 부적절하다는 점은 §5에서 지적함.

### 7.8 `02_v4_amendments.md`

A8(추출 프롬프트 확장 로드맵)만 미이관. 4단계 확장 일정과 안정화 판정 기준이 명확. 추가 피드백 없음.

---

## 8. v17 리뷰 피드백 반영 평가

v17 리뷰에서 제기한 주요 항목의 v18 반영 여부:

| v17 리뷰 항목 | v18 반영 여부 | 평가 |
|---|---|---|
| [R-5] 문서 간 중복 기술 정리 | 부분 반영 — 정본 지정으로 개선, 물리적 코드 이관은 미완 | B |
| [R-6] STAGE_SIMILARITY 비대칭 근거 | 반영 — 코드 주석으로 상세 근거 추가 | A |
| [R-7] industry_code 비교 방식 | 반영 — 문자열 슬라이싱 → code-hub lookup 기반 변경 | A |
| [R-9/O-7] overall_match_score 이중 감쇠 | 반영 — 단순 가중 평균 기본, 이중 감쇠 선택적 | A |
| [R-10/U-2] 다중 이력서 처리 | 반영 — 3가지 케이스별 처리 규칙 명시 | A |
| [T-1] SituationalSignal OTHER 모니터링 | 반영 — 30%/50% 임계값 기준 추가 | A |
| [T-2] SituationalSignal 경계 가이드 | 반영 — 5개 모호한 조합 판정 기준 추가 | A- (LLM 프롬프트 반영 미정) |
| [R-2] Outcome v1 ROI 결정 | 반영 — 비용 분석과 함께 명시적 결정 기록 | A |

**종합**: v17 리뷰 피드백의 대부분이 적절히 반영됨. 문서 물리적 분리/이관이 유일하게 미완인 항목.

---

## 9. 종합 권고사항

### 9.1 즉시 반영 권고 (v19)

| # | 권고 | 심각도 | 대상 문서 |
|---|---|---|---|
| S-1 | `02_candidate_context` §2.3 추출 프롬프트에 경계 가이드를 인라인 또는 few-shot으로 반영 | 중간 | 02 |
| S-2 | freshness_weight의 MappingFeatures 적용 지점 명시 | 중간 | 03 |
| S-3 | "resume-hub Career 레코드 1건 = 1 Chapter" 원칙 명시, 동일 회사 연속 근무 처리 규칙 추가 | 중간 | 02, 04 |
| S-4 | README.md의 "schema/v16" 참조를 현재 버전으로 업데이트 | 낮음 | README |
| S-5 | `02_candidate_context` §2.1 Experience 인터페이스 vs §3 JSON 예시의 `responsibilities` 불일치 해소 | 낮음 | 02 |

### 9.2 파일럿 필수 검증 항목 (우선순위 정리)

| 우선순위 | 검증 항목 | 50건으로 충분? |
|---|---|---|
| **P0** | hiring_context 추출 정확도 | 가능 (채용 전문가 대조) |
| **P0** | SituationalSignal 추출 정확도 (workDetails 길이별) | 가능 (인간 평가) |
| **P0** | overall_match_score 분포 정상 여부 | 가능 |
| **P0** | LLM output token 비율 실측 | 10건으로 충분 |
| **P1** | F1~F5 실제 ACTIVE 비율 | 가능 (분포 확인) |
| **P1** | OTHER signal 비율 | 가능 |
| **P1** | NEEDS_SIGNAL 자동 추론 Precision/Recall | 가능 (50건 × 14 signals) |
| **P2** | STAGE_SIMILARITY / ROLE_PATTERN_FIT 캘리브레이션 | 50건으로 부족 → v1 운영 3개월 후 |
| **P2** | FEATURE_WEIGHTS 최종 보정 | 50건으로 부족 → v1 운영 3개월 후 |
| **P3** | 이중 감쇠 vs 단순 가중 평균 비교 | 50건으로 불가 → v1 운영 데이터 축적 후 |
| **P3** | GraphRAG vs Vector 비교 실험 | 별도 실험으로 분리 완료 (05 문서) |

### 9.3 중장기 구조 개선 권고

| # | 권고 | 우선순위 |
|---|---|---|
| L-1 | 온톨로지 설계 문서를 (1) 스키마 정의, (2) 데이터 엔지니어링 설계, (3) 운영/평가 계획으로 물리적 분리 | 중간 (v2 전환 시점) |
| L-2 | 02.knowledge_graph README를 v18 스키마 기준으로 업데이트 (현재 v10 기반) | 높음 |
| L-3 | PastCompanyContext의 역사적 stage 추정을 투자 DB(T5) 연동으로 보강하는 v1.1 설계 착수 | 높음 |

---

## 10. 결론

v18은 v17 대비 의미 있는 개선을 달성했다. 특히 **overall_match_score 단순화**, **STAGE_SIMILARITY 비대칭 근거**, **SituationalSignal 경계 가이드**, **Outcome v1 ROI 결정**은 설계의 타당성과 투명성을 높인 변경이다. 문서 간 정본 관계 명확화와 구현 상세의 범위 축소도 진행 중이다.

그러나 18차 반복의 누적으로 인한 **파일럿 검증 항목 과부하**와 **문서 범위 혼재**는 아직 해결되지 않았다. 이 시점에서 가장 중요한 것은 **추가 설계 반복보다 파일럿 실행**이다. 현재 설계는 파일럿을 수행하기에 충분한 수준이며, 남은 불확실성은 실데이터 검증을 통해서만 해소할 수 있다.

**v18 이후 권고 방향**: 추가 온톨로지 반복(v19)은 §9.1의 즉시 반영 항목에 한정하고, 주력을 02.knowledge_graph 파일럿 구현으로 전환할 것을 권고한다.
