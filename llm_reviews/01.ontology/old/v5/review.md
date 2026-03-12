# v5 온톨로지 리뷰 — 크롤링 전략 & v4 보완 사항

> 리뷰 대상:
> - `ontology/v5/01_crawling_strategy.md` (크롤링 전략 및 실행 계획)
> - `ontology/v5/02_v4_amendments.md` (v4 스키마 보완 사항 A1~A6)
>
> 리뷰 기준: v4 문서 4건 (`01_company_context`, `02_candidate_context`, `03_mapping_features`, `04_graph_schema`) + v3 평가서 + 기존 크롤링 리뷰(`ontology/review/crawling_review.md`)
>
> 리뷰일: 2026-03-08

---

## 1. 전체 평가

v5는 **두 가지 역할**을 수행한다:
1. v4에서 미구축 상태였던 T3/T4 크롤링의 **구체적 실행 전략** 수립
2. v3 평가 및 v4 설계에서 식별된 **6개 갭을 패치**

전체적으로 v4의 "무엇을 채워야 하는가"에 대해 "어떻게 채울 것인가"를 잘 보완했으며, amendments는 v3→v4 전환 과정에서 누락된 항목들을 체계적으로 해소하고 있다.

| 평가 영역 | 점수 (5점) | 코멘트 |
|---|---|---|
| 크롤링 전략 완성도 | 4.0 | 필드-소스 매핑, 파이프라인, 신뢰도 보정 등 실행 가능 수준 |
| v4 Amendments 품질 | 4.5 | 6개 갭 모두 구체적 해결책 제시, 코드 수준 명시 |
| v4 문서와의 정합성 | 4.0 | 대부분 잘 정합되나 일부 미세 갭 존재 |
| 실행 가능성 | 3.5 | Phase 0~4 계획은 현실적이나 일부 전제 조건 검증 필요 |
| 로드맵 일관성 | 4.5 | v1/v1.1/v2 단계 구분이 문서 전반에 걸쳐 일관적 |
| **종합** | **4.0** | v4를 실행 가능한 수준으로 끌어올리는 좋은 보완 문서 |

---

## 2. 크롤링 전략 리뷰 (`01_crawling_strategy.md`)

### 2.1 잘된 점

| 항목 | 설명 |
|---|---|
| 문제 정의 명확 | 1절에서 "JD+NICE만으로는 채울 수 없는 필드"를 표로 정리하여, 크롤링의 ROI를 즉시 파악 가능 |
| 페이지 유형 타겟팅 | P1~P6으로 분류하고 필수/선택을 구분, 무분별한 전체 크롤링을 방지 |
| 추출 프롬프트 예시 | P1(회사 소개) 추출 프롬프트가 구체적이고, 광고성 필터링 주의사항까지 포함 |
| 뉴스 기사 유형 분류 | N1~N6으로 체계화하고 우선순위/기여 필드를 명시 |
| 신뢰도 다층 보정 | PR성 감쇠, 기사 나이 감쇠, 추측성 표현 감쇠 등 5단계 보정 체계 |
| 소스 간 충돌 해결 | Tier 우선순위 + confidence 하향 + contradiction 기록 — 보수적이고 안전한 설계 |
| 비용 추정 현실적 | 1,000기업 기준 월 ~$107, GCP 네이티브 스택 활용으로 비용 최적화 |

### 2.2 우려 사항 및 제안

#### [C-1] P2~P6 추출 프롬프트 누락 (중요도: 높음)

P1(회사 소개) 페이지에 대해서만 상세 추출 프롬프트가 제공되어 있다. P2(제품/서비스), P3(채용), P4(블로그) 등은 추출 대상 구조만 정의하고 프롬프트가 없다.

**영향**: Phase 1-4(LLM 추출 모듈) 구현 시 프롬프트 설계를 처음부터 해야 하며, 추출 품질의 기준선이 불분명해진다.

**제안**: 최소한 필수 페이지(P2, P3)에 대한 추출 프롬프트 예시를 추가. 특히 P3(채용 페이지)는 `operating_model` facets 보강의 핵심 소스이므로, 광고성 필터링(`NOISE_PATTERNS`)과 결합된 프롬프트가 중요하다.

