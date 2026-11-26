# AI University Digital Human

An avatar-led, multilingual university assistant. The project is intentionally being built in phases so the core interaction is polished before external AI and media services are introduced.

## Delivery roadmap

1. **Foundation and experience shell** — monorepo, responsive avatar-first UI, English/Hindi selection, local conversation state, quick actions, and provider contracts.
2. **Conversation intelligence** — FastAPI chat API, LLM provider selection (Gemini, OpenRouter, Ollama), streamed answers, language detection, and session context.
3. **Verified university knowledge** — PostgreSQL/pgvector, document ingestion, retrieval, citations, and a document-management API.
4. **Voice and avatar** — Whisper STT, Piper TTS, avatar-provider integration, and synchronized interaction states.
5. **Campus experience** — campus data, an interactive map, events/notices, and contextual actions.
6. **Hardening and delivery** — accessibility pass, tests, Docker Compose, observability, and kiosk/mobile polish.

## Phase 1: run the experience shell

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

The backend starter may be run independently:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Configure Phase 2 chat

Copy `.env.example` to `.env` and select one provider. For a hosted option, use `LLM_PROVIDER=gemini` with `GEMINI_API_KEY`, or `LLM_PROVIDER=openrouter` with `OPENROUTER_API_KEY`. For a local option, use `LLM_PROVIDER=ollama`, start Ollama, and set `OLLAMA_MODEL` to an installed model.

`POST /api/chat` accepts a message, optional `conversation_id`, and `language` (`auto`, `en`, or `hi`). `POST /api/chat/stream` returns server-sent events for the same request.

## Phase 3: verified university knowledge

Start the database with `docker compose up -d postgres`, then install the local embedding model once:

```bash
ollama pull nomic-embed-text
```

Upload university `.pdf` or `.txt` files to `POST /api/documents` with `file` and `title` multipart fields; optional fields are `category`, `department`, `academic_year`, and `version`. The service chunks the document, creates local Ollama embeddings, stores them in pgvector, and returns source citations from verified retrieval in every chat response.

## Phase 4: voice and avatar

The frontend now sends chat requests to the FastAPI service, transitions the avatar through listening, thinking, speaking, idle, and error states, and can record microphone audio in browsers that support `MediaRecorder`.

Install the backend requirements to enable local Whisper transcription. The first recording downloads the model selected by `WHISPER_MODEL`. For local speech output, install the Piper executable, download a compatible voice model, and configure its absolute file path:

```dotenv
PIPER_EXECUTABLE=piper
PIPER_ENGLISH_MODEL=/absolute/path/to/english-voice.onnx
PIPER_HINDI_MODEL=/absolute/path/to/hindi-voice.onnx
```

`POST /api/voice/transcriptions` accepts a multipart `file` and optional `language` (`auto`, `en`, or `hi`). `POST /api/voice/speech` accepts JSON with `text` and `language`, and returns WAV audio using that language's configured voice. Until Piper is configured, text chat still works and the avatar returns to idle without audio.

For a higher-quality local demo on macOS, set `TTS_PROVIDER=macos`. The default configuration uses the installed Indian voices `Tara` (English) and `Lekha` (Hindi); Piper remains the portable option for other platforms and deployment.

## Structure

```text
frontend/  Next.js UI
backend/   FastAPI API and provider contracts
ai/        Future AI integration assets
avatar/    Future avatar integrations
database/  Database migrations and seeds
docs/      Project documentation
tests/     Cross-service tests
scripts/   Development tooling
```
