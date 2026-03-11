# GraphRAG G-2: 대규모 적재 + 사이징 (2주, W10~11)

> **v5 원본**: `03_phase2_file_and_scale.md` §2-2
> **트리거**: S&F 산출물 ③ (480K+ JSONL) PubSub 순차 수신

---

## 대기 구간 B (W7~9, ~1.5주)

> **선행 작업 (~1주)**:
> - Neo4j Professional 사이징 외삽 스크립트 작성
> - Bulk Loading 오케스트레이션 코드 작성

---

## W10: Neo4j Free → Professional 전환

### v5 A3: AuraDB 마이그레이션 절차 (~30분)

```
1. Professional 인스턴스 생성 (사이징 결과 기반)
2. Cypher 쿼리로 Free 인스턴스에서 노드/관계 읽기
3. 새 인스턴스에 UNWIND 배치 적재 (기존 load_candidates_batch 재활용)
4. Vector Index 재생성 + Embedding 재적재
5. 연결 정보 업데이트 (URI, 인증)
6. API + Scheduler 연결 대상 변경
7. Free 인스턴스 삭제
```

### N8: 사이징 외삽

```python
def estimate_neo4j_sizing():
    # 1,000건 적재 후 메모리 측정
    result = session.run("""
        CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Store sizes')
        YIELD attributes RETURN attributes
    """)
    store_size = result  # 바이트

    # 600K 외삽
    estimated_total = store_size * 600
    vector_index_size = 1_800_000 * 768 * 4  # ~5.5GB

    total = estimated_total + vector_index_size
    if total < 8 * 1024**3:   return "8GB ($65/월)"
    elif total < 16 * 1024**3: return "16GB (~$130/월)"
    elif total < 32 * 1024**3: return "32GB (~$260/월)"
    else: return "Vector Index 분리 or 768d→384d 차원 축소"
```

### Vector DB 선택 기준 (VG4 §2.3)

> G-2 사이징 확정 시 아래 기준으로 Vector Index 전략 결정

| 조건 | 선택 | 근거 |
|------|------|------|
| Person < 1M, Chapter < 3M | **Neo4j Vector Index 유지** | 인프라 단순, 복합 쿼리 가능 |
| Person >= 1M 또는 QPS > 50 | Milvus/Pinecone 외부화 | Neo4j 메모리 $50~100/월 절감 |
| **현재 v5 규모 (600K)** | **Neo4j 유지 권장** | S&F가 벡터 검색 API 별도 관리 |

---

## W10~11: PubSub 트리거로 순차 적재

```
S&F 산출물 ③ (JSONL, 10K/chunk) → PubSub → Cloud Run Job
  → JSON Schema 검증
  → UNWIND batch_size=100 적재
  → BigQuery 적재 로그
```

---

## W11: 쿼리 성능 벤치마크

```
Cypher 5종 × 480K+ 데이터:
  □ p95 < 2초 확인
  □ 미달 시: 복합 인덱스 추가
```

---

## 버퍼 0.5주 (W11 후반): Go/No-Go

```
통과 조건:
  □ 480K+ 적재 완료
  □ Neo4j 사이징 안정 (N8)
  □ Cypher p95 < 2초
```