#### [C-2] 뉴스 추출 프롬프트도 N1만 제공 (중요도: 중간)

N1(투자 유치)에 대해서만 상세 프롬프트가 있고, N2~N5는 추출 구조만 정의되어 있다. N4(조직/경영 변화)는 `structural_tensions` 추론의 핵심 소스인데 프롬프트가 없다.

**제안**: N4에 대해 tension_type taxonomy(A6)를 활용한 추출 프롬프트를 추가. LLM이 A6의 8개 enum에서 선택하도록 유도하는 구조가 필요하다.

#### [C-3] 홈페이지 URL 발견 전략의 구체성 부족 (중요도: 중간)

2.3절에서 "sitemap.xml 파싱 또는 메인 페이지에서 링크 탐색"이라고 기술했으나:

- sitemap.xml이 없는 기업(한국 중소 스타트업 다수)의 fallback 전략이 불분명
- BFS depth 2에서 P1~P6을 식별하는 URL 패턴 매칭의 한국어 대응이 미비 (예: `/채용`, `/소개`, `/회사소개`)
- 서브도메인 처리 정책 부재 (예: `careers.company.com`, `blog.company.com`)

**제안**: URL 발견 우선순위를 다음과 같이 명시:
1. `sitemap.xml` → 2. 메인 페이지 nav/footer 링크 파싱 → 3. BFS depth 2 → 4. 한국어 URL 패턴 딕셔너리 매칭

```python
KO_URL_PATTERNS = {
    "about": ["소개", "회사소개", "회사", "기업소개", "about"],
    "careers": ["채용", "인재채용", "채용안내", "recruit", "careers", "jobs"],
    "product": ["제품", "서비스", "솔루션", "product", "service"],
    # ...
}
```

#### [C-4] 네이버 뉴스 API의 본문 크롤링 전략 상세 부족 (중요도: 중간)

3.4절에서 "본문은 funding/org_change 카테고리만 link 추가 크롤링"이라고 했으나:

- 네이버 뉴스 link가 가리키는 원본 언론사 사이트의 크롤링 정책(robots.txt)을 각각 확인해야 하는 오버헤드
- 언론사별 HTML 구조가 다양하여 본문 추출 품질이 불안정할 수 있음
- `Readability` 알고리즘이 한국 언론사 사이트(광고 과다)에서 잘 작동하는지 검증 필요

**제안**: 파일럿에서 주요 언론사 10곳의 본문 추출 성공률을 측정하고, 실패율이 높으면 네이버 뉴스 캐시 페이지(`news.naver.com/...`) 활용을 검토.

#### [C-5] CompanyContext 통합 시 evidence 추적 체계 (중요도: 중간)

4.2절에서 필드별 소스 우선순위를 잘 정의했으나, **크롤링 결과가 CompanyContext에 반영될 때 evidence 구조가 어떻게 확장되는지** 명시가 부족하다.

v4 `01_company_context.md`의 Evidence 통합 모델(`source_type` enum)에는 `crawl_site`과 `crawl_news`가 이미 정의되어 있으므로 호환성은 있지만, 크롤링 evidence의 `source_id` 네이밍 컨벤션(예: `crawl_site_{company_id}_{page_type}`, `crawl_news_{article_id}`)을 명시해야 한다.

#### [C-6] 재크롤링 시 데이터 버저닝 전략 미비 (중요도: 낮음)

30일 주기 재크롤링 시 이전 데이터와의 관계가 불명확하다:
- GCS에 `latest` symlink가 있지만, BigQuery `homepage_extracted` 테이블은 `crawl_date`로 구분
- 이전 크롤링과 현재 크롤링 결과가 달라졌을 때 CompanyContext의 confidence를 어떻게 갱신하는지 미정의
- 변경 감지(diff) 로직 없이 매번 전체 재추출하면 LLM 비용 낭비

**제안**: 원본 HTML의 해시 비교로 변경 감지 후, 변경된 페이지만 재추출하는 증분 전략을 추가.

---

## 3. v4 Amendments 리뷰 (`02_v4_amendments.md`)

### 3.1 전체 평가

