"""Tests for OpenAI, Anthropic, Google adapters using respx to mock httpx."""

from __future__ import annotations

import httpx
import pytest
import respx

from game2048.ai.llm.anthropic import ANTHROPIC_ENDPOINT, AnthropicSolver
from game2048.ai.llm.base import LLMError, build_prompt, parse_direction
from game2048.ai.llm.google import GOOGLE_BASE_URL, GoogleSolver
from game2048.ai.llm.openai import OPENAI_ENDPOINT, OpenAISolver
from game2048.engine.board import board_from_list
from game2048.engine.rules import Direction


def _b():
    return board_from_list(
        [
            [2, 2, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
        ]
    )


def test_base_prompt_contains_board_numbers():
    prompt = build_prompt(_b())
    assert "2" in prompt
    assert "UP" in prompt and "DOWN" in prompt and "LEFT" in prompt and "RIGHT" in prompt


def test_parse_direction_accepts_strict_json():
    assert parse_direction('{"move": "UP"}') is Direction.UP
    assert parse_direction('{"move": "left"}'.upper()) is Direction.LEFT


def test_parse_direction_accepts_fenced_json():
    assert parse_direction('```json\n{"move": "DOWN"}\n```') is Direction.DOWN


def test_parse_direction_falls_back_to_bare_token():
    assert parse_direction("My suggestion is RIGHT because...") is Direction.RIGHT


def test_parse_direction_rejects_empty_or_invalid():
    with pytest.raises(LLMError):
        parse_direction("")
    with pytest.raises(LLMError):
        parse_direction("I have no idea")
    with pytest.raises(LLMError):
        parse_direction('{"move": "DIAGONAL"}')


def test_llm_rejects_plain_http_endpoint():
    with pytest.raises(LLMError):
        OpenAISolver(endpoint="http://evil.example.com/api")


# ---- OpenAI ----


@respx.mock
def test_openai_adapter_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-KEY-0123456789")
    route = respx.post(OPENAI_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"move": "LEFT"}'}}]},
        )
    )
    solver = OpenAISolver()
    s = solver.suggest(_b())
    assert s.direction is Direction.LEFT
    assert s.provider == "openai"
    assert route.called
    req = route.calls[0].request
    assert req.headers["authorization"].startswith("Bearer sk-test-KEY")
    assert b'"temperature":0' in req.content
    assert b"json_object" in req.content


@respx.mock
def test_openai_adapter_no_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    solver = OpenAISolver()
    with pytest.raises(LLMError):
        solver.suggest(_b())


@respx.mock
def test_openai_adapter_non_200_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-KEY-0123456789")
    respx.post(OPENAI_ENDPOINT).mock(return_value=httpx.Response(429, json={"error": "rate"}))
    solver = OpenAISolver()
    with pytest.raises(LLMError):
        solver.suggest(_b())


@respx.mock
def test_openai_adapter_malformed_response_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-KEY-0123456789")
    respx.post(OPENAI_ENDPOINT).mock(return_value=httpx.Response(200, json={"unexpected": "shape"}))
    solver = OpenAISolver()
    with pytest.raises(LLMError):
        solver.suggest(_b())


@respx.mock
def test_openai_adapter_timeout_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-KEY-0123456789")
    respx.post(OPENAI_ENDPOINT).mock(side_effect=httpx.ReadTimeout("slow"))
    solver = OpenAISolver(timeout_s=0.1)
    with pytest.raises(LLMError) as exc:
        solver.suggest(_b())
    assert "timed out" in str(exc.value)


# ---- Anthropic ----


@respx.mock
def test_anthropic_adapter_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-0123456789abcdef")
    route = respx.post(ANTHROPIC_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={"content": [{"type": "text", "text": '{"move": "UP"}'}]},
        )
    )
    solver = AnthropicSolver()
    s = solver.suggest(_b())
    assert s.direction is Direction.UP
    assert route.called
    req = route.calls[0].request
    assert req.headers["x-api-key"].startswith("sk-ant-test")
    assert req.headers["anthropic-version"] == "2023-06-01"


@respx.mock
def test_anthropic_adapter_malformed_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-0123456789abcdef")
    respx.post(ANTHROPIC_ENDPOINT).mock(return_value=httpx.Response(200, json={"content": []}))
    solver = AnthropicSolver()
    with pytest.raises(LLMError):
        solver.suggest(_b())


# ---- Google ----


@respx.mock
def test_google_adapter_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "AIza-test-0123456789abcdef")
    solver = GoogleSolver(model="gemini-test")
    url = f"{GOOGLE_BASE_URL}/gemini-test:generateContent"
    route = respx.post(url).mock(
        return_value=httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"move": "DOWN"}'}]}}]},
        )
    )
    s = solver.suggest(_b())
    assert s.direction is Direction.DOWN
    assert route.called
    req = route.calls[0].request
    assert req.headers["x-goog-api-key"].startswith("AIza-test")


@respx.mock
def test_google_adapter_non_200_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "AIza-test-0123456789abcdef")
    solver = GoogleSolver(model="gemini-test")
    url = f"{GOOGLE_BASE_URL}/gemini-test:generateContent"
    respx.post(url).mock(return_value=httpx.Response(500, json={"error": "server"}))
    with pytest.raises(LLMError):
        solver.suggest(_b())
