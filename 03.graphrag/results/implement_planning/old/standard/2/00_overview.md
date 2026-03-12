# GraphRAG GCP 통합 실행 계획 standard.2

> **목적**: GCP 환경에서 GraphRAG 시스템 전체를 구축하기 위한 통합 계획.
> API 기능 검증 → Knowledge Graph 구축 → 크롤링 보강 → 운영까지 전 과정을 하나의 흐름으로 통합.
>
> **standard.2 변경 사항** (standard.1 리뷰 R-1 ~ R-15 반영):
> - [standard.1.1-1] Phase 1-1 전처리 모듈 2주→**3주** 확장 (R-1)
> - [standard.1.1-2] Phase 1 시작 시 코드 리팩토링 2~3일 명시 (R-3)
> - [standard.1.1-3] Phase 1~2 사이 **1주 버퍼** 추가 (R-6)
> - [standard.1.1-4] DE/MLE **역할 분담표** 추가 (R-7)
> - [standard.1.1-5] Phase 2-2 품질 평가 1주→**3일** 축소 (Cohen's d Phase 3 이동) (R-10)
> - [standard.1.1-6] Phase 2-5 서빙 인터페이스 1주→**3일** 축소 (R-9)
> - [standard.1.1-7] Phase 2-6 증분 처리 1~2주→**2주** 고정 + 보완 (R-2)
> - [standard.1.1-8] Cloud Workflows YAML 상세 제거, **DAG 구조만** 기술 (R-11)
> - [standard.1.1-9] 크롤링 BigQuery 테이블 5개→**3개** 축소 (R-14)
> - [standard.1.1-10] **운영 인력 계획** + 인수인계 문서 태스크 추가 (R-8)
> - [standard.1.1-11] Looker Studio를 Phase 3으로 이동, Phase 2는 BigQuery Saved Queries (R-11)
> - [standard.1.1-12] Neo4j **connection pool 한도 확인** 태스크 추가 (R-4)
> - [standard.1.1-13] Batch API 수치 **계획 확정 전 즉시 확인** 강조 (R-5)
> - [standard.1.1-14] Organization ER **한국어 전처리 규칙** + 전수 검수 추가 (R-12)
> - [standard.1.1-15] Phase 0→1, Phase 2→운영 **Go/No-Go 기준** 보완 (R-15)
> - [standard.1.1-16] 문서 간 **비용 수치 통일** (R-13)
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
| `05_models_and_methods.md` | 모델 · 방법론 · 알고리즘 정리 |

---

## 1. 전체 타임라인

```
Phase 0: 기반 구축 + API 검증 + PoC (4~5주)
  ├─ 0-1: GCP 환경 구성 + API 활성화 (3일)
  ├─ 0-2: Vertex AI API 기능 검증 (2일)
  ├─ 0-3: 데이터 탐색 + 프로파일링 (1주)
  ├─ 0-4: LLM 추출 PoC + HWP 파싱 PoC (1~2주)
  ├─ 0-5: 인프라 셋업 — Neo4j, BigQuery, GCS (1주, 0-3과 병행)
  └─ 0-6: Phase 0 의사결정

Phase 1: MVP 파이프라인 (11~13주) — [standard.1.1-1] +1주
  ├─ 1-0: Phase 0 코드 리팩토링 + 의사결정 통합 (2~3일) — [standard.1.1-2] 신규
  ├─ 1-1: 전처리 모듈 (3주) — [standard.1.1-1] 2주→3주
  ├─ 1-2: CompanyContext 파이프라인 (1~2주)
  ├─ 1-3: CandidateContext 파이프라인 (4주)
  ├─ 1-4: Graph 적재 (2주)
  ├─ 1-5: MappingFeatures + MAPPED_TO (2주)
  └─ 1-6: 테스트 인프라 + Regression Test (1주, 1-5와 병행)

버퍼: 1주 (Phase 1 완료 → Phase 2 시작 사이) — [standard.1.1-3] 신규

Phase 2: 확장 + 크롤링 + 품질 (11~14주) — [standard.1.1-5,6,7] -1~2주
  ├─ 2-0: Neo4j Professional 전환 (1일)
  ├─ 2-1: 전체 데이터 처리 — 450K 이력서 (3~4주)
  ├─ 2-2: 품질 평가 + Gold Test Set (3일, 2-1과 병행) — [standard.1.1-5] 1주→3일
  ├─ 2-3: 크롤링 파이프라인 구축 (4주) — 2-1 이후 직렬
  │   ├─ 2-3-1: 홈페이지 크롤러 (Playwright)
  │   ├─ 2-3-2: 뉴스 수집기 (네이버 API)
  │   └─ 2-3-3: LLM 추출 (Gemini Flash)
  ├─ 2-4: 크롤링 데이터 → CompanyContext 보강 (1주)
  ├─ 2-5: DS/MLE 서빙 인터페이스 (3일) — [standard.1.1-6] 1주→3일
  └─ 2-6: 증분 처리 + 운영 인프라 + 인수인계 (2주) — [standard.1.1-7,10]

Phase 3: 운영 최적화 (별도, 필요 시)
  ├─ 3-1: ML Knowledge Distillation (scope_type, seniority)
  ├─ 3-2: LLM 비용 최적화 (Confidence 기반 ML/LLM 라우팅)
  ├─ 3-3: 파이프라인 성능 튜닝
  └─ 3-4: Looker Studio 대시보드 구축 — [standard.1.1-11] Phase 2에서 이동

총 MVP 완성: ~27~33주
첫 동작 데모: ~19주 (Phase 0~1 완료 + 버퍼)
전체 데이터 + 크롤링 완료: ~33주
```

### standard.1 → standard.2 타임라인 변경 요약

| 항목 | standard.1 | standard.2 | 변경 이유 |
|------|----|----|-----------|
| Phase 1-0 코드 리팩토링 | 없음 | 2~3일 | Phase 0 PoC→프로덕션 전환 시간 명시 (R-3) |
| Phase 1-1 전처리 모듈 | 2주 | **3주** | 9개 태스크 현실적 소화 (R-1) |
| Phase 1 전체 | 10~12주 | **11~13주** | +1주 |
| Phase 1~2 버퍼 | 없음 | **1주** | 번아웃 방지 + 전환 준비 (R-6) |
| Phase 2-2 품질 평가 | 1주 | **3일** | Cohen's d Phase 3 이동 (R-10) |
| Phase 2-5 서빙 인터페이스 | 1주 | **3일** | SQL 작성에 1주 과다 (R-9) |
| Phase 2-6 증분+운영 | 1~2주 | **2주** | 증분 처리 복잡성 + 인수인계 (R-2, R-8) |
| Phase 2 전체 | 12~16주 | **11~14주** | -1~2주 |
| Looker Studio | Phase 2 | **Phase 3** | 2명 체제에서 과잉 (R-11) |
| 총 타임라인 | 26~33주 | **27~33주** | 실질 변화 없음, 부담 균등 분배 |

---

## 2. DE/MLE 역할 분담표 — [standard.1.1-4] 신규

> 2명 체제(DE 1명 + MLE 1명)에서 26~33주 연속 풀타임.
> 역할 분담을 명시하여 병목 방지 + 인력 추가 시 온보딩 가이드 역할.

| Phase | DE 담당 | MLE 담당 | 공동 |
|-------|---------|---------|------|
| **Phase 0** | GCP 환경, 인프라 셋업, Docker | LLM PoC, 프롬프트 설계, HWP PoC | 데이터 프로파일링 |
| **Phase 1-0** | 프로젝트 구조, CI/CD | Phase 0 프롬프트→프로덕션 통합 | 코드 리팩토링 |
| **Phase 1-1** | 파서(PDF/DOCX/HWP), SimHash, Docker | PII 마스킹, 섹션 분할, 경력 블록 분리 | 기술 사전 |
| **Phase 1-2** | NICE Lookup, Rule 엔진 | LLM 프롬프트 튜닝 | CompanyContext 통합 |
| **Phase 1-3** | Batch API 인프라, chunk 관리 | LLM 추출 프롬프트, 3-tier 파싱 | batch_tracking |
| **Phase 1-4** | Graph 적재, MERGE 로직, 벤치마크 | Organization ER, Embedding | checkpoint |
| **Phase 1-5** | BigQuery 서빙 테이블 | MappingFeatures 로직 | 수동 검증 |
| **Phase 1-6** | 통합 테스트 | regression test | 공동 |
| **Phase 2-0** | Neo4j 전환, Secret 업데이트 | — | 연결 테스트 |
| **Phase 2-1** | Batch API 운영, 모니터링 | dead-letter 분석, 품질 확인 | 공동 |
| **Phase 2-2** | — | 품질 평가 설계, Gold Test Set | 전문가 관리 |
| **Phase 2-3** | 크롤러 인프라, Playwright | 크롤링 LLM 프롬프트 | 파일럿 검수 |
| **Phase 2-4~5** | BigQuery 스키마 | CompanyContext 보강 로직 | 공동 |
| **Phase 2-6** | Cloud Scheduler, 증분 인프라 | 증분 변경 감지 로직 | 인수인계 문서 |

> **인력 추가 판단 시점**: Phase 1 완료(Week 19~20). 추가 인력 온보딩 2~3주 감안, Phase 2 시작 최소 3주 전 결정.

---

## 3. GCP 통합 아키텍처

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
│  │   └─ backups/                  (Neo4j export + Context 백업)              │
│  │                                                                            │
│  ├─ BigQuery: graphrag_kg                                                    │
│  │   ├─ processing_log            (처리 이력/모니터링 + checkpoint)            │
│  │   ├─ chunk_status              (chunk 상태 추적)                          │
│  │   ├─ batch_tracking            (Batch API batch_id 추적)                  │
│  │   ├─ mapping_features          (서빙 테이블)                               │
│  │   ├─ quality_metrics           (품질 평가 결과)                            │
│  │   ├─ parse_failure_log         (LLM 파싱 실패 모니터링)                   │
│  │   └─ crawl.*                   (크롤링 — 3개 테이블) — [standard.1.1-9] 5→3개     │
│  │       ├─ crawl_company_targets                                            │
│  │       ├─ crawl_raw_data        (homepage+news 통합)                       │
│  │       └─ crawl_extracted_fields                                           │
│  │                                                                            │
│  └─ Neo4j AuraDB                                                             │
│      ├─ Free (Phase 0~1) → Professional (Phase 2 시작 전 필수)               │
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
│  ├─ Makefile / bash              (Phase 1 수동 오케스트레이션)                │
│  ├─ Cloud Workflows             (Phase 2+ DAG 관리)                         │
│  └─ Cloud Scheduler             (증분 처리 일일 배치 트리거)                  │
│                                                                              │
│  [LLM API (외부)]                                                            │
│  ├─ Anthropic Batch API         (Claude Haiku 4.5 — KG 추출 Primary)         │
│  ├─ Anthropic API               (Claude Sonnet 4.6 — Fallback/PoC)           │
│  └─ Vertex AI Gemini            (크롤링 LLM 추출 + Phase 0 API 검증)        │
│                                                                              │
│  [Embedding API]                                                             │
│  ├─ Vertex AI                   (text-embedding-005 — 768d)                  │
│  └─ Vertex AI Gemini            (gemini-embedding-001 — Phase 0 비교 후 확정) │
│                                                                              │
│  [모니터링]                                                                   │
│  ├─ Cloud Monitoring            (인프라 메트릭)                               │
│  ├─ Cloud Logging               (애플리케이션 로그)                           │
│  └─ BigQuery Saved Queries      (커스텀 모니터링) — [standard.1.1-11] Looker 제거    │
│                                                                              │
│  [보안]                                                                       │
│  ├─ Secret Manager              (Anthropic, Neo4j, 네이버, OpenAI API 키)    │
│  ├─ IAM                         (서비스 계정 최소 권한)                       │
│  └─ VPC Service Controls        (PII 유출 방지, 선택적)                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. GCP 서비스 매핑 (통합)

### 4.1 파이프라인별 GCP 서비스

| 파이프라인 | GCP 서비스 | 선택 근거 |
|---|---|---|
| **Phase 0: API 검증** | Cloud Shell / 로컬 Python | 2일 단발 테스트, 인프라 불필요 |
| **이력서 파싱 (전처리)** | Cloud Run Jobs | CPU 집약, Task 단위 병렬 (최대 10,000 tasks) |
| **이력서 중복 제거** | Cloud Run Jobs | 메모리 집약 (SimHash 전체 비교) |
| **CompanyContext 생성** | Cloud Run Jobs + Anthropic Batch API | 10K JD 규모, Batch 50% 할인 |
| **CandidateContext 생성** | Cloud Run Jobs + Anthropic Batch API | 500K 이력서, 핵심 비용 포인트 |
| **Graph 적재** | Cloud Run Jobs | Neo4j AuraDB 연결, 트랜잭션 배치 |
| **Embedding 생성** | Cloud Run Jobs + Vertex AI Embedding | text-embedding-005 |
| **MappingFeatures 계산** | Cloud Run Jobs | Rule + Embedding cosine |
| **홈페이지 크롤링** | Cloud Run Jobs (Playwright) | headless Chrome, 타임아웃 1시간 |
| **뉴스 수집** | Cloud Run Jobs | 네이버 API + 본문 크롤링 (funding/org_change) |
| **크롤링 LLM 추출** | Cloud Run Jobs + Gemini API | Gemini Flash (Phase 0 확정 버전 snapshot 고정) |
| **증분 처리** | Cloud Functions + Cloud Scheduler | 일일 트리거, 경량 |
| **Dead-Letter 재처리** | Cloud Scheduler + Cloud Run Jobs | 일 1회 자동 재시도 |

### 4.2 Pipeline DAG 의존성

```
[Phase 0] API 검증 + PoC → 의사결정
                │
[Phase 1]       ▼
1-0: 코드 리팩토링 (2~3일) — [standard.1.1-2]
                │
Pipeline A (CompanyContext)  ──┐
                               ├──→ C (Graph 적재) ──→ D (Embedding+Mapping) ──→ E (서빙)
Pipeline B (CandidateContext) ─┘
                │
[버퍼 1주]      ▼ — [standard.1.1-3]
                │
[Phase 2]       ▼
Neo4j Professional 전환 (필수)
                │
전체 데이터 처리 (450 chunks, 3~4주) ──→ 품질 평가 (3일)
                │                           (직렬)
                ▼
크롤링 파이프라인 (4주) ──→ CompanyContext 보강 ──→ Graph 업데이트
```

---

## 5. 통합 환경 구성

```
프로젝트: graphrag-kg (단일 프로젝트)
리전: asia-northeast3 (서울) — 데이터 주권, 레이턴시
Vertex AI 리전: us-central1 — Gemini API + Embedding API
Neo4j AuraDB: asia-northeast1 (도쿄) — 서울 미지원, 가장 가까운 리전

API 활성화 필요:
  - Vertex AI API
  - Cloud Run API
  - Cloud Workflows API          (Phase 2부터 사용)
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

  # HWP 파싱 PoC
  pyhwp >= 0.1b12
  # + LibreOffice (Docker 설치)
  # + Gemini 멀티모달 (별도 SDK 불필요)

  # 크롤링
  playwright >= 1.40.0
  readability-lxml >= 0.8.1
  beautifulsoup4 >= 4.12.0
  requests >= 2.31.0

  # 테스트
  pytest >= 8.0.0
  pytest-cov >= 4.1.0
  deepdiff >= 6.7.0

Budget Alert:
  Phase 0: $500 (경고), $800 (강제 중단)
  Phase 1-2: $2,000 (경고), $3,500 (강제 중단)
  운영: 월 $300 (경고), $500 (강제 중단)
```

---

## 6. 의사결정 포인트 요약

| 시점 | 의사결정 | 입력 데이터 | GCP 영향 |
|------|---------|-----------|---------|
| Phase 0-2 완료 | **Embedding 모델 확정** | gemini-embedding-001 vs text-embedding-005 비교 | Vertex AI 모델/리전 설정 |
| Phase 0-2 완료 | **텍스트 추출 방법 확정** | Document AI vs Gemini 멀티모달 CER/WER 비교 | Phase 1에서 사용할 파이프라인 방법 |
| Phase 0-4 완료 | **LLM 모델 선택** | Claude Haiku vs Sonnet vs Gemini 품질·비용 비교 | Batch API 모델 설정 |
| Phase 0-4 완료 | **PII 전략 확정** | 법무 결론 + 마스킹 영향 테스트 | API (Cloud Run) vs On-premise (GPU) |
| Phase 0-4 완료 | **HWP 파싱 방법 확정** | LibreOffice vs pyhwp vs Gemini 멀티모달 비교 | Docker 이미지 구성 |
| Phase 0-6 | **Graph DB 플랜** | 예상 노드 수 계산 | Phase 2 전환 예산 확보 |
| Pre-Phase 0 | **NICE DB 접근** | 계약 상태 | Cloud Functions 구현 범위 |
| Pre-Phase 0 | **PII 법무 검토** | 법무팀 판단 | 시나리오 C 전환 여부 |
| Pre-Phase 0 | **Batch API quota 즉시 확인** | Anthropic 콘솔 [standard.1.1-13] | 타임라인 확정 가능 여부 |
| Pre-Phase 2 | **크롤링 법적 검토** | 법무팀 판단 | 크롤링 범위 제한 |
| Phase 1 완료 | **인력 추가 여부** [standard.1.1-4] | Phase 1 결과 | Phase 2 병렬화 가능 여부 |
| Phase 2 시작 전 | **Neo4j Professional 전환** | Phase 1 노드 수 | 월 $100~200 예산 |
| Phase 2 완료 | **운영 전환** [standard.1.1-15] | 전체 품질 결과 | 운영 인력 배치 |

---

## 7. Anthropic Batch API 제약사항

> Phase 2 전체 데이터 처리의 핵심 변수.
> **[standard.1.1-13] 계획 확정 전 즉시 확인** — Phase 0 시작 전이 아닌 **지금** Anthropic 콘솔에서 확인 가능한 항목은 즉시 확인.

| 제약사항 | 현재 값 (확인 필요) | 계획 영향 |
|---|---|---|
| 동시 활성 batch 수 | 기본 ~100 (계정 tier에 따라 상이) | 동시 10 batch 처리 가능 여부 |
| Batch 당 최대 요청 수 | 10,000 요청 | 1,000건/chunk 계획과 호환 |
| 일일 요청 한도 (RPD) | Tier에 따라 상이 | 450K 처리에 필요한 일수 |
| Batch 결과 보관 기간 | 29일 | 보관 기간 내 수집 보장 필요 |
| Batch 처리 SLA | 24시간 (실제 평균 2~6시간) | 처리 시간 계산 기준 |

### 즉시 확인 항목 [standard.1.1-13]

```
□ Anthropic 콘솔에서 현재 Tier 확인 → 계획 문서에 기록
□ Claude Haiku 4.5가 Batch API 지원 모델인지 확인
□ 동시 활성 batch 수 한도 확인
□ 확인 결과에 따라 Phase 2-1 타임라인 보정:
  - 동시 ≥ 10: 계획대로 3~4주
  - 동시 5~9: 4~5주로 조정
  - 동시 ≤ 4: 5~8주 또는 Gemini Flash 병행
```

### 현실적 처리 시간 계산

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

## 8. 에러 복구 / 재시작 전략

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

### 8.2 Batch API 추적

```sql
-- BigQuery batch_tracking 테이블
CREATE TABLE graphrag_kg.batch_tracking (
  batch_id STRING NOT NULL,
  chunk_id STRING NOT NULL,
  status STRING,                   -- SUBMITTED / PROCESSING / COMPLETED / FAILED / EXPIRED
  submitted_at TIMESTAMP,
  completed_at TIMESTAMP,
  result_collected BOOLEAN DEFAULT FALSE,
  retry_count INT64 DEFAULT 0,
  gcs_request_path STRING,
  gcs_response_path STRING
);
```

### 8.3 OOM/Timeout 대응

```
Cloud Run Job OOM/Timeout 시:
  - 자동 재시작 (max-retries=2)
  - 재시작 시 processing_log checkpoint 기반으로 이미 처리된 건 skip
  - 3회 연속 실패 → Cloud Monitoring 알림 → 수동 조치
```

---

## 9. Neo4j Free → Professional 전환 계획

### 전환 트리거

| 트리거 | 시점 | 조건 |
|--------|------|------|
| **확정** | Phase 2 시작 전 (Week 20~21) | 필수 전환 |
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
# Phase 0-5-2a에서 확인된 APOC 지원 여부에 따라 방법 선택:
#   방법 A (APOC 가능 시): CALL apoc.export.json.all(...)
#   방법 B (APOC 불가 시): Cypher UNWIND + CSV export → GCS
#   방법 C (APOC 불가 시): AuraDB Console 스냅샷 (Professional 기본 제공)

# 2. Professional 인스턴스 생성, 3. 데이터 Import, 4. Vector Index/Constraint 재생성
# 5. Secret Manager 연결 정보 업데이트, 6. 연결 테스트, 7. Free 인스턴스 삭제
```

### 비용

- AuraDB Professional: **$65/월** (최소 사양) ~ **$200/월** (8M 노드 규모)
- Phase 2 기간 (4개월): $260 ~ $800

---

## 10. Phase 간 Go/No-Go 기준 — [standard.1.1-15] 보완

### Phase 0 → Phase 1 Go/No-Go

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| 의사결정 9개 중 7개+ 확정 | 확정 7개 이상 | 미확정 항목이 Phase 1에 직접 영향 시 → Phase 0 1주 연장 |
| HWP 파싱 방법 | 3방법 중 1개 이상 CER ≤ 0.15 | 3개 모두 CER > 0.15 → Phase 1에서 HWP 제외, DOCX/PDF만 처리 |
| LLM 추출 품질 | scope_type 정확도 > 60% (50건) | 60% 미달 → 프롬프트 재설계 1주 추가 |
| Batch API quota | 계획 실행에 필요한 최소 조건 확인 | 미확인 시 Phase 1 진행하되, Phase 2 타임라인 미확정 |

### Phase 1 → Phase 2 Go/No-Go

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| E2E 파이프라인 | JD 100건 + 이력서 1,000건 정상 처리 | Phase 1 연장 (최대 2주) |
| Regression test | Golden 50건 전 항목 통과 | 실패 항목 프롬프트 수정 후 재실행 |
| 수동 검증 | 50건 중 치명적 결함 0건 | 결함 원인 분석 + 수정 후 재검증 |
| Neo4j 백업 | 백업 완료 + 노드/엣지 수 기록 | 백업 완료 전 Phase 2 진입 불가 |
| 적재 벤치마크 | 500K 추정 시간 산출 완료 | 벤치마크 미완료 시 Phase 2 Graph 적재 리스크 |

### Phase 2 → 운영 전환 Go/No-Go — [standard.1.1-15] 신규

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| 품질 평가 | Gold Test Set 최소 기준 전 항목 충족 | 미달 항목 프롬프트 재설계 + 재처리 |
| 증분 파이프라인 | 일일 증분 3일 연속 정상 동작 | 디버깅 후 재시도 |
| 백업 자동화 | Neo4j 주간 백업 + GCS Versioning 확인 | 자동화 완료 전 운영 전환 불가 |
| 인수인계 문서 | 운영 매뉴얼 작성 완료 [standard.1.1-10] | 문서 완료 전 운영 전환 불가 |
| 운영 인력 확정 | 운영 담당자 지정 완료 [standard.1.1-10] | 미지정 시 DE/MLE 중 1명 운영 겸임 |
