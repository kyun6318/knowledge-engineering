> 작성일: 2026-03-12
> 01.ontology/results/schema/v23/00_data_source_mapping.md §8, §10에서 이동.
> 구현 로드맵 및 LLM 비용 추정을 서비스 영역으로 분리.

---

## 1. 구현 로드맵

### Phase 1: 기반 데이터 정제 (구현 전 선행)

| 순서 | 과제 | 난이도 | 영향 범위 |
| --- | --- | --- | --- |
| 1 | days_worked (duration_months) 계산 | 낮음 | Chapter, F1, F5 |
| 2 | certificate type 매핑 변환 | 낮음 | 코드 매핑 정합성 |
| 3 | 회사명 정규화 파이프라인 | 중간 | Organization, Chapter->Org 엣지, F1 |
| 4 | 스킬 정규화 (경량 + 임베딩 폴백) | 높음 | Skill, Chapter->Skill 엣지, F3 |
| 5 | 전공명 정규화 (Tier 3 임베딩) | 중간 | F3 domain_fit 보조 |

### Phase 2: 핵심 노드/엣지 구축

| 순서 | 과제 | 의존성 |
| --- | --- | --- |
| 1 | Person + Chapter 노드 생성 | Phase 1-1 |
| 2 | Organization 노드 + OCCURRED_AT 엣지 | Phase 1-3 |
| 3 | Industry 노드 + IN_INDUSTRY 엣지 | codehub 63개 코드 (즉시 가능) |
| 4 | Role 노드 + PERFORMED_ROLE 엣지 | codehub JOB_CLASSIFICATION 242개 코드 |
| 5 | Skill 노드 + USED_SKILL 엣지 | Phase 1-4 |

### Phase 3: LLM 추출 노드/엣지

| 순서 | 과제 | 의존성 |
| --- | --- | --- |
| 1 | Outcome 추출 (careerDescription + selfIntroduction) | Phase 2-1 |
| 2 | SituationalSignal 추출 | Phase 2-1 |
| 3 | Person 속성 보강 (role_evolution_pattern, primary_domain) | Phase 3-1, 3-2 |

### Phase 4: 기업측 + 매핑

| 순서 | 과제 | 의존성 |
| --- | --- | --- |
| 1 | job-hub 상세 분석 | 독립 (병렬 가능) |
| 2 | Vacancy 노드 (구조화 + LLM 추출) | Phase 4-1 |
| 3 | MAPPED_TO 엣지 (매핑 피처 F1~F5 계산) | Phase 2, 3 완료 |

---

## 2. LLM 비용 총 추정

전체 파이프라인에서 LLM 호출이 필요한 지점과 예상 비용 산정

### 2.1 LLM 호출 지점 및 비용 추정

| # | 호출 지점 | 대상 규모 | 평균 입력 토큰 | 모델 | 예상 비용 |
| --- | --- | --- | --- | --- | --- |
| L1 | CandidateContext: Outcome/Signal 추출 (careerDesc+selfIntro) | ~2.2M 이력서 (서비스 풀 70%) | ~1K tokens | Gemini 2.0 Flash | **~$220** |
| L2 | CandidateContext: scope_type LLM fallback (workDetails) | ~1.0M 이력서 (구조화 미매칭 분) | ~200 tokens | Gemini 2.0 Flash | **~$20** |
| L3 | CandidateContext: role_evolution 추출 | ~2.2M 이력서 | ~500 tokens | Gemini 2.0 Flash | **~$110** |
| L4 | CandidateContext: work_style_signals 추출 | ~2.2M 이력서 | ~500 tokens | Gemini 2.0 Flash | **~$110** |
| L5 | CompanyContext: vacancy hiring_context/description | 공고 수 미정 (추정 ~100K) | ~1K tokens | Gemini 2.0 Flash | **~$10** |
| L6 | CompanyContext: operating_model facets | ~100K 공고 | ~1K tokens | Gemini 2.0 Flash | **~$10** |
| L7 | CompanyContext: stage_estimate LLM fallback | ~30K 공고 (Rule 미매칭 분) | ~500 tokens | Gemini 2.0 Flash | **~$1.5** |
| L8 | 크롤링: 홈페이지+뉴스 추출 | ~1,000 기업 × ~10페이지 | ~2K tokens | Gemini 2.0 Flash | **~$2** (월간 $107 포함) |
|  | **합계 (1회 전체 처리)** |  |  |  | **~$484** |

> 비용 기준: Gemini 2.0 Flash input $0.10/1M tokens, output $0.40/1M tokens (2026-03 기준)
출력 토큰은 입력의 ~30%로 추정하여 합산
>
> **[v5] Claude Haiku 시나리오**: 02.knowledge_graph의 1순위 모델 Claude Haiku 4.5 Batch($0.40/$2.00 per 1M tokens, 50% 할인 적용)로 산정 시, CandidateContext DB만 **$496**(01_extraction_pipeline.md §3.6)이며, 전체 파이프라인 비용은 ~$1,700~2,000 수준이다. Gemini Flash 대비 4~5배 차이가 발생하므로, **Phase 0 모델 선정 결과에 따라 본 테이블을 갱신**한다. Provider 추상화(06_graphrag_cost.md 참조)를 Phase 0에서 설계하여 전환 비용을 최소화한다.
>
> 실제 비용이 ~$700까지 상승할 가능성이 있다. **Phase 3 착수 전 L1에 대해 샘플 10건으로 실측 후 비율을 보정해야 한다.** 전체 비용이 $1,000 이내라면 관리 가능 범위 판단

### 2.2 처리 시간 추정

| 단계 | 대상 규모 | 동시 처리 수 | 예상 소요 시간 |
| --- | --- | --- | --- |
| L1 Outcome/Signal 추출 | 2.2M건 | 50 병렬 | ~44시간 |
| L2~L4 기타 CandidateContext | 2.2M건 | 50 병렬 | ~30시간 |
| L5~L7 CompanyContext | ~100K건 | 50 병렬 | ~1시간 |
| L8 크롤링 | 1,000기업 | 10 병렬 | ~5시간 |
| **전체** |  |  | **~80시간 (3.3일)** |

> **결론**: 1회 전체 파이프라인 LLM 비용은 **~$500 이내**로 관리 가능한 수준이다. 증분 처리(신규/변경분만) 시 월간 비용은 이보다 크게 감소한다.
