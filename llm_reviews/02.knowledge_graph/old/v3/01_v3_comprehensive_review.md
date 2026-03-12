# v3 계획 종합 리뷰 — 실현 가능성, 과설계, 부족 설계 분석

> v3 계획 5개 문서를 독립적으로 재검토한다.
> 기존 리뷰(00_v3_plan_review.md)에서 다루지 않은 관점을 중점적으로 분석한다.
>
> 리뷰일: 2026-03-08

---

## 1. 실현 가능성 분석

### 1.1 [Critical] 인력 × 일정 현실성

v3는 DE 1명 + MLE 1명으로 14~18주를 제시한다. 각 Phase의 작업량을 점검하면:

| Phase | 기간 | 주요 작업 | 1인당 병렬 가능 여부 | 판정 |
|---|---|---|---|---|
| 0 (기반+PoC) | 3~4주 | 데이터 탐색 + LLM PoC + 인프라 셋업 + PII 법무 | DE/MLE 분업 가능 | **적절** |
| 1-1 (전처리) | 2주 | PDF/DOCX/HWP 파서 + 섹션분할 + PII 마스킹 + 기술사전 | DE 주도, MLE 프롬프트 병행 | **빠듯함** |
| 1-2 (CompanyCtx) | 1~2주 | NICE 연동 + Rule 엔진 + LLM 프롬프트 + 통합테스트 100건 | MLE 주도 | **적절** |
| 1-3 (CandidateCtx) | 3주 | Rule 추출 + LLM 프롬프트 3종 + NICE 역산 + 통합테스트 200건 + Batch API | MLE 주도, DE 배치 인프라 | **빠듯함** |
| 1-4 (Graph) | 1주 | Neo4j 로더 2종 + Entity Resolution + Vector Index + Cypher 테스트 | DE 주도 | **위험** |
| 1-5 (Mapping) | 1주 | 5개 피처 계산 + BigQuery + 50건 검증 | DE/MLE 공동 | **적절** |
| 2-1 (전체처리) | 2~3주 | 500K 배치 + 에러 핸들링 + 모니터링 대시보드 + Neo4j 전환 | DE 주도 | **적절** |
| 2-2 (품질평가) | 1주 | Gold set 400건 + 평가지표 8종 + 캘리브레이션 | MLE 주도, 도메인 전문가 | **빠듯함** |

**핵심 병목**: Phase 1-4 (Graph 적재, 1주)가 가장 위험하다.
- Entity Resolution은 "회사명 정규화 사전 구축"만으로 해결되지 않는다
- Organization 노드의 MERGE 전략 (name vs org_id)이 혼재 — 02 §4.1에서는 `org_id`로 MERGE, §4.2에서는 `name`으로 MERGE. 이 불일치를 해결하고 정규화 파이프라인을 구축하는 데 1주는 부족
- **권장**: Phase 1-4를 2주로 확장하거나, Entity Resolution을 Phase 2로 분리

### 1.2 [High] PII 마스킹의 구현 복잡도 과소평가

05 §2.1에서 마스킹 전략을 `이름 → [NAME], 연락처 → [PHONE], 주소 → [ADDR] 치환`으로 설명하지만:

1. **span offset 보존**: 마스킹으로 문자열 길이가 바뀌면 LLM 추출 결과의 evidence_span이 원본과 불일치. 이를 역매핑하는 로직이 필요하며, 이는 비자명한 구현
2. **한국어 이름 NER**: "김철수 팀장", "김 대리" 등 다양한 패턴. 한국어 이름 인식은 단순 regex로 80% 이상 커버하기 어려움
3. **마스킹 후 LLM 품질 영향**: "[NAME]이 [COMPANY]에서 근무하며..."와 같은 마스킹 텍스트가 LLM의 추출 품질에 미치는 영향이 **미측정**

**권장**: Phase 0 PoC에서 "마스킹 전후 추출 품질 비교"를 반드시 포함할 것

