# v3/C4_Component_Layer_Triggers 변경 내역 표

**작업일**: 2026-02-28
**관련 리뷰 파일**: `review/C4_Component_Layer_Triggers_Review.md`

| ID | 수정 대상 파일 | 수정 이유 | 수정 전 | 수정 후 |
|---|---|---|---|---|
| **E1** | `C4_Component_Layer_Triggers.md` | 파이프라인 제출 후 즉시 종료되는 Cloud Function 생명주기에 비동기 VXP 이벤트 리시버를 끼워넣는 아키텍처 오류 수정 | `Generic_Trigger_Template` 서브그래프 안에 `PS_CLIENT`가 포함되어 완료 알림을 같이 수신함 | 비동기 상태를 통지받는 수신기 컴포넌트(`VXP Status Forwarder`)를 물리적으로 완벽히 분리 |
| **O1** | `C4_Component_Layer_Triggers.md` | `execution_plan`이 Payload로 통째로 넘어옴에도 매번 환경설정을 확인하러 DB I/O를 발생시키는 무상태(Stateless) 워커 원칙 위배 수정 | `TPL_RES -.->\|"fetch config mappings"\| FS_CLIENT` 로 매번 I/O 발생 | `FS_CLIENT` 의존성 제거. 정적 환경 변수(`ENV`)와 Payload 스키마만으로 파라미터를 조립하도록 I/O 삭제 극도로 간소화 |
| **I1** | `C4_Component_Layer_Triggers.md` | 공통 모듈 구조에서 Preprocess/Train/Infer 특화 분기를 소프트웨어 설계 패턴(다형성)으로 명확히 표기 | `Pipeline Template Resolver` 라는 불명확한 분기 컴포넌트 네이밍 | Factory 패턴을 적용한 `Pipeline Strategy Factory` 로 명칭 변경 및 분기 책임을 전략 패턴으로 문서화 |
