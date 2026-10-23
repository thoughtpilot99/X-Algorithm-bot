"""Conversation depth: does the author answering commenters go with more reach?

Built from reply threads captured under the client's own posts (tweet-detail,
`post_threads`). Compares posts where others replied and the author answered with
posts where others replied and the author didn't. This is an association: posts
that draw more comments are also more likely to get answers, so the comparison
is also shown for posts with similar comment counts.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from xaudit.analysis.stats import bootstrap_median_ratio, mann_whitney
from xaudit.db.models import PostThread
from xaudit.db.session import session

MIN_GROUP = 8


def depth(handle: str, df: pd.DataFrame) -> dict:
    with session() as s:
        rows = s.execute(select(PostThread).where(PostThread.handle == handle)).scalars().all()
        th = pd.DataFrame([{"tweet_id": r.tweet_id, "other_replies": r.other_replies,
                            "distinct_repliers": r.distinct_repliers, "author_replies": r.author_replies,
                            "author_first_reply_minutes": r.author_first_reply_minutes} for r in rows])
    out = {"threads": int(len(th)), "min_group": MIN_GROUP}
    if th.empty:
        return {**out, "status": "collecting", "note": "Reply threads under the account's posts are being "
                "collected daily from now on; this comparison appears once enough posts have them."}
    a = df[df["is_authored"] & df["mature"] & df["views"].notna()].merge(th, on="tweet_id")
    a = a[a["other_replies"] > 0]
    yes, no = a[a["author_replies"] > 0], a[a["author_replies"] == 0]
    out.update({"posts_with_comments": int(len(a)), "answered": int(len(yes)), "not_answered": int(len(no)),
                "answered_share": float(len(yes) / len(a)) if len(a) else None,
                "median_first_answer_minutes": float(yes["author_first_reply_minutes"].median()) if len(yes) else None})
    if len(yes) < MIN_GROUP or len(no) < MIN_GROUP:
        return {**out, "status": "collecting",
                "note": f"{len(yes)} answered and {len(no)} unanswered posts with comments so far; the comparison "
                        f"needs at least {MIN_GROUP} of each."}
    r = bootstrap_median_ratio(yes["vs_baseline"], no["vs_baseline"])
    rr = bootstrap_median_ratio(yes["replies_per_1k"], no["replies_per_1k"])
    # Same comparison among posts with only 1-3 replies by others, to limit the "more comments -> more answers" effect.
    low = a[a["other_replies"].between(1, 3)]
    ly, ln = low[low["author_replies"] > 0], low[low["author_replies"] == 0]
    out.update({
        "status": "ready",
        "vs_usual": {"answered": float(yes["vs_baseline"].median()), "not_answered": float(no["vs_baseline"].median()),
                     **r, "p": mann_whitney(yes["vs_baseline"], no["vs_baseline"])["p"]},
        "replies_per_1k": {"answered": float(yes["replies_per_1k"].median()),
                           "not_answered": float(no["replies_per_1k"].median()), **rr},
        "similar_comment_counts": ({"answered": float(ly["vs_baseline"].median()), "not_answered": float(ln["vs_baseline"].median()),
                                    "n": [int(len(ly)), int(len(ln))]} if len(ly) >= 5 and len(ln) >= 5 else None),
        "examples": a.sort_values("other_replies", ascending=False)[["tweet_id", "url", "views", "other_replies",
                                                                     "author_replies"]].head(6).to_dict("records"),
    })
    return out
