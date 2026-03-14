## 목적

<aside>
🔥

이력서/경력기술서 내 **경력-프로젝트-성과 구조 추출**

</aside>

- 경력기술서 내 구조화된 정보를 추출하기 위한 Structure Information Extraction(이하 SIE) 방안으로 **GLiNER2**를 선정하여 PoC를 진행하며, 동시에 SLM 기반 추출 모델인 **NuExtract 1.5**를 비교 검토하여 최적의 운영 파이프라인을 구축한다.
- Named Entity Recognition(NER)은 원본 데이터가 수정되거나 유실될 경우 추론된 데이터의 정확한 관계 파악이 어렵다.
    - 기존 표면적인 엔티티 추출은 사내 NER 모델이 수행하고 있으나, 각 엔티티가 표층적으로 추출될 뿐 구조화나 관계 정보가 누락된 상태
- GLiNER2 저자는 Parent-child relationships와 repeated patterns를 다루도록 설계되었다고 언급하며, hierarchical extraction이 복잡한 nested information을 다루기 위한 것이라고 말한다. 이는 이력서처럼 동일한 상위 구조가 문서 안에서 여러 번 반복되는 데이터에 적합하다고 판단된다. 출처- [ACL Anthology](https://aclanthology.org/2025.emnlp-demos.10.pdf)
    - 경력기술서 특징
        
        ```python
        - 이력서
            - 경력 1
                - 프로젝트 1
                    - 기술 / 성과 / 기간 …
                - 프로젝트 2
                    - 기술 / 성과 / 기간 …
            - 경력 2
                - 프로젝트 1
                    - 기술 / 성과 / 기간 …
                - 프로젝트 2
                    - 기술 / 성과 / 기간 …    
                    
                            
        **최종 Output **
        -> 경력 1 = {회사, 직무, 기간, 설명, 성과}, 경력 2 = {회사, 직무, 기간, 설명, 성과}
        ```
        

## 기대 효과

1. 파이프라인 단순화
    1. 표면적인 엔티티를 추출하는 모델이 아닌, SIE 중심 구조로 전환하면 모델 수와 후처리 조합 규칙 감소 기대
    2. GLiNER2 논문에서도 기존에 분리되어 있던 모델들을 하나의 효율적 솔루션으로 대체하는 방향을 핵심 메시지로 제시한다. [ACL Anthology](https://aclanthology.org/2025.emnlp-demos.10.pdf)
2. 다운스트림 활용성 향상
    1. JSON-ready 구조의 결과는 후보자 검색, 스킬 매칭, 프로젝트 기반 추천, 타임라인 검증, 프로필 요약 생성 등 후속 기능에서 별도 구조 복원 비용 감소 기대
3. 추적성, 정교한 운영 정책
    1. field별 confidence/span을 함께 저장하여 근거 확인의 용이성 존재
    2. 특정 필드만 threshold를 상향하는 방식 [GitHub](https://github.com/fastino-ai/GLiNER2)

## 검토 대안

1. NER + RE 파이프라인
    1. 경력/프로젝트처럼 반복 구조가 많은 문서에서는 엔티티 추출 오류가 관계 추론 오류로 직결되며 예외 규칙(Rule-based)이 빠르게 누적되어 유지보수가 어려움
2. 범용 LLM 기반 JSON 추출
    1. 초기 구현은 빠르나 출력 형식의 변동성이 존재
    2. API 비용, 개인정보 외부 전송 처리, 운영 통제의 어려움이 존재
3. **GLiNER2 기반 SIE**
    1. 처음부터 '구조 추출'을 목표로 설계된 인코더 기반 프레임워크
    2. Span 단위의 위치 정보와 신뢰도 제공
    3. Encoder 모델 특성 상 원문에서 정확한 값을 가져오기 때문에 Hallucination 위험 부재
4. **NuExtract 1.5 기반 SIE**
    1. 최근 공개된 구조화 데이터 추출 특화 SLM(Phi-3.5, Qwen 등 기반)모델
    2. 긴 문맥(Long Context) 처리와 다국어(한국어/영어 혼합) 문서에 우수
    3. 스키마만 주어지면 프롬프트 엔지니어링 없이 양질의 Stuructured 구조를 반환

### **GLiNER2 vs NuExtract 1.5 비교**

| 구분 | GLiNER2 | NuExtract 1.5 |
| --- | --- | --- |
| **기반 아키텍처** | BERT 계열(Encoder-based)
- microsoft/deberta-v3-base | 생성형 SLM
- Phi-3.5-mini |
| **추적성 (Traceability)** | **매우 우수**
(정확한 Start/End Span, Confidence Score 기본 제공) | **보통
(**생성 텍스트 기반이므로 원문 하이라이팅을 위해 별도 string-matching 필요) |
| **문맥 길이 (Context)** | 2048 토큰 제한 (장문 이력서는 Chunking 필수) | 무제한에 가까운 긴 문맥 지원 (Sliding Window 자체 지원) |
| **다국어 및 예외 처리** | 학습 데이터에 크게 의존 | 기본적으로 다국어 성능이 뛰어나며, 혼합 문서에 강함 |

## GLiNER2 중심의 NuExtract 1.5 병행 전략

### 주력 모델 (GLiNER2) 운영 전략

: 도메인 특화 및 통제력 강화

 Encoder 기반 모델로서 원문 텍스트 내에서 정확한 Span을 추출하므로 생성형 모델의 고질적인 문제인 Hallucination 위험을 차단하며, 추출된 결과의 field별 confidence score를 통해 중요도가 높은 필드는 개별 Threshold를 상향 적용하는 등 통제 및 검수 편의성을 극대화 하기 위해 주력 모델로 활용하는 전략을 제안한다.

 경량화된 인코더 아키텍처이므로 생성형 SLM(3.5B 등) 대비 파라미터 수와 연산량이 현저히 적다. 이로 인해 GPU VRAM 요구량이 상대적으로 낮고 추론 속도가 빠르며, 대규모 이력서 데이터의 일괄 처리 시 파이프라인 처리 효율성 확보할 수 있다.

### 보조 모델 (NuExtract 1.5) 활용 전략

: 초기 데이터 구축 및 엣지 케이스 대응

 NuExtract 1.5는 생성형 모델이므로 초기 검증용 및 데이터 레이블링에 효과적이다. 초기 학습 특성상 라벨 변동성이 높기에 초기 대응에는 생성형 모델이 우수하며, 본 모델은 최대 3.51B 파라미터 수준으로 VRAM 약 15GB 정도만 요구하므로 단일 일반 GPU(예: RTX 3090/4090 등) 환경에서도 원활하게 구동되어 로컬망 내 독립적인 구축 및 테스트에 용이하다.

 본 모델을 직접 파인튜닝하여 운영할 수도 있으나, 생성형 모델의 특성상 Hallucination과 높은 Latency, 그리고 원문 추적성 확보의 한계로 인해, 주력 모델보다는 데이터 생성용 혹은 파이프라인에서의 보조 도구로 활용하는 전략을 제안한다.

### **NuExtract 1.5를 활용한 하이브리드 보완 전략**

1. NuExtract 1.5로 데이터 레이블링 → 수동 검수 → LoRA 파인튜닝으로 Adapter 생성 → 데이터 확보 후 Full SFT 진행
2. GLiNER2의 가장 큰 한계인 '2048 토큰 길이 제한' → **NuExtract 1.5**를 보완재로 투입 가능
    1. **표준 길이의 이력서:** 추적성이 좋은 GLiNER2가 전담하여 정확도와 검수 편의성 확보
    2. **매우 긴 경력기술서나 혼합 언어 문서:** 문맥 길이 제한이 없고 다국어 추론에 강한 NuExtract 1.5로 라우팅하여 정보 유실 방지 및 추출 안정성 보장

## 예상 입력/출력 형태

### **예상 입력 텍스트**

```
ABC테크 / Backend Engineer / 2021.03 ~ 현재 재직중
- 결제 플랫폼 고도화 프로젝트 리드
- Spring Boot, Kafka, AWS 기반 백엔드 개발
- API 응답 시간 35% 개선, 장애율 20% 감소

실시간 정산 시스템 개편 / 2023.01 ~ 2023.09
- 주문-결제 정산 파이프라인 재설계
- Kafka Consumer 병렬화 및 배치 최적화
- 본 시스템의 리펙토링을 통해 처리량 2배 향상 및 에러 56% 감소
```

### **예상 출력 JSON**

```json
{
  "experience": [
    {
      "company": { "text": "ABC테크", "confidence": 0.98, "start": 6, "end": 11 },
      "title": { "text": "Backend Engineer", "confidence": 0.95, "start": 14, "end": 30 },
      "start_date": { "text": "2021.03", "confidence": 0.97, "start": 33, "end": 40 },
      "end_date": { "text": "현재", "confidence": 0.94, "start": 43, "end": 45 },
      "employment_status": { "text": "current", "confidence": 0.96 },
      "experience_description": [
        { "text": "결제 플랫폼 고도화 프로젝트 리드", "confidence": 0.90, "start": 49, "end": 68 },
        { "text": "Spring Boot, Kafka, AWS 기반 백엔드 개발", "confidence": 0.89, "start": 71, "end": 106 }
      ],
      "experience_achievements": [
        { "text": "API 응답 시간 35% 개선", "confidence": 0.92, "start": 109, "end": 126 },
        { "text": "장애율 20% 감소", "confidence": 0.90, "start": 128, "end": 138 }
      ]
    }
  ],
  "project": [
    {
      "anchor_company": { "text": "ABC테크", "confidence": 0.97 },
      "anchor_experience_start": { "text": "2021.03", "confidence": 0.96 },
      "project_name": { "text": "실시간 정산 시스템 개편", "confidence": 0.93, "start": 147, "end": 160 },
      "project_start_date": { "text": "2023.01", "confidence": 0.95, "start": 163, "end": 170 },
      "project_end_date": { "text": "2023.09", "confidence": 0.94, "start": 173, "end": 180 },
      "project_status": { "text": "ended", "confidence": 0.95 },
      "project_description": [
        { "text": "주문-결제 정산 파이프라인 재설계", "confidence": 0.91, "start": 184, "end": 203 },
        { "text": "Kafka Consumer 병렬화 및 배치 최적화", "confidence": 0.89, "start": 206, "end": 230 }
      ],
      "achievements": [
        { "text": "처리량 2배 향상", "confidence": 0.92, "start": 233, "end": 242 }
      ],
      "tech_stack": [
        { "text": "Kafka", "confidence": 0.94, "start": 206, "end": 211 }
      ]
    }
  ]
}
```