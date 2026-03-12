# C4 Component Layer - Failure Handling 리뷰

**작성일**: 2026-02-28
**대상**: `v3/C4_Component_Layer_FailureHandling.md`
**관점**: 설계 오류(Errors), 과잉 설계(Over-engineering), 개선점(Improvements)

---

## ❌ 설계 오류 (Design Errors) & 타당성 검증

### [E1] 수동 재처리(`MANUAL_INVOKER`)의 논리적 진입점 오류
- **설명**: 다이어그램에서 운영자가 `MANUAL_INVOKER`를 트리거하면, Firestore의 `attempt=0`으로 리셋한 뒤 "다시 `RETRY_ASSESS` (재시도 평가기)로 푸시한다"고 표시되어 있습니다.
- **오류 검증**: `RETRY_ASSESS`는 파이프라인 스텝이 막 "실패(`ml.step.failed`)"했을 때 오류 코드를 분석하고 백오프(지연시간) 연산을 수행하는 방어선 컴포넌트입니다. 수동 재실행은 이미 오류 원인이 해결된 상태에서 "바로 다시 시작"하기 위한 액션이므로, 지연 큐 연산기(`RETRY_ASSESS`)를 거치게 하는 것은 잘못된 이벤트 라우팅입니다.
- **올바른 아키텍처**: 수동 재처리는 에러 평가기를 탈 필요 없이 `attempt=0` 및 `state=STEP_RUNNING`으로 Firestore를 강제 업데이트 한 뒤, 곧바로 대상 파이프라인의 **실행 큐(`ml.{step}.requested`)에 메시지를 즉시 직행(Publish)** 시키는 우회로(Bypass)로 묘사되어야 합니다.

---

## ⚙️ 과잉 설계 (Over-engineering) & 타당성 검증

### [O1] 인프라 알림 시스템의 과도한 애플리케이션 컴포넌트화 (바퀴의 재발명)
- **설명**: 실패 알림을 보내기 위해 애플리케이션 내부에 `OBS_PUSH`, `ALERT_RENDER`, `MON_CLIENT`라는 3가지 별도 컴포넌트를 설계하였습니다.
- **과잉 설계 검증**: Google Cloud 환경을 사용하면서 애플리케이션 코드가 직접 메시지를 포맷팅하고 Cloud Monitoring/Slack API를 호출하는 릴레이 컴포넌트를 직접 개발하고 유지보수하는 것은 대표적인 클라우드 안티 패턴입니다.
- **올바른 아키텍처**: 다이어그램의 `Alert & Manual Action Tier` 안의 3개 송신 컴포넌트를 모두 통폐합/삭제해야 합니다. 컴포넌트는 단순히 구조화된 **에러 로그(stdout, JSON Payload)**를 찍고 `ml.dead-letter`로 이벤트만 쏘는 것으로 임무를 종료합니다. 알림 파싱과 Slack 연동은 **GCP Cloud Logging의 Log-based Alerting (또는 Eventarc 트리거 자동 연동)**이라는 GCP 내장 인프라 기능에 100% 위임하는 구조로 개선해야 코드가 획기적으로 줄어듭니다.

---

## 💡 개선점 (Improvements) & 타당성 검증

### [I1] DLQ 라우터의 단일 책임 원칙 (SRP) 강화
- **설명**: 현재 `DLQ_ROUTER`가 1) Firestore 상태 변경, 2) EventBus 쏠 발행, 3) 옴저버빌리티 푸시를 전부 지휘하고 있습니다.
- **개선 검증**: 상태 변경 자체는 Core Logic에 속하는 `STATE_MGR`가 해야 합니다(실제로 `C4_Component_Layer_RT.md`에서는 그렇게 묘사됨). `DLQ_ROUTER`는 순수하게 `ml.dead-letter`로 원본 메시지를 포워딩(라우팅)하는 책임만 지도록 화살표 관계를 단일화하면 `Component Details`의 설명과 완벽하게 부합합니다.

---

## 요약 (권고안)
Failure Handling 설계에서 불필요한 **수동 재처리의 지연큐 진입 논리 오류(E1)**를 다이렉트 실행으로 수정하고, 거대한 **커스텀 알림 발송 컴포넌트 군단(O1)을 제거하여 클라우드 네이티브 로깅 인프라로 대체**할 것을 강력히 권고합니다.