### 1.3 [Medium] Gold Label 400건의 분석 범위 한계

04 §2-2에서 "전문가 2인 × 200건 독립 annotation"으로 Gold set을 구축한다.

- 400건은 **전체 정확도 추정에는 충분**하다 (70% 정확도 기준, 95% CI ±4.5%)
- 그러나 **클래스별(scope_type 5개) / 직군별(5개) 세분화 분석에는 부족**할 수 있음
- 직무 5개 직군 × 경력 수준 3단계로 층화 추출하면 층당 ~27건으로 세밀한 분석은 제한적

**권장**: 400건으로 가능한 분석 범위(전체 정확도, inter-annotator agreement)를 명시하고, 클래스별 상세 분석이 필요하면 Phase 2 결과 후 Gold set 확대 여부를 결정하는 형태로 정리

### 1.4 [Medium] HWP 파싱 신뢰도

02 §3.1에서 `python-hwp / LibreOffice headless`를 제시하지만:
- `python-hwp`는 2026-03 기준 유지보수가 활발하지 않음
- LibreOffice headless 변환은 레이아웃/표가 깨질 수 있음
- 05 §2.3에서 "HWP → LibreOffice headless → DOCX/PDF로 우회"를 완화 전략으로 제시했으나, 이 우회 자체가 품질 손실을 동반

**판정**: HWP 비율이 10%(가정 A11)이면 관리 가능하나, 40%이면 전용 파서 개발 또는 상용 솔루션 검토 필요. Phase 0에서 확인 예정이므로 **현재 수준으로 충분**.

---

## 2. 과설계 (Over-engineering) 분석

### 2.1 [Medium] ML Knowledge Distillation — ROI 의문

02 §9에서 "ML 대체 범위가 제한적"이라고 스스로 인정하면서도 04 §2-3에 1~2주를 배정한다.

- **절감 효과**: 500K 기준 약 $250 (Batch 기준)
- **투자 비용**: MLE 1명 × 1~2주 인건비 ($2,500~$5,000 추정)
- **ROI**: 마이너스 (1회 처리 기준), 최소 10~20회 재처리해야 투자 회수

"선택적"이라 명시했으나, 실행 계획과 타임라인에 포함되어 있어 실무적으로는 "예정된 작업"으로 인식될 위험이 있다.

**권장**: Phase 2에서 명시적으로 "skip 기본, 투자 트리거 조건" 형태로 재정의. 예: "scope_type LLM 추출 정확도 < 70% AND 재처리 빈도 > 월 1회일 때만 투자"

### 2.2 [Low] operating_model LLM "광고성 필터링" — 불필요한 복잡도

02 §2.4의 `llm_assess_authenticity` 함수가 JD 내 키워드의 "진정성"을 LLM으로 평가한다.

- JD에 "자율적 업무 환경"이라고 쓰여 있어도 실제로 그런지는 JD만으로 판단 불가
- LLM "보정"이 오히려 **noise를 추가**할 위험 (JD의 tone을 과해석)
- v4 온톨로지 자체가 operating_model의 confidence를 낮게(0.20~0.60) 설정했는데, 거기에 LLM 보정까지 추가하면 **이중 불확실성**

**권장**: v1에서는 키워드 카운트만으로 operating_model을 산출하고, LLM 보정은 Phase 3으로 이동. confidence를 낮게 유지하면 MappingFeatures에서 자동으로 가중치가 줄어든다.

### 2.3 [Low] Vacancy → NEEDS_SIGNAL 엣지 (Graph) — 용도 명확화 필요

02 §4.1에서 `infer_vacancy_signals(company_ctx.vacancy)`로 Vacancy에서 signal을 추론하여 Graph에 적재한다.

- 이 추론은 MappingFeatures의 `vacancy_fit` 계산과 **동일한 로직**을 중복 적재하는 면이 있음
- 다만, Graph traversal 쿼리(예: "이 포지션과 유사한 경험을 가진 후보 탐색")에서 유용할 수 있음
- `inferred: true` 플래그가 있으나, Graph 쿼리에서 이를 필터링하는 지침이 없음

