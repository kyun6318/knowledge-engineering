# GraphRAG Core 확장 계획 v5 — v4 리뷰 반영 (최종)

> **목적**: Core Candidate-Only MVP(6주)를 출발점으로, standard의 모든 기능을
> **데이터 레이어 확장 순서**로 추가하여 에이전트 조회 역량을 점진적으로 확대.
>
> **v4 대비 변경** (core.4 리뷰 S1 + A1~A4 반영):
> - S1: Overview 비용 수치를 06_cost §1.6 기준으로 통일 ($5,563~9,208 → $5,527~9,137)
> - A1: Phase 3-1 JD 파서 0.5주의 job-hub API 스펙 확정 여부 인지 사항 추가
> - A2: Phase 0 Go/No-Go에 PoC 20건 비용 외삽 기준 추가
> - A3: AuraDB Free→Professional 마이그레이션 절차 명시 (Cypher 복사 방식)
> - A4: Phase 4 프로덕션 전환 시 Cloud Run cold start 고려 사항 추가
> - U2: mask_phones() 토큰 형식 변경 시 주의 사항 주석 추가
>
> **결론**: v4 리뷰에서 "추가 리비전(v5) 불필요, 실행 단계 즉시 진입 가능"으로 판정.
> v5는 S1(비용 동기화) + A1~A4(인지 사항 문서화)만 반영한 최종 실행 버전.
>
> 작성일: 2026-03-11

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| `00_overview.md` (본 문서) | 전체 구조, v4→v5 변경점, 데이터 확장 로드맵 |
| `01_phase0_setup_poc.md` | Phase 0: 환경 구성 + PoC (1주) |
| `02_phase1_core_candidate_mvp.md` | Phase 1: DB 텍스트 MVP + 에이전트 API (5주) |
| `03_phase2_file_and_scale.md` | Phase 2: 파일 이력서 통합 + 전체 처리 (**9주**, ★ v4: +1주) |
| `04_phase3_company_and_matching.md` | Phase 3: 기업 정보 + 매칭 관계 (**6주**, ★ v4: -1주) |
| `05_phase4_enrichment_and_ops.md` | Phase 4: 외부 보강 + 품질 + 운영 (4주) |
| `06_cost_and_monitoring.md` | 비용 추정 (**Single Source of Truth**) + 모니터링 + 운영 |

---

## 1. 에이전트 조회 역량 진화 로드맵

> 각 Phase 완료 시 에이전트가 **새로 할 수 있는 것**을 명시.

