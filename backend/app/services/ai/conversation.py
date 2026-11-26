from collections.abc import AsyncIterator
import re

import asyncpg

from ...repositories.conversations import InMemoryConversationRepository
from ...schemas.chat import ChatResponse
from ..rag.service import RetrievalResult, UniversityKnowledgeService
from ..rag.topics import TOPIC_WORDS, search_text, topic_of, words_of
from .providers import LLMProvider, LLMProviderError, PromptMessage
from .smalltalk import small_talk_reply

HINDI_PATTERN = re.compile(r"[ऀ-ॿ]")
HINGLISH_MARKERS = {"kaha", "kahan", "kaise", "hai", "hain", "kya", "mera", "mujhe", "batao", "bataiye", "kitni", "kitna", "chahiye"}
HINGLISH_WORDS = HINGLISH_MARKERS | {"admission", "fees", "hostel"}
NOT_FOUND = "NOT_FOUND"
_FOLLOW_UP_HINT = re.compile(r"\b(?:year|semester|sem|seater|ac|b\.?tech|cse|mba|bca|mca|it|that|this|they|those|one|single|double|first|second|third|fourth)\b|वर्ष|साल|सेमेस्टर|सीटर", re.IGNORECASE)
_FOLLOW_UP_START = re.compile(r"^(?:and|what about|how about|also|aur|और)\b", re.IGNORECASE)
_REFUSAL = re.compile(r"could not find|couldn.t find|no verified|not (?:mentioned|provided|available|specified|included)|does not (?:mention|contain|provide|include|specify)|जानकारी (?:नहीं|उपलब्ध नहीं)", re.IGNORECASE)
_ROOM_TYPE = re.compile(r"\b(?:[1-6][\s-]*seater|single|double)\b|[1-6]\s*सीटर", re.IGNORECASE)
_ROOM_SELECTION = re.compile(r"\b([1-6])[\s-]*seater\b|([1-6])\s*सीटर", re.IGNORECASE)

SUGGESTIONS = {
    "en": {
        "hostel": ["1-seater room", "2-seater room", "4-seater room", "6-seater room"],
        "fees": ["Are there any one-time fees?", "What is the last date to pay fees?", "What are the hostel charges?"],
        "admissions": ["What is the eligibility for B.Tech?", "How do I apply?", "What is the B.Tech CSE fee?"],
        "general": ["What are the hostel charges?", "What is the B.Tech CSE fee?", "Tell me about admissions"],
    },
    "hi": {
        "hostel": ["1 सीटर कमरा", "2 सीटर कमरा", "4 सीटर कमरा", "6 सीटर कमरा"],
        "fees": ["क्या कोई एक बार का शुल्क है?", "फीस भरने की अंतिम तारीख क्या है?", "हॉस्टल शुल्क क्या है?"],
        "admissions": ["B.Tech के लिए पात्रता क्या है?", "आवेदन कैसे करें?", "B.Tech CSE की फीस क्या है?"],
        "general": ["हॉस्टल शुल्क क्या है?", "B.Tech CSE की फीस क्या है?", "प्रवेश के बारे में बताइए"],
    },
}


def detect_language(message: str, selected: str) -> str:
    if selected in {"en", "hi"}:
        return selected
    if HINDI_PATTERN.search(message):
        return "hi"
    words = set(re.findall(r"[a-z]+", message.lower()))
    return "hi" if words & HINGLISH_MARKERS and len(words & HINGLISH_WORDS) >= 2 else "en"


def _missing_document_reply(message: str, language: str) -> str:
    topic = topic_of(message)
    if language == "hi":
        if topic == "admissions":
            return "मुझे अपलोड किए गए विश्वविद्यालय दस्तावेज़ों में प्रवेश की सत्यापित जानकारी नहीं मिली। कृपया प्रवेश विवरणिका अपलोड करें या प्रवेश कार्यालय से संपर्क करें।"
        if topic in {"fees", "hostel"}:
            return "मुझे अपलोड किए गए दस्तावेज़ों में इसकी सत्यापित जानकारी नहीं मिली। कृपया Fee Structure दस्तावेज़ अपलोड करें या लेखा कार्यालय से पूछें।"
        return "मुझे अपलोड किए गए विश्वविद्यालय दस्तावेज़ों में इस विषय की सत्यापित जानकारी नहीं मिली। कृपया संबंधित दस्तावेज़ अपलोड करें या अधिक विशिष्ट प्रश्न पूछें।"
    if topic == "admissions":
        return "I don’t have verified admissions information in the uploaded university documents yet. Please upload the admissions brochure or contact the admissions office."
    if topic in {"fees", "hostel"}:
        return "I couldn’t find verified information for that in the uploaded documents. Please upload the Fee Structure document, or check with the accounts office."
    return "I don’t have verified information for that in the uploaded university documents yet. Please upload the relevant document or ask a more specific question."


