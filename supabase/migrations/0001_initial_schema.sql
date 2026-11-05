-- 0001_initial_schema.sql
-- BizFlow AI initial database schema.
-- Safe to rerun during early development.

-- ------------------------------------------------------------
-- Extensions
-- ------------------------------------------------------------

create extension if not exists pgcrypto with schema extensions;
create extension if not exists vector with schema extensions;

-- ------------------------------------------------------------
-- Tables
-- ------------------------------------------------------------

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  filename text not null,
  file_hash text not null,
  mime_type text,
  size_bytes bigint,
  storage_path text,
  status text not null default 'pending',
  summary text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, file_hash)
);

-- Early development reset: Gemini embeddings are 3072-dimensional.
drop table if exists public.document_chunks cascade;

create table public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  user_id uuid not null,
  chunk_index int not null,
  content text not null,
  token_count int,
  metadata jsonb not null default '{}',
  embedding extensions.vector(3072),
  created_at timestamptz not null default now()
);

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  title text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null,
  role text not null,
  content text not null,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists public.workflow_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  document_id uuid references public.documents(id) on delete set null,
  workflow_type text not null,
  status text not null default 'pending',
  input_payload jsonb not null default '{}',
  output_payload jsonb not null default '{}',
  approved_by_user boolean not null default false,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.model_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  task_type text,
  provider text,
  model text,
  prompt_tokens int,
  completion_tokens int,
  cost numeric,
  latency_ms int,
  status text,
  created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- Row Level Security
-- ------------------------------------------------------------

alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.workflow_runs enable row level security;
alter table public.model_events enable row level security;

-- ------------------------------------------------------------
-- Documents policies
-- ------------------------------------------------------------

drop policy if exists "documents_select_own" on public.documents;
drop policy if exists "documents_insert_own" on public.documents;
drop policy if exists "documents_update_own" on public.documents;
drop policy if exists "documents_delete_own" on public.documents;

create policy "documents_select_own"
on public.documents
for select
to authenticated
using (auth.uid() = user_id);

create policy "documents_insert_own"
on public.documents
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "documents_update_own"
on public.documents
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "documents_delete_own"
on public.documents
for delete
to authenticated
using (auth.uid() = user_id);

-- ------------------------------------------------------------
-- Document chunks policies
-- ------------------------------------------------------------

drop policy if exists "chunks_select_own" on public.document_chunks;
drop policy if exists "chunks_insert_own" on public.document_chunks;
drop policy if exists "chunks_update_own" on public.document_chunks;
drop policy if exists "chunks_delete_own" on public.document_chunks;

create policy "chunks_select_own"
on public.document_chunks
for select
to authenticated
using (auth.uid() = user_id);

create policy "chunks_insert_own"
on public.document_chunks
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "chunks_update_own"
on public.document_chunks
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "chunks_delete_own"
on public.document_chunks
for delete
to authenticated
using (auth.uid() = user_id);

-- ------------------------------------------------------------
-- Conversations policies
-- ------------------------------------------------------------

drop policy if exists "conversations_select_own" on public.conversations;
drop policy if exists "conversations_insert_own" on public.conversations;
drop policy if exists "conversations_update_own" on public.conversations;
drop policy if exists "conversations_delete_own" on public.conversations;

create policy "conversations_select_own"
on public.conversations
for select
to authenticated
using (auth.uid() = user_id);

create policy "conversations_insert_own"
on public.conversations
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "conversations_update_own"
on public.conversations
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "conversations_delete_own"
on public.conversations
for delete
to authenticated
using (auth.uid() = user_id);

-- ------------------------------------------------------------
-- Messages policies
-- ------------------------------------------------------------

drop policy if exists "messages_select_own" on public.messages;
drop policy if exists "messages_insert_own" on public.messages;
drop policy if exists "messages_update_own" on public.messages;
drop policy if exists "messages_delete_own" on public.messages;

create policy "messages_select_own"
on public.messages
for select
to authenticated
using (auth.uid() = user_id);

create policy "messages_insert_own"
on public.messages
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "messages_update_own"
on public.messages
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "messages_delete_own"
on public.messages
for delete
to authenticated
using (auth.uid() = user_id);

