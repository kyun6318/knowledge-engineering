# v4 스키마 보완 사항 (Amendments)

> v4 평가에서 식별된 5개 보완 권장사항 + crawling 전략에서 발견된 1개 정합성 이슈를 해결.
> 이 문서의 내용은 v4 문서(01~04)에 대한 **패치**로, v5 이후 스키마에 반영한다.
>
> 작성일: 2026-03-08
>
> **v6 반영** (2026-03-08): v5 리뷰 피드백 반영
> - [A1-1] FOUNDER의 경력 연수 기반 HEAD 승격 규칙 추가
> - [A2-1] is_regulated 판정 기준 목록 추가
> - [A4-1] STAGE_SIMILARITY 매트릭스 캘리브레이션 계획 추가
> - [A6-1] tension_type 간 배타성 정리 및 related_tensions 구조 추가
> - [V-6] CompanyContext JSON 스키마 업데이트 지침 명시
>
> **v7 반영** (2026-03-08): v6 리뷰 잔여 권장사항 3건 반영
> - [V-6] T4 Tier ceiling 예외 규칙 명문화 (A6 뒤 신규 하위섹션)
> - [A7-1] Vector baseline 구체화 (임베딩 모델/입력/통제변수 명시)
> - [C6-1, C6-2] A8 추출 프롬프트 확장 로드맵 신규 추가

---

## A1. ScopeType <-> Seniority 매핑 테이블

### 문제

CandidateContext의 `scope_type`(`IC / LEAD / HEAD / FOUNDER / UNKNOWN`)과
CompanyContext vacancy의 `seniority`(`JUNIOR / MID / SENIOR / LEAD / HEAD / UNKNOWN`)는
서로 다른 체계를 사용한다. `03_mapping_features.md`의 `role_fit` 계산에서 이 두 체계를
직접 비교하는데, 변환 규칙이 없어 구현 시 모호하다.

### 해결: 명시적 매핑 테이블

**scope_type -> seniority 변환**:

| scope_type (Candidate) | 대응 seniority 범위 | 비고 |
|---|---|---|
| `IC` | `JUNIOR`, `MID`, `SENIOR` | 경력 연수로 세분화 |
| `LEAD` | `SENIOR`, `LEAD` | Lead 경험자는 Senior 이상 |
| `HEAD` | `HEAD` | 직접 대응 |
| `FOUNDER` | `LEAD`, `HEAD` | 경력 연수 기반 분기 [v6 수정] |
| `UNKNOWN` | -- | 매핑 불가, role_fit에서 경력 연수 기반 fallback |

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

**role_fit 계산 시 적용** [v6 수정: A1-1 반영]:

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
        # [v6] 경력 연수 기반 HEAD 승격 규칙 추가
        if years >= 10:
            return "HEAD"
        return "LEAD"
    else:
        return "UNKNOWN"
```

**v4 `03_mapping_features.md` F5 수정 사항**:

기존 `SENIORITY_ORDER`에 scope_type 변환을 선행 적용:

```python
# 기존 (v4)
latest_level = SENIORITY_ORDER.get(latest_exp.scope_type, 0)

# 수정 (v5/v6)
candidate_seniority = get_candidate_seniority(candidate_ctx)
latest_level = SENIORITY_ORDER.get(candidate_seniority, 0)
```

---

## A2. Industry 노드 정의

### 문제

`04_graph_schema.md`에서 `(:Organization)-[:IN_INDUSTRY]->(:Industry)` 관계를 정의했으나,
`:Industry` 노드의 스키마가 누락되어 있다.

### 해결: Industry 노드 정의 추가

```
(:Industry {
  industry_id: STRING,        -- NICE 업종 코드 (예: "J63112")
  label: STRING,              -- "소프트웨어 개발"
  category: STRING,           -- 대분류 (예: "J" = 정보통신업)
  category_label: STRING,     -- "정보통신업"
  is_regulated: BOOLEAN       -- 규제 산업 여부
})
```

**생성 규칙**:
- NICE 업종 코드 기반으로 Industry 노드를 **사전 생성** (마스터 데이터)
- Organization 노드 생성 시 `industry_code`로 매칭하여 `IN_INDUSTRY` 관계 생성
- 동일 업종의 기업들이 하나의 Industry 노드를 공유 -> "같은 산업의 기업" 그래프 탐색 가능

**is_regulated 판정 기준** [v6 추가: A2-1 반영]:

NICE 업종 대분류 기반 규제 산업 판정 목록:

| 대분류 코드 | 대분류명 | is_regulated | 근거 |
|---|---|---|---|
| K | 금융 및 보험업 | `true` | 금융위원회/금감원 규제 |
| Q | 보건업 및 사회복지 서비스업 | `true` | 보건복지부/식약처 규제 |
| D | 전기, 가스, 증기 및 공기조절 공급업 | `true` | 에너지 규제 |
| H | 운수 및 창고업 | `true` | 교통/물류 규제 |
| 기타 | -- | `false` | 기본값 |

```python
REGULATED_CATEGORIES = {"K", "Q", "D", "H"}

