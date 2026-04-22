"""Tests for the stateful `Game` wrapper."""

from __future__ import annotations

from game2048.engine.board import empty_cells
from game2048.engine.game import Game
from game2048.engine.rules import Direction, GameStatus


def test_initial_game_has_two_tiles():
    g = Game(seed=1)
    assert len(empty_cells(g.board)) == 14
    assert g.score == 0
    assert g.status is GameStatus.PLAYING
    assert g.history == []


def test_invalid_move_does_not_spawn_or_record():
    g = Game(seed=1)
    # Force a board where LEFT is a no-op.
    g.board = tuple(
        (
            (2, 0, 0, 0),
            (0, 0, 0, 0),
            (0, 0, 0, 0),
            (0, 0, 0, 0),
        )
    )
    g.score = 0
    g.history.clear()
    played = g.play(Direction.LEFT)
    assert played is False
    assert g.history == []
    assert g.score == 0


def test_valid_move_spawns_and_records():
    g = Game(seed=1)
    g.board = tuple(
        (
            (2, 2, 0, 0),
            (0, 0, 0, 0),
            (0, 0, 0, 0),
            (0, 0, 0, 0),
        )
    )
    g.score = 0
    g.history.clear()
    played = g.play(Direction.LEFT)
    assert played is True
    assert g.score == 4  # 2+2 merge
    assert len(g.history) == 1
    rec = g.history[0]
    assert rec.direction is Direction.LEFT
    assert rec.score_delta == 4
    # Board after spawn should have one more non-empty cell than after_move.
    non_empty_move = sum(1 for row in rec.board_after_move for v in row if v)
    non_empty_spawn = sum(1 for row in rec.board_after_spawn for v in row if v)
    assert non_empty_spawn == non_empty_move + 1


def test_reset_changes_four_prob_and_clears_state():
    g = Game(seed=1)
    g.play(Direction.LEFT)
    g.reset(four_prob=0.5, seed=2)
    assert g.four_prob == 0.5
    assert g.score == 0
    assert g.history == []
    assert g.status is GameStatus.PLAYING


def test_game_snapshot_is_json_friendly():
    g = Game(seed=1)
    snap = g.snapshot()
    assert set(snap.keys()) == {"board", "score", "status", "four_prob", "moves"}
    assert snap["status"] in {"playing", "won", "lost"}
