---
id: workflow
type: context
title: "Workflow: a researcher's week and an agent loop"
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [infra, idea, signal]
related: [strategy, tags]
---

# Workflow: a researcher's week and an agent loop

Written for a new teammate or a new agent. Everything below is done through `just` recipes inside
the devcontainer; `just` alone lists them. The rules are in `AGENTS.md` and the per-folder `AGENTS.md` files; this file is the story.

## Monday: an idea

You think EM currencies with the steepest carry mean-revert after a dollar shock. Before anything
else, search: `just search "carry mean reversion"` and `just search "dollar shock"`. The index
covers notes, decisions, meetings, past experiments and code. Read what comes back; if someone
already killed the idea, the research-log says why. If the idea survives, write a short note in
`knowledge/notes/<you>/` from the note template, tagged `idea` and `fx`.

## Tuesday: an experiment

Experiments live inside a project, which is a folder: `just project em-carry` creates
`research/em-carry/README.md` (goal, hypotheses, data, status) once. Then
`just experiment carry-reversion --project em-carry` creates
`research/em-carry/experiments/2026-10-27-carry-reversion/` with
`config.yaml` (slug, owner, hypothesis, datasets with snapshots, params, seed), a marimo `run.py`
that loads exactly those datasets through `quant.data.load`, a `results.md` stub and `figures/`.
Fill the hypothesis and params, pick the snapshot you want to be reproducible against, and run the
notebook. If the data you need is not in the catalog, stop and use the pull-data skill (below).

## Wednesday: data is missing

The pull-data skill scaffolds a new source: `just scaffold-source fred` writes the ingest module
from the template, the dataset README with its Schema table, the catalog view, a test with a small
fixture, the registry entry and the nightly workflow entry. You fill in `fetch` and `normalise`,
run `just ingest fred --dry-run`, then `just ingest fred` which writes to your `scratch/<you>/`
(a laptop can never write `raw/`). Open the PR; once merged, the nightly ingest fills `raw/`.
If a dataset you rely on goes stale, `just refresh` finds the gap and re-ingests it.

## Thursday: finish and promote

`just experiment carry-reversion --finish` drafts `results.md` and the research-log entry from
`config.yaml` and the run outputs, never inventing numbers. Set `status: final` when you are done;
the folder is frozen from then on and a follow-up is a new experiment with `parent:` set. If the
experiment produced a dataset others should build on, `just promote-request <name> <scratch key>`
validates the Parquet against the dataset README and writes a request under `promote/requests/`;
the merge to main promotes it to `curated/<name>/snapshot=<date>/`.

## The reuse rule

Code moves out of an experiment into a tool (`just new-tool <name>`, or an existing one under
`tools/`) only when a second experiment needs it, with a test, in its own PR. Until then,
duplication is fine and the new-experiment skill merely flags it. Experiments never import each
other: they meet only in the data layer, the dashboard and `knowledge/`.

## Friday: the PR and the index

Open the PR with a research-log entry and the experiment; CI runs `just check`, `just test` and
`just eval`. Squash-merge when green. On merge, `just index` runs in CI and the chunk table goes
to `curated/repo_index/`, so Monday's search finds this week's work.

## An agent loop

An agent gets the same tools and the same rules, plus a budget. `just task sweep-lookbacks` writes
`ai/tasks/sweep-lookbacks.yaml` with a goal, a metric, `max_iterations`, `max_hours`,
stop conditions and `allowed_paths`. `just loop sweep-lookbacks` re-invokes the named skill until a
stop condition or the budget is hit, appending every iteration to one agent-log entry. The runner
refuses to start without a budget and stops the moment a file lands outside `allowed_paths`. A
skill may merge its own PR only when CI is green and no changed path is under CODEOWNERS; otherwise
it opens the PR and stops.

## Meetings

Paste the transcript or bullets into the meeting-notes skill. It writes the meeting file in
template shape, applies the ADR test to each decision (an ADR when it changes a convention, a
dependency, a data source, a reusable method, or costs money; otherwise a line marked (minor)),
drafts the ADRs, checkboxes the actions with owners and dates, and links related files. The
transcript itself is never stored, only a link to the recording.
