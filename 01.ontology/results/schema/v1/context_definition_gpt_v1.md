# 구직자 검색 시스템 — 맥락(Context) 정의 v1 (Final)

> 본 문서는 기업 맥락 기반 인재 추천 시스템 설계를 위한 **맥락(Context)의 개념 정의, 구성 원칙, 스키마**를 통합 정리한 문서입니다.  
> 본 v1 정의는 **GraphRAG 기반 Context Layer** 구축(EPIC 5)의 기준 문서로 사용합니다.

---

## 0. 맥락이란 무엇인가

맥락은 단순한 "현재 상태(State)"가 아니라, **"어디서 와서 어디로 가는가"** — 즉 **궤적(Trajectory) + 상황(Situation)**의 복합 개념이다.

- 기업 맥락은 **"이 회사/포지션이 지금 어떤 챕터(Chapter)를 살고 있는가"**
- 구직자 맥락은 **"이 사람이 어떤 챕터(Chapter)를 살아왔는가"** 를 나타낸다.

### 매칭의 핵심 원리

> 기업이 **앞으로 겪을 챕터**를 구직자가 **이미 겪었는가**

기업 맥락의 미래 벡터  ←→  구직자 맥락의 과거 경험 벡터

예:  
"Series A→B 도약을 준비 중인 기업" ↔ "이전 회사에서 Series A→B 전환을 통과한 구직자"

---

## 1. 설계 원칙

### 1.1 독립성 (Separation)

- `CompanyContext`는 **후보와 무관하게**, 회사/포지션 소스(JD, 회사 문서, 채용 히스토리 등)에서만 생성한다.
- `CandidateContext`는 **회사와 무관하게**, 후보 소스(이력서, 경력 기술서, 프로젝트/성과)에서만 생성한다.
- v1에서 `CompanyContext`는 후보 집합 통계나 분포 데이터를 **정체성(Identity)** 으로 포함하지 않는다. (이유는 1.5 참조)

> 단, 후보 분포 기반의 관측 신호는 v1.1 이후 **별도 산출물(`CompanyTalentSignal`)** 로 확장 가능하다. (섹션 6 참조)

### 1.2 포함 관계 (Containment)

- `CandidateContext`는 `Experience[]`를 가지며, 각 `Experience`는 `PastCompanyContext` 스냅샷(스테이지/도메인/규모/운영방식 최소 요약)을 포함할 수 있다.
- `PastCompanyContext`는 후보 단독 서술만으로 모호한 경험 해석을 보완하고, 외부 데이터(펀딩 라운드, 규모 등)로 뒷받침할 수 있다.

### 1.3 근거 중심 (Evidence-first)

- 모든 맥락 주장(claim)은 **근거(evidence)** 와 반드시 연결된다.
- 근거의 최소 단위: `문장 span + source_id + 신뢰도(confidence)`
- **근거 없는 맥락 생성은 허용하지 않는다.**

### 1.4 버전/재현성 (Versioning)

- 모든 Context 산출물에 다음 메타데이터를 필수로 포함한다.

| 필드 | 설명 |
|---|---|
| `context_version` | Context 스키마 버전 |
| `dataset_version` | 입력 데이터셋 버전 |
| `code_sha` | 생성 코드 커밋 해시 |
| `generated_at` | 생성 타임스탬프 (ISO 8601) |

### 1.5 역방향 제외 이유 명시 (Anti-pattern: Company ← Candidate Stats)

v1에서 `CompanyContext`에 후보 분포/통계를 포함하지 않는 이유:

- 채용 기업별 후보 pool이 다르고, 시장 노출/브랜드 편향이 개입된다.
- 모집단이 바뀌면 회사 맥락이 후보 데이터에 의해 오염될 수 있다.
- 해석가능성 저하 — "회사 문화"가 후보 집합 통계로 대체되는 문제가 발생한다.

---

## 2. CompanyContext v1

**핵심 질문:**  
> "이 회사/포지션은 지금 어떤 상황에 있고, 무엇을 원하며, 어떤 방식으로 일하는가?"

### 2.1 필수 구성요소

#### (1) Situation / Stage
현재 회사가 처한 변곡점의 성격.

- 예: `Series A → B 도약`, `PMF 이후 Scale-up`, `효율화/수익화 단계`, `글로벌 진출 직전`
- 단순 스테이지 레이블이 아니라, **"왜 이 시점인가"** 의 맥락까지 포함

