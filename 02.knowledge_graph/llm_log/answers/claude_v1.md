이력서 지식 그래프 추출: LLM → ML 전환 비용 절감 전략
150GB 이력서에서 지식 그래프를 전부 LLM으로 추출하는 건 확실히 비용 폭탄입니다. 핵심 인사이트는 이력서는 범용 텍스트가 아니라 반정형(semi-structured) 문서라는 점입니다. 이걸 활용하면 LLM 호출을 극적으로 줄일 수 있습니다.

1. 구조적 파싱 레이어 (Rule-based + Regex) — LLM 불필요
이력서의 60~70%는 사실 LLM 없이도 추출 가능합니다.
섹션 분류: 이력서는 "경력", "학력", "기술스택", "자격증" 등 예측 가능한 섹션 구조를 가집니다. 간단한 키워드 매칭 + 헤더 패턴 인식으로 섹션을 나눌 수 있고, 이건 regex와 heuristic rule로 충분합니다.
정형 필드 추출: 회사명, 재직기간, 직급, 학교명, 졸업연도, 연락처, 이메일 등은 패턴이 매우 일정합니다. 예를 들어 "2019.03 ~ 2022.06 | 삼성전자 | 선임연구원" 같은 포맷은 regex + date parser로 엔티티와 관계(WORKED_AT with properties year)를 바로 뽑을 수 있습니다.
기술 스택 추출: 기술 키워드는 사전(dictionary) 기반 매칭이 가장 효율적입니다. "Python, PyTorch, AWS, Kubernetes" 같은 나열은 기술 사전 + fuzzy matching으로 거의 완벽하게 추출됩니다. 이건 HAS_SKILL 관계로 직접 매핑됩니다.
예상 비용: 거의 0 (compute cost만 발생)

2. 전통 ML 모델 레이어 — NER + Relation Extraction
구조적 파싱으로 못 잡는 부분은 학습된 ML 모델로 처리합니다.
Named Entity Recognition (NER)
한국어 이력서에 특화된 NER 모델을 fine-tune합니다.
베이스 모델 후보: KoELECTRA, KoBERT, 또는 multilingual DeBERTa. 이력서 도메인에서 추출할 엔티티 타입은 제한적입니다 — 인물, 조직, 기술, 학위, 직함, 자격증, 프로젝트명 정도. 이건 범용 NER보다 훨씬 쉬운 태스크입니다.
학습 데이터 구축 전략: 여기서 LLM을 "teacher"로 활용합니다. 전체 150GB가 아니라 대표 샘플 1~2%만 LLM으로 처리해서 silver label을 만들고, 사람이 일부 검수해서 gold label로 승격시킵니다. 이 데이터로 NER 모델을 학습하면, 나머지 98%는 NER 모델이 처리합니다.
추론 비용: KoELECTRA 기반 NER는 SageMaker ml.g4dn.xlarge 하나로 초당 수백 문서를 처리할 수 있습니다. 150GB 전체를 수 시간 내에 처리 가능하고, 비용은 LLM 대비 1/100 이하입니다.
Relation Extraction (RE)
엔티티 쌍이 주어졌을 때 관계 타입을 분류하는 모델입니다.
이력서 도메인의 관계 타입은 사실 매우 제한적입니다: WORKED_AT, STUDIED_AT, HAS_SKILL, CERTIFIED_IN, MANAGED, PARTICIPATED_IN, LOCATED_IN 정도. 이건 multi-class classification 문제로, 작은 BERT 모델로도 90%+ accuracy를 기대할 수 있습니다.
접근법은 entity marker 방식이 효과적입니다 — "[E1]삼성전자[/E1]에서 [E2]선임연구원[/E2]으로 근무" → WORKED_AT 분류. 마찬가지로 LLM 추출 결과를 학습 데이터로 활용합니다.

3. 하이브리드 파이프라인 아키텍처
[이력서 원문]
    │
    ▼
[1단계: Rule-based 파싱] ──→ 정형 엔티티/관계 (60-70%)
    │                         (회사, 기간, 학교, 기술스택)
    │ 파싱 실패 or 비정형 구간
    ▼
[2단계: ML NER + RE] ──────→ 반정형 엔티티/관계 (20-25%)
    │                         (프로젝트 설명, 업무 내용)
    │ 신뢰도 < threshold
    ▼
[3단계: LLM Fallback] ─────→ 복잡한 문맥 추출 (5-10%)
    │                         (모호한 관계, 복합 문장)
    ▼
[Knowledge Graph 통합]
핵심은 Confidence-based Routing입니다. 2단계 ML 모델의 출력에 confidence score를 달아서, 임계값 이하인 경우에만 LLM으로 보냅니다. 이력서는 대부분 정형적이라 LLM fallback 비율이 5~10%로 매우 낮을 겁니다.

4. 비용 비교 추정
대략적인 비교입니다 (150GB, 약 수백만 건 이력서 기준):
현재 (100% LLM): 이력서 1건당 평균 2~3K 토큰 입력 + 1K 출력이라고 가정하면, GPT-4o 기준으로도 수천만 원대, Claude 기준으로도 상당한 비용이 발생합니다. 게다가 처리 시간도 수일에서 수주가 걸립니다.
제안 (하이브리드): Rule-based 65% + ML 25% + LLM 10%로 전환하면, LLM 비용이 1/10로 줄고, ML 추론 비용은 SageMaker 인스턴스 수 시간 분량입니다. 전체적으로 90%+ 비용 절감이 현실적입니다.

5. 추가 최적화 포인트
LLM Teacher → ML Student 파이프라인 자동화: 주기적으로 LLM이 새로운 패턴의 이력서를 처리하고, 그 결과를 ML 모델 재학습에 투입하는 active learning 루프를 구성합니다. 시간이 갈수록 LLM fallback 비율이 더 줄어듭니다.
Batch 단위 LLM 호출: 어쩔 수 없이 LLM을 써야 하는 5~10%도, Anthropic Batch API나 OpenAI Batch API를 활용하면 50% 할인이 적용됩니다.
경량 LLM 활용: Fallback에도 Claude Opus/Sonnet 대신 Haiku급이나 Gemini Flash급 모델을 쓰면 추가 비용 절감이 됩니다. 이력서 관계 추출은 범용 지식이 많이 필요하지 않아서 작은 모델로도 충분합니다.
Properties 추출 분리: 현재 프롬프트에서 엔티티 properties(연도, 수량, 국적 등)도 LLM이 추출하는데, 이런 부가 정보는 NER 이후 후처리(regex, date parser)로 대부분 처리 가능합니다.

실행 우선순위 제안
가장 ROI가 높은 순서는 이렇습니다:
첫째, 기술 사전 기반 스킬 추출 — 바로 구현 가능하고, 이력서에서 기술스택이 차지하는 엔티티/관계 비중이 가장 큼. 둘째, 섹션 파싱 + 정형 필드 regex — 경력/학력 섹션의 회사·기간·학교 추출. 셋째, LLM silver label로 NER 학습 — 샘플 1~2%만 LLM 처리. 넷째, RE 모델 학습 + confidence routing — 파이프라인 완성.
1~2단계만 해도 LLM 호출량을 60~70% 줄일 수 있고, 전체 파이프라인이 완성되면 90%+ 절감이 가능합니다. 특정 단계에 대해 더 깊이 들어갈까요?