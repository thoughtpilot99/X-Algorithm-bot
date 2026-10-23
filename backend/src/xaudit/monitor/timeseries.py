"""Metric time series built from repeated observations (one row per collection)."""

from __future__ import annotations

from datetime import UTC

import numpy as np
import pandas as pd
from sqlalchemy import select

from xaudit.db.models import AccountSnapshot, Post, PostMetricObs
from xaudit.db.session import engine, session


def _utc(dt):  # noqa: ANN001, ANN202
    """SQLite drops tzinfo; every stored timestamp is UTC."""
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=UTC)


def post_curve(tweet_id: str) -> list[dict]:
    with session() as s:
        post = s.get(Post, tweet_id)
        if post is None:
            return []
        obs = s.execute(select(PostMetricObs).where(PostMetricObs.tweet_id == tweet_id)
                        .order_by(PostMetricObs.observed_at)).scalars().all()
        return [{"observed_at": _utc(o.observed_at).isoformat(),
                 "age_hours": round((_utc(o.observed_at) - _utc(post.created_at)).total_seconds() / 3600, 1),
                 "views": o.views, "likes": o.likes, "replies": o.replies, "bookmarks": o.bookmarks,
                 "import_time": o.observed_at_is_import_time, "source": o.source} for o in obs]


def views_at_age(hours: float = 72) -> pd.DataFrame:
    """Views interpolated at a fixed post age, for posts whose observations bracket that age.

    Only observations with a real scrape time are used (import-time stamps are excluded).
    """
    q = (select(PostMetricObs.tweet_id, PostMetricObs.observed_at, PostMetricObs.views, Post.created_at)
         .join(Post, Post.tweet_id == PostMetricObs.tweet_id)
         .where(PostMetricObs.observed_at_is_import_time.is_(False), PostMetricObs.views.is_not(None)))
    with engine().connect() as con:
        df = pd.read_sql(q, con)
    if df.empty:
        return pd.DataFrame(columns=["tweet_id", f"views_{int(hours)}h"])
    df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True, format="ISO8601")
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, format="ISO8601")
    df["age"] = (df["observed_at"] - df["created_at"]).dt.total_seconds() / 3600
    out = []
    for tid, g in df.sort_values("age").groupby("tweet_id"):
        ages, views = g["age"].to_numpy(), g["views"].to_numpy(dtype=float)
        if ages.min() <= hours <= ages.max() and len(ages) >= 2:
            out.append({"tweet_id": tid, f"views_{int(hours)}h": float(np.interp(hours, ages, views))})
    return pd.DataFrame(out, columns=["tweet_id", f"views_{int(hours)}h"])


def follower_series(handle: str) -> list[dict]:
    with session() as s:
        rows = s.execute(select(AccountSnapshot.observed_at, AccountSnapshot.followers_count)
                         .where(AccountSnapshot.handle == handle, AccountSnapshot.followers_count.is_not(None))
                         .order_by(AccountSnapshot.observed_at)).all()
    # One point per day (latest observation that day).
    by_day: dict[str, int] = {}
    for t, f in rows:
        by_day[t.date().isoformat()] = f
    return [{"day": d, "followers": f} for d, f in sorted(by_day.items())]
