# S&F ↔ GraphRAG 인터페이스 사양

> 두 팀 간의 **Data Contract, API SLA, Go/No-Go 기준, 의사결정 포인트**를 정의하는 공동 문서

---

## 핵심 원칙

S&F 팀과 GraphRAG 팀은 **Data Contract(JSON) + Event(PubSub)**으로만 결합합니다.
GraphRAG는 "텍스트가 어떻게 파싱/벡터화되었는지" 전혀 알 필요가 없고,
S&F는 "그래프가 어떻게 구조화/매칭되는지" 전혀 알 필요가 없습니다.

---

## 문서 목록

| # | 파일 | 내용 |
|---|------|------|
| 0 | `00_data_contract.md` | PubSub 토픽 스키마, JSON 3종(Candidate/Vacancy/Enrichment), 산출물 5종 교환 스펙, 2-Tier API SLA, 서비스 계정 4개 보안 |
| 1 | `01_go_nogo_decisions.md` | Phase별 Go/No-Go 통과 기준(팀별 주체 명시), 의사결정 14건(시점·주체·실패 대응), 주간 싱크 회의 |

---

## 2-Tier API SLA

| 구간 | p95 | 담당 |
|------|-----|------|
| S&F API (하드필터+벡터) | < 500ms | S&F |
| GraphRAG API (IN-list 매칭) | < 2s | GraphRAG |
| **전체 체인** | **< 3s** | 공동 |
