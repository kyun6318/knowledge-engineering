# 가정 및 리스크 v10

> 작성일: 2026-03-11 | 기준: 온톨로지 v19, GCP ML Pipeline, GraphRAG Core v2
>
> v9 05_assumptions_and_risks.md 기반 + GCP/GraphRAG 리스크 추가

---

## 1. 가정 목록 (A1-A32)

### 데이터 볼륨

| ID | 가정 | 값 | 검증 시점 |
|----|------|-----|----------|
| A1 | JD 수 (job-hub) | 10K | Pre-Phase 0 |
| A2 | DB 이력서 수 (resume-hub) | 500K | Pre-Phase 0 |
| A2' | 파일 이력서 수 (DB 미존재) | ~100K | Phase 2 |
| A4 | 이력서당 Career 수 | 평균 3 | Phase 0 DB 프로파일 |
| A9 | 매칭 쌍 수 | 5M (10K × 500 shortlisting) | Phase 3 |

### 데이터 품질

| ID | 가정 | 값 | 검증 시점 |
|----|------|-----|----------|
| A5 | NICE 매칭률 (BRN) | 80-90% | Phase 0 |
| A17 | 이력서 중복률 | 5-10% | Phase 0 |
| A19 | Career.BRN null 비율 | 40% | Pre-Phase 0 |
| A20 | Career.workDetails null 비율 | 20% | Pre-Phase 0 |
| A21 | overview.descriptions 평균 길이 | 1,000 chars | Pre-Phase 0 |
| A22 | Skill.code null + 비표준 | 10% null + 30-50% 비표준 | Pre-Phase 0 |
| A23 | resume-hub 적재 완료 | 100% | Pre-Phase 0 |
| A24 | Read replica 접근 | 가능 | Pre-Phase 0 |

### 모델 성능

| ID | 가정 | 값 | 검증 시점 |
|----|------|-----|----------|
| A6 | LLM 토큰 (CompanyContext / CandidateContext) | 2,200 / 1,800 | Phase 0 PoC |
| A8 | Haiku ≈ 85% Sonnet 품질 | 85% | Phase 0 PoC |
| A16 | 임베딩 한국어 분별력 | "excellent" | Phase 0 |
| **A27** | text-embedding-005 ≥ embedding-002 (한국어) | ≥동등 | **Phase 0 (v10 신규)** |

### 비즈니스/법률

| ID | 가정 | 값 | 검증 시점 |
|----|------|-----|----------|
| A10 | PII 외부 전송 가능 (마스킹) | 가능 | Pre-Phase 0 |
| A14 | Neo4j Professional $100/월 @ 800K 노드 | $100-200 | Phase 2 |
| A15 | Batch API 24시간 응답 | 24시간 | Phase 0 |
| A18 | CompanyTalentSignal 제외 | 제외 (v19 A3) | 확정 |

### 비교/임계값 (v9 유지)

| ID | 가정 | 값 | 검증 시점 |
|----|------|-----|----------|
| A25 | 임계값 (skill/major/role) | 0.85 / 0.75 / 0.80 | Phase 0 |
| A26 | canonical 커버리지 | skill ~2K, major ~500, role ~300 | Phase 0 |

### GCP 인프라 (v10 신규)

| ID | 가정 | 값 | 검증 시점 |
|----|------|-----|----------|
| **A28** | Cloud Run Jobs 50 병렬 안정 | 안정 | Phase 1 |
| **A29** | Neo4j AuraDB Free 200K 노드 충분 (Phase 1) | 충분 | Phase 1 |
| **A30** | Vertex AI us-central1 → asia-northeast3 레이턴시 | <2초 | Phase 0 |
| **A31** | Cloud Workflows 비용 무시 가능 | ~$1/월 | Phase 4 |
| **A32** | Secret Manager 6개월 로테이션 | 가능 | Phase 4 |

---

## 2. 리스크 분석

### Critical

#### R1: PII 데이터 처리 (v9 유지)

| 항목 | 상세 |
|------|------|
| 영향 | 전체 아키텍처 결정 |
| 전략 | "마스킹 후 API 전송" 선호 (최저 비용) |
| 대안 | On-premise EXAONE (1.6× 비용), Azure Private Endpoint (중간) |
| 완화 | Phase 0 법률 PII-마스킹 전략 확정, 미확정 시 마스킹 API 기본값 |

#### R2: LLM 추출 품질 (v9 유지)

| 항목 | 상세 |
|------|------|
| 영향 | 시스템 실현 가능성 |
| 완화 | DB 구조화 필드 사전 주입으로 정확도 향상 |
| 검증 | Phase 0에서 scope_type/outcomes/signals ≥50-60% 확인 |
| 폴백 | 택소노미 축소 옵션 |

#### ~~R2.3: 파싱 품질+LLM 상관~~ → v8에서 제거됨 (DB 기반)

### High

#### R2.4: NICE 매칭 (v9: High→Medium 예상)

BRN 직접 100% (60%) + fuzzy 폴백 (~60% of 40%) = **84% 예상**
완화: 미매칭 시 null 허용, v1.1 투자 DB로 스타트업 보강

#### R2.18: DB 접근/가용성 (v9 유지)

Pre-Phase 0 차단 의존성. 불가 시 v7 파일 파싱 폴백 (+5-6주)

#### R2.19: 데이터 적재 미완료 (v9 유지)

resume-hub <80% 완료 시 파일 폴백 비중 확대

#### R3: GCP 인프라 리스크 (v10 신규)

