# 모델 선정 및 GCP 인프라 v10

> 작성일: 2026-03-11 | 기준: 온톨로지 v19, GCP ML Pipeline, GraphRAG Core v2
>
> v9 03_model_candidates_and_costs.md + GCP 인프라 설계 통합

---

## 1. LLM 모델 후보

### 1.1 v1 MVP 추천

| 모델 | 입력/출력 단가 (1M tok) | Batch 단가 | 품질 | 용도 |
|------|----------------------|-----------|------|------|
| **Claude Haiku 4.5** (1순위) | $0.80 / $4.00 | $0.40 / $2.00 | 중상 | CandidateContext, CompanyContext 추출 |
| Claude Sonnet 4.6 (폴백) | $3.00 / $15.00 | $1.50 / $7.50 | 상 | Haiku 품질 <70% 시 전환 |
| Gemini 2.0 Flash (대안) | $0.10 / $0.40 | $0.05 / $0.20 | 미검증 | 최저 비용 시나리오 |
| Gemini 2.0 Flash (크롤링) | $0.10 / $0.40 | - | 중 | 크롤링 필드 추출 (T3/T4) |

**Batch API**: 50% 할인, 24시간 레이턴시 허용 (컨텍스트 생성은 비실시간)

### 1.2 Phase 0 모델 선정 기준

