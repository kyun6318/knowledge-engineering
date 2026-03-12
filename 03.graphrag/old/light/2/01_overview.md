# GraphRAG GCP Staged Fast Fail 계획 light.2

> **목적**: light.1 리뷰 결과를 반영하여 **현실적 타임라인**으로 보정.
> light.1의 "Staged Fast Fail" 철학과 Go/No-Go 게이트는 유지하되, 개발 시간 추정의 정밀도를 높인다.
>
> **light.1 → light.2 핵심 변경**:
> - [light.2-1] Pre-Phase 0(2~3주)를 전체 타임라인에 **명시적** 포함
> - [light.2-2] Phase 1-C(Graph+Embedding+Mapping)를 1주 → **2주**로 확대 (Org ER + 모듈 개발 시간)
> - [light.2-3] Phase 1-B에 **프롬프트 튜닝 전용 0.5주** 추가
> - [light.2-4] Phase 1-A에 **통합 테스트 0.5주 버퍼** 추가
> - [light.2-5] Phase 1-D를 **1주 확정** (0.5주 옵션 제거)
> - [light.2-6] Phase 2에서 Cloud Workflows 제거 → **Makefile + 스크립트** 유지 (후속 프로젝트로 이관)
> - [light.2-7] Phase 2 타임라인에 **3-시나리오**(낙관/기본/비관) 반영
> - [light.2-8] Gold Test Set 라벨링을 **Phase 1 후반(Week 11~12)**부터 선행 시작
> - [light.2-9] 인력 가용률 **80% 시나리오**를 병행 제시
> - [light.2-10] Dead-letter 재처리를 **별도 0.5주 태스크**로 격상
> - [light.2-11] Vertex AI Embedding **QPM/TPM 한도 확인**을 Phase 0에 추가
> - [light.2-12] Document AI 검증을 **선택적(nice-to-have)**으로 격하
> - [light.2-13] 도메인 전문가 **주차별 투입 시간** 명시
> - [light.2-14] 예산에 **20% contingency** 추가
> - [light.2-15] **데이터 전송 테스트**(10GB 샘플)를 Pre-Phase 0에 추가
>
> **light.1에서 유지하는 것 (변경 없음)**:
> - Fast Fail 부적합 분석 (00_fast_fail_analysis.md)
> - Phase 0 Go/No-Go 게이트 6개 의사결정
> - Checkpoint/재시작 전략 (BigQuery processing_log + batch_tracking)
> - pytest + deepdiff 테스트 인프라 + Golden 50건 regression test
> - LLM 파싱 실패 3-tier 구현
> - Makefile 오케스트레이션 (Phase 1 AND Phase 2)
> - 크롤링 후속 프로젝트 분리
> - 한국어 토큰 보정 (×1.88)
>
> 작성일: 2026-03-08

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| `00_fast_fail_analysis.md` | Fast Fail 전략 부적합 분석 (light.1와 동일) |
| `01_overview.md` (본 문서) | 전체 구조, 타임라인, 의사결정 포인트 |
| `02_phase0_validation_poc.md` | Pre-Phase 0 + Phase 0: 사전 준비 + API 검증 + PoC (2~3주 + 2.5주) |
| `03_phase1_mvp_pipeline.md` | Phase 1: MVP 파이프라인 (9주) |
| `04_phase2_full_processing.md` | Phase 2: 전체 데이터 처리 + 품질 평가 (5~6주) |
| `05_cost_monitoring.md` | 비용 추정 + 최소 모니터링 |

---

## 1. 전체 타임라인

