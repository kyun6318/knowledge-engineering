# 비용 추정 + 모니터링 + 운영

> ★ v4 R2: **이 문서가 비용의 Single Source of Truth**. Overview §14는 본 문서를 참조.
>
> 전체 라이프사이클 비용 통합 추정 + 모니터링 구성 + 보안 설계
>
> **v3 대비 변경**:
> - R2: 비용 Single Source of Truth 지정 (Overview §14 불일치 해소)
> - R5: Phase 2 8주 → 9주 (+1주 인프라 비용 추가)
> - O6: $10 이하 소규모 항목은 "기타"로 통합 (Phase 0~1)

---

## 1. 비용 추정

### 1.1 Phase 0: 환경 + PoC (1주)

| 서비스 | 비용 |
|---|---|
| Anthropic API (PoC 20건 + Sonnet 비교 + 적응형 호출 검증) | ~$7 |
| 기타 (Gemini 테스트, Embedding, Batch 실측, GCS/BQ 초기) | ~$3 |
| **Phase 0 합계** | **~$10** |

> ★ v4 O6: $1 미만 항목(Vertex AI Embedding $0.001 등)을 "기타"로 통합.
> ★ v4 R3: Phase 0에서 CMEK 비용 제거 (Phase 1-B로 이동).

### 1.2 Phase 1: Core Candidate MVP (5주)

| 서비스 | 비용 |
|---|---|
| Anthropic API (Batch 1,000건 + 프롬프트 튜닝 ~200건) | ~$24 |
| Cloud Run (크롤링 Job + 전처리 + API 서비스) | ~$11 |
| 기타 (Embedding, Neo4j Free $0, Scheduler $0, GCS/BQ) | ~$2 |
| **Phase 1 합계** | **~$37** |

> ★ v4 R3: CMEK 버킷 생성 비용(KMS $0.06/월) 여기에 포함.

### 1.3 Phase 2: 파일 이력서 + 전체 처리 (★ 9주)

#### LLM 비용

| 서비스 | 비용 | 비고 |
|---|---|---|
| Anthropic Batch API (600K, 적응형 호출) | $1,488 | v12 M1 |
| Anthropic API (재처리/에러 ~6,000건) | ~$30 | |
| Anthropic API (Parser 프롬프트 ~300건) | ~$2 | |
| 파일 섹션 분리 LLM 폴백 (30K건, ★ **Batch API**, v12 S1) | ~$60 | ★ v4 R4 |
| Vertex AI Embedding (2.6M건) | ~$52 | |
| Embedding Egress (서울→US) | ~$4 | |
| Dead-letter 재처리 (~18,000건) | ~$54 | |
| **Phase 2 LLM 합계** | **~$1,690** | |

> 적응형 호출 비용 상세:
> - 1-pass (80%): 480K × $0.00158 = $758 (Batch: $379)
> - N+1 pass (20%): 120K × 4.5회 × $0.0008 = $432 (Batch: $216)
> - Batch 합계: $595

#### 인프라 비용 (★ 9주)

| 서비스 | 월 비용 | ★ 9주 비용 | v3(8주) 대비 |
|---|---|---|---|
| Cloud Run Jobs | ~$32/월 | ~$84 | +$9 |
| GCS | $6/월 | ~$16 | +$2 |
| BigQuery | $5/월 | ~$14 | +$2 |
| Neo4j AuraDB Professional | $65~200/월 | ~$225~540 | +$25~60 |
| Cloud Monitoring + Logging | ~$7/월 | ~$20 | +$2 |
| **Phase 2 인프라 합계** | | **~$359~674** | +$40~75 |

#### Phase 2 소계

| 항목 | 비용 |
|---|---|
| LLM | ~$1,690 |
| 인프라 | ~$359~674 |
| **Phase 2 합계** | **~$2,049~2,364** |

### 1.4 Phase 3: 기업 정보 + 매칭 (★ 6주)

#### LLM 비용

| 서비스 | 비용 |
|---|---|
| Anthropic Batch API (CompanyContext 10K JD) | $4 |
| Anthropic Batch API (Vacancy 추출 10K) | $30 |
| Anthropic API (프롬프트 튜닝 + 검증) | ~$15 |
| Anthropic API (Organization ER LLM 2차) | ~$5 |
| MAPPED_TO 소규모 테스트 (N3) | ~$1 |
| Vertex AI Embedding (vacancy + company) | ~$0.2 |
| **Phase 3 LLM 합계** | **~$55** |

#### 인프라 비용 (★ 6주)

| 서비스 | 월 비용 | ★ 6주 비용 | v3(7주) 대비 |
|---|---|---|---|
| Neo4j Professional | $150~300/월 | ~$225~450 | -$35~75 |
| Cloud Run + GCS + BigQuery | ~$15/월 | ~$23 | -$3 |
| **Phase 3 인프라 합계** | | **~$248~473** | -$38~78 |

#### Phase 3 소계

| 항목 | 비용 |
|---|---|
| LLM | ~$55 |
| 인프라 | ~$248~473 |
| **Phase 3 합계** | **~$303~528** |

