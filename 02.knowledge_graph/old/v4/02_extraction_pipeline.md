# v4 온톨로지 기반 추출 파이프라인 설계

> v4 CompanyContext / CandidateContext / Graph Schema에 정합하는 추출 파이프라인.
> v1의 "범용 NER/RE" 접근을 폐기하고, 도메인 특화 Context 생성 파이프라인으로 재설계한다.
>
> 작성일: 2026-03-08 (v2 기반)
> 개정일: 2026-03-08 (v4 — Organization MERGE 통일, evidence_span 검증, Candidate Shortlisting, Graph 적재 전략 분리, embedding 텍스트 정의)

---

## 0. 설계 원칙

| 원칙 | 설명 |
|---|---|
| **v4 스키마 정합** | 추출 결과가 v4 JSON 스키마(CompanyContext, CandidateContext)에 직접 매핑 |
| **Rule-first, LLM-for-reasoning** | 정형/팩트 필드는 Rule/Lookup, 추론/해석 필드는 LLM |
| **Graceful Degradation** | null 허용 필드 명시, 비활성 피처 자동 처리 |
| **Evidence 필수** | 모든 추출에 source_id + span + confidence 첨부 |
| **비용 현실주의** | LLM 의존도를 인정하되 최적화 전략 적용 |
| **Fail-safe** | 에러 유형별 retry/skip/fallback 정책으로 대량 처리 안정성 확보 |

---

## 1. 파이프라인 전체 구조

```
[데이터 소스]
├─ JD (자사 보유 / 크롤링)
├─ NICE 기업 정보 DB
├─ 이력서 (자사 보유)
└─ (향후) 크롤링 / 투자DB

    ▼

[Pipeline A: CompanyContext 생성]
    JD + NICE → CompanyContext JSON
    ├─ company_profile (NICE Lookup)
    ├─ stage_estimate (Rule + LLM)
    ├─ vacancy + role_expectations (LLM 통합 추출)
    └─ operating_model (키워드 + LLM)

    ▼

[Pipeline B: CandidateContext 생성]
    이력서 + NICE → CandidateContext JSON
    ├─ experiences[] 추출 (Rule + LLM)
    │   ├─ 기본 정보 (Rule)
    │   ├─ scope_type, outcomes (LLM)
    │   ├─ situational_signals (LLM + taxonomy)
    │   └─ past_company_context (NICE Lookup)
    ├─ role_evolution (LLM)
    └─ domain_depth (LLM)

    ▼

[Pipeline C: Graph 적재]
    CompanyContext + CandidateContext → Neo4j
    ├─ 노드 생성 (Person, Chapter, Organization, ...)
    ├─ 관계 생성 (HAS_CHAPTER, OCCURRED_AT, ...)
    └─ Vector Index 업데이트

    ▼

[Pipeline D: MappingFeatures 계산]
    CompanyContext × CandidateContext → MappingFeatures JSON
    ├─ stage_match (Rule)
    ├─ vacancy_fit (Rule + lookup)
    ├─ domain_fit (Embedding)
    ├─ culture_fit (Rule, 대부분 INACTIVE)
    └─ role_fit (Rule + LLM)

    ▼

[Pipeline E: 서빙]
    MappingFeatures → BigQuery 테이블
```

---

## 2. Pipeline A: CompanyContext 생성

### 입력
- JD 텍스트 (job_id 단위)
- NICE 기업 정보 (company_id 기준)

### 2.1 company_profile — NICE Lookup (Rule, LLM 불필요)

```python
def extract_company_profile(nice_data):
    """NICE DB에서 직접 조회. LLM 불필요."""
    return {
        "company_name": nice_data.company_name,
        "industry_code": nice_data.industry_code,
        "industry_label": INDUSTRY_CODE_MAP[nice_data.industry_code],
        "founded_year": nice_data.founded_year,
        "employee_count": nice_data.employee_count,
        "revenue_range": categorize_revenue(nice_data.revenue),
        "is_regulated_industry": nice_data.industry_code[:2] in REGULATED_CODES,
        "evidence": [Evidence(source_type="nice", ...)]
    }
```

- **비용**: 0 (DB 조회만)
- **confidence**: 0.70 (NICE ceiling)

### 2.2 stage_estimate — Rule + LLM Fallback

```python
def extract_stage(nice_data, jd_text):
    """v4 01_company_context.md의 pseudo-code 그대로 구현"""
    # Step 1: Rule-based (NICE 데이터)
    if nice_data.founded_year and nice_data.employee_count:
        age = 2026 - nice_data.founded_year
        emp = nice_data.employee_count
        if age <= 3 and emp < 30:
            return "EARLY", 0.70
        elif 30 <= emp <= 300:
            return "GROWTH", 0.65
        elif emp > 300 or nice_data.revenue > 10_000_000_000:
            return "SCALE", 0.65
        elif age >= 15 and nice_data.revenue > 50_000_000_000:
            return "MATURE", 0.70

    # Step 2: LLM fallback (JD에서 stage 힌트)
    stage = llm_extract_stage(jd_text)  # Haiku/Flash급으로 충분
    if stage:
        return stage, 0.50
    return "UNKNOWN", 0.0
```

- **비용**: Rule로 해결되면 0, LLM fallback 시 JD 1건당 ~500 토큰
- **LLM fallback 예상 비율**: 20-30% (NICE 데이터가 불완전한 경우)

