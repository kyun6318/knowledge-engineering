# v12 부족한 설계 리뷰

> 리뷰일: 2026-03-11 | 리뷰어: Claude Opus 4.6
> 대상: 02.knowledge_graph/results/extraction_logic/v12/
> 기준: "구현 착수 수준(Implementation-Ready)"을 표방하면서 누락된 설계 요소

---

## 전체 평가

v12는 "구현 착수 수준"이라고 자체 선언했으나, **실제 코딩을 시작하면 부딪힐 4개의 미결 사항**이 존재한다. 이 중 2개는 **구현 전 결정 필수(Must)**, 2개는 **구현 중 결정 가능(Should)**이다.

v11 리뷰의 Must 3건이 모두 해소되었으므로 v12의 Must는 **신규 발견** 항목이다.

---

## 1. [Must] N+1 pass 컨텍스트 보강 전략 미정의

### 위치
03_prompt_design.md §2.2.2, 01_extraction_pipeline.md §3.4

### 문제
N+1 pass에서 Career별 개별 호출(Pass 1~N)은 해당 Career의 workDetails + CareerDescription만 입력한다. **전체 이력 맥락이 없으면** scope_type 판단이 부정확해질 수 있다.

### 구체적 시나리오

**Case 1: 스타트업 CTO → 대기업 팀장**
```
Career 1 (스타트업 CTO): workDetails에 "5인 팀 리드" 기술
  → 전체 맥락 없이 단독 판단: FOUNDER? LEAD?
  → 전체 맥락(다음 직장이 대기업 팀장): LEAD가 더 적절

Career 2 (대기업 팀장): workDetails에 "30명 부서 관리"
  → 전체 맥락 없이 단독 판단: HEAD
  → 정확 (독립적으로도 판단 가능)
```

**Case 2: 교차 참조 성과**
```
Career 1 (A사): "B사 프로젝트에서의 경험을 바탕으로 시스템 설계"
  → B사 정보가 없어 evidence span 불가
  → outcomes 누락 또는 부정확한 evidence
```

### 영향
- Career 4+ 이력서(전체의 ~20%)에서 scope_type 정확도 저하
- 교차 참조 outcomes 누락

### 권고
N+1 pass의 Pass 1~N 프롬프트에 **전체 Career 요약 컨텍스트**를 추가:

```
## 전체 경력 요약 (참고용 — 이 경력 외 다른 경력)
{career_summary_context}
(형식: "회사명 | 기간 | 직급코드", 분석 대상 Career 제외)
```

추가 토큰: ~200 토큰/호출
추가 비용: 100K × 평균 4.5회 × 200 토큰 × $0.0008/1K = ~$7.2 (Batch: ~$3.6) — 무시 가능

---

## 2. [Must] person_id vs candidate_id 통일

### 위치
01_extraction_pipeline.md §5 전체, 04.graphrag Core v2 §11

### 문제
v12는 **person_id**를 일관되게 사용:
```
MERGE (p:Person {person_id: row.person_id})
```

04.graphrag Core v2는 **candidate_id**를 사용:
```python
session.run("MERGE (p:Person {candidate_id: c.candidate_id})")
```

구현 시 어느 필드명을 사용할지 결정하지 않으면, Pipeline B 추출 결과와 Pipeline C 적재 코드가 **즉시 충돌**.

### 영향
- Graph 적재 시 노드 매칭 실패
- MERGE가 의도대로 동작하지 않아 중복 노드 생성

### 권고
- **person_id** 채택 권고 (resume-hub의 원본 식별자에 가까움)
- 04.graphrag Core v2의 candidate_id를 person_id로 통일하는 작업을 Phase 1 시작 전에 수행
- 또는 v12 문서에 "04.graphrag Core v2의 candidate_id = 본 문서의 person_id" 매핑 명시

---

## 3. [Should] 1-pass 출력에서 chapters 순서 보장

### 위치
03_prompt_design.md §2.3

