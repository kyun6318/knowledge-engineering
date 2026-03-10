# Phase 2: 전체 데이터 처리 + 품질 평가 (5~6주)

> **목적**: 전체 데이터(450K 이력서 + 10K JD) 처리 + Graph 적재 + 품질 평가.
>
> **light.2 변경사항** (light.1 4~5주 → light.2 5~6주):
> - [light.2-6] Cloud Workflows 제거 → **Makefile + 모니터링 스크립트**로 운영 (후속 프로젝트로 이관)
> - [light.2-7] Batch API **3-시나리오** 타임라인 반영
> - [light.2-8] Gold Test Set 라벨링이 Phase 1에서 **선행 시작** → Phase 2에서 평가만 실행
> - [light.2-10] Dead-letter 재처리를 **별도 0.5주 태스크**로 격상
> - [light.2-13] 전문가 B 투입 시점 명시
>
> **인력**: DE 1명 + MLE 1명 풀타임, 도메인 전문가 2명 (A: 파트타임 계속, B: Week 15~16)
> **산출물**: 전체 KG + 품질 리포트(Gold Test Set 200건) + SQL/Cypher 쿼리 문서

---

## 병렬 트랙 구성 (Week 13~18/19)

```
Week 13     Week 14     Week 15     Week 16     Week 17     Week 18
──────────────────────────────────────────────────────────────────────
[2-0] Neo4j Professional 전환 (1일 - Week 13 시작)
  │
  ▼
[DE]  ── 2-A: Batch 처리 (450K, 3~4주) ────────── 2-C: Graph적재 ──
[MLE] ── 2-B: 품질평가 (0.5주) ── 2-C: Embedding + Mapping ──── 2-E: 서빙──
[DE]  ─────────────────────────── 2-D: Dead-letter (0.5주) [light.2-10] ──

전문가 A: Week 13~14 라벨링 완료
전문가 B: Week 15~16 라벨링 + κ 검증 [light.2-13]
```

---

## 2-0. Neo4j Professional 전환 (1일) — Week 13 시작 전

light.1와 동일. Neo4j AuraDB Free → Professional 전환 필수.

**light.1 리뷰 반영**: Neo4j Free → Professional 전환 시 **APOC import 동작 확인**도 추가:

```bash
# Phase 1 백업 데이터 import 시 확인 항목:
□ apoc.import.json 지원 여부 확인 (Professional에서)
□ 파일 접근 권한 확인 (apoc.import.json은 로컬 파일 경로 필요)
□ 대안: Cypher LOAD CSV 또는 neo4j-admin import 사용
□ 연결 테스트 (Cloud Run Job → Neo4j Professional)
```

> **light.2 권장**: 전환을 Phase 1 마지막 주(Week 12)에 **시작**하여 Phase 2 시작(Week 13) 전 여유 확보.
> 예상외 이슈(APOC 호환성 등) 발생 시 1~2일 버퍼가 있어야 한다.

---

## 2-A. 전체 데이터 Batch 처리 (3~4주) — Week 13~16/17

> DE 담당 (MLE 품질 평가와 병행).

| # | 작업 | GCP 서비스 | 비고 |
|---|---|---|---|
| 2-A-1 | 이력서 500K 중복 제거 실행 | Cloud Run Job | canonical ~450K |
| 2-A-2 | 450 chunks × Batch API 처리 | Anthropic Batch API | 동시 5~10 batch |
| 2-A-3 | JD 10K × Batch API 처리 | Anthropic Batch API | ~10 chunks |
| 2-A-5 | BigQuery chunk_status + batch_tracking 모니터링 | BigQuery | 일일 진행률 확인 |

### [light.2-7] Batch API 3-시나리오 타임라인

> Phase 0에서 실측한 응답 시간 기반. 아래는 기본 추정치.

| 시나리오 | 라운드당 시간 | 450 chunks / 10 동시 | 재시도+수집 | **Batch 기간** | Phase 2 전체 |
|----------|------------|---------------------|-----------|-------------|-------------|
| **낙관** | 6시간 | 45 × 6h = 11일 | 4일 | **~2.5주** | **~4주** |
| **기본 (권장)** | 12시간 | 45 × 12h = 22일 | 6일 | **~4주** | **~5.5주** |
| **비관** | 24시간 | 45 × 24h = 45일 | 8일 | **~7.5주** | **~9주** |

> **비관 시나리오 대응**:
> - 동시 batch 수 증가 요청 (10 → 20)
> - Gemini Flash Batch 병행 처리로 부하 분산
> - chunk 크기 증가 (1,000건 → 2,000건)으로 라운드 수 감소

### 비용 체크포인트

light.1와 동일.

---

## 2-B. 품질 평가 (0.5주, Gold Set 선행 완료) — Week 13~14 [light.2-8]

> **light.1에서 1주 → light.2에서 0.5주.** Gold Test Set 라벨링이 Phase 1에서 선행 시작되었으므로,
> Phase 2에서는 **이미 구축된 Gold Set으로 평가만 실행**.

