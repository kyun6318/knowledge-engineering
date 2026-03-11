# Separate 문서 분리 리뷰 v1

> **리뷰 대상**: `04.graphrag/results/implement_planning/separate/` (graphrag 8개 + sf 8개 + interface 3개 = 19개 문서)
> **리뷰 기준**: VG4(`improvement_planning/vg4/`) 설계 + v5 리뷰(`llm_log/reviews/core/5/review.md`)
> **리뷰 관점**: VG4 대비 누락 항목, v5 리뷰 반영 여부, 문서 간 정합성
> **리뷰 일자**: 2026-03-12

---

## 1. 총평

VG4의 5개 문서를 **graphrag(7+README) / sf(7+README) / interface(2+README)** 3개 디렉토리로 분리한 결과, **Data Contract·Go/No-Go·Phase 상세·비용 SSOT** 등 실행에 필요한 핵심 내용은 잘 분리되었다. 특히 interface 디렉토리의 Go/No-Go를 Phase별로 세분화하고 의사결정 포인트를 11건→14건으로 확장한 것은 VG4 대비 **개선**이다.

그러나 **팀 분리 고유의 리스크(R1~R5)**가 완전 누락되어 있고, 두 팀의 병렬 동작을 한눈에 조망하는 **통합 Gantt**가 없으며, v5 리뷰의 **실행 단계 체크리스트(E1~E5)**가 반영되지 않았다. 이 3가지는 "분리 문서"이기 때문에 오히려 더 중요한 항목이며, 즉시 보완이 필요하다.

---

## 2. 커버리지 양호 항목

| VG4 원본 위치 | 내용 | separate 위치 | 평가 |
|-------------|------|-------------|------|
| 02 §1 | 비동기 파이프라인 (GCS→PubSub→적재) | `interface/00_data_contract.md` §1 | 완전 커버 |
| 02 §2 | JSON Data Contract 3종 | `interface/00_data_contract.md` §2 | 완전 커버 |
| 02 §2A | CandidateContext 필수 조건 4개 | `interface/00_data_contract.md` §2A | 완전 커버 |
| 02 §3 | 산출물 5종 교환 스펙 | `interface/00_data_contract.md` §3 | 완전 커버 |
| 02 §4 | 2-Tier API 체인 + SLA | `interface/00_data_contract.md` §4 | 완전 커버 |
| — | PII 보안 + 서비스 계정 4개 | `interface/00_data_contract.md` §5 | **VG4보다 상세** (신규 추가) |
| 03 §3 | Go/No-Go 통과 기준 | `interface/01_go_nogo_decisions.md` §1 | **VG4보다 상세** (Phase별 세분화) |
| 03 §4 | 의사결정 포인트 11건 | `interface/01_go_nogo_decisions.md` §2 | **14건으로 확장** (W0 즉시 2건 + W27 1건 추가) |
| — | 주간 싱크 회의 | `interface/01_go_nogo_decisions.md` §3 | 신규 추가 |
| 04 §1 | GraphRAG G-0~G-4 Phase 상세 | `graphrag/01~05` 각 문서 | 완전 커버 |
| 04 §2 | S&F 6범주 + 주차별 타임라인 | `sf/00~05` 각 문서 | 완전 커버 |
| 01 §2.1 | S&F 역할 (8범주 + SLA) | `sf/00_sf_overview.md` §3 | 완전 커버 |
| 01 §2.2 | GraphRAG 역할 (8범주 + SLA) | `graphrag/00_graphrag_overview.md` + README | 완전 커버 |
| 03 §2 | Work vs Wait 테이블 | `graphrag/00_graphrag_overview.md` §2 | GraphRAG만 커버 (S&F는 해당 없음) |

### v5 리뷰 반영 항목 — 분산 커버

| v5 항목 | separate 위치 | 평가 |
|---------|-------------|------|
| S1: 비용 SSOT | `graphrag/06_cost.md` + `sf/06_cost.md` | 각 팀별 SSOT 구성 |
| A1: JD 파서 대응 절차 | `sf/04_sf_phase3_jd_company.md` §3-1 | "비구조화 시 1주 확장" 명시 |
| A2: PoC 비용 외삽 ±50% | `interface/01_go_nogo_decisions.md` §1 Phase 0 | 통과 조건에 포함 |
| A3: AuraDB 마이그레이션 7단계 | `graphrag/03_graphrag_g2_scale.md` | 완전 커버 |
| A4: Cold Start 대안 2개 | `graphrag/05_graphrag_g4_ops.md` | 완전 커버 |
| U2: mask_phones() 주석 | `sf/02_sf_phase1_preprocessing.md` | "v5 U2" 주석 포함 |

---

## 3. 누락 항목

### N1. 5대 리스크 + 완화 방안 — 완전 누락 (HIGH)

