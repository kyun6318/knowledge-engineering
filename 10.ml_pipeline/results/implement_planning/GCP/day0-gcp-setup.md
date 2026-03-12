# Day 0 — GCP 환경 구성 & 데이터 GCS 업로드

> **목적**: Day 1~3 테스트를 GCP 환경(Vertex AI Workbench 또는 Compute Engine)에서 실행하기 위한 인프라 준비.
> 로컬 데이터를 GCS에 업로드하고, 테스트 VM을 프로비저닝한다.

---

## 0. GCP Init

### 회사 방화벽 설정
- Slakc #support-인프라보안 채널에서 Proxy SSL 복호화 예외처리 신청 진행([지윤님 온보딩 참조](https://www.notion.so/Day-1-Onboarding-2beb52ac8da18011b525feaa18c42a5c?source=copy_link#2beb52ac8da18072b4d7ead82b42d76f))

### gcloud 명령어 설정

```bash
# gcloud 설치 (Mac 환경)
# 방법1. Google Cloud CLI
curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-arm.tar.gz
tar -xf google-cloud-cli-darwin-arm.tar.gz
./google-cloud-sdk/install.sh

# 방법2. Homebrew
brew update && brew install --cask gcloud-cli
gcloud components update

# init
gcloud init
```

## 1. GCP 프로젝트 & API 활성화

```bash
export PROJECT_ID="jobkorea-test-project-11880e88"
export REGION="asia-northeast3"
export ZONE="asia-northeast3-a"
export GCS_BUCKET="gs://${PROJECT_ID}"

gcloud config set project ${PROJECT_ID}
gcloud config set compute/region ${REGION}
gcloud config set compute/zone ${ZONE}

# API 활성화
gcloud services enable \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  documentai.googleapis.com \
  discoveryengine.googleapis.com \
  notebooks.googleapis.com \
  compute.googleapis.com
```

---

## 2. GCS 버킷 생성 & 데이터 업로드

### 2.1 버킷 생성

```bash
# 버킷이 없으면 생성 (asia-northeast3 단일 리전)
export GCS_BUCKET="ml-api-test-vertex"

gsutil ls ${GCS_BUCKET} 2>/dev/null || \
  gsutil mb -l ${REGION} -b on ${GCS_BUCKET}
```

### 2.2 로컬 데이터셋 → GCS 업로드

```bash
# 프로젝트 루트에서 실행
cd ml-platform

# 데이터셋 전체 업로드
gsutil -m cp -r datasets/DS-LLM-EVAL/* ${GCS_BUCKET}/datasets/DS-LLM-EVAL/
gsutil -m cp -r datasets/DS-EMBED-SAMPLE/* ${GCS_BUCKET}/datasets/DS-EMBED-SAMPLE/

# PDF 샘플 (준비된 경우)
gsutil -m cp -r datasets/DS-PDF-SAMPLE/ ${GCS_BUCKET}/datasets/DS-PDF-SAMPLE/

# RAG 문서 (준비된 경우)
gsutil -m cp -r datasets/DS-RAG-DOCS/ ${GCS_BUCKET}/datasets/DS-RAG-DOCS/

# NER 평가셋 (준비된 경우)
gsutil -m cp -r datasets/DS-NER-EVAL/ ${GCS_BUCKET}/datasets/DS-NER-EVAL/

# RAG Gold 쿼리 (준비된 경우)
gsutil -m cp -r datasets/DS-RAG-GOLD/ ${GCS_BUCKET}/datasets/DS-RAG-GOLD/

# 프롬프트 파일
gsutil -m cp -r prompts/ ${GCS_BUCKET}/prompts/

# 업로드 확인
gsutil ls -r ${GCS_BUCKET}/datasets/
```

### 2.3 GCS 최종 구조 확인

```
gs://ml-api-test-vertex/
├── datasets/
│   ├── DS-RAG-DOCS/          # RAG 문서 (PDF + TXT, 200~500건)
│   ├── DS-PDF-SAMPLE/        # Document AI / 멀티모달 평가 (20~30 PDF)
│   │   └── gold/             # 텍스트 추출 정답 (3~5건)
│   ├── DS-LLM-EVAL/          # LLM 평가셋 (llm_eval.jsonl)
│   ├── DS-EMBED-SAMPLE/      # 임베딩 품질 평가 (embed_sample.jsonl)
│   ├── DS-NER-EVAL/          # NER 평가셋 (gold 엔티티/관계)
│   └── DS-RAG-GOLD/          # RAG 검색 gold 쿼리
├── prompts/                  # 프롬프트 파일 (medium_1k_ko.txt 등)
├── results/                  # 테스트 결과 저장 (VM에서 업로드)
├── docai-output/             # Document AI 배치 처리 출력
└── configs/                  # 설정 파일
```

---

## 3. 테스트 실행 환경 프로비저닝

### 옵션 A: Vertex AI Workbench (권장)

