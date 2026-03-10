1. 먼저 문제 정의를 바꾸는 게 가장 큰 절감 포인트

현재 프롬프트는 사실상 이런 작업을 한 번에 시키고 있어:
	•	엔티티 찾기
	•	엔티티 타입 결정
	•	관계 라벨 생성
	•	수동/능동 해석
	•	evidence 추출
	•	JSON 구조화

이건 LLM 입장에서는 비싼 작업이고, 이력서 도메인에서는 과한 경우가 많아.

이력서용 KG는 보통 관계가 거의 정해져 있어:
	•	CANDIDATE_WORKED_AT_COMPANY
	•	CANDIDATE_HELD_ROLE
	•	CANDIDATE_USED_SKILL
	•	CANDIDATE_STUDIED_AT_SCHOOL
	•	CANDIDATE_HAS_DEGREE
	•	CANDIDATE_HAS_CERTIFICATION
	•	PROJECT_USED_TECH
	•	EXPERIENCE_HAS_START_DATE / END_DATE

즉, 오픈 IE(open information extraction) 로 풀지 말고
“이력서 스키마 채우기 + 그 결과를 그래프로 materialize” 하는 방식으로 바꾸는 게 맞아.

이 한 단계만 바꿔도 비용이 크게 줄어.

⸻

2. 추천 구조: LLM 중심이 아니라 “하이브리드 추출 파이프라인”

A. 문서 전처리: LLM 없이 처리

여기서는 거의 다 비LLM으로 가능해.

1) 중복 제거 / 버전 제거
150GB면 같은 이력서의 수정본, PDF/DOCX 중복, 채용 사이트 export 중복이 많을 가능성이 높아.
	•	SimHash / MinHash / locality-sensitive hashing
	•	파일 해시 + 텍스트 정규화 해시
	•	section 단위 유사도 비교

이걸로 아예 처리 대상 자체를 줄일 수 있음.

2) 문서 타입 분류
이력서, 자기소개서, 포트폴리오, 경력기술서가 섞여 있으면 먼저 분류.
	•	char n-gram + linear model
	•	작은 문서 분류 모델

이유는 문서 타입별 추출 규칙이 완전히 다르기 때문.

3) 섹션 분할
이력서는 섹션 구조가 강해.
	•	경력
	•	학력
	•	기술
	•	프로젝트
	•	자격증
	•	수상
	•	자기소개

이건 heading 패턴, 위치 정보, 줄 간격, 날짜 패턴으로 꽤 잘 나뉜다.

여기서 전통적 ML이 강한 이유가 있어:
	•	입력 특성이 명확함
	•	레이블 공간이 작음
	•	반복 패턴이 많음

가능한 방법:
	•	규칙 + LightGBM/SVM
	•	CRF로 line labeling
	•	PDF layout feature 활용

섹션 분할만 잘해도 LLM 호출량이 확 줄어.
예를 들어 연락처/기본정보/목록형 기술 스택은 LLM이 필요 없다.

⸻

3. 엔티티 추출은 “전부 LLM”이 아니라 계층적으로

1순위: 규칙/사전으로 가능한 엔티티

이력서에는 규칙으로 잘 잡히는 항목이 많아.
	•	이메일
	•	전화번호
	•	날짜
	•	기간
	•	URL / GitHub / Blog
	•	학위 표기
	•	자격증 번호 패턴
	•	기술명 사전 매칭
	•	회사명/학교명 사전 매칭

여기서는 LLM이 필요 없음.

2순위: 작은 NER 모델

규칙으로 안 잡히는 엔티티만 작은 모델로.

예:
	•	회사명
	•	직무명
	•	프로젝트명
	•	역할명
	•	도메인 스킬
	•	제품/서비스명

추천 접근:
	•	token classification
	•	span classification
	•	BIO tagging

모델은 굳이 큰 생성형 모델일 필요 없고,
작은 한국어 encoder 기반 모델이나 CRF/BiLSTM-CRF 계열로도 충분히 실용적일 수 있어.

특히 이력서는 문장보다 라인/블록 구조가 중요해서,
텍스트 자체보다 아래 feature가 잘 먹혀:
	•	줄 위치
	•	섹션명
	•	괄호 패턴
	•	날짜 근접성
	•	bullet 여부
	•	콜론/슬래시/파이프 구분자
	•	이전/다음 줄 타입

즉, 전통적 ML의 ROI가 높아.

