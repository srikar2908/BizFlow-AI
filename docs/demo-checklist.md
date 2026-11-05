# BizFlow AI Demo Checklist

Use this checklist before recording or presenting the portfolio demo.

## Environment

- Backend is running on `http://localhost:8001`.
- Frontend is running on `http://localhost:3000`.
- Supabase project is configured.
- Supabase Storage bucket `documents` exists and is private.
- RLS policies and grants are applied for `documents`, `document_chunks`, and `workflow_runs`.
- Gemini API key is configured.
- `DEFAULT_CHAT_MODEL=gemini-2.5-flash`.
- `DEFAULT_EMBEDDING_MODEL=gemini-embedding-001`.
- n8n production webhook URL is configured.
- n8n webhook secret is configured.
- Langfuse keys and host are configured if traces will be shown.
- Google Sheets workflow log is connected in n8n.

## Demo Data

- Use `docs/demo-assets/client_brief_abc_logistics.txt`.
- Use a clean test user account.
- Confirm the document is not already uploaded if you want to show a fresh upload.
- If a duplicate upload appears, explain SHA-256 duplicate detection.

## Walkthrough

1. Log in.
2. Upload `client_brief_abc_logistics.txt`.
3. Ingest the document.
4. Ask: "What problem is this client trying to solve?"
5. Show answer citations.
6. Extract metadata.
7. Generate summary.
8. Generate proposal.
9. Generate email draft.
10. Preview workflow.
11. Approve workflow.
12. Execute workflow.
13. Show completed workflow status.
14. Show Google Sheets row.
15. Show Langfuse trace.

## Talking Points

- Real auth and backend-protected routes.
- Private Supabase Storage for originals.
- User isolation with `user_id`, RLS, and grants.
- Gemini embeddings and pgvector retrieval.
- Gemini 2.5 Flash grounded generation.
- Structured JSON outputs are validated before persistence.
- Human approval is required before workflow execution.
- n8n handles external automation, not the frontend.
- Langfuse traces are best-effort and do not include secrets or private document text.

## Screenshots To Capture

- `docs/screenshots/login.png`
- `docs/screenshots/documents-upload.png`
- `docs/screenshots/ingestion-completed.png`
- `docs/screenshots/chat-answer.png`
- `docs/screenshots/metadata-summary.png`
- `docs/screenshots/proposal-email.png`
- `docs/screenshots/workflow-approval.png`
- `docs/screenshots/google-sheets-log.png`
- `docs/screenshots/langfuse-trace.png`

## Final Checks

```bash
cd apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest

cd ../web
npm run lint
npm run build
```
