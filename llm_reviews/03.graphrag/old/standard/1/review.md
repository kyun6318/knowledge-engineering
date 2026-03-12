# GraphRAG GCP 통합 실행 계획 standard.1 — 리뷰

> 리뷰 대상: `03.ml-platform/plans/graphrag/standard.1-7months/` (6개 문서)
> 리뷰 일자: 2026-03-08
> 리뷰어: Claude
> 리뷰 관점: **실현 가능성**, **과도한 일정/기능**, **부족한 일정/기능**

---

## 총평

standard.1는 v2 리뷰의 16건 권장사항(R-1~R-16)을 **전수 반영**한 개선판이다. CRITICAL 2건(HWP 파싱, Neo4j 전환)과 HIGH 5건 모두 구체적 해결책이 기술되었고, 전체적인 계획 성숙도가 크게 향상되었다. 특히 Batch API 현실적 시간 계산, 파이프라인 레벨 checkpoint 전략, Phase 1 테스트 인프라 추가는 실행 가능성을 의미 있게 높였다.

다만 standard.1에서 새롭게 드러나는 **실현 가능성 리스크**, **과도한 설계/일정**, **부족한 설계/일정**을 아래 세 축으로 상세히 기술한다.

### v2 리뷰 반영 현황

| v2 권장 | 심각도 | standard.1 반영 | 반영 품질 |
|---------|--------|---------|-----------|
| R-1 HWP 파싱 PoC | CRITICAL | [standard.1-2] Phase 0-4-7에 3방법 비교 PoC 10건 | **충분** — CER, 표 보존, Docker 영향까지 기술 |
| R-2 Neo4j 전환 | CRITICAL | [standard.1-3] Phase 2 시작 전 필수 전환 + 마이그레이션 | **충분** — 노드 수 계산, APOC 절차, 비용까지 명시 |
| R-3 Batch API quota | HIGH | [standard.1-4] 제약사항 표 + Pre-Phase 0 사전 확인 | **충분** — 단, 일부 수치가 "확인 필요" 상태 |
| R-4 에러 복구 | HIGH | [standard.1-5] checkpoint + batch_tracking + OOM 대응 | **충분** — 코드 레벨 구현 예시 포함 |
| R-5 테스트 전략 | HIGH | [standard.1-6] Phase 1-6 테스트 인프라 신규 추가 | **충분** — regression test 설계까지 상세 |
| R-6 VAS/RAG 제거 | HIGH | [standard.2] 완전 제거, 이유 명시 | **충분** |
| R-7 타임라인 조정 | HIGH | [standard.1-7] 3~4주로 조정 + 현실적 계산 | **충분** |
| R-8 PII 법무 | MEDIUM | [standard.1-8] Pre-Phase 0에 법무 검토 추가 | **충분** — contingency 포함 |
| R-9 크롤링 법적 | MEDIUM | [standard.1-9] Pre-Phase 2에 법적 검토 체크포인트 | **충분** |
| R-10 백업 전략 | MEDIUM | [standard.20] GCS Versioning + Neo4j APOC + 자동 백업 | **충분** |
| R-11 한국어 토큰 비용 | MEDIUM | [standard.21] 한글 ×2.3배 보정, 비용 재계산 | **충분** — Cloud Run 상세 표 추가 |
| R-12 Embedding 모델명 | MEDIUM | [standard.22] text-embedding-005로 전 문서 통일 | **충분** |
| R-13 인력/직렬화 | MEDIUM | [standard.23] 크롤링 직렬화 + 인력 추가 옵션 명시 | **충분** |
| R-14 오케스트레이션 | LOW | [standard.24] Phase 1 Makefile, Phase 2 Workflows | **충분** |
| R-15 ML Distillation | LOW | [standard.25] Phase 3으로 분리 | **충분** |
| R-16 Egress 비용 | LOW | [standard.26] 상세 계산 + 보수적 추정 $3.6 | **충분** — 실제로 v2 예상보다 적음을 확인 |

> **16건 전수 반영, 반영 품질 모두 "충분" 이상.** v2→standard.1 리뷰 프로세스가 효과적으로 작동했다.

---

## 1. 실현 가능성 검증

### 1.1 [RISK-CRITICAL] Phase 1-1 전처리 모듈 2주 — 일정 과소 추정

- **현황**: Phase 1-1에서 2주(Week 5~7)에 9개 태스크를 완수하도록 계획:
  1. PDF 파서, 2. DOCX 파서, 3. HWP 파서, 4. 섹션 분할기, 5. 경력 블록 분리기,
  6. PII 마스킹(offset mapping), 7. SimHash 중복 제거, 8. JD 파서, 9. Docker + Cloud Run Jobs 등록
- **분석**:
  - DE 1명 + MLE 1명 = 2명 × 10일 = 20인일. 태스크당 평균 2.2인일
  - PII 마스킹(offset mapping 보존)과 SimHash 중복 제거는 각각 **알고리즘 설계 + 구현 + 테스트**에 최소 3~4일 필요
  - HWP 파서는 Phase 0-4-7에서 방법 확정 후에야 구현 시작 → Phase 0 결과 대기 의존성
  - Docker 이미지에 LibreOffice를 포함하면 빌드/디버깅에 추가 시간 소요 (이미지 ~1.5GB)
  - Phase 0의 PoC 코드를 Cloud Run Jobs용 프로덕션 코드로 **리팩토링하는 시간**이 미포함
