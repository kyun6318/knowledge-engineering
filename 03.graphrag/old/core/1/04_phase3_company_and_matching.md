# Phase 3: 기업 정보 + 매칭 관계 (6주, Week 14-19)

> **목적**: JD 데이터와 기업 정보를 Graph에 추가하고, 후보자-공고 매칭 관계를 구축.
>
> **데이터 확장**: Candidate-Only Graph → **+ Vacancy, CompanyContext, Organization(ER), MappingFeatures**
>
> **에이전트 역량 변화**:
>   - "이 JD에 적합한 후보자 Top 20" → 매칭 스코어 기반 랭킹
>   - "시리즈B 핀테크 기업 채용공고" → 기업 조건 필터
>   - "이 후보자에게 적합한 포지션" → 역방향 매칭
>
> **사전 조건**: NICE DB 접근 확보 (또는 DART/사업자등록 대체), Phase 2 Go/No-Go 통과
>
> **인력**: DE 1명 + MLE 1명 풀타임

---

## 3-1. JD 파서 + Vacancy 노드 (1주) — Week 14

### 개요
JD(Job Description) 파싱을 프로덕션 수준으로 완성하고, Vacancy 노드로 Neo4j Graph에 적재.
Phase 2-1-7에서 초안이 완료되었으므로, 여기서는 스케일 테스트와 프로덕션화.

### Tasks (3-1-1 ~ 3-1-4)

**T3.1.1**: JD 파서 모듈 프로덕션화 (DE)
- Phase 2에서 작성한 초안 코드 검토 및 최적화
- 에러 처리 강화 (인코딩 에러, malformed HTML, 이미지 기반 PDF)
- 병렬 처리 설정 (Cloud Run Job 10 tasks parallel)
- 예상 처리 시간: 10K JD × 0.1초/건 = 1,000초 (약 17분, 10 parallel tasks)

**T3.1.2**: JD 섹션 분할 + 구조화 (DE)
- 섹션 감지 정규식 및 규칙 업그레이드
  - "역할", "책임", "자격요건", "우대사항", "혜택", "근무지", "근무 형태"
  - 중국어/일본어 JD 처리 (아시안 버전 JobDetail이 포함되는 경우)
- 섹션별 길이 제한 적용 (section_length_tokens 추적)
- BigQuery staging 테이블에 적재

**T3.1.3**: Vacancy Pydantic 모델 정의 (MLE)
```python
# src/models/kg/vacancy.py
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class VacancyBenefit(BaseModel):
    category: str  # 'salary_range', 'equity', 'location', 'flexible_work', 'health', 'education'
    value: str

class VacancyLocation(BaseModel):
    city: str
    district: Optional[str]
    country: str = "KR"
    remote_available: bool = False

class Vacancy(BaseModel):
    vacancy_id: str = Field(..., description="Unique vacancy ID from source")
    company_id: str
    title: str
    title_normalized: str  # "주니어 SE" → "Software Engineer_Junior"
    scope_type: str  # 'technical', 'product', 'design', 'business', 'operations'
    jd_url: Optional[str]
    posted_date: datetime
    deadline_date: Optional[datetime]
    is_active: bool = True

    # Structured content
    role_summary: str  # 150 tokens max
    responsibilities: List[str]  # 5~10 items, 200 tokens total
    required_qualifications: List[str]  # 5~8 items
    preferred_qualifications: List[str]
    years_of_experience: Optional[int]

    # Features for matching
    required_skills: List[str]  # Extracted from responsibilities + qualifications
    industry_codes: List[str]  # NICE code, 기업에서 상속
    locations: List[VacancyLocation]
    benefits: List[VacancyBenefit]
    employment_type: str  # 'full_time', 'contract', 'internship'

    # Metadata
    source_name: str  # 'jobkorea', 'saramin', 'wanted'
    source_id: str
    language: str = "ko"

    # Extraction confidence
    extraction_quality_score: float  # 0.0~1.0, LLM self-assessment
    section_coverage: dict  # {'role_summary': 0.95, 'skills': 0.87, ...}

    created_at: datetime
    updated_at: datetime
```

**T3.1.4**: JD → LLM 추출 + Batch API 실행 (MLE)
- Vacancy 필드 추출 Gemini Flash 프롬프트
- Batch API 활용 (Phase 1에서 구축한 동일 인프라)
- 비용 추정: 10K JD × 2,500 tokens avg (input) × $0.00004/1M = $1
- 처리 스케줄:
  ```bash
  gcloud run jobs create kg-jd-extraction \
    --image=$IMAGE \
    --command="python,src/extract_vacancies.py" \
    --tasks=10 \
    --max-retries=2 \
    --cpu=2 --memory=4Gi \
    --task-timeout=7200 \
    --service-account=kg-pipeline@graphrag-kg.iam.gserviceaccount.com \
    --region=asia-northeast3 \
    --env-vars="BATCH_SIZE=1000,MODEL=gemini-2.0-flash"
  ```

- 100건 파일럿 + 수동 검증 (정확도 측정):
  - scope_type 분류 정확도 > 70%
  - required_skills extraction recall > 75%
  - 섹션 커버리지 평균 > 85%

### 3-1 산출물
```
□ jd_parser.py (최적화 완료)
□ Vacancy Pydantic 모델 + 검증
□ BigQuery 스키마: graphrag_kg.staging_vacancy (10K rows)
□ Batch API 작업 실행 로그
□ 100건 수동 검증 리포트 (정확도 > 70%)
□ 프롬프트 버전: jd-extraction-v1.0
```

---

## 3-2. CompanyContext 파이프라인 (2주) — Week 15-16

### 개요
회사 정보를 다층 소스에서 수집: NICE DB(또는 대체) → Rule 엔진 → LLM 추출 → 통합.
Phase 2-1-1에서 Candidate resume의 CompanyContext를 경험했으므로, 여기서는 vacancy 기반으로 확대.

### Tasks (3-2-1 ~ 3-2-7)

**T3.2.1**: CompanyContext Pydantic 모델 정의 (MLE)
```python
# src/models/kg/company_context.py
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class FundingRound(BaseModel):
    round_type: str  # 'pre_seed', 'seed', 'series_a', 'series_b', ...
    amount_usd: Optional[float]
    date: Optional[datetime]
    investors: List[str] = []

class CompanyContext(BaseModel):
    company_id: str
    company_name: str
    company_name_en: Optional[str]

    # Basic info
    nice_industry_code: Optional[str]
    industry_name_ko: Optional[str]
    founded_year: Optional[int]
    headquarters: Optional[str]
    website: Optional[str]

    # Scale signals
    employee_count_estimate: Optional[int]  # From NICE or rule
    employee_scale_category: str  # 'micro', 'small', 'medium', 'large', 'enterprise'
    annual_revenue_krw_estimate: Optional[float]  # From NICE or news

    # Growth stage
    growth_stage: Optional[str]  # 'bootstrapped', 'seed', 'growth', 'mature', 'declining'
    growth_stage_confidence: float  # 0.0~1.0

    # Funding (from NICE or news crawl)
    funding_rounds: List[FundingRound] = []
    total_funding_usd: Optional[float]

    # Business profile
    primary_product: Optional[str]
    market_segment: Optional[str]
    business_model: Optional[str]  # 'B2B', 'B2C', 'B2B2C', 'P2P'

    # Organization metadata
    is_public: bool = False
    is_subsidiary: bool = False
    parent_company_id: Optional[str]
    founding_team_size: Optional[int]

    # Data quality
    source_of_truth: str  # 'nice_primary', 'rule_inferred', 'llm_extracted'
    completeness_score: float  # 0.0~1.0 (filled_fields / total_fields)
    confidence_by_field: dict  # {'employee_scale': 0.9, 'growth_stage': 0.6, ...}

    created_at: datetime
    updated_at: datetime
```

