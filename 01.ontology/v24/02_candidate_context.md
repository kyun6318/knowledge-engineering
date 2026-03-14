# CandidateContext

> 작성일: 2026-03-11
> 

---

## 0. 데이터 소스 현황

| Tier | 소스 | confidence 상한 | 현재 상태 | source_type enum |
| --- | --- | --- | --- | --- |
| T1 | 자사 이력서 | 0.85 | 접근 가능 | `self_resume` |
| T2 | 경력 기술서 | 0.85 | 접근 가능 (이력서에 포함되는 경우) | `career_desc` |
| T3 | LinkedIn 프로필 | 0.65 | 접근 정책 확인 필요 | `linkedin` |
| T4 | NICE 기업 정보 (PastCompanyContext 역산용) | 0.70 | 보유 | `nice` |
| T5 | Closed-loop 질문 응답 | 0.80 | v2 이후 | `enrichment_qa` |

> *T1(자사 이력서) 상한 0.85는 01_company_context의 T1(JD) 상한 0.80보다 높다. 이력서는 본인이 직접 작성하여 신뢰도를 높이고, JD는 채용 특성 상 과장 가능성이 있어 차등 적용
> 

### 교차 검증 규칙

- 자사 이력서 + LinkedIn 동시 존재 시: 같은 사람인지 여부 파악 가능성 확인(?)
    - 일치하는 claim -> `confidence = min(max(c1, c2) + 0.10, 0.90)`
    - 불일치하는 claim -> `confidence = min(c1, c2) * 0.5` + `contradiction: true`
- 자사 이력서만 존재 시: 단일 소스 confidence 그대로 사용

NEW_COMER(신입, 전체 서비스 풀의 30.9%)는 Career 데이터가 없거나 인턴/아르바이트 수준이어서, 본 문서에서 정의하는 Experience/Chapter 기반 구조화가 의미 있게 작동하지 않는다.

| 항목 | EXPERIENCED | NEW_COMER |
| --- | --- | --- |
| Experience/Chapter 분해 | 평균 ~5.6건 | 0~1건 (인턴/아르바이트) |
| SituationalSignal 추출 | 가능 (~65-70%) | **추출 불가** |
| RoleEvolution 추출 | 가능 (경력 2건 이상) | **추출 불가** (경력 1건 미만) |
| PastCompanyContext | 가능 (62% BRN 보유) | **없음** |
| Outcome 추출 | 가능 (~65%) | **거의 불가** |

`career_type = "NEW_COMER"` 이력서 **매칭 대상에서 제외**
CandidateContext 자체는 생성하되(Person 노드 기본 속성), MappingFeatures 대상에서 제외

**신입 매칭 로드맵**:

| 단계 | 매칭 전략 | 데이터 소스 |
| --- | --- | --- |
| v2.0 | Education-based matching: 전공-산업 연관도 (Tier 3 임베딩) | Education 테이블 (95.6% 커버리지) |
| v2.0 | Certificate matching: 자격증-직무 요구 매칭 | Certificate 테이블 (54% 커버리지) |
| v2.1 | 희망 직무 매칭: workcondition.jobClassificationCodes 기반 | WorkCondition (82.6% 활용 가능) |
| v2.2 | SelfIntroduction 텍스트 기반 잠재 역량 추출 | SelfIntroduction (64.1% 커버리지) |

---

## 1. 필드 정의 - 추출 난이도별 분류

### 1.1 Low Difficulty - 이력서에서 직접 추출

| 필드 | 타입 | 추출 방법 | 추출 난이도 | 설명 |
| --- | --- | --- | --- | --- |
| `company` | string | Rule + LLM | 낮음 | 재직 회사명 |
| `role_title` | string | Rule + LLM | 낮음 | 직무/직책명 |
| `period` | Period | Rule | 낮음 | 재직 기간 (시작~종료) |
| `tech_stack` | string[] | Rule + LLM | 낮음 | 사용 기술 스택 |
| `responsibilities` | string[] | LLM | 낮음 | 주요 업무 |

### 1.2 Medium Difficulty - 문맥 해석 필요

