# Product Specification

## Summary

BizFlow AI helps SMEs turn business documents into useful actions. Users upload documents, the system ingests them into a retrieval index, and users can ask questions, extract metadata, generate proposals, and trigger approved automations.

The product must feel production-grade from the start: real auth, real persisted data, real retrieval, real model calls through a routing layer, and real workflow calls gated by human approval.

## Target Users

- SME owners and operators
- Sales and operations teams preparing client proposals
- Admin staff extracting structured information from contracts, briefs, RFPs, invoices, and internal documents

## MVP Capabilities

### Auth

Users authenticate through Supabase Auth. The application must associate all user-owned resources with the authenticated Supabase user.

### Document Upload

Users upload documents to Supabase Storage. Uploaded files are untrusted input and must be validated, size-limited, scanned by type, and never executed.

### RAG Ingestion

The backend extracts text, chunks content, creates embeddings, and stores chunks with source metadata in Postgres using pgvector.

### RAG Chat With Citations

Users ask questions against their uploaded documents. Answers must include citations pointing to source document chunks. If the retrieved context is insufficient, the assistant should say so instead of inventing unsupported claims.

### Metadata Extraction

Users can request structured metadata extraction from documents. The extraction result must preserve provenance and should be reviewable before being used in downstream workflows.

### Proposal Generation

Users can generate draft proposals using retrieved document context and user-provided requirements. Generated proposals are drafts and must preserve citations or source references where claims depend on uploaded documents.

### Human-Approved n8n Trigger

The system can prepare an external workflow request, but the user must explicitly approve it before `n8n_service.py` sends any webhook call.

## Out Of Scope For MVP

- Multi-tenant organization roles beyond single-user ownership
- Payment and subscription management
- Browser extension
- Real-time collaborative editing
- Autonomous workflow execution without approval
- Custom fine-tuning

## Success Criteria

- A user can sign in, upload a document, ingest it, and chat with grounded citations.
- A user can extract metadata and see the source document relationship.
- A user can generate a proposal draft from document context.
- A user can approve a prepared automation and trigger an n8n webhook.
- User data is isolated by RLS.
- Model and automation integrations are centralized behind their service modules.

## Product Constraints

- No fake endpoints: frontend actions must call real backend routes once implemented.
- No mock-only frontend: UI may have loading and empty states, but core flows must connect to real data.
- Uploaded content cannot be treated as trusted instructions.
- Model output cannot approve workflows or override security rules.
