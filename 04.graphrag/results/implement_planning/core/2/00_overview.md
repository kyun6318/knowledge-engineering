# GraphRAG Core 확장 계획 v2 — 데이터 확장 기반 단계적 구축

> **목적**: Core Candidate-Only MVP(6주)를 출발점으로, standard의 모든 기능을
> **데이터 레이어 확장 순서**로 추가하여 에이전트 조회 역량을 점진적으로 확대.
>
> **v1 대비 주요 변경** (core.1 리뷰 반영):
> - Phase 2 기간 연장 (6주→8주), 처리 완료 목표 80%로 조정
> - 에이전트 서빙 API 설계 추가 (Phase 1)
> - Organization ER 기간 확대 (1주→2주)
> - 크롤링을 선택적 분리 — DB-only MVP 가능
> - Embedding 768d(text-embedding-005) 전체 통일
> - Neo4j UNWIND 배치 처리, 롤백 전략 추가
> - 일별 시간표 제거, Runbook/Alarm Phase 4로 이동
> - tension/culture_signals Phase 5로 이동 (Phase 4: 6주→4주)
> - 버퍼 2주 확보 (Phase 2-3 사이 + Phase 3-4 사이)
> - 자동 품질 메트릭 + 통계적 샘플링 추가
> - 매칭 알고리즘 설계 문서 Phase 3 초반 추가
> - 서비스 계정 3개 분리 (최소 권한 원칙)
>
> 작성일: 2026-03-09

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| `00_overview.md` (본 문서) | 전체 구조, 데이터 확장 로드맵, v1 대비 변경점 |
| `01_phase0_setup_poc.md` | Phase 0: 환경 구성 + PoC (1주) |
| `02_phase1_core_candidate_mvp.md` | Phase 1: DB 텍스트 MVP + 에이전트 API 설계 (5주) |
| `03_phase2_file_and_scale.md` | Phase 2: 파일 이력서 통합 + 전체 처리 (8주) |
| `04_phase3_company_and_matching.md` | Phase 3: 기업 정보 + 매칭 관계 (7주) |
| `05_phase4_enrichment_and_ops.md` | Phase 4: 외부 보강 + 품질 + 운영 (4주) |
| `06_cost_and_monitoring.md` | 비용 추정 + 모니터링 + 운영 통합 |

---

## 1. 에이전트 조회 역량 진화 로드맵

> 각 Phase 완료 시 에이전트가 **새로 할 수 있는 것**을 명시.

```
Phase 1 완료 (Week 6):
  [데이터] DB 텍스트 이력서 1,000건 (+ 크롤링 법무 허용 시 크롤링 데이터)
  [그래프] Person, Chapter, Skill, Role, Organization(이름), Industry
  [서빙] GraphRAG API (REST) — 스킬 검색, 시맨틱 검색, 복합 조건 검색
  [에이전트 역량]
    ✓ "Python 경험 3년 이상 시니어" → 후보자 리스트
    ✓ "백엔드 아키텍처 경험" → 시맨틱 검색 (Vector Search)
    ✓ "삼성전자 출신" → 회사 기반 검색
    ✓ 복합 조건 (스킬 + 경력연수 + 시니어리티) 필터
    ✓ REST API를 통한 표준화된 에이전트 연동

Phase 2 완료 (Week 14):
  [데이터] 전체 450K 이력서 중 80%+ (DB + PDF/DOCX/HWP)
  [그래프] 동일 스키마, 규모 확장 (Person 360K+, Chapter 1.8M+)
  [에이전트 역량] — Phase 1과 동일한 쿼리를 대규모 모수에서 실행
    ✓ 전체 후보자 풀에서 검색 (데이터 커버리지 80%+)
    ✓ 자동 품질 메트릭 (schema 준수율, 필드 완성도)
    ✗ 기업 조건 필터 → Phase 3
    ✗ 매칭 스코어 → Phase 3

Phase 3 완료 (Week 22):
  [데이터] + JD 10K + CompanyContext (NICE/Rule/LLM)
  [그래프] + Vacancy, Organization(ER 완료), MAPPED_TO, MappingFeatures
  [에이전트 역량]
    ✓ "이 JD에 적합한 후보자 Top 20" → 매칭 스코어 기반 랭킹
    ✓ "시리즈B 핀테크 기업의 채용공고" → 기업 조건 필터
    ✓ "이 후보자에게 적합한 포지션" → 역방향 매칭
    ✓ 업종/직무 기반 필터 (KSIC + NICE)
    ✗ 기업 심층 정보 (펀딩, 성장성) → Phase 4
    ✗ 기업 문화/텐션 신호 → Phase 5

Phase 4 완료 (Week 27):
  [데이터] + 홈페이지/뉴스 크롤링 (기업 인텔리전스 기본)
  [그래프] CompanyContext 보강 (product, funding, growth)
  [에이전트 역량]
    ✓ "최근 시리즈C 투자받은 AI 스타트업 채용" → 기업 인텔리전스
    ✓ 일일 자동 증분 업데이트
    ✓ 프로덕션 운영 (자동화 + 모니터링 + 인수인계)
```

