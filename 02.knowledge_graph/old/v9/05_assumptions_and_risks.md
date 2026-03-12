# 가상 정보, 리스크, 완화 전략

> 이 계획에서 가정한 정보와 리스크를 명시적으로 정리한다.
> 각 가정이 잘못되었을 때의 영향과 대응 방안을 포함한다.
>
> 작성일: 2026-03-08 (v2 기반)
> 개정일: 2026-03-08 (v6 — v10 정합: Embedding 확정, CompanyTalentSignal 제외 명시, 스키마 진화 리스크)
> 개정일: 2026-03-08 (v7 — A5 NICE 접근 blocking dependency, R2.17 LLM 파싱 실패 리스크)
> 개정일: 2026-03-09 (v8 — DB 기반 파이프라인 전환: 가정 갱신, 리스크 제거/완화/신규 추가)
> 개정일: 2026-03-10 (v9 — v11 온톨로지 정합: 3-Tier 비교 전략 통일, 전공 threshold 0.75 조정, synonyms 매칭 추가)

---

## 1. 가상으로 설정한 정보 (Assumptions)

### 1.1 데이터 볼륨 관련

| ID | 가정 | 가정값 | 영향 범위 | 잘못되면 |
|---|---|---|---|---|
| **A1** | JD 보유량 | 10,000건 | CompanyContext 생성 비용 | 1,000건이면 비용 1/10, 100,000건이면 비용 10배 |
| **A2** | 이력서 보유량 | 500,000건 | **전체 비용의 핵심 드라이버** | resume-hub DB 카운트 쿼리로 즉시 확인 가능 **(v8 변경)** |
| ~~**A3**~~ | ~~이력서 평균 크기~~ | ~~300KB~~ | — | **제거** (v8: 파일 크기 무관, DB 레코드 단위 처리) |
| **A4** | 이력서당 평균 경력 수 | 3건 | LLM 호출 횟수/비용 | 5건이면 LLM 비용 67% 증가. resume-hub Career 엔티티 평균으로 즉시 확인 가능 **(v8 변경)** |
| **A9** | 매핑 대상 쌍 수 | 500만 (JD × 상위 500) | MappingFeatures 비용/인프라 | 비용 영향 작음 (계산이 저렴) |

### 1.2 데이터 품질 관련

| ID | 가정 | 가정값 | 영향 범위 | 잘못되면 |
|---|---|---|---|---|
| **A5** | NICE 매칭률 | **80-90%** **(v8 변경: 60%→80-90%)** | PastCompanyContext 커버리지 | BRN 직접 매칭이므로 v7 대비 대폭 향상. BRN null인 40%(A19)는 여전히 매칭 불가 → 회사명 fuzzy match fallback |
| ~~**A7**~~ | ~~Rule 추출 성공률~~ | ~~70%~~ | — | **제거** (v8: DB 직접 조회이므로 Rule 추출 불필요) |
| ~~**A11**~~ | ~~파일 형식 분포~~ | ~~PDF 70%, DOCX 20%, HWP 10%~~ | — | **제거** (v8: 파일 형식 무관) |
| ~~**A12**~~ | ~~OCR 필요 비율~~ | ~~5% 미만~~ | — | **제거** (v8: OCR 불필요) |
| **A17** | 이력서 중복률 | 5~10% | 처리 건수, Graph 품질 | **v8 완화**: SiteUserMapping 테이블로 중복 감지 가능 → 20%이어도 DB 기반 감지로 처리 효율적 |
| **A19** | Career.businessRegistrationNumber null 비율 | **40%** **(v8 신규)** | NICE 매칭률 핵심 드라이버 | 60%이면 BRN 기반 매칭은 40%만 가능, 나머지는 회사명 fuzzy match fallback |
| **A20** | Career.workDetails null 비율 | **20%** **(v8 신규)** | LLM 입력 품질 | 40%이면 LLM 추출 가능 건 40% 감소 → outcomes/signals 피처 활성화율 하락 |
| **A21** | overview.descriptions 평균 길이 | **1,000자** **(v8 신규)** | CompanyContext LLM 토큰 | 2,000자이면 토큰 2배 → CompanyContext LLM 비용 증가 (영향 미미) |
| **A22** | Skill.code null 비율 + 비표준 값 비율 | **code null 10%, 비표준 값 30-50%** **(v8.1 변경)** | Tier 2 embedding 정규화 부하 | code null 30%이면 Tier 2 embedding 의존도 증가, 비표준 값 70%이면 Tier 2 캐시 miss 증가 → embedding 비용 미미하게 증가 |
| **A25** | 3-Tier 비교 전략 embedding similarity threshold | **스킬 0.85, 전공 0.75, 직무 0.80** **(v9 변경: 전공 0.80→0.75, v11.1 정합)** | 정규화 정확도 | threshold가 너무 높으면 정규화율 하락 (매핑 안 됨), 너무 낮으면 오매핑 증가 → Phase 0에서 캘리브레이션 |
| **A26** | Tier 2 canonical embedding 사전 커버리지 | **스킬 ~2,000, 전공 ~500, 직무 ~300** **(v8.1 신규)** | 정규화 커버리지 | canonical 목록에 없는 엔티티는 정규화 불가 → needs_review 플래그 |
| **A23** | resume-hub 전체 이력서 적재 완료 | **완료** **(v8 신규)** | **전체 파이프라인 전제 조건** | 미완료 시 DB 기반 접근 자체가 불가 → v7 방식(파일 파싱) fallback 필요 |
| **A24** | DB 접근 방식 | **리드 레플리카 직접** **(v8 신규)** | 대량 조회 성능 | API only이면 조회 성능 제약 → 배치 사이즈/동시성 조정 필요 |

