# 비용 추정 + 모니터링 + 운영

> 전체 라이프사이클 비용 통합 추정 + 모니터링 구성 + 보안 설계
>
> **v2 대비 변경**:
> - LLM 비용: v12 적응형 호출(M1) + 600K 볼륨 반영 → Phase 2 LLM +$158
> - Gold Label: N6 2단계 접근 → $2,920~$5,840 (v2: $5,840 고정)
> - PII 보안: v12 S2 GCS CMEK 버킷 + kg-pii-reader 서비스 계정
> - 모니터링: v12 품질 메트릭 통합

---

## 1. 비용 추정

### 1.1 Phase 0: 환경 + PoC (1주)

| 서비스 | 비용 |
|---|---|
| Anthropic API (PoC 20건 + Sonnet 비교 + ★ 적응형 호출 검증) | ~$6 |
| Gemini Flash 대안 테스트 (10건) | ~$1 |
| Vertex AI Embedding (20쌍) | ~$0.001 |
| Batch API 실측 (3~5건) | ~$1 |
| GCS + BigQuery (초기 설정) | ~$1 |
| **Phase 0 합계** | **~$9** |

### 1.2 Phase 1: Core Candidate MVP (5주)

| 서비스 | 비용 |
|---|---|
| Cloud Run Jobs (크롤링, 법무 허용 시) | ~$3.6 |
| Cloud Run Jobs (전처리) | ~$2 |
| Cloud Run Service (GraphRAG API) | ~$5 |
| Anthropic Batch API (1,000건, ★ 적응형 호출) | ~$3.5 |
| Anthropic API (프롬프트 튜닝 ~200건) | ~$20 |
| Vertex AI Embedding (1,000건) | ~$0.5 |
| Neo4j AuraDB Free | $0 |
| ★ Cloud Scheduler (health check) | $0 |
| GCS + BigQuery | ~$1 |
| **Phase 1 합계** | **~$36** |

### 1.3 Phase 2: 파일 이력서 + 전체 처리 (8주)

#### LLM 비용

| 서비스 | v3 비용 | v2 대비 |
|---|---|---|
| Anthropic Batch API (600K, ★ 적응형 호출) | $1,488 | +$138 |
| Anthropic API (재처리/에러 ~6,000건) | ~$30 | +$5 |
| Anthropic API (Parser 프롬프트 ~300건) | ~$2 | 동일 |
| ★ 파일 섹션 분리 LLM 폴백 (30K건, v12 S1) | ~$60 | **신규** |
| Vertex AI Embedding (2.6M건) | ~$52 | +$5 |
| Embedding Egress (서울→US) | ~$4 | +$0.4 |
| Dead-letter 재처리 (~18,000건) | ~$54 | +$9 |
| **Phase 2 LLM 합계** | **~$1,690** | +$217 |

> ★ v12 M1 적응형 호출 비용 상세:
> - 1-pass (80%): 480K × $0.00158 = $758 (Batch: $379)
> - N+1 pass (20%): 120K × 4.5회 × $0.0008 = $432 (Batch: $216)
> - Batch 합계: **$595** (v2 $450 대비 +$145)
> - 적응형 호출의 비용 증가(+32%)는 Career 4+ 이력서의 추출 정확도 향상이 목적

#### 인프라 비용 (8주)

| 서비스 | 월 비용 | 8주 비용 |
|---|---|---|
| Cloud Run Jobs | ~$32/월 | ~$75 |
| GCS | $6/월 | ~$14 |
| BigQuery | $5/월 | ~$12 |
| Neo4j AuraDB Professional | $65~200/월 | ~$200~480 |
| Cloud Monitoring + Logging | ~$7/월 | ~$18 |
| **Phase 2 인프라 합계** | | **~$319~599** |

#### Phase 2 소계

| 항목 | 비용 |
|---|---|
| LLM | ~$1,690 |
| 인프라 | ~$319~599 |
| **Phase 2 합계** | **~$2,009~2,289** |

### 1.4 Phase 3: 기업 정보 + 매칭 (7주)

#### LLM 비용

| 서비스 | 비용 |
|---|---|
| Anthropic Batch API (CompanyContext 10K JD) | $4 |
| Anthropic Batch API (Vacancy 추출 10K) | $30 |
| Anthropic API (프롬프트 튜닝 + 검증) | ~$15 |
| Anthropic API (Organization ER LLM 2차) | ~$5 |
| ★ MAPPED_TO 소규모 테스트 (N3) | ~$1 |
| Vertex AI Embedding (vacancy + company) | ~$0.2 |
| **Phase 3 LLM 합계** | **~$55** |

#### 인프라 비용 (7주)

| 서비스 | 월 비용 | 7주 비용 |
|---|---|---|
| Neo4j Professional | $150~300/월 | ~$260~525 |
| Cloud Run + GCS + BigQuery | ~$15/월 | ~$26 |
| **Phase 3 인프라 합계** | | **~$286~551** |

#### Phase 3 소계

| 항목 | 비용 |
|---|---|
| LLM | ~$55 |
| 인프라 | ~$286~551 |
| **Phase 3 합계** | **~$341~606** |

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

#### ★ Gold Label 인건비 (N6: 2단계)

| 시나리오 | 비용 |
|---|---|
| ★ Phase 1만 (100건, 기준 충족 시) | ~$2,920 |
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

