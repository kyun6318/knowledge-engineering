# v3 데이터 요약 → v25/v18/v8 적용 변경 이력

> 적용일: 2026-03-14
> 소스: `00.datamodel/summary/v3.md`, `00.datamodel/summary/v3-db-schema.md`
> 타겟: `01.ontology/v25/`, `02.knowledge_graph/v18/`, `03.graphrag/separate/v8/`

---

## 적용된 v3 신규 내용 요약

| # | 항목 | 설명 |
|---|------|------|
| 1 | SIE 모델 | GLiNER2(주력) + NuExtract 1.5(보조), 경력기술서 구조 추출 |
| 2 | LinkedIn/BrightData | 2.0M 프로필, 2.7M AI 표준화 경력 |
| 3 | 구코드→신코드 학교 매핑 | ~110만건 미매핑 (U0/C0 구코드 457개) |
| 4 | 직무 코드 계층화 | 242개 → ~30개 상위 그룹 2단 계층 |
| 5 | 캠퍼스 코드 정리 | 공백 변형 제거 (경상국립대 8→5) |
| 6 | 회사명 정규화 3차 패스 | BRN 1차 → argMax 2차 → LinkedIn company_id 3차 |
| 7 | Phase 5 외부 데이터 통합 | LinkedIn ↔ resume-hub 교차 매핑 |
| 8 | code-hub 정밀 현황 | 58,413개 코드, code:name 1:1 완전 보장 |

---

## 01.ontology/v25/ 변경 상세

### 00_data_source_mapping.md
| 위치 | 변경 내용 |
|------|----------|
| §0 설계 원칙 | "v2.1 데이터 분석" → "v3 데이터 분석" 갱신 |
| §3.2 Experience 매핑 테이블 | scope_summary: "**SIE 확장 가능**" 추가, outcomes: "**SIE 보조**" 추가 |
| §3.2 [D5] | **신규 섹션**: SIE 모델 보조 추출 (GLiNER2/NuExtract 1.5) 설명, 적용 범위, 온톨로지 매핑 |
| §3.4 | company_name 비고에 "LinkedIn 933,923 고유 회사 교차 가능" 추가 |
| §3.7 | **신규 섹션**: LinkedIn 외부 데이터 매핑 — 6개 소스 필드→온톨로지 매핑 테이블, Phase 5 교차 매핑 전략 |
| §9 | **신규 테이블**: LinkedIn/BrightData 사용 불가 필드 6개 (location, country_code, recommendations_count 등) |

### 02_candidate_context.md
| 위치 | 변경 내용 |
|------|----------|
| §0 T3 LinkedIn | "접근 정책 확인 필요" → "**BrightData 2.0M 프로필 확보**, AI 표준화 경력 완료" |
| §2.7.1 | **신규 섹션**: SIE 모델 보완 — CareerDescription FK 부재 제약 부분 해소, workDetails(~56%) 구조 추출 |

### 04_graph_schema.md
| 위치 | 변경 내용 |
|------|----------|
| §1.2 Organization | LinkedIn 고유 회사명 통계(4,479,983 + 933,923), 정규화 3차 패스 전략 주석 추가 |
| §1.3 Chapter | SIE 모델(GLiNER2) evidence_chunk 정밀 추출 주석 추가 |
| §1.4 Role | JOB_CLASSIFICATION_SUBCATEGORY 242개 과도 세분화, JobCategory ~30개 2단 계층 권장 주석 추가 |

---

## 02.knowledge_graph/v18/ 변경 상세

### 01_extraction_pipeline.md
| 위치 | 변경 내용 |
|------|----------|
| §1.2 이후 | **신규 섹션**: Pipeline E — LinkedIn/BrightData 외부 데이터 통합 (E-1 프로필 정규화, E-2 Chapter 보강, E-3 Organization 교차) |
| 파이프라인 B/B' 부근 | **신규 섹션**: SIE 모델 통합 — 사전 추출 단계, 하이브리드 라우팅 (GLiNER2 vs NuExtract 1.5) |