| ID | 리스크 | 영향 | 완화 |
|----|--------|------|------|
| **R3.1** | Cloud Run Job 50 병렬 처리 불안정 | 배치 처리 지연 | 병렬 수 축소 (20→10), 재시도 전략 |
| **R3.2** | Neo4j AuraDB 커넥션 풀 한계 | 그래프 적재 병목 | ≤5 태스크 제한 (이미 설계 반영) |
| **R3.3** | Vertex AI 리전 레이턴시 | 임베딩 처리 지연 | 배치 처리로 레이턴시 무관, 캐싱 |
| **R3.4** | Cloud Workflows 복잡도 | 오케스트레이션 디버깅 어려움 | Makefile 우선 (Phase 1-3), Workflows는 Phase 4 |
| **R3.5** | 서비스 계정 권한 과소 | 파이프라인 실행 실패 | Phase 0에서 IAM 전체 테스트 |

#### R4: GraphRAG vs Vector 실험 리스크 (v10 신규)

| ID | 리스크 | 영향 | 완화 |
|----|--------|------|------|
| **R4.1** | GraphRAG 우위 미입증 (Case 3-4) | v2 전략 재검토 | v19 Decision Tree에 따라 Vector+LLM Reranking 또는 하이브리드 전환 |
| **R4.2** | 평가자 간 일치도 낮음 | 실험 결과 신뢰도 저하 | 사전 평가 기준 교육, Inter-rater agreement 모니터링 |
| **R4.3** | 50 JD 샘플 부족 | 통계적 검정력 부족 | Power analysis 기반 샘플 확장 |

### Medium

#### R2.10: Entity Resolution / 3-Tier 전략 (v9+v10)

| 리스크 | 완화 |
|--------|------|
| Tier 2/3 임계값 캘리브레이션 | Phase 0 PoC 50건 Gold Set |
| synonym dict 불완전 | needs_review 플래그, 운영 중 누적 보강 |
| code-hub 커버리지 부족 | 모니터링 (skill code match ≥70%, embedding coverage ≥85%) |
| 한국어 특수 처리 | "삼성"="SAMSUNG", "토스"≠"비바리퍼블리카" 등 사전 구축 |

#### R5: 파일 파싱 리스크 (v10 신규)

| ID | 리스크 | 영향 | 완화 |
|----|--------|------|------|
| **R5.1** | HWP 파서 품질 | 10-20% 파싱 실패 | Gemini Multimodal 폴백 |
| **R5.2** | 파일↔DB 교차 중복 오매칭 | 중복 노드 생성 | 이름+전화번호 해시 + 수동 검증 |
| **R5.3** | 파일 이력서 LLM 비용 증가 | DB 대비 ~27% 토큰 증가 | DB-first 원칙 유지, 파일은 보조 |

#### R6: 크롤링 리스크 (v19 06_crawling_strategy.md 기반)

| ID | 리스크 | 영향 | 완화 |
|----|--------|------|------|
| **R6.1** | 크롤링 법적 불가 | Phase 4 범위 축소 | DB-only MVP 가능 (크롤링 없이) |
| **R6.2** | 홈페이지 구조 다양성 | 추출 품질 저하 | P1-P6 페이지 유형별 프롬프트 |
| **R6.3** | 뉴스 중복/노이즈 | CompanyContext 오염 | 2단계 클러스터링 중복 제거 + PR 신뢰도 감쇄 |
| **R6.4** | Cloudflare/봇 차단 | 크롤링 실패 | Runbook 3 대응, User-Agent 변경 |

### Low

#### R2.15: 이력서 중복 (v9: Medium→Low)

SiteUserMapping(DB) + SimHash(파일) 이중 전략으로 리스크 최소화

#### R2.22: JSONB 스키마 불일치 (v9 유지)

Phase 0 50건 샘플링 + 방어적 파싱 + whole-text 폴백

---

## 3. v9 → v10 리스크 변화 요약

| 리스크 | v9 등급 | v10 등급 | 변화 이유 |
|--------|---------|---------|----------|
| R1 PII | Critical | **Critical** | 유지 |
| R2 LLM 품질 | Critical | **Critical** | 유지 |
| R2.3 파싱+LLM | ~~Critical~~ | **제거** | DB 기반으로 완전 제거 |
| R2.4 NICE | High | **High** | BRN 84% 예상이나 검증 필요 |
| R2.10 ER/3-Tier | Medium | **Medium** | 유지 |
| R2.15 중복 | Medium | **Low** | 이중 전략 |
| **R3 GCP 인프라** | (없음) | **High** | v10 신규 |
| **R4 실험 리스크** | (없음) | **High** | v10 신규 |
| **R5 파일 파싱** | (없음) | **Medium** | v10 신규 (DB 폴백) |
| **R6 크롤링** | (없음) | **Medium** | v10 신규 |

---

## 4. v9 → v10 핵심 변환

| 항목 | v9 | v10 |
|------|-----|-----|
| 목적 | v11 Context 생성 | **v19 Context 생성 + GraphRAG 매칭** |
| 데이터 소스 | resume-hub/job-hub/code-hub DB | **DB + 파일 폴백 + 크롤링** |
| 인프라 | 미정 | **GCP (Cloud Run + BigQuery + Vertex AI)** |
| 오케스트레이션 | Prefect vs Workflows 미결정 | **Cloud Workflows 확정** |
| 매칭 | 미정의 | **v19 F1-F5 (5대 특성, 확정 가중치)** |
| 평가 | 50건 수동 | **GraphRAG vs Vector 실험 (50 JD × 5 평가자)** |
| 운영 | 간략 | **Runbook 5 + Alarm 10 + 증분 + 핸드오프** |
| 서빙 | 없음 | **FastAPI Agent Serving API (8개 엔드포인트)** |
| 임베딩 | text-multilingual-embedding-002 | **text-embedding-005 (768d)** |
| 비용 | ~$8,899 | **$7,567-10,507** |
| 타임라인 | 14-17주 (MVP) | **27주 (프로덕션)** |
