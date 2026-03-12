# v4 계획 리뷰

> v4 계획 5개 문서를 종합 평가한다.
> v3 리뷰(create-kg/reviews/v3/01_v3_comprehensive_review.md)에서 지적한 사항의 반영 여부를 확인하고,
> v4에서 새로 발생한 이슈를 분석한다.
>
> 리뷰일: 2026-03-08

---

## 종합 평가 요약

| 항목 | v3 평가 | v4 평가 | 변화 |
|---|---|---|---|
| **v4 온톨로지 정합** | 우수 | 우수 (유지) | — |
| **설계 수준** | 우수 | **우수 (보강)** | Entity Resolution, 적재 전략, evidence 검증, Shortlisting 추가 |
| **실행 가능성** | 우수 | **우수 (보강)** | PoC 범위 확장, Phase 1-4 기간 현실화 |
| **비용 추정** | 우수 | **우수 (정밀화)** | 프롬프트 최적화 비용 현실화, embedding 평가 비용 추가 |
| **리스크 관리** | 우수 (보강) | **우수 (확장)** | PII 마스킹 영향, embedding 분별력 리스크 추가 |
| **운영 관점** | 양호 | **우수** | 프롬프트 버전 관리 체계 신설 |

---

## 1. v3 리뷰 지적 사항 반영 여부

### 1.1 Critical 사항

| 지적 | 반영 여부 | 위치 | 평가 |
|---|---|---|---|
| Candidate Shortlisting 전략 미정의 | **반영됨** | 02 §5.0 | 2단계 필터(Rule pre-filter → ANN) + 인프라(Neo4j Vector Index) + 범위 결정 명시 |

### 1.2 High 사항

| 지적 | 반영 여부 | 위치 | 평가 |
|---|---|---|---|
| Neo4j 초기 vs 증분 적재 전략 | **반영됨** | 02 §4.4 | LOAD CSV + APOC batch(초기) vs Cypher MERGE(증분) 분리, 시간 추정 포함 |
| Phase 0 PoC 범위 확장 | **반영됨** | 04 Phase 0-2 | PII 마스킹 영향(10건) + embedding 비교(20쌍) + 호출 전략(10건) 3개 실험 추가 |
| Embedding 모델 한국어 검증 | **반영됨** | 04 Phase 0-2, 05 §2.14 | PoC 실험 + 리스크 항목 + 가정 A16 모두 반영 |

### 1.3 Medium 사항

| 지적 | 반영 여부 | 위치 | 평가 |
|---|---|---|---|
| Organization MERGE 전략 통일 | **반영됨** | 02 §4.2, §4.3 | org_id canonical key + resolve_org_id() + 정규화 사전 + fallback 전략 |
| evidence_span 후처리 검증 | **반영됨** | 02 §8.2 | validate_evidence_spans() 함수 + confidence 감쇄 정책 |
| 프롬프트 버전 관리 전략 | **반영됨** | 04 운영 전략 | Git 관리 + Golden Set 회귀 테스트 + 변경 절차 |
| Gold set 분석 범위 명시 | **미반영** | — | 400건 기준 가능/불가능 분석 범위 미기술. 다만 실질적 영향 미미 |
| ML Distillation ROI 재정의 | **미반영** | — | 여전히 "선택적"으로만 표기. 구체적 투자 트리거 미명시 |

### 1.4 Low 사항

| 지적 | 반영 여부 | 위치 | 평가 |
|---|---|---|---|
| operating_model LLM 보정 제거 | **미반영** | — | v3 그대로 유지. 현재 수준으로 충분 |
| NEEDS_SIGNAL 엣지 용도 명확화 | **미반영** | — | v3 그대로 유지. 현재 수준으로 충분 |
| LLM 호출 최적화 (1회 통합) | **부분 반영** | 04 Phase 0-2 | PoC 비교 실험으로 추가. 설계 반영은 Phase 0 결과 후 |

---

## 2. v4에서 잘 개선된 부분

### 2.1 Organization Entity Resolution의 구체성

02 §4.3의 `resolve_org_id()` 함수가 3단계 매칭(사전 → NICE fuzzy → fallback)을 명확히 정의했다. v3에서 "Entity Resolution (Skill, Role, Organization 정규화)"로 뭉뚱그려 있던 것을 구체적 구현 수준으로 끌어올렸다.

### 2.2 Embedding 텍스트의 명시적 정의

02 §4.5에서 `build_chapter_embedding_text()`와 `build_vacancy_embedding_text()` 함수로 embedding 대상 텍스트를 명확히 정의한 것은 v3에서 누락된 중요한 설계 결정이었다.

### 2.3 Phase 0 PoC의 실험 설계

04 Phase 0-2에 추가된 3개 실험(PII 마스킹 영향, embedding 비교, 호출 전략)은 Phase 0의 의사결정 품질을 크게 높인다. 특히 PII 마스킹 전후 비교는 아키텍처 전체를 좌우하는 Critical 의사결정의 근거가 된다.

### 2.4 evidence_span 검증의 실용성

02 §8.2의 검증 로직은 단순하지만 효과적이다. 문자열 포함 검사만으로 LLM hallucination을 상당 부분 걸러낼 수 있으며, confidence 50% 감쇄는 합리적인 패널티이다.

---

## 3. v4에서 남아 있는 이슈

### 3.1 [Low] Gold set 분석 범위 미명시

