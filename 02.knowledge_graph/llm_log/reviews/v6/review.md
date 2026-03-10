# v6 계획 리뷰

> v6 계획(5개 문서)의 실현 가능성, 과설계, 부족 설계를 분석한다.
>
> 작성일: 2026-03-08
> 개정일: 2026-03-08 (타당성 검토 반영)
> 리뷰 대상: 01_v1_gap_analysis.md, 02_extraction_pipeline.md, 03_model_candidates_and_costs.md, 04_execution_plan.md, 05_assumptions_and_risks.md

---

## 1. 전체 평가 요약

v6는 v5↔v10 온톨로지 교차 검증에서 도출된 17건의 불일치를 체계적으로 해소한 판으로, **계획의 성숙도가 높다**. v1→v6까지 6회 반복을 거치며 Gap 분석, 파이프라인 설계, 비용 모델, 실행 계획, 리스크 관리가 상당히 촘촘해졌다. 다만 아래 영역에서 과설계/부족 설계/실현 가능성 우려가 있다.

| 등급 | 건수 | 요약 |
|---|---|---|
| **과설계 (Over-engineered)** | 2건 | v1 MVP 범위 초과 상세화 (Phase 3 관련) |
| **부족 설계 (Under-designed)** | 4건 | 누락된 고려사항, 구체성 부족 |
| **실현 가능성 우려 (Feasibility)** | 3건 | 가정의 낙관, 일정 리스크 |

> **타당성 검토 후 변경**: 초기 리뷰에서 과설계 4건, 부족 설계 5건으로 평가했으나,
> O-3(facet merge ~50줄 수준으로 실질 부담 미미), O-4(표 1개 수준으로 문서 부담 미미),
> U-5(Phase 2-4 소비자 인터뷰에서 결정해도 충분)를 제외하여 과설계 2건, 부족 설계 4건으로 조정.

---

## 2. 과설계 (Over-engineered)

### O-1. [Medium] Phase 3 크롤링 파이프라인의 과도한 상세화

**위치**: 04_execution_plan.md Phase 3 (C1~C4, 7주)

**문제**: Phase 3은 Phase 0~2 MVP 이후 "고도화" 단계인데, 크롤링 파이프라인이 7주 분량으로 매우 상세하게 설계되어 있다. C1~C4 단계별 체크리스트, 뉴스 카테고리 N1~N5, 우선순위 P1~P6 등이 Phase 0~2 수준으로 기술되어 있다.

**과설계 이유**:
- Phase 0~2가 완료되지 않은 시점에서 Phase 3을 이 수준으로 상세화하는 것은 시기상조
- Phase 2 결과에 따라 크롤링 우선순위/범위가 크게 달라질 수 있음 (예: structural_tensions보다 stage_match 활성화가 더 시급할 수 있음)
- 크롤링 대상 사이트의 robots.txt, 이용약관, 법적 이슈 등은 Phase 2 이후에 판단해야 할 사항

**참고 (타당성 검토)**: v10 06_crawling_strategy.md와의 정합성 확보를 위해 의도적으로 상세화한 것으로, "이유 있는 상세화"이긴 하나 MVP 관점에서는 과도함

**권장**: Phase 3은 "목표 + 대략적 접근법 + v10 06_crawling_strategy.md 참조" 수준으로 축소하고, Phase 2 완료 후 상세화

### O-2. [Low] structural_tensions 8-type taxonomy의 Pydantic 스키마 조기 확정

**위치**: 02_extraction_pipeline.md §1.1

**문제**: structural_tensions는 v1 MVP에서 `null`로 유지되는 필드인데, 8-type taxonomy의 Pydantic 스키마, LLM 프롬프트, source ceiling, 활성화 경로까지 상세하게 설계되어 있다.

**과설계 이유**:
- v1에서 사용하지 않는 필드에 ~400줄의 설계가 투입됨
- 크롤링 데이터 소스가 확보되기 전에 taxonomy를 확정하면, 실제 데이터와 맞지 않을 리스크가 있음
- v10 온톨로지 자체가 진화 중이므로 taxonomy가 변경될 가능성 있음

**권장**: Pydantic Enum과 기본 스키마만 정의하고, 프롬프트/활성화 로직은 Phase 3 시작 시 설계

