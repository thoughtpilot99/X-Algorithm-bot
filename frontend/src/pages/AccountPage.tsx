/* eslint-disable @typescript-eslint/no-explicit-any */
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { NavLink, useParams } from "react-router-dom";
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";
import { api, type Diagnostic, type Post } from "../api";
import EvidenceDrawer from "../components/EvidenceDrawer";
import { ClassBadge, Completeness, Confidence, ErrorBox, fmt, Loading, Panel, Stat } from "../components/ui";

export const SECTIONS: [string, string][] = [
  ["overview", "Executive overview"],
  ["trends", "Reach & engagement"],
  ["posts", "Original posts"],
  ["replies", "Replies & commenting"],
  ["topics", "Topics"],
  ["network", "Audience & network"],
  ["algorithm", "Algorithm findings"],
  ["blockers", "Growth blockers"],
  ["benchmarks", "Benchmarks"],
  ["experiments", "Experiments"],
  ["results", "Experiment results"],
  ["data", "Data & confidence"],
];

export interface Filters {
  start: string;
  end: string;
  types: string[];
  topic: string;
  segment: string;
}

const TYPES = ["original", "quote", "reply", "repost"];
const TYPE_COLORS: Record<string, string> = { original: "#2563eb", quote: "#7c3aed", reply: "#059669", repost: "#94a3b8" };

function median(xs: number[]): number | null {
  const a = xs.filter((x) => x != null && !Number.isNaN(x)).sort((p, q) => p - q);
  if (!a.length) return null;
  const m = Math.floor(a.length / 2);
  return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
}

function applyFilters(posts: Post[], f: Filters): Post[] {
  return posts.filter((p) => {
    const d = p.created_at.slice(0, 10);
    if (f.start && d < f.start) return false;
    if (f.end && d > f.end) return false;
    if (f.types.length && !f.types.includes(p.post_type)) return false;
    if (f.topic && p.topic !== f.topic) return false;
    const vb = p.vs_baseline;
    if (f.segment === "above_2x" && !(vb != null && vb >= 2)) return false;
    if (f.segment === "below_half" && !(vb != null && vb <= 0.5)) return false;
    if (f.segment === "near_baseline" && !(vb != null && vb > 0.5 && vb < 2)) return false;
    return true;
  });
}

