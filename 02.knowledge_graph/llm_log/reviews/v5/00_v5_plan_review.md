# v5 계획 리뷰

> v5 계획 5개 문서를 종합 평가한다.
> v4 리뷰(create-kg/reviews/v4/01_v4_comprehensive_review.md)에서 지적한 사항의 반영 여부를 확인하고,
> v5에서 새로 발생한 이슈를 분석한다.
>
> 리뷰일: 2026-03-08

---

## 종합 평가 요약

| 항목 | v4 평가 | v5 평가 | 변화 |
|---|---|---|---|
| **v4 온톨로지 정합** | 우수 | 우수 (유지) | — |
| **설계 수준** | 우수 (보강) | **우수 (보강)** | Idempotency, Deterministic ID, 중복 처리 추가 |
| **실행 가능성** | 우수 (보강) | **우수 (보강)** | 파싱 PoC 확장, 법무 기본값 전략 |
| **비용 추정** | 우수 (정밀화) | 우수 (유지) | 비용 변경 없음 (v4와 동일) |
| **리스크 관리** | 우수 (확장) | **우수 (확장)** | 이력서 중복 리스크, 파싱 커버리지 리스크 추가 |
| **운영 관점** | 우수 | **우수 (강화)** | Deterministic MERGE로 재처리 안정성 향상 |

---

## 1. v4 리뷰 지적 사항 반영 여부

### 1.1 High 사항

| 지적 | 반영 여부 | 위치 | 평가 |
|---|---|---|---|
| Graph 적재 Idempotency 미보장 | **반영됨** | 02 §4.1, §4.2, §4.6 | Vacancy/Outcome/Chapter 모두 deterministic ID + MERGE로 전환 |
| 이력서 중복 처리 전략 부재 | **반영됨** | 02 §3.4, 04 Phase 0-1, 2-1 | 동일 candidate_id 최신 선택 + SimHash 검토 큐 |
| Chapter/Outcome ID 생성 전략 미정의 | **반영됨** | 02 §4.6 | `generate_chapter_id()`, `generate_outcome_id()` 함수 + ID 원칙 정의 |
| 이력서 섹션 분할 커버리지 미실측 | **반영됨** | 04 Phase 0-2 | 파싱 → 섹션 분할 → 블록 분리 3단계 성공률 측정 + 판정 기준 |

### 1.2 Medium 사항

| 지적 | 반영 여부 | 위치 | 평가 |
|---|---|---|---|
| Phase 0 법무 의사결정 기본값 | **반영됨** | 04 Phase 0-3 | 마스킹 기반 API 기본값 + 법무 확정 시 전환 |
| evidence_span 검증 정규화 | **반영됨** | 02 §8.2 | `normalize_text()` + normalized match로 개선 |
| JD 갱신 cascade 처리 | **미반영** | — | 선택 항목. 운영 단계에서 자연스럽게 보완 가능 |
| Confidence aggregation 전략 | **미반영** | — | 선택 항목. Phase 2 품질 평가에서 검토 |
| domain_fit embedding 정의 | **미반영** | — | 선택 항목. 실질적 영향 미미 |
| BigQuery 서빙 쿼리 패턴 | **미반영** | — | 선택 항목. Phase 2-4에서 정의 예정 |

---

## 2. v5에서 잘 개선된 부분

### 2.1 Deterministic ID + MERGE 패턴의 체계성

02 §4.6의 ID 생성 전략은 모든 노드 타입에 대해 일관된 규칙을 제시한다:
- Person: `candidate_id` (시스템 ID)
- Chapter: `hash(candidate_id + company + period_start)`
- Vacancy: `job_id` (시스템 ID)
- Outcome: `hash(chapter_id + index)`
- Skill/Role/Signal: `name`/`label` 기반 MERGE

이 설계는 **초기 적재, 증분 적재, 재처리 세 시나리오 모두**에서 Graph 데이터 일관성을 보장한다.

### 2.2 법무 의사결정 기본값의 실용성

04 Phase 0-3의 기본값 전략("법무 미확정 시 마스킹 기반 API로 진행")은:
- Phase 1 블로킹을 방지하면서
- 법무 결론 확정 시 API endpoint만 변경하면 되는 **저비용 전환 경로**를 제공
- 이는 실무적으로 매우 실용적인 접근

### 2.3 파싱 PoC의 단계별 성공률 측정

04 Phase 0-2에 추가된 "파싱 → 섹션 분할 → 경력 블록 분리" 3단계 성공률 측정은:
- 05 §2.3의 파싱+LLM 상관 리스크를 **조기에 감지**하는 수단
- 판정 기준(< 50%이면 LLM fallback)과 비용 영향($250~500)까지 명시
- Phase 1-1에서의 일정 영향(0.5~1주)까지 사전 고지

### 2.4 evidence_span 정규화의 적절성

02 §8.2의 `normalize_text()` 함수는:
- 공백/줄바꿈/탭을 단일 공백으로 정규화하여 비교
- 구현이 단순하면서도 false negative를 효과적으로 감소시킴
- 비용 0 (문자열 정규화만)

---

## 3. v5에서 남아 있는 이슈

### 3.1 [Low] Outcome ID의 index 기반 생성 취약점

02 §4.6에서 `generate_outcome_id(chapter_id, outcome_index)`로 Outcome ID를 생성한다. 그러나 `outcome_index`는 LLM 추출 순서에 의존하므로:

- LLM이 동일 입력에서 outcome 순서를 다르게 출력하면 (temperature > 0일 때) 다른 ID가 생성됨
- 재처리 시 기존 Outcome과 다른 ID의 Outcome이 MERGE되지 않고 공존할 수 있음

