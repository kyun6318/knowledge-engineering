# GraphRAG light.1 실행 계획 리뷰

> **리뷰 대상**: light.1 Staged Fast Fail 계획 (6개 문서)
> **리뷰 초점**: 실현 가능성, 과도한 일정/기능, 부족한 일정/기능
> **리뷰 일자**: 2026-03-08

---

## 1. 총평

light.1 계획은 standard.1(26~33주)를 13~15주로 약 50% 압축하면서도 핵심 검증 사이클을 보존하려는 균형 잡힌 시도다. Fast Fail 전략의 부적합성 분석(00_fast_fail_analysis.md)은 논리적으로 탄탄하며, "빨리 검증한다"는 철학은 올바르다. 그러나 일부 단계에서 **낙관적 가정**이 과도하고, 반대로 일부 영역은 **필요 이상으로 상세하여** 핵심 리스크에 대한 집중도가 흐려지는 부분이 있다.

**전체 실현 가능성 판정: 조건부 가능 (60~70%)**

---

## 2. 실현 가능성 분석

### 2.1 높은 실현 가능성 (Green)

| 항목 | 근거 |
|------|------|
| Phase 0 병렬 구조 (0-A/B/C/D) | DE와 MLE의 역할이 명확히 분리되어 있고, 입력 데이터가 겹치지 않음. 2.5주 병렬 실행은 현실적 |
| Fast Fail 부적합 분석 | 5가지 근거가 데이터/KG 프로젝트의 본질적 특성을 정확히 짚음. 의사결정의 질을 담보하는 좋은 프레임워크 |
| 크롤링 후속 프로젝트 분리 | 스코프 축소의 가장 효과적인 결정. 크롤링은 KG 코어와 독립적이므로 분리가 타당 |
| Phase 0 Go/No-Go 게이트 | 6개 의사결정 항목이 명확하고, 미달 시 대응책이 구체적. 프로젝트 리스크 관리의 핵심 |
| Checkpoint/재시작 전략 (standard.1-5) | BigQuery processing_log + batch_tracking 기반 재시작은 450K 규모에서 필수적이며 설계가 적절 |
| Makefile → Cloud Workflows 전환 | Phase 1 소규모에서 Makefile, Phase 2 대규모에서 Workflows 전환은 합리적 단계적 접근 |

### 2.2 중간 실현 가능성 (Yellow) — 주의 필요

| 항목 | 우려 | 권장 |
|------|------|------|
| **Phase 1-A 병행 (2주)** | 전처리(DE)와 CompanyContext(MLE)를 2주 병행한다고 하나, 인터페이스 합의·통합 테스트까지 포함하면 2주는 빠듯. JSON 스키마 합의에 의외로 시간이 소요될 수 있음 | 통합 테스트를 0.5주 추가 버퍼로 확보 |
| **Phase 1-B CandidateContext 3주** | 10개 모듈(1-B-1~B-10) 구현을 2주에 완료해야 함. MLE 혼자 B-1~B-7(7개 모듈)을 2주에 끝내야 하는 구조 | MLE 부하가 집중됨. 일부 Rule 추출(B-2)을 DE에게 위임하거나 우선순위 조정 필요 |
| **2인 풀타임 가용성** | 전체 13~15주 동안 DE/MLE 2인 100% 풀타임이 전제. 실제로는 회의, 다른 프로젝트, 장애 대응 등으로 70~80% 가용이 현실적 | 가용률 80%를 적용하면 실질 16~19주. 명시적으로 "80% 가용률 시 16~19주" 시나리오 추가 권장 |
| **Neo4j AuraDB Free → Professional 전환** | 2-0에서 1일이면 전환 가능하다고 하나, Professional 인스턴스 프로비저닝 + 데이터 import + 검증에 예상외 이슈 발생 가능 (특히 APOC export/import 호환성) | 전환을 Phase 1 마지막 주(Week 9~10)에 시작하여 Phase 2 시작 전 여유 확보 |

### 2.3 낮은 실현 가능성 (Red) — 심각한 우려

