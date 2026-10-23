"""Load posts with their latest metric observation into a DataFrame."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from xaudit.db.session import engine
from xaudit.settings import analysis_cfg

METRICS = ["likes", "replies", "reposts", "quotes", "bookmarks", "views"]

_SQL = """
WITH latest AS (
  SELECT m.*, ROW_NUMBER() OVER (PARTITION BY m.tweet_id ORDER BY m.observed_at DESC) AS rn
  FROM post_metric_obs m
)
SELECT p.tweet_id, p.handle, p.created_at, p.text, p.lang, p.url, p.post_type, p.is_long_form,
       p.article_title, p.parent_author, p.parent_tweet_id, p.parent_source,
       l.observed_at, l.observed_at_is_import_time, l.likes, l.replies, l.reposts, l.quotes,
       l.bookmarks, l.views, l.source AS metric_source
FROM posts p JOIN latest l ON l.tweet_id = p.tweet_id AND l.rn = 1
WHERE p.handle IN :handles
"""


def load_posts(handles: list[str] | str, window_days: int | None = None) -> pd.DataFrame:
    handles = [handles] if isinstance(handles, str) else handles
    from sqlalchemy import bindparam

    stmt = text(_SQL).bindparams(bindparam("handles", expanding=True))
    with engine().connect() as con:
        df = pd.read_sql(stmt, con, params={"handles": handles})
    if df.empty:
        return df
    df["created_at"] = pd.to_datetime(df["created_at"], format="ISO8601", utc=True)
    df["observed_at"] = pd.to_datetime(df["observed_at"], format="ISO8601", utc=True)
    if window_days:
        cutoff = df["observed_at"].max() - pd.Timedelta(days=window_days)
        df = df[df["created_at"] >= cutoff]
    df["age_hours_at_obs"] = (df["observed_at"] - df["created_at"]).dt.total_seconds() / 3600
    df["mature"] = df["age_hours_at_obs"] >= analysis_cfg()["min_post_age_hours"]
    df["is_self_reply"] = (df["post_type"] == "reply") & (df["parent_author"] == df["handle"])
    # "authored" = content the account published as its own post (originals + quotes).
    df["is_authored"] = df["post_type"].isin(["original", "quote"])
    df["is_external_reply"] = (df["post_type"] == "reply") & ~df["is_self_reply"]
    for m in METRICS:
        df[m] = pd.to_numeric(df[m], errors="coerce")
    return df.sort_values("created_at").reset_index(drop=True)
