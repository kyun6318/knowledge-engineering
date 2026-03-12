# GraphRAG Core 확장 계획 v3 — 추출 설계 v12 통합 + 운영 안정성 보강

> **목적**: Core Candidate-Only MVP(6주)를 출발점으로, standard의 모든 기능을
> **데이터 레이어 확장 순서**로 추가하여 에이전트 조회 역량을 점진적으로 확대.
>
> **v2 대비 주요 변경** (core.2 리뷰 N1~N9 + extraction logic v12 통합):
> - N1: AuraDB Free Auto-Pause 대응 — Cloud Scheduler health check 12h 주기
> - N2: API 응답 PII 필드 정의서 추가 (Phase 1)
> - N3: MAPPED_TO 관계 규모 추정 + Neo4j 사이징 검증 (Phase 3)
> - N4: Phase 0 산출물에 "일일 이력서 유입량 확인" 추가
> - N5: LLM 추출 모듈 provider 추상화 레이어 (Phase 2-0)
> - N6: Gold Label 100건 시작 → 200건 확대 2단계 접근
> - N7: 매칭 가중치 튜닝 프로세스 1일 추가 (Phase 3-4)
> - N8: Neo4j 인스턴스 사이징 — 1,000건 적재 후 외삽 검증 (Phase 2-2)
> - N9: 잔여 배치 처리 현황 주간 리포트 (Phase 3)
> - V12: extraction logic v12 설계 전면 반영 (적응형 호출, v19 관계명, Hybrid 섹션 분리 등)
>
> 작성일: 2026-03-11

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| `00_overview.md` (본 문서) | 전체 구조, v2→v3 변경점, 데이터 확장 로드맵 |
| `01_phase0_setup_poc.md` | Phase 0: 환경 구성 + PoC (1주) |
| `02_phase1_core_candidate_mvp.md` | Phase 1: DB 텍스트 MVP + 에이전트 API (5주) |
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
         ★ v19 관계명 적용: HAS_CHAPTER, PERFORMED_ROLE, USED_SKILL, OCCURRED_AT, IN_INDUSTRY
  [서빙] GraphRAG API (REST) — 스킬 검색, 시맨틱 검색, 복합 조건 검색
  [에이전트 역량]
    ✓ "Python 경험 3년 이상 시니어" → 후보자 리스트
    ✓ "백엔드 아키텍처 경험" → 시맨틱 검색 (Vector Search)
    ✓ "삼성전자 출신" → 회사 기반 검색
    ✓ 복합 조건 (스킬 + 경력연수 + 시니어리티) 필터
    ✓ REST API를 통한 표준화된 에이전트 연동
    ★ API 응답에 PII 포함 범위 명시 (N2)

Phase 2 완료 (Week 14):
  [데이터] 전체 450K+100K(파일) 이력서 중 80%+ (DB + PDF/DOCX/HWP)
  [그래프] 동일 스키마, 규모 확장 (Person 480K+, Chapter 1.8M+)
         ★ 적응형 LLM 호출 (1-pass / N+1 pass) 적용 (v12 M1)
         ★ Hybrid 섹션 분리 (패턴→LLM 폴백) 적용 (v12 S1)
  [에이전트 역량] — Phase 1과 동일한 쿼리를 대규모 모수에서 실행
    ✓ 전체 후보자 풀에서 검색 (데이터 커버리지 80%+)
    ✓ 자동 품질 메트릭 (schema 준수율, 필드 완성도)
    ✗ 기업 조건 필터 → Phase 3
    ✗ 매칭 스코어 → Phase 3

Phase 3 완료 (Week 22):
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

> v2와 동일한 27주 구조. Phase 내부 태스크 세부 보강.

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
  └─ 공동: Go/No-Go

