# Day 3 — 검색/생성 + 운영 기능 + 결과 종합 (GCP 환경)

> **실행 환경**: Vertex AI Workbench / Compute Engine VM (asia-northeast3)
> **소요 시간**: 약 5~6시간
> **데이터 소스**: Day 2에서 인덱싱된 C5 Corpus + VAS Data Store
> **핵심 목표**: 검색+생성 품질 검증, 운영 기능 확인, 3일 테스트 결과 종합 및 의사결정

---

## 타임라인

| 시간 | 작업 | 스크립트 | 비고 |
|------|------|----------|------|
| 0:00 | VM 환경 확인 & 백그라운드 작업 완료 확인 | `day3_check_ops.py` | polling 최대 30분 |
| 0:30 | TEST-C5: RAG Engine 검색 + 생성 | `day3_test_c5.py` | gold 자동 hit 판정 |
| 1:30 | TEST-VAS: Vertex AI Search | `day3_test_vas.py` | C5 vs VAS 비교 |
| 2:30 | TEST-C6: Grounding (Google Search) | `day3_test_c6.py` | |
| 3:00 | TEST-C10: Prompt Caching | `day3_test_c10.py` | 비용 절감 검증 |
| 3:30 | TEST-X1: API 에러 핸들링 | `day3_test_x1.py` | |
| 4:00 | 결과 종합 & 비용 집계 | `day3_summary.py` | |
| 4:30 | 리소스 삭제 & GCS 최종 업로드 | 수동 | |

---

## 0. VM 환경 확인 & 백그라운드 작업 완료 확인

```bash
# VM 접속
gcloud compute ssh api-test-vm --zone=asia-northeast3-a

cd ~/plan-graph-rag-main/ml-platform

# 환경변수
export GCP_PROJECT="ml-api-test-vertex"
export GCP_LOCATION="asia-northeast3"
export GCS_BUCKET="gs://ml-api-test-vertex"

# Day 2 결과 동기화 (혹시 다른 세션에서 실행했을 경우)
gsutil -m rsync -r ${GCS_BUCKET}/results/day2/ results/

# pending_ops.json 확인
cat results/pending_ops.json
```

### 백그라운드 작업 완료 확인 (polling)

```bash
python3 scripts/day3_check_ops.py
```

이 스크립트가 확인하는 것:
1. **C5 Import 완료** — `corpora.list_files()` → 파일 수 > 0
2. **VAS Engine 준비** — `get_engine()` 성공
3. **VAS Import 완료** — `list_documents()` → 문서 존재

```
□ C5 Import: 완료 (___건 파일)
□ VAS Engine: 준비 완료
□ VAS Import: 완료 (문서 존재 확인)
```

> 30분 내 미완료 시: 해당 테스트를 후반으로 지연하고 다른 테스트부터 진행.

---

## 1. TEST-C5: RAG Engine — 문서 검색 + 생성

### 1.1 실행

```bash
python3 scripts/day3_test_c5.py
```

### 1.2 테스트 항목

| 항목 | 설명 |
|------|------|
| Retrieval 검색 | 한국어 쿼리 5개, top_k=5 |
| Gold hit 자동 판정 | DS-RAG-GOLD 기반 hit@5 |
| RAG 생성 | 검색+생성 결합, 한국어 품질 |

### 1.3 검색 쿼리 (C5 + VAS 공용)

```
1. Python과 머신러닝 경험이 있는 백엔드 개발자를 찾아줘
2. 데이터 엔지니어링과 클라우드 인프라 경험자
3. NLP 및 자연어처리 관련 연구 경험이 있는 후보자
4. 스타트업 경험이 풍부한 프로덕트 매니저
5. 그래프 데이터베이스 및 지식 그래프 전문가
```

### 1.4 검증 기준

| 항목 | 결과 | Pass 기준 |
|------|------|-----------|
| Corpus 생성 | Y/N | 정상 |
| 문서 인제스트 | ___건 | 에러율 < 5% |
| 한국어 hit@5 (gold) | ___/5 | >= 3/5 |
| relevance score 분포 | min=___, median=___, max=___ | 기록 |
| RAG 생성 한국어 품질 | ___/8 | >= 6 |
| grounding_metadata | Y/N | 소스 인용 존재 |

---

## 2. TEST-VAS: Vertex AI Search — GCS 문서 검색

### 2.1 실행

```bash
python3 scripts/day3_test_vas.py
```

### 2.2 테스트 항목

| 항목 | 설명 |
|------|------|
| GCS 문서 검색 | 동일 5개 쿼리 |
| AI 요약 | 한국어 summary 생성 |
| 인용 | citation 포함 여부 |

### 2.3 검증 기준

