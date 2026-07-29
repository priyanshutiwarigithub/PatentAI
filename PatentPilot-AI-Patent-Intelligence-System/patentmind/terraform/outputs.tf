output "s3_bucket_name" {
  description = "S3 bucket name for patent storage"
  value       = aws_s3_bucket.patent_storage.bucket
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.patent_storage.arn
}

output "rds_endpoint" {
  description = "PostgreSQL RDS connection endpoint"
  value       = aws_db_instance.postgres.endpoint
}