def _failure_reply(kind: str, language: str) -> str:
    replies = {
        "database_unavailable": (
            "I can’t open the university knowledge base right now, so I won’t guess. Please check that Docker and PostgreSQL are running, then try again.",
            "अभी विश्वविद्यालय का ज्ञान-भंडार उपलब्ध नहीं है, इसलिए मैं अनुमान नहीं लगाऊँगी। कृपया Docker और PostgreSQL चालू करके फिर कोशिश करें।",
        ),
        "model_unavailable": (
            "I found the topic, but my answering service isn’t responding right now. Please check that Ollama (or your Gemini key) is working, then try again.",
            "मेरी उत्तर देने वाली सेवा अभी जवाब नहीं दे रही है। कृपया Ollama (या Gemini key) जाँचकर फिर कोशिश करें।",
        ),
    }
    english, hindi = replies[kind]
    return hindi if language == "hi" else english


def _follow_up(message: str, language: str) -> str | None:
    topic = topic_of(message)
    has_programme = bool(re.search(r"b\.?\s?tech|m\.?\s?tech|\bcse\b|\bmba\b|\bbca\b|\bmca\b|\bbba\b|\bllb\b", message, re.IGNORECASE))
    questions = {
        "fees": ("Which year or semester should I look at?", "आपको किस वर्ष या सेमेस्टर की जानकारी चाहिए?") if has_programme
        else ("Which programme and year are you asking about?", "आप किस कोर्स और वर्ष के बारे में पूछ रहे हैं?"),
        "hostel": ("Which room type are you considering?", "आप किस तरह का कमरा लेना चाहेंगे?"),
        "admissions": ("Which programme are you hoping to join?", "आप किस कोर्स में प्रवेश लेना चाहते हैं?"),
    }
    if topic not in questions:
        return None
    return questions[topic][1 if language == "hi" else 0]


def _search_query(message: str, history: list[PromptMessage]) -> str:
    """Give short follow-ups ("and second year?") the topic of the previous question."""
    words = words_of(message)
    is_follow_up = bool(_FOLLOW_UP_START.match(message.strip())) or (not words & TOPIC_WORDS and len(message.split()) <= 6 and bool(_FOLLOW_UP_HINT.search(message)))
    if is_follow_up:
        for item in reversed(history):
            if item.role == "user" and words_of(item.content) & TOPIC_WORDS:
                return f"{item.content} {message}"
    return message


def _broad_hostel_prompt(message: str, language: str) -> str | None:
    """Ask for a room choice before pricing a broad hostel request."""
    if topic_of(message) != "hostel" or _ROOM_TYPE.search(message):
        return None
    if language == "hi":
        return "ज़रूर। हॉस्टल शुल्क कमरे के प्रकार पर निर्भर करता है। आप 1, 2, 4 या 6 सीटर AC कमरे में से किसके बारे में जानना चाहेंगे?"
    return "I can help with that. Hostel charges depend on the room type. Are you considering a 1-, 2-, 4-, or 6-seater AC room?"


def _selected_room_answer(message: str, context: str, language: str) -> str | None:
    selected = _ROOM_SELECTION.search(message)
    if not selected:
        return None
    seats = selected.group(1) or selected.group(2)
    row = re.search(
        rf"{seats}\s+Seater\s+AC\s+Room(?:\s+\(Shared(?:\s+Accommodation\))?)?\s+(\d{{1,3}}(?:,\d{{3}})+)\s+(\d{{1,3}}(?:,\d{{3}})+)",
        " ".join(context.split()),
        re.IGNORECASE,
    )
    if not row:
        return None
    annual, security = row.groups()
    if language == "hi":
        return f"{seats} सीटर AC कमरे का वार्षिक शुल्क INR {annual} है। एक बार की वापसी योग्य सिक्योरिटी INR {security} है।"
    return f"For the {seats}-seater AC room, the annual hostel charge is INR {annual}. The one-time refundable security deposit is INR {security}."


