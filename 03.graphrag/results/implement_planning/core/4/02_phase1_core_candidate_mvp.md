# Phase 1: Core Candidate MVP — DB 텍스트 + 에이전트 API (5주, Week 2~6)

> **목적**: DB 데이터를 CandidateContext로 변환 + Graph MVP + 에이전트 서빙 API 완성.
>
> **v3 대비 변경**:
> - R1: PII 마스킹 오프셋 버그 수정 — re.sub 콜백 방식으로 전면 교체
> - R3: CMEK 버킷 생성을 Phase 0 → **Phase 1-B로 이동** (Go 판정 후)
>
> **데이터 확장**: 없음 → **DB 텍스트 이력서 1,000건** (+ 크롤링 허용 시 추가)
> **에이전트 역량 변화**: 없음 → **REST API를 통한 후보자 검색**
>
> **인력**: DE 1명 + MLE 1명 풀타임
> **산출물**: 1,000건 E2E Graph + GraphRAG REST API + 에이전트 연동 가능 MVP

---

## 1-A. 크롤링 파이프라인 (Week 2~3, DE 담당) — 선택적

> v3와 동일 (법무 허용 시에만 진행).

---

## 1-B. 전처리 모듈 (Week 2~3, MLE 담당)

> v3 기반 + ★ v4 R1/R3 적용.

### ★ R3: CMEK 버킷 생성 (Phase 0에서 이동)

```bash
# ★ v4 R3: Phase 0에서 Phase 1-B로 이동
# Go/No-Go 판정 후 (Week 2 시작 시) 생성

# PII 매핑 테이블 전용 버킷 (CMEK)
gcloud storage buckets create gs://kg-pii-mapping \
  --location=asia-northeast3 \
  --uniform-bucket-level-access

# Cloud KMS 키 생성
gcloud kms keyrings create kg-pii-keyring \
  --location=asia-northeast3
gcloud kms keys create kg-pii-key \
  --location=asia-northeast3 \
  --keyring=kg-pii-keyring \
  --purpose=encryption

# CMEK 적용
gcloud storage buckets update gs://kg-pii-mapping \
  --default-encryption-key=projects/graphrag-kg/locations/asia-northeast3/keyRings/kg-pii-keyring/cryptoKeys/kg-pii-key

# PII 읽기 전용 서비스 계정
gcloud iam service-accounts create kg-pii-reader \
  --display-name="KG PII Reader (Read-Only)"
gcloud storage buckets add-iam-policy-binding gs://kg-pii-mapping \
  --member="serviceAccount:kg-pii-reader@graphrag-kg.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

### PII 마스킹 (★ v4 R1: re.sub 콜백 방식으로 수정)

```python
# src/pii/masker.py — v4: R1 오프셋 버그 수정 + v12 S2/S4

import re
from google.cloud import storage

# v12 S4: 한국 전화번호 8종 종합 패턴
PHONE_PATTERNS = [
    r'(?:\+82[-\s]?)?0?1[016789][-.\s)]*\d{3,4}[-.\s]?\d{4}',
    r'0[2-6][0-9]?[-.\s]?\d{3,4}[-.\s]?\d{4}',
]

# 주민번호, 이메일
SSN_PATTERN = r'\d{6}-\d{7}'
EMAIL_PATTERN = r'[\w.-]+@[\w.-]+\.\w+'

def mask_pii(text: str, person_id: str) -> tuple[str, dict]:
    """PII 마스킹 + 매핑 생성

    ★ v4 R1: re.sub 콜백 방식으로 오프셋 버그 수정.
    v3에서는 re.finditer로 순차 치환 시 텍스트 길이 변경으로 인해
    후속 매칭의 오프셋이 틀어지는 치명적 버그가 있었음.
    """
    mapping = {}
    masked = text

    # 전화번호 (v12 S4: 8종 커버) — ★ v4 R1: re.sub 콜백
    masked, phone_mapping = mask_phones(masked)
    mapping.update(phone_mapping)

    # 주민번호 (즉시 삭제, 매핑 미저장)
    masked = re.sub(SSN_PATTERN, '[SSN_REMOVED]', masked)

    # 이메일 — ★ v4 R1: re.sub 콜백
    masked, email_mapping = mask_emails(masked)
    mapping.update(email_mapping)

    return masked, mapping


