# v11 → v12 변경 이력

> 작성일: 2026-03-11 | 리뷰 기반: v11 리뷰 (01_review_validity ~ 05_review_action_items)

---

## 1. 변경 동기

v11 리뷰에서 **Must 3건, Should 5건, Could 1건** 총 9건의 조치 사항이 도출됨.
v11은 v10의 핵심 문제(문서 정체성, 프롬프트 부재, PII 전략 부재)를 성공적으로 해소했으나,
**실제 구현 단계에서 필요한 세부 설계**가 일부 미비한 상태.

v12는 구현 착수(Implementation-Ready) 수준을 달성하기 위한 **정밀 보강 버전**.

---

## 2. 핵심 변경 사항

### 2.1 Must 해소 (구현 전 필수)

| ID | 변경 | 문서 | 비고 |
|----|------|------|------|
| M1 | **Career별 vs 전체 이력 LLM 호출 전략 확정** | 03_prompt_design.md §2.2 | Career 1~3: 1-pass / 4+: N+1 pass |
| M2 | **관계명 canonical 소스 명시** | 01_extraction_pipeline.md §5.1 | v19가 canonical, 04.graphrag 업데이트 의무 명시 |
| M3 | **구현 순서 안내 추가** | 01_extraction_pipeline.md §1.3 | 논리적 순서 vs 실제 구현 순서 구분 |

### 2.2 Should 해소

| ID | 변경 | 문서 | 비고 |
|----|------|------|------|
| S1 | **파일 이력서 섹션 분리 전략** | 01_extraction_pipeline.md §4.1 | Hybrid 전략 (패턴 → LLM 폴백) |
| S2 | **PII 매핑 테이블 저장소 구체화** | 04_pii_and_validation.md §1.3 | GCS CMEK 추천 + 대안 2개 |
| S3 | **compute_skill_overlap 제거** | 01_extraction_pipeline.md | §5.4 삭제, §6 매핑 테이블만 유지 |
| S4 | **전화번호 정규식 확장** | 04_pii_and_validation.md §1.4, §2.3 | 한국 변형 8종 커버 |
| S5 | **v1 INACTIVE 필드 프롬프트 제외** | 03_prompt_design.md §1.3, §2.3 | structural_tensions, work_style_signals 제거 |

### 2.3 Could 해소

| ID | 변경 | 문서 | 비고 |
|----|------|------|------|
| C3 | **operating_model 진정성 체크 단순화** | 03_prompt_design.md §1.5 | LLM 진정성 판단 → 단순 confidence 규칙 |

---

## 3. 문서 구조 (변경 없음)

v12는 v11과 동일한 6개 문서 구조 유지. 신규/삭제 문서 없음.

| 문서 | 변경 수준 |
|------|----------|
| 00_v11_to_v12_changelog.md | 신규 (본 문서) |
| 01_extraction_pipeline.md | **중간** (M3 + S1 + S3 + M2) |
| 02_model_and_infrastructure.md | **없음** |
| 03_prompt_design.md | **중간** (M1 + S5 + C3) |
| 04_pii_and_validation.md | **소규모** (S2 + S4) |
| 05_extraction_operations.md | **없음** |

---

## 4. v11 리뷰 조치 현황

```
=== Must (구현 전) ===
[x] M1. LLM 호출 전략 확정 (Career별 vs 전체) → v12 해소
[△] M2. 04.graphrag v2 관계명 통일 → v12에서 canonical 안내 강화, 04.graphrag 측 업데이트는 별도
[x] M3. v11에 구현 순서 안내 추가 → v12 해소

=== Should (v12) ===
[x] S1. 파일 섹션 분리 전략 기술 → v12 해소
[x] S2. PII 매핑 테이블 저장소 구체화 → v12 해소
[x] S3. compute_skill_overlap 이동 → v12 해소 (삭제)
[x] S4. 전화번호 정규식 확장 → v12 해소
[x] S5. v1 INACTIVE 필드 프롬프트 제외 → v12 해소

=== Could (향후) ===
[ ] C1. Few-shot 예시 확장 → Phase 0 PoC 후 반영
[x] C3. operating_model 진정성 체크 단순화 → v12 해소
[ ] C2. 파일 이력서 품질 등급 → 향후
[ ] C4. DB 스키마 실제 매핑 반영 → Phase 0 후
```
