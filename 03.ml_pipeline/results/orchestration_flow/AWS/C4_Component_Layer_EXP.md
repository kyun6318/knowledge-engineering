> **Related Documents**: [C4_Component_Layer_Triggers.md](./C4_Component_Layer_Triggers.md) (Postprocess Trigger — EXP 동기 호출 주체), [C4_Component_Layer_RunAPI.md](./C4_Component_Layer_RunAPI.md) (인증 구조 참조)

```mermaid
graph TD
  subgraph Auth_Modules["Cross-Account IAM Auth"]
    ENV[(Environment Variables)]
    STS_CLIENT["STS AssumeRole Client"]
  end

  subgraph Sync_Engine["Cross-Account Sync Engine"]
    S3_ML_READER["S3 ML Account Reader"]
    S3_SVC_TM["S3 Transfer Manager\n(Service Account — Managed Concurrency)"]
    CSUM_VAL["Multipart-Aware Checksum Validator\n(SDK Native)"]
  end

  ECS_IN([Postprocess Trigger ECS Task Invoke]) --> STS_CLIENT

  %% 인증 획득
  ENV -.->|"inject SERVICE_ACCOUNT_ROLE_ARN"| STS_CLIENT
  STS_CLIENT -->|"1. AssumeRole (cross-account)"| AWS_STS[(AWS STS)]
  AWS_STS -.->|"Temporary S3 Credentials\n(Service Account PutObject)"| S3_SVC_TM

  %% 라우팅 & 전송 액션 (SDK 통합)
  S3_ML_READER -->|"2. stream objects from ML Account S3"| S3_SVC_TM
  S3_SVC_TM -->|"3. auto-split multipart & parallel put"| S3_Dest[(Service Account S3 Bucket)]

  %% 검증 (최대 1회 재시도)
  S3_SVC_TM --> CSUM_VAL
  CSUM_VAL -.->|"if mismatch & retry_count < 1\n→ 1회 재전송"| S3_ML_READER
  CSUM_VAL -.->|"if mismatch & retry_count ≥ 1\n→ Task FAILED"| TASK_FAIL([ECS Task Exit Code 1])
  CSUM_VAL -->|"if match → Task SUCCEEDED"| TASK_OUT([Process Result])

  %% 스타일 적용
  classDef comp fill:#cff,stroke:#333,stroke-width:2px;
  class STS_CLIENT,S3_ML_READER,S3_SVC_TM,CSUM_VAL comp;
```

### Component Details
1. **Environment Variables**: `SERVICE_ACCOUNT_ROLE_ARN`과 같은 Cross-Account Role ARN(비암호화 구성값)을 저장하고 주입하여 불필요한 Secrets Manager 호출 비용을 줄입니다.
2. **STS AssumeRole Client**: ECS Fargate Task의 Task Role을 사용하여 AWS STS에 `AssumeRole`을 호출, Service Account의 S3 쓰기 역할에 대한 제한된 수명을 가진 임시 접속 자격증명(S3 PutObject)을 취득합니다. 동일 AWS 내이므로 GCP의 WIF(Workload Identity Federation) 대신 표준 IAM Cross-Account AssumeRole을 사용하여 인증 체인이 크게 단순화됩니다. (STS 세션 토큰 재사용 포함)
3. **S3 ML Account Reader**: ML Account S3 bucket에서 모델 아티팩트 또는 추론 결과를 스트리밍 읽기합니다. ECS Task Role에 ML Account S3 읽기 권한이 직접 부여되어 있으므로 별도의 AssumeRole이 불필요합니다.
4. **S3 Transfer Manager**: 객체 크기에 따른 Multipart 분할, 병렬 스레드 풀 관리 책임을 애플리케이션 코드가 아닌 AWS 공식 SDK(`boto3 S3 Transfer` 등)의 관리형 인프라에 위임(통폐합)한 컴포넌트입니다. Service Account S3 bucket에 업로드합니다.
5. **Multipart-Aware Checksum Validator**: AWS SDK의 Native Checksum 기능(`ChecksumAlgorithm='SHA256'` 등)을 활용하여 S3 멀티파트 업로드 시 파일의 병합 해시 무결성을 안전하고 정확하게 검증합니다. Checksum 불일치 시 **최대 1회 재전송**을 시도하며, 재전송 후에도 불일치하면 즉시 ECS Task Exit Code 1(FAILED)을 반환하여 무한 루프를 방지합니다.
