# v9 온톨로지 스키마 리뷰

> 리뷰 대상: 7개 문서
> - `ontology/schema/v9/01_company_context.md` (568줄)
> - `ontology/schema/v9/02_candidate_context.md` (642줄)
> - `ontology/schema/v9/02_v4_amendments.md` (~146줄)
> - `ontology/schema/v9/03_mapping_features.md` (797줄)
> - `ontology/schema/v9/04_graph_schema.md` (394줄)
> - `ontology/schema/v9/05_evaluation_strategy.md` (796줄)
> - `ontology/schema/v9/06_crawling_strategy.md` (1489줄)
>
> 리뷰 기준: v8 리뷰 (권장사항 E-1~E-2, M-2~M-4), v7 리뷰, v6 리뷰, v5 리뷰, v4 문서 4건, v3 평가서
>
> 리뷰일: 2026-03-08

---

## 1. 전체 평가

v9는 v8 리뷰의 즉시 조치 2건(E-1, E-2)과 파일럿 중 검토 2건(M-2, M-4)을 반영한 버전이다. v8에서 남아 있던 마지막 정합성 이슈(A6 참조 경로 불일치, A7 이관 미처리)가 해결되었고, 05_evaluation_strategy의 Krippendorff's alpha 미달 대응 및 처리량 표기 교정이 완료되어 전체 문서가 매우 높은 완성도에 도달했다.

| 평가 영역 | v8 점수 | v9 점수 | 변화 | 코멘트 |
|---|---|---|---|---|
| CompanyContext 완성도 | 4.5 | **4.5** | 0 | v8과 동일, 변경 없음 |
| CandidateContext 완성도 | 4.5 | **4.5** | 0 | v8과 동일, 변경 없음 |
| MappingFeatures 완성도 | 4.5 | **4.5** | 0 | v8과 동일, 변경 없음 |
| Graph Schema 완성도 | 4.5 | **4.5** | 0 | v8과 동일, 변경 없음 |
| Evaluation Strategy | 4.5 | **4.7** | +0.2 | [M-2] alpha 미달 대응, [M-4] 처리량 표기 교정 |
| Crawling Strategy | 4.5 | **4.5** | 0 | [E-1] 참조 경로 교정 완료 |
| 문서 간 정합성 | 4.5 | **4.8** | +0.3 | A1~A7 전부 이관 완료, 참조 경로 일치, amendments가 사실상 아카이브로 전환 |
| **종합** | **4.5** | **4.6** | +0.1 | 파일럿 투입에 충분한 완성도. 잔여 이슈는 모두 비긴급 |

---

## 2. v8 리뷰 피드백 반영 상태

### 2.1 즉시 조치 — 2건

| # | v8 리뷰 항목 | v9 반영 상태 | 반영 위치 | 품질 |
|---|---|---|---|---|
| 1 | [E-1] 06 문서의 A6 참조 경로를 `01_company_context.md 2.2절`로 변경 | **반영 완료** | 06, 3.2절 N3 structural_tensions 기여 (~:558행) | 우수 — `01_company_context.md 2.2절`로 교정 완료 |
| 2 | [E-2] amendments A7도 A1~A6과 동일하게 이관 완료 처리 | **반영 완료** | 02_v4_amendments, A7절 | 우수 — "[v9] 통합판 이관 완료" + 정본 참조 안내. A8만 실질 내용 유지 (정당) |

### 2.2 파일럿 중 검토 — 2건

| # | v8 리뷰 항목 | v9 반영 상태 | 반영 위치 | 품질 |
|---|---|---|---|---|
| 3 | [M-2] Krippendorff's alpha < 0.6 대응 방안 | **반영 완료** | 05, Step 6 (~:154~158행) | 우수 — alpha 0.4~0.6 / alpha < 0.4 두 가지 시나리오 분리, 재교육→재평가→기준 재설계 단계적 에스컬레이션 구조 적절 |
| 4 | [M-4] Step 2 처리량 표기를 조건부 표기로 교정 | **반영 완료** | 05, Step 2 (~:128행) | 양호 — "~2시간 (임베딩 생성 포함) / 임베딩 사전 생성 완료 시 ~2초 (ANN 검색만)" 조건부 표기 |

**결과**: v8 리뷰의 4건 중 **4건 반영 완료 (100%)**.

---

## 3. 과도한 부분 (3건)

### [O-1] 02_v4_amendments.md의 존재 의의 약화 (심각도: 매우 낮음)

**현황**: A1~A7이 모두 "통합판 이관 완료"로 전환되었다. 실질 내용이 남은 것은 A8(추출 프롬프트 확장 로드맵) 하나뿐이다. 전체 146줄 중 A8이 ~65줄, 나머지 ~80줄은 이관 완료 안내 + 변경 요약 테이블이다.

