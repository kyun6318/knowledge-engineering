# 실행 계획 v9 — v11 온톨로지 기반 (DB 기반 재설계)

> v11 온톨로지의 CompanyContext + CandidateContext + Graph + MappingFeatures를
> 구축하기 위한 단계별 실행 계획.
>
> 작성일: 2026-03-08 (v2 기반)
> 개정일: 2026-03-08 (v6 — v10 정합: Industry 노드, Embedding 확정 검증, REQUIRES_ROLE/MAPPED_TO, 크롤링 파이프라인, power analysis)
> 개정일: 2026-03-08 (v7 — 오케스트레이션 전략 신설, 타임라인 현실화 18~22주, Pre-Phase 0 NICE DB 접근)
> 개정일: 2026-03-09 (v8 — DB 기반 파이프라인 재설계: 전처리 제거, DB 커넥터 전환, 타임라인 13~16주)
> 개정일: 2026-03-10 (v9 — v11 온톨로지 정합: 3-Tier 비교 전략 통일, compare_majors/compute_skill_overlap 하이브리드 추가, 전공 threshold 0.75)

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
Phase 0: 기반 구축 + PoC (2~3주) — v8 변경: 3~4주에서 단축
    ├─ DB 프로파일링 + 인프라 셋업 (v8 변경: 파일 탐색 → DB 프로파일링)
    ├─ LLM 추출 품질 PoC (50건)
    └─ 의사결정: 모델 선택, PII 전략

Phase 1: MVP 파이프라인 (6~8주) — v8 변경: 8~10주에서 단축
    ├─ DB 커넥터 + 데이터 매핑 + 3-Tier 비교 전략 모듈 (1~2주) — v9 변경: 3-Tier 통일
    ├─ CompanyContext 파이프라인 (1~2주)
    ├─ CandidateContext 파이프라인 (2주) — v8 변경: 3주(+1주 버퍼) → 2주
    ├─ Graph 적재 + Vector Index + Entity Resolution (1~2주) — v8 변경: 2주 → 1~2주
    └─ MappingFeatures + Candidate Shortlisting (1주)

Phase 2: 확장 + 최적화 (3~4주) — v8 변경: 4~5주에서 단축
    ├─ 전체 데이터 처리 (2~3주)
    ├─ 품질 평가 + 캘리브레이션 (1주, 병행)
    ├─ DS/MLE 서빙 인터페이스 (1주)
    └─ ML Knowledge Distillation (선택적, 1~2주)

Phase 3: 고도화 (지속)
    ├─ 크롤링 파이프라인 (7주)
    ├─ Company-to-Company 관계 로드맵
    ├─ GraphRAG vs baseline ablation
    └─ Active Learning
