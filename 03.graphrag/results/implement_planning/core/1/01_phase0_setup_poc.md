# Phase 0: 사전 준비 + 환경 구성 + PoC (Week 0~1)

> **목적**: 사전 준비를 병렬 진행하고, Week 1에서 GCP 환경 + LLM PoC + 크롤링 실현 가능성을 검증.
> Phase 2(파일 파싱)에 필요한 HWP/PDF PoC 항목도 사전 조사 수준으로 포함.
>
> **인력**: DE 1명 + MLE 1명 풀타임
> **산출물**: GCP 환경 완성 + PoC 결과 + 크롤링 설계서 + Go/No-Go 판정

---

## Week 0: 사전 준비 (8주 카운트에 미포함, 지금 즉시)

> 아래 항목은 모두 **병렬 실행** 가능. Phase 0 시작 전에 완료하거나 병행.

### Blocking #1: Anthropic Batch API Quota 확인

```
□ Anthropic 콘솔(console.anthropic.com)에서 즉시 확인:
  ├─ 현재 Tier → 결과: Tier ___
  ├─ Claude Haiku 4.5 Batch API 지원 여부 → 결과: ___
  ├─ 동시 활성 batch 수 한도 → 결과: ___
  ├─ 일일 요청 한도(RPD) → 결과: ___
  └─ Batch 결과 보관 기간 (현재 29일) → 결과: ___

□ 필요 시 Tier 업그레이드 요청 (1~2주 소요 감안)
  - 필요 조건: 동시 10+ batch, 일 50K+ 요청

확인 결과별 대응:
  - 동시 ≥ 10: 계획대로 진행
  - 동시 5~9: Phase 2 기간 +1~2주 연장 감안
  - 동시 ≤ 4: Gemini Flash 병행 또는 chunk 크기 확대
```

### Blocking #2: 법무 PII 검토

```
□ 법무팀에 PII 처리 방침 검토 요청
  - 이력서 PII를 외부 LLM API에 마스킹 전송 가능 여부
  - Anthropic Data Processing Agreement 검토

→ 결론 대기 중에도 마스킹 적용 상태로 진행
→ 법무 허용 판정 시 마스킹 제거 옵션 적용
```

### Blocking #3: 크롤링 법적 검토

```
□ 법무팀에 크롤링 법적 검토 요청
  - 채용 사이트 크롤링의 저작권법/정보통신망법 적합성
  - 이용약관 위반 가능성
  - 크롤링 데이터의 LLM 입력 활용 시 법적 이슈

□ 크롤링 정책 문서화:
  - robots.txt 준수
  - 요청 간격 3초+
  - User-Agent 명시
  - 원본 비보관 옵션 (추출 후 삭제 가능)
```

### 사전 조사: 크롤링 대상 사이트

```
□ 대상 사이트 목록 작성 (최소 3곳)
  - 사이트 A: ___
  - 사이트 B: ___
  - 사이트 C: ___

□ 각 사이트별 사전 조사:
  ├─ robots.txt 확인 → 크롤링 허용 범위
  ├─ 이력서 페이지 URL 패턴
  ├─ 로그인/인증 필요 여부
  ├─ 페이지네이션 방식 (offset? cursor? infinite scroll?)
  ├─ 이력서 데이터 형태 (HTML 구조화? 자유형 텍스트?)
  ├─ 예상 수집 가능 건수
  └─ Anti-bot 대응 (Cloudflare, reCAPTCHA 등)
```

### 기존 데이터 확보

```
□ 기존 이력서 DB 데이터 샘플 100건 확보
  ├─ 필드 구조 확인 (어떤 컬럼이 있는지)
  ├─ 텍스트 필드 내용 확인 (구조화 수준)
  └─ BigQuery 또는 다른 DB에서 export
```

### 사전 준비 체크리스트

