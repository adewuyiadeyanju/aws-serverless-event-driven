# AWS Serverless Event-Driven Operational Events Platform

A production-oriented AWS serverless reference architecture for ingesting, validating, persisting, and asynchronously processing operational events from distributed field environments.

The project demonstrates how an event-driven AWS architecture can support near-real-time operational workflows while remaining scalable, secure, observable, and cost-conscious.

---

## 1. Project Overview

Distributed operational environments such as drilling rigs, remote sites, and field operations continuously generate events from connectivity systems, equipment, telemetry, and operational applications.

This project implements a baseline serverless platform that:

- Accepts operational events through an HTTP API.
- Validates incoming payloads using Pydantic.
- Persists validated events in Amazon DynamoDB.
- Uses DynamoDB Streams to capture newly created events.
- Invokes a dedicated Lambda stream processor asynchronously.
- Provides CloudWatch logging for operational visibility.
- Uses Terraform to provision and manage the AWS infrastructure.

The implementation is intentionally focused on a practical baseline that can be extended incrementally.

---

## 2. Architecture

### High-Level Architecture

```text
Operational System / Client
          |
          | HTTP POST /events
          v
   Amazon API Gateway
          |
          v
   AWS Lambda
   Event Handler
          |
          | Validate
          | Persist
          v
   Amazon DynamoDB
   Operational Events
          |
          | DynamoDB Stream
          v
   AWS Lambda
   Stream Processor
          |
          v
   Amazon CloudWatch Logs
```

### Event Flow

1. A client submits an operational event to API Gateway.
2. API Gateway invokes the event-handler Lambda function.
3. The Lambda function parses and validates the request using the `OperationalEvent` Pydantic model.
4. A unique event ID and UTC timestamp are generated.
5. The event is stored in DynamoDB.
6. DynamoDB Streams captures the database change.
7. The stream processor Lambda receives the stream record.
8. The processor handles newly inserted events and records processing activity in CloudWatch Logs.

This creates an asynchronous processing boundary between event ingestion and downstream event processing.

---

## 3. AWS Services

| Service | Purpose |
|---|---|
| Amazon API Gateway | HTTP API endpoint for operational event ingestion |
| AWS Lambda | Serverless event ingestion and asynchronous stream processing |
| Amazon DynamoDB | Durable operational event storage |
| DynamoDB Streams | Change-data capture and event-driven processing |
| Amazon CloudWatch Logs | Application and stream processor observability |
| AWS IAM | Least-privilege execution permissions |
| Terraform | Infrastructure as Code |
| Amazon S3 | Reserved for future object-storage use cases |

---

## 4. Repository Structure

```text
aws-serverless-event-driven/
│
├── application/
│   ├── src/
│   │   ├── handler.py
│   │   ├── models.py
│   │   └── stream_handler.py
│   │
│   ├── tests/
│   │   └── test_handler.py
│   │
│   └── build/
│
├── architecture/
│
├── docs/
│   ├── architecture.md
│   ├── deployment.md
│   ├── troubleshooting.md
│   └── validation.md
│
├── terraform/
│   ├── api_gateway.tf
│   ├── cloudwatch.tf
│   ├── dynamodb.tf
│   ├── eventbridge.tf
│   ├── iam.tf
│   ├── lambda.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── s3.tf
│   ├── stream_lambda.tf
│   └── variables.tf
│
├── .gitignore
└── README.md
```

> `eventbridge.tf` and `s3.tf` are retained in the repository as infrastructure components reserved for future evolution of the platform. The currently validated baseline flow is API Gateway → Lambda → DynamoDB → DynamoDB Streams → Lambda.

---

## 5. Core Application Components

### Event Handler

`application/src/handler.py`

Responsible for:

- Parsing API Gateway request bodies.
- Validating operational events.
- Generating unique event IDs.
- Generating UTC timestamps.
- Writing events to DynamoDB.
- Returning an HTTP response to the caller.