```

---

## 사전 준비 (Pre-Phase 0) — Blocking Dependencies

> Phase 0 시작 전 반드시 확보해야 하는 외부 의존성.

### resume-hub / job-hub / code-hub DB 접근 확보 **(v8 신설, Blocking)**

- [ ] 3개 DB 읽기 접근 권한 확인
  - resume-hub: Career, Skill, Education, CareerDescription, SelfIntroduction, SiteUserMapping 테이블
  - job-hub: job, overview, requirement, work_condition, skill 테이블
  - code-hub: common_code (HARD_SKILL, SOFT_SKILL, JOB_CLASSIFICATION, INDUSTRY) 테이블
- [ ] 리드 레플리카 vs API 호출 방식 결정
  - 리드 레플리카 직접 접근이 이상적 (대량 조회 성능)
  - API only인 경우 배치 사이즈/동시성 제약 확인
- [ ] JSONB 필드 스키마 확인 (overview.descriptions, requirement.careers)
  - 50건 샘플로 실제 JSON 구조 확인
- [ ] 데이터 커버리지 확인
  - BRN null 비율 (A19 검증)
  - workDetails null 비율 (A20 검증)
  - Skill.code null 비율 (A22 검증)
  - 전체 이력서 적재 상태 (A23 검증)

**판정 기준**:
- 3개 DB 접근이 Phase 0 시작 2주 전까지 확보되지 않으면 → v7 방식(파일 파싱) fallback 검토
- 일부 DB만 접근 가능한 경우 → 접근 가능 DB는 v8 방식, 불가 DB는 v7 방식 혼용

### NICE DB 접근 확보 (v7 유지)

- [ ] NICE DB 접근 계약 상태 확인
- [ ] NICE DB 테스트 접근 권한 확보
- [ ] NICE 업종코드 마스터 데이터 확보 가능 여부 확인

---

## Phase 0: 기반 구축 + PoC (2~3주) **(v8 변경: 3~4주에서 단축)**

### 0-1. DB 프로파일링 (1주) **(v8 변경: 파일 탐색 → DB 프로파일링)**

> v7의 "이력서 파일 형식 분포 조사, OCR 비율, 평균 파일 크기" 등이 **전체 제거**됨.
> 대신 DB 필드 커버리지와 품질을 프로파일링한다.

#### resume-hub 프로파일링
- [ ] 전체 이력서(Career) 레코드 수 확인 (A2 검증)
- [ ] Career 엔티티 평균 개수 / 이력서 (A4 검증)
- [ ] 필드 커버리지 프로파일링:

| 필드 | 쿼리 | 가정 | 비고 |
|---|---|---|---|
| Career.businessRegistrationNumber null 비율 | `SELECT COUNT(*) FILTER (WHERE brn IS NULL) / COUNT(*) FROM career` | 40% (A19) | NICE 매칭률 핵심 |
| Career.workDetails null 비율 | 동일 패턴 | 20% (A20) | LLM 입력 품질 |
| CareerDescription.description null 비율 | 동일 패턴 | — | workDetails fallback |
| SelfIntroduction.description null 비율 | 동일 패턴 | — | LLM 보조 입력 |
| Skill.code null 비율 | `SELECT COUNT(*) FILTER (WHERE code IS NULL) / COUNT(*) FROM skill` | 10% (A22) | 코드 매핑 커버리지 |
| Career.positionGradeCode null 비율 | 동일 패턴 | — | scope_type 힌트 |
| Career.positionTitleCode null 비율 | 동일 패턴 | — | role 매핑 |

- [ ] SiteUserMapping 기반 중복률 확인
  - 동일 siteUserId가 여러 사이트에서 매핑되는 비율
- [ ] 무작위 50건 샘플링 → 텍스트 필드 품질 수동 확인
  - workDetails 평균 길이, 구조 패턴
  - CareerDescription 평균 길이

#### job-hub 프로파일링
- [ ] 전체 JD(job) 레코드 수 확인 (A1 검증)
- [ ] overview.descriptions JSONB 구조 분석 (50건 샘플)
  - 평균 길이 (A21 검증)
  - JSON 키 일관성 확인
- [ ] requirement.careers JSONB 구조 분석
- [ ] skill 테이블 → code-hub 매핑률 확인

#### code-hub 프로파일링
- [ ] HARD_SKILL 코드 수 + resume-hub Skill.code 커버리지
- [ ] JOB_CLASSIFICATION 코드 수 + 직무명 커버리지
- [ ] INDUSTRY 코드 계층 구조 확인

#### 비표준 값 프로파일링 **(v9 변경: 3-Tier 구조에 맞게 재구성)**
- [ ] **Tier 1 대상** (대학교, 회사명, 산업 코드): 변형 수 + alias 사전 커버리지 확인
  - `SELECT name, COUNT(*) FROM education GROUP BY LOWER(TRIM(name)) HAVING COUNT(DISTINCT name) > 1`
- [ ] **Tier 2 대상** (스킬): 비표준 비율 측정 + code-hub CI 매칭률 + synonyms 매칭률 확인
  - `SELECT name, COUNT(*) FROM skill GROUP BY LOWER(TRIM(name)) HAVING COUNT(DISTINCT name) > 1`
- [ ] **Tier 3 대상** (전공, 직무명): 변형 수 측정 (정규화하지 않으므로 임베딩 유사도 분포 확인)
  - 전공 비표준 비율 측정: Education.major 변형 수
  - 직무 비표준 비율 측정: Career.positionTitle 변형 수
- [ ] 3-Tier 비교 전략 threshold 검증을 위한 50건 샘플 수동 매핑 (gold set)
  - 스킬 20건 (Tier 2: CI+synonyms+임베딩), 전공 15건 (Tier 3: 임베딩 전용), 직무 15건 (Tier 3: 임베딩 전용)
  - 각 건에 대해 canonical 엔티티 수동 지정 → threshold 최적값 도출
  - **v9 변경**: 전공 threshold 기본값 0.75 (v11.1 §1.5 정합)

#### NICE 데이터 분석
- [ ] NICE DB 접근 확인 + 필드 매핑
- [ ] BRN 기반 NICE 매칭 테스트 (100건) (A5 검증)
  - BRN 있는 건: 직접 매칭 성공률
  - BRN 없는 건: 회사명 fuzzy match 성공률

**산출물**: DB 프로파일 리포트 — 가정 A1~A5, A19~A26 검증 + 데이터 커버리지 리포트 + 비표준 값 프로파일 리포트 **(v8.1 변경)**

### 0-2. LLM 추출 품질 PoC (1~2주)

**목적**: v10 스키마 기준으로 DB 정형 필드 + LLM 추출이 실제로 작동하는지 검증

#### v8 신규: v7 방식 vs v8 방식 품질 비교 **(v8 신설)**

- [ ] 이력서 50건에 대해 두 가지 방식 비교:
  - v7: 원본 텍스트 → LLM 추출
  - v8: DB 정형 필드 + 텍스트 필드 → LLM 추출
- [ ] 측정: scope_type 정확도, outcomes F1, situational_signals F1
- [ ] **결론**: v8 방식이 v7 방식 대비 품질 동등 이상인지 확인

#### CandidateContext 추출 테스트 (이력서 50건)
- [ ] 직무별 10건 × 5개 직군 (개발, 디자인, 마케팅, PM, 경영지원)
- [ ] **v8 변경**: DB에서 Career/CareerDescription/SelfIntroduction 조회 → LLM 추출
- [ ] 모델 비교:

| 모델 | 테스트 건수 | 측정 항목 |
|---|---|---|
| Claude Haiku 4.5 | 50건 | 추출 정확도, 토큰 사용량, 비용 |
| Gemini 2.0 Flash | 50건 | 동일 |
| Claude Sonnet 4.6 | 10건 | gold standard 비교 |

- [ ] 필드별 추출 성공률 측정:

| 필드 | 예상 성공률 | 실측 목표 |
|---|---|---|
| scope_type | **75-85%** (v8: positionGradeCode 힌트 제공) | > 70% |
| outcomes | 60-70% | > 60% |
| situational_signals | 50-70% | > 50% |
| failure_recovery | 10-20% | null 정상 |

#### CompanyContext 추출 테스트 (JD 30건)
- [ ] **v8 변경**: job-hub DB에서 overview/requirement/skill 조회 → 정형 필드 확인 → LLM 추출 (scope_type, operating_model만)
- [ ] vacancy scope_type 추출 정확도
- [ ] operating_model facets 추출 일관성
- [ ] NICE 매칭 → stage_estimate Rule 검증

#### PII 마스킹 영향 테스트 (10건)
- [ ] **v8 변경**: DB 필드 단위 마스킹 (이름, 연락처 컬럼 제외)
- [ ] 마스킹 전/후 LLM 추출 결과 diff

#### Embedding 모델 확정 검증 (20쌍)
- [ ] `text-multilingual-embedding-002` 한국어 분별력 검증
- [ ] 검증 실패 시에만 Cohere / BGE-M3 대안 검토

#### LLM 호출 전략 비교 (10건)
- [ ] 경력별 개별 LLM 호출 vs 이력서 전체 1회 호출 비교

**산출물**: 모델 비교 리포트 + v7 vs v8 품질 비교 리포트 + Embedding 확정 검증 리포트

### 0-3. 인프라 셋업 (1주, 0-1과 병행)

- [ ] Neo4j AuraDB Free 인스턴스 생성
- [ ] v10 Graph 스키마 적용 (노드/엣지/인덱스)
- [ ] Vector Index 설정 (chapter_embedding, vacancy_embedding)
- [ ] 프로젝트 리포지토리 셋업 (Python, Poetry/uv)
- [ ] **v8 변경**: DB 커넥터 셋업 (resume-hub, job-hub, code-hub 연결)
  - SQLAlchemy / asyncpg 기반 리드 레플리카 연결
  - 또는 API 클라이언트 셋업
- [ ] ~~이력서 파싱 라이브러리 설치~~ **(v8 제거)**
- [ ] PII 마스킹 전략 결정 (법무 확인 결과 반영)

#### Organization 크롤링 보강 속성 사전 선언 (v6 유지)
- [ ] Neo4j Organization 노드에 크롤링 속성 nullable로 사전 선언

#### Industry 마스터 노드 사전 생성 **(v8 변경: code-hub 활용)**
- [ ] **v8 변경**: code-hub INDUSTRY 코드 활용 (NICE 업종코드 대신 또는 병행)
  - code-hub INDUSTRY 계층 구조 → Industry 마스터 노드 생성
  - NICE 업종코드와 code-hub INDUSTRY 코드 간 매핑 확인
- [ ] Industry 노드 스키마 확정 + Neo4j 적재 스크립트 준비

### 0-3.1 오케스트레이션 전략 (v7 유지)

#### Pipeline DAG (의존성 그래프)

```
A (CompanyContext)  ──┐
                      ├──→ C (Graph 적재) ──→ D (MappingFeatures) ──→ E (서빙)
