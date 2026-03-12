# 세 AI 응답 타당성 검토 요약

## 검토 대상
- Gemini v1, Claude v1, ChatGPT v1
- 공통 주제: 150GB 이력서에서 KG 추출 시 LLM 비용 절감을 위한 하이브리드 ML 전략

---

## 1. 세 응답의 공통 주장 — 타당성 평가

### [VALID] LLM을 "교사"로, ML을 "운영자"로 사용하는 Knowledge Distillation
- 세 응답 모두 동일한 방향 제시
- 학술적/산업적으로 검증된 접근법
- 핵심: 1~2% 샘플만 LLM으로 처리 → silver label 생성 → ML 모델 학습

### [VALID] Rule-based → ML → LLM Fallback 계층 구조
- 산업 표준 패턴으로 방향성은 확실히 타당
- 단, 각 계층의 비율(60-70% / 20-30% / 5-15%)은 데이터 품질에 크게 좌우됨 → **파일럿 실측 필수**

### [VALID] 이력서가 반정형(semi-structured) 문서라는 전제
- 범용 텍스트 대비 구조적 패턴이 강함
- 섹션 구조, 날짜 패턴, 기술 스택 나열 등이 규칙 기반 처리에 적합

### [PARTIALLY VALID] "90%+ 비용 절감" 주장
- **API 토큰 비용만 비교하면** 90%+ 절감 가능
- **TCO(총소유비용) 포함 시** 60~80% 수준으로 하향 조정 필요
  - ML 모델 개발/학습 GPU 비용
  - 학습 데이터 annotation 인력 비용
  - 인프라 운영/유지보수 비용
  - Active Learning 루프 운영 비용

### [PARTIALLY VALID] Confidence-based Routing으로 LLM fallback 5~15%
- 안정화된 모델 기준 달성 가능하나, 초기에는 30~40% fallback 예상
- BERT 계열 softmax confidence는 잘 calibrated되지 않음 → Temperature Scaling 필요
- Threshold 튜닝용 gold test set 구축 필요

---

## 2. 응답별 고유 인사이트 — 타당성 평가

### Gemini 고유
| 주장 | 평가 | 비고 |
|------|------|------|
| Llama-3-8B / Phi-3-mini SLM | [PARTIALLY VALID] | 한국어 토크나이저 효율 문제, EEVE-Korean/EXAONE/Qwen2.5 등 한국어 특화 모델이 더 적합 |
| GLiNER zero-shot NER | [PARTIALLY VALID] | 한국어 성능 영어 대비 10~20%p 낮음, 기술명은 사전 매칭이 더 정확 |
| BGE-M3 + HDBSCAN Entity Resolution | [PARTIALLY VALID] | 방향 타당하나 수억 개 엔티티 스케일 문제, 타입별 분리 필요 |
| BERT-base Dependency Parsing 라우터 | [QUESTIONABLE] | 이력서 비문법 텍스트에서 불안정, 단순 휴리스틱으로 대체 가능 |
| "토큰당 비용 1/100" | [QUESTIONABLE] | TCO 포함 시 과장, 실질 절감 70~90% 수준 |

### Claude 고유
| 주장 | 평가 | 비고 |
|------|------|------|
| KoELECTRA NER "수백 문서/초" | [QUESTIONABLE] | 문서 1건 = 2~4 sequences, 실제 50~200 문서/초 |
| Entity Marker RE 90%+ accuracy | [QUESTIONABLE] | silver label noise 미고려, macro F1 기준 60~70%대 가능, negative class 처리 미언급 |
| Batch API 50% 할인 | [VALID] | Anthropic/OpenAI 모두 공식 지원 |
| Properties 추출 분리 (regex/후처리) | [VALID] | 실질적 토큰 절감 기여, 구현 난이도 낮음 |
| 실행 우선순위 ROI 기반 정렬 | [VALID] | 기술사전 → 섹션파싱 → NER → RE 순서 실무적으로 가치 있음 |

### ChatGPT 고유
| 주장 | 평가 | 비고 |
|------|------|------|
| Open IE → Closed Ontology 전환 | [VALID] | 가장 핵심적 설계 결정, 모든 후속 단계 복잡도 감소 |
| 블록 기반 Relation Assembly | [VALID] | 이력서 도메인에서 문장 파싱보다 안정적, 즉시 채택 가능 |
| Line NLP > Sentence NLP | [VALID] | 이력서 parsing 커뮤니티에서 검증된 사실 |
| Evidence → Span Offset 저장 | [VALID] | 토큰 절감 + 검증 용이 + 재현성, 단 PDF offset 보존 전제 |
| 템플릿 클러스터링 | [PARTIALLY VALID] | 플랫폼 수출 이력서에서 효과적이나 출처 다양 시 클러스터 폭발 |
| CRF/BiLSTM-CRF 추천 | [PARTIALLY VALID] | 2025년 기준 small BERT encoder가 더 나은 균형점 |
| 원래 프롬프트 비판 3가지 | [VALID] | 관계 자유생성, evidence 자연어, relation-first 모두 타당한 비판 |

