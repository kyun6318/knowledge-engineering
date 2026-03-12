# CompanyContext

> 작성일: 2026-03-10
> 

---

## 0. 설계 원칙

| 원칙 |  |
| --- | --- |
| 독립성 | 후보와 무관하게 생성 |
| Evidence-first | 모든 claim에 근거 필수 |
| 부분 완성 | missing_fields 명시 |
| **데이터 소스 계층화** | 필드 별 데이터 소스 Tier를 명시하고, Tier에 따라 confidence 상한을 제한 |
| **추출 방법 명시** | 각 필드의 추출 방식(LLM / Rule / Lookup)을 정의 |
| **Unknown 정상화** | v1에서 Unknown 비율이 높은 필드를 명시적으로 허용 |
| **의도적 제외 명문화** | 현 버전에서 의도적으로 제외한 기능/필드를 명시하고, 제외 이유와 도입 로드맵을 문서화 |

---

## 1. 데이터 소스 Tier 정의

각 소스에 **confidence 상한(ceiling)**을 부여한다. 해당 소스만으로 추출된 claim은 이 상한을 초과할 수 없다.

| Tier | 소스 | confidence 상한 | 현재 상태 | source_type enum |
| --- | --- | --- | --- | --- |
| T1 | JD (자사 보유 / 크롤링) | 0.80 | 자사 보유분 접근 가능, 외부는 크롤링 필요 | `jd_internal`, `jd_crawled` |
| T2 | NICE 기업 정보 | 0.70 | 보유 | `nice` |
| T3 | 회사 홈페이지 크롤링 | 0.60 | 미구축 (크롤러 필요) | `crawl_site` |
| T4 | 뉴스 / 기사 크롤링 | 0.55 (카테고리 별 예외, 아래 참조) | 미구축 | `crawl_news` |
| T5 | 투자 정보 DB (더브이씨, 크런치베이스 등) | 0.75 | 미구축 (API 연동 필요) | `invest_db` |

### confidence 상한 적용 규칙

```
field_confidence = min(extraction_confidence, source_ceiling)
```

- 복수 소스가 동일 claim을 지지하면: `boosted = min(max(c1, c2) + 0.10, 0.95)`
- 복수 소스가 모순되면: `field_confidence = min(c1, c2) * 0.5`, `contradiction=true` 표기

### T4 Tier ceiling 예외 규칙

T4(뉴스/기사)의 base ceiling 0.55에 대해 카테고리 별 예외 허용

| 카테고리 | 예외 ceiling | 적용 조건 | 근거 |
| --- | --- | --- | --- |
| funding | 0.65 | 투자 금액 + 투자사명이 동시에 추출된 경우에만 적용 | 두 팩트가 교차 검증 가능하므로 높은 신뢰도 인정 |
| performance | 0.60 | 구체적 수치(매출, MAU, 거래액 등)가 포함된 경우에만 적용 | 정량 데이터는 정성 추론보다 검증 가능성이 높음 |

> 본 문서의 T1(JD) 상한 0.80과 02_candidate_context의 T1(이력서) 상한 0.85는 서로 다른 데이터 소스에 대한 상한이다. JD는 채용 광고 특성상 과장/누락 가능성이 있어 이력서보다 낮은 상한을 적용한다.
> 

**적용 조건 미충족 시**: base ceiling 0.55를 적용한다.

```python
def get_category_ceiling(category, extracted_data):
    """카테고리 별 ceiling을 반환하되, 예외 조건 충족 여부 검증"""
    if category == "funding":
        has_amount = extracted_data.get("funding_amount") is not None
        has_investors = bool(extracted_data.get("investors"))
        if has_amount and has_investors:
            return 0.65
        return 0.55
    if category == "performance":
        has_numeric = extracted_data.get("metric_value") is not None
        if has_numeric:
            return 0.60
        return 0.55
    return CATEGORY_CEILING.get(category, 0.55)
```

> `06_crawling_strategy.md` 3.5절의 `CATEGORY_CEILING` 딕셔너리와 호환
> 

---

## 2. 필드 정의 - 소스 Tier 별 분류

### 2.1 T1+T2로 즉시 구현 가능한 필드

**현재 보유 데이터만으로 생성 가능**

### company_profile (NICE 기반)

