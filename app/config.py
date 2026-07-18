import os


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Empty string disables Sentry entirely — sentry_sdk.init() no-ops on a
    # falsy DSN, so local dev/CI never needs a real Sentry account.
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
    SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg2://contract_user:contract_pass@localhost:5433/contract_db_test",
    )


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
