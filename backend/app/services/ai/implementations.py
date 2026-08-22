import httpx

from .providers import LLMProvider, LLMProviderError, PromptMessage


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key, self.model = api_key, model

    async def generate(self, messages: list[PromptMessage]) -> str:
        if not self.api_key:
            raise LLMProviderError("GEMINI_API_KEY is not configured.")
        contents = [{"role": "model" if item.role == "assistant" else "user", "parts": [{"text": item.content}]} for item in messages]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(url, params={"key": self.api_key}, json={"contents": contents})
        if response.is_error:
            raise LLMProviderError("Gemini could not generate a response.")
        try:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as error:
            raise LLMProviderError("Gemini returned an unreadable response.") from error


class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key, self.model = api_key, model

    async def generate(self, messages: list[PromptMessage]) -> str:
        if not self.api_key:
            raise LLMProviderError("OPENROUTER_API_KEY is not configured.")
        payload = {"model": self.model, "messages": [{"role": item.role, "content": item.content} for item in messages]}
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {self.api_key}"}, json=payload)
        if response.is_error:
            raise LLMProviderError("OpenRouter could not generate a response.")
        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise LLMProviderError("OpenRouter returned an unreadable response.") from error


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url, self.model = base_url.rstrip("/"), model

    async def generate(self, messages: list[PromptMessage]) -> str:
        payload = {"model": self.model, "messages": [{"role": item.role, "content": item.content} for item in messages], "stream": False}
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.RequestError as error:
            raise LLMProviderError("Ollama is unavailable. Start Ollama or choose another LLM provider.") from error
        if response.is_error:
            raise LLMProviderError("Ollama could not generate a response.")
        try:
            return response.json()["message"]["content"]
        except (KeyError, TypeError) as error:
            raise LLMProviderError("Ollama returned an unreadable response.") from error
