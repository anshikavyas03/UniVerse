from collections.abc import AsyncIterator
import re

import asyncpg

from ...repositories.conversations import InMemoryConversationRepository
from ...schemas.chat import ChatResponse
from ..rag.service import RetrievalResult, UniversityKnowledgeService
from .providers import LLMProvider, LLMProviderError, PromptMessage

HINDI_PATTERN = re.compile(r"[\u0900-\u097F]")
HINGLISH_WORDS = {"kaha", "kaise", "hai", "kya", "mera", "mujhe", "admission", "fees", "hostel"}


def detect_language(message: str, selected: str) -> str:
    if selected in {"en", "hi"}:
        return selected
    if HINDI_PATTERN.search(message):
        return "hi"
    words = set(re.findall(r"[a-z]+", message.lower()))
    return "hi" if len(words & HINGLISH_WORDS) >= 2 else "en"


class ConversationEngine:
    def __init__(self, provider: LLMProvider, repository: InMemoryConversationRepository, knowledge: UniversityKnowledgeService | None = None) -> None:
        self.provider = provider
        self.repository = repository
        self.knowledge = knowledge

    def _prompt(self, conversation_id: str, message: str, language: str, retrieval: RetrievalResult | None) -> list[PromptMessage]:
        reply_language = "Hindi" if language == "hi" else "English"
        system = (
            "You are the AI University Digital Human, a concise and helpful virtual university representative. "
            f"Reply in {reply_language}. Maintain context from the conversation. "
            "Never invent university-specific facts. "
        )
        if retrieval and retrieval.context:
            system += "Answer university-specific questions using only the verified context below. If it does not answer the question, say so plainly.\n\nVERIFIED UNIVERSITY CONTEXT:\n" + retrieval.context
        else:
            system += "No verified university information was retrieved for this question. Say you could not find verified information in the university knowledge base rather than guessing."
        history = [PromptMessage(item.role, item.content) for item in self.repository.recent(conversation_id)]
        return [PromptMessage("system", system), *history, PromptMessage("user", message)]

    async def respond(self, message: str, language: str, conversation_id: str | None) -> ChatResponse:
        identifier = self.repository.get_or_create(conversation_id)
        detected = detect_language(message, language)
        retrieval = None
        if self.knowledge:
            try:
                retrieval = await self.knowledge.retrieve(message)
            except (LLMProviderError, OSError, asyncpg.PostgresError):
                retrieval = None
        prompt = self._prompt(identifier, message, detected, retrieval)
        self.repository.append(identifier, "user", message)
        try:
            answer = await self.provider.generate(prompt)
        except LLMProviderError:
            answer = "मुझे अभी उस जानकारी तक पहुँचने में समस्या हो रही है। कृपया फिर कोशिश करें।" if detected == "hi" else "I’m having trouble accessing that information right now. Please try again."
        self.repository.append(identifier, "assistant", answer)
        return ChatResponse(conversation_id=identifier, message=answer, language=detected, sources=retrieval.sources if retrieval else [], verified=bool(retrieval and retrieval.sources), provider=type(self.provider).__name__.removesuffix("Provider"))

    async def stream(self, message: str, language: str, conversation_id: str | None) -> tuple[str, str, AsyncIterator[str]]:
        response = await self.respond(message, language, conversation_id)

        async def chunks() -> AsyncIterator[str]:
            for word in response.message.split(" "):
                yield f"{word} "

        return response.conversation_id, response.language, chunks()
