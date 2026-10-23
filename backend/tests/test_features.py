import pandas as pd

from xaudit.analysis.features import add_features, is_fulfilment, text_features


def test_fulfilment_templates():
    assert is_fulfilment("@someone Sent")
    assert is_fulfilment("@a @b sent !!")
    assert is_fulfilment("@x Here you go : https://t.co/abc")
    assert is_fulfilment("@x Appreciate the comment: https://t.co/abc")
    assert not is_fulfilment("@x I sent 10k emails last month and the reply rate dropped")
    assert not is_fulfilment("@x great breakdown, how do you score champions?")


def test_text_features_strip_reply_prefix_and_urls():
    f = text_features("@bob How do you do this? https://t.co/x", is_reply=True)
    assert f["n_mentions"] == 0 and f["has_tco_url"] and f["has_question"]
    assert f["hook"].startswith("How do you")


def test_thread_and_link_confound_columns():
    ts = pd.Timestamp("2026-10-01T10:00:00Z")
    df = pd.DataFrame([
        {"tweet_id": "1", "handle": "a", "created_at": ts, "text": "Big post", "post_type": "original",
         "is_long_form": False, "article_title": None, "is_authored": True, "is_self_reply": False,
         "is_external_reply": False},
        {"tweet_id": "2", "handle": "a", "created_at": ts + pd.Timedelta(minutes=2), "text": "part 2",
         "post_type": "reply", "is_long_form": False, "article_title": None, "is_authored": False,
         "is_self_reply": True, "is_external_reply": False},
        {"tweet_id": "3", "handle": "a", "created_at": ts, "text": "https://t.co/article", "post_type": "original",
         "is_long_form": False, "article_title": "My article", "is_authored": True, "is_self_reply": False,
         "is_external_reply": False},
    ])
    out = add_features(df)
    assert out.loc[0, "format"] == "thread"
    assert out.loc[2, "format"] == "x_article"
    assert pd.isna(out.loc[2, "tco_url_excl_articles"])  # articles excluded from the link test