---

## 2. 전체 타임라인 (~27주)

> v1 대비: 25주 → 27주 (+2주). Phase 2 +2주, Phase 3 +1주, 버퍼 +1주, Phase 4 -2주(tension/culture Phase 5 이동).

```
사전 준비 (Week 0, 즉시 — 27주에 미포함)
  ├─ Anthropic Batch API quota/Tier 확인           ──┐
  ├─ Gemini Flash Batch 대안 사전 검증              ──┤ 병렬
  ├─ 법무 PII 검토 요청 → 마스킹 적용으로 우선 진행   ──┤
  ├─ 크롤링 대상 사이트 법적 검토 요청               ──┤
  ├─ 크롤링 대상 사이트 DOM 구조 사전 조사           ──┤
  └─ 기존 이력서 DB 샘플 100건 확보                 ──┘

Phase 0: 환경 + PoC (1주, Week 1)
  ├─ DE: GCP 환경 + Neo4j + BigQuery + 크롤링 분석
  ├─ MLE: DB 프로파일링 + LLM PoC 20건 + Embedding
  └─ 공동: Go/No-Go

Phase 1: Core Candidate MVP (5주, Week 2-6)            ★ 첫 에이전트 연동
  ├─ Week 2-3: DB 텍스트 전처리 (MLE) + 크롤링 파이프라인 (DE, 법무 허용 시)
  ├─ Week 4-5: CandidateContext LLM 추출 (1,000건)
  ├─ Week 5-6: Graph + Embedding + 에이전트 서빙 API 설계 (1일)
  └─ ★ DB-only MVP: 크롤링 법무 미결이어도 DB 데이터만으로 MVP 완성 가능

Phase 2: 파일 이력서 + 전체 처리 (8주, Week 7-14)       ★ 전체 후보자 검색
  ├─ 2-0: 코드 리팩토링 + 파일 파싱 PoC 검증 (1주)
  ├─ 2-1: PDF/DOCX/HWP 파서 + 전처리 확장 (2주)
  ├─ 2-2: Neo4j Professional 전환 (1일)
  ├─ 2-3: 전체 450K Batch 처리 (5주, 목표 80%+)
  └─ 2-4: 자동 품질 메트릭 + 쿼리 성능 벤치마크 (2-3과 병행)

버퍼 1주 (Week 15) — 번아웃 방지 + Go/No-Go + 기술 부채

Phase 3: 기업 정보 + 매칭 (7주, Week 16-22)             ★ 매칭 기능
  ├─ 3-0: 매칭 알고리즘 설계 문서 (2일, Week 16 초반)
  ├─ 3-1: JD 파서 + Vacancy 노드 (1주)
  ├─ 3-2: CompanyContext 파이프라인 (2주)
  ├─ 3-3: Organization ER + 한국어 특화 (2주, v1 대비 +1주)
  ├─ 3-4: MappingFeatures + MAPPED_TO (2주, 3-3과 1주 병렬)
  └─ 3-5: 통합 테스트 + Regression Test (병행)

버퍼 1주 (Week 23) — ★ v1 대비 신규 추가

Phase 4: 외부 보강 + 품질 + 운영 (4주, Week 24-27)      ★ 프로덕션 운영
  ├─ 4-1: 홈페이지/뉴스 크롤링 파이프라인 (2주)
  ├─ 4-2: CompanyContext 보강 — 기본 필드만 (1주, 4-1과 병행)
  ├─ 4-3: 품질 평가 Gold Test Set (3일)
  ├─ 4-4: Cloud Workflows + 증분 자동화 (1주)
  └─ 4-5: 운영 인프라 + Runbook + 인수인계 문서 (1주)

Phase 5: 운영 최적화 + 심화 (별도, 필요 시)
  ├─ tension_type, tension_description (기업 텐션 신호)
  ├─ culture_signals (remote_friendly, diversity_focus, learning_culture)
  ├─ scale_signals (growth_rate, market_position)
  ├─ ML Knowledge Distillation (scope_type, seniority)
  ├─ LLM 비용 최적화 (Confidence 라우팅)
  ├─ Looker Studio (운영 인력 5명+ 시)
  └─ A/B 테스트 + Cohen's d / Power analysis

─────────────────────────────────
첫 에이전트 데모:     Week 6   (1,000건 Candidate Graph + REST API)
전체 후보자 검색:     Week 14  (360K+ Candidate Graph, 80%+)
기업-후보자 매칭:     Week 22  (+ Company + Matching)
프로덕션 운영:       Week 27  (+ 외부 보강 + 자동화)
─────────────────────────────────
```