| 항목 | 우려 | 영향 | 권장 |
|------|------|------|------|
| **Phase 1-C: Graph+Embedding+Mapping 1주** | standard.1의 4주를 1주로 압축. "MVP 1,000건이므로 충분"이라는 근거이나, 실행 시간이 아니라 **모듈 개발 시간**이 문제. 1-C-3(Org ER), 1-C-7(MappingFeatures 계산), 1-C-11(Idempotency 테스트), 1-C-12(E2E 통합 테스트)를 1주에 완료하는 것은 비현실적 | Phase 1 전체 일정 1~2주 지연 | **1-C를 2주로 확대** 권장. 특히 Org ER 알고리즘은 한국어 회사명 변형 패턴이 복잡하여 1일로는 부족 |
| **Phase 1-D: 테스트+검증+백업 0.5~1주** | 1-D-1~D-6에서 pytest 프레임워크 구축, regression test 작성, 통합 테스트까지 0.5~1주. 테스트 코드 작성은 구현 코드만큼 시간이 소요됨. Golden 50건 수동 검증도 포함 | 테스트 품질 저하 또는 일정 지연 | **1주를 최소로 확정** (0.5주 옵션 제거). 가능하면 1.5주 확보 |
| **Phase 2: 4~5주에 전체 450K 처리 완료** | Batch API 물리적 대기 ~11일 + 실패 재시도 ~2일 + 결과 수집 ~2일 + Graph 적재 ~3일 + 버퍼 ~3일 = 21~28일. 그러나 이 계산에 **Phase 2-B 품질 평가 결과에 따른 프롬프트 수정 → 재처리** 시나리오가 반영되지 않음 | 품질 미달 시 Phase 2가 6~8주로 연장 | 품질 미달 시나리오를 명시적 타임라인으로 추가. "Phase 2: 4~5주 (정상) / 6~8주 (프롬프트 수정 1회)" |
| **Pre-Phase 0 Blocking Dependencies** | 법무 PII 검토(1~3주) + Batch API quota 확인(1~2주)이 Phase 0 시작 2~3주 전에 완료되어야 함. 이 기간이 타임라인에 포함되지 않음 | 실질적으로 Pre-Phase 0에 2~3주 추가 → 전체 15~18주 | Pre-Phase 0 기간을 전체 타임라인에 명시적으로 포함 |

---

## 3. 과도한 일정/기능 (Over-scoped)

### 3.1 Phase 0 API 검증 범위가 여전히 넓음

**문제**: Phase 0-A에서 Document AI OCR, Layout Parser, Gemini 멀티모달, NER 등 다수의 API를 3일 안에 검증한다. 이 중 **Document AI는 HWP를 직접 지원하지 않으며**, 이력서가 주로 PDF/DOCX/HWP인 점을 감안하면 Document AI의 가치가 제한적이다.

**권장**:
- Document AI 검증을 **선택적(nice-to-have)**으로 격하
- HWP 파싱 PoC(0-C-7)에 더 집중
- API 검증을 2일로 축소 가능

### 3.2 Gold Test Set 200건 + Silver Label이 Phase 2 초반에 과부하

**문제**: 2-B에서 "전문가 2인 × 100건" Gold Test Set을 1주 안에 구축한다. 전문가 라벨링은 1건당 15~30분이 소요되어, 100건 × 20분 = 33시간/인. 2인이 병렬로 해도 순수 라벨링만 4일. Cohen's κ 검증, Power analysis, 리포트 작성까지 1주는 매우 빡빡하다.

**권장**:
- Gold Test Set을 **Phase 1 후반(Week 8~9)**부터 병행 시작 (도메인 전문가가 Phase 1 결과물로 라벨링)
- Phase 2-B에서는 이미 구축된 Gold Set으로 **평가만** 실행 (1주 → 0.5주 가능)

### 3.3 Cloud Workflows YAML이 Phase 2 범위에서 과도

**문제**: 04_phase2_full_processing.md에 Cloud Workflows YAML이 상세하게 작성되어 있으나, Phase 2에서 실제로 Cloud Workflows를 full 구현할 필요성이 낮다. Phase 2는 본질적으로 "Phase 1 파이프라인을 대규모로 반복 실행"하는 것이므로, Makefile + 스크립트로도 충분히 운영 가능하다.

