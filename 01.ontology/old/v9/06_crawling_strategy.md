# 기업 크롤링 전략 및 실행 계획

> v4 CompanyContext의 T3(홈페이지 크롤링) / T4(뉴스 크롤링) 소스에서
> **무엇을 수집하고, 어떻게 추출하며, 어떤 필드를 보강하는지**에 대한 상세 정의와 실행 계획.
>
> 작성일: 2026-03-08 | 기준: v4 CompanyContext (01_company_context.md)
>
> **v1.1 동기화** (2026-03-08): GCP 구현 계획(`crawling-gcp-plan.md`)과 정합성 맞춤
> - LLM: GPT-4o-mini -> Gemini 2.0 Flash (GCP Vertex AI 네이티브)
> - 최대 페이지 수: 20 -> 10 (Cloud Run Job 타임아웃 정합)
> - N6(기술/제품 전략): v2로 이동 (N2와 중복도 높음)
> - GCS 버킷: 기존 프로젝트 버킷(`gs://ml-api-test-vertex/crawl/`) 재사용
> - 뉴스 수집: 네이버 API 본문 미제공 사실 반영 (link 추가 크롤링)
>
> **v6 반영** (2026-03-08): v5 리뷰 피드백 반영
> - [C-1] P2(제품), P3(채용) 추출 프롬프트 추가
> - [C-2] N4(조직변화) 추출 프롬프트에 A6 taxonomy 연동
> - [C-3] 한국어 URL 패턴 딕셔너리 및 URL 발견 우선순위 명시
> - [S-1] `is_actionable_signal` 로직 개선 (운영 컨텍스트 검증 추가)
> - [S-3] 카테고리별 confidence ceiling 차등 적용
> - [C-5] evidence source_id 네이밍 컨벤션 확정
> - [C-6] 재크롤링 시 해시 기반 변경 감지 증분 전략 추가
> - [D-1] BigQuery 테이블 간 데이터 플로우 정의
> - [D-2] 크롤링 데이터의 Graph 반영 스키마 확장 정의
> - [D-3] facet score 병합 규칙 확정
>
> **v7 반영** (2026-03-08): v6 리뷰 잔여 권장사항 8건 + 추가 개선 1건 반영
> - [C6-3] facet 병합 threshold 0.20 캘리브레이션 4단계 절차 추가
> - [S-4] 짧은 기사 관련성 필터 -- 본문 길이 적응형 기준으로 교체
> - [S-5] 중복 제거 임계값 -- 2단계 클러스터링(제목 유사도 + 핵심 엔티티)으로 교체
> - [C6-1, C6-2] P4~P6, N2/N3/N5 프롬프트 추가를 실행 계획 태스크로 반영
> - HTML 해시 vs 텍스트 해시 -- A/B 검증 계획 및 `text_hash` 컬럼 추가
> - [C6-4] 서브도메인 탐색 스킵 조건 추가
> - 집계 Job 트리거 방식 -- Eventarc(Primary) + Cloud Scheduler(Backup) 이중 구조
> - 실행 계획 Phase 1~4에 v7 검증 태스크 추가
>
> **v9 반영** (2026-03-08): v8 리뷰 피드백 반영
> - [E-1] A6 참조 경로를 `01_company_context.md 2.2절`로 변경 (A6 이관 완료 반영)

---

## 1. 크롤링이 해결하는 문제

v4 CompanyContext에서 JD + NICE만으로는 채울 수 없거나 confidence가 낮은 필드들이 존재한다.

| CompanyContext 필드 | JD+NICE만 사용 시 | 크롤링 추가 시 |
|---|---|---|
| `stage_estimate` | confidence 0.50~0.65 | 뉴스(투자 기사)로 0.70~0.80 |
| `domain_positioning.market_segment` | confidence 0.40~0.60 | 홈페이지로 0.55~0.70 |
| `domain_positioning.product_description` | **null** | 홈페이지로 활성화 |
| `domain_positioning.competitive_landscape` | **null** | 뉴스로 활성화 |
| `structural_tensions` | **null (70%+)** | 뉴스로 30~50% 활성화 |
| `operating_model.narrative_summary` | **null** | 홈페이지+뉴스로 활성화 |
| `operating_model.facets` (3개) | confidence 0.30~0.45 | 홈페이지로 0.40~0.60 |

---

## 2. T3 -- 회사 홈페이지 크롤링

### 2.1 수집 대상 페이지 유형

모든 페이지를 크롤링하는 것이 아니라, **CompanyContext에 기여하는 페이지 유형만 타겟팅**한다.

| # | 페이지 유형 | URL 패턴 (일반적) | 수집 우선순위 | 기여 필드 |
|---|---|---|---|---|
| P1 | **회사 소개 (About)** | `/about`, `/company`, `/about-us` | 필수 | product_description, market_segment, narrative_summary |
| P2 | **제품/서비스 소개** | `/product`, `/service`, `/solution`, `/features` | 필수 | product_description, market_segment, tech 힌트 |
| P3 | **채용 페이지** | `/careers`, `/jobs`, `/recruit`, `/채용` | 필수 | operating_model facets, team_context, narrative_summary |
| P4 | **기술 블로그** | `/blog`, `/tech-blog`, `/engineering` | 선택 | operating_model facets (process, speed), tech_stack |
| P5 | **팀/문화 소개** | `/team`, `/culture`, `/life` | 선택 | operating_model facets, narrative_summary |
| P6 | **고객 사례 / 파트너** | `/customers`, `/case-study`, `/partners` | 선택 | market_segment, competitive_landscape 힌트 |

### 2.2 페이지별 추출 정보 상세

#### P1: 회사 소개 (About)

```
추출 대상:
+-- company_description     : 회사가 하는 일 1~3문장 요약
+-- founding_story_signals  : 창업 배경/동기 (있으면)
+-- mission_vision          : 미션/비전 (있으면)
+-- market_segment_hints    : 타겟 시장/고객군 언급
+-- scale_signals           : 직원수/오피스/글로벌 거점 언급
+-- investor_mentions       : 투자사/투자 라운드 언급 (있으면)
```

**추출 프롬프트**:
```
아래 회사 소개 페이지 텍스트에서 다음 정보를 추출하세요.
각 항목에 대해 원문 근거(evidence_span)를 반드시 인용하세요.
추출할 수 없는 항목은 null로 표기하세요.

1. company_description: 회사가 하는 일 (1~3문장)
2. market_segment: 타겟 시장 (예: "B2B SaaS", "헬스케어 플랫폼")
3. product_description: 핵심 제품/서비스 설명
4. scale_signals: 규모를 짐작할 수 있는 언급 (직원수, 거점, 고객수 등)
5. investor_mentions: 투자사/투자 라운드 언급

[주의사항]
- "혁신적", "최고의", "세계적" 등 광고성 수식어는 제거하고 팩트만 추출
- 수치가 포함된 표현을 우선 추출

[텍스트]
{page_text}
```

#### P2: 제품/서비스 소개

```
추출 대상:
+-- product_name            : 제품/서비스명
+-- product_category        : 카테고리 (SaaS/플랫폼/하드웨어/컨설팅 등)
+-- target_customer         : 타겟 고객 (B2B/B2C/B2G, SMB/Enterprise 등)
+-- key_features            : 핵심 기능 목록 (최대 5개)
+-- tech_mentions           : 기술 스택 / AI / 클라우드 등 언급
+-- pricing_model_hints     : 가격 모델 힌트 (구독/건당/무료 등)
```

**기여 필드 매핑**:
- `product_category` + `target_customer` -> `domain_positioning.market_segment` 보강
- `product_name` + `key_features` -> `domain_positioning.product_description`
- `tech_mentions` -> `role_expectations.tech_stack` 교차 검증

**추출 프롬프트** [v6 추가]:
```
아래 제품/서비스 소개 페이지 텍스트에서 다음 정보를 추출하세요.
각 항목에 대해 원문 근거(evidence_span)를 반드시 인용하세요.
추출할 수 없는 항목은 null로 표기하세요.

1. product_name: 제품/서비스 이름
2. product_category: 카테고리 (다음 중 선택: SaaS, 플랫폼, 마켓플레이스, 하드웨어, 컨설팅, API, 모바일앱, 기타)
3. target_customer: 타겟 고객군
   - B2B / B2C / B2G 구분
   - SMB / Mid-market / Enterprise 구분 (가능하면)
   - 타겟 산업/직군 (명시되어 있으면)
4. key_features: 핵심 기능 목록 (최대 5개, 각각 1문장으로)
5. tech_mentions: 기술 관련 언급 (AI, 클라우드, 블록체인 등)
6. pricing_model_hints: 가격 모델 힌트 (구독/건당/무료/프리미엄 등)

[주의사항]
- "업계 최초", "혁신적" 등 광고성 수식어는 제거하고 기능/사실만 추출
- 동일 기능을 다른 표현으로 반복한 경우 하나로 통합
- 기술 언급은 구체적 기술명만 추출 (예: "최첨단 기술" X, "GPT-4 기반 NLP" O)

JSON 형식으로 응답하세요.
[텍스트]
{page_text}
```

