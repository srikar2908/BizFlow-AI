# Database Schema

**Updated:** 2026-11-05
**Source examined:** checked-in migrations `0001_initial_schema.sql`, `0002_workflow_execution_metadata.sql`, `0003_activity_events.sql`, plus current backend queries/schemas.
**Live status:** not inspected. The database connected to the running application may differ from these migrations. The two additive migrations are proposals until separately applied and verified. Confirm actual relations, columns, constraints, indexes, policies, grants, extensions, RPC definitions and migration history before applying SQL.

This document separates the local schema definition from application usage and proposed schema evolution. It is not evidence that the live Supabase project has this schema.

## Existing base schema (0001 definition; live presence unverified)

### `public.documents`

Defined columns: `id uuid` primary key (generated), `user_id uuid not null`, `filename text not null`, `file_hash text not null`, nullable `mime_type`, `size_bytes bigint`, `storage_path`, `summary`, `status`, `metadata jsonb not null default '{}'`, `created_at`, and `updated_at`. A unique constraint on `(user_id, file_hash)` provides per-user duplicate detection. The `documents` bucket name is configured in the API; bucket creation and Storage policies are not in the SQL migration.

Backend inserts/reads `user_id`, `filename`, `file_hash`, `mime_type`, `size_bytes`, `storage_path`, `status`, `summary`, `metadata`, `id`, and timestamps. Generated metadata, summary, proposal and email draft data are stored on this row, with structured generation outputs nested in `metadata`; there are no separate extraction/proposal tables.

### `public.document_chunks`

Defined columns: `id uuid` primary key (generated), `document_id uuid not null` referencing `documents(id) on delete cascade`, `user_id uuid not null`, `chunk_index int not null`, `content text not null`, nullable `token_count`, `metadata jsonb not null default '{}'`, `embedding extensions.vector(3072)`, and `created_at`.

Ingestion inserts document/user IDs, chunk index, content, estimated token count, metadata, and embedding. Search and generation read chunk content and source metadata. The RPC returns `chunk_id`, `document_id`, filename, chunk index, content and similarity. No vector index is enabled in the current working-tree migration; it uses exact vector distance ordering. The 3072-dimensional vector size is chosen for the configured Gemini embedding model.

### `public.conversations` and `public.messages`

`conversations`: `id`, `user_id`, optional title, created/updated timestamps.
`messages`: `id`, `conversation_id` referencing `conversations(id) on delete cascade`, `user_id`, role, content, metadata JSONB, created timestamp.

No current API routes/services use these relations. They do not implement persisted chat in the current application.

### `public.workflow_runs`

Defined columns: `id`, `user_id`, nullable `document_id` referencing `documents(id) on delete set null`, `workflow_type`, `status` (default `pending`), `input_payload jsonb`, `output_payload jsonb`, `approved_by_user boolean` (default false), nullable `error_message`, `created_at`, and `updated_at`.

The backend reads/writes these columns. It also joins `documents(filename)` for display. The Pydantic schema exposes workflow ID, document ID/name, workflow type, status, input/output payloads, approval boolean, error text and timestamps. It accepts a `sent` status in addition to pending/approved/running/completed/failed, although the main documented flow does not use it. The database defines no status check constraint.

The base schema has no approval/execution timestamps or dedicated execution result or n8n execution ID field. Migration `0002_workflow_execution_metadata.sql` proposes nullable fields for those values plus an idempotency key; these columns must not be assumed to exist in the live project until verified.

### `public.model_events`

Defined columns: `id`, `user_id`, optional task type/provider/model/token counts/cost/latency/status, and `created_at`. No backend code currently writes or reads this table.

## Existing constraints, indexes and relationships

- Primary keys are UUIDs with `gen_random_uuid()` defaults on all six tables.
- Unique constraint: `documents(user_id, file_hash)`.
- Foreign keys: chunks to documents (`ON DELETE CASCADE`); messages to conversations (`ON DELETE CASCADE`); workflow runs to documents (`ON DELETE SET NULL`).
- No database foreign keys connect `user_id` to `auth.users`, and no constraint verifies a chunk/message's `user_id` matches its parent row's owner.
- Explicit B-tree indexes: documents by user; documents by `(user_id,file_hash)`; chunks by user and by document; conversations by user; messages by user and conversation; workflow runs by user; model events by user. The unique document constraint already creates an index beginning with `(user_id,file_hash)`, making `idx_documents_file_hash` potentially redundant.
- No chunk-order composite index, workflow status/time composite index, or vector index is present in the current migration. Exact vector search may become costly as chunk volume grows.

## Existing RLS, policies, grants and RPC

