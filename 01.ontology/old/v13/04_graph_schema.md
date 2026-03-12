# 통합 Graph 스키마 v13 — 통합판

> v4 원본에 A2(Industry 노드 정의), A5(Company 간 관계 제외 명문화)를 통합.
>
> 작성일: 2026-03-10 | 기준: v4 Graph Schema + v4 amendments (A2, A5) + v12 데이터 분석 v2.1
>
> **v8 변경** (2026-03-08): [M-1] 임베딩 모델을 GCP 네이티브 `text-multilingual-embedding-002`로 통일
>
> **v10 변경** (2026-03-08): [N-3] Organization 노드에 크롤링 보강 속성을 optional로 추가하여 06_crawling_strategy.md 5.4절과 정합성 확보
>
> **v13 변경** (2026-03-10):
> - [C-1] Person 노드에 v12 데이터 분석 v2.1 기반 보강 속성 추가 (gender, age, career_type, freshness_weight, education_level)
> - Industry 노드를 code-hub INDUSTRY_SUBCATEGORY 기반으로 정합 (v11 00_data_source_mapping §1.1과 일치)

---

## 1. 노드 정의

### 1.1 Person (후보자)

```
(:Person {
  person_id: STRING,           -- 전역 고유 ID (SiteUserMapping.id)
  name: STRING,
  resume_id: STRING,
  total_experience_years: FLOAT,
  role_evolution_pattern: STRING,  -- "IC_TO_LEAD" 등
  primary_domain: STRING,

  // --- v13 보강 속성 (데이터 분석 v2.1 기반, 00_data_source_mapping §3.5) [C-1] ---
  gender: STRING | null,          -- "M" / "F" / "OTHER" (fill rate 100%, 매칭 점수에 사용 금지, 편향 모니터링 전용)
  age: INT | null,                -- 1~100 필터 적용 (fill rate 93.3%, 평균 36.2세, age>100 이상치 제거)
  career_type: STRING,            -- "EXPERIENCED" / "NEW_COMER" (fill rate 100%, EXPERIENCED 69.1%)
  freshness_weight: FLOAT,        -- 0.3~1.0 (resume.userUpdatedAt 기반, 00_data_source_mapping §3.5 참조)
  education_level: STRING | null, -- education.schoolType MAX 기반 (fill rate 95.6%, finalEducationLevel 35.6% 불일치 → schoolType 진실 소스)

  context_version: STRING,
  generated_at: DATETIME
})
```

### 1.2 Organization (기업)

**v3에서 누락되었던 Company 측 핵심 노드.** CompanyContext의 company_profile + stage_estimate를 그래프에 표현.

```
(:Organization {
  org_id: STRING,              -- company_id
  name: STRING,
  industry_code: STRING,
  industry_label: STRING,
  founded_year: INT,
  employee_count: INT,
  revenue_range: STRING,
  is_regulated_industry: BOOLEAN,
  stage_label: STRING,         -- "EARLY" / "GROWTH" / "SCALE" / "MATURE" / "UNKNOWN"
  stage_confidence: FLOAT,
  data_source: STRING,         -- "nice" / "invest_db" / "crawl"
  updated_at: DATETIME,

  // --- v1.1 크롤링 보강 속성 (optional, 크롤링 활성화 전까지 null) [v10] ---
  product_description: STRING | null,   -- 홈페이지 P2에서 추출
  market_segment: STRING | null,        -- 홈페이지 P1+P2에서 추출
  latest_funding_round: STRING | null,  -- 뉴스 N1에서 추출
  latest_funding_date: DATE | null,     -- 뉴스 N1에서 추출
  crawl_quality: FLOAT | null,          -- 크롤링 품질 지표 (0~1)
  last_crawled_at: DATETIME | null      -- 최종 크롤링 일시
})
```

> **[v10]** 크롤링 보강 속성은 `06_crawling_strategy.md` 5.4절의 Cypher 확장 스키마와 정합된다. v1에서는 모두 null이며, v1.1 크롤링 활성화 시 채워진다. v1 Neo4j 스키마 구현 시 이 속성들을 nullable로 선언해 두면 v1.1 마이그레이션 없이 바로 사용 가능하다.

### 1.3 Chapter (경험 단위)

Person의 각 Experience를 그래프 노드로 표현. v3 GraphDB의 Chapter 개념 유지.

