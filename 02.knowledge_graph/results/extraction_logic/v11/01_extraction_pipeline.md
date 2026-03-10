# Extraction Pipeline v11 — 추출 로직 중심 재정의

> 작성일: 2026-03-11 | 기준: 온톨로지 v19, GCP ML Pipeline, GraphRAG Core v2
>
> v10 대비 주요 변경: 범위를 Pipeline A/B/B'/C로 한정, D(MappingFeatures)/E(Serving API)는 04.graphrag 참조, 매칭 필드 매핑 추가, 검증 체크포인트 추가

---

## 0. 설계 원칙

1. **v19 스키마 준수**: 9 Node + v19 통합 관계 스키마
2. **DB-first, 파일 폴백**: resume-hub/job-hub/code-hub DB 우선, DB 미존재 이력서 ~20%는 파일 파싱
3. **LLM-for-reasoning**: 구조화 필드는 DB/코드 직접 매핑, LLM은 추론 필요 필드만
4. **3-Tier 비교 전략** (v19 §1.5): Tier 1 CI Lookup → Tier 2 정규화+임베딩 → Tier 3 임베딩 only
5. **GCP 네이티브**: Cloud Run Jobs(배치) + Cloud Workflows(오케스트레이션)
6. **Fail-safe**: null 허용 + dead-letter queue + 3-tier retry
7. **멱등성**: Deterministic ID + MERGE/UNWIND 패턴 + loaded_batch_id 태그
8. **비용 실용주의**: 구조화 필드 사전 주입으로 LLM 토큰 44% 절감(CompanyContext), 40% 절감(CandidateContext)

---

## 1. 파이프라인 아키텍처

### 1.1 전체 흐름 (v11 범위)

```
[Data Sources]                    [GCP Processing]                    [Graph]

resume-hub DB ─┐                  ┌─ Cloud Run Job: kg-preprocess     ┌─ Neo4j AuraDB
job-hub DB ────┼─→ DB Connectors ─┤  (정규화, PII 마스킹, 블록 분리) ──┤  (Graph MERGE)
code-hub DB ───┘                  │                                   │
NICE DB ───────→ BRN Lookup       ├─ Cloud Run Job: kg-extract        ├─ Vertex AI
PDF/DOCX/HWP ──→ File Parser ─────┤  (LLM 추출: Batch API)           │  (Vector Index)
                                  │                                   │
                                  ├─ Cloud Run Job: kg-graph-load     └─ BigQuery
                                  │  (Neo4j UNWIND 적재, ≤5 태스크)      (dead-letter)
                                  │
                                  └─ Cloud Workflows
                                     (A/B/B'/C DAG 오케스트레이션)

* Pipeline D (MappingFeatures) → 04.graphrag Phase 3 참조
* Pipeline E (Serving API) → 04.graphrag Phase 1 참조
```

### 1.2 데이터 소스 매핑 (v19 00_data_source_mapping.md 기준)

| 소스 | 파이프라인 | 매핑 대상 | 접근 방식 |
|------|-----------|----------|----------|
| resume-hub | B (CandidateContext) | Career, Skill, Education, CareerDescription, SelfIntroduction | asyncpg read replica |
| job-hub | A (CompanyContext) | job, overview, requirement, work_condition, skill | asyncpg read replica |
| code-hub | 공통 (정규화) | HARD_SKILL, SOFT_SKILL, JOB_CLASSIFICATION, INDUSTRY | Tier 1/2 lookup |
| NICE DB | A, B (기업 정보) | 기업 기본 정보, stage_estimate, PastCompanyContext | BRN 직접 매칭 |
| 파일 시스템 | B' (폴백) | PDF/DOCX/HWP 이력서 | Cloud Storage → Document AI / Gemini |

### 1.3 4개 파이프라인 정의 (v11 범위)

| 파이프라인 | 입력 | 출력 | GCP 리소스 |
|-----------|------|------|-----------|
| **A. CompanyContext** | job-hub + code-hub + NICE | CompanyContext JSON | Cloud Run Job: kg-extract |
| **B. CandidateContext (DB)** | resume-hub + code-hub + NICE | CandidateContext JSON | Cloud Run Job: kg-extract |
| **B'. CandidateContext (파일)** | PDF/DOCX/HWP | CandidateContext JSON | Cloud Run Job: kg-parse + kg-extract |
| **C. Graph 적재** | A/B/B' 출력 | Neo4j 그래프 | Cloud Run Job: kg-graph-load (≤5) |

> Pipeline A+ (크롤링 보강)은 Phase 4에서 추가. v19 06_crawling_strategy.md 참조.

