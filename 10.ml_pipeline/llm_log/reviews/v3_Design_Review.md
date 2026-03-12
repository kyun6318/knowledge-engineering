# v3 설계 종합 리뷰

**작성일**: 2026-02-28
**대상**: v3 설계 파일 13개 전체
**관점**: (1) 설계 오류, (2) 과잉 설계, (3) 개선점

---

## 우선 수정 권고 순서

| 순위 | ID | 유형 | 요약 | 영향도 |
|---|---|---|---|---|
| 1 | E2 | 설계 오류 | CANCELLING + retry 진입 — 운영 안전성 | ⚠️ HIGH |
| 2 | E3 | 설계 오류 | VXP 고아 job 미취소 — 데이터 오염 위험 | ⚠️ HIGH |
| 3 | E1 | 설계 오류 | retry_policy 필드 SSOT 불일치 | ⚠️ HIGH |
| 4 | E4 | 설계 오류 | DATA_SYNCED 상태명 다이어그램 불일치 | ⚠️ MEDIUM |
| 5 | E5 | 설계 오류 | execution_plan에 image_tag 누락 | ⚠️ MEDIUM |
| 6 | O1 | 과잉 설계 | force=true 미완성 기능 SM 언급 | ⚠️ MEDIUM |
| 7 | O2 | 과잉 설계 | EP의 WIF 토큰 직접 갱신 — 아키텍처 위반 | ⚠️ LOW |
| 8 | I1~I5 | 개선점 | 개선 검토 항목 | LOW |

---

## ❌ 설계 오류 (Design Errors)

---

### [E1] `retry_policy=SKIP_RETRY` 메시지 필드 vs Topic_Spec SSOT 불일치 ⚠️ HIGH

**발견 위치**: `Step-level_State_Machine_(preprocess).md`, `(train).md`, `(infer).md`, `(postprocess).md` — TIMED_OUT 상태
**참조 위치**: `Topic_Specification.md` — ml.step.failed 스키마

#### 문제 상세

Step-level SM 4개 파일의 TIMED_OUT 상태에서 `ml.step.failed` 발행 시 `retry_policy=SKIP_RETRY`를 메시지 페이로드에 포함하고 있다.

그러나 Topic_Specification.md(SSOT)는 명확히 선언한다:

> *"retry_policy: ml.step.failed 메시지에는 포함되지 않습니다. RT가 Firestore의 execution_plan.retry_policy를 조회하여 재시도 여부를 판단합니다."*

Topic_Spec 추가 설명:

> *"error_code=TIMEOUT 수신 시 기본 정책은 SKIP_RETRY"* → RT가 error_code를 보고 스스로 판단

#### 영향

RT 구현 시 메시지 필드에서 `retry_policy`를 읽는 코드가 생기면 Topic_Spec 규칙과 충돌한다. 구현 혼란 야기.

#### 수정 방법

Step-level SM 4개 파일의 TIMED_OUT 상태 `ml.step.failed` 페이로드에서 `retry_policy=SKIP_RETRY` 제거.
RT는 `error_code=TIMEOUT`을 수신하면 자체 로직으로 SKIP_RETRY를 적용.

---

### [E2] CANCELLING 상태 + `ml.step.failed`(사전 실패) → 재시도 진입 오류 ⚠️ HIGH

**발견 위치**: `Run-level_State_Machine.md` — CANCELLING 상태 전이 분기

#### 문제 상세

현재 설계:

```
CANCELLING --> FAILED : ml.step.failed 수신
  ★ step_failed.timestamp < cancel_requested_at
  → cancel 이전에 발생한 실패 (retry 정책 정상 적용)
```

운영자가 cancel을 요청한 상태(CANCELLING)에서, cancel 이전에 발생한 step 실패가 도착하면 → FAILED + retry 정책 적용이 이루어진다. 즉, **재시도가 발생**할 수 있다.

#### 왜 오류인가

- CANCELLING 상태는 "운영자가 명시적으로 run을 중단하겠다"고 결정한 상태
- step 실패 시각이 cancel 요청보다 이르더라도, 운영자의 cancel 의도는 유지됨
- 재시도 발생 → 사실상 cancel 요청이 무시되는 결과 초래

