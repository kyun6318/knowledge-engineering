# GraphRAG Core 확장 계획 v1 — 리뷰

> **리뷰 대상**: `03.ml-platform/plans/graphrag/core/1/` (7개 문서)
> **리뷰 관점**: 타당성, 실현 가능성, 과도한 설계, 부족한 설계
> **리뷰 일자**: 2026-03-08

---

## 1. 총평

데이터 확장 순서(DB텍스트 → 파일이력서 → 기업정보 → 외부보강)로 접근하는 전략은 **standard의 기능 단위 접근 대비 명확한 장점**이 있다. Week 6에 에이전트 최초 연동이 가능하다는 점은 비즈니스 가치 조기 시연 측면에서 우수하다. Go/No-Go 게이트, checkpoint 기반 재시작, 비용 추정 등 실무 필수 요소가 잘 갖춰져 있다.

그러나 **Phase 2의 450K Batch 처리 타임라인이 가장 큰 리스크**이며, 일부 영역에서 과도한 상세화(일별 시간표, 조기 Runbook)와 반대로 핵심 기술 난제(Organization ER, 매칭 알고리즘, 에이전트 API 설계)의 과소 설계가 공존한다.

**권장**: 전체 구조는 유지하되, 아래 지적 사항을 반영하여 리스크가 높은 영역의 설계를 보강하고, 불필요한 상세화를 줄일 것.

---

## 2. 타당성 (Validity)

### 2.1 전략적 타당성 — 우수

| 항목 | 평가 | 근거 |
|------|------|------|
| 데이터 확장 순서 접근 | **적절** | 에이전트 조기 연동(Week 6)으로 피드백 루프 형성 가능 |
| Phase별 Go/No-Go | **적절** | 5개 의사결정 포인트, 미달 시 대응 방안 명시 |
| 2명 체제 25주 | **적절** | DE/MLE 역할 분담 합리적, 병렬 작업 구조 |
| standard 대비 비용 절감 | **적절** | ~$1,000 절감 (Phase 0 축소 + 인프라 기간 효율화) |
| 크롤링 포함 | **조건부 적절** | 법적 리스크 해소 전까지는 가치 불확실 (아래 3.2 참조) |

### 2.2 기술적 타당성 — 양호 (일부 보완 필요)

**타당한 선택:**
- Neo4j AuraDB Free → Professional 전환 시점 (Phase 2 시작)
- Anthropic Batch API + Haiku 조합 (비용 효율)
- BigQuery processing_log 기반 checkpoint
- SimHash 중복 제거
- text-embedding-005 (768d) — 한국어 성능 우수

**재검토 필요:**

| 항목 | 문제 | 권장 |
|------|------|------|
| Embedding 차원 불일치 | Overview: 768d (text-embedding-005), Phase 2 참고: 1536d (Ada) | text-embedding-005 768d로 통일, Ada 언급 제거 |
| Neo4j MERGE 단건 처리 | `load_candidate_to_graph()`가 경력마다 개별 session.run() | UNWIND 배치 처리로 변경 (100건/트랜잭션) |
| Cloud Run Job task 수 | 파싱 Job tasks=50이지만, Neo4j max_connection_pool_size=2 | 파싱과 Graph 적재 분리 확인, Neo4j 접근 Job은 tasks ≤ 5 |
| Makefile 오케스트레이션 | Phase 1~2에서 Makefile 사용 → Phase 4에서 Cloud Workflows | 처음부터 Cloud Workflows 또는 일관된 오케스트레이션 도구 선택 |

---

## 3. 실현 가능성 (Feasibility)

### 3.1 Phase 2 — 450K Batch 처리 (HIGH RISK)

**핵심 문제**: 3주(Week 10-12)에 450K 처리 완료는 **기본 시나리오(12h/라운드)에서도 93%만 완료**되며, 비관 시나리오에서는 47%에 불과하다.

