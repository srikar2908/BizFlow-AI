# API Contract

## Status

The routes below reflect the current implementation in `apps/api/app/api`. Errors use FastAPI's `{ "detail": "..." }` response shape; the nested `error` shape below remains a future contract and must not be assumed by clients.

## Contract Rules

- No fake endpoints.
- No mock-only frontend calls.
- Every route must validate the authenticated user.
- Every route that accesses user-owned data must enforce `user_id` ownership.
- Request and response bodies must use typed schemas.
- Errors must use a consistent JSON shape.
- Model-backed routes must call `model_router.py`.
- n8n-backed routes must call `n8n_service.py`.

## Authentication

The frontend uses Supabase Auth. Backend requests should include the Supabase access token. The backend validates the token and derives `user_id` from the authenticated identity, not from client-provided body fields.

## Standard Error Shape

Planned error response:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

Do not expose provider stack traces, secrets, SQL details, or internal webhook URLs.

## MVP Routes

| Method | Path | Status | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | Implemented | Backend health check |
| `GET` | `/me` | Implemented | Return authenticated Supabase user identity |
| `GET` | `/documents` | Implemented | List current user's documents |
| `POST` | `/documents/upload` | Implemented | Validate and store original document upload |
| `GET` | `/dashboard` | Implemented | Return authenticated user's overview and persisted recent activity |
| `GET` | `/settings` | Implemented | Return account and safe service-configuration presence flags |
| `POST` | `/documents/{document_id}/ingest` | Implemented | Ingest an uploaded document |
| `POST` | `/documents/{document_id}/metadata` | Implemented | Extract structured metadata |
| `POST` | `/documents/{document_id}/summary` | Implemented | Generate a summary |
| `POST` | `/documents/{document_id}/proposal` | Implemented | Generate a proposal draft |
| `POST` | `/documents/{document_id}/email-draft` | Implemented | Generate an email draft (does not send it) |
| `POST` | `/rag/search` | Implemented | Search the current user's document chunks |
| `POST` | `/rag/answer` | Implemented | Generate a document-grounded answer with citations |
| `POST` | `/workflows/preview` | Implemented | Persist a workflow preview |
| `GET` | `/workflows` | Implemented | List the current user's workflow runs |
| `POST` | `/workflows/{workflow_id}/approve` | Implemented | Approve a pending workflow |
| `POST` | `/workflows/{workflow_id}/execute` | Implemented | Execute an explicitly approved workflow via n8n |
| `GET` | `/documents/{document_id}` | Planned | Get one document's details and ingestion status |
| `POST` | `/chat/sessions` | Planned | Persist a chat session (current chat history is page-local only) |

## Document Upload

`POST /documents/upload` accepts a multipart `file` field. The backend:

- Requires Supabase auth.
- Allows only `pdf`, `docx`, `txt`, and `md` filename extensions.
- Enforces `MAX_UPLOAD_BYTES`, defaulting to 20MB.
- Computes a SHA-256 hash over the uploaded bytes.
- Detects duplicates per authenticated user by `user_id + file_hash`.
- Stores the original file in the `documents` Supabase Storage bucket.
- Inserts a `documents` row with status `pending`.
- The UI separately calls the ingestion route; upload does not ingest automatically.

## Citation Requirements

RAG chat and proposal responses that rely on document context must return citations. A citation should include:

- `document_id`
- `chunk_id`
- Human-readable document name
- Optional page, section, or character offsets when available
- Short excerpt suitable for display

## Workflow Approval Requirements

Workflow trigger routes must:

- Load the prepared workflow request from the database.
- Confirm it belongs to the authenticated user.
- Confirm the user explicitly approved it.
- Persist approval metadata before calling n8n.
- Call n8n only through `n8n_service.py`.
- Persist the trigger result.

## Versioning

The initial API may ship unversioned during local MVP development. Before external release, prefer `/api/v1` or equivalent versioning.
