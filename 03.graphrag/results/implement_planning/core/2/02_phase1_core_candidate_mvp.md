# Phase 1: Core Candidate MVP — DB 텍스트 + 에이전트 API (5주, Week 2~6)

> **목적**: DB 데이터를 CandidateContext로 변환 + Graph MVP + 에이전트 서빙 API 완성.
>
> **v1 대비 변경**:
> - 크롤링을 선택적으로 분리 — 법무 허용 시에만 진행, DB-only MVP 보장
> - 에이전트 서빙 API 설계 추가 (1일, M2)
> - Neo4j UNWIND 배치 적재로 변경 (M5)
> - Graph 적재 버전 태그 추가 (S7)
>
> **데이터 확장**: 없음 → **DB 텍스트 이력서 1,000건** (+ 크롤링 허용 시 추가)
> **에이전트 역량 변화**: 없음 → **REST API를 통한 후보자 검색**
>
> **인력**: DE 1명 + MLE 1명 풀타임
> **산출물**: 1,000건 E2E Graph + GraphRAG REST API + 에이전트 연동 가능 MVP

---

## 1-A. 크롤링 파이프라인 (Week 2~3, DE 담당) — 선택적

> ★ v2 변경: 크롤링은 **법무 허용 시에만** 진행. 미허용 시 DE는 1-B/1-C 지원.

### 법무 허용 시: v1과 동일

Week 2-3에서 Playwright 크롤러 구현 + Cloud Run Job + Cloud Scheduler 설정.

### 법무 미허용/미결 시: DE 대체 업무

```
Week 2: DB 데이터 마이그레이션 + BigQuery 최적화
  - 기존 DB → resume_raw 전체 마이그레이션 (1일)
  - BigQuery 파티셔닝/클러스터링 최적화 (0.5일)
  - Cloud Run Job 인프라 사전 구축 (전처리/추출/적재) (1.5일)
  - 서비스 계정별 접근 권한 테스트 (0.5일)
  - Phase 2 파일 파싱 PoC 선행 조사 (1.5일)

Week 3: Batch API 인프라 + 모니터링
  - Batch API prepare/submit/poll/collect 모듈 (2일)
  - BigQuery 모니터링 쿼리 3종 (처리 현황, 실패율, 비용) (0.5일)
  - Slack 알림 연동 (수동) (0.5일)
  - E2E 파이프라인 연동 테스트 (2일)
```

---

## 1-B. 전처리 모듈 (Week 2~3, MLE 담당)

> v1과 동일 (정규화, PII 마스킹, 경력 블록 분리, SimHash, Cloud Run Job).

---

## 1-C. CandidateContext LLM 추출 (Week 4~5)

> v1과 동일 (프롬프트 3종, LLM 파싱 실패 3-tier, 1,000건 Batch API 처리).

---

## 1-D. Graph + Embedding + API MVP (Week 5~6)

### Week 5 후반 ~ Week 6 전반 (1.5주)

| # | 작업 | 담당 | 기간 |
|---|------|------|------|
| G-1 | Person 노드 → Neo4j UNWIND 배치 | DE | 0.5일 |
| G-2 | Chapter + 관계 → UNWIND 배치 | DE | 0.5일 |
| G-3 | Skill + Role + Organization → UNWIND 배치 | MLE | 0.5일 |
| G-4 | Industry 노드 + IN_INDUSTRY 관계 | MLE | 0.5일 |
| G-5 | Embedding 생성 (Vertex AI, 768d, 1,000건) | MLE | 0.5일 |
| G-6 | Vector Index 적재 | DE | 0.5일 |
| G-7 | Idempotency + 롤백 테스트 | 공동 | 0.5일 |
| G-8 | Cypher 쿼리 5종 작성 | MLE | 0.5일 |
| G-9 | ★ **에이전트 서빙 API 설계 + 구현** | MLE | **1일** |
| G-10 | E2E 검증 + 스팟체크 50건 | 공동 | 0.5일 |

### Graph 적재 코드 (★ v2: UNWIND 배치)

