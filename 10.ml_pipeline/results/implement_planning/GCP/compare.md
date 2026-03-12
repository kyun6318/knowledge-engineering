# GCP vs AWS ML Pipeline 비교 테스트 실행 계획

> 본 문서는 `research.md`에서 분석한 장점, 단점, 트레이드오프를 **실측 데이터로 검증**하기 위한 테스트 실행 계획입니다.
> 각 테스트는 research.md의 특정 주장에 매핑되며, 재현 가능한 조건과 정량적 판단 기준을 포함합니다.

---

## 목차

1. [테스트 전략 개요](#1-테스트-전략-개요)
2. [환경 구성](#2-환경-구성)
3. [Phase 1 — 데이터 전송 성능 비교](#3-phase-1--데이터-전송-성능-비교)
4. [Phase 2 — ML 컴퓨팅 성능 비교](#4-phase-2--ml-컴퓨팅-성능-비교)
5. [Phase 3 — E2E 파이프라인 Latency 비교](#5-phase-3--e2e-파이프라인-latency-비교)
6. [Phase 4 — 비용 실측 비교](#6-phase-4--비용-실측-비교)
7. [Phase 5 — 안정성 및 장애 처리 비교](#7-phase-5--안정성-및-장애-처리-비교)
8. [Phase 6 — 보안 비교](#8-phase-6--보안-비교)
9. [Phase 7 — 운영성 비교](#9-phase-7--운영성-비교)
10. [Phase 8 — 확장성 비교](#10-phase-8--확장성-비교)
11. [결과 종합 및 의사결정 매트릭스](#11-결과-종합-및-의사결정-매트릭스)
12. [일정 및 리소스](#12-일정-및-리소스)

---

## 1. 테스트 전략 개요

### 1.1 목적
research.md에서 제기한 6가지 장점, 6가지 단점, 6가지 트레이드오프 항목을 **동일 조건의 GCP/AWS 병렬 환경에서 실측하여** 데이터 기반 의사결정을 가능하게 합니다.

### 1.2 비교 대상

| 구분 | GCP 환경 (현재 설계) | AWS 대안 환경 |
|------|---------------------|-------------|
| **오케스트레이션** | Vertex AI Pipelines (Kubeflow) | SageMaker Pipelines |
| **이벤트 버스** | Pub/Sub + Cloud Tasks + Eventarc | SNS + SQS + EventBridge + Step Functions |
| **상태 저장소** | Firestore | DynamoDB |
| **컴퓨트** | Vertex AI Training (GPU/TPU) | SageMaker Training (GPU) |
| **컨테이너 실행** | Cloud Functions + Cloud Run | Lambda + ECS/Fargate |
| **데이터 전송** | STS (S3→GCS) + EXP (GCS→S3) | 동일 리전 S3 직접 접근 (전송 불필요) |
| **인증** | WIF + AssumeRoleWithWebIdentity | IAM Role (동일 계정/Cross-Account) |
| **모니터링** | Cloud Monitoring + Cloud Logging | CloudWatch + X-Ray |

### 1.3 테스트 원칙

1. **동일 워크로드**: 양 환경에서 동일한 모델, 동일한 데이터셋, 동일한 컨테이너 이미지를 사용
2. **3회 반복**: 모든 정량 테스트는 최소 3회 반복하여 중간값(median)을 기준으로 비교
3. **동시 실행**: 네트워크 상태 등 외부 변수 통제를 위해 가능한 한 동일 시간대에 병렬 실행
4. **비용 태깅**: 모든 GCP/AWS 리소스에 `test-id` 라벨/태그를 부착하여 비용 추적 가능

### 1.4 테스트 데이터셋 프로파일

| 프로파일 | 크기 | 파일 수 | 용도 |
|---------|-----|---------|------|
| **Small** | 1 GB | ~100 files | 기능 검증, 빠른 반복 |
| **Medium** | 10 GB | ~1,000 files | 기본 성능 비교 기준 |
| **Large** | 50 GB | ~5,000 files | 대용량 전송 병목 검증 |
| **XLarge** | 200 GB | ~20,000 files | 스트레스 테스트, Postprocess I1 타임아웃 재현 |

---

## 2. 환경 구성

### 2.1 GCP 환경 (현재 설계 기반 축소 구현)

```
프로젝트: ml-pipeline-compare-gcp
리전: us-central1 (Vertex AI TPU 가용 리전)

인프라 구성:
├── Cloud Run: RunAPI (FastAPI)
├── Cloud Functions (2nd gen):
│   ├── execution-planner
│   ├── run-tracker
│   ├── preprocess-trigger
│   ├── train-trigger
│   ├── infer-trigger
│   └── postprocess-trigger
├── Pub/Sub: ml.run.requested, ml.{step}.requested, ml.step.completed,
│            ml.step.failed, ml.dead-letter, ml.data.synced, ml.data.sync.failed
├── Cloud Tasks: retry-queue
├── Firestore: run, execution_plan, lock, duplicate_events, audit_events
├── Storage Transfer Service
├── GCS: staging/, artifacts/, results/
├── Vertex AI Pipelines (Kubeflow)
├── Vertex AI Model Registry
├── Artifact Registry
├── Secret Manager: WIF config
└── Cloud Monitoring + Alerting
```

**IaC**: Terraform GCP provider로 전체 환경을 코드로 관리. `terraform apply` 1회로 전체 생성.

### 2.2 AWS 대안 환경 (동등 기능 구현)

```
계정: ml-pipeline-compare-aws
리전: us-east-1

인프라 구성:
├── API Gateway + Lambda: RunAPI 역할
├── Lambda Functions:
│   ├── execution-planner
│   ├── run-tracker
│   ├── preprocess-trigger
│   ├── train-trigger
│   ├── infer-trigger
│   └── postprocess-trigger
├── SNS + SQS: 동일 토픽 구조 매핑
│   ├── SNS: ml-run-requested, ml-{step}-requested, ml-step-completed, etc.
│   └── SQS: 각 Lambda의 입력 큐 (DLQ 포함)
├── Step Functions: retry backoff 오케스트레이션
├── DynamoDB: run, execution_plan, lock, duplicate_events, audit_events
├── S3: training-data/, staging/, artifacts/, results/
│   (★ S3 직접 접근 — STS/EXP 크로스 클라우드 전송 불필요)
├── SageMaker Pipelines (SageMaker SDK)
├── SageMaker Model Registry
├── ECR: container images
├── Secrets Manager: 설정 저장
└── CloudWatch + X-Ray
```

**IaC**: Terraform AWS provider. `terraform apply` 1회로 전체 생성.

### 2.3 공통 워크로드

| 컴포넌트 | 내용 |
|---------|------|
| **Preprocess** | 텍스트 코퍼스 정제 + Embedding 파생 피처 생성. 동일 Python 코드, 동일 Docker 이미지 |
| **Train** | Knowledge Graph Embedding (KGE) 모델 학습. PyTorch 기반. GPU: NVIDIA T4/A100 |
| **Infer** | Batch Prediction. 동일 모델로 동일 테스트셋 추론 |
| **Postprocess** | GCP: EXP(GCS→S3), AWS: S3 내부 복사 (동일 리전) |

### 2.4 환경 구성 전 체크리스트

- [ ] GCP 프로젝트 생성 + billing account 연결
- [ ] AWS 계정 생성 + billing alarm 설정
- [ ] 양 환경에 동일 Docker 이미지 푸시 (Artifact Registry / ECR)
- [ ] 테스트 데이터셋 4종 (Small/Medium/Large/XLarge) S3에 업로드
- [ ] GCP 환경: S3 접근용 WIF + IAM Role 설정
- [ ] AWS 환경: SageMaker execution role + S3 접근 권한 설정
- [ ] 비용 태깅: GCP label `test-id`, AWS tag `test-id` 설정
- [ ] Terraform 코드 리뷰 및 `plan` 확인
- [ ] 모니터링 대시보드 양쪽 생성 (Grafana 또는 각 네이티브)

---

## 3. Phase 1 — 데이터 전송 성능 비교

> **검증 대상**: research.md §3.1 "크로스 클라우드 데이터 전송 오버헤드"

### TEST-1.1: Inbound 데이터 전송 Latency

**목적**: S3→GCS (STS) vs S3 직접 접근의 시간 차이 실측

| 항목 | 내용 |
|------|------|
| **GCP 시나리오** | EP → STS trigger → S3에서 GCS staging으로 전송 → Eventarc → ml.data.synced 수신 |
| **AWS 시나리오** | Lambda(EP) → S3에서 직접 읽기 (전송 단계 없음, latency ≈ 0) |
| **데이터셋** | Small(1GB), Medium(10GB), Large(50GB), XLarge(200GB) |
| **측정 지표** | 전송 시작~ml.data.synced 수신까지 wall-clock 시간 (초) |
| **반복 횟수** | 각 데이터셋 3회 |

**실행 단계**:
1. S3에 테스트 데이터셋 + `_READY` marker 업로드
2. GCP: RunAPI 호출 → EP가 STS 트리거하는 시점 타임스탬프 기록 (Firestore `run.updated_at`)
3. GCP: `ml.data.synced` 수신 시점 타임스탬프 기록
4. AWS: Lambda(EP) 시작 시점에서 S3 객체 접근 가능 여부 확인 (추가 전송 없으므로 즉시)
5. 결과를 `{test_id, env, dataset_size, transfer_seconds}` 형태로 기록

**기대 결과**:
```
| 데이터셋 | GCP (STS) | AWS (직접) | 차이 |
|---------|-----------|-----------|------|
| 1 GB    | ~30s      | ~0s       | ~30s |
| 10 GB   | ~3min     | ~0s       | ~3min|
| 50 GB   | ~15min    | ~0s       | ~15min|
| 200 GB  | ~60min    | ~0s       | ~60min|
```

**Pass/Fail 기준**: 기대값 테이블을 벤치마크로 삼되, 실측값이 기대값의 2배를 초과하면 STS 설정 검토 필요

---

### TEST-1.2: Outbound 데이터 전송 Latency (Postprocess)

**목적**: EXP(GCS→S3) vs S3 내부 복사의 시간 차이 + I1 타임아웃 재현

| 항목 | 내용 |
|------|------|
| **GCP 시나리오** | Postprocess Trigger → EXP 동기 HTTP 호출 → WIF 인증 → GCS read → S3 multipart upload → Checksum 검증 |
| **AWS 시나리오** | Lambda(Postprocess) → S3 CopyObject (동일 리전) |
| **데이터셋** | Small(1GB), Medium(10GB), Large(50GB), XLarge(200GB) |
| **측정 지표** | ① 전송 시간(초), ② Checksum 검증 시간(초), ③ WIF 인증 시간(초), ④ CF/Lambda 타임아웃 발생 여부 |
| **반복 횟수** | 각 데이터셋 3회 |

**실행 단계**:
1. GCS의 `artifacts/` 및 `results/` 버킷에 테스트 데이터 적재
2. GCP: `ml.postprocess.requested` 발행 → Postprocess Trigger → EXP 동기 호출
3. EXP 내부에서 단계별 타임스탬프 수집:
   - `t1`: WIF Token 발급 시작
   - `t2`: AssumeRoleWithWebIdentity 완료
   - `t3`: GCS 읽기 완료
   - `t4`: S3 multipart upload 완료
   - `t5`: Checksum 검증 완료
4. AWS: Lambda에서 `s3.copy_object()` 호출 시간 측정
5. XLarge 데이터셋에서 GCP CF timeout(60분) 초과 여부 확인 → I1 재현 테스트

**I1 타임아웃 재현 조건**:
- EXP의 Cloud Run Job max timeout: 3600s (60분)
- Postprocess Trigger CF timeout: 3600s (60분)
- XLarge(200GB) 전송이 60분을 초과하는지 확인
- 초과 시: 고아 Job 발생 여부 + Firestore 상태 일관성 확인

**Pass/Fail 기준**:
- Small/Medium: GCP가 AWS 대비 10배 이내이면 허용 범위
- Large: GCP가 15분 이내 완료
- XLarge: CF timeout 초과 시 → I1 이슈 확인, 비동기 패턴 전환 근거 확보

---

### TEST-1.3: 네트워크 Egress 비용 실측

**목적**: 크로스 클라우드 전송의 실제 네트워크 비용 측정

| 항목 | 내용 |
|------|------|
| **측정 방법** | GCP Billing Export + AWS Cost Explorer에서 `test-id` 태그 기반 필터 |
| **측정 기간** | Phase 1 전체 테스트 기간 (TEST-1.1 + TEST-1.2 모든 반복 포함) |
| **측정 지표** | ① GCS egress 비용($), ② AWS S3 egress 비용($), ③ GB당 단가 실측값 |

**실행 단계**:
1. 테스트 시작 전 양쪽 billing 현재 snapshot 기록
2. Phase 1 모든 테스트 완료 후 24시간 대기 (billing 반영 지연)
3. GCP: Billing Export → BigQuery 쿼리 (`labels.test-id = 'phase1'`)
4. AWS: Cost Explorer → 태그 필터 (`test-id = phase1`)
5. 전송된 총 데이터량 대비 실제 비용 계산

**산출 공식**:
```
월간 예상 egress 비용 = (GB당 실측 단가) × (월간 예상 파이프라인 실행 횟수) × (실행당 평균 전송량)
```

---

### TEST-1.4: STS 실패 재시도 시 누적 지연

**목적**: STS 전송 실패 시 재시도(max 2회)에 의한 최악 지연 실측

| 항목 | 내용 |
|------|------|
| **시나리오** | STS 전송 중 의도적 실패 주입 → EP의 재시도 로직 검증 |
| **실패 주입 방법** | S3 버킷 정책에서 일시적으로 STS 접근 차단 → `ACCESS_DENIED` 유발 |
| **측정 지표** | ① 첫 시도~최종 성공까지 총 시간, ② 재시도 간격, ③ Firestore `sync_attempt` 증가 확인 |

**실행 단계**:
1. Medium 데이터셋으로 실행
2. S3 버킷 정책 수정: STS role 접근 Deny (첫 번째 시도 실패)
3. EP가 `ml.data.sync.failed` 수신 + `sync_attempt` 증가 확인
4. S3 버킷 정책 복원 (두 번째 시도 성공)
5. 총 소요 시간 = 첫 시도 시간 + 실패 감지 시간 + 재시도 간격 + 두 번째 시도 시간
6. max_sync_attempts=2 초과 시 `state=FAILED` 전이 확인 (별도 실행)

---

## 4. Phase 2 — ML 컴퓨팅 성능 비교

> **검증 대상**: research.md §2.1 "Vertex AI Pipelines ML 전용 오케스트레이션", §2.7 "비용 최적화 가능성"

### TEST-2.1: GPU 학습 성능 비교 (T4 / A100)

**목적**: 동일 모델 학습에서 Vertex AI vs SageMaker의 처리 시간과 비용 비교

| 항목 | 내용 |
|------|------|
| **모델** | KGE (Knowledge Graph Embedding) — PyTorch, 동일 하이퍼파라미터 |
| **GPU 구성** | ① NVIDIA T4 ×1, ② NVIDIA A100 ×1 |
| **GCP** | Vertex AI Custom Training Job (`n1-standard-8` + T4 / `a2-highgpu-1g` + A100) |
| **AWS** | SageMaker Training Job (`ml.g4dn.2xlarge` + T4 / `ml.p4d.24xlarge` + A100) |
| **데이터셋** | Medium(10GB) |
| **반복** | 각 구성 3회 |
| **측정 지표** | ① 학습 시간(분), ② 최종 loss, ③ 에폭당 처리 시간, ④ GPU utilization (%), ⑤ 총 비용($) |

**실행 단계**:
1. 동일 Docker 이미지를 Artifact Registry / ECR에 푸시
2. 동일 하이퍼파라미터 설정 파일 (YAML) 적용
3. GCP: Kubeflow Pipeline → Custom Training Job 실행
4. AWS: SageMaker Pipeline → Training Job 실행
5. 학습 완료 후 metrics (loss, accuracy) 비교 → 수렴 결과가 동일한지 확인
6. GPU utilization: GCP Cloud Monitoring / AWS CloudWatch에서 수집

**비용 산출**:
```
비용 = (인스턴스 시간당 가격) × (학습 소요 시간)

# 참고 가격 (2026-03 기준, on-demand)
GCP a2-highgpu-1g: ~$3.67/hr
AWS ml.p4d.24xlarge: ~$32.77/hr (8xA100 — 단일 A100 인스턴스 미제공이므로 스펙 차이 주의)

# Spot/Preemptible 비교
GCP Spot a2-highgpu-1g: ~$1.10/hr (약 70% 할인)
AWS Spot ml.p4d.24xlarge: ~$13.11/hr (약 60% 할인)
```

**Pass/Fail 기준**: 동일 GPU 구성에서 학습 시간 차이 10% 이내이면 "성능 동등", 비용 차이 20% 이상이면 "유의미한 차이"

---

### TEST-2.2: TPU 학습 (GCP 전용)

**목적**: TPU v4/v5를 활용한 학습이 GPU 대비 얼마나 효율적인지 검증 (GCP 고유 강점)

| 항목 | 내용 |
|------|------|
| **GCP** | Vertex AI Custom Training on TPU v4 (`ct4p-hightpu-4t`, 4 chips) |
| **AWS** | AWS Trainium (`trn1.2xlarge`) — TPU 대응 가속기 비교 |
| **모델** | LLM Fine-tuning (LoRA) — GPT-2 base 또는 동등 규모 |
| **데이터셋** | Medium(10GB) |
| **반복** | 3회 |
| **측정 지표** | ① 학습 시간(분), ② 에폭당 처리 시간, ③ 총 비용($), ④ 코드 수정 난이도 (정성적) |

**코드 수정 난이도 평가**:
- GCP TPU: PyTorch XLA 라이브러리 사용 필요 → 기존 PyTorch 코드 변경 범위 측정
- AWS Trainium: AWS Neuron SDK 사용 필요 → 기존 PyTorch 코드 변경 범위 측정
- 변경 라인 수, 디버깅 시간을 정량적으로 기록

---

### TEST-2.3: Batch Prediction 성능 비교

**목적**: 대규모 추론에서 Vertex AI Batch Prediction vs SageMaker Batch Transform 비교

| 항목 | 내용 |
|------|------|
| **GCP** | Vertex AI Batch Prediction Job |
| **AWS** | SageMaker Batch Transform Job |
| **모델** | TEST-2.1에서 학습된 동일 모델 |
| **추론 데이터** | Medium(10GB), Large(50GB) |
| **인스턴스** | GPU ×1 동일 스펙 |
| **반복** | 3회 |
| **측정 지표** | ① 총 추론 시간(분), ② 처리량(records/sec), ③ 인스턴스 시작 지연(cold start), ④ 비용($) |

---

## 5. Phase 3 — E2E 파이프라인 Latency 비교

> **검증 대상**: research.md §4.1 "ML 서비스 품질 vs 운영 복잡도"

### TEST-3.1: Happy Path E2E Latency

**목적**: 정상 실행 시 전체 파이프라인(Trigger → Completed)의 소요 시간 비교

| 항목 | 내용 |
|------|------|
| **GCP 경로** | EventBridge → RunAPI → EP → STS → Preprocess → Train → Infer → Postprocess(EXP) → ml.run.completed |
| **AWS 경로** | API Gateway → Lambda(RunAPI) → EP → Preprocess → Train → Infer → Postprocess(S3 copy) → run.completed |
| **데이터셋** | Medium(10GB) |
| **반복** | 3회 |

**단계별 타임스탬프 수집**:
```
GCP:
  t0: RunAPI 요청 수신
  t1: EP 설정 조회 완료 + lock 획득
  t2: STS 전송 완료 (ml.data.synced)        ← AWS에는 이 단계 없음
  t3: Preprocess Pipeline 완료 (ml.step.completed)
  t4: Train Pipeline 완료 (ml.step.completed)
  t5: Infer Pipeline 완료 (ml.step.completed)
  t6: Postprocess EXP 완료 (ml.step.completed) ← AWS: S3 copy 완료
  t7: ml.run.completed 발행

AWS:
  t0: API Gateway 요청 수신
  t1: Lambda(EP) 설정 조회 완료 + lock 획득
  t3: Preprocess SageMaker Pipeline 완료
  t4: Train SageMaker Pipeline 완료
  t5: Infer SageMaker Pipeline 완료
  t6: Postprocess S3 copy 완료
  t7: run.completed 이벤트 발행
```

**측정 지표**:
| 지표 | 설명 |
|------|------|
| `total_e2e` | t7 - t0 |
| `data_transfer_overhead` | GCP: (t2 - t1) + (t6 시 EXP 전송 시간), AWS: 0 |
| `compute_only` | t6 - t3 (GCP), t6 - t1 (AWS) |
| `orchestration_overhead` | total_e2e - data_transfer_overhead - compute_only |

**핵심 비교**: `data_transfer_overhead`가 전체 E2E의 몇 %를 차지하는지

---

### TEST-3.2: 이벤트 전파 Latency (오케스트레이션 오버헤드)

**목적**: 이벤트 버스를 통한 컴포넌트 간 메시지 전파 지연 비교

| 항목 | 내용 |
|------|------|
| **GCP** | Pub/Sub publish → Cloud Function cold/warm start → 처리 시작까지 |
| **AWS** | SNS → SQS → Lambda cold/warm start → 처리 시작까지 |
| **측정 구간** | ① RT가 ml.{next_step}.requested publish → TRG가 수신까지, ② TRG가 ml.step.completed publish → RT가 수신까지 |
| **반복** | 10회 (cold start 포함 5회, warm 상태 5회) |

**측정 방법**:
- 각 Cloud Function / Lambda에 진입 시점 타임스탬프를 structured log로 출력
- Pub/Sub message의 `publishTime` vs Cloud Function의 첫 로그 타임스탬프 차이 계산
- SNS → SQS → Lambda의 경우 SQS message의 `SentTimestamp` vs Lambda 첫 로그 차이 계산

---

### TEST-3.3: Firestore vs DynamoDB 트랜잭션 Latency

**목적**: 상태 관리 DB의 트랜잭션 성능 비교

| 항목 | 내용 |
|------|------|
| **GCP** | Firestore 트랜잭션: idempotency_key 확인 + state 업데이트 + execution_plan 조회 (단일 txn) |
| **AWS** | DynamoDB TransactWriteItems: 동일 로직 |
| **동시성** | ① 단일 요청, ② 10 동시 요청, ③ 50 동시 요청 |
| **반복** | 각 동시성 레벨 10회 |
| **측정 지표** | ① p50/p95/p99 latency (ms), ② 트랜잭션 충돌률(%), ③ 재시도 횟수 |

---

## 6. Phase 4 — 비용 실측 비교

> **검증 대상**: research.md §2.7 "비용 최적화 가능성", §4.3 "비용 구조 비교"

### TEST-4.1: 단일 파이프라인 실행 비용 상세 분해

**목적**: 1회 파이프라인 실행의 항목별 비용 비교

**데이터셋**: Medium(10GB), Train=GPU T4×1, 1 epoch

**비용 항목**:
```
GCP 항목:
├── Compute
│   ├── Vertex AI Training (GPU 시간)
│   ├── Vertex AI Batch Prediction (GPU 시간)
│   ├── Cloud Functions 호출 (EP, RT, TRG ×4)
│   └── Cloud Run (RunAPI, EXP)
├── Storage
│   ├── GCS (staging + artifacts + results)
│   └── Firestore (읽기/쓰기 작업)
├── Messaging
│   ├── Pub/Sub (메시지 수 + 데이터량)
│   └── Cloud Tasks (작업 수)
├── Network
│   ├── GCS egress (→ S3)
│   └── STS 전송 비용
├── Other
│   ├── Artifact Registry (이미지 저장)
│   ├── Secret Manager (API 호출)
│   └── Cloud Monitoring (메트릭 + 로그)
└── TOTAL

AWS 항목:
├── Compute
│   ├── SageMaker Training (GPU 시간)
│   ├── SageMaker Batch Transform (GPU 시간)
│   ├── Lambda 호출 (EP, RT, TRG ×4)
│   └── API Gateway (RunAPI 역할)
├── Storage
│   ├── S3 (training-data + artifacts + results)
│   └── DynamoDB (읽기/쓰기 CU)
├── Messaging
│   ├── SNS + SQS (메시지 수)
│   └── Step Functions (상태 전이 수)
├── Network
│   └── 동일 리전 — 무료
├── Other
│   ├── ECR (이미지 저장)
│   ├── Secrets Manager (API 호출)
│   └── CloudWatch (메트릭 + 로그 + X-Ray)
└── TOTAL
```

**측정 방법**:
1. 테스트 전 billing snapshot
2. Medium 데이터셋으로 1회 파이프라인 실행 (양쪽 동시)
3. 24시간 후 billing 조회, `test-id` 기반 필터
4. 항목별 분해 기록

---

### TEST-4.2: 월간 비용 시뮬레이션

**목적**: 다양한 실행 빈도에서의 월간 비용 예측

| 시나리오 | 월간 실행 횟수 | 데이터셋 크기 | GPU |
|---------|-------------|------------|-----|
| **Low** | 5회/월 | Medium(10GB) | T4 ×1 |
| **Medium** | 20회/월 | Medium(10GB) | A100 ×1 |
| **High** | 60회/월 | Large(50GB) | A100 ×1 |
| **Peak** | 100회/월 | Large(50GB) | A100 ×4 |

**산출 공식**:
```
월간 총 비용 = (실행당 비용 from TEST-4.1) × 실행 횟수
             + (고정 비용: 스토리지, 모니터링, 최소 인스턴스 유지비)
             + (네트워크 비용: 실행당 egress × 횟수)    ← GCP 환경에만 해당
```

**Spot/Preemptible 할인 적용**:
- GCP Spot 가격 (약 60-70% 할인) 적용 버전 추가 계산
- AWS Spot 가격 (약 50-60% 할인) 적용 버전 추가 계산
- 중단 빈도(Spot preemption rate) 실측은 Phase 5에서 수행

---

### TEST-4.3: 유휴 비용 비교

**목적**: 파이프라인 미실행 상태에서의 기본 인프라 유지 비용

| 항목 | GCP | AWS |
|------|-----|-----|
| **서버리스 컴퓨팅** | Cloud Functions — $0 (미호출) | Lambda — $0 (미호출) |
| **이벤트 버스** | Pub/Sub — 구독 유지 비용 | SNS+SQS — $0 |
| **상태 DB** | Firestore — 저장 비용만 | DynamoDB — 온디맨드 모드 $0, 프로비전 모드 CU 비용 |
| **스토리지** | GCS — 저장 비용 | S3 — 저장 비용 |
| **컨테이너** | Artifact Registry — 저장 비용 | ECR — 저장 비용 |
| **모니터링** | Cloud Monitoring 무료 티어 | CloudWatch 무료 티어 |
| **Cloud Run** | 최소 인스턴스 0 설정 시 $0 | Fargate — $0 (미실행) |

**측정 방법**: 양쪽 환경을 1주일간 아무 파이프라인도 실행하지 않고 방치 후 비용 확인

---

## 7. Phase 5 — 안정성 및 장애 처리 비교

> **검증 대상**: research.md §2.2 "이벤트 기반 아키텍처", §4.2 "디버깅 난이도"

### TEST-5.1: 멱등성 검증

**목적**: 동일 메시지 중복 수신 시 정확히 한 번(exactly-once) 처리되는지 검증

| 항목 | 내용 |
|------|------|
| **시나리오** | 동일 `ml.step.completed` 메시지를 3회 연속 발행 |
| **GCP 검증** | RT의 idempotency_key 확인 → 첫 번째만 처리, 나머지 ACK만 반환 |
| **AWS 검증** | DynamoDB conditional write로 동일 로직 구현 검증 |
| **측정 지표** | ① 중복 처리 발생 횟수 (기대: 0), ② Firestore/DynamoDB 상태 일관성, ③ 다음 step 이벤트 중복 발행 여부 |

**실행 단계**:
1. 정상 파이프라인 실행으로 preprocess step 완료
2. `ml.step.completed {step=preprocess}` 메시지를 수동으로 2회 추가 발행
3. Firestore/DynamoDB에서 `run` 문서 상태 확인 → `ml.train.requested`가 1회만 발행되었는지 확인
4. Pub/Sub/SQS 메시지 로그에서 발행 카운트 확인

---

### TEST-5.2: 중복 요청 차단 (Optimistic Lock)

**목적**: 동일 run_key로 동시 요청 시 하나만 실행되는지 검증

| 항목 | 내용 |
|------|------|
| **시나리오** | 동일 `project + run_key`로 5개 요청을 동시 발행 |
| **GCP 검증** | EP의 create-if-absent lock → 1개 성공, 4개 IGNORED + `duplicate_events` 기록 |
| **AWS 검증** | DynamoDB conditional put → 동일 로직 |
| **측정 지표** | ① 성공 실행 수 (기대: 1), ② IGNORED 수 (기대: 4), ③ 경합 해소 시간 (ms) |

---

### TEST-5.3: Step 실패 → 재시도 → DLQ 전체 흐름

**목적**: 실패 처리 3-Tier (Retry → DLQ → Manual) 의 정상 동작 검증

| 항목 | 내용 |
|------|------|
| **시나리오** | Train step에서 의도적 OOM 발생 → max_attempts=3 재시도 → 모두 실패 → DLQ |
| **실패 주입** | 학습 컨테이너에 메모리 제한을 극도로 낮게 설정 (예: 512MB) |
| **GCP 검증** | RT → Cloud Tasks 지연 재시도 (attempt 0,1,2) → ml.dead-letter 발행 → Slack 알림 |
| **AWS 검증** | Lambda(RT) → Step Functions 재시도 → SQS DLQ 이동 → CloudWatch 알림 |

**단계별 검증 포인트**:
```
GCP:
  1. ml.step.failed {attempt=0, error_code=OOM} → RT 수신 확인
  2. Firestore: state=RETRYING, attempt=1
  3. Cloud Tasks: 지연 task 생성 확인 (scheduleTime = now + 2^0 × base_delay)
  4. 지연 후 ml.train.requested {attempt=1} 발행 확인
  5. 위 과정 반복 (attempt=1→2)
  6. attempt=2에서 실패 → attempt(2) ≥ max_attempts(3) 아닌가?
     ★ 주의: 설계상 attempt < max_attempts 검사이므로, attempt=2에서 재시도가 한 번 더 발생
     → attempt=3에서 ml.step.failed 수신 → 3 ≥ 3 → DLQ 라우팅
  7. ml.dead-letter 메시지 내용 검증:
     - original_topic = ml.step.failed
     - original_message 전체 보존 여부
     - first_receive_time = message.publishTime
  8. Firestore: state=FAILED
  9. Cloud Monitoring → Slack 알림 수신 확인

AWS:
  1~6: 동일 로직을 Lambda + Step Functions + SQS로 구현
  7. SQS DLQ 메시지 내용 검증
  8. DynamoDB: state=FAILED
  9. CloudWatch → Slack 알림 수신 확인
```

**측정 지표**: ① 첫 실패~DLQ 도착까지 총 시간, ② 재시도 간 backoff 정확도, ③ 알림 도착 시간

---

### TEST-5.4: Cancel 흐름 (STEP_RUNNING / RETRYING)

**목적**: 실행 중 취소 요청의 정상 처리 + Race Condition 검증

**시나리오 A — STEP_RUNNING 중 Cancel**:
1. Train step 실행 중 (Pipeline 상태: RUNNING)
2. `POST /runs/{run_id}/cancel` 호출
3. GCP: RT → VXP cancel API → Pipeline Job 중지 → CANCELLED
4. AWS: Lambda(RT) → SageMaker StopTrainingJob → CANCELLED
5. 검증: Firestore/DynamoDB state=CANCELLED, `cancel_requested_at` 기록, `ml.run.cancelled` 발행

**시나리오 B — RETRYING 중 Cancel**:
1. Train step 실패 후 RETRYING 상태 (Cloud Tasks에 지연 task 예약됨)
2. `POST /runs/{run_id}/cancel` 호출
3. GCP: RT → Cloud Tasks delete (best-effort) → CANCELLING → CANCELLED
4. AWS: Lambda(RT) → Step Functions cancel → CANCELLED
5. 검증: 지연 task가 실행되더라도 상태 기반 무력화로 무시되는지 확인

**시나리오 C — Race Condition: CANCELLING + ml.step.failed 동시 수신**:
1. STEP_RUNNING 중 cancel 요청 발행
2. 거의 동시에 Pipeline이 자연 실패하여 `ml.step.failed` 발행
3. GCP: CANCELLING 상태에서 ml.step.failed 수신 → retry 없이 CANCELLED 흡수
4. 검증: `step_failed.timestamp` 와 `cancel_requested_at` 비교와 무관하게 CANCELLED 처리되는지

---

### TEST-5.5: Cloud Tasks 생성 실패 시 즉시 DLQ

**목적**: 인프라 오류(Cloud Tasks 생성 불가) 시 graceful degradation 검증

| 항목 | 내용 |
|------|------|
| **실패 주입** | Cloud Tasks API에 대한 SA 권한 일시 제거 |
| **기대 동작** | RT가 Cloud Tasks 생성 실패 감지 → 즉시 ml.dead-letter 발행 + state=FAILED |
| **검증** | ① FAILED 전이 지연 시간, ② ml.dead-letter 메시지 무결성, ③ Firestore 상태 일관성 |

---

## 8. Phase 6 — 보안 비교

> **검증 대상**: research.md §2.5 "WIF 인증", §4.4 "보안 경계 분리 vs 공격 표면"

### TEST-6.1: WIF 인증 체인 안정성

**목적**: 3단계 인증 체인의 각 단계별 실패 시 동작 검증

| 시나리오 | 실패 지점 | 기대 동작 |
|---------|----------|----------|
| **6.1a** | Google OIDC Token 발행 실패 (SA 키 만료) | EXP 즉시 HTTP 500 → ml.step.failed |
| **6.1b** | AWS STS AssumeRole 실패 (Trust Policy 불일치) | EXP 즉시 HTTP 500 → ml.step.failed |
| **6.1c** | S3 PutObject 권한 없음 (IAM Policy 오류) | 업로드 실패 → HTTP 500 → ml.step.failed |
| **6.1d** | 토큰 만료 (1시간 경과 중 대용량 업로드) | 토큰 갱신 또는 실패 처리 확인 |

**각 시나리오 실행 단계**:
1. 정상 동작 확인 (baseline)
2. 해당 실패 조건 주입
3. EXP 호출 → 실패 감지 → Postprocess Trigger가 ml.step.failed 발행 확인
4. Firestore state 확인
5. 실패 조건 복원 → 재실행으로 복구 확인

---

### TEST-6.2: EventBridge → RunAPI 인증 검증

**목적**: AWS에서 GCP로의 크로스 클라우드 API 호출 인증 보안성 검증

| 테스트 | 방법 | 기대 결과 |
|--------|------|----------|
| **정상 호출** | EventBridge API Destination → RunAPI | HTTP 200 |
| **만료 토큰** | OIDC 토큰 TTL 경과 후 호출 | HTTP 401, Cloud Run IAM 거부 |
| **변조 토큰** | JWT payload 변조 후 호출 | HTTP 401, 서명 검증 실패 |
| **권한 없는 SA** | 다른 GCP SA로 토큰 발급 | HTTP 403, RBAC 거부 |

---

### TEST-6.3: 자격증명 유출 범위 비교

**목적**: 만약 자격증명이 유출되었을 때의 blast radius 비교

| 구분 | GCP 환경 (WIF) | AWS 환경 (IAM Role) |
|------|---------------|-------------------|
| **유출 시나리오** | GCP SA 키 유출 | AWS Access Key 유출 |
| **유효 기간** | OIDC 토큰: 1시간, STS 토큰: 1시간 | Access Key: 무기한 (수동 폐기까지) |
| **접근 범위** | WIF Trust Policy에 정의된 AWS Role만 | IAM 정책에 정의된 모든 리소스 |
| **검증 방법** | 유출된 토큰으로 S3 접근 시도 → 1시간 후 자동 만료 확인 | (시뮬레이션) 유출 키 감지까지의 평균 시간 측정 |

---

## 9. Phase 7 — 운영성 비교

> **검증 대상**: research.md §3.2 "운영 복잡도", §4.2 "디버깅 난이도", §4.6 "통합 테스트 어려움"

### TEST-7.1: 장애 근본 원인 분석 시간 (MTTR 시뮬레이션)

**목적**: 동일한 장애 시나리오에서 근본 원인 파악에 걸리는 시간 비교

**방법**: 운영 경험이 비슷한 엔지니어 2인에게 동일 장애를 각각 GCP/AWS 환경에서 분석하게 함

| 장애 시나리오 | 설명 |
|-------------|------|
| **Scenario A** | Preprocess step이 timeout으로 실패. 원인: GCS staging 데이터 corrupt |
| **Scenario B** | Train step 재시도 2회 후 DLQ. 원인: 학습 컨테이너 이미지 버전 불일치 |
| **Scenario C** | Postprocess EXP가 S3 업로드 중 실패. 원인: AWS IAM Policy 변경으로 권한 부족 |

**측정 방법**:
1. 장애를 주입하고 정상 알림이 발생하도록 대기
2. 엔지니어에게 Slack 알림만 제공 (구두 힌트 없음)
3. 근본 원인 파악까지 시간 측정 + 열어본 콘솔/페이지 수 기록
4. 장애 복구까지 추가 시간 측정

**측정 지표**:
| 지표 | 설명 |
|------|------|
| `time_to_detect` | 알림 수신 시점 (자동) |
| `time_to_diagnose` | 근본 원인 파악까지 시간 |
| `consoles_checked` | 확인한 콘솔/대시보드 수 (GCP는 2개 이상 예상) |
| `log_queries_run` | 로그 검색 쿼리 실행 횟수 |
| `time_to_recover` | 장애 복구까지 총 시간 |

---

### TEST-7.2: 로그 추적성 (Traceability)

**목적**: 특정 run_id의 전체 이벤트 흐름을 로그에서 재구성하는 데 걸리는 시간과 난이도

| 항목 | 내용 |
|------|------|
| **GCP** | Cloud Logging에서 `run_id` 기반 필터 → Pub/Sub 메시지 로그 + CF 실행 로그 + Firestore 감사 로그 교차 확인 |
| **AWS** | CloudWatch Logs에서 `run_id` 기반 필터 + X-Ray 트레이스 조회 |

**실행 단계**:
1. 정상 완료된 파이프라인 1건의 run_id 제공
2. 해당 run의 전체 이벤트 타임라인 재구성 (모든 step의 시작/완료 시간, 모든 Pub/Sub/SNS 메시지)
3. 재구성에 소요된 시간 + 사용한 쿼리 수 측정

**핵심 비교 포인트**:
- GCP: Pub/Sub 메시지 내용 조회 → 별도 DLQ 구독으로 메시지 내용 확인 필요 (native logging은 metadata만)
- AWS: X-Ray 서비스 맵으로 시각적 추적 가능 여부

---

### TEST-7.3: IaC 코드 복잡도 비교

**목적**: 동일 기능 구현에 필요한 Terraform 코드량과 복잡도 비교

| 측정 항목 | 방법 |
|----------|------|
| **Terraform 라인 수** | `wc -l *.tf` (GCP provider vs AWS provider) |
| **리소스 수** | `terraform state list \| wc -l` |
| **프로바이더 수** | GCP: google + google-beta (+ aws for WIF), AWS: aws만 |
| **Cross-reference 수** | 다른 프로바이더의 리소스를 참조하는 횟수 |
| **apply 시간** | `terraform apply` 소요 시간 |
| **destroy 시간** | `terraform destroy` 소요 시간 |

---

### TEST-7.4: CI/CD 파이프라인 복잡도

**목적**: 양쪽 환경에 대한 CI/CD 구성의 복잡도 비교

| 측정 항목 | 설명 |
|----------|------|
| **필요한 자격증명 수** | GCP SA key + AWS credentials vs AWS credentials만 |
| **배포 단계 수** | CI/CD YAML의 step 수 |
| **배포 소요 시간** | 전체 파이프라인 실행 시간 |
| **롤백 복잡도** | 롤백에 필요한 수동 단계 수 |

---

### TEST-7.5: 로컬 개발 환경 구축 난이도

**목적**: 새 엔지니어가 로컬에서 개발 및 테스트를 시작하기까지의 시간

| 항목 | GCP 환경 | AWS 환경 |
|------|---------|---------|
| **사전 설치** | gcloud CLI, Firebase emulator, Pub/Sub emulator | awscli, LocalStack 또는 SAM CLI |
| **에뮬레이터 지원** | Firestore emulator (O), Pub/Sub emulator (O), Vertex AI emulator (X) | DynamoDB local (O), SQS/SNS local (O), SageMaker local mode (△) |
| **E2E 로컬 테스트** | 불가능 (STS, Vertex AI 에뮬레이터 없음) | 부분 가능 (SageMaker local mode 지원) |
| **통합 테스트** | GCP 실제 환경 필요 | AWS 실제 환경 필요 |

**측정**: 새 엔지니어 1인에게 각 환경의 설정 문서를 주고, 첫 번째 단위 테스트 통과까지 시간 측정

---

## 10. Phase 8 — 확장성 비교

> **검증 대상**: research.md §2.4 "Cloud Functions 마이크로 컨트롤러", §2.2 "Pub/Sub throughput"

### TEST-8.1: 동시 파이프라인 실행 확장성

**목적**: 다수의 파이프라인이 동시 실행될 때의 안정성과 처리량

| 부하 수준 | 동시 실행 수 | 설명 |
|----------|------------|------|
| **Low** | 5 동시 | 일반 운영 |
| **Medium** | 20 동시 | 피크 시간대 |
| **High** | 50 동시 | 스트레스 테스트 |

**측정 지표**:
| 지표 | 설명 |
|------|------|
| `success_rate` | 전체 run 중 COMPLETED 비율 |
| `avg_e2e_latency` | 평균 E2E 소요 시간 |
| `p99_e2e_latency` | P99 E2E 소요 시간 |
| `lock_contention_rate` | 동시 요청에 의한 lock 충돌 비율 |
| `throttle_count` | Pub/Sub/SQS 스로틀 발생 횟수 |
| `cf_cold_start_rate` | Cold start 비율 |
| `cost_per_run` | run당 평균 비용 |

**실행 방법**:
1. 서로 다른 `run_key`를 가진 요청을 동시 발행 (중복 차단 회피)
2. 각 요청은 Small(1GB) 데이터셋 사용 (전송 시간 최소화하여 오케스트레이션 확장성에 집중)
3. 모든 run이 완료 또는 실패할 때까지 대기
4. 지표 수집 및 비교

---

### TEST-8.2: Pub/Sub vs SNS+SQS Throughput

**목적**: 이벤트 버스의 메시지 처리 처리량과 ordering 보장 검증

| 항목 | 내용 |
|------|------|
| **테스트 방법** | 1,000개의 테스트 메시지를 1분 내에 발행 |
| **GCP** | Pub/Sub topic → ordering key=run_id → 순서 보장 확인 |
| **AWS** | SNS → SQS FIFO (MessageGroupId=run_id) → 순서 보장 확인 |
| **측정 지표** | ① 초당 발행량, ② 초당 소비량, ③ 순서 위반 건수, ④ 메시지 유실 건수, ⑤ p99 전달 지연(ms) |

---

### TEST-8.3: Spot/Preemptible 인스턴스 중단 내성

**목적**: 학습 도중 인스턴스가 preemption되었을 때의 복구 동작 검증

| 항목 | 내용 |
|------|------|
| **GCP** | Vertex AI Training on Spot VM → preemption 시 Pipeline FAILED → RT 재시도 |
| **AWS** | SageMaker Training on Spot Instance → 체크포인트 기반 자동 재시도 (managed spot training) |
| **측정 지표** | ① 중단 후 재시도까지 시간, ② 체크포인트 복원 성공률, ③ 총 학습 시간 증가율 |

**핵심 비교**: SageMaker의 Managed Spot Training은 체크포인트 기반 자동 재개를 네이티브 지원. GCP Vertex AI는 Spot preemption 시 Pipeline 실패로 처리되며 RT의 재시도 메커니즘에 의존 → 전체 step 재실행.

---

## 11. 결과 종합 및 의사결정 매트릭스

### 11.1 정량적 결과 종합 템플릿

모든 Phase 완료 후 아래 테이블에 실측값을 기입합니다.

```
┌─────────────────────────────┬──────────────────┬──────────────────┬─────────┐
│ 비교 항목                     │ GCP (실측값)      │ AWS (실측값)      │ 차이(%)  │
├─────────────────────────────┼──────────────────┼──────────────────┼─────────┤
│ Inbound 전송 (10GB)          │ ___s             │ 0s               │ ___     │
│ Outbound 전송 (10GB)         │ ___s             │ ___s             │ ___     │
│ Train T4 소요 시간            │ ___min           │ ___min           │ ___     │
│ Train A100 소요 시간          │ ___min           │ ___min           │ ___     │
│ E2E 파이프라인 (10GB)         │ ___min           │ ___min           │ ___     │
│ 이벤트 전파 지연 (p95)        │ ___ms            │ ___ms            │ ___     │
│ DB 트랜잭션 (p95)            │ ___ms            │ ___ms            │ ___     │
│ 단일 실행 비용               │ $___             │ $___             │ ___     │
│ 월간 비용 (20회/월)          │ $___             │ $___             │ ___     │
│ 월간 네트워크 비용            │ $___             │ $0               │ ___     │
│ 유휴 비용 (월)               │ $___             │ $___             │ ___     │
│ 재시도 총 시간 (3회)          │ ___min           │ ___min           │ ___     │
│ MTTR (Scenario C)           │ ___min           │ ___min           │ ___     │
│ IaC 라인 수                  │ ___lines         │ ___lines         │ ___     │
│ 로컬 환경 구축 시간           │ ___hr            │ ___hr            │ ___     │
│ 50 동시 실행 성공률           │ ___%             │ ___%             │ ___     │
│ Spot 중단 복구 시간           │ ___min           │ ___min           │ ___     │
└─────────────────────────────┴──────────────────┴──────────────────┴─────────┘
```

### 11.2 가중치 기반 의사결정 매트릭스

각 비교 축에 조직의 우선순위에 따른 가중치를 부여하고 종합 점수를 산출합니다.

| 비교 축 | 가중치 (예시) | GCP 점수 (1-5) | AWS 점수 (1-5) | GCP 가중 | AWS 가중 |
|---------|------------|---------------|---------------|---------|---------|
| ML 컴퓨팅 성능 | 25% | ___ | ___ | ___ | ___ |
| E2E Latency | 15% | ___ | ___ | ___ | ___ |
| 총 비용 | 20% | ___ | ___ | ___ | ___ |
| 운영 복잡도 | 15% | ___ | ___ | ___ | ___ |
| 보안 | 10% | ___ | ___ | ___ | ___ |
| 확장성 | 10% | ___ | ___ | ___ | ___ |
| 장애 복구 | 5% | ___ | ___ | ___ | ___ |
| **합계** | **100%** | | | **___** | **___** |

> 가중치는 조직의 상황에 따라 조정합니다. 예: ML 품질이 최우선이면 ML 컴퓨팅 성능 40%, 소규모 팀이면 운영 복잡도 30%.

### 11.3 Go/No-Go 판단 기준

| 결과 | 판단 |
|------|------|
| GCP 가중 합계 > AWS + 15% | GCP 별도 환경 **강력 추천** |
| GCP ≈ AWS (±15%) | 조직 역량/전략적 방향에 따라 결정 |
| AWS 가중 합계 > GCP + 15% | AWS 단일 환경 **강력 추천** |
| 특정 축에서 한쪽이 1점 (deal-breaker) | 해당 축의 이슈를 먼저 해결 후 재평가 |

---

## 12. 일정 및 리소스

### 12.1 실행 일정

```
Week 1: 환경 구성 (Terraform IaC 작성 + apply)
  ├── Day 1-2: GCP 환경 Terraform 작성 + 리뷰
  ├── Day 3-4: AWS 환경 Terraform 작성 + 리뷰
  └── Day 5:   양쪽 apply + 데이터셋 업로드 + 연결 검증

Week 2: Phase 1 (데이터 전송) + Phase 2 (ML 컴퓨팅)
  ├── Day 1-2: TEST-1.1 ~ TEST-1.4 (전송 성능)
  ├── Day 3-4: TEST-2.1 ~ TEST-2.3 (GPU/TPU 학습 + 추론)
  └── Day 5:   데이터 정리 + 중간 결과 리뷰

Week 3: Phase 3 (E2E) + Phase 4 (비용)
  ├── Day 1-2: TEST-3.1 ~ TEST-3.3 (E2E + 오케스트레이션)
  ├── Day 3:   TEST-4.1 ~ TEST-4.3 (비용 실측)
  └── Day 4-5: 24시간 billing 반영 대기 + 비용 분석

Week 4: Phase 5 (안정성) + Phase 6 (보안)
  ├── Day 1-2: TEST-5.1 ~ TEST-5.5 (멱등성, 재시도, Cancel, DLQ)
  ├── Day 3:   TEST-6.1 ~ TEST-6.3 (인증, 보안)
  └── Day 4-5: 결과 정리

Week 5: Phase 7 (운영성) + Phase 8 (확장성)
  ├── Day 1-2: TEST-7.1 ~ TEST-7.5 (MTTR, 추적성, IaC, CI/CD, 로컬 개발)
  ├── Day 3-4: TEST-8.1 ~ TEST-8.3 (동시 실행, throughput, Spot 내성)
  └── Day 5:   최종 데이터 수집

Week 6: 결과 종합 + 의사결정
  ├── Day 1-2: 결과 종합 매트릭스 작성
  ├── Day 3:   가중치 토론 + Go/No-Go 판단
  ├── Day 4:   최종 보고서 작성
  └── Day 5:   환경 정리 (terraform destroy)
```

### 12.2 필요 리소스

| 리소스 | 수량 | 역할 |
|--------|-----|------|
| **엔지니어** | 2명 | GCP 담당 1명 + AWS 담당 1명 |
| **엔지니어 (MTTR 테스트)** | 2명 | TEST-7.1용 블라인드 테스트 참여자 |
| **GCP 프로젝트** | 1개 | billing alert: $3,000 (예상 $1,500~$2,500) |
| **AWS 계정** | 1개 | billing alert: $3,000 (예상 $1,000~$2,000) |
| **테스트 기간** | 6주 | 환경 구성 1주 + 테스트 4주 + 종합 1주 |

### 12.3 비용 예산

| 항목 | GCP 예상 | AWS 예상 | 합계 |
|------|---------|---------|------|
| GPU/TPU 컴퓨팅 | $800~$1,200 | $600~$1,000 | $1,400~$2,200 |
| 서버리스 (Functions, Pub/Sub 등) | $50~$100 | $50~$100 | $100~$200 |
| 스토리지 (GCS, S3, DB) | $30~$50 | $30~$50 | $60~$100 |
| 네트워크 (egress) | $100~$200 | $50~$100 | $150~$300 |
| 기타 (모니터링, 시크릿 등) | $20~$50 | $20~$50 | $40~$100 |
| **합계** | **$1,000~$1,600** | **$750~$1,300** | **$1,750~$2,900** |

### 12.4 리스크 및 완화

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| GPU/TPU quota 부족 | Phase 2 지연 | 사전 quota 증가 요청 (최소 2주 전) |
| STS 전송이 예상보다 느림 | Phase 1 지연 | XLarge 테스트를 야간/주말에 실행 |
| Spot preemption으로 학습 중단 | Phase 2 데이터 손실 | on-demand로 먼저 baseline 확보 후 Spot 테스트 |
| Billing 반영 지연 | Phase 4 정확도 하락 | 48시간 대기 + Billing Export API 활용 |
| 테스트 환경 정리 실패 | 불필요한 비용 | terraform destroy 자동화 스크립트 + billing alert |
| WIF 설정 오류 | Phase 6 진행 불가 | 사전에 WIF 연결 검증 (Week 1에 포함) |
