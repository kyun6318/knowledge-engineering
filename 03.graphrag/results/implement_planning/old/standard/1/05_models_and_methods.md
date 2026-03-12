# GraphRAG standard.1 — 모델 및 방법론 정리

> standard.1 계획 전체에서 사용하는 LLM, ML 모델, Embedding, 청킹/파싱 방법론을 한 곳에 정리.
> 출처: `00_overview.md` ~ `04_cost_monitoring_ops.md`

---

## 1. Phase 0 — PoC · 검증 · 의사결정

> 목표: 모델/방법론 비교 후 Phase 1 파이프라인에 사용할 기술 스택 확정

### 1.1 LLM 모델

#### Claude Sonnet 4.6 (PoC · Silver Label)

| 항목 | 값 |
|------|-----|
| **제공사** | Anthropic |
| **호출 방식** | 일반 API (실시간) |
| **용도** | PoC 모델 비교, Silver Label 생성 (2,000건), 프롬프트 최적화 |
| **건당 비용** | ~$0.01 (일반 API) |

#### Gemini (API 검증 · 텍스트 추출)

| 모델 | 용도 | 세부 Phase |
|------|------|-----------|
| Gemini 2.5 Flash | 기본 추론 + 한국어 품질 평가 + NER | Phase 0-2 |
| Gemini 2.5 Pro | 기본 추론 품질 비교 | Phase 0-2 |
| Gemini 멀티모달 | PDF 직접 텍스트 추출 (TEST-MMD), HWP 파싱 방법 C | Phase 0-2, 0-4-7 |

#### LLM 모델 선택 비교 (Phase 0-4-2 → 0-6 확정)

```
Phase 0-4-2에서 50건 PoC 비교:
  - Claude Haiku 4.5 vs Claude Sonnet 4.6 vs Gemini Flash
  - 평가 축: 품질 (scope_type 정확도, outcome F1) × 비용 × 속도
  - → Phase 0-6 의사결정에서 최종 확정
```

### 1.2 Embedding 모델 비교 (Phase 0-4-5)

#### 후보 모델

| 모델 | 제공사 | 차원 | 리전 | SDK |
|------|--------|------|------|-----|
| **text-embedding-005** | Google (Vertex AI 네이티브) | 768d | us-central1 | `vertexai.language_models.TextEmbeddingModel` |
| **gemini-embedding-001** | Google (Gemini) | 768d | us-central1 | `google.genai` |

#### 비교 방법

```
비교 설계:
  - 20쌍: 같은 도메인 10쌍 + 다른 도메인 10쌍
  - 한국어 코사인 유사도 분별력 비교
  - Mann-Whitney U test로 통계적 유의성 검증
  - task_type 4종 테스트: RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY,
    SEMANTIC_SIMILARITY, CLASSIFICATION

의사결정:
  - Phase 0-6에서 최종 확정
  - 기본 후보: text-embedding-005 (전 문서 통일) [standard.22]
```

### 1.3 텍스트 추출 / 파싱 방법론 비교

#### PDF 텍스트 추출 (Phase 0-2 TEST-E2E에서 비교 후 확정)

| 방법 | 도구 | 장점 | 단점 | 평가 기준 |
|------|------|------|------|-----------|
| **A: Document AI → Gemini NER** (2단계) | Google Document AI OCR + Layout Parser | OCR 정확도 높음 | 2단계 호출, 비용 높음 | CER ≤ 0.10 = GOOD |
| **B: Gemini 멀티모달** (1단계) | Gemini + PDF 직접 입력 | 단일 호출, 구조 인식 | 크기 제한 (10MB, 5p), 비용 | CER/WER 비교 |

```
의사결정 (Phase 0-2 TEST-E2E):
  품질 · 비용 · 속도 매트릭스 비교 → Phase 1 파이프라인 방법 확정
```

#### HWP 파싱 (Phase 0-4-7에서 비교 후 확정) [standard.1-2]