**T3.2.2**: NICE Lookup 모듈 구현 (DE)
- NICE DB 접근 API (또는 파트너 제공 REST endpoint)
- 조회 key: 회사명 (여러 스펠링 대응) + 사업자등록번호
- 캐싱 전략: Redis (1일 TTL) 또는 BigQuery lookup table
  ```python
  # src/connectors/nice_lookup.py
  class NICELookup:
      def __init__(self, api_key: str, redis_client=None):
          self.api_key = api_key
          self.redis = redis_client
          self.cache_ttl = 86400  # 1 day

      def lookup(self, company_name: str, biz_number: Optional[str] = None) -> Optional[dict]:
          """
          NICE DB 조회.
          Returns: {
              'nice_code': str,
              'company_name': str,
              'industry_code': str,
              'industry_name': str,
              'founded_year': int,
              'employee_count': int,
              'annual_revenue': float,
              'headquarters': str,
              'website': str,
              'status': 'active' | 'inactive'
          }
          """
          # 1. Cache check
          cache_key = f"nice:{company_name}:{biz_number}"
          cached = self.redis.get(cache_key) if self.redis else None
          if cached:
              return json.loads(cached)

          # 2. API call
          result = self._api_request(company_name, biz_number)

          # 3. Cache store
          if result and self.redis:
              self.redis.setex(cache_key, self.cache_ttl, json.dumps(result))

          return result

      def _api_request(self, company_name: str, biz_number: Optional[str]) -> Optional[dict]:
          """실제 NICE API 호출"""
          pass
  ```
- 실패 대체: 사업자등록상태 조회 (공개된 오픈 API) 또는 DART (상장사)

**T3.2.3**: Rule 엔진 구현 (DE)
- JD 텍스트 → 규칙 기반 회사 규모/업종/성장 단계 추정
- 규칙셋:
  ```python
  # src/rules/company_context_rules.py

  class CompanyContextRules:
      """
      JD 텍스트에서 회사 규모, 성장 단계를 추정하는 규칙 엔진.
      """

      # 직원 수 신호 (정규식)
      EMPLOYEE_SCALE_PATTERNS = {
          'micro': [
              r'(우리는|저희는|당사는)\s+(1~10명|5명\s*이하|소수정예)',
              r'스타트업',
          ],
          'small': [
              r'(우리는|저희는|당사는)\s+(10~50명|50명\s*이하)',
              r'(초기|초창기)\s+스타트업',
          ],
          'medium': [
              r'(우리는|저희는|당사는)\s+(50~300명|200명\s*규모)',
              r'(성장\s+중인|고성장)',
          ],
          'large': [
              r'(대기업|대형)',
              r'(500~|1,000~|5,000~)\s*명',
          ],
      }

      # 성장 단계 신호
      GROWTH_STAGE_PATTERNS = {
          'seed': [
              r'(시드|초기)\s*투자',
              r'(최근\s+)?설립',
          ],
          'growth': [
              r'(시리즈\s*[A-C]|Series\s+[A-C])\s*투자',
              r'(강한\s+)?성장세',
          ],
          'mature': [
              r'(안정적인|견고한)',
              r'(15년|20년|25년)\s+이상\s+(운영|역사)',
          ],
      }

      def infer_employee_scale(self, jd_text: str) -> tuple[str, float]:
          """직원 수 범주 추정. Returns (scale, confidence)"""
          for scale, patterns in self.EMPLOYEE_SCALE_PATTERNS.items():
              for pattern in patterns:
                  if re.search(pattern, jd_text, re.IGNORECASE):
                      return (scale, 0.7)  # 규칙 기반 신뢰도
          return (None, 0.0)

      def infer_growth_stage(self, jd_text: str) -> tuple[str, float]:
          """성장 단계 추정"""
          for stage, patterns in self.GROWTH_STAGE_PATTERNS.items():
              for pattern in patterns:
                  if re.search(pattern, jd_text, re.IGNORECASE):
                      return (stage, 0.65)
          return (None, 0.0)
  ```

**T3.2.4**: LLM CompanyContext 추출 프롬프트 (MLE)
- Gemini Flash 기반 프롬프트
- 입력: JD 텍스트 + NICE lookup 결과 (선택사항)
- 출력: CompanyContext JSON

```
# src/prompts/extract_company_context.txt

당신은 채용공고에서 회사 정보를 추출하는 전문가입니다.

주어진 채용공고(JD) 텍스트에서 다음 필드를 추출하세요:

## 필드 정의

1. **primary_product**: 회사의 주요 제품/서비스 (100 tokens max)
2. **market_segment**: 대상 시장 또는 고객 (50 tokens max)
3. **business_model**: B2B, B2C, B2B2C, P2P 중 선택
4. **growth_signals**: JD에 드러나는 성장 신호 (예: "빠른 확장", "신규 부서 설립")
5. **team_maturity**: 팀의 성숙도 신호 (예: "체계적인 프로세스", "스타트업 특유의 유연성")

## 입력 데이터

JD 텍스트:
{jd_text}

NICE 조회 결과 (available):
{nice_context_json}

## 출력 포맷

```json
{
  "primary_product": "string",
  "market_segment": "string",
  "business_model": "string",
  "growth_signals": ["signal1", "signal2", ...],
  "team_maturity": "string",
  "extraction_confidence": 0.85,
  "missing_fields": ["field1", "field2"]
}
```

## 주의사항

- 텍스트에 명시되지 않은 정보는 생성하지 마세요 (hallucination 방지)
- 신뢰도 점수는 텍스트 증거 기반으로만 부여하세요
- 한국어 회사명은 정규화하지 않습니다 (있는 그대로 보존)
```

- Batch API 실행 (Phase 1 동일 인프라)
- 비용: 10K JD × 1,500 tokens (input + NICE context) × $0.00004/1M = $0.60

