# C4 Component Layer - Pipeline Triggers 리뷰

**작성일**: 2026-02-28
**대상**: `v3/C4_Component_Layer_Triggers.md`
**관점**: 설계 오류(Errors), 과잉 설계(Over-engineering), 개선점(Improvements)

---

## ❌ 설계 오류 (Design Errors) & 타당성 검증

### [E1] 단일 Cloud Function 컨테이너 내의 동기/비동기 책임 혼재 (Lifecycle Error)
- **설명**: `Generic_Trigger_Template` 내부에 파이프라인 제출용 컴포넌트(`VXP_SUB`)와 함께 Vertex AI의 완료 알림을 받아 `ml.step.completed`를 발행하는 `PS_CLIENT`가 같은 흐름도 안에 병렬로 묶여 있습니다.
- **오류 검증**: Cloud Function은 Ephemeral(일회성) 컴퓨팅 리소스입니다. `ml.{step}.requested` 이벤트를 받아 PipelineJob을 Submit하고 나면 해당 함수 인스턴스는 즉시 소멸(종료)해야 합니다. 이후 몇 시간 뒤에 완료되는 Vertex AI State Change 이벤트를 같은 논리적 단위 안에서 "구독(Subscribe)하여 처리"하는 것처럼 표현하는 것은 생명주기와 호출 컨텍스트에 대한 중대한 아키텍처 오류입니다.
- **올바른 아키텍처**: 함수 코드베이스가 하나일 수는 있어도, 컴포넌트 레벨에서는 **Pipeline Submitter (트리거 담당)** 역할과 **Vertex AI Status Handler (상태 수신 및 포워딩 담당)** 역할이 별개의 진입점(Entrypoint)을 가진 독립적인 컴포넌트로 완벽하게 분리되어 묘사되어야 합니다.

---

## ⚙️ 과잉 설계 (Over-engineering) & 타당성 검증

### [O1] Stateless 트리거의 불필요한 Firestore 연동 (Config Mappings)
- **설명**: `Pipeline Template Resolver` 컴포넌트가 파이프라인 템플릿 정보를 얻기 위해 `FS_CLIENT[(Firestore)]`에 쿼리하여 설정값을 가져온다고 명시되어 있습니다.
- **과잉 설계 검증**: Topic 명세서를 보면 트리거가 수신하는 `ml.{step}.requested` 이벤트 페이로드 트리에 이미 `execution_plan` 객체가 통째로 포함되어 있습니다. 또한, 운영 환경별 Kubeflow 템플릿 URI나 머신 스펙은 동적이 아니라 인프라 배포 시점의 정적 값(Environment Variables)에 가깝습니다. 매번 Step이 트리거될 때마다 Firestore I/O를 발생시키는 것은 응답 속도를 저하시키는 오버헤드입니다.
- **올바른 아키텍처**: Trigger 모듈은 NoSQL 의존성을 배제하고 **순수하게 상태가 없는(Stateless) 워커** 모델로 유지해야 합니다. 즉, Payload(`execution_plan`) + 환경 변수(ENV)의 단순 조합으로만 파라미터를 조립하도록 수정하여 Firestore Read를 없애는 것이 이상적입니다.

---

## 💡 개선점 (Improvements) & 타당성 검증

### [I1] Pydantic Factory Pattern을 통한 확장의 명시
- **설명**: 공통 템플릿(Generic) 하나로 3가지 Step을 모두 대응하는 아이디어는 훌륭합니다. 이 설계가 더 명확해지기 위해서는, `Message Decoder` 다음 단계에 각 step에 특화된 포맷을 뱉어내는 Factory / Strategy 패턴이 소프트웨어 아키텍처 컴포넌트로 표기되면 더 좋습니다.
- **개선 제안**: `Pipeline Template Resolver` 대신 `Pipeline Strategy Factory` 컴포넌트를 두어, 내부 로직이 단순한 if/else 분기가 아니라 `PreprocessStrategy`, `TrainStrategy` 등 다형성 인터페이스로 분할되어 조립된다는 점을 명시해주면 개발 명세서로서 가치가 높아집니다.

---

## 요약 (권고안)
`Trigger` 컨테이너 내에서 **Vertex AI 이벤트 수신기 역할을 밖으로 빼내어 분리(E1)**하고, **Firestore 조회 로직을 제거(O1)**하여 순수 함수 형태의 완벽한 Stateless Factory(I1) 형태로 설계를 고도화할 것을 권고합니다.
