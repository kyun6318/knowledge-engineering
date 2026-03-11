# GraphRAG v5 실행계획 — 팀 분리 계획서 v2 (S&F / GraphRAG)

> **버전**: v2 (v1 c계열 기반 + g계열 리뷰 반영)
> **작성일**: 2026-03-12
> **기준 문서**: `04.graphrag/results/implement_planning/core/5/` (v5 최종, 7개 문서)
> **v1 대비 변경**: I1~I5 개선 반영 (상세 → `00_review_and_analysis.md`)

---

## 1. 분리 배경

v5 실행계획은 DE 1명 + MLE 1명이 **전처리(PII/파싱/LLM 추출/임베딩)부터 그래프 적재·매칭·서빙까지** 전 파이프라인을 일괄 수행하는 구조이다.

이 구조의 문제점:
1. Phase 2(9주)의 대부분은 **파일 파서 구축(PDF/DOCX/HWP)**, **LLM Batch 600K 호출**, **임베딩 생성** 등 그래프와 직접 관계없는 아티팩트 처리 작업이다.
2. Phase 3에서도 **JD 파싱**, **NICE 기업정보 조회**, **CompanyContext LLM 추출** 등이 선행되어야 비로소 그래프 매칭 로직에 착수할 수 있다.
3. GraphRAG 팀의 핵심 역량(그래프 모델링, 관계 패턴 분석, 매칭 알고리즘)이 ETL성 작업에 묻혀 희석된다.

> ★ **v2 I3**: 분리를 통해 **Polyglot Persistence 아키텍처**를 도입한다. S&F는 RDB/Vector DB에, GraphRAG는 Neo4j에 최적화된 저장소를 각각 독립 운영하여, 각 DB의 주특기를 최대한 활용한다.

---

## 2. 팀 역할 정의

### 2.1. Search & Filter(S&F) 아티팩트 처리팀

> **한마디**: "비정형 데이터를 정형 아티팩트로 변환하고, 하드 필터 + 벡터 검색으로 1차 후보군을 뽑는다."

| 범주 | 담당 업무 |
|------|---------|
| **데이터 수집** | DB 데이터 export, 크롤링 파이프라인(법무 허용 시), 홈페이지/뉴스 크롤링 |
| **전처리** | PII 마스킹(re.sub 콜백, 전화번호 8종), CMEK 버킷·KMS 관리, Career 블록 분리 |
| **파일 파싱** | PDF/DOCX/HWP 파서, Hybrid 섹션 분리(패턴→LLM 폴백 Batch) |
| **LLM 추출** | CandidateContext 추출(적응형 1-pass/N+1), CompanyContext 추출(DB+NICE+LLM 3단계), LLM Provider 추상화 |
| **임베딩 + 벡터** | Vertex AI Embedding 생성(768d), Vector DB 관리 (★ v2 I2 참조) |
| **Batch 운영** | 600K Batch 처리, 우선순위 전략(DB 500K→파일 100K), 잔여 배치 소화 |
| **품질 메트릭** | schema 준수율, 필드 완성도, PII 누출율, 적응형 호출 비율 |
| **하드 필터 API** | 스킬/연차/학력/시니어리티 등 속성 기반 1차 필터링 + 벡터 검색 기능 제공 |

> ★ **v2 I2: Vector DB 선택 기준**
> | 조건 | 선택 | 근거 |
> |------|------|------|
> | Person < 1M, Chapter < 3M | Neo4j Vector Index 유지 | 인프라 단순, 복합 쿼리 가능 |
> | Person ≥ 1M 또는 Vector 요청 QPS > 50 | Milvus/Pinecone 외부화 | Neo4j 메모리 $50~100/월 절감 |
> | 현재 v5 규모 (600K Person) | **Neo4j 유지 권장** | 단, S&F가 벡터 검색 API를 별도 관리 |

### 2.2. GraphRAG 팀

> **한마디**: "S&F가 정제한 아티팩트를 지식 그래프로 적재하고, 관계 패턴 기반의 정밀 매칭·랭킹을 수행한다."

| 범주 | 담당 업무 |
|------|---------|
| **그래프 모델링** | Neo4j 스키마 설계(v19 관계명), 인덱스 설계, UNWIND 배치 적재 코드 |
| **그래프 적재** | Person/Chapter/Skill/Role/Organization/Industry 노드·엣지 적재, NEXT_CHAPTER 연결 |
| **Neo4j 인프라** | AuraDB Free→Professional 전환, 사이징(N8), APOC, 백업 |
| **서빙 API** | GraphRAG REST API (검색 5종 + 매칭 + 기업 조회), PII 필터 미들웨어 |
| **매칭 알고리즘** | MappingFeatures 5-피처 스코어링, MAPPED_TO 관계 생성, 가중치 수동 튜닝 |
| **Vacancy 그래프** | Vacancy/SituationalSignal/Outcome 노드 적재, Organization ER + 한국어 특화 |
| **증분 처리** | 변경 감지(created/updated/deleted), DETACH DELETE 2단계, 소프트 삭제 + 쿼리 마이그레이션 |
| **운영** | Cloud Scheduler, Cloud Workflows DAG, Runbook, 모니터링 Alarm |

