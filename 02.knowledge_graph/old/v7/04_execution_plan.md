# 실행 계획 v7 — v10 온톨로지 기반

> v10 온톨로지의 CompanyContext + CandidateContext + Graph + MappingFeatures를
> 구축하기 위한 단계별 실행 계획.
>
> 작성일: 2026-03-08 (v2 기반)
> 개정일: 2026-03-08 (v6 — v10 정합: Industry 노드, Embedding 확정 검증, REQUIRES_ROLE/MAPPED_TO, 크롤링 파이프라인, power analysis)
> 개정일: 2026-03-08 (v7 — 오케스트레이션 전략 신설, 타임라인 현실화 18~22주, Pre-Phase 0 NICE DB 접근)

---

## 인력 배치 가정

| 역할 | 인원 | 투입 시기 | 비고 |
|---|---|---|---|
| **DE (Data Engineer)** | 1명 | Phase 0~2 (전체) | 파이프라인 구축, 인프라, 배치 처리 |
| **MLE (ML Engineer)** | 1명 | Phase 0~2 (전체) | LLM 프롬프트 설계, ML Distillation, 품질 평가 |
| **도메인 전문가 (HR/채용)** | 1명 | Phase 0, 2 (파트타임) | Gold Label 검수, taxonomy 검증 |

> 아래 타임라인은 **DE 1명 + MLE 1명 풀타임** 기준이다. 1인 작업 시 일정이 1.5~2배로 늘어난다.

---

## 전체 로드맵 개요

```
Phase 0: 기반 구축 + PoC (3~4주)
    ├─ 데이터 탐색 + 인프라 셋업
    ├─ LLM 추출 품질 PoC (50건)
    ├─ 파싱 품질 PoC (50건, v5 추가)
    └─ 의사결정: 모델 선택, PII 전략

Phase 1: MVP 파이프라인 (8~10주)
    ├─ 전처리 모듈 (2주)
    ├─ CompanyContext 파이프라인 (1~2주)
    ├─ CandidateContext 파이프라인 (3주)
    ├─ Graph 적재 + Vector Index + Entity Resolution (2주)
    └─ MappingFeatures + Candidate Shortlisting (1주)

Phase 2: 확장 + 최적화 (4~5주)
    ├─ 전체 데이터 처리 (2~3주)
    ├─ 품질 평가 + 캘리브레이션 (1주, 병행)
    ├─ DS/MLE 서빙 인터페이스 (1주)
    └─ ML Knowledge Distillation (선택적, 1~2주)

Phase 3: 고도화 (지속)
    ├─ 크롤링 파이프라인 (7주) — v6 확장
    │   ├─ C1: 크롤러 인프라 구축 (2주)
    │   ├─ C2: T3 홈페이지 크롤링 (2주)
    │   ├─ C3: T4 뉴스 크롤링 (2주)
    │   └─ C4: 데이터 병합 + 품질 검증 (1주)
    ├─ Company-to-Company 관계 로드맵
    ├─ GraphRAG vs baseline ablation
    └─ Active Learning
```

---

## 사전 준비 (Pre-Phase 0) — Blocking Dependencies **(v7 신설)**

> **v7 신설**: Phase 0 시작 전 반드시 확보해야 하는 외부 의존성.
> 이 항목들이 해결되지 않으면 Phase 0 자체를 시작할 수 없다.

### NICE DB 접근 확보 **(v7 신설, Blocking)**

- [ ] NICE DB 접근 계약 상태 확인
  - 기존 계약이 있는 경우: API 접근 키 + 사용 가능 필드 + 호출 제한 확인
  - 기존 계약이 없는 경우: 계약 협의 시작 (예상 소요: 2~4주)
- [ ] NICE DB 테스트 접근 권한 확보
  - Phase 0-1의 "NICE DB 접근 확인 + 필드 매핑" 태스크가 이 접근에 의존
  - 테스트 환경에서 API 호출 가능한 상태 확인
- [ ] NICE 업종코드 마스터 데이터 확보 가능 여부 확인
  - Industry 마스터 노드 생성(Phase 0-3)에 필요

**판정 기준**:
- NICE DB 접근이 Phase 0 시작 2주 전까지 확보되지 않으면 → NICE 의존 태스크를 Phase 0 후반으로 연기하고, 공개 데이터(DART, 사업자등록 조회)로 우선 대체
- 대체 시 stage_match 피처 품질 하락이 예상되므로, 05 문서 A5 리스크 참조

---

## Phase 0: 기반 구축 + PoC (3~4주)

### 0-1. 데이터 탐색 및 프로파일링 (1주)

#### 이력서 데이터 분석
- [ ] 150GB 데이터의 파일 형식 분포 조사 (PDF/DOCX/HWP/이미지)
- [ ] 무작위 500건 샘플링
  - 이력서 평균 크기 → 총 건수 추정 (가정 A2 검증)
  - 경력 블록 평균 개수 (가정 A4 검증)
  - 자유서술 vs 정형 블록 비율
  - 한국어/영문 혼합 비율
- [ ] OCR 필요 비율 확인 (가정 A12 검증)
- [ ] 중복률 추정 (SimHash 테스트)
  - **v5 추가**: 동일 candidate_id 다중 버전 비율 측정
  - **v5 추가**: SimHash 유사도 > 0.9인 다른 candidate_id 쌍 비율 측정

#### JD 데이터 분석
- [ ] 보유 JD 수량 확인 (가정 A1 검증)
- [ ] JD 평균 길이 + 구조 분석
- [ ] JD에서 vacancy scope_type 패턴 수동 확인 (20건)

#### NICE 데이터 분석
- [ ] NICE DB 접근 확인 + 필드 매핑
- [ ] 이력서 내 회사명 → NICE 매칭률 테스트 (100건) (가정 A5 검증)

**산출물**: 데이터 프로파일 리포트 — 가정 A1~A5, A11~A12 검증 + 중복률 리포트

### 0-2. LLM 추출 품질 PoC (1~2주)

**목적**: v10 스키마 기준으로 LLM 추출이 실제로 작동하는지 검증

#### v5 추가: 파싱 → 섹션 분할 → 경력 블록 분리 성공률 측정

> **v5 신설**: v4 리뷰에서 지적된 Rule 기반 섹션 분할 커버리지 실측 필요.

- [ ] 이력서 50건에 대해 파싱 → 섹션 분할 → 경력 블록 분리 단계별 성공률 측정
  | 단계 | 측정 항목 | 최소 기준 |
  |---|---|---|
  | 파싱 (PDF/DOCX/HWP → 텍스트) | 텍스트 추출 성공률 | > 90% |
  | 섹션 분할 (경력/학력/기술) | 섹션 경계 정확도 | > 70% |
  | 경력 블록 분리 (회사별) | 블록 분리 정확도 | > 60% |
- [ ] **판정 기준**: 경력 블록 분리 정확도 < 50%이면 LLM 기반 섹션 분할 fallback 검토
  - LLM fallback 전환 시 이력서당 추가 ~1,000 토큰 (비용 영향: $250~500 증가)
  - Phase 1-1에서 LLM 섹션 분할 모듈 개발 추가 (일정 0.5~1주 증가)

