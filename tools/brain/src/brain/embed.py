"""Embedding stub.

v1 retrieval is keyword-only (ADR-0001). When an embedding model is chosen, pass its name in
(``embed(repo, model=...)``; the justfile reads ``EMBEDDING_MODEL`` from .env and passes it),
implement the column, and record the choice as a new ADR (it changes a dependency and costs money).
"""

from __future__ import annotations

from brain.repo import Repo


def embed(repo: Repo, model: str | None = None) -> None:
    if not model:
        raise NotImplementedError(
            "no embedding model configured. Set EMBEDDING_MODEL in .env (and .env.example), "
            "pass it to brain.embed(), and implement the column; see ADR-0001."
        )
    raise NotImplementedError(
        f"embedding model {model!r} given but embedding is not implemented yet ({repo.index_file})"
    )
