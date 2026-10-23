"""Check each content pattern against the actions X's published ranking weights.

X's ranking (home-mixer) scores a post for a viewer as a weighted sum of predicted
probabilities of actions. Four of those actions are publicly countable on every
post: replies, quotes, reposts and likes. Their published weights are applied here
to each post's observed action rates per 1,000 views ("X-weighted actions per
1,000 views"). This is NOT X's score: X uses per-viewer predictions and also
weights actions nobody outside X can count (shares, follows, time spent).

For a segment (e.g. X Articles) the question is: does it also earn more of the
heavily weighted actions per view? If yes, the reach difference lines up with what
the published code rewards ("backed"). If reach differs but countable weighted
actions don't, the gap is left to actions we can't see ("partly").
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from xaudit.analysis.segments import FEATURES
from xaudit.analysis.stats import bh_adjust, mann_whitney
from xaudit.settings import analysis_cfg

# Countable actions and the param.rs weight each maps to.
OBSERVABLE = (("replies", "ReplyWeight"), ("quotes", "QuoteWeight"), ("reposts", "RetweetWeight"),
              ("likes", "FavoriteWeight"))
ALL_ACTIONS = ("replies", "quotes", "reposts", "likes", "bookmarks")
UNSEEN = (("ShareViaCopyLinkWeight", "share via copied link"), ("ShareViaDmWeight", "share by DM"),
          ("ShareWeight", "share"), ("FollowAuthorWeight", "follow the author"),
          ("ContClickDwellTimeWeight", "time spent after opening"))
PROXY_NOTE = ("Built from X's published weights applied to the actions anyone can count (replies, quotes, "
              "reposts, likes). It is not X's score: X uses per-viewer predictions and also counts shares, "
              "follows and time spent, which aren't public.")
RNG = np.random.default_rng(7)
TRIM = 0.1


def weights() -> dict[str, dict]:
    """Published weights with their source line (home-mixer defaults first)."""
    from xaudit.algo import param_extract

    try:
        rows = param_extract.current()
    except Exception:  # noqa: BLE001  (repo not synced locally)
        return {}
    out: dict[str, dict] = {}
    for p in sorted(rows, key=lambda r: not r["path"].startswith("home-mixer")):
        if p.get("value") is not None:
            out.setdefault(p["name"], {"value": p["value"], "path": p["path"], "line": p["line"],
                                       "permalink": p["permalink"]})
    return out


def add_weighted(df: pd.DataFrame, w: dict[str, dict]) -> pd.DataFrame:
    df = df.copy()
    v = df["views"].where(df["views"] > 0)
    for a in ALL_ACTIONS:
        df[f"{a}_per_1k"] = df[a].fillna(0) / v * 1000
    df["x_weighted_per_1k"] = sum(w[name]["value"] * df[f"{a}_per_1k"] for a, name in OBSERVABLE if name in w)
    df["x_weighted_per_post"] = sum(w[name]["value"] * df[a].fillna(0) for a, name in OBSERVABLE if name in w)
    return df


def _tmean(x: np.ndarray) -> float:
    return float(stats.trim_mean(x, TRIM)) if x.size else float("nan")


def _boot_ratio(a: np.ndarray, b: np.ndarray, n: int = 2000) -> dict:
    """Ratio of 10%-trimmed means with a percentile bootstrap 90% range."""
    if a.size < 2 or b.size < 2 or _tmean(b) <= 0:
        return {"ratio": None, "lo": None, "hi": None}
    ia = RNG.integers(0, a.size, (n, a.size))
    ib = RNG.integers(0, b.size, (n, b.size))
    ta = stats.trim_mean(a[ia], TRIM, axis=1)
    tb = stats.trim_mean(b[ib], TRIM, axis=1)
    ok = tb > 0
    r = ta[ok] / tb[ok]
    lo, hi = np.quantile(r, [0.05, 0.95])
    return {"ratio": _tmean(a) / _tmean(b), "lo": float(lo), "hi": float(hi)}


def post_card(r: pd.Series) -> dict:
    t = " ".join(str(r["text"]).split())
    title = r.get("article_title")
    if isinstance(title, str) and title.strip() and (t.startswith("https://t.co/") or not t):
        t = f"X Article: {title.strip()}"
    return {"tweet_id": str(r["tweet_id"]), "url": r["url"], "date": r["created_at"].strftime("%d %b %Y"),
            "text": t[:160], "format": str(r.get("format") or ""),
            **{k: (None if pd.isna(r.get(k)) else float(r.get(k))) for k in ("views", *ALL_ACTIONS)},
            "x_weighted_per_1k": None if pd.isna(r.get("x_weighted_per_1k")) else round(float(r["x_weighted_per_1k"]), 2),
            "vs_usual": None if pd.isna(r.get("vs_baseline")) else round(float(r["vs_baseline"]), 2)}


def chance_words(q: float | None) -> str:
    if q is None:
        return "not tested"
    if q < 0.001:
        return "would happen by chance less than 1 time in 1,000"
    if q < 0.01:
        return "would happen by chance less than 1 time in 100"
    if q < 0.05:
        return "would happen by chance less than 1 time in 20"
    if q < 0.1:
        return "would happen by chance less than 1 time in 10"
    return "could easily be chance"


def verdict(reach_ratio: float | None, wr: dict, n: int, n_rest: int, min_n: int) -> tuple[str, str]:
    if n < min_n or n_rest < min_n or reach_ratio is None or wr.get("ratio") is None:
        return "not_enough", "Not enough posts to check"
    up = reach_ratio > 1
    if (up and wr["lo"] > 1) or (not up and wr["hi"] < 1):
        return "backed", "Backed by X's code"
    return "partly", "Not explained by public reactions"


def check_segment(a: pd.DataFrame, feat: str, level: str, w: dict, min_n: int) -> dict:
    col = a[feat].astype(str)
    g, rest = a[col == level], a[(col != level) & a[feat].notna()]
    gv, rv = g["views"].to_numpy(float), rest["views"].to_numpy(float)
    reach_ratio = float(np.median(gv) / np.median(rv)) if len(gv) and len(rv) and np.median(rv) > 0 else None
    gw = g["x_weighted_per_1k"].dropna().to_numpy(float)
    rw = rest["x_weighted_per_1k"].dropna().to_numpy(float)
    wr = _boot_ratio(gw, rw)
    code, label = verdict(reach_ratio, wr, len(g), len(rest), min_n)
    actions = {k: {"segment": _tmean(g[f"{k}_per_1k"].dropna().to_numpy(float)),
                   "rest": _tmean(rest[f"{k}_per_1k"].dropna().to_numpy(float))} for k in ALL_ACTIONS}
    actions["x_weighted"] = {"segment": _tmean(gw), "rest": _tmean(rw)}
    per_post = {"segment": float(g["x_weighted_per_post"].median()) if len(g) else None,
                "rest": float(rest["x_weighted_per_post"].median()) if len(rest) else None}
    srt = g.sort_values("views", ascending=False)
    return {
        "feature": feat, "level": level, "feature_label": FEATURES.get(feat, feat), "n": int(len(g)),
        "n_rest": int(len(rest)),
        "reach": {"median": float(np.median(gv)) if len(gv) else None,
                  "median_rest": float(np.median(rv)) if len(rv) else None, "ratio": reach_ratio,
                  "p": mann_whitney(gv, rv)["p"]},
        "actions_per_1k": actions, "weighted": {**wr, "p": mann_whitney(gw, rw)["p"]},
        "weighted_per_post": per_post,
        "verdict": code, "verdict_label": label,
        "best_posts": [post_card(r) for _, r in srt.head(3).iterrows()],
        "worst_posts": [post_card(r) for _, r in srt.tail(3).iloc[::-1].iterrows()],
    }


def explain(c: dict, w: dict) -> str:
    """One plain sentence on what the check found."""
    if c["verdict"] == "not_enough":
        return "Too few posts on one side to compare the actions X weights."
    a = c["actions_per_1k"]
    xw = a["x_weighted"]
    detail = (f"replies {a['replies']['segment']:.2f} vs {a['replies']['rest']:.2f}, likes {a['likes']['segment']:.1f} vs "
              f"{a['likes']['rest']:.1f}, reposts {a['reposts']['segment']:.2f} vs {a['reposts']['rest']:.2f} per 1,000 views")
    rel = c["weighted"]["ratio"]
    head = (f"Per 1,000 views these posts earn {xw['segment']:.1f} X-weighted actions vs {xw['rest']:.1f} for the rest "
            f"({rel:.1f}×, likely range {c['weighted']['lo']:.1f}–{c['weighted']['hi']:.1f}×): {detail}.")
    pp = c["weighted_per_post"]
    totals = (f" Per post (typical): {pp['segment']:,.0f} vs {pp['rest']:,.0f} X-weighted actions."
              if pp.get("segment") is not None and pp.get("rest") is not None else "")
    if c["verdict"] == "backed":
        return head + totals + (" The reach difference goes the same way as the reactions X's code weights, so it "
                                "is consistent with the published ranking.")
    unseen = ", ".join(f"{lbl} ({w[n]['value']:g})" for n, lbl in UNSEEN if n in w)
    dilution = ""
    if (c["reach"]["ratio"] or 0) > 1 and rel < 1:
        dilution = (" Posts that travel further reach more people who don't follow the account, and they react "
                    "less per view, so per-view rates usually fall as reach grows.")
    return head + totals + dilution + (" Public reactions alone don't explain the reach difference. X also weights "
                                       f"actions nobody outside X can count — {unseen} — so that part can't be "
                                       "verified from public data.")


def run(df: pd.DataFrame, segments: list[dict], segments_ex: list[dict]) -> dict:
    """Check every tested segment (all posts, and posts other than X Articles)."""
    w = weights()
    if not w or df.empty:
        return {"available": False, "reason": "published weights or posts unavailable", "items": []}
    min_n = analysis_cfg()["min_segment_n"]
    base = add_weighted(df[df["is_authored"] & df["mature"] & df["views"].notna() & (df["views"] > 0)], w)
    items = []
    for scope, segs, frame in (("all", segments, base),
                               ("ex_articles", segments_ex, base[base["format"] != "x_article"])):
        for s in segs:
            if not s.get("tested") or s["feature"] not in frame.columns:
                continue
            c = check_segment(frame, s["feature"], str(s["level"]), w, min_n)
            c["scope"] = scope
            items.append(c)
    for it, q in zip(items, bh_adjust([i["reach"]["p"] for i in items]), strict=True):
        it["reach"]["q"] = q
        it["reach"]["chance"] = chance_words(q)
        it["explanation"] = explain(it, w)
    used = {n: w[n] for _, n in OBSERVABLE if n in w} | {n: w[n] for n, _ in UNSEEN if n in w}
    if "BookmarkWeight" not in w:
        bookmark_note = ("param.rs has no bookmark weight: bookmarks are shown for context but don't enter the "
                         "published weighted sum.")
    else:
        bookmark_note = ""
    return {"available": True, "proxy_note": PROXY_NOTE, "bookmark_note": bookmark_note,
            "weights": used, "items": items}


def find(check: dict, feature: str, level: str, scope: str) -> dict | None:
    return next((i for i in check.get("items", []) if i["feature"] == feature and i["level"] == str(level)
                 and i["scope"] == scope), None)


def peer_formats(handle: str, min_n: int = 5) -> dict:
    """What works for similar accounts: each peer's formats vs that peer's other posts."""
    from xaudit.analysis.pipeline import prepare
    from xaudit.settings import clients

    w = weights()
    rows = []
    for peer in clients()[handle].get("peers", []):
        df = prepare(peer, window_days=analysis_cfg()["peer_window_days"])
        if df.empty:
            rows.append({"peer": peer, "n": 0})
            continue
        a = df[df["is_authored"] & df["mature"] & df["views"].notna() & (df["views"] > 0)]
        if w:
            a = add_weighted(a, w)
        fm = {}
        for level, g in a.groupby("format"):
            rest = a[a["format"] != level]
            if len(g) < min_n or len(rest) < min_n or rest["views"].median() <= 0:
                continue
            fm[level] = {"n": int(len(g)), "reach_ratio": float(g["views"].median() / rest["views"].median()),
                         "median_views": float(g["views"].median()),
                         "x_weighted_ratio": (_tmean(g["x_weighted_per_1k"].dropna().to_numpy(float))
                                              / max(_tmean(rest["x_weighted_per_1k"].dropna().to_numpy(float)), 1e-9))
                         if w else None}
        rows.append({"peer": peer, "n": int(len(a)), "median_views": float(a["views"].median()) if len(a) else None,
                     "article_share": float((a["format"] == "x_article").mean()) if len(a) else None, "formats": fm})
    with_art = [r for r in rows if "x_article" in (r.get("formats") or {})]
    wins = [r for r in with_art if r["formats"]["x_article"]["reach_ratio"] > 1]
    return {"peers": rows, "peers_with_articles": len(with_art), "articles_win": len(wins),
            "note": "Each peer is compared with its own other posts (newest posts in the peer window); formats with "
                    f"fewer than {min_n} posts are left out."}
