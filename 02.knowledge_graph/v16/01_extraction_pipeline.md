> 작성일: 2026-03-13
> 

---

## 0. 설계 원칙

1. **스키마 준수**: 9 Node
2. **DB-first, 파일 폴백**: resume-hub/job-hub/code-hub DB 우선, DB 미존재 이력서 ~20%는 파일 파싱
3. **LLM-for-reasoning**: 구조화 필드는 DB/코드 직접 매핑, LLM은 추론 필요 필드만
4. **3-Tier 비교 전략**: Tier 1 CI Lookup -> Tier 2 정규화+임베딩 -> Tier 3 임베딩 only
5. **GCP 네이티브**: Cloud Run Jobs(배치) + Cloud Workflows(오케스트레이션)
6. **Fail-safe**: null 허용 + dead-letter queue + 3-tier retry
7. **멱등성**: Deterministic ID + MERGE/UNWIND 패턴 + loaded_batch_id 태그
8. **비용 실용주의**: 구조화 필드 사전 주입으로 LLM 토큰 44% 절감(CompanyContext), 40% 절감(CandidateContext)

---

## 1. 파이프라인 아키텍처

### 1.1 전체 흐름

```
[Data Sources]                    [GCP Processing]                    [Graph]

resume-hub DB ─┐                  ┌─ Cloud Run Job: kg-preprocess     ┌─ Neo4j AuraDB
job-hub DB ────┼─-> DB Connectors ─┤  (정규화, PII 마스킹, 블록 분리) ──┤  (Graph MERGE)
code-hub DB ───┘                  │                                   │
NICE DB ───────-> BRN Lookup       ├─ Cloud Run Job: kg-extract        ├─ Vertex AI
PDF/DOCX/HWP ──-> File Parser ─────┤  (LLM 추출: Batch API)           │  (Vector Index)
                                  │                                   │
                                  ├─ Cloud Run Job: kg-graph-load     └─ BigQuery
                                  │  (Neo4j UNWIND 적재, <5 태스크)      (dead-letter)
                                  │
                                  └─ Cloud Workflows
                                     (A/B/B'/C DAG 오케스트레이션)

* Pipeline D (MappingFeatures) -> 04.graphrag Phase 3 참조
* Pipeline E (Serving API) -> 04.graphrag Phase 1 참조
```

### 1.2 데이터 소스 매핑

| 소스 | 파이프라인 | 매핑 대상 | 접근 방식 |
| --- | --- | --- | --- |
| resume-hub | B (CandidateContext) | Career, Skill, Education, CareerDescription, SelfIntroduction | asyncpg read replica |
| job-hub | A (CompanyContext) | job, overview, requirement, work_condition, skill | asyncpg read replica |
| code-hub | 공통 (정규화) | HARD_SKILL, SOFT_SKILL, JOB_CLASSIFICATION, INDUSTRY | Tier 1/2 lookup |
| NICE DB | A, B (기업 정보) | 기업 기본 정보, stage_estimate, PastCompanyContext | BRN 직접 매칭 |
| 파일 시스템 | B’ (폴백) | PDF/DOCX/HWP 이력서 | Cloud Storage -> Document AI / Gemini |

### 1.3 4개 파이프라인 정의

| 파이프라인 | 입력 | 출력 | GCP 리소스 |
| --- | --- | --- | --- |
| **A. CompanyContext** | job-hub + code-hub + NICE | CompanyContext JSON | Cloud Run Job: kg-extract |
| **B. CandidateContext (DB)** | resume-hub + code-hub + NICE | CandidateContext JSON | Cloud Run Job: kg-extract |
| **B’. CandidateContext (파일)** | PDF/DOCX/HWP | CandidateContext JSON | Cloud Run Job: kg-parse + kg-extract |
| **C. Graph 적재** | A/B/B’ 출력 | Neo4j 그래프 | Cloud Run Job: kg-graph-load (<5) |

> Pipeline A+ (크롤링 보강)은 Phase 4에서 추가. 06_crawling_strategy.md 참조.
> 

> **구현 순서** (M3): 논리적 순서(A->B->B’->C)로 기술되어 있으나,
실제 구현 순서는 04.graphrag 실행 계획을 따른다:
- Phase 1 (Week 2-6): **B** (CandidateContext DB) -> C
- Phase 2 (Week 7-14): **B’** (CandidateContext 파일) -> C
- Phase 3 (Week 16-22): **A** (CompanyContext) -> C
> 
> 
> 구현 시 04.graphrag의 Phase별 일정과 상세 Task 참조
> 

