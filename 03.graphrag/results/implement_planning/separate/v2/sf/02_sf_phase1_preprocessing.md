# S&F Phase 1: 전처리 + LLM 추출 1,000건 (Week 2~5)

> **v5 원본**: `02_phase1_core_candidate_mvp.md` §1-A, §1-B, §1-C
> **산출물 ②**: CandidateContext 1,000건 JSONL → GCS → PubSub 자동 트리거

---

## 1-A. 크롤링 파이프라인 (Week 2~3, 선택적)

> 법무 허용 시에만. Playwright 기반 크롤링.
> 법무 미허용 시 DB 데이터만으로 진행 (DB-only MVP).

---

## 1-B. 전처리 모듈 (Week 2~3)

### CMEK 버킷 생성 (v4 R3: Phase 0 → Phase 1-B로 이동)

```bash
# Go/No-Go 판정 후 (Week 2 시작 시) 생성
gcloud storage buckets create gs://kg-pii-mapping --location=asia-northeast3 --uniform-bucket-level-access
gcloud kms keyrings create kg-pii-keyring --location=asia-northeast3
gcloud kms keys create kg-pii-key --location=asia-northeast3 --keyring=kg-pii-keyring --purpose=encryption
gcloud storage buckets update gs://kg-pii-mapping \
  --default-encryption-key=projects/graphrag-kg/locations/asia-northeast3/keyRings/kg-pii-keyring/cryptoKeys/kg-pii-key
gcloud iam service-accounts create kg-pii-reader --display-name="KG PII Reader (Read-Only)"
gcloud storage buckets add-iam-policy-binding gs://kg-pii-mapping \
  --member="serviceAccount:kg-pii-reader@graphrag-kg.iam.gserviceaccount.com" --role="roles/storage.objectViewer"
```

### PII 마스킹 (v4 R1: re.sub 콜백)

```python
# src/pii/masker.py — v4 R1 + v12 S2/S4
import re
from google.cloud import storage

PHONE_PATTERNS = [
    r'(?:\+82[-\s]?)?0?1[016789][-.\\s)]*\d{3,4}[-.\\s]?\d{4}',
    r'0[2-6][0-9]?[-.\\s]?\d{3,4}[-.\\s]?\d{4}',
]
SSN_PATTERN = r'\d{6}-\d{7}'
EMAIL_PATTERN = r'[\w.-]+@[\w.-]+\.\w+'

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
    # v5 U2: 토큰 형식 [PHONE_xxx]이 후속 패턴에 매칭되지 않아야 함
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

```
resume-hub DB → DB 커넥터
  → CP1: 입력 검증 (v12 §2.2)
  → PII 마스킹 (v12 S4 전화번호 8종, R1: re.sub 콜백)
  → PII 매핑 → GCS CMEK (v12 S2, R3: Phase 1-B에서 생성)
  → CP2: 마스킹 검증 (v12 §2.3)
  → Career 블록 분리
  → GCS jsonl (마스킹됨)
```

---

## 1-C. CandidateContext LLM 추출 (Week 4~5)

### 적응형 LLM 호출 (v12 M1)

```python
# src/extractors/candidate_extractor.py — v12 M1
async def extract_candidate_context(person: dict, provider: 'LLMProvider') -> dict:
    careers = person.get('careers', [])
    if len(careers) <= 3:
        return await extract_1pass(person, provider)    # 1-pass
    else:
        return await extract_n_plus_1(person, provider)  # N+1 pass
```

### LLM 파라미터

| 파라미터 | 1-pass | N+1: Career별 | N+1: 요약 |
|---------|--------|--------------|----------|
| model | claude-haiku-4-5 | claude-haiku-4-5 | claude-haiku-4-5 |
| temperature | 0.3 | 0.3 | 0.3 |
| max_tokens | 2,048 | 1,024 | 512 |
| batch_mode | true | true | true |

---

## 산출물 ② 전달

```
Week 5 완료 시:
  □ CandidateContext 1,000건 JSONL → GCS gs://kg-artifacts/candidate/batch_{id}.jsonl
  □ GCS Object Finalize → PubSub kg-artifact-ready 자동 발행
  □ GraphRAG 팀 Cloud Run Job이 자동 수신하여 Neo4j 적재 시작
```
