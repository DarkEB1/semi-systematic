#!/usr/bin/env python
"""Deterministic part of the repo-structure skill (`just where THING`).

run.py "ingest module"     explain where a new thing goes and which skill/recipe creates it
run.py --check             verify the convention files agree with each other:
                           templates exist per type, every SKILL.md has the four sections and
                           names only just recipes that exist, every skill has run.py + eval,
                           AGENTS.md lists every skill, team.yaml handles have notes dirs.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / ".claude" / "skills"
SECTIONS = ("## Inputs", "## Steps", "## Checks before opening the PR", "## Done when")

# (keywords, location, rule, how it is created)
MAP: list[tuple[tuple[str, ...], str, str, str]] = [
    (
        ("ingest", "source", "vendor", "fetch"),
        "src/quant/ingest/<source>.py + catalog/datasets/<dataset>.md + a view in catalog/catalog.sql + tests/test_ingest_<source>.py",
        "raw/ is written only by ingest.yml; a laptop writes scratch/<handle>/",
        "pull-data skill: just scaffold-source <source>",
    ),
    (
        ("dataset", "readme", "schema", "catalog"),
        "catalog/datasets/<name>.md (frontmatter type: dataset; the Schema table is the curated contract)",
        "schema contract applies to curated/ only; raw is stored as received",
        "pull-data (new source) or promote-dataset --write-readme (derived dataset)",
    ),
    (
        ("reference", "csv", "lookup", "calendar", "universe"),
        "catalog/reference/<name>.csv, exposed as view ref_<name> in catalog/catalog.sql",
        "hand-maintained, under 1 MB, changed by PR",
        "edit the CSV and add the view; `just check` enforces the size cap",
    ),
    (
        ("promote", "curated", "snapshot"),
        "promote/requests/<date>-<name>.yml",
        "curated/ is append-only and written by promote.yml only",
        "promote-dataset skill: just promote-request <name> <scratch key>",
    ),
    (
        ("experiment", "notebook", "hypothesis", "backtest", "run.py"),
        "research/experiments/<date>-<slug>/{config.yaml, run.py, results.md, figures/}",
        "frozen when results.md says status: final; follow-ups are new experiments with parent:",
        "new-experiment skill: just experiment <slug>",
    ),
    (
        ("signal", "reusable", "shared", "second use", "helper"),
        "a tool under tools/<name>/ (new or existing); never another experiment, never src/quant unless it is data-layer code",
        "code moves out of an experiment only on second use, with a test, in its own PR; units meet only in the data layer, the dashboard and knowledge/ (ADR-0003)",
        "`just new-tool <name>` or edit the existing tool; new-experiment --check-dupes flags candidates",
    ),
    (
        ("library", "quant", "data layer", "connect", "write_once"),
        "src/quant/ (base dependency group only; src/quant/data is CODEOWNERS-gated)",
        "imports only the base group (ruff TID251); data layer changes wait for the data-layer owner",
        "PR; tests under tests/",
    ),
    (
        ("tool", "engine", "package", "cli", "backtester", "optimiser"),
        "tools/<name>/ as an isolated workspace package: src/<name>/, own pyproject.toml, tests/, README",
        "imports only its declared dependencies, never quant or the repo; takes paths as arguments; one lockfile at the root (contract: tools/README.md, enforced by check_tools.py)",
        "`just new-tool <name>` then `uv lock && just setup`; adding a tool is an ADR",
    ),
    (
        ("decision", "adr", "convention", "policy"),
        "knowledge/decisions/ADR-NNNN-<slug>.md",
        "ADR test: changes a convention, a dependency, a data source, a reusable method, or costs money; otherwise a minutes line marked (minor). A changed decision is a new ADR with status: superseded on the old one",
        "template knowledge/templates/decision.md; meeting-notes drafts them from decisions",
    ),
    (
        ("meeting", "minutes", "transcript", "sync"),
        "knowledge/meetings/<date>-<slug>.md",
        "Decisions lines link an ADR or end with (minor); transcript never stored, only the recording link",
        'meeting-notes skill: just meeting <date> "<title>"',
    ),
    (
        ("note", "idea", "scratchpad", "thoughts"),
        "knowledge/notes/<handle>/<date>-<slug>.md",
        "no private key on notes; tags from tags.md; never rename or move",
        "template knowledge/templates/note.md",
    ),
    (
        ("context", "strategy", "glossary", "conventions", "standing"),
        "knowledge/context/<slug>.md (strategy, glossary, vendors, universe, conventions, workflow, tags)",
        "updated in place; git history is the changelog",
        "template knowledge/templates/context.md",
    ),
    (
        ("research-log", "result", "verdict", "finding"),
        "knowledge/research-log/<date>-<slug>.md",
        "every experiment ends in one; numbers come from outputs/ only",
        "new-experiment --finish drafts it",
    ),
    (
        ("agent-log", "agent", "loop", "task"),
        "knowledge/agent-log/<date>-<slug>.md; task definitions in ai/tasks/<slug>.yaml",
        "every agent task ends with an agent-log entry linking files touched and relied on; loops need a budget",
        "just task <slug>, just loop <slug>; template knowledge/templates/agent-log.md",
    ),
    (
        ("tag", "vocabulary", "taxonomy"),
        "knowledge/context/tags.md, one line per tag with a definition",
        "unknown tags fail `just check`; add the line in the same PR that first uses the tag",
        "edit tags.md; `just tags` lists them",
    ),
    (
        ("skill", "routine", "automation"),
        ".claude/skills/<name>/{SKILL.md, run.py} + ai/evals/<name>/{input.yaml, expected.txt}",
        "SKILL.md has Inputs, Steps, Checks before opening the PR, Done when, and names only just recipes that exist",
        "repo-structure skill updates templates, check_frontmatter.py, AGENTS.md and the skill together",
    ),
    (
        ("prompt", "eval", "model"),
        "ai/prompts/ (reusable prompts), ai/evals/<skill>/ (golden fixtures), ai/models.yaml (model names and limits)",
        "`just eval` diffs each skill's deterministic output against its golden",
        "edit and `just eval --update` in a reviewed PR",
    ),
    (
        ("dashboard", "page", "hub", "chart"),
        "dashboards/hub/pages/<name>.py, registered in dashboards/hub/app.py",
        "pages read only catalog views, the chunk table or repo files; they never compute a dataset they then cache",
        "`just dashboard`",
    ),
    (
        ("workflow", "ci", "cron", "action", "github"),
        ".github/workflows/<name>.yml (actions pinned to commit SHAs), CODEOWNERS-gated",
        "every step calls a just recipe; secrets come from repository secrets",
        "PR; data-layer owner reviews",
    ),
    (
        ("secret", "key", "token", "env", "variable"),
        ".env (laptop, gitignored) or GitHub repository secrets (CI); the name goes in .env.example",
        "`just check` fails if a recipe reads a variable not listed in .env.example; never commit a value",
        "edit .env.example in the same PR",
    ),
    (
        ("script", "check", "lint"),
        "scripts/<name>.py, wired into a just recipe (never called directly by people or CI)",
        "the justfile is the only interface",
        "add the recipe in the same PR",
    ),
    (
        ("asset", "image", "logo", "figure"),
        "assets/ (repo-wide) or research/experiments/<x>/figures/ (per experiment)",
        "under 1 MB each",
        "commit; `just check` enforces the cap",
    ),
]


def where(thing: str) -> str:
    t = thing.lower()
    scored = []
    for i, (keys, loc, rule, how) in enumerate(MAP):
        score = sum(1 for k in keys if k in t)
        if score:
            scored.append((score, i, loc, rule, how))
    if not scored:
        return f'No rule matches "{thing}". Closest places: knowledge/notes/<handle>/ for a thought, research/experiments/ for anything with data, src/quant/ for library code. Ask again with a noun from AGENTS.md\'s map.'
    scored.sort(key=lambda s: (-s[0], s[1]))
    out = [f'"{thing}" goes to:']
    for _, _, loc, rule, how in scored[:2]:
        out += [f"  where: {loc}", f"  rule:  {rule}", f"  how:   {how}", ""]
    return "\n".join(out).rstrip()


def check() -> list[str]:
    errs: list[str] = []
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_frontmatter import TYPES  # noqa: PLC0415

    for t in sorted(TYPES):
        if not (ROOT / "knowledge" / "templates" / f"{t}.md").exists():
            errs.append(f"no template for type {t!r} in knowledge/templates/")
    recipes = set(
        re.findall(
            r"^([a-z][a-z0-9-]*)(?:\s+[A-Z*][^:]*)?:\s*$",
            (ROOT / "justfile").read_text(encoding="utf-8"),
            flags=re.M,
        )
    )
    agents = (
        (ROOT / "AGENTS.md").read_text(encoding="utf-8") if (ROOT / "AGENTS.md").exists() else ""
    )
    for sdir in sorted(d for d in SKILLS.iterdir() if d.is_dir()):
        md = sdir / "SKILL.md"
        if not md.exists():
            errs.append(f"{sdir.name}: missing SKILL.md")
            continue
        text = md.read_text(encoding="utf-8")
        for s in SECTIONS:
            if s not in text:
                errs.append(f"{sdir.name}: SKILL.md lacks {s!r}")
        for r in set(re.findall(r"`just ([a-z][a-z0-9-]*)", text)):
            if r not in recipes:
                errs.append(f"{sdir.name}: SKILL.md names `just {r}` which is not a recipe")
        if not (sdir / "run.py").exists():
            errs.append(f"{sdir.name}: missing run.py")
        if not (ROOT / "ai" / "evals" / sdir.name / "input.yaml").exists():
            errs.append(f"{sdir.name}: missing ai/evals/{sdir.name}/input.yaml")
        if agents and sdir.name not in agents:
            errs.append(f"{sdir.name}: not listed in AGENTS.md")
    team = (
        yaml.safe_load((ROOT / "knowledge" / "context" / "team.yaml").read_text(encoding="utf-8"))
        or {}
    )
    for h in team.get("handles", []):
        if not (ROOT / "knowledge" / "notes" / h).is_dir():
            errs.append(f"handle {h}: no knowledge/notes/{h}/ directory")
        co = ROOT / ".github" / "CODEOWNERS"
        if co.exists() and f"@{h}" not in co.read_text(encoding="utf-8"):
            errs.append(f"handle {h}: not in CODEOWNERS")
    return errs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just where")
    p.add_argument("thing", nargs="?")
    p.add_argument("--check", action="store_true")
    a = p.parse_args(argv)
    if a.check:
        errs = check()
        for e in errs:
            print(e)
        print(f"repo-structure: {len(errs)} inconsistency(ies)")
        return 1 if errs else 0
    if not a.thing:
        p.error("THING or --check")
    print(where(a.thing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