```
계획서 자체 분석:
  낙관(6h): 100% → 11.25일
  기본(12h): 93% → 22.5일  ← 3주(21일) 부족
  비관(24h): 47% → 45일    ← 크게 부족
```

**추가 리스크 요인** (계획서에 미반영):
- Anthropic Batch API의 실제 동시 활성 batch 한도가 10 미만일 가능성
- 450K 중 dead-letter 비율이 5% 이상이면 재처리 시간 추가
- Graph 적재(Neo4j Professional)도 450K 노드 + 2.25M 관계 삽입에 상당 시간 소요
- Neo4j Professional의 동시 연결 한도(5~10개)로 적재 병렬성 제한

**권장**:
1. Phase 2 기간을 **6주 → 8주**로 연장하거나, 처리 완료 목표를 **80%**로 하향 조정
2. Graph 적재 시간을 별도 벤치마크 (1,000건 적재 → 450K 외삽)
3. Batch API 동시 한도가 5 미만이면 **Gemini Flash 병행** 전략을 Phase 0에서 사전 검증

### 3.2 크롤링 법적 리스크 (HIGH RISK)

계획서에서 크롤링을 Phase 1 핵심 작업으로 배치했으나, **법적 검토가 Week 0 사전 준비에 불과**하다. 법무 검토에 4~8주 소요될 수 있으며, 부정적 결론이면 Phase 1의 크롤링 파이프라인 전체가 무효화된다.

**권장**:
1. Phase 1에서 크롤링을 **선택적 부가 기능**으로 분리 — DB 데이터만으로도 MVP 완성 가능하도록 설계
2. 법무 결론 전까지 크롤링 개발에 DE 리소스를 **50% 이상 투입하지 않음**
3. 크롤링 불가 시 대체 데이터 소스(파트너사 API, 데이터 구매 등) 사전 식별

### 3.3 HWP 파싱 (MEDIUM RISK)

한국 특화 이력서의 HWP 비율이 높을 경우(30%+), CER ≤ 0.15 달성이 어려울 수 있다.

- `pyhwp`는 안정성 부족 (0.1b12 베타)
- LibreOffice headless 변환은 서식 손실
- Gemini 멀티모달 OCR은 비용 증가 (건당 ~$0.01)

**권장**: Phase 0에서 HWP 비율 확인 후, **30% 이상이면 Phase 2-0 PoC를 2일 → 4일로 확대**. HWP 전용 상용 파서(한글과컴퓨터 API 등) 검토.

### 3.4 Organization ER — 1주 배정 (MEDIUM RISK)

Phase 3-3에서 Organization Entity Resolution에 **1주(Week 17)**만 배정했으나, 한국어 회사명 ER은 극도로 어려운 문제다.

```
예시 난제:
- "삼성전자" vs "Samsung Electronics" vs "삼성전자(주)" vs "SAMSUNG"
- "카카오" vs "카카오뱅크" vs "카카오엔터프라이즈" (계열사 구분)
- "네이버" vs "NHN" (사명 변경 이력)
- "(주)토스" vs "비바리퍼블리카" (서비스명 vs 법인명)
```

계획서에 "전수 검수 500개"를 명시했으나, 50K Organization 노드 중 500개는 1%에 불과하다.

**권장**:
1. Organization ER 기간을 **1주 → 2주**로 확장
2. Rule-based 1차 매칭(정규화 + 사전) + LLM 2차 매칭(애매한 케이스) 2단계 접근
3. 검수 규모를 **1,000개 이상** (최소 2%)으로 확대
4. 계열사/사명변경 사전을 Phase 2-1-8에서 미리 구축

### 3.5 인력 소진도 (MEDIUM RISK)

2명이 25주(약 6개월) 풀타임으로 Phase 0~4를 수행하는 것은 **번아웃 리스크**가 있다. 버퍼 1주(Week 13)만으로는 부족하다.

