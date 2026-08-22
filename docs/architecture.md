# Architecture

## Purpose

This project demonstrates a serverless, event-driven architecture for ingesting, validating, persisting, and asynchronously processing operational events from distributed field environments.

Example events include:

- Connectivity degradation
- Equipment alerts
- Telemetry conditions
- Operational threshold breaches

The current implementation is a portfolio baseline focused on demonstrating AWS architecture, Infrastructure as Code, validation, asynchronous processing, and operational troubleshooting.

## Current Logical Architecture

```text
+---------------------------+
| Field / Operational       |
| Systems / API Clients     |
+-------------+-------------+
              |
              | HTTPS POST /events
              v
+---------------------------+
| Amazon API Gateway        |
| HTTP API                  |
+-------------+-------------+
              |
              v
+---------------------------+
| Lambda: Event Ingestion   |
| - Parse request           |
| - Pydantic validation     |
| - Generate UUID           |
| - Generate UTC timestamp  |
| - Persist event           |
+-------------+-------------+
              |
              | PutItem
              v
+---------------------------+
| Amazon DynamoDB           |
| fieldops-serverless-...   |
| PAY_PER_REQUEST           |
+-------------+-------------+
              |
              | DynamoDB Stream
              v
+---------------------------+
| Lambda: Stream Processor  |
| - Receive stream batch    |
| - Process INSERT events   |
| - Log NewImage            |
+-------------+-------------+
              |
              v
+---------------------------+
| Amazon CloudWatch Logs    |
+---------------------------+
```

## End-to-End Event Flow

1. A client submits an operational event to `POST /events`.
2. API Gateway forwards the request to the ingestion Lambda.
3. The Lambda parses the request body.
4. Pydantic validates the `OperationalEvent` model.
5. The Lambda generates a UUID and UTC timestamp.
6. The event is written to DynamoDB.
7. DynamoDB Streams captures the database change.
8. The stream event asynchronously invokes the stream processor Lambda.
9. The stream processor currently handles `INSERT` records and logs the new image.
10. CloudWatch Logs provides runtime evidence and diagnostics.

## Component Responsibilities

### API Gateway

Provides the HTTPS entry point:

```text
POST /events
```

The current baseline uses an HTTP API and does not yet implement authentication or authorization.

### Event Ingestion Lambda

The ingestion handler is responsible for:

- Parsing the API request.
- Validating required fields with Pydantic.
- Generating a unique event ID.
- Generating a UTC timestamp.
- Persisting the event.
- Returning the generated event ID.

### OperationalEvent Model

The required fields are:

```text
site_id
event_type
severity
message
```

The model applies minimum and maximum length constraints.

### DynamoDB

DynamoDB provides persistent operational-event storage.

Current configuration:

- Partition key: `event_id`
- Billing mode: `PAY_PER_REQUEST`
- Server-side encryption: enabled
- DynamoDB Streams: enabled
- Stream view type: `NEW_AND_OLD_IMAGES`

### DynamoDB Streams

DynamoDB Streams create the asynchronous boundary between persistence and downstream processing.

The current implementation consumes stream records through a Lambda event source mapping.

### Stream Processor Lambda

The stream processor:

- Receives DynamoDB Stream batches.
- Processes `INSERT` records.
- Extracts `NewImage`.
- Logs the operational event.
- Reports the number of processed records.

It is intentionally a simple baseline consumer. Future versions can route events to alerting, EventBridge, incident management, analytics, or notification systems.

### CloudWatch

CloudWatch Logs provides runtime observability for both Lambda functions and was used to validate successful stream processing.

## Event-Driven Characteristics

The core pattern is:

```text
Producer
   |
   v
API Gateway
   |
   v
Ingestion Lambda
   |
   v
Persistent Event
   |
   v
DynamoDB Stream
   |
   v
Stream Consumer
```

The API request does not wait for the downstream stream processor to complete. The downstream processing is therefore asynchronous.

This separation allows additional consumers to be introduced without changing the API ingestion contract.

## Near-Real-Time Capability

The implementation can support **near-real-time event processing**:

```text
Operational Event
      |
      v
API Gateway
      |
      v
Lambda
      |
      v
DynamoDB
      |
      v
DynamoDB Stream
      |
      v
Stream Processor
      +----> Alerting
      +----> EventBridge
      +----> Incident Management
      +----> Analytics
      +----> Notifications
```

The correct description for the current project is **near-real-time event-driven processing**, not a high-throughput streaming platform.

It is conceptually similar to real-time data pipelines because data changes can trigger downstream processing asynchronously. However, this baseline is not intended to replace technologies such as Amazon Kinesis or Apache Kafka when very high event throughput, partitioned streams, replay, or sophisticated stream analytics are required.

## Security Baseline

Current controls include:

- Dedicated IAM execution roles.
- Least-privilege DynamoDB write permissions for the ingestion Lambda.
- HTTPS at API Gateway.
- Pydantic input validation.
- DynamoDB server-side encryption.
- CloudWatch logging.

Not yet implemented:

- API authentication and authorization.
- API keys or usage plans.
- WAF protection.
- Secrets management.
- Formal security scanning in CI/CD.

## Scalability

API Gateway, Lambda, and DynamoDB are managed AWS services designed to scale with workload.

DynamoDB `PAY_PER_REQUEST` capacity is appropriate for variable event traffic without manually provisioning read/write capacity.

The stream processor is independently scalable through Lambda's DynamoDB Streams event source mapping.

For significantly higher throughput or advanced stream-processing requirements, a Kinesis- or Kafka-based architecture would be more appropriate.

## Reliability

The architecture separates synchronous ingestion from asynchronous downstream processing.

Current baseline reliability comes from managed AWS services and decoupled processing.

Production-hardening work should add:

- Retry strategy.
- Dead-letter destination.
- Idempotent processing.
- Partial batch failure handling.
- CloudWatch alarms.
- Failure dashboards.
- Explicit operational runbooks.

## AWS Well-Architected Alignment

| Pillar | Current baseline |
|---|---|
| Operational Excellence | Terraform, documentation, tests, CloudWatch logs |
| Security | IAM, least privilege, encryption, input validation |
| Reliability | Managed services and asynchronous processing |
| Performance Efficiency | Lambda and DynamoDB on-demand capacity |
| Cost Optimization | Serverless architecture and pay-per-request DynamoDB |
| Sustainability | Demand-based serverless execution |

## Future Evolution

```text
                         +--> EventBridge --> Alerting
                         |
API --> Lambda --> DynamoDB --> Stream --> Processor
                         |                  |
                         |                  +--> Analytics
                         |
                         +--> Operational Data
```

Potential next stages:

1. Add EventBridge routing.
2. Add alerting based on severity and event type.
3. Add idempotency and retry handling.
4. Add authentication and authorization.
5. Add CloudWatch alarms and dashboards.
6. Add CI/CD and automated security scanning.
7. Add additional event consumers.
8. Introduce Kinesis/Kafka if throughput and streaming requirements justify it.
