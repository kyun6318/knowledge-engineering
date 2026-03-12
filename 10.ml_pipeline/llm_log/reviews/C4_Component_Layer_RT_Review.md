# C4 Component Layer - Run Tracker (RT) 리뷰

**작성일**: 2026-02-28
**대상**: `v3/C4_Component_Layer_RT.md`
**관점**: 설계 오류(Errors), 과잉 설계(Over-engineering), 개선점(Improvements)

---

## ❌ 설계 오류 (Design Errors) & 타당성 검증

### [E1] Postprocess Step 도중 Cancel 발생 시 VXP 종속성 오류
- **설명**: `CANCEL_HDLR` 컴포넌트가 `state=STEP_RUNNING`일 때 무조건 `VXP_CLIENT`를 호출하여 Vertex AI PipelineJob을 Cancel하도록 그려져 있습니다.
- **오류 검증**: 이전 리뷰에서 확정했듯, `postprocess` 단계는 VXP 파이프라인(Kubeflow)을 사용하지 않고 Cloud Run Job 기반의 EXP(Cross-Cloud Exporter) 컴포넌트로 직접 수행됩니다. 따라서 `postprocess` 실행 중일 때 Firestore의 `run.pipeline_job_id`는 명세서(`Topic_Specification.md`) 상 `null`입니다. 이 상태에서 무조건 VXP API를 호출하면 NullPointerException이나 API 예외가 발생합니다.
- **올바른 아키텍처**: Cancel Handler는 Firestore에서 Run 문서를 읽은 뒤, `pipeline_job_id`가 존재하는 경우에만 `VXP_CLIENT`를 호출해야 합니다. (또는 `current_step != postprocess` 확인 로직 추가)

---

## ⚙️ 과잉 설계 (Over-engineering) & 타당성 검증

### [O1] Cloud Tasks의 지연 재시도 Task에 대한 명시적 Cancel (삭제) 로직
- **설명**: 현재 `CANCEL_HDLR`는 Run이 `RETRYING` 상태일 경우 `CT_CLIENT`를 통해 예약된 Cloud Task(재시도 스케줄)를 직접 삭제(cancel)하도록 다이어그램에 명세되어 있습니다.
- **과잉 설계 검증**: Cloud Tasks에 예약된 작업을 삭제하려면, RT가 지연 스케줄을 생성할 때 반환받은 고유한 `task_name`을 Firestore Run 문서에 추가로 저장하고 관리해야 하는 상태 관리 비용이 발생합니다(현재 스키마에 존재하지 않음).
- **올바른 아키텍처**: 지연된 Task를 굳이 비싼 API 연산을 들여 삭제할 필요가 없습니다. Cancel API가 호출되면 Firestore `run.state`를 `CANCELLING/CANCELLED`로 변경하기만 하면 됩니다. 이후 시간이 지나 Cloud Tasks가 Trigger를 쏘더라도, Trigger(또는 상태 머신)가 최신 상태(`CANCELLED`)를 확인하고 즉시 무시(No-op)하고 ACK를 반환하면 그만입니다. 이렇게 "상태 기반 무력화" 패턴을 쓰면 구조가 훨씬 단순해집니다.

---

## 💡 개선점 (Improvements) & 타당성 검증

### [I1] Firestore 연산의 오버헤드 축소 (Transaction 통합)
- **설명**: 다이어그램의 절차를 보면 `IDEMP_GUARD`가 Firestore 저장, `PLAN_NAV`가 execution_plan 읽기, `STATE_MGR`가 상태 업데이트 저장을 수행하는 것처럼 나뉘어 표현되어 있어 다수의 I/O가 발생할 여지가 있습니다.
- **개선 검증**: 상태 머신의 전환은 ACID(원자성)가 생명입니다. 이 세 컴포넌트의 동작(Idempotency 확인 → Plan 읽기 → State/Output 업데이트)은 개별 I/O가 아니라 **"단일 Firestore Transaction"** 블록 묶음으로 설계 및 표기되는 것이 동시성 충돌 방지와 요금 최적화(I/O 감소) 측면에서 바람직합니다.

---

## 요약 (권고안)
Run Tracker 설계에서 **Postprocess(VXP Null 예외) 고려 누락(E1)** 코너 케이스를 방어 로직으로 추가해야 합니다. 또한 재시도 대기열에 대한 **명시적 Task 취소 로직(O1)**을 삭제(스케줄러 무시 패턴 도입)하여 시스템 복잡도를 크게 낮출 것을 권고합니다.