- **리스크**: 2주 초과 시 Phase 1 전체(10~12주)의 여유가 소진되어 후속 단계에 연쇄 지연
- **권장**:
  - 전처리 모듈을 **3주**로 확장 (Phase 1 전체를 11~13주로 조정)
  - 또는 PII 마스킹을 Phase 0-4-4 PoC에서 프로덕션 수준으로 사전 구현하여 Phase 1 부담 감소
  - 기술 사전(2,000개) + 회사 사전 구축(1-1-8)은 0-3 프로파일링과 병행하여 사전 준비

### 1.2 [RISK-HIGH] Phase 0 Pre-Phase 의존성 병목 — 4개 Blocking 태스크 동시 지연

- **현황**: Pre-Phase 0에 4개 blocking dependency가 존재:
  1. NICE DB 접근 확보 (2~4주)
  2. 법무팀 PII 검토 (1~3주)
  3. GCP 프로젝트 사전 준비 (기술적, ~1일)
  4. Anthropic Batch API quota 확인 (1~2주)
- **분석**:
  - 1번과 2번은 외부 의존성으로 일정 통제 불가
  - NICE DB + 법무 PII가 동시에 지연되면 Phase 0 시작 자체가 3~4주 밀릴 수 있음
  - 계획에서는 각각의 지연 contingency는 있으나, **동시 지연의 복합 영향**은 미기술
- **권장**:
  - 최악 시나리오 일정: Pre-Phase 0 전체 지연 시 Phase 0 시작이 4주 밀림 → 총 타임라인 30~37주
  - NICE DB와 법무 PII 검토를 **동시에** 요청하여 병렬 처리 (이미 암묵적이나 명시 필요)
  - 법무 PII 지연 시 "마스킹 적용 상태로 진행" contingency는 적절. 다만 마스킹 모듈이 Phase 1-1에 위치해 있어 Phase 0 PoC에서는 **수동 마스킹**으로 진행해야 함을 명시

### 1.3 [RISK-HIGH] 인력 2명 체제에서 26~33주 연속 풀타임 — 번아웃 + 병목

- **현황**: Phase 0(4~5주) + Phase 1(10~12주) + Phase 2(12~16주) = **26~33주 연속 풀타임**
- **분석**:
  - DE 1명 + MLE 1명이 6~8개월 풀타임으로 하나의 파이프라인을 구축하는 것은 현실적이나 **번아웃 리스크**가 높음
  - Phase 1에서 DE와 MLE의 역할 분담이 암묵적 — 누가 파서를 만들고 누가 LLM 프롬프트를 튜닝하는지 불명확
  - Phase 2-1 전체 데이터 처리 3~4주는 Batch API 폴링/모니터링/dead-letter 대응으로 **야간/주말 대응** 필요 가능
  - "인력 추가 옵션" 언급은 있으나, 추가 인력의 **온보딩 시간**(2~3주)을 감안하면 Phase 2 시작 최소 3주 전 결정 필요
  - Phase 2-2 품질 평가에 "전문가 2인 × 200건" 필요 — 이 전문가의 **확보 시점**이 미명시 (비용 $5,840은 포함)
- **권장**:
  - Phase 1 완료 시점(Week 17)에서 인력 추가 여부 의사결정 추가
  - Phase 2-1 전체 데이터 처리 기간 중 "on-call 체계" 명시 (야간 자동 알림은 있으나 대응 SLA 부재)
  - Phase 1~2 사이에 **1주 버퍼** 확보 (현재는 Phase 1 완료 → 즉시 Neo4j 전환 → Phase 2 시작)
  - DE/MLE 역할 분담표 추가: 예) DE=파서/인프라/크롤링, MLE=프롬프트/품질/모델선택

### 1.4 [RISK-HIGH] Anthropic Batch API 미확정 수치 — 타임라인의 핵심 변수

- **현황**: 섹션 7 표에서 "동시 활성 batch 수: 기본 ~100 (확인 필요)", "일일 요청 한도: Tier에 따라 상이" 등 핵심 수치가 미확정
- **문제**:
  - 이 수치가 계획의 핵심 변수(동시 10 batch 가능 여부 → 처리 일수 결정)인데 "확인 필요"로 남아있으면 Phase 2 타임라인 계산의 신뢰성이 부족
  - Pre-Phase 0에 "사전 확인" 체크리스트는 있으나, **확인 실패 시 contingency가 추가됨** [R-3 반영]
  - 다만 Tier 업그레이드 거부 시의 대안(Gemini Flash 병행)은 **Gemini Flash의 KG 추출 품질 검증**이 Phase 0-4-2에서 수행되므로 실행 가능
- **권장**:
  - **즉시 확인** (계획 문서 작성 시점이 아닌 지금): Anthropic 콘솔에서 현재 Tier와 rate limit 확인 가능
  - 확인 결과를 Phase 0 시작 전이 아닌 **계획 확정 전**에 반영하여 타임라인의 신뢰성 확보