| 항목 | 결과 | Pass 기준 |
|------|------|-----------|
| 검색 결과 | Y/N | 관련 문서 반환 |
| AI 요약 (KO) | Y/N | 한국어 요약 |
| 인용 | Y/N | citation 포함 |
| latency | ___ms | < 2s |

### 2.4 C5 vs VAS 공정 비교 (Day 3 핵심 산출물)

| 비교 항목 | RAG Engine (C5) | Vertex AI Search (VAS) |
|-----------|-----------------|----------------------|
| 데이터 소스 | GCS 파일 업로드 | GCS + 웹 크롤링(옵션) |
| 임베딩 제어 | 모델 직접 선택 | 내장 (자동) |
| 검색 품질 (3축) | ___/8 | ___/8 |
| AI 생성/요약 품질 | ___/8 | ___/8 |
| chunk 제어 | chunk_size 직접 | 자동 |
| 비용 모델 | Spanner + Embedding | Enterprise 검색 |
| GraphRAG 적합성 | 커스텀 가능 | 매니지드 한정 |
| **결론** | | |

---

## 3. TEST-C6: Grounding with Google Search

### 3.1 실행

```bash
python3 scripts/day3_test_c6.py
```

### 3.2 테스트 항목

| 항목 | 설명 |
|------|------|
| Grounding ON | 최신 정보 질문, 검색 소스 메타데이터 |
| Grounding OFF | 동일 질문, 베이스라인 |
| 한국어 도메인 | "2026년 한국 AI 채용 시장 동향" |

### 3.3 검증 기준

| 항목 | Grounding ON | Grounding OFF | Pass 기준 |
|------|-------------|---------------|-----------|
| 호출 성공 | Y/N | Y/N | 정상 |
| 최신 정보 (2026) | Y/N | Y/N | ON에서 반영 |
| 한국어 품질 | ___/8 | ___/8 | >= 6 |
| 검색 소스 URL | Y/N | N/A | 출처 포함 |

---

## 4. TEST-C10: Prompt Caching

### 4.1 사전 확인

```bash
# 시스템 프롬프트 파일 확인 (~5K tokens)
wc -c prompts/graphrag_system_5k.txt
# 없으면 GCS에서 동기화
gsutil cp ${GCS_BUCKET}/prompts/graphrag_system_5k.txt prompts/
```

### 4.2 실행

```bash
python3 scripts/day3_test_c10.py
```

### 4.3 테스트 항목

| 항목 | 설명 |
|------|------|
| 캐시 생성/삭제 | CachedContent 생성, TTL=3600s |
| 캐시 ON (20회) | cached_content 참조 호출 |
| 캐시 OFF (20회) | 동일 system prompt 인라인 |
| 비용 절감 산출 | cached_content_token_count 기반 |

### 4.4 검증 기준

| 항목 | 캐시 ON | 캐시 OFF | Pass 기준 |
|------|---------|---------|-----------|
| 캐시 생성/삭제 | Y/N | N/A | 정상 |
| 평균 latency (20회) | ___ms | ___ms | 기록 |
| cached_content_token_count | ___ | N/A | 값 반환 |
| 캐시 토큰 비중 | ___% | N/A | 기록 |
| 토큰 감소율 (단가 무관) | ___% | — | >= 25% |
| 비용 절감 (추정) | ___% | — | 참고치 |

---

## 5. TEST-X1: API 에러 핸들링

### 5.1 실행

```bash
python3 scripts/day3_test_x1.py
```

### 5.2 테스트 시나리오

| 시나리오 | 기대 동작 | 결과 |
|----------|----------|------|
| 잘못된 모델 ID | 404 / NotFound | ___ |
| 빈 입력 | 400 / InvalidArgument | ___ |
| 토큰 초과 | 400 / InvalidArgument | ___ |
| 임베딩 배치 초과 | 400 / InvalidArgument | ___ |
| Rate Limit (10회) | 429 or 정상 | ___ |
| Safety filter | 파라미터 수용 + 메타데이터 | ___ |

---

## 6. 결과 종합 & 비용 집계

### 6.1 실행

```bash
python3 scripts/day3_summary.py
```

이 스크립트가 수행하는 것:
1. `cost_log.jsonl` 기반 모델별/테스트별 비용 집계 (`summarize_costs()`)
2. `test_results.json` 전체 결과 출력
3. `save_all_results()` — `test_run_summary.json` 생성

### 6.2 3일 전체 기능 검증 매트릭스

