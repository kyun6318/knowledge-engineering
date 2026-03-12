# GraphRAG GCP 통합 실행 계획 v2 — 리뷰

> 리뷰 대상: `03.ml-platform/plans/graphrag/v2/` (5개 문서)
> 리뷰 일자: 2026-03-08
> 리뷰어: Claude

---

## 총평

v2는 이전 v0/v1의 분산된 8개 문서를 5개 Phase 중심으로 잘 통합하였으며, API 검증→PoC→MVP→확장까지 논리적 흐름이 명확하다. 특히 api-test-3day P0 패치 5건 반영, 단일 GCP 프로젝트 통합, 크롤링 Phase 2 앞당김 등의 변경은 모두 합리적이다. 다만 일부 영역에서 **과설계(over-engineering)**, **낙관적 추정**, **누락된 리스크** 가 발견되어 아래에 상세히 기술한다.

---

## 1. 과한 부분 (Over-Engineering / Premature)

### 1.1 [HIGH] Phase 0에 Discovery Engine (VAS) 검증 포함 — 불필요

- **현황**: Phase 0-2 Day 2에서 VAS Data Store 생성 + Search Engine 생성 + Day 3에서 RAG 검색 테스트를 수행
- **문제**: GraphRAG 시스템의 최종 아키텍처는 Neo4j + Anthropic/Gemini LLM 기반이며, VAS(Vertex AI Search)를 사용하는 경로가 Phase 1~2 어디에도 없다. Phase 0 검증에 포함된 이유가 불분명
- **영향**: Discovery Engine API 활성화, VAS Data Store 생성/인덱싱 대기 시간, 검증 비용 (~$15) 소요
- **권장**: VAS 검증을 Phase 0에서 제거하거나, "향후 서빙 레이어 대안 탐색" 목적이라면 별도 Optional로 분리

### 1.2 [MEDIUM] Phase 0-2 RAG Engine (Corpus) 검증 — 목적 불분명

- **현황**: Day 2에서 RAG Corpus 생성 + Import, Day 3에서 RAG retrieval + 생성 테스트
- **문제**: VAS와 동일하게, Phase 1~2 파이프라인에서 Vertex AI RAG Engine을 사용하는 곳이 없다. KG 시스템은 Neo4j Vector Index를 활용
- **권장**: 삭제하거나, "Neo4j Vector Search와의 retrieval 품질 비교" 명시적 목적 부여. 현재는 API 기능 카탈로그 확인 수준에 그치고 있음

### 1.3 [MEDIUM] Cloud Workflows — Phase 1에서 즉시 필요하지 않음

- **현황**: Phase 1 완료 산출물에 "Cloud Workflows 파이프라인 배포"가 포함
- **문제**: Phase 1은 MVP로 JD 100건 + 이력서 1,000건 수준. 이 규모에서 Cloud Workflows DAG 오케스트레이션은 과하며, 수동 또는 간단한 셸 스크립트로 충분
- **권장**: Phase 1에서는 `Makefile` 또는 `bash` 스크립트로 수동 오케스트레이션, Phase 2 전체 데이터 처리 시점에 Cloud Workflows 도입

### 1.4 [LOW] 11개 Cloud Run Jobs — 초기 분리 과다

- **현황**: Phase 1에서 11개 별도 Cloud Run Jobs 등록 (parse, dedup, batch-prepare, batch-submit, batch-collect, company-ctx, graph-load, embedding, mapping, industry-load, dead-letter)
- **문제**: Phase 1은 1,000건 규모. 이 시점에 11개 Job을 분리하면 Docker 이미지 관리, Job 설정 관리 오버헤드가 MVP 개발 속도를 저하
- **권장**: Phase 1에서는 `kg-pipeline` 단일 이미지 + `--command` 인자로 모듈 선택하는 구조 (이미 계획 중). 개별 Job 분리는 Phase 2에서 성능 최적화 시점에 수행

### 1.5 [LOW] ML Knowledge Distillation (Phase 2-6) — 시기상조

- **현황**: Phase 2-6에서 KLUE-BERT 기반 scope_type/seniority 분류기 학습
- **문제**: 전체 파이프라인이 아직 품질 검증도 안 된 시점에 ML distillation은 조기 최적화. LLM 비용 절감이 목적이라면 Phase 2 완료 후 운영 데이터 기반으로 진행하는 것이 합리적
- **권장**: Phase 2 산출물에서 제거하고 "운영 최적화" 별도 Phase로 분리