| 필드 | 타입 | 소스 | 추출 방법 | 예시 |
| --- | --- | --- | --- | --- |
| `company_id` | string | 내부 ID | Lookup | `"comp_12345"` |
| `company_name` | string | NICE | Lookup | `"스타트업 A"` |
| `industry_code` | string | code-hub INDUSTRY | Lookup | `"SW_DEV"` (소프트웨어 개발업) |
| `industry_label` | string | NICE | Lookup + 매핑 | `"소프트웨어 개발"` |
| `founded_year` | int | NICE | Lookup | `2019` |
| `employee_count` | int | NICE | Lookup | `85` |
| `revenue_range` | string | NICE | Lookup | `"10억~50억"` |
| `is_regulated_industry` | bool | NICE industry_code | Rule | `false` |

### stage_estimate (NICE + JD 복합 추론)

| 필드 | 타입 | 추출 방법 | 설명 |
| --- | --- | --- | --- |
| `stage_label` | enum | Rule + LLM | 아래 taxonomy 참조 |
| `stage_confidence` | float | 계산 | source ceiling 적용 |
| `stage_signals` | Evidence[] | LLM + Rule | 판단 근거 |

**stage_label taxonomy**:

| label | 판단 기준 (Rule 우선, LLM 보조) |
| --- | --- |
| `EARLY` | 설립 3년 이내 AND 직원 30명 미만 |
| `GROWTH` | 직원 30~300명 OR JD에 "스케일업/성장" 언급 |
| `SCALE` | 직원 300명+ OR 매출 100억+ |
| `MATURE` | 설립 15년+ AND 매출 500억+ |
| `UNKNOWN` | 판단 불가 |

> estimate_stage() pseudo-code → 02.knowledge_graph/results/extraction_logic/v13/03_prompt_design.md 참조

### vacancy (JD 기반)

| 필드 | 타입 | 소스 | 추출 방법 | 설명 |
| --- | --- | --- | --- | --- |
| `hiring_context` | enum | JD | LLM | `BUILD_NEW` / `SCALE_EXISTING` / `RESET` / `REPLACE` / `UNKNOWN` |
| `scope_description` | string | JD | LLM | 포지션이 열린 맥락 서술 |
| `role_title` | string | JD | LLM + Rule | 직무명 |
| `seniority` | enum | JD | LLM | `JUNIOR` / `MID` / `SENIOR` / `LEAD` / `HEAD` / `UNKNOWN` |
| `team_context` | string | JD | LLM | 팀 구성/규모 맥락 (추출 가능 시) |

**hiring_context 추출 규칙**:

| hiring_context | v3 표현 | JD 내 탐지 패턴 |
| --- | --- | --- |
| `BUILD_NEW` | 0->1 | "신규 구축", "처음부터", "new team", "0->1", "greenfield" |
| `SCALE_EXISTING` | 1->10 | "확장", "스케일", "고도화", "성장", "scale" |
| `RESET` | reset | "개선", "리팩토링", "재설계", "전환", "migration" |
| `REPLACE` | (v3에 없음) | "충원", "결원", "대체" |
| `UNKNOWN` | - | 패턴 미탐지 시 |

### 2.3 동일 기업 다중 공고 처리 원칙

동일 기업(`company_id`)이 여러 Vacancy를 동시에 보유하는 경우의 처리 원칙:

| 수준 | 공유 여부 | 설명 |
| --- | --- | --- |
| `company_profile` | **공유** | 기업 기본 정보(업종, 직원수, 매출)는 기업 단위이므로 동일 기업 공고 간 공유 |
| `stage_estimate` | **공유** | 성장 단계는 기업 수준 속성 |
| `operating_model` | **공유** | 운영 방식(speed, autonomy, process)은 기업 수준 |
| `structural_tensions` | **공유** | 조직 긴장 상태는 기업 수준 |
| `vacancy` | **공고별 독립** | hiring_context, seniority, team_context는 공고마다 다름 |
| `role_expectations` | **공고별 독립** | 요구 역할/기술/자격요건은 공고마다 다름 |
| `domain_positioning` | **공유** | 시장 포지셔닝은 기업 수준 (사업부별 차이는 v2에서 검토) |

**구현 원칙**: CompanyContext는 `job_id`별로 하나씩 생성하되, 동일 `company_id`의 공고들은 company_profile, stage_estimate, operating_model, structural_tensions를 **캐싱하여 재사용**, 동일 기업의 100개 공고에 대해 기업 수준 데이터(NICE 조회, stage 추정 등)를 1회 수행

### role_expectations (JD 기반)

| 필드 | 타입 | 소스 | 추출 방법 |
| --- | --- | --- | --- |
| `responsibilities` | string[] | JD | LLM |
| `requirements` | string[] | JD | LLM |
| `preferred` | string[] | JD | LLM |
| `tech_stack` | string[] | JD | LLM + Rule (정규화) |

### operating_model (JD 기반)