| 필드 | 타입 | 추출 방법 | 추출 난이도 | 설명 |
| --- | --- | --- | --- | --- |
| `scope_summary` | string | LLM | 중간 | 역할 범위 요약 (IC/Lead/Head 수준) |
| `outcomes` | Outcome[] | LLM | 중간 | 정량/정성 성과 목록 |
| `situational_signals` | string[] | LLM | 중간 | 경험한 상황 라벨 (taxonomy 기반) |
| `team_scale` | string | LLM | 중간 | 팀 규모/조직 맥락 |
| `role_evolution` | string | LLM (전체 experience 대상) | 중간 | 커리어 성장 패턴 |

### 1.3 High Difficulty - 추론 또는 외부 데이터 필요

| 필드 | 타입 | 추출 방법 | 추출 난이도 | v1 대응 |
| --- | --- | --- | --- | --- |
| `failure_recovery` | string | LLM | 높음 | null 허용 (후보가 기술하지 않는 경우 다수) |
| `work_style_signals` | WorkStyle | LLM | 높음 | 이력서 텍스트에 단서가 있을 때만 |
| `past_company_context` | PastCompanyCtx | NICE Lookup + LLM | 중간~높음 | NICE 현재 시점 데이터 기반 |
| `domain_depth` | string | LLM (전체 experience 대상) | 중간 | 회사/산업 반복 패턴 분석 |

---

## 2. 핵심 구조 상세 정의

### 2.1 Experience (경험 단위 = Chapter)

Chapter 개념과 GraphDB의 Chapter 노드 통합 구조

### Career 레코드 ↔ Chapter 매핑 원칙 [S-3]

**“resume-hub Career 레코드 1건 = 1 Chapter (Experience)”** 를 기본 원칙으로 한다.

| 케이스 | 처리 규칙 | 비고 |
| --- | --- | --- |
| 서로 다른 회사의 Career 레코드 | 각각 독립 Chapter | 표준 케이스 |
| **동일 회사**에서 Career 레코드 2건 이상 (직급/직무 변경) | **각각 독립 Chapter** | resume-hub Career 레코드 단위를 존중 |
| 동일 회사 연속 근무 시 NEXT_CHAPTER | `gap_months = 0`으로 설정 | 이직 공백이 아닌 내부 전환 표현 |

**동일 회사 연속 근무의 추가 처리**:
- `role_evolution` 추출 시, 같은 회사 내 Chapter 시퀀스를 **“동일 회사 내 성장(internal_growth)”** 으로 인식하여 IC_TO_LEAD 등 패턴 판정에 활용
- SituationalSignal 추출 시, 동일 회사의 전/후 Chapter를 함께 LLM에 전달하여 “직급 승진 전후의 맥락 변화”를 포착
- PastCompanyContext는 동일 회사 Chapter 간 **공유** (동일 Organization 노드를 가리킴)

> **구현 시 검증 필요**: 동일 회사에서 Career 레코드가 3건 이상인 사용자의 빈도를 Phase 2에서 확인하고, 과도한 Chapter 분할이 매칭 품질에 미치는 영향을 파일럿에서 모니터링한다.
> 

