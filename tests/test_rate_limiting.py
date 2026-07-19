def test_rate_limiting_disabled_under_testing(app):
    # Mirrors the Sentry "disabled without config" test — locks in that the
    # test suite (which fires many requests per test run by design) never
    # gets rate-limited by accident.
    assert app.config["RATELIMIT_ENABLED"] is False
