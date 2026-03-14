# S&F Phase 3: JD 파싱 + CompanyContext (Week 17~18)

> **v5 원본**: `04_phase3_company_and_matching.md` §3-1, §3-2
> **산출물 ④**: JD JSONL + CompanyContext JSONL → GCS → PubSub 자동 트리거

---

## 3-1. JD 파싱 + Vacancy JSON 생성 (0.5주, W17 후반)

> ★ v5 A1: **Phase 3 시작 전 job-hub API 스펙 확정 여부 반드시 확인**
> API가 구조화된 JSON이면 0.5주 실현 가능. 비구조화 시 1주로 확장.

### JD → Vacancy JSON 변환

job-hub API의 구조화된 JSON을 `interface/00_data_contract.md`의 Vacancy 스키마로 변환:

```json
{
  "vacancy_id": "V_10001",
  "org_id": "ORG_samsung",
  "org_name": "삼성전자",
  "required_skills": ["Python", "TensorFlow"],
  "required_role": "ML Engineer",
  "seniority": "SENIOR",
  "needed_signals": ["TEAM_SCALING", "NEW_SYSTEM_BUILD"],
  "hiring_context_scope": "LEAD"
}
```

---

## 3-2. CompanyContext 파이프라인 (2주, W18-19)

### CompanyContext 추출 — DB 직접 + NICE Rule + LLM 3단계

```python
# src/extractors/company_extractor.py — v12 §1
async def extract_company_context(jd: dict, nice_info: dict, provider: LLMProvider) -> dict:
    # Step 1: DB 직접 매핑 (LLM 비용 $0)
    direct_fields = {
        "company_name": jd.get("company_name"),
        "industry": lookup_industry(jd.get("skill_codes")),
        "tech_stack": normalize_skills(jd.get("skills")),
        "career_types": parse_career_types(jd.get("requirement")),
        "education_level": jd.get("education_level"),
        "location": jd.get("work_condition", {}).get("location"),
        "salary_range": jd.get("work_condition", {}).get("salary"),
    }
    # Step 2: NICE Lookup (Rule 기반)
    stage_estimate = estimate_stage(
        employee_count=nice_info.get("employee_count"),
        revenue=nice_info.get("revenue"),
        founded_year=nice_info.get("founded_year"),
    )
    # Step 3: LLM 추출 (hiring_context, operating_model)
    llm_result = await provider.extract(
        build_company_prompt(jd, direct_fields, nice_info),
        CompanyContextExtraction
    )
    return {**direct_fields, "stage": stage_estimate, **llm_result}
```

### operating_model 검증 (v12 C3)

```python
def validate_operating_model(facets: dict, evidence: list[str]) -> dict:
    validated = {}
    MIN_EVIDENCE_LENGTH = 20
    for facet in ["speed", "autonomy", "process"]:
        value = facets.get(facet)
        if value is None:
            validated[facet] = None
            continue
        facet_evidence = " ".join(str(e) for e in evidence if facet.lower() in str(e).lower())
        validated[facet] = value if len(facet_evidence) >= MIN_EVIDENCE_LENGTH else None
    return validated
```

---

## 잔여 Batch 처리 (W19-22, Phase 2 미완료분)

### 비관 시나리오 명시적 Batch 할당

```
W17-18: Phase 3 전용 2 batch + 잔여 8 batch → ~140K 소화
W19-22: Phase 3 전용 3 batch + 잔여 7 batch → ~160K 소화
→ 비관 시나리오에서도 W22까지 90%+ 완료
```

### N9: 주간 리포트

```sql
SELECT DATE(processed_at) AS week_start,
  COUNT(*) AS processed,
  COUNTIF(status = 'SUCCESS') AS success,
  COUNTIF(status = 'FAILED') AS failed
FROM graphrag_kg.batch_tracking
GROUP BY week_start ORDER BY week_start DESC;
```

---

## 산출물 ④ 전달

```
W17~18:
  □ Vacancy JSONL → GCS gs://kg-artifacts/vacancy/batch_{id}.jsonl
  □ CompanyContext JSONL → GCS gs://kg-artifacts/company/batch_{id}.jsonl
  □ PubSub kg-artifact-ready 자동 발행 (artifact_type: "vacancy" / "company")
```
