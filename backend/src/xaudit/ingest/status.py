"""What the database holds per client — used to decide whether a backfill is needed."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from xaudit.db.models import Classification, Post
from xaudit.db.session import session
from xaudit.settings import clients


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


def needs_backfill(min_posts: int = 100, min_history_days: int = 150) -> bool:
    st = data_status()["clients"]
    return any(c["posts"] < min_posts or c["history_days"] < min_history_days for c in st.values())