**판정**: 실무적으로 Batch API(temperature=0 기본)에서는 출력 순서가 일관적이므로 **현재 수준으로 충분**. 만약 순서 변동이 관측되면 `hash(chapter_id + normalize_text(outcome_description))` 으로 전환 가능 (description도 LLM 출력이므로 정규화 필요).

### 3.2 [Low] 선택 항목 4개 미반영

v4 리뷰에서 "선택"으로 분류한 JD 갱신 cascade, Confidence aggregation, domain_fit embedding, BigQuery 쿼리 패턴이 미반영되었다. 이들은 모두 Phase 2~3에서 자연스럽게 보완 가능하므로 **현재 수준으로 충분**.

### 3.3 [Low] 03 문서의 비용 미변경

v5에서 이력서 중복 제거가 추가되었으므로 처리 대상 이력서 수가 줄어들 수 있다. 그러나 중복률이 5~10%라면 비용 절감도 5~10%(~$30~60)에 불과하므로 **비용 수정 불필요**.

---

## 4. 문서별 평가

### 4.1 `01_v1_gap_analysis.md` — 우수

§5.7에 v5 변경 사항 6개가 정확한 cross-reference와 함께 추가되었다.

### 4.2 `02_extraction_pipeline.md` — 우수 (v4 대비 주요 개선)

**개선된 부분**:
- §0: 설계 원칙에 "Idempotency" 추가
- §3.4: 이력서 중복 처리 전략 — 동일 candidate_id 최신 선택 + SimHash
- §4.1, §4.2: Vacancy/Chapter/Outcome 모두 MERGE로 전환 + deterministic ID 사용
- §4.5: 빈 embedding 텍스트 skip 로직
- §4.6: Deterministic ID 생성 전략 — 전체 노드 타입 ID 규칙 정의
- §8.2: evidence_span 검증 normalized match 도입
- §8.4: 배치 처리에 중복 제거 단계 추가

**잔존 이슈**: Outcome ID의 index 기반 생성 취약점 (Low)

### 4.3 `03_model_candidates_and_costs.md` — 우수

v4와 동일. 비용 변경 불필요.

### 4.4 `04_execution_plan.md` — 우수 (v4 대비 주요 개선)

**개선된 부분**:
- Phase 0-1: 중복률 측정 체크리스트 추가
- Phase 0-2: 파싱 → 섹션 분할 → 블록 분리 3단계 성공률 측정 + 판정 기준
- Phase 0-3: 법무 의사결정 기본값 전략 (마스킹 API 기본값)
- Phase 0-4: 의사결정 포인트에 "섹션 분할 전략", "이력서 중복 처리" 추가
- Phase 1-1: 중복 제거 모듈 + LLM 섹션 분할 fallback
- Phase 1-4: Deterministic ID 모듈 + Idempotency 테스트
- 운영 전략: MERGE 기반 재처리 (DELETE 불필요)
- 테스트 전략: Idempotency 테스트 레벨 추가

**잔존 이슈**: 없음

### 4.5 `05_assumptions_and_risks.md` — 우수

**개선된 부분**:
- A17: 이력서 중복률 가정 추가
- §2.15: 이력서 중복 리스크 추가
- §2.1: 법무 기본값 전략 cross-reference
- §2.3: 파싱 단계별 성공률 측정 cross-reference
- §2.8: Deterministic ID + MERGE 패턴 cross-reference

**잔존 이슈**: 없음

---

## 5. v4 → v5 개선 효과 요약

| 영역 | v4 상태 | v5 개선 |
|---|---|---|
| Graph Idempotency | Vacancy/Outcome CREATE (비멱등) | 전체 노드 deterministic MERGE (멱등) |
| 이력서 중복 | 중복률 측정만 (처리 전략 없음) | 중복 감지 + canonical 선택 + 처리 플로우 |
| 노드 ID 생성 | 미정의 | 전체 노드 타입 ID 규칙 + hash 함수 |
| evidence_span 검증 | strict match (false negative 높음) | normalized match (false negative 감소) |
| 파싱 PoC | LLM 추출 품질만 측정 | 파싱 단계별 성공률 + LLM fallback 판정 |
| 법무 의사결정 | 법무 결론 대기 (블로킹 위험) | 기본값 전략으로 블로킹 방지 |
| 재처리 안정성 | DELETE + 재생성 필요 | MERGE로 자동 upsert (DELETE 불필요) |

---

## 6. 최종 판정

> v5 계획은 v4의 **Graph 데이터 무결성 관련 이슈 4개(High)와 운영 안정성 이슈 2개(Medium)를 체계적으로 보강**했다.
> 특히 Deterministic ID + MERGE 패턴은 초기 적재, 증분 적재, 재처리 세 시나리오 모두의 안정성을 높이는 핵심 개선이다.
>
> 남아 있는 이슈는 모두 Low 수준으로, 계획 실행에 지장이 없다.

### 전체 완성도: 우수

v5 계획은 **즉시 실행 가능한 수준**이다. v4 대비 추가된 작업(파싱 PoC, 중복 제거, Idempotency 테스트)은 기존 Phase 기간 내 흡수 가능하므로 타임라인 변경이 없다.

### 추가 개선이 필요한 경우

v5 이후 추가 버전(v6)이 필요하지는 **않다**. 남아 있는 이슈는 모두 Low 수준이며, 실행 과정에서 자연스럽게 해결된다. **Phase 0 PoC 결과**에 따라 세부 설계를 조정하는 것이 다음 단계로 적절하다.
