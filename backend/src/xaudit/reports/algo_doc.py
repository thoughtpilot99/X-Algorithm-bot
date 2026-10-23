"""Generate docs/algorithm-research.md from the findings/claims registry and parameter history."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from xaudit.algo import param_extract, registry, repo_sync
from xaudit.db.models import AlgoParam
from xaudit.db.session import session
from xaudit.settings import REPO_ROOT

GAPS = [
    "Trained model weights for Phoenix retrieval/ranking are not published, so per-post predicted probabilities "
    "cannot be reproduced.",
    "Grox prompts and some botmaker rules are deliberately withheld; classifier thresholds (e.g. BDSM) are redacted.",
    "The `component_library` crate (maps model outputs to named scores, holds the retrieval client and "
    "quality_factor) is not in the repository.",
    "Published parameter values are defaults mirrored from feature switches; live experiments can override them. "
    "home-mixer and vm-ranker declare the same keys with different defaults.",
    "Per-account outputs (user-cred score, Agatha labels, visibility labels, safety labels) are not observable "
    "from public data, so no audit can confirm or rule out an account-level label.",
    "Only engagement on posts served in Home Timeline feeds ranking (per the repository's own note); public counts "
    "mix all surfaces.",
]


def _param_changes() -> list[dict]:
    with session() as s:
        rows = s.execute(select(AlgoParam).order_by(AlgoParam.path, AlgoParam.name, AlgoParam.committed_at)).scalars()
        prev: dict[tuple[str, str], str] = {}
        out = []
        for r in rows:
            k = (r.path, r.name)
            if k in prev and prev[k] != r.raw_value:
                out.append({"date": r.committed_at.strftime("%Y-%m-%d") if r.committed_at else "", "sha": r.sha[:7],
                            "path": r.path, "name": r.name, "from": prev[k], "to": r.raw_value})
            prev[k] = r.raw_value
    return sorted(out, key=lambda x: x["date"])


def write(path: Path | None = None) -> Path:
    path = path or (REPO_ROOT / "docs" / "algorithm-research.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    head = repo_sync.head()
    v = registry.verify()
    L: list[str] = []
    L += ["# X algorithm research — what the published repository says", "",
          f"Studied commit: [`{registry.STUDIED_SHA[:7]}`]({registry.STUDIED_SHA and repo_sync.permalink(registry.STUDIED_SHA, 'README.md')}) "
          f"· local HEAD `{head.sha[:7]}` ({head.committed_at:%Y-%m-%d}) · "
          f"{len(registry.findings())} findings · {len(registry.claims())} claims checked · "
          f"citation check: {v['checked'] - len(v['failures'])}/{v['checked']} anchors verified.", "",
          "Every finding records: the mechanism, repository path and line range, symbol, commit, a plain-English "
          "explanation, potential relevance to an account, verification status, and limitations. Citations are "
          "machine-checked (`xaudit verify-citations`): the anchor text must appear within the cited lines.", "",
          "> The public repository is not a complete representation of live production systems. Ranking weights "
          "multiply *predicted* per-viewer action probabilities, not raw counts.", ""]
    L += ["## Knowledge gaps", ""] + [f"- {g}" for g in GAPS] + [""]
    key = [p for p in param_extract.current("home-mixer/params/param.rs") if p["name"].endswith("Weight")]
    L += ["## Published ranking weights (home-mixer defaults at studied commit)", "",
          "| Parameter | Value | Source |", "|---|---:|---|"]
    L += [f"| {p['name']} | {p['raw_value']} | [{p['path']}:{p['line']}]({p['permalink']}) |" for p in key]
    ch = _param_changes()
    if ch:
        L += ["", "### Parameter changes in the last commits scanned", "", "| Date | Commit | File | Parameter | From | To |",
              "|---|---|---|---|---|---|"]
        L += [f"| {c['date']} | {c['sha']} | {c['path']} | {c['name']} | {c['from']} | {c['to']} |" for c in ch
              if "Weight" in c["name"] or "ColdStart" in c["name"] or "Diversity" in c["name"]]
    for area, name in registry.AREAS.items():
        L += ["", f"## {area}. {name}", ""]
        for f in [x for x in registry.findings() if x["area"] == area]:
            L += [f"### {f['id']} — {f['title']}", "",
                  f"- **Location:** [`{f['path']}:{f['lines'][0]}-{f['lines'][1]}`]({f['permalink']}) · "
                  f"symbol `{f.get('symbol', '')}` · commit `{f['commit'][:7]}`",
                  f"- **Status:** {f['status']}",
                  f"- **Mechanism:** {f['mechanism']}",
                  f"- **Relevance to an account:** {f['relevance']}",
                  f"- **Observable proxy:** {f.get('observable_proxy', '')}",
                  f"- **Limitations:** {f['limitations']}", ""]
    L += ["", "## Common claims checked against the repository", "", "| ID | Claim | Verdict | Explanation |",
          "|---|---|---|---|"]
    for c in registry.claims():
        ev = " ".join(f"[{e['path']}:{e['lines'][0]}]({e['permalink']})" for e in c.get("evidence") or [])
        expl = c["explanation"].replace("|", "\\|").replace("\n", " ")
        L.append(f"| {c['id']} | {c['claim']} | **{c['verdict'].replace('_', ' ')}** | {expl} {ev} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path
