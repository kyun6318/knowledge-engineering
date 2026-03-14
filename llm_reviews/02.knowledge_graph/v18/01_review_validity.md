# v18 기술적 타당성 리뷰

> 리뷰일: 2026-03-14 | 리뷰어: Claude Opus 4.6

---

## 1. 파이프라인 아키텍처 타당성

### 1.1 SIE 모델 통합 (01_extraction_pipeline §3.2)

**판정: 방향은 합리적, 구현 디테일 보완 필요**

| 항목 | 평가 |
|------|------|
| GLiNER2 주력 선정 | **적절** — Span 기반 추출로 Hallucination 없음, Confidence/Threshold 개별 설정 가능 |
| NuExtract 1.5 보조 | **적절** — 장문/혼합 언어에 대한 폴백 역할 명확 |
| 하이브리드 라우팅 기준 | **불충분** — "표준 길이"와 "장문"의 구체적 기준(토큰 수, 문자 수)이 없음 |
| SIE→LLM 핸드오프 | **미정의** — SIE 출력이 LLM 프롬프트에 주입되는 형식이 03_prompt_design.md에 없음 |

**보완 권고**:
- 하이브리드 라우팅 기준: "2,048 토큰 미만 → GLiNER2, 이상 → NuExtract 1.5" 등 구체적 임계값 정의
- SIE→LLM 핸드오프: 03_prompt_design.md에 SIE 결과가 포함된 프롬프트 템플릿 추가 (예: `## SIE 사전 추출 결과\n{sie_output_json}`)
- SIE 추출 실패(confidence < threshold) 시 처리: LLM-only 폴백 or skip

### 1.2 Pipeline E: LinkedIn 외부 데이터 (01_extraction_pipeline §Pipeline E)

**판정: 단계 분리 합리적, 동일 인물 매칭 전략 약함**

| 단계 | 평가 |
|------|------|
| E-1 (프로필 정규화) | **명확** — 2.0M 전량 처리, country_code KR 고정 활용 |
| E-2 (Chapter 보강) | **합리적** — AI 표준화 완료된 데이터 활용 |
| E-3 (Organization 교차) | **리스크 있음** — company_id 기반이나 한/영 혼재(삼성전자 vs Samsung Electronics) 해결 미상세 |

**핵심 미결 사항**:
- LinkedIn 프로필 ↔ resume-hub 이력서 동일 인물 매칭: "이름+회사명+기간"으로만 언급
- 동명이인 처리, 회사명 변형(약칭/영문), 기간 불일치 허용 범위 미정의
- Phase 5에서 매칭 정확도 검증이라고 했으나, 검증 기준(precision/recall 목표) 없음

**보완 권고**:
```
동일 인물 매칭 후보 알고리즘:
1. 이름 유사도 (한/영 혼재 고려) ≥ 0.90
2. 최소 1개 경력의 회사명 정규화 후 일치
3. 해당 경력 기간 overlap ≥ 50%
→ 3조건 AND 시 match, precision 목표 ≥ 0.90
```

### 1.3 적응형 호출 전략 (01_extraction_pipeline §3.4)

**판정: v12에서 이미 검증된 합리적 설계, 유지**

Career 1~3 → 1-pass, 4+ → N+1 pass 분기는 비용/품질 트레이드오프가 명확하고, Phase 0에서 분기점 조정 가능하다는 유연성이 있다. v18에서 변경 없이 유지된 것은 적절하다.

---

## 2. 정규화 전략 타당성

### 2.1 3-Tier 비교 전략 (06_normalization §1)

**판정: 견고함, v3 실측 데이터로 뒷받침**

| Tier | v3 실측 근거 | 적절성 |
|------|------------|--------|
| Tier 1 (CI Lookup) | code:name 1:1 완전 보장 (code-hub EDA) | **매우 적절** |
| Tier 2 (CI+synonyms+embedding) | HARD_SKILL 2,315개 기반, synonyms 소스 명시 | **적절** |
| Tier 3 (embedding only) | 전공 47,163 고유값, Levenshtein 오매칭 위험 확인 | **적절** — 임베딩 전용은 올바른 판단 |

### 2.2 v3 신규 정규화 과제 타당성

| 과제 | v3 근거 | 타당성 | 비고 |
|------|---------|--------|------|
| 구코드→신코드 학교 매핑 | U0/C0 457개, ~110만건 미매핑 | **Critical, 필수** | education_level 정확도 직접 영향 |
| 직무 코드 계층화 | 유사 코드 동시선택율 20%+ | **Medium, 합리적** | Role.category 매핑 품질 향상 |
| 캠퍼스 코드 정리 | 경상국립대 8→5 불필요 공백 3건 | **Low, 정당** | 영향 범위 작으나 비용도 낮음 |

### 2.3 정규화 과제 의존성 미명시 (지적 사항)

06_normalization.md §6에서 8개 과제를 나열하나 의존성이 불명확:

```
실제 의존성:
1. days_worked 계산 ← 독립 (즉시 가능)
2. Certificate type 매핑 ← 독립 (즉시 가능)
3. 캠퍼스 코드 정리 ← 독립 (즉시 가능)
4. 구코드→신코드 학교 매핑 ← 캠퍼스 코드 정리 완료 후 권장
5. 직무 코드 계층화 ← 독립 (code-hub만 참조)
6. 회사명 정규화 ← BRN 데이터 접근 필요
7. 스킬 정규화 ← code-hub synonyms 접근 필요
8. 전공명 정규화 ← Tier 3 임베딩 모델 확정 후
```