def mask_phones(text: str) -> tuple[str, dict]:
    """전화번호 마스킹 — re.sub 콜백 방식 (R1)"""
    mapping = {}
    counter = [0]

    def replacer(m):
        token = f"[PHONE_{counter[0]:03d}]"
        mapping[token] = m.group()
        counter[0] += 1
        return token

    for pattern in PHONE_PATTERNS:
        text = re.sub(pattern, replacer, text)

    return text, mapping


def mask_emails(text: str) -> tuple[str, dict]:
    """이메일 마스킹 — re.sub 콜백 방식 (R1)"""
    mapping = {}
    counter = [0]

    def replacer(m):
        token = f"[EMAIL_{counter[0]:03d}]"
        mapping[token] = m.group()
        counter[0] += 1
        return token

    text = re.sub(EMAIL_PATTERN, replacer, text)
    return text, mapping


# v12 S2: PII 매핑 테이블을 GCS CMEK 버킷에 저장
def save_pii_mapping(person_id: str, mapping: dict):
    """PII 매핑을 GCS CMEK 버킷에 JSONL로 저장"""
    import json
    client = storage.Client()
    bucket = client.bucket('kg-pii-mapping')
    blob = bucket.blob(f'mappings/{person_id}.json')
    blob.upload_from_string(json.dumps({
        'person_id': person_id,
        'mapping': mapping,
    }), content_type='application/json')
```

### 전처리 흐름 (v12 기준)

```
resume-hub DB → DB 커넥터
  → CP1: 입력 검증 (v12 §2.2)
  → PII 마스킹 (v12 S4 전화번호 8종, ★ v4 R1: re.sub 콜백)
  → PII 매핑 → GCS CMEK (v12 S2, ★ v4 R3: Phase 1-B에서 생성)
  → CP2: 마스킹 검증 (v12 §2.3)
  → Career 블록 분리
  → GCS jsonl (마스킹됨)
```

---

## 1-C. CandidateContext LLM 추출 (Week 4~5)

> v3와 동일 (v12 프롬프트 + 적응형 호출 전략).

### 적응형 LLM 호출 (v12 M1)

```python
# src/extractors/candidate_extractor.py — v12 M1

async def extract_candidate_context(person: dict, provider: 'LLMProvider') -> dict:
    """Career 수 기반 적응형 호출"""
    careers = person.get('careers', [])
    career_count = len(careers)

    if career_count <= 3:
        # 1-pass: 전체 이력서 한 번에 추출
        return await extract_1pass(person, provider)
    else:
        # N+1 pass: Career별 개별 + 전체 요약
        return await extract_n_plus_1(person, provider)

async def extract_1pass(person: dict, provider: 'LLMProvider') -> dict:
    """1-pass 호출 (Career 1~3): 전체 → chapters[] + role_evolution + domain_depth"""
    prompt = build_1pass_prompt(person)  # v12 §2.2.1 프롬프트
    result = await provider.extract(prompt, CandidateContextExtraction)
    return result

async def extract_n_plus_1(person: dict, provider: 'LLMProvider') -> dict:
    """N+1 pass 호출 (Career 4+): Career별 N회 + 요약 1회"""
    chapters = []
    for career in person['careers']:
        prompt = build_career_prompt(career)  # v12 §2.2.2 프롬프트
        chapter = await provider.extract(prompt, ChapterExtraction)
        chapters.append(chapter)

    # 전체 요약 (N+1번째 호출)
    summary_prompt = build_summary_prompt(person, chapters)  # v12 §2.2.3
    summary = await provider.extract(summary_prompt, CareerSummaryExtraction)

    return {
        'chapters': chapters,
        'role_evolution': summary.get('role_evolution'),
        'domain_depth': summary.get('domain_depth'),
    }