**실제 시나리오**:
step이 연속 실패 중 → 운영자 cancel 발행 → step 실패 이벤트 도착 → 재시도 → cancel 무시

#### 올바른 동작

CANCELLING은 **terminal-directed 상태**다. 이 상태에서 수신되는 모든 `ml.step.failed`는 이유와 무관하게 CANCELLED로 전이해야 한다 (retry 정책 적용 없음).

#### 수정 방법

CANCELLING + `ml.step.failed` 분기 단순화:

| 조건 | 현재 | 수정 후 |
|---|---|---|
| `step_failed.timestamp ≥ cancel_requested_at` | CANCELLED | CANCELLED (동일) |
| `step_failed.timestamp < cancel_requested_at` | FAILED + retry | **CANCELLED** (cancel 의도 우선) |

CANCELLING → FAILED 전이는 cancel API 자체 실패(cancel API timeout 등)에만 사용.

---

### [E3] TIMED_OUT 후 VXP Pipeline Job 미취소 → 고아 Job + spurious 이벤트 ⚠️ HIGH

**발견 위치**: `Step-level_State_Machine_(preprocess).md`, `(train).md`, `(infer).md` — TIMED_OUT 상태
(postprocess는 VXP를 사용하지 않으므로 해당 없음)

#### 문제 상세

현재 TIMED_OUT 상태 진입 후 흐름:

```
TIMED_OUT:
  → Firestore: timeout 저장
  → publish ml.step.failed {..., error_code=TIMEOUT}
  → [*] (상태 종료)
```

그러나 해당 step을 실행 중이던 **Vertex AI Pipeline Job은 여전히 실행 중**이다.
Vertex AI Pipeline은 독립 서비스로, Cloud Function의 timeout과 무관하게 계속 실행된다.

#### 문제 연쇄

1. VXP job이 TIMED_OUT 후 수 분~수십 분 내 완료 → 상태 변경 이벤트 발행
2. Pipeline Trigger가 해당 이벤트 수신 → `ml.step.completed` 발행 시도
3. 재시도가 이미 `attempt+1`로 진행 중 → 이전 `attempt=0` job의 완료 이벤트와 충돌
4. TRG가 어느 attempt 번호로 `ml.step.completed`를 구성할지 결정 불가
5. 두 VXP job이 동시에 GCS에 쓰기 가능 → **데이터 오염 위험**

#### 수정 방법

TIMED_OUT 상태에 VXP Pipeline Job cancel API 호출 추가:

```
TIMED_OUT:
  → Firestore: timeout 저장
  + Vertex AI PipelineJob.cancel(pipeline_job_id)  ← 추가
  → publish ml.step.failed {..., error_code=TIMEOUT}
  → [*]
```

`run.pipeline_job_id`가 Firestore에 이미 저장되어 있으므로 cancel 호출 가능.
Step-level SM 3개 파일(preprocess/train/infer) TIMED_OUT 상태에 적용.

---

### [E4] `DATA_SYNCED` 상태 — Run-level SM에 미정의 ⚠️ MEDIUM

**발견 위치**: `Execution_Sequence_default.md` vs `Run-level_State_Machine.md`

#### 문제 상세

`Execution_Sequence_default.md`에 다음과 같이 기술:

```
EP->>FS: 상태 업데이트 (DATA_SYNCED + gcs_dataset_uri)
```

그러나 `Run-level_State_Machine.md`에는 `DATA_SYNCED` 상태가 존재하지 않는다.
정의된 전이: `DATA_SYNCING → STEP_RUNNING` (중간 상태 없음)

두 다이어그램이 동일 시스템을 기술하므로 상태명은 일치해야 한다.

#### 수정 방법

`Execution_Sequence_default.md`의 `DATA_SYNCED` → `STEP_RUNNING`으로 수정 (Run-level SM 상태명과 일치).

---

### [E5] `execution_plan` 스키마에 `image_tag` 누락 ⚠️ MEDIUM

**발견 위치**: `Topic_Specification.md` — execution_plan 스키마
**참조 위치**: `Run-level_State_Machine.md` — run_key 구성

#### 문제 상세

Run-level SM에서 run_key 구성:

```
run_key = dataset_version + config_hash + image_tag + pipeline_name
```

