# Vertex AI API 테스트 실행 계획 — ML / Deep Learning / LLM

> 본 문서는 GCP Vertex AI API를 **Traditional ML**, **Deep Learning**, **LLM** 세 가지 측면에서 실측 테스트하여, 현재 ML Pipeline 설계(`designs/`)가 활용할 수 있는 Vertex AI의 실제 성능·비용·운영성을 검증하는 실행 계획입니다.
>
> `compare.md`의 Phase 2(ML 컴퓨팅)를 보완하며, Vertex AI API 고유 기능의 깊이 있는 평가에 초점을 맞춥니다.

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
                    ┌─────────────────────────────────────────────────┐
                    │              Vertex AI API 테스트 범위            │
                    ├────────────────┬────────────────┬───────────────┤
                    │  Part A: ML    │  Part B: DL    │  Part C: LLM  │
                    ├────────────────┼────────────────┼───────────────┤
                    │ AutoML         │ Custom Train   │ Gemini API    │
                    │ Feature Store  │ Kubeflow Pipes │ Embeddings    │
                    │ Model Registry │ HPT (Vizier)   │ Fine-Tuning   │
                    │ Batch Predict  │ GPU/TPU 학습    │ RAG Engine    │
                    │ Online Predict │ Distributed    │ Grounding     │
                    │                │                │ Model Garden  │
                    │                │                │ Agent Engine  │
                    └────────────────┴────────────────┴───────────────┘
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

1. **API-First**: SDK wrapper가 아닌 REST API 직접 호출 테스트를 병행하여 SDK 추상화 이면의 실제 동작 확인
2. **실측 비용 태깅**: 모든 API 호출에 `labels.test-id` 부착 → Billing Export로 정확한 비용 추적
3. **재현성**: 모든 테스트를 Python 스크립트 + YAML config로 정의하여 반복 실행 가능
4. **3회 반복**: 정량 테스트는 최소 3회 반복, 중간값(median) 기준
5. **Quota 사전 확보**: GPU/TPU quota 증가 요청은 테스트 2주 전 완료

### 1.4 SDK 버전 주의사항

```
# 2026-03 기준 권장 SDK
google-cloud-aiplatform >= 1.74.0   # Vertex AI SDK
google-genai >= 1.5.0               # GenAI SDK (vertexai.generative_models 대체)
kfp >= 2.10.0                       # Kubeflow Pipelines SDK v2

# ⚠ Deprecated (2026-06-24 제거 예정)
# vertexai.generative_models → google.genai로 마이그레이션 필요
# vertexai.language_models   → google.genai로 마이그레이션 필요
# vertexai.tuning            → google.genai로 마이그레이션 필요
```

---

## 2. 공통 환경 구성

### 2.1 GCP 프로젝트 설정

```
프로젝트: ml-api-test-vertex
리전: us-central1 (TPU v5e/v6e + A100/H100 가용)
Billing: Budget Alert $5,000

사전 Quota 요청:
├── NVIDIA_T4: 4 → 8
├── NVIDIA_A100: 0 → 4
├── NVIDIA_H100: 0 → 2 (Part B 전용)
├── TPU_V5E: 0 → 8 chips (Part B 전용)
├── Custom Training concurrent jobs: 2 → 10
├── Pipeline concurrent runs: 10 → 50
├── Online prediction QPS: 기본 → 필요 시 증가
└── Tuning concurrent jobs: 1 → 3 (Part C 전용)
```

### 2.2 데이터셋 준비

| ID | 용도 | 형태 | 크기 | Part |
|----|------|------|------|------|
| `DS-TAB` | Tabular ML | CSV (structured features) | 500MB, 1M rows | A |
| `DS-IMG` | Image Classification | JPEG (224×224) + labels | 2GB, 50K images | A |
| `DS-TXT-CORPUS` | Text Corpus (Graph/RAG) | JSONL (텍스트 코퍼스) | 5GB, 500K docs | A, B |
| `DS-KGE` | Knowledge Graph Triples | TSV (head, relation, tail) | 1GB, 10M triples | B |
| `DS-LLM-SFT` | SFT Training Data | JSONL (instruction/response) | 50MB, 10K examples | C |
| `DS-LLM-EVAL` | LLM Evaluation Set | JSONL (question/reference) | 5MB, 1K examples | C |
| `DS-RAG-DOCS` | RAG 문서 컬렉션 | PDF + TXT (기술 문서) | 500MB, 2K documents | C |

### 2.3 공통 인프라

```yaml
# GCS 버킷 구조
gs://ml-api-test-vertex/
├── datasets/          # 위 데이터셋 저장
├── pipeline-root/     # Kubeflow Pipeline 루트
├── models/            # 학습된 모델 아티팩트
├── predictions/       # 추론 결과
├── configs/           # 테스트 설정 파일
└── results/           # 테스트 결과 로그

# Artifact Registry
us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/
├── preprocess:latest
├── kge-trainer:latest
├── llm-trainer:latest
└── batch-predictor:latest

# 네트워크
VPC: default (Vertex AI 서비스 기본 연결)
Private Google Access: enabled
```

---

## 3. Part A — Traditional ML

> **목적**: Vertex AI의 코드 최소 ML(AutoML) 및 관리형 ML 서비스(Feature Store, Model Registry, Prediction)의 실용성 검증

---

### TEST-A1: AutoML Tabular — 학습 + 평가 + 배포

**목적**: 코드 없이 정형 데이터로 분류/회귀 모델을 학습하고, 수동 커스텀 모델 대비 품질·비용·시간 비교

| 항목 | 내용 |
|------|------|
| **데이터셋** | `DS-TAB` (1M rows, 50 features, binary classification) |
| **API** | `aiplatform.AutoMLTabularTrainingJob` |
| **학습 시간 예산** | 1시간, 4시간, 8시간 (3단계 비교) |
| **반복** | 각 예산 1회 (AutoML 내부에서 다수 trial 실행) |

**실행 코드 (SDK)**:
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
    budget_milli_node_hours=1000,  # 1hr = 1000 milli-node-hours
)
```

**실행 코드 (REST API 직접 호출)**:
```bash
curl -X POST \
  "https://us-central1-aiplatform.googleapis.com/v1/projects/ml-api-test-vertex/locations/us-central1/trainingPipelines" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "test-a1-automl-rest",
    "labels": {"test-id": "test-a1"},
    "trainingTaskDefinition": "gs://google-cloud-aiplatform/schema/trainingjob/definition/automl_tabular_1.0.0.yaml",
    "trainingTaskInputs": {
      "targetColumn": "target",
      "predictionType": "classification",
      "trainBudgetMilliNodeHours": 1000,
      "optimizationObjective": "maximize-au-prc"
    },
    "inputDataConfig": {
      "datasetId": "<DATASET_ID>",
      "fractionSplit": {"trainingFraction": 0.8, "validationFraction": 0.1, "testFraction": 0.1}
    },
    "modelToUpload": {"displayName": "test-a1-model-rest"}
  }'