```

### v12 프롬프트 적용 사항

```
v12 S5 적용:
  - structural_tensions: 프롬프트에서 제외 (v1 INACTIVE)
  - work_style_signals: 프롬프트에서 제외 (v1 INACTIVE)
  → 토큰 ~300 절감 (Company ~200 + Candidate ~100)

v12 §2.4 scope_type 분류:
  - positionGradeCode 힌트 활용 (직접 결정 아닌 참고)
  - v19 A1 매핑: scope_type → Seniority 자동 변환

v12 §2.5 outcomes:
  - 4+1 유형 (METRIC, SCALE, DELIVERY, ORGANIZATIONAL, OTHER)
  - Evidence Span 필수, confidence 상한 0.85

v12 §2.6 situational_signals:
  - 14개 라벨, 5개 카테고리
  - 최대 3개/Chapter, confidence 상한 0.85
```

### LLM 파라미터 (v12 §3)

| 파라미터 | 1-pass | N+1: Career별 | N+1: 요약 |
|---------|--------|--------------|----------|
| model | claude-haiku-4-5 | claude-haiku-4-5 | claude-haiku-4-5 |
| temperature | 0.3 | 0.3 | 0.3 |
| max_tokens | 2,048 | 1,024 | 512 |
| batch_mode | true | true | true |

---

## 1-D. Graph + Embedding + API MVP (Week 5~6)

### Week 5 후반 ~ Week 6 전반 (1.5주)

| # | 작업 | 담당 | 기간 |
|---|------|------|------|
| G-1 | Person 노드 → Neo4j UNWIND 배치 | DE | 0.5일 |
| G-2 | Chapter + 관계 → UNWIND 배치 (v19 관계명) | DE | 0.5일 |
| G-3 | Skill + Role + Organization → UNWIND 배치 | MLE | 0.5일 |
| G-4 | Industry 노드 + IN_INDUSTRY 관계 | MLE | 0.5일 |
| G-5 | Embedding 생성 (Vertex AI, 768d, 1,000건) | MLE | 0.5일 |
| G-6 | Vector Index 적재 | DE | 0.5일 |
| G-7 | Idempotency + 롤백 테스트 | 공동 | 0.5일 |
| G-8 | Cypher 쿼리 5종 작성 (v19 관계명) | MLE | 0.5일 |
| G-9 | 에이전트 서빙 API + PII 필드 정의 (N2) | MLE | 1일 |
| G-10 | Cloud Scheduler health check 설정 (N1) | DE | 0.5일 |
| G-11 | E2E 검증 + 스팟체크 50건 | 공동 | 0.5일 |

### Graph 적재 코드 (v19 관계명)

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
                SET p.career_type = c.career_type,
                    p.education_level = c.education_level,
                    p.role_evolution = c.role_evolution,
                    p.domain_depth = c.domain_depth,
                    p.loaded_batch_id = $batch_id,
                    p.loaded_at = datetime()
            """, batch=batch, batch_id=batch_id)

            # Chapter + HAS_CHAPTER
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
                        "outcomes": ch.get("outcomes", []),
                        "signals": ch.get("situational_signals", []),
                    })

            session.run("""
                UNWIND $chapters AS ch
                MERGE (c:Chapter {chapter_id: ch.chapter_id})
                SET c.scope_type = ch.scope_type,
                    c.period_start = ch.period_start,
                    c.period_end = ch.period_end,
                    c.loaded_batch_id = $batch_id
                WITH c, ch
                MATCH (p:Person {person_id: ch.person_id})
                MERGE (p)-[:HAS_CHAPTER]->(c)
            """, chapters=chapters, batch_id=batch_id)

            # v19: PERFORMED_ROLE
            role_rels = [{"chapter_id": ch["chapter_id"], "role": ch["role"]}
                        for ch in chapters if ch.get("role")]
            if role_rels:
                session.run("""
                    UNWIND $rels AS r
                    MERGE (role:Role {title: r.role})
                    WITH role, r
                    MATCH (c:Chapter {chapter_id: r.chapter_id})
                    MERGE (c)-[:PERFORMED_ROLE]->(role)
                """, rels=role_rels)

            # v19: OCCURRED_AT
            company_rels = [{"chapter_id": ch["chapter_id"], "company": ch["company"]}
                           for ch in chapters if ch.get("company")]
            if company_rels:
                session.run("""
                    UNWIND $rels AS r
                    MERGE (o:Organization {name: r.company})
                    WITH o, r
                    MATCH (c:Chapter {chapter_id: r.chapter_id})
                    MERGE (c)-[:OCCURRED_AT]->(o)
                """, rels=company_rels)

            # Skill + USED_SKILL
            skill_rels = []
            for ch in chapters:
                for skill in ch.get("skills", []):
                    skill_rels.append({"chapter_id": ch["chapter_id"], "skill": skill})
            if skill_rels:
                session.run("""
                    UNWIND $rels AS r
                    MERGE (s:Skill {name: r.skill})
                    WITH s, r
                    MATCH (c:Chapter {chapter_id: r.chapter_id})
                    MERGE (c)-[:USED_SKILL]->(s)
                """, rels=skill_rels)
```