#### P3: 채용 페이지

```
추출 대상:
+-- culture_statements      : 일하는 방식 관련 서술
+-- hiring_process          : 채용 프로세스 설명
+-- team_structure_hints    : 팀/조직 구조 언급 (스쿼드/트라이브 등)
+-- benefits_raw            : 복지/혜택 목록 (raw, 필터링 전)
+-- open_positions_count    : 현재 공개 채용 포지션 수
+-- growth_signals          : 채용 규모/속도로 추정되는 성장 신호
```

**추출 프롬프트** [v6 추가]:
```
아래 채용 페이지 텍스트에서 다음 정보를 추출하세요.
각 항목에 대해 원문 근거(evidence_span)를 반드시 인용하세요.
추출할 수 없는 항목은 null로 표기하세요.

1. culture_statements: 일하는 방식에 대한 구체적 서술 (최대 5개)
   - 반드시 구체적 행동/제도를 포함한 문장만 추출
   - 예시 (O): "2주 스프린트로 운영하며 매주 금요일 데모를 진행합니다"
   - 예시 (X): "수평적이고 자유로운 문화입니다" (광고성, 제외)
2. hiring_process: 채용 프로세스 단계 (서류->면접->... 순서로)
3. team_structure_hints: 팀/조직 구조 관련 언급
   - 조직 형태 (스쿼드/트라이브/기능조직 등)
   - 팀 규모 언급 (있으면)
4. open_positions_count: 현재 공개된 채용 포지션 수 (숫자)
5. growth_signals: 채용 규모/속도에서 추정되는 성장 신호
   - 예: "20개 포지션 동시 채용", "전 직군 대규모 채용 중"

[광고성 필터링 규칙]
다음 표현이 포함된 문장은 culture_statements에서 제외하세요:
- "수평적", "자유로운", "열정", "패밀리", "최고의 복지"
- "함께 성장", "꿈을 이루는", "행복한 일터", "가족 같은"

다음 표현이 포함된 문장은 우선 추출하세요 (운영 시그널):
- speed 관련: "스프린트", "주간 배포", "데일리 릴리즈", "CI/CD", "배포 주기"
- autonomy 관련: "자율 출퇴근", "리모트", "재량 근무", "오너십", "의사결정 권한"
- process 관련: "코드리뷰", "RFC", "ADR", "테스트 커버리지", "PR 리뷰", "문서화"

JSON 형식으로 응답하세요.
[텍스트]
{page_text}
```

**operating_model facets 보강 규칙**:

| 채용 페이지 단서 | 보강 대상 facet | 보강 방법 |
|---|---|---|
| "2주 스프린트", "빠른 배포 주기" 등 | speed | 키워드 매칭 -> score 보정 |
| "자율 출퇴근", "리모트 근무", "오너십" 등 | autonomy | 키워드 매칭 -> score 보정 |
| "코드리뷰 필수", "테스트 커버리지", "RFC 문화" 등 | process | 키워드 매칭 -> score 보정 |
| "수평적 문화", "자유로운 분위기" 등 | **무시** | 광고성 표현으로 분류 |

**광고성 필터링 강화** [v6 수정: S-1 반영]:
```python
NOISE_PATTERNS = [
    "수평적", "자유로운", "열정", "패밀리", "최고의 복지",
    "함께 성장", "꿈을 이루는", "행복한 일터", "가족 같은"
]

SIGNAL_PATTERNS = {
    "speed": ["스프린트", "주간 배포", "데일리 릴리즈", "ship fast",
              "CI/CD", "배포 주기", "iteration"],
    "autonomy": ["자율 출퇴근", "리모트", "재량 근무", "오너십",
                 "의사결정 권한", "셀프 매니징"],
    "process": ["코드리뷰", "RFC", "ADR", "테스트 커버리지",
                "PR 리뷰", "문서화", "온보딩 프로세스"]
}

# [v6] 운영 관련 컨텍스트 키워드 (S-1 반영)
OPERATIONAL_CONTEXT = ["주기", "주", "일", "배포", "리뷰", "회의",
                       "스프린트", "미팅", "데일리", "위클리", "분기"]

def is_actionable_signal(text, pattern):
    """광고성이 아닌, 실제 운영 행동을 나타내는 표현인지 판별"""
    if any(noise in text for noise in NOISE_PATTERNS):
        return False

    # 특정 시그널 패턴이 있으면 즉시 인정
    has_specific_action = any(p in text for p in pattern)
    if has_specific_action:
        return True

    # [v6] 숫자만 있는 경우: 운영 관련 컨텍스트가 동반될 때만 시그널로 인정
    has_number = bool(re.search(r'\d+', text))
    has_operational_context = any(w in text for w in OPERATIONAL_CONTEXT)
    return has_number and has_operational_context
```

#### P4: 기술 블로그 (선택)

```
추출 대상:
+-- recent_post_count       : 최근 6개월 포스팅 수 (활성도)
+-- tech_topics             : 다루는 기술 주제 목록
+-- engineering_culture     : 엔지니어링 문화 단서
|   +-- has_code_review_post: 코드리뷰 관련 글 존재 여부
|   +-- has_incident_post   : 장애 대응/포스트모템 글 존재 여부
|   +-- has_architecture_post: 아키텍처 의사결정 글 존재 여부
+-- team_size_hints         : 팀 규모 단서 ("우리 팀은 10명으로...")
```

**operating_model 보강 방식**:
- `has_incident_post = true` -> `process` facet 상향 (+0.1)
- `recent_post_count >= 3/6mo` -> `speed` facet 간접 지지 (활발한 기술 공유 = 빠른 조직)
- 블로그 존재 자체가 -> `process` facet 간접 지지 (문서화 문화)

### 2.3 홈페이지 크롤링 기술 설계

#### URL 발견 우선순위 [v6 개선: C-3 반영]

```
[입력: company_domain_url]
        |
    1. sitemap.xml 파싱
        |  성공 -> P1~P6 URL 패턴 매칭으로 대상 페이지 식별
        |  실패 (404/파싱 불가) ->
        |
    2. 메인 페이지 nav/footer 링크 파싱
        |  <nav>, <header>, <footer> 내 <a> 태그 수집
        |  P1~P6 URL 패턴 + 한국어 URL 패턴으로 매칭
        |  성공 -> 대상 페이지 식별
        |  부족 (필수 P1~P3 중 누락) ->
        |
    3. BFS depth 2 크롤링
        |  메인 페이지에서 depth 2까지 링크 탐색
        |  URL 패턴 + 페이지 제목 + 본문 키워드로 분류
        |  LLM 보조 분류 (분류 불가 시)
        |
    4. 서브도메인 탐색 [v6 추가]
        |  careers.{domain}, blog.{domain}, tech.{domain} 등
        |  DNS 확인 후 존재하면 해당 서브도메인에서 1~3 반복
        |
        |  [v7 추가: C6-4 서브도메인 스킵 조건]
        |  1~3단계에서 필수 P1+P2+P3가 모두 발견된 경우,
        |  서브도메인 탐색을 스킵하여 크롤링 시간을 단축한다.
        |  선택 P4~P6가 누락되어도 필수 페이지 확보가 우선이다.
```

**서브도메인 스킵 판정 함수** [v7 추가: C6-4 반영]:
```python
def should_explore_subdomains(discovered_pages):
    """
    1~3단계에서 발견한 페이지 목록을 기반으로
    서브도메인 탐색 필요 여부를 판정한다.

    Args:
        discovered_pages: dict[str, str] -- {page_type: url}
    Returns:
        bool -- True이면 서브도메인 탐색 수행
    """
    REQUIRED_TYPES = {"about", "product", "careers"}
    found_types = set(discovered_pages.keys())

    if REQUIRED_TYPES.issubset(found_types):
        # 필수 P1+P2+P3 모두 발견 -> 서브도메인 탐색 스킵
        return False

    # 필수 중 누락 있음 -> 서브도메인에서 추가 탐색
    return True
```

**한국어 URL 패턴 딕셔너리** [v6 추가: C-3 반영]:
```python
KO_URL_PATTERNS = {
    "about": ["소개", "회사소개", "회사", "기업소개", "about", "about-us",
              "company", "기업정보"],
    "careers": ["채용", "인재채용", "채용안내", "recruit", "careers", "jobs",
                "인재영입", "채용정보", "join"],
    "product": ["제품", "서비스", "솔루션", "product", "service", "solution",
                "features", "기능", "플랫폼"],
    "blog": ["블로그", "기술블로그", "blog", "tech-blog", "engineering",
             "기술", "tech"],
    "culture": ["문화", "팀", "조직문화", "culture", "team", "life",
                "우리팀", "팀소개"],
    "customers": ["고객", "고객사례", "파트너", "customers", "case-study",
                  "partners", "사례", "레퍼런스"]
}

SUBDOMAIN_PATTERNS = ["careers", "blog", "tech", "engineering", "recruit", "jobs"]
```

#### 크롤링 파이프라인

