import { EmptyState } from "@/src/components/state-patterns";

export default function SettingsPage() {
  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Settings</h1>
        <p className="mt-2 text-sm text-slate-600">Account and workspace settings foundation.</p>
      </div>
      <EmptyState
        title="No settings available"
        description="Settings will be added when authentication and workspace configuration are implemented."
      />
    </section>
  );
}
