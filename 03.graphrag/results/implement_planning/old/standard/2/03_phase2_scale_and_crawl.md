# Phase 2: 확장 + 크롤링 + 품질 (11~14주)

> **목적**: 전체 데이터(500K 이력서) 처리 + 크롤링으로 CompanyContext 보강 + 품질 평가 + 운영 자동화.
>
> **standard.2 변경**:
> - [standard.1.1-5] 2-2 품질 평가 1주→**3일** (Cohen's d/Power analysis Phase 3 이동) (R-10)
> - [standard.1.1-6] 2-5 서빙 인터페이스 1주→**3일** (R-9)
> - [standard.1.1-7] 2-6 증분 처리 1~2주→**2주** 고정 + 보완 (R-2)
> - [standard.1.1-8] Cloud Workflows YAML 상세 제거, **DAG 구조만** 기술 (R-11)
> - [standard.1.1-9] 크롤링 BigQuery 테이블 5개→**3개** 축소 (R-14)
> - [standard.1.1-10] **운영 인력 계획** + 인수인계 문서 태스크 추가 (R-8)
> - [standard.1.1-11] Looker Studio를 Phase 3으로 이동 (R-11)
> - [standard.1.1-15] Phase 2→운영 전환 Go/No-Go 기준 추가 (R-15)
>
> **인력**: DE 1명 + MLE 1명 풀타임, 도메인 전문가 1명 파트타임
> **인력 추가 옵션**: 크롤링 담당 1명 추가 시 2-1(전체 처리)과 2-3(크롤링) 병행 가능 → 9~11주로 단축

---

## Pre-Phase 2: 사전 준비 (Phase 1 완료 ~ Phase 2 시작 사이)

### 크롤링 법적 검토

```bash
□ 법무팀에 크롤링 법적 검토 요청
  - 검토 항목:
    ├─ 기업 홈페이지 크롤링의 저작권법 적합성
    ├─ 네이버 뉴스 API 이용약관 준수 사항
    ├─ 정보통신망법 관련 리스크 (대량 접근, 서버 부하)
    ├─ 크롤링 데이터의 LLM 입력 활용 시 저작권 이슈
    └─ 원본 비보관 정책의 법적 리스크 경감 효과
  - 판정 기한: Phase 2 Week 4 이전 (2-3 크롤링 시작 전)
□ 정책 명시:
  - "추출 목적 한정, 원본 비보관" 정책 문서화
  - robots.txt 준수 + 요청 간격 2초 이상
  - 크롤링 대상 기업 수 제한 (초기 1,000개)
```

### Neo4j Professional 전환 사전 준비

```bash
□ Professional 인스턴스 사양 결정
  - 예상 노드 수: ~2.77M (Phase 0-3-8 계산 기반)
  - 최소 사양: 4GB RAM / 16GB Storage
  - max concurrent connections 확인 → Phase 2 tasks 수 결정 [standard.1.1-12]
  - 리전: asia-northeast1 (도쿄)
□ 예산 승인: $65~200/월 (Phase 2 기간 ~4개월 = $260~800)
□ Phase 1 Neo4j 백업 완료 확인 (APOC export → GCS)
```

---

## 2-0. Neo4j Professional 전환 (1일) — Week 20

> standard.1과 동일. 상세 내용은 `standard.1/03_phase2_scale_and_crawl.md` 2-0절 참조.

---

## 2-1. 전체 데이터 처리 (3~4주) — Week 20-24

> standard.1과 동일한 처리 흐름. Batch API 처리 시간 계산 동일.

### Cloud Workflows DAG 구조 — [standard.1.1-8] YAML 상세 제거

> **standard.2 변경**: standard.1의 30줄+ YAML 구현을 제거. DAG 구조와 도입 의도만 기술.
> 이유: Phase 2 시작까지 16~17주 남은 시점에서 구체적 YAML은 시기상조.
> Phase 1 구현 과정에서 Job 이름, 파라미터, 실행 순서가 변경될 가능성 높음.

```
Cloud Workflows 도입 의도:
  - Phase 1의 Makefile 수동 실행을 자동화
  - DAG 형태로 의존성 관리 + 실패 시 재시도 + 알림

kg-full-pipeline DAG:
  parse_resumes
       ↓
  dedup_resumes
       ↓
  ┌─ company_ctx ──┐
  │                │
  │  candidate_ctx │
  │  (prepare →    │
  │   submit →     │
  │   poll →       │
  │   collect)     │
  └────────────────┘
       ↓
  graph_load
       ↓
  generate_embeddings
       ↓
  compute_mapping
       ↓
  notify (Slack)

kg-incremental DAG:
  detect_changes → (변경 없음 → 종료)
       ↓
  parse_new → extract_and_load

→ YAML 구현은 Phase 2 시작 시점에 작성
```

### Phase 2-1 업무 시간 외 대응 SLA

> 3~4주 전체 데이터 처리 중 야간/주말 모니터링 체계.

```
업무 시간 (09:00~18:00):
  - CRITICAL 알림: 즉시 대응 (30분 내)
  - WARNING 알림: 2시간 내 확인

업무 시간 외 (18:00~09:00, 주말):
  - CRITICAL 알림: Slack 전송만, 다음 업무일 아침 대응
  - 예외: Batch 결과 만료 24시간 이내 → kg-batch-poll 수동 실행 (원격)
  - WARNING 알림: 다음 업무일 아침 확인

자동화로 야간 대응 최소화:
  - kg-batch-poll: Cloud Scheduler 30분 주기 자동 실행
  - dead-letter 일일 자동 재시도
  - batch_tracking 일일 미수집 건 알림
```

---

## 2-2. 품질 평가 (3일, 2-1과 병행) — Week 22-23 [standard.1.1-5]

> **standard.2 변경**: 1주→**3일**. Cohen's d / Power analysis를 Phase 3으로 이동.
> 이유: Phase 2에서 모델은 이미 확정. 모델 간 비교(A/B 테스트)는 Phase 3 ML Distillation에서 적용.

| # | 작업 | 도구 | 소요 |
|---|---|---|---|
| 2-2-1 | Gold Test Set 구축 (전문가 2인 × 200건) | 수동 + BigQuery | 2일 |
| 2-2-2 | Inter-annotator agreement (Cohen's κ) | Python | 0.5일 |
| 2-2-3 | 평가 지표 측정 + BigQuery 적재 | BigQuery quality_metrics | 0.5일 |

> **Phase 3으로 이동된 항목**: Cohen's d (효과 크기), Power analysis → Phase 3-5에서 ML Distillation 모델 vs LLM 비교 시 적용.

### 평가 기준

| 지표 | 최소 기준 | 목표 |
|---|---|---|
| scope_type 분류 정확도 | > 70% | > 80% |
| outcome 추출 F1 | > 55% | > 70% |
| situational_signal 분류 F1 | > 50% | > 65% |
| vacancy scope_type 정확도 | > 65% | > 80% |
| stage_estimate 정확도 | > 75% | > 85% |
| 피처 1개+ ACTIVE 비율 | > 80% | > 90% |
| Human eval 상관관계 (r) | > 0.4 | > 0.6 |

### 전문가 확보 시점

> 전문가 2인 × 200건 검수 비용 $5,840 (Gold Label 인건비).
> **Phase 1 완료 시점(Week 18~19)**에서 전문가 확보 시작. Phase 2-2 시작(Week 22) 전까지 최소 3주 리드타임.

---

## 2-3. 크롤링 파이프라인 구축 (4주) — Week 24-28

> standard.1과 동일한 크롤링 아키텍처.

### [standard.1.1-9] BigQuery 크롤링 테이블 — 5개→3개 축소

> **standard.2 변경**: `crawl_company_summary`를 BigQuery 뷰로 대체, `crawl_homepage_pages`와 `crawl_news_articles`를 `crawl_raw_data`로 통합.

```sql
-- 1. 크롤링 대상 기업 목록 (유지)
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

-- 2. 크롤링 원본 데이터 (통합) — [standard.1.1-9] homepage_pages + news_articles 통합
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

-- 3. LLM 추출 결과 (유지)
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
  tension_type STRING,
  tension_description STRING,
  culture_signals JSON,
  scale_signals JSON,
  extraction_model STRING,
  evidence_spans JSON,
  confidence FLOAT64,
  adjusted_confidence FLOAT64,
  created_at TIMESTAMP
);

-- 4. 기업 크롤링 요약 — [standard.1.1-9] 테이블→뷰로 대체
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

### 크롤링 상세 구현

> 2-3-1(크롤러 인프라, 1주), 2-3-2(홈페이지, 1주), 2-3-3(뉴스, 1주 병행), 2-3-4(LLM 추출, 1주)는 standard.1과 동일.
> 상세 내용은 `standard.1/03_phase2_scale_and_crawl.md` 참조.

---

## 2-4. 크롤링 데이터 → CompanyContext 보강 (1주) — Week 28-29

> standard.1과 동일. 상세 내용은 `standard.1/03_phase2_scale_and_crawl.md` 2-4절 참조.

---

## 2-5. DS/MLE 서빙 인터페이스 (3일) — Week 29 [standard.1.1-6]

> **standard.2 변경**: 1주→**3일**. BigQuery SQL 예시 작성과 문서화에 1주는 과다.
> DS/MLE 인터페이스 요구사항은 Phase 1 중간(Week 12~14)에 사전 확인하여 방향 확정.

| # | 작업 | GCP 서비스 | 소요 |
|---|---|---|---|
| 2-5-1 | BigQuery mapping_features 스키마 확정 | BigQuery | 0.5일 |
| 2-5-2 | SQL 예시 쿼리 작성 + 문서화 | | 1일 |
| 2-5-3 | Context on/off ablation 테스트 쿼리 작성 | BigQuery | 1일 |

> **DS/MLE 인터페이스 사전 확인 (Phase 1 Week 12~14)**:
> - DS/MLE가 실제로 사용할 인터페이스 형태 확인 (API? Jupyter 노트북? BigQuery 직접 쿼리?)
> - 결과를 Phase 2-5 구현에 반영

---

## 2-6. 증분 처리 + 운영 인프라 + 인수인계 (2주) — Week 29-31 [standard.1.1-7, standard.1.1-10]

> **standard.2 변경**: 1~2주→**2주** 고정.
> - 증분 처리 복잡성 반영: kg-detect-changes Job 구현 3~5일 필요 (R-2)
> - 인수인계 문서 태스크 추가 (R-8)

### 2주 일정 배분

```
Week 29-30 (증분 처리):
  Day 1-3: kg-detect-changes Job 구현 (GCS 탐색 + BigQuery 조회 + 변경 분류)
  Day 4-5: Cloud Scheduler + Workflows 연동
  Day 6-7: Dead-letter 재처리 자동화 + Neo4j 백업 자동화
  Day 8: 증분 파이프라인 3일 연속 정상 동작 테스트 시작

Week 31 (운영 인프라 + 인수인계):
  Day 1-2: 운영 알림 설정 (Cloud Monitoring + Slack)
  Day 3-4: 인수인계 문서 작성 [standard.1.1-10]
  Day 5: Phase 2→운영 Go/No-Go 판정 [standard.1.1-15]
```

### 증분 처리 보완 — [standard.1.1-7]

#### 일일 증분량 추정 근거

```
일일 이력서 유입량 추정:
  - 현재 채용 플랫폼의 일일 이력서 유입량 데이터를 Phase 0-3에서 확인 필요
  - 가정: 월 20,000~30,000건 유입 → 일 ~1,000건 (영업일 기준)
  - 이 수치가 운영 비용($90/월)의 기반

  → Phase 0-3 프로파일링에서 실제 유입량 확인 후 보정:
    - 실제 유입량 < 500/일: 증분 주기를 주 1회로 변경, 비용 $90→$20/월
    - 실제 유입량 > 2,000/일: Batch API 사용 고려, 비용 재산정
```

#### 이력서 업데이트 시 Graph 처리 전략

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
SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com

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

### [standard.1.1-10] 운영 인력 계획 + 인수인계 — 신규

#### 운영 단계 필요 인력

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

#### 인수인계 문서 목차

```
□ 운영 매뉴얼 (Phase 2-6에서 작성):
  1. 시스템 아키텍처 개요
  2. 일일 운영 체크리스트
  3. 알림별 대응 절차 (Runbook)
  4. 증분 처리 파이프라인 구조 + 장애 대응
  5. 크롤링 파이프라인 구조 + 법적 준수 사항
  6. 프롬프트 업데이트 절차 + regression test 실행 방법
  7. 사전(tech/company/role) 업데이트 절차
  8. Neo4j 백업/복원 절차
  9. 비용 모니터링 + Budget Alert 설정
  10. Secret Manager 키 로테이션 절차
```

---

## Phase 2 산출물

```
□ Neo4j Professional 전환 완료
□ 전체 데이터 처리 완료 (450K 이력서 + 10K JD)
□ 크롤링 파이프라인 동작 (홈페이지 + 뉴스 + LLM 추출)
□ 크롤링 법적 검토 완료 + 정책 문서
□ CompanyContext 보강 완료 (fill_rate 0.85+ 목표)
□ 품질 평가 리포트 (Gold Test Set 400건) — 3일 [standard.1.1-5]
□ BigQuery 서빙 인터페이스 확정 — 3일 [standard.1.1-6]
□ Cloud Workflows DAG 구현 + 배포
□ 증분 처리 자동화 (Cloud Scheduler → Workflows)
□ 이력서 업데이트 시 Graph 처리 구현 [standard.1.1-7]
□ 크롤링 30일 주기 자동화
□ Dead-letter 일일 재처리 자동화
□ Neo4j 주간 백업 자동화
□ BigQuery Saved Queries (모니터링용) — [standard.1.1-11] Looker 대체
□ 운영 매뉴얼 (인수인계 문서) [standard.1.1-10]
□ 운영 인력 확정 [standard.1.1-10]
□ Phase 2→운영 Go/No-Go 판정 [standard.1.1-15]
```

---

## Phase 3: 운영 최적화 (별도, 필요 시)

| # | 작업 | 비고 |
|---|---|---|
| 3-1 | scope_type 분류기 학습 (KLUE-BERT) | F1 > 75% 목표 |
| 3-2 | seniority 분류기 학습 | F1 > 80% 목표 |
| 3-3 | Confidence 기반 라우팅 (ML > 0.85 → ML, else → LLM) | LLM 비용 절감 |
| 3-4 | 파이프라인 성능 튜닝 (Cloud Run Job 사양 최적화) | |
| 3-5 | **Prompt 최적화 A/B 테스트** + Cohen's d / Power analysis [standard.1.1-5] | Phase 2에서 이동 |
| 3-6 | **Looker Studio 대시보드 구축** [standard.1.1-11] | Phase 2에서 이동, 운영 인력 5명+ 시 |

### 진입 조건

- Phase 2 품질 평가 완료 (Gold Test Set 기준 최소 기준 충족)
- 운영 데이터 최소 3개월 축적
- LLM 비용이 월 $50 이상으로 비용 절감 ROI 확인
- (Looker Studio) 운영 인력 5명 이상으로 확대 시
