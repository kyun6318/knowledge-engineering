# CandidateContext v15 — 통합판

> v4 원본에 A1(ScopeType -> Seniority 변환 규칙)을 통합.
>
> 작성일: 2026-03-10 | 현재 유효 버전: **v15** | 기준: v4 CandidateContext + v4 amendments (A1) + v12 데이터 분석 v2.1
>
> **v15 변경** (2026-03-10): v14 리뷰 피드백 반영
> - [X-2] §2.6 Person 보강 속성에 `name` 필드 소스 명시 (04_graph_schema Person.name과의 불일치 해소)
>
> <details><summary>v8~v14 변경 이력</summary>
>
> **v14 변경** (2026-03-10): v13 리뷰 피드백 반영
> - [X-3] §0 T1(이력서) confidence 상한 0.85가 Company T1(JD) 0.80과 다른 이유 명시
> - [U-7] §2.8 Career[] 시간순 정렬 보장 전제 조건 명시
> - [U-6] §2.7 짧은 텍스트(50자 미만) LLM 추출 품질 대응 전략 추가
>
> <details><summary>v8~v13 변경 이력</summary>
>
> **v13 변경** (2026-03-10): v12 데이터 분석 v2.1 결과 인라인 반영
> - Person 보강 속성, CareerDescription FK 제약, duration_months 계산, 실측 fill rate
>
> **v8 변경** (2026-03-08): [M-3] domain_depth에 evidence 필드 추가
>
> </details>

---

## 0. 데이터 소스 현황

| Tier | 소스 | confidence 상한 | 현재 상태 | source_type enum |
|---|---|---|---|---|
| T1 | 자사 이력서 | 0.85 | 접근 가능 | `self_resume` |
| T2 | 경력 기술서 | 0.85 | 접근 가능 (이력서에 포함되는 경우) | `career_desc` |
| T3 | LinkedIn 프로필 | 0.65 | 접근 정책 확인 필요 | `linkedin` |
| T4 | NICE 기업 정보 (PastCompanyContext 역산용) | 0.70 | 보유 | `nice` |
| T5 | Closed-loop 질문 응답 | 0.80 | v2 이후 | `enrichment_qa` |

> **[v14] 참고**: 본 문서의 T1(자사 이력서) 상한 0.85는 01_company_context의 T1(JD) 상한 0.80보다 높다. 이력서는 본인이 직접 작성하여 사실 기반 신뢰도가 높으나, JD는 채용 마케팅 특성상 과장 가능성이 있어 차등 적용한다.

### 교차 검증 규칙

- 자사 이력서 + LinkedIn 동시 존재 시:
  - 일치하는 claim → `confidence = min(max(c1, c2) + 0.10, 0.90)`
  - 불일치하는 claim → `confidence = min(c1, c2) * 0.5` + `contradiction: true`
- 자사 이력서만 존재 시: 단일 소스 confidence 그대로 사용

---

## 1. 필드 정의 — 추출 난이도별 분류

### 1.1 Low Difficulty — 이력서에서 직접 추출

| 필드 | 타입 | 추출 방법 | 추출 난이도 | 설명 |
|---|---|---|---|---|
| `company` | string | Rule + LLM | 낮음 | 재직 회사명 |
| `role_title` | string | Rule + LLM | 낮음 | 직무/직책명 |
| `period` | Period | Rule | 낮음 | 재직 기간 (시작~종료) |
| `tech_stack` | string[] | Rule + LLM | 낮음 | 사용 기술 스택 |
| `responsibilities` | string[] | LLM | 낮음 | 주요 업무 |

### 1.2 Medium Difficulty — 문맥 해석 필요

| 필드 | 타입 | 추출 방법 | 추출 난이도 | 설명 |
|---|---|---|---|---|
| `scope_summary` | string | LLM | 중간 | 역할 범위 요약 (IC/Lead/Head 수준) |
| `outcomes` | Outcome[] | LLM | 중간 | 정량/정성 성과 목록 |
| `situational_signals` | string[] | LLM | 중간 | 경험한 상황 라벨 (taxonomy 기반) |
| `team_scale` | string | LLM | 중간 | 팀 규모/조직 맥락 |
| `role_evolution` | string | LLM (전체 experience 대상) | 중간 | 커리어 성장 패턴 |

