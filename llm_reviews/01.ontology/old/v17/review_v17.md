# v17 온톨로지 스키마 리뷰

> 리뷰 일시: 2026-03-10
> 리뷰 대상: `results/schema/v17/` 전체 (8개 파일)
> 리뷰 기준: README.md와의 방향성 일치, 실현 가능성/타당성, 과도한 설계, 부족한 설계
> 범위: 온톨로지 설계에 집중 (지식 그래프 구축은 02.knowledge_graph에서 진행)

---

## 1. 총평

v17은 v4 원본에서 16차례 반복 개선을 거쳐 상당히 성숙한 온톨로지 설계에 도달했다. README가 제시하는 "기업-인재 맥락 기반 매칭"이라는 핵심 비전을 충실히 구현하고 있으며, 특히 v12에서 실측 데이터 기반 설계로 전환한 점이 큰 강점이다. 다만 17차 반복의 부작용으로 문서 간 중복 기술이 누적되었고, 일부 영역에서 온톨로지 설계를 넘어선 구현 상세가 과도하게 포함되어 있다.

**종합 평가: B+ (양호, 개선 필요)**

| 평가 항목 | 점수 (5점 만점) | 한줄 요약 |
|---|---|---|
| README 방향성 일치 | 4.5 | 핵심 비전과 거의 완벽히 정렬 |
| 실현 가능성 | 3.5 | v1 범위는 현실적이나 일부 낙관적 가정 존재 |
| 타당성 | 4.0 | 도메인 지식에 기반한 합리적 설계 |
| 과도한 설계 | 3.0 | 구현 상세가 온톨로지 설계를 침범하는 부분 다수 |
| 부족한 설계 | 3.5 | 핵심 누락보다는 경계 사례 처리 부족 |

---

## 2. README 방향성 일치 분석

### 2.1 잘 정렬된 부분

| README 핵심 개념 | v17 구현 | 평가 |
|---|---|---|
| CompanyContext 독립 생성 | `01_company_context` §0에서 "후보와 무관하게 생성" 원칙 명시, §2.3에서 동일 기업 다중 공고 시 공유/독립 분리 명확 | 우수 |
| CandidateContext 독립 생성 | `02_candidate_context` Experience/Chapter 단위 분해, 14개 SituationalSignal taxonomy 고정 | 우수 |
| MappingFeatures 5개 피처 | `03_mapping_features` F1~F5 계산 로직과 Graceful Degradation 상세 정의 | 우수 |
| Evidence-first 원칙 | 모든 문서에서 Evidence 인터페이스 일관 적용, source ceiling 체계 | 우수 |
| 부분 완성 허용 | INACTIVE 피처 자동 처리, null 허용 필드 명시, missing_fields 추적 | 우수 |
| 데이터 소스 Tier 체계 | T1~T7 confidence ceiling 체계화, 교차 검증 규칙 | 우수 |

### 2.2 정렬이 약한 부분

| README 설명 | v17 현실 | 격차 |
|---|---|---|
| README "9종 노드" 다이어그램 | v17 `04_graph_schema`에서 9종 노드 유지하지만, Outcome 노드가 v1에서 MappingFeatures에 사용되지 않음 (v17 R-3) | Outcome 노드의 v1 역할이 "프로필 표시용"으로 축소. README에서 Outcome이 핵심 구성요소처럼 보이지만 실제 매칭에는 기여하지 않음 |
| README "Vector + Graph 하이브리드" | v17 Q3 쿼리에서 정의되었으나 실제 MappingFeatures 계산과의 통합 방식이 불명확 | 하이브리드 검색과 5개 피처 기반 매칭의 관계 정의 필요 |
| README §버전 로드맵 "schema/v16" 참조 | README가 v16 기준, 실제 스키마는 v17 | README 업데이트 필요 (사소) |

---

## 3. 실현 가능성 분석

### 3.1 현실적으로 잘 설계된 부분

**[F-1] 실측 데이터 기반 설계 전환 (v12+)**

