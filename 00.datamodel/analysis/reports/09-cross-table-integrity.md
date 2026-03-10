# 09. 크로스 테이블 조인 무결성 분석

> 분석일: 2026-03-03 | 데이터베이스: `import_resume_hub_tmp`
> 목적: 이력서 데이터 14개 테이블 간 FK 무결성 검증 — 에이전트 MCP 조인 시 데이터 손실 없이 사용 가능한지 확인

---

## 1. 테이블 기본 현황

| 테이블 | 레코드 수 | PK | 상위 FK |
|---|---|---|---|
| `user_profile.profile` | 7,780,115 | `id` | `site_user_mapping_id` |
| `resume.resume` | 8,018,110 | `id` | `site_user_mapping_id` |
| `resume.workcondition` | 8,018,110 | `resume_id` | `resume_id → resume.id` |
| `resume.career` | 18,709,830 | `id` | `resume_id → resume.id` |
| `resume.career_description` | 1,351,836 | `id` | `resume_id → resume.id` |
| `resume.self_introduction` | 7,960,158 | `id` | `resume_id → resume.id` |
| `resume.award` | 1,514,464 | `id` | `resume_id → resume.id` |
| `resume.certificate` | 13,579,693 | `id` | `resume_id → resume.id` |
| `resume.experience` | 6,632,242 | `id` | `resume_id → resume.id` |
| `resume.education` | 11,201,436 | `id` | `resume_id → resume.id` |
| `resume.major` | 7,147,005 | `id` | `resume_id`, `education_id → education.id` |
| `resume.language` | 651,561 | `id` | `resume_id → resume.id` |
| `resume.skill` | 20,816,734 | `id` | `resume_id → resume.id` |

> [참고] 일부 테이블 행수(skill, certificate, award, self_introduction, experience, language)는 쿼리 시점 차이로 README 기준값과 ±0.1% 내외 차이가 있을 수 있다. README의 수치를 정본(authoritative)으로 참조할 것.

---

## 2. FK 무결성 매트릭스 (고아 레코드 수)

| 관계 | 방향 | 고아 레코드 수 | 무결성 |
|---|---|---|---|
| `profile` ↔ `resume` (site_user_mapping_id) | 양방향 | **0** | 완전 |
| `resume` ↔ `workcondition` | 양방향 | **0** | 완전 |
| `career` → `resume` | 부모 없는 career | **0** | 완전 |
| `career_description` → `resume` | 부모 없는 career_description | **0** | 완전 |
| `self_introduction` → `resume` | 부모 없는 self_introduction | **0** | 완전 |
| `award` → `resume` | 부모 없는 award | **0** | 완전 |
| `certificate` → `resume` | 부모 없는 certificate | **0** | 완전 |
| `experience` → `resume` | 부모 없는 experience | **0** | 완전 |
| `education` → `resume` | 부모 없는 education | **0** | 완전 |
| `major` → `resume` (resume_id) | 부모 없는 major | **0** | 완전 |
| `major` → `education` (education_id) | 부모 없는 major | **0** | 완전 |
| `language` → `resume` | 부모 없는 language | **0** | 완전 |
| `skill` → `resume` | 부모 없는 skill | **0** | 완전 |

**모든 FK 관계에서 고아 레코드 0건. 데이터 무결성 완전.**

---

## 3. 주요 관계 상세

### 3-1. Profile ↔ Resume 연결

| 지표 | 값 |
|---|---|
| 총 이력서 수 | 8,018,110 |
| 총 프로필 수 | 7,780,115 |
| 이력서 보유 unique 유저 | 7,780,115 |
| 유저당 평균 이력서 수 | 1.0306 |
| 프로필 없는 이력서 | **0** |
| 이력서 없는 프로필 | **0** |

[AI 추정] 이력서 수(8.02M)가 프로필 수(7.78M)보다 237,995 많은 이유는 일부 유저가 복수 이력서를 보유하기 때문 (avg 1.0306).

### 3-2. Resume ↔ Workcondition 1:1 무결성

| 지표 | 값 |
|---|---|
| resume 수 | 8,018,110 |
| workcondition 수 | 8,018,110 |
| resume_id 중복 in workcondition | **0** |

완전한 1:1 관계. 모든 이력서에 희망근무조건 레코드가 정확히 하나씩 존재.

### 3-3. 전체 자식 테이블 커버리지

