# BizFlow AI

<img width="1599" height="781" alt="image" src="https://github.com/user-attachments/assets/a26b50e9-684a-4bfe-82af-91f1ab877fe4" />

BizFlow AI is a production-style full-stack document intelligence and workflow automation platform for small and midsize businesses. It lets authenticated users upload private business documents, ingest them into a RAG index, ask grounded questions with citations, generate structured business outputs, and execute human-approved automations through n8n.

The project is built as a portfolio-grade GenAI system rather than a single demo prompt: it includes real auth, persisted document storage, user isolation, vector retrieval, model-backed extraction/generation, approval-gated workflow execution, Google Sheets logging through n8n, and Langfuse observability.

## Problem Statement

SME teams often receive valuable business context in PDFs, briefs, proposals, notes, and client documents, but turning that information into follow-ups, summaries, proposals, and workflow actions is manual and error-prone. A useful AI assistant for this domain needs more than chat: it needs private document handling, grounded answers, traceability, approval gates, and operational automation.

## Solution

BizFlow AI turns uploaded documents into reviewable business actions:

1. A user uploads a PDF, DOCX, TXT, or MD document.
2. The backend stores the original file privately in Supabase Storage.
3. The document is extracted, chunked, embedded with Gemini embeddings, and stored in Postgres/pgvector.
4. The user can search or ask questions against only their own document chunks.
5. Gemini 2.5 Flash generates grounded answers, metadata, summaries, proposal drafts, and email drafts from retrieved or ingested context.
6. The user previews and approves a workflow payload before any external automation can run.
7. n8n receives approved workflow payloads and logs workflow execution to Google Sheets.
8. Langfuse traces key GenAI and workflow operations for observability.

## Key Features

- Supabase email/password auth with backend Bearer token verification.
- Auth-protected document upload and listing.
- Private Supabase Storage bucket for original document files.
- File validation, upload size limits, SHA-256 hashing, and duplicate detection.
- TXT, MD, DOCX, and PDF ingestion.
- Gemini embeddings using `gemini-embedding-001` with 3072-dimensional vectors.
- Authenticated RAG chunk search scoped to the current user.
- Grounded RAG answer generation using Gemini 2.5 Flash with citations.
- Structured metadata extraction from ingested document chunks.
- Concise and detailed document summaries with recommended actions.
- Proposal draft generation for completed documents.
- Email draft generation from document context and proposal metadata.
- Workflow preview and human approval before external execution.
- n8n webhook execution for approved workflows only.
- Google Sheets workflow logging through n8n.
- Langfuse tracing for RAG, extraction, generation, and workflow execution.
- Backend tests for auth, ingestion, RAG, document intelligence, workflow approval, n8n execution, and observability behavior.

## Architecture

```text
apps/web              Next.js dashboard
  app/dashboard       Documents, Chat, Workflows, Settings
  src/lib             Supabase and API clients

apps/api              FastAPI backend
  app/api             Auth, documents, RAG, workflow routes
  app/core            Settings and auth dependencies
  app/services        Document, ingestion, embedding, generation, n8n, observability services
  tests               Pytest coverage for backend slices

supabase/migrations   Postgres, pgvector, RLS, grants, storage metadata tables
docs                  Product, architecture, security, RAG, progress, decisions
```

High-level runtime flow:

```text
Next.js dashboard
  -> FastAPI API with Supabase access token
  -> Supabase Auth verifies identity
  -> Supabase Storage stores originals privately
  -> Postgres + pgvector stores document metadata and chunks
  -> Gemini generates embeddings and text outputs
  -> Langfuse traces GenAI/workflow operations
  -> n8n executes approved workflow payloads
  -> Google Sheets receives workflow log rows
```

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js App Router, React, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.12, uv, Pydantic Settings |
| Auth | Supabase Auth |
| Database | Supabase Postgres, pgvector, RLS policies and grants |
| Storage | Supabase Storage private `documents` bucket |
| AI | Google Gemini embeddings and Gemini 2.5 Flash generation |
| Parsing | `python-docx` for DOCX, `pypdf` for PDF |
| Automation | n8n webhook workflow, Google Sheets logging |
| Observability | Langfuse |
| Testing | Pytest, Ruff, Mypy, ESLint, Next.js build |

## AI/RAG Pipeline

The current RAG pipeline is document-grounded and user-scoped:

1. Upload validates extension and max size.
2. Backend computes a SHA-256 hash for duplicate detection.
3. Original file is stored in Supabase Storage.
4. A `documents` row is inserted with status `pending`.
5. Ingestion downloads the original file and extracts text:
   - TXT/MD: direct text extraction
   - DOCX: paragraph text extraction
   - PDF: page-by-page text extraction with page metadata where available
6. Text is chunked and embedded with Gemini `gemini-embedding-001`.
7. Chunks are stored in `public.document_chunks` with `extensions.vector(3072)`.
8. RAG search embeds the query and searches chunks by vector similarity.
9. RAG answer generation uses retrieved chunks, filenames, and chunk indexes to build a grounded prompt.
10. Answers return citations with document IDs, filenames, chunk indexes, and previews.

The system treats uploaded documents as untrusted data. Prompts explicitly instruct the model not to follow instructions inside uploaded documents and to answer only from retrieved context.

## Workflow Automation Pipeline

BizFlow AI uses an approval-first automation model:

```text
Generated proposal/email
  -> workflow preview
  -> user approval
  -> workflow_run status approved
  -> execute
  -> n8n webhook
  -> Google Sheets log row
  -> workflow_run status completed or failed
```

Important behavior:

