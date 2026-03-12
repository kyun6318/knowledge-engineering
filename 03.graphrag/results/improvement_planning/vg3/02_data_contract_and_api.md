# 2. 인터페이스 사양서 (Data Contract 및 API 체인) - VG3

> 앞선 아키텍처 비전을 실현하기 위한 S&F 팀과 GraphRAG 팀 간 구체적인 비동기 파이프라인 규격(Event/Contract) 및 에이전트 연계를 위한 동기 API SLA(서비스 수준 약정)를 명세합니다.

---

## 2.1. 비동기 이벤트 기반 데이터 적재 파이프라인

"수동 파일 전달 및 대기" 방식의 비효율을 막고자, 단계별 추출 완료 시 **GCS PubSub 트리거 시스템**을 의무 적용한다.

* **파이프라인 흐름**: 
  1. **S&F 엔진** ➔ GCS (`gs://kg-artifacts/...`)에 JSONL 덤프 업로드
  2. **GCS Event** ➔ PubSub 토픽(`kg-artifact-ready`)으로 이벤트 발생
  3. **GraphRAG 시스템** ➔ PubSub 구독/트리거 인지 시 `Cloud Run Job` 작동 (자동 유효성 검사 및 Neo4j 적재)

### JSON Data Contract (CandidateContext 예시)

S&F 팀은 **PII 마스킹과 임베딩 추출을 모두 끝낸 상태**로, 그래프 적재에 꼭 필요한 필드들만 담아 전달한다.

```json
{
  "person_id": "P_000001",
  "career_type": "experienced",
  "education_level": "bachelor",
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

* **필수 이행 조건 (GraphRAG 적재 로직 제약)**:
  * 모든 사람의 개인 식별 가능 정보(PII)는 S&F 인프라 단계에서 처리됨 (전달 금지).
  * `chapter_id`는 Graph 연결 무결성을 위해 `{person_id}_ch{index}` 포맷 고정.
  * GraphRAG의 `[NEXT_CHAPTER]` 연결 속도 확보를 위해 배열 요소는 반드시 **시간순(`period_start` 오름차순)** 정렬 상태로 전달한다.

---

## 2.2. 동기 2-Tier API 검색 체인

클라이언트/에이전트가 런타임 쿼리를 던질 때, 두 시스템이 협력하여 최적의 추천을 리턴하는 플로우.

```
[클라이언트(에이전트)] ──(1) 하드 검색 및 NLP 키워드 요청──→ [S&F API (ES/Vector DB)]
                                                          │
   ┌──────────────────────────────────────────────────────┘
   │ (2) 1차 필터링된 person_id 후보군 리스트 반환 (Top 500 ~ 1,000건)
   ↓
[에이전트] ──(3) 후보군 ID List + 심층 질의 요건────→ [GraphRAG API (Neo4j)]
                                                          │
   ┌──────────────────────────────────────────────────────┘
   │ (4) Graph Traversal 및 5-MAPPED_TO 점수 합산 기반의 최종 랭킹 반환 (Top 20명)
   ↓
[클라이언트 완료]
```

### SLA 보장 (목표 레이턴시 유지)

| 구간 | p95 레이턴시 목표 | 전략적 근거 및 튜닝 방안 |
|---|---|---|
| **에이전트 ➔ S&F API** | **< 500ms** | - 단순 조건(RDB/ES)과 Vector 검색 특화 엔진이므로 지연시간이 매우 짧아야 함. |
| **에이전트 ➔ GraphRAG API** | **< 2s** | - 미리 S&F가 건네준 ID 리스트 집합에 속한(`WHERE person_id IN $id_list`) 노드로만 탐색 공간을 극단적으로 축소하여 Neo4j 인메모리 연산을 최적화함.<br>- 트래픽 방어를 위해 Cloud Run 최소 인스턴스 1대 항시 구동 적용. |
| **전체 사용자 경험 (총합)** | **< 3s** | 사용자가 AI 에이전트로부터 인내할 수 있는 권장 로딩 타임 만족. |
