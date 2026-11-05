type EmptyStateProps = {
  title: string;
  description: string;
};

type LoadingStateProps = {
  label: string;
};

type ErrorStateProps = {
  title: string;
  description: string;
  actionLabel: string;
  onAction: () => void;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="border border-dashed border-slate-300 bg-white p-8 text-center shadow-sm">
      <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-600">{description}</p>
    </div>
  );
}

export function LoadingState({ label }: LoadingStateProps) {
  return (
    <div className="border border-slate-200 bg-white p-8 shadow-sm">
      <div className="h-2 w-36 animate-pulse rounded bg-slate-200" />
      <p className="mt-4 text-sm font-medium text-slate-600">{label}</p>
    </div>
  );
}

export function ErrorState({ title, description, actionLabel, onAction }: ErrorStateProps) {
  return (
    <div className="border border-red-200 bg-white p-8 shadow-sm">
      <h2 className="text-lg font-semibold text-red-700">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
      <button
        className="mt-5 rounded-md bg-red-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-800"
        onClick={onAction}
        type="button"
      >
        {actionLabel}
      </button>
    </div>
  );
}