그러나 execution_plan 스키마에는 `dataset_version`, `config_hash`만 존재한다.
`image_tag`, `pipeline_name`이 없다.

Pipeline Trigger가 `PipelineJob.submit()` 시 container image를 지정해야 하는데, 어디서 조회할지 불명확하다.
`config_hash`가 config에서 파생된다면 `image_tag`는 config 내부에 있을 수 있지만, 명시적 필드가 없다.

#### 수정 방법

execution_plan 스키마에 `image_tag: string` 필드 추가.
`pipeline_name`은 `steps` 배열에서 추론 가능하므로 생략 검토.

---

## ⚙️ 과잉 설계 (Over-engineering)

---

### [O1] `force=true` 재실행 플래그 — 미완성 기능이 SM에 언급 ⚠️ MEDIUM

**발견 위치**: `Run-level_State_Machine.md` — IGNORED 상태

#### 문제 상세

현재 IGNORED 상태 Edge Case 기술:

```
IGNORED:
  ★ Edge Case:
  - 기존 run이 COMPLETED/FAILED 상태이면 duplicate_events 기록만 하고 run 종료
  - 예외: 기존 run이 FAILED 상태 + 운영자 명시적 재실행 플래그(force=true) 제공 시
    → lock 해제 후 신규 run 허용
```

`force=true` 플래그는:
- RunAPI 스키마에 정의되어 있지 않음
- 관련 Sequence Diagram 없음
- lock 해제 프로세스 미정의

설계 불완전한 기능을 SM에 언급하는 것은 "현재 기능"인지 "미래 기능"인지 불명확하여 구현 혼란을 야기한다.

#### `force=true` 완전 구현을 위해 필요한 작업

1. RunAPI에 `force: boolean` 파라미터 추가 및 스키마 갱신
2. EP의 lock 해제 로직 정의
3. 별도 sequence diagram 작성

#### 권고

현재 설계 범위에서 `force=true` 제거 후 Run-level SM 하단에 다음 주석으로 이동:

```
<!-- Future Work: FAILED 상태 run 강제 재실행 (force=true) -->
<!-- 필요: RunAPI force 파라미터, lock 해제 로직, 전용 sequence diagram -->
```

---

### [O2] ACCESS_DENIED 재시도 시 EP의 WIF 토큰 갱신 — 아키텍처 불일치 ⚠️ LOW

**발견 위치**: `Execution_Sequence_DataSync_Failure.md` — ACCESS_DENIED 재시도 분기

#### 문제 상세

현재 sequence:

```
EP->>STS: WIF 토큰 갱신 요청 (AssumeRoleWithWebIdentity 재시도)
```

WIF(Workload Identity Federation) + STS AssumeRoleWithWebIdentity는 **STS(Storage Transfer Service) 자체**가 job 실행 시 내부적으로 처리하는 메커니즘이다.
EP는 STS transfer job을 제출(trigger)할 뿐이며, WIF 토큰 갱신을 직접 수행하지 않는다.

EP가 `AssumeRoleWithWebIdentity`를 직접 호출하는 것은 GCP STS(Storage Transfer Service)와 AWS STS(Security Token Service)의 역할을 혼동한 것이다.

#### 실제 구조

ACCESS_DENIED 시 EP가 해야 하는 것: **transfer job 재제출**.
STS 서비스가 새 job 실행 시 WIF를 통해 자동으로 AWS 임시 자격증명 재취득.

#### 수정 방법

"WIF 토큰 갱신 요청" 단계 제거.
다음으로 단순화:

```
EP->>STS: transfer job 재실행
Note over STS: STS가 내부적으로 WIF 재인증
```

---

## 💡 개선점 (Improvement Points)

---

### [I1] Postprocess 동기 HTTP 호출의 timeout 결합 문제 ⚠️ MEDIUM

**발견 위치**: `Step-level_State_Machine_(postprocess).md`, `C4_Container_Layer.md`

#### 현황

- Postprocess Trigger(Cloud Function) → EXP(Cloud Run Job) 동기 HTTP 호출
- Cloud Function 최대 timeout: 60분 (2nd gen)
- Cloud Run Job 최대 실행 시간: 24시간
- 대용량 아티팩트(수십 GB 모델)의 GCS→S3 전송 시 60분 초과 가능

