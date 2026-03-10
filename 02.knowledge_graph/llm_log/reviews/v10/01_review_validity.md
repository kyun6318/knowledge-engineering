# v10 타당성 리뷰

> 기술 선택, 아키텍처 판단, 논리적 일관성 평가

---

## 1. 타당한 설계 (긍정 평가)

### 1.1 DB-first + 파일 폴백 전략 — 적절

v9의 DB-only에서 DB-first + 파일 폴백으로 확장한 것은 현실적이다.

- DB 이력서 500K(80%)에 대해 LLM 의존도를 최소화
- 파일 이력서 100K(20%)만 파싱 + LLM 풀 추출
- SiteUserMapping(DB) + SimHash(파일)로 중복 제거 이원화

**다만**: DB에 없는 이력서가 정확히 20%인지는 Pre-Phase 0에서 검증 필요. 이 비율이 40%를 넘으면 파일 파싱 비용이 LLM 비용의 주요 비중이 된다.

### 1.2 3-Tier 비교 전략 — 적절

Tier 1(CI Lookup) → Tier 2(정규화+임베딩) → Tier 3(임베딩 only) 계단식 설계는 비용-정확도 트레이드오프를 잘 반영한다.

- code-hub의 canonical 데이터를 활용하는 Tier 1이 비용 $0
- Tier 2에서 synonym 사전 + 임베딩 하이브리드
- Tier 3은 정규화 불가능한 필드(전공, 직무명)에만 적용

**검증 포인트**: code-hub synonyms 필드 커버리지 50% 미만 시 수동 구축 계획이 Phase 0에 포함되어 있어 좋음.

### 1.3 LLM-for-reasoning 원칙 — 적절

구조화 필드는 DB/코드 직접 매핑, LLM은 추론 필요 필드(scope_type, outcomes, signals, operating_model)에만 사용. 44%/40% 토큰 절감 추정이 합리적.

### 1.4 UNWIND 배치 적재 — 적절

v9의 단건 MERGE에서 UNWIND 배치로 전환. Neo4j 성능 10배+ 향상 기대. loaded_batch_id 태그로 롤백 가능.

### 1.5 Cloud Run Jobs + Cloud Workflows 선택 — 적절

- Cloud Run Jobs: 배치 처리에 적합 (서버리스, 비용 효율)
- Cloud Workflows: 오케스트레이션에 적합 (DAG 정의, 단순)
- Makefile → Cloud Workflows 점진적 전환 (Phase 1-3 수동 → Phase 4 자동)

### 1.6 MappingFeatures 5대 특성 가중치 — 적절

v19에서 확정된 가중치(vacancy 30%, stage 25%, domain 20%, role 15%, culture 10%)를 그대로 반영. INACTIVE 상태인 culture_fit(10%)도 명시.

### 1.7 서비스 계정 3개 분리 — 적절

최소 권한 원칙. 특히 kg-loading만 Neo4j 접근 가능하게 한 것은 보안상 올바른 설계.

---

## 2. 타당성에 의문이 있는 설계

### 2.1 text-embedding-005 단일 표준화 — 조건부 타당

**우려**: Phase 0에서 한국어 분별력 검증을 전제로 하지만, 폴백 모델(Cohere embed-multilingual-v3.0, text-multilingual-embedding-002)로 전환 시 768d가 아닐 수 있다. Cohere v3.0은 1024d.

- Neo4j Vector Index가 768d cosine으로 생성되므로, 차원 변경 시 인덱스 재생성 필요
- Phase 0 1주 안에 검증 실패 → 폴백 → 인덱스 재설계까지 가능한지 타이트

**권고**: Phase 0에서 text-embedding-005와 Cohere v3.0 모두 벤치마크하되, 인덱스는 검증 완료 후 생성.

### 2.2 Neo4j AuraDB Free → Professional 전환 — 조건부 타당

Free 티어 200K 노드 한도에서 Phase 1(1,000건 → ~5K 노드)은 문제없으나, Phase 2(600K 이력서 → ~8M 노드)에서 Professional 필요.