**권장**: NEEDS_SIGNAL 엣지의 **주요 소비자**(Graph 쿼리 vs MappingFeatures)를 명시하고, Graph 쿼리 가이드에 `inferred` 필터링 지침을 추가. 만약 MappingFeatures에서만 사용한다면 Graph 적재를 생략하는 것이 더 깔끔.

---

## 3. 부족 설계 (Under-engineering) 분석

### 3.1 [Critical] "상위 500 후보" 선정 기준 미정의

02 §6에서 매핑 대상 쌍을 "JD × 상위 후보 500명 = 500만 쌍"으로 가정하지만, **"상위 500명"을 어떻게 선정하는지**가 정의되어 있지 않다.

- 전수 매핑(500K × 10K = 50억)은 비현실적이므로, **후보 축소 전략이 반드시 필요**
- 방법론 후보: (1) embedding 기반 ANN (2) domain/industry 필터 (3) rule-based pre-filter (기술스택/경력연수 조건)
- 방법에 따라 인프라 요구사항이 달라짐 (ANN이면 별도 인덱스 서빙 필요)
- 이것이 Pipeline D(MappingFeatures 계산)의 **전제 조건**

05 §A9에서 "비용 영향 작음"이라 했으나, 이는 MappingFeatures 계산 비용이 낮다는 의미이지, 후보 선정 자체의 인프라/설계 비용을 다루지 않는다.

**권장**: 02 또는 04에 "Candidate Shortlisting 전략" 섹션을 추가하고, 방법론과 예상 인프라를 최소 수준으로 정의할 것. 이 단계가 KG 구축 범위(create-kg)인지 서빙 시스템 범위인지도 명확히 할 것.

### 3.2 [High] Neo4j 트랜잭션 성능 — 대량 적재 전략 부재

02 §8.3에서 "Neo4j Transaction 배치: 100건/트랜잭션, 병렬 worker 4~8개"로 기술했지만:

- 500K 이력서 × 평균 10 노드 + 15 엣지 = ~1,250만 write 연산
- 100건/TX × 4 worker에서 예상 처리 속도: 실제로는 MERGE 비용, 인덱스 업데이트, lock 경합으로 이상적 계산보다 **2~3배 느림**
- **Vector Index 적재**: embedding 150만 건의 HNSW 빌드는 별도 시간이 상당히 소요
- 초기 적재(500K 전체)와 증분 적재의 전략이 구분되어 있지 않음

**참고**: Neo4j AuraDB(관리형)에서는 `neo4j-admin import`를 직접 사용할 수 없으므로, APOC `apoc.periodic.iterate`를 활용한 대량 적재 또는 CSV import 기능을 활용해야 한다.

**권장**:
- 초기 적재와 증분 적재의 전략을 명시적으로 구분
- AuraDB 환경에서의 대량 적재 방법(APOC batch / `LOAD CSV` / neo4j data importer) 검토
- 04 Phase 1-4에 "1,000건 적재 벤치마크" 항목 추가하여 전체 적재 시간 추정

### 3.3 [High] Embedding 모델의 한국어 성능 검증 계획 부재

03 §2.1에서 `text-embedding-3-small`을 MVP 추천하면서 한국어 성능을 "양호"로 평가했지만:

- domain_fit은 embedding cosine similarity가 **핵심 계산**
- 한국어 이력서/JD의 도메인 텍스트는 "핀테크 백엔드 개발", "이커머스 데이터 분석" 등 짧은 텍스트
- 짧은 한국어 텍스트에서 text-embedding-3-small의 cosine similarity 분별력이 검증되지 않음
- Phase 0 PoC에 embedding 모델 비교가 **포함되어 있지 않음**

**권장**: Phase 0 PoC에 "embedding 모델 비교 (text-embedding-3-small vs Cohere multilingual vs BGE-M3)"를 추가. 20쌍의 (이력서 도메인, JD 도메인) 텍스트로 cosine similarity 분별력 테스트.

