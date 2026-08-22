resource "aws_lambda_event_source_mapping" "dynamodb_stream" {
  event_source_arn  = aws_dynamodb_table.operational_events.stream_arn
  function_name     = aws_lambda_function.stream_processor.arn
  starting_position = "LATEST"

  batch_size = 10

  enabled = true

  depends_on = [
    aws_iam_role_policy.stream_processor
  ]
}