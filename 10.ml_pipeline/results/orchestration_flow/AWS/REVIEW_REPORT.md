# AWS ML Platform Design Review Report

> **검토 일시**: 2026-03-04
> **검토 범위**: `designs-aws/` 디렉토리 18개 설계 문서 전체
> **검토 방법**: 문서 간 교차 참조(cross-reference) 기반 일관성 검증, 아키텍처 갭 분석, AWS 서비스 특성 기반 실현 가능성 점검

---

## 요약

| 분류 | 건수 |
|------|------|
| **E — 오류/불일치 (Error/Inconsistency)** | 8건 |
| **G — 아키텍처 갭 (Architecture Gap)** | 6건 |
| **I — 개선 제안 (Improvement)** | 6건 |

---

## E — 오류 / 불일치 (Error / Inconsistency)

### E1. Secrets Manager 사용 여부 — 3개 문서 간 모순

| 문서 | 내용 |
|------|------|
| `C4_Component_Layer_EP.md` (line 66) | "민감 정보 조회는 **EXP 컴포넌트로 이관**하였으며, EP에서는 ENV 기반 비암호화 구성값만 사용합니다" |
| `C4_Component_Layer_EXP.md` (line 39) | "**Environment Variables**: SERVICE_ACCOUNT_ROLE_ARN … 불필요한 Secrets Manager 호출 비용을 줄입니다" |
| `C4_Container_Layer.md` (line 40, 125) | `SM["Secrets Manager"]` + `EXPORTER -->│read config│ SM` |
| `Execution_Sequence_default.md` (line 181-182) | `EXP->>SM: Cross-Account Role ARN 조회` / `SM-->>EXP: credentials` |

**문제**: EP도 EXP도 Secrets Manager를 사용하지 않는다고 Component Layer에서 명시했는데, Container Layer와 Sequence Diagram에서는 여전히 Secrets Manager 참조가 남아 있음. **Secrets Manager가 아키텍처에서 실제로 필요한 서비스인지, 아니면 ENV로 완전 대체된 것인지** 결정 후 전 문서 일괄 업데이트 필요.

**권고 조치**:
- Secrets Manager를 제거한다면: Container Layer에서 `SM` 노드 및 관련 edge 삭제, Sequence Diagram에서 EP→SM, EXP→SM 호출 삭제
- Secrets Manager를 유지한다면: EP/EXP Component Layer의 "ENV만 사용" 설명 수정, 어떤 값을 SM에서 읽는지 명시

---

### E2. `ml-config` DynamoDB 테이블 — 스키마 미정의

| 문서 | 내용 |
|------|------|
| `C4_Component_Layer_EP.md` (line 66) | "DynamoDB **`ml-config`** 테이블을 조회하여 설정값을 병합" |
| `Topic_Specification.md` | DynamoDB 스키마 섹션에 `ml-config` 테이블 **없음** |
| `C4_Container_Layer.md` (line 39) | DynamoDB 테이블 목록에 `ml-config` **없음** |

**문제**: EP의 Configuration Initializer가 참조하는 `ml-config` 테이블이 Topic Specification(SSOT)에 정의되지 않았음.

**권고 조치**: `Topic_Specification.md`의 DynamoDB 테이블 스키마 섹션에 `ml-config` 테이블 추가, Container Layer 다이어그램의 DDB 노드 라벨에도 반영.

---

### E3. EventBridge Scheduler 삭제 정책 — 동일 문서 내 자기 모순

| 위치 | 내용 |
|------|------|
| `C4_Component_Layer_RT.md` 다이어그램 (line 66-67) | `if RETRYING → cancel scheduled task` / `delete schedule (best-effort)` |
| `C4_Component_Layer_RT.md` Component Details #4 (line 94) | "Cancel이 발생하더라도 **명시적으로 Schedule을 지우지 않고**, 상태 기반 무력화 패턴을 사용합니다" |
| `Run-level_State_Machine.md` (line 50) | "EventBridge Schedule **삭제 시도** (삭제 성공 여부와 무관하게 CANCELLING 전이)" |
| `Execution_Sequence_Cancel.md` (line 51) | `RT->>SCHED: EventBridge Schedule **삭제 요청**` |