**T3.2.5**: CompanyContext 통합 로직 (DE)
- NICE lookup > Rule > LLM 우선순위로 병합
- 소스별 신뢰도 가중치:
  ```python
  # src/pipelines/company_context_integration.py

  class CompanyContextIntegration:
      """
      NICE, Rule, LLM 결과를 병합하여 최종 CompanyContext 생성.
      """

      SOURCE_WEIGHTS = {
          'nice_primary': 0.95,     # NICE DB 우선 신뢰
          'rule_inferred': 0.60,    # Rule 기반 신호
          'llm_extracted': 0.70,    # LLM 추출
      }

      def merge(self,
                nice_result: Optional[dict],
                rule_result: dict,
                llm_result: dict) -> CompanyContext:
          """
          3가지 소스를 병합.
          우선순위: NICE > LLM > Rule
          """
          merged = CompanyContext(
              company_id=...,
              company_name=...,
          )

          # 1. NICE 우선 적용
          if nice_result:
              merged.employee_scale_category = nice_result['employee_scale']
              merged.industry_name_ko = nice_result['industry_name']
              merged.founded_year = nice_result['founded_year']
              merged.source_of_truth = 'nice_primary'

          # 2. Rule 기반 추정 (NICE에 없는 필드)
          if not merged.employee_scale_category and rule_result:
              scale, conf = rule_result['employee_scale']
              if scale:
                  merged.employee_scale_category = scale
                  merged.confidence_by_field['employee_scale'] = conf

          # 3. LLM 추출 (구조화되지 않은 필드)
          if llm_result:
              merged.primary_product = llm_result.get('primary_product')
              merged.market_segment = llm_result.get('market_segment')
              merged.business_model = llm_result.get('business_model')
              merged.confidence_by_field.update({
                  'primary_product': llm_result.get('extraction_confidence', 0.7),
              })

          # 4. 완성도 계산
          filled_count = sum(1 for v in vars(merged).values() if v is not None)
          merged.completeness_score = filled_count / len(vars(merged))

          return merged
  ```

**T3.2.6**: 100건 파일럿 + 품질 확인 (MLE)
- 수동 검증 100건 (정확도 측정)
- completeness_score 평균 목표: > 0.75
- 각 필드별 신뢰도 분포 분석

**T3.2.7**: BigQuery 적재 (DE)
```sql
-- graphrag_kg.company_context
CREATE TABLE graphrag_kg.company_context (
  company_id STRING NOT NULL,
  company_name STRING NOT NULL,
  company_name_en STRING,
  nice_industry_code STRING,
  industry_name_ko STRING,

  founded_year INT64,
  headquarters STRING,
  website STRING,

  employee_count_estimate INT64,
  employee_scale_category STRING,
  annual_revenue_krw_estimate FLOAT64,

  growth_stage STRING,
  growth_stage_confidence FLOAT64,

  funding_rounds JSON,
  total_funding_usd FLOAT64,

  primary_product STRING,
  market_segment STRING,
  business_model STRING,

  is_public BOOL DEFAULT FALSE,
  is_subsidiary BOOL DEFAULT FALSE,
  parent_company_id STRING,

  source_of_truth STRING,
  completeness_score FLOAT64,
  confidence_by_field JSON,

  created_at TIMESTAMP,
  updated_at TIMESTAMP,

  PRIMARY KEY (company_id) NOT ENFORCED
);
```

### 3-2 산출물
```
□ CompanyContext Pydantic 모델
□ NICE Lookup 모듈 + Redis 캐싱
□ Rule 엔진 (employee_scale, growth_stage 추정)
□ LLM 프롬프트 (extract_company_context.txt)
□ 통합 로직 (CompanyContextIntegration)
□ BigQuery 스키마 + 데이터 (10K rows)
□ 100건 수동 검증 리포트 (completeness > 75%)
```

---

## 3-3. Organization ER + 한국어 특화 (1주) — Week 17

### 개요
수백 개의 회사명이 여러 형태(축약, 영문, 정식명칭)로 나타남.
Entity Resolution(ER)을 통해 동일 조직을 하나의 노드로 통합.
한국어 특화 정규화 규칙 적용.

### Tasks (3-3-1 ~ 3-3-5)

**T3.3.1**: 한국어 회사명 정규화 전처리 (DE)
```python
# src/preprocessing/company_name_normalization.py

class CompanyNameNormalizer:
    """
    한국어 회사명 정규화:
    - 법인 형태 제거
    - 부서/사업부 분리
    - 공백/특수문자 정규화
    """

    LEGAL_FORM_PATTERNS = {
        '주식회사': ['(주)', '주식회사', '㈜', 'Co., Ltd.', 'Corp.'],
        '유한회사': ['(유)', '유한회사', '유한책임회사'],
        '협동조합': ['(협)', '협동조합'],
        '사회적기업': ['사회적기업'],
    }

    DIVISION_SEPARATORS = ['부문', '그룹', '계열사', '자회사', '지사', '본부']

    def normalize(self, company_name: str) -> dict:
        """
        정규화된 회사명 반환.
        Returns: {
            'normalized_name': str,
            'legal_form': str,  # 추출된 법인 형태
            'division': Optional[str],  # 부서/사업부 (있으면)
            'original_name': str,
        }
        """
        name = company_name.strip()

        # 1. 법인 형태 제거 (우선순위 순)
        legal_form = None
        for form, patterns in self.LEGAL_FORM_PATTERNS.items():
            for pattern in patterns:
                if pattern in name:
                    name = name.replace(pattern, '').strip()
                    legal_form = form
                    break

        # 2. 부서/사업부 분리
        division = None
        for sep in self.DIVISION_SEPARATORS:
            if sep in name:
                parts = name.split(sep, 1)
                name = parts[0].strip()
                division = parts[1].strip() if len(parts) > 1 else None
                break

        # 3. 공백/특수문자 정규화
        name = re.sub(r'\s+', ' ', name)  # 연속 공백 제거
        name = name.strip()

        return {
            'normalized_name': name,
            'legal_form': legal_form,
            'division': division,
            'original_name': company_name,
        }

    def normalize_batch(self, company_names: list) -> list:
        """배치 정규화"""
        return [self.normalize(name) for name in company_names]
```

