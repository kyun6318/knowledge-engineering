# ML Platform Design Documents (GCP)

AWS 데이터 소스에서 시작하여 GCP 환경에서 ML 파이프라인(전처리 → 학습 → 추론 → 후처리)을 자동 실행하고, 결과물을 다시 AWS로 내보내는 **이벤트 기반 ML 오케스트레이션 플랫폼**의 설계 문서입니다.

---

## 시스템 개요

```
AWS Data Account          GCP ML Environment              AWS Service Domain
┌─────────────┐    ┌──────────────────────────────┐    ┌─────────────────┐
│ S3 Dataset   │───→│ Run API → Event Bus (Pub/Sub)│    │ S3 Artifacts    │
│ EventBridge  │    │   ↓                          │    │ S3 Results      │
└─────────────┘    │ Execution Planner (EP)        │    │ Serving API     │
                   │   ↓                          │    └────────▲────────┘
                   │ Pipeline Triggers (×4)        │             │
                   │   ↓                          │             │
                   │ Vertex AI Pipelines (VXP)     │             │
                   │   ↓                          │             │
                   │ Run Tracker (RT)              │             │
                   │   ↓                          │             │
                   │ Cross-Cloud Exporter (EXP) ──│─────────────┘
                   │                              │
                   │ Firestore (상태 저장)          │
                   └──────────────────────────────┘
```

### 핵심 흐름
1. AWS S3에 데이터가 도착하면 EventBridge → Run API로 실행 요청
2. **Execution Planner(EP)** 가 설정 조회, 멱등성 락 획득, 실행 계획 수립
3. 필요 시 S3 → GCS 데이터 동기화 (Storage Transfer Service)
4. **Pipeline Trigger**가 각 step을 Vertex AI Pipeline으로 실행
5. **Run Tracker(RT)** 가 step 완료/실패 이벤트를 수신하여 다음 step 진행 또는 재시도 결정
6. **Cross-Cloud Exporter(EXP)** 가 결과물을 AWS S3로 내보냄

---

## 문서 읽는 순서 (권장)

### 1단계: 전체 구조 파악

| 문서 | 설명 |
|------|------|
| **C4_Container_Layer.md** | 시스템 전체 아키텍처 (Mermaid 다이어그램). 모든 컴포넌트와 데이터 흐름을 한눈에 보여줌. **가장 먼저 읽을 것.** |
| **Topic_Specification.md** | Pub/Sub 토픽 명세 + Firestore 스키마. 모든 이벤트의 발행자/구독자/스키마 정의. 다른 문서의 **Single Source of Truth**. |

### 2단계: 실행 흐름 이해

| 문서 | 설명 |
|------|------|
| **Execution_Sequence_default.md** | 정상 실행 시퀀스 (데이터 도착 → 전처리 → 학습 → 추론 → 후처리 → 완료). 전체 흐름을 시간순으로 보여줌. |
| **Run-level_State_Machine.md** | Run의 전체 생명주기 상태 머신 (INTAKE → CONFIG_RESOLVING → LOCK_ACQUIRING → PLANNING → DATA_SYNCING → STEP_RUNNING → COMPLETED/FAILED/CANCELLED). |

### 3단계: Step 실행 상세

| 문서 | 설명 |
|------|------|
| **Step-level_State_Machine_(generic).md** | preprocess/train/infer step의 공통 상태 머신 (SUBMITTED → IN_PROGRESS → SUCCEEDED/FAILED/TIMED_OUT). |
| **Step-level_State_Machine_(postprocess).md** | postprocess step 전용 상태 머신. VXP 없이 Trigger가 EXP를 직접 동기 HTTP 호출하는 특수 경로. |

### 4단계: 예외 처리 흐름

| 문서 | 설명 |
|------|------|
| **Failure_Handling_State_Machine.md** | 실패 처리 상세 로직 (멱등성 확인 → 재시도 판단 → Cloud Tasks 지연 재발행 → DLQ → 수동 재처리). |
| **Execution_Sequence_Failure_Retry.md** | 실패 및 재시도 시퀀스 다이어그램. |
| **Execution_Sequence_Cancel.md** | 취소 시퀀스 다이어그램. 운영자가 실행 중인 run을 취소하는 흐름. |
| **Execution_Sequence_Idempotency.md** | 멱등성 시퀀스 다이어그램. 중복 요청 감지 및 처리. |

### 5단계: 컴포넌트 내부 설계

