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

output "api_endpoint" {
  description = "HTTP API endpoint"
  value       = aws_apigatewayv2_api.operational_events.api_endpoint
}

output "dynamodb_stream_arn" {
  description = "ARN of the DynamoDB stream for operational events"
  value       = aws_dynamodb_table.operational_events.stream_arn
}

output "stream_processor_lambda_arn" {
  description = "ARN of the DynamoDB stream processor Lambda"
  value       = aws_lambda_function.stream_processor.arn
}

output "stream_processor_lambda_name" {
  description = "Name of the DynamoDB stream processor Lambda"
  value       = aws_lambda_function.stream_processor.function_name
}