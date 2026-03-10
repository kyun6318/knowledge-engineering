# 구직자 검색 시스템 — Context 정의 v1 최종본

> 기업 맥락 기반 인재 추천 시스템 설계를 위한 **맥락(Context)의 개념 정의 / 산출물 분류 / 시스템 경계 / 스키마 / 운영 규칙** 통합 문서.  
> 본 v1 정의는 **GraphRAG 기반 Context Layer 구축(EPIC 5)** 의 기준 문서로 사용한다.  
> 이 문서는 GraphRAG 설계 및 일정 논의 진입 전 고정(freeze)하는 기준 문서다.

---

## 0. 핵심 정의

**맥락(Context)은 '현재 상태(state)'가 아니라 '어디서 와서 어디로 가는가'를 나타내는 궤적(Trajectory) + 상황(Situation)의 복합이다.**

실무 표현으로는 **"챕터(Chapter)"** 이며, 각 챕터는 변곡점 / 긴장 / 의도된 방향을 포함한다.

- 기업 맥락: **"이 회사/포지션이 지금 어떤 챕터를 살고 있는가"**
- 구직자 맥락: **"이 사람이 어떤 챕터를 살아왔는가"**

### 매칭의 핵심 원리

맥락 매칭은 키워드 매칭이 아니라,  
**"기업이 앞으로 겪을 챕터(미래 벡터)를 후보가 이미 겪었는가(과거 벡터)"** 를 평가하는 것이다.

```
기업 CompanyContext의 미래 벡터  ←→  CandidateContext의 과거 경험 벡터
```

예: "Series A→B 도약을 준비 중인 기업" ↔ "이전 회사에서 Series A→B 전환을 통과한 후보"

---

## 1. 산출물(Artifacts) 4종

| # | 산출물 | 정의 | 생성 소스 |
|---|---|---|---|
| 1 | **CompanyContext** | 채용 기업/포지션의 "현재 챕터 및 다음 챕터" 정의 | 기업 내부 정보 / JD / 사이트·기사 크롤링 / NICE |
| 2 | **CandidateContext** | 후보가 "살아온 챕터" 정의 (Experience별 PastCompanyContext 포함) | 자사 이력서 / LinkedIn 이력서 |
| 3 | **MappingFeatures + EvidenceBundle** | Company ↔ Candidate 챕터 정렬 결과 (피처 벡터 + 근거) | CompanyContext + CandidateContext |
| 4 | **CompanyTalentSignal** *(v1.1 이후 옵션)* | 후보 분포로부터 관측된 신호. CompanyContext 본체와 분리, feature로만 사용 | 후보 집합 통계 (표본/기간/모집단/신뢰도 포함) |

### 시스템 경계 선언

> **GraphRAG 파트의 책임**: CompanyContext / CandidateContext / MappingFeatures를 생산하고 근거(Evidence)를 공급한다.  
> **최종 랭킹 / 필터링**: DS/MLE 시스템이 수행한다.  
> GraphRAG는 "정렬 가능한 맥락 피처 + 근거"를 공급하는 것까지가 범위다.

---

## 2. 설계 원칙

### 2.1 독립성 (Separation)

- `CompanyContext`는 **후보와 무관하게**, 회사/포지션 소스만으로 생성한다.
- `CandidateContext`는 **회사와 무관하게**, 후보 소스만으로 생성한다.
- v1에서 `CompanyContext`에 후보 집합 통계를 **정체성(Identity)** 으로 내장하지 않는다. → 필요 시 `CompanyTalentSignal`로 별도 산출.

**역방향 제외 이유 명문화 (Anti-pattern 방어)**

역방향(`CompanyContext ← 후보 분포 통계`)을 v1에서 제외하는 이유:
- 채용 기업별 후보 pool이 다르고, 시장 노출/브랜드 편향이 개입된다.
- 모집단이 바뀌면 회사 맥락이 후보 데이터에 의해 오염된다.
- 해석가능성 저하 — "회사 문화"가 후보 집합 통계로 대체되는 문제가 발생한다.

### 2.2 포함 관계 (Containment)