---

## 2. Pipeline A: CompanyContext 생성

### 2.1 DB 직접 매핑 (LLM 비용 $0)

v19 01_company_context.md 기준 필드별 소스:

| 필드 | 소스 | 매핑 방법 | 신뢰 상한 |
| --- | --- | --- | --- |
| company_name | job-hub.job | 직접 | 0.95 |
| industry | code-hub INDUSTRY | **Tier 1** CI Lookup | 0.95 |
| tech_stack[] | job-hub.skill -> code-hub HARD_SKILL | **Tier 2** 정규화+임베딩 | 0.85 |
| career_types[] | job-hub.requirement.careers | JSONB 파싱 | 0.80 |
| education_level | job-hub.requirement | 직접 | 0.80 |
| designation | job-hub.job | 직접 | 0.95 |
| location | job-hub.work_condition | 직접 | 0.95 |
| salary_range | job-hub.work_condition | 직접 (공개 시) | 0.80 |

### 2.2 NICE Lookup (Rule 기반)

```python
# BRN 기반 NICE 직접 매칭
nice_info = nice_db.lookup(biz_registration_number)
stage_estimate = rule_engine.estimate_stage(
    employee_count=nice_info.employee_count,
    revenue=nice_info.revenue,
    founded_year=nice_info.founded_year,
    industry_code=nice_info.industry_code
)
```

> **[v16] Neo4j 적재 시 필드 매핑**:
> - `Organization.stage_label = stage_estimate.stage_label`
> - `Organization.stage_confidence = stage_estimate.stage_confidence`
> - Cypher 쿼리(`03.graphrag/separate/v6/graphrag/07_neo4j_schema.md` Q2)에서 `stage_label`로 참조한다.

### 2.3 LLM 추출 (구조화 필드 사전 주입)

**대상 필드**:
- `hiring_context` (BUILD_NEW, SCALE_EXISTING, RESET, REPLACE)
- `role_expectations` (역할 기대치)
- `operating_model` (speed, autonomy, process - 각 0.0-1.0)

- **LLM 입력**: overview.descriptions JSONB (~1,000 chars median) + 구조화 필드 힌트
- **LLM 입력 토큰**: ~2,000 (structural_tensions 제외로 v11 대비 ~200 토큰 추가 절감)

> 프롬프트 상세: 03_prompt_design.md §1 참조
> 

### 2.4 비용

- CompanyContext ~$0.00040/build (Haiku Batch, structural_tensions 제외)
- 10K JD × $0.00040 = **$4.0** (Batch: $2.0)

### [v16] 2.5 NEEDS_SIGNAL 관계 생성

Pipeline A에서 CompanyContext → Vacancy 적재 시, Vacancy→SituationalSignal 간 `NEEDS_SIGNAL` 관계를 자동 추론한다.

**방법**: 2-Track 병행

1. **Rule 기반**: `HIRING_CONTEXT_TO_SIGNALS` 매핑 테이블 적용 (`03.graphrag/separate/v6/graphrag/07_neo4j_schema.md` Q4 참조)
2. **LLM 기반**: JD 텍스트에서 SituationalSignal 직접 추출 (14개 taxonomy 기반, `01.ontology/v23/02_candidate_context.md` §2.3 정의)

**Phase 0 검증**: 50건 JD에서 Rule 기반 vs LLM 기반 precision/recall 비교
- Rule Precision ≥ 0.70, Recall ≥ 0.60 → Rule 단독 사용
- 미달 시 → LLM 보완 또는 LLM 단독으로 전환

---

## 3. Pipeline B: CandidateContext 생성 (DB)

### 3.1 DB 직접 매핑

| 필드 | 소스 | 매핑 방법 | 신뢰 상한 |
| --- | --- | --- | --- |
| company | resume-hub.Career.companyName -> NICE | **Tier 1** BRN 직접 | 0.95 |
| role_title | resume-hub.Career.position | **Tier 2** 정규화+임베딩 | 0.85 |
| period | resume-hub.Career.startDate/endDate | 직접 | 0.95 |
| tech_stack[] | resume-hub.Skill -> code-hub HARD_SKILL | **Tier 2** 정규화+임베딩 | 0.85 |
| position_grade | resume-hub.Career.positionGradeCode | 직접 (LLM 힌트) | 0.80 |
| education | resume-hub.Education | **Tier 1** 대학 alias | 0.95 |

### [v16] chapter_id 생성 규칙