### 2.3 vacancy + role_expectations — LLM 통합 추출 (필수)

> **v3 변경**: v2에서 별도 프롬프트였던 vacancy와 role_expectations를 **단일 프롬프트로 통합**.
> 토큰 절감 효과: JD 1건당 ~1,000 토큰 절감 (JD 본문 중복 입력 제거).

```python
VACANCY_AND_ROLE_PROMPT = """
아래 채용 공고(JD)를 분석하여 JSON으로 응답하세요.

[1. Vacancy 추출]
- scope_type: BUILD_NEW / SCALE_EXISTING / RESET / REPLACE / UNKNOWN
  - BUILD_NEW: "신규 구축", "0→1", "greenfield" 등
  - SCALE_EXISTING: "확장", "스케일", "고도화" 등
  - RESET: "리팩토링", "재설계", "전환" 등
  - REPLACE: "충원", "결원", "대체" 등
- seniority: JUNIOR / MID / SENIOR / LEAD / HEAD / UNKNOWN
- role_title: 직무명 (원문 그대로)
- team_context: 팀 구성/규모 (추출 가능시만, 없으면 null)

[2. Role Expectations 추출]
- responsibilities: 주요 업무 (리스트)
- requirements: 필수 자격 (리스트)
- preferred: 우대 사항 (리스트)
- tech_stack: 기술 스택 (정규화된 이름, 리스트)

[규칙]
- 반드시 근거 문장(span)을 원문에서 인용하세요.
- 인용할 수 없으면 UNKNOWN으로 분류하세요.
- confidence: 0.0~1.0 (확신도)

[JD]
{jd_text}

[출력 JSON]
{
  "vacancy": { "scope_type": ..., "seniority": ..., "role_title": ..., "team_context": ..., "evidence": [...] },
  "role_expectations": { "responsibilities": [...], "requirements": [...], "preferred": [...], "tech_stack": [...] }
}
"""
```

- **비용**: JD 1건당 ~2,500-3,500 토큰 (입력 + 출력)
- **모델**: Claude Haiku 4.5 / Gemini Flash 2.0 (비용 효율)
- **Rule 불가 이유**: scope_type 판별은 문맥 해석이 필수
- **tech_stack 후처리**: LLM 추출 후 기술 사전으로 정규화

### 2.4 operating_model — 키워드 + LLM 보정

```python
def extract_operating_model(jd_text):
    """v4의 키워드 카운트 + LLM 보정"""
    facets = {}
    for facet_name, keywords in FACET_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw.lower() in jd_text.lower())
        keyword_score = min(count / 5.0, 1.0)

        if count >= 2:
            # 키워드가 충분하면 LLM 보정으로 광고성 필터링
            llm_adj = llm_assess_authenticity(jd_text, facet_name, count)
            score = keyword_score * llm_adj
            confidence = min(0.60, 0.30 + count * 0.06)
        else:
            score = keyword_score
            confidence = max(0.20, count * 0.10)

        facets[facet_name] = {"score": score, "confidence": confidence}
    return facets
```

- **비용**: 키워드 카운트는 무료, LLM 보정은 선택적 (~500 토큰)
- **LLM 호출 조건**: 키워드 2개 이상 탐지 시만 보정 호출

### CompanyContext 생성 비용 요약 (1건당)

| 필드 | 방법 | 토큰 (입출력) | 비용 (Haiku 일반) | 비용 (Haiku Batch 50%) |
|---|---|---|---|---|
| company_profile | NICE Lookup | 0 | $0 | $0 |
| stage_estimate | Rule (80%) / LLM (20%) | 평균 ~100 | ~$0.00002 | ~$0.00001 |
| vacancy + role_expectations | LLM (통합 프롬프트) | ~3,000 | ~$0.0006 | ~$0.0003 |
| operating_model | 키워드 + LLM 보정 | ~800 | ~$0.00016 | ~$0.00008 |
| **합계** | | **~3,900** | **~$0.0008** | **~$0.0004** |

> **참고**: 대량 처리 시 Batch API(50% 할인) 적용을 권장. 03 문서의 시나리오별 비용은 Batch 가격 기준.

---

## 3. Pipeline B: CandidateContext 생성

### 입력
- 이력서 텍스트 (candidate_id 단위)
- NICE 기업 정보 (회사명 기반 조회)

### 3.1 전처리: 이력서 파싱

v1의 PDF/HWP 파싱은 그대로 유효하지만, 출력 형식을 v4에 맞춘다.

```
[이력서 원본]
    │
    ├─ PDF → PyMuPDF / pdfplumber
    ├─ DOCX → python-docx
    ├─ HWP → python-hwp / LibreOffice headless
    │
    ▼
[텍스트 + 레이아웃]
    │
    ├─[Rule] 섹션 분할 (경력, 학력, 기술, 프로젝트)
    ├─[Rule] 경력 블록 분리 (회사별 단위)
    └─[Rule] 기본 정보 추출 (이름, 연락처)
```

### 3.2 Experience 추출 — Rule + LLM 계층

#### Step 1: Rule 추출 (비용 0)

```python
def rule_extract_experience(block_text):
    """경력 블록에서 정형 필드 추출"""
    return {
        "company": extract_company_name(block_text),  # 패턴 매칭
        "role_title": extract_role_title(block_text),  # 패턴 매칭
        "period": extract_period(block_text),           # 날짜 regex
        "tech_stack": match_tech_dictionary(block_text), # 기술 사전
    }
```

**주요 정규식 패턴 예시**:

```python
# 회사명 추출 패턴 (한국어 이력서)
COMPANY_PATTERNS = [
    # "㈜카카오", "(주)네이버", "주식회사 라인"
    r'[㈜\(주\)]\s*([가-힣A-Za-z0-9]+)',
    r'주식회사\s+([가-힣A-Za-z0-9]+)',
    # "카카오 | 백엔드 개발자", "네이버 / 시니어 엔지니어"
    r'^([가-힣A-Za-z0-9\s]+?)\s*[|/·]\s*(.+?)$',
    # "카카오 (2020.03 ~ 2023.06)"
    r'^([가-힣A-Za-z0-9\s]+?)\s*[\(（]\s*\d{4}',
]

# 기간 추출 패턴
PERIOD_PATTERNS = [
    # "2020.03 ~ 2023.06", "2020-03 - 2023-06"
    r'(\d{4})[.\-/](\d{1,2})\s*[~\-–]\s*(\d{4})[.\-/](\d{1,2})',
    # "2020.03 ~ 현재", "2020-03 - 재직중"
    r'(\d{4})[.\-/](\d{1,2})\s*[~\-–]\s*(현재|재직중|Present)',
    # "2020년 3월 ~ 2023년 6월"
    r'(\d{4})년\s*(\d{1,2})월\s*[~\-–]\s*(\d{4})년\s*(\d{1,2})월',
]

# 직무명 추출 패턴
ROLE_PATTERNS = [
    # "백엔드 개발자", "시니어 엔지니어", "프론트엔드 리드"
    r'(시니어|주니어|리드|수석|책임|선임)?\s*([\w]+\s*(개발자|엔지니어|디자이너|매니저|PM|PO|리드))',
    # "CTO", "VP of Engineering"
    r'\b(CTO|CEO|VP|Director|Manager|Lead|Senior|Staff)\b',
]
```

- company, role_title: 경력 블록 첫 줄의 패턴으로 60-70% 커버
- period: 날짜 regex로 80-90% 커버
- tech_stack: 기술 사전 fuzzy matching으로 70-80% 커버

#### Step 2: LLM 추출 (Experience별, 핵심)

```python
EXPERIENCE_PROMPT = """
아래 경력 텍스트에서 다음을 추출하세요.

[필수 추출 항목]
1. scope_type: IC / LEAD / HEAD / FOUNDER / UNKNOWN
   - IC: 개인 기여자, 팀원
   - LEAD: 팀 리드, 테크 리드 (3~20명 관리)
   - HEAD: 부서장, CTO (20명+ 관리)
   - FOUNDER: 창업자
2. scope_summary: 역할 범위 한 문장 요약
3. outcomes: 정량/정성 성과 목록
   - 각 outcome에: description, outcome_type(METRIC/SCALE/DELIVERY/ORGANIZATIONAL),
     quantitative(bool), metric_value(수치 있으면)
4. situational_signals: 아래 taxonomy에서 해당하는 것만 선택
   [Taxonomy: EARLY_STAGE, SCALE_UP, TURNAROUND, GLOBAL_EXPANSION,
    TEAM_BUILDING, TEAM_SCALING, REORG, LEGACY_MODERNIZATION,
    NEW_SYSTEM_BUILD, TECH_STACK_TRANSITION, PMF_SEARCH,
    MONETIZATION, ENTERPRISE_TRANSITION, OTHER]
   - 각 signal에: label, description, evidence_span(원문 인용), confidence

[규칙]
- 근거 없이 추론하지 마세요. 인용할 수 없으면 해당 항목을 생성하지 마세요.
- confidence: 0.0~1.0

[경력 텍스트]
{experience_block}

[기본 정보 (Rule에서 추출)]
{basic_info_block}

[출력 JSON]
"""

# Rule 추출 결과에 따른 프롬프트 분기
def build_basic_info_block(basic):
    """Rule 추출 성공/실패에 따라 프롬프트 컨텍스트를 조정"""
    parts = []
    if basic.company:
        parts.append(f"회사: {basic.company}")
    if basic.role_title:
        parts.append(f"직무: {basic.role_title}")
    if basic.period:
        parts.append(f"기간: {basic.period}")

    if not parts:
        # Rule 추출 전체 실패 → LLM에 기본 필드도 함께 추출 요청
        return (
            "※ 기본 정보를 자동 추출하지 못했습니다.\n"
            "위 경력 텍스트에서 회사명, 직무명, 근무 기간도 함께 추출하세요."
        )
    elif len(parts) < 3:
        # 부분 실패 → 누락 필드만 추가 추출 요청
        missing = []
        if not basic.company: missing.append("회사명")
        if not basic.role_title: missing.append("직무명")
        if not basic.period: missing.append("근무 기간")
        return "\n".join(parts) + f"\n※ 다음 항목은 자동 추출 실패. 텍스트에서 추출하세요: {', '.join(missing)}"
    else:
        return "\n".join(parts)
```

- **비용**: Experience 1건당 ~2,000-3,500 토큰 (Rule 전체 실패 시 +500 토큰)
- **평균 이력서**: 경력 2-4개 → **이력서 1건당 ~6,000-12,000 토큰**
- **모델**: Claude Haiku 4.5 / Gemini Flash 2.0