```
Phase 1 완료 (Week 6):
  [데이터] DB 텍스트 이력서 1,000건 (+ 크롤링 법무 허용 시 크롤링 데이터)
  [그래프] Person, Chapter, Skill, Role, Organization(이름), Industry
         ★ v19 관계명 적용: HAS_CHAPTER, PERFORMED_ROLE, USED_SKILL, OCCURRED_AT, IN_INDUSTRY
  [서빙] GraphRAG API (REST) — 스킬 검색, 시맨틱 검색, 복합 조건 검색
  [에이전트 역량]
    ✓ "Python 경험 3년 이상 시니어" → 후보자 리스트
    ✓ "백엔드 아키텍처 경험" → 시맨틱 검색 (Vector Search)
    ✓ "삼성전자 출신" → 회사 기반 검색
    ✓ 복합 조건 (스킬 + 경력연수 + 시니어리티) 필터
    ✓ REST API를 통한 표준화된 에이전트 연동
    ★ API 응답에 PII 포함 범위 명시 (N2)

Phase 2 완료 (Week 15):                                    ★ v4: Week 14 → 15
  [데이터] 전체 450K+100K(파일) 이력서 중 80%+ (DB + PDF/DOCX/HWP)
  [그래프] 동일 스키마, 규모 확장 (Person 480K+, Chapter 1.8M+)
         ★ 적응형 LLM 호출 (1-pass / N+1 pass) 적용 (v12 M1)
         ★ Hybrid 섹션 분리 (패턴→LLM 폴백) 적용 (v12 S1)
  [에이전트 역량] — Phase 1과 동일한 쿼리를 대규모 모수에서 실행
    ✓ 전체 후보자 풀에서 검색 (데이터 커버리지 80%+)
    ✓ 자동 품질 메트릭 (schema 준수율, 필드 완성도)
    ✗ 기업 조건 필터 → Phase 3
    ✗ 매칭 스코어 → Phase 3

Phase 3 완료 (Week 22):                                    ★ v4: 동일 (6주로 단축)
  [데이터] + JD 10K + CompanyContext (NICE/Rule/LLM)
  [그래프] + Vacancy, Organization(ER 완료), MAPPED_TO, MappingFeatures
         ★ v19 관계명: HAS_VACANCY, REQUIRES_ROLE, REQUIRES_SKILL, NEEDS_SIGNAL
         ★ MAPPED_TO 규모 사전 추정 (N3)
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

> ★ v4: Phase 2를 9주로 연장, Phase 3을 6주로 축소. 총 27주 유지.

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
  ├─ ★ MLE: 일일 이력서 유입량 확인 (N4)
  ├─ ★ v4: CMEK 버킷 생성은 Phase 1-B로 이동 (R3)
  └─ 공동: Go/No-Go

Phase 1: Core Candidate MVP (5주, Week 2-6)            ★ 첫 에이전트 연동
  ├─ Week 2-3: DB 텍스트 전처리 (MLE) + 크롤링 파이프라인 (DE, 법무 허용 시)
  │   ★ v4: PII 매핑 GCS CMEK 버킷 생성 (R3, Phase 0에서 이동)
  ├─ Week 4-5: CandidateContext LLM 추출 (1,000건, ★ v12 프롬프트)
  ├─ Week 5-6: Graph + Embedding + 에이전트 서빙 API 설계 (1일)
  ├─ ★ API PII 필드 정의서 작성 (N2)
  ├─ ★ Cloud Scheduler health check 12h 주기 설정 (N1)
  └─ ★ DB-only MVP: 크롤링 법무 미결이어도 DB 데이터만으로 MVP 완성 가능

Phase 2: 파일 이력서 + 전체 처리 (★ 9주, Week 7-15)     ★ v4: 8주→9주 (R5)
  ├─ 2-0: 코드 리팩토링 + LLM provider 추상화 + 파일 파싱 PoC (1주)
  ├─ 2-1: PDF/DOCX/HWP 파서 + Hybrid 섹션 분리 (2주)
  │   ★ v4: LLM 폴백도 Batch API로 묶어 처리 (R4)
  ├─ 2-2: Neo4j Professional 전환 + 사이징 검증 (1일)
  ├─ 2-3: 전체 600K Batch 처리 (★ 6주, 목표 80%+, 적응형 호출 v12 M1)
  │   ★ v4: 처리 우선순위 — DB 500K 먼저 → 파일 100K 후순위 (R6)
  │   ★ v4: 비관 시나리오 대응 계획 명시
  └─ 2-4: 자동 품질 메트릭 + 쿼리 성능 벤치마크 (2-3과 병행)

버퍼 1주 (Week 16) — 번아웃 방지 + Go/No-Go + 기술 부채    ★ v4: Week 15→16

Phase 3: 기업 정보 + 매칭 (★ 6주, Week 17-22)           ★ v4: 7주→6주 (R5)
  ├─ 3-0: 매칭 알고리즘 설계 문서 + MAPPED_TO 규모 추정 (2일, Week 17)
  ├─ 3-1: JD 파서 + Vacancy 노드 (★ 0.5주, 단순 구조)     ★ v4: 1주→0.5주
  ├─ 3-2: CompanyContext 파이프라인 (2주)
  ├─ 3-3: Organization ER + 한국어 특화 (1.5주)             ★ v4: 2주→1.5주
  ├─ 3-4: MappingFeatures + MAPPED_TO + 가중치 튜닝 1일 (2주)
  │   ★ v4: Grid search → 수동 비교 우선, 자동화 참고 (O3)
  ├─ 3-5: 통합 테스트 + Regression Test (병행)
  └─ ★ 잔여 배치 처리 현황 주간 리포트 (N9)

버퍼 1주 (Week 23) — v3 유지

Phase 4: 외부 보강 + 품질 + 운영 (4주, Week 24-27)      ★ 프로덕션 운영
  ├─ 4-1: 홈페이지/뉴스 크롤링 파이프라인 (2주)
  ├─ 4-2: CompanyContext 보강 — 기본 필드만 (1주, 4-1과 병행)
  ├─ 4-3: 품질 평가 Gold Label 100건 시작 → 200건 확대 (3일)
  ├─ 4-4: Cloud Workflows + 증분 자동화 (1주)
  │   ★ v4: DETACH DELETE 4단계 → 2단계 통합 (R8)
  │   ★ v4: Cypher 쿼리 is_active 필터 마이그레이션 태스크 추가 (R7)
  └─ 4-5: 운영 인프라 + Runbook + 인수인계 문서 (1주)

Phase 5: 운영 최적화 + 심화 (별도, 필요 시) — v3 유지

─────────────────────────────────
첫 에이전트 데모:     Week 6   (1,000건 Candidate Graph + REST API)
전체 후보자 검색:     Week 15  (480K+ Candidate Graph, 80%+)     ★ v4: 14→15
기업-후보자 매칭:     Week 22  (+ Company + Matching)
프로덕션 운영:       Week 27  (+ 외부 보강 + 자동화)
─────────────────────────────────
```