#### CandidateContext 추출 테스트 (이력서 50건)
- [ ] 직무별 10건 × 5개 직군 (개발, 디자인, 마케팅, PM, 경영지원)
- [ ] 모델 비교:
  | 모델 | 테스트 건수 | 측정 항목 |
  |---|---|---|
  | Claude Haiku 4.5 | 50건 | 추출 정확도, 토큰 사용량, 비용 |
  | Gemini 2.0 Flash | 50건 | 동일 |
  | Claude Sonnet 4.6 | 10건 | gold standard 비교 |
- [ ] 필드별 추출 성공률 측정:
  | 필드 | 예상 성공률 | 실측 목표 |
  |---|---|---|
  | scope_type | 70-80% | > 70% |
  | outcomes | 60-70% | > 60% |
  | situational_signals | 50-70% | > 50% |
  | failure_recovery | 10-20% | null 정상 |
- [ ] confidence 값의 실제 정확도 상관관계 확인

#### CompanyContext 추출 테스트 (JD 30건)
- [ ] vacancy scope_type 추출 정확도
- [ ] operating_model facets 추출 일관성
- [ ] NICE 매칭 → stage_estimate Rule 검증

#### v4 추가: PII 마스킹 영향 테스트 (10건)

> **v4 신설**: 마스킹 전후 추출 품질 비교로 PII 전략 실현 가능성 사전 검증.

- [ ] 이력서 10건에 대해 마스킹 전/후 LLM 추출 결과 diff
  - 비교 대상: scope_type, outcomes, situational_signals
  - 측정: 필드별 일치율, evidence_span 정확도
- [ ] span offset 변동 테스트 (마스킹으로 인한 span 위치 이동 확인)
- [ ] 결론: 마스킹이 추출 품질에 유의미한 영향을 미치는지 판정

#### Embedding 모델 확정 검증 (20쌍) **(v6 변경)**

> **v4 신설, v6 변경**: ~~3개 모델 비교~~ → `text-multilingual-embedding-002` (Vertex AI) 확정 모델의 한국어 분별력 검증으로 변경.
> v10 온톨로지에서 Vertex AI 통합을 확정했으므로, 해당 모델의 분별력이 충분한지 확인하는 검증 단계로 전환.

- [ ] 20쌍의 (이력서 도메인 텍스트, JD 도메인 텍스트) 수동 구성
  - 10쌍: 의미적으로 유사 (같은 도메인), 10쌍: 의미적으로 상이 (다른 도메인)
- [ ] `text-multilingual-embedding-002` (Vertex AI) 한국어 분별력 검증 **(v6 변경)**
  - 측정: cosine similarity 분포 (유사 쌍 vs 상이 쌍의 분리도)
  - **합격 기준**: 유사 쌍과 상이 쌍의 cosine similarity 분포가 통계적으로 유의미하게 분리 (Mann-Whitney U test p < 0.05)
- [ ] **검증 실패 시에만** Cohere embed-multilingual-v3.0 / BGE-M3 대안 검토 **(v6 변경)**
- [ ] 결론: embedding 모델 확정 (기본값: `text-multilingual-embedding-002`)

#### v4 추가: LLM 호출 전략 비교 (10건)

> **v4 신설**: 경력별 개별 호출 vs 이력서 전체 1회 호출의 품질/비용 비교.

- [ ] 이력서 10건 (경력 3건 이상)에 대해 두 가지 호출 전략 비교
  - A: 경력 블록별 개별 LLM 호출 (현재 설계)
  - B: 이력서 전체를 1회 LLM 호출
- [ ] 측정: 추출 정확도, 토큰 사용량, JSON 파싱 성공률
- [ ] 결론: Phase 1에서 사용할 호출 전략 결정

**산출물**: 모델 비교 리포트 + 추출 품질 메트릭 + 파싱 품질 리포트(v5) + PII 영향 리포트 + Embedding 확정 검증 리포트(v6)

### 0-3. 인프라 셋업 (1주, 0-1과 병행)

- [ ] Neo4j AuraDB Free 인스턴스 생성
- [ ] v10 Graph 스키마 적용 (노드/엣지/인덱스)
- [ ] Vector Index 설정 (chapter_embedding, vacancy_embedding)
- [ ] 프로젝트 리포지토리 셋업 (Python, Poetry/uv)
- [ ] 이력서 파싱 라이브러리 설치 + 테스트 (PyMuPDF, python-docx, python-hwp)
- [ ] PII 마스킹 전략 결정 (법무 확인 결과 반영)

> **v5 추가: 법무 의사결정 기본값 전략**
>
> PII 법무 검토는 외부 의존성이 높아 Phase 0 기간(3~4주) 내 완료가 보장되지 않는다.
> 따라서 아래 기본값 전략을 적용한다:
>
> 1. **Phase 0 1주차**: 법무팀에 PII 마스킹 후 외부 API 전송 가능 여부 검토 요청
> 2. **Phase 0 완료 시점까지 법무 결론 확정**: 결론에 따라 시나리오 A(API) 또는 C(On-premise) 선택
> 3. **Phase 0 완료 시점에 법무 결론 미확정**: **마스킹 기반 API 사용으로 Phase 1 진행** (기본값)
>    - 마스킹 수준: 이름 + 연락처만 마스킹, 회사명/직무명은 유지
>    - 법무 결론 확정 시 전환: API 불가 판정 → 즉시 Azure OpenAI Private Endpoint로 전환
>    - 전환 영향: 프롬프트/파이프라인 구조는 동일, API endpoint만 변경 (~1일)

#### v6 신설: Organization 크롤링 보강 속성 사전 선언 **(v6 신설)**

> v10 온톨로지의 Organization 확장 속성을 Neo4j 스키마에 nullable로 사전 선언.
> Phase 3 크롤링 파이프라인에서 실제 데이터가 적재될 때까지 null로 유지.

- [ ] Neo4j Organization 노드에 아래 속성 nullable로 사전 선언:
  | 속성 | 타입 | 출처 | 비고 |
  |---|---|---|---|
  | `product_description` | String? | 홈페이지 크롤링 (Phase 3) | LLM 추출 |
  | `market_segment` | String? | 홈페이지 크롤링 (Phase 3) | LLM 분류 |
  | `latest_funding_round` | String? | TheVC API (Phase 3) | Series A/B/C 등 |
  | `latest_funding_date` | Date? | TheVC API (Phase 3) | ISO 8601 |
  | `crawl_quality` | Float? | 크롤링 메타데이터 | 0.0~1.0 |
  | `last_crawled_at` | DateTime? | 크롤링 메타데이터 | 마지막 크롤링 시점 |

#### v6 신설: Industry 마스터 노드 사전 생성 **(v6 신설)**

> NICE 업종 코드(한국표준산업분류 KSIC) 기반 Industry 마스터 노드를 사전 생성.
> Phase 1-4에서 Organization→BELONGS_TO→Industry 관계를 즉시 적재할 수 있도록 준비.

