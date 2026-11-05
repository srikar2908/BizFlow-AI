# Decisions

This file records architecture and product decisions. Add new entries as decisions are made.

## 0001. Documentation-First Start

Date: 2026-05-14

Decision:

Create repository documentation before writing application code.

Reasoning:

The platform has important integration, security, and data isolation requirements. Documenting contracts first reduces the chance of building fake endpoints, mock-only flows, or unsafe automation shortcuts.

## 0002. Supabase For Auth, Database, Storage, And RLS

Date: 2026-05-14

Decision:

Use Supabase for authentication, Postgres, Storage, pgvector, and Row Level Security.

Reasoning:

Supabase provides a coherent foundation for user identity, user-scoped data, document storage, vector retrieval, and database-level isolation.

## 0003. Centralized Model Routing

Date: 2026-05-14

Decision:

All model calls must go through `model_router.py`.

Reasoning:

Centralizing model calls makes provider routing, observability, error handling, retries, cost tracking, and safety controls consistent across RAG chat, extraction, embeddings, and proposal generation.

## 0004. Centralized n8n Integration

Date: 2026-05-14

Decision:

All n8n calls must go through `n8n_service.py`.

Reasoning:

Centralizing workflow calls protects webhook secrets, enforces approval checks, standardizes payload validation, and makes audit logging easier.

## 0005. Human Approval For External Workflows

Date: 2026-05-14

Decision:

External workflow triggers require explicit human approval.

Reasoning:

Uploaded documents and model outputs are untrusted. Human approval prevents prompt injection or generation errors from causing unintended external actions.