### 1.3 High Difficulty — 추론 또는 외부 데이터 필요

| 필드 | 타입 | 추출 방법 | 추출 난이도 | v1 대응 |
|---|---|---|---|---|
| `failure_recovery` | string | LLM | 높음 | null 허용 (후보가 기술하지 않는 경우 다수) |
| `work_style_signals` | WorkStyle | LLM | 높음 | 이력서 텍스트에 단서가 있을 때만 |
| `past_company_context` | PastCompanyCtx | NICE Lookup + LLM | 중간~높음 | NICE 현재 시점 데이터 기반 |
| `domain_depth` | string | LLM (전체 experience 대상) | 중간 | 회사/산업 반복 패턴 분석 |

---

## 2. 핵심 구조 상세 정의

### 2.1 Experience (경험 단위 = Chapter)

v3의 Chapter 개념과 GraphDB의 Chapter 노드를 통합한 구조.

```typescript
interface Experience {
  // --- 직접 추출 (Low) ---
  experience_id: string;         // 자동 생성 (candidate_id + seq)
  company: string;               // 회사명
  role_title: string;            // 직무/직책명
  period: {
    start: string;               // "2021-03" (YYYY-MM)
    end: string | "present";     // "2023-06" or "present"
    duration_months: number;     // [v13] career.period.period DATERANGE에서 직접 계산 (daysWorked 100% 제로, 00_data_source_mapping §3.2 D3)
  };
  tech_stack: string[];          // 정규화된 기술 스택

  // --- 문맥 해석 (Medium) ---
  scope_summary: string | null;  // "5명 팀의 테크 리드로서 결제 시스템 전체 아키텍처 담당"
  scope_type: ScopeType;         // IC / LEAD / HEAD / FOUNDER / UNKNOWN
  outcomes: Outcome[];           // 성과 목록
  situational_signals: SituationalSignal[]; // 상황 라벨

  // --- 외부 데이터 + 추론 (High) ---
  failure_recovery: string | null;
  past_company_context: PastCompanyContext | null;

  // --- Evidence ---
  evidence: Evidence[];
}

type ScopeType = "IC" | "LEAD" | "HEAD" | "FOUNDER" | "UNKNOWN";
```

#### ScopeType -> Seniority 변환 규칙 [v7 추가]

CandidateContext의 scope_type(IC/LEAD/HEAD/FOUNDER/UNKNOWN)과 CompanyContext vacancy의 seniority(JUNIOR/MID/SENIOR/LEAD/HEAD/UNKNOWN)는 서로 다른 체계를 사용한다. MappingFeatures의 role_fit 계산 시 아래 변환 규칙을 선행 적용한다.

**scope_type -> seniority 변환**:

| scope_type (Candidate) | 대응 seniority 범위 | 비고 |
|---|---|---|
| IC | JUNIOR, MID, SENIOR | 경력 연수로 세분화 |
| LEAD | SENIOR, LEAD | Lead 경험자는 Senior 이상 |
| HEAD | HEAD | 직접 대응 |
| FOUNDER | LEAD, HEAD | 경력 연수 기반 분기 |
| UNKNOWN | -- | 매핑 불가, role_fit에서 경력 연수 기반 fallback |

**IC의 세분화 규칙** (경력 연수 기반):

```python
def ic_to_seniority(total_experience_years):
    if total_experience_years < 3:
        return "JUNIOR"
    elif total_experience_years < 6:
        return "MID"
    else:
        return "SENIOR"
```

**role_fit 계산 시 적용**:

```python
def get_candidate_seniority(candidate_ctx):
    """후보의 최근 경험에서 seniority 추정"""
    latest_exp = candidate_ctx.experiences[0] if candidate_ctx.experiences else None
    if not latest_exp:
        return "UNKNOWN"

    scope = latest_exp.scope_type
    years = candidate_ctx.role_evolution.total_experience_years

    if scope == "IC":
        return ic_to_seniority(years)
    elif scope == "LEAD":
        return "LEAD"
    elif scope == "HEAD":
        return "HEAD"
    elif scope == "FOUNDER":
        # 경력 연수 기반 HEAD 승격 규칙
        if years >= 10:
            return "HEAD"
        return "LEAD"
    else:
        return "UNKNOWN"
```

