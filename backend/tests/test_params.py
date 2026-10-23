from xaudit.algo.param_extract import parse, sync_header

SRC = """// mirrored from config feature-switch defaults; last sync 2026-10-22T16:00:34Z
use xai_feature_switches::param;
param!(FavoriteWeight, f64, "rust_home_mixer_favorite_weight", 0.66);
param!(
    ReportWeight,
    f64,
    "rust_home_mixer_report_weight",
    -234.0
);
param!(EnableX, bool, "rust_enable_x", true);
param!(MaxAge, u64, "rust_max_age", 48 * 60 * 60);
"""


def test_parse_values_and_lines():
    ps = {p.name: p for p in parse(SRC)}
    assert ps["FavoriteWeight"].value == 0.66 and ps["FavoriteWeight"].line == 3
    assert ps["ReportWeight"].value == -234.0 and ps["ReportWeight"].line == 4
    assert ps["EnableX"].value == 1.0
    assert ps["MaxAge"].value == 172800.0


def test_sync_header():
    assert sync_header(SRC) == "2026-10-22T16:00:34Z"
