from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TextChunk:
    content: str
    page_number: int | None
    index: int


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def chunk_pages(pages: list[tuple[int | None, str]], chunk_size: int = 900, overlap: int = 160) -> list[TextChunk]:
    """Split text on word boundaries while retaining source page metadata."""
    chunks: list[TextChunk] = []
    for page_number, raw_text in pages:
        text = clean_text(raw_text)
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start, end)
                end = boundary if boundary > start else end
            content = text[start:end].strip()
            if content:
                chunks.append(TextChunk(content=content, page_number=page_number, index=len(chunks)))
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks
