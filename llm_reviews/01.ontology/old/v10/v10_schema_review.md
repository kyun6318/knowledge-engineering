# V10 Ontology Schema 설계 및 실현 가능성 리뷰

**작성일**: 2026-03-08
**대상 경로**: `01.ontology/schema/v10/` 내 7개 스키마 문서

---

## 1. 종합 평가 요약 (Executive Summary)

v10 온톨로지 스키마 설계는 매우 체계적이며, 현실적인 제약 상황(LLM의 환각, 결측치 등)을 고려한 **우아한 성능 저하(Graceful Degradation)** 원칙과 **증거 기반(Evidence-first)** 원칙이 매우 높은 수준으로 적용되어 있습니다. 특히 신뢰도(Confidence) 티어링 시스템, 평가 가설 검증 전략(A/B Testing), 한정된 크롤링 전략은 실현 가능한(Feasible) 범위 안에서 고도화되었습니다. 

하지만, V1 시스템 수준으로서는 데이터 적재 및 처리 과정에서 **오버엔지니어링(과한 설계) 요소**가 일부 존재하며, 실무 매칭 품질을 좌우하는 **스킬/도메인 용어 정규화(Normalization)** 부분에서 누락이 발견됩니다.

## 2. 설계의 타당성 (Design Validity) - 주요 강점

*   **구조적 대칭성과 정합성**: `CompanyContext`와 `CandidateContext`가 Mapping Features(5개 축)를 중심으로 대칭적으로 매핑되도록 설계된 것은 탁월합니다. 직무 단위(Vacancy)와 후보자의 커리어 단위(Chapter)로 정밀하게 연결되는 구조입니다.
*   **신뢰도(Confidence) 캘리브레이션 시스템**: 원천 데이터의 속성(T1~T7)에 맞춰 신뢰도 상한선(Ceiling)을 설정하고, 교차 검증 여부에 따라 신뢰도를 보정하는 규칙은 환각 방지 및 LLM의 한계를 제어할 수 있는 최고의 방안입니다. 데이터가 불충분할 경우 억지로 값을 채우지 않고 Null로 두어 매핑 점수에 불이익(Neutral/Negative)을 주는 방식은 매우 현실적입니다.
*   **견고한 단계별 실험 및 평가 프레임워크**: `05_evaluation_strategy.md`에 정의된 통계적 검정력(Power Analysis), Cohen's d 검증, Krippendorff's alpha를 활용한 평가자 일치도 확보 등은 GraphRAG 도입의 당위성(ROI)을 증명하기 위한 완벽에 가까운 프레임워크입니다.
*   **효율을 고려한 크롤링 파이프라인**: 10개 페이지 수집 제한, 필수 탐색(우선순위 P1~P3 식별), 텍스트 해시 기반 변경 감지(A/B) 등의 정책은 Cloud Run 타임아웃 방지 및 데이터 수집 비용 최적화 측면에서 현명한 결정입니다.

## 3. 실현 가능성 검토 (Feasibility)

*   **데이터 파이프라인**: 전반적으로 실현성이 매우 높습니다. GCP 인프라(Vertex AI, BigQuery, Playwright 기반 Cloud Run)를 적극 고려하여 구성되었기 때문에 아키텍처 연동에는 큰 무리가 없습니다.
*   **레이턴시 및 비용**: 크롤링에 10페이지 * Gemini 2.0 Flash 분석이 수반되는데, 모두 비동기 배치 작업으로 상정하였기에 매칭 실시간성에는 영향을 주지 않습니다. Vector Index 통합(Vertex AI Vector Search 활용) 역시 확장성을 충분히 고려한 설계입니다.

## 4. 과도한 설계 요소 (Over-engineering Warning)

*   **Evidence Span 및 메타데이터의 과도한 중첩 구조**: 
    현재의 스키마 구조는 모든 Context 내 필드 속성에 `{value, confidence, evidence: [{source_id, span, extracted_at...}]}`의 심층 JSON 구조를 강제하고 있습니다. 이는 데이터 투명성(Explainability) 측면에서는 이상적이나, 문서 DB 및 Neo4j의 속성(Properties) 크기를 기하급수적으로 팽창시키고 Graph 쿼리문을 복잡하게 만들게 됩니다. 
    **👉 대안**: V1에서는 Graph 속성에 '추출된 값'과 '출처 배열(`source_ids`)' 정도의 메타데이터만 포함하고, 상세한 Evidence Span은 BigQuery Document 스토어 등에 역색인(Look-up)용으로만 남겨두는 형태로 Graph를 경량화하는 것을 권장합니다.
