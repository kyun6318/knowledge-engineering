> 작성일: 2026-03-12
> 01.ontology/results/schema/v20/04_graph_schema.md §4-§9에서 이동.
> Neo4j 구현 상세 (Cypher, Vector Index, 인덱스, 동기화)를 GraphRAG 구현 영역으로 분리.

---

## 4. 핵심 그래프 탐색 쿼리 (Cypher 예시)

### Q1: vacancy_fit - 포지션이 필요로 하는 상황을 경험한 후보 탐색

```
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

### Q2: stage_match - 동일 성장 단계 기업 경험 후보 탐색

```
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

```
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
# vacancy hiring_context -> SituationalSignal 연결 (01_company_context.md의 매핑 테이블 기준)
# [v17] scope_type -> hiring_context 명칭 변경 반영
def infer_vacancy_signals(vacancy):
    HIRING_CONTEXT_TO_SIGNALS = {
        "BUILD_NEW": ["NEW_SYSTEM_BUILD", "EARLY_STAGE", "PMF_SEARCH", "TEAM_BUILDING"],
        "SCALE_EXISTING": ["SCALE_UP", "TEAM_SCALING", "LEGACY_MODERNIZATION"],
        "RESET": ["LEGACY_MODERNIZATION", "TURNAROUND", "TECH_STACK_TRANSITION", "REORG"],
        "REPLACE": []
    }

    signals = HIRING_CONTEXT_TO_SIGNALS.get(vacancy.hiring_context, [])

    # JD 텍스트에서 추가 시그널 탐지
    jd_signals = llm_extract_signals_from_jd(vacancy.evidence_chunk)
    signals = list(set(signals + jd_signals))

    return [
        ("NEEDS_SIGNAL", signal_label, {"inferred": True})
        for signal_label in signals
    ]
```

> **NEEDS_SIGNAL 자동 추론 파일럿 검증 계획 [R-5]**: `HIRING_CONTEXT_TO_SIGNALS` 매핑은 전문가 판단 기반 초기값이며, 이 매핑의 타당성이 검증되지 않은 상태이다. v1 파일럿에서 다음 검증을 수행한다:
>
> | 단계 | 방법 | 규모 | 성공 기준 |
> | --- | --- | --- | --- |
> | 1차 | 50건 JD에서 자동 추론 결과 vs 채용 전문가 수동 태깅 비교 | 50건 × 14 signals | Precision >= 0.70, Recall >= 0.60 |
> | 2차 | 자동 추론 signal이 실제 매칭 품질에 기여하는지 분석 | 파일럿 전체 | NEEDS_SIGNAL 매칭 활성화 시 vacancy_fit 점수 분포 분석 |
> - **1차 검증 미달 시**: HIRING_CONTEXT_TO_SIGNALS 매핑 테이블을 채용 전문가 피드백으로 보정하고, JD LLM 추출의 비중을 높인다.
> - **Precision 낮음** (불필요한 signal 과다): `HIRING_CONTEXT_TO_SIGNALS`의 strong -> moderate 또는 제거로 보정.
> - **Recall 낮음** (필요한 signal 누락): JD 텍스트 기반 LLM 추출에 더 의존하도록 전략 조정.

### Q5: 같은 산업의 기업에서 일한 후보 탐색

```
MATCH (target:Organization {org_id: $company_id})-[:IN_INDUSTRY]->(ind:Industry)
      <-[:IN_INDUSTRY]-(similar_org:Organization)
      <-[:OCCURRED_AT]-(ch:Chapter)
      <-[:HAS_CHAPTER]-(p:Person)
RETURN p.person_id, similar_org.name, ch.scope_type
```

---

## 5. Vector Index 전략

| 대상 노드 | 임베딩 대상 텍스트 | 인덱스 용도 |
| --- | --- | --- |
| `:Chapter` | evidence_chunk (이력서 원문 발췌) | JD <-> 경험 유사도 검색 |
| `:Vacancy` | evidence_chunk (JD 원문 발췌) | 후보 경험 <-> JD 유사도 검색 |
| `:Outcome` | description | 성과 유사도 검색 (v2) |

### 임베딩 모델 선택 기준

| 요구사항 | 권장 |
| --- | --- |
| 한국어+영어 혼합 | multilingual 모델 필수 |
| 문장~단락 수준 | sentence-level embedding |
| v1 채택 | **[v4] `text-embedding-005`** (Vertex AI, 768d) - GCP 네이티브, 다국어 지원. `02.knowledge_graph/v14/02_model_and_infrastructure.md`와 통일. 대안: Cohere embed-multilingual-v3.0 (1024d) |

