# 리스크 분석 및 원본 응답 수정 사항

## 1. 원본 프롬프트(prompt.md) 개선 포인트

ChatGPT가 지적한 3가지 비판은 모두 [VALID]로 검증됨.

### 수정 1: 관계 라벨 자유 생성 → 폐쇄 집합 제한
**현재**: "문맥에 맞는 다른 라벨을 자유롭게 생성하세요"
**문제**: LLM이 의미 해석 + naming까지 수행 → 비용 증가 + 정규화 비용 추가
  - 동일 관계가 WORKED_AT, WAS_EMPLOYED_BY, JOINED_COMPANY 등으로 분산
**수정**: 이력서 도메인에서는 12~15개 폐쇄 집합으로 제한

### 수정 2: evidence 자연어 생성 → span offset 참조
**현재**: "evidence": "엔티티와 관계를 추출한 원본 문장(원문에서 발췌)"
**문제**: 원문 복사에도 토큰 비용 발생, 할루시네이션 위험
**수정**: document_id + page + block_id + char_start/end로 대체
**주의**: PDF char offset 보존이 전제 조건 (파싱 품질 의존)

### 수정 3: Relation-first → Section/Block-first
**현재**: "문장에서 동사/서술어를 먼저 찾는다"
**문제**: 이력서는 문법적 완결 문장이 아닌 경우가 대부분
  - "AWS EC2 활용, 트래픽 30% 절감 달성" → 동사 기반 파싱 부적합
**수정**: 섹션/블록 구조를 먼저 파싱하고, 블록 내 슬롯 매핑으로 관계 조립

---

## 2. 과장된 수치 보정표

| 항목 | 원본 주장 | 보정 수치 | 근거 |
|------|----------|----------|------|
| 비용 절감률 | 90%+ (3사 공통) | TCO 60~80% | ML 인프라/개발/운영 비용 포함 |
| Rule-based 커버리지 | 60~70% (Claude) | 40~70% (편차 큼) | 데이터 품질, OCR 비율에 좌우 |
| LLM fallback 비율 | 5~10% (Claude/ChatGPT) | 초기 30~40%, 안정화 10~20% | 모델 성능 + calibration 반영 |
| NER 처리 속도 | 수백 문서/초 (Claude) | 50~200 문서/초 | 이력서 1건 = 2~4 sequences |
| RE accuracy | 90%+ (Claude) | Macro F1 60~80% | class imbalance, negative class |
| 토큰 비용 절감 | 1/100 (Gemini) | 1/5~1/10 (TCO) | GPU 인프라 비용 포함 |
| 기준 비용 | 수억 원 (Gemini) | 5,000만~1.5억 원 | GPT-4o 입출력 합산 기준 |

---

## 3. 기술적 리스크 상세

### [CRITICAL] PDF/HWP 파싱 — 전체 프로젝트의 병목

**왜 critical인가**:
- Rule-based + 블록 파싱 전략의 전제 조건이 "정확한 텍스트 + 레이아웃 추출"
- 이 전제가 무너지면 Phase 2 전체의 효과가 반감
- 한국 기업 환경에서 HWP 파일 비율이 높을 수 있으나, python-hwp의 완성도가 낮음

**대응**:
- Stage 1에서 파일 형식 분포를 먼저 확인
- OCR 비율이 30% 이상이면 LayoutLM / DocTR 도입 검토
- HWP 비율이 높으면 LibreOffice headless 변환 파이프라인 추가

### [CRITICAL] 개인정보보호법 (PIPA)

**이슈**:
- 이력서를 GPT-4o / Claude API로 전송 시 개인정보 해외 전송에 해당
- 동의 없이 처리 시 법적 제재 가능

**대응 옵션**:
1. **On-premise LLM**: vLLM + 한국어 모델 (EEVE-Korean, EXAONE) 자체 호스팅
2. **PII 마스킹**: 이름, 연락처, 주민번호를 토큰화 후 LLM 전송, 결과에서 역매핑
3. **데이터 주체 동의**: silver label 대상 샘플에 대해 사전 동의 확보

