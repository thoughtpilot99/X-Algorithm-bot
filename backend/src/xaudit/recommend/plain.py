"""Plain-English summary of an account's audit ("the short version").

Built only from stored artifacts and the posts table, so every number traces back to
the detailed analysis. Weights and constants quoted from X's published code are read
from the parameter extract at the studied commit, never typed in. No statistical
jargon: "typical post" stands for the median, "usual" for the account's own trailing
baseline, and certainty is said in words.
"""

from __future__ import annotations

import math
import re

import pandas as pd

from xaudit.db.session import load_artifact, save_artifact
from xaudit.settings import analysis_cfg, clients

CLASS_PLAIN = {
    "repo_verified": "Proven in X's published code",
    "account_observed": "Seen in your data",
    "statistical_association": "Pattern in your data (not proof of cause)",
    "hypothesis": "Idea to test",
    "unsupported": "Not supported",
    "insufficient": "Not enough data",
}
SURE_PLAIN = {"high": "We're fairly sure", "medium": "We're somewhat sure", "low": "We're not sure"}

FORMAT_PLAIN = {"x_article": "X Articles", "short_post": "Short posts", "long_post": "Long posts",
                "quote_post": "Quote posts", "thread": "Threads", "media_post": "Image/video posts",
                "link_post": "Link posts", "poll": "Polls"}
FEATURE_PLAIN = {
    "topic": "Posts about {level}",
    "hook_type": "Posts that open with a {level} hook",
    "narrative": "Posts written as {level}",
    "length_bucket": "{level} posts",
    "has_list": "Posts with list formatting",
    "has_numbers": "Posts that include numbers",
    "has_question": "Posts that ask a question",
    "uses_data": "Posts that use data",
    "personal_experience": "Posts about personal experience",
    "promotional": "Promotional posts",
    "keyword_cta": "Posts asking people to comment a keyword",
    "has_cta": "Posts with a call to action",
    "has_tco_url": "Posts with a link or media",
    "tco_url_excl_articles": "Posts with a link or media",
    "opinion_strength": "Posts with opinion strength {level} out of 3",
    "educational_value": "Posts with educational value {level} out of 3",
    "weekday": "Posts published on {level}",
    "daypart_utc": "Posts published {level} UTC",
}
GLOSSARY = [
    ("Typical post", "The middle post: half of the posts got more views, half got fewer. "
                     "One viral post can't distort it the way an average can."),
    ("Usual", "What the account's posts were getting in the weeks just before. A post at 2× usual did twice as "
              "well as the account normally does at that time."),
    ("Proven in X's published code", "We read it in the source code xAI published (file and line cited). "
                                     "The published code is not guaranteed to be everything X runs."),
    ("Seen in your data", "Counted directly from the account's public posts."),
    ("Pattern in your data (not proof of cause)",
     "Posts with this feature did better or worse, but other things may explain it."),
    ("Idea to test", "A reasoned suggestion that the data can't confirm yet."),
]


