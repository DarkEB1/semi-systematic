"""Model-driven loops: the task file carries a prompt and a budget, the runner builds a capped,
auto-mode `claude -p` command, and nothing in it can ask a person for approval."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


loop = _load("loop", ROOT / "scripts" / "loop.py")
task = _load("task", ROOT / "scripts" / "task.py")


def test_task_with_prompt_records_turn_and_spend_caps():
    rc = task.main(
        [
            "sweep",
            "--prompt",
            "/new-experiment {slug}-{i}",
            "--max-turns",
            "12",
            "--max-usd",
            "2.5",
            "--owner",
            "DarkEB1",
            "--date",
            "2026-01-01",
            "--dry-run",
        ]
    )
    assert rc == 0


def test_claude_command_is_auto_mode_and_capped():
    t = {
        "prompt": "/new-experiment {slug}-{i}: next lookback",
        "budget": {"max_iterations": 2, "max_hours": 1, "max_turns": 12, "max_usd": 2.5},
    }
    cmd = loop.claude_command(t, "sweep", 3)
    assert cmd[:3] == ["claude", "-p", "/new-experiment sweep-3: next lookback"]
    assert cmd[cmd.index("--permission-mode") + 1] == "auto"
    assert cmd[cmd.index("--max-turns") + 1] == "12"
    assert cmd[cmd.index("--max-budget-usd") + 1] == "2.5"
    assert "--bare" not in cmd and "--dangerously-skip-permissions" not in cmd


def test_iteration_command_prefers_command_then_prompt_then_runner():
    assert loop.iteration_command({"command": ["echo", "{i}"]}, "s", 1) == ["echo", "1"]
    assert loop.iteration_command({"prompt": "p", "budget": {}}, "s", 1)[0] == "claude"
    cmd = loop.iteration_command({"skill": "new-experiment", "args": ["{slug}-{i}"]}, "s", 2)
    assert cmd[1].endswith("new_experiment.py") and cmd[2] == "s-2"


def test_runner_name_follows_the_skill_name():
    assert loop.runner("repo-structure").name == "repo_structure.py"
    assert loop.runner("repo-structure").exists()


@pytest.fixture
def loop_repo(tmp_path, monkeypatch):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-b", "main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    (tmp_path / "outside.txt").write_text("original")
    git("add", ".")
    git("commit", "-m", "base")
    monkeypatch.setattr(loop, "ROOT", tmp_path)
    monkeypatch.setattr(loop, "LOGS", tmp_path / "knowledge/agent-log")
    return tmp_path, git


@pytest.mark.parametrize("commit", [False, True])
def test_loop_detects_edits_to_dirty_files_even_if_committed(loop_repo, monkeypatch, commit):
    root, _ = loop_repo
    (root / "outside.txt").write_text("already dirty")
    code = "from pathlib import Path; Path('outside.txt').write_text('changed again')"
    if commit:
        code += "; import subprocess; subprocess.run(['git','add','.'], check=True); subprocess.run(['git','commit','-m','iteration'], check=True)"
    spec = {
        "owner": "DarkEB1",
        "command": [sys.executable, "-c", code],
        "budget": {"max_iterations": 2, "max_hours": 1},
        "allowed_paths": ["research/"],
        "_path": root / "task.yaml",
    }
    monkeypatch.setattr(loop, "load_task", lambda _: spec)
    assert loop.main(["test", "--date", "2026-11-02"]) == 1
    log = (root / "knowledge/agent-log/2026-11-02-loop-test.md").read_text()
    assert "path violation: outside.txt" in log
    assert "### Iteration 2" not in log


def test_snapshot_detects_deleted_renamed_and_untracked_files(loop_repo):
    root, _ = loop_repo
    before = loop.file_snapshot()
    (root / "outside.txt").rename(root / "renamed.txt")
    (root / "new.txt").write_text("new")
    after = loop.file_snapshot()
    assert {f for f in before.keys() | after.keys() if before.get(f) != after.get(f)} == {
        "outside.txt",
        "renamed.txt",
        "new.txt",
    }


def test_allowed_path_does_not_match_sibling_prefix():
    assert loop.under_allowed("research/a/run.py", ["research"], "log.md")
    assert not loop.under_allowed("research-other/run.py", ["research"], "log.md")


def test_timeout_kills_child_processes(tmp_path, monkeypatch):
    monkeypatch.setattr(loop, "ROOT", tmp_path)
    child = "import time; from pathlib import Path; time.sleep(0.7); Path('escaped').touch()"
    code = f"import subprocess,sys,time; subprocess.Popen([sys.executable, '-c', {child!r}]); print('started', flush=True); time.sleep(30)"
    started = time.monotonic()
    result = loop.run_iteration({"command": [sys.executable, "-c", code]}, "test", 1, 0.3)
    assert result.returncode == 124
    assert "started" in result.stdout
    assert "max_hours" in result.stderr
    assert time.monotonic() - started < 5
    time.sleep(0.8)
    assert not (tmp_path / "escaped").exists()
