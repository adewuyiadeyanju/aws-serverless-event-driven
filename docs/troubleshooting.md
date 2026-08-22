# Troubleshooting Guide

## Overview

This document captures common issues encountered while developing and deploying the serverless event-driven application.

The troubleshooting approach follows the event path:

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

When an issue occurs, identify the first stage at which the expected behavior stops.

---

# 1. Lambda Import Error: `No module named 'pydantic'`

## Symptom

The Lambda invocation returns:

```json
{
  "errorMessage": "Unable to import module 'handler': No module named 'pydantic'"
}
```

## Cause

The Lambda deployment package did not contain the Python dependency required by the application.

The local virtual environment may contain Pydantic while the Lambda ZIP does not.

## Resolution

Rebuild the Lambda deployment directory with the required dependencies.

Verify:

```powershell
Get-ChildItem applicationuild
```

The build directory should contain packages such as:

```text
pydantic/
pydantic_core/
boto3/
```

Repackage and redeploy with Terraform.

---

# 2. Lambda Import Error: `No module named 'pydantic_core._pydantic_core'`

## Symptom

Lambda reports:

```text
No module named 'pydantic_core._pydantic_core'
```

## Cause

`pydantic_core` contains compiled/native components. A dependency package built for the local operating system can be incompatible with the AWS Lambda runtime.

This can occur when dependencies are installed into the build directory on Windows and then packaged for a Linux Lambda runtime.

## Resolution

Build Lambda dependencies in an environment compatible with AWS Lambda, such as a Linux environment or container.

The important principle is:

```text
Development OS != Lambda execution OS
```

The deployment artifact must contain dependencies compatible with the Lambda runtime.

After rebuilding the package, run:

```powershell
terraform plan
terraform apply
```

Then invoke the Lambda again.

---

# 3. Lambda Invocation Returns `FunctionError: Unhandled`

## Symptom

The AWS CLI returns:

```json
{
    "StatusCode": 200,
    "FunctionError": "Unhandled"
}
```

## Diagnosis

The HTTP status from the Lambda invocation does not mean the Lambda function executed successfully.

Inspect the invocation response:

```powershell
Get-Content lambda-response.json
```

Look for:

```text
errorMessage
errorType
stackTrace
```

Also inspect CloudWatch logs.

---

# 4. API Gateway Returns HTTP 400

## Symptom

The API responds:

```text
HTTP/1.1 400 Bad Request
```

## Diagnosis

Inspect the response body.

For example, if the request is missing `site_id`, Pydantic validation reports:

```text
1 validation error for OperationalEvent
site_id
Field required
```

## Cause

The API request does not satisfy the `OperationalEvent` model.

The required fields are:

```text
site_id
event_type
severity
message
```

## Resolution

Send a complete payload:

```json
{
  "event_type": "equipment_alert",
  "site_id": "RIG-003",
  "severity": "medium",
  "message": "Equipment telemetry alert detected"
}
```

---

# 5. PowerShell `curl.exe` JSON Errors

## Symptom

A request constructed using escaped JSON can produce errors such as:

```text
Expecting property name enclosed in double quotes
```

or:

```text
curl: (6) Could not resolve host
```

## Cause

PowerShell quoting and escaping can interact unexpectedly with `curl.exe`.

## Recommended Approach

Create the JSON payload as a file and send it using `--data-binary`.

Example:

```powershell
@"
{
  "event_type": "equipment_alert",
  "site_id": "RIG-003",
  "severity": "medium",
  "message": "Equipment telemetry alert detected"
}
"@ | ...
```

However, Windows PowerShell can write a UTF-8 BOM depending on the method used.

---

# 6. API Gateway Reports `Unexpected UTF-8 BOM`

## Symptom

The API returns:

```text
Unexpected UTF-8 BOM (decode using utf-8-sig)
```

## Cause

The request body begins with the UTF-8 byte-order mark:

```text
EF BB BF
```

The application expects standard UTF-8 JSON without the BOM.

## Diagnosis

Inspect the file:

```powershell
Format-Hex .\curl-test.json | Select-Object -First 2
```

If the first bytes are:

```text
EF BB BF
```

the file contains a BOM.

## Resolution

Generate the JSON file explicitly using UTF-8 without BOM.

For example, use Python:

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

Then send:

```powershell
curl.exe -i `
  -X POST `
  "https://57gu5fmekc.execute-api.eu-west-1.amazonaws.com/events" `
  -H "Content-Type: application/json" `
  --data-binary "@curl-test.json"
```

---

# 7. API Works but DynamoDB Does Not Contain the Event

## Diagnosis

First verify the Lambda invocation and then inspect the DynamoDB table:

```powershell
aws dynamodb scan `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1
```

If the API returns `201 Created` but the item is missing, investigate:

1. Lambda execution logs.
2. Lambda IAM permissions.
3. DynamoDB table name environment variable.
4. DynamoDB service availability.
5. Lambda execution role.

The Lambda requires:

```text
dynamodb:PutItem
```

against the operational events table.

---

# 8. DynamoDB Stream Is Not Processing Events

## Diagnosis

Confirm Streams are enabled:

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

Then inspect the stream processor logs:

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 5m
```

A successful invocation should show:

```text
Stream processor started
Processing DynamoDB Stream event: INSERT
New operational event
Stream processor completed
```

---

# 9. Stream Processor Lambda Exists but Receives No Records

Check that the Lambda event source mapping exists:

```powershell
aws lambda list-event-source-mappings `
  --function-name fieldops-serverless-dev-stream-processor `
  --region eu-west-1
```

Confirm that the mapping is enabled and associated with the DynamoDB Stream ARN.

Also verify that new records are actually being inserted after the stream processor was deployed.

---

# 10. Terraform Duplicate Resource Error

## Symptom

Terraform reports:

```text
Error: Duplicate resource "aws_iam_role" configuration
```

or:

```text
Error: Duplicate resource "aws_iam_role_policy" configuration
```

## Cause

The same Terraform resource name has been declared in more than one `.tf` file.

For example:

```text
iam.tf
stream_lambda.tf
```

cannot both declare:

```hcl
resource "aws_iam_role" "stream_processor" {
```

Terraform treats all `.tf` files in the same directory as one module.

## Resolution

Keep a resource declaration in only one location.

A clean organization is:

```text
terraform/
├── iam.tf
├── lambda.tf
├── stream_lambda.tf
└── ...
```

Use `iam.tf` for IAM resources and `stream_lambda.tf` for the Lambda and event-source mapping.

---

# 11. Terraform Plan Shows Unexpected Changes

Always run:

```powershell
terraform plan
```

before:

```powershell
terraform apply
```

Check for:

```text
+ create
~ change
- destroy
```

A `- destroy` or replacement of an important resource deserves investigation before applying.

Use:

```powershell
terraform state list
```

to understand what Terraform currently manages.

---

# 12. Lambda Package Changes Are Not Reflected

Terraform uses the package hash:

```hcl
source_code_hash = data.archive_file.lambda_package.output_base64sha256
```

If application code changes but the build directory does not, Terraform may package stale code.

Verify:

```powershell
Get-ChildItem applicationuild
```

Then regenerate the build and run:

```powershell
terraform plan
```

The Lambda source code hash should change when the deployment package changes.

---

# 13. CloudWatch Logs

Operational Lambda logs:

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-event-handler" `
  --region eu-west-1 `
  --since 10m
```

Stream processor logs:

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 10m
```

CloudWatch logs are the primary runtime diagnostic source for this project.

---

# 14. End-to-End Diagnostic Procedure

When the complete system appears not to be working, validate each layer in order.

## Step 1 — API Gateway

Send a valid request.

Expected:

```text
HTTP 201 Created
```

## Step 2 — Operational Lambda

Check its CloudWatch logs.

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

This provides a clear troubleshooting boundary between the synchronous API path and the asynchronous event-processing path.

---

# Lessons Learned

Several practical issues encountered during implementation demonstrate real-world cloud engineering concerns:

1. Dependencies must be packaged for the target Lambda runtime, not merely for the local development OS.
2. Serverless API validation should reject malformed requests early.
3. Windows PowerShell JSON handling can introduce encoding and quoting problems.
4. Terraform resources share a module namespace across all `.tf` files.
5. DynamoDB Streams provide a decoupled asynchronous processing mechanism.
6. CloudWatch logs are essential for diagnosing serverless execution.
7. Infrastructure changes should always be reviewed with `terraform plan` before applying.

These lessons are intentionally retained as part of the project because they demonstrate practical implementation and troubleshooting experience rather than only a theoretical architecture.