```
(:Chapter {
  chapter_id: STRING,          -- experience_id
  title: STRING,               -- "A사 Engineering Lead"
  scope_type: STRING,          -- "IC" / "LEAD" / "HEAD" / "FOUNDER"
  period_start: STRING,        -- "2021-03"
  period_end: STRING,          -- "2023-06" | "present"
  duration_months: INT,
  scope_summary: STRING,
  evidence_chunk: STRING,      -- 이력서 원문 발췌 (Vector Index용)
  evidence_chunk_embedding: VECTOR  -- 임베딩 벡터
})
```

### 1.4 Role (역할)

```
(:Role {
  role_id: STRING,             -- 정규화된 역할 ID
  name: STRING,                -- "Backend Engineer"
  name_ko: STRING,             -- "백엔드 엔지니어"
  category: STRING             -- "engineering" / "product" / "design" / "data" / "business"
})
```

**정규화 전략**: 동의어 사전 기반. `{"팀 리더": "Team Lead", "팀장": "Team Lead", "테크리드": "Tech Lead"}`

### 1.5 Skill (기술)

```
(:Skill {
  skill_id: STRING,            -- 정규화된 스킬 ID
  name: STRING,                -- "Python"
  category: STRING,            -- "language" / "framework" / "database" / "infra" / "tool"
  aliases: STRING[]            -- ["파이썬", "py"]
})
```

### 1.6 Outcome (성과)

v3의 이중 설계(별도 노드 vs 속성)를 **별도 노드**로 확정. Evidence와 분리.

```
(:Outcome {
  outcome_id: STRING,
  description: STRING,         -- "MAU 10x 달성"
  outcome_type: STRING,        -- "METRIC" / "SCALE" / "DELIVERY" / "ORGANIZATIONAL"
  quantitative: BOOLEAN,
  metric_value: STRING,        -- "10x"
  confidence: FLOAT,
  evidence_span: STRING        -- 원문 근거
})
```

### 1.7 SituationalSignal (상황 라벨) — v4 신규

같은 상황을 경험한 후보를 그래프 탐색으로 연결하기 위한 **공유 노드**.

```
(:SituationalSignal {
  signal_id: STRING,           -- signal_label과 동일
  label: STRING,               -- "SCALE_UP" (14개 taxonomy)
  category: STRING,            -- "growth" / "org_change" / "tech_change" / "business"
  description: STRING          -- taxonomy 설명
})
```

### 1.8 Vacancy (채용 포지션) — v4 신규

CompanyContext의 vacancy를 그래프에 표현. **매칭의 기업 측 앵커.**

```
(:Vacancy {
  vacancy_id: STRING,          -- job_id
  scope_type: STRING,          -- "BUILD_NEW" / "SCALE_EXISTING" / "RESET" / "REPLACE"
  role_title: STRING,
  seniority: STRING,           -- "JUNIOR" ~ "HEAD"
  team_context: STRING,
  evidence_chunk: STRING,      -- JD 원문 발췌 (Vector Index용)
  evidence_chunk_embedding: VECTOR
})
```

### 1.9 Industry — v7 추가, v13 code-hub 정합 [v7, v13]

`:Industry` 노드는 **code-hub INDUSTRY_SUBCATEGORY (63개 코드)** 기반의 마스터 데이터로 사전 생성된다.

> **[v13]** v10까지 NICE 업종 코드를 primary로 사용했으나, v11에서 code-hub INDUSTRY 코드를 primary 산업 코드로 채택함에 따라 (00_data_source_mapping §1.1), Industry 노드의 `industry_id`도 code-hub 기준으로 변경한다. NICE 코드는 보조 소스로 교차 검증에 활용한다.

```
(:Industry {
  industry_id: STRING,        -- code-hub INDUSTRY_SUBCATEGORY 코드 (63개, primary)
  label: STRING,              -- code-hub detail_name (예: "소프트웨어 개발")
  category: STRING,           -- code-hub INDUSTRY_CATEGORY (1depth 대분류)
  category_label: STRING,     -- 대분류명
  nice_code: STRING | null,   -- NICE 업종 코드 (보조, 교차 검증용) [v13]
  is_regulated: BOOLEAN       -- 규제 산업 여부
})
```

**생성 규칙**:
- code-hub INDUSTRY_SUBCATEGORY 63개 코드 기반으로 Industry 노드를 사전 생성 (마스터 데이터)
- Organization 노드 생성 시 industry_code로 매칭하여 IN_INDUSTRY 관계 생성
- 동일 업종의 기업들이 하나의 Industry 노드를 공유 -> "같은 산업의 기업" 그래프 탐색 가능
- NICE 코드가 있는 경우 `nice_code`에 보조 저장하여 외부 데이터 교차 검증에 활용