```

**측정 지표**:

| 지표 | 설명 | 수집 방법 |
|------|------|----------|
| `train_wall_time` | 학습 시작~완료 총 시간 | TrainingPipeline state 변경 시간차 |
| `au_prc` | 테스트셋 AU-PRC | Model Evaluation API |
| `au_roc` | 테스트셋 AU-ROC | Model Evaluation API |
| `log_loss` | 테스트셋 Log Loss | Model Evaluation API |
| `feature_importance` | 상위 10 피처 중요도 | Model Evaluation API |
| `cost` | 총 학습 비용 ($) | Billing Export (label filter) |
| `model_size_mb` | 모델 아티팩트 크기 | GCS 확인 |

**Baseline 비교**: 동일 데이터에 대해 XGBoost 수동 학습 (Custom Training Job, TEST-B1에서 수행) 결과와 비교

**Pass/Fail 기준**:
- AutoML AU-PRC ≥ 수동 XGBoost AU-PRC × 0.95 → AutoML 품질 수용 가능
- 1시간 예산에서 AU-PRC ≥ 0.80 → 최소 품질 달성
- 비용: $21.25/hr × 예산 시간 내 → 예산 초과 여부

---

### TEST-A2: AutoML Image Classification

**목적**: 이미지 데이터에 대한 AutoML 학습·배포·온라인 추론 E2E 검증

| 항목 | 내용 |
|------|------|
| **데이터셋** | `DS-IMG` (50K images, 10 classes) |
| **API** | `aiplatform.AutoMLImageTrainingJob` |
| **학습 시간** | 8 node-hours |
| **배포** | Online Endpoint (`n1-standard-4`, min replicas=1) |

**실행 단계**:
1. `ImageDataset.create()` — import schema: `gs://google-cloud-aiplatform/schema/dataset/ioformat/image_classification_single_label_io_format_1.0.0.yaml`
2. `AutoMLImageTrainingJob.run()` — 8 node-hours
3. `model.deploy()` — Online Endpoint 생성
4. 100장의 테스트 이미지로 Online Prediction 호출 → latency + accuracy 측정
5. Endpoint 삭제

**측정 지표**:

| 지표 | 설명 |
|------|------|
| `accuracy` | Top-1 accuracy on test set |
| `prediction_latency_p50` | 온라인 추론 p50 latency (ms) |
| `prediction_latency_p99` | 온라인 추론 p99 latency (ms) |
| `cold_start_time` | Endpoint 생성~첫 번째 요청 응답까지 시간 |
| `train_cost` | 학습 비용 ($3.465/node-hr × 8hr) |
| `serve_cost_per_hr` | 서빙 비용 ($/hr) |

---

### TEST-A3: Feature Store v2 (BigQuery-Powered)

**목적**: Feature Store의 온라인 서빙 latency와 벡터 검색 성능 검증

| 항목 | 내용 |
|------|------|
| **데이터** | `DS-TAB`에서 추출한 50개 피처, 1M entities |
| **온라인 스토어** | Bigtable 백엔드 + Optimized 백엔드 (둘 다 테스트) |

**실행 코드**:
```python
from google.cloud.aiplatform import feature_store

# Bigtable 백엔드
bt_store = feature_store.FeatureOnlineStore.create_bigtable_store(
    feature_online_store_id="test-a3-bigtable",
    labels={"test-id": "test-a3"}
)

# Optimized 백엔드 (벡터 검색용)
opt_store = feature_store.FeatureOnlineStore.create_optimized_store(
    feature_online_store_id="test-a3-optimized",
    labels={"test-id": "test-a3"}
)

# FeatureView 생성 + 동기화
view = bt_store.create_feature_view(
    feature_view_id="user-features",
    source=feature_store.utils.FeatureViewBigQuerySource(
        uri="bq://project.dataset.feature_table",
        entity_id_columns=["user_id"]
    )
)

# 온라인 서빙
result = view.fetch_feature_values(id="user_12345")

# 벡터 검색 (Optimized 전용)
results = opt_view.search_nearest_entities(
    embedding=[0.1, 0.2, ...],  # 768-dim
    neighbor_count=10
)
```

**측정 지표**:

| 지표 | Bigtable | Optimized |
|------|----------|-----------|
| `fetch_latency_p50` (ms) | ___ | ___ |
| `fetch_latency_p99` (ms) | ___ | ___ |
| `vector_search_latency_p50` (ms) | N/A | ___ |
| `vector_search_latency_p99` (ms) | N/A | ___ |
| `sync_time` (1M entities) | ___ | ___ |
| `cost_per_hr` | $0.94/node | $0.30/node |
| `max_qps_per_node` | ~15,000 | 측정 |

**부하 테스트**: Locust 또는 k6로 초당 1,000 → 5,000 → 10,000 요청 부하 인가

---

### TEST-A4: Model Registry 생명주기

**목적**: 모델 업로드 → 버전 관리 → Alias 지정 → 배포 → 삭제 전체 생명주기 API 검증

**실행 단계**:
```python
# 1. 모델 업로드 (v1)
model_v1 = aiplatform.Model.upload(
    display_name="test-a4-model",
    artifact_uri="gs://ml-api-test-vertex/models/xgboost-v1/",
    serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-7:latest",
    labels={"test-id": "test-a4"}
)

# 2. 모델 업로드 (v2 — 같은 display_name, parent_model 지정)
model_v2 = aiplatform.Model.upload(
    display_name="test-a4-model",
    parent_model=model_v1.resource_name,
    artifact_uri="gs://ml-api-test-vertex/models/xgboost-v2/",
    serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-7:latest",
    labels={"test-id": "test-a4"}
)

# 3. Alias 관리
registry = aiplatform.models.ModelRegistry(model=model_v1.resource_name)
registry.add_version_aliases(["champion"], version=model_v1.version_id)
registry.add_version_aliases(["challenger"], version=model_v2.version_id)

# 4. Alias로 배포
champion = registry.get_model(alias="champion")
endpoint = champion.deploy(
    machine_type="n1-standard-4",
    min_replica_count=1,
    max_replica_count=3,
    labels={"test-id": "test-a4"}
)

# 5. Champion ↔ Challenger 교체
registry.remove_version_aliases(["champion"], version=model_v1.version_id)
registry.add_version_aliases(["champion"], version=model_v2.version_id)

# 6. Prediction 동작 확인 (새 champion)
prediction = endpoint.predict(instances=[{"feature_1": 1.0, "feature_2": "A"}])

# 7. 정리
endpoint.undeploy_all()
endpoint.delete()
```

**측정 지표**:

| 지표 | 설명 |
|------|------|
| `upload_time` | 모델 업로드 소요 시간 (s) |
| `deploy_time` | Endpoint 배포 완료 시간 (s) |
| `alias_switch_time` | Alias 교체 소요 시간 (s) — 무중단 여부 확인 |
| `version_count` | 등록된 버전 수 확인 |
| `list_versions_latency` | 버전 목록 조회 latency (ms) |

**설계 문서 매핑**: `C4_Component_Layer_VXP.md`의 `Model Registry Integrator`가 이 API를 사용

---

### TEST-A5: Batch Prediction

**목적**: 대규모 오프라인 추론의 처리량·비용·소요 시간 검증

| 항목 | 내용 |
|------|------|
| **모델** | TEST-A1에서 학습한 AutoML Tabular 모델 |
| **데이터** | `DS-TAB` 전체 (1M rows) |
| **머신** | `n1-standard-8` × 1, × 4 (스케일 비교) |

**실행 코드**:
```python
batch_job = model.batch_predict(
    job_display_name="test-a5-batch",
    gcs_source="gs://ml-api-test-vertex/datasets/DS-TAB/predict_input.jsonl",
    gcs_destination_prefix="gs://ml-api-test-vertex/predictions/test-a5/",
    machine_type="n1-standard-8",
    starting_replica_count=1,       # 1대 vs 4대
    max_replica_count=1,
    labels={"test-id": "test-a5"}
)
batch_job.wait()
```

