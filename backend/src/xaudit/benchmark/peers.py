"""Peer benchmarking, normalised for account size.

Peers are taken from the client's configured sentinel list (accounts.yaml),
which content-agent maintained as the closest comparable voices. Selection
criteria recorded per peer: topic overlap (heuristic topic mix), follower
size ratio and posting activity.

Comparisons use the same slice for client and peers: authored posts
(originals + quotes) in the default window, mature posts only. Peer reply
behaviour was not collected, so reply strategy is not benchmarked.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from xaudit.analysis.classify import heuristic_content
from xaudit.analysis.dataset import load_posts
from xaudit.analysis.engagement import add_rates
from xaudit.analysis.features import add_features
from xaudit.settings import analysis_cfg, clients


def _profile(df: pd.DataFrame, followers: int | None) -> dict:
    a = df[df["is_authored"] & df["mature"] & df["views"].notna()]
    if a.empty:
        return {"n": 0}
    span_weeks = max(1.0, (a["created_at"].max() - a["created_at"].min()).days / 7)
    med = float(a["views"].median())
    topics = a["text"].map(lambda t: heuristic_content(t)["topic"]).value_counts(normalize=True)
    return {
        "n": int(len(a)),
        "followers": followers,
        "authored_per_week": float(len(a) / span_weeks),
        "median_views": med,
        "p90_views": float(a["views"].quantile(0.9)),
        "median_views_per_1k_followers": med / followers * 1000 if followers else None,
        "median_eng_per_1k_views": float(a["eng_per_1k"].median()),
        "median_replies_per_1k": float(a["replies_per_1k"].median()),
        "median_reposts_per_1k": float(a["reposts_per_1k"].median()),
        "median_bookmarks_per_1k": float(a["bookmarks_per_1k"].median()),
        "median_likes_per_1k": float(a["likes_per_1k"].median()),
        "share_long_form": float(a["is_long_form"].mean()),
        "share_article": float(a["article_title"].notna().mean()),
        "share_quote": float((a["post_type"] == "quote").mean()),
        "share_tco_url": float(a["has_tco_url"].mean()),
        "share_list": float(a["has_list"].mean()),
        "median_words": float(a["word_count"].median()),
        "topic_mix_heuristic": topics.round(3).head(5).to_dict(),
        "window": [a["created_at"].min().strftime("%Y-%m-%d"), a["created_at"].max().strftime("%Y-%m-%d")],
    }


def benchmark(handle: str, followers: dict[str, int]) -> dict:
    days = analysis_cfg()["default_window_days"]
    peers = clients()[handle].get("peers", [])
    rows = {}
    for h in [handle, *peers]:
        df = load_posts(h, window_days=days)
        if df.empty:
            rows[h] = {"n": 0, "note": "no stored posts for this account in the window"}
            continue
        df = add_rates(add_features(df))
        rows[h] = _profile(df, followers.get(h))
    client = rows[handle]
    peer_rows = {h: r for h, r in rows.items() if h != handle and r.get("n", 0) >= 10}

    def peer_median(key: str) -> float | None:
        vals = [r[key] for r in peer_rows.values() if r.get(key) is not None]
        return float(np.median(vals)) if vals else None

    keys = ["authored_per_week", "median_views_per_1k_followers", "median_eng_per_1k_views",
            "median_replies_per_1k", "median_reposts_per_1k", "median_bookmarks_per_1k", "median_likes_per_1k",
            "share_long_form", "share_article", "share_tco_url", "share_list", "median_words"]
    comparison = []
    for k in keys:
        pm = peer_median(k)
        cv = client.get(k)
        comparison.append({
            "metric": k, "client": cv, "peer_median": pm,
            "ratio": (cv / pm) if (cv is not None and pm) else None,
            "client_rank": (1 + sum(1 for r in peer_rows.values() if r.get(k) is not None and cv is not None
                                    and r[k] > cv)) if cv is not None else None,
            "of": 1 + sum(1 for r in peer_rows.values() if r.get(k) is not None),
        })
    selection = []
    for h in peers:
        r = rows.get(h, {})
        f = followers.get(h)
        selection.append({
            "peer": h, "followers": f,
            "size_ratio_vs_client": (f / followers[handle]) if (f and followers.get(handle)) else None,
            "posts_in_window": r.get("n", 0),
            "included": h in peer_rows,
            "reason": "configured sentinel peer (content-agent); "
                      + ("included" if h in peer_rows else "excluded: < 10 mature authored posts or no data"),
        })
    return {
        "window_days": days,
        "accounts": rows,
        "comparison": comparison,
        "selection": selection,
        "notes": [
            "Peers: newest <=100 original posts per peer in the window were collected; posting rate is "
            "computed over the span those posts cover.",
            "Size normalisation: views per 1,000 followers uses follower counts observed on the snapshot date, "
            "applied to the whole window (no follower history).",
            "Engagement per 1,000 views is size-independent but depends on audience composition.",
            "Peer reply/comment behaviour was not collected; the commenting audit has no peer benchmark.",
            "Quote-post share is not compared: peers were collected with the console's 'original' filter.",
            "Peer topic mix uses the heuristic labeller (keywords), not the reviewed labels used for clients.",
        ],
    }