| 테스트 | 핵심 결과 | 한국어 품질 | 비용 | 판단 |
|--------|----------|------------|------|------|
| C1: Gemini API | ttft=___ms | ___/8 | $___ | O/X |
| C1-LLM-EVAL | pass_rate=___% | KO avg=___/8 | $___ | O/X |
| C2: Embeddings | dim=___, 배치 OK | 유사도=___ | $___ | O/X |
| DOC: Document AI | CER=___ | 추출 CER=___ | $___ | O/X |
| MMD: Gemini 멀티모달 | CER=___, 구조화 ___% | ___/8 | $___ | O/X |
| NER: 엔티티/관계 | F1=___, 정합성=___% | ___/8 | $___ | O/X |
| E2E: 파이프라인 비교 | A vs B | N/A | $___ | O/X |
| C5: RAG Engine | hit@5=___/5 | ___/8 | $___ | O/X |
| VAS: Vertex AI Search | 검색+요약 | ___/8 | $___ | O/X |
| C6: Grounding | 최신 정보 반영 | ___/8 | $___ | O/X |
| C10: Caching | 절감=___% | ___/8 | $___ | O/X |
| X1: 에러 핸들링 | ___/6 확인 | N/A | — | O/X |

### 6.3 총 비용

| 모델 | Day 1 | Day 2 | Day 3 | 합계 |
|------|-------|-------|-------|------|
| gemini-2.5-flash | $___ | $___ | $___ | $___ |
| gemini-2.5-pro | $___ | $___ | $___ | $___ |
| gemini-embedding-001 | $___ | — | — | $___ |
| docai-ocr | — | $___ | — | $___ |
| docai-layout | — | $___ | — | $___ |
| discovery-engine | — | — | $___ | $___ |
| **합계** | $___ | $___ | $___ | **$___** |

---

## 7. GraphRAG 구축 의사결정

### 7.1 의사결정 포인트

| 의사결정 | 테스트 근거 | 결론 |
|----------|------------|------|
| 데이터 수집 방식 | VAS 크롤링 vs 자체 크롤러 | |
| PDF 정제 파이프라인 | DOC(방법A) vs MMD(방법B) | |
| NER 모델 (Flash vs Pro) | NER F1 + 비용 비교 | |
| NER 프롬프트 전략 | zero-shot vs few-shot F1 | |
| 관계 추출 → 그래프 | 관계 F1 + 정합성 | |
| 임베딩 모델 선택 | C2 품질 비교 | |
| RAG 서비스 | RAG Engine vs VAS | |
| Grounding 적용 여부 | C6 정확도 향상폭 | |
| Prompt Caching 적용 | C10 비용 절감 >= 25% | |
| 기본 LLM 모델 | Flash vs Pro 품질/비용 | |

### 7.2 최종 파이프라인 후보

```
후보 1: 매니지드 파이프라인
  VAS(크롤링+검색) → Gemini(생성) + Grounding(실시간)
  장점: 운영 부담 최소 / 단점: 커스텀 제한

후보 2: 하이브리드 파이프라인
  자체 크롤링 → Document AI(정제) → Gemini NER(그래프) → RAG Engine(검색)
  장점: 그래프 품질 통제 / 단점: 구현 복잡

후보 3: Gemini 올인원 파이프라인
  자체 크롤링 → Gemini 멀티모달(정제+NER) → RAG Engine(검색)
  장점: 단순 / 단점: Gemini 의존도 높음

→ 테스트 결과 기반 선택: ___
```

---

## 8. 리소스 삭제

```bash
# pending_ops.json에서 리소스 정보 확인
cat results/pending_ops.json

python3 scripts/day3_cleanup.py
```

### 삭제 체크리스트

```
□ RAG Corpus 삭제 (client.corpora.delete)
□ Prompt Cache 삭제 (테스트 코드에서 자동)
□ Document AI 프로세서 삭제 (Console)
□ Vertex AI Search 삭제:
  □ Search Engine 삭제
  □ Data Store 삭제
□ GCS 임시 파일 정리 (docai-output/)
□ Compute Engine VM 삭제 (또는 정지)
  gcloud compute instances delete api-test-vm --zone=asia-northeast3-a
  # 또는 Workbench 삭제
  gcloud workbench instances delete api-test-workbench --location=asia-northeast3-a
□ 48시간 내 Billing 잔여 비용 확인
```

---

## 9. 결과 GCS 최종 업로드

```bash
# Day 3 결과 업로드
gsutil -m cp -r results/ ${GCS_BUCKET}/results/day3/

# 전체 결과 아카이브
gsutil -m cp -r results/ ${GCS_BUCKET}/results/final/

# 결과 확인
gsutil ls ${GCS_BUCKET}/results/
```

---

## 10. Day 3 이슈 & 최종 정리

```
□ 이슈:
  -

□ 최종 결정:
  - 파이프라인 선택: ___
  - 주 LLM 모델: ___
  - 임베딩 모델: ___
  - RAG 서비스: ___

□ 후속 작업:
  - [ ] 선택한 파이프라인 PoC 구현
  - [ ] 성능 부하 테스트 (QPS, 동시성)
  - [ ] KGE 학습 인프라 별도 계획
  - [ ] Fine-tuning 필요성 재검토 (C1-LLM-EVAL 결과 기반)
```