---

## 2. Pipeline A: CompanyContext 생성

### 2.1 DB 직접 매핑 (LLM 비용 $0)

v19 01_company_context.md 기준 필드별 소스:

| 필드 | 소스 | 매핑 방법 | 신뢰 상한 |
|------|------|----------|----------|
| company_name | job-hub.job | 직접 | 0.95 |
| industry | code-hub INDUSTRY | **Tier 1** CI Lookup | 0.95 |
| tech_stack[] | job-hub.skill → code-hub HARD_SKILL | **Tier 2** 정규화+임베딩 | 0.85 |
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
# v19: STAGE = {EARLY, GROWTH, MATURE, ENTERPRISE}
# v19 A4: 4×4 STAGE_SIMILARITY 매트릭스 적용
```

### 2.3 LLM 추출 (구조화 필드 사전 주입)

**대상 필드** (v19 기준):
- `hiring_context` (BUILD_NEW, SCALE_EXISTING, RESET, REPLACE)
- `role_expectations` (역할 기대치)
- `operating_model` (speed, autonomy, process — 각 0.0-1.0)
- `structural_tensions` (8개 유형 분류, v1에서 대부분 null)

**LLM 입력**: overview.descriptions JSONB (~1,000 chars median) + 구조화 필드 힌트
**LLM 입력 토큰**: ~2,200 (구조화 필드 사전 주입으로 44% 절감)

> 프롬프트 상세: 03_prompt_design.md §1 참조

### 2.4 비용

- CompanyContext ~$0.00044/build (Haiku Batch)
- 10K JD × $0.00044 = **$4.4** (Batch: $2.2)

---

## 3. Pipeline B: CandidateContext 생성 (DB)

### 3.1 DB 직접 매핑

| 필드 | 소스 | 매핑 방법 | 신뢰 상한 |
|------|------|----------|----------|
| company | resume-hub.Career.companyName → NICE | **Tier 1** BRN 직접 | 0.95 |
| role_title | resume-hub.Career.position | **Tier 2** 정규화+임베딩 | 0.85 |
| period | resume-hub.Career.startDate/endDate | 직접 | 0.95 |
| tech_stack[] | resume-hub.Skill → code-hub HARD_SKILL | **Tier 2** 정규화+임베딩 | 0.85 |
| position_grade | resume-hub.Career.positionGradeCode | 직접 (LLM 힌트) | 0.80 |
| education | resume-hub.Education | **Tier 1** 대학 alias | 0.95 |

### 3.2 LLM 추출 (Career별)

**대상 필드** (v19 02_candidate_context.md 기준):
- `scope_type` (IC, LEAD, HEAD, FOUNDER — v19 A1: → Seniority 변환 포함)
- `outcomes[]` (METRIC, SCALE, DELIVERY, ORGANIZATIONAL, OTHER — 4+1 유형)
- `situational_signals[]` (14개 라벨, 5개 카테고리)

**LLM 입력**: Career.workDetails + CareerDescription + SelfIntroduction (~1,800 토큰, 40% 절감)
**힌트 활용**: positionGradeCode → scope_type 추정 가이드

> 프롬프트 상세: 03_prompt_design.md §2 참조

### 3.3 Career 수준 추출 (전체 이력 기반)

| 필드 | 추출 방법 |
|------|----------|
| role_evolution | LLM (전체 Career 시퀀스 분석) |
| domain_depth | LLM (산업/도메인 경험 깊이) |
| work_style_signals | LLM (업무 스타일 추론, v1 INACTIVE이나 추출) |
| career_type | Rule (v19: EXPERIENCED 우선) |
| freshness_weight | Rule (v19: 최근 경력 가중) |

### 3.4 PastCompanyContext (BRN 매칭)

```
BRN 존재 (60%) → NICE 직접 매칭 (100% 정확도)
BRN 부재 (40%) → companyName fuzzy 매칭 (~60% 정확도)
→ 전체 매칭률: ~84% (v7: ~60%)
```

### 3.5 비용

- CandidateContext ~$0.00158/build (~7,900 토큰)
- 500K 이력서 × $0.00158 = **$790** (Batch: ~$395)

---

## 4. Pipeline B': CandidateContext 생성 (파일 폴백)

> resume-hub에 없는 이력서 ~20% 처리

### 4.1 파일 파싱

| 형식 | 파서 | GCP 리소스 |
|------|------|-----------|
| PDF | Document AI OCR + Layout Parser / Gemini Multimodal | Cloud Run Job: kg-parse |
| DOCX | python-docx | Cloud Run Job: kg-parse |
| HWP | hwp5 / pyhwp (실패 시 Gemini Multimodal 폴백) | Cloud Run Job: kg-parse |

**처리 흐름**:
```
파일 (GCS) → Cloud Run Job: kg-parse (50 병렬, Neo4j 접근 없음)
→ 섹션 분리 → Career 블록 추출 → PII 마스킹 (04_pii_and_validation.md 참조)
→ Cloud Run Job: kg-extract (LLM 추출, Pipeline B와 동일 프롬프트)
```

### 4.2 중복 제거

- **DB 이력서**: SiteUserMapping 기반 (v9 유지)
- **파일 이력서**: SimHash 기반 (GraphRAG v2 정합)
- **DB↔파일 교차**: 이름+전화번호 해시 매칭 → DB 버전 우선

### 4.3 비용 추가

- 파일 파싱: ~$0.003/파일 (Document AI) 또는 ~$0.001/파일 (Gemini Multimodal)
- ~100K 파일 × $0.002 = **~$200**

---

## 5. Pipeline C: Graph 적재

### 5.1 v19 Graph Schema 매핑

**9 Node Types** (v19 04_graph_schema.md):

| 노드 | 속성 (핵심) | 소스 파이프라인 |
|------|-----------|--------------|
| Person | person_id, name, gender, age, career_type, education_level | B/B' |
| Organization | org_id, name, industry_code, stage, employee_count, BRN | A, NICE |
| Chapter | chapter_id, period, scope_type, seniority, domain_depth | B/B' |
| Role | role_id, title, normalized_title, match_method | B/B', code-hub |
| Skill | skill_id, name, normalized_name, category, match_method | B/B', A, code-hub |
| Outcome | outcome_id, type, description, metric_value | B/B' |
| SituationalSignal | signal_id, label (14개), category (5개), evidence | B/B' |
| Vacancy | vacancy_id, hiring_context, role_expectations, seniority | A |
| Industry | industry_id, code, name, hierarchy | code-hub INDUSTRY |

**관계** (v19 — canonical 관계명):

| 관계 | 방향 | 소스 |
|------|------|------|
| HAS_CHAPTER | Person → Chapter | B/B' |
| NEXT_CHAPTER | Chapter → Chapter | B/B' (시간순) |
| PERFORMED_ROLE | Chapter → Role | B/B' |
| USED_SKILL | Chapter → Skill | B/B' |
| OCCURRED_AT | Chapter → Organization | B/B' + NICE |
| PRODUCED_OUTCOME | Chapter → Outcome | B/B' |
| HAS_SIGNAL | Chapter → SituationalSignal | B/B' |
| HAS_VACANCY | Organization → Vacancy | A |
| REQUIRES_ROLE | Vacancy → Role | A |
| REQUIRES_SKILL | Vacancy → Skill | A |
| NEEDS_SIGNAL | Vacancy → SituationalSignal | A |
| IN_INDUSTRY | Organization → Industry | code-hub |
| MAPPED_TO | Person → Vacancy | 04.graphrag Phase 3 |

> 관계명은 v19 온톨로지가 canonical. GraphRAG Core v2의 HAD_ROLE/AT_COMPANY는 v19 기준으로 통일 권고.

### 5.2 UNWIND 배치 적재

```cypher
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

