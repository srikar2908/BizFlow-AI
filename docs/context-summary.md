# Context Summary

BizFlow AI is a production-style full-stack Agentic RAG Automation Platform for SMEs.

## Stack

- Backend: FastAPI, Python 3.12, uv
- Frontend: Next.js, TypeScript, Tailwind
- Database/Auth/Storage: Supabase, Postgres, pgvector, RLS
- AI: LiteLLM routing to DeepSeek, OpenAI, Claude
- Automation: n8n webhooks
- Observability: Langfuse
- Testing: Pytest, Ruff, Mypy, frontend typecheck/build

## MVP

- Auth
- Document upload
- RAG ingestion
- RAG chat with citations
- Metadata extraction
- Proposal generation
- Human-approved n8n workflow trigger

## Hard Rules

- No fake endpoints.
- No mock-only frontend.
- All model calls go through `model_router.py`.
- All n8n calls go through `n8n_service.py`.
- Every user-owned table has `user_id` and RLS.
- External workflows require human approval.
- Uploaded documents are untrusted data.

## Current State

The repository has a functioning FastAPI and Next.js application with Supabase auth, PDF/DOCX/TXT/MD upload and ingestion, Gemini embeddings and grounded RAG answers, metadata/summary/proposal/email draft generation, and approval-gated n8n workflow execution. The workflow service uses conditional owner-scoped transitions, persisted idempotency keys, and strict n8n completion validation. The user reports their n8n/Google Sheets integration works; this checkout has not independently contacted it.

The dashboard and settings UI now call authenticated backend endpoints. Dashboard activity is recorded forward-only by additive migration `0003_activity_events.sql`; remote database schema and migration history remain unverified. Chat messages remain page-local and are not persisted. CSV is deliberately rejected because ingestion does not implement CSV extraction. The model router remains a stub while the implementation currently uses Gemini directly.

## Key Design Boundaries

- Frontend authenticates with Supabase and talks to real backend routes.
- Backend validates auth and ownership before every user-owned operation.
- Supabase RLS provides database-level isolation.
- RAG retrieves only from the authenticated user's chunks.
- Model calls are centralized through `model_router.py`.
- n8n calls are centralized through `n8n_service.py`.
- Langfuse traces model and RAG activity without logging secrets or full sensitive documents.
