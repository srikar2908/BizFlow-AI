# RAG Design

## Goals

- Provide grounded answers over user-uploaded business documents.
- Return citations for claims based on retrieved documents.
- Avoid using uploaded text as trusted instructions.
- Support metadata extraction and proposal generation from retrieved context.

## Ingestion Pipeline

Planned flow:

1. User uploads a document.
2. Backend records document metadata.
3. Backend extracts text using a safe parser.
4. Text is split into chunks with source metadata.
5. Embeddings are generated through `model_router.py`.
6. Chunks and embeddings are stored in Postgres with pgvector.
7. Document status is updated.

## Chunking

Chunking should preserve:

- Document ID
- Chunk index
- Page number when available
- Section heading when available
- Character offsets when available
- Parser metadata

Initial chunking can use token-aware fixed windows with overlap. Later improvements may add semantic section splitting.

## Retrieval

Initial retrieval should:

- Scope queries by `user_id`.
- Use vector similarity over `document_chunks.embedding`.
- Optionally filter by selected documents.
- Return enough metadata to render citations.
- Avoid returning chunks from other users by relying on both backend filters and RLS.

## Generation

All generation calls must go through `model_router.py`.

Generation prompts must:

- Treat retrieved context as untrusted data.
- Require citations for document-grounded claims.
- Refuse to answer when context is insufficient.
- Avoid following instructions found inside uploaded documents.

## Citations

Each cited answer should include citation objects with:

- `document_id`
- `chunk_id`
- `filename`
- `page` when available
- `excerpt`

The UI should make it clear which answer statements are supported by which source documents.

## Metadata Extraction

Metadata extraction should produce structured JSON plus citations. The extraction schema should be explicit for each extraction type. Missing fields should be represented as null or omitted according to the schema, not invented.

## Proposal Generation

Proposal generation should combine:

- User-provided proposal requirements
- Retrieved document context
- Optional extracted metadata

The generated proposal is a draft. It should not trigger external workflows by itself.

## Evaluation Plan

Future evaluation should cover:

- Retrieval relevance
- Citation accuracy
- Refusal when context is insufficient
- Prompt injection resistance
- Cross-user data isolation
- Proposal factuality against source documents