### 인력 배치 전체 타임라인

```
         W1    W2-3    W4-5   W6    W7     W8-9    W10   W11-14   W15  W16   W17-18   W19-20  W21-22   W23  W24-25  W26-27
DE:     [환경] [크롤링*][Batch][Grph] [리팩] [PDF파서] [Neo4j][전체Batch] [버퍼][JD파서][NICE+ER ] [ER+BQ ] [테스트] [버퍼][크롤링보강][운영+인수]
MLE:    [PoC ] [전처리 ] [프롬] [API ] [PoC ] [HWP+PII][      ][품질메트릭][    ][매칭설계][CmpCtx] [Map  ] [Regrsn] [    ][LLM추출  ][품질+증분]
공동:   [G/NG]          [연동] [데모]  [정리]          [전환 ] [공동  ] [G/NG]        [검수    ] [검증]  [G/NG] [G/NG][파일럿  ] [G/NG   ]

* 크롤링: 법무 허용 시에만 진행, 미허용 시 DE는 전처리/인프라 지원
```

---

## 3. v1 대비 변경 상세

### 3.1 필수 변경 (Must) — 리뷰 반영

| # | 변경 | v1 | v2 | 영향 |
|---|------|----|----|------|
| M1 | Phase 2 기간 연장 | 6주 (Week 7-12) | **8주 (Week 7-14)** | 전체 +2주, 기본 시나리오에서 80%+ 달성 보장 |
| M2 | 에이전트 서빙 API 설계 | 미설계 (Cypher 직접 호출) | **Phase 1에 REST API 설계 1일 추가** | 에이전트 연동 실질화 |
| M3 | Organization ER 기간 | 1주 (Week 17) | **2주 (Week 19-20)** | 검수 1,000개+, 계열사 사전 구축 |
| M4 | Embedding 차원 | 768d/1536d 혼재 | **768d(text-embedding-005) 전체 통일** | 문서 일관성 |
| M5 | Neo4j 적재 방식 | 단건 MERGE | **UNWIND 배치 (100건/트랜잭션)** | 성능 10배+ 향상 |
| M6 | 크롤링 의존성 | Phase 1 필수 의존 | **선택적 분리 — DB-only MVP 가능** | 법적 리스크 분리 |

### 3.2 권장 변경 (Should) — 리뷰 반영

| # | 변경 | v1 | v2 |
|---|------|----|----|
| S1 | Phase 2-1 일정 | 일별 시간표 | **주 단위 마일스톤** |
| S2 | Runbook/Alarm | Phase 0-1에 Runbook 5종 + Alarm 10종 | **Phase 0-2: BQ 쿼리 3종 + Slack 수동, Phase 4: 전체 구축** |
| S3 | tension/culture_signals | Phase 4 (6주) | **Phase 5로 이동, Phase 4: 4주** |
| S4 | 품질 프레임워크 | 50건 수동 확인 | **자동 품질 메트릭 + 384건 통계적 샘플링** |
| S5 | 매칭 알고리즘 | 미설계 (Phase 3에서 구현만) | **Phase 3 초반 설계 문서 2일** |
| S6 | 서비스 계정 | 단일 kg-pipeline | **3개 분리 (crawling, processing, loading)** |
| S7 | 롤백 전략 | 없음 | **적재 버전 태그 + 선택적 삭제** |
| S8 | 버퍼 | 1주 (Week 13) | **2주 (Week 15, Week 23)** |

### 3.3 내부 불일치 수정

| # | v1 불일치 | v2 수정 |
|---|----------|--------|
| 1 | Overview 비용 $7,805 vs 06_cost $8,023 | 06_cost 기준으로 통일 |
| 2 | Embedding 768d vs 1536d | 768d(text-embedding-005)로 전체 통일 |
| 3 | 크롤러 파일명 linkedin_crawler/github_crawler | 실제 대상 사이트로 수정 |
| 4 | Vector Index dimensions: 1536 | 768로 수정, similarity_metric → similarity_function |
| 5 | 인력비 Phase 2에만 계상 | Phase 별 인력비 제거, 전체 비용에서 별도 관리 |

