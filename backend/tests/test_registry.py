import pytest

from xaudit.algo import registry
from xaudit.settings import ALGO_REPO_DIR

REQUIRED = {"id", "area", "title", "mechanism", "path", "lines", "symbol", "anchor", "status", "relevance",
            "limitations"}


def test_findings_schema():
    fs = registry.findings()
    assert len(fs) >= 40
    ids = [f["id"] for f in fs]
    assert len(ids) == len(set(ids))
    for f in fs:
        assert REQUIRED <= set(f), f["id"]
        assert f["status"] in {"verified", "inferred", "unknown"}
        assert f["lines"][0] <= f["lines"][1]


def test_claims_have_verdicts():
    allowed = {"supported", "partially_supported", "contradicted", "not_found_in_repo", "unverifiable"}
    assert all(c["verdict"] in allowed for c in registry.claims())


@pytest.mark.skipif(not (ALGO_REPO_DIR / ".git").exists(), reason="algorithm repo not cloned")
def test_every_citation_anchor_is_in_its_lines():
    r = registry.verify()
    assert r["failures"] == [], r["failures"][:3]
