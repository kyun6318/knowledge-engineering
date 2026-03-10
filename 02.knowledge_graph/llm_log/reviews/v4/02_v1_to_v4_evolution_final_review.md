# v1 → v4 전체 진화 최종 리뷰

> v1(4개 문서) → v2(5개) → v3(5개) → v4(5개), 총 19개 계획 문서를 통독하고
> 각 버전의 변경 사항이 최종 v4에 올바르게 반영되어 있는지 검증한다.
>
> 리뷰일: 2026-03-08

---

## 1. 버전별 핵심 변경 추적

### 1.1 v1 → v2: 방향 전환 (Critical)

v1은 범용 NER/RE 기반 KG 추출을 목표로 했으나, v4 온톨로지 요구사항과 근본적으로 불일치했다. v2에서 전면 재설계되었다.

| 변경 항목 | v1 | v2 | v4 최종 반영 상태 |
|---|---|---|---|
| 목표 | 범용 KG 추출 | v4 온톨로지 기반 Context 생성 | **반영됨** — 01 §1 |
| 스키마 | Person, Org, Skill, Role, Experience | Chapter, SituationalSignal, Outcome, Vacancy 등 추가 | **반영됨** — 02 전체 |
| 데이터 소스 | 이력서 150GB만 | JD + NICE + 이력서 | **반영됨** — 02 §1~§3 |
| 산출물 | Entity + Relation triples | CompanyContext + CandidateContext + Graph + MappingFeatures | **반영됨** — 02 §1 |
| 파이프라인 구조 | 단일 NER/RE | 5개 파이프라인 (A~E) | **반영됨** — 02 §1 |
| 하이브리드 비율 | Rule 60-70%, ML 20-30%, LLM 5-15% | Rule 25-35%, Embedding 10-15%, LLM 50-65% | **반영됨** — 01 §5.2 |
| 비용 모델 | 1,250만~4,800만 원 (범용 NER/RE) | $8,292~$16,804 (Context 생성) | **반영됨** — 03 전체 (v4: $9,255) |
| 실행 계획 | 6단계 로드맵 (기간 미정) | Phase 0-3, ~14주 | **반영됨** — 04 (v4: 16~19주) |

**검증 결과**: v1→v2 방향 전환은 v4에 **완전히 반영**되어 있다. v1의 범용 NER/RE 접근은 01(Gap 분석)에 기록되어 있고, v2에서 수립된 5개 파이프라인 구조가 v4까지 유지된다.

### 1.2 v2 → v3: 운영/실행 보강

v2의 설계 골격은 유지하되, 실행 가능성과 운영 안정성을 보강했다.

| 변경 항목 | v2 상태 | v3 변경 | v4 최종 반영 상태 |
|---|---|---|---|
| 에러 핸들링/retry | 미정의 | §8 Fail-safe 원칙 + retry 정책 | **반영됨** — 02 §8 |
| 배치 아키텍처 | 순차 처리 가정 | 500K 이력서 chunk 분할 + 동시 배치 | **반영됨** — 02 §8 |
| 프롬프트 통합 | vacancy/role 별도 프롬프트 | vacancy + role_expectations 단일 프롬프트 | **반영됨** — 02 §2.3 |
| 인력 배치 | 미명시 | DE 1 + MLE 1 + 도메인 전문가(PT) | **반영됨** — 04 서두 |
| 운영 전략 | 미정의 | 증분 처리, 롤백/재처리, Graph 업데이트 | **반영됨** — 04 운영 전략 |
| 타임라인 | ~14주 | 14~18주 (현실화) | **반영됨** — 04 (v4: 16~19주) |
| 테스트/모니터링 | 미정의 | 테스트 계층 + Grafana + BigQuery | **반영됨** — 04 |
| 비용 기준 | Standard API만 | Batch API 50% 할인 병기 | **반영됨** — 03 |
| Gold Label 비용 | 과소 추정 | 건당 30~40분 현실화 | **반영됨** — 03 |
| 오케스트레이션 비용 | 미포함 | $170 추가 | **반영됨** — 03 |
| SLM Distillation | 광범위 적용 가정 | 범위 축소 (scope_type만 현실적) | **반영됨** — 03 |
| 리스크 확장 | 12개 | 파싱+LLM 상관, Rate Limit, Model Pinning, 증분 처리, TTL 등 추가 | **반영됨** — 05 §2.3~§2.12 |

**검증 결과**: v2→v3 변경 사항은 v4에 **완전히 반영**되어 있다. v3에서 추가된 §8(에러 핸들링), §0(Fail-safe 원칙), 운영 전략 등이 v4에서도 동일하게 유지된다.

### 1.3 v3 → v4: 핵심 설계 결함 해결

v3 리뷰에서 지적된 Critical/High/Medium 이슈를 체계적으로 반영했다.