---

## 4. standard 대비 순서 변경 (데이터 확장 순)

> v1과 동일. 변경 없음.

| standard 순서 | core 확장 순서 | 변경 이유 |
|---|---|---|
| Phase 0 (4~5주): 대규모 API 검증 | Phase 0 (1주): 최소 PoC | DB 텍스트 기반이므로 파서 검증 불필요 |
| Phase 1: 전처리→CompanyCtx→CandidateCtx→Graph→Mapping (11~13주) | Phase 1 (5주): DB텍스트→CandidateCtx→Graph+API | 에이전트 최초 연동 Week 6으로 앞당김 |
| Phase 1에서 JD + Company 동시 처리 | Phase 3에서 JD + Company 분리 추가 | 후보자 데이터 먼저, 기업 데이터 후순위 |
| Phase 1에서 파일 파싱 필수 | Phase 2에서 파일 파싱 추가 | DB 텍스트로 빠른 MVP 먼저 |
| Phase 2: 전체 처리 + 크롤링 보강 동시 | Phase 2→4: 전체 처리, 크롤링 보강 분리 | 데이터 레이어별 순차 확장 |

---

## 5. GCP 아키텍처 (Phase별 진화)

### Phase 1: Candidate-Only + 서빙 API

```
[기존 DB]                           [크롤링 사이트] (법무 허용 시에만)
  │ export                             │ Playwright
  ▼                                    ▼
[BigQuery: resume_raw] ◄──── [Cloud Run Job: kg-crawler] (선택적)
  │
  ├─ [전처리: 정규화+PII+중복+분리]
  │
  ▼
[BigQuery: resume_processed]
  │
  ├─ [Anthropic Batch API: Haiku]
  │
  ▼
[GCS: CandidateContext JSON]
  │
  ├─ [Neo4j AuraDB Free]
  │   Person, Chapter, Skill, Role,
  │   Organization(이름), Industry
  │   Vector Index (chapter_embedding, 768d)
  │
  ▼
[Cloud Run Service: GraphRAG API]  ← ★ v2 신규
  ├─ /search/skills       (스킬 기반 검색)
  ├─ /search/semantic     (시맨틱 검색)
  ├─ /search/compound     (복합 조건)
  └─ /candidates/{id}     (상세 조회)
  │
  ▼
[에이전트]
```

### Phase 2~4: v1과 동일 아키텍처, API 레이어 추가

---

## 6. GCP 통합 환경 구성

```
프로젝트: graphrag-kg (단일 프로젝트)
리전: asia-northeast3 (서울) — 데이터 주권, 레이턴시
Vertex AI 리전: us-central1 — Gemini API + Embedding API
Neo4j AuraDB: asia-northeast1 (도쿄) — 서울 미지원

서비스 계정 (v2: 3개 분리 — 최소 권한 원칙):
  1. kg-crawling@graphrag-kg.iam.gserviceaccount.com
     - storage.objectCreator (GCS 쓰기)
     - bigquery.dataEditor (resume_raw 쓰기)
     - secretmanager.secretAccessor
  2. kg-processing@graphrag-kg.iam.gserviceaccount.com
     - storage.objectViewer + storage.objectCreator (GCS 읽기/쓰기)
     - bigquery.dataEditor
     - aiplatform.user (Embedding API)
     - secretmanager.secretAccessor
  3. kg-loading@graphrag-kg.iam.gserviceaccount.com
     - storage.objectViewer (GCS 읽기)
     - bigquery.dataViewer (읽기 전용)
     - secretmanager.secretAccessor
     - ★ Neo4j 접근은 이 계정에서만 허용

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
  pyhwp >= 0.1b12
  pypdf >= 4.0.0
  google-cloud-documentai >= 2.29.0

  # KG 파이프라인
  neo4j >= 5.15.0
  pydantic >= 2.5.0
  simhash >= 2.1.2
  json-repair >= 0.28.0

  # 크롤링 (선택적 Phase 1 + Phase 4)
  playwright >= 1.40.0
  readability-lxml >= 0.8.1
  beautifulsoup4 >= 4.12.0
  requests >= 2.31.0

  # API 서빙 (v2 신규)
  fastapi >= 0.110.0
  uvicorn >= 0.27.0

  # 테스트
  pytest >= 8.0.0
  pytest-cov >= 4.1.0
  deepdiff >= 6.7.0

Budget Alert (전 Phase):
  Phase 0~1: $200 (경고), $400 (강제 중단)
  Phase 2: $2,500 (경고), $3,500 (강제 중단)  ← v1 대비 +$500 (8주)
  Phase 3: $600 (경고), $900 (강제 중단)
  Phase 4: $400 (경고), $600 (강제 중단)       ← v1 대비 축소 (4주)
  운영: 월 $300 (경고), $500 (강제 중단)
```

