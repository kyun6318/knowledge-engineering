# v9 → v10 변경 이력

> 작성일: 2026-03-11 | 기준: 온톨로지 v19 + GCP ML Pipeline + GraphRAG Core v2

---

## 1. 변경 동기

v9는 온톨로지 v11 기준으로 작성되었으나, 이후 v19까지 8개 버전의 온톨로지 개정이 진행됨.
동시에 GCP ML Platform 인프라 설계(03.ml_pipeline)와 GraphRAG Core v2 구현 계획(04.graphrag)이 확정되어,
세 문서 간 불일치를 해소하고 단일 실행 계획으로 통합할 필요가 발생.

---

## 2. 핵심 변경 사항

### 2.1 온톨로지 v19 정합 (v11 → v19)

| 항목 | v9 (v11 기준) | v10 (v19 기준) | 영향 |
|------|-------------|---------------|------|
| Amendments | A1-A10 별도 관리 | **A1-A10 본문 통합 완료** | 스키마 참조 단순화 |
| Data Source Mapping | 개략적 | **00_data_source_mapping.md 상세 매핑** (code-hub 중심) | 파이프라인 입력 명확화 |
| MappingFeatures 가중치 | 미정의 | **F1-F5 확정** (vacancy=30%, stage=25%, domain=20%, role=15%, culture=10%) | Pipeline D 구현 확정 |
| STAGE_SIMILARITY | 언급만 | **4×4 매트릭스 확정** + 캘리브레이션 계획 | stage_match 계산 확정 |
| Evaluation Strategy | 50 샘플 수동 검증 | **GraphRAG vs Vector Baseline 실험 설계** (50 JD, 5 평가자, paired t-test) | Phase 2 평가 고도화 |
| Crawling Strategy | Phase 3 간략 | **v19 06_crawling_strategy.md** (T3 홈페이지 + T4 뉴스, 6주 계획) | Phase 3 구체화 |
| Graph Schema | 9 노드 기본 | **v19 통합판** (A2 Industry 노드, A5 Company 관계 제외 명문화) | 그래프 적재 정합 |
| ScopeType→Seniority | 암묵적 | **A1 매핑 테이블 확정** (EXECUTIVE→C_LEVEL 등) | CandidateContext 추출 반영 |
| Embedding 기반 비교 | A9 원칙만 | **v19 §1.5 3-Tier 전략 + 임계값 확정** | 비교 모듈 구현 확정 |

### 2.2 GCP 인프라 통합 (신규)

| 항목 | v9 | v10 | 비고 |
|------|-----|-----|------|
| 컴퓨팅 | 미정 | **Cloud Run Jobs** (배치) + **Cloud Run Service** (API) | 03.ml_pipeline 정합 |
| 오케스트레이션 | Prefect vs Cloud Workflows 미결정 | **Cloud Workflows** 확정 | GraphRAG v2 정합 |
| 상태 저장 | 미정 | **BigQuery** (메트릭/로그) + **Firestore** (상태) | GCP 네이티브 |
| 스케줄링 | 미정 | **Cloud Scheduler** (4개 Job) | GraphRAG v2 정합 |
| 임베딩 모델 | text-multilingual-embedding-002 | **text-embedding-005** (768d) | GraphRAG v2 표준화 |
| 서비스 계정 | 미정 | **3개 분리** (kg-crawling/kg-processing/kg-loading) | 최소 권한 원칙 |
| 컨테이너 | 미정 | **Artifact Registry** + Docker | GCP 표준 |
| 비밀 관리 | 미정 | **Secret Manager** | API 키, DB 자격증명 |
| 리전 | 미정 | **asia-northeast3** (서울) / Vertex AI: us-central1 | 데이터 주권 |

### 2.3 GraphRAG Core v2 정합

| 항목 | v9 | v10 | 비고 |
|------|-----|-----|------|
| 파일 파싱 | **제거** (DB-only) | **DB-first + 파일 폴백** | GraphRAG v2 Phase 2 포함 |
| 중복 제거 | SiteUserMapping only | **SiteUserMapping + SimHash 폴백** (파일 파싱 대상) | 하이브리드 |
| Agent Serving API | 없음 | **FastAPI + Cloud Run** (5개 엔드포인트) | Phase 1 MVP 포함 |
| UNWIND 배치 적재 | MERGE 기반 | **UNWIND 배치** + loaded_batch_id/loaded_at 태그 | 성능 최적화 |
| 자동 품질 메트릭 | 수동 | **BigQuery quality_metrics 테이블** + 통계 샘플링 | Phase 2 자동화 |
| Runbook/Alarm | 없음 | **Runbook 5 + Alarm 10** (Phase 4 구축) | 운영 체계화 |
| Neo4j 마이그레이션 | 미정 | **AuraDB Free → Professional** (Phase 2 시작 시) | 명시적 전환점 |
| Vector Index | 미정 | **768d + cosine** (text-embedding-005 정합) | 통일 |

### 2.4 충돌 해소

| 충돌 | 해소 방안 |
|------|----------|
| DB-only(v9) vs 파일 파싱 포함(GraphRAG v2) | **DB-first 원칙 유지** + resume-hub에 없는 이력서(~20%)는 파일 파싱 폴백 |
| embedding-002(v9) vs embedding-005(GraphRAG v2) | **text-embedding-005 (768d)** 단일 표준화. Phase 0 한국어 검증 후 확정 |
| SiteUserMapping(v9) vs SimHash(GraphRAG v2) | **SiteUserMapping 우선** (DB 이력서) + **SimHash 보조** (파일 이력서) |
| v19 매칭 가중치 vs GraphRAG v2 가중치 | **v19 확정 가중치 사용** (온톨로지가 canonical source) |
| 타임라인 14-17주(v9) vs 27주(GraphRAG v2) | **27주 기준** 통합 (GraphRAG v2의 Phase 구조 채택, v9 효율성 반영) |

---

## 3. 문서 구조 변경

| v9 문서 | v10 문서 | 변경 |
|---------|---------|------|
| 01_v1_gap_analysis.md | 00_v9_to_v10_changelog.md (본 문서) | gap 분석 → 변경 이력으로 전환 |
| 02_extraction_pipeline.md | 01_extraction_pipeline.md | v19 스키마 + GCP 인프라 반영 |
| 03_model_candidates_and_costs.md | 02_model_and_infrastructure.md | 모델 + GCP 인프라 비용 통합 |
| 04_execution_plan.md | 03_execution_plan.md | 27주 통합 실행 계획 |
| 05_assumptions_and_risks.md | 04_assumptions_and_risks.md | GCP + GraphRAG 리스크 추가 |
| (없음) | 05_operations_and_monitoring.md | 운영/모니터링 신규 |
