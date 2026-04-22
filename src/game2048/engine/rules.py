"""Enums and constants for the 2048 engine."""

from __future__ import annotations

from enum import StrEnum

BOARD_SIZE = 4
WIN_TILE = 2048
DEFAULT_FOUR_PROB = 0.1


class Direction(StrEnum):
    """A move direction. String values match the API payload."""

    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class GameStatus(StrEnum):
    """Overall state of a game."""

    PLAYING = "playing"
    WON = "won"
    LOST = "lost"