v12에서 추정치를 실측 fill rate로 전면 교체한 것은 가장 큰 강점이다. `00_data_source_mapping`의 §6.1 resume-hub 필드 가용성 테이블은 설계 결정의 근거를 명확히 제공한다.

- workDetails 56% fill rate, 중앙값 96자 → 이에 맞춰 50자 미만 텍스트에 대한 추출 품질 대응 전략 수립 (v14)
- careerDescription 16.9% fill rate → selfIntroduction 64.1% fallback 설계
- daysWorked 100% 제로 → 직접 계산 로직으로 대체

**[F-2] v1 매칭 범위 EXPERIENCED 제한 (v16)**

NEW_COMER 30.9%를 v1에서 과감히 매칭 대상에서 제외하고, v2 신입 매칭 로드맵(Education/Certificate 기반)을 정의한 점이 현실적이다. Career 데이터가 없는 신입에 대해 Experience/Chapter 기반 매칭을 억지로 적용하지 않는 것이 올바른 판단.

**[F-3] F4 culture_fit의 <10% ACTIVE 인정**

F4를 제거하지 않고 프레임워크 완성도를 위해 유지하면서도 v1에서 대부분 INACTIVE임을 인정한 점이 현실적. v17 R-6에서 포함 근거를 4가지로 명확히 설명한 것도 좋다.

### 3.2 낙관적이거나 검증이 필요한 부분

**[F-4] F1 stage_match ACTIVE 비율 50~60% 추정 — 낙관적 가능성**

- 병목: 회사명 정규화 (4.48M 고유값)
- BRN 62% 활용으로 1차 클러스터링이 가능하다고 했지만, BRN이 있어도 NICE 매핑까지 연결되려면 추가 단계(회사명→NICE 업체코드)가 필요
- PastCompanyContext 생성에 필요한 "이전 회사의 stage 추정"이 실제로 얼마나 가능한지 불확실
- **권고**: 파일럿 50건에서 F1 실제 ACTIVE 비율을 측정하고, 30% 미만이면 가중치 재배분 검토

**[F-5] SituationalSignal 추출 품질 가정**

14개 taxonomy 기반 LLM 추출이 workDetails(중앙값 96자)에서 얼마나 정확한지에 대한 검증 계획이 부족하다.

- 96자의 workDetails에서 "SCALE_UP", "TEAM_BUILDING" 같은 상황 라벨을 신뢰성 있게 추출할 수 있는가?
- `02_candidate_context` §2.7에서 50자 미만은 스킵한다고 했지만, 50~100자 구간(상당수)에서의 추출 품질은 0.8 감쇠로 충분한가?
- **권고**: 파일럿에서 workDetails 길이별 SituationalSignal 추출 정확도를 측정하는 실험 추가

**[F-6] LLM 비용 ~$500 추정 — output token 비율 불확실**

v15에서 N14-1로 output token 30% 가정의 위험성을 인지하고 $700까지 상승 가능성을 언급했다. 이는 적절한 주의사항이지만, **L1(Outcome/Signal 추출)에서 구조화된 JSON 출력 시 output이 입력의 50~80%**라는 추정은 실측 전까지 불확실. $1,000 이내를 관리 가능 범위로 본 것은 합리적.

**[F-7] NEEDS_SIGNAL 자동 추론의 타당성**

`04_graph_schema` §Q4에서 `HIRING_CONTEXT_TO_SIGNALS` 매핑 테이블로 Vacancy→SituationalSignal 관계를 자동 생성한다. v17 R-5에서 파일럿 검증 계획을 추가한 것은 좋지만, 이 매핑의 근본적 타당성이 의문:

- BUILD_NEW → PMF_SEARCH가 항상 성립하는가? (기존 기업이 새 사업부를 만드는 BUILD_NEW일 수 있음)
- SCALE_EXISTING → LEGACY_MODERNIZATION이 strong 매칭인가? (스케일링과 레거시 개선은 다른 상황)
- **권고**: HIRING_CONTEXT_TO_SIGNALS의 strong/moderate/weak 분류를 채용 전문가 3명 이상의 합의로 재검토

