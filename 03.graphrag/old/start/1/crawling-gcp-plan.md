# 기업 크롤링 파이프라인 — GCP 구현 계획

> **목적**: CompanyContext 보강을 위한 기업 홈페이지(T3) 및 뉴스(T4) 크롤링 파이프라인을
> GCP 환경에서 구축하기 위한 실행 계획.
>
> **기준 문서**: `ontology/v5/01_crawling_strategy.md` (수집 전략), `api-test-3day-v3.md` (GCP 환경 기준)
>
> 작성일: 2026-03-08
>
> **v1.1 수정 이력**:
> - [F1] 네이버 뉴스 API는 본문 미제공 → 기사 link 추가 크롤링 로직 추가
> - [F2] 홈페이지 크롤러 배치 크기 50→15로 축소 (타임아웃 정합)
> - [F3] Cloud Workflows는 운영 단계로 이동, 파일럿은 Python 스크립트로 실행
> - [F4] 기업 목록을 환경변수 대신 GCS 파일로 전달
> - [F5] robots.txt 파싱에 urllib.robotparser 표준 라이브러리 사용
> - [F6] Gemini API rate limit 대응 (QPM throttle) 추가
> - [F7] 기업 domain_url 확보 방법 명시
>
> **v1.2 전략 문서 동기화** (2026-03-08):
> - [S1] QUERY_TEMPLATES에 mna(N3) 추가 — 전략 문서와 정합
> - [S2] product/performance(N2,N5) LLM 추출 프롬프트 추가 — description 기반 간이 추출
> - [S3] 기업당 뉴스 최대 30건 cap 추가 (`MAX_ARTICLES_PER_COMPANY`)
> - [S4] `extracted_fields` 테이블에 `investors`, `growth_narrative` 컬럼 추가
> - [S5] Phase 4에 `company_crawl_summary` 집계 테이블 생성 태스크 추가
> - [S6] mna 카테고리 본문 크롤링 대상에 추가

---

## 1. 목표 및 범위

### 목표

기업 홈페이지와 뉴스 기사를 크롤링하여 CompanyContext의 빈 필드를 채운다.

| 보강 대상 필드 | 크롤링 전 | 크롤링 후 목표 |
|---|---|---|
| `domain_positioning.product_description` | null | 60%+ 활성화 |
| `structural_tensions` | null (70%+) | 30~50% 활성화 |
| `operating_model.facets` confidence | 0.30~0.45 | 0.40~0.60 |
| `stage_estimate` confidence | 0.50~0.65 | 0.65~0.80 |
| CompanyContext 전체 fill_rate | 0.71 | 0.85+ |

### 범위

| 포함 | 제외 |
|---|---|
| 홈페이지 크롤링 (About/Product/Careers) | 기술 블로그 심층 분석 (v2) |
| 뉴스 검색 API 연동 (네이버) | 직접 언론사 크롤링 |
| LLM 기반 정보 추출 (Gemini) | Closed-loop Enrichment (v2) |
| BigQuery 저장 + GCS 원본 보관 | 실시간 서빙 API (v2) |
| 배치 스케줄링 (30일 주기) | 이벤트 기반 실시간 크롤링 |

---

## 2. GCP 아키텍처

```
Cloud Scheduler (30일 주기)
    │
    ▼
Cloud Workflows (오케스트레이션)
    │
    ├─[Step 1] BigQuery에서 크롤링 대상 기업 목록 조회
    │
    ├─[Step 2] Cloud Run Job: 홈페이지 크롤링
    │   ├─ Playwright (headless Chrome)
    │   ├─ URL 발견 + 페이지 분류
    │   ├─ 텍스트 정제 (Readability)
    │   └─ 결과 → GCS (원본 HTML + 정제 텍스트)
    │
    ├─[Step 3] Cloud Run Job: 뉴스 수집
    │   ├─ 네이버 뉴스 검색 API 호출
    │   ├─ 중복 제거 + 관련성 필터
    │   └─ 결과 → GCS (기사 텍스트)
    │
    ├─[Step 4] Cloud Run Job: LLM 추출
    │   ├─ Gemini API (정보 추출)
    │   ├─ 페이지/기사 유형별 프롬프트
    │   └─ 결과 → BigQuery (추출 데이터)
    │
    └─[Step 5] BigQuery: CompanyContext 통합 뷰 갱신
```

### GCP 서비스 매핑

