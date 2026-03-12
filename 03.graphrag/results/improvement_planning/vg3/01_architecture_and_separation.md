# 1. 아키텍처 개요 및 팀별 역할 분리 (VG3)

> **목적**: 시스템 로드가 가장 큰 "하드필터 속성 및 임베딩 추출" 단계를 Search & Filter (S&F) 아티팩트 처리팀으로 완전히 분리(Delegation)하여, **GraphRAG 팀은 지식 그래프 본연의 기능(`Chapter` 중심의 관계 매칭 및 네트워크 패턴 추론)에 100% 집중**할 수 있는 아키텍처 구조를 확보한다.

---

## 1.1. 시스템 역할 분리 원칙 (Separation of Concerns)

| 구분 | Search & Filter (S&F) 팀 | GraphRAG 팀 |
|---|----------------|-------------|
| **핵심 미션** | 대규모 비정형 데이터의 **구조화/정량화** 및 **1차 후보군 탐색(Recall)** | 정제된 Entity 간 **맥락 추론** 및 **최종 적합도 랭킹 산출(Precision)** |
| **담당 범위 요약** | • 이력서/JD 텍스트 파싱 (PDF, HWP 등)<br>• PII(개인정보) 마스킹 등 컴플라이언스 1차 방어<br>• `CandidateContext` 속성 기반 하드 필터 요소 정제<br>• Vertex AI를 활용한 텍스트 임베딩 모델링 | • `Person`, `Chapter`, 기업 `Organization` 등 핵심 노드/엣지 적재<br>• `[NEXT_CHAPTER]` 순차 망 구성 및 이직 패턴 역량 모델링<br>• 기업 스테이지(`stage_match`) 및 상황 신호 등 5-피처 매칭 컴포넌트 평가 |
| **제공 API 목표** | 정량적 스킬/연차 등의 조건 및 키워드 벡터 쿼리에 부합하는 **ID 리스트(Top 500~1,000)** 반환 (p95 < 500ms) | S&F가 건넨 ID Pool 내에서만 심층 그래프 Traversal 매칭을 수행해 **최종 Top 20** 추천 (p95 < 2s) |
| **기반 인프라**| BigQuery, Vector DB (Milvus/Pinecone 등 외부화), GCS | Neo4j Professional, Cloud Run |

---

## 1.2. 마이크로서비스 및 Polyglot 아키텍처 비전

* **Polyglot Persistence**: 각 계층의 워크로드 특성에 가장 부합하는 최상의 저장소를 활용.
  * *조회 및 검색 (Recall)*: 텍스트 임베딩 매칭 등은 전용 Vector DB 혹은 Elasticsearch 등의 검색 엔진 아키텍처 체류를 허용하여 초고속 서치를 달성한다. (특히 Person 노드가 1M을 넘어갈 경우 연산 분리를 위해 Vector를 Neo4j 외부로 독립).
  * *관계 분석 (Precision)*: 복잡도 높은 벤 다이어그램 수준의 교집합 확인이나, Chapter 간 연결(Graph Traversal)이 필요한 정밀 평가는 메모리에 최적화된 Neo4j 가 전담한다.
* **Loose Coupling (느슨한 결합)**: 
  * 두 팀의 아키텍처는 철저히 **Data Contract (JSON)와 Event 체인**으로만 결합한다. GraphRAG 시스템은 "이력서 텍스트 파일이 어떻게 파싱되었는지" 혹은 "PII 마스킹이 어떻게 수행되었는지"에 관여하지 않고, 전달된 JSON의 규격 무결성만 신뢰한다.
