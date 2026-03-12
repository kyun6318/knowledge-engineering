# v12 조치 사항 및 권고

> 리뷰일: 2026-03-11 | 리뷰어: Claude Opus 4.6
> 대상: 02.knowledge_graph/results/extraction_logic/v12/

---

## 1. 조치 사항 요약

| 우선순위 | 건수 | 비고 |
|---------|------|------|
| Must (구현 전) | 2건 | v12 문서 보강 또는 Phase 1 시작 전 해소 |
| Should (Phase 1 중) | 3건 | Phase 1 구현 과정에서 해소 |
| Could (향후) | 3건 | Phase 2 이후 또는 필요 시 |

---

## 2. Must — 구현 전 필수

### M1. N+1 pass 프롬프트에 전체 Career 요약 컨텍스트 추가

- **문서**: 03_prompt_design.md §2.2.2
- **문제**: Career별 개별 호출 시 전체 이력 맥락 부재로 scope_type 판단 부정확
- **조치**: Pass 1~N 프롬프트에 "전체 경력 요약 (분석 대상 제외)" 섹션 추가
- **비용 영향**: Batch 기준 ~$3.6 추가 (무시 가능)
- **상세**: 04_review_under_engineering.md §1

### M2. person_id vs candidate_id 필드명 통일

- **문서**: 01_extraction_pipeline.md §5 전체, 04.graphrag Core v2 §10-11
- **문제**: v12(person_id)와 Core v2(candidate_id)의 ID 필드명 불일치
- **조치**:
  - 옵션 A: v12의 person_id 채택, Core v2를 수정 (권고)
  - 옵션 B: Core v2의 candidate_id 채택, v12를 수정
  - 최소: 매핑 관계를 양 문서에 명시
- **비용 영향**: $0 (문서 수정)

---

## 3. Should — Phase 1 구현 중 해소

### S1. chapters 출력 순서 보장

- **문서**: 03_prompt_design.md §2.3
- **문제**: LLM이 chapters를 입력 순서대로 반환하리라는 보장 없음
- **조치**: career_index 필드 추가 또는 프롬프트에 순서 지시 명시
- **상세**: 04_review_under_engineering.md §3

### S2. Batch API 부분 실패 재처리 전략

- **문서**: 01_extraction_pipeline.md §7.2
- **문제**: API 레벨 실패(타임아웃, 서버 에러)에 대한 재처리 전략 부재
- **조치**: 실패 건 수집 → mini-batch 재제출 → 2회 실패 시 dead-letter
- **상세**: 04_review_under_engineering.md §4

### S3. 04.graphrag Core v2 관계명 v19 기준 업데이트

- **문서**: 04.graphrag/results/implement_planning/core/2/ 전체
- **문제**: HAD_ROLE → PERFORMED_ROLE, AT_COMPANY → OCCURRED_AT 미반영
- **조치**: Core v2 문서의 Graph 스키마 + 코드 예시 일괄 업데이트
- **시점**: Phase 1 시작 전 (Week 1~2)

---

## 4. Could — 향후 검토

### C1. 비용 추정을 범위(range)로 표현

- **문서**: 01_extraction_pipeline.md §8
- **문제**: PoC 미실시 상태에서 구체적 금액은 거짓 정밀도
- **조치**: "$496" → "$400~$600" 형태로 변환
- **상세**: 03_review_over_engineering.md §3

### C2. 교차 참조 테이블 추가 (파이프라인 ↔ Phase)

