# GraphRAG v5 실행계획 — 팀 분리 계획서 (S&F / GraphRAG)

> **작성일**: 2026-03-12
> **기준 문서**: `04.graphrag/results/implement_planning/core/5/` (v5 최종, 7개 문서)
> **목적**: v5 실행계획(총 27주)의 모든 태스크를 **Search & Filter(S&F) 아티팩트 처리팀**과 **GraphRAG 팀** 두 조직으로 분리하여, 각 팀이 독립적으로 병렬 실행할 수 있는 구조를 설계한다.

---

## 1. 분리 배경

v5 실행계획은 DE 1명 + MLE 1명이 **전처리(PII/파싱/LLM 추출/임베딩)부터 그래프 적재·매칭·서빙까지** 전 파이프라인을 일괄 수행하는 구조이다.

이 구조의 문제점:
1. Phase 2(9주)의 대부분은 **파일 파서 구축(PDF/DOCX/HWP)**, **LLM Batch 600K 호출**, **임베딩 생성** 등 그래프와 직접 관계없는 아티팩트 처리 작업이다.
2. Phase 3에서도 **JD 파싱**, **NICE 기업정보 조회**, **CompanyContext LLM 추출** 등이 선행되어야 비로소 그래프 매칭 로직에 착수할 수 있다.
3. GraphRAG 팀의 핵심 역량(그래프 모델링, 관계 패턴 분석, 매칭 알고리즘)이 ETL성 작업에 묻혀 희석된다.

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
| **임베딩** | Vertex AI Embedding 생성(768d), Vector Index용 데이터 생산 |
| **Batch 운영** | 600K Batch 처리, 우선순위 전략(DB 500K→파일 100K), 잔여 배치 소화 |
| **품질 메트릭** | schema 준수율, 필드 완성도, PII 누출율, 적응형 호출 비율 |
| **하드 필터 API** | 스킬/연차/학력/시니어리티 등 속성 기반 1차 필터링 기능 제공 |

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

| Phase | v5 원본 기간 | 분리 후 GraphRAG 기간 | 핵심 단축 근거 |
|-------|------------|-------------------|-------------|
| Phase 0 | 1주 | **0.5주** | LLM PoC·Embedding 검증은 S&F 담당, GraphRAG는 Neo4j 환경만 |
| Phase 1 | 5주 | **2주** | 전처리(W2-3), LLM 추출(W4-5) 전부 S&F로 이관. GraphRAG는 적재+API만 |
| Phase 2 | 9주 | **2주** | 파서·Batch 600K·품질메트릭 전부 S&F. GraphRAG는 Bulk Loading+사이징+벤치마크 |
| Phase 3 | 6주 | **4주** | JD파싱·CompanyContext LLM 추출은 S&F. 매칭 알고리즘·ER·튜닝에 집중 |
| Phase 4 | 4주 | **3주** | 크롤링·LLM 보강은 S&F. 증분 자동화·Runbook·운영 인프라에 집중 |
| 버퍼 | 2주 | **1주** | Go/No-Go 판정 유지, 버퍼 1주 축소 가능 |
| **합계** | **27주** | **GraphRAG ~12.5주** | S&F와 병렬 실행 시 크리티컬 패스 대폭 감소 |

> ⚠️ **S&F 팀의 총 기간은 별도로 약 20~22주** 소요 (특히 Phase 2 Batch 600K가 병목).
> GraphRAG 팀은 S&F의 산출물이 준비되는 시점에 맞춰 적재를 수행하므로, **양 팀 병렬 실행 시 전체 프로젝트 크리티컬 패스는 S&F 측의 ~22주**로 결정된다.

### 3.2. 분리 후 타임라인 (병렬 실행)

```
                W1        W2-3       W4-6      W7-8       W9-15        W16       W17-18    W19-22       W23     W24-26   W27
S&F팀:        [환경+PoC] [전처리+PII] [LLM추출] [파서구축] [Batch 600K]  [버퍼]   [JD+Cmp]  [잔여배치]     [버퍼]   [크롤링]  [보강]
                                              [Provider]  [품질메트릭]          [LLM추출]
                ↓ ①                    ↓ ②                  ↓ ③                    ↓ ④                   ↓ ⑤
GraphRAG팀:   [Neo4j]              [적재+API] ─대기─     [Bulk+사이징]  [벤치]  [ER+매칭설계][매칭+튜닝]  [Go/NG] [증분+운영][인수]
               0.5주                  2주                    2주        0.5주     1.5주       2.5주      0.5주    2.5주    0.5주

인터페이스 포인트:
  ① S&F→GraphRAG: PoC 결과 + Go/No-Go 데이터
  ② S&F→GraphRAG: CandidateContext JSON 1,000건 (마스킹 완료)
  ③ S&F→GraphRAG: CandidateContext JSON 480K+ (Batch 처리 완료분)
  ④ S&F→GraphRAG: JD JSON + CompanyContext JSON
  ⑤ S&F→GraphRAG: 크롤링 기업 데이터
```

---

## 4. Data Contract (팀 간 인터페이스 사양)

### 4.1. S&F → GraphRAG 전달 데이터 (비동기, GCS JSONL)

#### A. CandidateContext (Phase 1~2)

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

