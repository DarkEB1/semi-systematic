"""`just todo`: a todo is a file in template shape, a move edits only the status line, and the
board groups cards by status and owner."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


todo = _load("todo", ROOT / "scripts" / "todo.py")


def test_new_todo_is_in_template_shape():
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
    assert "owner: DarkEB1\n" in text and text.count("\n# ") == 1


def test_slug_and_argument_validation():
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
    assert todo.main(["Decide EM rates", "--owner", "DarkEB1", "--dry-run"]) == 0


def test_move_changes_only_the_status_line(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(todo, "TODOS", tmp_path)
    monkeypatch.setattr(todo, "ROOT", tmp_path.parent)
    f = tmp_path / "2026-10-31-a.md"
    before = todo.todo_text("2026-10-31-a", "A", "DarkEB1", "2026-10-31", None, None)
    f.write_text(before, encoding="utf-8")
    assert todo.move("2026-10-31-a", "doing") == 0
    after = f.read_text(encoding="utf-8")
    assert after.replace("status: doing", "status: todo") == before
    assert todo.move("2026-10-31-a", "parked") == 2
    assert todo.move("missing", "done") == 1


def test_board_groups_by_status_and_filters_by_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(todo, "TODOS", tmp_path)
    monkeypatch.setattr(todo, "ROOT", tmp_path.parent)
    (tmp_path / "2026-10-31-a.md").write_text(
        todo.todo_text("2026-10-31-a", "A", "DarkEB1", "2026-10-31", "2026-01-01", None),
        encoding="utf-8",
    )
    (tmp_path / "2026-10-31-b.md").write_text(
        todo.todo_text("2026-10-31-b", "B", "someone", "2026-10-31", None, None).replace(
            "status: todo", "status: done"
        ),
        encoding="utf-8",
    )
    import datetime as dt

    board = todo.board_text(today=dt.date(2026, 10, 31))
    assert board.startswith(
        "todo (1)\n  2026-10-31-a  @DarkEB1  due 2026-01-01 LATE  A\ndoing (0)\ndone (1)"
    )
    assert "2026-10-31-b" not in todo.board_text("DarkEB1", today=dt.date(2026, 10, 31))
