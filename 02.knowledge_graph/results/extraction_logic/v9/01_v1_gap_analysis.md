# v1 계획 Gap 분석 — v11 온톨로지 대비

> v1 계획이 v11 온톨로지 요구사항에 맞지 않는 부분을 식별하고, v2/v3~v8에서 수정한 방향을 정리한다.
>
> 작성일: 2026-03-08 (v2 기반)
> 개정일: 2026-03-08 (v6 — v10 온톨로지 교차 검증 반영)
> 개정일: 2026-03-08 (v7 — LLM 파싱 실패 전략, Sonnet fallback 시나리오, 오케스트레이션/타임라인 현실화, 리스크 보강)
> 개정일: 2026-03-09 (v8 — 데이터모델 기반 추출 파이프라인 재설계: resume-hub/job-hub/code-hub DB 기반으로 전환)
> 개정일: 2026-03-09 (v9 — v11 온톨로지 정합: 3-Tier 비교 전략 통일, 00_data_source_mapping.md 참조 반영, synonyms 매칭 추가, confidence 세분화)

---

## 1. 근본적 목적 불일치

| 항목 | v1 계획 | v10 온톨로지 요구 | Gap |
|---|---|---|---|
| **목표** | 이력서에서 범용 KG 추출 (NER/RE) | Chapter-Trajectory 기반 맥락 매칭 시스템 구축 | **방향 자체가 다름** |
| **스키마** | Person, Org, Skill, Role, Experience (범용) | Person, Chapter, SituationalSignal, Outcome, Vacancy, Organization, Industry (도메인 특화) | **노드 9개 중 5개 누락** |
| **데이터 소스** | 이력서 150GB만 | JD + NICE + 이력서 + (크롤링/투자DB) | **기업 측 데이터 파이프라인 부재** |
| **최종 산출물** | Entity + Relation triples | CompanyContext JSON + CandidateContext JSON + Graph + MappingFeatures + MAPPED_TO 관계 | **매핑 레이어 전체 누락** |

---

## 2. 스키마 수준 Gap 상세

### 2.1 v1에 없는 v10 핵심 노드/개념

| v10 노드/개념 | v10에서의 역할 | v1 대응 | Gap 심각도 |
|---|---|---|---|
| `Chapter` (경험 단위) | 이력서의 각 경력을 구조화 — scope_type, outcomes, signals 포함 | `Experience` (단순 기간+회사+역할) | **Critical** — v10의 핵심 |
| `SituationalSignal` | 14개 taxonomy 기반 상황 라벨, 유사 경험 후보 연결 | 없음 | **Critical** |
| `Outcome` | 정량/정성 성과, metric_value 포함 | 없음 | **High** |
| `Vacancy` | JD 기반 채용 포지션 — scope_type, seniority, REQUIRES_ROLE 관계 | 없음 | **Critical** — 매칭의 기업 측 앵커 |
| `Industry` | NICE 업종 코드 기반 마스터 데이터, IN_INDUSTRY 관계 | 없음 | **High** — v10에서 추가 (v7) |
| `operating_model` | 기업 운영 방식 (v1: speed/autonomy/process 3 facets) | 없음 | **High** |
| `stage_estimate` | 기업 성장 단계 (EARLY/GROWTH/SCALE/MATURE) | 없음 | **High** |
| `PastCompanyContext` | 후보 재직 당시 회사 맥락 (NICE 역산) | 없음 | **High** |
| `role_evolution` | 커리어 성장 패턴 (IC_TO_LEAD 등) | 없음 | **Medium** |
| `work_style_signals` | 후보 업무 스타일 신호 (autonomy, process, experiment_orientation, collaboration_style) | 없음 | **Medium** (v1에서 대부분 null) |
| `MAPPED_TO` 관계 | Vacancy→Person 매핑 결과를 Graph에 반영 | 없음 | **High** — v10에서 추가 |

### 2.2 v1에 있지만 v10에서 변형/확장된 노드

