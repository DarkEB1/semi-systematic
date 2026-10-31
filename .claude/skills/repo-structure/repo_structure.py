#!/usr/bin/env python
"""Deterministic part of the repo-structure skill (`just where THING`).

repo_structure.py "ingest module"   explain where a new thing goes and which skill/recipe creates it
repo_structure.py --check           verify the convention files agree with each other:
                           templates exist per type, every SKILL.md has the four sections and
                           names only just recipes that exist, every skill has its runner + eval,
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
        ("experiment", "notebook", "hypothesis", "run.py"),
        "research/<project>/experiments/<date>-<slug>/{config.yaml, run.py, results.md, figures/}",
        "lives inside one project; frozen when results.md says status: final; follow-ups are new experiments with parent:; never imports another experiment (ADR-0003)",
        "new-experiment skill: just experiment <slug> --project <p>",
    ),
    (
        ("project", "research line", "programme", "workstream"),
        "research/<project>/ with README.md (type project, id = folder) and experiments/",
        "a project is a folder and an isolated unit (ADR-0004): it meets other projects only through datasets, the dashboard and knowledge/; never renamed",
        "just project <slug>, then just experiment <slug> --project <project>",
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
        ".claude/skills/<name>/{SKILL.md, <name_with_underscores>.py} + ai/evals/<name>/{input.yaml, expected.txt}",
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
        "assets/ (repo-wide) or research/<project>/experiments/<x>/figures/ (per experiment)",
        "under 1 MB each",
        "commit; `just check` enforces the cap",
    ),
    (
        ("hook", "deny", "permission", "guard"),
        "scripts/hooks/<name>.py (stdlib python, exit 2 blocks) wired in .claude/settings.json; a deny rule for a tool pattern",
        "only zero-exception rules are enforced; everything else is Claude's judgement in auto mode, never a prompt to a person",
        "add the script, a test in tests/test_hooks.py and the settings entry in one PR (ADR-0005)",
    ),
    (
        ("subagent", "agent", "reviewer", "review"),
        ".claude/agents/<name>.md (frontmatter: tools, disallowedTools, effort, maxTurns)",
        "a subagent that judges never edits; the reviewer ends with `verdict: merge` or `verdict: hold`",
        "add the file; mention it in knowledge/context/working-with-agents.md",
    ),
    (
        ("agents.md", "rules", "instructions", "claude.md"),
        "AGENTS.md (root router, under 100 lines) or <folder>/AGENTS.md for rules that only matter there",
        "only what the repo cannot tell an agent by itself; no CLAUDE.md (ADR-0005)",
        "edit; `/doctor prompt-audit` finds stale lines",
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
        return f'No rule matches "{thing}". Closest places: knowledge/notes/<handle>/ for a thought, research/<project>/experiments/ for anything with data, src/quant/ for library code. Ask again with a noun from AGENTS.md\'s map.'
    scored.sort(key=lambda s: (-s[0], s[1]))
    out = [f'"{thing}" goes to:']
    for _, _, loc, rule, how in scored[:2]:
        out += [f"  where: {loc}", f"  rule:  {rule}", f"  how:   {how}", ""]
    return "\n".join(out).rstrip()


def _recipes() -> set[str]:
    return set(
        re.findall(
            r"^([a-z][a-z0-9-]*)(?:\s+[A-Z*][^:]*)?:\s*$",
            (ROOT / "justfile").read_text(encoding="utf-8"),
            flags=re.M,
        )
    )


def check_templates() -> list[str]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_frontmatter import TYPES  # noqa: PLC0415

    return [
        f"no template for type {t!r} in knowledge/templates/"
        for t in sorted(TYPES)
        if not (ROOT / "knowledge" / "templates" / f"{t}.md").exists()
    ]


def check_skill(sdir: Path, recipes: set[str], agents: str) -> list[str]:
    md = sdir / "SKILL.md"
    if not md.exists():
        return [f"{sdir.name}: missing SKILL.md"]
    text = md.read_text(encoding="utf-8")
    errs = [f"{sdir.name}: SKILL.md lacks {s!r}" for s in SECTIONS if s not in text]
    errs += [
        f"{sdir.name}: SKILL.md names `just {r}` which is not a recipe"
        for r in set(re.findall(r"`just ([a-z][a-z0-9-]*)", text))
        if r not in recipes
    ]
    runner = sdir / (sdir.name.replace("-", "_") + ".py")
    if not runner.exists():
        errs.append(f"{sdir.name}: missing runner {runner.name}")
    if not (ROOT / "ai" / "evals" / sdir.name / "input.yaml").exists():
        errs.append(f"{sdir.name}: missing ai/evals/{sdir.name}/input.yaml")
    if agents and sdir.name not in agents:
        errs.append(f"{sdir.name}: not listed in AGENTS.md")
    return errs


def check_team() -> list[str]:
    team = (
        yaml.safe_load((ROOT / "knowledge" / "context" / "team.yaml").read_text(encoding="utf-8"))
        or {}
    )
    co = ROOT / ".github" / "CODEOWNERS"
    owners = co.read_text(encoding="utf-8") if co.exists() else None
    errs = []
    for h in team.get("handles", []):
        if not (ROOT / "knowledge" / "notes" / h).is_dir():
            errs.append(f"handle {h}: no knowledge/notes/{h}/ directory")
        if owners is not None and f"@{h}" not in owners:
            errs.append(f"handle {h}: not in CODEOWNERS")
    return errs


def check() -> list[str]:
    agents = (
        (ROOT / "AGENTS.md").read_text(encoding="utf-8") if (ROOT / "AGENTS.md").exists() else ""
    )
    recipes = _recipes()
    errs = check_templates()
    for sdir in sorted(d for d in SKILLS.iterdir() if d.is_dir()):
        errs += check_skill(sdir, recipes, agents)
    return errs + check_team()


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
