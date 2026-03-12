# Phase 1: Core Candidate MVP — 크롤링 + DB 텍스트 (5주, Week 2~6)

> **목적**: 크롤링 파이프라인 구축 + DB 데이터를 CandidateContext로 변환 + Graph MVP 완성.
>
> **데이터 확장**: 없음 → **DB 텍스트 이력서 1,000건 + 크롤링 데이터**
> **에이전트 역량 변화**: 없음 → **후보자 스킬/경력/시맨틱 검색 가능**
>
> **핵심 전략**: DE는 크롤링에 집중, MLE는 GraphRAG 파이프라인에 집중 — 완전 병렬.
>
> **인력**: DE 1명 + MLE 1명 풀타임
> **산출물**: 크롤링 파이프라인 동작 + 1,000건 E2E Graph + 에이전트 연동 가능 MVP

---

## 1-A. 크롤링 파이프라인 구축 (Week 2~3, DE 담당)

### Week 2: 크롤러 핵심 구현 (5일)

| # | 작업 | 산출물 | 기간 |
|---|------|--------|------|
| C-1 | 크롤링 DB 스키마 확정 + resume_raw 테이블 보완 | BigQuery DDL | 0.5일 |
| C-2 | Playwright 크롤러 — 로그인/세션 관리 | `src/crawlers/base.py` | 1일 |
| C-3 | 사이트별 크롤러 어댑터 (최소 2곳) | `src/crawlers/site_a.py` 등 | 2일 |
| C-4 | 이력서 페이지 파싱 (DOM → 텍스트/구조화) | `src/crawlers/parser.py` | 1일 |
| C-5 | 중복 감지 (content_hash 기반) | 코드 | 0.5일 |

### Week 3: 크롤러 운영 인프라 (5일)

| # | 작업 | 산출물 | 기간 |
|---|------|--------|------|
| C-6 | BigQuery 적재 모듈 (크롤링 결과 → resume_raw) | `src/crawlers/loader.py` | 0.5일 |
| C-7 | Cloud Run Job 패키징 (Playwright Docker) | Dockerfile + Job | 1일 |
| C-8 | Cloud Scheduler 연동 (일일/주간 트리거) | 스케줄 설정 | 0.5일 |
| C-9 | 에러 핸들링 + 재시도 (anti-bot, timeout, 세션 만료) | 코드 | 1일 |
| C-10 | 파일럿 크롤링 실행 (사이트당 100건) | 수집 결과 | 1일 |
| C-11 | 크롤링 모니터링 (일일 수집량, 실패율) | BigQuery 쿼리 | 0.5일 |
| C-12 | **기존 DB 데이터 → resume_raw 마이그레이션** | 데이터 로드 | 0.5일 |

### 크롤러 아키텍처

```python
# src/crawlers/base.py
from abc import ABC, abstractmethod
from playwright.async_api import async_playwright

class BaseCrawler(ABC):
    """사이트별 크롤러의 베이스 클래스"""

    def __init__(self, site_name: str, config: dict):
        self.site_name = site_name
        self.config = config
        self.rate_limit_seconds = config.get("rate_limit", 3)

    @abstractmethod
    async def login(self, page) -> bool:
        """사이트별 로그인 로직"""
        pass

    @abstractmethod
    async def get_resume_urls(self, page, offset: int, limit: int) -> list[str]:
        """이력서 목록 페이지에서 URL 추출"""
        pass

    @abstractmethod
    async def parse_resume(self, page, url: str) -> dict:
        """이력서 상세 페이지에서 데이터 추출"""
        pass

    async def crawl(self, max_pages: int = 100):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="GraphRAG-Crawler/1.0 (research)",
            )
            page = await context.new_page()

            await self.login(page)

            offset = 0
            while offset < max_pages:
                urls = await self.get_resume_urls(page, offset, limit=20)
                if not urls:
                    break

                for url in urls:
                    try:
                        resume = await self.parse_resume(page, url)
                        resume["source_site"] = self.site_name
                        resume["source_url"] = url
                        yield resume
                    except Exception as e:
                        yield {"error": str(e), "url": url}

                    await asyncio.sleep(self.rate_limit_seconds)

                offset += len(urls)

            await browser.close()
```