```
[입력: company_domain_url]
        |
    +-------+
    | 1. URL | Discovery (위 우선순위 1~4 적용)
    +---+---+
        |  최대 10 페이지로 제한 (필수 P1~P3 우선)
        |
    +-------+
    | 2. 변경 | 감지 [v6 추가: C-6 반영]
    +---+---+
        |  이전 크롤링 HTML 해시와 비교
        |  변경된 페이지만 재추출 (변경 없으면 스킵)
        |  신규 크롤링이면 전체 추출
        |
    +-------+
    | 3. 렌더링 | & 텍스트 추출
    +---+---+
        |  SPA(React/Vue) 대응: headless browser (Playwright)
        |  정적 사이트: HTTP GET + BeautifulSoup
        |  텍스트 정제: 네비게이션/푸터/광고 제거
        |
    +-------+
    | 4. 페이지 | 분류
    +---+---+
        |  URL 패턴 + 한국어 URL 패턴 + 페이지 제목 + 본문 키워드로 P1~P6 분류
        |  분류 불가 시 LLM 보조 분류
        |
    +-------+
    | 5. 정보 | 추출 (LLM)
    +---+---+
        |  페이지 유형별 전용 프롬프트 실행 (P1~P3: v6 프롬프트 사용)
        |  evidence_span 필수 추출
        |
    +-------+
    | 6. 저장  | & 인덱싱
    +---+---+
        |  원본 텍스트 + 추출 결과 + 메타데이터 + 원본 HTML 해시 저장
        |  company_id, crawl_date, page_type 태깅
        +-> [출력: CrawledCompanyData]
```

#### 변경 감지 로직 [v6 추가: C-6 반영]

```python
import hashlib

def should_re_extract(company_id, page_type, new_html):
    """이전 크롤링과 비교하여 변경 감지. 변경 시에만 LLM 재추출."""
    new_hash = hashlib.sha256(new_html.encode()).hexdigest()

    # 이전 해시 조회 (BigQuery 또는 GCS metadata)
    prev_hash = get_previous_html_hash(company_id, page_type)

    if prev_hash == new_hash:
        return False  # 변경 없음 -> LLM 추출 스킵, 이전 결과 재사용

    # 해시 갱신
    save_html_hash(company_id, page_type, new_hash)
    return True  # 변경 있음 -> LLM 재추출 필요
```

#### 텍스트 해시 기반 변경 감지 [v7 추가: HTML 해시 vs 텍스트 해시 A/B 검증]

v6의 HTML 해시 방식은 CSS/JS 변경만으로도 재추출이 트리거되어 불필요한 LLM 비용이 발생할 수 있다. 텍스트 해시 방식은 본문 내용이 실제로 변경된 경우에만 재추출을 수행한다.

```python
def should_re_extract_text_hash(company_id, page_type, new_html):
    """
    [v7] 텍스트 해시 기반 변경 감지.
    HTML 전체가 아닌 정제된 텍스트를 해싱하여,
    레이아웃/스타일 변경에 의한 불필요한 재추출을 방지한다.

    Args:
        company_id: 기업 ID
        page_type: 페이지 유형 (about/product/careers 등)
        new_html: 새로 크롤링한 HTML
    Returns:
        bool -- True이면 재추출 필요
    """
    # 1. HTML -> 정제된 텍스트 추출 (Readability + BeautifulSoup)
    cleaned_text = extract_clean_text(new_html)

    # 2. 공백/줄바꿈 정규화 후 해싱
    normalized = re.sub(r'\s+', ' ', cleaned_text).strip()
    new_text_hash = hashlib.sha256(normalized.encode()).hexdigest()

    # 3. 이전 텍스트 해시와 비교
    prev_text_hash = get_previous_text_hash(company_id, page_type)

    if prev_text_hash == new_text_hash:
        return False  # 텍스트 내용 변경 없음 -> 스킵

    save_text_hash(company_id, page_type, new_text_hash)
    return True  # 텍스트 변경 있음 -> 재추출
```

**A/B 검증 계획**:

| 항목 | 내용 |
|---|---|
| 목적 | HTML 해시 vs 텍스트 해시의 불필요 재추출 비율 비교 |
| 시기 | Phase 1 파일럿 (기업 20개) |
| 방법 | 동일 기업에 대해 양쪽 해시를 동시 계산, 30일 후 재크롤링 시 비교 |
| 측정 지표 | 불필요 재추출 비율 = (HTML 해시 변경 AND 텍스트 해시 미변경) / 전체 |
| 전환 기준 | 불필요 재추출 비율 > 30%이면 텍스트 해시로 전환 |
| 위험 완화 | 전환 초기 2주간은 양쪽 해시를 모두 저장하여 rollback 가능 |

> BigQuery `homepage_extracted` 테이블에 `text_hash` 컬럼을 추가하여 A/B 비교 데이터를 수집한다 (5.2절 참조).

#### 기술 스택

| 컴포넌트 | 도구 | 이유 |
|---|---|---|
| 크롤링 엔진 | **Playwright** (Python) | SPA 렌더링 지원, 안정적 |
| 스케줄링 | Cloud Scheduler + Cloud Run Job | 배치 실행, 서버리스 |
| 텍스트 정제 | **Readability + BeautifulSoup** | 본문 추출 정확도 |
| 정보 추출 | **LLM (Gemini 2.0 Flash)** | 비용 효율 + 한국어 지원 + GCP 네이티브 (Vertex AI) |
| 저장소 | **BigQuery** (정형) + **GCS** (원본 HTML) | 분석 용이 |
| URL 발견 | sitemap.xml + nav/footer 파싱 + BFS (depth 2) + 서브도메인 | 단계적 탐색 |

#### 크롤링 정책 및 제약

| 항목 | 정책 |
|---|---|
| robots.txt | **반드시 준수** -- disallow 경로 크롤링 금지 |
| 요청 간격 | 최소 2초 (동일 도메인) |
| 최대 페이지 수 | 기업당 10 페이지 (필수 P1~P3 우선, Cloud Run Job 1시간 타임아웃 정합) |
| 최대 페이지 크기 | 1MB (초과 시 스킵) |
| 재크롤링 주기 | 30일 (최신성 유지), 해시 기반 변경 감지로 증분 추출 |
| User-Agent | 명시적 봇 식별 (회사명 + 목적 명시) |
| 개인정보 | 직원 개인 프로필/SNS는 수집하지 않음 |
| JavaScript 렌더링 | 최대 10초 대기 후 타임아웃 |
| 서브도메인 | careers/blog/tech 서브도메인까지 탐색 허용 (P1~P3 확보 시 스킵 가능 [v7]) |

#### 실패 처리

| 실패 유형 | 처리 |
|---|---|
| 홈페이지 없음 | `crawl_status: "NO_SITE"`, 해당 소스 스킵 |
| robots.txt 차단 | `crawl_status: "BLOCKED"`, 해당 경로 스킵 |
| SPA 렌더링 실패 | HTTP GET fallback, 실패 시 스킵 |
| 본문 추출 실패 (텍스트 < 50자) | 해당 페이지 스킵 |
| LLM 추출 실패 | 2회 재시도 후 스킵, 로그 기록 |
| 한국어/영어 외 언어 | 스킵 (v1) |

---

## 3. T4 -- 뉴스/기사 크롤링

### 3.1 수집 대상 기사 유형

| # | 기사 유형 | 수집 우선순위 | 기여 필드 | 예시 쿼리 |
|---|---|---|---|---|
| N1 | **투자 유치 기사** | 필수 | stage_estimate 보강 | `"{회사명}" AND ("투자" OR "시리즈" OR "펀딩")` |
| N2 | **제품/서비스 런칭** | 필수 | product_description, market_segment | `"{회사명}" AND ("출시" OR "런칭" OR "서비스")` |
| N3 | **인수합병 / 파트너십** | 선택 | competitive_landscape, structural_tensions | `"{회사명}" AND ("인수" OR "합병" OR "파트너십" OR "MOU")` |
| N4 | **조직/경영 변화** | 선택 | structural_tensions | `"{회사명}" AND ("CEO" OR "대표" OR "조직개편" OR "구조조정")` |
| N5 | **실적/성과 발표** | 선택 | stage_estimate, market_segment | `"{회사명}" AND ("매출" OR "실적" OR "성장" OR "사용자")` |
| N6 | **기술/제품 전략** | 선택 (v2) | domain_positioning, operating_model | `"{회사명}" AND ("기술" OR "AI" OR "플랫폼" OR "전략")` -- v1에서는 N2와 중복도가 높아 제외, v2에서 추가 |

### 3.2 기사 유형별 추출 정보 상세

#### N1: 투자 유치 기사 (최우선)

```
추출 대상:
+-- funding_round      : 투자 라운드 (Seed, Series A/B/C...)
+-- funding_amount     : 투자 금액
+-- investors          : 투자사 목록
+-- funding_date       : 투자 일자
+-- valuation_hints    : 기업가치 언급 (있으면)
+-- use_of_funds       : 투자금 용도 ("인력 확충", "해외 진출" 등)
+-- growth_narrative   : 성장 서사 ("전년 대비 3배 성장", "MAU 100만 돌파" 등)
```

