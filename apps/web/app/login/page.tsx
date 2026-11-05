"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, MouseEvent, useState } from "react";

import { getSupabaseBrowserClient } from "@/src/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [mode, setMode] = useState<"sign-in" | "sign-up">("sign-in");

  async function handleSubmit(
    event: FormEvent<HTMLFormElement> | MouseEvent<HTMLButtonElement>,
    nextMode: "sign-in" | "sign-up",
  ) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);
    setMode(nextMode);

    try {
      const supabase = getSupabaseBrowserClient();
      const { error } =
        nextMode === "sign-in"
          ? await supabase.auth.signInWithPassword({
              email,
              password,
            })
          : await supabase.auth.signUp({
              email,
              password,
            });

      if (error) {
        setErrorMessage(error.message);
        return;
      }

      if (nextMode === "sign-up") {
        setErrorMessage("Account created. Check your email if confirmation is required.");
        return;
      }

      router.push("/dashboard");
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to authenticate.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
      <section className="w-full max-w-md border border-slate-200 bg-white p-8 shadow-sm">
        <Link className="text-sm font-semibold text-slate-600 hover:text-slate-950" href="/">
          BizFlow AI
        </Link>
        <h1 className="mt-8 text-2xl font-semibold tracking-tight text-slate-950">Log in</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Sign in with your Supabase email and password.
        </p>

        <form
          className="mt-8 space-y-5"
          onSubmit={(event) => handleSubmit(event, "sign-in")}
        >
          <div>
            <label className="text-sm font-medium text-slate-700" htmlFor="email">
              Email
            </label>
            <input
              autoComplete="email"
              className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500"
              id="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700" htmlFor="password">
              Password
            </label>
            <input
              autoComplete="current-password"
              className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500"
              id="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </div>

          {errorMessage ? (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {errorMessage}
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2">
            <button
              className="rounded-md bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting && mode === "sign-in" ? "Signing in" : "Sign in"}
            </button>
            <button
              className="rounded-md border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-800 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting}
              onClick={(event) => handleSubmit(event, "sign-up")}
              type="button"
            >
              {isSubmitting && mode === "sign-up" ? "Signing up" : "Sign up"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
