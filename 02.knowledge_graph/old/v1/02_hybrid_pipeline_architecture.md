# 하이브리드 KG 추출 파이프라인 설계 (검증 반영)

## 목적
이력서 + 기업 뉴스 + Nice 기업 정보에서 지식 그래프를 추출하되,
LLM 비용을 TCO 기준 60~80% 절감하는 것을 현실적 목표로 설정한다.

> "90%+ 절감"은 API 토큰 비용만 비교한 낙관적 수치이며,
> ML 인프라/개발/운영 비용을 포함한 TCO 기준으로는 60~80%가 현실적이다.

---

## Phase 0: 전제 조건 — 스키마 및 인프라

### 0-1. Closed Ontology 정의 (최우선)

이력서 도메인은 Open IE가 아닌 폐쇄형 온톨로지로 전환한다.

**노드 타입 (Node Types)**:
```
Person          — 후보자
Organization    — 회사, 기관
EducationInst   — 학교, 교육기관
Skill           — 기술 스택, 도구
Role            — 직함, 직무
Project         — 프로젝트
Certification   — 자격증, 인증
Degree          — 학위
Experience      — 경력 블록 (중간 노드)
Education       — 학력 블록 (중간 노드)
```

**엣지 타입 (Edge Types)** — 폐쇄 집합:
```
WORKED_AT           Person → Organization (via Experience)
HELD_ROLE           Person → Role (via Experience)
HAS_SKILL           Person → Skill
USED_TECH           Experience/Project → Skill
STUDIED_AT          Person → EducationInst (via Education)
HAS_DEGREE          Person → Degree (via Education)
CERTIFIED_IN        Person → Certification
PARTICIPATED_IN     Person → Project
STARTED_AT          Experience/Education → Date (property)
ENDED_AT            Experience/Education → Date (property)
LOCATED_IN          Organization → Location
MANAGED             Person → Project/Team
```

> **주의**: 기업 뉴스/Nice 기업 정보용 스키마는 별도 정의 필요.
> 이력서 스키마와 Organization 노드를 통해 연결된다.

### 0-2. PDF/HWP 파싱 인프라 (Critical)

세 응답 모두 누락했으나 전체 난이도의 30~40%를 차지하는 핵심 전처리.

```
[원본 파일]
    │
    ├─ PDF → PyMuPDF / pdfplumber (레이아웃 보존)
    ├─ DOCX → python-docx
    ├─ HWP → python-hwp / hwp5 (한국 특수)
    ├─ 스캔 이미지 → OCR (Tesseract / Naver Clova OCR)
    │
    ▼
[정규화된 텍스트 + 레이아웃 메타데이터]
    • line_id, block_id, page, char_offset
    • 표/컬럼 구조 보존
    • 이미지/로고 영역 제거
```

### 0-3. 개인정보 익명화

Silver label 생성 시 외부 LLM API로 이력서를 전송하려면:
- 이름, 연락처, 주민번호, 주소 등 PII를 마스킹/토큰화
- 또는 On-premise LLM (vLLM + 한국어 모델)으로 처리

---

## Phase 1: 전처리 (비용 ≈ 0, compute만)

### 1-1. 중복 제거
- **방법**: SimHash / MinHash + 텍스트 정규화 해시
- **목적**: 동일인 중복 지원서, 수정본, 채용 사이트 중복 제거
- **예상 효과**: 처리 대상 자체를 20~40% 감소 (데이터 출처에 따라 편차 큼)

### 1-2. 문서 타입 분류
- **방법**: char n-gram + linear model (SVM/LightGBM)
- **목적**: 이력서 / 자기소개서 / 포트폴리오 / 경력기술서 분리
- **이유**: 문서 타입별 추출 규칙이 완전히 다름

### 1-3. 템플릿 클러스터링 (선택적)
- **방법**: heading signature + 날짜 표현 패턴 + bullet 구조로 클러스터링
- **목적**: 채용 플랫폼별 양식 그룹화 → 템플릿별 추출 규칙 최적화
- **주의**: 출처가 다양하면 클러스터 수 폭발 가능 → 주요 5~10개 템플릿만 커버
- **현실적 판단**: 데이터 탐색 후 ROI 평가하여 적용 여부 결정

### 1-4. 섹션 분할
- **방법**: heading 패턴 + CRF line labeling + 위치/줄간격 피처
- **섹션**: 경력, 학력, 기술, 프로젝트, 자격증, 수상, 자기소개, 기본정보
- **모델**: Small BERT encoder (KLUE-BERT) 추천 (CRF/BiLSTM-CRF보다 2025년 기준 우위)
- **핵심**: 섹션별로 다른 추출 전략을 적용하기 위한 전제 조건

