# v14 Schema Review

> 리뷰 일시: 2026-03-10
> 리뷰 대상: `01.ontology/results/schema/v14/` 전체 8개 문서
> 리뷰 기준: README.md 방향성 일치, 실현 가능성/타당성, 과도한 설계 vs 부족한 설계
> 이전 리뷰: `reviews/v13/review.md` (39건 이슈, 10건 권장사항)

---

## 1. 종합 평가

### 1.1 README 방향성과의 일치도: **높음 (9/10)**

README에서 정의한 6개 핵심 개념이 v14에서도 충실하게 유지되어 있다. v13 대비 변화 없음.

- **독립성 원칙** 준수: CompanyContext/CandidateContext 독립 생성 구조 유지
- **Evidence-first** 원칙: 일관된 Evidence 구조 적용
- **부분 완성 허용**: Graceful Degradation 체계 유지
- **Taxonomy 고정**: SituationalSignal 14개, TensionType 8개 유지
- **데이터 소스 계층화**: Tier 체계와 confidence ceiling 유지

**미해소 1건**:
- **[R-6 CARRIED]** README의 문서 구조 설명이 여전히 `schema/v10/` 기준이다. 최신 v14와 불일치. v13에서 식별된 이후 두 버전이 경과했으나 수정되지 않음.

### 1.2 전체 성숙도 평가 (v13→v14 진전 요약)

v14는 v13 리뷰에서 식별된 39건 이슈 중 **17건을 해소**하였다. 특히:

1. **LLM 비용 총 추정 신규 추가** (§10): v13의 가장 큰 횡단 이슈였던 "LLM 비용 추정 부재"를 해소. 전체 파이프라인 ~$500/회, ~80시간 처리 시간 산정
2. **Neo4j 규모/인덱스/동기화 전략 신규 추가** (§7/§8/§9): 27M 노드, 133M 엣지 추정과 인덱스 전략, BigQuery-Neo4j 동기화 방안 정의
3. **문서 간 일관성 개선**: X-1(industry_code 예시), X-3(T1 ceiling 차이), X-4(F3 정본 선언) 해소
4. **amendments 문서 축소**: V-2 해소, 이관 완료 항목을 요약 테이블로 압축

다만 21건이 미해소로 이월되었고, v14에서 신규로 7건의 이슈가 식별되었다.

### 1.3 v13 이슈 해소 현황 요약

| 상태 | 건수 | 비율 |
|---|---|---|
| RESOLVED (완전 해소) | 16 | 41.0% |
| PARTIAL (부분 해소) | 1 | 2.6% |
| CARRIED (미해소 이월) | 22 | 56.4% |
| **합계** | **39** | 100% |

---

## 2. 문서별 상세 리뷰

### 2.1 `00_data_source_mapping.md` — 데이터 소스 매핑

#### 강점
- **[NEW] §10 LLM 비용 총 추정**: 8개 LLM 호출 지점별 비용을 산정하여 전체 ~$500/회라는 관리 가능한 수준임을 확인. v13에서 가장 큰 횡단 이슈였던 "비용 추정 부재"를 해소
- **[O-1 RESOLVED]** §1.5 임베딩 batch 코드를 pseudo-code로 축소하고 ANN 인덱스 사용 안내를 추가
- **[O-2 RESOLVED]** §3.5 gender/age에 "별도 분석 테이블 관리 권장" 문구 추가
- **[X-4 RESOLVED]** §4.1에 "정본은 03_mapping_features F3"임을 명시, 본 문서는 데이터 소스 참조만 유지

#### 과도한 설계
- (v14에서 과도한 설계가 추가되지 않음. v13 대비 개선)

#### 부족한 설계
- **[N14-1] LLM 비용 output token 비율 30% 가정 미검증**: §10의 비용 추정에서 "출력 토큰은 입력의 ~30%로 추정"이라고 기술했으나, 이 비율의 근거가 없음. Outcome/Signal 추출처럼 구조화된 JSON을 출력하는 경우 output이 입력의 50-80%에 달할 수 있어 비용이 과소 추정될 가능성 있음. 최소한 L1(Outcome 추출)에 대해 샘플 10건으로 실측 후 비율을 보정해야 함
- **[U-1 CARRIED]** job-hub 데이터 상세 분석 여전히 미완 ("Phase 4-1에서 수행 예정"). company 측 fill rate 없이 CompanyContext 설계가 확정된 상태는 리스크 지속