**기여 필드 매핑**:
- `funding_round` -> `stage_estimate.stage_label` 직접 보강 (confidence 상향 최대 +0.15)
- `funding_amount` + `investors` -> `stage_estimate.stage_signals` evidence 추가
- `use_of_funds` -> `structural_tensions` 힌트 ("기술 인력 확충" = tech_debt 시사)
- `growth_narrative` -> `domain_positioning.market_segment` 보강

**추출 프롬프트**:
```
아래 투자 기사에서 정보를 추출하세요.
반드시 원문에서 직접 인용(evidence_span)하세요.

1. funding_round: 투자 라운드 (Seed/Pre-A/Series A/B/C/D+/IPO)
2. funding_amount: 금액 (숫자 + 단위)
3. investors: 투자사 이름 목록
4. funding_date: 날짜 (YYYY-MM 형식)
5. use_of_funds: 투자금 사용 계획
6. growth_narrative: 성장 관련 수치/사실

[주의] 기사 제목/부제의 과장 표현은 무시하고 본문 팩트만 추출.

[기사 텍스트]
{article_text}
```

#### N2: 제품/서비스 런칭 기사

```
추출 대상:
+-- product_name       : 제품/서비스명
+-- launch_date        : 출시 일자
+-- target_market      : 타겟 시장/고객
+-- key_differentiator : 경쟁 차별점 (있으면)
+-- tech_approach      : 기술적 접근 ("AI 기반", "블록체인 활용" 등)
+-- traction_data      : 초기 성과 수치 (있으면)
```

#### N3: 인수합병/파트너십 기사

```
추출 대상:
+-- deal_type          : M&A / 전략적 제휴 / JV / MOU
+-- counterparty       : 상대 기업
+-- deal_purpose       : 목적 ("기술력 확보", "시장 확대" 등)
+-- deal_amount        : 금액 (있으면)
+-- strategic_signal   : 전략적 방향 시사점
```

**structural_tensions 기여** (enum: `01_company_context.md` 2.2절 참조):
- M&A -> `integration_tension`
- 파트너십 -> `build_vs_buy`

#### N4: 조직/경영 변화 기사

```
추출 대상:
+-- change_type        : CEO 교체 / CxO 영입 / 조직개편 / 구조조정 / 감원
+-- change_date        : 변화 시점
+-- scale_of_change    : 변화 규모 ("전사 조직개편", "30% 감원" 등)
+-- stated_reason      : 공식 사유
+-- implied_tension    : 암시되는 내부 긴장
```

**추출 프롬프트** [v6 추가: C-2 반영 -- A6 taxonomy 연동]:
```
아래 조직/경영 변화 관련 기사에서 정보를 추출하세요.
반드시 원문에서 직접 인용(evidence_span)하세요.
추출할 수 없는 항목은 null로 표기하세요.

1. change_type: 변화 유형 (다음 중 선택)
   - "CEO 교체" / "CxO 영입" / "조직개편" / "구조조정" / "감원" / "사업부 분리" / "사업부 합병"
2. change_date: 변화 시점 (YYYY-MM 형식)
3. scale_of_change: 변화 규모 (구체적 수치/범위)
4. stated_reason: 공식 발표 사유 (원문 인용)
5. tension_type: 아래 8개 유형 중 가장 적합한 것을 선택하세요.
   복수 해당 시 primary 1개 + related 최대 2개를 지정하세요.
   - "tech_debt_vs_features": 기술부채 해소 vs 신기능 개발
   - "speed_vs_reliability": 빠른 출시 vs 안정성/품질
   - "founder_vs_professional_mgmt": 창업자 경영 vs 전문경영인 전환
   - "efficiency_vs_growth": 효율화/비용 절감 vs 성장 투자
   - "scaling_leadership": 리더십 확장/전문화 필요
   - "integration_tension": M&A/합병 후 조직 통합 긴장
   - "build_vs_buy": 내부 개발 vs 외부 솔루션/파트너십
   - "portfolio_restructuring": 사업부 재편/선택과 집중
6. tension_confidence: tension_type 추론의 확신도 (0.0~1.0)

[판정 가이드]
- CEO 교체 -> 보통 "founder_vs_professional_mgmt" (confidence 0.45)
- CxO 영입 -> 보통 "scaling_leadership" (confidence 0.40)
- 조직개편 -> 보통 "portfolio_restructuring" (confidence 0.45)
- 구조조정/감원 -> 보통 "efficiency_vs_growth" (confidence 0.50)
- 사업부 분리/합병 -> 보통 "portfolio_restructuring" (confidence 0.45)
- 위 가이드는 기본값이며, 기사 내용에 따라 다른 유형이 더 적합할 수 있음

[주의]
- 기사 제목의 과장 표현은 무시하고 본문 팩트만 추출
- 추측성 표현("~할 것으로 보인다", "~전망")은 confidence를 0.1 낮추어 반영
- 여러 tension이 해당되면 primary_tension과 related_tensions로 구분

JSON 형식으로 응답하세요:
{
  "change_type": "...",
  "change_date": "YYYY-MM",
  "scale_of_change": "...",
  "stated_reason": "...",
  "primary_tension": {"type": "...", "confidence": 0.XX},
  "related_tensions": [{"type": "...", "confidence": 0.XX}],
  "evidence_spans": ["...", "..."]
}

[기사 텍스트]
{article_text}
```

**structural_tensions 기여 (핵심)**:

> tension_type은 `01_company_context.md` 2.2절에서 확정한 8개 taxonomy enum을 사용한다.

| change_type | 추론 가능한 tension_type (enum) | confidence |
|---|---|---|
| CEO 교체 | `founder_vs_professional_mgmt` | 0.45 |
| CxO 영입 | `scaling_leadership` | 0.40 |
| 조직개편 | `portfolio_restructuring` | 0.45 |
| 구조조정/감원 | `efficiency_vs_growth` | 0.50 |
| 사업부 분리/합병 | `portfolio_restructuring` | 0.45 |

#### N5: 실적/성과 발표

```
추출 대상:
+-- metric_type        : 매출 / MAU / 거래액 / 고객수 등
+-- metric_value       : 수치
+-- metric_period      : 측정 기간
+-- yoy_growth         : 전년 대비 성장률 (있으면)
+-- market_position    : 시장 내 포지션 언급 ("1위", "점유율 30%" 등)
```

### 3.3 뉴스 수집 소스 및 방법

| 소스 | 접근 방법 | 장점 | 단점 |
|---|---|---|---|
| **네이버 뉴스 검색** | 네이버 검색 API | 국내 커버리지 최대, API 제공 | 일일 호출 제한 |
| **Google News** | SerpAPI / Google News RSS | 글로벌 + 국내 커버리지 | 유료 API 필요 |
| **직접 언론사 크롤링** | HTTP GET | API 비용 없음 | 유지보수 높음, 법적 리스크 |
| **TheVC / 크런치베이스** | API | 투자 정보 정확도 높음 | 유료, 커버리지 제한 |
| **PR 통신사 (뉴스와이어 등)** | RSS / API | 공식 보도자료 | 기업 시각 편향 |

**v1 권장 조합**: 네이버 뉴스 검색 API (Primary) + TheVC API (투자 정보 보강)

#### 검색 전략

```python
def build_news_queries(company_name, aliases=None):
    """기업명 + 카테고리별 검색 쿼리 생성"""
    names = [company_name] + (aliases or [])
    queries = []

    for name in names:
        # N1: 투자 (최우선)
        queries.append({
            "query": f'"{name}" (투자 OR 시리즈 OR 펀딩 OR 유치)',
            "category": "funding",
            "priority": 1,
            "max_results": 10,
            "date_range": "2y"  # 최근 2년
        })
        # N2: 제품/서비스
        queries.append({
            "query": f'"{name}" (출시 OR 런칭 OR 서비스 OR 제품)',
            "category": "product",
            "priority": 1,
            "max_results": 5,
            "date_range": "1y"
        })
        # N4: 조직 변화
        queries.append({
            "query": f'"{name}" (CEO OR 대표이사 OR 조직개편 OR 구조조정 OR 인사)',
            "category": "org_change",
            "priority": 2,
            "max_results": 5,
            "date_range": "1y"
        })
        # N5: 실적
        queries.append({
            "query": f'"{name}" (매출 OR 실적 OR 성장 OR 사용자 OR 거래액)',
            "category": "performance",
            "priority": 2,
            "max_results": 5,
            "date_range": "1y"
        })
        # N3: M&A
        queries.append({
            "query": f'"{name}" (인수 OR 합병 OR 파트너십 OR MOU)',
            "category": "mna",
            "priority": 3,
            "max_results": 3,
            "date_range": "2y"
        })

    return queries
```

#### 중복/노이즈 제거