#### 문제 연쇄

1. CF timeout → TIMED_OUT → `ml.step.failed(TIMEOUT, SKIP_RETRY)`
2. EXP Cloud Run Job은 여전히 실행 중 (CF timeout과 무관)
3. 재시도 정책상 SKIP_RETRY → run FAILED
4. EXP가 성공적으로 S3 업로드 완료해도 시스템은 FAILED 처리
5. 다음 시도에서 새 EXP Job이 기동되면 이전 Job과 동시 실행 → S3 중복 업로드 위험

#### 권고

- **단기**: EXP 자체 timeout을 CF timeout보다 짧게 설정 → EXP가 먼저 timeout 처리 후 오류 응답 → CF가 명확한 실패 응답 수신
- **장기**: 비동기 패턴 도입 고려 (CF → EXP 트리거 → Pub/Sub 콜백) — 대용량 아티팩트 환경 대비

---

### [I2] `run.attempt` Firestore 필드 리셋 시점 미문서화 ⚠️ LOW

**발견 위치**: `Topic_Specification.md` — run 스키마

#### 현황

- `run.attempt`: 현재 step의 재시도 횟수 (Firestore 저장)
- step 전환(preprocess→train→infer→postprocess) 시 `attempt = 0`으로 리셋되어야 함
- 리셋 시점: RT가 `ml.{next_step}.requested`를 발행할 때 동시에 Firestore 업데이트 필요
- 현재 어느 파일에도 명시되지 않음

#### 권고

RT의 step 전환 처리 시 `run.attempt = 0` 리셋을 명시.
추가 위치: `Run-level_State_Machine.md` STEP_RUNNING 진입 시 또는 `Topic_Specification.md` run 스키마 노트.

---

### [I3] 수동 재처리(AWAITING_MANUAL → RETRY_ELIGIBLE) attempt 관리 미정의 ⚠️ LOW

**발견 위치**: `Failure_Handling_State_Machine.md`

#### 현황

```
AWAITING_MANUAL --> RETRY_ELIGIBLE : 수동 재처리 트리거
```

운영자가 DLQ 확인 후 수동 재처리를 요청할 때, `attempt` 카운터는 이미 `max_attempts`에 도달한 상태다.
RETRY_ELIGIBLE 진입 후:

```
retry_check: attempt >= max_attempts → DLQ_ROUTING (즉시 재진입 → 무한루프)
```

#### 권고

수동 재처리 진입 시 `attempt` 카운터 리셋 명시.
추가 검토: 운영자 재처리 전용 별도 상한 정의 (예: `manual_retry_max`).

---

### [I4] `audit_events` 컬렉션 C4 레이블 누락 ⚠️ LOW

**발견 위치**: `C4_Container_Layer.md` — Firestore 노드

#### 현황

```
FS["Firestore\n(run / execution_plan / lock / duplicate_events)"]
```

`Topic_Specification.md`에 `audit_events` 컬렉션 정의가 완료되어 있으나 C4 레이블에 누락되어 있다.

#### 권고

C4 Firestore 레이블 수정:

```
FS["Firestore\n(run / execution_plan / lock / duplicate_events / audit_events)"]
```

---

### [I5] `Execution_Sequence_default.md` DATA_SYNC 실패 분기 단순화 ⚠️ LOW

**발견 위치**: `Execution_Sequence_default.md`

#### 현황

- default sequence의 DATA_SYNC 실패 시 즉시 FAILED 처리로 단순 표시
- 실제로는 에러 코드별 재시도 로직이 존재 (`Execution_Sequence_DataSync_Failure.md` 참조)
- 두 파일 간 동작 기술이 불일치하여, 단순화가 의도적인지 불명확

#### 권고

default sequence의 DATA_SYNC 실패 분기에 참조 주석 추가:

```
Note over EP: DATA_SYNC 실패 → 에러 코드별 재시도 가능
Note over EP: 상세 시나리오: Execution_Sequence_DataSync_Failure.md 참조
```

---

## 제외 항목