**권장**:
- Phase 2에서도 **Makefile + 모니터링 스크립트**로 운영
- Cloud Workflows는 **후속 프로젝트(증분 처리 자동화)**에서 도입
- 이 결정으로 Phase 2에서 0.5~1주 절약 가능

### 3.4 비용 추정의 과도한 정밀도

**문제**: 05_cost_monitoring.md에서 Embedding Egress 비용을 $0.18 → $0.86 → $3.6 수준으로 계산하고 있으나, 전체 예산 $4,943 대비 무의미한 수준. 이런 세부 계산에 시간을 쓰기보다 **LLM 비용 변동 리스크**에 더 집중해야 한다.

**권장**:
- Egress 비용 계산 삭제
- 대신 "Anthropic 가격 변동 리스크" (현재 Haiku Batch $0.40/1M input 기준, 가격 변경 시 영향) 분석 추가

---

## 4. 부족한 일정/기능 (Under-scoped)

### 4.1 [Critical] Organization Entity Resolution에 대한 과소 평가

**문제**: 1-C-3에서 Org ER을 **1일**로 잡고 있다. 그러나 한국어 회사명 ER은 매우 복잡한 문제다:
- "삼성전자(주)" / "Samsung Electronics" / "삼성전자 DS부문" / "삼성전자 반도체" → 동일 회사?
- "삼성" → 삼성전자? 삼성물산? 삼성SDS?
- "현대자동차" / "현대차" / "HMC" / "Hyundai Motor"
- 합병/분할: "SK하이닉스" (구 하이닉스반도체)

ER 알고리즘 설계문서에서 "Jaro-Winkler threshold ≥ 0.85"로 제시하고 있으나, 한국어에서 이 threshold의 적절성은 검증이 필요하다. 1-D에도 "Organization ER 알고리즘 설계+구현 (개발 시간)"이 포함되어 있어 1-C-3과 중복/혼란이 있다.

**권장**:
- Org ER을 **별도 2~3일 태스크**로 격상
- Phase 0-B 프로파일링에서 **회사명 변형 패턴 Top-50**을 반드시 추출
- 1-C와 1-D의 Org ER 관련 태스크를 통합 정리

### 4.2 [Critical] Batch API 24시간 SLA 초과 시 대응 미비

**문제**: Phase 1-B-12에서 "24시간 SLA 대기"를 전제로 하고 있으나, Anthropic Batch API의 실제 응답 시간은 **부하에 따라 변동**된다. 24시간을 초과하거나, 일부 요청이 실패하여 재제출이 필요한 경우에 대한 대응이 부족하다.

Phase 2에서는 더 심각하다. "450 chunks / 10 동시 = 45 라운드 × 6시간 = ~11일"로 계산하나, 6시간은 **평균**이며 최악의 경우 24시간. 최악 시 45 라운드 × 24시간 = 45일.

**권장**:
- Batch API 응답 시간 분포를 Phase 0에서 **5~10건 실측**
- Phase 2 타임라인에 "낙관(6h) / 기본(12h) / 비관(24h)" 3-시나리오 제시
- "동시 10 batch"가 quota에서 허용되지 않을 경우의 타임라인 수정안 사전 준비

### 4.3 [Important] 프롬프트 엔지니어링 시간 과소 평가

**문제**: CandidateContext 추출 프롬프트가 계획의 핵심인데, 프롬프트 튜닝에 할당된 명시적 시간이 없다. Phase 0-C에서 50건 PoC로 "프롬프트 3~5회 튜닝 반복"을 언급하지만, 실제로는:
- Experience 추출 프롬프트
- Career-level 추출 프롬프트
- WorkStyleSignals 프롬프트
- CompanyContext vacancy_role 프롬프트

최소 4개 프롬프트를 각각 3~5회 반복해야 하며, 이는 **15~20회 LLM 호출 라운드**를 의미한다. 각 라운드마다 결과 검토 + 프롬프트 수정이 필요하다.

**권장**:
- Phase 1-B에 **프롬프트 튜닝 전용 0.5주** 명시적 할당
- 또는 Phase 0-C를 1.5주 → 2주로 확장하여 프롬프트 안정화 시간 확보

