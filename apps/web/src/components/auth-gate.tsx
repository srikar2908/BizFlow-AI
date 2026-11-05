"use client";

import type { Session } from "@supabase/supabase-js";
import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

import { LoadingState } from "@/src/components/state-patterns";
import { getSupabaseBrowserClient } from "@/src/lib/supabase";

type AuthGateProps = {
  children: ReactNode;
};

export function AuthGate({ children }: AuthGateProps) {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    let unsubscribe: (() => void) | undefined;

    Promise.resolve()
      .then(() => {
        const supabase = getSupabaseBrowserClient();

        const {
          data: { subscription },
        } = supabase.auth.onAuthStateChange((_event, nextSession) => {
          setSession(nextSession);
        });
        unsubscribe = () => subscription.unsubscribe();

        return supabase.auth.getSession();
      })
      .then(({ data, error }) => {
        if (!isMounted) {
          return;
        }

        if (error) {
          setErrorMessage(error.message);
        }

        setSession(data.session);
        setIsLoading(false);
      })
      .catch((error: unknown) => {
        if (!isMounted) {
          return;
        }

        setErrorMessage(error instanceof Error ? error.message : "Authentication is unavailable.");
        setIsLoading(false);
      });

    return () => {
      isMounted = false;
      unsubscribe?.();
    };
  }, []);

  if (isLoading) {
    return <LoadingState label="Checking session" />;
  }

  if (errorMessage) {
    return (
      <div className="border border-amber-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-950">Authentication setup required</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">{errorMessage}</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-950">Login required</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Sign in before opening the protected BizFlow workspace.
        </p>
        <Link
          className="mt-5 inline-flex rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
          href="/login"
        >
          Log in
        </Link>
      </div>
    );
  }

  return children;
}