---

## 2. 부족한 부분 (Missing / Under-specified)

### 2.1 [CRITICAL] HWP 파일 처리 전략 — 거의 미기술

- **현황**: 1-1-1에서 "PDF/DOCX/HWP 파서 모듈"로만 언급, Docker에 LibreOffice 포함
- **문제**: HWP는 한국 이력서에서 상당 비율을 차지할 수 있으나:
  - LibreOffice의 HWP 변환 품질이 불안정 (특히 표 구조, 한글 폰트)
  - hwp5txt, pyhwp 등 대안 라이브러리 검토 미기술
  - Phase 0-3 데이터 프로파일링에서 HWP 비율만 확인하고, HWP 파싱 품질 PoC가 없음
- **권장**: Phase 0-4에 "HWP 파싱 품질 PoC (10건)" 추가. LibreOffice / hwp5txt / Gemini 멀티모달 직접 추출 비교

### 2.2 [CRITICAL] Neo4j AuraDB Free 제약 — 프로덕션 전환 계획 부실

- **현황**: Phase 0~1에서 AuraDB Free 사용 → Phase 2에서 "필요 시" Professional 전환
- **문제**:
  - AuraDB Free는 **200K 노드 제한, 1GB 스토리지, 자동 일시정지(30일 미사용 시 삭제 가능)**
  - Phase 1에서 이력서 1,000건 + JD 100건이라도 Chapter/Skill/Role 노드를 포함하면 200K에 빠르게 도달 가능
  - Free→Professional 데이터 마이그레이션 방법이 미기술
  - Professional 전환 시 비용 $100~200/월로 급증하는데 전환 트리거 기준이 모호 ("필요 시")
- **권장**:
  - Phase 0-5에서 예상 노드 수 계산 (1,000 이력서 → Person 1K + Chapter ~5K + Skill ~3K + ... = 추정치 기록)
  - 전환 트리거 명시: "노드 수 150K 도달 시" 또는 "Phase 1 E2E 완료 시점"
  - 마이그레이션 방법: neo4j-admin dump/load 또는 APOC export → import

### 2.3 [HIGH] Anthropic Batch API Quota/Rate Limit — 미기술

- **현황**: Phase 2에서 450 chunks를 동시 5~10 batch로 처리 계획
- **문제**:
  - Anthropic Batch API의 동시 batch 수 제한, 일일 요청 한도, 결과 보관 기간 등이 명시되지 않음
  - Batch API SLA가 24시간인데, 450 chunks × 24시간 / 10 동시 = 최소 ~45일. 이는 2~3주 계획과 심각한 괴리
  - Batch API 결과 만료 기간 내 수집 실패 시 복구 방법 미기술
- **권장**:
  - Anthropic Batch API 현재 quota 확인 후 계획에 명시
  - 현실적 처리 시간 재계산: 평균 batch 처리 시간 × chunk 수 / 동시 수
  - Batch 결과 만료 전 자동 수집 보장 메커니즘 기술

### 2.4 [HIGH] 에러 복구 / 재시작 전략 — 파이프라인 레벨 미기술

- **현황**: 개별 item 레벨 dead-letter + 3-tier 파싱 실패 처리는 상세하나, 파이프라인 레벨 실패 복구가 부족
- **문제**:
  - Cloud Run Job이 중간에 OOM/timeout으로 죽을 경우 이미 처리된 건 건너뛰기(checkpoint) 메커니즘 미기술
  - Graph 적재 중 Neo4j 연결 끊김 시 부분 적재 상태 복구 방법 미기술
  - Batch API 제출 Job이 죽을 경우 이미 제출된 batch 추적/복구 방법 미기술
- **권장**:
  - BigQuery `processing_log`를 checkpoint로 활용: 재시작 시 이미 성공한 item_id skip
  - Graph 적재: 트랜잭션 단위를 batch (예: 100건)로 제한, 마지막 성공 batch 기록
  - Batch API: 제출 시점에 batch_id를 BigQuery에 즉시 기록, 폴링 Job은 미완료 batch부터 재개

### 2.5 [HIGH] 테스트/QA 전략 — Phase 1에 부재

