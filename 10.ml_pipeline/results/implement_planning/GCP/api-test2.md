# Vertex AI API 테스트 실행 계획 — ML / Deep Learning / LLM

> **v4 — 수정 이력**
> - v2: SDK 일관성, TPU 제약, 일정 현실화, 한국어 품질 지표 전면화, 비용 재산정
> - v3 (필수): Billing Label 한계 보완, ttft 스트리밍 측정, PSC 준비, B3 GCS I/O, C8/C9 분리, Embedding 동적 배치, Spanner 삭제, KR latency 추가
> - v3 (권장): Gemini 2.0 retire 비고, dim_sweep, SDK lockfile, 한국어 3축 평가, C10 Prompt Caching, RAG chunking sweep
> - v4 (필수): A3 Feature Store 코드 Bigtable/Optimized 완전 분리 + embedding index 지정, B3 KFP 데이터 전달 패턴 수정(output_gcs_uri: str + TSV 포맷 + metrics.json 고정 경로), C1 스트리밍 usage_metadata 안전 추출 + fallback, KR latency를 probe runner 방식으로 재정의, C8 time import + token 로깅 + first_token 텍스트 한정, C9 REST PoC Appendix 추가
> - v4 (권장): Embedding tokens_per_char 0.4→0.6 + 절반 재시도 로직, Cloud Logging 동시성 구간 10% 샘플링, KR overhead Pass/Fail을 P50 기준 + P99 관찰치로 완화

> 본 문서는 GCP Vertex AI API를 **Traditional ML**, **Deep Learning**, **LLM** 세 가지 측면에서 실측 테스트하여, 현재 ML Pipeline 설계(`designs/`)가 활용할 수 있는 Vertex AI의 실제 성능·비용·운영성을 검증하는 실행 계획입니다.

---

## 목차

