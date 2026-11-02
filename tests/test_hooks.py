"""The Claude Code hooks in scripts/hooks/: stdlib only, block exactly the zero-exception actions."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
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
agent_channel = _load("agent_channel")


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
        "cat ./.env",
        "cat /workspaces/semi-systematic/.env",
        'head ".env"',
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


URL = "https://github.com/o/r/issues/2#issuecomment-"


def _channel(monkeypatch, me: str | None, comments: list[dict] | None) -> None:
    def fake_gh(args, _cwd):
        if args[:2] == ["api", "user"]:
            return None if me is None else me + "\n"
        return None if comments is None else json.dumps({"comments": comments})

    monkeypatch.setattr(agent_channel, "gh", fake_gh)


def _comment(n: int, who: str, body: str) -> dict:
    return {
        "author": {"login": who},
        "body": body,
        "url": f"{URL}{n}",
        "createdAt": "2026-11-02T00:00:00Z",
    }


def test_inbox_lists_open_messages_only(tmp_path, monkeypatch, capsys):
    _channel(
        monkeypatch,
        "me",
        [
            _comment(1, "ann", "from: ann\nto: me\nneeds: answer\n\nwhich snapshot?"),
            _comment(2, "ann", "needs: review @me please look"),
            _comment(3, "me", "done: answered issuecomment-2"),
            _comment(4, "ann", "to: bob\nnot for me"),
            _comment(5, "me", "to: all\nmy own broadcast"),
            _comment(6, "bob", "to: all\nheads up"),
        ],
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"cwd": str(tmp_path)})))
    assert agent_channel.main(["inbox"]) == 0
    out = capsys.readouterr().out
    assert "2 open message(s) for @me" in out
    assert f"{URL}1 " in out and f"{URL}6 " in out
    assert all(f"{URL}{n} " not in out for n in (2, 3, 4, 5))
    assert "propose how to resolve" in out


def test_inbox_tells_the_agent_to_read_when_gh_fails(tmp_path, monkeypatch, capsys):
    _channel(monkeypatch, None, None)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"cwd": str(tmp_path)})))
    assert agent_channel.main(["inbox"]) == 0
    assert "gh issue view 2 --comments" in capsys.readouterr().out


def _owned_project(tmp_path: Path) -> Path:
    project = tmp_path / "research" / "p"
    project.mkdir(parents=True)
    (project / "README.md").write_text("---\nid: p\nowner: ann\n---\n# p\n", encoding="utf-8")
    return project


def _guard(monkeypatch, tmp_path: Path, rel: str) -> int:
    payload = {"cwd": str(tmp_path), "tool_input": {"file_path": rel}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    return agent_channel.main(["guard"])


def test_guard_blocks_another_owners_work_until_tagged(tmp_path, monkeypatch, capsys):
    _owned_project(tmp_path)
    _channel(monkeypatch, "me", [_comment(1, "ann", "@me research/p is mine")])
    assert _guard(monkeypatch, tmp_path, "research/p/experiments/x/run.py") == 2
    assert "owned by @ann" in capsys.readouterr().err
    _channel(monkeypatch, "me", [_comment(1, "me", "to: ann\n@ann I propose to fix research/p")])
    assert _guard(monkeypatch, tmp_path, "research/p/experiments/x/run.py") == 0


def test_guard_uses_the_files_own_owner_first(tmp_path, monkeypatch):
    project = _owned_project(tmp_path)
    (project / "note.md").write_text("---\nowner: me\n---\n# n\n", encoding="utf-8")
    _channel(monkeypatch, "me", [])
    assert _guard(monkeypatch, tmp_path, "research/p/note.md") == 0


def test_guard_allows_unowned_files_and_unknown_user(tmp_path, monkeypatch):
    _owned_project(tmp_path)
    _channel(monkeypatch, "me", [])
    assert _guard(monkeypatch, tmp_path, "src/quant/x.py") == 0
    _channel(monkeypatch, None, None)
    assert _guard(monkeypatch, tmp_path, "research/p/run.py") == 0


STUB = "#!/bin/sh\necho 'Python was not found'\nexit 49\n"


def _run_sh(tmp_path: Path, stubs: list[str], code: str) -> subprocess.CompletedProcess:
    """run.sh copied next to a one-line hook, with a PATH whose pythons are ``stubs`` or real."""
    hooks, bin_dir = tmp_path / "hooks", tmp_path / "bin"
    hooks.mkdir()
    bin_dir.mkdir()
    shutil.copy(HOOKS / "run.sh", hooks / "run.sh")
    (hooks / "h.py").write_text(code, encoding="utf-8")
    for name in ("python3", "python"):
        if name in stubs:
            (bin_dir / name).write_text(STUB, encoding="utf-8")
            (bin_dir / name).chmod(0o755)
        else:
            (bin_dir / name).symlink_to(sys.executable)
    return subprocess.run(
        ["/bin/sh", str(hooks / "run.sh"), "h.py"],
        input="{}",
        capture_output=True,
        text=True,
        env={"PATH": f"{bin_dir}:/usr/bin:/bin"},
    )


needs_sh = pytest.mark.skipif(os.name == "nt", reason="run.sh is tested with a POSIX PATH")


@needs_sh
def test_run_sh_skips_a_python_stub(tmp_path):
    result = _run_sh(tmp_path, ["python3"], "print('ran')")
    assert result.returncode == 0 and "ran" in result.stdout


@needs_sh
def test_run_sh_passes_a_block_through(tmp_path):
    result = _run_sh(tmp_path, [], "import sys; print('no', file=sys.stderr); sys.exit(2)")
    assert result.returncode == 2 and "no" in result.stderr


@needs_sh
def test_run_sh_blocks_when_the_hook_crashes(tmp_path):
    result = _run_sh(tmp_path, [], "raise RuntimeError('boom')")
    assert result.returncode == 2 and "failed with exit 1" in result.stderr


@needs_sh
def test_run_sh_blocks_without_a_working_python(tmp_path):
    result = _run_sh(tmp_path, ["python3", "python"], "print('ran')")
    assert result.returncode == 2 and "no working python" in result.stderr
