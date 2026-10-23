"""Reach analysis: distributions, baselines, trends.

"Views" are X's public view counts as stored by the console. They are a proxy
for impressions; private impression analytics are not available.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from xaudit.analysis.stats import robust_summary, theil_sen_trend
from xaudit.settings import analysis_cfg

SEGMENTS = {
    "authored (original + quote)": "is_authored",
    "original": None,
    "quote": None,
    "reply to others": "is_external_reply",
    "self-reply (thread)": "is_self_reply",
}


def _segment(df: pd.DataFrame, name: str) -> pd.DataFrame:
    col = SEGMENTS[name]
    if col:
        return df[df[col]]
    return df[df["post_type"] == name]


def add_baseline(df: pd.DataFrame, window_days: int = 28) -> pd.DataFrame:
    """Each authored post's views relative to the median of the account's previous
    authored posts in the trailing window (excluding itself). Requires >= 5 prior posts."""
    df = df.copy()
    df["baseline_views"] = np.nan
    df["vs_baseline"] = np.nan
    a = df[df["is_authored"] & df["mature"] & df["views"].notna()].sort_values("created_at")
    for _handle, g in a.groupby("handle"):
        ts = g["created_at"].to_numpy()
        vs = g["views"].to_numpy(dtype=float)
        for i, idx in enumerate(g.index):
            lo = ts[i] - np.timedelta64(window_days, "D")
            prior = vs[:i][ts[:i] >= lo]
            if prior.size >= 5:
                b = float(np.median(prior))
                df.at[idx, "baseline_views"] = b
                df.at[idx, "vs_baseline"] = vs[i] / b if b > 0 else np.nan
    return df


def reach_report(df: pd.DataFrame, followers: int | None) -> dict:
    cfg = analysis_cfg()
    mature = df[df["mature"]]
    out: dict = {"segments": {}, "followers_used": followers}
    for name in SEGMENTS:
        seg = _segment(mature, name)
        s = robust_summary(seg["views"])
        if followers and s.get("n"):
            s["median_views_per_follower"] = s["median"] / followers
        s["null_views"] = int(seg["views"].isna().sum())
        out["segments"][name] = s

    a = mature[mature["is_authored"] & mature["views"].notna()]
    if len(a):
        v = a["views"].sort_values(ascending=False)
        k = max(1, int(round(len(v) * 0.05)))
        out["concentration"] = {
            "top5pct_posts": k,
            "top5pct_share_of_views": float(v.head(k).sum() / v.sum()) if v.sum() else None,
            "top1_share_of_views": float(v.head(1).sum() / v.sum()) if v.sum() else None,
        }
        rel = a["vs_baseline"].dropna()
        out["vs_baseline"] = {
            "n_with_baseline": int(rel.size),
            "share_above_2x": float((rel >= cfg["above_baseline_multiple"]).mean()) if rel.size else None,
            "share_below_half": float((rel <= cfg["below_baseline_multiple"]).mean()) if rel.size else None,
            "share_above_1x": float((rel > 1).mean()) if rel.size else None,
        }
        t0 = a["created_at"].min()
        out["trend_authored"] = theil_sen_trend((a["created_at"] - t0).dt.total_seconds() / 86400, a["views"])
        r = mature[mature["is_external_reply"] & mature["views"].notna()]
        if len(r) >= 8:
            out["trend_replies"] = theil_sen_trend(
                (r["created_at"] - r["created_at"].min()).dt.total_seconds() / 86400, r["views"])

    def by(period: str) -> list[dict]:
        rows = []
        for key, g in mature.groupby(period):
            ga, gr = g[g["is_authored"]], g[g["is_external_reply"]]
            rows.append({
                period: key,
                "authored_n": int(len(ga)),
                "authored_median_views": float(ga["views"].median()) if len(ga) else None,
                "authored_total_views": float(ga["views"].sum()) if len(ga) else 0.0,
                "replies_n": int(len(gr)),
                "reply_median_views": float(gr["views"].median()) if len(gr) else None,
                "reply_total_views": float(gr["views"].sum()) if len(gr) else 0.0,
            })
        return rows

    out["weekly"] = by("week")
    out["monthly"] = by("month")
    out["immature_excluded"] = int((~df["mature"]).sum())
    return out


def post_table(df: pd.DataFrame) -> list[dict]:
    """Compact per-post rows for the API / CSV (authored + replies)."""
    cols = ["tweet_id", "url", "created_at", "post_type", "format", "text", "views", "likes", "replies",
            "reposts", "quotes", "bookmarks", "vs_baseline", "baseline_views", "mature", "parent_author",
            "topic", "subtopic", "hook_type", "narrative", "category", "length_bucket", "has_tco_url",
            "weekday", "daypart_utc", "label_method", "eng_per_1k", "quadrant"]
    keep = [c for c in cols if c in df.columns]
    d = df[keep].copy()
    d["created_at"] = d["created_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return [{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in r.items()}
            for r in d.to_dict("records")]
