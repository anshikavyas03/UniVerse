import asyncio
import json

import asyncpg
import httpx

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from .core.config import settings
from .repositories.conversations import InMemoryConversationRepository
from .schemas.chat import ChatRequest, ChatResponse
from .schemas.documents import DocumentResponse
from .schemas.voice import SpeechRequest, TranscriptionResponse
from .services.ai.conversation import ConversationEngine
from .services.ai.factory import build_llm_provider
from .services.ai.providers import LLMProviderError
from .services.rag.parsing import DocumentParseError
from .services.rag.service import UniversityKnowledgeService
from .services.voice.factory import build_speech_to_text_provider, build_text_to_speech_provider
from .services.voice.providers import VoiceProviderError
from .services.voice.speech_text import to_spoken_text

app = FastAPI(title="AI University Digital Human API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=sorted({settings.frontend_origin, settings.frontend_origin.replace("//localhost", "//127.0.0.1")}), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

try:
    knowledge = UniversityKnowledgeService(settings)
    engine = ConversationEngine(build_llm_provider(settings), InMemoryConversationRepository(), knowledge)
except ValueError as error:
    engine = None
    startup_error = str(error)
else:
    startup_error = None

speech_to_text = build_speech_to_text_provider(settings)
try:
    text_to_speech = build_text_to_speech_provider(settings)
except VoiceProviderError:
    text_to_speech = None


async def _database_status() -> tuple[str, int | None]:
    try:
        connection = await asyncpg.connect(settings.database_url, timeout=2)
        try:
            return "ok", await connection.fetchval("SELECT COUNT(*) FROM documents")
        finally:
            await connection.close()
    except (OSError, ValueError, asyncpg.PostgresError, asyncpg.InterfaceError):
        return "unavailable", None


async def _model_status() -> str:
    if settings.llm_provider == "gemini":
        return "ok" if settings.gemini_api_key else "not_configured"
    if settings.llm_provider == "openrouter":
        return "ok" if settings.openrouter_api_key else "not_configured"
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
        return "ok" if response.is_success else "unavailable"
    except httpx.HTTPError:
        return "unavailable"


@app.get("/health")
async def health() -> dict[str, str | int | None]:
    (database, documents), model = await asyncio.gather(_database_status(), _model_status())
    healthy = not startup_error and database == "ok" and model == "ok"
    return {"status": "ok" if healthy else "degraded", "phase": "conversation", "provider": settings.llm_provider, "model": model, "database": database, "documents": documents, "error": startup_error}


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
    except (OSError, asyncpg.PostgresError, asyncpg.InterfaceError) as error:
        raise HTTPException(status_code=503, detail="The university knowledge database is unavailable.") from error
    return DocumentResponse(**stored.__dict__, chunks_created=chunk_count)


@app.get("/api/documents", response_model=list[DocumentResponse])
async def list_documents() -> list[DocumentResponse]:
    try:
        documents = await get_engine().knowledge.list_documents()
    except (OSError, asyncpg.PostgresError, asyncpg.InterfaceError) as error:
        raise HTTPException(status_code=503, detail="The university knowledge database is unavailable.") from error
    return [DocumentResponse(**document.__dict__) for document in documents]


@app.post("/api/voice/transcriptions", response_model=TranscriptionResponse)
async def transcribe_audio(file: UploadFile = File(...), language: str = Form(default="auto")) -> TranscriptionResponse:
    if language not in {"auto", "en", "hi"}:
        raise HTTPException(status_code=422, detail="Language must be auto, en, or hi.")
    audio = await file.read()
    if len(audio) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio recordings must be 25 MB or smaller.")
    try:
        text = await speech_to_text.transcribe(audio, language)
    except VoiceProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    detected = "hi" if language == "hi" or any("\u0900" <= char <= "\u097f" for char in text) else "en"
    return TranscriptionResponse(text=text, language=detected, provider=type(speech_to_text).__name__.removesuffix("Provider"))


@app.post("/api/voice/speech")
async def synthesize_speech(request: SpeechRequest) -> Response:
    if text_to_speech is None:
        raise HTTPException(status_code=503, detail="Text-to-speech is not configured.")
    spoken_text = to_spoken_text(request.text, request.language)
    if not spoken_text:
        raise HTTPException(status_code=422, detail="There is no speakable text in this request.")
    try:
        audio = await text_to_speech.synthesize(spoken_text, request.language)
    except VoiceProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return Response(content=audio, media_type="audio/wav", headers={"Content-Disposition": "inline; filename=university-response.wav"})