Phase 1: Core Candidate MVP (5주, Week 2-6)            ★ 첫 에이전트 연동
  ├─ Week 2-3: DB 텍스트 전처리 (MLE) + 크롤링 파이프라인 (DE, 법무 허용 시)
  ├─ Week 4-5: CandidateContext LLM 추출 (1,000건, ★ v12 프롬프트)
  ├─ Week 5-6: Graph + Embedding + 에이전트 서빙 API 설계 (1일)
  ├─ ★ API PII 필드 정의서 작성 (N2)
  ├─ ★ Cloud Scheduler health check 12h 주기 설정 (N1)
  └─ ★ DB-only MVP: 크롤링 법무 미결이어도 DB 데이터만으로 MVP 완성 가능

Phase 2: 파일 이력서 + 전체 처리 (8주, Week 7-14)       ★ 전체 후보자 검색
  ├─ 2-0: 코드 리팩토링 + ★ LLM provider 추상화 레이어 (N5) + 파일 파싱 PoC (1주)
  ├─ 2-1: PDF/DOCX/HWP 파서 + ★ Hybrid 섹션 분리 (v12 S1) (2주)
  ├─ 2-2: Neo4j Professional 전환 + ★ 1,000건 적재 후 인스턴스 사이징 검증 (N8) (1일)
  ├─ 2-3: 전체 600K Batch 처리 (5주, 목표 80%+, ★ 적응형 호출 v12 M1)
  └─ 2-4: 자동 품질 메트릭 + 쿼리 성능 벤치마크 (2-3과 병행)

버퍼 1주 (Week 15) — 번아웃 방지 + Go/No-Go + 기술 부채

Phase 3: 기업 정보 + 매칭 (7주, Week 16-22)             ★ 매칭 기능
  ├─ 3-0: 매칭 알고리즘 설계 문서 + ★ MAPPED_TO 규모 추정 (N3) (2일, Week 16)
  ├─ 3-1: JD 파서 + Vacancy 노드 (1주)
  ├─ 3-2: CompanyContext 파이프라인 (2주, ★ v12 §2 전면 반영)
  ├─ 3-3: Organization ER + 한국어 특화 (2주)
  ├─ 3-4: MappingFeatures + MAPPED_TO + ★ 가중치 튜닝 1일 추가 (N7) (2주+1일)
  ├─ 3-5: 통합 테스트 + Regression Test (병행)
  └─ ★ 잔여 배치 처리 현황 주간 리포트 (N9)

버퍼 1주 (Week 23) — v2 유지

Phase 4: 외부 보강 + 품질 + 운영 (4주, Week 24-27)      ★ 프로덕션 운영
  ├─ 4-1: 홈페이지/뉴스 크롤링 파이프라인 (2주)
  ├─ 4-2: CompanyContext 보강 — 기본 필드만 (1주, 4-1과 병행)
  ├─ 4-3: 품질 평가 ★ Gold Label 100건 시작 → 200건 확대 (N6) (3일)
  ├─ 4-4: Cloud Workflows + 증분 자동화 (1주)
  └─ 4-5: 운영 인프라 + Runbook + 인수인계 문서 (1주)

Phase 5: 운영 최적화 + 심화 (별도, 필요 시) — v2 유지

─────────────────────────────────
첫 에이전트 데모:     Week 6   (1,000건 Candidate Graph + REST API)
전체 후보자 검색:     Week 14  (480K+ Candidate Graph, 80%+)
기업-후보자 매칭:     Week 22  (+ Company + Matching)
프로덕션 운영:       Week 27  (+ 외부 보강 + 자동화)
─────────────────────────────────
```

### 인력 배치 전체 타임라인

```
         W1    W2-3    W4-5   W6    W7     W8-9    W10   W11-14   W15  W16   W17-18   W19-20  W21-22   W23  W24-25  W26-27
