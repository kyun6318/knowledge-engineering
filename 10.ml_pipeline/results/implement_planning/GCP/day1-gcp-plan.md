# Day 1 — Gemini API 기본 추론 + Embeddings API (GCP 환경)

> **실행 환경**: Vertex AI Workbench / Compute Engine VM (asia-northeast3)
> **소요 시간**: 약 3~4시간
> **데이터 소스**: GCS (`gs://ml-api-test-vertex/datasets/`)

---

## 타임라인

| 시간 | 작업 | 스크립트 |
|------|------|----------|
| 0:00 | 환경 확인 & GCS 데이터 동기화 | `day1_setup.py` |
| 0:30 | TEST-C1: Gemini API 기본 추론 | `day1_test_c1.py` |
| 1:30 | TEST-C1-LLM-EVAL: LLM 품질 평가 | `day1_test_c1_llm_eval.py` |
| 2:30 | TEST-C2: Embeddings API | `day1_test_c2.py` |
| 3:30 | 결과 정리 & GCS 업로드 | 수동 |

---

## 0. GCP VM 환경 확인

```bash
# VM에 SSH 접속 (Workbench는 JupyterLab 터미널 사용)
gcloud compute ssh api-test-vm --zone=asia-northeast3-a
# 또는 Workbench JupyterLab → Terminal

cd ~/plan-graph-rag-main/ml-platform

# 환경변수 확인
export GCP_PROJECT="ml-api-test-vertex"
export GCP_LOCATION="asia-northeast3"
export GCS_BUCKET="gs://ml-api-test-vertex"

# GCS에서 데이터 동기화 (VM 로컬로)
gsutil -m rsync -r ${GCS_BUCKET}/datasets/ datasets/
gsutil -m rsync -r ${GCS_BUCKET}/prompts/ prompts/

# Python 환경 확인
python3 -c "import google.genai; print(google.genai.__version__)"

# ADC 인증 확인 (VM 서비스 계정 자동 사용)
python3 -c "
import google.auth
creds, project = google.auth.default()
print(f'Project: {project}')
print(f'Credentials type: {type(creds).__name__}')
"

# 환경 체크 스크립트 실행
python3 scripts/day1_setup.py
```

---

## 1. TEST-C1: Gemini API 기본 추론

### 1.1 테스트 항목

| 항목 | 모델 | 설명 |
|------|------|------|
| 비스트리밍 호출 | Flash KO+EN, Pro KO | 기본 호출 패턴 확인 |
| 스트리밍 + TTFT | Flash, Pro | 첫 토큰 응답 시간 측정 |
| 시스템 프롬프트 + JSON | Flash | 구조화 출력 검증 |

### 1.2 실행

```bash
python3 scripts/day1_test_c1.py
```

### 1.3 검증 기준

| 항목 | 2.5 Flash | 2.5 Pro | Pass 기준 |
|------|-----------|---------|-----------|
| 비스트리밍 호출 성공 | Y/N | Y/N | 정상 응답 |
| 스트리밍 TTFT (short_ko) | ___ms | ___ms | < 2s |
| 한국어 응답 품질 (0-8) | ___ | ___ | >= 6 |
| JSON 구조화 출력 | Y/N | Y/N | 유효 JSON |
| usage_metadata 반환 | Y/N | Y/N | 토큰 수 확인 |

---

## 2. TEST-C1-LLM-EVAL: Gemini 품질 평가 (LLM-as-Judge)

### 2.1 테스트 항목

llm_eval.jsonl (50~100건)의 각 항목을 Gemini로 생성하고, Gemini judge로 자동 채점.
- extraction: JSON 구조화 출력 + 정확성
- summarization: 스트리밍 TTFT + 품질
- classification: 분류 정확도
- generation: 생성 품질

### 2.2 실행

```bash
# 소량 테스트 (5건)
python3 scripts/day1_test_c1_llm_eval.py --limit 5

# 확인 후 전체 실행
python3 scripts/day1_test_c1_llm_eval.py

# 특정 언어만 (선택)
python3 scripts/day1_test_c1_llm_eval.py --lang ko
```

### 2.3 검증 기준 (Pass Criteria)

| 항목 | 기준 | Pass |
|------|------|------|
| KO 평균 점수 | >= 6.0 (8점 만점) | **필수** |
| extraction JSON valid | 100% | **필수** |
| summarization TTFT | < 2000ms | **필수** |
| overall pass rate | >= 75% | **필수** |

### 2.4 결과 파일