**권장**: Phase 2-3 사이(Week 13)와 Phase 3-4 사이(Week 19 후)에 각각 **1주 버퍼** 확보 (총 2주)

---

## 4. 과도한 설계 (Over-Engineering)

### 4.1 일별 시간 스케줄 (Phase 2-1)

Week 8-9의 **시간 단위 일정표**(Monday 09:00-10:30, 10:30-12:00...)는 과도하다. 실제 개발에서 이 수준의 계획은 첫 날부터 무너지며, 유지보수 비용만 발생한다.

```
현재 (과도):
  Monday (4일):
    09:00-10:30 - 2-1-3 시작 (섹션 분할기 구조 설계)
    10:30-12:00 - 2-1-1 시작 (PDF/DOCX 파서 구현 시작)
    13:00-17:00 - 2-1-1 진행 (파서 테스트 케이스)

권장 (주 단위로 충분):
  Week 8: PDF/DOCX/HWP 파서 + 섹션 분할 (DE + MLE 병렬)
  Week 9: PII + 중복제거 + JD 파서 + Docker (DE + MLE 병렬)
```

**권장**: 주(Week) 단위 마일스톤으로 축소, 일일 스탠드업으로 조정

### 4.2 Phase 0-1 단계의 Runbook (06_cost_and_monitoring.md)

Phase 0-1은 **PoC + MVP** 단계인데, Runbook 5종 + Alarm 10종 + Slack Webhook + PagerDuty 연동까지 설계되어 있다. 이 수준의 운영 인프라는 **Phase 4(프로덕션) 진입 시점**에 구축해도 충분하다.

**권장**:
- Phase 0-1: BigQuery 쿼리 3종 + Slack 수동 알림으로 축소
- Phase 2: Alarm 3종(Job 실패, Neo4j 연결, Batch 만료) 추가
- Phase 4: 전체 모니터링 + Runbook 구축

### 4.3 Phase 4 기업 인텔리전스 범위

CompanyContext 보강에서 `tension_type`, `tension_description`, `culture_signals`, `scale_signals` 등은 **에이전트 MVP에 필수가 아닌 nice-to-have** 기능이다.

```
필수 (Phase 4에 포함):
- product_description, market_segment
- funding (round, amount)
- employee_count, founded_year

선택 (Phase 5 이후로 이동 가능):
- tension_type, tension_description
- culture_signals (remote_friendly, diversity_focus, learning_culture)
- scale_signals (growth_rate, market_position)
- growth_narrative
```

**권장**: `tension`과 `culture_signals`를 Phase 5로 이동하여 Phase 4 기간을 **6주 → 4주**로 단축 가능

### 4.4 크롤링 정책 문서의 조기 상세화 (Phase 4)

Phase 4의 `CRAWLING_POLICY.md`가 Phase 4 시작 전(Week 19)에 이미 상세 작성되어 있다. 법무 검토 결과에 따라 전면 수정될 수 있으므로 조기 상세화는 낭비다.

**권장**: 법무 결론 후 작성. Phase 4 계획에는 정책 문서 작성 태스크만 명시.

### 4.5 Phase 2 인력비 추정

Phase 2 문서에 DE/MLE **시간당 인건비**(75,000원, 80,000원)와 총 인력비(37.2M원)가 포함되어 있으나, 이는 **프로젝트 전체 비용 문서(06_cost_and_monitoring.md)에서 Gold Label 인건비만 계상**하는 것과 일관성이 없다. 인건비는 별도 관리하거나 전체에 일괄 적용해야 한다.

**권장**: 인력비는 전 Phase 통합 비용 문서에서 일괄 계산하거나, 각 Phase 문서에서 제거

---

## 5. 부족한 설계 (Under-Engineering)

### 5.1 에이전트 서빙 API 설계 — 미흡

