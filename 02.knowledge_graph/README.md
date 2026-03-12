# 02.knowledge_graph — 지식그래프 추출 로직

## 이 문서는 무엇인가?

`01.ontology/v20/` 에서 정의한 온톨로지(v20)를 기반으로 **지식그래프(Knowledge Graph)** 를 구축하기 위한 **추출 로직 설계서**(how to build)입니다.

핵심 목표는 **이력서(resume-hub DB + 파일) + JD(job-hub DB) + NICE 기업정보 + code-hub 정규화 DB**로부터 온톨로지에 맞는 구조화된 데이터를 추출하여 Neo4j 그래프 DB에 적재하는 것입니다.

---

## 배경: v1에서 v13까지의 진화

초기 v1 계획은 이력서 150GB에서 범용 NER/RE로 엔티티-관계를 추출하는 접근이었습니다. v20 온톨로지는 **Chapter-Trajectory 기반 맥락 매칭 시스템**이라는 도메인 특화 구조를 요구하므로, v2~v13까지 반복적 개선을 거쳤습니다.

| 구분 | v1 (초기) | v13 (현재) |
|---|---|---|
| 목표 | 범용 KG 추출 | 맥락 기반 채용 매칭 시스템 |
| 스키마 | Person, Org, Skill 등 5개 | Person, Chapter, SituationalSignal, Vacancy 등 **9개** |
| 데이터 소스 | 파일 이력서 only | **DB-first** (resume-hub/job-hub/code-hub) + 파일 폴백 |
| 추출 방식 | Rule 60-70% + ML 20-30% + LLM 5-15% | DB 직접 매핑 + Rule + **LLM 추론 (Haiku Batch)** |
| 인프라 | 미정 | **GCP 네이티브** (Cloud Run Jobs + Cloud Workflows) |
| 산출물 | Entity + Relation triples | CompanyContext JSON + CandidateContext JSON + Graph + Embedding |

v12에서 구현 착수 수준을 달성했으며, v13에서 온톨로지(v20)에 있던 정규화/데이터 품질 로직을 추출 영역으로 통합했습니다.

---

## 디렉토리 구조

```
02.knowledge_graph/
├── README.md                          ← 현재 문서
├── v13/                               ← 최신 버전 (현재 기준)
│   ├── 01_extraction_pipeline.md
│   ├── 02_model_and_infrastructure.md
│   ├── 03_prompt_design.md
│   ├── 04_pii_and_validation.md
│   ├── 05_extraction_operations.md
│   ├── 06_normalization.md            ← v13 신규 (ontology에서 이동)
│   └── 07_data_quality.md             ← v13 신규 (ontology에서 이동)
├── results/
│   └── extraction_logic/
│       └── v1/ ~ v12/                 ← 이전 버전들
└── llm_log/
    ├── answers/                       ← v1 LLM별 응답 (Claude, GPT, Gemini)
    │   └── prompt.md                  ← 프로젝트 시작 프롬프트 (v1 기반)
    └── reviews/                       ← v2~v12 각 버전의 리뷰 기록
        └── v2/ ~ v12/
```

---

## v13 문서 가이드

### 01. 추출 파이프라인 설계 (`01_extraction_pipeline.md`)

4개 파이프라인의 상세 설계서입니다.

```
Pipeline A (CompanyContext)  ──┐
Pipeline B (CandidateContext DB) ──┼──→ Pipeline C (Graph 적재)
Pipeline B' (CandidateContext 파일) ─┘
```

| Pipeline | 입력 | 출력 | 핵심 기술 |
|---|---|---|---|
| **A: CompanyContext** | job-hub + code-hub + NICE | CompanyContext JSON | DB 직접 매핑 + Rule + LLM |
| **B: CandidateContext (DB)** | resume-hub + code-hub + NICE | CandidateContext JSON | DB 직접 매핑 + LLM (적응형 호출) |
| **B': CandidateContext (파일)** | PDF/DOCX/HWP | CandidateContext JSON | Hybrid 섹션 분리 + LLM |
| **C: Graph 적재** | A/B/B' 결과 | Neo4j 노드/엣지 | UNWIND MERGE + Deterministic ID |

