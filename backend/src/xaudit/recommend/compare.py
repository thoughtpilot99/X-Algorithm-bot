"""Report C inputs (cross-account comparison) and the 14 final answers per account."""

from __future__ import annotations

from xaudit.algo import registry
from xaudit.db.session import load_artifact, save_artifact
from xaudit.settings import clients


def _get(d: dict | None, *path, default=None):  # noqa: ANN001, ANN002, ANN202
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return default
        d = d[p]
    return d


def _seg(segs: list[dict], feature: str, level: str) -> dict | None:
    return next((s for s in segs or [] if s["feature"] == feature and str(s["level"]) == level), None)


def account_metrics(h: str) -> dict:
    reach = load_artifact("reach_90d", h) or {}
    reach180 = load_artifact("reach", h) or {}
    bench = load_artifact("benchmark", h) or {}
    com = load_artifact("comments", h) or {}
    cad = load_artifact("cadence", h) or {}
    segs = load_artifact("segments", h) or []
    prof = load_artifact("profile", h) or {}
    client = _get(bench, "accounts", h, default={}) or {}
    art = _seg(segs, "format", "x_article")
    share = _get(com, "category_share", default={}) or {}
    sub = sum(v for k, v in share.items() if k in {"original_insight", "expert_explanation",
                                                    "constructive_disagreement", "question", "personal_experience"})
    return {
        "handle": h,
        "followers": prof.get("followers"),
        "authored_median_views_90d": _get(reach, "segments", "authored (original + quote)", "median"),
        "median_views_per_1k_followers": client.get("median_views_per_1k_followers"),
        "median_eng_per_1k_views": client.get("median_eng_per_1k_views"),
        "median_replies_per_1k": client.get("median_replies_per_1k"),
        "median_bookmarks_per_1k": client.get("median_bookmarks_per_1k"),
        "median_likes_per_1k": client.get("median_likes_per_1k"),
        "authored_per_week": _get(cad, "frequency", "authored_per_week"),
        "replies_per_week": _get(cad, "frequency", "replies_per_week"),
        "share_article": client.get("share_article"),
        "article_lift": art.get("ratio") if art and art.get("tested") else None,
        "trend_per_30d": _get(reach180, "trend_authored", "per_30d"),
        "trend_ci": [_get(reach180, "trend_authored", "lo"), _get(reach180, "trend_authored", "hi")],
        "top5pct_share_of_views": _get(reach180, "concentration", "top5pct_share_of_views"),
        "conversational_comments": _get(com, "conversation", "n"),
        "median_views_per_comment": _get(com, "conversation", "views", "median"),
        "substantive_comment_share": sub,
        "fulfilment_replies": _get(com, "fulfilment", "n"),
        "comment_top5_share": _get(com, "concentration", "top5_share"),
        "third_post_vs_baseline": _get(cad, "same_day_order", "3rd+", "median"),
        "third_post_n": _get(cad, "same_day_order", "3rd+", "n"),
    }


def compare() -> dict:
    hs = list(clients())
    metrics = {h: account_metrics(h) for h in hs}
    diag = {h: {d["id"].split("-", 1)[1]: d for d in (load_artifact("diagnostics", h) or {}).get("items", [])}
            for h in hs}
    shared, specific = [], []
    for key in sorted({k for d in diag.values() for k in d}):
        statuses = {h: diag[h].get(key, {}).get("status") for h in hs}
        issue = next((diag[h][key]["issue"] for h in hs if key in diag[h]), key)
        row = {"diagnostic": key, "issue": issue, "status": statuses}
        if all(s in ("supported", "mixed") for s in statuses.values()):
            shared.append(row)
        elif any(s in ("supported", "mixed") for s in statuses.values()):
            specific.append(row)
    a, b = hs[0], hs[1]
    ma, mb = metrics[a], metrics[b]
    transfer = []
    if (ma.get("median_bookmarks_per_1k") or 0) > (mb.get("median_bookmarks_per_1k") or 0) * 1.5:
        transfer.append({"from": a, "to": b, "strategy": "Reference-style posts that earn saves",
                         "basis": "bookmarks per 1k views"})
    if (mb.get("median_bookmarks_per_1k") or 0) > (ma.get("median_bookmarks_per_1k") or 0) * 1.5:
        transfer.append({"from": b, "to": a, "strategy": "Reference-style tutorials/playbooks that earn saves "
                         "(bookmark rate)", "basis": "bookmarks per 1k views"})
    for x, y in ((a, b), (b, a)):
        if (metrics[x].get("share_article") or 0) > (metrics[y].get("share_article") or 0) * 1.5 and \
                (metrics[y].get("article_lift") or 0) > 1.5:
            transfer.append({"from": x, "to": y, "strategy": "Higher X Article cadence",
                             "basis": f"{y}'s own articles already outperform its other formats "
                                      f"({metrics[y]['article_lift']:.1f}x) but make up a smaller share of output"})
        if (metrics[x].get("median_views_per_comment") or 0) > (metrics[y].get("median_views_per_comment") or 0) * 1.3:
            transfer.append({"from": x, "to": y, "strategy": "Comment selection/format that earns more views per comment",
                             "basis": "median views per conversational comment"})
    out = {"accounts": metrics, "shared_issues": shared, "account_specific_issues": specific,
           "transferable": transfer,
           "notes": ["Normalised metrics use views per 1,000 followers and engagement per 1,000 views; follower counts "
                     "are a single 2026-10-23 snapshot.",
                     "The two accounts interact heavily (each is among the other's most-replied-to accounts), so their "
                     "audiences overlap; transferability is judged per account, never by pooling metrics."]}
    save_artifact("comparison", out)
    return out


