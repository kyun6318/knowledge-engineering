# AWS ML Platform 설계 문서

> AWS 서비스 기반 ML Pipeline 자동화 플랫폼의 아키텍처 설계 문서입니다.

## 이 플랫폼이 하는 일

데이터가 S3에 도착하면 **전처리 → 학습 → 추론 → 후처리(Cross-Account Export)** 4단계 ML Pipeline을 자동으로 실행하고, 실패 시 재시도·취소·수동 복구까지 처리하는 이벤트 기반 오케스트레이션 시스템입니다.

## 핵심 구성 요소

| 컴포넌트 | AWS 서비스 | 역할 |
|---------|-----------|------|
| **Run Request API** | API Gateway + Lambda | 외부 트리거 수신, 인증/인가, 이벤트 발행 |
| **Execution Planner (EP)** | Lambda | 설정 조회, run_key 중복 검사, 실행 계획 수립, Data Sync 트리거 |
| **Run Tracker (RT)** | Lambda | Step 완료/실패 수신, 상태 전이, 다음 Step 발행, 재시도 스케줄링 |
| **Pipeline Triggers** | Lambda × 4 | Step별 SageMaker Pipeline 실행 (postprocess는 EXP 직접 호출) |
| **Cross-Account Exporter (EXP)** | ECS Fargate Task | ML Account → Service Account S3로 아티팩트/결과 동기화 |
| **Event Bus** | EventBridge + SQS FIFO | 컴포넌트 간 비동기 메시지 전달 (run_id 기준 순서 보장) |
| **State Store** | DynamoDB | Run 상태, 실행 계획, 멱등성 락, 감사 로그 저장 |
| **ML Pipelines** | SageMaker Pipelines | 전처리/학습/추론 실행 (ECR 이미지 기반) |

## 3-Account 아키텍처

```
┌─────────────────┐    ┌─────────────────────────────┐    ┌──────────────────┐
│  Data Account   │    │        ML Account            │    │ Service Account  │
│                 │    │                               │    │                  │
│  S3 Dataset ────┼───►│  Lambda (EP/RT/TRG)           │    │  S3 Artifacts    │
│  EventBridge    │    │  SageMaker Pipelines          │◄───┼  S3 Results      │
│                 │    │  DynamoDB (상태 저장)           │    │  Serving API     │
│                 │    │  EventBridge + SQS FIFO       │    │  Service DB      │
│                 │    │  ECS Fargate (Exporter) ──────┼───►│                  │
└─────────────────┘    └─────────────────────────────┘    └──────────────────┘
```

- **Data Account**: 원본 데이터셋 저장, 데이터 도착 이벤트 발행
- **ML Account**: 모든 ML 워크로드 실행 (Lambda, SageMaker, DynamoDB 등)
- **Service Account**: 최종 모델/결과 저장, 서빙 API 운영

계정 간 통신은 **IAM Cross-Account AssumeRole**로 인증합니다.

## Run 실행 흐름 (Happy Path)

```
S3 데이터 도착
  → RunAPI (인증/검증)
    → EP (설정 조회 → 락 획득 → 실행 계획 수립)
      → Data Sync (S3 Cross-Account Copy)
        → Preprocess Trigger → SageMaker Pipeline
          → RT (완료 수신 → 다음 step 판단)
            → Train Trigger → SageMaker Pipeline
              → RT → Infer Trigger → SageMaker Pipeline
                → RT → Postprocess Trigger → EXP (Cross-Account Export)
                  → RT (모든 step 완료 → COMPLETED)
```

## Run 상태 머신

```
INTAKE → CONFIG_RESOLVING → LOCK_ACQUIRING → PLANNING
  → DATA_SYNCING → STEP_RUNNING ⇄ RETRYING
  → COMPLETED / FAILED / CANCELLED

특수 상태: REJECTED, IGNORED, CANCELLING, AWAITING_MANUAL, TERMINATED
```

- **RETRYING**: 실패 시 EventBridge Scheduler로 exponential backoff 지연 재시도
- **CANCELLING**: 운영자 Cancel 요청 시 SageMaker Pipeline 중지 후 CANCELLED 전이
- **AWAITING_MANUAL**: 최대 재시도 초과 후 운영자 수동 개입 대기

## 문서 구조 및 읽는 순서

### 1단계: 전체 구조 파악