- Workflow previews are built from existing document metadata, summaries, proposal drafts, email drafts, and recommended actions.
- A workflow starts as `pending`.
- A user must explicitly approve it before execution.
- Only `approved` workflows with `approved_by_user = true` can execute.
- Execution moves status through `running` to `completed` or `failed`.
- n8n errors are saved to `workflow_runs.error_message`.
- No email is sent directly by the backend.

## Security Model

- Supabase Auth is the source of user identity.
- Backend routes require Bearer tokens for protected actions.
- User-owned tables include `user_id`.
- RLS policies isolate rows by `auth.uid()`.
- Postgres grants and RLS are treated as separate layers:
  - Grants allow the authenticated role to access a table.
  - RLS decides which rows the role can access.
- Original uploads are stored in a private Supabase Storage bucket.
- Service role keys are never exposed to the frontend.
- Public frontend config only receives Supabase URL/anon key and API base URL.
- Workflow execution requires persisted human approval.
- n8n webhook secrets stay server-side.
- Langfuse traces do not include API keys, webhook secrets, full private documents, or full embeddings.

## Observability

Langfuse tracing is integrated through a backend observability wrapper. It is best-effort: if Langfuse is disabled or unavailable, the application continues normally.

Instrumented operations:

- `rag_answer`
- `metadata_extraction`
- `document_summary`
- `proposal_generation`
- `email_draft_generation`
- `workflow_execution`

Safe trace metadata includes operation name, user ID, document ID, workflow ID where applicable, model name, success/failure, latency, and error type/message. The app deliberately avoids logging full prompts, private document contents, embeddings, API keys, Supabase service role keys, and n8n webhook secrets.

## Local Setup

Prerequisites:

- Python 3.12
- uv
- Node.js and npm
- Supabase project with Auth, Storage, Postgres, pgvector, RLS policies, and grants configured
- Gemini API key
- Optional: n8n workflow webhook and Langfuse project

Install backend dependencies:

```bash
cd apps/api
uv sync
```

Install frontend dependencies:

```bash
cd apps/web
npm install
```

Run the backend:

```bash
cd apps/api
uv run uvicorn app.main:app --reload --port 8001
```

Run the frontend:

```bash
cd apps/web
npm run dev
```

Default local URLs:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8001`

## Environment Variables

Start from the template:

```bash
cp .env.example .env
```

The frontend also uses `apps/web/.env.local` for public browser variables.

Core variables:

```bash
GEMINI_API_KEY=
DEFAULT_EMBEDDING_PROVIDER=gemini
DEFAULT_EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSIONS=3072
DEFAULT_CHAT_PROVIDER=gemini
DEFAULT_CHAT_MODEL=gemini-2.5-flash

NEXT_PUBLIC_API_BASE_URL=http://localhost:8001

SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
SUPABASE_STORAGE_BUCKET=documents
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=

N8N_BASE_URL=
N8N_WEBHOOK_SECRET=
N8N_WORKFLOW_WEBHOOK_URL=

LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_ENABLED=false

MAX_UPLOAD_BYTES=20971520
```

Do not commit `.env`, `apps/api/.env`, `apps/web/.env.local`, API keys, webhook secrets, or service role keys.

## Testing Commands

Backend:

```bash
cd apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```

Frontend:

```bash
cd apps/web
npm run lint
npm run build
```

## Demo Flow

1. Sign up or log in.
2. Upload `docs/demo-assets/client_brief_abc_logistics.txt` or another PDF, DOCX, TXT, or MD document.
3. Ingest the document.
4. Ask a question on the Chat page and review cited chunks or a grounded answer.
5. Extract metadata from the completed document.
6. Generate a summary and recommended actions.
7. Generate a proposal draft.
8. Generate an email draft.
9. Preview a workflow from the document output.
10. Approve the workflow.
11. Execute the approved workflow.
12. Confirm the workflow is marked completed and logged through n8n/Google Sheets.
13. Review Langfuse traces for model and workflow operations.

## Screenshots

Screenshots can be added here as the final demo environment is captured:

| Screen | Placeholder |
| --- | --- |
| Login | `docs/screenshots/login.png` |
| Document upload | `docs/screenshots/documents-upload.png` |
| Ingestion completed | `docs/screenshots/ingestion-completed.png` |
| RAG answer with citations | `docs/screenshots/chat-answer.png` |
| Metadata and summary | `docs/screenshots/metadata-summary.png` |
| Proposal and email draft | `docs/screenshots/proposal-email.png` |
| Workflow approval | `docs/screenshots/workflow-approval.png` |
| Google Sheets workflow log | `docs/screenshots/google-sheets-log.png` |
| Langfuse trace | `docs/screenshots/langfuse-trace.png` |

## Roadmap

- Persist chat sessions and message history.
- Add richer PDF extraction/OCR for scanned documents.
- Add hybrid search over vectors and keywords.
- Add Gmail draft creation after approval.
- Add more workflow templates for CRM, Slack, Telegram, and lead routing.
- Expand Langfuse metrics and dashboards.
- Complete final LiteLLM/model router abstraction for multi-provider routing.
- Add end-to-end browser tests for the core demo flow.

## Lessons Learned

- RAG apps need ownership and isolation as much as retrieval quality. Supabase Auth, `user_id`, RLS, and grants are core architecture, not extras.
- Postgres grants and RLS solve different problems; both must be correct before authenticated Supabase REST calls behave.
- AI workflow systems should generate reviewable payloads before triggering external actions.
- Human approval is the boundary between model output and real-world automation.
- Observability must be best-effort. A tracing provider should never break a user-facing GenAI flow.
- Provider and model settings need regression tests because a small config drift can break answer generation.
- Private document content, prompts, embeddings, API keys, and webhook secrets should stay out of logs and traces.
