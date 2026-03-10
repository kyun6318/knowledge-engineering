# Phase 0: 기반 구축 + API 검증 + PoC (4~5주)

> **목적**: GCP API 기능 검증 + LLM 추출 품질 PoC + 인프라 셋업을 통합 수행.
>
> **standard.2 변경**:
> - [standard.1.1-12] 0-5-2에 Neo4j **connection pool 한도 확인** 태스크 추가 (R-4)
> - [standard.1.1-13] Batch API 수치 **계획 확정 전 즉시 확인** 강조 (R-5)
> - [standard.1.1-15] Phase 0→1 Go/No-Go 기준 **부분 통과 시 판단 기준** 추가 (R-15)
> - 기타: standard.1과 동일 (VAS 제거, HWP PoC, 법무 PII, Embedding 통일)
>
> **인력**: DE 1명 + MLE 1명 풀타임, 도메인 전문가 1명 파트타임

---

## 사전 준비 (Pre-Phase 0) — Blocking Dependencies

> Phase 0 시작 **2주 전**까지 완료 필요.

### NICE DB 접근 확보

```bash
□ NICE DB 접근 계약 상태 확인
  - 기존 계약 → API 접근 키 + 필드 + 호출 제한 확인
  - 신규 계약 → 협의 시작 (예상 2~4주)
□ NICE DB 테스트 환경 API 호출 가능 확인
□ NICE 업종코드 마스터 데이터 확보 (KSIC 대/중/소분류)
```

**판정**: 2주 전까지 미확보 시 → NICE 의존 태스크를 Phase 0 후반으로 연기, DART + 사업자등록 조회로 대체.

### 법무팀 PII 처리 방침 검토 요청 — Blocking

```bash
□ 법무팀에 PII 처리 방침 검토 요청 (Phase 0 시작 2주 전)
  - 검토 항목:
    ├─ 이력서 PII(이름, 연락처)를 외부 LLM API에 마스킹 전송 가능 여부
    ├─ 마스킹 없이 전송 가능한 조건 (개인정보 처리 동의 존재 시)
    ├─ Anthropic Data Processing Agreement 검토
    └─ 마스킹 적용 시 법적 리스크 해소 여부
  - 예상 소요: 1~3주
□ 법무 결론 도출 기한: Phase 0-4 시작 전 (Week 3)
```

**법무 지연 시 contingency**:
- 마스킹 적용 상태로 Phase 0~1 우선 진행 (Phase 0 PoC에서는 **수동 마스킹**으로 진행)
- 법무 허용 판정 시 마스킹 제거 옵션 적용
- 법무 불허 판정 시 시나리오 C(On-premise GPU) 전환 검토 (+4~8주 추가)

### GCP 프로젝트 사전 준비

```bash
gcloud projects create graphrag-kg --name="GraphRAG Knowledge Graph"
gcloud config set project graphrag-kg

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  bigquery.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  cloudfunctions.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  documentai.googleapis.com \
  storage.googleapis.com
# Note: Cloud Workflows API는 Phase 2에서 활성화

# 서비스 계정
gcloud iam service-accounts create kg-pipeline \
  --display-name="KG Pipeline Service Account"

SA=kg-pipeline@graphrag-kg.iam.gserviceaccount.com

for ROLE in storage.objectAdmin bigquery.dataEditor \
  secretmanager.secretAccessor run.invoker \
  monitoring.metricWriter logging.logWriter aiplatform.user; do
  gcloud projects add-iam-policy-binding graphrag-kg \
    --member="serviceAccount:$SA" \
    --role="roles/$ROLE"
done

# Artifact Registry
gcloud artifacts repositories create kg-pipeline \
  --repository-format=docker \
  --location=asia-northeast3

# GCS 버킷 + Object Versioning
gcloud storage buckets create gs://graphrag-kg-data \
  --location=asia-northeast3 \
  --uniform-bucket-level-access
gcloud storage buckets update gs://graphrag-kg-data --versioning

# BigQuery 데이터셋
bq mk --dataset --location=asia-northeast3 graphrag_kg
```

### [standard.1.1-13] Anthropic Batch API Quota — 계획 확정 전 즉시 확인

> **standard.2 변경**: "Phase 0 시작 전 확인"에서 "**지금 즉시** 확인 가능한 항목은 바로 확인"으로 강화.
> Anthropic 콘솔(console.anthropic.com)에서 현재 계정의 Tier, rate limit를 확인할 수 있다.