| 역할 | GCP 서비스 | 이유 |
|---|---|---|
| 크롤링 실행 | **Cloud Run Jobs** | 컨테이너 기반, Playwright 실행 가능, 타임아웃 최대 1시간 |
| 스케줄링 | **Cloud Scheduler** | cron 기반 배치 트리거 |
| 오케스트레이션 (운영 단계) | **Cloud Workflows** | Step 간 의존성 관리, 에러 핸들링. 파일럿에서는 Python 스크립트로 대체 |
| LLM 추출 | **Vertex AI Gemini API** | api-test-3day-v3에서 검증된 동일 SDK/모델 |
| 원본 저장 | **GCS** | HTML/텍스트 원본 보관 |
| 추출 결과 저장 | **BigQuery** | 분석/조인 용이, DS/MLE 직접 접근 |
| 시크릿 관리 | **Secret Manager** | 네이버 API 키 등 |

---

## 3. 환경 구성

```
프로젝트: ml-api-test-vertex (기존 프로젝트 재사용)
리전: asia-northeast3 (서울) — 크롤링 대상이 한국 기업 중심
Vertex AI 리전: us-central1 — Gemini API 호출 (기존 테스트 환경 동일)

API 활성화 필요 (기존 + 추가):
  - Cloud Run API
  - Cloud Workflows API
  - Cloud Scheduler API
  - Secret Manager API
  - Artifact Registry API (컨테이너 이미지)

SDK:
  google-genai >= 1.5.0            # Gemini API (api-test-3day-v3 동일)
  google-cloud-bigquery >= 3.20.0
  google-cloud-storage >= 2.14.0
  playwright >= 1.40.0             # 홈페이지 크롤링
  readability-lxml >= 0.8.1        # 본문 추출
  beautifulsoup4 >= 4.12.0         # HTML 파싱
  requests >= 2.31.0               # 뉴스 API 호출

Budget Alert: $200 (경고), $400 (강제 중단)
  — api-test와 별도 알림 설정

Gemini API Rate Limit:
  gemini-2.0-flash: 15 QPM (무료) / 1000 QPM (유료)
  → 파일럿은 무료 티어로 충분, 5초 간격 호출로 QPM 준수
```

### GCS 구조

```
gs://ml-api-test-vertex/
├── crawl/
│   ├── homepage/
│   │   └── {company_id}/
│   │       └── {crawl_date}/
│   │           ├── raw/           # 원본 HTML
│   │           ├── text/          # 정제된 텍스트
│   │           └── meta.json      # 크롤링 메타 (URL, status, page_type)
│   ├── news/
│   │   └── {company_id}/
│   │       └── {crawl_date}/
│   │           ├── articles/      # 기사 본문
│   │           └── meta.json      # 검색 쿼리, 기사 수
│   └── extracted/
│       └── {company_id}/
│           └── {crawl_date}.json  # LLM 추출 결과
```

### BigQuery 테이블

```sql
-- 크롤링 대상 기업 마스터
CREATE TABLE crawl.company_targets (
  company_id STRING NOT NULL,
  company_name STRING NOT NULL,
  aliases ARRAY<STRING>,          -- 검색용 별칭
  domain_url STRING,              -- 홈페이지 URL (null 가능)
  nice_industry_code STRING,
  is_active BOOLEAN DEFAULT TRUE,
  last_homepage_crawl TIMESTAMP,
  last_news_crawl TIMESTAMP,
  created_at TIMESTAMP
);

-- 홈페이지 크롤링 결과
CREATE TABLE crawl.homepage_pages (
  company_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  page_url STRING,
  page_type STRING,               -- about / product / careers / blog / culture / other
  text_length INT64,
  crawl_status STRING,            -- SUCCESS / BLOCKED / TIMEOUT / NO_CONTENT
  gcs_raw_path STRING,
  gcs_text_path STRING,
  created_at TIMESTAMP
);

-- 뉴스 수집 결과
CREATE TABLE crawl.news_articles (
  company_id STRING NOT NULL,
  article_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  title STRING,
  source_media STRING,
  publish_date DATE,
  article_url STRING,
  category STRING,                -- funding / product / org_change / performance / mna
  body_length INT64,
  is_press_release BOOLEAN,
  gcs_path STRING,
  created_at TIMESTAMP
);

-- LLM 추출 결과
CREATE TABLE crawl.extracted_fields (
  company_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  source_type STRING,             -- crawl_site / crawl_news
  source_id STRING,               -- page_url or article_id
  -- 추출 필드
  product_description STRING,
  market_segment STRING,
  funding_round STRING,
  funding_amount STRING,
  investors ARRAY<STRING>,         -- 뉴스(funding) 전용
  growth_narrative STRING,         -- 뉴스(funding/performance) 전용
  tension_type STRING,
  tension_description STRING,
  culture_signals JSON,           -- {speed: [...], autonomy: [...], process: [...]}
  scale_signals JSON,
  -- 메타
  extraction_model STRING,        -- gemini-2.0-flash
  evidence_spans JSON,
  confidence FLOAT64,
  adjusted_confidence FLOAT64,
  created_at TIMESTAMP
);
```