```
□ Anthropic Batch API quota 확인 완료
□ 법무 PII 검토 요청 완료
□ 크롤링 법적 검토 요청 완료
□ 크롤링 대상 사이트 3곳 사전 조사 완료
□ 기존 DB 샘플 100건 확보
□ GCP 프로젝트 생성 (또는 기존 프로젝트 사용 확인)
```

---

## Week 1: Phase 0 — 환경 + PoC (1주)

### DE 담당 (Day 1~5)

#### Day 1-2: GCP 환경 구성

```bash
# 프로젝트 설정
gcloud config set project graphrag-kg

# API 활성화
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  bigquery.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com

# 서비스 계정
gcloud iam service-accounts create kg-pipeline \
  --display-name="KG Pipeline Service Account"

SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com

for ROLE in storage.objectAdmin bigquery.dataEditor \
  secretmanager.secretAccessor run.invoker \
  monitoring.metricWriter logging.logWriter aiplatform.user; do
  gcloud projects add-iam-policy-binding graphrag-kg \
    --member="serviceAccount:$SA" \
    --role="roles/$ROLE"
done

# Artifact Registry
gcloud artifacts repositories create kg-pipeline \
  --repository-format=docker \
  --location=asia-northeast3

# GCS
gcloud storage buckets create gs://graphrag-kg-data \
  --location=asia-northeast3 \
  --uniform-bucket-level-access
gcloud storage buckets update gs://graphrag-kg-data --versioning

# BigQuery
bq mk --dataset --location=asia-northeast3 graphrag_kg
```

#### Day 2: BigQuery 테이블 생성

```sql
-- 크롤링 수집 이력서
CREATE TABLE graphrag_kg.resume_raw (
  resume_id STRING NOT NULL,
  source_site STRING NOT NULL,
  source_url STRING,
  crawl_date DATE,
  candidate_name STRING,
  raw_text STRING,
  structured_fields JSON,
  content_hash STRING,
  is_processed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- 전처리 완료 이력서
CREATE TABLE graphrag_kg.resume_processed (
  resume_id STRING NOT NULL,
  source_resume_id STRING NOT NULL,
  masked_text STRING,
  career_blocks JSON,
  dedup_hash STRING,
  is_duplicate BOOLEAN DEFAULT FALSE,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- 처리 이력 (checkpoint)
CREATE TABLE graphrag_kg.processing_log (
  id STRING NOT NULL,
  resume_id STRING NOT NULL,
  pipeline STRING NOT NULL,
  status STRING NOT NULL,
  error_message STRING,
  input_tokens INT64,
  output_tokens INT64,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Batch API 추적
CREATE TABLE graphrag_kg.batch_tracking (
  batch_id STRING NOT NULL,
  chunk_id STRING NOT NULL,
  status STRING,
  submitted_at TIMESTAMP,
  completed_at TIMESTAMP,
  result_collected BOOLEAN DEFAULT FALSE,
  retry_count INT64 DEFAULT 0,
  gcs_request_path STRING,
  gcs_response_path STRING
);

-- LLM 파싱 실패
CREATE TABLE graphrag_kg.parse_failure_log (
  id STRING NOT NULL,
  resume_id STRING NOT NULL,
  pipeline STRING,
  failure_tier STRING,
  error_type STRING,
  error_detail STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

#### Day 2-3: Neo4j + 인프라

```
□ Neo4j AuraDB Free 인스턴스 생성
  - 리전: asia-northeast1 (도쿄)
  - 연결 URI + password → Secret Manager 등록

□ Graph 스키마 적용:
  CREATE CONSTRAINT person_id FOR (p:Person) REQUIRE p.candidate_id IS UNIQUE;
  CREATE CONSTRAINT chapter_id FOR (c:Chapter) REQUIRE c.chapter_id IS UNIQUE;
  CREATE CONSTRAINT skill_name FOR (s:Skill) REQUIRE s.name IS UNIQUE;
  CREATE CONSTRAINT role_name FOR (r:Role) REQUIRE r.name IS UNIQUE;
  CREATE CONSTRAINT org_name FOR (o:Organization) REQUIRE o.name IS UNIQUE;
  CREATE CONSTRAINT industry_code FOR (i:Industry) REQUIRE i.code IS UNIQUE;