### 1.3 모델 성능 관련

| ID | 가정 | 가정값 | 영향 범위 | 잘못되면 |
|---|---|---|---|---|
| **A6** | LLM 추출 토큰 사용량 | **CompanyContext: 2,200 tok, CandidateContext: 1,800 tok** **(v8 변경)** | 비용 산출의 핵심 | 2배이면 LLM 비용 2배 |
| **A8** | Haiku 한국어 추출 품질 | Sonnet의 85% | 모델 선택 결정 | 70% 이하이면 Sonnet 필수 → 비용 5배 |
| **A16** | Embedding 모델 한국어 분별력 | `text-multilingual-embedding-002` (Vertex AI) 기준 "우수" | 도메인 매칭 정확도 | "양호" 이하이면 Cohere multilingual 또는 BGE-M3 전환 |

### 1.4 비즈니스/법적 관련

| ID | 가정 | 가정값 | 영향 범위 | 잘못되면 |
|---|---|---|---|---|
| **A10** | PII 외부 전송 가능 | 마스킹 후 가능 | **전체 아키텍처** | 불가 시 On-premise → 비용 14배, 일정 2배 |
| **A14** | Neo4j Professional 용량 | 800K 노드 $100/월 | 인프라 비용 | 더 큰 플랜 필요 시 $200-500/월 |
| **A15** | Batch API 응답 시간 | 24시간 이내 | 전체 처리 일정 | 지연 시 일정에 영향 |
| **A18** | CompanyTalentSignal은 v1에서 의도적으로 제외 | 제외 (v10 A3 참조) | Graph 스키마 범위 | 데이터 전제 조건 미충족, v2 이후 도입 검토 |

---

## 2. 리스크 분석

### 2.1 [Critical] PII 개인정보 처리 — 전체 아키텍처 결정

**리스크**: 이력서를 외부 LLM API로 전송 시 개인정보보호법 위반 가능

**영향**: 시나리오 A(API, ~$8,899) ↔ 시나리오 C(On-premise, ~$13,874)의 약 1.6배 비용 차이

**현실적 옵션 분석**:

