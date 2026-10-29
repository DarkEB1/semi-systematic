"""Embedding stub behind `just embed`.

v1 retrieval is repo-only ILIKE search (ADR-0001). When an embedding model is chosen, set
``EMBEDDING_MODEL`` in .env.example/.env, implement ``embed()`` to add an ``embedding`` column to
.index/chunks.parquet, and record the choice as a new ADR (it changes a dependency and costs money).
"""

from __future__ import annotations

import os


def embed() -> None:
    model = os.getenv("EMBEDDING_MODEL")
    if not model:
        raise NotImplementedError(
            "no embedding model configured. Set EMBEDDING_MODEL in .env (and .env.example), "
            "then implement brain.embed.embed(); see ADR-0001."
        )
    raise NotImplementedError(
        f"EMBEDDING_MODEL={model!r} is set but embedding is not implemented yet"
    )
