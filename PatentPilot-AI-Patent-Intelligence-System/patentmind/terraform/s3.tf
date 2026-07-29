resource "aws_s3_bucket" "patent_storage" {
  bucket        = var.s3_bucket_name
  force_destroy = false

  tags = {
    Name        = "PatentMind Storage"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "patent_versioning" {
  bucket = aws_s3_bucket.patent_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "patent_encryption" {
  bucket = aws_s3_bucket.patent_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