### 1.5 [RISK-HIGH] Neo4j AuraDB Professional의 APOC 지원 여부

- **현황**: 백업 전략이 전적으로 `CALL apoc.export.json.all()`에 의존
- **문제**:
  - AuraDB는 Managed 서비스로, **APOC Extended 플러그인이 기본 설치되지 않을 수 있음**
  - AuraDB Free에서 APOC Core는 사용 가능하나 `apoc.export.*`는 **APOC Extended**에 속하며 AuraDB에서 지원되지 않을 가능성 높음
  - AuraDB Professional도 APOC Extended 미지원 시 **백업/마이그레이션 전략 전체가 무효화**
- **완화**: standard.1에서 Phase 0-5-2a에 즉시 확인 태스크 추가 + 대안 방법(Cypher CSV, Console 스냅샷) 기술 — **적절한 대응**
- **잔존 리스크**: 대안 방법(Cypher UNWIND + CSV)의 경우 2.77M 노드 export에 수 시간 소요 가능. AuraDB Console 스냅샷은 Professional에서만 자동 제공되므로 Phase 1(Free) 단계에서는 사용 불가

### 1.6 [RISK-MEDIUM] Anthropic Claude Haiku 4.5 Batch API — 모델 가용성

- **현황**: 아키텍처에서 "Claude Haiku 4.5 — KG 추출 Primary"로 명시
- **분석**:
  - Anthropic Batch API에서 Claude Haiku 4.5 모델이 지원되는지 확인 필요
  - standard.1에서 Pre-Phase 0 체크리스트에 [R-3] 추가됨 — 적절
  - Batch API 미지원 시 일반 API 사용은 비용 2배 증가 ($1,500 → $3,000)

### 1.7 [RISK-MEDIUM] Neo4j AuraDB 도쿄 → 서울 Cloud Run 간 네트워크 레이턴시

- **현황**: Neo4j `asia-northeast1`(도쿄), Cloud Run `asia-northeast3`(서울)
- **분석**:
  - 도쿄↔서울 간 RTT: ~30-50ms
  - Phase 2에서 2.77M 노드 적재 시 배치 크기 100건 × 수만 트랜잭션 = 순수 네트워크 대기 ~33분
  - `kg-graph-load` Job의 timeout이 43,200s(12시간)인데, 8 tasks로 2.77M 노드 분산 시 task당 ~345K 노드 처리 필요
  - 배치 크기 100건 × 3,450 트랜잭션 × 50ms RTT = ~172초 순수 네트워크 대기 → 적재 로직 시간 포함 시 **12시간 내 완료 가능**하나 여유가 적음
- **standard.1 반영**: [R-9] 벤치마크 태스크 추가 + UNWIND 권장 — 적절
- **추가 권장**: timeout을 86,400s(24시간)로 확장하거나, tasks를 16으로 증가시켜 task당 부담 감소

### 1.8 [RISK-MEDIUM] 비용 추정 정합성 점검

- **분석**:
  - Phase 2 LLM 합계 `$2,131` = $1,500(Anthropic Batch CandidateContext) + $4(CompanyContext) + $30(Embedding) + $3.6(Egress) + $5(Gemini 크롤링) + $20(Silver Label) + $600(프롬프트 최적화) = **$2,162.6** → 약 $30 차이 (Cloud Run 비용이 LLM에 혼입된 것으로 추정)
  - 05_models_and_methods.md에서 Phase 2 LLM 합계는 **$2,159**로 기술 → 문서 간 $28 불일치
  - Phase 0 비용이 overview에서 $95이나 models_and_methods에서 $85 → **$10 불일치** (Embedding $10 분류 차이)
  - 시나리오 A 총비용 `$8,812` = $95 + $86 + $2,131 + $660 + $5,840 = **$8,812** — 정합
- **권장**:
  - 문서 간 비용 수치 통일 (04_cost vs 05_models_and_methods)
  - LLM 비용 vs 인프라 비용의 경계를 명확히 정의하고 항목별 합산 검증
  - 총비용 표에 **범위(min-max)** 형태로 제시 (현재는 시나리오별 점추정)

### 1.9 [RISK-LOW] Docker 이미지 크기 — Cold Start 영향

- **현황**: KG 파이프라인 이미지에 LibreOffice(~1.5GB), 크롤링 이미지에 Playwright/Chromium(~1.2GB) 포함
- **문제**: Cloud Run Jobs cold start 시간 증가 (이미지 풀 ~30s~1min)
- **영향**: 파이프라인 실행 자체에는 큰 문제 없으나, 개발 중 빌드/배포 속도에 영향
- **권장**: Phase 0-4-7 HWP PoC 결과에 따라 LibreOffice 불필요 시 이미지 경량화 검토

---

## 2. 과도한 일정/기능 (Over-Engineering / Premature)

### 2.1 [HIGH] Phase 2 Cloud Workflows YAML 상세 구현 — 시기상조

