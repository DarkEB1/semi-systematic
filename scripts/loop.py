#!/usr/bin/env python
"""`just loop SLUG`: re-invoke a task's skill until a stop condition or the budget is hit.

Reads ai/tasks/<slug>.yaml (made by `just task`). Refuses to start without a budget
(max_iterations > 0 and max_hours > 0) or without allowed_paths. Each iteration runs the skill's
deterministic part (.claude/skills/<skill>/run.py) with the task's args, checks that every file
the iteration changed is under allowed_paths, evaluates stop conditions, and appends the
iteration summary to ONE agent-log entry: knowledge/agent-log/<date>-loop-<slug>.md.

A model-driven loop uses the same file: set ``command: ["claude", "-p", "/<skill> {slug} iteration {i}"]``
in the task YAML and the runner executes that instead of run.py, with the same budget and path checks.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "ai" / "tasks"
SKILLS = ROOT / ".claude" / "skills"
LOGS = ROOT / "knowledge" / "agent-log"


class LoopError(RuntimeError):
    pass


def load_task(slug: str) -> dict:
    path = TASKS / f"{slug}.yaml"
    if not path.exists():
        raise LoopError(
            f"no task file {path.relative_to(ROOT).as_posix()}; run `just task {slug}` first"
        )
    task = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = task.get("budget") or {}
    if not (
        int(budget.get("max_iterations", 0) or 0) > 0 and float(budget.get("max_hours", 0) or 0) > 0
    ):
        raise LoopError(
            "refusing to start: budget.max_iterations and budget.max_hours must both be > 0"
        )
    if not task.get("allowed_paths"):
        raise LoopError("refusing to start: allowed_paths is empty")
    if not task.get("command") and not (SKILLS / str(task.get("skill")) / "run.py").exists():
        raise LoopError(f"skill {task.get('skill')!r} has no run.py")
    task["_path"] = path
    return task


def git_status() -> set[str]:
    out = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    files = set()
    for ln in out.splitlines():
        path = ln[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.add(path.strip('"'))
    return files


def under_allowed(path: str, allowed: list[str], log_rel: str) -> bool:
    return path == log_rel or any(path.startswith(a) for a in allowed)


def substitute(args: list[str], slug: str, i: int) -> list[str]:
    return [str(a).replace("{slug}", slug).replace("{i}", str(i)) for a in args]


def run_iteration(task: dict, slug: str, i: int) -> subprocess.CompletedProcess:
    if task.get("command"):
        cmd = substitute(task["command"], slug, i)
    else:
        cmd = [
            sys.executable,
            str(SKILLS / task["skill"] / "run.py"),
            *substitute(task.get("args") or [], slug, i),
        ]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


def stop_hit(conditions: list[str], stdout: str) -> str | None:
    for c in conditions or []:
        kind, _, val = str(c).partition(":")
        if kind == "stdout_contains" and val in stdout:
            return c
        if kind == "file_exists" and (ROOT / val).exists():
            return c
    return None


class AgentLog:
    def __init__(self, slug: str, task: dict, date: dt.date) -> None:
        LOGS.mkdir(parents=True, exist_ok=True)
        self.path = LOGS / f"{date.isoformat()}-loop-{slug}.md"
        self.rel = self.path.relative_to(ROOT).as_posix()
        self.slug, self.task, self.date = slug, task, date
        self.iterations: list[str] = []
        self.touched: set[str] = set()
        self.decisions: list[str] = []

    def write(self, *, stop_reason: str = "running", status: str = "draft") -> None:
        owner = self.task.get("owner", "unknown")
        skill = self.task.get("skill", "custom command")
        budget = self.task.get("budget", {})
        relied = [
            self.task["_path"].relative_to(ROOT).as_posix(),
            f".claude/skills/{skill}/SKILL.md",
            "AGENTS.md",
        ]
        touched = sorted(self.touched) or ["(none: no iteration changed a file)"]
        body = f"""---
