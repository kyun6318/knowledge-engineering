# 크롤링 전략 & GCP 구현 계획 리뷰

> 리뷰 대상:
> - `ontology/v5/01_crawling_strategy.md` (크롤링 전략)
> - `ml-platform/plans/crawling-gcp-plan.md` (GCP 구현 계획)
>
> 리뷰일: 2026-03-08

---

## 1. 전체 평가

두 문서는 **전략(What/Why) → 구현(How/Where)** 구조로 잘 분리되어 있고, GCP 구현 계획이 전략 문서의 설계를 충실히 반영하고 있다. 특히 v1.1 수정(F1~F7)은 실제 구현 시 부딪힐 현실적 문제를 잘 반영했다.

**강점**: 필드별 소스 매핑이 명확하고, confidence 보정 체계가 구체적이며, 비용 추정이 현실적이다.

---

## 2. 전략 문서 리뷰 (`01_crawling_strategy.md`)

### 2.1 잘된 점

| 항목 | 설명 |
|---|---|
| 필드-소스 매핑 | CompanyContext 필드별로 어떤 크롤링 소스가 기여하는지 표로 명확히 정리 |
| 광고성 필터링 | `NOISE_PATTERNS` / `SIGNAL_PATTERNS` 분리가 실용적 |
| 뉴스 신뢰도 보정 | PR성 감쇠, 기사 나이 감쇠, 추측성 감쇠 등 다층 보정 체계 |
| 충돌 해결 로직 | 소스 간 충돌 시 Tier 우선순위 + confidence 하향이 보수적이고 안전 |

### 2.2 우려 사항 및 제안

#### [S-1] `is_actionable_signal` 로직의 OR 조건 문제 (중요도: 높음)

```python
# 현재: has_number OR has_specific_action
return has_number or has_specific_action
```

**문제**: 숫자가 포함되기만 하면 모든 텍스트가 시그널로 인정된다. "직원 300명이 행복한 일터에서 함께 성장" 같은 문장도 통과한다.

**제안**: NOISE_PATTERNS 체크가 먼저 실행되므로 어느 정도 걸러지지만, `has_number`만으로 통과하는 경우 해당 숫자가 **운영 행동과 관련된 수치**인지 추가 검증이 필요하다.

```python
def is_actionable_signal(text, pattern):
    if any(noise in text for noise in NOISE_PATTERNS):
        return False
    has_specific_action = any(p in text for p in pattern)
    if has_specific_action:
        return True
    # 숫자만 있는 경우: 운영 관련 컨텍스트 동반 시에만 인정
    has_number = bool(re.search(r'\d+', text))
    has_operational_context = any(w in text for w in ["주기", "주", "일", "배포", "리뷰", "회의"])
    return has_number and has_operational_context
```

#### [S-2] N6(기술/제품 전략) 기사 유형이 검색 쿼리에 누락 (중요도: 중간)

전략 문서 3.1절에 N6(기술/제품 전략)이 정의되어 있으나, 3.3절 `build_news_queries`에 N6 검색 쿼리가 빠져 있다. 의도적 제외인지 누락인지 명시 필요.

#### [S-3] 뉴스 confidence ceiling이 0.55로 고정 (중요도: 중간)

```python
return min(c, 0.55)  # T4 source ceiling
```

복수 언론사 교차 확인 + 수치 동반 + 최신 기사(< 3개월)인 경우에도 0.55를 넘을 수 없다. 투자 유치 기사처럼 팩트 기반이 강한 N1 카테고리는 ceiling을 0.65까지 올려도 될 수 있다.

**제안**: 카테고리별 ceiling 차등 적용.

```python
CATEGORY_CEILING = {
    "funding": 0.65,    # 팩트 기반 (금액, 투자사 등 검증 가능)
    "product": 0.55,
    "org_change": 0.55,
    "performance": 0.60, # 수치 기반
    "mna": 0.55,
}
```

#### [S-4] `filter_irrelevant`의 본문 3회 등장 기준 (중요도: 낮음)

짧은 기사(200자 이하)에서는 회사명이 3회 등장하기 어렵다. 본문 길이 대비 비율로 전환하거나, 짧은 기사에 대한 별도 기준이 필요하다.

#### [S-5] 제목 유사도 기반 중복 제거의 임계값 (중요도: 낮음)