### 크롤링 Docker 이미지

```dockerfile
# Dockerfile.crawler
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app
COPY requirements-crawler.txt .
RUN pip install -r requirements-crawler.txt

COPY src/crawlers/ src/crawlers/
COPY src/shared/ src/shared/

# Playwright 브라우저 설치
RUN playwright install chromium

ENTRYPOINT ["python", "-m", "src.crawlers.run"]
```

```bash
# Cloud Run Job 등록
IMAGE=asia-northeast3-docker.pkg.dev/graphrag-kg/kg-pipeline/kg-crawler:latest
SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com

gcloud run jobs create kg-crawler \
  --image=$IMAGE \
  --tasks=1 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3

# Cloud Scheduler — 매일 새벽 2시 크롤링
gcloud scheduler jobs create http kg-crawler-daily \
  --schedule="0 2 * * *" \
  --uri="https://asia-northeast3-run.googleapis.com/v2/projects/graphrag-kg/locations/asia-northeast3/jobs/kg-crawler:run" \
  --http-method=POST \
  --oauth-service-account-email=$SA \
  --time-zone="Asia/Seoul"
```

### 크롤링 정책

```
□ robots.txt 준수 (각 사이트별 확인)
□ 요청 간격: 최소 3초 (rate_limit_seconds=3)
□ User-Agent: "GraphRAG-Crawler/1.0 (research)"
□ 일일 크롤링 한도: 사이트당 500건/일 (초기)
□ 세션 만료 시 자동 재로그인 (max 3회)
□ Anti-bot 감지 시: 크롤링 중단 + 알림
□ 원본 텍스트: resume_raw에 저장, 후속 정책에 따라 삭제 가능
□ 중복: content_hash 기반, 이미 수집된 이력서 skip
```

---

## 1-B. 전처리 모듈 (Week 2~3, MLE 담당)

### Week 2: 전처리 핵심 구현 (5일)

| # | 작업 | 산출물 | 기간 |
|---|------|--------|------|
| P-1 | DB 텍스트 정규화 모듈 | `src/preprocess/normalize.py` | 1일 |
| P-2 | PII 마스킹 모듈 (이름, 전화번호, 이메일, 주소) | `src/preprocess/pii.py` | 2일 |
| P-3 | 경력 블록 분리기 (텍스트 → 경력 단위) | `src/preprocess/career_split.py` | 1.5일 |
| P-4 | 기술 사전 2,000개 구축 | `reference/tech_dict.json` | 0.5일 |

### Week 3: 전처리 인프라 + 연동 (5일)

| # | 작업 | 산출물 | 기간 |
|---|------|--------|------|
| P-5 | SimHash 중복 제거 (resume_raw 레벨) | `src/preprocess/dedup.py` | 1일 |
| P-6 | CandidateContext Pydantic 모델 정의 | `src/models/candidate.py` | 0.5일 |
| P-7 | 전처리 파이프라인 통합 (정규화→PII→중복→분리) | `src/preprocess/pipeline.py` | 1일 |
| P-8 | Cloud Run Job 패키징 + 등록 | Dockerfile + Job | 0.5일 |
| P-9 | 전처리 결과 → resume_processed 적재 | 코드 | 0.5일 |
| P-10 | 통합 테스트 (100건) + 버그 수정 | 테스트 | 1.5일 |

### 정규화 모듈

```python
# src/preprocess/normalize.py
import re
import unicodedata

def normalize_resume_text(text: str) -> str:
    """DB 이력서 텍스트 정규화"""
    if not text:
        return ""

    # Unicode 정규화 (NFC)
    text = unicodedata.normalize("NFC", text)

    # HTML 태그 제거 (크롤링 데이터에 잔존 가능)
    text = re.sub(r"<[^>]+>", " ", text)

    # 연속 공백/탭/개행 정리
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 제어 문자 제거
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

    return text.strip()
```

### PII 마스킹 모듈

