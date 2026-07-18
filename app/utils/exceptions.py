class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""


class AppValidationError(Exception):
    """Raised for business-rule validation failures not caught by Pydantic
    (e.g. cross-field checks that depend on existing DB state)."""
