# VC3 — VG2 vs VC2 비교 리뷰 및 합성 전략

> **핵심 방향성 (불변)**: v5의 하드필터·PII·파싱·임베딩 태스크는 **S&F 팀**이, Chapter 기반 그래프 관계 모델링·매칭 알고리즘은 **GraphRAG 팀**이 전담한다. 이 분리의 목적은 GraphRAG 팀이 `[NEXT_CHAPTER]` 중심의 이직 패턴·기업핏 분석에 100% 집중하도록 하는 것이다.

---

## 1. VG2 vs VC2 장점 비교

| 차원 | VG2 강점 | VC2 강점 |
|------|---------|---------|
| **아키텍처 비전** | ★ Polyglot Persistence + Loose Coupling 명확히 선언. Recall(S&F) → Precision(GraphRAG) 2-Tier 흐름 | 분리 배경 3가지 문제점 나열 (실행 동기 중심) |
| **타임라인 시각화** | ★ Mermaid Gantt 차트로 병렬 파이프라인 한눈에 파악 | ASCII 타임라인 (상세하지만 시각성 부족) |
| **R&R 표현** | ★ SLA 목표(500ms/2s/3s)를 역할에 직접 바인딩 | 범주별 업무 테이블 (8개 범주) 상세 |
| **리스크 프레이밍** | ★ "비즈니스 영향"까지 칼럼 추가한 리스크 매트릭스 | 완화 방안은 유사하나 비즈니스 임팩트 미명시 |
| **태스크 추적성** | Phase 단위 요약만 | ★ v5 73개 태스크 1:1 S/G/공동 전수 분류 |
| **Data Contract** | JSON 샘플 + 필드 목록 | ★ JSON 샘플 + 필수 조건(시간순 정렬 등) + **PubSub 토픽 스키마** (artifact_type, batch_id, record_count) |
| **S&F 산출물** | 거시적 3줄 서술 | ★ 5단계 산출물 명세 (PoC→1K→480K→JD→보강) + 시점·형식·GCS 경로·트리거 방식 |
| **비용** | 팀별 통합 비용 1테이블 | ★ Phase별 LLM/Embedding/인프라 세분화 비용 + GraphRAG Phase별 Neo4j/Gold Label 분리 |
| **Work/Wait 분리** | 언급만 (87% 활용률) | ★ 구간별 순수 작업량 정량 테이블 (13주 작업 + 1.5주 유휴) |
| **Go/No-Go** | Phase별 1줄 통과 기준 | ★ Phase별 구체적 통과 조건 테이블 (적재량, p95, Top-10 70%) |
| **의사결정 포인트** | 없음 | ★ 11개 의사결정 시점별 주체 재배치 |
| **Vector DB 기준** | "1M 초과 시 외부화" 1줄 | ★ 3가지 시나리오 테이블 (Person < 1M / ≥ 1M / 현재 규모) |

---

## 2. VC3 합성 원칙

| # | VG2에서 가져올 것 | VC2에서 가져올 것 |
|---|-----------------|-----------------|
| 1 | **Polyglot + 2-Tier 아키텍처 비전** — 분리의 "왜"를 설계 철학으로 승격 | **73개 태스크 전수 분류** — 분리의 "무엇을"을 누락 없이 추적 |
| 2 | **Mermaid Gantt 시각화** — 타임라인 가독성 | **Work/Wait 정량 테이블** — 리소스 활용률 87% 근거 |
| 3 | **역할에 SLA 바인딩** — S&F < 500ms / GraphRAG < 2s | **PubSub 토픽 스키마** — 자동 트리거 구체화 |
| 4 | **비즈니스 임팩트 포함 리스크** — 경영진 보고 적합 | **Phase별 세분화 비용** — 예산 승인 근거 |
| 5 | — | **S&F 산출물 5종 명세** — GraphRAG 개발 일정 확정의 전제 |
| 6 | — | **Go/No-Go 통과 기준 + 의사결정 주체** — Phase 전환 품질 게이트 |

---

## 3. VC3 문서 구성

| 문서 | 합성 전략 |
|------|---------|
| `01_overview.md` | VG2의 Polyglot 비전 + VC2의 분리 배경/역할 정의/Vector DB 기준 + 양쪽 SLA 통합 |
| `02_data_contract.md` | VG2의 2-Tier API 흐름 다이어그램 + VC2의 JSON 스키마·PubSub 토픽·산출물 5종 명세 합산 |
| `03_graphrag_plan.md` | VG2의 Mermaid Gantt + VC2의 Phase G-0~G-4 상세 + Work/Wait 정량 테이블 + Go/No-Go |
| `04_sf_plan.md` | VC2의 S&F 6범주 + 산출물 5종 + Phase별 비용 전부 유지, VG2의 SLA 바인딩 추가 |
| `05_costs_and_risks.md` | VG2의 비즈니스 임팩트 리스크 프레이밍 + VC2의 Phase별 세분화 비용 + 의사결정 주체 11개 |
