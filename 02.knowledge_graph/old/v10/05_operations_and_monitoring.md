# 운영 및 모니터링 v10

> 작성일: 2026-03-11 | 기준: 온톨로지 v19, GCP ML Pipeline, GraphRAG Core v2
>
> v10 신규 문서: GraphRAG v2 운영 체계를 KG 추출 파이프라인에 통합

---

## 1. 단계적 모니터링 전략

### 1.1 Phase 0-2: 최소 모니터링

| 항목 | 구현 | 비용 |
|------|------|------|
| BigQuery 3개 쿼리 | 배치 성공률, 오류 수, 처리 건수 | $0 |
| Slack 알림 (수동) | 배치 완료/실패 시 수동 전송 | $0 |
| 기본 알람 3개 | Neo4j 다운, Batch 실패, dead-letter 누적 | $0 |

### 1.2 Phase 4: 전체 모니터링

| 항목 | 구현 | 비용 |
|------|------|------|
| Runbook 5 | 장애 대응 절차서 | $0 |
| Alarm 10 | Critical/Warning/Info 3등급 | ~$10/월 |
| Slack Webhook | 자동 알림 연동 | $0 |
| BigQuery 대시보드 | quality_metrics 시각화 | ~$5/월 |
| Cloud Logging | 파이프라인 실행 로그 | ~$5/월 |

---

## 2. 증분 처리 전략

### 2.1 변경 감지 (DB updated_at 기반)

```python
# 증분 처리 흐름
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

### 2.2 처리 유형별 전략

| 유형 | 전략 | 비고 |
|------|------|------|
| 신규 | 표준 파이프라인 (B→C→D) | 전체 처리 |
| 수정 (구조화 필드) | DB 필드 diff → 부분 업데이트 | LLM 불필요 |
| 수정 (텍스트 필드) | DETACH DELETE old Chapters → LLM 재추출 | 전체 재처리 |
| 삭제 | soft-delete (Graph에서 비활성) | 노드 유지, 관계 제거 |

### 2.3 일일 처리량 추정

- 일일 신규 이력서: ~1,000건 (가정)
- 일일 LLM 비용: ~$1.58 (Batch: ~$0.79)
- 일일 처리 시간: <2시간

---

## 3. 크롤링 운영

### 3.1 월간 크롤링 사이클

```
매월 1일 (0 0 1 * *)
→ crawl_company_targets에서 대상 1,000 기업 조회
→ T3 홈페이지 크롤링 (Playwright + Cloud Run)
→ T4 뉴스 수집 (Naver News API + TheVC)
→ Gemini Flash 필드 추출
→ CompanyContext 보강 적재
→ 결과 BigQuery 기록
```

### 3.2 크롤링 KPI (v19 06_crawling_strategy.md)

| KPI | 목표 |
|-----|------|
| 크롤링 성공률 | ≥80% |
| 뉴스 커버리지 | ≥70% |
| product_description 활성화 | ≥60% |
| 월간 비용 | ~$107 |

---

## 4. Neo4j 백업 및 롤백

### 4.1 백업 전략

| 백업 | 주기 | 보관 | 위치 |
|------|------|------|------|
| 자동 스냅샷 | 주간 (일요일 03:00) | 4주 | GCS kg-backups/ |
| 수동 스냅샷 | Phase 전환 시 | 영구 | GCS kg-backups/manual/ |
| BigQuery 내보내기 | 주간 | 4주 | BigQuery backup 데이터셋 |

### 4.2 롤백 전략

```python
# loaded_batch_id 기반 선택적 롤백
def rollback_batch(batch_id: str):
    """특정 배치의 모든 노드/관계 제거"""
    neo4j.run("""
        MATCH (n)
        WHERE n.loaded_batch_id = $batch_id
        DETACH DELETE n
    """, batch_id=batch_id)
