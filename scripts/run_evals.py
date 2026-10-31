#!/usr/bin/env python
"""`just eval`: run every skill's deterministic part against its golden fixture.

ai/evals/<skill>/input.yaml holds ``args`` (list) and optional ``env`` (dict); ``expected.txt`` is
the exact stdout. Dates and owners are passed explicitly in args so output is stable.
``--update`` rewrites expected.txt from the current output. Fails if a skill lacks its runner,
SKILL.md or an eval fixture.
"""

from __future__ import annotations

import argparse
import difflib
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"


def runner(skill: str) -> Path:
    """A skill's deterministic part: .claude/skills/<name>/<name_with_underscores>.py."""
    return SKILLS / skill / (skill.replace("-", "_") + ".py")


EVALS = ROOT / "ai" / "evals"
SECTIONS = ("## Inputs", "## Steps", "## Checks before opening the PR", "## Done when")


def run(skill: str, spec: dict) -> str:
    env = dict(os.environ)
    env.update({"TZ": "UTC", "PYTHONHASHSEED": "0", "QUANT_EVAL": "1", "PYTHONIOENCODING": "utf-8"})
    env.update({k: str(v) for k, v in (spec.get("env") or {}).items()})
    res = subprocess.run(
        [sys.executable, str(runner(skill)), *map(str, spec.get("args") or [])],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    out = res.stdout.replace("\r\n", "\n")
    if res.returncode != 0:
        out += f"\n[exit {res.returncode}]\n" + res.stderr.replace("\r\n", "\n")[-2000:]
    return "\n".join(ln.rstrip() for ln in out.splitlines()).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just eval")
    p.add_argument("skills", nargs="*", help="subset of skills (default: all)")
    p.add_argument("--update", action="store_true", help="rewrite expected.txt from current output")
    a = p.parse_args(argv)
    names = a.skills or sorted(d.name for d in SKILLS.iterdir() if d.is_dir())
    failures = 0
    for name in names:
        sdir = SKILLS / name
        problems = []
        if not runner(name).exists():
            problems.append(f"missing {runner(name).name}")
        skill_md = sdir / "SKILL.md"
        if not skill_md.exists():
            problems.append("missing SKILL.md")
        else:
            text = skill_md.read_text(encoding="utf-8")
            for s in SECTIONS:
                if s not in text:
                    problems.append(f"SKILL.md lacks section {s!r}")
        edir = EVALS / name
        spec_path, exp_path = edir / "input.yaml", edir / "expected.txt"
        if not spec_path.exists():
            problems.append("missing ai/evals/<skill>/input.yaml")
        if problems:
            failures += 1
            print(f"FAIL {name}: " + "; ".join(problems))
            continue
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
        got = run(name, spec)
        if a.update or not exp_path.exists():
            exp_path.write_text(got, encoding="utf-8")
            print(f"WROTE {name}: {exp_path.relative_to(ROOT).as_posix()}")
            continue
        exp = exp_path.read_text(encoding="utf-8").replace("\r\n", "\n")
        exp = "\n".join(ln.rstrip() for ln in exp.splitlines()).strip() + "\n"
        if got == exp:
            print(f"PASS {name}")
        else:
            failures += 1
            print(f"FAIL {name}: output differs from expected.txt")
            sys.stdout.writelines(
                difflib.unified_diff(exp.splitlines(True), got.splitlines(True), "expected", "got")
            )
    print(f"eval: {len(names)} skill(s), {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