def is_regulated_industry(industry_code):
    """NICE 업종 코드의 대분류가 규제 산업인지 판정"""
    category = industry_code[0] if industry_code else None
    return category in REGULATED_CATEGORIES
```

> 세분류 수준의 규제 산업(예: J631 내 핀테크)은 v2에서 수동 태깅으로 보완한다.

**활용 쿼리 예시**:

```cypher
// 같은 산업의 기업에서 일한 후보 탐색
MATCH (target:Organization {org_id: $company_id})-[:IN_INDUSTRY]->(ind:Industry)
      <-[:IN_INDUSTRY]-(similar_org:Organization)
      <-[:OCCURRED_AT]-(ch:Chapter)
      <-[:HAS_CHAPTER]-(p:Person)
RETURN p.person_id, similar_org.name, ch.scope_type
```

---

## A3. CompanyTalentSignal 처리 방침

### 문제

v3 Context Overview에서 정의한 `CompanyTalentSignal`(후보 분포 기반 관측 신호)이
v4 문서에서 언급되지 않아, 의도적 제외인지 누락인지 불명확하다.

### 해결: 의도적 제외 명문화 + v2 로드맵 배치

**v4/v5에서 CompanyTalentSignal을 제외하는 이유**:

1. **데이터 전제 조건 미충족**: CompanyTalentSignal은 "채용 완료 후보 중 재직 6개월 이상" 같은
   모집단 정의가 필요하며, 충분한 표본(v3 예시: 42명)이 있어야 유의미하다. 현재 대부분의
   기업에서 이 표본 크기를 확보하기 어렵다.

2. **독립성 원칙 강화**: v4는 CompanyContext와 CandidateContext의 독립성을 더욱 강화했다.
   CompanyTalentSignal은 후보 데이터에 의존하므로, 기본 파이프라인이 안정화된 후 별도
   모듈로 도입하는 것이 적절하다.

3. **편향 리스크**: v3에서도 명시한 대로 "모집단이 바뀌면 회사 맥락이 후보 데이터에 의해
   오염"되는 리스크가 있으며, v1에서 이를 제어할 인프라가 없다.

**v2 로드맵 배치**:

| 버전 | CompanyTalentSignal 상태 |
|---|---|
| v1 | 제외 (명시적) |
| v1.1 | 제외 |
| v2 | 도입 검토 -- 표본 크기 >= 20인 기업 대상 파일럿 |
| v2.1+ | MappingFeatures의 보조 feature로 통합 (weight 제한: max 0.05) |

---

## A4. STAGE_SIMILARITY 전체 매트릭스

### 문제

`03_mapping_features.md`의 F1(stage_match)에서 `STAGE_SIMILARITY` 매트릭스가
일부만 정의되어 있고 나머지는 기본값 0.2로 처리된다. 구현 시 모호함이 발생한다.

### 해결: 전체 4x4 매트릭스 확정

**STAGE_SIMILARITY** (행: 기업 stage, 열: 후보 경험 stage):

| Company \ Candidate | `EARLY` | `GROWTH` | `SCALE` | `MATURE` |
|---|---|---|---|---|
| **`EARLY`** | **1.00** | 0.30 | 0.15 | 0.10 |
| **`GROWTH`** | 0.50 | **1.00** | 0.40 | 0.20 |
| **`SCALE`** | 0.15 | 0.50 | **1.00** | 0.45 |
| **`MATURE`** | 0.10 | 0.20 | 0.45 | **1.00** |

**설계 근거**:

- 대각선(동일 stage) = 1.0 (완전 매칭)
- **인접 stage 비대칭**:
  - `GROWTH->EARLY`(0.50) > `EARLY->GROWTH`(0.30): GROWTH 기업은 초기 스타트업 경험자를
    "성장기를 겪어봤다"로 어느 정도 인정. 반면 EARLY 기업이 GROWTH 경험자를 찾는 것은
    오버스펙이므로 낮은 유사도.
  - `SCALE->GROWTH`(0.50) > `GROWTH->SCALE`(0.40): 유사한 논리.
  - `MATURE->SCALE`(0.45) = `SCALE->MATURE`(0.45): 대기업 <-> 스케일업 간 이동은 양방향 적합.
- **원거리 stage**: 0.10~0.20 (EARLY <-> MATURE는 맥락이 크게 다름)

**캘리브레이션 계획** [v6 추가: A4-1 반영]:

위 매트릭스 값은 채용 도메인 전문가 판단 기반 초기값이며, v1 파일럿 이후 데이터 기반 캘리브레이션을 수행한다.

| 단계 | 시기 | 방법 | 산출물 |
|---|---|---|---|
| 초기값 | v1 파일럿 | 전문가 판단 (현재 매트릭스) | 현재 4x4 매트릭스 |
| 1차 캘리브레이션 | v1 파일럿 후 | Human evaluation 50건에서 stage_match 분포 분석 | 보정 매트릭스 |
| 2차 캘리브레이션 | v1 운영 3개월 후 | 실제 매핑 결과의 stage_match score vs 채용 성공률 상관 분석 | 최종 매트릭스 |

> v4 `03_mapping_features.md` 7.1절의 "Human evaluation (5명), 매핑 50건"에서
> stage_match 피처의 스코어 분포를 분석하여 매트릭스 값을 조정한다.

**v4 코드 수정**:

```python
# v5/v6 확정 매트릭스 (v4의 부분 정의 대체)
STAGE_SIMILARITY = {
    ("EARLY", "EARLY"): 1.00,   ("EARLY", "GROWTH"): 0.30,
    ("EARLY", "SCALE"): 0.15,   ("EARLY", "MATURE"): 0.10,
    ("GROWTH", "EARLY"): 0.50,  ("GROWTH", "GROWTH"): 1.00,
    ("GROWTH", "SCALE"): 0.40,  ("GROWTH", "MATURE"): 0.20,
    ("SCALE", "EARLY"): 0.15,   ("SCALE", "GROWTH"): 0.50,
    ("SCALE", "SCALE"): 1.00,   ("SCALE", "MATURE"): 0.45,
    ("MATURE", "EARLY"): 0.10,  ("MATURE", "GROWTH"): 0.20,
    ("MATURE", "SCALE"): 0.45,  ("MATURE", "MATURE"): 1.00,
}
# 기본값 fallback 제거 -- 모든 조합이 명시됨
```

---

## A5. Company 간 관계 미포함 이유

### 문제

v3 평가에서 "경쟁사, 동종업계, 투자 관계 등이 그래프에 없다"고 지적했으나,
v4 graph schema에서도 Company 간 관계가 없다.

### 해결: 의도적 제외 명문화 + v2 로드맵

**v1에서 Company 간 관계를 제외하는 이유**:

1. **데이터 소스 부재**: 경쟁사 관계는 뉴스/기사에서 추론 가능하나, 정확도가 낮고
   정의 자체가 모호하다 ("경쟁사"의 범위는?). 투자 관계도 TheVC/크런치베이스 연동 전에는
   데이터가 없다.

2. **MappingFeatures에 직접 기여하지 않음**: v1의 5개 피처(stage_match, vacancy_fit,
   domain_fit, culture_fit, role_fit) 중 Company 간 관계가 필수 입력인 피처가 없다.
   `domain_fit`은 Industry 노드를 통해 간접적으로 해결된다 (A2 참조).

3. **그래프 복잡도 관리**: Company 간 관계를 추가하면 노드 수와 관계 수가 급증하여
   쿼리 성능과 유지보수 부담이 커진다.

**v2 로드맵**:

| 관계 | 도입 시기 | 데이터 소스 | 활용 피처 |
|---|---|---|---|
| `(:Organization)-[:COMPETES_WITH]->(:Organization)` | v2 | 뉴스(N3) + 수동 태깅 | competitive_landscape |
| `(:Organization)-[:INVESTED_BY]->(:Investor)` | v1.1 | TheVC API | stage_estimate 보강 |
| `(:Organization)-[:ACQUIRED]->(:Organization)` | v2 | 뉴스(N3) | structural_tensions |
| `(:Organization)-[:PARTNERED_WITH]->(:Organization)` | v2 | 뉴스(N3) | domain_positioning |

> [v6 참조: A5-1] `INVESTED_BY` 관계를 v1.1에 배치한 것과 정합되도록, 크롤링 전략의
> Phase 0에 "TheVC API 연동" 태스크를 추가했다 (`01_crawling_strategy.md` 6절 Phase 0-6).

---

## A6. structural_tensions Taxonomy 확정

### 문제

v4 `01_company_context.md`에서 `structural_tensions.tension_type`을 string으로만
정의했고, v3에서는 3개 예시(`tech_debt_vs_features`, `speed_vs_reliability`,
`founder_vs_pro_mgmt`)만 언급했다. 한편 v5 `01_crawling_strategy.md`의 N4 섹션에서
6개 신규 tension type을 도입했으나, 정식 taxonomy로 확정되지 않았다.

### 해결: tension_type Taxonomy 확정 (v1: 8개)

| tension_type | 설명 | 주요 소스 | v3 대응 |
|---|---|---|---|
| `tech_debt_vs_features` | 기술부채 해소 vs 신기능 개발 | 뉴스, JD | v3 유지 |
| `speed_vs_reliability` | 빠른 출시 vs 안정성/품질 | JD, 블로그 | v3 유지 |
| `founder_vs_professional_mgmt` | 창업자 경영 vs 전문경영인 전환 | 뉴스(N4) | v3 유지 |
| `efficiency_vs_growth` | 효율화/비용 절감 vs 성장 투자 | 뉴스(N4, N5) | v5 신규 |
| `scaling_leadership` | 리더십 확장/전문화 필요 | 뉴스(N4) | v5 신규 |
| `integration_tension` | M&A/합병 후 조직 통합 긴장 | 뉴스(N3) | v5 신규 |
| `build_vs_buy` | 내부 개발 vs 외부 솔루션/파트너십 | 뉴스(N3) | v5 신규 |
| `portfolio_restructuring` | 사업부 재편/선택과 집중 | 뉴스(N4) | v5 신규 |

**tension_type 간 배타성 가이드** [v6 추가: A6-1 반영]:

일부 tension_type 간 경계가 모호한 경우의 판정 기준:

| 모호한 조합 | 판정 기준 | 예시 |
|---|---|---|
| `efficiency_vs_growth` vs `portfolio_restructuring` | 전사 차원 비용 절감이면 `efficiency_vs_growth`, 특정 사업부 정리/재편이면 `portfolio_restructuring` | "전사 30% 감원" -> efficiency_vs_growth, "A사업부 매각" -> portfolio_restructuring |
| `scaling_leadership` vs `founder_vs_professional_mgmt` | 창업자가 여전히 CEO인 상태에서 CxO 영입이면 `scaling_leadership`, 창업자가 CEO를 내려놓으면 `founder_vs_professional_mgmt` | "CTO 외부 영입" -> scaling_leadership, "전문경영인 CEO 선임, 창업자 의장직" -> founder_vs_professional_mgmt |
| `build_vs_buy` vs `integration_tension` | M&A/파트너십 결정 시점이면 `build_vs_buy`, M&A 후 통합 과정이면 `integration_tension` | "B사 인수 결정" -> build_vs_buy, "B사 인수 후 조직 통합" -> integration_tension |

> 복수 tension이 해당되는 경우, `primary_tension`과 `related_tensions`로 구분하여 할당한다.

**TypeScript 정의** [v6 수정: related_tensions 추가]:

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
  tension_type: TensionType;          // primary tension
  related_tensions?: TensionType[];   // [v6] secondary tensions (있으면, 최대 2개)
  description: string;
  confidence: number;                 // source ceiling 적용 후
  evidence: Evidence[];
}
```