```python
# src/preprocess/pii.py
import re

PII_PATTERNS = {
    "phone": re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "name_kr": None,  # 별도 NER 또는 structured_fields에서 추출
}

def mask_pii(text: str, structured_fields: dict = None) -> str:
    """PII 마스킹 — 전화번호, 이메일은 regex, 이름은 structured_fields 활용"""
    masked = text

    # 전화번호
    masked = PII_PATTERNS["phone"].sub("[PHONE]", masked)

    # 이메일
    masked = PII_PATTERNS["email"].sub("[EMAIL]", masked)

    # 이름 — structured_fields에 이름이 있으면 그것으로 마스킹
    if structured_fields and structured_fields.get("name"):
        name = structured_fields["name"]
        masked = masked.replace(name, "[NAME]")

    return masked
```

### 경력 블록 분리기

```python
# src/preprocess/career_split.py
import re

# 경력 블록 시작 패턴 (한국어 이력서 공통)
CAREER_PATTERNS = [
    re.compile(r"(\d{4}[.\-/]\d{1,2})\s*[~\-–—]\s*(\d{4}[.\-/]\d{1,2}|현재|재직중)"),
    re.compile(r"(20\d{2}|19\d{2})\s*[~\-]\s*(20\d{2}|19\d{2}|현재)"),
]

def split_career_blocks(text: str) -> list[dict]:
    """이력서 텍스트를 경력 블록 단위로 분리"""
    blocks = []
    # 날짜 패턴 기반 분리 + 휴리스틱
    # ...
    return blocks
```

### Cloud Run Job 등록 (전처리)

```bash
IMAGE=asia-northeast3-docker.pkg.dev/graphrag-kg/kg-pipeline/kg-pipeline:latest
SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com

# 전처리 Job
gcloud run jobs create kg-preprocess \
  --image=$IMAGE \
  --command="python,-m,src.preprocess.pipeline" \
  --tasks=1 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3
```

---

## 1-C. CandidateContext LLM 추출 (Week 4~5)

### Week 4: LLM 추출 모듈 + 프롬프트 (DE + MLE 공동)

| # | 작업 | 담당 | 기간 |
|---|------|------|------|
| L-1 | LLM 추출 프롬프트 3종 작성 | MLE | 1일 |
| L-2 | LLM 파싱 실패 3-tier 구현 | MLE | 1일 |
| L-3 | Batch API 인프라 (prepare/submit/poll/collect) | DE | 2일 |
| L-4 | chunk 상태 추적 (BigQuery batch_tracking) | DE | 0.5일 |
| L-5 | 프롬프트 튜닝 (3종 × 5라운드) | MLE | 2.5일 |
| L-6 | **크롤링 운영 안정화** (에러 대응, rate limit 조정) | DE (병행) | Week 4 |

### 프롬프트 3종

```
프롬프트 1: experience_extract (경력별 상세 추출)
  - 입력: 경력 블록 1개 텍스트
  - 출력: company, role, duration, scope_type, skills, outcome

프롬프트 2: career_summary (전체 커리어 요약)
  - 입력: 전체 이력서 텍스트
  - 출력: seniority_estimate, total_years, primary_domain, career_trajectory

프롬프트 3: work_style_signals (업무 스타일)
  - 입력: 전체 이력서 텍스트
  - 출력: leadership, mentoring, cross_functional, self_directed
```

### LLM 파싱 실패 3-tier

```python
# src/shared/llm_parser.py
import json
from json_repair import repair_json

def parse_llm_response(response_text: str, resume_id: str) -> dict | None:
    """3-tier LLM 응답 파싱"""

    # Tier 1: 정상 파싱
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Tier 2: json-repair로 복구
    try:
        repaired = repair_json(response_text)
        return json.loads(repaired)
    except Exception:
        pass

    # Tier 3: 재시도 1회 (프롬프트에 "반드시 valid JSON" 강조)
    # → 재시도 실패 시 dead-letter로 이동
    return None
```

### Week 5: 1,000건 처리 + 검증

