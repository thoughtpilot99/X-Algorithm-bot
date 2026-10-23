"""Daily monitoring run: collect -> re-analyse -> alerts -> experiments -> periodic reports."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import numpy as np

from xaudit.db.session import load_artifact, save_artifact
from xaudit.settings import analysis_cfg, clients


def collect(peers: bool, threads_cap: int) -> list[dict]:
    from xaudit.ingest import collectors
    from xaudit.ingest.console_client import ConsoleClient, ConsoleError

    cc = ConsoleClient()
    if not cc.available():
        raise ConsoleError("XP_API_KEY not set")
    cfg = clients()
    handles = list(cfg)
    out = [collectors.collect_profiles(cc, handles + ([p for c in cfg.values() for p in c.get("peers", [])]
                                                      if peers else []))]
    for h, c in cfg.items():
        out.append(collectors.collect_timeline(cc, h, days=14))
        out.append(collectors.collect_engagers(cc, h))
        out.append(collectors.collect_threads_for_new_comments(cc, h, cap=threads_cap))
        if peers:
            for p in c.get("peers", []):
                out.append(collectors.collect_timeline(cc, p, days=14, include_replies=False, max_pages=5))
    return out


def weekly_summary(handle: str, df, today: date) -> dict:  # noqa: ANN001
    import pandas as pd

    end = pd.Timestamp(today, tz="UTC")
    wk = df[(df["created_at"] >= end - pd.Timedelta(days=7)) & (df["created_at"] < end)]
    prev = df[(df["created_at"] >= end - pd.Timedelta(days=35)) & (df["created_at"] < end - pd.Timedelta(days=7))]
    a, pa = wk[wk["is_authored"]], prev[prev["is_authored"]]
    conv = wk[wk["reply_role"] == "conversation"]
    cols = ["tweet_id", "url", "created_at", "format", "text", "views", "vs_baseline", "mature"]

    def rows(g):  # noqa: ANN001, ANN202
        g = g[cols].copy()
        g["created_at"] = g["created_at"].dt.strftime("%Y-%m-%d")
        g["text"] = g["text"].str.slice(0, 200)
        return g.replace({np.nan: None}).to_dict("records")

    return {
        "handle": handle, "week_ending": today.isoformat(),
        "authored_n": int(len(a)), "authored_median_views": float(a["views"].median()) if len(a) else None,
        "prior_4wk_weekly_median_views": float(pa["views"].median()) if len(pa) else None,
        "median_vs_baseline": float(a["vs_baseline"].median()) if a["vs_baseline"].notna().any() else None,
        "immature_share": float((~a["mature"]).mean()) if len(a) else None,
        "conversational_comments": int(len(conv)),
        "comment_median_views": float(conv["views"].median()) if len(conv) else None,
        "fulfilment_replies": int((wk["reply_role"] == "fulfilment").sum()),
        "top": rows(a.sort_values("views", ascending=False).head(3)),
        "bottom": rows(a[a["mature"]].sort_values("views").head(3)),
    }


def monthly_delta() -> dict:
    """Key metrics this month vs the previous stored snapshot."""
    from xaudit.recommend.compare import account_metrics

    hist = load_artifact("monthly_history") or {"items": []}
    # Run on the 1st, the audit covers the month that just ended.
    month = (date.today() - timedelta(days=1)).strftime("%Y-%m")
    cur = {h: account_metrics(h) for h in clients()}
    prev = next((x for x in reversed(hist["items"]) if x["month"] != month), None)
    hist["items"] = [x for x in hist["items"] if x["month"] != month] + [{"month": month, "metrics": cur}]
    save_artifact("monthly_history", hist)
    return {"month": month, "current": cur, "previous": prev}


def run(*, dry_run: bool = False, peers: bool | None = None, threads_cap: int = 40,
        weekly: bool | None = None, monthly: bool | None = None, pdf: bool = True) -> dict:
    from xaudit.algo import param_extract
    from xaudit.analysis.pipeline import prepare
    from xaudit.analysis.pipeline import run as analyze
    from xaudit.diagnostics.engine import run as diagnose
    from xaudit.monitor import alerts, experiments
    from xaudit.recommend.compare import compare
    from xaudit.recommend.engine import run as recommend

    today = datetime.now(UTC).date()
    peers = today.weekday() == 0 if peers is None else peers
    weekly = today.weekday() == 0 if weekly is None else weekly
    monthly = today.day == 1 if monthly is None else monthly
    summary: dict = {"date": today.isoformat(), "dry_run": dry_run}
    if not dry_run:
        summary["collection"] = collect(peers, threads_cap)
    try:
        param_extract.extract_history(10)
    except Exception as e:  # noqa: BLE001  (repo may be absent locally)
        summary["param_history_error"] = str(e)
    summary["analysis"] = analyze()
    frames = {}
    current_alerts = alerts.collection_alerts() + alerts.repo_alerts()
    for h in clients():
        diagnose(h)
        recommend(h)
        df = prepare(h, window_days=analysis_cfg()["extended_window_days"])
        frames[h] = df
        current_alerts += alerts.reach_alerts(h, df) + alerts.follower_alerts(h)
    compare()
    summary["alerts"] = len(alerts.update(current_alerts)["items"])
    summary["experiments"] = {h: [e["status"] for e in v] for h, v in experiments.evaluate_all(frames).items()}
    from xaudit.reports import periodic

    if weekly:
        ws = {h: weekly_summary(h, frames[h], today) for h in frames}
        save_artifact("weekly_latest", {"date": today.isoformat(), "accounts": ws})
        summary["weekly_report"] = str(periodic.write_weekly(today, ws))
    if monthly:
        summary["monthly_report"] = periodic.write_monthly(monthly_delta(), pdf=pdf)
    save_artifact("monitor_last_run", summary)
    return summary