DE:     [환경] [크롤링*][Batch][Grph] [리팩] [PDF파서] [Neo4j][전체Batch] [버퍼][JD파서][NICE+ER ] [ER+BQ ] [테스트] [버퍼][크롤링보강][운영+인수]
MLE:    [PoC ] [전처리 ] [프롬] [API ] [PoC ] [HWP+PII][      ][품질메트릭][    ][매칭설계][CmpCtx] [Map+튜닝][Regrsn] [    ][LLM추출  ][품질+증분]
공동:   [G/NG]          [연동] [데모]  [정리]          [사이징] [공동  ] [G/NG]        [검수    ] [검증]  [G/NG] [G/NG][파일럿  ] [G/NG   ]

* 크롤링: 법무 허용 시에만 진행, 미허용 시 DE는 전처리/인프라 지원
* v3 변경: W10에 Neo4j 사이징 검증 추가, W21-22에 가중치 튜닝 추가
```

---

## 3. v2 대비 변경 상세

### 3.1 v2 리뷰 반영 (N1~N9)

| # | 변경 | v2 | v3 | 영향 |
|---|------|----|----|------|
| N1 | AuraDB Free Auto-Pause 대응 | 미설계 | **Cloud Scheduler health check 12h 주기** | Phase 1 API 중단 방지, 비용 $0 |
| N2 | API 응답 PII 필드 정의 | 미정의 | **Phase 1 API 설계 시 PII 포함 여부 명시** | 법무 검토 연동 |
| N3 | MAPPED_TO 규모 추정 | 미추정 | **Phase 3-0 설계 문서에 규모 추정 + 소규모 테스트** | Neo4j 사이징 |
| N4 | 일일 이력서 유입량 확인 | Phase 0 산출물 미포함 | **Phase 0 산출물 체크리스트에 추가** | 증분 처리 비용 |
| N5 | Provider 추상화 레이어 | 미설계 | **Phase 2-0에서 LLM provider 인터페이스 추가** | Gemini 병행 대비 |
| N6 | Gold Label 규모 | 200건 고정 | **100건 시작 → 결과에 따라 200건 확대** | -$2,920 절감 가능 |
| N7 | 매칭 가중치 튜닝 | 초기값 고정 | **Phase 3-4 완료 시 50건 검증 기반 재조정 1일** | 매칭 품질 |
| N8 | Neo4j 인스턴스 사이징 | $65~200 넓은 범위 | **Phase 2-2 전환 시 1,000건 적재 후 메모리 외삽** | 비용 정확성 |
| N9 | 잔여 배치 처리 모니터링 | 미설계 | **Phase 3 주간 리포트에 잔여 현황 포함** | 연속성 |

### 3.2 Extraction Logic v12 통합

| 변경 ID | 내용 | 반영 위치 | 영향 |
|---------|------|----------|------|
| v12-M1 | Career 수 기반 적응형 LLM 호출 (1-pass / N+1 pass) | Phase 1-C, Phase 2-3 | 비용 +25%, 정확도 향상 |
| v12-M2 | v19 canonical 관계명 전면 적용 | 전 Phase Graph 적재 | HAS_CHAPTER, PERFORMED_ROLE, USED_SKILL 등 |
| v12-M3 | 구현 순서 안내 (B→B'→A 순) | 전체 타임라인 | Phase 1: B, Phase 2: B', Phase 3: A |
| v12-S1 | 파일 이력서 Hybrid 섹션 분리 (패턴→LLM 폴백) | Phase 2-1 | 섹션 분리 성공률 70%→90%+ |
| v12-S2 | PII 매핑 테이블 GCS CMEK 저장 | Phase 1-B, Phase 2-1 | PII 보안 강화 |
| v12-S3 | compute_skill_overlap 제거 | Phase 3-4 매칭 | 04.graphrag Phase 3에서 별도 설계 |
| v12-S4 | 한국 전화번호 정규식 8종 확장 | Phase 1-B, Phase 2-1 | PII 탐지율 70~80% → 90%+ |
| v12-S5 | v1 INACTIVE 필드 프롬프트 제외 | Phase 1-C 프롬프트 | structural_tensions, work_style_signals 제거 |
| v12-C3 | operating_model 진정성 체크 단순화 | Phase 3-2 CompanyContext | LLM 진정성 → 단순 confidence 규칙 |

### 3.3 데이터 볼륨 조정 (v12 기준)

| 항목 | v2 | v3 (v12 기준) | 비고 |
|------|-----|--------------|------|
| 이력서 (DB) | 450K | **500K** | v12 §8.1 기준 |
| 이력서 (파일, DB 미존재) | 포함 | **~100K 별도** | v12 §8.1 분리 |
| JD (job-hub) | 10K | **10K** | 동일 |
| 총 Person | ~450K | **~600K** | DB 500K + 파일 100K |
| 총 Chapter | ~1.35M | **~1.8M** | 평균 3 careers × 600K |
| 총 노드 | ~6M | **~8M** | v12 §5.5 |
| 총 엣지 | ~18M | **~25M** | v12 §5.5 |

### 3.4 비용 변동 요약 (v2→v3)

| 항목 | v2 | v3 | 차이 |
|------|-----|-----|------|
| Phase 2 LLM (적응형 호출) | $1,473 | **$1,631** | +$158 (v12 M1 적응형 호출 + 100K 파일 추가) |
| Phase 4 Gold Label | $5,840 | **$2,920~5,840** | -$2,920 (N6 2단계) |
| 추가 인프라 | — | +~$20 | N1 health check $0, N8 사이징 테스트 $0 |
| **총합계** | $8,215~8,890 | **$5,453~8,768** | Gold Label 축소에 따라 변동 |

---

## 4. standard 대비 순서 변경 (v2와 동일)

> v12 M3에서 명시한 구현 순서와 정합:
> - Phase 1 (Week 2-6): **B** (CandidateContext DB) → C
> - Phase 2 (Week 7-14): **B'** (CandidateContext 파일) → C
> - Phase 3 (Week 16-22): **A** (CompanyContext) → C

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
  │   ★ PII 매핑 → GCS CMEK (v12 S2)
  │   ★ 전화번호 8종 정규식 (v12 S4)
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

### Phase 2~4: v2와 동일 아키텍처 + v12 Hybrid 섹션 분리 + provider 추상화

---

## 6. GCP 통합 환경 구성

```
프로젝트: graphrag-kg (단일 프로젝트)
리전: asia-northeast3 (서울) — 데이터 주권, 레이턴시
Vertex AI 리전: us-central1 — Gemini API + Embedding API
Neo4j AuraDB: asia-northeast1 (도쿄) — 서울 미지원

