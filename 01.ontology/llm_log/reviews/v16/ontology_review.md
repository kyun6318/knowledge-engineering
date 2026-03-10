# v16 온톨로지 스키마 리뷰

> 리뷰 일시: 2026-03-10
> 리뷰 대상: `results/schema/v16/` 전체 (00~06)
> 리뷰 기준: README.md와의 방향성 일치, 실현 가능성/타당성, 과도/부족 설계
> 범위: 온톨로지 설계 관점 (KG 구현은 02.knowledge_graph에서 진행)

---

## 1. 종합 평가

v16은 16차에 걸친 반복 개선을 거친 성숙한 온톨로지 설계다. README에서 제시한 "기업-인재 맥락 매칭"이라는 핵심 방향과 잘 정렬되어 있으며, 실측 데이터(v12 데이터 분석 v2.1)를 기반으로 설계 결정을 내린 점이 강점이다. 다만 16번의 반복으로 인해 문서 간 중복이 많고, 일부 영역에서 과도한 설계가 관찰된다.

**등급: B+ (양호, 부분 개선 필요)**

---

## 2. README 방향성 일치 분석

### 2.1 잘 정렬된 부분

| README 방향 | v16 반영 상태 | 평가 |
|---|---|---|
| CompanyContext/CandidateContext 독립 생성 | 01/02에서 명확히 분리, 독립성 원칙 명문화 | **우수** |
| Evidence-first 원칙 | 모든 claim에 Evidence 구조 필수, source ceiling 적용 | **우수** |
| 5개 MappingFeatures 피처 | F1~F5 계산 로직 상세 정의, Graceful Degradation 적용 | **우수** |
| SituationalSignal 14개 taxonomy | 고정 taxonomy, LLM 자유 생성 방지 | **우수** |
| Graph Schema 9종 노드 | Person/Organization/Chapter/Vacancy 등 정의 완료 | **우수** |
| 데이터 소스 Tier 체계 | T1~T7 상한 정의, 교차 검증 규칙 | **우수** |
| 부분 완성 허용 (Graceful Degradation) | 피처별 INACTIVE 처리, null 안전 처리 | **우수** |

### 2.2 방향은 맞지만 보완이 필요한 부분

| README 방향 | v16 상태 | 이슈 |
|---|---|---|
| 버전 로드맵 (v1→v1.1→v2) | 각 문서에 로드맵 명시 | 문서별로 v1/v1.1/v2 구분이 미세하게 다름. 통합 로드맵 테이블이 README에만 존재하고 세부 문서와 미묘한 불일치 |
| 평가 전략 | 05_evaluation_strategy에 상세 실험 설계 | 온톨로지 설계 문서에 평가 실험 설계가 과도하게 상세. 별도 프로젝트 문서로 분리 권장 |

### 2.3 불일치 사항

| 항목 | README 기술 | v16 실제 | 심각도 |
|---|---|---|---|
| industry_code 예시 | NICE 코드 "J63112" 사용 | v11부터 code-hub INDUSTRY 코드가 primary, NICE는 보조 | **낮음** — README 예시 업데이트 필요 |
| CandidateContext JSON 예시 | `past_company_context.industry_code: "J63112"` | code-hub 코드여야 하나 예시가 NICE 코드 유지 | **낮음** — 02_candidate_context §3 JSON 예시 미수정 |
| Tier 수 | README: T1~T6 | v16: T1~T7 (T7 내부 문서 추가) | **낮음** — README 동기화 필요 |

---

## 3. 실현 가능성 및 타당성 분석

### 3.1 높은 실현 가능성 (즉시 구현 가능)

| 영역 | 근거 |
|---|---|
| **구조화 데이터 기반 Context 생성** | code-hub 매핑, NICE 조회, career 구조화 필드 등 이미 접근 가능한 데이터에 기반. fill rate 실측치가 설계의 현실성을 뒷받침 |
| **days_worked 계산** | 단순 DATERANGE 계산, 난이도 낮음 |
| **Certificate type 매핑** | 2줄 변환 테이블, 즉시 구현 가능 |
| **Industry/Role 마스터 노드** | code-hub 63개/242개 코드 기반, 사전 생성 가능 |
| **SituationalSignal 공유 노드** | 14개 고정 taxonomy, 즉시 생성 가능 |

### 3.2 중간 실현 가능성 (노력 필요하지만 가능)

