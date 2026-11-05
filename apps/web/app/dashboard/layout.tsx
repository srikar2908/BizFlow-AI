import type { ReactNode } from "react";

import { AppSidebar } from "@/src/components/app-sidebar";
import { AuthGate } from "@/src/components/auth-gate";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col md:flex-row">
        <AppSidebar />
        <main className="flex-1 px-5 py-6 md:px-8">
          <AuthGate>{children}</AuthGate>
        </main>
      </div>
    </div>
  );
}
