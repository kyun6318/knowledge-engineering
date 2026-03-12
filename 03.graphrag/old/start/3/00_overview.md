# GraphRAG GCP 통합 실행 계획 v2

> **목적**: GCP 환경에서 GraphRAG 시스템 전체를 구축하기 위한 통합 계획.
> API 기능 검증 → Knowledge Graph 구축 → 크롤링 보강 → 운영까지 전 과정을 하나의 흐름으로 통합.
>
> **병합 원본**:
> - `api-test/api-test-3day.md` + `api-test-3day-v3-review.md` — GCP API 기능 검증 (3일)
> - `graphrag/v0/crawling-gcp-plan.md` — 기업 크롤링 파이프라인 (홈페이지/뉴스)
> - `graphrag/v0/create-kg-gcp-plan.md` — KG 구축 GCP 인프라 (v5 기반)
> - `graphrag/v1/01_gcp_architecture.md` — v7 파이프라인 통합 아키텍처
> - `graphrag/v1/02_gcp_execution_plan.md` — Phase별 상세 실행 계획
> - `graphrag/v1/03_gcp_cost_and_monitoring.md` — 비용 추정 + 모니터링
>
> **v2 통합 변경 사항**:
> - [V2-1] API 검증을 별도 3일이 아닌 Phase 0 PoC 내에 내장 (검증 결과가 즉시 의사결정에 반영)
> - [V2-2] v0의 개별 크롤링/KG 계획을 v1 통합 아키텍처에 완전 흡수
> - [V2-3] api-test-3day-v3-review.md의 P0급 패치 5건 반영
> - [V2-4] 단일 GCP 프로젝트 `graphrag-kg`로 통합 (api-test 별도 프로젝트 불필요)
> - [V2-5] Embedding 모델 `text-multilingual-embedding-002` + Gemini `gemini-embedding-001` 비교를 Phase 0에서 확정
> - [V2-6] 크롤링 파이프라인을 Phase 3에서 Phase 2 후반으로 앞당김 (CompanyContext 보강 조기 반영)
> - [V2-7] 비용 추정에 Phase 0 API 검증 비용 포함 + 전체 라이프사이클 비용 일원화
>
> 작성일: 2026-03-08

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| `00_overview.md` (본 문서) | 전체 구조, 아키텍처, 의사결정 포인트 |
| `01_phase0_validation_poc.md` | Phase 0: GCP API 검증 + LLM PoC + 인프라 셋업 |
| `02_phase1_mvp_pipeline.md` | Phase 1: MVP 파이프라인 (전처리→Context→Graph→Mapping) |
| `03_phase2_scale_and_crawl.md` | Phase 2: 전체 데이터 처리 + 크롤링 + 품질 평가 |
| `04_cost_monitoring_ops.md` | 비용 추정 + 모니터링 + 운영 인프라 |

---

## 1. 전체 타임라인

```
Phase 0: 기반 구축 + API 검증 + PoC (4~5주)
  ├─ 0-1: GCP 환경 구성 + API 활성화 (3일)
  ├─ 0-2: Vertex AI API 기능 검증 (3일) — 기존 api-test-3day 내용 내장
  ├─ 0-3: 데이터 탐색 + 프로파일링 (1주)
  ├─ 0-4: LLM 추출 PoC (1~2주)
  ├─ 0-5: 인프라 셋업 — Neo4j, BigQuery, GCS (1주, 0-3과 병행)
  └─ 0-6: Phase 0 의사결정

Phase 1: MVP 파이프라인 (10~12주)
  ├─ 1-1: 전처리 모듈 (2주)
  ├─ 1-2: CompanyContext 파이프라인 (1~2주)
  ├─ 1-3: CandidateContext 파이프라인 (4주)
  ├─ 1-4: Graph 적재 (2주)
  └─ 1-5: MappingFeatures + MAPPED_TO (2주)

Phase 2: 확장 + 크롤링 + 품질 (10~12주)
  ├─ 2-1: 전체 데이터 처리 — 450K 이력서 (2~3주)
  ├─ 2-2: 크롤링 파이프라인 구축 (4주) — v0 크롤링 계획 통합
  │   ├─ 2-2-1: 홈페이지 크롤러 (Playwright)
  │   ├─ 2-2-2: 뉴스 수집기 (네이버 API)
  │   └─ 2-2-3: LLM 추출 (Gemini Flash)
  ├─ 2-3: 크롤링 데이터 → CompanyContext 보강 (1주)
  ├─ 2-4: 품질 평가 + Gold Test Set (1주, 2-1과 병행)
  ├─ 2-5: DS/MLE 서빙 인터페이스 (1주)
  └─ 2-6: 증분 처리 + 운영 인프라 (1~2주)

총 MVP 완성: ~24~29주
첫 동작 데모: ~18주 (Phase 0~1 완료)
전체 데이터 + 크롤링 완료: ~29주
```

