from flask import Flask

from app.api.contracts import contracts_bp
from app.api.health import health_bp
from app.api.reports import reports_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(contracts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(health_bp)
