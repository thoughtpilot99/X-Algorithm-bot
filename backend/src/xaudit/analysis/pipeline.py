"""Run every analysis engine for each client and persist the results as artifacts."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import select

from xaudit.analysis import cadence, classify, engagement, reach, segments
from xaudit.analysis.dataset import load_posts
from xaudit.analysis.features import add_features
from xaudit.benchmark.peers import benchmark
from xaudit.comments.intelligence import comment_report
from xaudit.db.models import AccountSnapshot, CollectionRun, Engager, ReplyThread
from xaudit.db.session import engine, save_artifact, session
from xaudit.settings import analysis_cfg, clients


def latest_followers() -> dict[str, int]:
    with session() as s:
        rows = s.execute(select(AccountSnapshot.handle, AccountSnapshot.followers_count,
                                AccountSnapshot.observed_at).order_by(AccountSnapshot.observed_at)).all()
    return {h: f for h, f, _ in rows if f is not None}


def follower_snapshots(handle: str) -> list[dict]:
    with session() as s:
        rows = s.execute(select(AccountSnapshot).where(AccountSnapshot.handle == handle)
                         .order_by(AccountSnapshot.observed_at)).scalars().all()
        return [{"observed_at": r.observed_at.isoformat(), "followers": r.followers_count,
                 "following": r.following_count, "verified": r.verified, "source": r.source} for r in rows]


def _merge_labels(df: pd.DataFrame) -> pd.DataFrame:
    content = classify.labels_frame("content")
    replies = classify.labels_frame("reply")
    if not content.empty:
        c = content.add_prefix("c_").rename(columns={"c_tweet_id": "tweet_id"})
        df = df.merge(c, on="tweet_id", how="left")
    if not replies.empty:
        r = replies.add_prefix("r_").rename(columns={"r_tweet_id": "tweet_id"})
        df = df.merge(r, on="tweet_id", how="left")
    for col in ("topic", "label_method"):
        cc, rc = f"c_{col}", f"r_{col}"
        df[col] = df[cc] if cc in df else None
        if rc in df:
            df[col] = df[col].where(df[col].notna(), df[rc])
    for col in ("subtopic", "hook_type", "narrative", "uses_data", "personal_experience", "opinion_strength",
                "educational_value", "promotional"):
        if f"c_{col}" in df:
            df[col] = df[f"c_{col}"]
    for col in ("category", "relevant_to_icp", "substantive"):
        if f"r_{col}" in df:
            df[col] = df[f"r_{col}"]
    df = df.drop(columns=[c for c in df.columns if c.startswith(("c_", "r_"))])
    for col in ("topic", "subtopic", "hook_type", "narrative", "category", "relevant_to_icp", "uses_data",
                "personal_experience", "promotional", "opinion_strength", "educational_value", "label_method"):
        if col not in df:
            df[col] = None
    return df


def _merge_threads(df: pd.DataFrame) -> pd.DataFrame:
    with engine().connect() as con:
        t = pd.read_sql(select(ReplyThread), con)
    if t.empty:
        return df
    t = t[["tweet_id", "latency_minutes", "parent_author_responded", "others_responded", "parent_views",
           "parent_likes", "parent_replies", "parent_text", "parent_created_at"]]
    return df.merge(t, on="tweet_id", how="left")


def prepare(handle: str, window_days: int | None = None, label_missing: bool = False) -> pd.DataFrame:
    """Posts + features + labels + thread context + baselines + rates for one account.

    ``label_missing`` labels any post without a current label first (Claude when
    ANTHROPIC_API_KEY is set, heuristics otherwise); cached labels are reused.
    """
    df = load_posts(handle, window_days=window_days)
    if df.empty:
        return df
    df = add_features(df)
    if label_missing:
        c = clients().get(handle, {})
        classify.classify(df, context=f"{c.get('name', handle)}: {c.get('positioning_hint', '')}")
    df = _merge_labels(df)
    df = _merge_threads(df)
    df = reach.add_baseline(df)
    df = engagement.add_rates(df)
    df = engagement.add_quadrant(df)
    return df


def completeness(handle: str, df: pd.DataFrame) -> dict:
    with session() as s:
        runs = s.execute(select(CollectionRun).order_by(CollectionRun.started_at.desc())).scalars().all()
        n_eng = len(s.execute(select(Engager.id).where(Engager.client_handle == handle)).all())
        n_threads = len(s.execute(select(ReplyThread.tweet_id)).all())
    ext = df[df["is_external_reply"]]
    conv = df[df["reply_role"] == "conversation"]
    lm = df["label_method"].fillna("none").value_counts().to_dict()
    items = [
        {"item": "Posts, replies, quotes, reposts (180 days)", "status": "available",
         "detail": f"{len(df)} records from the ThoughtPilot console store"},
        {"item": "Views (public view count)", "status": "available",
         "detail": f"{int(df['views'].notna().sum())} of {len(df)} records have views"},
        {"item": "Likes, replies, reposts, quotes, bookmarks", "status": "available", "detail": "public counts"},
        {"item": "Metric scrape time", "status": "partial",
         "detail": "the store does not record when metrics were scraped; observations are stamped at import "
                   "time. Spot-check vs an August scrape: stored views were equal or higher for overlapping "
                   "posts (metrics are refreshed, not frozen)."},
        {"item": "Engagement over time per post", "status": "unavailable",
         "detail": "one observation per post; monitoring (Phase 2) builds the time series"},
        {"item": "Follower count", "status": "partial",
         "detail": "single snapshot on 2026-10-23; no historical follower growth"},
        {"item": "Profile bio / account creation date", "status": "unavailable",
         "detail": "user-info returned no description or creation date"},
        {"item": "Media type (image/video)", "status": "unavailable",
         "detail": "not in source records; t.co URLs may be links or media"},
        {"item": "Profile visits, follows, link clicks, audience demographics", "status": "unavailable",
         "detail": "private analytics; this audit uses public data only (by decision)"},
        {"item": "Reply parent author", "status": "inferred",
         "detail": f"from leading @mention for {int((ext['parent_source'] == 'inferred_leading_mention').sum())} "
                   f"replies; confirmed by tweet-detail for {int((ext['parent_source'] == 'tweet_detail').sum())}"},
        {"item": "Reply parent post (time, text, engagement)", "status": "sample",
         "detail": f"tweet-detail collected for {n_threads} replies across clients (most recent conversational "
                   f"comments); {len(conv)} conversational comments in total for this account"},
        {"item": "Who engaged with the account's posts", "status": "available" if n_eng else "unavailable",
         "detail": f"{n_eng} public replies/quotes by others (client-engagers); likes are not exposed"},
        {"item": "Content/reply labels", "status": "available", "detail": f"label methods: {lm}"},
        {"item": "Immature posts (<72h old at observation)", "status": "excluded from baselines",
         "detail": f"{int((~df['mature']).sum())} posts"},
    ]
    return {"items": items, "collection_runs": [
        {"actor": r.actor, "source": r.source, "status": r.status, "items": r.items,
         "started_at": r.started_at.isoformat() if r.started_at else None, "coverage": r.coverage}
        for r in runs[:30]]}


def _jsonable(o):  # noqa: ANN001, ANN202
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    return o


def run(handles: list[str] | None = None) -> dict:
    cfg = clients()
    handles = handles or list(cfg)
    followers = latest_followers()
    summary = {}
    for h in handles:
        df = prepare(h, window_days=analysis_cfg()["extended_window_days"], label_missing=True)
        if df.empty:
            summary[h] = "no data"
            continue
        f = followers.get(h)
        last90 = df[df["created_at"] >= df["observed_at"].max() - pd.Timedelta(days=90)]
        arts = {
            "profile": {"handle": h, **cfg[h], "followers": f, "snapshots": follower_snapshots(h),
                        "window": [df["created_at"].min().isoformat(), df["created_at"].max().isoformat()],
                        "counts": df["post_type"].value_counts().to_dict(),
                        "reply_roles": df["reply_role"].value_counts().to_dict()},
            "reach": reach.reach_report(df, f),
            "reach_90d": reach.reach_report(last90, f),
            "engagement": engagement.engagement_report(df),
            "segments": segments.univariate(df),
            "multivariable": segments.multivariable(df),
            "strong_weak": segments.strong_weak_profile(df),
            "cadence": cadence.cadence_report(df),
            "comments": comment_report(df, h, followers, peers=list(cfg) + cfg[h].get("peers", [])),
            "posts": reach.post_table(df),
            "benchmark": benchmark(h, followers),
            "completeness": completeness(h, df),
        }
        for kind, payload in arts.items():
            save_artifact(kind, _jsonable(payload), h)
        summary[h] = {"posts": len(df), "artifacts": list(arts)}
    return summary