| facet | 스케일 | 추출 방법 | confidence 기대치 |
| --- | --- | --- | --- |
| `speed` | 0.0~1.0 | 키워드 카운트 + LLM 보정 | 0.3~0.6 |
| `autonomy` | 0.0~1.0 | 키워드 카운트 + LLM 보정 | 0.3~0.6 |
| `process` | 0.0~1.0 | 키워드 카운트 + LLM 보정 | 0.3~0.6 |

> extract_facet() pseudo-code + 키워드 → 02.knowledge_graph/results/extraction_logic/v13/03_prompt_design.md 참조

### 2.2 T3~T5 추가 시 보강되는 필드

크롤링 / 투자 DB 연동 후 활성화.

### stage_estimate 보강 (T5 투자 정보)

| 추가 필드 | 소스 | 추출 방법 |
| --- | --- | --- |
| `funding_stage` | 투자 DB | Lookup |
| `last_funding_date` | 투자 DB | Lookup |
| `total_funding_amount` | 투자 DB | Lookup |
| `investors` | 투자 DB | Lookup |

투자 정보가 있으면 stage_label의 confidence를 상향:

```python
# 투자 정보로 stage 보강
if invest_data.funding_stage:
    FUNDING_TO_STAGE = {
        "Seed": "EARLY", "Pre-A": "EARLY",
        "Series A": "GROWTH", "Series B": "GROWTH",
        "Series C": "SCALE", "Series D+": "SCALE",
        "IPO": "MATURE"
    }
    invest_stage = FUNDING_TO_STAGE.get(invest_data.funding_stage)
    if invest_stage == rule_stage:
        stage_confidence = min(stage_confidence + 0.15, 0.85)
    elif invest_stage:
        stage_label = invest_stage  # 투자 정보 우선
        stage_confidence = 0.75
```

### domain_positioning (T3+T4 크롤링)

| 필드 | 소스 | 추출 방법 | v1 대안 |
| --- | --- | --- | --- |
| `market_segment` | 크롤링 + JD | LLM | JD에서만 추출 (confidence 낮음) |
| `competitive_landscape` | 뉴스 크롤링 | LLM | v1 제외 |
| `product_description` | 홈페이지 크롤링 | LLM | v1 제외 |

### structural_tensions (T3+T4)

| 필드 | 소스 | 추출 방법 | v1 현실 |
| --- | --- | --- | --- |
| `tension_type` | 뉴스/내부문서/JD | LLM | **v1에서 Unknown 비율 70%+ 예상** |
| `tension_description` | 뉴스/내부문서 | LLM | v1에서 JD만으로는 거의 추출 불가 |

structural_tensions는 optional 필드로 두고, MappingFeatures에서 이 필드가 Unknown이면 `tension_alignment` 피처를 비활성화(null).

**tension_type Taxonomy**:

| tension_type | 설명 | 주요 소스 | v3 대응 |
| --- | --- | --- | --- |
| tech_debt_vs_features | 기술부채 해소 vs 신기능 개발 | 뉴스, JD | v3 유지 |
| speed_vs_reliability | 빠른 출시 vs 안정성/품질 | JD, 블로그 | v3 유지 |
| founder_vs_professional_mgmt | 창업자 경영 vs 전문경영인 전환 | 뉴스(N4) | v3 유지 |
| efficiency_vs_growth | 효율화/비용 절감 vs 성장 투자 | 뉴스(N4, N5) | v5 신규 |
| scaling_leadership | 리더십 확장/전문화 필요 | 뉴스(N4) | v5 신규 |
| integration_tension | M&A/합병 후 조직 통합 긴장 | 뉴스(N3) | v5 신규 |
| build_vs_buy | 내부 개발 vs 외부 솔루션/파트너십 | 뉴스(N3) | v5 신규 |
| portfolio_restructuring | 사업부 재편/선택과 집중 | 뉴스(N4) | v5 신규 |

**tension_type 간 배타성 가이드**:

| 모호한 조합 | 판정 기준 | 예시 |
| --- | --- | --- |
| efficiency_vs_growth vs portfolio_restructuring | 전사 차원이면 efficiency, 특정 사업부면 portfolio | "전사 30% 감원" -> efficiency, "A사업부 매각" -> portfolio |
| scaling_leadership vs founder_vs_professional_mgmt | 창업자가 CEO인 채 CxO 영입이면 scaling, CEO를 내려놓으면 founder | "CTO 외부 영입" -> scaling, "전문경영인 CEO" -> founder |
| build_vs_buy vs integration_tension | M&A 결정 시점이면 build_vs_buy, M&A 후 통합이면 integration | "B사 인수 결정" -> build_vs_buy, "B사 인수 후 통합" -> integration |

