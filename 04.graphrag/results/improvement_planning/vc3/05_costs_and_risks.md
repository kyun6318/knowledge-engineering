# VC3 — 비용 분배 + 리스크 + 의사결정 포인트

---

## 1. 전체 비용 분배

v5 전체 $5,527~9,137 중 팀 분리에 따른 구조:

| 항목 | v5 원본 | S&F 부담 | GraphRAG 부담 | 비고 |
|------|--------|---------|-------------|------|
| LLM (Anthropic+Gemini) | $1,807 | **$1,807** | $0 | LLM 전부 S&F |
| Embedding (Vertex AI) | $52 | **$52** | $0 | 벡터 생성 S&F |
| Neo4j AuraDB | $400~990 | $0 | **$400~990** | GraphRAG 전담 |
| Cloud Run/GCS/BQ | $200~300 | $120~180 | $80~120 | 분산 |
| Gold Label | $2,920~5,840 | $0 | **$2,920~5,840** | 매칭 품질 평가 |
| **합계** | **$5,527~9,137** | **~$2,000~2,100** | **~$3,500~7,000** | 총액 변화 없음 |

> **예산 최적화**: Vector를 S&F 외부 DB로 분리 시 Neo4j 메모리 한 단계 축소 (월 $50~100 절감)

---

## 2. 리스크 및 완화 방안

| # | 리스크 | 위험도 | 비즈니스 영향 | 완화 방안 |
|---|--------|:---:|-------------|---------|
| R1 | **필터링 역전 (Top-K 부족)** | **High** | 적합 후보가 S&F에서 잘려서 GraphRAG에 도달 못함 | S&F Top-K를 필요량 10배 (500~1,000건)으로 설정 |
| R2 | **S&F 산출물 지연** | **High** | GraphRAG 팀 대기(Idle) 증가, 프로젝트 지연 | PubSub 자동 트리거 + Mock Data로 선행 개발 + 주간 싱크 |
| R3 | **API 체인 레이턴시 초과** | **Medium** | 에이전트 사용자 체감 > 5초 → UX 치명적 저하 | SLA p95 < 3s 엄수, min-instances=1, 캐싱 |
| R4 | **Data Contract 스키마 충돌** | **Medium** | 속성명 변경 → Cypher 쿼리 실패 | JSON Schema Git 버저닝 + Phase별 Integration Test |
| R5 | **팀 분리 경계 모호** | **Medium** | 역할 혼동 → 중복/누락 발생 | 73개 태스크 분류 테이블로 경계 명확화 |

---

## 3. 의사결정 포인트 재배치

| 시점 | 의사결정 | 주체 |
|------|---------|------|
| W1 D3 | LLM 모델 선택 (Haiku vs Sonnet) | **S&F** |
| W1 D3 | Embedding 모델 확정 (768d) | **S&F** |
| W1 D5 | Phase 0 Go/No-Go | **공동** (S&F PoC 결과 기반) |
| W6 | Phase 1 Go/No-Go | **공동** (GraphRAG E2E + S&F 품질) |
| W10 | Neo4j 사이징 확정 (N8) | **GraphRAG** |
| W12 | DB 500K 완료율 확인 (R6) | **S&F** (리포트 → GraphRAG 공유) |
| W15 | Phase 2 Go/No-Go | **공동** |
| W17 | MAPPED_TO 규모 테스트 (N3) | **GraphRAG** |
| W17 | job-hub API 스펙 확정 (A1) | **S&F** |
| W22 | 매칭 가중치 재조정 (N7) | **GraphRAG** |
| W26 | Gold Label 100→200건 (N6) | **공동** |

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| `00_review_and_synthesis.md` | VG2 vs VC2 장점 비교 리뷰 + VC3 합성 전략 |
| `01_overview.md` | 분리 배경 + Polyglot 비전 + 역할(SLA 바인딩) + 태스크 집계 + Phase 비교 |
| `02_data_contract.md` | PubSub 파이프라인 + JSON 스키마 3종 + 산출물 5종 + 2-Tier API + SLA |
| `03_graphrag_plan.md` | Mermaid Gantt + Phase G-0~G-4 상세 + Work/Wait 87% + Go/No-Go + 비용 |
| `04_sf_plan.md` | S&F 6범주 + 타임라인 + Phase별 비용 |
| `05_costs_and_risks.md` (본 문서) | 전체 비용 분배 + 5대 리스크 + 의사결정 11건 재배치 |