1. [테스트 전략 개요](#1-테스트-전략-개요)
2. [공통 환경 구성](#2-공통-환경-구성)
3. [Part A — Traditional ML](#3-part-a--traditional-ml)
4. [Part B — Deep Learning](#4-part-b--deep-learning)
5. [Part C — LLM / Generative AI](#5-part-c--llm--generative-ai)
6. [Cross-Cutting 테스트](#6-cross-cutting-테스트)
7. [결과 종합 매트릭스](#7-결과-종합-매트릭스)
8. [일정 및 리소스](#8-일정-및-리소스)

---

## 1. 테스트 전략 개요

### 1.1 테스트 범위

```
                    ┌─────────────────────────────────────────────────────┐
                    │               Vertex AI API 테스트 범위               │
                    ├────────────────┬────────────────┬───────────────────┤
                    │  Part A: ML    │  Part B: DL    │   Part C: LLM     │
                    ├────────────────┼────────────────┼───────────────────┤
                    │ AutoML         │ Custom Train   │ Gemini API        │
                    │ Feature Store  │ Kubeflow Pipes │ Embeddings        │
                    │ Model Registry │ HPT (Vizier)   │ Fine-Tuning       │
                    │ Batch Predict  │ GPU/TPU 학습    │ RAG Engine        │
                    │ Online Predict │ Distributed    │ Grounding         │
                    │                │ KGE Serving    │ Model Garden      │
                    │                │                │ Live API          │
                    │                │                │ Agent Engine      │
                    │                │                │ Prompt Caching    │
                    └────────────────┴────────────────┴───────────────────┘
```

### 1.2 현재 설계와의 연결

| 설계 문서 컴포넌트 | Part A 연관 | Part B 연관 | Part C 연관 |
|-------------------|------------|------------|------------|
| **Preprocess Pipeline** (VXP) | Feature Store 연동 | Kubeflow 컴포넌트 | Embedding 생성 |
| **Train Pipeline** (VXP) | AutoML baseline | Custom Training + HPT | SFT / LoRA 학습 |
| **Infer Pipeline** (VXP) | Batch Prediction | Custom Job 추론 | Gemini API 추론 |
| **Model Registry** (MR) | 모델 버전 관리 | 커스텀 모델 등록 | 튜닝 모델 배포 |
| **Pipeline Trigger** (TRG) | — | PipelineJob.submit() | — |

### 1.3 테스트 원칙

1. **API-First**: SDK wrapper가 아닌 REST API 직접 호출 테스트를 병행
2. **비용 추적 이중화**: 리소스 기반(Job/Endpoint)은 `labels.test-id`로 Billing Export 추적. LLM/Embedding API 호출 단위는 **Cloud Logging 별도 저장** 병행 (아래 1.5 참고)
3. **재현성**: Python 스크립트 + YAML config로 정의, 반복 실행 가능. **실행 완료 후 `uv lock` 또는 `pip freeze > requirements-lock.txt`로 정확한 버전 고정 필수**, 결과 리포트에 실제 사용 버전 자동 삽입
4. **3회 반복**: 정량 테스트는 최소 3회, 중간값(median) 기준
   - *예외*: AutoML(A1/A2)은 비용·시간상 1회 + budget 구간 비교로 대체. C10 Prompt Caching은 100회 반복 자체가 통계량 확보.
5. **Quota 사전 확보**: GPU/TPU quota 증가 요청은 테스트 2주 전 완료
6. **한국어 품질 공통 측정**: 모든 LLM 테스트에서 한국어/영어 프롬프트 쌍 병행. **KR latency는 asia-northeast3 probe runner(Cloud Run/VM)에서 us-central1 리소스를 호출하는 방식**으로 측정 — 리전별 모델 가용성 차이와 리소스 스코프 문제를 우회하고 실제 서비스 체감 latency(RTT 포함)를 측정 (C1/C5/C8/C9 적용)
7. **한국어 평가 기준 통일**: 수동 평가는 3축(정확성·완전성·도메인 적합성) + 평가자 2인 중복 체크(10~20% 샘플)로 수행 (아래 1.6 참고)

### 1.4 SDK 버전 및 호환성

```
# 2026-03 기준 권장 SDK (전 테스트 통일)
google-cloud-aiplatform >= 1.74.0   # Training, Pipelines, Registry
google-genai >= 1.5.0               # LLM / Embedding / Tuning / RAG / Agent
kfp >= 2.10.0                       # Kubeflow Pipelines SDK v2
google-cloud-storage >= 2.14.0      # GCS I/O (B3 컴포넌트 내부 명시 사용)
# gcsfs: B3에서 google-cloud-storage로 대체 완료 — 불필요 시 제거 가능

# ⚠ Deprecated (2026-06-24 제거 예정) — 사용 금지
# vertexai.generative_models  → google.genai
# vertexai.language_models    → google.genai
# vertexai.tuning             → google.genai
# vertexai.preview.reasoning_engines → C9에서 Agent Engine REST API로 대체

# SDK 통일 원칙
# - Training / Pipeline / Registry: google-cloud-aiplatform
# - LLM / Embedding / Tuning / RAG / Live / Agent: google-genai (vertexai=True)
# - 두 SDK를 동일 테스트에서 혼용 금지

# ⚠ 모델 수명 주의
# Gemini 2.0 Flash / Flash-Lite: 2026-06-01 retire 예정
# → 2.0 계열은 "비용 최저 기준선"으로만 활용, 서비스 결론은 2.5 계열 기준

# API 버전 고정
# google-genai 사용 시 HttpOptions(api_version="v1") 명시 권장
# v1beta1은 기능이 추가되나 필드/동작이 변경될 수 있음
```

### 1.5 LLM/Embedding 비용 추적 전략

> Gemini API 요청 단위는 Billing Export에 label이 안정적으로 남지 않음.
> 아래 이중 추적 전략을 **모든 C파트 테스트 harness에 공통 적용**.

```python
import google.cloud.logging
import json, time, uuid, random

logging_client = google.cloud.logging.Client()
logger = logging_client.logger("vertex-test-cost-tracker")

def log_api_call(test_id: str, model_id: str, prompt_tokens: int,
                 output_tokens: int, latency_ms: float, region: str = "us-central1",
                 sampling_rate: float = 1.0):
    """LLM/Embedding 호출마다 Cloud Logging에 기록.
    동시성 테스트(C1 100 concurrent 등)에서는 sampling_rate=0.1로 호출해 로깅 비용 제어.
    """
    if sampling_rate < 1.0 and random.random() > sampling_rate:
        return  # 샘플링 드롭
    logger.log_struct({
        "test_id": test_id,
        "model_id": model_id,
        "region": region,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
        "request_id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "sampled": sampling_rate < 1.0,
        "sampling_rate": sampling_rate,
    })

# 사용 규칙
# - 단건/배치 테스트: sampling_rate=1.0 (전수 기록)
# - 동시성 테스트(concurrent ≥ 10): sampling_rate=0.1 (10% 샘플링)
# 샘플링 구간의 비용 집계: SUM(tokens) / sampling_rate 로 보정

# 비용 집계: Cloud Logging → BigQuery 싱크 후 쿼리
# SELECT test_id, model_id,
#        SUM(prompt_tokens / sampling_rate) as estimated_total_input,
#        SUM(output_tokens / sampling_rate) as estimated_total_output
# FROM `project.dataset.vertex_test_cost_tracker`
# GROUP BY test_id, model_id
```

리소스 기반(Job/Endpoint/Spanner) 비용은 기존대로 `labels.test-id`로 Billing Export 집계.
최종 비용 = **Billing Export(리소스) + Cloud Logging 집계(API 호출)** 합산.

### 1.6 한국어 품질 평가 기준

> 전 C파트 공통 적용. 단일 1-5점 대신 3축 분해로 평가자 간 편차 최소화.

| 축 | 설명 | 점수 |
|----|------|------|
| **정확성/환각** | 사실 오류, 존재하지 않는 정보 생성 여부 | 0~3 |
| **완전성** | 질문 의도를 충분히 충족했는가 | 0~3 |
| **도메인 적합성** | 채용/이력서/기업 맥락 용어·표현 적절성 | 0~2 |
| **합계** | | 0~8 |

- 평가자 2명이 독립 채점 후 평균
- 10~20% 샘플은 두 평가자 중복 채점 → 편차(ICC) 체크
- 6점 이상 = 서비스 사용 가능, 4~5점 = 개선 필요, 3점 이하 = 사용 불가

---

## 2. 공통 환경 구성

### 2.1 GCP 프로젝트 설정

```
프로젝트: ml-api-test-vertex
리전: us-central1 (TPU v5e/v6e + A100/H100 가용, 모든 리소스 생성)
       asia-northeast3 (KR probe runner 실행 전용 — Cloud Run Job 배포)
Billing: Budget Alert $4,000 (경고), $5,000 (강제 중단)

KR latency 측정 인프라:
  asia-northeast3에 Cloud Run Job 배포 (test-kr-probe)
  → us-central1 Vertex AI endpoint 호출 → RTT 포함 E2E latency 측정
  → C1/C5/C8/C9에서 공통 활용
  ⚠ client location="asia-northeast3"으로 직접 접근하지 않음
    (모델 미가용/리소스 스코프 이슈 방지)

사전 Quota 요청:
├── NVIDIA_T4: 4 → 8
├── NVIDIA_A100: 0 → 4
├── NVIDIA_H100: 0 → 2 (Part B 전용)
├── TPU_V5E: 0 → 8 chips (2주 전 신청 필수)
├── Custom Training concurrent jobs: 2 → 10
├── Pipeline concurrent runs: 10 → 50
├── Online prediction QPS: 기본 → 필요 시 증가
├── Tuning concurrent jobs: 1 → 3 (Part C 전용)
└── Feature Store online serving: 기본 300,000 req/min(≈5k QPS) → 10k QPS 필요 시
    사전 증가 요청 필수 (기본 quota로는 10k QPS 초과 가능)
```

### 2.2 Feature Store v2 사전 네트워크 준비 *(신규)*

> Optimized 백엔드는 **Private Service Connect(PSC)** 설정이 필요한 경우가 있음.
> 테스트 전 아래 항목을 반드시 확인.

```
체크리스트:
□ VPC에 PSC endpoint 생성 확인
  (gcloud compute forwarding-rules list --filter="target~servicedirectory")
□ Optimized store의 featureViews.searchNearestEntities 호출을 위해
  "indexable feature view" 설정 여부 확인
□ SDK 경로 확인: google.cloud.aiplatform.feature_store vs
  vertexai.resources.preview — 사용 버전에 맞는 경로로 코드 고정
□ 부하 테스트 목표 QPS가 현재 quota 내인지 사전 확인
  (10k QPS 목표 시 Quota 증가 요청 선행)
```

### 2.3 데이터셋 준비

> ⚠ **한국어 데이터 포함 원칙**: DS-TXT-CORPUS, DS-LLM-SFT, DS-LLM-EVAL은 한국어/영어 혼합(비율 7:3) 구성.

| ID | 용도 | 형태 | 크기 | 언어 | Part |
|----|------|------|------|------|------|
| `DS-TAB` | Tabular ML | CSV | 500MB, 1M rows | — | A |
| `DS-IMG` | Image Classification | JPEG + labels | 2GB, 50K images | — | A |
| `DS-TXT-CORPUS` | Text Corpus (이력서+기업뉴스) | JSONL | 5GB, 500K docs | **KO/EN 7:3** | A, B |
| `DS-KGE` | Knowledge Graph Triples | TSV | 1GB, 10M triples | — | B |
| `DS-LLM-SFT` | SFT Training Data | JSONL | 50MB, 10K examples | **KO/EN 7:3** | C |
| `DS-LLM-EVAL` | LLM Evaluation Set | JSONL | 5MB, 1K examples | **KO/EN 7:3** | C |
| `DS-RAG-DOCS` | RAG 문서 (이력서+뉴스) | PDF + TXT | 500MB, 2K docs | **KO/EN 7:3** | C |

### 2.4 공통 인프라

```yaml
gs://ml-api-test-vertex/
├── datasets/
├── pipeline-root/
├── models/
├── predictions/
├── configs/
└── results/

us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/
├── preprocess:latest
├── kge-trainer:latest
├── kge-trainer-tpu:latest   # XLA 빌드 (B2 전용, Week 1 PoC 후 빌드)
├── llm-trainer:latest
└── batch-predictor:latest

VPC: default
Private Google Access: enabled
PSC: Feature Store Optimized 전용 (2.2 체크리스트 선행)
```

### 2.5 테스트 완료 후 리소스 삭제 체크리스트

```
□ Vertex AI Endpoints 전체 undeploy + delete
□ Custom Training Jobs 완료 확인
□ Hyperparameter Tuning Jobs 완료 확인
□ RAG Corpus 삭제 (client.corpora.delete)
□ RagEngineConfig → Unprovisioned tier로 변경 확인
  (Corpus 삭제만으로는 Spanner billing이 멈추지 않을 수 있음)
□ Feature Store Online Stores 삭제
□ GCS 임시 파일 정리 (pipeline-root, predictions)
□ Cloud Logging 싱크 비활성화
□ Billing Export에서 잔여 비용 발생 여부 48시간 모니터링
```

---

## 3. Part A — Traditional ML

### TEST-A1: AutoML Tabular

```python
from google.cloud import aiplatform

aiplatform.init(project="ml-api-test-vertex", location="us-central1")

dataset = aiplatform.TabularDataset.create(
    display_name="test-a1-tabular",
    gcs_source="gs://ml-api-test-vertex/datasets/DS-TAB/data.csv",
    labels={"test-id": "test-a1"}
)

job = aiplatform.AutoMLTabularTrainingJob(
    display_name="test-a1-automl-1hr",
    optimization_prediction_type="classification",
    optimization_objective="maximize-au-prc",
    labels={"test-id": "test-a1"}
)

model = job.run(
    dataset=dataset,
    target_column="target",
    training_fraction_split=0.8,
    validation_fraction_split=0.1,
    test_fraction_split=0.1,
    budget_milli_node_hours=1000,
)
```

**측정 지표**:

| 지표 | 1hr | 4hr | 8hr |
|------|-----|-----|-----|
| `train_wall_time` (min) | ___ | ___ | ___ |
| `au_prc` | ___ | ___ | ___ |
| `au_roc` | ___ | ___ | ___ |
| `cost` ($) | ___ | ___ | ___ |

**Pass/Fail 기준**: 1hr AU-PRC ≥ 0.80, 비용 $21.25/hr × 예산 내

---

### TEST-A2: AutoML Image Classification

| 항목 | 내용 |
|------|------|
| **데이터셋** | `DS-IMG` (50K images, 10 classes) |
| **학습 시간** | 8 node-hours |
| **배포** | Online Endpoint (`n1-standard-4`, min replicas=1) |

> 실행 코드 구조는 A1과 동일 패턴. `AutoMLImageTrainingJob` → `model.deploy()` → Online Prediction 100장 → Endpoint 삭제.

| 지표 | 값 |
|------|---|
| `accuracy` | ___ |
| `prediction_latency_p50` (ms) | ___ |
| `prediction_latency_p99` (ms) | ___ |
| `cold_start_time` (sec) | ___ |
| `train_cost` ($) | ___ |

---

### TEST-A3: Feature Store v2

> ⚠ **실행 전 2.2 체크리스트 완료 필수**. PSC 미설정 시 Optimized 백엔드 실행 불가.
> 부하 테스트 10k QPS는 Quota 증가 신청 후 진행. 부하 생성 도구: **Locust** (Python 기반, Vertex AI SDK와 통합 용이) 또는 **k6** (HTTP 기반 raw endpoint 테스트).

| 항목 | 내용 |
|------|------|
| **데이터** | DS-TAB 50개 피처, 1M entities |
| **백엔드** | Bigtable(fetch 전용) + Optimized(vector search 전용) 완전 분리 |
| **SDK 경로** | `google.cloud.aiplatform.feature_store` (버전 확인 후 고정) |

```python
from google.cloud.aiplatform import feature_store

# ── 1. Bigtable 백엔드: entity fetch 전용 ──────────────────────────────
bt_store = feature_store.FeatureOnlineStore.create_bigtable_store(
    feature_online_store_id="test-a3-bigtable",
    labels={"test-id": "test-a3"}
)

bt_view = bt_store.create_feature_view(
    feature_view_id="user-features-bt",
    source=feature_store.utils.FeatureViewBigQuerySource(
        uri="bq://ml-api-test-vertex.feature_dataset.user_features",
        entity_id_columns=["user_id"]
    )
)

# fetch 테스트
result = bt_view.fetch_feature_values(id="user_12345")

# ── 2. Optimized 백엔드: vector search 전용 ────────────────────────────
# Optimized store는 PSC 설정 필요 (2.2 체크리스트 선행)
opt_store = feature_store.FeatureOnlineStore.create_optimized_store(
    feature_online_store_id="test-a3-optimized",
    labels={"test-id": "test-a3"}
)

# vector search용 FeatureView — embedding feature를 명시적으로 지정
# BQ 테이블에 `embedding ARRAY<FLOAT64>` 컬럼이 있어야 함
opt_view = opt_store.create_feature_view(
    feature_view_id="user-features-opt",
    source=feature_store.utils.FeatureViewBigQuerySource(
        uri="bq://ml-api-test-vertex.feature_dataset.user_features_with_embedding",
        entity_id_columns=["user_id"]
    ),
    index_config=feature_store.utils.IndexConfig(
        embedding_column="embedding",          # vector search 대상 컬럼 명시
        dimensions=768,
        algorithm_config=feature_store.utils.TreeAhConfig()
    )
)

# 동기화 완료 대기
opt_view.sync()

# vector search 테스트 (searchNearestEntities)
results = opt_view.search_nearest_entities(
    query=feature_store.utils.NearestNeighborQuery(
        embedding=[0.1, 0.2] * 384,  # 768-dim
        neighbor_count=10
    )
)
```

> ⚠ **IndexConfig 필드명은 SDK 버전에 따라 다를 수 있음.** 실행 전 `help(feature_store.utils.IndexConfig)`로 실제 파라미터 확인 필수.

| 지표 | Bigtable | Optimized |
|------|----------|-----------|
| `fetch_latency_p50` (ms) | ___ | ___ |
| `fetch_latency_p99` (ms) | ___ | ___ |
| `vector_search_latency_p50` (ms) | N/A | ___ |
| `vector_search_latency_p99` (ms) | N/A | ___ |
| `max_qps_achieved` | ___ | ___ |
| `cost_per_hr` | $0.94/node | $0.30/node |

---

### TEST-A4: Model Registry 생명주기

```python
model_v1 = aiplatform.Model.upload(
    display_name="test-a4-model",
    artifact_uri="gs://ml-api-test-vertex/models/xgboost-v1/",
    serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-7:latest",
    labels={"test-id": "test-a4"}
)

model_v2 = aiplatform.Model.upload(
    display_name="test-a4-model",
    parent_model=model_v1.resource_name,
    artifact_uri="gs://ml-api-test-vertex/models/xgboost-v2/",
    serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-7:latest",
    labels={"test-id": "test-a4"}
)

registry = aiplatform.models.ModelRegistry(model=model_v1.resource_name)
registry.add_version_aliases(["champion"], version=model_v1.version_id)
registry.add_version_aliases(["challenger"], version=model_v2.version_id)

# Alias 기반 배포 → 추론 → Champion 교체 → 정리
champion = registry.get_model(alias="champion")
endpoint = champion.deploy(
    machine_type="n1-standard-4",
    min_replica_count=1,
    labels={"test-id": "test-a4"}
)

prediction = endpoint.predict(instances=[{"feature_1": 1.0, "feature_2": "A"}])

# Champion ↔ Challenger 교체 (alias_switch_time 측정 구간)
import time
t0 = time.perf_counter()
registry.remove_version_aliases(["champion"], version=model_v1.version_id)
registry.add_version_aliases(["champion"], version=model_v2.version_id)
alias_switch_time = time.perf_counter() - t0

# 정리
endpoint.undeploy_all()
endpoint.delete()
```

| 지표 | 값 |
|------|---|
| `upload_time` (sec) | ___ |
| `deploy_time` (sec) | ___ |
| `alias_switch_time` (sec) | ___ |
| `prediction_verified` (bool) | ___ |

---

### TEST-A5: Batch Prediction

> 실행 코드: A1에서 학습한 모델로 `model.batch_predict()` 호출. 1 replica vs 4 replicas 스케일 비교.

| 지표 | 1 replica | 4 replicas |
|------|-----------|------------|
| `total_time` (min) | ___ | ___ |
| `throughput` (rows/sec) | ___ | ___ |
| `cost` ($) | ___ | ___ |
| `cost_per_1M_rows` ($) | ___ | ___ |

---

## 4. Part B — Deep Learning

### TEST-B1: Custom Training Job — GPU 학습 (KGE)

```python
job = aiplatform.CustomContainerTrainingJob(
    display_name="test-b1-kge-t4",
    container_uri="us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/kge-trainer:latest",
    labels={"test-id": "test-b1", "gpu": "t4"}
)

model = job.run(
    args=["--data_path=gs://ml-api-test-vertex/datasets/DS-KGE/",
          "--epochs=50", "--embedding_dim=256", "--batch_size=4096", "--lr=0.001"],
    machine_type="n1-standard-8",
    accelerator_type="NVIDIA_TESLA_T4",
    accelerator_count=1,
    replica_count=1,
    model_display_name="test-b1-kge-model",
    model_serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/pytorch-gpu.2-0:latest"
)
```

| 지표 | T4 ×1 | A100 ×1 | H100 ×1 |
|------|-------|---------|---------|
| `train_time` (min) | ___ | ___ | ___ |
| `final_mrr` | ___ | ___ | ___ |
| `final_hits@10` | ___ | ___ | ___ |
| `gpu_util_avg` (%) | ___ | ___ | ___ |
| `cost_total` ($) | ___ | ___ | ___ |
| `cold_start` (sec) | ___ | ___ | ___ |

**비용 참고**: T4≈$0.62/hr, A100≈$3.67/hr, H100≈$12.47/hr

**Pass/Fail 기준**: A100이 T4 대비 3× 이상 단축, cold start < 5분

---

### TEST-B2: Custom Training Job — TPU 학습

> ⚠ **Week 1 Day 5에 사전 PoC 필수**. 3일 내 미해결 시 B2 스킵 후 "TPU 진입 장벽" 보고.
> KGE(TransE)는 sparse embedding lookup 특성상 TPU 효율이 GPU 대비 낮을 수 있음 — 결과가 TPU 불리여도 정상 데이터.

```python
# 컨테이너 내부 필수 XLA 패턴
import torch_xla.core.xla_model as xm
import torch_xla.distributed.parallel_loader as pl

device = xm.xla_device()
train_loader = pl.MpDeviceLoader(original_loader, device)  # DataLoader 교체

# optimizer.step() 대신
xm.optimizer_step(optimizer)
xm.mark_step()  # 비동기 실행 강제 동기화

# 잡 제출
job = aiplatform.CustomContainerTrainingJob(
    display_name="test-b2-kge-tpu-v5e",
    container_uri="us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/kge-trainer-tpu:latest",
    labels={"test-id": "test-b2", "accel": "tpu-v5e"}
)

model = job.run(
    args=["--data_path=gs://ml-api-test-vertex/datasets/DS-KGE/",
          "--epochs=50", "--embedding_dim=256", "--batch_size=16384", "--use_tpu=true"],
    machine_type="ct5lp-hightpu-4t",
    replica_count=1,  # v5e 4칩 single-host — replica_count=1 맞음
)
```

| 지표 | A100 ×1 (B1) | TPU v5e ×4 |
|------|--------------|------------|
| `train_time` (min) | ___ | ___ |
| `cost_total` ($) | ___ | ___ |
| `sparse_op_efficiency` (%) | 100% | ___ |
| `code_change_effort` (hours) | 0 | ___ |

---

### TEST-B3: Kubeflow Pipeline — E2E

> ⚠ **GCS I/O 수정**: pandas GCS 직접 접근 불가. `gcsfs` 또는 `google-cloud-storage` 명시 사용으로 수정.

```python
from kfp import dsl, compiler
from google_cloud_pipeline_components.v1.custom_job import CustomTrainingJobOp

# KFP 데이터 전달 원칙:
# - 컴포넌트 간 경로 전달은 dsl.Output[dsl.Dataset].path(로컬) 대신
#   output_gcs_uri: str 을 반환해 명시적 GCS 경로로 전달
# - CustomTrainingJobOp 워커는 파이프라인 컴포넌트 로컬 파일에 접근 불가
#   → GCS URI 문자열로만 연결

@dsl.component(
    base_image="python:3.11",
    packages_to_install=["google-cloud-storage"]
)
def preprocess(input_uri: str, output_gcs_uri: str) -> str:
    """DS-KGE는 TSV 포맷 — pandas read_csv(sep='\t')로 읽어 GCS에 직접 저장.
    output_gcs_uri를 파라미터로 받아 명시적으로 쓰고 그대로 반환.
    """
    import csv, io
    from google.cloud import storage

    client = storage.Client()

    # TSV 읽기 (DS-KGE: head\trelation\ttail 형식)
    src_bucket, src_blob = input_uri.replace("gs://", "").split("/", 1)
    raw = client.bucket(src_bucket).blob(src_blob).download_as_text()
    rows = list(csv.reader(io.StringIO(raw), delimiter="\t"))

    # 전처리 후 GCS에 저장 (예: 헤더 추가, 필터링)
    processed = "head\trelation\ttail\n" + "\n".join(
        "\t".join(r) for r in rows if len(r) == 3
    )
    dst_bucket, dst_blob = output_gcs_uri.replace("gs://", "").split("/", 1)
    client.bucket(dst_bucket).blob(dst_blob).upload_from_string(processed)

    return output_gcs_uri  # str 반환으로 다음 컴포넌트에 GCS URI 전달

@dsl.component(
    base_image="python:3.11",
    packages_to_install=["google-cloud-storage"]
)
def evaluate(metrics_gcs_uri: str, threshold: float) -> bool:
    """trainer가 metrics를 gs://.../metrics.json 고정 경로에 저장하는 것을 전제.
    디렉터리가 아닌 파일 URI를 받아야 함.
    """
    import json
    from google.cloud import storage

    client = storage.Client()
    bucket_name, blob_path = metrics_gcs_uri.replace("gs://", "").split("/", 1)
    blob = client.bucket(bucket_name).blob(blob_path)
    metrics = json.loads(blob.download_as_text())
    return metrics["mrr"] >= threshold

@dsl.component(
    base_image="python:3.11",
    packages_to_install=["google-cloud-aiplatform"]
)
def register_model(model_gcs_uri: str, passed_gate: bool):
    if not passed_gate:
        return
    from google.cloud import aiplatform
    aiplatform.Model.upload(
        display_name="kge-model",
        artifact_uri=model_gcs_uri,
        serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/pytorch-gpu.2-0:latest"
    )

# trainer 컨테이너 내부 규약 (kge-trainer:latest에 반드시 구현):
# - 학습 결과: gs://{OUTPUT_DIR}/model/ 에 저장
# - metrics: gs://{OUTPUT_DIR}/metrics.json 에 고정 저장
#   형식: {"mrr": 0.35, "hits_at_10": 0.52, "epoch": 50}

# ⚠ KFP v2에서 파이프라인 파라미터(PipelineChannel)를 Python f-string으로
#   GCS 경로에 조합하면 컴파일 시점에 placeholder 치환 문제가 발생할 수 있음.
#   안전한 패턴: 전체 경로를 파이프라인 파라미터로 직접 전달.

@dsl.pipeline(name="test-b3-e2e-pipeline",
              pipeline_root="gs://ml-api-test-vertex/pipeline-root")
def ml_pipeline(dataset_uri: str, threshold: float = 0.3,
                preprocess_output_uri: str = "gs://ml-api-test-vertex/results/b3/run-001/preprocessed/data.tsv",
                train_output_dir: str = "gs://ml-api-test-vertex/results/b3/run-001/train-output",
                metrics_uri: str = "gs://ml-api-test-vertex/results/b3/run-001/train-output/metrics.json",
                model_uri: str = "gs://ml-api-test-vertex/results/b3/run-001/train-output/model/"):
    # 모든 GCS 경로를 파이프라인 파라미터로 전달 → 런타임 해석 보장 + 재실행 시 경로 변경 가능

    # Step 1: preprocess — TSV 읽어 GCS에 전처리 결과 저장, URI 반환
    preprocess_task = preprocess(
        input_uri=dataset_uri,
        output_gcs_uri=preprocess_output_uri
    )

    # Step 2: Custom Training — preprocess 출력 GCS URI를 str로 전달
    train_task = CustomTrainingJobOp(
        display_name="kge-train",
        worker_pool_specs=[{
            "machineSpec": {
                "machineType": "n1-standard-8",
                "acceleratorType": "NVIDIA_TESLA_T4",
                "acceleratorCount": 1
            },
            "replicaCount": 1,
            "containerSpec": {
                "imageUri": "us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/kge-trainer:latest",
                "args": [
                    "--data_path", preprocess_task.output,
                    "--output_dir", train_output_dir
                ]
            }
        }],
        project="ml-api-test-vertex",
        location="us-central1"
    )
    train_task.after(preprocess_task)

    # Step 3: evaluate — metrics.json 고정 URI 입력
    eval_task = evaluate(
        metrics_gcs_uri=metrics_uri,
        threshold=threshold
    )
    eval_task.after(train_task)

    # Step 4: register — model/ 디렉터리 URI 입력
    register_model(
        model_gcs_uri=model_uri,
        passed_gate=eval_task.output
    )

compiler.Compiler().compile(ml_pipeline, "pipeline.yaml")

# 재실행 시 run_id 부분만 변경 (run-001 → run-002 등)
RUN_ID = "run-001"
BASE_PATH = f"gs://ml-api-test-vertex/results/b3/{RUN_ID}"

job = aiplatform.PipelineJob(
    display_name="test-b3-e2e",
    template_path="pipeline.yaml",
    pipeline_root="gs://ml-api-test-vertex/pipeline-root",
    parameter_values={
        "dataset_uri": "gs://ml-api-test-vertex/datasets/DS-KGE/triples.tsv",
        "threshold": 0.3,
        "preprocess_output_uri": f"{BASE_PATH}/preprocessed/data.tsv",
        "train_output_dir": f"{BASE_PATH}/train-output",
        "metrics_uri": f"{BASE_PATH}/train-output/metrics.json",
        "model_uri": f"{BASE_PATH}/train-output/model/",
    },
    labels={"test-id": "test-b3"}
)
job.submit()
```

| 지표 | 값 |
|------|---|
| `compile_time` (sec) | ___ |
| `submit_to_running` (sec) | ___ |
| `total_pipeline_time` (min) | ___ |
| `per_component_overhead` (sec) | ___ |
| `cancel_response_time` (sec) | ___ |

---

### TEST-B4: Hyperparameter Tuning (Vizier)

```python
from google.cloud.aiplatform import hyperparameter_tuning as hpt

# HPT 기반 CustomJob 정의 (B1과 동일 컨테이너, epoch만 축소)
custom_job = aiplatform.CustomJob(
    display_name="test-b4-hpt-base",
    worker_pool_specs=[{
        "machineSpec": {"machineType": "n1-standard-8",
                        "acceleratorType": "NVIDIA_TESLA_T4", "acceleratorCount": 1},
        "replicaCount": 1,
        "containerSpec": {
            "imageUri": "us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/kge-trainer:latest",
            "args": ["--epochs=10"]  # HPT이므로 짧은 학습
        }
    }],
    labels={"test-id": "test-b4"}
)

hp_job = aiplatform.HyperparameterTuningJob(
    display_name="test-b4-hpt-bayesian",
    custom_job=custom_job,
    metric_spec={"mrr": "maximize"},
    parameter_spec={
        "lr": hpt.DoubleParameterSpec(min=1e-4, max=1e-1, scale="log"),
        "embedding_dim": hpt.IntegerParameterSpec(min=64, max=512, scale="linear"),
        "batch_size": hpt.IntegerParameterSpec(min=1024, max=16384, scale="log"),
        "margin": hpt.DoubleParameterSpec(min=0.5, max=5.0, scale="linear"),
    },
    max_trial_count=20,
    parallel_trial_count=5,
    labels={"test-id": "test-b4"}
)
hp_job.run()
```

| 지표 | Bayesian | Random |
|------|----------|--------|
| `best_mrr` | ___ | ___ |
| `trials_to_best` | ___ | ___ |
| `total_time` (min) | ___ | ___ |
| `total_cost` ($) | ___ | ___ |

---

### TEST-B5: 분산 학습 (Multi-GPU)

> 실행 코드: B1과 동일 컨테이너에 `--distributed=true` 추가. `a2-highgpu-1g`(1×A100) / `a2-highgpu-2g`(2×) / `a2-highgpu-4g`(4×).

| 지표 | 1× A100 | 2× A100 | 4× A100 |
|------|---------|---------|---------|
| `train_time` (min) | ___ | ___ | ___ |
| `scaling_efficiency` (%) | 100% | ___ | ___ |
| `cost_total` ($) | ___ | ___ | ___ |
| `gpu_util_avg` (%) | ___ | ___ | ___ |

**스케일링 효율**: `efficiency = (1GPU_time / (N_GPU_time × N)) × 100%`

---

### TEST-B6: KGE 모델 온라인 서빙 latency

> **GraphRAG 실시간 매칭 요구사항 검증.** p99 < 200ms가 Pass 기준.

```python
from google.cloud import aiplatform
import time, concurrent.futures

aiplatform.init(project="ml-api-test-vertex", location="us-central1")

# B1에서 학습한 KGE 모델을 Endpoint에 배포
model = aiplatform.Model("projects/ml-api-test-vertex/locations/us-central1/models/TEST_B1_MODEL_ID")

# CPU 서빙 Endpoint
endpoint_cpu = model.deploy(
    machine_type="n1-standard-4",
    min_replica_count=1,
    max_replica_count=1,
    deployed_model_display_name="test-b6-kge-cpu",
    labels={"test-id": "test-b6", "accel": "cpu"}
)

# GPU(T4) 서빙 Endpoint
endpoint_gpu = model.deploy(
    machine_type="n1-standard-4",
    accelerator_type="NVIDIA_TESLA_T4",
    accelerator_count=1,
    min_replica_count=1,
    max_replica_count=1,
    deployed_model_display_name="test-b6-kge-gpu",
    labels={"test-id": "test-b6", "accel": "t4"}
)

# 단건 latency 측정 (3회 반복, median)
test_instance = {"head": "entity_123", "relation": "similar_to"}  # KGE 모델 입력 형식에 맞춤

def measure_latency(endpoint, n=100):
    latencies = []
    for _ in range(n):
        start = time.perf_counter()
        endpoint.predict(instances=[test_instance])
        latencies.append((time.perf_counter() - start) * 1000)
    latencies.sort()
    return {"p50": latencies[n//2], "p99": latencies[int(n*0.99)]}

# 동시성 50 QPS 측정
def measure_concurrent(endpoint, concurrency=50, total=500):
    latencies = []
    def single_call():
        start = time.perf_counter()
        endpoint.predict(instances=[test_instance])
        return (time.perf_counter() - start) * 1000
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        latencies = list(pool.map(lambda _: single_call(), range(total)))
    return len(latencies) / (sum(latencies) / 1000)  # QPS

# 정리
endpoint_cpu.undeploy_all(); endpoint_cpu.delete()
endpoint_gpu.undeploy_all(); endpoint_gpu.delete()
```

| 지표 | CPU 서빙 | GPU(T4) 서빙 |
|------|---------|-------------|
| `single_query_latency_p50` (ms) | ___ | ___ |
| `single_query_latency_p99` (ms) | ___ | ___ |
| `throughput_at_50_concurrent` (QPS) | ___ | ___ |
| `cost_per_hr` ($) | ___ | ___ |
| `cold_start_time` (sec) | ___ | ___ |

**Pass/Fail 기준**: p99 < 200ms (CPU 또는 GPU 중 하나 이상)

---

## 5. Part C — LLM / Generative AI

> **모든 LLM 테스트 공통 원칙**:
> 1. 영어/한국어 프롬프트 쌍 병행 실행
> 2. **KR latency는 asia-northeast3 probe runner(Cloud Run Job)에서 us-central1 리소스를 호출**해 측정. 모델/리소스 가용성 문제를 우회하고 실제 서비스 체감 RTT를 측정. (C1/C5/C8/C9 적용)
> 3. 비용 추적은 1.5의 Cloud Logging 병행 방식 적용 (동시성 ≥10 구간은 10% 샘플링)
> 4. 한국어 수동 평가는 1.6의 3축 기준 적용

---

### TEST-C1: Gemini API — 기본 추론 성능

> ⚠ **ttft 측정 수정**: 비스트리밍으로는 ttft ≠ total_latency 구분 불가. **스트리밍(SSE)으로 first chunk 수신 시점을 ttft로 측정**.

```python
import google.genai as genai
from google.genai import types
import time

client_us = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")
# KR latency: client_us를 그대로 사용하되, asia-northeast3 probe runner(Cloud Run Job)에서 실행
# → client location 변경 대신 실행 환경 위치로 RTT 측정 (1.3 원칙 6 참고)

prompts = {
    "short_en": "Summarize the concept of knowledge graph embedding in one sentence.",
    "short_ko": "지식 그래프 임베딩 개념을 한 문장으로 요약해줘.",
    "medium_en": open("prompts/medium_1k_en.txt").read(),
    "medium_ko": open("prompts/medium_1k_ko.txt").read(),
    "long_en":  open("prompts/long_10k_en.txt").read(),
    "long_ko":  open("prompts/long_10k_ko.txt").read(),
    # xlong (100K tokens): 비용·시간 대비 효용이 낮아 의도적 제외.
    # 100K 컨텍스트 테스트가 필요할 경우 C5 RAG 또는 C10 Caching에서 간접 검증 가능.
}

def measure_streaming(client, model_id: str, prompt: str, test_id: str, region: str):
    ttft = None
    start = time.perf_counter()
    usage = None

    # 스트리밍 호출로 ttft / total_latency 분리 측정
    for chunk in client.models.generate_content_stream(
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=2048)
    ):
        # ttft: 텍스트가 있는 첫 chunk 도착 시점으로 한정 (빈 이벤트 제외)
        if ttft is None and getattr(chunk, "text", None):
            ttft = (time.perf_counter() - start) * 1000  # ms

        # usage_metadata는 마지막 summary chunk에만 존재하는 경우가 많음
        # → 루프 전체에서 가장 마지막으로 유효한 값을 누적
        if getattr(chunk, "usage_metadata", None) is not None:
            usage = chunk.usage_metadata

    total_latency = (time.perf_counter() - start) * 1000

    # usage 안전 추출 — summary chunk가 없으면 0으로 fallback 후 로그에 표시
    prompt_tokens  = getattr(usage, "prompt_token_count", 0)    if usage else 0
    output_tokens  = getattr(usage, "candidates_token_count", 0) if usage else 0
    token_source   = "api" if usage else "fallback_zero"

    log_api_call(test_id, model_id, prompt_tokens, output_tokens, total_latency, region)

    if usage is None:
        # fallback: non-stream 1회 호출로 토큰 수 보정 (샘플링 — 매 호출마다 하지 않음)
        import warnings
        warnings.warn(f"[{test_id}] usage_metadata 누락 — token count = 0 기록됨. "
                      "비용 집계 시 해당 구간은 SKU+시간창으로 Billing Export 대조 필요.")

    return ttft, total_latency, prompt_tokens, output_tokens
```

**측정 지표**:

| 지표 | 2.5 Flash | 2.5 Pro | 2.0 Flash-Lite* |
|------|-----------|---------|----------------|
| `ttft_p50_us` (ms) | ___ | ___ | ___ |
| `ttft_p99_us` (ms) | ___ | ___ | ___ |
| `ttft_p50_kr` (ms) | ___ | ___ | ___ |
| `total_latency_p50_us` (ms) | ___ | ___ | ___ |
| `total_latency_p50_kr` (ms) | ___ | ___ | ___ |
| `tokens_per_sec` | ___ | ___ | ___ |
| `korean_quality` (3축, 0-8) | ___ | ___ | ___ |
| `input_cost_per_1M` ($) | $0.30 | $1.25 | $0.075 |
| `output_cost_per_1M` ($) | $2.50 | $10.00 | $0.30 |
| `throttle_at_N_concurrent` | ___ | ___ | ___ |

> *Gemini 2.0 Flash-Lite: 2026-06-01 retire 예정 — 비용 최저 기준선으로만 활용

**Pass/Fail 기준**:
- ttft_p50 < 500ms (Short prompt, 단일 요청, us-central1)
- asia-northeast3(KR probe runner) latency overhead: **P50 기준 < 150ms 추가** / P99는 관찰치로만 기록 (네트워크 지터 제외 목적)

---

### TEST-C2: Embeddings API — 대규모 텍스트 임베딩

> ⚠ **동적 배치 수정**: 요청당 최대 250 texts + 20,000 tokens 제한. 한국어 문서는 토큰 수가 가변적이므로 **토큰 기반 동적 배치** 적용.
> ⚠ **dim_sweep 추가**: 소규모 샘플(10K)로 256/768/1536 품질 비교 후 본 테스트 차원 결정.

```python
import google.genai as genai
from google.genai import types

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")

def dynamic_batch(texts: list[str], max_texts: int = 250, max_tokens: int = 20000,
                  tokens_per_char: float = 0.6) -> list[list[str]]:
    """토큰 기반 동적 배치.
    tokens_per_char=0.6: 한국어는 영어보다 문자당 토큰 비율이 높아 0.4는 과소 추정.
    0.6으로 안전 마진 확보 (실제 상한 20,000의 ~66% 수준에서 배치 분할).
    """
    batches, current_batch, current_tokens = [], [], 0
    for text in texts:
        estimated_tokens = int(len(text) * tokens_per_char)
        if (len(current_batch) >= max_texts or
                current_tokens + estimated_tokens > max_tokens):
            if current_batch:
                batches.append(current_batch)
            current_batch, current_tokens = [text], estimated_tokens
        else:
            current_batch.append(text)
            current_tokens += estimated_tokens
    if current_batch:
        batches.append(current_batch)
    return batches

def embed_with_retry(client, model: str, batch: list[str],
                     config, max_splits: int = 3) -> list:
    """토큰 상한 초과 시 배치를 절반으로 쪼개 재시도.
    API가 토큰 초과 에러(InvalidArgument / 400)를 반환하면 재귀적으로 분할.
    """
    from google.api_core.exceptions import InvalidArgument
    try:
        resp = client.models.embed_content(model=model, contents=batch, config=config)
        return [e.values for e in resp.embeddings]
    except InvalidArgument as e:
        if "token" in str(e).lower() and max_splits > 0 and len(batch) > 1:
            mid = len(batch) // 2
            left  = embed_with_retry(client, model, batch[:mid], config, max_splits - 1)
            right = embed_with_retry(client, model, batch[mid:], config, max_splits - 1)
            return left + right
        raise  # 단일 텍스트 자체가 초과하거나 다른 에러면 재전파

# Step 1: dim_sweep — 10K 샘플로 모델별·차원별 품질 비교
# ⚠ dim_sweep과 본 테스트는 동일 모델을 사용해야 결과 적용 가능
MODELS = ["gemini-embedding-001", "text-embedding-005"]
DIM_SWEEP = [256, 768, 1536]  # text-embedding-005만 output_dimensionality 지원
sweep_results = {}
sample_texts = load_sample(n=10000)

for model_id in MODELS:
    dims = DIM_SWEEP if model_id == "text-embedding-005" else [None]  # gemini-embedding-001은 고정 차원
    for dim in dims:
        batches = dynamic_batch(sample_texts)
        embeddings = []
        for batch in batches:
            config = types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            if dim is not None:
                config = types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=dim
                )
            resp = client.models.embed_content(
                model=model_id, contents=batch, config=config
            )
            embeddings.extend([e.values for e in resp.embeddings])
        ndcg = evaluate_retrieval(embeddings, sample_texts)
        key = f"{model_id}:{dim or 'default'}"
        sweep_results[key] = ndcg
        print(f"{key}: nDCG@10={ndcg:.4f}")

# Step 2: 최적 모델+차원 조합 결정
best_key = max(sweep_results, key=sweep_results.get)
best_model, best_dim_str = best_key.split(":")
best_dim = None if best_dim_str == "default" else int(best_dim_str)
print(f"선택: model={best_model}, dim={best_dim_str} (본 테스트에 적용)")

# Step 3: 500K 전체 임베딩 (선택된 모델+차원 적용, 동적 배치)
all_texts = load_all_corpus()
batches = dynamic_batch(all_texts)
for batch in batches:
    config = types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
    if best_dim is not None:
        config = types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=best_dim
        )
    resp = client.models.embed_content(
        model=best_model, contents=batch, config=config
    )
```

**dim_sweep 결과 (10K 샘플)**:

| dim | `ko_ndcg@10` | `en_ndcg@10` | `cost_ratio` |
|-----|-------------|-------------|-------------|
| 256 | ___ | ___ | 1.0× |
| 768 | ___ | ___ | 1.0× |
| 1536 | ___ | ___ | 1.0× |

> 비용은 차원과 무관(토큰 기준 과금). 품질 차이가 0.02 이상이면 높은 차원 선택.

**본 테스트 측정 지표 (500K, 선택된 dim 적용)**:

| 지표 | gemini-embedding-001 | text-embedding-005 |
|------|---------------------|-------------------|
| `single_latency_p50` (ms) | ___ | ___ |
| `batch_dynamic_latency_p50` (ms) | ___ | ___ |
| `throughput` (docs/min) | ___ | ___ |
| `total_500K_time` (min) | ___ | ___ |
| `total_cost` ($) | ___ | ___ |
| `ko_ndcg@10` | ___ | ___ |
| `en_ndcg@10` | ___ | ___ |
| `ko_en_quality_delta` | ___ | ___ |

---

### TEST-C3: Supervised Fine-Tuning (SFT)

```python
import google.genai as genai
from google.genai import types

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")

tuning_job = client.tunings.tune(
    base_model="gemini-2.0-flash-001",
    training_dataset=types.TuningDataset(
        gcs_uri="gs://ml-api-test-vertex/datasets/DS-LLM-SFT/train.jsonl"
    ),
    config=types.CreateTuningJobConfig(
        tuned_model_display_name="test-c3-sft-flash-3ep",
        epoch_count=3,
        adapter_size="ADAPTER_SIZE_FOUR",
        learning_rate_multiplier=1.0,
        validation_dataset=types.TuningDataset(
            gcs_uri="gs://ml-api-test-vertex/datasets/DS-LLM-SFT/val.jsonl"
        )
    )
)
```

**측정 지표**:

| 지표 | Base | SFT 1ep | SFT 3ep | SFT 5ep |
|------|------|---------|---------|---------|
| `train_cost` ($) | — | ___ | ___ | ___ |
| `rouge_l_ko` | ___ | ___ | ___ | ___ |
| `rouge_l_en` | ___ | ___ | ___ | ___ |
| `korean_quality` (3축 0-8) | ___ | ___ | ___ | ___ |
| `inference_latency_p50` (ms) | ___ | ___ | ___ | ___ |

---

### TEST-C4: LoRA Fine-Tuning (Gemma 3)

```python
job = aiplatform.CustomContainerTrainingJob(
    display_name="test-c4-gemma3-lora",
    container_uri="us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/llm-trainer:latest",
    labels={"test-id": "test-c4"}
)

model = job.run(
    args=["--model_name=google/gemma-3-4b", "--method=lora",
          "--lora_rank=16", "--lora_alpha=32", "--epochs=3",
          "--batch_size=4", "--gradient_accumulation=8",
          "--data_path=gs://ml-api-test-vertex/datasets/DS-LLM-SFT/"],
    machine_type="a2-highgpu-1g",
    accelerator_type="NVIDIA_TESLA_A100",
    accelerator_count=1,
)
```

| 지표 | Gemini 2.0 Flash SFT | Gemma 3 4B LoRA |
|------|---------------------|----------------|
| `train_cost` ($) | ___ | ___ |
| `rouge_l_ko` | ___ | ___ |
| `korean_quality` (3축 0-8) | ___ | ___ |
| `inference_latency` (ms) | ___ | ___ |
| `deployment_flexibility` | Vertex AI only | 어디든 가능 |

---

### TEST-C5: RAG Engine — 문서 검색 + 생성

> ⚠ **삭제 절차**: 테스트 완료 후 Corpus 삭제 + RagEngineConfig → **Unprovisioned tier** 확인 필수 (Corpus 삭제만으로 Spanner billing이 멈추지 않을 수 있음).
> **chunking sweep 추가**: 한국어 이력서/뉴스는 512 고정이 최적이 아닐 수 있음.

```python
import google.genai as genai
from google.genai import types

client_us = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")
# KR latency: corpus/RAG는 us-central1에 생성.
# asia-northeast3 probe runner(Cloud Run Job)에서 us-central1 endpoint 호출 → RTT 포함 측정.
# RAG corpus는 리전 귀속 리소스이므로 client location="asia-northeast3"으로 접근하지 않음.

corpus = client_us.corpora.create(
    display_name="test-c5-rag-corpus",
    rag_embedding_model_config=types.RagEmbeddingModelConfig(
        vertex_prediction_endpoint=types.VertexPredictionEndpoint(
            model="publishers/google/models/gemini-embedding-001"
        )
    ),
    backend_config=types.RagCorpusBackendConfig(
        rag_managed_db=types.RagManagedDbConfig(tier="BASIC")  # BASIC 먼저, 필요 시 SCALED
    )
)

# Chunking sweep: 256 / 512 / 1024 — 소규모(200 docs)로 먼저 품질 비교
# ⚠ import_files는 기존 문서에 추가(append)됨 — chunk_size별 별도 corpus 필수
CHUNK_SIZES = [256, 512, 1024]
sweep_corpora = {}  # 삭제 대상 관리

for chunk_size in CHUNK_SIZES:
    # chunk_size별 별도 corpus 생성
    sweep_corpus = client_us.corpora.create(
        display_name=f"test-c5-sweep-{chunk_size}",
        rag_embedding_model_config=types.RagEmbeddingModelConfig(
            vertex_prediction_endpoint=types.VertexPredictionEndpoint(
                model="publishers/google/models/gemini-embedding-001"
            )
        ),
        backend_config=types.RagCorpusBackendConfig(
            rag_managed_db=types.RagManagedDbConfig(tier="BASIC")
        )
    )
    sweep_corpora[chunk_size] = sweep_corpus

    import_op = client_us.corpora.import_files(
        name=sweep_corpus.name,
        import_rag_files_config=types.ImportRagFilesConfig(
            gcs_source=types.GcsSource(
                uris=["gs://ml-api-test-vertex/datasets/DS-RAG-DOCS/sample_200/"]
            ),
            rag_file_chunking_config=types.RagFileChunkingConfig(
                chunk_size=chunk_size,
                chunk_overlap=int(chunk_size * 0.2)  # 20% overlap 고정
            ),
            max_embedding_requests_per_min=900
        )
    )
    # 한국어 쿼리 10개로 Recall@5 측정
    ko_recall = evaluate_retrieval_ko(sweep_corpus, chunk_size)
    print(f"chunk_size={chunk_size}: KO Recall@5={ko_recall:.3f}")

# sweep 완료 후 sweep용 corpus 삭제 (본 테스트 corpus는 별도 생성)
for cs, sc in sweep_corpora.items():
    client_us.corpora.delete(name=sc.name)
```

**Chunking sweep 결과 (200 docs 샘플)**:

| chunk_size | `ko_recall@5` | `en_recall@5` | 선택 여부 |
|-----------|--------------|--------------|---------|
| 256 | ___ | ___ | |
| 512 | ___ | ___ | |
| 1024 | ___ | ___ | ✓ 최고 성능 |

**본 테스트 측정 지표 (2K docs, 최적 chunk_size 적용)**:

| 지표 | us-central1 | KR probe→us |
|------|------------|----------------|
| `retrieval_latency_p50_ko` (ms) | ___ | ___ |
| `retrieval_latency_p99_ko` (ms) | ___ | ___ |
| `rag_generation_latency_p50_ko` (ms) | ___ | ___ |
| `recall_at_5_ko` | ___ | ___ |
| `recall_at_5_en` | ___ | ___ |
| `ndcg_at_5_ko` | ___ | ___ |
| `rag_vs_base_accuracy_delta_ko` (%) | ___ | ___ |
| `monthly_spanner_cost_basic` ($) | ___ | N/A |

**삭제 체크리스트**:
```
□ client.corpora.delete(name=corpus.name)
□ RagEngineConfig tier → Unprovisioned 확인
□ 48시간 후 Billing Export에서 Spanner 잔여 청구 없음 확인
```

---

### TEST-C6: Grounding with Google Search

```python
response = client_us.models.generate_content(
    model="gemini-2.5-flash",
    contents="2026년 최신 그래프 신경망 연구 동향을 알려줘.",
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
)
```

| 지표 | Grounding ON (KO) | Grounding ON (EN) | Grounding OFF |
|------|-----------------|-----------------|---------------|
| `factual_accuracy` (%) | ___ | ___ | ___ |
| `korean_quality` (3축 0-8) | ___ | N/A | ___ |
| `latency_p50_us` (ms) | ___ | ___ | ___ |
| `cost_per_query` ($) | $0.035+토큰 | $0.035+토큰 | 토큰만 |

---

### TEST-C7: Model Garden — 오픈 모델 비교

| 지표 | Gemini 2.5 Pro | Llama 4 Scout | Mistral Large |
|------|---------------|---------------|---------------|
| `latency_p50_us` (ms) | ___ | ___ | ___ |
| `tokens_per_sec` | ___ | ___ | ___ |
| `korean_quality` (3축 0-8) | ___ | ___ | ___ |
| `ko_latency_overhead` (ms) | ___ | ___ | ___ |
| `cost_per_1M_input` ($) | $1.25 | ___ | ___ |

---

### TEST-C8: Live API — 실시간 스트리밍 세션 *(분리)*

> **C8 분리 이유**: 기존 C8 코드(`client.aio.live.connect`)는 Gemini Live API(실시간 양방향 스트리밍)이며 Agent Engine(배포/툴체인/세션 스토리지)과 별개의 축.
> C8은 Live API 성능을, C9는 Agent Engine 운영을 각각 검증.

```python
import google.genai as genai
from google.genai import types
import asyncio
import time  # ← 누락 수정

# us-central1: Live API 직접 연결
client_us = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")
# KR latency: asia-northeast3 probe runner(Cloud Run Job)에서 us-central1 Live API 호출
# → Live API는 region별 가용성 차이가 있어 client location 변경 대신 probe runner 방식 사용
# probe runner 실행 시 client_us를 그대로 사용하고, 실행 환경(VM region)만 asia-northeast3으로 변경

async def test_live_session(client, region: str):
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        system_instruction="당신은 Graph/RAG 도메인 전문가입니다. 한국어로 응답해주세요."
    )
    async with client.aio.live.connect(model="gemini-2.5-flash", config=config) as session:
        turns = [
            "GraphRAG의 커뮤니티 탐지는 어떻게 작동해?",
            "그 결과를 요약 생성에 어떻게 활용해?",   # 컨텍스트 유지 확인
            "TransE 모델과 비교하면 어떤 차이가 있어?",
        ]
        for turn_idx, query in enumerate(turns):
            start = time.perf_counter()
            await session.send(input=query, end_of_turn=True)

            first_token_time = None
            char_count = 0
            async for response in session.receive():
                # TTFT: 텍스트가 있는 첫 응답 이벤트만 (빈 이벤트/메타 이벤트 제외)
                text = getattr(response, "text", None)
                if first_token_time is None and text:
                    first_token_time = (time.perf_counter() - start) * 1000
                if text:
                    char_count += len(text)

            total = (time.perf_counter() - start) * 1000

            # 토큰 수 근사: Live API는 usage_metadata가 없을 수 있음
            # → 문자 수 기반 근사치로 로깅 (한국어: ~0.6 tokens/char)
            # ⚠ 근사치 오차 20~40% 가능. Live API 호출은 Billing Export에서도
            #   개별 분리가 어려워 X3 대조 보정에 한계가 있음.
            #   비용 집계 시 "추정치(±40%)" 명시 필수.
            approx_output_tokens = int(char_count * 0.6)
            approx_input_tokens  = int(len(query) * 0.6)

            log_api_call(
                "test-c8", "gemini-2.5-flash",
                approx_input_tokens, approx_output_tokens,
                total, region
            )

            print(f"Turn {turn_idx+1} | ttft={first_token_time:.0f}ms | "
                  f"total={total:.0f}ms | ~{approx_output_tokens} out_tokens")

# us-central1에서 직접 실행
asyncio.run(test_live_session(client_us, "us-central1"))

# KR latency: 아래 코드를 asia-northeast3 Cloud Run Job에 배포 후 실행
# (동일 client_us 사용, 실행 환경 위치만 asia-northeast3)
# asyncio.run(test_live_session(client_us, "asia-northeast3-probe"))
```

**측정 지표**:

| 지표 | us-central1 | KR probe runner→us |
|------|------------|----------------|
| `ttft_p50` (ms) | ___ | ___ |
| `ttft_p99` (ms) | ___ | ___ |
| `turn_latency_p50` (ms) | ___ | ___ |
| `context_maintained_3turns` (bool) | ___ | ___ |
| `korean_response_quality` (3축 0-8) | ___ | ___ |
| `session_cost_per_1K_tokens_approx` ($) | ___ | N/A |

> `session_cost_per_1K_tokens_approx`: Live API 토큰 수는 문자 수 기반 근사치(0.6 tokens/char, **오차 ±40%**). Live API 호출은 Billing Export에서도 개별 분리가 어려워 X3 대조에 한계가 있음. 결과 보고 시 "추정치(±40%)" 명시 필수.

---

### TEST-C9: Agent Engine — 배포 + 툴 호출 + 세션 스토리지 *(신규)*

> Agent Engine은 LangChain/LlamaIndex 에이전트를 Vertex AI에 배포하고 세션 스토리지/툴체인을 관리하는 서비스. Live API와 별개 축.

```python
# Agent Engine은 현재 REST API / google-cloud-aiplatform SDK 경유 배포
# vertexai.preview.reasoning_engines는 deprecated — REST API로 직접 호출
from google.cloud import aiplatform
import requests, time
import google.auth
import google.auth.transport.requests

project  = "ml-api-test-vertex"
location = "us-central1"
parent   = f"projects/{project}/locations/{location}"

# ── OAuth 토큰 획득 (google.auth ADC 방식) ──────────────────────────
def get_access_token() -> str:
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token

headers = {
    "Authorization": f"Bearer {get_access_token()}",
    "Content-Type": "application/json"
}

# ⚠ Agent Engine은 현재 v1beta1에서만 제공 (v1 미지원).
# 1.4의 "api_version v1 권장"은 genai SDK 대상이며, Agent Engine REST는 예외.
# GA 전환 시 v1 엔드포인트로 교체 필요.
AGENT_ENGINE_BASE = f"https://{location}-aiplatform.googleapis.com/v1beta1/{parent}/reasoningEngines"

# 세션 생성 + 툴 호출 검증
queries_ko = [
    "GraphRAG에서 커뮤니티 탐지 결과를 검색에 어떻게 쓰나?",
    "앞서 말한 방법을 이력서 매칭에 적용하면?",  # 세션 컨텍스트 유지 확인
]
```

> ⚠ **Appendix C9-PoC 참고**: Week 5 착수 전 아래 최소 PoC 스크립트로 배포/호출 플로우를 사전 검증 권장.

**Appendix C9-PoC: Agent Engine 최소 동작 검증 스크립트**

> **사전 준비**: PoC 실행 전 `poc_agent.pkl` 파일을 생성해 GCS에 업로드해야 함.
> ```python
> # create_poc_agent.py — pickle 파일 생성
> import pickle
> from google.cloud import storage
>
> class PocAgent:
>     """Agent Engine에 배포할 최소 에이전트. query() 메서드만 구현."""
>     def query(self, input: dict) -> dict:
>         return {"output": f"Echo: {input.get('text', '')}"}
>
> # pickle 직렬화 → GCS 업로드
> agent = PocAgent()
> blob = storage.Client().bucket("ml-api-test-vertex").blob("agents/poc_agent.pkl")
> blob.upload_from_string(pickle.dumps(agent))
> print("Uploaded gs://ml-api-test-vertex/agents/poc_agent.pkl")
> ```

```python
# appendix_c9_poc.py — Week 5 이전 로컬에서 실행해 배포/호출 플로우 확인
# 목적: REST URL/토큰/리소스명 매핑을 Week 5 시작 전에 확정
import requests, time, json
import google.auth, google.auth.transport.requests

project  = "ml-api-test-vertex"
location = "us-central1"
BASE     = f"https://{location}-aiplatform.googleapis.com/v1beta1"
PARENT   = f"projects/{project}/locations/{location}"

def token():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token

H = lambda: {"Authorization": f"Bearer {token()}", "Content-Type": "application/json"}

# Step 1: 에이전트 배포 (LRO — polling 필요)
deploy_resp = requests.post(
    f"{BASE}/{PARENT}/reasoningEngines",
    headers=H(),
    json={
        "display_name": "poc-c9-agent",
        "reasoning_engine_spec": {
            "package_spec": {
                "python_version": "3.11",
                "pickle_object_gcs_uri": "gs://ml-api-test-vertex/agents/poc_agent.pkl",
                "requirements": ["google-cloud-aiplatform[langchain]>=1.74.0"]
            },
            "class_methods": [{"name": "query"}]
        }
    }
)
lro = deploy_resp.json()
print("Deploy LRO:", lro.get("name"))

# LRO polling
op_name = lro["name"]
for _ in range(30):
    op = requests.get(f"{BASE}/{op_name}", headers=H()).json()
    if op.get("done"):
        engine_name = op["response"]["name"]
        print("Engine:", engine_name)
        break
    time.sleep(10)

# Step 2: 세션 생성 (툴 호출 검증 대상)
sess_resp = requests.post(
    f"{BASE}/{engine_name}:createSession",
    headers=H(),
    json={"user_id": "test-ko-1"}
)
session_id = sess_resp.json().get("id")
print("Session:", session_id)

# Step 3: 의도적 툴 호출 쿼리 (RAG retrieval 툴이 등록된 에이전트 전제)
# 툴이 호출되지 않으면 tool_call_success_rate=0% → 에이전트 설계 재검토 필요
query_resp = requests.post(
    f"{BASE}/{engine_name}:query",
    headers=H(),
    json={
        "session_id": session_id,
        "input": {"text": "최근 AI 스타트업 채용 공고 3개를 검색해줘."}  # 반드시 툴 호출 유도
    }
)
result = query_resp.json()
print("Response:", json.dumps(result, ensure_ascii=False, indent=2))

# Step 4: 삭제
requests.delete(f"{BASE}/{engine_name}", headers=H())
print("Deleted.")
```

**측정 지표**:

| 지표 | 값 |
|------|---|
| `deploy_time` (sec) | ___ |
| `first_query_latency_us` (ms) | ___ |
| `first_query_latency_kr` (ms) | ___ |
| `subsequent_query_latency` (ms) | ___ |
| `session_context_maintained` (bool) | ___ |
| `tool_call_success_rate` (%) | ___ |
| `korean_response_quality` (3축 0-8) | ___ |
| `cost_per_query` ($) | ___ |

---

### TEST-C10: Prompt Caching *(신규)*

> **GraphRAG 운영 비용 절감 검증.** 긴 시스템 프롬프트(그래프 스키마, 툴 스키마)를 반복 사용하는 워크로드에서 Cached input 단가로 비용 절감 효과 측정.

| 항목 | 내용 |
|------|------|
| **모델** | Gemini 2.5 Flash |
| **캐시 대상** | 시스템 프롬프트 (GraphRAG 스키마 + 툴 정의, ~5K tokens) |
| **반복 횟수** | 100회 (캐시 ON vs OFF 비교) |

```python
import google.genai as genai
from google.genai import types

import time  # C10에서 perf_counter 사용

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")

SYSTEM_PROMPT = open("prompts/graphrag_system_5k.txt").read()  # ~5K tokens

# 캐시 생성
cache = client.caches.create(
    model="gemini-2.5-flash",
    config=types.CreateCachedContentConfig(
        # system_instruction에 긴 시스템 프롬프트를 캐시 (contents와 분리)
        system_instruction=SYSTEM_PROMPT,
        # contents: 캐시할 few-shot 예시나 컨텍스트 문서가 있으면 여기에 추가
        # 시스템 프롬프트만 캐시할 경우 contents는 비워도 됨
        ttl="3600s",
        display_name="test-c10-graphrag-cache"
    )
)

queries_ko = [f"후보자 {i}번의 경력과 기업 A의 요구사항을 매칭해줘." for i in range(100)]

# 캐시 ON
costs_cached, latencies_cached = [], []
for query in queries_ko:
    start = time.perf_counter()
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=query,
        config=types.GenerateContentConfig(
            cached_content=cache.name,
            max_output_tokens=512
        )
    )
    latencies_cached.append((time.perf_counter() - start) * 1000)
    # cached_input_tokens은 캐시 단가로 과금
    log_api_call("test-c10-cached", "gemini-2.5-flash",
                 resp.usage_metadata.prompt_token_count,
                 resp.usage_metadata.candidates_token_count,
                 latencies_cached[-1])

# 캐시 OFF (동일 프롬프트 매번 포함)
costs_uncached, latencies_uncached = [], []
for query in queries_ko:
    start = time.perf_counter()
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{SYSTEM_PROMPT}\n\n{query}",
        config=types.GenerateContentConfig(max_output_tokens=512)
    )
    latencies_uncached.append((time.perf_counter() - start) * 1000)
    log_api_call("test-c10-uncached", "gemini-2.5-flash",
                 resp.usage_metadata.prompt_token_count,
                 resp.usage_metadata.candidates_token_count,
                 latencies_uncached[-1])

# 캐시 삭제
client.caches.delete(name=cache.name)
```

**측정 지표**:

| 지표 | 캐시 ON | 캐시 OFF |
|------|--------|--------|
| `latency_p50` (ms) | ___ | ___ |
| `latency_p99` (ms) | ___ | ___ |
| `cost_100_queries` ($) | ___ | ___ |
| `cost_saving_rate` (%) | ___ | — |
| `cache_hit_rate` (%) | ___ | N/A |

**Pass/Fail 기준**: 캐시 ON 비용 절감 ≥ 30% (GraphRAG 운영 채택 기준)

---

## 6. Cross-Cutting 테스트

### TEST-X1: API 에러 핸들링 + Quota 초과 동작

| 시나리오 | 방법 | 기대 응답 |
|---------|------|----------|
| Quota 초과 (RPM) | 1초에 100회 연속 호출 | HTTP 429 + `Retry-After` 헤더 |
| 잘못된 모델 ID | 존재하지 않는 모델 | HTTP 404 |
| 인증 실패 | 만료된 토큰 | HTTP 401 |
| 잘못된 입력 스키마 | 필수 필드 누락 | HTTP 400 + 필드 에러 |
| Region 미지원 | TPU를 미지원 region | HTTP 400 + region 안내 |

---

### TEST-X2: SDK vs REST API 일관성

| Part | SDK | REST |
|------|-----|------|
| A | `Model.upload()` | `POST .../models:upload` |
| B | `CustomTrainingJob.run()` | `POST .../customJobs` |
| C | `client.models.generate_content()` | `POST .../models/{id}:generateContent` |

검증: 동일 결과, 에러 매핑, latency overhead, label 전달 정확성

---

### TEST-X3: Billing 정확성

```sql
-- Cloud Logging 기반 API 호출 비용
SELECT test_id, model_id,
       SUM(prompt_tokens) as total_input_tokens,
       SUM(output_tokens) as total_output_tokens
FROM `project.dataset.vertex_test_cost_tracker`
GROUP BY test_id, model_id
ORDER BY total_input_tokens DESC;

-- Billing Export 기반 리소스 비용
SELECT labels.value as test_id, service.description,
       SUM(cost) as total_cost
FROM `project.dataset.gcp_billing_export_v1_*`
WHERE labels.key = "test-id"
GROUP BY labels.value, service.description
ORDER BY total_cost DESC;
```

최종 비용 = Cloud Logging 집계(API 호출) + Billing Export(리소스) 합산.

```sql
-- 합산 비용 뷰: Cloud Logging(API 호출) + Billing Export(리소스) 조인
WITH api_costs AS (
    SELECT test_id,
           SUM(prompt_tokens / sampling_rate) * unit_price_input  AS api_input_cost,
           SUM(output_tokens / sampling_rate) * unit_price_output AS api_output_cost
    FROM `project.dataset.vertex_test_cost_tracker` t
    JOIN `project.dataset.model_pricing` p ON t.model_id = p.model_id
    GROUP BY test_id
),
resource_costs AS (
    SELECT labels.value AS test_id,
           SUM(cost) AS resource_cost
    FROM `project.dataset.gcp_billing_export_v1_*`
    WHERE labels.key = "test-id"
    GROUP BY labels.value
)
SELECT COALESCE(a.test_id, r.test_id) AS test_id,
       IFNULL(a.api_input_cost, 0) + IFNULL(a.api_output_cost, 0) AS api_cost,
       IFNULL(r.resource_cost, 0) AS resource_cost,
       IFNULL(a.api_input_cost, 0) + IFNULL(a.api_output_cost, 0)
         + IFNULL(r.resource_cost, 0) AS total_cost
FROM api_costs a
FULL OUTER JOIN resource_costs r ON a.test_id = r.test_id
ORDER BY total_cost DESC;
```

---

## 7. 결과 종합 매트릭스

### 7.1 Part A

| 테스트 | 핵심 결과 | 비용 | 판단 |
|--------|---------|------|------|
| A1: AutoML Tabular | AU-PRC=___ | $___/hr | ○/△/× |
| A2: AutoML Image | Acc=___, P99=___ms | $___/hr | ○/△/× |
| A3: Feature Store | P99=___ms, maxQPS=___ | $___/hr/node | ○/△/× |
| A4: Model Registry | Deploy=___s | — | ○/△/× |
| A5: Batch Prediction | ___rows/s | $___/1M rows | ○/△/× |

### 7.2 Part B

| 테스트 | 핵심 결과 | 비용 | 판단 |
|--------|---------|------|------|
| B1: GPU 학습 | T4:___m, A100:___m | T4:$__, A100:$__ | ○/△/× |
| B2: TPU 학습 | ___min, sparse=___% | $___ | ○/△/× |
| B3: Kubeflow Pipeline | E2E=___min | $___/run | ○/△/× |
| B4: HPT (Vizier) | Best MRR=___ | $___/20 trials | ○/△/× |
| B5: 분산 학습 | Efficiency=___% | $___ | ○/△/× |
| B6: KGE 서빙 | p99=___ms | $___/hr | ○/△/× |

### 7.3 Part C

| 테스트 | 핵심 결과 (KO) | US 비용 | KR latency | 판단 |
|--------|--------------|---------|-----------|------|
| C1: Gemini API | TTFT=___ms, KO=___ | $___/1M | +___ms | ○/△/× |
| C2: Embeddings | ___docs/min, KO nDCG=___ | $___/500K | N/A | ○/△/× |
| C3: SFT | ROUGE-KO Δ=+___ | $___/ep | N/A | ○/△/× |
| C4: LoRA | ROUGE-KO=___ | $___/run | N/A | ○/△/× |
| C5: RAG Engine | KO Recall@5=___ | $___/mo | +___ms | ○/△/× |
| C6: Grounding | KO Acc Δ=+___% | $___/1K | N/A | ○/△/× |
| C7: Model Garden | latency=___ms, KO=___ | $___/1M | N/A | ○/△/× |
| C8: Live API | TTFT=___ms, KO=___ | $___/1K | +___ms | ○/△/× |
| C9: Agent Engine | SessionOK, KO=___ | $___/q | +___ms | ○/△/× |
| C10: Prompt Caching | 절감=___% | $___ | N/A | ○/△/× |

---

## 8. 일정 및 리소스

### 8.1 실행 일정

```
Week 1: 환경 구성 + Part A
  ├── Day 1: GCP 설정, Quota 확인, PSC 체크리스트(A3), 데이터셋 업로드
  ├── Day 2: TEST-A1 (AutoML Tabular 3구간)
  ├── Day 3: TEST-A2 + TEST-A3 (PSC 사전 준비 완료 후)
  ├── Day 4: TEST-A4 + TEST-A5
  └── Day 5: Part A 결과 정리 + B2 TPU PoC 시작
             (XLA 환경 구성, kge-trainer-tpu 컨테이너 빌드)

Week 2: Part B — GPU + Pipeline
  ├── Day 1: TEST-B1 (T4 3회, A100 제출)
  ├── Day 2: TEST-B1 (A100 3회 완료) + TEST-B3 착수
  ├── Day 3: TEST-B1 (H100 3회) + TEST-B3 완료
  ├── Day 4: TEST-B4 (HPT 20 trials, ~4~6시간) + TEST-B5 착수
  └── Day 5: TEST-B5 완료 + TEST-B6 (KGE 서빙)

Week 3: Part B — TPU 전용 스프린트
  ├── Day 1: TPU XLA 컨테이너 검증 + 첫 실행 시도
  ├── Day 2: XLA 에러 디버깅 (DataLoader, optimizer_step, mark_step)
  ├── Day 3: TEST-B2 3회 반복
  ├── Day 4: 코드 변경 난이도 정리 + GPU vs TPU 비교
  └── Day 5: Part B 전체 결과 정리
             (3일 내 XLA 미해결 시 스킵, "TPU 진입 장벽" 문서화)

Week 4: Part C — LLM (us-central1)
  ├── Day 1: TEST-C1 (Gemini API, 영어/한국어 쌍, 스트리밍 ttft 측정)
  ├── Day 2: TEST-C2 (dim_sweep 10K → 본 테스트 500K, 동적 배치)
             + TEST-C6 (Grounding)
  ├── Day 3: TEST-C3 (SFT epoch별 순차) + TEST-C4 (LoRA Gemma)
  ├── Day 4: TEST-C5 (RAG Engine, chunking sweep → 본 테스트)
  └── Day 5: TEST-C7 (Model Garden) + TEST-C10 (Prompt Caching)

Week 5: Part C — 한국 리전 + Agent + Cross-Cutting
  ├── Day 1: TEST-C1/C5 asia-northeast3 latency 측정
             + TEST-C8 (Live API, US + KR)
  ├── Day 2: TEST-C9 (Agent Engine, US + KR — PoC 선행 필수)
             + TEST-X1 (에러 핸들링)
  ├── Day 3: TEST-X2 (SDK vs REST) + TEST-X3 Billing 쿼리
             + 48시간 모니터링 시작
  ├── Day 4: 한국어 수동 평가 (3축, C3/C5/C7/C8/C9 — 평가자 2인)
  └── Day 5: 결과 종합 매트릭스 + 최종 보고서 + 리소스 전체 삭제
             (2.5 삭제 체크리스트 전 항목 확인)
```

### 8.2 비용 예산

| Part | 주요 항목 | 보수적 추정 |
|------|---------|-----------|
| **A** | AutoML, Feature Store, Endpoint | $300~$500 |
| **B** | H100 3회×$12.47/hr×3hr + A100/T4 + TPU + HPT + 디버깅 재실행 | $1,200~$2,000 |
| **C** | Gemini API(영어+한국어 쌍), SFT $15/ep×6, RAG Spanner, Embedding 500K, Caching 테스트, asia-northeast3 | $600~$900 |
| **X** | Cross-cutting, Billing 검증 | $50~$100 |
| **인프라** | GCS, Registry, Firestore, Cloud Logging, 네트워크 | $100~$150 |
| **합계** | | **$2,250~$3,650** |

Budget Alert: $4,000 경고 / $5,000 강제 중단

### 8.3 필요 인력

| 역할 | 인원 | 담당 |
|------|-----|------|
| ML Engineer | 1명 | Part A + B (Training, Pipeline, TPU PoC) |
| LLM Engineer | 1명 | Part C (Gemini, RAG, SFT, Agent, Caching) |
| Platform Engineer | 1명 | 환경 구성, Cloud Logging 비용 추적, Cross-Cutting |
| 한국어 도메인 평가자 | 2명 (파트타임) | 3축 수동 평가, 편차 체크, 한국어 질문셋 작성 |

### 8.4 리스크 및 완화

| 리스크 | 영향 | 완화 |
|--------|------|------|
| GPU/TPU Quota 부족 | Part B 지연 | 2주 전 신청. H100 불가 시 A100 ×2 대체 |
| TPU XLA 디버깅 장기화 | Week 3 초과 | Week 1 PoC 선행. 3일 내 미해결 시 스킵 |
| Feature Store PSC 설정 지연 | A3 실행 불가 | Week 1 Day 1에 PSC 설정 우선 확인 |
| Feature Store IndexConfig API 변경 | A3 벡터 검색 실패 | 실행 전 `help(IndexConfig)` 파라미터 확인 |
| SFT Quota (1 concurrent) | Part C 지연 | epoch별 순차 실행, Quota 증가 사전 요청 |
| RAG Spanner 비용 초과 | 예산 이탈 | BASIC tier 우선, SCALED는 C5 전용, 완료 즉시 Unprovisioned |
| 한국어 평가자 일정 충돌 | 수동 평가 지연 | Week 4 착수 전 2인 일정 확정 |
| Gemini 2.0 계열 retire | 결론 유효기간 단축 | 2.0은 비용 baseline만. 서비스 결론은 2.5 기준 |
| LLM 비용 집계 오류 | Phase 비용 결론 왜곡 | Cloud Logging 병행 추적(1.5) + X3에서 합산 검증 |
| C1 streaming usage_metadata 누락 | 토큰 비용 집계 0 기록 | fallback warning 포함, X3에서 Billing Export 대조 |
| KR probe runner 미배포 | KR latency 미측정 | Week 1에 asia-northeast3 Cloud Run Job 배포 선행 |
| Agent Engine LRO 타임아웃 | C9 배포 실패 | Appendix PoC로 Week 4 이전 플로우 검증 |
| Embedding 토큰 초과(한국어) | API 400 오류 | tokens_per_char=0.6 + embed_with_retry 절반 분할 |