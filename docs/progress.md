# Progress

## Phase 1: Workflow Reliability and Idempotent Execution (2026-11-05)

### Implemented

- Replaced read-then-unconditional workflow state updates with owner-scoped conditional PATCH transitions for approval, execution claim and result persistence.
- Approval now records `approved_at`; execution persists a stable idempotency key and `execution_started_at` before the webhook call.
- Definite pre-delivery connection failures become retryable `failed` runs; retries reuse the persisted key. Ambiguous HTTP failures, timeouts and malformed/mismatched responses become `unknown` and are not automatically retried.
- Added a strict synchronous n8n completion response schema and configurable `N8N_REQUEST_TIMEOUT_SECONDS`.
- Added lifecycle/result fields to the API response schema and support for the `unknown` status. Preserved legacy `sent` status for reading; it is not executable.
- Updated the workflow UI with unknown outcome and stale-running guidance and an explicit retry action only for known definite failures.
- Added `docs/WORKFLOW_EXECUTION.md` and `docs/N8N_SETUP.md`; updated `.env.example` with the timeout variable.

### Verification

- Full backend suite using the existing `apps/api/bizflowai` environment with a process-local `BIZFLOW_DEFAULT_CHAT_MODEL=gemini-2.5-flash` override: 93 passed.
- Backend Ruff check, Ruff format check, and Mypy passed.
- Frontend ESLint, `npx tsc --noEmit`, and production `npm run build` passed.
- One initial un-overridden full-suite run had 91 passed and one configuration test failed because the active environment resolved a different chat model than the test expects. No environment files were inspected or changed.
- Tests mock all n8n HTTP calls and model conditional database updates in memory. No live Supabase/n8n/Google Sheets/email request was made.
- Migration `0002` remains unapplied and is required before deploying these workflow endpoints because they read/write its columns.
- End-to-end idempotency is not claimed: a durable n8n deduplication workflow is not present in the repository.

## Phase 0: Data Safety and Migration Review (2026-11-05)

### Completed

- Read `docs/PROJECT_AUDIT.md` and inspected all migration files present before this phase (one file: `0001_initial_schema.sql`).
- Compared local table definitions and workflow fields with backend REST usage, Pydantic schemas, and database documentation.
- Replaced stale `docs/database-schema.md` with an evidence-based description of the local migration and a separate proposal section. Live schema remains unverified.
- Added `docs/MIGRATION_SAFETY.md` with destructive SQL findings, live-schema preflight, apply checks, and data-preserving rollback guidance.
- Added unapplied, additive `supabase/migrations/0002_workflow_execution_metadata.sql` for nullable workflow lifecycle/result/idempotency fields and a partial unique index.

### Safety Boundary

- No SQL was run; no live Supabase project was contacted.
- `0001_initial_schema.sql` was not rerun or modified in this phase.
- No existing rows or document chunks were changed.
- Applying `0002` is gated on live-schema comparison, backup/recovery readiness, review of exact SQL, and explicit user approval.

## Repository Audit (2026-11-05)

### Completed

- Inspected the current repository structure, application routes/services, database migration, tests inventory, frontend pages, configuration, CI workflows, and project documentation.
- Added `docs/PROJECT_AUDIT.md` with the current architecture, evidence-based feature status, technical/security findings, deployment blockers, and prioritized implementation plan.

### Scope

- Audit-only; no application code or database changes were made.
- No automated checks or external integrations were run as part of this audit.
- `apps/api/.env` was not read or disclosed.

### Immediate Findings

- `supabase/migrations/0001_initial_schema.sql` drops and recreates `document_chunks`; do not rerun against data-bearing environments.
- Workflow approval/execution updates are not atomic or idempotent under concurrent requests/retries.
- `model_router.py` is still a stub; embedding and generation code call Gemini directly.
- Multiple docs describe an earlier implementation state and conflict with the current routes/schema.
- The n8n/Google Sheets live workflow is claimed in progress docs, but no workflow export is present to independently verify it.

