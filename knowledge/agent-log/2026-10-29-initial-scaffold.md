---
id: 2026-10-29-initial-scaffold
type: agent-log
title: "Initial scaffold of the monorepo (Step 0 storage setup and the repo layout)"
date: 2026-10-29
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra, data]
related: [ADR-0001-initial-setup, 2026-10-28-kickoff, workflow]
---

# Initial scaffold of the monorepo (Step 0 storage setup and the repo layout)

## Task

Asked by @DarkEB1 on 2026-10-28 with a written spec: set up a private monorepo for a small quant
research team (knowledge, code, experiments, dashboards as plain text with consistent metadata;
retrieval index; skills; sandboxed agent loops with budgets). Step 0 was interactive through the
Cloudflare and GitHub dashboards; the rest ran unattended and ends in the PR
"chore: initial scaffold". No loop, no budget: a one-off scaffold.

## Decisions with justification

- Bucket, endpoint, token and GitHub settings: recorded in [ADR-0001](../decisions/ADR-0001-initial-setup.md),
  including the three deviations the operator chose (repo stays public, lifecycle rule skipped,
  B2 deferred) and the EU endpoint that differed from the spec's template.
- Yahoo chart endpoint instead of Stooq for `prices_daily`: Stooq is behind a JavaScript
  challenge; Yahoo returns daily OHLCV for FX without a key. FRED is the documented fallback.
- Write policy by `QUANT_ROLE` with a run-stamped scratch mirror for off-CI ingests: R2 cannot
  scope a token to a prefix, so the rules live in `quant.data` and are enforced by tests.
- gitleaks runs from the pinned binary (local pre-commit hook and `just check`) with
  `.gitleaks.toml` excluding the local `.env`; the official pre-commit hook would download a Go toolchain.
- Evals compare each skill's `--dry-run` stdout with a golden file, dates and owners passed
  explicitly; the loop runner executes `run.py` by default and a `command:` for model-driven loops.
- The demo loop task runs new-experiment with `--dry-run` so the verification leaves no stray
  experiment folders; a second, real loop with a too-narrow `allowed_paths` was run to prove the
  path check stops the loop, and its outputs were deleted.
- CODEOWNERS lists every top-level directory (ownership map) but only the data-layer block
  (`src/quant/data/**`, `catalog/**`, `promote/**`, `.github/**`) gates skill autonomy, otherwise
  no skill could ever merge.
- `ci` is a reserved scratch handle for the audit, so CI runs without the ingest role have a
  legal place to write.

## Summary

Done: Step 0 verified (`rclone ls` and a DuckDB `SELECT 1` against the bucket with the team-read
key); the layout, environment, data layer, knowledge conventions and checkers, retrieval index,
experiments and dashboard hub, seven skills with evals, task and loop runner, seven workflows,
AGENTS.md and README. Verified in the devcontainer image: `just check`, `just test` (39 tests),
`just eval` (7 skills), `just index` (166 chunks), `just search "R2"` finds the ADR, the demo
experiment runs headless, the dashboard serves on port 2718 and lists the demo, the loop stops on
budget and on a path violation, a live ingest lands under `scratch/ci/` and read-only keys are
refused by R2 while `raw/` is refused by policy.

Not done, needs a human: the open TODOs in ADR-0001 (scratch lifecycle rule, B2 backup, first
vendor); the first nightly `ingest.yml` run has not happened yet, so `raw/` is empty and
data-health reports `prices_daily` as missing until then; the PR review and merge.