**T3.3.2**: ER 알고리즘 3단계 구현 (DE)
```python
# src/entity_resolution/company_er.py

class CompanyEntityResolver:
    """
    한국어 회사 Entity Resolution.
    3단계: 사전 매칭 → 문자열 유사도 → NICE 확인
    """

    def __init__(self, alias_db_path: str = None, nice_lookup: NICELookup = None):
        self.alias_db = self._load_alias_db(alias_db_path)
        self.nice_lookup = nice_lookup

    def resolve(self, company_names: list) -> dict:
        """
        company_names 리스트의 Entity Resolution.
        Returns: {
            'merged_organizations': [
                {
                    'org_id': 'org_001',
                    'canonical_name': 'Samsung Electronics',
                    'aliases': ['삼성전자', '삼성전자 DS부문'],
                    'nice_code': '1234567890',
                    'confidence': 0.95,
                    'merge_method': 'dictionary' | 'jaro_winkler' | 'nice_number',
                }
            ],
            'unmerged_candidates': [
                {
                    'names': ['회사A', '회사B'],
                    'similarity': 0.82,
                    'recommendation': 'manual_review',
                }
            ]
        }
        """
        normalized = [self._normalize(name) for name in company_names]

        # Step 1: Dictionary matching
        merged_dict = {}  # org_id -> organization
        remaining = []

        for norm_item in normalized:
            canonical = self.alias_db.get(norm_item['normalized_name'])
            if canonical:
                org_id = canonical['org_id']
                if org_id not in merged_dict:
                    merged_dict[org_id] = {
                        'org_id': org_id,
                        'canonical_name': canonical['canonical_name'],
                        'aliases': set(),
                        'nice_code': canonical.get('nice_code'),
                        'confidence': 0.95,
                        'merge_method': 'dictionary',
                    }
                merged_dict[org_id]['aliases'].add(norm_item['original_name'])
            else:
                remaining.append(norm_item)

        # Step 2: Jaro-Winkler similarity
        unmerged = []
        for i, item1 in enumerate(remaining):
            matched = False
            for j, item2 in enumerate(remaining[i+1:]):
                sim = self._jaro_winkler(item1['normalized_name'], item2['normalized_name'])
                if sim >= 0.85:  # 임계값
                    # 병합
                    org_id = f"org_{len(merged_dict)}"
                    merged_dict[org_id] = {
                        'org_id': org_id,
                        'canonical_name': item1['normalized_name'],
                        'aliases': {item1['original_name'], item2['original_name']},
                        'nice_code': None,
                        'confidence': sim,
                        'merge_method': 'jaro_winkler',
                    }
                    remaining[i+j+1] = None  # 마킹
                    matched = True
                    break

            if not matched:
                unmerged.append({'name': item1['original_name'], 'reason': 'no_match'})

        # Step 3: NICE 확인 (optional)
        if self.nice_lookup:
            for org in merged_dict.values():
                if not org['nice_code']:
                    nice_result = self.nice_lookup.lookup(org['canonical_name'])
                    if nice_result:
                        org['nice_code'] = nice_result['nice_code']
                        org['confidence'] = 0.98
                        org['merge_method'] = 'nice_number'

        return {
            'merged_organizations': list(merged_dict.values()),
            'unmerged_candidates': unmerged,
            'total_organizations': len(merged_dict),
        }

    def _normalize(self, name: str) -> dict:
        """정규화"""
        normalizer = CompanyNameNormalizer()
        return normalizer.normalize(name)

    def _jaro_winkler(self, s1: str, s2: str) -> float:
        """Jaro-Winkler 유사도"""
        from difflib import SequenceMatcher
        # 또는 jellyfish 라이브러리 사용
        return textdistance.jaro_winkler(s1, s2)

    def _load_alias_db(self, path: str) -> dict:
        """회사명 별칭 데이터베이스 로드"""
        if not path:
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
```

**T3.3.3**: 회사명 별칭 데이터베이스 구축 (DE)
```json
// data/company_alias.json (샘플)
{
  "삼성전자": {
    "org_id": "org_samsung_elec",
    "canonical_name": "Samsung Electronics",
    "nice_code": "1234567890",
    "aliases": ["Samsung", "삼성", "삼성전자"],
    "divisions": {
      "DS부문": "Samsung Semiconductor",
      "네트워크사업부": "Samsung Network"
    }
  },
  "카카오": {
    "org_id": "org_kakao",
    "canonical_name": "Kakao Corporation",
    "nice_code": "0987654321",
    "aliases": ["KAKAO", "카카오"]
  },
  "배달의민족": {
    "org_id": "org_bmin",
    "canonical_name": "Woowa Brothers",
    "nice_code": "5555555555",
    "aliases": ["배달의민족", "우아한형제들"],
    "parent_org": "org_kakao"
  }
}
```

**T3.3.4**: ER 결과 검증 + 반복 (DE/MLE)
- ER 알고리즘 실행: Phase 2에서 수집된 모든 회사명 → ER
- 500개 Organization 노드 생성 예상
- 정확도 측정: Precision, Recall (Confusion Matrix)

**T3.3.5**: 전수 검수 (DE/MLE 공동, 0.5일)
```
검수 프로세스:
1. 병합된 Organization 노드 500개 목록 출력
   - canonical_name, aliases, nice_code, merge_method, confidence
2. 각 조직별 합의된 매칭 확인 (임계값 < 0.85인 케이스 우선)
3. 미병합 유사 조직 후보 (similarity 0.75~0.85) 검토
   - 예: "메타", "Meta Korea" → 수동 병합 여부 결정
4. 발견된 패턴 → company_alias.json에 피드백
   - 예: "빅헬스" → "Big Health Korea" 수동 병합
```

**정확도 목표**:
- Precision ≥ 95% (잘못된 병합 최소화)
- Recall ≥ 80% (놓친 병합 최소화)

### 3-3 산출물
```
□ 한국어 정규화 모듈 (CompanyNameNormalizer)
□ ER 알고리즘 3단계 (CompanyEntityResolver)
□ company_alias.json 구축
□ 500개 Organization 노드
□ 전수 검수 완료 (Precision ≥ 95%, Recall ≥ 80%)
□ Neo4j Organization 노드 적재
□ 통합 리포트 (merging statistics)
```

---

## 3-4. MappingFeatures + MAPPED_TO (2주) — Week 18-19

### 개요
후보자 (Person) - 공고 (Vacancy) 간 매칭 피처를 계산하고, MAPPED_TO 관계로 모델링.
매칭 점수는 다중 피처의 가중합: scope_type, skill overlap, seniority, industry, embedding 유사도.

### Tasks (3-4-1 ~ 3-4-6)

**T3.4.1**: MappingFeatures 데이터 모델 (MLE)
```python
# src/models/kg/mapping_features.py

class MappingFeatures(BaseModel):
    """후보자-공고 매칭 피처"""

    candidate_id: str
    vacancy_id: str

    # 1. Scope Type Match
    candidate_scope_type: str  # technical, product, design, business, operations
    vacancy_scope_type: str
    scope_type_match: bool  # exact match
    scope_type_score: float  # 0.0~1.0

    # 2. Skill Overlap
    candidate_skills: List[str]  # extracted from resume chapters
    vacancy_skills: List[str]  # extracted from JD
    skill_overlap_set: List[str]  # intersection
    skill_overlap_score: float  # Jaccard or cosine

    # 3. Seniority Match
    candidate_seniority_years: int
    vacancy_min_years: int
    vacancy_max_years: Optional[int]
    seniority_within_range: bool
    seniority_match: float  # 0.0~1.0 (distance penalty)

    # 4. Industry Match
    candidate_industries: List[str]  # NICE codes from resume
    vacancy_industry: str  # NICE code from company
    industry_match: float  # 0.0~1.0 (exact + similar)

    # 5. Text Embedding Cosine
    candidate_embedding_summary: List[float]  # 768-dim vector
    vacancy_embedding_summary: List[float]
    embedding_cosine: float  # cosine similarity

    # 6. Overall Score
    overall_match_score: float  # weighted sum of above

    # Metadata
    active_feature_count: int  # non-null features
    computed_at: datetime
```