---

## 4. 컴포넌트 상세

### 4.1 홈페이지 크롤러 (Cloud Run Job)

**컨테이너 이미지**: `Dockerfile.homepage-crawler`

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
CMD ["python", "src/homepage_crawler.py"]
```

**핵심 로직**:

```python
# src/homepage_crawler.py (핵심 흐름만 발췌)
import json, os, re, time
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from readability import Document
from bs4 import BeautifulSoup
from google.cloud import storage, bigquery

# 환경 변수
PROJECT_ID = os.environ["PROJECT_ID"]
GCS_BUCKET = os.environ["GCS_BUCKET"]
# [F4] 기업 목록은 GCS 파일에서 로드 (환경변수 크기 제한 회피)
COMPANY_LIST_GCS = os.environ["COMPANY_LIST_GCS"]  # gs://bucket/crawl/batch_xxx.json

USER_AGENT = "CompanyContextBot/1.0 (crawl for recruitment matching)"

# 페이지 유형 분류 규칙
PAGE_PATTERNS = {
    "about":    ["/about", "/company", "/about-us", "/소개"],
    "product":  ["/product", "/service", "/solution", "/features"],
    "careers":  ["/careers", "/jobs", "/recruit", "/채용", "/hiring"],
}

def classify_page(url, title=""):
    url_lower = url.lower()
    for page_type, patterns in PAGE_PATTERNS.items():
        if any(p in url_lower for p in patterns):
            return page_type
    return "other"

# [F5] robots.txt 표준 파서
def check_robots(domain_url):
    rp = RobotFileParser()
    rp.set_url(f"{domain_url}/robots.txt")
    try:
        rp.read()
    except Exception:
        return lambda url: True  # 읽기 실패 시 허용 (관례)
    return lambda url: rp.can_fetch(USER_AGENT, url)

def crawl_company(company_id, domain_url, crawl_date):
    """단일 기업 홈페이지 크롤링"""
    if not domain_url:
        return {"status": "NO_SITE", "pages": 0}

    is_allowed = check_robots(domain_url)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)

        # 메인 페이지에서 링크 수집
        try:
            page.goto(domain_url, timeout=15000, wait_until="domcontentloaded")
        except Exception as e:
            browser.close()
            return {"status": "TIMEOUT", "pages": 0, "error": str(e)}

        links = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.href)"
        )
        # 동일 도메인 + 대상 패턴만 필터 + robots.txt 체크
        parsed_domain = urlparse(domain_url).netloc
        target_urls = [domain_url]
        for link in links:
            if parsed_domain in link and link != domain_url:
                if classify_page(link) != "other" and is_allowed(link):
                    target_urls.append(link)
        target_urls = list(set(target_urls))[:10]  # [F2] 최대 10페이지로 축소

        # 각 페이지 크롤링
        for url in target_urls:
            try:
                page.goto(url, timeout=15000, wait_until="domcontentloaded")
                html = page.content()

                doc = Document(html)
                clean_html = doc.summary()
                text = BeautifulSoup(clean_html, "html.parser").get_text(
                    separator="\n", strip=True
                )

                if len(text) < 50:
                    continue

                page_type = classify_page(url, doc.title())
                results.append({
                    "url": url,
                    "page_type": page_type,
                    "title": doc.title(),
                    "text": text[:10000],
                    "text_length": len(text),
                    "status": "SUCCESS"
                })
            except Exception as e:
                results.append({"url": url, "status": "FAIL", "error": str(e)})

            time.sleep(2)  # 요청 간격 2초

        browser.close()

    save_to_gcs(company_id, crawl_date, results)
    save_to_bigquery(company_id, crawl_date, results)
    return {"status": "OK", "pages": len([r for r in results if r["status"] == "SUCCESS"])}
