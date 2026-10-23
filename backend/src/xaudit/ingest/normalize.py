"""One normaliser for every source of console-shaped tweet records.

The ThoughtPilot console returns the same record shape from its job results
and from its stored-tweet query (and therefore from the Xplatfrom MCP tools):

    tweet_id, url, username, user_id, created_at, text, lang,
    like_count, reply_count, retweet_count, quote_count, bookmark_count,
    view_count, is_reply, is_quote, is_retweet, is_long_form, article_title

It does not return the parent post id, conversation id or media type. Where a
reply's parent author is needed, it is inferred from the text and the
inference is recorded in ``parent_source`` so reports can say so.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

LEADING_MENTIONS = re.compile(r"^((?:@\w{1,15}\s+)+)")


@dataclass(frozen=True)
class NormalizedPost:
    tweet_id: str
    handle: str
    user_id: str | None
    created_at: datetime
    text: str
    lang: str | None
    url: str | None
    post_type: str
    is_long_form: bool
    article_title: str | None
    parent_author: str | None
    parent_tweet_id: str | None
    parent_source: str | None
    conversation_id: str | None


@dataclass(frozen=True)
class NormalizedMetrics:
    tweet_id: str
    likes: int | None
    replies: int | None
    reposts: int | None
    quotes: int | None
    bookmarks: int | None
    views: int | None


def parse_ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def classify_type(rec: dict) -> str:
    if rec.get("is_retweet"):
        return "repost"
    if rec.get("is_reply"):
        return "reply"
    if rec.get("is_quote"):
        return "quote"
    return "original"


def leading_mentions(text: str) -> list[str]:
    m = LEADING_MENTIONS.match(text or "")
    if not m:
        return []
    return [h.lstrip("@") for h in m.group(1).split()]


def infer_parent(rec: dict, handle: str) -> tuple[str | None, str | None]:
    """Best available parent author for a reply, and how it was obtained.

    - explicit field from the source, when present  -> "source"
    - first leading @mention                         -> "inferred_leading_mention"
    - reply with no leading mention                  -> the author themself,
      "inferred_self_thread" (X omits the self-mention in thread continuations)
    """
    if not rec.get("is_reply"):
        return None, None
    explicit = rec.get("in_reply_to_username") or rec.get("parent_author")
    if explicit:
        return str(explicit), "source"
    mentions = leading_mentions(rec.get("text", ""))
    if mentions:
        return mentions[0], "inferred_leading_mention"
    return handle, "inferred_self_thread"


def _int(v) -> int | None:  # noqa: ANN001
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def normalize(rec: dict) -> tuple[NormalizedPost, NormalizedMetrics]:
    handle = rec.get("username") or ""
    parent_author, parent_source = infer_parent(rec, handle)
    tid = str(rec["tweet_id"])
    post = NormalizedPost(
        tweet_id=tid,
        handle=handle,
        user_id=str(rec["user_id"]) if rec.get("user_id") else None,
        created_at=parse_ts(rec["created_at"]),
        text=rec.get("text") or "",
        lang=rec.get("lang"),
        url=rec.get("url") or (f"https://x.com/{handle}/status/{tid}" if handle else None),
        post_type=classify_type(rec),
        is_long_form=bool(rec.get("is_long_form")),
        article_title=rec.get("article_title"),
        parent_author=parent_author,
        parent_tweet_id=rec.get("in_reply_to_tweet_id") or rec.get("parent_tweet_id"),
        parent_source=parent_source,
        conversation_id=rec.get("conversation_id"),
    )
    metrics = NormalizedMetrics(
        tweet_id=tid,
        likes=_int(rec.get("like_count")),
        replies=_int(rec.get("reply_count")),
        reposts=_int(rec.get("retweet_count")),
        quotes=_int(rec.get("quote_count")),
        bookmarks=_int(rec.get("bookmark_count")),
        views=_int(rec.get("view_count")),
    )
    return post, metrics