v3 리뷰에서 "400건으로 가능한 분석 범위를 명시적으로 제한"을 권장했으나 미반영. 다만 400건은 전체 정확도 추정에 충분하며, 세부 분석이 필요하면 Phase 2 결과 후 확대하면 되므로 **실질적 문제 아님**.

### 3.2 [Low] ML Distillation 투자 트리거 미명시

여전히 "선택적, Phase 2 품질 평가 결과에 따라 진행 여부 결정"으로만 기술. 구체적 조건(예: "scope_type LLM 정확도 < 70% AND 월 재처리 > 1회")이 없다. 다만 이는 Phase 2 결과를 보고 판단하는 것이 합리적이므로 **현재 수준으로 충분**.

### 3.3 [Low] ~~05 문서에서 프롬프트 관리 리스크 미추가~~ → **수정 완료**

05 헤더에서 "프롬프트 관리 리스크 추가" 문구를 제거하여 실제 내용과 일치시켰다. 04 문서에 프롬프트 버전 관리 전략이 충분히 기술되어 있어 별도 리스크 섹션 불필요.

### 3.4 [Low] ~~타임라인 1주 증가의 비용 영향 미반영~~ → **수정 완료**

03의 엔지니어 인건비 참고 기간을 "16~19주"로, 인건비 범위를 "$40,000~$75,000"로 업데이트했다.

---

## 4. 문서별 평가

### 4.1 `01_v1_gap_analysis.md` — 우수

v3와 동일한 높은 완성도. §5.6에 v4 변경 사항 목록이 정확한 cross-reference와 함께 추가되었다.

### 4.2 `02_extraction_pipeline.md` — 우수 (v3 대비 주요 개선)

**개선된 부분**:
- §4.3: Organization Entity Resolution — v3의 핵심 설계 결함 해결
- §4.4: 초기/증분 적재 전략 분리 — 대량 처리 실현 가능성 확보
- §4.5: Embedding 텍스트 정의 — 모호함 제거
- §5.0: Candidate Shortlisting — Pipeline D의 전제 조건 해결
- §8.2: evidence_span 검증 — hallucination 방지

**잔존 이슈**: 없음

### 4.3 `03_model_candidates_and_costs.md` — 우수

**개선된 부분**:
- 프롬프트 최적화 비용 현실화 ($200 → $600)
- Embedding 모델 평가 비용 추가 ($50)
- A16 가정 추가

**잔존 이슈**: 타임라인 참고 기간 미업데이트 (Low)

### 4.4 `04_execution_plan.md` — 우수 (v3 대비 주요 개선)

**개선된 부분**:
- Phase 0-2: PoC 실험 3개 추가 (PII, embedding, 호출 전략)
- Phase 1-4: 2주로 확장 + Entity Resolution + 벤치마크 구체화
- Phase 1-5: Candidate Shortlisting 추가
- 운영 전략: 프롬프트 버전 관리 체계 신설
- 의사결정 포인트: Embedding 모델, LLM 호출 전략 추가

**잔존 이슈**: 없음

### 4.5 `05_assumptions_and_risks.md` — 우수

**개선된 부분**:
- A16: Embedding 모델 한국어 분별력 가정
- §2.13: PII 마스킹 영향 리스크
- §2.14: Embedding 한국어 분별력 리스크

**잔존 이슈**: 프롬프트 관리 리스크 섹션 부재 (Low, 헤더와 불일치)

---

## 5. 최종 판정

> v4 계획은 v3의 **핵심 부족 사항 7개(Critical 1, High 3, Medium 3)를 체계적으로 보강**했다.
> 특히 Candidate Shortlisting, Organization Entity Resolution, evidence_span 검증,
> Phase 0 PoC 범위 확장은 계획의 **실현 가능성과 데이터 무결성**을 크게 높였다.
>
> 남아 있는 이슈는 모두 Low 수준으로, 계획 실행에 지장이 없다.

### 전체 완성도: 우수

v4 계획은 **즉시 실행 가능한 수준**이다. v3 대비 추가된 1주(Phase 1-4)는 Entity Resolution과 적재 벤치마크를 위한 합리적 투자이며, Phase 0 PoC의 확장된 범위는 주요 의사결정의 근거를 강화한다.

### v3 → v4 개선 효과 요약

| 영역 | v3 상태 | v4 개선 |
|---|---|---|
| Candidate Shortlisting | 미정의 (Critical) | 2단계 필터 + 인프라 + 범위 정의 |
| Organization MERGE | 불일치 (Medium) | org_id 통일 + Entity Resolution 모듈 |
| Graph 대량 적재 | Cypher MERGE만 | LOAD CSV/APOC(초기) + MERGE(증분) 분리 |
| Embedding 텍스트 | 미정의 | build_*_embedding_text() 함수 정의 |
| evidence_span 검증 | 없음 | 후처리 검증 + confidence 감쇄 |
| Phase 0 PoC | LLM 추출만 | +PII 영향 +embedding 비교 +호출 전략 |
| 프롬프트 관리 | 언급만 | Git 관리 + Golden Set 회귀 테스트 체계 |
| 비용 추정 | $9,005 | $9,255 (프롬프트/embedding 비용 현실화) |
| 타임라인 | 14~18주 | 16~19주 (Phase 1-4 2주 확장) |

### 추가 개선이 필요한 경우

v4 이후 추가 버전(v5)이 필요하지는 **않다**. 남아 있는 Low 이슈 4개는 모두 실행 과정에서 자연스럽게 해결되는 수준이다. **Phase 0 PoC 결과**에 따라 세부 설계를 조정하는 것이 다음 단계로 적절하다.
