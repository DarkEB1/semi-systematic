"""PostToolUse hook for Edit/Write: format the file that was just written, if a formatter exists.

Stdlib only. Uses the first of ``ruff`` on PATH, ``uvx ruff`` or ``uv run ruff``; with none of
them it exits 0 silently, so a machine without the toolchain is never blocked (pre-commit and CI
still format-check). Python files are import-sorted and formatted; markdown files are formatted
because ruff also formats python code blocks inside them.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

RUFF_VERSION = "0.17.3"  # keep equal to .pre-commit-config.yaml


def ruff_command() -> list[str] | None:
    if shutil.which("ruff"):
        return ["ruff"]
    if shutil.which("uvx"):
        return ["uvx", f"ruff@{RUFF_VERSION}"]
    if shutil.which("uv"):
        return ["uv", "run", "ruff"]
    return None


def run(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=False)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    raw = (payload.get("tool_input") or {}).get("file_path")
    if not raw:
        return 0
    path = Path(raw)
    if path.suffix not in {".py", ".md"} or not path.exists():
        return 0
    ruff = ruff_command()
    if ruff is None:
        return 0
    cwd = Path(payload.get("cwd") or ".")
    if path.suffix == ".py":
        run([*ruff, "check", "--select", "I", "--fix", "--quiet", str(path)], cwd)
    run([*ruff, "format", "--quiet", str(path)], cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
