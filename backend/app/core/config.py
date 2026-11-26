from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama").lower()
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "google/gemma-3-27b-it:free")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    ollama_embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_university")
    rag_similarity_threshold: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.60"))
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    tts_provider: str = os.getenv("TTS_PROVIDER", "piper").lower()
    piper_executable: str = os.getenv("PIPER_EXECUTABLE", "piper")
    piper_model: str | None = os.getenv("PIPER_MODEL")
    piper_english_model: str | None = os.getenv("PIPER_ENGLISH_MODEL")
    piper_hindi_model: str | None = os.getenv("PIPER_HINDI_MODEL") or os.getenv("PIPER_MODEL")
    macos_english_voice: str = os.getenv("MACOS_ENGLISH_VOICE", "Tara")
    macos_hindi_voice: str = os.getenv("MACOS_HINDI_VOICE", "Lekha")


settings = Settings()
