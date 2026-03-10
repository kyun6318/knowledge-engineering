# 실행 계획 v10 — 27주 통합 로드맵

> 작성일: 2026-03-11 | 기준: 온톨로지 v19, GCP ML Pipeline, GraphRAG Core v2
>
> v9 04_execution_plan.md를 GraphRAG v2 Phase 구조로 통합, v19 온톨로지 반영, GCP 인프라 매핑

---

## 0. 인력 가정

- 1 DE + 1 MLE + 1 도메인 전문가 (파트타임)
- 풀타임 기준; 1인 팀 시 1.5-2× 소요

---

## 1. 전체 로드맵

```
Pre-Phase 0 ─── Week 0 ──── Phase 0 (1주)
                             ├─ GCP 환경 구축
                             ├─ LLM PoC (20건)
                             └─ Go/No-Go

Phase 1 ─────── Week 2-6 ── Core Candidate MVP (5주)
                             ├─ DB 커넥터 + 3-Tier 비교 모듈
                             ├─ CandidateContext 파이프라인
                             ├─ Graph 적재 + 임베딩
                             └─ Agent Serving API MVP

Phase 2 ─────── Week 7-14 ── 파일 통합 + 전체 처리 (8주)
                             ├─ 파일 파서 (PDF/DOCX/HWP)
                             ├─ Neo4j Professional 전환
                             ├─ 450K+ 전체 배치 처리
                             └─ 자동 품질 메트릭

Buffer ─────── Week 15 ──── Phase 2→3 Go/No-Go

Phase 3 ─────── Week 16-22 ── 기업 정보 + 매칭 (7주)
                             ├─ 매칭 알고리즘 설계 (v19 F1-F5)
                             ├─ CompanyContext 파이프라인
                             ├─ Organization ER (Rule + LLM)
                             ├─ MappingFeatures + MAPPED_TO
                             └─ GraphRAG vs Vector 실험

Buffer ─────── Week 23 ──── Phase 3→4 Go/No-Go

Phase 4 ─────── Week 24-27 ── 보강 + 운영 (4주)
                             ├─ 크롤링 파이프라인 (T3/T4)
                             ├─ Gold Test Set 검증
                             ├─ Cloud Workflows 자동화
                             └─ Runbook + Alarm + 핸드오프
```

---

## 2. Pre-Phase 0: 차단 의존성 (Phase 0 2주 전)

### 필수 확보

- [ ] resume-hub / job-hub / code-hub **read replica 접근**
- [ ] JSONB 스키마 확인 (overview.descriptions, requirement.careers 구조)
- [ ] 데이터 커버리지 사전 확인:
  - BRN null 비율 (가정 A19: 40%)
  - workDetails null 비율 (가정 A20: 20%)
  - Skill.code null 비율 (가정 A22: 10% + 비표준 30-50%)
  - resume-hub 적재 완료 여부 (가정 A23)
- [ ] NICE DB 접근 계약
- [ ] Anthropic Batch API 할당량 확인 (tier, 동시 제한, RPD)
- [ ] PII 외부 전송 법률 검토 시작
- [ ] Gemini Flash Batch 대안 테스트 (10건)
- [ ] 샘플 이력서 100건 확보 (DB + 파일)

---

## 3. Phase 0: 환경 구축 + PoC (Week 0-1, 1주)

### 3.1 GCP 환경 (DE, Week 1)

| 작업 | 상세 | 산출물 |
|------|------|--------|
| GCP 프로젝트 초기화 | asia-northeast3, API 활성화 | 프로젝트 ID |
| 서비스 계정 3개 | kg-crawling, kg-processing, kg-loading | IAM 설정 완료 |
| Artifact Registry | Docker 이미지 저장소 | 레지스트리 URL |
| GCS 버킷 | kg-data (버전링), kg-results, kg-backups | 3개 버킷 |
| BigQuery 데이터셋 | kg (quality_metrics, dead_letter, batch_log 테이블) | 스키마 생성 |
| Neo4j AuraDB Free | v19 그래프 스키마 (9 노드, 13 관계) | 인스턴스 URL |
| Vector Index | 768d cosine (text-embedding-005 정합) | 인덱스 생성 |
| Secret Manager | Anthropic API Key, Neo4j 자격증명, DB 접속 정보 | 시크릿 등록 |
| 크롤링 사이트 DOM 분석 | (법률 허용 시) 대상 사이트 구조 파악 | 분석 리포트 |

