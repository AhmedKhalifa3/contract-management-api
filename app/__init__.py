import os

from flask import Flask, jsonify
from pydantic import ValidationError as PydanticValidationError

from app.config import config_by_name
from app.extensions import db, migrate
from app.utils.exceptions import AppValidationError, NotFoundError


def create_app(config_name: str | None = None) -> Flask:
    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401 — registers models with SQLAlchemy metadata
    from app.api import register_blueprints

    register_blueprints(app)
    _register_error_handlers(app)

    return app


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(PydanticValidationError)
    def handle_pydantic_error(err: PydanticValidationError):
        # err.errors() can include raw exception objects in 'ctx' for
        # custom validators, which jsonify can't serialize — strip to
        # the JSON-safe fields only.
        details = [
            {"loc": e["loc"], "msg": e["msg"], "type": e["type"]}
            for e in err.errors()
        ]
        return jsonify({"error": "validation_error", "details": details}), 400

    @app.errorhandler(AppValidationError)
    def handle_app_validation_error(err: AppValidationError):
        return jsonify({"error": "validation_error", "message": str(err)}), 400

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(err: NotFoundError):
        return jsonify({"error": "not_found", "message": str(err)}), 404
