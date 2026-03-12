# GraphRAG GCP Staged Fast Fail 계획 light.1

> **목적**: standard.1 계획(26~33주)을 **13~15주**로 압축하되, 검증 사이클과 standard.1 품질 개선사항은 모두 보존.
> "빨리 검증한다"에 초점을 맞추되, standard.1에서 도입한 안정성/추적성 기능은 유지.
>
> **standard.1 → light.1 핵심 변경**:
> - [light.1-1] Phase 0을 2.5주로 압축 (0-A/0-B/0-C/0-D 완전 병렬 + HWP 파싱 PoC 포함)
> - [light.1-2] Phase 1을 6.5~7주로 압축 (전처리/CompanyCtx 병행, Batch API 대기 중 Graph 선행, 테스트+검증 포함)
> - [light.1-3] Phase 2에서 크롤링 파이프라인 제거 → 후속 프로젝트로 분리 (standard.1과 동일 결정)
> - [light.1-4] Phase 2 서빙 최소화 (MVP 수준) + Cloud Workflows 오케스트레이션 도입
> - [light.1-5] 의사결정 포인트 6개 → 의도적 축소 (크롤링/운영 제외)
> - [light.1-6] 비용 예산 축소 (~$8,812 → ~$4,085, standard.1 한국어 토큰 기준)
>
> **standard.1 개선사항을 light.1에서 유지**:
> - [standard.2] VAS/RAG Engine 검증 제거 (이미 확정)
> - [standard.1-2] HWP 파싱 PoC (Phase 0에 3가지 방법 비교: LibreOffice vs pyhwp vs Gemini)
> - [standard.1-3] Neo4j Free→Professional 필수 전환 (Phase 2 전 필수)
> - [standard.1-4] Batch API quota/rate limit 사전 확인 (Pre-Phase 0 blocking)
> - [standard.1-5] checkpoint/재시작 전략 (BigQuery processing_log + batch_tracking)
> - [standard.1-6] pytest + deepdiff 테스트 인프라 + Golden 50건 regression test
> - [standard.1-8] Pre-Phase 0에 법무 PII 검토 (Blocking dependency)
> - [standard.20] GCS Versioning + Neo4j APOC export 백업 (backups/ 추가)
> - [standard.21] 한국어 토큰 보정 (한글 1자 ≈ 2-3 tokens, 이력서 1건당 $0.00300)
> - [standard.22] Embedding: text-embedding-005 vs gemini-embedding-001 (NOT text-multilingual-embedding-002)
> - [standard.24] Phase 1: Makefile, Phase 2: Cloud Workflows
> - [standard.25] ML Knowledge Distillation → Phase 3/후속 분리
> - [standard.26] Embedding egress 비용 추가
>
> **light.1에서 절대 생략하지 않는 것**:
> - Phase 0 의사결정 (모델/Embedding/PII/HWP 파싱/Graph DB 확정)
> - Phase 1 MVP 1,000건 E2E 검증
> - LLM 파싱 실패 3-tier 구현
> - 품질 평가 (최소 200건 Gold Set, standard.1 한국어 토큰 기준)
> - checkpoint/재시작 인프라 (batch_tracking)
> - pytest + regression test 프레임워크
>
> 작성일: 2026-03-08

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| `00_fast_fail_analysis.md` | Fast Fail 전략 부적합 분석 (8주 → 왜 안 되는가) |
| `01_overview.md` (본 문서) | 전체 구조, 아키텍처, 타임라인, 의사결정 포인트 |
| `02_phase0_validation_poc.md` | Phase 0: API 검증 + PoC + 인프라 (2.5주) |
| `03_phase1_mvp_pipeline.md` | Phase 1: MVP 파이프라인 (6.5~7주) |
| `04_phase2_full_processing.md` | Phase 2: 전체 데이터 처리 + 품질 평가 (4~5주) |
| `05_cost_monitoring.md` | 비용 추정 + 최소 모니터링 |

