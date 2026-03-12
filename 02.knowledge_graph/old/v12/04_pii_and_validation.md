# PII 마스킹 및 파이프라인 검증 v12

> 작성일: 2026-03-11 | 기준: 온톨로지 v19
>
> v11 대비 주요 변경:
> - S2: PII 매핑 테이블 저장소를 구체적으로 선택 (GCS CMEK 추천)
> - S4: 한국 전화번호 변형 패턴 8종 커버 정규식 추가

---

## 1. PII 마스킹 전략

### 1.1 대상 PII 필드

| PII 유형 | 소스 | 예시 | 위험도 |
|---------|------|------|--------|
| 이름 (성명) | resume-hub.Person.name | "김철수" | High |
| 전화번호 | resume-hub.Person.phone | "010-1234-5678" | High |
| 이메일 | resume-hub.Person.email | "kim@email.com" | High |
| 주소 | resume-hub.Person.address | "서울시 강남구..." | Medium |
| 주민번호 | 파일 이력서 | "900101-1234567" | Critical |
| 생년월일 | resume-hub.Person.birthDate | "1990-01-01" | Medium |

### 1.2 마스킹 방식

| 유형 | 방식 | 가역성 | 이유 |
|------|------|--------|------|
| 이름 | **비가역 토큰** `[NAME_001]` | 비가역 (매핑 테이블 별도) | LLM 전송 시 필수 마스킹 |
| 전화번호 | **비가역 토큰** `[PHONE_001]` | 비가역 | LLM 전송 시 필수 마스킹 |
| 이메일 | **비가역 토큰** `[EMAIL_001]` | 비가역 | LLM 전송 시 필수 마스킹 |
| 주소 | **삭제** | 비가역 | Graph에 불필요 |
| 주민번호 | **즉시 삭제** | 비가역 | 절대 저장/전송 불가 |
| 생년월일 | **연도만 유지** | 부분 가역 | 연령대 계산용 |

### 1.3 마스킹 범위

```
[DB 이력서 흐름]
resume-hub DB → DB 커넥터 → PII 마스킹 → GCS jsonl (마스킹됨)
                                ↓
                          매핑 테이블 (person_id → 원본 이름/전화번호)
                          → PII 매핑 저장소 (§1.3.1 참조)
                                ↓
                          LLM 전송: 마스킹된 텍스트만 전송
                          Graph 적재: person_id 기반 (원본 이름 불포함)

[파일 이력서 흐름]
파일 (GCS) → 파일 파서 → PII 탐지 → PII 마스킹 → LLM 추출
```

#### 1.3.1 PII 매핑 테이블 저장소 (v12 S2 신규)

> v11 리뷰에서 "매핑 테이블 저장소가 '별도 보안 저장소'로만 언급" (Medium) 지적.
> 500K+ 건의 PII 매핑은 Secret Manager에 부적합 (소량 키-값 전용).

**추천: GCS 암호화 파일 (CMEK)**

| 항목 | 설계 |
|------|------|
| 저장소 | GCS `gs://kg-pii-mapping/` (별도 버킷) |
| 암호화 | CMEK (Customer-Managed Encryption Key) — Cloud KMS |
| 형식 | JSONL (person_id → {name, phone, email}) |
| 접근 통제 | 별도 서비스 계정 `kg-pii-reader` (storage.objectViewer만) |
| 접근 로그 | Cloud Audit Logs 자동 기록 |
| 보존 기간 | 서비스 종료 시까지 (법률 검토 결과에 따라 조정) |
| 삭제 | 개인정보 삭제 요청 시 해당 JSONL 라인 제거 + GCS 버전 삭제 |

**대안 1: BigQuery 별도 데이터셋**
- `kg_pii.mapping` 데이터셋 + Column-level Security (DLP)
- 장점: SQL 쿼리로 조회 가능, 접근 통제 세밀
- 단점: BigQuery DLP 설정 복잡, 비용 +$10/월

**대안 2: CloudSQL (PostgreSQL)**
- 별도 인스턴스 + 디스크 암호화 + 별도 서비스 계정
- 장점: 개별 레코드 CRUD 용이
- 단점: 비용 +$30/월, 관리 부담

**선택 근거**: GCS CMEK가 가장 단순하며, 배치 처리 특성상 개별 레코드 CRUD가 드묾. 접근 로그가 자동으로 남아 감사 추적 가능. Phase 0에서 법률 검토 결과에 따라 대안으로 전환 가능.

### 1.4 파일 이력서 PII 탐지 (v12 S4 보강)