**CompanyContext 필드 수정** [v6 수정: V-6 반영 -- JSON 스키마 업데이트]:

```json
// v4 (기존)
"structural_tensions": null

// v6 (수정 -- related_tensions 포함)
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
]
```

> **[v6 V-6]** v4 `01_company_context.md` 3절의 CompanyContext JSON 스키마에서
> `structural_tensions` 필드의 타입을 `null | StructuralTension[]`로 업데이트해야 한다.
> 위 JSON 예시가 정식 스키마이며, `related_tensions`는 optional 필드이다.

#### T4 Tier ceiling 예외 규칙 [v7 추가: V-6 반영]

v4 `01_company_context.md`에서 T4(뉴스/기사)의 전체 ceiling을 0.55로 정의했다. v6에서 카테고리별 차등 ceiling을 도입하면서 일부 카테고리가 T4 base ceiling을 초과한다. 이를 Tier 시스템의 예외로 명문화한다.

**T4 Tier ceiling 규칙**:

```
T4 (뉴스/기사): base ceiling 0.55
  예외 1: funding 카테고리 -> ceiling 0.65
  예외 2: performance 카테고리 -> ceiling 0.60
```

**예외 적용 조건**:

| 카테고리 | 예외 ceiling | 적용 조건 | 근거 |
|---|---|---|---|
| funding | 0.65 | 투자 금액 + 투자사명이 동시에 추출된 경우에만 적용 | 두 팩트가 교차 검증 가능하므로 높은 신뢰도 인정 |
| performance | 0.60 | 구체적 수치(매출, MAU, 거래액 등)가 포함된 경우에만 적용 | 정량 데이터는 정성 추론보다 검증 가능성이 높음 |

