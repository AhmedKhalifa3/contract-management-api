import json
import logging

from app.utils.logging import JsonFormatter


def _make_record(**extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request completed",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_produces_valid_json_with_base_fields():
    record = _make_record()
    output = json.loads(JsonFormatter().format(record))

    assert output["message"] == "request completed"
    assert output["level"] == "INFO"
    assert output["logger"] == "app"
    assert "timestamp" in output


def test_json_formatter_includes_request_fields_when_present():
    record = _make_record(method="GET", path="/api/contracts", status_code=200, duration_ms=12.3)
    output = json.loads(JsonFormatter().format(record))

    assert output["method"] == "GET"
    assert output["path"] == "/api/contracts"
    assert output["status_code"] == 200
    assert output["duration_ms"] == 12.3


def test_json_formatter_omits_request_fields_when_absent():
    output = json.loads(JsonFormatter().format(_make_record()))
    assert "method" not in output
    assert "status_code" not in output