| 변경 항목 | v3 상태 | v4 변경 | 반영 위치 |
|---|---|---|---|
| **Candidate Shortlisting** (Critical) | 미정의 | 2단계 필터 (Rule pre-filter → ANN) + Neo4j Vector Index | 02 §5.0 |
| **Neo4j 적재 전략** (High) | Cypher MERGE만 | 초기: LOAD CSV + APOC batch / 증분: Cypher MERGE | 02 §4.4 |
| **Phase 0 PoC 범위** (High) | LLM 추출만 | +PII 마스킹 영향(10건) +embedding 비교(20쌍) +호출 전략(10건) | 04 Phase 0-2 |
| **Embedding 한국어 검증** (High) | 미고려 | PoC 실험 + 리스크 §2.14 + 가정 A16 | 04/05 |
| **Organization MERGE 통일** (Medium) | org_id(§4.1) vs name(§4.2) 불일치 | org_id canonical key + resolve_org_id() 3단계 매칭 | 02 §4.2~§4.3 |
| **evidence_span 검증** (Medium) | 없음 | validate_evidence_spans() + confidence 50% 감쇄 | 02 §8.2 |
| **프롬프트 버전 관리** (Medium) | 언급만 | Git 관리 + Golden Set 회귀 테스트 + 변경 절차 | 04 운영 전략 |
| **Embedding 텍스트 정의** | 미정의 | build_chapter/vacancy_embedding_text() 함수 | 02 §4.5 |
| **Phase 1-4 기간** | 1주 | 2주 (Entity Resolution + 벤치마크) | 04 Phase 1-4 |
| **프롬프트 최적화 비용** | $200 | $600 (현실화) | 03 |
| **Embedding 평가 비용** | 미포함 | $50 추가 | 03 |
| **타임라인** | 14~18주 | 16~19주 | 03/04 |
| **인건비** | $35,000~$70,000 | $40,000~$75,000 | 03 |

**검증 결과**: v3→v4 변경 사항은 **완전히 반영**되어 있다. v3 리뷰의 Critical 1건, High 3건, Medium 3건이 모두 해결되었다.

---

## 2. Cross-Reference 정합성 검증

v4 5개 문서 간의 상호 참조가 일관되는지 검증한다.

| 참조 관계 | 상태 | 비고 |
|---|---|---|
| 01 §5.6 → 02 §4.3, §4.4, §5.0, §8.2 | **정합** | v4 변경 사항 목록이 정확한 섹션 번호로 참조 |
| 02 §4.5 embedding 정의 → 03 embedding 비용 | **정합** | $50 평가 비용이 03에 반영 |
| 02 §5.0 Candidate Shortlisting → 04 Phase 1-5 | **정합** | Phase 1-5에 Shortlisting 구현 포함 |
| 03 타임라인 "16~19주" → 04 Phase 합계 | **정합** | Phase 0(3~4주) + Phase 1(8~10주) + Phase 2(3~4주) + Phase 3(시작) = 16~19주 |
| 03 인건비 "$40,000~$75,000" → 04 "16~19주" | **정합** | 16~19주 × $2,500~$3,950/주 ≈ $40,000~$75,000 |
| 04 Phase 0-2 PoC 3개 실험 → 05 A16, §2.13, §2.14 | **정합** | PII/embedding 리스크가 PoC 실험과 1:1 대응 |
| 05 가정 A16 → 02 §4.5, 04 Phase 0-2 | **정합** | embedding 한국어 분별력 검증이 일관되게 기술 |
| 03 비용 비교 "v1과 v4의 비용 차이" | **정합** | v3→v4 참조 오류 수정 완료 |

**검증 결과**: 문서 간 상호 참조가 **모두 정합**한다.

---

## 3. 버전 누적 변경의 정확성 검증

v1→v2→v3에서 추가된 내용이 v4에서 **실수로 삭제되거나 퇴행**하지 않았는지 확인한다.

### 3.1 v2에서 도입된 핵심 구조

| 항목 | v4 유지 여부 |
|---|---|
| 5개 파이프라인 (A~E) 구조 | **유지** — 02 §1 |
| CompanyContext/CandidateContext JSON 구조 | **유지** — 02 §2~§3 |
| LLM 프롬프트 (vacancy, candidate 추출) | **유지** — 02 §2.3, §3.3 |
| NICE 데이터 연동 (stage_estimate, org 정보) | **유지** — 02 §2.1, §4.3 |
| MappingFeatures 6개 피처 정의 | **유지** — 02 §5.1 |
| 4개 비용 시나리오 구조 | **유지** — 03 §5 |

### 3.2 v3에서 도입된 운영/안정성 요소

| 항목 | v4 유지 여부 |
|---|---|
| §0 Fail-safe 원칙 (모든 파이프라인 안전 우선) | **유지** — 02 §0 |
| §8 에러 핸들링 (retry 정책, 에러 유형별 처리) | **유지** — 02 §8 (§8.2 evidence 검증 추가) |
| §2.3 vacancy + role_expectations 통합 프롬프트 | **유지** — 02 §2.3 |
| 배치 처리 (chunk 분할, 동시 실행) | **유지** — 02 §8 |
| 테스트 계층 (Unit/Integration/E2E) | **유지** — 04 |
| 모니터링 (Grafana + BigQuery 로그) | **유지** — 04 |
| 증분 처리/롤백/재처리 운영 전략 | **유지** — 04 운영 전략 |
| Batch API 할인 비용 병기 | **유지** — 03 |
| 리스크 §2.3~§2.12 | **유지** — 05 |