cosine similarity 0.85는 제목이 거의 동일한 경우만 잡는다. 같은 사건을 다른 각도로 보도한 기사는 중복으로 잡히지 않을 수 있다. 이는 의도일 수 있으나, 같은 투자 유치를 5개 매체가 각각 다른 제목으로 보도하면 중복 기사가 5건 남는다. 본문 유사도 또는 핵심 엔티티(금액, 투자사) 기반 클러스터링 보조가 필요할 수 있다.

---

## 3. GCP 구현 계획 리뷰 (`crawling-gcp-plan.md`)

### 3.1 잘된 점

| 항목 | 설명 |
|---|---|
| F1~F7 수정 | 네이버 API 본문 미제공, 배치 크기 조정, GCS 파일 전달 등 현실 문제 반영 |
| 비용 추정 | 파일럿 ~$1, 월간 ~$12로 매우 저렴한 구성 |
| 파일럿 우선 접근 | Cloud Workflows를 운영 단계로 미루고 Python 스크립트로 시작하는 점 |
| Gemini QPM throttle | 무료 티어 15 QPM 내에서 안전 마진 확보 (5초 간격 = 12 QPM) |

### 3.2 우려 사항 및 제안

#### [G-1] 홈페이지 크롤러의 SPA 렌더링 대기 부족 (중요도: 높음)

```python
page.goto(domain_url, timeout=15000, wait_until="domcontentloaded")
```

`domcontentloaded`는 HTML 파싱 완료 시점이지, React/Vue의 데이터 렌더링 완료가 아니다. 전략 문서에서는 "JavaScript 렌더링 최대 10초 대기"를 정책으로 명시했는데, 구현에서는 `domcontentloaded`만 기다린다.

**제안**:
```python
page.goto(url, timeout=15000, wait_until="domcontentloaded")
# SPA 렌더링 대기: 본문 콘텐츠가 나타날 때까지 최대 10초
try:
    page.wait_for_selector("main, article, #content, .content", timeout=10000)
except:
    pass  # 셀렉터 없으면 현재 상태로 진행
```

#### [G-2] 뉴스 수집기에서 product/performance 본문 미수집 결정의 리스크 (중요도: 중간)

```python
# product/performance는 description만으로도 market_segment 등 추출 가능하므로 스킵
```

네이버 API description은 100~200자 요약이다. `product_description` 보강이 핵심 KPI(60%+ 활성화)인데, 100~200자 요약으로 충분한 `product_description`을 생성할 수 있을지 의문이다.

**제안**: 파일럿에서 product 카테고리도 본문 크롤링을 해보고, description만 vs 본문 포함의 추출 품질 차이를 비교한 뒤 결정해도 늦지 않다. 비용 영향은 미미하다(기사당 1초 sleep + HTTP GET 1회).

#### [G-3] LLM 추출기에서 product/performance 카테고리 스킵 (중요도: 중간)

```python
def extract_from_article(company_id, category, text):
    ...
    else:
        return None  # product/performance는 description만으로 처리, LLM 추출 스킵
```

LLM 추출을 스킵하면 product/performance 뉴스에서 `market_segment`, `growth_narrative` 등을 추출할 수 없다. 전략 문서(4.2절)에서 뉴스(N2)가 `product_description`과 `market_segment`의 2순위 소스로 정의되어 있는데, 구현에서 이를 활용하지 않는 것은 전략과의 갭이다.

**제안**: 간단한 프롬프트라도 추가하여 description에서 `market_segment`, `product_name` 정도는 추출.

```python
NEWS_PRODUCT_PROMPT = """아래 제품/서비스 관련 뉴스 요약에서 정보를 추출하세요.
1. product_name: 제품/서비스명
2. market_segment: 타겟 시장
3. traction_data: 초기 성과 수치 (있으면)
JSON 형식으로 응답하세요.
[텍스트]
{text}"""
```

#### [G-4] `gemini_extract`에서 JSONDecodeError 시 재시도 없이 즉시 반환 (중요도: 중간)

```python
except json.JSONDecodeError:
    return {"_error": "JSON parse failed", "_raw": response.text[:500]}
```

`response_mime_type="application/json"`을 설정했지만, Gemini가 가끔 markdown fence(```json ... ```)로 감싸서 반환하는 경우가 있다. JSON 파싱 실패 시 fence 제거 후 재파싱을 시도해볼 수 있다.

**제안**:
```python
except json.JSONDecodeError:
    # markdown fence 제거 후 재시도
    cleaned = re.sub(r'^```json?\s*|\s*```$', '', response.text.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"_error": "JSON parse failed", "_raw": response.text[:500]}
```

