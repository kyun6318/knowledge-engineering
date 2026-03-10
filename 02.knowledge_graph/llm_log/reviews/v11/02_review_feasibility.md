# v11 실현 가능성 리뷰

> 대상: 02.knowledge_graph/results/extraction_logic/v11/
> 기준: 비용 현실성, 전제 조건 충족 가능성, 04.graphrag 실행 계획과의 연동

---

## 1. 비용 실현 가능성

### 1.1 추출 LLM 비용: 현실적 (8/10)

| 시나리오 | 비용 | 판단 |
|---------|------|------|
| A. Haiku Batch (추천) | $523 | **현실적**. Haiku Batch 50% 할인이 실제로 적용되는 전제 |
| A'. DB-only | $397 | 파일 미포함 시 최소 비용 |
| B. Sonnet 폴백 | $2,863 | Haiku 품질 미달 시. **예산 5.5배 증가, 사전 승인 필요** |
| C. Gemini Flash | $288 | 최저 비용이나 **한국어 추출 품질 미검증** |

**리스크**: Haiku 4.5의 한국어 이력서 추출 품질이 70% 미만이면 Sonnet 전환 필수. 이 경우 **비용이 $523 → $2,863으로 5.5배 증가**하므로, Phase 0 Go/No-Go에서 이 분기점이 가장 중요.

**권고**: Phase 0에서 Haiku/Sonnet/Gemini Flash 3모델 동시 비교(20건)를 반드시 수행. 현재는 Haiku→Sonnet 2단계만 설계됨.

### 1.2 인프라 비용: 현실적 (8/10)

추출 관련 GCP 인프라 $362 (27주)는 합리적.
- Cloud Run Jobs $300: 배치 처리 특성상 실행 시간에만 과금
- GCS $36: 중간 결과 + 백업
- Vertex AI $26: 임베딩 1회성

### 1.3 숨겨진 비용

| 항목 | v11에서 미포함 | 예상 | 비고 |
|------|-------------|------|------|
| Neo4j AuraDB Professional | 04.graphrag 관리 | $100-200/월 | Phase 2부터 |
| Gold Label 인건비 | 04.graphrag 관리 | $5,840 | 전체 비용의 최대 항목 |
| DB 접근 비용 (resume-hub read replica) | 미언급 | 미상 | 기존 인프라 활용 가정 |
| Anthropic Batch API 한도 초과 시 | 미언급 | +20-50% | 동시 batch 제한 시 처리 시간 증가 |

---

## 2. 전제 조건 실현 가능성

### 2.1 Critical 전제 조건

| ID | 전제 | 실현 가능성 | 리스크 |
|----|------|-----------|--------|
| A2 | DB 이력서 500K | **미검증** | resume-hub 실제 데이터 수 확인 필요 |
| A8 | Haiku ≈ 85% Sonnet 품질 | **낙관적** | 한국어 이력서는 영어보다 품질 격차 클 수 있음 |
| A19 | BRN null 40% | **미검증** | 실제 비율 확인 전 |
| A27 | text-embedding-005 한국어 분별력 | **미검증** | Phase 0 검증 항목 |

### 2.2 전제 조건 충족 실패 시 영향

**최악 시나리오 분석**:

| 전제 실패 | 영향 | 비용 증가 | 일정 영향 |
|----------|------|----------|----------|
| Haiku 품질 <70% | Sonnet 전환 | +$2,340 | 없음 (동일 파이프라인) |
| DB 이력서 <300K | ROI 저하 | 없음 | 없음 |
| BRN null >60% | Organization 매칭률 70% 미만 | LLM 2차 매칭 비용 | +2주 |
| Embedding 한국어 미달 | Cohere 전환 | +$60 | +1주 (인덱스 재생성) |
| DB 접근 불가 | 전체 재설계 | 파일 파싱 비용 급증 | +5-6주 |

**DB 접근 불가(R2.18)**가 가장 치명적. v11이 DB-first 전략이므로 DB 접근이 차단되면 전체 아키텍처가 파일 기반으로 전환되어야 함.

### 2.3 가정 검증 순서 권고