---

## 3. Phase별 태스크 분리 요약

### 3.1. v5 원본 vs 분리 후 비교

| Phase | v5 원본 | 분리 후 GraphRAG | 핵심 단축 근거 |
|-------|--------|----------------|-------------|
| Phase 0 | 1주 | **0.5주** | LLM PoC·Embedding 검증은 S&F 담당 |
| Phase 1 | 5주 | **2주** | 전처리·LLM 추출 전부 S&F로 이관 |
| Phase 2 | 9주 | **2주** | 파서·Batch 600K·품질메트릭 전부 S&F |
| Phase 3 | 6주 | **4주** | JD 파싱·CompanyContext LLM 추출은 S&F |
| Phase 4 | 4주 | **3주** | 크롤링·LLM 보강은 S&F |
| 버퍼 | 2주 | **1주** | 버퍼 축소 |
| **합계** | **27주** | **캘린더 ~12.5주** | ★ v2 I4: 순수 작업 ~8주 + 대기 ~4.5주 |

> ★ **v2 I4**: GraphRAG 팀 12.5주 = **순수 작업 ~8주 + 대기 ~4.5주**
> - 대기 구간(W2~4, W7~9)에는 API 골격 설계, Bulk Loading 코드 등 선행 작업을 수행
> - S&F 팀 총 기간: ~22주 (Batch 600K가 병목)
> - **전체 크리티컬 패스: S&F 측 ~22주**

### 3.2. 분리 후 타임라인 (병렬 실행)

```
                W1        W2-3       W4-6      W7-8       W9-15        W16       W17-18    W19-22       W23     W24-26   W27
S&F팀:        [환경+PoC] [전처리+PII] [LLM추출] [파서구축] [Batch 600K]  [버퍼]   [JD+Cmp]  [잔여배치]     [버퍼]   [크롤링]  [보강]
                                              [Provider]  [품질메트릭]          [LLM추출]
                ↓ ①                    ↓ ②                  ↓ ③                    ↓ ④                   ↓ ⑤
GraphRAG팀:   [Neo4j]  [API골격+선행] [적재+API] [Bulk코드] [Bulk+사이징]  [벤치]  [ER+매칭설계][매칭+튜닝]  [Go/NG] [증분+운영][인수]
               0.5주  대기(선행2주)     2주    대기(선행1주)   2주        0.5주     1.5주       2.5주      0.5주    2.5주    0.5주

인터페이스 포인트 (★ v2 I1: 자동 트리거 포함):
  ① S&F→GraphRAG: PoC 결과 + Go/No-Go (수동 전달)
  ② S&F→GraphRAG: CandidateContext 1,000건 JSON → GCS → PubSub → GraphRAG 적재 트리거
  ③ S&F→GraphRAG: CandidateContext 480K+ JSON → GCS → PubSub → GraphRAG Bulk Loading 자동 트리거
  ④ S&F→GraphRAG: JD + CompanyContext JSON → GCS → PubSub → Vacancy/Company 적재 트리거
  ⑤ S&F→GraphRAG: 크롤링 기업 데이터 → GCS → PubSub → CompanyContext 보강 트리거
```

---

## 4. Data Contract (팀 간 인터페이스 사양)

### 4.1. S&F → GraphRAG 전달 데이터 (비동기, GCS JSONL)

> ★ **v2 I1**: GraphRAG 수신 아키텍처를 명시한다.

```
[S&F 파이프라인] → JSONL → GCS 버킷
                            ├─ gs://kg-artifacts/candidate/
                            ├─ gs://kg-artifacts/vacancy/
                            └─ gs://kg-artifacts/company_enrichment/
                                 │
                            GCS Object Finalize 이벤트
                                 │
                            PubSub Topic (kg-artifact-ready)
                                 │
                            [GraphRAG Cloud Run Job] 자동 트리거
                                 ├─ JSONL 읽기
                                 ├─ JSON Schema 검증
                                 ├─ UNWIND Batch 적재
                                 └─ BigQuery 적재 로그 기록
```

#### A. CandidateContext (Phase 1~2) — v1 동일

```json
{
  "person_id": "P_000001",
  "career_type": "experienced",
  "education_level": "bachelor",
  "role_evolution": "developer → lead → architect",
  "domain_depth": "backend_systems",
  "chapters": [
    {
      "chapter_id": "P_000001_ch0",
      "scope_type": "LEAD",
      "period_start": "2020-03",
      "period_end": "2024-12",
      "role": "Backend Lead",
      "company": "삼성전자",
      "skills": ["Python", "Kubernetes", "PostgreSQL"],
      "outcomes": [{"type": "SCALE", "description": "...", "confidence": 0.8}],
      "situational_signals": [{"label": "SCALING_TEAM", "confidence": 0.75}]
    }
  ]
}
```

