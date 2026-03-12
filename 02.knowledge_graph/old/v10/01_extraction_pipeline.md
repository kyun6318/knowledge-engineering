# Extraction Pipeline v10 — v19 온톨로지 + GCP + GraphRAG 통합

> 작성일: 2026-03-11 | 기준: 온톨로지 v19, GCP ML Pipeline, GraphRAG Core v2
>
> v9 대비 주요 변경: 온톨로지 v19 정합, GCP 인프라 매핑, DB-first + 파일 폴백, text-embedding-005 표준화, Agent Serving API

---

## 0. 설계 원칙

1. **v19 스키마 준수**: 9 Node (Person, Organization, Chapter, Role, Skill, Outcome, SituationalSignal, Vacancy, Industry) + v19 통합 관계 스키마
2. **DB-first, 파일 폴백**: resume-hub/job-hub/code-hub DB 우선, DB 미존재 이력서 ~20%는 파일 파싱 (PDF/DOCX/HWP)
3. **LLM-for-reasoning**: 구조화 필드는 DB/코드 직접 매핑, LLM은 추론 필요 필드만 (scope_type, outcomes, signals, operating_model)
4. **3-Tier 비교 전략** (v19 §1.5): Tier 1 code-hub CI Lookup → Tier 2 정규화+임베딩 → Tier 3 임베딩 only
5. **GCP 네이티브**: Cloud Run Jobs(배치) + Cloud Workflows(오케스트레이션) + BigQuery(메트릭) + Vertex AI(임베딩)
6. **Fail-safe**: null 허용 + dead-letter queue + 3-tier retry
7. **멱등성**: Deterministic ID + MERGE/UNWIND 패턴 + loaded_batch_id 태그
8. **비용 실용주의**: 구조화 필드 사전 주입으로 LLM 토큰 44% 절감 (CompanyContext), 40% 절감 (CandidateContext)

---

## 1. 파이프라인 아키텍처

### 1.1 전체 흐름

```
[Data Sources]                    [GCP Processing]                    [Graph + Serving]

resume-hub DB ─┐                  ┌─ Cloud Run Job: kg-preprocess     ┌─ Neo4j AuraDB
job-hub DB ────┼─→ DB Connectors ─┤  (정규화, PII 마스킹, 블록 분리) ──┤  (Graph MERGE)
code-hub DB ───┘                  │                                   │
NICE DB ───────→ BRN Lookup       ├─ Cloud Run Job: kg-extract        ├─ Vertex AI
PDF/DOCX/HWP ──→ File Parser ─────┤  (LLM 추출: Batch API)           │  (Vector Index)
                                  │                                   │
                                  ├─ Cloud Run Job: kg-graph-load     ├─ BigQuery
                                  │  (Neo4j UNWIND 적재, ≤5 태스크)   │  (MappingFeatures)
                                  │                                   │
                                  ├─ Cloud Run Job: kg-mapping        ├─ Cloud Run Service
                                  │  (매칭 점수 계산)                  │  (Agent Serving API)
                                  │                                   │
                                  └─ Cloud Workflows                  └─ Cloud Scheduler
                                     (전체 DAG 오케스트레이션)            (증분/크롤링/백업)
```

### 1.2 데이터 소스 매핑 (v19 00_data_source_mapping.md 기준)

| 소스 | 파이프라인 | 매핑 대상 | 접근 방식 |
|------|-----------|----------|----------|
| resume-hub | B (CandidateContext) | Career, Skill, Education, CareerDescription, SelfIntroduction | asyncpg read replica |
| job-hub | A (CompanyContext) | job, overview, requirement, work_condition, skill | asyncpg read replica |
| code-hub | 공통 (정규화) | HARD_SKILL, SOFT_SKILL, JOB_CLASSIFICATION, INDUSTRY | Tier 1/2 lookup |
| NICE DB | A, B (기업 정보) | 기업 기본 정보, stage_estimate, PastCompanyContext | BRN 직접 매칭 |
| 파일 시스템 | B' (폴백) | PDF/DOCX/HWP 이력서 | Cloud Storage → Document AI / Gemini |
| 크롤링 (T3/T4) | A+ (Phase 3) | 홈페이지/뉴스 → CompanyContext 보강 | Playwright + Gemini Flash |

