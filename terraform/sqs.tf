resource "aws_sqs_queue" "operational_alerts" {
  name = "${var.project_name}-${var.environment}-operational-alerts"

  visibility_timeout_seconds = 30

  message_retention_seconds = 86400

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}


resource "aws_sns_topic_subscription" "operational_alerts_sqs" {
  topic_arn = aws_sns_topic.operational_alerts.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.operational_alerts.arn
}


resource "aws_sqs_queue_policy" "operational_alerts" {
  queue_url = aws_sqs_queue.operational_alerts.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "AllowSNSToSendMessage"
        Effect = "Allow"

        Principal = {
          Service = "sns.amazonaws.com"
        }

        Action = "sqs:SendMessage"

        Resource = aws_sqs_queue.operational_alerts.arn

        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_sns_topic.operational_alerts.arn
          }
        }
      }
    ]
  })
}
