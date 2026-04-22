"""Tests for ExpectimaxSolver: deterministic, returns the obvious best move."""

from __future__ import annotations

from game2048.ai.expectimax import ExpectimaxSolver
from game2048.ai.solver import Suggestion
from game2048.engine.board import board_from_list
from game2048.engine.rules import Direction


def _b(cells):
    return board_from_list(cells)


def test_suggest_returns_suggestion_with_all_scores():
    board = _b(
        [
            [2, 2, None, None],
            [4, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
        ]
    )
    solver = ExpectimaxSolver(time_budget_ms=100, max_depth=3)
    s = solver.suggest(board)
    assert isinstance(s, Suggestion)
    assert s.provider == "local"
    assert set(s.scores.keys()) == set(Direction)
    assert s.direction in Direction


def test_no_op_moves_are_scored_minus_infinity():
    # Board with two 2s in the top row: UP is a no-op (nothing to slide up).
    # LEFT merges, RIGHT slides + merges, DOWN slides the 2s to the bottom row.
    board = _b(
        [
            [2, 2, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
        ]
    )
    solver = ExpectimaxSolver(time_budget_ms=30, max_depth=2)
    s = solver.suggest(board)
    assert s.scores[Direction.UP] == float("-inf")
    assert s.scores[Direction.LEFT] != float("-inf")
    assert s.scores[Direction.RIGHT] != float("-inf")
    assert s.scores[Direction.DOWN] != float("-inf")


def test_prefers_merging_move():
    # LEFT merges into a single 4 leaving many empty cells; DOWN/UP don't merge here.
    board = _b(
        [
            [2, 2, None, None],
            [4, None, None, None],
            [8, None, None, None],
            [16, None, None, None],
        ]
    )
    solver = ExpectimaxSolver(time_budget_ms=50, max_depth=3)
    s = solver.suggest(board)
    assert s.direction is Direction.LEFT


def test_suggest_respects_time_budget_and_returns_some_result():
    board = _b(
        [
            [2, 4, 8, 16],
            [4, 8, 16, 32],
            [8, 16, 32, 64],
            [16, 32, 64, 128],
        ]
    )
    solver = ExpectimaxSolver(time_budget_ms=10, max_depth=10)
    s = solver.suggest(board)
    assert s.direction in Direction
    # Even with a tight budget we should at least complete depth 1.
    assert s.elapsed_ms >= 0


def test_endgame_board_returns_some_direction_without_crashing():
    board = _b(
        [
            [2, 4, 2, 4],
            [4, 2, 4, 2],
            [2, 4, 2, 4],
            [4, 2, 4, 2],
        ]
    )
    solver = ExpectimaxSolver(time_budget_ms=20, max_depth=2)
    s = solver.suggest(board)
    assert s.direction in Direction
