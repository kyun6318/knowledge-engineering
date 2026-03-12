# Phase 4: 외부 보강 + 품질 + 운영 (6주, Week 20-25)

> **목적**: 홈페이지/뉴스 크롤링으로 CompanyContext를 보강하고,
> 품질 평가 + 자동화 + 운영 인프라를 구축하여 프로덕션 운영 상태로 전환.
>
> **데이터 확장**: Graph + Matching → **+ 기업 인텔리전스 (product, funding, culture, tension)**
>
> **에이전트 역량 변화**:
>   - "최근 시리즈C 투자받은 AI 스타트업" → 기업 인텔리전스 기반 필터
>   - "조직 변경이 있었던 기업의 채용" → 텐션 신호 기반 필터
>   - 일일 자동 증분 업데이트
>   - 프로덕션 운영 (자동화 + 모니터링 + 인수인계)
>
> **인력**: DE 1명 + MLE 1명 풀타임 + 도메인 전문가 1명 파트타임 (품질 평가)

---

## Pre-Phase 4: 크롤링 법적 검토 (1주, Week 19 병행)

### 법무팀 협력 체크리스트

```
□ 기업 홈페이지 크롤링 저작권법 적합성
  - 공공 영역 데이터로 간주되는 범위 확인
  - 회사소개/제품 페이지 vs. 회원가입 필수 영역 구분
  - 로봇배제표준(robots.txt) 준수 의무 확인

□ 네이버 뉴스 API 이용약관
  - 크롤링 vs. API 사용 구분
  - 기사 원본 저장 금지 확인
  - LLM 입력으로의 활용 가능 범위

□ 정보통신망법 관련 리스크
  - 접근 제한 기술 (개인정보 인증, 세션) 우회 금지
  - rate limiting 설정 (2초 간격 이상)
  - 서버 부하 체크 (동시 요청 제한)

□ 저작권법 + LLM 입력 활용
  - 원문 미보관 정책의 법적 리스크 경감 효과
  - 추출 정보 (투자 라운드, 팀 규모 등)의 재사용 가능성
  - 학습 데이터로의 활용 가능성

□ 정책 문서화
  - robots.txt 준수 자동화 (crawler-robots library)
  - 크롤링 대상 기업 수 제한 (초기 1,000개)
  - 원본 미보관 정책 명시
  - 크롤링 거부 기업 white-list 유지
```

### 크롤링 정책 문서 (src/config/CRAWLING_POLICY.md)

