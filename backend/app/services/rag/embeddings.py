import httpx

from ..ai.providers import LLMProviderError


class OllamaEmbeddingProvider:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url, self.model = base_url.rstrip("/"), model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(f"{self.base_url}/api/embed", json={"model": self.model, "input": texts})
        except httpx.RequestError as error:
            raise LLMProviderError("Ollama embeddings are unavailable. Start Ollama and install the embedding model.") from error
        if response.is_error:
            raise LLMProviderError("Ollama could not create document embeddings. Install the configured embedding model and try again.")
        embeddings = response.json().get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise LLMProviderError("Ollama returned invalid document embeddings.")
        return embeddings