```python
# [v7 수정: S-5 반영 -- 2단계 클러스터링으로 교체]
def deduplicate_articles(articles):
    """
    동일 사건에 대한 중복 기사 제거.
    [v7] 제목 유사도 + 핵심 엔티티 overlap 2단계 클러스터링.
    """
    # 1단계: 제목 유사도 기반 후보 클러스터링 (cosine sim > 0.85)
    title_clusters = cluster_by_title_similarity(articles, threshold=0.85)

    # 2단계: 핵심 엔티티 overlap 검증
    # 제목이 다르더라도 동일 사건(같은 인물/기업/금액)이면 중복 판정
    final_clusters = []
    for cluster in title_clusters:
        # 이미 제목 유사도로 묶인 클러스터는 유지
        final_clusters.append(cluster)

    # 제목 유사도 미충족 기사 중 핵심 엔티티 overlap으로 추가 클러스터링
    unclustered = [a for c in title_clusters for a in c if len(c) == 1]
    entity_clusters = cluster_by_key_entities(unclustered, overlap_threshold=0.60)
    final_clusters.extend(entity_clusters)

    # 각 클러스터에서 대표 기사 선택 (가장 긴 본문)
    deduped = []
    for cluster in final_clusters:
        representative = max(cluster, key=lambda a: len(a.body))
        representative.duplicate_count = len(cluster)
        deduped.append(representative)

    return deduped


def cluster_by_key_entities(articles, overlap_threshold=0.60):
    """
    [v7 추가: S-5] 핵심 엔티티 기반 중복 클러스터링.
    기사에서 추출된 핵심 엔티티(인물, 기업, 금액, 날짜)의
    overlap 비율이 threshold 이상이면 동일 사건으로 판정.

    Args:
        articles: 단독 클러스터(제목 유사도 미충족) 기사 목록
        overlap_threshold: 엔티티 overlap 비율 임계값 (0.60)
    Returns:
        list[list[Article]] -- 클러스터 목록
    """
    clusters = []
    assigned = set()

    for i, a in enumerate(articles):
        if i in assigned:
            continue
        cluster = [a]
        a_entities = extract_key_entities(a)  # {persons, orgs, amounts, dates}

        for j, b in enumerate(articles[i+1:], start=i+1):
            if j in assigned:
                continue
            b_entities = extract_key_entities(b)
            overlap = compute_entity_overlap(a_entities, b_entities)
            if overlap >= overlap_threshold:
                cluster.append(b)
                assigned.add(j)

        assigned.add(i)
        clusters.append(cluster)

    return clusters


def extract_key_entities(article):
    """기사에서 핵심 엔티티를 추출 (인물명, 기업명, 금액, 날짜)"""
    return {
        "persons": extract_person_names(article.body),
        "orgs": extract_org_names(article.body),
        "amounts": extract_monetary_amounts(article.body),
        "dates": extract_dates(article.body),
    }


def compute_entity_overlap(entities_a, entities_b):
    """두 엔티티 집합의 Jaccard 유사도 계산"""
    all_a = (entities_a["persons"] | entities_a["orgs"] |
             entities_a["amounts"] | entities_a["dates"])
    all_b = (entities_b["persons"] | entities_b["orgs"] |
             entities_b["amounts"] | entities_b["dates"])
    if not all_a or not all_b:
        return 0.0
    return len(all_a & all_b) / len(all_a | all_b)
```

**파일럿 검증 계획** [v7 추가]:

| 항목 | 내용 |
|---|---|
| 비교 대상 | 제목 유사도 threshold: 0.85 vs 0.75 vs 0.70 |
| 측정 지표 | 중복 제거율, 과도 제거율 (서로 다른 사건을 동일 사건으로 판정한 비율) |
| 합격 기준 | 과도 제거율 < 5% |
| 엔티티 overlap threshold | 0.60을 기준으로 0.50 / 0.70과 비교 |

```python
# [v7 수정: S-4 반영 -- 본문 길이 적응형 관련성 필터로 교체]
def filter_irrelevant(articles, company_name):
    """
    회사와 무관한 기사 필터링.
    [v7] 본문 길이에 따라 회사명 등장 횟수 기준을 적응적으로 조정.
    짧은 기사(200자 이하)는 1회 등장 + 제목 포함이면 허용.
    """
    filtered = []
    for article in articles:
        body_len = len(article.body)
        mention_count = article.body.lower().count(company_name.lower())
        title_has_name = company_name.lower() in article.title.lower()

        if body_len <= 200:
            # 짧은 기사: 1회 등장 + 제목에 회사명 있으면 허용
            if mention_count >= 1 and title_has_name:
                filtered.append(article)
        elif body_len <= 500:
            # 중간 기사: 2회 이상 등장
            if mention_count >= 2:
                filtered.append(article)
            elif mention_count >= 1 and title_has_name:
                filtered.append(article)
        else:
            # 긴 기사: 3회 이상 등장 (v6 기존 기준 유지)
            if mention_count >= 3:
                filtered.append(article)
            elif mention_count >= 1 and title_has_name:
                filtered.append(article)

    return filtered
```

**파일럿 검증 계획** [v7 추가]:

| 항목 | 내용 |
|---|---|
| 목적 | 길이 적응형 기준의 적합성 검증 |
| 방법 | 파일럿 20개 기업에서 수집된 기사를 v6 기준 vs v7 기준으로 비교 |
| 측정 지표 | 관련 기사 recall 변화, 무관 기사 오인율 |
| 합격 기준 | 관련 기사 recall +10% 이상, 무관 기사 오인율 < 5% |

### 3.4 뉴스 크롤링 파이프라인

```
[입력: company_name, company_aliases]
        |
    +-------+
    | 1. 검색 | 쿼리 생성
    +---+---+
        |  카테고리별 쿼리 생성 (N1~N5)
        |  기업명 + 별칭(aliases) 조합
        |
    +-------+
    | 2. 뉴스 | 수집
    +---+---+
        |  네이버 뉴스 검색 API 호출 (v1 Primary)
        |  기사당 제목 + description + link + 발행일 수집
        |  본문은 funding/org_change 카테고리만 link 추가 크롤링 (네이버 API 본문 미제공)
        |  기업당 최대 30건 (중복 제거 후)
        |
    +-------+
    | 3. 필터링 | & 중복 제거
    +---+---+
        |  [v7] 본문 길이 적응형 관련성 필터 (200/500자 경계)
        |  [v7] 2단계 중복 제거 (제목 유사도 + 핵심 엔티티 overlap)
        |  광고성 기사(PR성 보도자료) 마킹
        |
    +-------+
    | 4. 분류  | (기사 유형)
    +---+---+
        |  N1~N5 카테고리 자동 분류 (LLM)
        |  복수 카테고리 허용
        |
    +-------+
    | 5. 정보 | 추출 (LLM)
    +---+---+
        |  카테고리별 전용 프롬프트 실행 (N1, N4: v6 프롬프트 사용)
        |  evidence_span 필수
        |  confidence scoring
        |
    +-------+
    | 6. 시계열 | 정리
    +---+---+
        |  추출 결과를 시간순 정렬
        |  최신 정보 우선 (freshness 가중)
        |  동일 주제 최신 기사가 이전 기사를 대체
        |
    +-------+
    | 7. 저장  |
    +---+---+
        +-> [출력: NewsExtractedData]
```

### 3.5 뉴스 데이터의 신뢰도 보정

뉴스는 **편향과 과장**이 내재된 소스이므로 추가 보정이 필요하다.

| 보정 규칙 | 적용 대상 | 방법 |
|---|---|---|
| PR성 기사 감쇠 | 보도자료 기반 기사 | confidence x 0.7 |
| 복수 언론사 교차 확인 | 동일 사실을 여러 매체가 보도 | confidence + 0.10 |
| 기사 나이 감쇠 | 오래된 기사 | confidence x max(0.5, 1.0 - months_ago x 0.03) |
| 추측성 표현 감쇠 | "~할 것으로 보인다", "~전망" | confidence x 0.6 |
| 수치 동반 가산 | 구체적 숫자가 포함된 claim | confidence + 0.05 |

```python
# [v6] 카테고리별 confidence ceiling 차등 적용 (S-3 반영)
CATEGORY_CEILING = {
    "funding": 0.65,      # 팩트 기반 (금액, 투자사 등 검증 가능)
    "product": 0.55,      # 기업 발표 기반, 검증 어려움
    "org_change": 0.55,   # 팩트+추론 혼합
    "performance": 0.60,  # 수치 기반
    "mna": 0.55,          # 팩트 기반이나 전략적 해석 필요
}

def adjust_news_confidence(base_confidence, article):
    c = base_confidence

    # PR성 감쇠
    if article.is_press_release:
        c *= 0.7

    # 복수 매체 보강
    category_ceiling = CATEGORY_CEILING.get(article.category, 0.55)
    if article.duplicate_count >= 3:
        c = min(c + 0.10, category_ceiling)

    # 기사 나이 감쇠
    months_ago = (today - article.publish_date).days / 30
    freshness_factor = max(0.5, 1.0 - months_ago * 0.03)
    c *= freshness_factor

    # 추측성 표현
    speculative_patterns = ["전망", "것으로 보인다", "예상", "관측", "가능성"]
    if any(p in article.body for p in speculative_patterns):
        c *= 0.6

    return min(c, category_ceiling)  # [v6] 카테고리별 ceiling 적용
```

