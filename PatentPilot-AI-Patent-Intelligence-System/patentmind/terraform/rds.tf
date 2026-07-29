resource "aws_db_subnet_group" "patent_db_subnets" {
  name       = "patentmind-db-subnet-group"
  subnet_ids = ["subnet-0123456789abcdef0", "subnet-0fe23456789abcdef0"] # Placeholder subnet IDs

  tags = {
    Name = "PatentMind DB Subnet Group"
  }
}

resource "aws_security_group" "rds_sg" {
  name        = "patentmind-rds-sg"
  description = "Allow PostgreSQL access to RDS"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "postgres" {
  allocated_storage      = 20
  max_allocated_storage  = 100
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = "db.t4g.micro"
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  skip_final_snapshot    = true
  vpc_security_group_ids = [aws_security_group.rds_sg.id]

  tags = {
    Name = "PatentMind-PostgreSQL"
  }
}
