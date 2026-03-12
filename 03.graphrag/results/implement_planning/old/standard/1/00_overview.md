# GraphRAG GCP 통합 실행 계획 standard.1

> **목적**: GCP 환경에서 GraphRAG 시스템 전체를 구축하기 위한 통합 계획.
> API 기능 검증 → Knowledge Graph 구축 → 크롤링 보강 → 운영까지 전 과정을 하나의 흐름으로 통합.
>
> **standard.1 변경 사항** (v2 리뷰 R-1 ~ R-16 반영):
> - [standard.2] Phase 0에서 VAS/RAG Engine 검증 제거 — 파이프라인에서 미사용 (R-6)
> - [standard.1-2] Phase 0-4에 HWP 파싱 품질 PoC 10건 추가 (R-1)
> - [standard.1-3] Neo4j Free→Professional 전환 시점/방법/마이그레이션 명시 (R-2)
> - [standard.1-4] Anthropic Batch API quota/rate limit 명시, 처리 시간 재계산 (R-3)
> - [standard.1-5] 파이프라인 레벨 checkpoint/재시작 전략 추가 (R-4)
> - [standard.1-6] Phase 1에 테스트 인프라 + regression test 추가 (R-5)
> - [standard.1-7] Phase 2-1 타임라인 3~4주로 조정 (R-7)
> - [standard.1-8] Pre-Phase 0에 법무 PII 검토 추가 (R-8)
> - [standard.1-9] Pre-Phase 2에 크롤링 법적 검토 추가 (R-9)
> - [standard.20] GCS Versioning + Neo4j 백업 절차 기술 (R-10)
> - [standard.21] 한국어 토큰 기준 Batch API 비용 재계산 (R-11)
> - [standard.22] Embedding 비교 대상 모델명 전 문서 통일 (R-12)
> - [standard.23] Phase 2 크롤링/전체처리 직렬화 옵션 반영 (R-13)
> - [standard.24] Cloud Workflows를 Phase 2로 연기, Phase 1은 Makefile (R-14)
> - [standard.25] ML Knowledge Distillation을 Phase 3(운영 최적화)로 분리 (R-15)
> - [standard.26] Embedding egress 비용 계산 추가 (R-16)
>
> 작성일: 2026-03-08
> **standard.1 리뷰 반영** (2026-03-08): standard.1 리뷰 권장사항 R-1~R-12를 각 Phase 문서에 인라인 반영.
> 계획 구조/타임라인 변경 없이 실행 시 누락 방지 목적의 보완.

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
  ├─ 0-2: Vertex AI API 기능 검증 (2일) — VAS/RAG Engine 제거로 단축 [standard.2]
  ├─ 0-3: 데이터 탐색 + 프로파일링 (1주)
  ├─ 0-4: LLM 추출 PoC + HWP 파싱 PoC (1~2주) — [standard.1-2]
  ├─ 0-5: 인프라 셋업 — Neo4j, BigQuery, GCS (1주, 0-3과 병행)
  └─ 0-6: Phase 0 의사결정

Phase 1: MVP 파이프라인 (10~12주)
  ├─ 1-1: 전처리 모듈 (2주)
  ├─ 1-2: CompanyContext 파이프라인 (1~2주)
  ├─ 1-3: CandidateContext 파이프라인 (4주)
  ├─ 1-4: Graph 적재 (2주)
  ├─ 1-5: MappingFeatures + MAPPED_TO (2주)
  └─ 1-6: 테스트 인프라 + Regression Test (1주, 1-5와 병행) — [standard.1-6]