---

## 3. 세 응답 공통 누락 사항 (Critical Gaps)

### [CRITICAL] PDF/HWP 파싱 파이프라인
- 150GB 이력서의 파일 형식 분포(PDF/DOCX/HWP/스캔이미지) 미언급
- 한국 기업 환경에서 HWP 비율이 높을 수 있음 (python-hwp 별도 필요)
- OCR 이력서가 포함되면 rule-based 전제 자체가 약화됨
- **이 단계가 전체 프로젝트의 30~40% 난이도를 차지**

### [CRITICAL] KG 스키마/온톨로지 설계
- 어떤 노드/엣지 타입을 정의할지 구체적 설계 없음
- 스키마 변경 시 기존 그래프 마이그레이션 전략 없음

### [CRITICAL] 개인정보보호법(PIPA) 이슈
- Silver label 생성을 위해 이력서를 외부 API(GPT-4o)로 전송 시 법적 문제
- On-premise LLM 또는 익명화 전처리 필요

### [HIGH] 평가 프레임워크 부재
- KG 품질 측정 지표(Triple Precision/Recall, Entity F1) 미정의
- Gold test set 구축 방법 미명시

### [HIGH] 학습 데이터 구축 공수 과소평가
- NER + RE 학습 데이터 annotation은 도메인 전문가 필요
- 이력서 도메인 공개 데이터셋 거의 없음
- Silver label 품질 검증/검수 체계 미언급

### [HIGH] 그래프 통합 레이어
- 3단계 파이프라인(Rule + ML + LLM) 결과의 중복/충돌 처리
- 동일 인물의 수정 버전 이력서 KG 머지 전략

### [MEDIUM] Entity Resolution/Linking 난이도
- 한국어 회사명 정규화 ("네이버" / "NAVER" / "(주)네이버") 어려움
- 스타트업/중소기업/인수합병 회사명 alias 사전 구축/유지 비용

---

## 4. 과도하게 낙관적인 주장 정리

| 주장 | 출처 | 현실적 수치 |
|------|------|------------|
| 비용 1/100 절감 | Gemini | TCO 기준 70~90% 절감 |
| 수백 문서/초 처리 | Claude | 50~200 문서/초 |
| RE 90%+ accuracy | Claude | Macro F1 기준 60~80% |
| Rule-based 60~70% 커버 | Claude | 데이터 품질에 따라 40~75% |
| LLM fallback 5~10% | Claude/ChatGPT | 초기 30~40%, 안정화 후 10~20% |
| "수억 원" 기준 비용 | Gemini | GPT-4o 기준 5,000만~1.5억 원 (출력 포함) |

---

## 5. 결론

### 채택할 핵심 전략 (검증됨)
1. **Closed Ontology 전환** (ChatGPT) — 최우선
2. **블록 기반 Relation Assembly** (ChatGPT) — Rule-based 핵심
3. **LLM Teacher → ML Student Distillation** (3사 공통)
4. **Confidence-based Routing** (3사 공통)
5. **Properties 추출 분리** (Claude) — 즉시 적용 가능
6. **Evidence Span Offset** (ChatGPT) — 토큰 절감

### 수정/보완 필요 사항
1. SLM 모델은 한국어 특화 모델(EEVE-Korean, EXAONE, Qwen2.5) 우선 검토
2. GLiNER보다 기술명 사전 + small BERT encoder NER 조합 추천
3. 복잡도 라우터는 BERT Dependency Parsing 대신 단순 휴리스틱(문장길이, 패턴밀도)
4. Entity Resolution은 타입별 분리 + ANN 인덱스(FAISS) 필요
5. 비용 추정치는 파일럿 실측 후 보정 필수

### 추가 설계 필수 항목
1. PDF/HWP 파싱 파이프라인 (전체 난이도의 30~40%)
2. 개인정보 익명화 전처리
3. KG 스키마/온톨로지 정의
4. 평가 프레임워크 및 Gold Test Set
5. 그래프 통합 및 충돌 해결 로직
