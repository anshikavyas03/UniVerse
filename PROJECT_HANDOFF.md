# AI University Digital Human — Project Handoff

**Last updated:** 22 August 2026  
**Current status:** Phases 1–3 are implemented and tested. Phase 4 has started with a local-first voice baseline and frontend lifecycle integration; local media runtimes still require installation and manual end-to-end validation.

## 1. Project overview and final goal

AI University Digital Human is a multilingual, avatar-led virtual university assistant. Its intended final experience is a student-facing digital human that can answer university questions in English, Hindi, and Hinglish, using verified university documents rather than invented facts.

The planned finished product includes:

- A polished web interface with an on-screen digital-human/avatar presence.
- Text and eventually voice conversations in English, Hindi, and Hinglish.
- Retrieval-augmented answers grounded in official university documents, with citations.
- A university knowledge base for regulations, admissions, fees, timetables, departments, hostel information, notices, and similar content.
- Future campus-map, notice/event, avatar, speech-to-text, and text-to-speech capabilities.

The project is deliberately being developed in phases so the product remains runnable at every milestone.

## 2. Current exact point of progress

The project is at the end of **Phase 3: Verified university knowledge**.

- The frontend is connected to the live chat API and updates avatar states across chat and voice interactions.
- The FastAPI backend is functional with a locally verified Ollama LLM configuration.
- PostgreSQL with pgvector is running through Docker.
- Document ingestion for text-based PDF and TXT files is working.
- Retrieved university-document chunks are passed to the LLM as verified context.
- Chat responses expose citations and a `verified` flag.
- No real university documents have been uploaded by the user yet. This is expected and not an error.
- Local Whisper transcription and configurable Piper synthesis endpoints are implemented. Install the optional runtimes and voice model before testing them with a microphone.

## 3. Architecture

```text
Browser / Next.js frontend (localhost:3000)
        |
        | HTTP / future streaming chat
        v
FastAPI backend (localhost:8000)
        |
        +-- Chat orchestration
        |     +-- language detection (English / Hindi / Hinglish)
        |     +-- in-memory conversation history
        |     +-- provider abstraction
        |           +-- Ollama (currently used)
        |           +-- Gemini (supported configuration)
        |           +-- OpenRouter (supported configuration)
        |
        +-- RAG / university knowledge service
              +-- parse PDF/TXT
              +-- chunk text by page
              +-- request embeddings from Ollama nomic-embed-text
              +-- save / search vectors in PostgreSQL + pgvector
              +-- return source citations
        |
        v
PostgreSQL 16 + pgvector in Docker (localhost:5432)
```

### Important request flow

1. A user uploads a PDF or TXT document through `POST /api/documents`.
2. FastAPI extracts text, chunks it, asks Ollama's embedding model for vectors, and writes the document and chunks to PostgreSQL/pgvector.
3. A user asks a question through `POST /api/chat`.
4. The backend embeds the question and searches for semantically similar document chunks.
5. If relevant chunks pass the similarity threshold, they are sent to the selected LLM as **verified university context**.
6. The chat response includes the answer, source metadata, and `verified: true` when sources were used.

## 4. Completed phases

### Phase 1 — Foundation and experience shell (completed)

Implemented:

- Next.js frontend shell with an avatar-first visual design.
- Responsive user interface.
- English/Hindi language selector.
- Local mock chat state and quick-action prompts.
- Digital-human/avatar visual states.
- Initial monorepo-style folder organization.
- Configuration and service placeholders for future AI, voice, and avatar work.

Validation completed:

- Frontend dependencies were installed.
- `npm run build` completed successfully.
- The frontend was visually checked in the browser, including basic interaction states.

### Phase 2 — Conversation intelligence (completed)

Implemented:

- FastAPI API application.
- LLM provider abstraction with implementations for Ollama, Gemini, and OpenRouter.
- Environment-based provider selection.
- Standard chat endpoint and a server-sent-events-style stream endpoint.
- English, Hindi (Devanagari), and basic Hinglish detection.
- In-memory conversation/session history.
- Friendly fallback response when the LLM is unavailable.

Validation completed:

- Ollama service connection was checked successfully.
- Installed `llama3.2:3b` model was found and called successfully.
- Direct model generation returned the expected `CONNECTION_VERIFIED` response.
- Initial language detection and session tests passed.

### Phase 3 — Verified university knowledge (completed)

Implemented:

- Docker Compose PostgreSQL 16 database using the `pgvector/pgvector:pg16` image.
- Schema initialization with `vector` and `pgcrypto` extensions.
- `documents` and `document_chunks` tables plus an HNSW cosine-similarity vector index.
- PDF and TXT parsing.
- Text cleaning and page-aware document chunking.
- Ollama embedding integration using `nomic-embed-text`.
- Document upload and document-list APIs.
- Retrieval service that adds verified context to chat prompts.
- Response source citations and `verified` status.