**Cloud Run Job 제약**: kg-graph-load는 **≤5 동시 태스크** (Neo4j 커넥션 풀 제한)

### 5.3 3-Tier 비교 전략 (v19 §1.5)

| Tier | 대상 | 방법 | 임계값 | 비용 | normalization_confidence |
|------|------|------|--------|------|------------------------|
| 1 | 대학(~200), 기업(~500), 산업코드(~50) | CI + alias dict | exact | $0 | 0.95 |
| 2 | 스킬(~2,000) | CI → synonyms → embedding | 0.85 | ~$0.06 | CI: 0.95, synonyms: 0.85, embedding: 0.80 |
| 3 | 전공(~500), 직무명(~300) | embedding only (정규화 안 함) | 전공: 0.75, 직무: 0.80 | ~$0.06 | 0.70-0.80 |

**match_method 기록**: code_hub_ci, code_hub_synonyms, embedding_high, embedding_mid, embedding_low, unmatched

### 5.4 compute_skill_overlap 하이브리드 (v9 유지 + v19 정합)

```python
def compute_skill_overlap(candidate_skills, vacancy_skills):
    """
    v19 §4.3 + v9 하이브리드:
    - Tier 1/2 정규화 스킬: exact match (코드 기반)
    - Tier 3 미매칭 스킬: embedding similarity
    """
    exact_matches = 0
    embedding_scores = []

    for v_skill in vacancy_skills:
        # Tier 1/2: 정규화된 코드 비교
        if v_skill.normalized_code and any(
            c.normalized_code == v_skill.normalized_code
            for c in candidate_skills
        ):
            exact_matches += 1
            continue
        # Tier 3: embedding fallback
        best_sim = max(
            cosine_similarity(v_skill.embedding, c.embedding)
            for c in candidate_skills
        )
        if best_sim >= 0.85:  # v19 임계값
            embedding_scores.append(best_sim)

    total = len(vacancy_skills)
    if total == 0:
        return 0.0

    exact_ratio = exact_matches / total
    embed_ratio = sum(embedding_scores) / total if embedding_scores else 0.0

    return exact_ratio * 1.0 + embed_ratio * 0.8  # 임베딩 매칭은 0.8 가중
```

