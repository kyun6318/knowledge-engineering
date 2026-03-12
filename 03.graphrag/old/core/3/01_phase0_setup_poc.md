# Phase 0: 사전 준비 + 환경 구성 + PoC (Week 0~1)

> **목적**: 사전 준비를 병렬 진행하고, Week 1에서 GCP 환경 + LLM PoC + 크롤링 실현 가능성을 검증.
>
> **v2 대비 변경**:
> - N1: AuraDB Free Auto-Pause 대비 — Phase 0에서 인지, Phase 1에서 health check 설정
> - N4: Phase 0 산출물에 "일일 이력서 유입량 확인" 추가
> - N5: Gemini Flash 대안 테스트 시 provider 추상화 필요성 판단
> - v12 S2: PII 매핑 테이블 GCS CMEK 버킷 사전 생성
> - v12 S4: 전화번호 8종 정규식 PoC 검증
> - v12 M1: 적응형 호출 전략 PoC 포함 (20건 중 Career 4+ 건 포함)
>
> **인력**: DE 1명 + MLE 1명 풀타임
> **산출물**: GCP 환경 완성 + PoC 결과 + Go/No-Go 판정

---

## Week 0: 사전 준비 (27주 카운트에 미포함, 지금 즉시)

> v2와 동일. 아래 항목은 모두 **병렬 실행** 가능.

### Blocking #1: Anthropic Batch API Quota 확인

> v2와 동일.

### Blocking #1-B: Gemini Flash Batch 대안 검증

> v2와 동일.
> ★ v3 추가: 테스트 결과에 따라 Phase 2-0 provider 추상화 레이어(N5) 범위 결정.

### Blocking #2: 법무 PII 검토

> v2와 동일.

### Blocking #3: 크롤링 법적 검토

> v2와 동일.

### 기존 데이터 확보

> v2와 동일.

### 사전 준비 체크리스트

```
□ Anthropic Batch API quota 확인 완료
□ Gemini Flash Batch 대안 테스트 완료 → ★ provider 추상화 필요성 판단
□ 법무 PII 검토 요청 완료
□ 크롤링 법적 검토 요청 완료
□ 크롤링 대상 사이트 3곳 사전 조사 완료 (법무 허용 전제)
□ 크롤링 불허 시 대체 데이터 소스 목록 작성
□ 기존 DB 샘플 100건 확보
□ GCP 프로젝트 생성 (또는 기존 프로젝트 사용 확인)
□ ★ 샘플 100건 중 Career 4+ 이력서 비율 사전 확인 (v12 M1 적응형 호출 검증용)
```

---

## Week 1: Phase 0 — 환경 + PoC (1주)

### DE 담당 (Day 1~5)

#### Day 1-2: GCP 환경 구성

> v2와 동일 (서비스 계정 3개, API 활성화, GCS, BigQuery).

★ v3 추가: PII 매핑 전용 GCS 버킷 (v12 S2)

```bash
# ★ v3: PII 매핑 테이블 전용 버킷 (CMEK)
gcloud storage buckets create gs://kg-pii-mapping \
  --location=asia-northeast3 \
  --uniform-bucket-level-access

# Cloud KMS 키 생성
gcloud kms keyrings create kg-pii-keyring \
  --location=asia-northeast3
gcloud kms keys create kg-pii-key \
  --location=asia-northeast3 \
  --keyring=kg-pii-keyring \
  --purpose=encryption

# CMEK 적용
gcloud storage buckets update gs://kg-pii-mapping \
  --default-encryption-key=projects/graphrag-kg/locations/asia-northeast3/keyRings/kg-pii-keyring/cryptoKeys/kg-pii-key

# PII 읽기 전용 서비스 계정
gcloud iam service-accounts create kg-pii-reader \
  --display-name="KG PII Reader (Read-Only)"
gcloud storage buckets add-iam-policy-binding gs://kg-pii-mapping \
  --member="serviceAccount:kg-pii-reader@graphrag-kg.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# Cloud Audit Logs 자동 활성화 (GCS 기본)
```

#### Day 2: BigQuery 테이블 생성

> v2와 동일 (resume_raw, resume_processed, processing_log, batch_tracking, quality_metrics).

★ v3 추가: batch_tracking에 api_provider 컬럼

```sql
-- ★ v3: Batch tracking에 provider 추가 (N5 대비)
ALTER TABLE graphrag_kg.batch_tracking
ADD COLUMN api_provider STRING DEFAULT 'anthropic';
-- 값: 'anthropic', 'gemini'
```

#### Day 2-3: Neo4j + 인프라

> v2와 동일.

★ v3 추가: AuraDB Free Auto-Pause 인지 (N1)

```
□ Neo4j AuraDB Free 인스턴스 생성 (v2와 동일)

★ v3 인지 사항: AuraDB Free Auto-Pause
  - AuraDB Free는 72시간 비활성 시 자동 일시 중지
  - Phase 0에서는 매일 작업하므로 문제 없음
  - Phase 1 API 배포(Week 6) 시 Cloud Scheduler health check 설정 필수 (N1)
  - → 01_phase0 산출물이 아닌, Phase 1 완료 시점에서 설정

□ Graph 스키마 적용
  ★ v19 관계명 확인: PERFORMED_ROLE, OCCURRED_AT, HAS_CHAPTER 등
  (v2의 HAD_ROLE, AT_COMPANY는 사용하지 않음)

□ Vector Index 설정 (v2와 동일: 768d, cosine)
```

