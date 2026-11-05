# BizFlow AI Demo Script

## Opening Pitch

"BizFlow AI is a full-stack document intelligence and workflow automation platform for SMEs. It takes private business documents, turns them into grounded AI outputs, and only triggers external automation after a human approves the payload."

"This demo shows the end-to-end path: upload a client brief, ingest it into a RAG pipeline, ask a grounded question, generate business artifacts, approve a workflow, execute it through n8n, and observe the trace in Langfuse."

## Problem Statement

"Small business teams often receive key client context in briefs, PDFs, notes, and proposals. The work that follows is repetitive: summarize the document, understand the client problem, draft a proposal, write a follow-up email, and log the workflow somewhere operational."

"A simple chatbot is not enough for that workflow. The system needs private document handling, user isolation, grounded answers, reviewable outputs, human approval, workflow execution, and observability."

## Demo Steps

### 1. Log In

Action: Open the app and log in.

What to say:
"The app uses Supabase Auth. The frontend attaches the Supabase access token to backend API calls, and the FastAPI backend verifies the token before allowing document, RAG, or workflow actions."

### 2. Upload `client_brief_abc_logistics.txt`

Action: Go to Documents and upload `client_brief_abc_logistics.txt`.

What to say:
"The upload is not a mock. The backend validates file type and size, computes a SHA-256 hash for duplicate detection, stores the original in a private Supabase Storage bucket, and inserts a `documents` row scoped to the current user."

### 3. Ingest Document

Action: Click Ingest.

What to say:
"Ingestion extracts text, chunks it, embeds chunks with Gemini embeddings, and stores them in Postgres using pgvector. Document status moves from pending to processing to completed or failed."

### 4. Ask a RAG Question

Action: Go to Chat and ask:

```text
What problem is this client trying to solve?
```

What to say:
"This uses retrieval before generation. The query is embedded, matched against only this user's document chunks, and Gemini 2.5 Flash generates an answer from retrieved context. The answer includes citations back to the source document and chunk indexes."

### 5. Extract Metadata

Action: Return to Documents and click Extract metadata.

What to say:
"Metadata extraction turns the document into structured JSON: document type, title, summary, entities, key points, missing information, recommended actions, workflow recommendation, and confidence. The model output is validated before it is saved."

### 6. Generate Summary

Action: Click Generate summary.

What to say:
"The summary step creates both concise and detailed summaries, key points, recommended actions, and a suggested workflow. These are merged into document metadata without destroying existing fields."

### 7. Generate Proposal

Action: Click Generate proposal.

What to say:
"The proposal draft is generated from the ingested document context, summary, and metadata. It stays structured: executive summary, client problem, proposed solution, scope, deliverables, assumptions, missing information, and next steps."

### 8. Generate Email Draft

Action: Click Generate email draft.

What to say:
"The email draft is also reviewable structured JSON. The system does not invent client emails or send anything. It creates a subject, body, purpose, recipient context, missing information questions, and call to action."

### 9. Preview Workflow

Action: Click Preview workflow.

What to say:
"This is the safety layer. The backend builds a workflow preview from existing document outputs and creates a `workflow_runs` row with status pending. No external action happens yet."

### 10. Approve Workflow

Action: Go to Workflows and click Approve.

What to say:
"External workflow execution requires explicit human approval. Approval updates the workflow run to status approved and sets `approved_by_user` to true."

### 11. Execute Workflow

Action: Click Execute.

What to say:
"Only approved workflows can execute. The backend moves the run to running, sends the approved payload to n8n with a server-side webhook secret, and then marks the workflow completed or failed based on the n8n response."

### 12. Show Google Sheet Row

Action: Open the connected Google Sheet.

What to say:
"n8n receives the payload and logs the workflow execution to Google Sheets. This is intentionally a safe first automation: it records the action rather than sending an email or changing a CRM."

### 13. Show Langfuse Trace

Action: Open Langfuse and show the relevant trace.

What to say:
"The important AI and workflow operations are traced: RAG answer generation, metadata extraction, summary generation, proposal generation, email draft generation, and workflow execution. The traces include safe metadata like operation name, document ID, model name, latency, and success or failure. They do not include API keys, webhook secrets, full private documents, or embeddings."

## Technical Highlights

- FastAPI backend with typed request and response schemas.
- Next.js dashboard with authenticated API calls.
- Supabase Auth as the source of user identity.
- Supabase Storage for private original documents.
- Postgres tables with `user_id`, RLS policies, and grants for user isolation.
- pgvector-backed `document_chunks` table with 3072-dimensional Gemini embeddings.
- Gemini `gemini-embedding-001` for retrieval embeddings.
- Gemini 2.5 Flash for grounded answer and document generation tasks.
- TXT, MD, DOCX, and PDF ingestion support.
- Structured JSON outputs for metadata, summaries, proposals, and email drafts.
- n8n webhook execution after human approval.
- Google Sheets workflow logging.
- Langfuse observability for GenAI and workflow operations.

## Production Engineering Highlights

- Backend routes require Supabase access tokens.
- Users can only access their own documents, chunks, and workflow runs.
- Duplicate uploads are detected with SHA-256 file hashes.
- Uploaded documents are treated as untrusted data in prompts.
- Model output is validated before being saved or used downstream.
- External workflows cannot execute without persisted human approval.
- Secrets stay server-side and are not exposed to the frontend.
- Langfuse is best-effort: observability failures do not break user workflows.
- Tests cover auth, document upload, ingestion, RAG, generation, workflow approval, n8n execution, and observability no-op behavior.

## Closing Statement

"The main point of BizFlow AI is not just that it can answer questions over documents. It shows the production shape around an AI feature: private data handling, retrieval, validation, approval gates, workflow automation, and observability."

"That is the difference between a GenAI demo and a system that can become a real business workflow product."