## Current Status

Initial repository documentation is complete. Backend and frontend foundations have been started under `apps/api` and `apps/web`.

## Completed

- Defined product scope and MVP requirements.
- Documented architecture boundaries.
- Documented API contract principles and planned route surface.
- Documented planned database schema and RLS requirements.
- Documented security model.
- Documented RAG design.
- Documented testing strategy.
- Added environment variable template.
- Added git ignore rules.
- Initialized the backend with uv and Python 3.12.
- Added a FastAPI application factory in `apps/api/app/main.py`.
- Added Pydantic Settings in `apps/api/app/core/config.py`.
- Added a real `/health` endpoint.
- Added a Pytest test for `/health`.
- Added Ruff, Mypy, and Pytest configuration for the API app.
- Initialized the frontend with Next.js App Router, TypeScript, and Tailwind.
- Added a clean landing page and login placeholder.
- Added a protected dashboard layout placeholder with shared navigation.
- Added placeholder pages for documents, chat, workflows, and settings.
- Added frontend loading, empty, and error component patterns.
- Added frontend API and Supabase client placeholders.
- Added backend service skeletons for model routing, n8n workflows, and documents.
- Added typed document schemas and a placeholder `GET /documents` route.
- Added Supabase auth foundation with backend Bearer token verification and `/me`.
- Protected `GET /documents` behind the auth dependency while keeping its response empty.
- Added frontend Supabase client setup, email/password login, logout, dashboard auth gate, and API token attachment.
- Updated backend auth verification to validate access tokens through the Supabase Auth user endpoint.
- Added frontend sign-up support to the login page.
- Added real `POST /documents/upload` with authenticated multipart upload validation.
- Added SHA-256 duplicate detection per user before storing uploaded originals.
- Added Supabase Storage upload and `documents` table insertion for pending documents.
- Replaced placeholder `GET /documents` with Supabase-backed user document listing.
- Updated the frontend Documents page with real upload, loading, error, duplicate, and listing states.
- Added backend route tests for document upload auth, type validation, size limits, duplicates, and listing auth.
- Added Gemini embedding configuration and `google-genai` dependency.
- Added provider-neutral embedding service using Gemini embeddings.
- Added `POST /documents/{document_id}/ingest` for TXT/MD ingestion.
- Added TXT/MD text extraction, chunking, mocked embedding tests, chunk inserts, and document status transitions.
- Added basic authenticated RAG chunk search endpoint.
- Added Chat page search form that displays matching chunks without generating answers.
- Added basic RAG answer generation with citations from retrieved chunks.

## Not Started

- PDF/DOCX ingestion implementation
- Chat memory
- Model router implementation
- n8n service implementation
- Langfuse instrumentation

## Next Recommended Milestones

1. Smoke-test RAG answer generation against the configured Supabase project.
2. Add Langfuse instrumentation around future model and RAG calls.
3. Implement `model_router.py` through LiteLLM.
4. Implement approved workflow triggers through `n8n_service.py`.

## Rules To Preserve

- No fake endpoints.
- No mock-only frontend.
- All model calls go through `model_router.py`.
- All n8n calls go through `n8n_service.py`.
- Every user-owned table has `user_id` and RLS.
- External workflows require human approval.
- Uploaded documents are untrusted data.

## Document Upload Milestone

### Completed

- Supabase auth-protected document routes.
- Private `documents` storage bucket.
- Document upload from frontend.
- File validation.
- SHA-256 duplicate detection.
- Document metadata inserted into `public.documents`.
- Authenticated document listing.
- RLS policies and grants fixed for `authenticated` role.

### Verified

- Unauthenticated `GET /documents` returns 401.
- Authenticated user can upload `bizflow-test.txt`.
- Uploaded document appears in dashboard with status `pending`.

### Key lesson

Postgres grants and RLS are separate layers:

- Grants allow a role to access a table.
- RLS controls which rows the role can access.

### Next

Build RAG ingestion:
upload -> extract text -> chunk -> embed -> store chunks -> update status.

## RAG Ingestion Milestone

### Completed

- Added TXT/MD ingestion flow.
- Added Gemini embedding support.
- Added `document_chunks` storage with 3072-dimensional vectors.
- Added status transition: pending -> processing -> completed / failed.
- Added Ingest action in the documents dashboard.
- Verified `bizflow-test.txt` ingests into 1 chunk.

### Verified

- `bizflow-test.txt` moved to completed.
- Chunk row created in `public.document_chunks`.
- Existing DOCX remains pending because DOCX parsing is not implemented yet.

### Key decisions

- Use Gemini embeddings for now.
- Use vector(3072) for Gemini embedding compatibility.
- Start with TXT/MD only before PDF/DOCX support.

### Next

Build basic RAG chat:
question -> embed query -> retrieve chunks -> generate answer with citations.

## RAG Search Milestone

### Completed

- Added authenticated `POST /rag/search`.
- Query embeddings use the Gemini embedding service.
- Search calls a Supabase RPC over `public.document_chunks` vector similarity.
- Results are scoped to the authenticated user through Supabase auth/RLS.
- Chat page can submit a question and display matching chunks.

### Not Included

- Final AI answer generation.
- Chat memory.
- PDF/DOCX parsing.
- Hybrid search.

### Next

Build basic RAG answer generation:
question -> embed query -> retrieve chunks -> generate answer with citations.

## RAG Answer Milestone

### Completed

- Added authenticated `POST /rag/answer`.
- Reused RAG chunk search before answer generation.
- Added a provider-neutral generation service using Gemini for text generation.
- Built grounded prompts from the user question, filenames, chunk indexes, and retrieved content.
- Returned answers with citations containing document ID, filename, chunk index, and preview.
- Updated the Chat page with Search chunks and Generate answer actions.

### Not Included

- Chat memory.
- Streaming responses.
- PDF/DOCX parsing.
- Final LiteLLM model router integration.

### Next

Build basic chat history:
question -> retrieve chunks -> generate answer -> persist message and citations.

## RAG Answer Generation Milestone

### Completed

- Added grounded RAG answer generation.
- `/rag/answer` now retrieves relevant chunks and generates an answer.
- Gemini embeddings are used for retrieval.
- Gemini 2.5 Flash is used for answer generation.
- Answers include citations/sources from retrieved chunks.

### Verified

- User can ask a question from the Chat page.
- Backend retrieves ingested chunks.
- Backend generates a grounded answer.
- Frontend displays the answer.

### Key fix

- Switched chat model from `gemini-2.0-flash` to `gemini-2.5-flash` because the former caused answer generation failures in the current API setup.

### Next

- Add OCR or richer PDF layout parsing when needed.

## Document Metadata Milestone

### Completed

- Added authenticated `POST /documents/{document_id}/metadata`.
- Metadata extraction reads existing ingested chunks for the current user's document.
- Gemini 2.5 Flash generates structured metadata through the existing generation service.
- Metadata JSON is parsed, validated, and saved to `documents.metadata`.
- Generated summaries are saved to `documents.summary` when available.
- Documents page can extract and display metadata for completed documents.

### Verified

- Unauthenticated metadata extraction returns 401.
- Other users' documents remain hidden through user-scoped lookups.
- Documents without chunks return a useful ingest-first error.
- Metadata LLM calls are mocked in tests.
- Invalid JSON is handled safely.

### Not Included

- n8n workflow triggers.

### Next

- Generate reviewable email drafts before n8n workflow automation.

## Email Draft Generation Milestone

### Completed