def final_answers(h: str) -> list[dict]:
    """The brief's 14 questions, answered from artifacts with evidence class labels."""
    reach = load_artifact("reach", h) or {}
    diags = {d["id"].split("-", 1)[1]: d for d in (load_artifact("diagnostics", h) or {}).get("items", [])}
    rec = load_artifact("recommendations", h) or {}
    com = load_artifact("comments", h) or {}
    segs = load_artifact("segments", h) or []
    cad = load_artifact("cadence", h) or {}
    bench = load_artifact("benchmark", h) or {}
    hi = sorted([s for s in segs if s["signal"] == "higher" and s["feature"] in ("format", "topic", "narrative")],
                key=lambda s: -s["ratio"])[:4]
    lo = sorted([s for s in segs if s["signal"] == "lower" and s["feature"] in ("format", "topic", "narrative")],
                key=lambda s: s["ratio"])[:4]
    seg_txt = lambda ss: "; ".join(f"{s['feature']}={s['level']} {s['ratio']:.2f}x (n={s['n']})" for s in ss) or "none clear"  # noqa: E731
    beh = [s for s in segs if s["feature"] in ("weekday", "daypart_utc", "length_bucket", "has_list", "has_question")
           and s["signal"] in ("higher", "lower")]
    claims = registry.claims()
    unsupported = [c for c in claims if c["verdict"] in ("not_found_in_repo", "contradicted")]
    comp = {c["metric"]: c for c in bench.get("comparison", [])}
    root = rec.get("root_causes", [])
    actions = rec.get("actions", {})
    plan = rec.get("plan", {}).get("experiments", [])
    seg_a = reach.get("segments", {}).get("authored (original + quote)", {})
    return [
        {"q": "Why is the account receiving its current level of reach?",
         "a": (f"Median authored post: {seg_a.get('median', 0):.0f} views (n={seg_a.get('n')}). Ranked potential "
               "drivers: " + "; ".join(f"{r['rank']}. {r['issue']} ({r['confidence']})" for r in root)),
         "class": "statistical_association"},
        {"q": "Which content types perform best and worst?", "a": f"Best: {seg_txt(hi)}. Worst: {seg_txt(lo)}.",
         "class": "statistical_association"},
        {"q": "Which posting behaviours are associated with better results?",
         "a": (seg_txt(beh) + ". Same-day order (median vs baseline): " +
               ", ".join(f"{k} {v.get('median', 0):.2f}x (n={v.get('n')})"
                         for k, v in cad.get("same_day_order", {}).items())),
         "class": "statistical_association"},
        {"q": "Is the commenting strategy effective?", "a": diags.get("comments", {}).get("observation", "n/a"),
         "class": "account_observed"},
        {"q": "Which interactions are producing meaningful audience exposure?",
         "a": "Top comment targets by views: " + ", ".join(
             f"@{p['parent_author']} ({p['replies']} comments, median {p['median_views']:.0f} views)"
             for p in sorted(com.get("partners", []), key=lambda p: -p["median_views"])[:5] if p["replies"] >= 2),
         "class": "account_observed"},
        {"q": "Are there observable signs of potential visibility limitations?",
         "a": diags.get("visibility", {}).get("observation", "n/a"), "class": "insufficient"},
        {"q": "What does the published X algorithm actually tell us?",
         "a": ("Ranking is a weighted sum of per-viewer predicted action probabilities (reply 5.0, like 0.66, "
               "share-via-copy-link 20.0, follow 4.0, profile click 0.0, report -234.0 in published defaults), with "
               "author-diversity decay within a feed, a 0.75 out-of-network factor, a 48-hour age cutoff and "
               "candidate retrieval driven by viewers' engagement history. See the findings registry."),
         "class": "repo_verified"},
        {"q": "Which common algorithm claims are unsupported?",
         "a": "; ".join(f"{c['claim']} ({c['verdict'].replace('_', ' ')})" for c in unsupported[:10]),
         "class": "unsupported"},
        {"q": "How does the account compare with relevant peers?",
         "a": "; ".join(f"{k.replace('median_', '').replace('_', ' ')}: {v['client']:.2f} vs peer median "
                        f"{v['peer_median']:.2f}" for k, v in comp.items()
                        if v.get("client") is not None and v.get("peer_median") is not None
                        and k in ("median_views_per_1k_followers", "median_eng_per_1k_views", "median_replies_per_1k",
                                  "median_bookmarks_per_1k", "authored_per_week")),
         "class": "statistical_association"},
        {"q": "What should the account stop doing?", "a": "; ".join(x["action"] for x in actions.get("stop", [])),
         "class": "statistical_association"},
        {"q": "What should the account continue doing?",
         "a": "; ".join(x["action"] for x in actions.get("continue", [])), "class": "statistical_association"},
        {"q": "What should the account start doing?", "a": "; ".join(x["action"] for x in actions.get("start", [])),
         "class": "hypothesis"},
        {"q": "Which changes should be tested first?",
         "a": "; ".join(f"Week {e['week']}: {e['title']}" for e in plan if e["week"] <= 2), "class": "hypothesis"},
        {"q": "How will we measure whether those changes work?",
         "a": ("Each experiment has a primary metric and decision rule (see 30-day plan); judged on medians of views "
               "vs trailing baseline, replies/bookmarks per 1k views. " + rec.get("plan", {}).get("power", {}).get("note", "")),
         "class": "hypothesis"},
    ]