### 4.4 [Important] HWP 파싱의 실제 비중 미확인

**문제**: Phase 0-B-1에서 "파일 형식 분포 (PDF/DOCX/HWP)" 확인을 계획하고 있으나, HWP 비중에 따라 Phase 1의 아키텍처가 크게 달라진다:
- HWP < 5%: LibreOffice fallback으로 충분, Docker 이미지 경량 유지 가능
- HWP 20~40%: LibreOffice가 Docker 이미지를 ~1GB 이상 증가시킴. Cloud Run cold start 영향
- HWP > 40%: 전용 파싱 서비스 분리 검토 필요

**권장**:
- Phase 0-B-1 결과를 Phase 1 아키텍처 결정의 **blocking input**으로 명시
- Docker 이미지에 LibreOffice 포함 시 이미지 크기/cold start 영향 추정 추가

### 4.5 [Important] 데이터 전송 시간 (150GB GCS 업로드)

**문제**: 0-A-3에서 "이력서 원본 GCS 업로드 시작 (백그라운드)"로 150GB 업로드를 계획하나, 네트워크 속도에 따라:
- 100Mbps: ~3.3시간
- 50Mbps: ~6.7시간
- 사내 방화벽/프록시 경유 시: 수 일

업로드가 완료되지 않으면 Phase 0-B 프로파일링이 불가능하다.

**권장**:
- Pre-Phase 0에 **데이터 전송 테스트 (10GB 샘플)**를 추가
- 업로드 속도 실측 후 전체 전송 소요 시간을 Phase 0 타임라인에 반영
- Transfer Appliance 또는 gcloud storage rsync --parallel 옵션 검토

### 4.6 [Moderate] Dead-letter 재처리 전략 미흡

**문제**: 2-A-4에서 "Dead-letter 재처리 (1회)"로 간단히 처리하나, 450K 건에서 실패율 3~5%면 13,500~22,500건이 dead-letter에 쌓인다. 이 규모의 재처리는 단순 "1회 수동 재시도"로 해결되지 않으며, 실패 원인별 분류 → 프롬프트 수정 → 재처리 → 재검증 사이클이 필요하다.

**권장**:
- Dead-letter 재처리를 **별도 0.5주 태스크**로 격상
- 실패 원인별 분류 로직 (rate limit / timeout / safety filter / JSON parse 실패 등) 추가
- Phase 2 타임라인에 dead-letter 재처리 기간 반영

### 4.7 [Moderate] Embedding 모델 선택의 리전 제약

**문제**: Vertex AI Embedding을 `us-central1`에서 사용하고, 데이터는 `asia-northeast3`(서울)에 있다. Egress 비용보다 더 큰 문제는 **450K × 5.2 chapters = 2.34M 건의 Embedding 요청**에 대한 Vertex AI rate limit이다. Embedding API의 QPM(Queries Per Minute) 제한이 계획에 반영되어 있지 않다.

**권장**:
- Phase 0에서 Vertex AI Embedding API의 **QPM/TPM 한도** 확인 및 기록
- Phase 2 Embedding 생성 시간을 QPM 기반으로 재추정
- 필요 시 quota 증가 요청을 Pre-Phase 0에 추가

### 4.8 [Moderate] 도메인 전문가 파트타임의 구체적 시간 미명시

**문제**: "도메인 전문가 1명 파트타임"으로만 기술되어 있으나, 도메인 전문가가 필요한 시점이 구체적이지 않다:
- Phase 0: PoC 50건 품질 검증
- Phase 1: Golden 50건 라벨링
- Phase 2: Gold Test Set 200건 라벨링 (전문가 2인 × 100건)

특히 Phase 2에서 "전문가 2인"이 갑자기 필요해지는데, 1인은 어디서 오는가?

**권장**:
- 도메인 전문가의 **주차별 투입 시간**을 명시 (예: Phase 0 Week 2: 8시간, Phase 2 Week 10~11: 전문가 A 20시간 + 전문가 B 20시간)
- Phase 2 전문가 2인 확보를 **Pre-Phase 2 blocking dependency**에 추가

---

## 5. 일정 조정 권장안

### 5.1 현재 계획 vs 권장 조정

