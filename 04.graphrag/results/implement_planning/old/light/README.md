# GraphRAG GCP 경량 실현 계획

GCP 환경에서 Knowledge Graph(KG) 기반 GraphRAG 시스템을 구축하기 위한 경량(light) 실현 계획 문서입니다.

## 이 문서는 무엇인가요?

[`02.knowledge_graph/results/extraction_logic/v7/`](../../02.knowledge_graph/results/extraction_logic/v7/)에 정의된 KG 구축 파이프라인 설계를 **GCP 인프라 위에서 실제로 구현하기 위한 단계별 실행 계획**입니다.

- **무엇을 만드는가**: 이력서(500K)와 JD(10K)에서 LLM으로 정보를 추출하여 Knowledge Graph를 구축하고, 후보자-공고 매칭 피처를 생성하는 E2E 파이프라인
- **어디에 만드는가**: GCP 단일 프로젝트(`graphrag-kg`) — Cloud Run Jobs, Anthropic Batch API, Neo4j AuraDB, BigQuery, Vertex AI Embedding
- **얼마나 걸리는가**: 약 16.5~17.5주 코어 / Pre-Phase 포함 18.5~20.5주 (80% 가용률 시 ~22~25주)

## 세 트랙 안내

본 계획은 **경량(light)**, **표준(standard)**, **코어(core)** 세 트랙으로 관리됩니다.

| 트랙 | 디렉토리 | 특징 | 총 일정 |
|------|----------|------|---------|
| **light (light)** | `light/` | 크롤링 후속 분리, Staged Fast Fail, 최소 서빙 | 16.5~17.5주 코어 |
| **standard (standard)** | `standard/` | 크롤링 포함, 증분 처리, 운영 인프라 완비 | 27~33주 |
| **core (core)** | `core/` | **에이전트 역량 중심 점진적 확장, DB MVP 선행, API 서빙 강화** | 27주 |

> 전체 프로덕션 통합 파이프라인 여정이 궁금하다면 [`README.standard.md`](../standard/README.md)를, 에이전트 진화 중심의 점진적 파이프라인이 궁금하다면 [`README.core.md`](../../../../README.md)를 참조하세요.

## 최신 버전: light.2

> **light/2를 읽으세요.** 이전 버전은 참고용 히스토리입니다.

light.2는 light.1의 **Staged Fast Fail** 철학을 유지하면서, 리뷰를 통해 개발 시간 추정의 정밀도를 높인 **현실적 타임라인 보정판**으로 다음을 개선했습니다:

| 변경 | 내용 |
|------|------|
| [light.2-1] Pre-Phase 0 명시 | 법무 PII + Batch API quota + 데이터 전송 테스트 (2~3주) 전체 타임라인에 포함 |
| [light.2-2] Phase 1-C 확대 | 1주 → **2주** (Org ER 한국어 회사명 + 모듈 개발 시간) |
| [light.2-3] 프롬프트 튜닝 시간 | Phase 1-B에 **+0.5주** 전용 시간 추가 |
| [light.2-4] 통합 테스트 버퍼 | Phase 1-A에 **+0.5주** 버퍼 추가 |
| [light.2-5] 테스트 기간 확정 | Phase 1-D **1주 확정** (0.5주 옵션 제거) |
| [light.2-6] Cloud Workflows 제거 | Phase 2에서 제거 → **Makefile + 스크립트** 유지, 후속 프로젝트로 이관 |
| [light.2-7] 3-시나리오 타임라인 | Batch API 응답 시간 낙관/기본/비관 시나리오 반영 |
| [light.2-8] Gold Test Set 선행 | Phase 1 후반(Week 11~12)부터 라벨링 시작 |
| [light.2-9] 80% 가용률 시나리오 | 인력 가용률 80% 기준 병행 제시 |
| [light.2-10] Dead-letter 격상 | 별도 **0.5주** 태스크로 격상 |
| [light.2-11] Embedding QPM 확인 | Vertex AI QPM/TPM 한도 확인을 Phase 0에 추가 |
| [light.2-12] Document AI 격하 | Document AI 검증을 선택적(nice-to-have)으로 격하 |
| [light.2-13] 도메인 전문가 투입 명시 | 도메인 전문가 주차별 투입 시간 명시 |
| [light.2-14] 20% contingency | 예산에 20% contingency 추가 |
| [light.2-15] 데이터 전송 테스트 | 10GB 샘플 전송 테스트를 Pre-Phase 0에 추가 |

> **light.1에서 유지하는 핵심 개념:** Fast Fail 부적합 분석, Go/No-Go 게이트 6개 의사결정, Checkpoint/재시작 전략, pytest + regression test, LLM 파싱 3-tier, Makefile 오케스트레이션, 크롤링 후속 분리, 한국어 토큰 보정(x1.88)

## 문서 구조