```
Pre-Phase 0: 사전 준비 (2~3주, Phase 0과 독립)
  ├─ 법무 PII 검토 요청 (1~3주)                ──┐
  ├─ Batch API quota/Tier 확인 (1~2주)          ──┤ 완전 병렬
  ├─ 데이터 전송 테스트 (10GB 샘플, 1일) [light.2-15] ──┤
  └─ 도메인 전문가 확보 확인                     ──┘
  → Pre-Phase 완료 후 Phase 0 시작

Phase 0: 기반 구축 + API 검증 + PoC (2.5주)
  ├─ 0-A: GCP 환경 + API 검증 (3일)          ──┐
  ├─ 0-B: 데이터 탐색 + 프로파일링 (1주)       ──┤ 완전 병렬
  ├─ 0-C: LLM 추출 PoC (1.5주)               ──┤
  └─ 0-D: 인프라 셋업 (1주)                   ──┘
  → Week 2.5: 의사결정 완료

Phase 1: MVP 파이프라인 (9주) [light.1: 6.5~7주]
  ├─ 1-A: 전처리 + CompanyContext (2.5주, 병행) [light.2-4: +0.5주 통합 테스트]
  ├─ 1-B: CandidateContext (3.5주)              [light.2-3: +0.5주 프롬프트 튜닝]
  ├─ 1-C: Graph + Embedding + Mapping (2주)     [light.2-2: +1주 Org ER + 모듈 개발]
  └─ 1-D: 테스트 + 검증 + 백업 (1주)            [light.2-5: 0.5주 옵션 제거]
  → Week 14: MVP 1,000건 E2E 동작
  → Week 11~12: Gold Test Set 라벨링 선행 시작 [light.2-8]

Phase 2: 전체 처리 + 품질 평가 (5~6주) [light.1: 4~5주]
  ├─ 2-0: Neo4j Professional 전환 (1일)
  ├─ 2-A: 450K Batch 처리 (3~4주)              ──┐
  ├─ 2-B: 품질 평가 (0.5주, Gold Set 선행 완료)  ──┤ 병렬
  ├─ 2-C: Graph 전체 적재 + Embedding (1~2주)   ──┤
  ├─ 2-D: Dead-letter 재처리 (0.5주) [light.2-10]    ──┤
  └─ 2-E: 최소 서빙 인터페이스 (0.5주)          ──┘
  → Week 19~20: 전체 KG 완성 + 품질 리포트

후속 프로젝트 (별도):
  ├─ 크롤링 파이프라인 (4주)
  ├─ 증분 처리 + 운영 자동화 (2주)
  ├─ Cloud Workflows 도입 [light.2-6: light.1에서 이관]
  └─ Knowledge Distillation (선택)
```

### light.1 → light.2 일정 변경 상세

| Phase | light.1 | light.2 | 차이 | 사유 |
|-------|----|----|------|------|
| Pre-Phase 0 | (미포함) | **2~3주** | +2~3주 | [light.2-1] 법무 PII + Batch API quota + 데이터 전송 테스트 |
| Phase 0 | 2.5주 | **2.5주** | 0 | 적정 (Document AI 축소 → Embedding QPM 확인 교체) |
| Phase 1-A | 2주 | **2.5주** | +0.5주 | [light.2-4] JSON 스키마 합의 + 통합 테스트 버퍼 |
| Phase 1-B | 3주 | **3.5주** | +0.5주 | [light.2-3] 프롬프트 튜닝 전용 시간 |
| Phase 1-C | 1주 | **2주** | +1주 | [light.2-2] Org ER 한국어 회사명 + 모듈 개발 시간 |
| Phase 1-D | 0.5~1주 | **1주** | +0~0.5주 | [light.2-5] 테스트 최소 1주 확정 |
| Phase 2 | 4~5주 | **5~6주** | +1주 | [light.2-10] Dead-letter + 품질 미달 버퍼 |
| Cloud Workflows | Phase 2 포함 | **후속** | -0.5주 | [light.2-6] 복잡도 감소 |
| **코어 합계** | **13~15주** | **16.5~17.5주** | +2.5~3.5주 | |
| **Pre-Phase 포함** | **13~15주** | **18.5~20.5주** | +5.5주 | |

### 인력 가용률 시나리오 [light.2-9]

