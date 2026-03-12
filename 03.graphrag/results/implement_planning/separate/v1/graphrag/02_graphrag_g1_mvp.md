# GraphRAG G-1: MVP 적재 + API (2주, W5~6)

> **v5 원본**: `02_phase1_core_candidate_mvp.md` §1-D
> **트리거**: S&F 산출물 ② (CandidateContext 1,000건 JSONL) PubSub 수신

---

## W5: 1,000건 그래프 적재

### PubSub 트리거 → 자동 수신 → 적재

```
PubSub (kg-artifact-ready, artifact_type="candidate")
  → Cloud Run Job 자동 기동
  → GCS에서 JSONL 읽기
  → JSON Schema 검증
  → UNWIND Batch 적재
```

### 적재 코드 (v19 관계명)

```python
# src/graph/load_candidate.py — v19 canonical 관계명
def load_candidates_batch(driver, candidates: list[dict], batch_size: int = 100):
    batch_id = f"load_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i:i + batch_size]
        with driver.session() as session:
            # Person 노드
            session.run("""
                UNWIND $batch AS c
                MERGE (p:Person {person_id: c.person_id})
                SET p.career_type = c.career_type, p.education_level = c.education_level,
                    p.role_evolution = c.role_evolution, p.domain_depth = c.domain_depth,
                    p.loaded_batch_id = $batch_id, p.loaded_at = datetime()
            """, batch=batch, batch_id=batch_id)

            # Chapter + HAS_CHAPTER + NEXT_CHAPTER
            chapters = []
            for c in batch:
                for j, ch in enumerate(c.get("chapters", [])):
                    chapters.append({
                        "chapter_id": f"{c['person_id']}_ch{j}",
                        "person_id": c["person_id"],
                        "scope_type": ch.get("scope_type"),
                        "period_start": ch.get("period_start"),
                        "period_end": ch.get("period_end"),
                        "skills": ch.get("skills", []),
                        "role": ch.get("role"),
                        "company": ch.get("company"),
                    })

            session.run("""
                UNWIND $chapters AS ch
                MERGE (c:Chapter {chapter_id: ch.chapter_id})
                SET c.scope_type = ch.scope_type, c.period_start = ch.period_start,
                    c.period_end = ch.period_end, c.loaded_batch_id = $batch_id
                WITH c, ch
                MATCH (p:Person {person_id: ch.person_id})
                MERGE (p)-[:HAS_CHAPTER]->(c)
            """, chapters=chapters, batch_id=batch_id)

            # PERFORMED_ROLE, OCCURRED_AT, USED_SKILL (v19)
            # ... (각 관계 UNWIND)
```

### G-7: Idempotency + 롤백 테스트

---

## W6: Cypher 쿼리 + REST API

### Cypher 쿼리 5종 (v19)

```cypher
-- Q1: 스킬 기반 검색
MATCH (p:Person)-[:HAS_CHAPTER]->(c:Chapter)-[:USED_SKILL]->(s:Skill)
WHERE s.name IN $skills
WITH p, COUNT(DISTINCT s) AS matched WHERE matched >= $min_match
RETURN p, matched ORDER BY matched DESC LIMIT $limit

-- Q2: 시맨틱 검색 (Vector Search)
CALL db.index.vector.queryNodes('chapter_embedding', $top_k, $query_embedding)
YIELD node, score
MATCH (p:Person)-[:HAS_CHAPTER]->(node)
RETURN p, node, score ORDER BY score DESC

-- Q3: 회사 기반 검색 (OCCURRED_AT)
MATCH (p:Person)-[:HAS_CHAPTER]->(c:Chapter)-[:OCCURRED_AT]->(o:Organization)
WHERE o.name CONTAINS $company_name
RETURN p, c, o

-- Q4: 시니어리티 분포
MATCH (p:Person)-[:HAS_CHAPTER]->(c:Chapter) WHERE c.scope_type = $scope_type
RETURN p, c

-- Q5: 복합 조건 (PERFORMED_ROLE)
MATCH (p:Person)-[:HAS_CHAPTER]->(c:Chapter) WHERE c.scope_type IN $seniority_levels
WITH p, c
MATCH (c)-[:USED_SKILL]->(s:Skill) WHERE s.name IN $skills
WITH p, COUNT(DISTINCT s) AS skill_match WHERE skill_match >= $min_skills
RETURN p ORDER BY skill_match DESC LIMIT $limit
```

### REST API + PII 필터링 (N2)

```python
# src/api/main.py
from fastapi import FastAPI

app = FastAPI(title="GraphRAG API", version="1.2")

PII_FIELDS = {"name", "email", "phone", "address", "birth_date"}

def filter_pii(data: dict) -> dict:
    if isinstance(data, dict):
        return {k: filter_pii(v) for k, v in data.items() if k not in PII_FIELDS}
    elif isinstance(data, list):
        return [filter_pii(item) for item in data]
    return data

@app.get("/api/v1/candidates/{candidate_id}")
async def get_candidate(candidate_id: str):
    raw = fetch_candidate_from_neo4j(candidate_id)
    return filter_pii(raw)

@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "neo4j": "connected"}
```

### Cloud Scheduler (N1)

```bash
gcloud scheduler jobs create http graphrag-api-keepalive \
  --schedule="0 */12 * * *" \
  --uri="https://graphrag-api-HASH-an.a.run.app/api/v1/health" \
  --http-method=GET --time-zone="Asia/Seoul"
```

---

## G-1 산출물

```
□ Neo4j MVP (1K Person/Chapter/Skill/Role/Organization/Industry)
□ NEXT_CHAPTER 연결 (chapters[] 순서)
□ Cypher 쿼리 5종
□ REST API (PII 필터링, API Key, Rate limiting, /health)
□ Cloud Scheduler 12h keepalive
□ PubSub 자동 적재 파이프라인
□ E2E 검증 + 스팟체크 50건
```
