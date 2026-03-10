# CompanyContext v13 — 통합판

> v4 원본에 A3(CompanyTalentSignal 제외 명문화), A6(structural_tensions Taxonomy + Tier ceiling 예외)를 통합.
>
> 작성일: 2026-03-10 | 기준: v4 CompanyContext + v4 amendments (A3, A6) + v12 데이터 분석 v2.1
>
> **v13 변경** (2026-03-10): v12 데이터 분석 v2.1 결과 반영
> - industry_code: v11에서 code-hub INDUSTRY 코드를 primary로 채택 (NICE는 보조). 상세: 00_data_source_mapping §1.1
> - vacancy 매핑: job-hub 구조화 필드 활용 강화 (designation_codes → seniority, skill 테이블 → tech_stack). 상세: 00_data_source_mapping §2.3~2.5
> - job-hub 필드 실측 분석은 Phase 4-1에서 수행 예정 (현재는 예상 fill rate)

---

## 0. 설계 원칙 (v3 유지 + v4 추가 + v7 추가)

| 원칙 | v3 | v4 추가 | v7 추가 |
|---|---|---|---|
| 독립성 | 후보와 무관하게 생성 | 유지 | 유지 |
| Evidence-first | 모든 claim에 근거 필수 | 유지 | 유지 |
| 부분 완성 | missing_fields 명시 | 유지 | 유지 |
| **데이터 소스 계층화** | — | 필드별 데이터 소스 Tier를 명시하고, Tier에 따라 confidence 상한을 제한 | 유지 |
| **추출 방법 명시** | — | 각 필드의 추출 방식(LLM / Rule / Lookup)을 정의 | 유지 |
| **Unknown 정상화** | — | v1에서 Unknown 비율이 높은 필드를 명시적으로 허용 | 유지 |
| **의도적 제외 명문화** | — | — | 현 버전에서 의도적으로 제외한 기능/필드를 명시하고, 제외 이유와 도입 로드맵을 문서화 |

---

## 1. 데이터 소스 Tier 정의

각 소스에 **confidence 상한(ceiling)**을 부여한다. 해당 소스만으로 추출된 claim은 이 상한을 초과할 수 없다.

| Tier | 소스 | confidence 상한 | 현재 상태 | source_type enum |
|---|---|---|---|---|
| T1 | JD (자사 보유 / 크롤링) | 0.80 | 자사 보유분 접근 가능, 외부는 크롤링 필요 | `jd_internal`, `jd_crawled` |
| T2 | NICE 기업 정보 | 0.70 | 보유 | `nice` |
| T3 | 회사 홈페이지 크롤링 | 0.60 | 미구축 (크롤러 필요) | `crawl_site` |
| T4 | 뉴스 / 기사 크롤링 | 0.55 (카테고리별 예외 있음, 아래 참조) | 미구축 | `crawl_news` |
| T5 | 투자 정보 DB (더브이씨, 크런치베이스 등) | 0.75 | 미구축 (API 연동 필요) | `invest_db` |
| T6 | 자사 채용 히스토리 | 0.85 | 접근 가능 (추정) | `hiring_history` |
| T7 | 회사 보유 내부 기업 정보 | 0.90 | 미보유 | `internal_doc` |

### confidence 상한 적용 규칙

```
field_confidence = min(extraction_confidence, source_ceiling)
```

- 복수 소스가 동일 claim을 지지하면: `boosted = min(max(c1, c2) + 0.10, 0.95)`
- 복수 소스가 모순되면: `field_confidence = min(c1, c2) * 0.5`, `contradiction=true` 표기

### T4 Tier ceiling 예외 규칙 [v7 추가]

T4(뉴스/기사)의 base ceiling 0.55에 대해 카테고리별 예외를 허용한다.

| 카테고리 | 예외 ceiling | 적용 조건 | 근거 |
|---|---|---|---|
| funding | 0.65 | 투자 금액 + 투자사명이 동시에 추출된 경우에만 적용 | 두 팩트가 교차 검증 가능하므로 높은 신뢰도 인정 |
| performance | 0.60 | 구체적 수치(매출, MAU, 거래액 등)가 포함된 경우에만 적용 | 정량 데이터는 정성 추론보다 검증 가능성이 높음 |

**적용 조건 미충족 시**: base ceiling 0.55를 적용한다.