| 영역 | 리스크 | 완화 방안 |
|---|---|---|
| **LLM 추출 파이프라인 (L1~L4)** | 2.2M 이력서 × LLM 호출 = ~80시간, $500 비용 | 증분 처리, 병렬화로 관리 가능. 비용은 수용 범위 |
| **회사명 정규화** | 4.48M 고유값, BRN 62%만 보유 | BRN 1차 + 유사도 2차 전략은 합리적. 다만 정확도 검증 계획이 부족 |
| **스킬 정규화** | 97.6% 비표준, 임베딩 fallback | 임베딩 기반 비교 전략은 현실적. 다만 임베딩 매칭 정확도 85% 목표가 검증 전 |
| **scope_type 추정** | 직책(29.45%)/직급(39.16%) 저 fill rate | 3단계 fallback (구조화→구조화→LLM)은 합리적 설계 |

### 3.3 실현 가능성 우려 사항

| 영역 | 우려 | 심각도 |
|---|---|---|
| **F4 culture_fit** | v1에서 <10% ACTIVE 예상. work_style_signals 데이터 부재로 사실상 죽은 피처 | **중간** — v1에서 제거하고 v2에서 도입하는 것이 명확할 수 있음 |
| **PastCompanyContext의 estimated_stage_at_tenure** | 현재 시점 NICE 데이터로 과거 시점 stage를 "추정"하는 것의 정확도. 5년 전 재직한 회사의 현재 직원수로 당시 stage를 추론하는 것은 근본적으로 부정확 | **중간** — 문서에서 인정하고 있으나, confidence 감쇠(years_gap × 0.08)가 충분한지 의문 |
| **CareerDescription FK 부재** | career_id FK 없이 LLM이 텍스트 컨텍스트로 귀속 판단 → 복수 경력 이력서에서 오귀속 리스크 | **중간** — 데이터 구조적 한계이므로 설계로 해결 불가. LLM 귀속 정확도 검증 계획 필요 |
| **operating_model facets의 실효성** | JD 키워드 카운트 기반 추출, confidence 0.30~0.45. 광고성 필터링에도 불구하고 JD 자체가 마케팅 문서 | **낮음** — v1에서 낮은 confidence로 시작하고 크롤링으로 보강하는 전략은 합리적 |

### 3.4 LLM 비용/시간 추정의 타당성

| 항목 | 평가 |
|---|---|
| 총 비용 ~$500 | **합리적**. Gemini 2.0 Flash 기준 현실적 추정. v15에서 output token 비율 보정 주의사항 추가도 적절 |
| 처리 시간 ~80시간 | **수용 가능**. 50 병렬 기준이나, API rate limit과 에러 재시도 감안하면 실제로는 더 걸릴 수 있음 |
| 크롤링 비용 ~$107/월 | **매우 합리적**. GCP 서버리스 기반 비용 최적화 |

---

## 4. 과도한 설계 (Over-Engineering)

### 4.1 심각한 과도 설계

| 항목 | 내용 | 권장 |
|---|---|---|
| **05_evaluation_strategy의 분량** | 827줄. 온톨로지 설계 문서 안에 실험 설계가 과도하게 상세. 실험 절차, 함수 시그니처, 의사결정 트리, 평가 체크리스트까지 포함 | 온톨로지 설계에서는 "평가 방향과 성공 기준"만 명시하고, 상세 실험 설계는 별도 프로젝트 문서로 분리 |
| **06_crawling_strategy의 분량** | 1,493줄. 크롤링 구현 상세(Playwright, Cloud Run, Eventarc, BigQuery DDL)가 온톨로지 설계 범위를 넘어섬 | 온톨로지 관점에서는 "어떤 데이터를 어떤 필드에 매핑하는가"만 필요. 크롤링 구현 상세는 별도 모듈 설계 문서로 분리 |
| **문서 간 중복** | 추출 파이프라인이 00, 01, 02에 각각 기술. fill rate 데이터가 00, 02, 03에 반복. 재생성 조건이 01, 02에 교차 참조 | 정본(Single Source of Truth) 원칙 적용. 00_data_source_mapping을 정본으로 하고 나머지는 참조만 |

### 4.2 경미한 과도 설계