- `CandidateContext`는 `Experience[]`를 가지며, 각 `Experience`는 `PastCompanyContext` 스냅샷을 포함할 수 있다.
- `PastCompanyContext`는 후보 단독 서술만으로 모호한 경험 해석을 보완하고, 외부 데이터(크롤링/NICE)로 역산하여 뒷받침할 수 있다.
- 역방향 포함은 v1에서 제외. 단, `CompanyTalentSignal`로 "관측 신호"는 허용.

### 2.3 근거 중심 (Evidence-first)

모든 맥락 주장(claim)은 반드시 evidence와 연결된다.

- 최소 단위: `source_id + span(문장 범위) + source_type + confidence + extracted_at`
- 근거 없는 맥락 생성은 허용하지 않는다.

### 2.4 버전/재현성 (Versioning)

모든 산출물에 아래 메타데이터를 필수로 포함한다.

| 필드 | 설명 |
|---|---|
| `context_version` | Context 스키마 버전 |
| `dataset_version` | 입력 데이터셋 버전 |
| `code_sha` | 생성 코드 커밋 해시 |
| `generated_at` | 생성 타임스탬프 (ISO 8601) |

### 2.5 Chapter 구성요소 (개념 레퍼런스)

**CompanyChapter 구성요소**

| 구성요소 | 설명 | 예시 |
|---|---|---|
| **Growth Trajectory / Inflection** | 현재 변곡점의 성격 | `Series A→B 도약`, `PMF 이후 Scale-up` |
| **Structural Tensions** | 내부 긴장/딜레마 (의사결정 갈등 구조) | 창업자→전문경영 전환, 기술부채 vs 신기능 |
| **Domain / Market Positioning** | 경쟁 맥락 | B2B SaaS→Enterprise, 버티컬 AI 산업 진입 |
| **Vacancy Chapter (팀 공백의 성격)** | 포지션이 열린 이유 | `0→1` / `1→10` / `reset` |
| **Operating Model / Culture** | 일하는 방식 (facet + narrative + evidence) | Culture Proxy Facets 8개 (섹션 3.1 참조) |
| **Role Expectations** | 이 챕터에서 필요한 역할/스코프/성과 기대 | — |

**CandidateChapter 구성요소**

| 구성요소 | 설명 | 예시 |
|---|---|---|
| **Experienced Trajectory / Verified Inflection** | 실제로 통과한 변곡점 | 스케일업 통과, 팀 10→100명 생존 |
| **Role Evolution Pattern** | 역할 변화 패턴 | `IC→Lead→Head`, `downshift` |
| **Domain Depth** | 도메인 경험 깊이 | 버티컬 반복 경험 vs 제너럴리스트 |
| **Failure & Recovery** | 역경 속 행동 패턴 | 피봇/리오그/망함에서 무엇을 했는가 |
| **Work Style / Culture Signals** | 일하는 방식 단서 | 커뮤니케이션 / 프로세스 선호 / 실험 vs 안정 |
| **PastCompanyContext** | 그 챕터가 발생한 회사 배경 스냅샷 | `stage` / `scale` / `domain` / `operating_mode` |

### 2.6 데이터 품질 원칙

#### 소스 신뢰도 계층

**기업 소스**

| 소스 | 신뢰도 | 활용 범위 |
|---|---|---|
| 회사 보유 기업 정보 | 높음 | 전 필드 활용 |
| 회사 사이트/기사 크롤링 | 중간 | 맥락/facet 근거, 광고성 필터 적용 |
| NICE 기업 정보 | 낮음~중간 | 팩트 축(업종/규모/업력) + domain prior 보정에만 사용 |

**후보 소스**

| 소스 | 신뢰도 | 활용 범위 |
|---|---|---|
| 자사 이력서 | 높음 | 전 필드 활용 |
| LinkedIn 이력서 | 중간 | 자사 이력서 교차 검증 보완, confidence 상향 |

모든 claim은 Evidence에 `source_type + confidence`를 표기하며, 소스별 신뢰도를 MappingFeatures 단계에서 피처 weight에 반영한다.

#### 소스별 처리 원칙