### 3.3 퇴행 없음 확인

**v4에서 삭제되거나 퇴행된 v2/v3 요소: 없음.**

v4는 v2/v3의 모든 구조를 유지하면서 6개 주요 보강(Shortlisting, Entity Resolution, evidence 검증, Graph 적재 전략, embedding 정의, 프롬프트 관리)을 추가했다.

---

## 4. 미반영 항목 (의도적 유보)

v3 리뷰에서 지적되었으나 v4에서 **의도적으로 미반영**된 항목을 기록한다.

| 항목 | 심각도 | v4 상태 | 판정 |
|---|---|---|---|
| Gold set 400건 분석 범위 명시 | Low | 미반영 | Phase 2 결과 후 확대 가능, **현재 수준 충분** |
| ML Distillation 투자 트리거 구체화 | Low | "선택적"으로만 표기 | Phase 2 결과 보고 판단이 합리적, **현재 수준 충분** |
| operating_model LLM 보정 제거 | Low | v3 그대로 유지 | 비용 미미($1.50), **현재 수준 충분** |
| NEEDS_SIGNAL 엣지 용도 명확화 | Low | v3 그대로 유지 | 현재 기술 수준으로 충분, **문제 없음** |
| LLM 호출 최적화 (1회 통합) | Low | Phase 0 PoC에서 비교 실험으로 전환 | **적절한 대응** |

**판정**: 미반영 항목 5개 모두 Low 수준이며, 의도적 유보의 근거가 타당하다.

---

## 5. v4 자체 품질 이슈 (01_v4_comprehensive_review.md 요약)

별도 심층 리뷰(01 문서)에서 v4 자체의 실현 가능성, 과설계, 부족 설계를 분석했다. 주요 발견:

### 5.1 즉시 반영 권장 (High)

| 항목 | 요약 |
|---|---|
| Graph 적재 Idempotency | Vacancy/Outcome CREATE → deterministic MERGE 전환 필요 |
| 이력서 중복 처리 전략 | 동일인 다중 등록 시 canonical 선택 전략 부재 |
| Chapter/Outcome ID 생성 | deterministic ID 규칙 명시 필요 |
| 이력서 섹션 분할 커버리지 | Phase 0에서 파싱 단계별 성공률 측정 추가 필요 |

### 5.2 선택적 개선 (Medium)

| 항목 | 요약 |
|---|---|
| Phase 0 법무 기본값 전략 | 법무 미확정 시 기본 행동 명시 |
| evidence_span 정규화 | normalized_contains() 도입 |
| JD 갱신 cascade | Vacancy 업데이트 → MappingFeatures 재계산 |
| Confidence aggregation | vacancy_fit에 confidence 가중 도입 |
| domain_fit embedding 정의 | Vector Index와의 관계 명시 |

---

## 6. 최종 판정

### 6.1 버전 진화 추적 결과

| 검증 항목 | 결과 |
|---|---|
| v1→v2 방향 전환 반영 | **완전 반영** |
| v2→v3 운영/안정성 보강 반영 | **완전 반영** |
| v3→v4 핵심 설계 결함 해결 | **완전 반영** (Critical 1, High 3, Medium 3) |
| 문서 간 Cross-Reference 정합성 | **정합** |
| v2/v3 요소의 퇴행 여부 | **퇴행 없음** |
| 의도적 미반영 항목의 타당성 | **모두 타당** (Low 5건) |

### 6.2 v4 전체 진화 요약

```
v1 (범용 KG)
 ↓ [방향 전환] 스키마/파이프라인/비용 모델 전면 재설계
v2 (v4 온톨로지 정합)
 ↓ [운영 보강] 에러 핸들링, 배치, 모니터링, 운영 전략, 비용 현실화
v3 (실행 가능 수준)
 ↓ [설계 결함 해결] Entity Resolution, Shortlisting, evidence 검증, PoC 확장
v4 (즉시 실행 가능)
```

### 6.3 종합 평가

> v4 계획은 v1에서 v4까지의 **모든 누적 변경 사항이 정확하게 반영**되어 있다.
> 문서 간 상호 참조가 일관되고, 이전 버전 요소의 퇴행이 없으며,
> v3 리뷰의 핵심 지적 사항이 체계적으로 해결되었다.
>
> v4 계획은 **즉시 실행 가능한 수준**이며, 추가 버전(v5) 없이 Phase 0 PoC를 시작할 수 있다.
> 01_v4_comprehensive_review.md에서 발견된 High 이슈 4건은 Phase 0~1 실행 과정에서
> 반영하거나, 필요 시 v5로 보강할 수 있다.

### 6.4 리뷰 문서 목록

| 파일 | 역할 |
|---|---|
| `00_v4_plan_review.md` | v3 리뷰 지적 사항의 v4 반영 여부 점검 |
| `01_v4_comprehensive_review.md` | v4 자체의 실현 가능성, 과설계, 부족 설계 심층 분석 |
| `02_v1_to_v4_evolution_final_review.md` | v1→v4 전체 진화 추적 및 최종 검증 **(본 문서)** |