### 3.4 [Medium] 프롬프트 버전 관리 전략 미명시

04의 운영 전략에서 `prompt_version` 메타데이터를 Graph 노드에 부착한다고 했지만, 프롬프트 버전 관리의 구체적 방법이 명시되어 있지 않다.

- 프롬프트 파일의 관리 방식 (프로젝트 Git 리포에 포함? 별도 관리?)
- 프롬프트 변경 시 회귀 테스트 절차

**권장**: 간단한 전략 — "프롬프트 파일은 프로젝트 리포의 `prompts/` 디렉토리에 버전별 관리, 변경 시 50건 고정 테스트셋으로 회귀 테스트 실행" 정도면 충분. A/B 테스트 프레임워크는 Phase 3 범위.

### 3.5 [Medium] evidence_span 후처리 검증 로직 부재

02의 모든 LLM 프롬프트에 "근거 문장(span)을 원문에서 인용하세요"라고 지시하지만, **LLM이 실제로 원문에서 인용했는지 검증하는 후처리 로직**이 없다.

- LLM이 원문에 없는 span을 생성할 수 있음 (hallucination)
- 검증 방법: `evidence_span in original_text` 문자열 포함 검사
- span이 원문에 없으면 해당 추출 결과의 confidence를 자동 하향 (예: × 0.5)

**권장**: 02 §8.1 에러 핸들링에 "evidence_span 검증" 단계 추가

### 3.6 [Medium] CandidateContext의 LLM 호출 최적화 미흡

02 §3.2에서 이력서 1건당 LLM을 **경력 수 + 1회** 호출한다 (경력 3건이면 4회).

- 경력 블록이 짧은 경우 (200~500 토큰), 개별 호출보다 **이력서 전체를 1회 호출**하는 것이 효율적일 수 있음
- Haiku의 context window (200K)에 이력서 전체 + 프롬프트가 충분히 들어감
- 1회 호출 시: 총 토큰은 비슷하되, API 오버헤드(latency, batch 건수) 대폭 감소
- Batch API에서 건수가 줄면 처리 속도도 빨라짐

**트레이드오프**: 1회 호출 시 출력 JSON이 복잡해져 파싱 실패율이 올라갈 수 있음

**권장**: Phase 0 PoC에서 "경력별 개별 호출 vs 이력서 전체 1회 호출" 비교 실험 추가

---

## 4. 비용 모델 검증

### 4.1 비용 추정의 정확도

03 시나리오 A 총비용 $9,005는 합리적이나, 몇 가지 누락/과소평가가 있다:

| 항목 | 현재 추정 | 누락/과소 | 수정 추정 |
|---|---|---|---|
| PII 마스킹 개발 | 미포함 | 한국어 이름 NER + span offset 보존 구현 | 개발 인건비에 포함되지만 일정 영향 |
| Candidate Shortlisting | 미포함 | 후보 축소 전략의 인프라 비용 | 방법에 따라 $0~$500/년 |
| Embedding 모델 평가 | 미포함 | PoC에서 3개 모델 비교 | ~$50 |
| 프롬프트 최적화 | $200 | 3개 프롬프트 × 10~15회 반복이 현실적 | $500~$800 |

**수정 시나리오 A 총비용**: ~$9,500~$10,500 (주요 누락 반영 시). 큰 차이는 아니며, 03의 추정은 합리적 범위.

### 4.2 비용 낙관 편향

전반적으로 "정상 경로(happy path)" 기준 비용이며, 재처리/디버깅/프롬프트 반복 비용이 과소평가되어 있다. 실무 경험상 LLM 기반 파이프라인의 프롬프트 최적화에는 **계획 대비 2~3배의 반복**이 필요하다.

03 §5.1에서 "프롬프트 최적화 LLM 비용 $200"은 50건 × 4~5회를 가정하지만, 3개 프롬프트(Experience, Career, Vacancy) × 10~15회 반복이 더 현실적. **$500~$800** 수준.