B (CandidateContext) ─┘
```

- A와 B 병렬 실행 가능
- 오케스트레이션 도구: Prefect (self-hosted) 또는 Cloud Workflows (GCP)

#### Chunk 관리 전략 (500K 이력서)

```
[v8 변경: DB 기반 Chunk 분할]

resume-hub 500K 레코드
    │
    ├─ 중복 제거 (SiteUserMapping 기반) → canonical ~450K
    │
    ├─ 1,000건/chunk × 450 chunks로 분할
    │   (DB cursor 기반 또는 candidate_id 범위 분할)
    │
    ├─ Chunk 상태 추적 (BigQuery 또는 Firestore)
    │
    └─ 실패 chunk 재처리 (동일)
```

### 0-4. Phase 0 완료 의사결정

| 의사결정 | 판단 기준 | 옵션 |
|---|---|---|
| LLM 모델 선택 | PoC 추출 품질 + 비용 | Haiku / Flash / Sonnet / Sonnet fallback (A') |
| PII 전략 | 법무 확인 + 마스킹 영향 | API / On-premise / **기본값: 마스킹 API** |
| v8 방식 확정 | v7 vs v8 품질 비교 **(v8 신설)** | **v8(DB 기반) / v7(파일 기반) fallback** |
| Embedding 모델 확정 | 한국어 분별력 검증 | text-multilingual-embedding-002 / Cohere / BGE-M3 |
| LLM 호출 전략 | 품질/비용 비교 | 경력별 개별 / 이력서 전체 1회 |
| ~~섹션 분할 전략~~ | — | **제거** (v8: DB 기반, 섹션 분할 불필요) |
| Graph DB 플랜 | 예상 노드 수 | Free / Professional |
| MVP 범위 | 데이터 품질 | 전체 / 특정 직군만 |
| 오케스트레이션 도구 | DE 역량 + GCP 통합 요구 | Prefect / Cloud Workflows |

---

## Phase 1: MVP 파이프라인 구축 (6~8주) **(v8 변경: 8~10주에서 단축)**

### 1-1. DB 커넥터 + 데이터 매핑 + 3-Tier 비교 전략 모듈 (1~2주) **(v9 변경: 3-Tier 통일)**

> v7의 "PDF/DOCX/HWP 파서, 섹션 분할기, 경력 블록 분리기, 기술 사전, 회사 사전" 전체가
> **DB 커넥터 + 데이터 매핑 + 3-Tier 비교 전략 모듈**로 대체된다.
> **(v9 변경)**: DB 값이 비표준 상태이므로 3-Tier 비교 전략 적용. v11.1 `00_data_source_mapping.md` §1.5와 정합.

#### DB 커넥터 구현
- [ ] resume-hub 커넥터: Career, Skill, Education, CareerDescription, SelfIntroduction 조회
- [ ] job-hub 커넥터: job, overview, requirement, work_condition, skill 조회
- [ ] code-hub 커넥터: common_code (HARD_SKILL, SOFT_SKILL, JOB_CLASSIFICATION, INDUSTRY) 조회
- [ ] 배치 조회 최적화 (cursor 기반 pagination, 1,000건/batch)

#### 데이터 매핑 모듈
- [ ] resume-hub Career → CandidateContext 기본 필드 매핑
  - companyName → company (Tier 1 정규화 적용) **(v8.1)**
  - positionTitleCode → role_title (code-hub 참조 + Tier 2 embedding fallback) **(v8.1)**
  - startDate/endDate → period
  - positionGradeCode → scope_type 힌트
  - businessRegistrationNumber → NICE 매칭 키
- [ ] resume-hub Skill → tech_stack (code-hub HARD_SKILL 코드 참조 + Tier 2 embedding fallback) **(v8.1)**
- [ ] job-hub overview/requirement/skill → CompanyContext 기본 필드 매핑
  - overview.industry_codes → industry (code-hub INDUSTRY 참조)
  - skill → tech_stack (code-hub HARD_SKILL 참조 + Tier 2 embedding fallback) **(v8.1)**
  - requirement.careers → career_types, designation

#### 3-Tier 비교 전략 모듈 **(v9 변경: v11.1 정합)**
- [ ] **Tier 1: 정규화 적합** (code-hub CI Lookup)
  - 대학교 alias 사전 (~200개): "서울대"→"서울대학교", "KAIST"→"한국과학기술원" 등
  - 회사명 alias 사전 (~500개): BRN null fallback용
  - 산업 코드: code-hub INDUSTRY 직접 매핑
- [ ] **Tier 2: 경량 정규화 + 임베딩** (스킬)
  - `normalize_skill()`: CI 매칭 → synonyms 매칭 → 미매칭 시 원본 유지 (v11.1 §1.3 정합)
  - code-hub HARD_SKILL canonical embedding 사전 구축 (~2,000개, 1회성)
  - similarity threshold: 스킬 0.85 (Phase 0 PoC에서 캘리브레이션)
- [ ] **Tier 3: 임베딩 전용** (전공, 직무명, 롱테일 스킬)
  - 정규화 시도하지 않음 — 원본 유지, 임베딩 cosine similarity로 비교
  - `compare_majors()` 함수 구현 (v11.1 §1.5 정합, threshold 0.75)
  - `compute_embedding_similarity_batch()` 공통 함수 구현
  - 전공 canonical embedding (~500개), 직무 canonical embedding (~300개) 구축
  - Vertex AI `text-multilingual-embedding-002` 배치 임베딩
- [ ] **캐시 레이어**: 동일 텍스트 embedding 결과 캐시 (메모리 → 디스크)
- [ ] **`compute_skill_overlap()` 하이브리드**: 정규화 성공 스킬 exact match + 미정규화 스킬 임베딩 비교 (v11.1 §4.3 정합)
- [ ] **정규화 통합 테스트**: 100건 샘플로 3-Tier 비교 정확도 측정

#### 중복 제거 모듈
- [ ] SiteUserMapping 기반 중복 감지 + canonical 선택
- [ ] 동일 candidate에 여러 사이트 이력서 → 최신 선택

#### 공통
- [ ] PII 마스킹 모듈 (DB 필드 단위: 이름, 연락처 컬럼 제외/마스킹)
- [ ] ~~기술 사전 구축~~ **제거** (code-hub 직접 참조)
- [ ] ~~회사 사전 구축~~ **대폭 축소** (BRN null fallback용 최소 사전만)

### 1-2. CompanyContext 파이프라인 (1~2주)

#### 구현 순서

```python
class CompanyContextPipeline:
    def generate(self, job_id: str) -> CompanyContext:
        # 1. DB 조회 (v8 변경: JD 텍스트 파싱 → DB 직접 조회)
        job = self.job_hub.get_job(job_id)
        overview = self.job_hub.get_overview(job_id)
        requirement = self.job_hub.get_requirement(job_id)
        skills = self.job_hub.get_skills(job_id)

        # 2. 정형 필드 직접 매핑 (LLM 불필요)
        tech_stack = self.map_skills_to_hard_skill_codes(skills)
        industry = self.map_industry_codes(overview.industry_codes)
        career_types = self.extract_career_types(requirement)
        education = self.extract_education_requirement(requirement)
        designation = self.extract_designation(overview)

        # 3. company_profile (NICE Lookup — BRN 기반)
        nice = self.nice_store.get_by_brn(job.business_registration_number)
        profile = self.extract_company_profile(nice)

        # 4. stage_estimate (Rule + LLM fallback)
        stage = self.extract_stage(nice, overview)

        # 5. LLM 추출 (scope_type, seniority, operating_model만)
        #    정형 필드를 사전 제공하여 토큰 절감
        descriptions = overview.descriptions  # JSONB
        vacancy, role_exp = self.llm_extract_vacancy_and_role(
            descriptions, tech_stack=tech_stack, industry=industry
        )

        # 6. operating_model
        op_model = self.extract_operating_model(descriptions)

        return CompanyContext(...)