---

## 7. DE/MLE 역할 분담표

> 2명 체제(DE 1명 + MLE 1명) 27주 풀타임.

| Phase | DE 담당 | MLE 담당 | 공동 |
|-------|---------|---------|------|
| **Phase 0** | GCP 환경, Neo4j, 크롤링 분석 | DB 프로파일링, LLM PoC, Embedding | Go/No-Go |
| **Phase 1** | 크롤링(선택적), Batch 인프라, DB 적재 | 전처리, LLM 프롬프트, Graph, Embedding | **에이전트 API 설계**, MVP 데모 |
| **Phase 2-0** | 프로젝트 리팩토링, CI/CD | 파일 파싱 PoC, 프롬프트→프로덕션 통합 | 코드 정리 |
| **Phase 2-1** | PDF/DOCX 파서, SimHash, Docker | HWP 파서, PII(offset), 섹션 분할, 경력 블록 | 기술/회사 사전 |
| **Phase 2-2~3** | Neo4j 전환, Batch 운영, 모니터링 | dead-letter 분석, **자동 품질 메트릭** | 공동 |
| **Phase 2-4** | **쿼리 성능 벤치마크** (450K) | **통계적 샘플링 검증** (384건) | 품질 리포트 |
| **Phase 3-0** | — | **매칭 알고리즘 설계 문서** | 공동 리뷰 |
| **Phase 3-1** | JD 파서, BigQuery 스키마 | Vacancy 추출 LLM 프롬프트 | 공동 |
| **Phase 3-2** | NICE Lookup, Rule 엔진 | LLM CompanyContext 프롬프트 | CompanyContext 통합 |
| **Phase 3-3** | Organization ER 코드, **계열사/사명변경 사전** | 한국어 전처리, **Rule+LLM 2단계 매칭** | **전수 검수 1,000개+** |
| **Phase 3-4** | BigQuery 서빙 테이블, Embedding | MappingFeatures 로직 | 수동 검증 50건 |
| **Phase 3-5** | 통합 테스트 | regression test | 공동 |
| **Phase 4-1** | 크롤러 인프라, Playwright | 크롤링 LLM 프롬프트 (Gemini) | 파일럿 검수 |
| **Phase 4-3** | — | 품질 평가, Gold Test Set | 전문가 관리 |
| **Phase 4-4** | Cloud Scheduler, 증분 인프라, Workflows | 증분 변경 감지 로직 | 공동 |
| **Phase 4-5** | Neo4j 백업 자동화, **Runbook 5종** | — | 인수인계 문서 |

---

## 8. 의사결정 포인트

| 시점 | 의사결정 | 입력 데이터 | 실패 시 대응 |
|------|---------|-----------|------------|
| Week 0 (즉시) | Batch API quota 확인 | Anthropic 콘솔 | 동시 3 batch로 축소 |
| Week 0 (즉시) | **Gemini Flash Batch 대안 검증** | API 테스트 | Batch API 한도 시 병행 전략 |
| Week 1 Day 3 | LLM 모델 선택 | Haiku vs Sonnet 비교 | Haiku Batch 기본값 |
| Week 1 Day 3 | Embedding 모델 확정 | 분별력 테스트 | text-embedding-005(768d) 기본값 |
| Week 1 Day 3 | **Neo4j APOC + connection pool 확인** | AuraDB 콘솔 | APOC 불가 시 대안, tasks 수 조정 |
| Week 1 Day 5 | **Phase 0 Go/No-Go** | PoC 품질 + 크롤링 가능성 | 스코프 축소 |
| Week 6 | **Phase 1 Go/No-Go** | 1,000건 E2E 결과 + API 동작 | Phase 1 연장 |
| Week 7 | 파일 파싱 방법 확정 (HWP) | LibreOffice vs pyhwp vs Gemini | HWP 제외 |
| Week 9 | Neo4j Professional 전환 | 노드 수 추정 | Free 한도 도달 시 즉시 |
| Week 14 | **Phase 2 Go/No-Go** | 전체 처리 결과 (80%+ 목표) | Phase 2 배경 연장 |
| Week 14 | 인력 추가 여부 | Phase 2 결과 | Phase 3 병렬화 가능 여부 |
| Week 15 | NICE DB 접근 확보 | 계약 상태 | DART/사업자등록 대체 |
| Week 22 | **Phase 3 Go/No-Go** | 매칭 결과 | Phase 3 연장 |
| Pre-Phase 4 | 크롤링 법적 검토 완료 | 법무팀 판단 | 크롤링 범위 제한 |
| Week 27 | **Phase 4 Go/No-Go** | 전체 품질 결과 | 운영 인력 확정 |