**측정 지표**:

| 지표 | 1 replica | 4 replicas |
|------|-----------|------------|
| `total_time` (min) | ___ | ___ |
| `throughput` (rows/sec) | ___ | ___ |
| `cost` ($) | ___ | ___ |
| `cost_per_1M_rows` ($) | ___ | ___ |
| `output_size` (MB) | ___ | ___ |

---

## 4. Part B — Deep Learning

> **목적**: Vertex AI의 Custom Training, GPU/TPU 학습, Kubeflow Pipeline 오케스트레이션, 하이퍼파라미터 튜닝 성능 검증.
> 설계 문서의 Preprocess / Train / Infer Pipeline 구조를 실제 API로 구현·실행합니다.

---

### TEST-B1: Custom Training Job — GPU 학습 (KGE 모델)

**목적**: 현재 설계의 Train Pipeline에 해당하는 KGE 모델 학습을 GPU 스펙별로 비교

| 항목 | 내용 |
|------|------|
| **모델** | TransE (Knowledge Graph Embedding), PyTorch |
| **데이터셋** | `DS-KGE` (10M triples) |
| **GPU 구성** | ① T4 ×1, ② A100-40GB ×1, ③ H100 ×1 |
| **반복** | 각 구성 3회 |

**실행 코드 (SDK)**:
```python
job = aiplatform.CustomContainerTrainingJob(
    display_name="test-b1-kge-t4",
    container_uri="us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/kge-trainer:latest",
    labels={"test-id": "test-b1", "gpu": "t4"}
)

model = job.run(
    args=[
        "--data_path=gs://ml-api-test-vertex/datasets/DS-KGE/",
        "--epochs=50",
        "--embedding_dim=256",
        "--batch_size=4096",
        "--lr=0.001"
    ],
    machine_type="n1-standard-8",
    accelerator_type="NVIDIA_TESLA_T4",
    accelerator_count=1,
    replica_count=1,
    model_display_name="test-b1-kge-model",
    model_serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/pytorch-gpu.2-0:latest"
)
```

**실행 코드 (REST API 직접 호출)**:
```bash
curl -X POST \
  "https://us-central1-aiplatform.googleapis.com/v1/projects/ml-api-test-vertex/locations/us-central1/customJobs" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "test-b1-kge-a100-rest",
    "labels": {"test-id": "test-b1", "gpu": "a100"},
    "jobSpec": {
      "workerPoolSpecs": [{
        "machineSpec": {
          "machineType": "a2-highgpu-1g",
          "acceleratorType": "NVIDIA_TESLA_A100",
          "acceleratorCount": 1
        },
        "replicaCount": 1,
        "containerSpec": {
          "imageUri": "us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/kge-trainer:latest",
          "args": ["--epochs=50", "--embedding_dim=256", "--batch_size=4096"]
        },
        "diskSpec": {"bootDiskType": "pd-ssd", "bootDiskSizeGb": 100}
      }]
    }
  }'
```

**측정 지표**:

| 지표 | T4 ×1 | A100 ×1 | H100 ×1 |
|------|-------|---------|---------|
| `train_time` (min) | ___ | ___ | ___ |
| `epoch_time` (sec) | ___ | ___ | ___ |
| `final_mrr` (Mean Reciprocal Rank) | ___ | ___ | ___ |
| `final_hits@10` | ___ | ___ | ___ |
| `gpu_util_avg` (%) | ___ | ___ | ___ |
| `gpu_mem_peak` (GB) | ___ | ___ | ___ |
| `cost_total` ($) | ___ | ___ | ___ |
| `cost_per_epoch` ($) | ___ | ___ | ___ |
| `cold_start` (sec) | ___ | ___ | ___ |

**비용 참고 (on-demand, us-central1)**:
```
T4 ×1  (n1-standard-8): $0.2185 + $0.40 = $0.6185/hr
A100 ×1 (a2-highgpu-1g):              ≈ $3.67/hr
H100 ×1 (a3-highgpu-1g):              ≈ $12.47/hr
```

**Pass/Fail 기준**:
- A100이 T4 대비 학습 시간 3× 이상 빠르면 "A100 가성비 우수" 판단
- 3회 반복 간 학습 시간 표준편차 < 10% → "안정적 성능"
- Cold start (Job 생성~학습 시작) < 5분

---

### TEST-B2: Custom Training Job — TPU 학습

**목적**: TPU v5e에서의 KGE/Embedding 학습. GPU 대비 성능·비용 비교 + PyTorch XLA 코드 변경 난이도 평가

| 항목 | 내용 |
|------|------|
| **모델** | TransE (동일), PyTorch XLA로 변환 |
| **데이터셋** | `DS-KGE` (10M triples) |
| **TPU 구성** | TPU v5e 4 chips (`ct5lp-hightpu-4t`) |
| **반복** | 3회 |

**실행 코드**:
```python
job = aiplatform.CustomContainerTrainingJob(
    display_name="test-b2-kge-tpu-v5e",
    container_uri="us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/kge-trainer-tpu:latest",
    labels={"test-id": "test-b2", "accel": "tpu-v5e"}
)

model = job.run(
    args=[
        "--data_path=gs://ml-api-test-vertex/datasets/DS-KGE/",
        "--epochs=50",
        "--embedding_dim=256",
        "--batch_size=16384",  # TPU에서는 큰 배치 유리
        "--use_tpu=true"
    ],
    machine_type="ct5lp-hightpu-4t",
    replica_count=1,  # TPU는 단일 워커풀, 단일 레플리카만 지원
    model_display_name="test-b2-kge-tpu-model"
)
```

**코드 변경 난이도 측정**:

| 측정 항목 | 값 |
|----------|---|
| GPU→TPU 코드 변경 라인 수 | ___ lines |
| `torch_xla` import 추가 | ___ lines |
| DataLoader 변경 (xla.MpDeviceLoader) | ___ lines |
| Optimizer 변경 (xm.optimizer_step) | ___ lines |
| 디버깅에 소요된 시간 | ___ hours |
| TPU 전용 에러 해결 횟수 | ___ |

**GPU vs TPU 비교 테이블**:

| 지표 | A100 ×1 (TEST-B1) | TPU v5e ×4 |
|------|-------------------|------------|
| `train_time` (min) | ___ | ___ |
| `cost_total` ($) | ___ | ___ |
| `cost_per_epoch` ($) | ___ | ___ |
| `code_change_effort` (hours) | 0 (baseline) | ___ |

---

### TEST-B3: Kubeflow Pipeline — E2E ML 파이프라인 구성

**목적**: 현재 설계의 Preprocess → Train → Infer 파이프라인을 실제 Kubeflow SDK v2로 구현하고, Pipeline API 동작 검증

