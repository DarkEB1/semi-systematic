"""`just todo`: the team's kanban, one file per card on the `todos` branch (ADR-0007).

    just todo "Decide the EM rates instruments" [--owner H] [--due YYYY-MM-DD] [--project P]
    just todo 2026-10-31-decide-the-em-rates-instruments --move doing
    just todo --list [--owner H]
    just todo --sync

Cards are `knowledge/todos/<date>-<slug>.md` on the `todos` branch, which is checked out as a
worktree at `.todos/` (gitignored) whatever branch you are on. Every command fetches first; create
and move commit on that branch and push, so the board is the same for everyone within seconds and
never rides along with a feature branch. Offline, the commit waits and `--sync` pushes it. The
hub's board page reads the same worktree. `--move` edits only the status line; files are never
renamed or moved.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "todos"
WORKTREE = ROOT / ".todos"
TODOS = WORKTREE / "knowledge" / "todos"
TEAM = ROOT / "knowledge" / "context" / "team.yaml"
COLUMNS = ("todo", "doing", "done")
FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def git(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def default_owner() -> str:
    if os.getenv("R2_HANDLE"):
        return os.environ["R2_HANDLE"]
    team = yaml.safe_load(TEAM.read_text(encoding="utf-8")) if TEAM.exists() else {}
    return str(
        (team or {}).get("data_layer_owner") or ((team or {}).get("handles") or ["unknown"])[0]
    )


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if len(slug) > 40:  # cut at a word boundary
        slug = slug[:41].rsplit("-", 1)[0]
    return slug.rstrip("-")


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
    return "---\n" + "\n".join(head) + f"\n---\n\n# {title}\n\n## Done when\n\n_TODO_\n\n## Notes\n"


# --------------------------------------------------------------------------- the todos branch


def ensure_worktree() -> None:
    """Check out the todos branch at .todos/ and fast-forward it. The first time, the branch is
    created from origin/todos, or from HEAD when the remote has none yet."""
    remote = git("fetch", "--quiet", "origin", BRANCH).returncode == 0
    if not WORKTREE.exists():
        git("worktree", "prune")
        if git("rev-parse", "--verify", "--quiet", BRANCH).returncode != 0:
            start = ["--track", f"origin/{BRANCH}"] if remote else ["HEAD"]
            git("branch", BRANCH, *start)
        r = git("worktree", "add", "--quiet", str(WORKTREE), BRANCH)
        if r.returncode:
            print(
                f"cannot check out the {BRANCH} branch at .todos/: {r.stderr.strip()}",
                file=sys.stderr,
            )
            raise SystemExit(1)
    if remote:
        git("pull", "--quiet", "--ff-only", "origin", BRANCH, cwd=WORKTREE)


def push() -> int:
    """Push the todos branch; on a race, rebase once and retry. Offline, the commit waits."""
    r = git("push", "--quiet", "-u", "origin", BRANCH, cwd=WORKTREE)
    if (
        r.returncode
        and git("pull", "--quiet", "--rebase", "origin", BRANCH, cwd=WORKTREE).returncode == 0
    ):
        r = git("push", "--quiet", "-u", "origin", BRANCH, cwd=WORKTREE)
    if r.returncode:
        why = (r.stderr.strip().splitlines() or ["no network?"])[-1]
        print(
            f"committed on branch {BRANCH} but not pushed ({why}); `just todo --sync` retries",
            file=sys.stderr,
        )
    return 0


def commit_and_push(rel: str, message: str) -> int:
    for args in (("add", rel), ("commit", "--quiet", "-m", message)):
        r = git(*args, cwd=WORKTREE)
        if r.returncode:
            print((r.stdout + r.stderr).strip(), file=sys.stderr)
            return 1
    return push()


def validate(path: Path) -> list[str]:
    """The same checks `just check` applies to every knowledge file."""
    from check_frontmatter import check_file, load_handles, load_tags  # scripts/ is on sys.path

    return check_file(path, load_tags(), load_handles())


# --------------------------------------------------------------------------- cards


def read(path: Path) -> dict:
    m = FM_RE.match(path.read_text(encoding="utf-8"))
    fm = yaml.safe_load(m.group(1)) if m else {}
    return fm if isinstance(fm, dict) else {}


def cards() -> list[dict]:
    """Every card as a dict: id, title, owner, status, due, project, path."""
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
                "path": f"knowledge/todos/{p.name}",
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
        print(f"no card {todo_id} on the {BRANCH} branch (`just todo --list`)", file=sys.stderr)
        return 1
    if status not in COLUMNS:
        print(f"status must be one of {', '.join(COLUMNS)}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m or not re.search(r"^status:", m.group(1), flags=re.M):
        print(f"knowledge/todos/{path.name} has no status line", file=sys.stderr)
        return 1
    head = re.sub(r"^status:.*$", f"status: {status}", m.group(1), count=1, flags=re.M)
    path.write_text(text[: m.start(1)] + head + text[m.end(1) :], encoding="utf-8")
    print(f"knowledge/todos/{path.name}: status {status}")
    return commit_and_push(f"knowledge/todos/{path.name}", f"todo: {todo_id} -> {status}")


def create(rel: str, text: str, title: str) -> int:
    path = WORKTREE / rel
    if path.exists():
        print(f"exists, not overwritten: {rel}", file=sys.stderr)
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    errs = validate(path)
    if errs:
        path.unlink()
        print("\n".join(errs), file=sys.stderr)
        return 1
    print(rel)
    return commit_and_push(rel, f"todo: {title}")


# --------------------------------------------------------------------------- main


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="just todo")
    p.add_argument("title", nargs="?", help="a new card's title, or an existing id with --move")
    p.add_argument("--owner", default=None, help="handle; default R2_HANDLE or the team file")
    p.add_argument("--due", default=None, help="YYYY-MM-DD")
    p.add_argument("--project", default=None, help="project slug under research/")
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default today)")
    p.add_argument("--move", choices=COLUMNS, default=None, help="set the status of an existing id")
    p.add_argument("--list", action="store_true", help="print the board as text")
    p.add_argument(
        "--sync", action="store_true", help="fetch the board and push any waiting commit"
    )
    p.add_argument("--dry-run", action="store_true", help="print the new card instead of writing")
    return p


def new_card(a: argparse.Namespace) -> tuple[str, str] | str:
    """(relative path, text) for a new card, or an error message."""
    if not a.title or not slugify(a.title):
        return 'a title is needed: just todo "Decide the EM rates instruments"'
    for label, value in (("--due", a.due), ("--date", a.date)):
        if value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return f"{label} must be YYYY-MM-DD"
    date = a.date or dt.date.today().isoformat()
    todo_id = f"{date}-{slugify(a.title)}"
    text = todo_text(todo_id, a.title, a.owner or default_owner(), date, a.due, a.project)
    return f"knowledge/todos/{todo_id}.md", text


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    card = None
    if not (a.list or a.move or a.sync):
        card = new_card(a)
        if isinstance(card, str):
            print(card, file=sys.stderr)
            return 2
        if a.dry_run:
            print(f"--- {card[0]}")
            print(card[1], end="")
            return 0
    ensure_worktree()
    if a.sync:
        return push()
    if a.list:
        print(board_text(a.owner))
        return 0
    if a.move:
        return move(a.title or "", a.move)
    assert card is not None
    return create(card[0], card[1], a.title)


if __name__ == "__main__":
    sys.exit(main())