계획서에서 "에이전트 연동"을 반복 언급하지만, **에이전트가 Graph를 조회하는 API 인터페이스가 전혀 설계되어 있지 않다**. Cypher 쿼리 5종만 있을 뿐, 에이전트가 호출할 수 있는 서비스 레이어가 없다.

```
현재 설계:
  에이전트 → (?) → Neo4j Cypher

필요한 설계:
  에이전트 → GraphRAG API (REST/gRPC) → Query Router → Neo4j
                                           ├── Cypher 쿼리 실행
                                           ├── Vector Search
                                           ├── 매칭 스코어 계산
                                           └── 결과 포맷팅
```

**권장**:
1. Phase 1에 **에이전트 서빙 API 설계** 태스크 추가 (1일)
2. 최소 API 명세: 스킬 검색, 시맨틱 검색, 복합 조건 검색
3. 인증/인가, rate limiting, 응답 포맷 정의
4. Phase 3에서 매칭 API 확장

### 5.2 데이터 품질 프레임워크 — 미흡

450K 이력서 대규모 처리에서 **체계적 품질 측정 방법이 부족**하다. "50건 수동 검증"은 450K의 0.01%에 불과하다.

```
현재:
  Phase 1: 50건 수동 확인
  Phase 2: Golden 50건 regression
  Phase 4: Gold Test Set (200건)

필요:
  - 자동화된 품질 메트릭 (schema 준수율, 필드 완성도, 분포 이상)
  - 샘플링 기반 통계적 품질 추정 (95% 신뢰구간)
  - 프롬프트 버전별 A/B 비교
  - 데이터 드리프트 감지 (시간에 따른 품질 변화)
```

**권장**:
1. Phase 1에 **자동 품질 체크 스크립트** 추가: JSON schema 검증, 필수 필드 비율, 분포 이상 감지
2. Phase 2에 **통계적 샘플링 검증** 추가: 450K 중 무작위 384건 (95% 신뢰구간, ±5%)
3. BigQuery에 `quality_metrics` 테이블 추가

### 5.3 매칭 알고리즘 설계 — 미흡

Phase 3-4의 `MappingFeatures + MAPPED_TO`에 2주가 배정되었으나, **매칭 로직의 구체적 설계가 부재**하다.

```
현재 설계:
  MAPPED_TO { overall_match_score, feature_vector }
  → 이것만으로는 "어떻게 스코어를 계산하는지" 알 수 없음

필요한 설계:
  1. 피처 정의: 어떤 피처가 매칭에 사용되는가?
     - 스킬 매칭 (Jaccard? Cosine on embeddings?)
     - 경력 연수 매칭 (범위? 가중치?)
     - 시니어리티 매칭 (동일? 근접?)
     - 업종/직무 매칭 (KSIC 코드? LLM 판단?)

  2. 스코어 계산 방법:
     - 가중 합산? 학습 기반?
     - 임계값 (MAPPED_TO 관계 생성 기준)
     - 스코어 정규화 (0~1)

  3. 역방향 매칭:
     - "이 후보자에게 적합한 포지션" 구현 방법
     - 전수 계산? 근사? pre-computation?
```

**권장**: Phase 3 시작 전(Week 13 버퍼 또는 Phase 3 Day 1)에 **매칭 알고리즘 설계 문서** 작성

### 5.4 Neo4j 대규모 쿼리 성능 — 미흡

Phase 1의 Cypher 쿼리 5종이 **1,000건에서는 동작하지만, 450K에서의 성능이 검증되지 않았다**.

```
예: Q5 복합 조건 쿼리
  MATCH (p:Person)-[:HAS_CHAPTER]->(c:Chapter)-[:USED_SKILL]->(s:Skill)
  WHERE s.name IN $skills AND p.total_years >= $min_years ...

  Person 450K × Chapter 2.25M × Skill 5K
  → 인덱스 없이 실행하면 수십 초 이상 소요 가능
```

