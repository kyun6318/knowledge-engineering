# 구직자 검색 시스템 — Context 정의 v1 고정 문서

> 기업 맥락 기반 인재 추천 시스템 설계를 위한 맥락(Context)의 **개념 정의 / 산출물 분류 / 시스템 경계 / 스키마 / 운영 규칙** 통합 문서.
> 이 문서는 GraphRAG 설계 및 일정 논의 진입 전 고정(freeze)하는 기준 문서다.

---

## 0. 핵심 정의

**맥락(Context)은 '현재 상태(state)'가 아니라 '어디서 와서 어디로 가는가'를 나타내는 궤적(trajectory) + 상황(situation)의 복합이다.**

실무 표현으로는 **"챕터(chapter)"** 이며, 각 챕터는 변곡점 / 긴장 / 의도된 방향을 포함한다.

### 매칭의 핵심 원리

맥락 매칭은 키워드 매칭이 아니라,
**"기업이 앞으로 겪을 챕터(미래 벡터)를 후보가 이미 겪었는가(과거 벡터)"** 를 평가하는 것이다.

```
기업 CompanyContext의 미래 벡터  ←→  CandidateContext의 과거 경험 벡터
```

예: "Series A→B 도약을 준비 중인 기업" ↔ "이전 회사에서 Series A→B 전환을 통과한 후보"

---

## 1. 산출물(Artifacts) 4종

시스템이 생산하는 산출물은 아래 4종으로 분류한다.

| # | 산출물 | 정의 | 생성 소스 |
|---|---|---|---|
| 1 | **CompanyContext** | 채용 기업/포지션의 "현재 챕터 및 다음 챕터" 정의 | JD / 회사 문서 / 채용 히스토리 |
| 2 | **CandidateContext** | 후보가 "살아온 챕터" 정의 (Experience별 PastCompanyContext 포함) | 이력서 / 경력 기술서 / 프로젝트/성과 |
| 3 | **MappingFeatures + EvidenceBundle** | Company ↔ Candidate 챕터 정렬 결과 (피처 벡터 + 근거) | CompanyContext + CandidateContext |
| 4 | **CompanyTalentSignal** *(옵션)* | 후보 분포로부터 관측된 신호. CompanyContext 본체와 분리, feature로만 사용 | 후보 집합 통계 (표본/기간/모집단/신뢰도 포함) |

### 시스템 경계 선언

> **GraphRAG 파트의 책임**: CompanyContext / CandidateContext / MappingFeatures를 생산하고 근거(Evidence)를 공급한다.
> **최종 랭킹 / 필터링**: DS/MLE 시스템이 수행한다.
> GraphRAG는 "정렬 가능한 맥락 피처 + 근거"를 공급하는 것까지가 범위다.

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

- 최소 단위: `source_id + span(문장 범위) + confidence + extracted_at`
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

### 3.1 CompanyChapter 구성요소

"기업이 지금 어떤 챕터를 살고 있는가"

| 구성요소 | 설명 | 예시 |
|---|---|---|
| **Growth Trajectory / Inflection** | 현재 변곡점의 성격 | `Series A→B 도약`, `PMF 이후 Scale-up`, `글로벌 확장 준비` |
| **Structural Tensions** | 내부 긴장/딜레마 | 창업자→전문경영 전환, 기술부채 vs 신기능 개발 |
| **Domain / Market Positioning** | 경쟁 맥락 | B2B SaaS→Enterprise, 버티컬 AI 특정 산업 진입 |
| **Vacancy Chapter (팀 공백의 성격)** | 포지션이 열린 이유 | `0→1` (없어서 못함), `1→10` (있는데 느림), `reset` (잘못 가고 있음) |
| **Operating Model / Culture** | 일하는 방식 | facet(정형) + narrative(서술) + evidence(근거) |
| **Role Expectations** | 이 챕터에서 필요한 역할/스코프/성과 기대 | — |

### 3.2 CandidateChapter 구성요소

"후보가 어떤 챕터를 살아왔는가"

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

### GraphRAG 연결 전략