- [ ] NICE 업종 코드 데이터 확보 (대분류 ~21개, 중분류 ~77개, 소분류 ~232개)
- [ ] Industry 노드 스키마 확정:
  | 속성 | 타입 | 비고 |
  |---|---|---|
  | `industry_id` | String (PK) | KSIC 코드 (예: "62", "62010") |
  | `name` | String | 업종명 (예: "소프트웨어 개발 및 공급업") |
  | `level` | String | "대분류" / "중분류" / "소분류" |
  | `parent_id` | String? | 상위 업종 코드 |
- [ ] Neo4j에 Industry 마스터 노드 적재 스크립트 준비
- [ ] Industry 노드 간 계층 관계 (PARENT_OF) 설정

**산출물**: 인프라 준비 완료 + PII 전략 확정 (또는 기본값 적용) + Organization 확장 스키마 선언(v6) + Industry 마스터 노드 준비(v6)

### 0-3.1 오케스트레이션 전략 **(v7 신설)**

> **v7 신설**: 파이프라인 간 의존성 관리, 대규모 배치 처리의 chunk 관리, 오케스트레이션 도구 선정을 위한 전략.

#### Pipeline DAG (의존성 그래프)

```
A (CompanyContext)  ──┐
                      ├──→ C (Graph 적재) ──→ D (MappingFeatures) ──→ E (서빙)
B (CandidateContext) ─┘
```

| 관계 | 설명 |
|---|---|
| **A ∥ B** | CompanyContext와 CandidateContext는 **독립 병렬 실행** 가능 — 입력 데이터가 다름 (JD vs 이력서) |
| **A+B → C** | Graph 적재는 양쪽 Context가 **모두 완료**된 후 실행 |
| **C → D** | MappingFeatures는 Graph 적재 완료 후 계산 (Vector Index 필요) |
| **D → E** | 서빙(BigQuery + MAPPED_TO)은 MappingFeatures 계산 완료 후 |

- **A와 B 병렬 실행 시 이점**: Phase 1 기준 CompanyContext(1~2주) + CandidateContext(3주)가 순차 실행 시 4~5주이지만, 병렬 시 3주로 단축 가능
- **부분 적재 전략**: A 완료 후 Organization/Vacancy 노드를 먼저 Graph에 적재하고, B 완료 후 Person/Chapter 노드를 추가 적재하는 것도 가능 (Phase 1에서 검증)

#### 오케스트레이션 도구 선정 기준 **(v7 신설)**

| 기준 | Prefect | Cloud Workflows (GCP) |
|---|---|---|
| **언어** | Python 네이티브 (데코레이터 기반) | YAML 기반 |
| **호스팅** | Self-hosted 가능 (Cloud Run 등) | 서버리스 (GCP 관리형) |
| **비용** | 오픈소스 무료 / Cloud 유료 ($250~/월) | $0.01/1,000 step execution |
| **DAG 지원** | 네이티브 (task dependency) | 순차/병렬 step 가능 |
| **모니터링** | 내장 UI (flow runs, 에러 로그) | Cloud Logging 연동 |
| **retry** | 내장 (per-task retry, exponential backoff) | 기본 retry 정책 |
| **장점** | Python 코드 재사용, 유연한 조건 분기 | GCP 통합, 관리 부담 없음 |
| **단점** | 인프라 관리 필요 (self-hosted) | 복잡한 로직 표현 제한 |

**권장**: Phase 0에서 두 도구 중 하나를 선정한다.
- DE가 Python 중심이면 → **Prefect** (self-hosted on Cloud Run, 무료)
- GCP 네이티브 통합 우선이면 → **Cloud Workflows** (서버리스)
- **Phase 0-4 의사결정에 "오케스트레이션 도구 선정" 추가**

#### Chunk 관리 전략 (500K 이력서) **(v7 신설)**

```
[Chunk 분할 + 상태 추적]

이력서 500K
    │
    ├─ 중복 제거 (§3.4) → canonical ~450K
    │
    ├─ 1,000건/chunk × 450 chunks로 분할
    │
    ├─ Chunk 상태 추적 (BigQuery 또는 Firestore)
    │   ├─ chunk_id: "chunk_001" ~ "chunk_450"
    │   ├─ status: PENDING → PROCESSING → COMPLETED / FAILED
    │   ├─ start_time, end_time
    │   ├─ success_count, fail_count
    │   └─ error_summary (실패 시)
    │
    ├─ 실패 chunk 재처리
    │   ├─ FAILED chunk 자동 재시도 (최대 2회)
    │   ├─ 2회 실패 시 → 건별 분해 후 개별 재시도
    │   └─ 개별 재시도도 실패 → dead-letter
    │
    └─ 진행률 모니터링
        ├─ 전체 chunk 완료율 (COMPLETED / total)
        ├─ 예상 완료 시간 (처리 속도 기반 추정)
        └─ Grafana 대시보드 반영
```

- **chunk 크기 1,000건 근거**: Batch API 1회 요청 크기(~3,000건)보다 작게 설정하여 실패 시 재처리 범위를 최소화
- **동시 처리 chunk 수**: 5~10개 (API quota와 메모리에 따라 조정)
- **예상 처리 시간**: 450 chunks / 10 동시 = ~45 batch × 6시간/batch = ~11일 (여유 포함 2~3주)

### 0-4. Phase 0 완료 의사결정

| 의사결정 | 판단 기준 | 옵션 |
|---|---|---|
| LLM 모델 선택 | PoC 추출 품질 + 비용 | Haiku / Flash / Sonnet |
| PII 전략 | 법무 확인 + 마스킹 영향 테스트 | API (마스킹) / On-premise / **기본값: 마스킹 API** (v5) |
| Embedding 모델 확정 검증 **(v6 변경)** | 한국어 분별력 검증 | **기본값: text-multilingual-embedding-002** / 검증 실패 시 Cohere / BGE-M3 |
| LLM 호출 전략 | 품질/비용 비교 | 경력별 개별 호출 / 이력서 전체 1회 호출 |
| 섹션 분할 전략 | 파싱 성공률 실측 (v5) | Rule 기반 / LLM fallback |
| Graph DB 플랜 | 예상 노드 수 | Free / Professional |
| MVP 범위 | 데이터 품질 | 전체 / 특정 직군만 |
| 이력서 중복 처리 | 중복률 실측 (v5) | 동일 candidate_id 최신 선택 / SimHash 기반 검토 큐 |
| 오케스트레이션 도구 **(v7 신설)** | DE 역량 + GCP 통합 요구 | Prefect (self-hosted) / Cloud Workflows |

---

## Phase 1: MVP 파이프라인 구축 (8~10주)

### 1-1. 전처리 모듈 (2주)

> **v3 변경**: v2의 1주 → 2주로 확장. HWP 파싱 + PII 마스킹 + 기술 사전 구축에 최소 2주 필요.

#### 이력서 파서
- [ ] PDF/DOCX/HWP → 정규화 텍스트 변환기
- [ ] 레이아웃 메타데이터 보존 (line_id, block_id, page)
- [ ] 섹션 분할기 (Rule-based: heading 패턴 + 위치)
  - **v5 추가**: Phase 0 파싱 성공률 < 50%이면 LLM 기반 섹션 분할 모듈 추가 개발
- [ ] 경력 블록 분리기 (회사 단위)
- [ ] PII 마스킹 모듈 (이름, 연락처, 주소)
- [ ] **v5 추가**: 이력서 중복 제거 모듈 (02 문서 §3.4)