| 옵션 | 비용 | 품질 | 일정 | 비고 |
|---|---|---|---|---|
| **마스킹 후 API 전송** | 가장 저렴 | 최고 (Haiku/Sonnet) | 빠름 | 법무 승인 필수, 마스킹 품질이 관건 |
| **동의 기반 API 전송** | 저렴 | 최고 | 빠름 | 500K건 전체 동의 확보 현실적으로 불가 |
| **On-premise SLM** | 1.6배 비용 | Haiku 대비 낮음 | 느림 | EXAONE 7.8B 기준 |
| **Azure/AWS Private Endpoint** | API비용 + $500~2,000/월 | API 수준 | 중간 | Azure OpenAI: Private Endpoint |

**권장 대응**:
1. Phase 0에서 법무팀과 PII 마스킹 전략 확정
2. 마스킹 수준: 이름 → [NAME], 연락처 → [PHONE], 주소 → [ADDR] 치환
3. **v8 참고**: DB에서 조회하므로 PII 마스킹 대상 필드가 명확 (이름, 연락처 등은 별도 컬럼)
4. 법무 불가 판정 시 → Azure OpenAI Private Endpoint 또는 On-premise 전환
5. 법무 결론 미확정 시 **마스킹 기반 API를 기본값으로 Phase 1 진행**

### 2.2 [Critical] LLM 추출 품질 — 시스템 실현 가능성

**리스크**: v10가 요구하는 추출(outcomes, situational_signals)의 LLM 정확도가 기대 이하

**영향**: MappingFeatures의 핵심 피처(vacancy_fit, stage_match)가 무의미해질 수 있음

**v8 완화 요소**: DB 정형 필드를 LLM 프롬프트에 사전 제공하므로 LLM이 더 정확한 추출을 할 수 있음 (positionGradeCode → scope_type 힌트, industry_codes → 도메인 컨텍스트 등)

**완화 전략**:

```
Phase 0 PoC에서 검증할 핵심 질문:
1. situational_signals 14개 taxonomy 분류 정확도 → 50% 미만이면 taxonomy 축소
2. outcomes 추출 시 quantitative vs qualitative 판별 정확도
3. scope_type 분류 정확도 → 70% 미만이면 ML Distillation 우선 투자
4. (v8 신규) DB 정형 필드 사전 제공 유무에 따른 추출 품질 차이 비교

추출 품질이 낮을 때의 대안:
- taxonomy 축소: 14개 → 6개 상위 카테고리로
- 2-pass 추출: 1차 추출 → 자기 검증 → 2차 보정 (비용 2배, 정확도 향상)
- Human-in-the-loop: 낮은 confidence 건만 전문가 검수 (비용 증가)
```

### ~~2.3 [Critical] 파싱 품질 + LLM 품질 상관 리스크~~ **(v8 제거)**

> **v8 변경**: DB 조회 기반이므로 파싱 실패 자체가 발생하지 않음. 이 리스크는 **완전히 제거**된다.
> v7에서 Critical이었던 이 리스크의 제거는 v8의 가장 큰 이점 중 하나이다.

### 2.4 [Medium] NICE 데이터 매칭률 **(v8 변경: High→Medium)**

**리스크**: 이력서 내 회사 → NICE DB 매칭이 기대보다 낮을 수 있음

**v8 완화**: `Career.businessRegistrationNumber`(BRN) 직접 매칭으로 **60%→80-90%** 향상 예상
- BRN이 있는 경우 (A19 기준 60%): 직접 매칭 → 매칭률 ~100%
- BRN이 없는 경우 (40%): 기존 회사명 fuzzy match fallback → 매칭률 ~60%
- 가중 평균: 60% × 100% + 40% × 60% = **84%**

**매칭 실패 예상 케이스**:
- BRN null인 경우: 스타트업/프리랜서/해외 기업 경력
- BRN은 있으나 NICE 미등록: 신생 기업, 폐업 기업

**완화 전략**:
- BRN null 시 → 회사명 fuzzy match fallback (v7 방식 유지)
- 매칭 실패 시 → `past_company_context = null` (graceful degradation)
- v1.1에서 투자 DB 연동으로 스타트업 커버리지 보강

### 2.5 [High] Confidence 캘리브레이션

**리스크**: LLM 자가 평가 confidence 값이 실제 정확도와 상관없을 수 있음