서비스 계정 (v2 유지: 3개 분리):
  1. kg-crawling@graphrag-kg.iam.gserviceaccount.com
  2. kg-processing@graphrag-kg.iam.gserviceaccount.com
  3. kg-loading@graphrag-kg.iam.gserviceaccount.com

★ v3 추가 서비스 계정:
  4. kg-pii-reader@graphrag-kg.iam.gserviceaccount.com
     - storage.objectViewer (GCS kg-pii-mapping 버킷 전용)
     - v12 S2: PII 매핑 테이블 접근 전용

SDK (전 Phase 통합):
  # v2와 동일, 변경 없음

★ v3 추가 GCS 버킷:
  gs://kg-pii-mapping/       # v12 S2: PII 매핑 테이블 (CMEK 암호화)
    → Cloud KMS CMEK 적용
    → kg-pii-reader만 접근 가능
    → Cloud Audit Logs 자동 기록

Budget Alert (v2 유지):
  Phase 0~1: $200 (경고), $400 (강제 중단)
  Phase 2: $2,800 (경고), $3,800 (강제 중단)  ← v3: 600K 볼륨 반영 +$300
  Phase 3: $600 (경고), $900 (강제 중단)
  Phase 4: $400 (경고), $600 (강제 중단)
  운영: 월 $300 (경고), $500 (강제 중단)
