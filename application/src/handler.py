# Add modules
import json
import os
import uuid
from datetime import datetime, timezone

import boto3

from models import OperationalEvent


TABLE_NAME = os.environ.get("EVENT_TABLE_NAME", "operational-events")


def get_table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(TABLE_NAME)


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
            "severity": operational_event.severity,
            "message": operational_event.message,
            "timestamp": timestamp,
        }

        table = get_table()
        table.put_item(Item=item)

        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "event_id": event_id,
                "status": "created",
            }),
        }

    except Exception as exc:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": str(exc),
            }),
        }