# GraphRAG Core 확장 계획 v1 — 데이터 확장 기반 단계적 구축

> **목적**: Core Candidate-Only MVP(6주)를 출발점으로, standard의 모든 기능을
> **데이터 레이어 확장 순서**로 추가하여 에이전트 조회 역량을 점진적으로 확대.
>
> **핵심 전략**:
> - 기능 단위 개발이 아닌 **데이터 확장 → 에이전트 조회 역량 확장** 순서
> - 각 Phase 완료 시 에이전트가 조회할 수 있는 데이터 범위가 명확히 넓어짐
> - Phase 1 완료(Week 6) 시점부터 에이전트 연동 가능, 이후 데이터가 풍부해질수록 역량 향상
>
> **standard 대비 핵심 차이**:
> - standard는 전처리 → CompanyContext → CandidateContext → Graph → Mapping 순서 (기능 단위)
> - 본 계획은 DB텍스트 → 파일이력서 → 기업정보 → 외부보강 순서 (데이터 단위)
> - 동일한 최종 결과물, 다른 구축 순서
>
> 작성일: 2026-03-08

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| `00_overview.md` (본 문서) | 전체 구조, 데이터 확장 로드맵, 에이전트 역량 진화 |
| `01_phase0_setup_poc.md` | Phase 0: 환경 구성 + PoC (1주) |
| `02_phase1_core_candidate_mvp.md` | Phase 1: Core Candidate MVP — 크롤링 + DB 텍스트 (5주) |
| `03_phase2_file_and_scale.md` | Phase 2: 파일 이력서 통합 + 전체 처리 (6주) |
| `04_phase3_company_and_matching.md` | Phase 3: 기업 정보 + 매칭 관계 (6주) |
| `05_phase4_enrichment_and_ops.md` | Phase 4: 외부 보강 + 품질 + 운영 (6주) |
| `06_cost_and_monitoring.md` | 비용 추정 + 모니터링 + 운영 통합 |

---

## 1. 에이전트 조회 역량 진화 로드맵

> 각 Phase 완료 시 에이전트가 **새로 할 수 있는 것**을 명시.

```
Phase 1 완료 (Week 6):
  [데이터] DB 텍스트 이력서 1,000건 + 크롤링 데이터
  [그래프] Person, Chapter, Skill, Role, Organization(이름), Industry
  [에이전트 역량]
    ✓ "Python 경험 3년 이상 시니어" → 후보자 리스트
    ✓ "백엔드 아키텍처 경험" → 시맨틱 검색 (Vector Search)
    ✓ "삼성전자 출신" → 회사 기반 검색
    ✓ 복합 조건 (스킬 + 경력연수 + 시니어리티) 필터

Phase 2 완료 (Week 12):
  [데이터] 전체 450K 이력서 (DB + PDF/DOCX/HWP)
  [그래프] 동일 스키마, 규모 확장 (Person 450K, Chapter 2.25M)
  [에이전트 역량] — Phase 1과 동일한 쿼리를 전체 모수에서 실행
    ✓ 전체 후보자 풀에서 검색 (데이터 커버리지 100%)
    ✓ 크롤링 신규 데이터 자동 반영
    ✗ 기업 조건 필터 → Phase 3
    ✗ 매칭 스코어 → Phase 3

Phase 3 완료 (Week 19):
  [데이터] + JD 10K + CompanyContext (NICE/Rule/LLM)
  [그래프] + Vacancy, Organization(ER 완료), MAPPED_TO, MappingFeatures
  [에이전트 역량]
    ✓ "이 JD에 적합한 후보자 Top 20" → 매칭 스코어 기반 랭킹
    ✓ "시리즈B 핀테크 기업의 채용공고" → 기업 조건 필터
    ✓ "이 후보자에게 적합한 포지션" → 역방향 매칭
    ✓ 업종/직무 기반 필터 (KSIC + NICE)
    ✗ 기업 심층 정보 (펀딩, 문화, 성장성) → Phase 4

Phase 4 완료 (Week 25):
  [데이터] + 홈페이지/뉴스 크롤링 (기업 인텔리전스)
  [그래프] CompanyContext 보강 (product, funding, culture, tension)
  [에이전트 역량]
    ✓ "최근 시리즈C 투자받은 AI 스타트업 채용" → 기업 인텔리전스
    ✓ "조직 변경이 있었던 기업" → 텐션 기반 필터
    ✓ 일일 자동 증분 업데이트
    ✓ 프로덕션 운영 (자동화 + 모니터링 + 인수인계)
```

