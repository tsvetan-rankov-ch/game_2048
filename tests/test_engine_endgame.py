"""Endgame detection tests, mirroring the win/lose examples in the requirements doc."""

from __future__ import annotations

from game2048.engine.board import board_from_list, has_2048, has_moves, status
from game2048.engine.rules import GameStatus


def _b(cells):
    return board_from_list(cells)


def test_lose_when_board_full_and_no_merges_available():
    board = _b(
        [
            [2, 4, 2, 4],
            [4, 2, 4, 2],
            [2, 4, 2, 4],
            [4, 2, 4, 2],
        ]
    )
    assert has_moves(board) is False
    assert status(board) is GameStatus.LOST


def test_win_when_any_tile_is_2048():
    board = _b(
        [
            [4, None, None, 2],
            [2048, None, None, None],
            [4, 2, None, None],
            [4, None, None, None],
        ]
    )
    assert has_2048(board) is True
    assert status(board) is GameStatus.WON


def test_playing_when_moves_are_possible():
    board = _b(
        [
            [2, 2, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
        ]
    )
    assert has_moves(board) is True
    assert status(board) is GameStatus.PLAYING


def test_full_board_with_adjacent_equal_tiles_is_not_lost():
    board = _b(
        [
            [2, 2, 4, 8],
            [4, 8, 16, 32],
            [8, 16, 32, 64],
            [16, 32, 64, 128],
        ]
    )
    assert has_moves(board) is True
    assert status(board) is GameStatus.PLAYING