### 03_prompt_design.md
| 위치 | 변경 내용 |
|------|----------|
| §0 설계 원칙 | 6번 원칙 추가: SIE 모델 사전 추출 → LLM 프롬프트 컨텍스트 제공으로 정확도 향상 및 토큰 절감 |

### 05_extraction_operations.md
| 위치 | 변경 내용 |
|------|----------|
| 문서 말미 | **신규 §5**: LinkedIn 데이터 동기화 전략 — 초기 적재(2.0M), AI 표준화(2.7M), 증분 처리, Organization ER 3차 패스 |

### 06_normalization.md
| 위치 | 변경 내용 |
|------|----------|
| 정규화 과제 섹션 | **신규 3개 과제**: 구코드→신코드 학교 매핑(Critical), 직무 코드 계층화(Medium), 캠퍼스 코드 정리(Low) |
| 회사명 정규화 | LinkedIn company_id 3차 교차 추가, Organization 고유 회사명 수 LinkedIn 포함 갱신 |

### 07_data_quality.md
| 위치 | 변경 내용 |
|------|----------|
| 문서 말미 | **신규 §7**: LinkedIn 외부 데이터 품질 — 8개 지표 (총 프로필, 경력 보유율, company 유니크, AI 표준화 등) |

---

## 03.graphrag/separate/v8/ 변경 상세

### interface/implementation_roadmap.md
| 위치 | 변경 내용 |
|------|----------|
| Phase 4 이후 | **신규**: Phase 5 외부 데이터 통합 — LinkedIn 회사명 교차, Chapter 보강, scope_type/Role 보강, 데이터 규모 |

### interface/02_tasks.md
| 위치 | 변경 내용 |
|------|----------|
| Task 목록 말미 | **신규**: Phase 5 태스크 3건 (T5-1 Organization 교차, T5-2 Chapter 보강, T5-3 scope_type 교차 검증) |

### sf/00_sf_overview.md
| 위치 | 변경 내용 |
|------|----------|
| 문서 말미 | Phase 5 확장 노트 (LinkedIn/BrightData 2.0M 통합 예정) |

### sf/01_sf_phase0_poc.md
| 위치 | 변경 내용 |
|------|----------|
| PoC 섹션 | SIE 모델 PoC 병행 검증 노트 (LLM 단독 vs SIE+LLM 하이브리드 비교) |

### sf/02_sf_phase1_preprocessing.md
| 위치 | 변경 내용 |
|------|----------|
| 전처리 섹션 | SIE 사전 추출 통합 노트 (GLiNER2 → LLM 컨텍스트 제공) |

### graphrag/04_graphrag_g3_matching.md
| 위치 | 변경 내용 |
|------|----------|
| Organization ER 부근 | Organization ER 3차 패스 — LinkedIn company_id 교차, resume-hub + LinkedIn 통합 통계 |

### graphrag/05_graphrag_g4_ops.md
| 위치 | 변경 내용 |
|------|----------|
| 증분 처리 부근 | LinkedIn 증분 동기화 — BrightData delta → R7/R8 연계 |

---

## 변경하지 않은 파일 (변경 불필요)

| 파일 | 사유 |
|------|------|
| `01.ontology/v25/01_company_context.md` | v3 신규 내용이 CompanyContext에 직접 영향 없음 (LinkedIn은 후보측 데이터) |
| `01.ontology/v25/03_mapping_features.md` | F1-F5 계산 로직 변경 없음, 데이터 가용성 변화는 다른 문서에서 커버 |
| `01.ontology/v25/05_evaluation_strategy.md` | graphrag로 리다이렉트만 있는 파일 |
| `02.knowledge_graph/v18/02_model_and_infrastructure.md` | SIE 모델은 LLM이 아닌 별도 모델, 이 문서 범위 밖 |
| `02.knowledge_graph/v18/04_pii_and_validation.md` | LinkedIn 데이터 PII는 Phase 5에서 별도 정의 필요 |
| `03.graphrag/separate/v8/graphrag/` 나머지 | v3 내용이 직접 영향을 미치지 않는 파일들 (setup, MVP, scale, cost, schema, serving, evaluation) |