□ Vector Index 설정:
  CREATE VECTOR INDEX chapter_embedding FOR (c:Chapter)
  ON (c.embedding)
  OPTIONS {indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }};

□ Secret Manager 등록:
  - neo4j-uri, neo4j-password
  - anthropic-api-key
```

#### Day 3-5: 크롤링 대상 사이트 구조 분석

```
□ 사이트별 DOM 구조 분석 (Playwright dev tools)
  - 이력서 목록 페이지 → URL 패턴 + 페이지네이션
  - 이력서 상세 페이지 → 텍스트 추출 포인트
  - 로그인 플로우 → 세션 유지 방법

□ 파일럿 크롤링 (사이트당 10건)
  - 수집 성공률 확인
  - 데이터 품질 확인 (텍스트 길이, 구조화 수준)
  - Anti-bot 대응 필요 여부

□ 크롤링 설계서 산출:
  - 사이트별 크롤링 전략
  - 예상 일일 수집량
  - 에러 핸들링 전략
  - rate limiting 설정
```

---

### MLE 담당 (Day 1~5)

#### Day 1-2: DB 데이터 프로파일링

```python
# 샘플 100건 프로파일링
from google.cloud import bigquery
import json

client = bigquery.Client()

# 1. 필드 분포 확인
query = """
SELECT
  COUNT(*) as total,
  COUNTIF(raw_text IS NOT NULL AND LENGTH(raw_text) > 100) as has_text,
  COUNTIF(structured_fields IS NOT NULL) as has_structured,
  AVG(LENGTH(raw_text)) as avg_text_length,
  MIN(LENGTH(raw_text)) as min_text_length,
  MAX(LENGTH(raw_text)) as max_text_length
FROM graphrag_kg.resume_raw
LIMIT 100
"""

# 2. 텍스트 언어 분포
# 한국어/영어/혼합 비율 확인

# 3. 경력 정보 추출 가능성
# 회사명, 직책, 기간이 텍스트에서 식별 가능한지 20건 수동 확인

# 프로파일 산출물:
profile = {
    "total_records": None,
    "text_coverage": None,         # raw_text 비어있지 않은 비율
    "avg_text_length": None,       # 평균 텍스트 길이
    "language_distribution": {},    # 한국어/영어/혼합
    "structured_field_coverage": {},# 필드별 비어있지 않은 비율
    "career_block_identifiable": None,  # 경력 블록 분리 가능 비율
    "estimated_token_per_resume": None, # 한국어 보정 포함
}
```

#### Day 3-4: LLM 추출 PoC (20건)

```python
# CandidateContext 추출 PoC
# DB 텍스트 → 구조화된 경력 정보

import anthropic

client = anthropic.Anthropic()

CANDIDATE_EXTRACT_PROMPT = """
다음 이력서 텍스트에서 경력 정보를 추출해주세요.

## 출력 형식 (JSON)
{
  "experiences": [
    {
      "company": "회사명",
      "role": "직책/역할",
      "duration_months": 24,
      "scope_type": "EXECUTE|BUILD|DESIGN|STRATEGY",
      "skills": ["Python", "AWS"],
      "outcome": "주요 성과 요약",
      "is_current": false
    }
  ],
  "seniority_estimate": "JUNIOR|MID|SENIOR|LEAD|EXECUTIVE",
  "total_years": 5,
  "primary_domain": "Backend|Frontend|Data|DevOps|...",
  "work_style_signals": {
    "leadership": false,
    "mentoring": false,
    "cross_functional": false
  }
}

## 이력서 텍스트
{resume_text}
"""

# 20건 실행 + 품질 확인
results = []
for resume in sample_20:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": CANDIDATE_EXTRACT_PROMPT.format(
            resume_text=resume["masked_text"]
        )}]
    )
    results.append(parse_json(response.content[0].text))

