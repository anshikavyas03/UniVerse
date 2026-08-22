from abc import ABC, abstractmethod


class AvatarProvider(ABC):
    @abstractmethod
    async def speak(self, audio: bytes) -> str:
        """Return a playable avatar media reference."""
        raise NotImplementedError