| v1 노드 | v10 대응 | 변경 사항 |
|---|---|---|
| `Experience` | `Chapter` | scope_type, outcomes, situational_signals, evidence, evidence_chunk, evidence_chunk_embedding 추가 |
| `Organization` | `Organization` | stage_label, stage_confidence, is_regulated_industry, 크롤링 보강 속성(product_description, market_segment 등 nullable) 추가 |
| `Skill` | `Skill` | category, aliases 추가, 정규화 전략 명시 |
| `Role` | `Role` | category, name_ko 추가, 동의어 사전 기반 정규화 |

### 2.3 v1에 있지만 v10에서 불필요하거나 축소된 노드

| v1 노드 | v10 상태 | 이유 |
|---|---|---|
| `EducationInst` | Organization에 통합 가능 | v10에서 학력은 부차적 |
| `Degree` | 제거 | v10 매핑에서 사용하지 않음 |
| `Certification` | 제거 | v10 매핑에서 사용하지 않음 |
| `Education` (중간 노드) | 제거 | v10 MappingFeatures에 학력 피처 없음 |
| `Project` | Chapter의 outcomes로 흡수 | 별도 노드 불필요 |

---

## 3. 추출 난이도 불일치

v1은 NER/RE 기반 범용 추출을 가정하지만, v11이 요구하는 추출은 훨씬 복잡하다.

| 추출 대상 | v1 접근 | v11 요구 | v9 실제 난이도 |
|---|---|---|---|
| 회사명, 직무명, 기간 | Rule + NER | 동일 | **제거** — resume-hub DB 직접 조회 **(v8 변경)** |
| tech_stack | 기술 사전 + Fuzzy | 동일 + 정규화 | **3-Tier 비교 전략** — Tier 1(code-hub CI Lookup) + Tier 2(경량 정규화+임베딩) + Tier 3(임베딩 전용) **(v9 변경)** |
| scope_type (IC/LEAD/HEAD) | 없음 | LLM 추론 필요 | **중간** — DB 힌트(positionGradeCode)로 정확도 향상 **(v8 변경)** |
| outcomes (성과 추출) | 없음 | LLM + quantitative 판별 | **중간~높음** |
| situational_signals (14 labels) | 없음 | LLM + taxonomy 분류 | **중간~높음** |
| vacancy scope_type (BUILD_NEW 등) | 없음 | JD에서 LLM 추론 | **중간~높음** — overview.descriptions에서 추론 **(v8 변경)** |
| stage_estimate | 없음 | NICE + JD + Rule | **중간** |
| operating_model facets (3개) | 없음 | 키워드 + LLM 보정 | **중간~높음** |
| failure_recovery | 없음 | LLM (거의 추출 불가) | **높음** (v1에서 null 허용) |
| structural_tensions (8-type taxonomy) | 없음 | 외부 데이터 필요 | **매우 높음** (v1에서 null) |
| ScopeType→Seniority 변환 | 없음 | Rule 기반 변환 규칙 | **낮음** (v10 A1에서 확정) |

**v8 핵심 함의**: resume-hub/job-hub/code-hub DB에 이미 정형화된 데이터가 적재되어 있으므로, v1~v7에서 필요했던 파싱/전처리/Rule 추출의 상당 부분이 **DB 조회로 대체**된다. LLM은 scope_type, outcomes, situational_signals 등 추론이 필요한 필드에만 집중한다.

> **v1 MVP에서 failure_recovery / structural_tensions를 null 허용하는 비즈니스 근거**:
> - 이 두 필드는 MappingFeatures의 핵심 피처(stage_match, vacancy_fit, domain_fit, role_fit) 계산에 직접 관여하지 않음
> - structural_tensions는 뉴스/기사 크롤링 등 외부 데이터 소스 없이는 추출 자체가 불가능 (v10에서 8-type taxonomy + N4 프롬프트 확정)
> - failure_recovery는 이력서에서 "실패→회복" 내러티브가 명시적으로 기술되는 경우가 극히 드물어(추정 5% 미만) 추출 비용 대비 활용도가 낮음
> - 두 필드 모두 Phase 3 데이터 소스 확장 시 점진적으로 활성화하는 것이 비용 효율적

