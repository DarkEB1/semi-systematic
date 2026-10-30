#!/usr/bin/env python
"""Create ai/tasks/<slug>.yaml: a budgeted, path-restricted task for `just loop`.

Every loop needs a budget (max_iterations and max_hours) and allowed_paths; the runner refuses to
start without them. Edit the file after creation to set the goal, metric and stop conditions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "ai" / "tasks"
SKILLS = ROOT / ".claude" / "skills"
DEFAULT_ALLOWED = ["research/", "knowledge/agent-log/", "knowledge/research-log/"]


def build(
    slug: str,
    *,
    skill: str,
    goal: str,
    metric: str,
    max_iterations: int,
    max_hours: float,
    allowed: list[str],
    owner: str,
    date: str,
    args: list[str] | None = None,
) -> dict:
    return {
        "slug": slug,
        "created": date,
        "owner": owner,
        "goal": goal,
        "metric": metric,
        "skill": skill,
        # args for the skill's run.py; {slug} and {i} (1-based iteration) are substituted
        "args": args if args is not None else ["{slug}-{i}", "--owner", owner],
        "budget": {"max_iterations": int(max_iterations), "max_hours": float(max_hours)},
        # stop_conditions: "stdout_contains:<text>" | "file_exists:<relative path>"
        "stop_conditions": [],
        "allowed_paths": list(allowed),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just task", description="Create ai/tasks/<slug>.yaml")
    p.add_argument("slug")
    p.add_argument("--skill", default="new-experiment")
    p.add_argument("--goal", default="TODO: one sentence on what done looks like")
    p.add_argument("--metric", default="TODO: the number that says whether an iteration helped")
    p.add_argument("--max-iterations", type=int, default=2)
    p.add_argument("--max-hours", type=float, default=1.0)
    p.add_argument(
        "--allowed", action="append", default=None, help="allowed path prefix (repeatable)"
    )
    p.add_argument(
        "--arg",
        action="append",
        default=None,
        help="argument for the skill run.py (repeatable; {slug} and {i} are substituted; use --arg=--flag)",
    )
    p.add_argument("--owner", default=None)
    p.add_argument("--date", default=None, help="override today (evals)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="print the YAML instead of writing it")
    a = p.parse_args(argv)
    if not (SKILLS / a.skill / "run.py").exists():
        print(f"unknown skill {a.skill!r}: no .claude/skills/{a.skill}/run.py", file=sys.stderr)
        return 2
    owner = a.owner or _default_owner()
    doc = build(
        a.slug,
        skill=a.skill,
        goal=a.goal,
        metric=a.metric,
        max_iterations=a.max_iterations,
        max_hours=a.max_hours,
        allowed=a.allowed or DEFAULT_ALLOWED,
        owner=owner,
        date=a.date or dt.date.today().isoformat(),
        args=a.arg,
    )
    text = yaml.safe_dump(doc, sort_keys=False)
    if a.dry_run:
        print(f"--- ai/tasks/{a.slug}.yaml\n{text}", end="")
        return 0
    out = TASKS / f"{a.slug}.yaml"
    if out.exists() and not a.force:
        print(
            f"{out.relative_to(ROOT).as_posix()} exists; use --force to overwrite", file=sys.stderr
        )
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(out.relative_to(ROOT).as_posix())
    return 0


def _default_owner() -> str:
    import os

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    if os.getenv("R2_HANDLE"):
        return os.environ["R2_HANDLE"]
    team = (
        yaml.safe_load((ROOT / "knowledge" / "context" / "team.yaml").read_text(encoding="utf-8"))
        or {}
    )
    return str(team.get("data_layer_owner") or (team.get("handles") or ["unknown"])[0])


if __name__ == "__main__":
    sys.exit(main())