---

## 1. 전체 타임라인

```
Phase 0: 기반 구축 + API 검증 + PoC (2.5주)
  ├─ 0-A: GCP 환경 + API 검증 (3일)          ──┐
  ├─ 0-B: 데이터 탐색 + 프로파일링 (1주)       ──┤ 완전 병렬
  ├─ 0-C: LLM 추출 PoC (1.5주)               ──┤
  └─ 0-D: 인프라 셋업 (1주)                   ──┘
  → Week 2.5: 의사결정 완료

Phase 1: MVP 파이프라인 (6.5~7주)
  ├─ 1-A: 전처리 + CompanyContext (2주, 병행)  ──┐
  │   ├─ 전처리 모듈 (DE 담당)                  │
  │   └─ CompanyContext (MLE 담당)              │
  ├─ 1-B: CandidateContext (3주)               ──┤ 직렬
  │   ├─ 구현 2주 + Batch API 대기 활용 1주     │
  │   └─ Batch API 대기 중 Graph 적재 선행     │
  ├─ 1-C: Graph + Embedding + Mapping (1주)    ──┤
  └─ 1-D: 테스트 + 검증 + 백업 (0.5~1주)       ──┘
  → Week 9.5~10: MVP 1,000건 E2E 동작

Phase 2: 전체 처리 + 품질 평가 (4~5주)
  ├─ 2-A: 450K Batch 처리 (3~4주, 물리적 시간)  ──┐
  ├─ 2-B: 품질 평가 (1주, 2-A와 병행)           ──┤ 병렬
  ├─ 2-C: Graph 전체 적재 + Embedding (1~2주)   ──┤
  └─ 2-D: 최소 서빙 인터페이스 (0.5주)          ──┘
  → Week 13~15: 전체 KG 완성 + 품질 리포트

후속 프로젝트 (별도):
  ├─ 크롤링 파이프라인 (4주)
  ├─ 증분 처리 + 운영 자동화 (2주)
  └─ Knowledge Distillation (선택)

총 코어 KG 완성: ~13~15주
첫 동작 데모 (MVP): ~9.5~10주
```

### standard.1 대비 일정 압축 상세

| 항목 | standard.1 | light.1 | 절감 | 방법 |
|------|----|----|------|------|
| Phase 0 | 4~5주 | 2.5주 | **-2주** | 0-A/0-B/0-C/0-D 완전 병렬 (HWP PoC 포함) |
| Phase 1 전처리 | 2주 | 1주(병행) | **-1주** | CompanyCtx와 동시 진행 (DE/MLE 분업) |
| Phase 1 CompanyCtx | 1.5~2주 | 1주(병행) | **-1주** | 전처리와 동시 진행 |
| Phase 1 CandidateCtx | 4주 | 3주 | **-1주** | Batch API 대기 시간에 Graph 적재 선행 |
| Phase 1 Graph+Mapping | 2~3주 | 1주 | **-1~2주** | 1,000건이므로 1주 충분 |
| Phase 1 테스트+검증+백업 | (포함) | 0.5~1주 | **+0.5~1주** | standard.1-6 테스트, Org ER 알고리즘, standard.20 백업 (개발 시간) |
| Phase 2 크롤링 | 4주 | 0주 | **-4주** | 후속 프로젝트로 분리 (standard.1과 동일) |
| Phase 2 서빙+운영 | 2~3주 | 0.5주 | **-2주** | 최소 BigQuery 인터페이스만 |
| **합계** | **26~33주** | **13~15주** | **-14주** | |

---

## 2. GCP 아키텍처 (light.1 — 크롤링 제거, standard.1 추적성 강화)