---

## 9. Phase 간 Go/No-Go 기준

### Phase 0 → Phase 1

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| LLM 추출 품질 | scope_type 정확도 > 60% (20건) | 프롬프트 재설계 +3일 |
| DB 데이터 품질 | 텍스트 필드 비어있는 비율 < 20% | structured_fields 활용 |
| 크롤링 가능성 | 법무 검토 진행 중이면 **DB-only로 진행** | ★ 크롤링 불가해도 Phase 1 Go |
| Batch API quota | 최소 조건 확인 | 동시 3 batch로 축소, Gemini Flash 대비 |
| Embedding 분별력 | similar > 0.7, dissimilar < 0.4 | text-embedding-005(768d) 기본값 |
| Neo4j connection pool | 한도 확인 + tasks 수 조정 완료 | 미확인 시 tasks=3으로 보수적 실행 |

### Phase 1 → Phase 2

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| E2E 파이프라인 | 1,000건 정상 처리 | Phase 1 연장 (최대 2주) |
| 스팟체크 | 50건 치명적 결함 0건 | 결함 수정 후 재검증 |
| 에이전트 연동 | **GraphRAG API 동작** + Cypher 5종 | API 안정화 |
| 크롤링 파이프라인 | 법무 허용 시 일일 자동 수집 정상 | 미허용 시 DB-only 지속 |

### Phase 2 → Phase 3

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| 전체 처리 | 450K 중 **80%+** 성공 (v1: 미명시) | 잔여 처리 백그라운드 + Phase 3 시작 |
| 자동 품질 | **schema 준수율 95%+, 필수 필드 90%+** | 프롬프트 수정 후 재처리 |
| Neo4j | Professional 안정 동작 | 연결 이슈 해결 |
| Regression test | Golden 50건 전 항목 통과 | 프롬프트 수정 후 재실행 |
| **쿼리 벤치마크** | Cypher 5종 × 360K+ 데이터, p95 < 2초 | 인덱스 추가/쿼리 최적화 |
| Neo4j 백업 | **스냅샷 완료** + 노드/엣지 수 기록 | 백업 완료 전 Phase 3 진입 불가 |

### Phase 3 → Phase 4

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| CompanyContext | JD 100건 + 이력서 1,000건 정상 매칭 | Phase 3 연장 |
| Organization ER | **전수 검수 완료 (1,000개+, 2%+)** | 검수 완료 전 진입 불가 |
| MappingFeatures | 피처 1개+ ACTIVE 비율 > 80% | 로직 수정 |
| 매칭 품질 | **50건 중 치명적 결함 0건, 상위 10 적합도 70%+** | 결함 원인 분석 + 수정 |
| 크롤링 법적 검토 | 법무 결론 도출 | 크롤링 범위 제한 |
| NICE DB 접근 | 접근 확보 또는 대체 방안 확정 | DART/사업자등록 대체 |

### Phase 4 → 운영

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| 품질 평가 | Gold Test Set 최소 기준 전 항목 충족 | 프롬프트 재설계 + 재처리 |
| 증분 파이프라인 | 일일 증분 3일 연속 정상 동작 | 디버깅 후 재시도 |
| 백업 자동화 | Neo4j 주간 백업 + GCS Versioning 확인 | 자동화 완료 전 불가 |
| **Runbook** | **Runbook 5종 작성 완료** (v2: Phase 4 이동) | 문서 완료 전 불가 |
| 인수인계 문서 | 운영 매뉴얼 작성 완료 | 문서 완료 전 불가 |
| 운영 인력 확정 | 운영 담당자 지정 | DE/MLE 중 1명 겸임 |

---

## 10. Graph 스키마 진화

> v1과 동일 스키마. Embedding 차원만 768d로 통일.

### Phase 1: Candidate-Only