| # | 작업 | 담당 | 기간 |
|---|------|------|------|
| L-7 | 1,000건 Batch API 제출 | DE | 0.5일 |
| L-8 | Batch 대기 (~6-24h) + 폴링 | DE | (대기) |
| L-9 | **(대기 중)** Graph 적재 모듈 선행 구현 | DE | 2일 |
| L-10 | Batch 결과 수집 + CandidateContext 생성 | 공동 | 1일 |
| L-11 | 결과 검증 50건 수동 확인 | MLE | 1일 |
| L-12 | 크롤링 → 전처리 → LLM 파이프라인 E2E 연동 | 공동 | 0.5일 |

### Batch API 제출 모듈

```python
# src/batch/prepare.py
import json
from google.cloud import storage

def prepare_batch_requests(
    resume_ids: list[str],
    chunk_size: int = 1000,
    gcs_bucket: str = "graphrag-kg-data",
    prompt_template: str = None,
) -> list[str]:
    """resume_processed → Batch API 요청 파일 생성 (GCS)"""
    gcs = storage.Client()
    bucket = gcs.bucket(gcs_bucket)
    chunk_ids = []

    for i in range(0, len(resume_ids), chunk_size):
        chunk = resume_ids[i:i + chunk_size]
        chunk_id = f"chunk_{i // chunk_size:04d}"

        requests = []
        for rid in chunk:
            # resume_processed에서 텍스트 조회
            text = get_processed_text(rid)
            requests.append({
                "custom_id": rid,
                "params": {
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt_template.format(
                        resume_text=text
                    )}]
                }
            })

        # GCS에 JSONL 업로드
        blob = bucket.blob(f"batch-api/requests/{chunk_id}.jsonl")
        blob.upload_from_string(
            "\n".join(json.dumps(r) for r in requests)
        )
        chunk_ids.append(chunk_id)

    return chunk_ids
```

### checkpoint 내장

```python
# 모든 파이프라인 단계에 checkpoint 적용
# BigQuery processing_log 기반 — 재시작 시 이미 성공한 건 skip

def get_unprocessed_ids(pipeline: str) -> list[str]:
    """아직 처리되지 않은 resume_id 목록 조회"""
    query = f"""
    SELECT r.resume_id
    FROM graphrag_kg.resume_processed r
    LEFT JOIN graphrag_kg.processing_log p
      ON r.resume_id = p.resume_id AND p.pipeline = '{pipeline}' AND p.status = 'SUCCESS'
    WHERE p.resume_id IS NULL AND r.is_duplicate = FALSE
    """
    return [row.resume_id for row in bigquery_client.query(query)]
```

---

## 1-D. Graph + Embedding MVP (Week 5~6)

### Week 5 후반 ~ Week 6 전반 (1.5주)

| # | 작업 | 담당 | 기간 |
|---|------|------|------|
| G-1 | Person 노드 → Neo4j MERGE | DE | 0.5일 |
| G-2 | Chapter 노드 → Neo4j MERGE + HAS_CHAPTER 관계 | DE | 0.5일 |
| G-3 | Skill 노드 + USED_SKILL 관계 (기술사전 기반) | MLE | 0.5일 |
| G-4 | Role 노드 + HAD_ROLE 관계 | MLE | 0.5일 |
| G-5 | Organization 노드 + AT_COMPANY 관계 (이름만) | DE | 0.5일 |
| G-6 | Industry 노드 + IN_INDUSTRY 관계 (경력 기반) | MLE | 0.5일 |
| G-7 | Embedding 생성 (Vertex AI, 1,000건) | MLE | 0.5일 |
| G-8 | Vector Index 적재 | DE | 0.5일 |
| G-9 | Idempotency 테스트 (동일 데이터 2회 적재) | 공동 | 0.5일 |
| G-10 | Cypher 쿼리 5종 작성 (에이전트용) | MLE | 0.5일 |
| G-11 | E2E 검증 + 스팟체크 50건 | 공동 | 0.5일 |

### Graph 적재 코드

