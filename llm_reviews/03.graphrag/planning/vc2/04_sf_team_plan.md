# S&F(Search & Filter) 아티팩트 처리팀 범위 + 산출물 정의 (v2)

> **v1 대비 변경**: ★ I1 PubSub 자동 트리거를 모든 산출물 전달에 반영
> **인력**: 별도 정의

---

## 1. S&F 팀 담당 범위 — v1 동일

6개 범주: 데이터 수집, 전처리, 파일 파싱, LLM 추출, 임베딩+벡터, 품질 메트릭
(상세 → `v1/c_03_sf_team_plan.md` §1 참조)

---

## 2. S&F → GraphRAG 산출물 명세 (★ v2: PubSub 트리거 추가)

### 산출물 ①: PoC 결과 (W1 D5, Go/No-Go용)

| 항목 | 형식 | 전달 |
|------|------|------|
| LLM 추출 PoC 20건 + scope_type 정확도 | JSON + 리포트 | **수동 전달** (Go/No-Go 회의) |
| 적응형 호출 비교 (1-pass vs N+1) | 리포트 | Slack/회의 |
| Embedding 분별력 + Batch API 실측 | 리포트 | Slack/회의 |
| PoC 비용 외삽 (v5 A2) | 리포트 | Slack/회의 |

### 산출물 ②: CandidateContext 1,000건 (W5)

| 항목 | 형식 | 전달 |
|------|------|------|
| CandidateContext JSON | JSONL | GCS `gs://kg-artifacts/candidate/batch_{id}.jsonl` |
| 전달 조건 | PII 마스킹 완료, chapters[] 시간순, v12 스키마 | — |
| 검증 | JSON Schema 검증 스크립트 동봉 | GCS 동일 경로 |
| ★ **v2 트리거** | GCS Object Finalize → **PubSub `kg-artifact-ready`** | GraphRAG Cloud Run Job 자동 적재 |

### 산출물 ③: CandidateContext 480K+ (W9~15, 순차)

| 항목 | 형식 | 전달 |
|------|------|------|
| DB 500K 처리분 | JSONL (chunk 10K건/파일) | GCS + ★ **PubSub 자동 통지** |
| 파일 100K 처리분 | JSONL (chunk 10K건/파일) | GCS + ★ **PubSub 자동 통지** |
| 주간 진행 리포트 | Markdown | Slack |
| 품질 메트릭 | BigQuery quality_metrics | 공유 BQ 데이터셋 |

### 산출물 ④: JD + CompanyContext (W17~18)

| 항목 | 형식 | 전달 |
|------|------|------|
| Vacancy JSON (JD 10K) | JSONL | GCS `gs://kg-artifacts/vacancy/` + ★ **PubSub** |
| CompanyContext JSON | JSONL | GCS `gs://kg-artifacts/company/` + ★ **PubSub** |
| NICE 기업정보 원본 | BigQuery | 공유 BQ 데이터셋 |
| job-hub API 스펙 확정 (v5 A1) | 문서 | Confluence/Notion |

### 산출물 ⑤: 기업 보강 데이터 (W24~25)

| 항목 | 형식 | 전달 |
|------|------|------|
| 크롤링 기업 데이터 | JSONL | GCS `gs://kg-artifacts/company_enrichment/` + ★ **PubSub** |

### ★ v2 PubSub 토픽 사양

```
Topic: kg-artifact-ready
Message attributes:
  artifact_type: "candidate" | "vacancy" | "company" | "company_enrichment"
  batch_id: "batch_20260501_001"
  file_count: 5
  record_count: 10000
  gcs_prefix: "gs://kg-artifacts/candidate/batch_20260501/"
```

---

## 3. S&F 팀 타임라인 — v1 동일

```
W1:     [환경+PoC] → 산출물 ① (수동)
W2-3:   [전처리 모듈: PII+CMEK+Career분리]
W4-5:   [LLM 추출 1,000건] → 산출물 ② (PubSub)
W7:     [코드 리팩토링 + Provider 추상화]
W8-9:   [파서 구축: PDF/DOCX/HWP + Hybrid 분리]
W10-15: [Batch 600K 처리] → 산출물 ③ (PubSub, 순차)
W16:    [버퍼 + 품질 리포트]
W17-18: [JD 파싱 + CompanyContext 추출] → 산출물 ④ (PubSub)
W19-22: [잔여 배치 소화 + 품질 관리]
W23:    [버퍼]
W24-25: [크롤링] → 산출물 ⑤ (PubSub)
W26-27: [품질 메트릭 최종 + 인수인계]
```

---

## 4. S&F 팀 비용 — v1 동일

| Phase | LLM | Embedding | 인프라 | **합계** |
|-------|-----|-----------|-------|--------|
| Phase 0 | $7 | $0.1 | $3 | **~$10** |
| Phase 1 | $24 | $1 | $12 | **~$37** |
| Phase 2 | $1,690 | $52 | $210~360 | **~$1,952~2,102** |
| Phase 3 | $55 | $0.2 | $25 | **~$80** |
| Phase 4 | $11 | $0.1 | $25 | **~$36** |
| **합계** | **$1,787** | **$53** | **$275~425** | **~$2,115~2,265** |
