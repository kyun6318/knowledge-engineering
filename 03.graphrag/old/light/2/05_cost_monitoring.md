# 비용 추정 + 최소 모니터링 (light.2)

> light.1 기반 + light.2 변경사항 반영
>
> **light.2 변경사항**:
> - [light.2-14] 총 예산에 **20% contingency** 추가
> - [light.2-6] Cloud Workflows 비용 제거
> - [light.2-8] Gold Test Set 라벨링 타임라인 분산 (비용 변동 없음)
> - Egress 비용 세부 계산 삭제 → **Anthropic 가격 변동 리스크** 분석으로 교체
> - Gold Label 인건비 **산출 근거 명시**
> - **환율 가정 명시** ($1 = 1,370원)

---

## 1. 비용 추정

### 1.1 Phase 0: API 검증 + PoC (2.5주)

light.1와 동일: **~$83**

### 1.2 Phase 1: MVP 파이프라인 (9주)

light.1와 동일: **~$42**

> Phase 1 기간이 light.1(6.5~7주) → light.2(9주)로 늘었지만, 추가 비용은 인프라 대기 시간이므로 LLM 비용 변동 없음.

### 1.3 Phase 2: 전체 처리 + 품질 평가 (5~6주)

#### Anthropic Batch API 비용 (light.1와 동일)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| Anthropic Batch API (CandidateContext) | 450K × $0.00300/건 [standard.21] | **$1,350** |
| Anthropic Batch API (CompanyContext) | 10K JD × $0.0004/건 | **$4** |
| Vertex AI Embedding | 302M 토큰 × $0.0001/1K | **$30** |
| Silver Label (Sonnet) | 1,000건 × $0.01 | **$10** |
| 프롬프트 최적화 LLM | ~250건 | **$300** |
| Dead-letter 재처리 LLM [light.2-10] | ~15,000건 × $0.00300 | **$45** |
| **Phase 2 LLM 합계** | | **~$1,739** |

> light.1($1,698) 대비 +$41: Dead-letter 재처리 비용 추가 [light.2-10]

#### Phase 2 인프라 비용 (1개월)

| 서비스 | 사용량 | 비용 |
|---|---|---|
| Cloud Run Jobs (전체) | ~300시간 | ~$90 |
| GCS | 150GB + Versioning | ~$5 |
| BigQuery | + batch_tracking | ~$5 |
| Neo4j AuraDB Professional | 1개월 | $100~200 |
| **Phase 2 인프라 합계** | | **~$200** |

> light.1와 동일. Cloud Workflows 비용($0)은 원래 미미했으므로 삭제 영향 없음.

### 1.4 Gold Label 인건비 — 산출 근거 명시 [light.2-14]

> light.1에서 $2,920으로 전체 예산의 59%를 차지하나 산출 근거 누락. light.2에서 명시.

```
라벨링 단가 계산:
  - 도메인 전문가 시급: $30/시간 (한국 HR 도메인 전문가 기준, 약 4만원)
  - 1건당 라벨링 시간: 20분 (scope_type, outcome, signal, stage 등 복합 평가)
  - 1건당 비용: $30 × 20/60 = $10/건

전문가 A (200건 중 100건):
  - 100건 × $10 = $1,000
  - + Cohen's κ 검증 참여 (4시간): $120
  - 소계: $1,120

전문가 B (200건 중 100건):
  - 100건 × $10 = $1,000
  - 소계: $1,000

Power analysis + 리포트 작성 (MLE):
  - 내부 인력이므로 별도 비용 없음 (인건비에 포함)

Phase 0 PoC 50건 검증 (전문가 A):
  - 50건 × $10 = $500 (Phase 0 비용에 미포함, 여기에 합산)
  - + 검증 미팅 (4시간): $120
  - 소계: $620

총 Gold Label 인건비: $1,120 + $1,000 + $620 = $2,740
→ 버퍼 포함: ~$2,920 (light.1와 동일)
```

### 1.5 시나리오별 총비용 (light.2)

| 시나리오 | Phase 0 | Phase 1 | Phase 2 LLM | Phase 2 인프라 | Gold Label | **소계** | **+20% Contingency** |
|---|---|---|---|---|---|---|---|
| **A: Haiku Batch (권장)** | $83 | $42 | $1,739 | ~$200 | $2,920 | **~$4,984** | **~$5,981** |
| A': Haiku→Sonnet Fallback | $83 | $42 | +LLM | ~$200 | $2,920 | **~$5,700** | **~$6,840** |
| B: Sonnet Batch | $83 | $42 | +LLM | ~$200 | $2,920 | **~$5,500** | **~$6,600** |
| D: Gemini Flash | $83 | $42 | 낮음 | ~$200 | $2,920 | **~$4,300** | **~$5,160** |