```

**Cloud Run Job 설정**:

| 설정 | 값 | 이유 |
|---|---|---|
| CPU | 2 vCPU | Playwright 렌더링 |
| Memory | 2Gi | headless Chrome |
| Timeout | 3600s (1시간) | [F2] 기업 15개 배치 × 10페이지 × ~17초 = ~42분 |
| Max retries | 1 | 네트워크 일시 오류 대응 |
| Parallelism | 1 | 동일 도메인 과부하 방지 |

> [F2] v1.0에서는 기업 50개/배치였으나, 페이지당 대기(2초) + 렌더링(~15초) = ~17초/페이지,
> 10페이지/기업이면 ~170초/기업. 15개 기업이면 ~42분으로 1시간 내 완료.
> 1,000개 기업은 ~67배치로 나누어 Cloud Scheduler가 순차 트리거.

### 4.2 뉴스 수집기 (Cloud Run Job)

Playwright 불필요 — 가벼운 컨테이너.

```python
# src/news_collector.py (핵심 흐름만 발췌)
import requests, json, os, hashlib, time, re
from datetime import datetime, timedelta
from readability import Document
from bs4 import BeautifulSoup
from google.cloud import storage, bigquery, secretmanager

def get_naver_api_keys():
    """Secret Manager에서 네이버 API 키 조회"""
    client = secretmanager.SecretManagerServiceClient()
    client_id = client.access_secret_version(
        name=f"projects/{PROJECT_ID}/secrets/naver-api-client-id/versions/latest"
    ).payload.data.decode()
    client_secret = client.access_secret_version(
        name=f"projects/{PROJECT_ID}/secrets/naver-api-client-secret/versions/latest"
    ).payload.data.decode()
    return client_id, client_secret

def search_naver_news(query, display=10, sort="date"):
    """네이버 뉴스 검색 API 호출 — title, description, link 반환 (본문 미포함)"""
    client_id, client_secret = get_naver_api_keys()
    resp = requests.get(
        "https://openapi.naver.com/v1/search/news.json",
        headers={
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        },
        params={"query": query, "display": display, "sort": sort},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json().get("items", [])

# [F1] 네이버 뉴스 API는 본문 미제공 → link를 따라가서 본문 크롤링
def fetch_article_body(url, timeout=10):
    """기사 URL에서 본문 텍스트 추출. 실패 시 None 반환."""
    try:
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (compatible; CompanyContextBot/1.0)"
        })
        resp.raise_for_status()
        doc = Document(resp.text)
        text = BeautifulSoup(doc.summary(), "html.parser").get_text(
            separator="\n", strip=True
        )
        return text if len(text) >= 100 else None
    except Exception:
        return None

QUERY_TEMPLATES = {
    "funding":     '"{name}" (투자 OR 시리즈 OR 펀딩 OR 유치)',
    "product":     '"{name}" (출시 OR 런칭 OR 서비스 OR 제품)',
    "org_change":  '"{name}" (CEO OR 대표이사 OR 조직개편 OR 구조조정)',
    "performance": '"{name}" (매출 OR 실적 OR 성장 OR 사용자)',
    "mna":         '"{name}" (인수 OR 합병 OR 파트너십 OR MOU)',  # 전략 문서 N3
}

MAX_ARTICLES_PER_COMPANY = 30  # 중복 제거 후 기업당 최대 보관 수

def remove_html_tags(text):
    return re.sub(r'<[^>]+>', '', text)

def collect_news(company_id, company_name, aliases, crawl_date):
    """단일 기업 뉴스 수집 + 본문 크롤링"""
    all_articles = []
    names = [company_name] + (aliases or [])

    for name in names:
        for category, template in QUERY_TEMPLATES.items():
            query = template.format(name=name)
            try:
                items = search_naver_news(query, display=10)
                for item in items:
                    article_id = hashlib.md5(item["link"].encode()).hexdigest()[:12]
                    all_articles.append({
                        "article_id": article_id,
                        "title": remove_html_tags(item["title"]),
                        "description": remove_html_tags(item["description"]),
                        "link": item["link"],
                        "pub_date": item["pubDate"],
                        "category": category,
                        "search_name": name,
                    })
            except Exception as e:
                print(f"[WARN] 검색 실패: {query} - {e}")

    # 중복 제거 (동일 link 기준)
    seen = set()
    deduped = []
    for a in all_articles:
        if a["link"] not in seen:
            seen.add(a["link"])
            deduped.append(a)

    # 관련성 필터: description에 회사명 포함 여부
    filtered = [
        a for a in deduped
        if any(n in a["title"] or n in a["description"] for n in names)
    ]

    # 기업당 최대 수 제한
    filtered = filtered[:MAX_ARTICLES_PER_COMPANY]

    # [F1] 기사 본문 크롤링 (funding, org_change, mna — LLM 추출에 본문 필요)
    for article in filtered:
        if article["category"] in ("funding", "org_change", "mna"):
            body = fetch_article_body(article["link"])
            article["body"] = body  # None이면 description만으로 추출 시도
            time.sleep(1)  # 언론사 서버 부하 방지
        else:
            article["body"] = None  # product/performance는 description으로 충분

    # GCS + BigQuery 저장
    save_news_to_gcs(company_id, crawl_date, filtered)
    save_news_to_bigquery(company_id, crawl_date, filtered)

    return {"total_collected": len(all_articles),
            "after_dedup": len(deduped),
            "after_filter": len(filtered),
            "with_body": len([a for a in filtered if a.get("body")])}