- **현황**: `workflows/kg-full-pipeline.yaml`이 30줄+ YAML로 상세 구현, `workflows/kg-incremental.yaml`도 별도 정의
- **문제**:
  - Phase 2 시작까지 최소 16~17주 남은 시점에서 Cloud Workflows의 구체적 YAML 구조는 시기상조
  - Phase 1 구현 과정에서 Job 이름, 파라미터, 실행 순서가 변경될 가능성 **매우 높음**
  - 예: `kg-batch-submit`과 `kg-batch-poll` 분리(R-8 반영)가 이미 Workflows YAML의 기존 구조를 변경시킴
  - Workflows YAML 내 `googleapis.run.v1.namespaces.jobs.run` API 호출 구문은 Cloud Run v2와의 호환성 확인도 필요
- **영향**: 계획 문서의 유지보수 부담 증가, 실제 구현 시 재작성 필요
- **권장**: Workflows 도입 의도와 DAG 구조(텍스트/다이어그램)만 기술하고, YAML 구현은 Phase 2 시작 시점에 작성. **절감: 문서 작성/유지보수 2~3일**

### 2.2 [MEDIUM] Phase 2-5 DS/MLE 서빙 인터페이스 1주 — 범위 대비 일정 과다

- **현황**: 1주 동안 BigQuery 스키마 확정 + SQL 예시 + ablation 테스트 환경 구축
- **문제**:
  - BigQuery SQL 예시 작성과 문서화는 **2~3일**이면 충분
  - "ablation 테스트 환경"이라고 했으나 실제 내용은 BigQuery 뷰 생성 + 쿼리 작성 수준
  - DS/MLE가 실제로 사용할 인터페이스 형태(API? Jupyter 노트북? BigQuery 직접 쿼리?)가 불명확하여 1주를 투자해도 **방향이 맞는지 검증 불가**
- **권장**:
  - Phase 2-5를 **3일**로 축소하고, 잉여 시간을 Phase 2-6 증분 처리에 재할당
  - DS/MLE 인터페이스 요구사항을 Phase 1 중간에 사전 확인하여 Phase 2-5의 방향 확정

### 2.3 [MEDIUM] 크롤링 BigQuery 테이블 5개 — 운영 복잡성 과다

- **현황**: 크롤링용 BigQuery 테이블이 5개 (`crawl_company_targets`, `crawl_homepage_pages`, `crawl_news_articles`, `crawl_extracted_fields`, `crawl_company_summary`)
- **문제**:
  - 크롤링 대상 기업이 초기 1,000개로 소규모
  - `crawl_company_summary`는 `crawl_extracted_fields`의 집계 뷰로 대체 가능 — 별도 테이블 불필요
  - 5개 테이블 간의 조인 관계 + 데이터 정합성 유지는 크롤링 파이프라인의 복잡성을 불필요하게 증가시킴
- **권장**:
  - `crawl_company_summary`는 **BigQuery 뷰**로 대체
  - `crawl_homepage_pages`와 `crawl_news_articles`를 `crawl_raw_data` 단일 테이블로 통합 가능 (`source_type` 컬럼으로 구분)
  - 초기에는 3개 테이블(`crawl_company_targets`, `crawl_raw_data`, `crawl_extracted_fields`)로 충분

### 2.4 [LOW] Looker Studio 대시보드 — Phase 2에서도 BigQuery Console로 충분

- **현황**: Phase 2 산출물에 "Looker Studio 대시보드 구축" 포함, 11개 패널 설계
- **문제**:
  - 2명 운영 체제에서 Looker Studio 대시보드 11개 패널은 과잉 투자
  - BigQuery Console에서 저장된 쿼리(Saved Queries)로 동일한 모니터링 가능
  - 대시보드 구축 + 유지보수에 **2~3일** 소요되나, 동일 정보를 SQL 쿼리로 확인하는 데 **30분/일**
  - 운영 인력이 5명 이상으로 확대될 때 대시보드 ROI가 발생
- **권장**:
  - Phase 2에서는 BigQuery Saved Queries + Cloud Monitoring 알림으로 운영
  - Looker Studio는 Phase 3(운영 최적화) 또는 운영 인력 확대 시 도입

### 2.5 [LOW] Phase 2-2 품질 평가 기준 — 일부 과도한 통계 방법론

- **현황**: Cohen's d(효과 크기), Power analysis를 Phase 2-2에서 수행
- **문제**:
  - Cohen's κ(평가자 간 일치도)는 Gold Test Set 구축에 필수이므로 적절
  - 그러나 Cohen's d와 Power analysis는 **모델 간 비교**(A/B 테스트)에 사용하는 것인데, Phase 2에서 모델은 이미 확정된 상태
  - Phase 2-2의 목적이 "현재 파이프라인의 품질 측정"이라면 단순 정확도/F1 측정으로 충분
- **권장**: Cohen's d / Power analysis는 Phase 3에서 ML Distillation 모델과 LLM의 비교 시 적용. Phase 2-2에서는 제외하여 품질 평가를 **3일**로 단축 가능

---

## 3. 부족한 일정/기능 (Missing / Under-specified)