**현상**: VG4 `05_costs_and_risks.md` §3의 5대 리스크가 separate 19개 문서 어디에도 존재하지 않는다.

```
누락된 리스크:
  R1 필터링 역전 (Top-K 부족)     — High
     S&F가 100건만 넘기면 매칭 품질 치명 저하
     완화: Top-K를 500~1,000건으로 Data Contract 명문화

  R2 S&F 산출물 지연              — High
     600K 에러/지연 → GraphRAG 개발 정지
     완화: PubSub 자동 트리거 + Mock Data 선행 + 주간 싱크

  R3 API 체인 레이턴시 초과        — Medium
     2-Tier 연속 호출로 사용자 체감 > 5초
     완화: SLA p95 < 3s 엄수, min-instances=1, 캐싱

  R4 Data Contract 스키마 충돌     — Medium
     S&F 필드명 변경 → Cypher 쿼리 실패
     완화: JSON Schema Git 버저닝 + Phase별 Integration Test

  R5 팀 분리 경계 모호             — Medium
     역할 혼동 → 중복/누락
     완화: 73개 태스크 분류 테이블 + 주간 싱크 회의
```

**영향**: R1, R2는 **High** 등급이다. 팀 분리 문서이기 때문에 오히려 "분리로 인해 발생하는 리스크"가 핵심 관리 항목인데, 이것이 없으면 두 팀이 **리스크 인식 없이 실행**하게 된다. 특히 R4(스키마 충돌)는 Data Contract이 있지만 **변경 관리 절차**가 명시되지 않으면 실효성이 낮다.

**권장**: `interface/02_risks.md` 신규 생성. VG4 §3의 5대 리스크 + 완화 방안 + v5 리뷰 리스크 매트릭스 중 팀 분리 관련 항목(Phase 2 여유 0일, Batch API 동시 한도 등) 통합.

---

### N2. 통합 병렬 Gantt 차트 누락 (MEDIUM)

**현상**: VG4 `03_unified_execution_plan.md` §1의 **S&F + GraphRAG + 인터페이스 포인트**를 한눈에 보여주는 Mermaid Gantt가 없다.

```
현재 상태:
  graphrag/00_overview.md → GraphRAG만의 독립 Gantt
  sf/00_overview.md       → 텍스트 타임라인 (Gantt 아님)
  interface/              → 타임라인 시각화 없음

VG4 원본에는 있었던 것:
  section S&F 팀 (~22주)      ← 없음
  section 인터페이스 포인트     ← 없음 (①②③④ 마일스톤)
  section GraphRAG 팀 (~12.5주) ← graphrag/00에만 존재
```

**영향**: 팀 분리의 핵심 가치는 "병렬 동작"인데, 이 병렬성을 한눈에 보여주는 시각화가 없다. 각 팀이 자기 타임라인만 보고 **상대팀 일정과의 연관성을 놓칠** 수 있다. 특히 "대기 구간 A/B가 왜 발생하는지"는 통합 Gantt 없이 이해하기 어렵다.

**권장**: `interface/` README 또는 별도 문서에 VG4 §1의 통합 Mermaid Gantt 포함. 양쪽 팀 문서에서 이를 참조하도록 링크.

---

### N3. 실행 단계 체크리스트(E1~E5) 미반영 (MEDIUM)

**현상**: v5 리뷰 §8.2의 실행 시 인지 항목 5건이 separate 문서에 반영되지 않았다.

```
E1: Week 10 — Batch API 라운드 시간 실측, 18h 초과 시 비관 대응 발동
    → sf/03_phase2에 처리 시간 계산(45일/45일)은 있으나
      "18h 초과 시 비관 대응 발동"이라는 판단 기준 부재

E2: Week 16 — Phase 3-1 JD 파서 0.5주 가능 여부 확인
    → sf/04_phase3에 A1 반영됨 ✅ (커버됨)

E3: Week 22~23 — Gold Label 전문가 확보 + 국내 대안 사전 검토
    → graphrag/05_g4_ops에 Gold Label 2단계(N6)는 있으나
      "국내 전문가 대안($730~1,460)" 사전 검토가 없음

E4: Week 27 — Cold Start 대응 결정
    → graphrag/05_g4_ops에 반영됨 ✅ (커버됨)

E5: 실행 중 문서 수정 시 추적 테이블 분리 검토
    → 별도 분리 구조이므로 추적 테이블 문제 자체가 해소됨 ✅
```

**권장**:
- E1 → `sf/03_sf_phase2_file_and_batch.md`의 처리 시간 계산 부분에 **"W10 체크: 라운드 시간 18h 초과 시 비관 대응 발동"** 추가
- E3 → `graphrag/05_graphrag_g4_ops.md`의 Gold Label 부분에 **"국내 전문가 대안 사전 검토 (W22~23, $730~1,460 가능)"** 추가

