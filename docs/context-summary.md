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

The repository contains FastAPI and Next.js foundations with Supabase auth, protected backend routes, and an initial document upload/listing slice. Users can upload original PDF, DOCX, TXT, MD, and CSV files; the backend validates size/type, hashes bytes, detects duplicates per user, stores originals in Supabase Storage, and inserts pending document rows. RAG ingestion, extraction, embeddings, chat, proposal generation, and workflow execution have not started.

## Key Design Boundaries

- Frontend authenticates with Supabase and talks to real backend routes.
- Backend validates auth and ownership before every user-owned operation.
- Supabase RLS provides database-level isolation.
- RAG retrieves only from the authenticated user's chunks.
- Model calls are centralized through `model_router.py`.
- n8n calls are centralized through `n8n_service.py`.
- Langfuse traces model and RAG activity without logging secrets or full sensitive documents.