**적용 조건 미충족 시**: base ceiling 0.55를 적용한다.

```python
def get_category_ceiling(category, extracted_data):
    """
    [v7] 카테고리별 ceiling을 반환하되, 예외 조건 충족 여부를 검증.
    """
    if category == "funding":
        has_amount = extracted_data.get("funding_amount") is not None
        has_investors = bool(extracted_data.get("investors"))
        if has_amount and has_investors:
            return 0.65  # 예외: 금액 + 투자사 동시 추출
        return 0.55  # base ceiling

    if category == "performance":
        has_numeric = extracted_data.get("metric_value") is not None
        if has_numeric:
            return 0.60  # 예외: 구체적 수치 포함
        return 0.55  # base ceiling

    return CATEGORY_CEILING.get(category, 0.55)
```

> 이 예외 규칙은 `01_crawling_strategy.md` 3.5절의 `CATEGORY_CEILING` 딕셔너리와 정합된다.
> `CATEGORY_CEILING`의 값은 최대 허용 ceiling이며, 실제 적용은 위 조건을 통과해야 한다.

**`01_crawling_strategy.md` N4 섹션 정합성**:

crawling 전략의 N4 tension 추론 테이블과 이 taxonomy가 정합되도록, crawling 문서의
tension_type 값을 이 taxonomy의 enum으로 통일한다.

