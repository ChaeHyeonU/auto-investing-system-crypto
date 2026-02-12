locals {
  project_name = var.project_name
  environment  = var.environment
  common_tags = {
    project     = local.project_name
    environment = local.environment
    managed_by  = "terraform"
  }
}

# TODO: Sprint 2
# - 네트워크(VPC/VNet)
# - 애플리케이션 런타임(ECS/Kubernetes/Serverless)
# - 데이터 계층(Managed PostgreSQL/Redis)
# - 시크릿 매니저 및 KMS

