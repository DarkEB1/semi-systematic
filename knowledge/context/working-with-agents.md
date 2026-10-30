---
id: working-with-agents
type: context
title: "Working with agents: invoking skills, tasks and loops, reviewing their PRs"
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [infra]
related: [start-here, walkthrough, workflow]
---

# Working with agents: invoking skills, tasks and loops, reviewing their PRs

An agent here is any model with a terminal in the devcontainer. It gets the same recipes and the
same rules as a person, plus three things a person does not need: a written skill to follow, a
budget when it loops, and an agent-log entry when it stops. This page is for the human who asks
and for the agent who is asked.

## The seven skills

A skill is a folder `.claude/skills/<name>/` with two files. `SKILL.md` is the recipe: Inputs,
Steps, Checks before opening the PR, Done when. `run.py` is the deterministic part, the thing a
`just` recipe calls, so the boring half of every skill is a program with a golden test in
`ai/evals/<name>/` and the model only supplies judgement.

| skill | ask it to | deterministic part |
|---|---|---|
| new-experiment | start, finish or check an experiment | `just experiment SLUG [--finish]` |
| pull-data | add a data source end to end | `just scaffold-source SOURCE` |
| refresh-data | find and fill stale raw partitions | `just refresh [--execute]` |
| promote-dataset | move a scratch table to curated under the schema contract | `just promote-request NAME KEY` |
| meeting-notes | turn a transcript into minutes, ADR drafts and actions | `just meeting DATE TITLE` |
| build-index | rebuild the index, answer "what do we know about X" with citations | `just index`, `just search Q` |
| repo-structure | say where a thing goes; change a convention everywhere at once | `just where THING` |

## Invoking a skill

**From Claude Code** (the devcontainer has it on the path): open the repo and type the skill name
as a slash command with the inputs in words, for example

```text
/new-experiment slug carry-reversion, hypothesis "EM currencies with the steepest carry mean-revert
after a dollar shock", dataset prices_daily at snapshot 2026-10-29
```

Claude Code reads `CLAUDE.md` (which says "Read AGENTS.md") and the skill's `SKILL.md`, then
follows the Steps. You will see it run `just search`, then `just experiment`, then edit, then
write the agent-log entry and open the PR.

**From any other assistant with a terminal**: paste the matching prompt from `ai/prompts/<name>.md`
and fill the placeholders. Each prompt is self-contained: it tells the assistant where it is, the
rules that cannot be broken, to read `AGENTS.md` and the `SKILL.md`, and what done looks like.
[ai/prompts/README.md](../../ai/prompts/README.md) lists them.

**Without a model at all**: the deterministic part alone is often enough. `just experiment`,
`just meeting`, `just promote-request` and `just scaffold-source` are usable by hand; the skill
adds the search, the judgement and the write-up.

## What a good request looks like

Give the skill its Inputs section, nothing more. For new-experiment that is a slug, a one-line
hypothesis and the datasets with snapshots. For meeting-notes it is the date, the title, the
attendees, the recording link and the transcript pasted into the chat (it stays there). For
build-index it is a question. A vague request ("look into carry") makes the agent guess the
hypothesis, and a guessed hypothesis is the one thing the repo cannot check.

## Tasks and loops

A loop is a skill run repeatedly without a person in between. It needs a task file, and the task
file needs a budget; the runner refuses otherwise.

```text
$ just task sweep-lookbacks --skill new-experiment \
    --arg='{slug}-{i}' --arg=--project --arg=em-carry --arg=--owner --arg=DarkEB1 \
    --goal "find the lookback at which carry reversion stops improving" \
    --metric "sharpe after 5 bp costs from outputs/metrics.json"
```

writes `ai/tasks/sweep-lookbacks.yaml`:

```yaml
slug: sweep-lookbacks
created: '2026-10-29'
owner: DarkEB1
goal: find the lookback at which carry reversion stops improving
metric: sharpe after 5 bp costs from outputs/metrics.json
skill: new-experiment
args:
- '{slug}-{i}'
- --project
- em-carry
- --owner
- DarkEB1
budget:
  max_iterations: 2
  max_hours: 1.0
stop_conditions: []
allowed_paths:
- research/
- knowledge/agent-log/
- knowledge/research-log/
```

Edit it before running: raise the budget deliberately, add stop conditions
(`stdout_contains:<text>` or `file_exists:<path>`), and keep `allowed_paths` as narrow as the
job. `{slug}` and `{i}` (1-based iteration) are substituted into `args`.

`just loop sweep-lookbacks` then, per iteration: records `git status`, runs the skill's `run.py`
with the args, lists the files that changed, stops if any is outside `allowed_paths` (files are
left in place, nothing reverted), stops on a non-zero exit or a stop condition, and otherwise
continues until `max_iterations` or `max_hours`. Every iteration is appended to one file,
`knowledge/agent-log/<date>-loop-<slug>.md`, titled "Loop <slug>: <skill> x<iterations>", which
looks like this (from [the demo in the repo](../agent-log/2026-10-29-loop-demo.md)):

```markdown
## Task
- goal: ...
- budget: 2 iterations, 1.0 h
- allowed paths: research/, knowledge/agent-log/, knowledge/research-log/
- stop conditions: none (budget only)

## Summary
Stop reason: **budget: max_iterations reached**.

### Iteration 1
- exit code: 0
- changed: nothing
- output: (last five lines)

## PR
none yet. Review the files above, then open a PR with `gh pr create` (the loop never merges).
```

**Model-driven loops** use the same file and the same guard rails. Replace the deterministic part
with a command:

```yaml
command: ["claude", "-p", "/new-experiment {slug}-{i}: next lookback in the sweep; read ai/tasks/{slug}.yaml for the goal and metric"]
```

The runner executes that instead of `run.py`, with the same budget, path check and agent-log.
Models the agents may use are named in `ai/models.yaml`; adding a paid one is an ADR.

## Reviewing an agent's work

Open the PR and the agent-log entry side by side. The entry has six sections and each answers a
review question:

- **Task**: was it asked what the PR does, by whom, with which skill and budget?
- **Decisions with justification**: every judgement call and what was ruled out. An empty section on a non-trivial PR is a finding.
- **Summary**: done, not done, needs a human. "Not done" items are your to-do list, not a failure.
- **Files touched**: must equal the PR's diff. Anything in the diff but not here was unintended.
- **Files relied on**: what it read. If a decision contradicts one of these files, it misread it.
- **PR**: the link, or why there is none.

Then the usual: CI green, numbers in `results.md` traceable to `outputs/`, no file renamed or
moved under `knowledge/`, tags from `tags.md`, owner in `team.yaml`. The hub's agent-log page
lists every entry newest first, so a weekly skim is cheap.

## What an agent may do alone

- Commit, push, and merge its own PR when CI is green and no changed path is under
  `src/quant/data/**`, `catalog/**`, `promote/**` or `.github/**`. Otherwise it opens the PR and stops.
- Write data only under `scratch/<handle>/` (in CI, `scratch/ci/`). It cannot write `raw/` or
  `curated/`; the data layer refuses, and the keys on a laptop cannot either.
- Append a tag to `tags.md` with a definition, in the same PR that first uses it.
- Never: read a secret back, add a dependency without an ADR, rename or move a knowledge file, run
  without a budget, or notify anyone outside issues and PRs.
