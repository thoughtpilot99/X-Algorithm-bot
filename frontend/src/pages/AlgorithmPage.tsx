/* eslint-disable @typescript-eslint/no-explicit-any */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, STATIC } from "../api";
import { ClassBadge, fmt, Loading, Panel } from "../components/ui";

const AREAS: Record<string, string> = {
  A: "Content candidate retrieval",
  B: "Ranking and engagement prediction",
  C: "Account and content quality",
  D: "Feed-level ranking behaviour",
};

const VERDICT: Record<string, string> = {
  supported: "account_observed",
  partially_supported: "hypothesis",
  contradicted: "unsupported",
  not_found_in_repo: "unsupported",
  unverifiable: "insufficient",
};

export default function AlgorithmPage() {
  const findings = useQuery({ queryKey: ["findings"], queryFn: api.findings });
  const claims = useQuery({ queryKey: ["claims"], queryFn: api.claims });
  const params = useQuery({ queryKey: ["params"], queryFn: () => api.params() });
  const [area, setArea] = useState("A");
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<any[] | null>(null);
  const [hist, setHist] = useState<{ name: string; rows: any[] } | null>(null);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">What the published X algorithm says</h1>
      <p className="text-xs muted">
        Every finding cites a file and line range at commit {params.data?.studied_sha?.slice(0, 7) ?? "…"} and is machine-checked.
        The public repository is not a complete description of production. Weights multiply per-viewer predicted probabilities, not raw counts.
      </p>
      <Panel title="Published weights and key parameters (home-mixer defaults)">
        {params.data ? (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Parameter</th><th className="num">Value</th><th>Source</th><th /></tr></thead>
              <tbody>{params.data.key_params.filter((p: any) => p.path.startsWith("home-mixer")).map((p: any) => (
                <tr key={p.name}>
                  <td>{p.name}</td><td className="num">{p.raw_value}</td>
                  <td><a className="text-blue-600 hover:underline dark:text-blue-400" href={p.permalink} target="_blank" rel="noreferrer">{p.path}:{p.line}</a></td>
                  <td><button className="btn" onClick={async () => setHist({ name: p.name, rows: (await api.params(p.name)).history })}>history</button></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <Loading />}
        {hist && (
          <div className="mt-3 rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
            <b>{hist.name}</b> across scanned commits:{" "}
            {hist.rows.map((r, i) => <span key={i} className="mr-2">{r.committed_at?.slice(0, 10)} {r.path.split("/")[0]}={r.value}</span>)}
          </div>
        )}
      </Panel>
      {!STATIC && <Panel title="Code search (pinned commit)">
        <form className="flex gap-2" onSubmit={async (e) => { e.preventDefault(); setHits(await api.search(q)); }}>
          <input className="input flex-1" placeholder="e.g. author diversity, oon, cold start" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="btn">Search</button>
        </form>
        {hits && (
          <ul className="mt-3 space-y-2 text-xs">{hits.map((h, i) => (
            <li key={i}><a className="text-blue-600 hover:underline dark:text-blue-400" href={h.permalink} target="_blank" rel="noreferrer">{h.path}:{h.start}-{h.end}</a> <span className="muted">{h.symbol}</span>
              <pre className="mt-1 whitespace-pre-wrap rounded bg-slate-100 p-2 dark:bg-slate-800">{h.snippet}</pre></li>
          ))}</ul>
        )}
      </Panel>}
      <Panel title="Findings registry" right={
        <div className="flex gap-1">{Object.keys(AREAS).map((a) => (
          <button key={a} className={`btn ${area === a ? "bg-slate-200 dark:bg-slate-700" : ""}`} onClick={() => setArea(a)}>{a}. {AREAS[a]}</button>
        ))}</div>}>
        {findings.data ? (
          <div className="space-y-3">{findings.data.filter((f) => f.area === area).map((f) => (
            <article key={f.id} className="rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
              <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
                {f.id} · {f.title}<ClassBadge c={f.status === "verified" ? "repo_verified" : f.status === "inferred" ? "hypothesis" : "insufficient"} />
              </div>
              <a className="text-blue-600 hover:underline dark:text-blue-400" href={f.permalink} target="_blank" rel="noreferrer">{f.path}:{f.lines[0]}-{f.lines[1]}</a> <span className="muted">· {f.symbol}</span>
              <p className="mt-1">{f.mechanism}</p>
              <p className="mt-1"><b>Relevance:</b> {f.relevance}</p>
              <p className="mt-1 muted"><b>Observable proxy:</b> {f.observable_proxy}</p>
              <p className="mt-1 muted"><b>Limitations:</b> {f.limitations}</p>
            </article>
          ))}</div>
        ) : <Loading />}
      </Panel>
      <Panel title="Common claims checked against the repository">
        {claims.data ? (
          <table className="tbl">
            <thead><tr><th>Claim</th><th>Verdict</th><th>Explanation</th></tr></thead>
            <tbody>{claims.data.map((c) => (
              <tr key={c.id}>
                <td className="max-w-xs">{c.claim}</td>
                <td><ClassBadge c={VERDICT[c.verdict] ?? "hypothesis"} /> <div className="mt-1">{fmt.label(c.verdict)}</div></td>
                <td>{c.explanation}{(c.evidence ?? []).map((e: any, i: number) => (
                  <div key={i}><a className="text-blue-600 hover:underline dark:text-blue-400" href={e.permalink} target="_blank" rel="noreferrer">{e.path}:{e.lines[0]}-{e.lines[1]}</a></div>
                ))}</td>
              </tr>
            ))}</tbody>
          </table>
        ) : <Loading />}
      </Panel>
    </div>
  );
}