| 시나리오 | 코어 기간 | Pre-Phase 포함 | 첫 MVP 데모 |
|----------|----------|---------------|------------|
| **100% 풀타임** | 16.5~17.5주 | 18.5~20.5주 | ~14주 (Pre 포함 ~16~17주) |
| **80% 가용 (권장 기준)** | ~20~22주 | ~22~25주 | ~17주 (Pre 포함 ~19~21주) |

> **80% 가용률 적용 방법**: 개발 작업(코딩, 테스트, 검증)에만 1.25배 적용.
> Batch API 대기 시간, Pre-Phase 외부 대기 등 **비개발 대기 시간**에는 미적용.

---

## 2. GCP 아키텍처 (light.2 — light.1에서 Cloud Workflows 제거)

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
│  └─ Makefile + 모니터링 스크립트  (Phase 1 AND Phase 2) [light.2-6]   │
│                                                                  │
│  [LLM API (외부)]                                                │
│  ├─ Anthropic Batch API         (Claude Haiku 4.5 — Primary)     │
│  └─ Anthropic API               (Claude Sonnet 4.6 — PoC/비교)  │
│                                                                  │
│  [Embedding API]                                                 │
│  ├─ Vertex AI text-embedding-005     (768d — Primary)           │
│  └─ Vertex AI gemini-embedding-001   (비교, 한국어 검증)         │
│                                                                  │
│  [모니터링 — 최소 구성]                                           │
│  ├─ Cloud Monitoring            (Cloud Run Job 실패 알림)        │
│  └─ BigQuery                    (processing_log + batch_tracking)│
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### light.1 → light.2 아키텍처 변경

| 컴포넌트 | light.1 | light.2 | 변경 사유 |
|----------|----|----|----------|
| Cloud Workflows | Phase 2 필수 | **후속 프로젝트** | [light.2-6] 복잡도 감소, Phase 2도 Makefile로 충분 |
| Makefile | Phase 1만 | **Phase 1 + Phase 2** | [light.2-6] 일관된 오케스트레이션 |

> **Cloud Workflows 제거 근거**: Phase 2는 본질적으로 "Phase 1 파이프라인을 대규모 반복 실행"하는 것.
> Makefile + 모니터링 스크립트로 충분히 운영 가능하며, Cloud Workflows는 증분 처리 자동화 시 도입이 적합.

---

## 3. 파이프라인 DAG (light.2)

```
[Pre-Phase 0] 사전 준비 (2~3주, 병렬)
    │
    ▼ 법무/Batch API/데이터 전송 준비 완료
    │
[Phase 0] API 검증 + PoC (2.5주)
    │
    ▼ 의사결정 완료 (6개 항목)
    │
[Phase 1] (9주)
    │
    ├─ Pipeline A (전처리 + CompanyContext, 2.5주) ──┐
    │                                                 │
    ├─ Pipeline B (CandidateContext, 3.5주)          ──┤ 직렬
    │   (Batch API 대기 중 Graph/Org ER 선행)         │
    │                                                 │
    ├─ Pipeline C (Graph + Embedding + Mapping, 2주)──┤
    │   (Org ER 2~3일 포함)                           │
    │                                                 │
    └─ Pipeline D (테스트 + 검증 + 백업, 1주) ────────┘
    │
    │  Week 11~12: Gold Test Set 라벨링 시작 (MLE 병행) [light.2-8]
    │
    ▼ MVP 1,000건 데모 (Week ~14, Pre 포함 ~16~17)
    │
[Phase 2] (5~6주)
    │
    ├─ 전체 450K Batch 처리 ──┐
    │                          ├──→ 전체 Graph + Embedding + Mapping
    ├─ 품질 평가 (Gold Set 완료)┤
    ├─ Dead-letter 재처리 ─────┘
    │
    ▼ 전체 KG 완성 (Week ~19~20, Pre 포함 ~21~23)
```

---

## 4. 인력 배치 (light.2 — 80% 가용률 고려)

### 100% 풀타임 기준