---

## 2. 전체 타임라인 (~25주)

```
사전 준비 (Week 0, 즉시 — 25주에 미포함)
  ├─ Anthropic Batch API quota/Tier 확인           ──┐
  ├─ 법무 PII 검토 요청 → 마스킹 적용으로 우선 진행   ──┤ 병렬
  ├─ 크롤링 대상 사이트 법적 검토 요청               ──┤
  ├─ 크롤링 대상 사이트 DOM 구조 사전 조사           ──┤
  └─ 기존 이력서 DB 샘플 100건 확보                 ──┘

Phase 0: 환경 + PoC (1주, Week 1)
  ├─ DE: GCP 환경 + Neo4j + BigQuery + 크롤링 분석
  ├─ MLE: DB 프로파일링 + LLM PoC 20건 + Embedding
  └─ 공동: Go/No-Go

Phase 1: Core Candidate MVP (5주, Week 2-6)            ★ 첫 에이전트 연동
  ├─ Week 2-3: 크롤링 파이프라인 (DE) + 전처리 모듈 (MLE)
  ├─ Week 4-5: CandidateContext LLM 추출 (1,000건)
  └─ Week 5-6: Graph + Embedding + 에이전트 서빙

Phase 2: 파일 이력서 + 전체 처리 (6주, Week 7-12)       ★ 전체 후보자 검색
  ├─ 2-0: 코드 리팩토링 + 파일 파싱 PoC 검증 (1주)
  ├─ 2-1: PDF/DOCX/HWP 파서 + 전처리 확장 (2주)
  ├─ 2-2: Neo4j Professional 전환 (1일)
  └─ 2-3: 전체 450K Batch 처리 (3주)

버퍼 1주 (Week 13) — 번아웃 방지 + Go/No-Go + 기술 부채

Phase 3: 기업 정보 + 매칭 (6주, Week 14-19)             ★ 매칭 기능
  ├─ 3-1: JD 파서 + Vacancy 노드 (1주)
  ├─ 3-2: CompanyContext 파이프라인 (2주)
  ├─ 3-3: Organization ER + 한국어 특화 (1주)
  ├─ 3-4: MappingFeatures + MAPPED_TO (2주)
  └─ 3-5: 테스트 + Regression Test (병행)

Phase 4: 외부 보강 + 품질 + 운영 (6주, Week 20-25)      ★ 프로덕션 운영
  ├─ 4-1: 홈페이지/뉴스 크롤링 파이프라인 (4주)
  ├─ 4-2: CompanyContext 보강 (1주, 4-1과 병행)
  ├─ 4-3: 품질 평가 Gold Test Set (3일)
  ├─ 4-4: Cloud Workflows + 증분 자동화 (1주)
  └─ 4-5: 운영 인프라 + 인수인계 문서 (1주)

Phase 5: 운영 최적화 (별도, 필요 시)
  ├─ ML Knowledge Distillation (scope_type, seniority)
  ├─ LLM 비용 최적화 (Confidence 라우팅)
  ├─ Looker Studio (운영 인력 5명+ 시)
  └─ A/B 테스트 + Cohen's d / Power analysis

─────────────────────────────────
첫 에이전트 데모:     Week 6   (1,000건 Candidate Graph)
전체 후보자 검색:     Week 12  (450K Candidate Graph)
기업-후보자 매칭:     Week 19  (+ Company + Matching)
프로덕션 운영:       Week 25  (+ 외부 보강 + 자동화)
─────────────────────────────────
```

