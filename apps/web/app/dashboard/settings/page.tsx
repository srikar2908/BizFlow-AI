"use client";

import { useEffect, useState } from "react";
import { ErrorState, LoadingState } from "@/src/components/state-patterns";
import { apiClient } from "@/src/lib/api-client";

type Settings = {
  user_id: string;
  email: string | null;
  upload_limit_bytes: number;
  supabase_configured: boolean;
  ai_provider_configured: boolean;
  n8n_configured: boolean;
  langfuse_configured: boolean;
};

function ConfigRow({ label, ready }: { label: string; ready: boolean }) {
  return <li className="flex items-center justify-between gap-4 border-t border-slate-100 py-3"><span className="text-sm text-slate-700">{label}</span><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${ready ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>{ready ? "Configured" : "Not configured"}</span></li>;
}

export default function SettingsPage() {
  const [data, setData] = useState<Settings | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { let live = true; apiClient.request<Settings>("/settings").then(value => { if (live) setData(value); }).catch(e => { if (live) setError(e instanceof Error ? e.message : "Unable to load settings."); }); return () => { live = false; }; }, []);
  return <section className="mx-auto max-w-3xl space-y-6">
    <header><p className="text-sm font-semibold uppercase tracking-wider text-emerald-700">Workspace</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Settings</h1><p className="mt-2 text-sm text-slate-600">Account details and backend service configuration.</p></header>
    {error && <ErrorState title="Settings unavailable" description={error} actionLabel="Reload page" onAction={() => window.location.reload()} />}
    {!data && !error && <LoadingState label="Loading account settings…" />}
    {data && <>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold text-slate-950">Account</h2><dl className="mt-4 grid gap-4 sm:grid-cols-2"><div><dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Email</dt><dd className="mt-1 break-all text-sm text-slate-900">{data.email ?? "Not provided by your account"}</dd></div><div><dt className="text-xs font-medium uppercase tracking-wide text-slate-500">User ID</dt><dd className="mt-1 break-all font-mono text-xs text-slate-700">{data.user_id}</dd></div><div><dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Maximum upload size</dt><dd className="mt-1 text-sm text-slate-900">{(data.upload_limit_bytes / 1024 / 1024).toFixed(0)} MB</dd></div></dl></section>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold text-slate-950">Service configuration</h2><p className="mt-1 text-sm text-slate-500">This reports whether required backend settings are present. It does not test external service availability.</p><ul className="mt-4"><ConfigRow label="Supabase" ready={data.supabase_configured} /><ConfigRow label="AI provider" ready={data.ai_provider_configured} /><ConfigRow label="n8n workflow webhook" ready={data.n8n_configured} /><ConfigRow label="Langfuse observability" ready={data.langfuse_configured} /></ul></section>
    </>}
  </section>;
}
