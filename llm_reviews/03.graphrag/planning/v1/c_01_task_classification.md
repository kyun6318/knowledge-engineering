# V5 태스크별 팀 분류 테이블

> v5 실행계획(core/5/) 7개 문서의 **모든 태스크**를 S&F / GraphRAG / 공동으로 분류한다.
> 팀 표기: **S** = S&F 팀, **G** = GraphRAG 팀, **공** = 공동

---

## Phase 0: 환경 + PoC (1주, Week 1)

| # | 태스크 | v5 담당 | 분리 후 | 근거 |
|---|--------|--------|--------|------|
| 0-1 | GCP 환경 구성 (API, 서비스계정 3개, GCS, BQ) | DE | **공** | 공용 인프라 |
| 0-2 | BigQuery 테이블 5개 생성 | DE | **S** | 전처리 추적용 |
| 0-3 | Neo4j AuraDB Free + 스키마 + Vector Index | DE | **G** | 그래프 인프라 |
| 0-4 | DB 프로파일링 100건 | MLE | **S** | 원본 데이터 분석 |
| 0-5 | 일일 유입량 확인 (N4) | MLE | **S** | 증분 주기 결정용 |
| 0-6 | Career 수 분포 확인 (v12 M1) | MLE | **S** | 적응형 호출 전략 |
| 0-7 | LLM 추출 PoC 20건 + 적응형 호출 검증 | MLE | **S** | LLM 프롬프트 최적화 |
| 0-8 | Embedding 모델 확정 + 분별력 테스트 | MLE | **S** | 벡터 품질 |
| 0-9 | Batch API 응답 시간 실측 | MLE | **S** | Batch 운영 계획 |
| 0-10 | Gemini Flash Batch 대안 검증 (N5) | MLE | **S** | Provider 선택 |
| 0-11 | 크롤링 대상 사이트 구조 분석 | DE | **S** | 크롤링 설계 |
| 0-12 | Go/No-Go 판정 | 공동 | **공** | S&F 결과 기반 공동 판단 |
| 0-13 | PoC 비용 외삽 (v5 A2) | 공동 | **S** | LLM 비용 추정 |

---

## Phase 1: Core Candidate MVP (5주, Week 2~6)

| # | 태스크 | v5 담당 | 분리 후 | 근거 |
|---|--------|--------|--------|------|
| 1-A | 크롤링 파이프라인 (법무 허용 시) | DE | **S** | 데이터 수집 |
| 1-B-1 | CMEK 버킷 + KMS 키 생성 (R3) | DE | **S** | PII 인프라 |
| 1-B-2 | PII 마스킹 re.sub 콜백 (R1, v12 S4 전화번호 8종) | MLE | **S** | 전처리 |
| 1-B-3 | PII 매핑 → GCS CMEK 저장 (v12 S2) | MLE | **S** | PII 보관 |
| 1-B-4 | Career 블록 분리 | MLE | **S** | 구조화 |
| 1-C-1 | CandidateContext LLM 추출 1,000건 (v12 프롬프트) | MLE | **S** | LLM 추출 |
| 1-C-2 | 적응형 호출 (1-pass / N+1 pass, v12 M1) | MLE | **S** | 호출 전략 |
| 1-D-1 | Person 노드 → Neo4j UNWIND 배치 (G-1) | DE | **G** | 그래프 적재 |
| 1-D-2 | Chapter + HAS_CHAPTER 관계 (G-2, v19) | DE | **G** | 그래프 적재 |
| 1-D-3 | Skill + Role + Organization 노드 (G-3) | MLE | **G** | 그래프 적재 |
| 1-D-4 | Industry 노드 + IN_INDUSTRY (G-4) | MLE | **G** | 그래프 적재 |
| 1-D-5 | Embedding 생성 (Vertex AI, 768d, 1,000건, G-5) | MLE | **S** | 벡터 생성 |
| 1-D-6 | Vector Index 적재 (G-6) | DE | **S** | 벡터 인덱스는 S&F 검색용 |
| 1-D-7 | Idempotency + 롤백 테스트 (G-7) | 공동 | **G** | 그래프 무결성 |
| 1-D-8 | Cypher 쿼리 5종 작성 (G-8, v19) | MLE | **G** | 그래프 검색 |
| 1-D-9 | 에이전트 서빙 API + PII 필드 정의 (G-9, N2) | MLE | **G** | API 서빙 |
| 1-D-10 | Cloud Scheduler health check 설정 (G-10, N1) | DE | **G** | 그래프 인프라 |
| 1-D-11 | E2E 검증 + 스팟체크 50건 (G-11) | 공동 | **공** | 품질 검증 |

---

## Phase 2: 파일 이력서 + 전체 처리 (9주, Week 7~15)

