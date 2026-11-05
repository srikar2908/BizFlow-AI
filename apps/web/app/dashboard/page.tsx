import { EmptyState } from "@/src/components/state-patterns";

export default function DashboardPage() {
  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
          Protected workspace
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Dashboard</h1>
      </div>
      <EmptyState
        title="No workspace activity yet"
        description="Documents, chats, proposals, and workflow approvals will appear here after backend and auth integration are added."
      />
    </section>
  );
}