### Data Model

`application/src/models.py`

Defines the operational event contract:

```text
site_id
event_type
severity
message
```

The model enforces basic input constraints including non-empty values and maximum field lengths.

### Stream Processor

`application/src/stream_handler.py`

Responsible for processing records delivered by DynamoDB Streams.

The current baseline processes `INSERT` events and logs the received DynamoDB Stream record.

This component provides the foundation for downstream event processing such as:

- Alert generation
- Notification workflows
- Event routing
- Operational analytics
- Integration with external systems

---

# 6. Validation and Evidence

The implementation was validated progressively from application logic through the deployed AWS event-driven flow.

## 6.1 Unit Testing

The application test suite was executed using:

```powershell
python -m pytest application	ests
```

Result:

```text
1 passed
```

This confirms the baseline application test passed before relying on the deployed AWS environment.

---

## 6.2 Terraform Validation

Terraform configuration was validated and successfully deployed.

The infrastructure plan progressed from the initial Lambda and DynamoDB resources to the complete event-driven architecture.

The final deployment successfully created the stream-processing components.

---

## 6.3 API Gateway → Lambda → DynamoDB

A valid operational event was submitted through the API endpoint.

Example:

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

The event was then confirmed in DynamoDB.

Example stored event:

```text
site_id: RIG-003
event_type: equipment_alert
severity: medium
message: Equipment telemetry alert detected
```

---

## 6.4 Input Validation

An invalid request was submitted without the required `site_id` field.

The API rejected the request with a validation error:

```text
1 validation error for OperationalEvent
site_id
Field required
```

This demonstrates that the API does not blindly persist malformed operational events.

---

## 6.5 DynamoDB Streams

DynamoDB Streams was enabled using:

```text
StreamEnabled: true
StreamViewType: NEW_AND_OLD_IMAGES
```

The deployed table exposed a DynamoDB Stream ARN.

This establishes the change-data-capture layer required for asynchronous event processing.

---

## 6.6 DynamoDB → Stream Processor Lambda

A new operational event was created and the stream processor automatically received the resulting DynamoDB Stream record.

CloudWatch confirmed:

```text
Stream processor started. Records received: 1
Processing DynamoDB Stream event: INSERT
New operational event: ...
Stream processor completed. Processed records: 1
```

This is the key end-to-end validation of the event-driven architecture.

The demonstrated flow is therefore:

```text
API Request
    ↓
API Gateway
    ↓
Event Handler Lambda
    ↓
DynamoDB
    ↓
DynamoDB Stream
    ↓
Stream Processor Lambda
    ↓
CloudWatch
```

---

## 6.7 Near-Real-Time Processing Capability

The current implementation can function as the foundation of a near-real-time data-processing application.

DynamoDB Streams captures database changes and invokes the stream processor asynchronously. In the validation test, the newly created event was processed by the stream Lambda shortly after insertion.

The current implementation is intentionally a baseline processor rather than a full streaming analytics platform.

For higher-scale streaming requirements, the architecture could evolve toward services such as Amazon Kinesis or Amazon MSK depending on throughput, ordering, replay, and analytics requirements.

---

# 7. Security Design

The baseline implementation includes several security controls:

### IAM

Lambda execution roles are provisioned through Terraform.

The event handler is granted the required DynamoDB write permission rather than broad DynamoDB administrative access.

### Data Protection

DynamoDB server-side encryption is enabled.

### API Validation

Incoming requests are validated against the Pydantic data model before persistence.

### Infrastructure as Code

AWS infrastructure is managed through Terraform, providing repeatable and reviewable infrastructure changes.

---

# 8. AWS Well-Architected Alignment

The architecture demonstrates alignment with the AWS Well-Architected principles.

