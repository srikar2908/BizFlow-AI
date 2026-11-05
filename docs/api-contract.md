# API Contract

## Status

Auth, health, document listing, and original document upload are implemented. RAG ingestion, extraction, chat, proposal generation, and workflow routes remain planned.

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
| `GET` | `/documents/{document_id}` | Planned | Get document metadata and ingestion status |
| `POST` | `/documents/{document_id}/ingest` | Planned | Start ingestion for an uploaded document |
| `POST` | `/chat/sessions` | Planned | Create a chat session scoped to the user |
| `POST` | `/chat/sessions/{session_id}/messages` | Planned | Ask a RAG question and receive cited answer |
| `POST` | `/documents/{document_id}/extract-metadata` | Planned | Extract structured metadata from a document |
| `POST` | `/proposals` | Planned | Generate a proposal draft from user input and retrieved context |
| `POST` | `/workflow-requests` | Planned | Prepare an external workflow request for review |
| `POST` | `/workflow-requests/{request_id}/approve` | Planned | Approve and trigger an n8n workflow |

## Document Upload

`POST /documents/upload` accepts a multipart `file` field. The backend:

- Requires Supabase auth.
- Allows only `pdf`, `docx`, `txt`, `md`, and `csv` filename extensions.
- Enforces `MAX_UPLOAD_BYTES`, defaulting to 20MB.
- Computes a SHA-256 hash over the uploaded bytes.
- Detects duplicates per authenticated user by `user_id + file_hash`.
- Stores the original file in the `documents` Supabase Storage bucket.
- Inserts a `documents` row with status `pending`.
- Does not extract text, create embeddings, or start RAG ingestion.

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
