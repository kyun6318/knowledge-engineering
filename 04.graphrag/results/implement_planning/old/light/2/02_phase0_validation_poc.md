# Pre-Phase 0 + Phase 0: 사전 준비 + API 검증 + PoC

> **목적**: Pre-Phase 0를 전체 타임라인에 명시적으로 포함하고,
> Phase 0에서 Embedding QPM 확인과 데이터 전송 테스트를 추가.
>
> **light.2 변경사항**:
> - [light.2-1] Pre-Phase 0(2~3주)를 명시적 타임라인에 포함
> - [light.2-11] Vertex AI Embedding QPM/TPM 한도 확인 추가
> - [light.2-12] Document AI 검증을 선택적(nice-to-have)으로 격하
> - [light.2-15] 데이터 전송 테스트(10GB 샘플) 추가
>
> **인력**: DE 1명 + MLE 1명 풀타임, 도메인 전문가 1명 파트타임

---

## Pre-Phase 0: 사전 준비 (2~3주) — Phase 0 시작 전 [light.2-1]

> **light.1에서 누락**: Pre-Phase 0가 타임라인에 포함되지 않아 전체 일정이 과소 추정됨.
> light.2에서 명시적으로 전체 타임라인(18.5~20.5주)에 포함한다.

### 전체 Pre-Phase 0 타임라인

```
Week -3 ~ Week -1 (Phase 0 시작 기준 역산)
─────────────────────────────────────────────
[법무 PII 검토 요청] ─────────────── (1~3주)
[Batch API quota 확인] ──────────── (1~2주)   ← 모두 병렬
[데이터 전송 테스트] ──── (1일) [light.2-15]
[도메인 전문가 확보 확인] ── (1주)
[GCP 프로젝트 사전 준비] ── (0.5일)
```

### Blocking #1: [standard.1-8] 법무팀 PII 처리 방침 검토 요청

light.1와 동일. 법무 지연 시 contingency 포함.

### Blocking #2: [standard.1-4] Anthropic Batch API Quota 사전 확인

light.1와 동일. Tier 업그레이드 소요 시간(1~2주) 감안.

### [light.2-15] 데이터 전송 테스트 (10GB 샘플)

```bash
# Pre-Phase 0: 10GB 샘플로 전송 속도 실측
# 실측 결과로 150GB 전체 전송 소요 시간 추정

□ 10GB 이력서 샘플 선별
□ gsutil -m rsync로 GCS 업로드 테스트
□ 전송 속도 측정 (Mbps)
□ 150GB 전체 전송 소요 시간 추정
  - 100Mbps: ~3.3시간
  - 50Mbps: ~6.7시간
  - 사내 방화벽/프록시 경유: 수 일 가능
□ 전송 방법 결정:
  ├─ gsutil -m rsync (기본)
  ├─ gcloud storage rsync --parallel (고속)
  └─ Transfer Appliance (대역폭 극히 제한 시)
□ 결과를 Phase 0 타임라인에 반영
```

> **왜 Pre-Phase 0에서?**: 150GB 업로드가 완료되지 않으면 Phase 0-B 프로파일링이 불가능.
> 사전에 속도를 실측해야 Phase 0 시작 시점을 결정할 수 있다.

### [light.2-13] 도메인 전문가 확보 확인

```
□ 전문가 A 확보 확인 (Phase 0~Phase 2 전반 참여)
  - Phase 0 Week 2~3: 8시간
  - Phase 1 Week 11~14: 40시간 (Gold Test Set 100건 라벨링)
  - Phase 2 Week 16: 4시간 (Cohen's κ 검증)

□ 전문가 B 확보 계획 수립 (Phase 2 참여)
  - Phase 2 Week 15~16: 20시간 (Gold Test Set 추가 100건 라벨링)
  - Week 10까지 확보 완료 필요 (Phase 2 blocking dependency)
```

### GCP 프로젝트 사전 준비

light.1와 동일. (gcloud 프로젝트 생성, API 활성화, 서비스 계정, GCS 버킷 등)

### 사전 준비 체크리스트

```
□ 법무팀 PII 검토 요청 완료 [standard.1-8]
□ Anthropic Batch API quota 확인 완료 [standard.1-4]
□ 데이터 전송 테스트 (10GB) 완료 + 150GB 소요 시간 추정 [light.2-15]
□ 도메인 전문가 A 확보 확인 [light.2-13]
□ 도메인 전문가 B 확보 계획 수립 (Week 10까지 확보) [light.2-13]
□ GCP 프로젝트 API 활성화 완료
□ 서비스 계정 + ADC 설정
□ GCS Object Versioning 활성화 확인 [standard.20]
□ Document AI 프로세서 사전 생성 (선택적) [light.2-12]
□ DS-NER-EVAL gold 데이터 라벨링 완료
```

---

## Phase 0: 기반 구축 + API 검증 + PoC (2.5주)

### 병렬 트랙 구성 (Week 1 ~ Week 2.5)

light.1와 동일 구조. 변경사항만 아래 기술.

---

## 0-A. GCP 환경 + API 검증 (3일) — Week 1 Day 1-3

### DE 담당: 환경 구성 + 데이터 업로드

light.1와 동일. 단, 0-A-3은 Pre-Phase 0 전송 테스트 결과를 반영:

```
0-A-3: 이력서 원본 GCS 업로드 시작 (백그라운드)
  - Pre-Phase 0에서 실측한 전송 속도 기반
  - 예상 소요 시간: ___시간 (Pre-Phase 실측값)
  - 완료 기한: Phase 0-B 시작 전 (Week 1.5)
```

### MLE 담당: API 검증 (3일)

#### Day 1: Gemini API + Embeddings + QPM 확인 [light.2-11]

