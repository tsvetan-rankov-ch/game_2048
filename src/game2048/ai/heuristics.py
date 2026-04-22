"""Board evaluation heuristics for Expectimax.

The weighted sum below is informed by the literature on 2048 AIs
(see: https://stackoverflow.com/questions/22342854/what-is-the-optimal-algorithm-for-the-game-2048).
We don't tune the weights — they just need to be reasonable.
"""

from __future__ import annotations

import math

from game2048.engine.board import Board
from game2048.engine.rules import BOARD_SIZE

W_EMPTY = 2.7
W_MONOTONICITY = 1.0
W_SMOOTHNESS = 0.1
W_MAX_CORNER = 1.0


def _log2(v: int) -> float:
    return math.log2(v) if v > 0 else 0.0


def empty_count(board: Board) -> int:
    return sum(1 for row in board for v in row if v == 0)


def monotonicity(board: Board) -> float:
    """Reward rows/columns that are monotonic (sorted) in either direction.

    Computed in log2 space so higher tiles dominate, following standard practice.
    Returns the maximum monotonicity score across both directions in both axes.
    """
    totals = [0.0, 0.0, 0.0, 0.0]
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE - 1):
            a = _log2(board[r][c])
            b = _log2(board[r][c + 1])
            if a > b:
                totals[0] += b - a
            else:
                totals[1] += a - b
    for c in range(BOARD_SIZE):
        for r in range(BOARD_SIZE - 1):
            a = _log2(board[r][c])
            b = _log2(board[r + 1][c])
            if a > b:
                totals[2] += b - a
            else:
                totals[3] += a - b
    return max(totals[0], totals[1]) + max(totals[2], totals[3])


def smoothness(board: Board) -> float:
    """Negative sum of absolute log2 differences between neighbors.

    Smoother (values close to neighbors) is better, so the returned value is <= 0.
    """
    total = 0.0
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            v = board[r][c]
            if v == 0:
                continue
            lv = _log2(v)
            if c + 1 < BOARD_SIZE and board[r][c + 1] != 0:
                total -= abs(lv - _log2(board[r][c + 1]))
            if r + 1 < BOARD_SIZE and board[r + 1][c] != 0:
                total -= abs(lv - _log2(board[r + 1][c]))
    return total


def max_in_corner(board: Board) -> float:
    """Reward when the highest tile is in a corner (encourages the 'snake' strategy)."""
    max_v = max(v for row in board for v in row)
    if max_v == 0:
        return 0.0
    corners = (
        board[0][0],
        board[0][BOARD_SIZE - 1],
        board[BOARD_SIZE - 1][0],
        board[BOARD_SIZE - 1][BOARD_SIZE - 1],
    )
    return _log2(max_v) if max_v in corners else 0.0


def evaluate(board: Board) -> float:
    return (
        W_EMPTY * empty_count(board)
        + W_MONOTONICITY * monotonicity(board)
        + W_SMOOTHNESS * smoothness(board)
        + W_MAX_CORNER * max_in_corner(board)
    )