#### Step 3: NICE Lookup — PastCompanyContext (비용 0)

```python
def build_past_company_context(company_name, tenure_start, tenure_end):
    """v4 02_candidate_context.md의 로직 그대로"""
    nice = lookup_nice(company_name)
    if not nice:
        return None  # NICE에 없는 회사

    years_gap = 2026 - tenure_end.year
    confidence = max(0.20, 0.60 - years_gap * 0.08)

    return PastCompanyContext(
        company_name=company_name,
        industry_code=nice.industry_code,
        employee_count=nice.employee_count,
        founded_year=nice.founded_year,
        stage_estimation_method="nice_current",
        confidence=confidence,
        ...
    )
```

### 3.3 전체 커리어 수준 추출 — LLM (1회)

```python
CAREER_LEVEL_PROMPT = """
아래 후보의 전체 경력 요약을 분석하여 추출하세요.

[추출 항목]
1. role_evolution:
   - pattern: IC_TO_LEAD / IC_DEPTH / LEAD_TO_HEAD / FOUNDER / GENERALIST / DOWNSHIFT / LATERAL / UNKNOWN
   - description: 커리어 패턴 서술
   - total_experience_years: 총 경력 연수
2. domain_depth:
   - primary_domain: 주요 도메인
   - domain_experience_count: 해당 도메인 회사 수
   - description: 도메인 경험 서술
3. work_style_signals (있을 때만):
   - autonomy_preference: HIGH / MID / LOW / null
   - process_tolerance: HIGH / MID / LOW / null

[전체 경력]
{all_experiences_summary}

[출력 JSON]
"""
```

- **비용**: 이력서 1건당 ~2,000-3,000 토큰 (전체 경력 요약 1회)

### CandidateContext 생성 비용 요약 (이력서 1건당)

| 추출 단계 | 방법 | 토큰 (입출력) | 비용 (Haiku 일반) | 비용 (Haiku Batch 50%) |
|---|---|---|---|---|
| 전처리 (파싱, 섹션분할) | Rule | 0 | $0 | $0 |
| 기본 필드 (회사/직무/기간/기술) | Rule | 0 | $0 | $0 |
| Experience별 추출 (×3 평균) | LLM | ~9,000 | ~$0.0018 | ~$0.0009 |
| PastCompanyContext (×3) | NICE Lookup | 0 | $0 | $0 |
| 전체 커리어 (role_evolution 등) | LLM | ~2,500 | ~$0.0005 | ~$0.00025 |
| **합계** | | **~11,500** | **~$0.0023** | **~$0.00115** |

> **참고**: 대량 처리 시 Batch API(50% 할인) 적용을 권장. 03 문서의 시나리오별 비용은 Batch 가격 기준.

---

## 4. Pipeline C: Graph 적재

### 4.1 CompanyContext → Graph

```python
def load_company_to_graph(company_ctx, tx):
    """CompanyContext JSON → Neo4j 노드/엣지"""
    # Organization 노드
    tx.run("""
        MERGE (o:Organization {org_id: $org_id})
        SET o.name = $name, o.industry_code = $industry_code,
            o.stage_label = $stage_label, ...
    """, company_ctx.company_profile)

    # Vacancy 노드
    tx.run("""
        CREATE (v:Vacancy {vacancy_id: $job_id, scope_type: $scope_type, ...})
    """, company_ctx.vacancy)

    # Organization -[:HAS_VACANCY]-> Vacancy
    tx.run("""
        MATCH (o:Organization {org_id: $org_id})
        MATCH (v:Vacancy {vacancy_id: $job_id})
        CREATE (o)-[:HAS_VACANCY {posted_at: datetime()}]->(v)
    """)

    # Vacancy -[:REQUIRES_SKILL]-> Skill (tech_stack에서)
    for skill in company_ctx.role_expectations.tech_stack:
        tx.run("""
            MERGE (s:Skill {name: $name})
            MATCH (v:Vacancy {vacancy_id: $job_id})
            CREATE (v)-[:REQUIRES_SKILL]->(s)
        """, name=normalize_skill(skill))

    # Vacancy -[:NEEDS_SIGNAL]-> SituationalSignal (추론)
    signals = infer_vacancy_signals(company_ctx.vacancy)
    for signal_label in signals:
        tx.run("""
            MERGE (sig:SituationalSignal {label: $label})
            MATCH (v:Vacancy {vacancy_id: $job_id})
            CREATE (v)-[:NEEDS_SIGNAL {inferred: true}]->(sig)
        """, label=signal_label)
```

### 4.2 CandidateContext → Graph