light.1의 Day 1과 동일 + 아래 추가:

```python
# [light.2-11] Vertex AI Embedding QPM/TPM 확인
# Phase 2에서 2.34M 건 Embedding 요청이 필요하므로 rate limit 사전 확인

# 1. Quota 페이지 확인
# https://console.cloud.google.com/iam-admin/quotas
# → "aiplatform.googleapis.com/online_prediction_requests_per_minute" 검색

# 2. 현재 QPM 확인
import subprocess
result = subprocess.run([
    "gcloud", "services", "list", "--enabled",
    "--filter=aiplatform.googleapis.com",
    "--format=json"
], capture_output=True, text=True)

# 3. Phase 2 필요 QPM 계산
total_embeddings = 450_000 * 5.2 + 10_000  # ~2.34M
target_days = 3  # Phase 2-C에서 Embedding에 할당할 일수
required_qpm = total_embeddings / (target_days * 24 * 60)
print(f"필요 QPM: {required_qpm:.0f}")  # ~542 QPM

# → QPM 부족 시 quota 증가 요청 (1~2주 소요, Pre-Phase에서 요청)
```

#### Day 2: Document AI + Gemini 멀티모달 [light.2-12 축소]

> **light.2 변경**: Document AI는 HWP를 직접 지원하지 않으므로 **선택적(nice-to-have)**으로 격하.
> 이력서가 주로 PDF/DOCX/HWP인 점을 감안하면, Gemini 멀티모달과 HWP PoC에 더 집중.

| 테스트 | 내용 | Pass 기준 | 우선순위 |
|--------|------|----------|---------|
| TEST-DOC | Document AI OCR + Layout Parser (10건) | CER ≤ 0.10 | **선택적** [light.2-12] |
| TEST-MMD | Gemini 멀티모달 PDF 추출 (20건) | CER ≤ 0.10 | 필수 |
| TEST-E2E | 방법 A(DocAI) vs 방법 B(Gemini 멀티모달) | 품질/비용/속도 | 필수 |

> Document AI 검증 축소로 **0.5일 절약** → HWP PoC(0-C-7)에 시간 재배분.

#### Day 3: NER + 에러 핸들링

light.1와 동일.

---

## 0-B. 데이터 탐색 + 프로파일링 (1주) — Week 1-2

light.1와 동일. 추가사항:

### [light.2-2] 회사명 변형 패턴 Top-50 추출 (0-B 프로파일링 필수 항목)

```python
# Phase 0-B 프로파일링에서 반드시 추출
# → Phase 1-C의 Org ER 알고리즘 설계 입력 데이터

# 1,000건 샘플에서 회사명 추출 후 변형 패턴 분석
company_names_raw = extract_company_names(sample_1000)

# 변형 패턴 분류:
# - 괄호 변형: "삼성전자(주)" / "삼성전자 주식회사"
# - 영어/한국어: "Samsung Electronics" / "삼성전자"
# - 약칭: "현대차" / "현대자동차"
# - 부문/부서: "삼성전자 DS부문" / "삼성전자 반도체"
# - 합병/분할: "SK하이닉스" / "하이닉스반도체"

# Top-50 변형 패턴 리스트 산출
# → 1-C-3 Org ER 알고리즘의 company_alias.json 초안으로 활용
```

---

## 0-C. LLM 추출 품질 PoC (1.5주) — Week 1.5~2.5

light.1와 동일. 추가사항:

### [light.2-7] Batch API 응답 시간 실측

```python
# Phase 0-C에서 Batch API 5~10건 실측
# → Phase 2 타임라인 3-시나리오 확정에 사용

import time
from datetime import datetime

batch_timing = []
for i in range(5):
    batch = anthropic_client.messages.batches.create(requests=sample_requests_10)
    submit_time = datetime.utcnow()

    while True:
        status = anthropic_client.messages.batches.retrieve(batch.id)
        if status.processing_status == "ended":
            end_time = datetime.utcnow()
            elapsed = (end_time - submit_time).total_seconds() / 3600
            batch_timing.append(elapsed)
            break
        time.sleep(300)

print(f"Batch API 응답 시간: {batch_timing}")
print(f"평균: {sum(batch_timing)/len(batch_timing):.1f}h")
print(f"최소: {min(batch_timing):.1f}h, 최대: {max(batch_timing):.1f}h")

# → Phase 2 타임라인 확정:
#   낙관(p25): __h, 기본(median): __h, 비관(p75): __h
```

---

## 0-D. 인프라 셋업 (1주, 0-A/0-B와 병행) — Week 1-2

light.1와 동일.

---

## Phase 0 의사결정 — Week 2.5

light.1와 동일. Go/No-Go 게이트 6개 기준 유지.

### [light.2-7] 추가 의사결정: Batch API 시나리오 확정

| 시나리오 | 라운드당 시간 (실측) | Phase 2 Batch 기간 | Phase 2 전체 기간 |
|----------|-------------------|--------------------|-----------------|
| 낙관 | __h (p25 실측) | __주 | __주 |
| 기본 | __h (median 실측) | __주 | __주 |
| 비관 | __h (p75 실측) | __주 | __주 |

---

## Phase 0 산출물 체크리스트

light.1와 동일 + 아래 추가:

```
□ Vertex AI Embedding QPM/TPM 한도 확인 결과 [light.2-11]
  └─ 필요 시 quota 증가 요청 제출
□ Batch API 응답 시간 실측 결과 (5~10건) [light.2-7]
  └─ 3-시나리오 타임라인 확정
□ 회사명 변형 패턴 Top-50 리스트 [light.2-2]
  └─ 1-C-3 Org ER 입력 데이터
□ 데이터 전송 속도 실측 + 150GB 완료 여부 [light.2-15]
```