**문제**: 동일 파일(`C4_Component_Layer_RT.md`) 내에서 다이어그램은 "삭제"를 보여주고, 텍스트 설명은 "삭제하지 않음"이라고 기술. Run-level SM과 Cancel Sequence도 "삭제"로 설계. **4개 중 3개가 "삭제(best-effort)"이므로 Component Details #4 텍스트가 오류**.

**권고 조치**: `C4_Component_Layer_RT.md` Component Details #4의 설명을 다음과 같이 수정:
> "RETRYING 상태에서 Cancel 발생 시 EventBridge Schedule을 best-effort로 삭제 시도합니다. 삭제에 실패하더라도 CANCELLING으로 전이하며, 이후 Schedule이 실행되어 Pipeline이 시작되면 상태 머신이 CANCELLING 상태를 확인하고 CANCELLED로 흡수합니다."

---

### E4. SMP Status Forwarder vs Pipeline Trigger — 명칭/역할 불일치

| 문서 | 내용 |
|------|------|
| `C4_Component_Layer_Triggers.md` | **"SMP Status Forwarder (Lambda)"** — 별도 독립 Lambda. SageMaker 상태 변경 이벤트 수신 → `ml.step.completed/failed` 발행 |
| `C4_Container_Layer.md` (line 28) | **"Pipeline Triggers (독립 Lambda × 4)"** — 4개만 표시, SMP Status Forwarder 없음 |
| `Topic_Specification.md` (line 123-124) | `ml.step.completed/failed` Publisher = **"Pipeline Trigger (Lambda)"** |
| 전체 Sequence Diagram | SageMaker 완료 → **"Pipeline Trigger"** 가 수신 후 발행 |

**문제**:
- Triggers Component Layer에서 SMP Status Forwarder를 **5번째 독립 Lambda**로 설계했으나, Container Layer는 4개만 인지
- Topic Specification과 Sequence Diagram은 "Pipeline Trigger"가 발행한다고 기술 (Forwarder 미언급)
- **실제 Lambda 개수가 4개인지 5개인지**, 그리고 각 Trigger Lambda가 "요청 수신"과 "완료 수신"을 겸하는지 아닌지 불명확

**권고 조치**:
- 5개 Lambda 구조라면: Container Layer를 `Pipeline Triggers (Lambda × 4) + SMP Status Forwarder (Lambda × 1)`로 수정, Topic Spec의 Publisher도 "SMP Status Forwarder"로 수정
- 4개 Lambda 구조(각 Trigger가 겸임)라면: Triggers Component Layer에서 SMP Status Forwarder를 Generic Trigger Template에 통합

---

### E5. Pipeline Trigger의 DynamoDB 쓰기 — Component Diagram 누락

| 문서 | 내용 |
|------|------|
| `Topic_Specification.md` (line 26-28) | `pipeline_execution_arn: string # **Pipeline Trigger가** StartPipelineExecution() **후 저장**` |
| `C4_Component_Layer_Triggers.md` | Mermaid 다이어그램에 DynamoDB 연결 **없음**. "Stateless Lambda"로 설계 |

**문제**: Topic Spec에 따르면 Pipeline Trigger가 `pipeline_execution_arn`을 DynamoDB `ml-run` 테이블에 저장하는데, Triggers Component 다이어그램에는 DynamoDB 접근이 전혀 표현되지 않음. "완벽한 무상태(Stateless)" 설명과도 모순.

**권고 조치**: Triggers Component 다이어그램에 `SMP_SUB -->|"save pipeline_execution_arn"| DDB_CLIENT[(DynamoDB)]` edge 추가. "Stateless" 설명도 "준-무상태(Near-Stateless)"로 수정하거나, `pipeline_execution_arn` 저장 역할을 다른 컴포넌트로 이관.

---

### E6. `ml-execution-plan` 테이블에 `pipeline_name` 필드 누락

| 문서 | 내용 |
|------|------|
| `Topic_Specification.md` (line 59) | `run_key 구성 요소: dataset_version + config_hash + **image_tag + pipeline_name**` |
| `Run-level_State_Machine.md` (line 12) | `run_key = dataset_version + config_hash + **image_tag + pipeline_name**` |
| `Topic_Specification.md` (line 43-60) | `ml-execution-plan` 스키마에 `image_tag` 있음, **`pipeline_name` 없음** |

