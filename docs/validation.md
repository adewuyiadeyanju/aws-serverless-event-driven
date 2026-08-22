# Validation

## Objective

This document records the validation evidence for the deployed AWS Serverless Event-Driven Operational Events Platform.

The goal is to demonstrate the complete baseline path:

```text
API Gateway
    ↓
Ingestion Lambda
    ↓
DynamoDB
    ↓
DynamoDB Stream
    ↓
Stream Processor Lambda
    ↓
CloudWatch Logs
```

## 1. Local Unit Tests

Run from the repository root:

```powershell
python -m pytest application/tests
```

Observed baseline result:

```text
1 passed
```

This confirms the local application test passes before deployment.

## 2. Terraform Validation

From the Terraform directory:

```powershell
cd terraform
terraform validate
terraform plan
```

Terraform validation completed successfully and the deployed environment was subsequently applied.

## 3. Deployed Resources

Validated development resources include:

```text
API Gateway:
https://57gu5fmekc.execute-api.eu-west-1.amazonaws.com

DynamoDB:
fieldops-serverless-dev-events

Ingestion Lambda:
fieldops-serverless-dev-event-handler

Stream Processor Lambda:
fieldops-serverless-dev-stream-processor
```

The DynamoDB Stream ARN was also successfully returned by Terraform and AWS CLI.

## 4. API Functional Validation

A valid event was submitted:

```json
{
  "event_type": "equipment_alert",
  "site_id": "RIG-003",
  "severity": "medium",
  "message": "Equipment telemetry alert detected"
}
```

The API returned:

```text
HTTP/1.1 201 Created
```

The response contained a generated UUID and:

```json
{
  "status": "created"
}
```

This confirms successful API Gateway → ingestion Lambda execution.

## 5. DynamoDB Persistence Validation

The table was checked with:

```powershell
aws dynamodb scan `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1
```

Multiple operational events were confirmed in DynamoDB, including:

- `connectivity_degradation`
- `equipment_alert`

The validated records included multiple rig/site identifiers.

This confirms successful persistence after API ingestion.

## 6. Input Validation

A request without `site_id` was submitted.

The application returned a Pydantic validation error:

```text
1 validation error for OperationalEvent
site_id
Field required
```

The DynamoDB record count remained unchanged.

This confirms that invalid input is rejected before persistence.

## 7. DynamoDB Stream Validation

The table configuration was checked:

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

The stream ARN was also confirmed with:

```powershell
aws dynamodb describe-table `
  --table-name fieldops-serverless-dev-events `
  --region eu-west-1 `
  --query "Table.LatestStreamArn"
```

This confirms that DynamoDB changes are available to downstream consumers.

## 8. Stream Processor Validation

CloudWatch Logs were inspected:

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

This is direct evidence that:

1. A DynamoDB item was inserted.
2. DynamoDB Streams captured the change.
3. The stream event source mapping invoked the stream processor Lambda.
4. The processor received an `INSERT`.
5. The processor processed the record successfully.

## 9. End-to-End Result

The validated path is:

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

## 10. Validation Evidence Summary

| Test | Result |
|---|---|
| Python unit tests | PASS |
| Terraform validation | PASS |
| Terraform deployment | PASS |
| Valid API request | PASS |
| HTTP 201 response | PASS |
| DynamoDB persistence | PASS |
| Invalid `site_id` rejected | PASS |
| DynamoDB Streams enabled | PASS |
| Stream `INSERT` received | PASS |
| Stream processor executed | PASS |
| CloudWatch processing logs | PASS |

## 11. Near-Real-Time Validation

The observed stream processor invocation occurred shortly after the DynamoDB insertion.

This demonstrates the architecture's **near-real-time asynchronous processing capability**.

It should not be described as a high-throughput streaming system equivalent to Kafka or Kinesis. The current implementation demonstrates event-driven processing using DynamoDB Streams and Lambda.

## 12. Runtime Observability

The following CloudWatch log groups are relevant:

```text
/aws/lambda/fieldops-serverless-dev-event-handler
/aws/lambda/fieldops-serverless-dev-stream-processor
```

Useful commands:

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-event-handler" `
  --region eu-west-1 `
  --since 10m
```

```powershell
aws logs tail `
  "/aws/lambda/fieldops-serverless-dev-stream-processor" `
  --region eu-west-1 `
  --since 10m
```

## 13. Baseline Limitations

The current implementation is a strong portfolio baseline, but it is not yet production-hardened.

Not yet validated:

- API authentication and authorization.
- API throttling.
- Retry and backoff behavior.
- Dead-letter handling.
- Idempotent stream processing.
- Partial batch failure handling.
- CloudWatch alarms.
- Distributed tracing.
- CI/CD.
- Automated security scanning.
- Multi-environment deployment.
- Load/performance testing.
- High-throughput streaming behavior.

These are deliberate future enhancement areas rather than gaps in the validated baseline.

## 14. Recommended Next Validation Stage

The next maturity step should focus on production engineering rather than adding unrelated services:

1. Implement idempotency.
2. Add retry/error handling.
3. Configure partial batch failure handling.
4. Add CloudWatch alarms and metrics.
5. Add API authentication.
6. Add CI/CD.
7. Add security scanning.
8. Add integration tests.
9. Perform controlled load testing.
