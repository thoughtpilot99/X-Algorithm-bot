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
         "answer": "Insufficient data: parent post timestamps are not available, so reply latency cannot be "
                   "measured.", "evidence_class": "insufficient"},
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