#### JD 파서
- [ ] JD 텍스트 정규화
- [ ] 섹션 분할 (업무 소개, 자격 요건, 우대 사항, 기술 스택)

#### 공통
- [ ] 기술 사전 초기 구축 (2,000개 기술명 + alias)
- [ ] 회사 사전 초기 구축 (NICE 회사명 + alias)

### 1-2. CompanyContext 파이프라인 (1~2주)

#### 구현 순서

```python
class CompanyContextPipeline:
    def generate(self, job_id: str) -> CompanyContext:
        # 1. 입력 수집
        jd = self.jd_store.get(job_id)
        nice = self.nice_store.get(jd.company_id)

        # 2. company_profile (NICE Lookup)
        profile = self.extract_company_profile(nice)

        # 3. stage_estimate (Rule + LLM fallback)
        stage = self.extract_stage(nice, jd.text)

        # 4. vacancy + role_expectations (LLM 통합 프롬프트)
        vacancy, role_exp = self.llm_extract_vacancy_and_role(jd.text)

        # 5. operating_model (키워드 + LLM 보정)
        op_model = self.extract_operating_model(jd.text)

        # 6. 조합 + 메타데이터
        return CompanyContext(
            company_id=jd.company_id,
            job_id=job_id,
            company_profile=profile,
            stage_estimate=stage,
            vacancy=vacancy,
            role_expectations=role_exp,
            operating_model=op_model,
            structural_tensions=None,  # v1에서 null
            domain_positioning=self.extract_domain(jd.text, nice),
            _meta=self.build_meta(...)
        )
```

- [ ] CompanyContext JSON 스키마 Pydantic 모델 정의
- [ ] NICE Lookup 모듈
- [ ] stage_estimate Rule 엔진
- [ ] LLM 추출 프롬프트 (vacancy + role_expectations 통합)
- [ ] operating_model 키워드 엔진 + LLM 보정
- [ ] 통합 테스트 (JD 100건)
- [ ] Evidence 생성 모듈

### 1-3. CandidateContext 파이프라인 (3주)

> **v3 변경**: v2의 2~3주 → 3주 확정. 이력서 200건 통합 테스트 + Batch API 연동 포함.

#### 구현 순서

```python
class CandidateContextPipeline:
    def generate(self, resume_id: str) -> CandidateContext:
        # 1. 이력서 파싱 + 섹션 분할
        parsed = self.parser.parse(resume_id)
        sections = self.section_splitter.split(parsed)

        # 2. 경력 블록별 처리
        experiences = []
        for block in sections.career_blocks:
            # 2a. Rule 추출 (회사/직무/기간/기술)
            basic = self.rule_extract(block)

            # 2b. LLM 추출 (scope_type, outcomes, signals)
            enriched = self.llm_extract_experience(block, basic)

            # 2c. PastCompanyContext (NICE Lookup)
            pcc = self.build_past_company_context(
                basic.company, basic.period
            )
            enriched.past_company_context = pcc

            experiences.append(enriched)

        # 3. 전체 커리어 수준 (LLM 1회)
        role_evo = self.llm_extract_career_level(experiences)
        domain = self.llm_extract_domain_depth(experiences)

        # 4. WorkStyleSignals (v6 추가: experiment_orientation, collaboration_style)
        work_style = self.llm_extract_work_style(experiences)

        # 5. 조합
        return CandidateContext(
            candidate_id=...,
            resume_id=resume_id,
            experiences=experiences,
            role_evolution=role_evo,
            domain_depth=domain,
            work_style_signals=work_style,
            _meta=self.build_meta(...)
        )
```

- [ ] CandidateContext JSON 스키마 Pydantic 모델 정의
- [ ] Rule 추출 모듈 (날짜/회사/기술)
- [ ] LLM 추출 프롬프트 (Experience별)
- [ ] LLM 추출 프롬프트 (전체 커리어)
- [ ] PastCompanyContext NICE 역산 모듈
- [ ] **v6 추가**: WorkStyleSignals LLM 추출 프롬프트에 `experiment_orientation`, `collaboration_style` 항목 포함 **(v6 변경)**
  - `experiment_orientation`: 실험적 접근 vs 검증된 방법 선호 (EXPERIMENTAL / PROVEN / BALANCED)
  - `collaboration_style`: 독립 작업 vs 협업 중심 (INDEPENDENT / COLLABORATIVE / ADAPTIVE)
  - 이력서에서 관련 evidence_span 추출 포함
- [ ] 통합 테스트 (이력서 200건)
- [ ] Batch API 연동 (대량 처리)

### 1-4. Graph 적재 파이프라인 (2주)

> **v4 변경**: v3의 1주 → 2주로 확장. Entity Resolution + 대량 적재 전략 + 벤치마크 포함.

#### 1주차: 로더 + Entity Resolution
- [ ] CompanyContext → Neo4j 노드/엣지 로더
- [ ] CandidateContext → Neo4j 노드/엣지 로더
- [ ] **v5 추가**: Deterministic ID 생성 모듈 (02 문서 §4.6)
  - `generate_chapter_id()`, `generate_vacancy_id()`, `generate_outcome_id()` 구현
  - 모든 노드 CREATE → MERGE 전환 확인
- [ ] Organization Entity Resolution 모듈 (02 문서 §4.3)
  - 회사명 정규화 사전 구축 (NICE 기반 ~1,000개 + alias)
  - `resolve_org_id()` 함수: alias 사전 → NICE fuzzy match → fallback(name MERGE)
- [ ] Skill, Role 정규화 모듈

#### v6 신설: Industry 마스터 노드 적재 + 검증 **(v6 신설)**

> Phase 0-3에서 준비한 Industry 마스터 노드를 Neo4j에 적재하고,
> Organization→BELONGS_TO→Industry 관계를 NICE 업종 코드 기반으로 생성.

- [ ] Industry 마스터 노드 Neo4j 적재 실행 (KSIC 대분류/중분류/소분류)
- [ ] Organization→BELONGS_TO→Industry 관계 생성
  - NICE 업종 코드 → Industry `industry_id` 매핑
  - 매핑 실패 건 로깅 (fallback: 대분류만 매핑)
- [ ] Q5 쿼리 테스트: 특정 Industry 노드에 속한 Organization 목록 조회
  ```cypher
  MATCH (o:Organization)-[:BELONGS_TO]->(i:Industry {industry_id: "62"})
  RETURN o.name, i.name
  ```
- [ ] Industry 노드 수 + 관계 수 정합성 검증

#### v6 신설: Vacancy→REQUIRES_ROLE→Role 관계 생성 **(v6 신설)**

> v10 온톨로지에서 정의된 REQUIRES_ROLE 관계를 Phase 1-4에서 구현.
> Vacancy 노드에서 요구하는 Role을 명시적 관계로 연결.

- [ ] Vacancy→REQUIRES_ROLE→Role 관계 생성 로직 구현
  - CompanyContext의 vacancy.title → Role 노드 매핑 (Role 정규화 모듈 활용)
  - 매핑 실패 시 새 Role 노드 MERGE 생성
