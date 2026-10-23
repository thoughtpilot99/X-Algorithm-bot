"""Write normalised records with deduplication and a collection log."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from xaudit.db.models import Account, CollectionRun, Post, PostMetricObs, utcnow
from xaudit.ingest.normalize import normalize


def ensure_account(s: Session, handle: str, **fields) -> Account:  # noqa: ANN003
    acc = s.get(Account, handle)
    if acc is None:
        acc = Account(handle=handle, **fields)
        s.add(acc)
    else:
        for k, v in fields.items():
            if v is not None:
                setattr(acc, k, v)
    return acc


def upsert_records(
    s: Session,
    records: Iterable[dict],
    *,
    source: str,
    observed_at: datetime | None = None,
    observed_at_is_import_time: bool = True,
) -> tuple[int, int]:
    """Insert posts (first sighting wins for text) and append a metric observation.

    Returns (records_seen, new_posts).
    """
    observed_at = observed_at or utcnow()
    seen = new = 0
    existing_obs = set(
        s.execute(
            select(PostMetricObs.tweet_id).where(
                PostMetricObs.observed_at == observed_at, PostMetricObs.source == source
            )
        ).scalars()
    )
    for rec in records:
        post, m = normalize(rec)
        seen += 1
        row = s.get(Post, post.tweet_id)
        if row is None:
            s.add(Post(**post.__dict__, source=source))
            new += 1
        else:
            # Fill gaps from richer sources without clobbering known values.
            for k in ("parent_tweet_id", "conversation_id"):
                if getattr(row, k) is None and getattr(post, k) is not None:
                    setattr(row, k, getattr(post, k))
            if post.parent_source == "source" and row.parent_source != "source":
                row.parent_author, row.parent_source = post.parent_author, post.parent_source
        if post.tweet_id in existing_obs:
            continue
        existing_obs.add(post.tweet_id)
        s.add(
            PostMetricObs(
                tweet_id=post.tweet_id,
                observed_at=observed_at,
                observed_at_is_import_time=observed_at_is_import_time,
                likes=m.likes,
                replies=m.replies,
                reposts=m.reposts,
                quotes=m.quotes,
                bookmarks=m.bookmarks,
                views=m.views,
                source=source,
            )
        )
    return seen, new


def log_run(s: Session, *, source: str, actor: str, params: dict) -> CollectionRun:
    run = CollectionRun(source=source, actor=actor, params=params)
    s.add(run)
    s.flush()
    return run


def finish_run(run: CollectionRun, *, status: str, items: int = 0, new_items: int = 0,
               coverage: str | None = None, error: str | None = None) -> None:
    run.status = status
    run.items = items
    run.new_items = new_items
    run.coverage = coverage
    run.error = error
    run.finished_at = utcnow()
