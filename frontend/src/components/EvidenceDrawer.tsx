import { useEffect } from "react";
import type { Diagnostic } from "../api";
import { ClassBadge, Confidence, fmt } from "./ui";

export default function EvidenceDrawer({ d, onClose }: { d: Diagnostic | null; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  if (!d) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onClick={onClose}>
      <aside
        className="h-full w-full max-w-2xl overflow-y-auto bg-white p-5 shadow-xl dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
        aria-label="Evidence"
      >
        <div className="flex items-start justify-between gap-3">
          <h2 className="text-lg font-semibold">{d.issue}</h2>
          <button className="btn" onClick={onClose}>Close</button>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <ClassBadge c={d.evidence_class} />
          <span className="chip border-slate-400">{d.status}</span>
          <Confidence level={d.confidence} />
          <span className="chip border-slate-300">priority {fmt.r(d.priority)}</span>
        </div>
        <Field t="Observation">{d.observation}</Field>
        <Field t="Evidence">
          <ul className="space-y-1">
            {d.evidence.map((e, i) => (
              <li key={i} className="flex flex-wrap items-baseline gap-2">
                <ClassBadge c={e.evidence_class} />
                {e.url ? (
                  <a className="text-blue-600 hover:underline dark:text-blue-400" href={e.url} target="_blank" rel="noreferrer">
                    {e.label}
                  </a>
                ) : (
                  <span>
                    {e.label}
                    {e.value != null && <b className="ml-1 tabular-nums">{String(e.value)}</b>}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Field>
        <Field t="Algorithm connection">
          <p>{d.algo_connection}</p>
          <ul className="mt-2 space-y-1">
            {d.algo_findings.map((f) => (
              <li key={f.id}>
                <a className="text-blue-600 hover:underline dark:text-blue-400" href={f.permalink} target="_blank" rel="noreferrer">
                  {f.id} · {f.title}
                </a>{" "}
                <span className="muted text-xs">{f.path}:{f.lines[0]}-{f.lines[1]} · {f.status}</span>
              </li>
            ))}
          </ul>
        </Field>
        <Field t="Alternative explanations">
          <ul className="list-disc pl-5">{d.alternatives.map((a, i) => <li key={i}>{a}</li>)}</ul>
        </Field>
        <Field t="Impact">{d.impact}</Field>
        <Field t="Recommendation">{d.recommendation}</Field>
        <Field t="Validation">{d.validation}</Field>
        {d.success_criteria && <Field t="Success criteria">{d.success_criteria}</Field>}
        {d.confounders?.length > 0 && <Field t="Confounders">{d.confounders.join(", ")}</Field>}
      </aside>
    </div>
  );
}

function Field({ t, children }: { t: string; children: React.ReactNode }) {
  return (
    <div className="mt-4 text-sm">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide muted">{t}</div>
      {children}
    </div>
  );
}
