#!/usr/bin/env python
"""Frozen experiments: fail when the diff touches research/experiments/<x>/ whose results.md has
``status: final`` at the base revision. Freezing is one-way; a follow-up goes in a new experiment
with ``parent:`` set in its config.yaml."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP = "research/experiments/"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout


def base_ref() -> str | None:
    for cand in ("origin/main", "main"):
        if git("rev-parse", "--verify", "--quiet", cand).strip():
            mb = git("merge-base", "HEAD", cand).strip()
            if mb:
                return mb
    return None


def changed_files(base: str | None) -> set[str]:
    files: set[str] = set()
    if base:
        files |= set(git("diff", "--name-only", base, "HEAD").split())
    files |= set(git("diff", "--name-only", "HEAD").split())
    files |= set(git("ls-files", "--others", "--exclude-standard").split())
    return {f for f in files if f.startswith(EXP)}


def status_at(base: str | None, results_path: str) -> str | None:
    text = git("show", f"{base}:{results_path}") if base else ""
    if not text:
        p = ROOT / results_path
        text = p.read_text(encoding="utf-8") if p.exists() else ""
    m = re.search(r"^status:\s*([a-z-]+)\s*$", text, flags=re.M)
    return m.group(1) if m else None


def main() -> int:
    base = base_ref()
    touched = changed_files(base)
    frozen: dict[str, list[str]] = {}
    for f in touched:
        parts = f.split("/")
        if len(parts) < 3:
            continue
        folder = "/".join(parts[:3])
        if status_at(base, f"{folder}/results.md") == "final":
            frozen.setdefault(folder, []).append(f)
    for folder, fs in sorted(frozen.items()):
        print(f"{folder}/ is frozen (results.md status: final); modified: {', '.join(sorted(fs))}")
    print(
        f"frozen experiments: {len(touched)} experiment file(s) in diff, {len(frozen)} frozen folder(s) touched"
    )
    return 1 if frozen else 0


if __name__ == "__main__":
    sys.exit(main())
