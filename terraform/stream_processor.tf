data "archive_file" "stream_processor_package" {
  type = "zip"

  source_dir = "${path.module}/../application/build"

  output_path = "${path.module}/stream_processor_package.zip"
}


resource "aws_lambda_function" "stream_processor" {
  function_name = "${var.project_name}-${var.environment}-stream-processor"

  filename         = data.archive_file.stream_processor_package.output_path
  source_code_hash = data.archive_file.stream_processor_package.output_base64sha256

  role = aws_iam_role.stream_processor.arn

  handler = "stream_handler.handler"
  runtime = "python3.12"

  timeout     = 30
  memory_size = 256

  environment {
    variables = {
      PROCESSOR_NAME = "${var.project_name}-${var.environment}-stream-processor"
      SNS_TOPIC_ARN  = aws_sns_topic.operational_alerts.arn
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}