주요 내용:
- **DB-first 원칙**: 구조화 필드는 DB/코드 직접 매핑, LLM은 추론 필요 필드만
- **3-Tier 비교 전략**: CI Lookup → 정규화+임베딩 → 임베딩 only (상세: `06_normalization.md`)
- **적응형 LLM 호출**: Career 1~3은 1-pass, 4+는 N+1 pass
- **파일 섹션 분리**: 패턴 기반 → LLM 폴백 Hybrid 전략
- **관계명 canonical**: v20 온톨로지가 유일한 정본
- **Graph 규모**: ~8M 노드, ~25M 엣지

### 02. 모델 선정 및 인프라 (`02_model_and_infrastructure.md`)

사용 모델과 GCP 인프라를 정의합니다.

**모델 선택**:
- LLM 추출: **Claude Haiku 4.5** (Batch API 50% 할인), Sonnet 4.6 폴백
- Embedding: **text-embedding-005** (Vertex AI, 768d)
- Graph DB: **Neo4j AuraDB** (Free → Professional 마이그레이션)

**GCP 리소스**:
- Cloud Run Jobs: kg-parse, kg-preprocess, kg-extract, kg-graph-load
- Cloud Workflows: A/B/B'/C DAG 오케스트레이션
- 서비스 계정: kg-processing, kg-loading (최소 권한)

### 03. LLM 프롬프트 설계 (`03_prompt_design.md`)

CompanyContext / CandidateContext 추출을 위한 프롬프트 상세 설계입니다.

- **설계 원칙**: Taxonomy Enforcement, Evidence Span, Self-Confidence, 구조화 필드 사전 주입
- **CompanyContext**: hiring_context(4+1 유형), operating_model(3 facets), role_expectations
- **CandidateContext**: scope_type(4+1 유형), outcomes(4+1 유형), situational_signals(14 라벨)
- **호출 전략 분기**: 1-pass 프롬프트 vs N+1 pass 프롬프트
- **INACTIVE 필드 제외**: structural_tensions, work_style_signals
- **Pydantic v2 스키마**: 입출력 검증 + Few-shot 예시 포함

### 04. PII 마스킹 및 검증 (`04_pii_and_validation.md`)

PII 처리 전략과 6단계 파이프라인 검증 체크포인트를 정의합니다.

- **PII 마스킹**: 비가역 토큰 방식 (`[NAME_001]`), 주민번호 즉시 삭제
- **PII 매핑 저장소**: GCS CMEK 추천 (대안: BigQuery DLP, CloudSQL)
- **전화번호 탐지**: 한국 변형 8종 커버, 탐지율 90%+
- **6단계 검증**: 입력 → 마스킹 → LLM 출력 → 정규화 → 적재 → 임베딩
- **품질 메트릭**: scope_type ≥70%, outcomes F1 ≥55%, pii_leak_rate ≤0.01%

### 05. 추출 운영 (`05_extraction_operations.md`)

증분 처리, 테스트, Organization ER, 리스크를 정리합니다.

- **증분 처리**: DB updated_at 기반 변경 감지, 구조화/텍스트 필드 분류별 처리
- **DETACH DELETE 시 공유 노드 보호**: Skill/Organization은 관계만 제거, Outcome/Signal은 노드도 삭제
- **소프트 삭제**: is_active=false + 쿼리 패턴
- **테스트**: 단위/통합/멱등성/배치/스케일/품질/회귀
- **Gold Set**: Phase 0 50건 → Phase 4 200건
- **리스크**: Critical 2건 (PII, LLM 품질), High 2건, Medium 3건, Low 2건

### 06. 정규화 및 코드 매칭 (`06_normalization.md`)

v20 온톨로지에서 이동된 정규화/비교 구현 로직입니다.

- **3-Tier 비교 전략**: Tier 1 (code-hub CI lookup), Tier 2 (정규화+임베딩), Tier 3 (임베딩 only)
- **스킬 정규화**: `normalize_skill()` 함수, code-hub 38.3% 커버리지
- **임베딩 비교**: text-embedding-005, cosine similarity ≥0.82 threshold
- **자격증 타입 매핑**: code-hub certificateType → 7개 카테고리
- **코드 기반 매칭**: `compute_job_classification_match()`, `compute_skill_overlap()`
- **정규화 사전 조건**: 진실 소스(Truth Source) 우선순위

### 07. 데이터 품질 (`07_data_quality.md`)

v20 온톨로지에서 이동된 데이터 품질/커버리지 메트릭입니다.

