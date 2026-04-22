"""The `Solver` protocol that every AI provider implements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from game2048.engine.board import Board
from game2048.engine.rules import Direction


class SolverError(Exception):
    """Raised by a solver when it cannot produce a suggestion (network, parse, etc.)."""


@dataclass(frozen=True)
class Suggestion:
    """What a solver returns to the UI for a `Hint` request.

    `scores` is optional: only local solvers produce calibrated per-direction scores.
    LLM adapters return the chosen direction and leave `scores = None`.
    """

    direction: Direction
    provider: str
    scores: dict[Direction, float] | None = None
    elapsed_ms: int = 0

    def to_json(self) -> dict:
        return {
            "direction": self.direction.value,
            "provider": self.provider,
            "scores": (
                {d.value: s for d, s in self.scores.items()} if self.scores is not None else None
            ),
            "elapsed_ms": self.elapsed_ms,
        }


class Solver(Protocol):
    """Pluggable AI. Synchronous by design: called from a Flask request handler."""

    name: str

    def suggest(self, board: Board) -> Suggestion: ...
