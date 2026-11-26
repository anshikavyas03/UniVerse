import unittest

from app.core.config import settings
from app.repositories.conversations import InMemoryConversationRepository
from app.repositories.documents import RetrievedChunk
from app.schemas.chat import ChatRequest, Source
from app.services.ai.conversation import ConversationEngine, detect_language
from app.services.ai.providers import LLMProvider, LLMProviderError
from app.services.rag.service import RetrievalResult, UniversityKnowledgeService


class Model(LLMProvider):
    def __init__(self, answer="The fee is listed.", fail=False):
        self.answer, self.fail, self.calls = answer, fail, []

    async def generate(self, messages):
        self.calls.append(messages)
        if self.fail:
            raise LLMProviderError("down")
        return self.answer


class Knowledge:
    def __init__(self, found=True, error=None):
        self.found, self.error, self.queries = found, error, []

    async def retrieve(self, query):
        self.queries.append(query)
        if self.error:
            raise self.error
        sources = [Source(title="Fee Structure", page=1)] if self.found else []
        return RetrievalResult(context="fee data" if self.found else "", sources=sources)


def engine(model, knowledge):
    return ConversationEngine(model, InMemoryConversationRepository(), knowledge)


class GroundingTests(unittest.IsolatedAsyncioTestCase):
    async def test_greetings_are_warm_and_skip_search_and_model(self):
        model, knowledge = Model(), Knowledge()
        for text, language in [("Hi!", "en"), ("hello Aanya", "en"), ("नमस्ते", "hi"), ("How are you?", "en")]:
            response = await engine(model, knowledge).respond(text, language, None)
            self.assertFalse(response.verified)
            self.assertEqual(response.sources, [])
        self.assertEqual((model.calls, knowledge.queries), ([], []))

    async def test_greeting_with_a_question_is_still_searched(self):
        knowledge = Knowledge()
        await engine(Model(), knowledge).respond("Hello, what are the hostel charges?", "en", None)
        self.assertEqual(len(knowledge.queries), 1)

    async def test_database_down_never_asks_the_model(self):
        model = Model()
        response = await engine(model, Knowledge(error=ConnectionRefusedError())).respond("What is the CSE fee?", "en", None)
        self.assertEqual(response.error, "database_unavailable")
        self.assertFalse(response.verified)
        self.assertEqual(model.calls, [])

    async def test_no_matching_context_never_asks_the_model(self):
        model = Model()
        response = await engine(model, Knowledge(found=False)).respond("Who is the vice chancellor?", "en", None)
        self.assertIn("verified information", response.message)
        self.assertEqual(model.calls, [])

    async def test_model_failure_is_not_marked_verified_or_remembered(self):
        conversation = engine(Model(fail=True), Knowledge())
        response = await conversation.respond("What is the CSE fee?", "en", None)
        self.assertEqual(response.error, "model_unavailable")
        self.assertEqual((response.verified, response.sources), (False, []))
        self.assertEqual(conversation.repository.recent(response.conversation_id), [])

    async def test_not_found_answer_drops_sources(self):
        response = await engine(Model("NOT_FOUND"), Knowledge()).respond("Tell me about admissions", "en", None)
        self.assertEqual(response.sources, [])
        self.assertNotIn("NOT_FOUND", response.message)

    async def test_question_is_sent_once_and_follow_up_keeps_topic(self):
        model, knowledge = Model(), Knowledge()
        conversation = engine(model, knowledge)
        first = await conversation.respond("What is the B.Tech CSE fee?", "en", None)
        self.assertEqual([m.content for m in model.calls[0]].count("What is the B.Tech CSE fee?"), 1)
        self.assertTrue(first.follow_up and first.suggestions)
        await conversation.respond("and second year?", "en", first.conversation_id)
        self.assertIn("B.Tech CSE fee", knowledge.queries[-1])

    async def test_unrelated_short_question_does_not_inherit_the_topic(self):
        knowledge = Knowledge()
        conversation = engine(Model(), knowledge)
        first = await conversation.respond("What is the B.Tech CSE fee?", "en", None)
        await conversation.respond("Who is the vice chancellor?", "en", first.conversation_id)
        self.assertEqual(knowledge.queries[-1], "Who is the vice chancellor?")

    async def test_unknown_session_is_reported(self):
        response = await engine(Model(), Knowledge()).respond("hello", "en", "gone-after-restart")
        self.assertTrue(response.session_reset)

    async def test_hindi_fee_question_searches_english_terms(self):
        knowledge = Knowledge()
        await engine(Model(), knowledge).respond("हॉस्टल शुल्क क्या है?", "hi", None)
        self.assertIn("hostel", knowledge.queries[0])
        self.assertIn("fee", knowledge.queries[0])

    def test_english_hostel_fee_question_is_not_detected_as_hindi(self):
        self.assertEqual(detect_language("What are the hostel fees?", "auto"), "en")

    def test_blank_message_is_rejected(self):
        with self.assertRaises(ValueError):
            ChatRequest(message="   ")

    async def test_fee_questions_use_the_fee_structure_document(self):
        class Embeddings:
            async def embed(self, texts):
                return [[0.0] * 768 for _ in texts]

        class Repository:
            async def search_titled(self, embedding, keyword):
                return [RetrievedChunk("B.Tech CSE fee row", "Fee Structure", "Fees", 2, 0.5)]

            async def search(self, embedding):
                raise AssertionError("Other documents must not be searched when the fee document matches")

        result = await UniversityKnowledgeService(settings, Repository(), Embeddings()).retrieve("What is the B.Tech CSE fee?")
        self.assertEqual([source.title for source in result.sources], ["Fee Structure"])

    async def test_fee_keyword_rows_are_used_when_semantic_title_score_is_low(self):
        class Embeddings:
            async def embed(self, texts):
                return [[0.0] * 768 for _ in texts]

        class Repository:
            async def search_titled(self, embedding, keyword):
                return [RetrievedChunk("Fee introduction", "Fee Structure", "Fees", 1, 0.30)]

            async def search_by_keywords(self, query):
                return [RetrievedChunk("Hostel charges: shared room", "Fee Structure", "Fees", 1, 1.0)]

            async def search(self, embedding):
                raise AssertionError("Keyword fee rows should be used before broad semantic search")

        result = await UniversityKnowledgeService(settings, Repository(), Embeddings()).retrieve("What are the hostel charges?")
        self.assertIn("Hostel charges", result.context)


if __name__ == "__main__":
    unittest.main()