### 인력 배치 전체 타임라인

```
         W1    W2-3    W4-5   W6    W7     W8-9    W10   W11-12   W13  W14   W15-16   W17   W18-19   W20-23  W24-25
DE:     [환경] [크롤링 ] [Batch][Grph] [리팩] [PDF파서] [Neo4j][전체Batch] [버퍼][JD파서][NICE+ER ] [BQ  ] [테스트] [크롤링보강][운영+인수]
MLE:    [PoC ] [전처리 ] [프롬] [Emb ] [PoC ] [HWP+PII][      ][품질확인] [    ][VacLLM][CmpCtx  ] [Map ] [Regrsn] [LLM추출  ][품질+증분]
공동:   [G/NG]          [연동] [데모]  [정리]          [전환 ] [공동  ] [G/NG]        [검수    ] [검증]  [G/NG] [파일럿  ] [G/NG   ]
```

---

## 3. standard 대비 순서 변경 (데이터 확장 순)

| standard 순서 | core 확장 순서 | 변경 이유 |
|---|---|---|
| Phase 0 (4~5주): 대규모 API 검증 | Phase 0 (1주): 최소 PoC | DB 텍스트 기반이므로 파서 검증 불필요 |
| Phase 1: 전처리→CompanyCtx→CandidateCtx→Graph→Mapping (11~13주) | Phase 1 (5주): 크롤링→DB텍스트→CandidateCtx→Graph | 에이전트 최초 연동 Week 6으로 앞당김 |
| Phase 1에서 JD + Company 동시 처리 | Phase 3에서 JD + Company 분리 추가 | 후보자 데이터 먼저, 기업 데이터 후순위 |
| Phase 1에서 파일 파싱 필수 | Phase 2에서 파일 파싱 추가 | DB 텍스트로 빠른 MVP 먼저 |
| Phase 2: 전체 처리 + 크롤링 보강 동시 (11~14주) | Phase 2→4: 전체 처리, 크롤링 보강 분리 | 데이터 레이어별 순차 확장 |

### standard 기능 적용 위치 맵

| standard 기능 | standard 위치 | core 확장 위치 | 비고 |
|---|---|---|---|
| PDF/DOCX/HWP 파싱 | Phase 1-1 | **Phase 2-1** | DB 텍스트 우선 |
| CompanyContext | Phase 1-2 | **Phase 3-2** | 후보자 데이터 확보 후 |
| CandidateContext | Phase 1-3 | **Phase 1** (core) | 핵심, 동일 |
| Graph 적재 | Phase 1-4 | **Phase 1** (core) | 핵심, 동일 |
| Organization ER | Phase 1-4 | **Phase 3-3** | 기업 레이어에서 |
| MappingFeatures + MAPPED_TO | Phase 1-5 | **Phase 3-4** | 매칭 레이어에서 |
| 테스트/Regression | Phase 1-6 | **Phase 3-5** | 전체 기능 후 |
| Neo4j Professional 전환 | Phase 2-0 | **Phase 2-2** | 동일 시점 |
| 전체 450K 처리 | Phase 2-1 | **Phase 2-3** | 동일 |
| 품질 평가 Gold Test Set | Phase 2-2 | **Phase 4-3** | 전체 기능 완료 후 |
| 홈페이지/뉴스 크롤링 보강 | Phase 2-3 | **Phase 4-1** | 마지막 데이터 레이어 |
| CompanyContext 보강 | Phase 2-4 | **Phase 4-2** | 크롤링 후 |
| DS/MLE 서빙 인터페이스 | Phase 2-5 | **Phase 3-4** (통합) | 매칭과 함께 |
| 증분 처리 + 운영 | Phase 2-6 | **Phase 4-4~5** | 마지막 |
| 인수인계 문서 | Phase 2-6 | **Phase 4-5** | 마지막 |
| 이력서 웹 크롤링 | 없음 | **Phase 1** (core 추가) | standard에 없는 기능 |

