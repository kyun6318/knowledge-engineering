# 구직자 검색 시스템 — Context 정의 v1 고정 문서 (Final)

> 기업 맥락 기반 인재 추천 시스템 설계를 위한 맥락(Context)의 **개념 정의 / 산출물 분류 / 시스템 경계 / 스키마 / 운영 규칙 / 데이터 품질 원칙 / 문화 proxy 규칙 / GraphRAG 표현 원칙** 통합 문서.  
> 이 문서는 **GraphRAG 설계 및 일정 논의 진입 전 고정(freeze)** 하는 기준 문서다.  
> (last updated: 2026-02)

---

## 0. 핵심 정의

**맥락(Context)은 '현재 상태(state)'가 아니라 '어디서 와서 어디로 가는가'를 나타내는 궤적(trajectory) + 상황(situation)의 복합이다.**

실무 표현으로는 **"챕터(chapter)"**이며, 각 챕터는 **변곡점 / 긴장 / 의도된 방향**을 포함한다.

### 매칭의 핵심 원리

맥락 매칭은 키워드 매칭이 아니라,
**"기업이 앞으로 겪을 챕터(미래 벡터)를 후보가 이미 겪었는가(과거 벡터)"** 를 평가하는 것이다.

### 기업 CompanyContext의 미래 벡터  ←→  CandidateContext의 과거 경험 벡터

예: "Series A→B 도약을 준비 중인 기업" ↔ "이전 회사에서 Series A→B 전환을 통과한 후보"

---

## 1. 산출물(Artifacts) 4종

시스템이 생산하는 산출물은 아래 4종으로 분류한다.

| # | 산출물 | 정의 | 생성 소스 |
|---|---|---|---|
| 1 | **CompanyContext** | 채용 기업/포지션의 "현재 챕터 및 다음 챕터" 정의 | JD / 회사 문서 / 채용 히스토리 / 내부 기업 정보 |
| 2 | **CandidateContext** | 후보가 "살아온 챕터" 정의 (Experience별 PastCompanyContext 포함) | 자사 이력서 / LinkedIn 이력서 / 프로젝트·성과 |
| 3 | **MappingFeatures + EvidenceBundle** | Company ↔ Candidate 챕터 정렬 결과 (피처 벡터 + 근거) | CompanyContext + CandidateContext (+ GraphRAG retrieval) |
| 4 | **CompanyTalentSignal** *(옵션, v1.1+)* | 후보 분포로부터 관측된 신호. CompanyContext 본체와 분리, feature로만 사용 | 후보 집합 통계(표본/기간/모집단/신뢰도 포함) |

### 시스템 경계 선언

> **GraphRAG/Context Layer의 책임**: `CompanyContext` / `CandidateContext` / `MappingFeatures`를 생산하고 근거(Evidence)를 공급한다.  
> **최종 랭킹 / 필터링**: DS/MLE의 검색 시스템이 수행한다.  
> GraphRAG는 **"정렬 가능한 맥락 피처 + 근거"**를 공급하는 것까지가 범위다.

---

## 2. 설계 원칙

### 2.1 독립성 (Separation)

- `CompanyContext`는 **후보와 무관하게**, 회사/포지션 소스만으로 생성한다.
- `CandidateContext`는 **회사와 무관하게**, 후보 소스만으로 생성한다.
- v1에서 `CompanyContext`에 후보 집합 통계를 "정체성"으로 내장하지 않는다. → 필요 시 `CompanyTalentSignal`로 별도 산출.

**역방향 제외 이유 명문화 (Anti-pattern 방어)**  
역방향(`CompanyContext ← 후보 분포 통계`)을 v1에서 제외하는 이유:
- 채용 기업별 후보 pool이 다르고, 시장 노출/브랜드 편향이 개입된다.
- 모집단이 바뀌면 회사 맥락이 후보 데이터에 의해 오염된다.
- 해석가능성 저하 — "회사 문화"가 후보 집합 통계로 대체되는 문제가 발생한다.

### 2.2 포함 관계 (Containment)

- `CandidateContext`는 `Experience[]`를 가지며, 각 `Experience`는 `PastCompanyContext` 스냅샷을 포함할 수 있다.
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

---

## 3. Context의 최소 단위: Chapter(챕터)

CompanyContext와 CandidateContext 모두 **Chapter 단위**로 구조화한다.