**광고성 필터링**
크롤링 소스에서 "수평적/패밀리/열정" 같은 정성 표현은 facet claim에서 노이즈 처리. Structural Tensions와 Situation/Stage는 수치/사건/제약 표현이 있는 경우에만 claim으로 인정하고 evidence를 필수로 붙인다.

**NICE 활용 범위 제한**
업종/규모/업력 같은 팩트 필드와 Risk Tolerance facet의 domain prior 보정에만 사용. 문화/운영방식 해석 필드의 직접 근거로는 가중치를 최소화한다.

**PastCompanyContext 역산**
이력서 텍스트가 빈약해도 재직 회사명 + 기간이 있으면 크롤링/NICE로 당시 `stage / scale / domain`을 역산. 역산 출처는 evidence에 명시한다.

#### 부분 완성 원칙

> **Context는 완성이 아니라, 신뢰도가 표기된 부분 완성 상태로 생산한다.**

- 누락 필드는 에러가 아닌 `missing_fields`로 명시
- `signal_confidence`를 낮게 표기하여 MappingFeatures에서 해당 피처 weight 자동 하향
- LinkedIn + 자사 이력서 교차 검증 시 confidence 상향

```json
{
  "situational_signals": ["Series A→B"],
  "signal_confidence": 0.4,
  "missing_fields": ["failure_recovery", "role_evolution_detail"],
  "evidence": [
    { "span": "...", "source_id": "resume_001", "source_type": "self_resume", "confidence": 0.85 },
    { "span": "...", "source_id": "linkedin_001", "source_type": "linkedin", "confidence": 0.65 }
  ]
}
```

#### 추가 정보 수집 루프

`missing_fields` 기반으로 타겟 질문을 생성하여 Context를 보강하는 루프를 파이프라인에 포함한다.

```
자사 이력서 + LinkedIn
→ 부분 CandidateContext 생성
→ missing_fields 식별
→ 타겟 질문 생성 ("이 시기 팀 규모 변화가 있었나요?")
→ 응답으로 Context 보강 → confidence 재산정
```

---

## 3. CompanyContext v1

**핵심 질문: "이 회사/포지션은 지금 어떤 상황에 있고, 무엇을 원하며, 어떤 방식으로 일하는가?"**

### 3.1 Operating Model: Culture Proxy Facets 8

선언/홍보 문구를 믿지 않고, **행동/운영 proxy 신호를 관측 규칙으로 계산**한다.  
각 facet은 `score + evidence span + source_type`을 함께 저장한다.

**Facet 1 — Execution Speed (속도/배송 지향)**
```
관측: "빠르게/신속/ship/deliver/sprint/주간릴리즈" 패턴 카운트
      + 채용공고 업데이트 빈도 시계열 신호

speed_proxy = f(keyword_count, cadence_mentions, update_frequency)
evidence: cadence 문장, "ship/launch" 문장
```

**Facet 2 — Autonomy & Ownership (자율/오너십)**
```
관측: "오너십/주도/ownership/lead" + "end-to-end/0→1" 동시 등장
      + "You will own/결정" + 산출물(OKR/roadmap) 언급

autonomy_proxy = f(ownership_phrases, end_to_end_mentions, decision_words)
evidence: "own end-to-end" 문장
```

**Facet 3 — Process Discipline (프로세스/문서화/체계)**
```
관측: "OKR/KPI", "RFC/ADR", "PRD", "SOP", "runbook"
      + "CI/CD", "code review", "test coverage", "표준화/정책"

process_proxy = f(artifact_mentions, governance_mentions)
evidence: RFC/ADR/OKR/Runbook 문장
```

**Facet 4 — Quality & Reliability Bias (품질/안정성 편향)**
```
관측: "SLA/SLO/SLI", "on-call", "postmortem", "observability"
      + "unit/e2e testing" + 기술 블로그 장애 회고 콘텐츠 존재 여부

reliability_proxy = f(slo_mentions, oncall_mentions, testing_mentions, postmortem_presence)
evidence: SLO/온콜/포스트모템 문장
```

