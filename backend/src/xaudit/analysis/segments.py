"""Which post characteristics are associated with higher or lower reach.

Two layers, both reported as ASSOCIATIONS:

1. Univariate: each level of a feature vs all other authored posts — ratio of
   medians with bootstrap CI, Mann–Whitney p, Benjamini–Hochberg q across all
   comparisons. Levels with fewer than ``min_segment_n`` posts are not tested.
2. Multivariable: OLS on log(1+views) with month fixed effects and HC3 robust
   errors, so e.g. a format effect is estimated holding topic and month fixed.
   Coefficients are reported as multiplicative effects exp(b).

Neither layer establishes causation: posts were not randomly assigned.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from xaudit.analysis.stats import bh_adjust, bootstrap_median_ratio, mann_whitney
from xaudit.settings import analysis_cfg

FEATURES = {
    "format": "Content format",
    "topic": "Topic",
    "hook_type": "Opening hook type",
    "narrative": "Narrative structure",
    "length_bucket": "Length",
    "has_tco_url": "Contains t.co URL (link or media)",
    "tco_url_excl_articles": "Contains t.co URL, X Articles excluded",
    "has_list": "List formatting",
    "has_numbers": "Contains numbers/data",
    "has_question": "Contains a question",
    "uses_data": "Uses data (label)",
    "personal_experience": "Personal experience (label)",
    "promotional": "Promotional (label)",
    "keyword_cta": "\"Comment KEYWORD\" CTA",
    "has_cta": "Any CTA",
    "opinion_strength": "Opinion strength (0-3)",
    "educational_value": "Educational value (0-3)",
    "weekday": "Weekday",
    "daypart_utc": "Time of day (UTC)",
}


def univariate(df: pd.DataFrame, metric: str = "views") -> list[dict]:
    min_n = analysis_cfg()["min_segment_n"]
    a = df[df["is_authored"] & df["mature"] & df[metric].notna()]
    rows: list[dict] = []
    for feat, label in FEATURES.items():
        if feat not in a.columns:
            continue
        valid = a[a[feat].notna()]
        col = valid[feat].astype(str)
        for level, g in valid.groupby(col):
            rest = valid[col != level]
            row = {"feature": feat, "feature_label": label, "level": level, "n": int(len(g)),
                   "n_rest": int(len(rest)), "median": float(g[metric].median()),
                   "median_rest": float(rest[metric].median()) if len(rest) else None}
            if len(g) < min_n or len(rest) < min_n:
                row.update({"tested": False, "reason": f"n < {min_n}"})
            else:
                row.update({"tested": True, **bootstrap_median_ratio(g[metric], rest[metric]),
                            **mann_whitney(g[metric], rest[metric])})
            rows.append(row)
    qs = bh_adjust([r.get("p") for r in rows])
    for r, q in zip(rows, qs, strict=True):
        r["q"] = q
        r["evidence_class"] = "statistical_association"
        r["signal"] = (
            "insufficient data" if not r.get("tested") else
            "higher" if (q is not None and q < 0.1 and r["ratio"] and r["ratio"] > 1) else
            "lower" if (q is not None and q < 0.1 and r["ratio"] and r["ratio"] < 1) else
            "no clear difference"
        )
    return rows


def univariate_ex_articles(df: pd.DataFrame, metric: str = "views") -> list[dict]:
    """Univariate segments over authored posts other than X Articles.

    X Articles reach far more than anything else and are posted as bare links, so
    in the full set length, hook and narrative levels mostly re-measure the article
    effect. Excluding them shows what is associated with reach in everyday posts.
    """
    if "format" not in df.columns:
        return []
    return univariate(df[df["format"] != "x_article"], metric)


def multivariable(df: pd.DataFrame) -> dict:
    a = df[df["is_authored"] & df["mature"] & df["views"].notna()].copy()
    if len(a) < 40:
        return {"fitted": False, "reason": f"only {len(a)} mature authored posts (< 40)"}
    a["log_views"] = np.log1p(a["views"])
    terms = ["C(format)", "C(month)"]
    # hook_type is left out: for X Article posts it is mostly "announcement"/"other",
    # so it is collinear with format and inflates the article coefficient.
    for c, kind in (("topic", "cat"), ("tco_url_excl_articles", "bool"), ("has_list", "bool"),
                    ("uses_data", "bool"), ("personal_experience", "bool"), ("promotional", "bool"),
                    ("keyword_cta", "bool")):
        if c == "tco_url_excl_articles" and c in a.columns:
            a[c] = a[c].fillna(False).astype(bool)
        if c in a.columns and a[c].notna().all() and a[c].astype(str).nunique() > 1:
            if kind == "cat":
                # Collapse rare levels so the model is estimable.
                vc = a[c].value_counts()
                a[c] = a[c].where(a[c].map(vc) >= 8, "other/rare")
                terms.append(f"C({c})")
            else:
                a[c] = a[c].astype(int)
                terms.append(c)
    a["log_words"] = np.log1p(a["word_count"])
    terms.append("log_words")
    formula = "log_views ~ " + " + ".join(terms)
    try:
        fit = smf.ols(formula, data=a).fit(cov_type="HC3")
    except Exception as e:  # noqa: BLE001
        return {"fitted": False, "reason": str(e)}
    ci = fit.conf_int(alpha=0.1)
    coefs = []
    for name in fit.params.index:
        if name == "Intercept" or name.startswith("C(month)"):
            continue
        coefs.append({
            "term": name,
            "multiplier": float(np.exp(fit.params[name])),
            "lo": float(np.exp(ci.loc[name, 0])),
            "hi": float(np.exp(ci.loc[name, 1])),
            "p": float(fit.pvalues[name]),
        })
    return {
        "fitted": True,
        "formula": formula,
        "n": int(fit.nobs),
        "r2": float(fit.rsquared),
        "adj_r2": float(fit.rsquared_adj),
        "residual_sd_log": float(np.sqrt(fit.scale)),
        "controls": "month fixed effects; HC3 robust standard errors; 90% CIs",
        "coefficients": sorted(coefs, key=lambda c: c["p"]),
        "evidence_class": "statistical_association",
    }


def strong_weak_profile(df: pd.DataFrame) -> dict:
    """Recurring characteristics of top-quartile vs bottom-quartile posts vs own baseline."""
    a = df[df["is_authored"] & df["vs_baseline"].notna()]
    if len(a) < 20:
        return {"available": False}
    hi = a[a["vs_baseline"] >= a["vs_baseline"].quantile(0.75)]
    lo = a[a["vs_baseline"] <= a["vs_baseline"].quantile(0.25)]

    def share(g: pd.DataFrame, col: str) -> dict:
        return g[col].astype(str).value_counts(normalize=True).round(3).head(6).to_dict() if col in g else {}

    cols = ["format", "topic", "hook_type", "narrative", "length_bucket", "has_tco_url", "has_list"]
    return {"available": True, "n_top": int(len(hi)), "n_bottom": int(len(lo)),
            "top_quartile": {c: share(hi, c) for c in cols},
            "bottom_quartile": {c: share(lo, c) for c in cols}}