```
Person ──[HAS_CHAPTER]──→ Chapter ──[USED_SKILL]──→ Skill
  │                          │──[HAD_ROLE]──→ Role
  │                          └──[AT_COMPANY]──→ Organization (이름만)
  └──[IN_INDUSTRY]──→ Industry

Vector Index:
  chapter_embedding (768d, text-embedding-005)  ← 통일
```

### Phase 3: + Company + Matching

```
추가 Vector Index:
  vacancy_embedding (768d, text-embedding-005)  ← 768d로 통일
```

### Phase 4: CompanyContext 보강 (기본 필드만)

```
Organization 속성 확장:
  + product_description, market_segment
  + funding_round, funding_amount, investors
  + employee_count, founded_year
  + growth_narrative
  → tension_type, culture_signals, scale_signals는 Phase 5로 이동
```

---

## 11. Graph 적재: UNWIND 배치 처리 (v2 변경)

> v1의 단건 MERGE → UNWIND 배치 (100건/트랜잭션)

```python
# v2: UNWIND 배치 적재
def load_candidates_batch(driver, candidates: list[dict], batch_size: int = 100):
    """CandidateContext 배치 → Neo4j 적재 (UNWIND)"""
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i:i + batch_size]
        with driver.session() as session:
            # Person 노드 배치 적재
            session.run("""
                UNWIND $batch AS c
                MERGE (p:Person {candidate_id: c.candidate_id})
                SET p.total_years = c.total_years,
                    p.seniority_estimate = c.seniority_estimate,
                    p.primary_domain = c.primary_domain,
                    p.loaded_batch_id = $batch_id,
                    p.loaded_at = datetime()
            """, batch=batch, batch_id=f"batch_{i // batch_size}")

            # Chapter + Skill + Role 배치 적재
            chapters = []
            for c in batch:
                for j, exp in enumerate(c.get("experiences", [])):
                    chapters.append({
                        "chapter_id": f"{c['candidate_id']}_ch{j}",
                        "candidate_id": c["candidate_id"],
                        "scope_type": exp.get("scope_type"),
                        "outcome": exp.get("outcome"),
                        "duration_months": exp.get("duration_months"),
                        "is_current": exp.get("is_current", False),
                        "skills": exp.get("skills", []),
                        "role": exp.get("role"),
                        "company": exp.get("company"),
                    })

            session.run("""
                UNWIND $chapters AS ch
                MERGE (c:Chapter {chapter_id: ch.chapter_id})
                SET c.scope_type = ch.scope_type,
                    c.outcome = ch.outcome,
                    c.duration_months = ch.duration_months,
                    c.is_current = ch.is_current,
                    c.loaded_batch_id = $batch_id
                WITH c, ch
                MATCH (p:Person {candidate_id: ch.candidate_id})
                MERGE (p)-[:HAS_CHAPTER]->(c)
            """, chapters=chapters, batch_id=f"batch_{i // batch_size}")

            # Skill 관계 배치
            skill_rels = []
            for ch in chapters:
                for skill in ch["skills"]:
                    skill_rels.append({"chapter_id": ch["chapter_id"], "skill": skill})

            if skill_rels:
                session.run("""
                    UNWIND $rels AS r
                    MERGE (s:Skill {name: r.skill})
                    WITH s, r
                    MATCH (c:Chapter {chapter_id: r.chapter_id})
                    MERGE (c)-[:USED_SKILL]->(s)
                """, rels=skill_rels)
```

### 롤백 전략 (v2 신규)

```
Graph 적재 버전 관리:
  - 모든 노드에 loaded_batch_id, loaded_at 속성 추가
  - 적재 전 Neo4j 스냅샷 백업 필수
  - 특정 batch 선택적 삭제 가능:

    // 특정 batch 적재 결과 삭제
    MATCH (n) WHERE n.loaded_batch_id = $batch_id
    DETACH DELETE n

    // 특정 시점 이후 적재 데이터 삭제
    MATCH (n) WHERE n.loaded_at > datetime($cutoff)
    DETACH DELETE n
```

---

## 12. Anthropic Batch API + Gemini Flash 대비 전략 (v2 보강)

> v1의 Batch API 단독 의존 → Gemini Flash 병행 전략 추가.

### 즉시 확인 항목 (계획 확정 전)

```
□ Anthropic 콘솔에서 현재 Tier 확인 → 결과: Tier ___
□ Claude Haiku 4.5가 Batch API 지원 모델인지 확인 → 결과: ___
□ 동시 활성 batch 수 한도 확인 → 결과: ___
□ ★ Gemini Flash Batch API 호출 테스트 (10건) → 결과: ___

확인 결과별 대응:
  - Anthropic 동시 ≥ 10: Anthropic 단독 (계획대로)
  - Anthropic 동시 5~9: Phase 2 8주 범위 내 처리 가능, 단독 진행
  - Anthropic 동시 ≤ 4: ★ Gemini Flash 병행 (50:50 분할)
```

