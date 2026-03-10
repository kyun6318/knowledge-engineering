# 실행 계획 v5 — v4 온톨로지 기반

> v4 온톨로지의 CompanyContext + CandidateContext + Graph + MappingFeatures를
> 구축하기 위한 단계별 실행 계획.
>
> 작성일: 2026-03-08 (v2 기반)
> 개정일: 2026-03-08 (v5 — Phase 0 파싱 성공률 측정, 법무 기본값 전략, 이력서 중복 처리, Graph Idempotency)

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
    ├─ 크롤링/투자DB 연동
    ├─ GraphRAG vs baseline ablation
    └─ Active Learning
```

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

**목적**: v4 스키마 기준으로 LLM 추출이 실제로 작동하는지 검증

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

#### v4 추가: Embedding 모델 비교 (20쌍)

> **v4 신설**: domain_fit 피처의 핵심인 embedding 모델의 한국어 분별력 사전 검증.

- [ ] 20쌍의 (이력서 도메인 텍스트, JD 도메인 텍스트) 수동 구성
  - 10쌍: 의미적으로 유사 (같은 도메인), 10쌍: 의미적으로 상이 (다른 도메인)
- [ ] 3개 모델 비교: text-embedding-3-small / Cohere embed-multilingual-v3.0 / BGE-M3
- [ ] 측정: cosine similarity 분포 (유사 쌍 vs 상이 쌍의 분리도)
- [ ] 결론: embedding 모델 선정

#### v4 추가: LLM 호출 전략 비교 (10건)

> **v4 신설**: 경력별 개별 호출 vs 이력서 전체 1회 호출의 품질/비용 비교.

- [ ] 이력서 10건 (경력 3건 이상)에 대해 두 가지 호출 전략 비교
  - A: 경력 블록별 개별 LLM 호출 (현재 설계)
  - B: 이력서 전체를 1회 LLM 호출
- [ ] 측정: 추출 정확도, 토큰 사용량, JSON 파싱 성공률
- [ ] 결론: Phase 1에서 사용할 호출 전략 결정

**산출물**: 모델 비교 리포트 + 추출 품질 메트릭 + 파싱 품질 리포트(v5) + PII 영향 리포트 + Embedding 모델 리포트

### 0-3. 인프라 셋업 (1주, 0-1과 병행)

- [ ] Neo4j AuraDB Free 인스턴스 생성
- [ ] v4 Graph 스키마 적용 (노드/엣지/인덱스)
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

**산출물**: 인프라 준비 완료 + PII 전략 확정 (또는 기본값 적용)

### 0-4. Phase 0 완료 의사결정

| 의사결정 | 판단 기준 | 옵션 |
|---|---|---|
| LLM 모델 선택 | PoC 추출 품질 + 비용 | Haiku / Flash / Sonnet |
| PII 전략 | 법무 확인 + 마스킹 영향 테스트 | API (마스킹) / On-premise / **기본값: 마스킹 API** (v5) |
| Embedding 모델 선택 | 한국어 분별력 비교 | text-embedding-3-small / Cohere / BGE-M3 |
| LLM 호출 전략 | 품질/비용 비교 | 경력별 개별 호출 / 이력서 전체 1회 호출 |
| 섹션 분할 전략 | 파싱 성공률 실측 (v5) | Rule 기반 / LLM fallback |
| Graph DB 플랜 | 예상 노드 수 | Free / Professional |
| MVP 범위 | 데이터 품질 | 전체 / 특정 직군만 |
| 이력서 중복 처리 | 중복률 실측 (v5) | 동일 candidate_id 최신 선택 / SimHash 기반 검토 큐 |

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

        # 4. 조합
        return CandidateContext(
            candidate_id=...,
            resume_id=resume_id,
            experiences=experiences,
            role_evolution=role_evo,
            domain_depth=domain,
            work_style_signals=None,  # v1에서 대부분 null
            _meta=self.build_meta(...)
        )
```

- [ ] CandidateContext JSON 스키마 Pydantic 모델 정의
- [ ] Rule 추출 모듈 (날짜/회사/기술)
- [ ] LLM 추출 프롬프트 (Experience별)
- [ ] LLM 추출 프롬프트 (전체 커리어)
- [ ] PastCompanyContext NICE 역산 모듈
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

#### 2주차: Vector Index + 벤치마크 + 적재 전략
- [ ] Vector Index 적재 (Chapter/Vacancy embedding)
  - embedding 텍스트 생성: scope_summary + outcomes + signals (02 문서 §4.5)
  - **v5 추가**: 빈 embedding 텍스트 skip 로직 (02 문서 §4.5)
- [ ] Cypher 쿼리 테스트 (v4 graph_schema.md의 Q1~Q4)
- [ ] **적재 벤치마크**: 1,000건 적재 시간 측정 → 500K 전체 적재 시간 추정
- [ ] **대량 적재 전략 결정** (02 문서 §4.4)
  - LOAD CSV + APOC batch vs Cypher MERGE 성능 비교
  - 초기 적재 vs 증분 적재 파이프라인 분리
- [ ] **v5 추가**: Idempotency 테스트 — 동일 데이터 2회 적재 후 노드/엣지 수 변화 없음 확인

### 1-5. MappingFeatures 계산 (1주)