class ConversationEngine:
    def __init__(self, provider: LLMProvider, repository: InMemoryConversationRepository, knowledge: UniversityKnowledgeService | None = None) -> None:
        self.provider = provider
        self.repository = repository
        self.knowledge = knowledge

    def _prompt(self, history: list[PromptMessage], message: str, language: str, retrieval: RetrievalResult | None) -> list[PromptMessage]:
        reply_language = "Hindi" if language == "hi" else "English"
        system = (
            "You are Aanya, the AI University Digital Human: a warm, concise virtual university representative talking one-to-one with a student. "
            f"Reply in {reply_language}. Maintain context from the conversation. "
            "Never invent university-specific facts. "
            "Start with one short, direct sentence, then short bullet points only if needed. "
            "Do not greet the student again, do not use tables, and do not repeat the source text. "
            "Answer only the part of the context that directly addresses the question. "
            "For a broad fee question where fees vary by programme, do not list every programme: explain that fees vary and ask the student to name their programme and year. "
            "For a specific programme and year, state only that programme's relevant fee, then any essential one-time fee or deadline. "
            "For a shared-hostel-room question, list only the shared room options (such as 2-, 4-, and 6-seater) with their annual charge and refundable security. "
            "Keep every answer under six bullet points unless the student explicitly asks for a complete list. "
        )
        if retrieval and retrieval.context:
            system += (
                "Answer university-specific questions using only the verified context below. "
                f"If the context does not answer the question, reply with exactly {NOT_FOUND} and nothing else.\n\nVERIFIED UNIVERSITY CONTEXT:\n" + retrieval.context
            )
        else:
            system += "No verified university information was retrieved for this question. Say you could not find verified information in the university knowledge base rather than guessing."
        return [PromptMessage("system", system), *history, PromptMessage("user", message)]

    async def respond(self, message: str, language: str, conversation_id: str | None) -> ChatResponse:
        message = message.strip()
        session_reset = bool(conversation_id) and not self.repository.exists(conversation_id)
        identifier = self.repository.get_or_create(conversation_id)
        detected = detect_language(message, language)
        history = [PromptMessage(item.role, item.content) for item in self.repository.recent(identifier)]

        def reply(answer: str, *, sources=(), follow_up: str | None = None, error: str | None = None, topic: str = "general") -> ChatResponse:
            # Failed turns are left out of memory so a retry starts clean.
            if error is None:
                self.repository.append(identifier, "user", message)
                self.repository.append(identifier, "assistant", f"{answer} {follow_up}" if follow_up else answer)
            return ChatResponse(
                conversation_id=identifier, message=answer, language=detected, sources=list(sources), verified=bool(sources),
                provider=type(self.provider).__name__.removesuffix("Provider"), follow_up=follow_up, error=error,
                suggestions=[] if error else [item for item in SUGGESTIONS[detected][topic] if item != message], session_reset=session_reset,
            )

        social = small_talk_reply(message, detected)
        if social:
            return reply(social)

        query = _search_query(message, history)
        topic = topic_of(query)
        retrieval = None
        if self.knowledge:
            try:
                retrieval = await self.knowledge.retrieve(search_text(query))
            except (LLMProviderError, OSError, asyncpg.PostgresError, asyncpg.InterfaceError):
                return reply(_failure_reply("database_unavailable", detected), error="database_unavailable")
            if not retrieval.sources:
                return reply(_missing_document_reply(query, detected), topic=topic)

        hostel_prompt = _broad_hostel_prompt(query, detected)
        if hostel_prompt:
            return reply(hostel_prompt, sources=retrieval.sources if retrieval else [], topic="hostel")

        if retrieval:
            room_answer = _selected_room_answer(query, retrieval.context, detected)
            if room_answer:
                return reply(room_answer, sources=retrieval.sources, follow_up="Would you like to compare another room type?" if detected == "en" else "क्या आप किसी दूसरे कमरे के प्रकार की तुलना करना चाहेंगे?", topic="hostel")

        try:
            answer = (await self.provider.generate(self._prompt(history, message, detected, retrieval))).strip()
        except LLMProviderError:
            return reply(_failure_reply("model_unavailable", detected), error="model_unavailable")
        if not answer:
            return reply(_failure_reply("model_unavailable", detected), error="model_unavailable")
        if retrieval and (NOT_FOUND in answer or (len(answer) < 300 and not re.search(r"\d", answer) and _REFUSAL.search(answer))):
            return reply(_missing_document_reply(query, detected), topic=topic)
        return reply(answer, sources=retrieval.sources if retrieval else [], follow_up=_follow_up(query, detected), topic=topic)

    async def stream(self, message: str, language: str, conversation_id: str | None) -> tuple[str, str, AsyncIterator[str]]:
        response = await self.respond(message, language, conversation_id)

        async def chunks() -> AsyncIterator[str]:
            for word in response.message.split(" "):
                yield f"{word} "

        return response.conversation_id, response.language, chunks()
