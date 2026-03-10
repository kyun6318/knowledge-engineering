# 02.create-kg — 지식그래프 구축 계획

## 이 문서는 무엇인가?

`01.ontology/schema/` 에서 정의한 온톨로지(v10)를 실제 **지식그래프(Knowledge Graph)** 로 구축하기 위한 실행 계획서입니다.

핵심 목표는 **이력서 + JD(채용공고) + NICE 기업정보**로부터 온톨로지에 맞는 구조화된 데이터를 추출하여 Neo4j 그래프 DB에 적재하고, 후보자-채용공고 간 매칭 피처를 계산하는 것입니다.

---

## 배경: 왜 이 계획이 필요한가?

초기 v1 계획은 이력서 150GB에서 범용 NER/RE로 엔티티-관계를 추출하는 접근이었습니다. 그러나 v10 온톨로지는 **Chapter-Trajectory 기반 맥락 매칭 시스템**이라는 도메인 특화 구조를 요구하므로, 범용 추출 방식으로는 근본적으로 불일치합니다.

| 구분 | v1 (초기) | v10 (현재) |
|---|---|---|
| 목표 | 범용 KG 추출 | 맥락 기반 채용 매칭 시스템 |
| 스키마 | Person, Org, Skill 등 5개 | Person, Chapter, SituationalSignal, Vacancy 등 9개 |
| 추출 방식 | Rule 60-70% + ML 20-30% + LLM 5-15% | Rule 25-35% + Embedding 10-15% + **LLM 50-65%** |
| 산출물 | Entity + Relation triples | CompanyContext JSON + CandidateContext JSON + Graph + MappingFeatures |

v2~v7까지 7회의 반복적 개선을 통해 v10 온톨로지에 정합하는 계획으로 발전시켰습니다.

---

## 디렉토리 구조

```
02.create-kg/
├── README.md              ← 현재 문서
├── answers/               ← v1 LLM별 응답 (Claude, GPT, Gemini)
│   └── prompt.md          ← 프로젝트 시작 프롬프트 (v1 기반)
├── reviews/               ← v2~v7 각 버전의 리뷰 기록
│   └── v2/ ~ v7/
└── plans/
    └── v7/                ← 최신 계획 (현재 기준)
        ├── 01_v1_gap_analysis.md
        ├── 02_extraction_pipeline.md
        ├── 03_model_candidates_and_costs.md
        ├── 04_execution_plan.md
        └── 05_assumptions_and_risks.md
```

---

## v7 계획 문서 가이드

### 01. Gap 분석 (`01_v1_gap_analysis.md`)

v1 계획이 v10 온톨로지와 어떤 점에서 맞지 않는지를 체계적으로 분석합니다.

- **스키마 Gap**: v10에서 필요하지만 v1에 없는 노드 (Chapter, SituationalSignal, Vacancy, Industry 등)
- **추출 난이도 Gap**: scope_type, outcomes, situational_signals 등은 단순 NER/RE로 불가능하며 LLM 추론 필수
- **비용 모델 Gap**: LLM 의존도가 v1 예상보다 훨씬 높음
- **v2~v7 수정 이력**: 각 버전에서 어떤 문제를 해결했는지 요약

### 02. 추출 파이프라인 설계 (`02_extraction_pipeline.md`)

5단계 파이프라인의 상세 설계서입니다.

```
Pipeline A (CompanyContext)  ──┐
                               ├──→ Pipeline C (Graph 적재) → Pipeline D (매핑) → Pipeline E (서빙)
Pipeline B (CandidateContext) ─┘
```

| Pipeline | 입력 | 출력 | 핵심 기술 |
|---|---|---|---|
| **A: CompanyContext** | JD + NICE DB | CompanyContext JSON | NICE Lookup + Rule + LLM |
| **B: CandidateContext** | 이력서 + NICE | CandidateContext JSON | 파싱 + LLM 추출 + NICE 역산 |
| **C: Graph 적재** | A + B 결과 | Neo4j 노드/엣지 | Deterministic ID + MERGE |
| **D: MappingFeatures** | A × B | MappingFeatures JSON | Rule + Embedding cosine |
| **E: 서빙** | D 결과 | BigQuery + MAPPED_TO | 테이블 적재 |

