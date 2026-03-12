# Phase 4: 외부 보강 + 품질 + 운영 (4주, Week 24-27)

> **목적**: 홈페이지/뉴스 크롤링으로 CompanyContext 기본 필드를 보강하고,
> 품질 평가 + 자동화 + 운영 인프라를 구축하여 프로덕션 운영 상태로 전환.
>
> **v4 대비 변경**:
> - ★ v5 A4: 프로덕션 전환 시 **Cloud Run cold start 대응** 고려 사항 추가
>
> **v3 대비 변경 (v4에서 반영 완료)**:
> - R7: 소프트 삭제 도입 시 Cypher 쿼리 마이그레이션 태스크 명시 추가 (+0.5일)
> - R8: DETACH DELETE 4단계 → 2단계 통합 (트랜잭션 원자성 확보)
> - N6: Gold Label 100건 시작 → 200건 확대
>
> **데이터 확장**: Graph + Matching → **+ 기업 인텔리전스 (기본)**
> **에이전트 역량 변화**: 매칭 → **+ 기업 투자/성장 필터 + 프로덕션 운영**
>
> **인력**: DE 1명 + MLE 1명 풀타임 + 도메인 전문가 1명 파트타임 (품질 평가)

---

## 4-1. 홈페이지/뉴스 크롤링 파이프라인 (2주) — Week 24-25

> v3와 동일.

---

## 4-2. CompanyContext 보강 적재 (1주, 4-1과 병행) — Week 25

> v3와 동일 (기본 필드만).

---

## 4-3. 품질 평가 Gold Label 2단계 (N6) — Week 26 전반

### N6: 100건 시작 → 200건 확대

```
Phase 1: 100건 Gold Label (3일)
  ├─ 전문가 1명 × 20시간
  ├─ 비용: ~$2,920
  ├─ 검수 내용: 매칭 쌍 100건 (적합/부적합/애매)
  └─ 기준 달성 여부 판정

  결과별 대응:
  ├─ 전 항목 최소 기준 충족 → 100건으로 종료 (비용 $2,920)
  ├─ 일부 기준 미달 (±10% 이내) → 200건 확대하여 정밀 검증
  └─ 다수 기준 미달 → 프롬프트 재설계 + 재처리 후 100건 재검증

Phase 2 (필요 시): 200건 확대
  ├─ 추가 전문가 1명 × 20시간
  ├─ 추가 비용: ~$2,920 (누적 $5,840)
  └─ 최종 품질 보고서 작성
```

### LLM 추출 품질 평가 기준

| 지표 | 최소 기준 | 목표 |
|---|---|---|
| scope_type 분류 정확도 | > 70% | > 80% |
| outcome 추출 F1 | > 55% | > 70% |
| situational_signal 분류 F1 | > 50% | > 65% |
| vacancy scope_type 정확도 | > 65% | > 80% |
| stage_estimate 정확도 | > 75% | > 85% |
| 피처 1개+ ACTIVE 비율 | > 80% | > 90% |
| Human eval 상관관계 (r) | > 0.4 | > 0.6 |

---

## 4-4. Cloud Workflows + 증분 자동화 (1주) — Week 26

### 증분 처리 (v12 §5 전면 반영)

```python
# src/incremental/change_detector.py — v12 §1.1

def detect_changes(last_run_timestamp):
    """DB updated_at 기반 변경분 감지 (v12 §1.1)"""
    new_resumes = query("""
        SELECT * FROM resume_hub.career
        WHERE created_at > :last_run
    """, last_run=last_run_timestamp)

    updated_resumes = query("""
        SELECT * FROM resume_hub.career
        WHERE updated_at > :last_run AND created_at <= :last_run
    """, last_run=last_run_timestamp)

    deleted_resumes = query("""
        SELECT * FROM resume_hub.career
        WHERE deleted_at > :last_run
    """, last_run=last_run_timestamp)

    return new_resumes, updated_resumes, deleted_resumes
```

### v12 §1.2: 수정 유형별 처리