**영향**: MappingFeatures의 confidence 가중 스코어가 왜곡됨

**완화 전략**:
- Phase 2에서 gold set 기반 confidence 실측
- 캘리브레이션 함수 적용: `calibrated = sigmoid(a * raw + b)` (Platt Scaling)
- 필요 시 LLM confidence 대신 **출력 일관성 기반 confidence** 도입

### 2.6 [High] LLM API Rate Limit

**리스크**: 500K 이력서를 Batch API로 처리할 때 API 제공사의 rate limit/quota에 걸릴 수 있음

**완화 전략**:
- Phase 0에서 소규모 Batch API 테스트로 실제 처리 속도/제한 확인
- 1,000건/chunk 단위로 분할하여 순차 제출
- 여러 API 제공사 분산 (Haiku + Flash) 검토
- Enterprise 계약 시 quota 확대 협의

### 2.7 [High] LLM 모델 버전 변경 리스크

**리스크**: Haiku 4.5가 deprecated 되거나 동작이 변경되면 추출 결과 일관성 깨짐

**완화 전략 (Model Pinning)**:
- API 호출 시 **정확한 모델 버전 명시** (e.g., `claude-haiku-4-5-20251001`)
- 모델 변경 시 **50건 회귀 테스트** 실행 후 전환
- Context JSON에 `model_version` 메타데이터 기록

### 2.8 [High] 증분 처리 / 데이터 갱신 전략

**리스크**: 최초 500K 처리 후 신규 이력서 유입, 기존 이력서 갱신 시 재처리 전략 필요

**v8 완화**: DB 기반이므로 `updated_at` 필드로 변경 감지가 정확함 (파일 hash 비교보다 신뢰도 높음)

**완화 전략**: `04_execution_plan.md`의 "운영 전략" 섹션 참조

### 2.9 [Medium] Graph DB 스케일링

**리스크**: 500K 이력서 → ~800만 노드, ~2,500만 엣지 시 Neo4j 성능/비용 문제

**완화 전략**: Phase 1에서 1,000건으로 시작 → Phase 2 확장 시 Professional 전환

### 2.10 [Medium] Entity Resolution — 비표준 데이터 비교 전략 **(v9 변경: 3-Tier 비교 전략 통일)**

**리스크**: DB 데이터가 비표준 상태. "자바"/"JAVA"/"java", "서울대"/"서울대학교", "PM"/"프로덕트매니저" 등 동일 엔티티의 변형이 다수 존재

**v9 완화**: 3-Tier 비교 전략 도입 (v11.1 `00_data_source_mapping.md` §1.5 정합)
- **Tier 1 (정규화 적합)**: 대학교, 회사명, 산업 코드 → code-hub CI Lookup
  - 유한 집합, 명확한 정체성 → 비용 0, 정확도 높음 (95%+)
- **Tier 2 (경량 정규화 + 임베딩)**: 스킬 → CI 매칭 + synonyms 매칭, 미매칭 시 임베딩
  - `normalize_skill()`: CI 매칭 → synonyms 매칭 → 미매칭 시 원본 유지 (v11.1 §1.3 정합)
  - threshold: 스킬 0.85
  - 비용 ~$0.06 (전체 대비 무시)
- **Tier 3 (임베딩 전용)**: 전공, 직무명, 롱테일 스킬 → 정규화하지 않음, 임베딩 유사도로 비교
  - threshold: 전공 0.75 (v11.1 §1.5 정합), 직무 0.80
  - 정규화하지 않는 이유: "컴퓨터공학" vs "컴퓨터과학"은 다른 전공인데 코드 정규화 시 동일 처리 위험 (v11.1 A9)

**잔존 리스크**:
- Tier 2/3 threshold 최적화 필요 (Phase 0 PoC에서 캘리브레이션)
- canonical 사전에 없는 신규 스킬은 Tier 2 CI/synonyms 매칭 불가 → 임베딩 fallback
- embedding 모델의 한국어 동의어 분별력에 의존 (예: "PM" ↔ "프로덕트매니저" 유사도가 충분한지)
- synonyms 사전 커버리지 부족 시 Tier 2 매칭률 저하 → 운영 단계에서 점진적 보강