1. **Week 0 (즉시)**: resume-hub DB 접근 가능 여부 확인
2. **Week 0**: BRN null 비율 실측 (100건 샘플)
3. **Week 1 (Phase 0)**: Haiku vs Sonnet vs Gemini Flash 품질 비교
4. **Week 1**: text-embedding-005 한국어 분별력 검증
5. **Week 1**: Anthropic Batch API 한도 확인

---

## 3. 04.graphrag 실행 계획과의 연동

### 3.1 Phase별 의존성 매핑

| 04.graphrag Phase | v11 추출 담당 | 의존성 |
|-------------------|-------------|--------|
| Phase 0 (Week 1) | LLM PoC 20건, Embedding 검증 | v11 03_prompt_design 프롬프트 사용 |
| Phase 1 (Week 2-6) | Pipeline B (1,000건 CandidateContext) | v11 §3 전체 + 03_prompt_design §2 |
| Phase 2 (Week 7-14) | Pipeline B' (파일) + 전체 스케일 | v11 §4 + 04_pii_and_validation |
| Phase 3 (Week 16-22) | Pipeline A (CompanyContext) + C (Graph) | v11 §2 + 03_prompt_design §1 |
| Phase 4 (Week 24-27) | 증분 처리 자동화 | v11 05_extraction_operations |

### 3.2 연동 갭 (Gap Analysis)

| 갭 | 설명 | 영향 | 권고 |
|----|------|------|------|
| **G1** | v11은 Pipeline A를 단일 문서로 기술하나, 04.graphrag는 Phase 3에서 JD 파서/CompanyContext/Organization ER을 3주에 걸쳐 구현 | 구현 시 v11과 04.graphrag를 동시에 참조해야 함 | v11에 Phase 매핑 추가 |
| **G2** | v11의 검증 체크포인트(CP1~CP6)가 04.graphrag 실행 계획의 어느 Week에 구현되는지 미정 | CP 구현이 누락될 수 있음 | 04.graphrag에 CP 구현 일정 명시 |
| **G3** | v11의 매칭 필드 매핑 테이블(§6)이 04.graphrag Phase 3 매칭 알고리즘 설계와 연결되는 시점 불명확 | 매칭 설계 시 v11 §6 참조 누락 가능 | Phase 3-0 설계 문서에 v11 §6 참조 명시 |

### 3.3 실행 순서 리스크

v11은 추출 로직을 A/B/B'/C 순서로 기술하지만, 04.graphrag는 **B(Phase 1) → B'(Phase 2) → A(Phase 3) → C(전 Phase)** 순서로 구현한다.

이 순서 차이 자체는 문제가 아니나, **v11 문서를 처음 읽는 개발자가 A부터 구현하려 할 수 있음**. v11 §1.3에 **구현 순서는 04.graphrag를 따른다는 명시적 안내**가 필요.

---

## 4. 인력 실현 가능성

v11 자체는 인력 계획을 포함하지 않으나 (04.graphrag에 위임), 추출 로직의 복잡도에서 인력 관련 우려 사항:

| 우려 | 이유 |
|------|------|
| **프롬프트 엔지니어링 전문성** | 03_prompt_design의 Few-shot 설계, Ambiguity Rules, Taxonomy Enforcement 등은 LLM 프롬프트 경험이 있는 MLE가 필요 |
| **PII 마스킹 법적 검증** | 04_pii_and_validation의 법률 검토 연동은 법무팀 일정에 의존 |
| **Neo4j 전문성** | UNWIND 배치 적재, 공유 노드 보호 등 Neo4j 고급 패턴은 학습 곡선 있음 |

---

## 5. 종합 판정

| 항목 | 점수 | 비고 |
|------|------|------|
| 비용 현실성 | 8/10 | Haiku 품질 미달 시 비용 5.5배 증가 리스크 |
| 전제 조건 충족 | 6/10 | DB 접근, Haiku 품질, BRN 비율 모두 미검증 |
| 04.graphrag 정합 | 7/10 | 관계명 불일치, 구현 순서 안내 부재 |
| 기술 난이도 | 7/10 | 프롬프트, PII, Neo4j 전문성 필요 |
| **종합** | **7/10** | v10(6/10) 대비 개선, 전제 조건 검증이 관건 |