### 1.3 5개 파이프라인 정의

| 파이프라인 | 입력 | 출력 | GCP 리소스 |
|-----------|------|------|-----------|
| **A. CompanyContext** | job-hub + code-hub + NICE | CompanyContext JSON | Cloud Run Job: kg-extract |
| **A+. CompanyContext 보강** | 크롤링 (T3/T4) | CompanyContext 필드 업데이트 | Cloud Run Job: kg-crawl |
| **B. CandidateContext (DB)** | resume-hub + code-hub + NICE | CandidateContext JSON | Cloud Run Job: kg-extract |
| **B'. CandidateContext (파일)** | PDF/DOCX/HWP | CandidateContext JSON | Cloud Run Job: kg-parse + kg-extract |
| **C. Graph 적재** | A/A+/B/B' 출력 | Neo4j 그래프 | Cloud Run Job: kg-graph-load (≤5) |
| **D. MappingFeatures** | Neo4j 그래프 | BigQuery 매칭 테이블 | Cloud Run Job: kg-mapping |
| **E. Serving** | BigQuery + Neo4j | REST API 응답 | Cloud Run Service: kg-api |

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
- vacancy.scope_type (hiring_context: BUILD_NEW, SCALE_EXISTING, RESET, REPLACE)
- role_expectations (역할 기대치)
- operating_model (speed, autonomy, process — v19에서 v1 INACTIVE이나 추출은 수행)
- structural_tensions (v19 A6: 8개 유형 분류)

**LLM 입력 토큰**: ~2,200 (v9 대비 동일, 구조화 필드 사전 주입으로 44% 절감)

**비용**: ~$0.00044/build (Haiku Batch) 또는 ~$0.00084 (크롤링 포함)

### 2.4 크롤링 보강 (Pipeline A+, Phase 3)

v19 06_crawling_strategy.md 기준:

| 소스 유형 | 대상 페이지 | 추출 필드 | 비용 |
|----------|-----------|----------|------|
| T3 홈페이지 | About(P1), Product(P2), Careers(P3), Blog(P4), Team(P5), Customers(P6) | product_description, market_segment, employee_count, founded_year | ~$107/월 |
| T4 뉴스 | Funding(N1), Product(N2), M&A(N3), Org(N4), Performance(N5) | funding_round, funding_amount, investors, growth_narrative | (포함) |

**기술 스택**: Playwright + Cloud Run Job + Readability + Gemini 2.0 Flash
**크롤링 정책**: robots.txt 준수, 2초 간격, 최대 10페이지, 30일 재크롤 주기

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
- scope_type (v19 A1: → Seniority 변환 포함)
- outcomes[] (v19: METRIC, SCALE, DELIVERY, ORGANIZATIONAL 4유형)
- situational_signals[] (v19: 14개 라벨, 5개 카테고리)

**LLM 입력**: Career.workDetails + CareerDescription + SelfIntroduction (~1,800 토큰, 40% 절감)
**힌트 활용**: positionGradeCode → scope_type 추정 가이드

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

> v10 신규: resume-hub에 없는 이력서 ~20% 처리

### 4.1 파일 파싱 (GraphRAG v2 Phase 2 정합)

| 형식 | 파서 | GCP 리소스 |
|------|------|-----------|
| PDF | Document AI OCR + Layout Parser / Gemini Multimodal | Cloud Run Job: kg-parse |
| DOCX | python-docx | Cloud Run Job: kg-parse |
| HWP | hwp5 / pyhwp | Cloud Run Job: kg-parse |

