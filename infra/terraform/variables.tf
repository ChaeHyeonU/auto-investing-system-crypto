variable "project_name" {
  type        = string
  description = "Project name"
  default     = "auto-investing-system-crypto"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
  default     = "dev"
}

variable "region" {
  type        = string
  description = "Cloud region"
  default     = "us-east-1"
}

