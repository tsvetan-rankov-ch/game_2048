"""Anthropic Messages API adapter. https://docs.anthropic.com/en/api/messages"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import httpx

from game2048.ai.llm.base import DEFAULT_TIMEOUT_S, LLMError, LLMSolver

ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"


@dataclass
class AnthropicSolver(LLMSolver):
    name: ClassVar[str] = "anthropic"
    env_key_var: ClassVar[str] = "ANTHROPIC_API_KEY"

    model: str = "claude-haiku-4-5"
    endpoint: str = ANTHROPIC_ENDPOINT
    timeout_s: float = DEFAULT_TIMEOUT_S

    def _call_api(self, client: httpx.Client, prompt: str) -> str:
        key = self._api_key()
        resp = client.post(
            self.endpoint,
            headers={
                "x-api-key": key,
                "anthropic-version": ANTHROPIC_API_VERSION,
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 64,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        if resp.status_code != 200:
            raise LLMError(f"{self.name}: HTTP {resp.status_code}")
        data = resp.json()
        try:
            blocks = data["content"]
            for block in blocks:
                if block.get("type") == "text":
                    return block["text"]
        except (KeyError, TypeError) as exc:
            raise LLMError(f"{self.name}: malformed response") from exc
        raise LLMError(f"{self.name}: no text block in response")
