# S&F 아티팩트 처리팀 실행계획

> **v5 Core 실행계획**을 VG4 아키텍처에 따라 S&F 팀 담당 범위만 분리한 독립 실행계획

---

## 역할 정의

비정형 데이터(이력서, JD, 기업정보)를 정형 아티팩트(JSON)로 변환하고,
하드 필터 + 벡터 검색으로 1차 후보군(Top 500~1,000건)을 GraphRAG 팀에 제공합니다.

**SLA**: 하드필터+벡터 검색 API **p95 < 500ms**

---

## 문서 목록

| # | 파일 | 주차 | 내용 |
|---|------|------|------|
| 0 | `00_sf_overview.md` | — | 전체 타임라인, 6범주 담당 범위, 산출물 5종 교환 스펙 |
| 1 | `01_sf_phase0_poc.md` | W0~1 | GCP 환경, DB 프로파일링, LLM PoC 20건, Embedding 검증 |
| 2 | `02_sf_phase1_preprocessing.md` | W2~5 | PII 마스킹(re.sub R1), CMEK(R3), 적응형 LLM 1,000건 추출 |
| 3 | `03_sf_phase2_file_and_batch.md` | W7~15 | Provider 추상화(N5), PDF/DOCX/HWP 파서, Hybrid 분리(R4), 600K Batch(R6) |
| 4 | `04_sf_phase3_jd_company.md` | W17~18 | JD 파싱(A1), CompanyContext(DB+NICE+LLM), 잔여 Batch |
| 5 | `05_sf_phase4_crawling.md` | W24~25 | 홈페이지/뉴스 크롤링, 기업 보강 데이터 |
| 6 | `06_sf_cost.md` | — | S&F 비용 SSOT (총 ~$1,955) |

---

## 산출물 5종

| # | 산출물 | 시점 | 트리거 |
|---|--------|------|--------|
| ① | PoC 결과 20건 | W1 | 수동 |
| ② | CandidateContext 1K | W5 | PubSub |
| ③ | CandidateContext 480K+ | W9~15 | PubSub |
| ④ | JD + CompanyContext | W17~18 | PubSub |
| ⑤ | 기업 보강 데이터 | W24~25 | PubSub |

> Data Contract 상세: `../interface/00_data_contract.md` 참조