| change_type (crawling N4) | tension_type (taxonomy) |
|---|---|
| CEO 교체 | `founder_vs_professional_mgmt` |
| CxO 영입 | `scaling_leadership` |
| 조직개편 | `portfolio_restructuring` |
| 구조조정/감원 | `efficiency_vs_growth` |
| 사업부 분리/합병 | `portfolio_restructuring` |

---

## A7. GraphRAG vs Vector Baseline 비교 실험 계획 [v6 추가]

### 문제

v3 평가에서 "GraphRAG vs 단순 Vector 검색의 ROI 검증"이 제기되었으나, v4, v5에서도
구체적 비교 실험 계획이 수립되지 않았다 (v5 리뷰 5절 미해결 항목).

### 해결: v1 파일럿 후 비교 실험 계획

**실험 설계**:

| 항목 | 내용 |
|---|---|
| 목적 | GraphRAG(Neo4j + MappingFeatures)가 Vector-only 대비 매핑 품질을 유의미하게 개선하는지 검증 |
| 시기 | v1 파일럿 50건 완료 후 |
| 비교 대상 | (A) GraphRAG: 그래프 기반 MappingFeatures 5개 피처 | (B) Vector: JD+이력서 임베딩 cosine similarity |
| 평가 지표 | 매핑 정확도 (Human eval), Precision@5, Recall@5, NDCG |
| 평가 데이터 | 50건 매핑 결과에 대해 채용 전문가 5명의 적합도 평가 (1~5점) |
| 성공 기준 | GraphRAG의 평균 적합도 점수가 Vector-only 대비 +0.5점 이상 |

