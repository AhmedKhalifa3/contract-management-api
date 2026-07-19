import time

from flask import Flask, g, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)


def _endpoint_label() -> str:
    # request.path would create a new time series per contract UUID ever
    # requested (unbounded cardinality) — label with the route *pattern*
    # Flask matched against, not the resolved path.
    if request.url_rule is not None:
        return request.url_rule.rule
    return "unmatched"


def register_metrics(app: Flask) -> None:
    @app.before_request
    def _start_metrics_timer():
        g._metrics_start_time = time.monotonic()

    @app.after_request
    def _record_metrics(response):
        if request.path == "/metrics":
            return response

        duration = time.monotonic() - g._metrics_start_time
        endpoint = _endpoint_label()
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(
            duration
        )
        return response

    @app.route("/metrics")
    def metrics():
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}