- **현황**: Phase 2-4에서 품질 평가 (Gold Test Set)만 있고, Phase 1에 체계적 테스트 전략이 없음
- **문제**:
  - Phase 1 "50건 수동 검증"만으로는 파이프라인 품질 신뢰 불가
  - 단위 테스트, 통합 테스트 코드 작성 계획 미기술
  - Context 생성 결과의 regression 테스트 방법 미기술 (프롬프트 변경 시 기존 품질 유지 확인)
- **권장**:
  - Phase 1에 "테스트 인프라 구축" 태스크 추가: pytest + fixture 기반 단위 테스트
  - Golden 50건을 regression test set으로 활용: 프롬프트 변경마다 자동 비교

### 2.6 [MEDIUM] 데이터 백업/복구 전략 — 미기술

- **현황**: GCS에 `backups/` 디렉토리만 존재, 백업 주기/방법/복구 절차 미기술
- **문제**:
  - Context JSON이 유일한 소스인데 (LLM 재생성 비용 높음) 백업 정책이 없음
  - Neo4j AuraDB Free는 자동 백업이 없음
  - BigQuery 테이블 삭제 시 복구 방법 미기술
- **권장**:
  - GCS Object Versioning 활성화 (비용 미미)
  - Context JSON 백업: GCS lifecycle policy로 30일 보관
  - Neo4j: Phase 1 완료 시 APOC export → GCS 수동 백업, Professional 전환 후 자동 백업 활성화

### 2.7 [MEDIUM] PII 처리 법적 근거 — 불확실성 해소 방법 미기술

- **현황**: Phase 0-4-4에서 PII 마스킹 영향 테스트, 0-6에서 "법무 결론" 의사결정
- **문제**:
  - "법무 결론"이 Phase 0 완료 시점까지 나오지 않으면 전체 일정에 미치는 영향이 미기술
  - PII 마스킹 없이 Anthropic API에 전송 불가 판정 시 On-premise GPU(시나리오 C) 전환에 4~8주 추가 소요
  - Phase 0 시작 전 법무 검토를 선제적으로 시작해야 하는데 Pre-Phase 0에 누락
- **권장**:
  - Pre-Phase 0에 "법무팀 PII 처리 방침 검토 요청" 추가 (NICE DB 접근과 동일 레벨의 blocking dependency)
  - 법무 결론 지연 시 contingency: "마스킹 적용 상태로 우선 진행, 허용 판정 시 마스킹 제거 옵션"

### 2.8 [MEDIUM] 크롤링 법적 리스크 — robots.txt 외 미기술

- **현황**: robots.txt 준수만 언급
- **문제**:
  - 웹 크롤링의 법적 리스크는 robots.txt 준수만으로 해소되지 않음
  - 한국 저작권법, 정보통신망법 관련 검토 미기술
  - 크롤링 데이터의 LLM 학습 활용 시 추가 법적 이슈 존재 (이 프로젝트에서는 추출 목적이므로 상대적 리스크 낮음, 그러나 명시 필요)
- **권장**: Pre-Phase 2에 "크롤링 법적 검토" 체크포인트 추가, "추출 목적 한정, 원본 비보관" 정책 명시

### 2.9 [LOW] Vertex AI 리전 간 데이터 이동 비용 — 미계산

- **현황**: GCS/BigQuery는 `asia-northeast3`(서울), Vertex AI는 `us-central1`
- **문제**: Embedding 생성 시 텍스트를 서울→US로 전송하는 egress 비용이 비용 추정에 누락
- **영향**: 302M 토큰 규모이므로 raw text 크기에 따라 수십 GB 규모 가능. GCP egress $0.12/GB (아시아→미국)
- **권장**: Embedding 대상 텍스트 총 크기 추정 → egress 비용 계산 추가

---

## 3. 실현 가능성 검증

### 3.1 [RISK-HIGH] 타임라인 — Phase 2 전체 데이터 처리 2~3주는 비현실적

- **현황**: 450K 이력서를 450 chunks × Batch API로 2~3주 내 처리 계획
- **분석**:
  - 문서 자체에 "~45 batch × 6시간 = ~11일"로 추정하나, 이는 동시 10 batch 가정
  - Anthropic Batch API의 실제 처리 시간은 SLA 24시간이지만 평균 2~6시간 (부하에 따라 변동)
  - 450 chunks / 10 동시 = 45 라운드 × 6시간 평균 = 270시간 = **~11일** (연속 가동 가정)
  - 실패 chunk 재시도, 결과 수집, Graph 적재까지 포함하면 **3~4주가 현실적**
