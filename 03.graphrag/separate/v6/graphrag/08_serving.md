> 작성일: 2026-03-12
> 01.ontology/results/schema/v23/03_mapping_features.md §4.2, §5에서 이동.
> BigQuery 서빙 스키마/SQL, freshness_weight 서빙 로직을 GraphRAG 구현 영역으로 분리.

---

## 1. freshness_weight 적용 규칙

Person 노드의 `freshness_weight`(0.3~1.0, `00_data_source_mapping §3.5` 정의)는 **overall_match_score 산출 후, 최종 랭킹 점수를 계산하는 시점에 적용**한다.

```python
def compute_ranking_score(overall_match_score, candidate_ctx):
    """
    freshness_weight 적용 지점.

    overall_match_score는 피처의 순수한 적합도 평가이므로 freshness에 의해 왜곡하지 않는다.
    대신 최종 랭킹에서 신선도를 반영하여, 오래된 이력서의 순위를 하향 조정한다.

    적용 방식: ranking_score = overall_match_score × freshness_weight
    - freshness_weight = 1.0 (90일 이내): 순위 영향 없음
    - freshness_weight = 0.3 (5년+ 미갱신): 순위 70% 감소

    별도 저장:
    - BigQuery mapping_features 테이블에 overall_match_score(원본)와 ranking_score(보정) 모두 저장
    - 사용자(DS/MLE)가 용도에 따라 원본 또는 보정값 선택 가능
    """
    fw = candidate_ctx.freshness_weight  # 0.3~1.0
    ranking_score = overall_match_score * fw
    return {
        "overall_match_score": overall_match_score,  # 순수 적합도 (freshness 미적용)
        "ranking_score": ranking_score,               # 랭킹용 (freshness 적용)
        "freshness_weight": fw
    }
```

> **[v5] freshness_weight 모드 명시**: v1은 step 모드(00_data_source_mapping.md §3.5의 `use_smooth=False`)를 사용한다. smooth 모드로 전환 시 전체 Person 노드의 freshness_weight를 일괄 재계산해야 한다. Person 노드에 `freshness_mode` 속성을 별도로 추가하지 않고, 파이프라인의 설정값으로 관리한다. 모드 전환은 증분 배치가 아닌 **전량 재계산 배치**로 수행한다.

**설계 근거**:
- overall_match_score에 freshness를 곱하면 피처 품질 분석이 오염되므로 분리
- 랭킹 시점에서 곱셈 적용하면 "적합하지만 오래된 이력서"와 "덜 적합하지만 최신 이력서"를 비교할 수 있음
- `freshness_weight < 0.5`인 후보(3년+ 미갱신)는 결과에 포함하되 후순위로 표시하는 것이 기본 정책. 완전 제외는 서비스 레이어에서 결정

---

## 2. DS/MLE 소비 인터페이스

### 2.1 서빙 형태

| 옵션 | 장점 | 단점 | v1 권장 |
| --- | --- | --- | --- |
| BigQuery 테이블 | 기존 파이프라인 통합 쉬움, SQL 조인 | 실시간 불가 | **v1 채택** |
| REST API | 실시간 조회 가능 | 구축 비용 | v2 |
| Parquet 파일 (GCS) | 가장 단순 | 접근성 낮음 | PoC용 |

### 2.2 BigQuery 테이블 스키마 (v1)

```sql
-- mapping_features 테이블
CREATE TABLE context.mapping_features (
  mapping_id STRING NOT NULL,
  company_id STRING NOT NULL,
  job_id STRING NOT NULL,
  candidate_id STRING NOT NULL,

  -- 피처 스코어 (null = INACTIVE)
  stage_match_score FLOAT64,
  stage_match_confidence FLOAT64,
  vacancy_fit_score FLOAT64,
  vacancy_fit_confidence FLOAT64,
  domain_fit_score FLOAT64,
  domain_fit_confidence FLOAT64,
  culture_fit_score FLOAT64,
  culture_fit_confidence FLOAT64,
  role_fit_score FLOAT64,
  role_fit_confidence FLOAT64,

  -- 요약
  active_feature_count INT64,
  overall_match_score FLOAT64,
  avg_confidence FLOAT64,

  -- 메타
  context_version STRING,
  generated_at TIMESTAMP,

  -- JSON 상세 (디버깅/분석용)
  features_detail JSON
);

-- company_context 테이블
CREATE TABLE context.company_context (
  company_id STRING NOT NULL,
  job_id STRING NOT NULL,
  stage_label STRING,
  stage_confidence FLOAT64,
  vacancy_hiring_context STRING,
  vacancy_seniority STRING,
  industry_code STRING,
  industry_label STRING,
  employee_count INT64,
  speed_score FLOAT64,
  autonomy_score FLOAT64,
  process_score FLOAT64,
  fill_rate FLOAT64,
  context_version STRING,
  generated_at TIMESTAMP,
  full_context JSON
);

-- candidate_context 테이블
CREATE TABLE context.candidate_context (
  candidate_id STRING NOT NULL,
  resume_id STRING NOT NULL,
  role_evolution_pattern STRING,
  total_experience_years FLOAT64,
  primary_domain STRING,
  domain_experience_count INT64,
  experience_count INT64,
  signal_labels ARRAY<STRING>,  -- 모든 경험의 situational_signal 합집합
  fill_rate FLOAT64,
  context_version STRING,
  generated_at TIMESTAMP,
  full_context JSON
);
```

### 2.3 사용 예시

```sql
-- 기본 매핑 조회: job_id별 후보 랭킹
SELECT
  mf.candidate_id,
  mf.overall_match_score,
  mf.avg_confidence,
  mf.stage_match_score,
  mf.vacancy_fit_score,
  mf.domain_fit_score,
  mf.role_fit_score,
  mf.active_feature_count
FROM context.mapping_features mf
WHERE mf.job_id = 'job_67890'
  AND mf.overall_match_score IS NOT NULL
ORDER BY mf.overall_match_score * mf.avg_confidence DESC
LIMIT 50;

-- Context on/off ablation: 기존 스킬 매칭 + Context 피처 결합
SELECT
  s.candidate_id,
  s.skill_match_score,
  mf.overall_match_score AS context_score,
  -- 결합 스코어
  s.skill_match_score * 0.5 + COALESCE(mf.overall_match_score, 0) * 0.5 AS combined_score
FROM search.skill_matching s
LEFT JOIN context.mapping_features mf
  ON s.candidate_id = mf.candidate_id
  AND s.job_id = mf.job_id
WHERE s.job_id = 'job_67890'
ORDER BY combined_score DESC;
```