주요 내용:
- 파이프라인별 Pydantic 스키마, 프롬프트 예시, 비용 추정
- Pipeline A/B는 **병렬 실행 가능** (입력 데이터가 독립적)
- Source Tier 기반 confidence 규칙: `field_confidence = min(extraction_confidence, source_ceiling)`
- 에러 핸들링: 유형별 retry/skip/dead-letter 정책
- LLM 파싱 실패 3-tier 전략 (v7 신설): json-repair → temperature 재시도 → skip

### 03. 모델 후보 및 비용 (`03_model_candidates_and_costs.md`)

사용 모델과 비용을 시나리오별로 산출합니다.

**모델 선택 전략**:
- LLM 추출: Claude Haiku 4.5 (Batch API 50% 할인)
- Embedding: text-multilingual-embedding-002 (Vertex AI, v10 확정)
- Graph DB: Neo4j AuraDB

**비용 시나리오 요약** (이력서 500K + JD 10K 기준):

| 시나리오 | 설명 | 총비용 |
|---|---|---|
| **A (권장)** | Haiku Batch API | **~1,262만 원** |
| A' (v7 신설) | Haiku 품질 미달 시 Sonnet fallback | ~1,579만 원 |
| B | 처음부터 Sonnet | ~1,579만 원 |
| C | On-premise (PII 제약) | ~2,389만 원 |
| D | Gemini Flash (최저) | ~1,223만 원 |

### 04. 실행 계획 (`04_execution_plan.md`)

Phase별 상세 태스크, 인력 배치, 타임라인을 정의합니다.

**인력**: DE 1명 + MLE 1명 (풀타임) + 도메인 전문가 1명 (파트타임)

```
Pre-Phase 0: NICE DB 접근 확보 (Blocking)
Phase 0: 기반 구축 + PoC .............. 3~4주
Phase 1: MVP 파이프라인 .............. 8~10주
Phase 2: 확장 + 최적화 ............... 4~5주
Phase 3: 고도화 (크롤링 등) .......... 지속
                              총 18~22주
```

v7 주요 추가 사항:
- **Pre-Phase 0**: NICE DB 접근을 blocking dependency로 명시
- **오케스트레이션 전략**: Pipeline DAG, Prefect vs Cloud Workflows 비교
- **Chunk 관리**: 500K 이력서를 1,000건/chunk로 분할, 상태 추적

### 05. 가정 및 리스크 (`05_assumptions_and_risks.md`)

16개 가정(Assumptions)과 17개 리스크를 식별하고 완화 전략을 제시합니다.

**Critical 리스크**:
1. **PII 개인정보 처리** — API vs On-premise 결정, 비용 2배 차이
2. **LLM 추출 품질** — situational_signals, outcomes의 실제 정확도
3. **파싱 + LLM 품질 상관** — 파싱 실패가 추출 실패로 연쇄

**핵심 가정** (Phase 0에서 검증):
- A2: 이력서 500K건 (150GB ÷ 300KB)
- A8: Haiku 품질이 Sonnet의 85% 수준
- A10: PII 마스킹 후 외부 API 전송 가능

---

## 관련 문서

| 경로 | 설명 |
|---|---|
| `01.ontology/schema/v10/` | v10 온톨로지 정의 (CompanyContext, CandidateContext, Graph Schema 등 7개 문서) |
| `02.create-kg/answers/` | v1 시점의 Claude/GPT/Gemini 초기 응답 |
| `02.create-kg/reviews/v2~v7/` | 각 버전 리뷰 기록 (이전 버전의 문제점 식별 → 다음 버전에 반영) |

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

---

## 빠른 시작: 이 문서를 읽는 순서

1. **전체 그림 파악**: 이 README → `01_v1_gap_analysis.md` §1~2 (목적 불일치, 스키마 Gap)
2. **파이프라인 이해**: `02_extraction_pipeline.md` §0~1 (설계 원칙, 전체 구조)
3. **비용 확인**: `03_model_candidates_and_costs.md` §5~6 (시나리오별 비용)
4. **일정 확인**: `04_execution_plan.md` (Phase별 로드맵)
5. **리스크 확인**: `05_assumptions_and_risks.md` §1~2 (가정 + Critical 리스크)