| 방법 | 대상 | 정확도 |
|------|------|--------|
| 정규식 | 전화번호 (§1.4.1), 주민번호 (`\d{6}-\d{7}`), 이메일 | 90%+ |
| 패턴 매칭 | 주소 ("서울시", "경기도" 등 행정구역 + 번지) | 80% |
| 위치 기반 | 이력서 상단 1-5줄 (이름, 연락처 집중 영역) | 90% |

> NER 기반 탐지는 Phase 2 이후 검토. v1에서는 정규식 + 위치 기반으로 충분.

#### 1.4.1 한국 전화번호 정규식 (v12 S4 신규)

> v11 리뷰에서 "010-\d{4}-\d{4} 하나로는 변형 패턴 미탐지" (Low) 지적.
> 한국 전화번호 변형 8종을 커버하는 종합 패턴 추가.

```python
PHONE_PATTERNS = [
    # 휴대폰 (010/011/016/017/018/019)
    # 커버: 010-1234-5678, 010 1234 5678, 01012345678, +82-10-1234-5678,
    #       (010)1234-5678, 010.1234.5678, 011-123-4567
    r'(?:\+82[-\s]?)?0?1[016789][-.\s)]*\d{3,4}[-.\s]?\d{4}',

    # 일반전화 (02, 031~064)
    # 커버: 02-1234-5678, 031-123-4567
    r'0[2-6][0-9]?[-.\s]?\d{3,4}[-.\s]?\d{4}',
]

def detect_phone_numbers(text: str) -> list[tuple[int, int]]:
    """전화번호 위치(start, end) 목록 반환"""
    import re
    matches = []
    for pattern in PHONE_PATTERNS:
        for m in re.finditer(pattern, text):
            matches.append((m.start(), m.end()))
    return matches
```

**탐지율 추정**: v11 단일 패턴 70~80% → v12 종합 패턴 **90%+**

> 잔여 미탐지: 자연어 내 숫자열("전화 공일공 일이삼사 오육칠팔"), 이미지 내 전화번호 등.
> 이들은 NER 기반 탐지(Phase 2+)로 보완.

### 1.5 법률 검토 연동

| 시나리오 | 전략 | 비고 |
|---------|------|------|
| 법률 검토 완료 + 마스킹 승인 | 마스킹 후 LLM API 전송 | **기본 전략** |
| 법률 검토 미완료 | 마스킹 API 기본값 (전량 마스킹) | Phase 0 시작 가능 |
| 외부 전송 불가 판정 | On-premise LLM (EXAONE) 또는 Azure Private Endpoint | 비용 1.6x 증가 |

---

## 2. 파이프라인 검증 체크포인트

### 2.1 검증 흐름도

```
DB/파일 입력
    ↓
[CP1] 입력 검증 ────────────── skip + 로그
    ↓
PII 마스킹
    ↓
[CP2] 마스킹 검증 ──────────── 재마스킹
    ↓
LLM 추출
    ↓
[CP3] LLM 출력 검증 ─────────── 3-Tier 재시도
    ↓
3-Tier 비교
    ↓
[CP4] 정규화 검증 ──────────── needs_review 플래그
    ↓
Graph 적재
    ↓
[CP5] 적재 검증 ────────────── dead-letter
    ↓
Embedding
    ↓
[CP6] 임베딩 검증 ──────────── 재생성
```

### 2.2 CP1: 입력 검증

```python
def validate_input(resume: dict) -> tuple[bool, str]:
    """DB 커넥터 출력 검증"""
    errors = []

    # 필수 필드
    if not resume.get("person_id"):
        errors.append("person_id missing")
    if not resume.get("careers") or len(resume["careers"]) == 0:
        errors.append("no careers found")

    # Career 최소 품질
    for i, career in enumerate(resume.get("careers", [])):
        if not career.get("companyName"):
            errors.append(f"career[{i}].companyName missing")
        if not career.get("startDate"):
            errors.append(f"career[{i}].startDate missing")

    # 텍스트 최소 길이 (LLM 추출 의미 있는 수준)
    text_fields = [
        resume.get("work_details", ""),
        resume.get("career_description", ""),
        resume.get("self_introduction", "")
    ]
    total_text = sum(len(t) for t in text_fields)
    if total_text < 50:
        errors.append(f"insufficient text ({total_text} chars)")

    return len(errors) == 0, "; ".join(errors)
```

**실패 시**: skip + BigQuery 로그 (pipeline='B', error_type='input_validation')

### 2.3 CP2: 마스킹 검증 (v12 S4 보강)