**처리 흐름**:
```
파일 (GCS) → Cloud Run Job: kg-parse (50 병렬, Neo4j 접근 없음)
→ 섹션 분리 → Career 블록 추출 → PII 마스킹
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
| Outcome | outcome_id, type (METRIC/SCALE/DELIVERY/ORGANIZATIONAL), description | B/B' |
| SituationalSignal | signal_id, label (14개), category (5개), evidence | B/B' |
| Vacancy | vacancy_id, scope_type, hiring_context, role_expectations | A |
| Industry | industry_id, code, name, hierarchy | code-hub INDUSTRY |

**관계** (v19):

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
| MAPPED_TO | Person → Vacancy | D (매칭 결과) |

### 5.2 UNWIND 배치 적재 (GraphRAG v2 개선)

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

### 5.3 3-Tier 비교 전략 (v19 §1.5 + v9 유지)

| Tier | 대상 | 방법 | 임계값 | 비용 | normalization_confidence |
|------|------|------|--------|------|------------------------|
| 1 | 대학(~200), 기업(~500), 산업코드(~50) | CI + alias dict | exact | $0 | 0.95 |
| 2 | 스킬(~2,000) | CI → synonyms → embedding | 0.85 | ~$0.06 | CI: 0.95, synonyms: 0.85, embedding: 0.80 |
| 3 | 전공(~500), 직무명(~300) | embedding only (정규화 안 함) | 전공: 0.75, 직무: 0.80 | ~$0.06 | 0.70-0.80 |

**match_method 기록**: code_hub_ci, code_hub_synonyms, embedding_high, embedding_mid, embedding_low, unmatched

### 5.4 Vector Index (v10: text-embedding-005 표준화)

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
- v9의 text-multilingual-embedding-002에서 변경 (GraphRAG v2 표준화)
- Phase 0에서 한국어 분별력 검증 필수

### 5.5 규모 추정 (v19 기준)

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

---

## 6. Pipeline D: MappingFeatures 계산

### 6.1 v19 MappingFeatures 5대 특성 (확정)

| 특성 | 가중치 | 계산 방법 | v1 상태 |
|------|--------|----------|---------|
| **F1 stage_match** | 25% | v19 A4 STAGE_SIMILARITY 4×4 매트릭스 | ACTIVE |
| **F2 vacancy_fit** | 30% | hiring_context + situational_signals 정합 | ACTIVE |
| **F3 domain_fit** | 20% | 임베딩 + code-hub 산업코드 매칭 | ACTIVE |
| **F4 culture_fit** | 10% | operating_model facets vs work_style (대부분 v1 INACTIVE) | MOSTLY INACTIVE |
| **F5 role_fit** | 15% | seniority + role_evolution 매칭 (v19 A1 ScopeType→Seniority) | ACTIVE |

### 6.2 stage_match 계산 (v19 A4)

```python
STAGE_SIMILARITY = {
    ('EARLY', 'EARLY'): 1.0,    ('EARLY', 'GROWTH'): 0.6,
    ('EARLY', 'MATURE'): 0.2,   ('EARLY', 'ENTERPRISE'): 0.1,
    ('GROWTH', 'EARLY'): 0.5,   ('GROWTH', 'GROWTH'): 1.0,
    ('GROWTH', 'MATURE'): 0.5,  ('GROWTH', 'ENTERPRISE'): 0.2,
    ('MATURE', 'EARLY'): 0.2,   ('MATURE', 'GROWTH'): 0.5,
    ('MATURE', 'MATURE'): 1.0,  ('MATURE', 'ENTERPRISE'): 0.6,
    ('ENTERPRISE', 'EARLY'): 0.1, ('ENTERPRISE', 'GROWTH'): 0.2,
    ('ENTERPRISE', 'MATURE'): 0.6, ('ENTERPRISE', 'ENTERPRISE'): 1.0,
}
```

### 6.3 compute_skill_overlap 하이브리드 (v9 유지 + v19 정합)

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
        # v10 R-1: 현재 brute-force O(n×m). canonical ~2,800개 수준에서는 문제없으나,
        # 유니크 스킬 수만 개 시 FAISS IndexFlatIP로 전환 (구현 10줄, Phase 2 성능 이슈 시)
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

### 6.4 매칭 점수 및 MAPPED_TO 생성

```python
def compute_match_score(candidate, vacancy):
    """v19 MappingFeatures 가중치 적용"""
    scores = {
        'stage_match': compute_stage_match(candidate, vacancy),    # 25%
        'vacancy_fit': compute_vacancy_fit(candidate, vacancy),    # 30%
        'domain_fit': compute_domain_fit(candidate, vacancy),      # 20%
        'culture_fit': compute_culture_fit(candidate, vacancy),    # 10%
        'role_fit': compute_role_fit(candidate, vacancy),          # 15%
    }
    weights = {'stage_match': 0.25, 'vacancy_fit': 0.30, 'domain_fit': 0.20,
               'culture_fit': 0.10, 'role_fit': 0.15}

    # freshness_weight 적용 (v19)
    total = sum(scores[k] * weights[k] for k in scores)
    total *= candidate.freshness_weight

    return total, scores