- **권장**: Phase 2-1 일정을 3~4주로 조정하거나, 동시 batch 수를 늘릴 수 있는지 Anthropic과 사전 협의

### 3.2 [RISK-HIGH] 인력 — DE 1명 + MLE 1명으로 24~29주 프로젝트

- **현황**: 전체 프로젝트를 DE 1명 + MLE 1명 풀타임 + 도메인 전문가 1명 파트타임으로 수행
- **분석**:
  - Phase 0: 합리적 (검증 + PoC 성격)
  - Phase 1: 10~12주에 전처리/Context 2종/Graph/Embedding/Mapping 전체를 2명이 구현 — 타이트하지만 가능
  - Phase 2: 크롤링 파이프라인 구축(4주) + 전체 데이터 처리 + 품질 평가를 동시 수행 — **인력 부족 리스크 높음**
    - 크롤링은 Playwright, 뉴스 API, LLM 추출 등 별개 도메인
    - 전체 데이터 처리는 운영/모니터링에 상시 대응 필요
    - 품질 평가는 도메인 전문가 의존도 높음
- **권장**:
  - Phase 2 시작 시 크롤링 담당 인력 1명 추가 투입 검토
  - 또는 크롤링과 전체 데이터 처리를 완전 직렬화 (타임라인 ~4주 추가)

### 3.3 [RISK-MEDIUM] Neo4j AuraDB Free → Professional 전환 타이밍

- **문제**: Phase 1 E2E 테스트(JD 100 + 이력서 1,000)로도 노드 수가 빠르게 증가
  - Person ~1K + Chapter ~5K + Organization ~500 + Vacancy ~100 + Skill ~2K + Role ~500 + Industry ~100 = **~9K 노드**
  - 1,000건 규모에서는 여유 있으나, Phase 2에서 1,000건→450K으로 450배 증가 시 **~4M 노드**
  - AuraDB Free 200K 제한에 Phase 2 초기에 즉시 걸림
- **권장**: Phase 2 시작 전(Week 16~17)에 Professional 전환을 확정 일정으로 잡기 ("필요 시" → "필수")

### 3.4 [RISK-MEDIUM] 비용 추정 — 시나리오 A 낙관적

- **분석**:
  - Anthropic Batch API 비용 $575 (500K × $0.00115/건): 건당 input ~1,500 tokens + output ~500 tokens 가정. 한국어 이력서는 토큰 효율이 낮아(한글 1자 ≈ 2~3 tokens) 실제 input이 2~3배 가능
  - Cloud Run Jobs $150 (500시간): 합산이 맞는지 재검증 필요. 특히 Graph 적재 8 tasks × 12시간 = 96시간 × $0.18/vCPU-h ≈ $35 등 개별 계산 불투명
  - Gold Label 인건비 $5,840이 총비용의 75%를 차지하므로, LLM 비용 차이보다 인건비가 실제 프로젝트 비용을 좌우
- **권장**:
  - CandidateContext Batch API 비용을 한국어 토큰 기준으로 재계산 (가정: 평균 3,000 input tokens)
  - 각 Cloud Run Job의 시간×리소스 비용을 개별 표로 제시

### 3.5 [RISK-LOW] Gemini Embedding 비교 — text-embedding-005 vs 문서 내 불일치

- **현황**:
  - 00_overview.md: `text-multilingual-embedding-002` vs `gemini-embedding-001` 비교
  - 01_phase0.md (TEST-C2): `gemini-embedding-001` vs `text-embedding-005` 비교
- **문제**: 비교 대상 모델명이 문서 간 불일치. `text-multilingual-embedding-002` ≠ `text-embedding-005`
- **권장**: 비교 대상 모델 2종을 확정하고 전 문서에서 통일

---

## 4. 잘된 부분 (Strengths)

### 4.1 Phase 0 의사결정 포인트 설계 — 우수
- 8개 의사결정을 Phase 0 완료 시점에 집중 배치, 각 의사결정의 입력 데이터가 명시됨
- "검증 결과가 즉시 의사결정에 반영"되는 v2 구조가 v1 대비 명확히 개선

