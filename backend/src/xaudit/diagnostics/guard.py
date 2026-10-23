"""Evidence guard: refuse diagnostics that are not traceable to evidence.

Rules (each violation is returned as a message; ``enforce`` raises):
1. A diagnostic whose status is not "insufficient" must cite at least one
   non-data-gap evidence item.
2. Every algo link must exist in the findings registry.
3. Suppression language ("shadowban", "suppressed", "penalised" ...) is only
   allowed when the diagnostic is about visibility AND cites repo evidence —
   and even then never as a confirmed fact about this account.
4. Every number written in the prose fields must match (within rounding) a
   number present in the evidence values or in the allow-list of context
   numbers passed by the caller. This stops prose — templated or LLM-written —
   from introducing figures the engines did not compute.
"""

from __future__ import annotations

import re

from xaudit.diagnostics.model import Diagnostic

SUPPRESSION = re.compile(r"\b(shadow\s?-?ban\w*|suppress\w*|penali[sz]\w*|throttl\w*|blacklist\w*|deboost\w*)\b",
                         re.I)
NEGATED = re.compile(r"\b(no|not|never|without|cannot|can't|isn't|unsupported|unconfirmed)\b[^.]{0,60}$", re.I)
NUM = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)?(?:\s?%|x)?")
PROSE_FIELDS = ("observation", "impact", "recommendation", "algo_connection", "validation", "success_criteria")


class GuardError(ValueError):
    pass


def _numbers(text: str) -> list[float]:
    out = []
    for m in NUM.finditer(text or ""):
        tok = m.group(0).replace(",", "").replace(" ", "")
        pct = tok.endswith("%")
        tok = tok.rstrip("%x")
        try:
            v = float(tok)
        except ValueError:
            continue
        out.append(v / 100 if pct else v)
        if pct:
            out.append(v)
    return out


def _matches(v: float, pool: list[float]) -> bool:
    for p in pool:
        if p == 0 and v == 0:
            return True
        for cand in (p, p * 100):
            if cand and abs(v - cand) <= max(0.051 * abs(cand), 0.51 if abs(cand) >= 1 else 0.0051):
                return True
    return False


def check(d: Diagnostic, finding_ids: set[str], context_numbers: list[float] | None = None) -> list[str]:
    errs: list[str] = []
    real = [e for e in d.evidence if e.kind != "data_gap"]
    if d.status != "insufficient" and not real:
        errs.append(f"{d.id}: status {d.status!r} without evidence")
    for f in d.algo_links:
        if f not in finding_ids:
            errs.append(f"{d.id}: unknown finding {f}")
    for field in PROSE_FIELDS:
        text = getattr(d, field) or ""
        for m in SUPPRESSION.finditer(text):
            before = text[max(0, m.start() - 80):m.start()]
            if not NEGATED.search(before):
                errs.append(f"{d.id}.{field}: suppression language {m.group(0)!r} asserted")
    pool: list[float] = list(context_numbers or [])
    for e in d.evidence:
        if isinstance(e.value, (int, float)):
            pool.append(float(e.value))
        elif isinstance(e.value, str):
            pool.extend(_numbers(e.value))
        pool.extend(_numbers(e.label))
    small_ok = {0, 1, 2, 3, 4, 5, 10, 30, 90, 100}
    for field in PROSE_FIELDS:
        for v in _numbers(getattr(d, field) or ""):
            if v in small_ok or 2000 <= v <= 2100:  # small counts, years
                continue
            if not _matches(v, pool):
                errs.append(f"{d.id}.{field}: number {v:g} not traceable to evidence")
    return errs


def enforce(diags: list[Diagnostic], finding_ids: set[str], context_numbers: list[float] | None = None) -> None:
    errs = [e for d in diags for e in check(d, finding_ids, context_numbers)]
    if errs:
        raise GuardError("; ".join(errs))
