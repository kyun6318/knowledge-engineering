# 기업 크롤링 전략 및 실행 계획

> v4 CompanyContext의 T3(홈페이지 크롤링) / T4(뉴스 크롤링) 소스에서
> **무엇을 수집하고, 어떻게 추출하며, 어떤 필드를 보강하는지**에 대한 상세 정의와 실행 계획.
>
> 작성일: 2026-03-08 | 기준: v4 CompanyContext (01_company_context.md)
>
> **v1.1 동기화** (2026-03-08): GCP 구현 계획(`crawling-gcp-plan.md`)과 정합성 맞춤
> - LLM: GPT-4o-mini → Gemini 2.0 Flash (GCP Vertex AI 네이티브)
> - 최대 페이지 수: 20 → 10 (Cloud Run Job 타임아웃 정합)
> - N6(기술/제품 전략): v2로 이동 (N2와 중복도 높음)
> - GCS 버킷: 기존 프로젝트 버킷(`gs://ml-api-test-vertex/crawl/`) 재사용
> - 뉴스 수집: 네이버 API 본문 미제공 사실 반영 (link 추가 크롤링)

---

## 1. 크롤링이 해결하는 문제

v4 CompanyContext에서 JD + NICE만으로는 채울 수 없거나 confidence가 낮은 필드들이 존재한다.

| CompanyContext 필드 | JD+NICE만 사용 시 | 크롤링 추가 시 |
|---|---|---|
| `stage_estimate` | confidence 0.50~0.65 | 뉴스(투자 기사)로 0.70~0.80 |
| `domain_positioning.market_segment` | confidence 0.40~0.60 | 홈페이지로 0.55~0.70 |
| `domain_positioning.product_description` | **null** | 홈페이지로 활성화 |
| `domain_positioning.competitive_landscape` | **null** | 뉴스로 활성화 |
| `structural_tensions` | **null (70%+)** | 뉴스로 30~50% 활성화 |
| `operating_model.narrative_summary` | **null** | 홈페이지+뉴스로 활성화 |
| `operating_model.facets` (3개) | confidence 0.30~0.45 | 홈페이지로 0.40~0.60 |

---

## 2. T3 — 회사 홈페이지 크롤링

### 2.1 수집 대상 페이지 유형

모든 페이지를 크롤링하는 것이 아니라, **CompanyContext에 기여하는 페이지 유형만 타겟팅**한다.

| # | 페이지 유형 | URL 패턴 (일반적) | 수집 우선순위 | 기여 필드 |
|---|---|---|---|---|
| P1 | **회사 소개 (About)** | `/about`, `/company`, `/about-us` | 필수 | product_description, market_segment, narrative_summary |
| P2 | **제품/서비스 소개** | `/product`, `/service`, `/solution`, `/features` | 필수 | product_description, market_segment, tech 힌트 |
| P3 | **채용 페이지** | `/careers`, `/jobs`, `/recruit`, `/채용` | 필수 | operating_model facets, team_context, narrative_summary |
| P4 | **기술 블로그** | `/blog`, `/tech-blog`, `/engineering` | 선택 | operating_model facets (process, speed), tech_stack |
| P5 | **팀/문화 소개** | `/team`, `/culture`, `/life` | 선택 | operating_model facets, narrative_summary |
| P6 | **고객 사례 / 파트너** | `/customers`, `/case-study`, `/partners` | 선택 | market_segment, competitive_landscape 힌트 |

### 2.2 페이지별 추출 정보 상세

#### P1: 회사 소개 (About)

```
추출 대상:
├─ company_description     : 회사가 하는 일 1~3문장 요약
├─ founding_story_signals  : 창업 배경/동기 (있으면)
├─ mission_vision          : 미션/비전 (있으면)
├─ market_segment_hints    : 타겟 시장/고객군 언급
├─ scale_signals           : 직원수/오피스/글로벌 거점 언급
└─ investor_mentions       : 투자사/투자 라운드 언급 (있으면)
```

**추출 프롬프트 예시**:
```
아래 회사 소개 페이지 텍스트에서 다음 정보를 추출하세요.
각 항목에 대해 원문 근거(evidence_span)를 반드시 인용하세요.
추출할 수 없는 항목은 null로 표기하세요.

1. company_description: 회사가 하는 일 (1~3문장)
2. market_segment: 타겟 시장 (예: "B2B SaaS", "헬스케어 플랫폼")
3. product_description: 핵심 제품/서비스 설명
4. scale_signals: 규모를 짐작할 수 있는 언급 (직원수, 거점, 고객수 등)
5. investor_mentions: 투자사/투자 라운드 언급

[주의사항]
- "혁신적", "최고의", "세계적" 등 광고성 수식어는 제거하고 팩트만 추출
- 수치가 포함된 표현을 우선 추출

[텍스트]
{page_text}
```

