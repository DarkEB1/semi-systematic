"""brain: chunking, collection, build, search, index rendering, root discovery.

Self-contained: every test builds its own small repository under tmp_path."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import pytest
from brain import SCHEMA, Repo, build, chunk, collect, render_index, search, write_index

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

ADR = """---
id: ADR-0001-x
type: decision
title: "ADR-0001: use one bucket"
date: 2026-02-01
authors: [t]
owner: t
status: accepted
tags: [infra]
---

# ADR-0001: use one bucket

## Decision

One R2 bucket with three prefixes.
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


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    (tmp_path / "justfile").write_text("", encoding="utf-8")
    (tmp_path / "knowledge" / "notes" / "t").mkdir(parents=True)
    (tmp_path / "knowledge" / "notes" / "t" / "2026-01-01-x.md").write_text(MD, encoding="utf-8")
    (tmp_path / "knowledge" / "decisions").mkdir()
    (tmp_path / "knowledge" / "decisions" / "ADR-0001-x.md").write_text(ADR, encoding="utf-8")
    (tmp_path / "knowledge" / "templates").mkdir()
    (tmp_path / "knowledge" / "templates" / "note.md").write_text(MD, encoding="utf-8")
    (tmp_path / "catalog" / "datasets").mkdir(parents=True)
    (tmp_path / "catalog" / "datasets" / "d.md").write_text(
        ADR.replace("type: decision", "type: dataset").replace("ADR-0001-x", "d"), encoding="utf-8"
    )
    exp = tmp_path / "research" / "experiments" / "2026-01-01-demo"
    exp.mkdir(parents=True)
    (exp / "config.yaml").write_text(
        "slug: demo\nowner: t\ndatasets:\n  - name: prices_daily\n    snapshot: 2026-01-01\n",
        encoding="utf-8",
    )
    (exp / "results.md").write_text(
        "---\nslug: demo\nstatus: draft\n---\n\n# demo\n\n## Result\n\nx\n"
    )
    (tmp_path / ".claude" / "skills" / "s").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "s" / "SKILL.md").write_text(
        "---\nname: s\n---\n\n# s\n\n## Steps\n\n1. go\n", encoding="utf-8"
    )
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "x.py").write_text(PY, encoding="utf-8")
    return Repo(tmp_path)


def test_chunk_markdown_splits_on_h2_and_keeps_frontmatter():
    chunks = chunk(Path("knowledge/notes/t/2026-01-01-x.md"), MD)
    assert [c.heading for c in chunks] == ["", "First", "Second"]
    assert chunks[0].type == "note" and chunks[0].title == "A note"
    assert chunks[0].tags == ["fx", "idea"]
    assert chunks[2].text.startswith("```python") and "body two" in chunks[2].text
    assert len({c.chunk_id for c in chunks}) == 3


def test_private_markdown_is_dropped():
    assert chunk(Path("k.md"), MD.replace("tags: [fx, idea]", "tags: [fx]\nprivate: true")) == []


def test_chunk_python_per_toplevel_with_docstring_first():
    chunks = chunk(Path("src/pkg/x.py"), PY)
    assert [c.heading for c in chunks] == ["module", "alpha", "Beta"]
    assert chunks[1].text.startswith("Alpha does things.\n\ndef alpha")
    assert all(c.type == "code" for c in chunks)


def test_chunk_experiment_config_and_results(repo: Repo):
    exp = repo.path("research/experiments/2026-01-01-demo")
    (c,) = chunk(exp / "config.yaml", (exp / "config.yaml").read_text(), repo)
    assert c.type == "experiment" and c.title == "demo" and c.datasets == ["prices_daily"]
    assert c.date == "2026-01-01" and c.path == "research/experiments/2026-01-01-demo/config.yaml"
    res = chunk(exp / "results.md", (exp / "results.md").read_text(), repo)
    assert {r.type for r in res} == {"results"}


def test_collect_skips_templates_and_index_md(repo: Repo):
    write_index(repo)
    rels = [repo.rel(p) for p in collect(repo)]
    assert "knowledge/notes/t/2026-01-01-x.md" in rels
    assert "catalog/datasets/d.md" in rels
    assert ".claude/skills/s/SKILL.md" in rels
    assert "src/pkg/x.py" in rels
    assert not any("templates" in r or r.endswith("INDEX.md") for r in rels)


def test_build_writes_parquet_with_schema(repo: Repo):
    n = build(repo)
    t = pq.read_table(repo.index_file)
    assert n == t.num_rows > 5
    assert t.schema.names == SCHEMA.names
    assert set(t["source"].to_pylist()) == {"repo"}
    assert repo.index_file == repo.root / ".index" / "chunks.parquet"


def test_search_builds_on_demand_and_sorts_newest_first(repo: Repo):
    hits = search("R2", repo=repo)
    assert repo.index_file.exists()
    assert {h.path for h in hits} >= {
        "knowledge/decisions/ADR-0001-x.md",
        "knowledge/notes/t/2026-01-01-x.md",
    }
    dates = [h.date or "" for h in hits]
    assert dates == sorted(dates, reverse=True)


def test_search_without_repo_needs_an_existing_index(tmp_path: Path):
    with pytest.raises(ValueError):
        search("x")
    with pytest.raises(FileNotFoundError):
        search("x", index=tmp_path / "missing.parquet")


def test_index_md_has_three_sections_and_relative_links(repo: Repo):
    md = render_index(repo)
    assert "## By type" in md and "## By tag" in md and "## By owner" in md
    assert "(decisions/ADR-0001-x.md)" in md and "(../catalog/datasets/d.md)" in md
    assert "### dataset" in md


def test_custom_layout_and_index_dir(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text(MD, encoding="utf-8")
    repo = Repo(tmp_path, knowledge="docs", index_dir="build/index", index_md="docs/TOC.md")
    assert build(repo) == 3
    assert repo.index_file == tmp_path / "build" / "index" / "chunks.parquet"
    assert write_index(repo) == tmp_path / "docs" / "TOC.md"


def test_discover_walks_up_to_a_marker(repo: Repo):
    deep = repo.path("knowledge/notes/t")
    assert Repo.discover(deep).root == repo.root
    with pytest.raises(FileNotFoundError):
        Repo.discover(deep, markers=("no-such-marker",))