# The diagnostics' recommendation and success criterion, said plainly (same advice, no statistics).
PLAIN_DO = {
    "format": "Make X Articles the main format, each with a strong native post introducing it. Turn short "
              "standalone posts into Article teasers or replies.",
    "efficiency": "End posts with a specific question people can answer, tied to the post's point, and reply to "
                  "the first commenters within an hour to keep the conversation going.",
    "comments": "Swap generic 'great post' comments for 2–3 sentences of real expertise on bigger accounts in "
                "the niche, within the first hour of their post. Keep friendly comments, drop emoji-only ones.",
    "stacking": "Post at most 2 times a day, at least 6 hours apart. Put extra ideas in replies, threads or "
                "the next day.",
    "topics": "Post mainly on the topics that do better; move off-topic posts into replies.",
    "hooks": "Open with the concrete result or the how-to promise; avoid vague observations or opinion-only "
             "openers.",
    "trend": "Track each format's typical views week by week, so a change in the mix of formats isn't "
             "mistaken for falling reach. Look again after 4 weeks of daily tracking.",
    "concentration": "Study the best posts and turn what they share into a repeatable template. Judge changes "
                     "by the typical post, not by the occasional hit.",
    "fulfilment": "Keep the lead magnets, but deliver them in one pinned reply or by DM instead of hundreds of "
                  "identical public replies, or add a short personal line to each.",
    "links": "Don't restructure posts around a 'link penalty'. If you want to test it, put the link in a "
             "reply on half of link posts and compare.",
    "visibility": "Don't act on shadowban theories. Investigate only if views drop by more than half in one "
                  "week across every format.",
}
PLAIN_TITLE = {
    "format": "The format you post in matters most",
    "efficiency": "Posts get seen but not answered",
    "comments": "Comments are thin and go to the same few people",
    "stacking": "Too many posts on the same day",
    "topics": "Off-topic posts do worse",
    "hooks": "Weak openings",
    "trend": "Reach is drifting down",
    "concentration": "Reach comes from rare viral hits",
    "fulfilment": "Hundreds of identical 'Sent' replies",
    "links": "Links (a common claim, checked)",
    "visibility": "Signs of visibility limits (checked)",
}
PLAIN_CHECK = {
    "format": "Article posts keep their lead over other formats while posting volume stays the same.",
    "efficiency": "Replies per 1,000 views move toward what similar accounts get.",
    "comments": "Most comments add real substance, and a typical comment is seen by more people than now.",
    "stacking": "No more days with 3+ posts, with total weekly views not falling.",
    "topics": "A bigger share of posts in the stronger topics, without their typical views dropping.",
    "hooks": "The better openings keep doing better in a controlled 4-week test.",
    "trend": "Typical weekly views for each format stop falling for 4 weeks in a row.",
    "concentration": "More posts reach twice the usual, without the typical post getting fewer views.",
    "fulfilment": "Lead-magnet sign-ups hold up with far fewer identical public replies.",
    "links": "The link-in-reply test shows a clear difference, or doesn't.",
    "visibility": "No unexplained drop across every format at once.",
}


# ---------------------------------------------------------------------------
# Number wording
def views(v: float | None) -> str:
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:,.0f}"


def times(r: float) -> str:
    """Ratio of typical views in plain words."""
    if r >= 1.15:
        return f"about {r:.1f} times as many views" if r < 10 else f"about {round(r)} times as many views"
    if r <= 0.87:
        return f"only about {round(r * 100)}% as many views"
    return "about the same views"


def pct(x: float) -> str:
    return f"{round(x * 100)}%"


def level_text(level: str) -> str:
    return str(level).replace("_", " ").replace("(0-3)", "").strip()


def subject(seg: dict) -> str:
    f, lv = seg["feature"], str(seg["level"])
    if f == "format":
        return FORMAT_PLAIN.get(lv, level_text(lv).capitalize() + " posts")
    lvl = level_text(lv).removesuffix(".0")
    if f == "length_bucket":
        m = re.match(r"([a-z ]+?)\s*\((.*)\)", lvl)
        if m:
            words = m.group(2).replace("<", "under ").replace("-", "–").replace(" words", "")
            return f"{m.group(1).capitalize()} posts ({words} words)"
        return f"{lvl.capitalize()} posts"
    if f == "topic" and lvl in ("other", "other/rare"):
        return "Posts on other, uncategorised topics"
    if f == "hook_type":
        art = "an" if lvl[:1] in "aeiou" else "a"
        return f"Posts that open with {art} {lvl} hook"
    return FEATURE_PLAIN.get(f, seg["feature_label"] + ": {level}").format(level=lvl)


def _month(ym: str) -> str:
    try:
        return pd.Timestamp(ym + "-01").strftime("%B %Y")
    except ValueError:
        return ym


def lower_first(t: str) -> str:
    return t[:1].lower() + t[1:]


# ---------------------------------------------------------------------------
# What X's published code does, in plain words. Numbers come from the parameter extract.
def _params() -> dict[str, float]:
    try:
        from xaudit.algo import param_extract
        rows = [p for p in param_extract.current() if p.get("value") is not None]
    except Exception:  # noqa: BLE001  (repo not synced locally)
        return {}
    # home-mixer's defaults are the published weights used everywhere else in the audit; other files
    # (vm-ranker) only fill names home-mixer doesn't define (author diversity, out-of-network factor).
    out: dict[str, float] = {}
    for p in sorted(rows, key=lambda r: not r["path"].startswith("home-mixer")):
        out.setdefault(p["name"], p["value"])
    return out


