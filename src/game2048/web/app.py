"""Flask app factory + JSON API routes.

State model:
  - One global `Game` instance per app, guarded by a `threading.Lock`.
  - One background `SolveRunner` per app, sharing the same lock.
  - No sessions, no auth, no multi-user. Intended for a single local browser tab.
"""

from __future__ import annotations

import logging
import threading

from flask import Flask, current_app, jsonify, render_template, request

from game2048.ai.registry import LOCAL, SolverRegistry
from game2048.ai.solver import SolverError
from game2048.config import Settings
from game2048.engine.game import Game
from game2048.engine.rules import DEFAULT_FOUR_PROB, Direction
from game2048.web.solver_runner import SolveRunner

log = logging.getLogger(__name__)


def create_app(settings: Settings) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["JSON_SORT_KEYS"] = False

    game_lock = threading.Lock()
    game = Game(four_prob=DEFAULT_FOUR_PROB)
    registry = SolverRegistry(settings)
    solver_runner = SolveRunner(game=game, lock=game_lock)

    app.extensions["game2048"] = {
        "game": game,
        "lock": game_lock,
        "registry": registry,
        "solver_runner": solver_runner,
    }

    _register_routes(app)
    _register_error_handlers(app)
    return app


def _ext() -> dict:
    return current_app.extensions["game2048"]


def _state_payload() -> dict:
    ext = _ext()
    game: Game = ext["game"]
    registry: SolverRegistry = ext["registry"]
    runner: SolveRunner = ext["solver_runner"]
    return {
        **game.snapshot(),
        "providers": [
            {"name": p.name, "kind": p.kind, "label": p.label, "configured": p.configured}
            for p in registry.provider_info()
        ],
        "solving": runner.is_running(),
    }


def _register_routes(app: Flask) -> None:
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/state")
    def api_state():
        ext = _ext()
        with ext["lock"]:
            return jsonify(_state_payload())

    @app.post("/api/move")
    def api_move():
        ext = _ext()
        body = request.get_json(silent=True) or {}
        raw = str(body.get("direction", "")).lower()
        try:
            direction = Direction(raw)
        except ValueError:
            return jsonify({"error": "invalid_direction"}), 400

        with ext["lock"]:
            if ext["solver_runner"].is_running():
                return jsonify({"error": "solve_in_progress"}), 409
            played = ext["game"].play(direction)
            payload = {"changed": played, **_state_payload()}
        return jsonify(payload)

    @app.post("/api/new-game")
    def api_new_game():
        ext = _ext()
        body = request.get_json(silent=True) or {}
        four_prob = body.get("four_prob")
        if four_prob is not None:
            try:
                four_prob = float(four_prob)
            except (TypeError, ValueError):
                return jsonify({"error": "invalid_four_prob"}), 400
            if not 0.0 <= four_prob <= 1.0:
                return jsonify({"error": "invalid_four_prob"}), 400

        with ext["lock"]:
            ext["solver_runner"].stop()
            ext["game"].reset(four_prob=four_prob)
            return jsonify(_state_payload())

    @app.post("/api/hint")
    def api_hint():
        ext = _ext()
        body = request.get_json(silent=True) or {}
        provider = str(body.get("provider", LOCAL)).lower()

        try:
            solver = ext["registry"].get(provider)
        except SolverError as exc:
            return jsonify({"error": str(exc)}), 400

        with ext["lock"]:
            board = ext["game"].board

        try:
            suggestion = solver.suggest(board)
        except SolverError as exc:
            log.info("hint: provider=%s error=%s", provider, exc)
            return jsonify({"error": str(exc), "provider": provider}), 502

        return jsonify(suggestion.to_json())

    @app.post("/api/solve/start")
    def api_solve_start():
        ext = _ext()
        body = request.get_json(silent=True) or {}
        provider = str(body.get("provider", LOCAL)).lower()

        registry: SolverRegistry = ext["registry"]
        if not registry.is_local(provider):
            return jsonify({"error": "solve_local_only"}), 400

        try:
            solver = registry.get(provider)
        except SolverError as exc:
            return jsonify({"error": str(exc)}), 400

        with ext["lock"]:
            if ext["solver_runner"].is_running():
                return jsonify({"error": "already_running"}), 409
        ext["solver_runner"].start(solver)
        return jsonify({"running": True, "provider": provider})

    @app.post("/api/solve/stop")
    def api_solve_stop():
        ext = _ext()
        ext["solver_runner"].stop()
        return jsonify({"running": False})

    @app.get("/api/solve/status")
    def api_solve_status():
        ext = _ext()
        runner: SolveRunner = ext["solver_runner"]
        with ext["lock"]:
            state = _state_payload()
        state.update(
            {
                "running": runner.is_running(),
                "provider": runner.running_provider(),
                "log": [
                    {
                        "move_index": e.move_index,
                        "direction": e.direction,
                        "score": e.score,
                        "status": e.status,
                    }
                    for e in runner.log_entries()
                ],
            }
        )
        return jsonify(state)


def _register_error_handlers(app: Flask) -> None:
    from game2048.logging_setup import redact

    @app.errorhandler(Exception)
    def handle_any(exc: Exception):
        log.exception("unhandled error")
        # Never echo exception details verbatim (may contain keys or internals).
        msg = redact(str(exc))
        if len(msg) > 200:
            msg = msg[:200] + "..."
        return jsonify({"error": "internal_error", "detail": msg}), 500