# MAPPED_TO 임계값: 0.4 (GraphRAG v2 정합)
```

### 6.5 BigQuery 서빙 테이블

```sql
CREATE TABLE IF NOT EXISTS `kg.mapping_features` (
    person_id STRING,
    vacancy_id STRING,
    total_score FLOAT64,
    stage_match FLOAT64,
    vacancy_fit FLOAT64,
    domain_fit FLOAT64,
    culture_fit FLOAT64,
    role_fit FLOAT64,
    freshness_weight FLOAT64,
    feature_active_flags STRUCT<
        stage BOOL, vacancy BOOL, domain BOOL, culture BOOL, role BOOL
    >,
    computed_at TIMESTAMP,
    model_version STRING,
    loaded_batch_id STRING
);
```

---

## 7. Pipeline E: Agent Serving API (v10 신규)

> GraphRAG v2 Phase 1 MVP 정합

### 7.1 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| POST | /api/v1/search/skills | 스킬 기반 후보자 검색 |
| POST | /api/v1/search/semantic | 시맨틱 벡터 검색 |
| POST | /api/v1/search/compound | 복합 검색 (스킬 + 시맨틱 + 필터) |
| GET | /api/v1/candidates/{id} | 후보자 상세 |
| POST | /api/v1/match/jd-to-candidates | JD → 후보자 매칭 (Phase 3) |
| POST | /api/v1/match/candidate-to-jds | 후보자 → JD 역매칭 (Phase 3) |
| GET | /api/v1/companies/{org_id} | 기업 정보 (Phase 3) |
| GET | /api/v1/health | 헬스 체크 |

### 7.2 기술 스택

- **프레임워크**: FastAPI
- **배포**: Cloud Run Service (asia-northeast3)
- **인증**: API Key + 100 req/min rate limit
- **데이터 소스**: Neo4j (그래프 쿼리) + BigQuery (MappingFeatures) + Vertex AI (벡터 검색)

---

## 8. 오류 처리 및 배치 전략

### 8.1 3-Tier 재시도 (v9 유지)

| Tier | 조건 | 전략 |
|------|------|------|
| 1 | JSON 파싱 실패 | json-repair 라이브러리 |
| 2 | Pydantic 검증 실패 | temperature 0.3 → 0.5 재시도 |
| 3 | 2회 실패 | dead-letter queue (BigQuery) → 수동 검토 |

### 8.2 배치 처리 (GCP 매핑)

```
Cloud Workflows DAG:
1. kg-preprocess (Cloud Run Job, 50 병렬)
   → 정규화, PII 마스킹, Career 블록 분리
   → 결과: GCS jsonl

2. kg-extract (Cloud Run Job, Batch API 제출)
   → Anthropic Batch API (1,000건/청크)
   → 결과 수집: 30분 스케줄러 폴링
   → 결과: GCS jsonl

3. kg-graph-load (Cloud Run Job, ≤5 태스크)
   → Neo4j UNWIND 배치 MERGE
   → loaded_batch_id/loaded_at 태그

4. kg-mapping (Cloud Run Job)
   → MappingFeatures 계산
   → BigQuery 적재
   → MAPPED_TO 그래프 반영
