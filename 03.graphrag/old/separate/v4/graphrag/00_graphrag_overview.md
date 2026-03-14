> **역할**: S&F가 정제한 아티팩트를 지식 그래프로 적재하고, Chapter 관계 패턴 기반 정밀 매칭·랭킹 수행
> 
> 
> **SLA**: IN-list 그래프 매칭 API **p95 < 2s**
> (복합 인덱스 및 후보자 축소로 2초 이내 응답)
> 

---

## 1. GraphRAG 타임라인 (~18주)

```mermaid
gantt
    title GraphRAG 팀 독립 타임라인
    dateFormat W
    axisFormat %W주차

    section Phase
    G-0: Neo4j 환경 (0.5주)          :gr_0, 0, 0.5w
    [대기A] API골격+선행 (W2-4)      :gr_w1, after gr_0, 3w
    G-1: MVP 적재+API (W5-6)         :gr_1, 4, 2w
    [대기B] Bulk코드+Sizing (W7-9)   :gr_w2, after gr_1, 1.5w
    G-2: 대량 적재+벤치마크 (W10-11) :gr_2, 9, 2w
    버퍼 Go/No-Go (W11후반)          :gr_buf, after gr_2, 0.5w
    G-3: 매칭+ER+튜닝 (W17-22)       :gr_3, 16, 5.5w
    G-4: 증분+운영 (W24-26)          :gr_4, 23, 3w
```

> 통합 병렬 Gantt(S&F + GraphRAG + 인터페이스 포인트): `../interface/README.md` 참조
> 

---

## 2. 리소스 활용률 (Work vs Wait)

| 구간 | 기간 | 유형 | 순수 작업량 |
| --- | --- | --- | --- |
| G-0 | 0.5주 | Work | 0.5주 |
| 대기 A | 3주 | Wait+선행 | 선행 2주 + 유휴 1주 **[v4] 유휴 시간 활용: Organization ER 사전 구축, Gold Set 50건 작성 참여, Neo4j 쿼리 최적화 PoC** |
| G-1 | 2주 | Work | 2주 |
| 대기 B | 1.5주 | Wait+선행 | 선행 1주 + 유휴 0.5주 **[v4] 유휴 시간 활용: Bulk 적재 스크립트 사전 준비, Vector Index 벤치마크** |
| G-2 | 2주 | Work | 2주 |
| 버퍼 | 0.5주 | 판정 | - |
| G-3 | 5.5주 | Work | 5.5주 |
| G-4 | 3주 | Work | 3주 |
| **합계** | **18주** |  | **순수 ~13주, 유휴 ~1.5주 (87%)** |

---

## 3. 문서 구성

| 문서 | 내용 | v5 원본 참조 |
| --- | --- | --- |
| `01_graphrag_g0_setup.md` | Neo4j 환경 + 스키마 | Phase 0 DE Day 2-3 |
| `02_graphrag_g1_mvp.md` | 1K 적재 + API + PII | Phase 1 §1-D |
| `03_graphrag_g2_scale.md` | Professional 전환 + 480K+ + Vector DB 기준 | Phase 2 §2-2 |
| `04_graphrag_g3_matching.md` | 매칭 + ER + 가중치 튜닝 | Phase 3 §3-0, §3-3, §3-4 |
| `05_graphrag_g4_ops.md` | 증분 + Gold Label + 국내 대안 + 운영 | Phase 4 §4-3~4-5 |
| `06_graphrag_cost.md` | GraphRAG 비용 SSOT | `06_cost` |

---

## 5. Go/No-Go 기준

| 전환 | 통과 조건 |
| --- | --- |
| **G-1 -> G-2** | 1K 적재 정상, API 5종 응답, NEXT_CHAPTER 오류 0건 |
| **G-2 -> G-3** | 480K+ 적재, 사이징 안정, Cypher p95 < 2초 |
| **G-3 -> G-4** | MAPPED_TO 규모 정상 (N3), Top-10 적합도 70%+, 가중치 완료 |

---

## 6. S&F 산출물 연계

| S&F 산출물 | 시점 | GraphRAG 활용 |
| --- | --- | --- |
| A PoC 20건 | W1 D5 | Go/No-Go 판정 참여 |
| B 1K JSONL | W5 | **G-1 MVP 적재 시작** |
| C 480K+ JSONL | W9~15 | **G-2 대량 적재** |
| D JD+Company | W17~18 | **G-3 Vacancy 적재 + 매칭** |
| E 기업 보강 | W24~25 | **G-4 CompanyContext 보강 적재** |