#### [G-5] BigQuery 스키마와 전략 문서 스키마의 차이 (중요도: 낮음)

전략 문서(5.2절)의 `crawl.homepage_extracted` 테이블과 GCP 계획의 `crawl.extracted_fields` 테이블 구조가 다르다:
- 전략: `homepage_extracted` + `news_extracted` (소스별 분리)
- GCP: `extracted_fields` (소스 통합, `source_type` 컬럼으로 구분)

통합 테이블이 더 간결하긴 하나, 전략 문서와의 의도적 차이인지 명시가 필요하다. 또한 통합 테이블에서 `investors ARRAY<STRING>`, `growth_narrative` 등 뉴스 전용 필드가 빠져 있다.

#### [G-6] 기업 목록 GCS 전달(F4)에서 race condition (중요도: 낮음)

파일럿 스크립트에서 GCS에 기업 목록을 업로드한 뒤 Cloud Run Job을 트리거하는데, `trigger_cloud_run_job`이 비동기라면 이전 Job이 완료되기 전에 다음 Job이 시작될 수 있다. `run_pilot.py`에서 각 Job 완료를 동기적으로 기다리는 로직이 필요하다.

---

## 4. 두 문서 간 정합성 이슈 — 동기화 완료 (2026-03-08)

| # | 갭 | 해결 방법 | 상태 |
|---|---|---|---|
| C-1 | LLM: GPT-4o-mini vs Gemini 2.0 Flash | 전략 문서를 Gemini로 업데이트 + 비용 추정 갱신 | **완료** |
| C-2 | 최대 페이지 수 20 vs 10 | 전략 문서를 10으로 축소 + 사유 명시 | **완료** |
| C-3 | 뉴스 30건 cap 미명시 | GCP 계획에 `MAX_ARTICLES_PER_COMPANY = 30` 추가 | **완료** |
| C-4 | N3(mna) 쿼리 누락 + N5 추출 스킵 + N6 누락 | GCP에 mna 쿼리 추가, product/performance 추출 프롬프트 추가, N6은 전략 문서에서 v2로 이동 | **완료** |
| C-5 | `company_crawl_summary` 미명시 | GCP Phase 4에 태스크 추가 | **완료** |
| C-6 | GCS 버킷명 차이 | 전략 문서를 `gs://ml-api-test-vertex/crawl/`로 업데이트 | **완료** |

---

## 5. 전체 권장 사항

### 즉시 조치 (파일럿 전)

1. **[G-1]** 홈페이지 크롤러에 SPA 렌더링 대기 로직 추가
2. **[G-4]** JSON 파싱 실패 시 fence 제거 재시도 추가
3. ~~**[C-1]** 전략 문서 또는 GCP 계획에 LLM 변경 사유 기록~~ **완료**

### 파일럿 중 검증

4. **[G-2]** product 카테고리 본문 크롤링 여부를 파일럿에서 A/B 비교
5. **[S-4]** 짧은 기사에 대한 관련성 필터 기준 검증
6. ~~**[C-4]** N5(performance) LLM 추출 프롬프트 추가 여부 결정~~ **완료** — 프롬프트 추가됨

### 운영 전 정리

7. ~~**[C-2~C-6]** 전략 문서와 GCP 계획 간 수치/구조 차이를 한쪽에 맞추어 정리~~ **완료**
8. **[S-3]** 카테고리별 confidence ceiling 차등 적용 검토
9. **[G-5]** BigQuery 스키마 최종 확정 (통합 vs 분리) — 현재 통합 테이블로 진행, 뉴스 전용 필드 추가 완료

---

## 6. 요약

| 평가 영역 | 점수 (5점) | 코멘트 |
|---|---|---|
| 전략-구현 정합성 | 4.5 | C-1~C-6 동기화 완료 |
| 기술 설계 완성도 | 4.0 | SPA 대기, JSON 파싱 등 엣지케이스 보완 필요 |
| 비용 효율성 | 4.5 | 파일럿 ~$1, 월간 ~$12 — 매우 합리적 |
| 실행 가능성 | 4.0 | 파일럿 우선 접근 + 단계적 확장이 현실적 |
| 리스크 관리 | 4.0 | robots.txt, 개인정보, 법적 리스크 잘 고려 |
| **종합** | **4.0** | 파일럿 실행에 충분한 수준. 위 피드백 반영 시 더 견고해질 것 |