```python
def get_category_ceiling(category, extracted_data):
    """[v7] 카테고리별 ceiling을 반환하되, 예외 조건 충족 여부를 검증."""
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

> 이 예외 규칙은 `06_crawling_strategy.md` 3.5절의 `CATEGORY_CEILING` 딕셔너리와 정합된다.

---

## 2. 필드 정의 — 소스 Tier별 분류

### 2.1 T1+T2로 즉시 구현 가능한 필드 (v1 Core)

이 필드들은 **현재 보유 데이터만으로 생성 가능**하다.

#### company_profile (NICE 기반 팩트)

| 필드 | 타입 | 소스 | 추출 방법 | 예시 |
|---|---|---|---|---|
| `company_id` | string | 내부 ID | Lookup | `"comp_12345"` |
| `company_name` | string | NICE | Lookup | `"스타트업 A"` |
| `industry_code` | string | NICE | Lookup | `"J63112"` (소프트웨어 개발) |
| `industry_label` | string | NICE | Lookup + 매핑 | `"소프트웨어 개발"` |
| `founded_year` | int | NICE | Lookup | `2019` |
| `employee_count` | int | NICE | Lookup | `85` |
| `revenue_range` | string | NICE | Lookup | `"10억~50억"` |
| `is_regulated_industry` | bool | NICE industry_code | Rule | `false` |

#### stage_estimate (NICE + JD 복합 추론)

| 필드 | 타입 | 추출 방법 | 설명 |
|---|---|---|---|
| `stage_label` | enum | Rule + LLM | 아래 taxonomy 참조 |
| `stage_confidence` | float | 계산 | source ceiling 적용 |
| `stage_signals` | Evidence[] | LLM + Rule | 판단 근거 |

**stage_label taxonomy (v1 고정)**:

| label | 판단 기준 (Rule 우선, LLM 보조) |
|---|---|
| `EARLY` | 설립 3년 이내 AND 직원 30명 미만 |
| `GROWTH` | 직원 30~300명 OR JD에 "스케일업/성장" 언급 |
| `SCALE` | 직원 300명+ OR 매출 100억+ |
| `MATURE` | 설립 15년+ AND 매출 500억+ |
| `UNKNOWN` | 판단 불가 |

```python
# stage 추정 pseudo-code
def estimate_stage(nice_data, jd_text):
    # Rule-based primary
    if nice_data.founded_year and nice_data.employee_count:
        age = current_year - nice_data.founded_year
        emp = nice_data.employee_count
        if age <= 3 and emp < 30:
            return "EARLY", 0.70
        elif 30 <= emp <= 300:
            return "GROWTH", 0.65
        elif emp > 300 or nice_data.revenue > 10_000_000_000:
            return "SCALE", 0.65
        elif age >= 15 and nice_data.revenue > 50_000_000_000:
            return "MATURE", 0.70

    # LLM fallback — JD 텍스트에서 stage 힌트 추출
    llm_stage = llm_extract_stage(jd_text)
    if llm_stage:
        return llm_stage, 0.50  # JD만으로는 confidence 낮음

    return "UNKNOWN", 0.0
```

#### vacancy (JD 기반)

| 필드 | 타입 | 소스 | 추출 방법 | 설명 |
|---|---|---|---|---|
| `scope_type` | enum | JD | LLM | `BUILD_NEW` / `SCALE_EXISTING` / `RESET` / `REPLACE` / `UNKNOWN` |
| `scope_description` | string | JD | LLM | 포지션이 열린 맥락 서술 |
| `role_title` | string | JD | LLM + Rule | 직무명 |
| `seniority` | enum | JD | LLM | `JUNIOR` / `MID` / `SENIOR` / `LEAD` / `HEAD` / `UNKNOWN` |
| `team_context` | string | JD | LLM | 팀 구성/규모 맥락 (추출 가능 시) |

**scope_type 추출 규칙**:

| scope_type | v3 표현 | JD 내 탐지 패턴 |
|---|---|---|
| `BUILD_NEW` | 0→1 | "신규 구축", "처음부터", "new team", "0→1", "greenfield" |
| `SCALE_EXISTING` | 1→10 | "확장", "스케일", "고도화", "성장", "scale" |
| `RESET` | reset | "개선", "리팩토링", "재설계", "전환", "migration" |
| `REPLACE` | (v3에 없음) | "충원", "결원", "대체" |
| `UNKNOWN` | — | 패턴 미탐지 시 |

#### role_expectations (JD 기반)

| 필드 | 타입 | 소스 | 추출 방법 |
|---|---|---|---|
| `responsibilities` | string[] | JD | LLM |
| `requirements` | string[] | JD | LLM |
| `preferred` | string[] | JD | LLM |
| `tech_stack` | string[] | JD | LLM + Rule (정규화) |

#### operating_model (JD 기반, v1은 3 facets)

| facet | 스케일 | 추출 방법 | confidence 기대치 |
|---|---|---|---|
| `speed` | 0.0~1.0 | 키워드 카운트 + LLM 보정 | 0.3~0.6 |
| `autonomy` | 0.0~1.0 | 키워드 카운트 + LLM 보정 | 0.3~0.6 |
| `process` | 0.0~1.0 | 키워드 카운트 + LLM 보정 | 0.3~0.6 |

```python
# operating_model facet 추출 pseudo-code
SPEED_KEYWORDS = ["빠르게", "신속", "ship", "launch", "rapid", "fast-paced",
                  "스프린트", "애자일", "주간 배포"]