### 3.1 CompanyChapter 구성요소 — “기업이 지금 어떤 챕터를 살고 있는가”

| 구성요소 | 설명 | 예시 |
|---|---|---|
| **Growth Trajectory / Inflection** | 현재 변곡점의 성격 | `Series A→B 도약`, `PMF 이후 Scale-up`, `글로벌 확장 준비` |
| **Structural Tensions** | 내부 긴장/딜레마 | 창업자→전문경영 전환, 기술부채 vs 신기능 개발 |
| **Domain / Market Positioning** | 경쟁 맥락 | B2B SaaS→Enterprise, 버티컬 AI 특정 산업 진입 |
| **Vacancy Chapter (팀 공백의 성격)** | 포지션이 열린 이유 | `0→1` (없어서 못함), `1→10` (있는데 느림), `reset` (잘못 가고 있음) |
| **Operating Model / Culture** | 일하는 방식 | facet(정형) + narrative(서술) + evidence(근거) |
| **Role Expectations** | 이 챕터에서 필요한 역할/스코프/성과 기대 | — |

### 3.2 CandidateChapter 구성요소 — “후보가 어떤 챕터를 살아왔는가”

| 구성요소 | 설명 | 예시 |
|---|---|---|
| **Experienced Trajectory / Verified Inflection** | 실제로 통과한 변곡점 | 스케일업 통과, 팀 10→100명 생존 |
| **Role Evolution Pattern** | 역할 변화 패턴 | IC→Lead→Head, 또는 downshift |
| **Domain Depth** | 도메인 경험 깊이 | 버티컬 반복 경험 vs 제너럴리스트 |
| **Failure & Recovery** | 역경 속 행동 패턴 | 회사 망함/리오그/피봇에서 무엇을 했는가 |
| **Work Style / Culture Signals** | 일하는 방식 단서 | 커뮤니케이션 / 프로세스 선호 / 실험 vs 안정 |
| **PastCompanyContext** | 그 챕터가 발생한 회사 배경 스냅샷 | stage / scale / domain / operating_mode |

---

## 4. GraphRAG 표현 원칙

단순 스킬 그래프가 아니라 **Situation–Role–Outcome (+Evidence)** 트리플 중심으로 구성한다.

| 트리플 요소 | 설명 |
|---|---|
| **Situation (Chapter)** | 어떤 변곡점/긴장/공백 상황인가 |
| **Role** | 그 상황에서 후보(또는 팀)가 어떤 스코프로 행동했는가 |
| **Outcome** | 결과 — 성공/실패/지표/학습/조직 변화 |
| **Evidence** | 뒷받침하는 문장/문서/출처/그래프 경로 |

GraphRAG Indexing은 이 트리플을 만들기 위해 엔티티(`Company`, `Candidate`, `Chapter`, `Role`, `Outcome`, `Evidence`)를 추출/정리하고, community report를 생성해 Context Profile을 산출한다.

### GraphRAG 연결 전략(개요)

| Context | 입력 소스 | GraphRAG 역할 | 출력 |
|---|---|---|---|
| `CompanyContext` | JD, 회사 문서, 채용 히스토리, 내부 기업 정보 | 문서 묶음 indexing → community report | facets / narrative / tensions / evidence |
| `CandidateContext` | 자사/LinkedIn 이력서, 경력 기술서 | 경력 텍스트 indexing → signal/role/outcome 추출 | signals / role_evolution / evidence |
| `PastCompanyContext` | 내부 기업 정보 + 크롤링 + NICE | 시점 스냅샷 생성 | stage / scale / domain / operating_mode |
| `MappingFeatures` | job_id + candidate_id | GraphRAG retrieval + path/report 활용 | features + evidence_bundle |

---

## 5. MappingFeatures v1: "미래 챕터 ↔ 과거 챕터" 정렬

Mapping은 아래 두 가지를 출력한다.

### 5.1 Feature Vector (Chapter-aware 피처)

| 피처 | 설명 |
|---|---|
| `stage_transition_match` | 기업의 스테이지 전환과 후보의 경험 전환 정렬 |
| `tension_alignment` | 기업의 긴장/딜레마와 후보의 경험 패턴 정렬 |
| `vacancy_fit` | 0→1 / 1→10 / reset 분류 일치 여부 |
| `domain_positioning_fit` | 도메인/시장 포지션 적합도 |
| `role_evolution_fit` | 역할 성장 패턴 적합도 |
| `resilience_fit` | 실패/회복 경험 적합도 |
| `culture_fit` | Operating Model / Work Style 정렬 |

