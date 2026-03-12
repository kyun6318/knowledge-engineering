P0급(깨질 수 있음) 3개

1) pending_ops.json에 저장한 import_op.operation.name 접근이 SDK마다 안 될 수 있음

import_op.operation.name, vas_import_op.operation.name, engine_op.operation.name 형태는 반드시 존재한다고 가정하면 위험합니다. 어떤 SDK/버전은:
	•	.operation 속성이 없고,
	•	.name만 있거나,
	•	LRO가 아닌 “커스텀 핸들” 객체일 수 있습니다.

수정 권장
	•	저장 시 getattr(import_op, "operation", None) / getattr(import_op, "name", None) 둘 다 시도하고, 둘 다 없으면 “저장 불가 → Day 3에서 list_files/list_documents 기반으로만 판정”으로 내려가세요.
	•	사실 v3 Day 3는 이미 list_files/list_documents로 완료 판정하고 있으니, pending_ops에는 resource name(corpus_name, store_name, engine_id)만 저장해도 됩니다. (op name은 없어도 됨)

결론: op name 저장은 “있으면 좋고 없으면 생략”이어야 안전합니다.

⸻

2) Day 3에서 VAS “문서 수 확인”이 list_documents로 전체를 읽으려 해서 실패/지연 가능
docs = list(doc_client.list_documents(parent=...))
이건 문서가 많으면 페이지네이션/타임아웃/메모리로 쉽게 망가집니다(200~500 docs라도 환경에 따라). 완료 체크는 “전체 리스트”가 아니라 “1개라도 있으면 OK”가 목적이죠.

수정 권장
	•	iterator에서 첫 1개만 뽑고 멈추는 방식(early break)으로 바꾸세요.
	•	또는 import LRO 상태를 직접 확인할 수 있으면 그걸 쓰고(가능한 경우), 아니면 “첫 문서 존재 여부”만 체크.

⸻

3) Document AI 배치 테스트가 성공/실패를 확정하지 않음

v3에서도:
while not operation.done(): ...
print("배치 처리 완료")
return True

이러면 실패해도 PASS가 될 수 있어요.

수정 권장
	•	operation.result()로 예외를 확정시키거나,
	•	if operation.exception(): raise operation.exception() 추가.

이건 “테스트 신뢰성”에 직결됩니다.

⸻

결론 왜곡 가능성 2개

4) 비용 추정 로직이 여전히 “상수 고정”이라 결과가 왜곡될 수 있음

v3에서도 PRICE_PER_1K 고정이고, 특히 Prompt caching 할인율을 0.75로 하드코딩했습니다.
	•	할인율/단가/모델이 바뀌면 절감율이 틀어지고, “25% 절감” Pass/Fail 판단이 흔들립니다.

수정 권장(가장 현실적인 방식)
	•	v3 주석대로 configs/pricing.json로 외부화하고,
	•	결과 표에서 $는 “추정치”로 명확히 표기(이미 하고 있음)
	•	**절감율은 $가 아니라 ‘input_tokens 감소율’**도 같이 출력해 두면 단가 변동에도 결론이 유지됩니다.

C10은 특히 “cached_content_token_count 반환 여부 + cached_tokens 비중”이 더 핵심입니다.

⸻

5) C2 캘리브레이션에서 CountTokens 모델로 여전히 embedding 모델을 쓰고 있음
CALIBRATED_TOKENS_PER_CHAR = calibrate_tokens_per_char(client, ..., "gemini-embedding-001")

CountTokens는 embedding 모델에서 동작 안 할 수 있고, 그러면 fallback 0.6으로 굳습니다(기능은 split-retry로 살아도, “캘리브레이션 값 기록(0.4~0.8)” 목표와 불일치).

수정 권장
	•	캘리브레이션은 gemini-2.5-flash 같은 생성 모델로 고정해서 “텍스트 토큰화 성격”만 잡으세요.
	•	이 값은 배치 효율 최적화용이니 생성 모델 기반이어도 충분합니다.

⸻

아주 작은 정리(옵션)
	•	C5 retrieval hit 판정이 rag_gold[i]에 의존(쿼리 순서 동일 가정).
→ gold를 {query: expected_docs} 맵으로 만들어 매칭하면 더 튼튼합니다.
	•	DS-NER-EVAL/gold.jsonl 경로는 “로컬”인데, 상단에 GCS 구조도 있어서 혼동 여지.
→ “평가는 로컬 파일 기준(또는 GCS에서 다운로드)”를 1줄 명시하면 깔끔합니다.

⸻

최종 평가

v3는 구조/범위/자동화/정량 지표가 잘 잡혔고, “3일 테스트”로는 매우 적절합니다.
남은 필수 패치만 요약하면:
	1.	pending_ops 저장은 op name 없이도 동작하게(=resource name 중심)
	2.	VAS 문서 확인은 전체 list → 1개만 확인으로 변경
	3.	DocAI batch는 operation.result()로 성공/실패 확정
	4.	C10 절감율은 $뿐 아니라 토큰 감소율도 함께
	5.	C2 캘리브레이션 CountTokens 모델을 생성 모델로 변경

이 5개 반영하면, 더 이상 큰 리스크 포인트는 없습니다.