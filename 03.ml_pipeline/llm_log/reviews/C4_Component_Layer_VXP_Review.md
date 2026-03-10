# C4 Component Layer - Vertex AI Pipelines (VXP) 리뷰

**작성일**: 2026-02-28
**대상**: `v3/C4_Component_Layer_VXP.md`
**관점**: 설계 오류(Errors), 과잉 설계(Over-engineering), 개선점(Improvements)

---

## ❌ 설계 오류 (Design Errors) & 타당성 검증

### [E1] Vertex AI State Notification 발생 주체의 논리적 오류
- **설명**: 다이어그램 하단부에서 `PP_WRITE --> VXP_Notifier`, `TR_REG --> VXP_Notifier` 와 같이 파이프라인 내부의 "특정 노드(Component)"가 명시적으로 알림 서비스로 Done 시그널을 쏘는 화살표 흐름으로 그려져 있습니다.
- **오류 검증**: GCP Vertex AI Pipelines의 내장 알림(Pub/Sub State Notification) 기능은 파이프라인 내부의 개별 노드가 완료될 때마다 발생하는 것이 아니라, **경량화된 PipelineJob 전체 단위의 상태 변화(SUCCEEDED, FAILED, CANCELLED)** 에만 발동합니다. 개별 노드에서 시그널을 보낸다는 표현은 Kubeflow 엔진의 인프라 레벨 알림 아키텍처를 오해한 로직입니다.
- **올바른 아키텍처**: 개별 노드(`PP_WRITE`, `IN_WRITE` 등)에서 뻗어나오는 화살표를 삭제하고, 각 Subgraph(Pipeline) 박스 전체를 그룹화하여 런타임 종료 시 파이프라인 컨텍스트 자체가 `VXP_Notifier`로 상태를 라우팅한다고 표기하는 것이 정확합니다.

---

## ⚙️ 과잉 설계 (Over-engineering) & 타당성 검증

### [O1] Gating 임계치 미달 시 "파이프라인 강제 실패(FAILED)" 반환 (MLOps Anti-pattern)
- **설명**: `Component Details`의 2번 항목에서 "Evaluator의 결과 Metric이 사전에 정의된 임계점(Threshold)을 넘는 경우에만 다음 Model Registry 단계로 통과시킵니다. **(미달 시 Pipeline 실패 반환)**"이라고 정의되어 있습니다.
- **과잉 설계 검증**: 학습된 모델의 성능이 Baseline을 넘지 못한 것은 "데이터의 통계적 특성이나 모델링 한계"일 뿐, 파이프라인 자체의 장애나 버그를 의미하지 않습니다. 이를 인위적으로 예외(Exception)를 던져파이프라인 상태를 `FAILED`로 종료시키면, 상위의 `Run Tracker`는 이를 시스템 오류로 인지하여 **재시도(Retry)를 수행하거나 DLQ로 보내버리는 등 완전히 잘못된 에러 핸들링**을 유발하게 됩니다.
- **올바른 아키텍처**: 임계치 미달 시 조건부 분기(Condition Node)가 `Model Registry Integrator` 실행을 건너뛰도록(Skip) 제어하고 파이프라인 자체는 정상적으로 완료(`SUCCEEDED`)되도록 두어야 합니다. 로그나 지표로만 판단 결과를 남기는 것이 MLOps의 올바른 Gating 처리 패턴입니다.

---

## 💡 개선점 (Improvements) & 타당성 검증

### [I1] Batch Prediction의 모델 참조 방식 최적화
- **설명**: Infer Pipeline 내부에 `IN_MODEL["Model Artifact Fetcher"]` 노드가 파이프라인 스코프 내에 존재합니다.
- **개선 검증**: 커스텀 컨테이너 환경이 아니라 표준 Vertex AI Batch Prediction Job을 쓴다면, Pipeline Parameter 수준에서 Model Registry ID(`projects/.../models/...@version`)를 그대로 전달할 수 있습니다. 굳이 파이프라인 런타임 내부에 Model의 GCS 물리적 URI를 Fetch하는 별도의 리소스(노드)를 둘 필요가 없습니다. 노드 수를 하나 줄여 런타임 오버헤드를 감소시킬 수 있습니다.

---

## 요약 (권고안)
VXP 설계에서 **Vertex AI Job Notification의 범위(E1)를 Pipeline 런타임 통째로 수정**하고, 학습 스텝 미달로 인한 **인위적 Pipeline Failure 반환 로직(O1)을 제거하여 Run Tracker의 재시도 오동작을 예방**할 것을 강력히 권고합니다.
