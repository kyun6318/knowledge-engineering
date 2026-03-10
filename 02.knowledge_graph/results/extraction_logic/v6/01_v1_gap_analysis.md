# v1 계획 Gap 분석 — v10 온톨로지 대비

> v1 계획이 v10 온톨로지 요구사항에 맞지 않는 부분을 식별하고, v2/v3~v6에서 수정한 방향을 정리한다.
>
> 작성일: 2026-03-08 (v2 기반)
> 개정일: 2026-03-08 (v6 — v10 온톨로지 교차 검증 반영)

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

v1은 NER/RE 기반 범용 추출을 가정하지만, v10이 요구하는 추출은 훨씬 복잡하다.

| 추출 대상 | v1 접근 | v10 요구 | 실제 난이도 |
|---|---|---|---|
| 회사명, 직무명, 기간 | Rule + NER | 동일 | 낮음 |
| tech_stack | 기술 사전 + Fuzzy | 동일 + 정규화 | 낮음 |
| scope_type (IC/LEAD/HEAD) | 없음 | LLM 추론 필요 | **중간** |
| outcomes (성과 추출) | 없음 | LLM + quantitative 판별 | **중간~높음** |
| situational_signals (14 labels) | 없음 | LLM + taxonomy 분류 | **중간~높음** |
| vacancy scope_type (BUILD_NEW 등) | 없음 | JD에서 LLM 추론 | **중간~높음** |
| stage_estimate | 없음 | NICE + JD + Rule | **중간** |
| operating_model facets (3개) | 없음 | 키워드 + LLM 보정 | **중간~높음** |
| failure_recovery | 없음 | LLM (거의 추출 불가) | **높음** (v1에서 null 허용) |
| structural_tensions (8-type taxonomy) | 없음 | 외부 데이터 필요 | **매우 높음** (v1에서 null) |
| ScopeType→Seniority 변환 | 없음 | Rule 기반 변환 규칙 | **낮음** (v10 A1에서 확정) |

**핵심 함의**: v10의 추출 요구사항 중 상당수는 단순 NER/RE로 해결 불가하며, LLM 의존도가 v1 계획보다 훨씬 높다. 따라서 v1의 "Rule 60-70% → ML 20-30% → LLM 5-15%" 비율은 v10에 적용 불가하다.

> **v1 MVP에서 failure_recovery / structural_tensions를 null 허용하는 비즈니스 근거**:
> - 이 두 필드는 MappingFeatures의 핵심 피처(stage_match, vacancy_fit, domain_fit, role_fit) 계산에 직접 관여하지 않음
> - structural_tensions는 뉴스/기사 크롤링 등 외부 데이터 소스 없이는 추출 자체가 불가능 (v10에서 8-type taxonomy + N4 프롬프트 확정)
> - failure_recovery는 이력서에서 "실패→회복" 내러티브가 명시적으로 기술되는 경우가 극히 드물어(추정 5% 미만) 추출 비용 대비 활용도가 낮음
> - 두 필드 모두 Phase 3 데이터 소스 확장 시 점진적으로 활성화하는 것이 비용 효율적

---

## 4. 비용 모델 불일치

| v1 가정 | v10 현실 | 영향 |
|---|---|---|
| 범용 NER/RE → ML 모델로 대체 가능 | situational_signals, outcomes 추출은 ML 대체 어려움 | LLM 사용 비율 증가 |
| Rule-based 40-70% 커버리지 | 기본 필드(회사/기간/기술)만 Rule 가능, 나머지는 LLM | Rule 커버리지 실질 20-30% |
| Silver label로 ML 학습 → LLM 대체 | v10 추출 태스크는 분류보다 생성/추론에 가까움 | Knowledge Distillation 범위 제한 |
| 150GB 전체를 배치 처리 | CompanyContext는 JD 단위, CandidateContext는 이력서 단위 | 처리 단위와 볼륨이 다름 |

---

## 5. v2/v3~v6에서 수정한 핵심 사항

### 5.1 방향 전환: "범용 KG 추출" → "v10 온톨로지 기반 Context 생성 파이프라인"

- 최종 목표를 "entity+relation triples"가 아닌 "CompanyContext JSON + CandidateContext JSON + Graph 적재 + MappingFeatures 계산"으로 재정의
- 추출 파이프라인을 v10 스키마에 정확히 맞춰 재설계

### 5.2 하이브리드 전략 재정의

v10에서의 하이브리드:
- **Rule**: 날짜, 기간, 기술 스택, NICE 팩트 조회, stage 규칙 판정
- **Embedding**: domain_fit (cosine similarity), Chapter/Vacancy vector search
- **LLM**: scope_type, outcomes, situational_signals, vacancy scope_type, operating_model 보정

비율 (v10 기반 현실적 추정):
- Rule: **25-35%** (기본 팩트 + 정형 필드만)
- Embedding: **10-15%** (유사도 기반 피처)
- LLM: **50-65%** (핵심 추출의 대부분)

### 5.3 비용 모델 재수립

- LLM 의존도 증가에 따른 비용 재산정
- 경량 LLM (Haiku/Flash) 활용 범위 명확화
- 배치 vs 실시간 처리 전략 수립

### 5.4 데이터 소스별 파이프라인 분리

- **CompanyContext 파이프라인**: JD 파싱 + NICE 조회 + Rule 판정 + LLM 추출
- **CandidateContext 파이프라인**: 이력서 파싱 + LLM 추출 + NICE 역산
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
