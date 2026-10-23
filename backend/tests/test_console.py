"""Doctor and collectors against a mocked console API (no network)."""

import json

import httpx

from xaudit.ingest import doctor
from xaudit.ingest.console_client import ConsoleClient

REC = {"tweet_id": "900", "url": None, "username": "nifinet", "user_id": "286109542",
       "created_at": "2026-10-20T10:00:00Z", "text": "hello", "lang": "en", "like_count": 1, "reply_count": 0,
       "retweet_count": 0, "quote_count": 0, "bookmark_count": 0, "view_count": 50, "is_reply": False,
       "is_quote": False, "is_retweet": False, "is_long_form": False, "article_title": None}


def make_client(handler) -> ConsoleClient:  # noqa: ANN001
    return ConsoleClient(base="https://console.test/api", key="k", poll_every=0, max_retries=0,
                         transport=httpx.MockTransport(handler))


def store_handler(req: httpx.Request, honour: bool = True) -> httpx.Response:
    p = req.url.path
    q = dict(req.url.params)
    if p.endswith("/health"):
        return httpx.Response(200, json={"ok": True})
    if req.headers.get("X-API-Key") != "k":
        return httpx.Response(401, text="unauthorised")
    if p.endswith("/datasets/tweets"):
        rec = dict(REC)
        if honour:
            if "since" in q:
                rec["created_at"] = f"{q['since']}T12:00:00Z"
            if q.get("post_type") == "reply":
                rec.update(is_reply=True, text="@nifinet nice")
            if int(q.get("offset", 0)) > 0:
                rec["tweet_id"] = "901"
        else:
            rec["created_at"] = "2020-01-01T00:00:00Z"
        # Live store behaviour: items without page.total.
        return httpx.Response(200, json={"items": [rec]})
    return httpx.Response(404)


def test_doctor_ok_and_filters():
    rep = doctor.run(make_client(store_handler))
    assert rep.ok, rep.as_dict()
    assert rep.filters == {"since": True, "post_type": True, "contains": True, "offset": True}


def test_doctor_flags_ignored_filters_without_failing():
    rep = doctor.run(make_client(lambda r: store_handler(r, honour=False)))
    assert rep.ok
    assert rep.filters["since"] is False and rep.filters["offset"] is False


def test_doctor_reports_auth_failure():
    cc = ConsoleClient(base="https://console.test/api", key="wrong", max_retries=0,
                       transport=httpx.MockTransport(store_handler))
    rep = doctor.run(cc)
    assert not rep.ok and any("401" in c.detail for c in rep.checks)


def test_doctor_reports_shape_change():
    def handler(req):  # noqa: ANN001
        if req.url.path.endswith("/health"):
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"items": [{"id": 1, "body": "x"}], "page": {"total": 1}})

    rep = doctor.run(make_client(handler))
    assert not rep.ok and any(c.name == "record shape" and not c.ok for c in rep.checks)


def test_dataset_pagination_and_job_results_fallback():
    calls = []

    def handler(req):  # noqa: ANN001
        p = req.url.path
        calls.append(p)
        if p.endswith("/datasets/tweets"):
            off = int(req.url.params.get("offset", 0))
            items = [{**REC, "tweet_id": str(off + i)} for i in range(100 if off == 0 else 30)]
            nxt = 100 if off == 0 else None
            return httpx.Response(200, json={"items": items, "page": {"next_offset": nxt, "truncated": nxt is not None}})
        if p.endswith("/jobs") and req.method == "POST":
            return httpx.Response(200, json={"id": 7})
        if p.endswith("/jobs/7"):
            return httpx.Response(200, json={"status": "succeeded", "coverage": "complete"})
        if p.endswith("/jobs/7/results"):
            return httpx.Response(404)
        if p.endswith("/jobs/7/items"):
            return httpx.Response(200, json={"items": [REC], "page": {"truncated": False}})
        return httpx.Response(404)

    cc = make_client(handler)
    assert len(cc.dataset("tweets", username="nifinet")) == 130
    job = cc.run("tweet-detail", {"tweet_id": "1"})
    assert job.status == "succeeded"
    assert cc.job_items(7) == [REC] and cc._result_path == "/jobs/{id}/items"
    assert json.dumps(calls).count("/jobs/7/results") == 1


def test_dataset_pages_by_count_without_metadata():
    def handler(req):  # noqa: ANN001
        off = int(req.url.params.get("offset", 0))
        n = 100 if off < 200 else 7
        return httpx.Response(200, json={"items": [{**REC, "tweet_id": str(off + i)} for i in range(n)]})

    assert len(make_client(handler).dataset("tweets", username="nifinet")) == 207


