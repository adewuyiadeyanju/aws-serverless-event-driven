import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

import handler


def build_event(
    site_id="RIG-001",
    event_type="connectivity_degradation",
    severity="high",
    message="Primary connectivity latency exceeded threshold",
):
    return {
        "body": json.dumps({
            "site_id": site_id,
            "event_type": event_type,
            "severity": severity,
            "message": message,
        })
    }


def test_handler_creates_event(monkeypatch):
    mock_table = MagicMock()

    monkeypatch.setattr(
        handler,
        "get_table",
        lambda: mock_table,
    )

    response = handler.handler(
        build_event(),
        None,
    )

    assert response["statusCode"] == 201

    body = json.loads(response["body"])

    assert body["status"] == "created"
    assert "event_id" in body

    mock_table.put_item.assert_called_once()

    saved_item = mock_table.put_item.call_args.kwargs["Item"]

    assert saved_item["site_id"] == "RIG-001"
    assert saved_item["event_type"] == "connectivity_degradation"
    assert saved_item["severity"] == "high"
    assert saved_item["message"] == (
        "Primary connectivity latency exceeded threshold"
    )
    assert "event_id" in saved_item
    assert "timestamp" in saved_item


@pytest.mark.parametrize(
    "severity",
    ["low", "medium", "high", "critical"],
)
def test_handler_accepts_valid_severity(monkeypatch, severity):
    mock_table = MagicMock()

    monkeypatch.setattr(
        handler,
        "get_table",
        lambda: mock_table,
    )

    response = handler.handler(
        build_event(severity=severity),
        None,
    )

    assert response["statusCode"] == 201

    mock_table.put_item.assert_called_once()

    saved_item = mock_table.put_item.call_args.kwargs["Item"]

    assert saved_item["severity"] == severity


def test_handler_rejects_invalid_severity(monkeypatch):
    mock_table = MagicMock()

    monkeypatch.setattr(
        handler,
        "get_table",
        lambda: mock_table,
    )

    response = handler.handler(
        build_event(severity="urgent"),
        None,
    )

    assert response["statusCode"] == 400

    body = json.loads(response["body"])

    assert body["error"] == "Invalid operational event"
    assert "details" in body

    details = body["details"]

    assert any(
        detail["loc"] == ["severity"]
        and detail["type"] == "enum"
        for detail in details
    )

    mock_table.put_item.assert_not_called()


@pytest.mark.parametrize(
    "missing_field",
    [
        "site_id",
        "event_type",
        "severity",
        "message",
    ],
)
def test_handler_rejects_missing_required_field(
    monkeypatch,
    missing_field,
):
    mock_table = MagicMock()

    monkeypatch.setattr(
        handler,
        "get_table",
        lambda: mock_table,
    )

    payload = {
        "site_id": "RIG-001",
        "event_type": "connectivity_degradation",
        "severity": "high",
        "message": "Connectivity degradation detected",
    }

    del payload[missing_field]

    event = {
        "body": json.dumps(payload),
    }

    response = handler.handler(
        event,
        None,
    )

    assert response["statusCode"] == 400

    body = json.loads(response["body"])

    assert body["error"] == "Invalid operational event"
    assert "details" in body

    details = body["details"]

    assert any(
        detail["loc"] == [missing_field]
        and detail["type"] == "missing"
        for detail in details
    )

    mock_table.put_item.assert_not_called()