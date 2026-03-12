# GraphRAG GCP 통합 실현 계획

GCP 환경에서 Knowledge Graph(KG) 기반 GraphRAG 시스템을 구축하기 위한 통합 실현 계획 문서입니다.

## 이 문서는 무엇인가요?

[`02.create-kg/plans/v7/`](../../02.knowledge_graph/results/extraction_logic/v7/)에 정의된 KG 구축 파이프라인 설계를 **GCP 인프라 위에서 실제로 구현하기 위한 단계별 실행 계획**입니다.

- **무엇을 만드는가**: 이력서(500K)와 JD(10K)에서 LLM으로 정보를 추출하여 Knowledge Graph를 구축하고, 기업 크롤링으로 보강한 뒤, 후보자-공고 매칭 피처를 생성하는 E2E 파이프라인
- **어디에 만드는가**: GCP 단일 프로젝트(`graphrag-kg`) — Cloud Run Jobs, Anthropic Batch API, Neo4j AuraDB, BigQuery, Vertex AI Embedding
- **얼마나 걸리는가**: 약 27~33주 (Phase 0~2)

## 세 트랙 안내

본 계획은 **경량(light)**, **표준(standard)**, **코어(core)** 세 트랙으로 관리됩니다.

| 트랙 | 디렉토리 | 특징 | 총 일정 |
|------|----------|------|---------|
| **light (light)** | `light/` | 크롤링 후속 분리, Staged Fast Fail, 최소 서빙 | 16.5~17.5주 코어 |
| **standard (standard)** | `standard/` | 크롤링 포함, 증분 처리, 운영 인프라 완비 | 27~33주 |
| **core (core)** | `core/` | **에이전트 역량 중심 점진적 확장, DB MVP 선행, API 서빙 강화** | 27주 |

> 에이전트 진화 중심의 점진적 코어 파이프라인이 궁금하다면 [`README.core.md`](README.core.md)를 참조하세요.

## 최신 버전: standard.2

> **standard.2를 읽으세요.** v0/v1/v2/standard.1은 참고용 히스토리입니다.

standard.2는 standard.1 리뷰(R-1 ~ R-15)를 반영하여 다음을 개선했습니다:

| 변경 | 내용 |
|------|------|
| Phase 1-1 전처리 확대 | 2주 → **3주** (9개 태스크 현실적 소화) |
| 코드 리팩토링 명시 | Phase 1-0에 Phase 0 PoC → 프로덕션 전환 2~3일 추가 |
| Phase 1~2 버퍼 | **1주 버퍼** 추가 (번아웃 방지 + 전환 준비) |
| DE/MLE 역할 분담표 | Phase별 담당 영역 명시로 병목 방지 |
| Phase 2 축소 | 품질 평가 1주→3일, 서빙 인터페이스 1주→3일 |
| 증분 처리 보강 | 2주 고정 + 인수인계 문서 태스크 추가 |
| Looker Studio 후순위화 | Phase 3으로 이동, Phase 2는 BigQuery Saved Queries |
| 비용 수치 통일 | 문서 간 LLM/인프라 비용 경계 명확화 |
| Go/No-Go 보완 | Phase 2 → 운영 전환 기준 신규 추가 |

## 문서 구조

### standard.2 (최신) — `standard/2/`

| 문서 | 내용 | 핵심 키워드 |
|------|------|-------------|
| [`00_overview.md`](2/00_overview.md) | 전체 구조, 아키텍처, DE/MLE 역할 분담, 의사결정 포인트 | 타임라인, 아키텍처, DAG, Go/No-Go |
| [`01_phase0_validation_poc.md`](2/01_phase0_validation_poc.md) | Phase 0: GCP API 검증 + LLM PoC + 인프라 셋업 (4~5주) | Vertex AI 검증, Document AI, Embedding 비교, Neo4j 스키마 |
| [`02_phase1_mvp_pipeline.md`](2/02_phase1_mvp_pipeline.md) | Phase 1: MVP 파이프라인 구축 (11~13주) | 전처리, CompanyContext, CandidateContext, Graph 적재, Mapping |
| [`03_phase2_scale_and_crawl.md`](2/03_phase2_scale_and_crawl.md) | Phase 2: 전체 데이터 처리 + 크롤링 + 품질 평가 (11~14주) | 450K 이력서, 크롤링, Gold Test Set, 증분 처리, 인수인계 |
| [`04_cost_monitoring_ops.md`](2/04_cost_monitoring_ops.md) | 비용 추정 + 모니터링 + 보안 + 운영 인프라 | 시나리오별 비용, BigQuery Saved Queries, PII 처리, Docker |
| [`05_models_and_methods.md`](2/05_models_and_methods.md) | 모델 · 방법론 · 알고리즘 정리 | LLM, Embedding, 청킹, 파싱, ER |

### standard.1 (히스토리) — `standard/1/`

standard.1은 v2를 기반으로 크롤링 통합, Phase 구조 정비, 상세 코드 예시를 추가한 초판입니다.

### light (light 트랙) — `light/`

