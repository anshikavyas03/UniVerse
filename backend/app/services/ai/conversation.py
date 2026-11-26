from collections.abc import AsyncIterator
import re

import asyncpg

from ...repositories.conversations import InMemoryConversationRepository
from ...schemas.chat import ChatResponse
from ..rag.service import RetrievalResult, UniversityKnowledgeService
from .providers import LLMProvider, LLMProviderError, PromptMessage

HINDI_PATTERN = re.compile(r"[\u0900-\u097F]")
HINGLISH_WORDS = {"kaha", "kaise", "hai", "kya", "mera", "mujhe", "admission", "fees", "hostel"}
DOCUMENT_TOPIC_WORDS = {"admission", "admissions", "apply", "application", "eligibility", "fee", "fees", "charges", "hostel", "hostels", "room", "accommodation", "ordinance", "course", "courses", "programme", "program"}


def detect_language(message: str, selected: str) -> str:
    if selected in {"en", "hi"}:
        return selected
    if HINDI_PATTERN.search(message):
        return "hi"
    words = set(re.findall(r"[a-z]+", message.lower()))
    return "hi" if len(words & HINGLISH_WORDS) >= 2 else "en"


def _is_document_question(message: str) -> bool:
    words = set(re.findall(r"[a-z]+", message.lower()))
    return bool(words & DOCUMENT_TOPIC_WORDS)


def _missing_document_reply(message: str, language: str) -> str:
    is_admissions = bool(set(re.findall(r"[a-z]+", message.lower())) & {"admission", "admissions", "apply", "application", "eligibility"})
    if language == "hi":
        return "मुझे अपलोड किए गए विश्वविद्यालय दस्तावेज़ों में प्रवेश की सत्यापित जानकारी नहीं मिली। कृपया प्रवेश विवरणिका अपलोड करें या प्रवेश कार्यालय से संपर्क करें।" if is_admissions else "मुझे अपलोड किए गए विश्वविद्यालय दस्तावेज़ों में इस विषय की सत्यापित जानकारी नहीं मिली। कृपया संबंधित दस्तावेज़ अपलोड करें या अधिक विशिष्ट प्रश्न पूछें।"
    return "I don’t have verified admissions information in the uploaded university documents yet. Please upload the admissions brochure or contact the admissions office." if is_admissions else "I don’t have verified information for that in the uploaded university documents yet. Please upload the relevant document or ask a more specific question."


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
            "Write clear, student-friendly Markdown: use a short heading only when useful, then short bullet points. "
            "Avoid long tables and avoid repeating the source text. "
            "Answer only the part of the context that directly addresses the question. "
            "For a broad fee question where fees vary by programme, do not list every programme: explain that fees vary and ask the student to name their programme and year. "
            "For a specific programme and year, state only that programme's relevant fee, then any essential one-time fee or deadline. "
            "For a shared-hostel-room question, list only the shared room options (such as 2-, 4-, and 6-seater) with their annual charge and refundable security. "
            "Keep every answer under six bullet points unless the student explicitly asks for a complete list. "
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
        self.repository.append(identifier, "user", message)
        if retrieval is not None and not retrieval.sources and _is_document_question(message):
            answer = _missing_document_reply(message, detected)
        else:
            prompt = self._prompt(identifier, message, detected, retrieval)
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