| 항목 | 내용 | 권장 |
|---|---|---|
| **structural_tensions 8개 taxonomy** | v1에서 70%+ null 예상인데 배타성 가이드, related_tensions 체계까지 정의 | v16에서 "v1.1+ 상세화" 표시를 추가한 것은 적절. 다만 v1 문서에서 이 부분을 접을 수 있도록 구조화 권장 |
| **confidence 이중 감쇠** | overall_match_score 계산에서 confidence를 가중치로 사용하는 이중 감쇠. 설계 의도 주석이 있지만 복잡도 증가 | v1 파일럿에서 단순 가중 평균과 비교 실험을 먼저 하고, 이중 감쇠가 실제로 효과적인지 검증 후 결정 |
| **MAPPED_TO TTL/아카이빙 정책** | v1에 매핑 결과가 없는 상태에서 아카이빙 정책 정의 | v16에서 "v1.1+ 검토" 표시 추가한 것은 적절. 문서에서는 정책 방향만 남기고 상세 코드 제거 권장 |
| **BigQuery 테이블 스키마** | 03_mapping_features에 CREATE TABLE DDL 포함 | 온톨로지 설계에서는 논리적 스키마(필드 정의)만 필요. 물리적 DDL은 구현 문서로 |
| **Neo4j 인덱스/동기화 전략** | 04_graph_schema에 인덱스, 동기화, DLQ, retry 정책까지 포함 | 그래프 온톨로지(노드/엣지/속성 정의)와 구현 전략(인덱스/동기화)을 분리 |

---

## 5. 부족한 설계 (Under-Engineering)

### 5.1 심각한 부족

| 항목 | 내용 | 권장 |
|---|---|---|
| **Outcome의 정규화 부재** | Outcome은 LLM이 자유 텍스트로 추출하는데, OutcomeType 5개 분류 외에 Outcome 자체의 비교/집계 방법이 미정의. "MAU 10x"와 "사용자 10배 증가"가 같은 성과인지 판단하는 방법 없음 | Outcome 비교 전략 정의 필요: (1) outcome_type 기반 카테고리 매칭, (2) metric_value 정규화 규칙 (숫자 추출 + 단위 통일), (3) description 임베딩 유사도 |
| **Vacancy ↔ SituationalSignal 매핑의 자동 추론 검증** | Q4에서 SCOPE_TO_SIGNALS 매핑이 하드코딩되어 있으나, 이 매핑의 타당성 검증 계획이 없음. BUILD_NEW → [NEW_SYSTEM_BUILD, EARLY_STAGE, PMF_SEARCH, TEAM_BUILDING] 매핑이 실제로 적절한가? | NEEDS_SIGNAL 자동 추론의 정확도를 파일럿에서 검증하는 계획 추가. 50건 JD에서 자동 추론 결과 vs 전문가 판단 비교 |
| **NEW_COMER 온톨로지 부재** | v1에서 EXPERIENCED만 매칭 대상이라는 것은 합리적이나, NEW_COMER(30.9%)의 Person 노드 최소 속성 정의가 불명확. Education/Certificate 기반 매칭을 위한 온톨로지 확장 방향이 v2 로드맵에만 간략히 언급 | 02_candidate_context에 NEW_COMER용 최소 온톨로지(Education 노드, Certificate 노드, Major 노드)의 방향을 명시. v2에서 추가할 노드/엣지의 후보를 사전 정의 |

### 5.2 중간 부족

| 항목 | 내용 | 권장 |
|---|---|---|
| **시간 차원의 모델링** | Chapter에 period_start/period_end가 있지만, 온톨로지 수준에서 "시간에 따른 변화"를 어떻게 다루는지 미정의. Organization의 stage_label이 시간에 따라 변하는데, 과거 시점의 stage를 어떻게 표현하는가? | PastCompanyContext의 estimated_stage_at_tenure가 이를 부분적으로 다루지만, Organization 노드 자체는 현재 시점 스냅샷. 시점별 Organization 상태(stage, employee_count)를 별도 표현하는 방안 검토 필요 (v2) |
| **매칭의 방향성** | 현재 설계는 "Vacancy → Person" 단방향 매칭. 역방향("이 후보에게 적합한 공고 추천")의 온톨로지 지원이 미정의 | MAPPED_TO 엣지가 양방향 탐색 가능하긴 하나, 후보 관점의 매칭 피처(예: 후보의 희망 조건 vs 기업 조건)가 부재. v2에서 WorkCondition(희망 근무조건) 반영 검토 |
| **다국어/다문화 확장성** | 한국 시장 특화 설계(NICE, code-hub, 한국어 JD). 글로벌 확장 시 온톨로지 변경 범위가 미정의 | v1은 한국 시장 집중이 맞지만, Industry 노드의 코드 체계, Role 노드의 정규화 등에서 국제 표준(ISCO, ISIC) 호환 가능성을 메모 수준으로 남겨두면 좋음 |
| **Skill 노드의 시간적 감쇠** | 5년 전 사용한 스킬과 현재 사용 중인 스킬을 동일하게 USED_SKILL로 연결. 스킬의 현재 유효성(recency)이 반영되지 않음 | USED_SKILL 엣지에 `last_used_year` 또는 `recency_weight` 속성 추가 고려 |

