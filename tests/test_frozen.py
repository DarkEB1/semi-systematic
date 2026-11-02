"""Freeze applies to the base revision, not to a newly finished experiment."""

import runpy
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("previous,expected", [(None, 0), ("draft", 0), ("final", 1)])
def test_freeze_against_git_base(tmp_path, monkeypatch, previous, expected):
    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-b", "main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    folder = tmp_path / "research/demo/experiments/new"
    folder.mkdir(parents=True)
    result = folder / "results.md"
    if previous:
        result.write_text(f"---\nstatus: {previous}\n---\n")
        git("add", ".")
    git("commit", "--allow-empty", "-m", "base")
    git("checkout", "-b", "experiment")
    result.write_text("---\nstatus: final\n---\nfinished\n")
    git("add", ".")
    git("commit", "-m", "finish")
    check = runpy.run_path(str(ROOT / "scripts/check_frozen.py"))["main"]
    monkeypatch.setitem(check.__globals__, "ROOT", tmp_path)
    assert check() == expected


def test_renaming_a_frozen_experiment_is_caught(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-b", "main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    folder = tmp_path / "research/demo/experiments/done"
    folder.mkdir(parents=True)
    (folder / "results.md").write_text("---\nstatus: final\n---\n")
    git("add", ".")
    git("commit", "-m", "base")
    git("checkout", "-b", "rename")
    git("mv", "research/demo/experiments/done", "research/demo/experiments/renamed")
    git("commit", "-m", "rename")
    check = runpy.run_path(str(ROOT / "scripts/check_frozen.py"))["main"]
    monkeypatch.setitem(check.__globals__, "ROOT", tmp_path)
    assert check() == 1