| 방법 | 도구 | 장점 | 단점 |
|------|------|------|------|
| **A: LibreOffice CLI** | HWP → PDF → PyMuPDF | 표 구조 보존 우수, 안정적 | Docker 이미지 ~1.5GB, 처리 느림 |
| **B: pyhwp** | HWP → 텍스트 직접 추출 | 경량, 빠름 | 0.1 베타, HWPX 미지원 [R-5], 표 구조 손실 |
| **C: Gemini 멀티모달** | HWP → PDF → 이미지 → Gemini | 높은 인식률 | 비용 높음, 추가 API 호출 |

```
평가 기준:
  1. CER ≤ 0.15 (gold 수동 입력 대비)
  2. 표 구조 보존 ≥ 60%
  3. 한글 폰트 렌더링 정확도
  4. 처리 시간 + 비용
  5. Docker 이미지 크기 영향

[R-5] pyhwp 리스크 확인:
  - HWPX(한글 2014 이후) 파일 처리 가능 여부
  - 10건 샘플에서 HWP5 vs HWPX 비율 확인
  - HWPX 비율 높으면 → pyhwp 제외, LibreOffice 또는 Gemini 선택
```

### 1.4 알고리즘 / 통계 검정

| 알고리즘 | 용도 | 세부 Phase |
|----------|------|-----------|
| Mann-Whitney U test | Embedding 모델 분별력 비교 | Phase 0-4-5 |

### 1.5 Phase 0 의사결정 타임라인

| 시점 | 의사결정 | 후보 | 판단 기준 |
|------|---------|------|-----------|
| Phase 0-2 | **Embedding 모델 확정** | text-embedding-005 vs gemini-embedding-001 | Mann-Whitney U 한국어 분별력 |
| Phase 0-2 | **텍스트 추출 방법 확정** | Document AI vs Gemini 멀티모달 | CER/WER + 비용/속도 |
| Phase 0-4-2 | **LLM 모델 선택** | Haiku vs Sonnet vs Gemini Flash | 품질 × 비용 매트릭스 (50건) |
| Phase 0-4-6 | **LLM 호출 전략** | 단건 호출 vs 묶음 호출 | 품질/비용 비교 (10건) |
| Phase 0-4-7 | **HWP 파싱 방법 확정** | LibreOffice vs pyhwp vs Gemini | CER + 표 보존 + Docker 영향 |

### 1.6 Phase 0 비용

| 모델/서비스 | 비용 |
|---|---|
| Anthropic 일반 (Sonnet) | $20 |
| Gemini API (검증) | $55 |
| Vertex AI Embedding | $10 |
| **Phase 0 합계** | **$85** |

---

## 2. Phase 1 — MVP 파이프라인 (1,000건)

> 목표: Phase 0에서 확정된 모델/방법론으로 MVP 파이프라인 구축 및 검증

### 2.1 LLM 모델

#### Claude Haiku 4.5 (KG 추출 — Primary)

| 항목 | 값 |
|------|-----|
| **제공사** | Anthropic |
| **호출 방식** | Batch API (50% 할인) |
| **용도** | CandidateContext 추출, CompanyContext 추출 |
| **규모** | MVP 1,000건 |
| **한국어 토큰 보정** | 한글 1자 ≈ 2~3 tokens (영어 대비 ×2.3배) |
| **건당 비용** | $0.00300 (Batch, 한국어 보정 후) |
| **입출력 토큰** | input 평균 3,500 / output 평균 800 |
| **Batch 단가** | input $0.40/1M, output $2.00/1M (50% 할인 적용) |

#### 프롬프트 목록 (GCS `prompts/`)

| 프롬프트 파일 | 용도 | 대상 |
|---|---|---|
| `experience_extract_v1.txt` | Experience별 LLM 추출 | CandidateContext |
| `career_level_v1.txt` | 전체 커리어 레벨 추출 | CandidateContext |
| `vacancy_role_v1.txt` | Vacancy + Role 통합 추출 | CompanyContext |

### 2.2 텍스트 추출 / 파싱

> Phase 0에서 확정된 방법 적용