---

## 4. 비용 모델 불일치

| v1 가정 | v10 현실 | v8 영향 |
|---|---|---|
| 범용 NER/RE → ML 모델로 대체 가능 | situational_signals, outcomes 추출은 ML 대체 어려움 | LLM 사용 비율 증가 (단, DB 기반으로 입력 축소) |
| Rule-based 40-70% 커버리지 | 기본 필드(회사/기간/기술)만 Rule 가능, 나머지는 LLM | **v8**: 기본 필드는 DB 직접 조회, Rule 기반 전처리 제거 |
| Silver label로 ML 학습 → LLM 대체 | v10 추출 태스크는 분류보다 생성/추론에 가까움 | Knowledge Distillation 범위 제한 |
| 150GB 전체를 배치 처리 | CompanyContext는 JD 단위, CandidateContext는 이력서 단위 | **v8**: DB 조회 기반, 파일 I/O 제거 |

---

## 5. v2/v3~v8에서 수정한 핵심 사항

### 5.1 방향 전환: "범용 KG 추출" → "v11 온톨로지 기반 Context 생성 파이프라인"

- 최종 목표를 "entity+relation triples"가 아닌 "CompanyContext JSON + CandidateContext JSON + Graph 적재 + MappingFeatures 계산"으로 재정의
- 추출 파이프라인을 v11 스키마에 정확히 맞춰 재설계
- **v11 신규**: 내부 DB 매핑 가이드(00_data_source_mapping.md)를 기준으로 DB↔온톨로지 필드 매핑 구체화

### 5.2 하이브리드 전략 재정의

v11에서의 하이브리드:
- **Rule**: 날짜, 기간, 기술 스택, NICE 팩트 조회, stage 규칙 판정
- **Embedding**: domain_fit (cosine similarity), Chapter/Vacancy vector search, **비정형 값 비교 (v11.1)**
- **LLM**: scope_type, outcomes, situational_signals, vacancy scope_type, operating_model 보정

v9에서의 하이브리드 (DB 기반 + 3-Tier 비교 전략):
- **DB 조회**: 회사명, 직무명, 기간, 기술 스택, 학력, industry, career_types → **LLM 불필요**
- **3-Tier 비교 전략** **(v9 변경, v11.1 정합)**:
  - Tier 1: 정규화 적합 (대학교, 회사명, 산업 코드) → code-hub CI Lookup
  - Tier 2: 경량 정규화 + 임베딩 (스킬) → CI + synonyms → 미매칭 시 임베딩
  - Tier 3: 임베딩 전용 (전공, 직무명, 롱테일 스킬) → 정규화 시도하지 않음, 임베딩 유사도
- **Rule**: stage 규칙 판정, NICE 팩트 조회
- **Embedding**: domain_fit (cosine similarity), Chapter/Vacancy vector search, **Tier 2/3 비교 유사도**
- **LLM**: scope_type, seniority(일부), outcomes, situational_signals, operating_model, role_evolution, domain_depth

비율 (v9 기반 추정):
- DB 조회: **30-40%** (기존 Rule + 파싱 영역 대부분 흡수)
- 3-Tier 비교 전략: **10-15%** (비정형 값 비교/정규화) **(v9 변경)**
- Rule: **10-15%** (stage 판정 등)
- Embedding: **10-15%** (유사도 기반 피처 + Tier 2/3 비교)
- LLM: **25-40%** (핵심 추론 필드에 집중, v7 대비 축소)

### 5.3 비용 모델 재수립

- LLM 입력 토큰 절감에 따른 비용 재산정
- DB 정형 필드를 LLM 프롬프트에 사전 제공하여 토큰 절감
- 배치 vs 실시간 처리 전략 수립

### 5.4 데이터 소스별 파이프라인 분리

- **CompanyContext 파이프라인**: job-hub DB + code-hub + NICE → CompanyContext JSON **(v8 변경)**
- **CandidateContext 파이프라인**: resume-hub DB + code-hub + NICE → CandidateContext JSON **(v8 변경)**
- **MappingFeatures 계산**: Rule + Embedding + 양쪽 Context 조합
- **Graph 적재**: 양쪽 Context → Neo4j 노드/엣지 생성 + MAPPED_TO 관계