### 1.6 [light.2-14] 20% Contingency 근거

| 리스크 | 추가 비용 가능성 | 확률 |
|--------|---------------|------|
| 프롬프트 튜닝 추가 반복 (500~1,000건) | +$300~600 | 중 |
| Anthropic 가격 변경 (50% 할인 종료) | +$1,350 (LLM 비용 2배) | 낮 |
| Neo4j Professional 사양 업그레이드 | +$135 (1개월) | 중 |
| Phase 2 품질 미달 → 프롬프트 수정 → 재처리 | +$500~1,350 | 중 |
| Dead-letter 재처리 2차 | +$45 | 낮 |

> 20% contingency($997)는 위 리스크 중 1~2개 동시 발생 시 커버 가능한 수준.

### 1.7 Anthropic 가격 변동 리스크 분석 (Egress 비용 계산 대체)

> light.1에서 Egress 비용($3.6)을 상세 계산했으나, 전체 예산 대비 무의미.
> light.2에서는 **실질적 비용 리스크**인 Anthropic 가격 변동을 분석.

```
현재 가정:
  - Haiku Batch input: $0.40/1M tokens (50% 할인)
  - Haiku Batch output: $2.00/1M tokens (50% 할인)
  - 이력서 1건당: $0.00300

시나리오 A: 할인 유지 (현행)
  → 450K × $0.00300 = $1,350

시나리오 B: 할인 종료 (full price)
  → Haiku input: $0.80/1M, output: $4.00/1M
  → 이력서 1건당: ~$0.00600
  → 450K × $0.00600 = $2,700 (+$1,350)

시나리오 C: 모델 변경 (Haiku 4.5 → 5.0 등)
  → 가격 변동 예측 불가
  → Gemini Flash Batch로 대체 가능 (비용 유사 또는 저렴)

대응:
  □ Phase 0 시작 전 Anthropic에 Batch 할인 영구 여부 문의
  □ Gemini Flash Batch를 Phase 0에서 비교 검증 (이미 시나리오 D에 포함)
  □ 가격 변경 통보 시 즉시 Gemini Flash로 전환 가능하도록 프롬프트 호환성 확보
```

### 1.8 환율 가정 [light.2-14]

> **$1 = 1,370원** (2026년 3월 기준 가정)

| 시나리오 | USD | 원화 (환율 1,370) |
|----------|-----|-----------------|
| A (Haiku Batch, 소계) | $4,984 | ~683만원 |
| A (+20% contingency) | $5,981 | ~819만원 |
| D (Gemini Flash, 소계) | $4,300 | ~589만원 |
| D (+20% contingency) | $5,160 | ~707만원 |

### 1.9 Budget Alert 설정

light.1와 동일.

---

## 2. 최소 모니터링 (light.2)

light.1와 동일. Cloud Monitoring 알림 3개 + BigQuery 모니터링 쿼리.

> Cloud Workflows 관련 모니터링 항목 제거 [light.2-6].

---

## 3. 보안 설계

light.1와 동일.

---

## 4. 리전 선택

light.1와 동일. 단, Cloud Workflows 리전 행 제거 [light.2-6].

| 서비스 | 리전 | 근거 |
|---|---|---|
| GCS | `asia-northeast3` (서울) | 데이터 주권, 레이턴시 |
| BigQuery | `asia-northeast3` | GCS와 같은 리전 |
| Cloud Run Jobs | `asia-northeast3` | GCS 접근 레이턴시 |
| Vertex AI (Embedding) | `us-central1` | 모델 제공 리전 |
| Neo4j AuraDB | `asia-northeast1` (도쿄) | 서울 미지원 |
| Anthropic API | US (외부) | 선택 불가 |

---

## 5. Docker 이미지

light.1와 동일.

---

## 6. 백업 전략

light.1와 동일.

---

## 7. light.2 전체 비용 요약

```
Pre-Phase 0 (2~3주):  ~$0 (내부 작업)
Phase 0 (2.5주):      ~$83
Phase 1 (9주):        ~$42
Phase 2 LLM (1개월):  ~$1,739
Phase 2 인프라 (1개월): ~$200
Gold Label 인건비:     ~$2,920
────────────────────────────
소계:                 ~$4,984 (~683만원)
+20% Contingency:     ~$997
────────────────────────────
총 예산 (권장):       ~$5,981 (~819만원)

light.1 대비 변동:
  - Dead-letter 재처리 LLM: +$45 [light.2-10]
  - Contingency 20%: +$997 [light.2-14]
  - Egress 세부 계산: 삭제 (가격 변동 리스크 분석으로 교체)
  - Cloud Workflows: $0 변동 (원래 미미) [light.2-6]
```
