# VG4 — 팀별 스프린트 상세 (Team Sprints)

---

## 1. GraphRAG 팀 Phase 상세

### G-0: Neo4j 환경 + 스키마 (0.5주, W1 후반)
- DE: Neo4j AuraDB Free + v19 스키마 + Vector Index(768d)
- MLE: UNWIND Batch 적재 코드 골격
- 공동: GCP 환경 분담 (S&F팀과 공동)

### 대기 구간 A (W2~4, ~3주) — S&F 1K 처리 대기
> **선행 작업 (~2주)**:
> - GraphRAG REST API 골격 설계 (FastAPI, 라우트 정의)
> - Cypher 쿼리 5종 초안 + Mock 데이터 테스트
> - PII 필터 미들웨어 설계 + 단위 테스트 (N2)
> - NEXT_CHAPTER 연결 로직 설계 + 테스트 데이터
> - GCS→PubSub→Cloud Run Job 자동 적재 트리거 구축

### G-1: 그래프 MVP (2주, W5~6)
- W5: PubSub 트리거로 1,000건 JSON 자동 수신 → 노드/엣지 적재
  - Person, Chapter, Skill, Role, Organization, Industry (v19)
  - NEXT_CHAPTER 연결 (chapters[] 순서 기반)
  - Idempotency + 롤백 테스트
- W6: Cypher 쿼리 5종 + REST API 배포
  - /search/skills, /search/semantic, /search/compound
  - /candidates/{id} (PII 필터링)
  - API Key 인증 + Rate limiting + /health
- 공동: E2E 검증 + 스팟체크 50건

**산출물**: Neo4j MVP (1K), REST API 5종, PII 정의서, PubSub 적재 파이프라인

### 대기 구간 B (W7~9, ~1.5주) — S&F Batch 시작 대기
> **선행 작업 (~1주)**: Neo4j Professional 사이징 외삽 스크립트, Bulk Loading 오케스트레이션 코드

### G-2: 대규모 적재 + 사이징 (2주, W10~11)
- W10: Neo4j Free→Professional 전환 (A3), 메모리 측정 → 600K 외삽 (N8)
- W10~11: PubSub 트리거로 S&F 완료분 순차 적재 (batch_size=100)
- W11: 쿼리 성능 벤치마크 (Cypher 5종 × 480K+, **p95 < 2초**)

**산출물**: Neo4j Professional (사이징 확정), 480K+ Graph, 벤치마크 결과

### 버퍼 0.5주 (W11 후반): Go/No-Go 판정

### G-3: 매칭 알고리즘 + 기업 그래프 (4주+테스트, W17~22)
- W17: 매칭 설계 (MappingFeatures F1~F5, MAPPED_TO 규모 추정 N3)
- W17 후반: Vacancy 노드 적재 (PubSub로 S&F JD JSON 수신)
  - v19: HAS_VACANCY, REQUIRES_ROLE, REQUIRES_SKILL, NEEDS_SIGNAL
- W18: Organization ER + 한국어 특화 (계열사 사전: 삼성/현대/SK/LG/롯데 초기)
  - S&F NICE 데이터 + BigQuery 조인
- W19~20: 5-피처 스코어링 구현 + MAPPED_TO 생성 (임계값 ≥ 0.4)
  - GraphRAG API 확장: /match/jd-to-candidates, /match/candidate-to-jds
- W20: 가중치 수동 튜닝 (3~4 조합 Top-10 비교)
- W21: 통합 테스트 + 매칭 50건 수동 검증
- W22: 버퍼 Go/No-Go

**산출물**: 매칭 알고리즘, 5-피처 스코어링, Organization ER, 가중치 튜닝

### G-4: 증분 + 운영 (3주, W24~26)
- W24: 증분 처리 (변경 감지, DETACH DELETE 2단계, 소프트 삭제 마이그레이션)
- W25: Cloud Workflows DAG + 보강 데이터 PubSub 적재
- W25~26: Gold Label 100건 + Runbook 5종 + Alarm 10종 + Cold Start 대응
- W26: 인수인계 문서

**W27**: Final Go/No-Go → 프로덕션 전환

---

## 2. S&F 팀 주차별 타임라인

### 담당 범위 (6범주)

| 범주 | 상세 |
|------|------|
| **데이터 수집** | DB export, Playwright 크롤링, 홈페이지/뉴스 |
| **전처리** | PII 마스킹(re.sub, 8종), CMEK, Career 블록 분리 |
| **파일 파싱** | PDF/DOCX/HWP, Hybrid 섹션 분리 |
| **LLM 추출** | Candidate(적응형), Company(DB+NICE+LLM), Provider 추상화 |
| **임베딩+벡터** | Vertex AI 768d, Vector DB 관리 |
| **품질** | schema ≥95%, PII ≤0.01%, 384건 샘플링 |

### 주차별 실행

```
W1:     [환경+PoC] → 산출물 ① (수동, Go/No-Go 회의)
W2-3:   [전처리: PII+CMEK+Career 분리]
W4-5:   [LLM 추출 1,000건] → 산출물 ② (PubSub)
W7:     [코드 리팩토링 + Provider 추상화]
W8-9:   [파서 구축: PDF/DOCX/HWP + Hybrid]
W10-15: [Batch 600K 처리] → 산출물 ③ (PubSub, 순차)
W16:    [버퍼 + 품질 리포트]
W17-18: [JD 파싱 + CompanyContext 추출] → 산출물 ④ (PubSub)
W19-22: [잔여 배치 + 품질 관리]
W23:    [버퍼]
W24-25: [홈페이지/뉴스 크롤링] → 산출물 ⑤ (PubSub)
W26-27: [품질 최종 + 인수인계]
```