> 복수 tension이 해당되는 경우, primary_tension과 related_tensions로 구분하여 할당한다.
> 

**TypeScript 정의**:

```tsx
type TensionType =
  | "tech_debt_vs_features"
  | "speed_vs_reliability"
  | "founder_vs_professional_mgmt"
  | "efficiency_vs_growth"
  | "scaling_leadership"
  | "integration_tension"
  | "build_vs_buy"
  | "portfolio_restructuring";

interface StructuralTension {
  tension_type: TensionType;
  related_tensions?: TensionType[];   // [v7] secondary tensions (최대 2개)
  description: string;
  confidence: number;
  evidence: Evidence[];
}
```

**crawling N4 섹션 정합성**:

| change_type (crawling N4) | tension_type (taxonomy) |
| --- | --- |
| CEO 교체 | founder_vs_professional_mgmt |
| CxO 영입 | scaling_leadership |
| 조직개편 | portfolio_restructuring |
| 구조조정/감원 | efficiency_vs_growth |
| 사업부 분리/합병 | portfolio_restructuring |

---

### 2.4 CompanyContext 재생성 조건

> §2.4 재생성 조건 → 03.graphrag/results/implement_planning/separate/v3/shared/regeneration_policy.md로 이동

---

## 3. CompanyContext JSON 스키마

```json
{
  "$schema": "CompanyContext_v4",
  "company_id": "comp_12345",
  "job_id": "job_67890",

  "_meta": {
    "context_version": "4.0",
    "dataset_version": "2026-03-01",
    "code_sha": "abc1234",
    "generated_at": "2026-03-08T10:00:00Z",
    "sources_used": ["jd_internal", "nice"],
    "completeness": {
      "total_fields": 14,
      "filled_fields": 10,
      "fill_rate": 0.71,
      "missing_fields": [
        "structural_tensions",
        "domain_positioning.competitive_landscape",
        "domain_positioning.product_description",
        "operating_model.narrative_summary"
      ]
    }
  },

  "company_profile": {
    "company_name": "스타트업 A",
    "industry_code": "SW_DEV",
    "industry_label": "소프트웨어 개발업",
    "founded_year": 2019,
    "employee_count": 85,
    "revenue_range": "10억~50억",
    "is_regulated_industry": false,
    "evidence": [
      {
        "source_id": "nice_comp_12345",
        "source_type": "nice",
        "span": "종업원수: 85명, 설립: 2019년, 매출: 32억",
        "confidence": 0.70,
        "extracted_at": "2026-03-01T00:00:00Z"
      }
    ]
  },

  "stage_estimate": {
    "stage_label": "GROWTH",
    "stage_confidence": 0.65,
    "funding_stage": null,
    "stage_signals": [
      {
        "source_id": "nice_comp_12345",
        "source_type": "nice",
        "span": "설립 7년, 직원 85명",
        "confidence": 0.70,
        "extracted_at": "2026-03-01T00:00:00Z"
      },
      {
        "source_id": "jd_67890",
        "source_type": "jd_internal",
        "span": "급성장 중인 팀에서 함께할 시니어 엔지니어를 찾습니다",
        "confidence": 0.55,
        "extracted_at": "2026-03-08T10:00:00Z"
      }
    ]
  },

  "vacancy": {
    "hiring_context": "SCALE_EXISTING",
    "scope_description": "기존 백엔드 시스템의 트래픽 10배 증가 대응을 위한 시니어 엔지니어 충원",
    "role_title": "Senior Backend Engineer",
    "seniority": "SENIOR",
    "team_context": "백엔드 팀 5명, 프론트 3명 구성의 제품팀 소속",
    "evidence": [
      {
        "source_id": "jd_67890",
        "source_type": "jd_internal",
        "span": "현재 5명의 백엔드 팀에서 트래픽 10배 증가에 대응할 시니어 엔지니어를 모십니다",
        "confidence": 0.75,
        "extracted_at": "2026-03-08T10:00:00Z"
      }
    ]
  },

  "role_expectations": {
    "responsibilities": [
      "대용량 트래픽 처리 아키텍처 설계",
      "팀 기술 리딩 및 코드 리뷰"
    ],
    "requirements": [
      "백엔드 개발 경력 7년 이상",
      "대규모 트래픽 처리 경험"
    ],
    "preferred": [
      "스타트업 성장기 경험"
    ],
    "tech_stack": ["Python", "FastAPI", "PostgreSQL", "Redis", "AWS"],
    "evidence": [
      {
        "source_id": "jd_67890",
        "source_type": "jd_internal",
        "span": "...(JD 원문 발췌)",
        "confidence": 0.80,
        "extracted_at": "2026-03-08T10:00:00Z"
      }
    ]
  },

  "operating_model": {
    "facets": {
      "speed": { "score": 0.72, "confidence": 0.45 },
      "autonomy": { "score": 0.65, "confidence": 0.40 },
      "process": { "score": 0.38, "confidence": 0.35 }
    },
    "narrative_summary": null,
    "evidence": [
      {
        "source_id": "jd_67890",
        "source_type": "jd_internal",
        "span": "2주 스프린트 기반으로 빠르게 제품을 만들고 있습니다",
        "confidence": 0.55,
        "extracted_at": "2026-03-08T10:00:00Z"
      }
    ]
  },

  "structural_tensions": [
    {
      "tension_type": "efficiency_vs_growth",
      "related_tensions": ["portfolio_restructuring"],
      "description": "최근 30% 인력 감축 발표, 성장 투자 축소 시사. 동시에 비핵심 사업부 정리 진행",
      "confidence": 0.45,
      "evidence": [
        {
          "source_id": "crawl_news_c001_art_20260301_001",
          "source_type": "crawl_news",
          "span": "A사는 전사 구조조정을 통해 30%의 인력을 감축한다고 밝혔다",
          "confidence": 0.50,
          "extracted_at": "2026-03-01T00:00:00Z"
        }
      ]
    }
  ],

  "domain_positioning": {
    "market_segment": "B2B SaaS",
    "competitive_landscape": null,
    "product_description": null,
    "evidence": [
      {
        "source_id": "jd_67890",
        "source_type": "jd_internal",
        "span": "B2B SaaS 기반 HR 솔루션",
        "confidence": 0.60,
        "extracted_at": "2026-03-08T10:00:00Z"
      }
    ]
  }
}
```

