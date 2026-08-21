data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/../application/build"
  output_path = "${path.module}/lambda_package.zip"
}

resource "aws_lambda_function" "operational_event_handler" {
  function_name = "${var.project_name}-${var.environment}-event-handler"

  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256

  role = aws_iam_role.lambda_execution.arn

  handler = "handler.handler"
  runtime = "python3.12"

  timeout     = 10
  memory_size = 256

  environment {
    variables = {
      EVENT_TABLE_NAME = aws_dynamodb_table.operational_events.name
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}