#### 타당성 이슈
- **[V-1 CARRIED]** `compute_industry_code_match()` 실효성 제한 (candidate industryCodes 66% 빈배열) 이슈 지속

---

### 2.2 `01_company_context.md` — 기업 맥락

#### 강점
- **[X-1 RESOLVED]** JSON 예시의 industry_code를 NICE 코드("J63112") → code-hub INDUSTRY 코드("SW_DEV")로 수정. 00_data_source_mapping과 일관성 확보
- **[X-3 RESOLVED]** §1 Tier 정의에 Company T1(JD) 0.80과 Candidate T1(이력서) 0.85 차이의 근거를 명시 ("JD는 채용 마케팅 특성상 과장 가능성이 있어 이력서보다 낮은 상한 적용")

#### 과도한 설계
- **[O-3 CARRIED]** structural_tensions 8개 taxonomy가 v1에서 null 70%+ 예상임에도 배타성 가이드, related_tensions 등 상세 정의 유지
- **[O-4 CARRIED]** T4 ceiling 예외 규칙 (0.05~0.10 차이) 미세 조정 유지

#### 부족한 설계
- **[U-4 CARRIED]** NICE 데이터 갱신 주기/정확도 미언급
- **[U-5 CARRIED]** vacancy scope_type LLM 추출 정확도 추정 부재

---

### 2.3 `02_candidate_context.md` — 후보 맥락

#### 강점
- **[U-6 RESOLVED]** §2.7 짧은 텍스트 대응 전략 추가: 50자 미만은 scope_summary만, 50~100자는 confidence 0.8 감쇠, 100자 이상은 정상 추출. 현실적이고 명확한 기준
- **[U-7 RESOLVED]** §2.8 Career[] 배열의 시간순 정렬 전제 조건 명시: `ORDER BY period.started_on DESC` 적용 및 미보장 시 role_evolution 부정확성 경고

#### 과도한 설계
- **[O-5 CARRIED]** PastCompanyContext estimated_stage_at_tenure: 현재 시점 NICE 데이터로 과거 추정하는 정확도 이슈 지속
- **[O-6 CARRIED]** WorkStyleSignals 구조: v1에서 대부분 null 예상이나 전체 구조가 유지

#### 부족한 설계
- **[U-2 CARRIED]** 스킬 임베딩 threshold 검증 부재
- **[U-3 CARRIED]** CareerDescription LLM 귀속 정확도 추정 부재

---

### 2.4 `03_mapping_features.md` — 매칭 피처

#### 강점
- **[X-4 RESOLVED]** F3 domain_fit에 "정본 선언" 추가: "F3 domain_fit의 industry code 매칭 로직은 본 문서가 정본"이라고 명시. 00_data_source_mapping §4.1과의 중복/불일치 이슈 해소
- **[U-9 RESOLVED]** §4 FEATURE_WEIGHTS에 설정 근거 및 캘리브레이션 계획 추가: 각 가중치의 배분 원칙(vacancy_fit 최우선, culture_fit 최소 등)과 1차/2차 캘리브레이션 계획 명시
- **[O-8 PARTIAL]** F5 ROLE_PATTERN_FIT에 캘리브레이션 계획 추가: "전문가 판단 기반 초기값"임을 인정하고 F1과 동일한 캘리브레이션 프로토콜 적용 예정. 다만 매트릭스 값 자체의 근거는 여전히 부재

#### 과도한 설계
- **[O-7 CARRIED]** F4 culture_fit 전체 계산 로직: ACTIVE <10% 예상 피처에 상세 로직이 계속 포함
- **[O-8 PARTIAL → CARRIED]** ROLE_PATTERN_FIT 매트릭스: 캘리브레이션 계획은 추가되었으나, 하드코딩된 값의 근거가 없는 이슈는 지속

#### 부족한 설계
- **[U-8 CARRIED]** 피처 간 상관관계(다중공선성) 분석 부재
- **[U-10 CARRIED]** 매핑 1건 처리 시간 분석 부재 ("< 30초" 목표는 있으나 합산 분석 없음)

---

