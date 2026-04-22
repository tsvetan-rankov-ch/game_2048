"""Pure game engine: no Flask, no I/O, no globals."""

from game2048.engine.board import has_2048, has_moves, move, spawn_tile, status
from game2048.engine.game import Game
from game2048.engine.rules import Direction, GameStatus

__all__ = [
    "Direction",
    "Game",
    "GameStatus",
    "has_2048",
    "has_moves",
    "move",
    "spawn_tile",
    "status",
]
