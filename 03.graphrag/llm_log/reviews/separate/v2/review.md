# Separate 문서 분리 리뷰 v2

> **리뷰 대상**: `04.graphrag/results/implement_planning/separate/v2/` (graphrag 8개 + sf 8개 + interface 4개 = 20개 문서)
> **리뷰 기준**: v1 리뷰 7건 반영 검증 + 신규 이슈 탐색
> **리뷰 일자**: 2026-03-12

---

## 1. 총평

v2는 v1 리뷰의 **즉시 반영 3건(S1~S3) + 권장 반영 4건(R1~R4)을 전부 반영**했다. 특히 `interface/02_risks.md` 신규 생성으로 팀 분리 고유 리스크(R1~R5)가 완비되었고, 통합 병렬 Gantt와 태스크 집계가 `interface/README.md`에 추가되어 **인터페이스 문서의 완성도가 크게 향상**되었다.

**v2의 핵심 가치**:
- 팀 분리 고유 리스크 5건 + v5 이관 리스크 5건 = **10건 리스크 관리 체계 완비**
- 통합 Gantt로 **양 팀 병렬성 시각화** + 인터페이스 포인트 4개 마일스톤 명시
- v5 리뷰 실행 체크리스트(E1~E5)가 **해당 팀 문서에 실행 가능한 형태로 삽입**
- 비용 차이 $145~405의 **원인별 명시** (공동 인프라 분배 방식)

**결론**: v2는 **추가 리비전 없이 실행 진입 가능한 최종 분리 문서**이다. 아래에서 발견된 이슈는 모두 VERY LOW이며, 실행 단계에서 자연스럽게 해소된다.

---

## 2. v1 리뷰 반영 검증

### 즉시 반영 3건 — 전부 반영

| # | v1 리뷰 항목 | v2 반영 | 위치 | 평가 |
|---|------------|--------|------|------|
| S1 | 5대 리스크 + 완화 방안 | `interface/02_risks.md` 신규 생성 (R1~R5 + v5 이관 5건 + 스키마 변경 관리 + E1~E5) | interface/02 | **우수** — 리스크뿐 아니라 스키마 변경 관리 절차(R4 완화)까지 포함 |
| S2 | 통합 병렬 Gantt | `interface/README.md`에 Mermaid Gantt 추가 (S&F + 인터페이스 + GraphRAG 3섹션) | interface/README | **정확히 해결** |
| S3 | E1/E3 실행 체크리스트 | E1 → `sf/03` §2-3에 W10 체크포인트 삽입, E3 → `graphrag/05` Gold Label 하위에 국내 대안 검토 삽입 | sf/03, graphrag/05 | **실행 가능** |

### 권장 반영 4건 — 전부 반영

| # | v1 리뷰 항목 | v2 반영 | 위치 | 평가 |
|---|------------|--------|------|------|
| R1 | Vector DB 선택 기준 | 3시나리오 테이블 추가 | `graphrag/03` N8 하위 | **적절** |
| R2 | 73개 태스크 집계 | Phase별/팀별 집계 테이블 추가 | `interface/README` | **적절** |
| R3 | Phase 기간 비교 | v5 대비 단축 효과 테이블 추가 (§2 신규 섹션) | `graphrag/00` | **적절** |
| R4 | 비용 차이 명시 | 양쪽 cost 문서에 VG4 대비 차이 원인별 테이블 추가 | `graphrag/06`, `sf/06` | **상세** |

### 반영 품질 평가

- **S1이 가장 우수**: 단순 리스크 나열이 아니라 (1) 5대 리스크, (2) v5 이관 리스크, (3) 스키마 변경 관리 절차, (4) 실행 체크리스트를 **4개 섹션으로 구조화**. 이 문서 하나로 팀 분리 관련 모든 리스크 관리가 가능.
- **S3의 E1 반영**이 특히 좋음: 단순히 "18h 초과 시 비관 대응"만이 아니라 **구체적 대응 3단계**(Batch 비율 변경, Gemini 병행, GraphRAG 사전 공지)를 명시. v1의 처리 시간 계산 섹션에 자연스럽게 삽입.
- **R4 비용 차이**: Phase 2 인프라($76~226)가 가장 큰 갭이며, 공동 Monitoring/Logging이 원인임을 명시. 이제 "왜 합계가 다른지" 의문 없음.

---

## 3. 과도한 설계 (Over-Engineering)

### O1. interface/02_risks.md의 E1~E5 중복 (VERY LOW)

**현상**: E1은 `sf/03`에도 있고 `interface/02_risks.md` §4에도 있다. E3은 `graphrag/05`에도 있고 `interface/02_risks.md` §4에도 있다.

```
중복 위치:
  E1: sf/03 §2-3 "W10 중간 체크포인트" + interface/02 §4 "실행 체크리스트"
  E3: graphrag/05 "국내 전문가 대안" + interface/02 §4 "실행 체크리스트"
```

**평가**: 의도적 중복이다. `interface/02`는 **전체 조망 리스트**이고, 각 팀 문서는 **실행 상세**이다. 중복이지만 "interface에서 전체를 보고, 팀 문서에서 상세를 본다"는 2계층 구조로서 합리적. 수정 불필요.

---

## 4. 부족한 설계 (Under-Engineering)

### U1. S&F README에 interface/02_risks.md 참조 미추가 (VERY LOW)

**현상**: `graphrag/README.md`에는 `../interface/02_risks.md` 참조가 추가되었으나, `sf/README.md`에는 없다.