- **resume-hub 필드 가용성**: 실측 fill rate (Career 87.2%, Skill 38.3% 등)
- **job-hub 필드 가용성**: 실측 fill rate (회사명 99.8%, 연봉 69.2% 등)
- **Graceful Degradation 전략**: 필드 가용도별 피처 활성화 예측
- **모니터링 지표**: Coverage Rate, Confidence 분포, INACTIVE 피처 비율
- **Feature Activation Outlook**: v1~v1.2 피처별 활성화 전망

---

## 비용 요약 (추출 범위)

| 시나리오 | LLM 비용 | 비고 |
|---------|---------|------|
| **A. 추천 (Haiku Batch + DB-first + 적응형)** | **$654** | Batch API 50% 할인 |
| A'. DB-only (파일 미포함) | $498 | 파일 파싱/섹션 분리 비용 제외 |
| B. Sonnet 폴백 | $3,580 | Haiku 품질 <70% 시 |
| C. 최저 비용 (Gemini Flash) | $360 | 비용 최적화 |

> GCP 인프라 비용 (~$362), Neo4j, Gold Label 비용은 03.graphrag에서 통합 관리

---

## 관련 문서

| 경로 | 설명 |
|---|---|
| `01.ontology/v20/` | v20 온톨로지 정의 — 순수 스키마 (what to represent) |
| `03.graphrag/results/implement_planning/separate/v3/` | GraphRAG 구현 계획 — GCP 인프라, 매칭 설계, 서빙 (how to serve) |
| `02.knowledge_graph/llm_log/answers/` | v1 시점의 Claude/GPT/Gemini 초기 응답 |
| `02.knowledge_graph/llm_log/reviews/v2~v12/` | 각 버전 리뷰 기록 |

---

## 버전 이력

| 버전 | 주요 변경 |
|---|---|
| v1 | 초기 계획 (범용 NER/RE 기반) |
| v2 | v10 온톨로지 기반으로 방향 전환, 파이프라인 재설계 |
| v3 | 에러 핸들링, 인력 배치, 배치 처리 아키텍처, 타임라인 상세화 |
| v4 | Candidate Shortlisting, Neo4j 적재 전략, Phase 0 PoC 확장, Entity Resolution |
| v5 | Graph Idempotency, Deterministic ID, 이력서 중복 처리, 법무 기본값 전략 |
| v6 | v10 온톨로지 교차 검증 (17건 불일치 해소), Industry 노드, Embedding 확정, MAPPED_TO 엣지 |
| v7 | LLM 파싱 실패 전략, Sonnet fallback 시나리오, 오케스트레이션/타임라인 현실화, NICE DB blocking |
| v8~v9 | 문서 구조 통합, 추출 로직 분리 |
| v10 | 문서 정체성 재정의, 프롬프트 설계 신설, PII 전략 신설, 추출 운영 신설 |
| v11 | DB-first 원칙, 3-Tier 비교 전략, v19 온톨로지 정합, 증분 처리 설계, 비용 44% 절감 |
| v12 | **구현 착수 수준 보강** — 적응형 LLM 호출(M1), 관계명 canonical(M2), 구현 순서 안내(M3), 파일 섹션 분리(S1), PII 저장소(S2), INACTIVE 필드 제외(S5) |
| v13 | **온톨로지 콘텐츠 통합** — v20 온톨로지에서 정규화 로직(`06_normalization.md`), 데이터 품질(`07_data_quality.md`)을 추출 영역으로 이동 |

---

## 빠른 시작: 이 문서를 읽는 순서

1. **파이프라인 이해**: `01_extraction_pipeline.md` §0~1 (설계 원칙, 전체 구조)
2. **모델/인프라 확인**: `02_model_and_infrastructure.md` §1~4 (모델 선정, GCP 리소스)
3. **프롬프트 확인**: `03_prompt_design.md` §1~2 (CompanyContext, CandidateContext 프롬프트)
4. **PII/검증 확인**: `04_pii_and_validation.md` §1~2 (마스킹 전략, 검증 체크포인트)
5. **운영 확인**: `05_extraction_operations.md` §1~4 (증분 처리, 테스트, 리스크)
6. **정규화 로직**: `06_normalization.md` (3-Tier 비교 전략, 스킬 정규화)
7. **데이터 품질**: `07_data_quality.md` (필드 가용성, Graceful Degradation)