```

### 4.3 TTL 정책 (v19)

| 대상 | TTL | 처리 |
|------|-----|------|
| 이력서 | 3년 미갱신 | soft-delete |
| JD | 마감 후 1년 | soft-delete |
| 크롤링 원본 | 6개월 | GCS lifecycle 삭제 |
| dead-letter | 30일 | BigQuery partition 삭제 |

---

## 5. 프롬프트 버전 관리

### 5.1 버전 관리 정책

| 항목 | 전략 |
|------|------|
| 저장 | Git (prompts/ 디렉토리) |
| 버전 형식 | v{major}.{minor} (예: v1.0, v1.1) |
| 회귀 테스트 | 50건 Golden Set, <5% 품질 차이 |
| 메타데이터 | 추출 결과에 prompt_version 기록 |

### 5.2 업데이트 절차

```
1. prompts/ 디렉토리에 새 버전 작성
2. 50건 Golden Set 회귀 테스트 실행
3. 품질 차이 <5% 확인
4. git commit + PR 리뷰
5. 배포 (Cloud Run Job 이미지 업데이트)
6. 증분 파이프라인에서 자동 적용
```

---

## 6. 비용 모니터링

### 6.1 비용 추적

| 항목 | 추적 방법 | 알림 기준 |
|------|----------|----------|
| LLM API 비용 | Anthropic 대시보드 + BigQuery 로깅 | 일일 >$5 |
| Vertex AI 비용 | GCP Billing | 월간 >$50 |
| Neo4j 비용 | AuraDB 대시보드 | 월간 >$250 |
| Cloud Run 비용 | GCP Billing | 월간 >$100 |
| 크롤링 비용 | BigQuery crawl_company_summary | 월간 >$150 |
| **총 월간 비용** | GCP Budget Alert | **>$500** |

### 6.2 GCP Budget Alert 설정

```
- 50% 도달: INFO 알림
- 80% 도달: WARNING 알림
- 100% 도달: CRITICAL 알림 + 자동 스케일 제한
```

---

## 7. 보안

### 7.1 서비스 계정 (최소 권한)

| 계정 | 접근 범위 | 주의 |
|------|----------|------|
| kg-crawling | GCS 쓰기, BQ 쓰기 | **Neo4j 접근 불가** |
| kg-processing | GCS 읽기/쓰기, BQ 쓰기, Vertex AI | **Neo4j 접근 불가** |
| kg-loading | GCS 읽기, BQ 읽기 | **Neo4j 접근 전용** |

### 7.2 네트워크

| 설정 | 상세 |
|------|------|
| Neo4j AuraDB | VPC allowlist: Cloud Run Service IP만 허용 |
| Secret Manager | API 키, DB 자격증명, Neo4j 비밀번호 |
| PII 마스킹 | LLM 전송 전 이름/전화번호/주소 마스킹 |
| 크롤링 | robots.txt 준수, 2초 간격 |

### 7.3 Secret 로테이션

| 시크릿 | 주기 | 방법 |
|--------|------|------|
| Anthropic API Key | 6개월 | Secret Manager 버전 업데이트 |
| Neo4j 비밀번호 | 6개월 | AuraDB 콘솔 + Secret Manager |
| DB 접속 정보 | 6개월 | Secret Manager |

---

## 8. 운영 인력

| Phase | 인력 | 역할 |
|-------|------|------|
| 0-3 | 1 DE + 1 MLE (전업) | 개발 + 운영 겸임 |
| 4+ | 0.3-0.5 FTE | 모니터링 + 증분 처리 + 장애 대응 |
| 온콜 | 로테이션 | CRITICAL 알람 대응 |

---

## 9. 핸드오프 문서 목차 (Phase 4 Week 27)

1. 아키텍처 개요 (GCP 인프라 + Neo4j + 파이프라인)
2. 일일 체크리스트 (모니터링 확인 항목)
3. Runbook 5 절차 (장애 대응)
4. 증분 파이프라인 (Cloud Workflows + Cloud Scheduler)
5. 크롤링 파이프라인 (T3/T4 크롤링 운영)
6. 프롬프트 업데이트 (버전 관리 + 회귀 테스트)
7. 사전 업데이트 (3-Tier alias/synonym 보강)
8. Neo4j 백업/복원 (스냅샷 + 롤백)
9. 비용 모니터링 (GCP Budget + 항목별 추적)
10. Secret Manager 로테이션 (6개월 주기)
