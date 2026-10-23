"""HTTP API for the dashboard. Read-only over stored artifacts."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from xaudit.algo import indexer, param_extract, registry
from xaudit.db.models import AlgoParam
from xaudit.db.session import load_artifact, session
from xaudit.recommend.compare import final_answers
from xaudit.settings import REPO_ROOT, REPORTS_DIR, clients

ARTIFACT_KINDS = {"profile", "reach", "reach_90d", "engagement", "segments", "multivariable", "strong_weak",
                  "cadence", "comments", "benchmark", "completeness", "diagnostics", "recommendations"}

app = FastAPI(title="X Account Intelligence & Algorithm Audit", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def _client(handle: str) -> dict:
    c = clients().get(handle)
    if c is None:
        raise HTTPException(404, f"unknown account {handle}")
    return c


def _art(kind: str, handle: str = "_global") -> dict | list:
    a = load_artifact(kind, handle)
    if a is None:
        raise HTTPException(404, f"artifact {kind} not computed for {handle}; run `xaudit run`")
    return a


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/accounts")
def accounts() -> list[dict]:
    out = []
    for h, c in clients().items():
        prof = load_artifact("profile", h) or {}
        reach = load_artifact("reach", h) or {}
        out.append({"handle": h, "name": c["name"], "company": c.get("company"),
                    "followers": prof.get("followers"), "window": prof.get("window"),
                    "authored_median_views": reach.get("segments", {}).get("authored (original + quote)", {})
                    .get("median"), "peers": c.get("peers", [])})
    return out


@app.get("/api/accounts/{handle}/overview")
def overview(handle: str) -> dict:
    c = _client(handle)
    rec = load_artifact("recommendations", handle) or {}
    return {
        "handle": handle, "name": c["name"], "profile": _art("profile", handle),
        "reach": _art("reach", handle), "reach_90d": _art("reach_90d", handle),
        "comments_summary": {k: (_art("comments", handle) or {}).get(k) for k in
                             ("roles", "conversation", "fulfilment", "concentration")},
        "root_causes": rec.get("root_causes", []), "actions": rec.get("actions", {}),
        "completeness": _art("completeness", handle),
    }


@app.get("/api/accounts/{handle}/artifacts/{kind}")
def artifact(handle: str, kind: str):  # noqa: ANN201
    _client(handle)
    if kind not in ARTIFACT_KINDS:
        raise HTTPException(404, f"unknown artifact {kind}")
    return _art(kind, handle)


def _filter_posts(posts: list[dict], start: str | None, end: str | None, types: list[str] | None,
                  topic: str | None, segment: str | None) -> list[dict]:
    out = []
    for p in posts:
        d = (p.get("created_at") or "")[:10]
        if start and d < start or end and d > end:
            continue
        if types and p.get("post_type") not in types:
            continue
        if topic and p.get("topic") != topic:
            continue
        vb = p.get("vs_baseline")
        if segment == "above_2x" and not (vb is not None and vb >= 2):
            continue
        if segment == "below_half" and not (vb is not None and vb <= 0.5):
            continue
        if segment == "near_baseline" and not (vb is not None and 0.5 < vb < 2):
            continue
        out.append(p)
    return out


@app.get("/api/accounts/{handle}/posts")
def posts(handle: str, start: str | None = None, end: str | None = None,
          type: list[str] | None = Query(default=None), topic: str | None = None,  # noqa: A002
          segment: str | None = Query(default=None, pattern="^(above_2x|below_half|near_baseline)$"),
          limit: int = Query(default=2000, le=5000)) -> dict:
    _client(handle)
    rows = _filter_posts(_art("posts", handle), start, end, type, topic, segment)
    return {"total": len(rows), "items": rows[-limit:][::-1]}


@app.get("/api/accounts/{handle}/posts.csv")
def posts_csv(handle: str, start: str | None = None, end: str | None = None,
              type: list[str] | None = Query(default=None), topic: str | None = None,  # noqa: A002
              segment: str | None = None) -> StreamingResponse:
    _client(handle)
    rows = _filter_posts(_art("posts", handle), start, end, type, topic, segment)
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={handle}_posts.csv"})


@app.get("/api/accounts/{handle}/answers")
def answers(handle: str) -> list[dict]:
    _client(handle)
    return final_answers(handle)


@app.get("/api/comparison")
def comparison() -> dict:
    return _art("comparison")


@app.get("/api/algo/findings")
def findings(area: str | None = None) -> list[dict]:
    return [f for f in registry.findings() if area is None or f.get("area") == area]


@app.get("/api/algo/claims")
def claims() -> list[dict]:
    return registry.claims()


@app.get("/api/algo/params")
def params(name: str | None = None) -> dict:
    cur = param_extract.current()
    weights = [p for p in cur if p["name"].endswith("Weight") or "Diversity" in p["name"] or "Oon" in p["name"]
               or "ColdStart" in p["name"]]
    hist: list[dict] = []
    if name:
        with session() as s:
            rows = s.execute(select(AlgoParam).where(AlgoParam.name == name).order_by(AlgoParam.committed_at)).scalars()
            hist = [{"sha": r.sha[:7], "committed_at": r.committed_at.isoformat() if r.committed_at else None,
                     "path": r.path, "value": r.raw_value} for r in rows]
    return {"studied_sha": registry.STUDIED_SHA, "key_params": weights, "history": hist}


@app.get("/api/algo/search")
def algo_search(q: str = Query(min_length=2), limit: int = Query(default=10, le=50)) -> list[dict]:
    return indexer.search(q, limit)


@app.get("/api/reports")
def reports() -> list[dict]:
    if not REPORTS_DIR.exists():
        return []
    return [{"name": p.name, "url": f"/reports/{p.relative_to(REPORTS_DIR).as_posix()}", "bytes": p.stat().st_size}
            for p in sorted(REPORTS_DIR.rglob("*")) if p.is_file()]


if REPORTS_DIR.exists():
    app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

DIST = REPO_ROOT / "frontend" / "dist"


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):  # noqa: ANN201
    """Serve the built dashboard (frontend/dist) with SPA fallback."""
    if not DIST.exists():
        raise HTTPException(404, "dashboard not built; run `npm run build` in frontend/")
    f = DIST / path
    if path and f.is_file() and DIST in f.resolve().parents:
        return FileResponse(f)
    return FileResponse(Path(DIST) / "index.html")