---

## 4. GCP 아키텍처 (Phase별 진화)

### Phase 1: Candidate-Only

```
[크롤링 사이트]                    [기존 DB]
     │ Playwright                    │ export
     ▼                               ▼
[Cloud Run Job: kg-crawler] → [BigQuery: resume_raw]
                                     │
                              [전처리: 정규화+PII+중복+분리]
                                     │
                              [BigQuery: resume_processed]
                                     │
                              [Anthropic Batch API: Haiku]
                                     │
                              [GCS: CandidateContext JSON]
                                     │
                              [Neo4j AuraDB Free]
                              Person, Chapter, Skill, Role,
                              Organization(이름), Industry
                              Vector Index (chapter_embedding)
                                     │
                              [에이전트 서빙]
                              Cypher + Vector Search
```

### Phase 2: + 파일 이력서 (150GB)

```
[기존 Phase 1 파이프라인] ─────────────────────────┐
                                                    │
[GCS: 이력서 원본 150GB] → [Cloud Run Job: 파서] ───┘
  raw/resumes/               PDF/DOCX/HWP            │
                                                     ▼
                                              [Neo4j Professional]
                                              Person 450K, Chapter 2.25M
```

### Phase 3: + 기업 정보

```
[기존 Graph] ──────────────────────────────────────┐
                                                    │
[JD 데이터] → [JD 파서] ─────┐                     │
                              ├→ [CompanyContext] ──┘
[NICE DB] → [NICE Lookup] ──┘    + Rule + LLM       │
                                                     ▼
                                              [Neo4j: Full Graph]
                                              + Vacancy, Organization(ER)
                                              + MAPPED_TO, MappingFeatures
                                              [BigQuery: mapping_features 서빙]
```

### Phase 4: + 외부 보강 + 운영

```
[홈페이지 크롤러] → [Gemini Flash] ─┐
                                     ├→ [CompanyContext 보강]
[뉴스 수집기] ────→ [Gemini Flash] ─┘   + product, funding,
                                         culture, tension
                                              │
[Cloud Workflows] → [Cloud Scheduler]         ▼
  DAG 자동화          일일 증분           [프로덕션 운영]
```

---

## 5. GCP 통합 환경 구성

```
프로젝트: graphrag-kg (단일 프로젝트)
리전: asia-northeast3 (서울) — 데이터 주권, 레이턴시
Vertex AI 리전: us-central1 — Gemini API + Embedding API
Neo4j AuraDB: asia-northeast1 (도쿄) — 서울 미지원

API 활성화 (전 Phase 통합):
  Phase 0~1: run, cloudbuild, cloudscheduler, secretmanager,
             bigquery, monitoring, logging, artifactregistry,
             aiplatform, storage
  Phase 2:   documentai (HWP 비교용)
  Phase 4:   workflows, cloudfunctions

SDK (전 Phase 통합):
  # LLM / Embedding
  anthropic >= 0.39.0
  google-genai >= 1.5.0
  google-cloud-aiplatform >= 1.74.0

  # 인프라
  google-cloud-bigquery >= 3.20.0
  google-cloud-storage >= 2.14.0
  google-cloud-secret-manager >= 2.18.0

  # Phase 2 추가 (파일 파싱)
  pymupdf >= 1.23.0
  python-docx >= 1.1.0
  pyhwp >= 0.1b12         # HWP PoC
  pypdf >= 4.0.0
  google-cloud-documentai >= 2.29.0  # HWP 비교 테스트

  # KG 파이프라인
  neo4j >= 5.15.0
  pydantic >= 2.5.0
  simhash >= 2.1.2
  json-repair >= 0.28.0

  # 크롤링 (Phase 1 + Phase 4)
  playwright >= 1.40.0
  readability-lxml >= 0.8.1
  beautifulsoup4 >= 4.12.0
  requests >= 2.31.0

  # 테스트
  pytest >= 8.0.0
  pytest-cov >= 4.1.0
  deepdiff >= 6.7.0

Budget Alert (전 Phase):
  Phase 0~1: $200 (경고), $400 (강제 중단)
  Phase 2: $2,000 (경고), $3,000 (강제 중단)
  Phase 3: $500 (경고), $800 (강제 중단)
  Phase 4: $500 (경고), $800 (강제 중단)
  운영: 월 $300 (경고), $500 (강제 중단)
```