#### Day 3-5: 크롤링 대상 사이트 구조 분석 (법무 허용 시에만)

> v2와 동일.

---

### MLE 담당 (Day 1~5)

> v2와 동일 기반 + ★ v3 추가 항목.

#### Day 1-2: DB 프로파일링

> v2와 동일.

★ v3 추가: 일일 이력서 유입량 확인 (N4)

```sql
-- ★ v3 N4: 일일 유입량 확인 쿼리
SELECT
  DATE(created_at) AS dt,
  COUNT(*) AS daily_count
FROM resume_hub.career
WHERE created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY dt
ORDER BY dt DESC;

-- 결과 해석:
-- daily_count 평균 < 500 → 증분 주기: 주 1회 (비용 절감)
-- daily_count 평균 500~2,000 → 증분 주기: 일 1회 (기본값)
-- daily_count 평균 > 2,000 → Batch API 필요, 비용 재산정
```

★ v3 추가: Career 수 분포 확인 (v12 M1)

```sql
-- ★ v12 M1: Career 수 분포 확인 (적응형 호출 전략 검증)
SELECT
  CASE
    WHEN career_count <= 3 THEN '1-3 (1-pass)'
    ELSE '4+ (N+1 pass)'
  END AS strategy,
  COUNT(*) AS person_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM (
  SELECT person_id, COUNT(*) AS career_count
  FROM resume_hub.career
  GROUP BY person_id
)
GROUP BY strategy;

-- v12 가정: 80% 1-pass, 20% N+1 pass
-- 실제 비율에 따라 비용 추정 조정
```

#### Day 2-3: LLM 추출 PoC 20건

> v2와 동일 + ★ v12 프롬프트 적용.

```
★ v3 PoC 프롬프트 변경 (v12):
  - structural_tensions 제거 (S5)
  - work_style_signals 제거 (S5)
  - scope_type 분류 가이드라인 포함 (v12 §2.4)
  - outcomes 4+1 유형 포함 (v12 §2.5)
  - situational_signals 14개 라벨 포함 (v12 §2.6)

★ v3 PoC 구성 (v12 M1 적응형 호출 검증):
  - Career 1~3 이력서: 15건 (1-pass 프롬프트)
  - Career 4+ 이력서: 5건 (N+1 pass 프롬프트)
  - 품질 비교: 1-pass vs N+1 pass (Career 3개 건에서 동시 테스트)
```

#### Day 4-5: Embedding + Batch API

> v2와 동일.

---

### 공동: Go/No-Go 판정 (Day 5)

| 기준 | 통과 조건 | 미달 시 대응 |
|------|-----------|-------------|
| LLM 추출 품질 | 20건 scope_type 정확도 > 60% | 프롬프트 재설계 + 3일 추가 |
| ★ 적응형 호출 품질 | 1-pass ≈ N+1 pass (±10%) | Career 분기점 조정 (3→2 or 4) |
| DB 데이터 품질 | 텍스트 필드 비어있는 비율 < 20% | structured_fields 활용으로 전환 |
| Batch API quota | 계획 실행 최소 조건 확인 | 동시 3 batch + Gemini Flash 대비 |
| 크롤링 가능성 | ★ **법무 미결이어도 DB-only Go** | 크롤링은 법무 결론 후 추가 |
| Embedding 분별력 | similar > 0.7, dissimilar < 0.4 | text-embedding-005(768d) 기본값 |
| ★ **일일 유입량** | **확인 완료** (N4) | 가정값(1,000건/일) 유지 |
| ★ **Career 수 분포** | **1-pass/N+1 pass 비율 확인** (v12 M1) | v12 가정(80/20) 유지 |

---

## Phase 0 산출물

```
□ GCP 환경 구성 완료 (API, 서비스 계정 3+1개, GCS, BigQuery, Secret Manager)
  ★ kg-pii-reader 서비스 계정 추가 (v12 S2)
  ★ gs://kg-pii-mapping/ CMEK 버킷 생성 (v12 S2)
□ Neo4j AuraDB Free + 스키마 + Vector Index (768d)
  ★ v19 관계명 확인 (v12 M2)
□ Neo4j APOC Extended 지원 여부 확인 결과
□ Neo4j max concurrent connections 확인 결과 + tasks 수 결정
□ BigQuery 테이블 5개 + quality_metrics + ★ batch_tracking.api_provider
□ DB 데이터 프로파일 리포트 (100건)
  ★ 일일 유입량 확인 결과 (N4)
  ★ Career 수 분포 확인 결과 (v12 M1)
□ LLM 추출 PoC 결과 (20건) + 품질 측정
  ★ 적응형 호출 (1-pass vs N+1 pass) 비교 결과 (v12 M1)
  ★ v12 프롬프트 적용 (S5: INACTIVE 필드 제외)
□ Embedding 모델 확정 (text-embedding-005, 768d)
□ Batch API 응답 시간 실측 (3~5건)
□ Gemini Flash Batch 대안 테스트 결과
  ★ provider 추상화 필요성 판단 (N5)
□ 크롤링 대상 사이트 구조 분석 (법무 허용 시)
□ Go/No-Go 판정 문서

--- Phase 2 사전 조사 (우선순위 낮음) ---
□ 이력서 원본 파일 형식 분포 사전 조사
□ HWP 파싱 3방법 사전 조사
□ Document AI 프로세서 사전 생성

--- Phase 3 사전 준비 ---
□ NICE DB 접근 계약 상태 확인
```