- [ ] REQUIRES_ROLE 관계 속성 설정:
  | 속성 | 타입 | 비고 |
  |---|---|---|
  | `min_years` | Integer? | JD에서 추출한 최소 경력 |
  | `scope_type` | String? | vacancy의 scope_type |
- [ ] 테스트: Vacancy→REQUIRES_ROLE→Role 경로 조회
  ```cypher
  MATCH (v:Vacancy)-[:REQUIRES_ROLE]->(r:Role)
  RETURN v.title, r.name, v.scope_type
  LIMIT 20
  ```
- [ ] 관계 생성률 측정 (목표: JD 100건 중 > 95% 관계 생성 성공)

#### 2주차: Vector Index + 벤치마크 + 적재 전략
- [ ] Vector Index 적재 (Chapter/Vacancy embedding)
  - embedding 텍스트 생성: scope_summary + outcomes + signals (02 문서 §4.5)
  - **v5 추가**: 빈 embedding 텍스트 skip 로직 (02 문서 §4.5)
- [ ] Cypher 쿼리 테스트 (v10 graph_schema.md의 Q1~Q5)
- [ ] **적재 벤치마크**: 1,000건 적재 시간 측정 → 500K 전체 적재 시간 추정
- [ ] **대량 적재 전략 결정** (02 문서 §4.4)
  - LOAD CSV + APOC batch vs Cypher MERGE 성능 비교
  - 초기 적재 vs 증분 적재 파이프라인 분리
- [ ] **v5 추가**: Idempotency 테스트 — 동일 데이터 2회 적재 후 노드/엣지 수 변화 없음 확인

### 1-5. MappingFeatures 계산 (1주)

- [ ] **Candidate Shortlisting** (02 문서 §5.0)
  - Rule pre-filter (industry, tech_stack, 경력연수)
  - Neo4j Vector Index 기반 ANN search (top-500)
- [ ] v10 mapping_features.md 로직 구현
  - stage_match
  - vacancy_fit
  - domain_fit (embedding cosine)
  - culture_fit (대부분 INACTIVE)
  - role_fit
- [ ] **v6 추가**: role_fit 구현에 ScopeType→Seniority 변환 함수 통합 **(v6 변경)**
  - `ic_to_seniority(scope_type: str) -> str`: IC scope_type → seniority 레벨 매핑
    - IC_INDIVIDUAL → JUNIOR/MID, IC_TEAM_LEAD → SENIOR, IC_DOMAIN_LEAD → STAFF/PRINCIPAL
  - `get_candidate_seniority(experiences: list) -> str`: 최근 경력 기반 candidate seniority 산출
  - role_fit 계산 시 vacancy 요구 seniority와 candidate seniority 비교 반영

#### v6 신설: MAPPED_TO 관계 Graph 적재 + 검증 **(v6 신설)**

> MappingFeatures 계산 결과를 Graph에 MAPPED_TO 관계로 적재.
> Candidate→MAPPED_TO→Vacancy 관계를 통해 Graph 기반 추천 쿼리 활성화.

- [ ] MAPPED_TO 관계 생성 로직 구현
  - overall_match_score 기준 상위 매핑만 적재 (threshold: score > 0.3)
  - 관계 속성:
    | 속성 | 타입 | 비고 |
    |---|---|---|
    | `overall_score` | Float | overall_match_score |
    | `stage_match` | Float | stage_match 피처 값 |
    | `vacancy_fit` | Float | vacancy_fit 피처 값 |
    | `domain_fit` | Float | domain_fit 피처 값 |
    | `role_fit` | Float | role_fit 피처 값 |
    | `mapped_at` | DateTime | 매핑 생성 시점 |
- [ ] MAPPED_TO 적재 후 검증 쿼리:
  ```cypher
  MATCH (c:Candidate)-[m:MAPPED_TO]->(v:Vacancy)
  RETURN c.candidate_id, v.title, m.overall_score
  ORDER BY m.overall_score DESC
  LIMIT 20
  ```
- [ ] MAPPED_TO 관계 수 = BigQuery MappingFeatures 레코드 수 (threshold 이상) 정합성 확인

- [ ] overall_match_score 계산
- [ ] BigQuery 테이블 생성 + 적재
- [ ] 매핑 50건 수동 검증

**Phase 1 산출물**: E2E 파이프라인 (JD 100건 + 이력서 1,000건 + Graph + MappingFeatures)

---

## Phase 2: 확장 + 최적화 (4~5주)

### 2-1. 전체 데이터 처리 (2~3주)

- [ ] **v5 추가**: 이력서 중복 제거 실행 (02 문서 §3.4)
  - 동일 candidate_id 최신 선택
  - SimHash 유사 이력서 검토 (Phase 0 중복률에 따라)
- [ ] Batch 처리 인프라 구축
  - 이력서 500K × Batch API (Haiku), 1,000건/chunk 단위
  - JD 10K × Batch API
  - 동시 배치 수: 5~10개 (API quota 확인 후 조정)
- [ ] 에러 핸들링 인프라
  - Dead-letter 큐 구축 (처리 실패 건 관리)
  - 에러율 모니터링 (가정: 전체 2-5% 실패 예상)
  - 자동 재시도 (일 1회) + 2회 실패 시 수동 검토 전환
- [ ] 처리 모니터링 대시보드 (**Grafana + BigQuery** 기반)
  - 진행률, 에러율, LLM fallback 비율
  - 피처별 ACTIVE/INACTIVE 비율
  - 파이프라인 단계별 처리 시간/비용 추적
  - 대안: Cloud Monitoring (GCP) 또는 Datadog
- [ ] Neo4j AuraDB Professional 전환 (필요 시)
- [ ] BigQuery 전체 적재

### 2-2. 품질 평가 (1주, 2-1과 병행)

