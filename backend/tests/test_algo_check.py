"""Algorithm check: the X-weighted proxy, verdict rules, and own-post thread parsing."""

import numpy as np
import pandas as pd

from xaudit.analysis import algo_check as ac

W = {"ReplyWeight": {"value": 5.0}, "QuoteWeight": {"value": 5.0}, "RetweetWeight": {"value": 1.0},
     "FavoriteWeight": {"value": 0.66}}


def _posts(n: int, views: float, replies: float, likes: float, level: str, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    v = rng.lognormal(np.log(views), 0.3, n)
    return pd.DataFrame({
        "tweet_id": [f"{level}{i}" for i in range(n)], "url": "u", "text": "t", "article_title": None,
        "created_at": pd.Timestamp("2026-06-01", tz="UTC"), "format": level, "views": v,
        "replies": np.round(v * replies / 1000), "likes": np.round(v * likes / 1000), "quotes": 0.0, "reposts": 0.0,
        "bookmarks": 0.0, "vs_baseline": 1.0,
    })


def test_weighted_proxy_uses_published_weights():
    df = pd.DataFrame({"views": [1000.0], "replies": [2.0], "quotes": [1.0], "reposts": [3.0], "likes": [10.0],
                       "bookmarks": [50.0]})
    out = ac.add_weighted(df, W)
    # 5*2 + 5*1 + 1*3 + 0.66*10 per 1,000 views; bookmarks carry no published weight.
    assert out["x_weighted_per_1k"].iloc[0] == 5 * 2 + 5 * 1 + 1 * 3 + 0.66 * 10
    assert out["x_weighted_per_post"].iloc[0] == 5 * 2 + 5 * 1 + 1 * 3 + 0.66 * 10


def test_verdict_rules():
    assert ac.verdict(2.0, {"ratio": 1.5, "lo": 1.2, "hi": 1.8}, 20, 20, 8)[0] == "backed"
    assert ac.verdict(0.4, {"ratio": 0.6, "lo": 0.4, "hi": 0.8}, 20, 20, 8)[0] == "backed"
    assert ac.verdict(2.0, {"ratio": 0.9, "lo": 0.7, "hi": 1.1}, 20, 20, 8)[0] == "partly"
    assert ac.verdict(2.0, {"ratio": 1.5, "lo": 1.2, "hi": 1.8}, 5, 20, 8)[0] == "not_enough"


def test_segment_with_more_replies_per_view_is_backed():
    a = pd.concat([_posts(30, 4000, replies=4, likes=10, level="x_article", seed=1),
                   _posts(60, 1000, replies=1, likes=10, level="short_post", seed=2)], ignore_index=True)
    a = ac.add_weighted(a, W)
    c = ac.check_segment(a, "format", "x_article", W, 8)
    assert c["reach"]["ratio"] > 1 and c["verdict"] == "backed"
    assert len(c["best_posts"]) == 3 and all("replies" in p for p in c["best_posts"])
    # Same reach gap but equal reactions per view: not explained by public reactions.
    b = pd.concat([_posts(30, 4000, replies=1, likes=10, level="x_article", seed=3),
                   _posts(60, 1000, replies=1, likes=10, level="short_post", seed=4)], ignore_index=True)
    c2 = ac.check_segment(ac.add_weighted(b, W), "format", "x_article", W, 8)
    assert c2["verdict"] == "partly"


def test_chance_words():
    assert "1,000" in ac.chance_words(0.0005) and ac.chance_words(0.5) == "could easily be chance"


def test_own_post_thread_counts_author_answers(tmp_path, monkeypatch):
    from xaudit.db import session as db
    from xaudit.db.models import PostThread
    from xaudit.ingest.collectors import import_post_thread

    old = db.db_url()
    monkeypatch.setenv("XAUDIT_DB_URL", f"sqlite:///{tmp_path / 't.sqlite'}")
    db.reset_engine()
    try:
        items = [
            {"tweet_id": "1", "username": "nifinet", "created_at": "2026-10-01T10:00:00Z"},
            {"tweet_id": "2", "username": "alice", "created_at": "2026-10-01T10:05:00Z"},
            {"tweet_id": "3", "username": "bob", "created_at": "2026-10-01T10:07:00Z"},
            {"tweet_id": "4", "username": "nifinet", "created_at": "2026-10-01T10:30:00Z"},
        ]
        with db.session() as s:
            assert import_post_thread(s, "nifinet", "1", items)
        with db.session() as s:
            t = s.get(PostThread, "1")
            assert (t.other_replies, t.distinct_repliers, t.author_replies) == (2, 2, 1)
            assert t.author_first_reply_minutes == 30
    finally:
        monkeypatch.setenv("XAUDIT_DB_URL", old)
        db.reset_engine()
