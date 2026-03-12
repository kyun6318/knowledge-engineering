# 가상 정보, 리스크, 완화 전략

> 이 계획에서 가정한 정보와 리스크를 명시적으로 정리한다.
> 각 가정이 잘못되었을 때의 영향과 대응 방안을 포함한다.
>
> 작성일: 2026-03-08 (v2 기반)
> 개정일: 2026-03-08 (v4 — PII 마스킹 영향, embedding 검증 리스크 추가)

---

## 1. 가상으로 설정한 정보 (Assumptions)

### 1.1 데이터 볼륨 관련

| ID | 가정 | 가정값 | 영향 범위 | 잘못되면 |
|---|---|---|---|---|
| **A1** | JD 보유량 | 10,000건 | CompanyContext 생성 비용 | 1,000건이면 비용 1/10, 100,000건이면 비용 10배 |
| **A2** | 이력서 보유량 | 500,000건 (150GB ÷ 300KB) | **전체 비용의 핵심 드라이버** | 100K건이면 비용 1/5, 1M건이면 비용 2배 |
| **A3** | 이력서 평균 크기 | 300KB | A2 산출 근거 | 100KB이면 이력서 150만건, 1MB이면 15만건 |
| **A4** | 이력서당 평균 경력 수 | 3건 | LLM 호출 횟수/비용 | 5건이면 LLM 비용 67% 증가 |
| **A9** | 매핑 대상 쌍 수 | 500만 (JD × 상위 500) | MappingFeatures 비용/인프라 | 비용 영향 작음 (계산이 저렴) |

### 1.2 데이터 품질 관련

| ID | 가정 | 가정값 | 영향 범위 | 잘못되면 |
|---|---|---|---|---|
| **A5** | NICE 매칭률 | 60% | PastCompanyContext 커버리지 | 30%이면 stage_match 피처 대부분 INACTIVE |
| **A7** | Rule 추출 성공률 (날짜/회사명) | 70% | 전처리 비용, LLM 입력 품질 | 40%이면 LLM에 더 많은 컨텍스트 필요 |
| **A11** | 파일 형식 분포 | PDF 70%, DOCX 20%, HWP 10% | 파싱 파이프라인 구축 난이도 | HWP 40%이면 파싱 난이도 대폭 증가 |
| **A12** | OCR 필요 비율 | 5% 미만 | 전처리 비용/품질 | 20%이면 Rule 커버리지 급감, LayoutLM 필요 |

### 1.3 모델 성능 관련

| ID | 가정 | 가정값 | 영향 범위 | 잘못되면 |
|---|---|---|---|---|
| **A6** | LLM 추출 토큰 사용량 | Exp: 3,000 tok, Career: 2,500 tok | 비용 산출의 핵심 | 2배이면 LLM 비용 2배 |
| **A8** | Haiku 한국어 추출 품질 | Sonnet의 85% | 모델 선택 결정 | 70% 이하이면 Sonnet 필수 → 비용 5배 |
| **A16** | Embedding 모델 한국어 분별력 | text-embedding-3-small 기준 "양호" | 도메인 매칭 정확도 | "양호" 이하이면 Cohere multilingual 또는 BGE-M3 전환, domain_fit 피처 품질 하락 |

### 1.4 비즈니스/법적 관련

| ID | 가정 | 가정값 | 영향 범위 | 잘못되면 |
|---|---|---|---|---|
| **A10** | PII 외부 전송 가능 | 마스킹 후 가능 | **전체 아키텍처** | 불가 시 On-premise → 비용 14배, 일정 2배 |
| **A14** | Neo4j Professional 용량 | 800K 노드 $100/월 | 인프라 비용 | 더 큰 플랜 필요 시 $200-500/월 |
| **A15** | Batch API 응답 시간 | 24시간 이내 | 전체 처리 일정 | 지연 시 일정에 영향 |

---

## 2. 리스크 분석

### 2.1 [Critical] PII 개인정보 처리 — 전체 아키텍처 결정

**리스크**: 이력서를 외부 LLM API로 전송 시 개인정보보호법 위반 가능

