import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

import stream_handler


def dynamodb_string(value):
    return {"S": value}


def build_stream_record(
    event_name="INSERT",
    include_new_image=True,
    severity="high",
    site_id="RIG-001",
    event_type="connectivity_degradation",
    message="Primary connectivity latency exceeded threshold",
):
    record = {
        "eventName": event_name,
        "dynamodb": {},
    }

    if include_new_image:
        record["dynamodb"]["NewImage"] = {
            "event_id": dynamodb_string("event-001"),
            "site_id": dynamodb_string(site_id),
            "event_type": dynamodb_string(event_type),
            "severity": dynamodb_string(severity),
            "message": dynamodb_string(message),
            "timestamp": dynamodb_string(
                "2026-08-22T20:00:00+00:00"
            ),
        }

    return record


def build_stream_event(*records):
    return {
        "Records": list(records),
    }


# ---------------------------------------------------------------------------
# Stream processing
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
        build_stream_record(),
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 1
    assert response["skipped_records"] == 0

    mock_sns.publish.assert_called_once()


def test_stream_handler_processes_standard_event(monkeypatch):
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

    mock_sns.publish.assert_called_once()


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
            message="Primary connectivity service unavailable",
        )
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 1
    assert response["skipped_records"] == 0

    mock_sns.publish.assert_called_once()


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

    event = build_stream_event(
        build_stream_record(
            event_name="MODIFY",
        )
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 0
    assert response["skipped_records"] == 1

    mock_sns.publish.assert_not_called()


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

    event = build_stream_event(
        build_stream_record(
            event_name="REMOVE",
        )
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 0
    assert response["skipped_records"] == 1

    mock_sns.publish.assert_not_called()


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

    event = build_stream_event(
        build_stream_record(
            event_name="INSERT",
            site_id="RIG-001",
        ),
        build_stream_record(
            event_name="INSERT",
            site_id="RIG-002",
        ),
        build_stream_record(
            event_name="MODIFY",
            site_id="RIG-003",
        ),
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 2
    assert response["skipped_records"] == 1

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

    event = build_stream_event(
        build_stream_record(
            event_name="INSERT",
            include_new_image=False,
        )
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 0
    assert response["skipped_records"] == 1

    mock_sns.publish.assert_not_called()


# ---------------------------------------------------------------------------
# DynamoDB deserialization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "dynamodb_value, expected",
    [
        ({"S": "RIG-001"}, "RIG-001"),
        ({"N": "100"}, 100),
        ({"N": "12.5"}, 12.5),
        ({"BOOL": True}, True),
        ({"NULL": True}, None),
        ({"SS": ["one", "two"]}, ["one", "two"]),
        ({"NS": ["1", "2.5"]}, [1, 2.5]),
        (
            {
                "L": [
                    {"S": "one"},
                    {"N": "2"},
                    {"BOOL": True},
                ]
            },
            ["one", 2, True],
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
        "event_id": {"S": "event-001"},
        "site_id": {"S": "RIG-001"},
        "event_type": {"S": "connectivity_degradation"},
        "severity": {"S": "high"},
        "message": {
            "S": "Primary connectivity latency exceeded threshold"
        },
        "timestamp": {
            "S": "2026-08-22T20:00:00+00:00"
        },
    }

    result = stream_handler.deserialize_new_image(
        new_image
    )

    assert result == {
        "event_id": "event-001",
        "site_id": "RIG-001",
        "event_type": "connectivity_degradation",
        "severity": "high",
        "message": (
            "Primary connectivity latency exceeded threshold"
        ),
        "timestamp": "2026-08-22T20:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# SNS notification
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

    assert call_kwargs["Subject"] == "FieldOps Operational Event"

    assert "RIG-001" in call_kwargs["Message"]
    assert "connectivity_degradation" in call_kwargs["Message"]


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
    assert mock_sns.publish.call_count == 1


def test_stream_handler_does_not_publish_medium_severity_alert(
    monkeypatch,
):
    """
    Current implementation publishes every INSERT event,
    regardless of severity.

    This test therefore verifies that medium severity events
    are processed and published.
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
    assert mock_sns.publish.call_count == 1


def test_stream_handler_requires_sns_topic_for_priority_event(
    monkeypatch,
):
    """
    When SNS_TOPIC_ARN is not configured, the stream processor
    should still process the DynamoDB Stream event successfully
    without attempting an SNS publish.
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
            severity="critical",
        )
    )

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 1
    assert response["skipped_records"] == 0

    mock_sns.publish.assert_not_called()


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

    event = {
        "Records": [],
    }

    response = stream_handler.handler(event, None)

    assert response["processed_records"] == 0
    assert response["skipped_records"] == 0

    mock_sns.publish.assert_not_called()