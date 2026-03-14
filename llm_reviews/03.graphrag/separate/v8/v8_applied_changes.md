# v8 리뷰 적용 변경 이력

> 적용일: 2026-03-14
> 리뷰 원본: `llm_reviews/03.graphrag/separate/v8/review.md`

---

## 적용 요약

| 이슈 | 심각도 | 수정 파일 | 변경 내용 |
|------|--------|----------|----------|
| C1 | CRITICAL | `graphrag/01_graphrag_g0_setup.md` | MAPPED_TO 방향: `Person→Vacancy` → `Vacancy→Person` |
| C2 | CRITICAL | `sf/04_sf_phase3_jd_company.md` | Vacancy JSON 중복 `seniority` 키 제거 |
| C3 | CRITICAL | 8개 파일 | v19 → v25 스키마 참조 일괄 갱신 |
| C4 | CRITICAL | `interface/README.md`, `graphrag/README.md` | `02_risks.md` → `02_tasks.md` 파일명 수정 |
| H1 | HIGH | `graphrag/07_neo4j_schema.md` | Chapter ~18M 산출 근거 명시 (EXPERIENCED 필터 후 경력 보유율 ~100%) |
| H2 | HIGH | `graphrag/07_neo4j_schema.md` | Chapter/Outcome 유니크 제약 추가 |
| H3 | HIGH | `graphrag/05_graphrag_g4_ops.md` | Gold Label 비용 비율 53~64% → 54~67% |
| H4 | HIGH | `graphrag/07_neo4j_schema.md` | Q1~Q5 → GQ1~GQ5로 재번호 (MVP Q1~Q5와 충돌 해소) |
| H6 | HIGH | `graphrag/04_graphrag_g3_matching.md` | F4 culture_fit: 기본값 0.5 → None + 가중치 재분배 로직 적용 |
| H7 | HIGH | `graphrag/07_neo4j_schema.md` | v1 초기 적재(600K) 규모 추정 별도 기재 |
| L1 | LOW | `interface/01_go_nogo_decisions.md` | 의사결정 포인트 (11건) → (17건) |
| M2 | MEDIUM | `interface/README.md`, `interface/02_tasks.md` | 태스크 집계 73 → 76 (Phase 5 포함) |
| M5 | MEDIUM | `interface/02_tasks.md` | Phase 5 의존성 ID: T1-4/T2-1/T2-4 → 3-3-1/1-D-2/1-D-3 |

---

## 파일별 변경 상세

### graphrag/01_graphrag_g0_setup.md
- line 37: `Person ──[MAPPED_TO]──-> Vacancy` → `Vacancy ──[MAPPED_TO]──-> Person` (C1)
- line 80: `(v19)` → `(v25)` (C3)

### graphrag/02_graphrag_g1_mvp.md
- line 61: `(v19)` → `(v25)` (C3)

### graphrag/04_graphrag_g3_matching.md
- line 10: `(v19 A4)` → `(v25 STAGE_SIMILARITY)` (C3)
- line 31: `Vacancy 적재 (v19)` → `(v25)` (C3)
- line 39: `NEEDS_SIGNAL (v19)` → `(v25)` (C3)
- line 70: `(v19 A4 STAGE_SIMILARITY)` → `(v25 STAGE_SIMILARITY)` (C3)
- line 89-92: F4 culture_fit 기본값 0.5 → None + INACTIVE 처리 (H6)
- line 99-101: overall 계산에 가중치 재분배 로직 추가 (H6)

### graphrag/05_graphrag_g4_ops.md
- line 75: `53~64%` → `54~67%` (H3)

### graphrag/07_neo4j_schema.md
- §4 Q1~Q5 → GQ1~GQ5 (H4, 5개 쿼리 제목 + 인덱스 주석 4곳)
- §7.1 Chapter 산출 근거 보충 (H1)
- §7 서두에 v1 600K 규모 추정 주석 추가 (H7)
- §7.4 PoC 참조 Q→GQ (H4)
- §8.1 Chapter/Outcome 유니크 제약 2건 추가 (H2)
- §8 인덱스 전략 설명 GQ 번호 반영 (H4)

### graphrag/README.md
- line 23: `v19 스키마` → `v25 스키마` (C3)
- line 42: `02_risks.md` → `02_tasks.md` (C4)

### sf/04_sf_phase3_jd_company.md
- line 24-27: 중복 `"seniority": "LEAD"` 행 제거 (C2)

### interface/README.md
- 문서 목록: `02_risks.md` → `02_tasks.md` + 설명 갱신 (C4)
- 태스크 집계: 73 → 76, Phase 5 열 추가 (M2)

### interface/01_go_nogo_decisions.md
- §2 제목: (11건) → (17건) (L1)
- Phase 0 Go/No-Go: `v19 적용 완료` → `v25 적용 완료` (C3)

### interface/02_tasks.md
- 1-D-2, 1-D-8, 3-1-2: `v19` → `v25` (C3)
- Phase 5 의존성 ID 체계 통일: T1-4→3-3-1, T2-1→1-D-2, T2-4→1-D-3 (M5)
- 분류 집계: Phase 5 열 추가, 73 → 76 (M2)

---

## 미적용 항목

| 이슈 | 사유 |
|------|------|
| H5 (SIE 통합) | 구체적 태스크 정의에는 ML팀과의 협의가 필요. 리뷰 문서에 권장사항으로 유지 |
| M1 (LLM 비용 기준) | implementation_roadmap.md는 01.ontology 정본 영역에서 이동한 문서로, 모델 선택 시나리오는 Phase 0 확정 후 갱신 |
| M3 (벤치마크 대상) | G-2 벤치마크 쿼리 목록은 G-1 완료 후 확정 |
| M4 (freshness 참조) | 경로 표기 통일은 다음 전체 리뷰에서 일괄 처리 |
| M6 (Data Contract enum) | outcome_type enum은 02.knowledge_graph 프롬프트 설계와 동기화 필요 |
| L2 (async/sync) | 코드 골격 수준이므로 구현 시점에 통일 |
| L3 (구코드 매핑) | implementation_roadmap.md 갱신은 ontology 레이어 리뷰에서 처리 |
