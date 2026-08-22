from collections import defaultdict
from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class ConversationMessage:
    role: str
    content: str


class InMemoryConversationRepository:
    """Phase 2 session memory. Phase 3 will replace this with PostgreSQL."""

    def __init__(self, max_messages: int = 10) -> None:
        self._messages: dict[str, list[ConversationMessage]] = defaultdict(list)
        self._max_messages = max_messages

    def get_or_create(self, conversation_id: str | None) -> str:
        identifier = conversation_id or str(uuid4())
        self._messages[identifier]
        return identifier

    def recent(self, conversation_id: str) -> list[ConversationMessage]:
        return self._messages[conversation_id][-self._max_messages :]

    def append(self, conversation_id: str, role: str, content: str) -> None:
        self._messages[conversation_id].append(ConversationMessage(role=role, content=content))