### 5.5 v3에서 추가 보강한 사항 (v2 리뷰 반영)

- **에러 핸들링/retry 정책**: 파이프라인 내 에러 유형별 처리 정책 구체화 (02 문서 §8)
- **인력 배치 가정**: DE 1명 + MLE 1명 + 도메인 전문가 1명(파트타임) 명시 (04 문서 서두)
- **운영 전략**: 증분 처리, 롤백/재처리, Graph 업데이트 전략 신설 (04 문서)
- **배치 처리 아키텍처**: 500K 이력서의 chunk 분할, 동시 배치, 처리 시간 상세화 (02 문서 §8)
- **비용 기준 통일**: Batch API 가격 병기 (02 문서 비용 테이블)
- **프롬프트 통합**: vacancy + role_expectations 단일 프롬프트 (02 문서 §2.3)
- **타임라인 현실화**: 14~18주 (Phase 1 전처리 2주, CandidateContext 3주)
- **테스트 전략/모니터링**: 테스트 계층 + Grafana + BigQuery 모니터링 명시

### 5.6 v4에서 추가 보강한 사항 (v3 리뷰 반영)

- **Candidate Shortlisting 전략 정의**: 매핑 대상 후보 선정 방법론 명시 (02 문서 §5.0)
- **Neo4j 초기 적재 vs 증분 적재 전략 분리**: 초기 벌크 로드와 증분 Cypher MERGE 구분 (02 문서 §4.4)
- **Phase 0 PoC 범위 확장**: PII 마스킹 영향, embedding 모델 비교, LLM 호출 전략 비교 (04 문서 Phase 0-2)
- **evidence_span 후처리 검증 로직 추가**: LLM hallucination 방지를 위한 span 존재 확인 (02 문서 §8.2)
- **Organization MERGE 전략 org_id 기반 통일**: Entity Resolution 모듈 + org_id canonical key (02 문서 §4.3)
- **프롬프트 버전 관리 전략 명시**: Git 관리 + Golden Set 회귀 테스트 절차 (04 문서 운영 전략)

### 5.7 v5에서 추가 보강한 사항 (v4 리뷰 반영)

- **Graph 적재 Idempotency 보장**: 모든 노드를 deterministic ID 기반 MERGE로 통일 (02 문서 §4.6)
- **Deterministic ID 생성 전략**: Chapter, Outcome 등 ID 생성 규칙 명시 (02 문서 §4.6)
- **이력서 중복 처리 전략**: 중복 감지 + canonical 선택 + 처리 플로우 정의 (02 문서 §3.4)
- **evidence_span 검증 정규화**: strict match → normalized match로 개선 (02 문서 §8.2)
- **Phase 0 파싱 성공률 측정**: 섹션 분할 + 경력 블록 분리 성공률 별도 측정 (04 문서 Phase 0-2)
- **법무 의사결정 기본값 전략**: 법무 미확정 시 기본 행동 명시 (04 문서 Phase 0-3)

### 5.8 v6에서 추가 보강한 사항 (v5↔v10 교차 검증 반영)

> v6는 v5 계획과 v10 온톨로지 간 17건의 불일치(HIGH 6, MEDIUM 5, LOW 6)를 체계적으로 해소한다.

#### HIGH 반영 (6건)
- **H-1 Industry 노드**: Pipeline C에 Industry 마스터 노드 사전 생성 + Organization→Industry 관계 (02 문서 §4.1, §4.7)
- **H-2 Embedding 모델 확정**: `text-multilingual-embedding-002` (Vertex AI)로 확정, Phase 0 PoC를 "확정 검증"으로 변경 (02 문서 §4.5, 03 문서 §2)
- **H-3 크롤링 파이프라인**: Phase 3에 v10 06_crawling_strategy.md 4 Phase 실행 계획 인라인 반영 (04 문서 Phase 3)
- **H-4 structural_tensions 8-type taxonomy**: Pipeline A에 크롤링 데이터 유입 시 활성화 경로 명시, Pydantic 스키마에 taxonomy 반영 (02 문서 §1, §2.5)
- **H-5 REQUIRES_ROLE 엣지**: Pipeline C에 Vacancy→Role 관계 생성 추가 (02 문서 §4.1)
- **H-6 MAPPED_TO 엣지**: Pipeline D/E에 Graph 반영 단계 추가 (02 문서 §5, §4.1)