### AuraDB Free Auto-Pause 대응 (N1)

```bash
# N1: Cloud Scheduler로 12시간마다 health check
# Phase 1 API 배포 후 설정

gcloud scheduler jobs create http graphrag-api-keepalive \
  --schedule="0 */12 * * *" \
  --uri="https://graphrag-api-HASH-an.a.run.app/api/v1/health" \
  --http-method=GET \
  --oidc-service-account-email=kg-loading@graphrag-kg.iam.gserviceaccount.com \
  --time-zone="Asia/Seoul" \
  --description="Prevent AuraDB Free auto-pause by periodic health check"

# 비용: $0 (Cloud Scheduler 월 3개 무료)
```

### 에이전트 서빙 API + PII 필터링 (N2)

```python
# src/api/main.py — PII 필터링 미들웨어

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="GraphRAG API", version="1.2")

# N2: PII 필드 필터링 목록
PII_FIELDS = {"name", "email", "phone", "address", "birth_date"}

def filter_pii(data: dict) -> dict:
    """응답에서 PII 필드 제거"""
    if isinstance(data, dict):
        return {k: filter_pii(v) for k, v in data.items() if k not in PII_FIELDS}
    elif isinstance(data, list):
        return [filter_pii(item) for item in data]
    return data

@app.get("/api/v1/candidates/{candidate_id}")
async def get_candidate(candidate_id: str, request: Request):
    """후보자 상세 조회 — PII 자동 필터링"""
    raw = fetch_candidate_from_neo4j(candidate_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Candidate not found")

    filtered = filter_pii(raw)
    log_api_access(candidate_id, request.client.host, "candidates_detail")
    return filtered

@app.get("/api/v1/health")
async def health_check():
    """헬스체크 — N1: Cloud Scheduler 12h 호출 대상"""
    neo4j_status = check_neo4j_connection()
    return {
        "status": "ok" if neo4j_status else "degraded",
        "neo4j": "connected" if neo4j_status else "disconnected",
        "node_count": get_node_count() if neo4j_status else 0
    }
```

### 에이전트용 Cypher 쿼리 5종 (v19 관계명)