---

## 6. DE/MLE 역할 분담표

> 2명 체제(DE 1명 + MLE 1명) 25주 풀타임.

| Phase | DE 담당 | MLE 담당 | 공동 |
|-------|---------|---------|------|
| **Phase 0** | GCP 환경, Neo4j, 크롤링 분석 | DB 프로파일링, LLM PoC, Embedding | Go/No-Go |
| **Phase 1** | 크롤링 파이프라인, Batch 인프라, DB 적재 | 전처리, LLM 프롬프트, Graph, Embedding | MVP 데모, 에이전트 연동 |
| **Phase 2-0** | 프로젝트 리팩토링, CI/CD | 파일 파싱 PoC, 프롬프트→프로덕션 통합 | 코드 정리 |
| **Phase 2-1** | PDF/DOCX 파서, SimHash, Docker | HWP 파서, PII(offset), 섹션 분할, 경력 블록 | 기술/회사 사전 |
| **Phase 2-2~3** | Neo4j 전환, Batch 운영, 모니터링 | dead-letter 분석, 품질 확인 | 공동 |
| **Phase 3-1** | JD 파서, BigQuery 스키마 | Vacancy 추출 LLM 프롬프트 | 공동 |
| **Phase 3-2** | NICE Lookup, Rule 엔진 | LLM CompanyContext 프롬프트 | CompanyContext 통합 |
| **Phase 3-3** | Organization ER 코드 | 한국어 전처리 규칙, 사전 매칭 | **전수 검수 (500개)** |
| **Phase 3-4** | BigQuery 서빙 테이블, Embedding | MappingFeatures 로직 | 수동 검증 50건 |
| **Phase 3-5** | 통합 테스트 | regression test | 공동 |
| **Phase 4-1** | 크롤러 인프라, Playwright | 크롤링 LLM 프롬프트 (Gemini) | 파일럿 검수 |
| **Phase 4-3** | — | 품질 평가, Gold Test Set | 전문가 관리 |
| **Phase 4-4** | Cloud Scheduler, 증분 인프라, Workflows | 증분 변경 감지 로직 | 공동 |
| **Phase 4-5** | Neo4j 백업 자동화 | — | 인수인계 문서 |

> **인력 추가 판단 시점**: Phase 2 완료(Week 12). Phase 3~4 병렬화 가능 여부 결정.

---

## 7. 의사결정 포인트