```

- [ ] CompanyContext JSON 스키마 Pydantic 모델 정의
- [ ] **v8 변경**: job-hub DB 조회 → 정형 필드 매핑 모듈
- [ ] NICE Lookup 모듈 (BRN 기반)
- [ ] stage_estimate Rule 엔진
- [ ] LLM 추출 프롬프트 (vacancy + role_expectations — 정형 필드 사전 제공)
- [ ] operating_model 키워드 엔진 + LLM 보정
- [ ] 통합 테스트 (JD 100건)

### 1-3. CandidateContext 파이프라인 (2주) **(v8 변경: 3주+1주 버퍼 → 2주)**

> v7 대비 1~2주 단축. 파싱/섹션분할/블록분리/Rule 추출 모듈이 모두 DB 조회로 대체되어
> LLM 프롬프트 설계와 NICE 역산 모듈에 집중할 수 있다.

#### 구현 순서

```python
class CandidateContextPipeline:
    def generate(self, candidate_id: str) -> CandidateContext:
        # 1. DB 조회 (v8 변경: 파싱/섹션분할 전체 제거)
        careers = self.resume_hub.get_careers(candidate_id)
        skills = self.resume_hub.get_skills(candidate_id)
        career_descs = self.resume_hub.get_career_descriptions(candidate_id)
        self_intros = self.resume_hub.get_self_introductions(candidate_id)

        # 2. 경력별 처리 (DB가 이미 회사 단위로 분리)
        experiences = []
        for career in careers:
            # 2a. 정형 필드 직접 매핑 (LLM 불필요)
            basic = self.map_career_to_basic(career, skills)
            # → company, role_title, period, tech_stack 모두 DB에서 직접

            # 2b. LLM 추출 (scope_type, outcomes, signals만)
            text_input = self.build_llm_input(career, career_descs, self_intros)
            enriched = self.llm_extract_experience(
                text_input, basic,
                hints={
                    "positionGradeCode": career.positionGradeCode,
                    "positionTitleCode": career.positionTitleCode,
                }
            )

            # 2c. PastCompanyContext (BRN 기반 NICE 직접 매칭)
            if career.businessRegistrationNumber:
                pcc = self.build_past_company_context_by_brn(
                    career.businessRegistrationNumber, career.period
                )
            else:
                pcc = self.build_past_company_context_by_name(
                    career.companyName, career.period
                )
            enriched.past_company_context = pcc

            experiences.append(enriched)

        # 3. 전체 커리어 수준 (LLM 1회)
        role_evo = self.llm_extract_career_level(experiences)
        domain = self.llm_extract_domain_depth(experiences)
        work_style = self.llm_extract_work_style(experiences)

        return CandidateContext(...)
