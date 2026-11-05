# Database Migration Safety Plan

**Status:** Planning only. No SQL has been executed against Supabase. The new migration in `supabase/migrations/0002_workflow_execution_metadata.sql` is unapplied and requires explicit live-schema preflight and user approval before deployment.

## Findings from checked-in migrations

There is one migration in the repository baseline, `0001_initial_schema.sql`. The current working tree contains a local edit to that file that disables a vector index; this audit did not alter it. A second file, `0002_workflow_execution_metadata.sql`, is proposed by this phase and is additive.

### Destructive or behavior-replacing SQL in `0001`

1. **`DROP TABLE IF EXISTS public.document_chunks CASCADE`** (line 33): deletes every stored chunk and embedding. `CASCADE` also removes dependent database objects such as views/constraints that depend on the table. The following `CREATE TABLE` makes an empty replacement; data cannot be recovered from that replacement. Do not rerun this migration on a database with valuable data.
2. **24 `DROP POLICY IF EXISTS` statements** (lines 108–281): remove named RLS policies from six tables before recreating the expected policies. They do not delete table rows, but overwrite those policy definitions and may remove custom policies with the same names. Whether policy replacement is transaction-atomic depends on the migration runner; do not rely on a transient safe window.
3. **`CREATE OR REPLACE FUNCTION public.match_document_chunks(...)`** (line 367): replaces the existing function body/signature implementation (for the same signature). It does not delete rows, but can change retrieval behavior and permissions/security assumptions.
4. **Foreign key delete actions:** deleting a `documents` row cascades to its chunks; deleting a `conversations` row cascades to its messages; deleting a document sets a linked workflow's `document_id` to null. These are conditional data effects, not statements run merely by applying the migration.

Other DDL uses `CREATE ... IF NOT EXISTS` or creates policies/indexes/grants. `IF NOT EXISTS` does not check that an already-existing relation has the expected shape. The initial migration as a whole is therefore not safe to rerun despite its header comment.

## Proposed additive change

`0002_workflow_execution_metadata.sql` adds nullable approval/execution timestamps, the n8n execution ID, an idempotency key and a JSONB execution result to `workflow_runs`, then adds a partial unique index on `(user_id,idempotency_key)` for non-null keys.

- No existing column is dropped, renamed, rewritten or backfilled.
- Existing rows receive `NULL` for newly added columns where the column does not already exist.
- The unique index does not index legacy rows with null keys. If the live table already has a populated `idempotency_key`, duplicates can make index creation fail; preflight must detect this.
- `execution_result jsonb` is a storage type, not a result validator. Application code must validate and normalize n8n responses before persisting them.
- The migration intentionally does not change RLS, grants, status constraints, or RPCs. Those require a separate authorization design and tests.

Although the SQL is additive and uses `IF NOT EXISTS`, it assumes `public.workflow_runs` exists and that any same-named live columns have compatible types/meaning. This is why it must not be applied until the actual project schema is checked.

## Required preflight before any apply

1. **Confirm target and ownership:** select the correct Supabase project/environment and confirm with the project owner. Never infer production schema from this checkout.
2. **Inspect migration history:** use Supabase migration history to determine which migration files are recorded as applied. Do not mark or replay migrations to force alignment.
3. **Read-only schema comparison:** inspect `information_schema.columns`, `pg_constraint`, `pg_indexes`, `pg_policies`, grants/privileges, extension versions/schemas, and the live RPC definition. Compare against `docs/database-schema.md`. Confirm `workflow_runs` and `user_id` exist; verify each proposed column name, type, nullability and current values.
4. **Data preflight:** record row counts and status counts for `workflow_runs`. If `idempotency_key` already exists, check non-null duplicates by `(user_id,idempotency_key)` and determine ownership/meaning. Do not modify rows to make the index succeed without a reviewed plan.
5. **Storage/data baseline:** independently confirm document and chunk counts, storage bucket/object presence, and backup/restore availability. No DDL should be used to “repair” discrepancies during this phase.
6. **Backup and recovery readiness:** take/confirm a current recoverable backup or point-in-time restore capability and document the recovery owner/process. Check that a restore can be performed to a separate environment before relying on it.
7. **Operational review:** assess table size, active workflow traffic and lock tolerance. Adding an index can consume resources and take locks; choose a maintenance window if necessary. If a concurrent index build is required, prepare a separately reviewed migration because `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block.
8. **Review exact SQL:** review `0002` against the confirmed live schema. Make no edit to or replay of `0001` as part of this change.
9. **Approval gate:** present the target, preflight diff, backup status, exact SQL, maintenance window and rollback decision to the user. Apply only after explicit approval.

## Apply and verification plan (future; not performed)

After approval, apply the reviewed migration once through the project's normal Supabase migration mechanism, with output captured. Then perform read-only checks that the six columns have the intended types, the partial unique index exists and is valid, old workflow row counts/statuses are unchanged, and document/chunk counts are unchanged. Check PostgREST schema cache if the new fields are later consumed through REST. Test insert/update behavior only in a controlled test environment; do not send live n8n requests as part of a schema migration check.

The schema fields alone do **not** make execution idempotent. Backend code must atomically claim a workflow, reuse a stable idempotency key across retries, and send the same key to n8n; the n8n side must also deduplicate side effects. Those implementation and integration tests are outside this Phase 0 database review.

## Rollback and recovery

- **Before apply:** do not change the live project. Fix the proposed migration or abandon it.
- **If apply fails:** capture the error and inspect actual state before retrying. Do not rerun `0001`. Confirm whether the migration runner rolled back the failed transaction; do not assume it did.
- **After successful additive apply:** preferred rollback is application rollback/feature disable while leaving the new nullable columns and index in place. This preserves any data that may have been written to the fields.
- **Index-only rollback:** dropping the new unique index may be considered only if no running code depends on uniqueness and an approved incident/recovery decision requires it. This weakens idempotency protection.
- **Column rollback:** do not drop the new columns as a routine down migration. Dropping them would destroy approval/execution history written after rollout. If removal is ever required, first export and verify all affected values, obtain explicit approval, and prepare a separately reviewed recovery plan.
- **Data/schema mismatch:** restore from the verified backup/PITR only under the database owner's incident process. Never reset, truncate, or rebuild the chunk table.

## Assumptions that must be checked against live Supabase

- `workflow_runs` exists with the expected primary key and non-null `user_id`.
- The existing migration history and live schema are not necessarily the same as this repository.
- Any same-named proposed columns are absent or semantically/type compatible.
- There are no pre-existing duplicate non-null per-user idempotency keys that would block the unique index.
- The migration runner's transaction behavior and DDL lock behavior are understood.
- RLS, table privileges, RPC definition/grants, extensions and Storage policies match expectations.
- Current workflows/data volume and traffic allow the DDL/index operation.

None of these live assumptions were verified here. No credentials or `.env` files were inspected.
