# v4 스키마 보완 사항 (Amendments)

> v4 평가에서 식별된 5개 보완 권장사항 + crawling 전략에서 발견된 1개 정합성 이슈를 해결.
> 이 문서의 내용은 v4 문서(01~04)에 대한 **패치**로, v5 이후 스키마에 반영한다.
>
> 작성일: 2026-03-08

---

## A1. ScopeType ↔ Seniority 매핑 테이블

### 문제

CandidateContext의 `scope_type`(`IC / LEAD / HEAD / FOUNDER / UNKNOWN`)과
CompanyContext vacancy의 `seniority`(`JUNIOR / MID / SENIOR / LEAD / HEAD / UNKNOWN`)는
서로 다른 체계를 사용한다. `03_mapping_features.md`의 `role_fit` 계산에서 이 두 체계를
직접 비교하는데, 변환 규칙이 없어 구현 시 모호하다.

### 해결: 명시적 매핑 테이블

**scope_type → seniority 변환**:

| scope_type (Candidate) | 대응 seniority 범위 | 비고 |
|---|---|---|
| `IC` | `JUNIOR`, `MID`, `SENIOR` | 경력 연수로 세분화 |
| `LEAD` | `SENIOR`, `LEAD` | Lead 경험자는 Senior 이상 |
| `HEAD` | `HEAD` | 직접 대응 |
| `FOUNDER` | `LEAD`, `HEAD` | 창업 경험은 리더십 동등 |
| `UNKNOWN` | — | 매핑 불가, role_fit에서 경력 연수 기반 fallback |

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
    if scope == "IC":
        return ic_to_seniority(candidate_ctx.role_evolution.total_experience_years)
    elif scope == "LEAD":
        return "LEAD"
    elif scope == "HEAD":
        return "HEAD"
    elif scope == "FOUNDER":
        return "LEAD"  # 보수적 매핑, 경력 연수에 따라 HEAD 가능
    else:
        return "UNKNOWN"
```

**v4 `03_mapping_features.md` F5 수정 사항**:

기존 `SENIORITY_ORDER`에 scope_type 변환을 선행 적용:

```python
# 기존 (v4)
latest_level = SENIORITY_ORDER.get(latest_exp.scope_type, 0)

# 수정 (v5)
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
- 동일 업종의 기업들이 하나의 Industry 노드를 공유 → "같은 산업의 기업" 그래프 탐색 가능

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
| v2 | 도입 검토 — 표본 크기 >= 20인 기업 대상 파일럿 |
| v2.1+ | MappingFeatures의 보조 feature로 통합 (weight 제한: max 0.05) |

---

## A4. STAGE_SIMILARITY 전체 매트릭스

### 문제

`03_mapping_features.md`의 F1(stage_match)에서 `STAGE_SIMILARITY` 매트릭스가
일부만 정의되어 있고 나머지는 기본값 0.2로 처리된다. 구현 시 모호함이 발생한다.

### 해결: 전체 4×4 매트릭스 확정

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
  - `GROWTH→EARLY`(0.50) > `EARLY→GROWTH`(0.30): GROWTH 기업은 초기 스타트업 경험자를
    "성장기를 겪어봤다"로 어느 정도 인정. 반면 EARLY 기업이 GROWTH 경험자를 찾는 것은
    오버스펙이므로 낮은 유사도.
  - `SCALE→GROWTH`(0.50) > `GROWTH→SCALE`(0.40): 유사한 논리.
  - `MATURE→SCALE`(0.45) = `SCALE→MATURE`(0.45): 대기업 ↔ 스케일업 간 이동은 양방향 적합.
- **원거리 stage**: 0.10~0.20 (EARLY ↔ MATURE는 맥락이 크게 다름)

**v4 코드 수정**:

```python
# v5 확정 매트릭스 (v4의 부분 정의 대체)
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
# 기본값 fallback 제거 — 모든 조합이 명시됨
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

**TypeScript 정의**:

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
  description: string;
  confidence: number;         // source ceiling 적용 후
  evidence: Evidence[];
}
```

**CompanyContext 필드 수정**:

```json
// v4 (기존)
"structural_tensions": null

// v5 (수정)
"structural_tensions": [
  {
    "tension_type": "efficiency_vs_growth",
    "description": "최근 30% 인력 감축 발표, 성장 투자 축소 시사",
    "confidence": 0.45,
    "evidence": [
      {
        "source_id": "news_article_001",
        "source_type": "crawl_news",
        "span": "A사는 전사 구조조정을 통해 30%의 인력을 감축한다고 밝혔다",
        "confidence": 0.50,
        "extracted_at": "2026-03-01T00:00:00Z"
      }
    ]
  }
]
```

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

## 변경 요약

| # | 항목 | 영향 문서 | 변경 유형 |
|---|---|---|---|
| A1 | ScopeType ↔ Seniority 매핑 | `02_candidate_context`, `03_mapping_features` | 추가 (변환 규칙) |
| A2 | Industry 노드 정의 | `04_graph_schema` | 추가 (노드 스키마) |
| A3 | CompanyTalentSignal 제외 명문화 | 전체 | 명문화 (v2 로드맵) |
| A4 | STAGE_SIMILARITY 전체 매트릭스 | `03_mapping_features` | 수정 (부분 → 전체) |
| A5 | Company 간 관계 제외 명문화 | `04_graph_schema` | 명문화 (v2 로드맵) |
| A6 | structural_tensions Taxonomy | `01_company_context`, `01_crawling_strategy` | 추가 (8개 enum) |
