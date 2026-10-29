"""Knowledge page: knowledge/INDEX.md plus search over the chunk table (brain.search)."""

from __future__ import annotations

import sys

from pages import ROOT

if str(ROOT / "tools" / "brain") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools" / "brain"))

INDEX_MD = ROOT / "knowledge" / "INDEX.md"


def rows(query: str, limit: int = 30) -> list[dict]:
    from brain import search

    return [h.__dict__ for h in search.search(query, limit=limit)] if query else []


def render(mo, filters: dict):
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