```markdown
# 기업 정보 크롤링 정책

## 준칙

1. **robots.txt 준수**: 모든 크롤러는 robots.txt를 파싱하여 크롤링 가능 경로만 접근
2. **Rate Limiting**: 동일 도메인 요청 간 최소 2초 간격 유지
3. **User-Agent**: `GraphRAG-Bot/1.0 (+https://graphrag.example.com/bot)`
4. **타임아웃**: 1페이지 로드 타임아웃 30초
5. **동시 요청**: 최대 5 concurrent tasks

## 크롤링 대상

초기 단계: 1,000개 기업 (NICE 대분류별 균형)
- IT: 300개
- 금융: 200개
- 제조: 200개
- 기타: 300개

## 원본 미보관 정책

크롤링된 웹페이지:
- 원본 HTML 저장 안 함
- 추출된 텍스트만 일시 저장 (처리 후 삭제)
- 메타데이터 (URL, 제목, 크롤링 시간) 만 영구 저장
- GCS 정책: `retention_days=7` (자동 삭제)

## 거부 기업

크롤링 불가:
- robots.txt에 명시적 Disallow
- 접근 제한 (IP 차단, 인증 필수) 기업
- 유저 제시 거부 기업

## 모니터링

- 일일 크롤링 성공률 추적
- HTTP 429/403 에러 통계
- 도메인별 응답 시간 모니터링
```

---

## 4-1. 홈페이지/뉴스 크롤링 파이프라인 (4주) — Week 20-23

### 개요
기업의 제품, 시장, 팀 규모, 최근 소식 등을 자동으로 수집.
LLM 추출로 구조화된 CompanyContext 필드 생성.

### Sub-phases

#### 4-1-1: 크롤러 인프라 구축 (1주) — Week 20

**Tasks (4-1-1-1 ~ 4-1-1-3)**

**T4.1.1.1**: Cloud Run Job + Playwright Docker 설정 (DE)
```dockerfile
# Dockerfile (crawler image)
FROM mcr.microsoft.com/playwright/python:v1.40-focal

WORKDIR /app

COPY requirements-crawler.txt .
RUN pip install -r requirements-crawler.txt

COPY src/crawlers /app/src/crawlers
COPY src/config /app/src/config
COPY data/company_crawl_targets.json /app/data/

ENV PYTHONUNBUFFERED=1
ENV CRAWLER_BATCH_SIZE=100
ENV CRAWLER_TIMEOUT=30

ENTRYPOINT ["python", "-m", "src.crawlers.orchestrator"]
```

```bash
# 빌드 및 푸시
IMAGE="gcr.io/graphrag-kg/kg-crawler:latest"
docker build -t $IMAGE .
docker push $IMAGE

# Cloud Run Job 생성
gcloud run jobs create kg-crawl-homepage \
  --image=$IMAGE \
  --command="python,-m,src.crawlers.orchestrator" \
  --args="--mode=homepage" \
  --tasks=10 \
  --max-retries=2 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=kg-crawler@graphrag-kg.iam.gserviceaccount.com \
  --region=asia-northeast3 \
  --env-vars="BATCH_SIZE=100,CONCURRENT_TASKS=5"

gcloud run jobs create kg-crawl-news \
  --image=$IMAGE \
  --command="python,-m,src.crawlers.orchestrator" \
  --args="--mode=news" \
  --tasks=5 \
  --max-retries=1 \
  --cpu=1 --memory=2Gi \
  --task-timeout=1800 \
  --service-account=kg-crawler@graphrag-kg.iam.gserviceaccount.com \
  --region=asia-northeast3 \
  --env-vars="BATCH_SIZE=500"
```

**T4.1.1.2**: Rate limiting + robots.txt + Error handling (DE)
```python
# src/crawlers/base_crawler.py

import asyncio
import httpx
from datetime import datetime, timedelta
from urllib.robotparser import RobotFileParser

class BaseCrawler:
    """
    기본 크롤러: rate limiting, robots.txt, 에러 처리
    """

    def __init__(self, domain: str, rate_limit_seconds: float = 2.0):
        self.domain = domain
        self.rate_limit_seconds = rate_limit_seconds
        self.last_request_time = None
        self.robot_parser = RobotFileParser(f"https://{domain}/robots.txt")
        self.robot_parser.read()
        self.session = None

    async def crawl(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        URL 크롤링.
        Returns: HTML content 또는 None (실패)
        """

        # 1. robots.txt 확인
        if not self.robot_parser.can_fetch("GraphRAG-Bot/1.0", url):
            print(f"robots.txt Disallow: {url}")
            return None

        # 2. Rate limiting
        await self._rate_limit()

        # 3. HTTP 요청
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    url,
                    headers={
                        'User-Agent': 'GraphRAG-Bot/1.0 (+https://graphrag.example.com/bot)',
                        'Accept': 'text/html,application/xhtml+xml',
                    },
                    follow_redirects=True,
                )

                # 상태 코드 확인
                if response.status_code == 429:
                    # Rate limit exceeded
                    print(f"429 Too Many Requests: {url}")
                    return None
                elif response.status_code == 403:
                    print(f"403 Forbidden: {url}")
                    return None
                elif response.status_code != 200:
                    print(f"HTTP {response.status_code}: {url}")
                    return None

                return response.text

        except asyncio.TimeoutError:
            print(f"Timeout: {url}")
            return None
        except httpx.ConnectError as e:
            print(f"Connection error: {url} - {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {url} - {e}")
            return None

    async def _rate_limit(self):
        """Rate limiting 적용"""
        if self.last_request_time:
            elapsed = (datetime.utcnow() - self.last_request_time).total_seconds()
            wait_time = max(0, self.rate_limit_seconds - elapsed)
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        self.last_request_time = datetime.utcnow()
```

**T4.1.1.3**: 공통 에러 처리 + Retry 전략 (DE)
```python
# src/crawlers/retry_strategy.py

from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
)
async def crawl_with_retry(url: str) -> Optional[str]:
    """지수 백오프 재시도"""
    return await BaseCrawler(url).crawl(url)

# Retry policy by error type
RETRY_POLICIES = {
    'timeout': {'max_retries': 2, 'backoff': 'exponential'},
    'connection_error': {'max_retries': 3, 'backoff': 'exponential'},
    '429_rate_limit': {'max_retries': 1, 'backoff': 'exponential', 'min_wait': 60},
    '503_service_unavailable': {'max_retries': 2, 'backoff': 'exponential'},
    'robots_txt_disallow': {'max_retries': 0},  # 재시도 안 함
}
```

#### 4-1-2: 홈페이지 크롤러 (1주) — Week 21

**Tasks (4-1-2-1 ~ 4-1-2-3)**

**T4.1.2.1**: 타겟 페이지 감지 + 다운로드 (DE)
```python
# src/crawlers/homepage_crawler.py

from readability import Document
from urllib.parse import urljoin, urlparse

class HomepageCrawler(BaseCrawler):
    """
    기업 홈페이지 크롤링.
    타겟: about, product, careers, 뉴스룸 페이지
    """

    # 페이지 유형별 URL 패턴
    PAGE_PATTERNS = {
        'about': [
            r'/about',
            r'/company',
            r'/(회사소개|기업소개)',
        ],
        'product': [
            r'/product',
            r'/service',
            r'/solution',
            r'/(제품|서비스)',
        ],
        'careers': [
            r'/career',
            r'/recruit',
            r'/(채용|구인)',
        ],
        'newsroom': [
            r'/news',
            r'/press',
            r'/blog',
            r'/(뉴스|보도자료)',
        ],
    }

    def __init__(self, domain: str, company_name: str):
        super().__init__(domain)
        self.company_name = company_name
        self.base_url = f"https://{domain}"

    async def crawl_pages(self) -> dict:
        """
        회사 홈페이지의 주요 페이지 크롤링.
        Returns: {
            'about': {...},
            'product': {...},
            'careers': {...},
            'newsroom': {...}
        }
        """
        results = {}

        for page_type, patterns in self.PAGE_PATTERNS.items():
            # 1. URL 후보 생성
            url_candidates = self._generate_url_candidates(page_type, patterns)

            # 2. 각 URL 시도
            for url in url_candidates:
                html = await super().crawl(url)
                if html:
                    # 본문 추출
                    text = self._extract_body_text(html)
                    if len(text) > 100:  # 충분한 본문
                        results[page_type] = {
                            'url': url,
                            'text': text,
                            'crawl_date': datetime.utcnow().isoformat(),
                        }
                        break

        return results

    def _extract_body_text(self, html: str) -> str:
        """
        HTML에서 본문 텍스트 추출.
        readability-lxml 사용.
        """
        try:
            doc = Document(html)
            title = doc.short_title()
            content = doc.summary()

            # 태그 제거
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)

            # 공백 정규화
            import re
            text = re.sub(r'\s+', ' ', text)

            return text[:5000]  # 토큰 수 제한 (max 5K chars)

        except Exception as e:
            print(f"Error extracting body: {e}")
            return ""

    def _generate_url_candidates(self, page_type: str, patterns: list) -> list:
        """URL 후보 생성"""
        candidates = []

        for pattern in patterns:
            # 정확한 패턴 매칭
            url = urljoin(self.base_url, pattern.strip('/'))
            candidates.append(url)

        # 한국어 URL도 추가
        if page_type == 'about':
            candidates.append(f"{self.base_url}/회사소개")
        elif page_type == 'careers':
            candidates.append(f"{self.base_url}/채용")

        return candidates
```

**T4.1.2.2**: 한국 기업 특화 (DE)
```python
# src/crawlers/korean_business_crawler.py

class KoreanBusinessCrawler(HomepageCrawler):
    """
    한국 기업 홈페이지 특화.
    - NICE 기업 프로필 링크 추출
    - 사업보고서 다운로드 (상장사)
    - 자회사/계열사 추출
    """

    # 한국 기업 특화 정보 소스
    NICE_BASE_URL = "https://www.nicebizinfo.com"  # (실제 API endpoint)
    DART_BASE_URL = "https://dart.fss.or.kr"  # 상장사 공시

    async def crawl_nice_profile(self, company_id: str) -> Optional[dict]:
        """NICE 기업 프로필"""
        url = f"{self.NICE_BASE_URL}/firm/{company_id}"
        html = await self.crawl(url)

        if html:
            # 직원 수, 연매출 등 추출
            return self._parse_nice_profile(html)

        return None

    async def crawl_dart_reports(self, company_name: str) -> list:
        """DART 공시 수집 (상장사)"""
        reports = []

        # DART API 호출
        try:
            import requests
            response = requests.get(
                f"{self.DART_BASE_URL}/api/company/search",
                params={'crp_nm': company_name, 'start_page': 1}
            )

            if response.status_code == 200:
                data = response.json()
                for item in data.get('list', []):
                    reports.append({
                        'corp_code': item['corp_code'],
                        'report_nm': item['report_nm'],
                        'report_date': item['report_date'],
                    })

        except Exception as e:
            print(f"DART API error: {e}")

        return reports

    def _parse_nice_profile(self, html: str) -> dict:
        """NICE 프로필 파싱"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        # 직원 수, 연매출 등 추출 (NICE 페이지 구조에 맞게)
        profile = {
            'employee_count': None,
            'annual_revenue': None,
            'founded_year': None,
        }

        # 예: <span class="employee-count">150명</span>
        elem = soup.find('span', class_='employee-count')
        if elem:
            profile['employee_count'] = int(elem.text.replace('명', ''))

        return profile
```

**T4.1.2.3**: GCS 저장 + BigQuery 메타데이터 (DE)
```python
# src/crawlers/homepage_storage.py

from google.cloud import storage, bigquery

class HomepageStorage:
    """홈페이지 크롤링 결과 저장"""

    def __init__(self, gcs_bucket: str, bq_dataset: str):
        self.gcs_client = storage.Client()
        self.bq_client = bigquery.Client()
        self.bucket = self.gcs_client.bucket(gcs_bucket)
        self.dataset_id = bq_dataset

    async def save_crawl_result(self,
                                company_id: str,
                                page_type: str,
                                crawl_result: dict) -> str:
        """
        홈페이지 크롤링 결과 저장.
        Returns: GCS path
        """

        # 1. 원문 텍스트 GCS 저장 (일시, 7일 후 삭제)
        gcs_path = f"crawl/homepage/{company_id}/{page_type}/{datetime.utcnow().isoformat()}.txt"
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_string(
            crawl_result['text'],
            content_type='text/plain',
        )

        # 7일 후 자동 삭제 설정
        blob.metadata = {'deletion_date': (datetime.utcnow() + timedelta(days=7)).isoformat()}

        # 2. BigQuery 메타데이터 적재
        row = {
            'company_id': company_id,
            'page_type': page_type,
            'source_url': crawl_result['url'],
            'crawl_date': datetime.utcnow().isoformat(),
            'page_title': '...',  # extracted from HTML
            'body_length': len(crawl_result['text']),
            'gcs_text_path': gcs_path,
            'crawl_status': 'success',
        }

        errors = self.bq_client.insert_rows_json(
            f"{self.dataset_id}.crawl_raw_data",
            [row]
        )

        if errors:
            print(f"BigQuery insert error: {errors}")

        return gcs_path
```

#### 4-1-3: 뉴스 수집기 (1주, 병행) — Week 21

**Tasks (4-1-3-1 ~ 4-1-3-3)**

**T4.1.3.1**: 네이버 뉴스 API 수집 (DE)
```python
# src/crawlers/naver_news_collector.py

import asyncio
import httpx
from datetime import datetime, timedelta

class NaverNewsCollector:
    """
    네이버 뉴스 수집.
    - 무료 API (검색 결과)
    - 펀딩/M&A/조직 변경 카테고리
    """

    NAVER_API_BASE = "https://openapi.naver.com/v1/search"
    MAX_RESULTS = 100

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    async def search_news(self,
                         company_name: str,
                         keywords: list,
                         days_back: int = 30) -> list:
        """
        회사별 뉴스 검색.
        Args:
            company_name: 회사명
            keywords: ['펀딩', '투자', '시리즈A', ...]
            days_back: 몇 일 이내의 뉴스
        """

        articles = []
        start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        for keyword in keywords:
            query = f"{company_name} {keyword}"

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.NAVER_API_BASE}/news.json",
                        params={
                            'query': query,
                            'display': 100,
                            'sort': 'date',
                        },
                        headers={
                            'X-Naver-Client-Id': self.client_id,
                            'X-Naver-Client-Secret': self.client_secret,
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()

                        for item in data.get('items', []):
                            articles.append({
                                'source': 'naver_news',
                                'title': item['title'],
                                'link': item['link'],
                                'source_media': item.get('source', 'Unknown'),
                                'publish_date': item.get('pubDate', ''),
                                'description': item.get('description', ''),
                                'keyword': keyword,
                            })

                    # Rate limiting
                    await asyncio.sleep(0.5)

            except Exception as e:
                print(f"News API error: {company_name}, {keyword} - {e}")

        return articles

    def categorize_articles(self, articles: list) -> dict:
        """
        뉴스 카테고리화.
        Returns: {
            'funding': [...],  # 투자, 펀딩, 시리즈A/B/C
            'org_change': [...],  # M&A, 인수, 합병
            'personnel': [...],  # 임원 임명, 리더십 변경
            'product': [...],  # 제품 출시, 서비스 확대
        }
        """

        categorized = {
            'funding': [],
            'org_change': [],
            'personnel': [],
            'product': [],
        }

        funding_keywords = ['펀딩', '투자', '시리즈', '라운드', '자금조달']
        org_keywords = ['인수', 'M&A', '합병', '인수합병']
        personnel_keywords = ['임명', '리더십', '임원', 'CEO']
        product_keywords = ['출시', '론칭', '출범', '서비스 개시']

        for article in articles:
            title = article['title'].lower()

            if any(kw in title for kw in funding_keywords):
                categorized['funding'].append(article)
            elif any(kw in title for kw in org_keywords):
                categorized['org_change'].append(article)
            elif any(kw in title for kw in personnel_keywords):
                categorized['personnel'].append(article)
            elif any(kw in title for kw in product_keywords):
                categorized['product'].append(article)

        return categorized
```

**T4.1.3.2**: 기사 원문 크롤링 (DE)
```python
# src/crawlers/news_body_crawler.py

class NewsBodyCrawler(BaseCrawler):
    """뉴스 기사 원문 추출"""

    async def crawl_article(self, news_url: str) -> Optional[str]:
        """
        뉴스 기사 원문 크롤링.
        readability로 본문 추출.
        """

        # 도메인별 봇 규칙 적용
        domain = self._extract_domain(news_url)
        await self._rate_limit()

        html = await super().crawl(news_url, timeout=15)

        if not html:
            return None

        # 본문 추출
        from readability import Document
        try:
            doc = Document(html)
            content = doc.summary()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)

            # 정규화
            import re
            text = re.sub(r'\s+', ' ', text)

            return text[:3000]

        except Exception as e:
            print(f"Article parsing error: {e}")
            return None

    def _extract_domain(self, url: str) -> str:
        """URL에서 도메인 추출"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc
```

**T4.1.3.3**: BigQuery 적재 (DE)
```sql
-- crawl_raw_data 테이블에 뉴스 데이터도 함께 적재
INSERT INTO graphrag_kg.crawl_raw_data (
  company_id,
  source_type,
  source_id,
  crawl_date,
  title,
  url,
  page_type,
  category,
  source_media,
  publish_date,
  is_press_release,
  body_length,
  crawl_status,
  gcs_text_path,
  created_at
)
SELECT
  company_id,
  'news' as source_type,
  news_id,
  CURRENT_DATE(),
  title,
  url,
  NULL,
  category,
  source_media,
  PARSE_DATE('%Y-%m-%d', publish_date),
  is_press_release,
  body_length,
  'success',
  gcs_path,
  CURRENT_TIMESTAMP()
FROM staging.naver_news_raw
WHERE company_id IS NOT NULL;
```

#### 4-1-4: LLM 추출 (1주) — Week 22

**Tasks (4-1-4-1 ~ 4-1-4-2)**

**T4.1.4.1**: LLM 추출 프롬프트 (MLE)
```
# src/prompts/extract_company_intelligence.txt

당신은 기업 뉴스 및 웹사이트에서 중요한 정보를 추출하는 전문가입니다.

## 입력

회사명: {company_name}
출처 유형: {source_type}  (homepage|news)
페이지 유형: {page_type}  (about|product|careers|newsroom)
텍스트:
{text}

## 출력 필드 정의

1. **product_description** (str, 최대 300 tokens)
   - 회사의 주요 제품/서비스
   - 고객 가치 제안
   - 기술 스택 (있으면)

2. **market_segment** (str)
   - 대상 시장 (B2B, B2C, B2G, P2P)
   - 주요 산업 (금융, 헬스케어, 물류 등)
   - 지역 (국내, 글로벌)

3. **funding** (object)
   - round_type: 'seed', 'series_a', 'series_b', ...
   - amount_usd: number (있으면)
   - investors: string array (회사명 리스트)
   - date: string (YYYY-MM)

4. **growth_narrative** (str)
   - 회사의 성장 스토리
   - "최근 시리즈B 투자로 팀 확대" 같은 신호
   - 시장 확대 계획

5. **tension_type** (str, 선택사항)
   - 'M&A' (인수/합병)
   - 'Restructuring' (조직 개편)
   - 'Leadership_Change' (임원 변경)
   - 'Major_Pivot' (사업 방향 전환)
   - 'Downsizing' (인원 감축)

6. **tension_description** (str, 선택사항)
   - tension 신호의 구체적 내용

7. **culture_signals** (object, 선택사항)
   - team_size: int
   - remote_friendly: bool
   - diversity_focus: bool
   - learning_culture: bool
   - signals: string array

8. **scale_signals** (object, 선택사항)
   - growth_rate: str  ('rapid', 'steady', 'declining')
   - market_position: str  ('leader', 'challenger', 'emerging')
   - international_presence: bool

## 출력 포맷

```json
{
  "product_description": "...",
  "market_segment": {...},
  "funding": {...},
  "growth_narrative": "...",
  "tension_type": null,
  "tension_description": null,
  "culture_signals": {...},
  "scale_signals": {...},
  "extraction_confidence": 0.85,
  "evidence_spans": ["텍스트의 일부", "..."],
  "missing_fields": ["tension_type", "funding"]
}
```

## 주의사항

- 텍스트에 명시되지 않은 정보는 생성하지 마세요 (hallucination 방지)
- confidence는 증거의 명확성 기반으로만 부여하세요
- evidence_spans에는 원문의 정확한 구간을 인용하세요
- 숫자 정보 (펀딩 액수, 직원 수)는 정확히 추출하세요
```

**T4.1.4.2**: Batch API 추출 실행 (MLE)
```python
# src/extract/crawl_intelligence_extraction.py

from google.ai.generativelanguage_v1 import BatchProcessingRequest

class CrawlIntelligenceExtractor:
    """크롤링 데이터에서 기업 인텔리전스 추출"""

    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
        self.batch_size = 100

    def create_batch_requests(self, crawl_data_iter) -> list:
        """
        BigQuery crawl_raw_data에서 배치 요청 생성.
        """

        requests = []

        for idx, crawl_item in enumerate(crawl_data_iter):
            with open('src/prompts/extract_company_intelligence.txt') as f:
                prompt_template = f.read()

            prompt = prompt_template.format(
                company_name=crawl_item['company_id'],
                source_type=crawl_item['source_type'],
                page_type=crawl_item['page_type'],
                text=crawl_item['body_text'],
            )

            request = {
                'custom_id': f"extraction_{crawl_item['crawl_id']}",
                'request_body': {
                    'model': f"projects/graphrag-kg/locations/us-central1/endpoints/{self.model}",
                    'contents': [
                        {
                            'role': 'user',
                            'parts': [{'text': prompt}]
                        }
                    ],
                    'generationConfig': {
                        'temperature': 0.3,
                        'maxOutputTokens': 1000,
                        'responseMimeType': 'application/json',
                    }
                }
            }

            requests.append(request)

        return requests

    def submit_batch_job(self, requests: list) -> str:
        """배치 작업 제출"""
        from google.ai.generativelanguage_v1 import BatchCreateRequest
        import json

        # requests를 JSONL 형식으로 저장
        jsonl_path = f"/tmp/batch_{datetime.utcnow().timestamp()}.jsonl"
        with open(jsonl_path, 'w') as f:
            for req in requests:
                f.write(json.dumps(req) + '\n')

        # GCS 업로드
        from google.cloud import storage
        bucket = storage.Client().bucket('graphrag-kg-batch')
        blob = bucket.blob(f"batch_inputs/crawl_{datetime.utcnow().isoformat()}.jsonl")
        blob.upload_from_filename(jsonl_path)

        # Batch API 제출
        import subprocess
        result = subprocess.run([
            'gcloud', 'ai', 'batch-predictions', 'create',
            '--display-name', f'crawl-extraction-{datetime.utcnow().isoformat()}',
            '--input-config', f'gcs_source=gs://graphrag-kg-batch/{blob.name}',
            '--output-config', f'gcs_destination=gs://graphrag-kg-batch/batch_outputs/',
            '--model', f'projects/graphrag-kg/locations/us-central1/models/{self.model}',
        ], capture_output=True, text=True)

        batch_id = result.stdout.strip().split('/')[-1]
        return batch_id

    def process_batch_results(self, batch_id: str) -> Iterator[dict]:
        """배치 결과 처리"""
        from google.cloud import storage, bigquery

        bucket = storage.Client().bucket('graphrag-kg-batch')
        bq_client = bigquery.Client()

        # GCS에서 결과 파일 다운로드
        prefix = f"batch_outputs/{batch_id}/"
        blobs = list(bucket.list_blobs(prefix=prefix))

        for blob in blobs:
            if blob.name.endswith('.jsonl'):
                content = blob.download_as_string()
                for line in content.decode('utf-8').split('\n'):
                    if line.strip():
                        result = json.loads(line)
                        yield result
```

#### 4-1-5: GCS + BigQuery 통합 (1주, 병행)

**BigQuery 크롤링 테이블 3개** (전체 파이프라인 정의)

```sql
-- 1. 크롤링 대상 회사
CREATE TABLE graphrag_kg.crawl_company_targets (
  company_id STRING NOT NULL,
  company_name STRING NOT NULL,
  aliases ARRAY<STRING>,
  domain_url STRING,
  nice_industry_code STRING,
  is_active BOOLEAN DEFAULT TRUE,
  last_homepage_crawl TIMESTAMP,
  last_news_crawl TIMESTAMP,
  crawl_priority INT64 DEFAULT 100,  -- 1~1000 (낮을수록 우선)
  created_at TIMESTAMP,
  updated_at TIMESTAMP,

  PRIMARY KEY (company_id) NOT ENFORCED,
);

-- 2. 크롤링 원본 데이터
CREATE TABLE graphrag_kg.crawl_raw_data (
  crawl_id STRING NOT NULL,
  company_id STRING NOT NULL,
  source_type STRING NOT NULL,     -- 'homepage' | 'news'
  source_id STRING NOT NULL,
  crawl_date DATE NOT NULL,

  -- 메타데이터
  title STRING,
  url STRING,
  page_type STRING,  -- 'about', 'product', 'careers', 'newsroom' (homepage만)
  category STRING,  -- 'funding', 'org_change', 'personnel', 'product' (news만)
  source_media STRING,
  publish_date DATE,  -- 기사 발행일 (news만)
  is_press_release BOOLEAN,

  -- 크롤링 메타
  body_length INT64,
  crawl_status STRING,  -- 'success', 'timeout', 'robots_disallow', 'error'
  gcs_raw_path STRING,  -- 원문 저장 경로 (7일 후 삭제)
  gcs_text_path STRING,  -- 추출 텍스트 경로

  created_at TIMESTAMP,

  PRIMARY KEY (crawl_id) NOT ENFORCED,
  FOREIGN KEY (company_id) REFERENCES graphrag_kg.company_context(company_id) NOT ENFORCED,
);

-- 3. 크롤링 추출 결과
CREATE TABLE graphrag_kg.crawl_extracted_fields (
  crawl_id STRING NOT NULL,
  company_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  source_type STRING,
  source_id STRING,
  page_type STRING,
  category STRING,

  -- 추출된 필드
  product_description STRING,
  market_segment JSON,  -- {business_model, industry, region}
  funding JSON,  -- {round_type, amount_usd, investors, date}
  growth_narrative STRING,

  -- 기업 신호
  tension_type STRING,  -- 'M&A', 'Restructuring', 'Leadership_Change', 'Major_Pivot', 'Downsizing'
  tension_description STRING,
  culture_signals JSON,  -- {team_size, remote_friendly, diversity_focus, signals[]}
  scale_signals JSON,  -- {growth_rate, market_position, international_presence}

  -- 추출 품질
  extraction_model STRING,  -- 'gemini-2.0-flash-v1'
  evidence_spans ARRAY<STRING>,
  confidence FLOAT64,  -- 0.0~1.0 (모델 출력)
  adjusted_confidence FLOAT64,  -- 0.0~1.0 (후처리 후)
  missing_fields ARRAY<STRING>,

  created_at TIMESTAMP,

  PRIMARY KEY (crawl_id) NOT ENFORCED,
);

-- 뷰: 회사별 크롤링 통계
CREATE OR REPLACE VIEW graphrag_kg.crawl_company_summary AS
SELECT
  c.company_id,
  c.company_name,
  COUNT(DISTINCT CASE WHEN r.source_type = 'homepage' THEN r.crawl_id END) as homepage_crawls,
  COUNT(DISTINCT CASE WHEN r.source_type = 'news' THEN r.crawl_id END) as news_crawls,
  MAX(r.crawl_date) as last_crawl_date,
  COUNTIF(e.funding IS NOT NULL) as articles_with_funding,
  COUNTIF(e.tension_type IS NOT NULL) as articles_with_tension,
FROM graphrag_kg.company_context c
LEFT JOIN graphrag_kg.crawl_raw_data r USING (company_id)
LEFT JOIN graphrag_kg.crawl_extracted_fields e USING (crawl_id)
WHERE r.crawl_status = 'success'
GROUP BY c.company_id, c.company_name;
```

GCS 디렉토리 구조:
```
crawl/
  homepage/
    {company_id}/
      about/{timestamp}.txt
      product/{timestamp}.txt
      careers/{timestamp}.txt
      newsroom/{timestamp}.txt
  news/
    {company_id}/
      {article_id}_{timestamp}.txt
  extracted/
    {date}/
      homepage_extractions.jsonl
      news_extractions.jsonl
```

### 4-1 산출물
```
□ 크롤러 인프라 (Cloud Run Jobs + Playwright Docker)
□ Rate limiting + robots.txt + Error handling
□ 홈페이지 크롤러 (about, product, careers, newsroom)
□ 한국어 특화 (NICE 프로필, DART 공시)
□ 뉴스 수집기 (네이버 뉴스 API)
□ 기사 원문 크롤링
□ LLM 추출 프롬프트
□ Batch API 구현
□ BigQuery 크롤링 테이블 3개 (crawl_company_targets, crawl_raw_data, crawl_extracted_fields)
□ GCS 크롤링 데이터 저장
□ 예상 크롤링량: 1,000개 기업 × (3 homepage pages + 20 news articles) = 23,000건
```

---

## 4-2. CompanyContext 보강 (1주, 4-1과 병행) — Week 23

### 개요
4-1 크롤링 결과를 Phase 3의 CompanyContext와 병합하여 필드 채우기.

### Tasks (4-2-1 ~ 4-2-2)

**T4.2.1**: 크롤링 결과 → CompanyContext 병합 (DE)
```python
# src/pipelines/enrich_company_context.py

class CompanyContextEnricher:
    """
    크롤링 추출 결과로 CompanyContext 보강.
    우선순위: 기존 값 보존 > 크롤링 데이터로 채우기
    """

    def __init__(self, bq_client):
        self.bq_client = bq_client

    def enrich_all(self) -> tuple[int, int]:
        """
        모든 CompanyContext 보강.
        Returns: (total_updated, total_filled)
        """

        # 1. crawl_extracted_fields 조회 (최신 데이터만)
        crawl_data = self._load_latest_crawl_data()

        # 2. company_context와 병합
        updated_count = 0
        filled_count = 0

        for company_id, crawl_records in crawl_data.groupby('company_id'):
            updated = self._merge_for_company(company_id, crawl_records)
            if updated:
                updated_count += 1
                filled_count += len([r for r in crawl_records if r['product_description']])

        return (updated_count, filled_count)

    def _load_latest_crawl_data(self) -> pd.DataFrame:
        """최신 크롤링 추출 데이터 로드"""
        query = """
        SELECT
          company_id,
          MAX(crawl_date) as latest_crawl,
          ARRAY_AGG(
            STRUCT(
              crawl_id,
              source_type,
              product_description,
              market_segment,
              funding,
              tension_type,
              culture_signals,
              scale_signals,
              confidence
            ) IGNORE NULLS
          ) as records
        FROM graphrag_kg.crawl_extracted_fields
        WHERE adjusted_confidence > 0.5  -- 신뢰도 필터
        GROUP BY company_id
        """

        import pandas as pd
        return self.bq_client.query(query).to_dataframe()

    def _merge_for_company(self, company_id: str, crawl_records: list) -> bool:
        """
        특정 회사에 대해 CompanyContext 업데이트.
        Returns: 업데이트 여부
        """

        # 1. 기존 CompanyContext 조회
        existing = self._get_company_context(company_id)

        # 2. 크롤링 데이터에서 가장 신뢰도 높은 값 선택
        merged = existing.copy()

        # Product Description (존재하지 않으면 추가)
        if not existing['primary_product']:
            best_product = max(
                [r for r in crawl_records if r['product_description']],
                key=lambda x: x['confidence'],
                default=None
            )
            if best_product:
                merged['primary_product'] = best_product['product_description']

        # Funding (기존 funding 없으면 추가)
        if not existing['funding_rounds']:
            best_funding = max(
                [r for r in crawl_records if r['funding']],
                key=lambda x: x['confidence'],
                default=None
            )
            if best_funding:
                merged['funding_rounds'] = best_funding['funding']
                merged['total_funding_usd'] = best_funding['funding'].get('amount_usd')

        # Tension signals (신규 필드)
        tensions = [r for r in crawl_records if r['tension_type']]
        if tensions:
            merged['tension_signals'] = [
                {
                    'type': t['tension_type'],
                    'description': t['tension_description'],
                    'source_date': t['crawl_date'],
                }
                for t in tensions
            ]

        # 3. 완성도 재계산
        merged['completeness_score'] = self._calculate_completeness(merged)
        merged['updated_at'] = datetime.utcnow()

        # 4. BigQuery 업데이트
        self._update_company_context(merged)

        return True

    def _calculate_completeness(self, company_context: dict) -> float:
        """필드 채운 비율"""
        required_fields = [
            'company_name', 'employee_scale_category', 'growth_stage',
            'primary_product', 'market_segment', 'founded_year'
        ]

        filled = sum(1 for f in required_fields if company_context.get(f))
        return filled / len(required_fields)

    def _get_company_context(self, company_id: str) -> dict:
        """BigQuery에서 조회"""
        pass

    def _update_company_context(self, context: dict):
        """BigQuery에서 업데이트"""
        pass
```

**T4.2.2**: 품질 메트릭 (fill_rate, confidence) (DE)
```sql
-- fill_rate 측정
SELECT
  COUNT(*) as total_companies,
  COUNTIF(completeness_score >= 0.85) as complete_count,
  COUNTIF(completeness_score >= 0.70) as mostly_complete_count,
  AVG(completeness_score) as avg_completeness,
  PERCENTILE_CONT(completeness_score, 0.5) OVER() as median_completeness,
FROM graphrag_kg.company_context
WHERE updated_at >= CURRENT_TIMESTAMP() - INTERVAL 1 DAY;

-- 필드별 fill_rate
SELECT
  'primary_product' as field,
  COUNTIF(primary_product IS NOT NULL) / COUNT(*) as fill_rate,
FROM graphrag_kg.company_context
UNION ALL
SELECT
  'funding_rounds',
  COUNTIF(funding_rounds IS NOT NULL) / COUNT(*),
FROM graphrag_kg.company_context
UNION ALL
SELECT
  'tension_signals',
  COUNTIF(tension_signals IS NOT NULL) / COUNT(*),
FROM graphrag_kg.company_context;
```

### 4-2 산출물
```
□ 크롤링 결과 병합 로직
□ CompanyContext 업데이트 (우선순위 기반)
□ Completeness score 재계산
□ fill_rate 모니터링 대시보드
```

---

## 4-3. 품질 평가 Gold Test Set (3일) — Week 23

### 개요
Phase 3-5에서 구축한 테스트 프레임워크를 확장하여,
전체 파이프라인의 품질을 정량화.

### Tasks (4-3-1 ~ 4-3-3)

**T4.3.1**: Gold Test Set 구축 (도메인 전문가 2인 × 200건) — 2일
```python
# tests/gold_test_set.py

class GoldTestSetBuilder:
    """
    도메인 전문가 검증 기반 Gold Test Set 구축.
    구성: 후보자 100건 + 공고 100건
    """

    EVALUATION_CRITERIA = {
        'candidate_scope_type_accuracy': {
            'description': 'Resume에서 추출한 scope_type의 정확도',
            'metric': 'accuracy',
            'threshold': 0.80,
        },
        'vacancy_scope_type_accuracy': {
            'description': 'JD에서 추출한 scope_type의 정확도',
            'metric': 'accuracy',
            'threshold': 0.80,
        },
        'skill_extraction_f1': {
            'description': 'Skill 추출의 F1 점수',
            'metric': 'f1',
            'threshold': 0.70,
        },
        'company_context_completeness': {
            'description': 'CompanyContext 필드 채우기 비율',
            'metric': 'ratio',
            'threshold': 0.85,
        },
        'mapping_score_correlation': {
            'description': 'Matching score와 전문가 판정의 상관도',
            'metric': 'pearson_r',
            'threshold': 0.60,
        },
        'funding_extraction_precision': {
            'description': 'Funding 정보 추출의 정확도',
            'metric': 'precision',
            'threshold': 0.80,
        },
        'tension_detection_recall': {
            'description': 'Tension signal 감지의 recall',
            'metric': 'recall',
            'threshold': 0.70,
        },
    }

    def __init__(self, num_experts: int = 2):
        self.num_experts = num_experts
        self.evaluations = []

    def build(self, sample_size: int = 200):
        """
        Gold test set 구축.
        Args:
            sample_size: 평가할 샘플 수
        """

        # 1. 평가 대상 선정 (stratified sampling)
        candidates = self._sample_candidates(sample_size // 2)
        vacancies = self._sample_vacancies(sample_size // 2)

        # 2. 전문가 평가
        for expert_id in range(self.num_experts):
            print(f"Expert {expert_id} evaluation...")

            # 후보자 평가
            for candidate in candidates:
                evaluation = self._evaluate_candidate(candidate, expert_id)
                self.evaluations.append(evaluation)

            # 공고 평가
            for vacancy in vacancies:
                evaluation = self._evaluate_vacancy(vacancy, expert_id)
                self.evaluations.append(evaluation)

        # 3. Inter-annotator agreement 계산
        agreement = self._calculate_iaa()
        print(f"Inter-annotator agreement (Cohen's κ): {agreement}")

        # 4. 결과 저장
        self._save_evaluations()

        return self.evaluations

    def _evaluate_candidate(self, candidate: dict, expert_id: int) -> dict:
        """
        후보자 평가 (도메인 전문가).
        """
        return {
            'type': 'candidate',
            'candidate_id': candidate['candidate_id'],
            'expert_id': expert_id,
            'scope_type_correct': bool(candidate['scope_type'] == candidate['expected_scope']),
            'years_of_exp_accurate': abs(candidate['years'] - candidate['expected_years']) <= 1,
            'skills_completeness': len(candidate['skills']) / len(candidate['expected_skills']),
            'overall_quality': self._rate_quality(candidate),
            'comments': "",
        }

    def _evaluate_vacancy(self, vacancy: dict, expert_id: int) -> dict:
        """공고 평가"""
        return {
            'type': 'vacancy',
            'vacancy_id': vacancy['vacancy_id'],
            'expert_id': expert_id,
            'scope_type_correct': bool(vacancy['scope_type'] == vacancy['expected_scope']),
            'stage_estimate_accurate': abs(vacancy['stage'] - vacancy['expected_stage']) <= 1,
            'skill_requirement_clarity': self._rate_clarity(vacancy),
            'company_context_completeness': vacancy.get('company_context_score', 0),
            'overall_quality': self._rate_quality(vacancy),
        }

    def _calculate_iaa(self) -> float:
        """
        Inter-annotator agreement 계산 (Cohen's κ).
        """
        from sklearn.metrics import cohen_kappa_score

        expert_1_ratings = [e['overall_quality'] for e in self.evaluations if e['expert_id'] == 0]
        expert_2_ratings = [e['overall_quality'] for e in self.evaluations if e['expert_id'] == 1]

        kappa = cohen_kappa_score(expert_1_ratings, expert_2_ratings)
        return kappa

    def _save_evaluations(self):
        """평가 결과를 BigQuery에 저장"""
        import json
        from google.cloud import bigquery

        bq_client = bigquery.Client()

        rows = [
            {
                'evaluation_id': f"{e['type']}_{e['expert_id']}_{e.get('candidate_id', e.get('vacancy_id'))}",
                'type': e['type'],
                'expert_id': e['expert_id'],
                'evaluation_json': json.dumps(e),
                'created_at': datetime.utcnow().isoformat(),
            }
            for e in self.evaluations
        ]

        errors = bq_client.insert_rows_json(
            "graphrag_kg.quality_evaluations",
            rows
        )

        if errors:
            print(f"BigQuery insert error: {errors}")

    def _rate_quality(self, item: dict) -> int:
        """1~5 rating"""
        pass

    def _rate_clarity(self, item: dict) -> int:
        """1~5 rating"""
        pass

    def _sample_candidates(self, n: int) -> list:
        """무작위 샘플링"""
        pass

    def _sample_vacancies(self, n: int) -> list:
        """무작위 샘플링"""
        pass
```

**T4.3.2**: Inter-annotator agreement (Cohen's κ) 측정 — 0.5일
```python
# tests/iaa_analysis.py

def calculate_iaa_by_metric():
    """지표별 IAA 계산"""
    from sklearn.metrics import cohen_kappa_score

    metrics = {
        'scope_type_correct': [],
        'years_accurate': [],
        'skills_completeness': [],
        'overall_quality': [],
    }

    expert_1 = load_evaluations(expert_id=0)
    expert_2 = load_evaluations(expert_id=1)

    for metric in metrics:
        values_1 = [e[metric] for e in expert_1]
        values_2 = [e[metric] for e in expert_2]

        # Categorical: Cohen's κ
        if metric in ['scope_type_correct', 'years_accurate']:
            kappa = cohen_kappa_score(values_1, values_2)
            metrics[metric] = {'kappa': kappa}

        # Continuous: Pearson r
        else:
            import numpy as np
            corr = np.corrcoef(values_1, values_2)[0, 1]
            metrics[metric] = {'pearson_r': corr}

    return metrics
```

**T4.3.3**: 평가 지표 측정 + BigQuery 적재 — 0.5일

평가 기준 (Gold Test Set 기반):
| 지표 | 현재 | 최소 기준 | 목표 |
|---|---|---|---|
| scope_type 분류 정확도 | TBD | > 70% | > 80% |
| outcome 추출 F1 | TBD | > 55% | > 70% |
| situational_signal F1 | TBD | > 50% | > 65% |
| vacancy scope_type 정확도 | TBD | > 65% | > 80% |
| stage_estimate 정확도 | TBD | > 75% | > 85% |
| 피처 1개+ ACTIVE 비율 | TBD | > 80% | > 90% |
| Human eval 상관관계 (r) | TBD | > 0.4 | > 0.6 |

```sql
-- quality_metrics 테이블
CREATE TABLE graphrag_kg.quality_metrics (
  metric_id STRING NOT NULL,
  evaluation_date DATE NOT NULL,
  metric_name STRING NOT NULL,
  metric_value FLOAT64,
  sample_size INT64,
  confidence_interval_lower FLOAT64,
  confidence_interval_upper FLOAT64,
  evaluator STRING,
  notes STRING,
  created_at TIMESTAMP,

  PRIMARY KEY (metric_id) NOT ENFORCED,
);

-- 평가 결과 적재
INSERT INTO graphrag_kg.quality_metrics
SELECT
  GENERATE_UUID() as metric_id,
  CURRENT_DATE() as evaluation_date,
  'scope_type_accuracy' as metric_name,
  COUNTIF(scope_type_correct) / COUNT(*) as metric_value,
  COUNT(*) as sample_size,
  NULL, NULL,
  'domain_experts' as evaluator,
  'Gold test set from 200 samples',
  CURRENT_TIMESTAMP()
FROM graphrag_kg.quality_evaluations
WHERE type = 'candidate'
  AND evaluation_date = CURRENT_DATE();
```

**전문가 확보 및 비용**:
- 채용/HR 도메인 전문가 2인
- 기간: Phase 3 시작(Week 14) → Phase 4-3 시작(Week 23) 전 확보
- 리드타임: 6주
- 비용: 200건 × $20/건 × 2인 = $8,000 (높음, 조정 필요)

대안:
- 내부 채용팀 + 외부 전문가 1명 (비용 절감)
- 예상 비용: 200건 × $10/건 × 1.5명 = $3,000

### 4-3 산출물
```
□ Gold Test Set (200건, 전문가 검증)
□ Inter-annotator agreement 분석 (Cohen's κ)
□ 평가 지표 측정 (7가지)
□ BigQuery quality_metrics 테이블
□ 품질 리포트 (현황 vs. 목표)
```

---

## 4-4. Cloud Workflows + 증분 자동화 (1주) — Week 24

### 개요
일일 증분 처리 + 월별 크롤링 + 백업을 자동화하는 Cloud Workflows DAG 구축.

### Tasks (4-4-1 ~ 4-4-4)

**T4.4.1**: Full Pipeline DAG (DE)
```yaml
# src/workflows/kg-full-pipeline.yaml

main:
  steps:
    - step_parse_resumes:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: projects/graphrag-kg/locations/asia-northeast3/jobs/kg-jd-extraction
          body:
            overrides:
              task_count: 10
        result: parse_result
        next: step_dedup

    - step_dedup:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: projects/graphrag-kg/locations/asia-northeast3/jobs/kg-dedup-resumes
        result: dedup_result
        next: step_parallel_extract

    - step_parallel_extract:
        parallel:
          branches:
            - branch_company_context:
                steps:
                  - step_extract_company:
                      call: googleapis.run.v1.namespaces.jobs.run
                      args:
                        name: projects/graphrag-kg/locations/asia-northeast3/jobs/kg-company-context
                      result: company_result
            - branch_candidate_context:
                steps:
                  - step_extract_candidate:
                      call: googleapis.run.v1.namespaces.jobs.run
                      args:
                        name: projects/graphrag-kg/locations/asia-northeast3/jobs/kg-candidate-context
                      result: candidate_result
        next: step_graph_load

    - step_graph_load:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: projects/graphrag-kg/locations/asia-northeast3/jobs/kg-graph-load
        result: load_result
        next: step_embeddings

    - step_embeddings:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: projects/graphrag-kg/locations/asia-northeast3/jobs/kg-embeddings
        result: embed_result
        next: step_mapping

    - step_mapping:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: projects/graphrag-kg/locations/asia-northeast3/jobs/kg-mapping-features
        result: mapping_result
        next: step_notify

    - step_notify:
        call: googleapis.cloudtasks.v2.projects.locations.queues.tasks.create
        args:
          parent: projects/graphrag-kg/locations/asia-northeast3/queues/kg-notifications
          body:
            task:
              httpRequest:
                uri: https://slack-webhook.example.com/kg-pipeline
                method: POST
                body:
                  status: ${http.request_body.status}
                  result: "Full pipeline completed"
        result: notify_result
```

**T4.4.2**: Incremental Pipeline DAG (DE)
```yaml
# src/workflows/kg-incremental.yaml

main:
  steps:
    - step_detect_changes:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: projects/graphrag-kg/locations/asia-northeast3/jobs/kg-detect-changes
        result: detect_result
        next: step_check_changes

    - step_check_changes:
        switch:
          - condition: ${detect_result.body.changes_detected == false}
            next: step_end_no_changes
          - condition: ${detect_result.body.changes_detected == true}
            next: step_parse_new

    - step_end_no_changes:
        call: sys.log
        args:
          text: "No changes detected, skipping pipeline"
        next: step_end

    - step_parse_new:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: projects/graphrag-kg/locations/asia-northeast3/jobs/kg-parse-incremental
        result: parse_result
        next: step_extract_load

    - step_extract_load:
        parallel:
          branches:
            - branch_extract:
                steps:
                  - step_extract_incremental:
                      call: googleapis.run.v1.namespaces.jobs.run
                      args:
                        name: projects/graphrag-kg/locations/asia-northeast3/jobs/kg-extract-incremental
        next: step_end

    - step_end:
        call: sys.log
        args:
          text: "Incremental pipeline completed"
```

**T4.4.3**: 증분 처리 구현 (DE)
```python
# src/jobs/detect_changes.py

def detect_changes():
    """
    증분 데이터 변경 감지.
    GCS (new resumes/JDs) vs. BigQuery (processed)
    """

    from google.cloud import storage, bigquery
    from datetime import datetime, timedelta

    gcs = storage.Client().bucket('graphrag-kg-input')
    bq = bigquery.Client()

    # 1. GCS에서 최근 파일 조회 (last 24h)
    new_resumes = list(gcs.list_blobs(
        prefix='uploads/resumes/',
        delimiter='/'
    ))

    new_jds = list(gcs.list_blobs(
        prefix='uploads/jds/',
        delimiter='/'
    ))

    # 2. BigQuery에서 처리된 파일 확인
    query = """
    SELECT DISTINCT file_path
    FROM graphrag_kg.processing_log
    WHERE processed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    """

    processed = set(bq.query(query).to_dataframe()['file_path'])

    # 3. 미처리 파일 분류
    new_resume_files = [b for b in new_resumes if b.name not in processed]
    new_jd_files = [b for b in new_jds if b.name not in processed]

    changes_detected = len(new_resume_files) > 0 or len(new_jd_files) > 0

    return {
        'changes_detected': changes_detected,
        'new_resume_count': len(new_resume_files),
        'new_jd_count': len(new_jd_files),
        'timestamp': datetime.utcnow().isoformat(),
    }
```

**T4.4.4**: Cloud Scheduler 설정 (DE)
```bash
# Cloud Scheduler 작업 생성 스크립트

SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com
PROJECT=graphrag-kg
REGION=asia-northeast3

# 1. 일일 증분 파이프라인 (02:00 KST = 17:00 UTC)
gcloud scheduler jobs create pubsub kg-incremental-daily \
  --schedule="0 17 * * *" \
  --time-zone="UTC" \
  --topic="kg-workflow-trigger" \
  --message-body='{"workflow": "kg-incremental"}' \
  --location=$REGION \
  --project=$PROJECT

# 2. Dead-letter 재처리 (04:00 KST = 19:00 UTC)
gcloud scheduler jobs create pubsub kg-dead-letter-daily \
  --schedule="0 19 * * *" \
  --time-zone="UTC" \
  --topic="kg-deadletter-retry" \
  --message-body='{"job": "retry-deadletters"}' \
  --location=$REGION \
  --project=$PROJECT

# 3. 월별 크롤링 (매월 1일 00:00 KST = 전일 15:00 UTC)
gcloud scheduler jobs create pubsub kg-crawl-monthly \
  --schedule="0 15 L * *" \
  --time-zone="UTC" \
  --topic="kg-workflow-trigger" \
  --message-body='{"workflow": "kg-crawl-homepage-news"}' \
  --location=$REGION \
  --project=$PROJECT

# 4. Neo4j 주간 백업 (일요일 03:00 KST = 토요일 18:00 UTC)
gcloud scheduler jobs create pubsub kg-neo4j-backup \
  --schedule="0 18 * * 6" \
  --time-zone="UTC" \
  --topic="kg-maintenance" \
  --message-body='{"task": "backup-neo4j"}' \
  --location=$REGION \
  --project=$PROJECT

# 5. BigQuery 스냅샷 (매주 일요일 04:00 KST)
gcloud scheduler jobs create bigquery kg-bq-snapshot \
  --schedule="0 19 * * 6" \
  --time-zone="UTC" \
  --location=$REGION \
  --project=$PROJECT \
  --sql="CALL \`graphrag-kg.routines.snapshot_critical_tables\`();"

# 6. 프롬프트 A/B 테스트 평가 (월요일 10:00 KST)
gcloud scheduler jobs create pubsub kg-prompt-evaluation \
  --schedule="0 1 * * 1" \
  --time-zone="UTC" \
  --topic="kg-evaluation" \
  --message-body='{"task": "evaluate-prompts"}' \
  --location=$REGION \
  --project=$PROJECT
```

**증분 처리 예시** (Person 노드 업데이트):
```cypher
-- 기존 Person 노드의 이력서 Chapter 교체
MATCH (p:Person {candidate_id: $candidate_id})
DETACH DELETE (p)-[]->(old_chapter:Chapter)
WITH p
MATCH (file:ResumeFile {file_id: $new_file_id})
CREATE (p)-[:FROM_FILE]->(file)
CREATE (p)-[:HAS_CHAPTER]->(new_chapter:Chapter)
SET new_chapter.text = $chapter_text,
    new_chapter.chapter_type = $chapter_type,
    p.updated_at = datetime()
RETURN p;
```

### 4-4 산출물
```
□ Cloud Workflows DAG (Full + Incremental)
□ Cloud Scheduler 자동화 스크립트
□ 증분 처리 구현
□ Dead-letter 재처리
□ 크롤링 월별 자동화
□ Neo4j 주간 백업 자동화
□ BigQuery 스냅샷 자동화
□ 프롬프트 A/B 평가 자동화
```

---

## 4-5. 운영 인프라 + 인수인계 (1주) — Week 25

### 개요
프로덕션 운영을 위한 모니터링, 알림, 인수인계 문서 구축.

### Tasks (4-5-1 ~ 4-5-3)

**T4.5.1**: Cloud Monitoring + Slack 알림 (DE)
```python
# src/monitoring/setup_alerts.py

from google.cloud import monitoring_v3

def create_alert_policies():
    """운영 알림 정책 생성"""

    policies = [
        {
            'display_name': 'KG Pipeline Failure Rate > 5%',
            'conditions': [
                {
                    'metric': 'cloud.run/request_count',
                    'filter': 'metric.response_code_class == "5xx"',
                    'threshold': 0.05,
                    'comparison': 'COMPARISON_GT',
                    'duration': '300s',
                }
            ],
            'notification_channels': ['slack-kg-alerts'],
        },
        {
            'display_name': 'Neo4j Disk Usage > 80%',
            'conditions': [
                {
                    'metric': 'gke.io/container/disk/used_bytes',
                    'threshold': 0.8,  # 80%
                    'comparison': 'COMPARISON_GT',
                    'duration': '600s',
                }
            ],
            'notification_channels': ['slack-kg-alerts'],
        },
        {
            'display_name': 'BigQuery Slot Usage > 90%',
            'conditions': [
                {
                    'metric': 'bigquery.googleapis.com/slots/total_allocated_slots',
                    'threshold': 0.9,
                    'comparison': 'COMPARISON_GT',
                    'duration': '300s',
                }
            ],
            'notification_channels': ['slack-kg-alerts'],
        },
        {
            'display_name': 'GCS Crawler Error Rate > 10%',
            'conditions': [
                {
                    'metric': 'logging.googleapis.com/user/crawler_errors',
                    'threshold': 0.1,
                    'comparison': 'COMPARISON_GT',
                    'duration': '300s',
                }
            ],
            'notification_channels': ['slack-kg-alerts', 'pagerduty-escalation'],
        },
    ]

    client = monitoring_v3.AlertPolicyServiceClient()
    project = monitoring_v3.common.ProjectPath('graphrag-kg')

    for policy_def in policies:
        policy = monitoring_v3.AlertPolicy(
            display_name=policy_def['display_name'],
            conditions=[
                monitoring_v3.AlertPolicy.Condition(
                    display_name=cond.get('display_name', 'Condition'),
                    condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                        filter=cond['filter'],
                        comparison=cond['comparison'],
                        threshold_value=cond['threshold'],
                        duration=cond['duration'],
                    ),
                )
                for cond in policy_def['conditions']
            ],
            notification_channels=policy_def['notification_channels'],
        )

        created = client.create_alert_policy(
            name=project,
            alert_policy=policy
        )
        print(f"Alert policy created: {created.name}")
```

**완전한 알림 정책 테이블**:
| 알림 이름 | 메트릭 | 임계값 | 심각도 | 채널 |
|---|---|---|---|---|
| Pipeline Failure Rate | HTTP 5xx rate | > 5% | HIGH | Slack + PagerDuty |
| Neo4j Disk > 80% | gke.io/container/disk | > 80% | HIGH | Slack |
| BigQuery Slots > 90% | bq/slots_allocated | > 90% | MEDIUM | Slack |
| Crawler Error Rate | logging errors | > 10% | HIGH | Slack + PagerDuty |
| Budget Alert | GCP billing | > 80% of monthly | MEDIUM | Email + Slack |
| Processing Latency SLA | p99 latency | > 1 hour | MEDIUM | Slack |
| Deadletter Queue Size | Pub/Sub DLQ | > 100 messages | MEDIUM | Slack |

**T4.5.2**: 운영 문서 (인수인계 매뉴얼) (DE/MLE)
```markdown
# KG Pipeline 운영 매뉴얼

## 0. 빠른 시작

### 상태 확인
```bash
# Cloud Monitoring 대시보드
gcloud monitoring dashboards list --filter="displayName:KG-Pipeline"

# 최근 파이프라인 실행
gcloud cloud-tasks queues list --location=asia-northeast3

# Neo4j 헬스 체크
curl https://neo4j.graphrag-kg.example.com/health
```

### 알림 보면 먼저 할 것
1. 알림 상세 정보 확인 (Slack → Cloud Monitoring 링크)
2. 해당 컴포넌트 상태 확인 (아래 섹션)
3. Runbook 참조

---

## 1. 시스템 아키텍처 개요

### 주요 컴포넌트
- **Pipeline Orchestrator**: Cloud Workflows (DAG 실행)
- **Data Processing**: Cloud Run Jobs (JD 파싱, 임베딩, 매칭)
- **Storage**: BigQuery (메타데이터), GCS (원본 데이터), Neo4j (그래프)
- **Crawling**: Cloud Run Jobs + Playwright (홈페이지/뉴스)
- **Monitoring**: Cloud Monitoring + Slack

### 데이터 흐름
```
uploads/ (GCS)
  → detect_changes
  → parse (JD/resume)
  → extract (features)
  → [parallel: company_context, candidate_context]
  → graph_load (Neo4j)
  → embeddings
  → mapping_features
  → notify (Slack)
```

---

## 2. 일일 운영 체크리스트

```
매일 09:00:
□ 전날 파이프라인 실행 결과 확인
  gcloud logging read "resource.type=cloud_run_job" --limit=10
□ 알림 확인 (Slack #kg-alerts)
□ 크롤링 성공률 확인 (BigQuery 쿼리)
□ Processing latency p99 확인

문제 발견 시:
□ Runbook 참조
□ on-call 엔지니어 연락
```

---

## 3. 알림별 대응 절차 (Runbook)

### 알림: Pipeline Failure Rate > 5%

1. **상태 확인**
   ```bash
   gcloud logging read "severity=ERROR" \
     --limit=20 --filter="resource.type=cloud_run_job"
   ```

2. **원인 분류**
   - Cloud Run Job 타임아웃? → Task timeout 증가
   - BigQuery 쿼리 오류? → 쿼리 로그 확인 (failed_queries.sql)
   - Neo4j 연결 오류? → Neo4j 상태 확인

3. **대응**
   ```bash
   # 특정 Job 재시작
   gcloud run jobs execute kg-mapping-features --region=asia-northeast3

   # Dead-letter 수동 재처리
   python src/jobs/process_deadletters.py --limit=100
   ```

### 알림: Neo4j Disk > 80%

1. **현재 용량 확인**
   ```bash
   # Kubernetes 클러스터 연결
   kubectl get pvc -n neo4j
   kubectl describe pvc neo4j-data
   ```

2. **대응**
   - **즉시**: 크롤링 데이터 정리 (7일 이상 된 데이터 삭제)
   - **단기**: PVC 크기 확장 (현재 크기의 1.5배)
   - **분석**: 불필요한 노드/관계 정리

### 알림: BigQuery Slots > 90%

1. **현재 쿼리 확인**
   ```bash
   bq show --job=<job_id>
   ```

2. **대응**
   - Long-running 쿼리 취소
   - 증분 파이프라인 연기

### 알림: Crawler Error Rate > 10%

1. **에러 분석**
   ```bash
   gcloud logging read "resource.labels.job_name=kg-crawl-*" \
     --severity=ERROR --limit=50
   ```

2. **공통 원인**
   - robots.txt Disallow: 정상 동작
   - 429 Too Many Requests: rate limiting 증가
   - 403 Forbidden: 해당 도메인 제외
   - Timeout: 도메인별 타임아웃 증가

---

## 4. 증분 처리 파이프라인 구조

### 데일리 Incremental 흐름
```
02:00 KST: Cloud Scheduler 트리거
  → kg-incremental workflow 시작
  → detect_changes job (5분)
  → [if changes] parse_incremental (30분)
  → extract_incremental (1시간)
  → graph_update (30분)
  → notify Slack
```

### 예상 처리량
- 월 ~20,000~30,000건 신규 이력서/JD
- 일 ~1,000건 (증분)
- 처리 시간: ~2시간 (10 parallel tasks)

### 모니터링 쿼리
```sql
-- 어제 처리된 건수
SELECT
  COUNT(*) as processed_count,
  COUNT(DISTINCT candidate_id) as unique_candidates,
  COUNT(DISTINCT vacancy_id) as unique_vacancies,
FROM graphrag_kg.processing_log
WHERE processed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR);

-- 실패율
SELECT
  COUNT(*) as total,
  COUNTIF(status = 'failed') as failed,
  COUNTIF(status = 'failed') / COUNT(*) as failure_rate,
FROM graphrag_kg.processing_log
WHERE processed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR);
```

---

## 5. 크롤링 파이프라인 구조 + 법적 준수

### 월별 크롤링 (1000개 기업)
```
매월 1일 00:00 KST: Cloud Scheduler 트리거
  → crawl_company_targets 1000개 로드
  → [parallel 10 tasks] crawl_homepage
  → [parallel 10 tasks] crawl_news
  → [parallel 5 tasks] extract_intelligence (LLM)
  → update_company_context
  → BigQuery 적재
```

### 법적 준수 체크리스트
```
□ robots.txt 준수 (자동 확인)
  - 매 요청마다 robots.txt 파싱
  - Disallow 경로는 스킵

□ Rate limiting 설정
  - 도메인당 최소 2초 간격
  - 동시 요청: 최대 5개
  - Cloud Tasks 큐 제한

□ 원본 미보관 정책
  - GCS 파일 7일 자동 삭제
  - BigQuery에는 메타데이터만 보관
  - 추출 정보만 영구 저장
```

### 크롤링 거부 기업 관리
```python
# data/crawling_blocklist.json
{
  "blocked_domains": [
    "example.com",  # robots.txt에서 우리를 차단
    "private-company.kr",  # 요청으로 차단
  ],
  "last_updated": "2026-03-15"
}

# 매월 말 업데이트 (운영 담당자)
python src/crawlers/update_blocklist.py
```

---

## 6. 프롬프트 업데이트 + Regression Test

### 프롬프트 버전 관리
```
src/prompts/
  extract_jd_v1.0.txt (Phase 3)
  extract_jd_v1.1.txt (개선 버전, 테스트 중)
  extract_company_intelligence_v1.0.txt (Phase 4)
```

### 새 프롬프트 배포 절차
1. **A/B 테스트** (100건 샘플)
   ```python
   # 기존 프롬프트 vs. 신규 프롬프트로 동일 데이터 추출
   # 결과 비교 (정확도, 신뢰도)
   python tests/ab_test_prompts.py --new-prompt=extract_jd_v1.1.txt
   ```

2. **Regression Test 실행**
   ```bash
   # Golden 50건 테스트 + Phase 4 Gold 200건
   pytest tests/test_phase3_golden_set.py
   pytest tests/test_phase4_quality.py
   ```

3. **배포**
   ```bash
   # Config 업데이트
   gcloud secrets versions add kg-extraction-config \
     --data-file=config/extraction_prompts.json

   # 다음 파이프라인 실행부터 적용
   ```

---

## 7. 프로덕션 데이터 업데이트 절차

### BigQuery 데이터 업데이트 (긴급)
```sql
-- 잘못된 데이터 일괄 수정 (예: 공고 scope_type 재분류)
BEGIN TRANSACTION;

UPDATE graphrag_kg.vacancy_summary
SET scope_type = 'technical'
WHERE company_id = 'cid_xyz'
  AND scope_type = 'null';

-- 영향도 확인
SELECT COUNT(*) as updated_rows;

COMMIT TRANSACTION;
```

### Neo4j 데이터 업데이트 (긴급)
```cypher
-- 데이터 수정 예시
MATCH (o:Organization {company_id: 'org_xyz'})
SET o.employee_scale_category = 'medium',
    o.updated_at = datetime()
RETURN o;

-- 영향도 확인
MATCH (o:Organization {company_id: 'org_xyz'})
MATCH (o)<-[b:BELONGS_TO]-(v:Vacancy)
RETURN COUNT(v) as affected_vacancies;
```

---

## 8. Neo4j 백업/복원 절차

### 주간 백업 (자동화)
```bash
# 매주 일요일 03:00 KST에 자동 실행
gcloud run jobs execute kg-neo4j-backup

# 수동 백업
kubectl exec -it neo4j-0 -n neo4j -- \
  neo4j-admin database backup --to-path=/backups neo4j
```

### 백업 확인
```bash
# 백업 파일 목록
gsutil ls gs://graphrag-kg-backups/neo4j/

# 최신 백업 시간 확인
gsutil stat gs://graphrag-kg-backups/neo4j/neo4j_2026-03-08T03-00-00Z.tar.gz
```

### 복원 절차 (긴급)
```bash
# 1. 백업 파일 선택
BACKUP_FILE=gs://graphrag-kg-backups/neo4j/neo4j_2026-03-08T03-00-00Z.tar.gz

# 2. GCS에서 다운로드
gsutil cp $BACKUP_FILE ./

# 3. 압축 해제
tar -xzf neo4j_2026-03-08T03-00-00Z.tar.gz

# 4. Neo4j 서비스 중지
kubectl scale sts neo4j --replicas=0 -n neo4j

# 5. 복원
kubectl cp ./neo4j /neo4j-0:/var/lib/neo4j/data

# 6. 서비스 재시작
kubectl scale sts neo4j --replicas=1 -n neo4j
```

---

## 9. 비용 모니터링 + Budget Alert

### 월별 비용 분석 대시보드
```sql
-- 서비스별 월별 비용
SELECT
  service as gcp_service,
  SUM(cost) as total_cost_usd,
  COUNT(*) as line_items,
FROM \`graphrag-kg.billing.gcp_billing_export_v1\`
WHERE invoice_month = '202603'
GROUP BY service
ORDER BY total_cost_usd DESC;

-- 상위 비용 컴포넌트
SELECT
  sku.description,
  SUM(cast(usage.amount as float64)) as total_usage,
  SUM(cast(cost as float64)) as total_cost,
FROM \`graphrag-kg.billing.gcp_billing_export_v1\`
WHERE invoice_month = '202603'
GROUP BY sku.description
ORDER BY total_cost DESC
LIMIT 10;
```

### Budget Alert 설정
```bash
gcloud billing budgets create \
  --billing-account=<BILLING_ACCOUNT_ID> \
  --display-name="KG Pipeline Monthly Budget" \
  --budget-amount=5000 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100 \
  --notifications-disabled-pubsub-topic=projects/graphrag-kg/topics/budget-alerts
```

---

## 10. Secret Manager 키 로테이션

### 보관 중인 Secrets
```
kg-neo4j-password     (DB 접근)
kg-naver-api-keys     (뉴스 API)
kg-cloud-storage-key  (GCS 업로드)
kg-slack-webhook      (알림)
```

### 로테이션 절차 (분기별)
```bash
# 현재 Secret 버전 확인
gcloud secrets versions list kg-neo4j-password

# 새 비밀번호 생성
NEW_PASSWORD=$(openssl rand -base64 32)

# Secret 업데이트
echo -n "$NEW_PASSWORD" | gcloud secrets versions add kg-neo4j-password --data-file=-

# Neo4j 비밀번호 변경
cypher-shell -u neo4j -p $OLD_PASSWORD \
  "ALTER USER neo4j SET PASSWORD '$NEW_PASSWORD';"

# 확인
cypher-shell -u neo4j -p "$NEW_PASSWORD" "RETURN 1;"
```

---

## 11. 운영 인력 및 책임

### 운영 팀 구성
```
- Lead: Data Engineer (0.5 FTE)
  ├─ 증분 파이프라인 관리
  ├─ 크롤링 법적 준수
  └─ 인프라 모니터링

- On-Call: MLE (0.3 FTE, 교대)
  ├─ 프롬프트 성능 모니터링
  ├─ 품질 평가 (주 1회)
  └─ 파이프라인 품질 검증

- Backup: Product Manager (0.2 FTE, 필요시)
  ├─ 우선순위 조정
  └─ 비용 최적화
```

### On-Call 교대 일정
```
주 1회 (금요일) 30분 동안 on-call
- 알림 응답
- 긴급 대응
- 수동 개입 필요시 결정
```

---

## 12. 트러블슈팅 FAQ

### Q: "파이프라인이 안 돌아요"
A: 이 순서로 확인:
1. Cloud Logging에서 실패 원인 확인
2. Runbook 섹션 참조
3. 자동 복구 불가능 → on-call 호출

### Q: "Neo4j 쿼리가 느려요"
A:
1. SHOW INDEXES; 로 인덱스 확인
2. PROFILE로 쿼리 실행 계획 확인
3. 필요시 인덱스 추가
   ```cypher
   CREATE INDEX idx_person_candidate_id FOR (p:Person) ON (p.candidate_id);
   ```

### Q: "크롤링이 계속 실패해요"
A: robots.txt 준수 확인
   ```python
   python src/crawlers/check_robots_txt.py --domain=example.com
   ```

---

## 13. 연락처 및 에스컬레이션

```
긴급 (P1):
- on-call: slack #kg-oncall
- PagerDuty: kg-pipeline-p1

높음 (P2):
- Slack #kg-operations
- 업무 시간 내 대응 (1시간)

일반 (P3):
- Jira: KG-OPS
- 업무 시간 내 대응 (1일)
```

---

## 14. 참고 리소스

- **아키텍처 문서**: docs/architecture/
- **API 문서**: docs/api/
- **데이터 스키마**: docs/schema/
- **테스트 가이드**: tests/README.md
```

**T4.5.3**: 인수인계 워크샵 (DE/MLE, 0.5일)
- 현재 담당자 → 운영 담당자 지식 전수
- 실제 사례 기반 트러블슈팅 연습
- On-call 시뮬레이션

### 4-5 산출물
```
□ Cloud Monitoring 알림 정책 (8가지)
□ Slack 알림 채널 설정
□ PagerDuty 연동 (P1 알림)
□ 운영 매뉴얼 (14개 섹션)
□ Runbook (각 알림별 대응 절차)
□ 운영 인력 확정 (DE 0.5 FTE + MLE 0.3 FTE)
□ On-call 교대 일정
□ 인수인계 워크샵 완료
```

---

## Phase 4 완료 산출물

```
□ 홈페이지/뉴스 크롤링 파이프라인
  ├─ Cloud Run Jobs + Playwright Docker
  ├─ Rate limiting + robots.txt + Error handling
  ├─ 홈페이지 크롤러 (about, product, careers, newsroom)
  ├─ 한국 기업 특화 (NICE, DART)
  ├─ 뉴스 수집기 (네이버 뉴스 API)
  └─ 예상 크롤링: 1,000개 기업 × 23건 = 23,000건/월

□ CompanyContext 보강
  ├─ 크롤링 결과 병합 로직
  ├─ Completeness score 재계산
  └─ fill_rate 0.85+ 달성

□ 품질 평가 Gold Test Set
  ├─ 도메인 전문가 검증 (200건)
  ├─ Inter-annotator agreement 측정
  ├─ 7가지 품질 지표 측정
  └─ 품질 리포트

□ Cloud Workflows + 자동화
  ├─ Full Pipeline DAG
  ├─ Incremental Pipeline DAG
  ├─ Cloud Scheduler 자동화 (6가지 작업)
  ├─ 일일 증분 (02:00 KST)
  ├─ 월별 크롤링 (1일)
  ├─ 주간 Neo4j 백업
  └─ 주간 BigQuery 스냅샷

□ 운영 인프라
  ├─ Cloud Monitoring 알림 (8가지)
  ├─ Slack/PagerDuty 연동
  ├─ 운영 매뉴얼 (14개 섹션)
  ├─ Runbook (각 알림별)
  ├─ 운영 인력 확정
  └─ On-call 교대 일정

□ Phase 4 → 운영 Go/No-Go 판정
  ├─ 품질 지표 달성 확인
  ├─ 성능 지표 달성 확인
  ├─ 운영 준비 완료 확인
  └─ 인수인계 완료
```

---

## 예상 인프라 비용 (Phase 4 6주)

| 항목 | 단가 | 수량 | 소계 |
|---|---|---|---|
| **Cloud Run Jobs (크롤링)** | $0.096/시간 | 300시간 | $29 |
| **BigQuery** |  |  |  |
| Storage | $6.25/TB | 200GB | $1.25 |
| Queries | $6.25/TB | 300TB | $1,875 |
| **Batch API (LLM 추출)** | $0.0004/건 | 30K건 | $12 |
| **Neo4j** | $1/시간 | 168시간 | $168 |
| **GCS** | $0.020/GB | 500GB | $10 |
| **Cloud Monitoring** | $0.50/정책 | 8개 | $4 |
| **Cloud Scheduler** | 무료 | - | $0 |
| **Cloud Workflows** | $0.01/1K실행 | 180실행 | $2 |
| **전문가 비용** (외주) | $20/건 | 200건 × 1.5인 | $6,000 |
| **합계** |  |  | **$8,101** |

주: 전문가 비용은 빠진 항목. 실제로는 이것을 포함해야 함.
대안: 내부 채용팀 활용 → 비용 $3,000로 절감 가능.

---

## 타임라인

```
Week 20: 4-1-1 크롤러 인프라 (DE 5일)
Week 21: 4-1-2, 4-1-3 홈페이지/뉴스 (DE 5일, MLE 2일 병행)
Week 22: 4-1-4 LLM 추출 (MLE 4일)
Week 23: 4-1-5 GCS/BQ + 4-2 보강 (DE 3일) + 4-3 품질 (전문가 2일)
Week 24: 4-4 자동화 (DE 5일)
Week 25: 4-5 운영 인프라 (DE 4일, MLE 2일)

병렬 작업:
- Week 20-22: 크롤링 파이프라인 (DE 주도) & Phase 4 준비 (MLE)
- Week 23-24: 자동화 구축 (DE) & 품질 평가 진행 (전문가)
- Week 25: 인수인계 + on-call 교대 설정
```

---

## 예상 성과

### Phase 4 완료 시점 (Week 25 이후)

**Graph 규모**:
- Person 노드: 100K개
- Vacancy 노드: 10K개
- Organization 노드: 500개(ER 적용)
- MAPPED_TO 관계: 10억+ 개

**데이터 품질**:
- CompanyContext completeness: ≥ 85%
- Mapping score 신뢰도 (Human eval r): ≥ 0.60
- 크롤링 성공률: ≥ 85%

**운영 준비**:
- 자동화 비율: > 95% (수동 개입 < 5%)
- Alert 응답 시간: < 30분
- MTTR (Mean Time To Recovery): < 1시간

**비용 효율**:
- 월 운영비: ~$5K~8K
- 일일 처리량: 1K~2K 증분 데이터
- 비용/건: ~$5~8/건