### 3.2 DB 프로파일링 + LLM PoC (MLE, Week 1)

| 작업 | 상세 | 산출물 |
|------|------|--------|
| resume-hub 프로파일 | Career 수, 이력서당 Career 수(A4), null 비율(A19-A20), SiteUserMapping 분석 | DB Profile |
| job-hub 프로파일 | JD 수, JSONB 구조(A21), skill→code-hub 매핑률 | DB Profile |
| code-hub 프로파일 | HARD_SKILL 수+커버리지, JOB_CLASSIFICATION, INDUSTRY 계층 | DB Profile |
| 비표준 프로파일 (v10) | Tier 1 alias 커버리지, Tier 2 CI+synonym 매칭률 (code-hub attributes JSONB 내 synonyms 필드 커버리지 확인, 50% 미만 시 수동 구축 계획), Tier 3 변이 수 | 3-Tier Profile |
| LLM PoC (20건) | Haiku vs Flash vs Sonnet(10): scope_type/outcomes/signals | 모델 비교 리포트 |
| 임베딩 모델 검증 (20쌍) | text-embedding-005 한국어 분별력 | 임베딩 확인 리포트 |
| Batch API 타이밍 | 소규모 배치 제출→완료 시간 | 타이밍 데이터 |
| 50건 Gold Set | 3-Tier 임계값 캘리브레이션용 수동 검증 | 캘리브레이션 Gold Set |

### 3.3 Phase 0 결정 게이트 (Go/No-Go)