---

## 4. Evidence 통합 모델

- 자사 정보와 크롤링 정보 통합

```tsx
interface Evidence {
  source_id: string;           // 소스 문서/레코드의 고유 ID
  source_type: SourceType;     // enum (아래 정의)
  span: string;                // 원문 발췌 (최대 500자)
  confidence: number;          // 0.0~1.0, source ceiling 적용 후
  extracted_at: string;        // ISO 8601
  extraction_method?: string;  // "llm_gpt4o" | "rule_keyword" | "lookup_nice"
}

type SourceType =
  | "jd_internal"      // 자사 보유 JD
  | "jd_crawled"       // 외부 크롤링 JD
  | "nice"             // NICE 기업 정보
  | "crawl_site"       // 회사 홈페이지 크롤링
  | "crawl_news"       // 뉴스/기사 크롤링
  | "invest_db"        // 투자 정보 DB
  | "self_resume"      // 자사 이력서
  | "linkedin"         // LinkedIn 이력서
  | "career_desc"      // 경력 기술서
  | "enrichment_qa";   // Closed-loop 질문 응답
```

---

## 5. confidence 캘리브레이션 기준

confidence 수치 명확화

| 범위 | 의미 | 예시 |
| --- | --- | --- |
| 0.80~1.00 | 팩트 수준 확신 (복수 소스 교차 검증 완료) | NICE 직원수 + JD 팀 규모 일치 |
| 0.60~0.79 | 단일 신뢰 소스에서 명시적 추출 | JD에서 명확히 "시니어" 명시 |
| 0.40~0.59 | 단일 소스에서 추론/해석 필요 | JD 문맥에서 "빠른 성장" -> GROWTH 추론 |
| 0.20~0.39 | 약한 신호, 간접 추론 | 키워드 1~2개로 facet 추정 |
| 0.00~0.19 | 거의 추측, 사용 시 주의 | 소스 없이 industry prior만으로 추론 |
| null / 0.0 | 추출 불가, Unknown | structural_tensions 미추출 |

---

## 6. 데이터 수집 우선순위

CompanyContext 품질을 가장 빠르게 올릴 수 있는 순서:

| 순위 | 데이터 소스 | 영향 필드 | 구축 난이도 | ROI |
| --- | --- | --- | --- | --- |
| 1 | **투자 DB API 연동** | stage_estimate 대폭 보강 | 중 (API 연동) | 높음 |
| 2 | **회사 홈페이지 크롤링** | domain_positioning, operating_model 보강 | 중 (크롤러) | 중 |
| 3 | **뉴스/기사 크롤링** | structural_tensions 활성화 | 중~상 | 중 |

---