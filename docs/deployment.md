# Deployment Guide

## Overview

This project is deployed as an AWS serverless, event-driven application using Terraform.

The current development environment is deployed in:

```text
eu-west-1
```

Terraform provisions the validated baseline:

- Amazon API Gateway HTTP API
- Operational event ingestion Lambda
- DynamoDB operational events table
- DynamoDB Streams
- Stream processor Lambda
- IAM roles and policies
- CloudWatch logging
- Supporting Terraform resources

Some Terraform files such as `eventbridge.tf` and `s3.tf` exist as part of the project structure, but the currently validated end-to-end runtime path is API Gateway → Lambda → DynamoDB → DynamoDB Streams → Lambda → CloudWatch.

## Prerequisites

Install:

- Python 3.12
- AWS CLI
- Terraform
- Git

Verify:

```powershell
python --version
aws --version
terraform version
git --version
```

Verify AWS credentials:

```powershell
aws sts get-caller-identity
```

The AWS identity must have sufficient permissions to provision the required development resources.

## 1. Clone the Repository

```powershell
git clone <repository-url>
cd aws-serverless-event-driven
```

## 2. Create the Python Virtual Environment

```powershell
python -m venv .venv
```

Activate it in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Confirm the prompt shows:

```text
(.venv)
```

Install the project's development dependencies according to the repository dependency configuration.

## 3. Run Unit Tests

Run:

```powershell
python -m pytest application/tests
```

The validated baseline produced:

```text
1 passed
```

Do not deploy while the test suite is failing.

## 4. Build the Lambda Deployment Package

The Terraform configuration packages:

```text
application/build/
```

using the `archive_file` data source:

```hcl
data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/../application/build"
  output_path = "${path.module}/lambda_package.zip"
}
```

The build directory must contain Lambda-compatible dependencies, including the Pydantic runtime dependencies.

### Important

The local development environment is Windows, while AWS Lambda runs on Linux.

Compiled dependencies such as `pydantic_core` must therefore be built for a Lambda-compatible Linux/Python environment.

A Windows-built package can produce errors such as:

```text
No module named 'pydantic_core._pydantic_core'
```

The deployment artifact `lambda_package.zip` should normally remain untracked.

## 5. Initialize Terraform

```powershell
cd terraform
terraform init
```

## 6. Validate Terraform

```powershell
terraform validate
```

Expected:

```text
Success! The configuration is valid.
```

## 7. Review the Terraform Plan

```powershell
terraform plan
```

Review the proposed changes and confirm there are no unexpected destructive actions.

## 8. Deploy

```powershell
terraform apply
```

Review the plan and enter:

```text
yes
```

Terraform will provision or update the development infrastructure.

## 9. Review Outputs

```powershell
terraform output
```

Relevant outputs include:

```text
api_endpoint
dynamodb_table_name
dynamodb_stream_arn
lambda_function_arn
lambda_function_name
stream_processor_lambda_arn
stream_processor_lambda_name
```

The validated development environment used:

```text
api_endpoint = "https://57gu5fmekc.execute-api.eu-west-1.amazonaws.com"
dynamodb_table_name = "fieldops-serverless-dev-events"
lambda_function_name = "fieldops-serverless-dev-event-handler"
stream_processor_lambda_name = "fieldops-serverless-dev-stream-processor"
```

## 10. Validate DynamoDB Streams

```powershell
aws dynamodb describe-table `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1 `
  --query "Table.StreamSpecification"
```

Expected:

```json
{
    "StreamEnabled": true,
    "StreamViewType": "NEW_AND_OLD_IMAGES"
}
```

Retrieve the ARN:

```powershell
aws dynamodb describe-table `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1 `
  --query "Table.LatestStreamArn"
```

## 11. Test the API

Use PowerShell:

```powershell
$body = @{
    event_type = "connectivity_degradation"
    site_id    = "RIG-005"
    severity   = "high"
    message    = "Primary connectivity latency exceeded operational threshold"
} | ConvertTo-Json
```

Then:

```powershell
Invoke-RestMethod `
  -Uri "https://57gu5fmekc.execute-api.eu-west-1.amazonaws.com/events" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

Expected:

```text
event_id                             status
--------                             ------
<uuid>                               created
```

## 12. Validate Persistence

```powershell
aws dynamodb scan `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1
```

The newly submitted event should appear in the table.

## 13. Validate Stream Processing

The stream processor is triggered asynchronously after a DynamoDB `INSERT`.

View logs:

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 5m
```

A successful invocation should contain:

```text
Stream processor started. Records received: 1
Processing DynamoDB Stream event: INSERT
New operational event: ...
Stream processor completed. Processed records: 1
```

## 14. End-to-End Validation Path

```text
HTTP Request
     |
     v
API Gateway
     |
     v
Operational Lambda
     |
     v
DynamoDB
     |
     v
DynamoDB Stream
     |
     v
Stream Processor Lambda
     |
     v
CloudWatch Logs
```

## 15. Updating the Application

When application code changes:

1. Run unit tests.
2. Rebuild `application/build`.
3. Run `terraform plan`.
4. Confirm the Lambda source hash changes when expected.
5. Run `terraform apply`.
6. Invoke the API.
7. Validate DynamoDB.
8. Validate stream processing.
9. Review CloudWatch logs.
10. Commit the tested change.

Example:

```powershell
cd ..
python -m pytest application/tests

cd terraform
terraform plan
terraform apply
```

## 16. Destroy Development Resources

For a disposable development environment:

```powershell
terraform destroy
```

Review the resources carefully before confirming.

Never run `terraform destroy` against shared or production infrastructure without an explicit change-management decision.

## Deployment Principle

The deployment workflow is:

```text
Code
  ↓
Unit Tests
  ↓
Build Lambda Dependencies
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
DynamoDB Stream Validation
  ↓
Stream Processor Validation
  ↓
CloudWatch Validation
```

The objective is reproducible Infrastructure as Code rather than manually configured AWS resources.