**영향**: 시나리오 A(API, ~1,234만 원) ↔ 시나리오 C(On-premise, ~2,333만 원)의 약 2배 비용 차이

**현실적 옵션 분석**:

| 옵션 | 비용 | 품질 | 일정 | 비고 |
|---|---|---|---|---|
| **마스킹 후 API 전송** | 가장 저렴 | 최고 (Haiku/Sonnet) | 빠름 | 법무 승인 필수, 마스킹 품질이 관건 |
| **동의 기반 API 전송** | 저렴 | 최고 | 빠름 | 500K건 전체 동의 확보 현실적으로 불가 |
| **On-premise SLM** | 14배 비용 | Haiku 대비 낮음 | 느림 | EXAONE 7.8B 기준 |
| **Azure/AWS Private Endpoint** | API비용 + $500~2,000/월 | API 수준 | 중간 | Azure OpenAI: Private Endpoint $500~1,000/월 추정, Anthropic: Enterprise 계약 별도 문의 필요 |

**권장 대응**:
1. Phase 0에서 법무팀과 PII 마스킹 전략 확정
2. 마스킹 수준: 이름 → [NAME], 연락처 → [PHONE], 주소 → [ADDR] 치환
3. 마스킹 후 추출 결과에서 역매핑 (span offset 보존)
4. 법무 불가 판정 시 → Azure OpenAI Private Endpoint 또는 On-premise 전환

### 2.2 [Critical] LLM 추출 품질 — 시스템 실현 가능성

**리스크**: v4가 요구하는 추출(outcomes, situational_signals)의 LLM 정확도가 기대 이하

**영향**: MappingFeatures의 핵심 피처(vacancy_fit, stage_match)가 무의미해질 수 있음

**완화 전략**:

```
Phase 0 PoC에서 검증할 핵심 질문:
1. situational_signals 14개 taxonomy 분류 정확도 → 50% 미만이면 taxonomy 축소
2. outcomes 추출 시 quantitative vs qualitative 판별 정확도
3. scope_type 분류 정확도 → 70% 미만이면 ML Distillation 우선 투자

추출 품질이 낮을 때의 대안:
- taxonomy 축소: 14개 → 6개 상위 카테고리로 (성장/조직/기술/비즈니스/기타)
- 2-pass 추출: 1차 추출 → 자기 검증 → 2차 보정 (비용 2배, 정확도 향상)
- Human-in-the-loop: 낮은 confidence 건만 전문가 검수 (비용 증가)
```

### 2.3 [Critical] 파싱 품질 + LLM 품질 상관 리스크

> **v3 신설**: v2 리뷰에서 지적된 P1+P3 상관 리스크.

**리스크**: 이력서 파싱 품질(P3)이 낮으면 LLM 입력 품질도 낮아져 추출 정확도(P1)가 연쇄 하락. 이 두 리스크는 독립적이 아닌 **상관 리스크**다.

**특히 위험한 케이스**:
- 표 기반 이력서: 셀 경계가 깨져 텍스트 순서 뒤섞임
- 2단 레이아웃: 좌우 컬럼이 섞임
- 한글(HWP) 파일: python-hwp 라이브러리 성숙도 낮음
- 이미지 기반 PDF: OCR 없이는 텍스트 추출 불가

**완화 전략**:
- Phase 0에서 파일 형식 분포 + 파싱 품질 사전 평가
- 표/2단 레이아웃 → pdfplumber (표 추출) + layout analysis
- HWP → LibreOffice headless 변환 → DOCX/PDF로 우회
- OCR 비율 높으면 → DocTR / EasyOCR 도입
- **최악의 경우**: 파싱이 안 되는 이력서는 LLM에 원본 텍스트 직접 전달 (비용 증가 감수)
- **Phase 0 PoC에서 파싱+추출 통합 품질 측정** (별도가 아닌 연쇄 측정)

### 2.4 [High] NICE 데이터 매칭률

**리스크**: 이력서 내 회사명 → NICE DB 매칭이 기대(60%)보다 낮을 수 있음

**영향**: PastCompanyContext가 생성되지 않으면 stage_match 피처가 INACTIVE