**문제**: `run_key` 구성에 `pipeline_name`이 포함되지만, `ml-execution-plan` 테이블 스키마에 `pipeline_name` 필드가 정의되지 않음. Pipeline Trigger가 어느 SageMaker Pipeline을 실행할지 결정하는 데 필요한 정보.

**권고 조치**: `ml-execution-plan` 스키마에 `pipeline_name: string` 필드 추가.

---

### E7. CANCELLING 상태에서 `ml.step.completed` 수신 처리 미정의

| 문서 | 내용 |
|------|------|
| `Run-level_State_Machine.md` (line 63-64) | CANCELLING + `ml.step.failed` → CANCELLED (timestamp 무관, cancel 의도 우선) |
| `C4_Component_Layer_RT.md` (line 80) | `if state=CANCELLING → retry 없이 CANCELLED 흡수` (ml.step.failed 전용) |

**문제**: CANCELLING 상태에서 `ml.step.failed` 수신은 명시적으로 정의되어 있으나, **`ml.step.completed` 수신 처리는 어디에도 정의되지 않음**. StopPipelineExecution 호출 후에도 Pipeline이 이미 완료 중일 수 있는 Race Condition 시나리오:
1. Pipeline이 99% 완료된 시점에 Cancel 요청
2. StopPipelineExecution 호출 → Pipeline은 이미 SUCCEEDED
3. SageMaker 완료 EventBridge 이벤트 발행 → `ml.step.completed` 수신
4. CANCELLING + `ml.step.completed` → **미정의**

**권고 조치**: Run-level SM과 RT Component Layer에 CANCELLING + `ml.step.completed` 처리 추가:
- 옵션 A: CANCELLED로 흡수 (cancel 의도 우선 — `ml.step.failed`와 동일 정책)
- 옵션 B: COMPLETED로 전이 (이미 성공한 결과 보존)
- 어떤 정책이든 명시적 정의 필요

---

### E8. Cancel Sequence에서 StopPipelineExecution 동기 응답 표현 오류

| 문서 | 내용 |
|------|------|
| `Execution_Sequence_Cancel.md` (line 36) | `SMP-->>RT: execution status = Stopped` (동기 응답으로 표현) |

**문제**: AWS SageMaker `StopPipelineExecution` API는 **비동기 API**. 호출 시 즉시 acknowledgement를 반환하지만, Pipeline이 실제로 Stopped 상태가 되기까지는 시간이 걸림 (Executing → Stopping → Stopped). Sequence Diagram이 동기 응답처럼 그려져 있어 RT가 어떻게 "Stopped 확인"을 하는지 불명확.

**권고 조치**:
1. Cancel Sequence에 비동기 흐름 반영: `RT->>SMP: StopPipelineExecution()` → `SMP-->>EB: Pipeline Stopping/Stopped EventBridge 이벤트` → `EB->>TRG/RT: 상태 변경 수신` → `RT: CANCELLED 전이`
2. 또는 RT가 StopPipelineExecution 호출 후 즉시 CANCELLING으로 두고, SageMaker Stopped 이벤트를 Pipeline Trigger/SMP Status Forwarder가 수신 → `ml.step.failed`(cancel에 의한) 발행 → RT가 CANCELLING + failed를 CANCELLED로 흡수하는 기존 패턴에 위임하는 방식으로 정리

---

## G — 아키텍처 갭 (Architecture Gap)

### G1. RETRYING → STEP_RUNNING 전이 타이밍 — "유령 STEP_RUNNING" 구간

**현재 설계** (`Run-level_State_Machine.md` line 48):
```
RETRYING → STEP_RUNNING : 지연 schedule 생성 완료
```

**문제**: EventBridge Schedule이 생성된 시점(T1)에 STEP_RUNNING으로 전이하지만, Schedule이 실제로 실행되어 Pipeline이 시작되는 시점(T2)까지 지연 시간이 존재 (Exponential Backoff = 수 초~수 분). T1~T2 구간 동안:

- `state = STEP_RUNNING` (실제로는 아무것도 실행 중이 아님)
- `pipeline_execution_arn = null` (Pipeline 미시작)
- 이 구간에 Cancel 요청이 들어오면: CANCELLING 전이 후 Schedule이 실행되어 **불필요한 Pipeline이 시작**됨 (Pipeline Trigger가 "Stateless"이므로 state를 확인하지 않음)

**권고 조치**:
- 옵션 A: RETRYING 상태를 Schedule 실행 시점까지 유지 → Pipeline Trigger가 `pipeline_execution_arn` 저장 + `state=STEP_RUNNING` 전이를 담당
- 옵션 B: 현재 설계 유지 + Pipeline Trigger에 **state pre-check** 추가 (DynamoDB에서 state 확인 → CANCELLING/CANCELLED이면 Pipeline 미실행). "Stateless" 원칙은 완화되지만 불필요한 Pipeline 실행 방지

---

### G2. Pipeline Trigger가 SageMaker Step Outputs을 가져오는 경로 미정의

**현재 설계**: Pipeline Trigger (또는 SMP Status Forwarder)가 SageMaker EventBridge 상태 변경 이벤트를 수신하여 `ml.step.completed` 발행.

**문제**: SageMaker Pipeline의 EventBridge 네이티브 상태 변경 이벤트에는 `processed_uri`, `artifact_uri`, `model_version`, `metrics` 등의 **step-specific output 필드가 포함되지 않음**. Topic Spec의 `ml.step.completed` 스키마에는 이 필드들이 필수인데, Pipeline Trigger가 이를 어떻게 수집하는지 명시되지 않음.

**권고 조치**: Triggers Component Layer에 다음 중 하나를 명시:
- SageMaker `DescribePipelineExecution()` 또는 `ListPipelineExecutionSteps()` API 호출하여 outputs 수집
- SageMaker Pipeline 내에서 outputs을 S3 manifest에 기록하고, Trigger가 manifest를 읽기
- SageMaker Pipeline Parameter에 output S3 path를 convention으로 고정

---

### G3. SQS FIFO `MessageDeduplicationId` 전략 미정의

