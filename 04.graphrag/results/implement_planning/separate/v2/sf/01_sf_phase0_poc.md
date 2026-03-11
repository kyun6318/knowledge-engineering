# S&F Phase 0: 환경 + PoC (Week 0~1)

> **v5 원본**: `01_phase0_setup_poc.md`
> **S&F 담당 범위**: GCP 환경, DB 프로파일링, LLM PoC, Embedding 검증, 크롤링 분석

---

## Week 0: 사전 준비 (27주 외, 즉시 — 병렬)

```
□ Anthropic Batch API quota/Tier 확인
□ Gemini Flash Batch 대안 사전 검증
□ 법무 PII 검토 요청 → 마스킹 적용으로 우선 진행
□ 크롤링 대상 사이트 법적 검토 요청
□ 크롤링 대상 사이트 DOM 구조 사전 조사
□ 기존 이력서 DB 샘플 100건 확보
□ Career 4+ 이력서 비율 사전 확인 (v12 M1)
```

---

## Week 1: Phase 0

### DE 담당 (Day 1~5)

#### Day 1-2: GCP 환경 구성
> 서비스 계정 4개, API 활성화, GCS, BigQuery
> ★ v4 R3: CMEK 버킷은 Phase 1-B로 이동 (Go 판정 후)

#### Day 2: BigQuery 테이블 생성
> resume_raw, resume_processed, processing_log, batch_tracking, quality_metrics
> batch_tracking에 `api_provider` 컬럼 추가 (N5 대비)

```sql
ALTER TABLE graphrag_kg.batch_tracking
ADD COLUMN api_provider STRING DEFAULT 'anthropic';
```

#### Day 3-5: 크롤링 대상 사이트 구조 분석 (법무 허용 시에만)

### MLE 담당 (Day 1~5)

#### Day 1-2: DB 프로파일링 + 일일 유입량 확인 (N4)

```sql
-- N4: 일일 유입량 확인
SELECT DATE(created_at) AS dt, COUNT(*) AS daily_count
FROM resume_hub.career
WHERE created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY dt ORDER BY dt DESC;

-- v12 M1: Career 수 분포 (적응형 호출 검증)
SELECT
  CASE WHEN career_count <= 3 THEN '1-3 (1-pass)' ELSE '4+ (N+1 pass)' END AS strategy,
  COUNT(*) AS person_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM (SELECT person_id, COUNT(*) AS career_count FROM resume_hub.career GROUP BY person_id)
GROUP BY strategy;
```

#### Day 2-3: LLM 추출 PoC 20건

```
PoC 구성 (v12 M1 적응형 호출 검증):
  - Career 1~3 이력서: 15건 (1-pass)
  - Career 4+ 이력서: 5건 (N+1 pass)
  - 품질 비교: 1-pass vs N+1 pass (Career 3개 건에서 동시 테스트)

v12 프롬프트 적용:
  - S5: structural_tensions, work_style_signals 제외
  - scope_type 분류 가이드라인 (v12 §2.4)
  - outcomes 4+1 유형 (v12 §2.5)
  - situational_signals 14개 라벨 (v12 §2.6)
```

#### Day 4-5: Embedding 모델 확정 + Batch API 실측

---

## Phase 0 산출물 (S&F 담당분)

### Must
```
□ GCP 환경 (API, 서비스 계정 4개, GCS, BigQuery)
□ BigQuery 테이블 5개 + quality_metrics + batch_tracking.api_provider
□ DB 프로파일 리포트 (100건) + 일일 유입량 (N4) + Career 분포 (M1)
□ LLM 추출 PoC 결과 (20건) + 적응형 호출 비교 (M1)
□ Embedding 모델 확정 (text-embedding-005, 768d)
□ Batch API 응답 시간 실측
□ Gemini Flash Batch 대안 테스트 → provider 추상화 판단 (N5)
```

### Should
```
□ 크롤링 대상 사이트 구조 분석 (법무 허용 시)
□ 이력서 파일 형식 분포 조사 (Phase 2 사전)
□ HWP 파싱 3방법 조사 (Phase 2 사전)
□ NICE DB 접근 계약 상태 확인 (Phase 3 사전)
```

> **→ 산출물 ①**: PoC 결과 20건 + 리포트 → **수동** Go/No-Go 회의에서 GraphRAG 팀에 전달
