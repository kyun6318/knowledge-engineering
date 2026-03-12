# GCP Vertex AI API 기능 테스트 계획 (3일)

> GraphRAG 서비스 구축을 위해 GCP Vertex AI의 주요 API들이 **실제로 동작하는지**, **한국어 품질이 충분한지** 검증하는 3일 테스트 계획입니다.

## 이 테스트가 하는 일

GraphRAG 파이프라인의 각 단계에서 사용할 GCP API들의 **기능 동작 여부**와 **한국어 품질**을 검증하여, 서비스 설계 의사결정에 필요한 데이터를 확보합니다.

```
GraphRAG 파이프라인:  문서 수집 → 텍스트 정제 → NER(엔티티 추출) → 임베딩 → 검색 → 생성
                       ↑            ↑            ↑               ↑        ↑       ↑
GCP API:          Document AI   Gemini 멀티모달  Gemini API    Embeddings  RAG   Gemini API
                  Vertex AI Search                              API     Engine  Grounding
```

## 테스트 범위

| ID | 테스트 항목 | GCP 서비스 | 검증 목적 |
|----|-----------|-----------|----------|
| C1 | Gemini API 기본 추론 | Gemini 2.5 Flash/Pro | 호출 패턴, 스트리밍, 한국어 품질 |
| C2 | Embeddings API | gemini-embedding-001 | 문서 임베딩, 유사도 검색 품질 |
| DOC | Document AI | OCR / Layout Parser | PDF → 구조화 텍스트 추출 |
| MMD | Gemini 멀티모달 | Gemini (PDF/이미지 입력) | Document AI 대안 비교 |
| NER | Gemini 기반 NER | Gemini API | 엔티티/관계 추출 (지식 그래프 핵심) |
| C5 | RAG Engine | Vertex AI RAG | 문서 검색 + 생성 통합 |
| VAS | Vertex AI Search | Discovery Engine | URL 기반 자동 크롤링+인덱싱 |
| C6 | Grounding | Google Search 연동 | 실시간 정보 보완 |
| C10 | Prompt Caching | Gemini Context Caching | 운영 비용 절감 가능성 |
| X1 | API 에러 핸들링 | 전체 | 에러 코드, 재시도 패턴 확인 |

## 3일 일정 구조

```
Day 1                           Day 2                                     Day 3
┌───────────────────┐  ┌───────────────────────────────────────┐  ┌──────────────────────┐
│ LLM 기본 기능       │  │ 데이터 수집 → 정제 → NER                │  │ 검색 + 생성 + 운영     │
├───────────────────┤  ├───────────────────────────────────────┤  ├──────────────────────┤
│ C1: Gemini API    │  │ C5 corpus + VAS 인덱싱 (백그라운드)     │  │ C5: RAG 검색+생성     │
│ C2: Embedding     │  │ DOC: Document AI                      │  │ VAS: Vertex AI Search│
│                   │  │ MMD: Gemini 멀티모달                    │  │ C6: Grounding        │
│                   │  │ NER: 엔티티/관계 추출                   │  │ C10: Prompt Caching  │
│                   │  │ E2E: 정제→NER 파이프라인 비교            │  │ X1: 에러 핸들링       │
│                   │  │                                        │  │ 결과 종합 + 의사결정   │
└───────────────────┘  └───────────────────────────────────────┘  └──────────────────────┘
```

**핵심 흐름**: Day 2 오전에 RAG corpus import와 VAS 인덱싱을 먼저 트리거하고, 나머지 작업을 하는 동안 백그라운드로 완료시킵니다. Day 3 시작 시 즉시 검색 테스트에 진입합니다.

## 테스트 환경

- **GCP 프로젝트**: ml-api-test-vertex
- **리전**: us-central1 (Vertex AI), us (Document AI), global (Discovery Engine)
- **예산**: $500 경고 / $800 강제 중단
- **SDK**: `google-genai >= 1.5.0`, `google-cloud-documentai >= 2.29.0`, `google-cloud-discoveryengine >= 0.13.0`

## 데이터셋

