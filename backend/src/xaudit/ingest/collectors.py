"""Live collection through the ThoughtPilot console (requires XP_API_KEY).

Each collector submits a scrape job, waits for it, then reads the shared
dataset store and upserts with a timestamped metric observation. Re-running a
collector therefore builds a metric time series instead of overwriting.

Only public data is collected. Private analytics (profile visits, follows,
link clicks, audience) are not available through this source.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from xaudit.db.models import AccountSnapshot, Engager
from xaudit.db.session import session
from xaudit.ingest.console_client import ConsoleClient, ConsoleError
from xaudit.ingest.normalize import parse_ts
from xaudit.ingest.store import ensure_account, finish_run, log_run, upsert_records
from xaudit.settings import analysis_cfg, clients

SOURCE = "console_live"


def _since(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def collect_timeline(cc: ConsoleClient, handle: str, *, days: int | None = None,
                     include_replies: bool = True, max_pages: int = 50) -> dict:
    days = days or analysis_cfg()["extended_window_days"]
    params = {"username": handle, "since": _since(days), "include_replies": include_replies,
              "max_pages": max_pages, "limit": 5000}
    with session() as s:
        run = log_run(s, source=SOURCE, actor="user-tweets", params=params)
    try:
        job = cc.run("user-tweets", params)
        items = cc.dataset("tweets", username=handle, since=params["since"])
    except ConsoleError as e:
        with session() as s:
            run = s.merge(run)
            finish_run(run, status="failed", error=str(e))
        return {"handle": handle, "status": "failed", "error": str(e)}
    now = datetime.now(UTC).replace(microsecond=0)
    with session() as s:
        seen, new = upsert_records(s, items, source=SOURCE, observed_at=now,
                                   observed_at_is_import_time=False)
        run = s.merge(run)
        finish_run(run, status=job.status, items=seen, new_items=new, coverage=job.coverage,
                   error=job.error)
    return {"handle": handle, "status": job.status, "coverage": job.coverage, "items": seen, "new": new}


def collect_profiles(cc: ConsoleClient, handles: list[str]) -> dict:
    with session() as s:
        run = log_run(s, source=SOURCE, actor="user-info", params={"usernames": handles})
    try:
        job = cc.run("user-info", {"usernames": handles})
        profiles = cc.dataset("profiles", usernames=",".join(handles))
    except ConsoleError as e:
        with session() as s:
            finish_run(s.merge(run), status="failed", error=str(e))
        return {"status": "failed", "error": str(e)}
    now = datetime.now(UTC).replace(microsecond=0)
    with session() as s:
        for p in profiles:
            h = p.get("username")
            if not h or h not in handles:
                continue
            ensure_account(s, h, user_id=str(p.get("user_id") or "") or None)
            created = p.get("created_at")
            s.add(AccountSnapshot(
                handle=h, observed_at=now, followers_count=p.get("followers_count"),
                following_count=p.get("following_count"), verified=p.get("verified"),
                description=p.get("description"),
                account_created_at=parse_ts(created) if isinstance(created, str) else None,
                source=SOURCE, raw=p,
            ))
        finish_run(s.merge(run), status=job.status, items=len(profiles), coverage=job.coverage)
    return {"status": job.status, "profiles": len(profiles)}


def collect_engagers(cc: ConsoleClient, handle: str, *, days: int = 90) -> dict:
    """Who publicly replied to / quoted the client's posts (likes are not exposed)."""
    params = {"usernames": [handle], "since": _since(days), "max_pages": 20, "include_quotes": True}
    with session() as s:
        run = log_run(s, source=SOURCE, actor="client-engagers", params=params)
    try:
        job = cc.run("client-engagers", params, timeout=1200)
        rows = cc.dataset("tweets", to_username=handle, since=params["since"])
    except ConsoleError as e:
        with session() as s:
            finish_run(s.merge(run), status="failed", error=str(e))
        return {"handle": handle, "status": "failed", "error": str(e)}
    added = 0
    with session() as s:
        for r in rows:
            if r.get("username") == handle:
                continue
            kind = "quote" if r.get("is_quote") else "reply"
            s.merge(Engager(
                client_handle=handle,
                target_tweet_id=r.get("in_reply_to_tweet_id") or r.get("quoted_tweet_id"),
                engager_handle=r.get("username"),
                engagement_tweet_id=str(r["tweet_id"]),
                kind=kind,
                created_at=parse_ts(r["created_at"]) if r.get("created_at") else None,
                engager_followers=r.get("author_followers_count"),
                source=SOURCE,
            ))
            added += 1
        finish_run(s.merge(run), status=job.status, items=added, coverage=job.coverage)
    return {"handle": handle, "status": job.status, "engagements": added}


def collect_all(days: int | None = None) -> list[dict]:
    cc = ConsoleClient()
    if not cc.available():
        raise ConsoleError("XP_API_KEY not set; use `xaudit ingest --from-seed` or set the key")
    out = []
    cfg = clients()
    out.append(collect_profiles(cc, list(cfg) + [p for c in cfg.values() for p in c.get("peers", [])]))
    for handle, c in cfg.items():
        out.append(collect_timeline(cc, handle, days=days))
        out.append(collect_engagers(cc, handle))
        for peer in c.get("peers", []):
            out.append(collect_timeline(cc, peer, days=analysis_cfg()["default_window_days"],
                                        include_replies=False, max_pages=10))
    return out