---

## 2. GCP 통합 아키텍처

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      GCP Project: graphrag-kg                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [데이터 레이어]                                                              │
│  ├─ GCS: gs://graphrag-kg-data/                                             │
│  │   ├─ raw/resumes/              (이력서 원본 150GB)                         │
│  │   ├─ raw/jds/                  (JD 원본)                                  │
│  │   ├─ reference/                (NICE, 기술사전, 회사사전, 역할사전)           │
│  │   ├─ parsed/                   (파싱 결과 JSON)                           │
│  │   ├─ dedup/                    (중복 제거 결과)                            │
│  │   ├─ contexts/company/         (CompanyContext JSON)                       │
│  │   ├─ contexts/candidate/       (CandidateContext JSON)                    │
│  │   ├─ batch-api/                (Anthropic Batch API 요청/응답)             │
│  │   ├─ crawl/                    (크롤링 원본 — homepage/news/extracted)     │
│  │   ├─ mapping-features/         (MappingFeatures JSON)                     │
│  │   ├─ prompts/                  (프롬프트 버전 관리)                        │
│  │   ├─ dead-letter/              (처리 실패 건)                              │
│  │   ├─ quality/                  (Golden Set, Gold Labels)                  │
│  │   ├─ api-test/                 (Phase 0 API 검증 결과/cost_log)            │
│  │   └─ backups/                  (Context JSON 버전 백업)                    │
│  │                                                                            │
│  ├─ BigQuery: graphrag_kg                                                    │
│  │   ├─ processing_log            (처리 이력/모니터링)                        │
│  │   ├─ chunk_status              (chunk 상태 추적)                          │
│  │   ├─ mapping_features          (서빙 테이블)                               │
│  │   ├─ quality_metrics           (품질 평가 결과)                            │
│  │   ├─ parse_failure_log         (LLM 파싱 실패 모니터링)                   │
│  │   └─ crawl.*                   (크롤링 — company_targets, homepage_pages,  │
│  │                                 news_articles, extracted_fields,           │
│  │                                 company_crawl_summary)                    │
│  │                                                                            │
│  └─ Neo4j AuraDB (외부 관리형)                                               │
│      ├─ Person, Chapter, Organization, Vacancy, Industry, Skill, Role        │
│      ├─ Vector Index (chapter_embedding, vacancy_embedding)                   │
│      └─ MAPPED_TO, REQUIRES_ROLE, BELONGS_TO, IN_INDUSTRY 관계               │
│                                                                              │
│  [컴퓨팅 레이어]                                                              │
│  ├─ Cloud Run Jobs              (배치 파이프라인 — 파싱/Context/Graph/Mapping) │
│  │   └─ Cloud Run Jobs           (크롤링 — homepage-crawler/news-collector)   │
│  ├─ Cloud Functions             (이벤트 트리거, 경량 처리)                    │
│  └─ Compute Engine (GPU)        (시나리오 C: On-premise SLM 전용)           │
│                                                                              │
│  [오케스트레이션]                                                             │
│  ├─ Cloud Workflows             (파이프라인 DAG 관리 — 권장)                 │
│  └─ Cloud Scheduler             (증분 처리 일일 배치 트리거)                  │
│                                                                              │
│  [LLM API (외부)]                                                            │
│  ├─ Anthropic Batch API         (Claude Haiku 4.5 — KG 추출 Primary)         │
│  ├─ Anthropic API               (Claude Sonnet 4.6 — Fallback/PoC)           │
│  └─ Vertex AI Gemini            (크롤링 LLM 추출 + Phase 0 API 검증)        │
│                                                                              │
│  [Embedding API]                                                             │
│  ├─ Vertex AI                   (text-multilingual-embedding-002 — 768d)     │
│  └─ Vertex AI Gemini            (gemini-embedding-001 — Phase 0 비교 후 확정) │
│                                                                              │
│  [모니터링]                                                                   │
│  ├─ Cloud Monitoring            (인프라 메트릭)                               │
│  ├─ Cloud Logging               (애플리케이션 로그)                           │
│  └─ BigQuery + Looker Studio    (커스텀 대시보드)                             │
│                                                                              │
│  [보안]                                                                       │
│  ├─ Secret Manager              (Anthropic, Neo4j, 네이버, OpenAI API 키)    │
│  ├─ IAM                         (서비스 계정 최소 권한)                       │
│  └─ VPC Service Controls        (PII 유출 방지, 선택적)                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. GCP 서비스 매핑 (통합)

