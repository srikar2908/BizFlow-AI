"use client";

import { ErrorState } from "@/src/components/state-patterns";

export default function DashboardError({ reset }: { reset: () => void }) {
  return (
    <ErrorState
      title="Workspace unavailable"
      description="The dashboard shell could not render."
      actionLabel="Try again"
      onAction={reset}
    />
  );
}