**T3.4.2**: 매칭 피처 계산 로직 (MLE)
```python
# src/compute/mapping_features.py

class MappingFeaturesCompute:
    """
    후보자-공고 매칭 피처 계산.
    가중치 설정:
    - scope_type_match: 0.20
    - skill_overlap: 0.25
    - seniority_match: 0.15
    - industry_match: 0.15
    - embedding_cosine: 0.25
    """

    WEIGHTS = {
        'scope_type': 0.20,
        'skill_overlap': 0.25,
        'seniority': 0.15,
        'industry': 0.15,
        'embedding': 0.25,
    }

    def __init__(self, neo4j_driver, bigquery_client, embedding_service):
        self.neo4j = neo4j_driver
        self.bq = bigquery_client
        self.embeddings = embedding_service

    def compute_all_pairs(self, batch_size: int = 1000) -> Iterator[MappingFeatures]:
        """
        모든 (candidate, vacancy) 쌍에 대해 MappingFeatures 계산.
        배치 처리로 확장성 확보.

        예상 쌍의 수: 100K candidates × 10K vacancies = 1B pairs
        → 필터링: active candidates + recent vacancies만 처리
        """

        # Candidate 데이터 로드 (BigQuery)
        candidates = self._load_active_candidates(batch_size)
        vacancies = self._load_active_vacancies()

        for candidate_batch in candidates:
            for candidate in candidate_batch:
                for vacancy in vacancies:
                    features = self.compute_pair(candidate, vacancy)
                    if features.active_feature_count >= 3:  # 최소 3개 피처 필수
                        yield features

    def compute_pair(self, candidate: dict, vacancy: dict) -> MappingFeatures:
        """한 쌍의 매칭 피처 계산"""

        # 1. Scope Type Match
        scope_match, scope_score = self._compute_scope_type(
            candidate['scope_type'],
            vacancy['scope_type']
        )

        # 2. Skill Overlap
        skill_score = self._compute_skill_overlap(
            candidate['skills'],
            vacancy['required_skills']
        )

        # 3. Seniority Match
        seniority_match, seniority_score = self._compute_seniority(
            candidate['years_of_experience'],
            vacancy['years_of_experience'],
            vacancy.get('years_of_experience_max')
        )

        # 4. Industry Match
        industry_score = self._compute_industry(
            candidate['industry_codes'],
            vacancy['industry_codes']
        )

        # 5. Embedding Cosine
        embedding_score = self._compute_embedding_cosine(
            candidate['candidate_id'],
            vacancy['vacancy_id']
        )

        # 6. Overall Score (가중합)
        overall_score = (
            self.WEIGHTS['scope_type'] * scope_score +
            self.WEIGHTS['skill_overlap'] * skill_score +
            self.WEIGHTS['seniority'] * seniority_score +
            self.WEIGHTS['industry'] * industry_score +
            self.WEIGHTS['embedding'] * embedding_score
        )

        active_count = sum([
            int(scope_score > 0),
            int(skill_score > 0),
            int(seniority_score > 0),
            int(industry_score > 0),
            int(embedding_score > 0),
        ])

        return MappingFeatures(
            candidate_id=candidate['candidate_id'],
            vacancy_id=vacancy['vacancy_id'],
            scope_type_match=scope_match,
            scope_type_score=scope_score,
            skill_overlap_score=skill_score,
            seniority_match=seniority_match,
            seniority_match_score=seniority_score,
            industry_match=industry_score,
            embedding_cosine=embedding_score,
            overall_match_score=overall_score,
            active_feature_count=active_count,
            computed_at=datetime.utcnow(),
        )

    def _compute_scope_type(self, cand_type: str, vacancy_type: str) -> tuple:
        """Scope Type 일치도"""
        is_match = cand_type == vacancy_type
        score = 1.0 if is_match else 0.0
        return (is_match, score)

    def _compute_skill_overlap(self, cand_skills: list, vacancy_skills: list) -> float:
        """Skill 겹침 (Jaccard)"""
        if not vacancy_skills:
            return 0.0

        cand_set = set(cand_skills)
        vacancy_set = set(vacancy_skills)

        intersection = len(cand_set & vacancy_set)
        union = len(cand_set | vacancy_set)

        jaccard = intersection / union if union > 0 else 0.0
        return min(jaccard, 1.0)

    def _compute_seniority(self, cand_years: int, vac_min: int, vac_max: Optional[int]) -> tuple:
        """Seniority 범위 일치도"""
        if cand_years < vac_min:
            # 너무 junior
            gap = vac_min - cand_years
            score = max(0.0, 1.0 - (gap * 0.1))
            return (False, score)
        elif vac_max and cand_years > vac_max:
            # 너무 senior
            gap = cand_years - vac_max
            score = max(0.0, 1.0 - (gap * 0.05))  # senior은 페널티 작게
            return (False, score)
        else:
            # 범위 내
            return (True, 1.0)

    def _compute_industry(self, cand_codes: list, vacancy_codes: list) -> float:
        """Industry 매칭"""
        if not vacancy_codes or not cand_codes:
            return 0.0

        # Exact match
        if set(cand_codes) & set(vacancy_codes):
            return 1.0

        # Partial match (상위 카테고리)
        # NICE 코드: 5자리, 앞 3자리가 대분류
        cand_major = {code[:3] for code in cand_codes}
        vacancy_major = {code[:3] for code in vacancy_codes}

        if cand_major & vacancy_major:
            return 0.7

        return 0.0

    def _compute_embedding_cosine(self, candidate_id: str, vacancy_id: str) -> float:
        """Embedding 코사인 유사도"""
        cand_emb = self.embeddings.get_candidate_embedding(candidate_id)
        vac_emb = self.embeddings.get_vacancy_embedding(vacancy_id)

        if not cand_emb or not vac_emb:
            return 0.0

        from sklearn.metrics.pairwise import cosine_similarity
        score = cosine_similarity([cand_emb], [vac_emb])[0][0]
        return max(0.0, min(1.0, (score + 1) / 2))  # [-1, 1] → [0, 1]

    def _load_active_candidates(self, batch_size: int):
        """활성 후보자 로드 (BigQuery)"""
        query = """
        SELECT
            candidate_id,
            scope_type,
            years_of_experience,
            industry_codes,
            skills,
            candidate_embedding_summary
        FROM graphrag_kg.candidate_summary
        WHERE is_active = TRUE
        ORDER BY candidate_id
        """
        # BigQuery pagination 구현
        pass

    def _load_active_vacancies(self):
        """활성 공고 로드"""
        query = """
        SELECT
            vacancy_id,
            scope_type,
            years_of_experience,
            industry_codes,
            required_skills,
            vacancy_embedding_summary
        FROM graphrag_kg.vacancy_summary
        WHERE is_active = TRUE
        """
        pass
```

