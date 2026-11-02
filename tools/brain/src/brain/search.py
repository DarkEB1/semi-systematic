"""DuckDB ILIKE over text + heading + title, newest first."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import duckdb

from brain.build import build
from brain.repo import Repo


@dataclass
class Hit:
    path: str
    heading: str
    date: str | None
    type: str
    snippet: str


def _snippet(text: str, query: str, width: int = 90) -> str:
    m = re.search(re.escape(query), text, flags=re.I)
    if not m:
        return re.sub(r"\s+", " ", text[: 2 * width]).strip()
    a, b = max(0, m.start() - width), min(len(text), m.end() + width)
    s = re.sub(r"\s+", " ", text[a:b]).strip()
    return ("…" if a > 0 else "") + s + ("…" if b < len(text) else "")


def search(
    query: str, *, repo: Repo | None = None, index: Path | None = None, limit: int = 20
) -> list[Hit]:
    """Search ``index`` (default: ``repo.index_file``). With a ``repo`` and no index file yet, the
    index is built first; without a repo a missing index is an error."""
    if index is None:
        if repo is None:
            raise ValueError("search needs a repo or an index path")
        index = repo.index_file
    index = Path(index)
    if not index.exists():
        if repo is None:
            raise FileNotFoundError(f"no index at {index}; build one with brain.build(repo)")
        build(repo, out=index)
    con = duckdb.connect()
    like = f"%{query}%"
    rows = con.execute(
        """
        SELECT path, heading, date, type, text
        FROM read_parquet(?)
        WHERE text ILIKE ? OR heading ILIKE ? OR title ILIKE ?
        ORDER BY date DESC NULLS LAST, path, heading
        LIMIT ?
        """,
        [index.as_posix(), like, like, like, limit],
    ).fetchall()
    return [Hit(p, h, d, t, _snippet(x, query)) for p, h, d, t, x in rows]


def format_hits(hits: list[Hit], query: str) -> str:
    if not hits:
        return f'no results for "{query}" (rebuild the index if the repository changed)'
    out = []
    for h in hits:
        head = f"{h.path}" + (f" › {h.heading}" if h.heading else "")
        out.append(f"{head}  [{h.type}{', ' + h.date if h.date else ''}]\n    {h.snippet}")
    return "\n".join(out)
