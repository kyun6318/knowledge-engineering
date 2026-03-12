# v3/C4_Component_Layer_EXP 변경 내역 표

**작업일**: 2026-02-28
**관련 리뷰 파일**: `review/C4_Component_Layer_EXP_Review.md`

| ID | 수정 대상 파일 | 수정 이유 | 수정 전 | 수정 후 |
|---|---|---|---|---|
| **E1** | `C4_Component_Layer_EXP.md` | S3 Multipart Upload 시 발생하는 고유한 ETag(hash-N 형태)와 GCS MD5 간의 단순 텍스트 비교 시 무조건 발생하는 무결성 불일치(Mismatch) 버그 해결 | `Checksum Validator`가 S3 ETag와 GCS MD5 해시를 대조해 검증한다고 명시 | `Multipart-Aware Checksum Validator` 컴포넌트로 개편, 안전한 AWS SDK 자체 ChecksumAlgorithm(SHA256 등) 활용으로 명세 정정 |
| **O1** | `C4_Component_Layer_EXP.md` | "객체 사이즈 측정 -> Direct/Multipart 분기 -> 병렬 스레드 청크 전송"을 애플리케이션에서 직접 개발하는 '바퀴의 재발명' 과잉 설계 제거 | `SIZE_EVAL`, `S3_PUT`, `S3_MULTIPART` 3가지 커스텀 병렬 파이프라인 컴포넌트 조합 | SDK에 책임을 모두 위임한 단일 `AWS SDK Transfer Manager` (Managed Concurrency) 컴포넌트로 극적 통폐합 및 코드 간소화 |
| **I1** | `C4_Component_Layer_EXP.md` | 단순 클라우드 식별자(`AWS_ROLE_ARN`)를 Secret Manager에서 읽어와 불필요한 과금 및 I/O 오버헤드 유발하는 아키텍처 방지 | `SM_CLIENT`(`Secret Manager Client`)가 시작 포인트에서 ARN을 가져옴 | 환경 변수(`ENV`) 주입으로 변경하여 불필요한 Secret 서비스 의존성(`SM_CLIENT`) 제거 |