---

## 6. 기술 스택 후보

| 컴포넌트 | 옵션 A (권장) | 옵션 B | 비고 |
| --- | --- | --- | --- |
| Graph DB | **Neo4j AuraDB** | Amazon Neptune | Neo4j는 Vector Index 내장, Cypher 생태계 |
| Vector Index | Neo4j Vector Index | 별도 Pinecone/Weaviate | Neo4j 5.11+ 내장 벡터 인덱스 권장 |
| 서빙 (v1) | BigQuery 테이블 | - | Graph에서 배치 추출 후 BQ 적재 |
| LLM (추출) | GPT-4o / Claude | - | 추출 프롬프트 품질 비교 필요 |
| Embedding | **text-embedding-005** (Vertex AI, 768d) | Cohere multilingual (1024d) | GCP 네이티브, 02.knowledge_graph 02_model_and_infrastructure와 동일 모델 [v4] |

---

## 7. 노드/엣지 규모 추정 [v14 신규]

> **[v4] 적재 범위 확정 및 규모 추정 통일**:
> - 본 문서의 규모 추정(3.2M Person 기반)은 **전체 서비스 가용 풀**(PUBLIC+COMPLETED) 기준이다.
> - `02.knowledge_graph/v14/01_extraction_pipeline.md`의 규모 추정(600K Person 기반)은 **v1 초기 적재 범위**(EXPERIENCED + HIGH/PREMIUM 품질) 기준이다.
> - **Phase 0에서 적재 범위를 확정**하고, 아래 추정치를 확정된 범위로 갱신한다.
> - `00_data_source_mapping.md §3.1`의 필터 기준: 전체 5.5M → EXPERIENCED 3.7M → HIGH+PREMIUM 3.2M

서비스 풀 ~3.2M 이력서 기준으로 Neo4j에 적재될 노드/엣지 규모를 추정한다. (v1 초기 적재는 600K 규모로 시작, `01_extraction_pipeline.md §5.5` 참조)

### 7.1 노드 규모

| 노드 | 추정 수량 | 산출 근거 |
| --- | --- | --- |
| Person | ~3.2M | 서비스 가용 이력서 풀 (PUBLIC+COMPLETED) |
| Chapter | ~18M | 경력 보유자 기준, 이력서당 평균 ~5.6건 |
| Organization | ~500K | Career.companyName 4.48M 고유값 -> 정규화 후 추정 |
| Role | 242 | code-hub JOB_CLASSIFICATION_SUBCATEGORY 코드 수 |
| Skill | ~100K | 고유 스킬 101,925개 (정규화 후 ~50K 예상) |
| Industry | 63 | code-hub INDUSTRY_SUBCATEGORY 코드 수 |
| Outcome | ~5M | 이력서당 평균 ~2.3개 추출 예상 (Outcome 보유 ~65% × 3.2M) |
| SituationalSignal | 14 | 고정 taxonomy (공유 노드) |
| Vacancy | ~100K+ | job-hub 공고 수 (Phase 4-1에서 확정) |

### 7.2 관계(엣지) 규모

| 관계 | 추정 수량 | 산출 근거 |
| --- | --- | --- |
| HAS_CHAPTER | ~18M | Person -> Chapter (1:N) |
| NEXT_CHAPTER | ~15M | Chapter 간 시간순 연결 (경력 2건 이상) |
| PERFORMED_ROLE | ~18M | Chapter당 1개 |
| USED_SKILL | ~50M | Chapter당 평균 ~2.8개 스킬 |
| OCCURRED_AT | ~18M | Chapter당 1개 Organization |
| PRODUCED_OUTCOME | ~5M | Outcome 보유 Chapter |
| HAS_SIGNAL | ~8M | Chapter당 평균 ~1.5개 signal (보유 시) |
| IN_INDUSTRY | ~500K | Organization당 1개 |
| HAS_VACANCY | ~100K+ | Organization -> Vacancy |
| REQUIRES_ROLE | ~100K+ | Vacancy당 1개 |
| REQUIRES_SKILL | ~300K+ | Vacancy당 평균 ~3개 |
| NEEDS_SIGNAL | ~200K+ | Vacancy당 평균 ~2개 |
| MAPPED_TO | ~10M+ | 매핑 결과 (운영 후 증가, 아래 TTL 정책 참조) |

### 7.3 MAPPED_TO 엣지 수명 관리 정책 [v15 신규, v1.1+ 검토]

MAPPED_TO 엣지는 매핑이 수행될 때마다 생성되며, 정책 없이 운영하면 무한 증가하여 그래프 성능에 영향을 줄 수 있다. 다음 TTL/아카이빙 정책을 적용한다.