| Phase | 현재 계획 | 권장 조정 | 차이 | 사유 |
|-------|----------|----------|------|------|
| Pre-Phase 0 | (미포함) | **2~3주** | +2~3주 | 법무 PII + Batch API quota + 데이터 전송 테스트 |
| Phase 0 | 2.5주 | **2.5주** | 0 | 적정 |
| Phase 1-A | 2주 | **2.5주** | +0.5주 | 통합 테스트 버퍼 |
| Phase 1-B | 3주 | **3.5주** | +0.5주 | 프롬프트 튜닝 시간 |
| Phase 1-C | 1주 | **2주** | +1주 | Org ER + 모듈 개발 시간 |
| Phase 1-D | 0.5~1주 | **1주** | 0~+0.5주 | 테스트 최소 1주 확정 |
| Phase 2 | 4~5주 | **5~6주** | +1주 | Dead-letter 재처리 + 품질 미달 버퍼 |
| **코어 합계** | **13~15주** | **16.5~18.5주** | +3~3.5주 | |
| **Pre-Phase 포함** | **13~15주** | **18.5~21.5주** | +5.5~6.5주 | |

### 5.2 최적화 가능 영역 (조정안에서 다시 줄이기)

| 영역 | 절감 | 방법 |
|------|------|------|
| Cloud Workflows 제거 | -0.5주 | Phase 2도 Makefile + 스크립트로 운영 |
| Document AI 검증 축소 | -0.5일 | HWP 중심으로 전환 |
| Gold Test Set 선행 시작 | -0.5주 | Phase 1 후반부터 라벨링 시작 |
| **절감 합계** | **-1~1.5주** | |

### 5.3 최종 권장 타임라인

```
Pre-Phase 0: 2~3주 (법무/quota/데이터 전송 — 병렬 진행)
Phase 0: 2.5주 (현행 유지)
Phase 1: 8~9주 (현행 6.5~7주 + 2주 버퍼)
Phase 2: 5~6주 (현행 4~5주 + 1주 버퍼)

코어 기간: 15.5~17.5주
Pre-Phase 포함: 17.5~20.5주
첫 MVP 데모: ~12~13주 (Pre-Phase 포함 ~14~16주)
```

---

## 6. 비용 관련 리뷰

### 6.1 적정한 부분

