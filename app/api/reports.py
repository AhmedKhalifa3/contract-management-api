import io
from datetime import date, datetime

import numpy as np
import pandas as pd
from flask import Blueprint, Response, jsonify, request

from app.services import report_service
from app.utils.exceptions import AppValidationError

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


def _json_safe(value):
    # pandas/numpy scalars (int64, float64) and date objects aren't handled
    # by Flask's default JSON encoder the way the rest of this API expects
    # (dates would silently come out RFC-822 formatted instead of ISO, and
    # numpy ints raise "not JSON serializable" outright) — normalize both.
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def _respond(df: pd.DataFrame, filename_stem: str):
    fmt = request.args.get("format", default="json")
    if fmt not in ("json", "csv"):
        raise AppValidationError(f"unsupported format: {fmt}")

    if fmt == "csv":
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        return Response(
            buffer.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename_stem}.csv"
            },
        )

    records = [
        {key: _json_safe(value) for key, value in record.items()}
        for record in df.to_dict(orient="records")
    ]
    return jsonify(records)


@reports_bp.get("/value-by-category")
def value_by_category():
    df = report_service.value_by_category()
    return _respond(df, "value-by-category")


@reports_bp.get("/expiring-soon-summary")
def expiring_soon_summary():
    days = request.args.get("days", default=30, type=int)
    df = report_service.expiring_soon_summary(days)
    return _respond(df, "expiring-soon-summary")
