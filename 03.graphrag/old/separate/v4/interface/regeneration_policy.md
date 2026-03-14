> 작성일: 2026-03-12
> 01_company_context.md §2.4 + 02_candidate_context.md §2.9에서 이동.
> 재생성/갱신 정책을 운영 영역으로 분리.

---

## 1. CompanyContext 재생성 조건

CompanyContext가 한 번 생성된 후, 다음 이벤트가 발생하면 재생성한다.

| 트리거 | 재생성 범위 | 감지 방법 |
| --- | --- | --- |
| 공고 수정 (JD 내용 변경) | vacancy, role_expectations 재생성 | job-hub `updated_at` 변경 감지 |
| NICE 데이터 갱신 | company_profile, stage_estimate 재생성 | NICE 데이터 갱신 주기(주간) 배치 |
| 크롤링 데이터 갱신 | domain_positioning, structural_tensions 재생성 | 크롤링 완료 이벤트 |
| 공고 마감 | CompanyContext 아카이빙 (활성에서 제외) | job-hub 공고 상태 변경 감지 |

**재생성 우선순위**: 공고 수정 > 공고 마감 > NICE 갱신 > 크롤링 갱신

---

## 2. CandidateContext 재생성 조건

CandidateContext가 한 번 생성된 후, 다음 이벤트가 발생하면 재생성한다.

| 트리거 | 재생성 범위 | 감지 방법 |
| --- | --- | --- |
| 이력서 갱신 (`resume.userUpdatedAt` 변경) | 전체 CandidateContext 재생성 | 일간 배치에서 `userUpdatedAt > last_generated_at` 검사 |
| 신규 Career 추가 | 해당 Experience + RoleEvolution 재생성 | Career 테이블 변경 감지 |
| 스킬 데이터 변경 | 해당 Experience의 tech_stack 갱신 | Skill 테이블 변경 감지 |
| NICE 데이터 갱신 | PastCompanyContext 재생성 | NICE 데이터 갱신 주기(주간)에 맞춰 배치 |
| code-hub 코드 변경 | 영향받는 모든 정규화 결과 재계산 | code-hub 배포 이벤트 |

**재생성 우선순위**: 이력서 갱신 > 신규 Career > NICE 갱신 > 스킬/코드 변경