Phase 2: 확장 + 크롤링 + 품질 (12~16주) — [standard.1-7, standard.23]
  ├─ 2-0: Neo4j Professional 전환 (1일) — [standard.1-3] 필수, Phase 2 시작 전
  ├─ 2-1: 전체 데이터 처리 — 450K 이력서 (3~4주) — [standard.1-7]
  ├─ 2-2: 품질 평가 + Gold Test Set (1주, 2-1과 병행)
  ├─ 2-3: 크롤링 파이프라인 구축 (4주) — 2-1 이후 직렬 [standard.23]
  │   ├─ 2-3-1: 홈페이지 크롤러 (Playwright)
  │   ├─ 2-3-2: 뉴스 수집기 (네이버 API)
  │   └─ 2-3-3: LLM 추출 (Gemini Flash)
  ├─ 2-4: 크롤링 데이터 → CompanyContext 보강 (1주)
  ├─ 2-5: DS/MLE 서빙 인터페이스 (1주)
  └─ 2-6: 증분 처리 + 운영 인프라 (1~2주)

Phase 3: 운영 최적화 (별도, 필요 시) — [standard.25]
  ├─ 3-1: ML Knowledge Distillation (scope_type, seniority)
  ├─ 3-2: LLM 비용 최적화 (Confidence 기반 ML/LLM 라우팅)
  └─ 3-3: 파이프라인 성능 튜닝

총 MVP 완성: ~26~33주
첫 동작 데모: ~18주 (Phase 0~1 완료)
전체 데이터 + 크롤링 완료: ~33주
```

### v2 → standard.1 타임라인 변경 요약

| 항목 | v2 | standard.1 | 변경 이유 |
|------|----|----|-----------|
| Phase 0-2 API 검증 | 3일 | 2일 | VAS/RAG Engine 제거 (R-6) |
| Phase 2-1 전체 처리 | 2~3주 | 3~4주 | Batch API 현실적 처리 시간 (R-7) |
| Phase 2 크롤링 | 전체 처리와 병행 | 전체 처리 후 직렬 | 인력 부족 리스크 해소 (R-13) |
| Phase 2 전체 | 10~12주 | 12~16주 | 직렬화 + 여유 확보 |
| ML Distillation | Phase 2-6 | Phase 3 분리 | 시기상조 (R-15) |
| 오케스트레이션 | Phase 1 Cloud Workflows | Phase 1 Makefile, Phase 2 Workflows | 과설계 방지 (R-14) |

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
│  │   └─ backups/                  (Neo4j export + Context 백업) — [standard.20]    │
│  │                                                                            │
│  ├─ BigQuery: graphrag_kg                                                    │
│  │   ├─ processing_log            (처리 이력/모니터링 + checkpoint) — [standard.1-5]  │
│  │   ├─ chunk_status              (chunk 상태 추적)                          │
│  │   ├─ batch_tracking            (Batch API batch_id 추적) — [standard.1-5]        │
│  │   ├─ mapping_features          (서빙 테이블)                               │
│  │   ├─ quality_metrics           (품질 평가 결과)                            │
│  │   ├─ parse_failure_log         (LLM 파싱 실패 모니터링)                   │
│  │   └─ crawl.*                   (크롤링 — company_targets, homepage_pages,  │
│  │                                 news_articles, extracted_fields,           │
│  │                                 company_crawl_summary)                    │
│  │                                                                            │
│  └─ Neo4j AuraDB                                                             │
│      ├─ Free (Phase 0~1) → Professional (Phase 2 시작 전 필수) — [standard.1-3]      │
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
│  ├─ Makefile / bash              (Phase 1 수동 오케스트레이션) — [standard.24]      │
│  ├─ Cloud Workflows             (Phase 2+ DAG 관리) — [standard.24]              │
│  └─ Cloud Scheduler             (증분 처리 일일 배치 트리거)                  │
│                                                                              │
│  [LLM API (외부)]                                                            │
│  ├─ Anthropic Batch API         (Claude Haiku 4.5 — KG 추출 Primary)         │
│  ├─ Anthropic API               (Claude Sonnet 4.6 — Fallback/PoC)           │
│  └─ Vertex AI Gemini            (크롤링 LLM 추출 + Phase 0 API 검증)        │
│                                                                              │
│  [Embedding API]                                                             │
│  ├─ Vertex AI                   (text-embedding-005 — 768d) — [standard.22]       │
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
| **Phase 0: API 검증** | Cloud Shell / 로컬 Python | 2일 단발 테스트, 인프라 불필요 |
| **이력서 파싱 (전처리)** | Cloud Run Jobs | CPU 집약, Task 단위 병렬 (최대 10,000 tasks) |
| **이력서 중복 제거** | Cloud Run Jobs | 메모리 집약 (SimHash 전체 비교) |
| **CompanyContext 생성** | Cloud Run Jobs + Anthropic Batch API | 10K JD 규모, Batch 50% 할인 |
| **CandidateContext 생성** | Cloud Run Jobs + Anthropic Batch API | 500K 이력서, 핵심 비용 포인트 |
| **Graph 적재** | Cloud Run Jobs | Neo4j AuraDB 연결, 트랜잭션 배치 |
| **Embedding 생성** | Cloud Run Jobs + Vertex AI Embedding | text-embedding-005 [standard.22] |
| **MappingFeatures 계산** | Cloud Run Jobs | Rule + Embedding cosine |
| **홈페이지 크롤링** | Cloud Run Jobs (Playwright) | headless Chrome, 타임아웃 1시간 |
| **뉴스 수집** | Cloud Run Jobs | 네이버 API + 본문 크롤링 (funding/org_change) |
| **크롤링 LLM 추출** | Cloud Run Jobs + Gemini API | Gemini Flash (Phase 0 확정 버전 snapshot 고정, 예: `gemini-2.5-flash-001`) [R-11] |
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
Neo4j Professional 전환 (필수) — [standard.1-3]
                │
전체 데이터 처리 (450 chunks, 3~4주) ──→ 품질 평가
                │                           (직렬) — [standard.23]
                ▼
크롤링 파이프라인 (4주) ──→ CompanyContext 보강 ──→ Graph 업데이트
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
  - Cloud Workflows API          (Phase 2부터 사용) — [standard.24]
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

SDK (통합):
  # LLM / Embedding
  google-genai >= 1.5.0
  google-cloud-aiplatform >= 1.74.0
  anthropic >= 0.39.0

  # 인프라
  google-cloud-bigquery >= 3.20.0
  google-cloud-storage >= 2.14.0
  google-cloud-secret-manager >= 2.18.0

  # Phase 0 API 검증
  google-cloud-documentai >= 2.29.0
  pypdf >= 4.0.0

  # KG 파이프라인
  neo4j >= 5.15.0
  pymupdf >= 1.23.0
  python-docx >= 1.1.0
  pydantic >= 2.5.0
  simhash >= 2.1.2
  json-repair >= 0.28.0

  # HWP 파싱 PoC — [standard.1-2]
  pyhwp >= 0.1b12
  # + LibreOffice (Docker 설치)
  # + Gemini 멀티모달 (별도 SDK 불필요)

  # 크롤링
  playwright >= 1.40.0
  readability-lxml >= 0.8.1
  beautifulsoup4 >= 4.12.0
  requests >= 2.31.0

  # 테스트 — [standard.1-6]
  pytest >= 8.0.0
  pytest-cov >= 4.1.0
  deepdiff >= 6.7.0

Budget Alert:
  Phase 0: $500 (경고), $800 (강제 중단)
  Phase 1-2: $2,000 (경고), $3,500 (강제 중단) — [standard.21] 한국어 토큰 보정
  운영: 월 $300 (경고), $500 (강제 중단)
```

---

## 5. GCS 버킷 통합 구조

```yaml
gs://graphrag-kg-data/
├── raw/
│   ├── resumes/                    # 이력서 원본 (150GB)
│   │   ├── dev/                    # [R-10] Phase 0~1 테스트 데이터
│   │   │   ├── pdf/
│   │   │   ├── docx/
│   │   │   └── hwp/
│   │   └── prod/                   # [R-10] Phase 2 프로덕션 데이터
│   │       ├── pdf/
│   │       ├── docx/
│   │       └── hwp/
│   └── jds/                        # JD 원본
│       ├── dev/                    # [R-10]
│       └── prod/                   # [R-10]
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
│   │   └── {company_id}/{crawl_date}/
│   ├── news/
│   │   └── {company_id}/{crawl_date}/
│   └── extracted/
│       └── {company_id}/{crawl_date}.json
│
├── mapping-features/
│   └── {job_id}/top500.json
│
├── prompts/
│   ├── experience_extract_v1.txt
│   ├── career_level_v1.txt
│   ├── vacancy_role_v1.txt
│   ├── structural_tension_v1.txt
│   ├── homepage_extract_v1.txt
│   ├── news_funding_extract_v1.txt
│   ├── news_org_extract_v1.txt
│   └── CHANGELOG.md
│
├── api-test/                         # Phase 0 API 검증 결과
│   ├── results/cost_log.jsonl
│   ├── datasets/
│   └── docai-output/
│
├── dead-letter/
│   └── {pipeline}/{item_id}.json
│
├── quality/
│   ├── golden_set/                   # Phase 0 PoC 50건 → regression test 활용 [standard.1-6]
│   └── gold_labels/                  # Phase 2 전문가 검수 400건
│
└── backups/                          # [standard.20] 백업 전략 명시
    ├── neo4j/                        # APOC export (Phase 1 완료 시, Phase 2 전)
    │   └── {date}/nodes.json + rels.json
    └── contexts/                     # GCS Object Versioning으로 자동 보관
```

> **[standard.20] GCS Object Versioning**: `contexts/` 및 `mapping-features/` 하위에 Object Versioning 활성화. 비용 미미 (< $1/월).

---

## 6. 의사결정 포인트 요약

| 시점 | 의사결정 | 입력 데이터 | GCP 영향 |
|------|---------|-----------|---------|
| Phase 0-2 완료 | **Embedding 모델 확정** | gemini-embedding-001 vs text-embedding-005 비교 [standard.22] | Vertex AI 모델/리전 설정 |
| Phase 0-2 완료 | **텍스트 추출 방법 확정** | Document AI vs Gemini 멀티모달 CER/WER 비교 | Phase 1에서 사용할 파이프라인 방법 |
| Phase 0-4 완료 | **LLM 모델 선택** | Claude Haiku vs Sonnet vs Gemini 품질·비용 비교 | Batch API 모델 설정 |
| Phase 0-4 완료 | **PII 전략 확정** | 법무 결론 + 마스킹 영향 테스트 | API (Cloud Run) vs On-premise (GPU) |
| Phase 0-4 완료 | **HWP 파싱 방법 확정** | LibreOffice vs pyhwp vs Gemini 멀티모달 비교 [standard.1-2] | Docker 이미지 구성 |
| Phase 0-6 | **Graph DB 플랜** | 예상 노드 수 계산 | Phase 2 전환 예산 확보 |
| Pre-Phase 0 | **NICE DB 접근** | 계약 상태 | Cloud Functions 구현 범위 |
| Pre-Phase 0 | **PII 법무 검토** | 법무팀 판단 [standard.1-8] | 시나리오 C 전환 여부 |
| Pre-Phase 2 | **크롤링 법적 검토** | 법무팀 판단 [standard.1-9] | 크롤링 범위 제한 |
| Phase 2 시작 전 | **Neo4j Professional 전환** | Phase 1 노드 수 [standard.1-3] | 월 $100~200 예산 |
| Phase 2 완료 | **운영 모드** | 전체 품질 결과 | Cloud Scheduler 증분 주기 |

---

## 7. Anthropic Batch API 제약사항 — [standard.1-4]

> Phase 2 전체 데이터 처리의 핵심 변수. Phase 0 시작 전 Anthropic 측 확인 필요.