```
         Pre-P0    Week 1    Week 2    Week 3    Week 4    Week 5    Week 6
DE:    [법무/quota][──── Phase 0 환경+데이터 ────][──── 전처리 (2.5주) ────]
MLE:   [전문가확보][──── Phase 0 PoC+검증 ──────][── CompanyCtx (2.5주) ──]

         Week 7    Week 8    Week 9    Week 10   Week 11   Week 12
DE:    [───────── CandidateCtx (3.5주) ──────────────────][── Graph ──
MLE:   [───────── CandidateCtx + 프롬프트 튜닝 ──────────][── Graph ──

         Week 12   Week 13   Week 14   Week 15   Week 16   Week 17
DE:    ─ + Emb + Map (2주) ──][── 테스트+백업 1주 ──][───── Batch 처리 ──
MLE:   ─ + Org ER (2주) ─────][── 검증+Go/No-Go ───][── 품질평가 ──────

         Week 18   Week 19   Week 20
DE:    ─────── Graph 적재 + Dead-letter ──────]
MLE:   ─── Embedding + Mapping + 서빙 ───────]
```

### 도메인 전문가 투입 스케줄 [light.2-13]

| 시점 | 작업 | 투입 시간 |
|------|------|----------|
| Phase 0 Week 2~3 | PoC 50건 품질 검증 | 8시간 (1일) |
| Phase 1 Week 11~12 | Gold Test Set 라벨링 시작 (100건) | 20시간 (전문가 A) |
| Phase 1 Week 13~14 | Gold Test Set 라벨링 완료 (100건) | 20시간 (전문가 A) |
| Phase 2 Week 15~16 | Gold Test Set 추가 라벨링 (100건) | 20시간 (전문가 B) |
| Phase 2 Week 16 | Cohen's κ 검증 참여 | 4시간 |

> **전문가 B 확보**: Phase 1 후반(Week 10)까지 확보 완료 필요 → Pre-Phase 2 blocking dependency

---

## 5. 의사결정 포인트 (light.2 — light.1 + Embedding QPM)

| 시점 | 의사결정 | 입력 데이터 | 실패 시 대응 |
|------|---------|-----------|------------|
| Week 1.5 | **Embedding 모델 확정** | text-embedding-005 vs gemini-embedding-001 | text-embedding-005 기본값 |
| Week 1.5 | **HWP 파싱 방법 확정** | LibreOffice vs pyhwp vs Gemini 비교 | LibreOffice 기본값 |
| Week 2.5 | **LLM 모델 선택** | Haiku vs Sonnet 50건 비교 | Haiku Batch |
| Week 2.5 | **PII 전략 확정** | 법무 결론 + 마스킹 영향 테스트 | 마스킹 적용 진행 |
| Week 2.5 | **Graph DB 플랜** | 예상 노드 수 + Neo4j Free vs Professional | Free → Week 14 전환 |
| Pre-Phase 0 | **Batch API quota/rate limit** | Tier 확인 + 동시 batch 수 | 동시 3 batch로 축소 |
| Week 1.5 | **[light.2-11] Embedding QPM/TPM 한도** | Vertex AI quota 페이지 확인 | quota 증가 요청 |

### Go/No-Go 게이트 (Week 2.5)

light.1와 동일. 6개 기준 모두 유지.

---

## 6. 위험 요소 및 완화 (light.2 추가)

### light.1에서 유지하는 위험 요소

light.1 전체 위험 요소 테이블 유지 (법무 PII, Batch API quota, Neo4j Free 한계, HWP 파싱, LLM 실패율, 한국어 토큰, checkpoint, NICE DB, Phase 0 PoC 미달, 인력 가용성).

### light.2에서 추가하는 위험 요소