### light.2 (최신) — `light/2/`

| 문서 | 내용 | 핵심 키워드 |
|------|------|-------------|
| [`00_fast_fail_analysis.md`](2/00_fast_fail_analysis.md) | Fast Fail 전략 부적합 분석 (light.1와 동일) | 품질 신호, 직렬 의존성, 규모 전환, Staged Fast Fail |
| [`01_overview.md`](2/01_overview.md) | 전체 구조, 타임라인, 의사결정 포인트, 인력 배치 | 아키텍처, 80% 가용률, 3-시나리오, DAG |
| [`02_phase0_validation_poc.md`](2/02_phase0_validation_poc.md) | Pre-Phase 0 + Phase 0: 사전 준비 + API 검증 + PoC (2~3주 + 2.5주) | 법무 PII, Batch API quota, 4개 병렬 트랙, Embedding QPM |
| [`03_phase1_mvp_pipeline.md`](2/03_phase1_mvp_pipeline.md) | Phase 1: MVP 파이프라인 (9주) | 전처리/CompanyCtx 병행, 프롬프트 튜닝, Org ER, Gold Set 선행 |
| [`04_phase2_full_processing.md`](2/04_phase2_full_processing.md) | Phase 2: 전체 데이터 처리 + 품질 평가 (5~6주) | 450K 처리, Neo4j Professional, Dead-letter, Makefile |
| [`05_cost_monitoring.md`](2/05_cost_monitoring.md) | 비용 추정 + 최소 모니터링 | 20% contingency, 가격 변동 리스크, Gold Label 산출 근거 |

### light.1 (이전) — `light/1/`

light.2의 기반. Staged Fast Fail 최초 도입, 12~14주 코어 타임라인.

### standard (standard 트랙) — `standard/`

| 버전 | 내용 |
|------|------|
| `standard/1/` | 크롤링 + 증분 + 운영 포함 표준 계획 (v3 계열) |
| `standard/2/` | standard.1 리뷰 반영 보정판 (v3-1 계열, 27~33주) |

> standard 트랙 상세는 [`README.standard.md`](../standard/README.md) 참조.

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
Pre-Phase 0: 사전 준비 (2~3주, Phase 0과 독립)
  ├─ 법무 PII 검토 요청 (1~3주)                ──┐
  ├─ Batch API quota/Tier 확인 (1~2주)          ──┤ 완전 병렬
  ├─ 데이터 전송 테스트 (10GB 샘플, 1일)          ──┤
  └─ 도메인 전문가 확보 확인                     ──┘

Phase 0: 기반 구축 + API 검증 + PoC (2.5주)
  ├─ 0-A: GCP 환경 + API 검증 (3일)          ──┐
  ├─ 0-B: 데이터 탐색 + 프로파일링 (1주)       ──┤ 완전 병렬
  ├─ 0-C: LLM 추출 PoC (1.5주)               ──┤
  └─ 0-D: 인프라 셋업 (1주)                   ──┘
  → Week 2.5: 의사결정 완료

Phase 1: MVP 파이프라인 (9주)
  ├─ 1-A: 전처리 + CompanyContext (2.5주, 병행)
  ├─ 1-B: CandidateContext (3.5주, +프롬프트 튜닝)
  ├─ 1-C: Graph + Embedding + Mapping (2주, +Org ER)
  └─ 1-D: 테스트 + 검증 + 백업 (1주)
  → Week 14: MVP 1,000건 E2E 동작
  → Week 11~12: Gold Test Set 라벨링 선행 시작

Phase 2: 전체 처리 + 품질 평가 (5~6주)
  ├─ 2-0: Neo4j Professional 전환 (1일)
  ├─ 2-A: 450K Batch 처리 (3~4주)              ──┐
  ├─ 2-B: 품질 평가 (0.5주, Gold Set 선행 완료)  ──┤ 병렬
  ├─ 2-C: Graph 전체 적재 + Embedding (1~2주)   ──┤
  ├─ 2-D: Dead-letter 재처리 (0.5주)            ──┤
  └─ 2-E: 최소 서빙 인터페이스 (0.5주)          ──┘
  → Week 19~20: 전체 KG 완성 + 품질 리포트

후속 프로젝트 (별도):
  ├─ 크롤링 파이프라인 (4주)
  ├─ 증분 처리 + 운영 자동화 (2주)
  ├─ Cloud Workflows 도입 (1주)
  └─ Knowledge Distillation (선택)