---

## Phase 2: 규칙 기반 추출 (비용 ≈ 0)

> 예상 커버리지: 40~70% (데이터 품질에 크게 좌우, 파일럿 실측 필수)

### 2-1. 정형 필드 Regex
```
• 날짜/기간: 2019.03 ~ 2022.06, 2019년 3월, '19.3 등 다양한 변형 커버
• 이메일, 전화번호, URL, GitHub
• 자격증 번호 패턴
• 학위 표기 (학사, 석사, 박사, B.S., M.S., Ph.D.)
```

### 2-2. 기술 사전 + Fuzzy Matching
- Curated 기술명 사전 구축 (Python, PyTorch, React, AWS, ...)
- Fuzzy matching으로 변형 커버 (pytorch → PyTorch)
- **직접 HAS_SKILL / USED_TECH 엣지 생성**
- GLiNER zero-shot보다 정확도 높음 (검증됨)

### 2-3. 블록 기반 Relation Assembly (ChatGPT 핵심 인사이트)

이력서 경력 블록은 문장 파싱 없이 구조 파싱으로 관계 추출 가능:

```
입력:
  2021.03 - 2023.08 | ABC Tech | Backend Engineer
  - 추천 시스템 API 개발
  - Python, FastAPI, PostgreSQL 사용

출력 (구조 파싱만으로):
  Person — WORKED_AT → ABC Tech
  Person — HELD_ROLE → Backend Engineer
  Experience — STARTED_AT → 2021.03
  Experience — ENDED_AT → 2023.08
  Experience — USED_TECH → Python
  Experience — USED_TECH → FastAPI
  Experience — USED_TECH → PostgreSQL
```

- **관계 라벨**: Closed Ontology에서 선택 (자유 생성 X)
- **Evidence**: span offset으로 저장 (자연어 재생성 X)
  ```json
  {"document_id": "doc_001", "page": 1, "block_id": "exp_1", "line_start": 5, "line_end": 8}
  ```

### 2-4. 회사/학교 사전 매칭
- 주요 회사/학교 사전 구축 + alias dictionary
- "삼성전자", "Samsung Electronics", "삼성" → canonical name 매핑

---

## Phase 3: ML 모델 추출 (비용: GPU 수시간)

> 예상 커버리지: 규칙으로 못 잡은 나머지 중 20~30%

### 3-1. NER (Named Entity Recognition)
- **베이스 모델**: KLUE-BERT / KoELECTRA (small BERT encoder)
  - ~~Llama-3-8B~~: 한국어 토크나이저 비효율 → 한국어 특화 모델 우선
  - ~~GLiNER zero-shot~~: 한국어 F1 낮음 → fine-tuned NER 우선
- **추출 대상**: 프로젝트명, 역할명, 도메인 스킬, 제품/서비스명
- **학습 데이터**: LLM silver label + 사람 검수 (Phase 5 참조)
- **추론 성능**: T4 GPU 기준 50~200 문서/초 (~~수백 문서/초~~는 과장)
- **피처**: 텍스트 + 섹션명 + 줄 위치 + bullet 여부 + 날짜 근접성

### 3-2. Relation Extraction (관계 추출)
- **방법**: Entity Marker + multi-class classifier
- **관계 후보 필터링** (비용 절감 핵심):
  - 같은 블록 안 엔티티 쌍만
  - 타입 조합이 가능한 pair만 (회사-직무, 프로젝트-기술, 학교-학위)
  - 일정 토큰 거리 이내만
- **현실적 성능**: Macro F1 60~80% (~~90%+는 과장~~)
  - Class imbalance 대응 필요 (WORKED_AT 편중)
  - Negative class (관계 없음) 처리 별도 설계
- **학습 데이터**: NER과 동일하게 LLM silver label 활용

### 3-3. Confidence Score 부여
- 각 추출 결과에 confidence 부여
- **주의**: BERT softmax confidence는 calibration 필요 → Temperature Scaling 적용
- Threshold 튜닝용 gold test set 별도 구축

---

## Phase 4: LLM Fallback (비용: 원래의 10~20%)

> 초기 fallback 비율: 30~40% → 안정화 후: 10~20%
> (~~5~10%~~는 과도하게 낙관적)

### 4-1. LLM 전용 케이스
- 서술형 경력 요약에서 암묵적 관계 추출
- "성과"와 "역할" 분리
- 프로젝트 설명 속 기술 사용 맥락 해석
- 여러 줄에 흩어진 엔티티 연결
- ML 모델 confidence < threshold인 결과 재판정