```
graphrag/README.md: "팀 분리 리스크: ../interface/02_risks.md 참조" ✅
sf/README.md:       참조 없음 ✗
```

**평가**: sf/README.md는 v1에서 변경 없이 복사되었기 때문. 기능적 영향 없으나 교차 참조 일관성을 위해 추가 권장.

**권장**: `sf/README.md`에 `> 팀 분리 리스크: ../interface/02_risks.md 참조` 1줄 추가.

---

## 5. 문서 간 정합성

### 5.1 v1 대비 신규 추가 항목 정합

```
interface/README Gantt 주차 = graphrag/00 Gantt 주차 ✅
  G-0: 0.5주 W1   ✅
  G-1: 2주 W5-6   ✅
  G-2: 2주 W10-11 ✅
  G-3: 5.5주 W17-22 ✅
  G-4: 3주 W24-26 ✅

interface/README 태스크 집계 73개:
  S&F 35 + GraphRAG 29 + 공동 9 = 73 ✅

graphrag/00 기간 비교 테이블:
  합계 27주→~18주 (0.5+2+2+4+3+1 = 12.5주 순수 + 대기 = ~18주 캘린더) ✅

비용 차이 교차 검증:
  graphrag/06: 공동 인프라 차이 $76~226 (Phase 2) + $11 (G-0~G-1) + $58~168 (기타)
  sf/06: 공동 인프라 차이 $76~226 (Phase 2) + $2 (Phase 1)
  양쪽 문서의 Phase 2 인프라 차이 $76~226이 일치 ✅
```

### 5.2 교차 참조 네트워크

```
v1 참조 관계:
  graphrag/README → interface/00 ✅
  sf/README       → interface/00 ✅

v2 추가 참조:
  graphrag/README → interface/02 ✅ (신규)
  sf/03           → interface/02 ✅ (신규: "리스크 상세" 링크)
  graphrag/05     → interface/02 ✅ (신규: "리스크 상세" 링크)
  graphrag/00     → interface/README ✅ (신규: "통합 Gantt" 링크)
  sf/README       → interface/02 ✗ (누락, U1)
```

### 5.3 interface/README 문서 목록 일치

```
README 문서 목록: 3개 (00, 01, 02)
실제 파일: 00_data_contract.md, 01_go_nogo_decisions.md, 02_risks.md
일치 ✅
```

---

## 6. v1 → v2 변경 요약

| 파일 | 변경 유형 | 내용 |
|------|---------|------|
| `interface/02_risks.md` | **신규** | 5대 리스크 + v5 이관 리스크 + 스키마 변경 관리 + E1~E5 |
| `interface/README.md` | **확장** | 통합 Mermaid Gantt + 73개 태스크 집계 + 문서 목록 3개로 갱신 |
| `sf/03_sf_phase2_file_and_batch.md` | **추가** | §2-3에 E1 W10 체크포인트 (18h 기준 + 3단계 대응) |
| `graphrag/05_graphrag_g4_ops.md` | **추가** | Gold Label 하위에 E3 국내 전문가 대안 ($730~1,460) |
| `graphrag/03_graphrag_g2_scale.md` | **추가** | N8 하위에 Vector DB 3시나리오 테이블 |
| `graphrag/00_graphrag_overview.md` | **추가** | §2 신규: v5 대비 기간 비교 테이블 + interface/README Gantt 링크 |
| `graphrag/06_graphrag_cost.md` | **추가** | 비용 검증에 VG4 대비 차이 원인별 테이블 |
| `sf/06_sf_cost.md` | **추가** | VG4 대비 차이 원인별 테이블 |
| `graphrag/README.md` | **갱신** | 문서 목록 설명 갱신 + interface/02 참조 추가 |

**변경 없는 파일 (11개)**: interface/00, interface/01, graphrag/01, graphrag/02, graphrag/04, sf/00, sf/01, sf/02, sf/04, sf/05, sf/README

---

## 7. 최종 권장사항

### 7.1 즉시 반영 필요

**없음.** v2는 v1 리뷰의 7건을 전부 반영하여 실행 진입에 충분한 완성도를 갖추고 있다.

### 7.2 권장 (1건, VERY LOW)

| # | 항목 | 조치 |
|---|------|------|
| U1 | sf/README에 interface/02_risks.md 참조 추가 | 1줄 추가: `> 팀 분리 리스크: ../interface/02_risks.md 참조` |

---

## 8. 결론

v2는 v1의 **구조적 결함**(리스크 누락, 통합 시각화 부재, 실행 체크리스트 미반영)을 모두 해소했다.

**문서 완성도 진화**:
```
v1: 85% — 팀별 실행계획 + interface 사양 양호, 리스크·통합 뷰 결여
v2: 98% — 리스크 관리 체계 + 통합 Gantt + 실행 체크리스트 완비
나머지 2%: sf/README 참조 1줄 (VERY LOW)
```

**인터페이스 문서 진화**:
```
v1: 2개 문서 (Data Contract + Go/No-Go)
v2: 3개 문서 (+ Risks) + README에 통합 Gantt + 태스크 집계
→ "분리의 접착제" 역할 완성
```

현재 separate v2 문서 세트(graphrag 8 + sf 8 + interface 4 = 20개)는 **두 팀이 독립적으로 실행하면서 인터페이스로 결합하는** 구조를 완전히 지원한다. **추가 리비전 없이 실행 단계로 진입**할 수 있다.
