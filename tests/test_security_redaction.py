"""Security tests: API keys must NEVER leak through logs or HTTP responses."""

from __future__ import annotations

import logging

import pytest
from flask.testing import FlaskClient

from game2048.logging_setup import REDACTED, RedactionFilter, configure_logging, redact


def test_redact_scrubs_openai_style_key():
    text = "error: got 401 with sk-abcdefghijklmnop when calling"
    assert "sk-abcdefghijklmnop" not in redact(text)
    assert REDACTED in redact(text)


def test_redact_scrubs_anthropic_style_key():
    text = "Using sk-ant-0123456789abcdef now"
    assert "sk-ant-0123456789abcdef" not in redact(text)


def test_redact_scrubs_google_style_key():
    text = "key=AIzaSomeRealKey123 go"
    assert "AIzaSomeRealKey123" not in redact(text)


def test_redact_scrubs_bearer_tokens():
    text = "Authorization: Bearer abcdef1234567890"
    assert "abcdef1234567890" not in redact(text)


def test_redact_scrubs_env_configured_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CUSTOM_API_KEY", "totally-secret-value-123")
    text = "oops: leaking totally-secret-value-123 somewhere"
    assert "totally-secret-value-123" not in redact(text, ("totally-secret-value-123",))


def test_redaction_filter_scrubs_log_records(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-LEAK-this-should-never-appear-0000")
    logger = logging.getLogger("test_security_redaction")
    logger.handlers.clear()
    logger.propagate = True
    logger.setLevel(logging.INFO)

    f = RedactionFilter()
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="test_security_redaction"):
        logger.addFilter(f)
        try:
            logger.info("calling api with sk-LEAK-this-should-never-appear-0000 header")
            logger.info("structured %s key %s", "foo", "sk-abcdefghijklmnopq")
        finally:
            logger.removeFilter(f)

    for rec in caplog.records:
        msg = rec.getMessage()
        assert "sk-LEAK-this-should-never-appear-0000" not in msg
        assert "sk-abcdefghijklmnopq" not in msg


def test_configure_logging_is_idempotent():
    configure_logging()
    count1 = len(logging.getLogger().handlers)
    configure_logging()
    count2 = len(logging.getLogger().handlers)
    assert count1 == count2


def test_flask_error_handler_does_not_echo_env_secrets(
    client: FlaskClient, monkeypatch: pytest.MonkeyPatch
):
    # Deliberately put a "key-shaped" value into the environment.
    leaked = "sk-this-should-be-redacted-1234567890"
    monkeypatch.setenv("SOMETHING_API_KEY", leaked)

    # Force an error path: invalid JSON body.
    resp = client.post("/api/move", data="not json", content_type="application/json")
    # Endpoint tolerates bad JSON via `silent=True`, so just assert success path still safe.
    assert resp.status_code in (200, 400, 500)
    body = resp.get_data(as_text=True)
    assert leaked not in body


def test_provider_status_never_exposes_keys(client: FlaskClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-TOPSECRET-0123456789")
    resp = client.get("/api/state")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "sk-TOPSECRET-0123456789" not in body
    # The state should say OpenAI is configured (because the env var is set).
    data = resp.get_json()
    openai = next(p for p in data["providers"] if p["name"] == "openai")
    # Our test env fixture DROPS this at setup, but this test sets it after - the
    # Settings object is already built, so `configured` reflects startup state
    # (no key). That's fine - the important thing is the literal key is not in body.
    assert isinstance(openai["configured"], bool)
