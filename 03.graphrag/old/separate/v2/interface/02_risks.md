# 팀 분리 리스크 + 완화 방안 (S&F ↔ GraphRAG 공동)

> 팀 분리로 인해 **새롭게 발생하거나 증폭**되는 리스크를 정의한다.
> v5 리뷰 리스크 매트릭스 + VG4 §3 기반.

---

## 1. 5대 리스크 매트릭스

| # | 리스크 | 위험도 | 발생 시나리오 | 비즈니스 영향 | 완화 방안 | 담당 |
|---|--------|:---:|-------------|-------------|---------|------|
| R1 | **필터링 역전 (Top-K 부족)** | **High** | S&F API가 100건만 넘기면 진짜 적합 후보가 잘림 | 매칭 품질 치명적 저하 | Top-K를 500~1,000건(10배)으로 Data Contract 명문화. G-3 통합 테스트에서 Top-K 충분성 검증 | **공동** |
| R2 | **S&F 산출물 지연** | **High** | W10~15 Batch 600K 에러/지연 → GraphRAG G-2 개발 정지 | 프로젝트 일정 지연 | PubSub 자동 트리거 + Mock Data로 선행 개발 + 주간 싱크 리포트 + W12 중간 체크포인트(R6) | **S&F** (리포트) |
| R3 | **API 체인 레이턴시 초과** | **Medium** | 2-Tier 연속 호출로 사용자 체감 > 5초 | UX 치명적 저하 | SLA p95 < 3s 엄수, min-instances=1($10~15/월), 캐싱, IN-list 축소(500→200) | **공동** |
| R4 | **Data Contract 스키마 충돌** | **Medium** | S&F가 필드명 변경 → Cypher 쿼리 실패 → 적재 파이프라인 장애 | 적재 파이프라인 장애 | JSON Schema Git 버저닝 + Phase별 Integration Test + 스키마 변경 시 주간 싱크에서 사전 공지 필수 | **공동** |
| R5 | **팀 분리 경계 모호** | **Medium** | 역할 혼동 → 중복 작업 또는 누락 | 책임 공백 | 73개 태스크 분류 테이블 참조 + 주간 싱크 회의 + 의사결정 포인트 14건 명확화 | **공동** |

---

## 2. v5 리스크 중 팀 분리 관련 항목

v5 리뷰 리스크 매트릭스에서 팀 분리 시 **증폭 또는 변형**되는 리스크:

| v5 리스크 | 등급 | 분리 시 변화 | 대응 |
|----------|------|-----------|------|
| Phase 2 기본 시나리오 여유 0일 | **MEDIUM** | S&F 단독 리스크로 이관. **GraphRAG에도 연쇄 영향** (R2) | W10 체크: 라운드 18h 초과 시 비관 대응 발동 |
| Batch API 동시 한도 < 5 | **MEDIUM** | S&F 단독 관리. GraphRAG에 간접 영향 (산출물 지연) | S&F가 Gemini 대안 병행 (N5) |
| Hybrid 섹션 분리 성공률 < 70% | **MEDIUM** | S&F 단독. LLM 폴백 증가 → 비용·시간 영향 | R4 패턴→LLM 폴백 Batch 설계로 완화 |
| JD 파서 API 스펙 미확정 | **MEDIUM** | S&F가 JD 파싱 담당. **v5 A1 대응 절차 적용** | 미확정 시 0.5주→1주 확장 |
| Gold Label 비용 과다 | **LOW** | GraphRAG 단독. **국내 전문가 대안 사전 검토 필요** | W22~23에 국내 대안($730~1,460) 검토 |

---

## 3. 스키마 변경 관리 절차 (R4 완화)

```
스키마 변경 프로세스:
  1. 변경 요청자가 주간 싱크에서 사전 공지 (최소 1주 전)
  2. JSON Schema 변경 PR 생성 → 양쪽 팀 리뷰
  3. Integration Test 통과 확인
  4. 변경 적용 + PubSub message에 schema_version 속성 추가
  5. 적재 코드에서 schema_version별 분기 처리 (하위 호환)

JSON Schema 버저닝:
  gs://kg-artifacts/schema/candidate_v1.json
  gs://kg-artifacts/schema/vacancy_v1.json
  gs://kg-artifacts/schema/company_enrichment_v1.json
```

---

## 4. 실행 단계 체크리스트 (v5 리뷰 E1~E5)

> 문서 수정 불필요, 실행 시 인지 항목

| # | 내용 | 시점 | 관련 리스크 | 담당 |
|---|------|------|----------|------|
| E1 | Batch API 라운드 시간 실측 → **18h 초과 시 비관 대응 발동** | W10 | R2, Phase 2 여유 0일 | S&F |
| E2 | Phase 3-1 JD 파서 0.5주 가능 여부 확인 (job-hub API 스펙) | W16 | JD 파서 미확정 | S&F |
| E3 | Gold Label 전문가 확보 + **국내 대안 사전 검토 ($730~1,460)** | W22~23 | Gold Label 비용 | GraphRAG |
| E4 | Cloud Run cold start 대응 결정 (min-instances vs Scheduler) | W27 | R3 | GraphRAG |
| E5 | 문서 수정 시 변경 이력 관리 → 분리 구조이므로 각 팀 문서 내 관리 | 수시 | — | 각 팀 |