Pipeline B/B'에서 CandidateContext 생성 시 chapter_id를 다음 규칙으로 부여한다:

1. Person의 모든 Experience를 `period_start` 오름차순으로 정렬
2. 0-based 인덱스 부여: `chapter_id = f"{person_id}_ch{idx}"`
3. 예시: Person `P_000001`의 3개 경력 → `P_000001_ch0`(oldest), `P_000001_ch1`, `P_000001_ch2`(latest)

> 이 규칙은 `03.graphrag/separate/v6/interface/00_data_contract.md`의 JSON Contract과 일치한다.
> `chapters[]` 배열은 `period_start` 오름차순 정렬이며, NEXT_CHAPTER 관계 구축에 사용된다.

### 3.2 LLM 추출 (Career별)

**대상 필드** (02_candidate_context.md 기준):
- `scope_type` (IC, LEAD, HEAD, FOUNDER - A1: -> Seniority 변환 포함)
- `outcomes[]` (METRIC, SCALE, DELIVERY, ORGANIZATIONAL, OTHER - 4+1 유형)
- `situational_signals[]` (14개 라벨, 5개 카테고리)

**LLM 입력**: Career.workDetails + CareerDescription + SelfIntroduction (~1,700 토큰, work_style_signals 제외로 v11 대비 ~100 토큰 추가 절감)
**힌트 활용**: positionGradeCode -> scope_type 추정 가이드

> **[v14] CareerDescription 귀속 정확도 Phase 0 검증 요건**:
> - Phase 0 PoC 20건 중 **Career 2건 이상 이력서를 최소 10건** 포함하여 LLM 귀속 정확도를 측정
> - 귀속 실패 시 resume 전체 귀속 전략의 confidence 감쇠율: **0.6 배수** 적용 (예: 원래 confidence 0.80 → 귀속 실패 시 0.48)
> - SelfIntroduction fallback(64.1%)은 특정 Career 귀속이 CareerDescription보다 어려우므로, SelfIntroduction 경유 시 confidence 감쇠율: **0.5 배수** 적용
> - **Outcome/SituationalSignal의 Career별 정확도가 전체 매칭 품질의 병목**이 될 수 있으므로, Phase 0에서 귀속 정확도 60% 미만 시 프롬프트 개선을 Phase 1 전까지 수행
>

> 프롬프트 상세: 03_prompt_design.md §2 참조
>

### 3.3 Career 수준 추출 (전체 이력 기반)

| 필드 | 추출 방법 |
| --- | --- |
| role_evolution | LLM (전체 Career 시퀀스 분석) |
| domain_depth | LLM (산업/도메인 경험 깊이) |
| career_type | Rule (EXPERIENCED 우선) |
| freshness_weight | Rule (최근 경력 가중) |

> F4(culture_fit) 활성화 시(Phase 5) 프롬프트에 복원.
> 

### 3.4 LLM 호출 전략 (M1 신규)

> 비용 2~3배 차이가 발생할 수 있는 핵심 결정
> 

**전략: Career 수 기반 적응형 호출**

| Career 수 | 호출 전략 | 예상 토큰 | 비고 |
| --- | --- | --- | --- |
| 1~3 | **1-pass** (전체 이력서 -> chapters[] + role_evolution + domain_depth) | 1,700 입력 + 2,048 출력 | 80%+ 이력서 해당 |
| 4+ | **N+1 pass** (Career별 개별 호출 N회 + 전체 요약 1회) | N × (600 입력 + 1,024 출력) + 1,000 입력 + 512 출력 | ~20% 이력서 해당 |

**1-pass 호출** (Career 1~3):

```
입력: 전체 workDetails + CareerDescription + SelfIntroduction
출력: {chapters: [ChapterExtraction × N], role_evolution, domain_depth}
max_tokens: 2,048
```

**N+1 pass 호출** (Career 4+):

```
[Pass 1~N] Career별 개별 호출:
  입력: 해당 Career의 workDetails + CareerDescription
  출력: {chapter: ChapterExtraction}
  max_tokens: 1,024

[Pass N+1] 전체 요약 호출:
  입력: 전체 Career 목록 (company + period + scope_type 결과 요약)
  출력: {role_evolution, domain_depth}
  max_tokens: 512
```

**비용 영향 추정**:
- 1-pass (80%): 400K × $0.00158 = $632 (Batch: $316)
- N+1 pass (20%): 100K × 평균 4.5회 × $0.0008 = $360 (Batch: $180)
- **총 CandidateContext DB**: $992 (Batch: **$496**) - $790(Batch $395) 대비 +25% (정확도 향상 기대)