| Phase | LLM | 인프라 | Gold Label | **합계** |
|---|---|---|---|---|
| Phase 0 (1주) | $7 | $2 | — | **$9** |
| Phase 1 (5주) | $24 | $12 | — | **$36** |
| Phase 2 (8주) | $1,690 | $319~599 | — | **$2,009~2,289** |
| Phase 3 (7주) | $55 | $286~551 | — | **$341~606** |
| Phase 4 (4주) | $31 | $177~327 | $2,920~5,840 | **$3,128~6,198** |
| **총합계** | **$1,807** | **$796~1,491** | **$2,920~5,840** | **$5,523~9,138** |
| **원화** | | | | **~757~1,252만** |

> v2($8,215~8,890) 대비:
> - LLM: +$218 (v12 적응형 호출 + 600K + 파일 섹션 분리)
> - 인프라: +$10~30 (GCS CMEK, BQ 확장 등)
> - Gold Label 최소: -$2,920 (N6 2단계)
> - 하한: **$5,523** (Gold 100건) — v2 대비 -$2,692
> - 상한: **$9,138** (Gold 200건) — v2 대비 +$248
> - standard($8,825~9,225) 대비: $87~3,702 절감

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

> v2와 동일 (BigQuery 쿼리 3종 + Slack 수동).

★ v3 추가: v12 품질 메트릭 모니터링

```sql
-- ★ v12 품질 메트릭 쿼리 추가
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

> v2와 동일.

### Phase 4: 전체 모니터링 + Runbook

> v2와 동일 (05_phase4 참조).

---

## 3. 보안 — 서비스 계정 분리

### 서비스 계정 4개 (★ v3: +1)

| 계정 | 용도 | 권한 |
|------|------|------|
| `kg-crawling` | 크롤링 Job | storage.objectCreator, bigquery.dataEditor |
| `kg-processing` | 전처리 + LLM 추출 | storage.objectViewer/Creator, bigquery.dataEditor, aiplatform.user |
| `kg-loading` | Graph 적재 + API | storage.objectViewer, bigquery.dataViewer, **Neo4j 접근** |
| ★ `kg-pii-reader` | **PII 매핑 테이블 읽기 전용** | storage.objectViewer (**kg-pii-mapping 버킷만**) |

### PII 보안 강화 (★ v12 S2)

```
PII 매핑 테이블:
  저장소: gs://kg-pii-mapping/ (별도 버킷)
  암호화: CMEK (Cloud KMS)
  접근: kg-pii-reader만 읽기 가능
  로그: Cloud Audit Logs 자동 기록
  삭제: 개인정보 삭제 요청 시 해당 JSONL 라인 제거 + GCS 버전 삭제

API 보안:
  PII 필드(name, email, phone): API 응답에서 자동 제거 (N2)
  PII 필요 시: 별도 엔드포인트 (인증 강화, Phase 5 검토)
  접근 로그: /candidates/{id} 요청 BigQuery 기록
```

### VPC 네트워크 (v2 유지)

> Phase 4에서 구성 (Neo4j Allowlist).

---

## 4. 리전 선택 (v2 유지)

| 서비스 | 리전 | 근거 |
|---|---|---|
| GCP 프로젝트 | asia-northeast3 (서울) | 데이터 주권, 레이턴시 |
| Vertex AI | us-central1 | Gemini/Embedding API 가용성 |
| Neo4j AuraDB | asia-northeast1 (도쿄) | 서울 미지원, 최소 레이턴시 |

---

## 5. v2 리뷰 반영 추적

| # | v2 리뷰 권장 | v3 반영 | 문서 위치 |
|---|-------------|--------|----------|
| N1 | AuraDB Auto-Pause health check | ✅ Phase 1 설정 | 02_phase1 §1-D |
| N2 | API PII 필드 정의 | ✅ Phase 1 설계 | 02_phase1 §1-D, 00_overview §13 |
| N3 | MAPPED_TO 규모 추정 | ✅ Phase 3-0 설계 | 04_phase3 §3-0 |
| N4 | 일일 유입량 확인 | ✅ Phase 0 산출물 | 01_phase0 MLE 담당 |
| N5 | Provider 추상화 레이어 | ✅ Phase 2-0 구현 | 03_phase2 §2-0 |
| N6 | Gold Label 2단계 | ✅ Phase 4-3 | 05_phase4 §4-3 |
| N7 | 가중치 튜닝 1일 | ✅ Phase 3-4 | 04_phase3 §3-4 |
| N8 | Neo4j 사이징 검증 | ✅ Phase 2-2 | 03_phase2 §2-2 |
| N9 | 잔여 배치 주간 리포트 | ✅ Phase 3 진행 중 | 04_phase3 §3-4 |

### v12 Extraction Logic 반영 추적

| 변경 ID | 내용 | v3 반영 | 문서 위치 |
|---------|------|--------|----------|
| v12-M1 | 적응형 LLM 호출 | ✅ Phase 1-C, 2-3 | 02_phase1 §1-C |
| v12-M2 | v19 canonical 관계명 | ✅ 전 Phase | 00_overview §10~11 |
| v12-M3 | 구현 순서 (B→B'→A) | ✅ 타임라인 | 00_overview §4 |
| v12-S1 | Hybrid 섹션 분리 | ✅ Phase 2-1 | 03_phase2 §2-1 |
| v12-S2 | PII GCS CMEK | ✅ Phase 0, 1-B | 01_phase0, 02_phase1 |
| v12-S3 | compute_skill_overlap 제거 | ✅ Phase 3-0 확인 | 04_phase3 §3-0 |
| v12-S4 | 전화번호 8종 정규식 | ✅ Phase 1-B | 02_phase1 §1-B |
| v12-S5 | INACTIVE 필드 제외 | ✅ Phase 1-C | 02_phase1 §1-C |
| v12-C3 | operating_model 단순화 | ✅ Phase 3-2 | 04_phase3 §3-2 |