### 3.1 파이프라인별 GCP 서비스

| 파이프라인 | GCP 서비스 | 선택 근거 |
|---|---|---|
| **Phase 0: API 검증** | Cloud Shell / 로컬 Python | 3일 단발 테스트, 인프라 불필요 |
| **이력서 파싱 (전처리)** | Cloud Run Jobs | CPU 집약, Task 단위 병렬 (최대 10,000 tasks) |
| **이력서 중복 제거** | Cloud Run Jobs | 메모리 집약 (SimHash 전체 비교) |
| **CompanyContext 생성** | Cloud Run Jobs + Anthropic Batch API | 10K JD 규모, Batch 50% 할인 |
| **CandidateContext 생성** | Cloud Run Jobs + Anthropic Batch API | 500K 이력서, 핵심 비용 포인트 |
| **Graph 적재** | Cloud Run Jobs | Neo4j AuraDB 연결, 트랜잭션 배치 |
| **Embedding 생성** | Cloud Run Jobs + Vertex AI Embedding | text-multilingual-embedding-002 |
| **MappingFeatures 계산** | Cloud Run Jobs | Rule + Embedding cosine |
| **홈페이지 크롤링** | Cloud Run Jobs (Playwright) | headless Chrome, 타임아웃 1시간 |
| **뉴스 수집** | Cloud Run Jobs | 네이버 API + 본문 크롤링 (funding/org_change) |
| **크롤링 LLM 추출** | Cloud Run Jobs + Gemini API | gemini-2.0-flash, 정보 추출 |
| **증분 처리** | Cloud Functions + Cloud Scheduler | 일일 트리거, 경량 |
| **Dead-Letter 재처리** | Cloud Scheduler + Cloud Run Jobs | 일 1회 자동 재시도 |

### 3.2 Pipeline DAG 의존성

```
[Phase 0] API 검증 + PoC → 의사결정
                │
[Phase 1]       ▼
Pipeline A (CompanyContext)  ──┐
                               ├──→ C (Graph 적재) ──→ D (Embedding+Mapping) ──→ E (서빙)
Pipeline B (CandidateContext) ─┘
                │
[Phase 2]       ▼
전체 데이터 처리 (450 chunks) ──→ 품질 평가
                │
크롤링 파이프라인 (병행) ──→ CompanyContext 보강 ──→ Graph 업데이트
```

---

## 4. 통합 환경 구성