| 시점 | 의사결정 | 입력 데이터 | 실패 시 대응 |
|------|---------|-----------|------------|
| Week 0 (즉시) | Batch API quota 확인 | Anthropic 콘솔 | 동시 3 batch로 축소 |
| Week 1 Day 3 | LLM 모델 선택 | Haiku vs Sonnet 비교 | Haiku Batch 기본값 |
| Week 1 Day 3 | Embedding 모델 확정 | 분별력 테스트 | text-embedding-005 기본값 |
| Week 1 Day 5 | **Phase 0 Go/No-Go** | PoC 품질 + 크롤링 가능성 | 스코프 축소 |
| Week 6 | **Phase 1 Go/No-Go** | 1,000건 E2E 결과 | Phase 1 연장 |
| Week 7 | 파일 파싱 방법 확정 (HWP) | LibreOffice vs pyhwp vs Gemini | HWP 제외 |
| Week 7 | 텍스트 추출 방법 확정 | Document AI vs Gemini CER/WER | 최적 방법 |
| Week 9 | Neo4j Professional 전환 | 노드 수 추정 | Free 한도 도달 시 즉시 |
| Week 12 | **Phase 2 Go/No-Go** | 전체 처리 결과 | Phase 2 연장 |
| Week 12 | 인력 추가 여부 | Phase 2 결과 | Phase 3 병렬화 가능 여부 |
| Week 13 | NICE DB 접근 확보 | 계약 상태 | DART/사업자등록 대체 |
| Week 13 | PII 법무 최종 확정 | 법무팀 판단 | 마스킹 유지 |
| Week 19 | **Phase 3 Go/No-Go** | 매칭 결과 | Phase 3 연장 |
| Pre-Phase 4 | 크롤링 법적 검토 완료 | 법무팀 판단 | 크롤링 범위 제한 |
| Week 25 | **Phase 4 Go/No-Go** | 전체 품질 결과 | 운영 인력 확정 |

---

## 8. Phase 간 Go/No-Go 기준

### Phase 0 → Phase 1

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| LLM 추출 품질 | scope_type 정확도 > 60% (20건) | 프롬프트 재설계 +3일 |
| DB 데이터 품질 | 텍스트 필드 비어있는 비율 < 20% | structured_fields 활용 |
| 크롤링 가능성 | 대상 사이트 1곳+ 파일럿 성공 | 크롤링 스코프 축소, DB 데이터만 |
| Batch API quota | 최소 조건 확인 | 동시 3 batch로 축소 |
| Embedding 분별력 | similar > 0.7, dissimilar < 0.4 | text-embedding-005 기본값 |

### Phase 1 → Phase 2

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| E2E 파이프라인 | 1,000건 정상 처리 | Phase 1 연장 (최대 2주) |
| 스팟체크 | 50건 치명적 결함 0건 | 결함 수정 후 재검증 |
| 에이전트 연동 | Cypher 5종 + Vector Search 동작 | MVP 품질 개선 |
| 크롤링 파이프라인 | 일일 자동 수집 정상 동작 | 크롤링 안정화 |

### Phase 2 → Phase 3

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| 전체 처리 | 450K 중 80%+ 성공 | 잔여 처리 계속하며 Phase 3 시작 가능 |
| Neo4j | Professional 안정 동작 | 연결 이슈 해결 |
| Regression test | Golden 50건 전 항목 통과 | 프롬프트 수정 후 재실행 |
| 적재 벤치마크 | 1,000건 → 500K 추정 시간 산출 완료 | 벤치마크 미완료 시 보수적 진행 |
| Neo4j 백업 | 백업 완료 + 노드/엣지 수 기록 | 백업 완료 전 Phase 3 진입 불가 |

### Phase 3 → Phase 4

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| CompanyContext | JD 100건 + 이력서 1,000건 정상 매칭 | Phase 3 연장 |
| Organization ER | **전수 검수 완료** (~500개) | 검수 완료 전 진입 불가 |
| MappingFeatures | 피처 1개+ ACTIVE 비율 > 80% | 로직 수정 |
| 수동 검증 | 50건 중 치명적 결함 0건 | 결함 원인 분석 + 수정 |
| 크롤링 법적 검토 | 법무 결론 도출 | 크롤링 범위 제한 |
| NICE DB 접근 | 접근 확보 또는 대체 방안 확정 | DART/사업자등록 대체 |

### Phase 4 → 운영

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| 품질 평가 | Gold Test Set 최소 기준 전 항목 충족 | 프롬프트 재설계 + 재처리 |
| 증분 파이프라인 | 일일 증분 3일 연속 정상 동작 | 디버깅 후 재시도 |
| 백업 자동화 | Neo4j 주간 백업 + GCS Versioning 확인 | 자동화 완료 전 불가 |
| 인수인계 문서 | 운영 매뉴얼 작성 완료 | 문서 완료 전 불가 |
| 운영 인력 확정 | 운영 담당자 지정 | DE/MLE 중 1명 겸임 |

