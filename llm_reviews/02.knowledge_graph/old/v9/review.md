# v9 계획 리뷰

> v9 계획(5개 문서)의 타당성, 실현 가능성, 과설계, 부족 설계를 종합 평가한다.
> 실제 GraphRAG 구현 계획(`04.graphrag/results/implement_planning/core/`)과의 정합성도 검토한다.
>
> 작성일: 2026-03-11
> 리뷰 대상: 01~05 문서 전체 (v8 DB 기반 재설계 + v9 3-Tier 비교 전략 통일)

---

## 1. v7 리뷰 반영 완성도 (v8/v9 경유)

| v7 리뷰 잔여 항목 | 심각도 | v8/v9 반영 여부 | 반영 위치 | 평가 |
|---|---|---|---|---|
| R-1. 기본 temperature 미명시 | Low | **미반영** | — | v9에서도 여전히 LLM 호출 기본 temperature 미명시. 구현 시 해소 가능하나, 프롬프트 설계 문서에 `temperature=0.1` 등 기본값을 한 줄 명시하면 Tier 2 retry 전략과 일관성 확보 |
| R-2. chunk 크기 최적화 시점 | Low | **간접 반영** | 04 §0-3.1 | DB cursor 기반으로 변경되어 chunk 크기 조정이 더 유연해짐. 다만 의사결정 테이블에 여전히 미포함 |
| R-3. retry 비용 미반영 | Low | **미반영** | — | 03 문서 비용 모델에 파싱 실패 retry 비용이 여전히 미포함. v8 토큰 절감으로 retry 비용도 비례 감소하여 영향은 더 작아짐 (~$25~120) |
| R-4. INACTIVE 가중치 재분배 | Low | **미반영** | — | 02 §5.3에 여전히 `pass`. 구현 시 자연 해소 사항 |

**총평**: v7 잔여 이슈 4건 모두 Low이며, v8/v9에서 추가 반영하지 않은 것은 합리적 판단. DB 기반 전환과 3-Tier 비교 전략이라는 큰 변경에 집중한 것이 적절하다.

---

## 2. 타당성 평가

### 2.1 [매우 양호] DB 기반 파이프라인 전환 (v8 핵심)

**긍정적**:
- resume-hub/job-hub/code-hub DB 활용은 **가장 큰 아키텍처 개선**이다. 150GB 파일 파싱이라는 Critical 리스크(R2.3)를 완전 제거한 것은 매우 타당
- 토큰 절감(CompanyContext 44%, CandidateContext 40%)의 근거가 명확: 정형 필드 사전 제공으로 LLM이 추론에만 집중
- BRN 기반 NICE 매칭(60%→84%)으로 PastCompanyContext 커버리지가 실질적으로 향상
- Pre-Phase 0에서 DB 접근을 blocking dependency로 관리하여 v7 fallback 경로까지 확보

**판단**: v8 전환의 비즈니스 근거가 충분하며, 리스크 대비도 현실적이다.

### 2.2 [양호] 3-Tier 비교 전략 (v9 핵심)

**긍정적**:
- v11.1 `00_data_source_mapping.md` §1.5와 용어/구조/threshold를 통일한 것은 온톨로지-파이프라인 정합성 측면에서 정확한 접근
- Tier별 대상 분류 기준이 논리적:
  - Tier 1(정규화 적합): 유한 집합, 명확한 정체성 → CI Lookup
  - Tier 2(경량 정규화+임베딩): 상위 스킬은 CI 가능, 롱테일은 임베딩 → 하이브리드
  - Tier 3(임베딩 전용): 표현 다양성 높음, 정규화 시 거짓 동일성 위험 → 임베딩만
- `normalize_skill()` 함수가 v11.1 §1.3과 동일한 시그니처/로직으로 구현되어 온톨로지와의 정합성이 높음
- 전공 threshold 0.80→0.75 조정의 근거("의미적 유사성이 넓음")가 v11.1에 정의되어 있어 자의적이지 않음
- Embedding 비용 ~$0.06이 전체 비용 대비 무시할 수준이라는 산출이 정확

**경미한 이슈**:
- `compute_embedding_similarity_batch()`의 brute-force O(n×m) 비교는 canonical 사전이 ~2,800개 수준에서는 문제없으나, 향후 확장 시 FAISS/ScaNN 같은 ANN 인덱스 전환 경로가 미명시 (후술 R-1)

