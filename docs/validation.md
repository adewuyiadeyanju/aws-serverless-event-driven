# Validation

## Objective

The final objective was to demonstrate the complete deployed
event-driven path:

``` text
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
SNS
 ↓
SQS
```

CloudWatch Logs provide runtime evidence.

## 1. Automated Tests

Command:

``` powershell
python -m pytest application/tests -v
```

Final result:

``` text
33 passed in 0.80s
```

The suite covers ingestion behavior, severity validation, required
fields, stream INSERT/MODIFY/REMOVE handling, DynamoDB deserialization,
notification behavior, priority routing, SNS configuration, and empty
batches.

## 2. Terraform

The final infrastructure was successfully validated and applied:

``` powershell
terraform validate
terraform plan
terraform apply
```

Terraform subsequently reported no unexpected infrastructure drift.

## 3. API Validation

A real request for `RIG-006` was submitted:

``` json
{
  "site_id": "RIG-006",
  "event_type": "connectivity_degradation",
  "severity": "high",
  "message": "LEO connectivity latency exceeded operational threshold"
}
```

The API returned a generated event ID and:

``` text
status = created
```

## 4. DynamoDB Persistence

The event was confirmed in:

``` text
fieldops-serverless-dev-events
```

The stored event contains:

``` text
event_id
site_id
event_type
severity
message
timestamp
```

## 5. Input Validation

Automated tests confirm that missing required fields and invalid
severity values are rejected before persistence.

## 6. DynamoDB Streams

Observed configuration:

``` json
{
    "StreamEnabled": true,
    "StreamViewType": "NEW_AND_OLD_IMAGES"
}
```

This confirms the change-data-capture layer.

## 7. Stream Processor

CloudWatch showed:

``` text
Stream processor started. Records received: 1
Processing DynamoDB Stream event: INSERT
New operational event: {...}
Operational event notification published to SNS. MessageId: ...
Stream processor completed. Processed records: 1, Skipped records: 0
```

This proves that DynamoDB changes asynchronously invoked the stream
processor and that a high-severity event was routed to SNS.

## 8. SNS Validation

The deployed topic is:

``` text
fieldops-serverless-dev-operational-alerts
```

The topic has an SQS subscription.

Validation:

``` powershell
aws sns list-subscriptions-by-topic `
  --topic-arn "$(terraform output -raw sns_topic_arn)" `
  --region eu-west-1
```

Observed protocol:

``` text
sqs
```

## 9. SQS Validation

The queue is:

``` text
fieldops-serverless-dev-operational-alerts
```

A message was successfully retrieved with:

``` powershell
aws sqs receive-message `
  --queue-url "$(terraform output -raw sqs_queue_url)" `
  --region eu-west-1 `
  --max-number-of-messages 10 `
  --wait-time-seconds 5
```

The message contained the SNS envelope and the operational event,
including the `RIG-006` high-severity connectivity event.

Therefore the alert path was validated end-to-end:

``` text
DynamoDB
 ↓
Stream
 ↓
Lambda
 ↓
SNS
 ↓
SQS
```

## 10. Severity Routing

  Severity     Processed   Priority SNS Notification
  ---------- ----------- ---------------------------
  low                Yes                          No
  medium             Yes                          No
  high               Yes                         Yes
  critical           Yes                         Yes

## 11. Evidence Summary

  Validation                      Result
  ------------------------------- --------
  33 Python tests                 PASS
  Terraform validate              PASS
  Terraform plan                  PASS
  Terraform apply                 PASS
  API invocation                  PASS
  Event creation                  PASS
  DynamoDB persistence            PASS
  Input validation                PASS
  DynamoDB Streams                PASS
  Stream processor                PASS
  High-severity SNS publication   PASS
  SNS → SQS subscription          PASS
  SQS delivery                    PASS
  CloudWatch logs                 PASS

## 12. Near-Real-Time Capability

The stream processor executed shortly after the DynamoDB insertion.

This demonstrates **near-real-time asynchronous event processing**.

The platform should not be described as a Kafka/Kinesis-equivalent
high-throughput streaming platform.

## 13. Observability Baseline

Current observability is CloudWatch logging:

``` text
/aws/lambda/fieldops-serverless-dev-event-handler
/aws/lambda/fieldops-serverless-dev-stream-processor
```

Dedicated metrics, alarms, dashboards, structured logs, correlation IDs,
and tracing are intentionally deferred.

## 14. Baseline Limitations

Not yet implemented or validated:

-   API authentication/authorization
-   API throttling
-   Idempotency
-   Retry/backoff strategy
-   Partial batch failure handling
-   Dead-letter/redrive handling
-   SQS consumer
-   CloudWatch alarms
-   Dashboards
-   Distributed tracing
-   CI/CD
-   Security scanning
-   Multi-environment promotion
-   Load testing
-   High-throughput streaming

## 15. Completion Decision

The core architectural objective is complete.

The project now demonstrates:

``` text
Architecture
 ↓
Implementation
 ↓
Infrastructure as Code
 ↓
Testing
 ↓
Deployment
 ↓
Troubleshooting
 ↓
End-to-End Validation
 ↓
Asynchronous Alert Delivery
```

This is sufficient as a Solutions Architect portfolio baseline.

Observability and production hardening can be revisited later. The
recommended next step is to move to Project 3 and avoid adding
complexity to this baseline unless a specific requirement justifies it.