```

---

## 7. DE/MLE 역할 분담표

> v2 구조 유지. ★ 표시가 v3 변경/추가 사항.

| Phase | DE 담당 | MLE 담당 | 공동 |
|-------|---------|---------|------|
| **Phase 0** | GCP 환경, Neo4j, 크롤링 분석 | DB 프로파일링, LLM PoC, Embedding, ★ **일일 유입량 확인** | Go/No-Go |
| **Phase 1** | 크롤링(선택적), Batch 인프라, DB 적재, ★ **health check 설정** | 전처리, LLM 프롬프트(★v12), Graph, Embedding | **에이전트 API 설계** + ★ **PII 필드 정의**, MVP 데모 |
| **Phase 2-0** | 프로젝트 리팩토링, CI/CD | 파일 파싱 PoC, ★ **provider 추상화 레이어**, 프롬프트 통합 | 코드 정리 |
| **Phase 2-1** | PDF/DOCX 파서, SimHash, Docker | HWP 파서, PII(offset, ★ **GCS CMEK**), ★ **Hybrid 섹션 분리**, 경력 블록 | 기술/회사 사전 |
| **Phase 2-2~3** | Neo4j 전환 + ★ **사이징 검증**, Batch 운영, 모니터링 | dead-letter 분석, 자동 품질 메트릭 | 공동 |
| **Phase 2-4** | 쿼리 성능 벤치마크 (480K+) | 통계적 샘플링 검증 (384건) | 품질 리포트 |
| **Phase 3-0** | — | 매칭 알고리즘 설계 + ★ **MAPPED_TO 규모 추정** | 공동 리뷰 |
| **Phase 3-1** | JD 파서, BigQuery 스키마 | Vacancy 추출 LLM 프롬프트 | 공동 |
| **Phase 3-2** | NICE Lookup, Rule 엔진 | LLM CompanyContext 프롬프트 (★ v12 §1) | CompanyContext 통합 |
| **Phase 3-3** | Organization ER 코드, 계열사 사전 | 한국어 전처리, Rule+LLM 2단계 매칭 | 전수 검수 1,000개+ |
| **Phase 3-4** | BigQuery 서빙, Embedding | MappingFeatures + ★ **가중치 튜닝 1일** | 수동 검증 50건 |
| **Phase 3 진행 중** | — | — | ★ **잔여 배치 주간 리포트** |
| **Phase 4-3** | — | ★ **Gold Label 100건 → 200건 2단계** | 전문가 관리 |

---

## 8. 의사결정 포인트

> v2 유지 + ★ 추가 항목.

| 시점 | 의사결정 | 입력 데이터 | 실패 시 대응 |
|------|---------|-----------|------------|
| Week 0 (즉시) | Batch API quota 확인 | Anthropic 콘솔 | 동시 3 batch로 축소 |
| Week 0 (즉시) | Gemini Flash Batch 대안 검증 | API 테스트 | Batch API 한도 시 병행 |
| Week 1 Day 3 | LLM 모델 선택 | Haiku vs Sonnet 비교 | Haiku Batch 기본값 |
| Week 1 Day 3 | Embedding 모델 확정 | 분별력 테스트 | text-embedding-005 기본값 |
| ★ Week 1 Day 4 | **일일 이력서 유입량 확인** (N4) | DB 쿼리 | 증분 주기 조정 |
| Week 1 Day 5 | Phase 0 Go/No-Go | PoC 품질 + 크롤링 | 스코프 축소 |
| Week 6 | Phase 1 Go/No-Go | 1,000건 E2E + API | Phase 1 연장 |
| ★ Week 10 | **Neo4j 인스턴스 사이징 확정** (N8) | 1,000건 적재 메모리 | 인스턴스 크기 조정 |
| Week 14 | Phase 2 Go/No-Go | 전체 처리 80%+ | Phase 2 배경 연장 |
| ★ Week 16 | **MAPPED_TO 규모 소규모 테스트** (N3) | JD 100×Person 1K | 임계값/인스턴스 조정 |
| ★ Week 22 | **매칭 가중치 재조정** (N7) | 50건 검증 결과 | 가중치 업데이트 |
| Week 22 | Phase 3 Go/No-Go | 매칭 결과 | Phase 3 연장 |
| ★ Week 26 | **Gold Label 100건 결과 → 200건 확대 판단** (N6) | 100건 품질 | 100건으로 종료 or 확대 |
| Week 27 | Phase 4 Go/No-Go | 전체 품질 | 운영 인력 확정 |

---

## 9. Phase 간 Go/No-Go 기준

> v2 기준 유지. ★ 추가 항목만 기술.

### Phase 0 → Phase 1

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| LLM 추출 품질 | scope_type 정확도 > 60% (20건) | 프롬프트 재설계 +3일 |
| DB 데이터 품질 | 텍스트 필드 비어있는 비율 < 20% | structured_fields 활용 |
| 크롤링 가능성 | 법무 미결이어도 **DB-only Go** | 크롤링은 법무 결론 후 |
| ★ **일일 유입량** | **확인 완료 + 증분 주기 결정** (N4) | 가정값(1,000건/일) 유지 |
| v2 기준 동일 | ... | ... |

### Phase 2 → Phase 3 (★ v3 추가)

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| v2 기준 전부 유지 | ... | ... |
| ★ **Neo4j 사이징** | **인스턴스 크기 확정 + 안정 동작 확인** (N8) | 인스턴스 업그레이드 |
| ★ **잔여 배치** | **잔여 처리 자동화 확인 + Phase 3 리소스 충돌 없음** (N9) | Batch 할당 조정 |

### Phase 3 → Phase 4 (★ v3 추가)

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| v2 기준 전부 유지 | ... | ... |
| ★ **MAPPED_TO 규모** | **실제 관계 수 확인 + Neo4j 수용 가능** (N3) | 임계값 상향 or 인스턴스 |
| ★ **가중치 튜닝** | **50건 검증 기반 재조정 완료** (N7) | 초기값 유지 + Phase 5 재조정 |

---

## 10. Graph 스키마 진화

> ★ v3: v19 canonical 관계명 전면 적용 (v12 M2)

### Phase 1: Candidate-Only

```
Person ──[HAS_CHAPTER]──→ Chapter ──[USED_SKILL]──→ Skill
  │                          │──[PERFORMED_ROLE]──→ Role         ★ v19: HAD_ROLE → PERFORMED_ROLE
  │                          │──[OCCURRED_AT]──→ Organization    ★ v19: AT_COMPANY → OCCURRED_AT
  │                          └──[NEXT_CHAPTER]──→ Chapter        ★ v19: 시간순 연결
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

