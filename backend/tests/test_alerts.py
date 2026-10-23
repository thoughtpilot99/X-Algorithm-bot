from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from xaudit.monitor.alerts import control_check, reach_alerts


def _frame(weekly_medians: list[float], per_week: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    start = datetime(2026, 1, 5, 12, tzinfo=UTC)  # a Monday
    rows = []
    for w, med in enumerate(weekly_medians):
        for i in range(per_week):
            rows.append({"created_at": start + timedelta(days=7 * w + i), "views": float(med * rng.uniform(0.9, 1.1)),
                         "is_authored": True, "mature": True, "format": "long_post"})
    df = pd.DataFrame(rows)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    return df


def test_control_band_is_robust():
    chk = control_check([1.0, 1.1, 0.9, 1.0, 1.05, 0.95], 1.02, k=3, mad_floor=0.15)
    assert not chk["outside"]
    assert control_check([1.0, 1.1, 0.9, 1.0, 1.05, 0.95], -2.0, k=3, mad_floor=0.15)["direction"] == "down"


def test_stable_noise_does_not_alert():
    df = _frame([1000] * 12)
    today = df["created_at"].max().to_pydatetime() + timedelta(days=11)
    assert reach_alerts("x", df, today=today) == []


def test_step_change_alerts_once_with_abrupt_flag():
    df = _frame([1000] * 11 + [150])
    today = df["created_at"].max().to_pydatetime() + timedelta(days=11)
    alerts = reach_alerts("x", df, today=today)
    assert sum(1 for a in alerts if a["kind"] == "abrupt_change") == 1
    assert sum(1 for a in alerts if a["kind"] == "reach" and ":all:" in a["key"]) == 1
    assert all("visibility restriction" in a["detail"] for a in alerts if a["kind"] == "abrupt_change")


def test_not_enough_history_is_silent():
    df = _frame([1000, 1000, 100])
    today = df["created_at"].max().to_pydatetime() + timedelta(days=11)
    assert reach_alerts("x", df, today=today) == []


def test_recent_failed_collection_raises_alert():
    from xaudit.db.session import session
    from xaudit.ingest.store import finish_run, log_run
    from xaudit.monitor.alerts import collection_alerts

    with session() as s:
        run = log_run(s, source="console_live", actor="user-tweets", params={"username": "nifinet"})
        finish_run(run, status="failed", error="HTTP 500")
    alerts = collection_alerts()
    assert any(a["kind"] == "collection" and a["handle"] == "nifinet" for a in alerts)
