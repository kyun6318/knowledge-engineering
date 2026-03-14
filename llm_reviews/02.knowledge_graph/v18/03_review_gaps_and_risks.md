# v18 갭 분석 및 리스크 리뷰

> 리뷰일: 2026-03-14 | 리뷰어: Claude Opus 4.6

---

## 1. 설계 갭 (Design Gaps)

### 1.1 SIE 모델 운영 설계 부재

**심각도: High**

01_extraction_pipeline §3.2에서 SIE 모델 통합을 선언했으나, 운영 관점의 설계가 부재:

| 필요 항목 | 현재 상태 | 비고 |
|----------|----------|------|
| SIE 모델 서빙 방식 | 미정의 | Cloud Run GPU? GCE 전용? Vertex AI Endpoint? |
| SIE 처리 시간/비용 | 미추정 | 8M 이력서 대상 GLiNER2 처리 시간 |
| SIE 출력 스키마 | v3.md §3.5 예시만 존재 | Pydantic 스키마로 정식 정의 필요 |
| SIE 실패 처리 | 미정의 | 모델 에러, confidence 전부 <threshold 시 |
| SIE ↔ LLM 실행 순서 | "사전 추출 단계"만 언급 | 동기/비동기, 배치 단위 미정의 |

**권고**: 02_model_and_infrastructure.md에 §5 "SIE 모델 인프라" 섹션 추가. 최소 Phase 0 PoC에서 결정해야 할 항목 목록화.

### 1.2 LinkedIn 동일 인물 매칭 알고리즘 부재

**심각도: Medium**

05_extraction_operations §5에서 LinkedIn 데이터 동기화 전략을 정의했으나, 핵심인 "동일 인물 판별"이 개략적:

| 필요 항목 | 현재 상태 |
|----------|----------|
| 매칭 알고리즘 | "이름+회사명+기간 조합으로 추정" (한 줄) |
| 매칭 임계값 | 미정의 |
| False positive 처리 | 미정의 |
| 매칭 정확도 목표 | 미정의 |
| 매칭 결과 활용 방식 | "교차 검증" (구체적 방법 없음) |

**권고**: Phase 5 착수 전 별도 설계 문서 또는 05_extraction_operations에 §5.1 "동일 인물 매칭 알고리즘" 추가.

### 1.3 증분 처리와 LinkedIn 통합의 교차점 미설계

**심각도: Low**

05_extraction_operations §1의 증분 처리(DB updated_at 기반)와 §5의 LinkedIn 동기화가 독립적으로 설계되어 있으나, 실운영에서는 교차 상황이 발생:

- resume-hub 이력서 업데이트 + 동일 인물의 LinkedIn 프로필 변경이 동시 발생 시
- LinkedIn 데이터로 Organization을 보강한 후, 해당 Organization을 참조하는 Chapter가 업데이트될 때

현재 Phase 5에서 처리 예정이므로 즉각 해소는 불필요하나, Phase 1-4 설계 시 LinkedIn 통합 확장점을 고려하면 좋음.

---

## 2. 데이터 관련 갭

### 2.1 job-hub 실측 데이터 미확보

**심각도: Medium**

07_data_quality §2에서 job-hub 필드 가용성이 "예상" 수준:

| 필드 | 현재 표기 | 리스크 |
|------|----------|--------|
| industry_codes | "90%+" (예상) | 실측 시 70% 미만이면 Industry 노드 품질 저하 |
| job_classification_codes | "85%+" (예상) | 실측 시 낮으면 REQUIRES_ROLE 엣지 부족 |
| descriptions | "95%+" (예상) | 가장 확실하지만 미검증 |
| designation_codes | "40~50%" (예상) | seniority 추론에 직접 영향 |

**권고**: Phase 4-1(job-hub 상세 분석) 전이라도, 1K 샘플링으로 fill rate를 실측하여 예상치 검증 가능. Phase 0에서 병렬 수행 권고.

### 2.2 education_level 실효 fill rate 과대 추정 가능

**심각도: Low**

07_data_quality §1에서 education_level fill rate를 95.6%(education.schoolType 기준)으로 표기하나, 구코드 미매핑 ~110만건(~14%)을 고려하면 **실효 매핑 가능 fill rate는 ~82%**로 하락할 수 있음.

구코드→신코드 매핑 완료 시 95.6%로 복원되지만, 매핑 전 Phase 1-2에서는 82% 기준으로 설계해야 함.

---

## 3. 리스크 분석

### 3.1 기존 리스크 상태 (05_extraction_operations §4)

| ID | 리스크 | v12 상태 | v18 상태 | 비고 |
|----|--------|---------|---------|------|
| R1 | PII 처리 | Critical | **Critical 유지** | 책임 경계 미확정 |
| R2 | LLM 추출 품질 | Critical | **Critical 유지** | Phase 0 의존 |
| R2.4 | NICE 매칭률 | High | **High 유지** | BRN 84% 예상 |
| R2.18 | DB 접근 불가 | High | **High 유지** | 파일 폴백 존재 |

