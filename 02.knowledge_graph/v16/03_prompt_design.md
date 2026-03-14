> 작성일: 2026-03-11
> 

---

## 0. 프롬프트 설계 원칙

1. **Taxonomy Enforcement**: 고정 열거형 목록을 항상 제공, 자유 형식 생성 불가
2. **Evidence Span**: “원문에서 근거를 인용하라. 근거가 없으면 생성하지 마라”
3. **Self-Confidence**: LLM이 confidence(0.0-1.0) 추정 -> 소스 신뢰 상한 적용
4. **Ambiguity Rules**: 중복 가능 라벨 간 명시적 판단 기준 포함
5. **구조화 필드 사전 주입**: DB에서 확보 가능한 필드를 힌트로 제공하여 토큰 절감

---

## 1. CompanyContext 추출 프롬프트

### 1.1 System Prompt

```
You are a hiring context analyst. You extract structured hiring information from Korean job descriptions.

RULES:
- Output ONLY valid JSON matching the schema below
- Use Korean for description fields, English for enum values
- If information is not present in the text, use null (do not guess)
- Provide evidence spans from the original text
- Estimate confidence (0.0-1.0) for each field
- If the hiring context is ambiguous or cannot be determined, use "UNKNOWN" with confidence < 0.3
```

### 1.2 User Prompt Template

```
아래는 채용공고(JD)입니다. 구조화 정보와 함께 분석해주세요.

## 사전 확보 정보 (DB 기반, 참고용)
- 회사명: {company_name}
- 산업: {industry}
- 직무: {designation}
- 기술스택: {tech_stack_list}
- 인원 규모: {employee_count} (NICE)
- 설립연도: {founded_year} (NICE)

## JD 본문
{overview_descriptions}

## 요구사항
{requirement_text}

## 출력 JSON 스키마
{company_context_schema}

위 스키마에 맞춰 JSON으로 응답하세요.
```

### 1.3 출력 JSON 스키마 (Pydantic v2)

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum

class HiringContext(str, Enum):
    BUILD_NEW = "BUILD_NEW"           # 신규 구축, 0->1, greenfield
    SCALE_EXISTING = "SCALE_EXISTING" # 확장, 스케일, 고도화
    RESET = "RESET"                   # 개선, 리팩토링, 재설계, migration
    REPLACE = "REPLACE"               # 충원, 결원, 대체
    UNKNOWN = "UNKNOWN"

class OperatingModelFacets(BaseModel):
    speed: Optional[float] = Field(None, ge=0.0, le=1.0, description="Fast iteration (스프린트, 애자일, 빠르게)")
    autonomy: Optional[float] = Field(None, ge=0.0, le=1.0, description="Ownership (오너십, 주도, 자율)")
    process: Optional[float] = Field(None, ge=0.0, le=1.0, description="Rigor (OKR, code review, CI/CD)")
# [v16] operating_model 타입 정본: float(0.0~1.0)
# Data Contract(03.graphrag)에서도 float로 전달한다.
# 이산형 변환이 필요한 경우 서빙 레이어에서 변환:
#   HIGH: >= 0.7, MID: 0.3~0.7, LOW: < 0.3

# Phase 5에서 활성화 시 아래 주석을 해제하여 복원.
#
# class StructuralTension(str, Enum):
#     TECH_DEBT_VS_FEATURES = "tech_debt_vs_features"
#     SPEED_VS_RELIABILITY = "speed_vs_reliability"
#     FOUNDER_VS_PROFESSIONAL_MGMT = "founder_vs_professional_mgmt"
#     EFFICIENCY_VS_GROWTH = "efficiency_vs_growth"
#     SCALING_LEADERSHIP = "scaling_leadership"
#     INTEGRATION_TENSION = "integration_tension"
#     BUILD_VS_BUY = "build_vs_buy"
#     PORTFOLIO_RESTRUCTURING = "portfolio_restructuring"