Follow-up on the same PR (asked by @DarkEB1: "clear guides for other agents and humans on how
the workflow actually works and looks and how they can engage with it, all self-contained"):
added `knowledge/context/start-here.md` (reading order, annotated tree, first hour for people and
for agents), `walkthrough.md` (the week as real commands with output captured in the container),
`working-with-agents.md` (invoking skills from Claude Code or any assistant, tasks and loops,
reviewing agent PRs), `data-access.md` (connect, load, write_once examples), `CONTRIBUTING.md`,
`ai/prompts/` (one paste-ready prompt per skill plus the shared preamble), READMEs for
`src/quant`, `research`, `dashboards/hub`, `tools/brain`, `tools/backtest`, and a first filled
note under `knowledge/notes/DarkEB1/`. README and AGENTS.md link them; `check_links.py` now also
scans `CONTRIBUTING.md` and `src/`.

## Files touched

- [AGENTS.md](../../AGENTS.md), [README.md](../../README.md), [CLAUDE.md](../../CLAUDE.md), [justfile](../../justfile), [pyproject.toml](../../pyproject.toml), [.env.example](../../.env.example)
- [.devcontainer/Dockerfile](../../.devcontainer/Dockerfile), [.devcontainer/devcontainer.json](../../.devcontainer/devcontainer.json), [.pre-commit-config.yaml](../../.pre-commit-config.yaml), [.gitleaks.toml](../../.gitleaks.toml)
- [.github/CODEOWNERS](../../.github/CODEOWNERS), [.github/dependabot.yml](../../.github/dependabot.yml), the seven workflows under [.github/workflows](../../.github/workflows/ci.yml)
- [src/quant/data](../../src/quant/data/__init__.py), [src/quant/ingest](../../src/quant/ingest/__init__.py), [src/quant/promote](../../src/quant/promote/__init__.py), [src/quant/datahealth.py](../../src/quant/datahealth.py), [src/quant/audit.py](../../src/quant/audit.py), [tests](../../tests/test_data.py)
- [catalog/catalog.sql](../../catalog/catalog.sql), [catalog/datasets/prices_daily.md](../../catalog/datasets/prices_daily.md), [catalog/reference/universe.csv](../../catalog/reference/universe.csv)
- [knowledge/templates](../../knowledge/templates/meeting.md), [knowledge/context](../../knowledge/context/workflow.md), [ADR-0001](../decisions/ADR-0001-initial-setup.md), [2026-10-28-kickoff](../meetings/2026-10-28-kickoff.md), [research-log demo entry](../research-log/2026-10-29-demo-prices-daily-sanity.md), [loop demo entry](2026-10-29-loop-demo.md), [knowledge/INDEX.md](../INDEX.md)
- [tools/brain](../../tools/brain/brain/build.py), [tools/backtest](../../tools/backtest/README.md), [scripts](../../scripts/check_frontmatter.py), [dashboards/hub](../../dashboards/hub/app.py)
- [.claude/skills](../../.claude/skills/new-experiment/SKILL.md) (seven skills), [ai/evals](../../ai/evals/README.md), [ai/tasks/demo.yaml](../../ai/tasks/demo.yaml), [ai/models.yaml](../../ai/models.yaml)
- [research/experiments/2026-10-29-demo](../../research/experiments/2026-10-29-demo/results.md)
- Guides: [start-here](../context/start-here.md), [walkthrough](../context/walkthrough.md), [working-with-agents](../context/working-with-agents.md), [data-access](../context/data-access.md), [CONTRIBUTING.md](../../CONTRIBUTING.md), [ai/prompts](../../ai/prompts/README.md), [src/quant/README.md](../../src/quant/README.md), [research/README.md](../../research/README.md), [dashboards/hub/README.md](../../dashboards/hub/README.md), [tools/brain/README.md](../../tools/brain/README.md), [tools/backtest/README.md](../../tools/backtest/README.md), [first note](../notes/DarkEB1/2026-10-29-open-questions-after-the-scaffold.md), [scripts/check_links.py](../../scripts/check_links.py)

## Files relied on

- The setup spec pasted by @DarkEB1 (not stored in the repo; its decisions are in ADR-0001)
- The pre-existing [README.md](../../README.md) description and markets sections (kept verbatim)
- Cloudflare R2 dashboard (bucket settings, token forms) and the GitHub repository settings

## PR

`chore/initial-scaffold` -> `main`, titled "chore: initial scaffold"; the PR body holds the
done-when checklist with results. Not merged by the agent: `.github/**` and `catalog/**` are in
the data-layer CODEOWNERS block.
