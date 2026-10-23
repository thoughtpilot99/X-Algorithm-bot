"""Comment intelligence: what the account's replies do and whether they pay off.

Replies are split by role (see analysis.features):
- ``conversation``  comments on other people's posts (the commenting strategy);
- ``fulfilment``    "Sent" / "Here you go: <link>" replies delivering a lead
                    magnet to people who commented a keyword (operational);
- ``self_thread``   continuations of the author's own threads.

Data limits, stated in every output:
- the parent post (text, time, engagement) is not available from the source,
  so reply latency and parent-post topic cannot be measured;
- whether the parent author replied back is not observable; a reply with
  reply_count > 0 shows *someone* replied;
- parent-author follower counts are only present when profiles were collected.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from xaudit.analysis.classify import SUBSTANTIVE
from xaudit.analysis.stats import robust_summary
from xaudit.settings import config

LIMITS = [
    "Parent post text, timestamp and engagement are not in the source data: reply latency and "
    "parent-post topic are unavailable.",
    "Parent author is inferred from the reply's leading @mention (X convention), not from a parent id.",
    "Whether the parent author responded is not observable; reply_count > 0 means someone replied.",
    "Follower counts of parent authors are used only where profile snapshots exist.",
]


def _hhi(counts: pd.Series) -> float:
    s = counts / counts.sum()
    return float((s ** 2).sum())


def _gini(counts: pd.Series) -> float:
    x = np.sort(counts.to_numpy(dtype=float))
    n = x.size
    if n == 0 or x.sum() == 0:
        return 0.0
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def effectiveness_scores(conv: pd.DataFrame, followers: dict[str, int]) -> pd.DataFrame:
    """Commenting Effectiveness Score (INTERNAL DIAGNOSTIC, 0-100), per reply.

    Components (0..1), weights from accounts.yaml ``comment_score_weights``:
      relevance           label relevant_to_icp (or topic != other)
      originality         category in the substantive set
      observed_engagement reply views / account's median conversation-reply views, capped at 3x -> /3
      conversation        reply drew at least one public reply
      timing              unavailable (no parent timestamp) -> weight redistributed
    """
    w = dict(config()["comment_score_weights"])
    available = {k: v for k, v in w.items() if k != "timing"}
    total = sum(available.values())
    conv = conv.copy()
    med = conv["views"].median() or 1
    rel = conv.get("relevant_to_icp")
    conv["c_relevance"] = (rel.fillna(False).astype(bool) if rel is not None
                           else conv["topic"].fillna("other").ne("other")).astype(float)
    conv["c_originality"] = conv["category"].isin(SUBSTANTIVE).astype(float)
    conv["c_observed_engagement"] = (conv["views"].fillna(0) / med).clip(upper=3) / 3
    conv["c_conversation"] = (conv["replies"].fillna(0) > 0).astype(float)
    conv["effectiveness"] = 100 * sum(conv[f"c_{k}"] * v for k, v in available.items()) / total
    conv["parent_followers"] = conv["parent_author"].map(followers)
    return conv


def comment_report(df: pd.DataFrame, handle: str, followers: dict[str, int] | None = None,
                   peers: list[str] | None = None) -> dict:
    followers = followers or {}
    replies = df[df["post_type"] == "reply"]
    roles = replies["reply_role"].value_counts().to_dict()
    out: dict = {"limits": LIMITS, "roles": roles,
                 "score_label": "Commenting Effectiveness Score — internal diagnostic, not an X algorithm score",
                 "score_weights": config()["comment_score_weights"]}

    ful = replies[replies["reply_role"] == "fulfilment"]
    out["fulfilment"] = {
        "n": int(len(ful)),
        "per_week": float(len(ful) / max(1, (df["created_at"].max() - df["created_at"].min()).days / 7)),
        "distinct_recipients": int(ful["parent_author"].nunique()),
        "views": robust_summary(ful["views"]),
        "note": "Fulfilment replies are inferred from their template text. Each one answers a person who "
                "commented a keyword, so their volume is a lower bound on keyword-CTA comments received.",
    }

    conv = replies[(replies["reply_role"] == "conversation") & replies["mature"]]
    if conv.empty:
        out["conversation"] = {"n": 0}
        return out
    conv = effectiveness_scores(conv, followers)
    out["conversation"] = {
        "n": int(len(conv)),
        "views": robust_summary(conv["views"]),
        "likes": robust_summary(conv["likes"]),
        "share_with_reply": float((conv["replies"].fillna(0) > 0).mean()),
        "share_with_like": float((conv["likes"].fillna(0) > 0).mean()),
        "effectiveness": robust_summary(conv["effectiveness"]),
        "word_count": robust_summary(conv["word_count"]),
    }

    def by(col: str) -> list[dict]:
        rows = []
        for k, g in conv.groupby(conv[col].astype(str)):
            rows.append({col: k, "n": int(len(g)), "median_views": float(g["views"].median()),
                         "median_likes": float(g["likes"].median()),
                         "share_with_reply": float((g["replies"].fillna(0) > 0).mean()),
                         "median_effectiveness": float(g["effectiveness"].median())})
        return sorted(rows, key=lambda r: -r["n"])

    # Thread context (tweet-detail sample): latency to parent, whether the parent author replied.
    if "latency_minutes" in conv and conv["latency_minutes"].notna().any():
        t = conv[conv["latency_minutes"].notna()]
        out["thread_sample"] = {
            "n": int(len(t)),
            "latency_minutes": robust_summary(t["latency_minutes"]),
            "share_within_60min": float((t["latency_minutes"] <= 60).mean()),
            "share_after_24h": float((t["latency_minutes"] > 1440).mean()),
            "parent_author_responded_share": float(t["parent_author_responded"].fillna(False).astype(bool).mean()),
            "parent_views": robust_summary(t["parent_views"]),
            "reply_views_vs_parent_views_median": float((t["views"] / t["parent_views"].replace(0, np.nan)).median()),
            "early_vs_late_views": {
                "within_60min": robust_summary(t.loc[t["latency_minutes"] <= 60, "views"]),
                "after_60min": robust_summary(t.loc[t["latency_minutes"] > 60, "views"]),
            },
            "note": "Sample of the most recent conversational comments with tweet-detail context; the parent author "
                    "reply check only sees replies returned on the first page of the thread.",
        }
    out["by_category"] = by("category") if "category" in conv else []
    out["by_topic"] = by("topic") if "topic" in conv else []
    out["by_length"] = by("length_bucket")
    out["category_share"] = conv["category"].value_counts(normalize=True).round(3).to_dict() \
        if "category" in conv else {}

    # Interaction network: whose posts the account comments on.
    targets = conv["parent_author"].value_counts()
    peers = set(peers or [])
    partners = []
    for author, n in targets.head(25).items():
        g = conv[conv["parent_author"] == author]
        partners.append({
            "parent_author": author, "replies": int(n),
            "median_views": float(g["views"].median()),
            "total_views": float(g["views"].sum()),
            "share_with_reply": float((g["replies"].fillna(0) > 0).mean()),
            "median_effectiveness": float(g["effectiveness"].median()),
            "parent_followers": followers.get(author),
            "is_peer_or_client": author in peers,
        })
    out["partners"] = partners
    out["concentration"] = {
        "distinct_parent_authors": int(targets.size),
        "top5_share": float(targets.head(5).sum() / targets.sum()),
        "hhi": _hhi(targets),
        "gini": _gini(targets),
        "repeat_targets_3plus": int((targets >= 3).sum()),
        "one_off_targets": int((targets == 1).sum()),
    }
    # Downstream: views earned by comments (exposure) — heavy-tailed, so show both.
    out["exposure"] = {
        "total_views_from_comments": float(conv["views"].sum()),
        "top_comment_share_of_comment_views": float(conv["views"].max() / conv["views"].sum())
        if conv["views"].sum() else None,
    }
    cols = ["tweet_id", "url", "created_at", "parent_author", "text", "category", "topic", "views", "likes",
            "replies", "effectiveness"]
    best = conv.sort_values("effectiveness", ascending=False).head(10)
    worst = conv.sort_values("effectiveness").head(10)
    top_views = conv.sort_values("views", ascending=False).head(10)

    def rows(g: pd.DataFrame) -> list[dict]:
        g = g[[c for c in cols if c in g.columns]].copy()
        g["created_at"] = g["created_at"].dt.strftime("%Y-%m-%d")
        return g.replace({np.nan: None}).to_dict("records")

    out["examples"] = {"highest_score": rows(best), "lowest_score": rows(worst), "most_viewed": rows(top_views)}
    # Answers to the brief's commenting questions, with data availability.
    out["questions"] = _answers(out, conv, df)
    out["scored_replies"] = rows(conv.sort_values("created_at"))
    out["engagers"] = engager_report(handle, conv)
    return out


def _answers(out: dict, conv: pd.DataFrame, df: pd.DataFrame) -> list[dict]:
    c = out["conversation"]
    sub = float(conv["category"].isin(SUBSTANTIVE).mean()) if "category" in conv else None
    rel = float(conv["relevant_to_icp"].fillna(False).astype(bool).mean()) if "relevant_to_icp" in conv else None
    return [
        {"q": "Are the accounts commenting on relevant posts?",
         "answer": None if rel is None else f"{rel:.0%} of conversational comments are on ICP-relevant subjects "
                                            "(judged from reply text; parent post unavailable).",
         "evidence_class": "account_observed"},
        {"q": "Are replies early enough to participate in active discussions?",
         "answer": (f"In a sample of {out['thread_sample']['n']} recent comments with thread context, the median "
                    f"delay after the parent post was {out['thread_sample']['latency_minutes']['median']:.0f} "
                    f"minutes; {out['thread_sample']['share_within_60min']:.0%} were within the first hour.")
         if out.get("thread_sample") else
         "Insufficient data: parent post timestamps are not available, so reply latency cannot be measured.",
         "evidence_class": "account_observed" if out.get("thread_sample") else "insufficient"},
        {"q": "Do parent authors respond?",
         "answer": (f"{out['thread_sample']['parent_author_responded_share']:.0%} of sampled comments got a visible "
                    "reply from the parent author.") if out.get("thread_sample") else
         "Not observable without thread context.",
         "evidence_class": "account_observed" if out.get("thread_sample") else "insufficient"},
        {"q": "Are comments substantive or repetitive?",
         "answer": None if sub is None else f"{sub:.0%} substantive (insight, expertise, question, "
                                            "disagreement, experience); see category mix.",
         "evidence_class": "account_observed"},
        {"q": "Are replies attracting new people or the same small group?",
         "answer": f"{out['concentration']['distinct_parent_authors']} distinct accounts commented on; the top 5 "
                   f"receive {out['concentration']['top5_share']:.0%} of comments. Who engages *with* the "
                   "comments is not observable without engager collection.",
         "evidence_class": "account_observed"},
        {"q": "Is reply activity associated with follower growth?",
         "answer": "Insufficient data: no follower-count history exists yet (monitoring will create it).",
         "evidence_class": "insufficient"},
        {"q": "Typical exposure per comment",
         "answer": f"median {c['views']['median']:.0f} views per conversational comment (n={c['n']}).",
         "evidence_class": "account_observed"},
    ]


def engager_report(handle: str, conv: pd.DataFrame | None = None) -> dict:
    """Who publicly replied to / quoted the account (likes are not exposed), and reciprocity."""
    from sqlalchemy import select

    from xaudit.db.models import Engager
    from xaudit.db.session import session

    with session() as s:
        rows = s.execute(select(Engager.engager_handle, Engager.created_at, Engager.kind)
                         .where(Engager.client_handle == handle)).all()
    if not rows:
        return {"available": False, "note": "No engager data collected."}
    e = pd.DataFrame(rows, columns=["engager", "created_at", "kind"])
    counts = e["engager"].value_counts()
    targets = set(conv["parent_author"].dropna()) if conv is not None else set()
    top = []
    for h, n in counts.head(25).items():
        top.append({"handle": h, "engagements": int(n), "account_comments_on_them": bool(h in targets)})
    return {
        "available": True,
        "n_engagements": int(len(e)),
        "distinct_engagers": int(counts.size),
        "one_time_share": float((counts == 1).sum() / counts.size),
        "repeat_engagers_3plus": int((counts >= 3).sum()),
        "top10_share": float(counts.head(10).sum() / counts.sum()),
        "reciprocal_accounts": int(len(set(counts.index) & targets)),
        "reciprocal_share_of_engagements": float(e["engager"].isin(targets).mean()),
        "top": top,
        "window": [str(e["created_at"].min())[:10], str(e["created_at"].max())[:10]],
        "note": "Public replies/quotes that mention the account (since 2026-07-25), from the console store; "
                "includes replies to the account's comments elsewhere. Likes and reposts are not exposed.",
    }