Chapter ──[PRODUCED_OUTCOME]──→ Outcome            ★ v19 신규
Chapter ──[HAS_SIGNAL]──→ SituationalSignal        ★ v19 신규

추가 Vector Index:
  vacancy_embedding (768d, text-embedding-005)
```

> **v19 관계명 정합성**: v2에서 사용하던 HAD_ROLE, AT_COMPANY는 v19 이전 버전.
> v3부터 PERFORMED_ROLE, OCCURRED_AT로 전환. 구현 코드에서 반드시 v19 관계명 사용.

---

## 11. Graph 적재: UNWIND 배치 처리 (v2 유지 + v19 관계명)

```python
# v3: v19 canonical 관계명 적용
def load_candidates_batch(driver, candidates: list[dict], batch_size: int = 100):
    """CandidateContext 배치 → Neo4j 적재 (UNWIND, v19 관계명)"""
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i:i + batch_size]
        with driver.session() as session:
            # Person 노드 배치 적재
            session.run("""
                UNWIND $batch AS c
                MERGE (p:Person {person_id: c.person_id})
                SET p.career_type = c.career_type,
                    p.education_level = c.education_level,
                    p.loaded_batch_id = $batch_id,
                    p.loaded_at = datetime()
            """, batch=batch, batch_id=f"batch_{i // batch_size}")

            # Chapter + 관계 배치 적재 (★ v19 관계명)
            chapters = []
            for c in batch:
                for j, ch in enumerate(c.get("chapters", [])):
                    chapters.append({
                        "chapter_id": f"{c['person_id']}_ch{j}",
                        "person_id": c["person_id"],
                        "scope_type": ch.get("scope_type"),
                        "seniority": ch.get("seniority"),
                        "period_start": ch.get("period_start"),
                        "period_end": ch.get("period_end"),
                        "skills": ch.get("skills", []),
                        "role": ch.get("role"),
                        "company": ch.get("company"),
                    })

            session.run("""
                UNWIND $chapters AS ch
                MERGE (c:Chapter {chapter_id: ch.chapter_id})
                SET c.scope_type = ch.scope_type,
                    c.seniority = ch.seniority,
                    c.loaded_batch_id = $batch_id
                WITH c, ch
                MATCH (p:Person {person_id: ch.person_id})
                MERGE (p)-[:HAS_CHAPTER]->(c)
            """, chapters=chapters, batch_id=f"batch_{i // batch_size}")

            # ★ v19: PERFORMED_ROLE (v2의 HAD_ROLE에서 변경)
            role_rels = [{"chapter_id": ch["chapter_id"], "role": ch["role"]}
                        for ch in chapters if ch.get("role")]
            if role_rels:
                session.run("""
                    UNWIND $rels AS r
                    MERGE (role:Role {title: r.role})
                    WITH role, r
                    MATCH (c:Chapter {chapter_id: r.chapter_id})
                    MERGE (c)-[:PERFORMED_ROLE]->(role)
                """, rels=role_rels)

            # ★ v19: OCCURRED_AT (v2의 AT_COMPANY에서 변경)
            company_rels = [{"chapter_id": ch["chapter_id"], "company": ch["company"]}
                           for ch in chapters if ch.get("company")]
            if company_rels:
                session.run("""
                    UNWIND $rels AS r
                    MERGE (o:Organization {name: r.company})
                    WITH o, r
                    MATCH (c:Chapter {chapter_id: r.chapter_id})
                    MERGE (c)-[:OCCURRED_AT]->(o)
                """, rels=company_rels)
