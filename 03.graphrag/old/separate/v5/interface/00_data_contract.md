# S&F ↔ GraphRAG 공동

> 팀 분리의 성패는 **인터페이스 사양의 명확도**에 달려 있다.
> 

---

## 1. 비동기 파이프라인: GCS → PubSub → 자동 적재

```
[S&F 파이프라인] -> JSONL -> GCS 업로드
                           ├─ gs://kg-artifacts/candidate/
                           ├─ gs://kg-artifacts/vacancy/
                           └─ gs://kg-artifacts/company_enrichment/
                                │
                           GCS Object Finalize
                                │
                           PubSub (kg-artifact-ready)
                                │
                           [GraphRAG Cloud Run Job] 자동 트리거
                                ├─ JSONL 읽기 + JSON Schema 검증
                                ├─ UNWIND Batch 적재
                                └─ BigQuery 적재 로그 기록
```

### PubSub 토픽 스키마

```
Topic: kg-artifact-ready
Message attributes:
  artifact_type: "candidate" | "vacancy" | "company" | "company_enrichment"
  batch_id: "batch_20260501_001"
  file_count: 5
  record_count: 10000
  gcs_prefix: "gs://kg-artifacts/candidate/batch_20260501/"
```

---

## 2. JSON Data Contract (3종)

### A. CandidateContext (Phase 1~2)

```json
{
  "person_id": "P_000001",
  "career_type": "experienced",
  "education_level": "bachelor",
  "role_evolution": "developer -> lead -> architect",
  "domain_depth": "backend_systems",
  "chapters": [
    {
      "chapter_id": "P_000001_ch0",
      "scope_type": "LEAD",
      "period_start": "2020-03",
      "period_end": "2024-12",
      "role": "Backend Lead",
      "company": "삼성전자",
      "skills": ["Python", "Kubernetes"],
      "outcomes": [{"type": "SCALE", "description": "...", "confidence": 0.8}],
      "situational_signals": [{"label": "SCALING_TEAM", "confidence": 0.75}]
    }
  ]
}
```

**필수 조건**:
- PII 완전 마스킹 (원본은 S&F GCS CMEK)
- `chapter_id` = `{person_id}_ch{index}` (GraphRAG NEXT_CHAPTER 연결에 사용)
- `chapters[]` **시간 순서(period_start 오름차순)** 정렬
- Ontology 프롬프트 기준 필드 준수

### B. Vacancy + CompanyContext (Phase 3)

```json
{
  "vacancy_id": "V_10001",
  "org_id": "ORG_samsung",
  "org_name": "삼성전자",
  "org_stage": "ENTERPRISE",
  "industry": "반도체",
  "industry_code": "C261",
  "required_skills": ["Python", "TensorFlow"],
  "required_role": "ML Engineer",
  "seniority": "SENIOR",
  "needed_signals": ["SCALING_TEAM", "GREENFIELD"],
  "hiring_context_scope": "LEAD",
  "operating_model": {"speed": "FAST", "autonomy": "HIGH", "process": "AGILE"}
}
```

### C. 기업 보강 데이터 (Phase 4)

```json
{
  "org_id": "ORG_samsung",
  "product": ["갤럭시", "엑시노스"],
  "funding": null,
  "growth_signals": ["반도체 투자 확대"],
  "source": "homepage_crawl",
  "crawled_at": "2026-06-01T09:00:00Z"
}
```

---

## 3. 산출물 5종 교환 스펙

| # | 산출물 | 시점 | 형식 | GCS 경로 | 트리거 |
| --- | --- | --- | --- | --- | --- |
| 1 | PoC 결과 | W1 D5 | JSON+리포트 | - | **수동** (Go/No-Go 회의) |
| 2 | Candidate 1K | W5 | JSONL | `candidate/batch_{id}.jsonl` | **PubSub 자동** |
| 3 | Candidate 480K+ | W9~15 | JSONL (10K/chunk) | `candidate/batch_{id}.jsonl` | **PubSub 자동** + 주간 리포트 |
| 4 | JD + Company | W17~18 | JSONL | `vacancy/` + `company/` | **PubSub 자동** |
| 5 | 기업 보강 | W24~25 | JSONL | `company_enrichment/` | **PubSub 자동** |

---

## 4. 동기 API 체인 (2-Tier: Recall -> Precision)

```
[에이전트] ──(1) 하드필터+벡터 검색──-> [S&F API]
                                          │
                                    (2) person_id Top 500~1,000건
                                          │
            ←──(4) 최종 Top 20──────── [GraphRAG API: MAPPED_TO 5-피처]
```

### SLA

| 구간 | p95 목표 | 미달 시 대응 |
| --- | --- | --- |
| S&F API | **< 500ms** | ES/Vector 인덱스, 캐싱 |
| GraphRAG API | **< 2s** | 복합 인덱스, IN-list 축소 |
| **전체 체인** | **< 3s** | min-instances=1 |

---

## 5. 보안

### PII 보안 (Ontology S2)

```
- S&F: PII 매핑 -> gs://kg-pii-mapping/ (CMEK, kg-pii-reader만 접근)
- GraphRAG: PII 필드 API 응답에서 자동 제거 (N2)
- GraphRAG는 원시 PII를 절대 보관하지 않음
```

### 서비스 계정 4개

| 계정 | 팀 | 용도 |
| --- | --- | --- |
| kg-crawling | S&F | 크롤링 Job |
| kg-processing | S&F | 전처리 + LLM |
| kg-loading | GraphRAG | Graph 적재 + API |
| kg-pii-reader | S&F | PII 매핑 읽기 전용 |