> **[v16] 비용 변동 상세**: §2.3의 토큰 절감(~200 토큰)은 CompanyContext(Pipeline A)에서 structural_tensions 제외로 발생하며, 위 비용 증가(+25%)는 CandidateContext(Pipeline B)의 adaptive call 확대에 의한 것이다. 두 파이프라인은 독립적이므로 변동 방향이 반대일 수 있다.

**Phase 0 검증**: 20건 PoC에서 1-pass vs N+1 pass 품질/비용 비교 실측. Career 3개 분기점 조정 가능.

### 3.5 PastCompanyContext (BRN 매칭)

```
BRN 존재 (60%) -> NICE 직접 매칭 (100% 정확도)
BRN 부재 (40%) -> companyName fuzzy 매칭 (~60% 정확도)
-> 전체 매칭률: ~84% (v7: ~60%)
```

### 3.6 비용

- CandidateContext DB: **$496** (Batch, 적응형 호출 반영)
- v11 대비 변경: 1-pass/N+1 pass 적응형 전략으로 비용 +25%, 정확도 향상 기대

---

## 4. Pipeline B’: CandidateContext 생성 (파일 폴백)

> resume-hub에 없는 이력서 ~20% 처리
> 

### 4.1 파일 파싱 및 섹션 분리 (v12 S1 보강)

| 형식 | 파서 | GCP 리소스 |
| --- | --- | --- |
| PDF | Document AI OCR + Layout Parser / Gemini Multimodal | Cloud Run Job: kg-parse |
| DOCX | python-docx | Cloud Run Job: kg-parse |
| HWP | hwp5 / pyhwp → Gemini Multimodal 폴백 → **[v14] LibreOffice CLI 변환(hwp→pdf) 경유 3차 폴백** | Cloud Run Job: kg-parse |

**처리 흐름**:

```
파일 (GCS) -> Cloud Run Job: kg-parse (50 병렬, Neo4j 접근 없음)
-> 텍스트 추출 -> 섹션 분리 (§4.1.1) -> Career 블록 추출 (§4.1.2)
-> PII 마스킹 (04_pii_and_validation.md 참조)
-> Cloud Run Job: kg-extract (LLM 추출, Pipeline B와 동일 프롬프트)
```

### 4.1.1 섹션 분리 전략

> 한국 이력서는 형식이 극도로 다양하므로, Hybrid 전략 채택.
> 

**Hybrid 접근법: 패턴 기반 -> LLM 폴백**

```
Step 1: 패턴 기반 섹션 탐지 (비용 $0, 처리 시간 <1s)
  -> 성공 (70% 예상) -> Career 블록 추출 (§4.1.2)
  -> 실패 -> Step 2

Step 2: LLM 기반 섹션 분리 (비용 ~$0.002/건, 30% 대상)
  -> 전체 텍스트를 LLM에 전달, Career 구분도 LLM이 수행
```

**Step 1: 패턴 기반 섹션 탐지**

섹션 헤더 정규식:

```python
SECTION_PATTERNS = {
    "career": r'(?:경력\s*(?:사항|내역)?|EXPERIENCE|WORK\s*EXPERIENCE|Career)',
    "education": r'(?:학력\s*(?:사항)?|EDUCATION)',
    "skill": r'(?:보유\s*기술|기술\s*스택|SKILLS?|Technical)',
    "introduction": r'(?:자기\s*소개서?|ABOUT\s*ME|SUMMARY|PROFILE)',
    "project": r'(?:프로젝트|PROJECT)',
    "certificate": r'(?:자격증|자격\s*사항|CERTIFICATION)',
}
```

Career 구분 기준 (경력 섹션 내):

```python
CAREER_SEPARATOR_PATTERNS = [
    # 회사명 + 기간 패턴
    r'(?P<company>.+?)\s*[\|·/]\s*(?P<period>\d{4}[\.\-/]\d{1,2}\s*[~\-–]\s*(?:\d{4}[\.\-/]\d{1,2}|현재|재직중))',
    # 기간 + 회사명 패턴
    r'(?P<period>\d{4}[\.\-/]\d{1,2}\s*[~\-–]\s*(?:\d{4}[\.\-/]\d{1,2}|현재|재직중))\s*[\|·/]\s*(?P<company>.+)',
    # 테이블 형식 (잡코리아/사람인 양식)
    r'(?P<company>.+?)\s+(?P<position>.+?)\s+(?P<period>\d{4}\.\d{2}\s*[~\-]\s*\d{4}\.\d{2})',
]
```

