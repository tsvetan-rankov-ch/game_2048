"""The `Game` class: stateful wrapper around the pure engine functions.

Keeps the move history ready for a future `undo()` without shipping it in the UI.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from game2048.engine.board import (
    Board,
    board_to_list,
    initial_board,
    move,
    spawn_tile,
    status,
)
from game2048.engine.rules import DEFAULT_FOUR_PROB, Direction, GameStatus


@dataclass
class MoveRecord:
    """A single applied move. Stored to enable a future `undo()` trivially."""

    direction: Direction
    board_before: Board
    board_after_move: Board
    board_after_spawn: Board
    score_delta: int


@dataclass
class Game:
    """A single 2048 game session."""

    four_prob: float = DEFAULT_FOUR_PROB
    seed: int | None = None
    board: Board = field(init=False)
    score: int = 0
    status: GameStatus = GameStatus.PLAYING
    history: list[MoveRecord] = field(default_factory=list)
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not 0.0 <= self.four_prob <= 1.0:
            raise ValueError("four_prob must be in [0.0, 1.0]")
        self._rng = random.Random(self.seed)
        self.board = initial_board(self._rng, self.four_prob)
        self.status = status(self.board)

    def reset(self, four_prob: float | None = None, seed: int | None = None) -> None:
        """Start a fresh game. Optionally change spawn probability / seed."""
        if four_prob is not None:
            if not 0.0 <= four_prob <= 1.0:
                raise ValueError("four_prob must be in [0.0, 1.0]")
            self.four_prob = four_prob
        if seed is not None:
            self.seed = seed
            self._rng = random.Random(seed)
        self.board = initial_board(self._rng, self.four_prob)
        self.score = 0
        self.status = status(self.board)
        self.history.clear()

    def play(self, direction: Direction) -> bool:
        """Apply a move, spawn a new tile if it changed, refresh status.

        Returns True if the board changed (i.e. it was a valid move), False otherwise.
        No-op moves do not spawn a tile and are not added to history.
        """
        if self.status is not GameStatus.PLAYING:
            return False

        before = self.board
        after_move, delta, changed = move(before, direction)
        if not changed:
            return False

        after_spawn = (
            spawn_tile(after_move, self._rng, self.four_prob)
            if any(0 in row for row in after_move)
            else after_move
        )
        self.board = after_spawn
        self.score += delta
        self.status = status(self.board)
        self.history.append(
            MoveRecord(
                direction=direction,
                board_before=before,
                board_after_move=after_move,
                board_after_spawn=after_spawn,
                score_delta=delta,
            )
        )
        return True

    def snapshot(self) -> dict:
        """Return a JSON-serializable view of the current state."""
        return {
            "board": board_to_list(self.board),
            "score": self.score,
            "status": self.status.value,
            "four_prob": self.four_prob,
            "moves": len(self.history),
        }
