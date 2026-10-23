"""Import console-shaped JSON files (e.g. exported through the Xplatfrom MCP).

Layout under ``data/raw/console``::

    <client_handle>/page_*.json     a client's own timeline (posts + replies)
    peers/<peer_handle>.json        a peer's original posts
    profiles/*.json                 user-info results (list of profiles)

The files are verbatim copies of the console's ``items`` arrays. The scrape time
of their metrics is not in the record, so observations are stamped with the
file's modification time and flagged ``observed_at_is_import_time``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from xaudit.db.models import AccountSnapshot, Engager, Post, ReplyThread
from xaudit.db.session import session
from xaudit.ingest.normalize import parse_ts
from xaudit.ingest.store import ensure_account, finish_run, log_run, upsert_records
from xaudit.settings import RAW_DIR, clients

SOURCE = "console_store"


def _mtime(p: Path) -> datetime:
    return datetime.fromtimestamp(p.stat().st_mtime, tz=UTC).replace(microsecond=0)


def _load(p: Path) -> list[dict]:
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("items", [])


def import_seed(root: Path | None = None) -> dict:
    root = root or (RAW_DIR / "console")
    summary: dict[str, dict] = {}
    cfg = clients()
    with session() as s:
        for handle, c in cfg.items():
            ensure_account(s, handle, user_id=c.get("user_id"), name=c.get("name"),
                           role="client", company=c.get("company"))
            for peer in c.get("peers", []):
                ensure_account(s, peer, role="peer", client_of=handle)

        for handle in cfg:
            files = sorted((root / handle).glob("*.json"))
            if not files:
                continue
            run = log_run(s, source=SOURCE, actor="seed-import",
                          params={"handle": handle, "files": [f.name for f in files]})
            seen = new = 0
            # One observation time per import so repeated imports form a series.
            obs = max(_mtime(f) for f in files)
            for f in files:
                a, b = upsert_records(s, _load(f), source=SOURCE, observed_at=obs)
                seen, new = seen + a, new + b
            finish_run(run, status="succeeded", items=seen, new_items=new, coverage="seed")
            summary[handle] = {"records": seen, "new_posts": new}

        for f in sorted((root / "peers").glob("*.json")):
            recs = _load(f)
            run = log_run(s, source=SOURCE, actor="seed-import", params={"peer_file": f.name})
            a, b = upsert_records(s, recs, source=SOURCE, observed_at=_mtime(f))
            finish_run(run, status="succeeded", items=a, new_items=b, coverage="seed")
            summary[f.stem] = {"records": a, "new_posts": b}

        for f in sorted((root / "profiles").glob("*.json")):
            for prof in _load(f):
                handle = prof.get("username") or prof.get("screen_name")
                if not handle:
                    continue
                ensure_account(s, handle, user_id=str(prof.get("user_id") or prof.get("id") or "") or None)
                created = prof.get("created_at")
                dup = s.scalar(select(AccountSnapshot.id).where(
                    AccountSnapshot.handle == handle, AccountSnapshot.observed_at == _mtime(f),
                    AccountSnapshot.source == SOURCE))
                if dup:
                    continue
                s.add(AccountSnapshot(
                    handle=handle,
                    observed_at=_mtime(f),
                    followers_count=prof.get("followers_count"),
                    following_count=prof.get("following_count") or prof.get("friends_count"),
                    verified=prof.get("verified") if prof.get("verified") is not None
                    else prof.get("is_blue_verified"),
                    description=prof.get("description") or prof.get("bio"),
                    account_created_at=parse_ts(created) if isinstance(created, str) else None,
                    source=SOURCE,
                    raw=prof,
                ))
        summary["threads"] = import_threads(s, root / "threads")
        summary["engagers"] = import_engagers(s, root / "engagers")
    return summary


def import_threads(s, folder: Path) -> int:  # noqa: ANN001
    """tweet-detail results: <reply_tweet_id>.json holding parent, the reply and replies to it."""
    n = 0
    for f in sorted(folder.glob("[0-9]*.json")):
        focal_id = f.stem
        items = _load(f)
        focal = next((i for i in items if str(i["tweet_id"]) == focal_id), None)
        reply = s.get(Post, focal_id)
        if focal is None or reply is None:
            continue
        t0 = parse_ts(focal["created_at"])
        before = sorted((i for i in items if parse_ts(i["created_at"]) < t0), key=lambda i: i["created_at"])
        parent = next((i for i in reversed(before) if i.get("username") == reply.parent_author), None) \
            or (before[-1] if before else None)
        after = [i for i in items if parse_ts(i["created_at"]) > t0 and i.get("username") != reply.handle]
        p_author = parent.get("username") if parent else reply.parent_author
        row = s.get(ReplyThread, focal_id) or ReplyThread(tweet_id=focal_id, source=SOURCE)
        row.parent_tweet_id = str(parent["tweet_id"]) if parent else None
        row.parent_author = p_author
        row.parent_created_at = parse_ts(parent["created_at"]) if parent else None
        row.parent_text = parent.get("text") if parent else None
        row.parent_views = parent.get("view_count") if parent else None
        row.parent_likes = parent.get("like_count") if parent else None
        row.parent_replies = parent.get("reply_count") if parent else None
        row.latency_minutes = (t0 - row.parent_created_at).total_seconds() / 60 if parent else None
        row.parent_author_responded = any(i.get("username") == p_author for i in after)
        row.others_responded = len({i.get("username") for i in after} - {p_author})
        row.items_seen = len(items)
        row.observed_at = _mtime(f)
        s.merge(row)
        if parent and reply.parent_tweet_id is None:
            reply.parent_tweet_id = str(parent["tweet_id"])
            if parent.get("username"):
                reply.parent_author, reply.parent_source = parent["username"], "tweet_detail"
        n += 1
    return n


def import_engagers(s, folder: Path) -> int:  # noqa: ANN001
    """client-engagers results: replies/quotes other accounts made on a client's posts."""
    n = 0
    for f in sorted(folder.glob("*.json")):
        if f.stem.endswith("_job"):
            continue
        client = f.stem
        for r in _load(f):
            who = r.get("username")
            if not who or who == client or not r.get("tweet_id"):
                continue
            eid = str(r["tweet_id"])
            if s.scalar(select(Engager.id).where(Engager.engagement_tweet_id == eid)):
                continue
            s.add(Engager(
                client_handle=client,
                target_tweet_id=r.get("in_reply_to_tweet_id") or r.get("quoted_tweet_id"),
                engager_handle=who,
                engagement_tweet_id=eid,
                kind="quote" if r.get("is_quote") else "reply",
                created_at=parse_ts(r["created_at"]) if r.get("created_at") else None,
                engager_followers=r.get("author_followers_count") or r.get("followers_count"),
                source=SOURCE,
            ))
            n += 1
    return n
