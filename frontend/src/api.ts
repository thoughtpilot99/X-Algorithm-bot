// Thin typed client over the read-only audit API.
/* eslint-disable @typescript-eslint/no-explicit-any */

export type EvidenceClass =
  | "repo_verified"
  | "account_observed"
  | "statistical_association"
  | "hypothesis"
  | "unsupported"
  | "insufficient";

export interface Evidence {
  kind: string;
  ref: string;
  label: string;
  value: number | string | null;
  url: string | null;
  evidence_class: EvidenceClass;
}

export interface FindingRef {
  id: string;
  title: string;
  path: string;
  lines: [number, number];
  permalink: string;
  status: string;
}

export interface Diagnostic {
  id: string;
  issue: string;
  status: string;
  observation: string;
  evidence: Evidence[];
  algo_links: string[];
  algo_findings: FindingRef[];
  algo_connection: string;
  alternatives: string[];
  confidence: string;
  impact: string;
  recommendation: string;
  validation: string;
  evidence_class: EvidenceClass;
  priority: number;
  success_criteria: string;
  confounders: string[];
  example_posts: string[];
  rank?: number;
}

export interface Post {
  tweet_id: string;
  url: string;
  created_at: string;
  post_type: string;
  format: string;
  text: string;
  views: number | null;
  likes: number | null;
  replies: number | null;
  reposts: number | null;
  quotes: number | null;
  bookmarks: number | null;
  vs_baseline: number | null;
  baseline_views: number | null;
  mature: boolean;
  parent_author: string | null;
  topic: string | null;
  subtopic: string | null;
  hook_type: string | null;
  category: string | null;
  eng_per_1k: number | null;
  quadrant: string | null;
  label_method: string | null;
}

export interface Account {
  handle: string;
  name: string;
  company: string;
  followers: number | null;
  window: [string, string];
  authored_median_views: number | null;
  peers: string[];
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export const api = {
  accounts: () => get<Account[]>("/api/accounts"),
  overview: (h: string) => get<any>(`/api/accounts/${h}/overview`),
  artifact: <T = any>(h: string, kind: string) => get<T>(`/api/accounts/${h}/artifacts/${kind}`),
  posts: (h: string) => get<{ total: number; items: Post[] }>(`/api/accounts/${h}/posts?limit=5000`),
  answers: (h: string) => get<{ q: string; a: string; class: EvidenceClass }[]>(`/api/accounts/${h}/answers`),
  comparison: () => get<any>("/api/comparison"),
  findings: () => get<any[]>("/api/algo/findings"),
  claims: () => get<any[]>("/api/algo/claims"),
  params: (name?: string) => get<any>(`/api/algo/params${name ? `?name=${encodeURIComponent(name)}` : ""}`),
  search: (q: string) => get<any[]>(`/api/algo/search?q=${encodeURIComponent(q)}`),
  alerts: (h: string) => get<any[]>(`/api/accounts/${h}/alerts`),
  experiments: (h: string) => get<any[]>(`/api/accounts/${h}/experiments`),
  followers: (h: string) => get<{ day: string; followers: number }[]>(`/api/accounts/${h}/timeseries/followers`),
  curve: (id: string) => get<any[]>(`/api/posts/${id}/curve`),
  monitor: () => get<any>("/api/monitor"),
  reports: () => get<{ name: string; url: string; bytes: number }[]>("/api/reports"),
};
