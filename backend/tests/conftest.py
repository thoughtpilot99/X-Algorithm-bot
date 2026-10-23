"""Tests run against a throwaway database; the real data/ directory is never touched."""

import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="xaudit-test-")
os.environ["XAUDIT_DB_URL"] = f"sqlite:///{_tmp}/test.sqlite"
os.environ.setdefault("XAUDIT_REPORTS_DIR", f"{_tmp}/reports")