| 파일 형식 | 도구 | 비고 |
|-----------|------|------|
| PDF | Phase 0 확정 방법 (Document AI 또는 Gemini 멀티모달) | CER ≤ 0.10 |
| DOCX | `python-docx >= 1.1.0` | 텍스트 추출 |
| HWP | Phase 0 확정 방법 (LibreOffice / pyhwp / Gemini) | CER ≤ 0.15 |

#### 이력서 전처리 파이프라인 (Phase 1-1)

```
이력서 원본 (PDF/DOCX/HWP)
    │
    ├─ 1) 파일 형식별 파서 (PyMuPDF / python-docx / HWP 방법 확정)
    │
    ├─ 2) 섹션 분할 (Rule-based)
    │     └─ 섹션 경계 패턴 매칭
    │
    ├─ 3) 경력 블록 분리
    │     └─ 개별 경력 항목 단위로 분리
    │
    ├─ 4) PII 마스킹 (offset mapping 보존)
    │     ├─ 이름 → [NAME]
    │     ├─ 연락처 → [PHONE]
    │     └─ 주소 → [ADDR]
    │
    └─ 5) 결과 → parsed/resumes/{candidate_id}.json
         ├─ text, masked_text, offset_map
         ├─ sections, career_blocks
         └─ metadata
```

### 2.3 Embedding 모델

> Phase 0에서 확정된 모델 적용 (기본 후보: text-embedding-005)

| 대상 | Vector Index 이름 | 저장 위치 | 규모 |
|------|-------------------|-----------|------|
| Chapter evidence_chunk | `chapter_embedding` | Neo4j `c.evidence_chunk_embedding` | 1K × 5.2 ≈ 5.2K 벡터 |
| Vacancy description | `vacancy_embedding` | Neo4j `v.embedding` | 소규모 |

### 2.4 알고리즘

| 알고리즘 | 용도 | 세부 Phase |
|----------|------|-----------|
| SimHash | 이력서 중복 제거 | Phase 1-1-6 |
| Rule 추출 (정규식/패턴) | 날짜/회사/기술 추출, 섹션 분할, stage_estimate | Phase 1-1, 1-2, 1-3 |
| Jaro-Winkler 유사도 | Organization Entity Resolution (threshold ≥ 0.85) [R-4] | Phase 1-4-4 |
| Cosine Similarity | MappingFeatures 계산 (Embedding 기반 후보 shortlisting) | Phase 1-5 |

### 2.5 청킹 방법론

#### Batch API 청킹

| 항목 | 값 |
|------|-----|
| **chunk 크기** | 1,000건/chunk |
| **포맷** | JSONL (batch_{chunk_id}.jsonl) |
| **저장** | GCS `batch-api/requests/`, `batch-api/responses/` |

#### 이력서 청킹 (Context 생성 단위)

```
이력서 1건 내부 구조:
  이력서 원본
    ├─ 섹션 분할 (학력, 경력, 기술, 자격증, ...)
    │     └─ Rule-based 섹션 경계 인식
    │
    ├─ 경력 블록 분리 (Experience 단위)
    │     └─ 각 경력 항목 = 1 Chapter 노드 후보
    │
    └─ LLM 추출 단위:
          ├─ Experience별 추출 (experience_extract_v1.txt) — 경력 블록 단위
          └─ 전체 커리어 추출 (career_level_v1.txt) — 이력서 전체 단위

→ LLM에는 마스킹된 텍스트 전체 or 경력 블록 단위로 전송
→ Batch API 1건 = 이력서 1건 (내부에서 여러 프롬프트 호출 가능)
```

#### Graph 적재 배치

| 항목 | 값 |
|------|-----|
| **배치 크기** | 100건/트랜잭션 (기본, 벤치마크 후 최대 1,000건으로 조정 가능 [R-9]) |
| **적재 방식** | Neo4j MERGE (idempotent) |
| **UNWIND** | 단일 트랜잭션 내 다수 건 처리로 RTT 절감 |

