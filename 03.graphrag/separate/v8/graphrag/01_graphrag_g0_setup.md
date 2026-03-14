> DE Day 2-3
> 

---

## Neo4j AuraDB Free 설정

- [ ]  Neo4j AuraDB Free 인스턴스 생성(AuraDB Free Auto-Pause)
    - 72시간 비활성 시 자동 일시 중지
    - Phase 0에서는 매일 작업
    - Phase G-1 API 배포(W6) 시 Cloud Scheduler health check 설정 필수 (N1)
- [ ]  Graph 스키마 적용
    - PERFORMED_ROLE, OCCURRED_AT, HAS_CHAPTER, USED_SKILL, NEXT_CHAPTER
    - IN_INDUSTRY
- [ ]  Vector Index 설정 (768d, cosine)

### Graph 스키마

```
Phase 1 (Candidate-Only):
  Person ──[HAS_CHAPTER]──-> Chapter
    │                          │──[USED_SKILL]──-> Skill
    │                          │──[PERFORMED_ROLE]──-> Role
    │                          │──[OCCURRED_AT]──-> Organization
    │──────[HAS_CHAPTER]─────->└──[NEXT_CHAPTER]──-> Chapter
    └──(through Organization)──[IN_INDUSTRY]──-> Industry

  Vector Index: chapter_embedding (768d, text-embedding-005)
```

```
Phase G-3 (Company + Matching):
  Organization ──[HAS_VACANCY]──-> Vacancy ──[REQUIRES_ROLE]──-> Role
                                    │──[REQUIRES_SKILL]──-> Skill
                                    └──[NEEDS_SIGNAL]──-> SituationalSignal

  Vacancy ──[MAPPED_TO]──-> Person
  Chapter ──[PRODUCED_OUTCOME]──-> Outcome
  Chapter ──[HAS_SIGNAL]──-> SituationalSignal

  추가 Vector Index: vacancy_embedding (768d)
```

### [v7] SituationalSignal 초기화

14개 고정 taxonomy 공유 노드를 사전 생성한다 (`01.ontology/v25/02_candidate_context.md` §2.3 정의).

```cypher
// SituationalSignal 14개 공유 노드 사전 생성
UNWIND [
  "EARLY_STAGE", "SCALE_UP", "TURNAROUND", "GLOBAL_EXPANSION",
  "TEAM_BUILDING", "TEAM_SCALING", "REORG",
  "LEGACY_MODERNIZATION", "NEW_SYSTEM_BUILD", "TECH_STACK_TRANSITION",
  "PMF_SEARCH", "MONETIZATION", "ENTERPRISE_TRANSITION", "OTHER"
] AS label
MERGE (s:SituationalSignal {signal_id: label})
SET s.label = label,
    s.category = CASE
      WHEN label IN ["EARLY_STAGE", "SCALE_UP", "TURNAROUND", "GLOBAL_EXPANSION"] THEN "growth"
      WHEN label IN ["TEAM_BUILDING", "TEAM_SCALING", "REORG"] THEN "org_change"
      WHEN label IN ["LEGACY_MODERNIZATION", "NEW_SYSTEM_BUILD", "TECH_STACK_TRANSITION"] THEN "tech"
      WHEN label IN ["PMF_SEARCH", "MONETIZATION", "ENTERPRISE_TRANSITION"] THEN "business"
      ELSE "other"
    END
```

> Phase 1 적재 시작 전 1회 실행. 이후 HAS_SIGNAL, NEEDS_SIGNAL 관계는 이 노드들을 참조한다.

---

## UNWIND 배치 적재 코드 골격

```python
# src/graph/load_candidate.py - 골격 (G-0에서 준비, G-1에서 실행)
def load_candidates_batch(driver, candidates: list[dict], batch_size: int = 100):
    batch_id = f"load_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i:i + batch_size]
        with driver.session() as session:
            # Person, Chapter, Skill, Role, Organization 적재 (v25)
            ...
```

---

## 대기 구간 A (W2~4) - 선행 작업 (~2주)

- [ ]  GraphRAG REST API 설계 (FastAPI, 라우트 정의)
- [ ]  Cypher 쿼리 5종 초안 + Mock 데이터 테스트
- [ ]  PII 필터 미들웨어 설계 + 단위 테스트 (N2)
- [ ]  NEXT_CHAPTER 연결 로직 설계 + 테스트 데이터
- [ ]  GCS->PubSub->Cloud Run Job 자동 적재 트리거 구축