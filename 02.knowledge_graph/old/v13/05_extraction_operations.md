> 작성일: 2026-03-11
추출 로직 고유 내용만 추출하여 통합.
실행 계획, GCP 인프라, 서빙 API, Runbook/Alarm 등은 04.graphrag 참조.
> 

---

## 1. 증분 처리 전략

### 1.1 변경 감지 (DB updated_at 기반)

```python
def detect_changes(last_run_timestamp):
    """DB updated_at 필드 기반 변경분 감지"""
    new_resumes = query("""
        SELECT * FROM resume_hub.career
        WHERE created_at > :last_run
    """, last_run=last_run_timestamp)

    updated_resumes = query("""
        SELECT * FROM resume_hub.career
        WHERE updated_at > :last_run AND created_at <= :last_run
    """, last_run=last_run_timestamp)

    deleted_resumes = query("""
        SELECT * FROM resume_hub.career
        WHERE deleted_at > :last_run
    """, last_run=last_run_timestamp)

    return new_resumes, updated_resumes, deleted_resumes
```

### 1.2 처리 유형별 전략

| 유형 | 전략 | 비고 |
| --- | --- | --- |
| **신규** | 표준 파이프라인 (B->C) | 전체 처리 |
| **수정 (구조화 필드)** | DB 필드 diff -> 부분 업데이트 | LLM 불필요 |
| **수정 (텍스트 필드)** | DETACH DELETE old Chapters -> LLM 재추출 | 전체 재처리 |
| **삭제** | soft-delete (is_active=false, deleted_at 기록) | 노드 유지, 관계 비활성 |

### 1.3 구조화 vs 텍스트 필드 분류

| 분류 | 필드 | 수정 시 처리 |
| --- | --- | --- |
| **구조화** | companyName, position, startDate, endDate, positionGradeCode | DB diff -> 노드 속성 직접 업데이트 |
| **구조화** | Skill (코드 기반), Education | Tier 1/2 재비교 -> 관계 업데이트 |
| **텍스트** | workDetails, CareerDescription | Chapter DETACH DELETE -> LLM 재추출 |
| **텍스트** | SelfIntroduction | 전체 Career 재추출 (role_evolution 영향) |

### 1.4 DETACH DELETE 시 공유 노드 보호 (v11 신규)

```
// 문제: Chapter 삭제 시 공유 Skill/Organization 노드가 고아가 될 수 있음

// 안전한 Chapter 삭제 절차
// Step 1: Chapter -> 공유 노드 관계만 제거 (공유 노드는 유지)
MATCH (c:Chapter {chapter_id: $chapter_id})-[r]->(shared)
WHERE shared:Skill OR shared:Organization OR shared:Role OR shared:Industry
DELETE r

// Step 2: Chapter -> 비공유 노드 관계 + 노드 삭제
MATCH (c:Chapter {chapter_id: $chapter_id})-[r]->(owned)
WHERE owned:Outcome OR owned:SituationalSignal
DELETE r, owned

// Step 3: Person -> Chapter 관계 + Chapter 삭제
MATCH (p:Person)-[r:HAS_CHAPTER]->(c:Chapter {chapter_id: $chapter_id})
DELETE r, c

// Step 4: NEXT_CHAPTER 관계 재연결
MATCH (prev:Chapter)-[:NEXT_CHAPTER]->(deleted)
WHERE deleted.chapter_id = $chapter_id
MATCH (deleted)-[:NEXT_CHAPTER]->(next:Chapter)
MERGE (prev)-[:NEXT_CHAPTER]->(next)
```

**공유 노드 분류**:
| 노드 | 공유 여부 | 삭제 시 처리 |
|——|———-|————-|
| Skill | **공유** (여러 Chapter에서 사용) | 관계만 제거, 노드 유지 |
| Organization | **공유** (여러 Chapter/Vacancy에서 참조) | 관계만 제거, 노드 유지 |
| Role | **공유** | 관계만 제거, 노드 유지 |
| Industry | **공유** | 관계만 제거, 노드 유지 |
| Outcome | **비공유** (특정 Chapter에 귀속) | 관계 + 노드 삭제 |
| SituationalSignal | **비공유** (특정 Chapter에 귀속) | 관계 + 노드 삭제 |

