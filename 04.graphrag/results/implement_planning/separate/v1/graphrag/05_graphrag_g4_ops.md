# GraphRAG G-4: 증분 처리 + 운영 (3주, W24~26)

> **v5 원본**: `05_phase4_enrichment_and_ops.md` §4-3~4-5
> **트리거**: S&F 산출물 ⑤ (기업 보강 JSONL) PubSub 수신

---

## W24: 증분 처리

### 변경 감지 (v12 §1.1)

```python
# src/incremental/change_detector.py
def detect_changes(last_run_timestamp):
    new = query("SELECT * FROM resume_hub.career WHERE created_at > :last_run", last_run=last_run_timestamp)
    updated = query("SELECT * FROM resume_hub.career WHERE updated_at > :last_run AND created_at <= :last_run", ...)
    deleted = query("SELECT * FROM resume_hub.career WHERE deleted_at > :last_run", ...)
    return new, updated, deleted
```

### v4 R8: DETACH DELETE 2단계

```cypher
-- Step 1: 관계 제거 + 비공유 노드 삭제
MATCH (p:Person {person_id: $person_id})-[:HAS_CHAPTER]->(c:Chapter)
OPTIONAL MATCH (c)-[r1]->(owned) WHERE owned:Outcome OR owned:SituationalSignal
OPTIONAL MATCH (c)-[r2]->(shared) WHERE shared:Skill OR shared:Organization OR shared:Role
DELETE r1, r2, owned

-- Step 2: Chapter 삭제 + NEXT_CHAPTER 재연결
MATCH (p:Person {person_id: $person_id})-[hc:HAS_CHAPTER]->(c:Chapter)
OPTIONAL MATCH (prev:Chapter)-[nc1:NEXT_CHAPTER]->(c)
OPTIONAL MATCH (c)-[nc2:NEXT_CHAPTER]->(next:Chapter)
FOREACH (n IN CASE WHEN prev IS NOT NULL AND next IS NOT NULL THEN [1] ELSE [] END |
  MERGE (prev)-[:NEXT_CHAPTER]->(next))
DELETE nc1, nc2, hc, c
```

### v4 R7: 소프트 삭제 + 쿼리 마이그레이션

```cypher
-- 소프트 삭제
MATCH (p:Person {person_id: $person_id})
SET p.is_active = false, p.deleted_at = datetime()

-- 마이그레이션 (1회성)
MATCH (p:Person) WHERE p.is_active IS NULL SET p.is_active = true
CREATE INDEX person_active_idx FOR (p:Person) ON (p.is_active)

-- Q1~Q5 + 매칭 쿼리에 WHERE p.is_active <> false 추가
-- API 쿼리 빌더에 is_active 필터 자동 삽입 미들웨어
```

---

## W25: Cloud Workflows + 보강 적재

- Cloud Workflows 전체 DAG 구성
- S&F 산출물 ⑤ (기업 보강 JSONL) PubSub 수신 → CompanyContext 보강 적재

---

## W25-26: Gold Label + 운영 인프라

### Gold Label 2단계 (N6)

```
Phase 1: 100건 (전문가 1명 × 20시간, $2,920)
  → 전 항목 충족 시 100건으로 종료
  → 미달(±10%) 시 Phase 2: +100건 ($2,920 추가, 누적 $5,840)
```

### v5 A4: Cold Start 대응

```
대안 1: min-instances=1 → $10~15/월
대안 2: Cloud Scheduler 30분 주기 → $0
→ 에이전트 사용 빈도에 따라 선택
```

### 운영 인프라

```
□ Runbook 5종
□ Alarm 10종
□ Slack Webhook
□ Neo4j 백업 자동화
□ 인수인계 문서
```

---

## W27: Final Go/No-Go → 프로덕션 전환