**Vector Baseline 구성** [v7 수정: A7-1 반영]:

| 항목 | 내용 |
|---|---|
| 임베딩 모델 | `text-multilingual-embedding-002` (Vertex AI) -- GCP 네이티브, 다국어 지원 |
| 입력 방식 | JD 전문 / 이력서 전문 각각 단일 임베딩 (구조화 분할 없음) |
| 유사도 | cosine similarity |
| 검색 방식 | Top-K = 10, reranking 없이 cosine similarity 순위로 산출 |
| 인덱스 | Vertex AI Vector Search (ScaNN 기반 ANN) |

**통제 변수표**:

| 통제 변수 | GraphRAG (A) | Vector Baseline (B) | 동일 여부 |
|---|---|---|---|
| 입력 데이터 (JD) | 동일 50건 | 동일 50건 | 동일 |
| 입력 데이터 (이력서) | 동일 후보 풀 | 동일 후보 풀 | 동일 |
| 블라인드 평가 | 출처 비공개 | 출처 비공개 | 동일 |
| 전처리 (텍스트 정제) | 동일 파이프라인 | 동일 파이프라인 | 동일 |
| 평가자 | 채용 전문가 5명 | 동일 5명 | 동일 |
| 평가 기준 | 1~5점 적합도 | 동일 기준 | 동일 |

