"""The Claude Code hooks in scripts/hooks/: stdlib only, block exactly the zero-exception actions."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "scripts" / "hooks"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, HOOKS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


guard_bash = _load("guard_bash")
guard_edit = _load("guard_edit")
format_file = _load("format_file")


def _run(mod, payload: dict, monkeypatch) -> int:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    return mod.main()


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m x --no-verify",
        "git commit -n -m x",
        "git push --force origin feat",
        "git push -f",
        "git push origin main",
        "git mv knowledge/notes/a.md knowledge/notes/b.md",
        "rm -rf knowledge/agent-log",
        "cat .env",
        "grep R2 .env.local",
        "rclone copy x.parquet r2:bucket/curated/x/",
        "aws s3 cp x.parquet s3://bucket/raw/y/",
    ],
)
def test_guard_bash_blocks(command, monkeypatch, capsys):
    assert _run(guard_bash, {"tool_input": {"command": command}}, monkeypatch) == 2
    assert "blocked by" in capsys.readouterr().err


@pytest.mark.parametrize(
    "command",
    [
        "git push --force-with-lease origin feat",
        "git push -u origin research/x",
        "cat .env.example",
        "grep -rn R2_ knowledge/",
        "just check && just test",
        "rclone copy x.parquet r2:bucket/scratch/DarkEB1/x/",
        "ls research/ && rm -rf /tmp/scratch",
    ],
)
def test_guard_bash_allows(command, monkeypatch):
    assert _run(guard_bash, {"tool_input": {"command": command}}, monkeypatch) == 0


def test_guard_bash_ignores_bad_json(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert guard_bash.main() == 0


def test_guard_edit_blocks_generated_secret_and_frozen(tmp_path, monkeypatch):
    exp = tmp_path / "research" / "p" / "experiments" / "2026-01-01-x"
    exp.mkdir(parents=True)
    (exp / "results.md").write_text("---\nstatus: final\n---\n# x\n", encoding="utf-8")
    for rel in [".env", ".env.local", "knowledge/INDEX.md", "uv.lock", str(exp / "run.py")]:
        payload = {"cwd": str(tmp_path), "tool_input": {"file_path": rel}}
        assert _run(guard_edit, payload, monkeypatch) == 2, rel


def test_guard_edit_allows_ordinary_files(tmp_path, monkeypatch):
    exp = tmp_path / "research" / "p" / "experiments" / "2026-01-01-y"
    exp.mkdir(parents=True)
    (exp / "results.md").write_text("---\nstatus: draft\n---\n# y\n", encoding="utf-8")
    for rel in [".env.example", "src/quant/x.py", "knowledge/notes/a/b.md", str(exp / "run.py")]:
        payload = {"cwd": str(tmp_path), "tool_input": {"file_path": rel}}
        assert _run(guard_edit, payload, monkeypatch) == 0, rel


def test_format_file_is_a_no_op_without_a_formatter(tmp_path, monkeypatch):
    monkeypatch.setattr(format_file.shutil, "which", lambda _name: None)
    f = tmp_path / "x.py"
    f.write_text("x=1\n", encoding="utf-8")
    assert (
        _run(format_file, {"cwd": str(tmp_path), "tool_input": {"file_path": str(f)}}, monkeypatch)
        == 0
    )
    assert f.read_text(encoding="utf-8") == "x=1\n"
