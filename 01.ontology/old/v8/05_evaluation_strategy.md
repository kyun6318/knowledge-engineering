# GraphRAG vs Vector Baseline 비교 실험 계획 v8

> v4 amendments A7(GraphRAG vs Vector 비교 실험 계획)을 독립 문서로 확장.
>
> 작성일: 2026-03-08 | 기준: v4 amendments A7 + v7 Vector baseline 구체화
>
> **v8 변경** (2026-03-08):
> - [E-1] 피처명을 03_mapping_features 기준으로 교정 (5개 전부)
> - [E-2] 과도한 pseudo-code를 함수 시그니처 + 핵심 로직 주석으로 축소
> - [E-3] 10절 가상 실험 데이터에 경고 배너 추가
> - [M-1] 임베딩 모델 04_graph_schema와 통일 확인

---

## 0. 배경 및 문제 정의

v3 평가에서 "GraphRAG vs 단순 Vector 검색의 ROI 검증"이 제기되었으나, v4~v6에서도 구체적 비교 실험 계획이 수립되지 않았다. v1 파일럿 완료 후 GraphRAG의 구조적 피처(MappingFeatures 5개)가 단순 임베딩 유사도 대비 실질적 매핑 품질 개선을 가져오는지 정량적으로 검증해야 한다.

**핵심 질문:**
- GraphRAG의 그래프 기반 MappingFeatures(5개)가 없이, 단순 Vector 임베딩만으로도 충분한가?
- LLM Reranking 추가 시 구조화된 Graph의 가치가 상대적으로 감소하는가?
- v2 확장 방향(Company 간 관계, tension_alignment 등)에 투자할 가치가 있는가?

---

## 1. 실험 설계