### 3.3 데이터 품질 제약에 대한 인식 (양호)

스키마가 데이터 품질 제약을 솔직하게 인정하는 점이 좋다:
- 스킬 codehub 매핑 2.4% → 임베딩 fallback
- careerDescription에 career_id FK 없음 → LLM 텍스트 귀속
- positionGrade/Title 저입력 29-39% → 다단계 fallback
- SOFT_SKILL 편중 (성실성 25.2%) → 매칭에서 제외

---

## 4. 과도한 설계 (Over-engineering)

### 4.1 온톨로지 설계를 넘어선 구현 상세

**[O-1] 00_data_source_mapping의 pseudo-code 과다 — 심각**

이 문서는 1,100줄 이상으로, 온톨로지 매핑 문서라기보다 **구현 명세서**에 가깝다. 다음 코드들은 온톨로지 설계 단계에서 불필요하며 02.knowledge_graph 구현 단계로 이동해야 한다:

- `resolve_industry_code()` (§1.1, 70~94줄)
- `normalize_skill()` (§1.3, 146~183줄)
- `compute_embedding_similarity_batch()` (§1.5, 231~244줄)
- `compute_skill_overlap()` (§4.3, 731~777줄)
- `compute_freshness_weight()` (§3.5, 644~668줄)
- `get_service_resume_pool()` / `get_v1_matching_pool()` (§3.1, 402~443줄)

**권고**: 매핑 규칙은 테이블 형태로 유지하고, pseudo-code는 별도 구현 명세 문서로 분리. 온톨로지 문서에는 "어떤 필드가 어떤 소스에서 오는지"만 남기고 "어떻게 추출/계산하는지"는 구현 문서로.

**[O-2] 06_crawling_strategy의 범위 — 심각**

크롤링 전략은 **데이터 수집 파이프라인 설계**이지 온톨로지 설계가 아니다. 1,500줄에 달하는 이 문서는:
- Playwright 기반 크롤링 엔진 상세
- URL 발견 우선순위, 서브도메인 탐색 로직
- 네이버 뉴스 API 검색 전략
- Cloud Run Job/Eventarc/Cloud Scheduler 아키텍처
- HTML 해시 vs 텍스트 해시 A/B 테스트 계획
- BigQuery 테이블 DDL

이것들은 온톨로지 스키마와 분리되어야 한다. 온톨로지 설계에서 필요한 것은 "크롤링으로 어떤 필드가 보강되는지"와 "보강 시 confidence 변화"뿐이다.

**권고**: 06_crawling_strategy는 별도 프로젝트/디렉토리로 이동. 온톨로지 문서에는 "T3/T4 소스가 활성화되면 다음 필드가 보강된다" 수준의 요약만 유지.

**[O-3] 05_evaluation_strategy의 구현 상세 — 중간**

실험 계획 자체는 필요하지만, Step별 Python 함수 시그니처(vector_baseline_search, expert_evaluation_session 등)는 온톨로지 설계 문서에 포함될 내용이 아니다. 실험 설계의 "무엇을 비교하는가"와 "어떤 기준으로 판단하는가"만 유지하면 충분.

**[O-4] 04_graph_schema §9 BigQuery-Neo4j 동기화 — 중간**

sync_to_neo4j 함수의 에러 핸들링, DLQ, exponential backoff 등은 인프라 구현 상세이다. 그래프 스키마 문서에서는 "어떤 노드/엣지가 어떤 주기로 동기화되는지"만 기술하면 충분.

### 4.2 구조적 과도함

**[O-5] structural_tensions 8개 taxonomy — 경미**

v1에서 70%+ null이 예상되는 필드에 8개 taxonomy, 배타성 가이드, related_tensions 체계까지 정의한 것은 시기상조. v16에서 "v1에서는 tension_type 라벨만 사용"이라고 했지만 문서에는 여전히 상세 정의가 남아 있다.

**[O-6] MAPPED_TO 엣지 TTL/아카이빙 정책 — 경미**

