"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ErrorState, LoadingState } from "@/src/components/state-patterns";
import { apiClient } from "@/src/lib/api-client";

type Overview = {
  total_documents: number;
  processed_documents: number;
  proposals_generated: number;
  workflows_completed: number;
  pending_approvals: number;
  failed_or_unknown_executions: number;
  document_status_counts: Record<string, number>;
  documents: { id: string; filename: string; status: string; created_at: string }[];
  workflows: { id: string; document_filename?: string | null; workflow_type: string; status: string; created_at: string }[];
  activity: { id: string; event_type: string; filename?: string | null; occurred_at: string }[];
  activity_available: boolean;
};

const statNames: [keyof Overview, string][] = [
  ["total_documents", "Total documents"],
  ["processed_documents", "Processed"],
  ["proposals_generated", "Proposals"],
  ["workflows_completed", "Workflows completed"],
  ["pending_approvals", "Pending approvals"],
  ["failed_or_unknown_executions", "Failed or unknown"],
];

function date(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function DashboardPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try { setData(await apiClient.request<Overview>("/dashboard")); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to load workspace overview."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => {
    let live = true;
    apiClient.request<Overview>("/dashboard").then(value => {
      if (live) setData(value);
    }).catch(e => {
      if (live) setError(e instanceof Error ? e.message : "Unable to load workspace overview.");
    }).finally(() => {
      if (live) setLoading(false);
    });
    return () => { live = false; };
  }, []);

  return <section className="space-y-8">
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div><p className="text-sm font-semibold uppercase tracking-wider text-emerald-700">Workspace overview</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Dashboard</h1><p className="mt-2 text-sm text-slate-600">A live view of your documents and approved workflows.</p></div>
      <div className="flex gap-2"><Link className="rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800" href="/dashboard/documents">Upload document</Link><Link className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-white" href="/dashboard/chat">Ask a question</Link></div>
    </header>
    {loading && <LoadingState label="Loading your workspace…" />}
    {error && <ErrorState title="Dashboard unavailable" description={error} actionLabel="Try again" onAction={() => void load()} />}
    {data && <>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">{statNames.map(([key, label]) => <article key={key} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-sm text-slate-500">{label}</p><p className="mt-3 text-3xl font-semibold tabular-nums text-slate-950">{data[key] as number}</p></article>)}</div>
      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-5"><div className="flex items-center justify-between"><h2 className="text-lg font-semibold text-slate-950">Recent documents</h2><Link className="text-sm font-medium text-emerald-800 hover:underline" href="/dashboard/documents">View all</Link></div>
          {data.documents.length ? <ul className="mt-4 divide-y divide-slate-100">{data.documents.map(doc => <li className="flex items-center justify-between gap-3 py-3" key={doc.id}><div className="min-w-0"><p className="truncate text-sm font-medium text-slate-900">{doc.filename}</p><p className="mt-1 text-xs text-slate-500">{date(doc.created_at)}</p></div><span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700">{doc.status}</span></li>)}</ul> : <p className="py-10 text-center text-sm text-slate-500">No documents yet. Upload one to get started.</p>}
        </section>
        <section className="rounded-xl border border-slate-200 bg-white p-5"><div className="flex items-center justify-between"><h2 className="text-lg font-semibold text-slate-950">Recent workflows</h2><Link className="text-sm font-medium text-emerald-800 hover:underline" href="/dashboard/workflows">Review workflows</Link></div>
          {data.workflows.length ? <ul className="mt-4 divide-y divide-slate-100">{data.workflows.map(item => <li className="flex items-center justify-between gap-3 py-3" key={item.id}><div className="min-w-0"><p className="truncate text-sm font-medium capitalize text-slate-900">{item.workflow_type.replaceAll("_", " ")}</p><p className="mt-1 truncate text-xs text-slate-500">{item.document_filename ?? "Document unavailable"} · {date(item.created_at)}</p></div><span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-1 text-xs capitalize text-slate-700">{item.status}</span></li>)}</ul> : <p className="py-10 text-center text-sm text-slate-500">Workflow previews and their approval status will appear here.</p>}
        </section>
      </div>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="text-lg font-semibold text-slate-950">Document processing status</h2><div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">{Object.entries(data.document_status_counts).map(([status, count]) => <div className="rounded-lg bg-slate-50 p-4" key={status}><p className="text-sm capitalize text-slate-500">{status}</p><p className="mt-2 text-2xl font-semibold tabular-nums text-slate-950">{count}</p></div>)}</div></section>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="text-lg font-semibold text-slate-950">Recent activity</h2><p className="mt-1 text-sm text-slate-500">{data.activity_available ? "Recorded document and workflow actions." : "Activity history is unavailable until the optional activity ledger migration is installed."}</p>
        {data.activity.length ? <ol className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{data.activity.map(event => <li className="rounded-lg bg-slate-50 p-4" key={event.id}><p className="text-sm font-medium capitalize text-slate-900">{event.event_type.replaceAll("_", " ")}</p><p className="mt-1 truncate text-sm text-slate-600">{event.filename ?? "Workflow document"}</p><time className="mt-2 block text-xs text-slate-500">{date(event.occurred_at)}</time></li>)}</ol> : <p className="py-6 text-sm text-slate-500">{data.activity_available ? "No recorded activity yet." : "Other dashboard information is available above."}</p>}
      </section>
    </>}
  </section>;
}