**Facet 5 — Experimentation & Learning (실험/학습 지향)**
```
관측: "A/B test", "experiment", "hypothesis", "data-driven"
      + 지표(CTR/CVR/retention) 언급
      + 기사/블로그에서 "we learned that…" 형태 서술

experimentation_proxy = f(experiment_terms, metric_terms, learning_phrases)
evidence: A/B + metric 같이 나온 문장
```

**Facet 6 — Collaboration Structure (협업 방식/조직 운영)**
```
관측: "squad/tribe", "cross-functional", "PM/Design/Data 협업"
      + "async", "written communication", "documentation-first"
      + 채용공고에서 협업 상대 구체성

collaboration_proxy = f(structure_terms, async_terms, collaboration_specificity)
evidence: "cross-functional squad" 문장
```

**Facet 7 — Risk Tolerance & Innovation Posture (리스크 허용/혁신)**
```
관측: 혁신 키워드("0→1/greenfield/build from scratch")
      vs 보수 키워드("compliance/stability first/mission critical")
      + NICE 업종/규제 강도로 domain prior 보정
      (금융/의료 등 규제 산업 → risk_tolerance prior 낮게)

risk_tolerance_proxy = f(innovation_terms - compliance_terms, domain_prior)
evidence: "greenfield/0→1" 또는 "compliance-heavy" 문장
```

**Facet 8 — Transparency & Feedback Culture (투명성/피드백)**
```
관측: "retrospective", "feedback", "1:1", "blameless"
      + 실패/이슈를 공개적으로 다룬 블로그/기사 존재 여부
      + 채용 페이지에서 추상 미사여구 vs 숫자/팩트 공개 정도

transparency_proxy = f(retro_terms, blameless_terms, public_failure_discussion, metric_disclosure)
evidence: 회고/피드백/블레임리스 문장
```

### 3.2 필수 구성요소 요약

| 구성요소 | 설명 |
|---|---|
| Situation / Stage | 변곡점 성격 + "왜 이 시점인가" 맥락 |
| Objectives & Constraints | 달성 목표 + 제약 조건 |
| Operating Model | Culture Proxy Facets 8 (score + evidence) + narrative_summary |
| Structural Tensions | 딜레마/갈등 구조 (type + description + confidence, evidence 필수) |
| Role Expectations | scope_type(0→1 / 1→10 / reset) + 기대 수준 |

### 3.3 출력 스키마

```json
{
  "company_id": "...",
  "job_id": "...",
  "context_version": "1.0",
  "dataset_version": "...",
  "code_sha": "...",
  "generated_at": "2026-02-01T00:00:00Z",
  "situation": {
    "stage": "Series A → B",
    "narrative": "..."
  },
  "objectives": ["ARR 3x", "엔터프라이즈 영업 체계 구축"],
  "constraints": ["런웨이 18개월", "레거시 모놀리스"],
  "operating_model": {
    "facets": {
      "execution_speed":     { "score": 4, "evidence_span": "...", "source_type": "jd" },
      "autonomy":            { "score": 5, "evidence_span": "...", "source_type": "site_crawl" },
      "process_discipline":  { "score": 2, "evidence_span": "...", "source_type": "jd" },
      "quality_reliability": { "score": 3, "evidence_span": "...", "source_type": "tech_blog" },
      "experimentation":     { "score": 4, "evidence_span": "...", "source_type": "article" },
      "collaboration":       { "score": 3, "evidence_span": "...", "source_type": "jd" },
      "risk_tolerance":      { "score": 4, "evidence_span": "...", "source_type": "site_crawl", "domain_prior_applied": true },
      "transparency":        { "score": 3, "evidence_span": "...", "source_type": "tech_blog" }
    },
    "narrative_summary": "..."
  },
  "structural_tensions": [
    { "type": "tech_debt_vs_new_features", "description": "...", "confidence": 0.85,
      "evidence": { "span": "...", "source_id": "...", "source_type": "article" } }
  ],
  "role_expectations": {
    "scope_type": "1→10",
    "description": "..."
  },
  "missing_fields": [],
  "evidence": [
    { "span": "...", "source_id": "jd_001", "source_type": "jd", "confidence": 0.9, "extracted_at": "..." }
  ]
}
```

---

## 4. CandidateContext v1