### 1.5 소프트 삭제 설계

```
// 소프트 삭제: 노드 유지, 쿼리에서 제외
MATCH (p:Person {person_id: $person_id})
SET p.is_active = false,
    p.deleted_at = datetime()

// 관계 비활성화 (관계 속성 사용)
MATCH (p:Person {person_id: $person_id})-[r:HAS_CHAPTER]->(c:Chapter)
SET r.is_active = false,
    c.is_active = false

// 활성 데이터만 조회 (쿼리 패턴)
MATCH (p:Person {is_active: true})-[:HAS_CHAPTER]->(c:Chapter {is_active: true})
```

**주의**: 모든 쿼리에 `is_active: true` 필터 필수. 인덱스에 is_active 포함 권고.

### 1.6 일일 처리량 추정

- 일일 신규 이력서: ~1,000건 (가정)
- 일일 LLM 비용: ~$1.58 (Batch: ~$0.79)
- 일일 처리 시간: <2시간

---

## 2. 테스트 전략

> v10 03_execution_plan.md §11에서 이동 (추출 로직 고유 내용)
> 

### 2.1 추출 파이프라인 테스트

| 테스트 유형 | 대상 | 기준 |
| --- | --- | --- |
| 단위 | DB 커넥터, 3-Tier 모듈, Pydantic 스키마 | 커버리지 80%+ |
| 단위 | PII 마스킹 모듈 | 전화번호/주민번호/이메일 탐지율 100% |
| 통합 | 단일 이력서/JD E2E (B->C 전 파이프라인) | 전 단계 통과, 검증 체크포인트 all pass |
| 멱등성 | 2× 적재 시 노드/엣지 수 불변 | 완벽 멱등 |
| 배치 | 1K 청크 처리 | <5% 오류, <2시간 |
| 스케일 | 600K 전체 처리 | <3% 오류, <30일 |

### 2.2 추출 품질 테스트

| 테스트 유형 | 대상 | 기준 |
| --- | --- | --- |
| 품질 (Phase 0) | 20건 LLM PoC | scope_type >70%, outcomes F1 >50% |
| 품질 (Phase 1) | 50건 Gold Set | scope_type >70%, signal F1 >50% |
| 회귀 | 프롬프트 변경 시 50건 | <5% 품질 차이 |
| 통계 샘플링 (Phase 2) | 384건 | 95% CI, ±5% 오차 |

### 2.3 Gold Set 관리

| 항목 | Phase 0 | Phase 1 | Phase 4 |
| --- | --- | --- | --- |
| 규모 | 50건 | 50건 (동일) | 200건 |
| 용도 | 모델 선정, 임계값 캘리브레이션 | 파이프라인 검증, 회귀 테스트 | 최종 품질 검증 |
| 작성 | 도메인 전문가 수동 | 유지 | 확장 |
| 저장 | GCS kg-data/gold/ | 동일 | 동일 |

---

## 3. Organization ER 설계 보강

> v10 리뷰에서 “BRN 획득 경로, 자회사/개명 사전 소스 불명확” 지적 해소.
전체 Organization ER 알고리즘 설계는 04.graphrag Phase 3 참조.
여기서는 추출 파이프라인에서 필요한 입력 데이터 준비 사항만 정의.
> 

### 3.1 BRN 획득 경로

| 소스 | BRN 필드 | 가용률 | 비고 |
| --- | --- | --- | --- |
| resume-hub.Career | bizRegistrationNumber | **62%** (A19: null 40%) | 직접 사용 |
| resume-hub.Career | companyName | 100% | BRN null 시 NICE 역매칭 필요 |
| NICE DB | 기업명 -> BRN | - | companyName fuzzy 매칭 (~60% 정확도) |

**BRN null 케이스 처리**:

```
BRN 존재 (60%) -> NICE 직접 매칭 (100% 정확도)
BRN 부재 (40%) -> companyName -> NICE fuzzy 매칭 (~60% 정확도)
-> 매칭 실패 -> org_id = hash(companyName_normalized) (미확인 기업)
```

### 3.2 자회사/개명 사전