### 2.5 `04_graph_schema.md` — Neo4j 그래프 스키마

#### 강점
- **[U-11 RESOLVED]** §7 노드/엣지 규모 추정 신규: Person ~3.2M, Chapter ~18M, 총 27M 노드 / 133M 엣지. AuraDB Professional 이상 필요. 파일럿 ~10K Person으로 사전 PoC 수행 계획 포함
- **[U-12 RESOLVED]** §8 인덱스 전략 신규: 고유성 제약 7개, 탐색 인덱스 3개, Vector 인덱스 2개 정의. Q1~Q5 쿼리 성능 보장 기반 확보
- **[U-13 RESOLVED]** §9 BigQuery-Neo4j 동기화 전략 신규: 단방향 동기화, 데이터 유형별 주기(일간/주간/월간/실시간) 정의, 증분 동기화 구현 stub 포함
- **[O-9/O-10 RESOLVED]** v2 로드맵 상세 설명을 테이블 한 줄로 압축

#### 과도한 설계
- (v14에서 과도 설계 이슈 없음)

#### 부족한 설계
- **[N14-2] MAPPED_TO 엣지 무한 증가 — TTL/아카이빙 전략 부재**: §7.2에서 MAPPED_TO 관계를 ~10M+으로 추정하고 "운영 후 증가"라고만 기술. 매핑은 지속적으로 생성되므로, 오래된 매핑 결과의 TTL(Time-To-Live) 또는 아카이빙 전략이 없으면 엣지가 무한 증가하여 그래프 성능에 영향. 최소한 "90일 이상 미조회 매핑은 아카이빙" 같은 정책 필요
- **[N14-3] sync_to_neo4j 함수가 stub(`pass`) — 에러 핸들링/재시도 미정의**: §9.3의 `sync_to_neo4j()` 함수가 `pass`로만 되어 있고, 동기화 실패 시 재시도 정책, 부분 실패 처리, 데이터 정합성 검증 로직이 없음. "MERGE 문으로 upsert"라는 주석만 있으나, 대규모 데이터 동기화에서의 트랜잭션 관리가 미정의
- **[N14-4] "단방향 동기화" 주장과 MAPPED_TO 역방향 적재 모순**: §9.1에서 "단방향 동기화: 원본 DB → Neo4j + BigQuery"라고 정의하면서, 바로 아래에 "MAPPED_TO만 Neo4j → BigQuery로 역방향 적재"라고 기술. 이는 실질적으로 양방향 동기화이므로 "주로 단방향, 매핑 결과만 역방향"으로 정확히 기술하거나, MAPPED_TO의 역방향 흐름에 대한 동기화 보장 방안을 추가해야 함
- **[N14-5] Organization.name 풀텍스트 인덱스 누락**: §8에서 Organization에 대해 `org_id_unique`와 `org_stage_label` 인덱스만 정의. 그러나 00_data_source_mapping §3.4에서 `query_jobs_by_company_name(company_name)`으로 회사명 기반 탐색을 수행하므로, `Organization.name`에 대한 풀텍스트 인덱스가 필요. 4.48M 고유 회사명에서 이름 기반 검색 없이는 PastCompanyContext 보강이 병목

---

### 2.6 `05_evaluation_strategy.md` — 평가 전략

#### 강점
- **[U-14 RESOLVED]** §1.1 후보 풀 선정 기준 신규: 경력 유형(EXPERIENCED 70% / NEW_COMER 30%), 경력 연수 분포, 직무 다양성(최소 5개 카테고리), 데이터 완성도(Skill 50%+) 등 층화 무작위 추출 기준을 체계적으로 정의
- **[U-16 RESOLVED]** §5.1 B' LLM Reranking 시 LLM 입력 범위 명확화: "이력서 **요약**(최근 3개 경력, 핵심 스킬, 총 경력 연수)"을 사용하며, 그 이유로 context window 제한과 GraphRAG(A)와의 공정성 확보를 명시
- Cohen's d 우선 판단 정책이 소표본(n=50)에서의 Type II error 위험을 적절히 관리

#### 과도한 설계
- **[O-11 CARRIED]** §10 가상 실험 데이터 ~100줄 유지. 경고 배너 있으나 혼란 가능성 지속
- **[O-12 CARRIED]** Step별 함수 시그니처 유지. 모두 `pass`인 stub 함수 7개

