# Phase 1: MVP 파이프라인 (11~13주)

> **목적**: 전처리 → Context 생성 → Graph 적재 → MappingFeatures까지 E2E 파이프라인 완성.
>
> **standard.2 변경**:
> - [standard.1.1-1] 1-1 전처리 모듈 2주→**3주** 확장 (R-1)
> - [standard.1.1-2] **1-0 코드 리팩토링** 2~3일 신규 추가 (R-3)
> - [standard.1.1-3] Phase 1 완료 후 **1주 버퍼** 추가 (R-6)
> - [standard.1.1-12] Graph 적재 tasks 수를 **Neo4j connection pool 한도에 맞춰 조정** (R-4)
> - [standard.1.1-14] Organization ER에 **한국어 전처리 규칙** + **전수 검수** 추가 (R-12)
> - 기타: standard.1과 동일 (checkpoint, regression test, Makefile 오케스트레이션, Neo4j 백업)
>
> **인력**: DE 1명 + MLE 1명 풀타임
> **산출물**: E2E 파이프라인 (JD 100건 + 이력서 1,000건 + Graph + MappingFeatures + MAPPED_TO)

---

## 1-0. Phase 0 코드 리팩토링 + 의사결정 통합 (2~3일) — Week 5 [standard.1.1-2]

> **standard.2 신규**: Phase 0 PoC 코드(Jupyter 노트북/스크립트)를 프로덕션 코드로 전환하는 시간을 명시.

| # | 작업 | 담당 | 산출물 |
|---|---|---|---|
| 1-0-1 | Phase 0 PoC 코드 → `src/` 모듈 구조 리팩토링 | DE + MLE | `src/` 디렉토리 구조 |
| 1-0-2 | Phase 0-6 의사결정 결과 코드 반영 | MLE | 확정 모델/방법론 config |
| 1-0-3 | HWP 파싱 확정 방법 통합 | DE | `src/parsers/hwp.py` |
| 1-0-4 | LLM 모델/프롬프트 확정 버전 통합 | MLE | `prompts/` + config |

```
프로젝트 구조 (Phase 1 시작 시):
src/
  ├── parsers/         # PDF, DOCX, HWP 파서
  ├── splitters/       # 섹션 분할, 경력 블록 분리
  ├── pii/             # PII 마스킹
  ├── dedup/           # SimHash 중복 제거
  ├── extractors/      # Rule 추출, LLM 추출
  ├── models/          # Pydantic 모델 (Company, Candidate)
  ├── shared/          # 공통 유틸 (llm_parser, checkpoint)
  ├── nice/            # NICE Lookup
  └── graph/           # Neo4j 적재
tests/
  ├── test_parsers.py
  ├── test_llm_parser.py
  ├── test_models.py
  ├── test_regression.py
  └── test_integration.py
prompts/
  ├── experience_extract_v1.txt
  ├── career_level_v1.txt
  └── vacancy_role_v1.txt
```

---

## 1-1. 전처리 모듈 (3주) — Week 5-8 [standard.1.1-1]

> **standard.2 변경**: 2주→**3주**. 9개 태스크를 2명×15일=30인일로 소화. 태스크당 평균 3.3인일.
> PII 마스킹(offset mapping)과 SimHash 중복 제거에 각 3~4일 할당 가능.

| # | 작업 | 담당 | GCP 서비스 | 산출물 |
|---|---|---|---|---|
| 1-1-1 | PDF/DOCX 파서 모듈 | DE | Cloud Run Job 코드 | `src/parsers/` |
| 1-1-2 | **HWP 파서 모듈** (Phase 0-4-7 결정 반영) | DE | 동일 | `src/parsers/hwp.py` |
| 1-1-3 | 섹션 분할기 (Rule-based) | MLE | 동일 | `src/splitters/` |
| 1-1-4 | 경력 블록 분리기 | MLE | 동일 | |
| 1-1-5 | PII 마스킹 모듈 (offset mapping 보존) | MLE | 동일 | `src/pii/` |
| 1-1-6 | 이력서 중복 제거 모듈 (SimHash) | DE | 동일 | `src/dedup/` |
| 1-1-7 | JD 파서 + 섹션 분할 | DE | 동일 | |
| 1-1-8 | 기술 사전 (2,000개) + 회사 사전 구축 | 공동 | GCS | `reference/` |
| 1-1-9 | Docker 이미지 빌드 + Job 등록 | DE | Cloud Build + Cloud Run | |

### 3주 일정 배분