```python
# src/graph/load_candidate.py — v2: UNWIND 배치 처리

def load_candidates_batch(driver, candidates: list[dict], batch_size: int = 100):
    """CandidateContext 배치 → Neo4j UNWIND 적재"""
    batch_id = f"load_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    for i in range(0, len(candidates), batch_size):
        batch = candidates[i:i + batch_size]
        with driver.session() as session:
            # Person 노드 배치
            session.run("""
                UNWIND $batch AS c
                MERGE (p:Person {candidate_id: c.candidate_id})
                SET p.total_years = c.total_years,
                    p.seniority_estimate = c.seniority_estimate,
                    p.primary_domain = c.primary_domain,
                    p.loaded_batch_id = $batch_id,
                    p.loaded_at = datetime()
            """, batch=batch, batch_id=batch_id)

            # Chapter + Skill + Role 배치 (Overview 참조)
            # ...
```

### 에이전트 서빙 API (★ v2 신규)

```python
# src/api/main.py — GraphRAG REST API (FastAPI)
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

app = FastAPI(title="GraphRAG API", version="1.0")

class SkillSearchRequest(BaseModel):
    skills: list[str]
    min_match: int = 1
    limit: int = 20

class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 20

class CompoundSearchRequest(BaseModel):
    skills: list[str] = []
    min_years: int | None = None
    seniority: list[str] = []
    limit: int = 20

@app.post("/api/v1/search/skills")
async def search_by_skills(req: SkillSearchRequest):
    """스킬 기반 후보자 검색"""
    # Cypher Q1 실행
    ...

@app.post("/api/v1/search/semantic")
async def search_semantic(req: SemanticSearchRequest):
    """시맨틱 유사 경력 검색 (Vector Search)"""
    # Cypher Q2 실행 (query → embedding → Vector Search)
    ...

@app.post("/api/v1/search/compound")
async def search_compound(req: CompoundSearchRequest):
    """복합 조건 검색"""
    # Cypher Q5 실행
    ...

@app.get("/api/v1/candidates/{candidate_id}")
async def get_candidate(candidate_id: str):
    """후보자 상세 조회"""
    ...

@app.get("/api/v1/health")
async def health_check():
    """헬스체크"""
    ...
```

```bash
# Cloud Run Service 배포 (API 서빙)
gcloud run deploy graphrag-api \
  --image=$API_IMAGE \
  --port=8080 \
  --cpu=1 --memory=512Mi \
  --min-instances=0 --max-instances=3 \
  --service-account=$SA_LOAD \
  --region=asia-northeast3 \
  --allow-unauthenticated=false
```

### 에이전트용 Cypher 쿼리 5종

> v1과 동일 (Q1~Q5). API 레이어에서 호출.

---

## MVP 데모 (Week 6 중반)

```
Week 6 중반 체크포인트:
  □ DB 데이터 1,000건+ 처리 완료
  □ (선택) 크롤링 파이프라인 동작 (법무 허용 시)
  □ Neo4j Graph 동작 (Person, Chapter, Skill, Role 노드)
  □ Vector Index 동작 (chapter_embedding 768d)
  □ Cypher 쿼리 5종 동작 확인
  □ ★ GraphRAG REST API 동작 (4개 엔드포인트)
  □ ★ 에이전트 연동: REST API 경유

→ 에이전트 팀에 API 문서 + 연동 시작 안내
```

---

## 오케스트레이션 (Makefile)

> v1과 동일. Phase 4에서 Cloud Workflows로 전환.

---

## Phase 1 완료 산출물 (Week 6 중반)

```
□ (선택) 크롤링 파이프라인 동작
  ├─ 법무 허용 시: 사이트 N곳 크롤러 + 일일 자동 크롤링
  └─ 법무 미허용/미결 시: DB-only MVP

□ 전처리 파이프라인 동작 (v1과 동일)

□ CandidateContext LLM 추출 동작 (v1과 동일)

□ Neo4j Graph MVP
  ├─ UNWIND 배치 적재 (v2)
  ├─ 적재 버전 태그 (loaded_batch_id, loaded_at)
  ├─ Vector Index (chapter_embedding, 768d)
  └─ 50건 수동 검증

□ ★ GraphRAG REST API (v2 신규)
  ├─ /search/skills, /search/semantic, /search/compound
  ├─ /candidates/{id}, /health
  ├─ API Key 인증
  ├─ Rate limiting (100 req/min)
  └─ Cloud Run Service 배포

□ Makefile 기반 오케스트레이션
□ BigQuery checkpoint (processing_log, batch_tracking)
□ ★ 모니터링: BigQuery 쿼리 3종 + Slack 수동 알림
```
