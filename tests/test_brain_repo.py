"""brain against this repository (the consumer-side check; brain's own tests use fixtures)."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
from brain import Repo, build, render_index, search

ROOT = Path(__file__).resolve().parents[1]


def test_build_over_the_repo_finds_the_adr_and_the_data_layer(tmp_path):
    repo = Repo(ROOT, index_dir=str(tmp_path))
    n = build(repo)
    t = pq.read_table(repo.index_file)
    assert n == t.num_rows >= 20
    paths = t["path"].to_pylist()
    assert any(p.startswith("knowledge/decisions/ADR-0001") for p in paths)
    assert any(p.startswith("src/quant/data/") for p in paths)
    hits = search("R2", repo=repo)
    assert any("ADR-0001" in h.path for h in hits)


def test_index_md_lists_the_adr():
    md = render_index(Repo(ROOT))
    assert "## By type" in md and "ADR-0001" in md
