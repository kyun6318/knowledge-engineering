# Phase 4: 외부 보강 + 품질 + 운영 (4주, Week 24-27)

> **목적**: 홈페이지/뉴스 크롤링으로 CompanyContext 기본 필드를 보강하고,
> 품질 평가 + 자동화 + 운영 인프라를 구축하여 프로덕션 운영 상태로 전환.
>
> **v1 대비 변경**:
> - 기간 6주→4주 (S3): tension/culture_signals를 Phase 5로 이동
> - Runbook + Alarm 전체 구축을 이 단계에서 수행 (S2)
> - 크롤링 정책 문서: 법무 결론 후 작성 (S4 조기 상세화 제거)
> - CompanyContext 보강 범위: 기본 필드만 (product, funding, employee, growth)
>
> **데이터 확장**: Graph + Matching → **+ 기업 인텔리전스 (기본)**
> **에이전트 역량 변화**: 매칭 → **+ 기업 투자/성장 필터 + 프로덕션 운영**
>
> **인력**: DE 1명 + MLE 1명 풀타임 + 도메인 전문가 1명 파트타임 (품질 평가)

---

## 4-1. 홈페이지/뉴스 크롤링 파이프라인 (2주) — Week 24-25

> v1(4주)→v2(2주): tension/culture 추출 제거로 크롤링 범위 축소.

### Week 24: 크롤러 인프라 + 홈페이지 크롤링

| # | 작업 | 담당 | 기간 |
|---|------|------|------|
| 4-1-1 | Cloud Run Job + Playwright Docker | DE | 1일 |
| 4-1-2 | 기업 홈페이지 크롤러 (1,000개 기업) | DE | 2일 |
| 4-1-3 | 뉴스 수집기 (API/RSS 기반) | DE | 1일 |
| 4-1-4 | 크롤링 정책 문서 작성 (★ 법무 결론 반영) | 공동 | 0.5일 |

### Week 25: LLM 추출 + 적재

| # | 작업 | 담당 | 기간 |
|---|------|------|------|
| 4-1-5 | Gemini Flash 기업 정보 추출 (기본 필드만) | MLE | 2일 |
| 4-1-6 | CompanyContext 보강 적재 (Neo4j) | DE | 1일|
| 4-1-7 | 파일럿 검수 (100개 기업) | 공동 | 1일 |
| 4-1-8 | 에러 핸들링 + 재시도 자동화 | DE | 1일 |

### 크롤링 BigQuery 테이블 스키마 (3개 테이블 + 1 뷰)

```sql
-- 1. 크롤링 대상 기업 목록
CREATE TABLE graphrag_kg.crawl_company_targets (
  company_id STRING NOT NULL,
  company_name STRING NOT NULL,
  aliases ARRAY<STRING>,
  domain_url STRING,
  nice_industry_code STRING,
  is_active BOOLEAN DEFAULT TRUE,
  last_homepage_crawl TIMESTAMP,
  last_news_crawl TIMESTAMP,
  created_at TIMESTAMP
);

-- 2. 크롤링 원본 데이터 (homepage + news 통합)
CREATE TABLE graphrag_kg.crawl_raw_data (
  company_id STRING NOT NULL,
  source_type STRING NOT NULL,        -- 'homepage' | 'news'
  source_id STRING NOT NULL,          -- page URL 또는 article_id
  crawl_date DATE NOT NULL,
  title STRING,                       -- news: 기사 제목, homepage: 페이지 제목
  url STRING,
  page_type STRING,                   -- homepage: about/product/careers, news: null
  category STRING,                    -- news: funding/org_change/mna/etc, homepage: null
  source_media STRING,                -- news only
  publish_date DATE,                  -- news only
  is_press_release BOOLEAN,           -- news only
  body_length INT64,
  crawl_status STRING,
  gcs_raw_path STRING,
  gcs_text_path STRING,
  created_at TIMESTAMP
);

-- 3. LLM 추출 결과
CREATE TABLE graphrag_kg.crawl_extracted_fields (
  company_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  source_type STRING,
  source_id STRING,
  product_description STRING,
  market_segment STRING,
  funding_round STRING,
  funding_amount STRING,
  investors ARRAY<STRING>,
  growth_narrative STRING,
  extraction_model STRING,
  evidence_spans JSON,
  confidence FLOAT64,
  adjusted_confidence FLOAT64,
  created_at TIMESTAMP
);

-- 4. 기업 크롤링 요약 (뷰)
CREATE VIEW graphrag_kg.crawl_company_summary AS
SELECT
  company_id,
  COUNTIF(source_type = 'homepage') AS homepage_pages_count,
  COUNTIF(source_type = 'news') AS news_articles_count,
  (SELECT COUNT(*) FROM graphrag_kg.crawl_extracted_fields ef
   WHERE ef.company_id = rd.company_id) AS extracted_fields_count,
  MAX(crawl_date) AS last_crawl_date
FROM graphrag_kg.crawl_raw_data rd
GROUP BY company_id;
```