### 4.2 api-test P0 패치 반영 — 꼼꼼
- 5건의 P0 패치(CountTokens 모델, op name, batch LRO, VAS 문서 확인, 토큰 감소율)가 코드 레벨로 반영

### 4.3 LLM 파싱 실패 3-tier 전략 — 실용적
- json-repair → temperature 조정 재시도 → 부분 추출 허용의 3단계가 프로덕션 레벨 대비로 적절

### 4.4 비용 시나리오 5종 비교 — 의사결정 근거 충분
- Haiku Batch / Haiku→Sonnet Fallback / Sonnet Batch / On-premise / Gemini Flash 시나리오 비교로 의사결정 지원

### 4.5 크롤링 Phase 2 통합 — 합리적 판단
- CompanyContext 보강을 조기에 반영하여 Graph 품질 향상을 앞당기는 결정

### 4.6 BigQuery 모니터링 쿼리 — 즉시 활용 가능
- processing_log, chunk_status, parse_failure_log, 크롤링 대시보드 쿼리가 구체적

---

## 5. 개선 권장사항 요약

| # | 심각도 | 영역 | 권장 조치 |
|---|--------|------|-----------|
| R-1 | CRITICAL | HWP 파싱 | Phase 0-4에 HWP 파싱 PoC 10건 추가 |
| R-2 | CRITICAL | Neo4j 전환 | Free→Professional 전환 시점/방법 명시 |
| R-3 | HIGH | Batch API | Anthropic quota 확인, 처리 시간 재계산 |
| R-4 | HIGH | 에러 복구 | 파이프라인 레벨 checkpoint/재시작 전략 기술 |
| R-5 | HIGH | 테스트 전략 | Phase 1에 테스트 인프라 + regression test 추가 |
| R-6 | HIGH | Phase 0 범위 | VAS/RAG Engine 검증 제거 또는 목적 명시 |
| R-7 | HIGH | 타임라인 | Phase 2-1을 3~4주로 조정 |
| R-8 | MEDIUM | PII 법무 | Pre-Phase 0에 법무 검토 추가 |
| R-9 | MEDIUM | 크롤링 법적 | Pre-Phase 2에 크롤링 법적 검토 추가 |
| R-10 | MEDIUM | 백업 | GCS Versioning + Neo4j 백업 절차 기술 |
| R-11 | MEDIUM | 비용 정확성 | 한국어 토큰 기준 Batch API 비용 재계산 |
| R-12 | MEDIUM | 모델명 불일치 | Embedding 비교 대상 모델 전 문서 통일 |
| R-13 | MEDIUM | 인력 | Phase 2 인력 추가 또는 크롤링/처리 직렬화 |
| R-14 | LOW | Phase 1 오케스트레이션 | Cloud Workflows를 Phase 2로 연기 |
| R-15 | LOW | ML Distillation | Phase 2에서 제거, 운영 최적화 Phase로 분리 |
| R-16 | LOW | 리전 간 비용 | Embedding egress 비용 계산 추가 |

---

## 6. 최종 판정

| 항목 | 판정 |
|------|------|
| **전체 구조 / 논리 흐름** | PASS — Phase 중심 통합 구조 우수 |
| **Phase 0 (검증 + PoC)** | PASS with minor — VAS/RAG 범위 조정 필요 |
| **Phase 1 (MVP)** | CONDITIONAL PASS — 테스트 전략 보완 필요 |
| **Phase 2 (확장 + 크롤링)** | CONDITIONAL PASS — 타임라인/인력 현실성 재검토 필요 |
| **비용 추정** | PASS with minor — 한국어 토큰 기준 재검증 권장 |
| **모니터링 / 운영** | PASS — 상세하고 즉시 활용 가능 |
| **보안 설계** | PASS with minor — PII 법무 선제 검토 추가 필요 |
| **실현 가능성** | **CONDITIONAL PASS** — R-1~R-7 반영 후 실행 권장 |

> **결론**: 전체적으로 잘 설계된 계획이나, CRITICAL 2건(HWP 파싱, Neo4j 전환)과 HIGH 5건의 보완 후 실행을 권장한다. 특히 Phase 2의 타임라인과 인력 계획은 재검토가 필요하며, Anthropic Batch API의 실제 quota 확인이 전체 일정의 핵심 변수이다.
