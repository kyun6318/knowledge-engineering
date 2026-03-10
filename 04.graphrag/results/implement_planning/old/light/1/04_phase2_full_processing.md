# Phase 2: 전체 데이터 처리 + 품질 평가 (4~5주)

> **목적**: 전체 데이터(450K 이력서 + 10K JD) 처리 + Graph 적재 + 품질 평가.
> Phase 1 MVP에서 검증된 파이프라인을 규모 확장하여 실행.
>
> **light.1 변경 (v2 대비)**:
> - [light.1-P2-1] 크롤링 파이프라인 전체 제거 → 후속 프로젝트
> - [light.1-P2-2] 서빙 인터페이스 최소화 (BigQuery 직접 쿼리만)
> - [light.1-P2-3] 운영 자동화(증분 처리, Dead-letter 재처리) 제거 → 후속 프로젝트
> - [light.1-P2-4] Gold Test Set 400건 → 200건으로 축소
> - [light.1-P2-5] Looker Studio 대시보드 제거 → BigQuery 쿼리로 대체
>
> **light.1 추가 변경 (standard.1 기반)**:
> - [standard.1-3] Neo4j Professional 전환을 필수 선행 작업으로 격상
> - [standard.1-7] 전체 데이터 처리 현실적 타임라인 반영 (450 chunks / 10 동시 × 6시간 = ~11일)
> - [standard.24] Cloud Workflows 도입 (Phase 1의 Makefile에서 전환)
> - [standard.1-5] Batch tracking 연동으로 진행률 추적
>
> **인력**: DE 1명 + MLE 1명 풀타임, 도메인 전문가 1명 파트타임
> **산출물**: 전체 KG + 품질 리포트(Gold Test Set 200건) + SQL/Cypher 쿼리 문서

---

## Pre-Phase 2: 사전 준비 (Phase 1 완료 ~ Phase 2 시작 사이)

### [standard.1-3] Neo4j Professional 전환 사전 준비

```bash
□ Professional 인스턴스 사양 결정
  - 예상 노드 수: ~2.77M (Phase 1 ~9K에서 Phase 2 ~2.77M로 확장)
  - 최소 사양: 4GB RAM / 16GB Storage
  - 리전: asia-northeast1 (도쿄)
□ 예산 승인: $65~200/월 (light.1: Phase 2 1개월만 사용)
□ Phase 1 Neo4j 백업 완료 확인 (APOC export → GCS)
```

---

## 병렬 트랙 구성 (Week 10~15)

```
Week 10      Week 11      Week 12      Week 13      Week 14      Week 15
──────────────────────────────────────────────────────────────────────────
[2-0] Neo4j Professional 전환 (1일 - Week 10 시작)
  │
  ▼
[DE]  ── 2-A: Batch 처리 (450K) ─────────────────────── 2-C: Graph적재 ──
[MLE] ── 2-B: 품질 평가 ──── 2-C: Embedding + Mapping ──── 2-D: 서빙──

Batch API 물리적 대기 시간 (3~4주):
  └─ 450 chunks / 10 동시 = 45 라운드 × 6시간(평균) = ~11일
  └─ + 실패 재시도 + 결과 수집 + Graph 적재 + 버퍼 = ~21~28일
  └─ MLE는 대기 중 품질 평가 + Embedding 모듈 스케일업 준비
```

---

## 2-0. Neo4j Professional 전환 (1일) — Week 10 시작 전 [standard.1-3]

> **필수** 선행 작업. "필요 시"가 아닌 **확정 일정**.
> Phase 1의 ~9K 노드에서 Phase 2의 ~2.77M 노드로 확장 시 Free 200K 한도 즉시 초과.

| # | 작업 | 도구 | 소요 시간 |
|---|---|---|---|
| 2-0-1 | AuraDB Professional 인스턴스 생성 | Neo4j Console | 5분 |
| 2-0-2 | Phase 1 백업 데이터 Import | cypher-shell | 30분 |
| 2-0-3 | Vector Index 재생성 | cypher-shell | 5분 |
| 2-0-4 | Constraint 재생성 | cypher-shell | 5분 |
| 2-0-5 | Secret Manager 연결 정보 업데이트 | gcloud CLI | 5분 |
| 2-0-6 | 연결 테스트 (Cloud Run Job → Neo4j) | Cloud Run | 10분 |
| 2-0-7 | Free 인스턴스 삭제 | Neo4j Console | 1분 |