```

**Cloud Run Job 설정**:

| 설정 | 값 | 이유 |
|---|---|---|
| CPU | 1 vCPU | API 호출 + 기사 본문 크롤링 |
| Memory | 512Mi | 충분 |
| Timeout | 3600s (1시간) | [F1] 기업 15개 × 4쿼리 + 본문 크롤링 (funding/org_change만) |
| Max retries | 2 | API 일시 오류 대응 |

> [F1] 네이버 뉴스 API는 title + description(100~200자 요약)만 반환하고 기사 본문은 미제공.
> 투자 금액, 투자사 목록 등을 추출하려면 본문이 필요하므로,
> funding/org_change 카테고리 기사에 한해 link를 따라가 본문을 크롤링한다.
> product/performance 카테고리는 description만으로도 market_segment 등 추출 가능하므로 스킵.

### 4.3 LLM 추출기 (Cloud Run Job)

크롤링 결과(GCS)를 읽어 Gemini API로 정보를 추출하고 BigQuery에 저장.

```python
# src/llm_extractor.py (핵심 흐름만 발췌)
import google.genai as genai
from google.genai import types
import json

client = genai.Client(
    vertexai=True,
    project="ml-api-test-vertex",
    location="us-central1"  # Gemini API는 us-central1
)

MODEL = "gemini-2.0-flash"  # 비용 효율 + 한국어 지원

# --- 홈페이지 추출 프롬프트 ---
HOMEPAGE_PROMPT = """아래 회사 홈페이지 텍스트에서 정보를 추출하세요.
각 항목에 대해 원문 근거(evidence_span)를 반드시 인용하세요.
추출할 수 없는 항목은 null로 표기하세요.
광고성 수식어("혁신적", "최고의", "세계적")는 제거하고 팩트만 추출하세요.

페이지 유형: {page_type}

추출 항목:
1. product_description: 회사가 하는 일 (1~3문장, 팩트 중심)
2. market_segment: 타겟 시장 (예: "B2B SaaS", "헬스케어 플랫폼")
3. scale_signals: 규모 단서 (직원수, 고객수, 거점 등 수치 포함 표현)
4. culture_signals: 일하는 방식 단서 (speed/autonomy/process 관련)
   - speed: 배포 주기, 스프린트, 빠른 실행 관련
   - autonomy: 오너십, 자율, 의사결정 관련
   - process: 코드리뷰, 문서화, 테스트, RFC 관련
   주의: "수평적", "패밀리", "열정" 등은 광고성이므로 제외

JSON 형식으로 응답하세요.

[텍스트]
{text}"""

# --- 뉴스 추출 프롬프트 (투자 기사용) ---
NEWS_FUNDING_PROMPT = """아래 투자 관련 기사에서 정보를 추출하세요.
반드시 원문에서 직접 인용(evidence_span)하세요.
추측("~전망", "~것으로 보인다")은 confidence를 낮게 표기하세요.

추출 항목:
1. funding_round: 투자 라운드 (Seed/Pre-A/Series A/B/C/D+/IPO) — null 가능
2. funding_amount: 금액 (숫자 + 단위) — null 가능
3. investors: 투자사 이름 목록 — [] 가능
4. growth_narrative: 성장 관련 수치/사실 — null 가능
5. use_of_funds: 투자금 사용 계획 — null 가능

JSON 형식으로 응답하세요.

[기사 텍스트]
{text}"""

# --- 뉴스 추출 프롬프트 (조직 변화용) ---
NEWS_ORG_PROMPT = """아래 기업 뉴스에서 조직/경영 변화 정보를 추출하세요.
반드시 원문에서 직접 인용(evidence_span)하세요.

추출 항목:
1. change_type: CEO 교체 / CxO 영입 / 조직개편 / 구조조정 / 감원 / 기타 — null 가능
2. tension_type: 암시되는 내부 긴장 유형 — null 가능
   (founder_vs_professional_mgmt / scaling_leadership / efficiency_vs_growth /
    structure_optimization / portfolio_restructuring)
3. tension_description: 긴장에 대한 1문장 설명 — null 가능

JSON 형식으로 응답하세요.

[기사 텍스트]
{text}"""