### 2.3 [양호] compute_skill_overlap() 하이브리드 (v9 신설)

**긍정적**:
- 정규화 성공/실패 스킬을 분리하여 각각 exact match / embedding 비교하는 전략이 합리적
- v11.1 §4.3과 정합하는 구현
- `match_method`별 confidence 세분화(CI=0.95, synonyms=0.85, embedding=0.70~0.80)가 다운스트림 MappingFeatures에서 가중치로 활용 가능

**경미한 이슈**:
- `weighted_overlap`이 exact match와 embedding match를 **동등 가중**으로 합산하는데, confidence 차이(0.95 vs 0.70~0.80)를 반영한 가중 합산이 더 적절할 수 있음 (후술 R-2)

### 2.4 [양호] 비용 모델 갱신 (03 문서)

**긍정적**:
- v8 토큰 절감이 시나리오별 비용에 정확히 반영됨
- "비용 절감이 상대적으로 작은 이유" 분석(LLM은 전체의 10~13%, 인건비/인프라가 대부분)이 정직하고 유용
- v8의 실질적 이점이 비용보다 **일정 단축(4~5주)과 리스크 제거**에 있다는 결론이 정확

### 2.5 [양호] 비정형 값 비교 품질 모니터링 (02 §10, v9 신설)

**긍정적**:
- 스킬 코드 매칭률, 임베딩 커버리지, 임베딩 정확도, 유사도 분포 등 4개 지표가 v11.1 §6.4와 정합
- 알람 조건(매칭률 <60%, 커버리지 <75%)이 구체적
- Phase 1-2에서 500건 수동 검증으로 threshold 적정성 확인하는 계획이 현실적

---

## 3. 실현 가능성 평가

### 3.1 [양호] 타임라인: 14~17주 (v9)

| Phase | v7 | v9 | 변경 | 실현 가능성 |
|---|---|---|---|---|
| Phase 0 | 3~4주 | 2~3주 | -1주 | **양호** — DB 프로파일링이 파일 탐색보다 빠름 |
| Phase 1-1 | 전처리 2주 | DB 커넥터 + 3-Tier 1~2주 | -0~1주 | **주의** — 3-Tier 비교 전략 모듈이 새로 추가되어 실질 절감이 제한적 (후술 F-1) |
| Phase 1-3 | 3주+1주 | 2주 | -1~2주 | **양호** — Rule 추출 제거가 실질적 절감 |
| Phase 1-4 | 2주 | 1~2주 | -0~1주 | **양호** — BRN 기반 ER 간소화 |
| Phase 2 | 4~5주 | 3~4주 | -1주 | **양호** — SiteUserMapping 기반 중복 제거 간소화 |

**총평**: 14~17주는 DE+MLE 2명 풀타임 기준으로 실현 가능하다. 다만 Phase 1-1의 3-Tier 비교 전략 모듈이 새로운 복잡성을 추가하므로 1주가 아닌 2주를 기본으로 잡는 것이 안전하다.

### 3.2 [주의] Phase 1-1: 3-Tier 비교 전략 모듈 (F-1)

**리스크**: 3-Tier 비교 전략 모듈은 v9에서 신규 추가된 컴포넌트로, 다음 작업을 1~2주에 완료해야 함:
- DB 커넥터 3개 (resume-hub, job-hub, code-hub)
- 데이터 매핑 모듈
- Tier 1 alias 사전 구축 (~750개)
- Tier 2 `normalize_skill()` + synonyms 매칭 + embedding fallback
- Tier 3 `compare_majors()` + `compute_embedding_similarity_batch()`
- Canonical embedding 사전 구축 (~2,800개)
- 캐시 레이어
- `compute_skill_overlap()` 하이브리드
- 100건 통합 테스트

**판단**: 이 모든 것을 1주에 완료하는 것은 비현실적이며, 2주가 최소이다. 04 문서에서 "1~2주"로 범위를 잡은 것은 적절하나, **하한(1주)은 달성 어렵다**. Phase 1-1을 **2주 고정**으로 계획하는 것을 권장한다.

### 3.3 [양호] DB 접근 의존성 관리