id: {self.path.stem}
type: agent-log
title: "Loop {self.slug}: {skill} x{budget.get("max_iterations")}"
date: {self.date.isoformat()}
authors: [{owner}]
owner: {owner}
status: {status}
tags: [infra]
---

# Loop {self.slug}: {skill} x{budget.get("max_iterations")}

## Task

- goal: {self.task.get("goal")}
- metric: {self.task.get("metric")}
- skill: {skill}
- budget: {budget.get("max_iterations")} iterations, {budget.get("max_hours")} h
- allowed paths: {", ".join(self.task.get("allowed_paths", []))}
- stop conditions: {", ".join(map(str, self.task.get("stop_conditions") or [])) or "none (budget only)"}

## Decisions with justification

{chr(10).join(f"- {d}" for d in self.decisions) or "- Ran the skill's deterministic part unattended within the budget; no judgement calls were needed."}

## Summary

Stop reason: **{stop_reason}**.

{chr(10).join(self.iterations) or "_no iterations yet_"}

## Files touched

{chr(10).join(f"- [{t}](../../{t})" if (ROOT / t).exists() else f"- {t}" for t in touched)}

## Files relied on

{chr(10).join(f"- [{r}](../../{r})" for r in relied)}

## PR

none yet. Review the files above, then open a PR with `gh pr create` (the loop never merges).
"""
        self.path.write_text(body, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just loop")
    p.add_argument("slug")
    p.add_argument(
        "--date", type=dt.date.fromisoformat, default=None, help="override today (evals)"
    )
    a = p.parse_args(argv)
    try:
        task = load_task(a.slug)
    except LoopError as e:
        print(f"loop: {e}", file=sys.stderr)
        return 2
    date = a.date or dt.date.today()
    log = AgentLog(a.slug, task, date)
    log.write()
    budget = task["budget"]
    max_iter, max_hours = int(budget["max_iterations"]), float(budget["max_hours"])
    started = time.monotonic()
    stop_reason, rc = "budget: max_iterations reached", 0
    for i in range(1, max_iter + 1):
        elapsed_h = (time.monotonic() - started) / 3600
        if elapsed_h >= max_hours:
            stop_reason = f"budget: max_hours ({max_hours}) reached before iteration {i}"
            break
        before = git_status()
        res = run_iteration(task, a.slug, i)
        changed = sorted(git_status() - before | {f for f in git_status() if f not in before})
        violations = [c for c in changed if not under_allowed(c, task["allowed_paths"], log.rel)]
        log.touched |= set(changed)
        tail = (res.stdout.strip().splitlines() or ["(no output)"])[-5:]
        log.iterations.append(
            f"### Iteration {i}\n\n- exit code: {res.returncode}\n- changed: {', '.join(changed) or 'nothing'}\n- output:\n\n```\n"
            + "\n".join(tail)
            + "\n```\n"
        )
        if violations:
            stop_reason = f"path violation: {', '.join(violations)} outside allowed_paths"
            log.decisions.append(
                f"Stopped at iteration {i}: wrote outside allowed_paths ({', '.join(violations)}). Files left in place for review, nothing reverted."
            )
            rc = 1
            log.write(stop_reason=stop_reason)
            break
        if res.returncode != 0:
            stop_reason = f"iteration {i} failed (exit {res.returncode}): {(res.stderr.strip().splitlines() or ['?'])[-1][:200]}"
            rc = 1
            log.write(stop_reason=stop_reason)
            break
        hit = stop_hit(task.get("stop_conditions") or [], res.stdout)
        log.write(stop_reason="running")
        if hit:
            stop_reason = f"stop condition met: {hit}"
            break
    log.write(stop_reason=stop_reason, status="draft")
    print(f"loop {a.slug}: {len(log.iterations)} iteration(s); {stop_reason}")
    print(f"agent-log: {log.rel}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
