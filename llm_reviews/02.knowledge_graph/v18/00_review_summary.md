# v18 Knowledge Graph 리뷰 요약

> 리뷰일: 2026-03-14 | 리뷰어: Claude Opus 4.6
> 대상: 02.knowledge_graph/v18/ (7개 문서)
> 참조: 01.ontology/v25/, 00.datamodel/summary/v3.md, 00.datamodel/summary/v3-db-schema.md
> 비교 기준: v12 리뷰 (llm_reviews/02.knowledge_graph/v12/)

---

## 1. 총평

v18은 v12 대비 **v3 데이터 분석 결과(SIE 모델, LinkedIn 외부 데이터, code-hub 정밀 EDA)를 반영**하고, **온톨로지 v25와의 정합성을 강화**한 버전이다. 7개 문서 전반적으로 설계 성숙도가 높고, v3 데이터 분석에서 발견된 실측치(구코드 미매핑 ~110만건, 직무 과도 세분화, 캠퍼스 코드 공백 변형 등)를 정규화 선행 과제로 적절히 반영했다.

특히 **SIE 모델(GLiNER2/NuExtract 1.5) 통합**, **Pipeline E(LinkedIn 외부 데이터)**, **정규화 선행 과제 확장(구코드→신코드, 직무 코드 계층화, 캠퍼스 코드 정리)** 세 가지 신규 추가가 핵심 변화다.

그러나 v12 리뷰에서 지적된 일부 구조적 이슈가 아직 해소되지 않았으며, v3 신규 추가사항에 대한 구현 디테일이 아직 선언적 수준에 머물러 있다. SIE 모델과 LLM의 역할 분담이 구체적이지 않고, LinkedIn 동일 인물 매칭 전략이 개략적이며, 정규화 선행 과제의 우선순위 간 의존성이 불명확하다.

---

## 2. 문서별 평가

