import json

import asyncpg

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .core.config import settings
from .repositories.conversations import InMemoryConversationRepository
from .schemas.chat import ChatRequest, ChatResponse
from .schemas.documents import DocumentResponse
from .services.ai.conversation import ConversationEngine
from .services.ai.factory import build_llm_provider
from .services.ai.providers import LLMProviderError
from .services.rag.parsing import DocumentParseError
from .services.rag.service import UniversityKnowledgeService

app = FastAPI(title="AI University Digital Human API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

try:
    knowledge = UniversityKnowledgeService(settings)
    engine = ConversationEngine(build_llm_provider(settings), InMemoryConversationRepository(), knowledge)
except ValueError as error:
    engine = None
    startup_error = str(error)
else:
    startup_error = None


@app.get("/health")
def health() -> dict[str, str | None]:
    return {"status": "degraded" if startup_error else "ok", "phase": "conversation", "provider": settings.llm_provider, "error": startup_error}


def get_engine() -> ConversationEngine:
    if engine is None:
        raise HTTPException(status_code=503, detail=startup_error)
    return engine


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await get_engine().respond(request.message, request.language, request.conversation_id)


@app.post("/api/chat/stream")
async def stream_chat(request: ChatRequest) -> StreamingResponse:
    conversation_id, language, chunks = await get_engine().stream(request.message, request.language, request.conversation_id)

    async def event_stream():
        yield f"event: meta\ndata: {json.dumps({'conversation_id': conversation_id, 'language': language})}\n\n"
        async for chunk in chunks:
            yield f"event: delta\ndata: {json.dumps({'text': chunk})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=300),
    category: str | None = Form(default=None),
    department: str | None = Form(default=None),
    academic_year: str | None = Form(default=None),
    version: str | None = Form(default=None),
) -> DocumentResponse:
    if not file.filename:
        raise HTTPException(status_code=422, detail="A filename is required.")
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Documents must be 20 MB or smaller.")
    try:
        stored, chunk_count = await get_engine().knowledge.ingest(file.filename, content, {"title": title, "category": category, "department": department, "academic_year": academic_year, "version": version})
    except (DocumentParseError, LLMProviderError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except asyncpg.PostgresError as error:
        raise HTTPException(status_code=503, detail="The university knowledge database is unavailable.") from error
    return DocumentResponse(**stored.__dict__, chunks_created=chunk_count)


@app.get("/api/documents", response_model=list[DocumentResponse])
async def list_documents() -> list[DocumentResponse]:
    try:
        documents = await get_engine().knowledge.list_documents()
    except asyncpg.PostgresError as error:
        raise HTTPException(status_code=503, detail="The university knowledge database is unavailable.") from error
    return [DocumentResponse(**document.__dict__) for document in documents]
