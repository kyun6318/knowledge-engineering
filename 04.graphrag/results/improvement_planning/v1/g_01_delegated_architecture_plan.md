# GraphRAG 고도화 아키텍처 (Search & Filter 관심사 분리) 계획서

> **작성일**: 2026-03-12
> **목적**: Phase 1~3(총 20주)에서 리소스를 가장 많이 차지하던 "임베딩 추출" 및 "하드 필터링(속성 파싱)" 역할을 Search & Filter(이하 `S&F`) 아티팩트 처리팀으로 완전히 분리(Delegation)하여, **GraphRAG 팀은 "지식 그래프의 관계 매칭 및 네트워크 패턴 분석"에만 100% 집중**할 수 있도록 전체 실행 계획을 재구성함.
>
> **효과**: 
> 1. GraphRAG 구축 페이즈의 획기적인 기간 단축 (기존 20주 ➔ **약 9주 내외**)
> 2. 시스템 결합도 저하 및 스케일링 유연성 확보 (Microservice/Polyglot 아키텍처)
> 3. Neo4j의 라이선스 및 리소스 최적화

---

## 1. 아키텍처 역할 분리 (Separation of Concerns)

### 1.1. Search & Filter 팀 (S&F)
> "대규모 문서에서 속성을 추출하고 벡터 검색을 통해 1차 후보군(Recall)을 뽑아내는 역할"

* **데이터 전처리 전담**: 이력서 파일(PDF, DOCX 등) 및 JD 파싱, PII 마스킹, 하드 필터 요소(연차, 학력, 기술 스택 등) 정형화
* **Vector DB 전담**: LLM 호출을 통한 `CandidateContext` 텍스트 추출 및 임베딩 벡터 생성, Vector DB(Milvus/Pinecone 등) 또는 Search Engine(Elasticsearch) 적재
* **1차 Retrieval API 제공**: "3년 차 리드급 파이썬 개발자 1,000명"과 같은 질의를 받아 1차 필터링된 **후보자/채용공고 ID 리스트(Payload)** 반환

### 1.2. GraphRAG 팀
> "S&F 팀이 넘겨준 정제된 노드들을 연결하고, 그래프 고유의 '관계/패턴'을 추론하여 최종 랭킹(Refining)을 매기는 역할"

* **지식 그래프 엔진 최적화 전담**: S&F에서 넘어온 `person_id`, `chapter_id`, `vacancy_id` 및 연결 속성(회사, 스킬)만 노드로 가볍게 적재
* **매칭 알고리즘 고도화**: 단순 스킬 매칭에서 벗어나, "이전 직장에서의 성장 패턴(`[NEXT_CHAPTER]`)", "기업 스테이지 핏(`stage_match`)", "상황적 신호(`SituationalSignal`)" 교차 분석
* **결합 검색 API 제공**: S&F의 1차 풀(500명)을 입력받아 즉각적으로 최상위 핏 20명을 랭킹화하는 API 제공

---

## 2. Phase 1~3 일정 및 공수 재조정 (20주 ➔ 약 9주)

### Phase 1: Core Candidate Topology MVP (총 2.5주)
> *기존 5주 (Week 2~6)에서 S&F 처리 분리 후 대폭 축소*

* **1-1. 데이터 파이프라인 연동 (1주)**
  * S&F 팀으로부터 정제된(마스킹 완료된) 인물 및 챕터 JSON 데이터 수신 인터페이스 구축
  * Kafka 또는 GCS Event/PubSub을 통한 이벤트 기반 적재 파이프라인 연동
* **1-2. Graph 뼈대 적재 (1주)**
  * 벡터 임베딩 생성 및 인덱스 처리 제외 (S&F 이관)
  * `Person`, `Chapter`, `Skill`, `Role`, `Organization` 노드와 엣지(`HAS_CHAPTER`, `USED_SKILL` 등 v19 표준 관계) 고속 일괄 적재 (UNWIND Batch)
* **1-3. 그래프 전용 서빙 API & 데모 (0.5주)**
  * Neo4j에 최적화된 Cypher 그래프 쿼리 5종 작성 및 API 테스트

### Phase 2: 파일 이력서 전체 적재 및 네트워크 밀도 향상 (총 3주)
> *기존 9주 (Week 7~15)에서 문서 파싱 및 LLM 폴백 제거로 1/3 축소*

