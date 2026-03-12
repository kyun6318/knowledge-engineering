# v10 부족한 설계 리뷰

> 누락된 핵심 사항, 구현 세부사항 부재, 미검증 가정 식별

---

## 부족 #1: LLM 프롬프트 설계 전무 (Critical)

### 현황

"LLM 추출" 파이프라인이 핵심인데, 프롬프트 설계가 단 한 줄도 없다.

- CompanyContext: "vacancy.scope_type, role_expectations, operating_model, structural_tensions 추출"이라고만 기술
- CandidateContext: "per-career scope_type/outcomes/signals 추출"이라고만 기술
- LLM 입력 포맷, 출력 JSON 스키마, few-shot 예시, system prompt 모두 부재

### 영향

"추출 로직" 문서의 핵심이 추출 프롬프트인데, 이것이 없으면 문서의 존재 의의가 반감.

### 권고

**추출 프롬프트 설계 문서 추가 필요:**
1. CompanyContext 추출 프롬프트 (입력 포맷, 출력 JSON 스키마, few-shot 3-5개)
2. CandidateContext 추출 프롬프트 (동일)
3. scope_type 분류 가이드라인 (BUILD_NEW/SCALE_EXISTING/RESET/REPLACE 정의)
4. outcome 추출 가이드라인 (METRIC/SCALE/DELIVERY/ORGANIZATIONAL)
5. situational_signal 14개 라벨 분류 기준

이것이 v10의 가장 큰 부족 사항이며, Phase 0 PoC에서 프롬프트 품질이 Go/No-Go 결정의 핵심.

---

## 부족 #2: Pydantic 스키마 정의 부재 (High)

### 현황

"Pydantic 스키마 정의"가 Phase 1 작업으로 언급되나, 실제 스키마 구조가 없다.

- CandidateContext JSON 구조 미정의
- CompanyContext JSON 구조 미정의
- Chapter, Outcome, SituationalSignal 등의 세부 필드 타입/제약 조건 없음

### v19 온톨로지에서 참조 가능하나

v19 스키마가 Graph 스키마 중심이라, LLM 출력용 JSON 스키마는 별도 정의 필요.
예: `outcomes[]`의 각 원소 구조 (type, description, metrics, evidence 등).

### 권고

LLM 출력 JSON 스키마를 Pydantic으로 정의하고 v10에 포함. 이것이 추출 로직의 "계약(Contract)".

---

## 부족 #3: PII 마스킹 구체 전략 부재 (High)

### 현황

"PII 마스킹 모듈"이 Phase 1 작업으로 언급되나, 구체 전략이 없다.

- 어떤 필드를 마스킹하는가? (이름, 전화번호, 주소 외에 이메일? 주민번호?)
- 마스킹 방식은? (해시? 토큰 치환? 삭제?)
- 마스킹 후 원본 복원이 필요한가? (Graph 적재 시 원본 필요?)
- 파일 이력서의 PII는 어떻게 탐지하는가? (NER? 정규식?)

### 특히 중요한 이유

R1(PII 데이터 처리)이 Critical 리스크로 분류되어 있으면서, 구체 전략이 없는 것은 모순.

### 권고

PII 마스킹 전략 문서 별도 작성 또는 v10에 섹션 추가:
- 대상 필드 목록
- 마스킹 방식 (가역/비가역)
- LLM 전송 시 마스킹 범위
- Graph 적재 시 원본 사용 여부
- 법률 검토 결과 반영 방안

---

## 부족 #4: 증분 처리의 "수정" 케이스 구현 부재 (Medium)

### 현황

05_operations_and_monitoring.md §2.2에서 수정 유형을 정의:
- 구조화 필드 수정: "DB 필드 diff → 부분 업데이트"
- 텍스트 필드 수정: "DETACH DELETE old Chapters → LLM 재추출"

### 문제

1. **변경 감지 기준이 모호**: `updated_at`으로 변경 감지하지만, 어떤 필드가 변경되었는지 어떻게 판단?
   - resume-hub.Career의 어떤 필드 변경이 "구조화" vs "텍스트" 수정인지 정의 없음
2. **DETACH DELETE의 위험성**: Chapter에 연결된 Outcome, SituationalSignal, Skill 관계가 모두 삭제됨.
   - 공유 노드(Skill, Organization)가 의도치 않게 고아 노드가 되지 않는지?
3. **소프트 삭제 시 관계 처리**: "노드 유지, 관계 제거"라 했지만, 관계만 제거하면 Graph 쿼리에서 어떻게 제외하는지?

### 권고

