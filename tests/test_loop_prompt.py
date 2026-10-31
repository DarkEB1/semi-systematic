"""Model-driven loops: the task file carries a prompt and a budget, the runner builds a capped,
auto-mode `claude -p` command, and nothing in it can ask a person for approval."""

from __future__ import annotations

import importlib.util
from pathlib import Path

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