| 버전 | 내용 |
|------|------|
| `light/1/` | Staged Fast Fail 최초 도입 (12~14주) |
| `light/2/` | light.1 보정판, 현실적 타임라인 (16.5~17.5주) |

> light 트랙 상세는 [`README.light.md`](README.light.md) 참조.

### start.1, start.2, start.3 (히스토리) — `start/1/`, `start/2/`, `start/3/`

| 버전 | 파일 | 설명 |
|------|------|------|
| start.1 | `crawling-gcp-plan.md` | 기업 크롤링 단독 계획 (홈페이지/뉴스) |
| start.1 | `create-kg-gcp-plan.md` | KG 구축 GCP 인프라 계획 (v5 기반) |
| start.2 | `01_gcp_architecture.md` | v7 파이프라인 통합 아키텍처 |
| start.2 | `02_gcp_execution_plan.md` | Phase별 상세 실행 계획 |
| start.2 | `03_gcp_cost_and_monitoring.md` | 비용 추정 + 모니터링 |
| start.3 | `00_overview.md` ~ `04_cost_monitoring_ops.md` | Phase 중심 5개 문서 통합 |

## 전체 타임라인 요약

```
Phase 0: 기반 구축 + API 검증 + PoC          (4~5주)
  ├─ GCP 환경 구성 + Vertex AI API 검증 (1주)
  ├─ 데이터 탐색 + LLM 추출 PoC (2~3주)
  └─ 인프라 셋업 + 의사결정 (1~2주)

Phase 1: MVP 파이프라인                       (11~13주)
  ├─ 코드 리팩토링 (2~3일)
  ├─ 전처리 모듈 (3주)
  ├─ CompanyContext + CandidateContext (5~6주)
  └─ Graph 적재 + MappingFeatures (3주)

버퍼: 1주

Phase 2: 전체 처리 + 크롤링 + 품질             (11~14주)
  ├─ 450K 이력서 전체 처리 (3~4주)
  ├─ 품질 평가 (3일, 병행)
  ├─ 크롤링 파이프라인 (4주)
  ├─ CompanyContext 보강 + 서빙 인터페이스 (1.5주)
  └─ 증분 처리 + 운영 인프라 + 인수인계 (2주)

Phase 3: 운영 최적화 (별도, 필요 시)
  ├─ ML Knowledge Distillation
  ├─ LLM 비용 최적화
  └─ Looker Studio 대시보드

첫 동작 데모: ~19주 (Phase 0~1 + 버퍼)
전체 완성:   ~27~33주
```

## GCP 핵심 서비스

| 역할 | GCP 서비스 |
|------|-----------|
| 배치 파이프라인 | Cloud Run Jobs |
| LLM 추출 | Anthropic Batch API (Claude Haiku 4.5) |
| 크롤링 LLM | Vertex AI Gemini (gemini-2.0-flash) |
| Embedding | Vertex AI Embedding (text-embedding-005) |
| Graph DB | Neo4j AuraDB (Free → Professional) |
| 데이터 웨어하우스 | BigQuery (처리 로그, 서빙 테이블, 크롤링 데이터) |
| 오브젝트 스토리지 | GCS (`gs://graphrag-kg-data/`) |
| 오케스트레이션 | Makefile (Phase 1) / Cloud Workflows (Phase 2+) / Cloud Scheduler |
| 모니터링 | BigQuery Saved Queries + Cloud Monitoring |
| 보안 | Secret Manager + IAM 최소 권한 |

## 예상 비용

| 시나리오 | 총비용 (인건비 포함) | 비고 |
|---------|---------------------|------|
| **A: Haiku Batch (권장)** | **~$8,825~9,225 (~1,209~1,264만원)** | 가성비 최적 |
| D: Gemini Flash | ~$8,229~8,629 (~1,127~1,182만원) | 최저 비용, 품질 검증 필요 |
| B: Sonnet Batch | ~$11,984~12,384 (~1,642~1,697만원) | 고품질 |

운영 단계: **월 $236~336**

## 관련 문서

| 경로 | 설명 |
|------|------|
| [`02.create-kg/plans/v7/`](../../02.knowledge_graph/results/extraction_logic/v7/) | KG 구축 파이프라인 설계 (추출 파이프라인, 모델 후보, 실행 계획) — 본 문서의 입력 |
| [`01.ontology/`](../../01.ontology/) | 온톨로지 정의 (Graph 스키마의 근거) |

## 읽는 순서 (처음 접하는 분)

1. **이 README** — 전체 그림 파악
2. **[`standard/2/00_overview.md`](2/00_overview.md)** — 아키텍처, DE/MLE 역할 분담, GCP 서비스 매핑, 의사결정 포인트
3. 관심 Phase의 상세 문서 (01 → 02 → 03 순서)
4. **[`standard/2/04_cost_monitoring_ops.md`](2/04_cost_monitoring_ops.md)** — 비용/모니터링/보안은 필요할 때 참조
5. **[`standard/2/05_models_and_methods.md`](2/05_models_and_methods.md)** — 모델/방법론 상세는 필요할 때 참조