```bash
# Secret Manager 업데이트
echo -n "neo4j+s://XXXXX.databases.neo4j.io" | \
  gcloud secrets versions add neo4j-uri --data-file=-

echo -n "new_password_here" | \
  gcloud secrets versions add neo4j-password --data-file=-

# 연결 테스트
gcloud run jobs execute kg-industry-load --region=asia-northeast3 --wait
```

### Neo4j Professional 비용

- AuraDB Professional: **$65~200/월** (노드 규모에 따라)
- light.1 Phase 2 기간 (1개월): $65~200

---

## 2-A. 전체 데이터 Batch 처리 (3~4주) — Week 10~13

> DE 담당 (MLE 품질 평가와 병행). [standard.1-7] 현실적 처리 시간 반영.
> **light.1 타임라인 근거**: Batch API 물리적 대기 ~11일 + 실패 재시도 ~2일 + 결과 수집/Context ~2일
> + Graph 적재/Embedding ~3일 + 버퍼 ~3일 = ~21~28일 ≈ 3~4주.

| # | 작업 | GCP 서비스 | 비고 |
|---|---|---|---|
| 2-A-1 | 이력서 500K 중복 제거 실행 | Cloud Run Job | canonical ~450K |
| 2-A-2 | 450 chunks × Batch API 처리 | Anthropic Batch API | 동시 5~10 batch |
| 2-A-3 | JD 10K × Batch API 처리 | Anthropic Batch API | ~10 chunks |
| 2-A-4 | Dead-letter 재처리 (1회) | Cloud Run Job | 자동화 불가 (light.1 범위 제외) |
| 2-A-5 | BigQuery chunk_status + batch_tracking 모니터링 | BigQuery | 일일 진행률 확인 [standard.1-5] |

### Chunk 처리 흐름 — [standard.1-7] 현실적 추정

```
이력서 ~450K (중복 제거 후)
    │
    ├─ 1,000건/chunk × ~450 chunks
    │
    ├─ 동시 처리: 5~10 chunks (Batch API quota 기반)
    │
    ├─ BigQuery chunk_status + batch_tracking으로 진행률 추적 [standard.1-5]
    │   └─ Batch 결과 보관 기간 (29일) 내 수집 보장
    │
    ├─ 실패 chunk: 자동 재시도 (최대 2회)
    │   └─ 2회 실패 → 건별 분해 → 개별 재시도
    │
    └─ 현실적 추정: [standard.1-7]
        ├─ 450 chunks / 10 동시 = 45 라운드 × 6시간(평균) = ~11일
        ├─ + 실패 재시도: ~2일
        ├─ + 결과 수집 + Context 생성: ~2일
        ├─ + Graph 적재 + Embedding: ~3일
        ├─ + 버퍼: ~3일
        └─ = 총 ~21~28일 ≈ 3~4주 (light.1: Phase 1 Graph 모듈 이미 구축, 버퍼 포함)
```

### 규모 확장 시 Cloud Run Jobs 설정 변경

```bash
# Phase 2용 Task count 확대
gcloud run jobs update kg-parse-resumes --tasks=50 --region=asia-northeast3
gcloud run jobs update kg-batch-prepare --tasks=50 --region=asia-northeast3
gcloud run jobs update kg-batch-collect --tasks=50 --region=asia-northeast3
```

### 비용 체크포인트

| 시점 | 확인 항목 | 임계값 |
|------|----------|-------|
| 50 chunks 완료 (~11%) | 실제 단가 vs 추정 비교 | ±30% 이내 |
| 200 chunks 완료 (~44%) | 누적 비용 확인 | < $300 |
| 전체 완료 | 최종 비용 집계 | < $700 (예산) |

---

## 2-B. 품질 평가 (1주, 2-A와 병행) — Week 10~11

> MLE 담당. Batch API 대기 시간을 활용하여 MVP 1,000건 결과로 품질 평가.