---

## 4. 크롤링 결과 -> CompanyContext 필드 통합

### 4.1 통합 로직 개요

```
[NICE 데이터] ------------------+
[JD 데이터] --------------------+
[홈페이지 크롤링 결과] ---------+--> [CompanyContext 생성기] --> CompanyContext v4
[뉴스 크롤링 결과] -------------+
[투자 DB 데이터] ---------------+
```

### 4.2 필드별 소스 우선순위 및 통합 규칙

| 필드 | 1순위 소스 | 2순위 소스 | 3순위 소스 | 통합 규칙 |
|---|---|---|---|---|
| `stage_estimate.stage_label` | 투자 DB | 뉴스(N1) | NICE + JD | 최고 confidence 소스 채택, 교차 지지 시 boost |
| `domain_positioning.product_description` | 홈페이지(P2) | 뉴스(N2) | JD | 홈페이지 우선, 뉴스로 보강 |
| `domain_positioning.market_segment` | 홈페이지(P1+P2) | JD | 뉴스(N2) | 복수 소스 합의 시 confidence 상향 |
| `domain_positioning.competitive_landscape` | 뉴스(N3+N5) | 홈페이지(P6) | -- | 뉴스 기반, 경쟁사/시장 언급 수집 |
| `structural_tensions` | 뉴스(N4) | 뉴스(N3) | -- | 뉴스에서만 추출 가능, 없으면 null |
| `operating_model.facets` | JD | 홈페이지(P3+P4) | -- | JD 기준, 홈페이지로 보강 (아래 4.4 참조) |
| `operating_model.narrative_summary` | 홈페이지(P3+P5) | 뉴스 | JD | 홈페이지 채용/문화 페이지 기반 |

### 4.3 소스 간 충돌 해결

```python
def resolve_conflict(claims_from_sources):
    """복수 소스에서 동일 필드에 대해 다른 값을 주장할 때"""
    if len(set(c.value for c in claims_from_sources)) == 1:
        # 모든 소스 합의 -> boost
        best = max(claims_from_sources, key=lambda c: c.confidence)
        best.confidence = min(best.confidence + 0.10, 0.85)
        return best

    # 충돌 발생
    # 규칙 1: 소스 Tier가 높은 쪽 우선
    sorted_claims = sorted(claims_from_sources,
                           key=lambda c: SOURCE_TIER_PRIORITY[c.source_type])
    winner = sorted_claims[0]

    # 규칙 2: 충돌 사실 기록
    winner.has_contradiction = True
    winner.contradiction_sources = [c.source_type for c in sorted_claims[1:]]
    winner.confidence = min(winner.confidence, 0.50)  # 충돌 시 confidence 하향

    return winner
```

### 4.4 operating_model facet score 병합 규칙 [v6 추가: D-3 반영]

JD와 크롤링(P3/P4)에서 각각 추출한 facet score를 병합하는 규칙:

```python
def merge_facet_scores(jd_facet, crawl_facet, facet_name):
    """
    JD(T2)와 크롤링(T3)에서 추출한 facet score를 병합.
    JD가 1순위 소스이므로 JD 기반으로 크롤링이 보강하는 구조.

    Args:
        jd_facet: {"score": 0.72, "confidence": 0.45}
        crawl_facet: {"score": 0.60, "confidence": 0.35} or None
        facet_name: "speed" | "autonomy" | "process"
    Returns:
        {"score": float, "confidence": float, "sources": list}
    """
    if crawl_facet is None:
        # 크롤링 데이터 없음 -> JD만 사용
        return {
            "score": jd_facet["score"],
            "confidence": jd_facet["confidence"],
            "sources": ["jd"]
        }

    if jd_facet is None:
        # JD 데이터 없음 -> 크롤링만 사용 (T3 ceiling 0.60 적용)
        return {
            "score": crawl_facet["score"],
            "confidence": min(crawl_facet["confidence"], 0.60),
            "sources": ["crawl_site"]
        }

    # 양쪽 데이터 존재
    score_diff = abs(jd_facet["score"] - crawl_facet["score"])

    if score_diff <= 0.20:
        # 합의 범위 (차이 <= 0.20): 가중 평균 + confidence 보강
        total_conf = jd_facet["confidence"] + crawl_facet["confidence"]
        merged_score = (
            jd_facet["score"] * jd_facet["confidence"] +
            crawl_facet["score"] * crawl_facet["confidence"]
        ) / total_conf
        merged_confidence = min(jd_facet["confidence"] + 0.10, 0.70)  # 합의 보강
        return {
            "score": round(merged_score, 2),
            "confidence": merged_confidence,
            "sources": ["jd", "crawl_site"]
        }
    else:
        # 충돌 (차이 > 0.20): JD 우선, 크롤링은 참고만
        return {
            "score": jd_facet["score"],
            "confidence": min(jd_facet["confidence"], 0.50),  # 충돌 시 하향
            "has_contradiction": True,
            "contradiction_detail": {
                "jd_score": jd_facet["score"],
                "crawl_score": crawl_facet["score"]
            },
            "sources": ["jd"]
        }
```

#### facet 병합 threshold 캘리브레이션 [v7 추가: C6-3 반영]

v6에서 합의/충돌 경계를 `score_diff <= 0.20`으로 설정했으나 이 임계값의 근거가 없었다. 파일럿 데이터를 기반으로 4단계 캘리브레이션을 수행한다.

**캘리브레이션 4단계 절차**:

| 단계 | 작업 | 산출물 |
|---|---|---|
| 1. 데이터 수집 | 파일럿 20개 기업의 JD facet score와 크롤링 facet score를 동시 추출 | `(jd_score, crawl_score)` 쌍 60건 (3 facets x 20 기업) |
| 2. 분포 분석 | `score_diff` 분포의 히스토그램 작성, 자연적 분리점(bimodal gap) 확인 | score_diff 분포 차트 + 통계 요약 |
| 3. Human eval | 충돌 후보(score_diff > 0.15) 중 10건을 채용 전문가가 "실제 불일치인가?" 판정 | 합의/충돌 판정 ground truth 10건 |
| 4. 임계값 확정 | Human eval 결과와 score_diff를 대조하여 최적 threshold 산출 | 확정 threshold (0.15~0.25 범위 예상) |

**의사결정 기준표**:

| 조건 | 결정 |
|---|---|
| score_diff 분포에 0.15~0.25 사이 자연 gap 존재 | gap 위치를 threshold로 채택 |
| 자연 gap 없음 + Human eval에서 0.20 기준 정확도 >= 80% | 0.20 유지 |
| 자연 gap 없음 + Human eval 정확도 < 80% | ROC 분석으로 최적 threshold 재산출 |
| 60건 중 충돌 케이스 < 5건 | 표본 부족으로 0.20 유지, 운영 데이터 축적 후 재검토 |

### 4.5 Evidence source_id 네이밍 컨벤션 [v6 추가: C-5 반영]

크롤링 결과가 CompanyContext에 반영될 때, evidence의 `source_id` 형식:

| source_type | source_id 형식 | 예시 |
|---|---|---|
| `crawl_site` | `crawl_site_{company_id}_{page_type}_{crawl_date}` | `crawl_site_c001_about_20260308` |
| `crawl_news` | `crawl_news_{company_id}_{article_id}` | `crawl_news_c001_art_20260301_001` |
| `investment_db` | `investdb_{company_id}_{round_id}` | `investdb_c001_seriesA` |
| `jd` | `jd_{vacancy_id}` | `jd_v_20260201_001` |
| `nice` | `nice_{company_id}` | `nice_c001` |

v4 `01_company_context.md`의 Evidence 통합 모델과 호환되며, `source_type` enum에 이미 정의된 `crawl_site`, `crawl_news`를 사용한다.

---

## 5. 저장 스키마

### 5.1 크롤링 원본 저장 (GCS)

```
gs://ml-api-test-vertex/crawl/    # GCP 구현: 기존 프로젝트 버킷 재사용
+-- homepage/
|   +-- {company_id}/
|   |   +-- {crawl_date}/
|   |   |   +-- raw/          # 원본 HTML
|   |   |   |   +-- about.html
|   |   |   |   +-- product.html
|   |   |   |   +-- careers.html
|   |   |   +-- text/         # 정제된 텍스트
|   |   |   |   +-- about.txt
|   |   |   |   +-- ...
|   |   |   +-- extracted/    # LLM 추출 결과 JSON
|   |   |   |   +-- about.json
|   |   |   |   +-- ...
|   |   |   +-- meta.json     # [v6] 페이지별 HTML 해시, 변경 감지용
|   |   +-- latest -> {최신 crawl_date}/
+-- news/
|   +-- {company_id}/
|   |   +-- {crawl_date}/
|   |   |   +-- articles/     # 수집된 기사 원문
|   |   |   +-- extracted/    # 추출 결과 JSON
|   |   |   +-- summary.json  # 시계열 요약
|   |   +-- latest -> {최신 crawl_date}/
```