#### P2: 제품/서비스 소개

```
추출 대상:
├─ product_name            : 제품/서비스명
├─ product_category        : 카테고리 (SaaS/플랫폼/하드웨어/컨설팅 등)
├─ target_customer         : 타겟 고객 (B2B/B2C/B2G, SMB/Enterprise 등)
├─ key_features            : 핵심 기능 목록 (최대 5개)
├─ tech_mentions           : 기술 스택 / AI / 클라우드 등 언급
└─ pricing_model_hints     : 가격 모델 힌트 (구독/건당/무료 등)
```

**기여 필드 매핑**:
- `product_category` + `target_customer` → `domain_positioning.market_segment` 보강
- `product_name` + `key_features` → `domain_positioning.product_description`
- `tech_mentions` → `role_expectations.tech_stack` 교차 검증

#### P3: 채용 페이지

```
추출 대상:
├─ culture_statements      : 일하는 방식 관련 서술
├─ hiring_process          : 채용 프로세스 설명
├─ team_structure_hints    : 팀/조직 구조 언급 (스쿼드/트라이브 등)
├─ benefits_raw            : 복지/혜택 목록 (raw, 필터링 전)
├─ open_positions_count    : 현재 공개 채용 포지션 수
└─ growth_signals          : 채용 규모/속도로 추정되는 성장 신호
```

**operating_model facets 보강 규칙**:

| 채용 페이지 단서 | 보강 대상 facet | 보강 방법 |
|---|---|---|
| "2주 스프린트", "빠른 배포 주기" 등 | speed | 키워드 매칭 → score 보정 |
| "자율 출퇴근", "리모트 근무", "오너십" 등 | autonomy | 키워드 매칭 → score 보정 |
| "코드리뷰 필수", "테스트 커버리지", "RFC 문화" 등 | process | 키워드 매칭 → score 보정 |
| "수평적 문화", "자유로운 분위기" 등 | **무시** | 광고성 표현으로 분류 |

**광고성 필터링 강화**:
```python
NOISE_PATTERNS = [
    "수평적", "자유로운", "열정", "패밀리", "최고의 복지",
    "함께 성장", "꿈을 이루는", "행복한 일터", "가족 같은"
]

SIGNAL_PATTERNS = {
    "speed": ["스프린트", "주간 배포", "데일리 릴리즈", "ship fast",
              "CI/CD", "배포 주기", "iteration"],
    "autonomy": ["자율 출퇴근", "리모트", "재량 근무", "오너십",
                 "의사결정 권한", "셀프 매니징"],
    "process": ["코드리뷰", "RFC", "ADR", "테스트 커버리지",
                "PR 리뷰", "문서화", "온보딩 프로세스"]
}

def is_actionable_signal(text, pattern):
    """광고성이 아닌, 실제 운영 행동을 나타내는 표현인지 판별"""
    if any(noise in text for noise in NOISE_PATTERNS):
        return False
    # 수치/구체적 행동이 동반되면 시그널로 인정
    has_number = bool(re.search(r'\d+', text))
    has_specific_action = any(p in text for p in pattern)
    return has_number or has_specific_action
```

#### P4: 기술 블로그 (선택)

```
추출 대상:
├─ recent_post_count       : 최근 6개월 포스팅 수 (활성도)
├─ tech_topics             : 다루는 기술 주제 목록
├─ engineering_culture     : 엔지니어링 문화 단서
│   ├─ has_code_review_post: 코드리뷰 관련 글 존재 여부
│   ├─ has_incident_post   : 장애 대응/포스트모템 글 존재 여부
│   └─ has_architecture_post: 아키텍처 의사결정 글 존재 여부
└─ team_size_hints         : 팀 규모 단서 ("우리 팀은 10명으로...")
```

**operating_model 보강 방식**:
- `has_incident_post = true` → `process` facet 상향 (+0.1)
- `recent_post_count >= 3/6mo` → `speed` facet 간접 지지 (활발한 기술 공유 = 빠른 조직)
- 블로그 존재 자체가 → `process` facet 간접 지지 (문서화 문화)

### 2.3 홈페이지 크롤링 기술 설계

#### 크롤링 파이프라인