v16에서 스스로도 "v1 파일럿에서는 구현하지 않는다"고 했지만, 아카이빙 로직 코드(archive_stale_mappings)가 여전히 포함. v1.1+ 검토 대상이면 해당 시점에 설계해도 늦지 않다.

**[O-7] confidence 이중 감쇠 — 설계 의도는 이해하지만 과도할 가능성**

overall_match_score 계산에서 confidence를 가중치로 사용하는 이중 감쇠(v8 설계 의도 주석)는 개념적으로 이해되지만, v1의 대부분 피처 confidence가 0.40~0.65인 상황에서 점수 분포가 과도하게 압축될 위험. v16에서 모니터링 기준을 추가한 것은 적절하나, **단순 가중 평균을 기본으로 두고 이중 감쇠는 v1 파일럿 결과 후 도입 검토하는 것이 더 안전**하다.

---

## 5. 부족한 설계 (Under-engineering)

### 5.1 핵심 누락

**[U-1] Outcome의 v1 활용 방안 부재 — 중요**

v17 R-3에서 Outcome을 MappingFeatures에서 사용하지 않는 이유를 설명했고, 이는 합리적이다. 그러나 Outcome 노드를 "프로필 표시용"과 "그래프 탐색(Q3)"으로만 활용한다면, **Outcome 추출에 투입되는 LLM 비용(L1 ~$220 최대 비용 항목)의 ROI가 불명확**하다.

- v1에서 Outcome을 추출하지 않고, v2에서 정규화 후 도입하는 것이 비용 효율적일 수 있음
- 또는 Outcome을 "추출은 하되 노드 생성은 v2"로 두면 LLM 비용은 발생하지만 그래프 복잡도는 줄일 수 있음
- **권고**: Outcome 추출의 v1 ROI를 명시적으로 판단하고, "추출한다/하지 않는다"를 결정

**[U-2] 동일 후보의 다중 이력서 처리 — 누락**

`00_data_source_mapping` §3.1에서 main_flag=1 필터를 명시했지만, 한 사용자가 여러 resume를 갖는 경우(96.23%가 main 보유)의 처리가 불충분:
- main_flag가 없는 3.77%(~294K 사용자)는 어떻게 처리하는가?
- main이 여러 개인 경우는 없는가? (데이터 무결성 확인 필요)
- **권고**: multi-resume 사용자 처리 규칙을 명시 (최신 resume 사용, 또는 제외)

**[U-3] 온톨로지 버전 관리 전략 — 누락**

context_version "4.0"이 JSON 스키마에 포함되어 있지만, **스키마 진화(schema evolution) 전략**이 정의되지 않았다:
- v4 → v5로 스키마가 변경되면 기존 생성된 CompanyContext/CandidateContext와의 호환성은?
- 피처 추가/삭제 시 historical 매핑 결과의 연속성은?
- **권고**: breaking vs non-breaking 변경 정의, 마이그레이션 전략 수립

**[U-4] 시간 감쇠(temporal decay) 통합 설계 — 부족**

시간 관련 감쇠가 여러 곳에 분산되어 있으나 통합 설계가 없다:
- Person.freshness_weight (이력서 갱신 기준)
- PastCompanyContext.confidence 감쇠 (재직~현재 시간차)
- 뉴스 기사 나이 감쇠

이들 간의 관계와 전체 매칭에서의 상호작용이 정의되지 않았다. 예를 들어:
- 5년 전에 갱신된 이력서(freshness_weight=0.3)에서 추출된 SituationalSignal의 confidence는 추가 감쇠를 받아야 하는가?
- **권고**: temporal decay의 통합 정책 수립 (단일 감쇠점 vs 다중 감쇠)

### 5.2 경계 사례 처리 부족

**[U-5] 프리랜서/다중 재직 처리 — 경미**

Career 데이터에서 기간이 겹치는 경우(프리랜서, 겸직)의 처리가 정의되지 않았다. Experience 모델이 순차적 Chapter를 가정하는데, 병렬 경험은 어떻게 표현하는가?

**[U-6] 외국인 후보/외국 기업 처리 — 경미**