```python
def validate_masking(text: str) -> bool:
    """마스킹 후 PII 잔존 여부 검증"""
    patterns = [
        # 전화번호 — v12 종합 패턴
        r'(?:\+82[-\s]?)?0?1[016789][-.\s)]*\d{3,4}[-.\s]?\d{4}',
        r'0[2-6][0-9]?[-.\s]?\d{3,4}[-.\s]?\d{4}',
        # 주민번호
        r'\d{6}-\d{7}',
        # 이메일 (마스킹 적용 범위: 텍스트 필드만, tech_stack 제외)
        r'[\w.-]+@[\w.-]+\.\w+',
    ]
    for pattern in patterns:
        if re.search(pattern, text):
            return False
    return True
```

**실패 시**: 재마스킹 → 재검증 → 2회 실패 시 dead-letter

### 2.4 CP3: LLM 출력 검증

```python
def validate_llm_output(raw_output: str, schema_class) -> tuple[bool, Any, str]:
    """LLM 출력 → JSON 파싱 → Pydantic 검증"""
    # Step 1: JSON 파싱
    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError:
        # Tier 1: json-repair
        data = json_repair.loads(raw_output)
        if data is None:
            return False, None, "json_parse_failure"

    # Step 2: Pydantic 검증
    try:
        validated = schema_class.model_validate(data)
        return True, validated, "ok"
    except ValidationError as e:
        return False, None, f"pydantic_validation: {e.error_count()} errors"
```

**실패 시**: 3-Tier 재시도 (§7.1 of 01_extraction_pipeline.md 참조)

### 2.5 CP4: 정규화 검증

```python
def validate_normalization(entity: dict) -> str:
    """3-Tier 비교 결과 검증"""
    match_method = entity.get("match_method")
    confidence = entity.get("normalization_confidence", 0)

    if match_method == "unmatched":
        return "needs_review"
    if match_method in ("embedding_mid", "embedding_low") and confidence < 0.70:
        return "needs_review"
    return "ok"
```

**needs_review 시**: BigQuery quality_metrics에 기록, 운영 중 수동 검토 대상

### 2.6 CP5: 적재 검증

```python
def validate_graph_load(batch_result: dict) -> bool:
    """Graph 적재 결과 검증"""
    # 노드 ID 중복 체크
    if batch_result.get("duplicate_ids", 0) > 0:
        return False

    # 관계 무결성 (참조 노드 존재)
    if batch_result.get("dangling_relations", 0) > 0:
        return False

    # 적재 수 일치
    expected = batch_result.get("expected_count", 0)
    actual = batch_result.get("actual_count", 0)
    if expected > 0 and actual / expected < 0.95:
        return False

    return True
```

**실패 시**: dead-letter + loaded_batch_id 기반 롤백

### 2.7 CP6: 임베딩 검증

```python
def validate_embedding(embedding: list[float]) -> bool:
    """임베딩 벡터 검증"""
    # 차원 수 일치
    if len(embedding) != 768:
        return False

    # NaN/Inf 체크
    if any(math.isnan(v) or math.isinf(v) for v in embedding):
        return False

    # 영벡터 체크
    if all(v == 0.0 for v in embedding):
        return False

    return True
```

**실패 시**: 재생성 (1회) → 실패 시 null 임베딩 + 로그

---

## 3. 품질 메트릭 (추출 범위)

> GraphRAG vs Vector 실험 메트릭은 04.graphrag Phase 3 참조.

### 3.1 자동 품질 메트릭 (BigQuery quality_metrics)

| 메트릭 | 목표 | 체크 시점 | 파이프라인 |
|--------|------|----------|----------|
| schema_compliance | ≥95% | 배치 완료 후 | B/B' |
| required_field_rate | ≥90% | 배치 완료 후 | B/B' |
| skill_code_match_rate | ≥70% | Tier 1/2 완료 후 | B/B', A |
| embedding_coverage | ≥85% | Tier 2/3 완료 후 | C |
| scope_type_accuracy | ≥70% | Gold Label 검증 | B/B' |
| outcome_f1 | ≥55% | Gold Label 검증 | B/B' |
| signal_f1 | ≥50% | Gold Label 검증 | B/B' |
| hiring_context_accuracy | ≥65% | Gold Label 검증 | A |
| pii_leak_rate | ≤0.01% | 배치 완료 후 | B/B' |
| dead_letter_rate | <5% | 배치 완료 후 | 전체 |

> v12 변경: pii_leak_rate 목표를 0% → ≤0.01%로 조정.
> 정규식 기반 탐지로 실제 0% 보장은 불가. 확률적 목표가 더 정직.