### 문제
CandidateContextExtraction 스키마에서 `chapters: list[ChapterExtraction]`는 **Career 순서를 보장하지 않는다**. LLM이 이력서에 기술된 순서대로 chapters를 반환하리라는 보장이 없으며, 특히:

- 이력서가 최신→과거 순일 때 LLM이 과거→최신 순으로 반환할 수 있음
- 이력서에 Career 2개와 SelfIntroduction에서 언급된 추가 경력이 섞일 수 있음

### 영향
- NEXT_CHAPTER 관계 생성 시 시간순 보장 불가
- role_evolution 분석 결과와 chapters 순서 불일치

### 권고
ChapterExtraction에 **순서 식별 필드** 추가:
```python
class ChapterExtraction(BaseModel):
    career_index: int = Field(description="입력 Career 순서 (0부터 시작)")
    # ... 기존 필드
```

또는 프롬프트에 "입력 Career 순서대로 chapters를 반환하세요" 명시적 지시 추가.

---

## 4. [Should] Batch API 실패 시 부분 재처리 전략

### 위치
01_extraction_pipeline.md §7.2, 05_extraction_operations.md

### 문제
v12의 배치 처리는 "1,000건/청크 → Anthropic Batch API 제출"이지만, **Batch API가 부분 실패할 때의 처리 전략이 없다**.

시나리오:
```
1,000건 Batch 제출 → 24시간 후 결과 수집
  - 950건 성공
  - 30건 JSON 파싱 실패 → 3-Tier 재시도 (정의됨)
  - 20건 API 타임아웃/에러 → ??? (미정의)
```

3-Tier 재시도는 **LLM 출력의 품질 문제**에 대한 것이고, **API 레벨 실패**(타임아웃, rate limit, 서버 에러)에 대한 전략이 없다.

### 영향
- Batch API 부분 실패 시 전체 1,000건을 재제출하면 비용 낭비
- 실패 건만 추려서 재제출하는 로직이 없으면 수동 개입 필요

### 권고
```
Batch 결과 수집 후:
  - 성공: 정상 처리
  - LLM 품질 실패: 3-Tier 재시도 (기존)
  - API 실패 (timeout/error): 실패 건만 수집 → 새로운 mini-batch(실패 건만)로 재제출
  - 2회 연속 API 실패: dead-letter queue
```

---

## 5. [Low] 파일→DB 교차 중복 제거의 edge case

### 위치
01_extraction_pipeline.md §4.2

### 문제
"이름+전화번호 해시 매칭 → DB 버전 우선"이라고 기술하나:

- 이름이 동일하고 전화번호가 다른 경우 (전화번호 변경)
- 이름이 다르고 전화번호가 동일한 경우 (가족/동료가 같은 번호 사용 — 드묾)
- 파일 이력서에 전화번호가 없는 경우 (마스킹 또는 원래 미기재)

### 영향
- 전화번호 변경 케이스에서 동일인 미탐지 → 중복 노드
- 전화번호 미기재 시 해시 매칭 불가

### 권고
Phase 2-0 PoC에서 교차 중복 비율 실측 후, 필요 시 추가 매칭 기준(이메일 해시, 이름+생년) 검토. v1에서는 현 설계로 충분할 수 있으나, **중복 노드 비율을 모니터링하는 메트릭 추가** 권고.

---

## 6. 요약

| # | 항목 | 심각도 | 해소 시점 | 비용 |
|---|------|--------|---------|------|
| 1 | N+1 pass 컨텍스트 보강 | **Must** | v12 보강 또는 Phase 0 | ~$3.6 추가 |
| 2 | person_id vs candidate_id 통일 | **Must** | Phase 1 전 | $0 (문서 수정) |
| 3 | chapters 순서 보장 | Should | v12 보강 또는 Phase 1 | $0 |
| 4 | Batch API 부분 재처리 | Should | Phase 1 구현 시 | $0 |
| 5 | 교차 중복 edge case | Low | Phase 2 | $0 |