**매칭 실패 예상 케이스**:
- 스타트업/소규모 기업: NICE에 등록되지 않은 경우
- 해외 기업: NICE는 국내 기업 중심
- 회사명 변형: "카카오" vs "주식회사 카카오" vs "카카오엔터프라이즈"
- 인수합병: 과거 회사명으로 기재

**완화 전략**:
- 회사명 정규화 사전 구축 (alias dictionary)
- NICE 매칭 실패 시 → `past_company_context = null` (graceful degradation)
- v1.1에서 투자 DB 연동으로 스타트업 커버리지 보강

### 2.5 [High] Confidence 캘리브레이션

**리스크**: LLM 자가 평가 confidence 값이 실제 정확도와 상관없을 수 있음

**영향**: MappingFeatures의 confidence 가중 스코어가 왜곡됨

**완화 전략**:
- Phase 2에서 gold set 기반 confidence 실측
- 캘리브레이션 함수 적용: `calibrated = sigmoid(a * raw + b)` (Platt Scaling)
- 필요 시 LLM confidence 대신 **출력 일관성 기반 confidence** 도입
  - 동일 입력 2~3회 추출 → 일치율을 confidence로 사용 (Batch API 할인 적용 시 비용 1.0~1.5배, 신뢰도 향상)
    - 2회: majority vote 불가하나 일치/불일치 판정은 가능, 비용 효율적
    - 3회: majority vote 가능, Batch API 50% 할인 적용 시 비용 1.5배

### 2.6 [High] LLM API Rate Limit

> **v3 신설**: v2 리뷰에서 지적된 새 리스크.

**리스크**: 500K 이력서를 Batch API로 처리할 때 API 제공사의 rate limit/quota에 걸릴 수 있음

**Anthropic Batch API 제한 (2026-03 기준)**:
- 동시 배치: 계정 tier에 따라 제한 (기본 10개)
- 배치당 최대 요청: 10,000건
- 24시간 SLA (보장은 아님, best-effort)

**완화 전략**:
- Phase 0에서 소규모 Batch API 테스트로 실제 처리 속도/제한 확인
- 1,000건/chunk 단위로 분할하여 순차 제출
- 여러 API 제공사 분산 (Haiku + Flash) 검토
- Enterprise 계약 시 quota 확대 협의

### 2.7 [High] LLM 모델 버전 변경 리스크

> **v3 신설**: v2 리뷰에서 지적된 새 리스크.

**리스크**: Haiku 4.5가 deprecated 되거나 동작이 변경되면 추출 결과 일관성 깨짐

**영향**: 동일 프롬프트에서 다른 추출 결과 → Graph 데이터 불일치

**완화 전략 (Model Pinning)**:
- API 호출 시 **정확한 모델 버전 명시** (e.g., `claude-haiku-4-5-20251001`, snapshot ID 사용)
- 모델 변경 시 **50건 회귀 테스트** 실행 후 전환
- Context JSON에 `model_version` 메타데이터 기록
- 모델 deprecated 공지 시 최소 2주 전환 기간 확보

### 2.8 [High] 증분 처리 / 데이터 갱신 전략

> **v3 신설**: v2 리뷰에서 지적된 운영 리스크.

**리스크**: 최초 500K 처리 후 신규 이력서 유입, 기존 이력서 갱신, 프롬프트 변경 시 재처리 전략이 없으면 Graph 데이터가 부정확해짐

**영향**: 운영 단계에서 데이터 신선도 저하 → 매칭 품질 하락

**완화 전략**: `04_execution_plan.md`의 "운영 전략: 롤백 / 재처리 / 증분 처리" 섹션 참조

### 2.9 [Medium] Graph DB 스케일링

**리스크**: 500K 이력서 → ~800만 노드, ~2,500만 엣지 시 Neo4j 성능/비용 문제

**완화 전략**:
- Phase 1에서 1,000건으로 시작 → AuraDB Free (200K 노드)로 충분
- Phase 2 확장 시 Professional 전환
- 풀 스케일 시 Neo4j Enterprise 또는 NebulaGraph 검토

