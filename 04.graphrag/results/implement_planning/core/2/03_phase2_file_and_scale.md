# Phase 2: 파일 이력서 통합 + 전체 처리 (8주, Week 7-14)

> **목적**: Phase 1의 DB 텍스트 기반 Graph에 파일 이력서(PDF/DOCX/HWP)를 통합하고,
> 전체 450K 이력서를 처리하여 에이전트의 검색 범위를 전체 후보자 풀로 확대.
>
> **v1 대비 변경**:
> - 기간 6주→8주 (M1): 기본 시나리오에서 80%+ 완료 보장
> - 처리 완료 목표: 100%→80% (잔여 20%는 Phase 3 백그라운드)
> - 일별 시간표 제거 (S1): 주 단위 마일스톤으로 축소
> - Embedding 768d 통일 (M4)
> - 자동 품질 메트릭 + 통계적 샘플링 추가 (S4)
> - 쿼리 성능 벤치마크 추가 (C3)
> - Graph 적재: UNWIND 배치 + 버전 태그 (M5, S7)
> - Neo4j tasks 수 제한 (tasks ≤ 5, 연결 풀 고려)
> - 인력비 제거 (전체 비용 문서에서 별도 관리)
>
> **데이터 확장**: DB 텍스트 1,000건 → **전체 450K 중 80%+** (DB + 파일 소스 통합)
> **에이전트 역량 변화**: 1,000건 검색 → **360K+ 전체 후보자 검색**
>
> **인력**: DE 1명 + MLE 1명 풀타임

---

## 2-0. 코드 리팩토링 + 파일 파싱 PoC (1주) — Week 7

> v1과 동일 (PoC 코드 → 프로덕션 전환, HWP/PDF PoC).
> 크롤러 파일명 수정: linkedin_crawler/github_crawler → 실제 대상 사이트명으로.

### 프로젝트 구조 (Phase 2-3 전체 적용)

```
src/
├── parsers/              # PDF, DOCX, HWP 파서
├── splitters/            # 섹션 분할, 경력 블록 분리
├── pii/                  # PII 마스킹 (offset mapping 보존)
├── dedup/                # SimHash 중복 제거
├── extractors/           # Rule 추출, LLM 추출
├── models/               # Pydantic 모델
├── shared/               # 공유 유틸
├── crawlers/             # Phase 1 크롤러 (법무 허용 시)
│   ├── site_a_crawler.py ← ★ 실제 사이트명 (v1 오류 수정)
│   └── site_b_crawler.py
├── batch/                # Batch API
├── graph/                # Neo4j 적재 (UNWIND 배치)
├── api/                  # ★ v2: GraphRAG REST API
│   ├── main.py
│   └── routers/
├── quality/              # ★ v2 신규: 품질 메트릭
│   ├── auto_check.py     # 자동 품질 검사
│   ├── sampling.py       # 통계적 샘플링
│   └── __init__.py
└── requirements.txt
```

---

## 2-1. 파일 파싱 + 전처리 확장 (2주) — Week 8-9

### 주 단위 마일스톤 (★ v2: 일별 시간표 제거)

```
Week 8: 파서 구현 + 섹션 분할
  DE:  PDF/DOCX 파서 모듈 (2-1-1) + HWP 파서 모듈 (2-1-2)
  MLE: 섹션 분할기 Rule-based (2-1-3) + 경력 블록 분리기 (2-1-4)
  목표: 각 포맷 100건 테스트 통과

Week 9: 전처리 확장 + 인프라
  DE:  SimHash 대규모 중복 제거 (2-1-6) + Docker + Job 등록 (2-1-9)
  MLE: PII 마스킹 offset mapping (2-1-5) + 기술/회사 사전 확장 (2-1-8)
  목표: 전체 파이프라인 E2E 1,000건 테스트 통과
```

### Cloud Run Jobs 등록 — Neo4j 접근 Job tasks 제한 (★ v2)

```bash
# 파싱 Job (50개 병렬 task) — Neo4j 미접근이므로 병렬 OK
gcloud run jobs create kg-parse-resumes \
  --image=$IMAGE \
  --tasks=50 \
  --max-retries=2 \
  --cpu=2 --memory=4Gi \
  --service-account=$SA_PROC \
  --region=$REGION

# ★ Graph 적재 Job (tasks ≤ 5) — Neo4j 연결 풀 한도 고려
gcloud run jobs create kg-graph-load \
  --image=$IMAGE \
  --tasks=5 \
  --max-retries=2 \
  --cpu=2 --memory=4Gi \
  --service-account=$SA_LOAD \
  --region=$REGION
```

---

## 2-2. Neo4j Professional 전환 (1일) — Week 10 시작

> v1과 동일 절차. Vector Index 차원 수정:

```python
# ★ v2: Vector Index 768d + similarity_function
session.run("""
    CREATE VECTOR INDEX chapter_embedding IF NOT EXISTS
    FOR (c:Chapter)
    ON c.embedding
    OPTIONS {indexConfig: {
      `vector.dimensions`: 768,
      `vector.similarity_function`: 'cosine'
    }}
""")
```

