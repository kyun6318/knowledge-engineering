# VG3 합성 전략 (Synthesis Strategy)

> **작성 목적**: 기존 작성된 `vg2`(아키텍처 비전/시각화 모델)와 `vc2`(구체적 타임라인/Data Contract/비용 추적 모델)의 장점을 결합하여 최고 품질의 **vg3** 계획을 수립한다.
> **핵심 원칙**: v5 원본 계획의 문제점을 해결하기 위한 본연의 목표, 즉 **"하드필터, PII 마스킹, 임베딩 추출 등 대규모 데이터 가공 및 1차 탐색(Recall)은 Search & Filter(S&F) 팀으로 분리하고, 직무 챕터(`[NEXT_CHAPTER]`) 기반의 복합 그래프 연산 및 정밀 매칭(Precision)은 GraphRAG 팀에 100% 위임한다"**는 방향성을 철저히 지킨다.

---

## 1. 기반 문서 평가 및 장점 추출

### 1.1. `vg2` 계획의 핵심 강점 (적용)
* **Polyglot & Microservice 설계**: 각각의 저장소(Vector DB, Neo4j)가 가장 잘하는 일에 집중한다는 비전. 
* **2-Tier API 흐름 명확화**: 에이전트 ➔ S&F (수백 명단) ➔ GraphRAG (최종 20명) 로 이어지는 응답 최적화 파이프라인.
* **시각화 (Mermaid Gantt)**: 복잡한 병렬 처리 구조를 한 눈에 파악할 수 있는 시각적 로드맵 제공.

### 1.2. `vc2` 계획의 핵심 강점 (적용)
* **73개 태스크 전수 분류 (연결성/추적성)**: 누락 없는 실행을 위한 구체적인 책임 분할 및 E2E E2E 추적.
* **명세화된 Data Contract**: GraphRAG 팀 개발자가 즉시 mock Server를 띄울 수 있는 필수 필드/JSON 구조와 PubSub 트리거 조건.
* **현실적인 리소스 플래닝 (Work/Wait Split)**: GraphRAG 팀의 12.5주가 "순수 작업"과 "대기 타임"으로 나뉘고, 87%에 달하는 인력 가동률 수치를 수치화함.
* **예산 및 SLA, 리스크 명세**: 실질적인 프로젝트 승인과 관리에 필요한 정량적 근거들.

---

## 2. VG3 문서화 구조

위의 강점을 결합하기 위해 **VG3**의 문서는 아키텍처 비전에서 실행 상세 내역까지 하향식(Top-Down)으로 다음과 같이 구성된다.

1. **`01_architecture_and_separation.md`**: 전사 역할 분리, 아키텍처 비전 및 S&F / GraphRAG 팀별 담당 범위.
2. **`02_data_contract_and_api.md`**: 팀 간 통신을 위한 JSON Data Contract와 2-Tier API 체인 통신 SLA 사양.
3. **`03_execution_and_tasks.md`**: 73개 태스크 기반의 주차별 병렬 타임라인 (Mermaid 표기) 및 Go/No-Go 통과 기준.
4. **`04_costs_and_risks.md`**: 예산 최적화 계획과 발생 가능한 5대 리스크 방어 전략.
