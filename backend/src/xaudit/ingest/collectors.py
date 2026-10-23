"""Live collection through the ThoughtPilot console (requires XP_API_KEY).

Each collector records a CollectionRun and appends timestamped metric
observations, so re-running builds a time series instead of overwriting.

Only public data is collected. Private analytics (profile visits, follows,
link clicks, audience) are not available through this source.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select

from xaudit.db.models import AccountSnapshot, Engager, ReplyThread
from xaudit.db.session import session
from xaudit.ingest.console_client import ConsoleClient, ConsoleError
from xaudit.ingest.normalize import parse_ts
from xaudit.ingest.seed_import import import_threads
from xaudit.ingest.store import ensure_account, finish_run, log_run, upsert_records
from xaudit.settings import RAW_DIR, analysis_cfg, clients

SOURCE = "console_live"


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _since(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def _within(items: list[dict], since: str) -> list[dict]:
    """Client-side date filter (in case the store ignores `since`)."""
    return [i for i in items if (i.get("created_at") or "")[:10] >= since]


class _Run:
    """Context manager: open a CollectionRun, close it with status/items/error."""

    def __init__(self, actor: str, params: dict) -> None:
        self.actor, self.params = actor, params
        self.status, self.items, self.new, self.coverage, self.error = "succeeded", 0, 0, None, None

    def __enter__(self) -> _Run:
        with session() as s:
            self.id = log_run(s, source=SOURCE, actor=self.actor, params=self.params).id
        return self

    def __exit__(self, et, ev, tb) -> bool:  # noqa: ANN001
        if ev is not None:
            self.status, self.error = "failed", f"{type(ev).__name__}: {ev}"
        from xaudit.db.models import CollectionRun

        with session() as s:
            finish_run(s.get(CollectionRun, self.id), status=self.status, items=self.items, new_items=self.new,
                       coverage=self.coverage, error=self.error)
        return isinstance(ev, ConsoleError)  # swallow console errors (recorded); re-raise bugs


def collect_timeline(cc: ConsoleClient, handle: str, *, days: int, include_replies: bool = True,
                     max_pages: int = 20) -> dict:
    since = _since(days)
    params = {"username": handle, "since": since, "include_replies": include_replies, "max_pages": max_pages,
              "limit": 5000}
    with _Run("user-tweets", params) as run:
        job = cc.run("user-tweets", params)
        run.coverage = job.coverage
        if job.status != "succeeded":
            run.status, run.error = job.status, job.error
            return {"handle": handle, "status": job.status, "error": job.error}
        items = [i for i in _within(cc.dataset("tweets", username=handle, since=since), since)
                 if (i.get("username") or "").lower() == handle.lower()]
        if not include_replies:
            items = [i for i in items if not i.get("is_reply")]
        with session() as s:
            run.items, run.new = upsert_records(s, items, source=SOURCE, observed_at=_now(),
                                                observed_at_is_import_time=False)
        if run.items == 0:
            run.status = "empty"
    return {"handle": handle, "status": run.status, "coverage": run.coverage, "items": run.items, "new": run.new}


def collect_profiles(cc: ConsoleClient, handles: list[str]) -> dict:
    with _Run("user-info", {"usernames": handles}) as run:
        job = cc.run("user-info", {"usernames": handles}, timeout=300)
        run.coverage = job.coverage
        if job.status != "succeeded":
            run.status, run.error = job.status, job.error
            return {"status": job.status, "error": job.error}
        profiles = cc.job_items(job.job_id, kind="profiles")
        if not profiles:
            # A succeeded job with no profiles would silently stop follower tracking.
            run.status, run.error = "empty", f"user-info job {job.job_id} succeeded but returned no profiles"
            return {"status": run.status, "error": run.error, "profiles": 0}
        now = _now()
        with session() as s:
            for p in profiles:
                h = p.get("username")
                if not h:
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
        run.items = len(profiles)
    return {"status": run.status, "profiles": run.items}


def collect_engagers(cc: ConsoleClient, handle: str, *, default_days: int = 90) -> dict:
    """Public replies by others that mention the account, from the console store.

    The `client-engagers` actor's result plane returned no rows when tested (2026-10-23), while the
    same replies were readable from the store by mention, so the store query is used directly.
    """
    with session() as s:
        last = s.scalar(select(func.max(Engager.created_at)).where(Engager.client_handle == handle))
    since = (last.date() - timedelta(days=2)).isoformat() if last else _since(default_days)
    with _Run("store:mentions", {"handle": handle, "since": since}) as run:
        rows = _within(cc.dataset("tweets", contains=f"@{handle}", post_type="reply", since=since), since)
        added = 0
        with session() as s:
            for r in rows:
                who = r.get("username")
                if not who or who.lower() == handle.lower() or f"@{handle.lower()}" not in (r.get("text") or "").lower():
                    continue
                eid = str(r["tweet_id"])
                if s.scalar(select(Engager.id).where(Engager.engagement_tweet_id == eid)):
                    continue
                s.add(Engager(client_handle=handle, target_tweet_id=r.get("in_reply_to_tweet_id"),
                              engager_handle=who, engagement_tweet_id=eid,
                              kind="quote" if r.get("is_quote") else "reply",
                              created_at=parse_ts(r["created_at"]) if r.get("created_at") else None,
                              engager_followers=r.get("author_followers_count"), source=SOURCE))
                added += 1
        run.items, run.new = len(rows), added
    return {"handle": handle, "status": run.status, "engagements_new": added}


def pending_thread_ids(handle: str, cap: int) -> list[str]:
    """Newest conversational comments without thread context."""
    from xaudit.analysis.dataset import load_posts
    from xaudit.analysis.features import is_fulfilment

    df = load_posts(handle, window_days=30)
    if df.empty:
        return []
    with session() as s:
        have = set(s.execute(select(ReplyThread.tweet_id)).scalars())
    conv = df[df["is_external_reply"] & ~df["text"].map(is_fulfilment) & ~df["tweet_id"].isin(have)]
    return conv.sort_values("created_at", ascending=False)["tweet_id"].head(cap).tolist()


def collect_threads_for_new_comments(cc: ConsoleClient, handle: str, *, cap: int = 40) -> dict:
    ids = pending_thread_ids(handle, cap)
    folder = RAW_DIR / "console" / "threads"
    folder.mkdir(parents=True, exist_ok=True)
    ok = failed = 0
    with _Run("tweet-detail", {"handle": handle, "requested": len(ids)}) as run:
        for tid in ids:
            try:
                job = cc.run("tweet-detail", {"tweet_id": tid, "limit": 40, "max_pages": 1}, timeout=240)
                if job.status != "succeeded":
                    failed += 1
                    continue
                items = cc.job_items(job.job_id, kind="tweets")
            except ConsoleError:
                failed += 1
                continue
            (folder / f"{tid}.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            ok += 1
        with session() as s:
            import_threads(s, folder)
        run.items, run.new = ok, ok
        if failed:
            run.coverage = f"partial: {failed} failed"
    return {"handle": handle, "threads": ok, "failed": failed}


def collect_all(days: int | None = None, *, peers: bool = True, threads: bool = True) -> list[dict]:
    """Full live collection (also used for the first CI run)."""
    cc = ConsoleClient()
    if not cc.available():
        raise ConsoleError("XP_API_KEY not set; use `xaudit ingest --from-seed` or set the key")
    days = days or analysis_cfg()["extended_window_days"]
    cfg = clients()
    out = [collect_profiles(cc, list(cfg) + [p for c in cfg.values() for p in c.get("peers", [])])]
    for handle, c in cfg.items():
        with session() as s:
            ensure_account(s, handle, user_id=c.get("user_id"), name=c.get("name"), role="client",
                           company=c.get("company"))
            for p in c.get("peers", []):
                ensure_account(s, p, role="peer", client_of=handle)
        out.append(collect_timeline(cc, handle, days=days))
        out.append(collect_engagers(cc, handle))
        if threads:
            out.append(collect_threads_for_new_comments(cc, handle))
        if peers:
            for peer in c.get("peers", []):
                out.append(collect_timeline(cc, peer, days=min(days, analysis_cfg()["default_window_days"]),
                                            include_replies=False, max_pages=10))
    return out