```tsx
interface Experience {
  // --- 직접 추출 (Low) ---
  experience_id: string;         // 자동 생성: {person_id}_ch{idx} 형식 (Pipeline/Data Contract 통일)
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

### ScopeType -> Seniority 변환 규칙

CandidateContext의 scope_type(IC/LEAD/HEAD/FOUNDER/UNKNOWN)과 CompanyContext vacancy의 seniority(JUNIOR/MID/SENIOR/LEAD/HEAD/UNKNOWN)는 서로 다른 체계를 사용한다. MappingFeatures의 role_fit 계산 시 아래 변환 규칙을 선행 적용한다.

**scope_type -> seniority 변환**:

| scope_type (Candidate) | 대응 seniority 범위 | 비고 |
| --- | --- | --- |
| IC | JUNIOR, MID, SENIOR | 경력 연수로 세분화 |
| LEAD | SENIOR, LEAD | Lead 경험자는 Senior 이상(저연치 lead 경험자는?) |
| HEAD | HEAD | 직접 대응 |
| FOUNDER | LEAD, HEAD | 경력 연수 기반 분기 |
| UNKNOWN | – | 매핑 불가, role_fit에서 경력 연수 기반 fallback |

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
    latest_exp = candidate_ctx.experiences[-1] if candidate_ctx.experiences else None  # [v24] 오름차순 정렬이므로 마지막이 최신 경력
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

> 이 함수는 `03_mapping_features.md` F5(role_fit)에서 참조
> 

### 2.2 Outcome (성과)

GraphDB의 Outcome 노드를 Evidence 통합 모델 정합

### Outcome v1 ROI 명시적 결정

| 항목 | 내용 |
| --- | --- |
| v1 LLM 비용 | ~$220 (L1, 전체 파이프라인 최대 비용 항목) |
| v1 MappingFeatures 활용 | **없음** - F1~F5에서 미사용 (v17 R-3, `03_mapping_features.md §2 F2 보충` 참조) |
| v1 활용 용도 | (1) 후보 프로필 표시, (2) Q3 그래프 탐색 (vector+graph 하이브리드), (3) v2 매칭 확장 기반 데이터 축적 |
| 비용 정당화 | Outcome 추출은 SituationalSignal 추출과 **동일 LLM 호출**에서 수행 (L1). Outcome만 제거해도 LLM 호출 자체는 줄지 않으므로 추가 비용이 미미. output token 감소분은 $3050 수준 |
| 대안 검토 | “v1에서 추출 안 함, v2에서 도입”은 v2 시점에 전량 재추출이 필요하여 오히려 비효율적 |

> **결론**: Outcome 추출의 한계 비용(추가 output token $3050)이 낮고, v2 활용을 위한 데이터 축적 가치가 있으므로 v1에서 추출한다. 단, **Outcome 노드의 Neo4j 적재는 v1 파일럿에서 선택적**으로 수행하여 그래프 복잡도를 관리할 수 있다.
> 

```tsx
interface Outcome {
  description: string;          // "MAU 10x 달성", "팀 4->18명 확장"
  outcome_type: OutcomeType;    // METRIC / SCALE / DELIVERY / ORGANIZATIONAL / OTHER
  quantitative: boolean;        // 정량적 수치 포함 여부
  metric_value: string | null;  // "10x", "4->18명" (있으면)
  confidence: number;           // 성과 claim의 신뢰도
  evidence: Evidence[];          // 근거 (이력서 원문 span)
}

type OutcomeType =
  | "METRIC"          // MAU, 매출, 전환율 등 수치 성과
  | "SCALE"           // 팀/조직/시스템 규모 확장
  | "DELIVERY"        // 제품/프로젝트 완료
  | "ORGANIZATIONAL"  // 팀 빌딩, 프로세스 구축
  | "OTHER";