```
프로젝트: graphrag-kg (단일 프로젝트)
리전: asia-northeast3 (서울) — 데이터 주권, 레이턴시
Vertex AI 리전: us-central1 — Gemini API + Embedding API
Neo4j AuraDB: asia-northeast1 (도쿄) — 서울 미지원, 가장 가까운 리전

API 활성화 필요:
  - Vertex AI API
  - Cloud Run API
  - Cloud Workflows API
  - Cloud Scheduler API
  - Cloud Build API
  - Cloud Storage API
  - BigQuery API
  - Secret Manager API
  - Artifact Registry API
  - Cloud Monitoring API
  - Cloud Logging API
  - Cloud Functions API
  - Document AI API (리전: us) — Phase 0 비교 테스트용
  - Discovery Engine API (global) — Phase 0 비교 테스트용 (Vertex AI Search)

SDK (통합):
  # LLM / Embedding / RAG
  google-genai >= 1.5.0
  google-cloud-aiplatform >= 1.74.0
  anthropic >= 0.39.0

  # 인프라
  google-cloud-bigquery >= 3.20.0
  google-cloud-storage >= 2.14.0
  google-cloud-secret-manager >= 2.18.0

  # Phase 0 API 검증
  google-cloud-documentai >= 2.29.0
  google-cloud-discoveryengine >= 0.13.0
  pypdf >= 4.0.0

  # KG 파이프라인
  neo4j >= 5.15.0
  pymupdf >= 1.23.0
  python-docx >= 1.1.0
  pydantic >= 2.5.0
  simhash >= 2.1.2
  json-repair >= 0.28.0

  # 크롤링
  playwright >= 1.40.0
  readability-lxml >= 0.8.1
  beautifulsoup4 >= 4.12.0
  requests >= 2.31.0

Budget Alert:
  Phase 0: $500 (경고), $800 (강제 중단)
  Phase 1-2: $1,500 (경고), $2,500 (강제 중단)
  운영: 월 $300 (경고), $500 (강제 중단)
```

---

## 5. GCS 버킷 통합 구조

```yaml
gs://graphrag-kg-data/
├── raw/
│   ├── resumes/                    # 이력서 원본 (150GB)
│   │   ├── pdf/
│   │   ├── docx/
│   │   └── hwp/
│   └── jds/                        # JD 원본
│       └── *.json
│
├── reference/
│   ├── nice/                        # NICE 기업 정보 스냅샷
│   │   └── nice_companies.parquet
│   ├── nice_industry_codes.json     # KSIC 업종 코드 마스터
│   ├── tech_dictionary.json         # 기술 사전 (2,000+ 기술명)
│   ├── company_alias.json           # 회사명 정규화 사전
│   └── role_alias.json              # 직무명 정규화 사전
│
├── parsed/
│   ├── resumes/
│   │   └── {candidate_id}.json
│   └── jds/
│       └── {job_id}.json
│
├── dedup/
│   ├── canonical_list.json
│   └── review_queue.json
│
├── contexts/
│   ├── company/
│   │   └── {job_id}/
│   │       ├── v1.json
│   │       └── latest.json
│   └── candidate/
│       └── {candidate_id}/
│           ├── v1.json
│           └── latest.json
│
├── batch-api/
│   ├── requests/
│   │   └── batch_{chunk_id}.jsonl
│   └── responses/
│       └── batch_{chunk_id}_result.jsonl
│
├── crawl/                            # 크롤링 데이터 (Phase 2)
│   ├── homepage/
│   │   └── {company_id}/
│   │       └── {crawl_date}/
│   │           ├── raw/              # 원본 HTML
│   │           ├── text/             # 정제된 텍스트
│   │           └── meta.json
│   ├── news/
│   │   └── {company_id}/
│   │       └── {crawl_date}/
│   │           ├── articles/
│   │           └── meta.json
│   └── extracted/
│       └── {company_id}/
│           └── {crawl_date}.json     # LLM 추출 결과
│
├── mapping-features/
│   └── {job_id}/
│       └── top500.json
│
├── prompts/
│   ├── experience_extract_v1.txt
│   ├── career_level_v1.txt
│   ├── vacancy_role_v1.txt
│   ├── structural_tension_v1.txt
│   ├── homepage_extract_v1.txt       # 크롤링용
│   ├── news_funding_extract_v1.txt
│   ├── news_org_extract_v1.txt
│   └── CHANGELOG.md
│
├── api-test/                         # Phase 0 API 검증 결과
│   ├── results/
│   │   └── cost_log.jsonl
│   ├── datasets/
│   │   ├── DS-RAG-DOCS/
│   │   ├── DS-PDF-SAMPLE/
│   │   ├── DS-LLM-EVAL/
│   │   ├── DS-EMBED-SAMPLE/
│   │   └── DS-NER-EVAL/
│   └── docai-output/
│
├── dead-letter/
│   └── {pipeline}/{item_id}.json
│
├── quality/
│   ├── golden_set/                   # Phase 0 PoC 50건 (고정)
│   └── gold_labels/                  # Phase 2 전문가 검수 400건
│
└── backups/
    └── {date}/
```

