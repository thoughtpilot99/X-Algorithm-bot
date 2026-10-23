from xaudit.ingest.normalize import classify_type, infer_parent, leading_mentions, normalize


def rec(**kw):
    base = {"tweet_id": "1", "username": "alice", "user_id": "9", "created_at": "2026-10-01T10:00:00Z",
            "text": "hello", "is_reply": False, "is_quote": False, "is_retweet": False, "view_count": 10}
    return {**base, **kw}


def test_type_precedence():
    assert classify_type(rec(is_retweet=True, is_reply=True)) == "repost"
    assert classify_type(rec(is_reply=True, is_quote=True)) == "reply"
    assert classify_type(rec(is_quote=True)) == "quote"
    assert classify_type(rec()) == "original"


def test_parent_inference_is_labelled():
    assert infer_parent(rec(is_reply=True, text="@bob @carol nice"), "alice") == ("bob", "inferred_leading_mention")
    assert infer_parent(rec(is_reply=True, text="continuing the thread"), "alice") == ("alice", "inferred_self_thread")
    assert infer_parent(rec(is_reply=True, in_reply_to_username="dave", text="@bob x"), "alice") == ("dave", "source")
    assert infer_parent(rec(), "alice") == (None, None)


def test_leading_mentions_only_at_start():
    assert leading_mentions("@a @b hi @c") == ["a", "b"]
    assert leading_mentions("hi @c") == []


def test_normalize_keeps_missing_metrics_as_none():
    post, m = normalize(rec(view_count=None, like_count="3"))
    assert m.views is None and m.likes == 3
    assert post.url == "https://x.com/alice/status/1"