### 2.11 [Medium] v10 MappingFeatures 활성화 비율

**리스크**: culture_fit은 대부분 INACTIVE, stage_match도 NICE 매칭 실패 시 INACTIVE

**v8 개선**: NICE 매칭률 84%(v8) vs 60%(v7)로 향상 → stage_match ACTIVE 비율 향상 예상

**예상 활성화 비율**:

| 피처 | v7 예상 ACTIVE | v8 예상 ACTIVE | 변경 근거 |
|---|---|---|---|
| stage_match | 40-60% | **55-75%** | BRN 직접 매칭으로 NICE 매칭률 향상 |
| vacancy_fit | 60-80% | 60-80% | 변동 없음 |
| domain_fit | 70-85% | **75-90%** | code-hub INDUSTRY 코드로 industry_label 커버리지 향상 |
| culture_fit | 10-30% | 10-30% | 변동 없음 |
| role_fit | 70-85% | **75-90%** | positionGradeCode 힌트로 scope_type 정확도 향상 |

### 2.12 [Medium] Graph 데이터 TTL / 보존 정책

**리스크**: 오래된 이력서의 Graph 데이터를 무한 보유하면 노드 수 증가

**완화 전략**: 이력서 3년 경과 시 soft-delete, JD 마감 후 1년 경과 시 soft-delete

### 2.13 [High] PII 마스킹이 LLM 추출 품질에 미치는 영향

**리스크**: 마스킹이 LLM 추출에 영향

**v8 완화**: DB에서 조회하므로 PII 필드(이름, 연락처)와 추출 대상 필드(workDetails, CareerDescription)가 명확히 분리되어 있음. 마스킹 대상이 정확하고 span offset 변동 리스크가 없음.

### 2.14 [Medium] Embedding 모델 한국어 도메인 분별력

**리스크**: `text-multilingual-embedding-002`의 짧은 한국어 텍스트 분별력 부족 가능

**완화 전략**: Phase 0에서 확정 모델 검증, 실패 시 Cohere/BGE-M3 전환

### 2.15 [Low] 이력서 중복이 Graph/서빙 품질에 미치는 영향 **(v8 변경: Medium→Low)**

**리스크**: 동일인의 다중 이력서가 중복 처리됨

**v8 완화**: resume-hub의 `SiteUserMapping` 테이블로 사이트간 동일인 매핑이 가능하여 중복 감지가 대폭 간소화됨. SimHash 기반 비교가 불필요하거나 보조 수단으로만 사용.

### 2.16 [Medium] v10 스키마 진화에 따른 계획 정합성 리스크

**리스크**: 온톨로지 스키마 진화 시 파이프라인 코드 뒤처짐

**완화 전략**: Pydantic 모델 기반 스키마 검증 + 교차 검증 리뷰

### 2.17 [High] LLM 출력 파싱 실패

**리스크**: 150만 건 이상의 LLM 호출에서 JSON 파싱 실패 2-10% 발생

**v8 참고**: LLM 호출 건수는 v7과 동일하나, 건당 토큰이 줄어 프롬프트가 간결해져 파싱 실패율이 다소 감소할 수 있음 (정량적 추정은 Phase 0 PoC에서 확인)

**완화 전략**: 02 문서 §8.3 "LLM 출력 파싱 실패 전략" 참조 (3-tier retry)

### 2.18 [High] DB 접근 권한/가용성 **(v8 신규)**

**리스크**: resume-hub / job-hub / code-hub 3개 DB에 대한 읽기 접근 권한 미확보 또는 리드 레플리카 미제공

**영향**: DB 접근이 불가하면 v8 방식 자체가 성립하지 않음 → v7 방식(파일 파싱)으로 fallback 필요, 일정 5~6주 증가

**완화 전략**:
- **Pre-Phase 0 blocking dependency**로 관리 — Phase 0 시작 2주 전까지 반드시 확보
- 리드 레플리카 접근이 이상적이나, API 접근만 가능한 경우 배치 사이즈/동시성 조정으로 대응
- 3개 DB 중 일부만 접근 가능한 경우: 접근 가능한 DB는 v8 방식, 불가한 DB는 v7 방식 혼용

