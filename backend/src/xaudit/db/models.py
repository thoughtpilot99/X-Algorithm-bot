"""Storage schema.

Design rules:
- A post's text/identity lives in ``posts``; its metrics live in ``post_metric_obs``
  as timestamped observations, so history is never overwritten.
- Every row records where it came from (``source``) and when it was observed.
- Derived analysis is stored as JSON ``artifacts`` keyed by (kind, handle) so the
  API and reports read exactly what the engines produced.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    handle: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="peer")  # client | peer
    client_of: Mapped[str | None] = mapped_column(String)  # for peers: which client
    company: Mapped[str | None] = mapped_column(String)


class AccountSnapshot(Base):
    """Profile observation (followers etc.) at a point in time."""

    __tablename__ = "account_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    handle: Mapped[str] = mapped_column(ForeignKey("accounts.handle"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    followers_count: Mapped[int | None] = mapped_column(Integer)
    following_count: Mapped[int | None] = mapped_column(Integer)
    verified: Mapped[bool | None] = mapped_column(Boolean)
    description: Mapped[str | None] = mapped_column(Text)
    account_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String)
    raw: Mapped[dict | None] = mapped_column(JSON)


class Post(Base):
    __tablename__ = "posts"

    tweet_id: Mapped[str] = mapped_column(String, primary_key=True)
    handle: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    lang: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    # original | reply | quote | repost
    post_type: Mapped[str] = mapped_column(String, index=True)
    is_long_form: Mapped[bool] = mapped_column(Boolean, default=False)
    article_title: Mapped[str | None] = mapped_column(String)
    # Reply context. parent_author is derived from the leading @mention when the
    # source does not provide it (parent_source records which).
    parent_author: Mapped[str | None] = mapped_column(String, index=True)
    parent_tweet_id: Mapped[str | None] = mapped_column(String)
    parent_source: Mapped[str | None] = mapped_column(String)
    conversation_id: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PostMetricObs(Base):
    __tablename__ = "post_metric_obs"
    __table_args__ = (UniqueConstraint("tweet_id", "observed_at", "source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tweet_id: Mapped[str] = mapped_column(ForeignKey("posts.tweet_id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # True when observed_at is the import time rather than the scrape time.
    observed_at_is_import_time: Mapped[bool] = mapped_column(Boolean, default=False)
    likes: Mapped[int | None] = mapped_column(Integer)
    replies: Mapped[int | None] = mapped_column(Integer)
    reposts: Mapped[int | None] = mapped_column(Integer)
    quotes: Mapped[int | None] = mapped_column(Integer)
    bookmarks: Mapped[int | None] = mapped_column(Integer)
    views: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String)


class ReplyThread(Base):
    """Context for one of the client's replies, from a tweet-detail scrape."""

    __tablename__ = "reply_threads"

    tweet_id: Mapped[str] = mapped_column(String, primary_key=True)  # the client's reply
    parent_tweet_id: Mapped[str | None] = mapped_column(String)
    parent_author: Mapped[str | None] = mapped_column(String)
    parent_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_text: Mapped[str | None] = mapped_column(Text)
    parent_views: Mapped[int | None] = mapped_column(Integer)
    parent_likes: Mapped[int | None] = mapped_column(Integer)
    parent_replies: Mapped[int | None] = mapped_column(Integer)
    latency_minutes: Mapped[float | None] = mapped_column(Float)
    parent_author_responded: Mapped[bool | None] = mapped_column(Boolean)
    others_responded: Mapped[int | None] = mapped_column(Integer)
    items_seen: Mapped[int] = mapped_column(Integer, default=0)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str] = mapped_column(String)


class PostThread(Base):
    """Replies under one of the client's own posts, from a tweet-detail scrape (conversation depth)."""

    __tablename__ = "post_threads"

    tweet_id: Mapped[str] = mapped_column(String, primary_key=True)  # the client's post
    handle: Mapped[str] = mapped_column(String, index=True)
    items_seen: Mapped[int] = mapped_column(Integer, default=0)
    other_replies: Mapped[int] = mapped_column(Integer, default=0)
    distinct_repliers: Mapped[int] = mapped_column(Integer, default=0)
    author_replies: Mapped[int] = mapped_column(Integer, default=0)
    author_first_reply_minutes: Mapped[float | None] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str] = mapped_column(String)


class Engager(Base):
    """A public reply or quote someone else made on a client's post."""

    __tablename__ = "engagers"
    __table_args__ = (UniqueConstraint("engagement_tweet_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_handle: Mapped[str] = mapped_column(String, index=True)
    target_tweet_id: Mapped[str | None] = mapped_column(String)
    engager_handle: Mapped[str] = mapped_column(String, index=True)
    engagement_tweet_id: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)  # reply | quote
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    engager_followers: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String)


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    params: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, default="running")
    items: Mapped[int] = mapped_column(Integer, default=0)
    new_items: Mapped[int] = mapped_column(Integer, default=0)
    coverage: Mapped[str | None] = mapped_column(String)
    error: Mapped[str | None] = mapped_column(Text)


class Classification(Base):
    """LLM or heuristic labels for a post, cached by text hash."""

    __tablename__ = "classifications"
    __table_args__ = (UniqueConstraint("tweet_id", "kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tweet_id: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[str] = mapped_column(String)  # content | reply
    method: Mapped[str] = mapped_column(String)  # llm:<model> | heuristic:v1
    text_hash: Mapped[str] = mapped_column(String)
    labels: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RepoVersion(Base):
    __tablename__ = "repo_versions"

    sha: Mapped[str] = mapped_column(String, primary_key=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AlgoParam(Base):
    """A published parameter value at a given repository commit."""

    __tablename__ = "algo_params"
    __table_args__ = (UniqueConstraint("sha", "path", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sha: Mapped[str] = mapped_column(String, index=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    path: Mapped[str] = mapped_column(String)
    line: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String, index=True)
    value: Mapped[float | None] = mapped_column(Float)
    raw_value: Mapped[str] = mapped_column(String)
    value_type: Mapped[str | None] = mapped_column(String)


class Artifact(Base):
    """Engine output, stored as JSON for the API and reports."""

    __tablename__ = "artifacts"
    __table_args__ = (UniqueConstraint("kind", "handle"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String, index=True)
    handle: Mapped[str] = mapped_column(String, default="_global")
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