| 제약사항 | 현재 값 (확인 필요) | 계획 영향 |
|---|---|---|
| 동시 활성 batch 수 | 기본 ~100 (계정 tier에 따라 상이) | 동시 10 batch 처리 가능 여부 |
| Batch 당 최대 요청 수 | 10,000 요청 | 1,000건/chunk 계획과 호환 |
| 일일 요청 한도 (RPD) | Tier에 따라 상이 | 450K 처리에 필요한 일수 |
| Batch 결과 보관 기간 | 29일 | 보관 기간 내 수집 보장 필요 |
| Batch 처리 SLA | 24시간 (실제 평균 2~6시간) | 처리 시간 계산 기준 |

### 현실적 처리 시간 계산 — [standard.1-7]

```
450K 이력서 / 1,000건/chunk = 450 chunks
450 chunks / 10 동시 = 45 라운드
45 라운드 × 6시간 (평균) = 270시간 = ~11일 (연속 가동)

+ 실패 chunk 재시도: ~2일
+ 결과 수집 + Context 생성: ~2일
+ Graph 적재 + Embedding: ~3일
+ 버퍼: ~3일

= 총 ~21일 ≈ 3~4주 (현실적 추정)
```

---

## 8. 에러 복구 / 재시작 전략 — [standard.1-5]

### 8.1 파이프라인 레벨 Checkpoint

```
BigQuery processing_log를 checkpoint로 활용:
  - 각 item 처리 완료 시 (candidate_id, pipeline, status, processed_at) 기록
  - 재시작 시: SELECT candidate_id FROM processing_log WHERE pipeline='X' AND status='SUCCESS'
  - 이미 성공한 item은 skip

Graph 적재 Checkpoint:
  - 트랜잭션 단위: 100건/batch
  - 마지막 성공 batch 번호를 BigQuery에 기록
  - 재시작 시: 마지막 성공 batch 이후부터 재개
  - Neo4j MERGE 사용으로 중복 적재 안전
```

### 8.2 Batch API 추적 — [standard.1-5]

```sql
-- BigQuery batch_tracking 테이블
CREATE TABLE graphrag_kg.batch_tracking (
  batch_id STRING NOT NULL,        -- Anthropic batch ID
  chunk_id STRING NOT NULL,        -- 내부 chunk ID
  status STRING,                   -- SUBMITTED / PROCESSING / COMPLETED / FAILED / EXPIRED
  submitted_at TIMESTAMP,
  completed_at TIMESTAMP,
  result_collected BOOLEAN DEFAULT FALSE,
  retry_count INT64 DEFAULT 0,
  gcs_request_path STRING,
  gcs_response_path STRING
);
```

```
Batch API 제출 Job 중단 시:
  1. 제출 직전에 batch_id를 BigQuery에 즉시 기록
  2. 폴링 Job 재시작 → batch_tracking에서 미완료 batch 조회
  3. 미완료 batch → Anthropic API로 상태 확인 → 재개 or 재제출
  4. 결과 보관 기간(29일) 내 수집 보장: 일일 batch_tracking 점검 알림
```

### 8.3 OOM/Timeout 대응

```
Cloud Run Job OOM/Timeout 시:
  - 자동 재시작 (max-retries=2)
  - 재시작 시 processing_log checkpoint 기반으로 이미 처리된 건 skip
  - 3회 연속 실패 → Cloud Monitoring 알림 → 수동 조치
```

---

## 9. Neo4j Free → Professional 전환 계획 — [standard.1-3]

### 전환 트리거

| 트리거 | 시점 | 조건 |
|--------|------|------|
| **확정** | Phase 2 시작 전 (Week 16~17) | 필수 전환. "필요 시"가 아닌 **예정된 전환** |
| 조기 전환 | Phase 1 중 | 노드 수 150K 도달 시 |

### 예상 노드 수 계산

```
Phase 1 (1,000 이력서 + 100 JD):
  Person ~1K + Chapter ~5K + Organization ~500 + Vacancy ~100
  + Skill ~2K + Role ~500 + Industry ~100
  = ~9K 노드 → Free 여유 충분

Phase 2 (450K 이력서 + 10K JD):
  Person ~450K + Chapter ~2.25M + Organization ~50K + Vacancy ~10K
  + Skill ~5K + Role ~1K + Industry ~500
  = ~2.77M 노드 → Free 200K 한도 즉시 초과
```

