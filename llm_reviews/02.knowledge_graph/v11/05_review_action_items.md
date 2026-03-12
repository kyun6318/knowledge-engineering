# v11 조치 사항 및 권고

> 대상: 02.knowledge_graph/results/extraction_logic/v11/
> 우선순위: Must (구현 전 필수) > Should (v12에서 보강) > Could (향후 개선)

---

## 1. Must — 구현 전 반드시 해소

### M1. Career별 vs 전체 이력 LLM 호출 전략 확정 (U1)

**문제**: CandidateContext 추출에서 Career별 추출과 전체 이력 추출의 호출 구조가 미확정.

**조치**:
- 03_prompt_design.md §2에 호출 전략 섹션 추가
- 추천 전략:
  ```
  Career 1~3: 단일 호출 (전체 이력서 → chapters[] + role_evolution + domain_depth)
  Career 4+: Career별 개별 호출 → 마지막에 전체 요약 1회
  max_tokens: Career 1~3 → 2,048 / Career 4+ → 1,024 per career + 512 for summary
  ```
- Phase 0 PoC 20건에서 이 분기의 비용/품질 차이 실측

**영향**: 비용 2~3배 차이 가능. Phase 1 시작 전 확정 필수.

### M2. 04.graphrag v2 관계명 통일 (타당성 §5.2)

**문제**: v11(v19 canonical)은 PERFORMED_ROLE/OCCURRED_AT, 04.graphrag v2는 HAD_ROLE/AT_COMPANY 사용.

**조치**:
- **04.graphrag v2 측에서 관계명을 v19 canonical로 업데이트**
- 또는 v11에 "구현 시 04.graphrag가 사용하는 관계명을 따르되, v19 canonical을 목표로 한다" 과도기 안내
- 어느 쪽이든 **단일 canonical 소스** 확정

**영향**: 개발자가 코드 작성 시 어떤 관계명을 쓸지 혼란. Phase 1 시작 전 해소 필수.

### M3. v11에 구현 순서 안내 추가 (실현가능성 §3.3)

**문제**: v11이 A→B→B'→C 순서로 기술하지만, 실제 구현은 B(Phase 1) → B'(Phase 2) → A(Phase 3).

**조치**: 01_extraction_pipeline.md §1.3에 다음 추가:
```
> **구현 순서**: 본 문서는 논리적 순서(A→B→B'→C)로 기술되어 있으나,
> 실제 구현 순서는 04.graphrag 실행 계획을 따른다:
> Phase 1: B (CandidateContext DB) → C
> Phase 2: B' (CandidateContext 파일) → C
> Phase 3: A (CompanyContext) → C
```

---

## 2. Should — v12에서 보강 권고

### S1. 파일 이력서 섹션 분리 전략 (U2)

**문제**: Pipeline B'의 "섹션 분리 → Career 블록 추출" 구체적 방법 미기술.

**조치**: 01_extraction_pipeline.md §4 또는 별도 문서에 추가:
- 접근법 A: **패턴 기반 섹션 분리** (정규식으로 "경력사항" 등 헤더 탐지 → 회사명+날짜 패턴으로 Career 구분)
- 접근법 B: **LLM 기반 섹션 분리** (전체 텍스트를 LLM에 전달, "Career 블록별로 JSON 구분하라" 지시 — 비용 증가)
- 접근법 C: **Hybrid** (Document AI Layout Parser로 구조 파악 → 패턴 기반 분리 → 실패 시 LLM 폴백)
- Phase 2-0 파일 파싱 PoC에서 3가지 접근법 비교 검증

**시기**: Phase 2 시작 전 (Week 7 이전)

### S2. PII 매핑 테이블 저장소 구체화 (U4)

**문제**: 500K+ PII 매핑의 저장소가 "별도 보안 저장소"로만 언급.

**조치**: 04_pii_and_validation.md §1.3에 구체적 저장소 선택 추가:
- **추천**: GCS 암호화 파일 (CMEK) — 가장 단순, 접근 로그 자동
- **대안 1**: BigQuery 별도 데이터셋 + Column-level Security
- **대안 2**: CloudSQL (추가 비용 ~$30/월)

**시기**: Phase 1 시작 전 (Week 2 이전)

### S3. compute_skill_overlap 제거 또는 위치 변경 (O1)

**문제**: 매칭 로직이 추출 문서에 포함.

**조치**:
- 01_extraction_pipeline.md §5.4 삭제
- 04.graphrag Phase 3-0 매칭 설계 문서로 이동
- v11에는 §6 매칭 필드 매핑 테이블만 유지

### S4. 전화번호 정규식 확장 (U5)

**문제**: 010-\d{4}-\d{4} 하나로는 변형 패턴 미탐지.

