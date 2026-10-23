"""Synthetic data through import -> analysis -> diagnostics -> API."""

import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient

from xaudit.settings import ALGO_REPO_DIR, clients


def _records(handle: str, uid: str, n: int, seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    t0 = datetime(2026, 5, 1, 9, tzinfo=UTC)
    out = []
    for i in range(n):
        kind = i % 4
        article = kind == 0
        views = int(rng.lognormal(np.log(6000 if article else 1500), 0.6))
        is_reply = kind == 3
        text = ("@peer Sent" if i % 8 == 3 else "@peer how do you score this? curious") if is_reply else \
            ("https://t.co/abc" if article else f"How to build signal #{i}\n\n1. step\n2. step\nWhat would you add?")
        out.append({"tweet_id": str(10_000 + i + seed * 1000), "url": None, "username": handle, "user_id": uid,
                    "created_at": (t0 + timedelta(hours=13 * i)).strftime("%Y-%m-%dT%H:%M:%SZ"), "text": text,
                    "lang": "en", "like_count": views // 100, "reply_count": i % 3, "retweet_count": i % 2,
                    "quote_count": 0, "bookmark_count": views // 300, "view_count": views if not is_reply else 40,
                    "is_reply": is_reply, "is_quote": False, "is_retweet": False, "is_long_form": not is_reply,
                    "article_title": "An article" if article else None})
    return out


@pytest.fixture(scope="module")
def seeded(tmp_path_factory):
    root = tmp_path_factory.mktemp("console")
    for seed, (h, c) in enumerate(clients().items(), start=1):
        (root / h).mkdir()
        (root / h / "page_00000.json").write_text(json.dumps(_records(h, c["user_id"], 320, seed)), encoding="utf-8")
    from xaudit.ingest.seed_import import import_seed

    summary = import_seed(root)
    from xaudit.analysis.pipeline import run

    run()
    return summary


def test_import_counts(seeded):
    for h in clients():
        assert seeded[h]["records"] == 320


def test_artifacts_and_fulfilment(seeded):
    from xaudit.db.session import load_artifact

    h = next(iter(clients()))
    com = load_artifact("comments", h)
    assert com["roles"]["fulfilment"] > 0 and com["roles"]["conversation"] > 0
    seg = load_artifact("segments", h)
    art = next(s for s in seg if s["feature"] == "format" and s["level"] == "x_article")
    assert art["tested"] and art["ratio"] > 1


@pytest.mark.skipif(not (ALGO_REPO_DIR / ".git").exists(), reason="algorithm repo not cloned")
def test_diagnostics_pass_guard_and_api_serves(seeded):
    from xaudit.diagnostics.engine import run as drun
    from xaudit.recommend.engine import run as rrun

    h = next(iter(clients()))
    items = drun(h)
    assert items and all(d["evidence"] or d["status"] == "insufficient" for d in items)
    rec = rrun(h)
    assert len(rec["root_causes"]) <= 5
    # Stop/Continue: only the format line may come from the full set; other lines exclude X Articles,
    # and yes/no features appear once (never as their "False" mirror).
    lines = [a["action"] for k in ("stop", "continue") for a in rec["actions"][k] if a["action"].startswith(("Reduce", "Keep"))]
    assert lines and all("Content format" in x or x.endswith("(excluding X Articles)") for x in lines)
    assert not any(": False (" in x for x in lines)
    power = rec["plan"]["power"]
    assert power["min_detectable_ratio_30_days"] and "In 30 days" in power["note"]
    assert "cannot be detected within 30 days" not in power["note"]

    from xaudit.api.app import app

    c = TestClient(app)
    assert c.get("/api/health").json() == {"ok": True}
    assert c.get("/api/accounts").status_code == 200
    r = c.get(f"/api/accounts/{h}/posts", params={"type": ["original"], "segment": "above_2x"})
    assert r.status_code == 200 and all(p["post_type"] == "original" for p in r.json()["items"])
    assert c.get(f"/api/accounts/{h}/artifacts/diagnostics").status_code == 200
    assert c.get("/api/accounts/nobody/overview").status_code == 404
    assert c.get(f"/api/accounts/{h}/posts.csv").headers["content-type"].startswith("text/csv")


@pytest.mark.skipif(not (ALGO_REPO_DIR / ".git").exists(), reason="algorithm repo not cloned")
def test_static_export_writes_every_file(seeded, tmp_path):
    from xaudit.diagnostics.engine import run as drun
    from xaudit.recommend.compare import compare
    from xaudit.recommend.engine import run as rrun
    from xaudit.reports.static_export import ACCOUNT_ROUTES, ARTIFACTS, export

    for h in clients():
        drun(h)
        rrun(h)
    compare()
    r = export(tmp_path)
    for h in clients():
        for name in ACCOUNT_ROUTES:
            json.loads((tmp_path / "data" / h / name).read_text(encoding="utf-8"))
        for kind in ARTIFACTS:
            json.loads((tmp_path / "data" / h / "artifacts" / f"{kind}.json").read_text(encoding="utf-8"))
    params = json.loads((tmp_path / "data/algo/params.json").read_text(encoding="utf-8"))
    assert params["histories"] and r["files"] > 30


def test_slack_digest_builds_from_stored_data(seeded):
    from xaudit.monitor.slack import build_digest

    d = build_digest()
    assert d["text"].startswith("X audit daily digest")
    headers = [b["text"]["text"] for b in d["blocks"] if b["type"] == "header"]
    assert any("@nifinet" in h for h in headers) and any("@MichLieben" in h for h in headers)
    assert len(d["blocks"]) <= 50