```

- [ ] CandidateContext JSON 스키마 Pydantic 모델 정의
- [ ] **v8 변경**: resume-hub DB 조회 → 기본 필드 매핑 모듈 (회사/직무/기간/기술)
- [ ] **v8 변경**: LLM 입력 구성 모듈 (workDetails + CareerDescription + SelfIntroduction)
- [ ] LLM 추출 프롬프트 (Experience별 — positionGradeCode 힌트 포함)
- [ ] LLM 추출 프롬프트 (전체 커리어)
- [ ] PastCompanyContext BRN 기반 NICE 매칭 모듈 **(v8 변경)**
- [ ] PastCompanyContext 회사명 fuzzy match fallback (BRN null인 경우)
- [ ] WorkStyleSignals LLM 추출 프롬프트
- [ ] 통합 테스트 (이력서 200건)
- [ ] Batch API 연동 (대량 처리)
- [ ] ~~Rule 추출 모듈 (정규식)~~ **제거**
- [ ] ~~섹션 분할기~~ **제거**
- [ ] ~~경력 블록 분리기~~ **제거**

### 1-4. Graph 적재 파이프라인 (1~2주) **(v8 변경: 2주 → 1~2주)**

> Entity Resolution이 code-hub 코드 기반으로 간소화되어 0~1주 단축.

#### 1주차: 로더 + Entity Resolution (간소화)
- [ ] CompanyContext → Neo4j 노드/엣지 로더
- [ ] CandidateContext → Neo4j 노드/엣지 로더
- [ ] Deterministic ID 생성 모듈 (v5 유지)
- [ ] **v8 변경**: Organization Entity Resolution 간소화
  - BRN 기반 org_id 매핑 (주 경로)
  - code-hub INDUSTRY 코드 기반 Industry 노드 연결
  - ~~회사명 정규화 사전 ~1,000개~~ → 최소 사전 (BRN null fallback만)
- [ ] **v9 변경**: Skill, Role, Major — 3-Tier 비교 전략 적용
  - Tier 1 (대학교/회사명): alias 사전 기반 case-insensitive 매칭
  - Tier 2 (스킬): CI + synonyms 정규화, 미매칭 시 원본 유지 + 임베딩 비교
  - Tier 3 (전공/직무명): 정규화하지 않고 원본 저장, `compare_majors()` / 임베딩 유사도로 비교
  - Graph MERGE 시 `match_method` 기록 (code_hub_ci, code_hub_synonyms, embedding_pending, embedding_only)
  - `normalization_confidence` 세분화 적용 (§2.2 NORMALIZATION_CONFIDENCE)
  - threshold 미달 노드에 `needs_review = true` 플래그 부여

#### Industry 마스터 노드 적재 + REQUIRES_ROLE (v6 유지)
- [ ] Industry 마스터 노드 적재 (code-hub INDUSTRY + NICE 업종코드)
- [ ] Vacancy→REQUIRES_ROLE→Role 관계 생성

#### 2주차 (필요 시): Vector Index + 벤치마크
- [ ] Vector Index 적재 (Chapter/Vacancy embedding)
- [ ] Cypher 쿼리 테스트 (Q1~Q5)
- [ ] Idempotency 테스트

### 1-5. MappingFeatures 계산 (1주) — v7과 동일

- [ ] Candidate Shortlisting
- [ ] MappingFeatures 로직 구현 (stage_match, vacancy_fit, domain_fit, culture_fit, role_fit)
- [ ] MAPPED_TO 그래프 반영
- [ ] BigQuery 테이블 생성 + 적재
- [ ] 매핑 50건 수동 검증

**Phase 1 산출물**: E2E 파이프라인 (JD 100건 + 이력서 1,000건 + Graph + MappingFeatures)

---

## Phase 2: 확장 + 최적화 (3~4주) **(v8 변경: 4~5주에서 단축)**

### 2-1. 전체 데이터 처리 (2~3주)

- [ ] **v8 변경**: 이력서 중복 제거 (SiteUserMapping 기반 — v7의 SimHash 대비 간소화)
- [ ] Batch 처리 인프라 구축
  - **v8 변경**: DB cursor 기반 배치 분할 (파일 I/O 불필요)
  - 이력서 500K × Batch API (Haiku), 1,000건/chunk 단위
  - JD 10K × Batch API
- [ ] 에러 핸들링 인프라 (Dead-letter 큐, 모니터링)
- [ ] 처리 모니터링 대시보드 (Grafana + BigQuery)
- [ ] Neo4j AuraDB Professional 전환 (필요 시)
- [ ] BigQuery 전체 적재

### 2-2. 품질 평가 (1주, 2-1과 병행) — v7과 동일

- [ ] Gold Test Set 구축 (전문가 2인 × 200건)
- [ ] 사전 검정력 분석 (Power Analysis)
- [ ] 평가 지표 측정 (scope_type 정확도, outcome F1, human eval 등)

### 2-3. ML Knowledge Distillation (1~2주, 선택적) — v7과 동일

### 2-4. DS/MLE 서빙 인터페이스 (1주) — v7과 동일

**Phase 2 산출물**: 전체 데이터 처리 완료 + 품질 리포트 + 서빙 인터페이스

---

## 운영 전략: 롤백 / 재처리 / 증분 처리

### v8 변경: DB 기반 증분 처리

```
[증분 처리 플로우 — v8]
DB updated_at 기반 변경 감지
    │
    ├─ 신규 건 (resume-hub에 새 레코드): 기존 파이프라인 동일
    │   └─ deterministic ID로 MERGE → 중복 방지
    │
    ├─ 갱신 건 (updated_at 변경): 기존 Context JSON 조회 → diff
    │   ├─ DB 정형 필드 변경: 해당 필드만 업데이트 (LLM 재호출 불필요)
    │   └─ 텍스트 필드 변경: LLM 재추출 (해당 경력만)
    │
    └─ 삭제 건: Graph에서 soft-delete