- [ ] **Candidate Shortlisting** (02 문서 §5.0)
  - Rule pre-filter (industry, tech_stack, 경력연수)
  - Neo4j Vector Index 기반 ANN search (top-500)
- [ ] v4 mapping_features.md 로직 구현
  - stage_match
  - vacancy_fit
  - domain_fit (embedding cosine)
  - culture_fit (대부분 INACTIVE)
  - role_fit
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

- [ ] BigQuery 테이블 스키마 확정 (v4 mapping_features.md 참조)
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
| **Scale** | 500K 전체 처리 | 에러율 < 3%, 배치 완료 < 3일 | Phase 2-1 |
| **Regression** | 모델/프롬프트 변경 시 | 50건 회귀 테스트, 품질 지표 변화 < 5% | 운영 단계 |

---

## Phase 3: 고도화 (지속)

### 3-1. 데이터 소스 확장

- [ ] 투자 DB API 연동 (stage_estimate 보강)
- [ ] 회사 홈페이지 크롤링 (domain_positioning 보강)
- [ ] 뉴스/기사 크롤링 (structural_tensions 활성화)
- [ ] 자사 채용 히스토리 분석

### 3-2. GraphRAG 활용 확장

- [ ] Community Detection (유사 기업/후보 군집)
- [ ] Graph-based Recommendation (path 기반 추천)
- [ ] GraphRAG vs baseline ablation
  - baseline: LLM + Vector DB만으로 MappingFeatures 생산
  - GraphRAG: Graph traversal + Vector 하이브리드
  - 측정: MappingFeatures 품질 차이

### 3-3. 운영 고도화

- [ ] Active Learning 루프 (LLM fallback 케이스 재학습)
- [ ] operating_model 8 facets 확장 (v4 로드맵)
- [ ] Closed-loop Enrichment (후보 직접 질문)
- [ ] 실시간 API 서빙 (BigQuery → REST)

---

## 타임라인 요약

> **v5**: v4와 동일. 추가된 작업(파싱 성공률 측정, 중복 처리, Idempotency 테스트)은 기존 Phase 내 흡수 가능.

```
Week 1-2:   Phase 0-1, 0-2 (데이터 탐색 + 인프라)
Week 2-3:   Phase 0-2, 0-3 (LLM PoC + 파싱 PoC + 인프라 셋업)
Week 3-4:   Phase 0-4 의사결정 + Phase 1-1 시작 (전처리)

Week 4-6:   Phase 1-1 (전처리 모듈 + 중복 제거 — 2주)
Week 6-8:   Phase 1-2 (CompanyContext 파이프라인)
Week 8-11:  Phase 1-3 (CandidateContext 파이프라인 — 3주)
Week 11-13: Phase 1-4 (Graph 적재 + Entity Resolution + Idempotency — 2주)
Week 13-14: Phase 1-5 (MappingFeatures + Candidate Shortlisting)

Week 14-17: Phase 2-1 (전체 데이터 처리 — 2~3주)
Week 15-16: Phase 2-2 (품질 평가) — 2-1과 병행
Week 16-17: Phase 2-4 (DS/MLE 서빙 인터페이스)
Week 17-19: Phase 2-3 (ML Distillation — 선택적, 점선)

Week 19+:   Phase 3 (고도화, 지속)
```

**총 MVP 완성**: ~16~19주 (Phase 0~2, ML Distillation 제외 시 ~15~17주)
**첫 동작 데모**: ~14주 (Phase 0~1 완료 시점)

> **v5 일정 영향**: 추가 작업(파싱 성공률 측정, 이력서 중복 제거, Idempotency 테스트)은 기존 Phase 기간 내 흡수 가능하므로 전체 타임라인 변경 없음. 단, Phase 0에서 파싱 성공률이 50% 미만이면 LLM 섹션 분할 모듈 추가로 Phase 1-1이 0.5~1주 연장될 수 있다.

---

## 핵심 의사결정 포인트

| 시점 | 의사결정 | 판단 기준 | 옵션 |
|---|---|---|---|
| Phase 0 완료 | LLM 모델 선택 | PoC 추출 품질 | Haiku / Flash / Sonnet |
| Phase 0 완료 | PII 전략 | 법무 확인 + 마스킹 영향 테스트 | API / On-premise / **기본값: 마스킹 API** |
| Phase 0 완료 | Embedding 모델 선택 | 한국어 분별력 비교 (20쌍) | small / Cohere / BGE-M3 |
| Phase 0 완료 | LLM 호출 전략 | 품질/비용 비교 (10건) | 경력별 개별 / 이력서 전체 1회 |
| Phase 0 완료 | 섹션 분할 전략 (v5) | 파싱 성공률 실측 | Rule / LLM fallback |
| Phase 0 완료 | MVP 범위 | 데이터 품질 | 전체 직군 / 특정 직군 |
| Phase 1 중간 | 프롬프트 전략 | 추출 품질 추이 | 단일 vs 분리 프롬프트 |
| Phase 2 평가 후 | ML Distillation 투자 | scope_type ML F1 | ML 투자 / LLM 유지 |
| Phase 2 평가 후 | Graph DB 스케일 | 노드 수 / 성능 | Free → Professional |
| Phase 2 평가 후 | MappingFeatures 조정 | human eval r값 | weight 재조정 / 피처 재설계 |
| Phase 2 완료 | GraphRAG 투자 | ablation 결과 | Full GraphRAG / Vector only |