- Added authenticated `POST /documents/{document_id}/email-draft`.
- Email draft generation requires a completed document with chunks.
- Gemini 2.5 Flash generates structured email draft JSON from document context, summary, metadata, and proposal draft when available.
- Email drafts include subject, body, purpose, recipient context, missing information questions, and call to action.
- Email drafts are saved to `documents.metadata.email_draft` without overwriting existing metadata.
- Documents page can generate, display, and copy email drafts.

### Verified

- Unauthenticated email draft requests return 401.
- Other users' documents remain hidden through user-scoped lookups.
- Documents without chunks return a useful ingest-first error.
- Email draft LLM calls are mocked in tests.
- Invalid email draft JSON is handled safely.

### Not Included

- n8n workflow triggers.
- Email sending.

### Next

- Add human approval and n8n workflow trigger support.

## Workflow Preview And Approval Milestone

### Completed

- Added authenticated `POST /workflows/preview`.
- Added authenticated `POST /workflows/{workflow_id}/approve`.
- Added authenticated `GET /workflows`.
- Workflow previews create `workflow_runs` rows with status `pending`.
- Preview payloads are built from existing document summary, metadata, proposal draft, email draft, and recommended actions.
- Approval updates workflow runs to status `approved` with `approved_by_user = true`.
- Documents page can create a workflow preview for completed documents with proposal or email draft output.
- Workflows page lists workflow runs, displays input and preview payloads, and supports approval.

### Verified

- Unauthenticated workflow endpoints return 401.
- Other users' workflow runs remain hidden through user-scoped lookups.
- Preview creation returns a pending workflow run.
- Approval returns an approved workflow run.
- Listing returns current-user workflow runs.

### Not Included

- n8n webhook calls.
- Email sending.
- New AI generation.

### Next

- Connect approved workflow runs to n8n through `n8n_service.py`.

## n8n Workflow Trigger Milestone

### Completed

- Added n8n execution configuration for webhook URL and webhook secret.
- Implemented `N8nService` as the single backend boundary for n8n webhook calls.
- Added authenticated `POST /workflows/{workflow_id}/execute`.
- Workflow execution requires status `approved` and `approved_by_user = true`.
- Execution updates workflow status `approved -> running -> completed`.
- n8n failures update workflow status to `failed` and save `error_message`.
- Workflows page can execute approved workflow runs and display running, completed, and failed states.

### Verified

- Unauthenticated execute requests return 401.
- Other users' workflow runs remain hidden through user-scoped lookups.
- Pending workflows cannot execute.
- Approved workflow execution is tested with mocked n8n calls.
- Failed mocked n8n calls mark workflows as failed.

### Not Included

- Gmail draft creation.
- Google Sheets lead logging.
- Real email sending.

### Next

- Connect the approved n8n webhook to a safe Google Sheets lead log workflow.

## n8n Google Sheets Automation Milestone

### Completed

- Connected BizFlow approved workflow execution to n8n production webhook.
- Configured n8n to receive workflow payloads without manual listening.
- Added Google Sheets append/update workflow log.
- Verified workflow status completes after n8n execution.

### Verified

- BizFlow Execute triggers n8n automatically.
- Google Sheet receives workflow payload row.
- Backend marks workflow as completed.

## Langfuse Observability Milestone

### Completed

- Added Langfuse configuration with an enabled/disabled switch.
- Added a centralized observability wrapper that no-ops when Langfuse is disabled or unconfigured.
- Instrumented RAG answer generation.
- Instrumented metadata extraction.
- Instrumented document summary generation.
- Instrumented proposal generation.
- Instrumented email draft generation.
- Instrumented workflow execution.
- Captures safe metadata such as operation name, user ID, document ID, workflow ID, model, success/failure, and latency.

### Safety

- Does not log API keys.
- Does not log webhook secrets.
- Does not log full private documents.
- Does not log full embeddings.
- App continues normally when Langfuse is disabled.

### Verified

- Disabled Langfuse behavior is a no-op in tests.
- Success traces record safe metadata.
- Failure traces record error type/message without swallowing the original error.