### 3.1 [HIGH] 증분 처리(Incremental) 설계 — 핵심 로직 보완 필요

- **현황**: standard.1 리뷰 R-1 반영으로 `[R-1] 증분 처리 변경 감지 메커니즘`이 Phase 2-6에 추가됨
- **보완된 부분**:
  - 변경 감지 기준: `processing_log` 마지막 처리 시점 이후 GCS 신규 파일 탐지
  - JD 변경 시 영향 범위: CompanyContext 재생성 → MAPPED_TO만 재계산
  - 사전 업데이트 시: 전체 재처리 트리거 (수동, 분기 1회 이하)
- **여전히 부족한 부분**:
  - 증분 처리 **일일 1,000건**의 근거 없음 — 이 수치가 운영 비용($90/월)의 기반인데 실제 일일 신규 이력서 유입량 추정이 없음
  - `kg-detect-changes` Job의 **구현 일정**이 Phase 2-6(1~2주)에 포함되어 있으나, 이 Job은 Cloud Workflows 연동 + GCS 탐색 + BigQuery 조회 + 변경 분류 로직을 포함하므로 **단독으로 3~5일** 필요
  - 증분 시 **기존 Graph 노드와의 충돌 처리** 미기술 — 예: 동일 candidate_id로 이력서가 업데이트된 경우 기존 Chapter 노드는 어떻게 되는가? (삭제 후 재생성? 업데이트?)
- **권장**:
  - 일일 증분량 추정 근거 추가 (현재 채용 플랫폼의 일일 이력서 유입량 데이터 기반)
  - 이력서 업데이트 시 Graph 처리 전략 명시: `DETACH DELETE` 후 재생성 vs Chapter 노드 `MERGE` 업데이트

### 3.2 [HIGH] Phase 0 → Phase 1 전환 시 코드 재작성 리스크

- **현황**: Phase 0은 "Cloud Shell / 로컬 Python"으로 PoC를 수행하고, Phase 1에서 "Cloud Run Jobs" 코드로 전환
- **문제**:
  - Phase 0 PoC 코드(Jupyter 노트북 또는 스크립트)를 프로덕션 코드(모듈 구조, 에러 핸들링, checkpoint 내장, Docker 패키징)로 **리팩토링하는 시간**이 Phase 1 타임라인에 명시적으로 포함되지 않음
  - Phase 0에서 50건으로 검증한 프롬프트/파싱 로직이 1,000건 규모에서 예상치 못한 엣지 케이스를 발생시킬 가능성
  - Phase 0-4에서 확정된 의사결정(HWP 파싱 방법, Embedding 모델, LLM 모델)을 Phase 1 코드에 **통합하는 작업**이 별도 태스크로 분리되지 않음
- **권장**:
  - Phase 1 시작 시 **Week 5 첫 2~3일을 "코드 리팩토링 + Phase 0 의사결정 통합"**으로 명시
  - 또는 Phase 0-4 PoC를 처음부터 모듈 구조로 작성하도록 가이드 (예: `src/` 디렉토리 구조 준수)

### 3.3 [HIGH] Cloud Run Jobs 동시 실행 시 Neo4j Connection Pool 한계

- **현황**: `kg-graph-load`가 8 tasks 동시 실행, `kg-embedding`이 10 tasks 동시 실행
- **문제**:
  - Neo4j AuraDB Free의 동시 연결 수 한도가 명시되지 않음 (일반적으로 Free는 3~5 concurrent connections)
  - 8 tasks가 동시에 Neo4j에 연결하면 connection pool 부족으로 실패할 가능성
  - AuraDB Professional도 기본 concurrent connections 한도가 있음 (사양에 따라 다름)
- **영향**: Graph 적재 Job이 connection refused로 실패 → 자동 재시도 소진 → 수동 대응 필요
- **권장**:
  - Phase 0-5-2(Neo4j 인스턴스 생성) 시 **max concurrent connections 확인** 태스크 추가
  - Graph 적재 Job의 tasks 수를 connection pool 한도에 맞춰 조정 (Free 기간은 tasks=3~4로 제한)
  - connection pool 관리 로직 추가 (retry with exponential backoff + connection 재사용)

### 3.4 [MEDIUM] Organization Entity Resolution — 알고리즘 보완 필요

- **현황**: standard.1 리뷰 R-4 반영으로 ER 알고리즘 3단계 명시 + 정확도 목표 추가
- **보완된 부분**: 사전 매칭 → Jaro-Winkler → 사업자번호
- **여전히 부족한 부분**:
  - 한국어 회사명 정규화의 **전처리 규칙**이 없음: "(주)" 제거, "주식회사" 제거, 영문명 통일 등
  - Jaro-Winkler threshold 0.85가 한국어 회사명에 적합한지 **검증 근거 없음** — 영어에서의 일반적 threshold이며 한국어에서는 다를 수 있음
  - ER 결과의 **수동 검수 프로세스**가 없음 — Phase 1에서 500개 Organization 수준이면 전수 검수 가능
