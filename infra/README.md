# Infra

인프라 디렉터리는 IaC(Terraform)와 로컬 개발용 데이터 스택(PostgreSQL/Redis)을 관리한다.

## Local stack
```bash
docker compose -f infra/docker-compose.yml up -d
```

## Terraform skeleton
```bash
cd infra/terraform
terraform init
terraform validate
```

현재 Terraform은 MVP 골격(변수/환경 구분)까지만 구성되어 있고, 실제 클라우드 리소스 모듈은 Sprint 2부터 추가하는 것을 권장한다.