```

- **처리 주기**: 일 1회 배치 (DB updated_at 기반)
- **v8 이점**: DB 변경 감지가 파일 hash 비교보다 정확하고 효율적

### 프롬프트 버전 관리 — v7과 동일

### 롤백 전략 — v7과 동일 (Deterministic ID + MERGE 패턴)

---

## 테스트 전략

| 테스트 레벨 | 대상 | 기준 | 시점 |
|---|---|---|---|
| **Unit** | DB 커넥터, 코드 매핑, 3-Tier 비교 전략 모듈 **(v9 변경)** | 필드 매핑 정확도 100%, Tier 1 정확도 95%+, Tier 2 CI+synonyms precision 90%+, Tier 3 임베딩 coverage 85%+ | Phase 1-1 |
| **Integration** | 단일 이력서/JD E2E | DB 조회→LLM→Graph 적재 성공 | Phase 1-2, 1-3 |
| **Idempotency** | 동일 입력 2회 적재 | 노드/엣지 수 변화 없음 | Phase 1-4 |
| **Batch** | 1,000건 배치 처리 | 에러율 < 5%, 처리시간 < 2시간 | Phase 1 말 |
| **Quality** | 50건 수동 평가 | scope_type 정확도 > 70% | Phase 2-2 |
| **Power** | 50건 수동 평가 통계적 검정력 | Cohen's d ≥ 0.5 | Phase 2-2 |
| **Scale** | 500K 전체 처리 | 에러율 < 3%, 배치 완료 < 3일 | Phase 2-1 |
| **Regression** | 프롬프트 변경 시 | 50건 회귀 테스트, 품질 변화 < 5% | 운영 단계 |
| **v7 vs v8 비교** **(v8 신설)** | 50건 추출 품질 비교 | v8 ≥ v7 | Phase 0-2 |

---

## Phase 3: 고도화 (지속) — v7과 동일

### 3-1. 크롤링 파이프라인 (7주) — v6/v7과 동일
### 3-2. Company-to-Company 관계 로드맵 — v6 유지
### 3-3. GraphRAG 활용 확장 — v7과 동일
### 3-4. 운영 고도화 — v7과 동일

---

## 타임라인 요약

> **v8 변경**: DB 기반 파이프라인 전환으로 전처리/파싱 관련 작업이 대폭 축소. 18~22주 → 13~16주.

```
Pre-Phase 0: 사전 준비 (DB 접근 + NICE 접근 확보) — Phase 0 시작 2주 전까지