> 이 함수는 `03_mapping_features.md` F5(role_fit)에서 참조된다.

### 2.2 Outcome (성과)

v3 GraphDB의 Outcome 노드를 Evidence 통합 모델과 정합.

```typescript
interface Outcome {
  description: string;          // "MAU 10x 달성", "팀 4→18명 확장"
  outcome_type: OutcomeType;    // METRIC / SCALE / DELIVERY / ORGANIZATIONAL / OTHER
  quantitative: boolean;        // 정량적 수치 포함 여부
  metric_value: string | null;  // "10x", "4→18명" (있으면)
  confidence: number;           // 성과 claim의 신뢰도
  evidence: Evidence;           // 근거 (이력서 원문 span)
}

type OutcomeType =
  | "METRIC"          // MAU, 매출, 전환율 등 수치 성과
  | "SCALE"           // 팀/조직/시스템 규모 확장
  | "DELIVERY"        // 제품/프로젝트 완료
  | "ORGANIZATIONAL"  // 팀 빌딩, 프로세스 구축
  | "OTHER";
```

### 2.3 SituationalSignal (상황 라벨)

v3 Chapter의 "Experienced Trajectory / Verified Inflection"을 구현 가능하게 재정의.
**Taxonomy를 고정하여 LLM 추출의 일관성을 확보한다.**

```typescript
interface SituationalSignal {
  signal_label: SignalLabel;    // 고정 taxonomy
  description: string;          // 자유 서술
  confidence: number;
  evidence: Evidence;
}
```

**SignalLabel Taxonomy (v1 고정, 14개)**:

| 카테고리 | label | 설명 | 이력서 탐지 패턴 |
|---|---|---|---|
| 성장 단계 | `EARLY_STAGE` | 초기 스타트업 경험 | "초기 멤버", "n번째 직원", "시드/엔젤" |
| | `SCALE_UP` | 스케일업 경험 | "급성장", "사용자 n배", "팀 확장" |
| | `TURNAROUND` | 턴어라운드/회생 | "피봇", "방향 전환", "구조조정 후" |
| | `GLOBAL_EXPANSION` | 글로벌 확장 | "해외 진출", "글로벌", "다국적" |
| 조직 변화 | `TEAM_BUILDING` | 팀 신규 구성/빌딩 | "팀 구축", "0→n명", "채용" |
| | `TEAM_SCALING` | 팀 규모 확대 | "n→m명", "팀 확장", "조직 성장" |
| | `REORG` | 조직 개편 경험 | "조직 개편", "스쿼드 전환", "합병" |
| 기술 변화 | `LEGACY_MODERNIZATION` | 레거시 개선 | "리팩토링", "마이그레이션", "모놀리스→MSA" |
| | `NEW_SYSTEM_BUILD` | 신규 시스템 구축 | "신규 구축", "처음부터", "0→1" |
| | `TECH_STACK_TRANSITION` | 기술 스택 전환 | "전환", "도입", "migration" |
| 비즈니스 | `PMF_SEARCH` | PMF 탐색 | "PMF", "제품-시장 적합성", "가설 검증" |
| | `MONETIZATION` | 수익화/비즈 모델 구축 | "수익화", "BM", "매출 n배" |
| | `ENTERPRISE_TRANSITION` | B2C→B2B 또는 SMB→Enterprise | "엔터프라이즈", "B2B 전환" |
| 기타 | `OTHER` | 위 카테고리 미해당 | — |

