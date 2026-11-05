# Testing Strategy

## Goals

Testing must prove that BizFlow AI is real, integrated, and safe enough for production-style development. Mocking is acceptable for isolated unit tests, but the MVP cannot rely on fake endpoints or a mock-only frontend.

## Backend Checks

Required future commands:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

Backend tests should cover:

- Authenticated route access
- User ownership checks
- RLS-sensitive repository behavior
- Document ingestion status transitions
- RAG retrieval scoping
- Citation response shape
- Metadata extraction schemas
- Proposal generation orchestration
- Workflow approval requirements
- `model_router.py` as the only model integration boundary
- `n8n_service.py` as the only n8n integration boundary

## Frontend Checks

Required future commands:

```bash
npm run typecheck
npm run build
```

If the frontend package manager differs later, update this document.

Frontend tests or checks should cover:

- Authenticated and unauthenticated states
- Document upload flow
- Ingestion status display
- Chat with citations display
- Metadata extraction result display
- Proposal draft display
- Workflow approval confirmation
- Error and loading states from real API contracts

## Database Tests

Database verification should include:

- RLS enabled on all user-owned tables.
- Users cannot select, insert, update, or delete another user's rows.
- Vector retrieval is scoped to the authenticated user.
- Workflow requests cannot be approved or triggered across users.

## Integration Tests

At minimum, future integration tests should exercise:

1. Sign in or authenticate test user.
2. Upload/register a document.
3. Ingest document.
4. Ask a RAG question.
5. Verify answer contains citations.
6. Generate metadata extraction.
7. Generate proposal draft.
8. Prepare workflow request.
9. Approve workflow request.
10. Verify n8n call is made through the service boundary.

## Test Data

Test documents must be safe synthetic fixtures. Include prompt injection examples to confirm uploaded document text cannot override system behavior.

## CI Expectations

Before merging future implementation work, CI should run:

- Backend lint
- Backend typecheck
- Backend tests
- Frontend typecheck
- Frontend build
- Database migration checks when migrations exist