**필수 조건**:
- PII 완전 마스킹 상태 (원본은 S&F의 GCS CMEK에 보관)
- `chapter_id`는 `{person_id}_ch{index}` 형식 (GraphRAG가 NEXT_CHAPTER 연결에 사용)
- `chapters[]`는 **시간 순서(period_start 오름차순)로 정렬**하여 전달
- v12 프롬프트 기준 필드 준수 (scope_type, outcomes 4+1유형, signals 14개 라벨)

#### B. Vacancy + CompanyContext (Phase 3)

```json
{
  "vacancy_id": "V_10001",
  "org_id": "ORG_samsung",
  "org_name": "삼성전자",
  "org_stage": "ENTERPRISE",
  "industry": "반도체",
  "industry_code": "C261",
  "required_skills": ["Python", "TensorFlow"],
  "required_role": "ML Engineer",
  "seniority": "SENIOR",
  "needed_signals": ["SCALING_TEAM", "GREENFIELD"],
  "hiring_context_scope": "LEAD",
  "operating_model": {"speed": "FAST", "autonomy": "HIGH", "process": "AGILE"},
  "employee_count": 120000,
  "revenue": 302000000000000,
  "founded_year": 1969
}
```

#### C. 기업 보강 데이터 (Phase 4)

```json
{
  "org_id": "ORG_samsung",
  "product": ["갤럭시", "엑시노스"],
  "funding": null,
  "growth_signals": ["반도체 투자 확대"],
  "source": "homepage_crawl",
  "crawled_at": "2026-06-01T09:00:00Z"
}
```

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

> GraphRAG API의 `WHERE person_id IN $id_list` 방식으로 탐색 범위를 제한하여 성능을 확보한다.

---

## 5. 의사결정 포인트 재배치

| 시점 | 의사결정 | 주체 | v5 원본 |
|------|---------|------|--------|
| W1 D3 | LLM 모델 선택 (Haiku vs Sonnet) | **S&F** | Phase 0 |
| W1 D3 | Embedding 모델 확정 (768d) | **S&F** | Phase 0 |
| W1 D5 | Phase 0 Go/No-Go | **공동** (S&F PoC 결과 기반) | Phase 0 |
| W6 | Phase 1 Go/No-Go | **공동** (GraphRAG E2E + S&F 품질) | Phase 1 |
| W10 | Neo4j 사이징 확정 (N8) | **GraphRAG** | Phase 2 |
| W12 | DB 500K 완료율 확인 (R6) | **S&F** (리포트 → GraphRAG 공유) | Phase 2 |
| W15 | Phase 2 Go/No-Go | **공동** | Phase 2 |
| W17 | MAPPED_TO 규모 테스트 (N3) | **GraphRAG** | Phase 3 |
| W17 | job-hub API 스펙 확정 (A1) | **S&F** | Phase 3 |
| W22 | 매칭 가중치 재조정 (N7) | **GraphRAG** | Phase 3 |
| W26 | Gold Label 100→200건 (N6) | **공동** | Phase 4 |

---

## 6. 비용 영향

v5 전체 비용 $5,527~9,137 중 팀 분리에 따른 비용 구조 변화:

| 항목 | v5 원본 | 분리 후 S&F | 분리 후 GraphRAG | 비고 |
|------|--------|-----------|----------------|------|
| LLM (Anthropic+Gemini) | $1,807 | **$1,807** | $0 | LLM 호출은 전부 S&F |
| Embedding (Vertex AI) | $52 | **$52** | $0 | 벡터 생성은 S&F |
| Neo4j AuraDB | $400~990 | $0 | **$400~990** | 그래프 DB는 GraphRAG |
| Cloud Run/GCS/BQ | $200~300 | $120~180 | $80~120 | 분산 |
| Gold Label | $2,920~5,840 | $0 | **$2,920~5,840** | 매칭 품질 평가는 GraphRAG |
| **합계** | **$5,527~9,137** | **~$2,000~2,100** | **~$3,500~7,000** | 총액 변화 없음 |

> 팀 분리로 인한 추가 비용은 없음. 오히려 Neo4j 사이즈 최적화(벡터를 S&F로 이관) 시 월 $50~100 절감 가능.

---

## 7. 리스크

| # | 리스크 | 영향 | 완화 방안 |
|---|--------|------|---------|
| R1 | S&F 산출물 지연 시 GraphRAG 블로킹 | GraphRAG 대기 시간 발생 | 인터페이스 포인트 ①~⑤ 기준 마일스톤 합의, 주간 싱크 |
| R2 | Data Contract 불일치 | 적재 실패, 스키마 불일치 | JSON Schema + 검증 스크립트 사전 합의, 100건 Integration Test |
| R3 | 필터링 역전 (S&F Top-K 부족) | GraphRAG 최종 결과 품질 저하 | S&F Top-K를 필요량의 10배(500~1000건)로 넉넉히 설정 |
| R4 | 기존 팀 분리 경계 모호 | Organization ER, CompanyContext 등 양쪽 관련 | §3의 태스크 분류 테이블로 명확히 경계 정의 |

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| `00_separation_overview.md` (본 문서) | 분리 배경, 역할 정의, 타임라인, Data Contract, 비용, 리스크 |
| `01_task_classification.md` | v5 Phase 0~4 **전 태스크**를 S&F / GraphRAG / 공동으로 분류한 상세 테이블 |
| `02_graphrag_team_plan.md` | GraphRAG 팀 독립 실행 계획 (축소 Phase, 산출물, Go/No-Go) |
| `03_sf_team_plan.md` | S&F 팀 범위 정의 + GraphRAG에 전달할 산출물 명세 |
