-- Additive dashboard activity ledger. No historical rows can be reconstructed
-- reliably, so this records events only after deployment of the application code.
create table if not exists public.activity_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  document_id uuid references public.documents(id) on delete set null,
  event_type text not null check (event_type in (
    'document_uploaded', 'document_ingested', 'metadata_extracted',
    'summary_generated', 'proposal_generated', 'email_draft_generated',
    'workflow_approved', 'workflow_execution_started', 'workflow_completed',
    'workflow_failed', 'workflow_unknown'
  )),
  details jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null default now()
);

create index if not exists idx_activity_events_user_occurred
  on public.activity_events (user_id, occurred_at desc);

alter table public.activity_events enable row level security;
revoke all on public.activity_events from anon, authenticated;
grant select on public.activity_events to authenticated;
grant insert, select on public.activity_events to service_role;

create policy "Owners can read their activity events"
  on public.activity_events for select to authenticated
  using (auth.uid() = user_id);

comment on table public.activity_events is
  'Forward-only user activity events. Historical events are intentionally not backfilled.';
