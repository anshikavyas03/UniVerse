from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


class DocumentParseError(ValueError):
    pass


def extract_pages(filename: str, content: bytes) -> list[tuple[int | None, str]]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return [(1, content.decode("utf-8", errors="replace"))]
    if suffix == ".pdf":
        try:
            reader = PdfReader(BytesIO(content))
            return [(number, page.extract_text() or "") for number, page in enumerate(reader.pages, start=1)]
        except Exception as error:
            raise DocumentParseError("The PDF could not be read. Please upload a text-based PDF.") from error
    raise DocumentParseError("Only .pdf and .txt documents are supported in Phase 3.")