```
[입력: company_domain_url]
        │
    ┌───┴───┐
    │ 1. URL │ Discovery
    └───┬───┘
        │  sitemap.xml 파싱 또는 메인 페이지에서 링크 탐색
        │  대상 페이지 유형(P1~P6) URL 식별
        │  최대 10 페이지로 제한 (필수 P1~P3 우선)
        │
    ┌───┴───┐
    │ 2. 렌더링 │ & 텍스트 추출
    └───┬───┘
        │  SPA(React/Vue) 대응: headless browser (Playwright)
        │  정적 사이트: HTTP GET + BeautifulSoup
        │  텍스트 정제: 네비게이션/푸터/광고 제거
        │
    ┌───┴───┐
    │ 3. 페이지 │ 분류
    └───┬───┘
        │  URL 패턴 + 페이지 제목 + 본문 키워드로 P1~P6 분류
        │  분류 불가 시 LLM 보조 분류
        │
    ┌───┴───┐
    │ 4. 정보 │ 추출 (LLM)
    └───┬───┘
        │  페이지 유형별 전용 프롬프트 실행
        │  evidence_span 필수 추출
        │
    ┌───┴───┐
    │ 5. 저장  │ & 인덱싱
    └───┬───┘
        │  원본 텍스트 + 추출 결과 + 메타데이터 저장
        │  company_id, crawl_date, page_type 태깅
        └─→ [출력: CrawledCompanyData]
```

#### 기술 스택

| 컴포넌트 | 도구 | 이유 |
|---|---|---|
| 크롤링 엔진 | **Playwright** (Python) | SPA 렌더링 지원, 안정적 |
| 스케줄링 | Cloud Scheduler + Cloud Run Job | 배치 실행, 서버리스 |
| 텍스트 정제 | **Readability + BeautifulSoup** | 본문 추출 정확도 |
| 정보 추출 | **LLM (Gemini 2.0 Flash)** | 비용 효율 + 한국어 지원 + GCP 네이티브 (Vertex AI) |
| 저장소 | **BigQuery** (정형) + **GCS** (원본 HTML) | 분석 용이 |
| URL 발견 | sitemap.xml + BFS (depth 2) | 과도한 크롤링 방지 |

#### 크롤링 정책 및 제약

| 항목 | 정책 |
|---|---|
| robots.txt | **반드시 준수** — disallow 경로 크롤링 금지 |
| 요청 간격 | 최소 2초 (동일 도메인) |
| 최대 페이지 수 | 기업당 10 페이지 (필수 P1~P3 우선, Cloud Run Job 1시간 타임아웃 정합) |
| 최대 페이지 크기 | 1MB (초과 시 스킵) |
| 재크롤링 주기 | 30일 (최신성 유지) |
| User-Agent | 명시적 봇 식별 (회사명 + 목적 명시) |
| 개인정보 | 직원 개인 프로필/SNS는 수집하지 않음 |
| JavaScript 렌더링 | 최대 10초 대기 후 타임아웃 |

#### 실패 처리

| 실패 유형 | 처리 |
|---|---|
| 홈페이지 없음 | `crawl_status: "NO_SITE"`, 해당 소스 스킵 |
| robots.txt 차단 | `crawl_status: "BLOCKED"`, 해당 경로 스킵 |
| SPA 렌더링 실패 | HTTP GET fallback, 실패 시 스킵 |
| 본문 추출 실패 (텍스트 < 50자) | 해당 페이지 스킵 |
| LLM 추출 실패 | 2회 재시도 후 스킵, 로그 기록 |
| 한국어/영어 외 언어 | 스킵 (v1) |

---

## 3. T4 — 뉴스/기사 크롤링

### 3.1 수집 대상 기사 유형

| # | 기사 유형 | 수집 우선순위 | 기여 필드 | 예시 쿼리 |
|---|---|---|---|---|
| N1 | **투자 유치 기사** | 필수 | stage_estimate 보강 | `"{회사명}" AND ("투자" OR "시리즈" OR "펀딩")` |
| N2 | **제품/서비스 런칭** | 필수 | product_description, market_segment | `"{회사명}" AND ("출시" OR "런칭" OR "서비스")` |
| N3 | **인수합병 / 파트너십** | 선택 | competitive_landscape, structural_tensions | `"{회사명}" AND ("인수" OR "합병" OR "파트너십" OR "MOU")` |
| N4 | **조직/경영 변화** | 선택 | structural_tensions | `"{회사명}" AND ("CEO" OR "대표" OR "조직개편" OR "구조조정")` |
| N5 | **실적/성과 발표** | 선택 | stage_estimate, market_segment | `"{회사명}" AND ("매출" OR "실적" OR "성장" OR "사용자")` |
| N6 | **기술/제품 전략** | 선택 (v2) | domain_positioning, operating_model | `"{회사명}" AND ("기술" OR "AI" OR "플랫폼" OR "전략")` — v1에서는 N2와 중복도가 높아 제외, v2에서 추가 |