임베딩 모델이 multilingual을 지원한다고 했지만, 온톨로지 수준에서 다국어 데이터(영문 이력서, 외국 기업)의 처리 규칙이 없다. v1에서 한국어만 대상으로 한다면 명시적 제외 필요.

**[U-7] 산업 코드 계층 간 비교 로직 불완전 — 중간**

F3 domain_fit에서 "candidate INDUSTRY_SUBCATEGORY(2depth)와 company INDUSTRY(3depth) 비교 시 상위로 올려 비교"한다고 했는데, 실제로 INDUSTRY(3depth) → INDUSTRY_SUBCATEGORY(2depth) 매핑 방법이 00_data_source_mapping에는 있으나 03_mapping_features의 compute_domain_fit()에는 반영되지 않았다. industry_code[:3] 비교로 대분류 일치를 판단하는데, 이것이 code-hub 코드 체계에서 실제로 유효한지 확인 필요.

---

## 6. 문서 품질 이슈

### 6.1 문서 간 중복

| 중복 내용 | 중복 위치 | 권고 |
|---|---|---|
| 서비스 풀 필터링 로직 | 00 §3.1, 02 §5, 03 §0.1 | 정본을 00에 두고 나머지는 참조 |
| F1~F5 ACTIVE 비율 전망 | 00 §6.5, 03 §7.3 | 정본을 03에 두고 00은 제거 |
| 추출 파이프라인 흐름 | 00 §5.2, 02 §5 | 거의 동일한 흐름도가 2곳에 존재, 정본 하나로 통합 |
| Person 보강 속성 | 00 §3.5, 02 §2.6, 04 §1.1 | 3곳 중복, 정본을 02에 두고 나머지 참조 |
| v1 매칭 범위 EXPERIENCED 제한 | 00 §3.1, 02 §0.1, 03 §0.1, 04 §1.1 | 4곳 중복, 정본을 03에 두고 나머지 참조 |

### 6.2 변경 이력 가독성

모든 문서의 헤더에 v12~v17 변경 이력이 `<details>` 태그로 중첩되어 있다. 이것 자체는 문제가 아니지만, 변경 이력이 "[R-1]", "[S-5]", "[U-8]", "[N14-1]" 등 리뷰 피드백 코드로 관리되어 외부에서 맥락을 이해하기 어렵다. 02_v4_amendments에서 이관 현황을 관리하고 있지만, v14+ 리뷰 피드백의 추적성이 낮다.

**권고**: 리뷰 피드백 코드 → 변경 내용 매핑 테이블을 02_v4_amendments에 추가하거나, CHANGELOG 파일로 분리

### 6.3 섹션 번호 오류

`00_data_source_mapping`의 §11(v11→v12 마이그레이션 영향) 내부에 "10.1 변경 없는 항목", "10.2 변경 항목 요약"으로 번호가 맞지 않음. 실제로는 §11.1, §11.2여야 함.

---

## 7. 피처별 온톨로지 타당성 평가

### F1 stage_match

| 항목 | 평가 |
|---|---|
| 개념적 타당성 | 높음 — "기업의 현재 성장 단계를 후보가 경험했는가"는 채용에서 핵심 질문 |
| STAGE_SIMILARITY 매트릭스 | 합리적이나 비대칭 근거 불충분 (GROWTH→EARLY 0.50 > EARLY→GROWTH 0.30의 이유가 암묵적) |
| stage 추정 로직 | Rule 기반 1차 추정(직원수/설립연도)은 합리적이나, JD LLM fallback의 confidence 0.50이 너무 낮은지 아닌지 판단 근거 부족 |
| **개선 필요** | STAGE_SIMILARITY 비대칭의 명시적 근거 추가 (예: "성장기 기업은 초기 경험자를 적응시킬 수 있지만, 초기 기업은 성장기 경험만 있는 사람이 적응하기 어려움") |

### F2 vacancy_fit

