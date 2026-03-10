# v12 실현 가능성 리뷰

> 리뷰일: 2026-03-11 | 리뷰어: Claude Opus 4.6
> 대상: 02.knowledge_graph/results/extraction_logic/v12/
> 참조: 04.graphrag/results/implement_planning/core/2/

---

## 1. 비용 실현 가능성

### 1.1 v11 → v12 비용 변화 분석

| 항목 | v11 Batch | v12 Batch | 변화 | 원인 |
|------|----------|----------|------|------|
| CompanyContext | $2.2 | $2.0 | -$0.2 | structural_tensions 제거 (S5) |
| CandidateContext DB | $395 | $496 | +$101 | 적응형 호출 (M1) |
| CandidateContext 파일 | $100 | $100 | = | |
| 파일 파싱 | $200 | $200 | = | |
| **파일 섹션 분리** | **$0** | **$30** | **+$30** | **LLM 폴백 30% (S1 신규)** |
| Embedding | $25.5 | $25.5 | = | |
| **합계** | **$523** | **$654** | **+$131 (+25%)** | |

### 1.2 비용 증가의 정당성 평가

| 증가 항목 | 비용 | 정당성 | 평가 |
|----------|------|--------|------|
| 적응형 호출 +$101 | Career 4+ 이력서 추출 정확도 향상 | **정당** — 1-pass로 Career 5+를 처리하면 품질 저하 예상 |
| 섹션 분리 LLM +$30 | 비정형 이력서 처리 가능 | **정당** — 패턴 실패 시 아예 처리 불가보다 나음 |
| 총 +$131 | | **전체적으로 수용 가능** — $654는 여전히 Haiku Batch 시나리오 |

### 1.3 비용 리스크

| 시나리오 | 영향 | 확률 | 비용 변화 |
|---------|------|------|----------|
| Career 분포가 4+ > 30% (예상 20%) | N+1 호출 증가 | 20% | +$100~200 |
| 패턴 성공률 70% → 50% | LLM 폴백 50% | 30% | +$40 |
| Haiku 품질 미달 → Sonnet 전환 | 전면 비용 상승 | 15% | +$2,900 |
| 파일 이력서 100K → 150K | 전반적 증가 | 10% | +$80 |

**최악 시나리오** (Sonnet 전환): $654 → $3,580 — 이는 04.graphrag 전체 예산($8,235~8,895)의 40%에 해당. Phase 0 PoC에서 Haiku 품질 검증이 **프로젝트 성패를 좌우**.

---

## 2. 전제 조건 의존성 분석

### 2.1 Phase 0 PoC 의존 항목

v12는 다음 설계 결정을 Phase 0 PoC 결과에 의존:

| 결정 | PoC에서 검증 | 실패 시 영향 | 심각도 |
|------|------------|------------|--------|
| LLM 모델 (Haiku vs Sonnet) | scope_type ≥70% | 비용 5배 증가 | **Critical** |
| Embedding 모델 (text-embedding-005) | 한국어 분별력 | Vector Index 재생성 | High |
| Career 3/4 분기점 | Career 분포 프로파일 | 비용 ±20% | Medium |
| 1-pass vs N+1 품질 차이 | 20건 비교 | 전략 재설계 | High |
| 패턴 기반 섹션 분리 성공률 | 20건 파일 PoC | 비용 ±$40 | Low |

**5개 중 2개가 Critical/High이며, 모두 Week 1에 검증**. 이는 Phase 0의 1주일에 과도한 부담을 줄 수 있다.

### 2.2 20건 PoC 표본 크기의 적정성

| 검증 항목 | 20건으로 가능한 결론 | 한계 |
|----------|-------------------|------|
| scope_type 정확도 60% | 12/20 이상이면 통과 | 95% CI: ±21% (매우 넓음) |
| outcomes F1 50% | 대략적 방향 확인 | 통계적 유의성 불충분 |
| Embedding 분별력 | 방향 확인 가능 | 도메인별 편향 미탐지 가능 |

**20건은 Go/No-Go 판정에는 충분하지만, 설계 파라미터(분기점, 임계값) 확정에는 부족**. v12가 "Phase 0 검증: 20건 PoC에서 1-pass vs N+1 pass 품질/비용 비교 실측"이라고 기술한 것은 적절하나, **이 20건으로 Career 3개 분기점을 확정하는 것은 무리**.

### 2.3 권고

- Career 분기점은 Phase 0에서 **DB 프로파일링**(Career 수 분포)으로 결정하고, 품질 검증은 Phase 1의 1,000건에서 수행
- 1-pass vs N+1 품질 비교는 Phase 1에서 50건 Gold Set으로 재검증

---

## 3. 04.graphrag Core v2와의 정합성

### 3.1 일정 정합

| 추출 파이프라인 | v12 논리 순서 | Core v2 실제 Phase | Core v2 일정 | 정합 |
|--------------|-------------|-------------------|-------------|------|
| B (CandidateContext DB) | 2번째 | Phase 1 | Week 2-6 | **일치** |
| B' (CandidateContext 파일) | 3번째 | Phase 2 | Week 7-14 | **일치** |
| A (CompanyContext) | 1번째 | Phase 3 | Week 16-22 | **일치** |
| C (Graph 적재) | 4번째 | Phase 1-3 각각 | 전 Phase | **일치** |

v12의 §1.3 구현 순서 안내와 Core v2의 타임라인이 **일치**. 이 부분은 v12에서 잘 해소.

### 3.2 기술 스택 정합