**권장**:
1. Phase 2 완료 시점에 **쿼리 성능 벤치마크** 추가 (각 쿼리 × 450K 데이터)
2. 필요 시 **복합 인덱스** 추가 (Skill.name + Person.total_years 등)
3. Vector Search 성능 테스트 (768d × 2.25M 노드)
4. 쿼리 결과 캐싱 전략 (자주 사용되는 필터 조합)

### 5.5 롤백 전략 — 미흡

Neo4j 데이터 손상이나 잘못된 Batch 결과 적재 시 **롤백 방법이 없다**. MERGE 기반이라 중복은 방지되지만, 잘못된 데이터가 기존 노드를 덮어쓰는 경우 복구 불가.

**권장**:
1. Graph 적재 전 **스냅샷 백업** 필수화
2. 적재 트랜잭션에 **버전 태그** 추가 (`loaded_batch_id`, `loaded_at`)
3. 특정 batch의 적재 결과를 **선택적 삭제** 가능하도록 설계

### 5.6 보안 — 최소 권한 원칙 미적용

서비스 계정 `kg-pipeline`에 `storage.objectAdmin`, `bigquery.dataEditor`, `run.invoker` 등 **광범위한 권한**이 부여된다. 크롤링, 전처리, LLM 추출, Graph 적재가 **모두 동일 서비스 계정**을 공유한다.

**권장**:
1. 파이프라인 단계별 서비스 계정 분리 (최소 3개: 크롤링, 처리, 적재)
2. `storage.objectAdmin` → `storage.objectViewer` + `storage.objectCreator` 분리
3. VPC 네트워크 설정 (Neo4j 접근은 Cloud Run에서만 허용)

---

## 6. 내부 불일치

| # | 위치 | 불일치 내용 | 권장 수정 |
|---|------|-----------|----------|
| 1 | Overview §13 vs 06_cost §1.6 | 총비용 $7,805~8,205 vs $8,023~8,773 | 06_cost 기준으로 Overview 수정 |
| 2 | Overview §9 vs Phase 2 참고 | Embedding 768d (text-embedding-005) vs 1536d (Ada) | 768d로 통일 |
| 3 | Phase 2 프로젝트 구조 | `crawlers/linkedin_crawler.py`, `github_crawler.py` | 실제 크롤링 대상 사이트와 불일치 — 제거 또는 수정 |
| 4 | Phase 2-2 Vector Index | `vector.dimensions: 1536`, `vector.similarity_metric: 'cosine'` | 768d + `similarity_function`으로 수정 (Phase 0과 일치) |
| 5 | Phase 1 vs Phase 2 | Phase 1 Batch API 단가 $0.003/건, Phase 2도 $0.003/건 | Haiku Batch 실제 단가로 통일 확인 |
| 6 | Overview §1 | Phase 1 "크롤링 데이터" 포함 | 크롤링 법적 리스크 시 DB 텍스트만으로 MVP 가능 명시 |

---

## 7. 리스크 매트릭스 (종합)

| 리스크 | 확률 | 영향 | 등급 | 대응 |
|--------|------|------|------|------|
| Batch API 동시 한도 < 10 | 중 | 높음 | **HIGH** | Phase 0에서 즉시 확인, Gemini Flash 대비 |
| 450K 처리 3주 내 미완료 | 높음 | 중 | **HIGH** | Phase 2 기간 연장 (+2주) |
| 크롤링 법적 불허 | 중 | 높음 | **HIGH** | Phase 1에서 크롤링 분리, DB-only MVP |
| Organization ER 품질 미달 | 중 | 중 | **MEDIUM** | 기간 연장 + 계열사 사전 사전 구축 |
| HWP CER > 0.15 | 중 | 중 | **MEDIUM** | 상용 파서 검토, HWP 제외 옵션 |
| 2인 번아웃 | 중 | 중 | **MEDIUM** | 버퍼 2주 확보, Phase 3-4 분리 |
| Neo4j 쿼리 성능 (450K) | 낮음 | 중 | **MEDIUM** | Phase 2 벤치마크 추가 |
| 매칭 품질 미달 | 중 | 중 | **MEDIUM** | 매칭 알고리즘 사전 설계 |

