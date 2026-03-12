# Phase 1: MVP 파이프라인 (9주)

> **목적**: 전처리 → Context 생성 → Graph 적재 → MappingFeatures까지 E2E 파이프라인 완성.
>
> **light.2 변경사항** (light.1 6.5~7주 → light.2 9주):
> - [light.2-4] 1-A: 2주 → **2.5주** (+0.5주 통합 테스트 버퍼)
> - [light.2-3] 1-B: 3주 → **3.5주** (+0.5주 프롬프트 튜닝 전용 시간)
> - [light.2-2] 1-C: 1주 → **2주** (+1주 Org ER 한국어 회사명 + 모듈 개발 시간)
> - [light.2-5] 1-D: 0.5~1주 → **1주 확정** (0.5주 옵션 제거)
> - [light.2-8] 1-D: Gold Test Set 라벨링 **선행 시작** (Week 11~12)
>
> **인력**: DE 1명 + MLE 1명 풀타임
> **산출물**: E2E 파이프라인 (JD 100건 + 이력서 1,000건 + Graph + MappingFeatures + MAPPED_TO)

---

## 1-A. 전처리 + CompanyContext 병행 (2.5주) — Week 3~5.5 [light.2-4]

### DE 담당: 전처리 모듈 (2주 구현 + 0.5주 통합)

| # | 작업 | GCP 서비스 | 산출물 | 기간 |
|---|---|---|---|---|
| 1-A-1 | PDF/DOCX/HWP 파서 모듈 [standard.1-2] | Cloud Run Job | `src/parsers/hwp.py` | 2일 |
| 1-A-2 | 섹션 분할기 (Rule-based) | 동일 | `src/splitters/` | 1일 |
| 1-A-3 | 경력 블록 분리기 | 동일 | | 1일 |
| 1-A-4 | PII 마스킹 모듈 | 동일 | `src/pii/` | 1일 |
| 1-A-5 | 이력서 중복 제거 모듈 (SimHash) | 동일 | `src/dedup/` | 1일 |
| 1-A-6 | JD 파서 + 섹션 분할 | 동일 | | 1일 |
| 1-A-7 | 기술 사전 (2,000개) + 회사 사전 구축 | GCS | `reference/` | 1일 |
| 1-A-8 | Docker 이미지 빌드 + Job 등록 | Cloud Build | | 0.5일 |
| **1-A-16** | **[light.2-4] JSON 스키마 합의 + 통합 테스트** | DE+MLE | 인터페이스 문서 | **2.5일** |

### MLE 담당: CompanyContext 파이프라인 (2주 구현 + 0.5주 통합)

| # | 작업 | GCP 서비스 | 산출물 | 기간 |
|---|---|---|---|---|
| 1-A-9 | CompanyContext Pydantic 모델 정의 | 코드 | `src/models/company.py` | 0.5일 |
| 1-A-10 | NICE Lookup 모듈 | Cloud Functions | `src/nice/` | 2일 |
| 1-A-11 | stage_estimate Rule 엔진 | 코드 | | 1일 |
| 1-A-12 | LLM 추출 프롬프트 (vacancy + role) | GCS | `vacancy_role_v1.txt` | 1일 |
| 1-A-13 | operating_model 키워드 + LLM 보정 | 코드 | | 1일 |
| 1-A-14 | Evidence 생성 + source_ceiling | 코드 | | 1일 |
| 1-A-15 | 통합 테스트 (JD 100건) | Cloud Run Job | E2E 결과 | 1일 |
| **1-A-16** | **[light.2-4] 인터페이스 합의 + 크로스 테스트** | DE+MLE | 통합 결과 | **2.5일** |

### [light.2-4] 통합 테스트 버퍼 (0.5주) 근거

light.1에서 DE(전처리)와 MLE(CompanyContext)의 **JSON 스키마 합의** 시간이 누락됨:
- 전처리 출력 JSON과 CompanyContext 입력 JSON의 인터페이스 합의
- 파싱 결과 → CompanyContext 모듈 간 연동 테스트
- 엣지케이스 발견 → 스키마 수정 → 재테스트 사이클

실제로 이 단계에서 의외로 시간이 소요되며, 0.5주 버퍼가 없으면 1-B 시작이 지연될 수 있다.

### Cloud Run Jobs 등록

light.1와 동일.

### 파싱 Job 핵심 로직

light.1와 동일. [standard.1-5] Checkpoint 내장 유지.

---

## 1-B. CandidateContext 파이프라인 (3.5주) — Week 5.5~9 [light.2-3]