---

## 2-3. 전체 450K Batch 처리 (5주) — Week 10-14

> v1(3주)→v2(5주): 기본 시나리오에서 80%+ 완료 보장.

### 업무 시간 외 대응 SLA

> 5주 전체 데이터 처리 중 야간/주말 모니터링 체계.

```
업무 시간 (09:00~18:00):
  - CRITICAL 알림: 즉시 대응 (30분 내)
  - WARNING 알림: 2시간 내 확인

업무 시간 외 (18:00~09:00, 주말):
  - CRITICAL 알림: Slack 전송만, 다음 업무일 아침 대응
  - 예외: Batch 결과 만료 24시간 이내 → kg-batch-poll 수동 실행 (원격)
  - WARNING 알림: 다음 업무일 아침 확인

자동화로 야간 대응 최소화:
  - kg-batch-poll: Cloud Scheduler 30분 주기 자동 실행
  - dead-letter 일일 자동 재시도
  - batch_tracking 일일 미수집 건 알림
```

### 처리 시간 계산 (v2 수정)

```
총 이력서 수: 450,000건
Batch API chunk 크기: 1,000건/chunk
필요한 chunk 수: 450개

동시 실행: 10 batch
라운드 수: 45 라운드

시나리오별 소요 (v2: 5주 = 35일 기준):

낙관 (6h/라운드): 11.25일 → 100% 완료, 여유 24일
기본 (12h/라운드): 22.5일 → 100% 완료, 여유 12일      ← ★ 3주는 부족했으나 5주는 충분
비관 (24h/라운드): 45일 → 78%, 여유 없음               ← ★ 80% 근접, 잔여 Phase 3 백그라운드

Graph 적재: UNWIND 배치로 v1 대비 10배 빠름
  - 1,000건 적재 벤치마크 후 450K 외삽
  - Neo4j Professional tasks ≤ 5 (연결 풀)

실패 재시도: 자동화 (kg-batch-poll 30분 주기)
결과 수집: 자동화 (완료 즉시)
```

### 3-시나리오 타임라인 (v2)

| 시나리오 | 라운드당 | 5주(35일) 완료량 | 에이전트 상태 |
|----------|---------|-------------|------------|
| **낙관** (6h) | 11.25일 | **100% (450K)** | 전체 KG 활용 |
| **기본** (12h) | 22.5일 | **100% (450K)** | ★ 5주면 충분 |
| **비관** (24h) | 45일 | **~80% (360K)** | 대부분 활용, 잔여 백그라운드 |

---

## 2-4. 자동 품질 메트릭 + 벤치마크 (★ v2 신규, 2-3과 병행)

### 자동 품질 체크 스크립트

```python
# src/quality/auto_check.py

def run_quality_checks(pipeline: str = "extraction"):
    """자동 품질 검사 — Phase 2 대규모 처리 중 실행"""

    checks = {
        "schema_compliance": check_schema_compliance(),
        "required_field_rate": check_required_fields(),
        "distribution_anomaly": check_distribution(),
        "prompt_version_comparison": compare_prompt_versions(),
    }

    for name, result in checks.items():
        log_quality_metric(pipeline, name, result)

    return checks

def check_schema_compliance() -> float:
    """JSON schema 준수율 (목표: 95%+)"""
    query = """
    SELECT
      COUNTIF(JSON_EXTRACT(context, '$.experiences') IS NOT NULL
              AND JSON_EXTRACT(context, '$.seniority_estimate') IS NOT NULL) / COUNT(*) as rate
    FROM graphrag_kg.candidate_contexts
    WHERE processed_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
    """
    # ...

def check_required_fields() -> dict:
    """필수 필드 완성도 (목표: 90%+)"""
    required = ["experiences", "seniority_estimate", "total_years", "primary_domain"]
    # 각 필드별 비어있지 않은 비율 계산
    # ...

def check_distribution() -> dict:
    """분포 이상 감지 — seniority/scope_type 분포가 기대치에서 벗어나면 경고"""
    # ...
```

### 통계적 샘플링 검증 (Phase 2 완료 시)

```python
# src/quality/sampling.py

def statistical_sampling_validation(total_population: int = 450000):
    """95% 신뢰구간, ±5% 오차 → 384건 무작위 샘플링"""
    import random
    import math

    # 필요 샘플 크기 계산
    z = 1.96  # 95% 신뢰수준
    p = 0.5   # 최대 분산 가정
    e = 0.05  # ±5% 허용 오차
    n = math.ceil((z**2 * p * (1-p)) / e**2)  # = 384

    # BigQuery에서 무작위 384건 추출
    sample_ids = get_random_sample(n)

    # 각 건별 수동 검증 + 자동 검증 병행
    results = {
        "sample_size": n,
        "schema_pass": 0,
        "field_complete": 0,
        "extraction_correct": 0,  # 수동 확인 필요
    }

    for sid in sample_ids:
        context = get_candidate_context(sid)
        results["schema_pass"] += validate_schema(context)
        results["field_complete"] += validate_fields(context)

    # 신뢰구간 계산
    for key in ["schema_pass", "field_complete"]:
        p_hat = results[key] / n
        ci = z * math.sqrt(p_hat * (1 - p_hat) / n)
        results[f"{key}_ci"] = f"{p_hat:.3f} ± {ci:.3f}"

    return results
```