class CompanyContextExtraction(BaseModel):
    hiring_context: HiringContext
    hiring_context_evidence: Optional[str] = Field(None, description="JD 원문 근거 (50자 이내)")
    hiring_context_confidence: float = Field(ge=0.0, le=1.0)

    scope_description: Optional[str] = Field(None, description="채용 맥락 요약 (100자 이내)")

    role_expectations: Optional[str] = Field(None, description="역할 기대치 요약 (100자 이내)")

    operating_model: Optional[OperatingModelFacets] = None
    operating_model_evidence: Optional[list[str]] = Field(None, description="각 facet 근거 키워드")

    # [v16] Vacancy seniority 추출 (H3)
    seniority: Optional[Literal["JUNIOR", "SENIOR", "LEAD", "HEAD", "C_LEVEL"]] = Field(
        None, description="채용 포지션의 시니어리티 수준. designation 코드 또는 JD 본문에서 추출")
    seniority_confidence: float = Field(0.5, ge=0.0, le=1.0,
        description="designation 기반 추론 시 상한 0.65 적용")

    # Phase 5 복원 시:
    # structural_tensions: Optional[list[StructuralTension]] = Field(None)
    # structural_tension_evidence: Optional[str] = None
```

### 1.4 hiring_context 분류 가이드라인

| 값 | 판단 기준 | 한국어 키워드 | 영어 키워드 |
| --- | --- | --- | --- |
| BUILD_NEW | 새로운 팀/제품/시스템을 처음부터 구축 | “신규 구축”, “처음부터”, “새로운 팀”, “0->1” | “new team”, “greenfield”, “build from scratch” |
| SCALE_EXISTING | 기존 시스템/조직의 확장, 고도화 | “확장”, “스케일”, “고도화”, “성장” | “scale”, “grow”, “expand” |
| RESET | 기존 시스템/프로세스의 개선, 재설계 | “개선”, “리팩토링”, “재설계”, “마이그레이션” | “refactor”, “redesign”, “migration” |
| REPLACE | 기존 인원의 충원, 대체 | “충원”, “결원”, “대체”, “후임” | “backfill”, “replacement” |
| UNKNOWN | 판단 근거 불충분 | - | - |

**모호 케이스 판단 규칙**:
- BUILD_NEW vs SCALE_EXISTING: 팀이 0명에서 시작 -> BUILD_NEW; 기존 팀에 인원 추가 -> SCALE_EXISTING
- SCALE_EXISTING vs RESET: 현행 유지+확장 -> SCALE; 현행 불만족+변경 -> RESET
- 다수 해석 가능 시 **더 높은 신호(BUILD>SCALE>RESET>REPLACE)**를 선택하고 confidence를 낮춤

### 1.5 operating_model 추출 규칙

각 facet에 대해:
1. 키워드 수 카운트
2. `min(count / 5, 1.0)` 적용
3. confidence = `min(0.60, 0.30 + count × 0.06)` (JD 단일 소스 상한 0.60)
4. **구체적 맥락 부재 시 null 처리** (v12 C3 - 진정성 체크 단순화):
- 키워드가 구체적 맥락(스프린트 주기, 리뷰 빈도, 도구명 등) 없이 단독 사용 시 -> 해당 facet **null**
- 예: “애자일 팀”만 단독 사용 (스프린트 주기 미언급) -> speed = null
- 예: “2주 스프린트로 빠르게 배포” -> speed = 0.8 (구체적 맥락 있음)

> v11에서의 “LLM 진정성 체크”를 단순 규칙으로 대체. LLM에 “광고성 vs 실제” 판단을 요구하는 것은
JD 본문만으로는 사실상 불가능하므로, 구체적 맥락 유무만으로 판단.
> 

### 1.6 Few-shot 예시 (CompanyContext)

**예시 1: BUILD_NEW**

```json
{
  "hiring_context": "BUILD_NEW",
  "hiring_context_evidence": "새로운 AI 플랫폼을 처음부터 구축할 엔지니어를 찾습니다",
  "hiring_context_confidence": 0.85,
  "scope_description": "AI 플랫폼 신규 구축, 0->1 단계",
  "role_expectations": "AI 플랫폼 아키텍처 설계부터 MVP 구현까지 리드",
  "operating_model": {
    "speed": 0.8,
    "autonomy": 0.6,
    "process": null
  },
  "operating_model_evidence": ["2주 스프린트", "빠른 실험", "오너십"]
}
```

**예시 2: SCALE_EXISTING**

```json
{
  "hiring_context": "SCALE_EXISTING",
  "hiring_context_evidence": "급성장하는 서비스의 백엔드 시스템을 확장",
  "hiring_context_confidence": 0.80,
  "scope_description": "MAU 100만 서비스의 백엔드 스케일업",
  "role_expectations": "대규모 트래픽 처리 및 시스템 안정화",
  "operating_model": {
    "speed": 0.4,
    "autonomy": 0.4,
    "process": 0.6
  },
  "operating_model_evidence": ["코드 리뷰 필수", "CI/CD 파이프라인"]
}
```

---

## 2. CandidateContext 추출 프롬프트

### 2.1 System Prompt

```
You are a career analyst. You extract structured career information from Korean resumes.