**STS Eventarc label 전파**: 플랫폼(GCP STS Eventarc) 수준의 구현 세부사항으로, 설계 오류가 아닌 플랫폼 검증 필요 사항. 현재 설계 범위에서 제외.

---

# v3 설계 2차 추가 리뷰 (2026-02-28)

**작성일**: 2026-02-28
**대상**: v3 설계 파일 (1차 리뷰 반영 및 일부 간소화 이후 상태)
**관점**: (1) 설계 오류, (2) 과잉 설계, (3) 개선점 (타당성 검증 완료)

---

## 2차 우선 수정 권고 순서

| 순위 | ID | 유형 | 요약 | 영향도 |
|---|---|---|---|---|
| 1 | E1 | 설계 오류 | Postprocess SM 동작과 Sequence Diagram 간 불일치 | ⚠️ MEDIUM |
| 2 | E2 | 설계 오류 | Run-level SM의 CANCELLING + 실패 교차 시나리오 전이 누락 | ⚠️ MEDIUM |
| 3 | E3 | 설계 오류 | TIMED_OUT 시 VXP 파이프라인 실제 취소 로직 누락 | ⚠️ HIGH |
| 4 | O1 | 과잉 설계 | Run-level SM의 4-way step_transition 중복 | ⚠️ LOW |
| 5 | O2 | 과잉 설계 | Step-level SM의 구조적 중복 (Generic SM 병합 검토) | ⚠️ LOW |
| 6 | O3 | 과잉 설계 | DataSync_Failure 시퀀스 다이어그램 완전 중복 | ⚠️ LOW |
| 7 | I1 | 개선점 | EventBus 시각화 등 사용되지 않는 요소 명확화 표기 | LOW |
| 8 | I2 | 개선점 | 수동 재처리 진입 시 attempt 통제 명시 | LOW |

---

## ❌ 2차 설계 오류 (Design Errors) & 타당성 검증

### [E1] Postprocess State Machine-Sequence 간 검증(Verify) 시점 불일치 ⚠️ MEDIUM
- **설명**: Sequence Diagram(`Execution_Sequence_default.md`)에서는 `sync_target = both`일 때 모델 아티팩트 업로드 이후와 추론 결과 업로드 이후 각각 두 번의 `VERIFY` 단계를 수행합니다. 그러나 `Step-level_State_Machine_(postprocess).md`에서는 `ARTIFACT_SYNCING` 완료 후 `VERIFY`를 거치지 않고 바로 `RESULT_SYNCING`으로 전이하도록 되어 있어 문서 간 논리 구조가 어긋납니다.
- **타당성 검증(Validation)**: `Execution_Sequence_default.md` L182(`sync_target = both`) 설계 의도와 `Step-level_State_Machine_(postprocess).md` L12(`ARTIFACT_SYNCING --> RESULT_SYNCING`) 코드 전이 불일치 현황을 교차 대조하여 타당성을 입증했습니다.

### [E2] Run-level SM의 Cancel/Failure 교차 시나리오 전이선 누락 ⚠️ MEDIUM
- **설명**: `Run-level_State_Machine.md` 하단 주석에는 "CANCELLING 상태에서 ml.step.failed 수신 시 CANCELLED로 전이"라는 비즈니스 로직 정책이 명확히 적혀 있지만, 실제 다이어그램 노드에는 이와 관련한 이벤트 전이선 화살표가 그려져 있지 않습니다.
- **타당성 검증(Validation)**: 상태 다이어그램 파일 내부 전이 정의 확인 시 `CANCELLING --> CANCELLED : cancel 확인됨`만 존재하며 `ml.step.failed 수신` 이벤트 조건의 시각적 전이 경로는 명시적으로 누락되어 있음이 확인되었습니다. 타당성 검증을 통과했습니다.

### [E3] Pipeline TIMED_OUT 시 실제 Job 동작 제어 누락 ⚠️ HIGH
- **설명**: `TIMED_OUT` 발생 시 State Machine은 종료 상태로 넘어가버리나, 타임아웃의 원인이 된 실제 Vertex AI Pipeline Job에 대해 Stop/Cancel API 등을 호출하는 과정이 전혀 없습니다. 제어 불능 상태가 된 파이프라인이 뒤늦게 성공 이벤트를 트리거하면 현재 상태 머신 로직과 충돌하여 장애를 야기합니다.
- **타당성 검증(Validation)**: 모든 설계 문서를 교차 검증한 결과, VXP의 라이프사이클을 `TIMED_OUT` 이후 자발적으로 강제 소멸하는 로직이 다이어그램 단에 설계되어 있지 않아 타당성이 입증됩니다.

