# C4 Component Layer - Execution Planner (EP) 리뷰

**작성일**: 2026-02-28
**대상**: `v3/C4_Component_Layer_EP.md`
**관점**: 설계 오류(Errors), 과잉 설계(Over-engineering), 개선점(Improvements)

---

## ❌ 설계 오류 (Design Errors) & 타당성 검증

### [E1] 첫 번째 Step(Preprocess) 발행 주체의 정보 불일치 (Eventarc 연동 오류)
- **설명**: `v3/C4_Component_Layer_EP.md` 다이어그램에서, STS의 Sync 작업이 완료되었을 때 `ml.data.synced` 이벤트를 받아 `Staging Orchestrator`가 처리한 후 `Pub/Sub Publisher Client`를 통해 `ml.preprocess.requested`를 발행하도록 그려져 있습니다.
- **오류 검증**: 이전 v3(DataSync_Failure 제거, Exce_default 통합 병합 등) 리뷰 과정에서 논의된 바에 따르면, STS Sync 작업의 성공/실패 여부는 Cloud Storage 이벤트 기반 Eventarc 트리거 또는 STS Job 완료 알림을 통해 전달됩니다. 현재 설계도상 `EB_Sync`에서 `STG_ORCH`로 메시지가 들어오지만, Firestore의 Run State 상태 전이(RUNNING으로 변경) 없이 바로 Step Trigger를 날리는 구조입니다. EP는 Planning까지만 역할이 정의되어야 하는데, **"실행 중인 상태 트리거 발동"** 권한을 Run Tracker가 아닌 EP가 가져감으로써 Run Tracker와의 **권한 분리 원칙 위반 및 상태 머신 우회** 오류가 발생합니다.
- **올바른 아키텍처**: STS 완료 이벤트(`ml.data.synced`)의 구독자는 EP가 아니라 **Run Tracker(RT)**여야 합니다. RT가 DATA_SYNCING 상태를 IN_PROGRESS (첫 번째 step)로 전이시키고 `ml.preprocess.requested`를 발행하는 것이 State Machine 아키텍처에 부합합니다.

---

## ⚙️ 과잉 설계 (Over-engineering) & 타당성 검증

### [O1] `duplicate_events` 컬렉션을 위한 별도의 Audit Logger 컴포넌트
- **설명**: `Optimistic Lock Manager`가 트랜잭션 충돌(Already Exists)을 감지했을 때, 중복 이벤트를 무시하지 않고 `Duplicate Audit Logger` 컴포넌트를 통해 별도의 `duplicate_events` Firestore 컬렉션에 문서를 쓰는 로직이 있습니다.
- **과잉 설계 검증**: 락 획득 실패는 Pub/Sub 메시지 처리 중 흔하게 일어나는 at-least-once 전달(중복 전송)의 결과이거나 클라이언트 측의 단순 재요청입니다. 이를 위해 별도의 I/O 리소스를 소모하여 영구 저장소에 Insert 쿼리를 날리는 것은 시스템 부하를 가중시킵니다.
- **올바른 아키텍처**: 중복 요청 처리는 단순히 **HTTP 응답 분기(또는 Worker의 ACK 및 조기 리턴)** 로 처리하고, Cloud Logging 도구를 통해 `logger.info("Duplicate run request ignored: {run_key}")` 형태로 표준 출력(stdout)만 남겨 로그 싱크로 수집하는 것으로 충분합니다. `AUDIT_LOG` 컴포넌트 및 Firestore Write 로직은 삭제(간소화)해야 합니다.

---

## 💡 개선점 (Improvements) & 타당성 검증

### [I1] Config Resolver와 Run-Key Generator의 파이프라인 통합
- **설명**: 현재 다이어그램은 `Config Resolver`가 Firestore에서 설정을 읽고 해싱한 뒤, `Run-Key Generator`로 넘겨 조합하는 두 개의 분리된 컴포넌트를 정의하고 있습니다.
- **개선 검증**: 두 기능의 분리가 명확해 보일 수 있으나, 단일 Run 인입 과정에서 설정 조합과 Key 생성은 분할할 이유가 없는 순차적 파이프라인(동기 로직)입니다. 하나의 `Configuration Initializer` 클래스 내부 메서드로 병합하면 코드 가독성이 올라가고 불필요한 객체 주입 계층이 줄어듭니다.

---

## 요약 (권고안)
Execution Planner 단일 책임 원칙에 맞추어 **실행 파이프라인 시작(`ml.preprocess.requested` 발행) 책임을 Run Tracker로 이전(E1)**해야 합니다. 또한, 중복 로깅을 위한 Firestore 쓰기 로직(O1)을 제거하여 클라우드 네이티브한 로깅으로 되돌려 성능을 개선할 것을 권고합니다.
