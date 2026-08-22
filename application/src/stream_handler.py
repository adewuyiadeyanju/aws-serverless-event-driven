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

    This prevents pytest from requiring AWS credentials
    during module import.
    """
    return boto3.client("sns")


def deserialize_dynamodb_value(value):
    """Convert a DynamoDB Streams attribute value to Python."""

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
    """Convert DynamoDB Streams NewImage to a normal dictionary."""

    return {
        key: deserialize_dynamodb_value(value)
        for key, value in new_image.items()
    }


def publish_notification(event_data):
    """
    Publish an operational event to SNS.

    SNS is skipped when SNS_TOPIC_ARN is not configured.
    """

    if not SNS_TOPIC_ARN:
        logger.info(
            "SNS_TOPIC_ARN is not configured. Skipping notification."
        )
        return None

    message = json.dumps(event_data)

    response = get_sns_client().publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="FieldOps Operational Event",
        Message=message,
    )

    logger.info(
        "Operational event notification published to SNS. MessageId: %s",
        response.get("MessageId"),
    )

    return response


def handler(event, context):
    """
    Process records received from DynamoDB Streams.

    Processes INSERT events only.
    MODIFY and REMOVE events are skipped.
    """

    records = event.get("Records", [])

    logger.info(
        "Stream processor started. Records received: %d",
        len(records),
    )

    processed = 0
    skipped = 0

    for record in records:
        event_name = record.get("eventName")

        logger.info(
            "Processing DynamoDB Stream event: %s",
            event_name,
        )

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
                "INSERT event does not contain NewImage. Skipping record."
            )

            skipped += 1
            continue

        operational_event = deserialize_new_image(new_image)

        logger.info(
            "New operational event: %s",
            json.dumps(operational_event),
        )

        publish_notification(operational_event)

        processed += 1

    logger.info(
        "Stream processor completed. "
        "Processed records: %d, Skipped records: %d",
        processed,
        skipped,
    )

    return {
        "processed_records": processed,
        "skipped_records": skipped,
    }