| 정책 | 기준 | 처리 |
| --- | --- | --- |
| **활성 유지** | 생성 후 90일 이내 **또는** 90일 이내 조회된 매핑 | Neo4j에 유지 |
| **아카이빙** | 90일 이상 미조회 **且** Vacancy가 마감된 매핑 | Neo4j에서 삭제, BigQuery `mapping_features_archive` 테이블로 이관 |
| **영구 삭제** | 아카이빙 후 1년 경과 | BigQuery 아카이브에서도 삭제 |

> 아래 TTL/아카이빙 정책은 v1 파일럿 단계에서는 구현하지 않는다. 매핑 결과 자체가 없는 상태에서 아카이빙 정책을 구현하는 것은 시기상조이며, 운영 데이터가 축적된 후(6개월+) 실제 MAPPED_TO 엣지 증가 속도를 관측하고 정책을 수립한다. v1에서는 `last_accessed_at` 속성만 유지하고, 아카이빙 로직은 구현하지 않는다.

```python
def archive_stale_mappings():
    """
    주간 배치로 실행. 90일 이상 미조회 + Vacancy 마감인 MAPPED_TO 엣지를
    BigQuery 아카이브로 이관 후 Neo4j에서 삭제.
    """
    stale_cutoff = datetime.now() - timedelta(days=90)

    # 1. 아카이빙 대상 식별
    stale_mappings = neo4j_query("""
        MATCH (v:Vacancy)-[m:MAPPED_TO]->(p:Person)
        WHERE m.generated_at < $cutoff
          AND (m.last_accessed_at IS NULL OR m.last_accessed_at < $cutoff)
          AND v.status = 'CLOSED'
        RETURN v.vacancy_id, p.person_id, m.overall_score, m.generated_at
    """, cutoff=stale_cutoff)

    # 2. BigQuery 아카이브 적재
    bq_insert("mapping_features_archive", stale_mappings)

    # 3. Neo4j에서 삭제 (배치 단위, 트랜잭션당 1000건)
    for batch in chunked(stale_mappings, 1000):
        neo4j_query("""
            UNWIND $batch AS row
            MATCH (v:Vacancy {vacancy_id: row.vacancy_id})
                  -[m:MAPPED_TO]->(p:Person {person_id: row.person_id})
            DELETE m
        """, batch=batch)
```

> **MAPPED_TO 엣지 속성 추가**: TTL 관리를 위해 `last_accessed_at: DATETIME` 속성을 MAPPED_TO 엣지에 추가한다. 매핑 결과가 조회될 때마다 갱신한다.

### 7.4 총 규모 요약

| 구분 | 수량 |
| --- | --- |
| **총 노드** | ~27M |
| **총 관계** | ~133M+ |
| **Neo4j AuraDB 요구 tier** | Professional 이상 (Free: 200K 노드/400K 관계 한계 초과) |

> **사전 PoC**: 이 규모에서 Q1~Q5 쿼리의 응답 시간이 1초 이내인지, AuraDB Professional/Enterprise tier에서 감당 가능한지 사전 검증 필요. 파일럿에서 ~10K Person + ~50K Chapter 규모로 먼저 테스트한 후 full-scale 적재를 진행한다.
>
> **[v4] Neo4j 티어 확정을 Phase 0 필수 의사결정으로 격상**:
> - AuraDB Professional의 노드 상한이 "800K+"로만 기술되어 있어, 27M 노드 수용 가능 여부가 불확실
> - **Phase 0(W1)에서 Neo4j 영업팀에 사이징 문의를 선행**하고, Go/No-Go에 "Neo4j 티어 확정"을 Phase 0 필수 의사결정으로 추가
> - Professional 불가 판정 시 AuraDB Enterprise(월 $500+) 또는 자체 호스팅으로 전환 필요
> - 비용 영향: Enterprise 시나리오 추가 시 27주 기준 $2,100~3,500 (→ `06_graphrag_cost.md` 반영)

---

## 8. Neo4j 인덱스 전략

Q1~Q5 쿼리 성능을 보장하기 위한 인덱스 정의.

### 8.1 고유성 제약 (Unique Constraints)