# --- 뉴스 추출 프롬프트 (제품/실적용 — description 기반 간이 추출) ---
NEWS_PRODUCT_PROMPT = """아래 제품/서비스 또는 실적 관련 뉴스 요약에서 정보를 추출하세요.
반드시 원문에서 직접 인용(evidence_span)하세요.

추출 항목:
1. product_name: 제품/서비스명 — null 가능
2. market_segment: 타겟 시장 (예: "B2B SaaS", "헬스케어") — null 가능
3. traction_data: 성과 수치 (매출, MAU, 거래액, 성장률 등) — null 가능
4. growth_narrative: 성장 관련 서술 — null 가능

JSON 형식으로 응답하세요.

[뉴스 요약]
{text}"""

# [F6] Gemini API rate limit 대응
import time as _time
_last_gemini_call = 0.0

def gemini_extract(prompt):
    """Gemini API 호출 + QPM throttle + 재시도"""
    global _last_gemini_call
    # 최소 5초 간격 (12 QPM — 무료 15 QPM 이내 안전 마진)
    elapsed = _time.time() - _last_gemini_call
    if elapsed < 5.0:
        _time.sleep(5.0 - elapsed)

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )
            _last_gemini_call = _time.time()
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {"_error": "JSON parse failed", "_raw": response.text[:500]}
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                _time.sleep(30)  # rate limit hit — 30초 대기 후 재시도
                continue
            return {"_error": str(e)}

def extract_from_page(company_id, page_type, text):
    """홈페이지 페이지에서 정보 추출"""
    prompt = HOMEPAGE_PROMPT.format(page_type=page_type, text=text[:8000])
    return gemini_extract(prompt)

def extract_from_article(company_id, category, text):
    """뉴스 기사에서 정보 추출"""
    if category == "funding":
        prompt = NEWS_FUNDING_PROMPT.format(text=text[:6000])
    elif category in ("org_change", "mna"):
        prompt = NEWS_ORG_PROMPT.format(text=text[:6000])
    elif category in ("product", "performance"):
        prompt = NEWS_PRODUCT_PROMPT.format(text=text[:3000])  # description 기반 간이 추출
    else:
        return None

    result = gemini_extract(prompt)
    if result and "_error" not in result:
        result["_category"] = category
    return result
```

**Cloud Run Job 설정**:

| 설정 | 값 | 이유 |
|---|---|---|
| CPU | 1 vCPU | API 호출 대기 위주 |
| Memory | 1Gi | JSON 처리 |
| Timeout | 3600s | 기업 50개 × 페이지/기사당 추출 |
| Max retries | 1 | Gemini API 재시도는 코드 내부에서 처리 |

### 4.4 파일럿 실행 스크립트 [F3]

파일럿 단계에서는 Cloud Workflows 대신 **단순 Python 스크립트**로 순차 실행한다.
Workflows는 Phase 4(운영 단계)에서 도입.

```python
# scripts/run_pilot.py — 파일럿 실행 (로컬 또는 Cloud Shell에서 수동 실행)
"""
사용법:
  python scripts/run_pilot.py --companies 10 --crawl-date 2026-03-10
"""
import argparse, json
from google.cloud import bigquery

def get_targets(n):
    bq = bigquery.Client()
    query = f"""
        SELECT company_id, company_name, aliases, domain_url
        FROM crawl.company_targets
        WHERE is_active = TRUE
        AND (last_homepage_crawl IS NULL
             OR TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), last_homepage_crawl, DAY) >= 30)
        LIMIT {n}
    """
    return [dict(row) for row in bq.query(query)]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--companies", type=int, default=10)
    parser.add_argument("--crawl-date", required=True)
    args = parser.parse_args()

    targets = get_targets(args.companies)
    print(f"[1/4] 대상 기업 {len(targets)}개 조회 완료")

    # [F4] 기업 목록을 GCS에 업로드 (Cloud Run Job에서 읽도록)
    upload_targets_to_gcs(targets, args.crawl_date)

    # Step 2: 홈페이지 크롤링 (Cloud Run Job 트리거)
    print("[2/4] 홈페이지 크롤링 시작...")
    trigger_cloud_run_job("homepage-crawler", args.crawl_date)

    # Step 3: 뉴스 수집 (Cloud Run Job 트리거)
    print("[3/4] 뉴스 수집 시작...")
    trigger_cloud_run_job("news-collector", args.crawl_date)

    # Step 4: LLM 추출 (Cloud Run Job 트리거)
    print("[4/4] LLM 추출 시작...")
    trigger_cloud_run_job("llm-extractor", args.crawl_date)

    print("파일럿 완료. BigQuery에서 결과 확인:")
    print("  SELECT * FROM crawl.extracted_fields ORDER BY created_at DESC LIMIT 20;")