### CompanyContext 보강 범위 (★ v2: 기본 필드만)

```
Phase 4에서 보강하는 필드 (필수):
  - product_description: 주요 제품/서비스 설명
  - market_segment: 시장 분류
  - funding_round: 최근 투자 라운드 (Seed, Series A, B, C, ...)
  - funding_amount: 투자 금액
  - investors: 주요 투자사
  - employee_count: 직원 수 (추정)
  - founded_year: 설립 연도
  - growth_narrative: 성장 내러티브 (1~2문장)

Phase 5로 이동한 필드 (선택):
  - tension_type, tension_description  → Phase 5
  - culture_signals (remote_friendly, diversity_focus, learning_culture) → Phase 5
  - scale_signals (growth_rate, market_position) → Phase 5
```

---

## 4-2. CompanyContext 보강 적재 (1주, 4-1과 병행) — Week 25

> v1과 동일 구조, 범위만 축소 (기본 필드).

---

## 4-3. 품질 평가 Gold Test Set (3일) — Week 26 전반

> v1과 동일 (200건 후보자-매칭 쌍 검수, 도메인 전문가 파트타임).

### 전문가 확보 시점

> 전문가 2인 × 200건 검수 비용 $5,840 (Gold Label 인건비).
> **Phase 3 완료 시점(Week 22)**에서 전문가 확보 시작. Phase 4-3 시작(Week 26) 전까지 최소 3~4주 리드타임.

### LLM 추출 품질 평가 기준

| 지표 | 최소 기준 | 목표 |
|---|---|---|
| scope_type 분류 정확도 | > 70% | > 80% |
| outcome 추출 F1 | > 55% | > 70% |
| situational_signal 분류 F1 | > 50% | > 65% |
| vacancy scope_type 정확도 | > 65% | > 80% |
| stage_estimate 정확도 | > 75% | > 85% |
| 피처 1개+ ACTIVE 비율 | > 80% | > 90% |
| Human eval 상관관계 (r) | > 0.4 | > 0.6 |

---

## 4-4. Cloud Workflows + 증분 자동화 (1주) — Week 26

> v1과 동일 (Makefile → Cloud Workflows 전환, 일일 증분 파이프라인).

### 오케스트레이션 전환 (★ v2: 일관된 도구 사용)

```
Phase 0-3: Makefile 기반 (수동/반자동)
Phase 4:   Cloud Workflows로 전환 (전체 자동화)

→ 리뷰 C1(오케스트레이션 도구 통일)은 Phase 4에서 자연스럽게 해결
→ Phase 0-3에서는 Makefile이 충분 (PoC/MVP 단계)
```

### 증분 처리 일일 유입량 추정 근거

```
일일 이력서 유입량 추정:
  - 현재 채용 플랫폼의 일일 이력서 유입량 데이터를 Phase 0에서 확인 필요
  - 가정: 월 20,000~30,000건 유입 → 일 ~1,000건 (영업일 기준)
  - 이 수치가 운영 비용의 기반

  → Phase 0 프로파일링에서 실제 유입량 확인 후 보정:
    - 실제 유입량 < 500/일: 증분 주기를 주 1회로 변경, 비용 절감
    - 실제 유입량 > 2,000/일: Batch API 사용 고려, 비용 재산정
```

### 이력서 업데이트 시 Graph 처리 전략

