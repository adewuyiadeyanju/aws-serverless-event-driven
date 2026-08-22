import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3
from pydantic import ValidationError

from models import OperationalEvent


logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get(
    "EVENT_TABLE_NAME",
    "operational-events",
)


def get_table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(TABLE_NAME)


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(body),
    }


def handler(event, context):
    try:
        body = event.get("body")

        if isinstance(body, str):
            body = json.loads(body)

        operational_event = OperationalEvent(**body)

        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        item = {
            "event_id": event_id,
            "site_id": operational_event.site_id,
            "event_type": operational_event.event_type,
            "severity": operational_event.severity.value,
            "message": operational_event.message,
            "timestamp": timestamp,
        }

        table = get_table()
        table.put_item(Item=item)

        logger.info(
            "Operational event created: event_id=%s site_id=%s "
            "event_type=%s severity=%s",
            event_id,
            operational_event.site_id,
            operational_event.event_type,
            operational_event.severity.value,
        )

        return response(
            201,
            {
                "event_id": event_id,
                "status": "created",
            },
        )

    except ValidationError as exc:
        logger.warning(
            "Operational event validation failed: %s",
            exc.errors(),
        )

        return response(
            400,
            {
                "error": "Invalid operational event",
                "details": exc.errors(),
            },
        )

    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning(
            "Invalid request payload: %s",
            str(exc),
        )

        return response(
            400,
            {
                "error": "Invalid JSON request body",
            },
        )

    except Exception:
        logger.exception(
            "Unexpected error while processing operational event"
        )

        return response(
            500,
            {
                "error": "Internal server error",
            },
        )