### 5.2 추출 결과 저장 (BigQuery)

```sql
-- 홈페이지 크롤링 추출 결과
CREATE TABLE crawl.homepage_extracted (
  company_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  page_type STRING,                -- "about" / "product" / "careers" / "blog" / "culture"
  page_url STRING,
  -- 추출 필드
  product_description STRING,
  market_segment STRING,
  culture_signals JSON,            -- {speed: [...], autonomy: [...], process: [...]}
  scale_signals JSON,
  tech_mentions ARRAY<STRING>,
  -- [v6] 변경 감지
  html_hash STRING,                -- 원본 HTML SHA-256 해시
  text_hash STRING,                -- [v7 추가] 정제 텍스트 SHA-256 해시 (A/B 비교용)
  is_changed BOOLEAN,              -- 이전 크롤링 대비 변경 여부
  -- 메타
  text_length INT64,
  extraction_model STRING,
  evidence_spans JSON,             -- 원문 근거 배열
  confidence FLOAT64,
  generated_at TIMESTAMP
);

-- 뉴스 크롤링 추출 결과
CREATE TABLE crawl.news_extracted (
  company_id STRING NOT NULL,
  article_id STRING NOT NULL,
  crawl_date DATE NOT NULL,
  -- 기사 메타
  title STRING,
  source_media STRING,
  publish_date DATE,
  article_url STRING,
  category STRING,                 -- "funding" / "product" / "org_change" / "performance" / "mna"
  is_press_release BOOLEAN,
  -- 추출 필드
  funding_round STRING,
  funding_amount STRING,
  investors ARRAY<STRING>,
  tension_type STRING,             -- [v6] 01_company_context.md 2.2절 taxonomy enum
  tension_related ARRAY<STRING>,   -- [v6] related_tensions
  tension_description STRING,
  growth_narrative STRING,
  extracted_data JSON,             -- 카테고리별 추출 결과 전체
  -- 메타
  raw_confidence FLOAT64,
  adjusted_confidence FLOAT64,     -- 보정 후
  evidence_spans JSON,
  generated_at TIMESTAMP
);

-- 기업별 크롤링 요약 (CompanyContext 생성 시 참조)
CREATE TABLE crawl.company_crawl_summary (
  company_id STRING NOT NULL,
  last_homepage_crawl DATE,
  last_news_crawl DATE,
  homepage_pages_crawled INT64,
  news_articles_collected INT64,
  -- 핵심 추출 결과 요약
  best_product_description STRING,
  best_market_segment STRING,
  latest_funding_round STRING,
  latest_funding_date DATE,
  tension_signals JSON,            -- [{type, related, description, confidence, source}]
  culture_signals_aggregated JSON, -- {speed: {score, confidence}, ...}
  -- [v6] facet 병합 결과
  facet_merge_results JSON,        -- {speed: {merged_score, sources, has_contradiction}, ...}
  -- 메타
  overall_crawl_quality FLOAT64,   -- 0~1, 수집 성공률 기반
  updated_at TIMESTAMP
);
```

### 5.3 BigQuery 테이블 간 데이터 플로우 [v6 추가: D-1 반영]

```
[크롤링 파이프라인]
        |
        v
+---------------------------+    +---------------------------+
| crawl.homepage_extracted  |    | crawl.news_extracted      |
| (페이지별 추출 결과)       |    | (기사별 추출 결과)         |
+------------+--------------+    +------------+--------------+
             |                                |
             +-------+--------+---------------+
                     |        |
                     v        v
        +---------------------------+
        | crawl.company_crawl_summary|
        | (기업별 크롤링 요약 집계)    |
        +------------+--------------+
                     |
                     | CompanyContext 생성기에서 읽기
                     v
        +---------------------------+
        | context.company_context   |
        | (v4 CompanyContext 저장)   |
        +------------+--------------+
                     |
                     | MappingFeatures 계산기에서 읽기
                     v
        +---------------------------+
        | context.mapping_features  |
        | (매핑 피처 저장)           |
        +---------------------------+
```

**데이터 플로우 설명**:
1. **크롤링 파이프라인** -> `homepage_extracted` / `news_extracted`: 페이지/기사별 원본 추출 결과 저장
2. **집계 Job** -> `company_crawl_summary`: 기업별로 최신 크롤링 결과를 집계. facet 병합, 최신 투자 정보 등
3. **CompanyContext 생성기**: `company_crawl_summary` + NICE + JD 데이터를 읽어 `context.company_context` 생성
4. **MappingFeatures 계산기**: `company_context` + `candidate_context`를 읽어 매핑 피처 산출

#### 집계 Job 트리거 방식 [v7 추가]

`company_crawl_summary` 집계 Job의 트리거 방식을 정의한다. Primary(이벤트 기반) + Backup(스케줄 기반) 이중 구조로 안정성을 확보한다.

**아키텍처**:

```
[Cloud Run Job 완료]
        |
        | Eventarc (Primary)
        | Cloud Run Job 완료 이벤트 (google.cloud.run.job.v1.completed)
        v
+-------------------------------+
| aggregate_crawl Cloud Function|
| (집계 로직 실행)               |
+-------------------------------+
        |
        v
[crawl.company_crawl_summary 갱신]

---

[Cloud Scheduler (Backup)]
        | 매일 03:00 KST
        v
+-------------------------------+
| 동일 aggregate_crawl CF 호출  |
| (멱등성 보장으로 중복 실행 안전)|
+-------------------------------+
```

**Eventarc (Primary)**:
- Cloud Run Job(홈페이지 크롤러 / 뉴스 크롤러) 완료 시 자동 트리거
- 크롤링 완료 직후 summary가 갱신되어 최신성 보장
- 트리거 이벤트: `google.cloud.run.job.v1.completed`

**Cloud Scheduler (Backup)**:
- 매일 03:00 KST에 동일 Cloud Function을 호출
- Eventarc 실패 시에도 최소 1일 이내에 summary가 갱신되도록 보장
- 크롤링이 없었던 날에도 실행되지만, 멱등성으로 인해 불필요한 갱신 없음

**집계 함수**:

```python
def aggregate_crawl_summary(company_id):
    """
    [v7] 기업별 크롤링 결과를 company_crawl_summary에 집계.
    멱등성: 동일 company_id에 대해 여러 번 호출해도 결과가 동일.

    1. homepage_extracted에서 해당 기업의 최신 크롤링 데이터 조회
    2. news_extracted에서 해당 기업의 최신 크롤링 데이터 조회
    3. facet 병합, 투자 정보 등 집계
    4. company_crawl_summary UPSERT (INSERT ON CONFLICT UPDATE)
    """
    # 1. 최신 홈페이지 추출 결과
    homepage_data = query_latest_homepage(company_id)

    # 2. 최신 뉴스 추출 결과
    news_data = query_latest_news(company_id)

    # 3. 집계
    summary = {
        "company_id": company_id,
        "last_homepage_crawl": homepage_data.latest_date,
        "last_news_crawl": news_data.latest_date,
        "homepage_pages_crawled": len(homepage_data.pages),
        "news_articles_collected": len(news_data.articles),
        "best_product_description": select_best_product_desc(homepage_data),
        "best_market_segment": select_best_market_segment(homepage_data),
        "latest_funding_round": extract_latest_funding(news_data),
        "tension_signals": aggregate_tensions(news_data),
        "culture_signals_aggregated": aggregate_culture(homepage_data),
        "facet_merge_results": merge_all_facets(homepage_data),
        "overall_crawl_quality": compute_quality_score(homepage_data, news_data),
        "updated_at": datetime.utcnow(),
    }

    # 4. UPSERT (멱등성 보장)
    upsert_crawl_summary(summary)
```

### 5.4 크롤링 데이터의 Graph 반영 [v6 추가: D-2 반영]

크롤링으로 수집된 데이터가 Neo4j Graph에 반영되는 경로:

#### Organization 노드 확장

```cypher
// v4 기존
(:Organization {
  org_id, name, industry_code, employee_count, ...
})

// v6 크롤링 보강 후 확장 속성
(:Organization {
  // ... v4 기존 속성 유지 ...

  // 크롤링 보강 속성
  product_description: STRING,          -- P2에서 추출
  market_segment: STRING,               -- P1+P2에서 추출
  latest_funding_round: STRING,         -- N1에서 추출
  latest_funding_date: DATE,            -- N1에서 추출
  crawl_quality: FLOAT,                 -- 크롤링 품질 지표 (0~1)
  last_crawled_at: DATETIME             -- 최종 크롤링 일시
})
```

#### structural_tensions -> Graph 표현

structural_tensions는 Organization의 JSON 속성으로 저장하되, Graph에서의 직접 탐색은 v2에서 검토한다.

```cypher
// v1: Organization 속성으로 저장 (JSON)
SET org.structural_tensions = $tensions_json

// v2 검토: Tension 노드로 분리 시
// (:Organization)-[:HAS_TENSION]->(:Tension {type, confidence, detected_at})
```