코어 일정:     ~16.5~17.5주
Pre-Phase 포함: ~18.5~20.5주
80% 가용률:    ~22~25주
첫 MVP 데모:   ~14주 (Pre 포함 ~16~17주)
```

## 인력 가용률 시나리오

| 시나리오 | 코어 기간 | Pre-Phase 포함 | 첫 MVP 데모 |
|----------|----------|---------------|------------|
| **100% 풀타임** | 16.5~17.5주 | 18.5~20.5주 | ~14주 (Pre 포함 ~16~17주) |
| **80% 가용 (권장 기준)** | ~20~22주 | ~22~25주 | ~17주 (Pre 포함 ~19~21주) |

## light.1 대비 일정 비교

| Phase | light.1 | light.2 | 차이 | 사유 |
|-------|------|------|------|------|
| Pre-Phase 0 | (미포함) | **2~3주** | +2~3주 | 법무 PII + Batch API + 데이터 전송 |
| Phase 0 | 2.5주 | **2.5주** | 0 | Document AI 축소 → Embedding QPM 교체 |
| Phase 1 | 6.5~7주 | **9주** | +2~2.5주 | 통합 테스트, 프롬프트 튜닝, Org ER, 테스트 확정 |
| Phase 2 | 4~5주 | **5~6주** | +1주 | Dead-letter + 품질 미달 버퍼 |
| **코어 합계** | **13~15주** | **16.5~17.5주** | +2.5~3.5주 | |
| **Pre-Phase 포함** | **13~15주** | **18.5~20.5주** | +5.5주 | |

## GCP 핵심 서비스

| 역할 | GCP 서비스 |
|------|-----------|
| 배치 파이프라인 | Cloud Run Jobs |
| LLM 추출 | Anthropic Batch API (Claude Haiku 4.5) |
| LLM PoC/비교 | Anthropic API (Claude Sonnet 4.6) |
| Embedding | Vertex AI (text-embedding-005 standard gemini-embedding-001) |
| Graph DB | Neo4j AuraDB (Free → Professional) |
| 데이터 웨어하우스 | BigQuery (처리 로그, batch_tracking, 서빙 테이블) |
| 오브젝트 스토리지 | GCS (`gs://graphrag-kg-data/`, Object Versioning) |
| 오케스트레이션 | Makefile + 모니터링 스크립트 (Phase 1 AND Phase 2) |
| 보안 | Secret Manager + IAM 최소 권한 |
| 모니터링 | Cloud Monitoring (Cloud Run Job 실패 알림) + BigQuery 직접 쿼리 |

## 예상 비용

| 시나리오 | Phase 0 | Phase 1 | Phase 2 LLM | Phase 2 인프라 | Gold Label | **소계** | **+20% Contingency** |
|---|---|---|---|---|---|---|---|
| **A: Haiku Batch (권장)** | $83 | $42 | $1,739 | ~$200 | $2,920 | **~$4,984** | **~$5,981** |
| D: Gemini Flash | $83 | $42 | 낮음 | ~$200 | $2,920 | **~$4,300** | **~$5,160** |
| B: Sonnet Batch | $83 | $42 | +LLM | ~$200 | $2,920 | **~$5,500** | **~$6,600** |

> 환율 기준: $1 = 1,370원. 권장 시나리오 A 기준 **~683만원** (contingency 포함 ~819만원)

## 후속 프로젝트 (light.2 이후)

| 항목 | 예상 기간 | 의존성 |
|------|----------|-------|
| 크롤링 파이프라인 (홈페이지+뉴스) | 4주 | light.2 CompanyContext 스키마 |
| 크롤링 → CompanyContext 보강 | 1주 | 크롤링 파이프라인 |
| Cloud Workflows 오케스트레이션 | 1주 | light.2 E2E 파이프라인 |
| 증분 처리 자동화 (Cloud Scheduler) | 1주 | Cloud Workflows |
| Looker Studio 대시보드 | 1주 | BigQuery 테이블 |
| ML Knowledge Distillation | 2주 | light.2 품질 평가 결과 |
| DS/MLE 서빙 인터페이스 확장 | 1주 | light.2 mapping_features |

## 관련 문서

| 경로 | 설명 |
|------|------|
| [`02.create-kg/plans/v7/`](../../02.knowledge_graph/results/extraction_logic/v7/) | KG 구축 파이프라인 설계 (추출 파이프라인, 모델 후보, 실행 계획) — 본 문서의 입력 |
| [`01.ontology/`](../../01.ontology/) | 온톨로지 정의 (Graph 스키마의 근거) |

## 읽는 순서 (처음 접하는 분)

1. **이 README** — 전체 그림 파악
2. **[`light/2/00_fast_fail_analysis.md`](2/00_fast_fail_analysis.md)** — Fast Fail이 왜 안 되는지 이해 (선택적)
3. **[`light/2/01_overview.md`](2/01_overview.md)** — 아키텍처, 타임라인, 인력 배치, 의사결정 포인트
4. 관심 Phase의 상세 문서 (02 → 03 → 04 순서)
5. **[`light/2/05_cost_monitoring.md`](2/05_cost_monitoring.md)** — 비용/모니터링/보안은 필요할 때 참조