### 4-2. 비용 최적화
- **경량 LLM**: Claude Haiku / Gemini Flash급 (이력서 RE에 Opus급 불필요)
- **Batch API**: Anthropic/OpenAI 모두 50% 할인 (비동기 24시간 이내 처리)
- **Properties 분리**: 날짜/숫자/수량은 LLM이 아닌 regex/후처리로 추출 (토큰 절감)
- **Closed Ontology**: 관계 라벨 자유 생성 X → 프롬프트 토큰 및 출력 토큰 절감

---

## Phase 5: 학습 데이터 구축 (Knowledge Distillation)

### 5-1. 샘플링 전략
- 150GB 중 다양한 직무/양식/출처의 **2,000~5,000건** 샘플링
- 직무 카테고리(개발, 디자인, 마케팅 등), 경력 수준(신입/경력), 문서 형식별 층화 추출

### 5-2. Silver Label 생성
- Closed Ontology 기반 프롬프트로 GPT-4o / Claude Sonnet 처리
- **개인정보 마스킹 후** 전송 또는 On-premise LLM 사용
- 출력: 엔티티 + 관계 + span offset

### 5-3. Gold Label 확보
- 전문가 검수로 silver label의 10~20% 승격
- 이 gold set이 평가 프레임워크의 기준이 됨

### 5-4. 모델 학습
- **섹션 분류기**: KLUE-BERT fine-tune
- **NER**: KLUE-BERT / KoELECTRA + BIO tagging
- **RE**: Entity Marker + multi-class classifier
- **학습 인프라**: QLoRA (SLM의 경우) 또는 full fine-tune (small encoder의 경우)
- **Structured Output 안정화**: Constrained Decoding (Outlines/Guidance) 적용 (SLM 사용 시)

### 5-5. Active Learning 루프 (장기)
- LLM fallback 케이스를 주기적으로 수집
- 자주 발생하는 패턴만 선별하여 ML 모델 재학습에 투입
- 시간이 갈수록 LLM fallback 비율 감소

---

## Phase 6: 후처리 — Entity Resolution & 그래프 통합

### 6-1. Entity Resolution (동의어 통합)
- **임베딩**: BGE-M3 (한국어 지원 우수)
- **클러스터링**: HDBSCAN
- **스케일 대응**: FAISS / ScaNN ANN 인덱스 필요 (수천만 엔티티 시)
- **타입별 분리**: Skill, Organization, Role 각각 독립 클러스터링 공간
- **보조 수단**: alias dictionary + fuzzy matching + BM25 trigram

### 6-2. 그래프 통합 및 충돌 해결
- 3단계 파이프라인(Rule + ML + LLM) 결과 머지
- 동일 엔티티 다른 방식 추출 시: confidence 기반 우선순위
- 동일 인물 수정 버전 이력서: 최신 버전 우선 + 이력 보존

### 6-3. Provenance 저장
- 모든 triple에 추출 출처 (rule / ml / llm) 및 confidence 기록
- span offset으로 원문 참조 가능하게

---

## 데이터 소스별 전략 차이

| 항목 | 이력서 | 기업 뉴스 | Nice 기업 정보 |
|------|--------|-----------|---------------|
| 구조화 정도 | 반정형 (높음) | 비정형 (낮음) | 정형 (매우 높음) |
| Rule-based 효과 | 높음 (40~70%) | 낮음 (10~20%) | 매우 높음 (80~90%) |
| 추천 전략 | 블록 파싱 + ML + LLM fallback | SLM fine-tune + LLM fallback | 직접 그래프 매핑 (DB → KG) |
| 스키마 | 이력서 Closed Ontology | 뉴스 Ontology (별도 설계) | 기업 정보 스키마 (DB 스키마 기반) |
| 연결 노드 | Organization | Organization, Person | Organization |

---

## 비용 추정 (현실적 범위)

### 100% LLM 기준선
- 150GB 한국어 텍스트 ≈ 75억~150억 토큰 (입출력 합산)
- GPT-4o 기준: 5,000만~1.5억 원
- Claude Sonnet 기준: 유사 범위
- GPT-4o-mini / Haiku 기준: 500만~1,500만 원

### 하이브리드 파이프라인 예상 비용
| 항목 | 비용 범위 |
|------|----------|
| Silver Label 생성 (2~5K건) | 50만~200만 원 |
| Annotation 인력 (gold set) | 500만~1,000만 원 |
| ML 모델 학습 GPU | 100만~300만 원 |
| ML 추론 (150GB 전체) | 50만~200만 원 |
| LLM Fallback (10~20%) | 500만~3,000만 원 |
| Entity Resolution | 50만~100만 원 |
| **합계** | **1,250만~4,800만 원** |

> **TCO 기준 절감률**: 기준선 대비 약 60~80%
> (엔지니어링 인건비 별도, 프로젝트 규모에 따라 변동)
