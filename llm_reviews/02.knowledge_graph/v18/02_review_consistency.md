# v18 문서 간 정합성 리뷰

> 리뷰일: 2026-03-14 | 리뷰어: Claude Opus 4.6

---

## 1. v18 내부 문서 간 정합성

### 1.1 파이프라인 ↔ 프롬프트 정합

| 01_extraction_pipeline 참조 | 03_prompt_design 실제 | 일치 여부 | 비고 |
|---------------------------|---------------------|----------|------|
| §2.3 "LLM 입력 ~2,000 토큰" | §1.2 프롬프트 구조 확인 | **일치** | 구조화 필드 사전 주입 반영 |
| §3.2 "SIE 사전 추출 → LLM 보완" | §0 원칙 6 명시 | **원칙만 일치** | 실제 프롬프트 템플릿에 SIE 섹션 없음 |
| §3.4 "1-pass/N+1 분기" | §2.2.1~2.2.3 프롬프트 분리 | **일치** | 호출 전략별 프롬프트 명확 |
| §2.5 "NEEDS_SIGNAL 2-Track" | §1 CompanyContext + §2.6 taxonomy | **일치** | 14개 taxonomy 일관 |

**정합성 위반 1건**:
- 01_extraction_pipeline §3.2에서 "SIE 추출 결과를 컨텍스트로 제공"이라고 했으나, 03_prompt_design §2.2 프롬프트에 SIE 결과 주입 섹션이 없음 → **보완 필요**

### 1.2 파이프라인 ↔ 모델/인프라 정합

| 01_extraction_pipeline | 02_model_and_infrastructure | 일치 여부 |
|----------------------|--------------------------|----------|
| "Haiku Batch" 언급 | §1.1 Claude Haiku 4.5 1순위 | **일치** |
| "Cloud Run Job: kg-extract 10병렬" | §4.2 동일 | **일치** |
| "kg-graph-load <5 태스크" | §4.2 "5 이하" | **일치** |
| "text-embedding-005" | §2.1 동일 | **일치** |
| "SIE 모델 GPU 필요" 암시 | GPU 비용 미포함 | **불일치** |

**정합성 위반 1건**:
- SIE 모델(GLiNER2/NuExtract 1.5)이 01_extraction_pipeline에서 사용되나, 02_model_and_infrastructure에 해당 모델의 인프라 요건(GPU, VRAM, 처리량)이 없음

### 1.3 정규화 ↔ 데이터 품질 정합

| 06_normalization | 07_data_quality | 일치 여부 |
|-----------------|----------------|----------|
| §2 스킬 101,925개, 2.4% 표준 | §1 동일 수치 | **일치** |
| §6.1 days_worked 100% 제로 | §1 period ~100% | **일치** |
| §4 Certificate type 변환 | §3 Graceful Degradation 참조 | **일치** |
| §6 구코드 457개, ~110만건 | 07_data_quality에 미반영 | **누락** |

**정합성 위반 1건**:
- 06_normalization §6에 추가된 구코드→신코드 과제가 07_data_quality에서 education_level 영향으로 반영되지 않음 → Person.education_level 실효 fill rate가 95.6%보다 낮을 수 있음 (미매핑 ~110만건 영향)

### 1.4 PII/검증 ↔ 데이터 품질 정합

| 04_pii_and_validation 메트릭 목표 | 07_data_quality 병목 | 정합 |
|--------------------------------|-------------------|------|
| scope_type_accuracy >70% | positionGrade 39.16%, positionTitle 29.45% | **일치** — 저입력으로 70% 달성 도전적이라는 현실 반영 |
| outcome_f1 >55% | careerDescription 16.9% | **일치** — 낮은 소스 커버리지 고려한 목표 |
| pii_leak_rate <0.01% | 정규식 기반 90%+ | **일치** — "0% 보장 불가" 솔직하게 명시 |

---

## 2. 온톨로지 v25 ↔ v18 정합성

### 2.1 노드/엣지 정합