### 쿼리 성능 벤치마크 (Phase 2 완료 시)

```python
# src/quality/benchmark.py

def benchmark_queries(driver, data_size: int):
    """Cypher 쿼리 5종 × 대규모 데이터 성능 벤치마크"""
    queries = {
        "Q1_skill_search": ("MATCH (p:Person)-[:HAS_CHAPTER]->...", {"skills": ["Python", "Django"]}),
        "Q2_vector_search": ("CALL db.index.vector.queryNodes...", {"top_k": 20}),
        "Q3_company_search": ("MATCH ... WHERE o.name CONTAINS ...", {"company_name": "삼성"}),
        "Q4_seniority_dist": ("MATCH (p:Person) WHERE ...", {"seniority": "SENIOR"}),
        "Q5_compound": ("MATCH ... WHERE s.name IN ...", {"skills": ["Python"], "min_years": 3}),
    }

    results = {}
    for name, (query, params) in queries.items():
        times = []
        for _ in range(10):  # 10회 반복
            start = time.time()
            with driver.session() as session:
                session.run(query, params).consume()
            times.append(time.time() - start)

        results[name] = {
            "p50": sorted(times)[5],
            "p95": sorted(times)[9],
            "data_size": data_size,
        }

    # p95 < 2초 기준
    for name, r in results.items():
        status = "PASS" if r["p95"] < 2.0 else "FAIL — 인덱스 추가 필요"
        print(f"  {name}: p95={r['p95']:.3f}s — {status}")

    return results
```

---

## 버퍼 1주 — Week 15

> v1과 동일 구조. Go/No-Go 기준만 업데이트.

### Phase 2 → Phase 3 Go/No-Go 판정

```
평가 기준 (v2 업데이트):

1. 완료도 평가
   ├─ 처리량: 목표 80%+ (v1은 미명시)
   ├─ 파싱 성공률: 목표 95%+
   └─ CER (HWP): ≤ 0.15

2. ★ 자동 품질 평가 (v2 신규)
   ├─ schema 준수율: 95%+
   ├─ 필수 필드 완성도: 90%+
   ├─ 통계적 샘플링 384건 결과
   └─ 분포 이상 없음

3. ★ 쿼리 성능 벤치마크 (v2 신규)
   ├─ Cypher 5종 × 360K+ 데이터
   ├─ p95 < 2초
   └─ 미달 시: 복합 인덱스 추가

4. Neo4j 백업
   ├─ ★ 스냅샷 백업 완료 (적재 전 필수)
   └─ 노드/엣지 수 기록

5. 인력 평가
   └─ Phase 3 인력 추가 필요 여부
```

---

## Phase 2 완료 산출물

```
□ 파일 파싱 모듈 (v1과 동일)

□ 전처리 확장 모듈 (v1과 동일)

□ 인프라 전환
  ├─ Neo4j Professional (Vector Index 768d)
  ├─ ★ Graph 적재 Job tasks ≤ 5 (연결 풀 고려)
  └─ ★ UNWIND 배치 적재 + 버전 태그

□ 전체 데이터 처리 (450K 이력서)
  ├─ ★ 목표: 80%+ (360K+) — v1은 미명시
  ├─ 잔여 20%: Phase 3 백그라운드 자동화
  └─ Graph 적재: UNWIND 배치, 10배 성능 향상

□ ★ 자동 품질 메트릭 (v2 신규)
  ├─ schema 준수율, 필수 필드 완성도
  ├─ 통계적 샘플링 384건 (95% 신뢰구간)
  ├─ BigQuery quality_metrics 테이블
  └─ 분포 이상 감지

□ ★ 쿼리 성능 벤치마크 (v2 신규)
  ├─ Cypher 5종 × 360K+ 데이터
  ├─ p95 기준, 미달 시 인덱스 추가
  └─ Vector Search 768d × 1.8M+ 노드

□ Regression 테스트 (Golden 50건)

□ Go/No-Go 판정
```

---

## 예상 비용 (Phase 2, 8주)

> ★ v2: 인력비 제거 (전체 비용 문서에서 별도 관리)

| 항목 | 비용 | v1 대비 |
|------|------|---------|
| Anthropic Batch API (450K) | ~$1,350 | 동일 |
| Anthropic API (재처리/에러) | ~$72 | 동일 |
| Vertex AI Embedding | ~$50 | 동일 |
| Neo4j Professional (8주) | $200~480 | +$40~130 (기간 연장) |
| Cloud Run Jobs | ~$70 | +$18 (기간 연장) |
| GCS + BigQuery | ~$25 | +$7 (기간 연장) |
| 기타 (모니터링, 로깅) | ~$16 | +$4 |
| **Phase 2 합계** | **$1,783~2,043** | +$80~260 |