**실행 코드**:
```python
from kfp import dsl, compiler
from google_cloud_pipeline_components.v1.custom_job import CustomTrainingJobOp

@dsl.component(base_image="python:3.11", packages_to_install=["pandas", "pyarrow"])
def preprocess(input_uri: str, output_uri: dsl.Output[dsl.Dataset]):
    """Feature Engineering + Data Validation (VXP Preprocess Pipeline 대응)"""
    import pandas as pd
    df = pd.read_parquet(input_uri)
    # Feature engineering...
    df.to_parquet(output_uri.path)

@dsl.component(base_image="python:3.11")
def evaluate(metrics_uri: str, threshold: float) -> bool:
    """Threshold Gating Node (VXP Train Pipeline 대응)"""
    import json
    with open(metrics_uri) as f:
        metrics = json.load(f)
    return metrics["mrr"] >= threshold

@dsl.component(base_image="python:3.11")
def register_model(model_uri: str, passed_gate: bool):
    """Model Registry Integrator (VXP Train Pipeline 대응)"""
    if not passed_gate:
        print("Below threshold — skip registration")
        return
    from google.cloud import aiplatform
    aiplatform.Model.upload(
        display_name="kge-model",
        artifact_uri=model_uri,
        serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/pytorch-gpu.2-0:latest"
    )

@dsl.pipeline(name="test-b3-e2e-pipeline", pipeline_root="gs://ml-api-test-vertex/pipeline-root")
def ml_pipeline(dataset_uri: str, threshold: float = 0.3):
    preprocess_task = preprocess(input_uri=dataset_uri)

    train_task = CustomTrainingJobOp(
        display_name="kge-train",
        worker_pool_specs=[{
            "machineSpec": {"machineType": "n1-standard-8", "acceleratorType": "NVIDIA_TESLA_T4", "acceleratorCount": 1},
            "replicaCount": 1,
            "containerSpec": {
                "imageUri": "us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/kge-trainer:latest",
                "args": ["--data_path", preprocess_task.outputs["output_uri"]]
            }
        }],
        project="ml-api-test-vertex",
        location="us-central1"
    )

    eval_task = evaluate(
        metrics_uri=train_task.outputs["gcs_output_directory"],
        threshold=threshold
    )

    register_model(
        model_uri=train_task.outputs["gcs_output_directory"],
        passed_gate=eval_task.output
    )

# 컴파일 + 제출
compiler.Compiler().compile(ml_pipeline, "pipeline.yaml")

job = aiplatform.PipelineJob(
    display_name="test-b3-e2e",
    template_path="pipeline.yaml",
    pipeline_root="gs://ml-api-test-vertex/pipeline-root",
    parameter_values={"dataset_uri": "gs://ml-api-test-vertex/datasets/DS-KGE/", "threshold": 0.3},
    labels={"test-id": "test-b3"}
)
job.submit()
```

**검증 포인트**:

| 검증 항목 | 설명 |
|----------|------|
| 파이프라인 DAG 정상 실행 | 모든 컴포넌트 SUCCEEDED |
| 데이터 전달 (Output→Input) | GCS URI 전달 정상 동작 |
| 조건부 분기 (Threshold Gate) | threshold 미달 시 register 스킵, 파이프라인 SUCCEEDED |
| Pipeline 상태 변경 알림 | Pub/Sub notification 수신 확인 (설계의 TRG 구독 대응) |
| PipelineJob.cancel() | 실행 중 cancel API 호출 → CANCELLED 상태 전이 |
| 파이프라인 재실행 | 동일 파라미터로 재제출 → 새 run 생성 확인 |

**측정 지표**:

| 지표 | 값 |
|------|---|
| `compile_time` (sec) | ___ |
| `submit_to_running` (sec) | ___ |
| `total_pipeline_time` (min) | ___ |
| `per_component_overhead` (sec) | 컴포넌트 간 전환 시 오버헤드 |
| `cancel_response_time` (sec) | cancel API 호출~CANCELLED까지 |
| `pipeline_run_cost` ($) | $0.03 기본 + 컴퓨트 비용 |

---

### TEST-B4: Hyperparameter Tuning (Vizier)

**목적**: Vertex AI Vizier의 베이지안 최적화로 KGE 모델의 최적 하이퍼파라미터 탐색

| 항목 | 내용 |
|------|------|
| **탐색 공간** | learning_rate (1e-4~1e-1, log), embedding_dim (64~512, int), batch_size (1024~16384, int), margin (0.5~5.0, double) |
| **최대 trial** | 20 |
| **병렬 trial** | 5 |
| **GPU** | T4 ×1 per trial |
| **알고리즘** | Bayesian (Vizier default) vs Random (비교) |

**실행 코드**:
```python
from google.cloud.aiplatform import hyperparameter_tuning as hpt

custom_job = aiplatform.CustomJob(
    display_name="test-b4-hpt-base",
    worker_pool_specs=[{
        "machineSpec": {"machineType": "n1-standard-8", "acceleratorType": "NVIDIA_TESLA_T4", "acceleratorCount": 1},
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
    search_algorithm=None,  # Bayesian
    labels={"test-id": "test-b4"}
)
hp_job.run()
```

**측정 지표**:

| 지표 | Bayesian | Random |
|------|----------|--------|
| `best_mrr` | ___ | ___ |
| `trials_to_best` | ___ | ___ |
| `total_time` (min) | ___ | ___ |
| `total_cost` ($) | ___ | ___ |
| `cost_per_trial_avg` ($) | ___ | ___ |
| `early_stop_count` | ___ | ___ |

---

### TEST-B5: 분산 학습 (Multi-GPU)

**목적**: A100 ×4 분산 학습의 스케일링 효율 검증

| 항목 | 내용 |
|------|------|
| **모델** | TransE (PyTorch DDP) |
| **구성** | ① A100 ×1, ② A100 ×2, ③ A100 ×4 |
| **프레임워크** | PyTorch DistributedDataParallel |

**실행 코드 (4 GPU)**:
```python
job = aiplatform.CustomContainerTrainingJob(
    display_name="test-b5-distributed-4gpu",
    container_uri="us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/kge-trainer:latest",
    labels={"test-id": "test-b5"}
)

model = job.run(
    args=["--epochs=50", "--distributed=true"],
    machine_type="a2-highgpu-4g",       # 4× A100
    accelerator_type="NVIDIA_TESLA_A100",
    accelerator_count=4,
    replica_count=1,
)
```

**측정 지표**:

| 지표 | 1× A100 | 2× A100 | 4× A100 |
|------|---------|---------|---------|
| `train_time` (min) | ___ | ___ | ___ |
| `scaling_efficiency` (%) | 100% (baseline) | ___ | ___ |
| `cost_total` ($) | ___ | ___ | ___ |
| `gpu_util_avg` (%) | ___ | ___ | ___ |
| `communication_overhead` (%) | 0% | ___ | ___ |

**스케일링 효율 공식**: `efficiency = (1GPU_time / (N_GPU_time × N)) × 100%`

---

## 5. Part C — LLM / Generative AI

> **목적**: Vertex AI의 LLM API(Gemini), Embedding API, Fine-Tuning, RAG Engine, Grounding, Agent Engine을 검증.
> 설계 문서의 Graph/RAG용 Embedding 생성 및 LLM Fine-tuning 시나리오에 직접 대응합니다.

---

### TEST-C1: Gemini API — 기본 추론 성능

**목적**: Gemini 모델 패밀리의 추론 latency, 처리량, 비용 비교

| 항목 | 내용 |
|------|------|
| **모델** | Gemini 2.5 Flash, Gemini 2.5 Pro, Gemini 2.0 Flash-Lite |
| **프롬프트 크기** | ① Short (100 tokens), ② Medium (1K tokens), ③ Long (10K tokens), ④ XLong (100K tokens) |
| **최대 출력** | 2,048 tokens |
| **동시 요청** | 1, 10, 50, 100 |
| **반복** | 각 조합 10회 |