**보완 권고**: 의존성 그래프를 추가하여 병렬 가능 과제(1-3, 5)와 순차 필수 과제(4, 6-8)를 시각화

---

## 3. 프롬프트 설계 타당성

### 3.1 CompanyContext 프롬프트 (03_prompt_design §1)

**판정: 견고함, v25 정합**

- HiringContext 4+1 enum이 v25 01_company_context.md와 일치
- Seniority enum이 v25와 통일 (JUNIOR/MID/SENIOR/LEAD/HEAD/UNKNOWN) — v17 C1 해소 확인
- operating_model float(0.0~1.0) 타입이 v16 결정과 일치
- Few-shot 예시 2건이 BUILD_NEW, SCALE_EXISTING의 대표 케이스를 적절히 커버

### 3.2 CandidateContext 프롬프트 (03_prompt_design §2)

**판정: 견고하나 SIE 연동 템플릿 부재**

- ScopeType 5 enum, OutcomeType 5 enum, SignalLabel 14 enum이 v25 02_candidate_context.md와 일치
- 1-pass/N+1 pass 분기별 프롬프트가 명확히 분리
- **그러나**: §0 설계 원칙 6에서 "SIE 추출 결과를 LLM 프롬프트의 컨텍스트로 제공"한다고 명시했으나, §2.2 User Prompt Template에 SIE 결과 섹션이 없음

**보완 권고**: §2.2.1 1-pass 프롬프트에 선택적 SIE 섹션 추가:
```
## SIE 사전 추출 결과 (있는 경우)
{sie_extraction_json}
→ 위 SIE 결과를 참고하되, 최종 판단은 원문에 기반하세요.
```

### 3.3 SituationalSignal Taxonomy 정합성

**판정: v25와 거의 일치, 미세 차이 1건**

| 03_prompt_design.md SignalLabel | v25 02_candidate_context.md | 일치 여부 |
|--------------------------------|---------------------------|----------|
| EARLY_STAGE ~ ENTERPRISE_TRANSITION (13개) | 동일 | **일치** |
| OTHER | OTHER | **일치** |
| (없음) | MONETIZATION | **v25에만 존재** |

→ 03_prompt_design.md의 SignalLabel enum에 `MONETIZATION`이 누락됨. v25 §2.3에는 포함되어 있음.
**단, 재확인 필요**: 03_prompt_design.md §2.3의 Pydantic에는 `MONETIZATION = "MONETIZATION"`이 포함되어 있으므로, §2.6 가이드라인 테이블에만 누락된 것일 수 있음.

확인 결과: §2.3 Pydantic enum에 MONETIZATION이 **포함되어 있음**. §2.6 가이드라인 테이블에서도 "MONETIZATION | 수익화, BM, 매출 모델"로 **포함되어 있음**. → **정합 확인**.

---

## 4. PII 및 검증 체계 타당성

### 4.1 PII 처리 (04_pii_and_validation §1)

**판정: 견고함, Critical 이슈 명시됨**

- PII 처리 책임 경계 미확정 이슈가 문서 상단에 CRITICAL로 명시 — 적절한 경고
- GCS CMEK + 대안 2개(BigQuery DLP, CloudSQL) 제시는 v12에서 해소된 사항 유지
- 전화번호 정규식 8종 변형 커버, \b 추가로 false positive 방지 (v15)

### 4.2 검증 체크포인트 (04_pii_and_validation §2)

**판정: CP1-CP6 체계적, 실구현 가능**

각 체크포인트마다 Python 의사코드 + 실패 시 대응이 명확. 특히:
- CP3의 json-repair → Pydantic 검증 2단계가 LLM 출력 불안정성에 대한 현실적 대응
- CP5의 95% 적재율 임계값이 실운영에서 합리적인 수준
- CP6의 영벡터/NaN 체크가 임베딩 품질 보장에 필요한 최소 검증

---

## 5. 비용 추정 타당성

### 5.1 LLM 비용

| 파이프라인 | v18 비용 | v12 비용 | 변화 | 근거 |
|-----------|---------|---------|------|------|
| CompanyContext (A) | $2.0 (Batch) | $2.0 | = | structural_tensions 제외 유지 |
| CandidateContext DB (B) | $496 (Batch) | $496 | = | 적응형 호출 유지 |
| CandidateContext 파일 (B') | ~$260 | ~$260 | = | 변경 없음 |
| **총 LLM** | **~$758** | **~$758** | = | |

### 5.2 미반영 비용 (지적 사항)

| 항목 | 예상 비용 | 비고 |
|------|----------|------|
| **GLiNER2 GPU** | 미추정 | Cloud Run GPU 또는 GCE, 8M 이력서 처리 시 GPU 시간 필요 |
| **NuExtract 1.5 GPU** | 미추정 | 3.51B 파라미터, ~15GB VRAM, 장문 이력서 대상 |
| **LinkedIn 처리** | 미추정 | 2.0M 프로필 + 2.7M 경력, Phase 5 비용 별도 |

**보완 권고**: 02_model_and_infrastructure.md에 SIE 모델 GPU 비용 섹션 추가. 최소한 "Phase 0 PoC 시 GPU 비용 실측 후 반영" 명시 필요.
