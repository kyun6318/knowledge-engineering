# v18 Action Items

> 리뷰일: 2026-03-14 | 리뷰어: Claude Opus 4.6

---

## 분류 기준

| 분류 | 설명 |
|------|------|
| **Must** | v19 이전에 반드시 해소. 미해소 시 구현 차단 또는 심각한 품질 저하 |
| **Should** | v19에서 해소 권장. 미해소 시 구현 가능하나 품질/효율 저하 |
| **Could** | 개선하면 좋으나 당장 영향 적음. v20+ 또는 Phase별 점진 해소 |

---

## Must (3건)

### M1. SIE 모델 인프라 및 운영 설계 추가

**위치**: 02_model_and_infrastructure.md
**이유**: SIE(GLiNER2/NuExtract 1.5)가 01_extraction_pipeline에서 파이프라인 핵심 구성요소로 통합되었으나, 인프라 요건이 전혀 없음. GPU 비용, 서빙 방식, 처리량이 결정되어야 전체 비용 추정과 Phase 0 PoC 범위 확정 가능.

**추가 항목**:
```
§5 SIE 모델 인프라
- 서빙 방식: Cloud Run GPU / GCE / Vertex AI Endpoint
- GLiNER2 리소스: CPU/GPU 요구, 처리 시간/건
- NuExtract 1.5 리소스: ~15GB VRAM, 처리 시간/건
- 비용 추정: 처리 대상 건수별 GPU 시간
- Phase 0 PoC: 한국어 이력서 50건 추출 정확도 검증 추가
```

### M2. SIE→LLM 핸드오프 프롬프트 템플릿 정의

**위치**: 03_prompt_design.md §2.2
**이유**: §0 원칙 6에서 "SIE 결과를 LLM 컨텍스트로 제공"이라고 선언했으나, 실제 프롬프트에 SIE 섹션이 없음. 프롬프트 설계 문서에 SIE 연동 템플릿이 없으면 구현 시 임의 설계가 필요.

**추가 항목**:
```
§2.2에 선택적 SIE 섹션 추가:

## SIE 사전 추출 결과 (선택, SIE 적용 시에만 포함)
{sie_extraction_json}

→ SIE 결과의 company, title, tech_stack은 참고용입니다.
→ scope_type, outcomes, situational_signals는 SIE에서 추출하지 않으므로 원문 기반으로 판단하세요.

SIE 미적용 시: 이 섹션을 제거하고 기존 프롬프트 그대로 사용
```

### M3. Phase 0 PoC 범위에 SIE 검증 추가

**위치**: 05_extraction_operations.md §4.1, 01_extraction_pipeline.md §3.2
**이유**: SIE 모델의 한국어 성능이 미검증 상태. Phase 0 PoC에 SIE 검증이 포함되지 않으면, Phase 1에서 SIE 통합 실패 시 전체 파이프라인 재설계 필요.

**추가 항목**:
- 가정 A28: "GLiNER2의 한국어 이력서 Span 추출 정확도 ≥ 70%" → Phase 0 검증
- PoC 범위: 50건 이력서에서 GLiNER2 추출 → 수동 검증 → precision/recall 측정
- 실패 기준: precision < 60% 시 SIE 제외, LLM-only 파이프라인으로 진행

---

## Should (4건)

### S1. 정규화 과제 의존성 그래프 추가

**위치**: 06_normalization.md §6
**이유**: 8개 과제가 평면적으로 나열되어 있어 구현 시 우선순위/병렬화 판단이 어려움.

**추가 항목**:
```
의존성 그래프:
[독립, 즉시 가능]     [순차 의존]
  days_worked ──────────→ Chapter 생성
  cert_type_mapping ────→ Certificate 매칭
  campus_code_clean ────→ 구코드→신코드 매핑 → education_level 보정
  직무코드_계층화 ─────→ Role.category 정의

[병렬, DB 접근 필요]
  회사명_정규화 ────────→ Organization 생성 → LinkedIn 교차(E-3)
  스킬_정규화 ─────────→ Skill 노드 생성

[임베딩 모델 확정 후]
  전공명_정규화 ────────→ Tier 3 임베딩 비교
```

### S2. LinkedIn 동일 인물 매칭 설계 구체화

**위치**: 05_extraction_operations.md §5
**이유**: "이름+회사명+기간 조합으로 추정"만으로는 Phase 5 착수 시 설계 부족.

**추가 항목**:
- 매칭 알고리즘 초안 (이름 유사도, 회사명 정규화 후 일치, 기간 overlap)
- precision/recall 목표 (예: precision ≥ 0.90, recall ≥ 0.60)
- 오매칭 방지 규칙 (동명이인, 대기업 동명 부서)
- 매칭 결과 활용: source_type='linkedin' 태깅, confidence 보정 규칙

### S3. job-hub 샘플링 실측 검증 추가

**위치**: 07_data_quality.md §2
**이유**: "예상" fill rate가 5개 이상 필드에 사용됨. 1K 샘플링으로 실측 가능.

**추가 항목**:
```
[Phase 0 병렬 과제] job-hub 1K 샘플링
- 대상: job 테이블 1,000건 랜덤 샘플
- 측정: industry_codes, job_classification_codes, descriptions,
        designation_codes, skill 테이블 fill rate
- 기준: 예상치 대비 ±10% 이내면 현행 유지, ±10% 초과 시 문서 보정
```

### S4. 구코드 미매핑의 education_level 영향 명시

**위치**: 07_data_quality.md §1
**이유**: education_level fill rate 95.6%가 구코드 미매핑 ~110만건을 고려하지 않은 수치. 매핑 전 실효 fill rate는 ~82%.

**보정**:
- education_level fill rate: 95.6% (구코드 매핑 완료 시) / **~82% (매핑 전)**
- Phase 1-2에서는 82% 기준으로 설계, 구코드 매핑 완료 후 95.6%로 복원

---

## Could (3건)

### C1. SIE 출력 Pydantic 스키마 정식 정의

**위치**: 03_prompt_design.md 또는 별도 문서
**이유**: v3.md §3.5의 예시 JSON만 존재. 구현 시 정식 스키마 필요.

### C2. Gemini 2.0 Flash 대안 검토 구체화

**위치**: 02_model_and_infrastructure.md §1.1
**이유**: "최저 비용 시나리오"로 언급만 되어 있으나, 비용이 Haiku 대비 1/8 수준. Phase 0에서 Haiku와 병렬 비교 가치 있음.

### C3. 증분 처리와 LinkedIn 동기화 통합 설계

**위치**: 05_extraction_operations.md
**이유**: Phase 5에서 필요하므로 급하지 않으나, Phase 1-4 설계 시 확장점을 미리 고려하면 후속 작업 용이.

---

## 요약

| 분류 | 건수 | 핵심 |
|------|------|------|
| **Must** | 3건 | SIE 인프라 설계, SIE→LLM 프롬프트, Phase 0에 SIE 검증 추가 |
| **Should** | 4건 | 정규화 의존성, LinkedIn 매칭, job-hub 실측, 구코드 영향 |
| **Could** | 3건 | SIE 스키마, Gemini Flash 비교, 증분+LinkedIn 통합 |
