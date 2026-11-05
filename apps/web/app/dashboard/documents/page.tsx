"use client";

import { ChangeEvent, Fragment, FormEvent, useEffect, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/src/components/state-patterns";
import { apiClient } from "@/src/lib/api-client";

type DocumentStatus = "pending" | "ingesting" | "processing" | "ready" | "completed" | "failed";

type DocumentSummary = {
  id: string;
  filename: string;
  status: DocumentStatus;
  created_at: string;
  summary?: string | null;
  metadata?: DocumentMetadata | null;
};

type DocumentUploadResponse = DocumentSummary & {
  duplicate: boolean;
};

type DocumentIngestResponse = {
  id: string;
  status: DocumentStatus;
  chunks_created: number;
};

type DocumentMetadata = {
  document_type?: string;
  title?: string | null;
  summary?: string;
  entities?: string[];
  key_points?: string[];
  missing_information?: string[];
  recommended_actions?: string[];
  recommended_workflow?: string | null;
  suggested_workflow?: string | null;
  detailed_summary?: string;
  proposal_draft?: ProposalDraft;
  email_draft?: EmailDraft;
  confidence?: number;
};

type DocumentMetadataResponse = {
  id: string;
  filename: string;
  summary: string | null;
  metadata: DocumentMetadata;
};

type DocumentSummaryGeneration = {
  concise_summary: string;
  detailed_summary: string;
  key_points: string[];
  recommended_actions: string[];
  suggested_workflow: string | null;
};

type DocumentSummaryResponse = {
  id: string;
  filename: string;
  summary: string;
  metadata: DocumentMetadata;
  generated: DocumentSummaryGeneration;
};

type ProposalDraft = {
  proposal_title: string;
  executive_summary: string;
  client_problem: string | null;
  proposed_solution: string;
  scope_of_work: string[];
  deliverables: string[];
  timeline: string[];
  assumptions: string[];
  missing_information: string[];
  next_steps: string[];
};

type DocumentProposalResponse = {
  id: string;
  filename: string;
  proposal: ProposalDraft;
  metadata: DocumentMetadata;
};

type EmailDraft = {
  subject: string;
  body: string;
  purpose: string;
  recipient_context: string | null;
  missing_information_questions: string[];
  call_to_action: string | null;
};

type DocumentEmailDraftResponse = {
  id: string;
  filename: string;
  email_draft: EmailDraft;
  metadata: DocumentMetadata;
};

type WorkflowPreviewResponse = {
  id: string;
  workflow_type: string;
  status: string;
};

const acceptedFileTypes = ".pdf,.docx,.txt,.md,.csv";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusClasses(status: DocumentStatus) {
  switch (status) {
    case "ready":
    case "completed":
      return "bg-emerald-50 text-emerald-700 ring-emerald-200";
    case "failed":
      return "bg-red-50 text-red-700 ring-red-200";
    case "ingesting":
    case "processing":
      return "bg-blue-50 text-blue-700 ring-blue-200";
    case "pending":
      return "bg-amber-50 text-amber-700 ring-amber-200";
  }
}

function canIngest(status: DocumentStatus) {
  return status === "pending" || status === "failed";
}

function canExtractMetadata(status: DocumentStatus) {
  return status === "completed" || status === "ready";
}

function formatConfidence(value: number) {
  return `${Math.round(value * 100)}%`;
}

function metadataList(values: string[] | undefined) {
  return Array.isArray(values) ? values : [];
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [ingestingDocumentId, setIngestingDocumentId] = useState<string | null>(null);
  const [extractingDocumentId, setExtractingDocumentId] = useState<string | null>(null);
  const [summarizingDocumentId, setSummarizingDocumentId] = useState<string | null>(null);
  const [proposalDocumentId, setProposalDocumentId] = useState<string | null>(null);
  const [emailDraftDocumentId, setEmailDraftDocumentId] = useState<string | null>(null);
  const [workflowPreviewDocumentId, setWorkflowPreviewDocumentId] = useState<string | null>(null);
  const [copiedEmailDraftId, setCopiedEmailDraftId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function loadDocuments() {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const nextDocuments = await apiClient.request<DocumentSummary[]>("/documents");
      setDocuments(nextDocuments);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to load documents.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    let isMounted = true;

    async function loadInitialDocuments() {
      try {
        const nextDocuments = await apiClient.request<DocumentSummary[]>("/documents");
        if (isMounted) {
          setDocuments(nextDocuments);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(error instanceof Error ? error.message : "Unable to load documents.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadInitialDocuments();

    return () => {
      isMounted = false;
    };
  }, []);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.target.files?.[0] ?? null);
    setSuccessMessage(null);
    setErrorMessage(null);
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedFile) {
      setErrorMessage("Select a document before uploading.");
      return;
    }

    const formData = new FormData();
    formData.set("file", selectedFile);
    setIsUploading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const uploaded = await apiClient.request<DocumentUploadResponse>("/documents/upload", {
        method: "POST",
        body: formData,
      });
      setSuccessMessage(
        uploaded.duplicate
          ? `${uploaded.filename} was already uploaded.`
          : `${uploaded.filename} uploaded.`,
      );
      setSelectedFile(null);
      await loadDocuments();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to upload document.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleIngest(document: DocumentSummary) {
    setIngestingDocumentId(document.id);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const result = await apiClient.request<DocumentIngestResponse>(
        `/documents/${document.id}/ingest`,
        {
          method: "POST",
        },
      );
      setSuccessMessage(`${document.filename} ingested into ${result.chunks_created} chunk(s).`);
      await loadDocuments();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to ingest document.");
    } finally {
      setIngestingDocumentId(null);
    }
  }

  async function handleExtractMetadata(document: DocumentSummary) {
    setExtractingDocumentId(document.id);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response = await apiClient.request<DocumentMetadataResponse>(
        `/documents/${document.id}/metadata`,
        {
          method: "POST",
        },
      );
      setSuccessMessage(`${response.filename} metadata extracted.`);
      setDocuments((currentDocuments) =>
        currentDocuments.map((currentDocument) =>
          currentDocument.id === response.id
            ? {
                ...currentDocument,
                summary: response.summary,
                metadata: response.metadata,
              }
            : currentDocument,
        ),
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to extract metadata.");
    } finally {
      setExtractingDocumentId(null);
    }
  }

  async function handleGenerateSummary(document: DocumentSummary) {
    setSummarizingDocumentId(document.id);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response = await apiClient.request<DocumentSummaryResponse>(
        `/documents/${document.id}/summary`,
        {
          method: "POST",
        },
      );
      setSuccessMessage(`${response.filename} summary generated.`);
      setDocuments((currentDocuments) =>
        currentDocuments.map((currentDocument) =>
          currentDocument.id === response.id
            ? {
                ...currentDocument,
                summary: response.summary,
                metadata: response.metadata,
              }
            : currentDocument,
        ),
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to generate summary.");
    } finally {
      setSummarizingDocumentId(null);
    }
  }

  async function handleGenerateProposal(document: DocumentSummary) {
    setProposalDocumentId(document.id);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response = await apiClient.request<DocumentProposalResponse>(
        `/documents/${document.id}/proposal`,
        {
          method: "POST",
        },
      );
      setSuccessMessage(`${response.filename} proposal generated.`);
      setDocuments((currentDocuments) =>
        currentDocuments.map((currentDocument) =>
          currentDocument.id === response.id
            ? {
                ...currentDocument,
                metadata: response.metadata,
              }
            : currentDocument,
        ),
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to generate proposal.");
    } finally {
      setProposalDocumentId(null);
    }
  }

  async function handleGenerateEmailDraft(document: DocumentSummary) {
    setEmailDraftDocumentId(document.id);
    setCopiedEmailDraftId(null);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response = await apiClient.request<DocumentEmailDraftResponse>(
        `/documents/${document.id}/email-draft`,
        {
          method: "POST",
        },
      );
      setSuccessMessage(`${response.filename} email draft generated.`);
      setDocuments((currentDocuments) =>
        currentDocuments.map((currentDocument) =>
          currentDocument.id === response.id
            ? {
                ...currentDocument,
                metadata: response.metadata,
              }
            : currentDocument,
        ),
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to generate email draft.");
    } finally {
      setEmailDraftDocumentId(null);
    }
  }

  async function handleCopyEmailDraft(documentId: string, emailDraft: EmailDraft) {
    if (!navigator.clipboard) {
      setErrorMessage("Clipboard is not available in this browser.");
      return;
    }

    await navigator.clipboard.writeText(`${emailDraft.subject}\n\n${emailDraft.body}`);
    setCopiedEmailDraftId(documentId);
  }

  async function handleCreateWorkflowPreview(document: DocumentSummary) {
    setWorkflowPreviewDocumentId(document.id);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response = await apiClient.request<WorkflowPreviewResponse>("/workflows/preview", {
        method: "POST",
        body: JSON.stringify({
          document_id: document.id,
          workflow_type: "proposal_follow_up",
        }),
      });
      setSuccessMessage(
        `${document.filename} workflow preview created with status ${response.status}.`,
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to preview workflow.");
    } finally {
      setWorkflowPreviewDocumentId(null);
    }
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Documents</h1>
        <p className="mt-2 text-sm text-slate-600">
          Upload source files for metadata, proposals, and future retrieval workflows.
        </p>
      </div>

      <form className="border border-slate-200 bg-white p-5 shadow-sm" onSubmit={handleUpload}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0 flex-1">
            <label className="text-sm font-medium text-slate-700" htmlFor="document-file">
              Document
            </label>
            <input
              accept={acceptedFileTypes}
              className="mt-2 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 file:mr-4 file:rounded-md file:border-0 file:bg-slate-950 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-white"
              id="document-file"
              onChange={handleFileChange}
              type="file"
            />
            <p className="mt-2 truncate text-sm text-slate-500">
              {selectedFile ? selectedFile.name : "PDF, DOCX, TXT, MD, or CSV"}
            </p>
          </div>

          <button
            className="rounded-md bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isUploading}
            type="submit"
          >
            {isUploading ? "Uploading" : "Upload"}
          </button>
        </div>
      </form>

      {successMessage ? (
        <div className="border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {successMessage}
        </div>
      ) : null}

      {errorMessage ? (
        <ErrorState
          actionLabel="Retry"
          description={errorMessage}
          onAction={loadDocuments}
          title="Documents unavailable"
        />
      ) : null}

      {isLoading ? <LoadingState label="Loading documents" /> : null}

      {!isLoading && !errorMessage && documents.length === 0 ? (
        <EmptyState
          title="No documents"
          description="Uploaded files will appear here after they are stored for your workspace."
        />
      ) : null}

      {!isLoading && !errorMessage && documents.length > 0 ? (
        <div className="overflow-hidden border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Filename</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Status</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Created</th>
                <th className="px-4 py-3 text-right font-semibold text-slate-700">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {documents.map((document) => {
                const isIngesting = ingestingDocumentId === document.id;
                const isExtracting = extractingDocumentId === document.id;
                const isSummarizing = summarizingDocumentId === document.id;
                const isGeneratingProposal = proposalDocumentId === document.id;
                const isGeneratingEmailDraft = emailDraftDocumentId === document.id;
                const isCreatingWorkflowPreview = workflowPreviewDocumentId === document.id;
                const hasMetadata = Boolean(document.metadata || document.summary);
                const metadata = document.metadata;
                const workflow = metadata?.recommended_workflow ?? metadata?.suggested_workflow;
                const proposal = metadata?.proposal_draft;
                const emailDraft = metadata?.email_draft;
                const canPreviewWorkflow = canExtractMetadata(document.status) && Boolean(
                  proposal || emailDraft,
                );

                return (
                  <Fragment key={document.id}>
                    <tr>
                      <td className="max-w-xs truncate px-4 py-3 font-medium text-slate-950">
                        {document.filename}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ring-1 ring-inset ${statusClasses(
                            document.status,
                          )}`}
                        >
                          {isIngesting ? "processing" : document.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {formatDate(document.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          {canIngest(document.status) ? (
                            <button
                              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-800 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                              disabled={isIngesting || ingestingDocumentId !== null}
                              onClick={() => void handleIngest(document)}
                              type="button"
                            >
                              {isIngesting ? "Ingesting" : "Ingest"}
                            </button>
                          ) : null}
                          {canExtractMetadata(document.status) ? (
                            <button
                              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-800 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                              disabled={isExtracting || extractingDocumentId !== null}
                              onClick={() => void handleExtractMetadata(document)}
                              type="button"
                            >
                              {isExtracting ? "Extracting" : "Extract metadata"}
                            </button>
                          ) : null}
                          {canExtractMetadata(document.status) ? (
                            <button
                              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-800 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                              disabled={isSummarizing || summarizingDocumentId !== null}
                              onClick={() => void handleGenerateSummary(document)}
                              type="button"
                            >
                              {isSummarizing ? "Generating" : "Generate summary"}
                            </button>
                          ) : null}
                          {canExtractMetadata(document.status) ? (
                            <button
                              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-800 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                              disabled={isGeneratingProposal || proposalDocumentId !== null}
                              onClick={() => void handleGenerateProposal(document)}
                              type="button"
                            >
                              {isGeneratingProposal ? "Generating" : "Generate proposal"}
                            </button>
                          ) : null}
                          {canExtractMetadata(document.status) ? (
                            <button
                              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-800 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                              disabled={isGeneratingEmailDraft || emailDraftDocumentId !== null}
                              onClick={() => void handleGenerateEmailDraft(document)}
                              type="button"
                            >
                              {isGeneratingEmailDraft ? "Generating" : "Generate email draft"}
                            </button>
                          ) : null}
                          {canPreviewWorkflow ? (
                            <button
                              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-800 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                              disabled={
                                isCreatingWorkflowPreview || workflowPreviewDocumentId !== null
                              }
                              onClick={() => void handleCreateWorkflowPreview(document)}
                              type="button"
                            >
                              {isCreatingWorkflowPreview ? "Creating" : "Preview workflow"}
                            </button>
                          ) : null}
                          {!canIngest(document.status) && !canExtractMetadata(document.status) ? (
                            <span className="text-sm text-slate-400">-</span>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                    {hasMetadata ? (
                      <tr>
                        <td className="bg-slate-50 px-4 py-4" colSpan={4}>
                          <div className="space-y-3 border border-slate-200 bg-white p-4">
                            {document.summary ? (
                              <div>
                                <h3 className="text-sm font-semibold text-slate-950">Summary</h3>
                                <p className="mt-1 text-sm leading-6 text-slate-700">
                                  {document.summary}
                                </p>
                              </div>
                            ) : null}
                            {metadata ? (
                              <div className="grid gap-3 md:grid-cols-2">
                                <MetadataField
                                  label="Type"
                                  value={metadata.document_type ?? "Unknown"}
                                />
                                {typeof metadata.confidence === "number" ? (
                                  <MetadataField
                                    label="Confidence"
                                    value={formatConfidence(metadata.confidence)}
                                  />
                                ) : null}
                                <MetadataList label="Entities" values={metadataList(metadata.entities)} />
                                <MetadataList
                                  label="Key points"
                                  values={metadataList(metadata.key_points)}
                                />
                                <MetadataList
                                  label="Missing information"
                                  values={metadataList(metadata.missing_information)}
                                />
                                <MetadataList
                                  label="Recommended actions"
                                  values={metadataList(metadata.recommended_actions)}
                                />
                                <MetadataField
                                  label="Workflow"
                                  value={workflow ?? "None"}
                                />
                                {metadata.detailed_summary ? (
                                  <MetadataField
                                    label="Detailed summary"
                                    value={metadata.detailed_summary}
                                  />
                                ) : null}
                              </div>
                            ) : null}
                            {proposal ? <ProposalDraftCard proposal={proposal} /> : null}
                            {emailDraft ? (
                              <EmailDraftCard
                                copied={copiedEmailDraftId === document.id}
                                emailDraft={emailDraft}
                                onCopy={() => void handleCopyEmailDraft(document.id, emailDraft)}
                              />
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

function ProposalDraftCard({ proposal }: { proposal: ProposalDraft }) {
  return (
    <div className="space-y-3 border-t border-slate-200 pt-3">
      <div>
        <h3 className="text-sm font-semibold text-slate-950">{proposal.proposal_title}</h3>
        <p className="mt-1 text-sm leading-6 text-slate-700">{proposal.executive_summary}</p>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <MetadataField label="Client problem" value={proposal.client_problem ?? "Unknown"} />
        <MetadataField label="Proposed solution" value={proposal.proposed_solution} />
        <MetadataList label="Scope of work" values={proposal.scope_of_work} />
        <MetadataList label="Deliverables" values={proposal.deliverables} />
        <MetadataList label="Timeline" values={proposal.timeline} />
        <MetadataList label="Assumptions" values={proposal.assumptions} />
        <MetadataList label="Missing information" values={proposal.missing_information} />
        <MetadataList label="Next steps" values={proposal.next_steps} />
      </div>
    </div>
  );
}

function EmailDraftCard({
  copied,
  emailDraft,
  onCopy,
}: {
  copied: boolean;
  emailDraft: EmailDraft;
  onCopy: () => void;
}) {
  return (
    <div className="space-y-3 border-t border-slate-200 pt-3">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">Email draft</h3>
          <p className="mt-1 text-sm font-medium text-slate-800">{emailDraft.subject}</p>
        </div>
        <button
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-800 transition hover:border-slate-500"
          onClick={onCopy}
          type="button"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{emailDraft.body}</p>
      <div className="grid gap-3 md:grid-cols-2">
        <MetadataField label="Purpose" value={emailDraft.purpose} />
        <MetadataField
          label="Recipient context"
          value={emailDraft.recipient_context ?? "Unknown"}
        />
        <MetadataField label="Call to action" value={emailDraft.call_to_action ?? "None"} />
        <MetadataList
          label="Missing information questions"
          values={emailDraft.missing_information_questions}
        />
      </div>
    </div>
  );
}

function MetadataField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase text-slate-500">{label}</h3>
      <p className="mt-1 text-sm text-slate-700">{value}</p>
    </div>
  );
}

function MetadataList({ label, values }: { label: string; values: string[] }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase text-slate-500">{label}</h3>
      <ul className="mt-1 space-y-1 text-sm text-slate-700">
        {values.length > 0 ? values.map((value) => <li key={value}>{value}</li>) : <li>None</li>}
      </ul>
    </div>
  );
}