### 3.2 기사 유형별 추출 정보 상세

#### N1: 투자 유치 기사 (최우선)

```
추출 대상:
├─ funding_round      : 투자 라운드 (Seed, Series A/B/C...)
├─ funding_amount     : 투자 금액
├─ investors          : 투자사 목록
├─ funding_date       : 투자 일자
├─ valuation_hints    : 기업가치 언급 (있으면)
├─ use_of_funds       : 투자금 용도 ("인력 확충", "해외 진출" 등)
└─ growth_narrative   : 성장 서사 ("전년 대비 3배 성장", "MAU 100만 돌파" 등)
```

**기여 필드 매핑**:
- `funding_round` → `stage_estimate.stage_label` 직접 보강 (confidence 상향 최대 +0.15)
- `funding_amount` + `investors` → `stage_estimate.stage_signals` evidence 추가
- `use_of_funds` → `structural_tensions` 힌트 ("기술 인력 확충" = tech_debt 시사)
- `growth_narrative` → `domain_positioning.market_segment` 보강

**추출 프롬프트**:
```
아래 투자 기사에서 정보를 추출하세요.
반드시 원문에서 직접 인용(evidence_span)하세요.

1. funding_round: 투자 라운드 (Seed/Pre-A/Series A/B/C/D+/IPO)
2. funding_amount: 금액 (숫자 + 단위)
3. investors: 투자사 이름 목록
4. funding_date: 날짜 (YYYY-MM 형식)
5. use_of_funds: 투자금 사용 계획
6. growth_narrative: 성장 관련 수치/사실

[주의] 기사 제목/부제의 과장 표현은 무시하고 본문 팩트만 추출.

[기사 텍스트]
{article_text}
```

#### N2: 제품/서비스 런칭 기사

```
추출 대상:
├─ product_name       : 제품/서비스명
├─ launch_date        : 출시 일자
├─ target_market      : 타겟 시장/고객
├─ key_differentiator : 경쟁 차별점 (있으면)
├─ tech_approach      : 기술적 접근 ("AI 기반", "블록체인 활용" 등)
└─ traction_data      : 초기 성과 수치 (있으면)
```

#### N3: 인수합병/파트너십 기사

```
추출 대상:
├─ deal_type          : M&A / 전략적 제휴 / JV / MOU
├─ counterparty       : 상대 기업
├─ deal_purpose       : 목적 ("기술력 확보", "시장 확대" 등)
├─ deal_amount        : 금액 (있으면)
└─ strategic_signal   : 전략적 방향 시사점
```

**structural_tensions 기여** (enum: `02_v4_amendments.md` A6 참조):
- M&A → `integration_tension`
- 파트너십 → `build_vs_buy`

#### N4: 조직/경영 변화 기사

```
추출 대상:
├─ change_type        : CEO 교체 / CxO 영입 / 조직개편 / 구조조정 / 감원
├─ change_date        : 변화 시점
├─ scale_of_change    : 변화 규모 ("전사 조직개편", "30% 감원" 등)
├─ stated_reason      : 공식 사유
└─ implied_tension    : 암시되는 내부 긴장
```

**structural_tensions 기여 (핵심)**:

> tension_type은 `02_v4_amendments.md` A6에서 확정한 8개 taxonomy enum을 사용한다.

| change_type | 추론 가능한 tension_type (enum) | confidence |
|---|---|---|
| CEO 교체 | `founder_vs_professional_mgmt` | 0.45 |
| CxO 영입 | `scaling_leadership` | 0.40 |
| 조직개편 | `portfolio_restructuring` | 0.45 |
| 구조조정/감원 | `efficiency_vs_growth` | 0.50 |
| 사업부 분리/합병 | `portfolio_restructuring` | 0.45 |

#### N5: 실적/성과 발표

```
추출 대상:
├─ metric_type        : 매출 / MAU / 거래액 / 고객수 등
├─ metric_value       : 수치
├─ metric_period      : 측정 기간
├─ yoy_growth         : 전년 대비 성장률 (있으면)
└─ market_position    : 시장 내 포지션 언급 ("1위", "점유율 30%" 등)
```

### 3.3 뉴스 수집 소스 및 방법

| 소스 | 접근 방법 | 장점 | 단점 |
|---|---|---|---|
| **네이버 뉴스 검색** | 네이버 검색 API | 국내 커버리지 최대, API 제공 | 일일 호출 제한 |
| **Google News** | SerpAPI / Google News RSS | 글로벌 + 국내 커버리지 | 유료 API 필요 |
| **직접 언론사 크롤링** | HTTP GET | API 비용 없음 | 유지보수 높음, 법적 리스크 |
| **TheVC / 크런치베이스** | API | 투자 정보 정확도 높음 | 유료, 커버리지 제한 |
| **PR 통신사 (뉴스와이어 등)** | RSS / API | 공식 보도자료 | 기업 시각 편향 |