---

### N4. Vector DB 선택 기준 3시나리오 누락 (LOW)

**현상**: VG4 `01_architecture_and_roles.md` §2.3의 의사결정 기준이 `graphrag/` 어디에도 없다.

```
누락된 테이블:
  | 조건                          | 선택                    | 근거                     |
  | Person < 1M, Chapter < 3M    | Neo4j Vector Index 유지  | 인프라 단순, 복합 쿼리 가능 |
  | Person ≥ 1M 또는 QPS > 50    | Milvus/Pinecone 외부화   | Neo4j 메모리 절감          |
  | 현재 v5 규모 (600K)           | Neo4j 유지 권장          | S&F가 벡터 검색 별도 관리   |
```

**권장**: `graphrag/03_graphrag_g2_scale.md`의 사이징 섹션에 추가. G-2에서 사이징 확정 시 참조해야 할 의사결정 기준.

---

### N5. 73개 태스크 분류 집계 누락 (LOW)

**현상**: VG4 `01_architecture_and_roles.md` §3의 팀별/Phase별 태스크 집계 테이블이 없다.

```
누락된 테이블:
  | 팀       | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | 합계       |
  | S&F      | 10      | 8       | 10      | 6       | 1       | 35 (48%)   |
  | GraphRAG | 1       | 7       | 4       | 7       | 10      | 29 (40%)   |
  | 공동     | 2       | 1       | 2       | 3       | 1       | 9 (12%)    |
  | 합계     | 13      | 16      | 16      | 16      | 12      | 73         |
```

**영향**: R5(팀 분리 경계 모호) 리스크의 완화 수단이 이 집계 테이블이다. 리스크도 없고 완화 수단도 없는 상태.

**권장**: `interface/README.md`에 집계 테이블 추가. 상세 태스크 목록은 `v1/c_01_task_classification.md` 참조로 링크.

---

### N6. Phase별 기간 비교 테이블 누락 (LOW)

**현상**: VG4 `01_architecture_and_roles.md` §4의 v5 원본 vs 분리 후 기간 비교가 없다.

```
누락된 테이블:
  | Phase   | v5 원본 | 분리 후 GraphRAG | 단축 근거              |
  | Phase 0 | 1주     | 0.5주            | LLM PoC·Embedding은 S&F |
  | Phase 1 | 5주     | 2주              | 전처리·LLM 추출 S&F 이관 |
  | Phase 2 | 9주     | 2주              | 파서·600K Batch S&F      |
  | Phase 3 | 6주     | 4주              | JD 파싱·CompanyContext S&F |
  | Phase 4 | 4주     | 3주              | 크롤링·보강 S&F           |
  | 합계    | 27주    | ~12.5주           | 순수 ~8주 + 대기 ~4.5주   |
```

**영향**: "왜 27주가 12.5주로 줄었는지"의 근거. 신규 참여자나 의사결정자에게 분리 효과를 설명할 때 필요.

**권장**: `graphrag/README.md` 또는 `graphrag/00_graphrag_overview.md`에 추가.

---

### N7. 비용 총합 불일치 — 구체적 원인 미명시 (LOW)

**현상**: VG4와 separate 간 비용 총합에 차이가 있다.

```
| 출처     | S&F            | GraphRAG          | 합계              |
| VG4      | ~$2,000~2,100  | ~$3,500~7,000     | $5,527~9,137      |
| separate | ~$1,955        | ~$3,427~6,777     | ~$5,382~8,732     |
| 차이     | -$45~145       | -$73~223          | -$145~405         |

graphrag/06_cost.md 하단:
  "v5 원본 $5,527~9,137 대비 차이는 일부 공동 인프라 비용의 분배 방식 차이에 기인"
  → 어떤 공동 인프라 비용인지 미명시
```

**분석**:
- VG4 S&F Phase 1 합계 ~$37 vs separate ~$34 (차이 $3: Cloud Run 분배)
- VG4 S&F Phase 2 합계 ~$1,952~2,102 vs separate ~$1,824 (차이 $128~278: 가장 큰 갭)
- VG4 GraphRAG G-0~G-1 합계 ~$15 vs separate ~$4 (차이 $11)

Phase 2의 차이가 가장 크며, VG4에서는 인프라를 $210~360으로 잡았으나 separate에서는 $134로 세분화했다.

**권장**: 양쪽 cost 문서에 "VG4 대비 차이 항목" 각주 추가. 또는 `interface/`에 비용 교차 검증 테이블 1개 추가.

---

## 4. 개선된 항목 (VG4 대비)

separate 문서가 VG4보다 **더 나아진** 부분도 있다:

| 항목 | VG4 | separate | 평가 |
|------|-----|---------|------|
| Go/No-Go 세분화 | Phase 간 3개 테이블 | Phase별 주체·미달 대응까지 명시 | **개선** |
| 의사결정 포인트 | 11건 | 14건 (W0 즉시 2건 + W27 1건 추가) | **개선** |
| PII 보안 | Data Contract 내 암시 | §5에서 서비스 계정 4개 + 접근 정책 명시 | **개선** |
| 주간 싱크 | VG4에 없음 | `interface/01_go_nogo_decisions.md` §3 | **신규 추가** |
| 코드 예시 상세도 | 서술 중심 | 각 Phase 문서에 실행 가능 수준 코드 | **개선** |

---

## 5. 문서 간 정합성

### 5.1 교차 참조 — 양호

```
graphrag/README.md → interface/00_data_contract.md 참조 ✅
sf/README.md      → interface/00_data_contract.md 참조 ✅
graphrag/00       → S&F 산출물 수신 포인트 5종 명시 ✅
sf/00             → 산출물 5종 + interface 참조 ✅
```

### 5.2 내부 수치 정합

```
산출물 시점 일치:
  interface/00 ② W5 = graphrag/00 ② W5 = sf/00 ② W5 ✅
  interface/00 ③ W9~15 = graphrag/00 ③ W9~15 = sf/00 ③ W9~15 ✅
  interface/00 ④ W17~18 = graphrag/00 ④ W17~18 = sf/00 ④ W17~18 ✅
  interface/00 ⑤ W24~25 = graphrag/00 ⑤ W24~25 = sf/00 ⑤ W24~25 ✅

SLA 일치:
  interface/00 S&F < 500ms = sf/README < 500ms ✅
  interface/00 GraphRAG < 2s = graphrag/README < 2s ✅
  interface/00 전체 < 3s ✅

Go/No-Go 기준 일치:
  interface/01 G-1→G-2 = graphrag/00 §4 ✅
  interface/01 G-2→G-3 = graphrag/00 §4 ✅
  interface/01 G-3→G-4 = graphrag/00 §4 ✅
```

### 5.3 의사결정 포인트 수 불일치 — 경미

```
VG4 03_unified_execution_plan.md: 11건
interface/01_go_nogo_decisions.md: 14건 (+3건)

추가된 3건:
  - W0 즉시: Batch API quota 확인 (S&F)
  - W0 즉시: Gemini Flash Batch 검증 (S&F)
  - W27: Phase 4 Go/No-Go (공동)

평가: VG4 대비 개선. 추가 3건 모두 합리적.
interface/README.md에는 "14건"으로 표기 필요 (현재 미표기).
```

---

## 6. 최종 권장사항

### 6.1 즉시 반영 필요 (3건)

| # | 항목 | 조치 | 해당 누락 |
|---|------|------|---------|
| S1 | 5대 리스크 + 완화 방안 | `interface/02_risks.md` 신규 생성 | N1 |
| S2 | 통합 병렬 Gantt | `interface/` README 또는 별도 문서에 Mermaid Gantt 추가 | N2 |
| S3 | 실행 체크리스트 반영 | sf/03에 E1(18h 기준) 추가, graphrag/05에 E3(국내 대안) 추가 | N3 |

### 6.2 권장 반영 (4건)

| # | 항목 | 조치 | 해당 누락 |
|---|------|------|---------|
| R1 | Vector DB 선택 기준 | `graphrag/03_g2_scale.md`에 3시나리오 테이블 추가 | N4 |
| R2 | 73개 태스크 집계 | `interface/README.md`에 집계 테이블 추가 | N5 |
| R3 | Phase 기간 비교 | `graphrag/00_overview.md`에 비교 테이블 추가 | N6 |
| R4 | 비용 차이 명시 | 양쪽 cost 문서에 VG4 대비 차이 각주 추가 | N7 |

---

## 7. 결론

separate 문서의 **팀별 실행계획 + interface 사양**은 VG4의 의도를 잘 구현했다. 특히 Go/No-Go 세분화, 의사결정 포인트 확장, PII 보안 명시, 코드 예시 상세화는 **VG4보다 실행 친화적**이다.

그러나 **"분리했기 때문에 생기는 리스크"**가 빠진 것은 구조적 결함이다. 팀 분리 문서의 핵심 가치는 (1) 각 팀이 자기 범위를 명확히 아는 것, (2) 인터페이스 사양으로 결합하는 것, 그리고 **(3) 분리로 인한 리스크를 공동 관리하는 것**인데, 현재 (3)이 없다.

**S1(리스크) + S2(통합 Gantt) + S3(실행 체크리스트)** 3건을 반영하면 실행 진입에 충분한 완성도가 확보된다.
