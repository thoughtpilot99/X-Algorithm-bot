"""Robust statistics used across engines.

View counts are heavy-tailed (one viral post can be 100x the median), so the
default summaries are medians, quantiles and median absolute deviation, and
group comparisons use rank tests and bootstrap confidence intervals on the
ratio of medians.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

RNG = np.random.default_rng(20261023)


def _clean(x) -> np.ndarray:  # noqa: ANN001
    a = np.asarray(pd.to_numeric(pd.Series(x), errors="coerce").dropna(), dtype=float)
    return a


def robust_summary(x) -> dict:  # noqa: ANN001
    a = _clean(x)
    if a.size == 0:
        return {"n": 0}
    med = float(np.median(a))
    return {
        "n": int(a.size),
        "median": med,
        "mean": float(a.mean()),
        "p25": float(np.quantile(a, 0.25)),
        "p75": float(np.quantile(a, 0.75)),
        "p90": float(np.quantile(a, 0.90)),
        "max": float(a.max()),
        "mad": float(np.median(np.abs(a - med))),
        "trimmed_mean_10": float(stats.trim_mean(a, 0.1)),
        "sum": float(a.sum()),
    }


def bootstrap_median_ratio(a, b, n_boot: int = 2000, ci: float = 0.9) -> dict:  # noqa: ANN001
    """Median(a) / median(b) with a percentile bootstrap CI."""
    a, b = _clean(a), _clean(b)
    if a.size == 0 or b.size == 0 or np.median(b) == 0:
        return {"ratio": None, "lo": None, "hi": None}
    ia = RNG.integers(0, a.size, (n_boot, a.size))
    ib = RNG.integers(0, b.size, (n_boot, b.size))
    ma = np.median(a[ia], axis=1)
    mb = np.median(b[ib], axis=1)
    ok = mb > 0
    r = ma[ok] / mb[ok]
    lo, hi = np.quantile(r, [(1 - ci) / 2, 1 - (1 - ci) / 2])
    return {"ratio": float(np.median(a) / np.median(b)), "lo": float(lo), "hi": float(hi)}


def mann_whitney(a, b) -> dict:  # noqa: ANN001
    a, b = _clean(a), _clean(b)
    if a.size < 2 or b.size < 2:
        return {"p": None, "rank_biserial": None}
    res = stats.mannwhitneyu(a, b, alternative="two-sided")
    rb = 1 - 2 * res.statistic / (a.size * b.size)
    return {"p": float(res.pvalue), "rank_biserial": float(-rb)}


def bh_adjust(pvals: list[float | None]) -> list[float | None]:
    """Benjamini–Hochberg FDR adjustment, preserving None."""
    idx = [i for i, p in enumerate(pvals) if p is not None]
    if not idx:
        return pvals
    ps = np.array([pvals[i] for i in idx])
    order = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    prev = 1.0
    for rank, j in reversed(list(enumerate(order, start=1))):
        prev = min(prev, ps[j] * m / rank)
        adj[j] = prev
    out = list(pvals)
    for k, i in enumerate(idx):
        out[i] = float(adj[k])
    return out


def theil_sen_trend(t_days, y) -> dict:  # noqa: ANN001
    """Robust slope of log(1+y) per 30 days, as a multiplicative change with 90% CI."""
    t = np.asarray(t_days, dtype=float)
    yy = np.log1p(np.asarray(y, dtype=float))
    ok = ~np.isnan(t) & ~np.isnan(yy)
    if ok.sum() < 8:
        return {"n": int(ok.sum()), "per_30d": None}
    slope, _, lo, hi = stats.theilslopes(yy[ok], t[ok], alpha=0.90)
    return {"n": int(ok.sum()), "per_30d": float(math.exp(slope * 30)),
            "lo": float(math.exp(lo * 30)), "hi": float(math.exp(hi * 30))}


def spearman(x, y) -> dict:  # noqa: ANN001
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    ok = ~np.isnan(x) & ~np.isnan(y)
    if ok.sum() < 8:
        return {"n": int(ok.sum()), "rho": None, "p": None}
    r = stats.spearmanr(x[ok], y[ok])
    return {"n": int(ok.sum()), "rho": float(r.statistic), "p": float(r.pvalue)}


def required_n_per_arm(sd_log: float, min_ratio: float = 1.3, alpha: float = 0.05, power: float = 0.8) -> int:
    """Posts per arm to detect a multiplicative change in median views (normal approx. on log scale)."""
    if not sd_log or sd_log <= 0:
        return 0
    delta = math.log(min_ratio)
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return int(math.ceil(2 * (z * sd_log / delta) ** 2))


def min_detectable_ratio(sd_log: float, n_per_arm: float, alpha: float = 0.05, power: float = 0.8) -> float | None:
    """Smallest multiplicative change in median views detectable with n posts per arm (inverse of the above)."""
    if not sd_log or sd_log <= 0 or n_per_arm < 2:
        return None
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return float(math.exp(z * sd_log * math.sqrt(2 / n_per_arm)))


def fmt_ratio(r: float | None) -> str:
    return "n/a" if r is None else f"{r:.2f}x"