RLS is enabled on `documents`, `document_chunks`, `conversations`, `messages`, `workflow_runs`, and `model_events`. For each table, the migration defines authenticated-role SELECT/INSERT/UPDATE/DELETE policies using `auth.uid() = user_id` (with matching `WITH CHECK` for writes). It grants `authenticated` schema usage and CRUD table privileges. These are the local migration definitions; verify the live policies and grants independently.

**Workflow security caveat:** the table-level UPDATE grant and owner-only update policy allow an authenticated owner to update any column on their own `workflow_runs` rows through PostgREST, including `status` and `approved_by_user`. Backend endpoints check state and ownership, but the database policy does not enforce allowed transitions or prevent direct field changes. A later security migration should route sensitive workflow updates through a narrowly scoped backend operation/RPC and revoke broad direct update where compatible. Do not change grants/policies until tested against the actual frontend/backend access patterns.

The migration defines `public.match_document_chunks(query_embedding vector(3072), match_count int default 5, match_user_id uuid default auth.uid())`. It joins chunks to documents, requires both row user IDs and `auth.uid()` to equal `match_user_id`, skips null embeddings, orders by cosine distance, and returns at most `least(match_count,20)` rows. EXECUTE is granted to `authenticated`. The backend calls this RPC with the caller's access token and the verified user ID. Live function body, grants, and PostgREST exposure are unverified.

## Schema differences and documentation corrections

- Older docs used `chat_sessions`/`chat_messages`, `workflow_requests`, `metadata_extractions`, and `proposals`. The migration actually creates `conversations`, `messages`, `workflow_runs`, and `model_events`; generated business outputs currently live in document columns/JSON. Do not create the old planned relations without a reviewed product need.
- The migration uses `mime_type`, while older docs called this `content_type`; it has `file_hash` and `storage_path`; no `storage_bucket` column exists.
- Backend routes and service code use the migration's `workflow_runs`, not `workflow_requests`.
- The base schema has no workflow lifecycle fields. Migration `0002` adds `approved_at`, `execution_started_at`, `completed_at`, `n8n_execution_id`, `idempotency_key`, and `execution_result`; the application requires those fields for its current workflow implementation.
- The local migration's `CREATE TABLE IF NOT EXISTS` statements do not reconcile an already-existing table's shape. `document_chunks` is an exception: it is dropped then created, so rerunning can erase all chunks and cascade to dependent objects.

## Additive workflow schema extension (migration file; live apply status unverified)

Migration file `supabase/migrations/0002_workflow_execution_metadata.sql` adds nullable columns to existing `workflow_runs`:

- `approved_at timestamptz`
- `execution_started_at timestamptz`
- `completed_at timestamptz`
- `n8n_execution_id text`
- `idempotency_key text`
- `execution_result jsonb`

Old rows remain valid because the fields are nullable and have no backfill requirement. A partial unique index on `(user_id,idempotency_key)` when the key is non-null provides a per-owner uniqueness boundary for new idempotency keys. JSONB can hold a validated result, but the database type alone does not validate a response contract; backend validation is still required. The migration does not add state constraints or RLS/grant changes. It must not be applied until the preflight checks in `docs/MIGRATION_SAFETY.md` confirm the live table and expected columns.

## Proposed dashboard activity ledger (0003; not applied here)

`supabase/migrations/0003_activity_events.sql` adds a forward-only `activity_events` table for successful document operations and workflow lifecycle actions. It stores owner, optional document reference, event type, filename-only details, and occurrence time. It adds a user/time index and owner-scoped SELECT policy. Inserts are backend-only via `service_role`; authenticated users receive no insert/update/delete grant. There is deliberately no backfill because exact historical generation and workflow event times are unavailable. Dashboard activity starts only after the migration and backend logging are deployed. Workflow status totals and recent document/workflow lists remain sourced from their existing tables.

Before applying 0003, confirm the migration is unapplied, `documents` and `auth.users` exist, RLS/grants behave as expected, and `service_role` is used only on the API server. `CREATE TABLE IF NOT EXISTS` does not validate a conflicting existing relation's shape.

## Further live checks before production

1. Inspect Supabase migration history and actual schema; compare every column/index/constraint/policy/grant/function against this local definition.
2. Confirm vector and pgcrypto extensions, their schemas, and the live vector dimension.
3. Confirm private Storage bucket existence, policies, file objects and document-to-object path consistency.
4. Confirm RLS and grants for each relation, plus direct PostgREST access behavior. Test cross-user reads/writes and parent-child ownership constraints.
5. Confirm workflow rows' current values/status vocabulary and any existing execution metadata before selecting a backfill or transition strategy.
6. Check table size, active traffic, and lock tolerance before index creation.

No live database inspection or migration execution was performed for this update. Migration files do not prove that any migration is present on the connected Supabase project.