### 인력 배치 전체 타임라인

```
         W1    W2-3    W4-5   W6    W7     W8-9    W10   W11-15   W16  W17   W18-19   W20-21  W22     W23  W24-25  W26-27
DE:     [환경] [크롤링*][Batch][Grph] [리팩] [PDF파서] [Neo4j][전체Batch] [버퍼][JD파서][NICE+ER ] [ER+BQ ] [테스트] [버퍼][크롤링보강][운영+인수]
MLE:    [PoC ] [전처리 ] [프롬] [API ] [PoC ] [HWP+PII][      ][품질메트릭][    ][매칭설계][CmpCtx] [Map+튜닝][Regrsn] [    ][LLM추출  ][품질+증분]
공동:   [G/NG]          [연동] [데모]  [정리]          [사이징] [공동  ] [G/NG]        [검수    ] [검증]  [G/NG] [G/NG][파일럿  ] [G/NG   ]

* 크롤링: 법무 허용 시에만 진행, 미허용 시 DE는 전처리/인프라 지원
* v4 변경: Phase 2 → 9주(W7-W15), Phase 3 → 6주(W17-W22), 총 27주 유지
```

---

## 3. 변경 이력

### 3.1 v5 변경 (v4 리뷰 반영)

| # | 변경 | v4 | v5 | 영향 |
|---|------|----|----|------|
| S1 | 비용 수치 통일 | Overview $5,563~9,208 vs 06_cost $5,527~9,137 | **06_cost §1.6 기준 통일** | 문서 정합성 (MEDIUM) |
| A1 | JD 파서 API 스펙 확인 | 미명시 | **Phase 3 시작 전 job-hub API 스펙 확정 여부 확인** | Phase 3 리스크 관리 |
| A2 | Go/No-Go 비용 외삽 | 미포함 | **PoC 20건 토큰 사용량 → 600K 비용 외삽** | 예산 검증 |
| A3 | AuraDB 마이그레이션 절차 | 미상세 | **Cypher 복사 ~30분 + Vector Index 재생성** | 실행 가이드 |
| A4 | Cloud Run cold start | 미고려 | **Phase 4 운영 전환 시 min-instances 또는 Scheduler 30분 주기** | 운영 품질 |
| U2 | mask_phones() 안전성 | 주석 없음 | **토큰 형식 변경 시 다중 패턴 간섭 확인 필요 주석** | 유지보수성 |

### 3.2 v4 변경 (v3 리뷰 R1~R8, O3, O7 반영 — v4에서 반영 완료)

| # | 변경 | 반영 |
|---|------|------|
| R1 | PII 마스킹 re.sub 콜백 | ✅ 02_phase1 §1-B |
| R2 | 비용 Single Source of Truth | ✅ 06_cost §1.6 + ★ v5 S1 수치 통일 |
| R3 | CMEK Phase 1-B 이동 | ✅ |
| R4 | LLM 폴백 Batch API | ✅ 03_phase2 §2-1 |
| R5 | Phase 2 9주, Phase 3 6주 | ✅ |
| R6 | DB 500K 우선 처리 | ✅ 03_phase2 §2-3 |
| R7 | 쿼리 마이그레이션 태스크 | ✅ 05_phase4 §4-4 |
| R8 | DETACH DELETE 2단계 | ✅ 05_phase4 §4-4 |
| O3 | 가중치 수동 비교 우선 | ✅ 04_phase3 §3-4 |
| O7 | Phase 0 Must/Should 분류 | ✅ 01_phase0 |