### [HIGH] Silver Label 오류 전파

**이슈**:
- LLM이 생성한 silver label의 오류가 NER/RE 모델에 전파
- "garbage in, garbage out" — teacher 모델 정확도에 ceiling 종속

**대응**:
- Silver label의 10~20%를 전문가 검수 (gold set 확보)
- 검수 시 inter-annotator agreement 측정
- Silver label confidence가 낮은 항목 우선 검수

### [HIGH] Entity Resolution 스케일

**이슈**:
- 150GB 이력서에서 추출된 엔티티가 수천만~수억 개 예상
- HDBSCAN은 메모리 내 수백만 개까지만 처리 가능
- 한국어 회사명 정규화 ("구글", "Google Korea", "알파벳코리아") 난이도 높음

**대응**:
- FAISS / ScaNN ANN 인덱스 활용
- 타입별 독립 클러스터링 (Skill, Org, Role 분리)
- 주요 기업 canonical 사전 선구축 (KOSPI/KOSDAQ + 주요 외국기업)

### [MEDIUM] 한국어 NLP 도구 체인

**이슈**:
- KoELECTRA/KLUE-BERT는 뉴스/위키로 사전학습 → 이력서 특유 문체에 약할 수 있음
- 한국어 형태소 분석 없이 BIO tagging 시 경계 오류
- 기술 약어 (K8s, CI/CD, MSA) 처리 불안정

**대응**:
- 이력서 도메인 추가 사전학습 (Domain-Adaptive Pre-training)
- 형태소 분석기 (Mecab-ko) 연동
- 기술 약어 사전 별도 구축

### [MEDIUM] Confidence Calibration

**이슈**:
- BERT softmax 출력은 calibrated probability가 아님
- confidence 0.9가 실제 정확도 90%를 의미하지 않음
- 잘못된 threshold → LLM 과다 호출 또는 품질 저하

**대응**:
- Temperature Scaling / Platt Scaling 적용
- Reliability diagram으로 calibration 검증
- Gold test set 기반 threshold 최적화

---

## 4. 한국어 SLM 모델 선택 가이드 (Gemini 보정)

Gemini가 제안한 Llama-3-8B / Phi-3-mini 대신, 한국어 이력서 도메인에는 아래 모델을 우선 검토:

| 모델 | 크기 | 한국어 성능 | 비고 |
|------|------|------------|------|
| EEVE-Korean-10.8B | 10.8B | 우수 | 한국어 특화 학습 |
| EXAONE-3.5-7.8B | 7.8B | 우수 | LG AI Research, 한국어 강점 |
| Qwen2.5-7B | 7B | 양호 | 다국어, 한국어 토크나이저 효율적 |
| Llama-3-8B | 8B | 보통 | 한국어 토큰 효율 2~3배 낮음 |
| Phi-3-mini | 3.8B | 제한적 | 한국어 지원 부족, 비추천 |

> SLM fine-tuning 시에는 **한국어 토크나이저 효율**이 비용에 직결되므로
> 한국어 특화 모델 우선 선택이 중요하다.

---

## 5. 평가 프레임워크 (세 응답 모두 누락)

### 평가 지표
| 레이어 | 지표 | 목표 |
|--------|------|------|
| 섹션 분할 | Section Accuracy | > 85% |
| NER | Entity F1 (strict match) | > 80% |
| RE | Macro F1 (관계 유형별) | > 70% |
| Entity Resolution | Pairwise F1 | > 85% |
| E2E Triple | Triple F1 (exact match) | > 65% |

### Gold Test Set 구성
- 200~500건의 이력서를 전문가 2인이 독립 annotation
- Inter-annotator agreement (Cohen's κ) > 0.8 목표
- 직무/경력/문서형식별 층화 추출
- 이 test set은 **모델 학습에 사용하지 않고 평가 전용**으로 보존