#### MEDIUM 반영 (5건)
- **M-1 operating_model 3 facets 명시**: `FACET_KEYWORDS`를 speed/autonomy/process 3개로 명시, 나머지 5개는 v2 로드맵 (02 문서 §2.4)
- **M-2 ScopeType→Seniority 변환**: Pipeline D role_fit에 `ic_to_seniority()`, `get_candidate_seniority()` 통합 (02 문서 §5)
- **M-3 WorkStyleSignals 필드 추가**: LLM 프롬프트에 experiment_orientation, collaboration_style 추출 항목 추가 (02 문서 §3.3)
- **M-4 Evidence source tier 체계**: `field_confidence = min(extraction_confidence, source_ceiling)` 규칙 적용, T4 카테고리별 예외 반영 (02 문서 §2.1, §8.2)
- **M-5 Facet merge 로직**: 크롤링 활성화 시 JD↔크롤링 facet score 병합 규칙 설계 (02 문서 §2.4)

#### LOW 반영 (6건)
- **L-1 Chapter 필드명**: `embedding_text` → `evidence_chunk` / `evidence_chunk_embedding`으로 통일 (02 문서 §4.5)
- **L-2 Organization 크롤링 보강 속성**: Neo4j 스키마에 nullable로 사전 선언 (04 문서 Phase 0-3)
- **L-3 domain_positioning 하위 필드**: Pydantic 스키마에 market_segment, competitive_landscape, product_description Optional 정의 (02 문서 §1)
- **L-4 CompanyTalentSignal 제외 명시**: 05 문서에 v10 A3 참조 추가 (05 문서 §1.4)
- **L-5 Company-to-Company 관계 로드맵**: Phase 3에 v10 A5 로드맵 표 참조 (04 문서 Phase 3)
- **L-6 Power analysis 참조**: Phase 2-2에 v10 05_evaluation_strategy.md §1.1 적응적 표본 크기 프로토콜 참조 (04 문서 Phase 2-2)

### 5.9 v7에서 추가 보강한 사항 (v6 리뷰 반영)

- **LLM 출력 파싱 실패 전략**: 3-tier retry (json-repair → temperature 재시도 → skip + dead-letter) + Pydantic 부분 추출 허용 + 파싱 실패율 모니터링 메트릭 (02 문서 §8.3)
- **시나리오 A' (Sonnet Batch fallback)**: Haiku 품질 미달 시 Sonnet Batch로 전환하는 fallback 시나리오 추가, 총비용 ~$11,522 (03 문서 §5.1.1)
- **오케스트레이션 전략**: Pipeline DAG 의존성 정의 (A/B 병렬 → C → D → E), Prefect vs Cloud Workflows 비교, chunk 관리 전략 (04 문서)
- **타임라인 현실화**: 16~19주 → 18~22주 (Phase 1에 +2주 버퍼) (04 문서)
- **사전 준비 (Pre-Phase 0)**: NICE DB 접근을 Phase 0 이전 blocking dependency로 추가 (04 문서)
- **A5 NICE 매칭률 보강**: NICE DB 접근 계약은 Phase 0 이전 사전 확인 필요 (blocking dependency) (05 문서 §1.2)
- **R2.17 LLM 출력 파싱 실패 리스크**: 150만 건 호출에서 2-10% 파싱 실패 시 3~15만 건 수동 처리 필요, 완화: 02 문서 §8.3 참조 (05 문서 §2.17)

### 5.10 v8에서 추가 보강한 사항 (데이터모델 기반 재설계) **(v8 신설)**

