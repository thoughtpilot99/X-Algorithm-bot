"""Extract published `param!` defaults from the X algorithm repository.

The repository declares tunables as::

    param!(FavoriteWeight, f64, "rust_home_mixer_favorite_weight", 0.66);

`home-mixer/params/param.rs` states it is "mirrored from config feature-switch
defaults" with a sync timestamp; `vm-ranker/params.rs` carries its own,
sometimes different, defaults. Both are extracted and kept separate. These are
published *defaults*; live experiments may override them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select

from xaudit.algo import repo_sync
from xaudit.db.models import AlgoParam, RepoVersion
from xaudit.db.session import session
from xaudit.settings import ALGO_REPO_DIR

PARAM_FILES = ("home-mixer/params/param.rs", "vm-ranker/params.rs")

PARAM_RE = re.compile(
    r"param!\(\s*(?P<name>\w+)\s*,\s*(?P<type>[\w:<>]+)\s*,\s*\"(?P<key>[^\"]+)\"\s*,\s*(?P<value>[^;]*?)\s*\)\s*;",
    re.S,
)
SYNC_RE = re.compile(r"last sync (\S+)")


@dataclass(frozen=True)
class Param:
    name: str
    type: str
    key: str
    raw_value: str
    value: float | None
    line: int


def _to_float(raw: str) -> float | None:
    raw = raw.strip().replace("_", "")
    if raw in ("true", "false"):
        return 1.0 if raw == "true" else 0.0
    m = re.fullmatch(r"-?\d+(\.\d+)?(e-?\d+)?", raw)
    if m:
        return float(raw)
    # simple products such as 48 * 60 * 60
    if re.fullmatch(r"[\d\s.*]+", raw):
        out = 1.0
        for part in raw.split("*"):
            out *= float(part)
        return out
    return None


def parse(source: str) -> list[Param]:
    out = []
    for m in PARAM_RE.finditer(source):
        line = source.count("\n", 0, m.start()) + 1
        raw = " ".join(m.group("value").split())
        out.append(Param(m.group("name"), m.group("type"), m.group("key"), raw, _to_float(raw), line))
    return out


def sync_header(source: str) -> str | None:
    m = SYNC_RE.search(source.splitlines()[0] if source else "")
    return m.group(1) if m else None


def extract_history(n_commits: int = 50) -> dict:
    """Store params for the last `n_commits` commits; return a change log."""
    repo = ALGO_REPO_DIR
    history = repo_sync.commits(repo, n_commits)
    changes: list[dict] = []
    prev: dict[tuple[str, str], str] = {}
    with session() as s:
        for sha, when in reversed(history):
            if s.get(RepoVersion, sha) is None:
                s.add(RepoVersion(sha=sha, committed_at=when))
            known = set(s.execute(select(AlgoParam.path, AlgoParam.name).where(AlgoParam.sha == sha)).all())
            for path in PARAM_FILES:
                src = repo_sync.show(repo, sha, path)
                if src is None:
                    continue
                for p in parse(src):
                    k = (path, p.name)
                    if k not in known:
                        s.add(AlgoParam(sha=sha, committed_at=when, path=path, line=p.line, name=p.name,
                                        value=p.value, raw_value=p.raw_value, value_type=p.type))
                    if k in prev and prev[k] != p.raw_value:
                        changes.append({"sha": sha, "committed_at": when.isoformat(), "path": path,
                                        "name": p.name, "from": prev[k], "to": p.raw_value})
                    prev[k] = p.raw_value
    return {"commits_scanned": len(history), "changes": changes}


def current(path: str | None = None) -> list[dict]:
    st = repo_sync.head()
    out = []
    for f in PARAM_FILES if path is None else (path,):
        src = repo_sync.show(st.path, st.sha, f) or ""
        for p in parse(src):
            out.append({"path": f, "line": p.line, "name": p.name, "type": p.type, "key": p.key,
                        "raw_value": p.raw_value, "value": p.value,
                        "permalink": repo_sync.permalink(st.sha, f, p.line)})
    return out