- 한국어 토큰 보정(×1.88)은 현실적이고 중요한 보정
- Phase별 Budget Alert 설정은 실용적
- 시나리오별 비용 비교(A/A'/B/D)는 의사결정에 유용

### 6.2 우려 사항

| 항목 | 우려 | 영향 |
|------|------|------|
| **Gold Label 인건비 $2,920** | 전체 예산의 59%. 이 비용의 산출 근거가 문서에 없음 (200건 × 단가?) | 예산 정당성 검증 불가 |
| **프롬프트 최적화 LLM $300** | 250건으로 추정하나, 실제 프롬프트 튜닝은 반복적이어서 500~1,000건이 될 수 있음 | +$300~600 추가 가능 |
| **Neo4j Professional $65~200/월** | 레인지가 3배. 실제 필요 사양이 Phase 0-B-8의 노드 수 추정에 의존하는데, 이 추정 자체가 불확실 | 예산 불확실성 |
| **Anthropic 가격 변동 리스크** | Batch API 50% 할인이 프로모션일 경우, 프로젝트 진행 중 가격 변경 가능 | LLM 비용 2배 증가 가능 |

### 6.3 권장

- Gold Label 인건비 산출 근거 명시 (단가 × 건수 × 시간)
- Anthropic Batch API 가격 정책 확인 (영구 할인 vs 프로모션)
- 총 예산에 **20% contingency ($1,000)** 추가 → 총 ~$6,000

---

## 7. 기술적 리스크 추가 식별

### 7.1 계획에 누락된 리스크

| 리스크 | 영향 | 발생 확률 | 권장 대응 |
|--------|------|----------|----------|
| **Anthropic Batch API 서비스 중단/변경** | Phase 2 전체 중단 | 낮 | Gemini Flash Batch 대체 경로 사전 검증 |
| **Neo4j AuraDB Free에서 APOC 미지원** | 백업 불가, Phase 1-D 일정 차질 | 중 | 0-D-2a에서 즉시 확인 (계획에 포함됨, Good) |
| **Cloud Run Job 24시간 timeout 초과** | kg-batch-submit Job 실패 | 중 | Job을 polling + 재시작 방식으로 분리 |
| **pyhwp HWPX 미지원** | HWP 파싱 fallback 필요 | 높 | 계획에 포함됨 (R-5), 다만 HWPX 비율이 높으면 LibreOffice만 남음 |
| **Vertex AI Embedding 리전 제약 변경** | Embedding 파이프라인 수정 | 낮 | 리전 변경 시 코드 수정 최소화되도록 config 분리 |
| **BigQuery insert_rows_json 429 에러** | Checkpoint 기록 실패 → 중복 처리 | 중 | Exponential backoff + streaming insert 대신 load job 검토 |

### 7.2 APOC export 관련 추가 우려

AuraDB Free에서 `apoc.export.json.all`이 동작하는지는 0-D-2a에서 확인하지만, **AuraDB Professional로 전환 시 APOC import가 동작하는지**도 확인 필요. `apoc.import.json` 지원 여부 + Professional 인스턴스에서의 파일 접근 권한을 사전 검증해야 한다.

---

## 8. 문서 품질 리뷰

### 8.1 우수한 점

- standard.1 → light.1 변경 사항 추적이 체계적 (standard.2, light.1-P1-1 등 태그)
- Go/No-Go 게이트가 Phase 0과 Phase 1 모두에 명시
- 코드 예시가 실제 구현 수준으로 상세 (llm_parser.py, batch_submit.py 등)
- 위험 요소별 standard.1 연계 항목이 명확

### 8.2 개선 필요

| 문서 | 이슈 | 권장 |
|------|------|------|
| 01_overview.md | Phase 0 비용 $83 vs 05_cost.md $83 일치하지만, Phase 1 비용이 overview에서 $42, cost에서 $42로 표기되나 Phase 1 기간이 overview "6.5~7주" vs cost "5~6주"로 불일치 | Phase 1 기간 통일 |
| 03_phase1.md | 1-C-3 Org ER과 1-D의 Org ER이 중복 기술 | 1-C-3은 "구현", 1-D는 "테스트"로 역할 구분 명확화 |
| 04_phase2.md | Cloud Workflows YAML에 `kg-candidate-graph` Job이 등장하나, Phase 1에서 정의한 Job은 `kg-graph-load` | Job 이름 통일 |
| 05_cost.md | 원화 환산 기준 환율 미명시 ($4,943 → 677만원이면 $1 ≈ 1,370원?) | 환율 가정 명시 |

---

## 9. 결론 및 핵심 권장사항 (Top 5)

| 우선순위 | 권장사항 | 영향 |
|----------|---------|------|
| **1** | Pre-Phase 0 기간(2~3주)을 전체 타임라인에 명시적으로 포함 | 일정 현실성 확보 |
| **2** | Phase 1-C(Graph+Embedding+Mapping)를 1주 → 2주로 확대 (Org ER, 모듈 개발 시간 반영) | Phase 1 성공률 향상 |
| **3** | 인력 가용률 80% 시나리오를 기본 타임라인으로 채택 (현재 100% 가정) | 일정 신뢰도 향상 |
| **4** | Batch API 응답 시간 3-시나리오(낙관/기본/비관)를 Phase 2 타임라인에 반영 | Phase 2 리스크 가시화 |
| **5** | Cloud Workflows를 후속 프로젝트로 미루고, Phase 2도 Makefile 기반으로 운영 | 0.5~1주 절약 + 복잡도 감소 |

---

> **최종 판정**: light.1 계획은 standard.1 대비 **올바른 방향의 압축**이나, 현재 13~15주 추정은 **낙관적**이다.
> Pre-Phase 0 포함 시 **17~20주**가 현실적 범위이며, 이를 명시적으로 타임라인에 반영해야 이해관계자의 기대를 올바르게 관리할 수 있다.
> 핵심 강점인 "Staged Fast Fail" 철학과 Go/No-Go 게이트는 그대로 유지하되, 개발 시간 추정의 정밀도를 높이는 것이 필요하다.