---

## 9. Graph 스키마 진화

### Phase 1: Candidate-Only

```
Person ──[HAS_CHAPTER]──→ Chapter ──[USED_SKILL]──→ Skill
  │                          │──[HAD_ROLE]──→ Role
  │                          └──[AT_COMPANY]──→ Organization (이름만)
  └──[IN_INDUSTRY]──→ Industry

노드:
  Person       { candidate_id, pii_masked_name, total_years, seniority_estimate }
  Chapter      { chapter_id, scope_type, outcome, duration_months, is_current }
  Skill        { name, category }
  Role         { name, category }
  Organization { name }                  ← 이름만, ER 없음
  Industry     { code, name }            ← KSIC 대분류

Vector Index:
  chapter_embedding (768d, text-embedding-005)
```

### Phase 3: + Company + Matching (v10 Graph 스키마)

```
Person ──[HAS_CHAPTER]──→ Chapter ──[USED_SKILL]──→ Skill
  │                          │──[HAD_ROLE]──→ Role
  │                          └──[AT_COMPANY]──→ Organization (ER 완료)
  │                                                │──[IN_INDUSTRY]──→ Industry
  └──[MAPPED_TO]──→ Vacancy ──[REQUIRES_ROLE]──→ Role
                       └──[BELONGS_TO]──→ Organization

추가 노드:
  Vacancy      { vacancy_id, title, scope_type, stage_estimate }
  Organization { name, industry_code, size_estimate, hq_location }  ← ER + NICE

추가 관계:
  MAPPED_TO    { overall_match_score, feature_vector }
  REQUIRES_ROLE
  BELONGS_TO

추가 Vector Index:
  vacancy_embedding (768d)
```

### Phase 4: CompanyContext 보강

```
Organization 속성 확장:
  + product_description, market_segment
  + funding_round, funding_amount, investors
  + growth_narrative, tension_type, tension_description
  + culture_signals, scale_signals
  → 홈페이지/뉴스 크롤링 데이터 기반
```

---

## 10. Anthropic Batch API 제약사항

> 전 Phase 통합. Phase 2 전체 처리의 핵심 변수.

| 제약사항 | 현재 값 (확인 필요) | 계획 영향 |
|---|---|---|
| 동시 활성 batch 수 | 기본 ~100 (Tier 상이) | 동시 10 batch 처리 가능 여부 |
| Batch 당 최대 요청 수 | 10,000 요청 | 1,000건/chunk 계획과 호환 |
| 일일 요청 한도 (RPD) | Tier별 상이 | 450K 처리에 필요한 일수 |
| Batch 결과 보관 기간 | 29일 | 보관 기간 내 수집 보장 |
| Batch 처리 SLA | 24시간 (실제 평균 2~6시간) | 처리 시간 계산 기준 |

### 즉시 확인 항목 (계획 확정 전)

```
□ Anthropic 콘솔에서 현재 Tier 확인 → 결과: Tier ___
□ Claude Haiku 4.5가 Batch API 지원 모델인지 확인 → 결과: ___
□ 동시 활성 batch 수 한도 확인 → 결과: ___
□ 확인 결과에 따라 Phase 2-3 타임라인 보정:
  - 동시 ≥ 10: 계획대로 3주
  - 동시 5~9: 4~5주로 조정
  - 동시 ≤ 4: 5~8주 또는 Gemini Flash 병행
```

---

## 11. Neo4j Free → Professional 전환 계획

> Phase 2-2에서 실행. standard 2-0과 동일.

### 전환 트리거