| 테이블 | 데이터 보유 이력서 | 커버리지 | 이력서당 평균 행 수 |
|---|---|---|---|
| `education` | 7,665,296 | **95.60%** | 1.46 |
| `major` | 5,813,623 | **72.51%** | 1.23 |
| `career` | 5,523,101 | **68.88%** | 3.39 |
| `self_introduction` | 5,137,844 | **64.08%** | 1.55 |
| `certificate` | 4,325,794 | **53.95%** | 3.14 |
| `skill` | 3,074,732 | **38.35%** | 6.77 |
| `experience` | 2,240,622 | **27.94%** | 2.96 |
| `career_description` | 1,351,836 | **16.86%** | 1.00 |
| `award` | 707,646 | **8.83%** | 2.14 |
| `language` | 509,027 | **6.35%** | 1.28 |

### 3-4. 유저당 이력서 분포 (multi-resume)

| 이력서 수 | 유저 수 | 비율 |
|---|---|---|
| 1개 | 7,654,420 | **98.38%** |
| 2개 | 81,242 | 1.04% |
| 3개 이상 | 44,453 | 0.57% |

### 3-5. main_flag 분포

| main_flag | 이력서 수 | 비율 |
|---|---|---|
| 1 (대표) | 7,715,508 | **96.23%** |
| 0 (비대표) | 302,602 | 3.77% |

[AI 추정] `main_flag=0`인 302,602건은 multi-resume 유저의 부이력서. 대표이력서 필터링 시 7,715,508건이 기준 데이터셋.

---

## 4. MCP 에이전트 JOIN 전략

### 안전한 INNER JOIN

```sql
SELECT
    r.id AS resume_id,
    r.title,
    r.career_type,
    p.gender, p.age, p.job_search_status,
    wc.employment_types,
    wc.job_classification_codes
FROM `resume.resume` r
JOIN `user_profile.profile` p ON r.site_user_mapping_id = p.site_user_mapping_id
JOIN `resume.workcondition` wc ON r.id = wc.resume_id
WHERE r.main_flag = 1  -- 대표이력서만
```

INNER JOIN 가능: `resume` ↔ `profile`, `resume` ↔ `workcondition`, `education` → `major`

### LEFT JOIN 필수 관계 (선택적 데이터)

| 관계 | 커버리지 |
|---|---|
| `resume` → `career` | 68.88% |
| `resume` → `self_introduction` | 64.08% |
| `resume` → `certificate` | 53.95% |
| `resume` → `skill` | 38.35% |
| `resume` → `experience` | 27.94% |
| `resume` → `career_description` | 16.86% |
| `resume` → `award` | 8.83% |
| `resume` → `language` | 6.35% |

### JOIN 시 주의사항

| 패턴 | 주의사항 |
|---|---|
| multi-resume 유저 | `main_flag=1` 필터 없으면 1.62% 유저가 중복 집계됨 |
| `career_description` 활용 | `career_id` FK 없음 — career 항목별 매핑 불가, resume 단위로만 귀속 |
| `skill` 분포 | 20개에서 분포 피크 — cap 존재 가능성, 스킬 다양성 분석 시 편향 고려 |
| `education` 없는 이력서 | 4.40% (352,814건) — 학력 기반 필터링 시 누락 처리 필요 |

---

## 5. 한계 및 후속 작업

1. **스냅샷 데이터 및 레코드 수 미세 차이**: `import_resume_hub_tmp`는 특정 시점 임포트 데이터이다. 본 보고서의 레코드 수(예: skill 20,816,734, certificate 13,579,693)와 README/타 보고서 수치(각각 20,810,452, 13,573,606)에 0.03~0.15% 차이가 존재하며, 이는 쿼리 실행 시점의 데이터 파이프라인 상태 차이로 추정된다. 기준 수치는 README를 따를 것
2. **career_description ↔ career 연결 불가**: `career_id` FK 없어 특정 경력 항목과의 직접 매핑 불가 → 스키마 개선 검토
3. **skill 20개 cap 검증**: 데이터 수집 시 상한선 존재 여부 프로덕션 DB에서 확인
4. **JOIN 키 명세 정확화**: 에이전트 프롬프트에 `site_user_mapping_id` (not `site_user_ref`) 명시
5. **소프트 삭제 레코드**: `deleted_at` 컬럼 있는 테이블에서 삭제 레코드 포함 여부 검증 후 필터 추가

---

*데이터: ClickHouse `import_resume_hub_tmp` | 분석: Scientist Agent (claude-sonnet-4-6) | [AI 추정] 표기 항목은 AI 해석*