> v8은 실제 데이터가 resume-hub, job-hub, code-hub 3개 DB에 정형 데이터로 이미 적재되어 있다는 사실을 반영하여 파이프라인을 재설계한다.

#### 핵심 변경: 데이터 소스 전환

| 항목 | v7 | v8 |
|---|---|---|
| 이력서 소스 | 150GB 원본 파일 (PDF/DOCX/HWP) | **resume-hub DB** (Career, Skill, Education, CareerDescription, SelfIntroduction 엔티티) |
| JD 소스 | JD 텍스트 파일 | **job-hub DB** (job, overview, requirement, work_condition, skill 테이블) |
| 코드 정규화 | 기술 사전 2,000개 + fuzzy matching | **3-Tier 비교 전략**: Tier 1(대학교/회사명/산업 — code-hub CI Lookup) + Tier 2(스킬 — 경량 정규화+임베딩) + Tier 3(전공/직무 — 임베딩 전용) + code-hub 코드 참조 **(v9 변경)** |
| NICE 매칭 | 회사명 fuzzy match (60%) | **businessRegistrationNumber 직접 매칭 (80-90%)** |

#### Pipeline A (CompanyContext) 변경

- tech_stack: `job-hub.skill` → 3-Tier 비교 전략(Tier 2: 경량 정규화+임베딩) → **LLM 불필요** **(v9 변경)**
- industry: `overview.industry_codes` → `code-hub` INDUSTRY 계층 → **LLM 불필요**
- career_types, education, designation: `requirement`, `overview` 직접 조회 → **LLM 불필요**
- **여전히 LLM 필요**: scope_type, seniority, operating_model → 입력을 `overview.descriptions` JSONB에서 가져옴
- 정형 필드를 LLM 프롬프트에 사전 제공하여 **토큰 44% 절감** (3,900→2,200 tok/건)

#### Pipeline B (CandidateContext) 변경

- 파싱/섹션분할/블록분리 **전체 제거** — Career 엔티티가 이미 회사 단위 분리
- 회사명/기간/직급/직무/기술: DB에서 직접 조회 → **LLM 불필요**
- PastCompanyContext: `Career.businessRegistrationNumber` → NICE 직접 매칭 → **매칭률 60%→80-90%**
- scope_type 추론 시 `positionGradeCode`/`positionTitleCode`를 힌트로 제공 → **정확도 향상**
- **여전히 LLM 필요**: scope_type, outcomes, situational_signals, role_evolution, domain_depth
  - LLM 입력: `Career.workDetails` + `CareerDescription.description` + `SelfIntroduction.description`
- **토큰 40% 절감** (3,000→1,800 tok/건)

#### 제거된 모듈/단계

| v7 모듈 | v8 상태 | 이유 |
|---|---|---|
| PDF/DOCX/HWP 파서 | **제거** | DB에서 텍스트 필드 직접 조회 |
| OCR 모듈 | **제거** | 파일 파싱 불필요 |
| 섹션 분할기 (Rule-based) | **제거** | Career 엔티티가 이미 분리됨 |
| 경력 블록 분리기 | **제거** | Career 엔티티가 회사 단위로 구분됨 |
| 기술 사전 2,000개 구축 | **대폭 축소 → 3-Tier 비교 전략으로 대체** | Tier 1: code-hub CI Lookup + Tier 2: CI+synonyms+임베딩(~2,000개) + Tier 3: 임베딩 전용 **(v9 변경)** |
| 회사 사전 + alias | **대폭 축소** | BRN 기반 직접 매칭 |
| Rule 추출 모듈 (정규식) | **제거** | DB 정형 필드로 대체 |

#### 일정 단축 (5~6주)

| Phase | v7 | v8 | 단축 |
|---|---|---|---|
| Phase 0 | 3~4주 | 2~3주 | 1주 |
| Phase 1-1 | 전처리 2주 | DB 커넥터 + 정규화 1~2주 | 0~1주 **(v8.1)** |
| Phase 1-3 | 3주(+1주 버퍼) | 2주 | 1~2주 |
| Phase 1-4 | 2주 | 1~2주 | 0~1주 |
| Phase 2 | 4~5주 | 3~4주 | 1주 |
| **총 MVP** | 18~22주 | **14~17주** | **4~5주** **(v8.1)** |