> **타당성 검토 후 제외된 과설계 항목**:
> - ~~O-3. facet merge 로직 (~50줄 수준, 실질적 부담 미미)~~
> - ~~O-4. Company-to-Company 로드맵 (표 1개 수준, 향후 참조용으로 가치 있음)~~

---

## 3. 부족 설계 (Under-designed)

### U-1. [High] 오케스트레이션 도구 선택의 부재

**위치**: 04_execution_plan.md, 03_model_candidates_and_costs.md

**문제**: 파이프라인 오케스트레이션에 "Cloud Workflows / Prefect"로 $50/월이 배정되어 있지만, 구체적으로 어떤 도구를 사용할지, 파이프라인 DAG를 어떻게 구성할지 기술이 없다.

**부족한 이유**:
- Pipeline A→B→C→D→E의 의존성 관계와 병렬 처리 가능 여부가 불명확
- 500K 이력서의 배치 처리 시 chunk 분할, 재시도, 모니터링을 오케스트레이터 없이 어떻게 할지 불분명
- Cloud Workflows와 Prefect는 성격이 매우 다른 도구 — 선택 기준이 없음

**권장**: Phase 0-3 인프라 셋업에 오케스트레이션 도구 선정 의사결정 추가. 최소한 Pipeline A/B 병렬 실행 가능성, chunk 관리 전략, 실패 건 재처리 워크플로우를 명시

### U-2. [High] LLM 프롬프트 출력 파싱 실패 전략의 부재

**위치**: 02_extraction_pipeline.md 전체

**문제**: LLM 추출 의존도가 50-65%로 높은데, LLM이 유효하지 않은 JSON을 반환하거나, 스키마와 다른 형식으로 응답할 때의 처리 전략이 기술되지 않았다.

**부족한 이유**:
- 실제 운영에서 LLM JSON 파싱 실패율은 2-10% 수준
- 500K × 3 경력 = 150만 건의 LLM 호출에서 파싱 실패가 3~15만 건 발생 가능
- Pydantic validation 실패, 필수 필드 누락, enum 범위 초과 등의 처리가 없음

**권장**:
- LLM 응답 파싱 실패 시 retry 전략 (최대 2회, temperature 조정 등)
- Pydantic `ValidationError` 발생 시 fallback 로직 (부분 추출 허용 vs 전체 skip)
- JSON repair 라이브러리 (예: `json-repair`) 활용 검토
- 파싱 실패율을 모니터링 메트릭에 추가

### U-3. [Medium] 이력서 파싱 라이브러리의 현실적 커버리지 미검증

**위치**: 02_extraction_pipeline.md §3.1, 04_execution_plan.md Phase 0-2

**문제**: 파싱 도구로 PyMuPDF, python-docx, python-hwp을 지정하고 Phase 0에서 50건 테스트를 계획하지만, 이들 라이브러리의 **한국어 이력서** 커버리지에 대한 현실적 평가가 없다.

**부족한 이유**:
- `python-hwp`는 성숙도가 낮고 복잡한 HWP 포맷(OLE2)을 완전히 지원하지 않음
- 한국어 이력서는 표 기반 레이아웃이 매우 많은데, PyMuPDF의 표 추출은 제한적
- Phase 0에서 50건 테스트 후 "경력 블록 분리 정확도 < 50%이면 LLM fallback"이라는 기준이 있지만, 50% 미만일 때의 비용 증가($250~500)가 전체 비용에 미치는 영향이 경미하게 서술됨

**권장**:
- Phase 0에서 파싱 도구별 실패 케이스 카테고리화 (표, 2단, 이미지, HWP 세부 버전)
- `pdfplumber`를 기본 PDF 파서로 격상 검토 (표 추출에 PyMuPDF보다 우수)
- HWP → LibreOffice headless 변환을 기본값으로 설정하고, python-hwp는 fallback으로

### U-4. [Low] Gold Label 품질 기준의 구체성 부족

**위치**: 04_execution_plan.md Phase 2-2

**문제**: "전문가 2인 × 200건 독립 annotation"에 대한 annotation 가이드라인, 평가 기준, 불일치 해결 프로토콜이 없다.

