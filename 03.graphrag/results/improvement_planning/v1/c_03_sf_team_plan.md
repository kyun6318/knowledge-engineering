# S&F(Search & Filter) 아티팩트 처리팀 범위 + 산출물 정의

> **역할**: 비정형 데이터(이력서, JD, 기업 정보)를 정형 아티팩트(JSON)로 변환하고,
> GraphRAG 팀에 Data Contract에 맞는 산출물을 제공한다.
> **인력**: 별도 정의 (GraphRAG 팀과는 독립적으로 운영)

---

## 1. S&F 팀 담당 범위

### 1.1. 데이터 수집 파이프라인

| 항목 | v5 원본 위치 | 상세 |
|------|------------|------|
| DB 텍스트 이력서 export | Phase 0 MLE, Phase 1 1-B | resume-hub DB → BigQuery resume_raw |
| 크롤링 파이프라인 | Phase 1 1-A | Playwright 기반, 법무 허용 시에만 |
| 홈페이지/뉴스 크롤링 | Phase 4 4-1 | 기업 인텔리전스 수집 |

### 1.2. 전처리 모듈

| 항목 | v5 원본 위치 | 상세 |
|------|------------|------|
| PII 마스킹 | Phase 1 1-B | re.sub 콜백(R1), 전화번호 8종(v12 S4), 주민번호, 이메일 |
| PII 매핑 저장 | Phase 1 1-B | GCS CMEK 버킷(R3), kg-pii-reader 전용 |
| CMEK 인프라 | Phase 1 1-B | Cloud KMS 키링, 버킷, 서비스계정 |
| Career 블록 분리 | Phase 1 1-B | 정규화 → 마스킹 → 검증 → 분리 |

### 1.3. 파일 파싱

| 항목 | v5 원본 위치 | 상세 |
|------|------------|------|
| PDF/DOCX 파서 | Phase 2 2-1 | 파일→텍스트 변환 |
| HWP 파서 | Phase 2 2-1 | 3가지 방법 사전 조사 후 선택 |
| Hybrid 섹션 분리 | Phase 2 2-1 | 패턴(70%) → LLM 폴백(30%, Batch API R4) |
| 파일 소스 confidence | Phase 2 2-1 | v12 §4.1.2 패널티 적용 |

### 1.4. LLM 추출

| 항목 | v5 원본 위치 | 상세 |
|------|------------|------|
| CandidateContext 추출 | Phase 1 1-C | 적응형 호출: 1-pass(Career≤3) / N+1(Career≥4) |
| CompanyContext 추출 | Phase 3 3-2 | DB 직접 + NICE Rule + LLM 3단계 |
| LLM Provider 추상화 | Phase 2 2-0 | Anthropic + Gemini 인터페이스 (N5) |
| Batch API 운영 | Phase 2 2-3 | 600K 처리, DB 500K 우선(R6), 비관 시나리오 대응 |

### 1.5. 임베딩 + 벡터

| 항목 | v5 원본 위치 | 상세 |
|------|------------|------|
| Embedding 생성 | Phase 1 G-5 | Vertex AI text-embedding-005, 768d |
| 벡터 검색 인프라 | Phase 1 G-6 | 분리 시 Vector DB(Milvus 등) 또는 Neo4j 내 유지 |

### 1.6. 품질 메트릭

| 항목 | v5 원본 위치 | 상세 |
|------|------------|------|
| schema 준수율 | Phase 2 2-4 | 목표 ≥95% |
| 필수 필드 완성도 | Phase 2 2-4 | 목표 ≥90% |
| PII 누출율 | Phase 2 2-4 | 목표 ≤0.01% |
| 적응형 호출 비율 | Phase 2 2-4 | v12 M1 (80/20 가정 검증) |
| 통계적 샘플링 | Phase 2 2-4 | 384건 |

---

## 2. S&F → GraphRAG 산출물 명세

### 산출물 ①: PoC 결과 (W1, Go/No-Go용)

