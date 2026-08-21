import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

import handler


def test_handler_creates_event(monkeypatch):
    mock_table = MagicMock()

    monkeypatch.setattr(
        handler,
        "get_table",
        lambda: mock_table,
    )

    event = {
        "body": json.dumps({
            "site_id": "RIG-001",
            "event_type": "connectivity_degradation",
            "severity": "high",
            "message": "Primary connectivity latency exceeded threshold",
        })
    }

    response = handler.handler(event, None)

    assert response["statusCode"] == 201

    body = json.loads(response["body"])

    assert body["status"] == "created"
    assert "event_id" in body

    mock_table.put_item.assert_called_once()