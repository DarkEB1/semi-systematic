---
id: 2026-11-02-review-fixes
type: agent-log
title: "Fix catalog, ingestion, experiment freezing and loop limits"
date: 2026-11-02
authors: [Codex, Claude]
owner: DarkEB1
status: draft
tags: [infra, data]
related: [working-with-agents, workflow]
---

# Fix catalog, ingestion, experiment freezing and loop limits

## Task

DarkEB1 requested fixes for findings 1–4 of the repository setup review.

## Decisions with justification

- Preserve SQL statements following full-line comments; exercise the actual catalog in a regression test.
- Reject empty Yahoo responses and loss of stored symbol/date rows before any monthly replacement.
  Check all expected Yahoo symbols for freshness. No live bucket writes are needed for verification.
- Read freeze status only from the base revision (HEAD if no main ref exists), allowing a new
  experiment to be submitted as final while protecting previously final experiments.
- Compare file contents and modes across loop iterations, including dirty files and committed
  changes. Kill the subprocess group on deadline. Document post-execution path detection accurately;
  this repair does not introduce a sandbox or change the existing allowed-path policy.

## Summary

Regression tests cover the four findings. Verification runs in an isolated development-container
copy, with fixture storage and temporary Git repositories. All three gates passed:

- `just check`: exit 0; `Success: no issues found in 57 source files`; `no leaks found`.
- `just test`: `108 passed in 2.36s` (20 additional regression cases).
- `just eval`: `eval: 7 skill(s), 0 failure(s)`.

No production ingestion or research loop was run.

Claude then reviewed the diff and finished the PR. Each new test was run against the unfixed code
(`git worktree` at the previous HEAD, with `PYTHONPATH` pointing at its `src/` so the editable
install did not mask it) and failed there: 8 in data, ingest and data health, 6 in freeze and loop.
Gates on the fixed tree: `just check` exit 0, `just test` `108 passed`, `just eval`
`7 skill(s), 0 failure(s)`. Known behaviour, left as designed and named in the PR:

- The nightly ingest stops (no write) when a symbol returns no rows or when a symbol is removed from
  the universe mid-month, because its stored rows in the current month would be lost. Both need a
  person to look, which is the intent.
- `check_history` checks every stored month from `since` on, not only months in the response; a
  backfill with an explicit earlier `today` would be refused. Errs on the safe side.
- `check_frozen` compares with the merge base, so an experiment finalised and then edited on the
  same unmerged branch is not caught by CI; the `guard_edit` hook still blocks hand edits to it.
- The loop timeout uses `os.killpg`, POSIX only; `just loop` runs in the container.

## Files touched

- [AGENTS.md](../../AGENTS.md)
- [data layer](../../src/quant/data/__init__.py)
- [Yahoo ingestion](../../src/quant/ingest/yahoo.py)
- [data health](../../src/quant/datahealth.py)
- [freeze checker](../../scripts/check_frozen.py)
- [loop runner](../../scripts/loop.py)
- [data tests](../../tests/test_data.py)
- [ingestion tests](../../tests/test_ingest_yahoo.py)
- [data-health tests](../../tests/test_datahealth.py)
- [freeze tests](../../tests/test_frozen.py)
- [loop tests](../../tests/test_loop_prompt.py)
- [dataset contract](../../catalog/datasets/prices_daily.md)
- [workflow](../context/workflow.md)
- [agent guide](../context/working-with-agents.md)
- [this log](2026-11-02-review-fixes.md)

## Files relied on

All files listed above, plus:

- [quant rules](../../src/quant/AGENTS.md)
- [knowledge rules](../AGENTS.md)
- [agent-log template](../templates/agent-log.md)
- [team](../context/team.yaml)
- [test fixtures](../../tests/conftest.py)
- [ingest writer](../../src/quant/ingest/_base.py)
- [dataset metadata](../../src/quant/datasets.py)
- [catalog SQL](../../catalog/catalog.sql)
- [Python configuration](../../pyproject.toml)
- [demo task](../../ai/tasks/demo.yaml)
- [refresh runner](../../.claude/skills/refresh-data/refresh_data.py)
- [shell guard](../../scripts/hooks/guard_bash.py)
- [command recipes](../../justfile)
- [devcontainer image](../../.devcontainer/Dockerfile)
- [contributing guide](../../CONTRIBUTING.md)

## PR

[#3](https://github.com/DarkEB1/semi-systematic/pull/3), stacked on #1. It touches `src/quant/data/**` and `catalog/**`, so it is opened, not merged: the
data-layer owner reviews.
