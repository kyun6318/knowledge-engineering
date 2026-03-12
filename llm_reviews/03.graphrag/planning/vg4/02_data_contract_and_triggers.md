# VG4 — Data Contract 및 이벤트 트리거 사양

> 팀 분리의 성패는 **인터페이스 사양의 명확도**에 달려 있다.

---

## 1. 비동기 파이프라인: GCS → PubSub → 자동 적재

```
[S&F 파이프라인] → JSONL 생성 → GCS 버킷 업로드
                                  ├─ gs://kg-artifacts/candidate/
                                  ├─ gs://kg-artifacts/vacancy/
                                  └─ gs://kg-artifacts/company_enrichment/
                                       │
                                  GCS Object Finalize 이벤트
                                       │
                                  PubSub Topic (kg-artifact-ready)
                                       │
                                  [GraphRAG Cloud Run Job] 자동 트리거
                                       ├─ JSONL 읽기
                                       ├─ JSON Schema 검증
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
  "role_evolution": "developer → lead → architect",
  "domain_depth": "backend_systems",
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

**필수 조건**:
- PII 완전 마스킹 (원본은 S&F GCS CMEK에 보관)
- `chapter_id`는 `{person_id}_ch{index}` 형식 (GraphRAG NEXT_CHAPTER 연결에 사용)
- `chapters[]`는 **시간 순서(period_start 오름차순)로 정렬**
- v12 프롬프트 기준 필드 준수

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

## 3. S&F → GraphRAG 산출물 5종 명세

| # | 산출물 | 시점 | 형식 | 전달 경로 | 트리거 |
|---|--------|------|------|---------|--------|
| ① | PoC 결과 (20건+리포트) | W1 D5 | JSON+리포트 | **수동** (Go/No-Go 회의) | — |
| ② | CandidateContext 1,000건 | W5 | JSONL | GCS `candidate/batch_{id}.jsonl` | **PubSub 자동** |
| ③ | CandidateContext 480K+ | W9~15 | JSONL (10K건/chunk) | GCS + **PubSub 자동** (순차) | 주간 Slack 리포트 |
| ④ | JD + CompanyContext | W17~18 | JSONL | GCS `vacancy/` + `company/` | **PubSub 자동** |
| ⑤ | 기업 보강 데이터 | W24~25 | JSONL | GCS `company_enrichment/` | **PubSub 자동** |

---

## 4. 동기 API 체인 (2-Tier Recall → Precision)

```
[에이전트] ──(1) 하드필터+NLP 검색──→ [S&F API: 속성+벡터]
                                          │
                                    (2) person_id Top 500~1000건
                                          │
            ←──(4) 최종 Top 20──────── [GraphRAG API: 관계 매칭+랭킹]
                                          │
                                    (3) MAPPED_TO 5-피처 스코어링
```

### SLA

| 구간 | p95 목표 | 미달 시 대응 |
|------|---------|------------|
| S&F API (하드필터+벡터) | **< 500ms** | ES/Vector 인덱스 튜닝, 캐싱 |
| GraphRAG API (IN-list 매칭) | **< 2s** | 복합 인덱스, IN-list 축소(500→200) |
| **전체 체인** | **< 3s** | min-instances=1 ($10~15/월) |
