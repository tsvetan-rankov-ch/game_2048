"""Golden tests for moves, mirroring the examples in `2048 requirements.md`."""

from __future__ import annotations

import pytest

from game2048.engine.board import board_from_list, board_to_list, move
from game2048.engine.rules import Direction


def _b(cells: list[list[int | None]]):
    return board_from_list(cells)


def test_move_left_requirements_example():
    before = _b(
        [
            [None, 8, 2, 2],
            [4, 2, None, 2],
            [None, None, None, None],
            [None, None, None, 2],
        ]
    )
    expected_after = _b(
        [
            [8, 4, None, None],
            [4, 4, None, None],
            [None, None, None, None],
            [2, None, None, None],
        ]
    )
    after, delta, changed = move(before, Direction.LEFT)
    assert after == expected_after
    assert changed is True
    # merges: 2+2=4 (row0) and 2+2=4 (row1). score = 8.
    assert delta == 8


def test_move_right_requirements_example():
    before = _b(
        [
            [None, 8, 2, 2],
            [4, 2, None, 2],
            [None, None, None, None],
            [None, None, None, 2],
        ]
    )
    expected_after = _b(
        [
            [None, None, 8, 4],
            [None, None, 4, 4],
            [None, None, None, None],
            [None, None, None, 2],
        ]
    )
    after, delta, changed = move(before, Direction.RIGHT)
    assert after == expected_after
    assert changed is True
    assert delta == 8


def test_move_up_requirements_example():
    before = _b(
        [
            [None, 8, 2, 2],
            [4, 2, None, 2],
            [None, None, None, None],
            [None, None, None, 2],
        ]
    )
    expected_after = _b(
        [
            [4, 8, 2, 4],
            [None, 2, None, 2],
            [None, None, None, None],
            [None, None, None, None],
        ]
    )
    after, _, changed = move(before, Direction.UP)
    assert after == expected_after
    assert changed is True


def test_move_down_mirrors_up():
    before = _b(
        [
            [None, 8, 2, 2],
            [4, 2, None, 2],
            [None, None, None, None],
            [None, None, None, 2],
        ]
    )
    # col 0 [0,4,0,0]   -> [0,0,0,4]
    # col 1 [8,2,0,0]   -> [0,0,8,2]
    # col 2 [2,0,0,0]   -> [0,0,0,2]
    # col 3 [2,2,0,2]   -> [0,0,2,4]  (two bottom 2s merge to 4; remaining 2 stacks above)
    expected_after = _b(
        [
            [None, None, None, None],
            [None, None, None, None],
            [None, 8, None, 2],
            [4, 2, 2, 4],
        ]
    )
    after, _, changed = move(before, Direction.DOWN)
    assert after == expected_after
    assert changed is True


def test_triple_merge_pairs_leftmost_first():
    # [2,2,2,0] -> [4,2,0,0] (classic 2048: merges happen once, left-biased)
    before = _b(
        [
            [2, 2, 2, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
        ]
    )
    after, delta, changed = move(before, Direction.LEFT)
    assert board_to_list(after)[0] == [4, 2, None, None]
    assert changed is True
    assert delta == 4


def test_quadruple_merges_into_two_pairs():
    before = _b(
        [[2, 2, 2, 2], [None, None, None, None], [None, None, None, None], [None, None, None, None]]
    )
    after, delta, _ = move(before, Direction.LEFT)
    assert board_to_list(after)[0] == [4, 4, None, None]
    assert delta == 8


def test_no_op_move_returns_changed_false():
    before = _b([[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]])
    after, delta, changed = move(before, Direction.LEFT)
    assert after == before
    assert delta == 0
    assert changed is False


@pytest.mark.parametrize("direction", list(Direction))
def test_empty_board_is_no_op_in_all_directions(direction: Direction):
    before = _b([[None] * 4 for _ in range(4)])
    after, delta, changed = move(before, direction)
    assert after == before
    assert delta == 0
    assert changed is False
