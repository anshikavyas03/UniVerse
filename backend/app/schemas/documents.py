from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    title: str
    category: str | None = None
    department: str | None = None
    academic_year: str | None = None
    version: str | None = None


class DocumentResponse(DocumentMetadata):
    id: UUID
    original_filename: str
    uploaded_at: datetime
    chunks_created: int | None = None
