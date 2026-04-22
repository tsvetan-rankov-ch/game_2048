"""Shared pytest fixtures: Flask app + test client with a clean env."""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient

from game2048.config import Settings, load_settings
from game2048.web.app import create_app


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """A Settings object built from an environment with no provider keys set."""
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("AI_BUDGET_MS", "30")
    return load_settings()


@pytest.fixture
def client(settings: Settings) -> FlaskClient:
    app = create_app(settings)
    app.config["TESTING"] = True
    return app.test_client()