| 항목 | 형식 | 전달 시점 |
|------|------|---------|
| LLM 추출 PoC 20건 결과 | JSON | W1 D5 |
| scope_type 정확도 측정 | 리포트 | W1 D5 |
| 적응형 호출 비교 (1-pass vs N+1) | 리포트 | W1 D5 |
| Embedding 분별력 테스트 결과 | 리포트 | W1 D5 |
| PoC 비용 외삽 (v5 A2) | 리포트 | W1 D5 |

### 산출물 ②: CandidateContext 1,000건 (W5)

| 항목 | 형식 | 전달 경로 |
|------|------|---------|
| CandidateContext JSON | JSONL (1파일/배치) | GCS `gs://kg-artifacts/candidate/batch_{id}.jsonl` |
| 전달 조건 | PII 마스킹 완료, chapters[] 시간순 정렬, v12 스키마 준수 | — |
| 검증 | schema 검증 스크립트 동봉 | GCS 동일 경로 |

### 산출물 ③: CandidateContext 480K+ (W9~15, 순차 전달)

| 항목 | 형식 | 전달 방식 |
|------|------|---------|
| DB 500K 처리분 | JSONL (chunk 10K건/파일) | GCS + PubSub 이벤트 통지 |
| 파일 100K 처리분 | JSONL (chunk 10K건/파일) | GCS + PubSub 이벤트 통지 |
| 주간 진행 리포트 | Markdown | Slack 공유 |
| 품질 메트릭 | BigQuery quality_metrics 테이블 | 공유 BQ 데이터셋 |

### 산출물 ④: JD + CompanyContext (W17~18)

| 항목 | 형식 | 전달 경로 |
|------|------|---------|
| Vacancy JSON (JD 10K) | JSONL | GCS `gs://kg-artifacts/vacancy/` |
| CompanyContext JSON | JSONL | GCS `gs://kg-artifacts/company/` |
| NICE 기업정보 원본 | BigQuery 테이블 | 공유 BQ 데이터셋 |
| job-hub API 스펙 확정 결과 (v5 A1) | 문서 | Confluence/Notion |

### 산출물 ⑤: 기업 보강 데이터 (W24~25)

| 항목 | 형식 | 전달 경로 |
|------|------|---------|
| 크롤링 기업 데이터 (product, funding, growth) | JSONL | GCS `gs://kg-artifacts/company_enrichment/` |

---

## 3. S&F 팀 타임라인

```
W1:     [환경+PoC] → 산출물 ① 전달
W2-3:   [전처리 모듈: PII+CMEK+Career분리]
W4-5:   [LLM 추출 1,000건] → 산출물 ② 전달
W7:     [코드 리팩토링 + Provider 추상화]
W8-9:   [파서 구축: PDF/DOCX/HWP + Hybrid 분리]
W10-15: [Batch 600K 처리] → 산출물 ③ 순차 전달
W16:    [버퍼 + 품질 리포트]
W17-18: [JD 파싱 + CompanyContext 추출] → 산출물 ④ 전달
W19-22: [잔여 배치 소화 + 품질 관리]
W23:    [버퍼]
W24-25: [홈페이지/뉴스 크롤링] → 산출물 ⑤ 전달
W26-27: [품질 메트릭 최종 + 인수인계]
```

---

## 4. S&F 팀 비용

| Phase | LLM | Embedding | 인프라 | **합계** |
|-------|-----|-----------|-------|--------|
| Phase 0 (PoC) | $7 | $0.1 | $3 | **~$10** |
| Phase 1 (1,000건) | $24 | $1 | $12 | **~$37** |
| Phase 2 (600K) | $1,690 | $52 | $210~360 | **~$1,952~2,102** |
| Phase 3 (JD+Cmp) | $55 | $0.2 | $25 | **~$80** |
| Phase 4 (크롤링) | $11 | $0.1 | $25 | **~$36** |
| **합계** | **$1,787** | **$53** | **$275~425** | **~$2,115~2,265** |

> 전체 v5 비용($5,527~9,137) 중 약 **24~41%**가 S&F 팀 소관.
> Gold Label($2,920~5,840)은 GraphRAG 팀 소관이므로  S&F 순수 비용은 상대적으로 저렴.