```

### 2.3 SituationalSignal (상황 라벨)

Chapter의 “Experienced Trajectory / Verified Inflection”을 구현 가능하게 재정의.
**Taxonomy를 고정하여 LLM 추출의 일관성을 확보한다.**

```tsx
interface SituationalSignal {
  signal_label: SignalLabel;    // 고정 taxonomy
  description: string;          // 자유 서술
  confidence: number;
  evidence: Evidence;
}
```

**SignalLabel Taxonomy**:

| 카테고리 | label | 설명 | 이력서 탐지 패턴 |
| --- | --- | --- | --- |
| 성장 단계 | `EARLY_STAGE` | 초기 스타트업 경험 | “초기 멤버”, “n번째 직원”, “시드/엔젤” |
|  | `SCALE_UP` | 스케일업 경험 | “급성장”, “사용자 n배”, “팀 확장” |
|  | `TURNAROUND` | 턴어라운드/회생 | “피봇”, “방향 전환”, “구조조정 후” |
|  | `GLOBAL_EXPANSION` | 글로벌 확장 | “해외 진출”, “글로벌”, “다국적” |
| 조직 변화 | `TEAM_BUILDING` | 팀 신규 구성/빌딩 | “팀 구축”, “0->n명”, “채용” |
|  | `TEAM_SCALING` | 팀 규모 확대 | “n->m명”, “팀 확장”, “조직 성장” |
|  | `REORG` | 조직 개편 경험 | “조직 개편”, “스쿼드 전환”, “합병” |
| 기술 변화 | `LEGACY_MODERNIZATION` | 레거시 개선 | “리팩토링”, “마이그레이션”, “모놀리스->MSA” |
|  | `NEW_SYSTEM_BUILD` | 신규 시스템 구축 | “신규 구축”, “처음부터”, “0->1” |
|  | `TECH_STACK_TRANSITION` | 기술 스택 전환 | “전환”, “도입”, “migration” |
| 비즈니스 | `PMF_SEARCH` | PMF 탐색 | “PMF”, “제품-시장 적합성”, “가설 검증” |
|  | `MONETIZATION` | 수익화/비즈 모델 구축 | “수익화”, “BM”, “매출 n배” |
|  | `ENTERPRISE_TRANSITION` | B2C->B2B 또는 SMB->Enterprise | “엔터프라이즈”, “B2B 전환” |
| 기타 | `OTHER` | 위 카테고리 미해당 | - |

### 라벨 간 경계 가이드 [T-2]

경험 텍스트에서 복수 라벨이 해당될 수 있는 모호한 경우의 판정 기준:

| 모호한 조합 | 판정 기준 | 예시 |
| --- | --- | --- |
| `SCALE_UP` vs `TEAM_SCALING` | **조직 전체의 성장**이면 SCALE_UP, **특정 팀/부서 확대**이면 TEAM_SCALING | “회사가 급성장하며 직원 50->200명” -> SCALE_UP, “백엔드 팀 5->20명 확장” -> TEAM_SCALING |
| `NEW_SYSTEM_BUILD` vs `TECH_STACK_TRANSITION` | **기존 시스템 없이 새로 구축**이면 NEW_SYSTEM_BUILD, **기존 시스템에서 전환**이면 TECH_STACK_TRANSITION | “결제 시스템 0->1 구축” -> NEW_SYSTEM_BUILD, “모놀리스->MSA 전환” -> TECH_STACK_TRANSITION |
| `SCALE_UP` vs `EARLY_STAGE` | **급성장 결과에 초점**이면 SCALE_UP, **초기 불확실성/소규모에 초점**이면 EARLY_STAGE | “시리즈 B 이후 트래픽 10배” -> SCALE_UP, “3번째 직원으로 합류” -> EARLY_STAGE |
| `TEAM_BUILDING` vs `TEAM_SCALING` | **없던 팀을 새로 만듦**이면 TEAM_BUILDING, **기존 팀을 확대**이면 TEAM_SCALING | “데이터팀 신설 0->5명” -> TEAM_BUILDING, “기존 팀 5->20명” -> TEAM_SCALING |
| `TURNAROUND` vs `LEGACY_MODERNIZATION` | **사업/조직 방향 전환**이면 TURNAROUND, **기술/시스템 개선**이면 LEGACY_MODERNIZATION | “피봇 후 B2B 전환” -> TURNAROUND, “레거시 리팩토링” -> LEGACY_MODERNIZATION |

**복수 선택 규칙**: 하나의 경험에서 2개 이상의 signal이 명확한 근거와 함께 해당되면 **복수 선택을 허용**, 모호한 조합에서는 판정 기준에 따라 하나만 선택, 복수 선택 시 각 signal에 독립적인 confidence와 evidence를 부여한다.

### OTHER 비율 모니터링 기준 [T-1]

| 지표 | 기준 | 대응 |
| --- | --- | --- |
| OTHER 비율 (전체 추출 signal 중) | **30% 미만**: 정상 | taxonomy가 경험 유형을 충분히 포착 |
|  | **30~50%**: 주의 | 빈도 높은 OTHER 사례를 분석하여 신규 라벨 후보 식별 |
|  | **50% 초과**: 위험 | taxonomy 확장 필수 - OTHER 사례에서 반복 패턴 3개 이상 발견 시 v2 taxonomy에 추가 |

> **v1 파일럿에서 50건 매핑의 OTHER 비율을 측정**하고, 30% 초과 시 taxonomy 확장을 v1.1에서 검토
> 

> extract_signals() pseudo-code → 02.knowledge_graph/results/extraction_logic/v17/03_prompt_design.md 참조

### 2.4 PastCompanyContext (v1)

v1: **현재 시점 NICE 데이터**만 사용.

```tsx
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

