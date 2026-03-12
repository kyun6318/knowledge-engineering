# v12 Extraction Logic 리뷰 요약

> 리뷰일: 2026-03-11 | 리뷰어: Claude Opus 4.6
> 대상: 02.knowledge_graph/results/extraction_logic/v12/ (6개 문서)
> 참조: 04.graphrag/results/implement_planning/core/2/ (GraphRAG Core v2)
> 비교 기준: v11 리뷰 (02.knowledge_graph/llm_log/reviews/v11/)

---

## 1. 총평

v12는 v11 리뷰에서 도출된 **Must 3건, Should 5건, Could 1건** 중 **Must 3건 전량, Should 5건 전량, Could 1건**을 해소한 **정밀 보강 버전**이다. 문서 구조 변경 없이 실제 구현 착수에 필요한 세부 설계를 채운 점에서 **안정적이고 성숙한 진화**를 보여준다.

특히 M1(Career별 적응형 호출 전략), S1(파일 섹션 분리 Hybrid 전략), S2(PII 매핑 저장소 GCS CMEK)는 구현 단계에서 반드시 결정해야 할 사항들을 적절한 수준으로 확정했다.

다만, **"구현 착수 수준(Implementation-Ready)"이라는 자체 선언에 비해** 아직 04.graphrag Core v2와의 인터페이스 계약이 **코드 레벨이 아닌 문서 레벨**에 머물러 있고, 몇몇 설계 결정이 **Phase 0 PoC 결과에 과도하게 의존**하여 PoC 실패 시 설계 전체가 흔들릴 수 있는 위험이 있다.

---

## 2. v11 대비 개선도

| v11 리뷰 지적 사항 | 심각도 | v12 해소 여부 | 비고 |
|------------------|--------|-------------|------|
| Career별 vs 전체 이력 LLM 호출 전략 미확정 (M1) | High | **해소** | 1-pass/N+1 적응형 전략 확정 |
| 관계명 canonical 소스 불명확 (M2) | Medium | **부분 해소** | v19 canonical 명시했으나 04.graphrag 측 업데이트는 미완 |
| 구현 순서 안내 부재 (M3) | Medium | **해소** | 01_extraction_pipeline.md §1.3에 추가 |
| 파일 섹션 분리 전략 부재 (S1) | High | **해소** | Hybrid(패턴→LLM 폴백) 전략 상세 |
| PII 매핑 저장소 불명확 (S2) | Medium | **해소** | GCS CMEK + 대안 2개 제시 |
| compute_skill_overlap 위치 부적절 (S3) | Low | **해소** | 삭제 (04.graphrag 위임) |
| 전화번호 정규식 부족 (S4) | Low | **해소** | 8종 변형 커버 |
| v1 INACTIVE 필드 프롬프트 잔존 (S5) | Low | **해소** | structural_tensions, work_style_signals 제외 |
| operating_model 진정성 체크 비현실적 (C3) | Low | **해소** | 단순 confidence 규칙으로 대체 |

---

## 3. 점수 요약

| 평가 항목 | v11 | v12 | 변화 | 비고 |
|----------|-----|-----|------|------|
| 기술적 타당성 | 8/10 | **8.5/10** | +0.5 | 적응형 호출, Hybrid 파싱 합리적 |
| 온톨로지 v19 정합성 | 9/10 | **9/10** | = | v19 기준 충실 유지 |
| 실현 가능성 (일정) | 7/10 | **7/10** | = | 04.graphrag 위임 기조 유지 |
| 실현 가능성 (비용) | 8/10 | **8/10** | = | 비용 +25% 증가를 솔직히 기술 |
| 문서 정체성/범위 | 8/10 | **9/10** | +1 | 구현 순서 안내로 명확성 향상 |
| 구현 디테일 | 8/10 | **8.5/10** | +0.5 | 핵심 결정 사항 확정 |
| GraphRAG v2 정합성 | 8/10 | **8/10** | = | 관계명 canonical 안내 강화, 실제 반영은 미완 |

**종합: v11 8.0/10 → v12 8.3/10**

---

## 4. 핵심 판정

### 잘한 점 (Strengths)

1. **적응형 호출 전략 (M1)**: Career 수 기반 1-pass/N+1 분기는 비용과 품질의 합리적 타협점
2. **파일 섹션 분리 Hybrid (S1)**: 패턴 70% + LLM 폴백 30%는 한국 이력서 다양성을 현실적으로 인정
3. **operating_model 진정성 체크 단순화 (C3)**: 과도한 LLM 판단 요구를 구체적 맥락 유무 규칙으로 대체
4. **솔직한 비용 증가 기술**: +25% 비용 증가를 숨기지 않고 정확도 향상 목적과 함께 명시
5. **INACTIVE 필드 정리 (S5)**: Phase 5 복원 경로를 주석으로 남기면서 현재 프롬프트 간소화

### 남은 과제 (Areas for Improvement)

1. **04.graphrag 관계명 불일치 실질 미해소**: v19 canonical 안내만으로는 부족, 실제 수정 필요
2. **Phase 0 PoC 의존도 과다**: 핵심 설계 결정 5개 이상이 PoC 결과에 달려 있음
3. **파일 섹션 분리 성공률 70% 가정 근거 부재**: 실측 없는 추정치
4. **N+1 pass 프롬프트의 컨텍스트 단절 리스크**: Career별 개별 호출 시 이력서 전체 맥락 상실

---

## 5. 리뷰 문서 목록

| 파일 | 내용 |
|------|------|
| 00_review_summary.md | 본 요약 |
| 01_review_validity.md | 타당성 리뷰 (기술 선택, 적응형 호출, Hybrid 파싱, 검증 전략) |
| 02_review_feasibility.md | 실현 가능성 리뷰 (비용 영향, 전제 조건, 04.graphrag 정합) |
| 03_review_over_engineering.md | 과도한 설계 (범위 초과, 불필요한 복잡성) |
| 04_review_under_engineering.md | 부족한 설계 (누락된 핵심 사항) |
| 05_review_action_items.md | 조치 사항 및 권고 |