```python
def load_candidate_to_graph(candidate_ctx, tx):
    """CandidateContext JSON → Neo4j 노드/엣지"""
    # Person 노드
    tx.run("""
        MERGE (p:Person {person_id: $candidate_id})
        SET p.role_evolution_pattern = $pattern, ...
    """)

    for i, exp in enumerate(candidate_ctx.experiences):
        # Chapter 노드
        tx.run("""
            CREATE (ch:Chapter {chapter_id: $exp_id, scope_type: $scope_type, ...})
        """)

        # Person -[:HAS_CHAPTER]-> Chapter
        tx.run("""
            MATCH (p:Person {person_id: $candidate_id})
            MATCH (ch:Chapter {chapter_id: $exp_id})
            CREATE (p)-[:HAS_CHAPTER {order: $order}]->(ch)
        """, candidate_id=candidate_ctx.candidate_id, exp_id=exp.exp_id, order=i)

        # Chapter -[:OCCURRED_AT]-> Organization
        # v4 변경: name이 아닌 org_id로 MERGE (§4.1과 통일)
        if exp.company:
            org_id = resolve_org_id(exp.company)  # Entity Resolution: 회사명 → org_id 매핑
            if org_id:
                tx.run("""
                    MERGE (o:Organization {org_id: $org_id})
                    SET o.name = COALESCE(o.name, $company_name)
                    WITH o
                    MATCH (ch:Chapter {chapter_id: $exp_id})
                    CREATE (ch)-[:OCCURRED_AT {start: $start, end: $end}]->(o)
                """, org_id=org_id, company_name=exp.company,
                    exp_id=exp.exp_id, start=exp.period_start, end=exp.period_end)
            else:
                # NICE/사전에 없는 회사 → name 기반 MERGE (fallback)
                tx.run("""
                    MERGE (o:Organization {name: $company_name})
                    WITH o
                    MATCH (ch:Chapter {chapter_id: $exp_id})
                    CREATE (ch)-[:OCCURRED_AT {start: $start, end: $end}]->(o)
                """, company_name=exp.company, exp_id=exp.exp_id,
                    start=exp.period_start, end=exp.period_end)

        # Chapter -[:PERFORMED_ROLE]-> Role
        if exp.role_title:
            tx.run("""
                MERGE (r:Role {name: $role_name})
                MATCH (ch:Chapter {chapter_id: $exp_id})
                CREATE (ch)-[:PERFORMED_ROLE]->(r)
            """, role_name=normalize_role(exp.role_title), exp_id=exp.exp_id)

        # Chapter -[:USED_SKILL]-> Skill
        for skill in exp.tech_stack or []:
            tx.run("""
                MERGE (s:Skill {name: $name})
                MATCH (ch:Chapter {chapter_id: $exp_id})
                CREATE (ch)-[:USED_SKILL]->(s)
            """, name=normalize_skill(skill), exp_id=exp.exp_id)

        # Chapter -[:PRODUCED_OUTCOME]-> Outcome
        for outcome in exp.outcomes or []:
            tx.run("""
                CREATE (out:Outcome {
                    description: $desc, outcome_type: $type,
                    quantitative: $quant, metric_value: $metric
                })
                WITH out
                MATCH (ch:Chapter {chapter_id: $exp_id})
                CREATE (ch)-[:PRODUCED_OUTCOME]->(out)
            """, desc=outcome.description, type=outcome.outcome_type,
                quant=outcome.quantitative, metric=outcome.metric_value,
                exp_id=exp.exp_id)

        # Chapter -[:HAS_SIGNAL]-> SituationalSignal (공유 노드)
        for signal in exp.situational_signals or []:
            tx.run("""
                MERGE (sig:SituationalSignal {label: $label})
                MATCH (ch:Chapter {chapter_id: $exp_id})
                CREATE (ch)-[:HAS_SIGNAL {confidence: $conf}]->(sig)
            """, label=signal.label, exp_id=exp.exp_id, conf=signal.confidence)

    # Chapter -[:NEXT_CHAPTER]-> Chapter (시간순)
    sorted_exps = sorted(candidate_ctx.experiences, key=lambda e: e.period_start)
    for i in range(len(sorted_exps) - 1):
        tx.run("""
            MATCH (c1:Chapter {chapter_id: $id1})
            MATCH (c2:Chapter {chapter_id: $id2})
            CREATE (c1)-[:NEXT_CHAPTER]->(c2)
        """, id1=sorted_exps[i].exp_id, id2=sorted_exps[i+1].exp_id)
```

### 4.3 Organization Entity Resolution

> **v4 신설**: v3 리뷰에서 지적된 Organization MERGE 전략 불일치를 해결.

```python
def resolve_org_id(company_name: str) -> Optional[str]:
    """회사명 → org_id 매핑. NICE DB + 회사명 정규화 사전 활용."""
    # Step 1: 정규화 사전 조회 (alias → canonical name → org_id)
    canonical = COMPANY_ALIAS_DICT.get(normalize_company_name(company_name))
    if canonical:
        return canonical.org_id

    # Step 2: NICE DB 직접 조회 (fuzzy match)
    nice = lookup_nice_fuzzy(company_name, threshold=0.85)
    if nice:
        return nice.org_id

    # Step 3: 매칭 실패 → None (fallback: name 기반 MERGE)
    return None
```

**정규화 사전 구축**:
- KOSPI/KOSDAQ 상장사 + NICE 등록 기업에서 자동 생성 (~1,000개)
- "카카오" / "주식회사 카카오" / "(주)카카오" / "카카오엔터프라이즈" 등 alias 수동 추가
- Phase 1-4에서 구축, 이후 증분 갱신

### 4.4 Graph 적재 전략: 초기 vs 증분

> **v4 신설**: v3 리뷰에서 지적된 대량 적재 전략 부재를 보강.

#### 초기 적재 (Phase 2-1, 500K 전체)

AuraDB 관리형 환경에서 대량 적재 시:

