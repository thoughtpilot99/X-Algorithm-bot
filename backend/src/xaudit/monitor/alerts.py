"""Control-limit alerts that avoid firing on normal variation.

Weekly medians of log views are compared with the account's own trailing weeks:
an alert fires only when the latest complete week falls outside
median ± k · 1.4826 · MAD of the previous ``window`` weeks (a robust 3-sigma band),
and only with enough history. Alerts are keyed so the same condition is
reported once, then marked resolved when it clears.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import select

from xaudit.db.models import AlgoParam, CollectionRun
from xaudit.db.session import load_artifact, save_artifact, session
from xaudit.monitor.timeseries import follower_series
from xaudit.settings import config

DEFAULTS = {"k": 3.0, "window_weeks": 8, "min_history_weeks": 6, "mad_floor_log": 0.15, "abrupt_drop": 0.5,
            "min_posts_per_week": 3}


def cfg() -> dict:
    return {**DEFAULTS, **(config().get("alerts") or {})}


def control_check(history: list[float], latest: float, *, k: float, mad_floor: float) -> dict:
    h = np.asarray(history, dtype=float)
    med = float(np.median(h))
    mad = max(float(np.median(np.abs(h - med))) * 1.4826, mad_floor)
    lo, hi = med - k * mad, med + k * mad
    return {"median": med, "lo": lo, "hi": hi, "latest": latest,
            "outside": latest < lo or latest > hi, "direction": "down" if latest < lo else "up" if latest > hi else None}


def weekly_log_medians(df: pd.DataFrame, min_posts: int) -> pd.DataFrame:
    a = df[df["is_authored"] & df["mature"] & df["views"].notna() & (df["views"] > 0)].copy()
    if a.empty:
        return pd.DataFrame(columns=["week", "format", "n", "log_median"])
    a["week"] = a["created_at"].dt.tz_convert(None).dt.to_period("W-SUN").dt.start_time
    groups = [((week, fmt), g) for (week, fmt), g in a.groupby(["week", "format"])]
    groups += [((week, "all"), g) for week, g in a.groupby("week")]
    rows = []
    for (week, fmt), g in groups:
        if len(g) >= (min_posts if fmt == "all" else 2):
            rows.append({"week": week, "format": fmt, "n": len(g), "log_median": float(np.log(g["views"].median()))})
    return pd.DataFrame(rows, columns=["week", "format", "n", "log_median"])


def reach_alerts(handle: str, df: pd.DataFrame, today: datetime | None = None) -> list[dict]:
    c = cfg()
    today = today or datetime.now(UTC)
    w = weekly_log_medians(df, c["min_posts_per_week"])
    if w.empty:
        return []
    # Latest COMPLETE week whose posts are all mature (ends >= 3 days ago).
    cutoff = pd.Timestamp(today.replace(tzinfo=None)) - pd.Timedelta(days=10)
    out = []
    for fmt, g in w.groupby("format"):
        g = g.sort_values("week")
        done = g[g["week"] <= cutoff]
        if len(done) < c["min_history_weeks"] + 1:
            continue
        last = done.iloc[-1]
        hist = done.iloc[-(c["window_weeks"] + 1):-1]["log_median"].tolist()
        chk = control_check(hist, last["log_median"], k=c["k"], mad_floor=c["mad_floor_log"])
        if chk["outside"]:
            out.append({
                "key": f"{handle}:reach:{fmt}:{last['week'].date()}", "handle": handle, "kind": "reach",
                "severity": "high" if fmt == "all" else "medium",
                "title": f"Weekly median views {'below' if chk['direction'] == 'down' else 'above'} control limits"
                         f" ({'all formats' if fmt == 'all' else fmt})",
                "detail": f"Week of {last['week'].date()}: median {np.exp(chk['latest']):.0f} views (n={int(last['n'])}) "
                          f"vs trailing median {np.exp(chk['median']):.0f}, band {np.exp(chk['lo']):.0f}–"
                          f"{np.exp(chk['hi']):.0f}.",
                "evidence_class": "statistical_association",
            })
            if fmt == "all" and chk["direction"] == "down":
                prev4 = float(np.exp(np.median(hist[-4:])))
                drop = 1 - float(np.exp(chk["latest"])) / prev4
                if drop >= c["abrupt_drop"]:
                    out.append({
                        "key": f"{handle}:abrupt:{last['week'].date()}", "handle": handle, "kind": "abrupt_change",
                        "severity": "high",
                        "title": "Abrupt cross-format drop — investigate before acting",
                        "detail": f"Median views fell {drop:.0%} vs the previous 4 weeks across all formats. "
                                  "Check format mix, collection coverage and platform changes first; this is not "
                                  "evidence of a visibility restriction.",
                        "evidence_class": "account_observed",
                    })
    return out


def follower_alerts(handle: str) -> list[dict]:
    s = follower_series(handle)
    if len(s) < 35:
        return []
    f = pd.Series([x["followers"] for x in s], index=pd.to_datetime([x["day"] for x in s])).asfreq("D").ffill()
    weekly = f.diff(7).dropna()
    if len(weekly) < 28:
        return []
    hist, latest = weekly.iloc[-29:-1].tolist(), float(weekly.iloc[-1])
    chk = control_check(hist, latest, k=cfg()["k"], mad_floor=5.0)
    if not chk["outside"]:
        return []
    return [{"key": f"{handle}:followers:{weekly.index[-1].date()}", "handle": handle, "kind": "followers",
             "severity": "medium", "title": f"7-day follower change {chk['direction']} vs normal",
             "detail": f"{latest:+.0f} followers in 7 days vs typical {chk['median']:+.0f}.",
             "evidence_class": "account_observed"}]


def collection_alerts(hours: int = 36) -> list[dict]:
    # SQLite stores naive UTC timestamps; compare like with like.
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)
    with session() as s:
        runs = [r for r in s.execute(select(CollectionRun)).scalars().all()
                if r.started_at and r.started_at.replace(tzinfo=None) >= since]
    out = []
    for r in runs:
        if r.status in ("failed", "empty", "cancelled") or (r.coverage or "").startswith("partial"):
            out.append({"key": f"collection:{r.actor}:{(r.params or {}).get('username') or (r.params or {}).get('handle')}:"
                               f"{r.started_at.date()}",
                        "handle": (r.params or {}).get("username") or (r.params or {}).get("handle") or "_global",
                        "kind": "collection", "severity": "medium",
                        "title": f"Collection {r.status}: {r.actor}",
                        "detail": (r.error or r.coverage or "")[:300], "evidence_class": "account_observed"})
    return out


def repo_alerts(days: int = 8) -> list[dict]:
    since = datetime.now(UTC) - timedelta(days=days)
    keys = ("Weight", "Diversity", "Oon", "ColdStart", "MaxPostAge")
    with session() as s:
        rows = s.execute(select(AlgoParam).order_by(AlgoParam.path, AlgoParam.name, AlgoParam.committed_at)).scalars()
        prev: dict[tuple[str, str], str] = {}
        out = []
        for r in rows:
            k = (r.path, r.name)
            changed = k in prev and prev[k] != r.raw_value
            if changed and any(x in r.name for x in keys) and r.committed_at and r.committed_at.replace(
                    tzinfo=r.committed_at.tzinfo or UTC) >= since:
                out.append({"key": f"repo:{r.path}:{r.name}:{r.sha[:7]}", "handle": "_global", "kind": "repo_change",
                            "severity": "low", "title": f"Published parameter changed: {r.name}",
                            "detail": f"{r.path}: {prev[k]} → {r.raw_value} (commit {r.sha[:7]}). Review findings "
                                      "that cite it.", "evidence_class": "repo_verified"})
            prev[k] = r.raw_value
    try:
        from xaudit.algo import registry

        moved = registry.verify()["moved_since_studied"]
    except Exception:  # noqa: BLE001
        moved = []
    if moved:
        out.append({"key": f"repo:citations:{len(moved)}", "handle": "_global", "kind": "citation_drift",
                    "severity": "medium", "title": f"{len(moved)} citation(s) no longer match at HEAD",
                    "detail": "Findings to re-verify: " + ", ".join(moved[:15]), "evidence_class": "repo_verified"})
    return out


def update(current: list[dict]) -> dict:
    """Merge today's alerts into the stored history: new -> active, missing -> resolved."""
    now = datetime.now(UTC).isoformat(timespec="seconds")
    store = load_artifact("alerts") or {"items": []}
    by_key = {a["key"]: a for a in store["items"]}
    live = {a["key"] for a in current}
    for a in current:
        if a["key"] in by_key:
            by_key[a["key"]].update({**a, "last_seen": now, "status": "active"})
        else:
            by_key[a["key"]] = {**a, "first_seen": now, "last_seen": now, "status": "active"}
    for k, a in by_key.items():
        if k not in live and a["status"] == "active" and a["kind"] in ("collection", "citation_drift"):
            a["status"] = "resolved"
    items = sorted(by_key.values(), key=lambda a: a["last_seen"], reverse=True)[:500]
    out = {"items": items, "updated_at": now}
    save_artifact("alerts", out)
    return out
