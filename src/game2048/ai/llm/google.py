"""Google Gemini generateContent adapter.
https://ai.google.dev/api/generate-content
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import httpx

from game2048.ai.llm.base import DEFAULT_TIMEOUT_S, LLMError, LLMSolver

GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


@dataclass
class GoogleSolver(LLMSolver):
    name: ClassVar[str] = "google"
    env_key_var: ClassVar[str] = "GOOGLE_API_KEY"

    model: str = "gemini-2.0-flash"
    endpoint: str = GOOGLE_BASE_URL
    timeout_s: float = DEFAULT_TIMEOUT_S

    def _call_api(self, client: httpx.Client, prompt: str) -> str:
        key = self._api_key()
        url = f"{GOOGLE_BASE_URL}/{self.model}:generateContent"
        resp = client.post(
            url,
            headers={
                "x-goog-api-key": key,
                "Content-Type": "application/json",
            },
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                },
            },
        )
        if resp.status_code != 200:
            raise LLMError(f"{self.name}: HTTP {resp.status_code}")
        data = resp.json()
        try:
            candidates = data["candidates"]
            parts = candidates[0]["content"]["parts"]
            for part in parts:
                if "text" in part:
                    return part["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"{self.name}: malformed response") from exc
        raise LLMError(f"{self.name}: no text part in response")
