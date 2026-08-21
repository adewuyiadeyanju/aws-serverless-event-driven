output "lambda_function_name" {
  description = "Operational event Lambda function name"
  value       = aws_lambda_function.operational_event_handler.function_name
}

output "lambda_function_arn" {
  description = "Operational event Lambda function ARN"
  value       = aws_lambda_function.operational_event_handler.arn
}

output "dynamodb_table_name" {
  description = "Operational events DynamoDB table name"
  value       = aws_dynamodb_table.operational_events.name
}