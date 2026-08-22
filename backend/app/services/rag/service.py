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
        vector = (await self.embeddings.embed([query]))[0]
        _ensure_dimensions([vector])
        matches = await self.repository.search(vector)
        verified = [match for match in matches if match.similarity >= self.threshold]
        sources = _deduplicate_sources(verified)
        context = "\n\n".join(f"[Source {index + 1}: {match.title}, page {match.page_number or 'unknown'}]\n{match.content}" for index, match in enumerate(verified))
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


def _ensure_dimensions(vectors: list[list[float]]) -> None:
    if any(len(vector) != 768 for vector in vectors):
        raise LLMProviderError("The embedding model must return 768 dimensions. Use nomic-embed-text or update the database schema.")
