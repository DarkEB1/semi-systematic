"""brain: a retrieval index over a plain-text repository.

A tool (contract: tools/README.md). Point it at any folder with ``Repo(root, ...)``; it chunks
markdown on ``##`` and Python per top-level definition, writes one parquet table, searches it with
DuckDB, and renders a markdown table of contents. It never reads the environment or locates the
repository from its own file.

    from brain import Repo, build, search, write_index
    repo = Repo("/path/to/repo")          # defaults describe the semi-systematic layout
    build(repo)                           # <root>/.index/chunks.parquet
    search("carry", repo=repo)            # list[Hit], newest first
    write_index(repo)                     # <root>/knowledge/INDEX.md
"""

from __future__ import annotations

from brain.build import SCHEMA, Chunk, build, chunk, collect, split_frontmatter
from brain.embed import embed
from brain.index_md import render as render_index
from brain.index_md import write as write_index
from brain.repo import Repo
from brain.search import Hit, format_hits, search

__version__ = "0.2.0"
__all__ = [
    "SCHEMA",
    "Chunk",
    "Hit",
    "Repo",
    "build",
    "chunk",
    "collect",
    "embed",
    "format_hits",
    "render_index",
    "search",
    "split_frontmatter",
    "write_index",
]
