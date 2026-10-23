"""Deterministic, reproducible text and timing features.

Media type is not present in the source data. On X, both external links and
attached media can appear in text as t.co URLs, so ``has_tco_url`` means
"external link OR attached media" and is reported that way.
"""

from __future__ import annotations

import re

import pandas as pd

from xaudit.ingest.normalize import LEADING_MENTIONS

URL = re.compile(r"https?://\S+")
HASHTAG = re.compile(r"(?<!\w)#\w+")
MENTION = re.compile(r"(?<!\w)@\w{1,15}")
NUMBER = re.compile(r"(\$\s?\d|\d+(\.\d+)?\s?(%|x\b|k\b|m\b|M\b)|\b\d{2,}\b)")
LIST_LINE = re.compile(r"^\s*(\d+[.)]|[-•→✅❌▪️*]|[a-z]\))\s+", re.M)
FIRST_PERSON = re.compile(r"\b(I|I'm|I've|I'd|my|me|we|we've|we're|our|us)\b", re.I)
CTA = re.compile(
    r"\b(comment|reply|repost|retweet|rt\b|follow|bookmark|save this|dm me|link (in|below)|"
    r"check it out|sign up|grab|download|join)\b",
    re.I,
)
KEYWORD_CTA = re.compile(r"\b(comment|reply)\s+[\"'“]?[A-Z]{2,}[\"'”]?", re.I)
QUESTION = re.compile(r"\?")
# Lead-magnet fulfilment replies: the author answering people who commented a
# keyword ("Sent", "Here you go: <link>", "Appreciate the comment: <link>").
# These are operational replies, almost certainly under the author's own posts,
# and are analysed separately from conversational comments on others' posts.
FULFILMENT = re.compile(
    r"^\W*(sent|send|shared|done|unable to (share|dm)|check (your )?dms?)\W*$|"
    r"^\W*(here you go|appreciate the comment|thanks for (the )?comment(ing)?|dropping the (playbook|link|guide)"
    r"|the full breakdown is here)",
    re.I,
)


def strip_reply_prefix(text: str) -> str:
    return LEADING_MENTIONS.sub("", text or "", count=1)


def first_line(text: str) -> str:
    for ln in (text or "").splitlines():
        if ln.strip():
            return ln.strip()
    return ""


def is_fulfilment(text: str) -> bool:
    body = re.sub(r"@\w{1,15}", "", strip_reply_prefix(text)).strip()
    return bool(FULFILMENT.search(body))


def text_features(text: str, *, is_reply: bool = False) -> dict:
    body = strip_reply_prefix(text) if is_reply else (text or "")
    hook = first_line(body)
    lines = [ln for ln in body.splitlines() if ln.strip()]
    no_urls = URL.sub("", body)
    words = re.findall(r"\b\w+\b", no_urls)
    return {
        "char_len": len(no_urls.strip()),
        "word_count": len(words),
        "line_count": len(lines),
        "has_tco_url": bool(URL.search(body)),
        "n_urls": len(URL.findall(body)),
        "n_hashtags": len(HASHTAG.findall(body)),
        "n_mentions": len(MENTION.findall(body)),
        "has_numbers": bool(NUMBER.search(no_urls)),
        "has_list": len(LIST_LINE.findall(body)) >= 2,
        "has_question": bool(QUESTION.search(no_urls)),
        "first_person": bool(FIRST_PERSON.search(no_urls)),
        "has_cta": bool(CTA.search(no_urls)),
        "keyword_cta": bool(KEYWORD_CTA.search(no_urls)),
        "hook": hook[:280],
        "hook_word_count": len(re.findall(r"\b\w+\b", URL.sub("", hook))),
        "hook_has_number": bool(NUMBER.search(hook)),
        "hook_is_question": hook.rstrip().endswith("?"),
    }


def length_bucket(words: int) -> str:
    if words < 15:
        return "very short (<15 words)"
    if words < 50:
        return "short (15-49)"
    if words < 150:
        return "medium (50-149)"
    if words < 400:
        return "long (150-399)"
    return "very long (400+)"


def content_format(row: pd.Series) -> str:
    if isinstance(row.get("article_title"), str) and row["article_title"]:
        return "x_article"
    if row["post_type"] == "quote":
        return "quote_post"
    if row.get("has_self_thread"):
        return "thread"
    if row["is_long_form"]:
        return "long_post"
    return "short_post"


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    feats = pd.DataFrame(
        [text_features(t, is_reply=(pt == "reply")) for t, pt in zip(df["text"], df["post_type"], strict=True)],
        index=df.index,
    )
    out = pd.concat([df, feats], axis=1)
    # A thread = an authored post followed by self-replies from the same account
    # within 15 minutes. (Parent ids are unavailable, so this is a timing inference.)
    out["has_self_thread"] = False
    for _handle, g in out.groupby("handle"):
        selfs = g.loc[g["is_self_reply"], "created_at"].map(lambda t: t.timestamp()).to_numpy(dtype=float)
        if len(selfs) == 0:
            continue
        for idx, ts in g.loc[g["is_authored"], "created_at"].items():
            delta = selfs - ts.timestamp()
            if ((delta > 0) & (delta <= 900)).any():
                out.at[idx, "has_self_thread"] = True
    out["reply_role"] = None
    ext = out["is_external_reply"]
    out.loc[ext, "reply_role"] = out.loc[ext, "text"].map(
        lambda t: "fulfilment" if is_fulfilment(t) else "conversation")
    out.loc[out["is_self_reply"], "reply_role"] = "self_thread"
    out["format"] = out.apply(content_format, axis=1)
    out["length_bucket"] = out["word_count"].map(length_bucket)
    # X Article posts are usually a bare t.co link to the article, so "has URL" is
    # confounded with the article format. This variant is the fair link test.
    out["tco_url_excl_articles"] = out["has_tco_url"].where(out["format"] != "x_article")
    out["weekday"] = out["created_at"].dt.day_name()
    out["hour_utc"] = out["created_at"].dt.hour
    out["daypart_utc"] = pd.cut(out["hour_utc"], bins=[-1, 5, 11, 17, 23],
                                labels=["00-05", "06-11", "12-17", "18-23"]).astype(str)
    out["week"] = (out["created_at"].dt.tz_convert(None).dt.to_period("W-SUN").dt.start_time
                   .dt.date.astype(str))
    out["month"] = out["created_at"].dt.strftime("%Y-%m")
    return out