# 품질 측정: scope_type 정확도 (수동 라벨 대비)
```

#### Day 4: Embedding 모델 선택

```python
# text-embedding-005 빠른 검증
from google.cloud import aiplatform

# 10쌍 유사/비유사 경력 텍스트로 분별력 확인
similar_pairs = [
    ("Python 백엔드 3년 경험", "Django REST API 개발 경력"),
    # ...
]
dissimilar_pairs = [
    ("Python 백엔드 3년 경험", "인사총무 10년 경력"),
    # ...
]

# cosine similarity 분포 비교
# → similar > 0.7, dissimilar < 0.4 이면 Pass
```

#### Day 5: Batch API 응답 시간 실측

```python
# Batch API 3~5건 실측 → Phase 2 타임라인 확정
import time
from datetime import datetime

batch_timing = []
for i in range(3):
    batch = client.messages.batches.create(requests=sample_requests_5)
    submit_time = datetime.utcnow()

    while True:
        status = client.messages.batches.retrieve(batch.id)
        if status.processing_status == "ended":
            elapsed = (datetime.utcnow() - submit_time).total_seconds() / 3600
            batch_timing.append(elapsed)
            break
        time.sleep(300)

print(f"Batch API 평균 응답: {sum(batch_timing)/len(batch_timing):.1f}h")
# → Phase 2 시나리오 확정 (낙관/기본/비관)
```

---

### 공동: Go/No-Go 판정 (Day 5)

| 기준 | 통과 조건 | 미달 시 대응 |
|------|-----------|-------------|
| LLM 추출 품질 | 20건 scope_type 정확도 > 60% | 프롬프트 재설계 + 3일 추가 |
| DB 데이터 품질 | 텍스트 필드 비어있는 비율 < 20% | structured_fields 활용으로 전환 |
| Batch API quota | 계획 실행 최소 조건 확인 | 동시 3 batch로 축소 |
| 크롤링 가능성 | 대상 사이트 1곳+ 파일럿 성공 | 크롤링 스코프 축소 |
| Embedding 분별력 | similar > 0.7, dissimilar < 0.4 | text-embedding-005 기본값 |

---

## Phase 0 산출물

```
□ GCP 환경 구성 완료 (API, 서비스 계정, GCS, BigQuery, Secret Manager)
□ Neo4j AuraDB Free + 스키마 + Vector Index
□ BigQuery 테이블 5개 생성
□ DB 데이터 프로파일 리포트 (100건)
□ LLM 추출 PoC 결과 (20건) + 품질 측정
□ Embedding 모델 확정
□ Batch API 응답 시간 실측 (3~5건)
□ 크롤링 대상 사이트 구조 분석 + 설계서
□ 크롤링 파일럿 결과 (사이트당 10건)
□ Go/No-Go 판정 문서
□ Batch API quota 확인 결과

--- Phase 2 사전 조사 (Week 1 병행, 우선순위 낮음) ---
□ 이력서 원본 파일 형식 분포 사전 조사 (PDF/DOCX/HWP 비율)
  - GCS 업로드 가능 여부 확인
  - HWP 비율이 30% 이상이면 Phase 2 HWP PoC 필수
□ HWP 파싱 3방법 사전 조사 (실행은 Phase 2-0에서)
  - LibreOffice headless 변환 가능 여부
  - pyhwp 라이브러리 한계 확인
  - Gemini 멀티모달 OCR 가능성
□ Document AI 프로세서 사전 생성 (Phase 2 비교 테스트용)
  - OCR Processor → processor name 기록: ___
  - Layout Parser → processor name 기록: ___

--- Phase 3 사전 준비 (Week 0 병렬) ---
□ NICE DB 접근 계약 상태 확인
  - 기존 계약 → API 접근 키 + 필드 + 호출 제한 확인
  - 신규 계약 → 협의 시작 (예상 2~4주)
  - 2주 전까지 미확보 시 → DART + 사업자등록 조회로 대체
```