| ID | 용도 | 형태 | 규모 | 언어 비율 |
|----|------|------|------|----------|
| DS-RAG-DOCS | RAG 문서 (이력서+뉴스) | PDF + TXT | 200~500건 | KO/EN 7:3 |
| DS-PDF-SAMPLE | Document AI / 멀티모달 평가 | PDF (10MB 미만, 5p 이하) | 20~30건 | KO/EN 7:3 |
| DS-LLM-EVAL | LLM 평가셋 | JSONL | 50~100건 | KO/EN 7:3 |
| DS-EMBED-SAMPLE | 임베딩 품질 평가 | JSONL | 1K~5K건 | KO/EN 7:3 |
| DS-NER-EVAL | NER 정답 데이터 (사전 라벨링 필수) | JSONL | 10~20건 | KO/EN 7:3 |

## 한국어 품질 평가 기준

| 축 | 설명 | 점수 |
|----|------|------|
| 정확성/환각 | 사실 오류, 존재하지 않는 정보 생성 여부 | 0~3 |
| 완전성 | 질문 의도를 충분히 충족했는가 | 0~3 |
| 도메인 적합성 | 채용/이력서/기업 맥락 용어·표현 적절성 | 0~2 |
| **합계** | 6점 이상 = 사용 가능, 4~5 = 개선 필요, 3 이하 = 불가 | **0~8** |

## 문서 구조 및 읽는 순서

| 순서 | 문서 | 설명 |
|------|------|------|
| 1 | `api-test-3day.md` | **v2 — 기본 계획서.** 3일 테스트의 전체 구조, 환경 설정, 각 테스트별 상세 코드와 Pass/Fail 기준을 포함합니다. 가장 먼저 읽으세요. |
| 2 | `api-test-3day-v3.md` | **v3 — 리뷰 반영 개선본.** v2에서 발견된 문제점(코드 누락, 부하 과다, 평가 자동화 부족)을 수정한 버전입니다. 실제 테스트 실행 시 이 문서를 사용하세요. |
| 3 | `api-test-3day-v3-review.md` | **v3 리뷰 결과.** v3에 남아 있는 5개 필수 패치 항목과 2개 결론 왜곡 가능성을 정리한 리뷰입니다. 테스트 전 반드시 확인하세요. |

### 버전 변경 요약

```
v2 (api-test-3day.md)
 └─ 리뷰 피드백 반영 ─→ v3 (api-test-3day-v3.md)
                          ├─ 코드 누락 수정 (Few-shot NER, 관계 평가 등)
                          ├─ 부하 축소 (임베딩 sweep 제거, MMD 5건, Rate Limit 10회)
                          ├─ 테스트 프레임워크 추가 (run_test, save_test_result)
                          └─ 세션 단절 대응 (pending_ops.json 저장/복원)
                        └─ 리뷰 ─→ v3-review (api-test-3day-v3-review.md)
                                    ├─ P0: SDK 호환성, VAS 문서 확인, DocAI 성공/실패 확정
                                    └─ 결론 왜곡: 비용 추정 상수 고정, 캘리브레이션 모델 선택
```

## 사전 준비 체크리스트

테스트 시작 전 반드시 완료해야 할 항목입니다:

```
□ GCP 프로젝트 API 활성화 (Vertex AI, Cloud Storage, Document AI, Discovery Engine)
□ 서비스 계정 + ADC 설정
□ SDK 설치 및 버전 확인
□ Document AI 프로세서: GCP Console에서 사전 생성 (OCR + Layout Parser)
□ DS-NER-EVAL gold 데이터 라벨링 완료 (테스트 D-2까지)
□ 데이터셋 GCS 업로드
□ 프롬프트 파일 준비 (한국어·영어 쌍)
```

## 제외 항목

아래 항목들은 이 3일 테스트에서 다루지 않습니다:

- **Traditional ML** (AutoML, Feature Store, Batch Predict)
- **Deep Learning 인프라** (GPU/TPU 학습, KFP, 분산학습)
- **Fine-Tuning** (SFT, LoRA) — 추후 품질 개선 단계
- **Agent Engine** — 별도 일정
- **성능 부하 테스트** (QPS, 동시성) — 기능 확인 후 수행
- **리전 Latency 측정** — 별도 수행