### 5.5 Vector Index (text-embedding-005 표준화)

```cypher
CREATE VECTOR INDEX chapter_embedding IF NOT EXISTS
FOR (c:Chapter)
ON (c.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}}

CREATE VECTOR INDEX vacancy_embedding IF NOT EXISTS
FOR (v:Vacancy)
ON (v.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}}
```

**임베딩 모델**: `text-embedding-005` (Vertex AI, 768d, $0.0001/1K chars)
- Phase 0에서 한국어 분별력 검증 필수
- 실패 시 폴백: Cohere embed-multilingual-v3.0 (1024d) — 인덱스 재생성 필요

### 5.6 규모 추정 (v19 기준)

| 항목 | 수량 | 비고 |
|------|------|------|
| Person | ~500K (DB) + ~100K (파일) | 600K 총 |
| Organization | ~50K | BRN 기반 ER 후 |
| Chapter | ~1.8M | 평균 3 careers × 600K |
| Role | ~5K (정규화 후) | code-hub JOB_CLASSIFICATION |
| Skill | ~10K (정규화 후) | code-hub HARD_SKILL + SOFT_SKILL |
| Outcome | ~3.6M | 평균 2/chapter |
| SituationalSignal | ~1.8M | 평균 1/chapter |
| Vacancy | ~10K | job-hub JD 수 |
| Industry | ~500 | code-hub INDUSTRY 계층 |
| **총 노드** | **~8M** | |
| **총 엣지** | **~25M** | (관계 평균 3/노드) |

### 5.7 검증 체크포인트 (v11 신규)

> 상세: 04_pii_and_validation.md §2 참조

| 위치 | 검증 | 실패 시 |
|------|------|---------|
| DB 커넥터 출력 | 필수 필드 존재, Career 빈 이력서 필터링 | skip + 로그 |
| LLM 출력 | JSON 파싱 → Pydantic 검증 | 3-Tier 재시도 |
| Graph 적재 전 | 노드 ID 중복, 관계 무결성 | dead-letter |
| Embedding | 차원 수 768 일치, NaN 체크 | 재생성 |

---

## 6. 매칭 필드 매핑 (v11 신규)

> 매칭 함수 설계는 04.graphrag Phase 3에서 수행.
> 추출 시 매칭에 필요한 필드가 확실히 포함되도록 매핑 테이블을 정의.

### 6.1 MappingFeatures → 추출 필드 매핑

| 매칭 특성 | 가중치 | 필요 필드 (Candidate 측) | 필요 필드 (Vacancy 측) | 추출 파이프라인 |
|----------|--------|------------------------|---------------------|--------------|
| **F1 stage_match** | 25% | Chapter.OCCURRED_AT → Organization.stage | Vacancy.HAS_VACANCY → Organization.stage | B/B' + NICE, A + NICE |
| **F2 vacancy_fit** | 30% | Chapter.scope_type, Chapter.HAS_SIGNAL → SituationalSignal.label | Vacancy.hiring_context, Vacancy.NEEDS_SIGNAL → SituationalSignal.label | B/B' LLM, A LLM |
| **F3 domain_fit** | 20% | Chapter.USED_SKILL → Skill, Organization.IN_INDUSTRY → Industry | Vacancy.REQUIRES_SKILL → Skill, Organization.IN_INDUSTRY → Industry | B/B' Tier 2, A Tier 2 |
| **F4 culture_fit** | 10% | Person.work_style_signals | Organization.operating_model (speed/autonomy/process) | B/B' LLM, A LLM |
| **F5 role_fit** | 15% | Chapter.scope_type → seniority (A1 매핑), Person.role_evolution | Vacancy.seniority | B/B' LLM + Rule, A Rule |

### 6.2 추출 필수 보장 필드

