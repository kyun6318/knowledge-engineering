# v11 Extraction Logic 리뷰 요약

> 리뷰일: 2026-03-11 | 리뷰어: Claude Opus 4.6
> 대상: 02.knowledge_graph/results/extraction_logic/v11/ (6개 문서)
> 참조: 04.graphrag/results/implement_planning/core/2/ (GraphRAG Core v2)
> 비교 기준: v10 리뷰 (02.knowledge_graph/llm_log/reviews/v10/)

---

## 1. 총평

v11은 v10 리뷰의 **가장 큰 문제였던 "문서 정체성 혼란"을 성공적으로 해소**했다. Pipeline D/E를 04.graphrag로 이관하고, 실행 계획/인프라/서빙 API를 참조로 전환하여 **추출 로직 본연의 역할에 집중**하는 문서로 재탄생했다.

동시에 v10에서 **Critical로 지적된 LLM 프롬프트 설계 부재**를 03_prompt_design.md로 보강하고, **PII 마스킹 전략**과 **파이프라인 검증 체크포인트**를 신규 추가하여 구현 디테일을 대폭 강화했다.

다만, 일부 영역에서 **04.graphrag와의 경계가 여전히 모호**하거나, **실제 구현 시 부딪힐 현실적 제약**에 대한 고려가 부족한 부분이 남아 있다.

---

## 2. v10 대비 개선도

| v10 지적 사항 | 심각도 | v11 해소 여부 | 비고 |
|--------------|--------|-------------|------|
| 문서 정체성 혼란 (GraphRAG v2와 80% 중복) | Critical | **해소** | Pipeline A/B/B'/C로 범위 한정 |
| LLM 프롬프트 설계 전무 | Critical | **해소** | 03_prompt_design.md 신규 |
| Pydantic 스키마 부재 | Critical | **해소** | 03_prompt_design.md에 포함 |
| PII 마스킹 전략 부재 | High | **해소** | 04_pii_and_validation.md 신규 |
| 파이프라인 내 검증 부재 | Low→Medium | **해소** | CP1~CP6 체크포인트 |
| Embedding 비용 불일치 ($37.5 vs $25.5) | Medium | **해소** | $25.5로 통일 |
| 증분 처리 상세 미비 | Medium | **해소** | 변경 감지 + 공유 노드 보호 |
| 매칭 함수 미정의 | High | **부분 해소** | 매핑 테이블 추가, 함수 자체는 04.graphrag 위임 |

---

## 3. 점수 요약

| 평가 항목 | v10 | v11 | 변화 | 비고 |
|----------|-----|-----|------|------|
| 기술적 타당성 | 8/10 | **8/10** | = | 기존 강점 유지 |
| 온톨로지 v19 정합성 | 9/10 | **9/10** | = | v19 기준 충실 |
| 실현 가능성 (일정) | 6/10 | **7/10** | +1 | 범위 축소로 현실성 향상 |
| 실현 가능성 (비용) | 7/10 | **8/10** | +1 | 추출 범위 비용만 관리, 명확 |
| 문서 정체성/범위 | 4/10 | **8/10** | +4 | 가장 큰 개선 |
| 구현 디테일 | 5/10 | **8/10** | +3 | 프롬프트+검증+PII 보강 |
| GraphRAG v2 정합성 | 8/10 | **8/10** | = | 관계명 불일치 잔존 |

**종합: v10 6.7/10 → v11 8.0/10**

---

## 4. 핵심 판정

### 잘한 점 (Strengths)

1. **범위 재정의 성공**: 추출 로직(A/B/B'/C) 집중 + 나머지 04.graphrag 참조
2. **프롬프트 설계 충실**: Taxonomy Enforcement, Evidence Span, Few-shot 등 실전적
3. **검증 체크포인트 6단계**: 입력→마스킹→LLM→정규화→적재→임베딩 전 구간 커버
4. **증분 처리 공유 노드 보호**: DETACH DELETE 시 공유/비공유 노드 분류 적절
5. **매칭 필드 매핑 테이블**: 추출과 매칭의 인터페이스 계약 명시

### 남은 과제 (Areas for Improvement)

1. **GraphRAG v2와 관계명 불일치** 잔존 (HAD_ROLE vs PERFORMED_ROLE 등)
2. **Career별 LLM 호출 vs 이력서 전체 LLM 호출 전략** 미확정
3. **실제 resume-hub DB 스키마와의 정합성** 미검증
4. **한국어 LLM 추출 품질**에 대한 과도한 낙관 (Haiku 70% 가정)
5. **파일 이력서 섹션 분리 로직** 구체성 부족

---

## 5. 리뷰 문서 목록

| 파일 | 내용 |
|------|------|
| 00_review_summary.md | 본 요약 |
| 01_review_validity.md | 타당성 리뷰 (기술 선택, 프롬프트 설계, 검증 전략) |
| 02_review_feasibility.md | 실현 가능성 리뷰 (비용, 전제 조건, 04.graphrag 정합) |
| 03_review_over_engineering.md | 과도한 설계 (범위 초과, 불필요한 복잡성) |
| 04_review_under_engineering.md | 부족한 설계 (누락된 핵심 사항) |
| 05_review_action_items.md | 조치 사항 및 권고 |