**실행 코드 (google-genai SDK)**:
```python
import google.genai as genai
from google.genai import types
import time

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")

prompts = {
    "short": "Summarize the concept of knowledge graph embedding in one sentence.",
    "medium": open("prompts/medium_1k.txt").read(),
    "long": open("prompts/long_10k.txt").read(),
    "xlong": open("prompts/xlong_100k.txt").read(),
}

models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash-lite"]

for model_id in models:
    for prompt_name, prompt_text in prompts.items():
        latencies = []
        for _ in range(10):
            start = time.time()
            response = client.models.generate_content(
                model=model_id,
                contents=prompt_text,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=2048,
                )
            )
            elapsed = time.time() - start
            latencies.append(elapsed)

            # 토큰 사용량 기록
            usage = response.usage_metadata
            log_result(model_id, prompt_name, elapsed,
                      usage.prompt_token_count, usage.candidates_token_count)
```

**실행 코드 (REST API 직접 호출)**:
```bash
curl -X POST \
  "https://us-central1-aiplatform.googleapis.com/v1/projects/ml-api-test-vertex/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"role": "user", "parts": [{"text": "Summarize knowledge graph embedding."}]}],
    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 2048}
  }'
```

**측정 지표**:

| 지표 | 2.5 Flash | 2.5 Pro | 2.0 Flash-Lite |
|------|-----------|---------|----------------|
| `ttft_p50` (ms) — Time to First Token | ___ | ___ | ___ |
| `ttft_p99` (ms) | ___ | ___ | ___ |
| `total_latency_p50` (ms) | ___ | ___ | ___ |
| `total_latency_p99` (ms) | ___ | ___ | ___ |
| `tokens_per_sec` (output) | ___ | ___ | ___ |
| `input_cost_per_1M` ($) | $0.30 | $1.25 | $0.075 |
| `output_cost_per_1M` ($) | $2.50 | $10.00 | $0.30 |
| `100K context_supported` | O | O | 확인 |
| `throttle_at_N_concurrent` | ___ | ___ | ___ |

**Pass/Fail 기준**:
- TTFT < 500ms (Short prompt, 단일 요청) → 실시간 서비스 사용 가능
- 100K context에서 응답 품질 유지 여부 (정성 평가)
- 50 동시 요청에서 throttle 미발생 → 프로덕션 사용 가능

---

### TEST-C2: Embeddings API — 대규모 텍스트 임베딩

**목적**: Graph/RAG용 대규모 텍스트 코퍼스의 임베딩 생성 성능·비용 검증

| 항목 | 내용 |
|------|------|
| **모델** | `gemini-embedding-001`, `text-embedding-005` |
| **데이터** | `DS-TXT-CORPUS` (500K 문서, 평균 500자/문서) |
| **배치 크기** | 1, 50, 250 (API 최대) |
| **차원** | 256, 768 (text-embedding-005), 기본값 (gemini-embedding-001) |
| **task_type** | `RETRIEVAL_DOCUMENT`, `RETRIEVAL_QUERY`, `SEMANTIC_SIMILARITY` |

**실행 코드**:
```python
import google.genai as genai
from google.genai import types

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")

# 단건 호출
response = client.models.embed_content(
    model="gemini-embedding-001",
    contents="Knowledge graph embedding represents entities and relations as vectors.",
    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
)
embedding = response.embeddings[0].values

# 배치 호출 (250건)
texts = load_batch(batch_size=250)
response = client.models.embed_content(
    model="text-embedding-005",
    contents=texts,
    config=types.EmbedContentConfig(
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=256
    )
)
```

**전체 코퍼스 임베딩 실행 계획**:
```
500K 문서 ÷ 250 (배치 크기) = 2,000 API 호출
Quota: 5,000,000 tokens/min → 약 10,000 문서/min (500자/문서 기준)
예상 소요: 500K ÷ 10K = ~50분

비용: 500K × 500자 = 250M 문자 = 250K × 1000자 단위
      $0.000025/1000자 × 250K = $6.25
```

**측정 지표**:

| 지표 | gemini-embedding-001 | text-embedding-005 |
|------|---------------------|-------------------|
| `single_latency_p50` (ms) | ___ | ___ |
| `batch_250_latency_p50` (ms) | ___ | ___ |
| `throughput` (docs/min) | ___ | ___ |
| `total_500K_time` (min) | ___ | ___ |
| `total_cost` ($) | ___ | ___ |
| `embedding_dim` | ___ | 256 / 768 |
| `retrieval_quality` (nDCG@10) | ___ | ___ |

**품질 평가**: 생성된 임베딩으로 간단한 검색 태스크 (50개 쿼리 → 코퍼스 검색) 수행하여 nDCG@10 비교

---

### TEST-C3: Supervised Fine-Tuning (SFT) — Gemini 모델

**목적**: Gemini 모델의 SFT로 도메인 특화 성능 향상 정도 + 비용·시간 검증

| 항목 | 내용 |
|------|------|
| **Base 모델** | Gemini 2.0 Flash, Gemini 2.5 Flash-Lite |
| **학습 데이터** | `DS-LLM-SFT` (10K examples, instruction-response 형태) |
| **평가 데이터** | `DS-LLM-EVAL` (1K examples) |
| **Epochs** | 1, 3, 5 |
| **Adapter Size** | 4, 8 |

**학습 데이터 형식 (JSONL)**:
```json
{"contents": [
  {"role": "user", "parts": [{"text": "KGE 모델에서 TransE의 scoring function을 설명해줘."}]},
  {"role": "model", "parts": [{"text": "TransE는 h + r ≈ t 관계를 학습합니다. scoring function은 ..."}]}
]}
```

**실행 코드 (google-genai SDK)**:
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

# 완료 대기
completed_job = client.tunings.get(name=tuning_job.name)
# 튜닝된 모델 엔드포인트
tuned_model = completed_job.tuned_model.endpoint
```

**실행 코드 (REST API 직접 호출)**:
```bash
curl -X POST \
  "https://us-central1-aiplatform.googleapis.com/v1/projects/ml-api-test-vertex/locations/us-central1/tuningJobs" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "baseModel": "gemini-2.0-flash-001",
    "supervisedTuningSpec": {
      "trainingDatasetUri": "gs://ml-api-test-vertex/datasets/DS-LLM-SFT/train.jsonl",
      "validationDatasetUri": "gs://ml-api-test-vertex/datasets/DS-LLM-SFT/val.jsonl",
      "hyperParameters": {
        "epochCount": 3,
        "learningRateMultiplier": 1.0,
        "adapterSize": "ADAPTER_SIZE_FOUR"
      }
    },
    "tunedModelDisplayName": "test-c3-sft-rest"
  }'