#### 리스크 변경

| 변경 유형 | 항목 | 비고 |
|---|---|---|
| **제거** | R2.3 파싱 품질+LLM 상관 리스크 (Critical) | DB 조회이므로 파싱 실패 없음 |
| **완화** | R2.4 NICE 매칭률 (High→Medium) | BRN 직접 매칭 |
| **변경** | R2.10 Entity Resolution (Medium→Medium 유지) | DB 값이 비표준이므로 3-Tier 비교 전략 필요 **(v9 변경)** |
| **완화** | R2.15 이력서 중복 (Medium→Low) | SiteUserMapping 기반 |
| **신규** | R2.18 DB 접근 권한/가용성 (High) | Pre-Phase 0 blocking |
| **신규** | R2.19 데이터 적재 미완료 (High) | resume-hub 적재 상태 확인 |
| **신규** | R2.20 텍스트 필드 품질 (Medium) | workDetails null 비율에 따라 LLM 품질 변동 |
| **신규** | R2.21 code-hub 코드 완성도 (Medium) | HARD_SKILL 코드 커버리지 |
| **신규** | R2.22 JSONB 필드 스키마 불일치 (Medium) | overview.descriptions 구조 확인 필요 |

### 5.11 v9에서 추가 보강한 사항 (v11 온톨로지 정합) **(v9 신설)**

> v9는 v11 온톨로지(특히 v11.1의 A9 비정형 값 비교 전략)와의 정합성을 맞추기 위해 용어, 구조, threshold를 통일한다.

#### 핵심 변경: 2-Tier → 3-Tier 비교 전략 통일

| 항목 | v8.1 | v9 | 변경 근거 |
|---|---|---|---|
| 비교 전략 명칭 | 2-Tier 정규화 | **3-Tier 비교 전략** | v11.1 `00_data_source_mapping.md` §1.5와 용어 통일 |
| Tier 구조 | Tier 1(CI+alias) + Tier 2(embedding) | **Tier 1(CI Lookup) + Tier 2(경량 정규화+임베딩) + Tier 3(임베딩 전용)** | 스킬과 전공/직무의 비교 전략을 명시적으로 분리 |
| normalize_skill() | code-hub code → embedding fallback | **CI 매칭 + synonyms 매칭 → 미매칭 시 원본 유지 (비교는 임베딩)** | v11.1 §1.3 함수와 동일하게 통일 |
| 전공 threshold | 0.80 | **0.75** | v11.1 §1.5 `compare_majors()` 근거: "의미적 유사성이 넓음" |
| confidence 세분화 | db_structured: 0.80 (단일) | **비교 방법별 6단계** (CI=0.95, synonyms=0.85, emb≥0.90=0.80, emb 0.80~0.90=0.70, emb 0.75~0.80=0.60) | v11.1 §6.4 비교 방법별 신뢰도 테이블 반영 |

#### 신규 함수/모듈 추가

| 함수 | 출처 | 반영 위치 |
|---|---|---|
| `compute_embedding_similarity_batch()` | v11.1 §1.5 | 02 문서 §4.3 공통 유틸리티 |
| `compare_majors()` | v11.1 §1.5 | 02 문서 §4.3 전공 비교 |
| `compute_skill_overlap()` 하이브리드 | v11.1 §4.3 | 02 문서 §5 Pipeline D MappingFeatures |
| 비정형 값 비교 품질 모니터링 4개 지표 | v11.1 §6.4 | 02 문서 §6 모니터링 |

#### 온톨로지 버전 참조 갱신

- 전체 문서의 "v10 온톨로지" 참조를 "v11 온톨로지"로 갱신
- v11 신규 문서 `00_data_source_mapping.md` 참조 추가
- v10 문서 참조 시 "(v10)" 명시하여 버전 혼동 방지