*   **2단계 뉴스 중복 제거 로직 구현 복잡도**: 
    뉴스 기사 클러스터링(06_crawling_strategy.md)에서 Jaccard Similarity 기반 핵심 엔티티 Overlap 대조를 2차로 진행하는 것은 상당히 복잡합니다. V1 단계에서는 제목/본문 벡터 기반 임베딩 코사인 유사도 검색만으로도 충분한 중복 탐지 능력을 확보할 수 있으며, 이 편이 유지보수에 훨씬 유리합니다.
*   **뉴스 기사로부터의 미세한 구조적 긴장(Structural Tension) 추출**:
    언론 기사는 본질적으로 내부 갈등이나 기술 부채(tech_debt_vs_features 등)를 명시적으로 서술하지 않습니다. N4 조직/경영 변화 기사 프롬프트를 통해 이런 은밀한 Tension Type을 도출해내려는 시도는 LLM의 '추측성 답변 비중'을 오히려 증가시킬 가능성이 높습니다. Tension은 M&A 통계, 재무 실적 등의 지표에서만 Hard-rule로 제한적 추론하는 편이 안전합니다.

## 5. 누락/부족한 요소 (Missing Pieces & Gaps)

*   **엔티티/스킬 정규화 파이프라인 (Normalization/Canonical Mapping)의 부재**:
    `04_graph_schema.md`에 따르면 `Skill` 노드는 별도의 엔티티로 존재합니다. 이력서에 표기된 `NodeJS`, `Node.js`, `노드제이에스`는 모두 개별 노드로 분화될 우려가 높습니다. 문자열이 조금만 달라도 관계 매핑이 끊어지기 때문에, 크롤링 및 파싱 파이프라인 중간에 **동의어 사전(Synonym Dictionary) 기반 표준 스킬 도메인 맵핑 단계**가 반드시 추가되어야 합니다.
*   **"Supernode" (초거대 노드) 폭발 잠재 리스크**: 
    Graph DB (Neo4j) 상에서 `Python`, `Java`, `Communication`과 같은 대중적인 범용 스킬이나 도메인 노드는 거의 모든 Candidate Chapter/Vacancy와 연결됩니다. 이는 쿼리 시 방대한 Cartesian Product(카테시안 곱) 연산을 유발하여 Neo4j 성능을 크게 저하시킬 수 있습니다.
*   **뉴스 크롤링 시 Paywall(유료결제벽) 회피/예외 처리**: 
    비즈니스/IT 전문지의 핵심 팩트 기사는 종종 Paywall에 막혀 수집이 불가능한 경우가 많습니다. 본문 추출 시 Paywall 안내 텍스트가 섞여 들어오면 LLM 추출 품질이 저해되므로 해당 노이즈(예: 로그인, 정기구독) 필터링 처리가 필요해 보입니다.

## 6. 다음 단계 권고사항 (Recommendations)

1.  **Denormalized Graph (역정규화 그래프) 모델링 병행**: 공통된/다빈도로 쓰이는 스킬 노드 분해 전략 대신, 초기에는 `Candidate`의 `Chapter` 노드 내 속성 배열(`skills: ["python", "aws"]`)로 임베딩하여, 쿼리 내 Vector Search에 의존하는 'Vector-first, Graph-support' 형태를 벤치파일럿에 포함시키는 것을 고려해보십시오.
2.  **동의어 DB 통합 관리**: 텍스트 추출 직후, BigQuery로 가기 이전에 `Synonym Mapper Step`을 정의하여 `Skill` 및 `Job Role` 명칭에 대한 정규화 레이어를 반드시 추가합니다.
3.  **Graph 간소화 (Evidence)**: 그래프 내 노드 생성 시, 증거(Evidence) 리스트는 제외하여 순수 구조 탐색 최적화를 확보하는 구조로 아키텍처를 단순화할 것을 제안합니다.