| 문서 | 설명 |
|------|------|
| `C4_Container_Layer.md` | 전체 시스템 구조도 (Mermaid). **가장 먼저 읽으세요.** |
| `Topic_Specification.md` | 모든 이벤트 타입 명세 + DynamoDB 테이블 스키마 (Single Source of Truth) |

### 2단계: 상태 머신 이해

| 문서 | 설명 |
|------|------|
| `Run-level_State_Machine.md` | Run 전체 생명주기 상태 전이 |
| `Step-level_State_Machine_(generic).md` | 개별 Step(preprocess/train/infer) 상태 전이 |
| `Step-level_State_Machine_(postprocess).md` | Postprocess Step 전용 (SageMaker 없이 EXP 직접 호출) |
| `Failure_Handling_State_Machine.md` | 3-tier 실패 보상 흐름 (자동 재시도 → DLQ → 수동 복구) |

### 3단계: 실행 시퀀스 (Sequence Diagram)

| 문서 | 설명 |
|------|------|
| `Execution_Sequence_default.md` | 정상 실행 전체 흐름 (가장 상세한 시퀀스) |
| `Execution_Sequence_Cancel.md` | 취소 흐름 |
| `Execution_Sequence_Failure_Retry.md` | 실패 → 재시도 흐름 |
| `Execution_Sequence_Idempotency.md` | 중복 요청 처리 (멱등성) 흐름 |

### 4단계: 컴포넌트 상세

| 문서 | 설명 |
|------|------|
| `C4_Component_Layer.md` | 컴포넌트 문서 인덱스 (아래 7개 문서 목록) |
| `C4_Component_Layer_RunAPI.md` | Run Request API — 인증/인가, 스키마 검증 |
| `C4_Component_Layer_EP.md` | Execution Planner — 설정 병합, 멱등성 락, Data Sync |
| `C4_Component_Layer_RT.md` | Run Tracker — 상태 전이, 재시도 스케줄링, DLQ 발행 |
| `C4_Component_Layer_Triggers.md` | Pipeline Triggers — SageMaker 실행 팩토리 + Postprocess 경로 |
| `C4_Component_Layer_SMP.md` | SageMaker Pipelines — 전처리/학습/추론 파이프라인 구조 |
| `C4_Component_Layer_EXP.md` | Cross-Account Exporter — 멀티파트 업로드, Checksum 검증 |
| `C4_Component_Layer_FailureHandling.md` | 실패 보상 — 3-tier 구조, 수동 액션 처리기 |

### 부록

| 문서 | 설명 |
|------|------|
| `REVIEW_REPORT.md` | 설계 리뷰 결과 — 오류 8건, 아키텍처 갭 6건, 개선 제안 6건 |

## 주요 설계 원칙

- **이벤트 기반 (Event-Driven)**: 모든 컴포넌트는 EventBridge + SQS FIFO를 통해 비동기 통신
- **멱등성 (Idempotency)**: `idempotency_key = {run_id}_{step}_{attempt}`로 중복 처리 방지
- **상태 기반 제어**: DynamoDB에 저장된 Run 상태를 기준으로 모든 전이와 재시도 판단
- **Cross-Account 분리**: 데이터/ML/서비스 계정을 분리하여 보안 경계 확보
- **Stateless Lambda**: 각 Lambda는 상태를 DynamoDB에 위임하여 무상태 유지

## 이벤트 네이밍 규칙

`ml.{domain}.{action}` 형식으로 EventBridge `detail-type`에 사용합니다.

```
ml.run.requested        # Run 실행 요청
ml.preprocess.requested # 전처리 Step 실행 요청
ml.step.completed       # Step 완료
ml.step.failed          # Step 실패
ml.run.completed        # Run 전체 완료
ml.run.cancel.requested # 취소 요청
ml.dead-letter          # Application-level DLQ
```

## DynamoDB 테이블 요약

| 테이블 | 용도 | PK |
|-------|------|-----|
| `ml-run` | Run 상태 관리 | `run_id` |
| `ml-execution-plan` | 실행 계획 (steps, retry 정책 등) | `execution_plan_id` |
| `ml-lock` | 중복 실행 방지 락 | `idempotency_key` (= project#run_key) |
| `ml-duplicate-events` | 중복 요청 감사 기록 | `event_id` |
| `ml-audit-events` | 운영 이벤트 감사 (cancel 무시 등) | `event_id` |
| `ml-processed-events` | RT 멱등성 확인 (TTL 30일) | `idempotency_key` (= {run_id}\_{step}\_{attempt}) |