**is_regulated 판정 기준**:

| 대분류 코드 | 대분류명 | is_regulated | 근거 |
|---|---|---|---|
| K | 금융 및 보험업 | true | 금융위원회/금감원 규제 |
| Q | 보건업 및 사회복지 서비스업 | true | 보건복지부/식약처 규제 |
| D | 전기, 가스, 증기 및 공기조절 공급업 | true | 에너지 규제 |
| H | 운수 및 창고업 | true | 교통/물류 규제 |
| 기타 | -- | false | 기본값 |

```python
REGULATED_CATEGORIES = {"K", "Q", "D", "H"}

def is_regulated_industry(industry_code):
    """code-hub INDUSTRY_CATEGORY 대분류가 규제 산업인지 판정"""
    category = lookup_common_code(type="INDUSTRY_SUBCATEGORY", code=industry_code)
    if not category:
        return False
    return category.group_code in REGULATED_CATEGORIES
```

> 세분류 수준의 규제 산업(예: J631 내 핀테크)은 v2에서 수동 태깅으로 보완한다.

---

## 2. 관계(Edge) 정의

### 2.1 후보 측 관계 (v3 유지 + 확장)

| 관계 | 설명 | edge 속성 |
|---|---|---|
| `(:Person)-[:HAS_CHAPTER]->(:Chapter)` | 후보의 경험 | seq_order: INT |
| `(:Chapter)-[:NEXT_CHAPTER]->(:Chapter)` | 시간순 궤적 | gap_months: INT |
| `(:Chapter)-[:PERFORMED_ROLE]->(:Role)` | 해당 시기의 역할 | confidence: FLOAT |
| `(:Chapter)-[:USED_SKILL]->(:Skill)` | 사용 기술 | — |
| `(:Chapter)-[:OCCURRED_AT]->(:Organization)` | 경험 배경 회사 | tenure_start, tenure_end, stage_at_tenure |
| `(:Chapter)-[:PRODUCED_OUTCOME]->(:Outcome)` | 성과 | confidence: FLOAT |
| `(:Chapter)-[:HAS_SIGNAL]->(:SituationalSignal)` | 경험한 상황 | confidence: FLOAT |

### 2.2 기업 측 관계 (v4 신규)

| 관계 | 설명 | edge 속성 |
|---|---|---|
| `(:Organization)-[:HAS_VACANCY]->(:Vacancy)` | 기업의 채용 포지션 | posted_at: DATETIME |
| `(:Vacancy)-[:REQUIRES_ROLE]->(:Role)` | 포지션이 요구하는 역할 | seniority: STRING |
| `(:Vacancy)-[:REQUIRES_SKILL]->(:Skill)` | 포지션이 요구하는 기술 | required / preferred |
| `(:Vacancy)-[:NEEDS_SIGNAL]->(:SituationalSignal)` | 포지션이 필요로 하는 상황 경험 | inferred: BOOLEAN |
| `(:Organization)-[:IN_INDUSTRY]->(:Industry)` | 산업 분류 [v7] | — |

**v7 추가 설명**: Organization 생성 시 industry_code 기준으로 자동 연결. 동일 업종 기업은 같은 Industry 노드를 공유하여 산업별 그래프 탐색을 지원한다.

### 2.3 매핑 관계 (v4 신규)

| 관계 | 설명 | edge 속성 |
|---|---|---|
| `(:Vacancy)-[:MAPPED_TO]->(:Person)` | 매핑 결과 | overall_score, generated_at |

### 2.4 v1 범위 밖 관계 — v7 추가 [v7]

v1에서 Company 간 관계를 제외하는 이유:

1. **데이터 소스 부재**: 경쟁사 관계는 뉴스/기사에서 추론 가능하나 정확도가 낮고 정의 자체가 모호
2. **MappingFeatures에 직접 기여하지 않음**: v1의 5개 피처 중 Company 간 관계가 필수 입력인 피처가 없음. domain_fit은 Industry 노드를 통해 간접 해결 (A2 참조)
3. **그래프 복잡도 관리**: Company 간 관계 추가 시 노드/관계 수 급증으로 쿼리 성능/유지보수 부담 증가

**v2 로드맵**:

| 관계 | 도입 시기 | 데이터 소스 | 활용 피처 |
|---|---|---|---|
| `(:Organization)-[:COMPETES_WITH]->(:Organization)` | v2 | 뉴스(N3) + 수동 태깅 | competitive_landscape |
| `(:Organization)-[:INVESTED_BY]->(:Investor)` | v1.1 | TheVC API | stage_estimate 보강 |
| `(:Organization)-[:ACQUIRED]->(:Organization)` | v2 | 뉴스(N3) | structural_tensions |
| `(:Organization)-[:PARTNERED_WITH]->(:Organization)` | v2 | 뉴스(N3) | domain_positioning |

---

## 3. 그래프 다이어그램

```mermaid
graph TB
    subgraph "기업 측 (v4 신규)"
        ORG[":Organization<br/>name: 스타트업A<br/>stage: GROWTH"]
        VAC[":Vacancy<br/>scope: SCALE_EXISTING<br/>seniority: SENIOR"]
        IND[":Industry<br/>label: 소프트웨어 개발<br/>is_regulated: false"]
        ORG -->|"HAS_VACANCY"| VAC
        ORG -->|"IN_INDUSTRY [v7]"| IND
        VAC -->|"REQUIRES_ROLE"| R_BE[":Role<br/>Backend Engineer"]
        VAC -->|"REQUIRES_SKILL"| S_PY[":Skill<br/>Python"]
        VAC -->|"REQUIRES_SKILL"| S_AWS[":Skill<br/>AWS"]
        VAC -->|"NEEDS_SIGNAL"| SIG_SU[":SituationalSignal<br/>SCALE_UP"]
    end

    subgraph "후보 측"
        P[":Person<br/>name: 김민아<br/>pattern: IC_TO_LEAD"]
        C1[":Chapter<br/>A사 Engineering Lead<br/>2021-03~2023-06"]
        C2[":Chapter<br/>B사 Backend Developer<br/>2019-01~2021-02"]

        P -->|"HAS_CHAPTER"| C1
        P -->|"HAS_CHAPTER"| C2
        C2 -->|"NEXT_CHAPTER"| C1

        C1 -->|"PERFORMED_ROLE"| R_LEAD[":Role<br/>Engineering Lead"]
        C1 -->|"USED_SKILL"| S_PY
        C1 -->|"USED_SKILL"| S_AWS
        C1 -->|"OCCURRED_AT"| ORG_A[":Organization<br/>A사"]
        C1 -->|"PRODUCED_OUTCOME"| O1[":Outcome<br/>MAU 10x"]
        C1 -->|"HAS_SIGNAL"| SIG_SU
        C1 -->|"HAS_SIGNAL"| SIG_TS[":SituationalSignal<br/>TEAM_SCALING"]

        C2 -->|"PERFORMED_ROLE"| R_BE
        C2 -->|"OCCURRED_AT"| ORG_B[":Organization<br/>B사"]
    end

    subgraph "매핑"
        VAC -.->|"MAPPED_TO<br/>score: 0.72"| P
    end
```

---

## 4. 핵심 그래프 탐색 쿼리 (Cypher 예시)

### Q1: vacancy_fit — 포지션이 필요로 하는 상황을 경험한 후보 탐색

```cypher
// Vacancy가 NEEDS_SIGNAL로 연결된 SituationalSignal을 경험한 후보 찾기
MATCH (v:Vacancy {vacancy_id: $job_id})
      -[:NEEDS_SIGNAL]->(sig:SituationalSignal)
      <-[:HAS_SIGNAL]-(ch:Chapter)
      <-[:HAS_CHAPTER]-(p:Person)
RETURN p.person_id,
       collect(DISTINCT sig.label) AS matched_signals,
       count(DISTINCT sig) AS match_count
ORDER BY match_count DESC
```

### Q2: stage_match — 동일 성장 단계 기업 경험 후보 탐색

```cypher
// 채용 기업과 같은 stage의 기업에서 일한 후보 찾기
MATCH (target_org:Organization {org_id: $company_id})
MATCH (ch:Chapter)-[:OCCURRED_AT]->(past_org:Organization)
WHERE past_org.stage_label = target_org.stage_label
      AND ch.duration_months >= 12  // 최소 1년 경험
MATCH (p:Person)-[:HAS_CHAPTER]->(ch)
RETURN p.person_id,
       past_org.name AS experienced_company,
       ch.duration_months,
       ch.scope_type
ORDER BY ch.duration_months DESC
```

### Q3: 유사 경험 후보 탐색 (Vector + Graph 하이브리드)

