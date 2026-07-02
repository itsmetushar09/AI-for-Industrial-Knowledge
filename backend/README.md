# INDUS AI Backend

The backend currently includes the Phase 1 FastAPI foundation and Phase 2
Supabase integration: typed environment configuration, structured JSON logs,
dependency-injected async SQLAlchemy sessions, async Supabase Auth clients,
private Storage access, pgvector capability checks, and `GET /health`.

Phase 3 adds SQLAlchemy models and Alembic migrations for profiles,
departments, documents and chunks, conversations and messages, knowledge graph
nodes and edges, equipment, and audit logs. Application tables have Row Level
Security enabled by default; authenticated-user policies are introduced with
the authorization phase.

## Local setup

Python 3.12 is the supported runtime.

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Fill in `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, and
`SUPABASE_SECRET_KEY` in `.env`. Get the database URL from **Project > Connect**
and the other values from **Project Settings > API**. Legacy projects can use
`SUPABASE_ANON_KEY` and `SUPABASE_SERVICE_ROLE_KEY` instead.

Then run the idempotent Phase 2 setup once:

```powershell
python -m app.scripts.setup_supabase
```

It enables the PostgreSQL `vector` extension and creates a private `documents`
bucket restricted to PDFs up to 50 MiB. It does not create application tables;
those belong to Phase 3 migrations.

Apply and verify Phase 3 migrations with:

```powershell
python -m alembic upgrade head
python -m alembic check
python -m app.scripts.verify_schema
```

## Phase 4 document upload

Upload one PDF as multipart form data:

```powershell
curl.exe -X POST http://127.0.0.1:8000/upload `
  -F "file=@C:\path\to\manual.pdf;type=application/pdf"
```

An optional `department_id` form field accepts a department UUID. Successful
uploads return HTTP `202`, store the PDF in the private `documents` bucket, and
persist metadata with status `queued`. Run the self-cleaning integration check
with configured Supabase services using:

```powershell
python -m app.scripts.smoke_upload
```

## Phase 5 document processing

Gemini is the default free-tier AI provider. Set these values in `.env`:

```dotenv
AI_PROVIDER="gemini"
GEMINI_API_KEY="your-key"
GEMINI_EMBEDDING_MODEL="gemini-embedding-001"
GEMINI_CHAT_MODEL="gemini-2.5-flash-lite"
```

Queued uploads are processed in the background using PyMuPDF,
`cl100k_base` tokenization, 800-token chunks with 150-token overlap, and
1536-dimensional Gemini embeddings. Vectors are tagged by provider and model
so incompatible embedding spaces are never mixed. OpenAI remains available by
setting `AI_PROVIDER="openai"` and `OPENAI_API_KEY`.

Run the cost-free, self-cleaning extraction and pgvector integration check:

```powershell
python -m app.scripts.smoke_processing
```

## Phase 6 grounded chat

`POST /chat` embeds a question, retrieves the five nearest indexed chunks by
pgvector cosine distance, sends only that bounded context to the OpenAI
Responses API, and returns an answer with deterministic confidence and
document/page citations.

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat `
  -H "Content-Type: application/json" `
  -d '{"question":"Why did Pump A fail?"}'
```

Run the cost-free, self-cleaning retrieval check with:

```powershell
python -m app.scripts.smoke_chat
```

After changing AI provider or embedding model, safely re-queue incompatible
indexed and failed documents, then restart the API:

```powershell
python -m app.scripts.requeue_for_ai_provider
python -m uvicorn app.main:app --reload
```

The application still starts without Supabase values for local liveness checks.
`/health` reports each integration as `not_configured`; unavailable configured
services make the overall status `degraded`.

OpenAPI documentation is available at <http://localhost:8000/docs> and health
at <http://localhost:8000/health>.

## Tests

```powershell
cd backend
pytest
```

## Docker

```powershell
cd backend
Copy-Item .env.example .env
docker compose up --build
```

Secrets belong only in `backend/.env`; never commit that file.