---

## 5. 설계 일관성 이슈

### 5.1 [Medium] Organization MERGE 전략 불일치

02 §4.1 (CompanyContext → Graph):
```cypher
MERGE (o:Organization {org_id: $org_id})
```

02 §4.2 (CandidateContext → Graph):
```cypher
MERGE (o:Organization {name: $company_name})
```

동일한 Organization 노드를 `org_id`와 `name`으로 각각 MERGE하면 **중복 노드 생성** 위험. Entity Resolution이 이를 해결해야 하지만, 그 구체적 로직이 정의되지 않았다.

**권장**: Organization은 `org_id`를 canonical key로 통일. CandidateContext에서 회사명 → org_id 매핑은 Entity Resolution 단계에서 수행.

### 5.2 [Low] Embedding 대상 텍스트 불명확

02 §4.3에서 `chapter.evidence_chunk`를 embedding 대상으로 사용하지만:
- evidence_chunk가 정확히 어떤 텍스트인지 정의되지 않음 (원문 전체? scope_summary? outcomes 텍스트?)
- domain_fit 계산 시의 embedding 대상 텍스트와 Vector Index용 embedding 대상이 동일한지 불명확

---

## 6. 종합 판정

### 전체 완성도: 양호~우수

v3 계획은 v4 온톨로지에 대한 깊은 이해를 바탕으로 한 잘 설계된 계획이다. 에러 핸들링, 운영 전략, 비용 모델 모두 실무적으로 유용한 수준이다.

### 즉시 실행 가능 여부: 조건부 가능

아래 3가지가 해결되어야 한다:

1. **Candidate Shortlisting 전략 정의** (Critical) — Pipeline D의 전제 조건
2. **Organization MERGE 전략 통일** (Medium) — Graph 데이터 무결성
3. **Phase 0 PoC 범위 확장** (High) — PII 마스킹 영향, embedding 모델 비교, 호출 전략 비교 포함

### 개선 권장 사항 (우선순위순)

| 우선순위 | 항목 | 조치 | v4 반영 필요 |
|---|---|---|---|
| **Critical** | Candidate Shortlisting 전략 | 방법론 + 범위 명확화 (KG 범위 vs 서빙 범위) | **O** |
| **High** | Neo4j 초기 vs 증분 적재 전략 분리 | AuraDB 대량 적재 방법 검토 + 벤치마크 | **O** |
| **High** | Phase 0 PoC 범위 확장 | PII 영향, embedding 비교, 호출 전략 비교 | **O** |
| **High** | Embedding 모델 한국어 검증 | PoC에 비교 실험 추가 | **O** |
| **Medium** | Organization MERGE 전략 통일 | org_id 기반 통일 + 매핑 로직 | **O** |
| **Medium** | evidence_span 후처리 검증 | 원문 포함 여부 검사 로직 추가 | **O** |
| **Medium** | 프롬프트 버전 관리 전략 | Git 관리 + 회귀 테스트 절차 명시 | **O** |
| **Medium** | Gold set 분석 범위 명시 | 400건 기준 가능/불가능 분석 범위 기술 | 선택 |
| **Medium** | ML Distillation ROI 재정의 | skip 기본, 투자 트리거 조건 명시 | 선택 |
| **Low** | operating_model LLM 보정 제거 | v1은 키워드만, LLM 보정은 Phase 3 | 선택 |
| **Low** | NEEDS_SIGNAL 엣지 용도 명확화 | 소비자 + 쿼리 필터링 지침 | 선택 |
| **Low** | LLM 호출 최적화 (1회 통합) | PoC에서 비교 실험 | 선택 |

> **"v4 반영 필요 = O"인 항목**: v4 계획에 반영하면 계획의 품질이 의미 있게 향상되는 항목.
> **"선택"인 항목**: 현재 수준으로도 실행 가능하며, Phase 진행 중 자연스럽게 보완 가능한 항목.