### 2.10 [Medium] Entity Resolution — 회사명/기술명 정규화

**리스크**: "네이버" / "NAVER" / "(주)네이버" / "네이버 파이낸셜" 등 변형 처리

**완화 전략**:
- KOSPI/KOSDAQ + 주요 스타트업 canonical 사전 (1,000개) 선구축
- Skill 정규화 사전 (2,000개 기술명 + alias)
- 매칭 실패 시 BGE-M3 embedding + cosine similarity 0.85 이상이면 동일 엔티티 판정
- 타입별 독립 처리 (Skill, Organization, Role 분리)

### 2.11 [Medium] v4 MappingFeatures 활성화 비율

**리스크**: v4 온톨로지에서 예고한 대로 culture_fit은 대부분 INACTIVE, stage_match도 NICE 매칭 실패 시 INACTIVE

**예상 활성화 비율**:

| 피처 | 예상 ACTIVE 비율 | 주요 비활성 원인 |
|---|---|---|
| stage_match | 40-60% | NICE 매칭 실패 → past_company_context null (아래 근거 참조) |
| vacancy_fit | 60-80% | situational_signals 추출 실패 |
| domain_fit | 70-85% | industry_label 또는 domain_depth null |
| culture_fit | **10-30%** | work_style_signals 대부분 null |
| role_fit | 70-85% | role_evolution 추출 실패 |

**"피처 1개+ ACTIVE" 비율**: ~85-90% (vacancy_fit + domain_fit + role_fit이 커버)

> **stage_match 40% 하한 근거**: NICE 매칭률 60%(가정 A5)이더라도, stage_match가 ACTIVE가 되려면 (1) 후보의 경력 회사 중 최소 1곳이 NICE 매칭 성공 AND (2) 매칭된 회사의 stage_estimate가 유의미해야 한다. 평균 경력 3건 중 스타트업/해외 기업이 포함되면 NICE 매칭 성공 회사가 1곳도 없는 경우가 발생. 따라서 NICE 매칭률 60% ≠ stage_match ACTIVE 60%이며, 약 40%가 보수적 하한.

**완화 전략**:
- culture_fit은 v1에서 INACTIVE가 정상임을 DS/MLE에 사전 고지
- overall_match_score 계산 시 INACTIVE 피처 weight 재분배 (v4 로직 이미 포함)
- v1.1에서 투자 DB 연동으로 stage_match 활성화 비율 향상

### 2.12 [Medium] Graph 데이터 TTL / 보존 정책

> **v3 신설**: v2 리뷰에서 지적된 보존 정책 부재.

**리스크**: 오래된 이력서의 Graph 데이터를 무한 보유하면 노드 수 증가 → 비용/성능 문제

**완화 전략**:
- **이력서**: 마지막 갱신 후 3년 경과 시 soft-delete (Graph에서 제거, JSON은 아카이브)
- **JD**: 마감 후 1년 경과 시 soft-delete
- **MappingFeatures**: 대상 Vacancy 삭제 시 함께 삭제
- soft-delete: `is_archived = true` 플래그로 쿼리에서 제외, 물리 삭제는 별도 배치

### 2.13 [High] PII 마스킹이 LLM 추출 품질에 미치는 영향

**리스크**: 이름/연락처/주소를 [NAME]/[PHONE]/[ADDR]로 마스킹하면 LLM이 문맥을 잘못 해석하거나, evidence_span이 원문과 불일치할 수 있음

**특히 위험한 케이스**:
- span offset 변동: 마스킹으로 문자열 길이가 바뀌면 LLM이 인용한 span의 위치가 원본과 달라짐
- 한국어 이름 NER 실패: "김 대리", "박팀장" 등 패턴에서 이름과 직급이 붙어있으면 마스킹 누락
- 마스킹 과다: 회사명까지 마스킹하면 past_company_context 연결 불가

**완화 전략**:
- Phase 0 PoC에서 "마스킹 전후 추출 품질 비교" 실험 (10건) — 마스킹 버전과 원본 버전의 추출 결과 diff
- span offset 보존을 위한 character-level offset mapping 구현
- 마스킹 대상을 최소화: 이름 + 연락처만 마스킹, 회사명/직무명은 유지

