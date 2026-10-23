from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from xaudit.db.models import Artifact, Base, utcnow
from xaudit.settings import DATA_DIR


def db_url() -> str:
    return os.environ.get("XAUDIT_DB_URL", f"sqlite:///{Path(DATA_DIR) / 'xaudit.sqlite'}")


_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def engine() -> Engine:
    global _engine, _factory
    if _engine is None:
        url = db_url()
        if url.startswith("sqlite:///"):
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(url, future=True)

        @event.listens_for(_engine, "connect")
        def _pragmas(conn, _):  # noqa: ANN001
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        Base.metadata.create_all(_engine)
        _factory = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def reset_engine() -> None:
    """For tests: forget the cached engine so XAUDIT_DB_URL is re-read."""
    global _engine, _factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _factory = None


@contextmanager
def session() -> Iterator[Session]:
    engine()
    assert _factory is not None
    s = _factory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def save_artifact(kind: str, payload: dict, handle: str = "_global") -> None:
    with session() as s:
        row = s.scalar(select(Artifact).where(Artifact.kind == kind, Artifact.handle == handle))
        if row is None:
            s.add(Artifact(kind=kind, handle=handle, payload=payload))
        else:
            row.payload = payload
            row.created_at = utcnow()


def load_artifact(kind: str, handle: str = "_global") -> dict | None:
    with session() as s:
        row = s.scalar(select(Artifact).where(Artifact.kind == kind, Artifact.handle == handle))
        return None if row is None else row.payload
