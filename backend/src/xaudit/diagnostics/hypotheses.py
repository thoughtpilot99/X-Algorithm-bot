"""Hypothesis checkers: connect observed account behaviour to documented mechanisms.

Each checker reads computed artifacts (never raw guesses), decides whether the
data supports the candidate issue, and returns a Diagnostic whose prose only
uses numbers that are also carried as evidence. Algorithm links point to the
findings registry; a link means "a documented mechanism this could relate to",
never "this mechanism is confirmed to be acting on this account".
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from xaudit.algo import registry
from xaudit.diagnostics.model import Diagnostic, Evidence

Ctx = dict  # {"handle", "df", "art": {kind: payload}}


def _post_ev(df: pd.DataFrame, ids: list[str], label: str) -> list[Evidence]:
    rows = df.set_index("tweet_id").loc[[i for i in ids if i in set(df["tweet_id"])]]
    return [Evidence(kind="post", ref=i, label=f"{label}: {int(r['views']) if pd.notna(r['views']) else 'n/a'} views",
                     value=float(r["views"]) if pd.notna(r["views"]) else None, url=r["url"])
            for i, r in rows.iterrows()]


def _seg(art: dict, feature: str, level: str) -> dict | None:
    return next((s for s in art["segments"] if s["feature"] == feature and str(s["level"]) == level), None)


def _content_segs(art: dict) -> tuple[list[dict], str]:
    """Segments for content questions (topic, hook, structure) and a note on their scope.

    When X Articles clearly out-reach other formats, topic and hook levels in the full set mostly
    re-measure the article effect, so these questions are answered on posts other than Articles.
    """
    art_seg = _seg(art, "format", "x_article")
    if art_seg and art_seg.get("signal") == "higher" and art.get("segments_ex_articles"):
        return art["segments_ex_articles"], " (X Articles set aside)"
    return art["segments"], ""


def _r(x: float | None, nd: int = 2) -> float | int | None:
    if x is None:
        return None
    return int(round(float(x))) if nd == 0 else round(float(x), nd)


def _ids(*terms: str) -> list[str]:
    return registry.lookup(*terms, limit=2)


def _valid(ids: list[str]) -> list[str]:
    known = registry.finding_ids()
    return [i for i in ids if i in known]


# ---------------------------------------------------------------------------
# 1. Reach trend
def reach_trend(ctx: Ctx) -> Diagnostic:
    h, art = ctx["handle"], ctx["art"]
    t = art["reach"]["trend_authored"]
    monthly = [m for m in art["reach"]["monthly"] if m["authored_n"]]
    first, last = monthly[0], monthly[-1]
    declining = t.get("per_30d") is not None and t["hi"] < 1
    mixed = t.get("per_30d") is not None and t["per_30d"] < 1 <= t["hi"]
    pct = _r((1 - t["per_30d"]) * 100, 0) if t.get("per_30d") else None
    obs = (f"Median views on authored posts trend at {_r(t['per_30d'])}x per 30 days "
           f"(90% CI {_r(t['lo'])}–{_r(t['hi'])}, n={t['n']}); monthly medians went from "
           f"{first['authored_median_views']:.0f} ({first['month']}) to {last['authored_median_views']:.0f} "
           f"({last['month']}).") if t.get("per_30d") else "Not enough authored posts to estimate a trend."
    return Diagnostic(
        id=f"{h}-trend", handle=h, issue="Reach trend over the window",
        status="supported" if declining else "mixed" if mixed else "not_supported",
        observation=obs,
        evidence=[Evidence(kind="metric", ref="trend_authored.per_30d", label="Theil–Sen multiplicative trend per 30d",
                           value=_r(t.get("per_30d")), evidence_class="statistical_association"),
                  Evidence(kind="metric", ref="trend_authored.lo", label="trend CI low", value=_r(t.get("lo"))),
                  Evidence(kind="metric", ref="trend_authored.hi", label="trend CI high", value=_r(t.get("hi"))),
                  Evidence(kind="metric", ref="trend_authored.n", label="posts", value=t.get("n")),
                  Evidence(kind="metric", ref=f"monthly.{first['month']}", label="first month median views",
                           value=first["authored_median_views"]),
                  Evidence(kind="metric", ref=f"monthly.{last['month']}", label="last month median views",
                           value=last["authored_median_views"]),
                  *([Evidence(kind="metric", ref="decline_pct", label="implied decline % per 30d", value=pct)]
                    if pct is not None else [])],
        algo_links=_valid(["A04", "A05", "A12"]),
        algo_connection=("Out-of-network retrieval is driven by viewers' recent engagement histories (Phoenix "
                         "two-tower, SimClusters seeds). A sustained decline is consistent with fewer viewers "
                         "having recently engaged with the account, but the repository cannot attribute it."),
        alternatives=["Change in content mix (fewer X Articles or long tutorials in recent months)",
                      "Seasonality / audience attention (summer vs autumn)",
                      "Platform-wide changes in view counting or feed composition (weights changed in Sept–Oct; "
                      "see parameter history)",
                      "Recent posts' views still accruing despite the 72h maturity filter"],
        confidence="medium" if declining else "low",
        impact="Determines whether the priority is recovering lost distribution or growing from a stable base.",
        recommendation=("Track weekly median views for each format separately so a format-mix shift is not "
                        "mistaken for a reach decline; re-run after 4 weeks of monitoring."),
        validation="Format-stratified weekly medians from continuous monitoring; check the trend within X Articles only.",
        evidence_class="statistical_association",
        evidence_strength=0.8 if declining else 0.4, business_relevance=0.9, likely_impact=0.6, ease_of_testing=0.7,
        confounders=["content mix", "seasonality", "platform weight changes", "metric maturity"],
        success_criteria="Weekly authored median views stop declining for 4 consecutive weeks (format-adjusted).",
    )


# ---------------------------------------------------------------------------
# 2. Format: X Articles and long tutorials vs short / opinion posts
def format_effects(ctx: Ctx) -> Diagnostic:
    h, art, df = ctx["handle"], ctx["art"], ctx["df"]
    a = _seg(art, "format", "x_article")
    mv = art["multivariable"]
    coef = next((c for c in mv.get("coefficients", []) if c["term"] == "C(format)[T.x_article]"), None)
    weak = sorted([s for s in art["segments"] if s["feature"] == "format" and s["signal"] == "lower"],
                  key=lambda s: s["ratio"])
    ev = []
    if a and a.get("tested"):
        ev += [Evidence(kind="comparison", ref="format=x_article", label="X Article median / other authored median",
                        value=_r(a["ratio"]), evidence_class="statistical_association"),
               Evidence(kind="metric", ref="x_article.n", label="X Article posts", value=a["n"]),
               Evidence(kind="metric", ref="x_article.ci", label="ratio CI", value=f"{_r(a['lo'])}-{_r(a['hi'])}"),
               Evidence(kind="metric", ref="x_article.q", label="BH q-value", value=_r(a["q"], 3))]
    for w in weak:
        ev.append(Evidence(kind="comparison", ref=f"format={w['level']}", label=f"{w['level']} median ratio",
                           value=_r(w["ratio"]), evidence_class="statistical_association"))
        ev.append(Evidence(kind="metric", ref=f"{w['level']}.n", label=f"{w['level']} posts", value=w["n"]))
    if coef:
        ev.append(Evidence(kind="comparison", ref="mv.x_article", label="regression multiplier (month+topic controls)",
                           value=_r(coef["multiplier"], 1), evidence_class="statistical_association"))
    arts = df[(df["format"] == "x_article") & df["mature"]].nlargest(3, "views")["tweet_id"].tolist()
    ev += _post_ev(df, arts, "top X Article")
    supported = bool(a and a.get("signal") == "higher")
    obs = "X Article posts are not reliably different from other formats."
    if supported:
        obs = (f"X Article posts reach {_r(a['ratio'])}x the median views of the account's other authored posts "
               f"(n={a['n']}, 90% CI {_r(a['lo'])}-{_r(a['hi'])}).")
        if weak:
            obs += " Lower formats: " + ", ".join(f"{w['level']} {_r(w['ratio'])}x (n={w['n']})" for w in weak) + "."
    return Diagnostic(
        id=f"{h}-format", handle=h, issue="Content format drives most of the reach difference",
        status="supported" if supported else "not_supported", observation=obs, evidence=ev,
        algo_links=_valid(["B05", "B06", "B01"]),
        algo_connection=("The value model rewards predicted dwell, click-dwell and sharing (dwell, cont_click_dwell_time, "
                         "share_via_copy_link weights). Long-form articles plausibly raise those predictions; the repo "
                         "does not contain an article-specific boost."),
        alternatives=["Article topics may simply be the account's strongest topics",
                      "X may surface Articles through surfaces outside the For You ranking studied here",
                      "Articles are often promoted harder (pinned, quoted by co-founders/peers)"],
        confidence="high" if supported and a["q"] < 0.01 else "medium" if supported else "low",
        impact="Largest observed lever: shifting mix toward the best format changes the median outcome, not just outliers.",
        recommendation=("Make X Articles (with a strong native preview post) the anchor format, and turn short "
                        "standalone posts into either article teasers or replies."),
        validation="A/B over 4 weeks: alternate article vs non-article on matched topics; compare median views per format.",
        evidence_class="statistical_association",
        evidence_strength=0.9 if supported else 0.3, business_relevance=0.8, likely_impact=0.9 if supported else 0.3,
        ease_of_testing=0.8, example_posts=arts,
        confounders=["topic", "promotion effort", "author network resharing"],
        success_criteria="Article posts keep >= the current ratio vs other formats while posting volume is held constant.",
    )


# ---------------------------------------------------------------------------
# 3. Same-day stacking (author diversity)
def same_day_stacking(ctx: Ctx) -> Diagnostic:
    h, art = ctx["handle"], ctx["art"]
    cad = art["cadence"]
    order = cad.get("same_day_order", {})
    gaps = cad.get("gap_since_previous", {})
    first, third = order.get("1st", {}), order.get("3rd+", {})
    gaps.get("<2h", {})
    ev = [Evidence(kind="metric", ref="same_day_order.1st", label="1st post of day: median vs-baseline",
                   value=_r(first.get("median")), evidence_class="statistical_association"),
          Evidence(kind="metric", ref="same_day_order.1st.n", label="n first posts", value=first.get("n")),
          Evidence(kind="metric", ref="same_day_order.3rd", label="3rd+ post of day: median vs-baseline",
                   value=_r(third.get("median"))),
          Evidence(kind="metric", ref="same_day_order.3rd.n", label="n 3rd+ posts", value=third.get("n")),
          Evidence(kind="metric", ref="authored_per_week", label="authored posts per week",
                   value=_r(cad["frequency"]["authored_per_week"], 1))]
    for k, v in gaps.items():
        ev.append(Evidence(kind="metric", ref=f"gap.{k}", label=f"gap {k}: median vs-baseline (n={v.get('n')})",
                           value=_r(v.get("median"))))
    n3 = third.get("n", 0) or 0
    lower = third.get("median") is not None and first.get("median") and third["median"] < 0.8 * first["median"]
    status = "insufficient" if n3 < 8 else ("supported" if lower else "not_supported")
    obs = (f"Third-or-later authored posts on the same day reach a median {_r(third.get('median'))}x of baseline "
           f"(n={n3}) versus {_r(first.get('median'))}x for the first post of the day (n={first.get('n')}).")
    return Diagnostic(
        id=f"{h}-stacking", handle=h, issue="Several authored posts on the same day",
        status=status, observation=obs, evidence=ev,
        algo_links=_valid(["D09", "B12", "B13"]),
        algo_connection=("vm-ranker applies an author-diversity multiplier within each viewer's ranked feed: a repeat "
                         "author's later candidates are multiplied by (1 - floor) * decay^k + floor with "
                         "AuthorDiversityDecay 0.5 and AuthorDiversityFloor 0.25. Several fresh posts compete for the "
                         "same viewer slots. This is per viewer request, so it is a plausible mechanism, not a "
                         "measured penalty on this account."),
        alternatives=["Later posts of the day may be lower-effort or reactive",
                      "Time-of-day differences (later posts land outside peak hours)",
                      "Small sample for 3rd+ posts"],
        confidence="medium" if (status == "supported" and n3 >= 20) else "low" if status == "supported"
        else "insufficient evidence" if status == "insufficient" else "low",
        impact="Spacing posts is a free change; if the association is real, it recovers reach on the weakest third of posts.",
        recommendation=("Cap authored posts at 2 per day, at least 6 hours apart; move extra content into replies, "
                        "threads, or the next day."),
        validation="2-week alternating schedule (stacked vs spaced days) with the same formats; compare vs-baseline medians.",
        evidence_class="statistical_association", evidence_strength=0.6 if status == "supported" else 0.3,
        business_relevance=0.6, likely_impact=0.5, ease_of_testing=0.9,
        confounders=["time of day", "post quality", "format"],
        success_criteria="3rd+-post days disappear without lowering weekly total views.",
    )


# ---------------------------------------------------------------------------
# 4. Engagement efficiency vs peers (conversation generation)
def engagement_efficiency(ctx: Ctx) -> Diagnostic:
    h, art = ctx["handle"], ctx["art"]
    comp = {c["metric"]: c for c in art["benchmark"]["comparison"]}
    rep, eng, bm, lk = (comp.get(k, {}) for k in ("median_replies_per_1k", "median_eng_per_1k_views",
                                                   "median_bookmarks_per_1k", "median_likes_per_1k"))
    ev = []
    for name, c in (("replies per 1k views", rep), ("engagements per 1k views", eng),
                    ("bookmarks per 1k views", bm), ("likes per 1k views", lk)):
        if c.get("client") is not None:
            ev += [Evidence(kind="comparison", ref=f"{c['metric']}.client", label=f"client {name}", value=_r(c["client"])),
                   Evidence(kind="comparison", ref=f"{c['metric']}.peers", label=f"peer median {name}",
                            value=_r(c["peer_median"])),
                   Evidence(kind="comparison", ref=f"{c['metric']}.ratio", label=f"client/peer {name}",
                            value=_r(c["ratio"]))]
    low_reply = rep.get("ratio") is not None and rep["ratio"] < 0.75
    obs = (f"Replies per 1,000 views: {_r(rep.get('client'))} vs peer median {_r(rep.get('peer_median'))} "
           f"({_r(rep.get('ratio'))}x). Likes per 1,000 views: {_r(lk.get('client'))} vs {_r(lk.get('peer_median'))}. "
           f"Bookmarks per 1,000 views: {_r(bm.get('client'))} vs {_r(bm.get('peer_median'))}.")
    return Diagnostic(
        id=f"{h}-efficiency", handle=h, issue="Low conversation generation per impression",
        status="supported" if low_reply else "not_supported", observation=obs, evidence=ev,
        algo_links=_valid(["B03", "B08", "B15"]),
        algo_connection=("Published defaults weight a viewer's predicted reply probability at 5.0 versus 0.66 for a "
                         "like; for original posts from an author the viewer mutually follows, the reply weight is "
                         "raised by a further 15.0. Weights multiply the model's predicted probabilities per viewer, "
                         "not raw counts, so observed reply rates are only an outcome proxy for what the model "
                         "predicts."),
        alternatives=["Audience composition differs from peers (more lurkers / buyers who do not reply)",
                      "Lead-magnet CTAs convert replies into keyword comments counted elsewhere",
                      "Peer accounts differ in size; per-view rates partly normalise this but not fully"],
        confidence="medium" if low_reply else "low",
        impact="Conversation is the most heavily weighted positive action family; raising it is the most "
               "algorithm-aligned lever available from content alone.",
        recommendation=("End posts with a specific, answerable prompt tied to the post's claim; reply to early "
                        "commenters within the first hour to deepen threads."),
        validation="Compare replies per 1k views on posts with vs without a specific closing prompt over 4 weeks.",
        evidence_class="statistical_association", evidence_strength=0.6 if low_reply else 0.3,
        business_relevance=0.7, likely_impact=0.7 if low_reply else 0.3, ease_of_testing=0.8,
        confounders=["audience size", "topic", "CTA type"],
        success_criteria="Median replies per 1k views on authored posts moves toward the peer median.",
    )


# ---------------------------------------------------------------------------
# 5. Commenting strategy quality
def commenting_quality(ctx: Ctx) -> Diagnostic:
    h, art = ctx["handle"], ctx["art"]
    c = art["comments"]
    conv = c.get("conversation", {})
    share = c.get("category_share", {})
    sub = sum(v for k, v in share.items() if k in {"original_insight", "expert_explanation", "constructive_disagreement",
                                                    "question", "personal_experience"})
    low = share.get("generic_agreement", 0) + share.get("low_value_repetitive", 0) + share.get("humor", 0)
    conc = c.get("concentration", {})
    ev = [Evidence(kind="metric", ref="comments.n", label="conversational comments (mature)", value=conv.get("n")),
          Evidence(kind="metric", ref="comments.median_views", label="median views per comment",
                   value=_r(conv.get("views", {}).get("median"), 1)),
          Evidence(kind="metric", ref="comments.substantive_share", label="substantive share", value=_r(sub)),
          Evidence(kind="metric", ref="comments.low_value_share", label="generic/repetitive/humor share", value=_r(low)),
          Evidence(kind="metric", ref="comments.top5_share", label="share of comments to top-5 accounts",
                   value=_r(conc.get("top5_share"))),
          Evidence(kind="metric", ref="comments.distinct", label="distinct accounts commented on",
                   value=conc.get("distinct_parent_authors")),
          Evidence(kind="metric", ref="comments.share_with_reply", label="comments that drew a reply",
                   value=_r(conv.get("share_with_reply")))]
    for r in (c.get("by_category") or [])[:6]:
        ev.append(Evidence(kind="comparison", ref=f"category.{r['category']}",
                           label=f"{r['category']} (n={r['n']}) median views", value=r["median_views"]))
    supported = conv.get("n", 0) >= 20 and sub < 0.5
    obs = (f"{conv.get('n')} conversational comments in the window; {_r(sub * 100, 0)}% are substantive and "
           f"{_r(low * 100, 0)}% are generic, repetitive or humour. The top 5 accounts receive "
           f"{_r(conc.get('top5_share', 0) * 100, 0)}% of comments; median exposure is "
           f"{_r(conv.get('views', {}).get('median'), 1)} views per comment.")
    return Diagnostic(
        id=f"{h}-comments", handle=h, issue="Commenting is low-depth and concentrated on a small circle",
        status="supported" if supported else "insufficient" if conv.get("n", 0) < 20 else "not_supported",
        observation=obs, evidence=ev,
        algo_links=_valid(["D04", "D10", "B15"]),
        algo_connection=("In the published For You pipeline, out-of-network replies are filtered out by default and "
                         "in-network replies receive the 0.75 out-of-network-style rescore, so a comment is seen "
                         "mainly inside the parent conversation, not distributed in feeds. Comments can still build "
                         "mutual-follow relationships, and the reply weight is raised for original posts from "
                         "mutually-followed authors. The repo has no 'comment boost' for the commenter's own posts."),
        alternatives=["Comments within a founder circle may serve partnership/relationship goals rather than reach",
                      "Parent-post context (unavailable for most replies) may make short replies more relevant than "
                      "they look"],
        confidence="medium" if supported else "low",
        impact="Comment exposure is small per reply; quality matters more than volume for building recognition.",
        recommendation=("Replace generic agreement with 2-3 sentence expert additions on larger in-niche accounts' "
                        "posts within their first hour; keep relationship comments but stop emoji/one-word replies."),
        validation="Track median views and reply-backs per comment for 'expert addition' comments vs the current mix.",
        evidence_class="account_observed", evidence_strength=0.7 if supported else 0.3, business_relevance=0.6,
        likely_impact=0.5, ease_of_testing=0.8,
        confounders=["parent-post reach", "timing (unmeasured)", "relationship goals"],
        success_criteria="Substantive share > 60% and median views per comment above current median.",
    )


# ---------------------------------------------------------------------------
# 6. Lead-magnet fulfilment volume ("Sent" replies)
def fulfilment_volume(ctx: Ctx) -> Diagnostic:
    h, art = ctx["handle"], ctx["art"]
    f = art["comments"]["fulfilment"]
    kw = _seg(art, "keyword_cta", "True")
    promo = _seg(art, "promotional", "True")
    ev = [Evidence(kind="metric", ref="fulfilment.n", label="fulfilment replies", value=f["n"]),
          Evidence(kind="metric", ref="fulfilment.per_week", label="fulfilment replies per week", value=_r(f["per_week"], 1)),
          Evidence(kind="metric", ref="fulfilment.recipients", label="distinct recipients", value=f["distinct_recipients"])]
    for s, nm in ((kw, "keyword CTA posts"), (promo, "promotional posts")):
        if s and s.get("tested"):
            ev += [Evidence(kind="comparison", ref=f"{nm}.ratio", label=f"{nm}: median views ratio", value=_r(s["ratio"]),
                            evidence_class="statistical_association"),
                   Evidence(kind="metric", ref=f"{nm}.n", label=f"{nm} n", value=s["n"])]
    heavy = f["n"] >= 100
    obs = (f"{f['n']} template replies ('Sent', 'Here you go: <link>') to {f['distinct_recipients']} distinct accounts, "
           f"about {_r(f['per_week'], 1)} per week. These are fulfilment of comment-for-resource CTAs, "
           "inferred from their template text.")
    links = _valid(["C15", "C11", "C12"])
    return Diagnostic(
        id=f"{h}-fulfilment", handle=h, issue="High-volume templated replies (lead-magnet fulfilment)",
        status="supported" if heavy else "not_supported", observation=obs, evidence=ev,
        algo_links=links,
        algo_connection=("A published botmaker rule clusters replies with duplicate text and applies a "
                         "COPYPASTA_SPAM label (skipping high-PageRank and grey-verified users), and the Grox "
                         "reply_spam flow can label risky replies. Whether these clients' identical 'Sent' replies "
                         "are labelled, and what any label does to reach, is not observable and partly withheld; this "
                         "is a risk to monitor, not an observed penalty."),
        alternatives=["Keyword-CTA posts generate many replies, which is itself a strong positive signal",
                      "Templated fulfilment is normal for lead magnets and widely used by peers"],
        confidence="low",
        impact="Mainly risk management and time cost; also inflates 'reply' counts so commenting looks larger than it is.",
        recommendation=("Keep lead magnets but vary fulfilment (short personalised line + resource), or deliver "
                        "via one pinned reply / DM automation instead of hundreds of identical public replies."),
        validation="Compare authored-post reach in weeks with vs without mass fulfilment replies (matched formats).",
        evidence_class="hypothesis", evidence_strength=0.4 if heavy else 0.1, business_relevance=0.5,
        likely_impact=0.3, ease_of_testing=0.6,
        confounders=["lead-magnet topic quality", "CTA wording"],
        success_criteria="No drop in lead-magnet conversions with < 25% of current identical public replies.",
    )


# ---------------------------------------------------------------------------
# 7. Topic focus / audience-content alignment
def topic_alignment(ctx: Ctx) -> Diagnostic:
    h, art, df = ctx["handle"], ctx["art"], ctx["df"]
    a = df[df["is_authored"]]
    mix = a["topic"].value_counts(normalize=True)
    top2 = float(mix.head(2).sum()) if len(mix) else 0.0
    segs, scope = _content_segs(art)
    higher = [s for s in segs if s["feature"] == "topic" and s["signal"] == "higher"]
    lower = [s for s in segs if s["feature"] == "topic" and s["signal"] == "lower"]
    ev = [Evidence(kind="metric", ref="topic.top2_share", label="share of authored posts in top-2 topics", value=_r(top2))]
    ev += [Evidence(kind="comparison", ref=f"topic={s['level']}", label=f"{s['level']} (n={s['n']}) median ratio",
                    value=_r(s["ratio"]), evidence_class="statistical_association") for s in higher + lower]
    obs = f"The top two topics account for {_r(top2 * 100, 0)}% of authored posts."
    if scope and (higher or lower):
        obs += f" Topic comparisons{scope}:"
    if higher:
        obs += " Topics associated with higher reach: " + ", ".join(f"{s['level']} {_r(s['ratio'])}x" for s in higher) + "."
    if lower:
        obs += " Lower: " + ", ".join(f"{s['level']} {_r(s['ratio'])}x" for s in lower) + "."
    supported = bool(lower) or bool(higher)
    return Diagnostic(
        id=f"{h}-topics", handle=h, issue="Off-core topics underperform core topics",
        status="supported" if lower else "mixed" if higher else "not_supported",
        observation=obs, evidence=ev, algo_links=_valid(["A11", "A12", "A05"]),
        algo_connection=("SimClusters and Phoenix retrieval match posts to viewers whose recent engagement "
                         "resembles the post. Consistent topics make it more likely the right viewers already have "
                         "related engagement history; the repo exposes no per-account topic score."),
        alternatives=["Topic effects overlap with format (tutorial topics are more often articles)",
                      "Off-core posts may be personal/timely and judged on other goals"],
        confidence="medium" if lower and higher else "low",
        impact="Concentrating on the strongest clusters improves the median post without adding volume.",
        recommendation="Prioritise the higher-reach topics listed; reduce off-core posts or move them to replies.",
        validation="Re-run the topic comparison after 6 weeks with the regression (format + month controls).",
        evidence_class="statistical_association", evidence_strength=0.6 if supported else 0.2,
        business_relevance=0.8, likely_impact=0.6, ease_of_testing=0.7,
        confounders=["format", "timing", "promotion"],
        success_criteria="Share of authored posts in the higher-reach topics rises with no fall in their median.",
    )


# ---------------------------------------------------------------------------
# 8. Hooks / opening line
def hooks(ctx: Ctx) -> Diagnostic:
    h, art = ctx["handle"], ctx["art"]
    segs, scope = _content_segs(art)
    rows = [s for s in segs if s["feature"] in ("hook_type", "narrative", "educational_value")
            and s["signal"] in ("higher", "lower")]
    ev = [Evidence(kind="comparison", ref=f"{s['feature']}={s['level']}",
                   label=f"{s['feature_label']}: {s['level']} (n={s['n']}) median ratio", value=_r(s["ratio"]),
                   evidence_class="statistical_association") for s in rows]
    tested = [s for s in segs if s["feature"] in ("hook_type", "narrative", "educational_value") and s.get("tested")]
    ev.append(Evidence(kind="metric", ref="hooks.levels_tested", label=f"opening/structure levels compared{scope}",
                       value=len(tested), evidence_class="statistical_association"))
    hi = [s for s in rows if s["signal"] == "higher"]
    lo = [s for s in rows if s["signal"] == "lower"]
    obs = f"Opening/structure patterns with clear differences{scope}: "
    obs += "; ".join(f"{s['feature_label']} = {s['level']}: {_r(s['ratio'])}x (n={s['n']})" for s in hi + lo) or "none"
    return Diagnostic(
        id=f"{h}-hooks", handle=h, issue="Weak openings / low-utility structures",
        status="supported" if lo else "mixed" if hi else "not_supported", observation=obs + ".", evidence=ev,
        algo_links=_valid(["B05", "B04"]),
        algo_connection=("Dwell and click-dwell predictions are weighted positively and 'not_dwelled' negatively in "
                         "published defaults; an opening that earns an expand plausibly raises those predictions."),
        alternatives=["Hook type correlates with format and topic", "Labels are model judgements and can be noisy"],
        confidence="medium" if lo and hi else "low",
        impact="Hooks are cheap to change and testable post-by-post.",
        recommendation="Lead with the concrete outcome or how-to promise; avoid opinion-only or vague observational openers.",
        validation="Paired test: same topic, two hook styles on different days; compare vs-baseline ratios.",
        evidence_class="statistical_association", evidence_strength=0.5 if rows else 0.1, business_relevance=0.6,
        likely_impact=0.5, ease_of_testing=0.9,
        confounders=["topic", "format"], success_criteria="Hook-type gap persists in a controlled 4-week test.",
    )


# ---------------------------------------------------------------------------
# 9. External links (claim check against the data)
def link_usage(ctx: Ctx) -> Diagnostic:
    h, art = ctx["handle"], ctx["art"]
    s_true = _seg(art, "tco_url_excl_articles", "True")
    ev = []
    if s_true and s_true.get("tested"):
        ev = [Evidence(kind="comparison", ref="tco_url_excl_articles=True", label="non-article posts with t.co URL: ratio",
                       value=_r(s_true["ratio"]), evidence_class="statistical_association"),
              Evidence(kind="metric", ref="tco.n", label="n with URL", value=s_true["n"]),
              Evidence(kind="metric", ref="tco.n_rest", label="n without URL", value=s_true["n_rest"]),
              Evidence(kind="metric", ref="tco.ci", label="CI", value=f"{_r(s_true['lo'])}-{_r(s_true['hi'])}")]
    lower = bool(s_true and s_true.get("signal") == "lower")
    obs = ("Among non-article authored posts, posts containing a t.co URL (external link or media) reach "
           f"{_r(s_true['ratio'])}x the median of those without (n={s_true['n']} vs {s_true['n_rest']}).") \
        if ev else "Too few non-article posts with/without URLs to compare."
    return Diagnostic(
        id=f"{h}-links", handle=h, issue="External links reduce reach (common claim)",
        status="supported" if lower else "not_supported" if ev else "insufficient", observation=obs, evidence=ev,
        algo_links=_valid(["B04", "D17"]),
        algo_connection=("The published ranking code contains no link penalty: open_link carries a small positive "
                         "weight. has_url is computed only for an experimental debias payload that is off by default. "
                         "Media and external links cannot be separated in this data."),
        alternatives=["t.co URLs include attached media, which may help", "Link posts are often promotional"],
        confidence="low",
        impact="Determines whether link placement should change; the repository gives no reason to expect a penalty.",
        recommendation=("Do not restructure content around a link penalty; if testing, put the link in a self-reply "
                        "on half of link posts and compare."),
        validation="Randomised link-in-post vs link-in-reply on comparable posts for 4 weeks.",
        evidence_class="statistical_association", evidence_strength=0.4 if ev else 0.0, business_relevance=0.4,
        likely_impact=0.3, ease_of_testing=0.8,
        confounders=["media vs link", "promotional intent"], success_criteria="Decision rule in experiment plan.",
    )


# ---------------------------------------------------------------------------
# 10. Reach concentration / dependence on outliers
def concentration(ctx: Ctx) -> Diagnostic:
    h, art, df = ctx["handle"], ctx["art"], ctx["df"]
    c = art["reach"]["concentration"]
    vb = art["reach"]["vs_baseline"]
    top = df[df["is_authored"] & df["mature"]].nlargest(3, "views")["tweet_id"].tolist()
    ev = [Evidence(kind="metric", ref="top5pct_share", label="share of authored views from top 5% of posts",
                   value=_r(c["top5pct_share_of_views"])),
          Evidence(kind="metric", ref="top1_share", label="share from the single top post", value=_r(c["top1_share_of_views"])),
          Evidence(kind="metric", ref="share_below_half", label="posts below 0.5x baseline", value=_r(vb["share_below_half"])),
          Evidence(kind="metric", ref="share_above_2x", label="posts above 2x baseline", value=_r(vb["share_above_2x"])),
          *_post_ev(df, top, "top post")]
    high = c["top5pct_share_of_views"] >= 0.5
    obs = (f"The top 5% of authored posts produced {_r(c['top5pct_share_of_views'] * 100, 0)}% of authored views; the "
           f"single top post {_r(c['top1_share_of_views'] * 100, 0)}%. {_r(vb['share_below_half'] * 100, 0)}% of posts "
           f"land below half the trailing baseline and {_r(vb['share_above_2x'] * 100, 0)}% above twice it.")
    return Diagnostic(
        id=f"{h}-concentration", handle=h, issue="Reach depends on rare breakouts",
        status="supported" if high else "not_supported", observation=obs, evidence=ev,
        algo_links=_valid(["A07", "A08", "D19"]),
        algo_connection=("Out-of-network discovery starts small (cold-start pool for posts with few likes/views; "
                         "retrieval-index admission triggered by likes) and only some posts escape it. Heavy-tailed "
                         "outcomes are expected from this design."),
        alternatives=["Viral posts may be driven by external resharing (large accounts, newsletters)"],
        confidence="high" if high else "medium",
        impact="Averages mislead: judge experiments on medians and share-above-baseline, not totals.",
        recommendation="Reverse-engineer the top posts' structure into a repeatable template; judge tests on medians.",
        validation="Share of posts above 2x baseline per month.",
        evidence_class="account_observed", evidence_strength=0.8, business_relevance=0.5, likely_impact=0.4,
        ease_of_testing=0.6, example_posts=top, confounders=["external amplification"],
        success_criteria="Share above 2x baseline rises without lowering the median.",
    )


# ---------------------------------------------------------------------------
# 11. Visibility limitations — observable signs only
def visibility_check(ctx: Ctx) -> Diagnostic:
    h, art, df = ctx["handle"], ctx["art"], ctx["df"]
    a = df[df["is_authored"] & df["mature"] & df["views"].notna()]
    zero_like_low = int(((a["views"] < 100)).sum())
    replies = art["reach"]["segments"].get("reply to others", {})
    ev = [Evidence(kind="metric", ref="authored_under_100_views", label="mature authored posts with < 100 views",
                   value=zero_like_low),
          Evidence(kind="metric", ref="authored_n", label="mature authored posts", value=int(len(a))),
          Evidence(kind="metric", ref="reply_median_views", label="median views per reply", value=replies.get("median")),
          Evidence(kind="data_gap", ref="visibility_labels", label="X does not expose visibility labels or filter "
                   "decisions to the public; none can be observed here")]
    return Diagnostic(
        id=f"{h}-visibility", handle=h, issue="Signs of visibility limitations",
        status="not_supported" if zero_like_low <= 0.05 * max(1, len(a)) else "insufficient",
        observation=(f"{zero_like_low} of {len(a)} mature authored posts have fewer than 100 views; reach is "
                     "continuous with the account's normal range. No public signal indicates a visibility "
                     "restriction; this audit cannot observe X's visibility-filtering decisions."),
        evidence=ev,
        algo_links=_valid(["C16", "D13", "C07"]),
        algo_connection=("Visibility filtering (Allow/Notice/Interstitial/Drop) and account-quality systems exist in the "
                         "repository, but their per-account outputs are not public."),
        alternatives=["Any decline is better explained by format/topic mix and the trend analysis"],
        confidence="insufficient evidence",
        impact="No action warranted on current evidence; claims of suppression would be speculation.",
        recommendation="Do not act on shadowban theories; monitor for abrupt step-changes (>50% week-on-week drop "
                       "across all formats) as the trigger to investigate.",
        validation="Monitoring alert on control limits (rolling median ± 3 MAD) across formats.",
        evidence_class="insufficient", evidence_strength=0.1, business_relevance=0.3, likely_impact=0.1,
        ease_of_testing=0.3,
        success_criteria="No unexplained cross-format step change.",
    )


CHECKERS: list[Callable[[Ctx], Diagnostic]] = [
    reach_trend, format_effects, topic_alignment, hooks, engagement_efficiency, same_day_stacking,
    commenting_quality, fulfilment_volume, link_usage, concentration, visibility_check,
]
