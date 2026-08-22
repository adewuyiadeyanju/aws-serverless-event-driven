# Troubleshooting Guide

## Overview

This guide covers the issues encountered while developing and deploying the AWS serverless event-driven application.

Use the event path to locate the first failed stage:

```text
Client
  ↓
API Gateway
  ↓
Operational Lambda
  ↓
DynamoDB
  ↓
DynamoDB Stream
  ↓
Stream Processor Lambda
  ↓
CloudWatch Logs
```

The troubleshooting principle is simple:

> Find the first point where the expected behavior stops, then diagnose that layer before changing downstream components.

---

# 1. Lambda Import Error: `No module named 'pydantic'`

## Symptom

Lambda returns:

```json
{
  "errorMessage": "Unable to import module 'handler': No module named 'pydantic'"
}
```

## Cause

The local virtual environment contains Pydantic, but the Lambda deployment package does not.

## Resolution

Verify the deployment build:

```powershell
Get-ChildItem application/build
```

It should contain packages such as:

```text
pydantic/
pydantic_core/
boto3/
```

Rebuild the Lambda package and redeploy:

```powershell
terraform plan
terraform apply
```

Then invoke Lambda again.

---

# 2. Lambda Import Error: `No module named 'pydantic_core._pydantic_core'`

## Symptom

Lambda reports:

```text
No module named 'pydantic_core._pydantic_core'
```

## Cause

`pydantic_core` contains compiled/native components.

A dependency installed on Windows can be incompatible with the Linux environment used by AWS Lambda.

This was an actual deployment issue encountered during this project.

## Key Principle

```text
Development OS != Lambda execution OS
```

## Resolution

Build dependencies in an environment compatible with the Lambda runtime, for example:

- Linux/WSL
- Docker
- A Lambda-compatible build image

Then regenerate:

```text
application/build/
```

and redeploy.

Do not assume that a package working inside `.venv` will work inside Lambda.

---

# 3. Lambda Invocation Shows `FunctionError: Unhandled`

## Symptom

AWS CLI returns:

```json
{
    "StatusCode": 200,
    "FunctionError": "Unhandled"
}
```

## Important

`StatusCode: 200` from `aws lambda invoke` does not mean the Lambda function completed successfully.

Inspect:

```powershell
Get-Content lambda-response.json
```

Look for:

```text
errorMessage
errorType
stackTrace
```

Also inspect CloudWatch:

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-event-handler" `
  --region eu-west-1 `
  --since 10m
```

---

# 4. API Gateway Returns HTTP 400

## Symptom

The API returns:

```text
HTTP/1.1 400 Bad Request
```

Inspect the response body.

For example:

```text
1 validation error for OperationalEvent
site_id
Field required
```

## Cause

The request does not satisfy the Pydantic `OperationalEvent` model.

Required fields:

```text
site_id
event_type
severity
message
```

## Valid Example

```json
{
  "event_type": "equipment_alert",
  "site_id": "RIG-003",
  "severity": "medium",
  "message": "Equipment telemetry alert detected"
}
```

---

# 5. PowerShell `curl.exe` JSON Quoting Errors

## Symptom

A request can produce:

```text
Expecting property name enclosed in double quotes
```

and additional `curl` URL/host parsing errors.

## Cause

PowerShell quoting and escaping can interact unexpectedly with `curl.exe`.

## Recommended Approach

For PowerShell API testing, the most reliable option is usually:

```powershell
$body = @{
    event_type = "equipment_alert"
    site_id    = "RIG-003"
    severity   = "medium"
    message    = "Equipment telemetry alert detected"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "https://57gu5fmekc.execute-api.eu-west-1.amazonaws.com/events" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

---

# 6. API Gateway Reports `Unexpected UTF-8 BOM`

## Symptom

The API returns:

```text
Unexpected UTF-8 BOM (decode using utf-8-sig)
```

## Cause

The request file begins with a UTF-8 byte-order mark.

The BOM bytes are:

```text
EF BB BF
```

## Diagnosis

```powershell
Format-Hex .\curl-test.json | Select-Object -First 2
```

If the first bytes are:

```text
EF BB BF
```

the file contains a BOM.

## Resolution

Generate the file as UTF-8 without BOM.

A reliable Windows approach is to use Python:

```powershell
@"
from pathlib import Path

payload = '{"event_type":"equipment_alert","site_id":"RIG-003","severity":"medium","message":"Equipment telemetry alert detected"}'