---

## 13. 에이전트 서빙 API 명세 (v2 신규)

> Phase 1에서 설계, Phase 3에서 확장.

### Phase 1 API (최소 MVP)

```
POST /api/v1/search/skills
  Body: { "skills": ["Python", "Django"], "min_match": 2, "limit": 20 }
  Response: { "candidates": [...], "total": 150 }

POST /api/v1/search/semantic
  Body: { "query": "백엔드 아키텍처 경험", "top_k": 20 }
  Response: { "candidates": [...], "scores": [...] }

POST /api/v1/search/compound
  Body: { "skills": [...], "min_years": 3, "seniority": ["SENIOR", "LEAD"] }
  Response: { "candidates": [...] }

GET /api/v1/candidates/{candidate_id}
  Response: { "person": {...}, "chapters": [...], "skills": [...] }

GET /api/v1/health
  Response: { "status": "ok", "neo4j": "connected", "node_count": 1000 }
```

### Phase 3 API 확장

```
POST /api/v1/match/jd-to-candidates
  Body: { "vacancy_id": "...", "top_k": 20 }
  Response: { "matches": [{ "candidate_id": "...", "score": 0.87, "features": {...} }] }

POST /api/v1/match/candidate-to-jds
  Body: { "candidate_id": "...", "top_k": 10 }
  Response: { "matches": [{ "vacancy_id": "...", "score": 0.82 }] }

GET /api/v1/companies/{org_id}
  Response: { "organization": {...}, "vacancies": [...] }
```

### 인증/인가

```
Phase 1: API Key 기반 (X-API-Key 헤더)
Phase 3+: OAuth2 Bearer Token (서비스 간 통신)
Rate limiting: 100 req/min (에이전트당)
```

---

## 14. 비용 요약 (전 Phase)

> 상세 비용은 `06_cost_and_monitoring.md` 참조. 인력비는 전 Phase 통합 별도 관리.

| Phase | LLM/Embedding | 인프라 | **합계 (인프라+LLM)** |
|-------|--------------|-------|---------|
| Phase 0 (1주) | $7 | $1 | **$8** |
| Phase 1 (5주) | $24 | $12 | **$36** |
| Phase 2 (8주) | $1,473 | $310~570 | **$1,783~2,043** |
| Phase 3 (7주) | $64 | $290~530 | **$354~594** |
| Phase 4 (4주) | $34 | $180~340 | **$214~374** |
| Gold Label (Phase 4) | — | — | **$5,840** |
| **합계** | **$1,602** | **$793~1,453** | **~$8,235~8,895** |
| **원화** | | | **~1,128~1,219만** |

> standard 총비용 $8,825~9,225 대비: v2는 $8,235~8,895 ($590~330 절감)
> v1($7,805~8,205) 대비: Phase 2 기간 연장으로 인프라 비용 +$430 증가
> 인력비는 별도 관리 (Phase 4 Gold Label $5,840만 포함)

---

## 15. 후속 Phase 5: 운영 최적화 + 심화 (별도)

| # | 작업 | 비고 |
|---|------|------|
| 5-1 | **tension_type, tension_description** | v1 Phase 4에서 이동 |
| 5-2 | **culture_signals** (remote_friendly, diversity_focus, learning_culture) | v1 Phase 4에서 이동 |
| 5-3 | **scale_signals** (growth_rate, market_position) | v1 Phase 4에서 이동 |
| 5-4 | scope_type 분류기 학습 (KLUE-BERT) | F1 > 75% 목표 |
| 5-5 | seniority 분류기 학습 | F1 > 80% 목표 |
| 5-6 | Confidence 기반 라우팅 (ML > 0.85 → ML, else → LLM) | LLM 비용 절감 |
| 5-7 | A/B 테스트 + Cohen's d / Power analysis | 모델 비교 |
| 5-8 | Looker Studio 대시보드 | 운영 인력 5명+ 시 |

### 진입 조건

- Phase 4 품질 평가 완료 (Gold Test Set 기준 충족)
- 운영 데이터 최소 3개월 축적
- (tension/culture) 기업 크롤링 데이터 안정적 수집 확인
- (ML) LLM 비용이 월 $50 이상으로 비용 절감 ROI 확인