RULES:
- Output ONLY valid JSON matching the schema below
- Analyze each career (chapter) independently
- Use Korean for description/evidence fields, English for enum values
- If information is not present in the text, use null or empty array
- Cite evidence from original text. If no evidence, do not generate the item
- Estimate confidence (0.0-1.0) for each field
```

### 2.2 User Prompt Template (호출 전략별 분기)

### 2.2.1 1-pass 프롬프트 (Career 1~3)

```
아래는 후보자의 경력 정보입니다. Career별로 분석하고, 전체 이력 요약도 포함해주세요.

## 사전 확보 정보 (DB 기반, 참고용)
- 직급 코드: {position_grade_code} (null이면 없음)
- 직책 코드: {position_title_code} (null이면 없음)
- 재직 기간: {period_start} ~ {period_end}
- 회사명: {company_name}
- 회사 규모: {employee_count} (NICE, null이면 미확인)

## Career 상세 (workDetails)
{work_details}

## 경력 기술서 (CareerDescription)
{career_description}

## 자기소개서 (SelfIntroduction)
{self_introduction}

## 출력 JSON 스키마
{candidate_context_schema_full}

위 스키마에 맞춰 JSON으로 응답하세요.
```

### 2.2.2 N+1 pass 프롬프트 - Career별 (Career 4+, Pass 1~N)

```
아래는 후보자의 특정 경력(Career) 정보입니다. 이 경력만 분석해주세요.

## 사전 확보 정보 (DB 기반, 참고용)
- 직급 코드: {position_grade_code}
- 재직 기간: {period_start} ~ {period_end}
- 회사명: {company_name}
- 회사 규모: {employee_count}

## Career 상세 (workDetails)
{work_details_single}

## 경력 기술서 (CareerDescription, 해당 Career만)
{career_description_single}

## 출력 JSON 스키마
{chapter_extraction_schema}

위 스키마에 맞춰 JSON으로 응답하세요.
```

### 2.2.3 N+1 pass 프롬프트 - 전체 요약 (Career 4+, Pass N+1)

```
아래는 후보자의 전체 경력 요약입니다. 역할 성장 패턴과 도메인 경험 깊이를 분석해주세요.

## 경력 요약
{career_summary_list}
(형식: "회사명 | 기간 | scope_type | 주요 시그널")

## 출력 JSON 스키마
{summary_schema}

위 스키마에 맞춰 JSON으로 응답하세요.
```

### 2.3 출력 JSON 스키마 (Pydantic v2)

```python
class ScopeType(str, Enum):
    IC = "IC"           # Individual Contributor
    LEAD = "LEAD"       # 팀 리드 (3-10명)
    HEAD = "HEAD"       # 부서/본부장
    FOUNDER = "FOUNDER" # 창업자/공동창업자
    UNKNOWN = "UNKNOWN"

class OutcomeType(str, Enum):
    METRIC = "METRIC"               # 수치 기반 성과 (MAU, 매출, 전환율)
    SCALE = "SCALE"                 # 규모 확장 (팀, 시스템, 사용자)
    DELIVERY = "DELIVERY"           # 프로젝트 완수 (런칭, 구축, 도입)
    ORGANIZATIONAL = "ORGANIZATIONAL" # 조직 기여 (프로세스, 문화, 교육)
    OTHER = "OTHER"

