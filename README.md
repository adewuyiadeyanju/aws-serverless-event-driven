# AWS Serverless Event-Driven Operational Events Platform

## Project Status

**Baseline implementation: completed and validated.**

This project demonstrates a practical AWS serverless event-driven
platform for ingesting, validating, persisting, asynchronously
processing, and routing operational events from distributed field
environments.

The validated baseline is:

``` text
Client
  ↓
API Gateway HTTP API
  ↓
Event Ingestion Lambda
  ↓
DynamoDB
  ↓
DynamoDB Streams
  ↓
Stream Processor Lambda
  ├──→ CloudWatch Logs
  └──→ SNS → SQS
```

## What Is Implemented

-   API Gateway HTTP API with `POST /events`
-   Python 3.12 Lambda ingestion
-   Pydantic validation
-   UUID event IDs and UTC timestamps
-   DynamoDB with `PAY_PER_REQUEST`
-   DynamoDB Streams using `NEW_AND_OLD_IMAGES`
-   Asynchronous Lambda stream processing
-   High/critical severity alert routing
-   SNS operational-alert topic
-   SQS durable alert queue
-   IAM execution roles and scoped permissions
-   DynamoDB server-side encryption
-   Terraform Infrastructure as Code
-   CloudWatch runtime logging
-   Automated pytest coverage

## Validation

``` powershell
python -m pytest application/tests -v
```

Final result:

``` text
33 passed
```

Terraform also completed successfully with `terraform validate`,
`terraform plan`, and `terraform apply`.

A real API event was created successfully, persisted in DynamoDB,
processed from the DynamoDB Stream, published to SNS for high severity,
and delivered to the SQS queue.

## AWS Resources

Development region: `eu-west-1`

``` text
API:
https://57gu5fmekc.execute-api.eu-west-1.amazonaws.com

DynamoDB:
fieldops-serverless-dev-events

Ingestion Lambda:
fieldops-serverless-dev-event-handler

Stream Processor:
fieldops-serverless-dev-stream-processor

SNS:
fieldops-serverless-dev-operational-alerts

SQS:
fieldops-serverless-dev-operational-alerts
```

Use `terraform output` for environment-specific values.

## Repository

``` text
application/
  src/
    handler.py
    models.py
    stream_handler.py
  tests/
    test_handler.py
    test_stream_handler.py

docs/
  architecture.md
  deployment.md
  troubleshooting.md
  validation.md

terraform/
  api_gateway.tf
  dynamodb.tf
  iam.tf
  lambda.tf
  sns.tf
  sqs.tf
  stream_mapping.tf
  stream_processor.tf
  outputs.tf
```

`eventbridge.tf` and `s3.tf` remain reserved for future evolution and
are not part of the current validated path.

## Security Baseline

Implemented: IAM roles, scoped permissions, HTTPS, Pydantic validation,
DynamoDB encryption.

Not yet implemented: API authentication/authorization, WAF, Secrets
Manager integration, CI/CD security scanning, and formal threat
modelling.

## Current Limitations

This is a portfolio baseline, not a production-hardened platform.
Idempotency, retries, partial batch failure handling, alarms,
dashboards, CI/CD, load testing, and authentication remain future
enhancements.

## Portfolio Decision

The core architecture is now sufficiently complete for the Solutions
Architect portfolio. The next project should introduce a different
architectural problem rather than continuing to add complexity here.

Observability can be added later as a focused maturity phase.
