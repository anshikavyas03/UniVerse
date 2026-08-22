from ...core.config import Settings
from .implementations import GeminiProvider, OllamaProvider, OpenRouterProvider
from .providers import LLMProvider


def build_llm_provider(config: Settings) -> LLMProvider:
    if config.llm_provider == "gemini":
        return GeminiProvider(config.gemini_api_key, config.gemini_model)
    if config.llm_provider == "openrouter":
        return OpenRouterProvider(config.openrouter_api_key, config.openrouter_model)
    if config.llm_provider == "ollama":
        return OllamaProvider(config.ollama_base_url, config.ollama_model)
    raise ValueError("LLM_PROVIDER must be gemini, openrouter, or ollama.")