```python
# situational_signal 추출 pseudo-code
def extract_signals(experience_text, company_info=None):
    # Step 1: LLM에게 taxonomy 목록을 제공하고 분류 요청
    prompt = f"""
    아래 경력 텍스트에서 해당하는 상황 라벨을 모두 선택하세요.
    반드시 제공된 taxonomy에서만 선택하고, 각각에 대해 근거 문장을 인용하세요.
    근거가 없는 라벨은 선택하지 마세요.

    [Taxonomy]
    {SIGNAL_TAXONOMY}

    [경력 텍스트]
    {experience_text}

    [출력 형식]
    - signal_label: ...
      description: ...
      evidence_span: "..." (원문 인용)
      confidence: 0.0~1.0
    """
    raw_signals = llm_call(prompt)

    # Step 2: confidence 보정 — source ceiling 적용
    for signal in raw_signals:
        signal.confidence = min(signal.confidence, SOURCE_CEILING[source_type])

    # Step 3: PastCompanyContext가 있으면 교차 검증
    if company_info:
        for signal in raw_signals:
            if signal.label == "EARLY_STAGE" and company_info.employee_count > 100:
                signal.confidence *= 0.5  # 불일치 감쇠
            elif signal.label == "SCALE_UP" and company_info.employee_count > 50:
                signal.confidence = min(signal.confidence + 0.10, SOURCE_CEILING)

    return [s for s in raw_signals if s.confidence >= 0.20]  # 최소 임계값
```

### 2.4 PastCompanyContext (v1: 현재 시점 기반)

v3 평가에서 지적한 "시점 특정의 어려움"을 인정하고, v1에서는 **현재 시점 NICE 데이터**만 사용.

```typescript
interface PastCompanyContext {
  company_name: string;
  // NICE 팩트 (현재 시점)
  industry_code: string | null;
  industry_label: string | null;
  employee_count: number | null;      // 현재 시점
  founded_year: number | null;
  revenue_range: string | null;
  is_regulated_industry: boolean;

  // 추정 (Rule 기반)
  estimated_stage_at_tenure: string | null; // 재직 당시 추정 stage
  stage_estimation_method: string;          // "nice_current" | "nice_interpolated" | "unknown"

  // 메타
  nice_data_date: string | null;       // NICE 데이터 기준일
  confidence: number;                  // 전체 PastCompanyContext의 신뢰도
  evidence: Evidence[];
}
```

```python
# PastCompanyContext 역산 pseudo-code (v1)
def build_past_company_context(company_name, tenure_start, tenure_end):
    nice = lookup_nice(company_name)
    if not nice:
        return PastCompanyContext(
            company_name=company_name,
            confidence=0.0,
            stage_estimation_method="unknown",
            evidence=[]
        )

    # 현재 시점 데이터 그대로 사용 (v1)
    ctx = PastCompanyContext(
        company_name=company_name,
        industry_code=nice.industry_code,
        industry_label=nice.industry_label,
        employee_count=nice.employee_count,
        founded_year=nice.founded_year,
        revenue_range=nice.revenue_range,
        is_regulated_industry=is_regulated(nice.industry_code),
        nice_data_date=nice.data_date,
        stage_estimation_method="nice_current",
        evidence=[Evidence(source_id=nice.id, source_type="nice", ...)]
    )

    # 재직 시점 stage 추정 (rough heuristic)
    years_at_company = (tenure_start.year - nice.founded_year)
    ctx.estimated_stage_at_tenure = estimate_stage_by_age(
        years_at_company, nice.employee_count, nice.revenue_range
    )

    # confidence: 재직 시점과 현재의 차이가 클수록 하락
    years_gap = current_year - tenure_end.year
    ctx.confidence = max(0.20, 0.60 - years_gap * 0.08)

    return ctx
```

### 2.5 WorkStyleSignals

```typescript
interface WorkStyleSignals {
  autonomy_preference: Level | null;   // HIGH / MID / LOW / null
  process_tolerance: Level | null;
  experiment_orientation: Level | null;
  collaboration_style: string | null;  // 자유 서술
  confidence: number;                  // 전체 work_style의 신뢰도
  evidence: Evidence[];
}

type Level = "HIGH" | "MID" | "LOW";
```

**v1 현실**: 이력서에서 work_style_signals를 추출할 수 있는 경우는 **20~30% 미만**으로 예상. 대부분 null이 될 것이며, 이는 정상 상태로 처리.

### 2.6 Person 보강 속성 [v13 신규, 00_data_source_mapping §3.5 인라인]

v12 데이터 분석 v2.1에서 발견된 보강 가능 속성을 Person 수준에 추가한다. 상세 소스 매핑과 계산 로직은 `00_data_source_mapping.md §3.5`를 참조.