| 소스 | 예상 규모 | 구축 방법 | 시기 |
| --- | --- | --- | --- |
| NICE 관계사 정보 | ~500 그룹 | DB 매핑 | Phase 0 |
| 수동 구축 (한국 대기업) | ~100 그룹 (삼성, SK, LG 등) | 수동 작성 | Phase 2 |
| LLM 판정 (모호 케이스) | ~2,000 건 | LLM 2차 매칭 | Phase 3 |

**한국어 특수 케이스**:
| 케이스 | 규칙 |
|——–|——|
| “삼성” = “SAMSUNG” = “Samsung” | 이름 정규화 (한/영 통일) |
| “토스” = “비바리퍼블리카” | 자회사/개명 사전 |
| “카카오” ≠ “카카오뱅크” | 별개 법인 (BRN 다름) |
| “네이버” = “NHN” (구) | 개명 사전 |

### 3.3 추출 시 Organization 데이터 준비

Pipeline B/B’에서 추출 시, 매칭에 필요한 Organization 정보를 확보:

| 필드 | 추출 단계 | 방법 |
| --- | --- | --- |
| companyName (원본) | DB 커넥터 | 직접 |
| companyName (정규화) | kg-preprocess | 한/영 통일, 공백 제거, (주) 제거 |
| BRN | DB 커넥터 | 직접 (null 허용) |
| stage_estimate | NICE Lookup | Rule 기반 |
| industry_code | NICE Lookup + code-hub | Tier 1 매칭 |
| employee_count | NICE Lookup | 직접 |

---

## 4. 가정 및 리스크 (추출 로직 고유)

> GCP 인프라, GraphRAG 실험, 크롤링 리스크는 04.graphrag 참조.
> 

### 4.1 추출 고유 가정

| ID | 가정 | 값 | 검증 시점 |
| --- | --- | --- | --- |
| A2 | DB 이력서 수 | 500K | Pre-Phase 0 |
| A2’ | 파일 이력서 수 (DB 미존재) | ~100K | Phase 2 |
| A4 | 이력서당 Career 수 | 평균 3 | Phase 0 DB 프로파일 |
| A6 | LLM 토큰 (Company / Candidate) | 2,000 / 1,700 | Phase 0 PoC |
| A8 | Haiku ≈ 85% Sonnet 품질 | 85% | Phase 0 PoC |
| A19 | Career.BRN null 비율 | 40% | Pre-Phase 0 |
| A20 | Career.workDetails null 비율 | 20% | Pre-Phase 0 |
| A22 | Skill.code null + 비표준 | 10% null + 30-50% 비표준 | Pre-Phase 0 |
| A27 | text-embedding-005 > embedding-002 (한국어) | >동등 | Phase 0 |

### 4.2 추출 고유 리스크

### Critical

| ID | 리스크 | 영향 | 완화 |
| --- | --- | --- | --- |
| R1 | PII 데이터 처리 | 전체 아키텍처 | 04_pii_and_validation.md 전략 적용 |
| R2 | LLM 추출 품질 | 시스템 실현 가능성 | 03_prompt_design.md 프롬프트 + Phase 0 PoC |

### High

| ID | 리스크 | 영향 | 완화 |
| --- | --- | --- | --- |
| R2.4 | NICE 매칭률 미달 | Organization 품질 저하 | BRN 84% 예상, fuzzy 폴백 |
| R2.18 | DB 접근 불가 | 전체 프로젝트 차단 | 파일 폴백 (+5-6주) |

### Medium

| ID | 리스크 | 영향 | 완화 |
| --- | --- | --- | --- |
| R2.10 | 3-Tier 임계값 캘리브레이션 | 정규화 품질 | Phase 0 Gold Set 50건 |
| R5.1 | HWP 파서 품질 | 10-20% 파싱 실패 | Gemini Multimodal 폴백 |
| R5.2 | 파일<->DB 교차 중복 | 중복 노드 | 이름+전화번호 해시 + 수동 검증 |

### Low

| ID | 리스크 | 영향 | 완화 |
| --- | --- | --- | --- |
| R2.15 | 이력서 중복 | 불필요 노드 | SiteUserMapping + SimHash 이중 전략 |
| R2.22 | JSONB 스키마 불일치 | 파싱 실패 | Phase 0 샘플링 + 방어적 파싱 |