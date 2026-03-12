# GraphRAG GCP 구현 계획 — S&F / GraphRAG 2팀 분리 실행

> 현재 유효 버전: **separate/v3** (2026-03-12)

## 이 문서는 무엇인가요?

`01.ontology/v20/`에서 정의한 온톨로지(what to represent)와 `02.knowledge_graph/v13/`의 추출 로직(how to build)을 기반으로, **GCP 인프라 위에서 실제로 구현하고 서빙하기 위한 실행 계획**(how to serve)입니다.

- **무엇을 만드는가**: 이력서(500K)와 JD(10K)에서 LLM으로 정보를 추출하고, 기업 크롤링 데이터를 추가하여 Knowledge Graph를 구축하는 E2E 파이프라인 + 5-피처 매칭 시스템
- **어디에 만드는가**: GCP 단일 프로젝트(`graphrag-kg`) — Cloud Run Jobs, Anthropic Batch API, Neo4j AuraDB, BigQuery, Vertex AI Embedding, Cloud Run Service(API 서빙)
- **얼마나 걸리는가**: 약 27주 (S&F ~22주, GraphRAG ~18주, 병렬 실행)
- **누가 만드는가**: **S&F 팀** (아티팩트 처리) + **GraphRAG 팀** (그래프 적재/매칭)

---

## 계획 구조: 2팀 분리 (separate/v3)

core.5 단일 실행계획을 **S&F 팀**과 **GraphRAG 팀**으로 분리하고, 팀 간 Data Contract + PubSub 기반 인터페이스를 정의합니다.

```
separate/v3/
├── graphrag/          ← GraphRAG 팀 실행계획 (Neo4j 적재, 매칭, 서빙)
├── sf/                ← S&F 팀 실행계획 (추출, 전처리, 벡터 검색)
└── interface/         ← 팀 간 공유 (Data Contract, Go/No-Go, 정책, 로드맵)
```

### 핵심 원칙

S&F 팀과 GraphRAG 팀은 **Data Contract(JSON) + Event(PubSub)**으로만 결합합니다.
- S&F는 "그래프가 어떻게 구조화/매칭되는지" 알 필요 없음
- GraphRAG는 "텍스트가 어떻게 파싱/벡터화되었는지" 알 필요 없음

### 2-Tier API SLA

| 구간 | p95 | 담당 |
|------|-----|------|
| S&F API (하드필터+벡터) | < 500ms | S&F |
| GraphRAG API (IN-list 매칭) | < 2s | GraphRAG |
| **전체 체인** | **< 3s** | 공동 |

---

## 문서 구조

### GraphRAG 팀 — `graphrag/`

Neo4j 지식 그래프 적재, 5-피처 매칭 알고리즘, API 서빙을 담당합니다.

| # | 파일 | Phase | 내용 |
|---|------|-------|------|
| 0 | `00_graphrag_overview.md` | — | Gantt, Work/Wait, Go/No-Go, S&F 수신 포인트 |
| 1 | `01_graphrag_g0_setup.md` | G-0 (W1) | Neo4j AuraDB Free + 스키마 + 선행 작업 |
| 2 | `02_graphrag_g1_mvp.md` | G-1 (W5~6) | 1K 적재 + Cypher 5종 + REST API + PII 미들웨어 |
| 3 | `03_graphrag_g2_scale.md` | G-2 (W10~11) | AuraDB Professional 마이그레이션 + 사이징 + 벤치마크 |
| 4 | `04_graphrag_g3_matching.md` | G-3 (W17~22) | 5-피처 스코어링 + Vacancy 적재 + Organization ER + 가중치 튜닝 |
| 5 | `05_graphrag_g4_ops.md` | G-4 (W24~26) | 증분 처리 + Gold Label + 운영 Runbook |
| 6 | `06_graphrag_cost.md` | — | GraphRAG 비용 SSOT (~$3,427~6,777) |
| 7 | `07_neo4j_schema.md` | — | Cypher 쿼리 Q1-Q5, Vector Index, MAPPED_TO TTL, 노드/엣지 규모 |
| 8 | `08_serving.md` | — | BigQuery 서빙 스키마, freshness_weight 서빙 로직 |
| 9 | `09_evaluation.md` | — | GraphRAG vs Vector Baseline 비교 실험, 성공 기준 |

> 07~09는 v20 온톨로지에서 구현 상세를 분리하여 이동한 문서입니다.

### S&F 팀 — `sf/`

비정형 데이터를 정형 아티팩트(JSON)로 변환하고, 하드 필터 + 벡터 검색으로 1차 후보군을 제공합니다.

| # | 파일 | 주차 | 내용 |
|---|------|------|------|
| 0 | `00_sf_overview.md` | — | 전체 타임라인, 6범주 담당 범위, 산출물 5종 |
| 1 | `01_sf_phase0_poc.md` | W0~1 | GCP 환경, DB 프로파일링, LLM PoC 20건 |
| 2 | `02_sf_phase1_preprocessing.md` | W2~5 | PII 마스킹, CMEK, 적응형 LLM 1,000건 추출 |
| 3 | `03_sf_phase2_file_and_batch.md` | W7~15 | PDF/DOCX/HWP 파서, 600K Batch 처리 |
| 4 | `04_sf_phase3_jd_company.md` | W17~18 | JD 파싱, CompanyContext 추출 |
| 5 | `05_sf_phase4_crawling.md` | W24~25 | 홈페이지/뉴스 크롤링, 기업 보강 |
| 6 | `06_sf_cost.md` | — | S&F 비용 SSOT (~$1,955) |

