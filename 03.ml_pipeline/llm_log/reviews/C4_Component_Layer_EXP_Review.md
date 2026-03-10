# C4 Component Layer - Cross-Cloud Exporter (EXP) 리뷰

**작성일**: 2026-02-28
**대상**: `v3/C4_Component_Layer_EXP.md`
**관점**: 설계 오류(Errors), 과잉 설계(Over-engineering), 개선점(Improvements)

---

## ❌ 설계 오류 (Design Errors) & 타당성 검증

### [E1] S3 Multipart Upload의 ETag 무결성 검증 논리 오류 (Checksum Mismatch)
- **설명**: `Checksum Validator` 컴포넌트에서 "S3의 ETag와 GCS MD5 해시를 대조해 전송 데이터 무결성을 검증합니다"라고 정의되어 있으며, 이는 `S3_MULTIPART` (멀티파트 업로더) 흐름에도 연결되어 있습니다.
- **오류 검증**: 단일 `PutObject`로 업로드된 S3 객체의 ETag는 파일의 원본 MD5 해시와 일치하지만, **멀티파트 업로드(Multipart Upload)로 생성된 객체의 ETag는 전체 파일의 MD5가 아닙니다.** S3 멀티파트 ETag는 각 파트의 MD5 해시를 이어붙인 뒤 다시 해싱하고 뒤에 파트 개수를 붙이는 형태(예: `hash-N`)로 계산됩니다. 따라서 GCS의 단일 객체 MD5 해시와 S3 멀티파트 ETag를 단순 텍스트 비교하면 **무조건 Mismatch(실패)가 발생하여 무한 재시도나 500 에러를 유발하는 치명적인 버그**입니다.
- **올바른 아키텍처**: 멀티파트로 전송할 경우 단순 ETag 비교를 포기하고 AWS SDK가 제공하는 부가적인 Checksum 기능(예: `ChecksumAlgorithm='SHA256'`)을 명시하여 활용하거나, GCS에서 GCS-S3 간 전송 전용 Chunk Hash 계산 로직을 별도로 두어야 합니다.

---

## ⚙️ 과잉 설계 (Over-engineering) & 타당성 검증

### [O1] 사이즈 기반 라우팅 및 Multipart 직접 구현 (SDK 바퀴의 재발명)
- **설명**: 다이어그램 상에 `Object Size Evaluator`가 GCS 객체 크기를 판별하여 크기가 작으면 `S3 Direct Put Worker`로, 크면 `S3 Multipart Uploader`로 병렬 청크와 함께 분기시키는 커스텀 파이프라인 로직이 명세되어 있습니다.
- **과잉 설계 검증**: AWS 공식 SDK(Boto3, Go SDK, Java SDK 등)의 **S3 Transfer Manager** 모듈(예: Boto3의 `s3.upload_fileobj` 또는 `transfer.S3Transfer`)은 내부적으로 파일 객체의 크기를 파악하여 `multipart_threshold` (기본 8MB 등)를 넘으면 자동으로 멀티파트 청크를 분할하고 스레드 풀을 열어 병렬 업로드를 수행합니다. 개발자가 애플리케이션 레벨에서 Size Evaluator와 Worker 분기를 직접 구현하는 것은 완벽한 오버 엔지니어링이자 '바퀴의 재발명'입니다.
- **올바른 아키텍처**: `SIZE_EVAL`, `S3_PUT`, `S3_MULTIPART` 컴포넌트를 모두 지우고, **`AWS_SDK_Transfer_Manager` 단일 컴포넌트**로 통합하여 SDK 내장 최적화 기능에 전송 책임을 위임해야 합니다.

---

## 💡 개선점 (Improvements) & 타당성 검증

### [I1] 비암호화 구성값(ARN)의 Secret Manager 저장
- **설명**: `Secret Manager Client`의 설명에 "`AWS_ROLE_ARN` 및 `AWS_EXTERNAL_ID` 같은 설정 정보를 Secret Manager로부터 가져옵니다"라고 명시되어 있습니다.
- **개선 제안**: `AWS_EXTERNAL_ID`는 일종의 패스워드 역할을 할 수 있어 Secret Manager 사용이 적절할 수 있으나, `AWS_ROLE_ARN`은 클라우드 리소스의 식별자일 뿐 '비밀(Secret)'이 아닙니다. 식별자를 Secret Manager에 넣으면 요금 부과 및 관리 포인트 증가만 초래합니다. `Role ARN`은 단순 환경변수(Env Var) 또는 Config로 주입받고, Secret Manager 접근은 최소화하는 것이 인프라 구성의 모범 사례입니다.

---

## 요약 (권고안)
Cross-Cloud Exporter 설계에서 **S3 멀티파트 ETag 오류(E1)**를 수정하고, **전송 최적화 컴포넌트 3개를 AWS SDK 매니지드 코어로 통폐합(O1)**하여 코드를 극적으로 간소화할 것을 강력히 권고합니다.