```
[초기 적재 전략]
1. Context JSON → CSV 변환 (노드별, 엣지별 파일 분리)
   ├─ nodes_person.csv, nodes_chapter.csv, nodes_organization.csv, ...
   └─ edges_has_chapter.csv, edges_occurred_at.csv, ...

2. Neo4j LOAD CSV + APOC batch 활용
   ├─ USING PERIODIC COMMIT 500
   ├─ CALL apoc.periodic.iterate(...)로 대량 MERGE
   └─ 인덱스는 적재 후 빌드 (적재 중 인덱스 비활성화)

3. Vector Index 적재 (embedding 별도 배치)
   ├─ Chapter embedding: 150만 건
   ├─ Vacancy embedding: 1만 건
   └─ HNSW 인덱스 빌드: ~2~4시간 (150만 벡터)

예상 적재 시간: CSV 변환 4~6시간 + LOAD CSV 8~12시간 + Vector 2~4시간 = ~1~2일
```

#### 증분 적재 (운영 단계)

- 일일 신규/갱신 건만 Cypher MERGE로 처리
- 예상 일일 처리량: 100~1,000건 → ~수 분 이내
- 트랜잭션 배치: 100건/TX

### 4.5 Vector Index

> **v4 변경**: embedding 대상 텍스트를 명확히 정의.

```python
# Chapter embedding — scope_summary + outcomes 요약 텍스트
def build_chapter_embedding_text(chapter):
    """Vector search에 사용할 Chapter 요약 텍스트 생성"""
    parts = []
    if chapter.scope_summary:
        parts.append(chapter.scope_summary)
    for outcome in chapter.outcomes or []:
        parts.append(outcome.description)
    for signal in chapter.situational_signals or []:
        parts.append(f"{signal.label}: {signal.description}")
    return " ".join(parts)

for chapter in chapters:
    embed_text = build_chapter_embedding_text(chapter)
    embedding = embed_model.encode(embed_text)
    tx.run("""
        MATCH (ch:Chapter {chapter_id: $id})
        SET ch.embedding_text = $text, ch.embedding = $emb
    """, id=chapter.chapter_id, text=embed_text, emb=embedding)

# Vacancy embedding — vacancy scope_type + responsibilities 요약
def build_vacancy_embedding_text(vacancy, role_exp):
    parts = [f"scope: {vacancy.scope_type}"]
    parts.extend(role_exp.responsibilities or [])
    return " ".join(parts)

vacancy_text = build_vacancy_embedding_text(vacancy, role_expectations)
vacancy_emb = embed_model.encode(vacancy_text)
```

- **Embedding 모델**: Phase 0 PoC에서 3개 모델 비교 후 결정 (03 문서 참조)
  - 후보: text-embedding-3-small ($0.02/1M) / Cohere embed-multilingual-v3.0 ($0.10/1M) / BGE-M3 (자체 호스팅)

---

## 5. Pipeline D: MappingFeatures 계산

MappingFeatures는 v4 `03_mapping_features.md`의 로직을 그대로 구현한다.
이 단계에서는 **LLM을 사용하지 않는다** (Rule + Embedding만).

### 5.0 Candidate Shortlisting — 매핑 대상 후보 선정

> **v4 신설**: v3에서 "상위 500명"의 선정 기준이 미정의였던 점을 보강.

전수 매핑(500K × 10K = 50억 쌍)은 비현실적이므로, JD별 **상위 후보 500명**을 사전 선정한다.

#### 선정 방법 (2단계 필터)

```python
def shortlist_candidates(vacancy, all_candidates, top_k=500):
    """JD별 상위 후보 선정. Rule pre-filter → Embedding ANN 순서."""
    # Stage 1: Rule pre-filter (비용 0)
    # — industry, tech_stack 교집합, 경력연수 범위로 대상 축소
    filtered = [c for c in all_candidates if passes_rule_filter(vacancy, c)]
    # 예상 축소율: 500K → 5K~50K (industry + 경력연수 필터)

    # Stage 2: Embedding ANN (Vector Search)
    # — Vacancy embedding과 Chapter embedding의 cosine similarity top-K
    vacancy_emb = get_vacancy_embedding(vacancy.vacancy_id)
    results = vector_index.search(vacancy_emb, candidates=filtered, top_k=top_k)
    return results
```

#### 인프라

- **Rule pre-filter**: BigQuery SQL 또는 in-memory 필터링 (추가 인프라 불필요)
- **Embedding ANN**: Neo4j Vector Index (`db.index.vector.queryNodes`) 활용 — 별도 ANN 서비스 불필요
- **비용**: 사실상 $0 (Neo4j Vector Index가 이미 Pipeline C에서 구축됨)

#### 범위 결정

> Candidate Shortlisting은 KG 구축(create-kg)의 최종 단계이자, 서빙 시스템의 시작점이다.
> v1 MVP에서는 **배치 방식**으로 사전 계산하여 BigQuery에 적재하고,
> 실시간 Shortlisting은 Phase 3(서빙 API)에서 구현한다.

### 5.1 계산 비용

| 피처 | 방법 | 비용 |
|---|---|---|
| stage_match | Rule (lookup table) | 0 |
| vacancy_fit | Rule (signal alignment table, 아래 참조) | 0 |
| domain_fit | Embedding cosine similarity | ~0.00001/건 |
| culture_fit | Rule (facet 비교) — 대부분 INACTIVE | 0 |
| role_fit | Rule (pattern matching) | 0 |
| **합계** | | **~$0.00001/매핑** |

#### vacancy_fit Signal Alignment Table 구축 방법