| 문서 | 핵심 내용 | 강점 | 약점 | 점수 |
|------|----------|------|------|------|
| 01_extraction_pipeline | 4개 파이프라인(A/B/B'/C) + Pipeline E | SIE 통합 위치 명확, Pipeline E 단계 정의 | SIE→LLM 핸드오프 세부 미정의 | 8.5/10 |
| 02_model_and_infrastructure | LLM/임베딩/Neo4j/GCP 리소스 | 비용 추정 현실적, 모델 선정 기준 명확 | Gemini 2.0 Flash 대안 검토 구체성 부족 | 8.0/10 |
| 03_prompt_design | CompanyContext/CandidateContext 프롬프트 | Taxonomy 고정, Few-shot 충실, SIE 연동 원칙 | SIE 결과가 프롬프트에 주입되는 형식 미정의 | 8.0/10 |
| 04_pii_and_validation | PII 마스킹, 6개 검증 체크포인트 | CP1-CP6 체계적, 전화번호 정규식 종합 | 법률 검토 의존성이 Phase 0 차단 가능 | 8.5/10 |
| 05_extraction_operations | 증분 처리, 테스트, Organization ER | DETACH DELETE 안전 절차, 공유 노드 분류 | LinkedIn 동기화와 증분 처리 통합 미설계 | 7.5/10 |
| 06_normalization | 3-Tier 비교, 스킬/기타 정규화 | v3 신규 과제 3건 추가, 실측 데이터 기반 | 정규화 과제 간 의존성 그래프 부재 | 8.0/10 |
| 07_data_quality | 필드 가용성, Graceful Degradation | Confidence Penalty 규약 명시, LinkedIn 품질 | job-hub 실측 fill rate 아직 "예상" 수준 | 7.5/10 |

---

## 3. 점수 요약

| 평가 항목 | v12 | v18 | 변화 | 비고 |
|----------|-----|-----|------|------|
| 기술적 타당성 | 8.5/10 | **8.5/10** | = | SIE 통합은 유망하나 구현 디테일 부족 |
| 온톨로지 v25 정합성 | 9/10 | **9.5/10** | +0.5 | v25 참조 일관, SituationalSignal 14개 정합 |
| 실현 가능성 (일정) | 7/10 | **7/10** | = | Phase 5 추가로 전체 타임라인 연장 |
| 실현 가능성 (비용) | 8/10 | **8/10** | = | SIE GPU 비용 미반영 |
| 문서 정체성/범위 | 9/10 | **9/10** | = | 3-Layer 경계 준수 |
| 구현 디테일 | 8.5/10 | **8/10** | -0.5 | v3 신규 추가사항이 선언적 |
| 데이터 분석 반영도 | - | **9/10** | 신규 | v3 실측치 충실 반영 |

**종합: v12 8.3/10 → v18 8.2/10** (v3 신규 추가의 선언적 수준이 약간 감점, 데이터 분석 반영도가 보상)

---

## 4. 핵심 판정

### 잘한 점 (Strengths)

1. **v3 데이터 분석 충실 반영**: 구코드 미매핑 110만건, 직무 과도 세분화, 캠퍼스 공백 변형 등 실측 데이터에서 발견된 이슈를 정규화 선행 과제로 구체적으로 추가
2. **SIE 모델 통합 방향**: GLiNER2를 LLM 전 사전 추출 단계로 배치하여 Hallucination 없는 Span 기반 추출 + LLM 추론의 역할 분리 방향이 합리적
3. **Pipeline E 단계 정의**: LinkedIn 외부 데이터를 E-1(프로필)/E-2(Chapter 보강)/E-3(Organization 교차) 3단계로 명확히 분리
4. **Confidence Penalty 규약 체계화**: 07_data_quality.md에서 fallback 유형별 confidence penalty를 표로 명시 (-0.05 ~ -0.20)
5. **정규화 선행 과제 확장**: 기존 과제에 더해 구코드→신코드, 직무 코드 계층화, 캠퍼스 코드 정리를 난이도/영향범위와 함께 추가

### 개선 필요 (Weaknesses)

1. **SIE→LLM 핸드오프 구체성 부족**: SIE 추출 결과가 LLM 프롬프트에 어떤 형식으로 주입되는지, SIE 추출 실패 시 LLM-only 폴백 조건이 불명확
2. **LinkedIn 동일 인물 매칭**: "이름+회사명+기간 조합으로 추정"만 언급되어 있으며, 매칭 알고리즘/임계값/검증 방법이 없음
3. **SIE GPU 비용 미반영**: 02_model_and_infrastructure.md에서 GLiNER2/NuExtract 1.5의 GPU 리소스 비용이 비용 추정에 포함되지 않음
4. **정규화 과제 의존성**: 6개 정규화 과제가 독립적으로 나열되어 있으나, 순서 의존성(예: 회사명 정규화 → LinkedIn 교차 매핑)이 명시되지 않음
5. **job-hub 실측 데이터 부재**: 07_data_quality.md에서 job-hub 필드 가용성이 여전히 "예상" 수준 — Phase 4-1 이전까지 실측 불가하지만, 리스크로 명시 필요

---

## 5. v12 대비 변경 추적

| 영역 | v12 | v18 | 변경 유형 |
|------|-----|-----|----------|
| SIE 모델 | 없음 | GLiNER2/NuExtract 1.5 사전 추출 단계 | **신규** |
| Pipeline E | 없음 | LinkedIn 외부 데이터 통합 3단계 | **신규** |
| 정규화 과제 | 5개 | 8개 (+구코드 매핑, 직무 계층화, 캠퍼스 정리) | **확장** |
| 데이터 소스 | resume-hub + job-hub + code-hub + NICE | + LinkedIn/BrightData 2.0M | **확장** |
| 온톨로지 참조 | v19~v22 | v25 | **갱신** |
| SituationalSignal | 14개 (M&A 포함) | 14개 (MONETIZATION 추가, M_AND_A 온톨로지에서 제거) | **변경** |
| Confidence Penalty | 산재 | 07_data_quality.md 표로 통합 | **개선** |
| LinkedIn 데이터 품질 | 없음 | 07_data_quality.md §7 | **신규** |