```bash
# Workbench 인스턴스 생성 (JupyterLab 포함)
gcloud workbench instances create api-test-workbench \
  --location=${ZONE} \
  --machine-type=e2-standard-4 \
  --boot-disk-size=100 \
  --disable-public-ip=false

# 생성 후 JupyterLab URL 확인
gcloud workbench instances describe api-test-workbench \
  --location=${ZONE} \
  --format="value(proxyUri)"
```

### 옵션 B: Compute Engine VM

```bash
# VM 생성 (서비스 계정에 Vertex AI 권한 필요)
gcloud compute instances create api-test-vm \
  --zone=${ZONE} \
  --machine-type=e2-standard-4 \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=50GB \
  --scopes=cloud-platform \
  --metadata=startup-script='#!/bin/bash
    apt-get update && apt-get install -y python3-pip git
  '

# SSH 접속
gcloud compute ssh api-test-vm --zone=${ZONE}
```

### 옵션 C: Cloud Shell (소규모 빠른 테스트)

```bash
# Cloud Shell은 별도 프로비저닝 불요
# 제한: 세션 타임아웃 (20분 유휴), 메모리 제한
# Day 1 단독 테스트나 빠른 검증에 적합
```

---

## 4. VM 환경 초기화 (옵션 A/B 공통)

```bash
# 코드 클론 또는 GCS에서 다운로드
git clone <repo-url> ~/plan-graph-rag-main
cd ~/plan-graph-rag-main/ml-platform

# Python 의존성 설치
pip install google-genai>=1.5.0 \
            google-cloud-aiplatform>=1.74.0 \
            google-cloud-documentai>=2.29.0 \
            google-cloud-discoveryengine>=0.13.0 \
            pypdf>=4.0.0

# ADC 인증 (Workbench는 자동, VM은 서비스 계정 사용)
# VM의 경우 --scopes=cloud-platform으로 생성했으므로 ADC 자동 적용

# GCS에서 데이터셋 동기화 (로컬 작업용)
gsutil -m rsync -r ${GCS_BUCKET}/datasets/ datasets/
gsutil -m rsync -r ${GCS_BUCKET}/prompts/ prompts/

# 환경변수 설정
export GCP_PROJECT="${PROJECT_ID}"
export GCP_LOCATION="${REGION}"
export GCS_BUCKET="${GCS_BUCKET}"

# results 디렉토리 준비
mkdir -p results
```

---

## 5. Document AI 프로세서 사전 생성

> **반드시 GCP Console에서 수동 생성** (코드로 생성하지 않음)

```
□ GCP Console → Document AI → Processor Gallery
  ├── OCR Processor 생성 (리전: us)
  │   → processor name 기록: projects/ml-api-test-vertex/locations/us/processors/___
  └── Layout Parser 생성 (리전: us)
      → processor name 기록: projects/ml-api-test-vertex/locations/us/processors/___
```

---

## 6. 서비스 계정 권한 확인

```bash
# VM의 기본 서비스 계정 권한 확인
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:compute@developer.gserviceaccount.com" \
  --format="table(bindings.role)"

# 필요한 역할:
# - roles/aiplatform.user          (Vertex AI)
# - roles/storage.objectAdmin      (GCS)
# - roles/documentai.editor        (Document AI)
# - roles/discoveryengine.editor   (Vertex AI Search)

# 부족한 역할 추가 예시
SA="$(gcloud iam service-accounts list --filter='compute' --format='value(email)' | head -1)"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA}" \
  --role="roles/aiplatform.user"
```

---

## 7. 사전 준비 체크리스트

```
□ GCP 프로젝트 API 활성화 완료
□ GCS 버킷 생성 완료
□ 데이터셋 GCS 업로드 완료
  □ DS-LLM-EVAL/llm_eval.jsonl
  □ DS-EMBED-SAMPLE/embed_sample.jsonl
  □ DS-PDF-SAMPLE/ (20~30 PDF)
  □ DS-RAG-DOCS/ (200~500 문서)
  □ DS-NER-EVAL/ (gold 라벨링 10~20건)
  □ DS-RAG-GOLD/ (gold_queries.json)
□ 테스트 VM/Workbench 프로비저닝 완료
□ VM에서 Python 의존성 설치 완료
□ VM에서 ADC 인증 확인 완료
□ Document AI 프로세서 Console 생성 완료 (OCR + Layout)
□ 서비스 계정 권한 확인 완료
□ Budget Alert 설정: $500 경고, $800 강제 중단
```

---

## 8. 결과 업로드 스크립트 (각 Day 종료 시 실행)

```bash
# 테스트 결과를 GCS에 백업
gsutil -m cp -r results/ ${GCS_BUCKET}/results/day${DAY_NUM}/

# 예: Day 1 종료 시
DAY_NUM=1 gsutil -m cp -r results/ ${GCS_BUCKET}/results/day1/
```

---

> **다음 단계**: Day 0 체크리스트 완료 후 → [day1-gcp-plan.md](./day1-gcp-plan.md) 진행