| 항목 | v12 | Core v2 | 정합 |
|------|-----|---------|------|
| Graph DB | Neo4j AuraDB | Neo4j AuraDB | **일치** |
| LLM | Claude Haiku 4.5 Batch | Claude Haiku 4.5 Batch | **일치** |
| Embedding | text-embedding-005 (768d) | text-embedding-005 (768d) | **일치** |
| Batch 처리 | Cloud Run Jobs | Cloud Run Jobs | **일치** |
| 오케스트레이션 | Cloud Workflows | Cloud Workflows | **일치** |

### 3.3 관계명 불일치 (잔존)

| v12 (v19 canonical) | Core v2 사용 | 비고 |
|--------------------|-------------|------|
| PERFORMED_ROLE | HAD_ROLE | Phase 1 Graph 스키마 |
| OCCURRED_AT | AT_COMPANY | Phase 1 Graph 스키마 |
| IN_INDUSTRY | IN_INDUSTRY | **일치** |
| HAS_CHAPTER | HAS_CHAPTER | **일치** |

**2개 관계명 불일치**는 v12에서 "04.graphrag 측에서 v19 기준으로 업데이트할 의무"라고 선언했으나, Core v2 문서에서는 이 업데이트가 **미반영 상태**.

### 3.4 스키마 불일치 상세

Core v2의 Graph 스키마(§10)와 v12의 스키마(§5.1) 비교:

| 항목 | v12 | Core v2 | 차이 |
|------|-----|---------|------|
| Person 노드 속성 | person_id, name, gender, age, career_type, education_level | candidate_id, total_years, seniority_estimate, primary_domain | **ID 필드명 다름** |
| Chapter 노드 속성 | chapter_id, period, scope_type, seniority, domain_depth | chapter_id, scope_type, outcome, duration_months, is_current | **구조 차이** |
| Skill 노드 | skill_id, name, normalized_name, category, match_method | name (단순) | v12가 상세 |

**person_id vs candidate_id**는 구현 시 즉시 충돌할 수 있는 문제. Core v2의 코드 예시에서 `candidate_id`를 사용하고 있으므로, Phase 1 시작 전에 통일 필요.

---

## 4. 인프라 실현 가능성

### 4.1 Cloud Run Job 동시성

| Job | v12 설계 | Core v2 설계 | 정합 | 실현 가능성 |
|-----|---------|-------------|------|-----------|
| kg-parse | 50 병렬 | 명시 없음 | Core에서 구체화 필요 | Cloud Run 기본 제한 확인 필요 |
| kg-preprocess | 50 병렬 | 명시 없음 | Core에서 구체화 필요 | 동일 |
| kg-extract | 10 | 명시 없음 | Core에서 구체화 필요 | Batch API 동시성에 의존 |
| kg-graph-load | ≤5 | tasks=3~5 | **일치** | Neo4j connection pool 제한 |

### 4.2 Neo4j AuraDB Free 제약

| 제약 | v12 인지 여부 | 리스크 |
|------|-------------|--------|
| 200K 노드 한도 | 인지 (§3.1) | Phase 1은 1,000건이므로 문제 없음 |
| connection pool 3~5 | 인지 (Core v2) | kg-graph-load ≤5 적절 |
| APOC 미지원 가능성 | 인지 (Core v2) | 방법 B/C 대안 준비 |

### 4.3 결론

인프라 실현 가능성은 **높음**. Cloud Run Jobs 50 병렬은 GCP 기본 제한(default 100)을 넘지 않으므로 가능하나, 비용을 고려하면 Phase별 점진적 증가가 바람직.

---

## 5. 데이터 품질 전제 조건

### 5.1 DB 접근 전제

| 전제 | v12 의존도 | Core v2 준비 | 리스크 |
|------|-----------|-------------|--------|
| resume-hub asyncpg read replica | Pipeline B 전체 | Phase 0 사전 준비 | **DB 접근 불가 시 +5~6주 지연** |
| job-hub asyncpg read replica | Pipeline A | Phase 3 | Medium |
| code-hub 정규화 데이터 | Tier 1/2 비교 | Phase 1 | Low |
| NICE DB BRN 매칭 | Organization ER | Phase 3 | High (R2.4) |

### 5.2 텍스트 필드 품질

v12는 A20 가정(Career.workDetails null 비율 20%)에 의존:

```
workDetails null 20%일 때: LLM 추출 400K건
workDetails null 40%일 때: LLM 추출 300K건 (비용 -25%, 커버리지 -25%)
workDetails null 60%일 때: LLM 추출 200K건 (비용 -50%, 커버리지 -50%)
```

**workDetails null 비율이 40%를 넘으면**, CandidateContext 품질이 크게 저하되어 매칭 정확도에 직접 영향. 이 가정은 **Phase 0 DB 프로파일링에서 즉시 검증 필수**.

---

## 6. 종합 실현 가능성 평가

| 영역 | 점수 | 근거 |
|------|------|------|
| 비용 | 8/10 | $654 Batch는 합리적, Sonnet 전환 시만 리스크 |
| 일정 | 7/10 | 04.graphrag Core v2 일정과 정합, Phase 0 과부하 우려 |
| 기술 | 8/10 | GCP 네이티브 기반, 검증된 기술 스택 |
| 데이터 | 6/10 | DB 접근, NICE 매칭, 텍스트 품질 등 다수 전제 조건 |
| 팀 역량 | 7/10 | DE 1 + MLE 1 체제로 충분하나 병목 구간 존재 |
| **종합** | **7.2/10** | **구현 가능하지만 전제 조건 검증이 핵심** |