// [v22] PastCompanyContext confidence 계산 규칙:
// confidence = source_ceiling × temporal_decay
// - source_ceiling: NICE 소스 0.70 (01_company_context.md §1 T2)
// - temporal_decay: 현재 시점 NICE 데이터로 과거 stage를 추정하므로 감쇠 적용
//   재직 기간과 현재 시점의 차이(years_since_tenure)에 따라:
//   - 0~3년: decay = 0.90 (최근 데이터, 신뢰 가능)
//   - 3~7년: decay = 0.75 (직원수/매출 변동 가능)
//   - 7~15년: decay = 0.55 (상당한 변동 가능)
//   - 15년+: decay = 0.40 (데이터 유효성 낮음)
// 예시: NICE ceiling 0.70 × temporal_decay 0.63(5년 전 재직) = 0.44
```

> build_past_company_context() pseudo-code → 02.knowledge_graph/results/extraction_logic/v17/03_prompt_design.md 참조

### 2.5 WorkStyleSignals

```tsx
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

이력서에서 work_style_signals를 추출할 수 있는 경우는 **20~30% 미만**으로 예상. 대부분 null이 될 것이며, 이는 정상 상태로 처리.

### 2.6 Person 보강 속성

`00_data_source_mapping.md §3.5`를 참조.

| 속성 | 타입 | fill rate | 용도 | 주의사항 |
| --- | --- | --- | --- | --- |
| `name` | string | ~100% | Person 식별 (Graph 노드 표시용) | **소스: `profile.name`** (resume-hub). 매칭 점수에 사용 금지 [v15 X-2] |
| `gender` | string | null | 100% | 매칭 편향 모니터링 전용 | **매칭 점수에 사용 금지** |
| `age` | int | null | 93.3% | 세그먼트 분석 보조 | 1~100 필터, age>100 이상치 제거 |
| `career_type` | string | 100% | 경력/신입 세그먼트 | EXPERIENCED 69.1% / NEW_COMER 30.9% |
| `freshness_weight` | float | 100% | 데이터 신선도 가중치 | 90일 이내 1.0, 5년+ 0.3 |
| `education_level` | string | null | 95.6% | 학력 필터링 | **education.schoolType을 진실 소스** (finalEducationLevel 35.6% 불일치) |

> `04_graph_schema.md`의 Person 노드에도 반영 (C-1).
`name` 필드는 04_graph_schema Person 노드에 `name: STRING`와 매칭
> 

### 2.7 CareerDescription FK 부재 제약 [00_data_source_mapping §3.2 D4 인라인]

> **핵심 제약**: CareerDescription 테이블에 `career_id` FK가 없다. resume_id로만 연결되므로, 복수 경력이 있는 이력서에서 어떤 경력에 대한 기술인지 career 단위 매핑이 불가능하다.
> 

**처리 전략**:
1. CareerDescription.description 전문을 가져온다 (fill rate 16.9%, 중앙값 527자)
2. 해당 resume의 Career[] 목록을 함께 LLM에 전달한다
3. LLM이 텍스트 컨텍스트로 각 career에 outcome을 귀속한다
4. 귀속 불가 시 resume 전체에 귀속 (confidence 하향)
5. CareerDescription 미보유 시 SelfIntroduction fallback (fill rate 64.1%, 중앙값 1,320자)

> **짧은 텍스트 대응**: workDetails 중앙값 96자로, 50자 미만인 경우 LLM 추출 품질이 저하된다.
- 50자 미만 workDetails: scope_summary 추출만 시도, outcomes/situational_signals는 스킵 (confidence 부족)
- 50~100자 workDetails: 추출 시도하되 confidence에 0.8 감쇠 적용
- 100자 이상: 정상 추출
> 

### 2.8 RoleEvolution (전체 커리어 수준)