```cypher
-- Q1: 스킬 기반 검색
MATCH (p:Person)-[:HAS_CHAPTER]->(c:Chapter)-[:USED_SKILL]->(s:Skill)
WHERE s.name IN $skills
WITH p, COUNT(DISTINCT s) AS matched
WHERE matched >= $min_match
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
MATCH (p:Person)-[:HAS_CHAPTER]->(c:Chapter)
WHERE c.scope_type = $scope_type
RETURN p, c

-- Q5: 복합 조건 (PERFORMED_ROLE)
MATCH (p:Person)-[:HAS_CHAPTER]->(c:Chapter)
WHERE c.scope_type IN $seniority_levels
WITH p, c
MATCH (c)-[:USED_SKILL]->(s:Skill)
WHERE s.name IN $skills
WITH p, COUNT(DISTINCT s) AS skill_match
WHERE skill_match >= $min_skills
RETURN p ORDER BY skill_match DESC LIMIT $limit
```

---

## MVP 데모 (Week 6 중반)

```
Week 6 중반 체크포인트:
  □ DB 데이터 1,000건+ 처리 완료
  □ (선택) 크롤링 파이프라인 동작 (법무 허용 시)
  □ Neo4j Graph 동작 (v19 관계명: HAS_CHAPTER, PERFORMED_ROLE, USED_SKILL, OCCURRED_AT)
  □ Vector Index 동작 (chapter_embedding 768d)
  □ Cypher 쿼리 5종 동작 확인
  □ GraphRAG REST API 동작 (PII 필터링 적용, N2)
  □ Cloud Scheduler health check 12h 동작 확인 (N1)
  □ PII 매핑 GCS CMEK 저장 동작 확인 (v12 S2, ★ v4: Phase 1-B에서 생성)
  □ ★ v4: PII 마스킹 re.sub 콜백 방식 동작 확인 (R1)
  □ 적응형 LLM 호출 동작 확인 (v12 M1)
  □ 에이전트 연동: REST API 경유

→ 에이전트 팀에 API 문서 + PII 정책 + 연동 시작 안내
```

---

## Phase 1 완료 산출물 (Week 6 중반)

```
□ (선택) 크롤링 파이프라인 동작

□ 전처리 파이프라인 동작
  ★ v4 R1: PII 마스킹 re.sub 콜백 방식 (오프셋 버그 수정)
  ★ PII 마스킹: 전화번호 8종 정규식 (v12 S4)
  ★ v4 R3: PII 매핑 GCS CMEK 버킷 (Phase 1-B에서 생성)
  ★ 마스킹 검증: CP2 체크포인트 (v12 §2.3)

□ CandidateContext LLM 추출 동작
  ★ 적응형 호출: 1-pass (Career 1~3) / N+1 pass (Career 4+) (v12 M1)
  ★ v12 프롬프트: S5 INACTIVE 제외, scope_type/outcomes/signals 가이드라인
  ★ 3-Tier 재시도: json-repair → temperature 0.5 → dead-letter (v12 §7.1)

□ Neo4j Graph MVP
  ├─ UNWIND 배치 적재
  ├─ v19 관계명: PERFORMED_ROLE, OCCURRED_AT (v12 M2)
  ├─ 적재 버전 태그 (loaded_batch_id, loaded_at)
  ├─ Vector Index (chapter_embedding, 768d)
  └─ 50건 수동 검증

□ GraphRAG REST API
  ├─ /search/skills, /search/semantic, /search/compound
  ├─ /candidates/{id} PII 필터링 적용 (N2)
  ├─ /health Cloud Scheduler 12h 호출 대상 (N1)
  ├─ API Key 인증
  ├─ Rate limiting (100 req/min)
  └─ Cloud Run Service 배포

□ PII 필드 정의서 (N2)
□ Cloud Scheduler health check 설정 (N1)
□ Makefile 기반 오케스트레이션
□ BigQuery checkpoint (processing_log, batch_tracking)
□ 모니터링: BigQuery 쿼리 3종 + Slack 수동 알림
```