위 매핑에서 **추출 시 반드시 생성해야 하는 필드**:

| 필드 | 추출 방법 | null 허용 | 매칭 영향 |
|------|----------|----------|----------|
| scope_type | LLM (positionGradeCode 힌트) | UNKNOWN 허용 | F2, F5 |
| outcomes[] | LLM | 빈 배열 허용 | 현재 미사용 (v2 예정) |
| situational_signals[] | LLM | 빈 배열 허용 | F2 |
| stage (Organization) | NICE Rule | null 허용 | F1 |
| hiring_context | LLM | UNKNOWN 허용 | F2 |
| operating_model facets | LLM (keyword count) | null 허용 | F4 (INACTIVE) |
| work_style_signals | LLM | null 허용 | F4 (INACTIVE) |
| role_evolution | LLM | null 허용 | F5 |

---

## 7. 오류 처리 및 배치 전략

### 7.1 3-Tier 재시도 (v9 유지)

| Tier | 조건 | 전략 |
|------|------|------|
| 1 | JSON 파싱 실패 | json-repair 라이브러리 |
| 2 | Pydantic 검증 실패 | temperature 0.3 → 0.5 재시도 |
| 3 | 2회 실패 | dead-letter queue (BigQuery) → 수동 검토 |

### 7.2 배치 처리 (GCP 매핑)

```
Cloud Workflows DAG (v11 범위: A/B/B'/C):
1. kg-preprocess (Cloud Run Job, 50 병렬)
   → 정규화, PII 마스킹, Career 블록 분리
   → 결과: GCS jsonl

2. kg-extract (Cloud Run Job, Batch API 제출)
   → Anthropic Batch API (1,000건/청크)
   → 결과 수집: 30분 스케줄러 폴링
   → Pydantic 검증 → 3-Tier 재시도
   → 결과: GCS jsonl

3. kg-graph-load (Cloud Run Job, ≤5 태스크)
   → Neo4j UNWIND 배치 MERGE
   → loaded_batch_id/loaded_at 태그

* 4. kg-mapping → 04.graphrag Phase 3 참조
* 5. kg-api → 04.graphrag Phase 1 참조
```

### 7.3 Dead Letter 처리

```sql
-- BigQuery dead_letter 테이블
CREATE TABLE IF NOT EXISTS `kg.dead_letter` (
    id STRING,
    pipeline STRING,  -- 'A', 'B', 'B_prime', 'C'
    source_id STRING,
    error_type STRING,
    error_message STRING,
    retry_count INT64,
    created_at TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by STRING
);
```

---

## 8. 볼륨 및 비용 요약 (v11 — 추출 범위만)

### 8.1 데이터 볼륨

| 항목 | 수량 | 비고 |
|------|------|------|
| JD (job-hub) | 10K | |
| 이력서 (resume-hub DB) | 500K | DB 직접 |
| 이력서 (파일, DB 미존재) | ~100K | PDF/DOCX/HWP 폴백 |
| Career/이력서 | 평균 3 | |
| 총 Career | ~1.8M | |

### 8.2 LLM 비용 (추출만)

| 항목 | 단가 | 수량 | 비용 | Batch 50% |
|------|------|------|------|-----------|
| CompanyContext (Haiku) | $0.00044 | 10K | $4.4 | $2.2 |
| CandidateContext DB (Haiku) | $0.00158 | 500K | $790 | $395 |
| CandidateContext 파일 (Haiku) | $0.00200 | 100K | $200 | $100 |
| 파일 파싱 (Document AI/Gemini) | $0.002 | 100K | $200 | - |
| Embedding (text-embedding-005) | - | 1.8M chapters | **$25.5** | - |
| 3-Tier 비교 임베딩 | - | ~3K canonicals | $0.12 | - |
| **추출 LLM 소계** | | | **$1,220** | **$523** |

> v10 대비 변경: Embedding 비용 $37.5 → $25.5 수정 (text-embedding-005 기준 통일)
> MappingFeatures ($50) 비용은 04.graphrag Phase 3에서 관리

### 8.3 총 비용 (추출 범위)

| 시나리오 | LLM | 비고 |
|---------|-----|------|
| **A. 추천 (Haiku Batch + DB-first)** | **$523** | Batch API 50% 할인 |
| **A'. DB-only (파일 미포함)** | $397 | 파일 파싱 비용 제외 |
| **B. Sonnet 폴백** | $2,863 | Haiku 품질 <70% 시 |
| **C. 최저 비용 (Gemini Flash)** | $288 | 비용 최적화 |

> GCP 인프라 비용, Gold Label 비용은 04.graphrag에서 통합 관리
