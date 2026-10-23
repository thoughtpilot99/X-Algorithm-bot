"""Daily Slack digest of the end-to-end analysis, posted through an incoming webhook.

The digest is built only from stored artifacts and the posts table, so it says
exactly what the dashboard and reports say. Set SLACK_WEBHOOK_URL to enable it.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime

import httpx
import pandas as pd

from xaudit.db.session import load_artifact
from xaudit.monitor.timeseries import follower_series
from xaudit.settings import analysis_cfg, clients

REPO_URL = "https://github.com/thoughtpilot99/X-Algorithm-bot"


def _n(v) -> str:  # noqa: ANN001
    return "–" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{v:,.0f}"


def _x(v) -> str:  # noqa: ANN001
    return "–" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{v:.2f}x"


def _trim(text: str, n: int = 110) -> str:
    t = " ".join((text or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


def account_section(handle: str, df: pd.DataFrame, now: datetime) -> list[dict]:
    name = clients()[handle]["name"]
    end = pd.Timestamp(now)
    day = df[df["created_at"] >= end - pd.Timedelta(hours=24)]
    week = df[df["created_at"] >= end - pd.Timedelta(days=7)]
    prior = df[(df["created_at"] < end - pd.Timedelta(days=7)) & (df["created_at"] >= end - pd.Timedelta(days=35))]
    a7, ap = week[week["is_authored"]], prior[prior["is_authored"]]
    a1 = day[day["is_authored"]]
    conv1 = day[day["reply_role"] == "conversation"]
    ful1 = int((day["reply_role"] == "fulfilment").sum())

    fs = follower_series(handle)
    fol = fs[-1]["followers"] if fs else None
    fol_delta = (fs[-1]["followers"] - fs[-2]["followers"]) if len(fs) >= 2 else None
    fol_txt = f"{_n(fol)}" + (f" ({fol_delta:+,} since last snapshot)" if fol_delta is not None else " (first snapshot)")

    lines = [
        f"*Followers:* {fol_txt}",
        f"*Last 24h:* {len(a1)} posts · {len(conv1)} comments on others' posts · {ful1} lead-magnet replies",
        f"*Last 7 days:* {len(a7)} posts, median {_n(a7['views'].median() if len(a7) else None)} views "
        f"(previous 4 weeks: {_n(ap['views'].median() if len(ap) else None)})"
        + (f"; {int((~a7['mature']).sum())} still under 72h old" if len(a7) and (~a7["mature"]).any() else ""),
    ]
    mature7 = a7[a7["mature"] & a7["vs_baseline"].notna()]
    if len(mature7):
        lines.append(f"*vs own baseline (mature posts, 7d):* median {_x(mature7['vs_baseline'].median())}")
    top = a7.sort_values("views", ascending=False).head(2)
    for _, r in top.iterrows():
        lines.append(f"• <{r['url']}|{_n(r['views'])} views> ({str(r['format']).replace('_', ' ')}): "
                     f"{_trim(r['text'])}")
    weak = a7[a7["mature"]].sort_values("vs_baseline").head(1)
    for _, r in weak.iterrows():
        if pd.notna(r["vs_baseline"]):
            lines.append(f"• Weakest mature post: <{r['url']}|{_x(r['vs_baseline'])} baseline>: {_trim(r['text'], 80)}")

    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{name} (@{handle})"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}},
    ]
    exps = (load_artifact("experiment_results", handle) or {}).get("items", [])
    running = [e for e in exps if e.get("status") not in (None, "not_started")]
    if running:
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": "Experiments: " + "; ".join(
            f"{e['title']} — {e['status'].replace('_', ' ')}"
            + (f" ({_x(e.get('ratio'))}, n={e.get('n_treatment')}/{e.get('n_control')})" if e.get("ratio") else "")
            for e in running)}]})
    rec = load_artifact("recommendations", handle) or {}
    roots = rec.get("root_causes", [])[:3]
    if roots:
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": "Top barriers: " + "; ".join(
            f"{r['rank']}. {r['issue']} ({r['confidence']})" for r in roots)}]})
    return blocks


def build_digest(now: datetime | None = None) -> dict:
    from xaudit.analysis.pipeline import prepare

    now = now or datetime.now(UTC)
    last = load_artifact("monitor_last_run") or {}
    alerts = [a for a in (load_artifact("alerts") or {}).get("items", []) if a.get("status") == "active"]
    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": f"X audit · daily digest · {now:%a %d %b %Y}"}},
    ]
    runs = last.get("collection") or []
    if runs:
        ok = sum(1 for r in runs if r.get("status") in ("succeeded", None) and not r.get("error"))
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text":
                       f"Collection: {ok}/{len(runs)} steps succeeded · run {last.get('date', '')}"}]})
    if alerts:
        txt = "\n".join(f"• *{a['title']}* ({a['handle']}): {a['detail']}" for a in alerts[:6])
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f":rotating_light: *Alerts*\n{txt}"}})
    else:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text":
                       "No active alerts: weekly reach is inside its normal range (or history is still too short)."}})
    for h in clients():
        df = prepare(h, window_days=analysis_cfg()["extended_window_days"])
        if df.empty:
            continue
        blocks.append({"type": "divider"})
        blocks.extend(account_section(h, df, now))
    blocks.append({"type": "divider"})
    links = f"<{REPO_URL}/tree/claude/charming-hawking-pqaz1d/reports|Reports> · <{REPO_URL}/actions|Runs>"
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text":
                   f"{links} · public data only · associations are not causes"}]})
    return {"text": f"X audit daily digest {now:%Y-%m-%d}", "blocks": blocks[:50]}


def post(payload: dict, webhook: str | None = None, transport: httpx.BaseTransport | None = None) -> bool:
    webhook = webhook or os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook:
        return False
    with httpx.Client(timeout=30, transport=transport) as c:
        for attempt in range(3):
            r = c.post(webhook, json=payload)
            if r.status_code == 200:
                return True
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(float(r.headers.get("Retry-After", 2 * (attempt + 1))))
                continue
            raise RuntimeError(f"Slack webhook returned {r.status_code}: {r.text[:200]}")
    raise RuntimeError("Slack webhook: retries exhausted")
