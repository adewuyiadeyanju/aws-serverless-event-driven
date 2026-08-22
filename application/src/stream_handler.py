import json
import logging
import os

import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)


PROCESSOR_NAME = os.environ.get(
    "PROCESSOR_NAME",
    "operational-event-stream-processor",
)

SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")


def get_sns_client():
    """
    Create the SNS client only when it is needed.

    Keeping client creation out of module scope makes the Lambda
    easier to test locally without requiring AWS credentials during
    pytest collection.
    """
    return boto3.client("sns")


def deserialize_dynamodb_value(value):
    """
    Convert a DynamoDB Streams attribute value into a normal
    Python value.
    """

    if not value:
        return None

    if "S" in value:
        return value["S"]

    if "N" in value:
        number = value["N"]

        if "." in number:
            return float(number)

        return int(number)

    if "BOOL" in value:
        return value["BOOL"]

    if "NULL" in value:
        return None

    if "SS" in value:
        return value["SS"]

    if "NS" in value:
        return [
            float(number) if "." in number else int(number)
            for number in value["NS"]
        ]

    if "L" in value:
        return [
            deserialize_dynamodb_value(item)
            for item in value["L"]
        ]

    if "M" in value:
        return {
            key: deserialize_dynamodb_value(item)
            for key, item in value["M"].items()
        }

    return value


def deserialize_new_image(new_image):
    """
    Convert a DynamoDB Streams NewImage into a normal
    Python dictionary.
    """

    return {
        key: deserialize_dynamodb_value(value)
        for key, value in new_image.items()
    }


def should_publish_notification(event_data):
    """
    Determine whether an operational event should be published
    as an alert.

    Routing rules:

        low      -> no notification
        medium   -> no notification
        high     -> operational alert
        critical -> priority alert
    """

    severity = event_data.get("severity", "").lower()

    if severity in {"high", "critical"}:
        return True

    return False


def publish_notification(event_data):
    """
    Publish an operational event notification to SNS.

    SNS publishing is skipped when SNS_TOPIC_ARN is not configured.
    """

    if not SNS_TOPIC_ARN:
        logger.info(
            "SNS_TOPIC_ARN is not configured. "
            "Skipping notification."
        )
        return None

    message = json.dumps(event_data)

    severity = event_data.get("severity", "").lower()

    if severity == "critical":
        subject = "FieldOps CRITICAL Operational Alert"
    else:
        subject = "FieldOps Operational Alert"

    response = get_sns_client().publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject,
        Message=message,
    )

    logger.info(
        "Operational event notification published to SNS. "
        "Severity: %s, MessageId: %s",
        severity,
        response.get("MessageId"),
    )

    return response


def handler(event, context):
    """
    Process records received from DynamoDB Streams.

    Processing behavior:

      - Processes INSERT events.
      - Ignores MODIFY and REMOVE events.
      - Converts DynamoDB Stream data into normal Python values.
      - Publishes HIGH and CRITICAL events to SNS.
      - Does not publish LOW and MEDIUM events.
    """

    records = event.get("Records", [])

    logger.info(
        "Stream processor started. Records received: %d",
        len(records),
    )

    processed = 0
    skipped = 0
    notifications_published = 0

    for record in records:
        event_name = record.get("eventName")

        logger.info(
            "Processing DynamoDB Stream event: %s",
            event_name,
        )

        # Only process newly created operational events.
        if event_name != "INSERT":
            logger.info(
                "Skipping event type: %s",
                event_name,
            )

            skipped += 1
            continue

        dynamodb = record.get("dynamodb", {})
        new_image = dynamodb.get("NewImage", {})

        if not new_image:
            logger.warning(
                "INSERT event does not contain NewImage. "
                "Skipping record."
            )

            skipped += 1
            continue

        operational_event = deserialize_new_image(new_image)

        severity = operational_event.get(
            "severity",
            "",
        ).lower()

        logger.info(
            "New operational event: %s",
            json.dumps(operational_event),
        )

        processed += 1

        # Apply severity-based routing.
        if should_publish_notification(operational_event):

            logger.info(
                "Severity '%s' requires operational notification.",
                severity,
            )

            publish_notification(operational_event)

            notifications_published += 1

        else:
            logger.info(
                "Severity '%s' does not require notification.",
                severity,
            )

    logger.info(
        "Stream processor completed. "
        "Processed records: %d, "
        "Skipped records: %d, "
        "Notifications published: %d",
        processed,
        skipped,
        notifications_published,
    )

    return {
        "processed_records": processed,
        "skipped_records": skipped,
        "notifications_published": notifications_published,
    }