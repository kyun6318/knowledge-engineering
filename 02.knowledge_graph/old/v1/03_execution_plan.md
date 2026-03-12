# 실행 계획 — 우선순위 및 단계별 로드맵

## 원칙
- ROI 높은 순서대로 실행
- 각 단계에서 파일럿 실측 후 다음 단계 진행 여부 결정
- 비용 추정치는 모두 파일럿 결과로 보정

---

## Stage 1: 기반 구축 (1~2주)

### 1-1. 데이터 탐색 및 프로파일링
- [ ] 150GB 데이터의 파일 형식 분포 조사 (PDF/DOCX/HWP/이미지/기타)
- [ ] 무작위 500건 샘플링하여 구조 분석
  - 자유서술 비율 vs 정형 블록 비율
  - 한국어/영문 혼합 비율
  - 섹션 구조 패턴 유형
- [ ] OCR 필요 비율 확인
- [ ] 중복률 추정 (SimHash 테스트)

### 1-2. Closed Ontology 정의
- [ ] 이력서용 노드/엣지 타입 확정
- [ ] 기업 뉴스 / Nice 기업 정보용 스키마 초안
- [ ] 데이터 소스 간 연결 노드 (Organization) 설계

### 1-3. PDF/HWP 파싱 파이프라인 구축
- [ ] PyMuPDF + python-docx + python-hwp 통합 파서
- [ ] 레이아웃 메타데이터 보존 (line_id, block_id, page, char_offset)
- [ ] OCR 필요 문서 별도 처리 경로

**Stage 1 산출물**: 데이터 프로파일 리포트 + Closed Ontology v1 + 파싱 파이프라인

---

## Stage 2: 규칙 기반 추출 (2~3주)

### 2-1. 기술 사전 구축
- [ ] 기술 스택 사전 (초기 1,000~2,000개 기술명 + alias)
- [ ] Fuzzy matching 엔진 (RapidFuzz 등)
- [ ] HAS_SKILL / USED_TECH 자동 엣지 생성

### 2-2. 정형 필드 Regex
- [ ] 날짜/기간 파서 (다양한 한국어 표기 대응)
- [ ] 이메일, 전화번호, URL, 자격증 번호
- [ ] 학위 표기 패턴

### 2-3. 섹션 분할기
- [ ] Heading 패턴 + 위치 피처 기반 rule
- [ ] 파일럿 500건으로 정확도 측정
- [ ] (선택) KLUE-BERT line classifier 학습

### 2-4. 블록 기반 Relation Assembly
- [ ] 경력/학력/프로젝트 블록 파서
- [ ] 슬롯 매핑 규칙 → Closed Ontology 엣지 생성
- [ ] 회사/학교 사전 + alias dictionary

### 2-5. 파일럿 실측
- [ ] 500건 샘플에 규칙 파이프라인 적용
- [ ] **실제 커버리지 측정** (예상 40~70%, 실측으로 보정)
- [ ] 규칙으로 처리 불가한 케이스 분류 및 분석

**Stage 2 산출물**: 규칙 파이프라인 + 실측 커버리지 리포트

> **의사결정 포인트**: 규칙 커버리지가 50% 이상이면 Stage 3 진행.
> 30% 미만이면 SLM fine-tuning 우선 전략으로 전환.

---

## Stage 3: ML 모델 구축 (3~4주)

### 3-1. Silver Label 생성
- [ ] 개인정보 마스킹 파이프라인
- [ ] 2,000~5,000건 대표 샘플 추출 (층화 추출)
- [ ] Closed Ontology 기반 LLM 프롬프트 작성
- [ ] GPT-4o / Claude로 silver label 생성
- [ ] 전문가 검수 → gold set 확보 (silver의 10~20%)

### 3-2. NER 모델 학습
- [ ] KLUE-BERT / KoELECTRA 기반 BIO tagger
- [ ] 섹션 피처 + 레이아웃 피처 통합
- [ ] Gold set으로 평가 (Entity F1)
- [ ] 추론 최적화 (ONNX Runtime / TorchScript)

### 3-3. RE 모델 학습
- [ ] Entity Marker 방식 multi-class classifier
- [ ] 관계 후보 필터링 로직 (블록 내 + 타입 호환 쌍만)
- [ ] Negative class 처리 (관계 없음 분류)
- [ ] Gold set으로 평가 (Macro F1)