vacancy_fit은 Vacancy의 `scope_type`이 요구하는 상황과 후보의 `situational_signals` 보유 여부를 매칭한다.
이 매핑 테이블은 **수동 설계(도메인 전문가)**이며, v4 온톨로지의 비즈니스 로직에 기반한다.

```python
# 수동 설계된 정적 매핑 테이블 (v4 03_mapping_features.md 기반)
VACANCY_SIGNAL_ALIGNMENT = {
    "BUILD_NEW":       ["NEW_SYSTEM_BUILD", "EARLY_STAGE", "PMF_SEARCH", "TEAM_BUILDING"],
    "SCALE_EXISTING":  ["SCALE_UP", "TEAM_SCALING", "MONETIZATION"],
    "RESET":           ["TURNAROUND", "LEGACY_MODERNIZATION", "TECH_STACK_TRANSITION", "REORG"],
    "REPLACE":         [],  # 충원은 특별한 signal alignment 없음
}

def compute_vacancy_fit(vacancy_scope_type, candidate_signals):
    """Vacancy scope_type에 해당하는 signal을 후보가 보유하는지 룩업"""
    required = VACANCY_SIGNAL_ALIGNMENT.get(vacancy_scope_type, [])
    if not required:
        return {"score": 0.5, "status": "INACTIVE", "reason": "no_alignment_defined"}
    matched = [s for s in candidate_signals if s.label in required]
    score = len(matched) / len(required)
    return {"score": score, "status": "ACTIVE", "matched_signals": matched}
```

> **참고**: 이 테이블은 Phase 2 품질 평가에서 실제 매칭 효과를 검증한 후 조정한다.
> 현재는 v4 온톨로지 설계자의 도메인 지식에 기반한 초기 버전이다.

---

## 6. 처리 볼륨과 총비용 추정

### 가정 (가상 — 실제 데이터 확인 필요)

| 항목 | 가정값 | 근거 |
|---|---|---|
| JD 보유량 | 10,000건 | 자사 보유 + 크롤링 |
| 이력서 보유량 | 500,000건 | 150GB ÷ 이력서 평균 300KB |
| 이력서당 평균 경력 수 | 3건 | 경력직 기준 |
| 매핑 대상 쌍 | 5,000,000건 | JD × 상위 후보 500명 |

### 비용 산출

| 파이프라인 | 건수 | 건당 비용 | 총비용 |
|---|---|---|---|
| CompanyContext 생성 | 10,000 | $0.0008 | **$8** |
| CandidateContext 생성 | 500,000 | $0.0023 | **$1,150** |
| Graph 적재 | 510,000 | ~0 (compute) | 인프라 비용 |
| Embedding (Vector Index) | 1,500,000 chapters | $0.00002 | **$30** |
| MappingFeatures 계산 | 5,000,000 | $0.00001 | **$50** |
| **LLM 총비용** | | | **~$1,238** |

**원화 환산**: ~170만 원 (Haiku 기준, 2026-03 환율 1,370원/$)

### Sonnet 사용 시 비용 비교

| 모델 | CandidateContext 비용 | 총 LLM 비용 | 원화 |
|---|---|---|---|
| Claude Haiku 4.5 | $1,150 | ~$1,238 | ~170만 원 |
| Gemini 2.0 Flash | $875 | ~$950 | ~130만 원 |
| Claude Sonnet 4.6 | $5,750 | ~$5,838 | ~800만 원 |
| GPT-4o-mini | $1,725 | ~$1,813 | ~250만 원 |
| GPT-4o | $28,750 | ~$28,838 | ~3,950만 원 |

> **권장**: v1 MVP에서는 Haiku/Flash급으로 시작하고, 추출 품질 평가 후 필요 시 Sonnet급으로 업그레이드

---

## 7. v1 하이브리드 비율 재정의

### 이력서(CandidateContext) 추출 기준

| 추출 대상 | Rule | LLM | 비고 |
|---|---|---|---|
| company, role_title, period | **70%** | 30% fallback | 블록 패턴 커버리지 |
| tech_stack | **75%** | 25% (LLM에서 추가 발견) | 기술 사전 기반 |
| scope_type | 0% | **100%** | 문맥 해석 필수 |
| outcomes | 0% | **100%** | 성과 추출은 LLM만 가능 |
| situational_signals | 0% | **100%** | taxonomy 분류 = LLM |
| past_company_context | **100%** | 0% | NICE Lookup |
| role_evolution | 0% | **100%** | 전체 커리어 추론 |
| domain_depth | 0% | **100%** | 도메인 판별 = LLM |

**전체 가중 비율**: Rule ~25%, LLM ~75% (필드 중요도 가중)

### JD(CompanyContext) 추출 기준

| 추출 대상 | Rule | LLM | 비고 |
|---|---|---|---|
| company_profile | **100%** | 0% | NICE Lookup |
| stage_estimate | **75%** | 25% | Rule 우선, LLM fallback |
| vacancy + role_expectations | 0% | **100%** | 문맥 해석 필수 (통합 프롬프트) |
| operating_model | **40%** (키워드) | 60% (보정) | 하이브리드 |

---

## 8. 에러 핸들링 및 배치 처리 전략

> **v3 신설**: v2 리뷰에서 지적된 에러 핸들링 부재, 배치 아키텍처 미상세를 보강.

### 8.1 에러 유형별 처리 정책