### 1.5 Phase 4: 외부 보강 + 운영 (4주)

#### LLM 비용

| 서비스 | 비용 |
|---|---|
| Gemini API (크롤링 LLM 추출, 1,000기업) | ~$11 |
| Anthropic API (Gold Label 검증) | ~$20 |
| Vertex AI Embedding (5,000건) | ~$0.1 |
| **Phase 4 LLM 합계** | **~$31** |

#### 인프라 비용 (4주)

| 서비스 | 월 비용 | 4주 비용 |
|---|---|---|
| Neo4j Professional | $150~300/월 | ~$150~300 |
| Cloud Run | ~$20/월 | ~$20 |
| GCS + BigQuery | ~$5/월 | ~$5 |
| Cloud Workflows + Scheduler | ~$2/월 | ~$2 |
| **Phase 4 인프라 합계** | | **~$177~327** |

#### Gold Label 인건비 (N6: 2단계)

| 시나리오 | 비용 |
|---|---|
| Phase 1만 (100건, 기준 충족 시) | ~$2,920 |
| Phase 1+2 (200건, 기준 미달 시) | ~$5,840 |
| (국내 전문가 대안) | (~100~200만원) |

#### Phase 4 소계

| 항목 | 비용 |
|---|---|
| LLM | ~$31 |
| 인프라 | ~$177~327 |
| Gold Label | ~$2,920~5,840 |
| **Phase 4 합계** | **~$3,128~6,198** |

### 1.6 전체 비용 총괄

> ★ v4 R2: **이 테이블이 비용의 Single Source of Truth**.

| Phase | LLM | 인프라 | Gold Label | **합계** |
|---|---|---|---|---|
| Phase 0 (1주) | $7 | $3 | — | **$10** |
| Phase 1 (5주) | $24 | $13 | — | **$37** |
| Phase 2 (★ 9주) | $1,690 | $359~674 | — | **$2,049~2,364** |
| Phase 3 (★ 6주) | $55 | $248~473 | — | **$303~528** |
| Phase 4 (4주) | $31 | $177~327 | $2,920~5,840 | **$3,128~6,198** |
| **총합계** | **$1,807** | **$800~1,490** | **$2,920~5,840** | **$5,527~9,137** |
| **원화** | | | | **~758~1,253만** |

> v3($5,523~9,138) 대비:
> - Phase 2 인프라: +$40~75 (R5: 9주로 연장)
> - Phase 3 인프라: -$38~78 (R5: 6주로 축소)
> - 순 변동: **±$0~3** (거의 동일)
> - Phase 2+3 합산 기간은 동일 (15주)하므로 비용 변동 미미
>
> ★ v4: Overview §14는 이 테이블을 참조. 별도 비용 테이블을 유지하지 않음 (R2).

### 1.7 운영 단계 월간 비용 (Phase 4 이후)

| 서비스 | 월 비용 |
|---|---|
| Neo4j AuraDB Professional | $100~200 |
| GCS + BigQuery | ~$18 |
| Cloud Run Jobs (일일 크롤링 + 증분) | ~$15 |
| Cloud Scheduler | ~$2 |
| Cloud Monitoring + Logging | ~$10 |
| Cloud Workflows | ~$1 |
| **운영 월간 합계** | **~$146~246** |

---

## 2. 모니터링 — Phase별 점진적 구축

### Phase 0-2: 최소 모니터링

> v3와 동일 (BigQuery 쿼리 3종 + Slack 수동).

v12 품질 메트릭 모니터링 추가

```sql
-- v12 품질 메트릭 쿼리
-- Q4: PII 누출율 (v12 §3.1, 목표 ≤0.01%)
SELECT
  COUNTIF(pii_detected = TRUE) / COUNT(*) AS pii_leak_rate
FROM graphrag_kg.quality_metrics
WHERE metric_name = 'pii_leak_check'
  AND measured_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY);

-- Q5: 적응형 호출 비율 (v12 M1)
SELECT
  api_provider,
  COUNTIF(call_strategy = '1-pass') AS one_pass,
  COUNTIF(call_strategy = 'n+1') AS n_plus_1,
  COUNT(*) AS total
FROM graphrag_kg.batch_tracking
WHERE processed_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY api_provider;
```

### Phase 2 추가: Alarm 3종

> v3와 동일.

### Phase 4: 전체 모니터링 + Runbook

> v3와 동일 (05_phase4 참조).

---

## 3. 보안 — 서비스 계정 분리

### 서비스 계정 4개 (v3 유지)

| 계정 | 용도 | 권한 |
|------|------|------|
| `kg-crawling` | 크롤링 Job | storage.objectCreator, bigquery.dataEditor |
| `kg-processing` | 전처리 + LLM 추출 | storage.objectViewer/Creator, bigquery.dataEditor, aiplatform.user |
| `kg-loading` | Graph 적재 + API | storage.objectViewer, bigquery.dataViewer, **Neo4j 접근** |
| `kg-pii-reader` | PII 매핑 테이블 읽기 전용 | storage.objectViewer (**kg-pii-mapping 버킷만**) |