> light.1의 3주 → light.2 3.5주. **프롬프트 튜닝 전용 0.5주** 추가.

### Week 5.5~7.5: 모듈 구현 (DE + MLE 공동, 2주)

light.1의 1-B-1 ~ 1-B-10과 동일.

| # | 작업 | 담당 | 산출물 |
|---|---|---|---|
| 1-B-1 | CandidateContext Pydantic 모델 정의 | MLE | `src/models/candidate.py` |
| 1-B-2 | Rule 추출 모듈 (날짜/회사/기술) | MLE | `src/extractors/rule.py` |
| 1-B-3 | LLM 추출 프롬프트 (Experience별) | MLE | `experience_extract_v1.txt` |
| 1-B-4 | LLM 추출 프롬프트 (전체 커리어) | MLE | `career_level_v1.txt` |
| 1-B-5 | WorkStyleSignals LLM 프롬프트 | MLE | |
| 1-B-6 | PastCompanyContext NICE 역산 모듈 | MLE | |
| 1-B-7 | LLM 파싱 실패 3-tier 구현 | MLE | `src/shared/llm_parser.py` |
| 1-B-8 | Batch API 요청 생성 모듈 (1,000건/chunk) | DE | |
| 1-B-9 | Batch API 제출/폴링 모듈 + checkpoint | DE | |
| 1-B-10 | Chunk 상태 추적 인프라 | DE | BigQuery `batch_tracking` |

### [light.2-3] Week 7.5~8: 프롬프트 튜닝 전용 (0.5주)

> **light.1에서 누락**: CandidateContext에 최소 4개 프롬프트가 있으나, 프롬프트 튜닝에 할당된 명시적 시간이 없음.

```
프롬프트 튜닝 대상 (4개):
  1. Experience 추출 프롬프트 (experience_extract_v1.txt)
  2. Career-level 추출 프롬프트 (career_level_v1.txt)
  3. WorkStyleSignals 프롬프트
  4. CompanyContext vacancy_role 프롬프트

각 프롬프트 × 3~5회 반복 = 15~20회 LLM 호출 라운드
각 라운드: 결과 검토(30분) + 프롬프트 수정(30분) + 재실행(10분) = ~70분

총 소요: 15~20 × 70분 = 17.5~23시간 ≈ 2.5~3일

→ 0.5주(2.5일) 할당으로 안정화 시간 확보
```

### Week 8~9: Batch API 테스트 + (대기 중) Graph/Org ER 선행

| # | 작업 | 담당 | 비고 |
|---|---|---|---|
| 1-B-11 | 통합 테스트 (이력서 200건) | MLE | 로컬 Python |
| 1-B-12 | Batch API 연동 테스트 (1,000건 제출) | DE | 24시간 SLA 대기 |
| 1-B-13 | **(대기 중)** Graph 적재 모듈 구현 | DE | 1-C-1~2 선행 |
| 1-B-14 | **(대기 중)** Deterministic ID + Org ER 설계 | MLE | 1-C 선행 |
| 1-B-15 | Batch API 응답 수집 + Context 생성 | DE | 대기 완료 후 |

### LLM 파싱 실패 3-tier 전략

light.1와 동일.

### Batch API 제출 Job

light.1와 동일. [standard.1-5] batch_tracking & checkpoint 내장 유지.

---

## 1-C. Graph + Embedding + Mapping (2주) — Week 9~11 [light.2-2]

> **light.1의 1주 → light.2의 2주. 핵심 사유: Org ER + 모듈 개발 시간.**
>
> light.1에서 "MVP 1,000건이므로 실행 시간 1주 충분"이라고 했으나,
> 실행 시간이 아니라 **모듈 개발 시간**이 지배적이다:
> - Org ER 알고리즘: 한국어 회사명 변형 패턴이 복잡 (1일 → 2~3일)
> - MappingFeatures 계산 모듈: 비즈니스 로직 구현
> - Idempotency 테스트 + E2E 통합 테스트

### Week 9~10: 모듈 구현 + Org ER (DE + MLE)

| # | 작업 | 담당 | 시간 |
|---|---|---|---|
| 1-C-1 | CompanyContext → Neo4j 로더 (MERGE) | DE | 0.5일 (1-B-13에서 선행) |
| 1-C-2 | CandidateContext → Neo4j 로더 (MERGE) | DE | 0.5일 (1-B-13에서 선행) |
| **1-C-3** | **Organization Entity Resolution** [light.2-2] | MLE | **2~3일** (light.1: 1일) |
| 1-C-4 | Industry 마스터 노드 적재 | DE | 0.5일 |
| 1-C-5 | Vacancy→REQUIRES_ROLE→Role 관계 | MLE | 0.5일 |
| 1-C-6 | Vector Index 적재 (Vertex AI Embedding) | DE | 0.5일 |
| 1-C-7 | MappingFeatures 계산 모듈 | MLE | 1일 |
| 1-C-8 | MAPPED_TO 관계 적재 | DE | 0.5일 |
| 1-C-9 | BigQuery mapping_features 적재 | DE | 0.5일 |
| 1-C-10 | Graph 적재 checkpoint 구현 [standard.1-5] | DE | 포함됨 |

