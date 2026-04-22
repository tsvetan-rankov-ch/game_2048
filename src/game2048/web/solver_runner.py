"""Background thread that runs the local solver, applying a move every `tick_s` seconds.

Only the local Expectimax solver is allowed here — running LLM solvers in auto-mode
would burn money and hit rate limits. The Flask route rejects non-local providers.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass, field

from game2048.ai.solver import Solver
from game2048.engine.game import Game
from game2048.engine.rules import GameStatus

log = logging.getLogger(__name__)


@dataclass
class SolveLogEntry:
    move_index: int
    direction: str
    score: int
    status: str


@dataclass
class SolveRunner:
    """Owns the solver thread and its stop signal. One-at-a-time."""

    game: Game
    lock: threading.Lock
    tick_s: float = 0.5  # 2 moves/sec
    max_log_entries: int = 50
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _stop: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _log: deque[SolveLogEntry] = field(default_factory=deque, init=False, repr=False)
    _running_provider: str | None = field(default=None, init=False, repr=False)

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def log_entries(self) -> list[SolveLogEntry]:
        return list(self._log)

    def running_provider(self) -> str | None:
        return self._running_provider

    def start(self, solver: Solver) -> None:
        if self.is_running():
            return
        self._stop.clear()
        self._log.clear()
        self._running_provider = solver.name
        self._thread = threading.Thread(
            target=self._run, args=(solver,), name="solve-runner", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._running_provider = None

    def _run(self, solver: Solver) -> None:
        while not self._stop.is_set():
            with self.lock:
                if self.game.status is not GameStatus.PLAYING:
                    log.info("solve-runner: game over (%s), stopping", self.game.status.value)
                    break
                board = self.game.board
            try:
                suggestion = solver.suggest(board)
            except Exception:
                log.exception("solve-runner: solver failed, stopping")
                break

            with self.lock:
                played = self.game.play(suggestion.direction)
                if not played:
                    log.info("solve-runner: suggested move invalid, stopping")
                    break
                entry = SolveLogEntry(
                    move_index=len(self.game.history),
                    direction=suggestion.direction.value,
                    score=self.game.score,
                    status=self.game.status.value,
                )
                self._log.append(entry)
                if len(self._log) > self.max_log_entries:
                    self._log.popleft()

            if self._stop.wait(self.tick_s):
                break
        self._running_provider = None
