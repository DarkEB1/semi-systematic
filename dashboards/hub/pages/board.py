"""Board page: the team's kanban, one column per status (todo, doing, done) of the cards on the
`todos` branch, which `just todo` keeps checked out at .todos/ (ADR-0007). Filterable by owner
and status. Read-only: `just todo` creates and moves cards; `just dashboard` syncs first."""

from __future__ import annotations

import datetime as dt
from typing import Any

from pages import ROOT, frontmatter

WORKTREE = ROOT / ".todos"
TODOS = WORKTREE / "knowledge" / "todos"
COLUMNS = ("todo", "doing", "done")


def rows() -> list[dict]:
    out = []
    for p in sorted(TODOS.glob("*.md")) if TODOS.exists() else []:
        fm = frontmatter(p)
        if fm.get("type") != "todo":
            continue
        out.append(
            {
                "id": str(fm.get("id", p.stem)),
                "title": str(fm.get("title", p.stem)),
                "owner": str(fm.get("owner", "")),
                "status": str(fm.get("status", "todo")),
                "due": str(fm.get("due") or ""),
                "project": str(fm.get("project") or ""),
                "path": f"knowledge/todos/{p.name}",
            }
        )
    return out


def filtered(filters: dict) -> list[dict]:
    out = rows()
    if filters.get("owner"):
        out = [r for r in out if filters["owner"].lower() in r["owner"].lower()]
    if filters.get("status"):
        out = [r for r in out if r["status"] == filters["status"]]
    return out


def card(r: dict, today: str) -> str:
    late = r["due"] and r["status"] != "done" and r["due"] < today
    meta = [f"@{r['owner']}"]
    if r["due"]:
        meta.append(("**late** " if late else "due ") + r["due"])
    if r["project"]:
        meta.append(f"project {r['project']}")
    return f"**{r['title']}**  \n{' · '.join(meta)}  \n`{r['id']}`"


def render(mo: Any, filters: dict) -> Any:
    if not WORKTREE.exists():
        return mo.md(
            "_The board is the `todos` branch, checked out at `.todos/` by `just todo`. "
            "Run `just todo --list` once (or restart with `just dashboard`), then reload._"
        )
    data = filtered(filters)
    today = dt.date.today().isoformat()
    columns = []
    for col in COLUMNS:
        mine = [r for r in data if r["status"] == col]
        items = [mo.md(card(r, today)) for r in mine] or [mo.md("_empty_")]
        columns.append(mo.vstack([mo.md(f"### {col} ({len(mine)})"), *items]))
    head = mo.md(
        f'**{len(data)} card(s)** on the `todos` branch. `just todo "<title>" --owner <handle>` '
        "adds one; `just todo <id> --move doing` moves it; both push, so everyone sees it."
    )
    return mo.vstack([head, mo.hstack(columns, widths="equal", align="start")])
