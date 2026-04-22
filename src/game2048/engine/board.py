"""Pure board operations for 2048.

The board is an immutable `tuple[tuple[int, ...], ...]` of shape `BOARD_SIZE x BOARD_SIZE`.
`0` denotes an empty cell. All functions here are referentially transparent; the only
randomness lives in `spawn_tile`, which takes an injected `random.Random` instance.
"""

from __future__ import annotations

import random

from game2048.engine.rules import BOARD_SIZE, DEFAULT_FOUR_PROB, WIN_TILE, Direction, GameStatus

Row = tuple[int, ...]
Board = tuple[Row, ...]


def empty_board() -> Board:
    return tuple(tuple(0 for _ in range(BOARD_SIZE)) for _ in range(BOARD_SIZE))


def board_from_list(cells: list[list[int | None]]) -> Board:
    """Convert a list-of-lists (with `None` = empty) into a `Board`."""
    if len(cells) != BOARD_SIZE or any(len(row) != BOARD_SIZE for row in cells):
        raise ValueError(f"Board must be {BOARD_SIZE}x{BOARD_SIZE}")
    return tuple(tuple((v or 0) for v in row) for row in cells)


def board_to_list(board: Board) -> list[list[int | None]]:
    """Convert a `Board` back to list-of-lists form with `None` for empty cells."""
    return [[(v if v else None) for v in row] for row in board]


def empty_cells(board: Board) -> list[tuple[int, int]]:
    return [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if board[r][c] == 0]


def _collapse_left(row: Row) -> tuple[Row, int]:
    """Slide + merge a single row to the left. Returns (new_row, score_delta).

    Rules:
      - Non-zero tiles slide left, keeping order.
      - A pair of equal adjacent tiles merges into their sum; each tile merges at most once per move.
      - Merged tiles contribute their new value to the score (classic 2048 scoring).
    """
    compact = [v for v in row if v != 0]
    merged: list[int] = []
    score = 0
    i = 0
    while i < len(compact):
        if i + 1 < len(compact) and compact[i] == compact[i + 1]:
            new_val = compact[i] * 2
            merged.append(new_val)
            score += new_val
            i += 2
        else:
            merged.append(compact[i])
            i += 1
    merged.extend(0 for _ in range(BOARD_SIZE - len(merged)))
    return tuple(merged), score


def _transpose(board: Board) -> Board:
    return tuple(tuple(board[r][c] for r in range(BOARD_SIZE)) for c in range(BOARD_SIZE))


def _reverse_rows(board: Board) -> Board:
    return tuple(tuple(reversed(row)) for row in board)


def move(board: Board, direction: Direction) -> tuple[Board, int, bool]:
    """Apply `direction` to `board`. Returns (new_board, score_delta, changed).

    If the move does not change the board, `changed` is `False` and `new_board == board`.
    No random spawning happens here; callers decide whether to spawn.
    """
    if direction is Direction.LEFT:
        rows_in = board
    elif direction is Direction.RIGHT:
        rows_in = _reverse_rows(board)
    elif direction is Direction.UP:
        rows_in = _transpose(board)
    elif direction is Direction.DOWN:
        rows_in = _reverse_rows(_transpose(board))
    else:  # pragma: no cover - defensive
        raise ValueError(f"Unknown direction: {direction!r}")

    collapsed_rows: list[Row] = []
    total_score = 0
    for row in rows_in:
        new_row, score = _collapse_left(row)
        collapsed_rows.append(new_row)
        total_score += score

    collapsed: Board = tuple(collapsed_rows)

    if direction is Direction.LEFT:
        new_board = collapsed
    elif direction is Direction.RIGHT:
        new_board = _reverse_rows(collapsed)
    elif direction is Direction.UP:
        new_board = _transpose(collapsed)
    else:
        new_board = _transpose(_reverse_rows(collapsed))

    return new_board, total_score, new_board != board


def spawn_tile(
    board: Board,
    rng: random.Random,
    four_prob: float = DEFAULT_FOUR_PROB,
) -> Board:
    """Place a `2` or `4` at a uniformly-chosen empty cell.

    Raises `ValueError` if the board is full. The caller should check first.
    """
    cells = empty_cells(board)
    if not cells:
        raise ValueError("No empty cells to spawn into")
    r, c = rng.choice(cells)
    value = 4 if rng.random() < four_prob else 2
    return tuple(
        tuple(value if (rr == r and cc == c) else board[rr][cc] for cc in range(BOARD_SIZE))
        for rr in range(BOARD_SIZE)
    )


def has_moves(board: Board) -> bool:
    """True if any of the 4 directions would change the board."""
    if empty_cells(board):
        return True
    for direction in Direction:
        _, _, changed = move(board, direction)
        if changed:
            return True
    return False


def has_2048(board: Board) -> bool:
    return any(v >= WIN_TILE for row in board for v in row)


def status(board: Board) -> GameStatus:
    if has_2048(board):
        return GameStatus.WON
    if not has_moves(board):
        return GameStatus.LOST
    return GameStatus.PLAYING


def initial_board(
    rng: random.Random,
    four_prob: float = DEFAULT_FOUR_PROB,
    starting_tiles: int = 2,
) -> Board:
    """Classic start: an empty board with `starting_tiles` spawned tiles."""
    board = empty_board()
    for _ in range(starting_tiles):
        board = spawn_tile(board, rng, four_prob)
    return board
