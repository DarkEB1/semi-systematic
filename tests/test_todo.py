"""`just todo`: a card is a file in template shape, a move edits only the status line and
commits, the board groups cards by status and owner, and a dry run never touches git."""

from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


todo = _load("todo", ROOT / "scripts" / "todo.py")


@pytest.fixture
def board(tmp_path, monkeypatch):
    """A fake .todos/ worktree; git is replaced by a recorder."""
    todos = tmp_path / "knowledge" / "todos"
    todos.mkdir(parents=True)
    monkeypatch.setattr(todo, "WORKTREE", tmp_path)
    monkeypatch.setattr(todo, "TODOS", todos)
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(todo, "commit_and_push", lambda rel, msg: calls.append((rel, msg)) or 0)
    monkeypatch.setattr(todo, "ensure_worktree", lambda: calls.append(("ensure",)))
    return todos, calls


def test_new_card_is_in_template_shape():
    text = todo.todo_text(
        "2026-10-31-decide-em-rates",
        "Decide EM rates",
        "DarkEB1",
        "2026-10-31",
        "2026-11-15",
        "demo",
    )
    assert text.startswith("---\nid: 2026-10-31-decide-em-rates\ntype: todo\n")
    assert "status: todo\n" in text and "due: 2026-11-15\n" in text and "project: demo\n" in text
    assert "owner: DarkEB1\n" in text and text.count("\n# ") == 1 and text.endswith("## Notes\n")


def test_slugs_and_argument_validation(board):
    assert (
        todo.slugify("Decide the EM rates / credit instruments!")
        == "decide-the-em-rates-credit-instruments"
    )
    assert (
        todo.slugify("Build the backtesting framework (tools/backtest)")
        == "build-the-backtesting-framework-tools"
    )
    assert todo.main(["", "--dry-run"]) == 2
    assert todo.main(["x", "--due", "next week", "--dry-run"]) == 2


def test_dry_run_never_touches_git(board, capsys):
    _, calls = board
    assert (
        todo.main(["Decide EM rates", "--owner", "DarkEB1", "--date", "2026-10-31", "--dry-run"])
        == 0
    )
    assert calls == []
    assert capsys.readouterr().out.startswith(
        "--- knowledge/todos/2026-10-31-decide-em-rates.md\n---\n"
    )


def test_move_changes_only_the_status_line_and_commits(board):
    todos, calls = board
    f = todos / "2026-10-31-a.md"
    before = todo.todo_text("2026-10-31-a", "A", "DarkEB1", "2026-10-31", None, None)
    f.write_text(before, encoding="utf-8")
    assert todo.main(["2026-10-31-a", "--move", "doing"]) == 0
    assert f.read_text(encoding="utf-8").replace("status: doing", "status: todo") == before
    assert calls == [
        ("ensure",),
        ("knowledge/todos/2026-10-31-a.md", "todo: 2026-10-31-a -> doing"),
    ]
    assert todo.move("2026-10-31-a", "parked") == 2
    assert todo.move("missing", "done") == 1


def test_board_groups_by_status_and_filters_by_owner(board):
    todos, _ = board
    (todos / "2026-10-31-a.md").write_text(
        todo.todo_text("2026-10-31-a", "A", "DarkEB1", "2026-10-31", "2026-01-01", None),
        encoding="utf-8",
    )
    (todos / "2026-10-31-b.md").write_text(
        todo.todo_text("2026-10-31-b", "B", "someone", "2026-10-31", None, None).replace(
            "status: todo", "status: done"
        ),
        encoding="utf-8",
    )
    text = todo.board_text(today=dt.date(2026, 10, 31))
    assert text.startswith(
        "todo (1)\n  2026-10-31-a  @DarkEB1  due 2026-01-01 LATE  A\ndoing (0)\ndone (1)"
    )
    assert "2026-10-31-b" not in todo.board_text("DarkEB1", today=dt.date(2026, 10, 31))
