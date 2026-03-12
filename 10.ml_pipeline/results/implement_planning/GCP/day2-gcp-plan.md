# Day 2 — 데이터 수집/정제 + NER 파이프라인 (GCP 환경)

> **실행 환경**: Vertex AI Workbench / Compute Engine VM (asia-northeast3)
> **소요 시간**: 약 5~6시간 (백그라운드 인덱싱 제외)
> **데이터 소스**: GCS (`gs://ml-api-test-vertex/datasets/`)
> **핵심 목표**: Day 3 검색 테스트를 위해 **C5 Corpus + VAS Data Store 인덱싱을 오전에 트리거**하고, 나머지 시간에 DOC/MMD/NER/E2E 테스트 진행.

---

## 타임라인

| 시간 | 작업 | 우선순위 | 비고 |
|------|------|----------|------|
| 0:00 | VM 환경 확인 & Day 1 결과 확인 | - | |
| 0:15 | **C5 Corpus + VAS Data Store 생성** | **최우선** | 인덱싱 백그라운드 시작 |
| 0:45 | TEST-DOC: Document AI PDF 추출 | 높음 | OCR + Layout Parser |
| 2:00 | TEST-MMD: Gemini 멀티모달 추출 | 높음 | DOC vs MMD 비교 |
| 3:00 | TEST-NER: 엔티티/관계 추출 | 높음 | Zero-shot + Few-shot |
| 4:00 | TEST-E2E: 파이프라인 비교 (A vs B) | 중간 | 5건 PDF |
| 5:00 | 결과 정리 & GCS 업로드 | - | pending_ops.json 저장 확인 |

---

## 0. VM 환경 확인

```bash
# VM 접속
gcloud compute ssh api-test-vm --zone=asia-northeast3-a

cd ~/plan-graph-rag-main/ml-platform

# 환경변수
export GCP_PROJECT="ml-api-test-vertex"
export GCP_LOCATION="asia-northeast3"
export GCS_BUCKET="gs://ml-api-test-vertex"

# Day 1 결과 확인
cat results/test_results.json | python3 -m json.tool | head -30

# GCS 데이터 최신 동기화
gsutil -m rsync -r ${GCS_BUCKET}/datasets/ datasets/
```

---

## 1. C5 Corpus + VAS Data Store 생성 (최우선 - 오전 첫 작업)

> **Day 3 검색 테스트를 위해 인덱싱을 미리 시작해야 함.**
> C5 import + VAS 문서 인덱싱은 수십 분~수 시간 소요.

### 1.1 실행

```bash
python3 scripts/day2_c5_vas_setup.py
```

### 1.2 주요 동작

1. **C5 RAG Corpus 생성** — `gemini-embedding-001` 모델, BASIC tier
2. **C5 문서 Import 트리거** — `gs://ml-api-test-vertex/datasets/DS-RAG-DOCS/` → Corpus
3. **VAS Data Store 생성** — GCS 기반 비정형 문서 Store
4. **VAS 문서 Import 트리거** — 동일 GCS 경로에서 인덱싱
5. **VAS Search Engine 생성** — Enterprise tier + LLM 요약
6. **`results/pending_ops.json` 저장** — corpus name, store name, engine ID, RUN_ID

### 1.3 GCS 경로 확인

```bash
# RAG 문서가 GCS에 올바르게 업로드되었는지 확인
gsutil ls ${GCS_BUCKET}/datasets/DS-RAG-DOCS/ | head -10
gsutil ls ${GCS_BUCKET}/datasets/DS-RAG-DOCS/ | wc -l
```

### 1.4 검증

```
□ C5 Corpus 생성 성공 — corpus name 기록
□ C5 Import Operation 시작 — operation name 기록
□ VAS Data Store 생성 성공 — store name 기록
□ VAS Import Operation 시작
□ VAS Search Engine 생성 시작
□ pending_ops.json 저장 확인
```

### 1.5 백그라운드 상태 확인 (선택)

```bash
# 진행 중 다른 테스트 하면서 가끔 확인
python3 -c "
import json
with open('results/pending_ops.json') as f:
    ops = json.load(f)
print(json.dumps(ops, indent=2))
"
```

---

## 2. TEST-DOC: Document AI — PDF 텍스트 추출

### 2.1 사전 확인