```cypher
// Step 1: Vector 검색으로 유사한 Chapter 찾기
CALL db.index.vector.queryNodes('chapter_embedding_index', 10, $jd_embedding)
YIELD node AS similar_chapter, score AS vector_score

// Step 2: 그래프 탐색으로 주변 정보 수집
MATCH (p:Person)-[:HAS_CHAPTER]->(similar_chapter)
MATCH (similar_chapter)-[:PERFORMED_ROLE]->(r:Role)
MATCH (similar_chapter)-[:USED_SKILL]->(s:Skill)
OPTIONAL MATCH (similar_chapter)-[:PRODUCED_OUTCOME]->(o:Outcome)
OPTIONAL MATCH (similar_chapter)-[:HAS_SIGNAL]->(sig:SituationalSignal)

RETURN p.person_id,
       similar_chapter.title,
       vector_score,
       collect(DISTINCT r.name) AS roles,
       collect(DISTINCT s.name) AS skills,
       collect(DISTINCT o.description) AS outcomes,
       collect(DISTINCT sig.label) AS signals
ORDER BY vector_score DESC
```

### Q4: NEEDS_SIGNAL 자동 추론 (Vacancy 생성 시)

Vacancy 노드의 `NEEDS_SIGNAL` 관계를 JD 분석에서 자동 생성하는 로직.

```python
# vacancy_scope_type → SituationalSignal 연결 (01_company_context.md의 매핑 테이블 기준)
def infer_vacancy_signals(vacancy):
    SCOPE_TO_SIGNALS = {
        "BUILD_NEW": ["NEW_SYSTEM_BUILD", "EARLY_STAGE", "PMF_SEARCH", "TEAM_BUILDING"],
        "SCALE_EXISTING": ["SCALE_UP", "TEAM_SCALING", "LEGACY_MODERNIZATION"],
        "RESET": ["LEGACY_MODERNIZATION", "TURNAROUND", "TECH_STACK_TRANSITION", "REORG"],
        "REPLACE": []
    }

    signals = SCOPE_TO_SIGNALS.get(vacancy.scope_type, [])

    # JD 텍스트에서 추가 시그널 탐지
    jd_signals = llm_extract_signals_from_jd(vacancy.evidence_chunk)
    signals = list(set(signals + jd_signals))

    return [
        ("NEEDS_SIGNAL", signal_label, {"inferred": True})
        for signal_label in signals
    ]
```

### Q5: 같은 산업의 기업에서 일한 후보 탐색 — v7 추가 [v7]

```cypher
MATCH (target:Organization {org_id: $company_id})-[:IN_INDUSTRY]->(ind:Industry)
      <-[:IN_INDUSTRY]-(similar_org:Organization)
      <-[:OCCURRED_AT]-(ch:Chapter)
      <-[:HAS_CHAPTER]-(p:Person)
RETURN p.person_id, similar_org.name, ch.scope_type
```

---

## 5. Vector Index 전략

| 대상 노드 | 임베딩 대상 텍스트 | 인덱스 용도 |
|---|---|---|
| `:Chapter` | evidence_chunk (이력서 원문 발췌) | JD ↔ 경험 유사도 검색 |
| `:Vacancy` | evidence_chunk (JD 원문 발췌) | 후보 경험 ↔ JD 유사도 검색 |
| `:Outcome` | description | 성과 유사도 검색 (v2) |

### 임베딩 모델 선택 기준

| 요구사항 | 권장 |
|---|---|
| 한국어+영어 혼합 | multilingual 모델 필수 |
| 문장~단락 수준 | sentence-level embedding |
| v1 채택 | `text-multilingual-embedding-002` (Vertex AI) — GCP 네이티브, 다국어 지원. 대안: Cohere embed-multilingual-v3.0 |

---

## 6. 기술 스택 후보

| 컴포넌트 | 옵션 A (권장) | 옵션 B | 비고 |
|---|---|---|---|
| Graph DB | **Neo4j AuraDB** | Amazon Neptune | Neo4j는 Vector Index 내장, Cypher 생태계 |
| Vector Index | Neo4j Vector Index | 별도 Pinecone/Weaviate | Neo4j 5.11+ 내장 벡터 인덱스 권장 |
| 서빙 (v1) | BigQuery 테이블 | — | Graph에서 배치 추출 후 BQ 적재 |
| LLM (추출) | GPT-4o / Claude | — | 추출 프롬프트 품질 비교 필요 |
| Embedding | **text-multilingual-embedding-002** (Vertex AI) | Cohere multilingual | GCP 네이티브, 05_evaluation_strategy와 동일 모델 [v8] |
