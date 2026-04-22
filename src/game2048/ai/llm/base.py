"""Shared base for LLM solvers.

Security contract:
  - Reads the API key lazily from `os.environ` per request (never stored on the adapter).
  - Refuses plain `http://` endpoints.
  - Hard 8-second timeout. No retries. No response caching.
  - Raises `LLMError` with a user-safe message on any failure. Internal exception details
    pass through the logging redaction filter (see `logging_setup.py`).
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import ClassVar

import httpx

from game2048.ai.solver import Solver, SolverError, Suggestion
from game2048.engine.board import Board
from game2048.engine.rules import Direction

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 8.0


class LLMError(SolverError):
    """Raised when an LLM adapter cannot produce a valid suggestion."""


def _ensure_https(url: str) -> None:
    if not url.lower().startswith("https://"):
        raise LLMError("Provider endpoint must use HTTPS")


def board_to_prompt_grid(board: Board) -> str:
    """Render the board as a 4x4 grid of integers, 0 for empty cells."""
    return "\n".join(" ".join(f"{v:>5}" for v in row) for row in board)


PROMPT_TEMPLATE = """You are an expert 2048 player. Analyze the 4x4 board below \
and respond with the single best move direction as STRICT JSON.

Rules reminder:
- Tiles slide in the chosen direction and equal adjacent tiles merge once per move.
- After a valid move a new 2 or 4 tile spawns at random. Goal: reach 2048.
- Only these directions are valid: UP, DOWN, LEFT, RIGHT.

Board (0 = empty):
{grid}

Respond with EXACTLY this JSON shape, nothing else:
{{"move": "UP" | "DOWN" | "LEFT" | "RIGHT"}}
"""


def build_prompt(board: Board) -> str:
    return PROMPT_TEMPLATE.format(grid=board_to_prompt_grid(board))


def parse_direction(text: str) -> Direction:
    """Parse the provider's text response into a `Direction`.

    We accept either strict JSON `{"move": "UP"}` or a plain token anywhere in the text,
    since providers sometimes wrap their output. Invalid input -> LLMError.
    """
    if not text or not text.strip():
        raise LLMError("Empty response from provider")

    cleaned = text.strip().strip("`")
    # Strip optional ```json fences.
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()

    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict) and "move" in obj:
            token = str(obj["move"]).strip().upper()
            return _token_to_direction(token)
    except (json.JSONDecodeError, ValueError):
        pass

    # Fall back: look for an uppercase direction word in the response.
    upper = text.upper()
    for token in ("UP", "DOWN", "LEFT", "RIGHT"):
        if token in upper:
            return _token_to_direction(token)

    raise LLMError("Provider response did not contain a valid move")


def _token_to_direction(token: str) -> Direction:
    mapping = {
        "UP": Direction.UP,
        "DOWN": Direction.DOWN,
        "LEFT": Direction.LEFT,
        "RIGHT": Direction.RIGHT,
    }
    if token not in mapping:
        raise LLMError(f"Unknown move token: {token}")
    return mapping[token]


@dataclass
class LLMSolver(Solver):
    """Base class — subclasses only need to implement `_call_api`."""

    name: ClassVar[str] = "llm"
    env_key_var: ClassVar[str] = "API_KEY"

    model: str = ""
    endpoint: str = ""
    timeout_s: float = DEFAULT_TIMEOUT_S

    def __post_init__(self) -> None:
        _ensure_https(self.endpoint)

    def _api_key(self) -> str:
        key = os.environ.get(self.env_key_var, "").strip()
        if not key:
            raise LLMError(f"{self.name}: API key not configured ({self.env_key_var})")
        return key

    def suggest(self, board: Board) -> Suggestion:
        start = time.perf_counter()
        prompt = build_prompt(board)
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                text = self._call_api(client, prompt)
        except LLMError:
            raise
        except httpx.TimeoutException as exc:
            raise LLMError(f"{self.name}: request timed out") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"{self.name}: network error") from exc
        except Exception as exc:  # defensive; never expose internals
            log.exception("%s: unexpected error", self.name)
            raise LLMError(f"{self.name}: unexpected error") from exc

        direction = parse_direction(text)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        log.info("%s: suggested=%s elapsed_ms=%d", self.name, direction.value, elapsed_ms)
        return Suggestion(
            direction=direction,
            provider=self.name,
            scores=None,
            elapsed_ms=elapsed_ms,
        )

    def _call_api(self, client: httpx.Client, prompt: str) -> str:
        raise NotImplementedError
