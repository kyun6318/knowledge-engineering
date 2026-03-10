# Day 1 필요 데이터셋 및 GCP 서비스 정리

> 출처: `api-test-3day-v3.md` Day 1 (Gemini API 기본 추론 + Embeddings API)

---

## 필요 데이터셋

| 데이터셋 ID | 용도 | 형태 | 크기 | 언어 | 사용 테스트 |
|---|---|---|---|---|---|
| `DS-LLM-EVAL` | LLM 평가셋 (프롬프트 + 기대 응답) | JSONL | 50~100 examples | KO/EN 7:3 | TEST-C1 |
| `DS-EMBED-SAMPLE` | 임베딩 품질 평가 | JSONL | 1K~5K docs | KO/EN 7:3 | TEST-C2 |
| `prompts/medium_1k_ko.txt` | C1 medium 한국어 프롬프트 | TXT | ~1K 토큰 | KO | TEST-C1 |
| `prompts/medium_1k_en.txt` | C1 medium 영어 프롬프트 | TXT | ~1K 토큰 | EN | TEST-C1 |

### 참고: Day 1에 확인만 필요한 데이터 (Day 2~3 사용)

- `DS-NER-EVAL` gold 데이터 -- 사전 라벨링 완료 여부 확인
- `DS-RAG-GOLD` -- 쿼리별 기대 문서 준비 여부 확인
- `DS-PDF-SAMPLE` -- GCS 업로드 여부 확인

---

## 데이터셋 생성 방법

### 1. `DS-LLM-EVAL` (JSONL, 50~100건)

**목적**: Gemini 모델의 한국어/영어 응답 품질을 평가하기 위한 프롬프트 + 기대 응답 쌍

**생성 방법**:
1. 채용/이력서/기업 도메인 중심으로 질문 설계 (KO 35~70건, EN 15~30건)
2. 카테고리별 균등 분배:
   - 요약 (summarization): "다음 이력서의 핵심 역량을 요약해줘"
   - 추출 (extraction): "이 공고에서 필수 자격요건을 추출해줘"
   - 분류 (classification): "이 직무는 어떤 산업 분류에 해당하나?"
   - 생성 (generation): "이 경력에 맞는 자기소개서 초안을 작성해줘"
3. 각 항목에 reference 응답(gold answer)을 수동 작성

**JSONL 스키마 예시**:
```jsonl
{"id": "llm-eval-001", "lang": "ko", "category": "extraction", "prompt": "다음 이력서에서 기술 스택을 추출해줘: [이력서 텍스트]", "reference": "Python, TensorFlow, Kubernetes, ...", "eval_axes": ["정확성", "완전성", "도메인적합성"]}
```

**업로드**: `gs://ml-api-test-vertex/datasets/DS-LLM-EVAL/llm_eval.jsonl`

---

### 2. `DS-EMBED-SAMPLE` (JSONL, 1K~5K건)

**목적**: 임베딩 모델의 한국어 벡터 품질(코사인 유사도) 및 배치 처리 검증

**생성 방법**:
1. 소스 수집 (KO 70%, EN 30%):
   - 한국어 뉴스 기사 본문 (크롤링 또는 공개 데이터셋)
   - 한국어 이력서/채용공고 텍스트
   - 영어 기술 문서/뉴스 기사
2. 텍스트 전처리:
   - 문서당 200~500자로 청킹 (임베딩 입력 적정 길이)
   - HTML 태그, 특수문자 제거
3. 유사도 평가용 양성/음성 쌍 포함:
   - 양성 쌍 (동일 주제 문서 2개): 기대 유사도 > 0.7
   - 음성 쌍 (다른 주제 문서 2개): 기대 유사도 < 0.4

**JSONL 스키마 예시**:
```jsonl
{"id": "embed-001", "lang": "ko", "text": "Python 백엔드 개발자 3년차, Django REST framework 경험...", "category": "resume", "pair_id": "embed-002", "pair_type": "positive"}
```

**업로드**: `gs://ml-api-test-vertex/datasets/DS-EMBED-SAMPLE/embed_sample.jsonl`

---

### 3. `prompts/medium_1k_ko.txt`

**목적**: C1 비스트리밍/스트리밍 테스트용 한국어 medium 프롬프트 (~1K 토큰)

