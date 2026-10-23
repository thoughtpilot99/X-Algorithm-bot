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


def store_handler(req: httpx.Request) -> httpx.Response:
    p = req.url.path
    q = dict(req.url.params)
    if p.endswith("/health"):
        return httpx.Response(200, json={"ok": True})
    if req.headers.get("X-API-Key") != "k":
        return httpx.Response(401, text="unauthorised")
    if p.endswith("/datasets/tweets"):
        total = 100
        if "since" in q:
            total = 10
        if q.get("post_type") == "reply":
            total = min(total, 40)
        if "contains" in q:
            total = 5
        return httpx.Response(200, json={"items": [REC], "page": {"total": total, "returned": 1, "truncated": False}})
    return httpx.Response(404)


def test_doctor_ok_and_filters():
    rep = doctor.run(make_client(store_handler))
    assert rep.ok, rep.as_dict()
    assert rep.filters == {"since": True, "post_type": True, "contains": True}


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
