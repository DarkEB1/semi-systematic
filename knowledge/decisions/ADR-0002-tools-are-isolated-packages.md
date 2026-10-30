---
id: ADR-0002-tools-are-isolated-packages
type: decision
title: "ADR-0002: tools are isolated packages, instantiable anywhere"
date: 2026-10-30
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [infra]
related: [ADR-0001-initial-setup, start-here]
---

# ADR-0002: tools are isolated packages, instantiable anywhere

## Context

ADR-0001 made `tools/*` uv workspace members but said nothing about what a tool may know or
import. By the end of the scaffold, `brain` located the repository from its own file and
hard-coded the folder names it indexed, consumers reached it and `quant` through `sys.path`
hacks, and its tests ran against this repository's content. That is a monorepo with internal
helpers, not a set of tools. The intent, stated on 2026-10-30, is the opposite: a growing set of
tools (a backtester, an optimiser, a calendar library, vendor clients), each usable on its own, in
this repo or another, so that adopting or replacing an engine is one package's concern.

## Decision

A tool is an isolated package under `tools/<name>/` that follows the contract in
`tools/README.md`, enforced by `scripts/check_tools.py` in `just check`:

- src layout (`src/<name>/`), own `pyproject.toml` whose project name equals the folder, `tests/`, `README.md`, `__version__` and `__all__`.
- It imports only what its own `pyproject.toml` declares: never `quant`, `scripts`, `dashboards` or `tests`; another tool only when listed as a dependency.
- It does not locate the repository from its own file, read `.env`, or hard-code repo paths in behaviour. Inputs are arguments or a small config object with defaults (`brain.Repo`).
- Its tests build their own fixtures and run without the repository, the bucket or `.env`. Checks of the tool against this repository live in the root `tests/`.
- `just new-tool NAME` scaffolds a compliant tool and registers it; `uv lock` follows. Adding a tool is an ADR because it changes a dependency.
- No `sys.path.insert` anywhere in the repo beyond three allow-listed script-tier files; installed packages are imported.

`brain` was refactored to the contract (`Repo` config, `--root` on the CLI, fixture-based tests,
no `polars` or `python-frontmatter` dependency it did not use). `backtest` keeps its reserved,
empty shape in the new layout. The repo-specific code stays where it was: `src/quant/` for the
data layer, `scripts/` for checkers and runners, `.claude/skills/*/run.py` for skill logic.

## Consequences

- A second repository can `pip install` or workspace-link a tool and use it with its own paths.
- Replacing an engine (for example a third-party backtester) touches one tool and its tests.
- Each tool carries its own small overhead: pyproject, README, tests, a lock update.
- Skill runners remain script-tier. A skill whose core becomes reusable moves that core into a tool and keeps `run.py` thin; that move is the next step, not part of this ADR.
- The eight rules in `AGENTS.md` are unchanged; the map row for tools and the `just` interface gained `new-tool`.

## Alternatives considered

- Leave tools as plain workspace members with repo knowledge: cheapest today, but every new engine would be wired into the repo's layout and never reusable.
- One `tools` package with submodules: fewer files, but no per-tool dependencies and no way to install one tool without the others.
- Separate git repositories per tool: full isolation, but a second lockfile and release process per tool, against the one-lockfile decision in ADR-0001; revisit if a tool gains users outside this repo.