### Week 10~11: 통합 테스트 + 검증

| # | 작업 | 담당 | 시간 |
|---|---|---|---|
| 1-C-11 | Idempotency 테스트 (동일 데이터 2회) | 공동 | 0.5일 |
| 1-C-12 | E2E 통합 테스트 + 50건 수동 검증 | 공동 | 1일 |
| 1-C-13 | Org ER 정밀도 검증 (Top-50 회사 수동 확인) | MLE | 0.5일 |

### [light.2-2] Organization Entity Resolution 확대 설계

```
ER 알고리즘 단계 (light.2 확대):

  0단계: 회사명 변형 패턴 Top-50 기반 alias 사전 초안 [Phase 0-B에서 추출]
         → company_alias.json 구축 (0.5일)

  1단계: 사전 매칭 — company_alias.json 기반
         "삼성전자(주)" → "삼성전자"
         "Samsung Electronics" → "삼성전자"
         정규화: 괄호 제거, (주)/(유) 제거, 공백 정규화

  2단계: 문자열 유사도 (한국어 특화)
         - 한국어: 자모 분리 후 편집거리 (Jaro-Winkler보다 적합)
         - 영어: Jaro-Winkler (threshold ≥ 0.85)
         - 혼합: 한국어 정규형으로 통일 후 비교

  3단계: (NICE 접근 가능 시) 사업자등록번호 기반 최종 확인

한국어 특화 주의사항:
  - "삼성" → 삼성전자? 삼성물산? 삼성SDS? → 문맥 기반 disambiguation 필요
  - "현대자동차" / "현대차" / "HMC" → 약칭 패턴 사전 필요
  - "SK하이닉스" (구 "하이닉스반도체") → 합병/분할 이력 사전 필요
  - 부문/부서: "삼성전자 DS부문" → 모회사 "삼성전자"로 MERGE할지 별도 유지할지 정책 결정

정확도 목표:
  - Precision ≥ 95% (잘못된 병합 방지 — 다른 회사를 합치는 것은 치명적)
  - Recall ≥ 80% (미병합 허용, Phase 2에서 수동 검수로 보완)
```

### [standard.1-5] Graph 적재 Checkpoint / [R-9] 네트워크 레이턴시

light.1와 동일.

---

## 1-D. 테스트 + 검증 + 백업 (1주 확정) — Week 11~12 [light.2-5]

> **light.2 변경**: 0.5주 옵션 제거, **1주 확정**. 테스트 코드 작성은 구현 코드만큼 시간이 소요됨.

| # | 작업 | 도구 | 산출물 | 기간 |
|---|---|---|---|---|
| 1-D-1 | pytest 기반 단위 테스트 프레임워크 | pytest + fixtures | `tests/` | 0.5일 |
| 1-D-2 | 파서 모듈 단위 테스트 (PDF/DOCX/HWP) | pytest | `tests/test_parsers.py` | 0.5일 |
| 1-D-3 | LLM 파싱 3-tier 단위 테스트 | pytest | `tests/test_llm_parser.py` | 0.5일 |
| 1-D-4 | Pydantic 모델 검증 테스트 | pytest | `tests/test_models.py` | 0.5일 |
| 1-D-5 | Golden 50건 regression test | pytest + deepdiff | `tests/test_regression.py` | 1일 |
| 1-D-6 | 통합 테스트 (파싱→Context→Graph E2E) | pytest | `tests/test_integration.py` | 0.5일 |
| 1-D-7 | Go/No-Go 게이트 판정 | 문서 | 판정 리포트 | 0.5일 |
| 1-D-8 | Neo4j 백업 (APOC export → GCS) [standard.20] | cypher-shell | 백업 파일 | 0.5일 |

### [light.2-8] Gold Test Set 라벨링 선행 시작 (Week 11~12, 1-D와 병행)

> **light.1에서 Phase 2-B에 집중 배치 → light.2에서 Phase 1 후반부터 선행 시작.**
> 전문가 A가 Phase 1 결과물(1,000건)로 라벨링을 시작하면,
> Phase 2-B에서는 "이미 구축된 Gold Set으로 평가만 실행"하여 0.5주 절약.