```
Week 5 (1-0 + 1-1 시작):
  Day 1-3: 1-0 코드 리팩토링 (공동)
  Day 4-5: 1-1-1 PDF/DOCX 파서 (DE) + 1-1-3 섹션 분할 (MLE)

Week 6:
  Day 1-3: 1-1-2 HWP 파서 (DE) + 1-1-4 경력 블록 분리 (MLE)
  Day 4-5: 1-1-7 JD 파서 (DE) + 1-1-5 PII 마스킹 시작 (MLE)

Week 7:
  Day 1-2: 1-1-6 SimHash (DE) + 1-1-5 PII 마스킹 완료 (MLE)
  Day 3-4: 1-1-8 기술/회사 사전 (공동)
  Day 5: 1-1-9 Docker + Job 등록 (DE)

Week 8 (여유 + 1-2 시작):
  Day 1-2: 통합 테스트 + 버그 수정
  Day 3-5: 1-2 CompanyContext 시작
```

### Cloud Run Jobs 등록

```bash
IMAGE=asia-northeast3-docker.pkg.dev/graphrag-kg/kg-pipeline/kg-pipeline:latest
SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com

# 파싱 Job
gcloud run jobs create kg-parse-resumes \
  --image=$IMAGE \
  --command="python,src/parse_resumes.py" \
  --tasks=50 --max-retries=2 \
  --cpu=2 --memory=4Gi \
  --task-timeout=3600 \
  --service-account=$SA \
  --region=asia-northeast3

# 중복 제거 Job
gcloud run jobs create kg-dedup-resumes \
  --image=$IMAGE \
  --command="python,src/dedup_resumes.py" \
  --tasks=1 \
  --cpu=4 --memory=8Gi \
  --task-timeout=7200 \
  --service-account=$SA \
  --region=asia-northeast3
```

### 파싱 Job 핵심 로직 — checkpoint 내장

```python
# kg-parse-resumes/main.py (standard.1과 동일, 생략)
# → standard.1/02_phase1_mvp_pipeline.md 참조
```

---

## 1-2. CompanyContext 파이프라인 (1~2주) — Week 8-10

> standard.1과 동일. 상세 내용은 `standard.1/02_phase1_mvp_pipeline.md` 1-2절 참조.

---

## 1-3. CandidateContext 파이프라인 (4주) — Week 10-14

> standard.1과 동일. 상세 내용은 `standard.1/02_phase1_mvp_pipeline.md` 1-3절 참조.

---

## 1-4. Graph 적재 파이프라인 (2주) — Week 14-16

| # | 작업 | GCP 서비스 | 산출물 |
|---|---|---|---|
| 1-4-1 | CompanyContext → Neo4j 로더 (MERGE) | Cloud Run Job | |
| 1-4-2 | CandidateContext → Neo4j 로더 (MERGE) | Cloud Run Job | |
| 1-4-3 | Deterministic ID 생성 모듈 | 코드 | |
| 1-4-4 | Organization Entity Resolution 모듈 [standard.1.1-14] | 코드 | |
| 1-4-4a | **Organization ER 결과 전수 검수** (500개) [standard.1.1-14] | 수동 | 0.5일 |
| 1-4-5 | Industry 마스터 노드 적재 + 검증 | Cloud Run Job | |
| 1-4-6 | Vacancy→REQUIRES_ROLE→Role 관계 | 코드 | |
| 1-4-7 | Vector Index 적재 (Vertex AI Embedding) | Cloud Run Job | |
| 1-4-8 | Idempotency 테스트 (동일 데이터 2회 적재) | Neo4j | 노드/엣지 수 불변 확인 |
| 1-4-9 | 적재 벤치마크 (1,000건 → 500K 추정) + **도쿄↔서울 RTT 영향 측정** | 측정 | |
| 1-4-10 | Graph 적재 checkpoint 구현 | 코드 + BigQuery | batch 단위 재시작 |

### [standard.1.1-14] Organization Entity Resolution — 한국어 전처리 규칙 보완

```
ER 알고리즘 단계:
  0단계 (신규): 한국어 회사명 정규화 전처리
    - "(주)", "주식회사", "(유)", "유한회사" 제거
    - "㈜" → 제거
    - 영문 "Co., Ltd.", "Inc.", "Corp." 제거
    - 부서/사업부 분리: "삼성전자 DS부문" → "삼성전자" + note="DS부문"
    - 공백/특수문자 정규화
    - 대소문자 통일 (영문)

  1단계: 사전 매칭 — company_alias.json 기반 (삼성전자(주) → 삼성전자)
  2단계: 문자열 유사도 — Jaro-Winkler (threshold ≥ 0.85)
    - [standard.1.1-14] 한국어 회사명에서 threshold 적합성은 Phase 0-3 프로파일링에서 검증
    - 대안: 레벤슈타인 편집거리 (한국어에 더 적합할 수 있음)
  3단계: (NICE 접근 가능 시) 사업자등록번호 기반 최종 확인

[standard.1.1-14] Phase 1-4-4a 전수 검수 (신규):
  - Phase 1 규모: ~500개 Organization 노드 (전수 검수 가능)
  - 검수 방법: ER 결과 → 병합된 조직 목록 + 미병합 유사 조직 후보 리스트 출력
  - DE/MLE 공동 검수 (0.5일)
  - 검수에서 발견된 패턴 → company_alias.json에 추가

정확도 목표:
  - Precision ≥ 95% (잘못된 병합 방지)
  - Recall ≥ 80% (미병합 허용, 수동 검수로 보완)
```