def _w(p: dict, name: str) -> str | None:
    v = p.get(name)
    if v is None:
        return None
    return f"{v:g}"


def algo_plain(kind: str, p: dict) -> str:
    reply, like, link = _w(p, "ReplyWeight"), _w(p, "FavoriteWeight"), _w(p, "ShareViaCopyLinkWeight")
    quote, follow = _w(p, "QuoteWeight"), _w(p, "FollowAuthorWeight")
    mutual = _w(p, "BidirectionalFollowReplyWeightBoost")
    decay, floor = p.get("AuthorDiversityDecay"), p.get("AuthorDiversityFloor")
    oon = _w(p, "OonWeightFactor")
    weights = (f"Sharing a post by copying its link counts {link}, a reply {reply}, a quote {quote}, following the "
               f"author {follow}, a like {like}." if all((link, reply, quote, follow, like)) else "")
    base = ("For every viewer, X's ranking predicts how likely they are to like, reply, share, follow or spend time "
            "on a post, and adds those predictions up with fixed weights. ")
    if kind == "format":
        return (base + weights + " There is no special boost for X Articles in the published code; formats that "
                "earn the heavily weighted actions (shares, replies, time spent reading) rank higher.")
    if kind in ("efficiency", "conversation"):
        rel = f" — about {float(reply) / float(like):.1f} times a like ({like})" if reply and like else ""
        extra = (f" When the viewer and the author follow each other, a reply on an original post counts {mutual} "
                 "more on top." if mutual else "")
        return (f"A predicted reply counts {reply}{rel}.{extra} So a post that people are likely to reply to is "
                "ranked higher for the next viewers; a post that gets read but not answered is not.")
    if kind == "stacking" and decay is not None and floor is not None:
        m = [round((1 - floor) * decay ** k + floor, 3) for k in range(3)]
        return (f"When several posts from the same author compete in one viewer's feed, X scores the first at "
                f"{m[0]:g}×, the second at {m[1]:g}×, the third at {m[2]:g}× and later ones down towards {floor:g}× "
                "(author diversity). Several posts in a short time compete with each other for the same viewers.")
    if kind == "comments":
        return (f"Posts from accounts a viewer doesn't follow are scored at {oon}× in For You, and replies from "
                "accounts the viewer doesn't follow are mostly filtered out of For You. So a comment is seen mainly "
                "by people reading that thread: its reach comes from the post it sits under.")
    if kind == "topics":
        return ("X finds posts for each viewer from what that viewer engaged with recently (two retrieval systems, "
                "Phoenix and SimClusters, both seeded by the viewer's recent likes, replies and reads). Staying on "
                "consistent topics makes it more likely the right viewers have related history and get shown "
                "your posts.")
    if kind == "trend":
        return ("Retrieval follows each viewer's recent engagement. If fewer people engaged with the account "
                "recently, fewer viewers carry it in their history, so fewer are shown new posts.")
    if kind == "concentration":
        cap = _w(p, "ColdStartFollowerCap")
        lift = (f" Fresh original posts from authors with up to {int(float(cap)):,} followers can get a one-off "
                "'cold start' lift into some feeds." if cap else "")
        return ("A post enters some of X's retrieval indexes when it gets liked, so early likes decide whether it "
                "is found by new viewers at all." + lift + " Breakouts happen when early viewers react strongly.")
    if kind == "hooks":
        return (base + "Time spent on a post and opening it are counted, and scrolling straight past ('not dwelled') "
                "counts against it. The first lines decide whether people stop.")
    if kind == "fulfilment":
        return ("X's published spam rules group replies with identical text and can label them 'copy-paste spam' "
                "(some rules are not published). We cannot see whether these replies are labelled or what a label "
                "would do; it is a risk to manage, not a penalty we observed.")
    if kind == "links":
        return ("The published code has no penalty for links. The ranking does count predicted link opens as a "
                "small positive.")
    if kind == "visibility":
        return ("X's visibility rules can hide or label posts, but their decisions aren't public. Nothing in this "
                "account's numbers looks like a sudden restriction.")
    return ""


# ---------------------------------------------------------------------------
# What we see, in plain words (numbers from the diagnostic's own evidence)
def _ev(d: dict, ref: str):  # noqa: ANN202
    return next((e["value"] for e in d["evidence"] if e["ref"] == ref), None)