### 5.3 경미한 부족

| 항목 | 내용 | 권장 |
|---|---|---|
| **Role 노드의 계층 구조** | code-hub JOB_CLASSIFICATION이 3depth 계층인데, Role 노드는 flat. 같은 category 내 Role 간 관계 미정의 | v1에서는 flat으로 충분. v2에서 PARENT_ROLE 관계 검토 |
| **Skill 간 관계** | Co-occurrence 클러스터(Illustrator-Photoshop Lift 6.79) 데이터가 있으나 온톨로지에 반영되지 않음 | v2에서 RELATED_SKILL 또는 SkillGroup 노드 검토 |
| **Experience 간 transition 패턴** | NEXT_CHAPTER 엣지에 gap_months만 있고, transition 유형(동일 회사 내 이동/이직/창업 등)이 미분류 | v2에서 transition_type 속성 추가 검토 |

---

## 6. 설계 일관성 검토

### 6.1 일관성이 우수한 부분

- **Evidence 통합 모델**: 모든 문서에서 동일한 Evidence 인터페이스 사용
- **confidence 체계**: source ceiling, 교차 검증 boost/penalty 규칙이 일관적
- **Graceful Degradation**: 모든 피처에서 동일한 패턴(필수 입력 null → INACTIVE)
- **Taxonomy 고정**: SituationalSignal 14개, OutcomeType 5개, ScopeType 5개, StageLabel 5개 등 일관된 enum 체계

### 6.2 일관성 문제

| 항목 | 내용 | 심각도 |
|---|---|---|
| **JSON 예시의 industry_code** | 02_candidate_context §3 JSON 예시에서 `"industry_code": "J63112"` (NICE 코드) 사용. v14에서 01_company_context는 수정했으나 02는 미수정 | **낮음** |
| **source_type enum 누락** | Evidence의 source_type enum에 `"code_hub"`가 없음. code-hub 기반 정규화 결과의 extraction_method는 있지만 source_type은 미정의 | **낮음** — code-hub는 정규화 도구이지 데이터 소스가 아니므로 현재 구조가 맞을 수 있음. 다만 명시적으로 제외 이유를 문서화 권장 |
| **scope_type 용어 혼용** | Candidate의 scope_type(IC/LEAD/HEAD/FOUNDER)과 Vacancy의 scope_type(BUILD_NEW/SCALE_EXISTING/RESET/REPLACE)이 같은 필드명을 다른 의미로 사용 | **중간** — 혼동 가능. Vacancy 측은 `vacancy_type` 또는 `hiring_context`로 명칭 변경 권장 |

---

## 7. 문서 구조 개선 제안

### 7.1 현재 구조의 문제

1. **온톨로지 정의와 구현 설계가 혼재**: 논리적 온톨로지(개념, 관계, 제약)와 물리적 구현(BigQuery DDL, Neo4j 인덱스, Cloud Run, Eventarc)이 같은 문서에 공존
2. **문서 간 내용 중복**: 추출 파이프라인이 00, 01, 02에 각각 기술. 피처별 ACTIVE 비율이 00, 03에 중복
3. **변경 이력이 문서 헤더에 과도하게 축적**: v12~v16 변경 이력이 모든 문서 상단에 누적

### 7.2 권장 구조

