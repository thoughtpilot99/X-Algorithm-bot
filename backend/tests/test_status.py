import json
from datetime import UTC, datetime, timedelta

from xaudit.ingest.status import data_status, needs_backfill
from xaudit.settings import clients


def _recs(handle: str, uid: str, days: int, n: int, start_id: int) -> list[dict]:
    now = datetime.now(UTC)
    return [{"tweet_id": str(start_id + i), "username": handle, "user_id": uid,
             "created_at": (now - timedelta(days=days * i / n + 1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "text": "x", "view_count": 10, "is_reply": False, "is_quote": False, "is_retweet": False}
            for i in range(n)]


def test_backfill_needed_until_history_is_deep(tmp_path, monkeypatch):
    from xaudit.db import session as dbs
    from xaudit.ingest.seed_import import import_seed

    # Own database: other tests share the session DB and already hold deep history.
    old = dbs.db_url()
    monkeypatch.setenv("XAUDIT_DB_URL", f"sqlite:///{tmp_path}/status.sqlite")
    dbs.reset_engine()
    try:
        _run(tmp_path, import_seed)
    finally:
        monkeypatch.setenv("XAUDIT_DB_URL", old)
        dbs.reset_engine()


def _run(tmp_path, import_seed):  # noqa: ANN001

    root = tmp_path / "console"
    for k, (h, c) in enumerate(clients().items()):
        (root / h).mkdir(parents=True)
        (root / h / "page_00000.json").write_text(json.dumps(_recs(h, c["user_id"], 14, 30, 7_000_000 + k * 1000)))
    import_seed(root)
    assert needs_backfill()  # 14 days of history is a short history

    root2 = tmp_path / "console2"
    for k, (h, c) in enumerate(clients().items()):
        (root2 / h).mkdir(parents=True)
        (root2 / h / "page_00000.json").write_text(json.dumps(_recs(h, c["user_id"], 175, 150, 8_000_000 + k * 1000)))
    import_seed(root2)
    st = data_status()["clients"]
    assert all(v["history_days"] >= 150 and v["posts"] >= 100 for v in st.values())
    # Deep enough, but no backfill has covered the configured 12-month window yet.
    assert needs_backfill()
    from xaudit.db.session import save_artifact
    from xaudit.settings import analysis_cfg

    save_artifact("backfill_done", {"days": analysis_cfg()["extended_window_days"]})
    assert not needs_backfill()  # attempted once; not repeated daily even if the store held less
