"""Flask test-client tests for every API endpoint."""

from __future__ import annotations

import time

from flask.testing import FlaskClient


def test_index_renders(client: FlaskClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"2048" in resp.data


def test_state_returns_initial_game(client: FlaskClient):
    resp = client.get("/api/state")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "playing"
    assert data["score"] == 0
    assert data["four_prob"] == 0.1
    assert data["moves"] == 0
    assert sum(1 for row in data["board"] for v in row if v) == 2
    names = [p["name"] for p in data["providers"]]
    assert set(names) == {"local", "openai", "anthropic", "google"}
    # Only local should be configured by default in tests.
    configured = {p["name"] for p in data["providers"] if p["configured"]}
    assert configured == {"local"}


def test_move_with_invalid_direction_returns_400(client: FlaskClient):
    resp = client.post("/api/move", json={"direction": "diagonal"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_direction"


def test_move_returns_updated_state(client: FlaskClient):
    before = client.get("/api/state").get_json()
    resp = client.post("/api/move", json={"direction": "left"})
    assert resp.status_code == 200
    after = resp.get_json()
    assert "changed" in after
    # The state should be valid regardless of whether the move changed the board.
    assert after["status"] in {"playing", "won", "lost"}
    assert after["moves"] >= before["moves"]


def test_new_game_resets_score_and_accepts_four_prob(client: FlaskClient):
    # Make at least one move attempt so state may have changed.
    for d in ("left", "right", "up", "down"):
        client.post("/api/move", json={"direction": d})
    resp = client.post("/api/new-game", json={"four_prob": 0.25})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["score"] == 0
    assert data["four_prob"] == 0.25
    assert data["moves"] == 0


def test_new_game_rejects_invalid_four_prob(client: FlaskClient):
    resp = client.post("/api/new-game", json={"four_prob": 2.0})
    assert resp.status_code == 400
    resp = client.post("/api/new-game", json={"four_prob": "notanumber"})
    assert resp.status_code == 400


def test_hint_with_local_provider_returns_scored_directions(client: FlaskClient):
    resp = client.post("/api/hint", json={"provider": "local"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["provider"] == "local"
    assert data["direction"] in {"up", "down", "left", "right"}
    assert data["scores"] is not None
    assert set(data["scores"].keys()) == {"up", "down", "left", "right"}


def test_hint_with_unknown_provider_returns_400(client: FlaskClient):
    resp = client.post("/api/hint", json={"provider": "mystery"})
    assert resp.status_code == 400


def test_hint_with_unconfigured_llm_returns_502(client: FlaskClient):
    resp = client.post("/api/hint", json={"provider": "openai"})
    assert resp.status_code == 502
    assert "error" in resp.get_json()


def test_solve_start_rejects_non_local(client: FlaskClient):
    resp = client.post("/api/solve/start", json={"provider": "openai"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "solve_local_only"


def test_solve_start_and_stop_lifecycle(client: FlaskClient):
    start = client.post("/api/solve/start", json={"provider": "local"})
    assert start.status_code == 200
    assert start.get_json()["running"] is True

    # Give it a fraction of a second to apply at least one move.
    time.sleep(0.6)

    status = client.get("/api/solve/status")
    assert status.status_code == 200
    status_data = status.get_json()
    # Running flag can be true or false if the game happened to finish very fast (unlikely).
    assert "running" in status_data
    assert "log" in status_data

    stop = client.post("/api/solve/stop")
    assert stop.status_code == 200
    assert stop.get_json()["running"] is False


def test_move_during_solve_is_rejected(client: FlaskClient):
    client.post("/api/solve/start", json={"provider": "local"})
    try:
        # Racy by nature — poll briefly until we either see it running or time out.
        saw_conflict = False
        for _ in range(20):
            resp = client.post("/api/move", json={"direction": "left"})
            if resp.status_code == 409:
                saw_conflict = True
                break
            time.sleep(0.05)
        assert saw_conflict, "expected at least one 409 while solve was running"
    finally:
        client.post("/api/solve/stop")