```tsx
interface RoleEvolution {
  pattern: RolePattern;        // IC_TO_LEAD / IC_DEPTH / LEAD_TO_HEAD / etc.
  description: string;         // "IC -> Lead -> Head, 일관된 상향 이동"
  total_experience_years: number;
  confidence: number;
  evidence: Evidence[];        // 패턴 판단 근거 (여러 experience 걸침)
}

type RolePattern =
  | "IC_TO_LEAD"          // IC -> Lead 성장
  | "IC_DEPTH"            // IC 전문성 심화
  | "LEAD_TO_HEAD"        // Lead -> Head/Director 성장
  | "FOUNDER"             // 창업 경험
  | "GENERALIST"          // 다양한 역할 전환
  | "DOWNSHIFT"           // 상위 -> 하위 역할 이동
  | "LATERAL"             // 동급 역할 간 이동
  | "UNKNOWN";
```

> **[v24] 전제 조건**: Career[] 배열은 `period.start` 기준 **오름차순** (과거 -> 최근)으로 정렬되어야 한다. resume-hub에서 조회 시 `ORDER BY period.started_on ASC`를 적용한다. 시간순이 보장되지 않으면 role_evolution 추출이 부정확해질 수 있다.
> 

> extract_role_evolution() pseudo-code → 02.knowledge_graph/results/extraction_logic/v17/03_prompt_design.md 참조

### 2.9 Context 재생성 조건

> §2.9 재생성 조건 → 03.graphrag/results/implement_planning/separate/v7/shared/regeneration_policy.md로 이동

---

## 3. CandidateContext JSON 스키마

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
      "experience_id": "P_99999_ch0",
      "company": "A사",
      "role_title": "Engineering Lead",
      "period": {
        "start": "2021-03",
        "end": "2023-06",
        "duration_months": 27
      },
      "tech_stack": ["Python", "FastAPI", "PostgreSQL", "AWS"],
      "responsibilities": [
        "결제 시스템 전체 아키텍처 설계 및 운영",
        "백엔드 팀 채용/온보딩/기술 리딩",
        "대용량 트래픽 처리를 위한 인프라 최적화"
      ],
      "scope_summary": "백엔드 팀 4->18명 확장, 결제 시스템 아키텍처 전체 총괄",
      "scope_type": "LEAD",

      "outcomes": [
        {
          "description": "MAU 10x 달성",
          "outcome_type": "METRIC",
          "quantitative": true,
          "metric_value": "10x",
          "confidence": 0.75,
          "evidence": [{
            "source_id": "resume_001",
            "source_type": "self_resume",
            "span": "2년간 MAU를 50만에서 500만으로 성장시킴",
            "confidence": 0.75,
            "extracted_at": "2026-03-08T10:00:00Z"
          }]
        },
        {
          "description": "팀 4->18명 확장",
          "outcome_type": "SCALE",
          "quantitative": true,
          "metric_value": "4->18명",
          "confidence": 0.80,
          "evidence": [{
            "source_id": "resume_001",
            "source_type": "self_resume",
            "span": "백엔드 팀을 4명에서 18명으로 확장, 채용/온보딩 주도",
            "confidence": 0.80,
            "extracted_at": "2026-03-08T10:00:00Z"
          }]
        }
      ],

      "situational_signals": [
        {
          "signal_label": "SCALE_UP",
          "description": "Series A->B 전환기의 급성장 경험",
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
          "description": "팀 4->18명 스케일링 경험",
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
        "industry_code": "SW_DEV",
        "industry_label": "소프트웨어 개발업",
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
    "description": "Junior Engineer -> Senior -> Lead, 일관된 기술 리더십 성장",
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

> **[v24] JSON 스키마 버전 규약**: `$schema`의 `_v4`는 JSON 스키마 자체의 메이저 버전이며, 온톨로지 디렉토리 버전(v24)과 독립적이다. 스키마 구조(필드 추가/삭제/타입 변경)가 변경될 때만 증가한다. `_meta.context_version`은 동일 스키마에서의 마이너 버전 추적에 사용한다.

---

## 4. GraphDB 엔티티 구조 통합

> §4 GraphDB 엔티티 매핑 → 04_graph_schema.md §1-§2에 통합. Neo4j 구현 상세는 03.graphrag/results/implement_planning/separate/v7/graphrag/07_neo4j_schema.md 참조.

---

## 5. 추출 파이프라인 개요

> §5 추출 파이프라인 → 02.knowledge_graph/results/extraction_logic/v17/01_extraction_pipeline.md 참조.