⸻

4. 관계 추출은 “문장 전체 해석”보다 “블록 기반 조립”이 더 싸고 더 안정적

이력서의 관계는 문법 해석보다 구조 해석으로 많이 복원 가능해.

예를 들어 이런 블록:

2021.03 - 2023.08 | ABC Tech | Backend Engineer
- 추천 시스템 API 개발
- Python, FastAPI, PostgreSQL 사용

이걸 굳이 LLM에게 문장 해석시키지 않아도 아래 그래프는 만들 수 있어:
	•	Candidate — WORKED_AT → ABC Tech
	•	Candidate — HELD_ROLE → Backend Engineer
	•	Experience — STARTED_AT → 2021.03
	•	Experience — ENDED_AT → 2023.08
	•	Experience — USED_SKILL → Python
	•	Experience — USED_SKILL → FastAPI
	•	Experience — USED_SKILL → PostgreSQL

즉, 관계 추출을 두 단계로 바꾸는 게 좋다:

1단계: 블록 파싱

경력 블록, 학력 블록, 프로젝트 블록을 분리

2단계: relation assembly

블록 내부 슬롯 간 관계를 규칙으로 조립

이 방식은 비용도 싸고, 결과 정규화도 쉬워.

⸻

5. LLM은 어디에만 써야 하냐

LLM은 다음 같은 고난도/애매한 케이스에만 쓰는 게 맞아.

LLM 전용 후보
	•	자기소개/서술형 경력 요약에서 암묵적 관계 추출
	•	“성과”와 “역할” 분리
	•	프로젝트 설명 속 기술 사용 맥락 해석
	•	희소한 직무/산업 도메인 표현 정규화
	•	불완전한 문장 복원
	•	여러 줄에 흩어진 엔티티 연결
	•	confidence 낮은 경우 재판정

즉, 전체 문서의 100%가 아니라 잔여 5~20%만 LLM으로 보내는 구조가 이상적이야.

⸻

6. 비용 절감의 핵심 기술: confidence-based routing

이게 실무에서 가장 중요해.

각 추출 결과에 confidence를 붙여:
	•	규칙 신뢰도
	•	NER 모델 확률
	•	relation classifier 확률
	•	entity linking 유사도
	•	섹션 분류 확률

그리고 이렇게 분기:
	•	high confidence → 바로 저장
	•	medium confidence → 작은 재검증 모델
	•	low confidence → LLM 호출

이 방식이면 LLM은 “필요할 때만” 쓴다.

특히 relation extraction에서 효과가 큼.
모든 엔티티 쌍을 LLM에 던지면 비용이 폭증하니까,
먼저 후보 pair 생성(candidate generation) 을 해야 해.

예:
	•	같은 블록 안에 있는 엔티티만
	•	일정 거리 이내만
	•	타입 조합이 가능한 pair만
(회사-직무, 프로젝트-기술, 학교-학위 등)

이렇게 하면 relation 후보 수가 급감한다.

⸻

7. 가장 현실적인 방법: LLM으로 “학습 데이터”만 만들고, 운영은 ML로

이건 특히 추천해.

단계
	1.	전체 150GB 중 일부 샘플만 뽑음
	2.	지금의 강한 LLM 프롬프트로 high-quality silver label 생성
	3.	사람 검수로 gold set 일부 확보
	4.	그걸로 NER / relation / section 모델 학습
	5.	운영에서는 ML 우선, LLM fallback

이건 일종의 distillation이야.

즉,
비싼 LLM을 “교사”로 쓰고, 싼 모델을 “실무 운영자”로 쓰는 구조.

이 방식의 장점:
	•	초기에 라벨링 비용 절감
	•	도메인 적합한 모델 확보
	•	운영 비용 급감
	•	규칙/ML/LLM을 함께 개선 가능

⸻

8. 이력서 도메인에서 특히 잘 먹히는 전통적 ML 포인트

1) 템플릿 클러스터링

이력서는 완전 자유형 같아도 실제로는 패턴이 반복돼.
	•	채용 플랫폼 export 형식
	•	기업 양식
	•	대학/기관 양식
	•	PDF 생성기별 레이아웃

문서를 레이아웃/표제/구분자 기준으로 클러스터링해서
템플릿별 추출기를 두면 매우 싸게 처리 가능해.

예:
	•	heading signature
	•	날짜 표현 패턴
	•	표/컬럼 구조
	•	bullet structure