```

**평가 방법**:
1. `DS-LLM-EVAL`의 1K 질문을 base model과 tuned model 각각에 추론
2. Reference 답변 대비 ROUGE-L, BERTScore 자동 평가
3. 50개 샘플을 사람이 직접 비교 평가 (A/B blind test)

**측정 지표**:

| 지표 | Base (2.0 Flash) | SFT 1ep | SFT 3ep | SFT 5ep |
|------|-----------------|---------|---------|---------|
| `train_time` (min) | — | ___ | ___ | ___ |
| `train_cost` ($) | — | ___ | ___ | ___ |
| `rouge_l` | ___ | ___ | ___ | ___ |
| `bert_score` | ___ | ___ | ___ | ___ |
| `human_preference_win_rate` | — | ___ | ___ | ___ |
| `inference_latency_p50` (ms) | ___ | ___ | ___ | ___ |
| `inference_cost_per_1M` ($) | ___ | ___ | ___ | ___ |

**비용 참고**: Gemini 2.0 Flash SFT = $3.00/1M training tokens. 10K examples × ~500 tokens = ~5M tokens → ~$15/epoch

---

### TEST-C4: LoRA Fine-Tuning — 오픈 모델 (Gemma 3)

**목적**: Model Garden의 오픈 모델(Gemma 3)에 LoRA 적용하여 Custom Training Job으로 학습. SFT와 비교.

| 항목 | 내용 |
|------|------|
| **Base 모델** | Gemma 3 4B (Model Garden) |
| **방법** | LoRA (rank=16, alpha=32), TRL + PEFT 라이브러리 |
| **GPU** | A100-40GB ×1 |
| **데이터** | `DS-LLM-SFT` (동일) |
| **Epochs** | 3 |

**실행 코드**:
```python
job = aiplatform.CustomContainerTrainingJob(
    display_name="test-c4-gemma3-lora",
    container_uri="us-central1-docker.pkg.dev/ml-api-test-vertex/ml-containers/llm-trainer:latest",
    labels={"test-id": "test-c4"}
)

model = job.run(
    args=[
        "--model_name=google/gemma-3-4b",
        "--method=lora",
        "--lora_rank=16",
        "--lora_alpha=32",
        "--epochs=3",
        "--batch_size=4",
        "--gradient_accumulation=8",
        "--data_path=gs://ml-api-test-vertex/datasets/DS-LLM-SFT/",
        "--output_dir=gs://ml-api-test-vertex/models/gemma3-lora/"
    ],
    machine_type="a2-highgpu-1g",
    accelerator_type="NVIDIA_TESLA_A100",
    accelerator_count=1,
    replica_count=1,
)
```

**LoRA 컨테이너 내부 코드 (핵심)**:
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer

model = AutoModelForCausalLM.from_pretrained("google/gemma-3-4b", torch_dtype=torch.bfloat16)
lora_config = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM")
model = get_peft_model(model, lora_config)

trainer = SFTTrainer(model=model, train_dataset=dataset, tokenizer=tokenizer, args=training_args)
trainer.train()
```

**Gemini SFT vs Gemma LoRA 비교**:

| 지표 | Gemini 2.0 Flash SFT (C3) | Gemma 3 4B LoRA (C4) |
|------|--------------------------|---------------------|
| `train_time` | ___ | ___ |
| `train_cost` ($) | ___ | ___ |
| `rouge_l` | ___ | ___ |
| `inference_latency` (ms) | ___ | ___ |
| `inference_cost` ($) | 토큰 과금 | GPU 시간 과금 |
| `model_ownership` | Google 호스팅 | Self-hosted 가능 |
| `customization_depth` | Adapter만 | 전체 아키텍처 접근 |
| `deployment_flexibility` | Vertex AI Endpoint만 | 어디든 배포 가능 |

---

### TEST-C5: RAG Engine — 문서 검색 + 생성

**목적**: Vertex AI RAG Engine으로 기술 문서 기반 질의응답 시스템 구축 → 검색 품질 + E2E latency 검증

| 항목 | 내용 |
|------|------|
| **문서** | `DS-RAG-DOCS` (2K 기술 문서, 500MB) |
| **임베딩** | gemini-embedding-001 |
| **생성 모델** | Gemini 2.5 Flash |
| **검색 설정** | top_k=5, hybrid_search alpha=0.5 |

**실행 코드**:
```python
import google.genai as genai
from google.genai import types

client = genai.Client(vertexai=True, project="ml-api-test-vertex", location="us-central1")

# 1. RAG Corpus 생성
corpus = client.corpora.create(
    display_name="test-c5-rag-corpus",
    rag_embedding_model_config=types.RagEmbeddingModelConfig(
        vertex_prediction_endpoint=types.VertexPredictionEndpoint(
            model="publishers/google/models/gemini-embedding-001"
        )
    ),
    backend_config=types.RagCorpusBackendConfig(
        rag_managed_db=types.RagManagedDbConfig(
            tier="SCALED"
        )
    )
)

# 2. 문서 Import (GCS)
import_op = client.corpora.import_files(
    name=corpus.name,
    import_rag_files_config=types.ImportRagFilesConfig(
        gcs_source=types.GcsSource(uris=["gs://ml-api-test-vertex/datasets/DS-RAG-DOCS/"]),
        rag_file_chunking_config=types.RagFileChunkingConfig(
            chunk_size=512,
            chunk_overlap=100
        ),
        max_embedding_requests_per_min=900
    )
)

# 3. 검색 (Retrieval)
retrieval_response = client.corpora.retrieve_contexts(
    name=f"projects/ml-api-test-vertex/locations/us-central1",
    vertex_rag_store=types.VertexRagStore(
        rag_corpora=[corpus.name]
    ),
    query=types.RagQuery(
        text="GraphRAG에서 community detection 알고리즘은 어떻게 적용되나?",
        rag_retrieval_config=types.RagRetrievalConfig(
            top_k=5,
            hybrid_search=types.HybridSearch(alpha=0.5),
            filter=types.RagRetrievalConfig.Filter(
                vector_distance_threshold=0.5
            )
        )
    )
)

# 4. RAG + 생성 (Grounded Generation)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="GraphRAG에서 community detection 알고리즘은 어떻게 적용되나?",
    config=types.GenerateContentConfig(
        tools=[types.Tool(
            retrieval=types.Retrieval(
                vertex_rag_store=types.VertexRagStore(
                    rag_corpora=[corpus.name],
                    rag_retrieval_config=types.RagRetrievalConfig(top_k=5)
                )
            )
        )]
    )
)
```

**테스트 시나리오**:

| # | 시나리오 | 평가 항목 |
|---|---------|----------|
| 5a | 50개 질의에 대한 검색 품질 | Recall@5, nDCG@5 (수동 relevance 레이블 기반) |
| 5b | RAG 생성 답변 품질 | ROUGE-L, 정확성 (수동 평가) |
| 5c | RAG vs 순수 Gemini (RAG 없음) 비교 | 답변 정확성 차이 |
| 5d | 문서 수 증가 (500 → 1K → 2K) 시 검색 latency 변화 | p50/p99 latency |
| 5e | chunk_size 변경 (256/512/1024) 시 검색 품질 변화 | Recall@5 변화 |

**측정 지표**:

| 지표 | 값 |
|------|---|
| `corpus_create_time` (sec) | ___ |
| `import_2K_docs_time` (min) | ___ |
| `import_cost` ($) | ___ |
| `retrieval_latency_p50` (ms) | ___ |
| `retrieval_latency_p99` (ms) | ___ |
| `rag_generation_latency_p50` (ms) | ___ |
| `recall_at_5` | ___ |
| `ndcg_at_5` | ___ |
| `rag_vs_base_accuracy_delta` (%) | ___ |
| `monthly_spanner_cost` ($) | ___ (managed DB) |

---

### TEST-C6: Grounding with Google Search

**목적**: 최신 정보가 필요한 쿼리에서 Google Search Grounding의 품질 + 비용 검증

| 항목 | 내용 |
|------|------|
| **모델** | Gemini 2.5 Flash |
| **쿼리** | 30개 (최신 정보 필요 10개, 일반 지식 10개, 기술 심층 10개) |
| **비교** | Grounding ON vs OFF |