class SignalLabel(str, Enum):
    # Growth
    EARLY_STAGE = "EARLY_STAGE"
    SCALE_UP = "SCALE_UP"
    TURNAROUND = "TURNAROUND"
    GLOBAL_EXPANSION = "GLOBAL_EXPANSION"
    # Org Change
    TEAM_BUILDING = "TEAM_BUILDING"
    TEAM_SCALING = "TEAM_SCALING"
    REORG = "REORG"
    # Tech
    LEGACY_MODERNIZATION = "LEGACY_MODERNIZATION"
    NEW_SYSTEM_BUILD = "NEW_SYSTEM_BUILD"
    TECH_STACK_TRANSITION = "TECH_STACK_TRANSITION"
    # Business
    PMF_SEARCH = "PMF_SEARCH"
    MONETIZATION = "MONETIZATION"
    ENTERPRISE_TRANSITION = "ENTERPRISE_TRANSITION"
    # Other
    OTHER = "OTHER"

class Outcome(BaseModel):
    description: str = Field(description="성과 요약 (50자 이내)")
    outcome_type: OutcomeType
    quantitative: bool = Field(description="수치 포함 여부")
    metric_value: Optional[str] = Field(None, description="수치 (예: '10x', '4->18명')")
    evidence: str = Field(description="원문 근거 (100자 이내)")
    confidence: float = Field(ge=0.0, le=1.0)

class SituationalSignal(BaseModel):
    label: SignalLabel
    evidence: str = Field(description="원문 근거 (50자 이내)")
    confidence: float = Field(ge=0.0, le=1.0)

class ChapterExtraction(BaseModel):
    scope_type: ScopeType
    scope_type_evidence: Optional[str] = Field(None, description="판단 근거 (50자 이내)")
    scope_type_confidence: float = Field(ge=0.0, le=1.0)

    outcomes: list[Outcome] = Field(default_factory=list, max_length=5)
    situational_signals: list[SituationalSignal] = Field(default_factory=list, max_length=5)

class CandidateContextExtraction(BaseModel):
    """1-pass 호출 시 전체 출력 스키마"""
    chapters: list[ChapterExtraction] = Field(description="Career별 추출 결과")
    role_evolution: Optional[str] = Field(None, description="전체 이력 기반 역할 성장 패턴 (100자 이내)")
    domain_depth: Optional[str] = Field(None, description="도메인 경험 깊이 (50자 이내)")
    # v12 S5: work_style_signals 제거 (v1 INACTIVE)
    # Phase 5 복원 시:
    # work_style_signals: Optional[list[str]] = Field(None, description="업무 스타일 키워드")

class CareerSummaryExtraction(BaseModel):
    """N+1 pass의 N+1번째 호출 시 출력 스키마"""
    role_evolution: Optional[str] = Field(None, description="전체 이력 기반 역할 성장 패턴 (100자 이내)")
    domain_depth: Optional[str] = Field(None, description="도메인 경험 깊이 (50자 이내)")
