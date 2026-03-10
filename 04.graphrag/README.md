# GraphRAG GCP 코어 확장 실현 계획

GCP 환경에서 Knowledge Graph(KG) 기반 GraphRAG 시스템을 구축하기 위한 데이터 확장 기반 단계적 구축(core) 실현 계획 문서입니다.

## 이 문서는 무엇인가요?

[`02.create-kg/plans/v7/`](../../02.create-kg/plans/v7/)에 정의된 KG 구축 파이프라인 설계를 **GCP 인프라 위에서 실제로 구현하기 위한 에이전트 조회 역량 중심의 점진적 실행 계획**입니다.

- **무엇을 만드는가**: 이력서(500K)와 JD(10K)에서 LLM으로 정보를 추출하고, 기업 크롤링 데이터를 추가하여 Knowledge Graph를 구축하는 E2E 파이프라인. 특히 Core Candidate-Only MVP(DB 텍스트 기반)를 출발점으로 하여 데이터 레이어를 점진적으로 확장합니다.
- **어디에 만드는가**: GCP 단일 프로젝트(`graphrag-kg`) — Cloud Run Jobs, Anthropic Batch API, Neo4j AuraDB, BigQuery, Vertex AI Embedding, Cloud Run Service(API 서빙)
- **얼마나 걸리는가**: 약 27주 (Phase 0~4)

## 세 트랙 안내

본 계획은 **경량(light)**, **표준(standard)**, **코어(core)** 세 트랙으로 관리됩니다.

| 트랙 | 디렉토리 | 특징 | 총 일정 |
|------|----------|------|---------|
| **light (light)** | `light/` | 크롤링 후속 분리, Staged Fast Fail, 최소 서빙 | 16.5~17.5주 코어 |
| **standard (standard)** | `standard/` | 크롤링 포함, 증분 처리, 운영 인프라 완비 | 27~33주 |
| **core (core)** | `core/` | **에이전트 역량 중심 점진적 확장, DB MVP 선행, API 서빙 강화** | 27주 |

> 에이전트가 어떤 질문에 대답할 수 있는지를 기준으로 단계별 성장을 목표로 하는 코어 파이프라인 환경이 궁금하다면 본 문서를 계속 읽어주세요.

## 최신 버전: core.2

> **core.2를 읽으세요.** core.1은 참고용 히스토리입니다.

core.2는 core.1 리뷰를 반영하여 다음을 개선했습니다:

| 변경 | 내용 |
|------|------|
| Phase 2 연장 | 6주 → 8주 (80%+ 처리 완료 보장) |
| API 서빙 명시 | Phase 1에 에이전트 연동용 REST API 설계 1일 추가 |
| Org ER 확대 | 한국어 특화 및 검수 강화로 1주 → 2주 |
| 크롤링 분리 | 크롤링을 선택적으로 분리하여 DB-only MVP 가능 |
| Embedding 통일 | 전체 text-embedding-005 (768d) 로 통일 |
| Neo4j 최적화 | UNWIND 배치 처리 및 롤백 전략 도입 |
| 품질 자동화 | 자동 품질 메트릭 + 통계적 샘플링 추가 |
| 매칭 설계 문서 | Phase 3 초반에 매칭 알고리즘 설계 문서 작업 추가 (2일) |

## 문서 구조

### core.2 (최신) — `core/2/`

| 문서 | 내용 | 핵심 키워드 |
|------|------|-------------|
| [`00_overview.md`](results/implement_planning/core/2/00_overview.md) | 전체 구조, 에이전트 진화 로드맵, 변경점 | 점진적 확장, 에이전트 역량, REST API |
| [`01_phase0_setup_poc.md`](results/implement_planning/core/2/01_phase0_setup_poc.md) | Phase 0: GCP 환경 + LLM PoC (1주) | DB 텍스트 기반, Batch API 한도 |
| [`02_phase1_core_candidate_mvp.md`](results/implement_planning/core/2/02_phase1_core_candidate_mvp.md) | Phase 1: DB 텍스트 MVP + API 설계 (5주) | DB-only MVP, 우선 연동 |
| [`03_phase2_file_and_scale.md`](results/implement_planning/core/2/03_phase2_file_and_scale.md) | Phase 2: 파일 파싱 + 전체 이력서 처리 (8주) | 전체 모수 확장, 목표 80%+, 쿼리 벤치마크 |
| [`04_phase3_company_and_matching.md`](results/implement_planning/core/2/04_phase3_company_and_matching.md) | Phase 3: 기업 정보 + 후보자-JD 매칭 (7주) | 매칭 알고리즘, Organization ER |
| [`05_phase4_enrichment_and_ops.md`](results/implement_planning/core/2/05_phase4_enrichment_and_ops.md) | Phase 4: 크롤링 보강 + 품질 평가 + 운영 (4주) | CompanyContext 보강, Gold Test Set, 자동화 |
| [`06_cost_and_monitoring.md`](results/implement_planning/core/2/06_cost_and_monitoring.md) | 비용 추정 + 모니터링 + 운영 통합 | 예산 한도, 시나리오별 런북 |

