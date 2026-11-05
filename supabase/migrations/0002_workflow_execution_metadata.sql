-- Additive workflow execution metadata.
--
-- Preflight requirements are documented in docs/MIGRATION_SAFETY.md.
-- Do not run the initial migration again to obtain these fields.
-- All new columns are nullable so existing workflow_runs rows are preserved
-- without requiring an unsafe or speculative backfill.

alter table public.workflow_runs
  add column if not exists approved_at timestamptz,
  add column if not exists execution_started_at timestamptz,
  add column if not exists completed_at timestamptz,
  add column if not exists n8n_execution_id text,
  add column if not exists idempotency_key text,
  add column if not exists execution_result jsonb;

-- Enforce idempotency-key uniqueness per owner while leaving all existing rows
-- (whose new idempotency_key is NULL) untouched.
create unique index if not exists idx_workflow_runs_user_idempotency_key
  on public.workflow_runs (user_id, idempotency_key)
  where idempotency_key is not null;

comment on column public.workflow_runs.approved_at is
  'Timestamp when an owner explicitly approved this workflow.';
comment on column public.workflow_runs.execution_started_at is
  'Timestamp when an approved workflow execution was claimed.';
comment on column public.workflow_runs.completed_at is
  'Timestamp when workflow execution reached a terminal state.';
comment on column public.workflow_runs.n8n_execution_id is
  'Execution identifier returned by n8n, when available.';
comment on column public.workflow_runs.idempotency_key is
  'Stable per-owner key used to prevent duplicate external workflow side effects.';
comment on column public.workflow_runs.execution_result is
  'Validated, normalized execution result; application code must validate its structure.';