6개 amendment 모두 v3 평가서와 v4 설계 과정에서 식별된 실제 갭을 해결하고 있으며, 각각 코드 수준의 구체적 해결책을 제시한다. 특히 A4(STAGE_SIMILARITY 전체 매트릭스)와 A6(structural_tensions Taxonomy)는 구현 시 즉시 활용 가능한 수준이다.

### 3.2 Amendment별 리뷰

#### A1: ScopeType <-> Seniority 매핑 — 양호 (개선 1건)

**잘된 점**: v4 `03_mapping_features.md` F5의 `SENIORITY_ORDER.get(latest_exp.scope_type, 0)` 코드가 scope_type과 seniority 체계 불일치 문제를 가지고 있었는데, 이를 정확히 짚고 변환 함수를 제공했다.

**[A1-1] FOUNDER의 경력 연수 기반 HEAD 승격 규칙 누락 (중요도: 낮음)**

```python
elif scope == "FOUNDER":
    return "LEAD"  # 보수적 매핑, 경력 연수에 따라 HEAD 가능
```

주석에 "경력 연수에 따라 HEAD 가능"이라 했으나, 실제 분기 로직이 없다. 창업 경험 10년+ 대표의 경우 LEAD 매핑은 과소평가일 수 있다.

**제안**:
```python
elif scope == "FOUNDER":
    if candidate_ctx.role_evolution.total_experience_years >= 10:
        return "HEAD"
    return "LEAD"
```

#### A2: Industry 노드 정의 — 양호

**잘된 점**: v4 `04_graph_schema.md`에서 `IN_INDUSTRY` 관계가 있으면서 `:Industry` 노드 정의가 누락된 것을 정확히 보완했다. NICE 업종 코드 기반 마스터 데이터 생성 전략이 적절하다.

**[A2-1] `is_regulated` 판정 기준 미정의 (중요도: 낮음)**

`is_regulated: BOOLEAN`이 있지만 어떤 industry_code가 regulated인지 판정하는 기준/목록이 없다. v4 `01_company_context.md`의 `is_regulated_industry` 필드와 동일한 문제. Rule 기반 매핑 테이블이 필요하다.

#### A3: CompanyTalentSignal 제외 명문화 — 우수

**잘된 점**: 의도적 제외를 3가지 이유로 명문화하고 v2 로드맵에 배치한 것은 설계 의사결정의 추적성을 높인다. 특히 "편향 리스크"를 핵심 이유로 든 것은 v3의 독립성 원칙에 정확히 부합한다.

v2에서 "weight 제한: max 0.05"로 제한한 것도 보수적이고 합리적이다.

#### A4: STAGE_SIMILARITY 전체 매트릭스 — 우수

**잘된 점**: v4에서 일부만 정의되고 나머지가 기본값 0.2로 처리되던 것을 **비대칭 전체 4x4 매트릭스**로 확정했다. 비대칭 설계 근거("GROWTH 기업은 EARLY 경험자를 어느 정도 인정")가 채용 현장의 직관과 일치한다.

**[A4-1] 매트릭스 값의 검증/캘리브레이션 계획 부재 (중요도: 중간)**

0.50, 0.30, 0.15 등의 수치가 어떤 근거(전문가 판단? 데이터 분석?)에서 나왔는지 불명확하다. v1 파일럿 이후 Human evaluation 데이터로 이 매트릭스를 캘리브레이션하는 계획이 필요하다.

**제안**: v4 `03_mapping_features.md` 7.1절의 "Human evaluation (5명), 매핑 50건"에서 stage_match 피처의 스코어 분포를 분석하여 매트릭스 값을 조정하는 단계를 추가.

#### A5: Company 간 관계 미포함 이유 — 양호

**잘된 점**: 제외 이유 3가지가 합리적이고, v2 로드맵에 구체적 관계 유형과 데이터 소스를 매핑했다. 특히 `INVESTED_BY` 관계를 v1.1(TheVC API 연동)에 배치한 것은 크롤링 전략의 투자 정보 활용과 일관적이다.

**[A5-1] INVESTED_BY의 도입 시기와 크롤링 전략의 정합 (중요도: 낮음)**