def what_we_see(d: dict, kind: str, ctx: dict) -> str:
    seg = ctx["seg"]
    if kind == "format":
        s = seg("format", "x_article")
        if s and s.get("median_rest"):
            out = (f"A typical X Article post gets {views(s['median'])} views; a typical other post gets "
                   f"{views(s['median_rest'])} — {times(s['ratio'])} (based on {s['n']} Articles).")
            weak = [x for x in ctx["segments"] if x["feature"] == "format" and x["signal"] == "lower"]
            if weak:
                out += " Weakest formats: " + "; ".join(
                    f"{lower_first(subject(w))} get {views(w['median'])} views typically" for w in weak) + "."
            return out
    if kind == "efficiency":
        r, rp = _ev(d, "median_replies_per_1k.client"), _ev(d, "median_replies_per_1k.peers")
        lk, lkp = _ev(d, "median_likes_per_1k.client"), _ev(d, "median_likes_per_1k.peers")
        bm, bmp = _ev(d, "median_bookmarks_per_1k.client"), _ev(d, "median_bookmarks_per_1k.peers")
        parts = [f"For every 1,000 people who see a post, it gets about {r:g} replies; similar accounts get {rp:g}"]
        if lk is not None:
            parts.append(f"{lk:g} likes vs {lkp:g}")
        if bm is not None:
            parts.append(f"{bm:g} bookmarks vs {bmp:g}")
        return "; ".join(parts) + "."
    if kind == "comments":
        n, mv = _ev(d, "comments.n"), _ev(d, "comments.median_views")
        sub, low, top5 = _ev(d, "comments.substantive_share"), _ev(d, "comments.low_value_share"), _ev(d, "comments.top5_share")
        return (f"{views(n)} comments on other people's posts in the period. A typical comment is seen by about "
                f"{views(mv)} people. {pct(sub)} add real substance; {pct(low)} are generic, repetitive or jokes. "
                f"{pct(top5)} of comments go to the same 5 accounts.")
    if kind == "stacking":
        first, third = _ev(d, "same_day_order.1st"), _ev(d, "same_day_order.3rd")
        n3 = _ev(d, "same_day_order.3rd.n")
        return (f"The first post of a day does {first:.1f}× the account's usual; the third or later post that day "
                f"does {third:.1f}× (based on {views(n3)} posts).")
    if kind == "trend":
        per, lo, hi = _ev(d, "trend_authored.per_30d"), _ev(d, "trend_authored.lo"), _ev(d, "trend_authored.hi")
        first = next((e for e in d["evidence"] if e["ref"].startswith("monthly.")), None)
        last = [e for e in d["evidence"] if e["ref"].startswith("monthly.")][-1:]
        change = (f"Reach is falling about {round((1 - per) * 100)}% a month" if per < 1 else
                  f"Reach is growing about {round((per - 1) * 100)}% a month")
        if lo is not None and hi is not None and lo <= 1 <= hi:
            change += ", but that is within normal ups and downs"
        months = (f" A typical post got {views(first['value'])} views in {_month(first['ref'][8:])} and "
                  f"{views(last[0]['value'])} in {_month(last[0]['ref'][8:])}." if first and last else "")
        return change + "." + months
    if kind == "concentration":
        top1, below, above = _ev(d, "top1_share"), _ev(d, "share_below_half"), _ev(d, "share_above_2x")
        return (f"One post brought in {pct(top1)} of all views in the period. {pct(below)} of posts got less than "
                f"half the account's usual and {pct(above)} more than twice it, so reach comes in rare spikes.")
    if kind in ("topics", "hooks"):
        rows = [s for s in ctx["content_segs"] if s["signal"] in ("higher", "lower")
                and s["feature"] in (("topic",) if kind == "topics" else ("hook_type", "narrative", "educational_value"))]
        if rows:
            good = [s for s in rows if s["signal"] == "higher"][:3]
            bad = [s for s in rows if s["signal"] == "lower"][:3]
            bits = []
            if good:
                bits.append("Doing better: " + "; ".join(f"{lower_first(subject(s))} ({views(s['median'])} views typically)"
                                                        for s in good))
            if bad:
                bits.append("Doing worse: " + "; ".join(f"{lower_first(subject(s))} ({views(s['median'])} views typically)"
                                                       for s in bad))
            note = " (comparing posts other than X Articles)" if ctx["scoped"] else ""
            return ". ".join(bits) + note + "."
    if kind == "fulfilment":
        n, pw, rec = _ev(d, "fulfilment.n"), _ev(d, "fulfilment.per_week"), _ev(d, "fulfilment.recipients")
        return (f"{views(n)} near-identical public replies ('Sent', 'Here you go') to {views(rec)} people, about "
                f"{pw:g} a week — delivering lead magnets to people who commented a keyword.")
    return d["observation"]


