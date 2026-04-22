"""Application settings, loaded from environment variables (with optional `.env`).

Secrets (API keys) are held in memory only. They are never persisted by the app and
never echoed into logs or HTTP responses (see `logging_setup.RedactionFilter`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

_DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
_DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5"
_DEFAULT_GOOGLE_MODEL = "gemini-2.0-flash"
_DEFAULT_AI_BUDGET_MS = 150
_DEFAULT_PORT = 5050


@dataclass(frozen=True)
class ProviderConfig:
    """Static, non-secret configuration for a single LLM provider.

    `has_key` reflects whether an API key is present in the environment at startup.
    The key itself is fetched lazily from `os.environ` by the adapter so tests can
    override it without reloading settings.
    """

    name: str
    env_key_var: str
    model: str

    @property
    def has_key(self) -> bool:
        value = os.environ.get(self.env_key_var, "")
        return bool(value and value.strip())


@dataclass(frozen=True)
class Settings:
    """Top-level application settings. Contains NO secret values."""

    openai: ProviderConfig
    anthropic: ProviderConfig
    google: ProviderConfig
    ai_budget_ms: int
    port: int

    @property
    def providers(self) -> tuple[ProviderConfig, ...]:
        return (self.openai, self.anthropic, self.google)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def load_settings() -> Settings:
    """Load settings from environment, optionally hydrated from a local `.env` file.

    `.env` is loaded if present but is never required. It is listed in `.gitignore`.
    """
    load_dotenv(override=False)

    openai = ProviderConfig(
        name="openai",
        env_key_var="OPENAI_API_KEY",
        model=os.environ.get("OPENAI_MODEL", _DEFAULT_OPENAI_MODEL).strip()
        or _DEFAULT_OPENAI_MODEL,
    )
    anthropic = ProviderConfig(
        name="anthropic",
        env_key_var="ANTHROPIC_API_KEY",
        model=os.environ.get("ANTHROPIC_MODEL", _DEFAULT_ANTHROPIC_MODEL).strip()
        or _DEFAULT_ANTHROPIC_MODEL,
    )
    google = ProviderConfig(
        name="google",
        env_key_var="GOOGLE_API_KEY",
        model=os.environ.get("GOOGLE_MODEL", _DEFAULT_GOOGLE_MODEL).strip()
        or _DEFAULT_GOOGLE_MODEL,
    )

    return Settings(
        openai=openai,
        anthropic=anthropic,
        google=google,
        ai_budget_ms=max(1, _env_int("AI_BUDGET_MS", _DEFAULT_AI_BUDGET_MS)),
        port=_env_int("FLASK_RUN_PORT", _DEFAULT_PORT),
    )
