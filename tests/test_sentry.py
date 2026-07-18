def test_sentry_disabled_without_dsn(app):
    # Locks in the "no accidental data collection in local/CI runs" contract:
    # Sentry only activates when SENTRY_DSN is explicitly set.
    assert app.config["SENTRY_DSN"] == ""