- **권장**:
  - Phase 0-3 프로파일링에서 회사명 변형 패턴 분석 태스크 추가 (이미 R-4에서 언급, 구체화 필요)
  - Phase 1-4-4에서 ER 결과 전수 검수(500개 Organization) 태스크 추가 (**0.5일**)

### 3.5 [MEDIUM] pyhwp 라이브러리 성숙도 리스크

- **현황**: HWP 파싱 방법 B로 `pyhwp >= 0.1b12`를 사용
- **보완된 부분**: standard.1 리뷰 R-5 반영으로 HWPX 미지원 리스크 확인 항목 추가
- **잔존 리스크**:
  - pyhwp는 **0.1 베타** 버전, 프로덕션 환경 안정성 미검증
  - HWP5 포맷만 지원하며 HWPX(한글 2014 이후 표준) 미지원
  - PyPI 마지막 업데이트 확인 필요 — 유지보수 중단 시 보안 패치 없음
- **영향**: Phase 0-4-7에서 평가 후 결정되므로 계획 리스크는 낮음. 다만 pyhwp 선택 시 **장기 유지보수 리스크**를 의사결정에 반영해야 함

### 3.6 [MEDIUM] 모니터링 알림의 대응 절차 — 부분 보완됨

- **현황**: standard.1 리뷰 R-6 반영으로 CRITICAL 알림 4건에 대한 runbook 추가
- **보완된 부분**: 파싱 실패 > 10%, Batch 만료, Neo4j 연결 실패, Cloud Run 3회 연속 실패에 대한 대응 절차
- **여전히 부족한 부분**:
  - "Batch 결과 만료 72시간 이내" 알림에 대해 **자동 수집 트리거**가 아닌 수동 대응으로 기술
  - DE 1명 + MLE 1명 체제에서 **야간/주말 알림 대응 체계** 여전히 부재
  - Phase 2-1 전체 데이터 처리(3~4주) 동안 24/7 모니터링이 필요한데 2명으로는 불가능
- **권장**:
  - Batch 결과 만료 위험은 **Cloud Scheduler 일일 자동 수집** 트리거로 대응 (이미 `kg-batch-poll`이 30분 주기이므로 만료 위험은 낮으나, 폴링 Job 자체 실패 시의 fallback 필요)
  - Phase 2-1 기간 중 **업무 시간 외 알림은 Slack만** 전송, 다음 업무일 아침 대응으로 SLA 정의

### 3.7 [MEDIUM] Phase 간 Go/No-Go 기준 — 보완됨, 추가 필요

- **현황**: standard.1 리뷰 R-7 반영으로 Phase 1 → Phase 2 Go/No-Go 기준 5개 추가
- **보완된 부분**: E2E 파이프라인, Regression test, 수동 검증, Neo4j 백업, 적재 벤치마크
- **추가 필요**:
  - Phase 0 → Phase 1 Go/No-Go 기준이 Phase 0-6 의사결정 9개로 존재하나, **전체 통과/부분 통과 시 판단 기준** 없음
  - 예: HWP 파싱 방법이 3개 모두 CER > 0.15인 경우 → Phase 1을 HWP 제외하고 진행? 중단?
  - Phase 2 완료 → **운영 전환** 기준이 없음 (Phase 3 진입 조건은 있으나 "운영 모드 전환" 자체의 판단 기준 부재)

### 3.8 [MEDIUM] 운영 단계 인력 및 인수인계 계획 부재

- **현황**: Phase 2 완료 후 운영 단계 월 비용($236~336)은 상세히 기술되어 있으나, **운영 인력 계획**이 없음
- **문제**:
  - DE 1명 + MLE 1명이 프로젝트 완료 후에도 계속 운영을 담당하는가?
  - 다른 프로젝트로 이동 시 인수인계 대상과 범위가 미정
  - 증분 처리 파이프라인의 장애 대응, 프롬프트 업데이트, 사전 관리 등의 **운영 업무량** 추정 없음
- **권장**:
  - 운영 단계 필요 인력 추정: 풀타임 0.3~0.5명 (주 1~2일 모니터링 + 장애 대응)
  - 인수인계 문서 작성을 Phase 2-6에 태스크로 추가

### 3.9 [LOW] GCS 버킷 환경 분리

- **현황**: standard.1 리뷰 R-10 반영으로 `raw/resumes/dev/`, `raw/resumes/prod/` prefix 분리 추가
- **보완**: 적절한 수준의 분리가 이루어짐
- **잔존 참고사항**: `parsed/`, `contexts/`, `batch-api/` 등 중간 산출물도 dev/prod 분리가 필요할 수 있으나, Phase 1(dev)과 Phase 2(prod)가 시간상 분리되어 있으므로 현재 수준으로 충분

### 3.10 [LOW] Gemini 모델 버전 고정

- **현황**: standard.1 리뷰 R-11 반영으로 "Phase 0 확정 버전 snapshot 고정, 예: `gemini-2.5-flash-001`" 명시
- **보완**: 적절. 다만 크롤링 LLM 추출 외에 Phase 0 API 검증에서 사용하는 Gemini 모델도 동일 고정 정책 적용 필요

---

## 4. 일정 최적화 제안

### 4.1 Phase 1 재조정안 (10~12주 → 11~13주)