```

### 롤백 전략 (v2 유지)

```
Graph 적재 버전 관리: v2와 동일
  - loaded_batch_id, loaded_at
  - 스냅샷 백업
  - 선택적 삭제
```

---

## 12. LLM Provider 추상화 레이어 (★ v3 N5 신규)

> Phase 2-0에서 구현. Anthropic/Gemini 병행 시 파이프라인 분기 설계.

```python
# src/extractors/llm_provider.py
from abc import ABC, abstractmethod
from typing import Any

class LLMProvider(ABC):
    """LLM 추출 프로바이더 추상 인터페이스"""

    @abstractmethod
    async def extract(self, prompt: str, schema_class: type) -> dict:
        """프롬프트 → 구조화 JSON 추출"""
        ...

    @abstractmethod
    async def submit_batch(self, prompts: list[str], schema_class: type) -> str:
        """배치 제출 → batch_id 반환"""
        ...

    @abstractmethod
    async def poll_batch(self, batch_id: str) -> list[dict]:
        """배치 결과 폴링"""
        ...

class AnthropicProvider(LLMProvider):
    """Anthropic Claude Haiku/Sonnet"""
    def __init__(self, model: str = "claude-haiku-4-5"):
        self.model = model
    # ...

class GeminiProvider(LLMProvider):
    """Google Gemini Flash"""
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
    # ...

# 팩토리
def get_provider(name: str = "anthropic") -> LLMProvider:
    providers = {
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
    }
    return providers[name]()
