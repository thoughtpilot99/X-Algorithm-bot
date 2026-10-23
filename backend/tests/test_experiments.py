from datetime import date

import pandas as pd

from xaudit.monitor.experiments import assign, evaluate_one


def _df(n: int = 40) -> pd.DataFrame:
    ts = pd.date_range("2026-11-02 09:00", periods=n, freq="12h", tz="UTC")
    return pd.DataFrame({
        "tweet_id": [str(i) for i in range(n)], "created_at": ts, "text": ["post"] * n,
        "views": [2000.0 if (t - ts[0]).days // 7 % 2 == 0 else 1000.0 for t in ts],
        "replies": [2] * n, "bookmarks": [1] * n, "vs_baseline": [1.0] * n,
        "is_authored": [True] * n, "is_external_reply": [False] * n, "mature": [True] * n,
    })


def test_not_started_without_start():
    r = evaluate_one({"id": "e", "title": "t", "metric": "views", "start": None}, _df(), "x")
    assert r["status"] == "not_started"


def test_alternating_weeks_assignment_and_decision():
    exp = {"id": "fmt", "title": "t", "metric": "views", "population": "authored", "start": "2026-11-02",
           "end": "2026-11-21", "arm_rule": {"type": "alternating_weeks", "treatment_first": True},
           "decision": {"min_ratio": 1.3, "min_n_per_arm": 8}}
    df = _df()
    arms = assign(df, exp)
    assert set(arms.dropna()) == {"treatment", "control"}
    r = evaluate_one(exp, df, "x", today=date(2026, 12, 1))
    assert r["ratio"] == 2.0 and r["status"] == "met"


def test_small_sample_is_running_not_called():
    exp = {"id": "h", "title": "t", "metric": "views", "start": "2026-11-02", "end": None,
           "arm_rule": {"type": "tweet_ids", "treatment": ["0", "1"], "control": ["2", "3"]},
           "decision": {"min_ratio": 1.3, "min_n_per_arm": 8}}
    assert evaluate_one(exp, _df(), "x")["status"] == "running"