| 단계 | 현재 | 제안 | 변경 이유 |
|------|------|------|-----------|
| 1-1 전처리 모듈 | 2주 | **3주** | 9개 태스크 현실적 소화 (§1.1) |
| 1-2 CompanyContext | 1~2주 | 1~2주 | 유지 |
| 1-3 CandidateContext | 4주 | 4주 | 유지 (이미 v7에서 3주→4주 조정됨) |
| 1-4 Graph 적재 | 2주 | 2주 | 유지 |
| 1-5 MappingFeatures | 2주 | 2주 | 유지 |
| 1-6 테스트 | 1주 | 1주 | 유지 |
| **합계** | **10~12주** | **11~13주** | +1주 |

### 4.2 Phase 2 재조정안 (12~16주 → 11~14주)

| 단계 | 현재 | 제안 | 변경 이유 |
|------|------|------|-----------|
| 2-0 Neo4j 전환 | 1일 | 1일 | 유지 |
| 2-1 전체 데이터 처리 | 3~4주 | 3~4주 | 유지 |
| 2-2 품질 평가 | 1주 | **3일** | Cohen's d/Power analysis Phase 3으로 이동 (§2.5) |
| 2-3 크롤링 파이프라인 | 4주 | 4주 | 유지 |
| 2-4 크롤링 보강 | 1주 | 1주 | 유지 |
| 2-5 서빙 인터페이스 | 1주 | **3일** | SQL 작성에 1주 과다 (§2.2) |
| 2-6 증분 처리 + 운영 | 1~2주 | **2주** | 증분 처리 구현 복잡성 반영 (§3.1) |
| **합계** | **12~16주** | **11~14주** | -1~2주 |

### 4.3 총 타임라인 영향

| 항목 | 현재 | 제안 |
|------|------|------|
| Phase 0 | 4~5주 | 4~5주 (변경 없음) |
| Phase 1 | 10~12주 | 11~13주 (+1주) |
| Phase 1~2 버퍼 | 없음 | **1주** (§1.3) |
| Phase 2 | 12~16주 | 11~14주 (-1~2주) |
| **총 MVP 완성** | **26~33주** | **27~33주** (실질 변화 없음) |

> 총 타임라인은 거의 동일하나, Phase 1의 여유 확보 + Phase 2의 비핵심 태스크 축소로 **인력 부담이 더 균등하게 분배**됨.

---

## 5. 잘된 부분 (Strengths)

### 5.1 v2 리뷰 전수 반영 — 체계적 개선 프로세스

- 16건 권장사항 전수 반영, 각 변경에 `[standard.1-N]` 태그 부여로 추적 가능
- v2→standard.1 변경 요약 표(Overview 섹션 10)가 리뷰→개선 투명성을 제공

### 5.2 Batch API 현실적 처리 시간 계산 — 신뢰성 향상

- 450 chunks / 10 동시 = 45 라운드 × 6시간 + 실패 재시도 + 버퍼 = ~21일 계산이 명확
- batch_tracking BigQuery 테이블 설계가 구체적이고 즉시 구현 가능

### 5.3 파이프라인 레벨 Checkpoint 설계 — 프로덕션 레디

- `processing_log` 기반 checkpoint + Graph 적재 batch 단위 재시작 설계가 실용적
- 코드 예시가 포함되어 구현 모호성 최소화

### 5.4 Phase 1 테스트 전략 — 적절한 범위

- Golden 50건 regression test가 프롬프트 변경의 품질 회귀를 방지하는 실용적 접근
- `deepdiff` 기반 비교 + tolerance 설정이 LLM 출력의 비결정성을 고려

### 5.5 Makefile → Cloud Workflows 점진적 전환 — 과설계 방지

- Phase 1 MVP에서 Makefile 수동 실행 → Phase 2에서 Cloud Workflows 전환 전략이 "필요할 때 복잡성 추가" 원칙에 부합

### 5.6 한국어 토큰 비용 보정 — 비용 투명성 향상

- 한글 1자 ≈ 2~3 tokens 보정으로 비용이 ×1.88배 증가함을 명시
- Cloud Run Jobs 비용도 Job별 상세 표(vCPU·h × 단가)로 검증 가능성 확보

### 5.7 법적 리스크의 Contingency 설계 — 현실적

- PII 법무 지연 시 "마스킹 상태로 우선 진행"
- 크롤링 법무 불허 시 "NICE/DART 공공 데이터로 한정"
- 각각의 fallback이 프로젝트를 완전히 중단시키지 않는 설계

### 5.8 batch-submit/poll 분리 — 비용 최적화 적용

- standard.1 리뷰 R-8 반영으로 Cloud Run idle 비용 $62 → $0.5 절감
- Cloud Scheduler 30분 주기 폴링 설계가 비용-효율 균형 우수

### 5.9 05_models_and_methods.md — 모델/방법론 일원화

- 전 Phase에 걸친 모델, 알고리즘, 청킹 방법론을 한 문서에 정리
- Phase별 비용을 모델 관점에서 재집계하여 비용 구조의 투명성 향상

---

## 6. 개선 권장사항 요약

