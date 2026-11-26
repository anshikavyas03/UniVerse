from dataclasses import dataclass

from ...core.config import Settings
from ...repositories.documents import PostgresDocumentRepository, RetrievedChunk, StoredDocument
from ...schemas.chat import Source
from ..ai.providers import LLMProviderError
from .chunking import TextChunk, chunk_pages
from .embeddings import OllamaEmbeddingProvider
from .parsing import DocumentParseError, extract_pages


@dataclass(frozen=True)
class RetrievalResult:
    context: str
    sources: list[Source]


class UniversityKnowledgeService:
    def __init__(self, config: Settings, repository: PostgresDocumentRepository | None = None, embeddings: OllamaEmbeddingProvider | None = None) -> None:
        self.repository = repository or PostgresDocumentRepository(config)
        self.embeddings = embeddings or OllamaEmbeddingProvider(config.ollama_base_url, config.ollama_embedding_model)
        self.threshold = config.rag_similarity_threshold

    async def ingest(self, filename: str, content: bytes, metadata: dict[str, str | None]) -> tuple[StoredDocument, int]:
        pages = extract_pages(filename, content)
        chunks = chunk_pages(pages)
        if not chunks:
            raise DocumentParseError("No readable text was found in this document.")
        vectors = await self.embeddings.embed([chunk.content for chunk in chunks])
        _ensure_dimensions(vectors)
        stored = await self.repository.create_document(metadata, filename, [(chunk.content, chunk.page_number, chunk.index, vector) for chunk, vector in zip(chunks, vectors, strict=True)])
        return stored, len(chunks)

    async def retrieve(self, query: str) -> RetrievalResult:
        try:
            vector = (await self.embeddings.embed([query]))[0]
            _ensure_dimensions([vector])
            matches = await self.repository.search(vector)
        except LLMProviderError:
            matches = await self.repository.search_by_keywords(query)
        verified = [match for match in matches if match.similarity >= self.threshold]
        if not verified:
            verified = _keyword_fallback(query, matches)
        verified_titles = {match.title for match in verified}
        related_floor = max(0.45, self.threshold - 0.18)
        context_matches = [
            match for match in matches
            if match.similarity >= self.threshold or (match.title in verified_titles and match.similarity >= related_floor)
        ]
        sources = _deduplicate_sources(context_matches)
        context = "\n\n".join(f"[Source {index + 1}: {match.title}, page {match.page_number or 'unknown'}]\n{match.content}" for index, match in enumerate(context_matches))
        return RetrievalResult(context=context, sources=sources)

    async def list_documents(self) -> list[StoredDocument]:
        return await self.repository.list_documents()


def _deduplicate_sources(matches: list[RetrievedChunk]) -> list[Source]:
    seen: set[tuple[str, int | None]] = set()
    sources: list[Source] = []
    for match in matches:
        identity = (match.title, match.page_number)
        if identity not in seen:
            sources.append(Source(title=match.title, page=match.page_number, category=match.category))
            seen.add(identity)
    return sources


def _keyword_fallback(query: str, matches: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Keep a clearly matching fee or accommodation chunk when embeddings score it narrowly below the cutoff."""
    query_words = set(query.lower().replace("-", " ").split())
    topic_words = query_words & {"fee", "fees", "charges", "hostel", "hostels", "room", "rooms", "accommodation", "tuition"}
    if not topic_words:
        return []
    return [
        match
        for match in matches
        if match.similarity >= 0.45 and any(word in match.content.lower() for word in topic_words)
    ]


def _ensure_dimensions(vectors: list[list[float]]) -> None:
    if any(len(vector) != 768 for vector in vectors):
        raise LLMProviderError("The embedding model must return 768 dimensions. Use nomic-embed-text or update the database schema.")