| 항목 | 평가 |
|---|---|
| 개념적 타당성 | 높음 — hiring_context(BUILD_NEW/SCALE_EXISTING/RESET/REPLACE)와 SituationalSignal의 매칭은 직관적 |
| VACANCY_SIGNAL_ALIGNMENT 테이블 | 대체로 합리적이나, REPLACE의 빈 매핑이 아쉬움. "충원"도 이전 담당자와 유사한 상황 경험이 유리할 수 있음 |
| v17 naming 개선 | scope_type → hiring_context 변경은 적절 (Candidate의 scope_type과 혼동 해소) |
| Outcome 미활용 결정 | 합리적 — taxonomy 기반 매칭이 자유 텍스트 비교보다 v1에서 현실적 |
| **개선 필요** | REPLACE 공고에서도 "이전 담당자가 LEAD였다면 LEAD 경험이 strong" 같은 role 기반 매칭 로직 검토 |

### F3 domain_fit

| 항목 | 평가 |
|---|---|
| 개념적 타당성 | 높음 — 산업/도메인 적합도는 채용의 기본 필터 |
| 하이브리드 접근 | Embedding + industry code 보너스는 합리적 |
| industry code 비교 | `industry_code[:3]` 문자열 슬라이싱으로 대분류 일치를 판단하는 것은 code-hub 코드 체계에 의존적. 코드 체계가 hierarchical prefix가 아니면 오동작 가능 |
| **개선 필요** | code-hub INDUSTRY 코드가 실제로 prefix 기반 계층 구조인지 확인. 아니라면 `lookup_common_code`로 group_code를 조회하는 방식으로 변경 |

### F4 culture_fit

| 항목 | 평가 |
|---|---|
| 개념적 타당성 | 높음 — 문화 적합도는 채용 성공의 핵심 요소이나 측정이 어려움 |
| 현실성 | 매우 낮음 — v1 ACTIVE <10% |
| 3 facets 설계 | speed/autonomy/process는 합리적 분류이나, 이력서에서 work_style_signals를 추출하는 것 자체가 비현실적 (v1 인정) |
| v1 포함 근거 | v17 R-6의 4가지 근거는 논리적이나, **비활성 피처를 유지하는 비용(코드 복잡도, 테스트, 문서 관리)을 과소평가**하고 있을 가능성 |
| **권고** | v1에서 F4를 "정의만 유지, 구현은 스킵"으로 명확히 구분. 파이프라인에서 F4 계산 로직 자체를 구현하지 않고, INACTIVE를 하드코딩으로 반환하는 것이 실용적 |

### F5 role_fit

| 항목 | 평가 |
|---|---|
| 개념적 타당성 | 높음 — 시니어리티/역할 매칭은 채용의 기본 |
| ROLE_PATTERN_FIT 매트릭스 | 초기값으로 합리적이나, 조합이 불완전 (전체 5x8=40 조합 중 일부만 정의, 나머지는 기본값 0.50) |
| scope_type → seniority 변환 | IC의 경력 연수 기반 세분화(3/6년 경계)는 한국 채용 시장에 적합 |
| **개선 필요** | ROLE_PATTERN_FIT 매트릭스를 전체 조합으로 확장하거나, "정의되지 않은 조합은 기본값 0.50"이라는 규칙의 의미를 명확히 |

---

## 8. SituationalSignal Taxonomy 평가

14개 taxonomy는 v17의 핵심 설계 결정 중 하나이다.

### 강점
- 고정 taxonomy로 LLM 자유 생성 방지 → 일관성 확보
- 카테고리 4개(성장 단계/조직 변화/기술 변화/비즈니스)는 직관적 분류
- hiring_context와의 매핑이 명확 (VACANCY_SIGNAL_ALIGNMENT)

### 약점 및 개선 필요 사항

**[T-1] OTHER 카테고리의 남용 가능성**

14개 라벨에 해당하지 않는 상황은 모두 OTHER로 분류된다. LLM이 판단이 어려운 경우 OTHER를 과다 선택할 위험. **OTHER의 비율이 30%를 넘으면 taxonomy 확장이 필요**하다는 모니터링 기준을 추가해야 한다.