### 마이그레이션 방법

```bash
# 1. Phase 1 완료 시 Free 인스턴스 데이터 백업
# [R-2] APOC Extended 지원 여부에 따라 방법 선택:
#   방법 A (APOC 가능 시): CALL apoc.export.json.all("neo4j_backup.json", {useTypes: true})
#   방법 B (APOC 불가 시): Cypher UNWIND + CSV export → GCS
#   방법 C (APOC 불가 시): AuraDB Console 스냅샷 (Professional 기본 제공)
#   → Phase 0-5-2a에서 확인된 결과에 따라 확정
# → GCS 업로드: gs://graphrag-kg-data/backups/neo4j/{date}/

# 2. Professional 인스턴스 생성 (Neo4j Console)
# 리전: asia-northeast1, 노드 한도: 설정에 따라

# 3. 데이터 Import
# [R-2] APOC 가능 시: CALL apoc.import.json("neo4j_backup.json")
#        APOC 불가 시: Cypher LOAD CSV 또는 Neo4j Data Importer 활용

# 4. Vector Index 재생성
CREATE VECTOR INDEX chapter_embedding IF NOT EXISTS ...
CREATE VECTOR INDEX vacancy_embedding IF NOT EXISTS ...

# 5. 연결 정보 업데이트 (Secret Manager)
gcloud secrets versions add neo4j-uri --data-file=new_uri.txt
gcloud secrets versions add neo4j-password --data-file=new_password.txt

# 6. Free 인스턴스 삭제
```

### 비용

- AuraDB Professional: **$65/월** (최소 사양) ~ **$200/월** (8M 노드 규모)
- Phase 2 기간 (4개월): $260 ~ $800

---

## 10. v2 대비 standard.1 주요 변경 요약

| 항목 | v2 | standard.1 | 리뷰 참조 |
|------|----|----|-----------|
| Phase 0 API 검증 범위 | VAS + RAG Engine + Gemini | Gemini + DocAI만 (VAS/RAG 제거) | R-6 |
| HWP 파싱 | "LibreOffice 포함"으로만 언급 | 3가지 방법 비교 PoC 10건 추가 | R-1 |
| Neo4j 전환 | "필요 시" Professional | Phase 2 전 **필수** 전환 + 마이그레이션 절차 | R-2 |
| Batch API | quota 미기술 | 제약사항 표 + 현실적 시간 계산 | R-3 |
| 에러 복구 | item 레벨만 | 파이프라인 레벨 checkpoint + batch_tracking | R-4 |
| 테스트 전략 | Phase 2 품질 평가만 | Phase 1에 pytest + regression test | R-5 |
| Phase 2 타임라인 | 2~3주 전체 처리 | 3~4주 전체 처리 | R-7 |
| PII 법무 | Phase 0-6에서 판단 | Pre-Phase 0에 법무 검토 선제 시작 | R-8 |
| 크롤링 법적 | robots.txt만 | Pre-Phase 2 법적 검토 + 추출 목적 한정 정책 | R-9 |
| 백업 | GCS backups/ 디렉토리만 | GCS Versioning + Neo4j APOC export 절차 | R-10 |
| 비용 계산 | 영어 토큰 기준 | 한국어 토큰 (×2.5배) 보정 | R-11 |
| Embedding 모델명 | 문서 간 불일치 | text-embedding-005로 통일 | R-12 |
| Phase 2 인력 | 크롤링+처리 병행 | 직렬화 (인력 추가 불가 시) | R-13 |
| 오케스트레이션 | Phase 1 Cloud Workflows | Phase 1 Makefile, Phase 2 Workflows | R-14 |
| ML Distillation | Phase 2-6 | Phase 3 별도 분리 | R-15 |
| Egress 비용 | 누락 | Embedding egress $3.6 추가 | R-16 |