| 트리거 | 시점 | 조건 |
|--------|------|------|
| **확정** | Phase 2 시작 (Week 9~10) | 필수 전환 |
| 조기 전환 | Phase 1 중 | 노드 수 150K 도달 시 |

### 예상 노드 수

```
Phase 1 (1,000 이력서):
  Person ~1K + Chapter ~5K + Skill ~2K + Role ~500
  + Organization ~500 + Industry ~100
  = ~9K 노드 → Free 여유 충분

Phase 2 (450K 이력서):
  Person ~450K + Chapter ~2.25M + Skill ~5K + Role ~1K
  + Organization ~50K + Industry ~500
  = ~2.77M 노드 → Free 200K 한도 즉시 초과

Phase 3 (+10K JD):
  + Vacancy ~10K → ~2.78M 노드 총합
```

### 비용

- AuraDB Professional: **$65/월** (최소) ~ **$200/월** (8M 노드)
- Phase 2~4 기간 (4개월): $260 ~ $800

---

## 12. 에러 복구 / 재시작 전략

### 파이프라인 레벨 Checkpoint (전 Phase 공통)

```
BigQuery processing_log를 checkpoint로 활용:
  - 각 item 처리 완료 시 (resume_id/candidate_id, pipeline, status, processed_at) 기록
  - 재시작 시: 이미 성공한 item skip
  - 전 파이프라인 동일 패턴 적용

Graph 적재 Checkpoint:
  - 트랜잭션 단위: 100건/batch
  - 마지막 성공 batch 번호를 BigQuery에 기록
  - Neo4j MERGE 사용으로 중복 적재 안전

Cloud Run Job OOM/Timeout:
  - 자동 재시작 (max-retries=2)
  - checkpoint 기반 이미 처리된 건 skip
  - 3회 연속 실패 → 알림 → 수동 조치
```

---

## 13. 비용 요약 (전 Phase)

> 상세 비용은 `06_cost_and_monitoring.md` 참조.

| Phase | LLM/Embedding | 인프라 | 인건비 | **합계** |
|-------|--------------|-------|--------|---------|
| Phase 0 (1주) | $7 | $1 | — | **$8** |
| Phase 1 (5주) | $24 | $12 | — | **$36** |
| Phase 2 (6주) | $1,425 | $156~356 | — | **$1,581~1,781** |
| Phase 3 (6주) | $110 | $100~200 | — | **$210~310** |
| Phase 4 (6주) | $30 | $100~200 | $5,840 | **$5,970~6,070** |
| **합계** | **$1,596** | **$369~769** | **$5,840** | **~$7,805~8,205** |
| **원화** | | | | **~1,069~1,124만** |

> standard 총비용 $8,825~9,225 대비 약 $1,000 절감.
> 절감 원인: Phase 0 축소($87), 인프라 기간 효율화, 크롤링 LLM(Phase 4) 통합.
> Gold Label 인건비 $5,840은 Phase 4에서 동일 적용.

---

## 14. 후속 Phase 5: 운영 최적화 (별도)

| # | 작업 | 비고 |
|---|------|------|
| 5-1 | scope_type 분류기 학습 (KLUE-BERT) | F1 > 75% 목표 |
| 5-2 | seniority 분류기 학습 | F1 > 80% 목표 |
| 5-3 | Confidence 기반 라우팅 (ML > 0.85 → ML, else → LLM) | LLM 비용 절감 |
| 5-4 | 파이프라인 성능 튜닝 | Cloud Run 사양 최적화 |
| 5-5 | A/B 테스트 + Cohen's d / Power analysis | 모델 비교 |
| 5-6 | Looker Studio 대시보드 | 운영 인력 5명+ 시 |

### 진입 조건

- Phase 4 품질 평가 완료 (Gold Test Set 기준 충족)
- 운영 데이터 최소 3개월 축적
- LLM 비용이 월 $50 이상으로 비용 절감 ROI 확인
- (Looker Studio) 운영 인력 5명 이상 확대 시
