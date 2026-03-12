# GraphRAG 팀 독립 실행 계획

> **기준**: v5 실행계획에서 GraphRAG 관련 태스크만 추출하여 재구성
> **전제**: S&F 팀이 전처리·LLM 추출·임베딩을 전담하고, 정제된 JSON을 Data Contract에 맞춰 전달
> **인력**: DE 1명 + MLE 1명 (v5 동일)

---

## 1. GraphRAG 팀 타임라인 (~12.5주)

```
Phase G-0: Neo4j 환경 + 스키마 (0.5주, W1 후반)
  ├─ DE: Neo4j AuraDB Free 생성 + v19 스키마 + Vector Index(768d)
  ├─ MLE: 그래프 적재 코드 골격 작성 (UNWIND Batch 템플릿)
  └─ 공동: GCP 환경 분담 (S&F팀과 공동)

─ 대기: S&F팀 Phase 1 CandidateContext 1,000건 산출 대기 (W2~5) ─
  ★ 대기 중 선행 작업:
    ├─ GraphRAG API 골격 설계 (FastAPI + Cypher 쿼리 5종 초안)
    ├─ PII 필터 미들웨어 설계 (N2)
    └─ NEXT_CHAPTER 연결 로직 설계 + 테스트 데이터 작성

Phase G-1: 그래프 MVP 적재 + API (2주, W5~6)
  ├─ W5: S&F 산출물(1,000건 JSON) 수신 → 노드/엣지 적재
  │   ├─ Person, Chapter, Skill, Role, Organization, Industry (v19 관계명)
  │   ├─ NEXT_CHAPTER 연결 (chapters[] 배열 순서 기반)
  │   └─ Idempotency + 롤백 테스트
  ├─ W6: Cypher 쿼리 5종 + GraphRAG REST API 배포
  │   ├─ /search/skills, /search/semantic, /search/compound
  │   ├─ /candidates/{id} (PII 필터링)
  │   ├─ /health (Cloud Scheduler 12h)
  │   └─ API Key 인증 + Rate limiting
  └─ 공동: E2E 검증 + 스팟체크 50건 + 에이전트 팀 연동 안내

  ★ Phase G-1 산출물:
    □ Neo4j Graph MVP (1,000건, v19 관계명)
    □ GraphRAG REST API (검색 5종 + 헬스체크)
    □ PII 필드 정의서 (N2)
    □ Cloud Scheduler health check (N1)

─ 대기: S&F팀 Phase 2 Batch 처리 결과물 대기 (W7~9) ─
  ★ 대기 중 선행 작업:
    ├─ Neo4j Professional 전환 준비 (사이징 외삽 스크립트)
    └─ Bulk Loading 오케스트레이션 코드 작성

Phase G-2: 대규모 적재 + 사이징 (2주, W10~11)
  ├─ W10: Neo4j Free→Professional 전환 (v5 A3: Cypher 복사 ~30분)
  │   ├─ 1,000건 메모리 측정 → 600K 외삽 (N8)
  │   ├─ 인스턴스 크기 결정 (8GB / 16GB / 32GB)
  │   └─ Vector Index 재생성
  ├─ W10-11: S&F 완료분 순차 적재 (Bulk Loading)
  │   ├─ UNWIND Batch (batch_size=100, 버전 태그)
  │   ├─ NEXT_CHAPTER 연결 (Person별 chapters[] 순서)
  │   └─ 적재 진행률 모니터링
  └─ W11: 쿼리 성능 벤치마크 (Cypher 5종 × 480K+, p95 < 2초)

  ★ Phase G-2 산출물:
    □ Neo4j Professional 인스턴스 (사이징 확정)
    □ 480K+ Person Graph 적재 완료
    □ 쿼리 벤치마크 결과

버퍼 0.5주 (W11 후반): Go/No-Go + 기술 부채 정리

Phase G-3: 매칭 알고리즘 + 기업 그래프 (4주, W17~20)
  ├─ W17: 매칭 알고리즘 설계 (2일)
  │   ├─ MappingFeatures 5-피처 정의 (F1~F5, v12 §6)
  │   ├─ MAPPED_TO 규모 추정: JD 100 × Person 1K 테스트 (N3)
  │   └─ Neo4j 사이징 영향 분석 (500K~5M 관계)
  ├─ W17 후반: Vacancy 노드 + 관계 적재 (S&F의 JD JSON 수신)
  │   └─ v19: HAS_VACANCY, REQUIRES_ROLE, REQUIRES_SKILL, NEEDS_SIGNAL
  ├─ W18: Organization ER + 한국어 특화 (1.5주)
  │   ├─ 계열사 사전 (삼성/현대/SK/LG/롯데 초기)
  │   └─ S&F의 NICE 데이터 + BigQuery 조인
  ├─ W19~20: MappingFeatures 스코어링 구현 (2주)
  │   ├─ F1 stage_match (v19 A4: 4×4 매트릭스)
  │   ├─ F2 vacancy_fit (scope_type + signals)
  │   ├─ F3 domain_fit (Skill Jaccard + Industry)
  │   ├─ F4 culture_fit (v1 INACTIVE, 기본값 0.5)
  │   ├─ F5 role_fit (seniority + role_evolution)
  │   ├─ MAPPED_TO 관계 생성 (임계값 ≥ 0.4)
  │   └─ GraphRAG API 확장: /match/jd-to-candidates, /match/candidate-to-jds, /companies/{org_id}

  ★ 가중치 튜닝 (W20, 1일):
    ├─ 50건 수동 검증 결과 분석
    ├─ 3~4개 후보 가중치 조합 Top-10 비교
    └─ 전문가 최종 선택

  ★ Phase G-3 산출물:
    □ 매칭 알고리즘 설계 문서
    □ MAPPED_TO 규모 추정 결과 (N3)
    □ 5-피처 스코어링 구현
    □ 가중치 수동 튜닝 완료 (O3)
    □ Organization ER (주요 그룹 초기)
    □ GraphRAG API 확장 (매칭 + 기업)

통합 테스트 1주 (W21): Regression + 매칭 50건 수동 검증

버퍼 0.5주 (W22): Phase 3 Go/No-Go

Phase G-4: 증분 + 운영 인프라 (3주, W24~26)
  ├─ W24: 증분 처리 구현
  │   ├─ 변경 감지 (created/updated/deleted_at)
  │   ├─ 수정 유형별 분기 (구조화 vs 텍스트)
  │   ├─ DETACH DELETE 2단계 통합 (R8)
  │   └─ 소프트 삭제 + Cypher 마이그레이션 (R7)
  ├─ W25: Cloud Workflows DAG + 자동화
  │   ├─ 일일 증분 파이프라인
  │   ├─ is_active 인덱스 + API 미들웨어
  │   └─ S&F 크롤링 보강 데이터 → CompanyContext 적재
  ├─ W25-26: 품질 + 운영
  │   ├─ Gold Label 100건 (N6, 3일)
  │   ├─ Runbook 5종 + Alarm 10종
  │   ├─ Cloud Run Cold Start 대응 (v5 A4)
  │   └─ Slack Webhook 연동
  └─ W26: 인수인계 문서

  ★ Phase G-4 산출물:
    □ 증분 처리 파이프라인 (v12 §1 전면 반영)
    □ Cloud Workflows 전체 DAG
    □ Gold Label 품질 보고서
    □ Runbook + Alarm + 인수인계

W27: Final Go/No-Go → 프로덕션 운영 전환
```

