import type { ReactNode } from "react";

export const fmt = {
  n: (v: number | null | undefined) => (v == null || Number.isNaN(v) ? "–" : Math.round(v).toLocaleString("en-US")),
  r: (v: number | null | undefined, d = 2) => (v == null || Number.isNaN(v) ? "–" : v.toFixed(d)),
  x: (v: number | null | undefined, d = 2) => (v == null || Number.isNaN(v) ? "–" : `${v.toFixed(d)}x`),
  pct: (v: number | null | undefined, d = 0) => (v == null || Number.isNaN(v) ? "–" : `${(v * 100).toFixed(d)}%`),
  label: (s: string | null | undefined) => (s ?? "").replace(/_/g, " "),
};

export function Panel({ title, right, children, className = "" }: {
  title: ReactNode; right?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="h-panel">
        <h3>{title}</h3>
        {right}
      </div>
      {children}
    </section>
  );
}

export function Stat({ k, v, n }: { k: string; v: ReactNode; n?: ReactNode }) {
  return (
    <div className="panel">
      <div className="text-[11px] uppercase tracking-wide muted">{k}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{v}</div>
      {n && <div className="text-[11px] muted">{n}</div>}
    </div>
  );
}

export function Loading({ what = "data" }: { what?: string }) {
  return <div className="p-6 text-sm muted">Loading {what}…</div>;
}

export function ErrorBox({ error }: { error: unknown }) {
  return <div className="panel border-rose-300 text-sm text-rose-700">{String(error)}</div>;
}

export function Completeness({ status }: { status: string }) {
  const s = status.toLowerCase();
  const style = s.startsWith("available")
    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200"
    : s.startsWith("unavailable")
      ? "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200"
      : "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200";
  return <span className={`chip border-transparent ${style}`}>{status}</span>;
}