**선택적 추가 실험 (B')**:

GraphRAG(A)와의 공정 비교를 위해, Vector + LLM Reranking 조합(B')도 선택적으로 테스트한다.

| 항목 | 내용 |
|---|---|
| 방법 | Vector Top-K=10 결과를 Gemini 2.0 Flash로 reranking |
| 목적 | Vector의 한계가 임베딩 자체의 문제인지, 구조화된 피처(GraphRAG)의 기여인지 분리 |
| 성공 기준 | (A) > (B') > (B)이면 GraphRAG의 구조적 우위 확인, (B') >= (A)이면 구조화 없이 LLM reranking으로 충분 |

**실험 절차**:

1. v1 파일럿에서 50건의 기업-후보 매핑을 GraphRAG로 수행
2. 동일 50건을 Vector-only(임베딩 유사도)로 수행
3. (선택) 동일 50건을 Vector + LLM Reranking(B')으로 수행
4. 채용 전문가 5명이 각 매핑의 적합도를 1~5점 blind 평가
5. 통계 검정(paired t-test)으로 유의미한 차이 검증
6. GraphRAG가 특히 유리한 케이스 / 불리한 케이스 분석

> 이 실험 결과에 따라 v2 이후의 그래프 확장 범위(Company 간 관계 등)를 결정한다.

---

## A8. 추출 프롬프트 확장 로드맵 [v7 추가: C6-1, C6-2 반영]

### 문제

v6 기준으로 필수 페이지/기사 유형(P1~P3, N1, N4)에 대해서는 상세 추출 프롬프트가 완비되었으나, 선택 유형(P4~P6, N2, N3, N5)은 추출 구조만 정의되어 있다. 파일럿에서 필수 유형의 프롬프트가 안정화된 후 선택 유형의 프롬프트를 단계적으로 추가해야 한다.

### 현황: 프롬프트 완비/미비 정리

| 유형 | 우선순위 | 프롬프트 상태 | 비고 |
|---|---|---|---|
| P1 (회사 소개) | 필수 | 완비 | v6 |
| P2 (제품/서비스) | 필수 | 완비 | v6 |
| P3 (채용) | 필수 | 완비 | v6, 광고성 필터 내장 |
| P4 (기술 블로그) | 선택 | **미비** | 추출 구조만 정의 |
| P5 (팀/문화) | 선택 | **미비** | 추출 구조만 정의 |
| P6 (고객 사례) | 선택 | **미비** | 추출 구조만 정의 |
| N1 (투자) | 필수 | 완비 | v6 |
| N2 (제품 런칭) | 필수 | **미비** | 추출 구조만 정의 |
| N3 (M&A) | 선택 | **미비** | 추출 구조만 정의 |
| N4 (조직 변화) | 선택 | 완비 | v6, A6 taxonomy 연동 |
| N5 (실적) | 선택 | **미비** | 추출 구조만 정의 |

### 해결: 4단계 추가 일정

| 단계 | 시기 | 대상 | 전제 조건 |
|---|---|---|---|
| 1단계 | Phase 2 (파일럿) | N2 (제품 런칭), N5 (실적) | P1~P3/N1/N4 프롬프트 안정화 확인 |
| 2단계 | Phase 3 (통합) | N3 (M&A) | N2/N5 프롬프트 검증 완료, A6 taxonomy 연동 필요 |
| 3단계 | Phase 4 초기 (배치) | P4 (기술 블로그) | 홈페이지 크롤러 안정 운영 확인 |
| 4단계 | Phase 4 중기 | P5 (팀/문화), P6 (고객 사례) | P4 프롬프트 검증 완료 |

**우선순위 근거**:
- N2/N5: 필수/선택 카테고리이지만 수집 빈도가 높고, 구조화된 추출이 CompanyContext 보강에 직접 기여
- N3: A6 tension taxonomy와 연동 필요 (`build_vs_buy`, `integration_tension`), N4 프롬프트 패턴 재활용 가능
- P4: `operating_model.facets` 보강에 기여, 블로그 존재 자체가 `process` facet 지지
- P5/P6: 기여도가 가장 낮고, P3와 중복 추출 가능성 있음

### 안정화 판정 기준

각 단계 전환 시 이전 단계 프롬프트의 안정화를 다음 4개 지표로 판정한다:

| 지표 | 기준 | 측정 방법 |
|---|---|---|
| 추출 성공률 | >= 80% | 프롬프트 실행 건수 중 유효 JSON 반환 비율 |
| 팩트 정확도 | >= 85% | Human eval 샘플링 10건에서 추출 사실의 정확도 |
| 광고성 오추출률 | <= 10% | 광고성 표현이 결과에 포함된 비율 |
| JSON 파싱 성공률 | >= 95% | LLM 응답의 JSON 파싱 성공 비율 |

> 4개 지표 중 3개 이상을 충족하면 안정화로 판정하고 다음 단계를 진행한다.

---

## 변경 요약

| # | 항목 | 영향 문서 | 변경 유형 |
|---|---|---|---|
| A1 | ScopeType <-> Seniority 매핑 | `02_candidate_context`, `03_mapping_features` | 추가 (변환 규칙), [v6] FOUNDER HEAD 승격 |
| A2 | Industry 노드 정의 | `04_graph_schema` | 추가 (노드 스키마), [v6] is_regulated 판정 기준 |
| A3 | CompanyTalentSignal 제외 명문화 | 전체 | 명문화 (v2 로드맵) |
| A4 | STAGE_SIMILARITY 전체 매트릭스 | `03_mapping_features` | 수정 (부분 -> 전체), [v6] 캘리브레이션 계획 |
| A5 | Company 간 관계 제외 명문화 | `04_graph_schema` | 명문화 (v2 로드맵) |
| A6 | structural_tensions Taxonomy | `01_company_context`, `01_crawling_strategy` | 추가 (8개 enum), [v6] 배타성 가이드 + related_tensions, [v7] Tier ceiling 예외 |
| A7 | GraphRAG vs Vector 비교 실험 | 전체 | [v6] 신규, [v7] Vector baseline 구체화 + 통제변수 + 선택적 B' 실험 |
| A8 | 추출 프롬프트 확장 로드맵 | `01_crawling_strategy` | [v7] 신규 (4단계 일정 + 안정화 판정 기준) |
