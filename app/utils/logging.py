import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

_REQUEST_FIELDS = ("method", "path", "status_code", "duration_ms", "remote_addr")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in _REQUEST_FIELDS:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(app) -> None:
    formatter = JsonFormatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    handlers = [stream_handler]

    # Skip the file handler under pytest — no need to write log files to
    # disk on every test run.
    if not app.config.get("TESTING"):
        log_dir = os.environ.get("LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")

        # RotatingFileHandler assumes a single writer — fine for the one
        # flask-run dev process this project runs locally, but multiple
        # gunicorn workers writing the same file concurrently would
        # interleave at rotation boundaries. A real multi-worker deployment
        # would log to stdout only and let the container runtime aggregate
        # it instead.
        file_handler = RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=3)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    app.logger.handlers = handlers
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False

    # Replace werkzeug's plain-text access log with our structured one
    # (registered separately via request hooks) instead of logging twice.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