| 속성 | 타입 | fill rate | 용도 | 주의사항 |
|---|---|---|---|---|
| `name` | string | ~100% | Person 식별 (Graph 노드 표시용) | **소스: `profile.name`** (resume-hub). 매칭 점수에 사용 금지 [v15 X-2] |
| `gender` | string \| null | 100% | 매칭 편향 모니터링 전용 | **매칭 점수에 사용 금지** |
| `age` | int \| null | 93.3% | 세그먼트 분석 보조 | 1~100 필터, age>100 이상치 제거 |
| `career_type` | string | 100% | 경력/신입 세그먼트 | EXPERIENCED 69.1% / NEW_COMER 30.9% |
| `freshness_weight` | float | 100% | 데이터 신선도 가중치 | 90일 이내 1.0, 5년+ 0.3 |
| `education_level` | string \| null | 95.6% | 학력 필터링 | **education.schoolType을 진실 소스** (finalEducationLevel 35.6% 불일치) |

> **[v13]** 이 속성들은 `04_graph_schema.md`의 Person 노드에도 반영되었다 (C-1).
> **[v15]** `name` 필드 추가. 04_graph_schema Person 노드에 `name: STRING`이 정의되어 있으나 CandidateContext에서 소스가 미정의였던 불일치(X-2)를 해소.

### 2.7 CareerDescription FK 부재 제약 [v13 신규, 00_data_source_mapping §3.2 D4 인라인]

> **핵심 제약**: CareerDescription 테이블에 `career_id` FK가 없다. resume_id로만 연결되므로, 복수 경력이 있는 이력서에서 어떤 경력에 대한 기술인지 career 단위 매핑이 불가능하다.

**처리 전략**:
1. CareerDescription.description 전문을 가져온다 (fill rate 16.9%, 중앙값 527자)
2. 해당 resume의 Career[] 목록을 함께 LLM에 전달한다
3. LLM이 텍스트 컨텍스트로 각 career에 outcome을 귀속한다
4. 귀속 불가 시 resume 전체에 귀속 (confidence 하향)
5. CareerDescription 미보유 시 SelfIntroduction fallback (fill rate 64.1%, 중앙값 1,320자)

> **[v14] 짧은 텍스트 대응**: workDetails 중앙값 96자로, 50자 미만인 경우 LLM 추출 품질이 저하된다.
> - 50자 미만 workDetails: scope_summary 추출만 시도, outcomes/situational_signals는 스킵 (confidence 부족)
> - 50~100자 workDetails: 추출 시도하되 confidence에 0.8 감쇠 적용
> - 100자 이상: 정상 추출

### 2.8 RoleEvolution (전체 커리어 수준)

```typescript
interface RoleEvolution {
  pattern: RolePattern;        // IC_TO_LEAD / IC_DEPTH / LEAD_TO_HEAD / etc.
  description: string;         // "IC → Lead → Head, 일관된 상향 이동"
  total_experience_years: number;
  confidence: number;
  evidence: Evidence[];        // 패턴 판단 근거 (여러 experience 걸침)
}

type RolePattern =
  | "IC_TO_LEAD"          // IC → Lead 성장
  | "IC_DEPTH"            // IC 전문성 심화
  | "LEAD_TO_HEAD"        // Lead → Head/Director 성장
  | "FOUNDER"             // 창업 경험
  | "GENERALIST"          // 다양한 역할 전환
  | "DOWNSHIFT"           // 상위 → 하위 역할 이동
  | "LATERAL"             // 동급 역할 간 이동
  | "UNKNOWN";
```

> **[v14] 전제 조건**: Career[] 배열은 `period.start` 기준 **시간 역순** (최근 → 과거)으로 정렬되어야 한다. resume-hub에서 조회 시 `ORDER BY period.started_on DESC`를 적용한다. 시간순이 보장되지 않으면 role_evolution 추출이 부정확해질 수 있다.

```python
# role_evolution 추출 pseudo-code
def extract_role_evolution(experiences):
    if len(experiences) < 2:
        return RoleEvolution(pattern="UNKNOWN", confidence=0.30)

    scope_sequence = [exp.scope_type for exp in experiences]  # 시간순

    if scope_sequence == sorted(scope_sequence, key=SCOPE_ORDER.get):
        # 일관된 상향 이동
        if "HEAD" in scope_sequence:
            return RoleEvolution(pattern="LEAD_TO_HEAD", confidence=0.70)
        elif "LEAD" in scope_sequence:
            return RoleEvolution(pattern="IC_TO_LEAD", confidence=0.70)

    if all(s == "IC" for s in scope_sequence):
        return RoleEvolution(pattern="IC_DEPTH", confidence=0.65)

    if "FOUNDER" in scope_sequence:
        return RoleEvolution(pattern="FOUNDER", confidence=0.75)

    # LLM fallback
    return llm_classify_role_evolution(experiences)
```