**[T-2] 일부 라벨 간 경계 모호**

- SCALE_UP vs TEAM_SCALING: "팀이 5명에서 20명으로 확장"은 둘 다 해당. 배타성 가이드 없음
- NEW_SYSTEM_BUILD vs TECH_STACK_TRANSITION: "기존 모놀리스를 MSA로 전환하며 신규 시스템 구축"은 둘 다 해당
- **권고**: SituationalSignal도 structural_tensions처럼 primary + related 구조 도입 검토, 또는 복수 선택 허용 규칙 명확화

**[T-3] 도메인 특화 라벨 부재**

현재 taxonomy는 기술 기업 중심이다. 제조/유통/금융 등 전통 산업에서의 상황 경험은 14개로 포착하기 어려울 수 있다. v1이 IT 기업 중심이라면 문제없으나, 대상 산업 범위를 명시해야 한다.

---

## 9. 개선 권고 요약

### 높은 우선순위 (v17→v18 반영 권고)

| # | 권고 | 대상 문서 | 근거 |
|---|---|---|---|
| R-1 | 온톨로지 설계와 구현 상세 분리 — pseudo-code를 구현 명세로 이동 | 00, 06 | [O-1], [O-2] |
| R-2 | Outcome 추출의 v1 ROI 판단 및 결정 기록 | 02, 03 | [U-1] |
| R-3 | F1 stage_match ACTIVE 비율 파일럿 검증 계획 추가 | 03 | [F-4] |
| R-4 | SituationalSignal 추출 품질 검증 계획 (workDetails 길이별) | 02 | [F-5] |
| R-5 | 문서 간 중복 정리 — 정본 지정 후 참조로 변경 | 전체 | §6.1 |

### 중간 우선순위 (v1 파일럿 후 반영)

| # | 권고 | 대상 문서 | 근거 |
|---|---|---|---|
| R-6 | STAGE_SIMILARITY 비대칭 근거 명문화 | 03 | F1 평가 |
| R-7 | industry_code prefix 기반 비교의 code-hub 정합성 확인 | 03 | [U-7] |
| R-8 | SituationalSignal OTHER 비율 모니터링 기준 추가 | 02 | [T-1] |
| R-9 | confidence 이중 감쇠 vs 단순 가중 평균 파일럿 비교 | 03 | [O-7] |
| R-10 | 다중 이력서 / 기간 겹침 처리 규칙 정의 | 00, 02 | [U-2], [U-5] |

### 낮은 우선순위 (v2 이후)

| # | 권고 | 대상 문서 | 근거 |
|---|---|---|---|
| R-11 | 스키마 버전 관리 전략 수립 | 전체 | [U-3] |
| R-12 | temporal decay 통합 정책 | 전체 | [U-4] |
| R-13 | 다국어/외국 기업 대상 범위 명시 | 전체 | [U-6] |
| R-14 | NEEDS_SIGNAL 매핑 테이블 전문가 합의 재검토 | 04 | [F-7] |

---

## 10. 결론

v17 온톨로지 스키마는 채용 도메인의 복잡성을 잘 포착하고, 실측 데이터에 기반한 현실적 설계를 제시한다. 특히 **Evidence-first 원칙, Graceful Degradation, 의도적 제외 명문화**는 온톨로지 설계의 모범 사례로 평가할 수 있다.

가장 큰 개선 필요 사항은 **온톨로지 설계와 구현 상세의 분리**이다. 현재 문서는 "무엇을 구조화할 것인가(what)"와 "어떻게 구현할 것인가(how)"가 혼재되어 있어, 온톨로지 설계의 본질적 결정사항을 파악하기 어렵다. 이 분리가 이루어지면 문서 분량이 크게 줄고, 설계 결정의 추적성도 높아질 것이다.

v1 파일럿은 현재 설계 기반으로 진행해도 무방하나, **F1 stage_match ACTIVE 비율**, **SituationalSignal 추출 품질**, **confidence 이중 감쇠 효과**에 대한 파일럿 검증을 반드시 포함할 것을 권고한다.
