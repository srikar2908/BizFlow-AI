import Link from "next/link";

const principles = [
  "Private document workspace",
  "Cited retrieval answers",
  "Human-approved automation",
];

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-6">
        <nav className="flex items-center justify-between border-b border-slate-200 pb-5">
          <Link className="text-lg font-semibold tracking-tight" href="/">
            BizFlow AI
          </Link>
          <div className="flex items-center gap-3 text-sm font-medium">
            <Link className="text-slate-600 transition hover:text-slate-950" href="/login">
              Log in
            </Link>
            <Link
              className="rounded-md bg-slate-950 px-4 py-2 text-white transition hover:bg-slate-800"
              href="/dashboard"
            >
              Dashboard
            </Link>
          </div>
        </nav>

        <div className="grid flex-1 items-center gap-10 py-14 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="max-w-2xl">
            <p className="mb-4 text-sm font-semibold uppercase tracking-wide text-emerald-700">
              SME operations workspace
            </p>
            <h1 className="text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
              BizFlow AI
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
              A secure RAG and automation foundation for document-heavy business workflows,
              proposal drafting, and reviewed external actions.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                className="rounded-md bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
                href="/login"
              >
                Log in
              </Link>
              <Link
                className="rounded-md border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-800 transition hover:border-slate-500"
                href="/dashboard"
              >
                View shell
              </Link>
            </div>
          </div>

          <div className="border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-5 flex items-center justify-between border-b border-slate-200 pb-4">
              <div>
                <p className="text-sm font-semibold text-slate-950">MVP flow</p>
                <p className="text-sm text-slate-500">Foundation only</p>
              </div>
              <span className="rounded-md bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                Planned
              </span>
            </div>
            <div className="space-y-3">
              {principles.map((principle) => (
                <div
                  className="flex items-center justify-between border border-slate-200 px-4 py-3 text-sm"
                  key={principle}
                >
                  <span className="font-medium text-slate-800">{principle}</span>
                  <span className="text-slate-400">Queued</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