def test_dataset_stops_when_offset_is_ignored():
    def handler(req):  # noqa: ANN001
        return httpx.Response(200, json={"items": [{**REC, "tweet_id": str(i)} for i in range(100)]})

    assert len(make_client(handler).dataset("tweets", username="nifinet")) == 100


def test_llm_labels_skip_thinking_blocks(monkeypatch):
    import types

    import anthropic

    from xaudit.analysis import classify

    class FakeMessages:
        def create(self, **kw):  # noqa: ANN003
            return types.SimpleNamespace(content=[
                types.SimpleNamespace(type="thinking", thinking="..."),
                types.SimpleNamespace(type="text", text='{"id": "1", "category": "question", "topic": "other"}\n'
                                                          '{"id": "2", "category": "nonsense"}'),
            ])

    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setattr(anthropic, "Anthropic", lambda: types.SimpleNamespace(messages=FakeMessages()))
    out = classify._llm_labels("reply", [("1", "@a how?"), ("2", "@b hi")], "ctx")
    assert out == {"1": {"category": "question", "topic": "other", "substantive": True}}


def test_llm_failure_falls_back(monkeypatch):
    import types

    import anthropic

    from xaudit.analysis import classify

    class Boom:
        def create(self, **kw):  # noqa: ANN003
            raise RuntimeError("api down")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setattr(anthropic, "Anthropic", lambda: types.SimpleNamespace(messages=Boom()))
    assert classify._llm_labels("content", [("1", "post")], "ctx") == {}


def _profile_handler(empty_first: bool):  # noqa: ANN202
    def handler(req):  # noqa: ANN001
        p = req.url.path
        if p.endswith("/jobs") and req.method == "POST":
            return httpx.Response(200, json={"id": 9})
        if p.endswith("/jobs/9"):
            return httpx.Response(200, json={"status": "succeeded", "coverage": "complete"})
        if p.endswith("/jobs/9/results"):
            items = [] if empty_first else [{"username": "nifinet", "followers_count": 11613}]
            return httpx.Response(200, json={"items": items, "page": {"truncated": False}})
        if p.endswith("/jobs/9/items"):
            return httpx.Response(200, json={"items": [{"username": "nifinet", "followers_count": 11613}]})
        return httpx.Response(404)
    return handler


def test_job_items_skips_path_that_answers_empty():
    cc = make_client(_profile_handler(empty_first=True))
    cc._result_path = "/jobs/{id}/results"  # cached from an earlier tweets job
    assert cc.job_items(9, kind="profiles") == [{"username": "nifinet", "followers_count": 11613}]
    assert cc._result_path == "/jobs/{id}/items"


def test_job_items_all_empty_returns_nothing():
    def handler(req):  # noqa: ANN001
        return httpx.Response(200, json={"items": []})

    cc = make_client(handler)
    assert cc.job_items(9, kind="profiles") == [] and cc._result_path is None


def test_collect_profiles_marks_empty(tmp_path, monkeypatch):
    from xaudit.db import session as db
    from xaudit.ingest import collectors

    # Own database: other tests share the session DB.
    old = db.db_url()
    monkeypatch.setenv("XAUDIT_DB_URL", f"sqlite:///{tmp_path / 't.sqlite'}")
    db.reset_engine()
    try:
        def handler(req):  # noqa: ANN001
            if req.url.path.endswith("/jobs") and req.method == "POST":
                return httpx.Response(200, json={"id": 9})
            if req.url.path.endswith("/jobs/9"):
                return httpx.Response(200, json={"status": "succeeded"})
            return httpx.Response(200, json={"items": []})

        out = collectors.collect_profiles(make_client(handler), ["nifinet"])
        assert out["status"] == "empty" and out["profiles"] == 0
        out = collectors.collect_profiles(make_client(_profile_handler(empty_first=True)), ["nifinet"])
        assert out == {"status": "succeeded", "profiles": 1}
    finally:
        monkeypatch.setenv("XAUDIT_DB_URL", old)
        db.reset_engine()


def test_doctor_profiles_probe():
    def handler(req):  # noqa: ANN001
        if "/jobs" in req.url.path:
            return _profile_handler(empty_first=False)(req)
        return store_handler(req)

    rep = doctor.run(make_client(handler))
    assert rep.ok and any(c.name == "profiles" and c.ok for c in rep.checks)