| 문서 | 설명 |
|------|------|
| **C4_Component_Layer.md** | 컴포넌트 레이어 문서 목차 (아래 7개 문서 인덱스). |
| **C4_Component_Layer_RunAPI.md** | Run Request API — 인증/인가 분리 전략, 요청 검증. |
| **C4_Component_Layer_EP.md** | Execution Planner — Config 조합, 멱등성 락, STS 트리거. |
| **C4_Component_Layer_RT.md** | Run Tracker — 상태 머신 전환, DLQ, 지연 큐 백오프 발행. |
| **C4_Component_Layer_Triggers.md** | Pipeline Triggers — 템플릿 기반 VXP 제출 팩토리 + Postprocess 경로. |
| **C4_Component_Layer_VXP.md** | Vertex AI Pipelines — 전처리/학습/추론 파이프라인 컴포넌트 구조. |
| **C4_Component_Layer_EXP.md** | Cross-Cloud Exporter — 사이즈 기반 멀티파트 업로드 라우팅 및 검증. |
| **C4_Component_Layer_FailureHandling.md** | 3-tier 실패 보상 및 수동 액션 처리기. |

---

## 핵심 컴포넌트

| 컴포넌트 | GCP 서비스 | 역할 |
|----------|-----------|------|
| **Run API** | Cloud Run | 진입점. 요청 검증, 인증/인가, `ml.run.requested` 발행 |
| **Execution Planner (EP)** | Cloud Function | 설정 조회, run_key 계산, 멱등성 락, 실행 계획 수립, 데이터 동기화 트리거 |
| **Run Tracker (RT)** | Cloud Function | step 완료/실패 이벤트 처리, 다음 step 진행, 재시도/DLQ 결정 |
| **Pipeline Triggers** | Cloud Function ×4 | step별 독립 트리거. Vertex AI Pipeline 제출 및 완료 이벤트 수신 후 `ml.step.completed/failed` 발행 |
| **Vertex AI Pipelines (VXP)** | Vertex AI | Kubeflow 기반 전처리/학습/추론 실행 |
| **Cross-Cloud Exporter (EXP)** | Cloud Run Job | GCS → AWS S3 아티팩트/결과 내보내기 (WIF 인증) |
| **Event Bus** | Cloud Pub/Sub | 모든 컴포넌트 간 비동기 메시징. ordering key = `run_id` |
| **State Store** | Firestore | run, execution_plan, lock, duplicate_events, audit_events 컬렉션 |

---

## 주요 설계 원칙

- **이벤트 기반 아키텍처**: 모든 컴포넌트는 Pub/Sub 토픽을 통해 느슨하게 결합
- **멱등성**: `idempotency_key = {run_id}_{step}_{attempt}` 로 중복 메시지 처리 방지
- **재시도**: Cloud Tasks 기반 지연 재발행 (exponential backoff: `2^attempt × base_delay`)
- **취소**: 운영자 → RunAPI → Pub/Sub → RT → Vertex AI Pipeline cancel API
- **크로스 클라우드**: AWS S3 ↔ GCS 양방향 데이터 이동 (STS 인바운드, EXP+WIF 아웃바운드)
- **관측 가능성**: Cloud Monitoring → Slack 알림, run summary 푸시

---

## Run 상태 흐름 요약

```
INTAKE → CONFIG_RESOLVING → LOCK_ACQUIRING → PLANNING
  ↓                                              ↓
REJECTED                              DATA_SYNCING (선택)
                                           ↓
                               STEP_RUNNING ←──── RETRYING
                              ↙     ↓      ↘         ↑
                        COMPLETED  FAILED  CANCELLING  │
                                     ↑        ↓       │
                                     │    CANCELLED    │
                                     └────────────────┘
```

---

## ML Step 실행 순서

```
preprocess → train → infer → postprocess
   (VXP)     (VXP)   (VXP)    (EXP 직접 호출)
```

- preprocess/train/infer: Pipeline Trigger가 Vertex AI Pipeline을 제출하고, 완료 이벤트 수신 후 `ml.step.completed` 발행
- postprocess: Pipeline Trigger가 Cross-Cloud Exporter를 **동기 HTTP 호출**하여 결과물을 AWS로 내보낸 뒤 `ml.step.completed` 발행 (Vertex AI 미사용)

---

## Mermaid 다이어그램 렌더링

모든 설계 문서는 Mermaid 문법으로 작성되어 있습니다. 아래 환경에서 렌더링할 수 있습니다:
- GitHub / GitLab 마크다운 뷰어 (자동 렌더링)
- VS Code + [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid) 확장
- [Mermaid Live Editor](https://mermaid.live)
