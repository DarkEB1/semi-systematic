"""Agent-log page: knowledge/agent-log/*.md, newest first."""

from __future__ import annotations

from typing import Any

from pages import ROOT, frontmatter

LOGS = ROOT / "knowledge" / "agent-log"


def rows() -> list[dict]:
    out = []
    for p in LOGS.glob("*.md"):
        fm = frontmatter(p)
        out.append(
            {
                "date": str(fm.get("date", p.name[:10])),
                "title": str(fm.get("title", p.stem)),
                "owner": str(fm.get("owner", "")),
                "status": str(fm.get("status", "")),
                "tags": ", ".join(map(str, fm.get("tags") or [])),
                "file": p.relative_to(ROOT).as_posix(),
            }
        )
    return sorted(out, key=lambda r: (r["date"], r["title"]), reverse=True)


def render(mo: Any, filters: dict) -> Any:
    data = rows()
    if not data:
        return mo.md(
            "_No agent-log entries yet. Every agent task ends with one (template knowledge/templates/agent-log.md)._"
        )
    return mo.vstack(
        [mo.md(f"**{len(data)} entr(y/ies)**, newest first"), mo.ui.table(data, selection=None)]
    )