**핵심 질문: "이 사람은 어떤 상황 경험을 했고, 어떤 방식으로 일하며, 어떤 근거로 그렇게 말할 수 있는가?"**

### 4.1 필수 구성요소

| 구성요소 | 설명 |
|---|---|
| **Experience Timeline** | 회사 / 직무 / 기간 / 스코프 / 성과 요약 |
| **Situational Signals** | 실제로 노출된 상황 유형 신호 |
| **Failure & Recovery Signals** | 역경 속 행동 패턴 레이블 배열 |
| **Role Evolution Pattern** | `IC→Lead→Head` 등 역할 변화 패턴 (최상위 독립 필드) |
| **Domain Depth** | 버티컬 반복 경험 깊이 |
| **Work Style / Culture Signals** | 일하는 방식 단서 |
| **PastCompanyContext** | 각 Experience의 회사 배경 스냅샷 (역산 가능) |

### 4.2 출력 스키마

```json
{
  "candidate_id": "...",
  "resume_id": "...",
  "context_version": "1.0",
  "dataset_version": "...",
  "code_sha": "...",
  "generated_at": "2026-02-01T00:00:00Z",
  "role_evolution_pattern": "IC→Lead→Head",
  "domain_depth": "B2B SaaS 반복 경험 (3개 회사)",
  "experiences": [
    {
      "company": "...",
      "role": "Engineering Lead",
      "period": "2021-03 ~ 2023-06",
      "scope_summary": "...",
      "outcomes": ["MAU 10x", "팀 4→18명"],
      "situational_signals": ["Series A→B", "팀 스케일링"],
      "signal_confidence": 0.85,
      "failure_recovery_signals": ["pivot_survival", "post_layoff_rebuild"],
      "past_company_context": {
        "stage": "Series A → B",
        "scale": "50~150명",
        "domain": "B2B SaaS",
        "operating_mode": "자율 / 실험 중심",
        "inferred_from": "crawl+nice"
      }
    }
  ],
  "work_style_signals": {
    "autonomy_preference": "high",
    "process_tolerance": "low",
    "experiment_orientation": "high",
    "quality_bias": "medium"
  },
  "missing_fields": ["failure_recovery"],
  "evidence": [
    { "span": "...", "source_id": "resume_001", "source_type": "self_resume", "confidence": 0.85, "extracted_at": "..." },
    { "span": "...", "source_id": "linkedin_001", "source_type": "linkedin", "confidence": 0.65, "extracted_at": "..." }
  ]
}
```

---

## 5. MappingFeatures v1

**목적**: 후보 필터링/랭킹은 DS/MLE 시스템이 수행한다. 우리는 그 시스템이 사용할 수 있는 **"맥락 정렬 피처 + 근거 번들(Context Pack)"** 을 제공한다.

- 입력: `job_id + candidate_id`
- 출력: `features (chapter-aware 피처 벡터) + evidence_bundle`

### 5.1 Feature Vector (Chapter-aware 피처)

| 피처 | 설명 |
|---|---|
| `stage_transition_match` | 기업 스테이지 전환 ↔ 후보 경험 전환 정렬 |
| `tension_alignment` | 기업 긴장/딜레마 ↔ 후보 경험 패턴 정렬 |
| `vacancy_fit` | `0→1` / `1→10` / `reset` 분류 일치 |
| `domain_positioning_fit` | 도메인/시장 포지션 적합도 |
| `role_evolution_fit` | 역할 성장 패턴 적합도 |
| `resilience_fit` | 실패/회복 경험 적합도 |
| `culture_fit` | facet 8개 + narrative 기반 정렬 |

### 5.2 출력 스키마

