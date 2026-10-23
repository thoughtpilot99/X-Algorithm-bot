"""Export the dashboard's API responses as static JSON for a snapshot page.

Every file is produced by calling the live API in-process, so the snapshot shows
exactly what the running dashboard would.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from xaudit.settings import REPORTS_DIR, clients

ACCOUNT_ROUTES = {
    "overview.json": "/api/accounts/{h}/overview",
    "posts.json": "/api/accounts/{h}/posts?limit=5000",
    "answers.json": "/api/accounts/{h}/answers",
    "alerts.json": "/api/accounts/{h}/alerts",
    "experiments.json": "/api/accounts/{h}/experiments",
    "followers.json": "/api/accounts/{h}/timeseries/followers",
}
ARTIFACTS = ["reach", "segments", "multivariable", "comments", "benchmark", "engagement", "diagnostics",
             "recommendations"]


def _dump(path: Path, obj) -> None:  # noqa: ANN001
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def export(out: Path) -> dict:
    from xaudit.api.app import app

    c = TestClient(app)

    def get(route: str):  # noqa: ANN202
        r = c.get(route)
        r.raise_for_status()
        return r.json()

    data = out / "data"
    files: list[str] = []

    def put(rel: str, obj) -> None:  # noqa: ANN001
        _dump(data / rel, obj)
        files.append(f"data/{rel}")

    accounts = get("/api/accounts")
    put("accounts.json", accounts)
    put("comparison.json", get("/api/comparison"))
    put("monitor.json", get("/api/monitor"))
    put("algo/findings.json", get("/api/algo/findings"))
    put("algo/claims.json", get("/api/algo/claims"))
    params = get("/api/algo/params")
    params["histories"] = {p["name"]: get(f"/api/algo/params?name={p['name']}")["history"]
                           for p in params["key_params"]}
    put("algo/params.json", params)
    for h in clients():
        for name, route in ACCOUNT_ROUTES.items():
            put(f"{h}/{name}", get(route.format(h=h)))
        for kind in ARTIFACTS:
            put(f"{h}/artifacts/{kind}.json", get(f"/api/accounts/{h}/artifacts/{kind}"))

    reports = []
    (out / "reports").mkdir(parents=True, exist_ok=True)
    for pdf in sorted(REPORTS_DIR.glob("report-*.pdf")):
        shutil.copy2(pdf, out / "reports" / pdf.name)
        files.append(f"reports/{pdf.name}")
        reports.append({"name": pdf.name, "url": f"reports/{pdf.name}", "bytes": pdf.stat().st_size})
    put("reports.json", reports)
    windows = [a["window"] for a in accounts if a.get("window")]
    put("meta.json", {
        "snapshot_at": datetime.now(UTC).isoformat(timespec="minutes"),
        "data_from": min(w[0] for w in windows)[:10] if windows else None,
        "data_to": max(w[1] for w in windows)[:10] if windows else None,
    })
    return {"out": str(out), "files": len(files), "paths": files}


def publish_page(dist: Path, name: str = "dashboard.html") -> Path:
    """Write a single publishable page from a static Vite build.

    The page is the body content only (the artifact host adds the document
    skeleton), with the built CSS and JS inlined; the data JSON and report PDFs
    stay as separate files fetched by relative URL.
    """
    import re

    html = (dist / "index.html").read_text(encoding="utf-8")
    css = "".join((dist / m).read_text(encoding="utf-8")
                  for m in re.findall(r'<link rel="stylesheet" crossorigin href="\./([^"]+\.css)"', html))
    js = "".join((dist / m).read_text(encoding="utf-8")
                 for m in re.findall(r'<script type="module" crossorigin src="\./([^"]+\.js)"', html))
    js = js.replace("</script", "<\\/script")
    fonts = re.search(r'<link rel="stylesheet" href="(https://fonts\.googleapis\.com/[^"]+)"', html)
    page = "\n".join([
        "<title>X Audit Dashboard</title>",
        '<meta name="claude:viewport-fit-sides" content="cover">',
        f'<link rel="stylesheet" href="{fonts.group(1)}">' if fonts else "",
        f"<style>{css}</style>",
        '<div id="root"></div>',
        f'<script type="module">{js}</script>',
    ])
    out = dist / name
    out.write_text(page, encoding="utf-8")
    return out
