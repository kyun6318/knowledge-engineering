# v11 과도한 설계 리뷰

> 대상: 02.knowledge_graph/results/extraction_logic/v11/
> 기준: 추출 로직 범위를 넘는 내용, v1 MVP에 불필요한 복잡성, 04.graphrag와 중복

---

## 총평

v10에서 5건이던 과도한 설계가 v11에서 **3건으로 감소**. 범위 재정의가 효과적이었으나, 일부 영역에서 여전히 추출 범위를 넘는 설계가 잔존.

---

## O1. compute_skill_overlap 함수 포함 (Medium)

**위치**: 01_extraction_pipeline.md §5.4

**문제**: v11은 "추출 로직에 집중"을 선언했으나, compute_skill_overlap은 **매칭 로직**이다. Candidate와 Vacancy의 스킬을 비교하여 overlap score를 계산하는 것은 추출이 아니라 **04.graphrag Phase 3의 MappingFeatures** 영역.

**근거**:
- v11 §6 매칭 필드 매핑 테이블에서 "매칭 함수 설계는 04.graphrag Phase 3에서 수행"이라고 명시
- 그런데 바로 앞 §5.4에 매칭 함수 코드가 있으므로 **자체 모순**

**권고**: §5.4 삭제. §6 매핑 테이블만 유지. 04.graphrag Phase 3-0 매칭 설계 문서에서 이 함수를 정의.

**만약 유지한다면**: "추출 시 정규화 품질 검증 목적의 참고 구현"으로 목적을 명확히 하고, 매칭 로직이 아님을 주석으로 강조.

---

## O2. structural_tensions 전체 스키마 (Low)

**위치**: 03_prompt_design.md §1.3

**문제**: StructuralTension enum(8개 유형)이 프롬프트 스키마에 포함되어 있으나, v11 자체에서 "v1에서 대부분 null"이라고 기술. 04.graphrag에서도 tension은 Phase 5로 이동.

**영향**:
- 프롬프트 토큰 낭비 (~200 토큰/JD × 10K = 2M 토큰 = ~$0.80 추가)
- LLM이 불필요한 필드를 채우려는 경향 → noise 생성

**권고**: v1 프롬프트에서 structural_tensions 관련 필드를 **주석 처리하거나 제거**. Phase 5에서 활성화 시 복원.

---

## O3. work_style_signals 추출 (Low)

**위치**: 03_prompt_design.md §2.3, 01_extraction_pipeline.md §3.3

**문제**: work_style_signals가 "v1 INACTIVE"로 표시되면서도 추출 대상에 포함. 매칭에서도 F4(culture_fit)가 INACTIVE.

**영향**:
- 불필요한 LLM 토큰 소비 (~100 토큰/이력서 × 500K = 50M 토큰 = ~$20)
- 사용되지 않는 데이터의 품질 검증 부담

**권고**: v1 프롬프트에서 제거. Phase 5 활성화 시 복원.

---

## O4. operating_model "LLM 진정성 체크" (Low)

**위치**: 03_prompt_design.md §1.5

**문제**: "애자일 팀"이 광고성인지 실제 운영 방식인지 LLM이 판단하도록 요구. JD 본문만으로는 **사실상 판단 불가능**.

**영향**:
- LLM에 불가능한 과제를 부여하면 confidence가 불안정해짐
- 개발 시간 낭비 (이 규칙의 효과 검증 어려움)

**권고**: "키워드가 구체적 맥락 없이 단독 사용 시 confidence를 0.3으로 제한" 정도의 단순 규칙으로 대체. LLM에 "진정성"을 판단시키지 말 것.

---

## v10 대비 개선

| v10 과도 설계 | v11 | 해소 여부 |
|-------------|-----|----------|
| Pipeline D/E 포함 (매칭/서빙) | 04.graphrag 참조로 이관 | **해소** |
| 27주 실행 계획 포함 | 04.graphrag 참조로 이관 | **해소** |
| GCP 인프라 상세 포함 | 추출 관련 리소스로 간소화 | **해소** |
| 운영/모니터링 상세 포함 | 프롬프트 관리+증분 처리만 유지 | **해소** |
| FAISS 미래 최적화 | 제거 | **해소** |
| compute_skill_overlap (신규) | 추가됨 | 미해소 |

**v10: 과도 5건 → v11: 과도 4건 (기존 5건 해소, 신규 1건 추가 + 기존 잔존 3건)**

---

## 과도 설계 심각도 요약

| ID | 항목 | 심각도 | 비용 영향 | 구현 영향 |
|----|------|--------|----------|----------|
| O1 | compute_skill_overlap | Medium | 없음 (코드만) | 범위 혼란 |
| O2 | structural_tensions 스키마 | Low | ~$0.80 | 노이즈 |
| O3 | work_style_signals | Low | ~$20 | 불필요 품질 관리 |
| O4 | operating_model 진정성 체크 | Low | 없음 | 구현 불가 규칙 |

**총 불필요 비용**: ~$21 (전체 $523의 4%). 비용적으로는 경미하나, **범위 명확성과 구현 복잡도** 면에서 정리 권고.