```

### 2.4 scope_type 분류 가이드라인

| 값 | 판단 기준 | 힌트 (positionGradeCode) |
| --- | --- | --- |
| IC | 개인 기여자, 팀원, 실무자 | 사원, 주임, 대리, 과장 (하위) |
| LEAD | 팀 리드, 3-10명 관리 | 과장 (상위), 차장 |
| HEAD | 부서장, 본부장, 10명+ 관리 | 부장, 이사 |
| FOUNDER | 창업자, 공동창업자, 대표 | 대표이사, CEO |
| UNKNOWN | 판단 불가 | null |

**A1 매핑** (scope_type -> Seniority 변환):
- IC -> JUNIOR/MID (경력 연차 기반)
- LEAD -> SENIOR/LEAD
- HEAD -> HEAD
- FOUNDER -> LEAD / HEAD (경력 연수 기반, 02_candidate_context.md §2.1 ScopeType→Seniority 변환 참조) [v15]

**규칙**:
1. positionGradeCode가 있으면 **힌트로만** 사용 (LLM이 workDetails로 최종 판단)
2. “팀장”이라고 해도 1인 팀이면 IC
3. “CTO”라도 스타트업 5인 이하면 LEAD (규모 고려)

### 2.5 outcomes 추출 가이드라인

| 유형 | 한국어 패턴 | 예시 |
| --- | --- | --- |
| METRIC | 수치+동사 (달성, 향상, 증가, 감소) | “전환율 30% 향상”, “MAU 10만 달성” |
| SCALE | 규모 변화 (N->M, 확장) | “팀 4->18명 확장”, “서버 3대->30대” |
| DELIVERY | 프로젝트 완수 (런칭, 구축, 도입, 출시) | “결제 시스템 신규 구축”, “v2.0 출시” |
| ORGANIZATIONAL | 조직/프로세스 (도입, 교육, 문화) | “코드 리뷰 문화 정착”, “신입 온보딩 체계 구축” |
| OTHER | 위 4개에 해당하지 않는 성과 | “기술 블로그 운영” |

**규칙**:
1. 원문에 **명시적 근거**가 있어야 추출 (추측 금지)
2. quantitative=true는 구체적 수치가 있을 때만
3. 최대 5개, 중요도 순 정렬
4. confidence 상한: 0.85 (self_resume 소스)

### 2.6 situational_signals 분류 가이드라인

| 라벨 | 판단 패턴 | 모호 케이스 규칙 |
| --- | --- | --- |
| EARLY_STAGE | “초기 멤버”, “n번째 직원”, 10인 이하 | vs SCALE_UP: 초기 불확실성 -> EARLY; 성장 결과 -> SCALE_UP |
| SCALE_UP | “급성장”, “사용자 n배”, MAU 폭증 | vs TEAM_SCALING: 회사 전체 성장 -> SCALE_UP; 특정 팀 -> TEAM_SCALING |
| TURNAROUND | “피봇”, “방향 전환”, 위기 극복 |  |
| GLOBAL_EXPANSION | “해외 진출”, “글로벌”, 다국적 |  |
| TEAM_BUILDING | “팀 구축”, “0->n명”, 채용 주도 | vs TEAM_SCALING: 0명에서 시작 -> BUILDING; 기존 팀 확장 -> SCALING |
| TEAM_SCALING | “n->m명”, “팀 확장” (기존 팀) |  |
| REORG | “조직 개편”, “합병”, 구조 변경 |  |
| LEGACY_MODERNIZATION | “리팩토링”, “마이그레이션”, 레거시 | vs NEW_SYSTEM_BUILD: 기존 시스템 -> LEGACY; 없던 시스템 -> NEW |
| NEW_SYSTEM_BUILD | “신규 구축”, “0->1”, 처음부터 | vs TECH_STACK_TRANSITION: 처음 구축 -> NEW; 기존 전환 -> TRANSITION |
| TECH_STACK_TRANSITION | “전환”, “도입”, 기술 변경 |  |
| PMF_SEARCH | “PMF”, “제품-시장 적합성” |  |
| MONETIZATION | “수익화”, “BM”, 매출 모델 |  |
| ENTERPRISE_TRANSITION | “B2C->B2B”, “엔터프라이즈” |  |
| OTHER | 위 13개에 해당 없음 | **OTHER > 30%면 택소노미 확장 검토** |

**규칙**:
1. 동일 Chapter에서 **최대 3개** 시그널 (핵심만)
2. 원문 근거 필수
3. confidence 상한: 0.85 (self_resume 소스)

### 2.7 Few-shot 예시 (CandidateContext)

**예시 1: IC + SCALE_UP**

```json
{
  "chapters": [
    {
      "scope_type": "IC",
      "scope_type_evidence": "백엔드 개발자로 API 개발 담당",
      "scope_type_confidence": 0.80,
      "outcomes": [
        {
          "description": "API 응답 시간 50% 개선",
          "outcome_type": "METRIC",
          "quantitative": true,
          "metric_value": "50%",
          "evidence": "캐싱 도입으로 평균 응답 시간 200ms -> 100ms 달성",
          "confidence": 0.85
        }
      ],
      "situational_signals": [
        {
          "label": "SCALE_UP",
          "evidence": "MAU 10만에서 100만으로 급성장하는 시기",
          "confidence": 0.80
        }
      ]
    }
  ],
  "role_evolution": "IC 개발자로 시작, 점진적으로 기술 리드 역할 확대",
  "domain_depth": "핀테크 결제 도메인 4년 집중"
}
```

**예시 2: LEAD + TEAM_BUILDING**

```json
{
  "chapters": [
    {
      "scope_type": "LEAD",
      "scope_type_evidence": "백엔드 팀 리드로 5명 관리",
      "scope_type_confidence": 0.85,
      "outcomes": [
        {
          "description": "백엔드 팀 0->5명 구축",
          "outcome_type": "SCALE",
          "quantitative": true,
          "metric_value": "0->5명",
          "evidence": "채용부터 온보딩까지 백엔드 팀 구축 주도",
          "confidence": 0.80
        },
        {
          "description": "결제 시스템 v2 런칭",
          "outcome_type": "DELIVERY",
          "quantitative": false,
          "metric_value": null,
          "evidence": "3개월 만에 결제 시스템 전면 재설계 완료",
          "confidence": 0.75
        }
      ],
      "situational_signals": [
        {
          "label": "TEAM_BUILDING",
          "evidence": "백엔드 팀이 없는 상태에서 5명 팀 구축",
          "confidence": 0.85
        },
        {
          "label": "LEGACY_MODERNIZATION",
          "evidence": "레거시 결제 시스템을 MSA로 전면 재설계",
          "confidence": 0.75
        }
      ]
    }
  ],
  "role_evolution": "IC -> 팀 리드, 기술 의사결정 + 채용 역할 확대",
  "domain_depth": "이커머스/결제 도메인 6년"
}
```

---

## 3. LLM 파라미터

| 파라미터 | CompanyContext | CandidateContext (1-pass) | CandidateContext (N+1: Career별) | CandidateContext (N+1: 요약) | 비고 |
| --- | --- | --- | --- | --- | --- |
| model | claude-haiku-4-5 | claude-haiku-4-5 | claude-haiku-4-5 | claude-haiku-4-5 | Phase 0 검증 후 확정 |
| temperature | 0.3 | 0.3 | 0.3 | 0.3 | 재시도 시 0.5 |
| max_tokens | 1,024 | 2,048 | 1,024 | 512 | Career 수에 따라 분기 |
| response_format | json | json | json | json | Pydantic 검증 |
| batch_mode | true | true | true | true | 50% 비용 절감 |

---

## 4. Confidence 캘리브레이션

### 4.1 소스별 신뢰 상한

| 소스 | 상한 | 적용 대상 |
| --- | --- | --- |
| self_resume | **0.85** | CandidateContext 전체 |
| jd_internal | **0.80** | CompanyContext 전체 |
| NICE | 0.70 | stage_estimate |
| 크롤링 (T3) | 0.60 | CompanyContext 보강 (Phase 4) |
| 뉴스 (T4) | 0.55 | CompanyContext 보강 (Phase 4) |

### 4.2 캘리브레이션 규칙

```python
def calibrate_confidence(llm_confidence: float, source_ceiling: float) -> float:
    """LLM이 추정한 confidence에 소스 상한 적용"""
    return min(llm_confidence, source_ceiling)
```

### 4.3 신뢰도 등급

| 등급 | 범위 | 의미 |
| --- | --- | --- |
| High | 0.80-1.00 | 팩트 수준 (다중 소스 교차 검증) |
| Medium | 0.60-0.79 | 단일 신뢰 소스, 명시적 추출 |
| Low | 0.40-0.59 | 단일 소스, 추론 필요 |
| Very Low | 0.20-0.39 | 약한 신호, 간접 추론 |
| Unreliable | <0.19 | 추측, 주의 필요 |

---

## 5. 프롬프트 버전 관리

| 항목 | 전략 |
| --- | --- |
| 저장 | Git (prompts/ 디렉토리) |
| 버전 형식 | v{major}.{minor} (예: v1.0, v1.1) |
| 회귀 테스트 | 50건 Golden Set, <5% 품질 차이 |
| 메타데이터 | 추출 결과에 prompt_version 기록 |

**업데이트 절차**:
1. prompts/ 디렉토리에 새 버전 작성
2. 50건 Golden Set 회귀 테스트 실행
3. 품질 차이 <5% 확인
4. git commit + PR 리뷰
5. 배포 (Cloud Run Job 이미지 업데이트)
6. 증분 파이프라인에서 자동 적용