### 3-4. Confidence Calibration
- [ ] Temperature Scaling 적용
- [ ] Threshold 최적화 (Precision-Recall tradeoff)
- [ ] Gold test set 기반 검증

**Stage 3 산출물**: NER/RE 모델 + Calibrated confidence + 평가 리포트

---

## Stage 4: 파이프라인 통합 (2~3주)

### 4-1. Confidence-based Routing
- [ ] Rule → ML → LLM 3단계 라우팅 로직
- [ ] High confidence → 바로 저장
- [ ] Medium confidence → ML 재검증
- [ ] Low confidence → LLM fallback

### 4-2. LLM Fallback 최적화
- [ ] Haiku / Gemini Flash급 모델 선정
- [ ] Closed Ontology + Properties 분리 프롬프트
- [ ] Batch API 활용 (비동기 처리)

### 4-3. Entity Resolution
- [ ] BGE-M3 임베딩 + FAISS ANN 인덱스
- [ ] 타입별 독립 클러스터링 (HDBSCAN)
- [ ] Alias dictionary + fuzzy matching 보조

### 4-4. 그래프 통합
- [ ] 3단계 결과 머지 로직
- [ ] 중복/충돌 해결 규칙
- [ ] Provenance 저장 (출처 + confidence + span offset)

**Stage 4 산출물**: 통합 파이프라인 + E2E 테스트 결과

---

## Stage 5: 전체 데이터 처리 및 운영 (2~4주)

### 5-1. 150GB 전체 처리
- [ ] 배치 처리 인프라 (SageMaker Batch Transform 또는 자체 구성)
- [ ] 진행 상황 모니터링 + 에러 핸들링
- [ ] LLM fallback 비율 실시간 추적

### 5-2. 품질 검증
- [ ] 무작위 샘플 품질 검사
- [ ] Triple Precision/Recall 측정
- [ ] Entity Resolution 품질 검사

### 5-3. Active Learning 루프 (선택)
- [ ] LLM fallback 케이스 수집 + 패턴 분석
- [ ] 빈출 패턴 추가 학습
- [ ] 모델 재배포

---

## Stage 6: 기업 뉴스 / Nice 기업 정보 확장

### 6-1. Nice 기업 정보 (정형)
- [ ] DB 스키마 → KG 스키마 직접 매핑
- [ ] Organization 노드를 통해 이력서 KG와 연결

### 6-2. 기업 뉴스 (비정형)
- [ ] 뉴스 Ontology 정의
- [ ] SLM fine-tuning (한국어 특화 모델: EEVE-Korean / EXAONE / Qwen2.5)
- [ ] 또는 LLM 직접 사용 (뉴스 분량이 이력서 대비 적을 경우 비용 합리적)

---

## 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| PDF 파싱 품질 낮음 | Rule-based 커버리지 급감 | 레이아웃 분석 모델(LayoutLM) 도입 검토 |
| 한국어 NER 성능 부족 | ML 커버리지 감소, LLM fallback 증가 | 학습 데이터 증량 + 한국어 특화 모델 교체 |
| Silver label 오류 전파 | 하위 모델 품질 저하 | Gold set 비율 확대 (20~30%) |
| Confidence calibration 실패 | 라우팅 정확도 저하 | Platt Scaling 등 대안 기법 적용 |
| 개인정보 처리 법적 이슈 | 프로젝트 지연/중단 | On-premise LLM 우선 검토 |
| 이력서 트렌드 변화 (새 기술/직군) | 모델 성능 저하 | Active Learning + 기술 사전 자동 업데이트 |

---

## 핵심 의사결정 포인트

1. **Stage 1 완료 후**: 데이터 품질/형식에 따라 전체 전략 방향 확정
2. **Stage 2 파일럿 후**: 규칙 커버리지 실측 → ML 투자 규모 결정
3. **Stage 3 평가 후**: NER/RE 성능 → LLM fallback 비율 예측 → 비용 최종 추정
4. **기업 뉴스 전략**: 뉴스 분량에 따라 SLM vs LLM 직접 사용 결정