**T3.4.3**: MAPPED_TO 관계 Neo4j 적재 (DE)
```cypher
-- MAPPED_TO 관계 생성 및 속성 적재
WITH {mapping_features_json} as features
MATCH (c:Person {candidate_id: features.candidate_id})
MATCH (v:Vacancy {vacancy_id: features.vacancy_id})
CREATE (c)-[m:MAPPED_TO]->(v)
SET
  m.scope_type_match = features.scope_type_match,
  m.scope_type_score = features.scope_type_score,
  m.skill_overlap_score = features.skill_overlap_score,
  m.seniority_match = features.seniority_match,
  m.seniority_match_score = features.seniority_match_score,
  m.industry_match = features.industry_match,
  m.embedding_cosine = features.embedding_cosine,
  m.overall_match_score = features.overall_match_score,
  m.active_feature_count = features.active_feature_count,
  m.computed_at = features.computed_at
RETURN COUNT(m) as created_relationships;
```

```python
# src/load/neo4j_mapping_loader.py

class Neo4jMappingLoader:
    """MAPPED_TO 관계 적재"""

    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self.batch_size = 5000

    def load_mappings(self, mapping_features_iter: Iterator[MappingFeatures]):
        """스트리밍으로 MAPPED_TO 관계 적재"""
        batch = []

        with self.driver.session() as session:
            for features in mapping_features_iter:
                batch.append(features.dict())

                if len(batch) >= self.batch_size:
                    self._write_batch(session, batch)
                    batch = []

            # 남은 배치 처리
            if batch:
                self._write_batch(session, batch)

    def _write_batch(self, session, batch: list):
        """배치 쓰기"""
        query = """
        UNWIND $batch as feature
        MATCH (c:Person {candidate_id: feature.candidate_id})
        MATCH (v:Vacancy {vacancy_id: feature.vacancy_id})
        MERGE (c)-[m:MAPPED_TO]->(v)
        SET
          m.scope_type_score = feature.scope_type_score,
          m.skill_overlap_score = feature.skill_overlap_score,
          m.seniority_match = feature.seniority_match,
          m.seniority_match_score = feature.seniority_match_score,
          m.industry_match = feature.industry_match,
          m.embedding_cosine = feature.embedding_cosine,
          m.overall_match_score = feature.overall_match_score,
          m.active_feature_count = feature.active_feature_count,
          m.computed_at = feature.computed_at
        RETURN COUNT(m) as upserted
        """

        result = session.run(query, batch=batch)
        count = result.single()['upserted']
        print(f"Loaded {count} MAPPED_TO relationships")
```

**T3.4.4**: BigQuery 서빙 테이블 (DE)
```sql
-- graphrag_kg.mapping_features (서빙 테이블)
CREATE TABLE graphrag_kg.mapping_features (
  candidate_id STRING NOT NULL,
  vacancy_id STRING NOT NULL,
  scope_type_score FLOAT64,
  skill_overlap_score FLOAT64,
  seniority_match BOOL,
  seniority_match_score FLOAT64,
  industry_match FLOAT64,
  embedding_cosine FLOAT64,
  overall_match_score FLOAT64,
  active_feature_count INT64,
  computed_at TIMESTAMP,

  PRIMARY KEY (candidate_id, vacancy_id) NOT ENFORCED,
  FOREIGN KEY (candidate_id) REFERENCES graphrag_kg.candidate_summary(candidate_id) NOT ENFORCED,
  FOREIGN KEY (vacancy_id) REFERENCES graphrag_kg.vacancy_summary(vacancy_id) NOT ENFORCED
);

-- 인덱스
CREATE SNAPSHOT TABLE graphrag_kg.mapping_features_idx_overall
CLONE graphrag_kg.mapping_features;

-- Clustering
ALTER TABLE graphrag_kg.mapping_features
CLUSTER BY overall_match_score DESC, computed_at DESC;
```

**T3.4.5**: 에이전트 서빙 인터페이스 (SQL 예시 + 문서) (MLE)

SQL 예시 5종:
```sql
-- 1. JD 기반 후보자 매칭 (Top N)
SELECT
  c.candidate_id,
  c.name,
  c.seniority_estimate,
  m.overall_match_score,
  m.skill_overlap_score,
  m.scope_type_score,
FROM graphrag_kg.mapping_features m
JOIN graphrag_kg.candidate_summary c ON m.candidate_id = c.candidate_id
WHERE m.vacancy_id = @vacancy_id
  AND m.overall_match_score >= 0.5
ORDER BY m.overall_match_score DESC
LIMIT @limit;

-- 2. 후보자 기반 적합 포지션 (역방향)
SELECT
  v.vacancy_id,
  v.title,
  v.scope_type,
  o.company_name,
  m.overall_match_score,
FROM graphrag_kg.mapping_features m
JOIN graphrag_kg.vacancy_summary v ON m.vacancy_id = v.vacancy_id
JOIN graphrag_kg.company_context o ON v.company_id = o.company_id
WHERE m.candidate_id = @candidate_id
  AND m.overall_match_score >= 0.5
ORDER BY m.overall_match_score DESC;

-- 3. 기업 조건 필터 매칭 (industry + score)
SELECT
  v.vacancy_id,
  v.title,
  c.candidate_id,
  c.name,
  m.overall_match_score,
  o.company_name,
FROM graphrag_kg.mapping_features m
JOIN graphrag_kg.vacancy_summary v ON m.vacancy_id = v.vacancy_id
JOIN graphrag_kg.candidate_summary c ON m.candidate_id = c.candidate_id
JOIN graphrag_kg.company_context o ON v.company_id = o.company_id
WHERE o.industry_name_ko = @industry
  AND m.overall_match_score >= @min_score
ORDER BY m.overall_match_score DESC;

-- 4. 업종별 매칭 통계
SELECT
  o.industry_name_ko,
  COUNT(DISTINCT m.vacancy_id) as vacancy_count,
  COUNT(DISTINCT m.candidate_id) as candidate_count,
  AVG(m.overall_match_score) as avg_match_score,
  PERCENTILE_CONT(m.overall_match_score, 0.5) OVER() as median_score,
FROM graphrag_kg.mapping_features m
JOIN graphrag_kg.vacancy_summary v ON m.vacancy_id = v.vacancy_id
JOIN graphrag_kg.company_context o ON v.company_id = o.company_id
WHERE m.overall_match_score >= 0.5
GROUP BY o.industry_name_ko
ORDER BY vacancy_count DESC;

-- 5. 스킬 갭 분석
SELECT
  m.candidate_id,
  m.vacancy_id,
  c.skills as candidate_skills,
  v.required_skills as vacancy_skills,
  ARRAY(
    SELECT skill FROM UNNEST(v.required_skills) as skill
    WHERE skill NOT IN UNNEST(c.skills)
  ) as missing_skills,
FROM graphrag_kg.mapping_features m
JOIN graphrag_kg.candidate_summary c ON m.candidate_id = c.candidate_id
JOIN graphrag_kg.vacancy_summary v ON m.vacancy_id = v.vacancy_id
WHERE m.overall_match_score >= 0.6
ORDER BY m.overall_match_score DESC
LIMIT 100;
```