```
Week 11~12: 전문가 A가 100건 라벨링 시작 (20시간)
  ├─ Phase 1 MVP 결과물에서 무작위 100건 선별
  ├─ 라벨링 항목: scope_type, outcome, situational_signal, stage_estimate
  ├─ 1건당 15~20분 × 100건 = 25~33시간
  └─ Phase 1-D 테스트와 병행 (MLE는 테스트, 전문가 A는 라벨링)

Week 13~14 (Phase 2 초반): 전문가 A 라벨링 완료 + 전문가 B 라벨링 시작
  ├─ 전문가 A: 나머지 라벨링 완료
  ├─ 전문가 B: 추가 100건 라벨링 (20시간)
  └─ Week 15: Cohen's κ 검증 → Gold Set 200건 확정
```

### Regression Test 설계

light.1와 동일. [standard.1-6] 유지.

---

## 오케스트레이션 (Makefile) — [light.2-6] Phase 1 AND Phase 2

> **light.2 변경**: Phase 2에서도 Makefile 유지 (Cloud Workflows 후속 프로젝트로 이관).
> Phase 2용 대규모 타겟을 Makefile에 추가.

```makefile
# Makefile — Phase 1 + Phase 2 오케스트레이션 [light.2-6]
.PHONY: test parse dedup company-ctx candidate-ctx-prepare candidate-ctx-submit \
        candidate-ctx-collect graph-load embedding mapping full-pipeline status backup \
        phase2-batch phase2-graph phase2-full dead-letter-reprocess

# === Phase 1 타겟 (light.1와 동일) ===

test:
	pytest tests/ -v --tb=short

test-regression:
	pytest tests/test_regression.py -v

parse:
	gcloud run jobs execute kg-parse-resumes --region=asia-northeast3 --wait

dedup:
	gcloud run jobs execute kg-dedup-resumes --region=asia-northeast3 --wait

company-ctx:
	gcloud run jobs execute kg-company-ctx --region=asia-northeast3 --wait

candidate-ctx-prepare:
	gcloud run jobs execute kg-batch-prepare --region=asia-northeast3 --wait

candidate-ctx-submit:
	gcloud run jobs execute kg-batch-submit --region=asia-northeast3 --wait

candidate-ctx-collect:
	gcloud run jobs execute kg-batch-collect --region=asia-northeast3 --wait

graph-load:
	gcloud run jobs execute kg-graph-load --region=asia-northeast3 --wait

embedding:
	gcloud run jobs execute kg-embedding --region=asia-northeast3 --wait

mapping:
	gcloud run jobs execute kg-mapping --region=asia-northeast3 --wait

full-pipeline: parse dedup company-ctx candidate-ctx-prepare candidate-ctx-submit \
               candidate-ctx-collect graph-load embedding mapping
	@echo "Phase 1 full pipeline completed"

# === Phase 2 타겟 [light.2-6] ===

phase2-batch:
	@echo "=== Phase 2: Batch 처리 (450K) ==="
	gcloud run jobs update kg-parse-resumes --tasks=50 --region=asia-northeast3
	gcloud run jobs update kg-batch-prepare --tasks=50 --region=asia-northeast3
	gcloud run jobs update kg-batch-collect --tasks=50 --region=asia-northeast3
	gcloud run jobs execute kg-parse-resumes --region=asia-northeast3 --wait
	gcloud run jobs execute kg-dedup-resumes --region=asia-northeast3 --wait
	gcloud run jobs execute kg-batch-prepare --region=asia-northeast3 --wait
	gcloud run jobs execute kg-batch-submit --region=asia-northeast3 --wait

phase2-graph:
	@echo "=== Phase 2: Graph 적재 ==="
	gcloud run jobs update kg-graph-load --tasks=8 --task-timeout=43200 --region=asia-northeast3
	gcloud run jobs update kg-embedding --tasks=10 --task-timeout=21600 --region=asia-northeast3
	gcloud run jobs update kg-mapping --tasks=20 --task-timeout=10800 --region=asia-northeast3
	gcloud run jobs execute kg-batch-collect --region=asia-northeast3 --wait
	gcloud run jobs execute kg-graph-load --region=asia-northeast3 --wait
	gcloud run jobs execute kg-embedding --region=asia-northeast3 --wait
	gcloud run jobs execute kg-mapping --region=asia-northeast3 --wait

# [light.2-10] Dead-letter 재처리 전용 타겟
dead-letter-reprocess:
	@echo "=== Dead-letter 분류 + 재처리 ==="
	python src/dead_letter_classify.py
	python src/dead_letter_reprocess.py
	@echo "Dead-letter reprocessing completed"

phase2-full: phase2-batch phase2-graph dead-letter-reprocess
	@echo "Phase 2 full pipeline completed"

# === 공통 타겟 ===

status:
	@echo "=== Parsing Status ==="
	bq query --nouse_legacy_sql 'SELECT status, COUNT(*) as cnt FROM graphrag_kg.processing_log WHERE pipeline="parse" GROUP BY status'
	@echo ""
	@echo "=== Batch Tracking Status ==="
	bq query --nouse_legacy_sql 'SELECT status, COUNT(*) as cnt FROM graphrag_kg.batch_tracking GROUP BY status'
	@echo ""
	@echo "=== Graph Load Checkpoint ==="
	bq query --nouse_legacy_sql 'SELECT batch_idx, status FROM graphrag_kg.batch_checkpoint WHERE pipeline="graph_load" ORDER BY batch_idx DESC LIMIT 5'
	@echo ""
	@echo "=== Dead-letter Count ==="
	bq query --nouse_legacy_sql 'SELECT pipeline, COUNT(*) as cnt FROM graphrag_kg.parse_failure_log WHERE failure_tier="tier3" GROUP BY pipeline'

backup:
	@echo "Backing up Neo4j data..."
	cypher-shell -u neo4j -p $${NEO4J_PASSWORD} \
	  "CALL apoc.export.json.all('/tmp/backup.json', {useTypes: true})"
	gsutil cp /tmp/backup.json gs://graphrag-kg-data/backups/neo4j/$$(date +%Y%m%d)/
	@echo "Backup completed"
```