```
동일 candidate_id로 이력서가 업데이트된 경우:

1. 변경 감지: GCS Object metadata timeCreated vs processing_log 비교
   - 기존 candidate_id가 processing_log에 있고, GCS에 새 파일이 있으면 → 업데이트

2. Graph 처리 전략: DETACH DELETE 후 재생성
   - Person 노드는 유지 (MERGE)
   - 기존 Chapter 노드: DETACH DELETE (관계 포함 삭제)
   - 새 Chapter 노드: CREATE
   - 이유: Chapter는 경력 블록 단위이므로 부분 업데이트보다 재생성이 안전

3. 코드 패턴:
   MATCH (p:Person {candidate_id: $candidate_id})-[:HAS_CHAPTER]->(c:Chapter)
   DETACH DELETE c
   // → 새 Chapter 노드 생성

4. Embedding: 삭제된 Chapter의 embedding은 자동으로 Vector Index에서 제거
   새 Chapter의 embedding 재생성

5. MAPPED_TO: 해당 Person의 MAPPED_TO 관계 전체 재계산
```

### Cloud Scheduler 설정

```bash
SA=kg-loading@graphrag-kg.iam.gserviceaccount.com

# 일일 증분 처리
gcloud scheduler jobs create http kg-incremental-daily \
  --schedule="0 2 * * *" \
  --uri="https://workflowexecutions.googleapis.com/v1/projects/graphrag-kg/locations/asia-northeast3/workflows/kg-incremental/executions" \
  --http-method=POST \
  --oauth-service-account-email=$SA \
  --time-zone="Asia/Seoul"

# Dead-letter 재처리 (일일)
gcloud scheduler jobs create http kg-dead-letter-daily \
  --schedule="0 4 * * *" \
  --uri="https://asia-northeast3-run.googleapis.com/v2/projects/graphrag-kg/locations/asia-northeast3/jobs/kg-dead-letter:run" \
  --http-method=POST \
  --oauth-service-account-email=$SA \
  --time-zone="Asia/Seoul"

# 크롤링 (30일 주기)
gcloud scheduler jobs create http crawl-monthly \
  --schedule="0 0 1 * *" \
  --uri="https://workflowexecutions.googleapis.com/v1/projects/graphrag-kg/locations/asia-northeast3/workflows/crawl-pipeline/executions" \
  --http-method=POST \
  --oauth-service-account-email=$SA \
  --time-zone="Asia/Seoul"

# Neo4j 주간 백업
gcloud scheduler jobs create http neo4j-weekly-backup \
  --schedule="0 3 * * 0" \
  --uri="https://asia-northeast3-run.googleapis.com/v2/projects/graphrag-kg/locations/asia-northeast3/jobs/kg-neo4j-backup:run" \
  --http-method=POST \
  --oauth-service-account-email=$SA \
  --time-zone="Asia/Seoul"
```

---

## 4-5. 운영 인프라 + Runbook + 인수인계 (1주) — Week 27

> ★ v2: Runbook/Alarm을 이 단계에서 전체 구축 (v1은 Phase 0-1에 과도하게 배치).

### Runbook 5종 (★ v2: Phase 4로 이동)

```
1. Runbook: Batch API 실패 대응
   - 증상: chunk FAILED 상태, dead-letter 누적
   - 진단: BigQuery batch_tracking → 실패 원인 분류
   - 조치: 재시도 (max 2) → 프롬프트 수정 → Gemini Flash 전환

2. Runbook: Neo4j 연결 실패
   - 증상: Connection refused, timeout
   - 진단: AuraDB 콘솔 → 인스턴스 상태 확인
   - 조치: 연결 풀 리셋 → 인스턴스 재시작 → 백업 복구

3. Runbook: 크롤링 차단 대응
   - 증상: HTTP 403/429, Cloudflare 차단
   - 진단: 에러 로그 분석 → 차단 유형 식별
   - 조치: rate limit 확대 → 프록시 전환 → 해당 사이트 스킵

4. Runbook: 품질 이상 감지
   - 증상: schema 준수율 < 95%, 분포 이상
   - 진단: quality_metrics 테이블 조회 → 원인 분석
   - 조치: 프롬프트 버전 롤백 → 샘플 재검증 → 재처리

5. Runbook: 증분 파이프라인 실패
   - 증상: Cloud Workflows 실패, 일일 업데이트 중단
   - 진단: Workflows 로그 → 실패 단계 식별
   - 조치: 수동 재실행 → 단계별 디버깅 → Slack 알림
```

### Alarm 구성 (★ v2: Phase 4에서 구축)

