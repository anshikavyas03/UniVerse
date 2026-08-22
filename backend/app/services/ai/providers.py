from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptMessage:
    role: str
    content: str


class LLMProviderError(RuntimeError):
    """An LLM provider could not fulfill a request."""


class LLMProvider(ABC):
    """Stable contract for Gemini, OpenRouter, and Ollama providers."""

    @abstractmethod
    async def generate(self, messages: list[PromptMessage]) -> str:
        raise NotImplementedError

    async def stream(self, messages: list[PromptMessage]) -> AsyncIterator[str]:
        """Default streaming adapter; providers can override with native streaming."""
        answer = await self.generate(messages)
        for word in answer.split(" "):
            yield f"{word} "