**Step 2: LLM 기반 섹션 분리 (폴백)**

패턴 탐지 실패 시, 전체 텍스트를 LLM에 전달:

```
[System] You are a resume parser. Split the resume text into career blocks.
[User] 아래 이력서 텍스트에서 각 경력(Career)을 구분하여 JSON 배열로 반환하세요.
각 Career에는 company, period, role, details를 포함하세요.
경력을 구분할 수 없으면 전체를 단일 Career로 반환하세요.

{full_text}
```

**분리 실패 최종 처리**: 패턴+LLM 모두 실패 시, 전체 텍스트를 단일 Career로 취급하여 LLM 추출에 전달. scope_type confidence를 0.3으로 하향.

### 4.1.2 Career 블록 추출

섹션 분리 후 각 Career 블록에 대해:
1. 회사명, 재직 기간, 직책 추출 (패턴 또는 LLM 결과)
2. workDetails에 해당하는 텍스트 영역 매핑
3. Pipeline B와 동일한 LLM 프롬프트로 추출

**품질 차이 인지**: 파일 추출은 DB 추출 대비 필드 커버리지가 낮음. normalization_confidence에 소스 패널티 적용:
- DB 소스: confidence 상한 0.85 (기존)
- 파일 소스 (패턴 분리 성공): confidence 상한 0.75
- 파일 소스 (LLM 분리): confidence 상한 0.70

**Phase 2-0 PoC**: 3가지 접근법(패턴 only, LLM only, Hybrid) 비교 검증 (20건).

> **[v14] HWP 파서 Phase 2-0 PoC 추가 요건**: HWP 10건을 Gemini Multimodal로 처리한 결과를 포함. HWP는 한국 고유 포맷으로 Gemini의 지원 수준이 불확실하므로, 실패 시 `hwp5 → LibreOffice CLI(soffice --headless --convert-to pdf) → PDF 파서` 경유 전략을 대안으로 준비.

### 4.2 중복 제거

- **DB 이력서**: SiteUserMapping 기반
- **파일 이력서**: SimHash 기반
- **DB<->파일 교차**: 이름+전화번호 해시 매칭 -> DB 버전 우선

### 4.3 비용 추가

- 파일 파싱: ~$0.003/파일 (Document AI) 또는 ~$0.001/파일 (Gemini Multimodal)
- 섹션 분리 LLM 폴백: ~$0.002 × 30K건 (30%) = ~$60
- ~100K 파일 × $0.002 = **~$200** + 섹션 분리 **~$60** = **~$260**

---

## 5. Pipeline C: Graph 적재

### 5.1 Graph Schema 매핑

**9 Node Types** (04_graph_schema.md):

| 노드 | 속성 (핵심) | 소스 파이프라인 |
| --- | --- | --- |
| Person | person_id, name, gender, age, career_type, education_level | B/B’ |
| Organization | org_id, name, industry_code, stage, employee_count, BRN | A, NICE |
| Chapter | chapter_id, period, scope_type, seniority, domain_depth | B/B’ |
| Role | role_id, title, normalized_title, match_method | B/B’, code-hub |
| Skill | skill_id, name, normalized_name, category, match_method | B/B’, A, code-hub |
| Outcome | outcome_id, type, description, metric_value | B/B’ |
| SituationalSignal | signal_id, label (14개), category (5개), evidence | B/B’ |
| Vacancy | vacancy_id, hiring_context, role_expectations, seniority | A |
| Industry | industry_id, code, name, hierarchy | code-hub INDUSTRY |

**관계** (canonical 관계명):

| 관계 | 방향 | 소스 |
| --- | --- | --- |
| HAS_CHAPTER | Person -> Chapter | B/B’ |
| NEXT_CHAPTER | Chapter -> Chapter | B/B’ (시간순) |
| PERFORMED_ROLE | Chapter -> Role | B/B’ |
| USED_SKILL | Chapter -> Skill | B/B’ |
| OCCURRED_AT | Chapter -> Organization | B/B’ + NICE |
| PRODUCED_OUTCOME | Chapter -> Outcome | B/B’ |
| HAS_SIGNAL | Chapter -> SituationalSignal | B/B’ |
| HAS_VACANCY | Organization -> Vacancy | A |
| REQUIRES_ROLE | Vacancy -> Role | A |
| REQUIRES_SKILL | Vacancy -> Skill | A |
| NEEDS_SIGNAL | Vacancy -> SituationalSignal | A (아래 §2.5 참조) |
| IN_INDUSTRY | Organization -> Industry | code-hub |
| MAPPED_TO | Vacancy -> Person | 04.graphrag Phase 3 |