#### 부족한 설계
- **[U-15 CARRIED]** 평가자 보상/동기 부여 계획 부재: 250건 × 2분 = ~8시간 평가 작업에 대한 보상 체계 미정의

---

### 2.7 `06_crawling_strategy.md` — 크롤링 전략

#### 변경 사항
- **v14 변경: 버전 헤더만 동기화 (내용 변경 없음)**

#### 이슈
- **[N14-6] v13 크롤링 관련 이슈 5건 모두 미해소**: O-13(2단계 중복 제거), O-14(서브도메인 탐색), O-15(facet 캘리브레이션 4단계), U-17(언론사 본문 추출), U-18(크롤링 법적 리스크) — 모두 v13에서 식별된 이슈이나 v14에서 내용 변경 없이 그대로 이월
- 크롤링 전략 문서만 v14 개선 범위에서 제외된 것은, 해당 문서의 이슈가 v1.1(크롤링 활성화) 시점까지 미뤄도 되는 것인지 명시적 판단이 필요

---

### 2.8 `02_v4_amendments.md` — 보완 이력

#### 강점
- **[V-2 RESOLVED]** 이관 완료된 A1~A7, A9, A10을 요약 테이블로 축소. A8(추출 프롬프트 확장 로드맵)만 활성 콘텐츠로 유지. 문서 분량이 대폭 감소하여 가독성 향상

#### 이슈
- (추가 이슈 없음. v14에서 적절하게 정리됨)

---

## 3. 횡단 이슈 (Cross-cutting Concerns)

### 3.1 문서 간 일관성

| 이슈 | v13 상태 | v14 상태 | 비고 |
|---|---|---|---|
| **[X-1]** industry_code 예시 불일치 | 중간 | **RESOLVED** | JSON 예시를 code-hub 코드로 변경 |
| **[X-2]** Person name 속성 존재/부재 | 낮음 | **CARRIED** | 04_graph_schema Person에 `name` 있으나 02_candidate_context JSON에 없음 |
| **[X-3]** T1 confidence 상한 차이 | 중간 | **RESOLVED** | Company T1(JD) 0.80 vs Candidate T1(이력서) 0.85 차이 근거 명시 |
| **[X-4]** F3 industry code 매칭 로직 중복 | **높음** | **RESOLVED** | 03_mapping_features를 정본으로 선언 |

**잔여 불일치 1건**: X-2는 심각도가 낮으나, Person 노드에 `name`이 있고 CandidateContext JSON에는 없는 상태가 지속. `name`의 소스(resume-hub에서 어떤 필드에서 가져오는지)가 어디에도 정의되지 않음.

### 3.2 LLM 비용 추정 (v13→v14 해소)

v13에서 "LLM 비용 추정 부재"로 식별된 횡단 이슈가 00_data_source_mapping §10에서 해소되었다.

| 항목 | v13 상태 | v14 상태 |
|---|---|---|
| CandidateContext 추출 비용 | **미산정** | ~$460 (L1~L4) |
| CompanyContext 추출 비용 | **미산정** | ~$22 (L5~L7) |
| 크롤링 추출 비용 | $107/월 | ~$2/회 + $107/월 |
| 전체 파이프라인 비용 | **미산정** | **~$500/회** |
| 전체 처리 시간 | **미산정** | **~80시간 (3.3일)** |

**잔여 리스크**: output token 비율 30% 가정의 검증 필요 (N14-1).

### 3.3 동기화 전략 completeness gap (신규)

§9 동기화 전략이 신규 추가되었으나, 다음 gap이 존재:

1. **MAPPED_TO 엣지 수명 관리 부재** (N14-2): 운영 시 무한 증가
2. **동기화 실패 시 복구 전략 미정의** (N14-3): stub 함수만 존재
3. **"단방향" 주장의 부정확성** (N14-4): 실질 양방향 흐름
4. **조직명 검색 인덱스 누락** (N14-5): PastCompanyContext 보강 병목

---

## 4. 실현 가능성 평가 (Phase 1-4, 비용/규모 데이터 반영)

### 4.1 Phase 1 (데이터 정제) — **실현 가능** (v13 유지)