```json
{
  "job_id": "...",
  "candidate_id": "...",
  "mapping_version": "1.0",
  "context_version": "1.0",
  "dataset_version": "...",
  "code_sha": "...",
  "generated_at": "...",
  "features": {
    "stage_transition_match": 0.92,
    "tension_alignment": 0.78,
    "vacancy_fit": "1→10",
    "domain_positioning_fit": 0.85,
    "role_evolution_fit": 0.80,
    "resilience_fit": 0.70,
    "culture_fit": 0.88
  },
  "evidence_bundle": {
    "company": [
      { "span": "...", "source_id": "jd_001", "source_type": "jd", "confidence": 0.9 }
    ],
    "candidate": [
      { "span": "...", "source_id": "resume_001", "source_type": "self_resume", "confidence": 0.85 }
    ],
    "graph_paths": [
      { "path_summary": "Candidate played Role X during Chapter Y and led to Outcome Z", "confidence": 0.8 }
    ],
    "report_snippets": [
      { "span": "...", "source_id": "graphrag_report:...", "confidence": 0.8 }
    ]
  }
}
```

---

## 6. CompanyTalentSignal (v1.1 이후, 옵션)

"진취적인 후보가 많이 모인다" 같은 후보 분포 기반 관측 신호는 편향이 크다.

- `CompanyContext` 본체에 섞지 않고 **별도 산출물**로 분리
- 소비 시 **feature로만 사용** (가중치 조절 가능)
- 필수 메타데이터: `time_window / population_definition / sample_size / confidence`

```json
{
  "company_id": "...",
  "signal_type": "culture_progressiveness",
  "value": 0.74,
  "sample_size": 42,
  "time_window": "최근 180일",
  "population_definition": "채용 완료 후보 중 재직 6개월 이상",
  "confidence": 0.65,
  "generated_at": "..."
}
```

---

## 7. GraphRAG 연결 전략

### 7.1 그래프 모델 최소 단위

단순 스킬 그래프가 아니라 **Situation–Role–Outcome (+Evidence)** 트리플 중심으로 구성한다.

| 트리플 요소 | 설명 |
|---|---|
| **Situation (Chapter)** | 어떤 변곡점/긴장/공백 상황인가 |
| **Role** | 그 상황에서 후보(또는 팀)가 어떤 스코프로 행동했는가 |
| **Outcome** | 결과 — 성공/실패/지표/학습/조직 변화 |
| **Evidence** | 뒷받침하는 문장/문서/출처/그래프 경로 |

GraphRAG Indexing은 이 트리플을 만들기 위해 엔티티(`Company`, `Candidate`, `Chapter`, `Role`, `Outcome`, `Evidence`)를 추출/정리하고, community report를 생성해 Context Profile을 산출한다.

### 7.2 Context별 연결 방식

| Context | 입력 소스 | GraphRAG 역할 | 출력 |
|---|---|---|---|
| `CompanyContext` | 기업 내부 정보 + JD + 크롤링 + NICE | 문서 묶음 indexing → community report | facets / narrative / tensions / evidence |
| `CandidateContext` | 자사 이력서 + LinkedIn | 경력 텍스트 indexing → signal/role/outcome 추출 | signals / role_evolution / evidence |
| `PastCompanyContext` | 크롤링 + NICE | 스냅샷 역산 | stage / scale / domain |
| `MappingFeatures` | job_id + candidate_id | GraphRAG retrieval + path/report 활용 | features + evidence_bundle |

---

## 8. 확장 모듈 (v2 이후)

v1에서는 필수가 아니지만, 모듈 방식으로 확장 가능한 하위 Context 개념들.

| 모듈 | 설명 |
|---|---|
| `StageTransitionContext` | A→B, PMF→Scale 등 전환 패턴의 세분화 |
| `CultureContext` | Culture Proxy Facets 확장 + narrative + evidence 특화 모듈 |
| `RoleScopeContext` | 플랫폼/성장/데이터 등 역할 도메인 특화 |
| `ImpactContext` | 성과/스케일/지표 근거 중심 모듈 |
| `RiskConstraintContext` | 규제/레거시/품질 요구 등 제약 조건 특화 |

---

## 9. 다음 단계 (Next Steps)

이 문서를 고정(freeze)하고, 이어서 논의할 항목:

1. **GraphRAG indexing/retrieval 파이프라인** — community / report 등 어떤 아티팩트를 만들지
2. **저장소 및 서빙 설계** — CompanyContext / CandidateContext / MappingFeatures를 어떤 저장소로 서빙할지
3. **v1 MVP 일정** — 기본 구축 범위와 v2 이후 모듈 확장을 어떻게 쪼갤지
