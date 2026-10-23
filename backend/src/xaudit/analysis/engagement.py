"""Engagement efficiency (per 1,000 views) and the visibility/efficiency quadrant.

These are observed outcome rates. They are not the algorithm's predicted
probabilities and must not be read as ranking scores.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from xaudit.analysis.stats import robust_summary

PUBLIC_RATES = ["likes", "replies", "reposts", "quotes", "bookmarks"]
UNAVAILABLE = {
    "profile_visits_per_1k": "private analytics (account owner export) — not collected",
    "follows_per_1k": "private analytics — not collected",
    "link_clicks_per_1k": "private analytics — not collected",
    "video_watch_metrics": "private analytics; media type also not present in source data",
    "dwell_time": "not exposed publicly at all",
}


def add_rates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    v = df["views"].where(df["views"] > 0)
    for m in PUBLIC_RATES:
        df[f"{m}_per_1k"] = df[m] / v * 1000
    df["eng_per_1k"] = df[PUBLIC_RATES].sum(axis=1, min_count=1) / v * 1000
    return df


def add_quadrant(df: pd.DataFrame) -> pd.DataFrame:
    """Authored posts: reach vs own baseline (x) against engagement rate vs own median (y)."""
    df = df.copy()
    df["quadrant"] = None
    a = df["is_authored"] & df["mature"] & df["vs_baseline"].notna() & df["eng_per_1k"].notna()
    for _handle, g in df[a].groupby("handle"):
        med = g["eng_per_1k"].median()
        for idx, r in g.iterrows():
            hi_reach = r["vs_baseline"] >= 1
            hi_eff = r["eng_per_1k"] >= med
            df.at[idx, "quadrant"] = {
                (True, True): "reach + resonance",
                (True, False): "reach without resonance",
                (False, True): "resonance without reach",
                (False, False): "neither",
            }[(hi_reach, hi_eff)]
    return df


def engagement_report(df: pd.DataFrame) -> dict:
    mature = df[df["mature"] & (df["views"] > 0)]
    out: dict = {"by_type": {}, "unavailable": UNAVAILABLE}
    for name, mask in (("authored", mature["is_authored"]), ("reply to others", mature["is_external_reply"])):
        g = mature[mask]
        out["by_type"][name] = {f"{m}_per_1k": robust_summary(g[f"{m}_per_1k"]) for m in [*PUBLIC_RATES, "eng"]}
        # Pooled rate: total engagements / total views (dominated by high-view posts).
        tv = g["views"].sum()
        out["by_type"][name]["pooled_per_1k"] = {
            m: float(g[m].sum() / tv * 1000) if tv else None for m in PUBLIC_RATES
        }
    q = df["quadrant"].dropna()
    out["quadrants"] = q.value_counts().to_dict()
    out["reply_ratio_authored"] = float(
        np.median((mature.loc[mature["is_authored"], "replies"] /
                   mature.loc[mature["is_authored"], "likes"].replace(0, np.nan)).dropna())
    ) if mature["is_authored"].any() else None
    return out