**T3.4.6**: 수동 검증 50건 (MLE)
- 상위 매칭 점수 50건 + 하위 점수 50건 샘플
- 검증 지표:
  - 도메인 전문가 동의도 (주관적)
  - Skill 겹침 정확도 (객관적)
  - Overall score 분포의 합리성

### 3-4 산출물
```
□ MappingFeatures 데이터 모델
□ 매칭 피처 계산 로직 (5가지 피처, 가중합)
□ MAPPED_TO 관계 Neo4j 적재 (예상 수십억 관계)
□ BigQuery mapping_features 서빙 테이블
□ SQL 예시 5종 (에이전트 서빙)
□ 수동 검증 100건 완료
```

---

## 3-5. 테스트 인프라 + Regression Test (1주, 3-4와 병행) — Week 19

### 개요
Phase 3 전체 파이프라인의 품질을 보증하기 위해 Golden test set을 구축하고
자동화된 regression test를 구성.

### Tasks (3-5-1 ~ 3-5-3)

**T3.5.1**: Golden 50건 regression test suite 구축 (MLE)
```python
# tests/test_phase3_golden_set.py

import pytest
from src.models.kg import Vacancy, CompanyContext, MappingFeatures
from src.compute.mapping_features import MappingFeaturesCompute

class TestPhase3Golden:
    """Phase 3 Golden test set (50건)"""

    @pytest.fixture
    def golden_data(self):
        """수동 검증된 50건 샘플"""
        return [
            {
                'candidate_id': 'golden_001',
                'vacancy_id': 'golden_jd_001',
                'candidate_seniority_years': 5,
                'vacancy_scope_type': 'technical',
                'expected_overall_score': 0.75,  # 도메인 전문가 판정
                'expected_top_n': 3,  # Top 3 매칭 내 포함 여부
            },
            # ... 49개 더
        ]

    def test_vacancy_extraction(self, golden_data):
        """JD 파서 정확도"""
        for item in golden_data:
            jd_id = item['vacancy_id']
            vacancy = Vacancy.from_jd(jd_id)

            assert vacancy.scope_type == item['vacancy_scope_type']
            assert len(vacancy.required_skills) > 0
            assert vacancy.extraction_quality_score > 0.7

    def test_company_context_completeness(self, golden_data):
        """CompanyContext 완성도"""
        # 각 vacancy의 회사 정보 확인
        for item in golden_data:
            company_id = self._get_company_from_vacancy(item['vacancy_id'])
            context = CompanyContext.from_db(company_id)

            assert context.completeness_score > 0.7
            assert context.source_of_truth in ['nice_primary', 'llm_extracted']

    def test_mapping_score_range(self, golden_data):
        """매칭 점수 범위 검증"""
        for item in golden_data:
            features = MappingFeatures.from_db(
                item['candidate_id'],
                item['vacancy_id']
            )

            # 점수는 0~1 범위
            assert 0.0 <= features.overall_match_score <= 1.0
            assert 0.0 <= features.skill_overlap_score <= 1.0
            assert 0.0 <= features.embedding_cosine <= 1.0

    def test_top_n_ranking(self, golden_data):
        """Top N 순위 정확도"""
        for item in golden_data:
            top_matches = self._get_top_matches(
                item['candidate_id'],
                limit=10
            )

            vacancy_rank = next(
                (i for i, m in enumerate(top_matches)
                 if m.vacancy_id == item['vacancy_id']),
                None
            )

            assert vacancy_rank is not None
            assert vacancy_rank < item['expected_top_n']

    def _get_company_from_vacancy(self, vacancy_id: str) -> str:
        """vacancy → company_id 조회"""
        pass

    def _get_top_matches(self, candidate_id: str, limit: int):
        """상위 매칭 조회"""
        pass
```

**T3.5.2**: 단위 테스트 (파서, 모델, 추출기) (DE/MLE)
```python
# tests/unit/

# test_jd_parser.py
def test_jd_section_extraction():
    """JD 섹션 분할"""
    jd_text = "...역할: ... 자격요건: ... 우대사항: ..."
    sections = parse_jd_sections(jd_text)

    assert 'role' in sections
    assert 'qualifications' in sections
    assert len(sections['role']) > 0

# test_company_name_normalization.py
def test_normalize_korean_company():
    """한국어 회사명 정규화"""
    normalizer = CompanyNameNormalizer()

    assert normalizer.normalize("(주)삼성전자")['normalized_name'] == "삼성전자"
    assert normalizer.normalize("삼성전자 DS부문")['division'] == "DS부문"
    assert normalizer.normalize("㈜카카오")['normalized_name'] == "카카오"

# test_entity_resolution.py
def test_jaro_winkler_similarity():
    """문자열 유사도"""
    resolver = CompanyEntityResolver()

    sim = resolver._jaro_winkler("메타코리아", "Meta Korea")
    assert 0.7 < sim < 0.9  # Partial match

# test_mapping_features.py
def test_skill_overlap_jaccard():
    """Skill Jaccard 유사도"""
    compute = MappingFeaturesCompute(None, None, None)

    score = compute._compute_skill_overlap(
        ['Python', 'SQL', 'AWS'],
        ['Python', 'SQL', 'GCP']
    )

    assert 0.5 < score < 1.0  # 2/4 = 0.5
```

**T3.5.3**: 통합 테스트 (JD 100건 + 이력서 1,000건 E2E) (DE/MLE)
```python
# tests/integration/test_phase3_e2e.py

class TestPhase3E2E:
    """End-to-end 통합 테스트"""

    def test_full_pipeline_100_jds_1000_candidates(self):
        """
        JD 100건 → Vacancy 추출 → Company Context
        + Candidate 1,000건 → 매칭 계산
        """

        # 1. Load test data
        jds = load_test_jds(100)
        candidates = load_test_candidates(1000)

        # 2. JD extraction
        vacancies = [extract_vacancy(jd) for jd in jds]
        assert len(vacancies) == 100
        assert all(v.scope_type for v in vacancies)

        # 3. Company context
        companies = [infer_company_context(jd) for jd in jds]
        assert len(companies) == 100
        assert all(c.completeness_score > 0.6 for c in companies)

        # 4. Mapping computation (샘플링, 전수는 1B이라 불가)
        sample_pairs = select_top_pairs(candidates, vacancies, 10000)
        mappings = [compute_mapping(c, v) for c, v in sample_pairs]

        assert len(mappings) == 10000
        assert all(0 <= m.overall_match_score <= 1.0 for m in mappings)

        # 5. Validate distribution
        scores = [m.overall_match_score for m in mappings]
        assert np.mean(scores) > 0.3  # 평균 점수 > 0.3
        assert np.std(scores) > 0.1   # 분산 > 0.1 (다양성)
```

### 3-5 산출물
```
□ pytest 구성 (conftest.py, fixtures)
□ Golden 50건 regression test (test_phase3_golden_set.py)
□ 단위 테스트 (test_*.py 10개)
□ 통합 테스트 (test_*_e2e.py)
□ Test coverage > 80%
□ CI/CD 파이프라인 (GitHub Actions)
```

---

## Phase 3 에이전트 서빙 확장

