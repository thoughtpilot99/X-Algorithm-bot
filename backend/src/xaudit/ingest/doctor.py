"""Check the console API contract before collecting.

A collector that silently gets zero items is indistinguishable from "the
account posted nothing" — content-agent's Apify outage stayed invisible for
nine days that way. The doctor fails loudly instead, and records what it found.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from xaudit.ingest.console_client import ConsoleClient, ConsoleError
from xaudit.ingest.normalize import normalize

REQUIRED_FIELDS = {"tweet_id", "username", "created_at", "text", "view_count", "like_count", "reply_count",
                   "retweet_count", "is_reply", "is_quote", "is_retweet"}


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    blocking: bool = True


@dataclass
class DoctorReport:
    ok: bool
    checks: list[Check] = field(default_factory=list)
    filters: dict[str, bool] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"ok": self.ok, "filters": self.filters, "checks": [asdict(c) for c in self.checks]}


def _total(cc: ConsoleClient, **params) -> int | None:  # noqa: ANN003
    page = cc.page("tweets", limit=1, **params)
    meta = page.get("page") or {}
    if "total" in meta:
        return int(meta["total"])
    return None


def run(cc: ConsoleClient | None = None, handle: str = "nifinet") -> DoctorReport:
    cc = cc or ConsoleClient()
    checks: list[Check] = []
    filters: dict[str, bool] = {}

    def add(name: str, ok: bool, detail: str, blocking: bool = True) -> None:
        checks.append(Check(name, ok, detail, blocking))

    if not cc.available():
        add("api key", False, "XP_API_KEY is not set")
        return DoctorReport(False, checks)
    try:
        cc.health()
        add("health", True, "reachable")
    except Exception as e:  # noqa: BLE001
        add("health", False, f"{type(e).__name__}: {e}")
        return DoctorReport(False, checks)

    try:
        page = cc.page("tweets", username=handle, limit=1)
    except ConsoleError as e:
        add("auth + dataset read", False, f"{e} (status {e.status})")
        return DoctorReport(False, checks)
    items = page.get("items") or []
    add("auth + dataset read", True, f"{len(items)} item(s) for @{handle}")
    if not items:
        add("records present", False, f"no stored records for @{handle}")
        return DoctorReport(False, checks)
    missing = REQUIRED_FIELDS - set(items[0])
    add("record shape", not missing, "all expected fields present" if not missing else f"missing: {sorted(missing)}")
    try:
        normalize(items[0])
        add("normaliser", True, "first record normalises")
    except Exception as e:  # noqa: BLE001
        add("normaliser", False, f"{type(e).__name__}: {e}")
    has_meta = isinstance(page.get("page"), dict) and "total" in page["page"]
    add("pagination metadata", has_meta, "page.total present" if has_meta else "no page.total; paging by item count",
        blocking=False)

    # Filters: a filter is honoured if it changes the total in the expected direction.
    if has_meta:
        base = _total(cc, username=handle)
        recent = _total(cc, username=handle, since=(date.today() - timedelta(days=14)).isoformat())
        replies = _total(cc, username=handle, post_type="reply")
        mention = _total(cc, contains=f"@{handle}", post_type="reply")
        filters = {
            "since": recent is not None and base is not None and recent < base,
            "post_type": replies is not None and base is not None and replies < base,
            "contains": mention is not None and mention > 0,
        }
        for k, ok in filters.items():
            add(f"filter `{k}`", ok, "honoured" if ok else "not honoured — collector falls back to client-side filtering",
                blocking=k == "since")
    ok = all(c.ok for c in checks if c.blocking)
    return DoctorReport(ok, checks, filters)