```bash
# Document AI 프로세서 name 설정 (Day 0에서 Console 생성한 것)
export OCR_PROCESSOR_NAME="projects/ml-api-test-vertex/locations/us/processors/YOUR_OCR_ID"
export LAYOUT_PROCESSOR_NAME="projects/ml-api-test-vertex/locations/us/processors/YOUR_LAYOUT_ID"

# PDF 샘플 확인
ls datasets/DS-PDF-SAMPLE/*.pdf | wc -l
# 기대: 20~30개
```

### 2.2 실행

```bash
python3 scripts/day2_test_doc.py
```

### 2.3 테스트 항목

| 항목 | 설명 |
|------|------|
| 단건 동기 처리 | OCR + Layout Parser, 전체 PDF 대상 |
| 텍스트 추출 품질 | Gold 텍스트 대비 CER/WER (3~5건) |
| 배치 비동기 처리 | GCS → GCS, LRO polling |

### 2.4 검증 기준

| 항목 | OCR Processor | Layout Parser | Pass 기준 |
|------|---------------|---------------|-----------|
| PDF 추출 성공 | ___/20 | ___/20 | >= 95% |
| 한국어 CER | ___ | ___ | <= 0.10 |
| 표 구조 인식 | N/A | ___건 | 인식 |
| 2단 레이아웃 | Y/N | Y/N | 순서 보존 |
| 단건 latency | ___ms | ___ms | < 5s/page |
| 배치 LRO | Y/N | Y/N | 완료 |

### 2.5 배치 처리 GCS 경로

```
입력: gs://ml-api-test-vertex/datasets/DS-PDF-SAMPLE/
출력: gs://ml-api-test-vertex/docai-output/
```

---

## 3. TEST-MMD: Gemini 멀티모달 — PDF 직접 텍스트 추출

### 3.1 실행

```bash
python3 scripts/day2_test_mmd.py
```

### 3.2 테스트 항목

| 항목 | 설명 |
|------|------|
| PDF 직접 텍스트 추출 | 전체 PDF (10MB 미만, 5p 이하 필터) |
| 구조화 추출 (JSON) | 5건 샘플, response_schema 적용 |
| Gold 대비 CER/WER | 텍스트 추출 품질 평가 |

### 3.3 검증 기준

| 항목 | 텍스트 추출 | 구조화 추출 | Pass 기준 |
|------|------------|------------|-----------|
| 성공률 | ___/20 | ___/5 | >= 95% |
| 한국어 CER | ___ | N/A | <= 0.15 |
| 구조화 JSON | N/A | ___% | >= 90% |
| 단건 latency | ___ms | ___ms | < 10s/page |

### 3.4 DOC vs MMD 비교 매트릭스 (Day 2 핵심 산출물)

| 비교 항목 | Document AI (OCR) | Document AI (Layout) | Gemini 멀티모달 |
|-----------|-------------------|---------------------|----------------|
| CER | ___ | ___ | ___ |
| WER | ___ | ___ | ___ |
| 표 인식 | ___ | ___ | ___ |
| 구조화 출력 | X | 레이아웃만 | JSON 직접 |
| 한국어 OCR | ___ | ___ | ___ |
| latency | ___ms | ___ms | ___ms |
| 비용/page | $0.0015 | $0.01 | $___ |
| 후속 NER 연결 | 별도 NER | 별도 NER | 동시 처리 가능 |

---

## 4. TEST-NER: Gemini 기반 엔티티/관계 추출

### 4.1 사전 확인

```bash
# NER 평가셋 확인 (gold 라벨링 완료 필수)
wc -l datasets/DS-NER-EVAL/*.jsonl
```

### 4.2 실행

```bash
python3 scripts/day2_test_ner.py
```

### 4.3 테스트 항목

| 항목 | 모델 | 설명 |
|------|------|------|
| Zero-shot 엔티티 추출 | Flash, Pro | JSON 구조화, F1 측정 |
| Few-shot 엔티티 추출 | Flash | 예시 3~5건 포함, F1 비교 |
| 관계 추출 | Flash, Pro | subject-predicate-object |
| Entity-Relation 정합성 | Flash, Pro | relation의 subject/object가 entity에 존재하는지 |

### 4.4 검증 기준

| 항목 | Flash | Pro | Pass 기준 |
|------|-------|-----|-----------|
| JSON 출력 성공률 | ___% | ___% | >= 95% |
| Zero-shot 엔티티 F1 (KO) | ___ | ___ | >= 0.70 |
| Few-shot 엔티티 F1 (KO) | ___ | N/A | > Zero-shot |
| 관계 추출 F1 (KO) | ___ | ___ | >= 0.60 |
| Entity-Relation 정합성 | ___% | ___% | >= 90% |
| 단건 latency | ___ms | ___ms | < 3s |