```

### 8.3 Dead Letter 처리

```sql
-- BigQuery dead_letter 테이블
CREATE TABLE IF NOT EXISTS `kg.dead_letter` (
    id STRING,
    pipeline STRING,  -- 'A', 'B', 'B_prime', 'C', 'D'
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

## 9. 볼륨 및 비용 요약 (v10)

### 9.1 데이터 볼륨

| 항목 | 수량 | 비고 |
|------|------|------|
| JD (job-hub) | 10K | |
| 이력서 (resume-hub DB) | 500K | DB 직접 |
| 이력서 (파일, DB 미존재) | ~100K | PDF/DOCX/HWP 폴백 |
| Career/이력서 | 평균 3 | |
| 총 Career | ~1.8M | |
| 매칭 쌍 | ~5M | 10K × 500 shortlisting |

### 9.2 LLM 비용

| 항목 | 단가 | 수량 | 비용 | Batch 50% |
|------|------|------|------|-----------|
| CompanyContext (Haiku) | $0.00044 | 10K | $4.4 | $2.2 |
| CandidateContext DB (Haiku) | $0.00158 | 500K | $790 | $395 |
| CandidateContext 파일 (Haiku) | $0.00200 | 100K | $200 | $100 |
| 파일 파싱 (Document AI/Gemini) | $0.002 | 100K | $200 | - |
| Embedding (text-embedding-005) | - | 1.8M chapters | $37.5 | - |
| 3-Tier 비교 임베딩 | - | ~3K canonicals | $0.12 | - |
| MappingFeatures | - | 5M pairs | $50 | - |
| **LLM 소계** | | | **$1,282** | **$585** |

### 9.3 GCP 인프라 비용 (27주)

| 항목 | 월 비용 | 27주 비용 | 비고 |
|------|---------|----------|------|
| Neo4j AuraDB (Free→Pro) | $0→$100-200 | $600-1,200 | Phase 2부터 Pro |
| Cloud Run Jobs | ~$50 | $300 | 배치 처리 |
| Cloud Run Service (API) | ~$14 | $84 | Agent Serving |
| BigQuery | ~$10 | $60 | 메트릭/매핑/dead-letter |
| GCS | ~$6 | $36 | 중간 결과/백업 |
| Cloud Workflows | ~$1 | $6 | 오케스트레이션 |
| Cloud Scheduler | ~$2 | $12 | 4개 Job |
| Secret Manager | ~$1 | $6 | API 키 관리 |
| Vertex AI (임베딩) | - | $38 | 1회성 |
| **인프라 소계** | | **$1,142-1,742** | |

### 9.4 총 비용

| 시나리오 | LLM | 인프라 | Gold Label | 총액 | KRW |
|---------|-----|--------|-----------|------|-----|
| **A. 추천 (Haiku Batch + DB-first)** | $585 | $1,142 | $5,840 | **$7,567** | ~1,037만 |
| **A'. 파일 미포함 (DB-only)** | $447 | $1,042 | $5,840 | **$7,329** | ~1,005만 |
| **B. Sonnet 폴백** | $2,925 | $1,742 | $5,840 | **$10,507** | ~1,440만 |
| **C. 최저 비용 (Gemini Flash)** | $350 | $1,042 | $5,840 | **$7,232** | ~991만 |

---

## 10. 모니터링 메트릭 (v19 + GraphRAG v2 정합)

### 10.1 자동 품질 메트릭 (BigQuery quality_metrics)

| 메트릭 | 목표 | 체크 시점 |
|--------|------|----------|
| schema_compliance | ≥95% | 배치 완료 후 |
| required_field_rate | ≥90% | 배치 완료 후 |
| skill_code_match_rate | ≥70% | Tier 1/2 완료 후 |
| embedding_coverage | ≥85% | Tier 2/3 완료 후 |
| scope_type_accuracy | ≥70% | Gold Label 검증 |
| outcome_f1 | ≥55% | Gold Label 검증 |
| signal_f1 | ≥50% | Gold Label 검증 |
| stage_estimate_accuracy | ≥75% | Gold Label 검증 |
| features_active_rate | ≥80% | MappingFeatures 후 |
| human_correlation | ≥0.4 | Gold Label 검증 |

### 10.2 GraphRAG vs Vector Baseline 실험 (v19 05_evaluation_strategy.md)

| 메트릭 | 측정 대상 |
|--------|----------|
| Precision@5 | Top-5 중 적합 비율 |
| Recall@5 | 전체 적합 중 Top-5 포함 비율 |
| NDCG@5 | 순위 품질 |
| MRR | 첫 적합 결과 순위 |
| Cohen's d | 효과 크기 (≥0.5 목표) |
| Inter-rater agreement | 평가자 간 일치도 |

**실험 설계**: 50 JD × 5 평가자, paired t-test, 4가지 Decision Case
