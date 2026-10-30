---
id: 2026-10-30-tools-library
type: agent-log
title: "Make the tools tier a set of isolated packages"
date: 2026-10-30
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra]
related: [ADR-0002-tools-are-isolated-packages, 2026-10-29-initial-scaffold]
---

# Make the tools tier a set of isolated packages

## Task

Asked by @DarkEB1 on 2026-10-30 after a review of the setup: "lets make the tools library
structured. For example, if I build or import a backtesting tool, I want that to be a tool, not
part of the rest, and the aim is to build out a set of such tools." One-off refactor on the open
scaffold branch, no loop, no budget.

## Decisions with justification

- Wrote the contract down (`tools/README.md`) and enforced it (`scripts/check_tools.py` in
  `just check`) rather than relying on review: the point of the ask is that the next tool, by a
  person or an agent, comes out isolated without anyone remembering the rules.
- src layout for every tool: a package under `src/` cannot be imported from the working directory
  by accident, which is what made the old `sys.path` hacks "work".
- `brain` takes a `Repo` config object instead of a root constant: the defaults keep every
  existing call working, and another repository passes its own folder names. `Repo.discover()`
  exists for the CLI only; library callers pass a root.
- brain's dependency list was trimmed to what it imports (`polars` and `python-frontmatter` were
  declared and unused); the lockfile changes accordingly.
- brain's tests now build fixture repositories under `tmp_path`; the two assertions that
  depended on this repo (ADR-0001 is found, `src/quant/data` is indexed) moved to
  `tests/test_brain_repo.py` as consumer-side checks.
- Skill runners were not moved into packages: that was offered earlier as a separate step and the
  ask was about the tools tier. ADR-0002 names it as the next step.
- Three `sys.path.insert` uses stay, allow-listed with reasons: marimo's `app.py` for its own
  `pages/` package, `scripts/tags.py` importing a sibling script, and the repo-structure runner
  importing constants from `scripts/check_frontmatter.py`.

## Summary

Done: `tools/README.md` (contract), `scripts/check_tools.py` and `scripts/new_tool.py` with
`just new-tool`, both tools moved to src layout, `brain` 0.2.0 with `Repo`, `--root` and
fixture tests, consumers (`build-index/run.py`, hub pages, `upload_index.py`, two skill runners,
`onboard.py`) import installed packages, pytest `testpaths` globs `tools/*/tests`, ADR-0002,
docs updated (AGENTS.md map and interface, start-here tree, CONTRIBUTING, repo-structure MAP,
brain README). Verified in the devcontainer: `uv lock`, `just setup`, `just check`, `just test`,
`just eval`, `just index`, `just search "R2"`, `just new-tool --dry-run`.

Not done, needs a human: the PR review; the decision on whether skill cores move into tools
(ADR-0002 Consequences).

## Files touched

- [tools/README.md](../../tools/README.md), [tools/brain](../../tools/brain/README.md) (pyproject, `src/brain/*`, tests), [tools/backtest](../../tools/backtest/README.md) (pyproject, `src/backtest/__init__.py`, tests)
- [scripts/check_tools.py](../../scripts/check_tools.py), [scripts/new_tool.py](../../scripts/new_tool.py), [scripts/upload_index.py](../../scripts/upload_index.py), [scripts/onboard.py](../../scripts/onboard.py)
- [tests/test_new_tool.py](../../tests/test_new_tool.py), [tests/test_brain_repo.py](../../tests/test_brain_repo.py)
- [.claude/skills/build-index/run.py](../../.claude/skills/build-index/run.py), [promote-dataset/run.py](../../.claude/skills/promote-dataset/run.py), [refresh-data/run.py](../../.claude/skills/refresh-data/run.py), [repo-structure/run.py](../../.claude/skills/repo-structure/run.py)
- [dashboards/hub/pages/knowledge.py](../../dashboards/hub/pages/knowledge.py), [dashboards/hub/pages/data_health.py](../../dashboards/hub/pages/data_health.py)
- [justfile](../../justfile), [pyproject.toml](../../pyproject.toml), [uv.lock](../../uv.lock)
- [AGENTS.md](../../AGENTS.md), [CONTRIBUTING.md](../../CONTRIBUTING.md), [start-here](../context/start-here.md), [ADR-0002](../decisions/ADR-0002-tools-are-isolated-packages.md), [knowledge/INDEX.md](../INDEX.md)

## Files relied on

- [ADR-0001](../decisions/ADR-0001-initial-setup.md) (one lockfile, workspace members)
- [AGENTS.md](../../AGENTS.md) and [tools/README.md](../../tools/README.md)
- The previous `tools/brain/brain/*.py` (git history before this commit)

## PR

Same branch as the scaffold: `chore/initial-scaffold` -> `main`, PR "chore: initial scaffold".
Not merged by the agent.
