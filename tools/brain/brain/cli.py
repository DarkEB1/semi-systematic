"""`brain` CLI, wired to just recipes: build (just index), index-md (just index), search, embed."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from brain import build as _build
from brain import index_md as _index_md
from brain import search as _search

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Repo retrieval index.")


@app.command()
def build(out: Path | None = None) -> None:
    """Walk the repo and write .index/chunks.parquet (or --out PATH)."""
    out = out or _build.INDEX_FILE
    n = _build.build(out=out)
    typer.echo(
        f"index: {n} chunks -> {out.relative_to(_build.ROOT).as_posix() if out.is_relative_to(_build.ROOT) else out}"
    )


@app.command("index-md")
def index_md() -> None:
    """Regenerate knowledge/INDEX.md (by type, by tag, by owner)."""
    p = _index_md.write()
    typer.echo(f"index: wrote {p.relative_to(_build.ROOT).as_posix()}")


@app.command()
def search(query: str, limit: int = 20) -> None:
    """DuckDB ILIKE over text + heading, newest first."""
    hits = _search.search(query, limit=limit)
    typer.echo(_search.format_hits(hits, query))
    if not hits:
        raise typer.Exit(code=1)


@app.command()
def embed() -> None:
    """Embed chunks (not configured in v1)."""
    from brain.embed import embed as _embed

    try:
        _embed()
    except NotImplementedError as e:
        typer.echo(f"embed: {e}", err=True)
        sys.exit(2)


if __name__ == "__main__":
    app()
