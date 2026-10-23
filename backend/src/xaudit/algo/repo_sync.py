"""Keep a local clone of xai-org/x-algorithm and record which commit was studied."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from xaudit.settings import ALGO_REPO_DIR, ALGO_REPO_URL


@dataclass(frozen=True)
class RepoState:
    path: Path
    sha: str
    committed_at: datetime
    previous_sha: str | None = None

    @property
    def short(self) -> str:
        return self.sha[:7]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


def head(repo: Path = ALGO_REPO_DIR) -> RepoState:
    sha = _git(repo, "rev-parse", "HEAD")
    when = datetime.fromisoformat(_git(repo, "log", "-1", "--format=%cI"))
    return RepoState(repo, sha, when)


def sync(repo: Path = ALGO_REPO_DIR, depth: int = 60) -> RepoState:
    """Clone if missing, otherwise fetch and fast-forward. Returns old/new SHA."""
    if not (repo / ".git").exists():
        repo.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", str(depth), ALGO_REPO_URL, str(repo)], check=True)
        return head(repo)
    prev = _git(repo, "rev-parse", "HEAD")
    _git(repo, "fetch", "--depth", str(depth), "origin")
    branch = _git(repo, "rev-parse", "--abbrev-ref", "origin/HEAD").removeprefix("origin/") or "main"
    _git(repo, "reset", "--hard", f"origin/{branch}")
    st = head(repo)
    return RepoState(st.path, st.sha, st.committed_at, previous_sha=prev if prev != st.sha else None)


def commits(repo: Path = ALGO_REPO_DIR, n: int = 50) -> list[tuple[str, datetime]]:
    out = _git(repo, "log", f"-{n}", "--format=%H %cI")
    return [(line.split()[0], datetime.fromisoformat(line.split()[1])) for line in out.splitlines()]


def show(repo: Path, sha: str, path: str) -> str | None:
    try:
        return _git(repo, "show", f"{sha}:{path}")
    except subprocess.CalledProcessError:
        return None


def changed_files(repo: Path, old: str, new: str) -> list[str]:
    return _git(repo, "diff", "--name-only", old, new).splitlines()


def permalink(sha: str, path: str, line: int | None = None, end: int | None = None) -> str:
    url = f"{ALGO_REPO_URL}/blob/{sha}/{path}"
    if line:
        url += f"#L{line}" + (f"-L{end}" if end and end != line else "")
    return url
