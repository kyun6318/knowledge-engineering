# GraphRAG 팀 실행계획

> **v5 Core 실행계획**을 VG4 아키텍처에 따라 GraphRAG 팀 담당 범위만 분리한 독립 실행계획

---

## 역할 정의

S&F 팀이 정제한 아티팩트(JSON)를 Neo4j 지식 그래프로 적재하고,
`[NEXT_CHAPTER]` 기반 관계 패턴과 5-피처 매칭 알고리즘으로 정밀 랭킹을 수행합니다.

**SLA**: IN-list 그래프 매칭 API **p95 < 2s**
**인력**: DE 1명 + MLE 1명
**리소스 활용률**: 87% (순수 작업 ~13주, 유휴 ~1.5주)

---

## 문서 목록

| # | 파일 | Phase | 주차 | 내용 |
|---|------|-------|------|------|
| 0 | `00_graphrag_overview.md` | — | — | Mermaid Gantt, Work/Wait, Go/No-Go, S&F 수신 포인트 |
| 1 | `01_graphrag_g0_setup.md` | G-0 | W1 | Neo4j AuraDB Free + v19 스키마 + 선행 작업 |
| 2 | `02_graphrag_g1_mvp.md` | G-1 | W5~6 | 1K 적재 코드 + Cypher 5종 + REST API + PII 미들웨어 |
| 3 | `03_graphrag_g2_scale.md` | G-2 | W10~11 | AuraDB Professional 마이그레이션(A3) + 사이징(N8) + 벤치마크 |
| 4 | `04_graphrag_g3_matching.md` | G-3 | W17~22 | 5-피처 스코어링 + Vacancy 적재 + Organization ER + 가중치 튜닝(O3) |
| 5 | `05_graphrag_g4_ops.md` | G-4 | W24~26 | 증분 처리(R7/R8) + Gold Label(N6) + Runbook + 운영 |
| 6 | `06_graphrag_cost.md` | — | — | GraphRAG 비용 SSOT (총 ~$3,427~6,777) |

---

## S&F 산출물 수신 → Phase 매핑

| S&F 산출물 | 시점 | GraphRAG Phase |
|-----------|------|---------------|
| ② 1K JSONL | W5 | **G-1** MVP 적재 시작 |
| ③ 480K+ JSONL | W9~15 | **G-2** 대량 적재 |
| ④ JD+Company | W17~18 | **G-3** Vacancy 적재 + 매칭 |
| ⑤ 기업 보강 | W24~25 | **G-4** CompanyContext 보강 |

> Data Contract 상세: `../interface/00_data_contract.md` 참조