**우려**:
- Professional 800K+ 노드라고 했는데, 8M 노드를 수용하려면 얼마인지 가격 확인 필요
- AuraDB Professional의 실제 노드/엣지 한도가 8M+25M을 감당하는지 Phase 0에서 확인 필수
- asia-northeast1(도쿄)이 최근접이라 했지만, 레이턴시 벤치마크 없음

### 2.3 STAGE_SIMILARITY 4×4 매트릭스 비대칭 — 타당하나 검증 필요

```
EARLY→GROWTH: 0.6 vs GROWTH→EARLY: 0.5 (비대칭)
```

스타트업 출신이 성장기 기업에 적합할 가능성(0.6)이 역방향(0.5)보다 높다는 도메인 가정. 논리적으로 수긍 가능하나, 50건 Gold Set에서 캘리브레이션 필요.

### 2.4 MAPPED_TO 임계값 0.4 — 낮을 수 있음

5대 특성 가중합 0.4는 상당히 낮은 임계값. 매칭 쌍 5M이 과다 생성될 수 있다.

- 600K 후보 × 10K Vacancy에서 Top-500 shortlisting → 5M 쌍
- 임계값 0.4 적용 후 실제 MAPPED_TO 관계 수는 Phase 3에서 확인해야 함
- 너무 많으면 BigQuery 비용/Neo4j 엣지 수 문제

**권고**: 임계값 0.4는 시작점으로 두되, Phase 3 50건 수동 검증에서 Precision@10으로 튜닝.

---

## 3. v9 → v10 변경의 타당성

| 변경 사항 | 타당성 | 비고 |
|----------|--------|------|
| v11 → v19 온톨로지 정합 | 필수 | 8버전 차이 |
| embedding-002 → embedding-005 | 합리적 | 비용 절감 + GraphRAG v2 통일 |
| Prefect → Cloud Workflows | 합리적 | GCP 네이티브, 간단 |
| DB-only → DB-first + 파일 폴백 | 합리적 | 20% 커버리지 확보 |
| SiteUserMapping → + SimHash | 합리적 | 파일 이력서 대응 |
| 14-17주 → 27주 | 범위 확대 | MVP → 프로덕션 |
| Serving API 추가 | 합리적 | 에이전트 연동 필수 |
| Runbook/Alarm 추가 | 합리적 | 운영 체계화 |

---

## 4. 내부 일관성 검증

### 4.1 비용 수치 불일치

- §9.2 LLM 소계: "$1,282" (비Batch) / "$585" (Batch)
- §9.3 인프라 소계: "$1,142-1,742"
- §9.4 시나리오 A 총액: $7,567 (= $585 + $1,142 + $5,840)

**계산 확인**: $585 + $1,142 + $5,840 = $7,567 ✓
**의문**: §9.2의 Embedding $37.5와 §2 02_model_and_infrastructure.md의 §2.2 $25.5가 불일치.
01_extraction_pipeline.md §9.2에서 Embedding 비용이 $37.5로 표기되었으나, 02_model_and_infrastructure.md에서는 $25.5.

### 4.2 GraphRAG Core v2와의 소소한 불일치

| 항목 | v10 (extraction_logic) | GraphRAG Core v2 | 불일치 |
|------|----------------------|-------------------|--------|
| 비용 총액 | $7,567-10,507 | $8,235-8,895 | 범위 다름 |
| Embedding 비용 | $37.5 (01문서) / $25.5 (02문서) | $25.5 | v10 내부 불일치 |
| Phase 1 산출물 | API 5개 엔드포인트 | REST API 4개 엔드포인트 + health | 미세 차이 |
| Graph Schema 관계명 | PERFORMED_ROLE, OCCURRED_AT | HAD_ROLE, AT_COMPANY | **관계명 불일치** |

**관계명 불일치가 가장 심각**: v10은 v19 온톨로지 기준(PERFORMED_ROLE, OCCURRED_AT), GraphRAG Core v2는 자체 명명(HAD_ROLE, AT_COMPANY). 구현 시 혼란 야기.

**권고**: 관계명은 v19 온톨로지를 canonical로, GraphRAG Core v2를 업데이트.
