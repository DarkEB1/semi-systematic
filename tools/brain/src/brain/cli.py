"""`brain` CLI: build, index-md, search, embed. Every command takes ``--root``; the default is the
nearest repository above the working directory (see ``Repo.discover``)."""

from __future__ import annotations

from pathlib import Path

import typer

from brain.build import build as _build_index
from brain.embed import embed as _embed
from brain.index_md import write as _write_index
from brain.repo import Repo
from brain.search import format_hits as _format_hits
from brain.search import search as _search_index

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Retrieval index over a repo.")

ROOT_OPT = typer.Option(None, "--root", help="repository root (default: discovered from cwd)")


def _repo(root: Path | None) -> Repo:
    return Repo(root) if root else Repo.discover()


def _show(repo: Repo, p: Path) -> str:
    return p.relative_to(repo.root).as_posix() if p.is_relative_to(repo.root) else str(p)


@app.command()
def build(root: Path | None = ROOT_OPT, out: Path | None = None) -> None:
    """Walk the repo and write <index_dir>/chunks.parquet (or --out PATH)."""
    repo = _repo(root)
    target = out or repo.index_file
    n = _build_index(repo, out=target)
    typer.echo(f"index: {n} chunks -> {_show(repo, target)}")


@app.command("index-md")
def index_md(root: Path | None = ROOT_OPT) -> None:
    """Regenerate the knowledge index markdown (by type, by tag, by owner)."""
    repo = _repo(root)
    p = _write_index(repo)
    typer.echo(f"index: wrote {_show(repo, p)}")


@app.command()
def search(query: str, root: Path | None = ROOT_OPT, limit: int = 20) -> None:
    """DuckDB ILIKE over text + heading + title, newest first."""
    hits = _search_index(query, repo=_repo(root), limit=limit)
    typer.echo(_format_hits(hits, query))
    if not hits:
        raise typer.Exit(code=1)


@app.command()
def embed(root: Path | None = ROOT_OPT, model: str = "") -> None:
    """Add an embedding column with --model NAME (errors until one is implemented)."""
    _embed(_repo(root), model=model or None)
