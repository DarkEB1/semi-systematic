"""brain: chunking, collection rules, build output, search."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
from brain import build, index_md, search

MD = """---
id: 2026-01-01-x
type: note
title: "A note"
date: 2026-01-01
authors: [t]
owner: t
tags: [fx, idea]
---

# A note

intro paragraph

## First

body one about R2 buckets

## Second

```python
## not a heading inside a fence
```
body two
"""

PY = '''"""Module doc."""

import os


def alpha(x):
    """Alpha does things."""
    return x + 1


class Beta:
    """Beta holds state."""

    def m(self):
        return 1
'''


def test_chunk_markdown_splits_on_h2_and_keeps_frontmatter():
    chunks = build.chunk(Path("knowledge/notes/t/2026-01-01-x.md"), MD)
    assert [c.heading for c in chunks] == ["", "First", "Second"]
    assert (
        chunks[0].type == "note"
        and chunks[0].title == "A note"
        and chunks[0].tags == ["fx", "idea"]
    )
    assert chunks[2].text.startswith("```python") and "body two" in chunks[2].text
    assert len({c.chunk_id for c in chunks}) == 3


def test_private_markdown_is_dropped():
    assert (
        build.chunk(Path("k.md"), MD.replace("tags: [fx, idea]", "tags: [fx]\nprivate: true")) == []
    )


def test_chunk_python_per_toplevel_with_docstring_first():
    chunks = build.chunk(Path("src/quant/x.py"), PY)
    assert [c.heading for c in chunks] == ["module", "alpha", "Beta"]
    assert chunks[1].text.startswith("Alpha does things.\n\ndef alpha")
    assert chunks[2].text.startswith("Beta holds state.")
    assert all(c.type == "code" for c in chunks)


def test_chunk_experiment_config():
    cfg = "slug: demo\nowner: t\ndatasets:\n  - name: prices_daily\n    snapshot: 2026-01-01\n"
    (c,) = build.chunk(Path("research/experiments/2026-01-01-demo/config.yaml"), cfg)
    assert (
        c.type == "experiment"
        and c.title == "demo"
        and c.datasets == ["prices_daily"]
        and c.date == "2026-01-01"
    )


def test_build_writes_parquet_with_schema(tmp_path):
    out = tmp_path / "chunks.parquet"
    n = build.build(out=out)
    t = pq.read_table(out)
    assert n == t.num_rows >= 20
    assert t.schema.names == build.SCHEMA.names
    assert set(t["source"].to_pylist()) == {"repo"}
    assert any(p.startswith("knowledge/decisions/ADR-0001") for p in t["path"].to_pylist())
    assert any(p.startswith("src/quant/data/") for p in t["path"].to_pylist())


def test_search_finds_the_adr(tmp_path):
    out = tmp_path / "chunks.parquet"
    build.build(out=out)
    hits = search.search("R2", index=out)
    assert any("ADR-0001" in h.path for h in hits)
    dates = [h.date or "" for h in hits]
    assert dates == sorted(dates, reverse=True), "newest first"


def test_index_md_has_three_sections():
    md = index_md.render()
    assert "## By type" in md and "## By tag" in md and "## By owner" in md
    assert "ADR-0001" in md