**현재 설계** (`Topic_Specification.md` 공통 규칙 #2):
> `MessageGroupId = run_id` (동일 run의 이벤트 순서 보장)

**문제**: SQS FIFO Queue는 `MessageDeduplicationId`도 필요 (content-based dedup 비활성화 시). EventBridge → SQS FIFO 라우팅에서 dedup ID를 어떻게 생성하는지 정의되지 않음.

**권고 조치**:
- EventBridge Rule → SQS FIFO 라우팅 시 `MessageDeduplicationId`에 `event_id` (EventBridge가 자동 생성하는 UUID)를 사용하도록 명시
- 또는 SQS FIFO Queue에서 Content-Based Deduplication 활성화 (MessageBody 기반 SHA256 자동 생성)

---

### G4. DynamoDB `ml-lock` 테이블 정리(Cleanup) 메커니즘 부재

**현재 설계**: `ml-lock`은 `idempotency_key = project#run_key`로 중복 실행을 방지. Run이 완료/실패되어도 lock 레코드가 영구 보존.

**문제**:
- 동일 `run_key`로 재실행이 필요한 경우 (운영자 수동 재시도 후 run_key가 같은 새 요청) lock이 영구적으로 차단
- `ml-lock` 레코드가 무한 증가 → 스토리지 비용 + scan 성능 저하 (GSI가 없으므로 직접 영향은 적지만)
- `ml-processed-events`에는 TTL(30일)이 있으나, `ml-lock`에는 없음

**권고 조치**:
- `ml-lock` 테이블에 `ttl: int` 필드 추가 (DynamoDB TTL, run 완료 후 N일 경과 시 자동 삭제)
- 또는 Run 완료/실패 시 RT가 명시적으로 lock 삭제
- `ml-duplicate-events`, `ml-audit-events`에도 동일하게 TTL 정책 검토

---

### G5. DATA_SYNCING 실패 알림 패턴 불일치

| 실패 시나리오 | 알림 패턴 |
|-------------|----------|
| Step 실패 (train OOM 등) | RT → CloudWatch Logs (stdout JSON) → Metric Filter → Alarm → SNS → Slack |
| DATA_SYNCING 실패 | EP → CW 직접 알림 → Slack (`Execution_Sequence_default.md` line 79) |

**문제**: Step 실패는 `C4_Component_Layer_FailureHandling.md`의 클라우드 네이티브 패턴(구조화 로그 → Metric Filter)을 따르지만, DATA_SYNCING 실패는 EP가 CloudWatch에 직접 알림을 푸시. 알림 채널이 이원화되어 운영 복잡도 증가.

**권고 조치**: DATA_SYNCING 실패도 동일한 구조화 로그 → Metric Filter → Alarm 패턴으로 통일. 또는 EP 전용 에러 이벤트(`ml.data.sync.dead-letter`) 도입.

---

### G6. `error_code` 표준 분류 체계 부재

**현재 설계**: `ml.step.failed`에 `error_code` 필드가 있으나, `TIMEOUT`만 특수 처리(SKIP_RETRY)로 정의됨. Sequence Diagram에서 `OOM` 예시 사용.

**문제**:
- 표준 error_code 목록이 없음 (OOM, TIMEOUT 외 다른 코드는?)
- Retryable vs Non-retryable 분류 기준이 `retry_policy` 필드에만 의존하며, error_code 기반 자동 분류가 없음
- DATA_SYNCING의 error_code(`ACCESS_DENIED`, `TRANSFER_TIMEOUT`, `MANIFEST_INVALID`, `GCS_WRITE_ERROR`)는 GCP 문서 메모리에만 존재하고 AWS 문서에는 미정의

**권고 조치**: Topic Specification에 `error_code` Enum 정의 추가:
```yaml
error_codes:
  retryable: [OOM, RESOURCE_LIMIT, THROTTLED, TRANSIENT_ERROR]
  non_retryable: [TIMEOUT, MANIFEST_INVALID, SCHEMA_MISMATCH, PERMISSION_DENIED]
  data_sync: [ACCESS_DENIED, TRANSFER_TIMEOUT, S3_WRITE_ERROR, MANIFEST_INVALID]
```

---

## I — 개선 제안 (Improvement)

### I1. EventBridge Scheduler — 좀비 Schedule 정리 정책

One-time Schedule은 실행 후 자동 삭제되지만, **Cancel로 인해 실행되지 않고 삭제도 실패한 Schedule**은 좀비로 남을 수 있음.

**제안**:
- EventBridge Scheduler의 Schedule 이름에 `run_id`를 포함하여 추적 가능하게 함
- 주기적(일 1회) CloudWatch Events 기반 정리 Lambda: CANCELLED/FAILED/COMPLETED 상태 run의 잔여 Schedule 삭제

---

### I2. SQS FIFO Queue 구성 상세 — 큐 토폴로지 정의 필요

현재 설계에서 EventBridge Rule → SQS FIFO → Lambda 패턴이 반복 사용되지만, **큐 개수와 매핑**이 명시되지 않음.

**제안**: 이벤트 타입별 SQS FIFO Queue 매핑 테이블 추가:
```
| Queue Name                        | Source Event(s)                                  | Consumer Lambda |
|-----------------------------------|--------------------------------------------------|-----------------|
| ml-run-requested-q.fifo           | ml.run.requested                                 | EP              |
| ml-data-synced-q.fifo             | ml.data.synced, ml.data.sync.failed              | EP              |
| ml-preprocess-trigger-q.fifo      | ml.preprocess.requested                          | Preprocess TRG  |
| ml-train-trigger-q.fifo           | ml.train.requested                               | Train TRG       |
| ml-infer-trigger-q.fifo           | ml.infer.requested                               | Infer TRG       |
| ml-postprocess-trigger-q.fifo     | ml.postprocess.requested                         | Postprocess TRG |
| ml-step-completed-q.fifo          | ml.step.completed                                | RT              |
| ml-step-failed-q.fifo             | ml.step.failed                                   | RT              |
| ml-cancel-q.fifo                  | ml.run.cancel.requested                          | RT              |
```

---

### I3. Cross-Account EventBridge 라우팅 — Service Account 통보 경로 명확화

ML Account에서 발행되는 `ml.run.completed`, `ml.run.cancelled` 이벤트를 **Service Account의 Observability**가 어떻게 수신하는지 불명확.

**제안**: 다음 중 하나를 Container Layer에 명시:
- EventBridge Cross-Account Rule: ML Account EventBridge → Service Account EventBridge
- SNS Cross-Account Subscription
- CloudWatch Cross-Account Observability

---

### I4. Postprocess Lambda 타임아웃 결합 문제 — 명시적 해결책 선택

`Step-level_State_Machine_(postprocess).md` (line 70-75)에서 이미 인지된 이슈 (I1 태그). Lambda 15분 제한 vs ECS Task 장시간 실행 문제.

**제안**: 다음 중 하나를 선택하여 구체적 설계에 반영:
- **단기 (권장)**: Postprocess Trigger를 **비동기 ECS Task 호출 + EventBridge Callback 패턴**으로 변경. Lambda는 ECS RunTask만 호출하고 즉시 반환. ECS Task 완료 시 EventBridge 이벤트 발행 → 별도 Lambda가 수신하여 `ml.step.completed/failed` 발행
- **장기**: Step Functions Workflow로 전환

---

### I5. `ml-run` 테이블에 step별 상세 상태 필드 추가 검토

현재 `ml-run.current_step`과 `ml-run.state`로 전체 진행 상황을 추적하지만, 개별 step의 소요 시간, 시작/종료 시각, outputs URI 등은 `ml.step.completed` 이벤트 기록에만 존재.

**제안**: `ml-run` 테이블에 `step_results` Map 필드 추가하여 각 step의 결과를 인라인으로 보존:
```yaml
step_results:
  preprocess: {status: SUCCESS, processed_uri: "s3://...", duration_s: 120, completed_at: "..."}
  train: {status: SUCCESS, artifact_uri: "s3://...", model_version: "v3", duration_s: 3600, completed_at: "..."}
  infer: {status: RUNNING}
```
이를 통해 `ml.run.completed` 이벤트의 `steps_summary` 필드 생성이 용이해지고, 운영자 대시보드 조회 시 단일 DynamoDB GetItem으로 전체 run 상태를 확인 가능.

---

### I6. Cancel 시나리오에 DATA_SYNCING 상태 추가

현재 Cancel 흐름은 `STEP_RUNNING`과 `RETRYING` 상태만 처리. `DATA_SYNCING` 상태에서의 Cancel이 미정의.

**제안**: Run-level SM과 Cancel Sequence에 다음 추가:
- `DATA_SYNCING → CANCELLING`: Cancel 요청 수신 시 S3 Copy Lambda의 진행 중인 작업 중단 (best-effort) + CANCELLING 전이
- 또는 DATA_SYNCING은 비교적 짧은 작업이므로 완료까지 대기 후 CANCELLED로 전이하는 정책 명시

---

## 부록: 문서별 영향도 매트릭스

각 이슈가 영향을 미치는 문서 목록:

| 이슈 | Topic Spec | Container | Triggers | EP | RT | EXP | FailureH | Run SM | Step SM | Postprocess SM | Failure SM | Seq Default | Seq Cancel |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| E1 | | O | | O | | O | | | | | | O | |
| E2 | O | O | | O | | | | | | | | | |
| E3 | | | | | O | | | O | | | | | O |
| E4 | O | O | O | | | | | | | | | O | |
| E5 | O | | O | | | | | | | | | | |
| E6 | O | | | | | | | O | | | | | |
| E7 | | | | | O | | | O | | | | | O |
| E8 | | | | | | | | | | | | | O |
| G1 | | | O | | O | | | O | | | O | | |
| G2 | O | | O | | | | | | | | | | |
| G3 | O | | | | | | | | | | | | |
| G4 | O | | | | | | | | | | | | |
| G5 | | | | O | | | O | | | | | O | |
| G6 | O | | | | | | | | | | | | |

---

> **다음 단계**: 각 이슈의 우선순위를 결정하고, E(오류) 항목부터 해당 문서에 반영하는 것을 권장합니다.
