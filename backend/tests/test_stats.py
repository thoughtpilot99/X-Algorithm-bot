import numpy as np

from xaudit.analysis.stats import bh_adjust, bootstrap_median_ratio, required_n_per_arm, robust_summary


def test_robust_summary_resists_outlier():
    s = robust_summary([10, 11, 12, 13, 1_000_000])
    assert s["median"] == 12 and s["mean"] > 100_000


def test_bh_preserves_none_and_order():
    q = bh_adjust([0.01, None, 0.04, 0.03])
    assert q[1] is None
    assert all(a <= 1 for a in q if a is not None)
    assert q[0] <= q[2]


def test_bootstrap_ratio_brackets_truth():
    rng = np.random.default_rng(1)
    a = rng.lognormal(np.log(200), 0.5, 200)
    b = rng.lognormal(np.log(100), 0.5, 200)
    r = bootstrap_median_ratio(a, b)
    assert r["lo"] < 2.0 < r["hi"] or abs(r["ratio"] - 2) < 0.3


def test_power_grows_as_effect_shrinks():
    assert required_n_per_arm(1.0, 1.3) > required_n_per_arm(1.0, 2.0) > 0