- `results/llm_eval_gemini.jsonl` — 항목별 상세 결과
- `results/test_results.json` — C1-LLM-EVAL 요약 메트릭
- `results/cost_log.jsonl` — API 호출 비용 로그

---

## 3. TEST-C2: Embeddings API

### 3.1 테스트 항목

| 항목 | 모델 | 설명 |
|------|------|------|
| 단건 임베딩 | gemini-embedding-001, text-embedding-005 | 기본 동작 확인 |
| tokens_per_char 캘리브레이션 | Flash (참고용) | 배치 최적화 기준 |
| 동적 배치 처리 | gemini-embedding-001 | 250건 배치, split-retry |
| task_type 지원 | gemini-embedding-001 | RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY |

### 3.2 실행

```bash
python3 scripts/day1_test_c2.py
```

### 3.3 검증 기준

| 항목 | gemini-embedding-001 | text-embedding-005 | Pass 기준 |
|------|---------------------|---------------------|-----------|
| 단건 호출 성공 | Y/N | Y/N | 벡터 반환 |
| 기본 차원 | ___ | ___ | 기록 |
| 배치 처리 성공 (250건) | Y/N | N/A | 에러 없음 |
| split-retry 동작 | Y/N | N/A | 분할 후 성공 |
| task_type 2종 | ___/2 | N/A | 기록 |
| 한국어 코사인 유사도 | Y/N | N/A | 유사 문서 > 0.7 |

---

## 4. 전체 실행 (자동)

```bash
# Day 1 전체 순차 실행
python3 scripts/day1_run_all.py
```

실행 순서:
1. `day1_setup.py` — 환경 확인
2. `day1_test_c1.py` — Gemini API 기본 추론
3. `day1_test_c1_llm_eval.py` — LLM 품질 평가
4. `day1_test_c2.py` — Embeddings API

---

## 5. Day 1 종료 — 결과 GCS 업로드

```bash
# 결과 파일 확인
ls -la results/
# 기대 파일:
#   cost_log.jsonl
#   test_results.json
#   test_run_summary.json
#   llm_eval_gemini.jsonl

# GCS에 결과 백업
gsutil -m cp -r results/ ${GCS_BUCKET}/results/day1/

# 비용 확인 (간이)
python3 -c "
import json
costs = {}
with open('results/cost_log.jsonl') as f:
    for line in f:
        e = json.loads(line)
        key = e['model_id']
        if key not in costs:
            costs[key] = {'calls': 0, 'input': 0, 'output': 0}
        costs[key]['calls'] += 1
        costs[key]['input'] += e['input_tokens']
        costs[key]['output'] += e['output_tokens']
for m, v in costs.items():
    print(f'{m}: {v[\"calls\"]} calls, input={v[\"input\"]:,}, output={v[\"output\"]:,}')
"
```

---

## 6. Day 1 결과 기록

### C1 결과 요약

| 항목 | Flash | Pro | 판단 |
|------|-------|-----|------|
| 비스트리밍 | ___ms | ___ms | |
| 스트리밍 TTFT | ___ms | ___ms | |
| 한국어 품질 | ___/8 | ___/8 | |
| JSON 출력 | Y/N | - | |

### C1-LLM-EVAL 결과 요약

| 항목 | 값 | Pass |
|------|-----|------|
| KO avg score | ___/8 | Y/N |
| extraction JSON valid | ___% | Y/N |
| summarization TTFT | ___ms | Y/N |
| overall pass rate | ___% | Y/N |

### C2 결과 요약

| 항목 | gemini-embedding-001 | text-embedding-005 |
|------|---------------------|---------------------|
| 차원 | ___ | ___ |
| 배치 성공 | Y/N | - |
| 유사도 정상 | Y/N | - |

### Day 1 비용

| 모델 | 호출 수 | 입력 토큰 | 출력 토큰 | 추정 비용 |
|------|---------|-----------|-----------|-----------|
| gemini-2.5-flash | ___ | ___ | ___ | $___ |
| gemini-2.5-pro | ___ | ___ | ___ | $___ |
| gemini-embedding-001 | ___ | ___ | ___ | $___ |

---

## 7. Day 1 이슈 & 결정사항

```
□ 이슈:
  -

□ 결정사항:
  -

□ Day 2 준비사항:
  - DS-PDF-SAMPLE PDF 파일 GCS 업로드 확인
  - DS-NER-EVAL gold 데이터 라벨링 완료 확인
  - Document AI 프로세서 name 기록 확인
```

---

> **다음 단계**: Day 1 완료 후 → [day2-gcp-plan.md](./day2-gcp-plan.md) 진행