Path("curl-test.json").write_text(payload, encoding="utf-8")
"@ | Set-Content create_test_payload.py
```

Run:

```powershell
python create_test_payload.py
```

Verify:

```powershell
Format-Hex .\curl-test.json | Select-Object -First 2
```

The first byte should be:

```text
7B
```

which represents `{`.

Then:

```powershell
curl.exe -i `
  -X POST `
  "https://57gu5fmekc.execute-api.eu-west-1.amazonaws.com/events" `
  -H "Content-Type: application/json" `
  --data-binary "@curl-test.json"
```

Expected:

```text
HTTP/1.1 201 Created
```

Temporary test files such as `curl-test.json` and `create_test_payload.py` should normally be removed after testing or added to `.gitignore` if they are intentionally retained as local tooling.

---

# 7. API Works but DynamoDB Does Not Contain the Event

## Diagnosis

First verify the API response.

Then:

```powershell
aws dynamodb scan `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1
```

If the API returns `201 Created` but the item is missing, investigate:

1. Operational Lambda logs.
2. Lambda IAM permissions.
3. `EVENT_TABLE_NAME` environment variable.
4. DynamoDB table name.
5. Lambda execution role.

The ingestion Lambda requires:

```text
dynamodb:PutItem
```

against the operational events table.

---

# 8. DynamoDB Stream Is Not Processing Events

## Diagnosis

Confirm Streams:

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

Then inspect:

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 5m
```

Expected:

```text
Stream processor started
Processing DynamoDB Stream event: INSERT
New operational event
Stream processor completed
```

---

# 9. Stream Processor Lambda Exists but Receives No Records

Check:

### A. DynamoDB Stream

```powershell
aws dynamodb describe-table `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1 `
  --query "Table.StreamSpecification"
```

### B. Recent table activity

```powershell
aws dynamodb scan `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1
```

### C. Stream processor logs

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 10m
```

### D. Terraform configuration

Check that the event source mapping references the correct:

- Stream ARN.
- Stream processor Lambda.
- Starting position.
- Enabled state.

---

# 10. Terraform Duplicate Resource Error

## Symptom

Terraform reports:

```text
Error: Duplicate resource "aws_iam_role" configuration
```

## Cause

Terraform treats all `.tf` files in a module as one configuration namespace.

For example, the following cannot be declared twice:

```hcl
resource "aws_iam_role" "stream_processor" {
}
```

even if the declarations are in different files.

## Resolution

Search the Terraform directory for duplicate resource names and keep a single definition.

This issue occurred during the development of the stream processor and was resolved by consolidating the IAM definitions.

---

# 11. Lambda Package Changes Are Not Reflected

Terraform uses:

```hcl
source_code_hash = data.archive_file.lambda_package.output_base64sha256
```

If application source changes but `application/build` is not rebuilt, Terraform may package stale code.

Check:

```powershell
Get-ChildItem application/build
```

Then rebuild the deployment package and run:

```powershell
terraform plan
```

A changed deployment package should result in an updated source hash and Lambda update.

---

# 12. CloudWatch Logs

Operational Lambda:

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-event-handler" `
  --region eu-west-1 `
  --since 10m
```

Stream processor:

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 10m
```

CloudWatch Logs are the primary runtime diagnostic source for this baseline.

---

# 13. End-to-End Diagnostic Procedure

When the complete system appears not to work, validate each layer in order.

## Step 1 — API Gateway

Send a valid request.

Expected:

```text
HTTP 201 Created
```

## Step 2 — Operational Lambda

Check CloudWatch.

Expected:

```text
Successful invocation
```

## Step 3 — DynamoDB

Run:

```powershell
aws dynamodb scan `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1
```

Expected:

```text
New event exists
```

## Step 4 — DynamoDB Stream

Confirm:

```text
StreamEnabled = true
```

## Step 5 — Stream Processor

Inspect:

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 5m
```

Expected:

```text
Records received: 1
Processing DynamoDB Stream event: INSERT
Processed records: 1
```

This establishes a clear troubleshooting boundary between the synchronous ingestion path and asynchronous processing path.

---

# Lessons Learned

The implementation produced several practical cloud-engineering lessons:

1. Dependencies must be packaged for the target Lambda runtime, not merely the local development OS.
2. Input validation should happen before persistence.
3. Windows PowerShell can introduce JSON quoting and encoding problems.
4. Terraform resources share a module namespace across all `.tf` files.
5. DynamoDB Streams provide a decoupled asynchronous processing mechanism.
6. CloudWatch Logs are essential for serverless runtime diagnosis.
7. `terraform plan` should be reviewed before `terraform apply`.
8. Deployment artifacts should be separated from source-controlled application code.
9. A successful API response does not by itself prove downstream event processing.
10. End-to-end validation must verify persistence and asynchronous processing separately.

These lessons are intentionally retained as part of the portfolio because they demonstrate practical implementation and troubleshooting experience, not only theoretical architecture.