| # | 태스크 | v5 담당 | 분리 후 | 근거 |
|---|--------|--------|--------|------|
| 2-0-1 | 코드 리팩토링 + 프로젝트 구조 정리 | DE | **S** | 전처리 코드 |
| 2-0-2 | LLM Provider 추상화 레이어 (N5) | MLE | **S** | LLM 인프라 |
| 2-0-3 | 파일 파싱 PoC (PDF/DOCX/HWP) | MLE | **S** | 파서 검증 |
| 2-1-1 | PDF/DOCX 파서 모듈 | DE | **S** | 파일 파싱 |
| 2-1-2 | HWP 파서 모듈 | MLE | **S** | 파일 파싱 |
| 2-1-3 | Hybrid 섹션 분리 (패턴→LLM 폴백, v12 S1) | MLE | **S** | 구조화 |
| 2-1-4 | LLM 폴백 Batch API 처리 (R4) | MLE | **S** | Batch 최적화 |
| 2-1-5 | 파일 소스 confidence 패널티 (v12 §4.1.2) | MLE | **S** | 품질 보정 |
| 2-2-1 | Neo4j Professional 전환 + 사이징 검증 (N8) | DE | **G** | 그래프 인프라 |
| 2-2-2 | AuraDB Free→Professional 마이그레이션 (v5 A3) | DE | **G** | 마이그레이션 |
| 2-3-1 | DB 500K Batch 처리 (R6: 우선 처리) | 공동 | **S** | Batch 운영 |
| 2-3-2 | 파일 100K Batch 처리 (후순위) | 공동 | **S** | Batch 운영 |
| 2-3-3 | 비관 시나리오 대응: Phase 3 Batch 할당 | 공동 | **S** | Batch 계획 |
| 2-3-4 | 처리 완료분 → Neo4j Bulk Loading | DE | **G** | 대량 적재 |
| 2-4-1 | 자동 품질 메트릭 (schema/field/pii/adaptive) | MLE | **S** | 품질 측정 |
| 2-4-2 | 쿼리 성능 벤치마크 (Cypher 5종 × 480K+) | MLE | **G** | 그래프 성능 |
| 2-4-3 | 통계적 샘플링 384건 | 공동 | **S** | 품질 검증 |
| 2-BUF | 버퍼 1주 Go/No-Go (W16) | 공동 | **공** | 판정 |

---

## Phase 3: 기업 정보 + 매칭 (6주, Week 17~22)

| # | 태스크 | v5 담당 | 분리 후 | 근거 |
|---|--------|--------|--------|------|
| 3-0 | 매칭 알고리즘 설계 문서 + MAPPED_TO 규모 추정 (N3) | MLE | **G** | 매칭 핵심 |
| 3-1-1 | JD 파서 (job-hub API JSON 수신, v5 A1) | DE | **S** | 데이터 파싱 |
| 3-1-2 | Vacancy 노드 + 관계 적재 (v19: HAS_VACANCY 등) | DE | **G** | 그래프 적재 |
| 3-2-1 | CompanyContext DB 직접 매핑 (v12 §2.1) | MLE | **S** | 속성 추출 |
| 3-2-2 | CompanyContext NICE Lookup Rule (v12 §2.2) | MLE | **S** | 외부 데이터 |
| 3-2-3 | CompanyContext LLM 추출 (v12 §1) | MLE | **S** | LLM 추출 |
| 3-2-4 | operating_model 진정성 체크 (v12 C3) | MLE | **S** | 검증 로직 |
| 3-3-1 | Organization ER + 한국어 특화 (계열사 사전) | DE | **G** | 그래프 ER |
| 3-3-2 | Organization ER NICE+BigQuery 조인 | DE | **공** | S&F 데이터 + G 적재 |
| 3-4-1 | MappingFeatures 5-피처 스코어링 구현 | MLE | **G** | 매칭 알고리즘 |
| 3-4-2 | MAPPED_TO 관계 생성 (임계값 0.4) | MLE | **G** | 그래프 관계 |
| 3-4-3 | 가중치 수동 튜닝 (v4 O3) | MLE | **G** | 매칭 최적화 |
| 3-5-1 | 통합 테스트 + Regression Test | 공동 | **공** | 품질 검증 |
| 3-5-2 | 매칭 50건 수동 검증 | 공동 | **G** | 매칭 품질 |
| 3-N9 | 잔여 배치 처리 주간 리포트 | 공동 | **S** | Batch 현황 |
| 3-BUF | 버퍼 1주 Go/No-Go (W23) | 공동 | **공** | 판정 |

---

## Phase 4: 외부 보강 + 운영 (4주, Week 24~27)

| # | 태스크 | v5 담당 | 분리 후 | 근거 |
|---|--------|--------|--------|------|
| 4-1 | 홈페이지/뉴스 크롤링 파이프라인 | DE | **S** | 데이터 수집 |
| 4-2 | CompanyContext 보강 적재 (기본 필드) | MLE | **G** | 그래프 보강 |
| 4-3 | 품질 평가 Gold Label 100→200건 (N6) | 공동 | **G** | 매칭 품질 |
| 4-4-1 | Cloud Workflows DAG 구성 | DE | **G** | 자동화 |
| 4-4-2 | 증분 처리: 변경 감지 (created/updated/deleted) | MLE | **G** | 그래프 증분 |
| 4-4-3 | DETACH DELETE 2단계 통합 (R8) | MLE | **G** | 그래프 삭제 |
| 4-4-4 | 소프트 삭제 + Cypher 마이그레이션 (R7) | MLE | **G** | 쿼리 마이그레이션 |
| 4-4-5 | is_active 인덱스 + API 미들웨어 | MLE | **G** | API 보호 |
| 4-5-1 | Runbook 5종 | 공동 | **G** | 운영 |
| 4-5-2 | Alarm 10종 + Slack Webhook | 공동 | **G** | 모니터링 |
| 4-5-3 | Cloud Run Cold Start 대응 (v5 A4) | DE | **G** | 서빙 최적화 |
| 4-5-4 | 인수인계 문서 | 공동 | **공** | 인수인계 |

---

## 분류 집계

| 팀 | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | **합계** |
|----|---------|---------|---------|---------|---------|--------|
| **S&F (S)** | 10 | 8 | 10 | 6 | 1 | **35** |
| **GraphRAG (G)** | 1 | 7 | 4 | 7 | 10 | **29** |
| **공동 (공)** | 2 | 1 | 2 | 3 | 1 | **9** |
| **합계** | 13 | 16 | 16 | 16 | 12 | **73** |

> Phase 0~2는 S&F 태스크가 압도적으로 많고, Phase 3~4는 GraphRAG 태스크가 주류이다.
> 이는 "전처리/추출 → 그래프 적재/매칭" 순서와 정확히 일치한다.