Validation completed:

- Docker image, network, data volume, and PostgreSQL container were started successfully.
- pgvector extension and both database tables were verified inside the running database.
- `nomic-embed-text` was downloaded successfully with Ollama.
- A temporary document was ingested, retrieved semantically, and removed after testing.
- A complete live RAG chat test through Ollama returned a fact from a temporary test document with `verified: true` and a source citation; the temporary test document was removed afterwards.
- Backend unit tests passed: 4 tests, 0 failures.

## 5. Folder structure

```text
sem7/
├── .env                       # Local machine configuration; do not commit
├── .env.example               # Safe environment-variable template
├── .gitignore
├── README.md
├── PROJECT_HANDOFF.md         # This file
├── docker-compose.yml          # PostgreSQL + pgvector service
├── frontend/                   # Next.js experience shell
│   ├── app/
│   ├── components/
│   ├── package.json
│   └── AGENTS.md               # Local frontend development guidance
├── backend/                    # FastAPI service
│   ├── .venv/                  # Local virtual environment; do not commit
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             # API application and routes
│   │   ├── core/config.py      # Environment settings
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── repositories/       # Conversation and database access
│   │   └── services/
│   │       ├── ai/             # LLM provider and conversation logic
│   │       ├── rag/            # Parsing, chunking, embeddings, retrieval
│   │       ├── avatar/         # Future avatar provider contracts
│   │       └── voice/          # Future voice provider contracts
│   └── tests/
├── database/
│   └── init.sql                # pgvector schema initialization
├── ai/                         # Future AI integration assets
├── avatar/                     # Future avatar integrations
├── docs/                       # Project documentation / optional source storage
├── scripts/                    # Development tooling
└── tests/                      # Cross-service tests
```

## 6. Technologies and dependencies

### Frontend

- Next.js
- React
- TypeScript
- ESLint / `eslint-config-next`

### Backend

- Python 3
- FastAPI
- Uvicorn
- Pydantic v2
- HTTPX
- python-dotenv
- asyncpg
- pypdf
- python-multipart

### AI and data

- Ollama (current configured LLM provider)
- `llama3.2:3b` for local chat generation
- `nomic-embed-text` for local embeddings
- PostgreSQL 16
- pgvector extension

### Infrastructure

- Docker and Docker Compose

## 7. Environment variables

Create a root `.env` file by copying `.env.example`. Never commit `.env`, API keys, or other real credentials.

```bash
cp .env.example .env
```

Current local development configuration uses Ollama:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_university
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
RAG_SIMILARITY_THRESHOLD=0.68
FRONTEND_ORIGIN=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Other supported provider variables:

```dotenv
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
OPENROUTER_API_KEY=
OPENROUTER_MODEL=
```

`WHISPER_MODEL`, `TTS_PROVIDER`, and `AVATAR_PROVIDER` are present in `.env.example` as future configuration placeholders. Phase 4 has not implemented these integrations yet.

### Security note

The Docker Compose file contains local development database defaults. Do not use those defaults in a production deployment. Use a separate secure database user/password and a secret-management system for production.

## 8. Setup from a new laptop/account

### Prerequisites

Install:

- Git (if cloning a repository)
- Node.js and npm
- Python 3
- Docker Desktop, running
- Ollama, running locally

### Get the source

Either clone the repository or copy the complete project folder. Then enter the project root:

```bash
cd /path/to/sem7
```

### Configure the environment

```bash
cp .env.example .env
```

Edit `.env` and set the provider values. For the current fully tested path, use the Ollama configuration shown in the environment section above.

### Install Ollama models

Run once after Ollama is installed and running:

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

Check installed models if needed:

```bash
ollama list
```

### Start PostgreSQL / pgvector

From the project root:

```bash
docker compose up -d postgres
```

Check it:

```bash
docker compose ps
```

The database is exposed on `localhost:5432`. On first startup, Docker runs `database/init.sql` automatically to create extensions, tables, and indexes.

### Install backend dependencies

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Start the backend

Keep the virtual environment active, then run:

```bash
uvicorn app.main:app --reload --port 8000
```

Useful URLs:

- API docs (Swagger UI): `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/health`

### Install frontend dependencies

Open a separate terminal:

```bash
cd /path/to/sem7/frontend
npm install
```

### Start the frontend

```bash
npm run dev
```

Open `http://localhost:3000`.

## 9. Starting every service: quick reference

Use separate terminals for the services below.

### Terminal 1 — Ollama