| 기준 | Haiku 통과 | Sonnet 전환 (A') |
|------|-----------|-----------------|
| scope_type 정확도 | ≥70% | <70% |
| outcomes F1 | ≥50% | <50% |
| situational_signals F1 | ≥45% | <45% |
| JSON 파싱 성공률 | ≥95% | <90% |

---

## 2. Embedding 모델

### 2.1 v10 표준: text-embedding-005 (변경)

| 항목 | v9 (text-multilingual-embedding-002) | v10 (text-embedding-005) |
|------|--------------------------------------|--------------------------|
| 차원 | 768d | **768d** |
| 단가 | $0.0065/1M tok | **$0.0001/1K chars** |
| 한국어 | 다국어 지원 | 다국어 지원 (Phase 0 검증) |
| 플랫폼 | Vertex AI | **Vertex AI** |
| 선정 이유 | v9 시점 추천 | **GraphRAG v2 표준화, 최신 모델, 비용 효율** |

**Phase 0 검증**: 한국어 분별력 "excellent" 기준 충족 여부 확인
- 실패 시 폴백: Cohere embed-multilingual-v3.0 ($0.10/1M tok) 또는 text-multilingual-embedding-002

### 2.2 임베딩 비용

| 용도 | 대상 | 수량 | 비용 |
|------|------|------|------|
| Chapter 벡터 | 1.8M chapters × 200 tok avg | 360M tok | ~$25 |
| Vacancy 벡터 | 10K vacancies × 500 tok avg | 5M tok | ~$0.5 |
| 3-Tier canonical | ~3K canonicals × 50 tok avg | 150K tok | ~$0.01 |
| **임베딩 소계** | | | **~$25.5** |

---

## 3. Graph DB

### 3.1 Neo4j AuraDB 마이그레이션 경로

| Phase | 티어 | 노드 한도 | 월 비용 | 용도 |
|-------|------|----------|---------|------|
| 0-1 | **Free** | 200K | $0 | PoC + 1,000건 MVP |
| 2+ | **Professional** | 800K+ | $100-200 | 전체 데이터 (8M 노드) |
| 운영 | Professional+ | 확장 | $200-500 | 증분 처리 + 운영 |

**리전**: asia-northeast1 (도쿄) — 서울 미지원
**Vector Index**: 768d cosine (text-embedding-005 정합)
**APOC**: 지원 여부 Phase 0 확인

### 3.2 BigQuery

| 테이블 | 용도 | 예상 크기 |
|--------|------|----------|
| kg.mapping_features | 매칭 점수 서빙 | ~5M rows |
| kg.quality_metrics | 자동 품질 메트릭 | ~10K rows |
| kg.dead_letter | 오류 추적 | ~50K rows |
| kg.batch_log | 배치 실행 로그 | ~10K rows |
| kg.crawl_raw_data | 크롤링 원본 | ~100K rows |
| kg.crawl_extracted_fields | 크롤링 추출 | ~50K rows |

---

## 4. GCP 인프라 아키텍처

### 4.1 서비스 계정 (3개 분리, 최소 권한 원칙)

| 계정 | 역할 | 접근 범위 |
|------|------|----------|
| **kg-crawling** | storage.objectCreator, bigquery.dataEditor, secretmanager.secretAccessor | GCS 쓰기, BQ 쓰기, 크롤링 API 키 |
| **kg-processing** | storage.objectViewer/Creator, bigquery.dataEditor, aiplatform.user, secretmanager.secretAccessor | GCS 읽기/쓰기, BQ 쓰기, Vertex AI, LLM API 키 |
| **kg-loading** | storage.objectViewer, bigquery.dataViewer, secretmanager.secretAccessor | GCS 읽기, BQ 읽기, **Neo4j 접근 전용** |

### 4.2 리전 설정

| 서비스 | 리전 | 이유 |
|--------|------|------|
| GCP 프로젝트 | asia-northeast3 (서울) | 데이터 주권, 레이턴시 |
| Vertex AI | us-central1 | API 가용성, 최신 모델 |
| Neo4j AuraDB | asia-northeast1 (도쿄) | 서울 미지원, 최근접 |
| Cloud Run | asia-northeast3 | 데이터 근접성 |
| BigQuery | asia-northeast3 | 데이터 근접성 |

### 4.3 Cloud Run Jobs 정의

| Job 이름 | 역할 | 병렬 | 서비스 계정 |
|----------|------|------|-----------|
| kg-parse | 파일 파싱 (PDF/DOCX/HWP) | 50 | kg-processing |
| kg-preprocess | 정규화, PII 마스킹, 블록 분리 | 50 | kg-processing |
| kg-extract | LLM 추출 (Batch API 제출/수집) | 10 | kg-processing |
| kg-graph-load | Neo4j UNWIND 적재 | **≤5** | kg-loading |
| kg-mapping | MappingFeatures 계산 | 10 | kg-processing |
| kg-crawl | 홈페이지/뉴스 크롤링 | 10 | kg-crawling |
| kg-crawl-extract | 크롤링 LLM 추출 | 5 | kg-crawling |

### 4.4 Cloud Run Service

| Service 이름 | 역할 | 인스턴스 | 서비스 계정 |
|-------------|------|---------|-----------|
| kg-api | Agent Serving API (FastAPI) | 1-5 (auto-scale) | kg-loading |

### 4.5 Cloud Workflows

```yaml
# kg-pipeline-full (전체 배치)
steps:
  - preprocess: Cloud Run Job kg-preprocess
  - extract: Cloud Run Job kg-extract
  - wait_batch: Batch API 폴링 (30분 간격)
  - graph_load: Cloud Run Job kg-graph-load
  - mapping: Cloud Run Job kg-mapping
  - quality_check: BigQuery quality_metrics 업데이트
  - notify: Slack 알림

# kg-pipeline-incremental (증분)
steps:
  - detect_changes: BigQuery updated_at 기반 변경 감지
  - preprocess: 변경분만 처리
  - extract: 변경분만 LLM 추출
  - graph_load: MERGE (upsert)
  - mapping: 영향받는 매칭 쌍 재계산
```

### 4.6 Cloud Scheduler

| Job 이름 | Cron | 대상 |
|----------|------|------|
| kg-incremental-daily | `0 2 * * *` | kg-pipeline-incremental |
| kg-dead-letter-daily | `0 4 * * *` | dead-letter 재처리 |
| crawl-monthly | `0 0 1 * *` | kg-crawl (1,000 기업) |
| neo4j-weekly-backup | `0 3 * * 0` | Neo4j 백업 |

---

## 5. ML Knowledge Distillation (Phase 2, 선택적)

### 5.1 후보 모델

| 모델 | 파라미터 | 추론 속도 | 학습 비용 |
|------|---------|----------|----------|
| **KLUE-BERT-base** (추천) | 110M | ~200 docs/sec | ~$10/epoch |
| DeBERTa-v3-base-kor | 184M | ~120 docs/sec | ~$15/epoch |

### 5.2 ROI 판단 기준

Phase 2 평가 결과에 따라 결정:
- LLM 비용 20-30% 절감 가능 시 진행
- scope_type, outcomes 등 분류 가능 필드 대상
- 증분 처리 비용 절감이 주 목적

---

## 6. 비용 시나리오 비교

### 6.1 v9 → v10 비용 변화

| 항목 | v9 | v10 | 변화 | 이유 |
|------|-----|-----|------|------|
| LLM (Batch) | $485 | $585 | +$100 | 파일 이력서 100K 추가 |
| 임베딩 | $37.5 | $25.5 | -$12 | text-embedding-005 단가 인하 |
| Neo4j | $1,200 | $600-1,200 | 동일 | |
| Cloud Run | - | $384 | +$384 | GCP 인프라 신규 |
| BigQuery | - | $60 | +$60 | GCP 인프라 신규 |
| 기타 GCP | - | $60 | +$60 | Scheduler, Workflows 등 |
| Gold Label | $5,840 | $5,840 | 동일 | |
| **총액** | ~$8,899 | **$7,567-10,507** | | 시나리오별 |

### 6.2 월간 운영 비용 (Phase 4 이후)

| 항목 | 월 비용 |
|------|---------|
| Neo4j Professional | $100-200 |
| Cloud Run (Jobs + Service) | $64 |
| BigQuery | $10 |
| GCS | $6 |
| Cloud Scheduler + Workflows | $3 |
| Secret Manager | $1 |
| 크롤링 (Gemini Flash) | $107 |
| **월 소계** | **$291-391** |
| **연간 소계** | **$3,492-4,692** |