### [standard.1.1-12] Graph 적재 tasks 수 — Neo4j connection pool 연동

```bash
# Graph 적재 Job — tasks 수를 Phase 0-5-2b 확인 결과에 따라 설정
# AuraDB Free (max connections 확인 결과에 따라):
#   max ≤ 5:  tasks=3
#   max ≤ 10: tasks=5
#   Professional 전환 후: tasks=8 (Phase 2에서)

GRAPH_TASKS=3  # Phase 0-5-2b 결과 반영, 보수적 기본값

gcloud run jobs create kg-graph-load \
  --image=$IMAGE \
  --command="python,src/graph_load.py" \
  --tasks=$GRAPH_TASKS --max-retries=2 \
  --cpu=2 --memory=4Gi \
  --task-timeout=43200 \
  --service-account=$SA \
  --region=asia-northeast3

# Embedding Job — 동일 원칙 적용
EMBED_TASKS=4  # connection pool 한도 내

gcloud run jobs create kg-embedding \
  --image=$IMAGE \
  --command="python,src/generate_embeddings.py" \
  --tasks=$EMBED_TASKS \
  --cpu=2 --memory=4Gi \
  --task-timeout=21600 \
  --service-account=$SA \
  --region=asia-northeast3
```

### Connection Pool 관리 코드

```python
# src/shared/neo4j_pool.py — [standard.1.1-12]
import time
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

def create_driver_with_retry(uri, auth, max_retries=3):
    """Connection pool 부족 시 exponential backoff 재시도"""
    for attempt in range(max_retries):
        try:
            driver = GraphDatabase.driver(
                uri, auth=auth,
                max_connection_pool_size=2,  # task당 최소한의 pool
                connection_acquisition_timeout=30,
            )
            driver.verify_connectivity()
            return driver
        except ServiceUnavailable:
            wait = min(2 ** attempt, 30)
            print(f"Neo4j connection failed, retry in {wait}s (attempt {attempt+1}/{max_retries})")
            time.sleep(wait)
    raise ServiceUnavailable("Neo4j connection failed after max retries")
```

---

## 1-5. MappingFeatures + MAPPED_TO (2주) — Week 16-18

> standard.1과 동일. 상세 내용은 `standard.1/02_phase1_mvp_pipeline.md` 1-5절 참조.

---

## 1-6. 테스트 인프라 + Regression Test (1주, 1-5와 병행) — Week 17-18

> standard.1과 동일. 상세 내용은 `standard.1/02_phase1_mvp_pipeline.md` 1-6절 참조.

---

## Phase 1 완료 산출물

```
□ E2E 파이프라인 동작 (JD 100건 + 이력서 1,000건)
□ Neo4j Graph (Person, Chapter, Organization, Vacancy, Industry, Skill, Role 노드)
□ Vector Index (chapter_embedding, vacancy_embedding)
□ mapping_features BigQuery 테이블
□ MAPPED_TO 관계 Graph 반영
□ 50건 수동 검증 결과
□ Organization ER 전수 검수 완료 (500개) [standard.1.1-14]
□ Makefile 기반 파이프라인 실행 스크립트
□ pytest 테스트 스위트 (단위 + 통합 + regression)
□ Golden 50건 regression test 통과
□ Docker 이미지 (단일 kg-pipeline) + 11개 Cloud Run Jobs 등록
□ Neo4j 데이터 백업 (APOC export 또는 대안 방법 → GCS)
□ 인력 추가 여부 의사결정 [standard.1.1-4]
□ Phase 1 → Phase 2 Go/No-Go 판정 [standard.1.1-15]
```

---

## 버퍼 1주 — Week 19 [standard.1.1-3]

> **standard.2 신규**: Phase 1 완료 후 Phase 2 시작 전 1주 버퍼.
> 번아웃 방지 + Neo4j Professional 전환 준비 + Go/No-Go 의사결정 시간 확보.

```
버퍼 주간 활동:
  - Phase 1 → Phase 2 Go/No-Go 판정
  - Neo4j Professional 전환 사전 준비 (사양 결정, 예산 승인)
  - Phase 1 미완료 태스크 마무리 (있을 경우)
  - 기술 부채 해소 (코드 정리, 문서화)
  - 인력 추가 여부 최종 결정 [standard.1.1-4]
```
