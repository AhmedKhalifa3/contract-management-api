from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db, limiter

health_bp = Blueprint("health", __name__)


@health_bp.get("/healthz")
@limiter.exempt
def healthz():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 — any DB failure at all means unhealthy
        return jsonify({"status": "error", "message": "database unreachable"}), 503
    return jsonify({"status": "ok"})