```python
# src/incremental/updater.py — v12 §1.2~1.4

# 구조화 vs 텍스트 필드 분류 (v12 §1.3)
STRUCTURAL_FIELDS = {"companyName", "position", "startDate", "endDate", "positionGradeCode"}
TEXT_FIELDS = {"workDetails", "careerDescription", "selfIntroduction"}

async def process_update(person_id: str, changed_fields: set, driver):
    """변경 필드에 따른 처리 분기"""

    if changed_fields & TEXT_FIELDS:
        # 텍스트 필드 변경 → 전체 재추출
        await safe_delete_chapters(driver, person_id)  # ★ v4 R8: 2단계
        await full_reextract(person_id)
    elif changed_fields & STRUCTURAL_FIELDS:
        # 구조화 필드 변경 → 부분 업데이트 (LLM 불필요)
        await partial_update(driver, person_id, changed_fields)
```

### ★ v4 R8: DETACH DELETE 4단계 → 2단계 통합

```cypher
-- ★ v4 R8: 안전한 Chapter 삭제 — 2단계 통합
-- v3의 4단계(공유 관계 제거 → 비공유 노드 삭제 → Chapter 삭제 → NEXT_CHAPTER 재연결)를
-- 2단계로 통합하여 트랜잭션 원자성 확보.

-- Step 1: 관계 제거 + 비공유 노드 삭제 (단일 트랜잭션)
MATCH (p:Person {person_id: $person_id})-[:HAS_CHAPTER]->(c:Chapter)
OPTIONAL MATCH (c)-[r1]->(owned)
  WHERE owned:Outcome OR owned:SituationalSignal
OPTIONAL MATCH (c)-[r2]->(shared)
  WHERE shared:Skill OR shared:Organization OR shared:Role OR shared:Industry
DELETE r1, r2, owned

-- Step 2: Chapter 삭제 + NEXT_CHAPTER 재연결 (단일 트랜잭션)
MATCH (p:Person {person_id: $person_id})-[hc:HAS_CHAPTER]->(c:Chapter)
OPTIONAL MATCH (prev:Chapter)-[nc1:NEXT_CHAPTER]->(c)
OPTIONAL MATCH (c)-[nc2:NEXT_CHAPTER]->(next:Chapter)
// 이전-다음 Chapter를 직접 연결
FOREACH (n IN CASE WHEN prev IS NOT NULL AND next IS NOT NULL
         THEN [1] ELSE [] END |
  MERGE (prev)-[:NEXT_CHAPTER]->(next)
)
DELETE nc1, nc2, hc, c
```

> **★ v4 R8 개선점**:
> - v3: 4개 별도 Cypher 쿼리 순차 실행 → 트랜잭션 실패 위험 4배
> - v4: 2단계 → 트랜잭션 실패 위험 2배 (50% 감소)
> - v12 §1.4의 핵심 의도(공유 노드 Skill/Organization/Role 삭제 방지) 유지
> - Step 1에서 공유 노드의 **관계만 제거**, 노드는 보존

### ★ v4 R7: 소프트 삭제 + Cypher 쿼리 마이그레이션

```cypher
-- 소프트 삭제 (v12 §1.5)
MATCH (p:Person {person_id: $person_id})
SET p.is_active = false, p.deleted_at = datetime()

MATCH (p:Person {person_id: $person_id})-[r:HAS_CHAPTER]->(c:Chapter)
SET r.is_active = false, c.is_active = false
```

```
★ v4 R7: Cypher 쿼리 마이그레이션 태스크 (Phase 4-4, +0.5일)

소프트 삭제 도입 시 반드시 수행해야 할 마이그레이션:

1. 기존 Person 노드에 is_active = true 일괄 설정
   MATCH (p:Person) WHERE p.is_active IS NULL
   SET p.is_active = true

2. is_active 인덱스 생성
   CREATE INDEX person_active_idx FOR (p:Person) ON (p.is_active)

3. Phase 1~3 Cypher 쿼리 5종 + 매칭 쿼리에 is_active 필터 추가
   모든 Person 매칭 시작점에 WHERE p.is_active <> false 추가:
   - Q1: 스킬 기반 검색
   - Q2: 시맨틱 검색
   - Q3: 회사 기반 검색
   - Q4: 시니어리티 분포
   - Q5: 복합 조건
   - 매칭 쿼리 (jd-to-candidates, candidate-to-jds)

4. GraphRAG API 쿼리 빌더에 is_active 필터 자동 삽입 로직 추가
   → 개별 쿼리에 WHERE 절 추가보다 미들웨어 방식이 누락 방지에 효과적

5. 마이그레이션 검증
   - is_active = true인 Person 수 = 마이그레이션 전 전체 수
   - is_active = false 설정 후 쿼리에서 제외되는지 확인
   - 인덱스 적용 후 쿼리 성능 변화 측정
```