---

## 3. v4 CandidateContext JSON 스키마

```json
{
  "$schema": "CandidateContext_v4",
  "candidate_id": "cand_99999",
  "resume_id": "resume_001",

  "_meta": {
    "context_version": "4.0",
    "dataset_version": "2026-03-01",
    "code_sha": "abc1234",
    "generated_at": "2026-03-08T10:00:00Z",
    "sources_used": ["self_resume"],
    "completeness": {
      "total_fields": 12,
      "filled_fields": 9,
      "fill_rate": 0.75,
      "missing_fields": [
        "work_style_signals",
        "experiences[0].failure_recovery",
        "experiences[1].past_company_context"
      ]
    }
  },

  "experiences": [
    {
      "experience_id": "cand_99999_exp_01",
      "company": "A사",
      "role_title": "Engineering Lead",
      "period": {
        "start": "2021-03",
        "end": "2023-06",
        "duration_months": 27
      },
      "tech_stack": ["Python", "FastAPI", "PostgreSQL", "AWS"],
      "scope_summary": "백엔드 팀 4→18명 확장, 결제 시스템 아키텍처 전체 총괄",
      "scope_type": "LEAD",

      "outcomes": [
        {
          "description": "MAU 10x 달성",
          "outcome_type": "METRIC",
          "quantitative": true,
          "metric_value": "10x",
          "confidence": 0.75,
          "evidence": {
            "source_id": "resume_001",
            "source_type": "self_resume",
            "span": "2년간 MAU를 50만에서 500만으로 성장시킴",
            "confidence": 0.75,
            "extracted_at": "2026-03-08T10:00:00Z"
          }
        },
        {
          "description": "팀 4→18명 확장",
          "outcome_type": "SCALE",
          "quantitative": true,
          "metric_value": "4→18명",
          "confidence": 0.80,
          "evidence": {
            "source_id": "resume_001",
            "source_type": "self_resume",
            "span": "백엔드 팀을 4명에서 18명으로 확장, 채용/온보딩 주도",
            "confidence": 0.80,
            "extracted_at": "2026-03-08T10:00:00Z"
          }
        }
      ],

      "situational_signals": [
        {
          "signal_label": "SCALE_UP",
          "description": "Series A→B 전환기의 급성장 경험",
          "confidence": 0.70,
          "evidence": {
            "source_id": "resume_001",
            "source_type": "self_resume",
            "span": "시리즈 A에서 B로 전환하는 급성장기에 핵심 기술 인프라 구축",
            "confidence": 0.70,
            "extracted_at": "2026-03-08T10:00:00Z"
          }
        },
        {
          "signal_label": "TEAM_SCALING",
          "description": "팀 4→18명 스케일링 경험",
          "confidence": 0.80,
          "evidence": {
            "source_id": "resume_001",
            "source_type": "self_resume",
            "span": "백엔드 팀을 4명에서 18명으로 확장",
            "confidence": 0.80,
            "extracted_at": "2026-03-08T10:00:00Z"
          }
        }
      ],

      "failure_recovery": null,

      "past_company_context": {
        "company_name": "A사",
        "industry_code": "J63112",
        "industry_label": "소프트웨어 개발",
        "employee_count": 150,
        "founded_year": 2018,
        "revenue_range": "50억~100억",
        "is_regulated_industry": false,
        "estimated_stage_at_tenure": "GROWTH",
        "stage_estimation_method": "nice_current",
        "nice_data_date": "2026-01-15",
        "confidence": 0.44,
        "evidence": [
          {
            "source_id": "nice_comp_A",
            "source_type": "nice",
            "span": "A사: 설립 2018, 종업원 150명, 소프트웨어 개발",
            "confidence": 0.70,
            "extracted_at": "2026-01-15T00:00:00Z"
          }
        ]
      },

      "evidence": [
        {
          "source_id": "resume_001",
          "source_type": "self_resume",
          "span": "A사 Engineering Lead (2021.03~2023.06) ...",
          "confidence": 0.85,
          "extracted_at": "2026-03-08T10:00:00Z"
        }
      ]
    }
  ],

  "role_evolution": {
    "pattern": "IC_TO_LEAD",
    "description": "Junior Engineer → Senior → Lead, 일관된 기술 리더십 성장",
    "total_experience_years": 7,
    "confidence": 0.70,
    "evidence": [
      {
        "source_id": "resume_001",
        "source_type": "self_resume",
        "span": "...(전체 커리어 요약 부분)",
        "confidence": 0.70,
        "extracted_at": "2026-03-08T10:00:00Z"
      }
    ]
  },

  "domain_depth": {
    "primary_domain": "B2B SaaS",
    "domain_experience_count": 3,
    "description": "B2B SaaS 3개 회사에서 반복 경험, 결제/인프라 도메인 특화",
    "confidence": 0.65,
    "evidence": [
      {
        "source_id": "resume_001",
        "source_type": "self_resume",
        "span": "A사(B2B SaaS), B사(B2B SaaS 결제), C사(B2B SaaS 인프라)",
        "confidence": 0.65,
        "extracted_at": "2026-03-08T10:00:00Z"
      }
    ]
  },

  "work_style_signals": null
}
```