**필수 조건**: PII 마스킹 완료, chapter_id `{person_id}_ch{index}`, chapters[] 시간순 정렬, v12 스키마 준수

#### B. Vacancy + CompanyContext (Phase 3) — v1 동일

#### C. 기업 보강 데이터 (Phase 4) — v1 동일

### 4.2. 에이전트 → S&F → GraphRAG (동기 API 체인)

```
[에이전트] ──(1) 검색 요청──→ [S&F API: 하드필터+벡터]
                                    │
                              (2) person_id Top 500~1000건
                                    │
            ←──(4) 최종 Top 20──── [GraphRAG API: 관계 매칭+랭킹]
                                    │
                              (3) MAPPED_TO 스코어링
```

> ★ **v2 I5: API 체인 레이턴시 SLA**
>
> | 구간 | p95 목표 | 비고 |
> |------|---------|------|
> | 에이전트 → S&F API (하드필터+벡터) | **< 500ms** | ES/Vector DB 인덱스 최적화 |
> | 에이전트 → GraphRAG API (IN-list 매칭) | **< 2s** | Neo4j Cypher + IN $id_list 최적화 |
> | **전체 체인 (S&F + GraphRAG)** | **< 3s** | 에이전트 사용자 체감 기준 |
>
> 미달 시 대응:
> - S&F p95 > 500ms: ES/Vector 인덱스 튜닝 또는 캐싱
> - GraphRAG p95 > 2s: 복합 인덱스 추가 또는 IN-list 크기 축소(500→200)
> - Cold start 포함 시: min-instances=1 설정 ($10~15/월)

---

## 5. 의사결정 포인트 재배치 — v1 동일

| 시점 | 의사결정 | 주체 |
|------|---------|------|
| W1 D3 | LLM 모델 / Embedding 모델 확정 | **S&F** |
| W1 D5 | Phase 0 Go/No-Go | **공동** |
| W6 | Phase 1 Go/No-Go | **공동** |
| W10 | Neo4j 사이징 확정 (N8) | **GraphRAG** |
| W12 | DB 500K 완료율 확인 (R6) | **S&F** |
| W15 | Phase 2 Go/No-Go | **공동** |
| W17 | MAPPED_TO 규모 테스트 (N3) + job-hub API 확정 (A1) | **GraphRAG / S&F** |
| W22 | 매칭 가중치 재조정 (N7) | **GraphRAG** |
| W26 | Gold Label 100→200건 (N6) | **공동** |

---

## 6. 비용 영향 — v1 동일

| 항목 | v5 원본 | S&F | GraphRAG |
|------|--------|-----|----------|
| LLM (Anthropic+Gemini) | $1,807 | **$1,807** | $0 |
| Embedding (Vertex AI) | $52 | **$52** | $0 |
| Neo4j AuraDB | $400~990 | $0 | **$400~990** |
| Cloud Run/GCS/BQ | $200~300 | $120~180 | $80~120 |
| Gold Label | $2,920~5,840 | $0 | **$2,920~5,840** |
| **합계** | **$5,527~9,137** | **~$2,000~2,100** | **~$3,500~7,000** |

---

## 7. 리스크 — v1 + v2 추가

| # | 리스크 | 영향 | 완화 방안 |
|---|--------|------|---------|
| R1 | S&F 산출물 지연 시 GraphRAG 블로킹 | 대기 시간 발생 | 마일스톤 합의 + 주간 싱크 + PubSub 자동 트리거 |
| R2 | Data Contract 불일치 | 적재 실패 | JSON Schema + 검증 스크립트 + 100건 Integration Test |
| R3 | 필터링 역전 (S&F Top-K 부족) | 최종 품질 저하 | Top-K 500~1000건 (필요량 10배) |
| R4 | 팀 분리 경계 모호 | 역할 혼동 | `01_task_classification.md` 73개 태스크 추적 |
| ★R5 | **API 체인 레이턴시 초과** | 사용자 체감 저하 | SLA p95 < 3s + min-instances + 캐싱 |

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| `00_review_and_analysis.md` | v1 c/g 비교 리뷰 + 타당성 분석 + v2 개선 방향 |
| `01_separation_overview.md` (본 문서) | 분리 배경, 역할 정의, 타임라인, Data Contract, 비용, 리스크 |
| `02_task_classification.md` | v5 Phase 0~4 전 태스크 S&F/GraphRAG/공동 분류 (v1 동일) |
| `03_graphrag_team_plan.md` | GraphRAG 팀 독립 실행 계획 (v2: 순수작업/대기 구간 분리) |
| `04_sf_team_plan.md` | S&F 팀 범위 + 산출물 명세 (v2: PubSub 자동 트리거 추가) |