-- ------------------------------------------------------------
-- Workflow runs policies
-- ------------------------------------------------------------

drop policy if exists "workflow_runs_select_own" on public.workflow_runs;
drop policy if exists "workflow_runs_insert_own" on public.workflow_runs;
drop policy if exists "workflow_runs_update_own" on public.workflow_runs;
drop policy if exists "workflow_runs_delete_own" on public.workflow_runs;

create policy "workflow_runs_select_own"
on public.workflow_runs
for select
to authenticated
using (auth.uid() = user_id);

create policy "workflow_runs_insert_own"
on public.workflow_runs
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "workflow_runs_update_own"
on public.workflow_runs
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "workflow_runs_delete_own"
on public.workflow_runs
for delete
to authenticated
using (auth.uid() = user_id);

-- ------------------------------------------------------------
-- Model events policies
-- ------------------------------------------------------------

drop policy if exists "model_events_select_own" on public.model_events;
drop policy if exists "model_events_insert_own" on public.model_events;
drop policy if exists "model_events_update_own" on public.model_events;
drop policy if exists "model_events_delete_own" on public.model_events;

create policy "model_events_select_own"
on public.model_events
for select
to authenticated
using (auth.uid() = user_id);

create policy "model_events_insert_own"
on public.model_events
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "model_events_update_own"
on public.model_events
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "model_events_delete_own"
on public.model_events
for delete
to authenticated
using (auth.uid() = user_id);

-- ------------------------------------------------------------
-- Grants
-- ------------------------------------------------------------
-- Grants allow the authenticated role to access the tables.
-- RLS then restricts access to only the user's own rows.

grant usage on schema public to authenticated;

grant select, insert, update, delete on public.documents to authenticated;
grant select, insert, update, delete on public.document_chunks to authenticated;
grant select, insert, update, delete on public.conversations to authenticated;
grant select, insert, update, delete on public.messages to authenticated;
grant select, insert, update, delete on public.workflow_runs to authenticated;
grant select, insert, update, delete on public.model_events to authenticated;

-- ------------------------------------------------------------
-- Indexes
-- ------------------------------------------------------------

create index if not exists idx_documents_user_id
on public.documents(user_id);

create index if not exists idx_documents_file_hash
on public.documents(user_id, file_hash);

create index if not exists idx_document_chunks_user_id
on public.document_chunks(user_id);

create index if not exists idx_document_chunks_document_id
on public.document_chunks(document_id);

create index if not exists idx_conversations_user_id
on public.conversations(user_id);

create index if not exists idx_messages_user_id
on public.messages(user_id);

create index if not exists idx_messages_conversation_id
on public.messages(conversation_id);

create index if not exists idx_workflow_runs_user_id
on public.workflow_runs(user_id);

create index if not exists idx_model_events_user_id
on public.model_events(user_id);

-- Vector index for future RAG search.
-- This is useful later when document_chunks has embeddings.
-- Keep lists modest for early development.

-- Vector index disabled because 3072 dimensions
-- exceed the 2000-dimension IVFFlat limit.
-- Exact vector search will be used for now.


-- ------------------------------------------------------------
-- RAG search RPC
-- ------------------------------------------------------------

create or replace function public.match_document_chunks(
  query_embedding extensions.vector(3072),
  match_count int default 5,
  match_user_id uuid default auth.uid()
)
returns table (
  chunk_id uuid,
  document_id uuid,
  filename text,
  chunk_index int,
  content text,
  similarity double precision
)
language sql
stable
set search_path = public, extensions
as $$
  select
    dc.id as chunk_id,
    dc.document_id,
    d.filename,
    dc.chunk_index,
    dc.content,
    1 - (dc.embedding <=> query_embedding) as similarity
  from public.document_chunks dc
  join public.documents d on d.id = dc.document_id
  where dc.user_id = match_user_id
    and d.user_id = match_user_id
    and auth.uid() = match_user_id
    and dc.embedding is not null
  order by dc.embedding <=> query_embedding
  limit least(match_count, 20);
$$;

grant execute on function public.match_document_chunks(extensions.vector, int, uuid)
to authenticated;

-- ------------------------------------------------------------
-- Reload PostgREST schema cache
-- ------------------------------------------------------------

notify pgrst, 'reload schema';