#### Embedding 대상 청킹

| 대상 | 텍스트 소스 | 평균 크기 |
|------|-------------|-----------|
| Chapter evidence_chunk | 경력 블록의 evidence 텍스트 | ~200자/chunk |
| Vacancy embedding | JD description 전체 | ~500자 |

### 2.6 Phase 1 비용

| 모델/서비스 | 비용 |
|---|---|
| Anthropic Batch (Haiku) | ~$50 |
| Vertex AI Embedding | $1 |
| **Phase 1 합계** | **$51** |

---

## 3. Phase 2 — 전체 확장 (450K건)

> 목표: Phase 1 파이프라인을 전체 데이터에 적용 + 크롤링 파이프라인 추가

### 3.1 LLM 모델

#### Claude Haiku 4.5 (KG 추출 — 전체 확장)

| 항목 | 값 |
|------|-----|
| **호출 방식** | Batch API (50% 할인) |
| **규모** | 450K 전체 |
| **총 chunk 수** | ~450 chunks |
| **동시 처리** | 5~10 chunks (Anthropic quota에 따라) |

#### Claude Sonnet 4.6 (Silver Label)

| 항목 | 값 |
|------|-----|
| **용도** | Silver Label 생성 (2,000건) — 품질 평가용 |
| **건당 비용** | ~$0.01 |

#### Gemini Flash (크롤링 LLM 추출)

| 항목 | 값 |
|------|-----|
| **모델** | Gemini Flash (Phase 0 확정 버전 snapshot 고정, 예: `gemini-2.5-flash-001`) [R-11] |
| **제공사** | Google (Vertex AI) |
| **호출 방식** | Vertex AI Gemini API (실시간) |
| **용도** | 크롤링 데이터에서 구조화 정보 추출 (홈페이지/뉴스) |
| **Rate limit 대응** | QPM throttle 5초 간격, 429 → 30초 대기 재시도 |
| **비용** | 1,000기업 × ~15건 ≈ $5 |

#### 크롤링 프롬프트 (4종)

| 프롬프트 | 입력 소스 | 추출 필드 |
|---|---|---|
| `homepage_extract_v1.txt` | 기업 홈페이지 | product_description, market_segment, scale/culture_signals |
| `news_funding_extract_v1.txt` | 펀딩 뉴스 | funding_round, amount, investors, growth_narrative |
| `news_org_extract_v1.txt` | 조직변동 뉴스 | change_type, tension_type, tension_description |
| `news_product_extract_v1.txt` | 제품 뉴스 | product_name, traction_data, growth_narrative |

#### 추가 프롬프트

| 프롬프트 파일 | 용도 | 대상 |
|---|---|---|
| `structural_tension_v1.txt` | 구조적 긴장 추출 | CompanyContext (크롤링 보강) |

### 3.2 Embedding 모델

| 대상 | Vector Index 이름 | 저장 위치 | 규모 (Phase 2) |
|------|-------------------|-----------|----------------|
| Chapter evidence_chunk | `chapter_embedding` | Neo4j `c.evidence_chunk_embedding` | 450K × 5.2 ≈ 2.34M 벡터 |
| Vacancy description | `vacancy_embedding` | Neo4j `v.embedding` | 10K 벡터 |

#### Vector Index 설정

```cypher
CREATE VECTOR INDEX chapter_embedding IF NOT EXISTS
FOR (c:Chapter) ON (c.evidence_chunk_embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX vacancy_embedding IF NOT EXISTS
FOR (v:Vacancy) ON (v.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};
```

#### Embedding 비용

| 항목 | 값 |
|------|-----|
| Phase 2 총 토큰 | ~302M 토큰 |
| 단가 | $0.0001/1K 토큰 |
| Embedding 비용 | $30 |
| Egress 비용 (서울↔US) | $3.6 (보수적 추정) |

### 3.3 알고리즘