**v1에서 Tension 노드를 분리하지 않는 이유**:
- MappingFeatures v1의 5개 피처 중 structural_tensions를 직접 입력으로 사용하는 피처가 없음
- `culture_fit` 계산에서 간접 참조만 하며, 이는 CompanyContext JSON에서 읽어도 충분
- v2에서 `tension_match` 피처를 도입할 때 노드 분리를 검토

---

## 6. 실행 계획

### Phase 0: 설계 및 준비 (1주)

| # | 작업 | 산출물 | 담당 |
|---|---|---|---|
| 0-1 | 크롤링 대상 기업 목록 확정 | 기업 리스트 (company_id + domain URL + aliases) | 데이터 |
| 0-2 | 네이버 뉴스 API 키 발급 / TheVC API 계약 | API 접근 권한 | 인프라 |
| 0-3 | GCS 버킷 + BigQuery 테이블 생성 | 저장소 | 인프라 |
| 0-4 | 추출 프롬프트 초안 작성 (P1~P3, N1, N4 -- v6 기준) | 프롬프트 셋 | ML |
| 0-5 | robots.txt 준수 로직 구현 | 크롤링 정책 모듈 | 개발 |
| 0-6 | TheVC API 연동 모듈 구현 [v6 추가: A5-1 반영] | 투자 데이터 수집기 | 개발 |

### Phase 1: 홈페이지 크롤러 구축 (2주)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 1-1 | Playwright 기반 크롤링 엔진 구현 | 크롤러 코어 | SPA 렌더링 포함 |
| 1-2 | URL 발견 + 페이지 분류 모듈 (한국어 URL 패턴 포함) | 페이지 타이핑 | sitemap + nav + BFS + 서브도메인 |
| 1-3 | 텍스트 정제 모듈 (Readability) | 본문 추출기 | 네비/푸터 제거 |
| 1-4 | LLM 추출 모듈 (P1~P3 전용 프롬프트) | 정보 추출기 | Gemini 2.0 Flash |
| 1-5 | 해시 기반 변경 감지 모듈 [v6 추가] | 증분 추출기 | SHA-256 비교 |
| 1-6 | 파일럿: 기업 20개 크롤링 | 파일럿 결과 | 품질 검증 |
| 1-7 | 추출 품질 Human eval (파일럿) | 품질 리포트 | 프롬프트 튜닝 |
| 1-8 | [v7 추가] 해시 전략 A/B 비교 데이터 수집 | html_hash + text_hash 동시 기록 | 파일럿 20개 기업 |

### Phase 2: 뉴스 크롤러 구축 (2주, Phase 1과 병렬 가능)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 2-1 | 네이버 뉴스 API 연동 | 뉴스 수집기 | 검색 쿼리 생성 포함 |
| 2-2 | 기사 필터링 + 중복 제거 모듈 | 필터 모듈 | [v7] 2단계 클러스터링 |
| 2-3 | 기사 분류 모듈 (N1~N5) | 분류기 | LLM 기반 |
| 2-4 | LLM 추출 모듈 (N1, N4 전용 프롬프트 포함) | 정보 추출기 | 01_company_context 2.2절 taxonomy 연동 |
| 2-5 | 카테고리별 confidence ceiling 적용 보정 모듈 [v6 수정] | 보정 로직 | 차등 ceiling |
| 2-6 | 파일럿: 기업 20개 뉴스 수집 | 파일럿 결과 | 품질 검증 |
| 2-7 | 파일럿 검증: 언론사 본문 추출 성공률 측정 [v6 추가: C-4] | 검증 리포트 | 주요 언론사 10곳 |
| 2-8 | [v7 추가] P4~P6, N2/N3/N5 추출 프롬프트 초안 작성 | 프롬프트 셋 (선택 유형) | P1~P3/N1/N4 안정화 후 |

### Phase 3: 통합 및 CompanyContext 보강 (1주)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 3-1 | 크롤링 결과 -> CompanyContext 통합 모듈 | 통합 로직 | 소스 우선순위/충돌 해결 |
| 3-2 | facet score 병합 모듈 [v6 추가] | 병합 로직 | JD+크롤링 통합 (4.4절) |
| 3-3 | company_crawl_summary 집계 | 요약 테이블 | BigQuery |
| 3-4 | Graph 스키마 확장 및 크롤링 데이터 반영 [v6 추가] | Graph 업데이트 | Organization 노드 확장 |
| 3-5 | CompanyContext fill_rate 비교 (크롤링 전 vs 후) | 효과 리포트 | 핵심 성과 지표 |
| 3-6 | 배치 스케줄링 (Cloud Scheduler) | 운영 파이프라인 | 30일 주기 |
| 3-7 | [v7 추가] 집계 Cloud Function + Eventarc 설정 | 집계 트리거 | Primary + Backup 이중 구조 |

### Phase 4: 배치 실행 및 모니터링 (지속)

| # | 작업 | 산출물 | 비고 |
|---|---|---|---|
| 4-1 | 전체 대상 기업 크롤링 실행 | 크롤링 데이터 | 배치 |
| 4-2 | 실패/부분 성공 모니터링 | 대시보드 | 성공률/에러율 추적 |
| 4-3 | 추출 품질 샘플링 검수 (주간) | 품질 리포트 | 랜덤 20건 |
| 4-4 | STAGE_SIMILARITY 매트릭스 캘리브레이션 [v6 추가: A4-1] | 보정 매트릭스 | Human eval 50건 기반 |
| 4-5 | [v7 추가] facet 병합 threshold 캘리브레이션 | 확정 threshold | 4단계 절차 (4.4절) |
| 4-6 | [v7 추가] 뉴스 필터/중복 제거 임계값 검증 | 확정 임계값 | S-4, S-5 파일럿 결과 분석 |
| 4-7 | [v7 추가] 해시 전략 A/B 분석 및 확정 | 해시 전략 확정 | 불필요 재추출 비율 기준 |

---

## 7. 성과 측정 (KPI)

| 지표 | 측정 방법 | 목표 |
|---|---|---|
| **홈페이지 크롤링 성공률** | 크롤링 시도 기업 중 1페이지 이상 수집 성공 비율 | 80%+ |
| **뉴스 수집 커버리지** | 대상 기업 중 1건 이상 관련 기사 발견 비율 | 70%+ |
| **product_description 활성화율** | 크롤링 후 product_description != null 비율 | 60%+ |
| **structural_tensions 활성화율** | 크롤링 후 structural_tensions != null 비율 | 30%+ (뉴스 의존) |
| **stage_estimate confidence 상승** | 크롤링 전후 평균 confidence 비교 | +0.10 이상 |
| **operating_model facet confidence 상승** | 크롤링 전후 평균 confidence 비교 | +0.08 이상 |
| **CompanyContext fill_rate 상승** | 크롤링 전후 평균 fill_rate 비교 | 0.71 -> 0.85+ |

---

## 8. 비용 추정

### 기업 1,000개 기준 (월간)

| 항목 | 단가 | 수량 | 월비용 (추정) |
|---|---|---|---|
| Cloud Run (Playwright) | $0.01/건 | 1,000기업 x 10페이지 | $100 |
| 네이버 뉴스 API | 무료 (일 25,000건) | ~5,000 쿼리/월 | $0 |
| TheVC API | 월 정액 | -- | 확인 필요 |
| LLM (Gemini 2.0 Flash, 추출) | $0.10/1M input | ~5M tokens/월 | ~$0.5 |
| GCS 저장 | $0.02/GB | ~10GB | $0.2 |
| BigQuery | $5/TB 쿼리 | 소량 | $1~5 |
| **합계** | | | **~$107/월** |

재크롤링 주기 30일 기준. 해시 기반 변경 감지로 재추출 건수 감소 시 LLM 비용 절감 기대.

---

## 9. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|---|---|---|
| 홈페이지가 없는 기업 (소규모) | product_description null | 뉴스로 보완, 불가 시 NICE만 사용 |
| SPA 렌더링 실패율 높음 | 크롤링 성공률 저하 | HTTP GET fallback + 타임아웃 조정 |
| 뉴스에서 동명이인 기업 혼동 | 잘못된 정보 연결 | company_id + 산업코드로 교차 검증 |
| 네이버 API 호출 제한 | 수집량 부족 | 분산 스케줄링 + Google News 보조 |
| 크롤링 법적 리스크 | -- | robots.txt 준수, 개인정보 미수집, 요청 간격 준수 |
| LLM 추출 품질 불안정 | 잘못된 claim 생산 | evidence_span 필수, 주간 샘플링 검수 |
| 광고성 콘텐츠 과다 | facet 스코어 왜곡 | 광고성 필터 강화 (v6 운영 컨텍스트 검증) + LLM 판별 |
| 한국어 URL 인식 실패 | 크롤링 커버리지 저하 | 한국어 URL 패턴 딕셔너리 (v6) + BFS fallback |
| 언론사 본문 추출 실패 | 뉴스 추출 품질 저하 | 네이버 뉴스 캐시 페이지 fallback 검토 (파일럿 결과 기반) |