---

## Phase 1 완료 산출물 (Week ~12)

light.1와 동일 + 아래 추가:

```
# light.2 추가 산출물
□ Gold Test Set 라벨링 진행 중 (전문가 A, ~50~100건 완료) [light.2-8]
□ Batch API 응답 시간 실측 기반 Phase 2 타임라인 확정 [light.2-7]
□ 회사명 변형 패턴 company_alias.json (Top-50+) [light.2-2]
□ Embedding QPM 확인 결과 + quota 상태 [light.2-11]
```

### Phase 2 진행 Go/No-Go 게이트

light.1와 동일 기준 유지. "미달 판정 시 Phase 1 최대 2주 연장"도 유지.

---

## 전체 일정 요약

```
Week 3~5.5: Phase 1-A (전처리 + CompanyContext + 통합 테스트)
  ├─ DE: 파싱, 중복제거, 기술/회사 사전 (2주) + 통합 테스트 (0.5주)
  └─ MLE: CompanyContext 모듈 (2주) + 통합 테스트 (0.5주)

Week 5.5~9: Phase 1-B (CandidateContext)
  ├─ Week 5.5~7.5: 모듈 구현 (DE+MLE)
  ├─ Week 7.5~8: 프롬프트 튜닝 전용 [light.2-3]
  ├─ Week 8~9: Batch API 제출 + (대기) Graph/Org ER 선행 구현
  └─ Week 9: Batch API 응답 수집 + Context 생성

Week 9~11: Phase 1-C (Graph + Embedding + Mapping) [light.2-2: 2주]
  ├─ Org ER 2~3일 (한국어 회사명 특화)
  ├─ Graph 적재 + Embedding + MappingFeatures
  └─ Idempotency + E2E 통합 테스트

Week 11~12: Phase 1-D (테스트 + 검증 + 백업) [light.2-5: 1주 확정]
  ├─ pytest 프레임워크 + regression test
  ├─ Go/No-Go 게이트 판정
  ├─ Neo4j 백업 (APOC export → GCS)
  └─ [light.2-8] Gold Test Set 라벨링 선행 시작 (전문가 A 병행)

→ 총 9주 (Week 3~12)
```

### light.1 → light.2 Phase 1 비교

| 단계 | light.1 | light.2 | 차이 | 사유 |
|------|----|----|------|------|
| 1-A | 2주 | **2.5주** | +0.5주 | [light.2-4] 통합 테스트 버퍼 |
| 1-B | 3주 | **3.5주** | +0.5주 | [light.2-3] 프롬프트 튜닝 |
| 1-C | 1주 | **2주** | +1주 | [light.2-2] Org ER + 모듈 개발 |
| 1-D | 0.5~1주 | **1주** | +0~0.5주 | [light.2-5] 최소 1주 확정 |
| **합계** | **6.5~7주** | **9주** | **+2~2.5주** | |