| # | 작업 | 도구 | 비고 |
|---|---|---|---|
| 2-B-1 | Gold Test Set 구축 (전문가 2인 × 100건) | 수동 + BigQuery | light.1: 200건 (standard.1: 400건) |
| 2-B-2 | Inter-annotator agreement (Cohen's κ) | Python | κ ≥ 0.7 |
| 2-B-3 | Power analysis (Cohen's d) | Python (scipy) | d ≥ 0.5 |
| 2-B-4 | 평가 지표 측정 + BigQuery 적재 | BigQuery | quality_metrics |
| 2-B-5 | 품질 리포트 작성 | 문서 | 최종 산출물 |

### 평가 기준

| 지표 | 최소 기준 | 목표 |
|------|----------|------|
| scope_type 분류 정확도 | > 70% | > 80% |
| outcome 추출 F1 | > 55% | > 70% |
| situational_signal 분류 F1 | > 50% | > 65% |
| vacancy scope_type 정확도 | > 65% | > 80% |
| stage_estimate 정확도 | > 75% | > 85% |
| 피처 1개+ ACTIVE 비율 | > 80% | > 90% |
| Human eval 상관관계 (r) | > 0.4 | > 0.6 |
| Cohen's d 효과 크기 | ≥ 0.5 | ≥ 0.8 |

### 품질 미달 시 대응

| 상황 | 대응 | 추가 시간 |
|------|------|----------|
| F1 지표 최소 기준 미달 (1~2개) | 프롬프트 튜닝 → 해당 1,000건 재추출 | +0.5주 |
| F1 지표 다수 미달 (3개+) | 접근법 재검토 (Phase 1 일부 재설계) | +1~2주 |
| 파싱 실패율 > 5% | 3-tier 로직 보강 | +0.5주 |
| 전체 기준 충족 | Phase 2-C 진행 | 없음 |

---

## 2-C. Graph 전체 적재 + Embedding + Mapping (1~2주) — Week 12~14

> DE + MLE 공동. 2-A Batch 처리가 충분히 진행된 후 시작.
> Batch가 완전히 끝나지 않아도 완료된 chunk부터 순차 적재 가능.

| # | 작업 | 담당 | GCP 서비스 |
|---|---|---|---|
| 2-C-1 | CompanyContext 전체 Graph 적재 | DE | Cloud Run Job (tasks=8) |
| 2-C-2 | CandidateContext 전체 Graph 적재 | DE | Cloud Run Job (tasks=8) |
| 2-C-3 | Embedding 전체 생성 | MLE | Cloud Run Job (tasks=10) |
| 2-C-4 | MappingFeatures 전체 계산 | MLE | Cloud Run Job (tasks=20) |
| 2-C-5 | MAPPED_TO 관계 전체 적재 | DE | Cloud Run Job |
| 2-C-6 | BigQuery mapping_features 전체 적재 | DE | BigQuery |

### Phase 2 Cloud Run Jobs 설정

```bash
# 전체 규모 Task count
gcloud run jobs update kg-graph-load \
  --tasks=8 --task-timeout=43200 \
  --region=asia-northeast3

gcloud run jobs update kg-embedding \
  --tasks=10 --task-timeout=21600 \
  --region=asia-northeast3

gcloud run jobs update kg-mapping \
  --tasks=20 --task-timeout=10800 \
  --region=asia-northeast3
```

### 적재 벤치마크 (Phase 1에서 측정한 추정치 기반)

| Job | Phase 1 (1K건) | Phase 2 추정 (450K건) | 비고 |
|-----|---------------|---------------------|------|
| Graph 적재 | ~30분 | ~8~12시간 (8 tasks) | 리니어 스케일 |
| Embedding | ~30분 | ~4~6시간 (10 tasks) | API rate limit |
| Mapping | ~20분 | ~2~3시간 (20 tasks) | CPU 바운드 |

---

## 2-D. Cloud Workflows 파이프라인 배포 [standard.24]

> Phase 2부터 Cloud Workflows 도입. Phase 1의 Makefile보다 안정적 오케스트레이션 필요.

### Cloud Workflows API 활성화

```bash
gcloud services enable workflows.googleapis.com

# Workflows IAM
gcloud projects add-iam-policy-binding graphrag-kg \
  --member="serviceAccount:$SA" \
  --role="roles/workflows.invoker"
```

### kg-full-pipeline.yaml

```yaml
main:
  params: [args]
  steps:
    - init:
        assign:
          - project_id: ${sys.get_env("GOOGLE_CLOUD_PROJECT_ID")}
          - region: "asia-northeast3"
          - run_id: ${text.replace_all(time.format(sys.now()), ":", "")}

    # Phase 1: 전처리 + 중복 제거
    - dedup_resumes:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-dedup-resumes"}
          location: ${region}

    # Phase 2: Batch 처리 + Context 생성
    - prepare_batches:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-batch-prepare"}
          location: ${region}
          body:
            overrides:
              containerOverrides:
                - env:
                    - name: RUN_ID
                      value: ${run_id}

    - submit_batches:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-batch-submit"}
          location: ${region}

    - collect_results:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-batch-collect"}
          location: ${region}

    # Phase 3: Graph 적재
    - load_company_graph:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-graph-load"}
          location: ${region}
          body:
            overrides:
              taskCount: 8

    - load_candidate_graph:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-candidate-graph"}
          location: ${region}
          body:
            overrides:
              taskCount: 8

    # Phase 4: Embedding + MappingFeatures
    - generate_embeddings:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-embedding"}
          location: ${region}
          body:
            overrides:
              taskCount: 10

    - compute_mapping:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-mapping"}
          location: ${region}
          body:
            overrides:
              taskCount: 20

    - load_mappings:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-load-mappings"}
          location: ${region}

    - load_to_bigquery:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + project_id + "/jobs/kg-bigquery-sync"}
          location: ${region}

    - notify:
        call: http.post
        args:
          url: ${args.slack_webhook_url}
          body:
            text: ${"Phase 2 파이프라인 완료: run_id=" + run_id}
```

---

## 2-E. 최소 서빙 인터페이스 (0.5주) — Week 14~15

> MLE 담당. light.1에서는 BigQuery 직접 쿼리만 제공.

| # | 작업 | 비고 |
|---|---|---|
| 2-E-1 | BigQuery mapping_features 스키마 문서화 | DS/MLE 전달용 |
| 2-E-2 | SQL 예시 쿼리 5종 작성 | 즉시 사용 가능한 쿼리 |
| 2-E-3 | Neo4j Cypher 예시 쿼리 5종 작성 | Graph 탐색용 |

### SQL 예시 쿼리

```sql
-- 1. JD별 Top-50 매칭 후보
SELECT
  vacancy_id,
  candidate_id,
  overall_match_score,
  stage_match_status,
  vacancy_fit_status,
  domain_fit_status
FROM graphrag_kg.mapping_features
WHERE vacancy_id = @vacancy_id
ORDER BY overall_match_score DESC
LIMIT 50;

-- 2. 피처 활성화 현황
SELECT
  COUNT(*) AS total_mappings,
  COUNTIF(stage_match_status = 'ACTIVE') AS stage_active,
  COUNTIF(vacancy_fit_status = 'ACTIVE') AS vacancy_active,
  COUNTIF(domain_fit_status = 'ACTIVE') AS domain_active,
  COUNTIF(culture_fit_status = 'ACTIVE') AS culture_active,
  COUNTIF(role_fit_status = 'ACTIVE') AS role_active,
  ROUND(COUNTIF(active_feature_count >= 1) / COUNT(*) * 100, 1) AS at_least_1_active_pct,
  ROUND(AVG(overall_match_score), 3) AS avg_overall_score
FROM graphrag_kg.mapping_features;

-- 3. 파이프라인 처리 현황
SELECT
  pipeline,
  COUNTIF(status = 'SUCCESS') AS success,
  COUNTIF(status = 'FAILED') AS failed,
  COUNTIF(status = 'PARTIAL') AS partial,
  ROUND(COUNTIF(status = 'FAILED') / COUNT(*) * 100, 2) AS error_rate
FROM graphrag_kg.processing_log
GROUP BY pipeline;

-- 4. LLM 파싱 실패 tier 분포
SELECT
  pipeline,
  failure_tier,
  COUNT(*) AS count,
  ROUND(AVG(partial_fields_extracted / NULLIF(total_fields, 0)) * 100, 1) AS avg_extraction_pct
FROM graphrag_kg.parse_failure_log
GROUP BY pipeline, failure_tier;

-- 5. Chunk 진행률
SELECT
  pipeline,
  COUNT(*) AS total_chunks,
  COUNTIF(status = 'COMPLETED') AS completed,
  COUNTIF(status = 'FAILED') AS failed,
  ROUND(COUNTIF(status = 'COMPLETED') / COUNT(*) * 100, 1) AS completion_pct
FROM graphrag_kg.chunk_status
GROUP BY pipeline;
```

### Cypher 예시 쿼리

```cypher
// 1. 특정 Vacancy에 매핑된 Person 목록
MATCH (v:Vacancy {vacancy_id: $vacancy_id})-[m:MAPPED_TO]-(p:Person)
RETURN p.candidate_id, m.overall_match_score, m.stage_match_status
ORDER BY m.overall_match_score DESC
LIMIT 20;

// 2. 특정 Person의 경력 그래프
MATCH (p:Person {candidate_id: $candidate_id})-[:HAS_CHAPTER]->(c:Chapter)
OPTIONAL MATCH (c)-[:WORKED_AT]->(o:Organization)
RETURN c.title, c.scope_type, o.name, c.start_date, c.end_date
ORDER BY c.start_date;

// 3. Organization별 재직자 수
MATCH (o:Organization)<-[:WORKED_AT]-(c:Chapter)
RETURN o.name, o.industry, COUNT(DISTINCT c) AS chapter_count
ORDER BY chapter_count DESC
LIMIT 20;

// 4. Vector similarity 검색
CALL db.index.vector.queryNodes('vacancy_embedding', 10, $query_embedding)
YIELD node, score
RETURN node.vacancy_id, node.title, score;

// 5. 그래프 통계
MATCH (n)
RETURN labels(n)[0] AS label, COUNT(*) AS count
ORDER BY count DESC;
```

---

## Phase 2 완료 산출물 (Week 13~15)

```
□ Neo4j Professional 전환 완료 [standard.1-3]
□ 전체 데이터 처리 완료 (450K 이력서 + 10K JD)
□ Neo4j Graph 전체 적재 (Person, Chapter, Organization, Vacancy, Industry, Skill, Role)
□ Vector Index 전체 적재 (chapter_embedding, vacancy_embedding)
□ BigQuery mapping_features 전체 적재
□ MAPPED_TO 관계 전체 반영
□ 품질 평가 리포트 (Gold Test Set 200건)
□ 처리 현황 리포트 (chunk_status + processing_log + batch_tracking) [standard.1-5]
□ 파싱 실패 리포트 (tier별 분포)
□ SQL + Cypher 예시 쿼리 문서
□ Cloud Workflows 파이프라인 배포 [standard.24]
□ 비용 정산 리포트 (실제 vs 추정)
```

### light.1 완료 시점의 상태

| 항목 | 상태 |
|------|------|
| 코어 KG | **완성** — 전체 데이터 적재 + 품질 검증 |
| 크롤링 보강 | **미완성** — 후속 프로젝트 |
| 증분 처리 | **미완성** — 후속 프로젝트 |
| 대시보드 | **미완성** — BigQuery 직접 쿼리로 대체 |
| 서빙 API | **미완성** — BigQuery + Cypher 직접 쿼리 |

---

## 후속 프로젝트 연결점

light.1 완료 후 바로 시작 가능한 작업과 선행 조건:

| 후속 작업 | light.1 선행 조건 | 바로 시작 가능? |
|----------|-------------|--------------|
| 크롤링 파이프라인 | CompanyContext 스키마 확정 | Yes (light.1 Phase 1에서 확정) |
| 증분 처리 자동화 | E2E 파이프라인 동작 확인 | Yes (light.1 Phase 1에서 확인) |
| Looker Studio | BigQuery 테이블 확정 | Yes (light.1에서 테이블 존재) |
| 지식증류 (Knowledge Distillation) | 품질 평가 결과 + 학습 데이터 | Yes (light.1 Phase 2에서 생성) |
| 서빙 API | mapping_features 스키마 확정 | Yes (light.1에서 스키마 존재) |