# ---------------------------------------------------------------------------
def _examples(df: pd.DataFrame, seg: dict, scoped: bool, best: bool, seen: set, k: int = 2) -> list[dict]:
    a = df[df["is_authored"] & df["mature"] & df["views"].notna()]
    if scoped:
        a = a[a["format"] != "x_article"]
    f = seg["feature"]
    if f not in a.columns:
        return []
    a = a[(a[f].astype(str) == str(seg["level"])) & ~a["tweet_id"].isin(seen)]
    a = a.sort_values("views", ascending=not best).head(k)
    seen.update(a["tweet_id"])  # each example post is shown once across the summary
    def label(r) -> str:  # noqa: ANN001
        t = " ".join(str(r["text"]).split())
        title = r.get("article_title")
        if isinstance(title, str) and title.strip() and (t.startswith("https://t.co/") or not t):
            return f"X Article: {title.strip()}"
        if re.fullmatch(r"https://t\.co/\S+", t):
            return "(the post is only a link)"
        return t[:160]

    return [{"text": label(r), "views": float(r["views"]), "url": r["url"],
             "date": r["created_at"].strftime("%d %b %Y"),
             "vs_usual": float(r["vs_baseline"]) if pd.notna(r.get("vs_baseline")) else None}
            for _, r in a.iterrows()]


def _finding(item: dict, scoped: bool, df: pd.DataFrame, best: bool, seen: set) -> dict:
    s = item
    scope = " (comparing posts other than X Articles)" if scoped else ""
    return {
        "headline": subject(s),
        "detail": (f"A typical one gets {views(s['median'])} views vs {views(s['median_rest'])} for the account's "
                   f"other posts — {times(s['ratio'])}{scope}."),
        "based_on": f"Based on {s['n']} posts",
        "label": CLASS_PLAIN["statistical_association"],
        "examples": _examples(df, s, scoped, best, seen),
    }


