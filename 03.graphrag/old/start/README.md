# GraphRAG GCP 통합 실행 계획 (start)

GCP 환경에서 Knowledge Graph(KG) 기반 GraphRAG 시스템을 구축하기 위한 **통합 실행 계획** 문서입니다.

## 이 문서는 무엇인가요?

API 기능 검증 → KG 구축 → 크롤링 보강 → 운영까지 전 과정을 하나의 흐름으로 통합한 **GCP 인프라 구현 계획**입니다.

- **무엇을 만드는가**: 이력서(500K)와 JD(10K)에서 LLM으로 정보를 추출하고, 기업 크롤링 데이터를 추가하여 Knowledge Graph를 구축하는 E2E 파이프라인
- **어디에 만드는가**: GCP 단일 프로젝트(`graphrag-kg`) — Cloud Run Jobs, Anthropic Batch API, Neo4j AuraDB, BigQuery, Vertex AI Embedding
- **얼마나 걸리는가**: 약 24~29주 (Phase 0~2)

## 세 버전의 진화 과정

`start/` 디렉토리에는 3개의 버전이 존재하며, 각 버전은 이전 버전을 통합·개선한 결과입니다.

| 버전 | 디렉토리 | 특징 | 문서 수 |
|------|----------|------|---------|
| **v0** | `1/` | 개별 계획 — 크롤링/KG 구축을 별도 문서로 분리 | 2 |
| **v1** | `2/` | v7 파이프라인 통합 — 아키텍처·실행·비용을 일원화 | 3 |
| **v2 (최신)** | `3/` | API 검증 내장 + 크롤링 Phase 2 조기 통합 + 비용 라이프사이클 통합 | 5 |

> **v2(`3/`)를 읽으세요.** v0, v1은 참고용 히스토리입니다.

### v2 주요 변경 사항 (v1 대비)

| 변경 | 내용 |
|------|------|
| API 검증 내장 | 별도 3일 테스트 → Phase 0 PoC에 통합 (의사결정 즉시 반영) |
| 단일 GCP 프로젝트 | `graphrag-kg` 하나로 통합 (별도 api-test 프로젝트 불필요) |
| 크롤링 조기화 | Phase 3 → Phase 2 후반으로 앞당김 (CompanyContext 보강 조기 반영) |
| P0 패치 반영 | api-test-3day-v3-review.md의 5건 패치 적용 |
| Embedding 비교 | `text-multilingual-embedding-002` vs `gemini-embedding-001` Phase 0에서 확정 |
| 비용 통합 | API 검증 비용 포함 + 전체 라이프사이클 비용 일원화 |

## 문서 구조

### v2 (최신) — `3/`

| 문서 | 내용 | 핵심 키워드 |
|------|------|-------------|
| [`00_overview.md`](3/00_overview.md) | 전체 구조, 아키텍처, 의사결정 포인트 | 통합 타임라인, GCS 구조, DAG |
| [`01_phase0_validation_poc.md`](3/01_phase0_validation_poc.md) | Phase 0: GCP API 검증 + LLM PoC + 인프라 셋업 | Gemini, Document AI, 50건 PoC |
| [`02_phase1_mvp_pipeline.md`](3/02_phase1_mvp_pipeline.md) | Phase 1: MVP 파이프라인 (전처리→Context→Graph→Mapping) | 1,000건 E2E, 3-tier 실패 처리 |
| [`03_phase2_scale_and_crawl.md`](3/03_phase2_scale_and_crawl.md) | Phase 2: 전체 데이터 처리 + 크롤링 + 품질 평가 | 450K 확장, 홈페이지/뉴스 크롤링 |
| [`04_cost_monitoring_ops.md`](3/04_cost_monitoring_ops.md) | 비용 추정 + 모니터링 + 운영 인프라 | ~$7,800, Looker Studio |

### v1 (히스토리) — `2/`

| 문서 | 내용 |
|------|------|
| [`01_gcp_architecture.md`](2/01_gcp_architecture.md) | v7 파이프라인 GCP 아키텍처 매핑 |
| [`02_gcp_execution_plan.md`](2/02_gcp_execution_plan.md) | Phase별 상세 실행 계획 |
| [`03_gcp_cost_and_monitoring.md`](2/03_gcp_cost_and_monitoring.md) | 비용 추정 + 모니터링 |

### v0 (히스토리) — `1/`

| 문서 | 내용 |
|------|------|
| [`crawling-gcp-plan.md`](1/crawling-gcp-plan.md) | 기업 크롤링 파이프라인 (홈페이지/뉴스) |
| [`create-kg-gcp-plan.md`](1/create-kg-gcp-plan.md) | KG 구축 GCP 인프라 (v5 기반) |

## 전체 타임라인 요약