### 3.2 v18 신규 리스크

| ID | 리스크 | 심각도 | 영향 | 완화 방안 |
|----|--------|--------|------|----------|
| R6.1 | **SIE 모델 한국어 성능 미검증** | High | GLiNER2가 한국어 이력서에서 Span 추출 정확도 미확인 (학습 데이터 의존) | Phase 0에서 한국어 이력서 50건 SIE 추출 PoC 필수 |
| R6.2 | **SIE GPU 비용 예상 초과** | Medium | NuExtract 1.5(3.51B)는 GPU 요구 높음, 대규모 처리 시 비용 급증 | GLiNER2 우선, NuExtract는 장문에만 제한적 사용 |
| R6.3 | **LinkedIn 동일 인물 매칭 정확도** | Medium | 오매칭 시 Person 노드에 잘못된 보강 데이터 유입 | Phase 5에서 정확도 검증 후 활용, 보강 데이터에 source_type 태깅 |
| R6.4 | **구코드→신코드 매핑 테이블 부재** | Medium | 매핑 테이블이 code-hub에 존재하지 않으면 학교명 기반 수동 매칭 필요 | 데이터팀에 구코드→신코드 매핑 히스토리 보유 여부 확인 |
| R6.5 | **직무 코드 계층화 기준 모호** | Low | 242개 → ~30개 그룹핑 기준이 없으면 임의 분류 위험 | 도메인 전문가(채용팀) 참여하여 그룹핑 정의 |

### 3.3 Phase 0 PoC 의존도 분석

v18의 설계 결정 중 Phase 0 PoC 결과에 의존하는 항목이 다수:

| PoC 검증 항목 | 의존 설계 결정 | 실패 시 영향 |
|-------------|-------------|-------------|
| Haiku 품질 >70% | 전체 LLM 모델 선정 | Sonnet 전환 → 비용 3~4배 |
| text-embedding-005 한국어 | 임베딩 모델 선정 | Cohere 폴백 → 인덱스 재생성 |
| 1-pass vs N+1 품질 비교 | 호출 전략 | 분기점 조정 |
| CareerDescription 귀속 정확도 | confidence 감쇠율 | 프롬프트 개선 필요 |
| **[v18 신규] SIE 한국어 성능** | SIE 통합 여부 | SIE 제외 → LLM 전량 처리, 비용/정확도 영향 |
| **[v18 신규] Rule 기반 NEEDS_SIGNAL** | NEEDS_SIGNAL 생성 방식 | LLM 전환 → 비용 증가 |

**권고**: Phase 0 PoC 검증 항목에 "SIE 한국어 이력서 50건 추출 PoC"를 추가. PoC 범위가 확장되므로 Phase 0 일정(W0-W1) 재검토 필요.

---

## 4. 문서 범위 경계 준수 (3-Layer)

### 4.1 02.knowledge_graph 범위 준수 여부

| 내용 | 적절한 위치 | 실제 위치 | 판정 |
|------|-----------|----------|------|
| 추출 파이프라인 | 02.knowledge_graph | 01_extraction_pipeline | **적절** |
| SIE 모델 선정/인프라 | 02.knowledge_graph | 02_model_and_infrastructure | **적절** |
| 프롬프트 설계 | 02.knowledge_graph | 03_prompt_design | **적절** |
| Neo4j UNWIND 쿼리 | 03.graphrag (서빙) | 01_extraction_pipeline §5.2 | **경계 케이스** — Graph 적재는 빌드와 서빙 경계 |
| 비용 추정 | 03.graphrag (통합 관리) | 02_model_and_infrastructure §4.4 | **적절** — 추출 관련만 |
| MappingFeatures 코드 매칭 | 02.knowledge_graph? 03.graphrag? | 06_normalization §5 | **경계 케이스** — 매칭은 서빙이나 정규화는 빌드 |

**판정**: 06_normalization §5의 `compute_skill_overlap`, `compute_job_classification_match` 함수는 **매칭 로직**에 해당하여 03.graphrag 영역에 더 가까움. 다만 정규화 문서에서 "데이터 소스 관점의 매핑 정보만 기술"이라고 명시한 점에서 경계 준수 노력은 인정.

### 4.2 온톨로지 침범 여부

| v18 내용 | 01.ontology 정의와 관계 | 판정 |
|---------|---------------------|------|
| ScopeType enum 정의 | v25 02_candidate_context.md 정본 참조 | **적절** — 참조만 |
| HiringContext enum 정의 | v25 01_company_context.md 정본 참조 | **적절** — 참조만 |
| SituationalSignal 14개 taxonomy | v25 02_candidate_context.md 정본 | **적절** — 중복 기술이나 참조 표기 있음 |
| Confidence Penalty 규약 | v25 03_mapping_features.md 연계 | **적절** — 07_data_quality에서 "v25 연계" 명시 |
