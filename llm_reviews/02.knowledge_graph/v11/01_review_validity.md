# v11 타당성 리뷰

> 대상: 02.knowledge_graph/results/extraction_logic/v11/
> 기준: 기술적 합리성, 프롬프트 설계 품질, 검증 전략 적절성, 04.graphrag와의 정합성

---

## 1. 파이프라인 아키텍처 (01_extraction_pipeline.md)

### 1.1 4개 파이프라인 분리: 타당 (8/10)

A(Company), B(Candidate DB), B'(Candidate 파일), C(Graph 적재) 분리는 합리적이다.

**타당한 점**:
- DB-first, 파일 폴백 전략으로 80% 데이터를 저비용으로 처리
- Pipeline D/E를 04.graphrag로 이관하여 범위 명확화
- Cloud Run Jobs 기반 배치 처리로 비용 최적화

**우려 사항**:
- Pipeline B'(파일)와 B(DB)의 출력 스키마가 동일하다고 가정하나, 파일에서 추출한 데이터의 **필드 커버리지가 DB보다 현저히 낮을 것**
  - DB: companyName, position, startDate, endDate 직접 확보 가능
  - 파일: LLM이 비정형 텍스트에서 모든 것을 추출해야 함 → 정확도 편차 큼
- 이 품질 차이를 **normalization_confidence 하나로 퉁치기에는** 부족할 수 있음

### 1.2 DB 직접 매핑 + LLM-for-reasoning: 타당 (9/10)

구조화 필드는 DB에서 직접 추출하고, LLM은 추론이 필요한 필드(hiring_context, scope_type, outcomes, signals)만 담당하는 전략은 **비용과 품질 모두에서 최적**.

- CompanyContext LLM 토큰 44% 절감, CandidateContext 40% 절감은 현실적 추정
- 이 절감은 DB 필드를 "사전 확보 정보"로 프롬프트에 주입하는 방식으로 달성

### 1.3 3-Tier 비교 전략: 타당 (8/10)

Tier 1(CI Lookup) → Tier 2(정규화+임베딩) → Tier 3(임베딩 only) 폴백은 합리적이다.

**타당한 점**:
- 비용: Tier 1은 $0, Tier 2/3는 임베딩 비용만 (~$0.12)
- match_method 기록으로 추후 품질 분석 가능

**우려 사항**:
- **Tier 2 synonyms 사전의 규모와 출처가 불명확**. code-hub에 synonyms가 있는지, 누가 관리하는지 미기술
- Tier 3(임베딩 only)의 0.75~0.80 임계값이 한국어 전공/직무명에서 **과도하게 관대**할 수 있음
  - "경영학"과 "경영정보학"이 높은 유사도를 가질 수 있으나 실제로는 다른 전공

### 1.4 compute_skill_overlap 하이브리드: 타당하나 범위 모호 (6/10)

이 함수는 **매칭 로직이지 추출 로직이 아니다**. v11이 범위를 추출에 한정했다면서 01_extraction_pipeline.md §5.4에 매칭 함수를 포함하는 것은 **잔존하는 범위 혼란**.

04.graphrag Phase 3에서 매칭을 담당하므로, 여기서는 삭제하고 매칭 필드 매핑 테이블(§6)만 유지하는 것이 일관적.

### 1.5 비용 추정: 타당 (8/10)

| 항목 | 추정 | 검증 |
|------|------|------|
| CompanyContext $0.00044/build | Haiku Batch 입력 2,200 tok × $0.40/M + 출력 ~500 tok × $2.00/M | 계산 정합 |
| CandidateContext $0.00158/build | Haiku Batch 입력 1,800 tok + 출력 ~800 tok | 합리적 |
| Embedding $25.5 | 1.8M × 200 tok avg × $0.0001/1K chars ≈ $25 | 합리적 |
| 추출 총 비용 $523 (Batch) | LLM + Embedding + 파일 파싱 | **04.graphrag 비용과 정합** |

---

## 2. 프롬프트 설계 (03_prompt_design.md)

### 2.1 설계 원칙: 우수 (9/10)

5가지 원칙(Taxonomy Enforcement, Evidence Span, Self-Confidence, Ambiguity Rules, 구조화 필드 사전 주입)은 **프로덕션 LLM 추출에서 검증된 베스트 프랙티스**.

특히:
- **Evidence Span** ("근거 없으면 생성하지 마라")은 hallucination 방지에 핵심
- **Taxonomy Enforcement** (열거형 강제)는 JSON 파싱 안정성 확보
- **Ambiguity Rules** (BUILD_NEW vs SCALE_EXISTING 구분 규칙)는 일관성 보장

