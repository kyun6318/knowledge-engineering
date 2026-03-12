# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

채용 도메인에서 기업-인재 맥락 매칭을 위한 Knowledge Graph 설계/구축/서빙 **문서 저장소**입니다. 코드가 아닌 설계 문서(마크다운)가 주요 산출물입니다.

## 3-Layer 아키텍처

이 저장소는 **what → how to build → how to serve** 3계층으로 분리됩니다. 문서 작성/수정 시 이 경계를 반드시 준수해야 합니다.

| 디렉토리 | 역할 | 현재 버전 | 포함하는 것 | 포함하면 안 되는 것 |
|----------|------|-----------|-------------|-------------------|
| `01.ontology/` | **what to represent** (순수 스키마) | v20 | 필드 정의, 타입, Taxonomy, JSON 스키마, 매핑 규칙, confidence 모델, 논리 그래프 구조 | 구현 코드, 기술 스택, 비용, 파이프라인, 인프라 |
| `02.knowledge_graph/` | **how to build** (추출/정규화/품질) | v13 | 추출 방법, 정규화 로직, LLM 프롬프트, PII 처리, 데이터 품질, 파이프라인 흐름 | 서빙 방법, 매칭 알고리즘, Neo4j/BQ 구현 |
| `03.graphrag/` | **how to serve** (구현/배포/평가) | separate/v3 | GCP 구현 계획, Neo4j/BQ 스키마, 비용, 평가, 운영 정책, 서빙 인터페이스 | 순수 온톨로지 정의, 추출 프롬프트 설계 |

## 핵심 도메인 개념

- **CompanyContext**: 기업의 성장 단계, 채용 맥락, 운영 방식 (JD, NICE 기업정보에서 추출)
- **CandidateContext**: 후보의 경력을 Chapter 단위로 분해 (resume-hub Career 1건 = 1 Chapter)
- **MappingFeatures**: 5개 적합도 피처(F1~F5) → `overall_match_score × freshness_weight = ranking_score`
- **Graph Schema**: 9개 노드 (Person, Organization, Chapter, Vacancy, Role, Skill, Outcome, SituationalSignal, Industry)
- **SituationalSignal**: 14개 고정 taxonomy (EARLY_STAGE, SCALE_UP, TEAM_BUILDING 등)

## 디렉토리 구조 규칙

- 각 디렉토리의 최신 버전만 활성 문서 (`v20/`, `v13/`, `separate/v3/`)
- `old/` 폴더: 이전 버전 아카이브 (참조만, 수정 금지)
- `llm_log/`: LLM 리뷰/응답 이력 (참조용)
- `llm_reviews/`: 디렉토리별 리뷰, changelog, 개선 계획

## 문서 작성 원칙

1. **Evidence-first**: 모든 claim에 원문 근거(Evidence) 필수
2. **Taxonomy 고정**: LLM 자유 생성 방지, 고정 분류 체계에서 선택
3. **부분 완성 허용**: 데이터 없으면 null 명시, Graceful Degradation
4. **데이터 소스 계층화**: T1(JD)~T6(채용 히스토리), 소스별 confidence 상한 적용
5. **의도적 제외 명문화**: 현 버전에서 제외한 기능의 이유와 도입 로드맵 문서화

## 버전 관리 패턴

새 버전 생성 시:
- 새 버전 디렉토리 생성 (예: `v21/`)
- README.md의 현재 유효 버전 번호 갱신
- 이전 버전을 `old/`로 이동하지 않음 (별도 정리 시점에 일괄 이동)
- 변경 사항은 README.md 내 버전 이력 테이블에 기록

## 관련 외부 시스템

- 설계 완료 문서 이동처: `https://git.jobkorea.co.kr/agentic-services/docs/`
- Notion 위키: GraphRag 프로젝트 페이지
- GCP 프로젝트: `graphrag-kg` (Cloud Run Jobs, Neo4j AuraDB, BigQuery, Vertex AI)
- LLM: Claude Haiku 4.5 (Batch API), text-embedding-005 (Vertex AI)