AUTONOMY_KEYWORDS = ["오너십", "주도", "ownership", "lead", "end-to-end",
                     "자율", "재량", "의사결정"]
PROCESS_KEYWORDS = ["OKR", "KPI", "코드리뷰", "code review", "CI/CD",
                    "테스트", "문서화", "RFC", "PRD"]

def extract_facet(jd_text, keywords):
    count = sum(1 for kw in keywords if kw.lower() in jd_text.lower())
    keyword_score = min(count / 5.0, 1.0)  # 5개 이상이면 1.0

    # LLM 보정: 키워드가 광고성인지 실제 운영 맥락인지 판별
    llm_adjustment = llm_assess_authenticity(jd_text, keywords, count)

    score = keyword_score * llm_adjustment  # adjustment: 0.5~1.0
    confidence = min(0.60, 0.30 + count * 0.06)  # JD 단독 소스이므로 ceiling 0.60
    return score, confidence
```

**광고성 필터링 규칙 (v3 계승)**:
- "수평적", "패밀리", "열정", "최고의 복지" 등 정성 구호 → facet 스코어에 반영하지 않음
- 수치/사건/제약이 동반된 표현만 claim으로 인정

### 2.2 T3~T5 추가 시 보강되는 필드 (v1.1 확장)

크롤링 / 투자 DB 연동 후 활성화.

#### stage_estimate 보강 (T5 투자 정보)

| 추가 필드 | 소스 | 추출 방법 |
|---|---|---|
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

#### domain_positioning (T3+T4 크롤링)

| 필드 | 소스 | 추출 방법 | v1 대안 |
|---|---|---|---|
| `market_segment` | 크롤링 + JD | LLM | JD에서만 추출 (confidence 낮음) |
| `competitive_landscape` | 뉴스 크롤링 | LLM | v1 제외 |
| `product_description` | 홈페이지 크롤링 | LLM | v1 제외 |

#### structural_tensions (T3+T4+T7) [v7 대폭 확장]

| 필드 | 소스 | 추출 방법 | v1 현실 |
|---|---|---|---|
| `tension_type` | 뉴스/내부문서/JD | LLM | **v1에서 Unknown 비율 70%+ 예상** |
| `tension_description` | 뉴스/내부문서 | LLM | v1에서 JD만으로는 거의 추출 불가 |

**v1 대응**: structural_tensions는 optional 필드로 두고, MappingFeatures에서 이 필드가 Unknown이면 `tension_alignment` 피처를 비활성화(null).

**tension_type Taxonomy [v7 신규] (v1: 8개)**:

| tension_type | 설명 | 주요 소스 | v3 대응 |
|---|---|---|---|
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
|---|---|---|
| efficiency_vs_growth vs portfolio_restructuring | 전사 차원이면 efficiency, 특정 사업부면 portfolio | "전사 30% 감원" -> efficiency, "A사업부 매각" -> portfolio |
| scaling_leadership vs founder_vs_professional_mgmt | 창업자가 CEO인 채 CxO 영입이면 scaling, CEO를 내려놓으면 founder | "CTO 외부 영입" -> scaling, "전문경영인 CEO" -> founder |
| build_vs_buy vs integration_tension | M&A 결정 시점이면 build_vs_buy, M&A 후 통합이면 integration | "B사 인수 결정" -> build_vs_buy, "B사 인수 후 통합" -> integration |

> 복수 tension이 해당되는 경우, primary_tension과 related_tensions로 구분하여 할당한다.

**TypeScript 정의 [v7]**:

```typescript
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
|---|---|
| CEO 교체 | founder_vs_professional_mgmt |
| CxO 영입 | scaling_leadership |
| 조직개편 | portfolio_restructuring |
| 구조조정/감원 | efficiency_vs_growth |
| 사업부 분리/합병 | portfolio_restructuring |

---

## 3. v4 CompanyContext JSON 스키마 (structural_tensions 예제 추가 [v7])

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
    "industry_code": "J63112",
    "industry_label": "소프트웨어 개발",
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
    "scope_type": "SCALE_EXISTING",
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

v3에서 두 문서 간 불일치했던 evidence 구조를 단일 모델로 통합.

