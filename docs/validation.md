# Validation

## Objective

This document records validation of the deployed AWS Serverless Event-Driven Operational Events Platform.

## Local Tests

Run:

```powershell
python -m pytest application	ests
```

Observed baseline result:

```text
1 passed
```

## Terraform

Run:

```powershell
cd terraform
terraform validate
terraform plan
terraform apply
```

Terraform deployment completed successfully.

## Deployed Resources

API endpoint:

```text
https://57gu5fmekc.execute-api.eu-west-1.amazonaws.com
```

DynamoDB table:

```text
fieldops-serverless-dev-events
```

Ingestion Lambda:

```text
fieldops-serverless-dev-event-handler
```

Stream processor Lambda:

```text
fieldops-serverless-dev-stream-processor
```

## API Validation

A valid request such as:

```json
{
  "event_type": "equipment_alert",
  "site_id": "RIG-003",
  "severity": "medium",
  "message": "Equipment telemetry alert detected"
}
```

returned:

```text
HTTP/1.1 201 Created
```

The response included a generated event ID and `created` status.

## Persistence Validation

Events were confirmed using:

```powershell
aws dynamodb scan `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1
```

The table contained successfully persisted events for multiple sites, including connectivity degradation and equipment alert events.

## Input Validation

A request without `site_id` was rejected with a Pydantic validation error:

```text
1 validation error for OperationalEvent
site_id
Field required
```

The DynamoDB count remained unchanged after the invalid request.

This demonstrates validation before persistence.

## DynamoDB Streams

Verify the stream with:

```powershell
aws dynamodb describe-table `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1 `
  --query "Table.StreamSpecification"
```

Observed:

```json
{
    "StreamEnabled": true,
    "StreamViewType": "NEW_AND_OLD_IMAGES"
}
```

## Stream Processor Validation

CloudWatch Logs were checked using:

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 5m
```

Observed:

```text
Stream processor started. Records received: 1
Processing DynamoDB Stream event: INSERT
New operational event: {...}
Stream processor completed. Processed records: 1
```

This confirms:

```text
DynamoDB INSERT
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

## End-to-End Result

The following path has been successfully demonstrated:

```text
HTTP Client
    |
    v
API Gateway
    |
    v
Ingestion Lambda
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

## Evidence

Validation evidence includes:

- Passing Python unit tests.
- Successful Terraform deployment.
- Successful API invocation.
- Successful request validation.
- Successful DynamoDB persistence.
- Enabled DynamoDB Streams.
- Successful stream-triggered Lambda invocation.
- CloudWatch processing logs.

## Baseline Limitations

The current implementation is a portfolio baseline rather than a production-hardened platform.

Future validation should cover:

- Authentication and authorization.
- API throttling.
- Retry behavior.
- Dead-letter destinations.
- Idempotent processing.
- Partial batch failure handling.
- CloudWatch alarms.
- Distributed tracing.
- CI/CD.
- Security scanning.
- Multi-environment deployment.
