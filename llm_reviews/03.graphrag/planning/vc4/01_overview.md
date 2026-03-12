# VC4 — 팀 분리 아키텍처 개요

> **핵심 원칙**: 하드필터·PII·파싱·임베딩은 S&F 팀이, Chapter 기반 그래프 관계·매칭은 GraphRAG 팀이 전담한다.

---

## 1. 분리 배경

v5(27주)는 DE 1 + MLE 1이 전 파이프라인을 일괄 수행한다. 문제:
1. Phase 2(9주) 대부분은 파일 파서·LLM 600K·임베딩 등 **그래프와 무관한 ETL**
2. Phase 3에서도 JD 파싱·CompanyContext LLM 추출이 선행되어야 매칭 착수 가능
3. GraphRAG 핵심 역량(`[NEXT_CHAPTER]` 패턴, 5-피처 매칭)이 ETL에 희석

**Polyglot Persistence**: S&F는 RDB/Vector DB에, GraphRAG는 Neo4j에 최적화된 저장소를 독립 운영. 두 시스템은 **Data Contract(JSON)와 Event(PubSub)**로만 결합하며, GraphRAG는 "텍스트가 어떻게 파싱/벡터화되었는지"를 전혀 알 필요가 없다.

---

## 2. 팀 역할 정의

### 2.1. S&F 아티팩트 처리팀 — Recall (1차 탐색)

> "비정형 데이터를 정형 아티팩트로 변환하고, 하드 필터 + 벡터 검색으로 1차 후보군을 뽑는다."
> **SLA 책임: 하드필터+벡터 검색 API p95 < 500ms**

| 범주 | 담당 업무 |
|------|---------|
| **데이터 수집** | DB export, 크롤링(법무 허용 시), 홈페이지/뉴스 크롤링 |
| **전처리** | PII 마스킹(re.sub 콜백, 전화번호 8종), CMEK 버킷·KMS, Career 블록 분리 |
| **파일 파싱** | PDF/DOCX/HWP 파서, Hybrid 섹션 분리(패턴→LLM 폴백) |
| **LLM 추출** | CandidateContext(적응형 1-pass/N+1), CompanyContext(DB+NICE+LLM), Provider 추상화 |
| **임베딩+벡터** | Vertex AI 768d 생성, Vector DB 관리 |
| **Batch 운영** | 600K 처리, DB 500K→파일 100K 우선순위 |
| **품질 메트릭** | schema 준수율 ≥95%, 필드 완성도 ≥90%, PII 누출율 ≤0.01% |
| **하드 필터 API** | 스킬/연차/학력/시니어리티 필터 + 벡터 검색 → **ID Top 500~1,000건** |

### 2.2. GraphRAG 팀 — Precision (정밀 랭킹)

> "S&F가 정제한 아티팩트를 지식 그래프로 적재하고, Chapter 관계 패턴 기반의 정밀 매칭·랭킹을 수행한다."
> **SLA 책임: IN-list 그래프 매칭 API p95 < 2s**

| 범주 | 담당 업무 |
|------|---------|
| **그래프 모델링** | Neo4j 스키마(v19), 인덱스 설계, UNWIND 배치 적재 |
| **그래프 적재** | Person/Chapter/Skill/Role/Organization/Industry 노드·엣지, **NEXT_CHAPTER 연결** |
| **Neo4j 인프라** | AuraDB Free→Professional 전환, 사이징(N8), 백업 |
| **서빙 API** | GraphRAG REST API (검색 5종 + 매칭 + 기업 조회), PII 필터 미들웨어 |
| **매칭 알고리즘** | MappingFeatures 5-피처 스코어링, MAPPED_TO 관계 생성, 가중치 튜닝 |
| **Vacancy 그래프** | Vacancy/SituationalSignal 적재, Organization ER + 한국어 특화 |
| **증분 처리** | 변경 감지, DETACH DELETE 2단계, 소프트 삭제 마이그레이션 |
| **운영** | Cloud Scheduler, Workflows DAG, Runbook, Alarm |

### 2.3. Vector DB 선택 기준

| 조건 | 선택 | 근거 |
|------|------|------|
| Person < 1M, Chapter < 3M | Neo4j Vector Index 유지 | 인프라 단순, 복합 쿼리 가능 |
| Person ≥ 1M 또는 QPS > 50 | Milvus/Pinecone 외부화 | Neo4j 메모리 $50~100/월 절감 |
| **현재 v5 규모 (600K)** | **Neo4j 유지 권장** | S&F가 벡터 검색 API 별도 관리 |

---

## 3. 태스크 분류 집계

> 73개 태스크 상세: `v1/c_01_task_classification.md` 참조

| 팀 | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | **합계** |
|----|---------|---------|---------|---------|---------|--------|
| **S&F** | 10 | 8 | 10 | 6 | 1 | **35 (48%)** |
| **GraphRAG** | 1 | 7 | 4 | 7 | 10 | **29 (40%)** |
| **공동** | 2 | 1 | 2 | 3 | 1 | **9 (12%)** |
| **합계** | 13 | 16 | 16 | 16 | 12 | **73** |

---

## 4. Phase별 기간 비교

| Phase | v5 원본 | 분리 후 GraphRAG | 단축 근거 |
|-------|--------|----------------|---------|
| Phase 0 | 1주 | **0.5주** | LLM PoC·Embedding은 S&F |
| Phase 1 | 5주 | **2주** | 전처리·LLM 추출 S&F 이관 |
| Phase 2 | 9주 | **2주** | 파서·600K Batch·품질 S&F |
| Phase 3 | 6주 | **4주** | JD 파싱·CompanyContext S&F |
| Phase 4 | 4주 | **3주** | 크롤링·보강 S&F |
| 버퍼 | 2주 | **1주** | — |
| **합계** | **27주** | **캘린더 ~12.5주** | 순수 작업 ~8주 + 대기 ~4.5주 |