#### (2) Objectives & Constraints
회사가 이 시점에 달성하려는 목표와 그것을 제약하는 조건.

- 목표: 성장 가속, 신규 런칭, 기술 부채 해소, 시장 진입 등
- 제약: 인력 규모, 타임라인, 레거시 시스템, 규제 환경 등

#### (3) Operating Model (문화 / 일하는 방식)
- **facets**: 속도 / 자율 / 프로세스 / 협업 / 품질 / 리스크 허용도 등 5~8개 축의 정형 값
- **narrative_summary**: 비정형 서술 요약 (GraphRAG report 기반, 200~500자)

#### (4) Structural Tensions (조직 구조의 긴장)
회사가 해당 챕터에서 겪고 있는 핵심 딜레마/마찰 구조.

- 예: `tech_debt vs new_features`, `founder-led vs professional_mgmt`, `speed vs reliability`
- tension은 단순 문화가 아니라 **의사결정 갈등 구조**로 취급하며, evidence를 필수로 붙인다.

#### (5) Role Expectations
이 포지션이 해결해야 할 과제의 스코프와 기대 수준.

- 특히 아래의 **챕터 타입(scope_type)** 을 명시한다:
  - `0→1` (없어서 못하는 것)
  - `1→10` (있지만 느린 것)
  - `reset` (잘못 가고 있어 리셋이 필요한 것)

### 2.2 출력 형태 (예시)