### 3.3 데이터 볼륨 (v3와 동일)

| 항목 | v3 | v4 | 비고 |
|------|-----|-----|------|
| 이력서 (DB) | 500K | **500K** | 동일 |
| 이력서 (파일) | ~100K | **~100K** | 동일 |
| 총 Person | ~600K | **~600K** | 동일 |

### 3.4 비용 변동 요약 (v3→v5)

> ★ 비용 상세는 `06_cost_and_monitoring.md` §1 참조 (Single Source of Truth).

| 항목 | v3 | v5 | 차이 |
|------|-----|-----|------|
| Phase 2 인프라 (9주, +1주) | $319~599 | **$359~674** | +$40~75 (1주 추가) |
| 기타 | 동일 | 동일 | — |
| **총합계** | $5,523~9,138 | **$5,527~9,137** | +$4~-1 (거의 동일) |

> ★ v5 S1: v4에서 Overview($5,563~9,208)와 06_cost($5,527~9,137) 간 $36~71 불일치가 있었음.
> 원인: Overview는 "v3 비용 + 변동분"으로 계산, 06_cost는 Phase별 독립 합산 → 경로 차이.
> v5에서 06_cost §1.6 기준으로 통일.

---

## 4. standard 대비 순서 변경 (v3와 동일)

> v12 M3에서 명시한 구현 순서와 정합:
> - Phase 1 (Week 2-6): **B** (CandidateContext DB) → C
> - Phase 2 (Week 7-15): **B'** (CandidateContext 파일) → C
> - Phase 3 (Week 17-22): **A** (CompanyContext) → C

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
  │   ★ PII 매핑 → GCS CMEK (v12 S2, ★ v4: Phase 1-B에서 생성)
  │   ★ 전화번호 8종 정규식 (v12 S4)
  │   ★ v4: PII 마스킹 re.sub 콜백 방식 (R1)
  │
  ▼
[BigQuery: resume_processed]
  │
  ├─ [Anthropic Batch API: Haiku]
  │   ★ v12 프롬프트 (S5: INACTIVE 제외)
  │   ★ 적응형 호출: 1-pass (Career 1~3) / N+1 pass (Career 4+)
  │
  ▼
[GCS: CandidateContext JSON]
  │
  ├─ [Neo4j AuraDB Free]
  │   Person, Chapter, Skill, Role,
  │   Organization(이름), Industry
  │   ★ v19 관계명: HAS_CHAPTER, PERFORMED_ROLE, USED_SKILL, OCCURRED_AT
  │   Vector Index (chapter_embedding, 768d)
  │
  ▼
[Cloud Run Service: GraphRAG API]
  ├─ /search/skills       (스킬 기반 검색)
  ├─ /search/semantic     (시맨틱 검색)
  ├─ /search/compound     (복합 조건)
  ├─ /candidates/{id}     (상세 조회, ★ PII 필터 적용 N2)
  └─ /health              (★ Cloud Scheduler 12h 호출 N1)
  │
  ▼
[에이전트]
```

### Phase 2~4: v3와 동일 아키텍처 + v12 Hybrid 섹션 분리 + provider 추상화

---

## 6. GCP 통합 환경 구성

```
프로젝트: graphrag-kg (단일 프로젝트)
리전: asia-northeast3 (서울) — 데이터 주권, 레이턴시
Vertex AI 리전: us-central1 — Gemini API + Embedding API
Neo4j AuraDB: asia-northeast1 (도쿄) — 서울 미지원

서비스 계정 (v3 유지: 4개):
  1. kg-crawling@graphrag-kg.iam.gserviceaccount.com
  2. kg-processing@graphrag-kg.iam.gserviceaccount.com
  3. kg-loading@graphrag-kg.iam.gserviceaccount.com
  4. kg-pii-reader@graphrag-kg.iam.gserviceaccount.com (v12 S2)