**v1 권장 조합**: 네이버 뉴스 검색 API (Primary) + TheVC API (투자 정보 보강)

#### 검색 전략

```python
def build_news_queries(company_name, aliases=None):
    """기업명 + 카테고리별 검색 쿼리 생성"""
    names = [company_name] + (aliases or [])
    queries = []

    for name in names:
        # N1: 투자 (최우선)
        queries.append({
            "query": f'"{name}" (투자 OR 시리즈 OR 펀딩 OR 유치)',
            "category": "funding",
            "priority": 1,
            "max_results": 10,
            "date_range": "2y"  # 최근 2년
        })
        # N2: 제품/서비스
        queries.append({
            "query": f'"{name}" (출시 OR 런칭 OR 서비스 OR 제품)',
            "category": "product",
            "priority": 1,
            "max_results": 5,
            "date_range": "1y"
        })
        # N4: 조직 변화
        queries.append({
            "query": f'"{name}" (CEO OR 대표이사 OR 조직개편 OR 구조조정 OR 인사)',
            "category": "org_change",
            "priority": 2,
            "max_results": 5,
            "date_range": "1y"
        })
        # N5: 실적
        queries.append({
            "query": f'"{name}" (매출 OR 실적 OR 성장 OR 사용자 OR 거래액)',
            "category": "performance",
            "priority": 2,
            "max_results": 5,
            "date_range": "1y"
        })
        # N3: M&A
        queries.append({
            "query": f'"{name}" (인수 OR 합병 OR 파트너십 OR MOU)',
            "category": "mna",
            "priority": 3,
            "max_results": 3,
            "date_range": "2y"
        })

    return queries
```

#### 중복/노이즈 제거

```python
def deduplicate_articles(articles):
    """동일 사건에 대한 중복 기사 제거"""
    # 1. 제목 유사도 기반 클러스터링 (cosine sim > 0.85)
    clusters = cluster_by_title_similarity(articles, threshold=0.85)

    # 2. 각 클러스터에서 대표 기사 선택 (가장 긴 본문)
    deduped = []
    for cluster in clusters:
        representative = max(cluster, key=lambda a: len(a.body))
        representative.duplicate_count = len(cluster)
        deduped.append(representative)

    return deduped

def filter_irrelevant(articles, company_name):
    """회사와 무관한 기사 필터링"""
    filtered = []
    for article in articles:
        # 회사명이 본문에 3회 이상 등장해야 주요 기사로 판단
        mention_count = article.body.lower().count(company_name.lower())
        if mention_count >= 3:
            filtered.append(article)
        elif mention_count >= 1:
            # 제목에 회사명이 있으면 허용
            if company_name.lower() in article.title.lower():
                filtered.append(article)
    return filtered
```

### 3.4 뉴스 크롤링 파이프라인

```
[입력: company_name, company_aliases]
        │
    ┌───┴───┐
    │ 1. 검색 │ 쿼리 생성
    └───┬───┘
        │  카테고리별 쿼리 생성 (N1~N5)
        │  기업명 + 별칭(aliases) 조합
        │
    ┌───┴───┐
    │ 2. 뉴스 │ 수집
    └───┬───┘
        │  네이버 뉴스 검색 API 호출 (v1 Primary)
        │  기사당 제목 + description + link + 발행일 수집
        │  본문은 funding/org_change 카테고리만 link 추가 크롤링 (네이버 API 본문 미제공)
        │  기업당 최대 30건 (중복 제거 후)
        │
    ┌───┴───┐
    │ 3. 필터링 │ & 중복 제거
    └───┬───┘
        │  회사 관련성 필터 (mention_count >= 3)
        │  제목 유사도 기반 중복 제거
        │  광고성 기사(PR성 보도자료) 마킹
        │
    ┌───┴───┐
    │ 4. 분류  │ (기사 유형)
    └───┬───┘
        │  N1~N5 카테고리 자동 분류 (LLM)
        │  복수 카테고리 허용
        │
    ┌───┴───┐
    │ 5. 정보 │ 추출 (LLM)
    └───┬───┘
        │  카테고리별 전용 프롬프트 실행
        │  evidence_span 필수
        │  confidence scoring
        │
    ┌───┴───┐
    │ 6. 시계열 │ 정리
    └───┬───┘
        │  추출 결과를 시간순 정렬
        │  최신 정보 우선 (freshness 가중)
        │  동일 주제 최신 기사가 이전 기사를 대체
        │
    ┌───┴───┐
    │ 7. 저장  │
    └───┬───┘
        └─→ [출력: NewsExtractedData]
```