```
Critical (즉시 대응):
  1. Neo4j 연결 실패 (5분 연속)
  2. Batch API 3회 연속 실패
  3. 증분 파이프라인 2일 연속 실패

Warning (당일 대응):
  4. schema 준수율 < 95%
  5. dead-letter 비율 > 5%
  6. Neo4j 노드 수 급변 (±10% 이상)

Info (주간 리뷰):
  7. 일일 처리 건수 요약
  8. 비용 추적 (일일/주간)
  9. 크롤링 성공률
  10. 쿼리 응답 시간 p95
```

### Neo4j 백업 자동화

```
□ 주간 백업: Neo4j → GCS (스냅샷)
□ GCS Versioning 활성화
□ 백업 복구 테스트 (1회)
□ 롤백 가능: loaded_batch_id 기반 선택적 삭제
```

### 운영 인력 계획

```
운영 업무량 추정:
  - 일일 증분 파이프라인 모니터링: 30분/일
  - 주간 알림 확인 + 장애 대응: 2시간/주
  - 월간 크롤링 결과 검수: 4시간/월
  - 분기 사전 업데이트 + 전체 재처리: 2~3일/분기
  - 프롬프트 업데이트 (필요 시): 2~3일/건

필요 인력: 풀타임 0.3~0.5명 (주 1~2일)
  - DE 또는 MLE 중 1명이 운영 겸임 (다른 프로젝트와 병행)
  - 장애 대응 on-call: DE/MLE 교대
```

### 인수인계 문서 목차

```
□ 운영 매뉴얼:
  1. 시스템 아키텍처 개요
  2. 일일 운영 체크리스트
  3. 알림별 대응 절차 (Runbook 5종)
  4. 증분 처리 파이프라인 구조 + 장애 대응
  5. 크롤링 파이프라인 구조 + 법적 준수 사항
  6. 프롬프트 업데이트 절차 + regression test 실행 방법
  7. 사전(tech/company/role) 업데이트 절차
  8. Neo4j 백업/복원 절차
  9. 비용 모니터링 + Budget Alert 설정
  10. Secret Manager 키 로테이션 절차

□ API 문서 (Swagger/OpenAPI)
□ 비용 리포트 (Phase 0-4 실적)
□ 담당자 연락처 + 에스컬레이션 경로
```

---

## Phase 4 완료 산출물

```
□ 홈페이지/뉴스 크롤링 파이프라인 (2주, v1: 4주)
  ├─ 1,000개 기업 크롤링
  ├─ Gemini Flash 추출 (기본 필드)
  └─ 크롤링 정책 문서 (법무 반영)

□ CompanyContext 보강 (기본 필드만)
  ├─ product, funding, employee, growth
  └─ tension/culture/scale은 Phase 5

□ 품질 평가 Gold Test Set (200건)

□ 자동화
  ├─ Cloud Workflows (전체 DAG)
  ├─ Cloud Scheduler (일일 증분)
  └─ Makefile → Workflows 전환 완료

□ ★ 운영 인프라 (v2: 이 단계에서 전체 구축)
  ├─ Runbook 5종
  ├─ Alarm 10종 (Critical 3 + Warning 3 + Info 4)
  ├─ Slack Webhook 연동
  ├─ Neo4j 백업 자동화
  ├─ Cloud Scheduler 설정 (일일 증분, dead-letter, 월간 크롤링, 주간 백업)
  ├─ 이력서 업데이트 시 Graph 처리 전략 (DETACH DELETE + 재생성)
  ├─ 운영 인력 계획 (풀타임 0.3~0.5명)
  └─ 인수인계 문서 (10개 항목 목차)

□ Go/No-Go → 운영 전환
```

---

## 예상 비용 (Phase 4, 4주)

> v1(6주, $6,138~6,363)→v2(4주, $214~374 + Gold Label $5,840)

| 항목 | 비용 | v1 대비 |
|------|------|---------|
| Gemini API (크롤링 LLM) | ~$11 | 동일 (기본 필드만) |
| Anthropic API (Gold Label) | ~$20 | 동일 |
| Vertex AI Embedding | ~$0.1 | 동일 |
| Neo4j Professional (4주) | $100~200 | -$125~250 (기간 축소) |
| Cloud Run + GCS + BQ | ~$20 | -$17 |
| Cloud Workflows + Scheduler | ~$2 | 동일 |
| **Phase 4 인프라+LLM 합계** | **$153~253** | -$111~236 |
| Gold Label 인건비 | $5,840 | 동일 |
| **Phase 4 총합계** | **$5,993~6,093** | -$45~270 |