| 결정 항목 | 통과 기준 | 실패 시 |
|----------|----------|---------|
| LLM 모델 | scope_type ≥70%, outcomes F1 ≥50% | Sonnet 전환 (A') |
| 임베딩 모델 | 한국어 분별력 "excellent" | Cohere 또는 embedding-002 폴백 |
| DB 접근 | 3개 DB 모두 접근 가능 | 파일 기반 폴백 (+5-6주) |
| PII 전략 | 법률 검토 완료 | 마스킹 API 기본값 |
| Batch API | 24시간 내 응답 | Gemini Flash 대안 |
| 데이터 품질 | resume-hub ≥80% 적재 | 파일 폴백 비중 확대 |
| Neo4j | APOC 지원, 커넥션 한도 확인 | 대안 검토 |

---

## 4. Phase 1: Core Candidate MVP (Week 2-6, 5주)

### 4.1 DB 커넥터 + 3-Tier 비교 모듈 (Week 2-3, 2주)

#### Week 2: DB 커넥터 + 데이터 매핑

| 작업 | 상세 |
|------|------|
| resume-hub 커넥터 | asyncpg, Career/Skill/Education/CareerDescription/SelfIntroduction |
| job-hub 커넥터 | asyncpg, job/overview/requirement/work_condition/skill |
| code-hub 커넥터 | asyncpg, HARD_SKILL/SOFT_SKILL/JOB_CLASSIFICATION/INDUSTRY |
| 데이터 매핑 | v19 스키마 기준 필드 매핑 (§2, §3 참조) |
| SiteUserMapping 중복 제거 | DB 이력서 기본 중복 탐지 |
| PII 마스킹 모듈 | 이름, 전화번호, 주소 마스킹 |

#### Week 3: 3-Tier 비교 모듈 (v19 §1.5)

| Tier | 구현 | 테스트 |
|------|------|--------|
| Tier 1 | 대학 alias (~200), 기업 alias (~500), 산업코드 code-hub lookup | CI 매칭 정확도 |
| Tier 2 | `normalize_skill()` (CI→synonyms→original), canonical embedding 캐시 (~2K 스킬), threshold 0.85 | 정규화율 |
| Tier 3 | `compare_majors()` (threshold 0.75), `compute_embedding_similarity_batch()` | 임계값 검증 |
| Hybrid | `compute_skill_overlap()` (exact + embedding 가중) | 100건 정확도 |

**Docker 이미지 빌드 → Artifact Registry 푸시**

### 4.2 CandidateContext 파이프라인 (Week 4-5, 2주)

#### Week 4: Pipeline B 구현

| 작업 | 상세 |
|------|------|
| Pydantic 스키마 | v19 CandidateContext 전체 필드 정의 |
| DB 직접 매핑 | company/role/period/tech_stack (Tier 1/2 정규화) |
| LLM 프롬프트 | per-career scope_type/outcomes/signals (positionGradeCode 힌트) |
| Career 수준 추출 | role_evolution, domain_depth, work_style_signals |
| PastCompanyContext | BRN 직접 NICE 매칭, companyName fuzzy 폴백 |
| Batch API 연동 | Anthropic Batch API 제출/수집 모듈 |

#### Week 5: 1,000건 파일럿

| 작업 | 상세 |
|------|------|
| 1,000건 DB 이력서 처리 | Batch API 제출 → 결과 수집 → 검증 |
| 오류 처리 | 3-tier retry, dead-letter queue |
| CompanyContext 간이 | 1,000건 대응 JD의 기본 필드 DB 매핑 (LLM 추출은 Phase 3) |

### 4.3 Graph 적재 + 임베딩 + API (Week 5-6, 2주)

#### Week 5 (4.2와 병렬): Graph 적재

| 작업 | 상세 |
|------|------|
| UNWIND 배치 적재 | Person, Chapter, Skill, Role, Organization, Industry 노드 |
| 관계 적재 | HAS_CHAPTER, NEXT_CHAPTER, PERFORMED_ROLE, USED_SKILL, OCCURRED_AT 등 |
| loaded_batch_id 태그 | 배치 추적용 메타데이터 |
| 3-Tier match_method | 노드별 match_method, normalization_confidence 기록 |
| Vertex AI 임베딩 | 1,000 Chapter × text-embedding-005 → Vector Index |

#### Week 6: Agent Serving API MVP

| 작업 | 상세 |
|------|------|
| FastAPI 구현 | 5개 엔드포인트 (skills, semantic, compound, candidates/{id}, health) |
| Cloud Run Service 배포 | asia-northeast3, auto-scale 1-5 |
| API Key 인증 | 100 req/min rate limit |
| Cypher 쿼리 Q1-Q5 | v19 04_graph_schema.md 기준 5개 핵심 쿼리 |
| 모니터링 | 3개 BigQuery 쿼리 + Slack 알림 |
| Makefile 오케스트레이션 | 수동 파이프라인 실행용 |

### 4.4 Phase 1 산출물

- [x] 1,000건 후보자 그래프 (Neo4j AuraDB Free)
- [x] GraphRAG REST API (5개 엔드포인트)
- [x] API 인증 + rate limiting
- [x] 3-Tier 비교 모듈 (Tier 1/2/3 + hybrid)
- [x] DB 커넥터 (resume-hub, job-hub, code-hub)
- [x] Batch API 연동
- [x] 모니터링 (BigQuery 3개 쿼리 + Slack)

### 4.5 Phase 1 데모 (Week 6)

> "Python 3년 이상 시니어" → 후보자 리스트 REST API 반환

---

## 5. Phase 2: 파일 통합 + 전체 처리 (Week 7-14, 8주)

### 5.0 리팩토링 + 파일 파싱 PoC (Week 7)

| 작업 | 상세 |
|------|------|
| 프로젝트 구조 정리 | 모듈화 (connectors/, extractors/, loaders/, api/) |
| 파일 파서 PoC | PDF (Document AI vs Gemini Multimodal), DOCX, HWP 검증 |
| SimHash 모듈 | 파일 이력서 중복 제거 (DB 이력서는 SiteUserMapping 유지) |
| DB↔파일 교차 중복 | 이름+전화번호 해시 매칭 |

### 5.1 파일 파싱 + 전처리 확장 (Week 8-9)

#### Week 8: 파서 모듈

| 작업 | GCP 리소스 |
|------|-----------|
| PDF 파서 (Document AI OCR + Layout Parser) | Vertex AI Document AI |
| DOCX 파서 (python-docx) | Cloud Run Job: kg-parse |
| HWP 파서 (hwp5/pyhwp) | Cloud Run Job: kg-parse |
| 섹션 분리기 + Career 블록 추출 | Cloud Run Job: kg-parse |

#### Week 9: 전처리 통합

| 작업 | GCP 리소스 |
|------|-----------|
| PII 마스킹 (오프셋 매핑 포함) | Cloud Run Job: kg-preprocess |
| 기술 사전 / 기업 사전 확장 | code-hub 기반 |
| SimHash 모듈 배포 | Cloud Run Job: kg-preprocess |
| Docker 이미지 빌드 + 등록 | Artifact Registry |

**Cloud Run Jobs 설정**:
- `kg-parse`: 50 병렬 태스크 (Neo4j 접근 없음)
- `kg-graph-load`: **≤5 태스크** (Neo4j 커넥션 풀)

### 5.2 Neo4j Professional 전환 (Week 10 시작, 1일)

| 작업 | 상세 |
|------|------|
| Free → Professional 전환 | 데이터 마이그레이션 |
| Vector Index 재생성 | 768d cosine 확인 |
| 인덱스 최적화 | v19 인덱싱 전략 적용 |

### 5.3 전체 배치 처리 (Week 10-14, 5주)

#### 처리 시간 계산

```
DB 이력서: 500K ÷ 1,000/청크 = 500 청크
파일 이력서: 100K ÷ 1,000/청크 = 100 청크
총: 600 청크 × 10 동시 배치 = 60 라운드

낙관 (6시간/라운드): 15일 → Week 12 완료 (100%)
기준 (12시간/라운드): 30일 → Week 14 완료 (100%)
비관 (24시간/라운드): 60일 → Week 14에 ~80% → Phase 3 백그라운드 계속
```

**SLA**: CRITICAL <30분, WARNING <2시간 (업무 시간) / 야간 fire-and-forget + auto-retry

#### 자동 배치 결과 수집
- 30분 Cloud Scheduler 폴링
- dead-letter 자동 재처리

### 5.4 자동 품질 메트릭 + 벤치마크 (Week 10-14 병렬)

| 메트릭 | 목표 | 자동 체크 |
|--------|------|----------|
| schema_compliance | ≥95% | 배치 완료 시 |
| required_field_rate | ≥90% | 배치 완료 시 |
| distribution_anomaly | 정상 범위 | 주간 |
| prompt_version_comparison | <5% 품질 차이 | 프롬프트 변경 시 |
| 통계 샘플링 (384건) | 95% CI, ±5% 오차 | Phase 2 완료 시 |
| Cypher 쿼리 벤치마크 | p95 <2초 (360K+) | Phase 2 완료 시 |

### 5.5 Buffer Week 15: Phase 2→3 Go/No-Go

| 체크 항목 | 기준 |
|----------|------|
| 처리 완료율 | ≥80% (360K+) |
| 자동 품질 메트릭 | schema ≥95%, fields ≥90% |
| 쿼리 벤치마크 | p95 <2초 |
| Golden 50 회귀 테스트 | 통과 |
| Neo4j 스냅샷 백업 | 완료 |

### 5.6 Phase 2 산출물

- [x] 파일 파서 (PDF/DOCX/HWP)
- [x] 전처리 모듈 (SimHash, PII 마스킹)
- [x] Neo4j Professional + UNWIND 배치 적재
- [x] 80%+ 전체 처리 (360K+)
- [x] 자동 품질 메트릭 (BigQuery)
- [x] 쿼리 벤치마크 (p95 <2초)
- [x] Golden 50 회귀 테스트

---

## 6. Phase 3: 기업 정보 + 매칭 (Week 16-22, 7주)

### 6.0 매칭 알고리즘 설계 문서 (Week 16, 2일)

> v19 MappingFeatures 확정 가중치 기반

| 특성 | 가중치 | 계산 방법 |
|------|--------|----------|
| F1 stage_match | 25% | v19 A4 STAGE_SIMILARITY 4×4 매트릭스 |
| F2 vacancy_fit | 30% | hiring_context + situational_signals 정합 |
| F3 domain_fit | 20% | 임베딩 + code-hub 산업코드 |
| F4 culture_fit | 10% | operating_model vs work_style (대부분 INACTIVE) |
| F5 role_fit | 15% | seniority + role_evolution (v19 A1 매핑) |

**역매칭**: 2단계 (벡터 근사 Top-K + fine-grained scoring)
**MAPPED_TO 임계값**: 0.4
**검증**: 50건 수동, Top-10 적합도 70%+

### 6.1 JD 파서 + Vacancy 노드 (Week 16-17)

| 작업 | 상세 |
|------|------|
| job-hub DB 쿼리 | overview, requirement, work_condition, skill |
| Vacancy Pydantic 스키마 | v19 01_company_context.md 기준 |
| Vacancy 노드 생성 | UNWIND 배치 적재 |
| REQUIRES_ROLE, REQUIRES_SKILL 관계 | Tier 2 정규화 매칭 |
| Vacancy 임베딩 | text-embedding-005 → Vector Index |

### 6.2 CompanyContext 파이프라인 (Week 17-18)

| 작업 | 상세 |
|------|------|
| Pydantic 스키마 | v19 CompanyContext 전체 필드 |
| DB 직접 매핑 | §2.1 (LLM 비용 $0) |
| NICE Lookup | BRN 기반 stage_estimate Rule |
| LLM 추출 | vacancy scope_type, role_expectations, operating_model, structural_tensions |
| Organization 노드 | UNWIND 배치 적재, IN_INDUSTRY 관계 |

### 6.3 Organization ER + 한국어 특수 처리 (Week 19-20, 2주)

#### Week 19: Rule 기반 1차 매칭

| 작업 | 상세 |
|------|------|
| 이름 정규화 | "삼성" = "SAMSUNG" = "Samsung" 통일 |
| 자회사/개명 사전 | 사전 구축 (Phase 2 중 준비) |
| Levenshtein ≤2 | 오탈자 허용 |
| 500건 수동 검증 | Rule 매칭 정확도 확인 |

#### Week 20: LLM 2차 매칭 + 풀 검증

| 작업 | 상세 |
|------|------|
| 모호 케이스 LLM 판정 | "토스" ≠ "비바리퍼블리카" but 동일 기업 |
| 법인 분리 확인 | "카카오" ≠ "카카오뱅크" (별개 법인) |
| 1,000건+ 풀 검증 | Rule + LLM 통합 정확도 |
| org_id 확정 | BRN → org_id 최종 매핑 |

### 6.4 MappingFeatures + MAPPED_TO (Week 20-22, 6.3과 부분 겹침)

| 작업 | 상세 |
|------|------|
| 5대 특성 계산 모듈 | `compute_match_score()` (§6.3-6.4 of 01_extraction_pipeline.md) |
| Shortlisting | 벡터 근사 Top-K 후보 선정 |
| Fine-grained Scoring | 5대 특성 가중 합산 |
| MAPPED_TO 관계 생성 | UNWIND 배치, score ≥ 0.4 |
| BigQuery 적재 | kg.mapping_features 테이블 |
| 50건 수동 검증 | Top-10 적합도 70%+ |

### 6.5 GraphRAG vs Vector Baseline 실험 (Week 21-22, 6.4와 병렬)

> v19 05_evaluation_strategy.md 기반

| 항목 | 상세 |
|------|------|
| 설계 | 50 JD × 5 평가자, paired t-test |
| A 조건 | GraphRAG (5대 특성 매칭) |
| B 조건 | Vector Baseline (text-embedding-005 cosine) |
| B' 조건 (선택) | Vector + LLM Reranking (Gemini Flash) |
| 메트릭 | Precision@5, Recall@5, NDCG@5, MRR |
| 효과 크기 | Cohen's d ≥ 0.5 |
| 결정 | Case 1-4 (v19 Decision Tree) |

### 6.6 API 확장 (Week 22)

| 엔드포인트 | 설명 |
|-----------|------|
| POST /api/v1/match/jd-to-candidates | JD → 후보자 매칭 |
| POST /api/v1/match/candidate-to-jds | 후보자 → JD 역매칭 |
| GET /api/v1/companies/{org_id} | 기업 정보 |

### 6.7 Buffer Week 23: Phase 3→4 Go/No-Go

| 체크 항목 | 기준 |
|----------|------|
| GraphRAG vs Vector 실험 결과 | Cohen's d ≥ 0.5 |
| 매칭 Top-10 적합도 | ≥70% |
| Organization ER 정확도 | 1,000건+ 검증 완료 |
| Phase 2 백그라운드 완료 | ≥95% |
| 코드 정리 | 기술 부채 해소 |
| 법률 최종 검토 | 크롤링 가능 여부 확정 |

### 6.8 Phase 3 산출물

- [x] 매칭 알고리즘 설계 문서 (v19 F1-F5 가중치)
- [x] JD 파서 + Vacancy 노드
- [x] CompanyContext 파이프라인 (NICE + Rule + LLM)
- [x] Organization ER (Rule + LLM, 1,000건+ 검증)
- [x] MappingFeatures + MAPPED_TO (5대 특성, ≥0.4 임계값)
- [x] GraphRAG vs Vector Baseline 실험 결과
- [x] API 확장 (매칭 + 기업 엔드포인트)

### 6.9 Phase 3 데모 (Week 22)

> 360K+ 후보자 매칭, 점수 포함, 기업 필터 가능

---

## 7. Phase 4: 보강 + 운영 (Week 24-27, 4주)

### 7.1 크롤링 파이프라인 (Week 24-25, 2주)

> v19 06_crawling_strategy.md 기반

#### Week 24: 크롤러 구축

| 작업 | GCP 리소스 |
|------|-----------|
| Playwright Docker 이미지 | Cloud Run Job: kg-crawl |
| 홈페이지 크롤러 (1,000 기업) | P1-P6 페이지 유형 |
| 뉴스 수집기 (Naver News API + TheVC) | N1-N5 기사 유형 |
| 크롤링 정책 문서 | robots.txt, 2초 간격, 최대 10페이지 |
| BigQuery 스키마 | crawl_company_targets, crawl_raw_data, crawl_extracted_fields |

#### Week 25: LLM 추출 + 적재

| 작업 | 상세 |
|------|------|
| Gemini Flash 추출 | product_description, market_segment, funding, growth_narrative |
| CompanyContext 보강 적재 | Organization 노드 필드 업데이트 |
| 100개 기업 파일럿 | 정확도 검증 |
| 오류 처리 + 자동 재시도 | 403/429/Cloudflare 대응 |

**Phase 4 범위**: 기본 필드만 (product, funding, employee, growth)
**Phase 5 이후**: tension_type, culture_signals, scale_signals

### 7.2 Gold Test Set 검증 (Week 26, 3일)

> v19 05_evaluation_strategy.md + GraphRAG v2 정합

| 항목 | 상세 |
|------|------|
| 검증 규모 | 200 후보-매칭 쌍 |
| 전문가 | 2명 × $5,840 Gold Label 예산 |
| 확보 시점 | Week 22에 사전 섭외 (3-4주 리드 타임) |

| 메트릭 | 목표 |
|--------|------|
| scope_type accuracy | >70% |
| outcome F1 | >55% |
| situational_signal F1 | >50% |
| vacancy scope accuracy | >65% |
| stage_estimate accuracy | >75% |
| features ACTIVE rate | >80% |
| human correlation | >0.4 |

### 7.3 Cloud Workflows 자동화 (Week 26, 1주)

| 작업 | 상세 |
|------|------|
| Makefile → Cloud Workflows 전환 | 전체 DAG 자동화 |
| 증분 파이프라인 | 일일 ~1,000건 (updated_at 기반 변경 감지) |
| 이력서 업데이트 처리 | DETACH DELETE old Chapters + 재생성 |

**Cloud Scheduler 4개 Job**:

| Job | Cron | 대상 |
|-----|------|------|
| kg-incremental-daily | `0 2 * * *` | 증분 파이프라인 |
| kg-dead-letter-daily | `0 4 * * *` | dead-letter 재처리 |
| crawl-monthly | `0 0 1 * *` | 1,000 기업 크롤링 |
| neo4j-weekly-backup | `0 3 * * 0` | Neo4j 백업 |

### 7.4 Runbook + Alarm + 핸드오프 (Week 27, 1주)

#### Runbook 5

| # | 상황 | 대응 |
|---|------|------|
| 1 | Batch API 장애 | Gemini Flash 폴백, 재시도 전략 |
| 2 | Neo4j 연결 장애 | 커넥션 풀 리셋, AuraDB 상태 확인 |
| 3 | 크롤링 차단 (403/429) | User-Agent 변경, 대기 시간 증가, 프록시 |
| 4 | 품질 이상 (schema <95%) | 프롬프트 롤백, 샘플 수동 검토 |
| 5 | 증분 파이프라인 장애 | dead-letter 확인, DB 변경 감지 리셋 |

#### Alarm 10

| 등급 | 알람 | 조건 |
|------|------|------|
| CRITICAL (즉시) | Neo4j 다운 | 5분 무응답 |
| CRITICAL | Batch 3회 연속 실패 | 3회 실패 |
| CRITICAL | 증분 2일 연속 실패 | 2일 실패 |
| WARNING (당일) | schema compliance | <95% |
| WARNING | dead-letter 비율 | >5% |
| WARNING | 노드 수 이상 변동 | ±10% |
| WARNING | dead-letter 누적 | >5% |
| INFO (주간) | 일일 적재 수 | 로그 |
| INFO | 일일/주간 비용 | 로그 |
| INFO | 크롤링 성공률 | 로그 |

#### Neo4j 백업 + 롤백

- 주간 자동 백업 (Cloud Scheduler)
- GCS 버전닝
- 롤백 전략: loaded_batch_id 기반 선택적 삭제

#### 핸드오프 문서

10개 섹션: 아키텍처 개요, 일일 체크리스트, Runbook 절차, 증분 파이프라인, 크롤링 파이프라인, 프롬프트 업데이트, 사전 업데이트, Neo4j 백업/복원, 비용 모니터링, Secret Manager 로테이션

#### 운영 인력

- 0.3-0.5 FTE (주 1-2일)
- 온콜 로테이션

### 7.5 Phase 4 산출물

- [x] 크롤링 파이프라인 (1,000 기업, T3/T4)
- [x] Gemini Flash 추출 (기본 필드)
- [x] CompanyContext 보강
- [x] Gold Test Set 200건 검증 완료
- [x] Cloud Workflows DAG + Cloud Scheduler 4개 Job
- [x] Runbook 5 + Alarm 10
- [x] Neo4j 백업 자동화
- [x] 증분 파이프라인 (일일 + dead-letter + 월간 크롤링 + 주간 백업)
- [x] 운영 핸드오프 문서

---

## 8. 타임라인 요약

```
Week 0  : Pre-Phase 0 (DB 접근 확보)
Week 1  : Phase 0 — GCP 환경 + PoC + Go/No-Go
Week 2-3: Phase 1-1 — DB 커넥터 + 3-Tier 비교 모듈
Week 4-5: Phase 1-2,3 — CandidateContext + 1,000건 파일럿
Week 5-6: Phase 1-4 — Graph 적재 + API MVP
          ★ Week 6 데모: "Python 3yrs+ senior" → 후보자 리스트

Week 7  : Phase 2-0 — 리팩토링 + 파일 파싱 PoC
Week 8-9: Phase 2-1 — 파서 + 전처리 확장
Week 10 : Phase 2-2 — Neo4j Professional 전환
Week 10-14: Phase 2-3 — 전체 배치 처리 (600K)
            Phase 2-4 — 자동 품질 메트릭 (병렬)
          ★ Week 14: 360K+ 후보자 검색 가능 (80%+)

Week 15 : Buffer — Phase 2→3 Go/No-Go

Week 16 : Phase 3-0 — 매칭 알고리즘 설계 (v19 F1-F5)
Week 16-17: Phase 3-1 — JD 파서 + Vacancy
Week 17-18: Phase 3-2 — CompanyContext 파이프라인
Week 19-20: Phase 3-3 — Organization ER (Rule + LLM)
Week 20-22: Phase 3-4 — MappingFeatures + MAPPED_TO
Week 21-22: Phase 3-5 — GraphRAG vs Vector 실험 (병렬)
Week 22 : Phase 3-6 — API 확장
          ★ Week 22: 매칭 점수 + 기업 필터 가능

Week 23 : Buffer — Phase 3→4 Go/No-Go

Week 24-25: Phase 4-1 — 크롤링 파이프라인
Week 26 : Phase 4-2,3 — Gold Test + Workflows 자동화
Week 27 : Phase 4-4 — Runbook + Alarm + 핸드오프
          ★ Week 27: 프로덕션 운영 (자동화 + 모니터링)
```

---

## 9. 핵심 결정 포인트

| 시점 | 결정 | 영향 |
|------|------|------|
| Pre-Phase 0 | DB 접근 (3개 DB) + NICE 계약 | 전체 시작 가능 여부 |
| Phase 0 | LLM 모델 / 임베딩 모델 / PII 전략 | 비용 + 품질 결정 |
| Phase 0 | DB 접근 불가 시 | 파일 기반 폴백 (+5-6주) |
| Phase 1 | Batch API 할당량 부족 시 | Gemini Flash 대안 |
| Phase 2 | 처리율 <80% 시 | Phase 3 진입 지연 |
| Phase 3 | GraphRAG vs Vector 실험 결과 | Case 1-4 v2 전략 분기 |
| Phase 3 | 법률 크롤링 불가 시 | Phase 4 DB-only (크롤링 제외) |
| Phase 4 | Gold Label 품질 미달 시 | 프롬프트 최적화 또는 Sonnet 전환 |

---

## 10. v9 → v10 타임라인 비교

| 항목 | v9 | v10 | 변화 |
|------|-----|-----|------|
| Phase 0 | 2-3주 | **1주** | GCP 환경 간소화, 사전 의존성 분리 |
| Phase 1 | 6-8주 | **5주** | DB 커넥터 효율화, API MVP 포함 |
| Phase 2 | 3-4주 | **8주** | 파일 파싱 추가, 전체 처리 포함 |
| Phase 3 | - | **7주** | 기업 정보 + 매칭 (v9에는 없음) |
| Phase 4 | - | **4주** | 크롤링 + 운영 (v9에는 없음) |
| Buffer | 없음 | **2주** | Go/No-Go 게이트 |
| **총계** | **14-17주 (MVP)** | **27주 (프로덕션)** | MVP→프로덕션 전체 범위 |
| 첫 데모 | ~12주 | **Week 6** | GraphRAG v2 정합 |
| 80%+ 처리 | ~14주 | **Week 14** | 동일 시점 |

**핵심 차이**: v9는 MVP 범위, v10은 프로덕션 전체 범위 (매칭 + 크롤링 + 운영 포함)

---

## 11. 테스트 전략

| 테스트 유형 | 대상 | 기준 |
|-----------|------|------|
| 단위 | DB 커넥터, 3-Tier 모듈, Pydantic 스키마 | 커버리지 80%+ |
| 통합 | 단일 이력서/JD E2E | 전 파이프라인 통과 |
| 멱등성 | 2× 적재 시 노드/엣지 수 불변 | 완벽 멱등 |
| 배치 | 1K 청크 처리 | <5% 오류, <2시간 |
| 품질 | 50건 수동 검증 | scope_type ≥70%, outcomes F1 ≥50% |
| 파워 | 50건 Cohen's d | ≥0.5 |
| 스케일 | 600K 전체 처리 | <3% 오류, <30일 |
| 회귀 | 프롬프트 변경 시 50건 | <5% 품질 차이 |
| v7 vs v8 비교 | 50건 | v8 ≥ v7 품질 |
| GraphRAG vs Vector | 50 JD × 5 평가자 | Cohen's d ≥ 0.5 |