### core.1 (히스토리) — `core/1/`

core.1은 DB 텍스트 중심의 Candidate-Only MVP를 최우선으로 하여 파이프라인을 구축하는 초기 로드맵입니다.

## 전체 타임라인 요약

```
사전 준비: Batch API/Gemini 한도 검증, PII 검토 (즉시)

Phase 0: 환경 + PoC                           (1주, Week 1)
  ├─ GCP 환경 구성 + 크롤링 분석
  └─ DB 텍스트 프로파일링 + LLM 추출 PoC

Phase 1: Core Candidate MVP                   (5주, Week 2-6)
  ├─ DB 텍스트 전처리 + 크롤링 파이프라인 (선택)
  ├─ CandidateContext LLM 추출 (1,000건)
  └─ Graph 적재 + 에이전트 API 제공 ★

Phase 2: 파일 이력서 + 전체 처리               (8주, Week 7-14)
  ├─ 리팩토링 + PDF/DOCX/HWP 파서
  ├─ 450K 전체 데이터 Batch 처리 (목표 80%+)
  └─ 자동 품질 메트릭 + 쿼리 성능 벤치마크

버퍼: 1주 (Week 15)

Phase 3: 기업 정보 + 매칭                      (7주, Week 16-22)
  ├─ 매칭 알고리즘 설계 + JD 파서
  ├─ CompanyContext + Organization ER
  └─ MappingFeatures + 통합 테스트

버퍼: 1주 (Week 23)

Phase 4: 외부 보강 + 품질 + 운영              (4주, Week 24-27)
  ├─ 홈페이지/뉴스 크롤링 (기업 정보 기본)
  ├─ Gold Test Set 품질 평가
  └─ 증분 자동화(Cloud Workflows) + 인수인계

Phase 5: 운영 최적화 (별도, 필요 시)
  └─ 기업 문화/텐션 신호 보강, ML 모델화 등

첫 에이전트 데모: Week 6  (Phase 0~1)
전체 완성:      Week 27
```

## GCP 핵심 서비스

| 역할 | GCP 서비스 |
|------|-----------|
| 배치 파이프라인 | Cloud Run Jobs |
| LLM 추출 | Anthropic Batch API (Claude Haiku 4.5) |
| 크롤링 LLM | Vertex AI Gemini (gemini-2.0-flash) |
| Embedding | Vertex AI Embedding (text-embedding-005) |
| Graph DB | Neo4j AuraDB (Free → Professional, UNWIND 배치 적재) |
| 데이터 웨어하우스 | BigQuery (처리 로그, 서빙 테이블) |
| 서빙 인터페이스 | **Cloud Run Service (GraphRAG REST API)** |
| 오케스트레이션 | Cloud Workflows (Phase 4 도입) + Cloud Scheduler |
| 모니터링 | BigQuery Saved Queries + Cloud Monitoring |
| 보안 | Secret Manager + 서비스 계정 분리 (최소 권한) |

## 예상 비용

| 시나리오 | 총비용 (LLM+인프라) | 비고 |
|---------|---------------------|------|
| **코어 전체 (Phase 0~4)** | **~$8,235~8,895 (~1,128~1,219만원)** | 초기 PoC부터 파일럿까지 |

운영 단계: **월 $300~500 수준** (에이전트 트래픽 한도 기준)

## 관련 문서

| 경로 | 설명 |
|------|------|
| [`02.create-kg/plans/v7/`](../../02.knowledge-engineering/results/implement_planning/v7/) | KG 구축 파이프라인 설계 (추출 파이프라인, 모델 후보, 실행 계획) — 본 문서의 입력 |
| [`01.ontology/`](../../01.ontology/) | 온톨로지 정의 (Graph 스키마의 근거) |

## 읽는 순서 (처음 접하는 분)

1. **이 README** — 전체 그림 파악
2. **[`core/2/00_overview.md`](results/implement_planning/core/2/00_overview.md)** — 에이전트 진화 로드맵, 데이터 확장 순서, DE/MLE 역할, 의사결정 포인트
3. 관심 Phase의 상세 문서 (01 → 02 → 03 → 04 → 05 순서)
4. **[`core/2/06_cost_and_monitoring.md`](results/implement_planning/core/2/06_cost_and_monitoring.md)** — 비용/모니터링/보안/Runbook은 필요할 때 참조