| Context | 입력 소스 | GraphRAG 역할 | 출력 |
|---|---|---|---|
| `CompanyContext` | JD, 회사 문서, 채용 히스토리 | 문서 묶음 indexing → community report | facets / narrative / evidence |
| `CandidateContext` | 이력서, 경력 기술서 | 경력 텍스트 indexing → signal 추출 | signals / timeline / evidence |
| `PastCompanyContext` | 외부 펀딩 데이터, 회사 정보 DB | 스냅샷 생성 | stage / scale / domain |

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

- 회사 근거 (JD/문서 span + source_id + confidence)
- 후보 근거 (이력서/경력 span + source_id + confidence)
- 그래프 경로 / community report 요약 (있으면)

---

## 6. CompanyTalentSignal (옵션): 후보 분포 기반 관측 신호

"진취적인 후보가 많은 회사는 진취적이다" 같은 가설은 관측 신호로 유용하지만 편향이 크다.

- `CompanyContext` 본체에 섞지 않고 **별도 산출물**로 분리한다.
- 필수 포함 메타데이터: 표본 크기 / 기간 / 모집단 정의 / 신뢰도
- 소비 시에도 **feature로만 사용** (가중치 조절 가능)

```json
{
  "company_id": "...",
  "signal_type": "culture_progressiveness",
  "value": 0.74,
  "sample_size": 42,
  "period": "2022-01 ~ 2024-12",
  "population_definition": "채용 완료 후보 중 재직 6개월 이상",
  "confidence": 0.65,
  "generated_at": "..."
}
```

---

## 7. 스키마 참조 (JSON)

### CompanyContext

```json
{
  "company_id": "...",
  "context_version": "1.0",
  "dataset_version": "...",
  "code_sha": "...",
  "generated_at": "2026-02-01T00:00:00Z",
  "chapter": {
    "stage": "Series A → B",
    "trajectory_narrative": "...",
    "structural_tensions": ["창업자→전문경영 전환 중"],
    "domain_positioning": "B2B SaaS → Enterprise"
  },
  "vacancy": {
    "scope_type": "1→10",
    "description": "..."
  },
  "objectives": ["ARR 3x", "엔터프라이즈 영업 체계 구축"],
  "constraints": ["런웨이 18개월", "레거시 모놀리스"],
  "operating_model": {
    "facets": { "speed": 4, "autonomy": 5, "process": 2, "risk_tolerance": 4 },
    "narrative_summary": "..."
  },
  "role_expectations": { "scope": "...", "success_criteria": "..." },
  "evidence": [
    { "source_id": "jd_001", "span": "...", "confidence": 0.9, "extracted_at": "..." }
  ]
}
```

### CandidateContext

```json
{
  "candidate_id": "...",
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
    "experiment_orientation": "high"
  },
  "evidence": [
    { "source_id": "resume_001", "span": "...", "confidence": 0.85, "extracted_at": "..." }
  ]
}
```

### MappingFeatures

```json
{
  "company_id": "...",
  "candidate_id": "...",
  "context_version": "1.0",
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
    "company_evidence": [{ "source_id": "...", "span": "...", "confidence": 0.9 }],
    "candidate_evidence": [{ "source_id": "...", "span": "...", "confidence": 0.85 }],
    "graph_path_summary": "..."
  }
}
```

---

## 8. 확장 모듈 (v2 이후)

v1에서는 필수가 아니지만, 모듈 방식으로 확장 가능한 하위 Context 개념들.

| 모듈 | 설명 |
|---|---|
| `StageTransitionContext` | A→B, PMF→Scale 등 전환 패턴의 세분화 |
| `CultureContext` | facet + narrative + evidence의 문화 특화 모듈 |
| `RoleScopeContext` | 플랫폼/성장/데이터 등 역할 도메인 특화 |
| `ImpactContext` | 성과/스케일/지표 근거 중심 모듈 |
| `RiskConstraintContext` | 규제/레거시/품질 요구 등 제약 조건 특화 |

---

## 9. 다음 단계 (Next Steps)

이 문서를 고정(freeze)하고, 이어서 논의할 항목:

1. **GraphRAG indexing/retrieval 파이프라인** — community / report 등 어떤 아티팩트를 만들지
2. **저장소 및 서빙 설계** — CompanyContext / CandidateContext / MappingFeatures를 어떤 저장소로 서빙할지
3. **v1 MVP 일정** — 기본 구축 범위와 v2 이후 모듈 확장을 어떻게 쪼갤지

---

*version: v1.0 | last updated: 2026-02*
