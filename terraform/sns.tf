resource "aws_sns_topic" "operational_alerts" {
  name = "${var.project_name}-${var.environment}-operational-alerts"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}