import type { ReactNode } from "react";
import type { EvidenceClass } from "../api";

export const fmt = {
  n: (v: number | null | undefined) => (v == null || Number.isNaN(v) ? "–" : Math.round(v).toLocaleString("en-US")),
  r: (v: number | null | undefined, d = 2) => (v == null || Number.isNaN(v) ? "–" : v.toFixed(d)),
  x: (v: number | null | undefined, d = 2) => (v == null || Number.isNaN(v) ? "–" : `${v.toFixed(d)}x`),
  pct: (v: number | null | undefined, d = 0) => (v == null || Number.isNaN(v) ? "–" : `${(v * 100).toFixed(d)}%`),
  label: (s: string | null | undefined) => (s ?? "").replace(/_/g, " "),
};

const CLASS_STYLE: Record<string, string> = {
  repo_verified: "border-blue-500 text-blue-700 dark:text-blue-300",
  account_observed: "border-emerald-600 text-emerald-700 dark:text-emerald-300",
  statistical_association: "border-violet-500 text-violet-700 dark:text-violet-300",
  hypothesis: "border-amber-500 text-amber-700 dark:text-amber-300",
  unsupported: "border-rose-500 text-rose-700 dark:text-rose-300",
  insufficient: "border-rose-500 text-rose-700 dark:text-rose-300",
};

export const CLASS_PLAIN: Record<string, string> = {
  repo_verified: "Proven in X's published code",
  account_observed: "Seen in your data",
  statistical_association: "Pattern in your data (not proof of cause)",
  hypothesis: "Idea to test",
  unsupported: "Not supported",
  insufficient: "Not enough data",
};

export function ClassBadge({ c }: { c: EvidenceClass | string }) {
  return <span title={`Evidence class: ${fmt.label(c)}`} className={`chip ${CLASS_STYLE[c] ?? "border-slate-400"}`}>{CLASS_PLAIN[c] ?? fmt.label(c)}</span>;
}

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