**실행 코드**:
```python
# Grounding with Google Search
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="2026년 최신 Graph Neural Network 연구 동향을 알려줘.",
    config=types.GenerateContentConfig(
        tools=[types.Tool(
            google_search=types.GoogleSearch()
        )]
    )
)

# Grounding metadata 확인
grounding = response.candidates[0].grounding_metadata
print(grounding.search_entry_point)  # 검색 쿼리
print(grounding.grounding_chunks)    # 참조된 소스
print(grounding.grounding_supports)  # 지원 근거
```

**측정 지표**:

| 지표 | Grounding ON | Grounding OFF |
|------|-------------|---------------|
| `factual_accuracy` (수동 평가, %) | ___ | ___ |
| `source_citation_rate` (%) | ___ | N/A |
| `latency_p50` (ms) | ___ | ___ |
| `latency_overhead` (ms) | ___ | — |
| `cost_per_query` ($) | $0.035 + 토큰비용 | 토큰비용만 |

---

### TEST-C7: Model Garden — 오픈 모델 배포 + 추론

**목적**: Model Garden에서 Llama 4 / Mistral 등 오픈 모델을 배포하여 Gemini 대비 비용·성능 비교

| 항목 | 내용 |
|------|------|
| **모델** | Llama 4 Scout (Managed API), Mistral Large (Managed API) |
| **프롬프트** | TEST-C1과 동일 (Short/Medium/Long) |
| **비교 대상** | Gemini 2.5 Pro (TEST-C1 결과 참조) |

**실행 코드 (Managed API)**:
```python
# Llama 4 Scout
response = client.models.generate_content(
    model="meta/llama-4-scout",
    contents="Explain knowledge graph embedding methods.",
    config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=2048)
)

# Mistral Large
response = client.models.generate_content(
    model="mistralai/mistral-large",
    contents="Explain knowledge graph embedding methods.",
    config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=2048)
)
```

**측정 지표**:

| 지표 | Gemini 2.5 Pro | Llama 4 Scout | Mistral Large |
|------|---------------|---------------|---------------|
| `latency_p50` (ms) | ___ | ___ | ___ |
| `tokens_per_sec` | ___ | ___ | ___ |
| `cost_per_1M_input` ($) | $1.25 | ___ | ___ |
| `cost_per_1M_output` ($) | $10.00 | ___ | ___ |
| `answer_quality` (1-5 수동) | ___ | ___ | ___ |
| `korean_quality` (1-5) | ___ | ___ | ___ |

---

### TEST-C8: Agent Engine — 에이전트 배포 + 세션 관리

**목적**: Vertex AI Agent Engine으로 LLM 에이전트를 배포하고 세션 관리·메모리 기능 검증

| 항목 | 내용 |
|------|------|
| **에이전트** | LangChain 기반 RAG 에이전트 (TEST-C5 RAG Corpus 활용) |
| **기능** | 세션 유지, 대화 메모리, 도구 호출 |

**실행 코드**:
```python
from vertexai.preview import reasoning_engines

# 에이전트 정의
def create_agent():
    from langchain_google_vertexai import ChatVertexAI
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate

    llm = ChatVertexAI(model_name="gemini-2.5-flash", temperature=0)
    tools = [rag_search_tool, calculator_tool]
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a Graph/RAG domain expert."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools)

# 에이전트 배포
remote_agent = reasoning_engines.ReasoningEngine.create(
    create_agent(),
    requirements=["google-cloud-aiplatform[langchain]", "langchain-google-vertexai"],
    display_name="test-c8-rag-agent"
)

# 세션 생성 + 대화
session = remote_agent.create_session(user_id="test-user-1")

response1 = remote_agent.query(
    input="GraphRAG의 community detection은 어떻게 작동해?",
    session_id=session.id
)

# 후속 질문 (세션 컨텍스트 유지 확인)
response2 = remote_agent.query(
    input="그럼 그 결과를 요약 생성에 어떻게 활용해?",
    session_id=session.id
)

# 메모리 확인
memories = remote_agent.list_memories(user_id="test-user-1")
```

**측정 지표**:

| 지표 | 값 |
|------|---|
| `deploy_time` (sec) | ___ |
| `first_query_latency` (ms) | ___ |
| `subsequent_query_latency` (ms) | ___ |
| `session_context_maintained` (bool) | ___ |
| `tool_call_success_rate` (%) | ___ |
| `memory_persistence_verified` (bool) | ___ |
| `cost_per_query` ($) | ___ |
| `max_concurrent_sessions` | ___ (quota: 10 BidiStream) |

---

## 6. Cross-Cutting 테스트

> Part A/B/C를 관통하는 공통 검증 항목

### TEST-X1: API 에러 핸들링 + Quota 초과 동작

**목적**: Quota 초과, 잘못된 요청, 인증 실패 시 API 응답 검증

| 시나리오 | 방법 | 기대 응답 |
|---------|------|----------|
| Quota 초과 (RPM) | 1초에 100회 연속 호출 | HTTP 429 + `Retry-After` 헤더 |
| 잘못된 모델 ID | 존재하지 않는 모델 지정 | HTTP 404 + 명확한 에러 메시지 |
| 인증 실패 | 만료된 토큰 사용 | HTTP 401 |
| 잘못된 입력 스키마 | 필수 필드 누락 | HTTP 400 + 필드 레벨 에러 |
| Region 미지원 | TPU를 미지원 region에서 요청 | HTTP 400 + region 안내 |

**검증**: 에러 응답의 일관성, 재시도 가능 여부 판단 정보 포함 여부

---

### TEST-X2: SDK vs REST API 일관성

**목적**: Python SDK와 REST API 직접 호출의 동작 일관성 확인

**대상 API** (각 Part에서 1개씩):
- Part A: `Model.upload()` vs `POST .../models:upload`
- Part B: `CustomTrainingJob.run()` vs `POST .../customJobs`
- Part C: `client.models.generate_content()` vs `POST .../models/{id}:generateContent`

**검증 항목**:
| 항목 | 확인 내용 |
|------|----------|
| 동일 결과 | SDK와 REST 호출이 동일 output 반환 |
| 에러 형태 | SDK exception vs HTTP status code 매핑 |
| latency 차이 | SDK 오버헤드 측정 (SDK - REST) |
| label/metadata 전달 | labels, displayName 등 전달 정확성 |

---

### TEST-X3: Billing Label 정확성

**목적**: `labels.test-id`가 Billing Export에 정확히 반영되는지 검증

**실행 방법**:
1. Phase 전체 완료 후 48시간 대기
2. BigQuery Billing Export 쿼리:
```sql
SELECT
  labels.key, labels.value,
  service.description,
  SUM(cost) as total_cost
FROM `project.dataset.gcp_billing_export_v1_*`
WHERE labels.key = "test-id"
GROUP BY labels.key, labels.value, service.description
ORDER BY total_cost DESC
```
3. 각 test-id별 비용이 예상 범위 내인지 확인

---

## 7. 결과 종합 매트릭스

### 7.1 Part A — Traditional ML 종합

```
┌───────────────────────┬──────────────────┬─────────────────┬──────────────┐
│ 테스트                 │ 핵심 결과         │ 비용             │ 판단          │
├───────────────────────┼──────────────────┼─────────────────┼──────────────┤
│ A1: AutoML Tabular    │ AU-PRC=___       │ $___/hr         │ ○/△/×       │
│ A2: AutoML Image      │ Acc=___, P99=___ms│ $___/hr        │ ○/△/×       │
│ A3: Feature Store     │ P99=___ms        │ $___/hr/node    │ ○/△/×       │
│ A4: Model Registry    │ Deploy=___s      │ —               │ ○/△/×       │
│ A5: Batch Prediction  │ ___rows/s        │ $___/1M rows    │ ○/△/×       │
└───────────────────────┴──────────────────┴─────────────────┴──────────────┘
```