### 3.5 뉴스 데이터의 신뢰도 보정

뉴스는 **편향과 과장**이 내재된 소스이므로 추가 보정이 필요하다.

| 보정 규칙 | 적용 대상 | 방법 |
|---|---|---|
| PR성 기사 감쇠 | 보도자료 기반 기사 | confidence × 0.7 |
| 복수 언론사 교차 확인 | 동일 사실을 여러 매체가 보도 | confidence + 0.10 |
| 기사 나이 감쇠 | 오래된 기사 | confidence × max(0.5, 1.0 - months_ago × 0.03) |
| 추측성 표현 감쇠 | "~할 것으로 보인다", "~전망" | confidence × 0.6 |
| 수치 동반 가산 | 구체적 숫자가 포함된 claim | confidence + 0.05 |

```python
def adjust_news_confidence(base_confidence, article):
    c = base_confidence

    # PR성 감쇠
    if article.is_press_release:
        c *= 0.7

    # 복수 매체 보강
    if article.duplicate_count >= 3:
        c = min(c + 0.10, 0.55)  # T4 ceiling은 0.55

    # 기사 나이 감쇠
    months_ago = (today - article.publish_date).days / 30
    freshness_factor = max(0.5, 1.0 - months_ago * 0.03)
    c *= freshness_factor

    # 추측성 표현
    speculative_patterns = ["전망", "것으로 보인다", "예상", "관측", "가능성"]
    if any(p in article.body for p in speculative_patterns):
        c *= 0.6

    return min(c, 0.55)  # T4 source ceiling
```

---

## 4. 크롤링 결과 → CompanyContext 필드 통합

### 4.1 통합 로직 개요

```
[NICE 데이터] ──────────────────┐
[JD 데이터] ────────────────────┤
[홈페이지 크롤링 결과] ────────┤──→ [CompanyContext 생성기] ──→ CompanyContext v4
[뉴스 크롤링 결과] ────────────┤
[투자 DB 데이터] ──────────────┘
```

### 4.2 필드별 소스 우선순위 및 통합 규칙

| 필드 | 1순위 소스 | 2순위 소스 | 3순위 소스 | 통합 규칙 |
|---|---|---|---|---|
| `stage_estimate.stage_label` | 투자 DB | 뉴스(N1) | NICE + JD | 최고 confidence 소스 채택, 교차 지지 시 boost |
| `domain_positioning.product_description` | 홈페이지(P2) | 뉴스(N2) | JD | 홈페이지 우선, 뉴스로 보강 |
| `domain_positioning.market_segment` | 홈페이지(P1+P2) | JD | 뉴스(N2) | 복수 소스 합의 시 confidence 상향 |
| `domain_positioning.competitive_landscape` | 뉴스(N3+N5) | 홈페이지(P6) | — | 뉴스 기반, 경쟁사/시장 언급 수집 |
| `structural_tensions` | 뉴스(N4) | 뉴스(N3) | — | 뉴스에서만 추출 가능, 없으면 null |
| `operating_model.facets` | JD | 홈페이지(P3+P4) | — | JD 기준, 홈페이지로 보강 |
| `operating_model.narrative_summary` | 홈페이지(P3+P5) | 뉴스 | JD | 홈페이지 채용/문화 페이지 기반 |

### 4.3 소스 간 충돌 해결

```python
def resolve_conflict(claims_from_sources):
    """복수 소스에서 동일 필드에 대해 다른 값을 주장할 때"""
    if len(set(c.value for c in claims_from_sources)) == 1:
        # 모든 소스 합의 → boost
        best = max(claims_from_sources, key=lambda c: c.confidence)
        best.confidence = min(best.confidence + 0.10, 0.85)
        return best

    # 충돌 발생
    # 규칙 1: 소스 Tier가 높은 쪽 우선
    sorted_claims = sorted(claims_from_sources,
                           key=lambda c: SOURCE_TIER_PRIORITY[c.source_type])
    winner = sorted_claims[0]

    # 규칙 2: 충돌 사실 기록
    winner.has_contradiction = True
    winner.contradiction_sources = [c.source_type for c in sorted_claims[1:]]
    winner.confidence = min(winner.confidence, 0.50)  # 충돌 시 confidence 하향

    return winner
```

---

## 5. 저장 스키마

### 5.1 크롤링 원본 저장 (GCS)

