# S&F 팀 실행계획 — 개요

> **역할**: 비정형 데이터를 정형 아티팩트(JSON)로 변환하고, 하드 필터 + 벡터 검색으로 1차 후보군을 제공
> **SLA**: 하드필터+벡터 검색 API **p95 < 500ms**
> **산출물**: GraphRAG 팀에 Data Contract에 맞는 산출물 5종 제공

---

## 1. S&F 팀 타임라인 (~22주)

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

## 2. 문서 구성

| 문서 | 내용 | v5 원본 참조 |
|------|------|------------|
| `01_sf_phase0_poc.md` | 환경+PoC (W1) | `01_phase0_setup_poc.md` |
| `02_sf_phase1_preprocessing.md` | 전처리+LLM 1K (W2-5) | `02_phase1_core_candidate_mvp.md` §1-A~1-C |
| `03_sf_phase2_file_and_batch.md` | 파서+600K Batch (W7-15) | `03_phase2_file_and_scale.md` §2-0~2-4 |
| `04_sf_phase3_jd_company.md` | JD+CompanyContext (W17-18) | `04_phase3_company_and_matching.md` §3-1~3-2 |
| `05_sf_phase4_crawling.md` | 크롤링+보강 (W24-25) | `05_phase4_enrichment_and_ops.md` §4-1~4-2 |
| `06_sf_cost.md` | S&F 비용 SSOT | `06_cost_and_monitoring.md` |

---

## 3. 담당 범위

| 범주 | 상세 |
|------|------|
| **데이터 수집** | DB export, Playwright 크롤링, 홈페이지/뉴스 |
| **전처리** | PII 마스킹(re.sub R1, 8종), CMEK(R3), Career 블록 분리 |
| **파일 파싱** | PDF/DOCX/HWP, Hybrid 섹션 분리(패턴→LLM 폴백 R4) |
| **LLM 추출** | CandidateContext(적응형 v12 M1), CompanyContext(DB+NICE+LLM), Provider 추상화(N5) |
| **임베딩** | Vertex AI 768d, Vector DB 관리 |
| **Batch 운영** | 600K (DB 500K 우선 R6), 비관 시나리오 명시적 Batch 할당 |
| **품질 메트릭** | schema ≥95%, 필드 ≥90%, PII ≤0.01%, 적응형 80/20 |
| **하드 필터 API** | 속성+벡터 검색 → ID Top 500~1,000건 |

---

## 4. 산출물 5종 교환 스펙

| # | 산출물 | 시점 | 형식 | 트리거 |
|---|--------|------|------|--------|
| ① | PoC 결과 (20건+리포트) | W1 D5 | JSON+리포트 | 수동 (Go/No-Go) |
| ② | CandidateContext 1,000건 | W5 | JSONL | PubSub 자동 |
| ③ | CandidateContext 480K+ | W9~15 | JSONL (10K/chunk) | PubSub 자동 |
| ④ | JD + CompanyContext | W17~18 | JSONL | PubSub 자동 |
| ⑤ | 기업 보강 데이터 | W24~25 | JSONL | PubSub 자동 |

> 상세 JSON 스키마 및 PubSub 토픽: `interface/00_data_contract.md` 참조
