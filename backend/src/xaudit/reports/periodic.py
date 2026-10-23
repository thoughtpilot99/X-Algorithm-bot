"""Weekly performance report and monthly growth audit."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from xaudit.db.session import load_artifact
from xaudit.reports.render import _common, env, render_all
from xaudit.settings import REPORTS_DIR, clients


def write_weekly(today: date, summaries: dict) -> Path:
    alerts = [a for a in (load_artifact("alerts") or {}).get("items", []) if a["status"] == "active"]
    exps = {h: (load_artifact("experiment_results", h) or {}).get("items", []) for h in clients()}
    html = env().get_template("weekly.html.j2").render(
        **_common(), today=today.isoformat(), accounts=summaries, names={h: c["name"] for h, c in clients().items()},
        alerts=alerts, experiments=exps)
    out = REPORTS_DIR / "weekly" / f"{today.isoformat()}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def write_monthly(delta: dict, pdf: bool = True) -> list[str]:
    files = render_all(pdf=pdf)
    folder = REPORTS_DIR / "monthly" / delta["month"]
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for paths in files.values():
        for p in paths:
            src = Path(p)
            if src.suffix in (".html", ".pdf"):
                shutil.copy2(src, folder / src.name)
                out.append(str(folder / src.name))
    html = env().get_template("monthly_delta.html.j2").render(
        **_common(), delta=delta, names={h: c["name"] for h, c in clients().items()})
    p = folder / "month-over-month.html"
    p.write_text(html, encoding="utf-8")
    out.append(str(p))
    return out
