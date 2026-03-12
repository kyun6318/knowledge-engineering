# Phase 4: 외부 보강 + 품질 + 운영 (4주, Week 24-27)

> **목적**: 홈페이지/뉴스 크롤링으로 CompanyContext 기본 필드를 보강하고,
> 품질 평가 + 자동화 + 운영 인프라를 구축하여 프로덕션 운영 상태로 전환.
>
> **v2 대비 변경**:
> - N6: Gold Label 100건 시작 → 결과에 따라 200건 확대 (2단계 접근)
> - v12 §5 증분 처리 전략 전면 반영 (DETACH DELETE 시 공유 노드 보호)
>
> **데이터 확장**: Graph + Matching → **+ 기업 인텔리전스 (기본)**
> **에이전트 역량 변화**: 매칭 → **+ 기업 투자/성장 필터 + 프로덕션 운영**
>
> **인력**: DE 1명 + MLE 1명 풀타임 + 도메인 전문가 1명 파트타임 (품질 평가)

---

## 4-1. 홈페이지/뉴스 크롤링 파이프라인 (2주) — Week 24-25

> v2와 동일.

---

## 4-2. CompanyContext 보강 적재 (1주, 4-1과 병행) — Week 25

> v2와 동일 (기본 필드만).

---

## 4-3. 품질 평가 ★ Gold Label 2단계 (N6) — Week 26 전반

### ★ N6: 100건 시작 → 200건 확대

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

### LLM 추출 품질 평가 기준 (v2 유지)

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

### 증분 처리 (★ v12 §5 전면 반영)

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

### ★ v12 §1.2: 수정 유형별 처리

```python
# src/incremental/updater.py — v12 §1.2~1.4

# 구조화 vs 텍스트 필드 분류 (v12 §1.3)
STRUCTURAL_FIELDS = {"companyName", "position", "startDate", "endDate", "positionGradeCode"}
TEXT_FIELDS = {"workDetails", "careerDescription", "selfIntroduction"}

async def process_update(person_id: str, changed_fields: set, driver):
    """변경 필드에 따른 처리 분기"""

    if changed_fields & TEXT_FIELDS:
        # 텍스트 필드 변경 → 전체 재추출
        await safe_detach_delete_chapters(driver, person_id)  # v12 §1.4
        await full_reextract(person_id)
    elif changed_fields & STRUCTURAL_FIELDS:
        # 구조화 필드 변경 → 부분 업데이트 (LLM 불필요)
        await partial_update(driver, person_id, changed_fields)
```

### ★ v12 §1.4: DETACH DELETE 시 공유 노드 보호

```cypher
-- v12 §1.4: 안전한 Chapter 삭제 (공유 노드 보호)

-- Step 1: Chapter → 공유 노드 관계만 제거 (노드 유지)
MATCH (c:Chapter {chapter_id: $chapter_id})-[r]->(shared)
WHERE shared:Skill OR shared:Organization OR shared:Role OR shared:Industry
DELETE r

-- Step 2: Chapter → 비공유 노드 관계 + 노드 삭제
MATCH (c:Chapter {chapter_id: $chapter_id})-[r]->(owned)
WHERE owned:Outcome OR owned:SituationalSignal
DELETE r, owned

-- Step 3: Person → Chapter 관계 + Chapter 삭제
MATCH (p:Person)-[r:HAS_CHAPTER]->(c:Chapter {chapter_id: $chapter_id})
DELETE r, c

-- Step 4: NEXT_CHAPTER 관계 재연결
MATCH (prev:Chapter)-[:NEXT_CHAPTER]->(deleted)
WHERE deleted.chapter_id = $chapter_id
MATCH (deleted)-[:NEXT_CHAPTER]->(next:Chapter)
MERGE (prev)-[:NEXT_CHAPTER]->(next)
```

### ★ v12 §1.5: 소프트 삭제

```cypher
-- 소프트 삭제 (v12 §1.5)
MATCH (p:Person {person_id: $person_id})
SET p.is_active = false, p.deleted_at = datetime()

MATCH (p:Person {person_id: $person_id})-[r:HAS_CHAPTER]->(c:Chapter)
SET r.is_active = false, c.is_active = false

-- ★ 모든 쿼리에 is_active: true 필터 필수
-- GraphRAG API의 모든 Cypher 쿼리에 필터 추가
```

### Cloud Scheduler 설정

> v2와 동일 (일일 증분, dead-letter, 월간 크롤링, 주간 백업).

---

## 4-5. 운영 인프라 + Runbook + 인수인계 (1주) — Week 27

> v2와 동일 (Runbook 5종, Alarm 10종).

---

## Phase 4 완료 산출물

```
□ 홈페이지/뉴스 크롤링 파이프라인 (v2 유지)

□ CompanyContext 보강 (기본 필드만, v2 유지)

□ ★ 품질 평가 Gold Label (N6: 2단계)
  ├─ Phase 1: 100건 ($2,920)
  ├─ Phase 2 (필요 시): +100건 ($2,920)
  └─ 비용: $2,920~$5,840

□ 자동화
  ├─ Cloud Workflows (전체 DAG)
  ├─ Cloud Scheduler (일일 증분)
  ├─ ★ 증분 처리: v12 §1 전면 반영
  │   ├─ 변경 감지: created_at/updated_at/deleted_at
  │   ├─ 수정 유형별 분기: 구조화 vs 텍스트
  │   ├─ DETACH DELETE 시 공유 노드 보호 (v12 §1.4)
  │   └─ 소프트 삭제 (v12 §1.5)
  └─ Makefile → Workflows 전환 완료

□ 운영 인프라 (v2 유지)
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

| 항목 | v3 비용 | v2 대비 |
|------|--------|---------|
| Gemini API (크롤링 LLM) | ~$11 | 동일 |
| Anthropic API (Gold Label) | ~$20 | 동일 |
| Vertex AI Embedding | ~$0.1 | 동일 |
| Neo4j Professional (4주) | $100~200 | 동일 |
| Cloud Run + GCS + BQ | ~$20 | 동일 |
| Cloud Workflows + Scheduler | ~$2 | 동일 |
| **Phase 4 인프라+LLM 합계** | **$153~253** | 동일 |
| ★ Gold Label 인건비 (N6) | **$2,920~5,840** | **-$2,920 가능** |
| **Phase 4 총합계** | **$3,073~6,093** | -$2,920~동일 |