```
현재:
  00_data_source_mapping.md    (1,092줄 — 데이터 매핑 + 파이프라인 + 비용 + 로드맵)
  01_company_context.md        (627줄 — 기업 맥락 + JSON 스키마 + 재생성 조건)
  02_candidate_context.md      (761줄 — 후보 맥락 + JSON 스키마 + 재생성 조건)
  03_mapping_features.md       (889줄 — 매핑 피처 + BigQuery DDL + SQL 예시)
  04_graph_schema.md           (684줄 — 노드/엣지 + 인덱스 + 동기화 + 규모 추정)
  05_evaluation_strategy.md    (827줄 — 실험 설계 전체)
  06_crawling_strategy.md      (1,493줄 — 크롤링 전체 구현)

권장 분리:
  [온톨로지 코어] — 개념/관계/제약 중심
    01_company_context.md      — 기업 맥락 개념 정의 (축소)
    02_candidate_context.md    — 후보 맥락 개념 정의 (축소)
    03_mapping_features.md     — 매핑 피처 정의 + 계산 로직 (축소)
    04_graph_schema.md         — 노드/엣지/속성 정의만 (축소)

  [데이터 설계] — 구현 관점
    10_data_source_mapping.md  — 데이터 매핑 정본
    11_extraction_pipeline.md  — 추출 파이프라인 통합
    12_implementation_roadmap.md — 구현 로드맵 + 비용

  [별도 프로젝트 문서]
    evaluation_experiment.md   — 실험 설계 (독립)
    crawling_strategy.md       — 크롤링 구현 (독립)
```

---

## 8. 핵심 권장 사항 (우선순위 순)

### P1 (v16 즉시 수정 권장)

| # | 항목 | 사유 |
|---|---|---|
| R-1 | **scope_type 명칭 혼동 해소** | Candidate scope_type과 Vacancy scope_type이 같은 이름으로 다른 의미. `vacancy_scope_type` 또는 `hiring_context`로 변경 |
| R-2 | **02_candidate_context JSON 예시의 industry_code 수정** | "J63112" → code-hub INDUSTRY 코드로 수정 (v14에서 01은 수정했으나 02 미반영) |
| R-3 | **Outcome 비교 전략 추가** | MappingFeatures에서 Outcome을 어떻게 활용하는지 명시. 현재 F2 vacancy_fit에서 Outcome을 사용하지 않고 SituationalSignal만 사용 — 이것이 의도적이라면 명시, 아니라면 활용 방안 추가 |

### P2 (다음 버전에서 개선)

| # | 항목 | 사유 |
|---|---|---|
| R-4 | **문서 구조 재편** | 온톨로지 코어와 구현 설계 분리. 현재 6개 문서 합계 ~6,300줄은 과다 |
| R-5 | **NEEDS_SIGNAL 자동 추론 검증 계획** | SCOPE_TO_SIGNALS 하드코딩 매핑의 타당성 검증 |
| R-6 | **F4 culture_fit v1 처리 방침 명확화** | <10% ACTIVE 피처를 v1에서 포함할 이유를 명시하거나, v1에서는 4개 피처로 시작하고 v2에서 추가하는 것을 검토 |
| R-7 | **Skill recency 반영** | USED_SKILL 엣지에 시간 속성 추가 (최소한 Chapter의 period로 추론 가능하므로 속성 추가 불필요할 수도 있으나, 명시적 결정 필요) |

### P3 (v2에서 검토)

| # | 항목 | 사유 |
|---|---|---|
| R-8 | **NEW_COMER 온톨로지 확장 방향** | Education/Certificate/Major 노드의 사전 설계 |
| R-9 | **Organization 시간 차원 모델링** | 시점별 stage/규모 표현 방안 |
| R-10 | **역방향 매칭 온톨로지** | 후보 관점의 희망 조건 → 적합 공고 매칭 |

---

## 9. 피처별 설계 품질 세부 평가

### F1 stage_match

| 항목 | 평가 | 비고 |
|---|---|---|
| 개념 정의 | **우수** | "기업 stage와 후보 과거 경험 stage 비교"는 직관적이고 가치 있는 매칭 기준 |
| STAGE_SIMILARITY 매트릭스 | **양호** | 비대칭 설계(GROWTH→EARLY 0.50 > EARLY→GROWTH 0.30)는 도메인 직관에 부합. 다만 초기값이 전문가 판단 기반이므로 캘리브레이션 계획이 중요 |
| duration_bonus/scope_bonus | **양호** | 보너스 가산 방식은 단순하지만 효과적. 다만 보너스 계수(0.15, 0.10)의 근거 미기술 |
| 실현 가능성 | **중간** | PastCompanyContext 의존. NICE 현재 시점 데이터로 과거 stage 추정의 정확도가 핵심 병목 |