**조치**: 04_pii_and_validation.md §1.4 정규식 업데이트:
```python
PHONE_PATTERNS = [
    r'(?:\+82[-\s]?)?0?1[016789][-.\s]?\d{3,4}[-.\s]?\d{4}',  # 휴대폰
    r'0[2-6][0-9]?[-.\s]?\d{3,4}[-.\s]?\d{4}',                # 일반전화
]
```

### S5. v1 불필요 필드 프롬프트 제외 (O2, O3)

**문제**: structural_tensions, work_style_signals가 v1 INACTIVE이면서 프롬프트에 포함.

**조치**:
- 03_prompt_design.md의 CompanyContextExtraction에서 structural_tensions 관련 필드 주석 처리
- CandidateContextExtraction에서 work_style_signals 주석 처리
- 해당 필드 제거로 토큰 ~300/호출 절약

---

## 3. Could — 향후 개선 사항

### C1. Few-shot 예시 확장

**현황**: CompanyContext 2개, CandidateContext 2개.
**권고**: 각 열거형 값(HiringContext 4개, ScopeType 4개)에 대해 최소 1개씩 확대. Phase 0 PoC 결과에서 우수 사례를 Few-shot으로 추가.

### C2. 파일 이력서 품질 등급 도입

**현황**: Pipeline B(DB)와 B'(파일)의 출력을 동일하게 취급.
**권고**: 파일 추출 결과에 `source_quality` 필드 추가 (DB_HIGH, FILE_STANDARD, FILE_LOW). 매칭 시 가중치 차등 적용.

### C3. operating_model "진정성 체크" 단순화 (O4)

**현황**: LLM이 광고성 문구를 판단하도록 요구.
**권고**: "키워드가 구체적 맥락(스프린트 주기, 리뷰 빈도 등) 없이 단독 사용 시 해당 facet null" 규칙으로 단순화.

### C4. DB 스키마 실제 매핑 반영 (U3)

**현황**: 가정 기반 필드명 사용.
**권고**: Phase 0 DB 프로파일링 후 실제 필드명으로 업데이트. 또는 면책 조항 추가.

---

## 4. 조치 사항 체크리스트

```
=== Must (구현 전) ===
□ M1. LLM 호출 전략 확정 (Career별 vs 전체)
□ M2. 04.graphrag v2 관계명 통일 (PERFORMED_ROLE vs HAD_ROLE)
□ M3. v11에 구현 순서 안내 추가

=== Should (v12) ===
□ S1. 파일 섹션 분리 전략 기술
□ S2. PII 매핑 테이블 저장소 구체화
□ S3. compute_skill_overlap 이동
□ S4. 전화번호 정규식 확장
□ S5. v1 INACTIVE 필드 프롬프트 제외

=== Could (향후) ===
□ C1. Few-shot 예시 확장
□ C2. 파일 이력서 품질 등급
□ C3. operating_model 진정성 체크 단순화
□ C4. DB 스키마 실제 매핑 반영
```

---

## 5. v10 조치 사항 해소 현황

| v10 조치 | 심각도 | v11 해소 | 비고 |
|---------|--------|---------|------|
| 문서 범위 재정의 | Critical | **해소** | A/B/B'/C 집중 |
| LLM 프롬프트 작성 | Critical | **해소** | 03_prompt_design.md |
| Pydantic 스키마 작성 | Critical | **해소** | 프롬프트 내 포함 |
| PII 전략 수립 | High | **해소** | 04_pii_and_validation.md |
| 검증 체크포인트 추가 | Medium | **해소** | CP1~CP6 |
| Embedding 비용 통일 | Medium | **해소** | $25.5 통일 |
| 매칭 함수 정의 | High | **부분** | 매핑 테이블 추가, 함수 위임 |
| 관계명 통일 | Medium | **미해소** | 04.graphrag 측 업데이트 필요 |

**v10 조치 8건 중 6건 해소, 1건 부분 해소, 1건 미해소.**

---

## 6. 최종 평가

v11은 v10의 핵심 문제를 대부분 해소한 **양질의 개선 버전**이다.

**강점**:
- 문서 정체성 확립 (추출 로직 집중)
- 프롬프트 설계의 실전적 품질
- 검증 체크포인트의 체계적 설계
- 증분 처리의 공유 노드 보호

**최우선 과제**:
- Must 3건(LLM 호출 전략, 관계명 통일, 구현 순서 안내)을 Phase 0 이전에 해소
- Should 5건은 v12 또는 해당 Phase 시작 전까지 보강

**문서 성숙도**: 설계 문서로서 **구현 착수 가능한 수준(Implementation-Ready)**에 근접. Must 3건 해소 시 "Implementation-Ready" 판정.