```
gs://ml-api-test-vertex/crawl/    # GCP 구현: 기존 프로젝트 버킷 재사용
├── homepage/
│   ├── {company_id}/
│   │   ├── {crawl_date}/
│   │   │   ├── raw/          # 원본 HTML
│   │   │   │   ├── about.html
│   │   │   │   ├── product.html
│   │   │   │   └── careers.html
│   │   │   ├── text/         # 정제된 텍스트
│   │   │   │   ├── about.txt
│   │   │   │   └── ...
│   │   │   └── extracted/    # LLM 추출 결과 JSON
│   │   │       ├── about.json
│   │   │       └── ...
│   │   └── latest -> {최신 crawl_date}/
├── news/
│   ├── {company_id}/
│   │   ├── {crawl_date}/
│   │   │   ├── articles/     # 수집된 기사 원문
│   │   │   ├── extracted/    # 추출 결과 JSON
│   │   │   └── summary.json  # 시계열 요약
│   │   └── latest -> {최신 crawl_date}/
```

### 5.2 추출 결과 저장 (BigQuery)

```sql
-- 홈페이지 크롤링 추출 결과
CREATE TABLE crawl.homepage_extracted (
  company_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  page_type STRING,                -- "about" / "product" / "careers" / "blog" / "culture"
  page_url STRING,
  -- 추출 필드
  product_description STRING,
  market_segment STRING,
  culture_signals JSON,            -- {speed: [...], autonomy: [...], process: [...]}
  scale_signals JSON,
  tech_mentions ARRAY<STRING>,
  -- 메타
  text_length INT64,
  extraction_model STRING,
  evidence_spans JSON,             -- 원문 근거 배열
  confidence FLOAT64,
  generated_at TIMESTAMP
);

-- 뉴스 크롤링 추출 결과
CREATE TABLE crawl.news_extracted (
  company_id STRING NOT NULL,
  article_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  -- 기사 메타
  title STRING,
  source_media STRING,
  publish_date DATE,
  article_url STRING,
  category STRING,                 -- "funding" / "product" / "org_change" / "performance" / "mna"
  is_press_release BOOLEAN,
  -- 추출 필드
  funding_round STRING,
  funding_amount STRING,
  investors ARRAY<STRING>,
  tension_type STRING,
  tension_description STRING,
  growth_narrative STRING,
  extracted_data JSON,             -- 카테고리별 추출 결과 전체
  -- 메타
  raw_confidence FLOAT64,
  adjusted_confidence FLOAT64,     -- 보정 후
  evidence_spans JSON,
  generated_at TIMESTAMP
);

-- 기업별 크롤링 요약 (CompanyContext 생성 시 참조)
CREATE TABLE crawl.company_crawl_summary (
  company_id STRING NOT NULL,
  last_homepage_crawl DATE,
  last_news_crawl DATE,
  homepage_pages_crawled INT64,
  news_articles_collected INT64,
  -- 핵심 추출 결과 요약
  best_product_description STRING,
  best_market_segment STRING,
  latest_funding_round STRING,
  latest_funding_date DATE,
  tension_signals JSON,            -- [{type, description, confidence, source}]
  culture_signals_aggregated JSON, -- {speed: {score, confidence}, ...}
  -- 메타
  overall_crawl_quality FLOAT64,   -- 0~1, 수집 성공률 기반
  updated_at TIMESTAMP
);
```

---

## 6. 실행 계획

### Phase 0: 설계 및 준비 (1주)

| # | 작업 | 산출물 | 담당 |
|---|---|---|---|
| 0-1 | 크롤링 대상 기업 목록 확정 | 기업 리스트 (company_id + domain URL + aliases) | 데이터 |
| 0-2 | 네이버 뉴스 API 키 발급 / TheVC API 계약 | API 접근 권한 | 인프라 |
| 0-3 | GCS 버킷 + BigQuery 테이블 생성 | 저장소 | 인프라 |
| 0-4 | 추출 프롬프트 초안 작성 (페이지/기사 유형별) | 프롬프트 셋 | ML |
| 0-5 | robots.txt 준수 로직 구현 | 크롤링 정책 모듈 | 개발 |

### Phase 1: 홈페이지 크롤러 구축 (2주)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 1-1 | Playwright 기반 크롤링 엔진 구현 | 크롤러 코어 | SPA 렌더링 포함 |
| 1-2 | URL 발견 + 페이지 분류 모듈 | 페이지 타이핑 | sitemap + BFS |
| 1-3 | 텍스트 정제 모듈 (Readability) | 본문 추출기 | 네비/푸터 제거 |
| 1-4 | LLM 추출 모듈 (페이지 유형별) | 정보 추출기 | Gemini 2.0 Flash |
| 1-5 | 파일럿: 기업 20개 크롤링 | 파일럿 결과 | 품질 검증 |
| 1-6 | 추출 품질 Human eval (파일럿) | 품질 리포트 | 프롬프트 튜닝 |

