"""Render Reports A/B/C (HTML + PDF) and CSV exports from stored artifacts."""

from __future__ import annotations

import csv
import math
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import func, select

from xaudit.algo import registry, repo_sync
from xaudit.db.models import Engager
from xaudit.db.session import load_artifact, session
from xaudit.recommend.compare import compare, final_answers
from xaudit.settings import ALGO_REPO_URL, REPORTS_DIR, clients

TEMPLATES = Path(__file__).resolve().parent / "templates"


def _isnum(v) -> bool:  # noqa: ANN001
    return isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v))


def _num(v) -> str:  # noqa: ANN001
    return f"{v:,.0f}" if _isnum(v) else "–"


def _rn(nd: int):  # noqa: ANN202
    return lambda v: f"{v:.{nd}f}" if _isnum(v) else "–"


def _pct(v, nd: int = 0) -> str:  # noqa: ANN001
    return f"{v * 100:.{nd}f}%" if _isnum(v) else "–"


def _fmt(v, f: str) -> str:  # noqa: ANN001
    return {"num": _num, "pct": _pct, "r2": _rn(2), "r1": _rn(1)}.get(f, str)(v)


def _ev(v) -> str:  # noqa: ANN001
    if isinstance(v, float) and v.is_integer():
        return f"{int(v):,}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def env() -> Environment:
    e = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]))
    e.filters.update(ev=_ev, num=_num, r1=_rn(1), r2=_rn(2), r3=_rn(3), pct=_pct, fmt=_fmt)
    return e


def monthly_svg(monthly: list[dict], w: int = 900, h: int = 170) -> str:
    rows = [m for m in monthly if m.get("authored_median_views")]
    if not rows:
        return ""
    mx = max(m["authored_median_views"] for m in rows)
    bw = (w - 40) / len(rows)
    parts = [f'<svg viewBox="0 0 {w} {h + 30}" width="100%" role="img" aria-label="Monthly median views">']
    for i, m in enumerate(rows):
        bh = (m["authored_median_views"] / mx) * (h - 20)
        x = 30 + i * bw
        parts.append(f'<rect x="{x + 6:.1f}" y="{h - bh:.1f}" width="{bw - 12:.1f}" height="{bh:.1f}" fill="#2f5bd3" '
                     f'opacity="0.85"><title>{m["month"]}: {m["authored_median_views"]:,.0f}</title></rect>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{h + 14}" text-anchor="middle">{m["month"]}</text>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{h - bh - 4:.1f}" text-anchor="middle">'
                     f'{m["authored_median_views"]:,.0f} (n={m["authored_n"]})</text>')
    parts.append("</svg>")
    return "".join(parts)


def _engagers(handle: str) -> list[dict]:
    with session() as s:
        rows = s.execute(select(Engager.engager_handle, func.count()).where(Engager.client_handle == handle)
                         .group_by(Engager.engager_handle).order_by(func.count().desc()).limit(20)).all()
    return [{"handle": h, "n": n} for h, n in rows]


def _common() -> dict:
    st = repo_sync.head()
    return {"css": (TEMPLATES / "base.css").read_text(encoding="utf-8"),
            "generated": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
            "repo_url": ALGO_REPO_URL, "sha": registry.STUDIED_SHA, "head_sha": st.sha}


def account_context(handle: str, letter: str) -> dict:
    c = clients()[handle]
    diags = (load_artifact("diagnostics", handle) or {}).get("items", [])
    used = sorted({f for d in diags for f in d["algo_links"]})
    return {
        **_common(), "letter": letter, "handle": handle, "name": c["name"],
        "profile": load_artifact("profile", handle), "window": load_artifact("profile", handle)["window"],
        "reach": load_artifact("reach", handle), "reach90": load_artifact("reach_90d", handle),
        "engagement": load_artifact("engagement", handle), "segments": load_artifact("segments", handle),
        "mv": load_artifact("multivariable", handle), "cadence": load_artifact("cadence", handle),
        "comments": load_artifact("comments", handle), "bench": load_artifact("benchmark", handle),
        "completeness": load_artifact("completeness", handle), "rec": load_artifact("recommendations", handle),
        "diagnostics": diags, "used_findings": [registry.by_id(f) for f in used if registry.by_id(f)],
        "answers": final_answers(handle), "claims": registry.claims(),
        "monthly_svg": monthly_svg(load_artifact("reach", handle)["monthly"]), "engagers": _engagers(handle),
    }


