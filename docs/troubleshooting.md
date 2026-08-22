# Troubleshooting Guide

## Diagnostic Path

``` text
Client → API Gateway → Ingestion Lambda → DynamoDB
                                      ↓
                               DynamoDB Stream
                                      ↓
                              Stream Processor
                                 ↓        ↓
                               SNS     CloudWatch
                                 ↓
                                SQS
```

Always find the first failed layer before changing downstream
components.

## 1. Pydantic Import Error

### Symptom

``` text
No module named 'pydantic'
```

### Cause

Pydantic is present locally but missing from the Lambda package.

### Fix

Rebuild `application/build` with dependencies and redeploy.

## 2. `pydantic_core._pydantic_core` Import Error

### Cause

`pydantic_core` contains native code. A Windows-built dependency may not
be compatible with Lambda's Linux runtime.

This was an actual issue encountered during deployment.

### Principle

``` text
Development OS != Lambda execution OS
```

Build dependencies using WSL/Linux, Docker, or a Lambda-compatible build
environment.

## 3. Lambda `FunctionError: Unhandled`

`aws lambda invoke` may show HTTP status 200 while the function itself
failed.

Inspect:

``` powershell
Get-Content lambda-response.json
```

Then:

``` powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-event-handler" `
  --region eu-west-1 `
  --since 10m
```

Look for `errorMessage`, `errorType`, and `stackTrace`.

## 4. API HTTP 400

Check the Pydantic contract.

Required:

``` text
site_id
event_type
severity
message
```

Severity:

``` text
low
medium
high
critical
```

## 5. PowerShell JSON Problems

Prefer `Invoke-RestMethod` with `ConvertTo-Json`:

``` powershell
$body = @{
    site_id    = "RIG-006"
    event_type = "connectivity_degradation"
    severity   = "high"
    message    = "LEO connectivity latency exceeded operational threshold"
} | ConvertTo-Json
```

Then submit with `Invoke-RestMethod`.

## 6. DynamoDB Is Empty

Check:

``` powershell
aws dynamodb scan `
  --table-name "$(terraform output -raw dynamodb_table_name)" `
  --region eu-west-1
```

Then inspect:

1.  Ingestion Lambda logs
2.  `EVENT_TABLE_NAME`
3.  IAM `dynamodb:PutItem`
4.  Table name
5.  Lambda execution role

## 7. DynamoDB Stream Not Processing

Check:

``` powershell
aws dynamodb describe-table `
  --table-name "$(terraform output -raw dynamodb_table_name)" `
  --region eu-west-1 `
  --query "Table.StreamSpecification"
```

Expected:

``` text
StreamEnabled = true
StreamViewType = NEW_AND_OLD_IMAGES
```

Then inspect the stream processor logs.

## 8. High/Critical Event Not Published to SNS

Check stream processor logs:

``` powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 10m
```

Verify:

-   `SNS_TOPIC_ARN`
-   SNS topic exists
-   Stream processor IAM has `sns:Publish`

Current behavior:

``` text
high     → SNS
critical → SNS
medium   → no priority notification
low      → no priority notification
```

## 9. SNS Has No SQS Subscription

Run:

``` powershell
aws sns list-subscriptions-by-topic `
  --topic-arn "$(terraform output -raw sns_topic_arn)" `
  --region eu-west-1
```

Expected:

``` text
Protocol: sqs
```

## 10. SNS Published but SQS Is Empty

Run:

``` powershell
aws sqs receive-message `
  --queue-url "$(terraform output -raw sqs_queue_url)" `
  --region eu-west-1 `
  --max-number-of-messages 10 `
  --wait-time-seconds 5
```

Check:

-   SNS subscription
-   SQS queue policy
-   Topic ARN
-   Queue URL
-   Whether a message has already been consumed
-   Visibility timeout

## 11. Terraform Duplicate Resource

All `.tf` files in a directory share one Terraform module namespace.

Do not define the same resource address twice, even in different files.

## 12. Lambda Package Changes Not Reflected

If source changes but `application/build` is not rebuilt, Terraform may
package stale code.

Check:

``` powershell
Get-ChildItem application/build
```

Then rebuild and run:

``` powershell
terraform plan
```

A changed package should produce a changed Lambda source hash.

## 13. CloudWatch Logs

Ingestion Lambda:

``` powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-event-handler" `
  --region eu-west-1 `
  --since 10m
```

Stream processor:

``` powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 10m
```

## Lessons Learned

1.  Native dependencies must be built for the Lambda runtime.
2.  Validate before persistence.
3.  PowerShell can introduce JSON quoting issues.
4.  Terraform has one module namespace.
5.  DynamoDB Streams provide a natural asynchronous boundary.
6.  SNS/SQS provide durable downstream decoupling.
7.  CloudWatch is essential for serverless diagnosis.
8.  `terraform plan` must be reviewed before `apply`.
9.  API success does not prove downstream success.
10. End-to-end validation must verify persistence and asynchronous
    delivery independently.