---

## 8. 권장 변경 요약

### 8.1 필수 (Must)

| # | 변경 | 영향 |
|---|------|------|
| M1 | Phase 2 기간 6주 → 8주 (또는 완료 목표 80%로 하향) | 타임라인 +2주 |
| M2 | 에이전트 서빙 API 설계 추가 (Phase 1, 1일) | 에이전트 연동 실질화 |
| M3 | Organization ER 기간 1주 → 2주 | Phase 3 기간 +1주 |
| M4 | Embedding 차원 768d로 전체 통일 | 문서 일관성 |
| M5 | Graph 적재 Neo4j MERGE → UNWIND 배치 처리 | 성능 |
| M6 | 크롤링을 Phase 1 필수 의존에서 제거 (DB-only MVP 가능) | 법적 리스크 분리 |

### 8.2 권장 (Should)

| # | 변경 | 영향 |
|---|------|------|
| S1 | Phase 2-1 일별 시간표 → 주 단위로 축소 | 계획 유지보수 비용 감소 |
| S2 | Phase 0-1 Runbook/Alarm → Phase 4로 이동 | 설계 부담 감소 |
| S3 | tension/culture_signals → Phase 5로 이동 | Phase 4 기간 -2주 |
| S4 | 자동 품질 메트릭 + 통계적 샘플링 추가 | 품질 보장 |
| S5 | 매칭 알고리즘 설계 문서 작성 (Phase 3 전) | 설계 완성도 |
| S6 | 서비스 계정 분리 (최소 3개) | 보안 강화 |
| S7 | Graph 적재 버전 태그 + 선택적 롤백 | 운영 안정성 |
| S8 | 버퍼 1주 추가 (Phase 3-4 사이, 총 2주) | 번아웃 방지 |

### 8.3 선택 (Could)

| # | 변경 | 영향 |
|---|------|------|
| C1 | 오케스트레이션 도구 통일 (Makefile → Cloud Workflows) | 일관성 |
| C2 | 인력비 계산 방식 통일 | 비용 문서 일관성 |
| C3 | Phase 2 쿼리 성능 벤치마크 추가 | 사전 위험 감지 |
| C4 | HWP 상용 파서 검토 (한글과컴퓨터 API) | 파싱 품질 |

---

## 9. 변경 적용 시 예상 타임라인

```
현재 계획: ~25주 (Week 1-25)
변경 적용 후: ~29주 (Week 1-29)

Phase 0 (1주):     Week 1       ← 변경 없음
Phase 1 (5주):     Week 2-6     ← +에이전트 API 설계 (기존 기간 내 흡수)
Phase 2 (8주):     Week 7-14    ← +2주 연장 (M1)
버퍼 (1주):        Week 15      ← 변경 없음
Phase 3 (7주):     Week 16-22   ← +1주 (Organization ER, M3)
버퍼 (1주):        Week 23      ← 신규 추가 (S8)
Phase 4 (4-6주):   Week 24-29   ← tension/culture 이동 시 -2주 (S3)

최종: ~29주 (보수적) / ~27주 (S3 적용 시)
```

---

## 10. 결론

본 계획은 **데이터 확장 순서 접근이라는 핵심 전략이 우수**하며, GraphRAG 구축을 위한 실무적 로드맵으로서 높은 완성도를 보인다. 그러나 **Phase 2의 대규모 처리 타임라인**, **에이전트 API 부재**, **Organization ER 과소 추정**이 실현 가능성을 위협하는 주요 요인이다. 위 권장 사항 중 Must 6건을 우선 반영하면 실행 리스크를 크게 줄일 수 있다.