★ v4 변경: GCS CMEK 버킷 생성을 Phase 0 → Phase 1-B로 이동 (R3)
  gs://kg-pii-mapping/       # v12 S2: PII 매핑 테이블 (CMEK 암호화)
    → Phase 1-B (Go 판정 후) 생성
    → Cloud KMS CMEK 적용
    → kg-pii-reader만 접근 가능

Budget Alert (v3 유지):
  Phase 0~1: $200 (경고), $400 (강제 중단)
  Phase 2: $2,800 (경고), $3,800 (강제 중단)
  Phase 3: $600 (경고), $900 (강제 중단)
  Phase 4: $400 (경고), $600 (강제 중단)
  운영: 월 $300 (경고), $500 (강제 중단)
```

---

## 7. DE/MLE 역할 분담표

> v3 구조 유지. ★ 표시가 v4 변경/추가 사항.

| Phase | DE 담당 | MLE 담당 | 공동 |
|-------|---------|---------|------|
| **Phase 0** | GCP 환경, Neo4j, 크롤링 분석, ★ **CMEK 제거 (R3)** | DB 프로파일링, LLM PoC, Embedding, 일일 유입량 확인 | Go/No-Go |
| **Phase 1-B** | ★ **CMEK 버킷 생성 (R3)**, 크롤링(선택적), Batch 인프라 | 전처리, ★ **PII 마스킹 re.sub 수정 (R1)**, LLM 프롬프트(v12) | 에이전트 API 설계 + PII 필드 정의 |
| **Phase 2** | 리팩토링, PDF/DOCX 파서, Neo4j 전환+사이징, Batch 운영 | 파일 파싱, HWP, ★ **Hybrid LLM 폴백 Batch화 (R4)**, 품질 메트릭 | ★ **DB 500K 우선 처리 (R6)** |
| **Phase 3** | JD 파서, NICE+ER, BigQuery | 매칭 설계, CompanyContext, ★ **가중치 수동 튜닝 (O3)** | 잔여 배치 리포트 |
| **Phase 4** | 크롤링 보강, ★ **Cypher 쿼리 마이그레이션 (R7)** | ★ **증분 처리 2단계 통합 (R8)**, Gold Label, 품질 | 운영+인수 |

---

## 8. 의사결정 포인트

| 시점 | 의사결정 | 입력 데이터 | 실패 시 대응 |
|------|---------|-----------|------------|
| Week 0 (즉시) | Batch API quota 확인 | Anthropic 콘솔 | 동시 3 batch로 축소 |
| Week 0 (즉시) | Gemini Flash Batch 대안 검증 | API 테스트 | Batch API 한도 시 병행 |
| Week 1 Day 3 | LLM 모델 선택 | Haiku vs Sonnet 비교 | Haiku Batch 기본값 |
| Week 1 Day 3 | Embedding 모델 확정 | 분별력 테스트 | text-embedding-005 기본값 |
| Week 1 Day 4 | 일일 이력서 유입량 확인 (N4) | DB 쿼리 | 가정값(1,000건/일) 유지 |
| Week 1 Day 5 | Phase 0 Go/No-Go | PoC 품질 + 크롤링 | 스코프 축소 |
| Week 6 | Phase 1 Go/No-Go | 1,000건 E2E + API | Phase 1 연장 |
| Week 10 | Neo4j 인스턴스 사이징 확정 (N8) | 1,000건 적재 메모리 | 인스턴스 크기 조정 |
| ★ Week 12 | **DB 500K 처리 완료율 확인** (R6) | Batch 진행률 | 파일 100K 우선순위 하향 |
| Week 15 | Phase 2 Go/No-Go | 전체 처리 80%+ | Phase 2 배경 연장 |
| Week 17 | MAPPED_TO 규모 소규모 테스트 (N3) | JD 100×Person 1K | 임계값/인스턴스 조정 |
| Week 22 | 매칭 가중치 재조정 (N7) | 50건 검증 결과 | 가중치 업데이트 |
| Week 22 | Phase 3 Go/No-Go | 매칭 결과 | Phase 3 연장 |
| Week 26 | Gold Label 100건 결과 → 200건 확대 판단 (N6) | 100건 품질 | 100건으로 종료 or 확대 |
| Week 27 | Phase 4 Go/No-Go | 전체 품질 | 운영 인력 확정 |

---

## 9. Phase 간 Go/No-Go 기준

### Phase 0 → Phase 1

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| LLM 추출 품질 | scope_type 정확도 > 60% (20건) | 프롬프트 재설계 +3일 |
| DB 데이터 품질 | 텍스트 필드 비어있는 비율 < 20% | structured_fields 활용 |
| 크롤링 가능성 | 법무 미결이어도 **DB-only Go** | 크롤링은 법무 결론 후 |
| 일일 유입량 | 확인 완료 + 증분 주기 결정 (N4) | 가정값(1,000건/일) 유지 |
| 적응형 호출 품질 | 1-pass ≈ N+1 pass (±10%) | Career 분기점 조정 |
| ★ **PoC 비용 외삽** (v5 A2) | **20건 평균 토큰 → 600K 외삽, 예산 $1,690 대비 ±50%** | 비용 재산정 |

### Phase 2 → Phase 3

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| 처리량 | 목표 80%+ (480K+) | Phase 3 백그라운드 연장 |
| 파싱 성공률 | 목표 95%+ | 파서 개선 |
| Neo4j 사이징 | 인스턴스 크기 확정 + 안정 동작 (N8) | 인스턴스 업그레이드 |
| 잔여 배치 | 잔여 처리 자동화 + Phase 3 리소스 충돌 없음 (N9) | Batch 할당 조정 |
| ★ **DB 500K 완료율** | **DB 500K 중 90%+ 완료** (R6) | 파일 100K는 Phase 3 백그라운드 |

### Phase 3 → Phase 4

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| MAPPED_TO 규모 | 실제 관계 수 확인 + Neo4j 수용 가능 (N3) | 임계값 상향 or 인스턴스 |
| 가중치 튜닝 | 50건 검증 기반 재조정 완료 (N7) | 초기값 유지 + Phase 5 재조정 |
| 매칭 품질 | Top-10 적합도 70%+ | 프롬프트/가중치 재조정 |

---

## 10. Graph 스키마 진화

> v3와 동일 (v19 canonical 관계명).

### Phase 1: Candidate-Only

```
Person ──[HAS_CHAPTER]──→ Chapter ──[USED_SKILL]──→ Skill
  │                          │──[PERFORMED_ROLE]──→ Role
  │                          │──[OCCURRED_AT]──→ Organization
  │                          └──[NEXT_CHAPTER]──→ Chapter
  └──(through Organization)──[IN_INDUSTRY]──→ Industry