```

> **구현 범위**: Phase 2-0에서 인터페이스 + Anthropic 구현만. Gemini 구현은 Anthropic 한도 도달 시 추가.
> **batch_tracking 확장**: `api_provider` 컬럼 추가 (BigQuery)

---

## 13. 에이전트 서빙 API 명세 (v2 유지 + ★ PII 필드 정의 N2)

### Phase 1 API (최소 MVP)

```
POST /api/v1/search/skills
POST /api/v1/search/semantic
POST /api/v1/search/compound
GET  /api/v1/candidates/{candidate_id}
GET  /api/v1/health
```

### ★ API 응답 PII 필드 정의서 (N2)

```
GET /api/v1/candidates/{candidate_id}

PII 포함 정책:
  ┌──────────────────────┬────────────┬────────────┐
  │ 필드                  │ PII 여부    │ API 반환    │
  ├──────────────────────┼────────────┼────────────┤
  │ person_id            │ 비식별 ID   │ ✓ 반환      │
  │ name                 │ ★ PII      │ ✗ 미반환    │
  │ email                │ ★ PII      │ ✗ 미반환    │
  │ phone                │ ★ PII      │ ✗ 미반환    │
  │ career_type          │ 비식별      │ ✓ 반환      │
  │ education_level      │ 비식별      │ ✓ 반환      │
  │ chapters[]           │ 비식별      │ ✓ 반환      │
  │ skills[]             │ 비식별      │ ✓ 반환      │
  │ role_evolution       │ 비식별      │ ✓ 반환      │
  │ outcomes[]           │ 비식별      │ ✓ 반환      │
  │ situational_signals[]│ 비식별      │ ✓ 반환      │
  └──────────────────────┴────────────┴────────────┘

  * PII 필드(name, email, phone)는 API에서 절대 반환하지 않음
  * 에이전트가 PII를 필요로 하는 경우:
    → 별도 PII 조회 엔드포인트 (인증 강화, 접근 로그)
    → Phase 5에서 검토 (법무 승인 후)
  * 이력서 원문 텍스트: API에서 미반환 (마스킹 텍스트도 미포함)
  * 법무 PII 검토(Week 0)와 연동: 검토 결과에 따라 정책 조정 가능

Phase 1 구현:
  - Response에서 PII 필드 자동 필터링 미들웨어
  - 접근 로그: 모든 /candidates/{id} 요청 BigQuery 기록
```

### Phase 3 API 확장 (v2와 동일)

```
POST /api/v1/match/jd-to-candidates
POST /api/v1/match/candidate-to-jds
GET  /api/v1/companies/{org_id}
```

---

## 14. 비용 요약 (전 Phase)

> 상세 비용은 `06_cost_and_monitoring.md` 참조.

| Phase | LLM/Embedding | 인프라 | Gold Label | **합계** |
|-------|--------------|-------|-----------|---------|
| Phase 0 (1주) | $7 | $1 | — | **$8** |
| Phase 1 (5주) | $24 | $12 | — | **$36** |
| Phase 2 (8주) | $1,631 | $310~570 | — | **$1,941~2,201** |
| Phase 3 (7주) | $54 | $286~551 | — | **$340~605** |
| Phase 4 (4주) | $31 | $177~327 | $2,920~5,840 | **$3,128~6,198** |
| **합계** | **$1,747** | **$786~1,461** | **$2,920~5,840** | **$5,453~9,048** |
| **원화** | | | | **~747~1,240만** |

> v2($8,215~8,890) 대비:
> - LLM +$158 (v12 적응형 호출 + 600K 볼륨)
> - Gold Label 최소: -$2,920 (N6 2단계 시작)
> - Gold Label 최대: 동일 ($5,840)
> - 비용 레인지 확대: Gold Label 2단계 적용에 따라 하한 크게 감소

---

## 15. 후속 Phase 5: 운영 최적화 + 심화 (v2 유지)

> v2와 동일. 변경 없음.