| v25 04_graph_schema 정의 | v18 01_extraction_pipeline §5.1 | 일치 |
|-------------------------|-------------------------------|------|
| 9 노드 (Person, Organization, Chapter, Vacancy, Role, Skill, Outcome, SituationalSignal, Industry) | 동일 9 노드 | **일치** |
| 13 관계 (HAS_CHAPTER ~ MAPPED_TO) | 동일 13 관계 | **일치** |
| Chapter.scope_type → seniority 변환은 매칭 시점 | §5.1 Chapter 노드에 "[v18] scope_type → seniority 변환은 매칭 시점" 명시 | **일치** |
| SituationalSignal 14개 고정 taxonomy | 03_prompt_design §2.3 SignalLabel 14개 | **일치** |

### 2.2 필드 레벨 정합

| v25 필드 정의 | v18 대응 | 일치 여부 | 비고 |
|-------------|---------|----------|------|
| Person.freshness_weight: 0.3~1.0 | 07_data_quality 및 v25 00_data_source_mapping §3.5 | **일치** | step/smooth 모드 구분 포함 |
| Vacancy.seniority: JUNIOR~HEAD+UNKNOWN | 03_prompt_design §1.3 동일 enum | **일치** | v17 C1 해소 확인 |
| Organization.stage_label | 01_extraction_pipeline §2.2 NICE Lookup | **일치** | |
| Chapter.duration_months | 06_normalization §6.1 직접 계산 | **일치** | daysWorked 100% 제로 처리 |

### 2.3 데이터 소스 매핑 정합

| v25 00_data_source_mapping 정의 | v18 대응 | 일치 |
|-------------------------------|---------|------|
| §1 code-hub 산업/직무/스킬 매핑 | 06_normalization §2~§4 | **일치** |
| §2 job-hub → CompanyContext | 01_extraction_pipeline §2 Pipeline A | **일치** |
| §3 resume-hub → CandidateContext | 01_extraction_pipeline §3 Pipeline B | **일치** |
| §3.7 LinkedIn 외부 데이터 매핑 | 01_extraction_pipeline §Pipeline E | **일치** |
| §9 사용 불가 필드 (LinkedIn) | 07_data_quality §7 | **일치** — 동일 필드 목록 |

---

## 3. v3 데이터 분석 ↔ v18 정합성

### 3.1 실측 수치 정합

| v3.md 수치 | v18 반영 위치 | 일치 |
|-----------|------------|------|
| 이력서 8,018,110 | 06_normalization §6.1 | **일치** |
| career 18,709,830 | 06_normalization §6.1 | **일치** |
| 스킬 101,925, 2.4% 표준 | 06_normalization §2 | **일치** |
| LinkedIn 2,019,293 | 01_extraction_pipeline Pipeline E | **일치** |
| AI 표준화 경력 2,695,840 | 05_extraction_operations §5 | **일치** |
| 구코드 457개, ~110만건 | 06_normalization §6 | **일치** |
| 캠퍼스 공백 변형 3건 | 06_normalization §6 | **일치** |
| 직무 과도 세분화 20%+ | 06_normalization §6 | **일치** |

### 3.2 v3-db-schema.md 정합

| v3-db-schema 필드/타입 | v18 반영 | 비고 |
|----------------------|---------|------|
| Career.jobClassificationCodes: Array(Code) | 06_normalization §5.2 | **일치** |
| Certificate type CERTIFICATE/LANGUAGE_TEST | 06_normalization §4 변환 테이블 | **일치** |
| education.schoolCode: UNIVERSITY_CAMPUS | 06_normalization §6 구코드 과제 | **일치** |
| profile.birthday: 100% sentinel | v25 00_data_source_mapping §9에서 제외 | **일치** |

---

## 4. 정합성 위반 종합

| ID | 위반 내용 | 심각도 | 위치 | 권고 |
|----|----------|--------|------|------|
| C-1 | SIE 결과 주입 프롬프트 부재 | **Medium** | 03_prompt_design §2.2 | SIE 결과 섹션 추가 |
| C-2 | SIE 인프라 요건 미포함 | **Medium** | 02_model_and_infrastructure | GPU/VRAM/처리량 추가 |
| C-3 | 구코드 영향이 07_data_quality에 미반영 | **Low** | 07_data_quality §1 | education_level 실효 fill rate 보정 |
| C-4 | 정규화 과제 의존성 미명시 | **Low** | 06_normalization §6 | 의존성 그래프 추가 |
