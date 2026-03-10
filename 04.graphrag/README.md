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

## 최신 버전: core.5

> **core.5를 읽으세요.** core.5는 v4 리뷰를 반영한 최종 실행 버전입니다. core.1~4는 참고용 히스토리입니다.

core.5는 core.4 리뷰(S1 + A1~A4)를 반영하여 다음을 개선했습니다:

| 변경 | 내용 |
|------|------|
| 비용 수치 통일 (S1) | Overview 비용을 06_cost §1.6 기준으로 통일 ($5,527~9,137) |
| JD 파서 API 스펙 (A1) | Phase 3 시작 전 job-hub API 스펙 확정 여부 인지 사항 추가 |
| Go/No-Go 비용 외삽 (A2) | PoC 20건 토큰 사용량 → 600K 비용 외삽 기준 추가 |
| AuraDB 마이그레이션 (A3) | Cypher 복사 ~30분 + Vector Index 재생성 절차 명시 |
| Cloud Run cold start (A4) | Phase 4 운영 전환 시 min-instances 또는 Scheduler 30분 주기 |
| mask_phones() 안전성 (U2) | 토큰 형식 변경 시 다중 패턴 간섭 확인 필요 주석 추가 |

> **결론**: v4 리뷰에서 "추가 리비전(v5) 불필요, 실행 단계 즉시 진입 가능"으로 판정. v5는 S1(비용 동기화) + A1~A4(인지 사항 문서화)만 반영한 최종 실행 버전.

## 문서 구조

### core.5 (최신, 최종 실행 버전) — `core/5/`

| 문서 | 내용 | 핵심 키워드 |
|------|------|-------------|
| [`00_overview.md`](results/implement_planning/core/5/00_overview.md) | 전체 구조, v4→v5 변경점, 데이터 확장 로드맵 | 점진적 확장, 에이전트 역량, 비용 통일 |
| [`01_phase0_setup_poc.md`](results/implement_planning/core/5/01_phase0_setup_poc.md) | Phase 0: GCP 환경 + LLM PoC (1주) | DB 텍스트 기반, PoC 비용 외삽 |
| [`02_phase1_core_candidate_mvp.md`](results/implement_planning/core/5/02_phase1_core_candidate_mvp.md) | Phase 1: DB 텍스트 MVP + API 설계 (5주) | DB-only MVP, PII 필드 정의 |
| [`03_phase2_file_and_scale.md`](results/implement_planning/core/5/03_phase2_file_and_scale.md) | Phase 2: 파일 파싱 + 전체 이력서 처리 (**9주**) | 전체 모수 확장, 목표 80%+, DB 500K 우선 |
| [`04_phase3_company_and_matching.md`](results/implement_planning/core/5/04_phase3_company_and_matching.md) | Phase 3: 기업 정보 + 후보자-JD 매칭 (**6주**) | 매칭 알고리즘, JD 파서 API 스펙 |
| [`05_phase4_enrichment_and_ops.md`](results/implement_planning/core/5/05_phase4_enrichment_and_ops.md) | Phase 4: 크롤링 보강 + 품질 평가 + 운영 (4주) | Cold start 대응, 증분 2단계 통합 |
| [`06_cost_and_monitoring.md`](results/implement_planning/core/5/06_cost_and_monitoring.md) | 비용 추정 (**Single Source of Truth**) + 모니터링 + 운영 | $5,527~9,137, 시나리오별 런북 |

### core.4 (히스토리) — `core/4/`

core.4는 core.3 리뷰(R1~R8)를 반영하여 PII 마스킹 수정, Phase 2→9주/Phase 3→6주 재배분, DB 500K 우선 처리 등을 적용한 버전입니다.

### core.3 (히스토리) — `core/3/`

core.3은 v12 온톨로지 + v19 관계명을 반영하고 적응형 LLM 호출, Hybrid 섹션 분리 등을 도입한 버전입니다.

### core.2 (히스토리) — `core/2/`

core.2는 Phase 2 연장(6→8주), API 서빙 명시, Embedding 통일, UNWIND 배치 처리 등을 도입한 버전입니다.

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

Phase 2: 파일 이력서 + 전체 처리               (9주, Week 7-15)
  ├─ 리팩토링 + PDF/DOCX/HWP 파서
  ├─ 600K 전체 데이터 Batch 처리 (목표 80%+, DB 500K 우선)
  └─ 자동 품질 메트릭 + 쿼리 성능 벤치마크

버퍼: 1주 (Week 16)

Phase 3: 기업 정보 + 매칭                      (6주, Week 17-22)
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
전체 후보자 검색: Week 15 (480K+ Candidate Graph, 80%+)
기업-후보자 매칭: Week 22 (+ Company + Matching)
프로덕션 운영:   Week 27 (+ 외부 보강 + 자동화)
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

> 비용 Single Source of Truth: `06_cost_and_monitoring.md` §1

| 시나리오 | 총비용 (LLM+인프라) | 비고 |
|---------|---------------------|------|
| **코어 전체 (Phase 0~4)** | **~$5,527~9,137 (~758~1,253만원)** | 06_cost §1.6 기준 |

운영 단계: **월 $300~500 수준** (에이전트 트래픽 한도 기준)

## 관련 문서

| 경로 | 설명 |
|------|------|
| [`02.create-kg/plans/v7/`](../../02.knowledge-engineering/results/implement_planning/v7/) | KG 구축 파이프라인 설계 (추출 파이프라인, 모델 후보, 실행 계획) — 본 문서의 입력 |
| [`01.ontology/`](../../01.ontology/) | 온톨로지 정의 (Graph 스키마의 근거) |

## 읽는 순서 (처음 접하는 분)

1. **이 README** — 전체 그림 파악
2. **[`core/5/00_overview.md`](results/implement_planning/core/5/00_overview.md)** — 에이전트 진화 로드맵, 데이터 확장 순서, DE/MLE 역할, 의사결정 포인트
3. 관심 Phase의 상세 문서 (01 → 02 → 03 → 04 → 05 순서)
4. **[`core/5/06_cost_and_monitoring.md`](results/implement_planning/core/5/06_cost_and_monitoring.md)** — 비용/모니터링/보안/Runbook은 필요할 때 참조
