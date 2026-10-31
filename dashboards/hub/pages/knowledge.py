"""Knowledge page: knowledge/INDEX.md plus search over the chunk table (the brain tool)."""

from __future__ import annotations

from typing import Any

from brain import Repo, search

from pages import ROOT

REPO = Repo(ROOT)
INDEX_MD = REPO.index_md_path


def rows(query: str, limit: int = 30) -> list[dict]:
    return [h.__dict__ for h in search(query, repo=REPO, limit=limit)] if query else []


def render(mo: Any, filters: dict) -> Any:
    q = filters.get("query") or ""
    parts = []
    if q:
        hits = rows(q)
        parts.append(mo.md(f"**{len(hits)} hit(s) for `{q}`** (newest first)"))
        parts.append(
            mo.ui.table(hits, selection=None)
            if hits
            else mo.md("_nothing matches; `just index` if files changed_")
        )
    index = (
        INDEX_MD.read_text(encoding="utf-8")
        if INDEX_MD.exists()
        else "_knowledge/INDEX.md missing; run `just index`._"
    )
    parts.append(mo.accordion({"knowledge/INDEX.md": mo.md(index)}))
    return mo.vstack(parts)