```python
# src/graph/load_candidate.py
from neo4j import GraphDatabase

def load_candidate_to_graph(driver, candidate_context: dict):
    """CandidateContext → Neo4j 적재"""
    with driver.session() as session:
        # Person 노드
        session.run("""
            MERGE (p:Person {candidate_id: $cid})
            SET p.total_years = $total_years,
                p.seniority_estimate = $seniority,
                p.primary_domain = $domain,
                p.updated_at = datetime()
        """, cid=candidate_context["candidate_id"],
             total_years=candidate_context.get("total_years"),
             seniority=candidate_context.get("seniority_estimate"),
             domain=candidate_context.get("primary_domain"))

        # Chapter 노드 + 관계
        for i, exp in enumerate(candidate_context.get("experiences", [])):
            chapter_id = f"{candidate_context['candidate_id']}_ch{i}"
            session.run("""
                MERGE (c:Chapter {chapter_id: $chid})
                SET c.scope_type = $scope,
                    c.outcome = $outcome,
                    c.duration_months = $duration,
                    c.is_current = $current
                WITH c
                MATCH (p:Person {candidate_id: $cid})
                MERGE (p)-[:HAS_CHAPTER]->(c)
            """, chid=chapter_id, cid=candidate_context["candidate_id"],
                 scope=exp.get("scope_type"), outcome=exp.get("outcome"),
                 duration=exp.get("duration_months"), current=exp.get("is_current", False))

            # Skill 관계
            for skill in exp.get("skills", []):
                session.run("""
                    MERGE (s:Skill {name: $skill})
                    WITH s
                    MATCH (c:Chapter {chapter_id: $chid})
                    MERGE (c)-[:USED_SKILL]->(s)
                """, skill=skill, chid=chapter_id)

            # Role 관계
            if exp.get("role"):
                session.run("""
                    MERGE (r:Role {name: $role})
                    WITH r
                    MATCH (c:Chapter {chapter_id: $chid})
                    MERGE (c)-[:HAD_ROLE]->(r)
                """, role=exp["role"], chid=chapter_id)

            # Organization 관계 (이름만)
            if exp.get("company"):
                session.run("""
                    MERGE (o:Organization {name: $company})
                    WITH o
                    MATCH (c:Chapter {chapter_id: $chid})
                    MERGE (c)-[:AT_COMPANY]->(o)
                """, company=exp["company"], chid=chapter_id)
```

### 에이전트용 Cypher 쿼리 5종

```cypher
-- Q1: 스킬 기반 후보자 검색
MATCH (p:Person)-[:HAS_CHAPTER]->(c:Chapter)-[:USED_SKILL]->(s:Skill)
WHERE s.name IN $skills
WITH p, COUNT(DISTINCT s) AS matched_skills, COLLECT(DISTINCT s.name) AS skill_list
WHERE matched_skills >= $min_match
RETURN p.candidate_id, p.seniority_estimate, p.total_years, skill_list
ORDER BY matched_skills DESC
LIMIT 20

-- Q2: Vector Search (시맨틱 유사 경력 검색)
CALL db.index.vector.queryNodes('chapter_embedding', $top_k, $query_embedding)
YIELD node AS c, score
MATCH (p:Person)-[:HAS_CHAPTER]->(c)
RETURN p.candidate_id, c.scope_type, c.outcome, score
ORDER BY score DESC

-- Q3: 특정 회사 출신 후보자
MATCH (p:Person)-[:HAS_CHAPTER]->(c:Chapter)-[:AT_COMPANY]->(o:Organization)
WHERE o.name CONTAINS $company_name
RETURN p.candidate_id, p.seniority_estimate, c.duration_months, o.name

-- Q4: 시니어리티별 도메인 분포
MATCH (p:Person)
WHERE p.seniority_estimate = $seniority
RETURN p.primary_domain, COUNT(*) AS cnt
ORDER BY cnt DESC

-- Q5: 복합 조건 (스킬 + 경력연수 + 시니어리티)
MATCH (p:Person)-[:HAS_CHAPTER]->(c:Chapter)-[:USED_SKILL]->(s:Skill)
WHERE s.name IN $skills
  AND p.total_years >= $min_years
  AND p.seniority_estimate IN $seniority_levels
WITH p, COLLECT(DISTINCT s.name) AS skills, COUNT(DISTINCT c) AS chapters
RETURN p.candidate_id, p.total_years, p.seniority_estimate, skills, chapters
ORDER BY p.total_years DESC
LIMIT 20
```

