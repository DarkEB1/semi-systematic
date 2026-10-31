"""`just todo`: the team's kanban as files under knowledge/todos/ (ADR-0006).

    just todo "Decide the EM rates instruments" [--owner H] [--due YYYY-MM-DD] [--project P]
    just todo 2026-10-31-decide-the-em-rates-instruments --move doing
    just todo --list [--owner H]

One file per todo from knowledge/templates/todo.md; the column is `status` (todo, doing, done) and
the card belongs to `owner` (a handle in knowledge/context/team.yaml). The hub's board page renders
the same files. `--move` edits only the status line, so a file is never renamed or moved.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TODOS = ROOT / "knowledge" / "todos"
TEAM = ROOT / "knowledge" / "context" / "team.yaml"
COLUMNS = ("todo", "doing", "done")
FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def default_owner() -> str:
    if os.getenv("R2_HANDLE"):
        return os.environ["R2_HANDLE"]
    team = yaml.safe_load(TEAM.read_text(encoding="utf-8")) if TEAM.exists() else {}
    return str(
        (team or {}).get("data_layer_owner") or ((team or {}).get("handles") or ["unknown"])[0]
    )


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:40].rstrip("-")


def todo_text(
    todo_id: str, title: str, owner: str, date: str, due: str | None, project: str | None
) -> str:
    title = title.replace('"', "'")
    head = [
        f"id: {todo_id}",
        "type: todo",
        f'title: "{title}"',
        f"date: {date}",
        f"authors: [{owner}]",
        f"owner: {owner}",
        "status: todo",
        *([f"due: {due}"] if due else []),
        "tags: []",
        *([f"project: {project}"] if project else []),
        "related: []",
    ]
    return (
        "---\n" + "\n".join(head) + f"\n---\n\n# {title}\n\n## Done when\n\n_TODO_\n\n## Notes\n\n"
    )


def read(path: Path) -> dict:
    m = FM_RE.match(path.read_text(encoding="utf-8"))
    fm = yaml.safe_load(m.group(1)) if m else {}
    return fm if isinstance(fm, dict) else {}


def cards() -> list[dict]:
    """Every todo as a dict: id, title, owner, status, due, project, path."""
    out = []
    for p in sorted(TODOS.glob("*.md")) if TODOS.exists() else []:
        fm = read(p)
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
                "path": p.relative_to(ROOT).as_posix(),
            }
        )
    return out


def board_text(owner: str | None = None, today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    rows = [c for c in cards() if not owner or c["owner"].lower() == owner.lower()]
    lines = []
    for col in COLUMNS:
        mine = [c for c in rows if c["status"] == col]
        lines.append(f"{col} ({len(mine)})")
        for c in mine:
            late = c["due"] and c["status"] != "done" and c["due"] < today.isoformat()
            due = f"  due {c['due']}{' LATE' if late else ''}" if c["due"] else ""
            lines.append(f"  {c['id']}  @{c['owner']}{due}  {c['title']}")
    return "\n".join(lines)


def move(todo_id: str, status: str) -> int:
    path = TODOS / f"{todo_id}.md"
    if not path.exists():
        print(f"no todo knowledge/todos/{todo_id}.md", file=sys.stderr)
        return 1
    if status not in COLUMNS:
        print(f"status must be one of {', '.join(COLUMNS)}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m or not re.search(r"^status:", m.group(1), flags=re.M):
        print(f"{path.relative_to(ROOT).as_posix()} has no status line", file=sys.stderr)
        return 1
    head = re.sub(r"^status:.*$", f"status: {status}", m.group(1), count=1, flags=re.M)
    path.write_text(text[: m.start(1)] + head + text[m.end(1) :], encoding="utf-8")
    print(f"{path.relative_to(ROOT).as_posix()}: status {status}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="just todo")
    p.add_argument("title", nargs="?", help="a new todo's title, or an existing id with --move")
    p.add_argument("--owner", default=None, help="handle; default R2_HANDLE or the team file")
    p.add_argument("--due", default=None, help="YYYY-MM-DD")
    p.add_argument("--project", default=None, help="project slug under research/")
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default today)")
    p.add_argument("--move", choices=COLUMNS, default=None, help="set the status of an existing id")
    p.add_argument("--list", action="store_true", help="print the board as text")
    p.add_argument("--dry-run", action="store_true", help="print the file instead of writing")
    return p


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    if a.list:
        print(board_text(a.owner))
        return 0
    if a.move:
        return move(a.title or "", a.move)
    if not a.title or not slugify(a.title):
        print('a title is needed: just todo "Decide the EM rates instruments"', file=sys.stderr)
        return 2
    for label, value in (("--due", a.due), ("--date", a.date)):
        if value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            print(f"{label} must be YYYY-MM-DD", file=sys.stderr)
            return 2
    date = a.date or dt.date.today().isoformat()
    todo_id = f"{date}-{slugify(a.title)}"
    text = todo_text(todo_id, a.title, a.owner or default_owner(), date, a.due, a.project)
    rel = f"knowledge/todos/{todo_id}.md"
    if a.dry_run:
        print(f"--- {rel}")
        print(text, end="")
        return 0
    path = ROOT / rel
    if path.exists():
        print(f"exists, not overwritten: {rel}", file=sys.stderr)
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
