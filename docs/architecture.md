# Architecture

## Purpose

This project demonstrates a serverless, event-driven architecture for
ingesting, validating, persisting, asynchronously processing, and
routing operational events.

## Current Architecture

``` text
Operational Client
       |
       | HTTPS POST /events
       v
API Gateway HTTP API
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
       +----→ CloudWatch Logs
       |
       +----→ SNS Topic
                    |
                    v
                 SQS Queue
```

## Event Flow

1.  Client sends an operational event to `POST /events`.
2.  API Gateway invokes the ingestion Lambda.
3.  Pydantic validates the event.
4.  Lambda generates `event_id` and UTC timestamp.
5.  Event is persisted to DynamoDB.
6.  DynamoDB Streams captures the change.
7.  The event source mapping invokes the stream processor.
8.  The processor handles `INSERT` records and deserializes `NewImage`.
9.  High and critical events are published to SNS.
10. SNS delivers the alert to SQS.
11. CloudWatch Logs provide runtime evidence.

## Data Model

Required fields:

``` text
site_id
event_type
severity
message
```

Supported severity values:

``` text
low
medium
high
critical
```

DynamoDB configuration:

-   Partition key: `event_id`
-   Billing: `PAY_PER_REQUEST`
-   Server-side encryption: enabled
-   Streams: enabled
-   Stream view: `NEW_AND_OLD_IMAGES`

## Component Responsibilities

### API Gateway

Provides the HTTPS API entry point. Authentication is a future hardening
item.

### Event Ingestion Lambda

Parses, validates, generates IDs/timestamps, persists events, and
returns the creation response.

### Stream Processor Lambda

Processes `INSERT` events, deserializes DynamoDB values, logs events,
evaluates severity, and publishes priority alerts.

### SNS

Provides the notification fan-out boundary for high and critical
operational events.

### SQS

Provides a durable downstream alert queue and decouples future consumers
from the stream processor.

### CloudWatch

Provides current runtime logging and troubleshooting evidence.

## Why DynamoDB Streams?

The event is already persisted in DynamoDB, so Streams provide a natural
asynchronous change-data-capture boundary without introducing another
ingestion stream.

This is appropriate for the current moderate-scale serverless use case.
Kinesis or Kafka/MSK would be considered for high-throughput streaming,
replay-heavy workloads, or advanced stream analytics.

## Security

Current controls:

-   Dedicated IAM roles
-   Scoped DynamoDB permissions
-   Scoped SNS publish permission
-   HTTPS
-   Input validation
-   DynamoDB encryption

Future controls:

-   Authentication/authorization
-   WAF
-   Secrets Manager
-   CI/CD security scanning
-   Formal threat modelling

## Reliability

The architecture separates synchronous ingestion from asynchronous
processing and alert delivery.

Future hardening:

-   Idempotency
-   Retry strategy
-   Partial batch failure
-   Dead-letter/redrive handling
-   CloudWatch alarms
-   Operational runbooks

## Well-Architected Alignment

  Pillar                   Baseline
  ------------------------ -------------------------------------------------
  Operational Excellence   Terraform, tests, documentation, CloudWatch
  Security                 IAM, scoped permissions, encryption, validation
  Reliability              Managed services and decoupling
  Performance              Serverless and on-demand DynamoDB
  Cost                     Pay-per-request and managed services
  Sustainability           Demand-based serverless execution

## Future Evolution

``` text
API → Lambda → DynamoDB → Stream → Processor → SNS → SQS
                                      |
                                      +→ Analytics
                                      +→ Incident Management
                                      +→ EventBridge
```

Observability, authentication, CI/CD, and reliability hardening can be
added later without changing the core ingestion contract.