```
┌──────────────────────────────────────────────────────────────────┐
│                    GCP Project: graphrag-kg                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [데이터 레이어]                                                  │
│  ├─ GCS: gs://graphrag-kg-data/                                 │
│  │   ├─ raw/resumes/              (이력서 원본 150GB)             │
│  │   ├─ raw/jds/                  (JD 원본)                      │
│  │   ├─ reference/                (NICE, 기술사전, 회사사전)       │
│  │   ├─ parsed/                   (파싱 결과 JSON)               │
│  │   ├─ dedup/                    (중복 제거 결과)                │
│  │   ├─ contexts/company/         (CompanyContext JSON)           │
│  │   ├─ contexts/candidate/       (CandidateContext JSON)        │
│  │   ├─ batch-api/                (Anthropic Batch API 요청/응답) │
│  │   ├─ mapping-features/         (MappingFeatures JSON)         │
│  │   ├─ prompts/                  (프롬프트 버전 관리)            │
│  │   ├─ dead-letter/              (처리 실패 건)                  │
│  │   ├─ quality/                  (Golden Set, Gold Labels)      │
│  │   ├─ backups/                  (GCS Versioning + Neo4j export)│
│  │   └─ api-test/                 (Phase 0 API 검증 결과)        │
│  │                                                                │
│  ├─ BigQuery: graphrag_kg                                        │
│  │   ├─ processing_log            (처리 이력/checkpoint 기반)     │
│  │   ├─ batch_tracking            (Batch API 상태 추적)          │
│  │   ├─ chunk_status              (chunk 상태 추적)              │
│  │   ├─ mapping_features          (서빙 테이블)                   │
│  │   ├─ quality_metrics           (품질 평가 결과)                │
│  │   └─ parse_failure_log         (LLM 파싱 실패 모니터링)       │
│  │                                                                │
│  └─ Neo4j AuraDB (Professional tier, Phase 2 전환)               │
│      ├─ Person, Chapter, Organization, Vacancy, Industry,        │
│      │  Skill, Role                                              │
│      ├─ Vector Index (chapter_embedding, vacancy_embedding)       │
│      └─ MAPPED_TO, REQUIRES_ROLE, BELONGS_TO, IN_INDUSTRY 관계   │
│                                                                  │
│  [컴퓨팅 레이어]                                                  │
│  ├─ Cloud Run Jobs              (배치 파이프라인)                 │
│  └─ Cloud Functions             (이벤트 트리거, 경량 처리)        │
│                                                                  │
│  [오케스트레이션]                                                 │
│  ├─ Makefile                    (Phase 1: 로컬/개발)             │
│  └─ Cloud Workflows             (Phase 2: 프로덕션 DAG)          │
│                                                                  │
│  [LLM API (외부)]                                                │
│  ├─ Anthropic Batch API         (Claude Haiku 4.5 — Primary)     │
│  └─ Anthropic API               (Claude Sonnet 4.6 — PoC/비교)  │
│                                                                  │
│  [Embedding API]                                                 │
│  ├─ Vertex AI text-embedding-005     (768d — Primary)           │
│  └─ Vertex AI gemini-embedding-001   (비교, standard.1 한국어 검증)      │
│                                                                  │
│  [Document 파싱 (Phase 0 PoC)]                                   │
│  ├─ LibreOffice (HWP→PDF 변환)                                   │
│  ├─ pyhwp (직접 파싱)                                            │
│  └─ Gemini 멀티모달 (비교)                                       │
│                                                                  │
│  [모니터링 — 최소 구성]                                           │
│  ├─ Cloud Monitoring            (Cloud Run Job 실패 알림)        │
│  └─ BigQuery                    (processing_log + batch_tracking)│
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### standard.1 대비 변경사항

| 컴포넌트 | standard.1 | light.1 | 주요 변경 |
|----------|----|----|----------|
| 크롤링 Cloud Run Jobs | 포함 | 제거 | 후속 프로젝트 분리 |
| Cloud Scheduler | 포함 | 제거 | 크롤링 제거에 따라 |
| Looker Studio | 포함 | 제거 | BigQuery 직접 쿼리 |
| Makefile | 선택적 | Phase 1 필수 | standard.24: 명시적 도입 |
| Cloud Workflows | 권장 | Phase 2 필수 | standard.24: 명시적 도입 |
| Neo4j 계획 | Free→Professional | Free→Professional | standard.1-3: Phase 2 전 반드시 전환 |
| Embedding 모델 | text-embedding-005 + gemini-embedding-001 비교 후 확정 | 동일 (standard.22 통일 유지) | standard.22 |
| GCS 백업 | 없음 | backups/ 추가 | standard.20: versioning + APOC export |
| BigQuery 추적 | processing_log만 | + batch_tracking | standard.1-5: checkpoint/재시작 |
| 문서 파싱 PoC | 미정 | 3가지 비교 (HWP) | standard.1-2: Phase 0에 포함 |

---

## 3. 파이프라인 DAG (light.1 간소화)

```
[Phase 0] API 검증 + PoC (2.5주)
    │
    ▼ 의사결정 완료
    │
