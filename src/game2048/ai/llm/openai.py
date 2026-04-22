"""OpenAI Chat Completions adapter. https://platform.openai.com/docs/api-reference/chat"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import httpx

from game2048.ai.llm.base import DEFAULT_TIMEOUT_S, LLMError, LLMSolver

OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"


@dataclass
class OpenAISolver(LLMSolver):
    name: ClassVar[str] = "openai"
    env_key_var: ClassVar[str] = "OPENAI_API_KEY"

    model: str = "gpt-4o-mini"
    endpoint: str = OPENAI_ENDPOINT
    timeout_s: float = DEFAULT_TIMEOUT_S

    def _call_api(self, client: httpx.Client, prompt: str) -> str:
        key = self._api_key()
        resp = client.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
        )
        if resp.status_code != 200:
            raise LLMError(f"{self.name}: HTTP {resp.status_code}")
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"{self.name}: malformed response") from exc