## Portfolio Documentation Polish

### Completed

- Rewrote `README.md` as a portfolio-grade technical README.
- Documented the product problem, solution, architecture, tech stack, AI/RAG pipeline, workflow automation pipeline, security model, observability, setup, testing, demo flow, screenshots placeholders, roadmap, and lessons learned.
- Updated the README to reflect the current implemented product state instead of the initial documentation-only phase.

### Notes

- The README calls out human approval before external workflow execution.
- The README documents RLS/grants, user isolation, private Supabase Storage handling, Gemini embeddings, Gemini 2.5 Flash, n8n Google Sheets logging, and Langfuse traces.

## Portfolio Demo Materials

### Completed

- Added a polished recruiter/interviewer demo script.
- Added a demo-ready `client_brief_abc_logistics.txt` sample document.
- Added a final demo checklist.
- Added GitHub repository profile suggestions.
- Added a tracked `docs/screenshots` folder for future screenshots.
- Updated README screenshot placeholders to match the planned screenshot filenames.

## Proposal Generation Milestone

### Completed

- Added authenticated `POST /documents/{document_id}/proposal`.
- Proposal generation requires a completed document with chunks.
- Gemini 2.5 Flash generates a structured proposal draft from document context, summary, and metadata.
- Proposal drafts include executive summary, client problem, solution, scope, deliverables, timeline, assumptions, missing information, and next steps.
- Proposal drafts are saved to `documents.metadata.proposal_draft`.
- Documents page can generate and display proposal drafts.

### Verified

- Unauthenticated proposal requests return 401.
- Other users' documents remain hidden through user-scoped lookups.
- Documents without chunks return a useful ingest-first error.
- Proposal LLM calls are mocked in tests. 
- Invalid proposal JSON is handled safely.
- Backend checks pass with 53 tests.
- Frontend lint and build pass.

### Not Included

- n8n workflow triggers.
- Email sending.

### Next

- Add human approval and n8n workflow trigger support.

## Document Summary Actions Milestone

### Completed

- Added authenticated `POST /documents/{document_id}/summary`.
- Summary generation requires an ingested completed document with chunks.
- Gemini 2.5 Flash generates concise summary, detailed summary, key points, recommended actions, and suggested workflow.
- Concise summaries are saved to `documents.summary`.
- Key points, recommended actions, suggested workflow, and detailed summary are merged into `documents.metadata`.
- Documents page can generate and display summaries and recommended actions.

### Verified

- Unauthenticated summary requests return 401.
- Other users' documents remain hidden through user-scoped lookups.
- Documents without chunks return a useful ingest-first error.
- Summary LLM calls are mocked in tests.
- Existing metadata fields are preserved during summary updates.

### Not Included

- n8n workflow triggers.
- Proposal generation.

### Next

- Build proposal generation from extracted metadata and retrieved context.

## PDF Ingestion Milestone

### Completed

- Added PDF text extraction with `pypdf`.
- Existing TXT/MD/DOCX ingestion remains supported.
- PDF text is extracted page by page.
- PDF chunks preserve page number metadata where possible.
- PDF ingestion reuses the existing chunking and Gemini embedding pipeline.

### Verified

- PDF extraction unit test covers page text and page metadata.
- Mocked embeddings are used in ingestion tests.
- Document status moves to `completed` on successful PDF ingestion.

### Not Included

- OCR for scanned PDFs.
- Rich table/layout parsing.

### Next

- Add OCR or richer PDF layout parsing when needed.

## DOCX Ingestion Milestone

### Completed

- Added DOCX text extraction.
- Reused existing chunking and Gemini embedding pipeline.
- DOCX documents can now move from pending -> processing -> completed.
- Grounded RAG answers work over ingested DOCX content.

### Verified

- DOCX upload works.
- DOCX ingestion works.
- Chat can answer questions from ingested DOCX chunks.

### Next

- Add PDF ingestion support.