```
CREATE CONSTRAINT person_id_unique FOR (p:Person) REQUIRE p.person_id IS UNIQUE;
CREATE CONSTRAINT org_id_unique FOR (o:Organization) REQUIRE o.org_id IS UNIQUE;
CREATE CONSTRAINT vacancy_id_unique FOR (v:Vacancy) REQUIRE v.vacancy_id IS UNIQUE;
CREATE CONSTRAINT role_id_unique FOR (r:Role) REQUIRE r.role_id IS UNIQUE;
CREATE CONSTRAINT skill_id_unique FOR (s:Skill) REQUIRE s.skill_id IS UNIQUE;
CREATE CONSTRAINT industry_id_unique FOR (i:Industry) REQUIRE i.industry_id IS UNIQUE;
CREATE CONSTRAINT signal_id_unique FOR (ss:SituationalSignal) REQUIRE ss.signal_id IS UNIQUE;
```

### 8.2 탐색 인덱스

```
-- Q2 stage_match: Organization.stage_label 기반 탐색
CREATE INDEX org_stage_label FOR (o:Organization) ON (o.stage_label);

-- Q1/Q5: 복합 탐색
CREATE INDEX chapter_duration FOR (c:Chapter) ON (c.duration_months);

-- Person 검색
CREATE INDEX person_career_type FOR (p:Person) ON (p.career_type);

-- [v15] Organization.name 풀텍스트 인덱스 (PastCompanyContext 보강 시 회사명 기반 탐색)
CREATE FULLTEXT INDEX org_name_fulltext FOR (o:Organization) ON EACH [o.name];
```

### 8.3 Vector Index

```
-- Q3 하이브리드 검색
CREATE VECTOR INDEX chapter_embedding_index
FOR (c:Chapter) ON (c.evidence_chunk_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

CREATE VECTOR INDEX vacancy_embedding_index
FOR (v:Vacancy) ON (v.evidence_chunk_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};
```

---

## 9. BigQuery-Neo4j 데이터 동기화 전략

서빙(BigQuery)과 그래프 탐색(Neo4j) 간 데이터 일관성을 보장하기 위한 동기화 방안.

### 9.1 동기화 방향

```
[resume-hub / job-hub] ──-> [ETL Pipeline] ──┬──-> [Neo4j] (그래프 탐색, Q1~Q5)
                                             └──-> [BigQuery] (서빙, SQL 조회)
```

- **주로 단방향 동기화**: 원본 DB -> Neo4j + BigQuery가 기본 흐름
- **매핑 결과만 역방향**: MAPPED_TO 엣지는 Neo4j에서 생성되어 BigQuery로 역방향 적재. 이 1건의 역방향 흐름을 제외하면 Neo4j는 읽기 전용이다 [v15 N14-4 정확화]

### 9.2 동기화 주기

| 데이터 유형 | 동기화 주기 | 트리거 | 비고 |
| --- | --- | --- | --- |
| Person/Chapter/Skill 노드 | 일간 (배치) | Cloud Scheduler | 신규/변경 이력서 증분 |
| Organization/Industry 노드 | 주간 (배치) | Cloud Scheduler | NICE 데이터 갱신 주기 |
| Vacancy 노드 | 일간 (배치) | Cloud Scheduler | 신규 공고 증분 |
| MAPPED_TO 관계 | 실시간 (이벤트) | 매핑 완료 후 | 매핑 파이프라인에서 직접 적재 |
| 크롤링 보강 속성 | 월간 | 크롤링 완료 후 | 06_crawling_strategy 재크롤링 주기와 동일 |

### 9.3 증분 동기화 원칙

> **범위 축소**: 에러 핸들링(DLQ, exponential backoff), 배치 크기, 정합성 검증 등의 **구현 상세는 02.knowledge_graph 구현 단계에서 정의**한다. 온톨로지 설계 문서에서는 동기화 대상과 Cypher 패턴만 기술한다.

**동기화 Cypher 패턴**:

```
-- Person/Chapter 노드 증분 동기화
MERGE (p:Person {person_id: $person_id}) SET p += $props

-- Organization 노드 증분 동기화
MERGE (o:Organization {org_id: $org_id}) SET o += $props

-- Vacancy 노드 증분 동기화
MERGE (v:Vacancy {vacancy_id: $vacancy_id}) SET v += $props

-- MAPPED_TO 관계 생성 (매핑 결과)
MATCH (v:Vacancy {vacancy_id: $vacancy_id})
MATCH (p:Person {person_id: $person_id})
MERGE (v)-[m:MAPPED_TO]->(p)
SET m.overall_score = $overall_score,
    m.generated_at = datetime($generated_at),
    m.last_accessed_at = datetime($generated_at)
```

**구현 시 고려사항** (상세는 02.knowledge_graph에서 정의):
- 배치 단위 트랜잭션 처리 (권장 1,000건/트랜잭션)
- 실패 시 재시도 정책 (exponential backoff)
- 부분 실패 처리 (DLQ 기록)
- 동기화 완료 후 count 비교 정합성 검증
