# AWS Serverless Event-Driven Operational Events Platform

## Overview

A production-oriented AWS serverless and event-driven reference architecture for ingesting, validating, storing, and asynchronously processing operational events from distributed field environments.

The project demonstrates AWS Lambda, API Gateway, DynamoDB, DynamoDB Streams, Terraform, Python, Pydantic, IAM least privilege, and CloudWatch observability.

## Architecture

```text
Operational / Field System
          |
          | HTTPS POST /events
          v
   Amazon API Gateway
          |
          v
 Event Ingestion Lambda
          |
          | Validate + PutItem
          v
      DynamoDB
          |
          | DynamoDB Stream
          v
 Stream Processor Lambda
          |
          v
    CloudWatch Logs
```

The ingestion path is synchronous while downstream processing is asynchronous.

## Event Flow

1. Client sends an operational event to `POST /events`.
2. API Gateway forwards the request to Lambda.
3. Lambda validates the payload using Pydantic.
4. Lambda generates an event ID and UTC timestamp.
5. The event is stored in DynamoDB.
6. DynamoDB Streams captures the change.
7. The stream processor Lambda receives the stream record.
8. The processor logs the event and processing result.

## Example Event

```json
{
  "event_type": "connectivity_degradation",
  "site_id": "RIG-004",
  "severity": "high",
  "message": "LEO connectivity latency exceeded operational threshold"
}
```

## Project Structure

```text
aws-serverless-event-driven/
├── application/
│   ├── src/
│   │   ├── handler.py
│   │   ├── models.py
│   │   └── stream_handler.py
│   ├── tests/
│   │   └── test_handler.py
│   └── build/
├── architecture/
├── docs/
│   ├── architecture.md
│   ├── deployment.md
│   ├── troubleshooting.md
│   └── validation.md
└── terraform/
    ├── api_gateway.tf
    ├── cloudwatch.tf
    ├── dynamodb.tf
    ├── eventbridge.tf
    ├── iam.tf
    ├── lambda.tf
    ├── stream_lambda.tf
    ├── outputs.tf
    ├── providers.tf
    ├── s3.tf
    └── variables.tf
```

## AWS Resources

Terraform provisions an API Gateway HTTP API, two Lambda functions, DynamoDB, DynamoDB Streams, IAM roles/policies, and CloudWatch logging.

DynamoDB uses on-demand capacity and server-side encryption.

## Validation

The baseline has been validated end-to-end:

```powershell
python -m pytest application	ests
```

Result:

```text
1 passed
```

Terraform validation and deployment completed successfully.

A valid API request returned `HTTP/1.1 201 Created` and the event was confirmed in DynamoDB.

DynamoDB Streams was verified as enabled with `NEW_AND_OLD_IMAGES`.

CloudWatch logs confirmed the stream processor received an `INSERT` record and processed it successfully.

## Security

- Dedicated IAM roles for Lambda functions.
- Least-privilege DynamoDB permissions.
- HTTPS through API Gateway.
- Pydantic input validation.
- DynamoDB server-side encryption.
- CloudWatch logging.

## AWS Well-Architected Alignment

| Pillar | Baseline implementation |
|---|---|
| Operational Excellence | Terraform, documentation, CloudWatch logging |
| Security | IAM, least privilege, encryption, input validation |
| Reliability | Managed services and asynchronous processing |
| Performance Efficiency | Lambda and DynamoDB on-demand capacity |
| Cost Optimization | Serverless and pay-per-request services |
| Sustainability | Demand-based serverless execution |

## Real-Time Capability

The architecture supports **near-real-time event processing**. A DynamoDB write produces a stream record that invokes the downstream Lambda asynchronously.

It is a baseline event-driven platform rather than a high-throughput streaming platform such as Kafka or Kinesis.

## Future Enhancements

- EventBridge routing
- Dead-letter handling
- Retry and partial-batch failure handling
- Idempotency
- CloudWatch alarms
- API authentication and authorization
- X-Ray tracing
- Structured JSON logging
- CI/CD
- Security scanning
- Multi-environment Terraform
- Additional event consumers
