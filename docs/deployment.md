# Deployment Guide

## Overview

The platform is deployed with Terraform in AWS region `eu-west-1`.

The deployment contains API Gateway, two Lambda functions, DynamoDB,
DynamoDB Streams, SNS, SQS, IAM policies, and CloudWatch logging.

## Prerequisites

-   Python 3.12
-   AWS CLI
-   Terraform
-   Git
-   AWS credentials with required permissions

``` powershell
aws sts get-caller-identity
```

## Test

From the repository root:

``` powershell
python -m pytest application/tests -v
```

Expected final result:

``` text
33 passed
```

## Lambda Packaging

Dependencies must be packaged for the AWS Lambda Linux runtime. This was
important because Pydantic's native `pydantic_core` can fail when
dependencies are built on Windows.

The build directory is:

``` text
application/build/
```

Terraform packages it using `archive_file`.

## Terraform

``` powershell
cd terraform
terraform init
terraform validate
terraform plan
terraform apply
```

Review the plan for unexpected destructive changes before applying.

## Outputs

``` powershell
terraform output
```

Important outputs include:

``` text
api_endpoint
dynamodb_table_name
dynamodb_stream_arn
lambda_function_name
stream_processor_lambda_name
sns_topic_arn
sqs_queue_name
sqs_queue_url
sqs_queue_arn
```

## API Test

``` powershell
$body = @{
    site_id    = "RIG-006"
    event_type = "connectivity_degradation"
    severity   = "high"
    message    = "LEO connectivity latency exceeded operational threshold"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "$(terraform output -raw api_endpoint)/events" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

Expected:

``` text
event_id                             status
--------                             ------
<uuid>                               created
```

## Validate Stream Processor

``` powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 5m
```

Expected for a high-severity event:

``` text
Processing DynamoDB Stream event: INSERT
Operational event notification published to SNS
Stream processor completed. Processed records: 1
```

## Validate SNS Subscription

``` powershell
aws sns list-subscriptions-by-topic `
  --topic-arn "$(terraform output -raw sns_topic_arn)" `
  --region eu-west-1
```

The subscription should use protocol `sqs`.

## Validate SQS

``` powershell
aws sqs receive-message `
  --queue-url "$(terraform output -raw sqs_queue_url)" `
  --region eu-west-1 `
  --max-number-of-messages 10 `
  --wait-time-seconds 5
```

For high/critical events, an SNS notification containing the operational
event should be received.

## Validate DynamoDB Streams

``` powershell
aws dynamodb describe-table `
  --table-name "$(terraform output -raw dynamodb_table_name)" `
  --region eu-west-1 `
  --query "Table.StreamSpecification"
```

Expected:

``` json
{
  "StreamEnabled": true,
  "StreamViewType": "NEW_AND_OLD_IMAGES"
}
```

## Updating the Application

After code changes:

``` powershell
python -m pytest application/tests -v
```

Rebuild `application/build`, then:

``` powershell
cd terraform
terraform plan
terraform apply
```

Validate API, DynamoDB, Streams, SNS, SQS, and CloudWatch logs.

## Deployment Principle

``` text
Code
 ↓
Tests
 ↓
Build
 ↓
Terraform Validate
 ↓
Terraform Plan
 ↓
Terraform Apply
 ↓
API Validation
 ↓
DynamoDB Validation
 ↓
Stream Validation
 ↓
SNS Validation
 ↓
SQS Validation
```

## Current Status

The development deployment is successfully applied and end-to-end
validated. Further observability and production-hardening work is
intentionally deferred.