Phase 1에서 구축한 Cypher 쿼리 5종을 확장, Phase 3용 5종 추가.
총 10종 쿼리로 Neo4j 그래프 활용도 극대화.

```cypher
-- Q6: JD 기반 후보자 매칭 (Top N)
MATCH (v:Vacancy {vacancy_id: $vid})-[m:MAPPED_TO]->(p:Person)
RETURN
  p.candidate_id as candidate_id,
  p.name as name,
  p.seniority_estimate as seniority,
  m.overall_match_score as match_score,
  m.skill_overlap_score as skill_score,
  m.scope_type_score as scope_score
ORDER BY m.overall_match_score DESC
LIMIT $limit;

-- Q7: 후보자 기반 적합 포지션 (역방향)
MATCH (p:Person {candidate_id: $cid})<-[m:MAPPED_TO]-(v:Vacancy)
WITH v, m, p
MATCH (v)-[:BELONGS_TO]->(o:Organization)
RETURN
  v.vacancy_id as vacancy_id,
  v.title as title,
  v.scope_type as scope_type,
  o.company_name as company_name,
  m.overall_match_score as match_score
ORDER BY m.overall_match_score DESC;

-- Q8: 기업 조건 필터 매칭
MATCH (o:Organization {nice_industry_code: $industry_code})<-[:BELONGS_TO]-(v:Vacancy)
WITH v
MATCH (v)-[m:MAPPED_TO]->(p:Person)
WHERE m.overall_match_score > $threshold
RETURN
  v.title as vacancy_title,
  p.candidate_id as candidate_id,
  p.name as name,
  m.overall_match_score as match_score,
  COUNT(DISTINCT p) as candidate_count
ORDER BY m.overall_match_score DESC;

-- Q9: 업종별 매칭 통계
MATCH (o:Organization)-[:IN_INDUSTRY]->(i:Industry)
WITH o, i
MATCH (o)<-[:BELONGS_TO]-(v:Vacancy)
WITH o, i, v
MATCH (v)-[m:MAPPED_TO]->(p:Person)
WHERE m.overall_match_score >= 0.5
RETURN
  i.code as industry_code,
  i.name as industry_name,
  COUNT(DISTINCT v) as vacancy_count,
  COUNT(DISTINCT p) as candidate_count,
  AVG(m.overall_match_score) as avg_score,
  PERCENTILE_CONT(m.overall_match_score, 0.5) as median_score
GROUP BY i.code, i.name
ORDER BY vacancy_count DESC;

-- Q10: 스킬 갭 분석
MATCH (p:Person {candidate_id: $cid})-[has:HAS_SKILL]->(ps:Skill)
WITH p, COLLECT(ps.name) as person_skills
MATCH (p)<-[m:MAPPED_TO]-(v:Vacancy)
UNWIND v.required_skills as req_skill
WITH person_skills, req_skill, v, m
WHERE NOT req_skill IN person_skills
RETURN
  v.vacancy_id as vacancy_id,
  v.title as title,
  COLLECT(DISTINCT req_skill) as missing_skills,
  COUNT(DISTINCT req_skill) as gap_size,
  m.overall_match_score as match_score
ORDER BY gap_size ASC, m.overall_match_score DESC;
```

---

## Phase 3 완료 산출물

```
□ JD 파서 + Vacancy 노드 (10K JD)
  ├─ BigQuery: graphrag_kg.staging_vacancy (10K rows)
  ├─ Neo4j: :Vacancy 노드 (10K개)
  └─ 수동 검증: 100건 (정확도 > 70%)

□ CompanyContext 파이프라인 (NICE + Rule + LLM)
  ├─ NICE Lookup 모듈 + Redis 캐싱
  ├─ Rule 엔진 (employee_scale, growth_stage 추정)
  ├─ LLM 프롬프트 (extract_company_context.txt)
  ├─ BigQuery: graphrag_kg.company_context (10K rows)
  └─ 수동 검증: 100건 (completeness > 75%)

□ Organization Entity Resolution (한국어 특화)
  ├─ CompanyNameNormalizer 모듈
  ├─ CompanyEntityResolver (3단계 ER)
  ├─ company_alias.json 데이터베이스
  ├─ Neo4j: :Organization 노드 (500개)
  └─ 전수 검수: 완료 (Precision ≥ 95%, Recall ≥ 80%)

□ MappingFeatures + MAPPED_TO 관계
  ├─ 5가지 피처 계산 (scope_type, skill, seniority, industry, embedding)
  ├─ Overall match score (가중합)
  ├─ BigQuery: graphrag_kg.mapping_features (서빙 테이블)
  ├─ Neo4j: MAPPED_TO 관계 (수십억 규모)
  ├─ SQL 예시 5종 (에이전트 서빙)
  └─ 수동 검증: 100건

□ 테스트 인프라
  ├─ Golden 50건 regression test
  ├─ 단위 테스트 (10개)
  ├─ 통합 테스트 (E2E)
  ├─ Test coverage > 80%
  └─ CI/CD 파이프라인 (GitHub Actions)

□ 에이전트 서빙
  ├─ Cypher 쿼리 10종 (Phase 1 5종 + Phase 3 5종)
  ├─ 에이전트 API 문서화
  └─ 매칭 기반 답변 예시 3종

□ Phase 3 → Phase 4 Go/No-Go 판정
  ├─ 품질 지표 확인
  ├─ 성능 지표 확인
  └─ 비용 수립
```

---

## 예상 인프라 비용 (Phase 3 6주)

| 항목 | 단가 | 수량 | 소계 |
|---|---|---|---|
| **BigQuery** |  |  |  |
| Storage (staging_vacancy, company_context, mapping_features) | $6.25/TB/월 | 50GB | $0.31 |
| Queries (JD extraction, company context, mapping compute) | $6.25/TB | 100TB | $625 |
| **Batch API** | $0.0004/건 | 20K 건 (JD + Context) | $8 |
| **Neo4j** |  |  |  |
| Cloud Run (Enterprise) | $0.096/시간 | 168시간 | $16 |
| **Embeddings** | $0.02/1M tokens | 500M tokens | $10 |
| **GCS** | $0.020/GB | 100GB | $2 |
| **합계** |  |  | **$661** |

---

## 타임라인

```
Week 14: 3-1 JD 파서 + Vacancy (DE 3일, MLE 4일)
Week 15-16: 3-2 CompanyContext 파이프라인 (DE 6일, MLE 4일)
Week 17: 3-3 Organization ER (DE 4일, MLE 3일)
Week 18-19: 3-4 MappingFeatures + MAPPED_TO (DE 4일, MLE 6일)
Week 19: 3-5 테스트 인프라 (DE/MLE 병행)

병렬 작업:
- Week 15: 3-2 CompanyContext 파이프라인 진행 중 → LLM 프롬프트 개선 (MLE 병행)
- Week 17: 3-3 ER 진행 중 → 3-4 MAPPED_TO 준비 (MLE 시작)
- Week 19: 3-5 테스트 작성 동시 진행
```
