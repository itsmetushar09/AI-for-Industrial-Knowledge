"""Phase 11 structured logging and request-correlation tests."""

import json
import logging

from fastapi.testclient import TestClient

from app.core.logging import JsonFormatter, bind_request_id, reset_request_id
from app.main import app


def test_json_formatter_includes_bound_request_id() -> None:
    token = bind_request_id("test-request-123")
    try:
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Safe event",
            args=(),
            exc_info=None,
        )
        record.event = "test_event"
        payload = json.loads(JsonFormatter().format(record))
    finally:
        reset_request_id(token)

    assert payload["request_id"] == "test-request-123"
    assert payload["event"] == "test_event"
    assert payload["message"] == "Safe event"


def test_http_middleware_echoes_safe_request_id(caplog) -> None:
    caplog.set_level(logging.INFO, logger="app.main")
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "browser-test-42"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "browser-test-42"
    completed = [
        record for record in caplog.records if getattr(record, "event", None) == "http_request_completed"
    ]
    assert completed
    assert completed[-1].status_code == 200
    assert completed[-1].duration_ms >= 0


def test_invalid_request_id_is_replaced() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "unsafe request id!"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "unsafe request id!"
    assert len(response.headers["x-request-id"]) == 36