```bash
# === 즉시 확인 (계획 확정 전) ===
□ Anthropic 콘솔에서 현재 Tier 확인 → 결과: Tier ___
□ Claude Haiku 4.5가 Batch API 지원 모델인지 확인 → 결과: ___
□ 동시 활성 batch 수 한도 확인 → 결과: ___
□ 일일 요청 한도(RPD) 확인 → 결과: ___
□ Batch 결과 보관 기간 확인 (현재 29일) → 결과: ___
□ 확인 결과를 본 문서에 업데이트

# === 필요 시 (Phase 0 시작 3주 전) ===
□ Tier 업그레이드 또는 한도 증가 요청
  - 예상 필요: 동시 10+ batch, 일 50K+ 요청
  - Tier 업그레이드 소요 시간(1~2주) 감안
```

**확인 결과별 타임라인 보정**:
- 동시 ≥ 10: Phase 2-1을 3~4주로 유지
- 동시 5~9: Phase 2-1을 4~5주로 조정
- 동시 ≤ 4: Phase 2-1을 5~8주로 조정, 또는 Gemini Flash 병행
- Haiku 4.5 Batch 미지원: 일반 API 사용 시 비용 2배($1,500→$3,000), 또는 Gemini Flash 전환
- Tier 업그레이드 거부: 일일 처리 한도 내 순차 제출

### Pre-Phase 0 복합 지연 시나리오

> NICE DB(2~4주) + 법무 PII(1~3주) + Batch API Tier 업그레이드(1~2주)가 **동시에** 지연되는 최악 시나리오.

```
최악 시나리오: Pre-Phase 0 전체 지연 4주
  → Phase 0 시작이 4주 밀림
  → 총 타임라인: 31~37주

완화 전략:
  - NICE DB와 법무 PII를 동시에 요청 (병렬 처리)
  - Batch API quota는 콘솔에서 즉시 확인 가능 → 지연 원인에서 제거 [standard.1.1-13]
  - NICE DB 미확보 시 DART/사업자등록으로 대체하여 Phase 0 시작
  - 법무 PII 미결 시 마스킹 상태로 진행
```

### 사전 준비 체크리스트

```
□ GCP 프로젝트 API 활성화 완료
□ 서비스 계정 + ADC 설정
□ SDK 설치 및 버전 확인 → requirements-lock.txt 생성
□ GCS Object Versioning 활성화 확인

□ Document AI 프로세서: GCP Console에서 사전 생성 (코드 생성 금지)
  ├── OCR Processor → processor name 기록: ___
  └── Layout Parser → processor name 기록: ___

□ DS-NER-EVAL gold 데이터 라벨링 완료
  ├── 최소 10~20건 (한국어 이력서/뉴스)
  ├── 엔티티: (text, type) 쌍
  ├── 관계: (subject, predicate, object) 쌍
  └── 담당: ___ / 완료 기한: Phase 0 시작 D-2

□ 데이터셋 GCS 업로드
  ├── DS-PDF-SAMPLE (20~30 files, 10MB 미만, 5p 이하)
  ├── DS-LLM-EVAL (50~100 examples)
  ├── DS-EMBED-SAMPLE (1K~5K docs)
  └── DS-NER-EVAL (10~20 examples, 사전 라벨링)

□ 프롬프트 파일 준비 (short/medium 한국어·영어 쌍)

□ 법무팀 PII 검토 요청 완료
□ Anthropic Batch API quota 즉시 확인 완료 [standard.1.1-13]
```

---

## 0-1 ~ 0-4: standard.1과 동일

> Phase 0-1(GCP 환경 구성 3일), 0-2(API 검증 2일), 0-3(데이터 프로파일링 1주), 0-4(LLM PoC 1~2주)는 standard.1과 동일.
> 상세 내용은 `standard.1/01_phase0_validation_poc.md` 참조.

---

## 0-5. 인프라 셋업 (1주, 0-3과 병행) — Week 3-4

| # | 작업 | GCP 서비스 |
|---|---|---|
| 0-5-1 | Secret Manager 시크릿 등록 | Secret Manager |
| 0-5-2 | Neo4j AuraDB Free 인스턴스 생성 | Neo4j Console |
| 0-5-2a | **APOC Extended 지원 여부 즉시 확인** | Neo4j Console |
| 0-5-2b | **[standard.1.1-12] max concurrent connections 확인** | Neo4j Console |
| 0-5-3 | v10 Graph 스키마 적용 | Neo4j |
| 0-5-4 | Vector Index 설정 (768차원) | Neo4j |
| 0-5-5 | BigQuery 테이블 생성 (7개 — batch_tracking 포함) | BigQuery |
| 0-5-6 | Artifact Registry 레포 생성 | Artifact Registry |
| 0-5-7 | Industry 마스터 노드 준비 (KSIC 코드) | GCS + 스크립트 |
| 0-5-8 | Docker 베이스 이미지 빌드 | Cloud Build |