이건 LLM보다 오히려 전통적 방법이 강하다.

2) entity linking

회사명/기술명/학교명은 생성보다 정규화가 중요해.

예:
	•	네이버, NAVER, (주)네이버
	•	PyTorch, pytorch, torch
	•	서울대, 서울대학교

이건 LLM보다 아래 조합이 더 안정적:
	•	alias dictionary
	•	fuzzy matching
	•	BM25 / trigram
	•	embedding nearest neighbor
	•	rerank classifier

즉, 엔티티 생성보다 canonicalization에 ML을 써라.

3) line/block classification

이력서는 sentence NLP보다 line NLP가 더 중요함.
문장 단위가 아니라 줄 단위 분류로도 많은 정보가 풀린다.

⸻

9. 현재 프롬프트에서 특히 비용을 키우는 부분

1) 관계 라벨을 자유 생성

ENGLISH_RELATION_TYPE을 자유롭게 만들게 하면
LLM이 의미 해석 + naming까지 하게 된다.

이력서라면 관계 라벨은 폐쇄 집합으로 제한하는 게 맞아.

2) evidence를 항상 자연어로 생성

evidence는 생성하지 말고 원문 span offset으로 저장하는 게 낫다.

예:
	•	document_id
	•	page
	•	block_id
	•	line_start / line_end
	•	char_start / char_end

이렇게 하면 토큰 절감 + 검증 용이.

3) 모든 문장을 관계 우선으로 해석

이력서는 관계가 문장에만 있지 않다.
오히려 표, 라인, 헤더, bullet에 많다.

그래서 relation-first LLM보다
section/block-first parsing이 맞다.

⸻

10. 권장 아키텍처

추천 파이프라인
	1.	문서 정규화
	•	OCR/PDF 파싱
	•	line/block 추출
	•	중복 제거
	2.	문서/섹션 분류
	•	이력서/자기소개서/포트폴리오 분리
	•	경력/학력/기술/프로젝트 섹션 분리
	3.	규칙 기반 추출
	•	날짜, 이메일, URL, 전화번호, 자격증 패턴
	•	기술 사전, 학교/회사 사전
	4.	작은 ML 추출
	•	NER
	•	section-aware slot filling
	•	pairwise relation classifier
	5.	그래프 조립
	•	템플릿/블록 규칙으로 엣지 생성
	•	canonical entity linking
	6.	LLM fallback
	•	confidence 낮은 블록만
	•	자유서술/요약/성과/복합 프로젝트 설명만
	7.	후처리
	•	중복 엔티티 병합
	•	충돌 해결
	•	provenance 저장

⸻

11. 비용 절감 효과는 어느 정도 기대할 수 있나

정확한 수치는 데이터 형태를 봐야 하지만, 방향성은 분명해.

현재:
	•	전체 문서 100%를 LLM 처리

개선 후:
	•	전처리/섹션분리/정형 항목: 비LLM
	•	명확한 엔티티/관계: 규칙 + 작은 ML
	•	애매한 일부만 LLM

실무적으로는 보통 아래 구조를 목표로 잡는다:
	•	50~70%: 규칙/사전/템플릿
	•	20~40%: 작은 ML
	•	5~15%: LLM fallback

이력서가 반정형이고 반복 양식이 많다면
LLM 토큰 비용을 원래의 10~30% 수준까지 낮추는 것도 충분히 노려볼 만해.
데이터 품질이 좋고 템플릿 편중이 크면 그보다 더 낮아질 수도 있다.

다만 이 수치는 추정치고,
실제 절감률은 다음에 크게 좌우돼:
	•	PDF 품질
	•	스캔/OCR 비중
	•	이력서 양식 다양성
	•	한국어/영문 혼합 정도
	•	자유서술 비중

⸻

12. 내가 가장 추천하는 현실적 실행 순서

1단계: 목표 KG를 줄여

오픈형 KG 말고 채용/이력서용 폐쇄형 ontology로 바꿔.

2단계: 1,000~5,000개 샘플에만 현재 LLM 적용

silver label 생성.

3단계: 아래 4개부터 모델화
	•	문서/섹션 분류
	•	날짜/기간/연락처 추출
	•	회사/직무/기술 NER
	•	블록 기반 relation assembly

4단계: confidence routing 붙여

LLM fallback만 남겨.

5단계: 운영 로그로 active learning

LLM이 자주 처리하는 케이스만 추가 학습.