### Gold Test Set 구축 타임라인 (light.1 → light.2 변경)

```
light.1: Phase 2 Week 10~11에 집중 (전문가 2인 × 100건 = 1주, 매우 빡빡)
                ↓
light.2: Phase 1 후반부터 분산 실행
  ├─ Phase 1 Week 11~14: 전문가 A 100건 라벨링 (20시간, 4주에 분산)
  ├─ Phase 2 Week 15~16: 전문가 B 100건 라벨링 (20시간)
  └─ Phase 2 Week 16: Cohen's κ 검증 → 200건 확정

효과: Phase 2-B 소요 시간 1주 → 0.5주 (라벨링이 아닌 평가만)
```

### Phase 2-B 작업 (0.5주)

| # | 작업 | 도구 | 비고 |
|---|---|---|---|
| 2-B-1 | (완료) Gold Test Set 100건 (전문가 A, Phase 1에서 완료) | - | [light.2-8] |
| 2-B-2 | Gold Test Set 추가 100건 (전문가 B, Week 15~16) | 수동 | [light.2-13] |
| 2-B-3 | Inter-annotator agreement (Cohen's κ) | Python | κ ≥ 0.7 |
| 2-B-4 | 평가 지표 측정 + BigQuery 적재 | BigQuery | quality_metrics |
| 2-B-5 | 품질 리포트 작성 | 문서 | 최종 산출물 |

### 평가 기준

light.1와 동일. (scope_type > 70%, outcome F1 > 55%, etc.)

### 품질 미달 시 대응

| 상황 | 대응 | 추가 시간 |
|------|------|----------|
| F1 지표 최소 기준 미달 (1~2개) | 프롬프트 튜닝 → 해당 1,000건 재추출 | +0.5주 |
| F1 지표 다수 미달 (3개+) | 접근법 재검토 (Phase 1 일부 재설계) | +1~2주 |
| 파싱 실패율 > 5% | 3-tier 로직 보강 | +0.5주 |
| 전체 기준 충족 | Phase 2-C 진행 | 없음 |

> **light.2 추가**: 품질 미달 시 "+0.5~2주"가 Phase 2 타임라인(5~6주)에 **포함되지 않음**.
> 품질 미달 발생 시 전체 일정은 **5.5~8주**로 연장될 수 있다.
> 이를 이해관계자에게 사전 고지하여 기대 관리를 한다.

---

## 2-C. Graph 전체 적재 + Embedding + Mapping (1~2주) — Week 16~18

light.1와 동일 구조.

| # | 작업 | 담당 | GCP 서비스 |
|---|---|---|---|
| 2-C-1 | CompanyContext 전체 Graph 적재 | DE | Cloud Run Job (tasks=8) |
| 2-C-2 | CandidateContext 전체 Graph 적재 | DE | Cloud Run Job (tasks=8) |
| 2-C-3 | Embedding 전체 생성 | MLE | Cloud Run Job (tasks=10) |
| 2-C-4 | MappingFeatures 전체 계산 | MLE | Cloud Run Job (tasks=20) |
| 2-C-5 | MAPPED_TO 관계 전체 적재 | DE | Cloud Run Job |
| 2-C-6 | BigQuery mapping_features 전체 적재 | DE | BigQuery |

### [light.2-11] Embedding 생성 시간 QPM 기반 재추정

```
총 Embedding 대상: 450K × 5.2 + 10K = ~2.35M 건

Vertex AI Embedding QPM (Phase 0에서 확인):
  - 기본 QPM: ___  (Phase 0 실측)
  - quota 증가 요청 후: ___

소요 시간 계산:
  - QPM 600 (기본): 2.35M / 600 / 60 = ~65시간 ≈ ~3일 (8시간/일)
  - QPM 1,200 (증가): 2.35M / 1,200 / 60 = ~33시간 ≈ ~1.5일
  - QPM 3,000 (대량): 2.35M / 3,000 / 60 = ~13시간 ≈ ~0.5일

→ QPM에 따라 Phase 2-C 기간이 크게 달라짐. Phase 0에서 반드시 확인.
```

---

## 2-D. Dead-letter 재처리 (0.5주) — Week 17~18 [light.2-10]

> **light.1에서 "1회 수동 재시도" → light.2에서 별도 0.5주 태스크로 격상.**
>
> 450K 건에서 실패율 3~5%면 13,500~22,500건이 dead-letter에 쌓인다.
> 이 규모의 재처리는 단순 수동 재시도로 해결되지 않으며,
> 실패 원인별 분류 → 수정 → 재처리 → 재검증 사이클이 필요하다.

### Dead-letter 분류 로직

```python
# src/dead_letter_classify.py

from google.cloud import storage
import json
from collections import Counter

def classify_dead_letters(bucket_name: str, prefix: str = "dead-letter/"):
    """실패 원인별 분류"""
    gcs = storage.Client()
    bucket = gcs.bucket(bucket_name)

    categories = Counter()
    details = []

    for blob in bucket.list_blobs(prefix=prefix):
        dl = json.loads(blob.download_as_text())
        error = dl.get("error", "")

        if "rate_limit" in error.lower() or "429" in error:
            category = "RATE_LIMIT"
        elif "timeout" in error.lower():
            category = "TIMEOUT"
        elif "safety" in error.lower() or "content_filter" in error.lower():
            category = "SAFETY_FILTER"
        elif "json" in error.lower() or "parse" in error.lower():
            category = "JSON_PARSE_FAIL"
        elif "token" in error.lower() and "limit" in error.lower():
            category = "TOKEN_LIMIT_EXCEEDED"
        else:
            category = "UNKNOWN"

        categories[category] += 1
        details.append({
            "file": blob.name,
            "category": category,
            "error_snippet": error[:200],
        })

    return categories, details

# 출력 예시:
# RATE_LIMIT: 3,200건 → 지수 백오프로 자동 재시도
# TIMEOUT: 1,500건 → chunk 크기 축소 후 재시도
# SAFETY_FILTER: 800건 → PII 마스킹 강화 후 재시도
# JSON_PARSE_FAIL: 2,100건 → json-repair 버전 업그레이드 + 프롬프트 수정
# TOKEN_LIMIT_EXCEEDED: 500건 → 입력 텍스트 truncate 후 재시도
# UNKNOWN: 400건 → 수동 검토
```

### Dead-letter 재처리 프로세스

```
Day 1: 분류 + 대응 전략 수립
  ├─ dead_letter_classify.py 실행
  ├─ 카테고리별 건수 확인
  └─ 자동 재시도 가능/불가능 분류

Day 2~3: 자동 재처리
  ├─ RATE_LIMIT: 지수 백오프 + 동시성 축소 → 재제출
  ├─ TIMEOUT: chunk 크기 1,000 → 500으로 축소 → 재제출
  ├─ TOKEN_LIMIT_EXCEEDED: 입력 텍스트 truncate → 재제출
  └─ JSON_PARSE_FAIL: 프롬프트에 "반드시 valid JSON으로" 강조 → 재제출

Day 4: 수동 검토 + SAFETY_FILTER 대응
  ├─ SAFETY_FILTER: PII 마스킹 강화 후 재시도
  ├─ UNKNOWN: 수동 에러 분석
  └─ 재처리 불가능 건 → 최종 dead-letter로 기록

Day 5: 재검증 + 리포트
  ├─ 재처리 결과 품질 검증
  ├─ 최종 실패율 계산 (목표: < 1%)
  └─ Dead-letter 처리 리포트 작성
```

---

## 2-E. 최소 서빙 인터페이스 (0.5주) — Week 18~19

light.1의 2-E와 동일. (BigQuery SQL 예시 5종 + Neo4j Cypher 예시 5종)

---

## Phase 2 완료 산출물 (Week 18~20)

```
□ Neo4j Professional 전환 완료 [standard.1-3]
□ 전체 데이터 처리 완료 (450K 이력서 + 10K JD)
□ Neo4j Graph 전체 적재
□ Vector Index 전체 적재
□ BigQuery mapping_features 전체 적재
□ MAPPED_TO 관계 전체 반영
□ 품질 평가 리포트 (Gold Test Set 200건)
□ Dead-letter 재처리 완료 + 최종 실패율 리포트 [light.2-10]
□ 처리 현황 리포트 (chunk_status + processing_log + batch_tracking)
□ 파싱 실패 리포트 (tier별 분포)
□ SQL + Cypher 예시 쿼리 문서
□ Makefile 기반 Phase 2 운영 완료 [light.2-6]
□ 비용 정산 리포트 (실제 vs 추정)
```

### light.2에서 Phase 2 산출물 변경

| 항목 | light.1 | light.2 | 변경 사유 |
|------|----|----|----------|
| Cloud Workflows 배포 | 포함 | **제거** | [light.2-6] 후속 프로젝트 |
| Dead-letter 리포트 | 간략 | **상세 (카테고리별)** | [light.2-10] |
| Gold Test Set 라벨링 | Phase 2 집중 | **Phase 1 선행** | [light.2-8] |

---

## 후속 프로젝트 연결점

light.1와 동일 + Cloud Workflows 추가:

| 후속 작업 | light.2 선행 조건 | 바로 시작 가능? |
|----------|-------------|--------------|
| **Cloud Workflows 오케스트레이션** [light.2-6] | E2E 파이프라인 동작 확인 | Yes (Makefile → Workflows 전환) |
| 크롤링 파이프라인 | CompanyContext 스키마 확정 | Yes |
| 증분 처리 자동화 | Cloud Workflows + E2E 확인 | Cloud Workflows 완료 후 |
| Looker Studio | BigQuery 테이블 확정 | Yes |
| 지식증류 | 품질 평가 결과 + 학습 데이터 | Yes |
| 서빙 API | mapping_features 스키마 확정 | Yes |