Start Ollama using the normal app/service installation for the operating system. Confirm it is available:

```bash
ollama list
```

### Terminal 2 — PostgreSQL

```bash
cd /path/to/sem7
docker compose up -d postgres
```

### Terminal 3 — FastAPI backend

```bash
cd /path/to/sem7/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Terminal 4 — Next.js frontend

```bash
cd /path/to/sem7/frontend
npm run dev
```

## 10. APIs currently available

Base URL: `http://localhost:8000`

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Reports backend status, selected provider, and startup errors. |
| `POST` | `/api/chat` | Returns a full chat response. Uses document retrieval when available. |
| `POST` | `/api/chat/stream` | Returns a streamed response using server-sent events. |
| `GET` | `/api/documents` | Lists uploaded document metadata. |
| `POST` | `/api/documents` | Uploads and indexes a PDF/TXT document. |

### Chat request example

```json
{
  "message": "What are the library timings?",
  "language": "auto",
  "conversation_id": null
}
```

`language` accepts `auto`, `en`, or `hi`. `conversation_id` is optional; reuse it to preserve the in-memory session context while the backend remains running.

The chat response includes fields such as:

- `conversation_id`
- `message`
- `language`
- `sources` — source document/page metadata when retrieval succeeded
- `verified` — `true` when verified sources were used
- `provider` — selected LLM provider name

### Upload request fields

`POST /api/documents` is multipart form data:

- Required: `file` (`.pdf` or `.txt`)
- Required: `title`
- Optional: `category`, `department`, `academic_year`, `version`

Use Swagger UI to upload without writing code:

1. Visit `http://localhost:8000/docs`.
2. Expand **POST /api/documents**.
3. Click **Try it out**.
4. Choose a text-based PDF or TXT file, enter a title, optionally fill metadata, and click **Execute**.
5. Call **GET /api/documents** to confirm it was indexed.

Documents are limited to 20 MB by the current API implementation.

## 11. Database schema

Database: `ai_university`  
Schema file: `database/init.sql`

### Extensions

- `vector` — pgvector embedding storage and similarity search.
- `pgcrypto` — UUID generation through `gen_random_uuid()`.

### `documents`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key; generated automatically. |
| `title` | TEXT | Required document title. |
| `category` | TEXT | Optional classification. |
| `department` | TEXT | Optional department. |
| `academic_year` | TEXT | Optional year. |
| `version` | TEXT | Optional document version. |
| `original_filename` | TEXT | Uploaded filename. |
| `uploaded_at` | TIMESTAMPTZ | Creation timestamp. |

### `document_chunks`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key; generated automatically. |
| `document_id` | UUID | Foreign key to `documents`; cascade deletes chunks. |
| `content` | TEXT | Extracted chunk text. |
| `page_number` | INTEGER | Source page when known. |
| `chunk_index` | INTEGER | Order within document. |
| `embedding` | `vector(768)` | Embedding produced by `nomic-embed-text`. |
| `created_at` | TIMESTAMPTZ | Creation timestamp. |

Indexes:

- Standard document-ID index: `document_chunks_document_id_idx`.
- HNSW cosine similarity index: `document_chunks_embedding_idx`.

## 12. Important development decisions

1. **Use local Ollama as the primary current path.** It avoids API cost/keys during development and was successfully verified with `llama3.2:3b` and `nomic-embed-text`.
2. **Use RAG for university-specific claims.** The system prompt tells the model not to invent university facts. University answers should be based on retrieved context and return citations.
3. **Keep provider abstraction.** Gemini and OpenRouter are supported through configuration; do not hard-code Ollama into general chat logic.
4. **Keep embeddings at 768 dimensions.** The PostgreSQL schema uses `vector(768)`, matching the current `nomic-embed-text` setup. Changing embedding models can require a schema migration and re-indexing every document.
5. **Use pgvector HNSW cosine search.** This is the implemented retrieval strategy and should be retained unless there is a deliberate migration plan.
6. **Keep source metadata.** Title, page, category, and other document metadata support trustworthy citations and should not be removed.
7. **Frontend is intentionally not yet wired to the live backend.** It is an approved visual shell for now. Integrating chat APIs can be a focused later task.
8. **Develop in phases.** Do not begin broad production hardening or replace the frontend while Phase 4–5 capabilities remain incomplete, unless the project owner changes priorities.

## 13. Known limitations / current issues

These are known current limitations, not blockers for the completed phases:

- No real university files are indexed yet; the database is expected to be empty until uploads begin.
- PDF support currently works for **text-based PDFs** only. Scanned/image-only PDFs need OCR, which is not implemented.
- Original uploaded files are not retained by the current API; extracted chunks and metadata are stored in PostgreSQL. Keep source files separately, for example in a controlled `docs/university-documents/` folder outside version control if they are sensitive.
- Document deletion, replacement, re-indexing, and administrative authentication endpoints are not implemented.
- Conversation history is in memory only. It is lost whenever FastAPI restarts and is not shared across backend instances.
- `/api/chat/stream` currently splits a completed answer into word chunks. It is not true token-by-token streaming from the LLM provider yet.
- Retrieval failure is handled gracefully but is not surfaced in a detailed user-facing diagnostics format.
- The current frontend does not yet call the live FastAPI API.
- No OCR, voice input/output, animated avatar provider, campus map, events/notices, authentication, role-based administration, analytics, deployment setup, or production observability exists yet.
- The current PostgreSQL credentials/port are development defaults only.

## 14. What a new developer must not change casually

- **Do not commit `.env`** or add real API keys to source code or documentation.
- **Do not change `vector(768)`** in `database/init.sql` without intentionally choosing a new embedding model, migrating the schema, and re-indexing existing documents.
- **Do not replace the RAG prompt constraint** that prevents invented university-specific information. It is central to the project’s trust requirement.
- **Do not remove source citations or the `verified` field** from chat responses.
- **Do not reset or delete the Docker volume casually.** It contains indexed documents. Use `docker compose down -v` only when intentionally discarding local database data.
- **Do not treat the document ingestion endpoint as a secure admin feature yet.** It currently has no authentication; do not expose it publicly as-is.
- **Do not assume a scanned PDF will work.** Test text extraction first or add OCR deliberately.
- **Do not change the frontend tooling without reading `frontend/AGENTS.md` first.** It contains project-specific frontend guidance.

## 15. Suggested next steps, in order

### Immediate manual validation (before new feature work)

1. Start Ollama, PostgreSQL, the backend, and optionally the frontend using the commands above.
2. Open `http://localhost:8000/docs` and call `GET /health`; it should report `status: "ok"` and provider `ollama` when the configuration is correct.
3. Upload one small, official, text-based university PDF or TXT through `POST /api/documents`.
4. Call `GET /api/documents` to confirm the upload and chunk count.
5. Test `POST /api/chat` with a question that is explicitly answered in that uploaded document.
6. Verify that the response has `verified: true` and a correct `sources` entry.
7. Ask a question absent from the uploaded documents. Confirm that the model does not invent a university-specific answer.

### Current implementation phase: Phase 4 — Voice and avatar

Recommended order:

1. Local-first processing is selected: the optional `faster-whisper` runtime is used for transcription and Piper is used for synthesis.
2. Voice provider interfaces and factories are implemented under `backend/app/services/voice/`.
3. `POST /api/voice/transcriptions` accepts a browser audio upload and returns its text.
4. `POST /api/voice/speech` returns synthesized WAV audio when `PIPER_MODEL` is configured.
5. The existing CSS digital-human stage remains the selected avatar implementation for this milestone.
6. The frontend now drives idle, listening, thinking, speaking, and error states from the live chat and media lifecycle.
7. Remaining work: install/configure local media dependencies and add browser-level end-to-end coverage for a real microphone and speaker.

### Following phases

- **Phase 5:** Add university campus data, map UI, notices/events, and contextual actions.
- **Phase 6:** Add authentication/authorization where needed, OCR, document administration, persistent conversations, true LLM streaming, accessibility, test coverage, Docker Compose for all services, logging/monitoring, and deployment readiness.

## 16. Useful verification commands

From the project root:

```bash
# Confirm database container status
docker compose ps

# Inspect backend tests
cd backend
source .venv/bin/activate
python -m unittest discover -s tests

# Build the frontend for production
cd ../frontend
npm run build
```

To check database extensions/tables (optional):

```bash
cd /path/to/sem7
docker compose exec postgres psql -U postgres -d ai_university -c "\\dx"
docker compose exec postgres psql -U postgres -d ai_university -c "\\dt"
```

## 17. Ownership handoff checklist

Before a teammate begins feature work, they should be able to confirm all of the following:

- [ ] `.env` exists locally and contains no committed secrets.
- [ ] Docker Desktop and Ollama are running.
- [ ] `ollama list` shows `llama3.2:3b` and `nomic-embed-text`.
- [ ] `docker compose ps` shows the PostgreSQL service running.
- [ ] `http://localhost:8000/health` responds successfully.
- [ ] `http://localhost:8000/docs` shows the five current endpoints.
- [ ] `http://localhost:3000` shows the frontend after `npm run dev`.
- [ ] At least one real, text-based university document has been uploaded and a grounded/cited answer has been manually verified.