Vector Index:
  chapter_embedding (768d, text-embedding-005)
```

### Phase 3: + Company + Matching

```
Organization ──[HAS_VACANCY]──→ Vacancy ──[REQUIRES_ROLE]──→ Role
                                   │──[REQUIRES_SKILL]──→ Skill
                                   └──[NEEDS_SIGNAL]──→ SituationalSignal

Person ──[MAPPED_TO]──→ Vacancy   (04.graphrag Phase 3)

Chapter ──[PRODUCED_OUTCOME]──→ Outcome
Chapter ──[HAS_SIGNAL]──→ SituationalSignal

추가 Vector Index:
  vacancy_embedding (768d, text-embedding-005)
```

---

## 11. Graph 적재: UNWIND 배치 처리 (v3 유지)

> v3와 동일. 코드 예시는 02_phase1 §1-D 참조.

---

## 12. LLM Provider 추상화 레이어 (v3 유지)

> v3와 동일. 코드 예시는 03_phase2 §2-0 참조.
> 현재 수준 유지 — 추가 확장(라우팅, 품질 기반 동적 분배) 자제.

---

## 13. 에이전트 서빙 API 명세 (v3 유지)

> v3와 동일. Phase 1 API + Phase 3 API 확장.

---

## 14. 비용 요약 (전 Phase)

> 비용 상세는 `06_cost_and_monitoring.md` 참조. 이 섹션은 **참조 링크만 유지**.
>
> **비용 Single Source of Truth: `06_cost_and_monitoring.md` §1** (R2)
>
> 총합계 범위: **~$5,527~9,137** (06_cost §1.6 기준, ★ v5 S1 통일)
>
> 원화: **~758~1,253만**

---

## 15. 후속 Phase 5: 운영 최적화 + 심화 (v3 유지)

> v3와 동일. 변경 없음.
