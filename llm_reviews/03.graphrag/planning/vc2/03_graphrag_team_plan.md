# GraphRAG 팀 독립 실행 계획 (v2)

> **v1 대비 변경**: ★ I4 순수 작업/대기 구간 분리 표기, ★ I1 PubSub 자동 적재 트리거 반영
> **인력**: DE 1명 + MLE 1명, v5 동일

---

## 1. GraphRAG 팀 타임라인

> ★ v2 I4: **캘린더 ~12.5주 = 순수 작업 ~8주 + 대기(선행 작업 포함) ~4.5주**

```
Phase G-0: Neo4j 환경 + 스키마 (0.5주, W1 후반)
  ├─ DE: Neo4j AuraDB Free 생성 + v19 스키마 + Vector Index(768d)
  ├─ MLE: 그래프 적재 코드 골격 (UNWIND Batch 템플릿)
  └─ 공동: GCP 환경 분담 (S&F팀과 공동)
  ──── 순수 작업: 0.5주 ────

─ 대기 구간 A (W2~4, 약 3주) ─ S&F CandidateContext 1,000건 산출 대기
  ★ 선행 작업 (대기 중 수행, ~2주 분량):
    ├─ GraphRAG REST API 골격 설계 (FastAPI 프로젝트, 라우트 정의)
    ├─ Cypher 쿼리 5종 초안 작성 + Mock 데이터 기반 테스트
    ├─ PII 필터 미들웨어 설계 + 단위 테스트 (N2)
    ├─ NEXT_CHAPTER 연결 로직 설계 + 테스트 데이터 작성
    └─ ★ v2 I1: GCS→PubSub→Cloud Run Job 자동 적재 트리거 구축
  ──── 대기(선행 작업): ~3주 중 ~2주 활용 ────

Phase G-1: 그래프 MVP 적재 + API (2주, W5~6)
  ├─ W5: GCS PubSub 트리거로 1,000건 JSON 자동 수신 → 노드/엣지 적재
  │   ├─ Person, Chapter, Skill, Role, Organization, Industry (v19 관계명)
  │   ├─ NEXT_CHAPTER 연결 (chapters[] 배열 순서 기반)
  │   └─ Idempotency + 롤백 테스트
  ├─ W6: Cypher 쿼리 5종 + GraphRAG REST API 배포
  │   ├─ /search/skills, /search/semantic, /search/compound
  │   ├─ /candidates/{id} (PII 필터링)
  │   ├─ /health (Cloud Scheduler 12h)
  │   └─ API Key 인증 + Rate limiting
  └─ 공동: E2E 검증 + 스팟체크 50건
  ──── 순수 작업: 2주 ────

  ★ Phase G-1 산출물:
    □ Neo4j Graph MVP (1,000건, v19 관계명)
    □ GraphRAG REST API (검색 5종 + 헬스체크)
    □ PII 필드 정의서 (N2)
    □ Cloud Scheduler health check (N1)
    □ ★ v2: GCS→PubSub→적재 자동 파이프라인

─ 대기 구간 B (W7~9, 약 1.5주) ─ S&F Batch 처리 시작 대기
  ★ 선행 작업 (~1주 분량):
    ├─ Neo4j Professional 전환 사전 준비 (사이징 외삽 스크립트)
    └─ Bulk Loading 오케스트레이션 코드 작성 (batch_size 최적화)
  ──── 대기(선행 작업): ~1.5주 중 ~1주 활용 ────

Phase G-2: 대규모 적재 + 사이징 (2주, W10~11)
  ├─ W10: Neo4j Free→Professional 전환 (v5 A3: Cypher 복사 ~30분)
  │   ├─ 1,000건 메모리 측정 → 600K 외삽 (N8)
  │   ├─ 인스턴스 크기 결정 (8GB / 16GB / 32GB)
  │   └─ Vector Index 재생성
  ├─ W10~11: PubSub 트리거로 S&F 완료분 순차 적재
  │   ├─ UNWIND Batch (batch_size=100, 버전 태그)
  │   ├─ NEXT_CHAPTER 연결 (Person별 chapters[] 순서)
  │   └─ 적재 진행률 모니터링
  └─ W11: 쿼리 성능 벤치마크 (Cypher 5종 × 480K+, p95 < 2초)
  ──── 순수 작업: 2주 ────

  ★ Phase G-2 산출물:
    □ Neo4j Professional 인스턴스 (사이징 확정)
    □ 480K+ Person Graph 적재 완료
    □ 쿼리 벤치마크 결과 (p95 확인)

버퍼 0.5주 (W11 후반): Go/No-Go + 기술 부채 정리

Phase G-3: 매칭 알고리즘 + 기업 그래프 (4주, W17~20)
  ├─ W17: 매칭 알고리즘 설계 (2일)
  │   ├─ MappingFeatures 5-피처 정의 (F1~F5, v12 §6)
  │   ├─ MAPPED_TO 규모 추정: JD 100 × Person 1K 테스트 (N3)
  │   └─ Neo4j 사이징 영향 분석 (500K~5M 관계)
  ├─ W17 후반: Vacancy 노드 + 관계 적재 (PubSub 트리거로 S&F JD JSON 수신)
  │   └─ v19: HAS_VACANCY, REQUIRES_ROLE, REQUIRES_SKILL, NEEDS_SIGNAL
  ├─ W18: Organization ER + 한국어 특화 (1.5주)
  │   ├─ 계열사 사전 (삼성/현대/SK/LG/롯데 초기)
  │   └─ S&F NICE 데이터 + BigQuery 조인
  ├─ W19~20: MappingFeatures 스코어링 구현 (2주)
  │   ├─ F1~F5 구현 + MAPPED_TO 관계 생성 (임계값 ≥ 0.4)
  │   └─ GraphRAG API 확장: /match/jd-to-candidates, /match/candidate-to-jds
  └─ W20 (1일): 가중치 수동 튜닝 (3~4개 조합 Top-10 전문가 비교)
  ──── 순수 작업: 4주 ────

  통합 테스트 1주 (W21) + 버퍼 0.5주 (W22) Go/No-Go

Phase G-4: 증분 + 운영 인프라 (3주, W24~26)
  ├─ W24: 증분 처리 (변경 감지, DETACH DELETE 2단계, 소프트 삭제 마이그레이션)
  ├─ W25: Cloud Workflows DAG + S&F 보강 데이터 PubSub 수신 적재
  ├─ W25~26: Gold Label 100건 + Runbook 5종 + Alarm 10종 + Cold Start 대응
  └─ W26: 인수인계 문서
  ──── 순수 작업: 3주 ────

W27: Final Go/No-Go → 프로덕션 운영 전환
```

