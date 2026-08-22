import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PROCESSOR_NAME = os.environ.get(
    "PROCESSOR_NAME",
    "operational-event-stream-processor"
)


def handler(event, context):
    """
    Process records received from DynamoDB Streams.
    """

    records = event.get("Records", [])

    logger.info(
        "Stream processor started. Records received: %d",
        len(records),
    )

    processed = 0

    for record in records:
        event_name = record.get("eventName")

        logger.info(
            "Processing DynamoDB Stream event: %s",
            event_name,
        )

        # For this phase we only process newly created items.
        if event_name != "INSERT":
            logger.info(
                "Skipping event type: %s",
                event_name,
            )
            continue

        dynamodb = record.get("dynamodb", {})
        new_image = dynamodb.get("NewImage", {})

        logger.info(
            "New operational event: %s",
            json.dumps(new_image),
        )

        processed += 1

    logger.info(
        "Stream processor completed. Processed records: %d",
        processed,
    )

    return {
        "processed_records": processed,
    }