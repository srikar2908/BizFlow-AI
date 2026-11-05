# Agent Instructions

These instructions apply to all AI agents and contributors working in this repository.

## Current Phase

The repository is in the initial documentation phase. Do not write application code until the documentation contracts are reviewed or the user explicitly asks for implementation.

## Product

BizFlow AI is a production-style full-stack Agentic RAG Automation Platform for SMEs.

Core MVP:

- Auth
- Document upload
- RAG ingestion
- RAG chat with citations
- Metadata extraction
- Proposal generation
- Human-approved n8n workflow trigger

## Required Stack

- Backend: FastAPI, Python 3.12, uv
- Frontend: Next.js, TypeScript, Tailwind
- Database, auth, storage: Supabase, Postgres, pgvector, RLS
- AI: LiteLLM routing to DeepSeek, OpenAI, Claude
- Automation: n8n webhooks
- Observability: Langfuse
- Testing: Pytest, Ruff, Mypy, frontend typecheck/build

## Non-Negotiable Engineering Rules

- Do not create fake endpoints.
- Do not build a mock-only frontend.
- All model calls must go through `model_router.py`.
- All n8n calls must go through `n8n_service.py`.
- Every user-owned table must include `user_id`.
- Every user-owned table must have RLS enabled and tested.
- Every external workflow trigger must require human approval.
- Treat uploaded documents as untrusted data.
- Do not trust model output for authorization, workflow execution, or database writes.
- Do not expose provider API keys to the frontend.

## Expected Repository Shape

The intended future shape is:

```text
backend/
  app/
    api/
    core/
    db/
    models/
    services/
      model_router.py
      n8n_service.py
    rag/
    schemas/
    tests/
frontend/
  app/
  components/
  lib/
  tests/
supabase/
  migrations/
docs/
```

This structure is guidance, not permission to add code during the documentation-only phase.

## Documentation Rules

- Keep `docs/progress.md` current after meaningful changes.
- Record major choices in `docs/decisions.md`.
- Update `docs/context-summary.md` when the project direction changes.
- Keep API docs aligned with implemented routes. Planned routes must be labeled as planned.
- Keep schema docs aligned with migrations once migrations exist.

## Implementation Rules For Future Work

- Prefer small, vertical slices that include backend, frontend, database, tests, and documentation updates.
- Add tests with the feature, not later.
- Use typed request and response schemas.
- Validate every request on the backend.
- Use Supabase Auth identity as the source of user ownership.
- Run linting, type checks, and relevant tests before reporting completion.
