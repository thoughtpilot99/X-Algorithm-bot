import pytest

from xaudit.diagnostics.guard import GuardError, check, enforce
from xaudit.diagnostics.model import Diagnostic, Evidence


def diag(**kw):
    base = dict(id="x-1", handle="x", issue="i", status="supported", observation="Median is 120 views.",
                evidence=[Evidence(kind="metric", ref="m", label="median views", value=120)], algo_links=["B03"],
                confidence="medium", impact="", recommendation="", validation="", evidence_class="account_observed")
    return Diagnostic(**{**base, **kw})


def test_accepts_traceable_numbers():
    assert check(diag(), {"B03"}) == []


def test_rejects_invented_number():
    errs = check(diag(observation="Median is 120 views and reach fell 63%."), {"B03"})
    assert any("63" in e for e in errs)


def test_rejects_supported_without_evidence():
    errs = check(diag(evidence=[], observation="Something happened."), {"B03"})
    assert any("without evidence" in e for e in errs)


def test_rejects_unknown_finding():
    assert any("unknown finding" in e for e in check(diag(), {"A01"}))


def test_suppression_language():
    with pytest.raises(GuardError):
        enforce([diag(observation="The account is shadowbanned (120 views).")], {"B03"})
    assert check(diag(recommendation="Do not act on shadowban theories."), {"B03"}) == []