A5에서는 `INVESTED_BY`를 v1.1에 배치했고, 크롤링 전략에서도 "TheVC API (투자 정보 보강)"을 v1 권장 조합에 포함했다. 그러나 v4 `01_company_context.md` 7절(데이터 수집 우선순위)에서는 투자 DB API 연동을 1순위로 두면서도 실행 계획에는 명시적 Phase가 없다.

**제안**: 크롤링 전략의 Phase 0-2에 "TheVC API 연동" 태스크를 명시적으로 추가.

#### A6: structural_tensions Taxonomy 확정 — 우수 (개선 1건)

**잘된 점**: v3의 3개 예시에서 8개 enum으로 확장하되 과도하지 않은 적정 수준이다. TypeScript 정의, JSON 예시, 크롤링 N4 섹션과의 정합 테이블까지 제공하여 구현 즉시 활용 가능하다.

**[A6-1] tension_type 간 배타성/중복 정리 필요 (중요도: 중간)**

일부 tension_type 간 경계가 모호하다:

| 조합 | 모호성 |
|---|---|
| `efficiency_vs_growth` + `portfolio_restructuring` | 사업부 정리가 효율화의 일환일 때 어느 것을 선택? |
| `scaling_leadership` + `founder_vs_professional_mgmt` | CxO 영입이 창업자 경영 전환의 일환일 때? |
| `build_vs_buy` + `integration_tension` | M&A 후 통합이 buy 전략의 결과일 때? |

**제안**: 각 tension_type에 대해 "이 타입이 아닌 경우" 가이드를 추가하거나, 복수 tension 할당을 허용하되 `primary_tension`을 지정하는 구조로 변경.

```typescript
interface StructuralTension {
  tension_type: TensionType;        // primary
  related_tensions?: TensionType[]; // secondary (있으면)
  description: string;
  confidence: number;
  evidence: Evidence[];
}
```

---

## 4. 문서 간 정합성 검증

### 4.1 v5 내부 정합성 (01 <-> 02)

| # | 항목 | 상태 | 설명 |
|---|---|---|---|
| I-1 | N4 tension_type ↔ A6 taxonomy | **정합** | 02의 A6 마지막 테이블에서 명시적으로 매핑 |
| I-2 | 크롤링 결과 → structural_tensions 활성화 ↔ A6 스키마 | **정합** | A6의 JSON 예시가 크롤링 소스를 사용 |
| I-3 | N6(기술/제품 전략) v2 이동 ↔ 검색 쿼리 | **정합** | `build_news_queries`에 N6 미포함, 전략 문서에서 v2로 명시 |

### 4.2 v5 ↔ v4 정합성

| # | 항목 | 상태 | 설명 |
|---|---|---|---|
| V-1 | 크롤링 confidence ceiling ↔ v4 Tier 정의 | **정합** | T3=0.60, T4=0.55 일관 |
| V-2 | Evidence source_type enum | **정합** | `crawl_site`, `crawl_news` 양쪽 일치 |
| V-3 | A1 seniority 매핑 ↔ F5 role_fit | **정합** | A1이 F5의 `SENIORITY_ORDER.get(latest_exp.scope_type)` 수정 방법 명시 |
| V-4 | A2 Industry 노드 ↔ graph_schema `IN_INDUSTRY` | **정합** | 누락된 노드 정의를 보완 |
| V-5 | A4 매트릭스 ↔ F1 stage_match | **정합** | 부분 매트릭스를 전체로 대체, 기본값 fallback 제거 |
| V-6 | A6 tension TypeScript ↔ CompanyContext schema | **부분 갭** | 아래 V-6 상세 참조 |

**[V-6] A6의 StructuralTension 인터페이스 vs v4 CompanyContext JSON**

A6에서 정의한 `StructuralTension` 인터페이스에 `evidence: Evidence[]`가 있지만, v4 `01_company_context.md`의 JSON 예시에서 `structural_tensions`는 단순히 `null`로만 표시되어 있다. A6의 JSON 예시는 제공되었으나, v4 CompanyContext의 3절 JSON 스키마 자체를 업데이트하라는 명시적 지침이 없다.