### 2.14 [Medium] Embedding 모델 한국어 도메인 분별력

**리스크**: text-embedding-3-small이 짧은 한국어 도메인 텍스트("핀테크 백엔드", "이커머스 데이터")에서 충분한 cosine similarity 분별력을 제공하지 못할 수 있음

**영향**: domain_fit 피처의 정확도 하락 → 매칭 품질 감소

**완화 전략**:
- Phase 0에서 3개 모델 비교: text-embedding-3-small vs Cohere embed-multilingual-v3.0 vs BGE-M3
- 20쌍의 (이력서 도메인, JD 도메인) 텍스트로 cosine similarity 분별력 테스트
- 분별력 부족 시 → Cohere multilingual로 전환 (비용 $6 → $30, 허용 범위)

---

## 3. v1 계획에서 유효한 부분 (계승)

v1 계획의 모든 것이 잘못된 것은 아니다. 아래는 v3에서도 유효하게 활용한다.

| v1 내용 | v3 활용 | 비고 |
|---|---|---|
| PDF/HWP 파싱 파이프라인 설계 | **그대로 계승** | 핵심 전처리 |
| 기술 사전 + Fuzzy Matching | **그대로 계승** | tech_stack 추출의 기반 |
| 블록 기반 Relation Assembly | **경력 블록 분리에 활용** | v4의 Experience별 처리 단위 |
| PII 마스킹 전략 | **그대로 계승** | API 사용 시 필수 |
| 회사/학교 사전 + alias | **회사 사전만 계승** | NICE 매칭 보조 |
| Silver/Gold label 체계 | **Phase 2 ML Distillation에 활용** | 범위 축소 (scope_type, seniority만) |
| Entity Resolution (BGE-M3 + FAISS) | **Graph 적재 시 활용** | 타입별 분리 전략 유지 |
| Batch API 50% 할인 활용 | **핵심 비용 최적화** | Anthropic/OpenAI 모두 |
| Confidence calibration (Temperature Scaling) | **Phase 2에서 활용** | ML Distillation 시 |
| 한국어 SLM 모델 가이드 (EXAONE, Qwen2.5) | **On-premise 시나리오에서 활용** | PII 불가 시 |

---

## 4. v1 → v4 핵심 변경 요약

| 항목 | v1 | v4 | 변경 이유 |
|---|---|---|---|
| 목표 | 범용 KG 추출 | v4 Context 생성 | 온톨로지가 구체화됨 |
| 스키마 | 10개 노드 + 12개 엣지 (범용) | 8개 노드 + 12개 엣지 (v4 특화) | v4 graph_schema 반영 |
| Rule 커버리지 | 40-70% | 25-35% | v4 추출 태스크가 더 복잡 |
| LLM 비율 | 5-15% (fallback) | 50-65% (핵심) | outcomes, signals 등 LLM 필수 |
| ML Distillation | 핵심 전략 (60-80% 절감) | 보조 전략 (20-30% 절감) | v4 태스크의 ML 대체 범위 제한 |
| 비용 추정 | 1,250만~4,800만 원 | 1,167만~2,333만 원 | 처리 방식/모델 차이 |
| LLM 모델 | GPT-4o / Claude Sonnet | Haiku / Flash (+ Sonnet fallback) | 추출 복잡도에 맞는 모델 층위 |
| Graph DB | 미정 | Neo4j AuraDB | v4 Cypher 쿼리 호환 |
| 최종 산출물 | Entity + Relation triples | Context JSON + Graph + MappingFeatures | v4 온톨로지의 요구 |
| 에러 핸들링 | 없음 | 에러 유형별 retry/skip/fallback 정책 | 500K 대량 처리 안정성 |
| 운영 전략 | 없음 | 증분 처리, 롤백, TTL 정책 | 최초 처리 이후 운영 고려 |
| 타임라인 | 12주 (미명시) | 14~18주 (DE+MLE 2명 기준) | 현실적 일정 반영 |