### F2 vacancy_fit

| 항목 | 평가 | 비고 |
|---|---|---|
| 개념 정의 | **우수** | "Vacancy scope_type ↔ SituationalSignal 매칭"은 이 온톨로지의 핵심 차별점 |
| VACANCY_SIGNAL_ALIGNMENT 매핑 | **양호** | strong/moderate/weak 3단계 분류는 적절. REPLACE 처리(v16)도 합리적 |
| base_score 설정 | **주의** | strong=0.85, moderate=0.60, weak=0.35의 간격이 고르지 않음. 특히 "no matching signals"일 때 0.15를 반환하는 것이 INACTIVE와 어떻게 다른지 불명확 |
| 실현 가능성 | **중간** | SituationalSignal 추출 품질에 의존. LLM 추출의 일관성이 핵심 |

### F3 domain_fit

| 항목 | 평가 | 비고 |
|---|---|---|
| 개념 정의 | **양호** | Embedding + Industry code 하이브리드는 합리적 |
| 계산 로직 | **주의** | cosine_sim(임베딩) + code_match_bonus + repeat_bonus를 단순 합산. 임베딩 유사도 범위(보통 0.3~0.9)와 보너스(0.15~0.25)의 스케일이 맞는지 검증 필요 |
| industry_code 비교 | **양호** | 3depth→2depth→1depth 계층적 비교, code-hub 기반으로 일관적 |

### F4 culture_fit

| 항목 | 평가 | 비고 |
|---|---|---|
| 개념 정의 | **양호** | speed/autonomy/process facet 비교는 의미 있는 매칭 기준 |
| 실현 가능성 | **낮음** | v1에서 <10% ACTIVE. 사실상 죽은 피처. 문서에서 이를 인정하고 있으나, v1 피처 목록에 포함시키는 이유가 불분명 |
| ALIGNMENT_LOGIC | **과도** | facet_level × ws_value 조합의 전체 매트릭스가 미완성(... 표시). 완성 시 수십 개 엔트리가 필요하며, 검증 없이는 의미 없음 |

### F5 role_fit

| 항목 | 평가 | 비고 |
|---|---|---|
| 개념 정의 | **양호** | seniority + role_pattern 매칭은 직관적 |
| scope_type → seniority 변환 | **양호** | 02_candidate_context에 명확한 변환 규칙. IC의 경력 연수 기반 세분화도 합리적 |
| ROLE_PATTERN_FIT 매트릭스 | **주의** | 불완전(... 표시). 모든 조합을 채우지 않으면 기본값 0.50으로 처리되어 변별력 저하 |

---

## 10. 온톨로지 설계 관점의 핵심 강점

1. **Taxonomy 고정 + Evidence 필수**: LLM 자유 생성을 방지하고 모든 claim에 근거를 요구하는 원칙이 온톨로지의 품질을 보장
2. **Graceful Degradation**: 데이터 불완전성을 전제하고, 부분 데이터로도 안전하게 동작하는 설계
3. **실측 데이터 기반 의사결정**: fill rate, 품질 등급 등 실측치로 설계 결정을 뒷받침
4. **SituationalSignal 공유 노드**: "같은 상황을 경험한 후보"를 탐색할 수 있는 그래프 연결은 이 온톨로지의 핵심 차별점
5. **의도적 제외 명문화**: CompanyTalentSignal, Company 간 관계 등을 제외하면서 이유와 도입 로드맵을 문서화

---

## 11. 결론

v16 온톨로지 스키마는 **방향성과 설계 원칙이 우수**하며, 실측 데이터 기반의 현실적인 설계를 보여준다. 주요 개선 필요 사항은:

1. **문서 구조**: 온톨로지 코어와 구현 설계의 분리 (현재 ~6,300줄 → 코어 ~2,000줄 목표)
2. **scope_type 명칭 혼동**: Candidate vs Vacancy에서 같은 이름의 다른 의미 해소
3. **Outcome 활용 방안**: 추출은 하지만 매칭에서 어떻게 사용하는지 미정의
4. **F4 culture_fit**: v1에서 사실상 비활성 피처의 처리 방침 명확화
5. **NEEDS_SIGNAL 추론 검증**: 하드코딩 매핑의 타당성 검증 계획

이 사항들을 개선하면 v17에서 더 간결하고 실행 가능한 온톨로지 설계가 될 것이다.
