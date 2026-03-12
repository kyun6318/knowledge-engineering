# 모델 선정 및 추출 인프라 v12

> 작성일: 2026-03-11 | 기준: 온톨로지 v19, GCP ML Pipeline, GraphRAG Core v2
>
> v11 대비 변경: 없음 (v12 변경 사항은 01/03/04 문서에 집중)

---

## 1. LLM 모델 후보

### 1.1 v1 MVP 추천

| 모델 | 입력/출력 단가 (1M tok) | Batch 단가 | 품질 | 용도 |
|------|----------------------|-----------|------|------|
| **Claude Haiku 4.5** (1순위) | $0.80 / $4.00 | $0.40 / $2.00 | 중상 | CandidateContext, CompanyContext 추출 |
| Claude Sonnet 4.6 (폴백) | $3.00 / $15.00 | $1.50 / $7.50 | 상 | Haiku 품질 <70% 시 전환 |
| Gemini 2.0 Flash (대안) | $0.10 / $0.40 | $0.05 / $0.20 | 미검증 | 최저 비용 시나리오 |

**Batch API**: 50% 할인, 24시간 레이턴시 허용 (컨텍스트 생성은 비실시간)

### 1.2 Phase 0 모델 선정 기준

| 기준 | Haiku 통과 | Sonnet 전환 |
|------|-----------|------------|
| scope_type 정확도 | ≥70% | <70% |
| outcomes F1 | ≥50% | <50% |
| situational_signals F1 | ≥45% | <45% |
| JSON 파싱 성공률 | ≥95% | <90% |

---

## 2. Embedding 모델

### 2.1 v12 표준: text-embedding-005

| 항목 | v9 (embedding-002) | v12 (embedding-005) |
|------|---------------------|---------------------|
| 차원 | 768d | **768d** |
| 단가 | $0.0065/1M tok | **$0.0001/1K chars** |
| 한국어 | 다국어 지원 | 다국어 지원 (Phase 0 검증) |
| 플랫폼 | Vertex AI | **Vertex AI** |
| 선정 이유 | v9 시점 추천 | **GraphRAG v2 표준화, 비용 효율** |

**Phase 0 검증**: 한국어 분별력 "excellent" 기준 충족 여부
- 실패 시 폴백: Cohere embed-multilingual-v3.0 ($0.10/1M tok, **1024d**) — Neo4j Vector Index 차원 변경 필요
- Phase 0에서 Neo4j Vector Index 생성은 **임베딩 모델 확정 후로 순서 조정 권고**

### 2.2 임베딩 비용

| 용도 | 대상 | 수량 | 비용 |
|------|------|------|------|
| Chapter 벡터 | 1.8M chapters × 200 tok avg | 360M tok | ~$25 |
| Vacancy 벡터 | 10K vacancies × 500 tok avg | 5M tok | ~$0.5 |
| 3-Tier canonical | ~3K canonicals × 50 tok avg | 150K tok | ~$0.01 |
| **임베딩 소계** | | | **~$25.5** |

---

## 3. Graph DB

### 3.1 Neo4j AuraDB 마이그레이션 경로

| Phase | 티어 | 노드 한도 | 월 비용 | 용도 |
|-------|------|----------|---------|------|
| 0-1 | **Free** | 200K | $0 | PoC + 1,000건 MVP |
| 2+ | **Professional** | 800K+ | $100-200 | 전체 데이터 (8M 노드) |

**Phase 0 검증 필수**: AuraDB Professional이 8M 노드 + 25M 엣지를 수용하는지 확인.
불가 시 AuraDB Enterprise 또는 자체 호스팅 검토.

**리전**: asia-northeast1 (도쿄) — 서울 미지원
**Vector Index**: 768d cosine (임베딩 모델 확정 후 생성)

---

## 4. 추출 관련 GCP 리소스

> 전체 GCP 인프라 아키텍처는 04.graphrag를 참조.
> 여기서는 추출 파이프라인(A/B/B'/C)에 직접 관련된 리소스만 정의.

### 4.1 서비스 계정 (추출 관련)

| 계정 | 역할 | 접근 범위 |
|------|------|----------|
| **kg-processing** | storage.objectViewer/Creator, bigquery.dataEditor, aiplatform.user, secretmanager.secretAccessor | GCS 읽기/쓰기, BQ 쓰기, Vertex AI, LLM API 키 |
| **kg-loading** | storage.objectViewer, bigquery.dataViewer, secretmanager.secretAccessor | GCS 읽기, BQ 읽기, **Neo4j 접근 전용** |

> kg-crawling 계정은 Pipeline A+ (Phase 4)에서 사용. 04.graphrag 참조.

### 4.2 Cloud Run Jobs (추출 관련)

| Job 이름 | 역할 | 병렬 | 서비스 계정 |
|----------|------|------|-----------|
| kg-parse | 파일 파싱 (PDF/DOCX/HWP) | 50 | kg-processing |
| kg-preprocess | 정규화, PII 마스킹, 블록 분리 | 50 | kg-processing |
| kg-extract | LLM 추출 (Batch API 제출/수집) | 10 | kg-processing |
| kg-graph-load | Neo4j UNWIND 적재 | **≤5** | kg-loading |

### 4.3 상태 저장

| 서비스 | 용도 | 비고 |
|--------|------|------|
| BigQuery | dead_letter, batch_log | 추출 오류 추적 |
| GCS | 중간 결과 jsonl, 백업 | 버전닝 활성화 |

### 4.4 비용 (추출 관련 인프라, 27주)

| 항목 | 27주 비용 | 비고 |
|------|----------|------|
| Cloud Run Jobs (kg-parse/preprocess/extract/graph-load) | ~$300 | 배치 처리 |
| GCS | ~$36 | 중간 결과/백업 |
| Vertex AI (임베딩) | ~$26 | 1회성 |
| **추출 인프라 소계** | **~$362** | |

> Neo4j, BigQuery 전체, Cloud Workflows, Scheduler 비용은 04.graphrag에서 통합 관리