**문제**: amendments 파일이 "변경 이력 아카이브"로 기능하고 있으나, 이 역할은 각 통합판 문서의 헤더에 이미 기록되어 있다. 하나 남은 A8도 06_crawling_strategy.md의 내용(2-8 태스크, A8 프롬프트 로드맵)과 중복 관계에 있다.

**권장**:
- A8의 내용을 06_crawling_strategy.md에 인라인 반영하고, amendments 파일 전체를 폐기하거나 순수 변경 이력 인덱스로 축소하는 것을 **v10에서 검토**
- 현재로서는 파일럿 진행에 영향 없으므로 비긴급

### [O-2] 05_evaluation_strategy.md의 10절 가상 데이터가 여전히 상세함 (심각도: 매우 낮음)

**현황**: v8에서 "가상 예시 데이터" 경고 배너가 추가되었으나, 가상 데이터의 분량 자체는 ~120줄(JSON 2건)로 여전히 상당하다.

**문제**: 실험 수행 전 문서에 가상 수치(Mean(A): 3.82, Cohen's d: 0.48 등)가 상세하게 기술되어 있으면, 읽는 사람이 무의식적으로 이 수치를 기대값이나 목표값으로 인식할 수 있다. 경고 배너만으로는 이를 충분히 방지하지 못할 수 있다.

**권장**: 가상 데이터를 **구조(스키마) 예시만** 남기고 수치를 `X.XX`나 `TBD`로 대체하는 것을 파일럿 시작 전 검토. 또는 가상 데이터를 별도 부록 파일로 분리.

### [O-3] 01_company_context.md의 T4 Tier ceiling 예외 Python 코드 (심각도: 매우 낮음)

**현황**: 1절(데이터 소스 Tier 정의)에 `get_category_ceiling()` Python 함수가 인라인으로 포함되어 있다(~:57~72행). 이 함수는 06_crawling_strategy.md 3.5절의 `CATEGORY_CEILING` 딕셔너리와 정합된다고 명시되어 있다.

**문제**: 동일 로직이 01(CompanyContext 스키마 정의)과 06(크롤링 전략)에 각각 Python 코드로 존재한다. 01은 스키마 정의 문서이므로 규칙의 **의미**를 기술하면 충분하고, 구현 코드는 06에만 있으면 된다.

**영향**: 미미. 코드가 짧고 두 곳 모두 정합되어 있다.

**권장**: 01의 Python 코드를 표/서술로 대체하고 "구현은 06 3.5절 참조"로 링크하는 것을 **비긴급으로 검토**.

---

## 4. 부족한 부분 (5건)

### [N-1] 05_evaluation_strategy.md: 50건 표본 크기의 통계적 검정력 부족 우려 (심각도: 중)

**현황**: 실험 설계에서 50건 매핑에 대해 Paired t-test (p < 0.05)를 수행한다. 성공 기준은 평균 적합도 점수 +0.5점(5점 척도)이다.

**문제**: 50건 Paired t-test로 0.5점 차이를 p < 0.05에서 탐지하려면, 표준편차(SD)에 따라 검정력(power)이 급격히 변한다.
- SD = 1.0 → Cohen's d ≈ 0.5, power ≈ 0.70 (부족)
- SD = 0.8 → Cohen's d ≈ 0.625, power ≈ 0.85 (적정)
- SD = 1.2 → Cohen's d ≈ 0.42, power ≈ 0.55 (매우 부족)

가상 데이터의 SD가 0.94~1.12 범위이므로, 실제로 power가 부족할 가능성이 높다. 이 경우 실제 차이가 존재해도 유의하지 않은 결과(Type II error)가 나올 수 있다.

**권장**:
1. **사전 검정력 분석(power analysis)** 섹션을 추가: 예상 SD 범위에서 50건이 충분한지 계산하고, 필요 시 표본 크기를 70~100건으로 상향하는 기준을 명시
2. 또는 **효과 크기(Cohen's d)를 주 판단 기준으로**, p-value를 보조 기준으로 사용하는 것을 명시 (소표본에서는 효과 크기가 더 유의미)
3. 최소한 05 문서 1절의 "성공 기준"에 "표본 크기 50건에서 power >= 0.80을 달성하지 못할 경우 표본 확대 검토"를 주석으로 추가

### [N-2] 03_mapping_features.md: F4(culture_fit)의 ALIGNMENT_LOGIC 매핑 불완전 (심각도: 낮음)

**현황**: F4 계산에서 `ALIGNMENT_LOGIC` 딕셔너리가 정의되어 있으나, 코드에 `# ...`으로 생략된 부분이 있다. 현재 명시된 것은 `speed_high × autonomy`, `process_high × process_tolerance`의 6개 조합뿐이다.

**문제**: 실제로는 3 facets × 3 levels × 3 preferences = 27가지 조합이 필요하다. 또한:
- `speed`와 `autonomy` 두 facet이 모두 `autonomy_preference`에 매핑되어 있어, `speed` facet과 `autonomy` facet의 구분이 모호하다
- `autonomy` facet이 `experiment_orientation`이나 `collaboration_style`과는 매핑되지 않는다
- `facet_level`이 `mid`인 경우의 매핑이 없다 (코드에서 `ALIGNMENT_LOGIC.get(key, 0.5)` 기본값으로 처리)

**영향**: v1에서 culture_fit은 대부분 INACTIVE(work_style_signals null 70%+)이므로 즉각적 영향은 적다. 그러나 v2에서 Closed-loop 질문으로 work_style_signals가 활성화되면 이 불완전한 매핑이 문제가 된다.

**권장**:
1. v1 파일럿 중에는 현재 상태 유지 (INACTIVE 비율이 높으므로)
2. v2 설계 시 `ALIGNMENT_LOGIC` 전체 27-cell 매트릭스를 완성하고, facet↔work_style 매핑의 1:1 원칙을 재검토
3. `speed`와 `autonomy`가 동일한 `autonomy_preference`에 매핑되는 이유를 설계 의도로 문서화하거나, 별도 work_style 필드(`speed_preference`)를 v2에서 도입

### [N-3] 04_graph_schema.md: Organization 노드에 크롤링 보강 속성 반영 미완 (심각도: 낮음)

**현황**: 06_crawling_strategy.md 5.4절에서 Organization 노드에 `product_description`, `market_segment`, `latest_funding_round` 등 크롤링 보강 속성을 추가한다고 정의했다. 그러나 04_graph_schema.md 1.2절의 Organization 노드 정의에는 이 속성들이 포함되어 있지 않다.

**문제**: 04는 Graph 스키마의 정본(source of truth)인데, 06에서 정의한 확장 속성이 04에 반영되지 않아 두 문서 사이 불일치가 존재한다. 04만 보고 Neo4j 스키마를 구현하면 크롤링 보강 속성이 누락된다.

**영향**: 크롤링 전략은 v1.1 이후 활성화되므로 v1 파일럿에 직접 영향은 없다. 다만 06의 "v6 크롤링 보강 후 확장 속성" Cypher가 04와 불일치하는 상태가 지속된다.

**권장**: 04_graph_schema.md의 Organization 노드 정의에 크롤링 보강 속성을 **optional** 표시로 추가하고, "v1.1 크롤링 활성화 시 사용" 주석을 달아 정합성 확보. 또는 04에 "v1.1 확장 속성" 서브섹션을 별도로 추가.

### [N-4] 전체: 데이터 파이프라인 오류 처리/모니터링 통합 뷰 부재 (심각도: 낮음)

**현황**: 각 문서가 독립적으로 실패 처리를 정의한다:
- 06: 크롤링 실패 처리 (NO_SITE, BLOCKED, SPA 실패 등)
- 03: 피처 계산 실패 (required inputs missing → INACTIVE)
- 05: 실험 실행 실패 (alpha 미달 대응)

**문제**: 전체 파이프라인(크롤링 → CompanyContext 생성 → MappingFeatures 계산 → 실험 평가)의 **end-to-end 오류 전파** 규칙이 어디에도 통합 정의되어 있지 않다. 예를 들어:
- 크롤링이 `NO_SITE`로 실패하면 → CompanyContext의 어떤 필드가 null이 되고 → MappingFeatures의 어떤 피처가 INACTIVE가 되는가?
- 이 연쇄적 degradation을 모니터링하는 대시보드 설계는?

**영향**: 파일럿 50건 규모에서는 수동 추적이 가능하지만, 1,000건+ 배치에서는 오류 전파 추적이 어려워진다.

**권장**: v1.1 또는 v2에서 별도 문서(`07_pipeline_monitoring.md` 등)로 오류 전파 맵과 모니터링 대시보드 설계를 추가. 파일럿에서는 각 문서의 실패 처리 규칙으로 충분.

### [N-5] 01_company_context.md / 02_candidate_context.md: 버전 넘버링 혼동 (심각도: 매우 낮음)

**현황**:
- 01 헤더: "CompanyContext v8 — 통합판", context_version: "4.0"
- 02 헤더: "CandidateContext v8 — 통합판", context_version: "4.0"
- 03 헤더: "MappingFeatures v8 — 통합판"
- 04 헤더: "통합 Graph 스키마 v8 — 통합판"
- 05 헤더: "GraphRAG vs Vector Baseline 비교 실험 계획 v9"
- 06 헤더: (별도 버전 표기 없음)

**문제**: 스키마 디렉토리는 `v9`인데, 대부분 문서의 헤더 버전은 `v8`이다. 05만 `v9`이고, 06은 버전 표기가 없다. `context_version`은 `4.0`으로 별도 체계를 사용한다. 세 가지 버전 넘버(디렉토리, 문서 헤더, JSON context_version)가 혼재한다.

**영향**: 실질적 혼동 가능성은 낮지만, "v9 스키마"를 참조할 때 어떤 버전 번호를 사용해야 하는지 불명확하다.

**권장**: 각 문서 헤더에 "디렉토리 버전: v9, 스키마 버전: v4"를 명시하는 메타 정보를 추가하거나, 문서 헤더 버전을 디렉토리와 일치시키는 규칙을 정립. **비긴급이지만 장기적으로 버전 혼동 방지를 위해 검토 필요**.

---

## 5. 잘된 부분 (4건)

### [P-1] amendments의 체계적 이관 완료

A1~A7 전부 "통합판 이관 완료"로 전환되어, 각 amendment의 정본이 어디인지 명확하다. 변경 이력도 1줄로 요약되어 있어 추적이 쉽다. 이는 여러 버전에 걸친 점진적 개선의 좋은 마무리다.

### [P-2] 05_evaluation_strategy.md의 alpha 미달 대응 방안

Krippendorff's alpha 미달 시나리오를 0.4~0.6 / < 0.4 두 단계로 나누고, 재교육→재측정→재설계의 에스컬레이션 경로를 명확히 정의했다. 실험 계획에서 흔히 빠지는 "실패 시 대응"이 잘 설계되어 있다.

### [P-3] 문서 간 정합성의 높은 수준

v3→v4→v5→v6→v7→v8→v9까지 9번의 반복을 거치며, 문서 간 참조(피처명, taxonomy, 임베딩 모델, evidence 구조 등)가 모두 정합되었다. 특히:
- 01의 tension_type enum ↔ 06의 N4 프롬프트 taxonomy: 일치
- 02의 scope_type ↔ 03의 F5 get_candidate_seniority(): 일치
- 04의 임베딩 모델 ↔ 05의 임베딩 모델: `text-multilingual-embedding-002`로 통일
- 01의 Evidence 통합 모델 ↔ 02/03/04의 evidence 구조: 일치

### [P-4] Graceful Degradation 설계의 일관성

전체 시스템에 걸쳐 "데이터 없으면 null, null이면 INACTIVE, INACTIVE이면 weight 재분배"의 패턴이 일관되게 적용되어 있다. 이는 v1처럼 데이터가 불완전한 초기 단계에서 시스템이 견고하게 작동할 수 있는 좋은 설계다.

---

## 6. 종합 권장사항

### 즉시 조치 (파일럿 시작 전)

없음. v9는 파일럿 투입에 충분한 완성도다.

### 파일럿 중 검토 (2건)

| # | 항목 | 심각도 | 대상 문서 | 조치 |
|---|---|---|---|---|
| M-1 | [N-1] 50건 표본 크기에 대한 사전 검정력 분석 추가 | 중 | 05 | power analysis 결과에 따라 표본 크기 조정 또는 효과 크기 기반 판단 기준 보완 |
| M-2 | [N-3] Organization 노드 크롤링 확장 속성 정합성 | 낮음 | 04, 06 | v1.1 크롤링 활성화 전에 04에 확장 속성 반영 |

### 비긴급 (v1.1 / v2에서 검토)

| # | 항목 | 대상 문서 | 시기 |
|---|---|---|---|
| L-1 | [O-1] amendments 파일 폐기 또는 축소 | 02_v4_amendments | v10 |
| L-2 | [O-2] 05 가상 데이터 수치 마스킹 | 05 | 파일럿 시작 전 선택 |
| L-3 | [O-3] 01의 인라인 Python 코드를 표/서술로 대체 | 01 | v10 |
| L-4 | [N-2] F4 ALIGNMENT_LOGIC 전체 매트릭스 완성 | 03 | v2 (Closed-loop 도입 시) |
| L-5 | [N-4] End-to-end 오류 전파 맵 설계 | 신규 문서 | v1.1 (배치 확대 시) |
| L-6 | [N-5] 버전 넘버링 체계 정리 | 전체 | v10 |

---

## 7. 결론

v9는 **v3부터 시작된 7차례 반복 개선의 안정화 지점**에 도달했다. v8 리뷰의 4건이 모두 반영되었고, 문서 간 정합성이 최고 수준이며, 즉시 조치가 필요한 결함이 없다.

잔여 이슈는 대부분 "과도한 부분의 경량화"(amendments 정리, 가상 데이터 축소)와 "장기 확장성"(power analysis, culture_fit 완성, 파이프라인 모니터링)에 해당하며, v1 파일럿 진행에 영향을 주지 않는다.

**가장 중요한 후속 조치**: [N-1] 표본 크기 검정력 분석. 이는 파일럿 결과의 통계적 신뢰성에 직접 영향을 미치므로 파일럿 실험 설계 확정 전에 수행해야 한다.