**제안**: 02_v4_amendments.md의 변경 요약 테이블에 "v4 JSON 스키마 예시 업데이트 필요" 항목을 추가하거나, v5에서 통합 JSON 스키마를 별도 문서로 제공.

### 4.3 v5 ↔ 기존 크롤링 리뷰 정합성

기존 `ontology/review/crawling_review.md`에서 제기된 이슈의 반영 여부:

| 리뷰 이슈 | v5 반영 상태 | 비고 |
|---|---|---|
| [S-1] `is_actionable_signal` OR 조건 | **미반영** | 여전히 `has_number or has_specific_action` |
| [S-2] N6 검색 쿼리 누락 | **해결** | N6을 v2로 이동, 의도적 제외 명시 |
| [S-3] 카테고리별 confidence ceiling | **미반영** | 여전히 전체 0.55 고정 |
| [S-4] 짧은 기사 관련성 필터 | **미반영** | 파일럿 중 검증 항목으로 유지 |
| [S-5] 중복 제거 임계값 | **미반영** | 파일럿 중 검증 항목으로 유지 |

**코멘트**: S-1, S-3은 파일럿 전 반영이 권장되었으나 아직 미반영 상태. 파일럿에서 검증 후 반영 예정이라면 문서에 해당 의도를 명시하는 것이 좋다.

---

## 5. 누락 항목 분석

v3 평가서에서 제기되었으나 v5에서도 해결되지 않은 항목:

| v3 평가 항목 | v4 해결 여부 | v5 해결 여부 | 현재 상태 |
|---|---|---|---|
| 3.1 기업 데이터 가용성 | **해결** (소스 Tier 계층화) | **보강** (크롤링 전략) | 해결됨 |
| 3.2 두 문서 간 정합성 | **해결** (통합 스키마 v4) | — | 해결됨 |
| 3.3 LLM 추출 품질 | 프롬프트 설계 원칙 제시 | **부분** (P1, N1 프롬프트만) | 추가 프롬프트 필요 |
| 3.4 MappingFeatures 계산 방식 | **해결** (pseudo-code) | A1, A4로 보강 | 해결됨 |
| 3.5 PastCompanyContext 역산 | **해결** (현재 시점 기반 v1) | — | 해결됨 |
| 3.6 GraphRAG ROI 검증 | 미해결 | 미해결 | **여전히 미해결** |
| confidence 캘리브레이션 | **해결** (v4 §5) | — | 해결됨 |
| Company 측 그래프 모델링 | **해결** (Organization, Vacancy 노드) | A2, A5로 보강 | 해결됨 |
| Skill/Role 정규화 전략 | **해결** (동의어 사전) | — | 해결됨 |

**주목할 미해결 항목**: GraphRAG vs 단순 Vector 검색의 ROI 검증 계획이 v3 평가 이후 어떤 문서에서도 구체화되지 않았다. v4 `04_graph_schema.md` 6절에서 "Neo4j AuraDB 권장"이라 했지만, baseline 비교 실험 계획이 없다.

---

## 6. 추가 발견 사항

### [D-1] BigQuery 스키마 이중 정의 (중요도: 중간)

크롤링 전략 5.2절에 `crawl.homepage_extracted`, `crawl.news_extracted`, `crawl.company_crawl_summary` 3개 테이블이 정의되어 있고, v4 `03_mapping_features.md` 5.2절에 `context.mapping_features`, `context.company_context`, `context.candidate_context` 3개 테이블이 정의되어 있다. 이 6개 테이블 간의 **데이터 플로우**가 명시되지 않았다.

특히 `crawl.company_crawl_summary` → `context.company_context`로의 데이터 흐름(크롤링 결과가 CompanyContext에 어떻게 합류하는지)이 파이프라인 수준에서 정의되어야 한다.

### [D-2] 크롤링 데이터의 Graph 반영 경로 미정의 (중요도: 중간)

크롤링으로 수집된 데이터가 BigQuery에 저장되는 것은 명확하나, **Neo4j Graph에 어떻게 반영되는지** 경로가 없다. 예를 들어:
- 크롤링으로 얻은 `product_description` → Organization 노드의 속성으로 추가?
- 뉴스에서 추출한 `structural_tensions` → 새로운 노드/관계로 표현?