```typescript
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
  | "hiring_history"   // 자사 채용 히스토리
  | "internal_doc"     // 회사 내부 문서
  | "self_resume"      // 자사 이력서
  | "linkedin"         // LinkedIn 이력서
  | "career_desc"      // 경력 기술서
  | "enrichment_qa";   // Closed-loop 질문 응답
```

---

## 5. confidence 캘리브레이션 기준

v3에서 미정의였던 confidence 수치의 의미를 명확화.

| 범위 | 의미 | 예시 |
|---|---|---|
| 0.80~1.00 | 팩트 수준 확신 (복수 소스 교차 검증 완료) | NICE 직원수 + JD 팀 규모 일치 |
| 0.60~0.79 | 단일 신뢰 소스에서 명시적 추출 | JD에서 명확히 "시니어" 명시 |
| 0.40~0.59 | 단일 소스에서 추론/해석 필요 | JD 문맥에서 "빠른 성장" → GROWTH 추론 |
| 0.20~0.39 | 약한 신호, 간접 추론 | 키워드 1~2개로 facet 추정 |
| 0.00~0.19 | 거의 추측, 사용 시 주의 | 소스 없이 industry prior만으로 추론 |
| null / 0.0 | 추출 불가, Unknown | structural_tensions 미추출 |

---

## 6. v1 / v1.1 / v2 필드 로드맵

| 필드 | v1 (즉시) | v1.1 (크롤링 후) | v2 (고도화) |
|---|---|---|---|
| company_profile (NICE 팩트) | O | O | O |
| stage_estimate (Rule + JD) | O | 투자 DB 보강 | taxonomy 확장 |
| vacancy (JD 추출) | O | O | O |
| role_expectations (JD 추출) | O | O | O |
| operating_model (3 facets) | O | 크롤링 보강 | 8 facets 확장 |
| structural_tensions | **null (허용)** | 크롤링+뉴스로 시도 | 내부 문서 연동 |
| domain_positioning.market_segment | JD만 (낮은 confidence) | 크롤링 보강 | 경쟁 맥락 추가 |
| domain_positioning.competitive_landscape | null | 뉴스 크롤링 | O |
| operating_model.narrative_summary | null | 크롤링 보강 | O |
| funding_stage (투자 정보) | null | 투자 DB 연동 | O |
| CompanyTalentSignal | **v1 범위 밖 (명시적 제외)** | 제외 | v2 도입 검토 (표본>=20 기업 파일럿) |

---

## 7. 데이터 수집 우선순위 (구현 관점)

CompanyContext 품질을 가장 빠르게 올릴 수 있는 순서:

| 순위 | 데이터 소스 | 영향 필드 | 구축 난이도 | ROI |
|---|---|---|---|---|
| 1 | **투자 DB API 연동** | stage_estimate 대폭 보강 | 중 (API 연동) | 높음 |
| 2 | **회사 홈페이지 크롤링** | domain_positioning, operating_model 보강 | 중 (크롤러) | 중 |
| 3 | **뉴스/기사 크롤링** | structural_tensions 활성화 | 중~상 | 중 |
| 4 | **자사 채용 히스토리 분석** | vacancy 패턴, 이직률 신호 | 중 (내부 데이터) | 중 |
| 5 | **내부 기업 정보 확보** | 전체 필드 고도화 | 상 (비즈니스 의존) | 높음 (장기) |

---

## 8. 의도적 범위 제외 사항 [v7 추가]

### 8.1 CompanyTalentSignal

v3 Context Overview에서 정의한 CompanyTalentSignal(후보 분포 기반 관측 신호)을 v1에서 의도적으로 제외한다.

**제외 이유**:

1. **데이터 전제 조건 미충족**: "채용 완료 후보 중 재직 6개월 이상" 같은 모집단 정의가 필요하며, 충분한 표본(v3 예시: 42명)이 있어야 유의미. 현재 대부분 기업에서 표본 크기 확보 어려움
2. **독립성 원칙 강화**: v4는 CompanyContext와 CandidateContext의 독립성을 강화. CompanyTalentSignal은 후보 데이터에 의존하므로 기본 파이프라인 안정화 후 별도 모듈로 도입이 적절
3. **편향 리스크**: "모집단이 바뀌면 회사 맥락이 후보 데이터에 의해 오염"되는 리스크가 있으며, v1에서 이를 제어할 인프라 없음

**v2 로드맵**:

| 버전 | CompanyTalentSignal 상태 |
|---|---|
| v1 | 제외 (명시적) |
| v1.1 | 제외 |
| v2 | 도입 검토 — 표본 크기 >= 20인 기업 대상 파일럿 |
| v2.1+ | MappingFeatures의 보조 feature로 통합 (weight 제한: max 0.05) |
