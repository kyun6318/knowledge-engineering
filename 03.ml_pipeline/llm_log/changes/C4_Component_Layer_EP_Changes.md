# v3/C4_Component_Layer_EP 변경 내역 표

**작업일**: 2026-02-28
**관련 리뷰 파일**: `review/C4_Component_Layer_EP_Review.md`

| ID | 수정 대상 파일 | 수정 이유 | 수정 전 | 수정 후 |
|---|---|---|---|---|
| **E1** | `C4_Component_Layer_EP.md` | Data Sync 완료 후 Step 실행 트리거 권한을 Run Tracker(RT)가 가져가도록 권한/아키텍처 위반 오탈자 수정 | `STG_ORCH -->\|"sync success"\| PS_CLIENT -->\|"publish ml.preprocess.requested"\|` | 화살표 제거 및 주석 업데이트 ("Sync 성공 시는 RT가 처리" 명시) |
| **O1** | `C4_Component_Layer_EP.md` | 멱등성 락 획득 실패 시 불필요한 중복 저장을 수행하는 `Duplicate Audit Logger` 객체와 Firestore 쓰기 오버헤드 제거 | `LOCK_MGR -.->\|"Conflict"\| AUDIT_LOG -->\|"write duplicate_events"\| FS_CLIENT` | `LOCK_MGR -.->\|"Conflict (Already Exists)"\| ACK([Log & HTTP 409 / ACK])` 로 간략화 |
| **I1** | `C4_Component_Layer_EP.md` | 설정 해석과 런 키 생성을 동기적 순차 흐름으로 처리할 필요 없이 단일 Configuration 파이프라인으로 통합 | `CFG_RES` + `RUN_KEY_GEN` 별도 컴포넌트 | `CFG_INIT` (`Configuration Initializer`) 단일 컴포넌트로 병합 |