| Pillar | Implementation |
|---|---|
| Operational Excellence | Terraform, automated deployment, CloudWatch logging |
| Security | IAM execution roles, scoped DynamoDB permissions, validation |
| Reliability | Managed serverless services and asynchronous stream processing |
| Performance Efficiency | Serverless execution and event-driven processing |
| Cost Optimization | Pay-per-request DynamoDB and Lambda/serverless consumption model |
| Sustainability | Serverless architecture avoids continuously running application servers |

---

# 9. Scalability

The architecture is designed around managed serverless services.

API Gateway and Lambda can scale with incoming requests, while DynamoDB uses on-demand capacity in the current implementation.

DynamoDB Streams decouples persistence from downstream processing, allowing the stream processor to evolve independently from the ingestion API.

Future scale considerations include:

- Lambda concurrency controls
- Dead-letter handling
- Retry strategy
- Idempotent processing
- Event filtering
- Kinesis for high-throughput streaming
- Additional downstream consumers

---

# 10. Observability

CloudWatch Logs provides visibility into the Lambda and stream-processing lifecycle.

The stream processor records:

- Number of records received
- DynamoDB event type
- New event contents
- Number of records processed
- Lambda execution details

This provides a foundation for operational monitoring and troubleshooting.

Future improvements can include:

- CloudWatch metrics
- Alarms
- Structured JSON logging
- Distributed tracing
- Dashboards
- Operational SLOs

---

# 11. Current Baseline vs Future Evolution

The project is deliberately being developed incrementally.

### Current baseline

```text
API Gateway
    ↓
Lambda
    ↓
DynamoDB
    ↓
DynamoDB Streams
    ↓
Lambda Stream Processor
```

### Potential evolution

```text
                         ┌──→ Alerting
                         │
API → Lambda → DynamoDB ─┼──→ Analytics
                         │
                         ├──→ Event Routing
                         │
                         └──→ External Systems

                  DynamoDB Stream
                         ↓
                  Stream Processor
```

Potential future capabilities include:

- EventBridge-based event routing
- Notification workflows
- Automated incident creation
- S3-based event archival
- Operational dashboards
- Dead-letter queues
- Retry and failure handling
- Idempotency controls
- Kinesis-based high-throughput streaming
- Security hardening
- CI/CD deployment

---

# 12. Deployment

Detailed deployment instructions are available in:

- `docs/deployment.md`

The infrastructure is provisioned using Terraform.

Typical workflow:

```powershell
cd terraform

terraform init
terraform validate
terraform plan
terraform apply
```

The application dependencies are packaged into the Lambda deployment artifact before deployment.

---

# 13. Troubleshooting

Deployment and runtime issues encountered during implementation are documented in:

- `docs/troubleshooting.md`

Examples include:

- Lambda dependency packaging problems with Pydantic
- Native `pydantic_core` compatibility issues
- Windows JSON UTF-8 BOM problems
- Terraform duplicate resource definitions
- API payload validation failures
- DynamoDB Stream processing validation

Documenting these issues demonstrates practical deployment and troubleshooting experience rather than only theoretical architecture design.

---

# 14. Project Status

**Baseline implementation: Completed and validated**

The current implementation demonstrates:

- Serverless API ingestion
- Schema validation
- Persistent event storage
- DynamoDB change-data capture
- Asynchronous Lambda processing
- Infrastructure as Code
- IAM-based access control
- CloudWatch observability
- End-to-end validation

The next development stages will focus on making the platform more production-ready through stronger reliability, observability, security, event routing, and operational controls.

---

## 15. Portfolio Objective

This project is part of a broader cloud architecture portfolio demonstrating practical AWS Solutions Architect capabilities across:

- Cloud architecture
- Serverless design
- Event-driven architecture
- Infrastructure as Code
- Security
- Reliability
- Scalability
- Cost optimization
- Operational observability
- Migration and modernization patterns

The goal is to demonstrate not only knowledge of AWS services, but the ability to design, implement, validate, troubleshoot, and evolve cloud solutions.