### 2.2 CompanyContext 프롬프트: 타당하나 보완 필요 (7/10)

**타당한 점**:
- hiring_context 분류 가이드라인이 구체적 (한국어/영어 키워드, 모호 케이스 규칙)
- operating_model 추출의 키워드 카운트 기반 정량화 + 광고성 문구 필터
- Few-shot 예시 2개 제공

**보완 필요**:
- **Few-shot이 2개로 부족**. 4개 HiringContext 값 × 최소 1개씩 = 4개 이상 필요. 특히 RESET과 REPLACE 예시 누락
- **operating_model의 "LLM 진정성 체크"가 구현 불가능에 가까움**. "애자일 팀"이 광고성인지 실제인지 LLM이 JD 본문만으로 구분하기 극히 어려움 → confidence를 낮추는 것으로 충분
- **structural_tensions는 "v1에서 대부분 null"이라면서 스키마에 포함**. Phase 5에서 활성화 예정이라면 v1에서는 프롬프트에서 아예 제외하여 토큰 절약 가능

### 2.3 CandidateContext 프롬프트: 타당 (8/10)

**타당한 점**:
- scope_type 분류 가이드라인이 positionGradeCode 힌트 활용과 함께 구체적
- outcomes 5개 유형(METRIC/SCALE/DELIVERY/ORGANIZATIONAL/OTHER) 분류가 실용적
- situational_signals 14개 라벨 + 모호 케이스 규칙은 **이 프로젝트의 핵심 차별점**

**보완 필요**:
- **Career별 추출 vs 전체 이력 추출 전략이 혼재**
  - ChapterExtraction은 Career별인데, role_evolution/domain_depth는 전체 이력 기반
  - 하나의 LLM 호출에서 둘 다 하는지, 2-pass인지 불명확
  - 500K 이력서에서 Career 평균 3개면 LLM 호출 구조가 비용에 큰 영향
- **work_style_signals가 "v1 INACTIVE"인데 추출**한다는 것은 불필요 비용. 프롬프트에서 제외 권고

### 2.4 Confidence 캘리브레이션: 타당 (8/10)

소스별 신뢰 상한(self_resume 0.85, jd_internal 0.80)은 합리적.

**우려**: `min(llm_confidence, source_ceiling)` 단순 적용은 LLM이 항상 source_ceiling 근처 값을 출력할 가능성. **실제 사용 시 LLM confidence 분포를 Phase 0에서 확인** 필요.

### 2.5 프롬프트 버전 관리: 타당 (8/10)

Git 기반 + 50건 Golden Set 회귀 테스트 + 메타데이터(prompt_version) 기록은 프로덕션 수준.

---

## 3. PII 마스킹 및 검증 (04_pii_and_validation.md)

### 3.1 PII 마스킹 전략: 타당 (8/10)

**타당한 점**:
- 비가역 토큰 방식(`[NAME_001]`)은 LLM 전송 시 표준 접근법
- 주민번호 즉시 삭제, 주소 삭제, 생년월일 연도만 유지는 합리적
- 법률 검토 미완료 시에도 진행 가능한 설계 (전량 마스킹 기본값)

**우려 사항**:
- **매핑 테이블(person_id → 원본 이름/전화번호) 자체가 PII 집합체**. "별도 보안 저장소"라고만 하고 구체적 보호 방안 미기술. Secret Manager는 소량 키-값 전용이므로 500K 매핑에 부적합
- **정규식 기반 전화번호 탐지가 한국 전화번호 변형(010 1234 5678, +82-10-1234-5678, 01012345678)을 모두 커버하는지** 패턴이 하나뿐
- **DB 이력서의 경우 workDetails/CareerDescription 내 이름 멘션** 가능성. "김철수 대리와 협업"처럼 타인 이름이 포함될 수 있으나 마스킹 대상에서 누락

### 3.2 파이프라인 검증 체크포인트: 우수 (9/10)

CP1~CP6 6단계 검증은 v10 대비 **가장 큰 개선 중 하나**.

**특히 우수**:
- CP1(입력 검증): Career 빈 이력서 필터링, 텍스트 최소 길이 체크
- CP3(LLM 출력): JSON → Pydantic 검증의 3-Tier 재시도
- CP5(적재 검증): 노드 ID 중복, 관계 무결성, 적재 수 95% 일치

**보완 필요**:
- CP4(정규화 검증)의 `needs_review` 플래그가 달린 데이터의 **수동 검토 프로세스가 미정의**. 누가 언제 어떻게?
- CP2(마스킹 검증)에서 주소 패턴 탐지 정확도 80%는 **의도적으로 낮게 설정한 것인지, 개선 필요한 것인지** 불명확

