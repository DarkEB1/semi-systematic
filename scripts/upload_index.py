#!/usr/bin/env python
"""`just index-upload`: put .index/chunks.parquet at curated/repo_index/snapshot=<git sha>/data.parquet.

Runs in index.yml with QUANT_ROLE=promote (curated/ is append-only; a re-run on the same sha is a
no-op with a notice). Exposed as the `repo_index` catalog view."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pyarrow.parquet as pq
from brain import Repo

from quant import data

ROOT = Path(__file__).resolve().parents[1]
INDEX_FILE = Repo(ROOT).index_file


def main() -> int:
    if not INDEX_FILE.exists():
        print("no .index/chunks.parquet; run `just index` first", file=sys.stderr)
        return 1
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    key = f"{data.CURATED}repo_index/snapshot={sha}/data.parquet"
    try:
        data.write_once(pq.read_table(INDEX_FILE), key)
    except data.ExistsError:
        print(f"already uploaded: {key}")
        return 0
    print(key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