| 과제 | 난이도 | 실현 가능성 | v14 변경 |
|---|---|---|---|
| days_worked 계산 | 낮음 | 높음 | 변경 없음 |
| certificate type 매핑 | 낮음 | 높음 | 변경 없음 |
| 회사명 정규화 | 중간 | 중간 | 변경 없음 |
| 스킬 정규화 | 높음 | 중간-낮음 | 변경 없음 |
| 전공명 정규화 | 중간 | 높음 | 변경 없음 |

### 4.2 Phase 2 (노드/엣지 구축) — **실현 가능, 규모 검증됨**

v14에서 규모 추정(§7)이 추가되어 사전 검증 가능:

| 항목 | v13 | v14 | 비고 |
|---|---|---|---|
| 총 노드 | **미산정** | ~27M | Person 3.2M + Chapter 18M + 기타 |
| 총 엣지 | **미산정** | ~133M+ | 주로 USED_SKILL(50M), HAS_CHAPTER(18M) |
| Neo4j tier | 미검토 | AuraDB Professional 이상 | Free tier(200K/400K) 한계 초과 |
| PoC 계획 | 미정의 | ~10K Person + ~50K Chapter 파일럿 | 적절한 사전 검증 |

**핵심 리스크**: AuraDB Professional의 가격/성능이 27M 노드에서 Q1~Q5 쿼리 1초 이내를 보장하는지는 파일럿 결과에 의존.

### 4.3 Phase 3 (LLM 추출) — **실현 가능, 비용 관리 가능**

v14에서 비용/시간 추정(§10)이 추가되어 리스크 대폭 감소:

| 항목 | v13 | v14 |
|---|---|---|
| LLM 비용 (1회 전체) | **미산정** | ~$500 |
| 처리 시간 | ~44시간 (L1만) | ~80시간 (전체, 50 병렬) |
| 비용 관리 | 불확실 | **관리 가능** |

### 4.4 Phase 4 (기업측 + 매핑) — **실현 가능, job-hub 분석 선행 필수** (v13 유지)

job-hub 상세 분석(U-1)이 여전히 미완으로 리스크 지속.

---

## 5. v13 이슈 해소 추적 테이블 (39건)