def build_brief(handle: str) -> dict:
    from xaudit.analysis.pipeline import prepare

    df = prepare(handle, window_days=analysis_cfg()["extended_window_days"])
    reach = load_artifact("reach", handle) or {}
    segs = load_artifact("segments", handle) or []
    segs_ex = load_artifact("segments_ex_articles", handle) or []
    bench = load_artifact("benchmark", handle) or {}
    cad = load_artifact("cadence", handle) or {}
    rec = load_artifact("recommendations", handle) or {}
    diags = (load_artifact("diagnostics", handle) or {}).get("items", [])
    prof = load_artifact("profile", handle) or {}
    p = _params()

    def seg(feature: str, level: str) -> dict | None:
        return next((s for s in segs if s["feature"] == feature and str(s["level"]) == level), None)

    art = seg("format", "x_article")
    scoped = bool(art and art.get("signal") == "higher" and segs_ex)
    content = segs_ex if scoped else segs
    ctx = {"seg": seg, "segments": segs, "content_segs": content, "scoped": scoped}

    # 1. Where the account stands
    au = reach.get("segments", {}).get("authored (original + quote)", {})
    vb = reach.get("vs_baseline", {})
    tr = reach.get("trend_authored", {})
    a = df[df["is_authored"] & df["views"].notna()]
    best = a.sort_values("views", ascending=False).head(1)
    ppw = (cad.get("frequency") or {}).get("authored_per_week")
    stand = [
        f"A typical post gets {views(au.get('median'))} views (half of posts get more, half get fewer), "
        f"based on {au.get('n', 0)} posts over {analysis_cfg()['extended_window_days']} days.",
        f"{views(prof.get('followers'))} followers; about {ppw:.0f} posts a week." if ppw else
        f"{views(prof.get('followers'))} followers.",
    ]
    if len(best):
        b = best.iloc[0]
        stand.append(f"Best post in the period: {views(b['views'])} views ({b['created_at']:%d %b %Y}).")
    if vb:
        stand.append(f"{pct(vb['share_above_2x'])} of posts did more than twice the account's usual; "
                     f"{pct(vb['share_below_half'])} did less than half.")
    if tr.get("per_30d"):
        per = tr["per_30d"]
        steady = tr.get("lo", 0) <= 1 <= tr.get("hi", 0)
        stand.append("Reach over the period: " + (
            "roughly steady (changes are within normal ups and downs)." if steady else
            f"falling about {round((1 - per) * 100)}% a month." if per < 1 else
            f"growing about {round((per - 1) * 100)}% a month."))
    comp = {c["metric"]: c for c in bench.get("comparison", [])}
    peers = []
    for key, what in (("median_replies_per_1k", "replies per 1,000 views"),
                      ("median_eng_per_1k_views", "reactions of any kind per 1,000 views"),
                      ("median_views_per_1k_followers", "views per 1,000 followers"),
                      ("authored_per_week", "posts per week")):
        c = comp.get(key)
        if c and c.get("peer_median"):
            peers.append(f"{what}: {c['client']:.1f} (similar accounts: {c['peer_median']:.1f})")
    if peers:
        stand.append(f"Compared with similar accounts over the last {bench.get('window_days', 90)} days — "
                     + "; ".join(peers) + ".")

    # 2/3. What's working / not working (format from all posts; the rest without Articles)
    def pick(sig: str) -> list[tuple[dict, bool]]:
        f_rows = [s for s in segs if s["feature"] == "format" and s["signal"] == sig]
        o_rows = [s for s in content if s["feature"] not in ("format", "tco_url_excl_articles")
                  and s["signal"] == sig and s["level"] != "False"]
        key = (lambda s: -s["ratio"]) if sig == "higher" else (lambda s: s["ratio"])
        return [(s, False) for s in sorted(f_rows, key=key)] + [(s, scoped) for s in sorted(o_rows, key=key)]

    seen: set = set()
    working = [_finding(s, sc, df, True, seen) for s, sc in pick("higher")[:4]]
    not_working = [_finding(s, sc, df, False, seen) for s, sc in pick("lower")[:4]]

    # 4. Why reach isn't coming
    by_id = {d["id"]: d for d in diags}
    why = []
    for rc in rec.get("root_causes", [])[:5]:
        d = by_id.get(rc["id"], rc)
        kind = d["id"].split("-", 1)[1]
        why.append({
            "title": PLAIN_TITLE.get(kind, d["issue"]),
            "we_see": what_we_see(d, kind, ctx),
            "we_see_label": CLASS_PLAIN.get(d["evidence_class"], d["evidence_class"]),
            "x_code": algo_plain(kind, p),
            "x_code_label": CLASS_PLAIN["repo_verified"],
            "x_code_refs": [{"id": f["id"], "title": f["title"], "url": f["permalink"]} for f in d.get("algo_findings", [])],
            "our_reading": d.get("algo_connection", ""),
            "do": PLAIN_DO.get(kind, d["recommendation"]),
            "check": PLAIN_CHECK.get(kind, d.get("success_criteria", "")),
            "sure": SURE_PLAIN.get(d["confidence"], d["confidence"]),
        })

    # 5. What to do next (from the ranked barriers, plus the 30-day honesty note)
    power = (rec.get("plan") or {}).get("power", {})
    mde = power.get("min_detectable_ratio_30_days")
    todo = [{"action": w["do"], "why": w["x_code"].split(". ")[0] + ".", "check": w["check"]} for w in why]
    honesty = (f"At about {ppw:.0f} posts a week, a 30-day test can only prove a change of about {mde:.1f}× or more "
               "in typical views. Smaller improvements will show a direction, not proof — keep testing."
               if mde and ppw else "")

    brief = {"handle": handle, "name": clients()[handle]["name"], "stand": stand, "working": working,
             "not_working": not_working, "why": why, "todo": todo, "test_note": honesty,
             "glossary": [{"term": t, "meaning": m} for t, m in GLOSSARY]}
    save_artifact("brief", brief, handle)
    return brief