v4 `04_graph_schema.md`의 Organization 노드에는 크롤링 관련 속성이 없으므로, 크롤링 보강 후 그래프 스키마 확장이 필요하다.

### [D-3] operating_model facets 보강 시 기존 JD 스코어와의 병합 규칙 (중요도: 중간)

크롤링 전략 2.2절의 P3(채용 페이지)에서 operating_model facets를 보강하는데:
- JD에서 추출한 facet score(v4 기준 `speed: 0.72, confidence: 0.45`)
- 크롤링에서 추출한 facet score(예: `speed: 0.60, confidence: 0.35`)

이 두 소스의 병합 규칙이 명시되지 않았다. 4.2절의 통합 규칙에서 "JD 기준, 홈페이지로 보강"이라 했으나, 구체적으로:
- 가중 평균? (`weighted_avg = jd_score * jd_conf + crawl_score * crawl_conf`)
- JD 우선, 크롤링은 confidence 보정만? (`confidence = min(jd_conf + 0.10, ceiling)`)
- 충돌 시? (JD `speed: 0.72` vs 크롤링 `speed: 0.30`)

---

## 7. 권장 사항

### 즉시 조치 (파일럿 전)

| # | 항목 | 근거 |
|---|---|---|
| 1 | P2(제품), P3(채용) 추출 프롬프트 추가 | [C-1] 필수 페이지 추출 품질 기준 필요 |
| 2 | N4(조직변화) 추출 프롬프트에 A6 taxonomy 연동 | [C-2] tension_type 추론의 핵심 |
| 3 | 한국어 URL 패턴 딕셔너리 추가 | [C-3] 국내 스타트업 크롤링 커버리지 |
| 4 | 기존 크롤링 리뷰 [S-1] 반영 | 광고성 필터링 정확도 |

### 파일럿 중 검증

| # | 항목 | 근거 |
|---|---|---|
| 5 | 언론사 본문 추출 성공률 측정 | [C-4] 네이버 link 크롤링 품질 |
| 6 | STAGE_SIMILARITY 매트릭스 Human eval | [A4-1] 수치 캘리브레이션 |
| 7 | tension_type 간 모호성 케이스 수집 | [A6-1] taxonomy 정제 |
| 8 | 카테고리별 confidence ceiling 차등 검증 | [S-3] funding은 ceiling 상향 검토 |

### v1 운영 전

| # | 항목 | 근거 |
|---|---|---|
| 9 | BigQuery 6개 테이블 간 데이터 플로우 정의 | [D-1] 크롤링→Context 파이프라인 |
| 10 | 크롤링 데이터의 Graph 반영 스키마 확장 | [D-2] Organization 노드 확장 |
| 11 | facet score 병합 규칙 확정 | [D-3] JD+크롤링 통합 |
| 12 | GraphRAG vs Vector baseline 비교 실험 설계 | v3 평가 3.6 미해결 |
| 13 | evidence source_id 네이밍 컨벤션 확정 | [C-5] 추적 가능성 |

---

## 8. 요약

v5 문서는 v4의 **실행 가능성을 한 단계 끌어올린** 좋은 보완 문서다.

**크롤링 전략**은 "무엇을, 어디서, 어떻게 수집하는가"를 체계적으로 정의했으며, CompanyContext의 fill_rate를 0.71 → 0.85+로 올리겠다는 목표가 현실적이다. 다만 추출 프롬프트가 P1/N1에만 제공되어 있어, 나머지 유형에 대한 보완이 필요하다.

**v4 Amendments**는 6개 갭 모두를 코드 수준으로 해결했으며, 특히 A4(STAGE_SIMILARITY)와 A6(tension taxonomy)는 즉시 구현에 투입 가능한 품질이다. A1의 FOUNDER 승격 규칙과 A6의 tension_type 배타성 정리가 소소한 개선 포인트다.

전체적으로 **파일럿 실행에 충분한 수준**이며, 위 권장사항 중 즉시 조치 4건을 반영하면 파일럿의 품질이 크게 향상될 것이다.
