#!/usr/bin/env python
"""Deterministic part of the build-index skill (`just index`, `just search`).

build_index.py build         rebuild .index/chunks.parquet and knowledge/INDEX.md
build_index.py search QUERY  ILIKE search, newest first, with paths to cite
build_index.py chunk-file PATH  show how one file is chunked (JSON), used by the eval
build_index.py answer QUERY  search and print a citation list for "what do we know about X"

Thin wrapper over the `brain` tool (tools/brain): this file knows the repo root, brain does not.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from brain import Repo, build, chunk, format_hits, search, write_index

ROOT = Path(__file__).resolve().parents[3]
REPO = Repo(ROOT)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="build-index")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=20)
    c = sub.add_parser("chunk-file")
    c.add_argument("path", type=Path)
    an = sub.add_parser("answer")
    an.add_argument("query")
    an.add_argument("--limit", type=int, default=8)
    a = p.parse_args(argv)

    if a.cmd == "build":
        n = build(REPO)
        write_index(REPO)
        print(f"index: {n} chunks; knowledge/INDEX.md regenerated")
        return 0
    if a.cmd == "chunk-file":
        text = a.path.read_text(encoding="utf-8")
        rows = [
            {
                "heading": ch.heading,
                "type": ch.type,
                "title": ch.title,
                "tags": ch.tags,
                "chars": len(ch.text),
                "first_line": ch.text.splitlines()[0][:80] if ch.text else "",
            }
            for ch in chunk(a.path, text)
        ]
        print(json.dumps(rows, indent=1))
        return 0
    hits = search(a.query, repo=REPO, limit=a.limit)
    if a.cmd == "search":
        print(format_hits(hits, a.query))
        return 0 if hits else 1
    print(f'What we know about "{a.query}" ({len(hits)} chunk(s), newest first):\n')
    for h in hits:
        print(
            f"- {h.path}"
            + (f" › {h.heading}" if h.heading else "")
            + f" ({h.type}{', ' + h.date if h.date else ''})"
        )
        print(f"  {h.snippet}")
    if not hits:
        print("- nothing indexed matches; try another phrasing or `just index` if files changed")
    print("\nCite the paths above; do not restate numbers that are not in the snippets.")
    return 0 if hits else 1


if __name__ == "__main__":
    sys.exit(main())