Pre-Phase 0에서 3개 DB 접근을 blocking dependency로 관리하고, 부분 접근 시 v7/v8 혼용까지 고려한 것은 현실적이다. 다만 실제 구현 계획(`04.graphrag`)에서는 DB-only MVP를 Phase 1에서 선행하고, 파일 이력서는 Phase 2로 미룬 구조이므로 정합성이 잘 맞는다.

### 3.4 [양호] Batch API 처리 (500K 이력서)

DB cursor 기반 1,000건/chunk 분할은 파일 I/O 대비 확실히 빠르고 안정적이다. Haiku Batch API 24시간 이내 응답 가정은 Anthropic 공식 SLA와 일치한다.

---

## 4. 과설계 평가

### O-1. [Medium] NORMALIZATION_CONFIDENCE 6단계 세분화 (02 §2.2)

```python
NORMALIZATION_CONFIDENCE = {
    "code_hub_ci":       0.95,
    "code_hub_synonyms": 0.85,
    "embedding_high":    0.80,   # >= 0.90
    "embedding_mid":     0.70,   # 0.80~0.90
    "embedding_low":     0.60,   # 0.75~0.80
    "unmatched":         0.0,
}
```

6단계 세분화는 v11.1 §6.4에 근거하므로 **온톨로지 정합 측면에서는 정당**하다. 그러나 Phase 0 PoC에서 이 6단계의 실질적 차별력을 검증하기 전에는 **3단계(high/mid/low)**로도 충분할 수 있다.

**판단**: v11.1과의 정합이 우선이므로 유지. 다만 Phase 0-2에서 6단계가 실질적으로 MappingFeatures 품질에 영향을 주는지 확인할 것을 권장한다.

### O-2. [Low] normalize_and_merge_skill() 3분기 분리 (02 §4.4)

CI 매칭, synonyms 매칭, 미매칭 각각에 대해 별도 Cypher 쿼리를 정의한 것은 코드 수준의 상세도이다. 계획 문서에서는 "match_method별 MERGE 전략" 한 줄로 충분할 수 있다.

**판단**: 구현 참조로서 가치가 있으므로 유지. **수정 불필요**.

### O-3. [Low] Phase 3 크롤링/structural_tensions 상세 (v7 이전부터 유지)

v7 리뷰에서 O-1, O-2로 지적한 항목이 v9에서도 그대로 유지되어 있다.

**판단**: v10 정합 참조용이므로 수용 가능. **수정 불필요**.

### O-4. [Low] Tier 1 alias 사전 예시 코드 (02 §4.3)

```python
TIER1_ALIAS = {
    "university": {"서울대": "서울대학교", ...},
    "company": {"네이버": "naver", ...},
    "skill_category": {"frontend": "프론트엔드", ...},
}
```

코드 예시가 계획 문서에 포함되어 있으나, 이는 구현 시점에 충분히 결정할 수 있는 사항이다.

**판단**: 구현 가이드로서 유용. **수정 불필요**.

---

## 5. 부족 설계 평가

### R-1. [Medium] ANN 인덱스 전환 경로 미정의

`compute_embedding_similarity_batch()`는 brute-force O(n×m) 비교이다. 현재 canonical 사전 ~2,800개에서는 문제없으나:
- Phase 2에서 500K 이력서의 미정규화 스킬을 비교할 때, 유니크 스킬 수가 수만 개에 달하면 성능 문제 발생 가능
- v9에서 캐시 전략(동일 텍스트 1번만 계산)으로 유니크 수를 줄이지만, canonical 사전 대비 비교 횟수는 여전히 O(유니크 수 × canonical 수)

**권장**: Phase 1-1에서 FAISS/ScaNN 같은 ANN 인덱스를 canonical embedding에 적용하는 것을 선택적 최적화로 명시. 구현 복잡도는 10줄 미만(FAISS IndexFlatIP 생성)이므로 일정 영향 미미.

### R-2. [Low] compute_skill_overlap() 동등 가중 합산

```python
weighted_overlap = (len(exact_matches) + len(embedding_matches)) / total_jd
```

exact match(confidence 0.95)와 embedding match(confidence 0.70~0.80)를 동등하게 합산한다. "Java" exact match와 "자바스크립트↔TypeScript" embedding match(0.86)가 동일 가중이 되는데, 이는 다운스트림에서 왜곡을 줄 수 있다.