### 2.19 [High] 데이터 적재 미완료 **(v8 신규)**

**리스크**: resume-hub에 전체 이력서가 아직 적재 중이거나, 일부 엔티티(CareerDescription, SelfIntroduction 등)가 미적재 상태

**영향**: 적재 미완료 비율에 따라 LLM 추출 가능 건수 감소 → MappingFeatures 커버리지 하락

**완화 전략**:
- Phase 0 프로파일링에서 각 테이블의 레코드 수 + null 비율 확인 (A23 검증)
- 적재 완료 비율 80% 미만이면: 적재 완료 대기 또는 파일 파싱 fallback 병행 검토
- 부분 적재 상태에서도 파이프라인 개발은 진행 가능 (테스트 데이터로 개발)

### 2.20 [Medium] 텍스트 필드 품질 **(v8 신규)**

**리스크**: `Career.workDetails` null 비율이 가정(20%)보다 높거나, 내용이 너무 짧아 LLM 추출 품질이 기대 이하

**영향**: workDetails가 없으면 outcomes, situational_signals 추출이 불가 → 해당 피처 INACTIVE

**완화 전략**:
- Phase 0에서 workDetails null 비율 + 평균 길이 프로파일링 (A20 검증)
- workDetails null인 경우: `CareerDescription.description`을 대체 입력으로 사용
- 두 필드 모두 null인 경우: scope_type은 positionGradeCode Rule 기반 추정, outcomes/signals는 null

### 2.21 [Medium] code-hub 코드 완성도 + synonyms 커버리지 **(v9 변경)**

**리스크**: code-hub의 HARD_SKILL 코드가 실제 기술 스택을 충분히 커버하지 못하고, synonyms 사전이 불완전하여 Tier 2 CI+synonyms 매칭률이 기대 이하일 수 있음

**영향**:
- code null인 경우: code-hub CI 매칭 불가 → synonyms 매칭 시도 → 임베딩 fallback
- synonyms 사전 부족: CI 매칭 실패 + synonyms 매칭 실패 → 임베딩 비교로 전환 (confidence 하락)
- 비표준 값: `normalize_skill()` CI+synonyms 2단계로 매핑하지만, 양쪽 모두 미매칭 시 원본 유지

**완화 전략**:
- Phase 0에서 Skill.code null 비율 + 비표준 값 비율 확인 (A22 검증)
- **3-Tier 비교 전략**: Tier 2 CI+synonyms 미매칭 시 원본 유지 + 임베딩 비교 (v11.1 §1.3 정합)
- synonyms 사전 초기 구축: code-hub 기반 + 도메인 전문가 검토
- 스킬 코드 매칭률 모니터링 (§10.1): 70% 미만 시 synonyms 사전 보강
- threshold 미달 노드에 `needs_review` 플래그 → 운영 단계에서 점진적 보강

### 2.22 [Medium] JSONB 필드 스키마 불일치 **(v8 신규)**

**리스크**: `overview.descriptions`, `requirement.careers` 등 JSONB 필드의 실제 구조가 예상과 다름

**영향**: JSONB 파싱 실패 → CompanyContext LLM 입력 구성 불가

**완화 전략**:
- Phase 0에서 JSONB 필드 스키마 샘플링 (50건)으로 실제 구조 확인
- JSONB 구조가 일관적이지 않은 경우: 방어적 파싱 로직 + fallback (전체 텍스트를 LLM에 전달)
- Pydantic 모델로 JSONB 스키마 정의 → 불일치 시 자동 감지

---

## 3. v1 계획에서 유효한 부분 (계승)

v1 계획의 모든 것이 잘못된 것은 아니다. 아래는 v8에서도 유효하게 활용한다.

