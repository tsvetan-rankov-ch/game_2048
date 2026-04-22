"""Solver registry: name -> factory. Also reports which providers have keys set."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from game2048.ai.expectimax import ExpectimaxSolver
from game2048.ai.llm.anthropic import AnthropicSolver
from game2048.ai.llm.google import GoogleSolver
from game2048.ai.llm.openai import OpenAISolver
from game2048.ai.solver import Solver, SolverError
from game2048.config import Settings

LOCAL = "local"
OPENAI = "openai"
ANTHROPIC = "anthropic"
GOOGLE = "google"


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    kind: str
    label: str
    configured: bool


class SolverRegistry:
    """Owns the factories for each known provider."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._factories: dict[str, Callable[[], Solver]] = {
            LOCAL: lambda: ExpectimaxSolver(time_budget_ms=settings.ai_budget_ms),
            OPENAI: lambda: OpenAISolver(model=settings.openai.model),
            ANTHROPIC: lambda: AnthropicSolver(model=settings.anthropic.model),
            GOOGLE: lambda: GoogleSolver(model=settings.google.model),
        }

    def get(self, name: str) -> Solver:
        if name not in self._factories:
            raise SolverError(f"Unknown provider: {name}")
        return self._factories[name]()

    def provider_info(self) -> list[ProviderInfo]:
        return [
            ProviderInfo(name=LOCAL, kind="local", label="Local (Expectimax)", configured=True),
            ProviderInfo(
                name=OPENAI,
                kind="llm",
                label="OpenAI",
                configured=self._settings.openai.has_key,
            ),
            ProviderInfo(
                name=ANTHROPIC,
                kind="llm",
                label="Anthropic",
                configured=self._settings.anthropic.has_key,
            ),
            ProviderInfo(
                name=GOOGLE,
                kind="llm",
                label="Google",
                configured=self._settings.google.has_key,
            ),
        ]

    def is_local(self, name: str) -> bool:
        return name == LOCAL
