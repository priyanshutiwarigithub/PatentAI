variable "aws_region" {
  description = "AWS region for infrastructure deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for original patent PDFs"
  type        = string
  default     = "patentmind-patent-storage"
}

variable "db_name" {
  description = "PostgreSQL DB name"
  type        = string
  default     = "patentmind_db"
}

variable "db_username" {
  description = "PostgreSQL DB admin username"
  type        = string
  default     = "patentuser"
}

variable "db_password" {
  description = "PostgreSQL DB admin password"
  type        = string
  sensitive   = true
  default     = "patentpass123Secure!"
}