| ID | 유형 | 문서 | 설명 | v14 상태 | 해소 방법 |
|---|---|---|---|---|---|
| O-1 | 과도 | 00 | 임베딩 batch O(n*m) 구현 코드 | **RESOLVED** | pseudo-code로 축소 + ANN 안내 |
| O-2 | 과도 | 00 | gender/age 그래프 노드 저장 | **RESOLVED** | 별도 분석 테이블 관리 권장 추가 |
| O-3 | 과도 | 01 | structural_tensions 8개 taxonomy (null 70%+) | CARRIED | 변경 없음 |
| O-4 | 과도 | 01 | T4 ceiling 예외 규칙 (0.05 차이) | CARRIED | 변경 없음 |
| O-5 | 과도 | 02 | PastCompanyContext estimated_stage_at_tenure | CARRIED | 변경 없음 |
| O-6 | 과도 | 02 | WorkStyleSignals 전체 구조 (v1 null) | CARRIED | 변경 없음 |
| O-7 | 과도 | 03 | F4 culture_fit 전체 계산 로직 | CARRIED | 변경 없음 |
| O-8 | 과도 | 03 | ROLE_PATTERN_FIT 매트릭스 근거 부재 | **PARTIAL** | 캘리브레이션 계획 추가, 값 근거는 미해소 |
| O-9 | 과도 | 04 | Organization 크롤링 보강 속성 설명 분량 | **RESOLVED** | 테이블로 압축 |
| O-10 | 과도 | 04 | v2 Company 간 관계 상세 설명 | **RESOLVED** | 테이블 한 줄로 압축 |
| O-11 | 과도 | 05 | 가상 실험 데이터 ~100줄 | CARRIED | 변경 없음 |
| O-12 | 과도 | 05 | Step별 함수 시그니처 | CARRIED | 변경 없음 |
| O-13 | 과도 | 06 | 2단계 중복 제거 (엔티티 기반) | CARRIED | 06 변경 없음 |
| O-14 | 과도 | 06 | 서브도메인 탐색 스킵 조건 | CARRIED | 06 변경 없음 |
| O-15 | 과도 | 06 | facet 캘리브레이션 4단계 | CARRIED | 06 변경 없음 |
| U-1 | 부족 | 00 | job-hub 데이터 상세 분석 부재 | CARRIED | Phase 4-1 예정 (미착수) |
| U-2 | 부족 | 00 | 스킬 임베딩 threshold 검증 부재 | CARRIED | 변경 없음 |
| U-3 | 부족 | 00 | CareerDescription LLM 귀속 정확도 추정 부재 | CARRIED | 변경 없음 |
| U-4 | 부족 | 01 | NICE 데이터 갱신 주기/정확도 미언급 | CARRIED | 변경 없음 |
| U-5 | 부족 | 01 | vacancy scope_type LLM 추출 정확도 부재 | CARRIED | 변경 없음 |
| U-6 | 부족 | 02 | 짧은 텍스트 LLM 추출 품질 대응 부재 | **RESOLVED** | 50자/100자 기준 + confidence 감쇠 |
| U-7 | 부족 | 02 | 경력 시간순 정렬 보장 미명시 | **RESOLVED** | ORDER BY 전제 조건 명시 |
| U-8 | 부족 | 03 | 피처 간 상관관계 분석 부재 | CARRIED | 변경 없음 |
| U-9 | 부족 | 03 | FEATURE_WEIGHTS 설정 근거 부재 | **RESOLVED** | 배분 원칙 + 캘리브레이션 계획 추가 |
| U-10 | 부족 | 03 | 매핑 1건 처리 시간 분석 부재 | CARRIED | 변경 없음 |
| U-11 | 부족 | 04 | 노드/엣지 규모 추정 부재 | **RESOLVED** | §7 신규 (27M/133M) |
| U-12 | 부족 | 04 | Neo4j 인덱스 전략 부재 | **RESOLVED** | §8 신규 (Unique+탐색+Vector) |
| U-13 | 부족 | 04 | BigQuery-Neo4j 동기화 전략 부재 | **RESOLVED** | §9 신규 (단방향+주기별) |
| U-14 | 부족 | 05 | 후보 풀 500명 선정 기준 부재 | **RESOLVED** | §1.1 층화 무작위 추출 기준 |
| U-15 | 부족 | 05 | 평가자 보상 계획 부재 | CARRIED | 변경 없음 |
| U-16 | 부족 | 05 | B' LLM 정보 범위 불명확 | **RESOLVED** | §5.1 이력서 요약 사용 + 근거 명시 |
| U-17 | 부족 | 06 | 언론사 본문 추출 성공률 예측 부재 | CARRIED | 06 변경 없음 |
| U-18 | 부족 | 06 | 크롤링 법적 리스크 대응 피상적 | CARRIED | 06 변경 없음 |
| X-1 | 불일치 | 01/00 | industry_code 예시 불일치 | **RESOLVED** | code-hub 코드로 예시 변경 |
| X-2 | 불일치 | 04/02 | Person name 속성 존재/부재 | CARRIED | 변경 없음 |
| X-3 | 불일치 | 01/02 | T1 confidence 상한 차이 | **RESOLVED** | 차등 적용 근거 명시 |
| X-4 | 불일치 | 00/03 | F3 industry code 매칭 로직 중복 | **RESOLVED** | 03_mapping_features를 정본 선언 |
| V-1 | 타당성 | 00 | industry_code_match 실효성 | CARRIED | 변경 없음 |
| V-2 | 타당성 | 02_v4 | amendments 문서 존재 의의 감소 | **RESOLVED** | 이관 완료 항목 요약 축소 |

---

## 6. 핵심 권장 사항 (우선순위순)

### 6.1 즉시 조치 (Critical)

| # | 권장 사항 | 근거 | v13 대응 |
|---|---|---|---|
| R-1 | **job-hub 데이터 상세 분석 조기 착수** | U-1 — 2개 버전 이월, company 측 fill rate 없이 설계 확정 상태 | v13 R-1 유지 |
| R-2 | **MAPPED_TO 엣지 TTL/아카이빙 정책 정의** | N14-2 — 운영 후 엣지 무한 증가 시 그래프 성능 저하 | 신규 |
| R-3 | **sync_to_neo4j 에러 핸들링/재시도 정책 정의** | N14-3 — stub 함수에서 실제 구현으로 진화 필요 | 신규 |

