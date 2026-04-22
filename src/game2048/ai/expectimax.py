"""Expectimax search for 2048.

Player nodes maximize over the 4 directions. Chance nodes weight-average over
every possible tile spawn (`2` with probability `1 - four_prob`, `4` otherwise)
in every empty cell. Depth is controlled by iterative deepening with a wall-clock budget.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from game2048.ai.heuristics import evaluate
from game2048.ai.solver import Suggestion
from game2048.engine.board import Board, empty_cells, move
from game2048.engine.rules import DEFAULT_FOUR_PROB, Direction

log = logging.getLogger(__name__)


@dataclass
class ExpectimaxSolver:
    """Local, offline, deterministic Expectimax solver.

    `time_budget_ms` caps how long `suggest` is allowed to think. `max_depth` caps the
    deepest player-node ply the search will reach even if time permits (safety net).
    """

    name: str = "local"
    four_prob: float = DEFAULT_FOUR_PROB
    time_budget_ms: int = 150
    max_depth: int = 6

    def suggest(self, board: Board) -> Suggestion:
        start = time.perf_counter()
        deadline = start + (self.time_budget_ms / 1000.0)

        best_scores: dict[Direction, float] = {}
        depth = 1
        while depth <= self.max_depth and time.perf_counter() < deadline:
            try:
                scores = self._evaluate_all_moves(board, depth, deadline)
            except _TimeUp:
                break
            best_scores = scores
            depth += 1

        if not best_scores:
            # No moves at all: return any direction, the UI will handle endgame.
            best_scores = {d: float("-inf") for d in Direction}

        best_direction = max(best_scores.items(), key=lambda kv: kv[1])[0]
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        log.info(
            "expectimax: depth=%d best=%s elapsed_ms=%d",
            depth - 1,
            best_direction.value,
            elapsed_ms,
        )
        return Suggestion(
            direction=best_direction,
            provider=self.name,
            scores=best_scores,
            elapsed_ms=elapsed_ms,
        )

    def _evaluate_all_moves(
        self, board: Board, depth: int, deadline: float
    ) -> dict[Direction, float]:
        scores: dict[Direction, float] = {}
        for direction in Direction:
            next_board, _, changed = move(board, direction)
            if not changed:
                scores[direction] = float("-inf")
                continue
            scores[direction] = self._chance(next_board, depth - 1, deadline)
        return scores

    def _player(self, board: Board, depth: int, deadline: float) -> float:
        if depth <= 0:
            return evaluate(board)
        if time.perf_counter() >= deadline:
            raise _TimeUp

        best = float("-inf")
        any_move = False
        for direction in Direction:
            next_board, _, changed = move(board, direction)
            if not changed:
                continue
            any_move = True
            best = max(best, self._chance(next_board, depth - 1, deadline))
        if not any_move:
            return evaluate(board)
        return best

    def _chance(self, board: Board, depth: int, deadline: float) -> float:
        if depth <= 0:
            return evaluate(board)
        if time.perf_counter() >= deadline:
            raise _TimeUp

        empties = empty_cells(board)
        if not empties:
            return self._player(board, depth, deadline)

        # Limit branching factor for speed by sampling up to N empty cells uniformly.
        # For small boards (4x4) the number of empties is <= 16, so we evaluate all of them.
        total = 0.0
        for r, c in empties:
            b2 = _place(board, r, c, 2)
            b4 = _place(board, r, c, 4)
            total += (1.0 - self.four_prob) * self._player(b2, depth - 1, deadline)
            total += self.four_prob * self._player(b4, depth - 1, deadline)
        return total / len(empties)


class _TimeUp(Exception):
    """Raised internally when the wall-clock budget is exhausted."""


def _place(board: Board, r: int, c: int, value: int) -> Board:
    return tuple(
        tuple(value if (rr == r and cc == c) else board[rr][cc] for cc in range(len(board)))
        for rr in range(len(board))
    )