Week 1-2:   Phase 0-1, 0-2 (DB 프로파일링 + LLM PoC + v7 vs v8 비교)
Week 2-3:   Phase 0-3, 0-4 (인프라 셋업 + 의사결정)

Week 3-5:   Phase 1-1 (DB 커넥터 + 데이터 매핑 + 3-Tier 비교 전략 — 1~2주) **(v9 변경)**
Week 4-6:   Phase 1-2 (CompanyContext 파이프라인 — 1~2주)
Week 6-8:   Phase 1-3 (CandidateContext 파이프라인 — 2주)
Week 8-10:  Phase 1-4 (Graph 적재 + Entity Resolution + Industry 노드 — 1~2주)
Week 10-11: Phase 1-5 (MappingFeatures + MAPPED_TO + Shortlisting — 1주)

Week 11-14: Phase 2-1 (전체 데이터 처리 — 2~3주)
Week 12-13: Phase 2-2 (품질 평가 + power analysis) — 2-1과 병행
Week 13-14: Phase 2-4 (DS/MLE 서빙 인터페이스)
Week 14-16: Phase 2-3 (ML Distillation — 선택적, 점선)

Week 16-18: Phase 3 C1 (크롤러 인프라 구축 — 2주)
Week 18-20: Phase 3 C2 (T3 홈페이지 크롤링 — 2주)
Week 20-22: Phase 3 C3 (T4 뉴스 크롤링 — 2주)
Week 22-23: Phase 3 C4 (데이터 병합 + 품질 검증 — 1주)
Week 23+:   Phase 3-2~3-4 (Company 관계, GraphRAG, 운영 고도화, 지속)
```

**총 MVP 완성**: ~**14~17주** (Phase 0~2, ML Distillation 제외 시 ~13~15주) **(v9 변경: 3-Tier 비교 전략 모듈 +1주)**
**첫 동작 데모**: ~**12주** (Phase 0~1 완료 시점) **(v9 변경)**
**크롤링 파이프라인 완료**: ~23주 (Phase 3 C1~C4)

### v7→v8 일정 단축 상세 **(v8 신설)**

| Phase | v7 | v8 | 단축 | 근거 |
|---|---|---|---|---|
| Phase 0 | 3~4주 | **2~3주** | 1주 | 파일 형식/OCR/파싱 성공률 측정 불필요 |
| Phase 1-1 | 전처리 2주 | DB 커넥터 + 3-Tier 비교 전략 1~2주 | 0~1주 | 파서/분할기 불필요, 단 3-Tier 비교 전략 모듈 추가 **(v9 변경)** |
| Phase 1-3 | 3주(+1주 버퍼) | 2주 | 1~2주 | Rule 추출 모듈(정규식) 불필요, DB 매핑만 구현 |
| Phase 1-4 | 2주 | 1~2주 | 0~1주 | Entity Resolution 간소화 (BRN + code-hub) |
| Phase 2 | 4~5주 | 3~4주 | 1주 | 중복 제거 간소화 (SiteUserMapping) |
| **총 MVP** | **18~22주** | **14~17주** | **4~5주** | v9: 3-Tier 비교 전략 모듈 추가로 +1주 **(v9 변경)** |
| **첫 동작 데모** | 16주 | **12주** | **4주** | **(v9 변경)** |

---

## 핵심 의사결정 포인트

| 시점 | 의사결정 | 판단 기준 | 옵션 |
|---|---|---|---|
| Pre-Phase 0 | DB 접근 확보 **(v8 신설)** | 3개 DB 읽기 권한 | 리드 레플리카 / API / v7 fallback |
| Pre-Phase 0 | NICE DB 접근 | 계약 상태 | 기존 계약 / 신규 / 공개 데이터 |
| Phase 0 완료 | v8 방식 확정 **(v8 신설)** | v7 vs v8 품질 비교 | v8(DB 기반) / v7(파일 기반) |
| Phase 0 완료 | 오케스트레이션 도구 | DE 역량 + GCP 통합 | Prefect / Cloud Workflows |
| Phase 0 완료 | LLM 모델 선택 | PoC 추출 품질 | Haiku / Flash / Sonnet / A' |
| Phase 0 완료 | PII 전략 | 법무 확인 | API / On-premise / 기본값: 마스킹 API |
| Phase 0 완료 | Embedding 확정 | 한국어 분별력 | text-multilingual-embedding-002 / 대안 |
| Phase 0 완료 | LLM 호출 전략 | 품질/비용 비교 | 경력별 개별 / 전체 1회 |
| Phase 0 완료 | MVP 범위 | 데이터 품질 | 전체 직군 / 특정 직군 |
| Phase 1 중간 | 프롬프트 전략 | 추출 품질 추이 | 단일 vs 분리 프롬프트 |
| Phase 2 평가 후 | ML Distillation 투자 | scope_type ML F1 | ML 투자 / LLM 유지 |
| Phase 2 평가 후 | 평가 표본 확대 | Cohen's d | 50건 유지 / 100건 확대 |