증분 처리 상세 설계 추가:
- 구조화/텍스트 필드 분류 테이블
- DETACH DELETE 시 공유 노드 보호 전략
- 소프트 삭제 플래그 설계 (is_active, deleted_at)

---

## 부족 #5: Organization ER 알고리즘 상세 부재 (Medium)

### 현황

03_execution_plan.md에서 Organization ER은 "Rule 1차 + LLM 2차"로 기술.

- Rule: 이름 정규화 + 자회사/개명 사전 + Levenshtein ≤2
- LLM: 모호 케이스 판정

### 문제

1. **BRN 기반 매칭**: Career.BRN → NICE 직접 매칭(60% 적중)은 좋지만, resume-hub의 Career.companyName에서 BRN을 어떻게 획득하는지 불명
   - resume-hub에 BRN 필드가 있는지? 없으면 NICE에서 이름 → BRN 역매칭 필요
2. **자회사/개명 사전**: 어디서 확보하는가? (수동 구축? 외부 DB?)
3. **LLM 2차 매칭 비용**: 모호 케이스 비율 추정 없음
4. **매칭 결과 검증**: 1,000건 전수 검수라 했지만, 50K Organization 중 1,000건은 2%

### 권고

Organization ER 설계 문서 별도 작성:
- BRN 획득 경로 명확화
- 자회사/개명 사전 소스
- LLM 2차 매칭 프롬프트 + 비용 추정
- 검수 기준 (2% 샘플 vs 전수)

---

## 부족 #6: compute_vacancy_fit() 등 핵심 함수 미정의 (Medium)

### 현황

01_extraction_pipeline.md §6.4에서 `compute_match_score()`가 5개 함수를 호출:
- `compute_stage_match()`: §6.2에서 정의 ✓
- `compute_skill_overlap()`: §6.3에서 정의 ✓ (domain_fit의 일부)
- `compute_vacancy_fit()`: **미정의**
- `compute_domain_fit()`: **미정의** (skill_overlap만 부분 정의)
- `compute_culture_fit()`: **미정의**
- `compute_role_fit()`: **미정의**

5개 중 2개만 정의되어 있다. 나머지 3개는 어떻게 계산하는지 불명.

### 특히 vacancy_fit (30% 가중치)

가장 높은 가중치인 vacancy_fit가 "hiring_context + situational_signals 정합"이라고만 기술.
- hiring_context 4종(BUILD_NEW, SCALE_EXISTING, RESET, REPLACE)과 candidate의 어떤 필드를 비교?
- situational_signals 14개 라벨 간 유사도 계산은?

### 권고

**MappingFeatures 5대 특성 계산 상세 설계가 필요**. 이것은 04.graphrag Phase 3에서 다룰 수 있지만, 추출 로직 문서에서도 "어떤 필드가 매칭에 사용되는지"는 명시해야 추출 시 해당 필드를 확실히 포함할 수 있다.

---

## 부족 #7: 데이터 검증/품질 체크 파이프라인 내 위치 부재 (Low)

### 현황

모니터링 메트릭(schema_compliance, required_field_rate 등)은 **배치 완료 후** 체크.
하지만 파이프라인 **내부**에서의 데이터 검증 위치가 불명확.

### 필요한 검증 포인트

1. DB 커넥터 출력 검증: 필수 필드 존재 여부 (Career 빈 이력서 필터링)
2. LLM 출력 검증: JSON 파싱 + Pydantic 검증 (3-Tier 재시도 전)
3. Graph 적재 전 검증: 노드 ID 중복, 관계 무결성
4. Embedding 검증: 차원 수 일치, NaN 체크

### 권고

파이프라인 단계별 검증 체크포인트 추가. 특히 LLM 출력 → Pydantic 검증 흐름을 명시.

---

## 부족한 설계 종합

| # | 항목 | 심각도 | 조치 |
|---|------|--------|------|
| 1 | LLM 프롬프트 설계 | Critical | 프롬프트 + JSON 스키마 + few-shot 추가 |
| 2 | Pydantic 스키마 | High | LLM 출력 JSON 계약 정의 |
| 3 | PII 마스킹 전략 | High | 대상/방식/범위 상세 설계 |
| 4 | 증분 처리 상세 | Medium | 변경 감지/삭제/공유 노드 보호 |
| 5 | Organization ER 상세 | Medium | BRN 경로/사전/비용 |
| 6 | 매칭 함수 정의 | Medium | vacancy_fit 등 3개 함수 설계 |
| 7 | 파이프라인 내 검증 | Low | 단계별 체크포인트 |
