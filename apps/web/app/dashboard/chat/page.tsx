"use client";

import { FormEvent, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/src/components/state-patterns";
import { apiClient } from "@/src/lib/api-client";

type RagSearchResult = {
  chunk_id: string;
  document_id: string;
  filename: string;
  chunk_index: number;
  content: string;
  similarity: number;
};

type RagSearchResponse = {
  results: RagSearchResult[];
};

type RagCitation = {
  document_id: string;
  filename: string;
  chunk_index: number;
  preview: string;
};

type RagAnswerResponse = {
  answer: string;
  citations: RagCitation[];
};

function formatSimilarity(value: number) {
  return `${Math.round(value * 100)}%`;
}

function previewContent(content: string) {
  return content.length > 360 ? `${content.slice(0, 360)}...` : content;
}

export default function ChatPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RagSearchResult[]>([]);
  const [answer, setAnswer] = useState<string | null>(null);
  const [citations, setCitations] = useState<RagCitation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<"answer" | "search" | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await generateAnswer();
  }

  async function searchChunks() {
    const cleanQuery = query.trim();
    if (!cleanQuery) {
      setErrorMessage("Enter a question before searching.");
      return;
    }

    setIsLoading(true);
    setActiveAction("search");
    setHasSubmitted(true);
    setErrorMessage(null);

    try {
      const response = await apiClient.request<RagSearchResponse>("/rag/search", {
        method: "POST",
        body: JSON.stringify({ query: cleanQuery, match_count: 5 }),
      });
      setResults(response.results);
    } catch (error) {
      setResults([]);
      setErrorMessage(error instanceof Error ? error.message : "Unable to search documents.");
    } finally {
      setIsLoading(false);
      setActiveAction(null);
    }
  }

  async function generateAnswer() {
    const cleanQuery = query.trim();
    if (!cleanQuery) {
      setErrorMessage("Enter a question before generating an answer.");
      return;
    }

    setIsLoading(true);
    setActiveAction("answer");
    setHasSubmitted(true);
    setErrorMessage(null);
    setAnswer(null);
    setCitations([]);

    try {
      const response = await apiClient.request<RagAnswerResponse>("/rag/answer", {
        method: "POST",
        body: JSON.stringify({ query: cleanQuery, match_count: 5 }),
      });
      setAnswer(response.answer);
      setCitations(response.citations);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to generate an answer.");
    } finally {
      setIsLoading(false);
      setActiveAction(null);
    }
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Chat</h1>
        <p className="mt-2 text-sm text-slate-600">
          Ask questions grounded in your ingested documents.
        </p>
      </div>

      <form className="border border-slate-200 bg-white p-5 shadow-sm" onSubmit={handleSubmit}>
        <label className="text-sm font-medium text-slate-700" htmlFor="rag-query">
          Question
        </label>
        <div className="mt-2 flex flex-col gap-3 md:flex-row">
          <input
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500"
            id="rag-query"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search your ingested documents"
            type="search"
            value={query}
          />
          <button
            className="rounded-md border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isLoading}
            onClick={searchChunks}
            type="button"
          >
            {activeAction === "search" ? "Searching" : "Search chunks"}
          </button>
          <button
            className="rounded-md bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isLoading}
            type="submit"
          >
            {activeAction === "answer" ? "Generating" : "Generate answer"}
          </button>
        </div>
      </form>

      {errorMessage ? (
        <ErrorState
          actionLabel="Try again"
          description={errorMessage}
          onAction={() => setErrorMessage(null)}
          title="Chat unavailable"
        />
      ) : null}

      {isLoading ? (
        <LoadingState label={activeAction === "answer" ? "Generating answer" : "Searching chunks"} />
      ) : null}

      {!isLoading && !errorMessage && !hasSubmitted ? (
        <EmptyState
          title="No question yet"
          description="Ask a question to search or generate an answer from ingested documents."
        />
      ) : null}

      {!isLoading && !errorMessage && answer ? (
        <article className="border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-950">Answer</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">{answer}</p>
        </article>
      ) : null}

      {!isLoading && !errorMessage && answer && citations.length > 0 ? (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-950">Sources</h2>
          {citations.map((citation) => (
            <article
              className="border border-slate-200 bg-white p-4 shadow-sm"
              key={`${citation.document_id}-${citation.chunk_index}`}
            >
              <h3 className="font-semibold text-slate-950">{citation.filename}</h3>
              <p className="mt-1 text-xs text-slate-500">Chunk {citation.chunk_index}</p>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                {citation.preview}
              </p>
            </article>
          ))}
        </div>
      ) : null}

      {!isLoading && !errorMessage && hasSubmitted && !answer && results.length === 0 ? (
        <EmptyState
          title="No matches"
          description="No ingested chunks matched that question yet."
        />
      ) : null}

      {!isLoading && !errorMessage && results.length > 0 ? (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-950">Matching chunks</h2>
          {results.map((result) => (
            <article className="border border-slate-200 bg-white p-4 shadow-sm" key={result.chunk_id}>
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="font-semibold text-slate-950">{result.filename}</h2>
                  <p className="mt-1 text-xs text-slate-500">Chunk {result.chunk_index}</p>
                </div>
                <span className="w-fit rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200 ring-inset">
                  {formatSimilarity(result.similarity)}
                </span>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                {previewContent(result.content)}
              </p>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