### Cloud Scheduler 설정

> v3와 동일 (일일 증분, dead-letter, 월간 크롤링, 주간 백업).

---

## 4-5. 운영 인프라 + Runbook + 인수인계 (1주) — Week 27

> v3와 동일 (Runbook 5종, Alarm 10종).

### ★ v5 A4: Cloud Run Cold Start 대응

```
프로덕션 전환 시 Cloud Run cold start 고려 사항:

현재 설계:
  - Cloud Scheduler 12h 주기 (AuraDB Auto-Pause 방지 목적)
  - Cloud Run min-instances 미설정 (기본값 0)

문제:
  - 에이전트가 2시간 이상 미사용 후 검색 요청 → cold start 5-15초
  - Neo4j 연결 재설정 추가 2-3초 → 첫 응답 시간 7-18초

대안 (Phase 4 운영 전환 시 결정):
  1. min-instances=1 설정: 월 ~$10-15 추가 (idle 비용)
  2. Cloud Scheduler 주기를 30분으로 단축: $0 (월 3개 무료)
  → 에이전트 사용 빈도에 따라 선택. 빈도 높으면 (1), 낮으면 (2)
```

---

## Phase 4 완료 산출물

```
□ 홈페이지/뉴스 크롤링 파이프라인 (v3 유지)

□ CompanyContext 보강 (기본 필드만, v3 유지)

□ 품질 평가 Gold Label (N6: 2단계)
  ├─ Phase 1: 100건 ($2,920)
  ├─ Phase 2 (필요 시): +100건 ($2,920)
  └─ 비용: $2,920~$5,840

□ 자동화
  ├─ Cloud Workflows (전체 DAG)
  ├─ Cloud Scheduler (일일 증분)
  ├─ 증분 처리: v12 §1 전면 반영
  │   ├─ 변경 감지: created_at/updated_at/deleted_at
  │   ├─ 수정 유형별 분기: 구조화 vs 텍스트
  │   ├─ ★ v4 R8: DETACH DELETE 2단계 통합 (공유 노드 보호)
  │   └─ ★ v4 R7: 소프트 삭제 + Cypher 쿼리 마이그레이션
  │       ├─ 기존 Person is_active = true 일괄 설정
  │       ├─ is_active 인덱스 생성
  │       ├─ Q1~Q5 + 매칭 쿼리 is_active 필터 추가
  │       └─ API 쿼리 빌더 미들웨어 방식 적용
  └─ Makefile → Workflows 전환 완료

□ 운영 인프라 (v3 유지)
  ├─ Runbook 5종
  ├─ Alarm 10종
  ├─ Slack Webhook 연동
  ├─ Neo4j 백업 자동화
  ├─ 운영 인력 계획 (풀타임 0.3~0.5명)
  └─ 인수인계 문서

□ Go/No-Go → 운영 전환
```

---

## 예상 비용 (Phase 4, 4주)

> 상세 비용은 `06_cost_and_monitoring.md` §1.5 참조 (R2: Single Source of Truth).

| 항목 | v4 비용 | v3 대비 |
|------|--------|---------|
| Gemini API (크롤링 LLM) | ~$11 | 동일 |
| Anthropic API (Gold Label) | ~$20 | 동일 |
| Vertex AI Embedding | ~$0.1 | 동일 |
| Neo4j Professional (4주) | $100~200 | 동일 |
| Cloud Run + GCS + BQ | ~$20 | 동일 |
| Cloud Workflows + Scheduler | ~$2 | 동일 |
| **Phase 4 인프라+LLM 합계** | **$153~253** | 동일 |
| Gold Label 인건비 (N6) | **$2,920~5,840** | 동일 |
| **Phase 4 총합계** | **$3,073~6,093** | 동일 |
