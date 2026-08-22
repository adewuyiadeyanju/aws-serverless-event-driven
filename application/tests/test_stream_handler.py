import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

import test_stream_handler


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

def build_stream_record(
    severity="high",
    event_type="connectivity_degradation",
    message="Primary connectivity latency exceeded threshold",
):
    return {
        "eventName": "INSERT",
        "dynamodb": {
            "NewImage": {
                "event_id": {
                    "S": "event-001",
                },
                "site_id": {
                    "S": "RIG-001",
                },
                "event_type": {
                    "S": event_type,
                },
                "severity": {
                    "S": severity,
                },
                "message": {
                    "S": message,
                },
                "timestamp": {
                    "S": "2026-08-22T20:00:00+00:00",
                },
            }
        },
    }


def build_stream_event(record):
    return {
        "Records": [record],
    }


# ---------------------------------------------------------------------------
# Stream handler tests
# ---------------------------------------------------------------------------

def test_stream_handler_processes_insert_event(monkeypatch):
    mock_sns = MagicMock()

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:eu-west-1:123456789012:fieldops-alerts",
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    event = build_stream_event(
        build_stream_record(
            severity="high",
        )
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 1
    assert response["skipped_records"] == 0
    assert mock_sns.publish.call_count == 1


def test_stream_handler_processes_standard_event(monkeypatch):
    """
    Medium-severity events are valid operational events.

    They should be processed successfully but should not generate
    an operational alert notification.
    """

    mock_sns = MagicMock()

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:eu-west-1:123456789012:fieldops-alerts",
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    event = build_stream_event(
        build_stream_record(
            severity="medium",
            event_type="equipment_alert",
            message="Equipment telemetry alert detected",
        )
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 1
    assert response["skipped_records"] == 0
    assert mock_sns.publish.call_count == 0


def test_stream_handler_processes_critical_event(monkeypatch):
    mock_sns = MagicMock()

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:eu-west-1:123456789012:fieldops-alerts",
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    event = build_stream_event(
        build_stream_record(
            severity="critical",
            event_type="connectivity_loss",
            message="Primary connectivity completely unavailable",
        )
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 1
    assert response["skipped_records"] == 0
    assert mock_sns.publish.call_count == 1


def test_stream_handler_skips_modify_event(monkeypatch):
    mock_sns = MagicMock()

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:eu-west-1:123456789012:fieldops-alerts",
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    record = build_stream_record(
        severity="high",
    )

    record["eventName"] = "MODIFY"

    response = stream_handler.handler(
        build_stream_event(record),
        None,
    )

    assert response["processed_records"] == 0
    assert response["skipped_records"] == 1
    assert mock_sns.publish.call_count == 0


def test_stream_handler_skips_remove_event(monkeypatch):
    mock_sns = MagicMock()

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:eu-west-1:123456789012:fieldops-alerts",
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    record = build_stream_record(
        severity="critical",
    )

    record["eventName"] = "REMOVE"

    response = stream_handler.handler(
        build_stream_event(record),
        None,
    )

    assert response["processed_records"] == 0
    assert response["skipped_records"] == 1
    assert mock_sns.publish.call_count == 0


def test_stream_handler_processes_multiple_records(monkeypatch):
    mock_sns = MagicMock()

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:eu-west-1:123456789012:fieldops-alerts",
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    event = {
        "Records": [
            build_stream_record(
                severity="high",
            ),
            build_stream_record(
                severity="medium",
            ),
            build_stream_record(
                severity="critical",
            ),
        ]
    }

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 3
    assert response["skipped_records"] == 0

    # Only HIGH and CRITICAL generate alerts.
    assert mock_sns.publish.call_count == 2


def test_stream_handler_skips_insert_without_new_image(monkeypatch):
    mock_sns = MagicMock()

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:eu-west-1:123456789012:fieldops-alerts",
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    event = {
        "Records": [
            {
                "eventName": "INSERT",
                "dynamodb": {},
            }
        ]
    }

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 0
    assert response["skipped_records"] == 1
    assert mock_sns.publish.call_count == 0


# ---------------------------------------------------------------------------
# DynamoDB deserialization tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "dynamodb_value, expected",
    [
        (
            {"S": "RIG-001"},
            "RIG-001",
        ),
        (
            {"N": "100"},
            100,
        ),
        (
            {"N": "12.5"},
            12.5,
        ),
        (
            {"BOOL": True},
            True,
        ),
        (
            {"NULL": True},
            None,
        ),
        (
            {"SS": ["rig-001", "rig-002"]},
            ["rig-001", "rig-002"],
        ),
        (
            {"NS": ["1", "2.5", "3"]},
            [1, 2.5, 3],
        ),
        (
            {
                "L": [
                    {"S": "RIG-001"},
                    {"N": "10"},
                ]
            },
            ["RIG-001", 10],
        ),
        (
            {
                "M": {
                    "site_id": {"S": "RIG-001"},
                    "severity": {"S": "high"},
                }
            },
            {
                "site_id": "RIG-001",
                "severity": "high",
            },
        ),
    ],
)
def test_deserialize_dynamodb_values(
    dynamodb_value,
    expected,
):
    result = stream_handler.deserialize_dynamodb_value(
        dynamodb_value
    )

    assert result == expected


def test_deserialize_new_image():
    new_image = {
        "event_id": {
            "S": "event-001",
        },
        "site_id": {
            "S": "RIG-001",
        },
        "severity": {
            "S": "high",
        },
        "message": {
            "S": "Connectivity degraded",
        },
    }

    result = stream_handler.deserialize_new_image(
        new_image
    )

    assert result == {
        "event_id": "event-001",
        "site_id": "RIG-001",
        "severity": "high",
        "message": "Connectivity degraded",
    }


# ---------------------------------------------------------------------------
# SNS notification tests
# ---------------------------------------------------------------------------

def test_publish_notification(monkeypatch):
    mock_sns = MagicMock()

    mock_sns.publish.return_value = {
        "MessageId": "message-001",
    }

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:eu-west-1:123456789012:fieldops-alerts",
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    event_data = {
        "event_id": "event-001",
        "site_id": "RIG-001",
        "event_type": "connectivity_degradation",
        "severity": "high",
        "message": "Primary connectivity latency exceeded threshold",
        "timestamp": "2026-08-22T20:00:00+00:00",
    }

    response = stream_handler.publish_notification(
        event_data
    )

    assert response["MessageId"] == "message-001"

    mock_sns.publish.assert_called_once()

    call_kwargs = mock_sns.publish.call_args.kwargs

    assert (
        call_kwargs["TopicArn"]
        == "arn:aws:sns:eu-west-1:123456789012:fieldops-alerts"
    )

    assert (
        call_kwargs["Subject"]
        == "FieldOps Operational Alert"
    )

    assert json.loads(
        call_kwargs["Message"]
    ) == event_data


def test_publish_notification_skips_without_topic(
    monkeypatch,
):
    mock_sns = MagicMock()

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        None,
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    event_data = {
        "event_id": "event-001",
        "site_id": "RIG-001",
        "severity": "high",
    }

    response = stream_handler.publish_notification(
        event_data
    )

    assert response is None
    mock_sns.publish.assert_not_called()


# ---------------------------------------------------------------------------
# Severity notification policy tests
# ---------------------------------------------------------------------------

def test_stream_handler_publishes_high_severity_alert(
    monkeypatch,
):
    mock_sns = MagicMock()

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:eu-west-1:123456789012:fieldops-alerts",
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    event = build_stream_event(
        build_stream_record(
            severity="high",
        )
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 1
    assert response["skipped_records"] == 0
    assert mock_sns.publish.call_count == 1


def test_stream_handler_does_not_publish_medium_severity_alert(
    monkeypatch,
):
    """
    Medium-severity events are processed but do not generate
    SNS notifications.
    """

    mock_sns = MagicMock()

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:eu-west-1:123456789012:fieldops-alerts",
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    event = build_stream_event(
        build_stream_record(
            severity="medium",
        )
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 1
    assert response["skipped_records"] == 0
    assert mock_sns.publish.call_count == 0


def test_stream_handler_requires_sns_topic_for_priority_event(
    monkeypatch,
):
    """
    High-severity events should still be processed when SNS
    is not configured. The notification is simply skipped.
    """

    mock_sns = MagicMock()

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        None,
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    event = build_stream_event(
        build_stream_record(
            severity="high",
        )
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 1
    assert response["skipped_records"] == 0
    assert mock_sns.publish.call_count == 0


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

def test_stream_handler_empty_records(monkeypatch):
    mock_sns = MagicMock()

    monkeypatch.setattr(
        stream_handler,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:eu-west-1:123456789012:fieldops-alerts",
    )

    monkeypatch.setattr(
        stream_handler,
        "get_sns_client",
        lambda: mock_sns,
    )

    response = stream_handler.handler(
        {
            "Records": [],
        },
        None,
    )

    assert response["processed_records"] == 0
    assert response["skipped_records"] == 0
    assert mock_sns.publish.call_count == 0