**영향도**: Low — MappingFeatures 단계에서 별도로 confidence 가중을 적용할 수 있으므로 파이프라인 수준에서는 수용 가능. 다만 `compute_skill_overlap()` 자체에 confidence 가중 옵션을 추가하면 더 정확한 overlap_ratio를 산출할 수 있음.

### R-3. [Low] synonyms 사전 구축 계획 부재

02 문서 §4.3의 `normalize_skill()`에서 synonyms 매칭을 2단계로 적용하지만, synonyms 사전의 **초기 구축 방법과 규모**가 명시되지 않았다:
- code-hub `attributes` JSONB 내 `synonyms` 필드를 참조한다고 했으나, 이 필드의 실제 커버리지가 불확실
- synonyms 사전이 비어있으면 Tier 2의 2단계(synonyms 매칭)가 무력화되어 바로 임베딩 fallback으로 전환

**권장**: Phase 0-1 DB 프로파일링에 "code-hub attributes JSONB 내 synonyms 필드 커버리지 확인" 항목을 추가. 커버리지 50% 미만이면 수동/반자동 synonyms 구축 계획 수립.

### R-4. [Low] v7 리뷰 잔여 미반영 (R-1~R-4)

v7 리뷰의 4건 잔여 이슈가 모두 미반영이나, 전부 Low이고 구현 시 자연 해소 가능. 문서 레벨에서의 추가 반영은 불필요.

---

## 6. 04.graphrag 구현 계획과의 정합성

> 실제 GraphRAG 구현 계획(`04.graphrag/results/implement_planning/core/v2`)과 v9 추출 파이프라인 계획의 정합성을 검토한다.

### 6.1 구조적 정합

| 항목 | v9 (02.knowledge_graph) | core v2 (04.graphrag) | 정합 여부 |
|---|---|---|---|
| **Phase 구조** | Phase 0→1→2→3 (순차) | Phase 0→1→2→3→4 (순차, 데이터 확장 중심) | **유사** — core v2가 Phase를 더 세분화 |
| **MVP 범위** | JD 100건 + 이력서 1,000건 | DB 텍스트 이력서 1,000건 (Phase 1) | **정합** |
| **파일 이력서** | v8에서 제거 (DB 기반) | Phase 2에서 PDF/DOCX/HWP 통합 | **불일치** — 아래 상세 |
| **기업 정보** | Pipeline A (CompanyContext) | Phase 3에서 JD + NICE + 매칭 | **정합** — 순서만 다름 |
| **Embedding 모델** | text-multilingual-embedding-002 | text-embedding-005 (768d) | **불일치** — 아래 상세 |
| **Graph DB** | Neo4j AuraDB | Neo4j AuraDB | **정합** |

### 6.2 [주의] 파일 이력서 처리 불일치

- **v9**: DB 기반으로 전환하여 파일 파싱을 **완전 제거**. v7 fallback은 DB 접근 불가 시에만 적용
- **core v2**: Phase 1은 DB 텍스트 MVP, Phase 2(8주)에서 **파일 이력서 통합을 주요 작업**으로 계획

이는 **모순이 아닌 보완 관계**로 볼 수 있다:
- v9는 "추출 로직 설계" 관점에서 DB-first를 정당화
- core v2는 "실제 구현" 관점에서 DB에 없는 이력서(파일만 존재)도 커버해야 하므로 Phase 2에서 파일 처리를 추가

**권장**: v9 문서에서 "DB에 적재되지 않은 이력서가 존재할 경우"의 처리 경로를 명시적으로 언급하면 정합성이 향상된다. 현재는 A23("resume-hub 전체 이력서 적재 완료" 가정)에 의존하고 있으나, core v2는 이 가정이 충족되지 않는 시나리오를 Phase 2로 명시적으로 다루고 있다.

### 6.3 [주의] Embedding 모델 불일치

- **v9**: `text-multilingual-embedding-002` (Vertex AI) — v6에서 v10 확정 모델로 채택
- **core v2**: `text-embedding-005` (768d) — 전체 통일

두 문서가 서로 다른 Embedding 모델을 사용한다. 동일 프로젝트의 두 계획이 다른 모델을 사용하면 **벡터 호환성 문제**가 발생한다 (같은 텍스트의 embedding이 다른 모델에서 다른 벡터를 생성하므로 cosine similarity가 무의미해짐).