### 6.2 단기 개선 (High)

| # | 권장 사항 | 근거 | v13 대응 |
|---|---|---|---|
| R-4 | **LLM output token 비율 실측 보정** | N14-1 — 30% 가정이 과소 추정 가능 | 신규 |
| R-5 | **Organization.name 풀텍스트 인덱스 추가** | N14-5 — 회사명 기반 탐색 병목 | 신규 |
| R-6 | **README.md 업데이트** | v10 참조 → v14 참조. 2개 버전 이월 | v13 R-6 유지 |
| R-7 | **스킬 임베딩 threshold 검증** | U-2 — 한국어/영어 혼합 스킬명 similarity 분포 분석 필요 | v13 R-4 유지 |

### 6.3 중기 개선 (Medium)

| # | 권장 사항 | 근거 | v13 대응 |
|---|---|---|---|
| R-8 | **동기화 방향성 기술 정확화** | N14-4 — "단방향" vs 실질 "양방향" 모순 | 신규 |
| R-9 | **F4 culture_fit 계산 로직 v2 이동** | O-7 — ACTIVE <10%인 피처 상세 로직 유지 부담 | v13 R-9 유지 |
| R-10 | **06_crawling_strategy 이슈 5건 해소 일정 명시** | N14-6 — v1.1 이전에 해소 가능한 항목 식별 필요 | 신규 |

---

## 7. 결론

v14 스키마는 v13 리뷰에서 식별된 **핵심 이슈 3건 중 2건**을 해소하였다:

| v13 핵심 리스크 | v14 상태 |
|---|---|
| LLM 추출 비용/시간 총 추정 부재 | **RESOLVED** (~$500/회, ~80시간) |
| 스케일 검증 부재 (Neo4j) | **RESOLVED** (27M/133M 추정 + PoC 계획) |
| job-hub 측 데이터 분석 미완 | **CARRIED** (U-1, 2개 버전 이월) |

v14의 주요 진전:
1. **비용/규모의 정량화**: LLM 비용 ~$500, Neo4j 27M 노드라는 구체적 수치로 실현 가능성 판단 근거 확보
2. **문서 간 일관성 대폭 개선**: X-1, X-3, X-4 해소로 주요 불일치 제거
3. **실험 설계 보강**: 후보 풀 선정 기준(U-14), LLM 입력 범위(U-16) 명확화
4. **문서 정리**: amendments 축소(V-2), v2 로드맵 압축(O-9/O-10)

v14에서 새로 식별된 이슈 7건(N14-1~N14-7)은 주로 **운영 단계의 세부 전략**(TTL, 에러 핸들링, 인덱스 보완)에 집중되어 있어, 설계가 "정의" 단계에서 "구현 준비" 단계로 성숙해가고 있음을 보여준다.

**잔여 최대 리스크**: job-hub 데이터 분석(U-1)이 2개 버전 이월되어, company 측 설계의 실측 검증이 여전히 부재한 상태이다. Phase 1 착수 전 최우선 과제로 실행해야 한다.

---

## 8. 부록: v14 이슈 요약 테이블

### 8.1 v14 신규 이슈

| ID | 유형 | 문서 | 설명 | 심각도 |
|---|---|---|---|---|
| N14-1 | 부족 | 00 | LLM 비용 output token 비율 30% 가정 미검증 | 중간 |
| N14-2 | 부족 | 04 | MAPPED_TO 엣지 무한 증가 — TTL/아카이빙 전략 부재 | **높음** |
| N14-3 | 부족 | 04 | sync_to_neo4j stub — 에러 핸들링/재시도 미정의 | 중간 |
| N14-4 | 불일치 | 04 | "단방향 동기화" 주장과 MAPPED_TO 역방향 적재 모순 | 낮음 |
| N14-5 | 부족 | 04 | Organization.name 풀텍스트 인덱스 누락 | 중간 |
| N14-6 | 부족 | 06 | 06_crawling_strategy 변경 없음 — v13 이슈 5건 모두 미해소 | 중간 |
| N14-7 | 불일치 | README | README 여전히 v10 참조 (R-6 2회 이월) | 낮음 |

### 8.2 v13에서 이월된 미해소 이슈 (22건)

