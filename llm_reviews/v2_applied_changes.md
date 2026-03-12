# v2 리뷰 반영 Changelog

> **리뷰 원본**: `llm_reviews/v2.md`
> **반영일**: 2026-03-13
> **대상 버전 변경**: `01.ontology/v20→v21`, `02.knowledge_graph/v13→v14`, `03.graphrag/separate/v3→v4`

---

## 요약

v2.md 리뷰에서 식별된 CRITICAL/HIGH/MEDIUM/LOW 항목 중 **19건**을 3개 디렉토리에 걸쳐 13개 파일에 반영하였다.

| 심각도 | 반영 | 보류 | 사유 |
|--------|------|------|------|
| CRITICAL | 4 | 0 | — |
| HIGH | 8 | 0 | — |
| MEDIUM | 5 | 0 | — |
| LOW | 2 | 0 | — |

---

## 01.ontology/ (v20 → v21)

### 1. freshness_weight 듀얼 모드 지원 — CRITICAL
- **파일**: `00_data_source_mapping.md`
- **내용**: `compute_freshness_weight` 함수를 step/smooth(지수감쇠, half_life_days=958) 듀얼 모드로 교체
- **리뷰 근거**: step function의 불연속 구간이 랭킹에 민감한 영향을 줄 수 있음

### 2. designation_codes Phase 0 검증 노트 — HIGH
- **파일**: `00_data_source_mapping.md`
- **내용**: NICE 업종코드와 자기기입 업종 불일치율 30%+ 시 confidence cap 0.55 적용 방안 추가
- **리뷰 근거**: 데이터 소스 간 불일치율이 높을 수 있어 Phase 0에서 사전 검증 필요

### 3. STAGE_SIMILARITY 비대칭 근거 명시 — HIGH
- **파일**: `03_mapping_features.md`
- **내용**: 행렬 비대칭 가정("대기업→스타트업 적응이 역방향보다 용이")의 근거 코멘트 블록 추가
- **리뷰 근거**: 비대칭 가정이 문서화되지 않아 향후 유지보수 시 혼란 가능

### 4. REPLACE 공고 비율 모니터링 — MEDIUM
- **파일**: `03_mapping_features.md`
- **내용**: Phase 0에서 JD hiring_context 분포(REPLACE 비율) 모니터링 노트 추가
- **리뷰 근거**: REPLACE 공고 비율에 따라 매칭 전략 조정 필요

### 5. operating_model v1 ROI 리뷰 — MEDIUM
- **파일**: `01_company_context.md`
- **내용**: culture_fit이 대부분 INACTIVE인 v1에서 LLM facet 추출의 낮은 ROI에 대한 리뷰 노트 추가
- **리뷰 근거**: v1 스코프에서 operating_model 전체 추출은 비용 대비 효과 미미

---

## 02.knowledge_graph/ (v13 → v14)

### 6. Embedding 모델 통일 (text-embedding-005) — CRITICAL
- **파일**: `06_normalization.md`
- **내용**: `text-multilingual-embedding-002 (1536d)` → `text-embedding-005 (768d)`로 수정
- **리뷰 근거**: 01.ontology와 03.graphrag는 이미 text-embedding-005 사용, 02만 구 모델 참조 중

### 7. PII 처리 책임 경계 명확화 — CRITICAL
- **파일**: `04_pii_and_validation.md`
- **내용**: 모호한 PII 노트를 `[v14 CRITICAL]` 콜아웃으로 교체, W0 시점 S&F팀/데이터플랫폼팀 결정 필수 명시
- **리뷰 근거**: PII 처리 주체가 불명확하면 Phase 1 진입 불가

### 8. CareerDescription 귀속 정확도 요건 — HIGH
- **파일**: `01_extraction_pipeline.md`
- **내용**: career_id FK 부재 시 LLM 귀속 실패 confidence 감쇠(0.6x), SelfIntroduction 폴백 감쇠(0.5x), Phase 0 정확도 임계값 60% 추가
- **리뷰 근거**: FK 없는 귀속의 품질 리스크가 문서화되지 않음