| v1 내용 | v8 활용 | 비고 |
|---|---|---|
| ~~PDF/HWP 파싱 파이프라인 설계~~ | **제거** **(v8 변경)** | DB 조회로 대체 |
| ~~기술 사전 + Fuzzy Matching~~ | **제거** **(v8 변경)** | code-hub HARD_SKILL 코드로 대체 |
| ~~블록 기반 Relation Assembly~~ | **제거** **(v8 변경)** | Career 엔티티가 이미 분리됨 |
| PII 마스킹 전략 | **계승** | API 사용 시 필수 (DB 필드 단위 마스킹) |
| ~~회사/학교 사전 + alias~~ | **대폭 축소** **(v8 변경)** | BRN 기반 직접 매칭, 회사 사전은 fallback만 |
| Silver/Gold label 체계 | **Phase 2 ML Distillation에 활용** | 범위 축소 (scope_type, seniority만) |
| Entity Resolution (BGE-M3 + FAISS) | **방향 전환 → 3-Tier 비교 전략** **(v9 변경)** | Tier 1(code-hub CI) + Tier 2(CI+synonyms+임베딩) + Tier 3(임베딩 전용), text-multilingual-embedding-002 사용 |
| Batch API 50% 할인 활용 | **핵심 비용 최적화** | Anthropic/OpenAI 모두 |
| Confidence calibration (Temperature Scaling) | **Phase 2에서 활용** | ML Distillation 시 |
| 한국어 SLM 모델 가이드 (EXAONE, Qwen2.5) | **On-premise 시나리오에서 활용** | PII 불가 시 |

---

## 4. v1 → v8 핵심 변경 요약

| 항목 | v1 | v8 | 변경 이유 |
|---|---|---|---|
| 목표 | 범용 KG 추출 | v10 Context 생성 | 온톨로지가 구체화됨 |
| 데이터 소스 | 150GB 원본 파일 | **resume-hub/job-hub/code-hub DB** | 정형 데이터 활용 **(v8 핵심)** |
| 스키마 | 10개 노드 + 12개 엣지 (범용) | 8개 노드 + 12개 엣지 (v10 특화) | v10 graph_schema 반영 |
| 전처리 | PDF/DOCX/HWP 파싱 + 섹션 분할 + 블록 분리 | **DB 커넥터만** | 파싱 전체 제거 **(v8 핵심)** |
| Rule 커버리지 | 40-70% | **DB 조회 35-45%** + Rule 10-15% | DB 직접 조회로 대체 |
| LLM 비율 | 5-15% (fallback) | **30-45%** (핵심 추론에 집중) | 입력 축소로 효율 향상 |
| NICE 매칭 | 회사명 fuzzy match (60%) | **BRN 직접 매칭 (80-90%)** | businessRegistrationNumber 활용 |
| 코드 정규화 | 기술 사전 2,000개 | **3-Tier 비교 전략**: Tier 1(CI Lookup) + Tier 2(CI+synonyms+임베딩) + Tier 3(임베딩 전용) | 비표준 데이터 대응 **(v9 변경)** |
| ML Distillation | 핵심 전략 (60-80% 절감) | 보조 전략 (20-30% 절감) | v10 태스크의 ML 대체 범위 제한 |
| 비용 추정 | 1,250만~4,800만 원 | **1,196만~1,901만 원** | DB 기반 토큰 절감 |
| LLM 모델 | GPT-4o / Claude Sonnet | Haiku / Flash (+ Sonnet fallback) | 추출 복잡도에 맞는 모델 |
| Embedding 모델 | text-embedding-3-small | text-multilingual-embedding-002 (v6) | v10 확정 모델 |
| Graph DB | 미정 | Neo4j AuraDB | v10 Cypher 쿼리 호환 |
| Graph Idempotency | 없음 | Deterministic ID + MERGE (v5) | 재처리/증분 안정성 |
| 최종 산출물 | Entity + Relation triples | Context JSON + Graph + MappingFeatures | v11 온톨로지의 요구 |
| 타임라인 | 12주 (미명시) | **14~17주 (v9, v7의 18~22주에서 단축)** | DB 기반 전처리 제거 + 3-Tier 비교 전략 모듈 추가 **(v9 변경)** |