### 3.3 품질 메트릭: 타당 (8/10)

자동 품질 메트릭 10개 항목은 적절하나:
- **pii_leak_rate 0% 목표**는 현실적이나, 측정 방법이 정규식 기반이므로 **실제 0% 보장은 불가**. 확률적 목표(≤0.01%)가 더 정직
- **outcome_f1 ≥55%, signal_f1 ≥50% 목표**는 매우 보수적. 이 수준이면 매칭 정확도에 미치는 영향 검토 필요

---

## 4. 증분 처리 및 운영 (05_extraction_operations.md)

### 4.1 증분 처리 전략: 타당 (8/10)

**타당한 점**:
- 구조화 vs 텍스트 필드 분류 후 차등 처리 (구조화: 직접 업데이트, 텍스트: LLM 재추출)
- 공유 노드 보호 (Skill/Organization은 관계만 제거, Outcome/SituationalSignal은 노드도 삭제)
- NEXT_CHAPTER 관계 재연결까지 고려

**우려 사항**:
- **SelfIntroduction 변경 시 "전체 Career 재추출"**은 비용 폭탄 가능. 500K 이력서에서 자기소개서 업데이트가 빈번하다면(이직 시즌 등) 일일 비용 급증
- **소프트 삭제의 `is_active: true` 필터**를 모든 쿼리에 추가해야 하는 것은 **운영 부담**. Neo4j에서는 라벨 기반 필터링이 더 효율적일 수 있음 (`:ActivePerson`, `:ArchivedPerson`)

### 4.2 Organization ER 설계 보강: 타당 (7/10)

**타당한 점**:
- BRN 획득 경로 명시 (직접 62% + fuzzy 40%)
- 한국어 특수 케이스 (토스 = 비바리퍼블리카 등)

**우려 사항**:
- BRN 부재 40%에서 companyName fuzzy 매칭 ~60% 정확도는 **전체 Organization 매칭률 84%의 근거**이나, fuzzy 매칭의 60% 정확도가 어떻게 산출되었는지 근거 없음
- "미확인 기업"에 `hash(companyName_normalized)`를 쓰면, **동일 기업의 다른 표기가 별도 노드로 생성**될 위험 (예: "삼성SDS" vs "삼성에스디에스")

### 4.3 테스트 전략: 타당 (8/10)

단위/통합/멱등성/배치/스케일/품질 테스트 구분이 적절하다.

- Gold Set 50건 → 200건 확장 경로가 명확
- 384건 통계 샘플링 (95% CI, ±5%)은 Phase 2 이후 적절한 수준

---

## 5. 04.graphrag와의 정합성

### 5.1 정합 (일치하는 항목)

| 항목 | v11 | 04.graphrag v2 | 정합 |
|------|-----|----------------|------|
| Embedding 모델 | text-embedding-005, 768d | 768d 통일 | O |
| Neo4j 적재 | UNWIND 배치, ≤5 태스크 | UNWIND 배치, 100건/트랜잭션 | O |
| 서비스 계정 | kg-processing, kg-loading | 3개 분리 (crawling, processing, loading) | O |
| LLM 모델 | Haiku 4.5 (Batch), Sonnet 폴백 | 동일 | O |
| Pipeline D/E 위치 | 04.graphrag 참조 | Phase 3/1에서 관리 | O |
| 비용 | 추출 $523 (Batch) | Phase 2 LLM $1,473에 포함 | O |

### 5.2 불일치 (주의 필요)

| 항목 | v11 | 04.graphrag v2 | 영향 |
|------|-----|----------------|------|
| **관계명** | PERFORMED_ROLE, OCCURRED_AT (v19) | HAD_ROLE, AT_COMPANY | **Medium** — 어느 것이 canonical? |
| **Graph 스키마** | 9 Node + v19 통합 관계 | Phase 1 스키마에 HAD_ROLE, AT_COMPANY 사용 | **Medium** — 코드 작성 시 혼란 |
| **롤백 전략** | loaded_batch_id 기반 언급만 | DETACH DELETE 구체적 쿼리 | **Low** — 04.graphrag가 더 상세 |

### 5.3 권고

- **관계명은 v19 온톨로지가 canonical**이라고 v11이 명시했으므로, **04.graphrag v2 측에서 관계명을 v19 기준으로 업데이트** 필요
- 이 불일치를 해소하지 않으면 **구현 Phase 1에서 개발자가 어떤 관계명을 쓸지 혼란**