```json
{
  "company_id": "...",
  "job_id": "...",
  "context_version": "1.0",
  "dataset_version": "...",
  "code_sha": "...",
  "generated_at": "...",
  "situation": {
    "stage": "Series A → B",
    "narrative": "..."
  },
  "objectives": ["..."],
  "constraints": ["..."],
  "operating_model": {
    "facets": { "speed": 4, "autonomy": 5, "process": 2, "collaboration": 4, "quality": 3, "risk": 4 },
    "narrative_summary": "..."
  },
  "structural_tensions": [
    { "type": "tech_debt_vs_new_features", "description": "...", "confidence": 0.85 }
  ],
  "role_expectations": {
    "scope_type": "0→1",
    "description": "..."
  },
  "evidence": [
    { "span": "...", "source_id": "...", "confidence": 0.9 }
  ]
}


⸻

3. CandidateContext v1

핵심 질문:

“이 사람은 어떤 상황 경험을 했고, 어떤 방식으로 일하며, 어떤 근거로 그렇게 말할 수 있는가?”

3.1 필수 구성요소

(1) Experience Timeline
각 경력 항목의 기본 구조.
	•	회사 / 직무 / 기간 / 스코프 / 성과 요약

(2) Situational Signals
후보가 실제로 노출된 상황 유형 신호.
	•	예: Series A→B 전환, 스케일링(팀 10→100명), 제로투원, 레거시 개선, 조직 재편
	•	여기에 실패/회복 패턴 도 포함한다 — 회사가 어려워졌을 때 무엇을 했는가

(3) Role Evolution Pattern
역할 변화 패턴(성장/다운시프트)을 구조적 시그널로 포함한다.
	•	예: IC → Lead → Head, Lead → IC 등

(4) Work Style / Culture Signals
	•	커뮤니케이션 스타일, 프로세스 선호도, 실험 vs 안정 지향, 품질 관점 등

(5) PastCompanyContext (Experience별 포함)
각 경력 항목에 그때 그 회사가 어떤 챕터/맥락이었는지 최소 스냅샷을 부착.

필드
설명
stage
당시 펀딩/성장 스테이지
scale
대략적 규모 (인원/매출 범위)
domain
산업/도메인
operating_mode
일하는 방식 (있다면)

3.2 출력 형태 (예시)
{
  "candidate_id": "...",
  "resume_id": "...",
  "context_version": "1.0",
  "dataset_version": "...",
  "code_sha": "...",
  "generated_at": "...",
  "role_evolution_pattern": "IC→Lead→Head",
  "experiences": [
    {
      "company": "...",
      "role": "...",
      "period": "2021-03 ~ 2023-06",
      "scope_summary": "...",
      "outcomes": ["..."],
      "situational_signals": ["Series A→B", "팀 스케일링"],
      "failure_recovery_signals": ["pivot_survival", "post_layoff_rebuild"],
      "past_company_context": {
        "stage": "Series A → B",
        "scale": "50~150명",
        "domain": "B2B SaaS",
        "operating_mode": "자율 / 실험 중심"
      }
    }
  ],
  "work_style_signals": {
    "autonomy_preference": "high",
    "process_tolerance": "low",
    "quality_bias": "medium"
  },
  "evidence": [
    { "span": "...", "source_id": "...", "confidence": 0.85 }
  ]
}


⸻

4. MappingFeatures v1 (Company ↔ Candidate 정렬 결과)

목적:
후보 필터링/랭킹은 DS/MLE 시스템이 수행한다. 우리는 그 시스템이 사용할 수 있는 “맥락 정렬 피처 + 근거 번들(Context Pack)” 을 제공한다.

4.1 입력/출력
	•	입력: job_id + candidate_id(resume_id)
	•	출력:
	•	features: chapter-aware 피처 벡터
	•	evidence_bundle: 회사 근거 + 후보 근거 + (가능하면) 그래프 경로/리포트 요약

4.2 feature 예시
	•	stage_transition_match (A→B, PMF→Scale 등)
	•	tension_alignment (speed vs reliability 같은 딜레마 대응 경험)
	•	vacancy_fit (0→1 / 1→10 / reset)
	•	domain_positioning_fit
	•	role_evolution_fit
	•	resilience_fit (실패/회복 적합)
	•	culture_fit (facet + narrative 기반)

4.3 출력 형태 (예시)

{
  "job_id": "...",
  "candidate_id": "...",
  "mapping_version": "1.0",
  "context_version": "1.0",
  "dataset_version": "...",
  "code_sha": "...",
  "generated_at": "...",
  "features": {
    "stage_transition_match": 0.9,
    "vacancy_fit": 0.8,
    "tension_alignment": 0.7,
    "culture_fit": 0.6,
    "role_evolution_fit": 0.5,
    "resilience_fit": 0.4
  },
  "evidence_bundle": {
    "company": [
      { "span": "...", "source_id": "...", "confidence": 0.9 }
    ],
    "candidate": [
      { "span": "...", "source_id": "...", "confidence": 0.85 }
    ],
    "graph_paths": [
      { "path_summary": "Candidate played Role X during Chapter Y and led to Outcome Z", "confidence": 0.8 }
    ],
    "report_snippets": [
      { "span": "...", "source_id": "graphrag_report:...", "confidence": 0.8 }
    ]
  }
}


⸻

5. 확장 모듈 (v1 이후)

v1에서는 필수가 아니지만, 모듈 방식으로 확장 가능한 하위 Context 개념들.

모듈
설명
StageTransitionContext
A→B, PMF→Scale 등 전환 패턴의 세분화
CultureContext
facet + narrative + evidence의 문화 특화 모듈
RoleScopeContext
플랫폼/성장/데이터 등 역할 도메인 특화
ImpactContext
성과/스케일/지표 근거 중심 모듈
RiskConstraintContext
규제/레거시/품질 요구 등 제약 조건 특화


⸻

6. CompanyTalentSignal (v1.1 이후 확장, 옵션)

후보 분포 기반 관측 신호(예: “진취적인 후보가 많이 모인다”)는 편향이 크므로 CompanyContext 본체에 섞지 않고 별도 산출물로 제공한다.

포함해야 할 메타데이터(필수)
	•	time_window (최근 90/180일 등)
	•	population_definition (지원자/서치 노출/컨택 응답 등)
	•	sample_size
	•	confidence (표본·편향·커버리지 기반)

본 산출물은 feature로만 사용하며, CompanyContext의 정체성을 대체하지 않는다.

⸻

7. GraphRAG 연결 전략 (다음 단계 개요)

7.1 Graph 모델의 최소 단위 (핵심)

GraphRAG 그래프는 단순 스킬 그래프가 아니라, Situation(Chapter)–Role–Outcome(+Evidence) 트리플을 최소 단위로 구성한다.
이를 통해 “맥락(챕터)이 살아있는 그래프”를 구축한다.

7.2 Context별 연결 방식

Context
입력 소스
GraphRAG 역할
출력
CompanyContext
JD, 회사 문서, 채용 히스토리
문서 묶음 indexing → community report
facets / narrative / tensions / evidence
CandidateContext
이력서, 경력 기술서
경력 텍스트 indexing → signal/role/outcome 추출
signals / role_evolution / evidence
PastCompanyContext
외부 펀딩 데이터, 회사 정보 DB
스냅샷 생성
stage / scale / domain
MappingFeatures
job_id + candidate_id
GraphRAG retrieval + path/report 활용
features + evidence_bundle