def compare_context() -> dict:
    cmp = compare()
    hs = list(clients())
    seg = {}
    for h in hs:
        s = [x for x in load_artifact("segments", h) or [] if x["signal"] in ("higher", "lower")
             and x["feature"] in ("format", "topic", "hook_type", "narrative", "length_bucket")]
        seg[h] = sorted(s, key=lambda x: -x["ratio"])[:5] + sorted(s, key=lambda x: x["ratio"])[:4]
    rows = [("followers", "Followers (snapshot)", "num"),
            ("authored_median_views_90d", "Median views per authored post (90d)", "num"),
            ("median_views_per_1k_followers", "Median views per 1k followers (90d)", "r1"),
            ("median_eng_per_1k_views", "Engagements per 1k views", "r1"),
            ("median_likes_per_1k", "Likes per 1k views", "r2"),
            ("median_replies_per_1k", "Replies per 1k views", "r2"),
            ("median_bookmarks_per_1k", "Bookmarks per 1k views", "r2"),
            ("authored_per_week", "Authored posts per week", "r1"),
            ("share_article", "Share of output as X Articles (90d)", "pct"),
            ("article_lift", "X Article median vs other formats", "r2"),
            ("trend_per_30d", "Reach trend per 30 days (multiplier)", "r2"),
            ("top5pct_share_of_views", "Share of views from top 5% posts", "pct"),
            ("third_post_vs_baseline", "3rd+ same-day post vs baseline", "r2")]
    comment_rows = [("replies_per_week", "Replies per week (all roles)", "r1"),
                    ("conversational_comments", "Conversational comments (mature)", "num"),
                    ("fulfilment_replies", "Lead-magnet fulfilment replies", "num"),
                    ("median_views_per_comment", "Median views per comment", "num"),
                    ("substantive_comment_share", "Substantive comment share", "pct"),
                    ("comment_top5_share", "Share of comments to top-5 accounts", "pct")]
    roots = {h: (load_artifact("recommendations", h) or {}).get("root_causes", []) for h in hs}
    return {**_common(), "cmp": cmp, "handles": hs, "names": [clients()[h]["name"] for h in hs], "rows": rows,
            "comment_rows": comment_rows, "seg": seg, "roots": roots}


def html_to_pdf(html_path: Path, pdf_path: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    import os

    exe = "/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").exists() else None
    with sync_playwright() as p:
        kw = {"executable_path": exe} if exe and os.access(exe, os.X_OK) else {}
        try:
            browser = p.chromium.launch(**kw)
        except Exception:  # noqa: BLE001
            browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri())
        page.pdf(path=str(pdf_path), format="A4", print_background=True,
                 margin={"top": "14mm", "bottom": "14mm", "left": "10mm", "right": "10mm"})
        browser.close()
    return True


def write_csvs(handle: str, outdir: Path) -> list[Path]:
    out = []

    def dump(name: str, rows: list[dict]) -> None:
        if not rows:
            return
        p = outdir / f"{handle}_{name}.csv"
        keys = list(dict.fromkeys(k for r in rows for k in r))
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in rows:
                w.writerow({k: (str(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})
        out.append(p)

    dump("posts", load_artifact("posts", handle) or [])
    dump("comments_scored", (load_artifact("comments", handle) or {}).get("scored_replies", []))
    dump("segments", load_artifact("segments", handle) or [])
    dump("diagnostics", [{k: v for k, v in d.items() if k not in ("evidence", "algo_findings")}
                         for d in (load_artifact("diagnostics", handle) or {}).get("items", [])])
    rec = load_artifact("recommendations", handle) or {}
    dump("experiments", rec.get("plan", {}).get("experiments", []))
    dump("rewrites", rec.get("rewrites", []))
    dump("benchmark", (load_artifact("benchmark", handle) or {}).get("comparison", []))
    return out


def render_all(pdf: bool = True) -> dict:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "csv").mkdir(exist_ok=True)
    e = env()
    out: dict[str, list[str]] = {}
    for letter, h in zip("AB", clients(), strict=False):
        slug = clients()[h]["name"].lower().replace(" ", "-")
        p = REPORTS_DIR / f"report-{letter}-{slug}.html"
        p.write_text(e.get_template("account.html.j2").render(**account_context(h, letter)), encoding="utf-8")
        files = [str(p)]
        if pdf and html_to_pdf(p, p.with_suffix(".pdf")):
            files.append(str(p.with_suffix(".pdf")))
        files += [str(x) for x in write_csvs(h, REPORTS_DIR / "csv")]
        out[h] = files
    p = REPORTS_DIR / "report-C-comparative.html"
    p.write_text(e.get_template("compare.html.j2").render(**compare_context()), encoding="utf-8")
    out["comparison"] = [str(p)]
    if pdf and html_to_pdf(p, p.with_suffix(".pdf")):
        out["comparison"].append(str(p.with_suffix(".pdf")))
    return out
