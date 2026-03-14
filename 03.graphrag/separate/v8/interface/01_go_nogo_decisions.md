# S&F <-> GraphRAG 공동

---

## 1. Phase 간 Go/No-Go 기준

### [v5] W0 선행 결정 (Phase 0 시작 전)

| 기준 | 통과 조건 | 미달 시 | 주체 |
| --- | --- | --- | --- |
| **[v4] PII 처리 책임** | 데이터 플랫폼과 경계 확정 | Phase 1 지연 | 공동 |

### Phase 0 -> Phase 1 (W1 D5 판정)

| 기준 | 통과 조건 | 미달 시 | 주체 |
| --- | --- | --- | --- |
| LLM 추출 품질 | scope_type 정확도 > 60% (20건) | 프롬프트 +3일 | S&F |
| 적응형 호출 품질 | 1-pass ≈ N+1 pass (±10%) | Career 분기점 조정 | S&F |
| DB 데이터 품질 | 비어있는 비율 < 20% | structured_fields 활용 | S&F |
| 크롤링 가능성 | 법무 미결이어도 **DB-only Go** | 크롤링 후순위 | 공동 |
| Embedding 분별력 | similar > 0.7, dissimilar < 0.4 | 기본값 유지 | S&F |
| PoC 비용 외삽 (A2) | 600K 외삽 시 $1,690 ±50% | 비용 재산정 | S&F |
| Neo4j 스키마 | v25 적용 완료 | - | GraphRAG |
| **[v4] Neo4j 티어** | Professional 27M 노드 수용 확인 | Enterprise 전환 검토 | GraphRAG |

### Phase 2 -> Phase 3

| 기준 | 통과 조건 | 미달 시 | 주체 |
| --- | --- | --- | --- |
| 처리량 | 80%+ (480K+) | Phase 3 백그라운드 | S&F |
| DB 500K 완료율 (R6) | 90%+ | 파일 하향 | S&F |
| 파싱 성공률 | 95%+ | 파서 개선 | S&F |
| Neo4j 사이징 (N8) | 안정 동작 | 업그레이드 | GraphRAG |
| Cypher 벤치마크 | p95 < 2초 | 인덱스 추가 | GraphRAG |
| 잔여 배치 (N9) | 자동화 확인 | Batch 할당 조정 | S&F |

### Phase 3 -> Phase 4

| 기준 | 통과 조건 | 미달 시 | 주체 |
| --- | --- | --- | --- |
| MAPPED_TO 규모 (N3) | Neo4j 수용 가능 | 임계값 상향 | GraphRAG |
| 가중치 튜닝 (N7) | 50건 재조정 완료 | 초기값 + Phase 5 | GraphRAG |
| 매칭 품질 | Top-10 적합도 70%+ | 재조정 | GraphRAG |
| 잔여 배치 | 100% 완료 확인 | 추가 처리 | S&F |

---

## 2. 의사결정 포인트 (17건)

| 시점 | 의사결정 | 주체 | 입력 데이터 | 실패 시 |
| --- | --- | --- | --- | --- |
| W0 즉시 | Batch API quota 확인 | **S&F** | Anthropic 콘솔 | 동시 3 batch |
| W0 즉시 | Gemini Flash Batch 검증 | **S&F** | API 테스트 | 한도 시 병행 |
| W1 D3 | LLM 모델 선택 | **S&F** | Haiku vs Sonnet | Haiku Batch |
| W1 D3 | Embedding 모델 확정 | **S&F** | 분별력 테스트 | 005 기본값 |
| W1 D5 | Phase 0 Go/No-Go | **공동** | PoC + 크롤링 + Neo4j | 스코프 축소 |
| W6 | Phase 1 Go/No-Go | **공동** | 1K E2E + API | Phase 1 연장 |
| W10 | Neo4j 사이징 확정 (N8) | **GraphRAG** | 1K 메모리 외삽 | 크기 조정 |
| W12 | DB 500K 완료율 (R6) | **S&F** | Batch 진행률 | 파일 하향 |
| W15 | Phase 2 Go/No-Go | **공동** | 80%+ + 사이징 | 연장 |
| W17 | MAPPED_TO 규모 테스트 (N3) | **GraphRAG** | JD 100 × Person 1K | 임계값 조정 |
| W17 | job-hub API 스펙 확정 (A1) | **S&F** | API 스펙 문서 | JD 파서 1주 확장 |
| W22 | 매칭 가중치 재조정 (N7) | **GraphRAG** | 50건 검증 | 가중치 업데이트 |
| W22 | **[v5] Gold Set 50->100 확장** | **공동** | Phase 3 완료 시 | 50건 유지 |
| W26 | Gold Label 100->200 (N6) | **공동** | 100건 품질 | 100건으로 종료 |
| **W0 즉시** | **[v4] PII 처리 책임 경계 확정** | **공동** | 데이터 플랫폼 팀 협의 | Phase 1 PII 모듈 구현 지연 |
| **W1** | **[v4] Neo4j 티어 확정 (사이징 문의)** | **GraphRAG** | Neo4j 영업팀 사이징 결과 | Enterprise 전환 비용 2~5배 증가 |
| **W4** | **[v4] 크롤링 법률 검토 완료** | **공동** | 법무팀 검토 결과 | Phase 4를 DB 보강(NICE 추가 조회, 투자DB API)으로 대체 |
| W27 | Phase 4 Go/No-Go | **공동** | 전체 품질 | 운영 인력 확정 |