/* eslint-disable @typescript-eslint/no-explicit-any */
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { ErrorBox, fmt, Loading, Panel } from "../components/ui";

const ROWS: [string, string, (v: any) => string][] = [
  ["followers", "Followers (snapshot)", fmt.n],
  ["authored_median_views_90d", "Median views per authored post (90d)", fmt.n],
  ["median_views_per_1k_followers", "Median views per 1k followers", (v) => fmt.r(v, 1)],
  ["median_eng_per_1k_views", "Engagements per 1k views", (v) => fmt.r(v, 1)],
  ["median_likes_per_1k", "Likes per 1k views", (v) => fmt.r(v)],
  ["median_replies_per_1k", "Replies per 1k views", (v) => fmt.r(v)],
  ["median_bookmarks_per_1k", "Bookmarks per 1k views", (v) => fmt.r(v)],
  ["authored_per_week", "Authored posts per week", (v) => fmt.r(v, 1)],
  ["share_article", "Share of output as X Articles", fmt.pct],
  ["article_lift", "X Article median vs other formats", (v) => fmt.x(v)],
  ["trend_per_30d", "Reach trend per 30 days", (v) => fmt.x(v)],
  ["top5pct_share_of_views", "Views from top 5% of posts", fmt.pct],
  ["third_post_vs_baseline", "3rd+ same-day post vs baseline", (v) => fmt.x(v)],
  ["replies_per_week", "Replies per week (all roles)", (v) => fmt.r(v, 1)],
  ["conversational_comments", "Conversational comments", fmt.n],
  ["fulfilment_replies", "Lead-magnet fulfilment replies", fmt.n],
  ["median_views_per_comment", "Median views per comment", fmt.n],
  ["substantive_comment_share", "Substantive comment share", fmt.pct],
];

export default function ComparePage() {
  const q = useQuery({ queryKey: ["comparison"], queryFn: api.comparison });
  if (q.error) return <ErrorBox error={q.error} />;
  if (!q.data) return <Loading />;
  const c = q.data;
  const hs = Object.keys(c.accounts);
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Comparative growth intelligence</h1>
      <p className="text-xs muted">Independent audits compared on normalised metrics — never pooled.</p>
      <Panel title="Normalised metrics">
        <table className="tbl">
          <thead><tr><th>Metric</th>{hs.map((h) => <th key={h} className="num">@{h}</th>)}</tr></thead>
          <tbody>{ROWS.map(([k, label, f]) => (
            <tr key={k}><td>{label}</td>{hs.map((h) => <td key={h} className="num">{f(c.accounts[h][k])}</td>)}</tr>
          ))}</tbody>
        </table>
        <ul className="mt-2 list-disc pl-5 text-xs muted">{c.notes.map((n: string) => <li key={n}>{n}</li>)}</ul>
      </Panel>
      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="Shared issues">
          <ul className="space-y-1 text-sm">{c.shared_issues.map((r: any) => (
            <li key={r.diagnostic}>{r.issue} <span className="muted text-xs">({hs.map((h) => `${h}: ${r.status[h]}`).join(" · ")})</span></li>
          ))}</ul>
        </Panel>
        <Panel title="Account-specific issues">
          <ul className="space-y-1 text-sm">{c.account_specific_issues.map((r: any) => (
            <li key={r.diagnostic}>{r.issue} <span className="muted text-xs">({hs.map((h) => `${h}: ${r.status[h]}`).join(" · ")})</span></li>
          ))}</ul>
        </Panel>
      </div>
      <Panel title="Transferable strategies">
        {c.transferable.length ? (
          <table className="tbl">
            <thead><tr><th>From</th><th>To</th><th>Strategy</th><th>Basis</th></tr></thead>
            <tbody>{c.transferable.map((t: any, i: number) => (
              <tr key={i}><td>@{t.from}</td><td>@{t.to}</td><td>{t.strategy}</td><td>{t.basis}</td></tr>
            ))}</tbody>
          </table>
        ) : <p className="text-sm muted">Nothing clears the transfer threshold.</p>}
        <p className="mt-2 text-xs muted">Proposed only where the receiving account's own data already shows the mechanism working. Copying a post is not expected to reproduce its performance.</p>
      </Panel>
    </div>
  );
}