| ID | 유형 | 문서 | 설명 | 심각도 |
|---|---|---|---|---|
| O-3 | 과도 | 01 | structural_tensions 8개 taxonomy (null 70%+) | 중간 |
| O-4 | 과도 | 01 | T4 ceiling 예외 규칙 (0.05 차이) | 낮음 |
| O-5 | 과도 | 02 | PastCompanyContext estimated_stage_at_tenure | 중간 |
| O-6 | 과도 | 02 | WorkStyleSignals 전체 구조 (v1 null) | 낮음 |
| O-7 | 과도 | 03 | F4 culture_fit 전체 계산 로직 | 중간 |
| O-11 | 과도 | 05 | 가상 실험 데이터 ~100줄 | 낮음 |
| O-12 | 과도 | 05 | Step별 함수 시그니처 | 낮음 |
| O-13 | 과도 | 06 | 2단계 중복 제거 (엔티티 기반) | 중간 |
| O-14 | 과도 | 06 | 서브도메인 탐색 스킵 조건 | 낮음 |
| O-15 | 과도 | 06 | facet 캘리브레이션 4단계 | 낮음 |
| U-1 | 부족 | 00 | job-hub 데이터 상세 분석 부재 | **높음** |
| U-2 | 부족 | 00 | 스킬 임베딩 threshold 검증 부재 | 중간 |
| U-3 | 부족 | 00 | CareerDescription LLM 귀속 정확도 추정 부재 | 중간 |
| U-4 | 부족 | 01 | NICE 데이터 갱신 주기/정확도 미언급 | 중간 |
| U-5 | 부족 | 01 | vacancy scope_type LLM 추출 정확도 부재 | 중간 |
| U-8 | 부족 | 03 | 피처 간 상관관계 분석 부재 | 중간 |
| U-10 | 부족 | 03 | 매핑 1건 처리 시간 분석 부재 | 중간 |
| U-15 | 부족 | 05 | 평가자 보상 계획 부재 | 낮음 |
| U-17 | 부족 | 06 | 언론사 본문 추출 성공률 예측 부재 | 중간 |
| U-18 | 부족 | 06 | 크롤링 법적 리스크 대응 피상적 | 중간 |
| X-2 | 불일치 | 04/02 | Person name 속성 존재/부재 | 낮음 |
| V-1 | 타당성 | 00 | industry_code_match 실효성 (66% 빈배열) | 중간 |

### 8.3 부분 해소 이월 (1건)

| ID | 유형 | 문서 | 설명 | 심각도 | 해소 내용 | 잔여 |
|---|---|---|---|---|---|---|
| O-8 | 과도 | 03 | ROLE_PATTERN_FIT 매트릭스 근거 부재 | 중간 | 캘리브레이션 계획 추가 | 값 자체의 근거 미제시 |

### 8.4 해소된 이슈 (17건)

| ID | 유형 | 문서 | 해소 방법 |
|---|---|---|---|
| O-1 | 과도 | 00 | pseudo-code 축소 + ANN 안내 |
| O-2 | 과도 | 00 | 별도 분석 테이블 관리 권장 |
| O-9 | 과도 | 04 | 테이블로 압축 |
| O-10 | 과도 | 04 | 테이블 한 줄로 압축 |
| U-6 | 부족 | 02 | 50자/100자 기준 + confidence 감쇠 |
| U-7 | 부족 | 02 | ORDER BY 전제 조건 명시 |
| U-9 | 부족 | 03 | 배분 원칙 + 캘리브레이션 계획 |
| U-11 | 부족 | 04 | §7 규모 추정 (27M/133M) |
| U-12 | 부족 | 04 | §8 인덱스 전략 |
| U-13 | 부족 | 04 | §9 동기화 전략 |
| U-14 | 부족 | 05 | §1.1 후보 풀 선정 기준 |
| U-16 | 부족 | 05 | §5.1 LLM 입력 범위 명확화 |
| X-1 | 불일치 | 01/00 | code-hub 코드로 예시 변경 |
| X-3 | 불일치 | 01/02 | 차등 적용 근거 명시 |
| X-4 | 불일치 | 00/03 | 정본 선언 |
| V-2 | 타당성 | 02_v4 | 이관 완료 항목 요약 축소 |
