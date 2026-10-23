"""Run hypothesis checkers, enforce the evidence guard, persist diagnostics."""

from __future__ import annotations

from xaudit.algo import param_extract, registry
from xaudit.analysis.pipeline import prepare
from xaudit.db.session import load_artifact, save_artifact
from xaudit.diagnostics import guard
from xaudit.diagnostics.hypotheses import CHECKERS
from xaudit.settings import analysis_cfg

ARTIFACTS = ["reach", "engagement", "segments", "multivariable", "cadence", "comments", "benchmark"]

# Thresholds that appear in recommendations/success criteria by design (not data
# claims). Kept explicit so the guard can tell a policy constant from an invented figure.
POLICY_NUMBERS = [2, 3, 6, 8, 15, 20, 25, 40, 50, 60, 72, 0.25, 0.5, 0.75, 1000]


def context_numbers() -> list[float]:
    nums = list(POLICY_NUMBERS)
    nums += [p["value"] for p in param_extract.current() if p["value"] is not None]
    return nums


def run(handle: str) -> list[dict]:
    art = {k: load_artifact(k, handle) for k in ARTIFACTS}
    df = prepare(handle, window_days=analysis_cfg()["extended_window_days"])
    ctx = {"handle": handle, "df": df, "art": art}
    diags = [c(ctx) for c in CHECKERS]
    guard.enforce(diags, registry.finding_ids(), context_numbers())
    out = []
    for d in sorted(diags, key=lambda d: -d.priority):
        rec = d.model_dump()
        rec["priority"] = d.priority
        rec["algo_findings"] = [
            {k: registry.by_id(f).get(k) for k in ("id", "title", "path", "lines", "permalink", "status")}
            for f in d.algo_links if registry.by_id(f)
        ]
        out.append(rec)
    save_artifact("diagnostics", {"items": out}, handle)
    return out