### 인터페이스 — `interface/`

두 팀 간의 계약, 의사결정 기준, 공유 정책을 정의합니다.

| # | 파일 | 내용 |
|---|------|------|
| 0 | `00_data_contract.md` | PubSub 토픽 스키마, JSON 3종, 산출물 5종 교환 스펙, 서비스 계정 보안 |
| 1 | `01_go_nogo_decisions.md` | Phase별 Go/No-Go 기준, 의사결정 14건, 주간 싱크 회의 |
| 2 | `02_tasks.md` | 73개 태스크 분류 (S&F 35, GraphRAG 29, 공동 9) |
| — | `regeneration_policy.md` | CompanyContext/CandidateContext 재생성 트리거 (ontology v20에서 이동) |
| — | `implementation_roadmap.md` | 4-Phase 구현 로드맵 + LLM 비용 추정 (~$484) (ontology v20에서 이동) |

---

## 전체 타임라인 요약

```
Phase 0: 환경 + PoC                              (1주, W1)
  ├─ [S&F] GCP 환경 + DB 프로파일링 + LLM PoC
  └─ [GraphRAG] Neo4j AuraDB 환경 구성

Phase 1: Core Candidate MVP                      (5주, W2~6)
  ├─ [S&F] PII 마스킹 + LLM 추출 1,000건
  ├─ [GraphRAG] API 골격 + 선행 작업 (W2~4, 대기)
  └─ [GraphRAG] G-1: 1K 적재 + Cypher + REST API ★

Phase 2: 파일 이력서 + 전체 처리                    (9주, W7~15)
  ├─ [S&F] PDF/DOCX/HWP 파서 + 600K Batch
  └─ [GraphRAG] G-2: 대량 적재 + AuraDB Pro + 벤치마크

Phase 3: 기업 정보 + 매칭                           (6주, W17~22)
  ├─ [S&F] JD 파싱 + CompanyContext
  └─ [GraphRAG] G-3: 5-피처 매칭 + Vacancy + ER + 튜닝

Phase 4: 외부 보강 + 운영                           (4주, W24~27)
  ├─ [S&F] 홈페이지/뉴스 크롤링
  └─ [GraphRAG] G-4: 증분 처리 + Gold Label + 운영

첫 에이전트 데모: Week 6  (Phase 0~1)
전체 후보자 검색: Week 15 (480K+ Candidate Graph, 80%+)
기업-후보자 매칭: Week 22 (+ Company + Matching)
프로덕션 운영:   Week 27 (+ 외부 보강 + 자동화)
```

---

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
| 오케스트레이션 | Cloud Workflows + Cloud Scheduler |
| 이벤트 | PubSub (S&F → GraphRAG 산출물 전달) |
| 모니터링 | BigQuery Saved Queries + Cloud Monitoring |
| 보안 | Secret Manager + 서비스 계정 분리 (최소 권한) |

---

## 예상 비용

| 팀 | 비용 SSOT | 총비용 |
|----|----------|--------|
| S&F | `sf/06_sf_cost.md` | ~$1,955 |
| GraphRAG | `graphrag/06_graphrag_cost.md` | ~$3,427~6,777 |
| **합계** | — | **~$5,382~8,732** |

운영 단계: **월 $300~500 수준** (에이전트 트래픽 한도 기준)

---

## 관련 문서

| 경로 | 설명 |
|------|------|
| `01.ontology/v20/` | v20 온톨로지 — 순수 스키마 정의 (what to represent) |
| `02.knowledge_graph/v13/` | v13 추출 로직 — 파이프라인, 프롬프트, PII, 정규화 (how to build) |

---

## 버전 이력

| 버전 | 구조 | 주요 변경 |
|------|------|-----------|
| core.1~5 | 단일 실행계획 | 에이전트 역량 중심 점진적 확장, DB MVP 선행, 27주 |
| separate/v1 | 2팀 분리 (초안) | core.5를 S&F/GraphRAG로 분리, Data Contract 정의 |
| separate/v2 | 2팀 분리 (리뷰 반영) | 리스크 관리, Go/No-Go 기준 보강 |
| **separate/v3** | **2팀 분리 (현재)** | **ontology v20에서 Neo4j 스키마/서빙/평가 전략 통합, 재생성 정책/로드맵 추가** |

---

## 읽는 순서 (처음 접하는 분)

1. **이 README** — 전체 그림, 2팀 분리 구조 파악
2. **`interface/00_data_contract.md`** — 두 팀이 어떻게 연결되는지
3. **`graphrag/00_graphrag_overview.md`** 또는 **`sf/00_sf_overview.md`** — 관심 팀의 전체 타임라인
4. 관심 Phase의 상세 문서
5. **`graphrag/06_graphrag_cost.md`** + **`sf/06_sf_cost.md`** — 비용은 필요할 때 참조
