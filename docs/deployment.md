# Deployment Guide

## Overview

This project is deployed as an AWS serverless, event-driven application using Terraform.

The deployment provisions:

- Amazon API Gateway HTTP API
- AWS Lambda operational event handler
- Amazon DynamoDB operational events table
- DynamoDB Streams
- AWS Lambda stream processor
- IAM execution roles and policies
- CloudWatch logging
- Supporting Terraform configuration

The AWS region used for the development environment is `eu-west-1`.

---

## Prerequisites

Ensure the following are installed and configured locally:

- Python 3.12
- AWS CLI
- Terraform
- Git
- A configured AWS identity with permission to provision the required resources

Verify the tools:

```powershell
python --version
aws --version
terraform version
git --version
```

Verify the AWS identity:

```powershell
aws sts get-caller-identity
```

---

## 1. Clone the Repository

```powershell
git clone <repository-url>
cd aws-serverless-event-driven
```

---

## 2. Create the Python Virtual Environment

Create the project virtual environment:

```powershell
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

The shell should show:

```text
(.venv)
```

Install the development dependencies required by the project.

---

## 3. Run Unit Tests

Run the application tests before deploying:

```powershell
python -m pytest application	ests
```

The baseline implementation was validated with:

```text
1 passed
```

Do not proceed with deployment if the application test suite is failing.

---

## 4. Build the Lambda Package

The Lambda deployment package is assembled under:

```text
application/build/
```

The package contains the Lambda handler, models, and required Python dependencies.

The Terraform configuration packages this directory using the `archive_file` data source:

```hcl
data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/../application/build"
  output_path = "${path.module}/lambda_package.zip"
}
```

The generated ZIP file is a deployment artifact and should not normally be committed to Git.

---

## 5. Initialize Terraform

Change to the Terraform directory:

```powershell
cd terraform
```

Initialize Terraform:

```powershell
terraform init
```

This downloads the required providers and initializes the Terraform working directory.

---

## 6. Validate Terraform

Run:

```powershell
terraform validate
```

Expected result:

```text
Success! The configuration is valid.
```

---

## 7. Review the Deployment Plan

Run:

```powershell
terraform plan
```

Review the resources carefully before applying.

The plan should show the serverless infrastructure being created or updated without unexpected destructive changes.

---

## 8. Deploy the Infrastructure

Apply the configuration:

```powershell
terraform apply
```

Review the proposed changes and enter:

```text
yes
```

Terraform will provision the infrastructure.

The project exposes outputs including:

- API endpoint
- DynamoDB table name
- DynamoDB Stream ARN
- Operational Lambda ARN
- Stream processor Lambda ARN

Example outputs from the development environment:

```text
api_endpoint = "https://57gu5fmekc.execute-api.eu-west-1.amazonaws.com"
dynamodb_table_name = "fieldops-serverless-dev-events"
lambda_function_name = "fieldops-serverless-dev-event-handler"
stream_processor_lambda_name = "fieldops-serverless-dev-stream-processor"
```

---

## 9. Validate DynamoDB Streams

Confirm that the DynamoDB table has Streams enabled:

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

Retrieve the stream ARN:

```powershell
aws dynamodb describe-table `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1 `
  --query "Table.LatestStreamArn"
```

---

## 10. Test the API

Use PowerShell to construct the request body:

```powershell
$body = @{
    event_type = "connectivity_degradation"
    site_id    = "RIG-005"
    severity   = "high"
    message    = "Primary connectivity latency exceeded operational threshold"
} | ConvertTo-Json
```

Send the request:

```powershell
Invoke-RestMethod `
  -Uri "https://57gu5fmekc.execute-api.eu-west-1.amazonaws.com/events" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

Expected response:

```text
event_id                             status
--------                             ------
<uuid>                               created
```

---

## 11. Validate the DynamoDB Record

Query the table:

```powershell
aws dynamodb scan `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1
```

The newly submitted event should appear in the table.

---

## 12. Validate Stream Processing

The stream processor is triggered by DynamoDB Streams when a new event is inserted.

View recent logs:

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 5m
```

A successful invocation should contain messages similar to:

```text
Stream processor started. Records received: 1
Processing DynamoDB Stream event: INSERT
New operational event: ...
Stream processor completed. Processed records: 1
```

This validates the end-to-end flow:

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

---

## 13. Terraform Outputs

At any time, retrieve the deployed outputs with:

```powershell
terraform output
```

For an individual output:

```powershell
terraform output api_endpoint
terraform output dynamodb_table_name
terraform output lambda_function_name
terraform output stream_processor_lambda_name
```

---

## 14. Updating the Application

When application code changes:

1. Run unit tests.
2. Rebuild `application/build`.
3. Run `terraform plan`.
4. Review the Lambda source hash and infrastructure changes.
5. Run `terraform apply`.
6. Invoke the API.
7. Validate DynamoDB.
8. Validate stream processor CloudWatch logs.
9. Commit the tested changes.

Example:

```powershell
python -m pytest application	ests
cd terraform
terraform plan
terraform apply
```

---

## 15. Destroying the Development Environment

For a disposable development environment:

```powershell
terraform destroy
```

Review the resources Terraform proposes to remove before confirming.

Do not run `terraform destroy` against a shared or production environment without an explicit change-management decision.

---

## Deployment Principle

The project uses Infrastructure as Code so that the complete serverless architecture can be reproduced consistently rather than relying on manually configured AWS resources.

The deployment workflow is therefore:

```text
Code
  ↓
Unit Tests
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
Stream Processing Validation
  ↓
CloudWatch Validation
```