[Phase 1] (6.5~7주)
    │
    ├─ Pipeline A (CompanyContext)  ──┐
    │   (DE: 전처리 병행)              │
    │                                 ├──→ C (Graph 적재) ──→ D (테스트+검증+백업)
    ├─ Pipeline B (CandidateContext) ─┘
    │   (Batch API 대기 중 Graph 선행)
    │
    ▼ MVP 1,000건 데모 (Week 9.5~10)
    │
[Phase 2] (4~5주)
    │
    ├─ 전체 450K Batch 처리 ──┐
    │                          ├──→ 전체 Graph + Embedding + Mapping
    ├─ 품질 평가 (병행) ───────┘
    │
    ▼ 전체 KG 완성 (Week 13~15)
```

---

## 4. 인력 배치 (light.1 — 2인 최적화)

```
         Week 1    Week 2    Week 3    Week 4    Week 5    Week 6    Week 7    Week 8    Week 9    Week 10
DE:    [──── Phase 0 환경+데이터 ────][── 전처리 ──][──────── CandidateCtx ────────][Graph+Map][테스트+백업]
MLE:   [──── Phase 0 PoC+검증 ──────][CompanyCtx ][──────── CandidateCtx ────────][Graph+Map][검증+OrgER]

         Week 10   Week 11   Week 12   Week 13   Week 14   Week 15