if __name__ == "__main__":
    main()
```

### 4.5 Cloud Workflows (운영 단계, Phase 4)

파일럿 검증 완료 후 자동화에 사용. 기업 목록을 GCS 파일로 전달.

```yaml
# workflows/crawl-pipeline.yaml (Phase 4에서 배포)
main:
  steps:
    - init:
        assign:
          - project_id: "ml-api-test-vertex"
          - region: "asia-northeast3"
          - batch_size: 15

    - get_and_upload_targets:
        call: http.post
        args:
          url: ${"https://" + region + "-run.googleapis.com/v2/projects/" + project_id + "/locations/" + region + "/jobs/batch-prep:run"}
          auth:
            type: OAuth2
        result: prep_result

    - run_homepage_crawl:
        call: http.post
        args:
          url: ${"https://" + region + "-run.googleapis.com/v2/projects/" + project_id + "/locations/" + region + "/jobs/homepage-crawler:run"}
          auth:
            type: OAuth2
        result: homepage_result

    - run_news_collect:
        call: http.post
        args:
          url: ${"https://" + region + "-run.googleapis.com/v2/projects/" + project_id + "/locations/" + region + "/jobs/news-collector:run"}
          auth:
            type: OAuth2
        result: news_result

    - run_extraction:
        call: http.post
        args:
          url: ${"https://us-central1-run.googleapis.com/v2/projects/" + project_id + "/locations/us-central1/jobs/llm-extractor:run"}
          auth:
            type: OAuth2
        result: extract_result
```

---

## 5. 실행 계획

### Phase 0: 환경 준비 (2일)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 0-1 | 크롤링 대상 기업 목록 작성 | `crawl.company_targets` 테이블 | 아래 [F7] domain_url 확보 방법 참조 |
| 0-2 | 네이버 뉴스 API 키 발급 | Secret Manager 등록 | 일 25,000건 무료 |
| 0-3 | BigQuery 데이터셋 + 테이블 생성 | `crawl` 데이터셋 | 위 스키마 4개 테이블 |
| 0-4 | GCS 버킷 구조 생성 | `gs://ml-api-test-vertex/crawl/` | 폴더 구조 |
| 0-5 | Artifact Registry 레포 생성 | `crawl-images` 레포 | 컨테이너 이미지용 |

**[F7] 기업 domain_url 확보 방법**:

| 방법 | 대상 | 커버리지 |
|---|---|---|
| NICE 기업 정보에서 웹사이트 필드 추출 | NICE 보유 기업 | 중 (필드가 있는 경우) |
| 자사 JD에서 회사 URL 추출 | JD 보유 기업 | 중 (JD에 명시된 경우) |
| 네이버 검색 `"{회사명}" site:` 첫 결과 | 전체 | 높음 (자동화 가능) |
| 수동 확인 (파일럿 10개) | 파일럿 | 100% |

파일럿 10개는 수동 확인, 이후 확장 시 네이버 검색으로 자동 추출 + 수동 검수 병행.

### Phase 1: 홈페이지 크롤러 구축 + 파일럿 (3일)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 1-1 | Playwright 크롤러 코드 작성 | `src/homepage_crawler.py` | robots.txt 준수 포함 |
| 1-2 | Dockerfile 작성 + 이미지 빌드 | `Dockerfile.homepage-crawler` | Playwright + Chrome |
| 1-3 | Cloud Run Job 배포 | Job 리소스 | asia-northeast3 |
| 1-4 | **파일럿: 기업 10개 크롤링** | GCS + BigQuery 결과 | 수동 트리거 |
| 1-5 | 파일럿 결과 검수 | 품질 리포트 | 페이지 분류 정확도, 텍스트 추출 품질 |

### Phase 2: 뉴스 수집기 구축 + 파일럿 (2일, Phase 1과 병렬)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 2-1 | 뉴스 수집기 코드 작성 | `src/news_collector.py` | 네이버 API 연동 |
| 2-2 | Dockerfile 작성 + Cloud Run Job 배포 | Job 리소스 | |
| 2-3 | **파일럿: 기업 10개 뉴스 수집** | GCS + BigQuery 결과 | 수집량/관련성 확인 |

