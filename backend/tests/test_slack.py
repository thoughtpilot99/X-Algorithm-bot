import httpx
import pytest

from xaudit.monitor import slack


def test_post_skips_without_webhook(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    assert slack.post({"text": "x"}) is False


def test_post_sends_json_and_retries_on_429():
    calls = []

    def handler(req):  # noqa: ANN001
        calls.append(req)
        return httpx.Response(429, headers={"Retry-After": "0"}) if len(calls) == 1 else httpx.Response(200, text="ok")

    assert slack.post({"text": "hi"}, webhook="https://hooks.slack.test/x", transport=httpx.MockTransport(handler))
    assert len(calls) == 2 and b'"text":"hi"' in calls[-1].content.replace(b" ", b"")


def test_post_raises_on_bad_webhook():
    with pytest.raises(RuntimeError):
        slack.post({"text": "x"}, webhook="https://hooks.slack.test/x",
                   transport=httpx.MockTransport(lambda r: httpx.Response(404, text="no_service")))
