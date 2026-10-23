"""Findings and claims registry with mechanical citation checks.

Every finding cites (path, line range, anchor) at a specific commit. ``verify``
re-opens the file at that commit and confirms the anchor text is inside the
cited lines, so a citation that drifted or was mistyped is caught, and a
repository update that moves code flags the finding for review.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from xaudit.algo import repo_sync
from xaudit.settings import ALGO_REPO_DIR

HERE = Path(__file__).resolve().parent
FINDING_FILES = ("findings_ab.yaml", "findings_cd.yaml")
STUDIED_SHA = "07d159b69109f069c85f84d39dd38e38adc040f0"

AREAS = {
    "A": "Content candidate retrieval",
    "B": "Ranking and engagement prediction",
    "C": "Account and content quality",
    "D": "Feed-level ranking behaviour",
}


def _load(name: str) -> list[dict]:
    p = HERE / name
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


@lru_cache
def findings() -> list[dict]:
    out = []
    for name in FINDING_FILES:
        for f in _load(name):
            f.setdefault("commit", STUDIED_SHA)
            f["area_name"] = AREAS.get(f.get("area"), f.get("area"))
            f["permalink"] = repo_sync.permalink(f["commit"], f["path"], *f.get("lines", [None, None])[:2])
            out.append(f)
    return out


@lru_cache
def claims() -> list[dict]:
    out = []
    for c in _load("claims.yaml"):
        for e in c.get("evidence") or []:
            e["permalink"] = repo_sync.permalink(STUDIED_SHA, e["path"], *e.get("lines", [None, None])[:2])
        out.append(c)
    return out


def finding_ids() -> set[str]:
    return {f["id"] for f in findings()}


def by_id(fid: str) -> dict | None:
    return next((f for f in findings() if f["id"] == fid), None)


def lookup(*terms: str, limit: int = 3) -> list[str]:
    """Finding ids whose title/symbol/params/mechanism mention any term (case-insensitive), best first."""
    scored = []
    for f in findings():
        hay_hi = " ".join([f.get("title", ""), str(f.get("symbol", "")), " ".join(f.get("params") or [])]).lower()
        hay_lo = (f.get("mechanism", "") + " " + f.get("path", "")).lower()
        s = sum(3 for t in terms if t.lower() in hay_hi) + sum(1 for t in terms if t.lower() in hay_lo)
        if s:
            scored.append((s, f["id"]))
    return [fid for _, fid in sorted(scored, key=lambda x: (-x[0], x[1]))[:limit]]


def _check(path: str, lines: list[int], anchor: str, sha: str, repo: Path) -> str | None:
    src = repo_sync.show(repo, sha, path)
    if src is None:
        return f"{path} missing at {sha[:7]}"
    body = "\n".join(src.splitlines()[lines[0] - 1:lines[1]])
    return None if anchor in body else f"anchor not found in {path}:{lines[0]}-{lines[1]}"


def verify(repo: Path = ALGO_REPO_DIR) -> dict:
    """Check every citation at its studied commit, and whether it still holds at HEAD."""
    head = repo_sync.head(repo).sha
    results = []
    for f in findings():
        lines = f.get("lines") or [1, 1]
        at_commit = _check(f["path"], lines, f["anchor"], f["commit"], repo)
        at_head = _check(f["path"], lines, f["anchor"], head, repo) if head != f["commit"] else at_commit
        results.append({"id": f["id"], "ok": at_commit is None, "error": at_commit,
                        "still_valid_at_head": at_head is None})
    for c in claims():
        for i, e in enumerate(c.get("evidence") or []):
            err = _check(e["path"], e.get("lines") or [1, 1], e["anchor"], STUDIED_SHA, repo)
            results.append({"id": f"{c['id']}.{i}", "ok": err is None, "error": err, "still_valid_at_head": None})
    return {"head": head, "studied": STUDIED_SHA, "checked": len(results),
            "failures": [r for r in results if not r["ok"]],
            "moved_since_studied": [r["id"] for r in results if r["still_valid_at_head"] is False],
            "results": results}
