import unittest

from app.repositories.conversations import InMemoryConversationRepository
from app.services.ai.conversation import ConversationEngine, detect_language
from app.services.ai.providers import LLMProvider, PromptMessage
from app.repositories.documents import RetrievedChunk
from app.services.rag.chunking import chunk_pages
from app.services.rag.service import UniversityKnowledgeService
from app.core.config import settings


class FakeProvider(LLMProvider):
    async def generate(self, messages: list[PromptMessage]) -> str:
        return f"Replying to: {messages[-1].content}"


class ConversationEngineTests(unittest.IsolatedAsyncioTestCase):
    def test_detects_hindi_and_hinglish(self):
        self.assertEqual(detect_language("पुस्तकालय कहाँ है?", "auto"), "hi")
        self.assertEqual(detect_language("admission office kaha hai", "auto"), "hi")
        self.assertEqual(detect_language("Where is the library?", "auto"), "en")

    async def test_retains_session_and_returns_id(self):
        engine = ConversationEngine(FakeProvider(), InMemoryConversationRepository())
        first = await engine.respond("Tell me about CSE", "en", None)
        second = await engine.respond("What about first year?", "en", first.conversation_id)
        self.assertEqual(first.conversation_id, second.conversation_id)
        self.assertIn("What about first year?", second.message)

    def test_chunks_keep_their_source_page(self):
        chunks = chunk_pages([(4, "Course registration opens in July. " * 60)], chunk_size=120, overlap=20)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.page_number == 4 for chunk in chunks))
        self.assertTrue(all(chunk.content for chunk in chunks))

    async def test_retrieval_returns_verified_source_metadata(self):
        class FakeEmbeddings:
            async def embed(self, texts):
                return [[0.0] * 768 for _ in texts]

        class FakeRepository:
            async def search(self, embedding):
                return [RetrievedChunk(content="The library opens at 8 AM.", title="Campus Guide", category="Campus", page_number=3, similarity=0.95)]

        result = await UniversityKnowledgeService(settings, repository=FakeRepository(), embeddings=FakeEmbeddings()).retrieve("When does the library open?")
        self.assertIn("The library opens at 8 AM", result.context)
        self.assertEqual(result.sources[0].title, "Campus Guide")
        self.assertEqual(result.sources[0].page, 3)


if __name__ == "__main__":
    unittest.main()