---

## 5. TEST-E2E: 정제 → NER 파이프라인 비교

### 5.1 실행

```bash
python3 scripts/day2_test_e2e.py
```

### 5.2 파이프라인 비교

```
방법 A: PDF → Document AI OCR → 텍스트 → Gemini NER → 트리플 (2단계)
방법 B: PDF → Gemini 멀티모달 NER → 트리플 (1단계)
```

5건 PDF로 양쪽 실행, 품질/비용/속도 비교.

### 5.3 검증 기준

| 비교 항목 | 방법 A (DocAI → NER) | 방법 B (멀티모달 NER) |
|-----------|---------------------|---------------------|
| E2E latency | ___ms | ___ms |
| 엔티티 수 | ___ | ___ |
| 관계 수 | ___ | ___ |
| 정합성 | ___% | ___% |
| 비용/문서 | $___ | $___ |
| 구현 복잡도 | 2단계 (SDK 2개) | 1단계 |
| 대량 처리 | 배치 API 지원 | 순차 호출 |

---

## 6. Day 2 종료 — 결과 정리 & GCS 업로드

```bash
# pending_ops.json 확인 (Day 3에서 필수)
cat results/pending_ops.json

# 결과 파일 확인
ls -la results/

# GCS에 결과 백업
gsutil -m cp -r results/ ${GCS_BUCKET}/results/day2/

# 백그라운드 작업 상태 확인
python3 -c "
import google.genai as genai
import json

with open('results/pending_ops.json') as f:
    ops = json.load(f)

client = genai.Client(vertexai=True, project='ml-api-test-vertex', location='asia-northeast3')

# C5 import 상태
try:
    files = list(client.corpora.list_files(name=ops['c5_corpus_name']))
    print(f'C5 Import: {len(files)} files indexed')
except Exception as e:
    print(f'C5 Import: checking... ({e})')

print(f'RUN_ID: {ops[\"run_id\"]}')
print(f'VAS Engine: {ops[\"vas_engine_id\"]}')
"
```

---

## 7. Day 2 결과 기록

### DOC 결과

| 항목 | OCR | Layout | 판단 |
|------|-----|--------|------|
| 성공률 | ___/20 | ___/20 | |
| CER (KO) | ___ | ___ | |
| 표 인식 | - | ___건 | |

### MMD 결과

| 항목 | 텍스트 | 구조화 | 판단 |
|------|--------|--------|------|
| 성공률 | ___/20 | ___/5 | |
| CER (KO) | ___ | - | |

### NER 결과

| 항목 | Flash | Pro | 판단 |
|------|-------|-----|------|
| 엔티티 F1 (zero) | ___ | ___ | |
| 엔티티 F1 (few) | ___ | - | |
| 관계 F1 | ___ | ___ | |
| 정합성 | ___% | ___% | |

### E2E 비교

| 항목 | 방법 A | 방법 B | 선택 |
|------|--------|--------|------|
| latency | ___ms | ___ms | |
| 품질 | ___ | ___ | |
| 비용 | $___ | $___ | |

### Day 2 비용

| 모델 | 호출 수 | 입력 토큰 | 출력 토큰 | 추정 비용 |
|------|---------|-----------|-----------|-----------|
| gemini-2.5-flash | ___ | ___ | ___ | $___ |
| docai-ocr | ___ | - | - | $___ |
| docai-layout | ___ | - | - | $___ |

### 백그라운드 작업 상태

```
□ C5 Corpus Import: 완료/진행 중 (___건 파일)
□ VAS 문서 Import: 완료/진행 중
□ VAS Search Engine: 생성 완료/진행 중
□ pending_ops.json GCS 백업 완료
```

---

## 8. Day 2 이슈 & 결정사항

```
□ 이슈:
  -

□ 결정사항:
  - PDF 정제 방법 선택: A / B / 하이브리드
  - NER 모델 선택: Flash / Pro
  - NER 프롬프트: zero-shot / few-shot

□ Day 3 준비사항:
  - pending_ops.json 백업 확인
  - 백그라운드 인덱싱 완료 여부 모니터링
  - prompts/graphrag_system_5k.txt 준비 (C10 Caching용)
```

---

> **다음 단계**: Day 2 완료 후 → [day3-gcp-plan.md](./day3-gcp-plan.md) 진행