---

## 6. 의사결정 포인트 요약

| 시점 | 의사결정 | 입력 데이터 | GCP 영향 |
|------|---------|-----------|---------|
| Phase 0-2 완료 | **Embedding 모델 확정** | gemini-embedding-001 vs text-multilingual-embedding-002 비교 | Vertex AI 모델/리전 설정 |
| Phase 0-2 완료 | **텍스트 추출 방법 확정** | Document AI vs Gemini 멀티모달 CER/WER 비교 | Phase 1에서 사용할 파이프라인 방법 |
| Phase 0-4 완료 | **LLM 모델 선택** | Claude Haiku vs Sonnet vs Gemini 품질·비용 비교 | Batch API 모델 설정 |
| Phase 0-4 완료 | **PII 전략 확정** | 법무 결론 + 마스킹 영향 테스트 | API (Cloud Run) vs On-premise (GPU) |
| Phase 0-6 | **오케스트레이션 도구** | DE 역량 + 통합 요구 | Cloud Workflows vs Prefect |
| Phase 0-6 | **Graph DB 플랜** | 예상 노드 수 | Free → Professional 전환 시점 |
| Pre-Phase 0 | **NICE DB 접근** | 계약 상태 | Cloud Functions 구현 범위 |
| Phase 2 시작 | **크롤링 인프라** | Phase 0 Gemini 검증 결과 | Gemini Flash 모델 + Cloud Run Jobs |
| Phase 2 완료 | **운영 모드** | 전체 품질 결과 | Cloud Scheduler 증분 주기 |

---

## 7. v0/v1 대비 v2 주요 변경 요약

| 항목 | v0/v1 | v2 |
|------|-------|-----|
| API 검증 | 별도 프로젝트 `ml-api-test-vertex`에서 3일 독립 수행 | Phase 0에 내장, 동일 프로젝트 `graphrag-kg` |
| 크롤링 | Phase 3 (Week 22-29)에 후순위 | Phase 2 후반 (Week 18-22)으로 앞당김 |
| GCP 프로젝트 | api-test / create-kg / crawl 혼재 | `graphrag-kg` 단일 프로젝트 |
| Embedding 비교 | OpenAI text-embedding-3-small 포함 | Vertex AI 네이티브 2종으로 단순화 |
| 비용 추적 | 테스트별 개별 추적 | BigQuery `processing_log` 통합 |
| api-test review P0 패치 | 미반영 | 5건 모두 반영 (01_phase0 문서) |
| 크롤링 LLM | Gemini 2.0 Flash | Phase 0 검증 결과에 따라 확정 |
| 문서 구조 | 8개 파일 분산 | 5개 파일 통합 (Phase 중심) |