**생성 방법**:
1. 채용 도메인 맥락의 복합 질문 작성 (약 800~1200자, 한국어)
2. 예시 내용:
   - 이력서 텍스트를 포함하고, 해당 이력서를 분석하여 강점/약점/추천 직무를 도출하라는 지시
   - 또는 기업 채용공고 3~4개를 나열하고 비교 분석 요청
3. 토큰 수 검증: CountTokens API 또는 `len(text) * 0.6` 추정으로 ~1K 토큰 확인

**업로드**: `gs://ml-api-test-vertex/prompts/medium_1k_ko.txt`

---

### 4. `prompts/medium_1k_en.txt`

**목적**: C1 비스트리밍 테스트용 영어 medium 프롬프트 (~1K 토큰)

**생성 방법**:
1. `medium_1k_ko.txt`와 동일한 구조의 영어 버전 작성 (약 600~800 단어)
2. 예시: 영문 이력서를 포함하여 skills gap analysis 또는 job matching 요청
3. 토큰 수 검증: 영어는 `len(text.split()) * 1.3` 추정으로 ~1K 토큰 확인

**업로드**: `gs://ml-api-test-vertex/prompts/medium_1k_en.txt`

---

### 데이터셋 GCS 업로드 절차

```bash
# 1. 로컬에서 데이터셋 준비 후 GCS 업로드
gsutil -m cp datasets/DS-LLM-EVAL/*.jsonl gs://ml-api-test-vertex/datasets/DS-LLM-EVAL/
gsutil -m cp datasets/DS-EMBED-SAMPLE/*.jsonl gs://ml-api-test-vertex/datasets/DS-EMBED-SAMPLE/
gsutil cp prompts/medium_1k_ko.txt gs://ml-api-test-vertex/prompts/
gsutil cp prompts/medium_1k_en.txt gs://ml-api-test-vertex/prompts/

# 2. 업로드 확인
gsutil ls gs://ml-api-test-vertex/datasets/
gsutil ls gs://ml-api-test-vertex/prompts/
```

---

## 필요 GCP 서비스

### 핵심 서비스 (API 호출 발생)

| 서비스 | 용도 | 리전 | 사용 테스트 |
|---|---|---|---|
| **Vertex AI API (Gemini)** | Gemini 2.5 Flash / 2.5 Pro 모델 추론 (비스트리밍, 스트리밍, 구조화 출력) | `asia-northeast3` | TEST-C1 |
| **Vertex AI API (Embeddings)** | gemini-embedding-001 / text-embedding-005 임베딩 생성 | `asia-northeast3` | TEST-C2 |
| **Cloud Storage API** | 데이터셋/프롬프트 파일 저장 및 읽기 | - | C1, C2 공통 |

### 사전 설정 필요 (Day 1 시작 전 완료)

| 항목 | 세부 |
|---|---|
| GCP 프로젝트 | `ml-api-test-vertex` |
| API 활성화 | Vertex AI API, Cloud Storage API |
| 인증 | 서비스 계정 + ADC 설정 |
| SDK 설치 | `google-genai >= 1.5.0` |
| GCS 버킷 | `gs://ml-api-test-vertex/datasets/`, `gs://ml-api-test-vertex/prompts/` |
| Document AI 프로세서 | Console에서 사전 생성 완료 확인 (OCR, Layout Parser) -- Day 2 사용이지만 Day 1 환경 구성에서 확인 |

### Day 1에서 활성화하지만 사용하지 않는 API (Day 2~3용 사전 활성화)

- Document AI API (리전: `asia`)
- Discovery Engine API (Vertex AI Search)

---

## Day 1 테스트 요약

### TEST-C1: Gemini API 기본 추론

- **모델**: `gemini-2.5-flash` (KO+EN), `gemini-2.5-pro` (KO만)
- **테스트**: 비스트리밍 호출, 스트리밍 호출(ttft 측정), 시스템 프롬프트 + JSON 구조화 출력
- **검증**: 호출 성공, ttft < 2s, 한국어 품질 >= 6점(8점 만점), JSON 유효성

### TEST-C2: Embeddings API

- **모델**: `gemini-embedding-001`, `text-embedding-005`
- **테스트**: 단건 임베딩, tokens_per_char 캘리브레이션, 동적 배치(250건), split-retry, task_type 2종(RETRIEVAL_DOCUMENT/RETRIEVAL_QUERY)
- **검증**: 벡터 반환, 차원 확인, 배치 성공, 한국어 코사인 유사도 > 0.7