---

## 4. v3 GraphDB 엔티티 구조와의 통합

v3 GraphDB Ideation에서 정의한 노드/관계를 CandidateContext v4와 매핑.

### 노드 매핑

| GraphDB 노드 | CandidateContext v4 필드 | 속성 |
|---|---|---|
| `:Person` | 최상위 CandidateContext | candidate_id, resume_id |
| `:Chapter` | `experiences[]` 각 항목 | experience_id, scope_summary, situational_signals, evidence_chunk(=evidence[].span 결합) |
| `:Role` | `experiences[].role_title` + `scope_type` | name, scope_type |
| `:Skill` | `experiences[].tech_stack[]` | name (정규화) |
| `:Organization` | `experiences[].past_company_context` | 모든 PastCompanyContext 필드 |
| `:Outcome` | `experiences[].outcomes[]` | description, outcome_type, metric_value |

### 관계 매핑

| GraphDB 관계 | 생성 규칙 | edge 속성 |
|---|---|---|
| `(:Person)-[:HAS_EXPERIENCED]->(:Chapter)` | 모든 experience에 대해 | period, seq_order |
| `(:Chapter)-[:NEXT_CHAPTER]->(:Chapter)` | period.start 기준 시간순 연결 | gap_months (공백기) |
| `(:Chapter)-[:PERFORMED_ROLE]->(:Role)` | role_title + scope_type으로 | confidence |
| `(:Chapter)-[:USED_SKILL]->(:Skill)` | tech_stack 각 항목에 대해 | proficiency_level (v2) |
| `(:Chapter)-[:OCCURRED_AT]->(:Organization)` | past_company_context 기반 | tenure_start, tenure_end |
| `(:Chapter)-[:PRODUCED_OUTCOME]->(:Outcome)` | outcomes 각 항목에 대해 | confidence |
| `(:Chapter)-[:HAS_SIGNAL]->(:SituationalSignal)` | **v4 추가** | confidence |

### v4 추가 노드: SituationalSignal

v3에 없던 노드. situational_signals를 **공유 가능한 노드**로 분리하여 "같은 상황을 경험한 후보"를 그래프 탐색으로 찾을 수 있게 한다.

```
(:SituationalSignal {label: "SCALE_UP", description: "급성장기 경험"})
```

- 같은 signal_label을 가진 노드는 **공유**된다 (여러 Chapter가 동일 SituationalSignal 노드를 가리킴)
- 이를 통해 `MATCH (c1:Chapter)-[:HAS_SIGNAL]->(s:SituationalSignal)<-[:HAS_SIGNAL]-(c2:Chapter)` 패턴으로 유사 경험 후보를 탐색 가능

---

## 5. 추출 파이프라인 개요 [v13 업데이트]