---

## MVP 데모 (Week 6 중반)

```
Week 6 중반 체크포인트:
  □ 크롤링 파이프라인 동작 (일일 자동 수집)
  □ 기존 DB + 크롤링 데이터 1,000건+ 처리 완료
  □ Neo4j Graph 동작 (Person, Chapter, Skill, Role 노드)
  □ Vector Index 동작 (chapter_embedding 검색)
  □ Cypher 쿼리 5종 동작 확인
  □ 에이전트 연동 가능 상태

→ 에이전트 팀에 연동 시작 안내
```

---

## 오케스트레이션 (Makefile)

```makefile
# Makefile — Phase 1 + Phase 2 오케스트레이션
.PHONY: crawl preprocess batch-prepare batch-submit batch-collect \
        graph-load embedding full-pipeline status

SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com
REGION=asia-northeast3

# === 크롤링 ===
crawl:
	gcloud run jobs execute kg-crawler --region=$(REGION) --wait

# === 전처리 ===
preprocess:
	gcloud run jobs execute kg-preprocess --region=$(REGION) --wait

# === LLM 추출 (Batch API) ===
batch-prepare:
	gcloud run jobs execute kg-batch-prepare --region=$(REGION) --wait

batch-submit:
	gcloud run jobs execute kg-batch-submit --region=$(REGION) --wait

batch-collect:
	gcloud run jobs execute kg-batch-collect --region=$(REGION) --wait

# === Graph ===
graph-load:
	gcloud run jobs execute kg-graph-load --region=$(REGION) --wait

embedding:
	gcloud run jobs execute kg-embedding --region=$(REGION) --wait

# === 통합 ===
full-pipeline: preprocess batch-prepare batch-submit
	@echo "Batch submitted. Run 'make batch-collect' after completion."
	@echo "Then run 'make graph-load embedding'"

# === 모니터링 ===
status:
	@echo "=== Processing Status ==="
	@bq query --nouse_legacy_sql \
	  'SELECT pipeline, status, COUNT(*) as cnt FROM graphrag_kg.processing_log GROUP BY pipeline, status'
	@echo ""
	@echo "=== Batch Tracking ==="
	@bq query --nouse_legacy_sql \
	  'SELECT status, COUNT(*) as cnt FROM graphrag_kg.batch_tracking GROUP BY status'
	@echo ""
	@echo "=== Crawling Status ==="
	@bq query --nouse_legacy_sql \
	  'SELECT source_site, COUNT(*) as cnt, MAX(crawl_date) as latest FROM graphrag_kg.resume_raw GROUP BY source_site'
	@echo ""
	@echo "=== Dead Letters ==="
	@bq query --nouse_legacy_sql \
	  'SELECT failure_tier, COUNT(*) as cnt FROM graphrag_kg.parse_failure_log GROUP BY failure_tier'
```

---

## Phase 1 완료 산출물 (Week 6 중반)

```
□ 크롤링 파이프라인 동작
  ├─ 사이트 N곳 크롤러 구현
  ├─ Cloud Run Job + Cloud Scheduler 설정
  ├─ 일일 자동 크롤링 가동
  └─ 파일럿 수집 결과 (사이트당 100건+)

□ 전처리 파이프라인 동작
  ├─ 정규화 + PII 마스킹 + SimHash 중복제거
  ├─ 경력 블록 분리
  └─ 기존 DB + 크롤링 데이터 통합 처리

□ CandidateContext LLM 추출 동작
  ├─ LLM 프롬프트 3종 (experience, career, work_style)
  ├─ Batch API 인프라 (prepare/submit/poll/collect)
  ├─ LLM 파싱 실패 3-tier
  └─ 1,000건 E2E 완료

□ Neo4j Graph MVP
  ├─ Person, Chapter, Skill, Role, Organization, Industry 노드
  ├─ Vector Index (chapter_embedding)
  ├─ Cypher 쿼리 5종
  └─ 50건 수동 검증

□ Makefile 기반 오케스트레이션
□ BigQuery checkpoint (processing_log, batch_tracking)
```