| 알고리즘 | 용도 | 세부 Phase |
|----------|------|-----------|
| SimHash | 이력서 중복 제거 (500K → ~450K) | Phase 2-1-1 |
| Cohen's κ | Inter-annotator agreement (품질 평가) | Phase 2-2 |
| Cohen's d | 효과 크기 측정 (Power analysis) | Phase 2-2 |

### 3.4 Phase 2 비용

| 모델/서비스 | 비용 |
|---|---|
| Anthropic Batch (Haiku) | $1,504 |
| Anthropic 일반 (Sonnet) | $620 |
| Gemini API (크롤링) | $5 |
| Vertex AI Embedding | $30 |
| **Phase 2 합계** | **$2,159** |

---

## 4. Phase 3 — 운영 최적화

> 목표: ML Distillation으로 LLM 비용 절감 + 지속 운영

### 4.1 ML 모델: Knowledge Distillation

> Phase 0~2에서는 ML 모델 미사용. Phase 3에서 도입.

| 항목 | 값 |
|------|-----|
| **모델** | KLUE-BERT (한국어 사전학습 BERT) |
| **용도** | LLM 추출 결과를 학습 데이터로 활용, ML 분류기 학습 |
| **진입 조건** | Phase 2 품질 평가 완료 + 운영 데이터 3개월 축적 + 월 LLM 비용 $50 이상 |

| 분류기 | 목표 F1 | 입력 | 출력 |
|--------|---------|------|------|
| scope_type 분류기 | > 75% | 경력 블록 텍스트 | scope_type 라벨 |
| seniority 분류기 | > 80% | 전체 커리어 텍스트 | seniority 라벨 |

### 4.2 Confidence 기반 라우팅

```
추론 시:
  ML 분류기 confidence > 0.85 → ML 결과 사용 (비용 $0)
  ML 분류기 confidence ≤ 0.85 → LLM fallback (건당 $0.003)

목표: LLM 호출량 50~70% 절감
```

### 4.3 운영 단계 LLM/Embedding (월간)

| 모델/서비스 | 월 비용 |
|---|---|
| Anthropic API (증분 1,000건/일) | $90 |
| Gemini API (크롤링 1,000기업/월) | $5 |
| Vertex AI Embedding (증분) | ~$0.01 |
| **운영 LLM/Embedding 월 합계** | **~$95** |

### 4.4 의사결정

| 시점 | 의사결정 | 후보 | 판단 기준 |
|------|---------|------|-----------|
| Phase 3 진입 시 | **ML Distillation 시작** | KLUE-BERT | 운영 데이터 3개월 + ROI 확인 |

---

## 5. 공통 — LLM 응답 파싱 전략

> 모든 Phase에서 공통 적용

### 5.1 3-Tier 파싱 실패 처리

| Tier | 동작 | 허용 |
|------|------|------|
| **Tier 1** | `json-repair` 라이브러리로 JSON 복구 → Pydantic 검증 | 정상 파싱 |
| **Tier 2** | temperature 조정 후 LLM 재호출 (호출측에서 처리) | 재시도 |
| **Tier 3** | 부분 추출 허용 (`model_construct`) 또는 skip + dead-letter | 부분 데이터 / 실패 |

```
목표: tier1 > 85%, tier3_fail < 3%
```

### 5.2 관련 라이브러리

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| `json-repair` | >= 0.28.0 | LLM JSON 출력 복구 |
| `pydantic` | >= 2.5.0 | 스키마 검증 + 부분 추출 (`model_construct`) |

---

## 6. 비용 총괄 요약

### Phase별 비용

| 모델/서비스 | Phase 0 | Phase 1 | Phase 2 | 합계 |
|---|---|---|---|---|
| Anthropic Batch (Haiku) | — | ~$50 | $1,504 | **$1,554** |
| Anthropic 일반 (Sonnet) | $20 | — | $620 | **$640** |
| Gemini API (검증 + 크롤링) | $55 | — | $5 | **$60** |
| Vertex AI Embedding | $10 | $1 | $30 | **$41** |
| **LLM/Embedding 합계** | **$85** | **$51** | **$2,159** | **$2,295** |