| 에러 유형 | 원인 | 정책 | 최대 재시도 | 비고 |
|---|---|---|---|---|
| **LLM API 호출 실패** | 네트워크, 서버 에러 (5xx) | **재시도** (exponential backoff) | 3회 | 1초 → 2초 → 4초 |
| **LLM API Rate Limit** | 429 Too Many Requests | **대기 후 재시도** (Retry-After 헤더) | 5회 | Batch API 사용 시 거의 없음 |
| **LLM 응답 파싱 실패** | JSON 형식 오류 | **재시도** (temperature 0.1 상향) | 2회 | 2회 실패 시 skip + 로그 |
| **LLM 응답 스키마 불일치** | 필수 필드 누락 | **부분 수용** (있는 필드만 사용) | 0 | null로 graceful degradation |
| **NICE DB 타임아웃** | DB 부하, 네트워크 | **재시도** | 3회 | 실패 시 past_company_context = null |
| **NICE DB 매칭 실패** | 회사명 미등록 | **skip** (graceful degradation) | 0 | 정상 케이스로 처리 |
| **이력서 파싱 실패** | 손상된 파일, 미지원 형식 | **skip + 로그** | 0 | dead-letter 큐로 이동 |
| **Graph 적재 실패** | Neo4j 연결 문제, 제약 조건 위반 | **재시도** (트랜잭션 롤백 후) | 3회 | 실패 시 skip + 로그 |

### 8.2 evidence_span 후처리 검증

> **v4 신설**: LLM이 원문에 없는 span을 생성(hallucination)하는 케이스를 방지.

```python
def validate_evidence_spans(extraction_result, original_text):
    """LLM 추출 결과의 evidence_span이 원문에 실제로 존재하는지 검증"""
    for field_name, field_value in extraction_result.items():
        if hasattr(field_value, 'evidence_span') and field_value.evidence_span:
            span = field_value.evidence_span
            if span not in original_text:
                # span이 원문에 없음 → confidence 하향
                field_value.confidence *= 0.5
                field_value.evidence_span_verified = False
                logger.warning(f"evidence_span not found in original: {span[:50]}...")
            else:
                field_value.evidence_span_verified = True
```

- **비용**: 0 (문자열 포함 검사만)
- **예상 hallucination 비율**: 5~15% (Phase 0 PoC에서 실측)
- **정책**: span 미검증 건은 추출 결과를 유지하되 confidence를 50% 감쇄

### 8.3 Dead-Letter 큐 및 재처리

```python
class DeadLetterHandler:
    """처리 실패 건을 별도 관리하여 이후 수동/자동 재처리"""
    def handle_failure(self, item_id, pipeline, error_type, error_msg):
        self.dead_letter_store.save({
            "item_id": item_id,
            "pipeline": pipeline,      # "company_context" / "candidate_context"
            "error_type": error_type,   # "parse_fail" / "llm_fail" / "graph_fail"
            "error_message": error_msg,
            "failed_at": datetime.utcnow(),
            "retry_count": 0,
            "status": "PENDING"         # PENDING → RETRYING → RESOLVED / SKIPPED
        })
```

- **에러율 가정**: 전체 처리 중 2-5% 실패 예상
- **재처리 주기**: 일 1회 dead-letter 큐 자동 재시도 → 2회 실패 시 수동 검토 전환

### 8.4 배치 처리 / 병렬 설계 (500K 이력서)

```
[Batch Processing Architecture]

이력서 500K
    │
    ├─ Chunk 분할 (1,000건/chunk × 500 chunks)
    │
    ├─ Batch API 요청 (chunk 단위)
    │   ├─ Anthropic Batch API: 최대 10,000건/batch, 24시간 SLA
    │   ├─ 동시 배치 수: 5~10개 (API quota에 따라 조정)
    │   └─ 예상 처리 시간: 2~3일 (500K ÷ 50K/일)
    │
    ├─ 결과 수집 + 파싱
    │   ├─ 성공: CandidateContext JSON → Graph 적재 큐
    │   └─ 실패: Dead-Letter 큐
    │
    └─ Graph 적재 (비동기, 병렬 worker 4~8개)
        ├─ Neo4j Transaction 배치: 100건/트랜잭션
        └─ 예상 적재 시간: 1~2일
```

**처리 오케스트레이션**: Cloud Workflows (GCP) 또는 Prefect (셀프 호스팅) 권장
- 단계 간 의존성 관리 (파싱 → LLM 추출 → Graph 적재)
- 재시도/실패 알림/진행률 모니터링 내장

---

## 9. ML Knowledge Distillation 적용 범위 (요약)

> **상세 실행 계획은 `04_execution_plan.md` Phase 2-3 참조**

v1의 "LLM Teacher → ML Student" 전략은 v4에서도 유효하지만 **적용 범위가 제한적**이다.

- **ML 대체 가능**: scope_type 분류, seniority 분류 (KLUE-BERT 기반, Phase 2 선택적)
- **ML 대체 불가**: outcomes 추출, situational_signals, vacancy scope_type, role_evolution, operating_model 보정
- **비용 절감 효과**: 이력서 1건당 LLM 토큰 22% 감소, 500K 기준 약 $250 절감 (Batch 기준)

**결론**: ML Distillation은 v4에서 **20-30% 수준**의 비용 절감만 가능. LLM 비용 최적화(모델 선택, Batch API)가 더 큰 영향을 미친다.
