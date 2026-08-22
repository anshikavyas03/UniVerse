from dataclasses import dataclass
from uuid import UUID

import asyncpg

from ..core.config import Settings


@dataclass(frozen=True)
class StoredDocument:
    id: UUID
    title: str
    category: str | None
    department: str | None
    academic_year: str | None
    version: str | None
    original_filename: str
    uploaded_at: object


@dataclass(frozen=True)
class RetrievedChunk:
    content: str
    title: str
    category: str | None
    page_number: int | None
    similarity: float


class PostgresDocumentRepository:
    def __init__(self, settings: Settings) -> None:
        self.database_url = settings.database_url

    async def create_document(self, metadata: dict[str, str | None], original_filename: str, chunks: list[tuple[str, int | None, int, list[float]]]) -> StoredDocument:
        connection = await asyncpg.connect(self.database_url)
        try:
            async with connection.transaction():
                row = await connection.fetchrow(
                    """INSERT INTO documents (title, category, department, academic_year, version, original_filename)
                       VALUES ($1, $2, $3, $4, $5, $6)
                       RETURNING id, title, category, department, academic_year, version, original_filename, uploaded_at""",
                    metadata["title"], metadata["category"], metadata["department"], metadata["academic_year"], metadata["version"], original_filename,
                )
                await connection.executemany(
                    """INSERT INTO document_chunks (document_id, content, page_number, chunk_index, embedding)
                       VALUES ($1, $2, $3, $4, $5::vector)""",
                    [(row["id"], text, page, index, _vector(embedding)) for text, page, index, embedding in chunks],
                )
            return StoredDocument(**dict(row))
        finally:
            await connection.close()

    async def list_documents(self) -> list[StoredDocument]:
        connection = await asyncpg.connect(self.database_url)
        try:
            rows = await connection.fetch("SELECT id, title, category, department, academic_year, version, original_filename, uploaded_at FROM documents ORDER BY uploaded_at DESC")
            return [StoredDocument(**dict(row)) for row in rows]
        finally:
            await connection.close()

    async def search(self, embedding: list[float], limit: int = 5) -> list[RetrievedChunk]:
        connection = await asyncpg.connect(self.database_url)
        try:
            rows = await connection.fetch(
                """SELECT c.content, d.title, d.category, c.page_number, 1 - (c.embedding <=> $1::vector) AS similarity
                   FROM document_chunks c JOIN documents d ON d.id = c.document_id
                   ORDER BY c.embedding <=> $1::vector LIMIT $2""",
                _vector(embedding), limit,
            )
            return [RetrievedChunk(**dict(row)) for row in rows]
        finally:
            await connection.close()


def _vector(values: list[float]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"