### 7.2 Part B — Deep Learning 종합

```
┌───────────────────────┬──────────────────┬─────────────────┬──────────────┐
│ 테스트                 │ 핵심 결과         │ 비용             │ 판단          │
├───────────────────────┼──────────────────┼─────────────────┼──────────────┤
│ B1: GPU 학습 (KGE)    │ T4:___m A100:___m│ T4:$__ A100:$__ │ ○/△/×       │
│ B2: TPU 학습          │ ___min           │ $___            │ ○/△/×       │
│ B3: Kubeflow Pipeline │ E2E=___min       │ $___/run        │ ○/△/×       │
│ B4: HPT (Vizier)      │ Best MRR=___     │ $___/20 trials  │ ○/△/×       │
│ B5: 분산 학습 (4GPU)   │ Efficiency=___%  │ $___            │ ○/△/×       │
└───────────────────────┴──────────────────┴─────────────────┴──────────────┘
```

### 7.3 Part C — LLM 종합

```
┌───────────────────────┬──────────────────┬─────────────────┬──────────────┐
│ 테스트                 │ 핵심 결과         │ 비용             │ 판단          │
├───────────────────────┼──────────────────┼─────────────────┼──────────────┤
│ C1: Gemini API        │ TTFT=___ms       │ $___/1M tokens  │ ○/△/×       │
│ C2: Embeddings        │ ___docs/min      │ $___/500K docs  │ ○/△/×       │
│ C3: SFT (Gemini)      │ ROUGE-L Δ=+___  │ $___/epoch      │ ○/△/×       │
│ C4: LoRA (Gemma)      │ ROUGE-L=___      │ $___/run        │ ○/△/×       │
│ C5: RAG Engine        │ Recall@5=___     │ $___/month      │ ○/△/×       │
│ C6: Grounding         │ Accuracy Δ=+___% │ $___/1K queries │ ○/△/×       │
│ C7: Model Garden      │ latency=___ms    │ $___/1M tokens  │ ○/△/×       │
│ C8: Agent Engine      │ Session OK=___   │ $___/query      │ ○/△/×       │
└───────────────────────┴──────────────────┴─────────────────┴──────────────┘
```

### 7.4 최종 의사결정 연결

이 테스트 결과는 `compare.md`의 Phase 2 결과와 통합하여, **GCP Vertex AI를 ML 플랫폼으로 채택할 때의 API 수준 실현 가능성**을 판단하는 데 사용됩니다.

| compare.md Phase | 본 문서 연결 |
|-----------------|------------|
| Phase 2 (ML 컴퓨팅) | TEST-B1~B5 결과로 상세화 |
| Phase 4 (비용 실측) | TEST-A1~C8의 cost 필드로 API 단위 비용 분해 |
| Phase 3 (E2E Latency) | TEST-B3의 Pipeline E2E로 검증 |
| Phase 8 (확장성) | TEST-B5 분산 학습, TEST-C1 동시 요청 |

---

## 8. 일정 및 리소스

### 8.1 실행 일정

```
Week 1: 환경 구성 + Part A (Traditional ML)
  ├── Day 1:   GCP 프로젝트 설정, Quota 확인, 데이터셋 업로드
  ├── Day 2:   TEST-A1 (AutoML Tabular — 1hr/4hr/8hr 예산)
  ├── Day 3:   TEST-A2 (AutoML Image) + TEST-A3 (Feature Store)
  ├── Day 4:   TEST-A4 (Model Registry) + TEST-A5 (Batch Prediction)
  └── Day 5:   Part A 결과 정리 + 중간 리뷰

Week 2: Part B (Deep Learning)
  ├── Day 1:   TEST-B1 (GPU 학습 — T4, A100, H100 각 3회)
  ├── Day 2:   TEST-B2 (TPU 학습 — v5e 3회)
  ├── Day 3:   TEST-B3 (Kubeflow Pipeline E2E)
  ├── Day 4:   TEST-B4 (HPT Vizier — 20 trials)
  └── Day 5:   TEST-B5 (분산 학습 1/2/4 GPU)

Week 3: Part C (LLM)
  ├── Day 1:   TEST-C1 (Gemini API 모델별 추론)
  ├── Day 2:   TEST-C2 (Embeddings 500K 문서) + TEST-C6 (Grounding)
  ├── Day 3:   TEST-C3 (SFT — 3 에폭 구성별) + TEST-C4 (LoRA Gemma)
  ├── Day 4:   TEST-C5 (RAG Engine 구축 + 평가)
  └── Day 5:   TEST-C7 (Model Garden) + TEST-C8 (Agent Engine)

Week 4: Cross-Cutting + 결과 종합
  ├── Day 1:   TEST-X1 (에러 핸들링) + TEST-X2 (SDK vs REST)
  ├── Day 2:   TEST-X3 (Billing 검증) + 48시간 billing 대기 시작
  ├── Day 3:   LLM 수동 평가 (C3 A/B test, C5 관련성 평가)
  ├── Day 4:   결과 종합 매트릭스 작성
  └── Day 5:   최종 보고서 + 환경 정리 (리소스 삭제)
```

### 8.2 비용 예산

| Part | 주요 비용 항목 | 예상 범위 |
|------|-------------|----------|
| **A** | AutoML training (8hr×$21.25), Feature Store nodes, Endpoint serving | $200~$400 |
| **B** | GPU: T4($0.62/hr), A100($3.67/hr), H100($12.47/hr) × 반복, TPU v5e, HPT 20 trials | $500~$1,200 |
| **C** | Gemini API tokens, SFT training ($15/epoch×6), RAG Spanner, Embedding 500K docs | $200~$500 |
| **X** | 추가 API 호출, Billing 검증용 | $50~$100 |
| **인프라** | GCS, Artifact Registry, Firestore, 네트워크 | $50~$100 |
| **합계** | | **$1,000~$2,300** |

### 8.3 필요 인력

| 역할 | 인원 | 담당 |
|------|-----|------|
| **ML Engineer** | 1명 | Part A + B 실행 (Vertex AI Training, Pipelines) |
| **LLM Engineer** | 1명 | Part C 실행 (Gemini, RAG, SFT, Agent) |
| **Platform Engineer** | 1명 | 환경 구성, Billing 분석, Cross-Cutting |
| **도메인 전문가** | 1명 (파트타임) | TEST-C3/C5 수동 평가, 질문셋 작성 |

### 8.4 리스크 및 완화

| 리스크 | 영향 | 완화 |
|--------|------|------|
| GPU/TPU Quota 부족 | Part B 지연 | 2주 전 Quota 증가 요청. 불가 시 T4만으로 진행 |
| SFT Quota (1 concurrent) | Part C 지연 | epoch별 순차 실행. Quota 증가 요청 |
| Gemini 3 SFT 접근 제한 | TEST-C3 범위 축소 | Gemini 2.x로 대체 (이미 계획에 포함) |
| RAG Engine Spanner 비용 | 예산 초과 | BASIC tier 사용, 테스트 완료 즉시 Corpus 삭제 |
| SDK 버전 호환성 | 코드 실행 실패 | requirements.txt 버전 고정, 가상환경 격리 |
| 대용량 Embedding 처리 Quota | TEST-C2 지연 | 5M tokens/min Quota 내 배치 크기 조절 |