```
Phase 0: 기반 구축 + API 검증 + PoC              (4~5주)
  ├─ 0-1: GCP 환경 구성 + API 활성화 (3일)
  ├─ 0-2: Vertex AI API 기능 검증 (3일)
  ├─ 0-3: 데이터 탐색 + 프로파일링 (1주)
  ├─ 0-4: LLM 추출 PoC — 50건 이력서 (1~2주)
  ├─ 0-5: 인프라 셋업 — Neo4j, BigQuery, GCS (1주, 병행)
  └─ 0-6: 의사결정 (LLM 모델, PII, Embedding, 오케스트레이션)

Phase 1: MVP 파이프라인                           (10~12주)
  ├─ 1-1: 전처리 — PDF/DOCX/HWP 파싱, PII, 중복 제거
  ├─ 1-2: CompanyContext 추출 — NICE + LLM (100 JD)
  ├─ 1-3: CandidateContext 추출 — Batch API (1,000건)
  ├─ 1-4: Graph 적재 — Neo4j + Entity Resolution
  └─ 1-5: MappingFeatures + MAPPED_TO

Phase 2: 전체 데이터 + 크롤링 + 운영              (10~12주)
  ├─ 2-1: 전체 처리 — 450K 이력서, 10K JD
  ├─ 2-2: 크롤링 파이프라인 — 홈페이지/뉴스/LLM 추출
  ├─ 2-3: CompanyContext 보강 (fill_rate 0.85+)
  ├─ 2-4: 품질 평가 — Gold Test Set 200건
  ├─ 2-5: DS/MLE 서빙 인터페이스
  └─ 2-6: 증분 자동화 + 운영 이관

첫 MVP 데모: ~Week 17 (Phase 0~1 완료)
전체 완성:   ~Week 29
```

## GCP 핵심 서비스

| 역할 | GCP 서비스 |
|------|-----------|
| 배치 파이프라인 | Cloud Run Jobs (11개 Job) |
| LLM 추출 | Anthropic Batch API (50% 할인) |
| 크롤링 LLM | Vertex AI Gemini |
| Embedding | Vertex AI Embedding (768d) |
| Graph DB | Neo4j AuraDB (Free → Professional) |
| 데이터 웨어하우스 | BigQuery (처리 로그, 서빙 테이블) |
| 오케스트레이션 | Cloud Workflows + Cloud Scheduler |
| 모니터링 | BigQuery + Looker Studio + Cloud Monitoring |
| 보안 | Secret Manager + 서비스 계정 분리 (최소 권한) |

## 예상 비용

| 항목 | 비용 |
|------|------|
| Phase 0 (API 검증 + PoC) | ~$120 |
| Phase 1 (MVP 개발) | ~$86 |
| Phase 2 (LLM + 인프라) | ~$1,756 |
| **총 구축 비용 (Scenario A: Haiku Batch)** | **~$7,802 (~1,069만원)** |
| **월 운영 비용** | **~$180~280/월** |

> Scenario D (Gemini Flash)가 ~$7,482로 가장 저렴. Scenario C (On-premise GPU)는 $17,594로 가장 비쌈.

## 핵심 아키텍처 결정

| 결정 | 선택 | 근거 |
|------|------|------|
| GCP 프로젝트 | 단일 `graphrag-kg` | 비용 추적 통합, IAM 단순화 |
| 오케스트레이션 | Cloud Workflows | GCP 네이티브, ~무료 |
| KG 배치 처리 | Anthropic Batch API | 50% 할인 ($575 vs $1,150) |
| LLM 실패 처리 | 3-tier (json-repair → retry → partial) | Dead-letter 비용 최소화 |
| Graph 멱등성 | MERGE + Deterministic ID | 재실행 시 중복 없음 |
| 청크 추적 | BigQuery `chunk_status` | 450 청크 실시간 진행률 |
| 크롤링 시점 | Phase 2 (Phase 3 아닌) | CompanyContext 조기 보강 |

## 리전 배치

| 서비스 | 리전 |
|--------|------|
| GCS / BigQuery / Cloud Run | asia-northeast3 (서울) |
| Vertex AI (Gemini / Embedding) | us-central1 |
| Document AI | us (멀티 리전) |
| Neo4j AuraDB | asia-northeast1 (도쿄, ~10ms) |

## 읽는 순서 (처음 접하는 분)

1. **이 README** — 전체 그림 파악
2. **[`3/00_overview.md`](3/00_overview.md)** — 통합 구조, DAG, GCS/BigQuery 스키마, 의사결정 포인트
3. 관심 Phase의 상세 문서 (`01` → `02` → `03` 순서)
4. **[`3/04_cost_monitoring_ops.md`](3/04_cost_monitoring_ops.md)** — 비용/모니터링/보안/알림은 필요할 때 참조