### 9. HWP 파서 3단계 폴백 — HIGH
- **파일**: `01_extraction_pipeline.md`
- **내용**: hwp5 → Gemini Multimodal → LibreOffice CLI 3rd 폴백 전략 추가
- **리뷰 근거**: hwp5 + Gemini로 처리 불가 케이스 대비 필요

### 10. Gold Set vs 통계 샘플링 역할 구분 — MEDIUM
- **파일**: `05_extraction_operations.md`
- **내용**: Gold Set(50→200건, 회귀 테스트)과 통계 샘플링(384건, 품질 검증)의 상이한 역할 설명 추가
- **리뷰 근거**: 두 평가 방식의 목적 혼동 방지

---

## 03.graphrag/ (separate/v3 → v4)

### 11. Neo4j 벡터 인덱스 차원 수정 — CRITICAL
- **파일**: `graphrag/07_neo4j_schema.md`
- **내용**: 벡터 인덱스 dimension `1536 → 768`, 임베딩 모델 참조 통일 (text-embedding-005)
- **리뷰 근거**: 01/02와 동일 모델 사용해야 하며, 차원 불일치 시 런타임 에러

### 12. 스케일 추정치 스코프 명확화 — HIGH
- **파일**: `graphrag/07_neo4j_schema.md`
- **내용**: 3.2M Person(전체 풀) vs 600K Person(v1 초기 스코프) 병기 및 범위 명시
- **리뷰 근거**: 01_extraction_pipeline.md(600K)와 07_neo4j_schema.md(3.2M) 간 불일치 혼란

### 13. Neo4j 티어 Phase 0 의사결정 — HIGH
- **파일**: `graphrag/07_neo4j_schema.md`
- **내용**: 27M 노드가 Professional 티어 한계 초과 가능, Enterprise 시나리오(+$645~1,140) 추가
- **리뷰 근거**: 비용 계획에 Enterprise 시나리오 누락

### 14. 평가 문서 임베딩 모델 통일 — HIGH
- **파일**: `graphrag/09_evaluation.md`
- **내용**: baseline config 및 데이터 흐름도의 임베딩 모델을 text-embedding-005 (768d)로 통일
- **리뷰 근거**: 평가 파이프라인과 프로덕션 파이프라인의 모델 일치 필수

### 15. Go/No-Go 결정 포인트 추가 — HIGH
- **파일**: `interface/01_go_nogo_decisions.md`
- **내용**: PII 책임(W0), Neo4j 티어(W1), 크롤링 법적 검토(W4) 3개 결정 포인트 추가
- **리뷰 근거**: 주요 블로커가 Go/No-Go 체크리스트에 누락

### 16. Enterprise 비용 시나리오 및 FTE — MEDIUM
- **파일**: `graphrag/06_graphrag_cost.md`
- **내용**: Enterprise 비용 테이블(+$645~1,140), 운영 FTE 추정(0.5 FTE) 추가
- **리뷰 근거**: Professional 초과 시 비용 점프폭이 크므로 사전 시나리오 필요

### 17. Anthropic Batch API 가격 의존성 리스크 — MEDIUM
- **파일**: `graphrag/06_graphrag_cost.md`
- **내용**: Provider abstraction을 Phase 0에서 구현 권고, 가격 변동 리스크 노트 추가
- **리뷰 근거**: 단일 프로바이더 의존은 비용 예측 리스크

### 18. 대기 기간 활용 구체화 — LOW
- **파일**: `graphrag/00_graphrag_overview.md`
- **내용**: Wait A(데이터 확인/PII 결정), Wait B(Neo4j 티어 확정/크롤링 법적 검토) 구체 태스크 명시
- **리뷰 근거**: 대기 기간에 수행할 작업이 불명확

### 19. Phase 1 소규모 매칭 시뮬레이션 — LOW
- **파일**: `graphrag/04_graphrag_g3_matching.md`
- **내용**: Phase 3 전체 시뮬레이션 전 Phase 1 소규모(JD 10 × Person 1K) 시뮬레이션 단계 추가
- **리뷰 근거**: 전체 시뮬레이션 전 빠른 피드백 루프 확보
