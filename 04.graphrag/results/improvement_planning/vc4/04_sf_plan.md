# VC4 — S&F 팀 범위 + 산출물 정의

> **역할**: 비정형 데이터를 정형 아티팩트(JSON)로 변환하고, GraphRAG 팀에 Data Contract에 맞는 산출물을 제공
> **SLA 책임**: 하드필터+벡터 검색 API **p95 < 500ms** 달성
> **인력**: 별도 정의 (GraphRAG 팀과 독립 운영)

---

## 1. 담당 범위

### 1.1. 데이터 수집

| 항목 | v5 위치 | 상세 |
|------|--------|------|
| DB 텍스트 이력서 export | Phase 0/1 | resume-hub DB → BigQuery |
| 크롤링 파이프라인 | Phase 1 1-A | Playwright, 법무 허용 시 |
| 홈페이지/뉴스 크롤링 | Phase 4 | 기업 인텔리전스 |

### 1.2. 전처리

| 항목 | v5 위치 | 상세 |
|------|--------|------|
| PII 마스킹 | Phase 1 1-B | re.sub 콜백(R1), 전화번호 8종, 주민번호, 이메일 |
| PII 매핑 저장 | Phase 1 1-B | GCS CMEK 버킷(R3), kg-pii-reader 전용 |
| CMEK 인프라 | Phase 1 1-B | Cloud KMS 키링, 버킷, 서비스계정 |
| Career 블록 분리 | Phase 1 1-B | 정규화 → 마스킹 → 검증 → 분리 |

### 1.3. 파일 파싱

| 항목 | v5 위치 | 상세 |
|------|--------|------|
| PDF/DOCX 파서 | Phase 2 2-1 | 파일→텍스트 |
| HWP 파서 | Phase 2 2-1 | 3가지 방법 조사 후 선택 |
| Hybrid 섹션 분리 | Phase 2 2-1 | 패턴(70%)→LLM 폴백(30%, Batch API) |
| 파일 소스 confidence | Phase 2 2-1 | v12 §4.1.2 패널티 |

### 1.4. LLM 추출

| 항목 | v5 위치 | 상세 |
|------|--------|------|
| CandidateContext | Phase 1 1-C | 적응형: 1-pass(Career≤3) / N+1(Career≥4) |
| CompanyContext | Phase 3 3-2 | DB 직접 + NICE + LLM 3단계 |
| Provider 추상화 | Phase 2 2-0 | Anthropic + Gemini (N5) |
| Batch API 운영 | Phase 2 2-3 | 600K 처리, DB 500K 우선(R6) |

### 1.5. 임베딩+벡터

| 항목 | v5 위치 | 상세 |
|------|--------|------|
| Embedding 생성 | Phase 1 G-5 | Vertex AI text-embedding-005, 768d |
| 벡터 검색 인프라 | Phase 1 G-6 | Vector DB 또는 Neo4j Vector Index 관리 |

### 1.6. 품질 메트릭

| 항목 | 목표 |
|------|------|
| schema 준수율 | ≥95% |
| 필수 필드 완성도 | ≥90% |
| PII 누출율 | ≤0.01% |
| 적응형 호출 비율 | v12 M1 (80/20 검증) |
| 통계적 샘플링 | 384건 |

---

## 2. S&F 타임라인

```
W1:     [환경+PoC] → 산출물 ① (수동, Go/No-Go 회의)
W2-3:   [전처리: PII+CMEK+Career 분리]
W4-5:   [LLM 추출 1,000건] → 산출물 ② (PubSub)
W7:     [코드 리팩토링 + Provider 추상화]
W8-9:   [파서 구축: PDF/DOCX/HWP + Hybrid]
W10-15: [Batch 600K 처리] → 산출물 ③ (PubSub, 순차)
W16:    [버퍼 + 품질 리포트]
W17-18: [JD 파싱 + CompanyContext 추출] → 산출물 ④ (PubSub)
W19-22: [잔여 배치 + 품질 관리]
W23:    [버퍼]
W24-25: [홈페이지/뉴스 크롤링] → 산출물 ⑤ (PubSub)
W26-27: [품질 최종 + 인수인계]
```

---

## 3. S&F 비용

| Phase | LLM | Embedding | 인프라 | **합계** |
|-------|-----|-----------|-------|--------|
| Phase 0 (PoC) | $7 | $0.1 | $3 | **~$10** |
| Phase 1 (1,000건) | $24 | $1 | $12 | **~$37** |
| Phase 2 (600K) | $1,690 | $52 | $210~360 | **~$1,952~2,102** |
| Phase 3 (JD+Cmp) | $55 | $0.2 | $25 | **~$80** |
| Phase 4 (크롤링) | $11 | $0.1 | $25 | **~$36** |
| **합계** | **$1,787** | **$53** | **$275~425** | **~$2,115~2,265** |
