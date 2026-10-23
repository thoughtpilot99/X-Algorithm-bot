"""Turn diagnostics into ranked root causes, actions, rewrites and a 30-day test plan."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from xaudit.analysis.pipeline import prepare
from xaudit.analysis.stats import required_n_per_arm
from xaudit.db.session import load_artifact, save_artifact
from xaudit.settings import DATA_DIR, analysis_cfg

REWRITES_DIR = DATA_DIR / "labels" / "rewrites"


def rank_root_causes(diags: list[dict], k: int = 5) -> list[dict]:
    """Top-k potential barriers among diagnostics the data supports (fully or partly)."""
    eligible = [d for d in diags if d["status"] in ("supported", "mixed")]
    ranked = sorted(eligible, key=lambda d: -d["priority"])[:k]
    return [{"rank": i + 1, **d} for i, d in enumerate(ranked)]


def select_rewrites(df: pd.DataFrame, n: int = 12) -> list[dict]:
    """Underperforming mature authored posts with enough text to rewrite, lowest vs-baseline first."""
    a = df[df["is_authored"] & df["mature"] & df["vs_baseline"].notna() & (df["word_count"] >= 12)]
    a = a[a["vs_baseline"] < 0.6].sort_values("vs_baseline")
    picked = a.drop_duplicates(subset=["hook"]).head(n)
    cols = ["tweet_id", "url", "created_at", "format", "topic", "hook_type", "text", "views", "likes", "replies",
            "reposts", "bookmarks", "baseline_views", "vs_baseline", "eng_per_1k", "quadrant"]
    out = picked[cols].copy()
    out["created_at"] = out["created_at"].dt.strftime("%Y-%m-%d %H:%M UTC")
    return out.replace({np.nan: None}).to_dict("records")


def load_rewrites(handle: str, selected: list[dict]) -> list[dict]:
    """Merge externally drafted rewrites (JSON list keyed by tweet_id) onto the selected posts."""
    p = REWRITES_DIR / f"{handle}.json"
    drafts = {}
    if p.exists():
        with open(p, encoding="utf-8") as f:
            drafts = {str(d["tweet_id"]): d for d in json.load(f)}
    out = []
    for s in selected:
        d = drafts.get(str(s["tweet_id"]), {})
        out.append({**s,
                    "observed_issue": d.get("observed_issue"),
                    "can_conclude": d.get("can_conclude"),
                    "cannot_conclude": d.get("cannot_conclude"),
                    "rewrite": d.get("rewrite"),
                    "editorial_changes": d.get("editorial_changes"),
                    "test": d.get("test"),
                    "drafted_by": d.get("drafted_by"),
                    "disclaimer": "A rewrite is an editorial proposal to test; it is not predicted to receive more "
                                  "distribution."})
    return out


def _arm_weeks(n_per_arm: int, posts_per_week: float, arms: int = 2) -> float | None:
    return None if posts_per_week <= 0 else n_per_arm * arms / posts_per_week


def experiment_plan(handle: str, df: pd.DataFrame, diags: list[dict]) -> dict:
    a = df[df["is_authored"] & df["mature"] & df["views"].notna()]
    sd = float(np.log1p(a["views"]).std()) if len(a) > 5 else None
    mv = load_artifact("multivariable", handle) or {}
    sd_resid = mv.get("residual_sd_log") or sd
    cad = load_artifact("cadence", handle) or {}
    ppw = cad.get("frequency", {}).get("authored_per_week", 0.0)
    rpw = cad.get("frequency", {}).get("replies_per_week", 0.0)
    n13 = required_n_per_arm(sd_resid, 1.3)
    n15 = required_n_per_arm(sd_resid, 1.5)
    n20 = required_n_per_arm(sd_resid, 2.0)
    d = {x["id"].split("-", 1)[1]: x for x in diags}

    def power_note(n: int) -> str:
        w = _arm_weeks(n, ppw)
        return ("" if w is None else
                f"Needs ~{n} posts per arm; at the current {ppw:.1f} authored posts/week that is ~{w:.0f} weeks.")

    def exp(eid: str, week: int, title: str, hypothesis: str, intervention: str, control: str, primary: str,
            secondary: list[str], n_per_arm: int | None, period: str, confounders: list[str], decision: str,
            source: str | None) -> dict:
        weeks_needed = _arm_weeks(n_per_arm, ppw) if n_per_arm else None
        return {"id": eid, "week": week, "title": title, "hypothesis": hypothesis, "intervention": intervention,
                "control": control, "primary_metric": primary, "secondary_metrics": secondary,
                "required_n_per_arm": n_per_arm, "minimum_period": period,
                "weeks_needed_at_current_rate": round(weeks_needed, 1) if weeks_needed else None,
                "underpowered_in_30_days": bool(weeks_needed and weeks_needed > 4),
                "confounders": confounders, "decision_rule": decision, "from_diagnostic": source}

    plan = [
        exp("W1-baseline", 1, "Freeze the baseline and fix data gaps",
            "Current medians are a valid benchmark for the next 3 weeks.",
            "Start daily metric snapshots (monitoring) for posts and follower count; log every post's format and "
            "topic at publish time.", "n/a", "data completeness", ["metric snapshots per post at 24h/72h/7d"],
            None, "7 days", ["none"], "Proceed when 24h/72h snapshots exist for every new post.", None),
        exp("W1-spacing", 1, "Space authored posts (max 2/day, >= 6h apart)",
            "Same-day stacking is associated with lower reach for later posts (author-diversity mechanism).",
            "Cap authored posts at 2 per day, >= 6h apart; extra items become replies/threads or move to the next day.",
            "Previous 4 weeks of the same account (pre/post) and the stacking days in history",
            "median views relative to trailing baseline", ["weekly total authored views", "posts/week"],
            n15, "3-4 weeks", ["format mix", "seasonality"],
            "Keep spacing if median vs-baseline of posts that would have been 3rd+ rises above 0.8x without "
            "lowering weekly total views by > 10%.", "stacking"),
        exp("W2-format", 2, "Article-anchored week vs mixed week",
            "X Articles (with a native preview post) outperform other formats on matched topics.",
            "Alternate weeks: anchor week = 2-3 X Articles on core topics + supporting posts; control week = usual mix.",
            "Alternating control weeks (A/B/A/B)", "median views per authored post",
            ["bookmarks per 1k views", "replies per 1k views"], n13, "4 weeks (alternating)",
            ["topic", "promotion effort", "co-founder reshares"],
            "Adopt as default if anchor-week median >= 1.3x control-week median in both alternating pairs.", "format"),
        exp("W2-hooks", 2, "Outcome-first hooks vs current openers",
            "Openings that state a concrete outcome or how-to promise earn more expands/dwell than observational "
            "openers.",
            "Randomise (coin flip per post) between an outcome/how-to hook and the author's natural opener for "
            "non-article posts.", "Coin-flip control posts", "median views vs baseline",
            ["likes per 1k", "bookmarks per 1k"], n15, "3-4 weeks", ["topic", "format"],
            "Adopt if treatment median vs-baseline exceeds control by >= 1.3x with both arms >= 8 posts.", "hooks"),
        exp("W2-prompts", 2, "Specific closing prompt + first-hour author replies",
            "Ending with a specific, answerable question and replying to early commenters raises replies per 1k views.",
            "Half of posts (randomised) end with a specific question; author replies to the first 5 comments "
            "within 60 minutes.", "Randomised posts without the prompt", "replies per 1k views",
            ["views vs baseline", "share of posts with >= 5 replies"], n15, "4 weeks", ["topic", "time of day"],
            "Adopt if replies per 1k views is >= 1.3x control with no drop in views vs baseline.", "efficiency"),
        exp("W3-comments", 3, "Expert-addition comments on larger in-niche accounts",
            "2-3 sentence expert additions on in-niche posts earn more views and reply-backs than generic replies.",
            "10 comments/day: substantive additions on posts < 60 min old from accounts with 2-20x the client's "
            "followers in core topics; stop emoji/one-word replies.",
            "The account's previous 4 weeks of conversational comments", "median views per comment",
            ["share of comments that receive a reply", "new accounts engaging with the client's posts"],
            None, "2-3 weeks", ["parent-post reach", "parent author"],
            "Continue if median views per comment >= 2x the previous median and reply-back share rises.", "comments"),
        exp("W3-fulfilment", 3, "Lead-magnet delivery without mass identical replies",
            "Delivering lead magnets via DM/pinned reply instead of hundreds of identical public 'Sent' replies keeps "
            "conversions and removes a duplicate-reply risk.",
            "For half of lead-magnet posts (alternating), deliver via one pinned reply + DM automation; vary wording.",
            "Alternating lead-magnet posts with the current 'Sent' replies",
            "keyword comments per lead-magnet post", ["views vs baseline of the lead-magnet post", "DMs delivered"],
            None, "4 weeks (needs >= 4 lead-magnet posts per arm)", ["lead-magnet topic", "CTA wording"],
            "Switch if comments per post are within 15% of control.", "fulfilment"),
        exp("W4-review", 4, "Evaluate, keep or drop",
            "n/a", "Re-run the full audit pipeline; compare each experiment's primary metric against its decision rule.",
            "n/a", "decision per experiment", [], None, "end of week 4", ["seasonality"],
            "Retain experiments that met their rule; extend underpowered ones rather than calling them.", None),
    ]
    for p in plan:
        if p["from_diagnostic"] and p["from_diagnostic"] in d:
            dd = d[p["from_diagnostic"]]
            p["diagnostic_status"] = dd["status"]
            p["diagnostic_confidence"] = dd["confidence"]
    return {
        "power": {
            "log_view_sd": sd, "residual_sd_log": sd_resid,
            "posts_per_arm_for_1.3x": n13, "posts_per_arm_for_1.5x": n15, "posts_per_arm_for_2x": n20,
            "authored_posts_per_week": ppw, "replies_per_week": rpw,
            "note": ("Sample sizes assume a two-sided test at alpha 0.05 and 80% power on log views, using the "
                     "residual spread after month/format/topic controls. Effects smaller than ~1.3x cannot be "
                     "detected within 30 days at current posting rates. " + power_note(n13)),
        },
        "experiments": plan,
    }


def stop_continue_start(handle: str, diags: list[dict], segments: list[dict]) -> dict:
    hi = sorted([s for s in segments if s["signal"] == "higher"], key=lambda s: -s["ratio"])
    lo = sorted([s for s in segments if s["signal"] == "lower"], key=lambda s: s["ratio"])
    d = {x["id"].split("-", 1)[1]: x for x in diags}

    def seg_line(s: dict) -> str:
        return f"{s['feature_label']}: {s['level']} ({s['ratio']:.2f}x median, n={s['n']})"

    stop, cont, start = [], [], []
    for s in lo[:5]:
        stop.append({"action": f"Reduce: {seg_line(s)}", "evidence_class": "statistical_association"})
    if d.get("stacking", {}).get("status") == "supported":
        stop.append({"action": "Stop publishing a 3rd authored post on the same day", "evidence_class":
                     "statistical_association"})
    if d.get("comments", {}).get("status") == "supported":
        stop.append({"action": "Stop generic/emoji-only comments; they earn little exposure",
                     "evidence_class": "account_observed"})
    if d.get("fulfilment", {}).get("status") == "supported":
        stop.append({"action": "Stop mass identical public 'Sent' replies (test DM/pinned delivery)",
                     "evidence_class": "hypothesis"})
    for s in hi[:5]:
        cont.append({"action": f"Keep: {seg_line(s)}", "evidence_class": "statistical_association"})
    start += [
        {"action": "Start measuring: daily metric snapshots + follower history (monitoring)",
         "evidence_class": "account_observed"},
        {"action": "Start the randomised hook and closing-prompt tests (see 30-day plan)", "evidence_class": "hypothesis"},
        {"action": "Start substantive comments on larger in-niche accounts within their first hour",
         "evidence_class": "hypothesis"},
    ]
    if d.get("efficiency", {}).get("status") == "supported":
        start.append({"action": "Start replying to early commenters within 60 minutes to build conversation depth",
                      "evidence_class": "hypothesis"})
    return {"stop": stop, "continue": cont, "start": start}


def run(handle: str) -> dict:
    diags = (load_artifact("diagnostics", handle) or {}).get("items", [])
    segs = load_artifact("segments", handle) or []
    df = prepare(handle, window_days=analysis_cfg()["extended_window_days"])
    selected = select_rewrites(df)
    out = {
        "root_causes": rank_root_causes(diags),
        "actions": stop_continue_start(handle, diags, segs),
        "rewrites": load_rewrites(handle, selected),
        "plan": experiment_plan(handle, df, diags),
    }
    save_artifact("recommendations", out, handle)
    return out


def export_rewrite_requests(handle: str, path: Path | None = None) -> Path:
    df = prepare(handle, window_days=analysis_cfg()["extended_window_days"])
    sel = select_rewrites(df)
    path = path or (DATA_DIR / "labels" / "rewrite_requests" / f"{handle}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sel, f, ensure_ascii=False, indent=2, default=str)
    return path


def _isfinite(x) -> bool:  # noqa: ANN001
    return x is not None and not (isinstance(x, float) and math.isnan(x))
