> **산출물 B**: CandidateContext 1,000건 JSONL -> GCS -> PubSub 자동 트리거
> 

---

## 1-A. 크롤링 파이프라인 (Week 2~3, 선택적)

> 법무 허용 시에만. Playwright 기반 크롤링.
법무 미허용 시 DB 데이터만으로 진행 (DB-only MVP).
> 

---

## 1-B. 전처리 모듈 (Week 2~3)

### CMEK 버킷 생성

```bash
# Go/No-Go 판정 후 (Week 2 시작 시) 생성
gcloud storage buckets create gs://kg-pii-mapping --location=asia-northeast3 --uniform-bucket-level-access
gcloud kms keyrings create kg-pii-keyring --location=asia-northeast3
gcloud kms keys create kg-pii-key --location=asia-northeast3 --keyring=kg-pii-keyring --purpose=encryption
gcloud storage buckets update gs://kg-pii-mapping \\
  --default-encryption-key=projects/graphrag-kg/locations/asia-northeast3/keyRings/kg-pii-keyring/cryptoKeys/kg-pii-key
gcloud iam service-accounts create kg-pii-reader --display-name="KG PII Reader (Read-Only)"
gcloud storage buckets add-iam-policy-binding gs://kg-pii-mapping \\
  --member="serviceAccount:kg-pii-reader@graphrag-kg.iam.gserviceaccount.com" --role="roles/storage.objectViewer"
```

### PII 마스킹 (단순 매칭)

```python
import re
from google.cloud import storage

PHONE_PATTERNS = [
    r'(?:\\+82[-\\s]?)?0?1[016789][-.\\\\s)]*\\d{3,4}[-.\\\\s]?\\d{4}',
    r'0[2-6][0-9]?[-.\\\\s]?\\d{3,4}[-.\\\\s]?\\d{4}',
]
SSN_PATTERN = r'\\d{6}-\\d{7}'
EMAIL_PATTERN = r'[\\w.-]+@[\\w.-]+\\.\\w+'

def mask_pii(text: str, person_id: str) -> tuple[str, dict]:
    mapping = {}
    masked = text
    masked, phone_mapping = mask_phones(masked)
    mapping.update(phone_mapping)
    masked = re.sub(SSN_PATTERN, '[SSN_REMOVED]', masked)
    masked, email_mapping = mask_emails(masked)
    mapping.update(email_mapping)
    return masked, mapping

def mask_phones(text: str) -> tuple[str, dict]:
    mapping = {}
    counter = [0]
    def replacer(m):
        token = f"[PHONE_{counter[0]:03d}]"
        mapping[token] = m.group()
        counter[0] += 1
        return token
    for pattern in PHONE_PATTERNS:
        text = re.sub(pattern, replacer, text)
    return text, mapping

def mask_emails(text: str) -> tuple[str, dict]:
    mapping = {}
    counter = [0]
    def replacer(m):
        token = f"[EMAIL_{counter[0]:03d}]"
        mapping[token] = m.group()
        counter[0] += 1
        return token
    text = re.sub(EMAIL_PATTERN, replacer, text)
    return text, mapping

def save_pii_mapping(person_id: str, mapping: dict):
    import json
    client = storage.Client()
    bucket = client.bucket('kg-pii-mapping')
    blob = bucket.blob(f'mappings/{person_id}.json')
    blob.upload_from_string(json.dumps({'person_id': person_id, 'mapping': mapping}),
                           content_type='application/json')
```

### 전처리 흐름

`knowledge_graph/01_extraction_pipeline.md`

```
resume-hub DB -> DB 커넥터
 -> CP1: 입력 검증
 -> PII 마스킹
 -> PII 매핑 -> GCS CMEK
 -> CP2: 마스킹 검증
 -> Career 블록 분리
 -> GCS jsonl (마스킹됨)
```

---

> **[v3 신규] SIE 사전 추출 통합**: Phase 1 전처리에서 GLiNER2 모델을 workDetails/careerDescription 텍스트에 적용하여 경력-프로젝트-성과 구조를 사전 추출한다. 추출 결과는 LLM 프롬프트의 컨텍스트로 제공되어 추출 정확도를 향상시킨다.

## 1-C. CandidateContext LLM 추출 (Week 4~5)

### 적응형 LLM 호출 (`knowledge_graph/01_extraction_pipeline.md`)

```python
# src/extractors/candidate_extractor.py
async def extract_candidate_context(person: dict, provider: 'LLMProvider') -> dict:
    careers = person.get('careers', [])
    if len(careers) <= 3:
        return await extract_1pass(person, provider)    # 1-pass
    else:
        return await extract_n_plus_1(person, provider)  # N+1 pass
```

### LLM 파라미터

| 파라미터 | 1-pass | N+1: Career별 | N+1: 요약 |
| --- | --- | --- | --- |
| model | claude-haiku-4-5 | claude-haiku-4-5 | claude-haiku-4-5 |
| temperature | 0.3 | 0.3 | 0.3 |
| max_tokens | 2,048 | 1,024 | 512 |
| batch_mode | true | true | true |

---

## 산출물 B

Week 5 완료 시:

[] CandidateContext 1,000건 JSONL -> GCS gs://kg-artifacts/candidate/batch_{id}.jsonl

[] GCS Object Finalize -> PubSub kg-artifact-ready 자동 발행

[] GraphRAG - Cloud Run Job이 자동 수신하여 Neo4j 적재 시작