### [standard.1.1-12] Neo4j Connection Pool 한도 확인

```
□ AuraDB Free 인스턴스에서 max concurrent connections 확인
  - 일반적으로 Free: 3~5 concurrent connections
  - 확인 방법: Neo4j Browser에서 CALL dbms.showConnections()
  - 또는 Neo4j AuraDB 문서에서 플랜별 한도 확인

□ 결과에 따라 Phase 1 Cloud Run Jobs tasks 수 조정:
  - max connections ≤ 5: kg-graph-load tasks=3, kg-embedding tasks=4
  - max connections ≤ 10: kg-graph-load tasks=5, kg-embedding tasks=5
  - Professional 전환 후: 플랜에 따라 tasks 상향

□ Connection pool 관리 코드 추가 계획 확인:
  - retry with exponential backoff (base=1s, max=30s)
  - connection 재사용 (session per task, 사용 후 반환)
  - connection refused 시 Task 대기 후 재시도 (max 3회)
```

---

## 0-6. Phase 0 완료 의사결정 — Week 4-5

| 의사결정 | 판단 기준 | 입력 데이터 |
|---|---|---|
| **Embedding 모델** | 한국어 분별력 (Mann-Whitney U) | Phase 0-2 C2 + 0-4-5 비교 |
| **텍스트 추출 방법** | CER/WER + 비용/속도 매트릭스 | Phase 0-2 DOC vs MMD vs E2E |
| **LLM 모델 선택** | 품질·비용 비교 (Haiku vs Sonnet vs Gemini) | Phase 0-4-2 PoC |
| **PII 전략** | 법무 결론 + 마스킹 영향 | Phase 0-4-4 + Pre-Phase 0 법무 |
| **HWP 파싱 방법** | CER + 표 보존 + 비용 | Phase 0-4-7 |
| **LLM 호출 전략** | 단건 vs 묶음 품질/비용 | Phase 0-4-6 |
| **섹션 분할 전략** | 파싱 성공률 | Phase 0-4-1 |
| **Graph DB 플랜** | 예상 노드 수 계산 | Phase 0-3-8 |
| **Batch API 처리 계획** | quota 확인 결과 | Pre-Phase 0 확인 [standard.1.1-13] |

### [standard.1.1-15] Phase 0 → Phase 1 Go/No-Go 기준

| 기준 | 통과 조건 | 미달 시 조치 |
|------|-----------|-------------|
| **의사결정 확정률** | 9개 중 7개+ 확정 | 미확정 항목이 Phase 1 1-0~1-1에 직접 영향 시 → Phase 0 1주 연장 |
| **HWP 파싱 방법** | 3방법 중 1개+ CER ≤ 0.15 | 3개 모두 실패 → Phase 1에서 HWP 제외, DOCX/PDF만 처리. HWP 비율이 30% 이상이면 프로젝트 리스크 검토 |
| **LLM 추출 품질** | scope_type 정확도 > 60% (50건) | 60% 미달 → 프롬프트 재설계 1주 추가 |
| **Batch API quota** | 계획 실행 최소 조건 확인 | 미확인 시 Phase 1 진행, Phase 2 타임라인 미확정 |
| **Neo4j connection pool** | 한도 확인 + tasks 수 조정 완료 [standard.1.1-12] | 미확인 시 Phase 1-4에서 tasks=3으로 보수적 실행 |

### Phase 0 산출물 체크리스트

```
□ API 검증 결과 종합 리포트 (cost_log.jsonl + 검증 매트릭스)
□ LLM 추출 품질 PoC 리포트 (50건 결과)
□ HWP 파싱 품질 PoC 리포트 (10건, 3방법 비교)
□ 데이터 프로파일 리포트 (파일 형식, 중복률, OCR 비율)
□ 예상 노드 수 계산 + Neo4j 전환 계획 확정
□ Embedding 모델 비교 리포트 (text-embedding-005 vs gemini-embedding-001)
□ Anthropic Batch API quota 확인 결과 + 처리 계획 [standard.1.1-13]
□ Neo4j connection pool 한도 확인 결과 + tasks 수 결정 [standard.1.1-12]
□ 법무 PII 검토 결과 (또는 지연 시 contingency 적용)
□ 의사결정 문서 (위 9개 항목 확정)
□ Phase 0 → Phase 1 Go/No-Go 판정 [standard.1.1-15]
□ Neo4j 스키마 + Vector Index 설정 완료
□ BigQuery 테이블 생성 완료 (batch_tracking 포함)
□ Docker 베이스 이미지 빌드 완료
□ 이력서 원본 GCS 업로드 진행 중 (또는 완료)
```
