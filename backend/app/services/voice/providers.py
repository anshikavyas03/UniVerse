from abc import ABC, abstractmethod


class VoiceProviderError(Exception):
    """Raised when a configured voice runtime cannot process a request."""


class SpeechToTextProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, language: str) -> str:
        raise NotImplementedError


class TextToSpeechProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, language: str) -> bytes:
        raise NotImplementedError