### 5.2 UNWIND 배치 적재

```
// Person 노드 배치 적재
UNWIND $batch AS row
MERGE (p:Person {person_id: row.person_id})
SET p += row.properties,
    p.loaded_batch_id = $batch_id,
    p.loaded_at = datetime()

// Chapter + 관계 배치 적재
UNWIND $batch AS row
MERGE (c:Chapter {chapter_id: row.chapter_id})
SET c += row.properties,
    c.loaded_batch_id = $batch_id,
    c.loaded_at = datetime()
WITH c, row
MATCH (p:Person {person_id: row.person_id})
MERGE (p)-[:HAS_CHAPTER]->(c)
```

**Cloud Run Job 제약**: kg-graph-load는 **동시 태스크** (Neo4j 커넥션 풀 제한)

### 5.3 3-Tier 비교 전략

| Tier | 대상 | 방법 | 임계값 | 비용 | normalization_confidence |
| --- | --- | --- | --- | --- | --- |
| 1 | 대학(~200), 기업(~500), 산업코드(~50) | CI + alias dict | exact | $0 | 0.95 |
| 2 | 스킬(~2,000) | CI -> synonyms -> embedding | 0.85 | ~$0.06 | CI: 0.95, synonyms: 0.85, embedding: 0.80 |
| 3 | 전공(~500), 직무명(~300) | embedding only (정규화 안 함) | 전공: 0.75, 직무: 0.80 | ~$0.06 | 0.70-0.80 |

**match_method 기록**: code_hub_ci, code_hub_synonyms, embedding_high, embedding_mid, embedding_low, unmatched

### 5.4 Vector Index (text-embedding-005 표준화)

```
CREATE VECTOR INDEX chapter_embedding IF NOT EXISTS
FOR (c:Chapter)
ON (c.evidence_chunk_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}}

CREATE VECTOR INDEX vacancy_embedding IF NOT EXISTS
FOR (v:Vacancy)
ON (v.evidence_chunk_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}}
```

**임베딩 모델**: `text-embedding-005` (Vertex AI, 768d, $0.0001/1K chars)
- Phase 0에서 한국어 분별력 검증 필수
- 실패 시 폴백: Cohere embed-multilingual-v3.0 (1024d) - 인덱스 재생성 필요

### 5.5 규모 추정

| 항목 | 수량 | 비고 |
| --- | --- | --- |
| Person | ~500K (DB) + ~100K (파일) | 600K 총 |
| Organization | ~50K | BRN 기반 ER 후 |
| Chapter | ~1.8M | 평균 3 careers × 600K |
| Role | ~5K (정규화 후) | code-hub JOB_CLASSIFICATION |
| Skill | ~10K (정규화 후) | code-hub HARD_SKILL + SOFT_SKILL |
| Outcome | ~3.6M | 평균 2/chapter |
| SituationalSignal | ~1.8M | 평균 1/chapter |
| Vacancy | ~10K | job-hub JD 수 |
| Industry | ~500 | code-hub INDUSTRY 계층 |
| **총 노드** | **~8M** |  |
| **총 엣지** | **~25M** | (관계 평균 3/노드) |

> **[v15] 듀얼 규모 시나리오**: 위 추정은 **v1 초기 적재 범위 600K Person** 기준이다. 전체 서비스 풀(3.2M Person)을 적재하는 경우 규모가 크게 달라진다. Phase 0에서 적재 범위를 확정한 후 아래 시나리오 중 하나를 선택한다.
>
> | 항목 | v1 초기 (600K) | 전체 풀 (3.2M) |
> |---|---|---|
> | Person | ~600K | ~3.2M |
> | Chapter | ~1.8M | ~18M |
> | 총 노드 | **~8M** | **~27M** |
> | 총 엣지 | **~25M** | **~133M** |
> | Neo4j 티어 | Professional 가능 | Enterprise 검토 필요 |
> | 비용 영향 | 06_graphrag_cost.md Professional 시나리오 | 06_graphrag_cost.md Enterprise 시나리오 (+$645~1,140) |
>
> 이 듀얼 시나리오는 `03.graphrag/separate/v6/graphrag/07_neo4j_schema.md`의 3.2M 기준 추정과 연결된다.