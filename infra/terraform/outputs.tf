output "project_context" {
  value = {
    project_name = var.project_name
    environment  = var.environment
    region       = var.region
  }
}