### 5.2 EvidenceBundle

각 피처에 대응하는 근거 묶음.

- 회사 근거 (JD/문서 span + source_id + source_type + confidence)
- 후보 근거 (이력서 span + source_id + source_type + confidence)
- 그래프 경로 / community report 요약 (있으면)

---

## 6. CompanyTalentSignal (옵션, v1.1+): 후보 분포 기반 관측 신호

"진취적인 후보가 많은 회사는 진취적이다" 같은 가설은 관측 신호로 유용하지만 편향이 크다.

- `CompanyContext` 본체에 섞지 않고 **별도 산출물**로 분리한다.
- 필수 포함 메타데이터: 표본 크기 / 기간(rolling window 권장) / 모집단 정의 / 신뢰도
- 소비 시에도 **feature로만 사용** (가중치 조절 가능)

예시:
```json
{
  "company_id": "...",
  "signal_type": "culture_progressiveness",
  "value": 0.74,
  "sample_size": 42,
  "time_window_days": 180,
  "population_definition": "채용 완료 후보 중 재직 6개월 이상",
  "confidence": 0.65,
  "generated_at": "..."
}


⸻

## 7. 스키마 참조 (JSON)

### 7.1 CompanyContext (예시)

```json
{
  "company_id": "...",
  "job_id": "...",
  "context_version": "1.0",
  "dataset_version": "...",
  "code_sha": "...",
  "generated_at": "2026-02-01T00:00:00Z",
  "chapter": {
    "stage": "Series A → B",
    "trajectory_narrative": "...",
    "structural_tensions": [
      { "type": "tech_debt_vs_new_features", "description": "...", "confidence": 0.85 }
    ],
    "domain_positioning": "B2B SaaS → Enterprise"
  },
  "vacancy": {
    "scope_type": "1→10",
    "description": "..."
  },
  "objectives": ["ARR 3x", "엔터프라이즈 영업 체계 구축"],
  "constraints": ["런웨이 18개월", "레거시 모놀리스"],
  "operating_model": {
    "facets": { "speed": 4, "autonomy": 5, "process": 2, "collaboration": 4, "quality": 3, "risk_tolerance": 4 },
    "narrative_summary": "..."
  },
  "role_expectations": { "scope": "...", "success_criteria": "..." },
  "evidence": [
    { "source_id": "jd_001", "source_type": "crawl_jd", "span": "...", "confidence": 0.9, "extracted_at": "..." }
  ]
}
```

### 7.2 CandidateContext (예시)

```json
{
  "candidate_id": "...",
  "resume_id": "...",
  "context_version": "1.0",
  "dataset_version": "...",
  "code_sha": "...",
  "generated_at": "2026-02-01T00:00:00Z",
  "experiences": [
    {
      "company": "...",
      "role": "Engineering Lead",
      "period": "2021-03 ~ 2023-06",
      "scope_summary": "...",
      "outcomes": ["MAU 10x", "팀 4→18명"],
      "situational_signals": ["Series A→B 전환", "팀 스케일링", "레거시 개선"],
      "failure_recovery": "시리즈 A 실패 후 피봇, 핵심 기능 재설계 주도",
      "past_company_context": {
        "stage": "Series A → B",
        "scale": "50~150명",
        "domain": "B2B SaaS",
        "operating_mode": "자율/실험 중심"
      }
    }
  ],
  "role_evolution": "IC → Lead → Head",
  "domain_depth": "B2B SaaS 반복 경험 (3개 회사)",
  "work_style_signals": {
    "autonomy_preference": "high",
    "process_tolerance": "low",
    "experiment_orientation": "high",
    "quality_bias": "medium"
  },
  "missing_fields": ["role_evolution_detail", "failure_recovery_detail"],
  "evidence": [
    { "source_id": "resume_001", "source_type": "self_resume", "span": "...", "confidence": 0.85, "extracted_at": "..." }
  ]
}
```

### 7.3 MappingFeatures (예시)

```json
{
  "company_id": "...",
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
    "company_evidence": [{ "source_id": "...", "source_type": "crawl_site", "span": "...", "confidence": 0.9 }],
    "candidate_evidence": [{ "source_id": "...", "source_type": "linkedin", "span": "...", "confidence": 0.65 }],
    "graph_paths": [{ "path_summary": "...", "confidence": 0.8 }],
    "report_snippets": [{ "source_id": "graphrag_report:...", "span": "...", "confidence": 0.8 }]
  }
}
```

## 8. 데이터 품질·신뢰도 원칙 (Data Quality Principles)

목표: 데이터가 빈약/왜곡되어도 거짓을 그럴듯하게 채우지 않고, 근거·신뢰도·누락을 명시하며, downstream(랭킹 시스템)이 안전하게 감쇠/무시할 수 있도록 한다.

### 8.1 소스 신뢰도 계층(Tier) + source_type 강제

기업 소스

| 소스 | 신뢰도 | 특징 |
| --- | --- | --- |
| 회사 보유 기업 정보 | 높음 | 실제 채용 맥락 기반, 편집 편향 낮음 |
| 회사 사이트/기사 크롤링 | 중간 | 맥락은 있으나 광고성 표현 개입 |
| NICE 기업 정보 | 낮음~중간 | 팩트 신뢰(규모/업력) 가능, 최신성 낮음 |

후보 소스

| 소스 | 신뢰도 | 특징 |
| --- | --- | --- |
| 회사 자체 이력서 | 높음 | 실제 지원 맥락, 가장 직접 데이터 |
| LinkedIn 이력서 | 중간 | 보완 소스, 공개 범위 따라 밀도 편차 |

규칙:
	•	모든 claim은 evidence에 source_type + confidence를 표기한다.
	•	소스별 prior는 MappingFeatures 단계에서 feature weight로 반영한다.

### 8.2 소스별 처리 원칙

(1) 광고성 필터링(크롤링 소스)
	•	“수평적/패밀리/열정” 같은 정성 구호는 Operating Model claim에서 노이즈로 처리한다.
	•	Structural Tensions와 Situation/Stage는 수치/사건/제약 표현이 있는 경우에만 claim 인정하며 evidence를 필수로 붙인다.

(2) NICE 활용 범위 제한
	•	NICE는 업력/업종/규모(인원/매출 범위) 같은 팩트성 필드에만 사용한다.
	•	문화/운영방식 같은 해석성 필드에는 사용하지 않는다.
	•	단, 규제 산업 등 domain prior 보정에는 제한적으로 활용 가능.

(3) PastCompanyContext 역산(표준 기능)
	•	이력서 텍스트가 빈약해도, 재직 회사명 + 재직 기간이 있으면 회사 소스(내부/크롤링/NICE)로 해당 시점의 PastCompanyContext를 역산한다.
	•	역산 출처는 evidence에 명시하고 confidence는 소스 tier로 보정한다.

### 8.3 부분 완성(Partial Completion)을 정상 상태로 정의
	•	Context는 완성이 아니라, 신뢰도가 표기된 부분 완성 상태로 생산한다.
	•	누락 필드는 에러가 아니라 missing_fields로 명시한다.
	•	각 신호/피처에 signal_confidence(또는 field-level confidence)를 두고,
	•	confidence가 낮으면 MappingFeatures에서 해당 feature weight가 자동 하향되도록 설계한다.
	•	자체 이력서 + LinkedIn이 모두 있으면 교차 검증으로 confidence 상향(불일치 시 하향/contradiction 표기).

예시:

```json
{
  "situational_signals": ["Series A→B"],
  "signal_confidence": 0.4,
  "missing_fields": ["failure_recovery", "role_evolution_detail"],
  "evidence": [
    { "span": "...", "source_id": "resume_001", "source_type": "self_resume", "confidence": 0.85, "extracted_at": "..." },
    { "span": "...", "source_id": "linkedin_001", "source_type": "linkedin", "confidence": 0.65, "extracted_at": "..." }
  ]
}
```

### 8.4 coverage/freshness/source_diversity 동시 관리
	•	confidence만으로는 부족하므로 claim/field 단위로 최소:
	•	coverage(근거 개수/다양성),
	•	freshness(근거 최신성),
	•	source_diversity(서로 다른 source_type 수)
를 함께 관리하고 MappingFeatures에서 보정한다.

### 8.5 추가 정보 수집 루프(Closed-loop Enrichment)

이력서만으로 Context가 부족할 경우 missing_fields 기반으로 타겟 질문을 생성해 후보/담당자에게 요청하는 루프를 포함한다.
	•	자체 이력서 + LinkedIn → 부분 CandidateContext 생성
	•	→ missing_fields 식별
	•	→ 타겟 질문 생성(예: “이 시기 팀 규모 변화가 있었나요?”)
	•	→ 응답 반영 → confidence 재산정/업데이트

⸻

## 9. 문화 Proxy Facets 8개 (관측 가능한 규칙 전용)

목표: “우린 수평적” 같은 선언이 아니라, 운영/행동 프록시로 문화 신호를 만든다.
각 facet은 score + evidence(span/source_id/source_type) + confidence/coverage를 함께 저장한다.

### 9.1 Execution Speed (속도/배송 지향)
	•	“빠르게/신속/ship/launch/rapid/fast-paced” + 릴리즈 cadence(스프린트/주간/월간) 언급 카운트
	•	공고/기사/블로그 업데이트 빈도(가능 시)
	•	speed_proxy = f(keyword_count, cadence_mentions, update_frequency)

### 9.2 Autonomy & Ownership (자율/오너십)
	•	“오너십/주도/ownership/lead/end-to-end/0→1” 동시 등장
	•	책임 범위 문장(own/lead/결정) + 산출물(OKR/metric/roadmap) 언급
	•	autonomy_proxy = f(ownership_phrases, end_to_end_mentions, decision_words)

### 9.3 Process Discipline (프로세스/문서화/체계)
	•	OKR/KPI, RFC/ADR, PRD, roadmap, SOP, runbook, code review, CI/CD, test coverage, release process 언급
	•	process_proxy = f(artifact_mentions, governance_mentions)

### 9.4 Quality & Reliability Bias (품질/안정성 편향)
	•	SLA/SLO/SLI, on-call, incident/postmortem, reliability, availability, latency
	•	observability/monitoring/alerting, testing 언급
	•	reliability_proxy = f(slo_mentions, oncall_mentions, testing_mentions, postmortem_presence)

### 9.5 Experimentation & Learning (실험/학습 지향)
	•	A/B test, experiment, hypothesis, iteration, data-driven + metric(CTR/CVR/retention) 결합
	•	experimentation_proxy = f(experiment_terms, metric_terms, learning_phrases)

### 9.6 Collaboration Structure (협업 방식/조직 운영 형태)
	•	squad/tribe/cross-functional/matrix, PM·Design·Data 협업 명시
	•	async/written communication/documentation-first/meeting-lite 언급
	•	collaboration_proxy = f(structure_terms, async_terms, collaboration_specificity)

### 9.7 Risk Tolerance & Innovation Posture (리스크 허용/혁신 성향)
	•	0→1/greenfield/new business/build from scratch/pioneer vs compliance/risk management/mission critical
	•	규제 산업 prior(NICE/내부 업종 분류)로 보정
	•	risk_tolerance_proxy = f(innovation_terms - compliance_terms, domain_prior)

### 9.8 Transparency & Feedback Culture (투명성/피드백/회고)
	•	retrospective/feedback/1:1/open/blameless + 공개적인 실패/학습 서술 여부
	•	지표/팩트 공개 정도(추상 구호 vs 수치/사례)
	•	transparency_proxy = f(retro_terms, blameless_terms, public_failure_discussion, metric_disclosure)

⸻

## 10. 확장 모듈 (v2 이후)

v1에서는 필수가 아니지만, 모듈 방식으로 확장 가능한 하위 Context 개념들.

| 모듈 | 설명 |
| --- | --- |
| StageTransitionContext | A→B, PMF→Scale 등 전환 패턴의 세분화 |
| CultureContext | facet + narrative + evidence의 문화 특화 모듈 |
| RoleScopeContext | 플랫폼/성장/데이터 등 역할 도메인 특화 |
| ImpactContext | 성과/스케일/지표 근거 중심 모듈 |
| RiskConstraintContext | 규제/레거시/품질 요구 등 제약 조건 특화 |


## 11. 다음 단계 (Next Steps)

이 문서를 고정(freeze)하고, 이어서 논의할 항목:
1. **GraphRAG indexing/retrieval 파이프라인** — community/report 등 어떤 아티팩트를 만들지
2. **저장소 및 서빙 설계** — CompanyContext/CandidateContext/MappingFeatures를 어디에 저장/서빙할지
3. **v1 MVP 일정** — 기본 구축 범위와 v2 모듈 확장을 어떻게 쪼갤지