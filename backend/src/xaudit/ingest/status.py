"""What the database holds per client — used to decide whether a backfill is needed."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from xaudit.db.models import Classification, Post
from xaudit.db.session import load_artifact, session
from xaudit.settings import analysis_cfg, clients


def data_status() -> dict:
    now = datetime.now(UTC)
    out = {}
    with session() as s:
        n_labels = s.scalar(select(func.count()).select_from(Classification)) or 0
        for h in clients():
            n, oldest = s.execute(select(func.count(), func.min(Post.created_at)).where(Post.handle == h)).one()
            if oldest is not None and oldest.tzinfo is None:
                oldest = oldest.replace(tzinfo=UTC)
            out[h] = {"posts": int(n or 0), "oldest": oldest.isoformat() if oldest else None,
                      "history_days": (now - oldest).days if oldest else 0}
    return {"clients": out, "labels": int(n_labels)}


def backfill_state(min_posts: int = 100, min_history_days: int = 150) -> dict[str, str]:
    """Per client: "ok" once its full-history timeline was collected (or history already covers the window).

    A client whose timeline step failed stays "failed" and is retried on the next run; a client whose
    timeline succeeded is "ok" even if the console store held less history than the window.
    """
    window = analysis_cfg()["extended_window_days"]
    done = load_artifact("backfill_done") or {}
    marks = done.get("clients") or {}
    out = {}
    for h, c in data_status()["clients"].items():
        if c["posts"] < min_posts or c["history_days"] < min_history_days:
            out[h] = "thin"
        elif c["history_days"] >= window - 35 or (marks.get(h) == "ok" and int(done.get("days") or 0) >= window):
            out[h] = "ok"
        else:
            out[h] = marks.get(h, "missing")
    return out


def missing_backfill() -> list[str]:
    return [h for h, s in backfill_state().items() if s != "ok"]


def needs_backfill() -> bool:
    return bool(missing_backfill())