#### Gold Test Set 구축
- [ ] 전문가 2인 × 200건 독립 annotation
- [ ] Inter-annotator agreement (Cohen's κ) 측정
- [ ] 직무/경력/문서형식별 층화 추출

#### v6 추가: 사전 검정력 분석 (Power Analysis) **(v6 신설)**

> v10 05_evaluation_strategy.md §1.1 참조.
> 50건 수동 평가의 통계적 신뢰성을 사전에 판단하기 위해 검정력 분석 수행.

- [ ] 사전 검정력 분석 (power analysis) 실행
  - 목표 검정력 (1-β): 0.80
  - 유의 수준 (α): 0.05
  - 효과 크기: Cohen's d (중간 이상, d ≥ 0.5)
  - 산출: 50건 평가로 검출 가능한 최소 효과 크기 확인
- [ ] **적응적 표본 크기 결정 프로토콜**:
  1. 50건 평가 완료 후 관측된 효과 크기 산출
  2. Cohen's d < 0.3 (작은 효과)이면 → 표본 100건으로 확대 여부 결정
  3. Cohen's d ≥ 0.5 (중간 효과)이면 → 50건으로 통계적 결론 유효
- [ ] **Cohen's d 효과 크기를 Human eval 상관관계(r)와 함께 공동 주 판단 기준으로 사용** **(v6 변경)**

#### 평가 지표 측정
| 지표 | 대상 | 최소 기준 | 목표 |
|---|---|---|---|
| scope_type 분류 정확도 | CandidateContext | > 70% | > 80% |
| outcome 추출 F1 | CandidateContext | > 55% | > 70% |
| situational_signal 분류 F1 | CandidateContext | > 50% | > 65% |
| vacancy scope_type 정확도 | CompanyContext | > 65% | > 80% |
| stage_estimate 정확도 | CompanyContext | > 75% | > 85% |
| 피처 1개+ ACTIVE 비율 | MappingFeatures | > 80% | > 90% |
| Human eval 상관관계 | MappingFeatures (50건) | r > 0.4 | r > 0.6 |
| Human eval 효과 크기 **(v6 신설)** | MappingFeatures (50건) | Cohen's d ≥ 0.5 | Cohen's d ≥ 0.8 |
| 처리 시간 (1건 매핑) | E2E | < 30초 | < 10초 |

### 2-3. ML Knowledge Distillation (1~2주, 선택적 — Phase 2 품질 평가 결과에 따라 진행 여부 결정)

Phase 1에서 수집된 LLM 추출 결과를 silver label로 활용.

- [ ] scope_type 분류기 학습 (KLUE-BERT, 5-class)
  - Silver label: Phase 1 추출 결과 중 confidence > 0.7인 것
  - 목표: F1 > 75% → LLM 대체
- [ ] seniority 분류기 학습 (KLUE-BERT, 6-class)
  - 목표: F1 > 80% → LLM 대체
- [ ] Confidence 기반 라우팅: ML confidence > 0.85 → ML 사용, 아래 → LLM fallback
- [ ] 비용 절감 효과 실측

### 2-4. DS/MLE 서빙 인터페이스 (1주)

- [ ] BigQuery 테이블 스키마 확정 (v10 mapping_features.md 참조)
- [ ] DS/MLE 소비자 인터뷰 → 요구사항 반영
- [ ] SQL 예시 쿼리 작성 + 문서화
- [ ] Context on/off ablation 테스트 환경 구축

**Phase 2 산출물**: 전체 데이터 처리 완료 + 품질 리포트 + 서빙 인터페이스

---

## 운영 전략: 롤백 / 재처리 / 증분 처리

> **v3 신설**: v2 리뷰에서 지적된 운영 관점 부재를 보강.

### 롤백 및 재처리 전략

프롬프트 변경 등으로 재추출이 필요한 경우:

```
[재처리 시나리오]
1. 프롬프트 변경 → 특정 필드만 재추출
   → CandidateContext JSON에서 해당 필드만 업데이트
   → Graph: deterministic ID + MERGE로 자동 upsert (v5 — DELETE 불필요)

2. 스키마 변경 → 전체 재처리
   → 새 Graph DB 인스턴스에 적재 (blue-green 배포)
   → 검증 후 라우팅 전환

3. 데이터 품질 이슈 → 대상 건 재처리
   → item_id 기반 selective 재처리
   → 기존 Context JSON 백업 후 덮어쓰기
   → Graph: deterministic ID + MERGE로 자동 upsert (v5)
```

- Context JSON은 GCS/S3에 **버전 관리하여 보관** (이전 버전 복원 가능)
- Graph 노드에 `extracted_at`, `prompt_version` 메타데이터 부착
- 재처리 시 `prompt_version`이 다른 노드만 대상으로 필터링
- **v5 변경**: Deterministic ID + MERGE 패턴으로 재처리 시 별도 DELETE 단계 불필요

### 프롬프트 버전 관리

> **v4 신설**: v3 리뷰에서 지적된 프롬프트 관리 전략 부재를 보강.

```
[프롬프트 관리 체계]
prompts/
├─ experience_extract_v1.txt    # CandidateContext Experience 추출
├─ career_level_v1.txt          # CandidateContext 전체 커리어 추출
├─ vacancy_role_v1.txt          # CompanyContext vacancy + role 추출
└─ CHANGELOG.md                 # 프롬프트 변경 이력

[변경 절차]
1. 새 프롬프트 파일 작성 (v2 suffix)
2. 50건 고정 테스트셋(Golden Set)으로 회귀 테스트 실행
   - 품질 지표 변화 < 5%이면 자동 승인
   - 5% 이상 변화 시 MLE 수동 검토
3. 승인 후 프롬프트 배포 + prompt_version 메타데이터 갱신
4. 재처리 대상 결정: prompt_version이 다른 건만 선택적 재처리
```

- 프롬프트 파일은 프로젝트 Git 리포에 포함 (코드와 동일 버전 관리)
- Golden Set: Phase 0 PoC에서 사용한 50건 재활용 (고정, 변경하지 않음)

### 증분 처리 (Incremental Pipeline)

최초 500K 처리 후 신규/갱신 이력서 유입 시:

```
[증분 처리 플로우]
신규 이력서/JD 유입
    │
    ├─ 변경 감지 (파일 hash 비교 또는 DB updated_at)
    │
    ├─ 신규 건: 기존 파이프라인 동일하게 처리
    │   └─ v5: deterministic ID로 MERGE → 중복 노드 방지
    │
    ├─ 갱신 건: 기존 Context JSON 조회 → diff 계산
    │   ├─ 변경된 경력 블록만 재추출 (비용 절감)
    │   └─ Graph: deterministic chapter_id로 MERGE → 자동 upsert
    │
    └─ 삭제 건: Graph에서 관련 노드/엣지 soft-delete
        └─ MappingFeatures에서 해당 쌍 제외
```

- **처리 주기**: 일 1회 배치 (신규 유입량에 따라 조정)
- **예상 일일 유입량**: 100~1,000건 (비즈니스 확인 필요)
- **비용**: 일 1,000건 × $0.00115/건 = ~$1.15/일

---

## 테스트 전략

> **v3 신설**: v2 리뷰에서 지적된 테스트 전략 부재를 보강.

| 테스트 레벨 | 대상 | 기준 | 시점 |
|---|---|---|---|
| **Unit** | Rule 추출 모듈 (정규식, 기술사전) | 정규식 커버리지 > 90% | Phase 1-1 |
| **Integration** | 단일 이력서/JD E2E | 파싱→추출→Graph 적재 성공 | Phase 1-2, 1-3 |
| **Idempotency** | 동일 입력 2회 적재 | 노드/엣지 수 변화 없음 (v5 추가) | Phase 1-4 |
| **Batch** | 1,000건 배치 처리 | 에러율 < 5%, 처리시간 < 2시간 | Phase 1 말 |
| **Quality** | 50건 수동 평가 | scope_type 정확도 > 70% | Phase 2-2 |
| **Power** **(v6 신설)** | 50건 수동 평가 통계적 검정력 | Cohen's d ≥ 0.5 | Phase 2-2 |
| **Scale** | 500K 전체 처리 | 에러율 < 3%, 배치 완료 < 3일 | Phase 2-1 |
| **Regression** | 모델/프롬프트 변경 시 | 50건 회귀 테스트, 품질 지표 변화 < 5% | 운영 단계 |

---

## Phase 3: 고도화 (지속)

> **v6 변경**: Phase 3을 크롤링 파이프라인 중심으로 대폭 확장. v10 06_crawling_strategy.md의 4 Phase 실행 계획을 반영.

### 3-1. 크롤링 파이프라인 (7주) **(v6 변경 — 대폭 확장)**

> v5의 "데이터 소스 확장" 항목을 v10 06_crawling_strategy.md의 4 Phase 실행 계획 기반으로
> 구체적 크롤링 파이프라인으로 확장.

#### Phase C1: 크롤러 인프라 구축 (2주)

> v10 06_crawling_strategy.md Phase C1 참조.

- [ ] Cloud Run Job 기반 크롤러 프레임워크 구축
  - 크롤링 워커 (Python, httpx + BeautifulSoup4)
  - GCS 원본 HTML 저장 (버킷: `gs://{project}-crawl-raw/`)
  - BigQuery 크롤링 메타데이터 테이블 (URL, status, crawl_time, content_hash)
- [ ] 크롤링 스케줄러 (Cloud Scheduler → Pub/Sub → Cloud Run Job)
- [ ] Rate limiter + robots.txt 준수 모듈
- [ ] LLM 추출 파이프라인 (Gemini 2.0 Flash 기반)
  - HTML → 정제 텍스트 → LLM 구조화 추출
  - 추출 대상: product_description, market_segment, team_size, tech_stack
- [ ] GCS → BigQuery → Neo4j 적재 파이프라인 프레임워크
- [ ] 크롤링 품질 모니터링 대시보드 (BigQuery 기반)

#### Phase C2: T3 홈페이지 크롤링 (2주)

> v10 06_crawling_strategy.md Phase C2 참조.
> Organization의 product_description, market_segment 등 CompanyContext 보강을 위한 홈페이지 크롤링.

- [ ] 크롤링 대상 URL 수집 (NICE DB 홈페이지 필드 + 수동 보완)
- [ ] 필수 페이지 (P1~P3) 크롤링:
  | 우선순위 | 페이지 | 추출 대상 | 비고 |
  |---|---|---|---|
  | P1 | 메인 페이지 | product_description, 슬로건 | 필수 |
  | P2 | 회사 소개 / About | market_segment, team_size | 필수 |
  | P3 | 채용 / Careers | tech_stack, 문화 키워드 | 필수 |
- [ ] 선택 페이지 (P4~P6) 크롤링:
  | 우선순위 | 페이지 | 추출 대상 | 비고 |
  |---|---|---|---|
  | P4 | 블로그 / 뉴스룸 | 기술 블로그 → tech_stack 보강 | 선택 |
  | P5 | 제품 / 서비스 | product_description 상세 | 선택 |
  | P6 | 투자자 관계 (IR) | funding_round 보강 | 선택 |
- [ ] LLM 추출 (Gemini 2.0 Flash) 실행
  - 페이지별 구조화 추출 → JSON 출력
  - 추출 결과 → Organization 노드 속성 업데이트 (MERGE)
- [ ] `crawl_quality` 스코어 산출 (추출 필드 충족률 기반)
- [ ] Neo4j Organization 노드 속성 업데이트 (product_description, market_segment, crawl_quality, last_crawled_at)

#### Phase C3: T4 뉴스 크롤링 (2주)

> v10 06_crawling_strategy.md Phase C3 참조.
> structural_tensions 활성화 + CompanyContext 보강을 위한 뉴스 크롤링.

- [ ] 네이버 뉴스 API 연동 (검색 API + 본문 추가 크롤링)
  - 검색 쿼리: 회사명 + 키워드 조합
  - 기간: 최근 1년
- [ ] 뉴스 카테고리별 크롤링:
  | 카테고리 | 코드 | 추출 대상 | 비고 |
  |---|---|---|---|
  | N1: 채용/인사 | HR | 채용 규모, 조직 변화 | structural_tensions |
  | N2: 투자/재무 | FIN | funding_round, 매출 | stage_estimate 보강 |
  | N3: 사업/전략 | BIZ | 사업 확장, 파트너십 | domain_positioning |
  | N4: 기술/제품 | TECH | 신제품, 기술 전환 | tech_stack 보강 |
  | N5: 조직문화 | CULT | 원격근무, 복지 | operating_model 보강 |
- [ ] **v6 추가**: 8-type taxonomy 기반 structural_tensions 추출 활성화 **(v6 변경)**
  - LLM (Gemini 2.0 Flash) 기반 뉴스 기사에서 structural_tensions 추출
  - 8-type taxonomy: RAPID_GROWTH / PIVOT / RESTRUCTURING / ACQUISITION / IPO_PREP / COST_CUTTING / LEADERSHIP_CHANGE / CULTURAL_SHIFT
  - 추출 결과 → CompanyContext.structural_tensions 필드 업데이트
  - tension별 evidence (뉴스 URL + 발행일 + 핵심 문장) 보존
- [ ] 뉴스 본문 추가 크롤링 모듈 (네이버 뉴스 API는 요약만 제공)
- [ ] 중복 뉴스 필터링 (제목 SimHash 기반)

#### Phase C4: 데이터 병합 + 품질 검증 (1주)

> v10 06_crawling_strategy.md Phase C4 참조.

- [ ] 홈페이지 크롤링 결과 + 뉴스 크롤링 결과 → CompanyContext 보강 병합
  - product_description: 홈페이지(P1) 우선, 뉴스(N3) 보조
  - market_segment: 홈페이지(P2) 우선
  - structural_tensions: 뉴스(N1~N5) 기반
- [ ] facet score 병합 로직
  - 기존 operating_model facets + 크롤링 보강 facets 가중 평균
  - 크롤링 소스 confidence 반영 (홈페이지 > 뉴스)
- [ ] 크롤링 전/후 CompanyContext 품질 비교 (50건 샘플)
  - 측정: ACTIVE 피처 비율 변화, stage_estimate 정확도 변화
- [ ] Neo4j 최종 정합성 검증
  - Organization 노드 속성 완성도 (null 비율)
  - Industry→Organization 관계 커버리지

### 3-2. Company-to-Company 관계 로드맵 **(v6 신설)**

> v10 A5 로드맵 표 참조. Phase 3 크롤링 데이터를 활용한 Company-to-Company 관계 구축 로드맵.

| 관계 | 도입 버전 | 데이터 소스 | 비고 |
|---|---|---|---|
| `INVESTED_BY` | v1.1 | TheVC API | 투자사→피투자사 관계, latest_funding_round 보강 |
| `COMPETES_WITH` | v2 | 뉴스(N3) + 수동 태깅 | 동일 market_segment 내 경쟁 관계 |
| `ACQUIRED` | v2 | 뉴스(N3) | 인수/합병 관계 |
| `PARTNERED_WITH` | v2 | 뉴스(N3) | 전략적 파트너십 |

- [ ] TheVC API 연동 조사 + 접근 권한 확인
- [ ] INVESTED_BY 관계 스키마 설계 (속성: round, amount, date)
- [ ] v2 관계 (COMPETES_WITH, ACQUIRED, PARTNERED_WITH) 추출 파이프라인 설계 (Phase C3 뉴스 데이터 활용)

### 3-3. GraphRAG 활용 확장

- [ ] Community Detection (유사 기업/후보 군집)
- [ ] Graph-based Recommendation (path 기반 추천)
- [ ] GraphRAG vs baseline ablation
  - baseline: LLM + Vector DB만으로 MappingFeatures 생산
  - GraphRAG: Graph traversal + Vector 하이브리드
  - 측정: MappingFeatures 품질 차이

### 3-4. 운영 고도화

- [ ] Active Learning 루프 (LLM fallback 케이스 재학습)
- [ ] operating_model 8 facets 확장 (v10 로드맵)
- [ ] Closed-loop Enrichment (후보 직접 질문)
- [ ] 실시간 API 서빙 (BigQuery → REST)

---

## 타임라인 요약

> **v7 변경**: Phase 1에 +2주 버퍼를 추가하여 타임라인을 현실화. Pre-Phase 0 추가.

```
Pre-Phase 0: 사전 준비 (NICE DB 접근 확보 등) — Phase 0 시작 2주 전까지 (v7 신설)

Week 1-2:   Phase 0-1, 0-2 (데이터 탐색 + 인프라)
Week 2-3:   Phase 0-2, 0-3 (LLM PoC + 파싱 PoC + 인프라 셋업 + 오케스트레이션 도구 선정)
Week 3-4:   Phase 0-4 의사결정 + Phase 1-1 시작 (전처리)

Week 4-6:   Phase 1-1 (전처리 모듈 + 중복 제거 — 2주)
Week 6-8:   Phase 1-2 (CompanyContext 파이프라인)
Week 8-12:  Phase 1-3 (CandidateContext 파이프라인 — 4주, v7 변경: +1주 버퍼)
Week 12-14: Phase 1-4 (Graph 적재 + Entity Resolution + Industry 노드 + REQUIRES_ROLE + Idempotency — 2주)
Week 14-16: Phase 1-5 (MappingFeatures + MAPPED_TO + Candidate Shortlisting + 통합 테스트 — 2주, v7 변경: +1주 버퍼)

Week 16-19: Phase 2-1 (전체 데이터 처리 — 3주)
Week 17-18: Phase 2-2 (품질 평가 + power analysis) — 2-1과 병행
Week 18-19: Phase 2-4 (DS/MLE 서빙 인터페이스)
Week 19-22: Phase 2-3 (ML Distillation — 선택적, 점선)

Week 22-24: Phase 3 C1 (크롤러 인프라 구축 — 2주)
Week 24-26: Phase 3 C2 (T3 홈페이지 크롤링 — 2주)
Week 26-28: Phase 3 C3 (T4 뉴스 크롤링 + structural_tensions — 2주)
Week 28-29: Phase 3 C4 (데이터 병합 + 품질 검증 — 1주)
Week 29+:   Phase 3-2~3-4 (Company 관계, GraphRAG, 운영 고도화, 지속)
```

**총 MVP 완성**: ~18~22주 (Phase 0~2, ML Distillation 제외 시 ~17~19주) **(v7 변경: 16~19주에서 현실화)**
**첫 동작 데모**: ~16주 (Phase 0~1 완료 시점) **(v7 변경: 14주에서 현실화)**
**크롤링 파이프라인 완료**: ~29주 (Phase 3 C1~C4)

> **v7 타임라인 변경 근거**:
> - Phase 1-3 (CandidateContext): 3주 → 4주. LLM 파싱 실패 전략(02 문서 §8.3)의 3-tier retry 구현 + chunk 관리 인프라 구축에 추가 시간 필요
> - Phase 1-5 (MappingFeatures): 1주 → 2주. MAPPED_TO 적재 + 통합 E2E 테스트 + chunk 상태 추적 인프라에 추가 시간 필요
> - 전체: 16~19주 → 18~22주 (+2주 버퍼). CandidateContext 파이프라인이 전체 비용/복잡도의 핵심이므로 여유 확보

> **v5 일정 영향**: 추가 작업(파싱 성공률 측정, 이력서 중복 제거, Idempotency 테스트)은 기존 Phase 기간 내 흡수 가능하므로 전체 타임라인 변경 없음. 단, Phase 0에서 파싱 성공률이 50% 미만이면 LLM 섹션 분할 모듈 추가로 Phase 1-1이 0.5~1주 연장될 수 있다.
>
> **v6 일정 영향**: Phase 0~2 타임라인 변경 없음. Industry 노드, REQUIRES_ROLE, MAPPED_TO, ScopeType→Seniority 변환, WorkStyleSignals 항목은 기존 Phase 기간 내 흡수 가능. Phase 3은 크롤링 파이프라인 4단계(7주)가 구체화되어 Week 19~26으로 명시.
>
> **v7 일정 영향 (v7 변경)**: Phase 1에 +2주 버퍼 추가 (16~19주 → 18~22주). LLM 파싱 실패 전략, chunk 관리 인프라, 오케스트레이션 도구 셋업에 소요되는 추가 시간을 반영. Pre-Phase 0에서 NICE DB 접근 미확보 시 Phase 0 시작이 2~4주 지연될 수 있음.

---

## 핵심 의사결정 포인트

| 시점 | 의사결정 | 판단 기준 | 옵션 |
|---|---|---|---|
| Pre-Phase 0 **(v7 신설)** | NICE DB 접근 | 계약 상태 + API 접근 키 | 기존 계약 / 신규 계약 / 공개 데이터 대체 |
| Phase 0 완료 | 오케스트레이션 도구 **(v7 신설)** | DE 역량 + GCP 통합 요구 | Prefect (self-hosted) / Cloud Workflows |
| Phase 0 완료 | LLM 모델 선택 | PoC 추출 품질 | Haiku / Flash / Sonnet / **Sonnet fallback (시나리오 A', v7)** |
| Phase 0 완료 | PII 전략 | 법무 확인 + 마스킹 영향 테스트 | API / On-premise / **기본값: 마스킹 API** |
| Phase 0 완료 | Embedding 모델 확정 검증 **(v6 변경)** | 한국어 분별력 검증 | **기본값: text-multilingual-embedding-002** / 실패 시 Cohere / BGE-M3 |
| Phase 0 완료 | LLM 호출 전략 | 품질/비용 비교 (10건) | 경력별 개별 / 이력서 전체 1회 |
| Phase 0 완료 | 섹션 분할 전략 (v5) | 파싱 성공률 실측 | Rule / LLM fallback |
| Phase 0 완료 | MVP 범위 | 데이터 품질 | 전체 직군 / 특정 직군 |
| Phase 1 중간 | 프롬프트 전략 | 추출 품질 추이 | 단일 vs 분리 프롬프트 |
| Phase 2 평가 후 | ML Distillation 투자 | scope_type ML F1 | ML 투자 / LLM 유지 |
| Phase 2 평가 후 | 평가 표본 확대 **(v6 신설)** | Cohen's d 효과 크기 | 50건 유지 (d ≥ 0.5) / 100건 확대 (d < 0.3) |
| Phase 2 평가 후 | Graph DB 스케일 | 노드 수 / 성능 | Free → Professional |
| Phase 2 평가 후 | MappingFeatures 조정 | human eval r값 + Cohen's d | weight 재조정 / 피처 재설계 |
| Phase 2 완료 | GraphRAG 투자 | ablation 결과 | Full GraphRAG / Vector only |
| Phase 3 C2 완료 | 선택 페이지 크롤링 **(v6 신설)** | P1~P3 커버리지 | P4~P6 추가 / P1~P3만 유지 |
