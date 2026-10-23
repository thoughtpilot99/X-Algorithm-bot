"""Evaluate registered experiments against their decision rules.

Results are reported per arm with a bootstrap CI on the ratio of medians. An
experiment that has not reached its minimum sample is "running" (or
"underpowered" once its end date passes) — never declared a win early.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import yaml

from xaudit.analysis.features import is_fulfilment
from xaudit.analysis.stats import bootstrap_median_ratio, required_n_per_arm
from xaudit.db.session import save_artifact
from xaudit.settings import CONFIG_DIR

METRICS = {
    "vs_baseline": lambda d: d["vs_baseline"],
    "views": lambda d: d["views"],
    "replies_per_1k": lambda d: d["replies"] / d["views"].where(d["views"] > 0) * 1000,
    "bookmarks_per_1k": lambda d: d["bookmarks"] / d["views"].where(d["views"] > 0) * 1000,
    "comment_views": lambda d: d["views"],
}


def load_registry(path=None) -> list[dict]:  # noqa: ANN001
    with open(path or CONFIG_DIR / "experiments.yaml", encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("experiments", [])


def _d(x) -> date | None:  # noqa: ANN001
    if x is None or x == "":
        return None
    return x if isinstance(x, date) else date.fromisoformat(str(x))


def population(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    if kind == "conversational_comments":
        return df[df["is_external_reply"] & ~df["text"].map(is_fulfilment)]
    return df[df["is_authored"]]


def assign(df: pd.DataFrame, exp: dict) -> pd.Series:
    """Return 'treatment' / 'control' / None per row."""
    rule = exp.get("arm_rule") or {}
    t = rule.get("type")
    start, end = _d(exp.get("start")), _d(exp.get("end"))
    day = df["created_at"].dt.date
    in_window = (day >= start) & ((day <= end) if end else True)
    arm = pd.Series([None] * len(df), index=df.index, dtype=object)
    if t == "tweet_ids":
        arm[df["tweet_id"].isin([str(x) for x in rule.get("treatment", [])])] = "treatment"
        arm[df["tweet_id"].isin([str(x) for x in rule.get("control", [])])] = "control"
    elif t == "alternating_weeks":
        weeks = ((pd.to_datetime(day) - pd.Timestamp(start)).dt.days // 7)
        first = "treatment" if rule.get("treatment_first", True) else "control"
        other = "control" if first == "treatment" else "treatment"
        arm[in_window] = np.where(weeks[in_window] % 2 == 0, first, other)
    elif t == "first_post_of_day":
        order = df.sort_values("created_at").groupby(day).cumcount() + 1
        arm[in_window] = np.where(order[in_window] <= 2, "treatment", "control")
    elif t == "text_tag":
        tag = rule.get("tag", "")
        arm[in_window] = np.where(df.loc[in_window, "text"].str.contains(tag, regex=False), "treatment", "control")
    elif t == "pre_post":
        cs, ce = _d(rule.get("control_start")), _d(rule.get("control_end"))
        arm[in_window] = "treatment"
        if cs and ce:
            arm[(day >= cs) & (day <= ce)] = "control"
    return arm


def evaluate_one(exp: dict, df: pd.DataFrame, handle: str, today: date | None = None) -> dict:
    today = today or date.today()
    base = {"id": exp["id"], "title": exp["title"], "handle": handle, "metric": exp["metric"],
            "start": str(exp.get("start") or ""), "end": str(exp.get("end") or "")}
    if not exp.get("start"):
        return {**base, "status": "not_started", "note": "Set `start` in config/experiments.yaml to begin tracking."}
    pop = population(df, exp.get("population", "authored"))
    pop = pop[pop["mature"]]
    arms = assign(pop, exp)
    vals = METRICS[exp["metric"]](pop)
    t = vals[(arms == "treatment")].dropna()
    c = vals[(arms == "control")].dropna()
    dec = exp.get("decision") or {}
    min_n, min_ratio = int(dec.get("min_n_per_arm", 8)), float(dec.get("min_ratio", 1.3))
    res = {**base, "n_treatment": int(len(t)), "n_control": int(len(c)),
           "median_treatment": float(t.median()) if len(t) else None,
           "median_control": float(c.median()) if len(c) else None,
           "decision_rule": f"treatment/control median >= {min_ratio} with >= {min_n} per arm"}
    if len(t) and len(c):
        res.update(bootstrap_median_ratio(t, c))
        both = pd.concat([t, c])
        sd = float(np.log(both[both > 0]).std()) if (both > 0).sum() > 3 else None
        res["required_n_per_arm_for_min_ratio"] = required_n_per_arm(sd, max(min_ratio, 1.05)) if sd else None
    ended = bool(exp.get("end")) and _d(exp["end"]) < today
    if len(t) < min_n or len(c) < min_n:
        res["status"] = "underpowered" if ended else "running"
    elif res.get("ratio") is not None and res["ratio"] >= min_ratio and (res.get("lo") or 0) > 1:
        res["status"] = "met"
    elif res.get("ratio") is not None and res["ratio"] >= min_ratio:
        res["status"] = "met (directional)" if ended else "running"
    else:
        res["status"] = "not_met" if ended else "running"
    return res


def evaluate_all(frames: dict[str, pd.DataFrame], registry: list[dict] | None = None) -> dict:
    registry = registry if registry is not None else load_registry()
    out: dict[str, list[dict]] = {}
    for h, df in frames.items():
        out[h] = [evaluate_one(e, df, h) for e in registry if h in (e.get("handles") or [])]
        save_artifact("experiment_results", {"items": out[h]}, h)
    return out