| 항목 | 내용 |
|---|---|
| **목적** | GraphRAG(Neo4j + MappingFeatures)가 Vector-only 대비 매핑 품질을 유의미하게 개선하는지 검증 |
| **시기** | v1 파일럿 50건 완료 후 (2026-04월 예정) |
| **비교 대상** | (A) GraphRAG: 그래프 기반 MappingFeatures 5개 피처 / (B) Vector: JD+이력서 임베딩 cosine similarity / (B') Vector + LLM Reranking |
| **평가 데이터** | 50건 매핑 결과에 대해 채용 전문가 5명의 적합도 평가 (1~5점) |
| **성공 기준** | GraphRAG의 평균 적합도 점수가 Vector-only 대비 +0.5점 이상 (p < 0.05) |
| **통계 검정** | Paired t-test (GraphRAG vs Vector) + 효과 크기(Cohen's d) 검증 |

---

## 2. Vector Baseline 구성

### 2.1 기술 스택

| 항목 | 내용 |
|---|---|
| **임베딩 모델** | `text-multilingual-embedding-002` (Vertex AI) — GCP 네이티브, 다국어 지원, 1536차원 |
| **입력 방식** | JD 전문 / 이력서 전문 각각 단일 임베딩 (구조화 분할 없음, 전체 텍스트 그대로 사용) |
| **유사도 측도** | cosine similarity |
| **검색 방식** | Top-K=10, reranking 없이 cosine similarity 순위로 산출 |
| **벡터 인덱스** | Vertex AI Vector Search (ScaNN 기반 ANN) |
| **처리량** | 동기 처리 (50건 × 후보풀~500명 = ~25k 쿼리, ~2시간) |

### 2.2 Vector Baseline 구현

```python
def vector_baseline_search(jd_text: str, candidate_resumes: List[Resume], top_k: int = 10) -> List[Dict]:
    """
    단순 임베딩 유사도 기반 매핑. 구조화 피처 없이 JD↔이력서 전체 텍스트를 직접 비교.

    핵심 로직:
    1. JD 전문 → text-multilingual-embedding-002 임베딩 (정규화)
    2. 후보 이력서 전문 → 동일 모델 임베딩 (배치 처리)
    3. cosine similarity 계산 → Top-K 정렬
    4. 반환: [{"candidate_id": str, "score": float, "rank": int}, ...]

    구현 시 별도 스크립트로 작성.
    """
    pass
```

### 2.3 데이터 흐름

```
[JD 50건] ──→ 임베딩 [1536d] ────┐
                                 ├─→ Vector Search (ANN) ──→ Top-10 후보
[후보 ~500명] ──→ 임베딩 배치 [1536d] ──┘
                    ↓
            cosine similarity 계산
                    ↓
            Top-5 후보 (50건 × 5 = 250건)
```

---

## 3. 통제 변수표

실험의 신뢰성을 위해 다음 변수들을 **동일하게 통제**한다.

| 통제 변수 | GraphRAG (A) | Vector Baseline (B) | Vector+Rerank (B') | 동일 여부 |
|---|---|---|---|---|
| **입력 데이터 (JD)** | 동일 50건 | 동일 50건 | 동일 50건 | ✓ |
| **입력 데이터 (이력서)** | 동일 후보 풀 (~500명) | 동일 후보 풀 | 동일 후보 풀 | ✓ |
| **전처리 (텍스트 정제)** | 동일 파이프라인 (정규화, 토큰화) | 동일 파이프라인 | 동일 파이프라인 | ✓ |
| **평가자** | 채용 전문가 5명 | 동일 5명 | 동일 5명 | ✓ |
| **평가 기준** | 1~5점 적합도 (역할, 성장단계, 도메인) | 동일 기준 | 동일 기준 | ✓ |
| **블라인드 처리** | 출처 비공개 | 출처 비공개 | 출처 비공개 | ✓ |
| **Top-K 결과물 비교** | Top-5 추출 | Top-5 추출 | Top-5 추출 | ✓ |

**변수 불일치 기록:**
- GraphRAG(A)는 Neo4j 그래프 탐색 시간 포함 (~1초/건)
- Vector(B)는 ANN 벡터 검색만 (~50ms/건)
- B'의 LLM Reranking 추가 시간은 별도 로깅

---

## 4. 실험 절차

### 4.1 전체 워크플로우

```
┌──────────────────────────────────────────────────────────────────┐
│                         실험 절차                                  │
└──────────────────────────────────────────────────────────────────┘

[Step 1] v1 파일럿 완료 (50건 매핑)
    입력: CompanyContext + CandidateContext + MappingFeatures 5개 피처
    처리: GraphRAG(Neo4j) 기반 매핑
    출력: GraphRAG Top-5 (A)
    시간: ~50초 (50건 × ~1초)

[Step 2] Vector Baseline 실행 (동일 50건)
    입력: JD 전문 + 이력서 전문 (구조화 없음)
    처리: 임베딩 + cosine similarity + ANN
    출력: Vector Top-5 (B)
    시간: ~2초 (배치 처리)

[Step 3] (선택) Vector + LLM Reranking (동일 50건)
    입력: Vector Top-10 결과 + Gemini 2.0 Flash
    처리: LLM이 Top-10을 재순위화
    출력: Vector+Rerank Top-5 (B')
    시간: ~3분 (50건 × ~3초, 동시 처리 가능)

[Step 4] 결과 셔플 및 블라인드 처리
    작업: A/B/(B') 결과를 무작위 순서로 섞기
    마킹: 데이터 소스 제거, ID만 노출
    검증: 평가자 간 의도하지 않은 편향 확인

[Step 5] 전문가 5명의 blind 평가 (병렬)
    각 평가자가:
      - 250건 (50건 × 5 Top-K) 을 1~5점으로 평가
      - 평가 기준: 역할 적합성, 성장 단계 경험, 도메인 적합성
      - 평균 소요 시간: 8시간 (건당 ~2분)

[Step 6] 통계 검정 (사후 분석)
    기법:
      - Paired t-test (GraphRAG A vs Vector B)
      - p < 0.05 유의도 기준
      - Cohen's d 효과 크기 계산
      - Krippendorff's alpha (평가자 간 일치도)

[Step 7] 피처별 기여도 분석
    작업:
      - MappingFeatures 5개 중 활성 피처 비율 vs 평가 점수 상관
      - GraphRAG 유리 사례 / 불리 사례 분석
      - 도메인 / 산업 / 경력 수준 별 성능 차이 검토
```

### 4.2 Step별 상세

**Step 1: GraphRAG 매핑 (기존 v1 파일럿 결과 재사용)**

```python
def graphrag_mapping(company_context: CompanyContext,
                     candidate_pool: List[CandidateContext],
                     mapping_features: List[MappingFeature]) -> List[Mapping]:
    """
    GraphRAG 기반 매핑 (v1 파일럿 프로세스).

    - Neo4j 그래프 탐색
    - 5개 MappingFeatures 활성화 (03_mapping_features.md 기준):
      1. stage_match (F1) — 성장 단계 경험 매칭
      2. vacancy_fit (F2) — 포지션 유형 적합도
      3. domain_fit (F3) — 도메인 적합도
      4. culture_fit (F4) — 문화/운영 방식 정렬
      5. role_fit (F5) — 역할 적합도

    - 반환: Top-5 후보 (rank 1~5)
    """
    # ... v1 파일럿 코드 활용
    pass
```

**Step 2: Vector Baseline 실행**

```python
def vector_baseline_evaluation(jd_50: List[str],
                               candidate_resumes_500: List[Resume]) -> Dict[str, List[Dict]]:
    """
    모든 50건 JD × 500명 후보에 대해 Vector 매핑 수행.

    핵심 로직:
    1. 500명 후보 이력서 일괄 임베딩 (batch_size=32)
    2. 각 JD 임베딩 → 전체 후보와 cosine similarity 계산
    3. 점수 정규화 (0~1, min-max) → Top-10 추출
    4. 반환: {jd_id: [{"candidate_id": str, "score": float, "rank": int}, ...]}

    구현 시 별도 스크립트로 작성.
    """
    pass
```

**Step 3: Vector + LLM Reranking (선택)**

```python
def vector_llm_rerank_evaluation(vector_results: Dict[str, List[Dict]],
                                  jd_50: List[str],
                                  candidate_resumes: Dict[str, Resume],
                                  top_k_final: int = 5) -> Dict[str, List[Dict]]:
    """
    Vector Top-10 결과를 Gemini 2.0 Flash로 재순위화.

    핵심 로직:
    1. 각 JD의 Vector Top-10 후보 정보 포맷팅 (이름, 경력, 역할, Vector 점수)
    2. LLM 프롬프트: 채용 매칭 전문가 페르소나 + 평가 기준 4가지
       (역할 적합성, 성장 단계 경험, 도메인 적합성, 문화적 적합성)
    3. Gemini 2.0 Flash 호출 (temperature=0.2)
    4. 응답 파싱: "N. [후보명]: 적합도 X점" 형식 → candidate_id 매칭
    5. 반환: {jd_id: [Top-5 재순위화 결과]}

    구현 시 별도 스크립트로 작성.
    """
    pass
```

**Step 4: 블라인드 처리**

```python
def prepare_blind_evaluation(graphrag_results: Dict,
                             vector_results: Dict,
                             reranked_results: Optional[Dict] = None) -> Tuple[List[Dict], List[Dict]]:
    """
    평가용 데이터셋 준비 (블라인드 처리).

    핵심 로직:
    1. A/B/(B') 결과를 하나의 리스트로 통합 (_source 내부 추적용으로만 유지)
    2. 무작위 셔플 → 평가 ID 부여 (eval_000001~)
    3. 평가자 노출 필드: eval_id, jd_id, candidate_id만 (rank, method 제거)
    4. 반환: (evaluation_dataset, all_results_with_source)

    구현 시 별도 스크립트로 작성.
    """
    pass
```

**Step 5: 전문가 평가**

```python
def expert_evaluation_session(evaluation_dataset: List[Dict],
                               candidate_resumes: Dict[str, Resume],
                               jd_texts: Dict[str, str],
                               evaluator_id: str) -> List[Dict]:
    """
    한 명의 평가자가 수행할 평가 작업 (250건, ~8시간).

    평가 기준 (각 1~5점):
    1. role_fit_score — 역할 적합성
    2. stage_fit_score — 성장 단계 경험 일치도
    3. domain_fit_score — 도메인 적합성
    → overall_score = 3개 평균

    출력 스키마: {eval_id, evaluator_id, jd_id, candidate_id,
                  role_fit_score, stage_fit_score, domain_fit_score,
                  overall_score, reasoning, timestamp}

    구현 시 평가 UI/폼 기반으로 별도 스크립트 작성.
    """
    pass
```

**Step 6: 통계 검정**

```python
def statistical_analysis(evaluation_results: List[Dict],
                         blind_metadata: List[Dict]) -> Dict:
    """
    수집된 평가 데이터에 대한 사후 분석.

    핵심 로직:
    1. 평가 결과를 Method별(A/B/B') 그룹화 (blind_metadata로 source 추적)
    2. Paired t-test: A vs B, A vs B', B vs B' (scipy.stats.ttest_rel)
    3. Cohen's d 효과 크기: pooled_std 기반 계산
    4. Krippendorff's alpha: 평가자 5명 간 일치도
    5. 95% 신뢰 구간 계산

    반환 스키마: {paired_t_test, effect_size, inter_rater_agreement,
                  confidence_intervals, descriptive_stats}

    구현 시 별도 분석 스크립트로 작성.
    """
    pass
```

**Step 7: 피처별 기여도 분석**

```python
def feature_contribution_analysis(graphrag_results: Dict,
                                   evaluation_results: Dict,
                                   feature_activation_log: Dict) -> Dict:
    """
    MappingFeatures 5개의 활성화 여부와 평가 점수의 상관관계 분석.

    5개 피처 (03_mapping_features.md 기준):
    1. stage_match (F1)
    2. vacancy_fit (F2)
    3. domain_fit (F3)
    4. culture_fit (F4)
    5. role_fit (F5)

    분석:
    - 각 피처의 활성 비율 (%)
    - 활성 vs 비활성 매핑의 평가 점수 차이
    - Pearson 상관계수 (활성 피처 수 vs 평가 점수)

    핵심 로직:
    1. 5개 피처별 활성화 통계 (active_rate, avg_score_active/inactive)
    2. 유리 케이스 (overall > 4.0) / 불리 케이스 (overall < 2.5) 추출
    3. Pearson 상관: 활성 피처 수 vs 평가 점수

    반환 스키마: {feature_stats, correlation, case_analysis}

    구현 시 별도 분석 스크립트로 작성.
    """
    pass
```

---

## 5. 선택적 추가 실험 (B': Vector + LLM Reranking)

GraphRAG(A)와의 공정한 비교를 위해, Vector + LLM Reranking 조합(B')도 선택적으로 테스트한다.

### 5.1 설계

| 항목 | 내용 |
|---|---|
| **방법** | Vector Top-K=10 결과를 Gemini 2.0 Flash로 재순위화 |
| **목적** | Vector의 한계가 임베딩 자체의 문제인지, 구조화된 피처(GraphRAG)의 기여인지 분리 |
| **모델** | Gemini 2.0 Flash (저지연, 저비용) |
| **프롬프트** | 채용 매칭 전문가 페르소나 + 평가 기준 3가지 |
| **성공 기준** | (A) > (B') > (B)이면 GraphRAG의 구조적 우위 확인 / (B') >= (A)이면 구조화 없이 LLM reranking으로 충분 |

### 5.2 상세 구현

```python
def vector_llm_rerank(jd_text: str, candidate_resumes: List[Resume],
                      top_k_vector: int = 10, final_k: int = 5) -> List[Dict]:
    """
    Vector Top-K 결과를 LLM으로 재순위화.

    핵심 로직:
    1. vector_baseline_search()로 Top-10 추출
    2. 후보 프로필 포맷팅 (이름, 경력, 최근 역할, 핵심 기술, Vector 점수)
    3. Gemini 2.0 Flash 프롬프트 (채용 컨설턴트 페르소나, temperature=0.2)
       평가 기준: 역할 적합성, 성장 단계 경험, 도메인 적합성
    4. 응답 파싱: "N. [이름] (적합도: X점)" 정규식 매칭
    5. 반환: [{"candidate_id", "score", "rank", "method": "vector_llm_rerank"}, ...]

    구현 시 별도 스크립트로 작성.
    """
    pass
```

---

## 6. 의사결정 트리

실험 결과에 따라 v2 이후의 확장 범위를 결정한다.

```
실험 결과 분석:

┌─────────────────────────────────────────────────────────────────┐
│                    결과 분기 시나리오                            │
└─────────────────────────────────────────────────────────────────┘

기준:
- Mean(A) = GraphRAG 평균 점수
- Mean(B) = Vector Baseline 평균 점수
- Mean(B') = Vector + LLM Reranking 평균 점수
- Δ = Mean(A) - Mean(B)
- p < 0.05 유의 기준

═══════════════════════════════════════════════════════════════════

Case 1: (A) >> (B) & (A) > (B') & Δ >= +0.5 & p < 0.05
        → GraphRAG 구조적 우위 명확 확인

        분석: 그래프 기반 피처(MappingFeatures 5개)가
              단순 임베딩이나 LLM reranking보다 우수

        의사결정:
        ✓ v2: Company 간 관계(A5) 추가 개발 (ROI 양수)
        ✓ v2: tension_alignment 피처 도입
        ✓ Graph 인프라 투자 정당화
        ✓ v2 스코프 확대 (Feature Rich Model 방향)

───────────────────────────────────────────────────────────────────

Case 2: (A) > (B) & (B') >= (A) & Δ >= +0.3 & p < 0.1
        → LLM Reranking으로도 GraphRAG 수준 달성 가능

        분석: 구조화 없이 LLM의 추론 능력만으로 충분할 수 있음
              그래프의 추가 가치가 한계적

        의사결정:
        ✓ v2: GraphRAG 유지하되 LLM reranking 레이어 추가 (Hybrid)
        ✗ Graph 확장 축소 (비용 대비 효과 낮음)
        ✓ LLM 모델 개선에 집중 (Gemini, Claude 등)
        ✓ v2 스코프: 경량화 (Simple Features)

───────────────────────────────────────────────────────────────────

Case 3: (A) ≈ (B) & Δ < +0.3 & p > 0.1
        → GraphRAG의 추가 가치 불분명

        분석: 구조화된 Graph의 기여도가 통계적으로 유의하지 않음
              임베딩만으로 충분할 가능성 높음

        의사결정:
        ✓ 피처별 ablation 분석 (5개 중 어떤 피처가 작동하지 않는가?)
        ✓ v2: 기여도 높은 피처만 유지 (2~3개)
        ✓ 나머지 피처는 제거 (기술 부채 감소)
        ✓ v2 스코프: Hybrid 경량화 (Graph + Vector)

───────────────────────────────────────────────────────────────────

Case 4: (B) > (A) & (B') > (A)
        → GraphRAG 설계 근본적 문제

        분석: 그래프 기반 피처가 오히려 노이즈 추가
              데이터 품질? 피처 엔지니어링? Graph 구조?

        의사결정:
        ✓ 근본 원인 분석:
          - MappingFeatures 5개 재검토
          - Neo4j 쿼리 성능 / 결과 정확도 검증
          - 엣지 정보 품질 평가

        ✓ v2 전략 변경:
          - Vector-first 모델로 아키텍처 재설계
          - Graph는 보조 (설명가능성, 감사용)로 축소
          - 간단한 BM25 + Vector 조합으로 start

        ✗ v2에서 Company 간 관계(A5) 추가 금지
        ✓ v1.x: GraphRAG 디버깅 + 재검증 (2~3주)

═══════════════════════════════════════════════════════════════════
```

### 6.1 분기별 상세 의사결정 프로토콜

```yaml
Case 1: GraphRAG 우위 확인 (추천)
  결과:
    Mean(A): 4.1점
    Mean(B): 3.4점
    Mean(B'): 3.6점
    Δ: +0.7점 (p=0.008)
    Cohen's d: 0.65 (중간 효과)

  의사결정:
    - v2 스코프: Graph Expansion (Company 관계, tension_alignment)
    - 투자 규모: GraphRAG 인프라 +40%
    - Timeline: v2 개발 6개월
    - 성공 지표: v2에서도 Vector 대비 +0.5점 이상 유지

Case 2: Hybrid 모델 (Vector + LLM)
  결과:
    Mean(A): 3.7점
    Mean(B): 3.5점
    Mean(B'): 3.8점
    Δ: +0.2점 (p=0.15, 유의 아님)

  의사결정:
    - v2 스코프: LLM Reranking 레이어 추가 (Graph 유지)
    - 투자 규모: GraphRAG 유지, LLM API 비용 +30%
    - Timeline: v2 개발 3개월
    - 성공 지표: Vector+LLM으로 충분, Graph 확장 불필요

Case 3: GraphRAG 재검토 필요
  결과:
    Mean(A): 3.5점
    Mean(B): 3.4점
    Δ: +0.1점 (p=0.42, 유의 아님)

  의사결정:
    - v1.x 패치: MappingFeatures 일부 제거 or 가중치 조정
    - Ablation 분석: 각 피처의 기여도 정량화
    - v2 스코프: Vector + 최소 GraphRAG (기여도 높은 2~3개만)
    - 투자 규모: GraphRAG 축소 (-50%)
    - Timeline: v2 개발 2개월

Case 4: 근본 설계 재검토 (높은 위험)
  결과:
    Mean(A): 3.0점
    Mean(B): 3.5점
    Mean(B'): 3.6점
    Δ: -0.5점 (GraphRAG가 더 낮음!)

  의사결정:
    - v1.x 긴급 검토: 2~3주 집중 분석
      * Neo4j 쿼리 검증 (노이즈 확인)
      * Edge 정보 품질 평가
      * MappingFeatures 엔지니어링 재검토

    - 결과에 따라:
      A) 문제 발견 & 해결 → v2는 GraphRAG 개선 모드
      B) 문제 없음 → v2 아키텍처 Vector-first로 전환

    - 투자 규모: GraphRAG 심화 분석 (1인월 5명)
    - Timeline: v2 출시 1개월 연기
```

---

## 7. 평가 지표 상세 정의

| 지표 | 정의 | 계산 방법 | 해석 |
|---|---|---|---|
| **Human Eval Score** | 전문가의 주관적 적합도 평가 | 5명 평가자의 1~5점 평균 | 3.5점 이상: 양호, 4.0점 이상: 우수 |
| **Precision@5** | Top-5 중 적합한 후보 비율 | (적합 판정 >= 3점인 후보 수) / 5 | 60% 이상: 양호, 80% 이상: 우수 |
| **Recall@5** | 전체 적합 후보 중 Top-5에 포함된 비율 | (Top-5 내 적합 후보) / (전체 적합 후보 수) | 50% 이상: 양호, 70% 이상: 우수 |
| **NDCG@5** | 순위 품질 (이상적 순위 대비 실제 순위) | DCG@5 / IDCG@5 | 0.7 이상: 양호, 0.85 이상: 우수 |
| **Mean Reciprocal Rank (MRR)** | 첫 적합 후보의 평균 역순위 | 1 / Σ(첫 적합 후보 순위) / n | 0.5 이상: 양호, 0.7 이상: 우수 |
| **Inter-rater Agreement** | 평가자 간 일치도 | Krippendorff's alpha | 0.6 이상: 양호, 0.8 이상: 우수 |
| **Effect Size (Cohen's d)** | 그룹 간 차이의 크기 | (Mean(A) - Mean(B)) / Pooled_SD | <0.5: 작음, 0.5~0.8: 중간, >0.8: 큼 |

---

## 8. 로드맵

| 단계 | 시기 | 활동 | 산출물 | 담당 |
|---|---|---|---|---|
| **준비** | v1 파일럿 중 (2026-02월) | • Vector Baseline 인덱스 구축 (Vertex AI Vector Search)<br>• 평가 프레임워크 설계 (평가 기준, 보상 체계)<br>• 평가자 5명 모집 및 교육<br>• 블라인드 평가 플랫폼 개발 | • 평가 가이드라인 문서<br>• Vector Baseline 인덱스 (500명 후보 임베딩)<br>• 평가 UI 프로토타입 | ML Platform PM, Evaluation Specialist |
| **실험** | v1 파일럿 완료 후 (2026-03월 중순, ~1주) | • Step 1~3: A/B/(B') 매핑 수행 (병렬, 1~2일)<br>• Step 4: 결과 셔플 및 블라인드 처리 (1일)<br>• Step 5: 채용 전문가 5명의 평가 (병렬, 5~8일)<br>• 데이터 수집 및 정제 | • 원시 평가 데이터 (250건 × 5명 = 1,250건)<br>• 평가자 의견 기록<br>• 메타 데이터 (소요 시간, 일치도) | Evaluation Team (5명) |
| **분석** | 실험 완료 후 (2026-03월 말, ~1주) | • Step 6: 통계 검정 (Paired t-test, Cohen's d)<br>• Step 7: 피처별 기여도 분석 (Ablation)<br>• Case 분석 (유리 케이스 / 불리 케이스)<br>• 최종 보고서 작성 | • 실험 보고서 (20~30페이지)<br>• 통계 분석 결과 (표, 그래프)<br>• 피처별 기여도 분석<br>• Executive Summary | Data Scientist, Analytics Engineer |
| **의사결정** | 분석 완료 후 (2026-04월 초) | • 결과 리뷰 (Steering Committee)<br>• v2 스코프 결정<br>• 투자 우선순위 조정<br>• v2 개발 계획 수립 | • v2 스코프 문서<br>• 의사결정 기록<br>• v2 Project Charter | Product Director, Engineering Lead |

---

## 9. 부록: 평가 기준 상세

### 9.1 역할 적합성 (Role Fit) 평가 체크리스트

```
5점 (매우 적합)
  □ 공고의 level(senior/mid/junior)과 경력이 정확히 일치
  □ 핵심 기술 스택 100% 일치
  □ 최근 경험이 공고의 역할과 동일
  □ 책임 범위(scope) 완벽히 일치

4점 (적합)
  □ Level이 거의 일치 (±1 level)
  □ 핵심 기술 70% 이상 일치
  □ 관련 역할 경험 있음
  □ 책임 범위가 비슷

3점 (보통)
  □ Level이 비슷하지만 정확히 일치하지 않음
  □ 핵심 기술 50% 이상 일치
  □ 관련 역할의 부분적 경험
  □ 책임 범위가 일부 다름

2점 (부적합)
  □ Level이 상당히 낮거나 높음
  □ 핵심 기술 30% 이상 일치
  □ 간접적인 경험만 있음

1점 (매우 부적합)
  □ Level이 크게 다름
  □ 핵심 기술 거의 없음
  □ 무관한 경험
```

### 9.2 성장 단계 경험 (Stage Fit) 평가 체크리스트

```
회사의 성장 단계에 따른 필요 경험:

Seed/Series A (0~20명):
  5점: 스타트업 여러 곳에서 초기 단계 경험, 빠른 의사결정 경험
  4점: 스타트업 경험, 작은 팀에서 다역할
  3점: 스타트업 또는 스케일업에서 부분 경험
  2점: 대기업만의 경험, 느린 의사결정 문화
  1점: 스타트업 경험 없음

Series B/C (20~100명):
  5점: 스케일업 여러 곳에서 조직 확대 경험
  4점: 스케일업에서 핵심 역할
  3점: 스타트업 또는 스케일업 경험
  2점: 대기업 경험, 스케일업 부분 경험
  1점: 대기업만의 경험

Growth/Late Stage (100명+):
  5점: 대기업 또는 엔터프라이즈에서 대규모 프로젝트 리드 경험
  4점: 대기업에서 중요한 역할 수행
  3점: 대기업 또는 스케일업 경험
  2점: 주로 작은 조직 경험
  1점: 대규모 조직 경험 부족
```

### 9.3 도메인 적합성 (Domain Fit) 평가 체크리스트

```
5점 (매우 적합)
  □ 동일 산업에서 3년 이상 경험
  □ 해당 산업의 비즈니스 모델 완벽 이해
  □ 핵심 기술 스택에 대한 깊은 이해
  □ 관련 도메인 문제 해결 경험

4점 (적합)
  □ 동일 또는 유사 산업에서 1~3년 경험
  □ 비즈니스 모델에 대한 기본 이해
  □ 관련 기술 스택 경험
  □ 도메인 문제 인식

3점 (보통)
  □ 유사 산업에서 부분 경험
  □ 비즈니스 모델에 대한 기초 이해
  □ 관련 기술 공부 의지
  □ 배우려는 태도

2점 (부적합)
  □ 다른 산업 경험만 있음
  □ 비즈니스 모델 이해 부족
  □ 관련 기술 경험 없음

1점 (매우 부적합)
  □ 도메인 관련 경험 전무
  □ 산업 이해 불가능 수준
```

---

## 10. 실험 데이터 예시

> **가상 예시 데이터** — 아래 수치는 실험 수행 전 예상 구조를 보여주기 위한 가상 데이터입니다.
> 실제 실험 결과가 아니며, 실험 완료 후 실제 데이터로 대체됩니다.

### 10.1 평가 결과 샘플

```json
{
  "experiment_metadata": {
    "start_date": "2026-03-15",
    "end_date": "2026-03-22",
    "total_evaluations": 250,
    "evaluators": 5,
    "jd_count": 50,
    "candidate_pool_size": 500,
    "blind_processed": true,
    "inter_rater_agreement": 0.72
  },
  "aggregate_scores": {
    "method_A_graphrag": {
      "mean": 3.82,
      "std": 0.94,
      "median": 4.0,
      "min": 1.5,
      "max": 5.0
    },
    "method_B_vector": {
      "mean": 3.34,
      "std": 1.12,
      "median": 3.0,
      "min": 1.0,
      "max": 5.0
    },
    "method_B_prime_vector_llm": {
      "mean": 3.58,
      "std": 1.05,
      "median": 3.5,
      "min": 1.0,
      "max": 5.0
    }
  },
  "statistical_tests": {
    "paired_t_test_a_vs_b": {
      "t_statistic": 2.84,
      "p_value": 0.0062,
      "significant": true,
      "confidence_interval_95": [0.14, 0.82]
    },
    "paired_t_test_a_vs_b_prime": {
      "t_statistic": 1.52,
      "p_value": 0.1364,
      "significant": false,
      "confidence_interval_95": [-0.08, 0.52]
    },
    "effect_size_a_vs_b": {
      "cohens_d": 0.48,
      "interpretation": "small to medium"
    }
  },
  "metric_breakdown": {
    "method_A": {
      "precision_at_5": 0.78,
      "recall_at_5": 0.65,
      "ndcg_at_5": 0.82,
      "mrr": 0.72
    },
    "method_B": {
      "precision_at_5": 0.62,
      "recall_at_5": 0.51,
      "ndcg_at_5": 0.68,
      "mrr": 0.58
    }
  }
}
```

### 10.2 피처 기여도 분석 샘플

```json
{
  "feature_contribution_analysis": {
    "stage_match": {
      "active_rate": 0.68,
      "avg_score_when_active": 4.05,
      "avg_score_when_inactive": 3.42,
      "difference": 0.63,
      "correlation_with_overall": 0.54
    },
    "vacancy_fit": {
      "active_rate": 0.82,
      "avg_score_when_active": 4.12,
      "avg_score_when_inactive": 2.95,
      "difference": 1.17,
      "correlation_with_overall": 0.68
    },
    "domain_fit": {
      "active_rate": 0.56,
      "avg_score_when_active": 3.98,
      "avg_score_when_inactive": 3.58,
      "difference": 0.40,
      "correlation_with_overall": 0.32
    },
    "role_fit": {
      "active_rate": 0.71,
      "avg_score_when_active": 3.94,
      "avg_score_when_inactive": 3.51,
      "difference": 0.43,
      "correlation_with_overall": 0.38
    },
    "culture_fit": {
      "active_rate": 0.42,
      "avg_score_when_active": 4.08,
      "avg_score_when_inactive": 3.60,
      "difference": 0.48,
      "correlation_with_overall": 0.41
    }
  },
  "feature_importance_ranking": [
    {"feature": "vacancy_fit", "importance": 0.68},
    {"feature": "stage_match", "importance": 0.54},
    {"feature": "culture_fit", "importance": 0.41},
    {"feature": "role_fit", "importance": 0.38},
    {"feature": "domain_fit", "importance": 0.32}
  ]
}
```

---

## 11. 결론 및 다음 단계

이 실험 계획은 **GraphRAG의 실질적 ROI를 정량적으로 검증**하기 위해 설계되었다.

**핵심 원칙:**
1. **공정한 비교**: A/B/(B') 세 가지 방법을 동일한 데이터와 평가 기준으로 비교
2. **통제된 변수**: 입력 데이터, 평가자, 평가 기준 모두 동일
3. **통계적 유의성**: p < 0.05 기준으로 유의미한 차이 검증
4. **명확한 의사결정 기준**: 결과에 따른 v2 스코프 결정 기준 사전 정의

**실험 출력물:**
- GraphRAG vs Vector 성능 비교 보고서
- MappingFeatures별 기여도 분석
- v2 확장 방향에 대한 데이터 기반 의사결정

**일정:**
- 준비: 2026-02월 (v1 파일럿 병행)
- 실험: 2026-03월 중순 (1~2주)
- 분석: 2026-03월 말 (1주)
- 의사결정: 2026-04월 초

이 결과를 바탕으로 v2 설계의 우선순위와 투자 규모가 결정된다.