### PII 보안 강화 (v12 S2)

```
PII 매핑 테이블:
  저장소: gs://kg-pii-mapping/ (별도 버킷)
  암호화: CMEK (Cloud KMS)
  접근: kg-pii-reader만 읽기 가능
  로그: Cloud Audit Logs 자동 기록
  삭제: 개인정보 삭제 요청 시 해당 JSONL 라인 제거 + GCS 버전 삭제
  ★ v4 R3: 버킷 생성 시점 Phase 1-B (Go 판정 후)

API 보안:
  PII 필드(name, email, phone): API 응답에서 자동 제거 (N2)
  PII 필요 시: 별도 엔드포인트 (인증 강화, Phase 5 검토)
  접근 로그: /candidates/{id} 요청 BigQuery 기록
```

### VPC 네트워크 (v3 유지)

> Phase 4에서 구성 (Neo4j Allowlist).

---

## 4. 리전 선택 (v3 유지)

| 서비스 | 리전 | 근거 |
|---|---|---|
| GCP 프로젝트 | asia-northeast3 (서울) | 데이터 주권, 레이턴시 |
| Vertex AI | us-central1 | Gemini/Embedding API 가용성 |
| Neo4j AuraDB | asia-northeast1 (도쿄) | 서울 미지원, 최소 레이턴시 |

---

## 5. v3 리뷰 반영 추적

| # | v3 리뷰 권장 | v4 반영 | 문서 위치 |
|---|-------------|--------|----------|
| R1 | PII 마스킹 오프셋 버그 수정 | ✅ re.sub 콜백 방식 | 02_phase1 §1-B |
| R2 | 비용 단일 소스 통일 | ✅ 본 문서 §1.6 | 06_cost §1.6, 00_overview §14 참조 |
| R3 | CMEK → Phase 1로 이동 | ✅ Phase 0에서 제거, Phase 1-B로 | 01_phase0, 02_phase1 §1-B |
| R4 | LLM 폴백 Batch API | ✅ split_by_llm_batch() | 03_phase2 §2-1 |
| R5 | Phase 2 → 9주 | ✅ Phase 3 → 6주로 축소 | 03_phase2, 04_phase3 |
| R6 | 처리 우선순위 전략 | ✅ DB 500K 먼저 | 03_phase2 §2-3 |
| R7 | 소프트 삭제 쿼리 마이그레이션 | ✅ Phase 4-4에 태스크 명시 | 05_phase4 §4-4 |
| R8 | DETACH DELETE 4→2단계 | ✅ 단일 트랜잭션 통합 | 05_phase4 §4-4 |
| O3 | Grid search → 수동 비교 | ✅ tune_weights_manual() | 04_phase3 §3-4 |
| O7 | Phase 0 산출물 Must/Should | ✅ 분류 완료 | 01_phase0 산출물 |

### v2 리뷰 반영 추적 (v3에서 반영 완료, v4 유지)

| # | v2 리뷰 권장 | 반영 | 문서 위치 |
|---|-------------|------|----------|
| N1 | AuraDB Auto-Pause health check | ✅ | 02_phase1 §1-D |
| N2 | API PII 필드 정의 | ✅ | 02_phase1 §1-D |
| N3 | MAPPED_TO 규모 추정 | ✅ | 04_phase3 §3-0 |
| N4 | 일일 유입량 확인 | ✅ | 01_phase0 MLE 담당 |
| N5 | Provider 추상화 레이어 | ✅ | 03_phase2 §2-0 |
| N6 | Gold Label 2단계 | ✅ | 05_phase4 §4-3 |
| N7 | 가중치 튜닝 1일 | ✅ | 04_phase3 §3-4 |
| N8 | Neo4j 사이징 검증 | ✅ | 03_phase2 §2-2 |
| N9 | 잔여 배치 주간 리포트 | ✅ | 04_phase3 §3-4 |

### v12 Extraction Logic 반영 추적 (v3에서 반영 완료, v4 유지)

| 변경 ID | 내용 | 반영 | 문서 위치 |
|---------|------|------|----------|
| v12-M1 | 적응형 LLM 호출 | ✅ | 02_phase1 §1-C |
| v12-M2 | v19 canonical 관계명 | ✅ | 전 Phase |
| v12-M3 | 구현 순서 (B→B'→A) | ✅ | 00_overview §4 |
| v12-S1 | Hybrid 섹션 분리 | ✅ + ★ R4 Batch화 | 03_phase2 §2-1 |
| v12-S2 | PII GCS CMEK | ✅ + ★ R3 Phase 1 이동 | 02_phase1 §1-B |
| v12-S3 | compute_skill_overlap 제거 | ✅ | 04_phase3 §3-0 |
| v12-S4 | 전화번호 8종 정규식 | ✅ + ★ R1 버그 수정 | 02_phase1 §1-B |
| v12-S5 | INACTIVE 필드 제외 | ✅ | 02_phase1 §1-C |
| v12-C3 | operating_model 단순화 | ✅ ★ v4: evidence 길이 기반 | 04_phase3 §3-2 |