| 위험 | 영향 | 발생 확률 | 완화 전략 | light.2 태그 |
|------|------|----------|----------|---------|
| **Batch API 응답 시간 변동** | Phase 2 기간 6~8주 연장 | 중 | Phase 0에서 5~10건 실측 + 3-시나리오 타임라인 | [light.2-7] |
| **Anthropic 가격 변경** | LLM 비용 2배 증가 | 낮 | Batch 50% 할인 영구 여부 확인 + Gemini Flash 대체 경로 | [light.2-14] |
| **Vertex AI Embedding QPM 한도 초과** | Phase 2 Embedding 지연 | 중 | Phase 0에서 QPM 확인 + quota 증가 요청 | [light.2-11] |
| **도메인 전문가 B 미확보** | Gold Test Set 라벨링 지연 | 중 | Week 10까지 확보 → Phase 2 blocking | [light.2-13] |
| **150GB GCS 업로드 지연** | Phase 0-B 프로파일링 불가 | 중 | Pre-Phase에서 10GB 샘플 전송 테스트 | [light.2-15] |
| **Anthropic Batch API 서비스 중단** | Phase 2 전체 중단 | 낮 | Gemini Flash Batch 대체 경로 사전 검증 | |

### Batch API 3-시나리오 [light.2-7]

| 시나리오 | 라운드당 시간 | 450 chunks / 10 동시 | Phase 2 Batch 기간 |
|----------|------------|---------------------|-------------------|
| **낙관** | 6시간 | 45 라운드 × 6h = 11일 | ~2.5주 |
| **기본** | 12시간 | 45 라운드 × 12h = 22일 | ~4.5주 |
| **비관** | 24시간 | 45 라운드 × 24h = 45일 | ~9주 |

> Phase 0에서 Batch API 5~10건 실측하여 시나리오 확정.
> 비관 시나리오 발생 시 동시 batch 수 증가 요청 또는 Gemini Flash 병행으로 대응.

---

## 7. light.1 → light.2 종합 비교

| 항목 | light.1 (13~15주) | light.2 (16.5~17.5주) | 변화 |
|------|-------------|-----------------|------|
| 총 코어 일정 | 13~15주 | **16.5~17.5주** | +2.5~3.5주 |
| Pre-Phase 포함 | 13~15주 | **18.5~20.5주** | +5.5주 |
| 80% 가용률 | (미제시) | **~20~22주 코어** | 현실적 시나리오 |
| 첫 데모 (MVP) | ~9.5~10주 | **~14주** | +4주 (현실적) |
| Phase 0 | 2.5주 | **2.5주** | 변화 없음 |
| Phase 1 | 6.5~7주 | **9주** | +2~2.5주 |
| Phase 2 | 4~5주 | **5~6주** | +1주 |
| Cloud Workflows | Phase 2 포함 | **후속 프로젝트** | 스코프 축소 |
| Gold Test Set | Phase 2 집중 | **Phase 1 후반 선행** | 리스크 분산 |
| 인력 가용률 | 100% only | **100% + 80%** | 시나리오 추가 |
| Batch API 시나리오 | 단일 (6h) | **3-시나리오** | 리스크 가시화 |
| Dead-letter | 1회 수동 재시도 | **별도 0.5주** | 태스크 격상 |
| 도메인 전문가 | 파트타임 (비구체적) | **주차별 투입 명시** | 투명도 향상 |
| 예상 비용 | ~$4,943 | **~$5,100 (+contingency ~$6,100)** | +20% contingency |
| 원화 예상 | ~677만원 | **~700만원 (+contingency ~836만원)** | |

---

## 8. 후속 프로젝트 범위 (light.2 이후)

light.1와 동일 + Cloud Workflows 추가:

| 항목 | 예상 기간 | 의존성 |
|------|----------|-------|
| 크롤링 파이프라인 (홈페이지+뉴스) | 4주 | light.2 CompanyContext 스키마 |
| 크롤링 → CompanyContext 보강 | 1주 | 크롤링 파이프라인 |
| **Cloud Workflows 오케스트레이션** [light.2-6] | **1주** | **light.2 E2E 파이프라인** |
| 증분 처리 자동화 (Cloud Scheduler) | 1주 | Cloud Workflows |
| Looker Studio 대시보드 | 1주 | BigQuery 테이블 |
| ML Knowledge Distillation | 2주 | light.2 품질 평가 결과 |
| DS/MLE 서빙 인터페이스 확장 | 1주 | light.2 mapping_features |