---

## 2. GraphRAG 팀 Go/No-Go 기준

### Phase G-1 → G-2

| 기준 | 통과 조건 |
|------|-----------|
| 그래프 적재 | 1,000건 Person·Chapter·Skill 정상 적재 |
| API 동작 | Cypher 5종 + REST API 정상 응답 |
| 관계 무결성 | NEXT_CHAPTER 연결 오류 0건 |

### Phase G-2 → G-3

| 기준 | 통과 조건 |
|------|-----------|
| 적재량 | 480K+ Person Graph (S&F 완료분) |
| Neo4j 사이징 | 인스턴스 안정 동작 (N8) |
| 쿼리 성능 | Cypher 5종 p95 < 2초 |

### Phase G-3 → G-4

| 기준 | 통과 조건 |
|------|-----------|
| MAPPED_TO | 규모 추정 범위 내 (N3) |
| 매칭 품질 | Top-10 적합도 70%+ |
| 가중치 튜닝 | 50건 검증 기반 재조정 완료 (N7) |

---

## 3. GraphRAG 팀 비용

| Phase | Neo4j | Cloud Run/기타 | Gold Label | **합계** |
|-------|-------|-------------|-----------|--------|
| G-0~G-1 (W1~6) | $0 (Free) | ~$15 | — | **~$15** |
| G-2 (W10~11) | $55~110 | ~$20 | — | **~$75~130** |
| G-3 (W17~21) | $225~450 | ~$25 | — | **~$250~475** |
| G-4 (W24~27) | $150~300 | ~$25 | $2,920~5,840 | **~$3,095~6,165** |
| **합계** | **$430~860** | **~$85** | **$2,920~5,840** | **~$3,435~6,785** |

> LLM 비용($1,807)과 Embedding 비용($52)은 전액 S&F 팀 소관.