> 상세 파이프라인은 `00_data_source_mapping.md §5.2`를 참조.

```
[resume-hub DB]
    │
    ├─[0] 서비스 풀 필터링 [v12 D6]
    │   ├─ PUBLIC + COMPLETED + main_flag=1 → 5,545,741
    │   ├─ 품질 등급 HIGH+PREMIUM → 3,183,554 (57.4%)
    │   └─ deletedAt IS NULL 필터
    │
    ├─[1] 구조화 데이터 조회 (Rule-based)
    │   ├─ SiteUserMapping.id → candidate_id
    │   ├─ Profile → gender, age(1~100 필터), career_type [v13]
    │   ├─ Resume.userUpdatedAt → freshness_weight [v13]
    │   ├─ Career[] → company, period (DATERANGE → duration_months 직접 계산) [v13 D3]
    │   ├─ Career.positionTitleCode/positionGradeCode → scope_type 1차 추정
    │   ├─ Career.jobClassificationCodes → role_title (code-hub Lookup)
    │   ├─ Skill[] (type=HARD) → tech_stack (code-hub 정규화, 38.3% 커버리지)
    │   ├─ Education[] → education_level (schoolType 진실 소스) [v13 D8]
    │   └─ Certificate[] → type 변환 후 codehub 조회 [v12 D5]
    │
    ├─[2] LLM 추출 (Experience별)
    │   ├─ scope_summary, scope_type (구조화 결과 교차 검증)
    │   ├─ outcomes (description + metric_value)
    │   ├─ situational_signals (taxonomy 기반)
    │   └─ failure_recovery (있을 때만)
    │
    ├─[3] LLM 추출 (전체 커리어)
    │   ├─ CareerDescription.description (16.9%) → outcomes 1차 추출 [v13 D4 제약]
    │   ├─ SelfIntroduction[] (64.1%) → outcomes 2차 추출, work_style_signals
    │   ├─ role_evolution
    │   ├─ domain_depth (구조화 결과와 LLM 결과 병합)
    │   └─ work_style_signals
    │
    ├─[4] PastCompanyContext 보강
    │   ├─ Career.companyName → job-hub 역참조 (confidence 0.75) [v12]
    │   ├─ Career.businessRegistrationNumber (62%) → BRN 기반 클러스터링
    │   └─ NICE Lookup fallback
    │
    └─[5] 교차 검증
        ├─ 구조화 scope_type vs LLM scope_type
        ├─ 구조화 tech_stack vs LLM tech_stack
        ├─ education.schoolType vs resume.finalEducationLevel (35.6% 불일치 로깅) [v13]
        └─ LinkedIn 교차 검증 (정책 확인 후)
```

### 추출 프롬프트 설계 원칙

1. **Taxonomy 제공 필수**: LLM에게 자유 생성을 허용하지 않고, 고정된 목록(SignalLabel, OutcomeType, ScopeType 등)에서 선택하도록 강제
2. **Evidence span 필수**: "근거 문장을 원문에서 인용하세요. 인용할 수 없으면 해당 항목을 생성하지 마세요."
3. **Confidence 자기 평가**: LLM에게 각 추출 항목의 확신도를 0.0~1.0으로 자가 평가하도록 요청하되, source ceiling으로 상한 제한
4. **분리 추출**: Experience별로 독립 추출 → 전체 커리어 수준 추출을 분리하여 context window 관리

---

## 6. v1 / v1.1 / v2 필드 로드맵

| 필드 | v1 | v1.1 | v2 |
|---|---|---|---|
| company, role_title, period | O | O | O |
| tech_stack (정규화) | O | 정규화 사전 확장 | O |
| scope_summary, scope_type | O | O | O |
| outcomes (Outcome[]) | O | O | 숫자 추출 강화 |
| situational_signals (14 labels) | O | O | taxonomy 확장 |
| failure_recovery | null 허용 | null 허용 | Closed-loop 질문 |
| past_company_context (NICE 현재) | O | 투자 DB 보강 | 시점 보정 |
| role_evolution | O | O | 세분화 |
| domain_depth | O | O | O |
| work_style_signals | **null 대부분** | null 대부분 | Closed-loop 질문 |
| LinkedIn 교차 검증 | 정책 확인 후 | O | O |
