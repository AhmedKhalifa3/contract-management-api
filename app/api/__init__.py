from flask import Flask

from app.api.contracts import contracts_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(contracts_bp)
