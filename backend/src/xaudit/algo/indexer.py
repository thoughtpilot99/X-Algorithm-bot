"""Code-aware search over the X algorithm repository (SQLite FTS5).

Files are split into chunks at definition boundaries (fn/struct/impl/class/def/
param!) so a search hit points at a function, with a line range and a permalink
pinned to the indexed commit.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from xaudit.algo import repo_sync
from xaudit.settings import ALGO_REPO_DIR, DATA_DIR

INDEX_PATH = DATA_DIR / "algo_index.sqlite"
EXTS = {".rs", ".py", ".scala", ".java", ".md", ".proto", ".thrift", ".toml", ".yaml", ".yml", ".strato"}
BOUNDARY = re.compile(
    r"^\s*(pub(\(\w+\))?\s+)?(async\s+)?(fn|struct|enum|impl|trait|mod|class|object|def|case class|"
    r"param!|message|service|#{1,3}\s)",
)
MAX_CHUNK_LINES = 120


def _chunks(lines: list[str]) -> list[tuple[int, int]]:
    starts = [i for i, ln in enumerate(lines) if BOUNDARY.match(ln)] or [0]
    if starts[0] != 0:
        starts.insert(0, 0)
    spans = []
    for a, b in zip(starts, [*starts[1:], len(lines)], strict=True):
        while b - a > MAX_CHUNK_LINES:
            spans.append((a, a + MAX_CHUNK_LINES))
            a += MAX_CHUNK_LINES
        if b > a:
            spans.append((a, b))
    return spans


def build(repo: Path = ALGO_REPO_DIR, index: Path = INDEX_PATH) -> dict:
    st = repo_sync.head(repo)
    index.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(index)
    con.executescript(
        """
        DROP TABLE IF EXISTS chunks;
        DROP TABLE IF EXISTS meta;
        CREATE VIRTUAL TABLE chunks USING fts5(path, start UNINDEXED, end UNINDEXED, symbol, body,
                                               tokenize='unicode61 tokenchars _');
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
        """
    )
    files = n = 0
    for p in sorted(repo.rglob("*")):
        if ".git" in p.parts or not p.is_file() or p.suffix not in EXTS or p.stat().st_size > 400_000:
            continue
        rel = p.relative_to(repo).as_posix()
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        files += 1
        for a, b in _chunks(lines):
            body = "\n".join(lines[a:b])
            if not body.strip():
                continue
            con.execute("INSERT INTO chunks VALUES (?,?,?,?,?)", (rel, a + 1, b, lines[a].strip()[:200], body))
            n += 1
    con.executemany("INSERT INTO meta VALUES (?,?)",
                    [("sha", st.sha), ("committed_at", st.committed_at.isoformat())])
    con.commit()
    con.close()
    return {"sha": st.sha, "files": files, "chunks": n}


def search(query: str, limit: int = 10, index: Path = INDEX_PATH) -> list[dict]:
    con = sqlite3.connect(index)
    sha = con.execute("SELECT value FROM meta WHERE key='sha'").fetchone()[0]
    terms = " OR ".join(f'"{t}"' for t in re.findall(r"\w+", query))
    rows = con.execute(
        "SELECT path, start, end, symbol, snippet(chunks, 4, '[', ']', ' … ', 24), bm25(chunks) "
        "FROM chunks WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT ?",
        (terms, limit),
    ).fetchall()
    con.close()
    return [
        {"path": r[0], "start": int(r[1]), "end": int(r[2]), "symbol": r[3], "snippet": r[4],
         "score": round(-r[5], 3), "sha": sha, "permalink": repo_sync.permalink(sha, r[0], int(r[1]), int(r[2]))}
        for r in rows
    ]