### Phase 2: 뉴스 크롤러 구축 (2주, Phase 1과 병렬 가능)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 2-1 | 네이버 뉴스 API 연동 | 뉴스 수집기 | 검색 쿼리 생성 포함 |
| 2-2 | 기사 필터링 + 중복 제거 모듈 | 필터 모듈 | 제목 유사도 클러스터링 |
| 2-3 | 기사 분류 모듈 (N1~N5) | 분류기 | LLM 기반 |
| 2-4 | LLM 추출 모듈 (기사 유형별) | 정보 추출기 | 카테고리별 프롬프트 |
| 2-5 | 신뢰도 보정 모듈 | 보정 로직 | PR성 감쇠 등 |
| 2-6 | 파일럿: 기업 20개 뉴스 수집 | 파일럿 결과 | 품질 검증 |

### Phase 3: 통합 및 CompanyContext 보강 (1주)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 3-1 | 크롤링 결과 → CompanyContext 통합 모듈 | 통합 로직 | 소스 우선순위/충돌 해결 |
| 3-2 | company_crawl_summary 집계 | 요약 테이블 | BigQuery |
| 3-3 | CompanyContext fill_rate 비교 (크롤링 전 vs 후) | 효과 리포트 | 핵심 성과 지표 |
| 3-4 | 배치 스케줄링 (Cloud Scheduler) | 운영 파이프라인 | 30일 주기 |

### Phase 4: 배치 실행 및 모니터링 (지속)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 4-1 | 전체 대상 기업 크롤링 실행 | 크롤링 데이터 | 배치 |
| 4-2 | 실패/부분 성공 모니터링 | 대시보드 | 성공률/에러율 추적 |
| 4-3 | 추출 품질 샘플링 검수 (주간) | 품질 리포트 | 랜덤 20건 |

---

## 7. 성과 측정 (KPI)

| 지표 | 측정 방법 | 목표 |
|---|---|---|
| **홈페이지 크롤링 성공률** | 크롤링 시도 기업 중 1페이지 이상 수집 성공 비율 | 80%+ |
| **뉴스 수집 커버리지** | 대상 기업 중 1건 이상 관련 기사 발견 비율 | 70%+ |
| **product_description 활성화율** | 크롤링 후 product_description ≠ null 비율 | 60%+ |
| **structural_tensions 활성화율** | 크롤링 후 structural_tensions ≠ null 비율 | 30%+ (뉴스 의존) |
| **stage_estimate confidence 상승** | 크롤링 전후 평균 confidence 비교 | +0.10 이상 |
| **operating_model facet confidence 상승** | 크롤링 전후 평균 confidence 비교 | +0.08 이상 |
| **CompanyContext fill_rate 상승** | 크롤링 전후 평균 fill_rate 비교 | 0.71 → 0.85+ |

---

## 8. 비용 추정

### 기업 1,000개 기준 (월간)

| 항목 | 단가 | 수량 | 월비용 (추정) |
|---|---|---|---|
| Cloud Run (Playwright) | $0.01/건 | 1,000기업 × 10페이지 | $100 |
| 네이버 뉴스 API | 무료 (일 25,000건) | ~5,000 쿼리/월 | $0 |
| TheVC API | 월 정액 | — | 확인 필요 |
| LLM (Gemini 2.0 Flash, 추출) | $0.10/1M input | ~5M tokens/월 | ~$0.5 |
| GCS 저장 | $0.02/GB | ~10GB | $0.2 |
| BigQuery | $5/TB 쿼리 | 소량 | $1~5 |
| **합계** | | | **~$107/월** |

재크롤링 주기 30일 기준. 초기 구축 시 1회성 비용은 인건비가 지배적.

---

## 9. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|---|---|---|
| 홈페이지가 없는 기업 (소규모) | product_description null | 뉴스로 보완, 불가 시 NICE만 사용 |
| SPA 렌더링 실패율 높음 | 크롤링 성공률 저하 | HTTP GET fallback + 타임아웃 조정 |
| 뉴스에서 동명이인 기업 혼동 | 잘못된 정보 연결 | company_id + 산업코드로 교차 검증 |
| 네이버 API 호출 제한 | 수집량 부족 | 분산 스케줄링 + Google News 보조 |
| 크롤링 법적 리스크 | — | robots.txt 준수, 개인정보 미수집, 요청 간격 준수 |
| LLM 추출 품질 불안정 | 잘못된 claim 생산 | evidence_span 필수, 주간 샘플링 검수 |
| 광고성 콘텐츠 과다 | facet 스코어 왜곡 | 광고성 필터 강화 + LLM 판별 |