---

## ⚙️ 2차 과잉 설계 (Over-engineering) & 타당성 검증

### [O1] 상태 머신(Run-level)의 step_transition 4중 분기 중복 ⚠️ LOW
- **설명**: `step_transition` 이라는 choice 노드에서 뻗어나가는 4개의 선(preprocess, train, infer, postprocess)이 도착점(`STEP_RUNNING`)과 결과 동작(`publish ml.{next_step}.requested`) 측면에서 완전히 동일한 로직 구조를 보입니다. 단일 분기로 축약하고 문자열 변수화 하면 훨씬 직관적입니다.
- **타당성 검증(Validation)**: 4개의 분기가 구조적으로 동치 문맥임이 소스에서 확인되었으므로, 불필요한 복잡성을 줄이라는 이 지적은 논리적으로 타당합니다.

### [O2] Step-level State Machine 3개의 완벽한 구조적 중복 ⚠️ LOW
- **설명**: 전처리, 학습, 추론 등 3개 단계의 상태 머신이 진입(`SUBMITTED`), 진행(`IN_PROGRESS`), 종료(`SUCCEEDED`, `FAILED`, `TIMED_OUT`)까지 구조 프레임워크가 100% 동일합니다. 유지 보수를 위하여 단일 Generic Step SM으로 합칠 필요가 큽니다.
- **타당성 검증(Validation)**: 해당 파일 3개의 Mermaid 소스를 직접 Diff 대조한 결과, 상태 전이 네트워크와 연결관계가 완전히 동일함을 확인했습니다. 타당성 입증 완료.

### [O3] Execution_Sequence_DataSync_Failure.md의 설계 역할 중첩 ⚠️ LOW
- **설명**: 이 파일은 4가지 세부 장애사유를 보여줍니다. 그러나 그 목적지 및 처리 동작(Eventarc 발행 → Pub/Sub → EP 수신 → FAILED 에러 발생)은 이미 본류 플로우인 `Execution_Sequence_default.md` 내의 동기화 실패 블록에서 포괄하여 처리할 수 있습니다.
- **타당성 검증(Validation)**: 기본 모듈에서 이미 분기와 Eventarc 라우팅에러가 잡혀있음을 `Execution_Sequence_default.md` L74에서 확인했습니다. 단일 아키텍처 흐름 관점에서 과잉 분리가 맞습니다.

---

## 💡 2차 개선점 (Improvements) & 타당성 검증

### [I1] C4 EventBus 시각화의 불필요 정보 포함 LOW
- **설명**: C4 컨테이너 다이어그램 내에서 `Stream` (Kinesis/Kafka) 등 어떠한 시퀀스 다이어그램이나 실제 아키텍처 플로우와도 연관되지 않은 노드들이 혼선 유발합니다. 향후 확장성(Placeholder)이라면 점선 표기를 하여 구현 명세와 차이를 둬야 합니다.
- **타당성 검증(Validation)**: 나머지 12종 주요 시퀀스와 SM 플로우 다이어그램에서 해당 참여자의 Call을 전혀 찾을 수 없음에 기반한 합리적 지적입니다.

### [I2] Dead Letter (DLQ) 수동 처리에 대한 attempt 초기화 표기 누락 LOW
- **설명**: 운영자가 수동 조작으로 `AWAITING_MANUAL --> RETRY_ELIGIBLE` 트리거를 보낼 때 `attempt`가 `max_attempts`에 계속 도달해 있다면 곧바로 또 실패하여 DLQ로 또다시 전개될 수 있습니다. `attempt = 0` 등의 초기화 로직 표기가 빠져 있습니다.
- **타당성 검증(Validation)**: `Failure_Handling_State_Machine.md` 내의 전이 루프를 시뮬레이션 해 본 결과 카운터 관련 초기화 조건이 빠져 있다는 문제의 타당성을 입증했습니다.