* **2-1. 대규모 데이터 Bulk Loading (1.5주)**
  * 복잡한 파이프라인 (PDF 파싱, HWP 파싱, LLM 폴백 등) 전면 S&F 팀 이관
  * 60만 건 수준의 대규모 ID/분류 데이터베이스를 Neo4j로 안정적으로 적재하는 오케스트레이션 집중 (Airflow / Cloud Workflows)
* **2-2. Data Quality 및 Topology 검증 (1주)**
  * 노드 간 고립(Orphan) 추적, `[NEXT_CHAPTER]` 연결의 정확성, 비정상 밀도 추적
* **2-3. 구조적 쿼리 성능 벤치마크 (0.5주)**
  * S&F가 넘겨주는 In-list(`WHERE id IN [...]`) 조건에 대한 대규모 성능 튜닝 및 인덱스 최적화

### Phase 3: 기업 정보 + 심층 매칭 알고리즘 (총 3.5주)
> *기존 6주 (Week 17~22)에서 JD 파서 등 단순 연계 작업 제외*

* **3-1. 공고 및 매칭 파이프라인 (1주)**
  * S&F 팀으로부터 JD/기업 컨텍스트 완성 구조체(JSON) 직접 수신
  * `Vacancy`, `CompanyContext` Graph 즉시 적재
* **3-2. 매칭 스코어링 고도화 로직 집중 (1.5주)**
  * 단순 교집합(Domain Fit)은 넘기고, `stage_match`, `culture_fit`, `role_evolution` (F1, 4, 5) 등 고차원 피처에 리소스 집중
  * `[NEXT_CHAPTER]`를 활용한 시계열 이직 패턴/체류 기간 역량 모델링 
* **3-3. 가중치 튜닝 및 MAPPED_TO 캐싱 (1주)**
  * 전문가 수동 튜닝 (Top-10 적합도 최우선)
  * 매칭 점수 임계값 검토 후 Graph 내 `[MAPPED_TO]` 관계로 구체화

---

## 3. 분리 (Delegation) 환경의 인터페이스 사양

두 시스템 간 통신 오버헤드나 순서 뒤엉킴(역전 현상)을 막기 위해 아래의 인터페이스 계약(Data Contract)을 전제로 합니다.

### A. Graph 적재 시 (Asynchronous Event)
* **포맷**: S&F 시스템이 텍스트/이미지를 통해 추출/정제한 **Vector 제외** JSONL 파일 (GCS 등 적재)
* **필수 포함 데이터**: `person_id`, `chapter_id`, `vacancy_id`, `org_stage`, 정규화된 `skills`, `role`, 챕터 `period_start/end`
* **PII(개인정보)**: 모든 PII 마스킹 처리 후 해시/마스킹 된 형태로 전달할 것. GraphRAG Neo4j는 PII 원본을 보관하지 않음.

### B. 에이전트/API 쿼리 조회 시 (Synchronous API Flow)
1. 클라이언트(에이전트) ➔ S&F API를 호출 (하드 조건 파라미터 + 자연어)
2. **S&F 엔진**: 자신의 RDB 및 Vector DB를 통해 1차 부합 후보군 ID **Top 500~1,000건** 리턴 (Recall 단계)
3. 클라이언트(에이전트) ➔ GraphRAG API로 1차 풀(ex: `[ID1, ID2, ... ID500]`) 전달
4. **GraphRAG 엔진**:
   * 전달받은 ID들로만 한정하여(`WHERE person_id IN $id_list`)
   * `Candidate ↔ Vacancy` 매칭 피처 스코어 5종 계산 및 `[NEXT_CHAPTER]` 순차망 교차 분석
   * 최종적으로 최상위 정밀 적합 후보 **Top 20명** 반환 (Precision/Refining 단계)

---

## 4. 리스크 및 완화 방안

* **리스크 1. S&F 팀과 스펙 싱크로(Sync) 불일치**
   * *완화 방안*: Phase 1 시작 이전에 JSON Schema를 기반으로 한 강력한 상호 Data Contract 문서 수립 및 1주차 모의 인터페이스 연동(Integration Test) 강제 수행
* **리스크 2. 필터링 역전 및 최종 결과 누수**
   * *완화 방안*: S&F 팀의 Top-K(임계치 허용량)를 넉넉하게 설정(최소 필요량의 10배수 이상인 500~1000건)하도록 강제하여, GraphRAG에서 필터링 후에도 충분한 풀(Pool)이 보장되게 조정.