export default function AccountPage() {
  const { handle = "", section = "overview" } = useParams();
  const [filters, setFilters] = useState<Filters>({ start: "", end: "", types: [], topic: "", segment: "" });
  const [drawer, setDrawer] = useState<Diagnostic | null>(null);
  const overview = useQuery({ queryKey: ["overview", handle], queryFn: () => api.overview(handle) });
  const posts = useQuery({ queryKey: ["posts", handle], queryFn: () => api.posts(handle) });
  const filtered = useMemo(() => applyFilters(posts.data?.items ?? [], filters), [posts.data, filters]);
  const topics = useMemo(
    () => [...new Set((posts.data?.items ?? []).map((p) => p.topic).filter(Boolean) as string[])].sort(),
    [posts.data],
  );

  if (overview.error) return <ErrorBox error={overview.error} />;
  if (!overview.data) return <Loading what="account" />;
  const o = overview.data;
  const showFilters = ["trends", "posts", "replies", "topics"].includes(section);

  return (
    <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
      <nav className="flex gap-1 overflow-x-auto lg:sticky lg:top-20 lg:flex-col lg:self-start" aria-label="Sections">
        {SECTIONS.map(([id, label], i) => (
          <NavLink
            key={id}
            to={`/a/${handle}/${id}`}
            className={({ isActive }) =>
              `whitespace-nowrap rounded-md px-3 py-1.5 text-sm ${isActive ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900" : "hover:bg-slate-200 dark:hover:bg-slate-800"}`
            }
          >
            <span className="muted mr-1.5 tabular-nums">{i + 1}.</span>
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="min-w-0 space-y-4">
        <header>
          <h1 className="text-2xl font-semibold">{o.name} <span className="muted text-lg font-normal">@{handle}</span></h1>
          <p className="text-xs muted">
            {o.profile.window[0].slice(0, 10)} → {o.profile.window[1].slice(0, 10)} · public data only · {fmt.n(o.profile.followers)} followers (snapshot)
          </p>
        </header>
        {showFilters && (
          <FilterBar filters={filters} setFilters={setFilters} topics={topics} count={filtered.length} handle={handle} />
        )}
        {posts.error && <ErrorBox error={posts.error} />}
        {section === "overview" && <Overview o={o} handle={handle} open={setDrawer} />}
        {section === "trends" && <Trends handle={handle} posts={filtered} />}
        {section === "posts" && <OriginalPosts handle={handle} posts={filtered} />}
        {section === "replies" && <Replies handle={handle} posts={filtered} />}
        {section === "topics" && <Topics handle={handle} posts={filtered} />}
        {section === "network" && <Network handle={handle} />}
        {section === "algorithm" && <AlgoFindings handle={handle} open={setDrawer} />}
        {section === "blockers" && <Blockers handle={handle} open={setDrawer} />}
        {section === "benchmarks" && <Benchmarks handle={handle} />}
        {section === "experiments" && <Experiments handle={handle} />}
        {section === "results" && <Results />}
        {section === "data" && <DataSection completeness={o.completeness} />}
      </div>
      <EvidenceDrawer d={drawer} onClose={() => setDrawer(null)} />
    </div>
  );
}

function FilterBar({ filters, setFilters, topics, count, handle }: {
  filters: Filters; setFilters: (f: Filters) => void; topics: string[]; count: number; handle: string;
}) {
  const qs = new URLSearchParams();
  if (filters.start) qs.set("start", filters.start);
  if (filters.end) qs.set("end", filters.end);
  filters.types.forEach((t) => qs.append("type", t));
  if (filters.topic) qs.set("topic", filters.topic);
  if (filters.segment) qs.set("segment", filters.segment);
  return (
    <div className="panel flex flex-wrap items-end gap-3 text-xs">
      <label className="flex flex-col gap-1">From
        <input type="date" className="input" value={filters.start} onChange={(e) => setFilters({ ...filters, start: e.target.value })} />
      </label>
      <label className="flex flex-col gap-1">To
        <input type="date" className="input" value={filters.end} onChange={(e) => setFilters({ ...filters, end: e.target.value })} />
      </label>
      <fieldset className="flex flex-col gap-1">
        <legend>Content type</legend>
        <div className="flex gap-2">
          {TYPES.map((t) => (
            <label key={t} className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={filters.types.includes(t)}
                onChange={(e) =>
                  setFilters({ ...filters, types: e.target.checked ? [...filters.types, t] : filters.types.filter((x) => x !== t) })
                }
              />
              {t}
            </label>
          ))}
        </div>
      </fieldset>
      <label className="flex flex-col gap-1">Topic
        <select className="input" value={filters.topic} onChange={(e) => setFilters({ ...filters, topic: e.target.value })}>
          <option value="">All topics</option>
          {topics.map((t) => <option key={t}>{t}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1">Performance segment
        <select className="input" value={filters.segment} onChange={(e) => setFilters({ ...filters, segment: e.target.value })}>
          <option value="">All posts</option>
          <option value="above_2x">Above 2x baseline</option>
          <option value="near_baseline">Near baseline</option>
          <option value="below_half">Below 0.5x baseline</option>
        </select>
      </label>
      <button className="btn" onClick={() => setFilters({ start: "", end: "", types: [], topic: "", segment: "" })}>Reset</button>
      <span className="muted ml-auto">{count.toLocaleString()} records</span>
      <a className="btn" href={`/api/accounts/${handle}/posts.csv?${qs}`}>Export CSV</a>
    </div>
  );
}

function Overview({ o, handle, open }: { o: any; handle: string; open: (d: Diagnostic) => void }) {
  const answers = useQuery({ queryKey: ["answers", handle], queryFn: () => api.answers(handle) });
  const a = o.reach.segments["authored (original + quote)"] ?? {};
  const t = o.reach.trend_authored ?? {};
  const c = o.comments_summary?.conversation ?? {};
  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat k="Median views / authored post" v={fmt.n(a.median)} n={`n=${a.n} · 180 days`} />
        <Stat k="Trend per 30 days" v={fmt.x(t.per_30d)} n={`90% CI ${fmt.r(t.lo)}–${fmt.r(t.hi)}`} />
        <Stat k="Posts above 2x baseline" v={fmt.pct(o.reach.vs_baseline?.share_above_2x)} n={`below 0.5x: ${fmt.pct(o.reach.vs_baseline?.share_below_half)}`} />
        <Stat k="Median views / comment" v={fmt.n(c.views?.median)} n={`n=${c.n} conversational`} />
      </div>
      <Panel title="Top 5 potential barriers to organic growth" right={<span className="text-xs muted">click for evidence</span>}>
        <ol className="space-y-2">
          {o.root_causes.map((r: Diagnostic) => (
            <li key={r.id}>
              <button className="w-full rounded-lg border border-slate-200 p-3 text-left hover:border-slate-400 dark:border-slate-800" onClick={() => open(r)}>
                <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                  <span className="tabular-nums muted">{r.rank}.</span>
                  {r.issue}
                  <ClassBadge c={r.evidence_class} />
                  <Confidence level={r.confidence} />
                </div>
                <p className="mt-1 text-xs muted">{r.observation}</p>
              </button>
            </li>
          ))}
        </ol>
      </Panel>
      <div className="grid gap-4 md:grid-cols-3">
        {(["stop", "continue", "start"] as const).map((k) => (
          <Panel key={k} title={k[0].toUpperCase() + k.slice(1)}>
            <ul className="space-y-1.5 text-xs">
              {(o.actions[k] ?? []).map((x: any, i: number) => (
                <li key={i} className="flex flex-col gap-0.5">
                  <span>{x.action}</span>
                  <span><ClassBadge c={x.evidence_class} /></span>
                </li>
              ))}
            </ul>
          </Panel>
        ))}
      </div>
      <Panel title="The fourteen questions">
        {answers.data ? (
          <ol className="space-y-3 text-sm">
            {answers.data.map((q, i) => (
              <li key={i}>
                <div className="font-medium">{i + 1}. {q.q} <ClassBadge c={q.class} /></div>
                <p className="text-xs muted">{q.a}</p>
              </li>
            ))}
          </ol>
        ) : <Loading what="answers" />}
      </Panel>
    </>
  );
}

function weekly(posts: Post[]) {
  const by: Record<string, { a: number[]; r: number[] }> = {};
  for (const p of posts) {
    if (!p.mature || p.views == null) continue;
    const d = new Date(p.created_at);
    const monday = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() - ((d.getUTCDay() + 6) % 7)));
    const k = monday.toISOString().slice(0, 10);
    by[k] ??= { a: [], r: [] };
    if (p.post_type === "original" || p.post_type === "quote") by[k].a.push(p.views);
    else if (p.post_type === "reply") by[k].r.push(p.views);
  }
  return Object.entries(by)
    .sort(([x], [y]) => x.localeCompare(y))
    // Log axis: a zero median would collapse the scale, so it is plotted as a gap.
    .map(([week, v]) => {
      const pos = (x: number | null) => (x != null && x > 0 ? x : null);
      return { week, t: Date.parse(week), authored: pos(median(v.a)), replies: pos(median(v.r)), n: v.a.length };
    });
}

function Trends({ handle, posts }: { handle: string; posts: Post[] }) {
  const eng = useQuery({ queryKey: ["engagement", handle], queryFn: () => api.artifact(handle, "engagement") });
  const w = useMemo(() => weekly(posts), [posts]);
  const pts = useMemo(
    () => posts.filter((p) => p.views && p.views > 0).map((p) => ({ t: Date.parse(p.created_at), v: p.views, type: p.post_type, id: p.tweet_id })),
    [posts],
  );
  return (
    <>
      <Panel title="Weekly median views (mature posts in filter)" right={<span className="chip border-violet-500 text-violet-700">medians — robust to viral outliers</span>}>
        <div className="h-72">
          <ResponsiveContainer>
            <LineChart data={w}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]}
                tickFormatter={(t) => new Date(t).toISOString().slice(0, 10)} tick={{ fontSize: 10 }} />
              <YAxis scale="log" domain={[1, "auto"]} tick={{ fontSize: 10 }} allowDataOverflow />
              <Tooltip labelFormatter={(t) => `week of ${new Date(t as number).toISOString().slice(0, 10)}`} formatter={(v: any) => fmt.n(v)} />
              <Legend />
              <Line type="linear" dataKey="authored" name="authored (original+quote)" stroke="#2563eb" dot={false} connectNulls />
              <Line type="linear" dataKey="replies" name="replies" stroke="#059669" dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Panel>
      <Panel title="Every post: views over time (log scale)">
        <div className="h-72">
          <ResponsiveContainer>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="t" type="number" domain={["auto", "auto"]} tickFormatter={(t) => new Date(t).toISOString().slice(5, 10)} tick={{ fontSize: 10 }} />
              <YAxis dataKey="v" type="number" scale="log" domain={[1, "auto"]} tick={{ fontSize: 10 }} allowDataOverflow />
              <ZAxis range={[14, 14]} />
              <Tooltip formatter={(v: any, k: any) => (k === "t" ? new Date(v).toISOString().slice(0, 10) : fmt.n(v))} />
              <Legend />
              {TYPES.map((t) => (
                <Scatter key={t} name={t} data={pts.filter((p) => p.type === t)} fill={TYPE_COLORS[t]} opacity={0.6} />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </Panel>
      <Panel title="Engagement efficiency (per 1,000 views, all mature posts)" right={<ClassBadge c="account_observed" />}>
        {eng.data ? (
          <>
            <table className="tbl">
              <thead><tr><th>Type</th>{["likes", "replies", "reposts", "quotes", "bookmarks", "eng"].map((m) => <th key={m} className="num">{m}/1k</th>)}</tr></thead>
              <tbody>
                {Object.entries(eng.data.by_type).map(([t, d]: any) => (
                  <tr key={t}><td>{t}</td>{["likes", "replies", "reposts", "quotes", "bookmarks", "eng"].map((m) => <td key={m} className="num">{fmt.r(d[`${m}_per_1k`]?.median)}</td>)}</tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-xs muted">Observed outcome rates, not ranking scores. Unavailable: {Object.keys(eng.data.unavailable).map(fmt.label).join(", ")}.</p>
          </>
        ) : <Loading />}
      </Panel>
    </>
  );
}

function PostTable({ posts, cols }: { posts: Post[]; cols: ("vs_baseline" | "topic" | "category" | "parent")[] }) {
  const [sort, setSort] = useState<"views" | "vs_baseline" | "created_at">("created_at");
  const rows = [...posts].sort((a, b) =>
    sort === "created_at" ? b.created_at.localeCompare(a.created_at) : ((b as any)[sort] ?? -1) - ((a as any)[sort] ?? -1),
  ).slice(0, 300);
  return (
    <div className="overflow-x-auto">
      <div className="mb-2 flex gap-2 text-xs">
        Sort:
        {(["created_at", "views", "vs_baseline"] as const).map((s) => (
          <button key={s} className={`btn ${sort === s ? "bg-slate-200 dark:bg-slate-700" : ""}`} onClick={() => setSort(s)}>{fmt.label(s)}</button>
        ))}
        <span className="muted">showing {rows.length} of {posts.length}</span>
      </div>
      <table className="tbl">
        <thead>
          <tr>
            <th>Date</th><th>Type / format</th>{cols.includes("parent") && <th>To</th>}<th>Text</th>
            {cols.includes("topic") && <th>Topic</th>}{cols.includes("category") && <th>Category</th>}
            <th className="num">Views</th>{cols.includes("vs_baseline") && <th className="num">vs baseline</th>}
            <th className="num">Likes</th><th className="num">Replies</th><th className="num">Bkm</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.tweet_id} className={p.mature ? "" : "opacity-60"}>
              <td className="whitespace-nowrap">{p.created_at.slice(0, 10)}</td>
              <td>{p.post_type}<div className="muted">{fmt.label(p.format)}</div></td>
              {cols.includes("parent") && <td>@{p.parent_author}</td>}
              <td className="max-w-md"><a className="hover:underline" href={p.url} target="_blank" rel="noreferrer">{p.text.slice(0, 180)}</a></td>
              {cols.includes("topic") && <td>{p.topic}</td>}
              {cols.includes("category") && <td>{fmt.label(p.category)}</td>}
              <td className="num">{fmt.n(p.views)}</td>
              {cols.includes("vs_baseline") && <td className="num">{fmt.x(p.vs_baseline)}</td>}
              <td className="num">{fmt.n(p.likes)}</td><td className="num">{fmt.n(p.replies)}</td><td className="num">{fmt.n(p.bookmarks)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs muted">Faded rows are younger than 72h at observation (views still accruing) and are excluded from baselines.</p>
    </div>
  );
}

function OriginalPosts({ handle, posts }: { handle: string; posts: Post[] }) {
  const segs = useQuery({ queryKey: ["segments", handle], queryFn: () => api.artifact<any[]>(handle, "segments") });
  const mv = useQuery({ queryKey: ["mv", handle], queryFn: () => api.artifact(handle, "multivariable") });
  const authored = posts.filter((p) => p.post_type === "original" || p.post_type === "quote");
  const quad: Record<string, number> = {};
  authored.forEach((p) => p.quadrant && (quad[p.quadrant] = (quad[p.quadrant] ?? 0) + 1));
  return (
    <>
      <Panel title="Characteristics associated with higher / lower reach" right={<ClassBadge c="statistical_association" />}>
        <p className="mb-2 text-xs muted">Each level vs all other authored posts (180 days). Ratio of medians, 90% bootstrap CI, Benjamini–Hochberg q. Associations, not causes.</p>
        <div className="overflow-x-auto">
          <table className="tbl">
            <thead><tr><th>Feature</th><th>Level</th><th className="num">n</th><th className="num">Median</th><th className="num">Ratio</th><th className="num">90% CI</th><th className="num">q</th><th>Signal</th></tr></thead>
            <tbody>
              {(segs.data ?? []).filter((s) => s.signal === "higher" || s.signal === "lower").map((s, i) => (
                <tr key={i}>
                  <td>{s.feature_label}</td><td>{s.level}</td><td className="num">{s.n}</td><td className="num">{fmt.n(s.median)}</td>
                  <td className="num">{fmt.x(s.ratio)}</td><td className="num">{fmt.r(s.lo)}–{fmt.r(s.hi)}</td><td className="num">{fmt.r(s.q, 3)}</td>
                  <td className={s.signal === "higher" ? "text-emerald-600" : "text-rose-600"}>{s.signal}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      {mv.data?.fitted && (
        <Panel title={`Multivariable model (n=${mv.data.n}, R² ${fmt.r(mv.data.r2)})`} right={<ClassBadge c="statistical_association" />}>
          <p className="mb-2 text-xs muted">{mv.data.controls}. Multipliers relative to the reference level.</p>
          <table className="tbl">
            <thead><tr><th>Term</th><th className="num">Multiplier</th><th className="num">90% CI</th><th className="num">p</th></tr></thead>
            <tbody>{mv.data.coefficients.slice(0, 12).map((c: any) => (
              <tr key={c.term}><td>{c.term}</td><td className="num">{fmt.x(c.multiplier)}</td><td className="num">{fmt.r(c.lo)}–{fmt.r(c.hi)}</td><td className="num">{fmt.r(c.p, 3)}</td></tr>
            ))}</tbody>
          </table>
        </Panel>
      )}
      <Panel title="Visibility vs efficiency quadrant (authored, filtered)">
        <div className="flex flex-wrap gap-3 text-sm">
          {Object.entries(quad).map(([k, v]) => <span key={k} className="chip border-slate-300">{k}: {v}</span>)}
        </div>
        <p className="mt-2 text-xs muted">Reach vs the post's trailing baseline × engagement per 1k views vs the account median. “Resonance without reach” posts are candidates for redistribution, not rewriting.</p>
      </Panel>
      <Panel title="Authored posts">
        <PostTable posts={authored} cols={["vs_baseline", "topic"]} />
      </Panel>
    </>
  );
}

function Replies({ handle, posts }: { handle: string; posts: Post[] }) {
  const c = useQuery({ queryKey: ["comments", handle], queryFn: () => api.artifact(handle, "comments") });
  const replies = posts.filter((p) => p.post_type === "reply");
  if (!c.data) return <Loading what="comments" />;
  const d = c.data;
  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {Object.entries(d.roles).map(([k, v]: any) => <Stat key={k} k={`${fmt.label(k)} replies`} v={fmt.n(v)} />)}
      </div>
      <p className="text-xs muted">{d.fulfilment.note}</p>
      <Panel title="Conversational comments by category" right={<span className="text-xs muted">{d.score_label}</span>}>
        <table className="tbl">
          <thead><tr><th>Category</th><th className="num">n</th><th className="num">Median views</th><th className="num">Median likes</th><th className="num">With a reply</th><th className="num">Effectiveness</th></tr></thead>
          <tbody>{d.by_category.map((r: any) => (
            <tr key={r.category}><td>{fmt.label(r.category)}</td><td className="num">{r.n}</td><td className="num">{fmt.n(r.median_views)}</td><td className="num">{fmt.r(r.median_likes, 1)}</td><td className="num">{fmt.pct(r.share_with_reply)}</td><td className="num">{fmt.r(r.median_effectiveness, 1)}</td></tr>
          ))}</tbody>
        </table>
        <p className="mt-2 text-xs muted">Score weights (user-editable in accounts.yaml): {Object.entries(d.score_weights).map(([k, v]) => `${k} ${v}`).join(", ")}; timing is unavailable and redistributed.</p>
      </Panel>
      {d.thread_sample && (
        <Panel title={`Thread-context sample (n=${d.thread_sample.n})`} right={<ClassBadge c="account_observed" />}>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat k="Median delay after parent" v={`${fmt.n(d.thread_sample.latency_minutes.median)} min`} />
            <Stat k="Within first hour" v={fmt.pct(d.thread_sample.share_within_60min)} />
            <Stat k="Parent author replied" v={fmt.pct(d.thread_sample.parent_author_responded_share)} />
            <Stat k="Median parent views" v={fmt.n(d.thread_sample.parent_views.median)} />
          </div>
          <p className="mt-2 text-xs muted">{d.thread_sample.note}</p>
        </Panel>
      )}
      <Panel title="Commenting questions">
        <ul className="space-y-2 text-sm">{d.questions.map((q: any, i: number) => (
          <li key={i}><div className="font-medium">{q.q} <ClassBadge c={q.evidence_class} /></div><p className="text-xs muted">{q.answer}</p></li>
        ))}</ul>
      </Panel>
      <Panel title="Replies (filtered)"><PostTable posts={replies} cols={["parent", "category"]} /></Panel>
      <Panel title="Data limits"><ul className="list-disc pl-5 text-xs muted">{d.limits.map((l: string) => <li key={l}>{l}</li>)}</ul></Panel>
    </>
  );
}

function Topics({ handle, posts }: { handle: string; posts: Post[] }) {
  const segs = useQuery({ queryKey: ["segments", handle], queryFn: () => api.artifact<any[]>(handle, "segments") });
  const rows = useMemo(() => {
    const by: Record<string, Post[]> = {};
    posts.filter((p) => (p.post_type === "original" || p.post_type === "quote") && p.mature).forEach((p) => {
      (by[p.topic ?? "unlabelled"] ??= []).push(p);
    });
    return Object.entries(by).map(([t, ps]) => ({
      topic: t, n: ps.length, median: median(ps.map((p) => p.views ?? NaN)),
      vb: median(ps.map((p) => p.vs_baseline ?? NaN)), eng: median(ps.map((p) => p.eng_per_1k ?? NaN)),
    })).sort((a, b) => b.n - a.n);
  }, [posts]);
  const topicSegs = (segs.data ?? []).filter((s) => s.feature === "topic");
  return (
    <>
      <Panel title="Topic performance (authored, filtered, mature)">
        <table className="tbl">
          <thead><tr><th>Topic</th><th className="num">Posts</th><th className="num">Median views</th><th className="num">Median vs baseline</th><th className="num">Eng / 1k</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.topic}><td>{r.topic}</td><td className="num">{r.n}</td><td className="num">{fmt.n(r.median)}</td><td className="num">{fmt.x(r.vb)}</td><td className="num">{fmt.r(r.eng, 1)}</td></tr>
          ))}</tbody>
        </table>
        <p className="mt-2 text-xs muted">Topics are model labels (method shown per post in CSV export); small groups are noisy.</p>
      </Panel>
      <Panel title="Topic comparisons with significance (180 days)" right={<ClassBadge c="statistical_association" />}>
        <table className="tbl">
          <thead><tr><th>Topic</th><th className="num">n</th><th className="num">Ratio</th><th className="num">90% CI</th><th className="num">q</th><th>Signal</th></tr></thead>
          <tbody>{topicSegs.map((s) => (
            <tr key={s.level}><td>{s.level}</td><td className="num">{s.n}</td><td className="num">{fmt.x(s.ratio)}</td><td className="num">{s.tested ? `${fmt.r(s.lo)}–${fmt.r(s.hi)}` : "–"}</td><td className="num">{fmt.r(s.q, 3)}</td><td>{s.signal}</td></tr>
          ))}</tbody>
        </table>
      </Panel>
    </>
  );
}

function Network({ handle }: { handle: string }) {
  const c = useQuery({ queryKey: ["comments", handle], queryFn: () => api.artifact(handle, "comments") });
  if (!c.data) return <Loading />;
  const conc = c.data.concentration ?? {};
  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat k="Accounts commented on" v={fmt.n(conc.distinct_parent_authors)} />
        <Stat k="Share to top 5" v={fmt.pct(conc.top5_share)} />
        <Stat k="Repeat targets (3+)" v={fmt.n(conc.repeat_targets_3plus)} />
        <Stat k="HHI concentration" v={fmt.r(conc.hhi, 3)} />
      </div>
      <Panel title="Interaction partners (whose posts the account comments on)">
        <table className="tbl">
          <thead><tr><th>Account</th><th className="num">Comments</th><th className="num">Median views</th><th className="num">Total views</th><th className="num">With a reply</th><th className="num">Effectiveness</th><th>Peer/client</th></tr></thead>
          <tbody>{c.data.partners.map((p: any) => (
            <tr key={p.parent_author}><td><a className="hover:underline" href={`https://x.com/${p.parent_author}`} target="_blank" rel="noreferrer">@{p.parent_author}</a></td><td className="num">{p.replies}</td><td className="num">{fmt.n(p.median_views)}</td><td className="num">{fmt.n(p.total_views)}</td><td className="num">{fmt.pct(p.share_with_reply)}</td><td className="num">{fmt.r(p.median_effectiveness, 1)}</td><td>{p.is_peer_or_client ? "yes" : ""}</td></tr>
          ))}</tbody>
        </table>
      </Panel>
      {c.data.engagers?.available && (
        <Panel title="Who engages with the account (public replies/quotes)" right={<ClassBadge c="account_observed" />}>
          <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat k="Engagements" v={fmt.n(c.data.engagers.n_engagements)} n={`${c.data.engagers.window[0]} → ${c.data.engagers.window[1]}`} />
            <Stat k="Distinct engagers" v={fmt.n(c.data.engagers.distinct_engagers)} n={`one-time: ${fmt.pct(c.data.engagers.one_time_share)}`} />
            <Stat k="Top 10 share" v={fmt.pct(c.data.engagers.top10_share)} n={`${c.data.engagers.repeat_engagers_3plus} engaged 3+ times`} />
            <Stat k="Reciprocal accounts" v={fmt.n(c.data.engagers.reciprocal_accounts)} n={`${fmt.pct(c.data.engagers.reciprocal_share_of_engagements)} of engagements`} />
          </div>
          <table className="tbl">
            <thead><tr><th>Account</th><th className="num">Engagements</th><th>Account also comments on them</th></tr></thead>
            <tbody>{c.data.engagers.top.map((e: any) => (
              <tr key={e.handle}><td>@{e.handle}</td><td className="num">{e.engagements}</td><td>{e.account_comments_on_them ? "yes (reciprocal)" : ""}</td></tr>
            ))}</tbody>
          </table>
          <p className="mt-2 text-xs muted">{c.data.engagers.note}</p>
        </Panel>
      )}
      <Panel title="Limits">
        <p className="text-xs muted">Private social-graph relationships (follows, mutual follows) are not inferred from public replies.</p>
      </Panel>
    </>
  );
}

function AlgoFindings({ handle, open }: { handle: string; open: (d: Diagnostic) => void }) {
  const diags = useQuery({ queryKey: ["diagnostics", handle], queryFn: () => api.artifact(handle, "diagnostics") });
  if (!diags.data) return <Loading />;
  const used = new Map<string, { f: any; ds: Diagnostic[] }>();
  diags.data.items.forEach((d: Diagnostic) => d.algo_findings.forEach((f) => {
    const e = used.get(f.id) ?? { f, ds: [] };
    e.ds.push(d);
    used.set(f.id, e);
  }));
  return (
    <Panel title="Repository findings connected to this account's diagnostics" right={<NavLink className="btn" to="/algorithm">Full research →</NavLink>}>
      <table className="tbl">
        <thead><tr><th>Finding</th><th>Location (pinned commit)</th><th>Used by</th></tr></thead>
        <tbody>{[...used.values()].map(({ f, ds }) => (
          <tr key={f.id}>
            <td><b>{f.id}</b> {f.title} <ClassBadge c={f.status === "verified" ? "repo_verified" : "hypothesis"} /></td>
            <td><a className="text-blue-600 hover:underline dark:text-blue-400" href={f.permalink} target="_blank" rel="noreferrer">{f.path}:{f.lines[0]}-{f.lines[1]}</a></td>
            <td>{ds.map((d) => <button key={d.id} className="mr-1 underline decoration-dotted" onClick={() => open(d)}>{d.issue}</button>)}</td>
          </tr>
        ))}</tbody>
      </table>
      <p className="mt-2 text-xs muted">A link means “a documented mechanism this could relate to”, not “this mechanism is confirmed to be acting on the account”.</p>
    </Panel>
  );
}

function Blockers({ handle, open }: { handle: string; open: (d: Diagnostic) => void }) {
  const diags = useQuery({ queryKey: ["diagnostics", handle], queryFn: () => api.artifact(handle, "diagnostics") });
  if (!diags.data) return <Loading />;
  return (
    <div className="space-y-3">
      {diags.data.items.map((d: Diagnostic) => (
        <button key={d.id} onClick={() => open(d)} className="panel block w-full text-left hover:border-slate-400">
          <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
            {d.issue}<ClassBadge c={d.evidence_class} /><span className="chip border-slate-400">{d.status}</span><Confidence level={d.confidence} />
            <span className="ml-auto text-xs muted tabular-nums">priority {fmt.r(d.priority)}</span>
          </div>
          <p className="mt-1 text-xs">{d.observation}</p>
          <p className="mt-1 text-xs muted"><b>Recommendation:</b> {d.recommendation}</p>
        </button>
      ))}
    </div>
  );
}

function Benchmarks({ handle }: { handle: string }) {
  const b = useQuery({ queryKey: ["benchmark", handle], queryFn: () => api.artifact(handle, "benchmark") });
  if (!b.data) return <Loading />;
  return (
    <>
      <Panel title={`Peers — authored posts, last ${b.data.window_days} days`} right={<ClassBadge c="statistical_association" />}>
        <div className="overflow-x-auto">
          <table className="tbl">
            <thead><tr><th>Account</th><th className="num">Followers</th><th className="num">Posts/wk</th><th className="num">Median views</th><th className="num">Views/1k followers</th><th className="num">Eng/1k</th><th className="num">Replies/1k</th><th className="num">Bookmarks/1k</th><th className="num">Articles</th></tr></thead>
            <tbody>{Object.entries(b.data.accounts).filter(([, a]: any) => a.n).map(([h, a]: any) => (
              <tr key={h} className={h === handle ? "font-semibold" : ""}>
                <td>@{h}</td><td className="num">{fmt.n(a.followers)}</td><td className="num">{fmt.r(a.authored_per_week, 1)}</td><td className="num">{fmt.n(a.median_views)}</td><td className="num">{fmt.r(a.median_views_per_1k_followers, 1)}</td><td className="num">{fmt.r(a.median_eng_per_1k_views, 1)}</td><td className="num">{fmt.r(a.median_replies_per_1k)}</td><td className="num">{fmt.r(a.median_bookmarks_per_1k)}</td><td className="num">{fmt.pct(a.share_article)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </Panel>
      <Panel title="Client vs peer median">
        <table className="tbl">
          <thead><tr><th>Metric</th><th className="num">Client</th><th className="num">Peer median</th><th className="num">Ratio</th><th className="num">Rank</th></tr></thead>
          <tbody>{b.data.comparison.map((c: any) => (
            <tr key={c.metric}><td>{fmt.label(c.metric)}</td><td className="num">{fmt.r(c.client)}</td><td className="num">{fmt.r(c.peer_median)}</td><td className="num">{fmt.x(c.ratio)}</td><td className="num">{c.client_rank} / {c.of}</td></tr>
          ))}</tbody>
        </table>
        <ul className="mt-2 list-disc pl-5 text-xs muted">{b.data.notes.map((n: string) => <li key={n}>{n}</li>)}</ul>
      </Panel>
      <Panel title="Peer selection">
        <table className="tbl"><thead><tr><th>Peer</th><th className="num">Followers</th><th className="num">Size vs client</th><th className="num">Posts in window</th><th>Included</th></tr></thead>
          <tbody>{b.data.selection.map((s: any) => (
            <tr key={s.peer}><td>@{s.peer}</td><td className="num">{fmt.n(s.followers)}</td><td className="num">{fmt.x(s.size_ratio_vs_client)}</td><td className="num">{s.posts_in_window}</td><td>{s.reason}</td></tr>
          ))}</tbody></table>
      </Panel>
    </>
  );
}

function Experiments({ handle }: { handle: string }) {
  const r = useQuery({ queryKey: ["recommendations", handle], queryFn: () => api.artifact(handle, "recommendations") });
  if (!r.data) return <Loading />;
  const plan = r.data.plan;
  return (
    <>
      <div className="panel border-amber-300 text-xs">{plan.power.note}</div>
      {[1, 2, 3, 4].map((wk) => (
        <Panel key={wk} title={`Week ${wk}`}>
          <div className="space-y-3">
            {plan.experiments.filter((e: any) => e.week === wk).map((e: any) => (
              <div key={e.id} className="rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
                <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
                  {e.title}
                  {e.underpowered_in_30_days && <span className="chip border-rose-400 text-rose-600">underpowered in 30 days — directional only</span>}
                  {e.diagnostic_confidence && <Confidence level={e.diagnostic_confidence} />}
                </div>
                <dl className="mt-2 grid gap-x-3 gap-y-1 sm:grid-cols-[140px_1fr]">
                  <dt className="muted">Hypothesis</dt><dd>{e.hypothesis}</dd>
                  <dt className="muted">Intervention</dt><dd>{e.intervention}</dd>
                  <dt className="muted">Control</dt><dd>{e.control}</dd>
                  <dt className="muted">Primary metric</dt><dd>{e.primary_metric}</dd>
                  <dt className="muted">Secondary</dt><dd>{e.secondary_metrics.join(", ") || "–"}</dd>
                  <dt className="muted">Sample / period</dt><dd>{e.required_n_per_arm ? `${e.required_n_per_arm} posts per arm` : "n/a"} · {e.minimum_period}{e.weeks_needed_at_current_rate ? ` · ~${e.weeks_needed_at_current_rate} weeks at current rate` : ""}</dd>
                  <dt className="muted">Confounders</dt><dd>{e.confounders.join(", ")}</dd>
                  <dt className="muted">Decision rule</dt><dd>{e.decision_rule}</dd>
                </dl>
              </div>
            ))}
          </div>
        </Panel>
      ))}
      <Panel title="Post rewrites to test">
        <div className="space-y-4">
          {r.data.rewrites.map((w: any, i: number) => (
            <div key={w.tweet_id} className="rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
              <div className="font-semibold">{i + 1}. {fmt.label(w.format)} · {w.created_at} · {fmt.n(w.views)} views ({fmt.x(w.vs_baseline)} baseline)</div>
              <div className="mt-2 grid gap-3 md:grid-cols-2">
                <div><div className="muted mb-1">Original</div><p className="whitespace-pre-wrap rounded bg-slate-100 p-2 dark:bg-slate-800"><a href={w.url} target="_blank" rel="noreferrer">{w.text}</a></p></div>
                <div><div className="muted mb-1">Rewrite (editorial proposal)</div><p className="whitespace-pre-wrap rounded bg-blue-50 p-2 dark:bg-blue-950/50">{w.rewrite ?? "not drafted yet"}</p></div>
              </div>
              {w.rewrite && (
                <dl className="mt-2 grid gap-x-3 gap-y-1 sm:grid-cols-[140px_1fr]">
                  <dt className="muted">Observed issue</dt><dd>{w.observed_issue}</dd>
                  <dt className="muted">Can conclude</dt><dd>{w.can_conclude}</dd>
                  <dt className="muted">Cannot conclude</dt><dd>{w.cannot_conclude}</dd>
                  <dt className="muted">Changes</dt><dd><ul className="list-disc pl-4">{(w.editorial_changes ?? []).map((c: string) => <li key={c}>{c}</li>)}</ul></dd>
                  <dt className="muted">Test</dt><dd>{w.test}</dd>
                </dl>
              )}
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs muted">{r.data.rewrites[0]?.disclaimer}</p>
      </Panel>
    </>
  );
}

function Results() {
  return (
    <Panel title="Experiment results">
      <p className="text-sm">No experiment has run yet. Results appear here once Phase 2 monitoring records post-level metric snapshots
        and each experiment's arm assignment; every result will be judged against the decision rule set in the plan.</p>
    </Panel>
  );
}

function DataSection({ completeness }: { completeness: any }) {
  return (
    <>
      <Panel title="Data completeness and confidence">
        <table className="tbl">
          <thead><tr><th>Data</th><th>Status</th><th>Detail</th></tr></thead>
          <tbody>{completeness.items.map((i: any) => (
            <tr key={i.item}><td>{i.item}</td><td><Completeness status={i.status} /></td><td>{i.detail}</td></tr>
          ))}</tbody>
        </table>
      </Panel>
      <Panel title="Collection log">
        <table className="tbl">
          <thead><tr><th>Actor</th><th>Source</th><th>Status</th><th className="num">Items</th><th>Coverage</th><th>Started</th></tr></thead>
          <tbody>{completeness.collection_runs.map((r: any, i: number) => (
            <tr key={i}><td>{r.actor}</td><td>{r.source}</td><td>{r.status}</td><td className="num">{r.items}</td><td>{r.coverage}</td><td>{r.started_at?.slice(0, 16)}</td></tr>
          ))}</tbody>
        </table>
      </Panel>
    </>
  );
}
