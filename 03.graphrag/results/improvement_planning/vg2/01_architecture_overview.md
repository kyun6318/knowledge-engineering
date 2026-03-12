# 1. 아키텍처 개요 및 역할 분리 (vg2)

> **목적**: 시스템 로드가 가장 큰 "필터 속성 및 임베딩 추출" 단계를 Search & Filter (S&F) 아티팩트 처리팀으로 분리(Delegation)하여, **GraphRAG 팀은 지식 그래프 본연의 기능(관계 매칭 및 네트워크 패턴 분석)에 100% 집중**할 수 있는 아키텍처 구조를 확보한다.

---

## 1.1. 시스템 역할 분리 (Separation of Concerns)

| 구분 | S&F (Search & Filter) 팀 | GraphRAG 팀 |
|---|----------------|-------------|
| **핵심 역할** | 대규모 비정형 데이터 정형화 및 **Recall (1차 탐색)** | 정제된 엔티티 간 관계 패턴 추론 및 **Precision (정밀 랭킹)** |
| **주요 기능** | • PDF/DOCX/HWP 및 JD 파싱<br>• PII(개인정보) 필수 마스킹<br>• `CandidateContext` 속성 분리<br>• 텍스트 임베딩 생성(Vertex AI) | • S&F가 건네준 핵심 노드 구조체만 적재<br>• `[NEXT_CHAPTER]`, 기업 스테이지, 이직 패턴 등 분석<br>• 5-피처 매칭 컴포넌트 평가 로직 |
| **제공 API** | 특정 필터 및 자연어를 입력받아 부합하는 **ID 리스트(Top 500~1,000)** 반환 API | S&F가 건넨 ID Pool 내에서만 심층 그래프 매칭을 수행해 **최종 Top 20** 반환 API |
| **기반 인프라**| BigQuery, Vector DB (Milvus/Pinecone 등), GCS | Neo4j Professional, Cloud Run |

---

## 1.2. 마이크로서비스 및 Polyglot 비전

* **Polyglot Persistence**: 
  * 텍스트 처리나 벡터 임베딩이 많이 필요한 대용량 검색(Recall)은 전용 Vector DB나 Elasticsearch 기반 검색 엔진에서 높은 처리량을 달성한다.
  * 복잡도 높은 상호 관계 참조(Graph Traversal)가 필요한 Precision 단계는 메모리에 최적화된 Neo4j 가 전담한다.
* **Loose Coupling (느슨한 결합)**: 
  * 두 시스템은 철저히 API와 Event 체인으로 결합한다. GraphRAG 시스템은 "텍스트가 어떻게 벡터화되었는지" 또는 "PII가 어떻게 가려졌는지"를 전혀 알 필요가 없다.

---

## 1.3. 시스템 간 인터페이스 (Data Contract & Flow)

### A. 비동기 이벤트 기반 데이터 적재 파이프라인
* **구조**: `S&F 추출 ➔ GCS (JSON 적재) ➔ PubSub 이벤트 트리거 ➔ GraphRAG (자동 인지 후 Neo4j 적재)`
* **Data Contract 예시 (JSON)**:
  S&F 팀이 PII 마스킹 완료 후, 임베딩을 제외한 필수 필드 위주로 GraphRAG 쪽에 전달하는 규격.

```json
{
  "person_id": "P_000001",
  "career_type": "experienced",
  "role_evolution": "developer → lead → architect",
  "chapters": [
    {
      "chapter_id": "P_000001_ch0",
      "scope_type": "LEAD",
      "period_start": "2020-03",
      "period_end": "2024-12",
      "role": "Backend Lead",
      "company": "삼성전자",
      "skills": ["Python", "Kubernetes", "PostgreSQL"],
      "outcomes": [{"type": "SCALE", "description": "...", "confidence": 0.8}],
      "situational_signals": [{"label": "SCALING_TEAM", "confidence": 0.75}]
    }
  ]
}
```

### B. 동기 2-Tier API 검색 흐름

*검색 시점의 런타임 레이턴시를 최소화하기 위한 2단계 쿼리 체인.*

1. **사용자 요청**: 에이전트나 프론트엔드에서 요구사항 전달
2. **S&F API (Recall)**: "S&F 시스템, 이 조건(학력/연차 등)에 맞고 이 키워드 벡터와 가장 유사한 `person_id` 리스트 500개를 찾아줘"
3. **GraphRAG API (Precision)**: "GraphRAG 시스템, 해당 500개 ID(`WHERE person_id IN $list`) 안에서, JD 요구사항과 과거 채용 트렌드, 직무 시계열 이동 패턴에 가장 부합하는 정밀 순위 Top 20명만 스코어 산출해서 돌려줘"

> **레이턴시 목표 (SLA)**: S&F 하드 검색(p95 < 500ms) + GraphRAG 인메모리 IN-list 서칭(p95 < 2s) = 전체 체인 에이전트 반환 (p95 < 3s)