DE:    [──────────── 전체 Batch 처리 + Graph 적재 ──────────────────]
MLE:   [── 품질평가 ──][──── 전체 Embedding + Mapping ─────][서빙]
```

### Phase별 역할 분담

| Phase | DE | MLE |
|-------|------|------|
| Phase 0 | GCP 환경 구성, 데이터 업로드, 프로파일링 | API 검증, LLM PoC, Embedding 비교 |
| Phase 1 전반 | 전처리 모듈 (파싱/분할/PII/중복) | CompanyContext (NICE/LLM/Evidence) |
| Phase 1 중반 | Batch API 인프라 (요청생성/제출/폴링) | CandidateContext 모델 + 프롬프트 |
| Phase 1 후반 | Graph 적재 + Embedding | MappingFeatures + 검증 |
| Phase 2 | 전체 Batch 운영 + Graph 적재 | 품질 평가 + Embedding + 서빙 |

---

## 5. 의사결정 포인트 (light.1 — 6개, standard.1 기반)

| 시점 | 의사결정 | 입력 데이터 | 실패 시 대응 | standard.1 연계 |
|------|---------|-----------|------------|--------|
| Week 1.5 (0-B 완료) | **Embedding 모델 확정** | text-embedding-005 vs gemini-embedding-001 (한국어 검증) | text-embedding-005 (768d) | standard.22 |
| Week 1.5 (0-B 완료) | **HWP 파싱 방법 확정** | LibreOffice vs pyhwp vs Gemini 멀티모달 성능 비교 | LibreOffice (가장 안정) | standard.1-2 |
| Week 2.5 (0-C 완료) | **LLM 모델 선택** | Haiku vs Sonnet 품질·비용 비교 (50건, 한국어 토큰 보정) | Haiku Batch (한국어 $0.00300/건) | standard.21 |
| Week 2.5 (0-C 완료) | **PII 전략 확정** | 법무 결론 + 마스킹 영향 테스트 (Blocking) | 법무 승인 후 진행 | standard.1-8 |
| Week 2.5 (Phase 0 완료) | **Graph DB 플랜** | 예상 노드 수 계산 + Neo4j Free vs Professional | Free → Week 10 전환 예정 | standard.1-3 |
| Pre-Phase 0 | **Batch API quota/rate limit 사전 확인** | GCP quota 신청 + 동시 5 batch (축소 가능성) | 동시 3 batch로 축소 | standard.1-4 |

### standard.1에서 유지된 의사결정

| 의사결정 | standard.1 결정 | light.1 상태 | 비고 |
|---------|--------|--------|------|
| 오케스트레이션 도구 | Makefile (Phase 1) + Cloud Workflows (Phase 2) | 확정 | standard.24 |
| 크롤링 전략 | 후속 프로젝트 분리 | 확정 | standard.1-9 제외 |
| Knowledge Distillation | Phase 3/후속 분리 | 확정 | standard.25 |
| 테스트 인프라 | pytest + deepdiff + Golden 50건 | 확정 | standard.1-6 |

---

## 6. 위험 요소 및 완화 (standard.1 기반)

| 위험 | 영향 | 발생 확률 | 완화 전략 | standard.1 항목 |
|------|------|----------|----------|--------|
| 법무 PII 불허 | 마스킹 불가능→시나리오 C 전환 | 중 | Pre-Phase 0에 blocking 검토 | standard.1-8 |
| Batch API quota 부족 | Phase 2 처리 지연 | 낮 | Pre-Phase 0에 사전 확인 + 동시 5→3 축소 | standard.1-4 |
| Neo4j Free 노드 한계 초과 | Phase 2 적재 불가 | 높 | Week 10에 Professional tier 전환 (사전 예산 책정) | standard.1-3 |
| HWP 파싱 성능 저조 | Phase 0 지연 | 중 | LibreOffice 기본값, 3가지 병행 검증 | standard.1-2 |
| LLM 파싱 실패율 > 5% | 품질 기준 미달 | 중 | 3-tier 구현 필수 (reject/tier2/tier3) |  |
| 한국어 토큰 과다 예상 | 비용 초과 | 중 | 한글 1자 ≈ 2-3 tokens로 재추정 (이력서 1건 $0.00300) | standard.21 |
| Batch API checkpoint 실패 | Phase 2 재처리 필요 | 낮 | BigQuery batch_tracking + processing_log 기반 재시작 | standard.1-5 |
| NICE DB 접근 지연 | CompanyContext 품질 저하 | 중 | DART + 사업자등록으로 대체 |  |
| Phase 0 HWP/Embedding PoC 미달 | 접근법 재검토 필요 | 낮 | Week 2.5에서 Go/No-Go 결정 |  |
| 인력 가용성 (2인 풀타임) | 전체 일정 지연 | 중 | 크리티컬 패스 (Phase 1 CandidateCtx) 집중 |  |

### Go/No-Go 게이트 (Week 2.5)

Phase 0 완료 시 다음 기준으로 Phase 1 진행 여부를 결정한다:

| 기준 | 최소 통과 | 미달 시 대응 | standard.1 연계 |
|------|----------|------------|--------|
| LLM 추출 품질 (50건) | tier1 > 80% | 프롬프트 재설계 (+1주) | standard.1-6 |
| Embedding 한국어 분별력 | 유사 > 비유사 (p < 0.05) | 모델 변경 (text-embedding-005 ↔ gemini-embedding-001) | standard.22 |
| HWP 파싱 성공률 | > 90% | 다른 파싱 방법 우선순위 변경 (+0.5주) | standard.1-2 |
| 비용 추정 대비 실제 (한국어 토큰) | ±30% 이내 | 예산 재조정 | standard.21 |
| Batch API quota 확인 | 동시 5 batch 승인 | 동시 3 batch로 축소 (Phase 2 기간 연장 가능) | standard.1-4 |
| 법무 PII 승인 | 마스킹 적용 가능 | 불가 시 데이터 수집 전략 변경 (시나리오 C) | standard.1-8 |

---

## 7. standard.1 대비 light.1 종합 비교

| 항목 | standard.1 (26~33주) | light.1 (13~15주) | 변화 |
|------|-------------|-------------|------|
| 총 일정 | 26~33주 | **13~15주** | **-50% 단축** |
| 첫 데모 (MVP) | ~18주 | **~9.5~10주** | **-47% 단축** |
| 인력 | DE 1 + MLE 1 + 도메인 전문가 PT | **동일** | 변화 없음 |
| Phase 0 | 4~5주 | **2.5주** | **-2주 압축** |
| Phase 1 | 10~12주 | **6.5~7주** | **-4~5주 압축** |
| Phase 2 | 12~16주 | **4~5주** | **-8~11주 압축** |
| 크롤링 | 4주 포함 | **후속 분리** | 스코프 축소 |
| 증분 처리 | 포함 | **후속 분리** | 스코프 축소 |
| Looker Studio | 포함 | **BigQuery 직접 쿼리** | 운영 최소화 |
| 오케스트레이션 | Makefile + Cloud Workflows | **동일 유지** | 변화 없음 |
| 품질 평가 대상 | 400건 Gold Set | **200건 Gold Set** | 적정 조정 |
| 예상 비용 (standard.1 한국어) | ~$8,812 | **~$4,085** | **-54% 절감** |
| Phase 0 예상 비용 | ~$186 | **~$83** | standard.21 한국어 토큰 기준 |
| Phase 1 예상 비용 | ~$94 | **~$42** | standard.21 한국어 토큰 기준 |
| Phase 2 LLM 비용 | ~$2,052 | **~$934** | 200건 Gold Label $2,920 포함 |
| 인프라 비용 (1개월) | ~$150 | **~$106** | 크롤링 제거 |
| 원화 예상 총액 | ~620만원 | **~560만원** | standard.21 기준 |
| 산출물 | 전체 KG + 크롤링 + 운영 | **전체 KG + 품질 리포트** | 스코프 축소 |
| 위험도 | 중간 | **중간** | 동일 (PII/Batch API blocking) |
| standard.1 개선사항 유지 | - | **standard.2,2,3,4,5,6,8,10,11,12,14,15,16 모두 포함** | 품질 보증 |

---

## 8. 후속 프로젝트 범위 (light.1 이후, standard.1 기반)

light.1 완료 후 별도 프로젝트로 진행할 항목:

| 항목 | 예상 기간 | 의존성 | standard.1 항목 |
|------|----------|-------|--------|
| 크롤링 파이프라인 (홈페이지+뉴스) | 4주 | light.1 CompanyContext 스키마 | standard.1-9, standard.23 제외 |
| 크롤링 → CompanyContext 보강 | 1주 | 크롤링 파이프라인 |  |
| 증분 처리 자동화 (Cloud Scheduler) | 1주 | light.1 E2E 파이프라인 |  |
| Looker Studio 대시보드 | 1주 | BigQuery 테이블 |  |
| ML Knowledge Distillation | 2주 | light.1 품질 평가 결과 | standard.25 |
| DS/MLE 서빙 인터페이스 확장 | 1주 | light.1 mapping_features |  |
| VPC Service Controls / 보안 강화 | 2주 | 프로덕션 준비 | 선택적 |
