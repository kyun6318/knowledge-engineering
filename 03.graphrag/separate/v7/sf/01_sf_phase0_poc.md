> **S&F 담당 범위**: GCP 환경, DB 프로파일링, LLM PoC, Embedding 검증, 크롤링 분석
> 

---

## Week 0: 사전 준비

[] Anthropic Batch API quota/Tier 확인

[] Gemini Flash Batch 대안 사전 검증

[] 법무 PII 검토 요청 -> 마스킹 적용으로 우선 진행

[] 크롤링 대상 사이트 법적 검토 요청

[] 크롤링 대상 사이트 DOM 구조 사전 조사

[] 기존 이력서 DB 샘플 100건 확보

[] Career 4+ 이력서 비율 사전 확인 (v12 M1)

---

## Week 1: Phase 0

### Day 1-2: GCP 환경 구성

> 서비스 계정 4개, API 활성화, GCS, BigQuery
> 

### Day 2: BigQuery 테이블 생성

> resume_raw, resume_processed, processing_log, batch_tracking, quality_metrics
> 

```sql
-- 1. 크롤링 수집 이력서 (core/1 최초 정의)
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

-- 2. 전처리 완료 이력서 (core/1 최초 정의)
CREATE TABLE graphrag_kg.resume_processed (
  resume_id STRING NOT NULL,
  source_resume_id STRING NOT NULL,
  masked_text STRING,
  career_blocks JSON,
  dedup_hash STRING,
  is_duplicate BOOLEAN DEFAULT FALSE,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- 3. 처리 이력 checkpoint (core/1 최초 정의)
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

-- 4. Batch API 추적 (core/1 최초 정의 및 core/5 업데이트 사항 반영)
CREATE TABLE graphrag_kg.batch_tracking (
  batch_id STRING NOT NULL,
  chunk_id STRING NOT NULL,
  status STRING,
  submitted_at TIMESTAMP,
  completed_at TIMESTAMP,
  result_collected BOOLEAN DEFAULT FALSE,
  retry_count INT64 DEFAULT 0,
  gcs_request_path STRING,
  gcs_response_path STRING,
  api_provider STRING DEFAULT 'anthropic'
);

-- 5. 자동 품질 메트릭 테이블 (core/2 단계에서 parse_failure_log 대신 도입됨)
CREATE TABLE graphrag_kg.quality_metrics (
  id STRING NOT NULL,
  pipeline STRING NOT NULL,
  metric_name STRING NOT NULL,
  metric_value FLOAT64,
  sample_size INT64,
  confidence_interval STRING,
  measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

### Day 3-5: 크롤링 대상 사이트 구조 분석 (법무 허용 시에만)

### Day 1-2: DB 프로파일링 + 일일 유입량 확인 (온톨로지 크롤링: N4)

```sql
-- 온톨로지 크롤링:: 일일 유입량 확인
SELECT DATE(created_at) AS dt, COUNT(*) AS daily_count
FROM resume_hub.career
WHERE created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY dt ORDER BY dt DESC;

-- Career 수 분포 (적응형 호출 검증)
SELECT
  CASE WHEN career_count <= 3 THEN '1-3 (1-pass)' ELSE '4+ (N+1 pass)' END AS strategy,
  COUNT(*) AS person_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM (SELECT person_id, COUNT(*) AS career_count FROM resume_hub.career GROUP BY person_id)
GROUP BY strategy;
```

### Day 2-3: LLM 추출 PoC 20건

PoC 구성 (v12 M1 적응형 호출 검증):
- v12 M1
- 이력서 기재 경력 개수에 따른 Adaptive Invocation
- `knowledge_graph/01_extraction_pipeline.md`
- `knowledge_graph/03_prompt_design.md`
- Career 1~3 이력서: 15건 (1-pass)
- Career 4+ 이력서: 5건 (N+1 pass)
- 품질 비교: 1-pass vs N+1 pass (Career 3개 건에서 동시 테스트)

`knowledge_graph/03_prompt_design.md` 프롬프트 적용:
- S5: structural_tensions, work_style_signals 제외
- scope_type 분류 가이드라인 (§2.4)
- outcomes 4+1 유형 (§2.5)
- situational_signals 14개 라벨 (§2.6)

### Day 4-5: Embedding 모델 확정 + Batch API 실측

---

## Phase 0 산출물 (S&F)

### Must

[] GCP 환경 (API, 서비스 계정 4개, GCS, BigQuery)

[] BigQuery 테이블 5개 + quality_metrics + batch_tracking.api_provider

[] DB 프로파일 리포트 (100건) + 일일 유입량 (N4) + Career 분포 (M1)

[] LLM 추출 PoC 결과 (20건) + 적응형 호출 비교 (M1)

[] Embedding 모델 확정 (text-embedding-005, 768d)

[] Batch API 응답 시간 실측

[] Gemini Flash Batch 대안 테스트 -> provider 추상화 판단 (N5)

### Should

[] 크롤링 대상 사이트 구조 분석 (법무 허용 시)

[] 이력서 파일 형식 분포 조사 (Phase 2 사전)

[] HWP 파싱 3방법 조사 (Phase 2 사전)

[] NICE DB 접근 계약 상태 확인 (Phase 3 사전)

> **-> 산출물 A**: PoC 결과 20건 + 리포트 -> **수동** Go/No-Go -> GraphRAG 에 전달
>