### 리소스 활용율 요약 (★ v2 I4)

| 구간 | 기간 | 유형 | 순수 작업량 |
|------|------|------|-----------|
| G-0 | 0.5주 | 작업 | 0.5주 |
| 대기 A | 3주 | 대기(선행) | 선행 2주 + 유휴 1주 |
| G-1 | 2주 | 작업 | 2주 |
| 대기 B | 1.5주 | 대기(선행) | 선행 1주 + 유휴 0.5주 |
| G-2 | 2주 | 작업 | 2주 |
| 버퍼 | 0.5주 | 판정 | — |
| G-3+테스트 | 5.5주 | 작업 | 5.5주 (W17~22, 테스트+버퍼 포함) |
| G-4 | 3주 | 작업 | 3주 |
| **합계** | **18주(W1~27 중 가동)** | | **순수 작업 ~13주, 유휴 ~1.5주** |

> **리소스 활용율: ~87%** (유휴 1.5주 / 전체 가동 18주 × 100%).
> 대기 구간 선행 작업으로 유휴를 최소화.

---

## 2. Go/No-Go 기준 — v1 동일

### G-1 → G-2: 적재 1K + API 5종 +관계 무결성
### G-2 → G-3: 적재 480K+ + 사이징 + p95 < 2s
### G-3 → G-4: MAPPED_TO 규모 + Top-10 70%+ + 가중치 튜닝

---

## 3. GraphRAG 팀 비용 — v1 동일

| Phase | Neo4j | Cloud Run/기타 | Gold Label | **합계** |
|-------|-------|-------------|-----------|--------|
| G-0~G-1 | $0 (Free) | ~$15 | — | **~$15** |
| G-2 | $55~110 | ~$20 | — | **~$75~130** |
| G-3 | $225~450 | ~$25 | — | **~$250~475** |
| G-4 | $150~300 | ~$25 | $2,920~5,840 | **~$3,095~6,165** |
| **합계** | **$430~860** | **~$85** | **$2,920~5,840** | **~$3,435~6,785** |
