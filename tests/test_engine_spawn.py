"""Tests for `spawn_tile` with a seeded RNG."""

from __future__ import annotations

import random
from collections import Counter

from game2048.engine.board import board_from_list, board_to_list, empty_cells, spawn_tile


def test_spawn_places_exactly_one_tile_in_an_empty_cell():
    board = board_from_list([[None] * 4 for _ in range(4)])
    rng = random.Random(1234)
    new_board = spawn_tile(board, rng, four_prob=0.1)

    empties_before = 16
    empties_after = len(empty_cells(new_board))
    assert empties_after == empties_before - 1
    cells = board_to_list(new_board)
    occupied = [v for row in cells for v in row if v]
    assert len(occupied) == 1
    assert occupied[0] in (2, 4)


def test_spawn_distribution_respects_four_prob():
    rng = random.Random(42)
    four_prob = 0.25
    samples = 2000
    fours = 0
    board = board_from_list([[None] * 4 for _ in range(4)])
    for _ in range(samples):
        new = spawn_tile(board, rng, four_prob=four_prob)
        v = next(v for row in new for v in row if v != 0)
        if v == 4:
            fours += 1

    # Allow generous tolerance so the test is stable.
    expected = samples * four_prob
    assert abs(fours - expected) < 0.05 * samples


def test_spawn_is_deterministic_with_same_seed():
    board = board_from_list([[None] * 4 for _ in range(4)])
    rng1 = random.Random(7)
    rng2 = random.Random(7)
    assert spawn_tile(board, rng1, 0.1) == spawn_tile(board, rng2, 0.1)


def test_spawn_uses_all_empty_cells_over_time():
    rng = random.Random(0)
    board = board_from_list([[None] * 4 for _ in range(4)])
    positions: Counter[tuple[int, int]] = Counter()
    for _ in range(2000):
        new = spawn_tile(board, rng, 0.0)
        (r, c) = next((r, c) for r, row in enumerate(new) for c, v in enumerate(row) if v)
        positions[(r, c)] += 1
    # All 16 cells should have been chosen at least once.
    assert len(positions) == 16