### Phase 3: LLM 추출기 구축 + 파일럿 (3일)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 3-1 | 추출 프롬프트 작성 (홈페이지 1종 + 뉴스 3종) | 프롬프트 셋 | funding, org_change/mna, product/performance |
| 3-2 | LLM 추출기 코드 작성 | `src/llm_extractor.py` | Gemini API |
| 3-3 | Dockerfile 작성 + Cloud Run Job 배포 | Job 리소스 | us-central1 |
| 3-4 | **파일럿: 기업 10개 추출** | BigQuery 결과 | 추출 품질 Human eval |
| 3-5 | 프롬프트 튜닝 (파일럿 결과 기반) | 개선된 프롬프트 | 1~2회 반복 |

### Phase 4: 통합 + 배치 운영 (2일)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 4-1 | Cloud Workflows 작성 + 배포 | `crawl-pipeline.yaml` | Step 간 연결 |
| 4-2 | Cloud Scheduler 설정 | 30일 주기 cron | |
| 4-3 | **전체 파이프라인 통합 테스트 (기업 10개)** | End-to-end 결과 | |
| 4-4 | `crawl.company_crawl_summary` 집계 테이블 생성 | BigQuery 테이블 | 전략 문서 5.2절 스키마 참조 |
| 4-5 | CompanyContext 통합 뷰 작성 | BigQuery VIEW | 기존 NICE + 크롤링 결합 |

---

## 6. 비용 추정

### 기업 100개 파일럿 기준

| 항목 | 산출 근거 | 비용 |
|---|---|---|
| Cloud Run (홈페이지) | 2 vCPU × 2Gi × ~1시간 | ~$0.20 |
| Cloud Run (뉴스) | 1 vCPU × 512Mi × ~30분 | ~$0.05 |
| Cloud Run (LLM 추출) | 1 vCPU × 1Gi × ~1시간 | ~$0.10 |
| Gemini API (추출) | 100기업 × ~15건 × ~3K tokens | ~$0.50 |
| BigQuery | 소량 쿼리 | ~$0.10 |
| GCS | ~1GB | ~$0.02 |
| 네이버 뉴스 API | 무료 | $0 |
| **파일럿 합계** | | **~$1** |

### 기업 1,000개 월간 운영 기준

| 항목 | 비용/월 |
|---|---|
| Cloud Run (3 Jobs) | ~$5 |
| Gemini API | ~$5 |
| BigQuery + GCS | ~$2 |
| Cloud Scheduler + Workflows | ~$0 (무료 티어) |
| **월간 합계** | **~$12** |

---

## 7. 모니터링

| 지표 | 수집 방법 | 알림 조건 |
|---|---|---|
| 크롤링 성공률 | BigQuery: `homepage_pages.crawl_status` 집계 | 성공률 < 70% |
| 뉴스 수집량 | BigQuery: `news_articles` 기업당 건수 | 평균 < 2건/기업 |
| LLM 추출 성공률 | BigQuery: `extracted_fields._error` IS NULL 비율 | 성공률 < 85% |
| Gemini API 비용 | Cloud Billing Alerts | 월 $20 초과 |
| Workflow 실행 상태 | Cloud Logging | 실패 시 알림 |

```sql
-- 크롤링 품질 대시보드 쿼리
SELECT
  DATE(created_at) AS crawl_date,
  COUNT(DISTINCT company_id) AS companies_crawled,
  COUNTIF(crawl_status = 'SUCCESS') AS pages_success,
  COUNTIF(crawl_status != 'SUCCESS') AS pages_failed,
  ROUND(COUNTIF(crawl_status = 'SUCCESS') / COUNT(*) * 100, 1) AS success_rate_pct
FROM crawl.homepage_pages
GROUP BY 1
ORDER BY 1 DESC;
```

---

## 8. 파일럿 성공 기준

| 지표 | 기준 | 비고 |
|---|---|---|
| 홈페이지 크롤링 성공률 | 80%+ (10개 중 8개 이상 1페이지+ 수집) | NO_SITE 제외 |
| 뉴스 수집 커버리지 | 70%+ (10개 중 7개 이상 1건+ 수집) | |
| LLM 추출 성공률 | 90%+ (유효 JSON 반환) | |
| product_description 활성화 | 60%+ | 크롤링 후 non-null 비율 |
| 추출 정확도 (Human eval 10건) | 70%+ (팩트 일치) | 랜덤 샘플링 |
| 전체 파이프라인 비용 | < $5 (100기업 기준) | |
