"""Posting time, frequency and volume vs outcomes.

The repository's author-diversity attenuation acts within a single viewer's
feed request (see findings registry). Same-day posting order is the closest
public proxy, and the analysis says so rather than claiming a measured penalty.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from xaudit.analysis.stats import robust_summary, spearman


def cadence_report(df: pd.DataFrame) -> dict:
    out: dict = {}
    if df.empty:
        return out
    days = pd.date_range(df["created_at"].min().normalize(), df["created_at"].max().normalize(), freq="D")
    d = df.assign(day=df["created_at"].dt.normalize())
    per_day = pd.DataFrame(index=days)
    per_day["authored"] = d[d["is_authored"]].groupby("day").size()
    per_day["replies"] = d[d["is_external_reply"]].groupby("day").size()
    per_day["self_replies"] = d[d["is_self_reply"]].groupby("day").size()
    per_day["reposts"] = d[d["post_type"] == "repost"].groupby("day").size()
    per_day = per_day.fillna(0).astype(int)
    per_day["total"] = per_day.sum(axis=1)
    weeks = max(1.0, len(days) / 7)
    out["frequency"] = {
        "days_observed": int(len(days)),
        "authored_per_week": float(per_day["authored"].sum() / weeks),
        "replies_per_week": float(per_day["replies"].sum() / weeks),
        "active_days_share": float((per_day["total"] > 0).mean()),
        "authored_days_share": float((per_day["authored"] > 0).mean()),
        "max_replies_in_a_day": int(per_day["replies"].max()),
        "median_replies_on_active_days": float(per_day.loc[per_day["replies"] > 0, "replies"].median())
        if (per_day["replies"] > 0).any() else 0.0,
    }
    # Consistency: coefficient of variation of weekly authored counts.
    wk = per_day["authored"].resample("W").sum()
    out["consistency"] = {"weekly_authored": robust_summary(wk),
                          "cv_weekly_authored": float(wk.std() / wk.mean()) if wk.mean() else None}

    # Inactivity: gaps between authored posts.
    a = d[d["is_authored"]].sort_values("created_at")
    gaps = a["created_at"].diff().dt.total_seconds() / 3600
    out["authored_gap_hours"] = robust_summary(gaps)
    long_gaps = a.loc[gaps > 72, "created_at"]
    out["inactivity_periods_over_3d"] = [
        {"resumed_at": ts.strftime("%Y-%m-%d"), "gap_days": round(float(g) / 24, 1)}
        for ts, g in zip(long_gaps, gaps[gaps > 72], strict=True)
    ]
    hi = per_day["total"].quantile(0.9)
    out["high_activity_days"] = [
        {"day": i.strftime("%Y-%m-%d"), **{k: int(v) for k, v in r.items()}}
        for i, r in per_day[per_day["total"] >= max(hi, 1)].iterrows()
    ][:20]

    # Same-day order of authored posts vs reach relative to baseline.
    am = a[a["mature"] & a["vs_baseline"].notna()].copy()
    if len(am):
        am["order_in_day"] = am.groupby(am["created_at"].dt.normalize()).cumcount() + 1
        am["order_bucket"] = am["order_in_day"].clip(upper=3).map({1: "1st", 2: "2nd", 3: "3rd+"})
        out["same_day_order"] = {
            k: robust_summary(g["vs_baseline"]) for k, g in am.groupby("order_bucket")
        }
        prev_gap = am["created_at"].diff().dt.total_seconds() / 3600
        am["gap_bucket"] = pd.cut(prev_gap, [-1, 2, 6, 24, 1e9], labels=["<2h", "2-6h", "6-24h", ">24h"])
        out["gap_since_previous"] = {
            str(k): robust_summary(g["vs_baseline"]) for k, g in am.groupby("gap_bucket", observed=True)
        }

    # Reply volume vs authored outcome (same day and following 2 days).
    if len(am):
        rv = per_day["replies"]
        am["replies_same_day"] = am["created_at"].dt.normalize().map(rv)
        am["replies_prev_3d"] = am["created_at"].dt.normalize().map(rv.rolling(3).sum().shift(1))
        out["reply_volume_vs_authored_reach"] = {
            "same_day": spearman(am["replies_same_day"], am["vs_baseline"]),
            "previous_3_days": spearman(am["replies_prev_3d"], am["vs_baseline"]),
            "note": "Spearman correlation with authored-post reach relative to baseline; association only.",
        }
    # Weekly volume vs weekly median outcome (diminishing returns check).
    wkly = d[d["mature"]].groupby("week").agg(
        authored=("is_authored", "sum"),
        replies=("is_external_reply", "sum"),
    )
    wa = d[d["mature"] & d["is_authored"]].groupby("week")["views"].median()
    wkly["authored_median_views"] = wa
    wkly = wkly.dropna()
    out["weekly_volume_vs_median_views"] = {
        "authored_count": spearman(wkly["authored"], wkly["authored_median_views"]),
        "reply_count": spearman(wkly["replies"], wkly["authored_median_views"]),
    }
    out["per_day_series"] = [
        {"day": i.strftime("%Y-%m-%d"), **{k: int(v) for k, v in r.items()}} for i, r in per_day.iterrows()
    ]
    # Weekday/hour posting distribution.
    out["posting_hours_utc"] = a["created_at"].dt.hour.value_counts().sort_index().to_dict()
    out["posting_weekdays"] = a["created_at"].dt.day_name().value_counts().to_dict()
    return out


def np_float(x) -> float | None:  # noqa: ANN001
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else float(x)