- **문서**: 01_extraction_pipeline.md §1.3
- **문제**: "04.graphrag의 Phase별 일정과 상세 Task를 참조할 것"만으로는 불충분
- **조치**: 파이프라인(A/B/B'/C) ↔ Core v2 Phase(1/2/3) ↔ 주차(Week) 매핑 테이블 추가
- **예시**:
  ```
  | 파이프라인 | Core v2 Phase | 주차 | 주요 산출물 |
  |-----------|-------------|------|-----------|
  | B | Phase 1 | Week 2-6 | CandidateContext JSON (DB) |
  | B' | Phase 2 | Week 8-14 | CandidateContext JSON (파일) |
  | A | Phase 3 | Week 17-22 | CompanyContext JSON |
  | C | Phase 1-3 각각 | 각 Phase 후반 | Neo4j Graph |
  ```

### C3. 패턴 분리 실패 시 confidence 0.30 → 0.20 하향

- **문서**: 01_extraction_pipeline.md §4.1.2
- **문제**: 전체 텍스트를 단일 Career로 처리하면 scope_type이 사실상 무의미
- **조치**: confidence 상한을 0.30 → 0.20으로 하향 검토
- **상세**: 01_review_validity.md §2.3

---

## 5. v12 → v13 필요성 판단

### 결론: v13은 불필요. Must 2건은 문서 내 소규모 보강으로 해소 가능.

| 판단 기준 | v12 상태 |
|----------|---------|
| Must 건수 | 2건 (경미한 보강) |
| 구조 변경 필요 | 없음 |
| 신규 문서 필요 | 없음 |
| Phase 0 진입 가능 여부 | **가능** — Must 2건은 Phase 0 중 해소 가능 |

**권고**: v12를 최종 버전으로 확정하고, Must 2건(M1: N+1 컨텍스트, M2: ID 통일)은 Phase 0 시작 시 인라인 보강. **별도 v13 버전은 불필요**.

---

## 6. Phase 0 PoC 검증 항목 체크리스트 (v12 기준)

Phase 0에서 v12의 핵심 가정을 검증해야 하는 항목:

```
=== 비용/아키텍처 결정 ===
[ ] Haiku scope_type 정확도 ≥ 70% (20건) → 미달 시 Sonnet 전환
[ ] text-embedding-005 한국어 분별력 → 미달 시 Cohere 전환
[ ] Career 수 분포 (DB 프로파일링) → 3/4 분기점 조정
[ ] workDetails null 비율 → 20% 초과 시 비용/커버리지 재계산
[ ] Batch API 동시 batch 수 → ≤4 시 Gemini Flash 병행

=== 품질 결정 ===
[ ] 1-pass vs N+1 pass 품질 비교 (Career 4+ 이력서 5건) → 전략 확정
[ ] 파일 섹션 분리 패턴 성공률 (파일 이력서 10건) → 70% 미달 시 LLM 비율 조정
[ ] JSON 파싱 성공률 ≥ 95% → 미달 시 프롬프트 수정

=== 인프라 결정 ===
[ ] Neo4j AuraDB Free APOC 지원 여부 → 마이그레이션 방법 결정
[ ] Neo4j connection pool 한도 → kg-graph-load tasks 수 결정
```

---

## 7. v11 → v12 조치 현황 (최종)

```
=== Must (구현 전) ===
[x] M1. LLM 호출 전략 확정 → v12 해소 (적응형 1-pass/N+1)
[△] M2. 04.graphrag v2 관계명 통일 → v12에서 canonical 안내 강화, 실제 수정은 미완 (→ v12 S3)
[x] M3. 구현 순서 안내 → v12 해소

=== Should ===
[x] S1. 파일 섹션 분리 전략 → v12 해소 (Hybrid 패턴+LLM)
[x] S2. PII 매핑 저장소 구체화 → v12 해소 (GCS CMEK)
[x] S3. compute_skill_overlap 이동 → v12 해소 (삭제)
[x] S4. 전화번호 정규식 확장 → v12 해소 (8종 변형)
[x] S5. v1 INACTIVE 필드 프롬프트 제외 → v12 해소

=== Could ===
[ ] C1. Few-shot 예시 확장 → Phase 0 PoC 후
[x] C3. operating_model 진정성 체크 단순화 → v12 해소
[ ] C2. 파일 이력서 품질 등급 → 향후
[ ] C4. DB 스키마 실제 매핑 반영 → Phase 0 후

=== v12 신규 ===
[ ] M1(v12). N+1 pass 컨텍스트 보강 → Phase 0 인라인 보강
[ ] M2(v12). person_id vs candidate_id 통일 → Phase 1 전
[ ] S1(v12). chapters 순서 보장 → Phase 1 중
[ ] S2(v12). Batch API 부분 재처리 → Phase 1 중
[ ] S3(v12). Core v2 관계명 업데이트 → Phase 1 전
```