| # | 심각도 | 영역 | 권장 조치 | Phase 영향 |
|---|--------|------|-----------|------------|
| R-1 | CRITICAL | Phase 1-1 일정 | 전처리 모듈 2주→3주 확장 | Phase 1 전체 +1주 |
| R-2 | HIGH | 증분 처리 | 일일 증분량 근거 + 이력서 업데이트 시 Graph 처리 전략 | Phase 2-6 |
| R-3 | HIGH | 코드 전환 | Phase 0→1 리팩토링 시간 명시 (2~3일) | Phase 1 시작 |
| R-4 | HIGH | Neo4j 연결 | Cloud Run tasks 수와 AuraDB connection pool 한도 정합성 확인 | Phase 0-5, Phase 1-4 |
| R-5 | HIGH | Batch API 수치 | 계획 확정 전 Anthropic Tier/limit 즉시 확인 | Pre-Phase 0 |
| R-6 | MEDIUM | Phase 1~2 버퍼 | Phase 1 완료 후 1주 버퍼 확보 | 타임라인 |
| R-7 | MEDIUM | 인력 역할 분담 | DE/MLE 역할 분담표 추가 | 전체 |
| R-8 | MEDIUM | 운영 인력 | 운영 단계 인력 계획 + 인수인계 문서 태스크 추가 | Phase 2-6 |
| R-9 | MEDIUM | 서빙 인터페이스 | Phase 2-5를 1주→3일로 축소 | Phase 2-5 |
| R-10 | MEDIUM | 품질 평가 | Cohen's d/Power analysis를 Phase 3으로 이동, Phase 2-2를 3일로 축소 | Phase 2-2 |
| R-11 | MEDIUM | Workflows YAML | 상세 YAML 제거, DAG 구조만 기술 | Phase 2-1 문서 |
| R-12 | MEDIUM | Organization ER | 한국어 전처리 규칙 + Phase 1-4-4 전수 검수 태스크 추가 | Phase 1-4 |
| R-13 | LOW | 비용 정합성 | 문서 간 비용 수치 통일 (04_cost vs 05_models) | 문서 |
| R-14 | LOW | 크롤링 테이블 | 5개→3개 축소 (summary를 뷰로 대체) | Phase 2-3 |
| R-15 | LOW | Go/No-Go | Phase 0→1 전환 기준 + Phase 2→운영 전환 기준 추가 | Phase 0-6, Phase 2 완료 |

---

## 7. 최종 판정

| 항목 | 판정 | v2 대비 변화 |
|------|------|-------------|
| **전체 구조 / 논리 흐름** | **PASS** | 유지 |
| **Phase 0 (검증 + PoC)** | **PASS** | 개선 (VAS 제거, HWP PoC 추가) |
| **Phase 1 (MVP)** | **PASS with minor** | 개선 (테스트, checkpoint) — 1-1 일정 과소 추정 주의 |
| **Phase 2 (확장 + 크롤링)** | **PASS with minor** | 개선 (직렬화, 타임라인) — 일부 과설계 축소 권장 |
| **비용 추정** | **PASS with minor** | 개선 (한국어 보정, 상세 표) — 문서 간 소액 불일치 |
| **모니터링 / 운영** | **PASS with minor** | 개선 (runbook 추가) — 운영 인력 계획 부재 |
| **보안 설계** | **PASS** | 개선 (PII 법무, 크롤링 법적) |
| **에러 복구 / 재시작** | **PASS** | 신규 (standard.1에서 추가, 적절) |
| **테스트 전략** | **PASS** | 신규 (standard.1에서 추가, 적절) |
| **실현 가능성** | **PASS with minor** | 개선 — Phase 1-1 일정/Neo4j 연결 수 리스크 잔존 |
| **과설계 여부** | **PASS with minor** | 신규 축 — Workflows YAML/Looker Studio 축소 권장 |
| **일정 균형** | **PASS with minor** | 과설계 축소분을 부족 부분에 재할당 가능 |

> **결론**: standard.1는 v2의 CRITICAL/HIGH 이슈를 모두 해소한 **실행 가능한(actionable) 계획**이다.
>
> 새로 발견된 CRITICAL 이슈 1건(Phase 1-1 전처리 모듈 일정 과소 추정)은 **1주 확장으로 즉시 해소 가능**하며,
> HIGH 이슈 4건(증분 처리 보완, 코드 전환 시간, Neo4j 연결 수, Batch API 수치)은
> 모두 **Phase 0 시작 전후에 해소 가능**한 성격이다.
>
> 과설계 영역(Workflows YAML, 서빙 인터페이스, 품질 평가 통계)을 축소하면
> **총 타임라인 변경 없이** Phase 1의 여유를 확보하고 Phase 2의 핵심 태스크에 집중할 수 있다.
>
> **권장**: R-1(전처리 일정 확장)을 즉시 반영하고, R-5(Batch API 수치)는 계획 확정 전 확인한다.
> 나머지 권장사항은 해당 Phase 시작 시 보완하는 것이 적절하다.
> 전체적으로 **실행 승인(Go)** 판정을 내린다.
