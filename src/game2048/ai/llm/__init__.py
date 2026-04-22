"""LLM-backed solvers (OpenAI, Anthropic, Google). Each hits the provider's REST API directly."""

from game2048.ai.llm.anthropic import AnthropicSolver
from game2048.ai.llm.base import LLMError, LLMSolver
from game2048.ai.llm.google import GoogleSolver
from game2048.ai.llm.openai import OpenAISolver

__all__ = ["AnthropicSolver", "GoogleSolver", "LLMError", "LLMSolver", "OpenAISolver"]