**부족한 이유**:
- scope_type 분류는 5-class (IC/LEAD/HEAD/FOUNDER/UNKNOWN)인데, IC vs LEAD 경계가 모호한 경우의 판정 기준이 필요
- outcomes 추출의 경우, "정량적 성과"의 기준이 annotator마다 다를 수 있음
- Inter-annotator agreement(Cohen's κ)의 최소 기준이 설정되어 있지 않음

**참고 (타당성 검토)**: Phase 2 시점에 가이드라인을 작성해도 크게 늦지 않으나, Phase 0 PoC에서 50건 평가 시 기본 기준은 필요

**권장**:
- Phase 0 PoC 시 기본 annotation 기준 수립 (scope_type 경계 판정 규칙, 최소한의 예시)
- Phase 2 annotation 시작 전 가이드라인 확정 + Cohen's κ 최소 기준(κ > 0.6) 설정
- 불일치 해결: 도메인 전문가 최종 판정 프로토콜

> **타당성 검토 후 제외된 부족 설계 항목**:
> - ~~U-5. BigQuery 스키마 (Phase 2-4 소비자 인터뷰에서 결정해도 충분, 사전 확정 시 오히려 재설계 리스크)~~

---

## 4. 실현 가능성 우려 (Feasibility)

### F-1. [High] DE 1명 + MLE 1명 기준 16~19주 타임라인의 낙관

**위치**: 04_execution_plan.md 타임라인 요약

**문제**: DE 1명 + MLE 1명이 16~19주에 Phase 0~2를 완수한다는 일정이 낙관적이다.

**근거**:
- **Phase 1-3 CandidateContext 파이프라인 3주**: Rule 추출 + LLM 프롬프트 설계 + Batch API 연동 + 200건 통합 테스트를 MLE 1명이 3주에 완료하기 어려움. 프롬프트 최적화만 2~3주 소요 가능
- **Phase 1-4 Graph 적재 2주**: Entity Resolution + Deterministic ID + Industry 노드 + REQUIRES_ROLE + Vector Index + 벤치마크를 DE 1명이 2주에 완료하기 빠듯
- **Phase 0 병행 작업**: 0-1(데이터 탐색)과 0-3(인프라 셋업)을 병행한다고 했지만, DE 1명이 Neo4j 셋업 + 파싱 라이브러리 테스트 + NICE DB 연동을 동시에 하기 어려움
- **도메인 전문가 파트타임**: Gold Label 검수가 Phase 2에서만 필요하다고 했지만, 실제로는 Phase 0 annotation 가이드라인, Phase 1 프롬프트 검증에도 도메인 전문가가 필요

**현실적 추정**: 20~24주 (DE 1 + MLE 1 기준), 병렬 업무 비효율과 소통 오버헤드 고려

### F-2. [Medium] Haiku 4.5의 한국어 구조화 추출 품질 가정

**위치**: 03_model_candidates_and_costs.md §1.1, 05_assumptions_and_risks.md A8

**문제**: Haiku가 "Sonnet의 85% 수준"이라는 가정(A8)으로 전체 비용 모델이 구축되었지만, 이 수치는 검증되지 않은 가정이다.

**실현 가능성 우려**:
- 한국어 이력서의 비정형 텍스트에서 14-label taxonomy 분류 + JSON 출력이라는 복합 태스크에서 Haiku의 실제 성능은 예측하기 어려움
- 특히 outcomes 추출(정량/정성 구분, metric_value 추출)과 situational_signals(14개 중 다중 선택)는 Haiku에게 어려울 수 있음
- Haiku→Sonnet 전환 시 비용이 5배 증가하여, 비용 모델이 크게 변동

**참고 (타당성 검토)**: v6는 이미 Phase 0 PoC에서 Haiku vs Flash vs Sonnet 비교 평가를 계획하고 있어, 이 리스크를 인지하고 있다. 다만 비용 모델의 "기본 시나리오"가 Haiku 성공을 전제로 구성된 점이 우려사항.

**완화**: Phase 0 PoC의 50건 비교 평가에서 이 가정을 반드시 검증하되, **비용 모델에 "Haiku 품질 미달 시" 시나리오를 시나리오 A의 변형(A')으로 추가** — Sonnet Batch 기반 비용 범위를 기본 보고에 포함

### F-3. [Medium] NICE 데이터 접근 및 매칭률

**위치**: 05_assumptions_and_risks.md A5, §2.4

**문제**: NICE 매칭률 60% 가정이지만, NICE DB 접근 방법(API? 덤프? 계약?)이 구체적으로 기술되지 않았다.

**실현 가능성 우려**:
- NICE DB 접근 계약이 별도로 필요하며, 비용/시간이 소요될 수 있음
- "Phase 0에서 NICE DB 접근 확인"이라고 했지만, 계약/비용이 확정되지 않으면 Phase 0이 지연됨
- NICE 매칭률이 30% 이하이면 stage_match가 대부분 INACTIVE → MappingFeatures의 핵심 피처가 무용화

**권장**: NICE DB 접근 계약을 Phase 0 **이전**에 사전 확인 (blocking dependency로 표기)

---

## 5. 긍정적 평가 (Well-designed)

### W-1. Deterministic ID + MERGE 패턴 (v5)
Graph idempotency를 보장하는 핵심 설계. 재처리, 증분 처리, 롤백 모든 시나리오에서 데이터 일관성을 유지.

### W-2. Source Tier Confidence (v6 M-4)
`field_confidence = min(extraction_confidence, source_ceiling)` 규칙이 모든 추출에 일관되게 적용. T4 카테고리 예외 처리도 현실적.

### W-3. 비용 모델의 투명성
4개 시나리오(A/B/C/D)별 비용이 건당 단가까지 분해되어 산출. 가정 목록(A1~A18)과 검증 방법이 매핑.

### W-4. Phase 0 PoC의 다면적 검증
LLM 추출 품질, 파싱 품질, PII 마스킹 영향, Embedding 분별력, LLM 호출 전략까지 5개 축의 PoC. 의사결정 테이블도 명확.

### W-5. v10 온톨로지 정합성
Industry 노드, REQUIRES_ROLE, MAPPED_TO, ScopeType→Seniority 변환 등 v10 스키마의 세부 요구사항이 파이프라인에 정확히 매핑.

---

## 6. 리뷰 결론

| 영역 | 판정 | 비고 |
|---|---|---|
| Gap 분석 (01) | **충분** | v1→v10 차이를 빠짐없이 식별 |
| 파이프라인 설계 (02) | **대체로 충분, 일부 과설계** | Phase 3 관련 상세화 과도, JSON 파싱 실패 전략 부족 |
| 비용 모델 (03) | **충분** | 시나리오별 비용 투명, Haiku 가정 검증 필요 |
| 실행 계획 (04) | **대체로 충분, 일정 낙관** | 오케스트레이션 미정, 일정 20~24주가 현실적 |
| 리스크 (05) | **충분** | 16개 리스크 커버, NICE 접근 blocking dependency 미표기 |

**v7 반영 권장 사항** (타당성 검토 후 확정, 우선순위순):

| 순위 | 항목 | 유형 | 영향도 | v7 반영 난이도 |
|---|---|---|---|---|
| 1 | LLM 출력 파싱 실패 전략 추가 | U-2 (부족) | High | 낮음 (§8에 추가) |
| 2 | 오케스트레이션 도구 선정 기준 + DAG 설계 | U-1 (부족) | High | 중간 |
| 3 | NICE DB 접근을 Phase 0 전 blocking dependency로 명시 | F-3 (실현가능성) | High | 낮음 |
| 4 | 타임라인 20~24주로 현실화 + 버퍼 | F-1 (실현가능성) | High | 낮음 |
| 5 | 비용 모델에 "Haiku 미달 시" 시나리오 A' 추가 | F-2 (실현가능성) | Medium | 낮음 |

> **v7 작성 여부 판단**: 위 5건 중 U-2(JSON 파싱)와 U-1(오케스트레이션)은 **실행 단계에서 반드시 필요한 설계가 누락**된 것이므로, v7에서 반영하는 것이 권장됨. 나머지 3건은 기존 문서에 1~2줄 추가/수정으로 해결 가능한 수준이지만, 함께 반영하는 것이 효율적.