**권장**: 두 문서 간 Embedding 모델을 통일해야 한다. Phase 0 PoC에서 두 모델을 비교 검증한 후 하나로 확정하는 것이 적절하다.

### 6.4 [양호] 나머지 정합

- Graph 스키마(Node/Edge 구조), Deterministic ID, Idempotency 전략은 양쪽이 일관적
- 비용 모델의 LLM 선택(Haiku 4.5 primary)이 일치
- 오케스트레이션 전략(Pipeline DAG)이 양립 가능

---

## 7. 리뷰 결론

### 문서별 판정

| 영역 | v7 판정 | v9 판정 | 변화 |
|---|---|---|---|
| Gap 분석 (01) | 충분 | **충분** | v8 DB 전환 + v9 3-Tier 변경사항 반영, 버전 이력 추적 우수 |
| 파이프라인 설계 (02) | 충분 | **충분 (강화)** | DB 기반 재설계 + 3-Tier 비교 전략 + 모니터링 지표 추가 |
| 비용 모델 (03) | 충분 | **충분** | 토큰 절감 반영, Embedding 비용 산출 추가, v7→v8 비용 변경 분석 정직 |
| 실행 계획 (04) | 충분 | **충분** | DB 기반 타임라인 단축(14~17주), 3-Tier 모듈 일정 반영 |
| 리스크 (05) | 충분 | **충분 (강화)** | 4건 제거(파싱 관련), 5건 신규(DB 관련), 심각도 조정 적절 |

### 잔여 이슈 요약

| ID | 이슈 | 심각도 | 구현 시 자연 해소 | 문서 수정 필요 |
|---|---|---|---|---|
| R-1 | ANN 인덱스 전환 경로 미정의 | Medium | O (Phase 2 성능 이슈 시) | 선택적 — 04 Phase 1-1에 한 줄 추가 |
| R-2 | skill overlap 동등 가중 합산 | Low | O | X |
| R-3 | synonyms 사전 구축 계획 부재 | Low | O (Phase 0 프로파일링에서 확인) | 선택적 — 04 Phase 0-1에 항목 추가 |
| R-4 | v7 리뷰 잔여 4건 미반영 | Low | O | X |
| O-1 | NORMALIZATION_CONFIDENCE 6단계 | Medium (과설계 가능) | — | X (v11.1 정합 우선) |

### 04.graphrag 정합성 이슈

| ID | 이슈 | 심각도 | 해소 방법 |
|---|---|---|---|
| G-1 | 파일 이력서 처리 불일치 | Medium | v9에 "DB 미적재 이력서" 처리 경로 언급 추가 |
| G-2 | Embedding 모델 불일치 | **High** | Phase 0에서 모델 통일 확정 필수 |

### 최종 판정

v9는 v8의 DB 기반 전환과 v11 온톨로지 정합이라는 **두 가지 핵심 변경을 적절히 수행**했다.

**타당성**: DB-first 접근은 파싱 리스크 제거, 토큰 절감, 일정 단축의 세 가지 이점을 동시에 달성하며, 3-Tier 비교 전략은 비표준 데이터 비교에 대한 체계적 해법을 제시한다.

**실현 가능성**: 14~17주 타임라인은 Phase 1-1을 2주로 잡으면 현실적이다. DB 접근 확보가 전제 조건이며, 이를 blocking dependency로 관리하고 있으므로 적절하다.

**과설계**: 코드 수준의 상세도(Pydantic 스키마, Cypher 쿼리, Python 함수)가 계획 문서로서는 과하나, 구현 가이드로서의 가치가 있으므로 수용 가능하다.

**부족 설계**: synonyms 사전 구축 계획, ANN 인덱스 전환 경로가 미비하나 모두 구현 시 자연 해소 가능한 수준이다.

**가장 중요한 액션 아이템**: 04.graphrag 구현 계획과의 **Embedding 모델 불일치(G-2)**를 Phase 0 PoC 이전에 반드시 해소해야 한다.

**v9 계획은 04.graphrag 구현 계획의 입력 설계 문서로서 충분한 완성도를 갖추었다.** G-2 해소 후 실행 단계 진입 가능.
